from __future__ import annotations

from datetime import UTC, datetime
import json
import re
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.github_issue_creation_real_run_gate import (
    DEFAULT_AUTONOMY_PROFILE,
    LIVE_AUTONOMY_PROFILE,
    GitHubIssueRealRunClient,
    create_github_issue_real_run_gate,
)
from aresforge.operator.github_issue_sync_plan import plan_github_issue_sync
from aresforge.operator.github_link_registry import inspect_github_link_registry
from aresforge.operator.local_project_queue import resolve_project_queue_path
from aresforge.operator.machine_safety_gate_engine import evaluate_machine_safety_gates

COMMAND_NAME = "backfill-queue-items-to-github-issues"
RECORD_TYPE = "queue_to_github_issue_backfill_v1"
DEFAULT_PROJECT_ID = "aresforge"
DEFAULT_ITEM_ID = "m172-queue-to-github-issue-backfill"

_BOUNDARY_CONFIRMATIONS: tuple[str, ...] = (
    "Dry-run is the default behavior and performs no GitHub mutation.",
    "Backfill scans local queue items and skips items with local linked-issue metadata or an existing local registry issue link.",
    "Live issue creation requires --github-enabled, non-dry-run behavior, autonomy_profile=github_issue_sync_enabled, candidate-level safety checks, local duplicate prevention, and passing machine gates.",
    "Creation attempts are idempotent through local queue metadata, the local GitHub link registry, and per-item idempotency keys.",
    "No pull request merge, auto-merge, force push, protected branch update, release creation, workflow mutation, issue closure, source patch application, Codex execution, model execution, validation command execution, retry, resume, or next-item execution is performed.",
)


