from __future__ import annotations

import json
import re
import subprocess
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.child_evidence_marker_template import generate_child_evidence_marker_template
from aresforge.operator.evidence_completeness_checker import check_issue_evidence_readiness
from aresforge.operator.milestone_dashboard import inspect_milestone_dashboard
from aresforge.operator.ready_issue_intake import PROTECTED_ISSUE_NUMBER, fetch_issue_details

COMMAND_NAME = "generate-evidence-comment-template"
_AC_PATTERN = re.compile(r"^\s*(?:[-*]|\d+\.)\s+(?P<item>.+)$")


def generate_evidence_comment_template(config: AppConfig, *, issue_number: int) -> dict[str, Any]:
    issue_payload = fetch_issue_details(config, issue_number)
    if not issue_payload.get("ok"):
        return {
            "command": COMMAND_NAME,
            "ok": False,
            "read_only": True,
            "target_issue": issue_number,
            "parent_issue": None,
            "error": issue_payload.get("error", "issue_lookup_failed"),
            "details": issue_payload.get("details"),
            "boundary_confirmations": _boundaries(),
        }

    issue = issue_payload.get("issue")
    if not isinstance(issue, dict):
        return {
            "command": COMMAND_NAME,
            "ok": False,
            "read_only": True,
            "target_issue": issue_number,
            "parent_issue": None,
            "error": "issue_lookup_failed",
            "boundary_confirmations": _boundaries(),
        }

    target_issue = issue.get("number") if isinstance(issue.get("number"), int) else issue_number
    parent_issue = _resolve_parent_issue(issue=issue, target_issue=target_issue)
    issue_readiness = check_issue_evidence_readiness(config, issue_number=target_issue)
    pr_evidence = _collect_pr_evidence(config, issue)
    parent_context = _collect_parent_context(config, parent_issue=parent_issue)
    marker_payload = _collect_canonical_marker_payload(
        config,
        parent_issue=parent_issue,
        target_issue=target_issue,
    )

    template = _render_template(
        issue=issue,
        parent_issue=parent_issue,
        parent_context=parent_context,
        issue_readiness=issue_readiness,
        pr_evidence=pr_evidence,
        marker_payload=marker_payload,
    )
    warnings = _warnings(
        target_issue=target_issue,
        parent_issue=parent_issue,
        issue_readiness=issue_readiness,
        pr_evidence=pr_evidence,
        parent_context=parent_context,
        marker_payload=marker_payload,
    )

    return {
        "command": COMMAND_NAME,
        "ok": True,
        "read_only": True,
        "inspection_mode": "github_read_only_template_generation",
        "repo": f"{config.github_owner}/{config.github_repo}",
        "target_issue": {
            "number": target_issue,
            "title": issue.get("title"),
            "state": issue.get("state"),
            "url": issue.get("url"),
        },
        "parent_issue": parent_issue,
        "template": template,
        "template_summary": {
            "issue_specific": True,
            "includes_implementation_evidence_section": True,
            "includes_validation_evidence_section": True,
            "includes_files_changed_section": True,
            "includes_acceptance_criteria_mapping": True,
            "includes_closeout_readiness_statement": True,
            "includes_canonical_marker_completeness_section": True,
            "contains_nested_markdown_fences": "```" in template,
        },
        "evidence_status": {
            "readiness_ok": bool(issue_readiness.get("ok")),
            "classification": issue_readiness.get("classification"),
            "reasons": issue_readiness.get("reasons") if isinstance(issue_readiness.get("reasons"), list) else [],
            "closeout_ready": ((issue_readiness.get("duplicate_noop_planning") or {}).get("closeout_ready")),
            "related_pr_count": len(pr_evidence["prs"]),
            "related_commit_count": len(pr_evidence["commits"]),
            "files_changed_count": len(pr_evidence["files_changed"]),
        },
        "canonical_marker": marker_payload["canonical_marker"],
        "canonical_marker_text": marker_payload["canonical_marker_text"],
        "canonical_marker_completeness": marker_payload["canonical_marker_completeness"],
        "closeout_comment_ready": marker_payload["canonical_marker_completeness"]["marker_complete"],
        "safety_gates": {
            "read_only": True,
            "mutation_performed": False,
            "post_comments": False,
            "close_issues": False,
            "create_branches": False,
            "create_prs": False,
            "bulk_closeout_allowed": False,
            "operator_review_required": True,
        },
        "required_operator_actions": _required_operator_actions(parent_issue=parent_issue),
        "boundary_confirmations": _boundary_confirmations(parent_context=parent_context, parent_issue=parent_issue),
        "warnings": warnings,
    }


