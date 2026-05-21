from __future__ import annotations

import json
import re
import subprocess
from typing import Any

from aresforge.config import AppConfig


READY_TRIGGER_LABEL = "aresforge-ready"
PROTECTED_ISSUE_NUMBER = 39

IMPLEMENTATION_REFERENCE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(?:closes|fixes|resolves|implements)\s+#(?P<number>\d+)\b", re.IGNORECASE),
    re.compile(r"\b(?:parent\s+issue|linked\s+issue)\s*:\s*#(?P<number>\d+)\b", re.IGNORECASE),
    re.compile(r"\bpart\s+of\s+#(?P<number>\d+)\b", re.IGNORECASE),
    re.compile(r"\bchild\s+of\s+#(?P<number>\d+)\b", re.IGNORECASE),
    re.compile(r"\bparent\s*:\s*#(?P<number>\d+)\b", re.IGNORECASE),
)

SAFETY_REFERENCE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bdo\s+not\s+modify\s+issue\s+#(?P<number>\d+)\b", re.IGNORECASE),
    re.compile(r"\bissue\s+#(?P<number>\d+)\s+remains\s+protected\b", re.IGNORECASE),
    re.compile(r"\bdoes\s+not\s+close\s+issue\s+#(?P<number>\d+)\b", re.IGNORECASE),
    re.compile(r"\bhistorical\s+validation\s+evidence\s+only\s*:\s*#(?P<number>\d+)\b", re.IGNORECASE),
    re.compile(r"\bprotected\s+issue\s*:\s*#(?P<number>\d+)\b", re.IGNORECASE),
)

GENERIC_REFERENCE_PATTERN = re.compile(r"#(?P<number>\d+)\b")
EXPLICIT_IMPLEMENTATION_LINE_PATTERN = re.compile(
    r"^\s*(?:[-*]\s*)?(?:part\s+of|implements|linked\s+issue|parent\s+issue|closes|fixes|resolves)\b",
    re.IGNORECASE,
)


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
        "Protected historical reference handling remained read-only.",
    ]


def classify_issue_references(body: str | None) -> dict[str, Any]:
    text = body or ""
    safety_numbers: set[int] = set()
    implementation_numbers: set[int] = set()
    explicit_implementation_numbers: set[int] = set()
    incidental_reference_numbers: set[int] = set()

    for pattern in SAFETY_REFERENCE_PATTERNS:
        for match in pattern.finditer(text):
            safety_numbers.add(int(match.group("number")))

    for pattern in IMPLEMENTATION_REFERENCE_PATTERNS:
        for match in pattern.finditer(text):
            number = int(match.group("number"))
            if number not in safety_numbers:
                implementation_numbers.add(number)

    for match in GENERIC_REFERENCE_PATTERN.finditer(text):
        number = int(match.group("number"))
        if number not in implementation_numbers and number not in safety_numbers:
            incidental_reference_numbers.add(number)
        if number == PROTECTED_ISSUE_NUMBER and number not in implementation_numbers:
            safety_numbers.add(number)

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or not EXPLICIT_IMPLEMENTATION_LINE_PATTERN.search(line):
            continue
        for match in GENERIC_REFERENCE_PATTERN.finditer(line):
            number = int(match.group("number"))
            if number not in safety_numbers:
                explicit_implementation_numbers.add(number)
                implementation_numbers.add(number)
            incidental_reference_numbers.discard(number)

    protected_in_impl = PROTECTED_ISSUE_NUMBER in implementation_numbers
    if PROTECTED_ISSUE_NUMBER in safety_numbers and protected_in_impl:
        implementation_numbers.discard(PROTECTED_ISSUE_NUMBER)

    parent_child = {
        "parent_issue_numbers": sorted(
            number
            for number in implementation_numbers
            if re.search(rf"\bparent\s+issue\s*:\s*#{number}\b", text, re.IGNORECASE)
        ),
        "linked_issue_numbers": sorted(
            number
            for number in implementation_numbers
            if re.search(rf"\blinked\s+issue\s*:\s*#{number}\b", text, re.IGNORECASE)
        ),
    }

    return {
        "implementation_issue_numbers": sorted(implementation_numbers),
        "explicit_implementation_issue_numbers": sorted(explicit_implementation_numbers),
        "incidental_reference_issue_numbers": sorted(incidental_reference_numbers),
        "safety_or_historical_issue_numbers": sorted(safety_numbers),
        "protected_issue_excluded_from_implementation": PROTECTED_ISSUE_NUMBER in safety_numbers,
        "contains_protected_issue_implementation_link": protected_in_impl,
        "parent_child_references": parent_child,
    }


