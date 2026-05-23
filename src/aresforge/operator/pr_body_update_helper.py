from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.github_mutation_audit_log import append_github_mutation_audit_log
from aresforge.operator.ready_issue_intake import _repo_slug, _run_gh_command


def prepare_pr_body_update(
    config: AppConfig,
    *,
    pr_number: int,
    target_issue: int | None,
    scope_summary: str,
    files_changed: list[str],
    validation_results: list[str],
    safety_notes: list[str],
    execute: bool = False,
    approval_marker: str | None = None,
) -> dict[str, Any]:
    blocked_reasons: list[str] = []
    if pr_number <= 0:
        blocked_reasons.append("invalid_pr_target")
    if target_issue is not None and target_issue <= 0:
        blocked_reasons.append("invalid_target_issue")
    if not scope_summary.strip():
        blocked_reasons.append("scope_summary_required")
    if execute and not approval_marker:
        blocked_reasons.append("approval_marker_required_for_execution")

    rendered_body = _render_body(
        pr_number=pr_number,
        target_issue=target_issue,
        scope_summary=scope_summary,
        files_changed=files_changed,
        validation_results=validation_results,
        safety_notes=safety_notes,
    )

    mutation_attempted = False
    mutation_succeeded = False
    mutation_error: dict[str, Any] | None = None

    if execute and len(blocked_reasons) == 0:
        mutation_attempted = True
        body_file = _write_temp_body_file(rendered_body)
        try:
            code, _stdout, stderr = _run_gh_command(
                [
                    "pr",
                    "edit",
                    str(pr_number),
                    "--repo",
                    _repo_slug(config),
                    "--body-file",
                    str(body_file),
                ]
            )
            if code == 0:
                mutation_succeeded = True
            else:
                mutation_error = {"step": "pr_body_update", "exit_code": code, "stderr": stderr.strip()}
        finally:
            body_file.unlink(missing_ok=True)

    payload = {
        "command": "prepare-pr-body-update",
        "ok": len(blocked_reasons) == 0 and (not execute or mutation_succeeded),
        "mode": "execute" if execute else "dry_run",
        "repo": _repo_slug(config),
        "pr_number": pr_number,
        "target_issue": target_issue,
        "blocked": len(blocked_reasons) > 0,
        "blocked_reasons": sorted(set(blocked_reasons)),
        "dry_run_rendered_body": rendered_body,
        "mutation_attempted": mutation_attempted,
        "mutation_succeeded": mutation_succeeded,
        "audit_ready_result": {
            "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "mutation_intent": "pr_body_update",
            "target": {"type": "pr", "number": pr_number},
            "approval_marker": approval_marker,
            "execution_result": "succeeded" if mutation_succeeded else "not_executed_or_failed",
            "command_concept": "prepare-pr-body-update",
            "recovery_notes": (
                "Fix blocked reasons and rerun targeted PR body update."
                if blocked_reasons
                else "No recovery action required."
            ),
            "local_only_audit_artifact_recommended": True,
        },
        "boundary_confirmations": [
            "Dry-run is default.",
            "Execution requires explicit approval marker.",
            "Single PR target only.",
            "No bulk PR mutation path.",
            "Generated body avoids nested markdown fences in PowerShell here-string examples.",
        ],
        **({"mutation_error": mutation_error} if mutation_error is not None else {}),
    }
    append_github_mutation_audit_log(
        config,
        record={
            "command": "prepare-pr-body-update",
            "mutation_intent": "pr_body_update",
            "dry_run_output": {"active": not execute, "summary": "Dry-run rendered body prepared."},
            "approval_marker": approval_marker,
            "execution_result": "succeeded" if mutation_succeeded else "not_executed_or_failed",
            "target": {"type": "pr", "number": pr_number},
            "command_concept": "prepare-pr-body-update",
            "recovery_notes": payload["audit_ready_result"]["recovery_notes"],
        },
    )
    return payload


def _render_body(
    *,
    pr_number: int,
    target_issue: int | None,
    scope_summary: str,
    files_changed: list[str],
    validation_results: list[str],
    safety_notes: list[str],
) -> str:
    lines = [
        f"Target PR: #{pr_number}",
        f"Target issue: #{target_issue}" if target_issue is not None else "Target issue: N/A",
        "",
        "Scope summary",
        scope_summary.strip(),
        "",
        "Files changed",
    ]
    if files_changed:
        lines.extend(f"- {item}" for item in files_changed)
    else:
        lines.append("- N/A")
    lines.extend(["", "Validation results"])
    if validation_results:
        lines.extend(f"- {item}" for item in validation_results)
    else:
        lines.append("- N/A")
    lines.extend(["", "Safety notes"])
    if safety_notes:
        lines.extend(f"- {item}" for item in safety_notes)
    else:
        lines.append("- N/A")
    lines.extend(
        [
            "",
            "PowerShell example (plain text, no nested markdown fences)",
            "Set-Location C:\\Projects\\aresforge",
            "python -m pytest",
            "python -m aresforge inspect-repo-governance",
        ]
    )
    return "\n".join(lines).strip() + "\n"


def _write_temp_body_file(content: str) -> Path:
    p = Path(".tmp_pr_body_update.txt")
    p.write_text(content, encoding="utf-8")
    return p
