from __future__ import annotations

from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.evidence_completeness_checker import check_milestone_evidence_readiness
from aresforge.operator.milestone_execution_queue_planner import plan_milestone_execution_queue
from aresforge.operator.milestone_reconciliation_planner import plan_milestone_final_reconciliation
from aresforge.operator.milestone_state_inspector import inspect_milestone_state

COMMAND_NAME = "inspect-milestone-dashboard"
_ACCOUNTED_CLASSIFICATIONS = {"ready", "already_closed"}


def inspect_milestone_dashboard(config: AppConfig, *, parent_issue: int) -> dict[str, Any]:
    milestone_state = inspect_milestone_state(config, parent_issue=parent_issue)
    execution_queue = plan_milestone_execution_queue(config, parent_issue=parent_issue)
    evidence_readiness = check_milestone_evidence_readiness(config, parent_issue=parent_issue)
    final_reconciliation = plan_milestone_final_reconciliation(config, parent_issue=parent_issue)

    failures = _collect_failures(
        milestone_state=milestone_state,
        execution_queue=execution_queue,
        evidence_readiness=evidence_readiness,
        final_reconciliation=final_reconciliation,
    )
    if failures:
        return {
            "command": COMMAND_NAME,
            "ok": False,
            "read_only": True,
            "parent_issue": parent_issue,
            "error": "dashboard_dependency_failed",
            "failures": failures,
            "warnings": ["One or more read-only dependency commands failed; inspect failures for details."],
            "required_operator_actions": [
                "Resolve dependency command failures before relying on this dashboard for sequencing or closeout planning."
            ],
            "safety_gates": _default_safety_gates(),
            "boundary_confirmations": _boundaries(),
        }

    parent_payload = milestone_state.get("parent_issue")
    child_issues = milestone_state.get("child_issues") if isinstance(milestone_state.get("child_issues"), list) else []
    child_states = [item for item in child_issues if isinstance(item, dict)]

    issue_classifications = _issue_classifications(evidence_readiness)
    accounted_numbers = _accounted_child_numbers(child_states, issue_classifications)
    open_numbers = _open_child_numbers(child_states)
    closed_numbers = _closed_child_numbers(child_states)
    recommended_next = _recommended_next_child(execution_queue)
    final_issue = final_reconciliation.get("final_reconciliation_issue")

    warnings = _collect_warnings(
        milestone_state=milestone_state,
        execution_queue=execution_queue,
        evidence_readiness=evidence_readiness,
        final_reconciliation=final_reconciliation,
    )
    required_operator_actions = _collect_required_operator_actions(
        execution_queue=execution_queue,
        evidence_readiness=evidence_readiness,
        final_reconciliation=final_reconciliation,
    )
    safety_gates = _collect_safety_gates(execution_queue=execution_queue, final_reconciliation=final_reconciliation)

    return {
        "command": COMMAND_NAME,
        "ok": True,
        "read_only": True,
        "parent_issue": parent_payload,
        "dashboard": {
            "parent_state": parent_payload.get("state") if isinstance(parent_payload, dict) else None,
            "child_issue_count": len(child_states),
            "open_child_issue_count": len(open_numbers),
            "closed_child_issue_count": len(closed_numbers),
            "accounted_for_child_issue_count": len(accounted_numbers),
            "recommended_next_child_issue": recommended_next,
            "final_reconciliation_issue": final_issue,
            "milestone_closeout_ready": (
                evidence_readiness.get("milestone_closeout_readiness") or {}
            ).get("closeout_ready"),
            "parent_should_remain_open": final_reconciliation.get("parent_should_remain_open"),
            "execution_mutation_disabled": True,
            "operator_review_required": True,
        },
        "child_summary": {
            "open_child_issue_numbers": open_numbers,
            "closed_child_issue_numbers": closed_numbers,
            "accounted_for_child_issue_numbers": accounted_numbers,
            "unaccounted_children": final_reconciliation.get("unaccounted_children"),
        },
        "execution_queue": {
            "recommended_order": execution_queue.get("recommended_order"),
            "blocked_items": execution_queue.get("blocked_items"),
            "signals": execution_queue.get("signals"),
        },
        "evidence_readiness": {
            "status_counts": evidence_readiness.get("status_counts"),
            "milestone_closeout_readiness": evidence_readiness.get("milestone_closeout_readiness"),
            "issues": evidence_readiness.get("issues"),
        },
        "final_reconciliation": {
            "final_reconciliation_issue": final_issue,
            "implementation_children": final_reconciliation.get("implementation_children"),
            "unaccounted_children": final_reconciliation.get("unaccounted_children"),
            "ready_for_final_reconciliation": final_reconciliation.get("ready_for_final_reconciliation"),
            "parent_should_remain_open": final_reconciliation.get("parent_should_remain_open"),
            "docs_only_expected": final_reconciliation.get("docs_only_expected"),
        },
        "warnings": warnings,
        "required_operator_actions": required_operator_actions,
        "safety_gates": safety_gates,
        "boundary_confirmations": _collect_boundaries(
            milestone_state=milestone_state,
            execution_queue=execution_queue,
            evidence_readiness=evidence_readiness,
            final_reconciliation=final_reconciliation,
        ),
    }


