from __future__ import annotations

from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.child_evidence_marker_template import generate_child_evidence_marker_template
from aresforge.operator.evidence_bundle import EvidenceBundleInput, render_evidence_bundle_text
from aresforge.operator.ready_issue_intake import fetch_issue_details
from aresforge.operator.validation_summary import ValidationEntryInput, build_validation_summary

COMMAND_NAME = "generate-child-closeout-evidence-bundle"


def generate_child_closeout_evidence_bundle(
    config: AppConfig,
    *,
    parent_issue: int,
    child_issue: int,
) -> dict[str, Any]:
    issue_payload = fetch_issue_details(config, child_issue)
    if not issue_payload.get("ok"):
        return {
            "command": COMMAND_NAME,
            "ok": False,
            "read_only": True,
            "parent_issue": parent_issue,
            "child_issue": child_issue,
            "error": issue_payload.get("error", "issue_lookup_failed"),
            "details": issue_payload.get("details"),
        }

    issue = issue_payload.get("issue") if isinstance(issue_payload.get("issue"), dict) else {}
    validation_summary = build_validation_summary(
        [
            ValidationEntryInput(command="git diff --check", state="unknown"),
            ValidationEntryInput(command="python -m pytest", state="unknown"),
            ValidationEntryInput(command="python -m aresforge inspect-repo-governance", state="unknown"),
        ]
    )
    bundle = EvidenceBundleInput(
        summary_lines=(
            f"- Child closeout evidence bundle generated for issue #{child_issue}.",
            "- Read-only output only; no issue comments or closeout mutation executed.",
        ),
        issue_ref=f"Issue: #{child_issue}",
        pr_ref="PR: <fill-after-merge>",
        branch_name="<fill-branch>",
        commit_sha="<fill-main-commit>",
        files_changed=("<fill-files-changed>",),
        validation_lines=tuple(validation_summary["summary_lines"]),
        safety_notes=(
            "- Read-only by default.",
            "- Targeted mutation requires explicit operator approval.",
            f"- Parent issue #{parent_issue} must remain open until parent-closeout readiness succeeds.",
        ),
        warnings=(
            "- Replace placeholders with concrete evidence before posting.",
            "- Do not close multiple issues in one command.",
        ),
    )
    canonical = generate_child_evidence_marker_template(
        config,
        parent_issue=parent_issue,
        child_issue=child_issue,
    )
    canonical_marker_text = str(canonical.get("canonical_marker_text") or "")
    canonical_marker = canonical.get("canonical_marker") if isinstance(canonical.get("canonical_marker"), dict) else {}
    missing_fields = canonical_marker.get("missing_required_fields")
    invalid_reasons = canonical_marker.get("invalid_reasons")
    missing_fields_list = list(missing_fields) if isinstance(missing_fields, (list, tuple)) else []
    invalid_reasons_list = list(invalid_reasons) if isinstance(invalid_reasons, (list, tuple)) else []
    marker_state = canonical_marker.get("marker_state") if isinstance(canonical_marker.get("marker_state"), str) else "unknown"
    marker_complete = marker_state == "ready" and not missing_fields_list and not invalid_reasons_list

    evidence_comment_body = render_evidence_bundle_text(bundle)
    evidence_comment_body += "\n### Canonical Marker\n\n"
    evidence_comment_body += canonical_marker_text if canonical_marker_text else "<missing>\n"

    return {
        "command": COMMAND_NAME,
        "ok": True,
        "read_only": True,
        "parent_issue": parent_issue,
        "child_issue": child_issue,
        "child_state": issue.get("state"),
        "child_title": issue.get("title"),
        "child_url": issue.get("url"),
        "canonical_marker": canonical_marker,
        "canonical_marker_text": canonical_marker_text,
        "canonical_marker_completeness": {
            "state": marker_state,
            "missing_required_fields": missing_fields_list,
            "invalid_reasons": invalid_reasons_list,
            "marker_complete": marker_complete,
            "post_hoc_marker_repair_required": not marker_complete,
        },
        "evidence_comment_body": evidence_comment_body,
        "expected_validation_summary_section": list(bundle.validation_lines),
        "targeted_closeout_guidance": [
            f"1. Post evidence comment to issue #{child_issue} after placeholder replacement.",
            f"2. Close only issue #{child_issue} with targeted gh issue close command.",
            f"3. Confirm issue #{child_issue} is CLOSED and parent #{parent_issue} remains OPEN.",
        ],
        "safety_notes": list(bundle.safety_notes),
    }

