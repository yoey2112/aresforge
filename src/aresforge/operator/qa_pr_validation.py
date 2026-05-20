from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.artifact_discovery import (
    discover_local_evidence_packages,
    discover_local_review_packages,
)
from aresforge.operator.ready_issue_intake import (
    PROTECTED_ISSUE_NUMBER,
    _parse_json_payload,
    _repo_slug,
    _run_gh_command,
)

_PR_VIEW_FIELDS = (
    "number,title,state,isDraft,mergeStateStatus,baseRefName,headRefName,url,body,"
    "files,closingIssuesReferences,mergeable"
)

_FORBIDDEN_FILE_PREFIXES = (
    ".github/",
)

_DOCUMENTATION_REQUIRED_PREFIXES = (
    "src/",
    "tests/",
    "scripts/",
    "config/",
    "migrations/",
)

_GATE_ORDER = (
    "pr_exists",
    "pr_open",
    "pr_not_draft",
    "merge_state_clean",
    "linked_issue_present",
    "protected_issue_untouched",
    "validation_evidence_present",
    "required_tests_passed",
    "documentation_updated_when_required",
    "forbidden_changes_absent",
    "generated_conventions_respected",
)

_BLOCKING_GATES = {
    "pr_exists",
    "pr_open",
    "pr_not_draft",
    "merge_state_clean",
    "linked_issue_present",
}

_GATE_FIXES = {
    "pr_exists": "Confirm the PR exists and is readable via gh pr view.",
    "pr_open": "Reopen the PR or update the review target.",
    "pr_not_draft": "Mark the PR ready for review before QA validation.",
    "merge_state_clean": "Resolve merge conflicts so the PR is cleanly mergeable.",
    "linked_issue_present": "Link the PR to an expected issue using closing keywords.",
    "protected_issue_untouched": "Remove any reference to protected Issue #39.",
    "validation_evidence_present": "Provide a linked validation evidence package or review package.",
    "required_tests_passed": "Record evidence that required tests or checks passed.",
    "documentation_updated_when_required": "Update required documentation or explain why none is needed.",
    "forbidden_changes_absent": "Remove forbidden repository setting, release, or project changes.",
    "generated_conventions_respected": "Keep generated artifacts under artifacts/*/generated paths.",
}


def qa_review_pr(config: AppConfig, pr_number: int) -> dict[str, Any]:
    repo = _repo_slug(config)
    pr_payload = _fetch_pr_details(config, pr_number)
    pr_exists = pr_payload.get("ok") is True

    pr_data = pr_payload.get("pr") if pr_exists else None
    pr_title = pr_data.get("title") if isinstance(pr_data, dict) else None
    pr_url = pr_data.get("url") if isinstance(pr_data, dict) else None
    state = pr_data.get("state") if isinstance(pr_data, dict) else None
    is_draft = pr_data.get("isDraft") if isinstance(pr_data, dict) else None
    merge_state = pr_data.get("mergeStateStatus") if isinstance(pr_data, dict) else None
    base_branch = pr_data.get("baseRefName") if isinstance(pr_data, dict) else None
    head_branch = pr_data.get("headRefName") if isinstance(pr_data, dict) else None

    changed_files = _extract_changed_files(pr_data)
    linked_issue_numbers = _extract_linked_issues(pr_data)
    linked_issue_number = linked_issue_numbers[0] if linked_issue_numbers else None

    evidence_summary = _find_validation_evidence(
        config,
        linked_issue_number=linked_issue_number,
        pr_number=pr_number,
    )

    documentation_update_required = _documentation_update_required(changed_files)
    documentation_update_detected = _documentation_update_detected(changed_files)
    protected_issue_status = _protected_issue_status(linked_issue_numbers)
    forbidden_file_changes = _forbidden_file_changes(changed_files)
    generated_conventions_respected = _generated_conventions_respected(changed_files)

    gate_results = {
        "pr_exists": pr_exists,
        "pr_open": pr_exists and isinstance(state, str) and state.upper() == "OPEN",
        "pr_not_draft": pr_exists and is_draft is False,
        "merge_state_clean": pr_exists
        and isinstance(merge_state, str)
        and merge_state.upper() == "CLEAN",
        "linked_issue_present": linked_issue_number is not None,
        "protected_issue_untouched": protected_issue_status == "not_linked",
        "validation_evidence_present": evidence_summary["validation_evidence_found"],
        "required_tests_passed": evidence_summary["tests_passed"],
        "documentation_updated_when_required": (
            (not documentation_update_required) or documentation_update_detected
        ),
        "forbidden_changes_absent": not forbidden_file_changes,
        "generated_conventions_respected": generated_conventions_respected,
    }

    passed_gates, failed_gates = _partition_gates(gate_results)
    qa_decision = _qa_decision(failed_gates)
    merge_eligible = qa_decision == "pass"
    closeout_eligible = qa_decision == "pass"

    payload = {
        "ok": pr_exists,
        "command": "qa-review-pr",
        "inspection_mode": "github_read_only",
        "repo": repo,
        "pr_number": pr_number,
        "pr_url": pr_url,
        "pr_title": pr_title,
        "linked_issue_number": linked_issue_number,
        "merge_state": merge_state,
        "is_draft": is_draft,
        "branch_name": head_branch,
        "base_branch": base_branch,
        "changed_files": changed_files,
        "validation_evidence_found": evidence_summary["validation_evidence_found"],
        "review_package_found": evidence_summary["review_package_found"],
        "evidence_package_found": evidence_summary["evidence_package_found"],
        "documentation_update_required": documentation_update_required,
        "documentation_update_detected": documentation_update_detected,
        "protected_issue_status": protected_issue_status,
        "forbidden_file_changes": forbidden_file_changes,
        "failed_gates": failed_gates,
        "passed_gates": passed_gates,
        "qa_decision": qa_decision,
        "merge_eligible": merge_eligible,
        "closeout_eligible": closeout_eligible,
        "required_fixes": _required_fixes(failed_gates),
        "recommended_next_command": _recommended_next_command(pr_number),
        "boundary_confirmations": _boundary_confirmations(),
    }

    if not pr_exists and pr_payload.get("error"):
        payload["error"] = pr_payload["error"]
        if pr_payload.get("details"):
            payload["details"] = pr_payload["details"]

    return payload


