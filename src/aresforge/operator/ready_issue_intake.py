from __future__ import annotations

import json
import subprocess
from typing import Any

from aresforge.config import AppConfig


READY_TRIGGER_LABEL = "aresforge-ready"
PROTECTED_ISSUE_NUMBER = 39


def _run_gh_command(args: list[str]) -> tuple[int, str, str]:
    result = subprocess.run(
        ["gh", *args],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode, result.stdout, result.stderr


def _parse_json_payload(raw_output: str) -> Any:
    if not raw_output.strip():
        raise ValueError("empty_json_output")
    return json.loads(raw_output)


def _normalize_label_names(raw_labels: Any) -> list[str]:
    if not isinstance(raw_labels, list):
        return []
    normalized: list[str] = []
    for item in raw_labels:
        if isinstance(item, dict):
            name = item.get("name")
            if isinstance(name, str):
                normalized.append(name)
        elif isinstance(item, str):
            normalized.append(item)
    return sorted(set(normalized), key=lambda label: (label.lower(), label))


def _label_present(labels: list[str], target: str) -> bool:
    lowered = {label.lower() for label in labels}
    return target.lower() in lowered


def _repo_slug(config: AppConfig) -> str:
    return f"{config.github_owner}/{config.github_repo}"


def _error_payload(
    *,
    config: AppConfig,
    error: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "ok": False,
        "error": error,
        "repo": _repo_slug(config),
        "inspection_mode": "github_read_only",
        "ready_label": READY_TRIGGER_LABEL,
        "protected_issue": PROTECTED_ISSUE_NUMBER,
    }
    if details:
        payload["details"] = details
    return payload


def _boundary_confirmations() -> list[str]:
    return [
        "Human-triggered GitHub read-only inspection.",
        "No GitHub mutation was performed by this command surface.",
        "No PR creation or closeout automation was performed.",
        "No background polling or scheduled behavior was performed.",
        "Issue #39 was not modified.",
    ]


def list_ready_issues(config: AppConfig) -> dict[str, Any]:
    args = [
        "issue",
        "list",
        "--repo",
        _repo_slug(config),
        "--state",
        "open",
        "--label",
        READY_TRIGGER_LABEL,
        "--json",
        "number,title,url,labels,createdAt,updatedAt,author",
    ]
    code, stdout, stderr = _run_gh_command(args)
    if code != 0:
        return _error_payload(
            config=config,
            error="gh_cli_failed",
            details={"exit_code": code, "stderr": stderr.strip()},
        )

    try:
        raw_items = _parse_json_payload(stdout)
    except (ValueError, json.JSONDecodeError) as exc:
        return _error_payload(
            config=config,
            error="gh_cli_invalid_json",
            details={"message": str(exc)},
        )

    items: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []

    if isinstance(raw_items, list):
        for raw_issue in raw_items:
            if not isinstance(raw_issue, dict):
                continue
            number = raw_issue.get("number")
            if not isinstance(number, int):
                continue
            if number == PROTECTED_ISSUE_NUMBER:
                excluded.append({"number": number, "reason": "protected_issue"})
                continue

            labels = _normalize_label_names(raw_issue.get("labels"))
            if not _label_present(labels, READY_TRIGGER_LABEL):
                continue

            author = raw_issue.get("author")
            author_login = author.get("login") if isinstance(author, dict) else None
            items.append(
                {
                    "number": number,
                    "title": raw_issue.get("title"),
                    "url": raw_issue.get("url"),
                    "labels": labels,
                    "author": author_login,
                    "created_at": raw_issue.get("createdAt"),
                    "updated_at": raw_issue.get("updatedAt"),
                    "ready_for_automation": True,
                }
            )

    items.sort(key=lambda issue: issue["number"])

    return {
        "ok": True,
        "inspection_mode": "github_read_only",
        "repo": _repo_slug(config),
        "ready_label": READY_TRIGGER_LABEL,
        "protected_issue": PROTECTED_ISSUE_NUMBER,
        "issue_count": len(items),
        "issues": items,
        "excluded_issues": excluded,
        "boundary_confirmations": _boundary_confirmations(),
    }


def inspect_ready_issue(config: AppConfig, issue_number: int) -> dict[str, Any]:
    if issue_number == PROTECTED_ISSUE_NUMBER:
        return _error_payload(config=config, error="protected_issue")

    args = [
        "issue",
        "view",
        str(issue_number),
        "--repo",
        _repo_slug(config),
        "--json",
        "number,title,state,url,labels,createdAt,updatedAt,author,assignees,milestone,body",
    ]
    code, stdout, stderr = _run_gh_command(args)
    if code != 0:
        return _error_payload(
            config=config,
            error="gh_cli_failed",
            details={"exit_code": code, "stderr": stderr.strip()},
        )

    try:
        raw_issue = _parse_json_payload(stdout)
    except (ValueError, json.JSONDecodeError) as exc:
        return _error_payload(
            config=config,
            error="gh_cli_invalid_json",
            details={"message": str(exc)},
        )

    if not isinstance(raw_issue, dict):
        return _error_payload(config=config, error="issue_not_found")

    labels = _normalize_label_names(raw_issue.get("labels"))
    if not _label_present(labels, READY_TRIGGER_LABEL):
        return _error_payload(
            config=config,
            error="issue_not_ready",
            details={"issue_number": issue_number, "labels": labels},
        )

    state = raw_issue.get("state")
    if isinstance(state, str) and state.upper() != "OPEN":
        return _error_payload(
            config=config,
            error="issue_not_open",
            details={"issue_number": issue_number, "state": state},
        )

    author = raw_issue.get("author")
    author_login = author.get("login") if isinstance(author, dict) else None

    assignees_raw = raw_issue.get("assignees")
    assignees: list[str] = []
    if isinstance(assignees_raw, list):
        for entry in assignees_raw:
            if isinstance(entry, dict) and isinstance(entry.get("login"), str):
                assignees.append(entry["login"])
    assignees = sorted(set(assignees), key=lambda login: (login.lower(), login))

    milestone_raw = raw_issue.get("milestone")
    milestone: dict[str, Any] | None = None
    if isinstance(milestone_raw, dict):
        milestone = {
            "number": milestone_raw.get("number"),
            "title": milestone_raw.get("title"),
            "url": milestone_raw.get("url"),
        }

    return {
        "ok": True,
        "inspection_mode": "github_read_only",
        "repo": _repo_slug(config),
        "ready_label": READY_TRIGGER_LABEL,
        "protected_issue": PROTECTED_ISSUE_NUMBER,
        "automation_trigger": {
            "type": "manual_label",
            "label": READY_TRIGGER_LABEL,
            "active": True,
        },
        "issue": {
            "number": raw_issue.get("number"),
            "title": raw_issue.get("title"),
            "state": state,
            "url": raw_issue.get("url"),
            "labels": labels,
            "author": author_login,
            "assignees": assignees,
            "milestone": milestone,
            "created_at": raw_issue.get("createdAt"),
            "updated_at": raw_issue.get("updatedAt"),
            "body": raw_issue.get("body"),
        },
        "boundary_confirmations": _boundary_confirmations(),
    }