def backfill_queue_items_to_github_issues(
    config: AppConfig,
    *,
    project_id: str = DEFAULT_PROJECT_ID,
    item_id: str = DEFAULT_ITEM_ID,
    queue_path: str | Path | None = None,
    registry_path: str | Path | None = None,
    dry_run: bool = True,
    github_enabled: bool = False,
    autonomy_profile: str = DEFAULT_AUTONOMY_PROFILE,
    repo: str | None = None,
    max_creations: int | None = None,
    output: str | Path | None = None,
    force: bool = False,
    output_format: str = "json",
    github_client: GitHubIssueRealRunClient | None = None,
) -> dict[str, Any]:
    fmt = _text(output_format).lower() or "json"
    if fmt != "json":
        return _error("invalid_format", {"format": output_format, "supported_formats": ["json"]})

    normalized_project_id = _text(project_id) or DEFAULT_PROJECT_ID
    normalized_item_id = _text(item_id) or DEFAULT_ITEM_ID
    normalized_repo = _normalize_repo(config, repo)
    selected_autonomy_profile = _text(autonomy_profile) or DEFAULT_AUTONOMY_PROFILE
    effective_dry_run = bool(dry_run) or not bool(github_enabled)
    creation_budget = _creation_budget(max_creations=max_creations, effective_dry_run=effective_dry_run)
    generated_at = _now_iso()
    resolved_queue_path = resolve_project_queue_path(config.repo_root, queue_path)
    preflight_path: Path | None = None
    if not effective_dry_run and github_enabled:
        preflight_path = _write_preflight_record(
            config=config,
            project_id=normalized_project_id,
            item_id=normalized_item_id,
            repository=normalized_repo,
            autonomy_profile=selected_autonomy_profile,
            max_creations=creation_budget,
        )

    plan_payload = _payload(
        plan_github_issue_sync(
            config,
            project_id=normalized_project_id,
            item_id=normalized_item_id,
            queue_path=queue_path,
            output_format="json",
        )
    )
    gate_payload = _payload(
        evaluate_machine_safety_gates(
            config,
            item_id=normalized_item_id,
            gate_profile="read_only_agent" if effective_dry_run else "github_sync",
            artifact_path=preflight_path,
            execution_record=preflight_path,
            queue_path=queue_path,
            force=bool(github_enabled),
            output_format="json",
        )
    )
    gate_summary = _gate_summary(gate_payload, default_profile="read_only_agent" if effective_dry_run else "github_sync")

    backfill_items: list[dict[str, Any]] = []
    creation_count = 0
    github_execution_performed = False
    mutation_performed = False
    registry_mutation_performed = False

    for item_plan in _dicts(plan_payload.get("issue_sync_items")):
        item_record = _backfill_item_record(
            config,
            item_plan=item_plan,
            project_id=normalized_project_id,
            repository=normalized_repo,
            registry_path=registry_path,
            queue_path=queue_path,
            effective_dry_run=effective_dry_run,
            github_enabled=bool(github_enabled),
            autonomy_profile=selected_autonomy_profile,
            creation_budget_remaining=max(0, creation_budget - creation_count) if creation_budget is not None else None,
            github_client=github_client,
        )
        backfill_items.append(item_record)
        if bool(item_record.get("github_execution_performed")):
            github_execution_performed = True
        if bool(item_record.get("mutation_performed")):
            mutation_performed = True
        if bool(item_record.get("registry_mutation_performed")):
            registry_mutation_performed = True
        if _text(item_record.get("sync_status")) == "synced":
            creation_count += 1

    blocked_reasons = _dedupe([*_list(plan_payload.get("blocked_reasons")), *_list(gate_payload.get("blocked_reasons"))])
    if plan_payload.get("blocked") is True:
        blocked_reasons.append("GitHub issue sync source plan is blocked.")
    if gate_payload.get("passed") is not True or gate_payload.get("blocked") is True:
        blocked_reasons.append("Backfill machine gate did not pass.")
    if not effective_dry_run and not github_enabled:
        blocked_reasons.append("Live backfill requires --github-enabled.")
    if not effective_dry_run and selected_autonomy_profile != LIVE_AUTONOMY_PROFILE:
        blocked_reasons.append(f"Live backfill requires autonomy_profile={LIVE_AUTONOMY_PROFILE}.")

    blocked = bool(blocked_reasons)
    operation_counts = _operation_counts(backfill_items)
    payload: dict[str, Any] = {
        "record_type": RECORD_TYPE,
        "artifact_type": RECORD_TYPE,
        "generated": True,
        "generated_at": generated_at,
        "project_id": normalized_project_id,
        "item_id": normalized_item_id,
        "repository": normalized_repo,
        "issue_number": None,
        "issue_url": "",
        "pr_number": None,
        "pr_url": "",
        "sync_status": "blocked" if blocked else ("dry_run_ready" if effective_dry_run else "completed"),
        "status": "blocked" if blocked else ("dry_run_ready" if effective_dry_run else "completed"),
        "blocked": blocked,
        "blocked_reasons": blocked_reasons,
        "warnings": _dedupe([*_list(plan_payload.get("warnings")), *_list(gate_payload.get("warnings"))]),
        "machine_gates_checked": [gate_summary],
        "machine_gates_passed": bool(gate_summary.get("passed")) and not blocked,
        "autonomy_profile": selected_autonomy_profile,
        "dry_run": bool(effective_dry_run),
        "github_enabled": bool(github_enabled),
        "github_execution_performed": bool(github_execution_performed and not blocked),
        "mutation_performed": bool(mutation_performed and not blocked),
        "github_issue_mutation_performed": bool(mutation_performed and not blocked),
        "registry_mutation_performed": bool(registry_mutation_performed and not blocked),
        "queue_mutation_performed": False,
        "codex_execution_performed": False,
        "model_execution_performed": False,
        "patch_application_performed": False,
        "idempotency_key": _idempotency_key(project_id=normalized_project_id, repository=normalized_repo),
        "recovery_available": True,
        "local_only": not bool(github_execution_performed and not blocked),
        "next_safe_action": _next_safe_action(blocked=blocked, dry_run=effective_dry_run, operation_counts=operation_counts),
        "artifacts_created": [str(preflight_path)] if preflight_path else [],
        "queue_path": str(resolved_queue_path),
        "registry_path": _registry_path_from_items(backfill_items),
        "source_plan_record_type": _text(plan_payload.get("record_type")),
        "queue_item_count": len(backfill_items),
        "operation_counts": operation_counts,
        "max_creations": creation_budget,
        "github_creation_limit_reached": bool(creation_budget is not None and creation_count >= creation_budget),
        "backfill_items": backfill_items,
        "github_operations_blocked": [
            "merge_pull_request",
            "force_push",
            "update_protected_branch",
            "enable_auto_merge",
            "create_release",
            "modify_github_workflow",
            "close_issue",
            "source_code_patch",
        ],
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
        "completed_at": _now_iso(),
    }
    return _emit_or_write(config=config, payload=payload, output=output, force=force)


