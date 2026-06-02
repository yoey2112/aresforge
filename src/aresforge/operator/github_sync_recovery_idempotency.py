from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import re
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.github_link_registry import inspect_github_link_registry
from aresforge.operator.local_project_queue import resolve_project_queue_path
from aresforge.operator.machine_safety_gate_engine import evaluate_machine_safety_gates

COMMAND_NAME = "inspect-github-sync-recovery"
RECORD_TYPE = "github_sync_recovery_idempotency_v1"
ITEM_RECORD_TYPE = "github_sync_recovery_item_v1"
DEFAULT_PROJECT_ID = "aresforge"
DEFAULT_ITEM_ID = "m179-github-sync-recovery-and-idempotency"

_OPERATIONS: tuple[dict[str, str], ...] = (
    {
        "operation_type": "issue_creation",
        "command": "create-github-issue-real-run-gate",
        "artifact_dir": "github_issue_creation_real_run_gate",
    },
    {
        "operation_type": "status_comment_sync",
        "command": "sync-github-status-comment-durable",
        "artifact_dir": "github_status_comment_durable_sync",
    },
    {
        "operation_type": "issue_closure",
        "command": "gate-github-issue-closure",
        "artifact_dir": "github_issue_closure_safe_execution_gate",
    },
    {
        "operation_type": "pr_draft_creation",
        "command": "create-pr-draft-gate",
        "artifact_dir": "pr_draft_creation_gate",
    },
    {
        "operation_type": "pr_evidence_comment_sync",
        "command": "sync-pr-evidence-comment",
        "artifact_dir": "pr_evidence_comment_sync",
    },
)

_BOUNDARY_CONFIRMATIONS: tuple[str, ...] = (
    "GitHub sync recovery inspection is read-only and local-only.",
    "Registry records are treated as durable completion anchors for idempotent no-op decisions.",
    "Preflight gate artifacts without durable registry completion are treated as partial attempts that need operator review.",
    "Resume and repair plans are recommendations only and do not execute GitHub mutations.",
    "No issue creation, comment creation/update, issue closure, PR creation/update/merge, auto-merge, force push, protected branch update, release, workflow mutation, source patch application, queue mutation, Codex execution, model execution, validation command execution, retry, resume, or next-item execution is performed.",
)