def _collect_failures(
    *,
    milestone_state: dict[str, Any],
    execution_queue: dict[str, Any],
    evidence_readiness: dict[str, Any],
    final_reconciliation: dict[str, Any],
) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    for name, payload in (
        ("inspect-milestone-state", milestone_state),
        ("plan-milestone-execution-queue", execution_queue),
        ("check-milestone-evidence-readiness", evidence_readiness),
        ("plan-milestone-final-reconciliation", final_reconciliation),
    ):
        if bool(payload.get("ok")):
            continue
        failures.append(
            {
                "command": name,
                "error": payload.get("error", "unknown_error"),
                "details": payload,
            }
        )
    return failures


def _issue_classifications(evidence_readiness: dict[str, Any]) -> dict[int, str]:
    classifications: dict[int, str] = {}
    issues = evidence_readiness.get("issues") if isinstance(evidence_readiness.get("issues"), list) else []
    for item in issues:
        if not isinstance(item, dict):
            continue
        issue = item.get("issue")
        if not isinstance(issue, dict):
            continue
        issue_number = issue.get("number")
        classification = item.get("classification")
        if isinstance(issue_number, int) and isinstance(classification, str):
            classifications[issue_number] = classification
    return classifications


def _open_child_numbers(child_states: list[dict[str, Any]]) -> list[int]:
    numbers: list[int] = []
    for item in child_states:
        issue_number = item.get("issue_number")
        state = item.get("state")
        if isinstance(issue_number, int) and isinstance(state, str) and state.upper() == "OPEN":
            numbers.append(issue_number)
    return sorted(numbers)


def _closed_child_numbers(child_states: list[dict[str, Any]]) -> list[int]:
    numbers: list[int] = []
    for item in child_states:
        issue_number = item.get("issue_number")
        state = item.get("state")
        if isinstance(issue_number, int) and isinstance(state, str) and state.upper() == "CLOSED":
            numbers.append(issue_number)
    return sorted(numbers)


def _accounted_child_numbers(
    child_states: list[dict[str, Any]],
    issue_classifications: dict[int, str],
) -> list[int]:
    numbers: list[int] = []
    for item in child_states:
        issue_number = item.get("issue_number")
        state = item.get("state")
        if not isinstance(issue_number, int):
            continue
        state_text = state.upper() if isinstance(state, str) else ""
        classification = issue_classifications.get(issue_number)
        if state_text == "CLOSED" or classification in _ACCOUNTED_CLASSIFICATIONS:
            numbers.append(issue_number)
    return sorted(numbers)


def _recommended_next_child(execution_queue: dict[str, Any]) -> dict[str, Any] | None:
    recommended_order = execution_queue.get("recommended_order")
    if not isinstance(recommended_order, list):
        return None
    for item in recommended_order:
        if not isinstance(item, dict):
            continue
        if bool(item.get("is_final_reconciliation")):
            continue
        state = item.get("state")
        if isinstance(state, str) and state.upper() == "CLOSED":
            continue
        return {
            "issue_number": item.get("issue_number"),
            "position": item.get("position"),
            "title": item.get("title"),
            "state": item.get("state"),
        }
    return None


