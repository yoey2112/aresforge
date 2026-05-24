from __future__ import annotations

import re
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.lineage_mapping_signals import (
    BLOCKED_STATE,
    READY_STATE,
    SIGNAL_CASE_INCOMPLETE,
    SIGNAL_CASE_MISSING,
    SIGNAL_CASE_READY,
    LineageMappingSignal,
    aggregate_lineage_mapping_signals,
)
from aresforge.operator.milestone_state_inspector import inspect_milestone_state
from aresforge.operator.canonical_evidence_markers import parse_canonical_evidence_marker
from aresforge.operator.ready_issue_intake import fetch_issue_details


COMMAND_NAME = "inspect-child-evidence-marker-preflight"

_BRANCH_PATTERN = re.compile(r"\bbranch\s*:\s*[\w./-]+", re.IGNORECASE)
_COMMIT_PATTERN = re.compile(r"\bcommit\s*:\s*[0-9a-f]{7,40}\b", re.IGNORECASE)
_PR_PATTERN = re.compile(r"\b(?:pr|pull request)\s*[:#]\s*(?:#\d+|https?://\S+)", re.IGNORECASE)
_VALIDATION_PATTERN = re.compile(r"\bpython\s+-m\s+pytest\b|\bvalidation\s*:\s*", re.IGNORECASE)
_SAFETY_PATTERN = re.compile(r"\bsafety\s+notes?\b|\bread-only\b|\bno\s+mutation\b", re.IGNORECASE)
_EVIDENCE_MARKER_PATTERN = re.compile(r"\bevidence\b", re.IGNORECASE)