def inspect_github_sync_recovery(
    config: AppConfig,
    *,
    project_id: str = DEFAULT_PROJECT_ID,
    item_id: str = DEFAULT_ITEM_ID,
    queue_path: str | Path | None = None,
    registry_path: str | Path | None = None,
    repo: str | None = None,
    output_format: str = "json",
) -> dict[str, Any]:
    fmt = _text(output_format).lower() or "json"
    if fmt != "json":
        return _error("invalid_format", {"format": output_format, "supported_formats": ["json"]})

    normalized_project_id = _text(project_id) or DEFAULT_PROJECT_ID
    normalized_item_id = _text(item_id) or DEFAULT_ITEM_ID
    repository = _normalize_repo(config, repo)
    generated_at = _now_iso()
    queue_path_resolved = resolve_project_queue_path(config.repo_root, queue_path)
    queue_result = _load_queue(queue_path_resolved)
    queue = queue_result.get("queue") if queue_result.get("ok") else {}
    queue_items = [
        item
        for item in _dicts(queue.get("work_items"))
        if (_text(item.get("project_id")) or normalized_project_id) == normalized_project_id
    ]

    registry_payload = _payload(
        inspect_github_link_registry(
            config,
            project_id=normalized_project_id,
            item_id=normalized_item_id,
            registry_path=registry_path,
            repository=repository,
            output_format="json",
        )
    )
    registry_records = _dicts(registry_payload.get("records"))
    preflight_records = _load_preflight_records(config)
    gate_payload = _payload(
        evaluate_machine_safety_gates(
            config,
            item_id=normalized_item_id,
            gate_profile="read_only_agent",
            queue_path=queue_path,
            output_format="json",
        )
    )
    gate_summary = _gate_summary(gate_payload)

    recovery_items = [
        _recovery_item(
            item=item,
            project_id=normalized_project_id,
            repository=repository,
            registry_records=registry_records,
            preflight_records=preflight_records,
        )
        for item in queue_items
    ]
    operation_counts = _operation_counts(recovery_items)
    blocked_reasons = _dedupe(
        [
            *queue_result.get("blocked_reasons", []),
            *_list(registry_payload.get("blocked_reasons")),
            *_list(gate_payload.get("blocked_reasons")),
        ]
    )
    if gate_payload.get("passed") is not True or gate_payload.get("blocked") is True:
        blocked_reasons.append("Read-only GitHub sync recovery machine gate did not pass.")
    blocked = bool(blocked_reasons)
    warnings = _dedupe(
        [
            *queue_result.get("warnings", []),
            *_list(registry_payload.get("warnings")),
            *_list(gate_payload.get("warnings")),
            *_preflight_warnings(preflight_records),
        ]
    )

    payload: dict[str, Any] = {
        "record_type": RECORD_TYPE,
        "artifact_type": RECORD_TYPE,
        "generated": True,
        "generated_at": generated_at,
        "project_id": normalized_project_id,
        "item_id": normalized_item_id,
        "repository": repository,
        "issue_number": None,
        "issue_url": "",
        "pr_number": None,
        "pr_url": "",
        "sync_status": "blocked" if blocked else "recovery_inspected",
        "status": "blocked" if blocked else "recovery_inspected",
        "blocked": blocked,
        "blocked_reasons": blocked_reasons,
        "warnings": warnings,
        "machine_gates_checked": [gate_summary],
        "machine_gates_passed": bool(gate_summary.get("passed")) and not blocked,
        "autonomy_profile": "github_sync_dry_run",
        "dry_run": True,
        "github_enabled": False,
        "github_execution_performed": False,
        "mutation_performed": False,
        "github_issue_mutation_performed": False,
        "github_comment_mutation_performed": False,
        "github_pr_mutation_performed": False,
        "registry_mutation_performed": False,
        "queue_mutation_performed": False,
        "codex_execution_performed": False,
        "model_execution_performed": False,
        "patch_application_performed": False,
        "validation_command_execution_performed": False,
        "idempotency_key": _inspect_idempotency_key(project_id=normalized_project_id, repository=repository),
        "recovery_available": True,
        "local_only": True,
        "next_safe_action": _next_safe_action(blocked=blocked, operation_counts=operation_counts),
        "queue_path": str(queue_path_resolved),
        "registry_path": _text(registry_payload.get("registry_path")),
        "queue_item_count": len(queue_items),
        "registry_record_count": len(registry_records),
        "preflight_record_count": len(preflight_records),
        "operation_counts": operation_counts,
        "recovery_items": recovery_items,
        "resume_plan": _resume_plan(recovery_items),
        "repair_plan": _repair_plan(recovery_items),
        "github_operations_blocked": [
            "create_issue",
            "update_issue",
            "create_comment",
            "update_comment",
            "close_issue",
            "reopen_issue",
            "create_pull_request",
            "update_pull_request",
            "merge_pull_request",
            "enable_auto_merge",
            "force_push",
            "update_protected_branch",
            "create_release",
            "modify_github_workflow",
            "source_code_patch",
        ],
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
        "completed_at": _now_iso(),
    }
    return _stdout_result(payload)


