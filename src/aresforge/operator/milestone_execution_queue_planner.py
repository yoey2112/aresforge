from __future__ import annotations

from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.evidence_completeness_checker import check_issue_evidence_readiness
from aresforge.operator.milestone_state_inspector import inspect_milestone_state

COMMAND_NAME = "plan-milestone-execution-queue"


def plan_milestone_execution_queue(config: AppConfig, *, parent_issue: int) -> dict[str, Any]:
    inspection = inspect_milestone_state(config, parent_issue=parent_issue)
    if not inspection.get("ok"):
        return {
            "command": COMMAND_NAME,
            "ok": False,
            "read_only": True,
            "error": "milestone_state_inspection_failed",
            "details": inspection,
            "execution_enabled": False,
            "close_issues": False,
            "bulk_closeout_allowed": False,
            "operator_review_required": True,
            "boundary_confirmations": _boundaries(),
        }

    parent = inspection.get("parent_issue")
    child_issues = inspection.get("child_issues") if isinstance(inspection.get("child_issues"), list) else []
    normalized_children = [item for item in child_issues if isinstance(item, dict)]

    recommended_order = _recommend_order(normalized_children)
    blockers = _collect_blockers(parent_issue=parent_issue, parent=parent, child_issues=normalized_children)
    missing_lineage = _collect_missing_lineage(normalized_children)
    issue_evidence_readiness = _collect_issue_evidence_readiness(config, normalized_children)
    missing_evidence = _collect_missing_evidence(normalized_children, issue_evidence_readiness)
    duplicate_noop_pr_risks = _collect_duplicate_noop_risks(normalized_children, issue_evidence_readiness)
    parent_eligible_for_close = _parent_eligible_for_close(parent, normalized_children)

    required_operator_actions = [
        "Review blockers and resolve missing parent/child lineage before execution.",
        "Execute child issues one-by-one in recommended order with explicit human-triggered commands.",
        "Confirm merged PR evidence and validation traceability per child issue before any closeout step.",
        "Keep reconciliation issue #276 last when present.",
        "Do not close the parent issue while any child issue remains open.",
    ]

    return {
        "command": COMMAND_NAME,
        "ok": True,
        "read_only": True,
        "inspection_mode": "github_read_only",
        "repo": f"{config.github_owner}/{config.github_repo}",
        "parent_issue": parent,
        "child_issues": normalized_children,
        "recommended_order": recommended_order,
        "blocked_items": blockers,
        "safety_gates": {
            "execution_enabled": False,
            "close_issues": False,
            "bulk_closeout_allowed": False,
            "operator_review_required": True,
            "parent_closeout_allowed": parent_eligible_for_close,
        },
        "signals": {
            "missing_parent_child_lineage": missing_lineage,
            "missing_evidence_signals": missing_evidence,
            "duplicate_or_noop_pr_risks": duplicate_noop_pr_risks,
            "final_reconciliation_last_enforced": any(item.get("is_final_reconciliation") for item in recommended_order),
        },
        "evidence_readiness": issue_evidence_readiness,
        "required_operator_actions": required_operator_actions,
        "boundary_confirmations": _boundaries(),
    }


