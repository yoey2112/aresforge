from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.milestone_state_inspector import inspect_milestone_state
from aresforge.operator.ready_issue_intake import fetch_issue_details

COMMAND_ISSUE = "check-issue-evidence-readiness"
COMMAND_MILESTONE = "check-milestone-evidence-readiness"

STATE_READY = "ready"
STATE_NOT_READY = "not_ready"
STATE_AMBIGUOUS = "ambiguous"
STATE_BLOCKED = "blocked"
STATE_ALREADY_CLOSED = "already_closed"

_DUPLICATE_PATTERN = re.compile(r"\bduplicate\b|\bno[- ]?op\b", re.IGNORECASE)
_DOCS_ONLY_PATTERN = re.compile(r"\bdocs[- ]only\b|\bdocumentation\b|\breconciliation\b", re.IGNORECASE)
_MAPPING_PATTERN = re.compile(r"\b(implements|fixes|resolves|closes)\s+#\d+\b", re.IGNORECASE)


def check_issue_evidence_readiness(config: AppConfig, *, issue_number: int) -> dict[str, Any]:
    payload = fetch_issue_details(config, issue_number)
    if not payload.get("ok"):
        return _error_payload(COMMAND_ISSUE, payload, issue_number=issue_number)

    issue = payload.get("issue")
    if not isinstance(issue, dict):
        return _error_payload(COMMAND_ISSUE, {"error": "issue_lookup_failed"}, issue_number=issue_number)

    classification, reasons = _classify_issue(issue)
    merged_prs = issue.get("merged_pr_evidence") if isinstance(issue.get("merged_pr_evidence"), list) else []
    duplicate_pr_risk = _has_duplicate_or_noop_signals(issue)
    docs_only_reconciliation = _is_docs_only_reconciliation(issue)
    explicit_mapping = _has_explicit_mapping(issue)

    new_pr_needed = _new_pr_needed(
        classification=classification,
        merged_prs=merged_prs,
        docs_only_reconciliation=docs_only_reconciliation,
    )
    recommendation = _recommendation(
        classification=classification,
        merged_prs=merged_prs,
        duplicate_pr_risk=duplicate_pr_risk,
        new_pr_needed=new_pr_needed,
    )
    closeout_ready = True if classification in (STATE_READY, STATE_ALREADY_CLOSED) else (
        "ambiguous" if classification == STATE_AMBIGUOUS else False
    )

    operator_actions = _operator_actions(
        classification=classification,
        explicit_mapping=explicit_mapping,
        merged_prs=merged_prs,
        duplicate_pr_risk=duplicate_pr_risk,
        new_pr_needed=new_pr_needed,
    )

    return {
        "command": COMMAND_ISSUE,
        "ok": True,
        "read_only": True,
        "issue": {
            "number": issue.get("number"),
            "title": issue.get("title"),
            "state": issue.get("state"),
            "url": issue.get("url"),
        },
        "classification": classification,
        "reasons": reasons,
        "evidence_signals": {
            "merged_pr_evidence_count": len(merged_prs),
            "explicit_issue_evidence_mapping": explicit_mapping,
            "docs_only_reconciliation": docs_only_reconciliation,
            "duplicate_or_noop_pr_detected": duplicate_pr_risk,
            "historical_or_protected_references_present": _has_historical_or_protected(issue),
            "missing_issue_specific_proof": not explicit_mapping and len(merged_prs) == 0,
        },
        "duplicate_noop_planning": {
            "new_pr_needed": new_pr_needed,
            "recommendation": recommendation,
            "requires_operator_evidence_mapping": bool(merged_prs) and not explicit_mapping,
            "duplicate_pr_risk": duplicate_pr_risk,
            "closeout_ready": closeout_ready,
            "mutation_allowed": False,
        },
        "safety": _safety_fields(),
        "operator_next_actions": operator_actions,
        "boundary_confirmations": _boundaries(),
    }


