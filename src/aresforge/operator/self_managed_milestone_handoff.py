from __future__ import annotations

import subprocess
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.milestone_dashboard import inspect_milestone_dashboard
from aresforge.operator.milestone_state_inspector import inspect_milestone_state

COMMAND_NAME = "generate-self-managed-milestone-handoff"


def generate_self_managed_milestone_handoff(
    config: AppConfig,
    *,
    parent_issue: int,
    completed_child: int,
    next_child: int | None = None,
    pr_url: str | None = None,
    validation_results: list[str] | None = None,
    evidence_comment_url: str | None = None,
    warning: list[str] | None = None,
) -> dict[str, Any]:
    milestone_state = inspect_milestone_state(config, parent_issue=parent_issue)
    if not milestone_state.get("ok"):
        return {
            "command": COMMAND_NAME,
            "ok": False,
            "read_only": True,
            "error": "milestone_state_inspection_failed",
            "details": milestone_state,
            "boundary_confirmations": _boundaries(),
        }

    dashboard = inspect_milestone_dashboard(config, parent_issue=parent_issue)
    if not dashboard.get("ok"):
        return {
            "command": COMMAND_NAME,
            "ok": False,
            "read_only": True,
            "error": "milestone_dashboard_inspection_failed",
            "details": dashboard,
            "boundary_confirmations": _boundaries(),
        }

    child_issues = milestone_state.get("child_issues") if isinstance(milestone_state.get("child_issues"), list) else []
    child_map: dict[int, dict[str, Any]] = {
        item["issue_number"]: item
        for item in child_issues
        if isinstance(item, dict) and isinstance(item.get("issue_number"), int)
    }
    if completed_child not in child_map:
        return {
            "command": COMMAND_NAME,
            "ok": False,
            "read_only": True,
            "error": "completed_child_not_in_parent_lineage",
            "parent_issue": parent_issue,
            "completed_child": completed_child,
            "boundary_confirmations": _boundaries(),
        }

    derived_next = _derive_next_child(
        child_issues=child_issues,
        explicit_next=next_child,
        completed_child=completed_child,
    )
    final_reconciliation = (((dashboard.get("final_reconciliation") or {}).get("final_reconciliation_issue") or {}).get("issue_number"))
    open_children = [
        item.get("issue_number")
        for item in child_issues
        if isinstance(item, dict) and str(item.get("state", "")).upper() == "OPEN"
    ]

    payload = {
        "schema_version": "m21.handoff.v1",
        "parent_issue": {
            "number": parent_issue,
            "state": (milestone_state.get("parent_issue") or {}).get("state"),
            "url": (milestone_state.get("parent_issue") or {}).get("url"),
        },
        "completed_child": {
            "issue_number": completed_child,
            "state": child_map[completed_child].get("state"),
            "title": child_map[completed_child].get("title"),
            "url": child_map[completed_child].get("url"),
        },
        "next_child": {
            "issue_number": derived_next,
            "is_final_reconciliation": isinstance(final_reconciliation, int) and derived_next == final_reconciliation,
        },
        "current_main_head": _current_main_head(config),
        "pr_url": pr_url,
        "validation_results": list(validation_results or []),
        "evidence_comment_url": evidence_comment_url,
        "child_state_snapshot": [
            {
                "issue_number": item.get("issue_number"),
                "state": item.get("state"),
                "title": item.get("title"),
            }
            for item in child_issues
            if isinstance(item, dict)
        ],
        "known_warnings": sorted(set(list(dashboard.get("warnings") or []) + list(warning or []))),
        "exact_next_recommended_commands": _next_commands(
            parent_issue=parent_issue,
            completed_child=completed_child,
            next_child=derived_next,
        ),
        "safety_state": {
            "read_only": True,
            "dry_run_default_preserved": True,
            "mutation_requires_explicit_approval": True,
            "targeted_scope_only": True,
            "bulk_closeout_forbidden": True,
            "parent_closeout_blocked_while_children_open": bool(open_children),
            "open_children": open_children,
        },
        "parent_status_note": (
            f"Parent issue #{parent_issue} remains OPEN until children are closed/accounted for and readiness checks pass."
        ),
    }

    return {
        "command": COMMAND_NAME,
        "ok": True,
        "read_only": True,
        "parent_issue": parent_issue,
        "completed_child": completed_child,
        "next_child": derived_next,
        "package": payload,
        "boundary_confirmations": _boundaries(),
    }


def _derive_next_child(*, child_issues: list[dict[str, Any]], explicit_next: int | None, completed_child: int) -> int | None:
    if isinstance(explicit_next, int):
        return explicit_next
    found_completed = False
    for item in child_issues:
        if not isinstance(item, dict):
            continue
        number = item.get("issue_number")
        state = str(item.get("state", "")).upper()
        if number == completed_child:
            found_completed = True
            continue
        if found_completed and isinstance(number, int) and state == "OPEN":
            return number
    open_children = [
        item.get("issue_number")
        for item in child_issues
        if isinstance(item, dict) and isinstance(item.get("issue_number"), int) and str(item.get("state", "")).upper() == "OPEN"
    ]
    return min(open_children) if open_children else None


def _current_main_head(config: AppConfig) -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(config.repo_root),
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def _next_commands(*, parent_issue: int, completed_child: int, next_child: int | None) -> list[str]:
    commands = [
        f"python -m aresforge inspect-milestone-dashboard --parent-issue {parent_issue}",
        f"python -m aresforge inspect-milestone-state --parent-issue {parent_issue}",
        (
            "python -m aresforge "
            f"generate-self-managed-milestone-handoff --parent-issue {parent_issue} "
            f"--completed-child {completed_child}"
            + (f" --next-child {next_child}" if isinstance(next_child, int) else "")
        ),
    ]
    if isinstance(next_child, int):
        commands.extend(
            [
                (
                    "python -m aresforge run-sequential-child-closeout-flow "
                    f"--parent-issue {parent_issue} --child-issue {next_child} "
                    "--comment-body \"M21 child evidence draft\""
                ),
                (
                    "python -m aresforge generate-sequential-closeout-execution-package "
                    f"--parent-issue {parent_issue} --child-issue {next_child}"
                ),
            ]
        )
    return commands


def _boundaries() -> list[str]:
    return [
        "read_only: true",
        "dry_run_default_preserved: true",
        "No GitHub mutation was performed.",
        "No issues were closed.",
        "No pull requests were created or merged.",
        "No comments were added.",
    ]
