from __future__ import annotations

import json
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.evidence_bundle import EvidenceBundleInput, render_evidence_bundle_text
from aresforge.operator.ready_issue_intake import _repo_slug, _run_gh_command, fetch_issue_details
from aresforge.operator.validation_summary import ValidationEntryInput, build_validation_summary

COMMAND_NAME = "generate-pr-evidence-bundle"


def generate_pr_evidence_bundle(
    config: AppConfig,
    *,
    issue_number: int,
    pr_number: int,
    marker_context: dict[str, str] | None = None,
) -> dict[str, Any]:
    blocked_reasons: list[str] = []
    if issue_number <= 0:
        blocked_reasons.append("invalid_issue_target")
    if pr_number <= 0:
        blocked_reasons.append("invalid_pr_target")
    if blocked_reasons:
        return {
            "command": COMMAND_NAME,
            "ok": False,
            "read_only": True,
            "issue": issue_number,
            "pr": pr_number,
            "error": "invalid_target",
            "blocked_reasons": sorted(set(blocked_reasons)),
        }

    issue_payload = fetch_issue_details(config, issue_number)
    if not issue_payload.get("ok"):
        return {
            "command": COMMAND_NAME,
            "ok": False,
            "read_only": True,
            "issue": issue_number,
            "pr": pr_number,
            "error": issue_payload.get("error", "issue_lookup_failed"),
            "details": issue_payload.get("details"),
        }
    pr_payload = _fetch_pr_details(config, pr_number)
    if not pr_payload.get("ok"):
        return {
            "command": COMMAND_NAME,
            "ok": False,
            "read_only": True,
            "issue": issue_number,
            "pr": pr_number,
            "error": pr_payload.get("error", "pr_lookup_failed"),
            "details": pr_payload.get("details"),
        }

    issue = issue_payload.get("issue") if isinstance(issue_payload.get("issue"), dict) else {}
    pr = pr_payload.get("pr") if isinstance(pr_payload.get("pr"), dict) else {}
    files_changed = pr.get("files_changed") if isinstance(pr.get("files_changed"), list) else []
    files_lines = tuple(
        item
        for item in (str(path).strip() for path in files_changed)
        if item
    )
    validation_summary = build_validation_summary(
        [
            ValidationEntryInput(command="git diff --check", state="unknown"),
            ValidationEntryInput(command="python -m pytest", state="unknown"),
            ValidationEntryInput(command="python -m aresforge inspect-repo-governance", state="unknown"),
        ]
    )

    from aresforge.operator.pr_evidence_marker_template import generate_pr_evidence_marker_template

    context = marker_context if isinstance(marker_context, dict) else {}
    canonical = generate_pr_evidence_marker_template(
        config,
        issue_number=issue_number,
        pr_number=pr_number,
        branch=_context_value(context, "branch"),
        commit=_context_value(context, "commit"),
        changed_files=_context_value(context, "changed_files"),
        validation_summary=_context_value(context, "validation_summary"),
        merge_status=_context_value(context, "merge_status"),
        safety_posture=_context_value(context, "safety_posture"),
        evidence_status=_context_value(context, "evidence_status"),
        notes_warnings=_context_value(context, "notes_warnings"),
    )
    canonical_marker_text = str(canonical.get("canonical_marker_text") or "")
    canonical_marker = canonical.get("canonical_marker") if isinstance(canonical.get("canonical_marker"), dict) else {}
    missing_fields = canonical_marker.get("missing_required_fields")
    invalid_reasons = canonical_marker.get("invalid_reasons")
    missing_fields_list = list(missing_fields) if isinstance(missing_fields, (list, tuple)) else []
    invalid_reasons_list = list(invalid_reasons) if isinstance(invalid_reasons, (list, tuple)) else []
    marker_state = canonical_marker.get("marker_state") if isinstance(canonical_marker.get("marker_state"), str) else "unknown"
    marker_complete = marker_state == "ready" and not missing_fields_list and not invalid_reasons_list

    pr_body_text = render_evidence_bundle_text(
        EvidenceBundleInput(
            summary_lines=(
                f"- PR evidence bundle generated for PR #{pr_number}.",
                f"- Linked issue: #{issue_number}.",
                "- Read-only generation only; no PR updates were executed.",
            ),
            issue_ref=f"Issue: #{issue_number} - {issue.get('title') or '<unknown>'}",
            pr_ref=f"PR: #{pr_number} - {pr.get('title') or '<unknown>'}",
            branch_name=pr.get("head_branch") if isinstance(pr.get("head_branch"), str) else "<unknown>",
            commit_sha=pr.get("merge_commit") if isinstance(pr.get("merge_commit"), str) else "<none>",
            files_changed=files_lines or ("<none>",),
            validation_lines=tuple(validation_summary["summary_lines"]),
            safety_notes=(
                "- Read-only by default.",
                "- No PR body update was executed by this command.",
                "- Targeted PR mutation requires explicit operator approval.",
            ),
            warnings=(
                "- Replace validation placeholders with concrete command outputs before mutation.",
                "- Keep mutation targeted to one PR only.",
            ),
        )
    )
    pr_body_text += "\n### Canonical Marker\n\n"
    pr_body_text += canonical_marker_text if canonical_marker_text else "<missing>\n"

    return {
        "command": COMMAND_NAME,
        "ok": True,
        "read_only": True,
        "issue": {
            "number": issue_number,
            "title": issue.get("title"),
            "url": issue.get("url"),
            "state": issue.get("state"),
        },
        "pr": {
            "number": pr_number,
            "title": pr.get("title"),
            "url": pr.get("url"),
            "head_branch": pr.get("head_branch"),
            "merge_commit": pr.get("merge_commit"),
            "files_changed": list(files_lines),
        },
        "canonical_marker": canonical_marker,
        "canonical_marker_text": canonical_marker_text,
        "canonical_marker_completeness": {
            "state": marker_state,
            "missing_required_fields": missing_fields_list,
            "invalid_reasons": invalid_reasons_list,
            "marker_complete": marker_complete,
            "post_hoc_marker_repair_required": not marker_complete,
        },
        "pr_body_text": pr_body_text,
        "targeted_pr_update_guidance": [
            f"1. Save reviewed body text to a local file for PR #{pr_number} (for example artifacts/pr-{pr_number}-body.md).",
            f"2. Targeted update command (operator-approved): gh pr edit {pr_number} --body-file artifacts/pr-{pr_number}-body.md",
            f"3. Optional controlled path: python -m aresforge prepare-pr-body-update --pr-number {pr_number} --target-issue {issue_number} --scope-summary \"<summary>\"",
        ],
        "mutation": {
            "attempted": False,
            "allowed_by_default": False,
            "requires_explicit_operator_approval": True,
        },
    }


