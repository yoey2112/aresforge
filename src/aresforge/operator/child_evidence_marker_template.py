from __future__ import annotations

from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.canonical_evidence_markers import create_canonical_evidence_marker
from aresforge.operator.ready_issue_intake import fetch_issue_details


COMMAND_NAME = "generate-child-evidence-marker-template"


def generate_child_evidence_marker_template(
    config: AppConfig,
    *,
    parent_issue: int,
    child_issue: int,
    branch: str | None = None,
    commit: str | None = None,
    pr: str | None = None,
    validation_summary: str | None = None,
    safety_notes: str | None = None,
    closeout_status: str | None = None,
    evidence_comment_status: str | None = None,
    merge_status: str | None = None,
) -> dict[str, Any]:
    issue_payload = fetch_issue_details(config, child_issue)
    issue_lookup_ok = bool(issue_payload.get("ok"))
    issue = issue_payload.get("issue") if isinstance(issue_payload.get("issue"), dict) else {}

    resolved_closeout_status = closeout_status
    if resolved_closeout_status is None:
        state_value = issue.get("state") if isinstance(issue.get("state"), str) else "unknown"
        resolved_closeout_status = state_value.lower()

    marker = create_canonical_evidence_marker(
        marker_type="child_evidence",
        required_fields={
            "parent_issue": f"#{parent_issue}",
            "child_issue": f"#{child_issue}",
            "branch": branch,
            "commit": commit,
            "pr": pr,
            "validation_summary": validation_summary,
            "safety_notes": safety_notes,
        },
        optional_fields={
            "closeout_status": resolved_closeout_status,
            "evidence_comment_status": evidence_comment_status or "pending",
            "merge_status": merge_status or "unknown",
        },
    )

    warnings: list[str] = []
    if not issue_lookup_ok:
        warnings.append("child_issue_lookup_failed")

    return {
        "command": COMMAND_NAME,
        "ok": True,
        "read_only": True,
        "parent_issue": parent_issue,
        "child_issue": child_issue,
        "issue_lookup_ok": issue_lookup_ok,
        "child_issue_title": issue.get("title"),
        "child_issue_state": issue.get("state"),
        "child_issue_url": issue.get("url"),
        "canonical_marker": marker.to_dict(),
        "canonical_marker_text": marker.render(),
        "targeted_guidance": [
            f"Fill missing required marker fields for child issue #{child_issue}.",
            f"Post one targeted evidence comment to issue #{child_issue}.",
            f"Close only issue #{child_issue} after validations and merge are confirmed.",
        ],
        "safety_notes": [
            "Read-only template generation only.",
            "No issue, PR, or closeout mutation was executed.",
            "Use generated marker text as copy/paste-safe guidance.",
        ],
        "warnings": warnings,
    }