def _fetch_pr_details(config: AppConfig, pr_number: int) -> dict[str, Any]:
    args = [
        "pr",
        "view",
        str(pr_number),
        "--repo",
        _repo_slug(config),
        "--json",
        _PR_VIEW_FIELDS,
    ]
    code, stdout, stderr = _run_gh_command(args)
    if code != 0:
        return {
            "ok": False,
            "error": "gh_cli_failed",
            "details": {"exit_code": code, "stderr": stderr.strip()},
        }

    try:
        pr = _parse_json_payload(stdout)
    except ValueError as exc:
        return {
            "ok": False,
            "error": "gh_cli_invalid_json",
            "details": {"message": str(exc)},
        }
    if not isinstance(pr, dict):
        return {"ok": False, "error": "pr_not_found"}

    return {"ok": True, "pr": pr}


def _extract_changed_files(pr_data: dict[str, Any] | None) -> list[str]:
    files = pr_data.get("files") if isinstance(pr_data, dict) else None
    if not isinstance(files, list):
        return []
    paths: list[str] = []
    seen = set()
    for item in files:
        if not isinstance(item, dict):
            continue
        path = item.get("path") or item.get("file") or item.get("filename")
        if not isinstance(path, str) or not path.strip():
            continue
        normalized = path.replace("\\", "/")
        if normalized in seen:
            continue
        seen.add(normalized)
        paths.append(normalized)
    return sorted(paths, key=lambda value: (value.lower(), value))


def _extract_linked_issues(pr_data: dict[str, Any] | None) -> list[int]:
    numbers: list[int] = []
    if not isinstance(pr_data, dict):
        return numbers
    closing = pr_data.get("closingIssuesReferences")
    if isinstance(closing, list):
        for entry in closing:
            if isinstance(entry, dict) and isinstance(entry.get("number"), int):
                numbers.append(entry["number"])

    if not numbers:
        body = pr_data.get("body")
        if isinstance(body, str):
            for match in re.findall(r"#(\d+)", body):
                try:
                    numbers.append(int(match))
                except ValueError:
                    continue

    return sorted(set(numbers))


