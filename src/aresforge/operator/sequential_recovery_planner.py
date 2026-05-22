from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.child_execution_gates import inspect_child_execution_gates
from aresforge.operator.milestone_dashboard import inspect_milestone_dashboard
from aresforge.operator.sequential_run_state import resolve_sequential_run_state_path

COMMAND_NAME = "plan-sequential-run-recovery"
SCHEMA_VERSION = "1.0"


def plan_sequential_run_recovery(
    config: AppConfig,
    *,
    parent_issue: int,
    state_path: Path | None = None,
) -> dict[str, Any]:
    resolved = state_path or resolve_sequential_run_state_path(config=config)
    run_state = _load_state(resolved, parent_issue=parent_issue)
    dashboard = inspect_milestone_dashboard(config, parent_issue=parent_issue)

    if not dashboard.get("ok"):
        return {
            "command": COMMAND_NAME,
            "ok": False,
            "read_only": True,
            "error": "dashboard_inspection_failed",
            "parent_issue": parent_issue,
            "dashboard_details": dashboard,
            "boundary_confirmations": _boundaries(),
        }

    current_child = run_state.get("current_child_issue")
    gate = None
    if isinstance(current_child, int):
        gate = inspect_child_execution_gates(config, issue_number=current_child, parent_issue=parent_issue)

    states = _recovery_states(run_state=run_state, dashboard=dashboard, gate=gate)
    next_action = _next_action(states=states, current_child=current_child)

    return {
        "command": COMMAND_NAME,
        "ok": True,
        "read_only": True,
        "parent_issue": parent_issue,
        "sequential_run_state_path": str(resolved),
        "run_state_exists": run_state.get("exists"),
        "run_state_loaded_ok": run_state.get("ok"),
        "run_state_errors": run_state.get("errors", []),
        "current_child_issue": current_child,
        "dashboard_recommended_child_issue": (
            (dashboard.get("dashboard") or {}).get("recommended_next_child_issue") or {}
        ).get("issue_number"),
        "recovery_states": states,
        "next_recommended_action": next_action,
        "safety": {
            "read_only": True,
            "mutation_allowed": False,
            "operator_review_required": True,
        },
        "boundary_confirmations": _boundaries(),
    }


def _load_state(path: Path, *, parent_issue: int) -> dict[str, Any]:
    if not path.exists():
        return {"ok": True, "exists": False, "errors": [], "current_child_issue": None, "failed_step": None}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        return {"ok": False, "exists": True, "errors": [f"invalid_json: {exc}"], "current_child_issue": None, "failed_step": None}
    if not isinstance(payload, dict) or payload.get("schema_version") != SCHEMA_VERSION:
        return {"ok": False, "exists": True, "errors": ["unsupported_schema_or_shape"], "current_child_issue": None, "failed_step": None}
    records = payload.get("records")
    if not isinstance(records, list):
        return {"ok": False, "exists": True, "errors": ["records_missing_or_invalid"], "current_child_issue": None, "failed_step": None}
    selected = None
    for item in records:
        if isinstance(item, dict) and item.get("parent_issue") == parent_issue:
            selected = item
            break
    if not isinstance(selected, dict):
        return {"ok": True, "exists": True, "errors": [], "current_child_issue": None, "failed_step": None}
    return {
        "ok": True,
        "exists": True,
        "errors": [],
        "current_child_issue": selected.get("current_child_issue"),
        "failed_step": selected.get("failed_step"),
        "current_branch": selected.get("current_branch"),
    }


def _recovery_states(*, run_state: dict[str, Any], dashboard: dict[str, Any], gate: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    failed_step = run_state.get("failed_step")
    gate_status = (gate or {}).get("gate_status", {})
    checks = (gate or {}).get("checks", {})
    merged_pr_count = checks.get("merged_pr_count")
    evidence_classification = checks.get("evidence_classification")
    branch_name = checks.get("current_branch")
    run_state_branch = run_state.get("current_branch")
    dashboard_child = (((dashboard.get("dashboard") or {}).get("recommended_next_child_issue") or {}).get("issue_number"))
    current_child = run_state.get("current_child_issue")

    return {
        "failed_validation": {
            "active": failed_step == "validation_failed",
            "reason": "run_state_failed_step_validation_failed",
        },
        "failed_pr_creation": {
            "active": failed_step == "pr_creation_failed",
            "reason": "run_state_failed_step_pr_creation_failed",
        },
        "unmerged_pr": {
            "active": bool(checks.get("open_pr")),
            "reason": "open_pr_detected_for_current_child",
        },
        "merged_pr_missing_evidence": {
            "active": isinstance(merged_pr_count, int) and merged_pr_count > 0 and evidence_classification not in {"ready", "already_closed"},
            "reason": "merged_pr_present_but_evidence_not_ready",
        },
        "closed_child": {
            "active": bool(gate_status.get("already_closed")),
            "reason": "current_child_already_closed",
        },
        "stale_branch": {
            "active": isinstance(run_state_branch, str) and isinstance(branch_name, str) and run_state_branch != branch_name,
            "reason": "run_state_branch_differs_from_current_branch",
        },
        "dirty_tree": {
            "active": bool(checks.get("dirty_worktree")),
            "reason": "working_tree_not_clean",
        },
        "dashboard_mismatch": {
            "active": isinstance(current_child, int) and isinstance(dashboard_child, int) and current_child != dashboard_child,
            "reason": "run_state_current_child_differs_from_dashboard_recommendation",
        },
    }


def _next_action(*, states: dict[str, dict[str, Any]], current_child: Any) -> str:
    for key in (
        "dirty_tree",
        "failed_validation",
        "failed_pr_creation",
        "unmerged_pr",
        "merged_pr_missing_evidence",
        "dashboard_mismatch",
        "stale_branch",
    ):
        if states.get(key, {}).get("active"):
            return f"Resolve recovery state '{key}' before continuing sequential execution."
    if states.get("closed_child", {}).get("active"):
        return "Current child is closed; move to the next open child after dashboard inspection."
    if isinstance(current_child, int):
        return f"No active recovery blockers detected; continue child #{current_child} from clean synced main."
    return "No current child found in persisted run-state; regenerate run-state and inspect parent lineage."


def _boundaries() -> list[str]:
    return [
        "read_only: true",
        "mutation_allowed: false",
        "No issues were closed.",
        "No pull requests were created or merged.",
        "No comments were added.",
    ]