def _recovery_item(
    *,
    item: dict[str, Any],
    project_id: str,
    repository: str,
    registry_records: list[dict[str, Any]],
    preflight_records: list[dict[str, Any]],
) -> dict[str, Any]:
    queue_item_id = _text(item.get("item_id"))
    registry_record = _registry_record_for_item(registry_records, queue_item_id, repository)
    preflights = [record for record in preflight_records if _text(record.get("item_id")) == queue_item_id]
    operations = [
        _operation_record(
            operation=operation,
            item=item,
            project_id=project_id,
            repository=repository,
            registry_record=registry_record,
            preflights=preflights,
        )
        for operation in _OPERATIONS
    ]
    partial = [operation for operation in operations if operation["sync_status"] == "partial"]
    completed = [operation for operation in operations if operation["sync_status"] == "complete"]
    blocked = bool(_list(item.get("blocked_by")))
    blocked_reasons = ["Queue item has blocked_by entries."] if blocked else []
    return {
        "record_type": ITEM_RECORD_TYPE,
        "artifact_type": ITEM_RECORD_TYPE,
        "generated": True,
        "project_id": project_id,
        "item_id": queue_item_id,
        "repository": repository,
        "issue_number": _issue_number(item, registry_record),
        "issue_url": _issue_url(item, registry_record),
        "pr_number": _int_or_none(registry_record.get("pr_number")),
        "pr_url": _text(registry_record.get("pr_url")),
        "sync_status": "partial_recovery_available" if partial else ("complete_noop" if completed else "no_recovery_needed"),
        "blocked": blocked,
        "blocked_reasons": blocked_reasons,
        "warnings": _dedupe(_list(item.get("warnings")) + _partial_warnings(partial)),
        "machine_gates_checked": [],
        "machine_gates_passed": not blocked,
        "autonomy_profile": "github_sync_dry_run",
        "dry_run": True,
        "github_enabled": False,
        "github_execution_performed": False,
        "mutation_performed": False,
        "idempotency_key": _item_idempotency_key(project_id=project_id, item_id=queue_item_id, repository=repository),
        "recovery_available": bool(partial),
        "local_only": True,
        "next_safe_action": _item_next_safe_action(partial=partial, completed=completed),
        "queue_status": _text(item.get("status")),
        "registry_record_found": bool(registry_record),
        "registry_record": registry_record,
        "operation_count": len(operations),
        "partial_operation_count": len(partial),
        "completed_operation_count": len(completed),
        "operations": operations,
    }


def _operation_record(
    *,
    operation: dict[str, str],
    item: dict[str, Any],
    project_id: str,
    repository: str,
    registry_record: dict[str, Any],
    preflights: list[dict[str, Any]],
) -> dict[str, Any]:
    operation_type = operation["operation_type"]
    command = operation["command"]
    matching_preflights = [record for record in preflights if _text(record.get("source_command")) == command]
    issue_number = _issue_number(item, registry_record)
    issue_url = _issue_url(item, registry_record)
    pr_number = _int_or_none(registry_record.get("pr_number"))
    pr_url = _text(registry_record.get("pr_url"))
    completed = _operation_completed(operation_type, item=item, registry_record=registry_record)
    partial = bool(matching_preflights) and not completed
    sync_status = "complete" if completed else ("partial" if partial else "not_started")
    idempotency_key = _operation_idempotency_key(
        operation_type=operation_type,
        project_id=project_id,
        item_id=_text(item.get("item_id")),
        repository=repository,
        issue_number=issue_number,
        pr_number=pr_number,
    )
    return {
        "record_type": "github_sync_recovery_operation_v1",
        "artifact_type": "github_sync_recovery_operation_v1",
        "generated": True,
        "project_id": project_id,
        "item_id": _text(item.get("item_id")),
        "repository": repository,
        "issue_number": issue_number,
        "issue_url": issue_url,
        "pr_number": pr_number,
        "pr_url": pr_url,
        "operation_type": operation_type,
        "source_command": command,
        "sync_status": sync_status,
        "blocked": False,
        "blocked_reasons": [],
        "warnings": _operation_warnings(operation_type, registry_record, partial, completed),
        "machine_gates_checked": [],
        "machine_gates_passed": True,
        "autonomy_profile": "github_sync_dry_run",
        "dry_run": True,
        "github_enabled": False,
        "github_execution_performed": False,
        "mutation_performed": False,
        "idempotency_key": idempotency_key,
        "registry_completion_proves_noop": completed,
        "recovery_available": partial,
        "local_only": True,
        "next_safe_action": _operation_next_safe_action(
            operation_type=operation_type,
            command=command,
            completed=completed,
            partial=partial,
            issue_number=issue_number,
            pr_number=pr_number,
        ),
        "preflight_artifacts": [record["path"] for record in matching_preflights],
        "latest_preflight_artifact": matching_preflights[-1]["path"] if matching_preflights else "",
        "preflight_count": len(matching_preflights),
        "registry_record_found": bool(registry_record),
        "registry_sync_status": _text(registry_record.get("sync_status")),
        "registry_link_source": _text(registry_record.get("link_source")),
        "registry_last_sync_result": _text(registry_record.get("last_sync_result")),
    }


