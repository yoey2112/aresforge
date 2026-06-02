from __future__ import annotations

from datetime import UTC, datetime
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.github_issue_status_comment_sync import (
    DEFAULT_AUTONOMY_PROFILE,
    LIVE_AUTONOMY_PROFILE,
    STATUS_COMMENT_MARKER,
    GhCliGitHubIssueStatusCommentClient,
    GitHubIssueStatusCommentClient,
    _artifact_paths,
    _autonomy_summary,
    _gate_payload,
    _gate_summary,
    _github_issue_sync_capability_enabled,
    _item_plan,
    _load_queue,
    _normalize_repo,
    _payload,
    _run_summary,
    _source_plan_summary,
    _status_comment_body,
    _validation_evidence,
)
from aresforge.operator.github_issue_sync_plan import plan_github_issue_sync
from aresforge.operator.github_link_registry import inspect_github_link_registry, record_github_link
from aresforge.operator.local_project_queue import resolve_project_queue_path
from aresforge.operator.operator_autonomy_configuration_profile import inspect_autonomy_profile
from aresforge.operator.orchestration_run_monitor import inspect_orchestration_run_monitor

COMMAND_NAME = "sync-github-status-comment-durable"
RECORD_TYPE = "github_status_comment_durable_sync_v1"
DEFAULT_PROJECT_ID = "aresforge"
DEFAULT_ITEM_ID = "m173-github-status-comment-durable-sync"
SAFE_QUEUE_STATUSES: frozenset[str] = frozenset({"proposed", "ready", "in_progress", "done"})

_BOUNDARY_CONFIRMATIONS: tuple[str, ...] = (
    "Dry-run is the default behavior and performs no GitHub mutation.",
    "Durable live status comment sync requires --github-enabled, a non-dry-run request, github_issue_sync_enabled autonomy profile, linked issue metadata, safe queue item status, and a passing github_sync machine gate.",
    "Only one managed status comment per linked issue is created or updated per command invocation.",
    "Successful live sync stores the managed comment_id in the local GitHub link registry for idempotent future updates.",
    "No queue mutation, Codex execution, model execution, source patch application, PR merge, protected branch update, force push, auto-merge, release, workflow mutation, issue closure, retry, resume, or next-item execution is performed.",
)


