from __future__ import annotations

import subprocess
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.ready_issue_intake import (
    PROTECTED_ISSUE_NUMBER,
    fetch_issue_batch_for_planning,
)


def plan_batch_closeout(config: AppConfig, *, parent_issue: int) -> dict[str, Any]:
    parent_payload = fetch_issue_batch_for_planning(config, [parent_issue])
    parent_issues = parent_payload.get("issues") if isinstance(parent_payload.get("issues"), list) else []
    if not parent_issues:
        return {
            "command": "plan-batch-closeout",
            "ok": False,
            "inspection_mode": "github_read_only",
            "repo": f"{config.github_owner}/{config.github_repo}",
            "error": "parent_issue_unavailable",
            "parent_issue": parent_issue,
            "warnings": parent_payload.get("warnings", []),
            "excluded_issues": parent_payload.get("excluded_issues", []),
        }

    parent = parent_issues[0]
    child_candidates = _collect_child_issue_numbers(parent)

    children_payload = fetch_issue_batch_for_planning(config, child_candidates)
    children = children_payload.get("issues") if isinstance(children_payload.get("issues"), list) else []

    completed_children: list[dict[str, Any]] = []
    open_or_blocked_children: list[dict[str, Any]] = []
    excluded_issues: list[dict[str, Any]] = []

    if isinstance(children_payload.get("excluded_issues"), list):
        excluded_issues.extend(
            item for item in children_payload["excluded_issues"] if isinstance(item, dict)
        )

    for issue in children:
        number = issue.get("number")
        if not isinstance(number, int):
            continue
        if number == PROTECTED_ISSUE_NUMBER:
            excluded_issues.append({"number": number, "reason": "protected_issue"})
            continue

        state = str(issue.get("state") or "").upper()
        details = {
            "number": number,
            "title": issue.get("title"),
            "state": state,
            "url": issue.get("url"),
            "labels": issue.get("labels", []),
            "pr_merge_evidence": _detect_pr_merge_evidence(issue),
        }

        if state == "CLOSED":
            completed_children.append(details)
        else:
            open_or_blocked_children.append(details)

    completed_children.sort(key=lambda item: item["number"])
    open_or_blocked_children.sort(key=lambda item: item["number"])
    excluded_issues = sorted(
        {
            (item.get("number"), item.get("reason")): item
            for item in excluded_issues
            if isinstance(item.get("number"), int)
        }.values(),
        key=lambda item: (item["number"], str(item.get("reason", ""))),
    )

    readiness = "closeout_ready" if not open_or_blocked_children else "not_ready"

    return {
        "command": "plan-batch-closeout",
        "ok": True,
        "inspection_mode": "github_read_only",
        "repo": f"{config.github_owner}/{config.github_repo}",
        "parent_issue": {
            "number": parent.get("number"),
            "title": parent.get("title"),
            "state": parent.get("state"),
            "url": parent.get("url"),
        },
        "child_issue_group": {
            "requested_child_issue_numbers": child_candidates,
            "completed_children": completed_children,
            "open_or_blocked_children": open_or_blocked_children,
            "excluded_issues": excluded_issues,
        },
        "closeout_plan": {
            "readiness": readiness,
            "human_actions_required": [
                "Review completed child evidence and validation outputs.",
                "Confirm parent issue narrative reflects final child status.",
                "Run human-triggered PR merge/issue closeout only after review.",
            ],
            "mutation_posture": "planning_only_no_close_or_comment",
        },
        "warnings": [
            "This command is read-only and does not close or comment on issues.",
            "Labels, milestones, PR state, and issue state were not mutated.",
            "Issue #39 remains protected historical evidence and is excluded from active closeout planning.",
        ],
    }


def _collect_child_issue_numbers(parent_issue: dict[str, Any]) -> list[int]:
    numbers: set[int] = set()
    references = parent_issue.get("reference_classification")
    if isinstance(references, dict):
        impl = references.get("implementation_issue_numbers")
        if isinstance(impl, list):
            for item in impl:
                if isinstance(item, int):
                    numbers.add(item)

    body = parent_issue.get("body")
    if isinstance(body, str):
        for raw_line in body.splitlines():
            line = raw_line.strip()
            if "#" not in line:
                continue
            if "- [" not in line and "child" not in line.lower():
                continue
            for token in line.split():
                if token.startswith("#") and token[1:].rstrip(",.)").isdigit():
                    numbers.add(int(token[1:].rstrip(",.)")))

    numbers.discard(PROTECTED_ISSUE_NUMBER)
    parent_number = parent_issue.get("number")
    if isinstance(parent_number, int):
        numbers.discard(parent_number)
    return sorted(numbers)


def _detect_pr_merge_evidence(issue: dict[str, Any]) -> dict[str, Any]:
    references = issue.get("reference_classification")
    if not isinstance(references, dict):
        return {"available": False, "signals": []}

    signals: list[str] = []
    impl = references.get("implementation_issue_numbers")
    if isinstance(impl, list) and impl:
        signals.append("implementation_link_references_present")

    state = str(issue.get("state") or "").upper()
    if state == "CLOSED":
        signals.append("issue_state_closed")

    return {"available": bool(signals), "signals": signals}


def current_branch(repo_root: str) -> str | None:
    result = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    value = result.stdout.strip()
    return value or None
