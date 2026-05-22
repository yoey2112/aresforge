from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.evidence_completeness_checker import check_milestone_evidence_readiness
from aresforge.operator.milestone_execution_queue_planner import plan_milestone_execution_queue
from aresforge.operator.milestone_state_inspector import inspect_milestone_state

COMMAND_NAME = "inspect-sequential-run-state"
SCHEMA_VERSION = "1.0"
DEFAULT_STATE_RELATIVE_PATH = ".aresforge/sequential-run-state.json"


def resolve_sequential_run_state_path(
    *,
    config: AppConfig | None = None,
    path_override: str | None = None,
) -> Path:
    if path_override:
        candidate = Path(path_override)
        if candidate.is_absolute():
            return candidate
        if config is not None:
            return (config.repo_root / candidate).resolve()
        return candidate.resolve()
    root = config.repo_root if config is not None else Path.cwd()
    return (root / DEFAULT_STATE_RELATIVE_PATH).resolve()


def inspect_sequential_run_state(
    config: AppConfig,
    *,
    parent_issue: int,
    state_path: Path,
    write_local_state: bool = False,
) -> dict[str, Any]:
    snapshot = _build_snapshot(config, parent_issue=parent_issue)
    if not snapshot.get("ok"):
        return snapshot

    existing = _load_state(state_path)
    payload = {
        "command": COMMAND_NAME,
        "ok": True,
        "read_only": not write_local_state,
        "parent_issue": parent_issue,
        "sequential_run_state_path": str(state_path),
        "state_exists": bool(existing.get("exists")),
        "state_loaded_ok": bool(existing.get("ok")),
        "state_validation_errors": existing.get("errors", []),
        "snapshot": snapshot["snapshot"],
        "next_recommended_action": snapshot["snapshot"].get("next_recommended_action"),
        "safety": {
            "github_mutation_allowed": False,
            "bulk_closeout_allowed": False,
            "operator_review_required": True,
            "local_state_write_enabled": bool(write_local_state),
        },
        "boundary_confirmations": [
            "No GitHub issues, PRs, comments, labels, milestones, or repository settings were mutated.",
            "Inspection/planning output is safe for operator review.",
            "Local state writes occur only with explicit --write-local-state.",
        ],
    }
    if write_local_state:
        stored = _persist_snapshot(state_path, snapshot["snapshot"])
        payload["local_write"] = {
            "performed": True,
            "path": str(state_path),
            "record_count": stored["record_count"],
            "schema_version": stored["schema_version"],
        }
    else:
        payload["local_write"] = {"performed": False}
    return payload


def _build_snapshot(config: AppConfig, *, parent_issue: int) -> dict[str, Any]:
    milestone_state = inspect_milestone_state(config, parent_issue=parent_issue)
    queue = plan_milestone_execution_queue(config, parent_issue=parent_issue)
    evidence = check_milestone_evidence_readiness(config, parent_issue=parent_issue)
    failures: list[str] = []
    for name, result in (
        ("inspect-milestone-state", milestone_state),
        ("plan-milestone-execution-queue", queue),
        ("check-milestone-evidence-readiness", evidence),
    ):
        if not bool(result.get("ok")):
            failures.append(name)
    if failures:
        return {
            "command": COMMAND_NAME,
            "ok": False,
            "read_only": True,
            "parent_issue": parent_issue,
            "error": "dependency_command_failed",
            "failed_dependencies": failures,
            "boundary_confirmations": [
                "No GitHub state was mutated.",
                "Local state was not written.",
            ],
        }

    children = [item for item in milestone_state.get("child_issues", []) if isinstance(item, dict)]
    completed_children = sorted(
        item["issue_number"]
        for item in children
        if isinstance(item.get("issue_number"), int) and str(item.get("state", "")).upper() == "CLOSED"
    )
    current_child = _current_child_issue(queue)
    failed_step = _failed_step(queue=queue, evidence=evidence)
    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "parent_issue": parent_issue,
        "current_child_issue": current_child,
        "completed_children": completed_children,
        "failed_step": failed_step,
        "pr_references": _pr_references(children),
        "validation_status": _validation_status(children),
        "evidence_status": _evidence_status(evidence),
        "next_recommended_action": _next_action(queue=queue, failed_step=failed_step, current_child=current_child),
        "dashboard_context": {
            "blocked_items": queue.get("blocked_items"),
            "status_counts": evidence.get("status_counts"),
        },
    }
    return {"ok": True, "snapshot": snapshot}


