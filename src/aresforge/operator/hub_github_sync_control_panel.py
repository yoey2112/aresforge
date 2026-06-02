from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import re
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.github_issue_closure_safe_execution_gate import gate_github_issue_closure
from aresforge.operator.github_issue_state_reconciliation import reconcile_github_issue_state
from aresforge.operator.github_issue_sync_plan import plan_github_issue_sync
from aresforge.operator.github_link_registry import inspect_github_link_registry
from aresforge.operator.github_status_comment_durable_sync import sync_github_status_comment_durable
from aresforge.operator.github_sync_recovery_idempotency import inspect_github_sync_recovery
from aresforge.operator.local_project_queue import resolve_project_queue_path
from aresforge.operator.machine_safety_gate_engine import evaluate_machine_safety_gates
from aresforge.operator.operator_autonomy_configuration_profile import inspect_autonomy_profile
from aresforge.operator.pr_draft_branch_planning_contract import plan_pr_draft_branch
from aresforge.operator.pr_evidence_comment_sync import sync_pr_evidence_comment

COMMAND_NAME = "inspect-hub-github-sync-control-panel-data"
RECORD_TYPE = "hub_github_sync_control_panel_v1"
DEFAULT_PROJECT_ID = "aresforge"
DEFAULT_ITEM_ID = "m180-hub-github-sync-control-panel"
DEFAULT_AUTONOMY_PROFILE = "github_sync_dry_run"

_BOUNDARY_CONFIRMATIONS: tuple[str, ...] = (
    "Hub GitHub Sync Control Panel is read-only and dry-run by default.",
    "The panel aggregates local registry, issue sync, comment, reconciliation, closure, PR draft, PR evidence, and recovery evidence.",
    "No unsafe default execute buttons or live GitHub mutations are exposed by this panel.",
    "Any real GitHub mutation remains in separate commands that require explicit enablement, autonomy profile allowance, and passing machine gates.",
    "No PR merge, auto-merge, force push, protected branch update, release creation, workflow mutation, automatic issue closure, source patch application, queue mutation, Codex execution, model execution, validation command execution, retry, resume, or automatic next-item execution is performed.",
)