def _fetch_pr_details(config: AppConfig, pr_number: int) -> dict[str, Any]:
    code, stdout, stderr = _run_gh_command(
        [
            "pr",
            "view",
            str(pr_number),
            "--repo",
            _repo_slug(config),
            "--json",
            "number,title,url,headRefName,mergeCommit,files",
        ]
    )
    if code != 0:
        return {
            "ok": False,
            "error": "pr_lookup_failed",
            "details": stderr.strip() or stdout.strip() or "gh_pr_view_failed",
        }
    try:
        payload = json.loads(stdout)
    except Exception:
        return {
            "ok": False,
            "error": "pr_lookup_parse_failed",
            "details": "Unable to parse gh pr view JSON output.",
        }

    if not isinstance(payload, dict):
        return {
            "ok": False,
            "error": "pr_lookup_parse_failed",
            "details": "Unexpected gh pr view payload shape.",
        }

    files = payload.get("files") if isinstance(payload.get("files"), list) else []
    return {
        "ok": True,
        "pr": {
            "number": payload.get("number"),
            "title": payload.get("title"),
            "url": payload.get("url"),
            "head_branch": payload.get("headRefName"),
            "merge_commit": (
                payload["mergeCommit"].get("oid")
                if isinstance(payload.get("mergeCommit"), dict)
                else None
            ),
            "files_changed": [
                item.get("path")
                for item in files
                if isinstance(item, dict) and isinstance(item.get("path"), str)
            ],
        },
    }


def _context_value(context: dict[str, str], key: str) -> str | None:
    value = context.get(key)
    if value is None:
        return None
    text = str(value).strip()
    return text or None