def _find_validation_evidence(
    config: AppConfig,
    *,
    linked_issue_number: int | None,
    pr_number: int,
) -> dict[str, bool]:
    evidence_payload = discover_local_evidence_packages(config)
    review_payload = discover_local_review_packages(config)

    evidence_packages = evidence_payload.get("evidence_packages")
    review_packages = review_payload.get("review_packages")

    evidence_found = bool(evidence_packages)
    review_found = bool(review_packages)
    linked_evidence = False

    for payload, root_key, path_key in (
        (evidence_payload, "evidence_root", "evidence_path"),
        (review_payload, "review_package_root", "review_path"),
    ):
        root = payload.get(root_key)
        items = payload.get("evidence_packages" if path_key == "evidence_path" else "review_packages")
        if not isinstance(root, str) or not isinstance(items, list):
            continue
        root_path = Path(root)
        for item in items:
            if not isinstance(item, dict):
                continue
            raw_path = item.get(path_key)
            if not isinstance(raw_path, str):
                continue
            if _path_mentions_number(raw_path, linked_issue_number, pr_number):
                linked_evidence = True
                continue
            if _file_mentions_number(root_path / raw_path, linked_issue_number, pr_number):
                linked_evidence = True

    tests_passed = linked_evidence

    return {
        "validation_evidence_found": linked_evidence,
        "review_package_found": review_found,
        "evidence_package_found": evidence_found,
        "tests_passed": tests_passed,
    }


def _path_mentions_number(path: str, issue_number: int | None, pr_number: int) -> bool:
    lowered = path.lower()
    if issue_number is not None and f"issue-{issue_number}" in lowered:
        return True
    return f"pr-{pr_number}" in lowered


def _file_mentions_number(path: Path, issue_number: int | None, pr_number: int) -> bool:
    if not path.exists() or not path.is_file():
        return False
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return False
    except UnicodeDecodeError:
        return False

    content_lower = content.lower()
    if issue_number is not None:
        if f"issue #{issue_number}" in content_lower:
            return True
        if f"issue-{issue_number}" in content_lower:
            return True
        if f"#{issue_number}" in content_lower:
            return True
    return f"pr-{pr_number}" in content_lower or f"#{pr_number}" in content_lower


def _documentation_update_required(changed_files: list[str]) -> bool:
    for path in changed_files:
        if path.startswith(_DOCUMENTATION_REQUIRED_PREFIXES):
            return True
    return False


def _documentation_update_detected(changed_files: list[str]) -> bool:
    for path in changed_files:
        if path.startswith("docs/") or path.startswith(".agent/"):
            return True
    return False


def _protected_issue_status(linked_issues: list[int]) -> str:
    if not linked_issues:
        return "not_linked"
    if linked_issues[0] == PROTECTED_ISSUE_NUMBER:
        return "linked_to_protected_issue"
    if PROTECTED_ISSUE_NUMBER in linked_issues:
        return "references_protected_issue"
    return "not_linked"


def _forbidden_file_changes(changed_files: list[str]) -> list[str]:
    forbidden: list[str] = []
    for path in changed_files:
        for prefix in _FORBIDDEN_FILE_PREFIXES:
            if path.startswith(prefix):
                forbidden.append(path)
                break
    return sorted(forbidden, key=lambda value: (value.lower(), value))


def _generated_conventions_respected(changed_files: list[str]) -> bool:
    for path in changed_files:
        if path.startswith("artifacts/") and "/generated/" not in path:
            return False
    return True


def _partition_gates(gate_results: dict[str, bool]) -> tuple[list[str], list[str]]:
    passed: list[str] = []
    failed: list[str] = []
    for gate in _GATE_ORDER:
        if gate_results.get(gate):
            passed.append(gate)
        else:
            failed.append(gate)
    return passed, failed


def _qa_decision(failed_gates: list[str]) -> str:
    if any(gate in _BLOCKING_GATES for gate in failed_gates):
        return "blocked"
    if failed_gates:
        return "fail"
    return "pass"


def _required_fixes(failed_gates: list[str]) -> list[str]:
    fixes: list[str] = []
    for gate in failed_gates:
        fix = _GATE_FIXES.get(gate)
        if fix:
            fixes.append(fix)
    return fixes


def _recommended_next_command(pr_number: int) -> str:
    return f"qa-review-pr --pr-number {pr_number}"


def _boundary_confirmations() -> list[str]:
    return [
        "Human-triggered GitHub read-only inspection.",
        "No GitHub mutation was performed by this command surface.",
        "No merge, closeout, labeling, or commenting was performed.",
        "No background polling or scheduled behavior was performed.",
        "Issue #39 was not modified.",
    ]