def inspect_hub_github_sync_control_panel_data(
    config: AppConfig,
    *,
    project_id: str = DEFAULT_PROJECT_ID,
    item_id: str = DEFAULT_ITEM_ID,
    queue_path: str | Path | None = None,
    registry_path: str | Path | None = None,
    repo: str | None = None,
    autonomy_profile: str = DEFAULT_AUTONOMY_PROFILE,
    output: str | Path | None = None,
    force: bool = False,
    output_format: str = "json",
) -> dict[str, Any]:
    fmt = _text(output_format).lower() or "json"
    if fmt != "json":
        return _error("invalid_format", {"format": output_format, "supported_formats": ["json"]})

    normalized_project_id = _text(project_id) or DEFAULT_PROJECT_ID
    normalized_item_id = _text(item_id) or DEFAULT_ITEM_ID
    selected_profile = _text(autonomy_profile) or DEFAULT_AUTONOMY_PROFILE
    repository = _normalize_repo(config, repo)
    resolved_queue_path = resolve_project_queue_path(config.repo_root, queue_path)
    queue_result = _load_queue(resolved_queue_path)
    queue = queue_result.get("queue") if queue_result.get("ok") else {}
    queue_item = _find_item(queue, normalized_item_id)

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
    selected_record = _selected_registry_record(registry_records, normalized_item_id)
    issue_sync_payload = _payload(
        plan_github_issue_sync(
            config,
            project_id=normalized_project_id,
            item_id=normalized_item_id,
            queue_path=queue_path,
            output_format="json",
        )
    )
    reconciliation_payload = _payload(
        reconcile_github_issue_state(
            config,
            project_id=normalized_project_id,
            item_id=normalized_item_id,
            queue_path=queue_path,
            registry_path=registry_path,
            dry_run=True,
            github_enabled=False,
            autonomy_profile=selected_profile,
            repo=repository,
            output_format="json",
        )
    )
    status_comment_payload = _payload(
        sync_github_status_comment_durable(
            config,
            item_id=normalized_item_id,
            project_id=normalized_project_id,
            queue_path=queue_path,
            registry_path=registry_path,
            dry_run=True,
            github_enabled=False,
            autonomy_profile=selected_profile,
            repo=repository,
            output_format="json",
        )
    )
    closure_payload = _payload(
        gate_github_issue_closure(
            config,
            item_id=normalized_item_id,
            project_id=normalized_project_id,
            queue_path=queue_path,
            registry_path=registry_path,
            dry_run=True,
            github_enabled=False,
            autonomy_profile=selected_profile,
            repo=repository,
            output_format="json",
        )
    )
    pr_draft_payload = _payload(
        plan_pr_draft_branch(
            config,
            item_id=normalized_item_id,
            project_id=normalized_project_id,
            queue_path=queue_path,
            registry_path=registry_path,
            autonomy_profile=selected_profile,
            repo=repository,
            output_format="json",
        )
    )
    pr_evidence_payload = _payload(
        sync_pr_evidence_comment(
            config,
            item_id=normalized_item_id,
            project_id=normalized_project_id,
            queue_path=queue_path,
            registry_path=registry_path,
            dry_run=True,
            github_enabled=False,
            autonomy_profile=selected_profile,
            repo=repository,
            output_format="json",
        )
    )
    recovery_payload = _payload(
        inspect_github_sync_recovery(
            config,
            project_id=normalized_project_id,
            item_id=normalized_item_id,
            queue_path=queue_path,
            registry_path=registry_path,
            repo=repository,
            output_format="json",
        )
    )
    autonomy_payload = _payload(
        inspect_autonomy_profile(
            config,
            project_id=normalized_project_id,
            item_id=normalized_item_id,
            autonomy_profile=selected_profile,
            queue_path=queue_path,
            output_format="json",
        )
    )
    gates = [
        _gate_summary(
            _payload(
                evaluate_machine_safety_gates(
                    config,
                    item_id=normalized_item_id,
                    gate_profile="read_only_agent",
                    queue_path=queue_path,
                    output_format="json",
                )
            ),
            required_for_panel=True,
        ),
        _gate_summary(
            _payload(
                evaluate_machine_safety_gates(
                    config,
                    item_id=normalized_item_id,
                    gate_profile="github_sync",
                    queue_path=queue_path,
                    output_format="json",
                )
            ),
            required_for_panel=False,
        ),
    ]
    required_gates = [gate for gate in gates if bool(gate.get("required_for_panel"))]
    blocked_reasons = _dedupe(
        [
            *queue_result.get("blocked_reasons", []),
            *(reason for gate in required_gates for reason in _list(gate.get("blocked_reasons"))),
        ]
    )
    blocked = bool(blocked_reasons)
    warnings = _dedupe(
        [
            *queue_result.get("warnings", []),
            *_list(registry_payload.get("warnings")),
            *_list(issue_sync_payload.get("warnings")),
            *_list(reconciliation_payload.get("warnings")),
            *_list(status_comment_payload.get("warnings")),
            *_list(closure_payload.get("warnings")),
            *_list(pr_draft_payload.get("warnings")),
            *_list(pr_evidence_payload.get("warnings")),
            *_list(recovery_payload.get("warnings")),
            *_list(autonomy_payload.get("warnings")),
            "Panel rows are control metadata only; use separate dry-run commands before any explicitly enabled mutation.",
        ]
    )
    issue_number = _issue_number(queue_item, selected_record)
    pr_number = _int_or_none(selected_record.get("pr_number"))
    payload: dict[str, Any] = {
        "record_type": RECORD_TYPE,
        "artifact_type": RECORD_TYPE,
        "generated": True,
        "generated_at": _now_iso(),
        "project_id": normalized_project_id,
        "item_id": normalized_item_id,
        "repository": repository,
        "issue_number": issue_number,
        "issue_url": _issue_url(queue_item, selected_record),
        "pr_number": pr_number,
        "pr_url": _text(selected_record.get("pr_url")),
        "sync_status": "blocked" if blocked else "control_panel_ready",
        "status": "blocked" if blocked else "control_panel_ready",
        "blocked": blocked,
        "blocked_reasons": blocked_reasons,
        "warnings": warnings,
        "machine_gates_checked": gates,
        "machine_gates_passed": bool(required_gates) and all(bool(gate.get("passed")) for gate in required_gates) and not blocked,
        "autonomy_profile": selected_profile,
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
        "idempotency_key": _panel_idempotency_key(
            project_id=normalized_project_id,
            item_id=normalized_item_id,
            repository=repository,
        ),
        "recovery_available": bool(recovery_payload.get("recovery_available", True)),
        "local_only": True,
        "next_safe_action": _next_safe_action(blocked=blocked, recovery_payload=recovery_payload),
        "queue_path": str(resolved_queue_path),
        "queue_item": _queue_item_summary(queue_item, normalized_item_id),
        "link_registry": {
            **_source_summary(registry_payload, "link_registry"),
            "registry_path": _text(registry_payload.get("registry_path")),
            "record_count": int(registry_payload.get("record_count") or 0),
            "matched_record_count": int(registry_payload.get("matched_record_count") or 0),
            "records": [_registry_record_summary(record) for record in registry_records[:20]],
        },
        "issue_sync_plans": {
            **_source_summary(issue_sync_payload, "issue_sync_plan"),
            "operation_counts": issue_sync_payload.get("operation_counts", {}) if isinstance(issue_sync_payload.get("operation_counts"), dict) else {},
            "items": [_issue_sync_item_summary(item) for item in _dicts(issue_sync_payload.get("issue_sync_items"))[:20]],
        },
        "status_comments": _source_summary(status_comment_payload, "status_comment_sync"),
        "reconciliation": {
            **_source_summary(reconciliation_payload, "issue_state_reconciliation"),
            "operation_counts": reconciliation_payload.get("operation_counts", {}) if isinstance(reconciliation_payload.get("operation_counts"), dict) else {},
            "items": [_reconciliation_item_summary(item) for item in _dicts(reconciliation_payload.get("reconciliation_items"))[:20]],
        },
        "closure_gates": _source_summary(closure_payload, "issue_closure_gate"),
        "pr_draft_plans": _source_summary(pr_draft_payload, "pr_draft_branch_plan"),
        "pr_evidence_comments": _source_summary(pr_evidence_payload, "pr_evidence_comment_sync"),
        "recovery_actions": {
            **_source_summary(recovery_payload, "github_sync_recovery"),
            "operation_counts": recovery_payload.get("operation_counts", {}) if isinstance(recovery_payload.get("operation_counts"), dict) else {},
            "resume_plan": _dicts(recovery_payload.get("resume_plan"))[:20],
            "repair_plan": _dicts(recovery_payload.get("repair_plan"))[:20],
        },
        "safety_boundaries": _safety_boundaries(),
        "next_safe_actions": _next_safe_actions(
            project_id=normalized_project_id,
            item_id=normalized_item_id,
            repository=repository,
            issue_number=issue_number,
            pr_number=pr_number,
            recovery_payload=recovery_payload,
        ),
        "unsafe_actions_available": False,
        "github_mutation_allowed": False,
        "issue_creation_allowed": False,
        "status_comment_sync_allowed": False,
        "issue_closure_allowed": False,
        "pr_draft_creation_allowed": False,
        "pr_evidence_comment_sync_allowed": False,
        "pull_request_merge_allowed": False,
        "auto_merge_allowed": False,
        "force_push_allowed": False,
        "protected_branch_update_allowed": False,
        "release_creation_allowed": False,
        "workflow_mutation_allowed": False,
        "source_patch_application_allowed": False,
        "hub_visibility": {
            "api_endpoint": "/api/github-sync/control-panel",
            "operator_cli": "python -m aresforge inspect-hub-github-sync-control-panel-data --project-id "
            + normalized_project_id
            + " --format json",
            "local_only": True,
        },
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
        "artifacts_created": [],
    }
    return _emit_or_write(config=config, payload=payload, output=output, force=force)