def sync_github_status_comment_durable(
    config: AppConfig,
    *,
    item_id: str = DEFAULT_ITEM_ID,
    project_id: str = DEFAULT_PROJECT_ID,
    queue_path: str | Path | None = None,
    registry_path: str | Path | None = None,
    run_id: str | None = None,
    dry_run: bool = True,
    github_enabled: bool = False,
    autonomy_profile: str = DEFAULT_AUTONOMY_PROFILE,
    repo: str | None = None,
    issue_number: int | None = None,
    output: str | Path | None = None,
    force: bool = False,
    output_format: str = "json",
    github_client: GitHubIssueStatusCommentClient | None = None,
) -> dict[str, Any]:
    fmt = _text(output_format).lower() or "json"
    if fmt != "json":
        return _error("invalid_format", {"format": output_format, "supported_formats": ["json"]})

    normalized_item_id = _text(item_id) or DEFAULT_ITEM_ID
    normalized_project_id = _text(project_id) or DEFAULT_PROJECT_ID
    normalized_repo = _normalize_repo(config, repo)
    selected_autonomy_profile = _text(autonomy_profile) or DEFAULT_AUTONOMY_PROFILE
    effective_dry_run = bool(dry_run) or not bool(github_enabled)
    generated_at = _now_iso()
    idempotency_key = _idempotency_key(project_id=normalized_project_id, item_id=normalized_item_id, repository=normalized_repo)

    queue_path_resolved = resolve_project_queue_path(config.repo_root, queue_path)
    queue_result = _load_queue(queue_path_resolved)
    queue = queue_result.get("queue") if queue_result.get("ok") else {}
    item = _find_item(queue, normalized_item_id)
    item_project_id = _text(item.get("project_id")) or normalized_project_id

    plan_payload = _payload(plan_github_issue_sync(config, project_id=item_project_id, item_id=normalized_item_id, queue_path=queue_path, output_format="json"))
    item_plan = _item_plan(plan_payload, normalized_item_id)
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
    registry_record = _first_record(registry_payload)
    effective_issue_number = _int(issue_number) or _int(registry_record.get("issue_number")) or _int(linked_issue.get("issue_number"))
    effective_issue_url = _text(registry_record.get("issue_url")) or _text(linked_issue.get("issue_url"))
    registry_comment_id = _text(registry_record.get("comment_id"))

    monitor_payload = _payload(
        inspect_orchestration_run_monitor(
            config,
            project_id=item_project_id,
            item_id=normalized_item_id,
            run_id=run_id,
            queue_path=queue_path,
            output_format="json",
        )
    )
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
    comment_body = _status_comment_body(
        item=item,
        item_plan=item_plan,
        monitor_payload=monitor_payload,
        generated_at=generated_at,
        machine_gate_status="pending",
    )
    preflight_path: Path | None = None
    if not effective_dry_run and github_enabled:
        preflight_path = _write_preflight_record(
            config=config,
            item_id=normalized_item_id,
            project_id=item_project_id,
            repository=normalized_repo,
            issue_number=effective_issue_number,
            comment_body=comment_body,
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
    comment_body = _status_comment_body(
        item=item,
        item_plan=item_plan,
        monitor_payload=monitor_payload,
        generated_at=generated_at,
        machine_gate_status="passed" if gate_summary.get("passed") else "blocked",
    )

    blocked_reasons = _blocked_reasons(
        queue_result=queue_result,
        item=item,
        item_plan=item_plan,
        plan_payload=plan_payload,
        registry_payload=registry_payload,
        effective_issue_number=effective_issue_number,
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
            *_list(monitor_payload.get("warnings")),
            *_list(autonomy_payload.get("warnings")),
            *_list(gate_payload.get("warnings")),
        ]
    )

    github_execution_performed = False
    status_comment_synced = False
    registry_mutation_performed = False
    operation = "dry_run" if effective_dry_run else "blocked"
    existing_comment: dict[str, Any] = {}
    synced_comment: dict[str, Any] = {}
    local_registry_record: dict[str, Any] = {}
    operation_error = ""

    if not blocked_reasons and not effective_dry_run:
        client = github_client or GhCliGitHubIssueStatusCommentClient()
        try:
            if registry_comment_id:
                synced_comment = client.update_comment(repo=normalized_repo, comment_id=registry_comment_id, body=comment_body)
                operation = "update_by_registry_comment_id"
            else:
                existing = client.find_status_comment(repo=normalized_repo, issue_number=effective_issue_number, marker=STATUS_COMMENT_MARKER)
                existing_comment = existing or {}
                if existing:
                    synced_comment = client.update_comment(repo=normalized_repo, comment_id=existing.get("id"), body=comment_body)
                    operation = "update_by_marker"
                else:
                    synced_comment = client.create_comment(repo=normalized_repo, issue_number=effective_issue_number, body=comment_body)
                    operation = "create"
            github_execution_performed = True
            status_comment_synced = True
            comment_id = _comment_id(synced_comment, fallback=registry_comment_id or existing_comment.get("id"))
            comment_url = _text(synced_comment.get("html_url") or synced_comment.get("url") or existing_comment.get("html_url"))
            registry_result = record_github_link(
                config,
                project_id=item_project_id,
                item_id=normalized_item_id,
                registry_path=registry_path,
                queue_item_id=normalized_item_id,
                repository=normalized_repo,
                issue_number=effective_issue_number,
                issue_url=effective_issue_url,
                comment_id=comment_id,
                comment_url=comment_url,
                sync_status="status_comment_synced",
                last_sync_result=f"{COMMAND_NAME} {operation}.",
                linked_by="aresforge-status-comment-durable-sync",
                link_source=COMMAND_NAME,
                output_format="json",
            )
            registry_payload_after = _payload(registry_result)
            local_registry_record = registry_payload_after.get("link_record", {})
            registry_mutation_performed = bool(registry_payload_after.get("mutation_performed"))
        except (RuntimeError, OSError, subprocess.SubprocessError) as exc:
            operation_error = str(exc)
            blocked_reasons.append(f"Durable GitHub status comment sync failed: {exc}")

    blocked = bool(blocked_reasons)
    payload: dict[str, Any] = {
        "record_type": RECORD_TYPE,
        "artifact_type": RECORD_TYPE,
        "generated": True,
        "generated_at": generated_at,
        "project_id": item_project_id,
        "item_id": normalized_item_id,
        "repository": normalized_repo,
        "repo": normalized_repo,
        "issue_number": effective_issue_number or None,
        "issue_url": effective_issue_url,
        "pr_number": registry_record.get("pr_number"),
        "pr_url": _text(registry_record.get("pr_url")),
        "sync_status": "blocked" if blocked else ("dry_run_ready" if effective_dry_run else "status_comment_synced"),
        "status": "blocked" if blocked else ("dry_run_ready" if effective_dry_run else "status_comment_synced"),
        "blocked": blocked,
        "blocked_reasons": _dedupe(blocked_reasons),
        "warnings": warnings,
        "machine_gates_checked": [gate_summary],
        "machine_gates_passed": bool(gate_summary.get("passed")) and not blocked,
        "autonomy_profile": selected_autonomy_profile,
        "dry_run": bool(effective_dry_run),
        "github_enabled": bool(github_enabled),
        "github_execution_performed": bool(github_execution_performed and not blocked),
        "mutation_performed": bool(status_comment_synced and not blocked),
        "status_comment_mutation_performed": bool(status_comment_synced and not blocked),
        "registry_mutation_performed": bool(registry_mutation_performed and not blocked),
        "queue_mutation_performed": False,
        "codex_execution_performed": False,
        "model_execution_performed": False,
        "patch_application_performed": False,
        "idempotency_key": idempotency_key,
        "recovery_available": True,
        "local_only": not bool(github_execution_performed and not blocked),
        "next_safe_action": _next_safe_action(blocked=blocked, dry_run=effective_dry_run, synced=status_comment_synced),
        "artifacts_created": [str(preflight_path)] if preflight_path else [],
        "github_preflight_record_path": str(preflight_path) if preflight_path else "",
        "queue_path": str(queue_path_resolved),
        "registry_path": _text(registry_payload.get("registry_path")),
        "queue_item_found": bool(item),
        "queue_status": _text(item.get("status")),
        "queue_summary": _queue_summary(item),
        "orchestration_run_summary": _run_summary(monitor_payload),
        "validation_evidence": _validation_evidence(item),
        "artifact_paths": _artifact_paths(item, monitor_payload),
        "machine_gate_status": gate_summary,
        "linked_issue": linked_issue or {"linked": False, "issue_number": None, "issue_url": "", "metadata_source": ""},
        "registry_lookup_summary": _registry_summary(registry_payload, registry_record),
        "status_comment_marker": STATUS_COMMENT_MARKER,
        "status_comment_body": comment_body,
        "status_comment_sync_allowed": not blocked and not effective_dry_run,
        "status_comment_synced": bool(status_comment_synced and not blocked),
        "status_comment_operation": operation if status_comment_synced and not blocked else ("dry_run" if effective_dry_run else "blocked"),
        "managed_comment_id": _comment_id(synced_comment, fallback=registry_comment_id) if status_comment_synced and not blocked else registry_comment_id,
        "existing_status_comment": _summarize_comment(existing_comment),
        "synced_status_comment": _summarize_comment(synced_comment) if status_comment_synced and not blocked else {},
        "local_registry_record": local_registry_record,
        "operation_error": operation_error,
        "autonomy_profile_summary": _autonomy_summary(autonomy_payload),
        "source_plan_summary": _source_plan_summary(plan_payload, item_plan),
        "github_mutation_scope": "single_issue_managed_status_comment_create_or_update",
        "github_operations_blocked": [
            "merge_pull_request",
            "force_push",
            "update_protected_branch",
            "enable_auto_merge",
            "create_release",
            "modify_github_workflow",
            "close_issue",
            "bulk_comment_sync",
            "source_code_patch",
        ],
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
        "completed_at": _now_iso(),
    }
    return _emit_or_write(config=config, payload=payload, output=output, force=force)