def normalize_issue_for_planning(raw_issue: dict[str, Any]) -> dict[str, Any]:
    labels = _normalize_label_names(raw_issue.get("labels"))
    body = raw_issue.get("body") if isinstance(raw_issue.get("body"), str) else ""

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

    references = classify_issue_references(body)
    comments = _normalize_issue_comments(raw_issue.get("comments"))

    issue_number = raw_issue.get("number")
    protected = issue_number == PROTECTED_ISSUE_NUMBER

    return {
        "number": issue_number,
        "title": raw_issue.get("title"),
        "state": raw_issue.get("state"),
        "url": raw_issue.get("url"),
        "labels": labels,
        "milestone": milestone,
        "assignees": assignees,
        "body": body,
        "comments": comments,
        "reference_classification": references,
        "detectable_parent_child_references": references["parent_child_references"],
        "merged_pr_evidence": _normalize_closed_by_pull_requests(
            raw_issue.get("closedByPullRequestsReferences")
        ),
        "is_protected_issue": protected,
    }


def _normalize_closed_by_pull_requests(raw_items: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_items, list):
        return []
    normalized: list[dict[str, Any]] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        merged = item.get("mergedAt")
        if not isinstance(merged, str) or not merged.strip():
            continue
        number = item.get("number")
        if not isinstance(number, int):
            continue
        normalized.append(
            {
                "number": number,
                "url": item.get("url"),
                "title": item.get("title"),
                "state": item.get("state"),
                "merged_at": merged,
            }
        )
    normalized.sort(key=lambda entry: entry["number"])
    return normalized


def _normalize_issue_comments(raw_items: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_items, list):
        return []
    normalized: list[dict[str, Any]] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        body = item.get("body")
        if not isinstance(body, str):
            body = ""
        author = item.get("author")
        author_login = author.get("login") if isinstance(author, dict) else None
        normalized.append(
            {
                "id": item.get("id"),
                "url": item.get("url"),
                "created_at": item.get("createdAt"),
                "updated_at": item.get("updatedAt"),
                "author": author_login,
                "body": body,
                "reference_classification": classify_issue_references(body),
            }
        )
    return normalized


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
    issue_payload = fetch_issue_details(config, issue_number)
    if not issue_payload.get("ok"):
        return issue_payload

    issue = issue_payload["issue"]
    labels = issue.get("labels", [])
    if not _label_present(labels, READY_TRIGGER_LABEL):
        return _error_payload(
            config=config,
            error="issue_not_ready",
            details={"issue_number": issue_number, "labels": labels},
        )

    state = issue.get("state")
    if isinstance(state, str) and state.upper() != "OPEN":
        return _error_payload(
            config=config,
            error="issue_not_open",
            details={"issue_number": issue_number, "state": state},
        )

    issue_payload["automation_trigger"] = {
        "type": "manual_label",
        "label": READY_TRIGGER_LABEL,
        "active": True,
    }
    return issue_payload


def fetch_issue_details(config: AppConfig, issue_number: int) -> dict[str, Any]:
    if issue_number == PROTECTED_ISSUE_NUMBER:
        return _error_payload(config=config, error="protected_issue")

    args = [
        "issue",
        "view",
        str(issue_number),
        "--repo",
        _repo_slug(config),
        "--json",
        (
            "number,title,state,url,labels,createdAt,updatedAt,author,assignees,milestone,body,"
            "closedByPullRequestsReferences,comments"
        ),
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

    normalized = normalize_issue_for_planning(raw_issue)
    normalized["author"] = (
        raw_issue.get("author", {}).get("login")
        if isinstance(raw_issue.get("author"), dict)
        else None
    )
    normalized["created_at"] = raw_issue.get("createdAt")
    normalized["updated_at"] = raw_issue.get("updatedAt")

    return {
        "ok": True,
        "inspection_mode": "github_read_only",
        "repo": _repo_slug(config),
        "ready_label": READY_TRIGGER_LABEL,
        "protected_issue": PROTECTED_ISSUE_NUMBER,
        "issue": normalized,
        "boundary_confirmations": _boundary_confirmations(),
    }


def fetch_issue_batch_for_planning(config: AppConfig, issue_numbers: list[int]) -> dict[str, Any]:
    normalized_numbers = sorted(set(number for number in issue_numbers if isinstance(number, int)))
    issues: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    for number in normalized_numbers:
        if number == PROTECTED_ISSUE_NUMBER:
            excluded.append({"number": number, "reason": "protected_issue"})
            continue
        details = fetch_issue_details(config, number)
        if not details.get("ok"):
            warnings.append(
                {
                    "issue_number": number,
                    "error": details.get("error", "unknown_error"),
                    "details": details.get("details"),
                }
            )
            continue
        issue = details.get("issue")
        if isinstance(issue, dict):
            issues.append(issue)

    return {
        "ok": True,
        "inspection_mode": "github_read_only",
        "repo": _repo_slug(config),
        "requested_issue_numbers": normalized_numbers,
        "issues": issues,
        "excluded_issues": excluded,
        "warnings": warnings,
        "boundary_confirmations": _boundary_confirmations(),
    }
