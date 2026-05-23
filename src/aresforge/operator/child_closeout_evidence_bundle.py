from __future__ import annotations

from typing import Any

from aresforge.config import AppConfig
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
    evidence_comment_body = render_evidence_bundle_text(bundle)

    return {
        "command": COMMAND_NAME,
        "ok": True,
        "read_only": True,
        "parent_issue": parent_issue,
        "child_issue": child_issue,
        "child_state": issue.get("state"),
        "child_title": issue.get("title"),
        "child_url": issue.get("url"),
        "evidence_comment_body": evidence_comment_body,
        "expected_validation_summary_section": list(bundle.validation_lines),
        "targeted_closeout_guidance": [
            f"1. Post evidence comment to issue #{child_issue} after placeholder replacement.",
            f"2. Close only issue #{child_issue} with targeted gh issue close command.",
            f"3. Confirm issue #{child_issue} is CLOSED and parent #{parent_issue} remains OPEN.",
        ],
        "safety_notes": list(bundle.safety_notes),
    }

