from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import subprocess
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.ready_issue_intake import (
    PROTECTED_ISSUE_NUMBER,
    fetch_issue_details,
)

COMMAND_NAME = "inspect-milestone-state"

_CHILD_LINE_PATTERN = re.compile(
    r"^\s*(?:[-*]\s*|\d+\.\s*)?(?:\[[ xX]\]\s*)?#(?P<number>\d+)\b",
    re.IGNORECASE,
)
_CHECKLIST_INLINE_PATTERN = re.compile(r"\(#(?P<number>\d+)\)")
_MILESTONE_NAME_PATTERN = re.compile(r"^M\d+\b")


@dataclass(frozen=True)
class ChildState:
    issue_number: int
    state: str | None
    title: str | None
    url: str | None
    milestone_title: str | None
    linked_pr_count: int
    merged_pr_count: int
    lineage_detected: bool
    lineage_sources: tuple[str, ...]


def inspect_milestone_state(
    config: AppConfig,
    *,
    parent_issue: int,
    state_file: str | Path | None = None,
) -> dict[str, Any]:
    if state_file is not None:
        return _inspect_milestone_state_from_local_file(
            config,
            parent_issue=parent_issue,
            state_file=state_file,
        )

    parent_payload = fetch_issue_details(config, parent_issue)
    if not parent_payload.get("ok"):
        return {
            "command": COMMAND_NAME,
            "ok": False,
            "read_only": True,
            "error": parent_payload.get("error", "parent_issue_lookup_failed"),
            "parent_issue": parent_issue,
            "details": parent_payload.get("details"),
            "boundary_confirmations": _boundaries(),
        }

    parent_issue_payload = parent_payload.get("issue")
    if not isinstance(parent_issue_payload, dict):
        return {
            "command": COMMAND_NAME,
            "ok": False,
            "read_only": True,
            "error": "parent_issue_lookup_failed",
            "parent_issue": parent_issue,
            "boundary_confirmations": _boundaries(),
        }

    discovered_child_numbers = _discover_child_issue_numbers(
        parent_issue=parent_issue,
        parent_payload=parent_issue_payload,
    )
    discovery_position = {number: index for index, number in enumerate(discovered_child_numbers, start=1)}
    child_states: list[ChildState] = []
    lookup_warnings: list[dict[str, Any]] = []
    for child_number in discovered_child_numbers:
        child_payload = fetch_issue_details(config, child_number)
        if not child_payload.get("ok"):
            lookup_warnings.append(
                {
                    "issue_number": child_number,
                    "error": child_payload.get("error", "child_issue_lookup_failed"),
                    "details": child_payload.get("details"),
                }
            )
            continue
        child_issue = child_payload.get("issue")
        if not isinstance(child_issue, dict):
            lookup_warnings.append(
                {
                    "issue_number": child_number,
                    "error": "child_issue_lookup_failed",
                }
            )
            continue
        child_states.append(_to_child_state(parent_issue=parent_issue, issue=child_issue))

    summary = _build_summary(parent_issue_payload=parent_issue_payload, child_states=child_states)

    warnings = _build_warnings(
        parent_issue=parent_issue,
        parent_issue_payload=parent_issue_payload,
        child_states=child_states,
        lookup_warnings=lookup_warnings,
    )
    lineage_hints = _lineage_hints(parent_issue=parent_issue, child_states=child_states)
    evidence_hints = _evidence_hints(child_states)

    return {
        "command": COMMAND_NAME,
        "ok": True,
        "read_only": True,
        "inspection_mode": "github_read_only",
        "repo": f"{config.github_owner}/{config.github_repo}",
        "parent_issue": _issue_summary(parent_issue_payload),
        "child_discovery": {
            "strategy": "parent_body_and_parent_comments_reference_scan",
            "discovered_child_issue_numbers": discovered_child_numbers,
            "child_issue_count": len(child_states),
            "lookup_warnings": lookup_warnings,
        },
        "child_issues": [
            {
                "issue_number": item.issue_number,
                "state": item.state,
                "title": item.title,
                "url": item.url,
                "milestone_title": item.milestone_title,
                "linked_pr_count": item.linked_pr_count,
                "merged_pr_count": item.merged_pr_count,
                "lineage_detected": item.lineage_detected,
                "lineage_sources": list(item.lineage_sources),
                "discovery_position": discovery_position.get(item.issue_number),
            }
            for item in child_states
        ],
        "summary": summary,
        "lineage_hints": lineage_hints,
        "evidence_hints": evidence_hints,
        "warnings": warnings,
        "boundary_confirmations": _boundaries(),
    }


