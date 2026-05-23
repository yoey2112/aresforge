from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.github_mutation_audit_log import append_github_mutation_audit_log
from aresforge.operator.ready_issue_intake import _repo_slug, _run_gh_command


def execute_github_issue_comment(
    config: AppConfig,
    *,
    issue_number: int,
    comment_body: str,
    execute: bool = False,
    parent_issue: int | None = None,
    allow_parent_target: bool = False,
    approval_marker: str | None = None,
) -> dict[str, Any]:
    blocked_reasons: list[str] = []
    if issue_number <= 0:
        blocked_reasons.append("invalid_issue_target")
    if not comment_body.strip():
        blocked_reasons.append("empty_comment_body")
    if parent_issue is not None and issue_number == parent_issue and not allow_parent_target:
        blocked_reasons.append("parent_target_blocked_without_explicit_override")

    dry_run = not execute
    approved_for_execution = execute and bool(approval_marker)
    if execute and not approval_marker:
        blocked_reasons.append("approval_marker_required_for_execution")

    ok = len(blocked_reasons) == 0
    mutation_attempted = False
    mutation_succeeded = False
    comment_url: str | None = None
    mutation_error: dict[str, Any] | None = None

    if execute and ok:
        mutation_attempted = True
        code, stdout, stderr = _run_gh_command(
            [
                "issue",
                "comment",
                str(issue_number),
                "--repo",
                _repo_slug(config),
                "--body",
                comment_body,
            ]
        )
        if code == 0:
            mutation_succeeded = True
            parsed = stdout.strip()
            if parsed.startswith("http"):
                comment_url = parsed
        else:
            mutation_error = {
                "step": "comment_issue",
                "exit_code": code,
                "stderr": stderr.strip(),
            }

    payload = {
        "command": "execute-github-issue-comment",
        "ok": ok and (not execute or mutation_succeeded),
        "mode": "execute" if execute else "dry_run",
        "repo": _repo_slug(config),
        "issue_number": issue_number,
        "parent_issue": parent_issue,
        "allow_parent_target": allow_parent_target,
        "approved_for_execution": approved_for_execution,
        "blocked": len(blocked_reasons) > 0,
        "blocked_reasons": blocked_reasons,
        "dry_run": {
            "active": dry_run,
            "would_execute": False if dry_run else mutation_attempted,
            "summary": "Dry-run mode only. No GitHub mutation was performed." if dry_run else "Execute mode requested.",
        },
        "mutation_attempted": mutation_attempted,
        "mutation_succeeded": mutation_succeeded,
        "comment_url": comment_url,
        "audit_ready_result": {
            "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "mutation_type": "issue_comment",
            "target": {"type": "issue", "number": issue_number},
            "approval_marker": approval_marker,
            "execute_mode": execute,
            "mutation_attempted": mutation_attempted,
            "mutation_succeeded": mutation_succeeded,
            "recovery_notes": (
                "Retry targeted comment execution after fixing blocked reasons."
                if blocked_reasons
                else "No recovery action required."
            ),
            "local_only_audit_artifact_recommended": True,
        },
        "boundary_confirmations": [
            "Single-issue target is required.",
            "Dry-run is default.",
            "Execution requires explicit approval marker.",
            "This command does not close issues.",
            "No bulk comment mutation path is available.",
        ],
        **({"mutation_error": mutation_error} if mutation_error is not None else {}),
    }
    append_github_mutation_audit_log(
        config,
        record={
            "command": "execute-github-issue-comment",
            "mutation_intent": "issue_comment",
            "dry_run_output": payload.get("dry_run"),
            "approval_marker": approval_marker,
            "execution_result": "succeeded" if mutation_succeeded else "not_executed_or_failed",
            "target": {"type": "issue", "number": issue_number},
            "command_concept": "execute-github-issue-comment",
            "recovery_notes": payload["audit_ready_result"]["recovery_notes"],
        },
    )
    return payload


def load_comment_body(*, inline_body: str | None, body_file: str | None) -> str:
    if inline_body is not None:
        return inline_body
    if body_file is not None:
        return Path(body_file).read_text(encoding="utf-8")
    return ""