def _recommend_order(child_issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sortable: list[tuple[int, int, int, dict[str, Any]]] = []
    for item in child_issues:
        issue_number = item.get("issue_number")
        if not isinstance(issue_number, int):
            continue
        is_final = _is_final_reconciliation(item)
        rank = 1 if is_final else 0
        discovery_position = item.get("discovery_position")
        sequence_key = discovery_position if isinstance(discovery_position, int) and discovery_position > 0 else 999999
        sortable.append((rank, sequence_key, issue_number, item))
    sortable.sort(key=lambda entry: (entry[0], entry[1], entry[2]))
    ordered: list[dict[str, Any]] = []
    for position, (_, _, issue_number, item) in enumerate(sortable, start=1):
        ordered.append(
            {
                "position": position,
                "issue_number": issue_number,
                "title": item.get("title"),
                "state": item.get("state"),
                "is_final_reconciliation": _is_final_reconciliation(item),
                "discovery_position": item.get("discovery_position"),
            }
        )
    return ordered


def _is_final_reconciliation(item: dict[str, Any]) -> bool:
    number = item.get("issue_number")
    title = item.get("title")
    title_text = title.lower() if isinstance(title, str) else ""
    if number == 276:
        return True
    return bool("source-of-truth" in title_text or "source of truth" in title_text)


def _collect_blockers(
    *, parent_issue: int, parent: Any, child_issues: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    blocked: list[dict[str, Any]] = []
    if not child_issues:
        blocked.append(
            {
                "type": "child_discovery_incomplete",
                "issue_number": parent_issue,
                "reason": "No child issues detected from current references.",
            }
        )
    for item in child_issues:
        issue_number = item.get("issue_number")
        if not isinstance(issue_number, int):
            continue
        if not bool(item.get("lineage_detected")):
            blocked.append(
                {
                    "type": "missing_parent_child_lineage",
                    "issue_number": issue_number,
                    "reason": "Child issue does not include detectable parent lineage.",
                }
            )
    parent_state = parent.get("state") if isinstance(parent, dict) else None
    if isinstance(parent_state, str) and parent_state.upper() == "CLOSED":
        blocked.append(
            {
                "type": "parent_state_unexpected",
                "issue_number": parent_issue,
                "reason": "Parent issue is closed; verify milestone sequencing and child lineage.",
            }
        )
    return blocked


def _collect_missing_lineage(child_issues: list[dict[str, Any]]) -> list[int]:
    missing: list[int] = []
    for item in child_issues:
        issue_number = item.get("issue_number")
        if isinstance(issue_number, int) and not bool(item.get("lineage_detected")):
            missing.append(issue_number)
    return sorted(missing)


def _collect_missing_evidence(
    child_issues: list[dict[str, Any]], readiness_map: dict[int, dict[str, Any]]
) -> list[dict[str, Any]]:
    missing: list[dict[str, Any]] = []
    for item in child_issues:
        issue_number = item.get("issue_number")
        if not isinstance(issue_number, int):
            continue
        readiness = readiness_map.get(issue_number, {})
        classification = readiness.get("classification")
        if classification in ("not_ready", "ambiguous", "blocked"):
            missing.append(
                {
                    "issue_number": issue_number,
                    "reason": "issue_evidence_not_closeout_ready",
                    "classification": classification,
                }
            )
            continue
        merged_pr_count = item.get("merged_pr_count")
        if not isinstance(merged_pr_count, int) or merged_pr_count <= 0:
            missing.append(
                {
                    "issue_number": issue_number,
                    "reason": "merged_pr_evidence_missing",
                }
            )
    return missing


def _collect_duplicate_noop_risks(
    child_issues: list[dict[str, Any]], readiness_map: dict[int, dict[str, Any]]
) -> list[dict[str, Any]]:
    risks: list[dict[str, Any]] = []
    for item in child_issues:
        issue_number = item.get("issue_number")
        title = item.get("title")
        if not isinstance(issue_number, int):
            continue
        readiness = readiness_map.get(issue_number, {})
        duplicate_planning = readiness.get("duplicate_noop_planning")
        if isinstance(duplicate_planning, dict) and duplicate_planning.get("duplicate_pr_risk") is True:
            risks.append(
                {
                    "issue_number": issue_number,
                    "risk": "evidence_checker_duplicate_or_noop_risk",
                    "recommendation": duplicate_planning.get("recommendation"),
                }
            )
            continue
        text = title.lower() if isinstance(title, str) else ""
        if "duplicate" in text or "no-op" in text or "noop" in text:
            risks.append(
                {
                    "issue_number": issue_number,
                    "risk": "title_indicates_duplicate_or_noop_risk",
                }
            )
    return risks


def _collect_issue_evidence_readiness(
    config: AppConfig, child_issues: list[dict[str, Any]]
) -> dict[int, dict[str, Any]]:
    readiness: dict[int, dict[str, Any]] = {}
    for item in child_issues:
        issue_number = item.get("issue_number")
        if not isinstance(issue_number, int):
            continue
        result = check_issue_evidence_readiness(config, issue_number=issue_number)
        readiness[issue_number] = {
            "ok": bool(result.get("ok")),
            "classification": result.get("classification"),
            "duplicate_noop_planning": result.get("duplicate_noop_planning"),
        }
    return readiness


def _parent_eligible_for_close(parent: Any, child_issues: list[dict[str, Any]]) -> bool:
    _ = parent
    for item in child_issues:
        state = item.get("state")
        if isinstance(state, str) and state.upper() != "CLOSED":
            return False
    return bool(child_issues)


def _boundaries() -> list[str]:
    return [
        "read_only: true",
        "execution_enabled: false",
        "close_issues: false",
        "bulk_closeout_allowed: false",
        "operator_review_required: true",
        "Planner is planning-only and performs no GitHub mutation.",
        "No issues were closed, no PRs were created, and no comments were added.",
    ]
