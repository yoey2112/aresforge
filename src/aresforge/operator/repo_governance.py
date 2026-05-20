from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
from typing import Any

from aresforge.config import AppConfig


PLATFORM_REQUIRED_LABELS: tuple[str, ...] = (
    "aresforge-ready",
)

PLATFORM_OPTIONAL_LABELS: tuple[str, ...] = (
    "aresforge-automerge",
    "aresforge-blocked",
    "aresforge-needs-evidence",
    "aresforge-needs-docs",
    "aresforge-closeout-ready",
    "aresforge-managed",
    "aresforge-generated",
)

AUTOMATION_TRIGGER_LABELS: tuple[str, ...] = (
    "aresforge-ready",
    "aresforge-automerge",
)

PLATFORM_MILESTONES: tuple[str, ...] = (
    "M0 - Foundation",
    "M1 - Validation",
    "M2 - Local Automation Foundation",
    "M3 - Registry And Routing Deepening",
    "M4 - Local Operator Expansion",
)


def inspect_repo_governance(config: AppConfig) -> dict[str, Any]:
    warnings: list[str] = []
    repo_slug = f"{config.github_owner}/{config.github_repo}"

    default_branch, default_branch_warning = _inspect_default_branch(config.repo_root, repo_slug)
    if default_branch_warning:
        warnings.append(default_branch_warning)

    labels, labels_warning = _inspect_labels(config.repo_root, repo_slug)
    if labels_warning:
        warnings.append(labels_warning)
    label_set = {label.lower() for label in labels} if labels is not None else None

    milestones, milestones_warning = _inspect_milestones(config.repo_root, repo_slug)
    if milestones_warning:
        warnings.append(milestones_warning)

    open_issues, issues_warning = _inspect_open_issues(config.repo_root, repo_slug)
    if issues_warning:
        warnings.append(issues_warning)

    open_prs, prs_warning = _inspect_open_prs(config.repo_root, repo_slug)
    if prs_warning:
        warnings.append(prs_warning)

    required_labels = _label_contract_status(PLATFORM_REQUIRED_LABELS, label_set)
    optional_labels = _label_contract_status(PLATFORM_OPTIONAL_LABELS, label_set)
    trigger_labels = _label_contract_status(AUTOMATION_TRIGGER_LABELS, label_set)
    milestone_status = _milestone_status(milestones)
    issue_signal = _issue_readiness_signal(open_issues)
    pr_signal = _pr_readiness_signal(open_prs)

    return {
        "command": "inspect-repo-governance",
        "ok": True,
        "inspection_mode": "github_read_only_with_local_fallback",
        "repository_slug": repo_slug,
        "default_branch": default_branch,
        "governance_contract": {
            "required_platform_labels": list(PLATFORM_REQUIRED_LABELS),
            "optional_platform_labels": list(PLATFORM_OPTIONAL_LABELS),
            "automation_trigger_labels": list(AUTOMATION_TRIGGER_LABELS),
            "platform_milestones": list(PLATFORM_MILESTONES),
            "project_specific_label_extension_policy": (
                "Managed repositories may add project-specific labels, but must preserve the "
                "platform required and automation-trigger labels so reusable automation contracts remain intact."
            ),
            "automerge_label_policy": (
                "aresforge-automerge is a gated intent marker only and does not grant autonomous merge permission."
            ),
        },
        "required_platform_labels": required_labels,
        "optional_platform_labels": optional_labels,
        "automation_trigger_labels": trigger_labels,
        "milestone_naming_status": milestone_status,
        "open_issue_readiness_signal": issue_signal,
        "open_pr_readiness_signal": pr_signal,
        "warnings": warnings,
        "recommended_next_action": _recommended_next_action(
            required_labels=required_labels,
            milestone_status=milestone_status,
            issue_signal=issue_signal,
            pr_signal=pr_signal,
            warnings=warnings,
            repo_slug=repo_slug,
        ),
        "managed_repository_bootstrap_expectations": {
            "required_labels": list(PLATFORM_REQUIRED_LABELS),
            "optional_labels": list(PLATFORM_OPTIONAL_LABELS),
            "milestone_naming": "Adopt canonical platform milestone naming and map project-specific milestones to platform phases.",
            "default_branch": "A default branch should exist and be visible to read-only inspection.",
            "issue_pr_linking": "Implementation PRs should explicitly link target issues for QA and closeout checks.",
            "documentation": "Source-of-truth docs must be reviewed and updated before closeout for project-state-changing work.",
            "automation_boundaries": "GitHub mutation remains human-triggered and gated; read-only inspections are safe defaults.",
            "evidence_packages": "PR and closeout evidence packages should include deterministic validation outputs.",
            "closeout_expectations": "Closeout remains QA-gated and human-approved before merge and issue closure.",
        },
        "boundary_confirmations": [
            "Read-only governance inspection only.",
            "No labels, milestones, issues, pull requests, branches, settings, or workflows were mutated.",
            "No background jobs, schedulers, or polling loops were used.",
            "Issue #39 remains retired historical validation evidence and was not modified.",
        ],
    }