def _blocked_reasons(
    *,
    queue_result: dict[str, Any],
    item: dict[str, Any],
    item_plan: dict[str, Any],
    plan_payload: dict[str, Any],
    registry_payload: dict[str, Any],
    effective_issue_number: int,
    github_enabled: bool,
    effective_dry_run: bool,
    selected_autonomy_profile: str,
    autonomy_payload: dict[str, Any],
    gate_payload: dict[str, Any],
    repo: str,
) -> list[str]:
    reasons = [*queue_result.get("blocked_reasons", [])]
    if not queue_result.get("ok"):
        reasons.append("Local queue must be readable before durable status comment sync can be considered.")
    if not item:
        reasons.append("Queue item must exist before durable status comment sync can be considered.")
    status = _text(item.get("status"))
    if item and status not in SAFE_QUEUE_STATUSES:
        reasons.append(f"Queue item status is not safe for durable status comment sync: {status or 'missing'}.")
    if _list(item.get("blocked_by")):
        reasons.append("Queue item has blocked_by entries.")
    if not item_plan:
        reasons.append("Queue item was not present in the GitHub issue sync plan.")
    if bool(item_plan.get("blocked")):
        reasons.extend(_list(item_plan.get("blocked_reasons")))
    if bool(plan_payload.get("blocked")):
        reasons.extend(_list(plan_payload.get("blocked_reasons")))
    if bool(registry_payload.get("blocked")):
        reasons.append("GitHub link registry lookup is blocked.")
        reasons.extend(_list(registry_payload.get("blocked_reasons")))
    if not repo or "/" not in repo:
        reasons.append("Repository must use owner/name format.")
    if not effective_dry_run and not github_enabled:
        reasons.append("Live durable status comment sync requires --github-enabled.")
    if not effective_dry_run:
        if effective_issue_number <= 0:
            reasons.append("Live durable status comment sync requires linked GitHub issue metadata, a registry issue link, or --issue-number.")
        if selected_autonomy_profile != LIVE_AUTONOMY_PROFILE:
            reasons.append(f"Live durable status comment sync requires autonomy_profile={LIVE_AUTONOMY_PROFILE}.")
        if not _github_issue_sync_capability_enabled(autonomy_payload):
            reasons.append("Selected autonomy profile does not enable github_issue_sync.")
        if autonomy_payload.get("blocked") is True or autonomy_payload.get("machine_gates_passed") is not True:
            reasons.append("Autonomy profile inspection did not pass required machine gates.")
        if gate_payload.get("passed") is not True or gate_payload.get("blocked") is True:
            reasons.append("Durable GitHub status comment sync machine gate did not pass.")
            reasons.extend(_list(gate_payload.get("blocked_reasons")))
    elif gate_payload.get("passed") is not True or gate_payload.get("blocked") is True:
        reasons.append("Dry-run read-only machine gate did not pass.")
        reasons.extend(_list(gate_payload.get("blocked_reasons")))
    return _dedupe(reasons)