def _source_summary(payload: dict[str, Any], source_id: str) -> dict[str, Any]:
    return {
        "record_type": _text(payload.get("record_type")),
        "artifact_type": _text(payload.get("artifact_type") or payload.get("record_type")),
        "source_id": source_id,
        "project_id": _text(payload.get("project_id")),
        "item_id": _text(payload.get("item_id")),
        "repository": _text(payload.get("repository")),
        "issue_number": _int_or_none(payload.get("issue_number")),
        "issue_url": _text(payload.get("issue_url")),
        "pr_number": _int_or_none(payload.get("pr_number")),
        "pr_url": _text(payload.get("pr_url")),
        "sync_status": _text(payload.get("sync_status") or payload.get("status")),
        "status": _text(payload.get("status") or payload.get("sync_status")),
        "blocked": bool(payload.get("blocked")),
        "blocked_reasons": _list(payload.get("blocked_reasons")),
        "warnings": _list(payload.get("warnings")),
        "machine_gates_checked": _dicts(payload.get("machine_gates_checked")),
        "machine_gates_passed": bool(payload.get("machine_gates_passed")),
        "autonomy_profile": _text(payload.get("autonomy_profile")),
        "dry_run": bool(payload.get("dry_run", True)),
        "github_enabled": bool(payload.get("github_enabled")),
        "github_execution_performed": bool(payload.get("github_execution_performed")),
        "mutation_performed": bool(payload.get("mutation_performed")),
        "idempotency_key": _text(payload.get("idempotency_key")),
        "recovery_available": bool(payload.get("recovery_available", True)),
        "local_only": bool(payload.get("local_only", True)),
        "next_safe_action": _text(payload.get("next_safe_action")),
    }


