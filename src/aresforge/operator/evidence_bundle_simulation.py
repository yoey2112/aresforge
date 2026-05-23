from __future__ import annotations

from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.child_closeout_evidence_bundle import generate_child_closeout_evidence_bundle
from aresforge.operator.milestone_execution_queue_planner import plan_milestone_execution_queue
from aresforge.operator.milestone_state_inspector import inspect_milestone_state
from aresforge.operator.parent_closeout_evidence_bundle import generate_parent_closeout_evidence_bundle
from aresforge.operator.parent_closeout_readiness import inspect_parent_closeout_readiness
from aresforge.operator.validation_summary import ValidationEntryInput, build_validation_summary

COMMAND_NAME = "simulate-evidence-bundle-generation"


def simulate_evidence_bundle_generation(config: AppConfig, *, parent_issue: int) -> dict[str, Any]:
    milestone = inspect_milestone_state(config, parent_issue=parent_issue)
    queue = plan_milestone_execution_queue(config, parent_issue=parent_issue)
    readiness = inspect_parent_closeout_readiness(config, parent_issue=parent_issue)

    failures = _collect_failures(milestone=milestone, queue=queue, readiness=readiness)
    if failures:
        return {
            "command": COMMAND_NAME,
            "ok": False,
            "read_only": True,
            "dry_run": True,
            "parent_issue": parent_issue,
            "error": "simulation_dependency_failed",
            "failures": failures,
            "mutation": _mutation_flags(),
        }

    child_items = milestone.get("child_issues") if isinstance(milestone.get("child_issues"), list) else []
    child_numbers = [
        item.get("issue_number")
        for item in child_items
        if isinstance(item, dict) and isinstance(item.get("issue_number"), int)
    ]
    child_numbers = sorted(set(int(number) for number in child_numbers if isinstance(number, int)))

    child_simulations = _simulate_child_bundles(config, parent_issue=parent_issue, child_numbers=child_numbers)
    parent_blocked = generate_parent_closeout_evidence_bundle(config, parent_issue=parent_issue)
    ready_fixture = _ready_fixture(parent_issue=parent_issue, child_numbers=child_numbers)

    queue_order = queue.get("recommended_order") if isinstance(queue.get("recommended_order"), list) else []
    final_reconciliation_last = _final_reconciliation_last(queue_order)
    pr_simulation = _simulate_pr_body_generation(config, queue_order=queue_order)

    validation_summary = build_validation_summary(
        [
            ValidationEntryInput(command="python -m aresforge inspect-milestone-state", state="pass"),
            ValidationEntryInput(command="python -m aresforge plan-milestone-execution-queue", state="pass"),
            ValidationEntryInput(command="python -m aresforge inspect-parent-closeout-readiness", state="pass"),
        ]
    )

    return {
        "command": COMMAND_NAME,
        "ok": True,
        "read_only": True,
        "dry_run": True,
        "parent_issue": parent_issue,
        "simulation": {
            "multi_child_milestone": len(child_numbers) > 1,
            "final_reconciliation_last": final_reconciliation_last,
            "child_bundle_generation": child_simulations,
            "parent_bundle_blocked_state": {
                "parent_closeout_ready": _extract_parent_ready(parent_blocked),
                "blocked_reasons": _extract_blocked_reasons(parent_blocked),
            },
            "parent_bundle_ready_state_fixture": ready_fixture,
            "pr_body_generation": pr_simulation,
            "validation_summary_reuse": {
                "overall_state": validation_summary.get("overall_state"),
                "summary_lines": validation_summary.get("summary_lines"),
            },
            "final_reconciliation_must_remain_last": True,
        },
        "mutation": _mutation_flags(),
        "safety_notes": [
            "Dry-run simulation only; no issue, PR, or branch mutation executed.",
            "Parent closeout remains a separate targeted operator-approved action.",
            "Final reconciliation issue must remain last in sequential execution order.",
        ],
    }


