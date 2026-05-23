from __future__ import annotations

from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.lineage_mapping_signals import (
    BLOCKED_STATE,
    READY_STATE,
    SIGNAL_CASE_CONFLICTING,
    SIGNAL_CASE_INCOMPLETE,
    SIGNAL_CASE_MISSING,
    SIGNAL_CASE_READY,
    UNKNOWN_STATE,
    WARNING_STATE,
    LineageMappingSignal,
    aggregate_lineage_mapping_signals,
)
from aresforge.operator.milestone_state_inspector import inspect_milestone_state
from aresforge.operator.ready_issue_intake import fetch_issue_details


COMMAND_NAME = "inspect-parent-child-linkage-preflight"


def inspect_parent_child_linkage_preflight(config: AppConfig, *, parent_issue: int) -> dict[str, Any]:
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
                "Resolve inspect-milestone-state failures before relying on parent-child linkage preflight."
            ],
        }

    parent_payload = milestone.get("parent_issue") if isinstance(milestone.get("parent_issue"), dict) else {}
    child_rows = milestone.get("child_issues") if isinstance(milestone.get("child_issues"), list) else []

    signals: list[LineageMappingSignal] = []
    rendered_children: list[dict[str, Any]] = []
    warnings: list[str] = []

    for row in child_rows:
        if not isinstance(row, dict):
            continue
        issue_number = row.get("issue_number")
        if not isinstance(issue_number, int):
            continue

        signal, child_summary, child_warnings = _build_child_lineage_signal(
            config=config,
            parent_issue=parent_issue,
            child_row=row,
        )
        signals.append(signal)
        rendered_children.append(child_summary)
        warnings.extend(child_warnings)

    aggregate = aggregate_lineage_mapping_signals(signals)
    aggregate_payload = aggregate.to_dict()

    required_actions = _required_actions(aggregate_payload)
    rendered_children.sort(key=lambda item: int(item["issue_number"]))
    warnings = sorted(set(item for item in warnings if item))

    return {
        "command": COMMAND_NAME,
        "ok": True,
        "read_only": True,
        "parent_issue": parent_payload,
        "lineage_summary": {
            "child_issue_count": len(rendered_children),
            "aggregate_state": aggregate_payload["aggregate_state"],
            "closeout_ready": aggregate_payload["closeout_ready"],
        },
        "children": rendered_children,
        "signals": aggregate_payload["signals"],
        "blocked_reasons": aggregate_payload["blocked_reasons"],
        "warning_reasons": aggregate_payload["warning_reasons"],
        "unknown_reasons": aggregate_payload["unknown_reasons"],
        "repair_guidance": aggregate_payload["repair_guidance"],
        "required_operator_actions": required_actions,
        "warnings": warnings,
        "boundary_confirmations": [
            "Read-only preflight inspection only.",
            "No GitHub mutation was executed.",
            "No issue, PR, branch, label, milestone, or repository file mutation was executed by this command.",
        ],
    }


def _build_child_lineage_signal(
    *,
    config: AppConfig,
    parent_issue: int,
    child_row: dict[str, Any],
) -> tuple[LineageMappingSignal, dict[str, Any], list[str]]:
    issue_number = int(child_row["issue_number"])
    title = child_row.get("title")
    state = child_row.get("state")
    lineage_detected = bool(child_row.get("lineage_detected"))
    lineage_sources = sorted(
        item for item in (child_row.get("lineage_sources") or []) if isinstance(item, str)
    )

    fetched = fetch_issue_details(config, issue_number)
    referenced_parents = _parent_refs_from_issue(fetched.get("issue"))
    conflicting_parent_refs = sorted(
        set(ref for ref in referenced_parents if ref != parent_issue)
    )

    warnings: list[str] = []
    if not bool(fetched.get("ok")):
        warnings.append(f"child_issue_lookup_failed:{issue_number}")

    if conflicting_parent_refs:
        signal_case = SIGNAL_CASE_CONFLICTING
        status = BLOCKED_STATE
        guidance = (
            f"Update child issue #{issue_number} to reference only parent #{parent_issue} for this milestone lineage.",
            f"Remove conflicting parent references from child issue #{issue_number}: {conflicting_parent_refs}.",
        )
    elif lineage_detected:
        signal_case = SIGNAL_CASE_READY
        status = READY_STATE
        guidance = ()
    elif bool(fetched.get("ok")):
        signal_case = SIGNAL_CASE_MISSING
        status = BLOCKED_STATE
        guidance = (
            f"Add explicit parent lineage reference to child issue #{issue_number}: Parent issue: #{parent_issue}.",
            f"Update parent issue #{parent_issue} child checklist to include child issue #{issue_number} if missing.",
        )
    else:
        signal_case = SIGNAL_CASE_INCOMPLETE
        status = UNKNOWN_STATE
        guidance = (
            f"Re-run linkage preflight after issue lookup succeeds for child issue #{issue_number}.",
        )

    signal = LineageMappingSignal(
        signal_key=f"lineage.parent_child.{issue_number}",
        source="inspect-milestone-state",
        confidence=1.0 if signal_case == SIGNAL_CASE_READY else (0.7 if signal_case == SIGNAL_CASE_MISSING else 0.4),
        status=status,
        signal_case=signal_case,
        parent_issue=parent_issue,
        child_issue=issue_number,
        repair_guidance=guidance,
    )

    return (
        signal,
        {
            "issue_number": issue_number,
            "title": title,
            "state": state,
            "lineage_detected": lineage_detected,
            "lineage_sources": lineage_sources,
            "referenced_parent_issues": referenced_parents,
            "conflicting_parent_issues": conflicting_parent_refs,
            "signal_status": status,
            "signal_case": signal_case,
        },
        warnings,
    )


def _parent_refs_from_issue(issue_payload: Any) -> list[int]:
    if not isinstance(issue_payload, dict):
        return []
    refs = (issue_payload.get("reference_classification") or {}).get("implementation_issue_numbers")
    if not isinstance(refs, list):
        return []
    return sorted(set(item for item in refs if isinstance(item, int)))


def _required_actions(payload: dict[str, Any]) -> list[str]:
    state = payload.get("aggregate_state")
    blocked = payload.get("blocked_reasons") if isinstance(payload.get("blocked_reasons"), list) else []
    guidance = payload.get("repair_guidance") if isinstance(payload.get("repair_guidance"), list) else []
    actions: list[str] = []

    if state == READY_STATE:
        return [
            "Parent-child lineage preflight is ready; proceed to evidence marker and PR mapping preflight checks.",
        ]

    if blocked:
        actions.append("Resolve blocked lineage findings before milestone closeout preflight can report ready.")
    if state in {UNKNOWN_STATE, WARNING_STATE}:
        actions.append("Resolve unknown or warning lineage findings before parent closeout readiness review.")
    actions.extend(guidance)
    return sorted(set(actions))
