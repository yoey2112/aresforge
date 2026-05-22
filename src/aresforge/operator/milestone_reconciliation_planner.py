from __future__ import annotations

import re
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.evidence_completeness_checker import (
    STATE_ALREADY_CLOSED,
    STATE_READY,
    check_issue_evidence_readiness,
    check_milestone_evidence_readiness,
)
from aresforge.operator.milestone_state_inspector import inspect_milestone_state
from aresforge.operator.ready_issue_intake import fetch_issue_details

COMMAND_NAME = "plan-milestone-final-reconciliation"

_DOCS_ONLY_PATTERN = re.compile(r"\bdocs[- ]only\b|\bdocumentation\b|\breconciliation\b", re.IGNORECASE)
_FINAL_RECONCILIATION_PATTERN = re.compile(r"source[- ]of[- ]truth|reconciliation", re.IGNORECASE)

_DOCS_LIKELY_REQUIRED = [
    "docs/context/BUILD_STATE.md",
    "docs/context/AGENT_CONTEXT.md",
    "docs/roadmap/ROADMAP.md",
    "docs/operator/LOCAL_OPERATOR_USAGE.md",
    "docs/architecture/RUNNABLE_SKELETON.md",
    "docs/architecture/MILESTONE_EXECUTION_PLAN_CONTRACT.md",
]


def plan_milestone_final_reconciliation(config: AppConfig, *, parent_issue: int) -> dict[str, Any]:
    milestone = inspect_milestone_state(config, parent_issue=parent_issue)
    if not milestone.get("ok"):
        return {
            "command": COMMAND_NAME,
            "ok": False,
            "read_only": True,
            "error": "milestone_state_inspection_failed",
            "details": milestone,
            "parent_issue": {"issue_number": parent_issue},
            "close_issues": False,
            "create_pr": False,
            "comment_on_issue": False,
            "mutation_allowed": False,
            "operator_review_required": True,
            "boundary_confirmations": _boundaries(),
        }

    parent = milestone.get("parent_issue") if isinstance(milestone.get("parent_issue"), dict) else {}
    child_issues = milestone.get("child_issues") if isinstance(milestone.get("child_issues"), list) else []
    normalized_children = [item for item in child_issues if isinstance(item, dict)]

    final_issue = _detect_final_reconciliation_issue(normalized_children)
    implementation_children = _implementation_children(normalized_children, final_issue)
    per_issue_readiness = _collect_issue_readiness(config, implementation_children)
    unaccounted_children = _collect_unaccounted_children(implementation_children, per_issue_readiness)
    final_issue_last = _final_issue_is_last(normalized_children, final_issue)
    milestone_evidence = check_milestone_evidence_readiness(config, parent_issue=parent_issue)

    parent_state = parent.get("state") if isinstance(parent.get("state"), str) else None
    final_issue_complete = _final_issue_complete(final_issue)
    docs_only_expected = _docs_only_expected(config, final_issue)
    ready_for_final_reconciliation = bool(final_issue and not unaccounted_children and final_issue_last)
    parent_should_remain_open = not final_issue_complete

    return {
        "command": COMMAND_NAME,
        "ok": True,
        "read_only": True,
        "inspection_mode": "github_read_only",
        "repo": f"{config.github_owner}/{config.github_repo}",
        "parent_issue": parent,
        "final_reconciliation_issue": final_issue,
        "implementation_children": implementation_children,
        "unaccounted_children": unaccounted_children,
        "docs_likely_required": list(_DOCS_LIKELY_REQUIRED),
        "docs_only_expected": docs_only_expected,
        "ready_for_final_reconciliation": ready_for_final_reconciliation,
        "parent_should_remain_open": parent_should_remain_open,
        "close_issues": False,
        "create_pr": False,
        "comment_on_issue": False,
        "mutation_allowed": False,
        "operator_review_required": True,
        "safety_signals": {
            "no_generated_evidence_artifact_changes_expected": True,
            "final_reconciliation_should_be_last": final_issue_last,
            "parent_state": parent_state,
            "duplicate_or_noop_risk_signals": _duplicate_noop_signals(per_issue_readiness),
        },
        "evidence_mapping_expectations": {
            "schema_orientation": "reference_classification.explicit_implementation_issue_numbers",
            "required_issue_fields": [
                "issue.number",
                "issue.state",
                "reference_classification.implementation_issue_numbers",
                "reference_classification.explicit_implementation_issue_numbers",
                "merged_pr_evidence",
            ],
            "milestone_readiness_summary": {
                "ok": bool(milestone_evidence.get("ok")),
                "status_counts": milestone_evidence.get("status_counts"),
            },
        },
        "required_operator_actions": _required_operator_actions(
            final_issue=final_issue,
            unaccounted_children=unaccounted_children,
            final_issue_last=final_issue_last,
            docs_only_expected=docs_only_expected,
        ),
        "boundary_confirmations": _boundaries(),
    }


def _detect_final_reconciliation_issue(child_issues: list[dict[str, Any]]) -> dict[str, Any] | None:
    final_candidates: list[dict[str, Any]] = []
    for item in child_issues:
        issue_number = item.get("issue_number")
        title = item.get("title")
        title_text = title.lower() if isinstance(title, str) else ""
        if issue_number == 276 or _FINAL_RECONCILIATION_PATTERN.search(title_text):
            final_candidates.append(item)
    if not final_candidates:
        return None
    final_candidates.sort(key=lambda issue: int(issue.get("issue_number", 0)))
    selected = final_candidates[-1]
    return {
        "issue_number": selected.get("issue_number"),
        "title": selected.get("title"),
        "state": selected.get("state"),
        "url": selected.get("url"),
        "lineage_detected": bool(selected.get("lineage_detected")),
    }