def _operation_completed(operation_type: str, *, item: dict[str, Any], registry_record: dict[str, Any]) -> bool:
    issue_number = _issue_number(item, registry_record)
    pr_number = _int_or_none(registry_record.get("pr_number"))
    comment_id = _text(registry_record.get("comment_id"))
    link_source = _text(registry_record.get("link_source"))
    last_sync = _text(registry_record.get("last_sync_result")).lower()
    if operation_type == "issue_creation":
        return bool(issue_number)
    if operation_type == "status_comment_sync":
        return bool(issue_number and comment_id and link_source == "sync-github-status-comment-durable")
    if operation_type == "issue_closure":
        issue_state = _text((item.get("github_issue") if isinstance(item.get("github_issue"), dict) else {}).get("state")).lower()
        return issue_state == "closed" or "closed github issue" in last_sync
    if operation_type == "pr_draft_creation":
        return bool(pr_number)
    if operation_type == "pr_evidence_comment_sync":
        return bool(pr_number and comment_id and link_source == "sync-pr-evidence-comment")
    return False


def _load_preflight_records(config: AppConfig) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for operation in _OPERATIONS:
        root = config.artifact_root / operation["artifact_dir"] / "gates"
        if not root.exists():
            continue
        for path in sorted(root.glob("*.json")):
            try:
                raw = json.loads(path.read_text(encoding="utf-8-sig"))
            except (OSError, json.JSONDecodeError):
                records.append(
                    {
                        "path": str(path),
                        "source_command": operation["command"],
                        "item_id": "",
                        "blocked": True,
                        "blocked_reasons": ["Preflight artifact could not be read as JSON."],
                    }
                )
                continue
            if isinstance(raw, dict):
                records.append(
                    {
                        **raw,
                        "path": str(path),
                        "source_command": operation["command"],
                        "operation_type": operation["operation_type"],
                    }
                )
    return records


def _registry_record_for_item(records: list[dict[str, Any]], item_id: str, repository: str) -> dict[str, Any]:
    candidates = [
        record
        for record in records
        if _text(record.get("queue_item_id") or record.get("item_id")) == item_id
        and (not _text(record.get("repository")) or _text(record.get("repository")) == repository)
    ]
    if not candidates:
        return {}
    return sorted(candidates, key=lambda record: _text(record.get("last_sync_time")))[-1]


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


def _operation_counts(items: list[dict[str, Any]]) -> dict[str, int]:
    counts = {
        "items_inspected": len(items),
        "operations_complete_noop": 0,
        "operations_partial": 0,
        "operations_not_started": 0,
        "resume_recommended": 0,
        "repair_recommended": 0,
    }
    for item in items:
        for operation in _dicts(item.get("operations")):
            status = _text(operation.get("sync_status"))
            if status == "complete":
                counts["operations_complete_noop"] += 1
            elif status == "partial":
                counts["operations_partial"] += 1
                counts["repair_recommended"] += 1
                if _resume_allowed(operation):
                    counts["resume_recommended"] += 1
            else:
                counts["operations_not_started"] += 1
    return counts


