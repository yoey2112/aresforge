from __future__ import annotations

from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.github_issue_close_executor import execute_github_issue_close
from aresforge.operator.github_issue_comment_executor import execute_github_issue_comment
from aresforge.operator.github_mutation_planner import plan_github_mutation
from aresforge.operator.milestone_state_inspector import inspect_milestone_state

COMMAND_NAME = "run-sequential-child-closeout-flow"


def run_sequential_child_closeout_flow(
    config: AppConfig,
    *,
    parent_issue: int,
    child_issue: int,
    comment_body: str,
    execute: bool = False,
    approval_marker: str | None = None,
) -> dict[str, Any]:
    inspection = inspect_milestone_state(config, parent_issue=parent_issue)
    blocked_reasons: list[str] = []

    if not inspection.get("ok"):
        blocked_reasons.append("milestone_state_inspection_failed")

    children = inspection.get("child_issues") if isinstance(inspection.get("child_issues"), list) else []
    child_map: dict[int, dict[str, Any]] = {}
    for item in children:
        if not isinstance(item, dict):
            continue
        number = item.get("issue_number")
        if isinstance(number, int):
            child_map[number] = item

    if child_issue == parent_issue:
        blocked_reasons.append("parent_target_forbidden_for_child_closeout_flow")

    if child_issue not in child_map:
        blocked_reasons.append("target_issue_not_discovered_as_parent_child")

    target_state = (child_map.get(child_issue) or {}).get("state")
    if isinstance(target_state, str) and target_state.upper() == "CLOSED":
        blocked_reasons.append("target_child_already_closed")

    if execute and not approval_marker:
        blocked_reasons.append("approval_marker_required_for_execution")

    comment_plan = plan_github_mutation(
        config=config,
        mutation_type="issue_comment",
        planned_action=f"Post M21 child closeout evidence comment for #{child_issue}",
        target_issue=child_issue,
        approval_marker=approval_marker,
    )
    close_plan = plan_github_mutation(
        config=config,
        mutation_type="issue_close",
        planned_action=f"Close M21 child issue #{child_issue} after evidence comment",
        target_issue=child_issue,
        approval_marker=approval_marker,
    )

    dry_run = not execute
    comment_result: dict[str, Any] | None = None
    close_result: dict[str, Any] | None = None

    if execute and not blocked_reasons:
        comment_result = execute_github_issue_comment(
            config,
            issue_number=child_issue,
            comment_body=comment_body,
            execute=True,
            parent_issue=parent_issue,
            allow_parent_target=False,
            approval_marker=approval_marker,
        )
        if not comment_result.get("ok"):
            blocked_reasons.append("targeted_comment_execution_failed")
        else:
            close_result = execute_github_issue_close(
                config,
                issue_target=str(child_issue),
                parent_issue=parent_issue,
                execute=True,
                approval_marker=approval_marker,
            )
            if not close_result.get("ok"):
                blocked_reasons.append("targeted_child_close_execution_failed")

    return {
        "command": COMMAND_NAME,
        "ok": len(blocked_reasons) == 0,
        "mode": "execute" if execute else "dry_run",
        "parent_issue": parent_issue,
        "target_child_issue": child_issue,
        "dry_run": {
            "active": dry_run,
            "summary": "Dry-run mode only. No GitHub mutation was performed." if dry_run else "Execute mode requested.",
        },
        "mutation_plans": {
            "issue_comment": comment_plan,
            "issue_close": close_plan,
        },
        "execution_results": {
            "issue_comment": comment_result,
            "issue_close": close_result,
        },
        "blocked": len(blocked_reasons) > 0,
        "blocked_reasons": sorted(set(blocked_reasons)),
        "safety_checks": {
            "dry_run_default": True,
            "approval_required_for_execution": True,
            "single_child_target_only": True,
            "parent_target_forbidden": True,
            "bulk_closeout_forbidden": True,
        },
        "boundary_confirmations": [
            "Flow is child-targeted only and does not accept bulk targets.",
            "Dry-run remains default.",
            "Execution requires explicit approval marker.",
            "Parent issue closeout is forbidden in this child flow.",
            "No sibling issues are targeted by this flow.",
        ],
    }
