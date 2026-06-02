from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
import re
import subprocess
from typing import Any, Protocol

from aresforge.config import AppConfig
from aresforge.operator.github_issue_sync_plan import plan_github_issue_sync
from aresforge.operator.github_link_registry import (
    inspect_github_link_registry,
    record_github_link,
)
from aresforge.operator.local_project_queue import resolve_project_queue_path
from aresforge.operator.machine_safety_gate_engine import evaluate_machine_safety_gates
from aresforge.operator.operator_autonomy_configuration_profile import inspect_autonomy_profile

COMMAND_NAME = "create-github-issue-real-run-gate"
RECORD_TYPE = "github_issue_creation_real_run_gate_v1"
DEFAULT_PROJECT_ID = "aresforge"
DEFAULT_ITEM_ID = "m171-github-issue-creation-real-run-gate"
DEFAULT_AUTONOMY_PROFILE = "github_sync_dry_run"
LIVE_AUTONOMY_PROFILE = "github_issue_sync_enabled"
SAFE_QUEUE_STATUSES: frozenset[str] = frozenset({"proposed", "ready", "in_progress"})

_BOUNDARY_CONFIRMATIONS: tuple[str, ...] = (
    "Dry-run is the default behavior and performs no GitHub mutation.",
    "Real issue creation requires --github-enabled, a non-dry-run request, github_issue_sync_enabled autonomy profile, a safe queue item status, no linked issue in local queue metadata, no matching issue link in the local GitHub link registry, and a passing github_sync machine gate.",
    "Only one queue item and one GitHub issue create attempt are considered per command invocation.",
    "Successful real issue creation records an idempotent local GitHub link registry entry; it does not mutate queue item state.",
    "No pull request merge, auto-merge, force push, protected branch update, release creation, workflow mutation, issue closure, source patch application, Codex execution, model execution, validation command execution, retry, resume, or next-item execution is performed.",
)


class GitHubIssueRealRunClient(Protocol):
    def create_issue(
        self,
        *,
        repo: str,
        title: str,
        body: str,
        labels: list[str],
        milestone: str,
    ) -> dict[str, Any]:
        ...


@dataclass(frozen=True)
class GhCliGitHubIssueRealRunClient:
    timeout_seconds: int = 30

    def create_issue(
        self,
        *,
        repo: str,
        title: str,
        body: str,
        labels: list[str],
        milestone: str,
    ) -> dict[str, Any]:
        command = ["gh", "issue", "create", "--repo", repo, "--title", title, "--body", body]
        for label in labels:
            command.extend(["--label", label])
        if milestone:
            command.extend(["--milestone", milestone])
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=max(1, self.timeout_seconds),
            shell=False,
        )
        if completed.returncode != 0:
            detail = completed.stderr.strip() or completed.stdout.strip() or "gh issue create failed"
            raise RuntimeError(detail)
        url = completed.stdout.strip()
        return {
            "url": url,
            "html_url": url,
        }