def _backfill_item_record(
    config: AppConfig,
    *,
    item_plan: dict[str, Any],
    project_id: str,
    repository: str,
    registry_path: str | Path | None,
    queue_path: str | Path | None,
    effective_dry_run: bool,
    github_enabled: bool,
    autonomy_profile: str,
    creation_budget_remaining: int | None,
    github_client: GitHubIssueRealRunClient | None,
) -> dict[str, Any]:
    queue_item_id = _text(item_plan.get("item_id"))
    linked_issue = item_plan.get("linked_issue") if isinstance(item_plan.get("linked_issue"), dict) else {}
    registry_payload = _payload(
        inspect_github_link_registry(
            config,
            project_id=project_id,
            item_id=DEFAULT_ITEM_ID,
            registry_path=registry_path,
            queue_item_id=queue_item_id,
            repository=repository,
            output_format="json",
        )
    )
    registry_duplicate = _registry_duplicate(registry_payload)
    blocked_reasons = _dedupe([*_list(item_plan.get("blocked_reasons")), *_list(registry_payload.get("blocked_reasons"))])
    warnings = _dedupe([*_list(item_plan.get("warnings")), *_list(registry_payload.get("warnings"))])
    candidate = (
        not bool(item_plan.get("blocked"))
        and not bool(linked_issue.get("linked"))
        and not registry_duplicate
        and _has_create_recommendation(item_plan)
    )
    skip_reason = ""
    if bool(linked_issue.get("linked")):
        skip_reason = "already_linked_queue_metadata"
    elif registry_duplicate:
        skip_reason = "already_linked_registry"
    elif item_plan.get("blocked"):
        skip_reason = "queue_item_blocked"
    elif not _has_create_recommendation(item_plan):
        skip_reason = "no_create_recommendation"
    elif creation_budget_remaining is not None and creation_budget_remaining <= 0:
        candidate = False
        skip_reason = "creation_limit_reached"

    creation_payload: dict[str, Any] = {}
    if candidate and not effective_dry_run:
        creation_payload = _payload(
            create_github_issue_real_run_gate(
                config,
                item_id=queue_item_id,
                project_id=project_id,
                queue_path=queue_path,
                registry_path=registry_path,
                dry_run=effective_dry_run,
                github_enabled=github_enabled,
                autonomy_profile=autonomy_profile,
                repo=repository,
                output_format="json",
                github_client=github_client,
            )
        )
        blocked_reasons = _dedupe([*blocked_reasons, *_list(creation_payload.get("blocked_reasons"))])
        warnings = _dedupe([*warnings, *_list(creation_payload.get("warnings"))])

    sync_status = _item_sync_status(
        candidate=candidate,
        skip_reason=skip_reason,
        creation_payload=creation_payload,
        effective_dry_run=effective_dry_run,
        blocked_reasons=blocked_reasons,
    )
    issue_number = creation_payload.get("issue_number") if creation_payload else linked_issue.get("issue_number")
    issue_url = creation_payload.get("issue_url") if creation_payload else linked_issue.get("issue_url")
    return {
        "record_type": "queue_to_github_issue_backfill_item_v1",
        "artifact_type": "queue_to_github_issue_backfill_item_v1",
        "generated": True,
        "project_id": project_id,
        "item_id": queue_item_id,
        "repository": repository,
        "issue_number": issue_number,
        "issue_url": _text(issue_url),
        "pr_number": None,
        "pr_url": "",
        "sync_status": sync_status,
        "blocked": bool(blocked_reasons),
        "blocked_reasons": blocked_reasons,
        "warnings": warnings,
        "machine_gates_checked": _list_dicts(creation_payload.get("machine_gates_checked")),
        "machine_gates_passed": bool(creation_payload.get("machine_gates_passed")) if creation_payload else not bool(blocked_reasons),
        "autonomy_profile": autonomy_profile,
        "dry_run": bool(effective_dry_run),
        "github_enabled": bool(github_enabled),
        "github_execution_performed": bool(creation_payload.get("github_execution_performed")),
        "mutation_performed": bool(creation_payload.get("mutation_performed")),
        "registry_mutation_performed": bool(creation_payload.get("registry_mutation_performed")),
        "idempotency_key": _item_idempotency_key(project_id=project_id, item_id=queue_item_id, repository=repository),
        "recovery_available": True,
        "local_only": not bool(creation_payload.get("github_execution_performed")),
        "next_safe_action": _item_next_safe_action(sync_status),
        "queue_status": _text(item_plan.get("queue_status")),
        "backfill_action": "create_issue" if candidate else "skip",
        "skip_reason": skip_reason,
        "linked_issue": linked_issue or {"linked": False, "issue_number": None, "issue_url": "", "metadata_source": ""},
        "registry_duplicate_link_blocked": registry_duplicate,
        "registry_lookup_summary": {
            "record_type": _text(registry_payload.get("record_type")),
            "matched_record_count": _int(registry_payload.get("matched_record_count")),
            "registry_path": _text(registry_payload.get("registry_path")),
        },
        "issue_payload": creation_payload.get("issue_draft") if creation_payload else item_plan.get("issue_draft", {}),
        "created_issue": creation_payload.get("created_issue", {}),
    }