def _registry_record_summary(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "record_type": _text(record.get("record_type")) or "github_link_registry_record_v1",
        "project_id": _text(record.get("project_id")),
        "item_id": _text(record.get("queue_item_id") or record.get("item_id")),
        "queue_item_id": _text(record.get("queue_item_id") or record.get("item_id")),
        "repository": _text(record.get("repository")),
        "issue_number": _int_or_none(record.get("issue_number")),
        "issue_url": _text(record.get("issue_url")),
        "pr_number": _int_or_none(record.get("pr_number")),
        "pr_url": _text(record.get("pr_url")),
        "sync_status": _text(record.get("sync_status")),
        "idempotency_key": _text(record.get("idempotency_key")),
        "local_only": True,
        "next_safe_action": "Use this local registry record as idempotency evidence before any separate gated GitHub command.",
    }


def _issue_sync_item_summary(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "record_type": _text(item.get("record_type")) or "github_issue_sync_plan_item_v1",
        "project_id": _text(item.get("project_id")),
        "item_id": _text(item.get("item_id")),
        "issue_number": _int_or_none(item.get("issue_number")),
        "issue_url": _text(item.get("issue_url")),
        "sync_status": _text(item.get("sync_status")),
        "blocked": bool(item.get("blocked")),
        "blocked_reasons": _list(item.get("blocked_reasons")),
        "warnings": _list(item.get("warnings")),
        "dry_run": True,
        "github_enabled": False,
        "github_execution_performed": False,
        "mutation_performed": False,
        "local_only": True,
        "next_safe_action": _text(item.get("next_safe_action")),
    }


def _reconciliation_item_summary(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "record_type": _text(item.get("record_type")) or "github_issue_state_reconciliation_item_v1",
        "project_id": _text(item.get("project_id")),
        "item_id": _text(item.get("item_id")),
        "repository": _text(item.get("repository")),
        "issue_number": _int_or_none(item.get("issue_number")),
        "issue_url": _text(item.get("issue_url")),
        "sync_status": _text(item.get("sync_status")),
        "blocked": bool(item.get("blocked")),
        "blocked_reasons": _list(item.get("blocked_reasons")),
        "recommended_actions": _list(item.get("recommended_actions")),
        "dry_run": True,
        "github_enabled": False,
        "github_execution_performed": False,
        "mutation_performed": False,
        "local_only": True,
        "next_safe_action": _text(item.get("next_safe_action")),
    }