def _resolve_parent_issue(*, issue: dict[str, Any], target_issue: int) -> int | None:
    refs = issue.get("reference_classification")
    if not isinstance(refs, dict):
        return None

    parent_child = refs.get("parent_child_references")
    if isinstance(parent_child, dict):
        parent_numbers = parent_child.get("parent_issue_numbers")
        if isinstance(parent_numbers, list):
            normalized = [
                number
                for number in parent_numbers
                if isinstance(number, int) and number not in (target_issue, PROTECTED_ISSUE_NUMBER)
            ]
            if normalized:
                return min(normalized)

    implementation_numbers = refs.get("implementation_issue_numbers")
    if isinstance(implementation_numbers, list):
        normalized = [
            number
            for number in implementation_numbers
            if isinstance(number, int) and number not in (target_issue, PROTECTED_ISSUE_NUMBER)
        ]
        if normalized:
            return min(normalized)

    return None


def _collect_parent_context(config: AppConfig, *, parent_issue: int | None) -> dict[str, Any]:
    if not isinstance(parent_issue, int):
        return {
            "ok": False,
            "detected": False,
        }
    dashboard = inspect_milestone_dashboard(config, parent_issue=parent_issue)
    if not dashboard.get("ok"):
        return {
            "ok": False,
            "detected": True,
            "parent_issue": parent_issue,
            "error": dashboard.get("error", "dashboard_lookup_failed"),
        }
    parent_payload = dashboard.get("parent_issue") if isinstance(dashboard.get("parent_issue"), dict) else {}
    final_reconciliation = (
        dashboard.get("final_reconciliation") if isinstance(dashboard.get("final_reconciliation"), dict) else {}
    )
    return {
        "ok": True,
        "detected": True,
        "parent_issue": {
            "issue_number": parent_payload.get("issue_number"),
            "state": parent_payload.get("state"),
            "title": parent_payload.get("title"),
            "url": parent_payload.get("url"),
        },
        "dashboard": {
            "recommended_next_child_issue": ((dashboard.get("dashboard") or {}).get("recommended_next_child_issue")),
            "parent_should_remain_open": ((dashboard.get("dashboard") or {}).get("parent_should_remain_open")),
            "milestone_closeout_ready": ((dashboard.get("dashboard") or {}).get("milestone_closeout_ready")),
        },
        "final_reconciliation_issue": final_reconciliation.get("final_reconciliation_issue"),
        "child_summary": dashboard.get("child_summary"),
    }


def _collect_pr_evidence(config: AppConfig, issue: dict[str, Any]) -> dict[str, Any]:
    repo = f"{config.github_owner}/{config.github_repo}"
    merged_prs = issue.get("merged_pr_evidence") if isinstance(issue.get("merged_pr_evidence"), list) else []
    collected_prs: list[dict[str, Any]] = []
    collected_commits: list[dict[str, Any]] = []
    collected_files: set[str] = set()
    warnings: list[str] = []

    for item in merged_prs:
        if not isinstance(item, dict):
            continue
        pr_number = item.get("number")
        if not isinstance(pr_number, int):
            continue
        pr_details = _fetch_pr_details(repo=repo, pr_number=pr_number)
        collected_prs.append(
            {
                "number": pr_number,
                "url": item.get("url"),
                "title": item.get("title"),
                "state": item.get("state"),
                "merged_at": item.get("merged_at"),
                "merge_commit": pr_details.get("merge_commit"),
            }
        )
        merge_commit = pr_details.get("merge_commit")
        if isinstance(merge_commit, str) and merge_commit:
            collected_commits.append(
                {
                    "sha": merge_commit,
                    "source": f"pr:{pr_number}",
                }
            )
        for path in pr_details.get("files", []):
            if isinstance(path, str) and path:
                collected_files.add(path)
        warning = pr_details.get("warning")
        if isinstance(warning, str) and warning:
            warnings.append(warning)

    collected_prs.sort(key=lambda item: int(item["number"]))
    collected_commits.sort(key=lambda item: item["sha"])
    files_changed = sorted(collected_files)

    return {
        "prs": collected_prs,
        "commits": collected_commits,
        "files_changed": files_changed,
        "warnings": sorted(set(warnings)),
    }


