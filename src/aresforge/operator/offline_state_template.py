from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig

COMMAND_NAME = "generate-offline-closeout-state-template"


def generate_offline_closeout_state_template(
    config: AppConfig,
    *,
    parent_issue: int,
    children: str,
    output: str | Path,
    parent_title: str | None = None,
    milestone_title: str | None = None,
    final_main_head: str | None = None,
    final_validation_results: str | None = None,
    force: bool = False,
) -> dict[str, Any]:
    child_numbers = _parse_children(children)
    if not child_numbers:
        return _error(parent_issue=parent_issue, output=output, error="children_required")

    output_path = Path(output)
    if output_path.exists() and not force:
        return _error(
            parent_issue=parent_issue,
            output=output_path,
            error="output_exists",
            details={"path": str(output_path), "hint": "Re-run with --force to overwrite."},
        )

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return _error(
            parent_issue=parent_issue,
            output=output_path,
            error="output_directory_create_failed",
            details={"path": str(output_path.parent), "message": str(exc)},
        )

    payload = _build_template(
        config=config,
        parent_issue=parent_issue,
        child_numbers=child_numbers,
        parent_title=parent_title,
        milestone_title=milestone_title,
        final_main_head=final_main_head,
        final_validation_results=final_validation_results,
    )

    try:
        output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    except OSError as exc:
        return _error(
            parent_issue=parent_issue,
            output=output_path,
            error="output_write_failed",
            details={"path": str(output_path), "message": str(exc)},
        )

    return {
        "command": COMMAND_NAME,
        "ok": True,
        "read_only": False,
        "local_only": True,
        "parent_issue": parent_issue,
        "child_issue_numbers": child_numbers,
        "output": str(output_path),
        "force": force,
        "template_markers": {
            "template_only": True,
            "editable_local_artifact": True,
        },
        "boundary_confirmations": _boundaries(),
    }


def _parse_children(raw: str) -> list[int]:
    numbers: list[int] = []
    seen: set[int] = set()
    for item in raw.split(","):
        token = item.strip()
        if not token:
            continue
        try:
            number = int(token)
        except ValueError:
            continue
        if number <= 0 or number in seen:
            continue
        seen.add(number)
        numbers.append(number)
    return numbers


def _build_template(
    *,
    config: AppConfig,
    parent_issue: int,
    child_numbers: list[int],
    parent_title: str | None,
    milestone_title: str | None,
    final_main_head: str | None,
    final_validation_results: str | None,
) -> dict[str, Any]:
    resolved_milestone_title = (milestone_title or "MXX").strip() or "MXX"
    resolved_parent_title = (parent_title or f"Parent issue #{parent_issue} (offline template)").strip()
    issue_base_url = f"https://github.com/{config.github_owner}/{config.github_repo}/issues"
    pr_base_url = f"https://github.com/{config.github_owner}/{config.github_repo}/pull"

    child_issues = [
        {
            "number": child,
            "state": "OPEN",
            "title": f"Child issue #{child} (offline template)",
            "url": f"{issue_base_url}/{child}",
            "milestone": {"title": resolved_milestone_title},
            "body": "",
            "comments": [],
            "reference_classification": {
                "implementation_issue_numbers": [parent_issue],
                "explicit_implementation_issue_numbers": [child],
            },
            "merged_pr_evidence": [
                {
                    "number": 0,
                    "url": f"{pr_base_url}/0",
                    "marker": _incomplete_marker(),
                }
            ],
            "closeout_marker": _incomplete_marker(),
            "closeout_comment_marker": _incomplete_marker(),
        }
        for child in child_numbers
    ]

    result: dict[str, Any] = {
        "template_only": True,
        "editable_local_artifact": True,
        "template_note": (
            "Editable local offline closeout state template. Replace placeholders before running readiness checks."
        ),
        "parent_issue": {
            "number": parent_issue,
            "state": "OPEN",
            "title": resolved_parent_title,
            "url": f"{issue_base_url}/{parent_issue}",
            "milestone": {"title": resolved_milestone_title},
            "body": "",
            "comments": [],
            "reference_classification": {
                "implementation_issue_numbers": child_numbers,
            },
        },
        "child_issues": child_issues,
        "final_reconciliation": {
            "ready_for_final_reconciliation": False,
            "final_reconciliation_issue": None,
            "parent_should_remain_open": True,
            "unaccounted_children": child_numbers,
            "required_operator_actions": [
                "Fill child states, merged PR evidence, and marker completeness.",
                "Update final reconciliation and closeout readiness fields.",
            ],
            "warnings": [
                "Template placeholders detected; update fields before production closeout checks.",
            ],
        },
    }
    if final_main_head is not None:
        result["final_main_head"] = final_main_head
    if final_validation_results is not None:
        result["final_validation_results"] = final_validation_results
    return result


def _incomplete_marker() -> dict[str, Any]:
    return {
        "state": "incomplete",
        "marker_complete": False,
        "missing_required_fields": ["<fill-required-fields>"],
        "invalid_reasons": [],
        "post_hoc_marker_repair_required": False,
    }


def _error(
    *,
    parent_issue: int,
    output: str | Path,
    error: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "command": COMMAND_NAME,
        "ok": False,
        "read_only": False,
        "local_only": True,
        "error": error,
        "parent_issue": parent_issue,
        "output": str(output),
        "details": details or {},
        "boundary_confirmations": _boundaries(),
    }


def _boundaries() -> list[str]:
    return [
        "local_only: true",
        "No gh command was executed.",
        "No subprocess.run was executed.",
        "No GitHub API calls were executed.",
        "No live issue inspection dependency was executed.",
    ]