def _queue_item_summary(item: dict[str, Any], item_id: str) -> dict[str, Any]:
    return {
        "record_type": "hub_github_sync_control_panel_queue_item_v1",
        "project_id": _text(item.get("project_id")),
        "item_id": _text(item.get("item_id")) or item_id,
        "found": bool(item),
        "status": _text(item.get("status")),
        "title": _text(item.get("title")),
        "blocked": bool(_list(item.get("blocked_by"))),
        "blocked_reasons": [f"Blocked by {_text(blocker)}" for blocker in _list(item.get("blocked_by"))],
        "repository": "",
        "issue_number": _issue_number(item, {}),
        "issue_url": _issue_url(item, {}),
        "sync_status": "queue_item_found" if item else "queue_item_missing",
        "dry_run": True,
        "github_enabled": False,
        "github_execution_performed": False,
        "mutation_performed": False,
        "local_only": True,
        "next_safe_action": "Review queue metadata before choosing a separate gated GitHub sync command.",
    }


def _next_safe_actions(
    *,
    project_id: str,
    item_id: str,
    repository: str,
    issue_number: int | None,
    pr_number: int | None,
    recovery_payload: dict[str, Any],
) -> list[dict[str, Any]]:
    actions = [
        _action(
            "refresh_link_registry",
            "Review local link registry",
            f"python -m aresforge inspect-github-link-registry --project-id {project_id} --format json",
        ),
        _action(
            "review_issue_sync_plan",
            "Review issue sync plan",
            f"python -m aresforge plan-github-issue-sync --project-id {project_id} --format json",
        ),
        _action(
            "review_reconciliation",
            "Review issue reconciliation",
            f"python -m aresforge reconcile-github-issue-state --project-id {project_id} --dry-run --format json",
        ),
        _action(
            "review_recovery",
            "Review sync recovery",
            f"python -m aresforge inspect-github-sync-recovery --project-id {project_id} --format json",
        ),
    ]
    actions.append(
        _action(
            "dry_run_status_comment",
            "Dry-run status comment sync",
            f"python -m aresforge sync-github-status-comment-durable --item-id {item_id} --dry-run --format json",
            issue_number=issue_number,
        )
    )
    actions.append(
        _action(
            "dry_run_closure_gate",
            "Dry-run issue closure gate",
            f"python -m aresforge gate-github-issue-closure --item-id {item_id} --dry-run --format json",
            issue_number=issue_number,
        )
    )
    actions.append(
        _action(
            "review_pr_draft_plan",
            "Review PR draft branch plan",
            f"python -m aresforge plan-pr-draft-branch --item-id {item_id} --format json",
            pr_number=pr_number,
        )
    )
    actions.append(
        _action(
            "dry_run_pr_evidence_comment",
            "Dry-run PR evidence comment",
            f"python -m aresforge sync-pr-evidence-comment --item-id {item_id} --dry-run --format json",
            pr_number=pr_number,
        )
    )
    if int((recovery_payload.get("operation_counts") or {}).get("operations_partial") or 0) > 0:
        actions.append(
            {
                "record_type": "hub_github_sync_control_panel_next_safe_action_v1",
                "action_id": "repair_partial_sync_first",
                "label": "Repair partial sync evidence first",
                "project_id": project_id,
                "item_id": item_id,
                "repository": repository,
                "sync_status": "repair_recommended",
                "blocked": False,
                "blocked_reasons": [],
                "warnings": ["Partial GitHub sync operations require operator review before retry."],
                "dry_run": True,
                "github_enabled": False,
                "github_execution_performed": False,
                "mutation_performed": False,
                "recovery_available": True,
                "local_only": True,
                "next_safe_action": "Verify remote state and update the durable local registry before retrying creation-like operations.",
            }
        )
    return actions