def _item_sync_status(
    *,
    candidate: bool,
    skip_reason: str,
    creation_payload: dict[str, Any],
    effective_dry_run: bool,
    blocked_reasons: list[str],
) -> str:
    if skip_reason.startswith("already_linked"):
        return "already_linked"
    if blocked_reasons and not candidate:
        return "blocked"
    if skip_reason:
        return "skipped"
    if creation_payload.get("sync_status"):
        return _text(creation_payload.get("sync_status"))
    if candidate and effective_dry_run:
        return "dry_run_ready"
    if candidate:
        return "planned"
    return "skipped"


def _operation_counts(items: list[dict[str, Any]]) -> dict[str, int]:
    counts = {
        "create_planned": 0,
        "already_linked": 0,
        "blocked": 0,
        "skipped": 0,
        "issue_created": 0,
    }
    for item in items:
        status = _text(item.get("sync_status"))
        if status in {"dry_run_ready", "planned"}:
            counts["create_planned"] += 1
        elif status == "synced":
            counts["issue_created"] += 1
        elif status == "already_linked":
            counts["already_linked"] += 1
        elif status == "blocked":
            counts["blocked"] += 1
        else:
            counts["skipped"] += 1
    return counts


def _write_preflight_record(
    *,
    config: AppConfig,
    project_id: str,
    item_id: str,
    repository: str,
    autonomy_profile: str,
    max_creations: int | None,
) -> Path:
    path = config.artifact_root / "queue_to_github_issue_backfill" / "gates" / f"{_stamp()}-{_safe_id(item_id)}.json"
    payload = {
        "artifact_type": "queue_to_github_issue_backfill_preflight_v1",
        "execution_record_type": "queue_to_github_issue_backfill_preflight_v1",
        "project_id": project_id,
        "item_id": item_id,
        "repository": repository,
        "autonomy_profile": autonomy_profile,
        "max_creations": max_creations,
        "local_only": True,
        "execution_allowed": False,
        "execution_performed": False,
        "external_execution_performed": False,
        "github_execution_performed": False,
        "model_execution_performed": False,
        "codex_execution_performed": False,
        "patch_application_performed": False,
        "queue_mutation_performed": False,
        "validation_commands": ["python -m pytest tests/test_queue_to_github_issue_backfill.py"],
        "tests_reported": ["python -m pytest tests/test_queue_to_github_issue_backfill.py -> runnable"],
        "capabilities_used": ["read_local_queue", "read_local_issue_sync_plan", "read_local_github_link_registry"],
        "created_at": _now_iso(),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def _registry_duplicate(registry_payload: dict[str, Any]) -> bool:
    for record in _dicts(registry_payload.get("records")):
        if _int(record.get("issue_number")) > 0 or _text(record.get("issue_url")):
            return True
    return False


def _has_create_recommendation(item_plan: dict[str, Any]) -> bool:
    for recommendation in _dicts(item_plan.get("recommendations")):
        if _text(recommendation.get("recommended_action")) == "create":
            return True
    return False


def _gate_summary(gate_payload: dict[str, Any], *, default_profile: str) -> dict[str, Any]:
    checks = gate_payload.get("checks", [])
    failed = [
        _text(check.get("check_id"))
        for check in checks
        if isinstance(check, dict) and not bool(check.get("passed")) and not bool(check.get("warning_only"))
    ]
    return {
        "gate_profile": _text(gate_payload.get("gate_profile")) or default_profile,
        "passed": bool(gate_payload.get("passed")) and not bool(gate_payload.get("blocked")),
        "blocked": bool(gate_payload.get("blocked")),
        "blocked_reasons": _list(gate_payload.get("blocked_reasons")),
        "checks_failed": failed,
    }


def _next_safe_action(*, blocked: bool, dry_run: bool, operation_counts: dict[str, int]) -> str:
    if blocked:
        return "Resolve local plan or machine-gate blockers before any backfill execution."
    if dry_run:
        return "Review planned issue payloads and existing-link skips; live backfill requires --github-enabled with autonomy_profile=github_issue_sync_enabled."
    if operation_counts.get("issue_created", 0):
        return "Review created issues and local registry links; continue only with separate gated status-comment or PR-summary commands."
    return "No GitHub issue creation was performed."


def _item_next_safe_action(sync_status: str) -> str:
    if sync_status == "already_linked":
        return "Use the existing local link and skip duplicate issue creation."
    if sync_status == "dry_run_ready":
        return "Review this issue payload before any separate live creation attempt."
    if sync_status == "synced":
        return "Review the created issue and local registry record."
    if sync_status == "blocked":
        return "Resolve item-level blockers before retrying backfill."
    return "No live action is safe from this item record without a separate gated command."


def _emit_or_write(
    *,
    config: AppConfig,
    payload: dict[str, Any],
    output: str | Path | None,
    force: bool,
) -> dict[str, Any]:
    if output is None:
        return {
            "command": COMMAND_NAME,
            "ok": not bool(payload.get("blocked")),
            "local_only": bool(payload.get("local_only")),
            "format": "json",
            "wrote_output_file": False,
            "stdout": json.dumps(payload, indent=2),
            "payload": payload,
        }
    output_path = _resolve(config.repo_root, output)
    if output_path.exists() and not force:
        blocked = dict(payload)
        blocked["status"] = "blocked"
        blocked["sync_status"] = "blocked"
        blocked["blocked"] = True
        blocked["blocked_reasons"] = _dedupe(
            [*_list(blocked.get("blocked_reasons")), "Output file already exists. Re-run with --force to overwrite."]
        )
        blocked["github_execution_performed"] = False
        blocked["mutation_performed"] = False
        return {
            "command": COMMAND_NAME,
            "ok": False,
            "local_only": True,
            "format": "json",
            "output": str(output_path),
            "force": force,
            "wrote_output_file": False,
            "stdout": json.dumps(blocked, indent=2),
            "payload": blocked,
        }
    artifact_payload = dict(payload)
    artifact_payload["artifacts_created"] = _dedupe([*_list(payload.get("artifacts_created")), str(output_path)])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact_payload, indent=2) + "\n", encoding="utf-8")
    return {
        "command": COMMAND_NAME,
        "ok": not bool(artifact_payload.get("blocked")),
        "local_only": bool(artifact_payload.get("local_only")),
        "format": "json",
        "output": str(output_path),
        "force": force,
        "wrote_output_file": True,
        "payload": artifact_payload,
    }


