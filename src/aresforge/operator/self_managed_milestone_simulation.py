from __future__ import annotations

from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.milestone_dashboard import inspect_milestone_dashboard
from aresforge.operator.milestone_state_inspector import inspect_milestone_state
from aresforge.operator.self_managed_milestone_execution_contract import (
    inspect_self_managed_milestone_execution_contract,
)

COMMAND_NAME = "simulate-self-managed-milestone-execution"


def simulate_self_managed_milestone_execution(config: AppConfig, *, parent_issue: int) -> dict[str, Any]:
    contract = inspect_self_managed_milestone_execution_contract(config)
    milestone_state = inspect_milestone_state(config, parent_issue=parent_issue)
    dashboard = inspect_milestone_dashboard(config, parent_issue=parent_issue)

    if not bool(contract.get("ok")):
        return _dependency_error(parent_issue=parent_issue, dependency="execution_contract", details=contract)
    if not bool(milestone_state.get("ok")):
        return _dependency_error(parent_issue=parent_issue, dependency="milestone_state", details=milestone_state)
    if not bool(dashboard.get("ok")):
        return _dependency_error(parent_issue=parent_issue, dependency="milestone_dashboard", details=dashboard)

    child_issues = milestone_state.get("child_issues") if isinstance(milestone_state.get("child_issues"), list) else []
    normalized_children = [item for item in child_issues if isinstance(item, dict)]
    ordered_children = sorted(
        [
            item
            for item in normalized_children
            if isinstance(item.get("issue_number"), int)
        ],
        key=lambda item: int(item["issue_number"]),
    )
    closed_children = [
        int(item["issue_number"])
        for item in ordered_children
        if str(item.get("state", "")).upper() == "CLOSED"
    ]
    open_children = [
        int(item["issue_number"])
        for item in ordered_children
        if str(item.get("state", "")).upper() == "OPEN"
    ]
    next_open_child = _recommended_next_child(dashboard)
    final_reconciliation = _final_reconciliation_issue(dashboard)

    return {
        "command": COMMAND_NAME,
        "ok": True,
        "read_only": True,
        "parent_issue": parent_issue,
        "simulation_mode": "dry_run_only",
        "inputs": {
            "parent_issue": parent_issue,
            "child_discovery_count": len(ordered_children),
            "child_issue_numbers": [int(item["issue_number"]) for item in ordered_children],
        },
        "child_discovery": {
            "open_child_issue_numbers": open_children,
            "closed_child_issue_numbers": closed_children,
            "next_open_child_issue": next_open_child,
            "final_reconciliation_issue": final_reconciliation,
        },
        "sequential_plan": {
            "ordered_child_issue_numbers": [int(item["issue_number"]) for item in ordered_children],
            "final_reconciliation_last_enforced": bool(
                ((dashboard.get("execution_queue") or {}).get("signals") or {}).get("final_reconciliation_last_enforced")
            ),
            "recommended_next_child_issue": next_open_child,
        },
        "per_child_validation_envelope": {
            "required_validation_commands": _required_validation_commands(parent_issue=parent_issue, child_issue=next_open_child),
        },
        "mutation_plan": {
            "comment_plan": {
                "target_issue": next_open_child,
                "mode": "dry_run_planning_only",
                "bulk_closeout_allowed": False,
            },
            "closeout_plan": {
                "target_issue": next_open_child,
                "mode": "dry_run_planning_only",
                "bulk_closeout_allowed": False,
                "parent_target_forbidden": True,
            },
        },
        "handoff_plan": {
            "command_template": _handoff_command(parent_issue=parent_issue, completed_children=closed_children, next_child=next_open_child),
            "completed_child_detected": closed_children[-1] if closed_children else None,
            "next_child": next_open_child,
        },
        "parent_closeout_plan": {
            "blocked_until_children_accounted_for": True,
            "parent_closeout_ready": bool(((dashboard.get("dashboard") or {}).get("milestone_closeout_ready"))),
            "blocked_reasons": _parent_blocked_reasons(open_children=open_children),
        },
        "safety_checks": {
            "github_mutation_performed": False,
            "issue_closure_performed": False,
            "bulk_closeout_path_generated": False,
            "dry_run_default_preserved": True,
            "targeted_scope_only": True,
        },
        "boundary_confirmations": [
            "Simulation is read-only and dry-run only.",
            "No GitHub mutation was performed.",
            "No issue was closed.",
            "No bulk closeout path was generated.",
            "Parent closeout remains blocked until children are closed/accounted for.",
        ],
    }


def _required_validation_commands(*, parent_issue: int, child_issue: int | None) -> list[str]:
    commands = [
        "git diff --check",
        "python -m pytest",
        "python -m aresforge inspect-repo-governance",
        f"python -m aresforge inspect-milestone-dashboard --parent-issue {parent_issue}",
        f"python -m aresforge inspect-milestone-state --parent-issue {parent_issue}",
        "python -m aresforge inspect-self-managed-milestone-execution-contract",
    ]
    if isinstance(child_issue, int):
        commands.extend(
            [
                (
                    "python -m aresforge run-sequential-child-closeout-flow "
                    f"--parent-issue {parent_issue} --child-issue {child_issue} "
                    "--comment-body \"M21 child evidence draft\""
                ),
                (
                    "python -m aresforge generate-sequential-closeout-execution-package "
                    f"--parent-issue {parent_issue} --child-issue {child_issue}"
                ),
            ]
        )
    return commands


def _recommended_next_child(dashboard: dict[str, Any]) -> int | None:
    candidate = ((dashboard.get("dashboard") or {}).get("recommended_next_child_issue")) or {}
    value = candidate.get("issue_number") if isinstance(candidate, dict) else None
    return value if isinstance(value, int) else None


def _final_reconciliation_issue(dashboard: dict[str, Any]) -> int | None:
    final_issue = ((dashboard.get("dashboard") or {}).get("final_reconciliation_issue")) or {}
    value = final_issue.get("issue_number") if isinstance(final_issue, dict) else None
    return value if isinstance(value, int) else None


def _handoff_command(*, parent_issue: int, completed_children: list[int], next_child: int | None) -> str | None:
    if not completed_children:
        return None
    command = (
        "python -m aresforge generate-self-managed-milestone-handoff "
        f"--parent-issue {parent_issue} --completed-child {completed_children[-1]}"
    )
    if isinstance(next_child, int):
        command += f" --next-child {next_child}"
    return command


def _parent_blocked_reasons(*, open_children: list[int]) -> list[str]:
    reasons = []
    if open_children:
        reasons.append(
            "open_or_unaccounted_children_remaining: " + ", ".join(str(number) for number in open_children)
        )
    return reasons


def _dependency_error(*, parent_issue: int, dependency: str, details: dict[str, Any]) -> dict[str, Any]:
    return {
        "command": COMMAND_NAME,
        "ok": False,
        "read_only": True,
        "parent_issue": parent_issue,
        "error": "simulation_dependency_failed",
        "dependency": dependency,
        "details": details,
        "boundary_confirmations": [
            "Simulation is read-only and performed no GitHub mutation.",
            "No issue was closed.",
        ],
    }
