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
from aresforge.operator.pr_evidence_extraction import (
    MAPPING_STATE_AMBIGUOUS,
    MAPPING_STATE_MISSING,
    MAPPING_STATE_READY,
    MAPPING_STATE_UNMERGED,
    MAPPING_STATE_UNKNOWN,
    extract_pr_evidence_mapping,
)
from aresforge.operator.ready_issue_intake import fetch_issue_details


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
        signal, rendered = _inspect_child(config=config, parent_issue=parent_issue, child_row=row)
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


def _inspect_child(
    *,
    config: AppConfig,
    parent_issue: int,
    child_row: dict[str, Any],
) -> tuple[LineageMappingSignal, dict[str, Any]]:
    issue_number = int(child_row["issue_number"])
    linked_pr_count = int(child_row.get("linked_pr_count") or 0)
    merged_pr_count = int(child_row.get("merged_pr_count") or 0)

    issue_payload = fetch_issue_details(config, issue_number)
    issue = issue_payload.get("issue") if isinstance(issue_payload.get("issue"), dict) else {}
    issue_body = issue.get("body") if isinstance(issue.get("body"), str) else ""
    comments = issue.get("comments") if isinstance(issue.get("comments"), list) else []
    mapping = extract_pr_evidence_mapping(
        issue_number=issue_number,
        issue_body=issue_body,
        comments=comments,
        linked_pr_count=linked_pr_count,
        merged_pr_count=merged_pr_count,
    )
    mapping_state = mapping.get("mapping_state")

    if mapping_state == MAPPING_STATE_MISSING:
        status = BLOCKED_STATE
        signal_case = SIGNAL_CASE_MISSING
        guidance = (
            f"Link child issue #{issue_number} to its implementation PR.",
            f"Merge the mapped PR for child issue #{issue_number} before parent closeout.",
        )
    elif mapping_state == MAPPING_STATE_AMBIGUOUS:
        status = WARNING_STATE
        signal_case = SIGNAL_CASE_AMBIGUOUS
        guidance = (
            f"Resolve ambiguous PR mapping for child issue #{issue_number}; keep one canonical linked PR.",
            f"Merge the selected PR for child issue #{issue_number} before parent closeout.",
        )
    elif mapping_state == MAPPING_STATE_UNMERGED:
        status = BLOCKED_STATE
        signal_case = SIGNAL_CASE_INCOMPLETE
        guidance = (
            f"Merge linked PR for child issue #{issue_number} before parent closeout preflight can report ready.",
        )
    elif mapping_state == MAPPING_STATE_READY:
        status = READY_STATE
        signal_case = SIGNAL_CASE_READY
        guidance = ()
    else:
        status = "unknown"
        signal_case = "incomplete"
        guidance = (
            f"Review PR mapping evidence for child issue #{issue_number} and reconcile unknown mapping state.",
        )

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
            "normalized_pr_number": mapping.get("pr_number"),
            "normalized_branch": mapping.get("branch"),
            "normalized_commit": mapping.get("commit"),
            "normalized_merge_status": mapping.get("merge_status"),
            "normalized_evidence_status": mapping.get("evidence_status"),
            "mapping_source": mapping.get("source"),
            "canonical_preferred": mapping.get("source") == "canonical_marker",
            "signal_status": status,
            "signal_case": signal_case,
            "mapping_state": mapping_state,
            "missing_pr_mapping": mapping_state == MAPPING_STATE_MISSING,
            "ambiguous_pr_mapping": mapping_state == MAPPING_STATE_AMBIGUOUS,
            "unmerged_prs": mapping_state == MAPPING_STATE_UNMERGED,
            "unknown_pr_mapping": mapping_state == MAPPING_STATE_UNKNOWN,
            "canonical_candidate_count": (mapping.get("canonical") or {}).get("candidate_count"),
            "canonical_invalid_block_count": (mapping.get("canonical") or {}).get("invalid_block_count"),
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