def _payload(result: dict[str, Any]) -> dict[str, Any]:
    payload = result.get("payload", {}) if isinstance(result, dict) else {}
    return payload if isinstance(payload, dict) else {}


def _registry_path_from_items(items: list[dict[str, Any]]) -> str:
    for item in items:
        summary = item.get("registry_lookup_summary")
        if isinstance(summary, dict) and _text(summary.get("registry_path")):
            return _text(summary.get("registry_path"))
    return ""


def _creation_budget(*, max_creations: int | None, effective_dry_run: bool) -> int | None:
    if effective_dry_run:
        return None
    if max_creations is None:
        return 1
    return max(0, int(max_creations))


def _normalize_repo(config: AppConfig, repo: str | None) -> str:
    raw = _text(repo)
    if raw:
        return raw
    return f"{config.github_owner}/{config.github_repo}"


def _idempotency_key(*, project_id: str, repository: str) -> str:
    return "queue-github-issue-backfill:" + ":".join([_slug(project_id), _slug(repository)])


def _item_idempotency_key(*, project_id: str, item_id: str, repository: str) -> str:
    return "queue-github-issue-backfill-item:" + ":".join([_slug(project_id), _slug(item_id), _slug(repository)])


def _resolve(repo_root: Path, value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


def _dicts(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [entry for entry in value if isinstance(entry, dict)]
    return []


def _list_dicts(value: Any) -> list[dict[str, Any]]:
    return _dicts(value)


def _list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [_text(entry) for entry in value if _text(entry)]
    if isinstance(value, tuple):
        return [_text(entry) for entry in value if _text(entry)]
    if value in (None, ""):
        return []
    return [_text(value)]


def _dedupe(values: Any) -> list[str]:
    deduped: list[str] = []
    for value in values:
        text = _text(value)
        if text and text not in deduped:
            deduped.append(text)
    return deduped


def _int(value: Any) -> int:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    text = _text(value)
    return int(text) if text.isdigit() else 0


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", _text(value).lower()).strip("-") or "unknown"


def _safe_id(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in _text(value).lower())
    return cleaned.strip("-") or "queue-to-github-issue-backfill"


def _stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")


def _text(value: Any) -> str:
    return str(value or "").strip()


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _error(error: str, details: dict[str, Any]) -> dict[str, Any]:
    return {
        "command": COMMAND_NAME,
        "ok": False,
        "local_only": True,
        "error": error,
        "details": details,
    }