def _collect_failures(
    *,
    milestone: dict[str, Any],
    queue: dict[str, Any],
    readiness: dict[str, Any],
) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    for name, payload in (
        ("inspect-milestone-state", milestone),
        ("plan-milestone-execution-queue", queue),
        ("inspect-parent-closeout-readiness", readiness),
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


def _simulate_child_bundles(
    config: AppConfig,
    *,
    parent_issue: int,
    child_numbers: list[int],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for issue_number in child_numbers:
        payload = generate_child_closeout_evidence_bundle(
            config,
            parent_issue=parent_issue,
            child_issue=issue_number,
        )
        rows.append(
            {
                "issue_number": issue_number,
                "ok": bool(payload.get("ok")),
                "read_only": bool(payload.get("read_only")),
                "has_evidence_comment_body": isinstance(payload.get("evidence_comment_body"), str),
            }
        )
    return rows


def _final_reconciliation_last(queue_order: list[Any]) -> bool:
    normalized = [item for item in queue_order if isinstance(item, dict)]
    if not normalized:
        return True
    indices = [index for index, item in enumerate(normalized) if item.get("is_final_reconciliation") is True]
    if not indices:
        return True
    return max(indices) == len(normalized) - 1


def _simulate_pr_body_generation(config: AppConfig, *, queue_order: list[Any]) -> dict[str, Any]:
    _ = config
    for item in queue_order:
        if not isinstance(item, dict):
            continue
        issue_number = item.get("issue_number")
        if not isinstance(issue_number, int):
            continue
        return {
            "simulated": True,
            "issue_number": issue_number,
            "read_only": True,
            "generated_sections": [
                "Summary",
                "Issue",
                "Files changed",
                "Validation",
                "Safety posture",
                "Notes/warnings",
            ],
            "targeted_update_guidance": [
                f"python -m aresforge generate-pr-evidence-bundle --issue {issue_number} --pr <PR_NUMBER>",
                "gh pr edit <PR_NUMBER> --body-file artifacts/pr-<PR_NUMBER>-body.md",
            ],
        }
    return {
        "simulated": True,
        "issue_number": None,
        "read_only": True,
        "generated_sections": [
            "Summary",
            "Issue",
            "Files changed",
            "Validation",
            "Safety posture",
            "Notes/warnings",
        ],
        "targeted_update_guidance": [
            "python -m aresforge generate-pr-evidence-bundle --issue <ISSUE_NUMBER> --pr <PR_NUMBER>",
            "gh pr edit <PR_NUMBER> --body-file artifacts/pr-<PR_NUMBER>-body.md",
        ],
        "notes": ["PR body generation simulation fallback used because no issue/PR pair was available."],
    }


def _ready_fixture(*, parent_issue: int, child_numbers: list[int]) -> dict[str, Any]:
    return {
        "parent_issue": parent_issue,
        "child_issue_count": len(child_numbers),
        "parent_closeout_ready": True,
        "blocked_reasons": [],
        "all_children_closed_or_accounted_for": True,
        "final_reconciliation_complete": True,
    }


def _extract_parent_ready(payload: dict[str, Any]) -> bool:
    readiness = payload.get("readiness_gates") if isinstance(payload.get("readiness_gates"), dict) else {}
    return readiness.get("parent_closeout_ready") is True


def _extract_blocked_reasons(payload: dict[str, Any]) -> list[str]:
    readiness = payload.get("readiness_gates") if isinstance(payload.get("readiness_gates"), dict) else {}
    reasons = readiness.get("blocked_reasons") if isinstance(readiness.get("blocked_reasons"), list) else []
    return [item for item in reasons if isinstance(item, str)]


def _mutation_flags() -> dict[str, Any]:
    return {
        "attempted": False,
        "issue_mutation": False,
        "pr_mutation": False,
        "branch_mutation": False,
        "allowed_by_default": False,
    }