def _write_preflight_record(
    *,
    config: AppConfig,
    item_id: str,
    project_id: str,
    repository: str,
    issue_number: int,
    comment_body: str,
    autonomy_profile: str,
    idempotency_key: str,
) -> Path:
    path = config.artifact_root / "github_status_comment_durable_sync" / "gates" / f"{_stamp()}-{_slug(item_id)}.json"
    payload = {
        "artifact_type": "github_status_comment_durable_sync_preflight_v1",
        "execution_record_type": "github_status_comment_durable_sync_preflight_v1",
        "project_id": project_id,
        "item_id": item_id,
        "repository": repository,
        "issue_number": issue_number,
        "status_comment_marker": STATUS_COMMENT_MARKER,
        "comment_body_sha_hint": str(len(comment_body)),
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
        "validation_commands": ["python -m pytest tests/test_github_status_comment_durable_sync.py"],
        "tests_reported": ["python -m pytest tests/test_github_status_comment_durable_sync.py -> runnable"],
        "capabilities_used": ["read_local_queue", "read_local_run_monitor", "read_local_issue_sync_plan", "read_local_github_link_registry"],
        "created_at": _now_iso(),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def _first_record(registry_payload: dict[str, Any]) -> dict[str, Any]:
    records = registry_payload.get("records")
    if isinstance(records, list) and records and isinstance(records[0], dict):
        return records[0]
    return {}


def _registry_summary(registry_payload: dict[str, Any], registry_record: dict[str, Any]) -> dict[str, Any]:
    return {
        "record_type": _text(registry_payload.get("record_type")),
        "status": _text(registry_payload.get("status")),
        "blocked": bool(registry_payload.get("blocked")),
        "blocked_reasons": _list(registry_payload.get("blocked_reasons")),
        "matched_record_count": _int(registry_payload.get("matched_record_count")),
        "registry_path": _text(registry_payload.get("registry_path")),
        "comment_id": _text(registry_record.get("comment_id")),
        "issue_number": _int(registry_record.get("issue_number")) or None,
    }


def _queue_summary(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": _text(item.get("status")),
        "priority": _text(item.get("priority")),
        "item_type": _text(item.get("item_type")),
        "dependencies": _list(item.get("dependencies")) + _list(item.get("depends_on")),
        "blocked_by": _list(item.get("blocked_by")),
    }


def _next_safe_action(*, blocked: bool, dry_run: bool, synced: bool) -> str:
    if blocked:
        return "Resolve blocked reasons before any durable GitHub status comment sync attempt."
    if dry_run:
        return "Review the generated status comment and registry lookup; live sync requires --github-enabled with autonomy_profile=github_issue_sync_enabled."
    if synced:
        return "Review the synced GitHub status comment and durable registry comment_id before any separate gated follow-up."
    return "No GitHub follow-up was performed."


def _summarize_comment(value: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    keys = ("id", "node_id", "html_url", "url", "created_at", "updated_at")
    return {key: value[key] for key in keys if key in value}


def _comment_id(value: dict[str, Any], *, fallback: Any = "") -> str:
    return _text(value.get("id") or fallback)


def _emit_or_write(*, config: AppConfig, payload: dict[str, Any], output: str | Path | None, force: bool) -> dict[str, Any]:
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
        blocked["blocked_reasons"] = _dedupe([*_list(blocked.get("blocked_reasons")), "Output file already exists. Re-run with --force to overwrite."])
        blocked["status_comment_sync_allowed"] = False
        blocked["status_comment_synced"] = False
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


def _find_item(queue: dict[str, Any], item_id: str) -> dict[str, Any]:
    items = queue.get("work_items", []) if isinstance(queue, dict) else []
    if not isinstance(items, list):
        return {}
    for item in items:
        if isinstance(item, dict) and _text(item.get("item_id")) == item_id:
            return item
    return {}


def _idempotency_key(*, project_id: str, item_id: str, repository: str) -> str:
    return "github-status-comment-durable:" + ":".join([_slug(project_id), _slug(item_id), _slug(repository)])


def _resolve(repo_root: Path, value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", _text(value).lower()).strip("-") or "unknown"


def _stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")


def _text(value: Any) -> str:
    return str(value or "").strip()


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