def _run_command(args: list[str], cwd: Path) -> tuple[bool, int | None, str, str]:
    try:
        result = subprocess.run(
            args,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return False, None, "", "command_not_found"
    except OSError as exc:
        return False, None, "", str(exc)

    return True, result.returncode, result.stdout, result.stderr


def _run_json_command(args: list[str], cwd: Path, warning_label: str) -> tuple[Any | None, str | None]:
    available, code, stdout, stderr = _run_command(args, cwd)
    if not available:
        return None, f"gh command unavailable; {warning_label} inspection is unavailable."
    if code != 0:
        message = stderr.strip() or "unknown_error"
        return None, f"gh {warning_label} inspection failed: {message}"
    try:
        return json.loads(stdout), None
    except json.JSONDecodeError as exc:
        return None, f"gh {warning_label} inspection returned invalid JSON: {exc}"


def _inspect_default_branch(repo_root: Path, repo_slug: str) -> tuple[str | None, str | None]:
    payload, warning = _run_json_command(
        [
            "gh",
            "repo",
            "view",
            repo_slug,
            "--json",
            "defaultBranchRef",
        ],
        repo_root,
        "default branch",
    )
    if warning:
        return None, warning
    if not isinstance(payload, dict):
        return None, "gh default branch inspection returned unexpected JSON shape."
    default_branch = payload.get("defaultBranchRef")
    if isinstance(default_branch, dict):
        name = default_branch.get("name")
        if isinstance(name, str) and name.strip():
            return name.strip(), None
    return None, "default branch was not present in repository metadata."


def _inspect_labels(repo_root: Path, repo_slug: str) -> tuple[list[str] | None, str | None]:
    payload, warning = _run_json_command(
        [
            "gh",
            "label",
            "list",
            "--repo",
            repo_slug,
            "--limit",
            "200",
            "--json",
            "name",
        ],
        repo_root,
        "labels",
    )
    if warning:
        return None, warning
    if not isinstance(payload, list):
        return None, "gh labels inspection returned unexpected JSON shape."

    labels: list[str] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        if isinstance(name, str) and name.strip():
            labels.append(name.strip())
    labels = sorted(set(labels), key=lambda value: (value.lower(), value))
    return labels, None


def _inspect_milestones(repo_root: Path, repo_slug: str) -> tuple[list[dict[str, Any]] | None, str | None]:
    payload, warning = _run_json_command(
        [
            "gh",
            "api",
            f"repos/{repo_slug}/milestones?state=all&per_page=100",
        ],
        repo_root,
        "milestones",
    )
    if warning:
        return None, warning
    if not isinstance(payload, list):
        return None, "gh milestones inspection returned unexpected JSON shape."

    milestones: list[dict[str, Any]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        title = item.get("title")
        state = item.get("state")
        if not isinstance(title, str) or not title.strip():
            continue
        milestones.append(
            {
                "title": title.strip(),
                "state": state if isinstance(state, str) else None,
                "number": item.get("number"),
            }
        )
    milestones.sort(key=lambda row: row["title"].lower())
    return milestones, None


def _inspect_open_issues(repo_root: Path, repo_slug: str) -> tuple[list[dict[str, Any]] | None, str | None]:
    payload, warning = _run_json_command(
        [
            "gh",
            "issue",
            "list",
            "--repo",
            repo_slug,
            "--state",
            "open",
            "--limit",
            "100",
            "--json",
            "number,labels,milestone,title,url",
        ],
        repo_root,
        "open issues",
    )
    if warning:
        return None, warning
    if not isinstance(payload, list):
        return None, "gh open issues inspection returned unexpected JSON shape."
    return _normalize_issue_or_pr_rows(payload), None


def _inspect_open_prs(repo_root: Path, repo_slug: str) -> tuple[list[dict[str, Any]] | None, str | None]:
    payload, warning = _run_json_command(
        [
            "gh",
            "pr",
            "list",
            "--repo",
            repo_slug,
            "--state",
            "open",
            "--limit",
            "100",
            "--json",
            "number,labels,title,url",
        ],
        repo_root,
        "open pull requests",
    )
    if warning:
        return None, warning
    if not isinstance(payload, list):
        return None, "gh open pull requests inspection returned unexpected JSON shape."
    return _normalize_issue_or_pr_rows(payload), None


def _normalize_issue_or_pr_rows(items: list[Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        number = item.get("number")
        if not isinstance(number, int):
            continue
        milestone = item.get("milestone")
        milestone_title = None
        if isinstance(milestone, dict):
            title = milestone.get("title")
            if isinstance(title, str) and title.strip():
                milestone_title = title.strip()
        rows.append(
            {
                "number": number,
                "title": item.get("title"),
                "url": item.get("url"),
                "labels": _normalize_labels(item.get("labels")),
                "milestone": milestone_title,
            }
        )
    rows.sort(key=lambda row: row["number"])
    return rows


def _normalize_labels(raw_labels: Any) -> list[str]:
    labels: list[str] = []
    if not isinstance(raw_labels, list):
        return labels
    for item in raw_labels:
        if isinstance(item, dict):
            name = item.get("name")
            if isinstance(name, str) and name.strip():
                labels.append(name.strip())
        elif isinstance(item, str) and item.strip():
            labels.append(item.strip())
    return sorted(set(labels), key=lambda value: (value.lower(), value))


def _label_contract_status(
    contract_labels: tuple[str, ...],
    available_labels: set[str] | None,
) -> dict[str, Any]:
    if available_labels is None:
        return {
            "contract": list(contract_labels),
            "found": [],
            "missing": [],
            "all_present": None,
            "available": False,
        }

    found: list[str] = []
    missing: list[str] = []
    for label in contract_labels:
        if label.lower() in available_labels:
            found.append(label)
        else:
            missing.append(label)
    return {
        "contract": list(contract_labels),
        "found": found,
        "missing": missing,
        "all_present": not missing,
        "available": True,
    }


def _milestone_status(milestones: list[dict[str, Any]] | None) -> dict[str, Any]:
    if milestones is None:
        return {
            "expected_platform_milestones": [],
            "missing_platform_milestones": [],
            "unknown_platform_like_milestones": [],
            "project_specific_milestones": [],
            "project_specific_mapping_expectation": (
                "Project-specific milestones should map to one platform milestone phase for governance traceability."
            ),
            "naming_ok": None,
            "available": False,
        }

    by_title: dict[str, dict[str, Any]] = {item["title"]: item for item in milestones if "title" in item}
    expected: list[dict[str, Any]] = []
    missing: list[str] = []

    for name in PLATFORM_MILESTONES:
        milestone = by_title.get(name)
        expected.append(
            {
                "title": name,
                "present": milestone is not None,
                "state": milestone.get("state") if milestone else None,
            }
        )
        if milestone is None:
            missing.append(name)

    platform_pattern = re.compile(r"^M\d+\s+-\s+")
    platform_like_unknown = [
        item["title"]
        for item in milestones
        if isinstance(item.get("title"), str)
        and platform_pattern.match(item["title"])
        and item["title"] not in PLATFORM_MILESTONES
    ]
    platform_like_unknown.sort(key=lambda value: value.lower())

    project_specific = [
        item["title"]
        for item in milestones
        if isinstance(item.get("title"), str)
        and item["title"] not in PLATFORM_MILESTONES
    ]
    project_specific.sort(key=lambda value: value.lower())

    naming_ok = not missing and not platform_like_unknown
    return {
        "expected_platform_milestones": expected,
        "missing_platform_milestones": missing,
        "unknown_platform_like_milestones": platform_like_unknown,
        "project_specific_milestones": project_specific,
        "project_specific_mapping_expectation": (
            "Project-specific milestones should map to one platform milestone phase for governance traceability."
        ),
        "naming_ok": naming_ok,
        "available": True,
    }


def _issue_readiness_signal(open_issues: list[dict[str, Any]] | None) -> dict[str, Any]:
    if open_issues is None:
        return {
            "signal": "unavailable",
            "open_issue_count": None,
            "ready_issue_count": None,
            "ready_issue_numbers": [],
            "open_issues_missing_milestone": [],
            "available": False,
        }

    ready_label = "aresforge-ready"
    ready_numbers = [
        issue["number"]
        for issue in open_issues
        if isinstance(issue, dict)
        and isinstance(issue.get("labels"), list)
        and ready_label in {label.lower() for label in issue["labels"] if isinstance(label, str)}
    ]

    missing_milestone = [
        issue["number"]
        for issue in open_issues
        if isinstance(issue, dict) and issue.get("milestone") is None
    ]

    signal = "ready_issues_available" if ready_numbers else "no_ready_issues_detected"
    return {
        "signal": signal,
        "open_issue_count": len(open_issues),
        "ready_issue_count": len(ready_numbers),
        "ready_issue_numbers": ready_numbers,
        "open_issues_missing_milestone": missing_milestone,
        "available": True,
    }


def _pr_readiness_signal(open_prs: list[dict[str, Any]] | None) -> dict[str, Any]:
    if open_prs is None:
        return {
            "signal": "unavailable",
            "open_pr_count": None,
            "automerge_intent_pr_count": None,
            "automerge_intent_pr_numbers": [],
            "qa_review_recommended": False,
            "available": False,
        }

    automerge_label = "aresforge-automerge"
    intent_pr_numbers = [
        pr["number"]
        for pr in open_prs
        if isinstance(pr, dict)
        and isinstance(pr.get("labels"), list)
        and automerge_label in {label.lower() for label in pr["labels"] if isinstance(label, str)}
    ]

    signal = "open_prs_available" if open_prs else "no_open_prs_detected"
    return {
        "signal": signal,
        "open_pr_count": len(open_prs),
        "automerge_intent_pr_count": len(intent_pr_numbers),
        "automerge_intent_pr_numbers": intent_pr_numbers,
        "qa_review_recommended": bool(open_prs),
        "available": True,
    }


def _recommended_next_action(
    *,
    required_labels: dict[str, Any],
    milestone_status: dict[str, Any],
    issue_signal: dict[str, Any],
    pr_signal: dict[str, Any],
    warnings: list[str],
    repo_slug: str,
) -> str:
    missing_required = required_labels.get("missing")
    labels_available = required_labels.get("available") is True
    if labels_available and isinstance(missing_required, list) and missing_required:
        labels = ", ".join(missing_required)
        return (
            f"Create required labels in {repo_slug}: {labels}, then rerun inspect-repo-governance. "
            "Keep mutation human-triggered and explicitly reviewed."
        )

    missing_milestones = milestone_status.get("missing_platform_milestones")
    milestones_available = milestone_status.get("available") is True
    if milestones_available and isinstance(missing_milestones, list) and missing_milestones:
        first = missing_milestones[0]
        return (
            f"Create missing platform milestone '{first}' and align project milestones to platform phases "
            "before enabling broader automation workflows."
        )

    ready_issue_count = issue_signal.get("ready_issue_count")
    if isinstance(ready_issue_count, int) and ready_issue_count > 0:
        return "Run python -m aresforge run-ready-issue-batch --plan-only to generate deterministic ready-issue planning artifacts."

    open_pr_count = pr_signal.get("open_pr_count")
    if isinstance(open_pr_count, int) and open_pr_count > 0:
        return "Run python -m aresforge qa-review-pr --pr-number <number> for open PR governance and QA readiness checks."

    if warnings:
        return "Resolve environment or GitHub CLI warnings and rerun inspect-repo-governance for a complete governance snapshot."

    return "Governance contract baseline appears healthy; maintain manual-trigger label discipline and milestone mapping for new managed repositories."