def check_milestone_evidence_readiness(
    config: AppConfig,
    *,
    parent_issue: int,
    state_file: str | Path | None = None,
) -> dict[str, Any]:
    milestone = inspect_milestone_state(config, parent_issue=parent_issue, state_file=state_file)
    if not milestone.get("ok"):
        return {
            "command": COMMAND_MILESTONE,
            "ok": False,
            "read_only": True,
            "error": "milestone_state_inspection_failed",
            "details": milestone,
            "safety": _safety_fields(),
            "boundary_confirmations": _boundaries(),
        }

    children = milestone.get("child_issues") if isinstance(milestone.get("child_issues"), list) else []
    local_child_issues = _load_local_child_issues(state_file) if state_file is not None else {}
    per_issue: list[dict[str, Any]] = []
    for child in children:
        if not isinstance(child, dict):
            continue
        number = child.get("issue_number")
        if not isinstance(number, int):
            continue
        local_issue = local_child_issues.get(number)
        if isinstance(local_issue, dict):
            issue_result = _check_issue_evidence_readiness_from_issue(local_issue)
        else:
            issue_result = check_issue_evidence_readiness(config, issue_number=number)
        per_issue.append(issue_result)

    status_counts: dict[str, int] = {
        STATE_READY: 0,
        STATE_NOT_READY: 0,
        STATE_AMBIGUOUS: 0,
        STATE_BLOCKED: 0,
        STATE_ALREADY_CLOSED: 0,
    }
    for item in per_issue:
        cls = item.get("classification")
        if isinstance(cls, str) and cls in status_counts:
            status_counts[cls] += 1

    milestone_ready = status_counts[STATE_NOT_READY] == 0 and status_counts[STATE_BLOCKED] == 0
    payload: dict[str, Any] = {
        "command": COMMAND_MILESTONE,
        "ok": True,
        "read_only": True,
        "parent_issue": milestone.get("parent_issue"),
        "child_issue_count": len(per_issue),
        "status_counts": status_counts,
        "milestone_closeout_readiness": {
            "closeout_ready": milestone_ready if status_counts[STATE_AMBIGUOUS] == 0 else "ambiguous",
            "operator_review_required": True,
        },
        "issues": per_issue,
        "safety": _safety_fields(),
        "boundary_confirmations": _boundaries(),
    }
    if state_file is not None:
        payload["inspection_mode"] = "local_state_file"
        payload["state_file"] = str(state_file)
    return payload


def _check_issue_evidence_readiness_from_issue(issue: dict[str, Any]) -> dict[str, Any]:
    classification, reasons = _classify_issue(issue)
    merged_prs = issue.get("merged_pr_evidence") if isinstance(issue.get("merged_pr_evidence"), list) else []
    duplicate_pr_risk = _has_duplicate_or_noop_signals(issue)
    docs_only_reconciliation = _is_docs_only_reconciliation(issue)
    explicit_mapping = _has_explicit_mapping(issue)

    new_pr_needed = _new_pr_needed(
        classification=classification,
        merged_prs=merged_prs,
        docs_only_reconciliation=docs_only_reconciliation,
    )
    recommendation = _recommendation(
        classification=classification,
        merged_prs=merged_prs,
        duplicate_pr_risk=duplicate_pr_risk,
        new_pr_needed=new_pr_needed,
    )
    closeout_ready = True if classification in (STATE_READY, STATE_ALREADY_CLOSED) else (
        "ambiguous" if classification == STATE_AMBIGUOUS else False
    )

    operator_actions = _operator_actions(
        classification=classification,
        explicit_mapping=explicit_mapping,
        merged_prs=merged_prs,
        duplicate_pr_risk=duplicate_pr_risk,
        new_pr_needed=new_pr_needed,
    )

    return {
        "command": COMMAND_ISSUE,
        "ok": True,
        "read_only": True,
        "issue": {
            "number": issue.get("number"),
            "title": issue.get("title"),
            "state": issue.get("state"),
            "url": issue.get("url"),
        },
        "classification": classification,
        "reasons": reasons,
        "evidence_signals": {
            "merged_pr_evidence_count": len(merged_prs),
            "explicit_issue_evidence_mapping": explicit_mapping,
            "docs_only_reconciliation": docs_only_reconciliation,
            "duplicate_or_noop_pr_detected": duplicate_pr_risk,
            "historical_or_protected_references_present": _has_historical_or_protected(issue),
            "missing_issue_specific_proof": not explicit_mapping and len(merged_prs) == 0,
        },
        "duplicate_noop_planning": {
            "new_pr_needed": new_pr_needed,
            "recommendation": recommendation,
            "requires_operator_evidence_mapping": bool(merged_prs) and not explicit_mapping,
            "duplicate_pr_risk": duplicate_pr_risk,
            "closeout_ready": closeout_ready,
            "mutation_allowed": False,
        },
        "safety": _safety_fields(),
        "operator_next_actions": operator_actions,
        "boundary_confirmations": _boundaries(),
    }