def _collect_warnings(
    *,
    milestone_state: dict[str, Any],
    execution_queue: dict[str, Any],
    evidence_readiness: dict[str, Any],
    final_reconciliation: dict[str, Any],
) -> list[str]:
    warnings: list[str] = []
    source_warnings = milestone_state.get("warnings")
    if isinstance(source_warnings, list):
        warnings.extend(item for item in source_warnings if isinstance(item, str))

    blocked_items = execution_queue.get("blocked_items")
    if isinstance(blocked_items, list):
        for item in blocked_items:
            if not isinstance(item, dict):
                continue
            issue_number = item.get("issue_number")
            reason = item.get("reason")
            if isinstance(issue_number, int) and isinstance(reason, str):
                warnings.append(f"Queue blocker for issue #{issue_number}: {reason}")

    not_ready_numbers = _not_ready_issue_numbers(evidence_readiness)
    if not_ready_numbers:
        warnings.append(
            "Evidence not closeout-ready for issues: "
            + ", ".join(str(issue_number) for issue_number in sorted(not_ready_numbers))
        )

    unaccounted_children = final_reconciliation.get("unaccounted_children")
    if isinstance(unaccounted_children, list) and unaccounted_children:
        unaccounted_numbers = sorted(
            item.get("issue_number")
            for item in unaccounted_children
            if isinstance(item, dict) and isinstance(item.get("issue_number"), int)
        )
        if unaccounted_numbers:
            warnings.append(
                "Final reconciliation is blocked by unaccounted implementation children: "
                + ", ".join(str(issue_number) for issue_number in unaccounted_numbers)
            )

    return sorted(set(warnings))


def _not_ready_issue_numbers(evidence_readiness: dict[str, Any]) -> list[int]:
    numbers: list[int] = []
    issues = evidence_readiness.get("issues") if isinstance(evidence_readiness.get("issues"), list) else []
    for item in issues:
        if not isinstance(item, dict):
            continue
        issue = item.get("issue")
        if not isinstance(issue, dict):
            continue
        issue_number = issue.get("number")
        classification = item.get("classification")
        if isinstance(issue_number, int) and classification in {"not_ready", "ambiguous", "blocked"}:
            numbers.append(issue_number)
    return numbers


def _collect_required_operator_actions(
    *,
    execution_queue: dict[str, Any],
    evidence_readiness: dict[str, Any],
    final_reconciliation: dict[str, Any],
) -> list[str]:
    actions: list[str] = []
    for source in (
        execution_queue.get("required_operator_actions"),
        final_reconciliation.get("required_operator_actions"),
    ):
        if isinstance(source, list):
            actions.extend(item for item in source if isinstance(item, str))

    not_ready_numbers = sorted(set(_not_ready_issue_numbers(evidence_readiness)))
    if not_ready_numbers:
        actions.append(
            "Collect or link merged PR evidence before closeout for issues: "
            + ", ".join(str(issue_number) for issue_number in not_ready_numbers)
            + "."
        )

    return sorted(set(actions))


def _collect_safety_gates(*, execution_queue: dict[str, Any], final_reconciliation: dict[str, Any]) -> dict[str, Any]:
    queue_safety = execution_queue.get("safety_gates") if isinstance(execution_queue.get("safety_gates"), dict) else {}
    return {
        "execution_enabled": bool(queue_safety.get("execution_enabled")),
        "close_issues": False,
        "bulk_closeout_allowed": bool(queue_safety.get("bulk_closeout_allowed")),
        "create_pr": False,
        "comment_on_issue": False,
        "mutation_allowed": False,
        "operator_review_required": bool(
            queue_safety.get("operator_review_required")
            or final_reconciliation.get("operator_review_required")
            or True
        ),
        "parent_closeout_allowed": bool(queue_safety.get("parent_closeout_allowed")),
        "parent_should_remain_open": bool(final_reconciliation.get("parent_should_remain_open")),
    }


def _collect_boundaries(
    *,
    milestone_state: dict[str, Any],
    execution_queue: dict[str, Any],
    evidence_readiness: dict[str, Any],
    final_reconciliation: dict[str, Any],
) -> list[str]:
    lines: set[str] = set(_boundaries())
    for source in (
        milestone_state.get("boundary_confirmations"),
        execution_queue.get("boundary_confirmations"),
        evidence_readiness.get("boundary_confirmations"),
        final_reconciliation.get("boundary_confirmations"),
    ):
        if not isinstance(source, list):
            continue
        for item in source:
            if isinstance(item, str):
                lines.add(item)
    return sorted(lines)


def _default_safety_gates() -> dict[str, Any]:
    return {
        "execution_enabled": False,
        "close_issues": False,
        "bulk_closeout_allowed": False,
        "create_pr": False,
        "comment_on_issue": False,
        "mutation_allowed": False,
        "operator_review_required": True,
        "parent_closeout_allowed": False,
        "parent_should_remain_open": True,
    }


def _boundaries() -> list[str]:
    return [
        "read_only: true",
        "close_issues: false",
        "create_pr: false",
        "comment_on_issue: false",
        "mutation_allowed: false",
        "operator_review_required: true",
        "Dashboard is read-only and performs no GitHub mutation.",
        "No issues were closed, no PRs were created, and no comments were added.",
    ]