def _action(action_id: str, label: str, command: str, *, issue_number: int | None = None, pr_number: int | None = None) -> dict[str, Any]:
    return {
        "record_type": "hub_github_sync_control_panel_next_safe_action_v1",
        "action_id": action_id,
        "label": label,
        "command": command,
        "issue_number": issue_number,
        "pr_number": pr_number,
        "sync_status": "dry_run_or_read_only",
        "blocked": False,
        "blocked_reasons": [],
        "warnings": [],
        "dry_run": True,
        "github_enabled": False,
        "github_execution_performed": False,
        "mutation_performed": False,
        "recovery_available": True,
        "local_only": True,
        "next_safe_action": "Run this as a separate review command only; do not infer live GitHub authorization from the panel.",
    }


def _safety_boundaries() -> dict[str, Any]:
    return {
        "record_type": "hub_github_sync_control_panel_safety_boundaries_v1",
        "dry_run_default": True,
        "github_enabled": False,
        "github_execution_performed": False,
        "mutation_performed": False,
        "unsafe_default_execute_buttons": False,
        "real_github_mutation_requires": [
            "explicit operator command",
            "--github-enabled",
            "non-dry-run invocation",
            "github_issue_sync_enabled autonomy profile where required",
            "passing github_sync machine gates",
        ],
        "blocked_operations": [
            "merge_pull_request",
            "enable_auto_merge",
            "force_push",
            "update_protected_branch",
            "create_release",
            "modify_github_workflow",
            "automatic_issue_closure",
            "source_code_patch_application",
        ],
        "local_only": True,
    }


def _gate_summary(gate_payload: dict[str, Any], *, required_for_panel: bool) -> dict[str, Any]:
    checks = gate_payload.get("checks", [])
    failed = [
        _text(check.get("check_id"))
        for check in checks
        if isinstance(check, dict) and not bool(check.get("passed")) and not bool(check.get("warning_only"))
    ]
    return {
        "gate_profile": _text(gate_payload.get("gate_profile") or gate_payload.get("profile")) or "read_only_agent",
        "passed": bool(gate_payload.get("passed")) and not bool(gate_payload.get("blocked")),
        "blocked": bool(gate_payload.get("blocked")),
        "blocked_reasons": _list(gate_payload.get("blocked_reasons")),
        "warnings": _list(gate_payload.get("warnings")),
        "checks_failed": failed,
        "required_for_panel": required_for_panel,
        "dry_run_label": "required_read_only_gate" if required_for_panel else "future_action_gate_status_only",
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
    for item in _dicts(queue.get("work_items")):
        if _text(item.get("item_id")) == item_id:
            return item
    return {}


def _selected_registry_record(records: list[dict[str, Any]], item_id: str) -> dict[str, Any]:
    candidates = [record for record in records if _text(record.get("queue_item_id") or record.get("item_id")) == item_id]
    if not candidates:
        return {}
    return sorted(candidates, key=lambda record: _text(record.get("last_sync_time") or record.get("updated_at")))[-1]


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


def _next_safe_action(*, blocked: bool, recovery_payload: dict[str, Any]) -> str:
    if blocked:
        return "Resolve local read-only panel blockers before relying on GitHub sync control guidance."
    operation_counts = recovery_payload.get("operation_counts", {}) if isinstance(recovery_payload.get("operation_counts"), dict) else {}
    if int(operation_counts.get("operations_partial") or 0) > 0:
        return "Review recovery repair/resume plans; verify remote state before any separate gated retry."
    return "Review registry, dry-run sync plans, reconciliation, and gates; use only separate explicit gated commands for live GitHub work."


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
            "local_only": True,
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
        "local_only": True,
        "format": "json",
        "output": str(output_path),
        "force": force,
        "wrote_output_file": True,
        "payload": artifact_payload,
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


def _panel_idempotency_key(*, project_id: str, item_id: str, repository: str) -> str:
    return "hub-github-sync-control-panel:" + ":".join([_slug(project_id), _slug(item_id), _slug(repository)])


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", _text(value).lower()).strip("-") or "unknown"


def _resolve(repo_root: Path, value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


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
