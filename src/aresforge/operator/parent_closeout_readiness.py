from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.evidence_completeness_checker import check_milestone_evidence_readiness
from aresforge.operator.milestone_reconciliation_planner import plan_milestone_final_reconciliation
from aresforge.operator.milestone_state_inspector import inspect_milestone_state

COMMAND_NAME = "inspect-parent-closeout-readiness"
_ACCOUNTED_CLASSIFICATIONS = {"ready", "already_closed"}


def inspect_parent_closeout_readiness(
    config: AppConfig,
    *,
    parent_issue: int,
    state_file: str | Path | None = None,
) -> dict[str, Any]:
    milestone = inspect_milestone_state(config, parent_issue=parent_issue, state_file=state_file)
    evidence = check_milestone_evidence_readiness(config, parent_issue=parent_issue, state_file=state_file)
    reconciliation = (
        _offline_reconciliation_from_state_file(parent_issue=parent_issue, state_file=state_file)
        if state_file is not None
        else plan_milestone_final_reconciliation(config, parent_issue=parent_issue)
    )

    failures = _collect_failures(milestone=milestone, evidence=evidence, reconciliation=reconciliation)
    if failures:
        failure_payload: dict[str, Any] = {
            "command": COMMAND_NAME,
            "ok": False,
            "read_only": True,
            "error": "parent_closeout_readiness_dependency_failed",
            "parent_issue": {"issue_number": parent_issue},
            "failures": failures,
            "required_operator_actions": [
                "Resolve dependency command failures before relying on parent closeout readiness."
            ],
            "safety_gates": _safety_gates(parent_state=None, closeout_ready=False),
            "boundary_confirmations": _boundaries(),
        }
        if state_file is not None:
            failure_payload["inspection_mode"] = "local_state_file"
            failure_payload["state_file"] = str(state_file)
        return failure_payload

    parent = milestone.get("parent_issue") if isinstance(milestone.get("parent_issue"), dict) else {}
    children = milestone.get("child_issues") if isinstance(milestone.get("child_issues"), list) else []
    child_items = [item for item in children if isinstance(item, dict)]

    issue_details = _index_issue_details(evidence)
    child_lineage = _child_lineage(child_items, issue_details)
    lineage_signals = _lineage_signals(child_items, child_lineage)
    blocked_reasons = _blocked_reasons(parent=parent, child_lineage=child_lineage, reconciliation=reconciliation)
    closeout_ready = len(blocked_reasons) == 0
    parent_state = parent.get("state") if isinstance(parent.get("state"), str) else None

    warnings: list[str] = []
    for source in (
        milestone.get("warnings"),
        reconciliation.get("warnings"),
    ):
        if isinstance(source, list):
            warnings.extend(item for item in source if isinstance(item, str))
    warnings = sorted(set(warnings))

    payload: dict[str, Any] = {
        "command": COMMAND_NAME,
        "ok": True,
        "read_only": True,
        "parent_issue": parent,
        "closeout_readiness": {
            "parent_closeout_ready": closeout_ready,
            "parent_state": parent_state,
            "parent_evidence_ready": bool(
                isinstance(evidence.get("milestone_closeout_readiness"), dict)
                and evidence["milestone_closeout_readiness"].get("closeout_ready") is True
            ),
            "final_reconciliation_complete": bool(reconciliation.get("ready_for_final_reconciliation")),
            "parent_should_remain_open": bool(reconciliation.get("parent_should_remain_open")),
        },
        "child_lineage": child_lineage,
        "lineage_signals": lineage_signals,
        "blocked_reasons": blocked_reasons,
        "required_operator_actions": _required_operator_actions(
            blocked_reasons=blocked_reasons,
            reconciliation=reconciliation,
            closeout_ready=closeout_ready,
        ),
        "safety_gates": _safety_gates(parent_state=parent_state, closeout_ready=closeout_ready),
        "boundary_confirmations": _collect_boundaries(
            milestone_boundaries=milestone.get("boundary_confirmations"),
            evidence_boundaries=evidence.get("boundary_confirmations"),
            reconciliation_boundaries=reconciliation.get("boundary_confirmations"),
        ),
        "warnings": warnings,
    }
    if state_file is not None:
        payload["inspection_mode"] = "local_state_file"
        payload["state_file"] = str(state_file)
    return payload


