from __future__ import annotations

from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.lineage_mapping_signals import (
    BLOCKED_STATE,
    READY_STATE,
    SIGNAL_CASE_AMBIGUOUS,
    SIGNAL_CASE_INCOMPLETE,
    SIGNAL_CASE_MISSING,
    SIGNAL_CASE_READY,
    WARNING_STATE,
    LineageMappingSignal,
    aggregate_lineage_mapping_signals,
)
from aresforge.operator.milestone_state_inspector import inspect_milestone_state


COMMAND_NAME = "inspect-pr-mapping-preflight"


def inspect_pr_mapping_preflight(config: AppConfig, *, parent_issue: int) -> dict[str, Any]:
    milestone = inspect_milestone_state(config, parent_issue=parent_issue)
    if not bool(milestone.get("ok")):
        return {
            "command": COMMAND_NAME,
            "ok": False,
            "read_only": True,
            "error": "milestone_state_inspection_failed",
            "parent_issue": {"issue_number": parent_issue},
            "details": milestone,
            "required_operator_actions": [
                "Resolve inspect-milestone-state failures before running PR mapping preflight."
            ],
        }

    parent_payload = milestone.get("parent_issue") if isinstance(milestone.get("parent_issue"), dict) else {}
    child_rows = milestone.get("child_issues") if isinstance(milestone.get("child_issues"), list) else []

    signals: list[LineageMappingSignal] = []
    children: list[dict[str, Any]] = []

    for row in child_rows:
        if not isinstance(row, dict):
            continue
        issue_number = row.get("issue_number")
        if not isinstance(issue_number, int):
            continue
        signal, rendered = _inspect_child(parent_issue=parent_issue, child_row=row)
        signals.append(signal)
        children.append(rendered)

    aggregate = aggregate_lineage_mapping_signals(signals).to_dict()
    children.sort(key=lambda item: int(item["issue_number"]))

    return {
        "command": COMMAND_NAME,
        "ok": True,
        "read_only": True,
        "parent_issue": parent_payload,
        "pr_mapping_summary": {
            "child_issue_count": len(children),
            "aggregate_state": aggregate["aggregate_state"],
            "closeout_ready": aggregate["closeout_ready"],
        },
        "children": children,
        "signals": aggregate["signals"],
        "blocked_reasons": aggregate["blocked_reasons"],
        "warning_reasons": aggregate["warning_reasons"],
        "unknown_reasons": aggregate["unknown_reasons"],
        "repair_guidance": aggregate["repair_guidance"],
        "required_operator_actions": _required_actions(aggregate=aggregate),
        "boundary_confirmations": [
            "Read-only preflight inspection only.",
            "No GitHub mutation was executed.",
            "No issue, PR, branch, label, milestone, or repository file mutation was executed by this command.",
        ],
    }


def _inspect_child(*, parent_issue: int, child_row: dict[str, Any]) -> tuple[LineageMappingSignal, dict[str, Any]]:
    issue_number = int(child_row["issue_number"])
    linked_pr_count = int(child_row.get("linked_pr_count") or 0)
    merged_pr_count = int(child_row.get("merged_pr_count") or 0)

    if linked_pr_count == 0 and merged_pr_count == 0:
        status = BLOCKED_STATE
        signal_case = SIGNAL_CASE_MISSING
        guidance = (
            f"Link child issue #{issue_number} to its implementation PR.",
            f"Merge the mapped PR for child issue #{issue_number} before parent closeout.",
        )
    elif linked_pr_count > 1 and merged_pr_count == 0:
        status = WARNING_STATE
        signal_case = SIGNAL_CASE_AMBIGUOUS
        guidance = (
            f"Resolve ambiguous PR mapping for child issue #{issue_number}; keep one canonical linked PR.",
            f"Merge the selected PR for child issue #{issue_number} before parent closeout.",
        )
    elif linked_pr_count >= 1 and merged_pr_count == 0:
        status = BLOCKED_STATE
        signal_case = SIGNAL_CASE_INCOMPLETE
        guidance = (
            f"Merge linked PR for child issue #{issue_number} before parent closeout preflight can report ready.",
        )
    elif linked_pr_count > 1 and merged_pr_count >= 1:
        status = WARNING_STATE
        signal_case = SIGNAL_CASE_AMBIGUOUS
        guidance = (
            f"Keep one canonical merged PR mapping for child issue #{issue_number} to avoid ambiguity.",
        )
    else:
        status = READY_STATE
        signal_case = SIGNAL_CASE_READY
        guidance = ()

    signal = LineageMappingSignal(
        signal_key=f"pr.mapping.{issue_number}",
        source="inspect-milestone-state",
        confidence=1.0 if status == READY_STATE else 0.8,
        status=status,
        signal_case=signal_case,
        parent_issue=parent_issue,
        child_issue=issue_number,
        pr_mapping_marker="linked" if linked_pr_count > 0 else None,
        repair_guidance=guidance,
    )

    return (
        signal,
        {
            "issue_number": issue_number,
            "title": child_row.get("title"),
            "state": child_row.get("state"),
            "linked_pr_count": linked_pr_count,
            "merged_pr_count": merged_pr_count,
            "signal_status": status,
            "signal_case": signal_case,
            "missing_pr_mapping": linked_pr_count == 0,
            "ambiguous_pr_mapping": linked_pr_count > 1,
            "unmerged_prs": linked_pr_count > 0 and merged_pr_count == 0,
        },
    )


def _required_actions(*, aggregate: dict[str, Any]) -> list[str]:
    state = aggregate.get("aggregate_state")
    blocked = aggregate.get("blocked_reasons") if isinstance(aggregate.get("blocked_reasons"), list) else []
    warnings = aggregate.get("warning_reasons") if isinstance(aggregate.get("warning_reasons"), list) else []
    guidance = aggregate.get("repair_guidance") if isinstance(aggregate.get("repair_guidance"), list) else []

    actions: list[str] = []
    if state == READY_STATE:
        actions.append("PR mapping preflight is ready; proceed to repair guidance and orchestration preflight.")
    if blocked:
        actions.append("Resolve blocked PR mapping and unmerged PR findings before parent closeout readiness review.")
    if warnings:
        actions.append("Resolve ambiguous PR mappings before final closeout preflight orchestration.")
    actions.extend(guidance)
    return sorted(set(actions))