def _load_local_child_issues(state_file: str | Path | None) -> dict[int, dict[str, Any]]:
    if state_file is None:
        return {}
    state_path = Path(state_file)
    try:
        parsed = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(parsed, dict):
        return {}
    child_issues = parsed.get("child_issues")
    if not isinstance(child_issues, list):
        return {}
    issues_by_number: dict[int, dict[str, Any]] = {}
    for item in child_issues:
        if not isinstance(item, dict):
            continue
        number = item.get("number")
        if isinstance(number, int):
            issues_by_number[number] = item
    return issues_by_number


def _classify_issue(issue: dict[str, Any]) -> tuple[str, list[str]]:
    reasons: list[str] = []
    state = issue.get("state")
    if isinstance(state, str) and state.upper() == "CLOSED":
        return STATE_ALREADY_CLOSED, ["issue_state_closed"]

    merged_prs = issue.get("merged_pr_evidence") if isinstance(issue.get("merged_pr_evidence"), list) else []
    explicit_mapping = _has_explicit_mapping(issue)
    mapping_conflict = _has_conflicting_evidence_mapping(issue)
    historical = _has_historical_or_protected(issue)
    lineage_refs = (issue.get("reference_classification") or {}).get("implementation_issue_numbers")
    if not isinstance(lineage_refs, list) or not lineage_refs:
        return STATE_BLOCKED, ["missing_issue_lineage_references"]

    if mapping_conflict:
        return STATE_BLOCKED, ["conflicting_or_ambiguous_structured_evidence_mapping"]

    if merged_prs and explicit_mapping:
        reasons.extend(["merged_pr_evidence_present", "explicit_issue_mapping_present"])
        if _is_docs_only_reconciliation(issue):
            reasons.append("docs_only_reconciliation_detected")
        if _has_duplicate_or_noop_signals(issue):
            reasons.append("duplicate_or_noop_reference_detected")
        return STATE_READY, reasons

    if historical and not merged_prs:
        return STATE_AMBIGUOUS, ["historical_or_protected_reference_present", "missing_merged_pr_evidence"]

    if not merged_prs:
        return STATE_NOT_READY, ["missing_merged_pr_evidence"]

    return STATE_AMBIGUOUS, ["merged_pr_present_without_explicit_issue_mapping"]


def _has_explicit_mapping(issue: dict[str, Any]) -> bool:
    body = issue.get("body")
    if isinstance(body, str) and _MAPPING_PATTERN.search(body):
        return True
    mapping = issue.get("evidence_mapping_analysis")
    if isinstance(mapping, dict) and bool(mapping.get("issue_specific_mapping_detected")):
        return True
    refs = (issue.get("reference_classification") or {}).get("explicit_implementation_issue_numbers")
    return isinstance(refs, list) and len(refs) > 0


def _has_conflicting_evidence_mapping(issue: dict[str, Any]) -> bool:
    mapping = issue.get("evidence_mapping_analysis")
    if not isinstance(mapping, dict):
        return False
    return bool(
        mapping.get("conflicting_structured_blocks_detected")
        or mapping.get("duplicate_structured_blocks_detected")
        or (mapping.get("malformed_structured_blocks_detected") or 0) > 0
    )