def _offline_reconciliation_from_state_file(
    *,
    parent_issue: int,
    state_file: str | Path,
) -> dict[str, Any]:
    state_path = Path(state_file)
    try:
        parsed = json.loads(state_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return _offline_reconciliation_error(
            parent_issue=parent_issue,
            state_file=state_path,
            error="state_file_not_found",
            details={"path": str(state_path)},
        )
    except json.JSONDecodeError as exc:
        return _offline_reconciliation_error(
            parent_issue=parent_issue,
            state_file=state_path,
            error="state_file_invalid_json",
            details={"path": str(state_path), "message": str(exc)},
        )
    except OSError as exc:
        return _offline_reconciliation_error(
            parent_issue=parent_issue,
            state_file=state_path,
            error="state_file_read_failed",
            details={"path": str(state_path), "message": str(exc)},
        )

    if not isinstance(parsed, dict):
        return _offline_reconciliation_error(
            parent_issue=parent_issue,
            state_file=state_path,
            error="invalid_state_file_schema",
            details={"reason": "state_file_root_must_be_object"},
        )

    summary = parsed.get("final_reconciliation")
    if not isinstance(summary, dict):
        return {
            "command": "plan-milestone-final-reconciliation",
            "ok": True,
            "read_only": True,
            "inspection_mode": "local_state_file",
            "state_file": str(state_path),
            "parent_issue": {"issue_number": parent_issue},
            "ready_for_final_reconciliation": False,
            "parent_should_remain_open": True,
            "unaccounted_children": [],
            "required_operator_actions": [
                "Add final_reconciliation to the local state file before relying on offline parent closeout readiness."
            ],
            "warnings": ["offline_final_reconciliation_not_provided_in_state_file"],
            "boundary_confirmations": _boundaries(),
        }

    ready = summary.get("ready_for_final_reconciliation") is True
    parent_should_remain_open = bool(summary.get("parent_should_remain_open")) if "parent_should_remain_open" in summary else (not ready)
    unaccounted_children = summary.get("unaccounted_children")
    if not isinstance(unaccounted_children, list):
        unaccounted_children = []

    required_operator_actions: list[str] = []
    source_actions = summary.get("required_operator_actions")
    if isinstance(source_actions, list):
        required_operator_actions.extend(item for item in source_actions if isinstance(item, str))
    if not ready:
        required_operator_actions.append(
            "Complete final source-of-truth reconciliation in local state before parent closeout."
        )

    payload: dict[str, Any] = {
        "command": "plan-milestone-final-reconciliation",
        "ok": True,
        "read_only": True,
        "inspection_mode": "local_state_file",
        "state_file": str(state_path),
        "parent_issue": {"issue_number": parent_issue},
        "ready_for_final_reconciliation": ready,
        "parent_should_remain_open": parent_should_remain_open,
        "unaccounted_children": unaccounted_children,
        "required_operator_actions": sorted(set(required_operator_actions)),
        "boundary_confirmations": _boundaries(),
    }

    final_reconciliation_issue = summary.get("final_reconciliation_issue")
    if isinstance(final_reconciliation_issue, int):
        payload["final_reconciliation_issue"] = {"issue_number": final_reconciliation_issue}
    elif isinstance(final_reconciliation_issue, dict):
        payload["final_reconciliation_issue"] = final_reconciliation_issue

    warnings = summary.get("warnings")
    if isinstance(warnings, list):
        payload["warnings"] = [item for item in warnings if isinstance(item, str)]

    return payload


def _offline_reconciliation_error(
    *,
    parent_issue: int,
    state_file: Path,
    error: str,
    details: dict[str, Any],
) -> dict[str, Any]:
    return {
        "command": "plan-milestone-final-reconciliation",
        "ok": False,
        "read_only": True,
        "error": error,
        "inspection_mode": "local_state_file",
        "state_file": str(state_file),
        "parent_issue": {"issue_number": parent_issue},
        "details": details,
        "boundary_confirmations": _boundaries(),
    }


def _collect_failures(
    *,
    milestone: dict[str, Any],
    evidence: dict[str, Any],
    reconciliation: dict[str, Any],
) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    for command, payload in (
        ("inspect-milestone-state", milestone),
        ("check-milestone-evidence-readiness", evidence),
        ("plan-milestone-final-reconciliation", reconciliation),
    ):
        if bool(payload.get("ok")):
            continue
        failures.append(
            {
                "command": command,
                "error": payload.get("error", "unknown_error"),
                "details": payload,
            }
        )
    return failures


def _index_issue_details(evidence: dict[str, Any]) -> dict[int, dict[str, Any]]:
    index: dict[int, dict[str, Any]] = {}
    issues = evidence.get("issues") if isinstance(evidence.get("issues"), list) else []
    for item in issues:
        if not isinstance(item, dict):
            continue
        issue = item.get("issue")
        if not isinstance(issue, dict):
            continue
        number = issue.get("number")
        if not isinstance(number, int):
            continue
        index[number] = {
            "classification": item.get("classification"),
            "duplicate_noop_planning": item.get("duplicate_noop_planning"),
            "evidence_signals": item.get("evidence_signals"),
        }
    return index


def _child_lineage(child_items: list[dict[str, Any]], issue_details: dict[int, dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[int] = set()
    duplicates: set[int] = set()
    for item in child_items:
        number = item.get("issue_number")
        if not isinstance(number, int):
            continue
        if number in seen:
            duplicates.add(number)
        seen.add(number)
        state = item.get("state")
        detail = issue_details.get(number, {})
        classification = detail.get("classification")
        accounted = (
            isinstance(state, str)
            and state.upper() == "CLOSED"
            or isinstance(classification, str)
            and classification in _ACCOUNTED_CLASSIFICATIONS
        )
        evidence_signals = detail.get("evidence_signals") if isinstance(detail.get("evidence_signals"), dict) else {}
        rows.append(
            {
                "issue_number": number,
                "title": item.get("title"),
                "state": state,
                "lineage_detected": bool(item.get("lineage_detected")),
                "lineage_sources": sorted(
                    src for src in (item.get("lineage_sources") or []) if isinstance(src, str)
                ),
                "classification": classification,
                "issue_specific_evidence_mapping": bool(evidence_signals.get("explicit_issue_evidence_mapping")),
                "individually_closed": bool(isinstance(state, str) and state.upper() == "CLOSED"),
                "accounted_for": bool(accounted),
                "duplicate_reference_detected": number in duplicates,
            }
        )
    rows.sort(key=lambda row: int(row["issue_number"]))
    return rows


def _lineage_signals(child_items: list[dict[str, Any]], child_lineage: list[dict[str, Any]]) -> dict[str, Any]:
    discovered_numbers = sorted(
        number for number in (item.get("issue_number") for item in child_items) if isinstance(number, int)
    )
    missing_lineage = sorted(
        row["issue_number"] for row in child_lineage if row.get("lineage_detected") is False
    )
    duplicate_numbers = sorted(
        row["issue_number"] for row in child_lineage if row.get("duplicate_reference_detected") is True
    )
    return {
        "child_issue_count": len(child_lineage),
        "discovered_child_issue_numbers": discovered_numbers,
        "missing_child_lineage_issue_numbers": missing_lineage,
        "duplicated_child_issue_numbers": sorted(set(duplicate_numbers)),
        "ambiguous_child_lineage": bool(missing_lineage or duplicate_numbers),
    }


def _blocked_reasons(
    *,
    parent: dict[str, Any],
    child_lineage: list[dict[str, Any]],
    reconciliation: dict[str, Any],
) -> list[str]:
    reasons: list[str] = []
    parent_state = parent.get("state")
    parent_state_text = parent_state.upper() if isinstance(parent_state, str) else ""
    if parent_state_text != "OPEN":
        reasons.append("parent_issue_not_open")

    if any(row.get("lineage_detected") is False for row in child_lineage):
        reasons.append("child_lineage_missing_for_one_or_more_children")
    if any(row.get("duplicate_reference_detected") is True for row in child_lineage):
        reasons.append("duplicate_child_lineage_detected")
    if any(row.get("issue_specific_evidence_mapping") is False for row in child_lineage):
        reasons.append("missing_issue_specific_evidence_mapping_for_one_or_more_children")
    if any(row.get("individually_closed") is False for row in child_lineage):
        reasons.append("one_or_more_children_not_individually_closed")
    if any(row.get("accounted_for") is False for row in child_lineage):
        reasons.append("one_or_more_children_not_closed_or_accounted_for")

    if not bool(reconciliation.get("ready_for_final_reconciliation")):
        reasons.append("final_source_of_truth_reconciliation_incomplete")
    if bool(reconciliation.get("parent_should_remain_open")):
        reasons.append("parent_should_remain_open_until_final_reconciliation_complete")

    return sorted(set(reasons))


def _required_operator_actions(
    *,
    blocked_reasons: list[str],
    reconciliation: dict[str, Any],
    closeout_ready: bool,
) -> list[str]:
    actions: list[str] = []
    if closeout_ready:
        actions.append("Parent closeout prerequisites appear complete; perform a separate human-reviewed parent closeout step.")
    if "child_lineage_missing_for_one_or_more_children" in blocked_reasons:
        actions.append("Resolve missing child lineage references before parent closeout.")
    if "duplicate_child_lineage_detected" in blocked_reasons:
        actions.append("Resolve duplicate child lineage references before parent closeout.")
    if "missing_issue_specific_evidence_mapping_for_one_or_more_children" in blocked_reasons:
        actions.append("Add or confirm issue-specific evidence mapping for each child issue.")
    if "one_or_more_children_not_individually_closed" in blocked_reasons:
        actions.append("Close each child issue individually; do not use bulk closure.")
    if "one_or_more_children_not_closed_or_accounted_for" in blocked_reasons:
        actions.append("Close or evidence-account all implementation children before parent closeout.")
    if "final_source_of_truth_reconciliation_incomplete" in blocked_reasons:
        actions.append("Complete final source-of-truth reconciliation before parent closeout.")

    source_actions = reconciliation.get("required_operator_actions")
    if isinstance(source_actions, list):
        actions.extend(item for item in source_actions if isinstance(item, str))

    actions.extend(
        [
            "Do not close the parent issue from this command output.",
            "Do not close child issues from this command output.",
            "Do not create PRs, comments, labels, milestones, or branches from this command output.",
        ]
    )
    return sorted(set(actions))


def _safety_gates(*, parent_state: str | None, closeout_ready: bool) -> dict[str, Any]:
    return {
        "read_only": True,
        "close_parent_issue": False,
        "close_child_issues": False,
        "bulk_closeout_allowed": False,
        "create_pr": False,
        "comment_on_issue": False,
        "mutation_allowed": False,
        "operator_review_required": True,
        "parent_state": parent_state,
        "parent_closeout_ready": closeout_ready,
    }


def _collect_boundaries(
    *,
    milestone_boundaries: Any,
    evidence_boundaries: Any,
    reconciliation_boundaries: Any,
) -> list[str]:
    lines: set[str] = set(_boundaries())
    for source in (milestone_boundaries, evidence_boundaries, reconciliation_boundaries):
        if not isinstance(source, list):
            continue
        for item in source:
            if isinstance(item, str):
                lines.add(item)
    return sorted(lines)


def _boundaries() -> list[str]:
    return [
        "read_only: true",
        "close_parent_issue: false",
        "close_child_issues: false",
        "bulk_closeout_allowed: false",
        "create_pr: false",
        "comment_on_issue: false",
        "mutation_allowed: false",
        "operator_review_required: true",
        "Command is read-only and performs no GitHub mutation.",
    ]
