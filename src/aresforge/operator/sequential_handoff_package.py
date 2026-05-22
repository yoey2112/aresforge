from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from aresforge.artifacts.store import write_markdown_json_bundle
from aresforge.config import AppConfig
from aresforge.operator.milestone_dashboard import inspect_milestone_dashboard
from aresforge.operator.ready_issue_intake import fetch_issue_details

COMMAND_NAME = "generate-sequential-handoff-package"
_ISSUE_REF = re.compile(r"#(?P<number>\d+)\b")
_BRANCH_LINE = re.compile(r"^\s*-\s*Branch\s*$", re.IGNORECASE)
_COMMIT_LINE = re.compile(r"^\s*-\s*Commit hash\s*$", re.IGNORECASE)
_PR_LINE = re.compile(r"https://github\.com/[^/]+/[^/]+/pull/\d+")


def generate_sequential_handoff_package(
    config: AppConfig,
    *,
    parent_issue: int,
    child_issue: int | None = None,
    write_package: bool = False,
) -> dict[str, Any]:
    parent_payload = fetch_issue_details(config, parent_issue)
    if not parent_payload.get("ok"):
        return {
            "command": COMMAND_NAME,
            "ok": False,
            "read_only": True,
            "error": "parent_issue_lookup_failed",
            "details": parent_payload,
        }
    parent = parent_payload["issue"]
    children = _discover_children(parent)
    if isinstance(child_issue, int):
        children = [number for number in children if number == child_issue]
    records: list[dict[str, Any]] = []
    for number in children:
        details = fetch_issue_details(config, number)
        if not details.get("ok") or not isinstance(details.get("issue"), dict):
            continue
        records.append(_issue_record(details["issue"]))

    dashboard = inspect_milestone_dashboard(config, parent_issue=parent_issue)
    next_child = _next_child(records)
    package = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "parent_issue": {
            "number": parent.get("number"),
            "title": parent.get("title"),
            "state": parent.get("state"),
            "url": parent.get("url"),
        },
        "children": records,
        "next_child_recommendation": next_child,
        "dashboard_status": {
            "ok": bool(dashboard.get("ok")),
            "parent_should_remain_open": ((dashboard.get("dashboard") or {}).get("parent_should_remain_open")),
            "warnings": dashboard.get("warnings"),
        },
    }
    result = {
        "command": COMMAND_NAME,
        "ok": True,
        "read_only": not write_package,
        "parent_issue": parent_issue,
        "child_issue": child_issue,
        "package": package,
        "boundary_confirmations": [
            "No GitHub mutation was performed.",
            "Package generation is read-only unless local artifact write is explicitly requested.",
        ],
    }
    if write_package:
        title = f"M19 sequential handoff package parent {parent_issue}"
        markdown = _render_markdown(package)
        bundle = write_markdown_json_bundle(config.evidence_dir, title=title, markdown=markdown, payload=package)
        result["artifact"] = {"markdown_path": str(bundle.markdown_path), "json_path": str(bundle.json_path)}
    return result


def _discover_children(parent_issue: dict[str, Any]) -> list[int]:
    body = parent_issue.get("body") if isinstance(parent_issue.get("body"), str) else ""
    numbers: set[int] = set()
    for match in _ISSUE_REF.finditer(body):
        number = int(match.group("number"))
        if number != parent_issue.get("number"):
            numbers.add(number)
    return sorted(numbers)


def _issue_record(issue: dict[str, Any]) -> dict[str, Any]:
    evidence_url = None
    branch = None
    commit = None
    pr_url = None
    comments = issue.get("comments") if isinstance(issue.get("comments"), list) else []
    for comment in reversed(comments):
        if not isinstance(comment, dict):
            continue
        body = comment.get("body") if isinstance(comment.get("body"), str) else ""
        pr_match = _PR_LINE.search(body)
        if pr_match and pr_url is None:
            pr_url = pr_match.group(0)
            evidence_url = comment.get("url")
        lines = body.splitlines()
        for idx, line in enumerate(lines):
            if _BRANCH_LINE.search(line) and idx + 1 < len(lines):
                if lines[idx + 1].strip().startswith("- "):
                    branch = lines[idx + 1].strip()[2:].strip()
            if _COMMIT_LINE.search(line) and idx + 1 < len(lines):
                if lines[idx + 1].strip().startswith("- "):
                    commit = lines[idx + 1].strip()[2:].strip()
    merged_prs = issue.get("merged_pr_evidence") if isinstance(issue.get("merged_pr_evidence"), list) else []
    merge_commit = None
    if merged_prs:
        latest = merged_prs[-1]
        if isinstance(latest, dict):
            merge_commit = latest.get("merge_commit") or latest.get("merged_at")
            if pr_url is None and isinstance(latest.get("url"), str):
                pr_url = latest.get("url")
    return {
        "issue_number": issue.get("number"),
        "title": issue.get("title"),
        "final_child_state": issue.get("state"),
        "branch": branch,
        "commit": commit,
        "pr_url": pr_url,
        "merge_commit_or_main_hash": merge_commit,
        "validations": [
            "git diff --check",
            "python -m pytest",
            "python -m aresforge inspect-repo-governance",
            "python -m aresforge inspect-milestone-dashboard --parent-issue 309",
            "python -m aresforge inspect-milestone-state --parent-issue 309",
            "python -m aresforge check-milestone-evidence-readiness --parent-issue 309",
        ],
        "evidence_url_if_known": evidence_url,
    }


def _next_child(records: list[dict[str, Any]]) -> int | None:
    open_children = [
        int(item["issue_number"])
        for item in records
        if isinstance(item.get("issue_number"), int) and str(item.get("final_child_state", "")).upper() == "OPEN"
    ]
    return min(open_children) if open_children else None


def _render_markdown(package: dict[str, Any]) -> str:
    lines = [
        "# Sequential Handoff Package",
        "",
        f"- Parent issue: #{package['parent_issue']['number']}",
        f"- Parent state: {package['parent_issue']['state']}",
        f"- Next child recommendation: {package.get('next_child_recommendation')}",
        "",
        "## Children",
    ]
    children = package.get("children") if isinstance(package.get("children"), list) else []
    if not children:
        lines.append("- No child records.")
        return "\n".join(lines)
    for child in children:
        lines.extend(
            [
                f"- Issue #{child.get('issue_number')}: {child.get('title')}",
                f"  State: {child.get('final_child_state')}",
                f"  Branch: {child.get('branch')}",
                f"  Commit: {child.get('commit')}",
                f"  PR: {child.get('pr_url')}",
                f"  Merge/main: {child.get('merge_commit_or_main_hash')}",
                f"  Evidence URL: {child.get('evidence_url_if_known')}",
            ]
        )
    return "\n".join(lines)