def _has_historical_or_protected(issue: dict[str, Any]) -> bool:
    refs = issue.get("reference_classification")
    if not isinstance(refs, dict):
        return False
    safety = refs.get("safety_or_historical_issue_numbers")
    if isinstance(safety, list) and safety:
        return True
    return bool(refs.get("contains_protected_issue_implementation_link"))


def _has_duplicate_or_noop_signals(issue: dict[str, Any]) -> bool:
    title = issue.get("title")
    body = issue.get("body")
    title_text = title if isinstance(title, str) else ""
    body_text = body if isinstance(body, str) else ""
    return bool(_DUPLICATE_PATTERN.search(title_text) or _DUPLICATE_PATTERN.search(body_text))


def _is_docs_only_reconciliation(issue: dict[str, Any]) -> bool:
    title = issue.get("title")
    body = issue.get("body")
    text = f"{title or ''}\n{body or ''}"
    return bool(_DOCS_ONLY_PATTERN.search(text))


def _new_pr_needed(*, classification: str, merged_prs: list[dict[str, Any]], docs_only_reconciliation: bool) -> bool:
    if merged_prs:
        return False
    if classification == STATE_ALREADY_CLOSED:
        return False
    if docs_only_reconciliation and classification in (STATE_READY, STATE_AMBIGUOUS):
        return False
    return classification in (STATE_NOT_READY, STATE_BLOCKED)


def _recommendation(
    *, classification: str, merged_prs: list[dict[str, Any]], duplicate_pr_risk: bool, new_pr_needed: bool
) -> str:
    if merged_prs:
        return "reuse_existing_pr_evidence"
    if duplicate_pr_risk and not new_pr_needed:
        return "avoid_duplicate_pr_reuse_existing_evidence"
    if classification == STATE_BLOCKED:
        return "resolve_lineage_or_evidence_gaps_before_new_pr"
    return "collect_issue_specific_evidence_before_closeout"


def _operator_actions(
    *,
    classification: str,
    explicit_mapping: bool,
    merged_prs: list[dict[str, Any]],
    duplicate_pr_risk: bool,
    new_pr_needed: bool,
) -> list[str]:
    actions: list[str] = []
    if not explicit_mapping:
        actions.append("Add explicit issue-specific evidence mapping in issue or PR traceability notes.")
    if not merged_prs:
        actions.append("Capture or link merged PR evidence for this issue before closeout consideration.")
    if duplicate_pr_risk:
        actions.append("Review duplicate/no-op signals and reuse valid merged PR evidence instead of opening a duplicate PR.")
    if not new_pr_needed:
        actions.append("Do not create a new PR for this issue unless evidence mapping proves a true gap.")
    if classification in (STATE_AMBIGUOUS, STATE_BLOCKED):
        actions.append("Run human review to resolve ambiguous or blocked evidence lineage before closeout.")
    if not actions:
        actions.append("Proceed with human closeout review using existing evidence; no mutation is performed by this command.")
    return actions


def _error_payload(command: str, details_payload: dict[str, Any], *, issue_number: int) -> dict[str, Any]:
    return {
        "command": command,
        "ok": False,
        "read_only": True,
        "error": details_payload.get("error", "issue_lookup_failed"),
        "issue": issue_number,
        "details": details_payload.get("details"),
        "safety": _safety_fields(),
        "boundary_confirmations": _boundaries(),
    }


def _safety_fields() -> dict[str, Any]:
    return {
        "read_only": True,
        "close_issues": False,
        "create_pr": False,
        "comment_on_issue": False,
        "mutation_allowed": False,
        "operator_review_required": True,
    }


def _boundaries() -> list[str]:
    return [
        "read_only: true",
        "close_issues: false",
        "create_pr: false",
        "comment_on_issue: false",
        "mutation_allowed: false",
        "operator_review_required: true",
        "Evidence checking and duplicate/no-op prevention are recommendation-only.",
    ]