def _fetch_pr_details(*, repo: str, pr_number: int) -> dict[str, Any]:
    result = subprocess.run(
        [
            "gh",
            "pr",
            "view",
            str(pr_number),
            "--repo",
            repo,
            "--json",
            "mergeCommit,files",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return {
            "merge_commit": None,
            "files": [],
            "warning": f"Unable to inspect PR #{pr_number} details for merge commit/files.",
        }
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {
            "merge_commit": None,
            "files": [],
            "warning": f"PR #{pr_number} details returned invalid JSON.",
        }

    merge_commit = payload.get("mergeCommit")
    merge_commit_sha = merge_commit.get("oid") if isinstance(merge_commit, dict) else None
    files_raw = payload.get("files") if isinstance(payload.get("files"), list) else []
    files = [item.get("path") for item in files_raw if isinstance(item, dict) and isinstance(item.get("path"), str)]
    files = sorted(set(files))

    return {
        "merge_commit": merge_commit_sha,
        "files": files,
    }


def _render_template(
    *,
    issue: dict[str, Any],
    parent_issue: int | None,
    parent_context: dict[str, Any],
    issue_readiness: dict[str, Any],
    pr_evidence: dict[str, Any],
    marker_payload: dict[str, Any],
) -> str:
    target_issue = issue.get("number")
    issue_title = issue.get("title") if isinstance(issue.get("title"), str) else ""
    readiness_classification = issue_readiness.get("classification") if isinstance(issue_readiness.get("classification"), str) else "unknown"
    readiness_reasons = issue_readiness.get("reasons") if isinstance(issue_readiness.get("reasons"), list) else []
    parent_state = ((parent_context.get("parent_issue") or {}).get("state")) if isinstance(parent_context, dict) else None
    final_issue = parent_context.get("final_reconciliation_issue") if isinstance(parent_context, dict) else None
    final_number = final_issue.get("issue_number") if isinstance(final_issue, dict) else None
    final_state = final_issue.get("state") if isinstance(final_issue, dict) else None

    acceptance_items = _extract_acceptance_items(issue.get("body") if isinstance(issue.get("body"), str) else "")
    pr_lines = _render_pr_lines(pr_evidence.get("prs") if isinstance(pr_evidence.get("prs"), list) else [])
    commit_lines = _render_commit_lines(pr_evidence.get("commits") if isinstance(pr_evidence.get("commits"), list) else [])
    file_lines = _render_file_lines(pr_evidence.get("files_changed") if isinstance(pr_evidence.get("files_changed"), list) else [])
    readiness_lines = _render_readiness_lines(readiness_reasons)
    canonical_marker_text = str(marker_payload.get("canonical_marker_text") or "")
    canonical_marker_completeness = (
        marker_payload.get("canonical_marker_completeness")
        if isinstance(marker_payload.get("canonical_marker_completeness"), dict)
        else {}
    )
    marker_state = canonical_marker_completeness.get("state")
    marker_complete = canonical_marker_completeness.get("marker_complete")
    missing_fields = canonical_marker_completeness.get("missing_required_fields")
    invalid_reasons = canonical_marker_completeness.get("invalid_reasons")
    missing_fields_text = (
        ", ".join(str(item) for item in missing_fields)
        if isinstance(missing_fields, list) and missing_fields
        else "<none>"
    )
    invalid_reasons_text = (
        ", ".join(str(item) for item in invalid_reasons)
        if isinstance(invalid_reasons, list) and invalid_reasons
        else "<none>"
    )

    lines = [
        "### Issue-Specific Evidence Mapping",
        "",
        f"- Target issue: #{target_issue}",
        f"- Issue title: {issue_title}",
        f"- Issue state: {issue.get('state')}",
        f"- Parent issue: #{parent_issue} (state: {parent_state})" if isinstance(parent_issue, int) else "- Parent issue: not detected from lineage metadata",
        (
            f"- Final reconciliation issue: #{final_number} (state: {final_state})"
            if isinstance(final_number, int)
            else "- Final reconciliation issue: not detected from parent context"
        ),
        "",
        "Implementation evidence:",
        *pr_lines,
        *commit_lines,
        "",
        "Files changed (where known):",
        *file_lines,
        "",
        "Validation evidence:",
        f"- check-issue-evidence-readiness classification: {readiness_classification}",
        *readiness_lines,
        "- git diff --check: <fill-after-validation>",
        "- python -m pytest: <fill-after-validation>",
        "- python -m aresforge inspect-repo-governance: <fill-after-validation>",
        f"- python -m aresforge generate-evidence-comment-template --issue {target_issue}: generated",
        f"- python -m aresforge generate-child-closeout-script --issue {target_issue}: generated",
        "",
        "Canonical marker completeness:",
        f"- state: {marker_state}",
        f"- marker_complete: {marker_complete}",
        f"- missing_required_fields: {missing_fields_text}",
        f"- invalid_reasons: {invalid_reasons_text}",
        (
            "- marker_repair_guidance: resolve missing/invalid marker fields before treating this comment as closeout-ready."
            if marker_complete is not True
            else "- marker_repair_guidance: none required."
        ),
        "",
        "Canonical marker (copy/paste-safe):",
        canonical_marker_text if canonical_marker_text else "<missing>",
        "",
        "Acceptance criteria mapping:",
        *acceptance_items,
        "",
        "Closeout readiness statement:",
        "- This template is issue-specific and read-only; it does not close issues or post comments.",
        "- Do not infer completion from placeholders; replace with concrete evidence before closeout.",
        "- Child issue closeout is not ready until implementation evidence and validation evidence are both concrete.",
        "",
        "Safety and boundary confirmations:",
        "- No broad mutation or bulk closeout was used to generate this template.",
        "- No branch, PR, commit, label, milestone, comment, or close mutation was performed.",
        (
            f"- Parent #{parent_issue} remains open when applicable."
            if isinstance(parent_issue, int)
            else "- Parent lineage could not be detected automatically; confirm parent-open status manually."
        ),
        (
            f"- Final reconciliation issue #{final_number} remains open when applicable."
            if isinstance(final_number, int)
            else "- Final reconciliation issue could not be detected automatically from current context."
        ),
        "",
        "Operator checklist before closing this issue:",
        "- Confirm this evidence mapping comment is posted before running any issue-close command.",
        "- Confirm no prior milestones or protected historical issues were mutated.",
        "- Confirm exactly one target issue is closed when closeout is executed.",
        "",
        "Optional structured evidence map (preferred when posting):",
        "ARESFORGE_EVIDENCE_MAP_START",
        f"Issue: #{target_issue}",
        "Evidence Type: child-closeout",
        "Implemented By: PR #<pr_number>",
        "Merged Commit: <commit_hash>",
        "Validation:",
        "- git diff --check: pass",
        "- python -m pytest: pass",
        "- python -m aresforge inspect-repo-governance: pass",
        "Closeout Ready: true",
        "ARESFORGE_EVIDENCE_MAP_END",
    ]
    return "\n".join(lines) + "\n"


def _extract_acceptance_items(body: str) -> list[str]:
    items: list[str] = []
    for line in body.splitlines():
        match = _AC_PATTERN.match(line)
        if not match:
            continue
        item = match.group("item").strip()
        if not item:
            continue
        if item.lower().startswith("target issue:"):
            continue
        items.append(f"- {item}")
    if not items:
        return ["- No explicit acceptance-criteria bullet list detected in issue body."]
    return items[:8]


def _render_pr_lines(prs: list[dict[str, Any]]) -> list[str]:
    if not prs:
        return ["- Related PRs: none detected from merged PR evidence."]
    lines = ["- Related PRs:"]
    for item in prs:
        merge_commit = item.get("merge_commit") if isinstance(item.get("merge_commit"), str) else "unknown"
        lines.append(
            f"  - #{item.get('number')}: {item.get('title')} ({item.get('url')}) merged_at={item.get('merged_at')} merge_commit={merge_commit}"
        )
    return lines


def _render_commit_lines(commits: list[dict[str, Any]]) -> list[str]:
    if not commits:
        return ["- Related commits: none detected from merged PR metadata."]
    lines = ["- Related commits:"]
    for item in commits:
        lines.append(f"  - {item.get('sha')} ({item.get('source')})")
    return lines


def _render_file_lines(paths: list[str]) -> list[str]:
    if not paths:
        return ["- <none detected>"]
    return [f"- {path}" for path in paths]


def _render_readiness_lines(reasons: list[Any]) -> list[str]:
    if not reasons:
        return ["- Evidence-readiness reasons: <none reported>"]
    lines = ["- Evidence-readiness reasons:"]
    for reason in reasons:
        lines.append(f"  - {reason}")
    return lines


def _required_operator_actions(*, parent_issue: int | None) -> list[str]:
    actions = [
        "Review and replace placeholders with concrete implementation and validation evidence before posting.",
        "Post the issue-specific evidence mapping comment before running any closeout command.",
        "Confirm read-only command output aligns with latest merged PR and validation outputs.",
        "Run closeout using target-issue-only commands; do not use bulk closeout operations.",
    ]
    if isinstance(parent_issue, int):
        actions.append(f"Verify parent issue #{parent_issue} remains open after child closeout.")
    return actions


def _warnings(
    *,
    target_issue: int,
    parent_issue: int | None,
    issue_readiness: dict[str, Any],
    pr_evidence: dict[str, Any],
    parent_context: dict[str, Any],
    marker_payload: dict[str, Any],
) -> list[str]:
    warnings = [
        "Template generation is read-only; no GitHub mutation was performed.",
        "Do not infer closeout completion from this template until evidence placeholders are replaced.",
    ]
    if issue_readiness.get("classification") != "ready":
        warnings.append("Issue evidence readiness is not fully ready; closeout should remain blocked until evidence is complete.")
    for warning in pr_evidence.get("warnings", []):
        if isinstance(warning, str):
            warnings.append(warning)
    if parent_issue is None:
        warnings.append("Parent issue lineage was not detected automatically from issue metadata.")
    if parent_context.get("detected") is True and not parent_context.get("ok"):
        warnings.append("Parent dashboard context could not be fully inspected; verify parent/final reconciliation states manually.")
    marker_completeness = (
        marker_payload.get("canonical_marker_completeness")
        if isinstance(marker_payload.get("canonical_marker_completeness"), dict)
        else {}
    )
    if marker_completeness.get("marker_complete") is not True:
        warnings.append(
            "Canonical marker completeness is not ready; missing/invalid marker fields must be resolved before closeout comment posting."
        )
    if target_issue == 301:
        warnings.append("Target issue is #301 final reconciliation; do not close without explicit final-reconciliation authorization.")
    return warnings


def _collect_canonical_marker_payload(
    config: AppConfig,
    *,
    parent_issue: int | None,
    target_issue: int,
) -> dict[str, Any]:
    if not isinstance(parent_issue, int):
        missing_fields_list = ["parent_issue"]
        invalid_reasons_list = ["parent_issue_lineage_not_detected"]
        return {
            "canonical_marker": {
                "marker_type": "child_evidence",
                "marker_state": "incomplete",
                "missing_required_fields": missing_fields_list,
                "invalid_reasons": invalid_reasons_list,
            },
            "canonical_marker_text": "",
            "canonical_marker_completeness": {
                "state": "incomplete",
                "marker_type": "child_evidence",
                "marker_scope": "generated_closeout_comment",
                "missing_required_fields": missing_fields_list,
                "invalid_reasons": invalid_reasons_list,
                "marker_complete": False,
                "post_hoc_marker_repair_required": True,
            },
        }

    marker_payload = generate_child_evidence_marker_template(
        config,
        parent_issue=parent_issue,
        child_issue=target_issue,
    )
    canonical_marker = (
        marker_payload.get("canonical_marker")
        if isinstance(marker_payload.get("canonical_marker"), dict)
        else {}
    )
    canonical_marker_text = str(marker_payload.get("canonical_marker_text") or "")
    missing_fields = canonical_marker.get("missing_required_fields")
    invalid_reasons = canonical_marker.get("invalid_reasons")
    missing_fields_list = list(missing_fields) if isinstance(missing_fields, (list, tuple)) else []
    invalid_reasons_list = list(invalid_reasons) if isinstance(invalid_reasons, (list, tuple)) else []
    marker_state = canonical_marker.get("marker_state") if isinstance(canonical_marker.get("marker_state"), str) else "unknown"
    marker_complete = marker_state == "ready" and not missing_fields_list and not invalid_reasons_list
    return {
        "canonical_marker": canonical_marker,
        "canonical_marker_text": canonical_marker_text,
        "canonical_marker_completeness": {
            "state": marker_state,
            "marker_type": canonical_marker.get("marker_type"),
            "marker_scope": "generated_closeout_comment",
            "missing_required_fields": missing_fields_list,
            "invalid_reasons": invalid_reasons_list,
            "marker_complete": marker_complete,
            "post_hoc_marker_repair_required": not marker_complete,
        },
    }


def _boundary_confirmations(*, parent_context: dict[str, Any], parent_issue: int | None) -> list[str]:
    confirmations = list(_boundaries())
    if isinstance(parent_issue, int):
        parent_state = ((parent_context.get("parent_issue") or {}).get("state")) if isinstance(parent_context, dict) else None
        confirmations.append(f"parent_issue_context_detected: {parent_issue}")
        confirmations.append(f"parent_issue_state_observed: {parent_state}")
    final_issue = parent_context.get("final_reconciliation_issue") if isinstance(parent_context, dict) else None
    if isinstance(final_issue, dict) and isinstance(final_issue.get("issue_number"), int):
        confirmations.append(f"final_reconciliation_issue_detected: {final_issue.get('issue_number')}")
        confirmations.append(f"final_reconciliation_state_observed: {final_issue.get('state')}")
    return confirmations


def _boundaries() -> list[str]:
    return [
        "read_only: true",
        "mutation_performed: false",
        "post_comments: false",
        "close_issues: false",
        "create_branches: false",
        "create_prs: false",
        "bulk_closeout_allowed: false",
    ]