def create_github_issue_real_run_gate(
    config: AppConfig,
    *,
    item_id: str = DEFAULT_ITEM_ID,
    project_id: str = DEFAULT_PROJECT_ID,
    queue_path: str | Path | None = None,
    registry_path: str | Path | None = None,
    dry_run: bool = True,
    github_enabled: bool = False,
    autonomy_profile: str = DEFAULT_AUTONOMY_PROFILE,
    repo: str | None = None,
    output: str | Path | None = None,
    force: bool = False,
    output_format: str = "json",
    github_client: GitHubIssueRealRunClient | None = None,
) -> dict[str, Any]:
    fmt = _text(output_format).lower() or "json"
    if fmt != "json":
        return _error("invalid_format", {"format": output_format, "supported_formats": ["json"]})

    normalized_item_id = _text(item_id) or DEFAULT_ITEM_ID
    normalized_project_id = _text(project_id) or DEFAULT_PROJECT_ID
    normalized_repo = _normalize_repo(config, repo)
    selected_autonomy_profile = _text(autonomy_profile) or DEFAULT_AUTONOMY_PROFILE
    requested_dry_run = bool(dry_run)
    effective_dry_run = requested_dry_run or not bool(github_enabled)
    generated_at = _now_iso()
    idempotency_key = _idempotency_key(
        project_id=normalized_project_id,
        item_id=normalized_item_id,
        repository=normalized_repo,
    )

    queue_path_resolved = resolve_project_queue_path(config.repo_root, queue_path)
    queue_result = _load_queue(queue_path_resolved)
    queue = queue_result.get("queue") if queue_result.get("ok") else {}
    item = _find_item(queue, normalized_item_id)
    item_project_id = _text(item.get("project_id")) or normalized_project_id

    plan_payload = _payload(
        plan_github_issue_sync(
            config,
            project_id=item_project_id,
            item_id=normalized_item_id,
            queue_path=queue_path,
            output_format="json",
        )
    )
    item_plan = _item_plan(plan_payload, normalized_item_id)
    issue_draft = item_plan.get("issue_draft") if isinstance(item_plan.get("issue_draft"), dict) else {}
    linked_issue = item_plan.get("linked_issue") if isinstance(item_plan.get("linked_issue"), dict) else {}

    registry_payload = _payload(
        inspect_github_link_registry(
            config,
            project_id=item_project_id,
            item_id=normalized_item_id,
            registry_path=registry_path,
            queue_item_id=normalized_item_id,
            repository=normalized_repo,
            output_format="json",
        )
    )
    registry_duplicate = _registry_duplicate(registry_payload)

    autonomy_payload = _payload(
        inspect_autonomy_profile(
            config,
            project_id=item_project_id,
            item_id=normalized_item_id,
            autonomy_profile=selected_autonomy_profile,
            queue_path=queue_path,
            output_format="json",
        )
    )

    preflight_path: Path | None = None
    if not effective_dry_run and github_enabled:
        preflight_path = _write_preflight_record(
            config=config,
            item_id=normalized_item_id,
            project_id=item_project_id,
            repo=normalized_repo,
            issue_draft=issue_draft,
            autonomy_profile=selected_autonomy_profile,
            idempotency_key=idempotency_key,
        )
    gate_payload = _gate_payload(
        config,
        item_id=normalized_item_id,
        queue_path=queue_path,
        dry_run=effective_dry_run,
        github_enabled=bool(github_enabled),
        preflight_path=preflight_path,
    )
    gate_summary = _gate_summary(gate_payload, default_profile="read_only_agent" if effective_dry_run else "github_sync")

    blocked_reasons = _blocked_reasons(
        queue_result=queue_result,
        item=item,
        item_plan=item_plan,
        plan_payload=plan_payload,
        linked_issue=linked_issue,
        registry_payload=registry_payload,
        registry_duplicate=registry_duplicate,
        github_enabled=bool(github_enabled),
        effective_dry_run=effective_dry_run,
        selected_autonomy_profile=selected_autonomy_profile,
        autonomy_payload=autonomy_payload,
        gate_payload=gate_payload,
        repo=normalized_repo,
    )
    warnings = _dedupe(
        [
            *queue_result.get("warnings", []),
            *_list(plan_payload.get("warnings")),
            *_list(item_plan.get("warnings")),
            *_list(registry_payload.get("warnings")),
            *_list(autonomy_payload.get("warnings")),
            *_list(gate_payload.get("warnings")),
        ]
    )

    github_execution_performed = False
    issue_created = False
    created_issue: dict[str, Any] = {}
    operation_error = ""
    registry_record: dict[str, Any] = {}
    registry_mutation_performed = False
    if not blocked_reasons and not effective_dry_run:
        client = github_client or GhCliGitHubIssueRealRunClient()
        try:
            created_issue = client.create_issue(
                repo=normalized_repo,
                title=_text(issue_draft.get("title")),
                body=_text(issue_draft.get("body")),
                labels=_list(issue_draft.get("labels")),
                milestone=_text(issue_draft.get("milestone")),
            )
            github_execution_performed = True
            issue_created = True
            issue_number = _issue_number(created_issue)
            issue_url = _issue_url(created_issue)
            registry_result = record_github_link(
                config,
                project_id=item_project_id,
                item_id=normalized_item_id,
                registry_path=registry_path,
                queue_item_id=normalized_item_id,
                repository=normalized_repo,
                issue_number=issue_number,
                issue_url=issue_url,
                sync_status="synced",
                last_sync_result=f"{COMMAND_NAME} created GitHub issue and recorded local link.",
                linked_by="aresforge-real-run-gate",
                link_source=COMMAND_NAME,
                output_format="json",
            )
            registry_record = _payload(registry_result).get("link_record", {})
            registry_mutation_performed = bool(_payload(registry_result).get("mutation_performed"))
        except (RuntimeError, OSError, subprocess.SubprocessError) as exc:
            operation_error = str(exc)
            blocked_reasons.append(f"GitHub issue creation real-run failed: {exc}")

    blocked = bool(blocked_reasons)
    issue_number = _issue_number(created_issue) if issue_created and not blocked else (_int(linked_issue.get("issue_number")) or None)
    issue_url = _issue_url(created_issue) if issue_created and not blocked else _text(linked_issue.get("issue_url"))
    status = _status(blocked=blocked, dry_run=effective_dry_run, issue_created=issue_created)
    payload: dict[str, Any] = {
        "record_type": RECORD_TYPE,
        "artifact_type": RECORD_TYPE,
        "generated": True,
        "generated_at": generated_at,
        "project_id": item_project_id,
        "item_id": normalized_item_id,
        "repository": normalized_repo,
        "repo": normalized_repo,
        "issue_number": issue_number,
        "issue_url": issue_url,
        "pr_number": None,
        "pr_url": "",
        "sync_status": "blocked" if blocked else ("dry_run_ready" if effective_dry_run else "synced"),
        "status": status,
        "blocked": blocked,
        "blocked_reasons": _dedupe(blocked_reasons),
        "warnings": warnings,
        "machine_gates_checked": [gate_summary],
        "machine_gates_passed": bool(gate_summary.get("passed")) and not blocked,
        "autonomy_profile": selected_autonomy_profile,
        "dry_run": bool(effective_dry_run),
        "github_enabled": bool(github_enabled),
        "github_execution_performed": bool(github_execution_performed and not blocked),
        "mutation_performed": bool(issue_created and not blocked),
        "github_issue_mutation_performed": bool(issue_created and not blocked),
        "registry_mutation_performed": bool(registry_mutation_performed and not blocked),
        "queue_mutation_performed": False,
        "codex_execution_performed": False,
        "model_execution_performed": False,
        "patch_application_performed": False,
        "idempotency_key": idempotency_key,
        "recovery_available": True,
        "local_only": not bool(github_execution_performed and not blocked),
        "next_safe_action": _next_safe_action(blocked=blocked, dry_run=effective_dry_run, issue_created=issue_created),
        "artifacts_created": [str(preflight_path)] if preflight_path else [],
        "queue_path": str(queue_path_resolved),
        "registry_path": _text(registry_payload.get("registry_path")),
        "queue_item_found": bool(item),
        "queue_item_status": _text(item.get("status")),
        "safe_queue_statuses": sorted(SAFE_QUEUE_STATUSES),
        "safe_queue_item_status": _text(item.get("status")) in SAFE_QUEUE_STATUSES,
        "linked_issue": linked_issue or {"linked": False, "issue_number": None, "issue_url": "", "metadata_source": ""},
        "duplicate_linked_issue_blocked": bool(linked_issue.get("linked")),
        "registry_duplicate_link_blocked": registry_duplicate,
        "registry_lookup_summary": _registry_summary(registry_payload),
        "issue_draft": issue_draft,
        "issue_creation_allowed": not blocked and not effective_dry_run,
        "issue_created": bool(issue_created and not blocked),
        "created_issue": _summarize_issue(created_issue) if issue_created and not blocked else {},
        "local_registry_record": registry_record if issue_created and not blocked else {},
        "operation_error": operation_error,
        "github_preflight_record_path": str(preflight_path) if preflight_path else "",
        "autonomy_profile_summary": _autonomy_summary(autonomy_payload),
        "source_plan_summary": _source_plan_summary(plan_payload, item_plan),
        "github_mutation_scope": "single_issue_create",
        "github_operations_blocked": [
            "merge_pull_request",
            "force_push",
            "update_protected_branch",
            "enable_auto_merge",
            "create_release",
            "modify_github_workflow",
            "close_issue",
            "bulk_issue_creation",
            "source_code_patch",
        ],
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
        "completed_at": _now_iso(),
    }
    return _emit_or_write(config=config, payload=payload, output=output, force=force)