def _inspect_milestone_state_from_local_file(
    config: AppConfig,
    *,
    parent_issue: int,
    state_file: str | Path,
) -> dict[str, Any]:
    state_path = Path(state_file)
    try:
        parsed = json.loads(state_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return _local_state_error(
            parent_issue=parent_issue,
            state_file=state_path,
            error="state_file_not_found",
            details={"path": str(state_path)},
        )
    except json.JSONDecodeError as exc:
        return _local_state_error(
            parent_issue=parent_issue,
            state_file=state_path,
            error="state_file_invalid_json",
            details={"path": str(state_path), "message": str(exc)},
        )
    except OSError as exc:
        return _local_state_error(
            parent_issue=parent_issue,
            state_file=state_path,
            error="state_file_read_failed",
            details={"path": str(state_path), "message": str(exc)},
        )

    if not isinstance(parsed, dict):
        return _local_state_error(
            parent_issue=parent_issue,
            state_file=state_path,
            error="invalid_state_file_schema",
            details={"reason": "state_file_root_must_be_object"},
        )

    parent_issue_payload = parsed.get("parent_issue")
    if not isinstance(parent_issue_payload, dict):
        return _local_state_error(
            parent_issue=parent_issue,
            state_file=state_path,
            error="invalid_state_file_schema",
            details={"reason": "parent_issue_must_be_object"},
        )

    file_parent_number = parent_issue_payload.get("number")
    if not isinstance(file_parent_number, int):
        return _local_state_error(
            parent_issue=parent_issue,
            state_file=state_path,
            error="invalid_state_file_schema",
            details={"reason": "parent_issue.number_must_be_integer"},
        )
    if file_parent_number != parent_issue:
        return _local_state_error(
            parent_issue=parent_issue,
            state_file=state_path,
            error="parent_issue_mismatch",
            details={"expected_parent_issue": parent_issue, "state_file_parent_issue": file_parent_number},
        )

    child_issues_payload = parsed.get("child_issues")
    if not isinstance(child_issues_payload, list):
        return _local_state_error(
            parent_issue=parent_issue,
            state_file=state_path,
            error="invalid_state_file_schema",
            details={"reason": "child_issues_must_be_list"},
        )

    child_issue_objects: list[dict[str, Any]] = []
    for index, item in enumerate(child_issues_payload):
        if not isinstance(item, dict):
            return _local_state_error(
                parent_issue=parent_issue,
                state_file=state_path,
                error="invalid_state_file_schema",
                details={"reason": "child_issue_must_be_object", "child_index": index},
            )
        issue_number = item.get("number")
        if not isinstance(issue_number, int):
            return _local_state_error(
                parent_issue=parent_issue,
                state_file=state_path,
                error="invalid_state_file_schema",
                details={"reason": "child_issue.number_must_be_integer", "child_index": index},
            )
        child_issue_objects.append(item)

    discovered_child_numbers = [int(item["number"]) for item in child_issue_objects]
    discovery_position = {number: index for index, number in enumerate(discovered_child_numbers, start=1)}
    child_states = [
        _to_child_state(parent_issue=parent_issue, issue=item)
        for item in child_issue_objects
    ]
    lookup_warnings: list[dict[str, Any]] = []
    summary = _build_summary(parent_issue_payload=parent_issue_payload, child_states=child_states)
    warnings = _build_warnings(
        parent_issue=parent_issue,
        parent_issue_payload=parent_issue_payload,
        child_states=child_states,
        lookup_warnings=lookup_warnings,
    )
    lineage_hints = _lineage_hints(parent_issue=parent_issue, child_states=child_states)
    evidence_hints = _evidence_hints(child_states)

    return {
        "command": COMMAND_NAME,
        "ok": True,
        "read_only": True,
        "inspection_mode": "local_state_file",
        "repo": f"{config.github_owner}/{config.github_repo}",
        "state_file": str(state_path),
        "parent_issue": _issue_summary(parent_issue_payload),
        "child_discovery": {
            "strategy": "local_state_file",
            "discovered_child_issue_numbers": discovered_child_numbers,
            "child_issue_count": len(child_states),
            "lookup_warnings": lookup_warnings,
        },
        "child_issues": [
            {
                "issue_number": item.issue_number,
                "state": item.state,
                "title": item.title,
                "url": item.url,
                "milestone_title": item.milestone_title,
                "linked_pr_count": item.linked_pr_count,
                "merged_pr_count": item.merged_pr_count,
                "lineage_detected": item.lineage_detected,
                "lineage_sources": list(item.lineage_sources),
                "discovery_position": discovery_position.get(item.issue_number),
            }
            for item in child_states
        ],
        "summary": summary,
        "lineage_hints": lineage_hints,
        "evidence_hints": evidence_hints,
        "warnings": warnings,
        "boundary_confirmations": _boundaries(),
    }


def _local_state_error(
    *,
    parent_issue: int,
    state_file: Path,
    error: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "command": COMMAND_NAME,
        "ok": False,
        "read_only": True,
        "inspection_mode": "local_state_file",
        "error": error,
        "parent_issue": parent_issue,
        "state_file": str(state_file),
        "details": details or {},
        "boundary_confirmations": _boundaries(),
    }


def _discover_child_issue_numbers(*, parent_issue: int, parent_payload: dict[str, Any]) -> list[int]:
    discovered: list[int] = []
    seen: set[int] = set()

    def _add(number: int) -> None:
        if number in seen or number == parent_issue or number == PROTECTED_ISSUE_NUMBER:
            return
        seen.add(number)
        discovered.append(number)

    refs = (parent_payload.get("reference_classification") or {}).get("implementation_issue_numbers")
    if isinstance(refs, list):
        for item in refs:
            if isinstance(item, int):
                _add(item)

    body = parent_payload.get("body")
    if isinstance(body, str):
        for line in body.splitlines():
            match = _CHILD_LINE_PATTERN.search(line)
            if match:
                _add(int(match.group("number")))
                continue
            stripped = line.strip()
            if (
                stripped.startswith("- [")
                or stripped.startswith("* [")
                or bool(re.match(r"^\d+\.\s+", stripped))
            ):
                for inline in _CHECKLIST_INLINE_PATTERN.finditer(line):
                    _add(int(inline.group("number")))

    comments = parent_payload.get("comments")
    if isinstance(comments, list):
        for comment in comments:
            if not isinstance(comment, dict):
                continue
            refs = (comment.get("reference_classification") or {}).get("implementation_issue_numbers")
            if not isinstance(refs, list):
                continue
            for item in refs:
                if isinstance(item, int):
                    _add(item)

    if not discovered:
        for child_number in _discover_children_from_repo_scan(
            parent_issue=parent_issue,
            owner_repo_hint=parent_payload.get("url"),
        ):
            _add(child_number)

    return discovered


def _discover_children_from_repo_scan(*, parent_issue: int, owner_repo_hint: Any) -> list[int]:
    if not isinstance(owner_repo_hint, str) or "/issues/" not in owner_repo_hint:
        return []
    prefix = owner_repo_hint.split("/issues/")[0]
    if "github.com/" not in prefix:
        return []
    repo_slug = prefix.split("github.com/", 1)[1].strip("/")
    if not repo_slug:
        return []

    search = f"\"Parent issue: #{parent_issue}\" in:body"
    result = subprocess.run(
        [
            "gh",
            "issue",
            "list",
            "--repo",
            repo_slug,
            "--state",
            "all",
            "--limit",
            "200",
            "--json",
            "number,body",
            "--search",
            search,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return []
    try:
        payload = json.loads(result.stdout)
    except Exception:
        return []
    if not isinstance(payload, list):
        return []
    discovered: list[int] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        body = item.get("body")
        number = item.get("number")
        if not isinstance(number, int) or not isinstance(body, str):
            continue
        if re.search(rf"\bparent\s+issue\s*:\s*#{parent_issue}\b", body, re.IGNORECASE):
            discovered.append(number)
    return sorted(set(discovered))


def _to_child_state(*, parent_issue: int, issue: dict[str, Any]) -> ChildState:
    issue_number = issue.get("number")
    refs = (issue.get("reference_classification") or {}).get("implementation_issue_numbers") or []
    if not isinstance(refs, list):
        refs = []
    body = issue.get("body")
    lineage_sources: list[str] = []
    if parent_issue in refs:
        lineage_sources.append("reference_classification")
    if isinstance(body, str) and re.search(rf"\bparent\s+issue\s*:\s*#{parent_issue}\b", body, re.IGNORECASE):
        lineage_sources.append("explicit_parent_issue_line")
    comments = issue.get("comments")
    if isinstance(comments, list):
        for comment in comments:
            if not isinstance(comment, dict):
                continue
            comment_refs = (
                (comment.get("reference_classification") or {}).get("implementation_issue_numbers") or []
            )
            if isinstance(comment_refs, list) and parent_issue in comment_refs:
                lineage_sources.append("comment_reference")
                break

    merged_prs = issue.get("merged_pr_evidence")
    merged_pr_count = len(merged_prs) if isinstance(merged_prs, list) else 0
    milestone = issue.get("milestone")
    milestone_title = milestone.get("title") if isinstance(milestone, dict) else None

    return ChildState(
        issue_number=issue_number if isinstance(issue_number, int) else -1,
        state=issue.get("state") if isinstance(issue.get("state"), str) else None,
        title=issue.get("title") if isinstance(issue.get("title"), str) else None,
        url=issue.get("url") if isinstance(issue.get("url"), str) else None,
        milestone_title=milestone_title if isinstance(milestone_title, str) else None,
        linked_pr_count=merged_pr_count,
        merged_pr_count=merged_pr_count,
        lineage_detected=bool(lineage_sources),
        lineage_sources=tuple(sorted(set(lineage_sources))),
    )


def _issue_summary(issue: dict[str, Any]) -> dict[str, Any]:
    milestone = issue.get("milestone")
    milestone_title = milestone.get("title") if isinstance(milestone, dict) else None
    merged_prs = issue.get("merged_pr_evidence")
    merged_pr_count = len(merged_prs) if isinstance(merged_prs, list) else 0
    return {
        "issue_number": issue.get("number"),
        "state": issue.get("state"),
        "title": issue.get("title"),
        "url": issue.get("url"),
        "milestone_title": milestone_title,
        "merged_pr_count": merged_pr_count,
    }


def _build_summary(*, parent_issue_payload: dict[str, Any], child_states: list[ChildState]) -> dict[str, Any]:
    open_count = sum(1 for item in child_states if (item.state or "").upper() == "OPEN")
    closed_count = sum(1 for item in child_states if (item.state or "").upper() == "CLOSED")
    missing_lineage = sorted(item.issue_number for item in child_states if not item.lineage_detected)
    return {
        "parent_state": parent_issue_payload.get("state"),
        "child_issue_count": len(child_states),
        "open_child_issue_count": open_count,
        "closed_child_issue_count": closed_count,
        "child_issues_missing_lineage_count": len(missing_lineage),
        "child_issues_missing_lineage": missing_lineage,
    }


def _lineage_hints(*, parent_issue: int, child_states: list[ChildState]) -> dict[str, Any]:
    missing = sorted(item.issue_number for item in child_states if not item.lineage_detected)
    return {
        "parent_issue": parent_issue,
        "missing_parent_lineage_issue_numbers": missing,
        "suggested_parent_reference_format": f"Parent issue: #{parent_issue}",
    }


def _evidence_hints(child_states: list[ChildState]) -> dict[str, Any]:
    without_pr = sorted(item.issue_number for item in child_states if item.merged_pr_count == 0)
    with_pr = sorted(item.issue_number for item in child_states if item.merged_pr_count > 0)
    return {
        "child_issues_without_merged_pr_evidence": without_pr,
        "child_issues_with_merged_pr_evidence": with_pr,
    }


def _build_warnings(
    *,
    parent_issue: int,
    parent_issue_payload: dict[str, Any],
    child_states: list[ChildState],
    lookup_warnings: list[dict[str, Any]],
) -> list[str]:
    warnings: list[str] = []
    if not child_states:
        warnings.append(
            f"No child issues were discovered for parent issue #{parent_issue} from currently detectable references."
        )
    if lookup_warnings:
        warnings.append("One or more discovered child issues could not be inspected.")

    parent_milestone = parent_issue_payload.get("milestone")
    parent_milestone_title = parent_milestone.get("title") if isinstance(parent_milestone, dict) else None
    if not isinstance(parent_milestone_title, str) or not parent_milestone_title.strip():
        warnings.append("Parent issue does not have a milestone assigned.")
    elif not _MILESTONE_NAME_PATTERN.search(parent_milestone_title.strip()):
        warnings.append("Parent issue milestone title does not match expected M<number> naming.")

    for child in child_states:
        if not child.milestone_title:
            warnings.append(f"Child issue #{child.issue_number} has no milestone assigned.")
            continue
        if not _MILESTONE_NAME_PATTERN.search(child.milestone_title):
            warnings.append(
                f"Child issue #{child.issue_number} milestone title does not match expected M<number> naming."
            )
    return sorted(set(warnings))


def _boundaries() -> list[str]:
    return [
        "read_only: true",
        "No issues were closed.",
        "No pull requests were created.",
        "No comments were added.",
        "No GitHub state was edited.",
        "No local planning or closeout mutation was performed.",
    ]