def _implementation_children(
    child_issues: list[dict[str, Any]], final_issue: dict[str, Any] | None
) -> list[dict[str, Any]]:
    final_number = final_issue.get("issue_number") if isinstance(final_issue, dict) else None
    implementation: list[dict[str, Any]] = []
    for item in child_issues:
        issue_number = item.get("issue_number")
        if not isinstance(issue_number, int):
            continue
        if final_number == issue_number:
            continue
        implementation.append(
            {
                "issue_number": issue_number,
                "title": item.get("title"),
                "state": item.get("state"),
                "lineage_detected": bool(item.get("lineage_detected")),
                "merged_pr_count": item.get("merged_pr_count"),
            }
        )
    implementation.sort(key=lambda child: child["issue_number"])
    return implementation


def _collect_issue_readiness(config: AppConfig, implementation_children: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    readiness: dict[int, dict[str, Any]] = {}
    for child in implementation_children:
        issue_number = child.get("issue_number")
        if not isinstance(issue_number, int):
            continue
        result = check_issue_evidence_readiness(config, issue_number=issue_number)
        readiness[issue_number] = {
            "classification": result.get("classification"),
            "duplicate_noop_planning": result.get("duplicate_noop_planning"),
        }
    return readiness


def _collect_unaccounted_children(
    implementation_children: list[dict[str, Any]],
    per_issue_readiness: dict[int, dict[str, Any]],
) -> list[dict[str, Any]]:
    unaccounted: list[dict[str, Any]] = []
    for child in implementation_children:
        issue_number = child.get("issue_number")
        if not isinstance(issue_number, int):
            continue
        state = child.get("state")
        state_text = state.upper() if isinstance(state, str) else ""
        readiness = per_issue_readiness.get(issue_number, {})
        classification = readiness.get("classification")
        accounted = state_text == "CLOSED" or classification in (STATE_READY, STATE_ALREADY_CLOSED)
        if accounted:
            continue
        unaccounted.append(
            {
                "issue_number": issue_number,
                "state": state,
                "classification": classification,
                "reason": "implementation_child_not_closed_or_not_evidence_accounted",
            }
        )
    return unaccounted


def _final_issue_is_last(child_issues: list[dict[str, Any]], final_issue: dict[str, Any] | None) -> bool:
    if not final_issue:
        return False
    final_number = final_issue.get("issue_number")
    if not isinstance(final_number, int):
        return False
    numbers = sorted(item.get("issue_number") for item in child_issues if isinstance(item.get("issue_number"), int))
    return bool(numbers) and numbers[-1] == final_number


def _final_issue_complete(final_issue: dict[str, Any] | None) -> bool:
    if not final_issue:
        return False
    state = final_issue.get("state")
    return isinstance(state, str) and state.upper() == "CLOSED"


def _docs_only_expected(config: AppConfig, final_issue: dict[str, Any] | None) -> bool:
    if not final_issue:
        return True
    issue_number = final_issue.get("issue_number")
    if not isinstance(issue_number, int):
        return True
    details_payload = fetch_issue_details(config, issue_number)
    issue = details_payload.get("issue") if isinstance(details_payload.get("issue"), dict) else {}
    title = issue.get("title")
    body = issue.get("body")
    title_text = title if isinstance(title, str) else ""
    body_text = body if isinstance(body, str) else ""
    if issue_number == 276:
        return True
    return bool(_DOCS_ONLY_PATTERN.search(title_text) or _DOCS_ONLY_PATTERN.search(body_text))


def _duplicate_noop_signals(per_issue_readiness: dict[int, dict[str, Any]]) -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []
    for issue_number, readiness in sorted(per_issue_readiness.items()):
        planning = readiness.get("duplicate_noop_planning")
        if isinstance(planning, dict) and planning.get("duplicate_pr_risk") is True:
            signals.append(
                {
                    "issue_number": issue_number,
                    "risk": "duplicate_or_noop_pr_risk",
                    "recommendation": planning.get("recommendation"),
                }
            )
    return signals


def _required_operator_actions(
    *,
    final_issue: dict[str, Any] | None,
    unaccounted_children: list[dict[str, Any]],
    final_issue_last: bool,
    docs_only_expected: bool,
) -> list[str]:
    actions: list[str] = []
    if not final_issue:
        actions.append("Create or link a final reconciliation issue before parent closeout planning.")
    if unaccounted_children:
        actions.append("Close or evidence-account all implementation children before final reconciliation.")
    if not final_issue_last:
        actions.append("Keep final reconciliation issue sequenced as the last milestone child.")
    if docs_only_expected:
        actions.append("Keep final reconciliation changes docs-focused and avoid generated evidence artifact churn.")
    actions.append("Keep parent issue open until final reconciliation is merged/accounted and child lineage is complete.")
    actions.append("Do not close issues, create PRs, or comment from this planner output.")
    return actions


def _boundaries() -> list[str]:
    return [
        "read_only: true",
        "close_issues: false",
        "create_pr: false",
        "comment_on_issue: false",
        "mutation_allowed: false",
        "operator_review_required: true",
        "Planner is planning-only and performs no GitHub mutation.",
    ]