def _gate_payload(
    config: AppConfig,
    *,
    item_id: str,
    queue_path: str | Path | None,
    dry_run: bool,
    github_enabled: bool,
    preflight_path: Path | None,
) -> dict[str, Any]:
    if dry_run:
        result = evaluate_machine_safety_gates(
            config,
            item_id=item_id,
            gate_profile="read_only_agent",
            queue_path=queue_path,
            output_format="json",
        )
    else:
        result = evaluate_machine_safety_gates(
            config,
            item_id=item_id,
            gate_profile="github_sync",
            artifact_path=preflight_path,
            execution_record=preflight_path,
            queue_path=queue_path,
            force=bool(github_enabled),
            output_format="json",
        )
    return _payload(result)


def _write_preflight_record(
    *,
    config: AppConfig,
    item_id: str,
    project_id: str,
    repo: str,
    issue_draft: dict[str, Any],
    autonomy_profile: str,
    idempotency_key: str,
) -> Path:
    path = config.artifact_root / "github_issue_creation_real_run_gate" / "gates" / f"{_stamp()}-{_safe_id(item_id)}.json"
    payload = {
        "artifact_type": "github_issue_creation_real_run_gate_preflight_v1",
        "execution_record_type": "github_issue_creation_real_run_gate_preflight_v1",
        "item_id": item_id,
        "project_id": project_id,
        "repository": repo,
        "repo": repo,
        "title": _text(issue_draft.get("title")),
        "labels": _list(issue_draft.get("labels")),
        "milestone": _text(issue_draft.get("milestone")),
        "autonomy_profile": autonomy_profile,
        "idempotency_key": idempotency_key,
        "local_only": True,
        "execution_allowed": False,
        "execution_performed": False,
        "external_execution_performed": False,
        "github_execution_performed": False,
        "model_execution_performed": False,
        "codex_execution_performed": False,
        "patch_application_performed": False,
        "queue_mutation_performed": False,
        "validation_commands": ["python -m pytest tests/test_github_issue_creation_real_run_gate.py"],
        "tests_reported": ["python -m pytest tests/test_github_issue_creation_real_run_gate.py -> runnable"],
        "capabilities_used": ["read_local_queue", "read_local_issue_sync_plan", "read_local_github_link_registry"],
        "created_at": _now_iso(),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def _blocked_reasons(
    *,
    queue_result: dict[str, Any],
    item: dict[str, Any],
    item_plan: dict[str, Any],
    plan_payload: dict[str, Any],
    linked_issue: dict[str, Any],
    registry_payload: dict[str, Any],
    registry_duplicate: bool,
    github_enabled: bool,
    effective_dry_run: bool,
    selected_autonomy_profile: str,
    autonomy_payload: dict[str, Any],
    gate_payload: dict[str, Any],
    repo: str,
) -> list[str]:
    reasons = [*queue_result.get("blocked_reasons", [])]
    if not queue_result.get("ok"):
        reasons.append("Local queue must be readable before GitHub issue creation can be considered.")
    if not item:
        reasons.append("Queue item must exist before GitHub issue creation can be considered.")
    status = _text(item.get("status"))
    if not effective_dry_run and item and status not in SAFE_QUEUE_STATUSES:
        reasons.append(f"Queue item status is not safe for real issue creation: {status or 'missing'}.")
    if not effective_dry_run and _list(item.get("blocked_by")):
        reasons.append("Queue item has blocked_by entries.")
    if not item_plan:
        reasons.append("Queue item was not present in the GitHub issue sync plan.")
    if bool(item_plan.get("blocked")):
        reasons.extend(_list(item_plan.get("blocked_reasons")))
    if bool(plan_payload.get("blocked")):
        reasons.extend(_list(plan_payload.get("blocked_reasons")))
    if not effective_dry_run and bool(linked_issue.get("linked")):
        reasons.append("Queue item already has linked GitHub issue metadata; duplicate real issue creation is blocked.")
    if bool(registry_payload.get("blocked")):
        reasons.append("GitHub link registry lookup is blocked.")
        reasons.extend(_list(registry_payload.get("blocked_reasons")))
    if not effective_dry_run and registry_duplicate:
        reasons.append("Local GitHub link registry already has an issue link for this queue item and repository.")
    if not repo or "/" not in repo:
        reasons.append("Repository must use owner/name format.")
    if not effective_dry_run and not github_enabled:
        reasons.append("Real issue creation requires --github-enabled.")
    if not effective_dry_run:
        if selected_autonomy_profile != LIVE_AUTONOMY_PROFILE:
            reasons.append(f"Real issue creation requires autonomy_profile={LIVE_AUTONOMY_PROFILE}.")
        if not _github_issue_sync_capability_enabled(autonomy_payload):
            reasons.append("Selected autonomy profile does not enable github_issue_sync.")
        if autonomy_payload.get("blocked") is True or autonomy_payload.get("machine_gates_passed") is not True:
            reasons.append("Autonomy profile inspection did not pass required machine gates.")
        if gate_payload.get("passed") is not True or gate_payload.get("blocked") is True:
            reasons.append("GitHub issue creation real-run machine gate did not pass.")
            reasons.extend(_list(gate_payload.get("blocked_reasons")))
    elif gate_payload.get("passed") is not True or gate_payload.get("blocked") is True:
        reasons.append("Dry-run read-only machine gate did not pass.")
        reasons.extend(_list(gate_payload.get("blocked_reasons")))
    return _dedupe(reasons)


def _github_issue_sync_capability_enabled(autonomy_payload: dict[str, Any]) -> bool:
    selected = autonomy_payload.get("selected_profile")
    controls = selected.get("capability_controls", []) if isinstance(selected, dict) else []
    if not isinstance(controls, list):
        return False
    for control in controls:
        if isinstance(control, dict) and control.get("capability_id") == "github_issue_sync":
            return _text(control.get("status")) == "enabled"
    return False


def _registry_duplicate(registry_payload: dict[str, Any]) -> bool:
    for record in _dicts(registry_payload.get("records")):
        if _int(record.get("issue_number")) > 0 or _text(record.get("issue_url")):
            return True
    return False


def _registry_summary(registry_payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "record_type": _text(registry_payload.get("record_type")),
        "status": _text(registry_payload.get("status")),
        "blocked": bool(registry_payload.get("blocked")),
        "blocked_reasons": _list(registry_payload.get("blocked_reasons")),
        "matched_record_count": _int(registry_payload.get("matched_record_count")),
        "registry_path": _text(registry_payload.get("registry_path")),
    }


def _payload(result: dict[str, Any]) -> dict[str, Any]:
    payload = result.get("payload", {}) if isinstance(result, dict) else {}
    return payload if isinstance(payload, dict) else {}


def _item_plan(plan_payload: dict[str, Any], item_id: str) -> dict[str, Any]:
    for entry in plan_payload.get("issue_sync_items", []):
        if isinstance(entry, dict) and _text(entry.get("item_id")) == item_id:
            return entry
    return {}


def _source_plan_summary(plan_payload: dict[str, Any], item_plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "record_type": _text(plan_payload.get("record_type")),
        "status": _text(plan_payload.get("status")),
        "machine_gates_passed": bool(plan_payload.get("machine_gates_passed")),
        "operation_counts": plan_payload.get("operation_counts", {}),
        "item_recommendations": item_plan.get("recommendations", []),
    }


def _autonomy_summary(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "record_type": _text(payload.get("record_type")),
        "status": _text(payload.get("status")),
        "blocked": bool(payload.get("blocked")),
        "blocked_reasons": _list(payload.get("blocked_reasons")),
        "machine_gates_passed": bool(payload.get("machine_gates_passed")),
        "autonomy_profile": _text(payload.get("autonomy_profile")),
        "github_issue_sync_enabled": _github_issue_sync_capability_enabled(payload),
    }


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


def _load_queue(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"ok": False, "queue": {}, "warnings": [], "blocked_reasons": [f"Project queue not found: {path}"]}
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"ok": False, "queue": {}, "warnings": [], "blocked_reasons": [f"Project queue could not be read as JSON: {exc}"]}
    if not isinstance(raw, dict):
        return {"ok": False, "queue": {}, "warnings": [], "blocked_reasons": ["Project queue JSON must decode to an object."]}
    return {"ok": True, "queue": raw, "warnings": [], "blocked_reasons": []}