def _current_child_issue(queue: dict[str, Any]) -> int | None:
    order = queue.get("recommended_order")
    if not isinstance(order, list):
        return None
    for item in order:
        if not isinstance(item, dict):
            continue
        issue_number = item.get("issue_number")
        state = str(item.get("state", "")).upper()
        if isinstance(issue_number, int) and state != "CLOSED" and not bool(item.get("is_final_reconciliation")):
            return issue_number
    return None


def _failed_step(*, queue: dict[str, Any], evidence: dict[str, Any]) -> str | None:
    blocked = queue.get("blocked_items")
    if isinstance(blocked, list) and blocked:
        return "queue_blocked"
    issues = evidence.get("issues")
    if isinstance(issues, list):
        for item in issues:
            if not isinstance(item, dict):
                continue
            if item.get("classification") in {"blocked", "not_ready", "ambiguous"}:
                return "evidence_not_ready"
    return None


def _pr_references(children: list[dict[str, Any]]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for item in children:
        issue_number = item.get("issue_number")
        if not isinstance(issue_number, int):
            continue
        refs.append(
            {
                "issue_number": issue_number,
                "merged_pr_count": item.get("merged_pr_count"),
            }
        )
    return refs


def _validation_status(children: list[dict[str, Any]]) -> dict[str, Any]:
    closed = 0
    open_count = 0
    for item in children:
        state = str(item.get("state", "")).upper()
        if state == "CLOSED":
            closed += 1
        elif state == "OPEN":
            open_count += 1
    return {
        "closed_children": closed,
        "open_children": open_count,
        "all_closed": open_count == 0 and (closed > 0 or len(children) == 0),
    }


def _evidence_status(evidence: dict[str, Any]) -> dict[str, Any]:
    status_counts = evidence.get("status_counts") if isinstance(evidence.get("status_counts"), dict) else {}
    readiness = evidence.get("milestone_closeout_readiness") if isinstance(
        evidence.get("milestone_closeout_readiness"), dict
    ) else {}
    return {
        "status_counts": status_counts,
        "milestone_closeout_ready": readiness.get("closeout_ready"),
        "operator_review_required": readiness.get("operator_review_required"),
    }


def _next_action(*, queue: dict[str, Any], failed_step: str | None, current_child: int | None) -> str:
    if failed_step == "queue_blocked":
        return "Resolve queue blockers before starting or continuing child execution."
    if failed_step == "evidence_not_ready":
        return "Resolve evidence/validation gaps on the active child before closeout."
    if isinstance(current_child, int):
        return f"Proceed with child issue #{current_child} from clean synced main."
    blocked = queue.get("blocked_items")
    if isinstance(blocked, list) and blocked:
        return "Review blocked items and parent/child lineage references."
    return "No actionable child detected; inspect parent checklist and lineage references."


def _load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"ok": True, "exists": False, "errors": []}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"ok": False, "exists": True, "errors": [f"invalid_json: {exc}"]}
    if not isinstance(payload, dict):
        return {"ok": False, "exists": True, "errors": ["root_must_be_object"]}
    version = payload.get("schema_version")
    if version != SCHEMA_VERSION:
        return {"ok": False, "exists": True, "errors": ["unsupported_schema_version"]}
    records = payload.get("records")
    if not isinstance(records, list):
        return {"ok": False, "exists": True, "errors": ["records_missing_or_invalid"]}
    return {"ok": True, "exists": True, "errors": []}


def _persist_snapshot(path: Path, snapshot: dict[str, Any]) -> dict[str, Any]:
    if path.exists():
        try:
            current = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            current = {"schema_version": SCHEMA_VERSION, "records": []}
    else:
        current = {"schema_version": SCHEMA_VERSION, "records": []}
    if not isinstance(current, dict) or current.get("schema_version") != SCHEMA_VERSION:
        current = {"schema_version": SCHEMA_VERSION, "records": []}
    records = current.get("records")
    if not isinstance(records, list):
        records = []
    parent_issue = snapshot.get("parent_issue")
    records = [
        item
        for item in records
        if not (isinstance(item, dict) and item.get("parent_issue") == parent_issue)
    ]
    records.append(snapshot)
    records.sort(key=lambda item: str(item.get("parent_issue")))
    current["records"] = records
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(current, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"record_count": len(records), "schema_version": current.get("schema_version")}
