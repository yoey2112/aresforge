from __future__ import annotations

from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.canonical_evidence_markers import create_canonical_evidence_marker
from aresforge.operator.pr_evidence_bundle import _fetch_pr_details
from aresforge.operator.ready_issue_intake import fetch_issue_details


COMMAND_NAME = "generate-pr-evidence-marker-template"


def generate_pr_evidence_marker_template(
    config: AppConfig,
    *,
    issue_number: int,
    pr_number: int,
    branch: str | None = None,
    commit: str | None = None,
    changed_files: str | None = None,
    validation_summary: str | None = None,
    merge_status: str | None = None,
    safety_posture: str | None = None,
    evidence_status: str | None = None,
    notes_warnings: str | None = None,
) -> dict[str, Any]:
    issue_payload = fetch_issue_details(config, issue_number)
    issue_lookup_ok = bool(issue_payload.get("ok"))
    issue = issue_payload.get("issue") if isinstance(issue_payload.get("issue"), dict) else {}

    pr_payload = _fetch_pr_details(config, pr_number)
    pr_lookup_ok = bool(pr_payload.get("ok"))
    pr = pr_payload.get("pr") if isinstance(pr_payload.get("pr"), dict) else {}

    resolved_branch = branch if branch is not None else _as_text(pr.get("head_branch"))
    resolved_commit = commit if commit is not None else _as_text(pr.get("merge_commit"))
    resolved_files = changed_files if changed_files is not None else _render_changed_files(pr)
    resolved_merge_status = merge_status if merge_status is not None else _infer_merge_status(pr)

    marker = create_canonical_evidence_marker(
        marker_type="pr_evidence",
        required_fields={
            "issue": f"#{issue_number}",
            "pr": f"#{pr_number}",
            "branch": resolved_branch,
            "commit": resolved_commit,
            "changed_files": resolved_files,
            "validation_summary": validation_summary,
            "merge_status": resolved_merge_status,
            "safety_posture": safety_posture,
            "evidence_status": evidence_status,
        },
        optional_fields={
            "notes_warnings": notes_warnings or "",
        },
    )

    warnings: list[str] = []
    if not issue_lookup_ok:
        warnings.append("issue_lookup_failed")
    if not pr_lookup_ok:
        warnings.append("pr_lookup_failed")

    return {
        "command": COMMAND_NAME,
        "ok": True,
        "read_only": True,
        "issue": {
            "number": issue_number,
            "title": issue.get("title"),
            "state": issue.get("state"),
            "url": issue.get("url"),
        },
        "pr": {
            "number": pr_number,
            "title": pr.get("title"),
            "url": pr.get("url"),
        },
        "issue_lookup_ok": issue_lookup_ok,
        "pr_lookup_ok": pr_lookup_ok,
        "canonical_marker": marker.to_dict(),
        "canonical_marker_text": marker.render(),
        "targeted_pr_body_update_guidance": [
            f"1. Review and complete the canonical marker fields for PR #{pr_number}.",
            f"2. Save reviewed PR marker text to artifacts/pr-{pr_number}-marker.md.",
            f"3. Targeted command (operator-approved text only): gh pr edit {pr_number} --body-file artifacts/pr-{pr_number}-marker.md",
        ],
        "safety_notes": [
            "Read-only marker generation only.",
            "No PR body mutation was executed by this command.",
            "Use targeted operator-approved mutation commands separately when required.",
        ],
        "warnings": warnings,
    }


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _render_changed_files(pr: dict[str, Any]) -> str:
    files = pr.get("files_changed") if isinstance(pr.get("files_changed"), list) else []
    items = [str(path).strip() for path in files if isinstance(path, str) and path.strip()]
    return ", ".join(sorted(set(items)))


def _infer_merge_status(pr: dict[str, Any]) -> str:
    if _as_text(pr.get("merge_commit")):
        return "merged"
    return ""