def _find_item(queue: dict[str, Any], item_id: str) -> dict[str, Any]:
    items = queue.get("work_items", []) if isinstance(queue, dict) else []
    if not isinstance(items, list):
        return {}
    for item in items:
        if isinstance(item, dict) and _text(item.get("item_id")) == item_id:
            return item
    return {}


def _status(*, blocked: bool, dry_run: bool, issue_created: bool) -> str:
    if blocked:
        return "blocked"
    if dry_run:
        return "dry_run_ready"
    if issue_created:
        return "issue_created"
    return "not_executed"


def _next_safe_action(*, blocked: bool, dry_run: bool, issue_created: bool) -> str:
    if blocked:
        return "Resolve blocked reasons before any live GitHub issue creation attempt."
    if dry_run:
        return "Review the issue draft, local registry lookup, autonomy profile, and machine gates; real creation requires --github-enabled with autonomy_profile=github_issue_sync_enabled."
    if issue_created:
        return "Review the created GitHub issue and local registry record; continue only with separate explicit gated status-comment or PR-summary commands."
    return "No GitHub follow-up was performed."


def _summarize_issue(value: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    keys = ("id", "number", "state", "title", "html_url", "url", "created_at", "updated_at")
    return {key: value[key] for key in keys if key in value}


def _issue_number(value: dict[str, Any]) -> int | None:
    number = _int(value.get("number"))
    if number:
        return number
    url = _issue_url(value)
    match = re.search(r"/issues/(\d+)(?:\D*)?$", url)
    return int(match.group(1)) if match else None


def _issue_url(value: dict[str, Any]) -> str:
    return _text(value.get("html_url") or value.get("url"))


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
        blocked["issue_creation_allowed"] = False
        blocked["issue_created"] = False
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


def _normalize_repo(config: AppConfig, repo: str | None) -> str:
    raw = _text(repo)
    if raw:
        return raw
    return f"{config.github_owner}/{config.github_repo}"


def _resolve(repo_root: Path, value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


def _idempotency_key(*, project_id: str, item_id: str, repository: str) -> str:
    return "github-issue-real-run:" + ":".join([_slug(project_id), _slug(item_id), _slug(repository)])


def _safe_id(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in _text(value).lower())
    return cleaned.strip("-") or "github-issue-real-run"


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", _text(value).lower()).strip("-") or "unknown"


def _stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")


def _text(value: Any) -> str:
    return str(value or "").strip()


def _dicts(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [entry for entry in value if isinstance(entry, dict)]
    return []


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