def _resume_plan(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    plans: list[dict[str, Any]] = []
    for item in items:
        for operation in _dicts(item.get("operations")):
            if _text(operation.get("sync_status")) != "partial":
                continue
            plans.append(
                {
                    "record_type": "github_sync_recovery_resume_plan_v1",
                    "project_id": operation.get("project_id"),
                    "item_id": operation.get("item_id"),
                    "repository": operation.get("repository"),
                    "issue_number": operation.get("issue_number"),
                    "issue_url": operation.get("issue_url"),
                    "pr_number": operation.get("pr_number"),
                    "pr_url": operation.get("pr_url"),
                    "operation_type": operation.get("operation_type"),
                    "sync_status": "resume_available" if _resume_allowed(operation) else "repair_first",
                    "idempotency_key": operation.get("idempotency_key"),
                    "recovery_available": True,
                    "dry_run": True,
                    "github_enabled": False,
                    "github_execution_performed": False,
                    "mutation_performed": False,
                    "local_only": True,
                    "next_safe_action": operation.get("next_safe_action"),
                }
            )
    return plans


def _repair_plan(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    repairs: list[dict[str, Any]] = []
    for item in items:
        for operation in _dicts(item.get("operations")):
            if _text(operation.get("sync_status")) != "partial":
                continue
            repairs.append(
                {
                    "record_type": "github_sync_recovery_repair_plan_v1",
                    "project_id": operation.get("project_id"),
                    "item_id": operation.get("item_id"),
                    "repository": operation.get("repository"),
                    "issue_number": operation.get("issue_number"),
                    "issue_url": operation.get("issue_url"),
                    "pr_number": operation.get("pr_number"),
                    "pr_url": operation.get("pr_url"),
                    "operation_type": operation.get("operation_type"),
                    "sync_status": "repair_registry_or_verify_remote",
                    "idempotency_key": operation.get("idempotency_key"),
                    "recovery_available": True,
                    "dry_run": True,
                    "github_enabled": False,
                    "github_execution_performed": False,
                    "mutation_performed": False,
                    "local_only": True,
                    "next_safe_action": "Verify whether the preflighted GitHub operation completed remotely; if yes, record the durable local registry link, otherwise rerun only the matching gated command.",
                }
            )
    return repairs


def _resume_allowed(operation: dict[str, Any]) -> bool:
    operation_type = _text(operation.get("operation_type"))
    if operation_type in {"status_comment_sync"}:
        return _int_or_none(operation.get("issue_number")) is not None
    if operation_type in {"pr_evidence_comment_sync"}:
        return _int_or_none(operation.get("pr_number")) is not None
    if operation_type == "issue_closure":
        return _int_or_none(operation.get("issue_number")) is not None
    return False


def _issue_number(item: dict[str, Any], registry_record: dict[str, Any]) -> int | None:
    from_registry = _int_or_none(registry_record.get("issue_number"))
    if from_registry is not None:
        return from_registry
    github_issue = item.get("github_issue") if isinstance(item.get("github_issue"), dict) else {}
    return _int_or_none(github_issue.get("number"))


def _issue_url(item: dict[str, Any], registry_record: dict[str, Any]) -> str:
    from_registry = _text(registry_record.get("issue_url"))
    if from_registry:
        return from_registry
    github_issue = item.get("github_issue") if isinstance(item.get("github_issue"), dict) else {}
    return _text(github_issue.get("url"))


def _operation_warnings(operation_type: str, registry_record: dict[str, Any], partial: bool, completed: bool) -> list[str]:
    warnings: list[str] = []
    if completed:
        warnings.append("Durable registry or queue state proves completion; repeat mutation should be skipped.")
    if partial:
        warnings.append("Preflight evidence exists without durable completion in the local registry.")
    if operation_type in {"status_comment_sync", "pr_evidence_comment_sync"} and _text(registry_record.get("comment_id")) and not completed:
        warnings.append("A registry comment_id exists, but it is associated with a different managed comment source.")
    return warnings


def _partial_warnings(partial: list[dict[str, Any]]) -> list[str]:
    return [
        f"Partial GitHub sync operation needs review: {_text(operation.get('operation_type'))}."
        for operation in partial
    ]


def _preflight_warnings(preflight_records: list[dict[str, Any]]) -> list[str]:
    return _dedupe(
        f"Unreadable preflight artifact: {_text(record.get('path'))}."
        for record in preflight_records
        if bool(record.get("blocked"))
    )


def _operation_next_safe_action(
    *,
    operation_type: str,
    command: str,
    completed: bool,
    partial: bool,
    issue_number: int | None,
    pr_number: int | None,
) -> str:
    if completed:
        return "Skip this mutation; durable registry or queue state already proves completion."
    if partial:
        if operation_type == "issue_creation":
            return "Verify whether the issue was created remotely; record the issue link locally before any retry to avoid duplicate creation."
        if operation_type == "status_comment_sync" and issue_number:
            return f"Resume with {command} only after operator review; registry idempotency will update by known comment_id or marker when available."
        if operation_type == "issue_closure" and issue_number:
            return f"Verify current issue state, then resume with {command} only if the issue is still open and gates pass."
        if operation_type == "pr_draft_creation":
            return "Verify whether the draft PR exists remotely; record the PR link locally before any retry to avoid duplicate PR creation."
        if operation_type == "pr_evidence_comment_sync" and pr_number:
            return f"Resume with {command} only after operator review; registry idempotency will update by known comment_id or marker when available."
        return "Repair local registry evidence or verify remote state before retrying this gated operation."
    return "No resume is needed; start only through the matching dry-run-default gated command if future scope requires it."


def _item_next_safe_action(*, partial: list[dict[str, Any]], completed: list[dict[str, Any]]) -> str:
    if partial:
        return "Review repair and resume plans for partial GitHub sync operations before any separate gated command."
    if completed:
        return "Skip completed registry-backed mutations and continue with separate gated commands only for missing operations."
    return "No recovery action is needed for this item."


def _next_safe_action(*, blocked: bool, operation_counts: dict[str, int]) -> str:
    if blocked:
        return "Resolve local queue, registry, or read-only machine-gate blockers before relying on recovery plans."
    if operation_counts.get("operations_partial", 0):
        return "Review repair_plan and resume_plan; do not repeat mutations when registry completion anchors exist."
    return "No partial GitHub sync operations were detected; continue with dry-run gated sync commands only as needed."


def _gate_summary(gate_payload: dict[str, Any]) -> dict[str, Any]:
    checks = gate_payload.get("checks", [])
    failed = [
        _text(check.get("check_id"))
        for check in checks
        if isinstance(check, dict) and not bool(check.get("passed")) and not bool(check.get("warning_only"))
    ]
    return {
        "gate_profile": _text(gate_payload.get("gate_profile")) or "read_only_agent",
        "passed": bool(gate_payload.get("passed")) and not bool(gate_payload.get("blocked")),
        "blocked": bool(gate_payload.get("blocked")),
        "blocked_reasons": _list(gate_payload.get("blocked_reasons")),
        "checks_failed": failed,
    }


def _stdout_result(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "command": COMMAND_NAME,
        "ok": not bool(payload.get("blocked")),
        "local_only": True,
        "format": "json",
        "wrote_output_file": False,
        "stdout": json.dumps(payload, indent=2),
        "payload": payload,
    }


def _error(error: str, details: dict[str, Any]) -> dict[str, Any]:
    return {
        "command": COMMAND_NAME,
        "ok": False,
        "local_only": True,
        "error": error,
        "details": details,
    }


def _payload(result: dict[str, Any]) -> dict[str, Any]:
    payload = result.get("payload", {}) if isinstance(result, dict) else {}
    return payload if isinstance(payload, dict) else {}


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


def _int_or_none(value: Any) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    text = _text(value)
    return int(text) if text.isdigit() else None


def _normalize_repo(config: AppConfig, repo: str | None) -> str:
    raw = _text(repo)
    if raw:
        return raw
    return f"{config.github_owner}/{config.github_repo}"


def _inspect_idempotency_key(*, project_id: str, repository: str) -> str:
    return "github-sync-recovery:" + ":".join([_slug(project_id), _slug(repository)])


def _item_idempotency_key(*, project_id: str, item_id: str, repository: str) -> str:
    return "github-sync-recovery-item:" + ":".join([_slug(project_id), _slug(item_id), _slug(repository)])


def _operation_idempotency_key(
    *,
    operation_type: str,
    project_id: str,
    item_id: str,
    repository: str,
    issue_number: int | None,
    pr_number: int | None,
) -> str:
    target = f"issue-{issue_number}" if issue_number else "issue-unlinked"
    if pr_number:
        target += f":pr-{pr_number}"
    return "github-sync-recovery-operation:" + ":".join(
        [_slug(operation_type), _slug(project_id), _slug(item_id), _slug(repository), _slug(target)]
    )


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", _text(value).lower()).strip("-") or "unknown"


def _text(value: Any) -> str:
    return str(value or "").strip()


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