def inspect_child_evidence_marker_preflight(config: AppConfig, *, parent_issue: int) -> dict[str, Any]:
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
                "Resolve inspect-milestone-state failures before running child evidence marker preflight."
            ],
        }

    parent_payload = milestone.get("parent_issue") if isinstance(milestone.get("parent_issue"), dict) else {}
    child_rows = milestone.get("child_issues") if isinstance(milestone.get("child_issues"), list) else []

    signals: list[LineageMappingSignal] = []
    children: list[dict[str, Any]] = []
    warnings: list[str] = []

    for row in child_rows:
        if not isinstance(row, dict):
            continue
        issue_number = row.get("issue_number")
        if not isinstance(issue_number, int):
            continue
        signal, rendered, child_warnings = _inspect_child(config=config, parent_issue=parent_issue, child_row=row)
        signals.append(signal)
        children.append(rendered)
        warnings.extend(child_warnings)

    aggregate = aggregate_lineage_mapping_signals(signals).to_dict()
    children.sort(key=lambda item: int(item["issue_number"]))
    warnings = sorted(set(item for item in warnings if item))

    return {
        "command": COMMAND_NAME,
        "ok": True,
        "read_only": True,
        "parent_issue": parent_payload,
        "evidence_summary": {
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
        "warnings": warnings,
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
) -> tuple[LineageMappingSignal, dict[str, Any], list[str]]:
    issue_number = int(child_row["issue_number"])
    title = child_row.get("title")
    state = child_row.get("state")

    payload = fetch_issue_details(config, issue_number)
    issue = payload.get("issue") if isinstance(payload.get("issue"), dict) else {}
    body = issue.get("body") if isinstance(issue.get("body"), str) else ""
    comments = issue.get("comments") if isinstance(issue.get("comments"), list) else []
    joined_comments = "\n".join(
        item.get("body", "")
        for item in comments
        if isinstance(item, dict) and isinstance(item.get("body"), str)
    )
    combined = f"{body}\n{joined_comments}"

    canonical = _extract_canonical_child_marker(combined)

    if canonical is not None:
        markers = {
            "evidence_marker": True,
            "branch": _has_required(canonical.get("required_fields"), "branch"),
            "commit": _has_required(canonical.get("required_fields"), "commit"),
            "pr": _has_required(canonical.get("required_fields"), "pr"),
            "validation": _has_required(canonical.get("required_fields"), "validation_summary"),
            "safety_notes": _has_required(canonical.get("required_fields"), "safety_notes"),
        }
        missing_fields = sorted(name for name, present in markers.items() if not present)
        marker_source = "canonical_marker"
    else:
        markers = {
            "evidence_marker": bool(_EVIDENCE_MARKER_PATTERN.search(combined)),
            "branch": bool(_BRANCH_PATTERN.search(combined)),
            "commit": bool(_COMMIT_PATTERN.search(combined)),
            "pr": bool(_PR_PATTERN.search(combined)),
            "validation": bool(_VALIDATION_PATTERN.search(combined)),
            "safety_notes": bool(_SAFETY_PATTERN.search(combined)),
        }
        missing_fields = sorted(name for name, present in markers.items() if not present)
        marker_source = "legacy_pattern_scan"

    warnings: list[str] = []
    if not bool(payload.get("ok")):
        warnings.append(f"child_issue_lookup_failed:{issue_number}")

    if not bool(payload.get("ok")):
        status = BLOCKED_STATE
        signal_case = SIGNAL_CASE_MISSING
        guidance = (
            f"Re-run evidence marker preflight after child issue #{issue_number} lookup succeeds.",
        )
    elif len(missing_fields) == 0:
        status = READY_STATE
        signal_case = SIGNAL_CASE_READY
        guidance = ()
    elif len(missing_fields) == len(markers):
        status = BLOCKED_STATE
        signal_case = SIGNAL_CASE_MISSING
        guidance = (
            f"Add child evidence marker block to issue #{issue_number} including branch, commit, PR, validation, and safety notes.",
        )
    else:
        status = "warning"
        signal_case = SIGNAL_CASE_INCOMPLETE
        guidance = tuple(
            f"Add missing evidence field '{field}' to child issue #{issue_number} evidence marker."
            for field in missing_fields
        )

    signal = LineageMappingSignal(
        signal_key=f"evidence.child_marker.{issue_number}",
        source="issue_body_and_comments",
        confidence=1.0 if status == READY_STATE else (0.8 if status == "warning" else 0.6),
        status=status,
        signal_case=signal_case,
        parent_issue=parent_issue,
        child_issue=issue_number,
        evidence_comment_marker="detected" if markers["evidence_marker"] else None,
        repair_guidance=guidance,
    )

    return (
        signal,
        {
            "issue_number": issue_number,
            "title": title,
            "state": state,
            "marker_source": marker_source,
            "signal_status": status,
            "signal_case": signal_case,
            "markers": markers,
            "missing_fields": missing_fields,
        },
        warnings,
    )


def _extract_canonical_child_marker(text: str) -> dict[str, Any] | None:
    marker = parse_canonical_evidence_marker(text).to_dict()
    if marker.get("marker_type") != "child_evidence":
        return None
    return marker


def _has_required(required_fields: Any, field_name: str) -> bool:
    if not isinstance(required_fields, dict):
        return False
    value = required_fields.get(field_name)
    return isinstance(value, str) and bool(value.strip())


def _required_actions(*, aggregate: dict[str, Any]) -> list[str]:
    state = aggregate.get("aggregate_state")
    blocked = aggregate.get("blocked_reasons") if isinstance(aggregate.get("blocked_reasons"), list) else []
    warnings = aggregate.get("warning_reasons") if isinstance(aggregate.get("warning_reasons"), list) else []
    guidance = aggregate.get("repair_guidance") if isinstance(aggregate.get("repair_guidance"), list) else []

    actions: list[str] = []
    if state == READY_STATE:
        actions.append("Child evidence marker preflight is ready; proceed to PR mapping preflight.")
    if blocked:
        actions.append("Resolve missing child evidence markers before milestone closeout preflight can report ready.")
    if warnings:
        actions.append("Complete incomplete child evidence fields before parent closeout readiness review.")
    actions.extend(guidance)
    return sorted(set(actions))
