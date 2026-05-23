from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.evidence_completeness_checker import check_issue_evidence_readiness
from aresforge.operator.github_mutation_audit_log import append_github_mutation_audit_log
from aresforge.operator.parent_closeout_readiness import inspect_parent_closeout_readiness
from aresforge.operator.ready_issue_intake import _repo_slug, _run_gh_command

_ISSUE_TARGET_PATTERN = re.compile(r"^\d+$")
_ACCOUNTED_CLASSIFICATIONS = {"ready", "already_closed"}


def execute_github_issue_close(
    config: AppConfig,
    *,
    issue_target: str,
    parent_issue: int | None = None,
    execute: bool = False,
    approval_marker: str | None = None,
) -> dict[str, Any]:
    blocked_reasons: list[str] = []
    issue_number = _parse_issue_target(issue_target)
    if issue_number is None:
        blocked_reasons.append("invalid_issue_target_format")

    if execute and not approval_marker:
        blocked_reasons.append("approval_marker_required_for_execution")

    readiness: dict[str, Any] = {}
    is_parent_target = (
        isinstance(issue_number, int) and isinstance(parent_issue, int) and issue_number == parent_issue
    )
    if isinstance(issue_number, int):
        readiness = _readiness_for_target(config, issue_number=issue_number, is_parent_target=is_parent_target)
        if readiness.get("ready") is not True:
            blocked_reasons.append(str(readiness.get("blocked_reason", "readiness_check_failed")))

    dry_run = not execute
    mutation_attempted = False
    mutation_succeeded = False
    mutation_error: dict[str, Any] | None = None

    if execute and len(blocked_reasons) == 0 and isinstance(issue_number, int):
        mutation_attempted = True
        code, _stdout, stderr = _run_gh_command(
            [
                "issue",
                "close",
                str(issue_number),
                "--repo",
                _repo_slug(config),
                "--reason",
                "completed",
            ]
        )
        if code == 0:
            mutation_succeeded = True
        else:
            mutation_error = {"step": "close_issue", "exit_code": code, "stderr": stderr.strip()}

    payload = {
        "command": "execute-github-issue-close",
        "ok": len(blocked_reasons) == 0 and (not execute or mutation_succeeded),
        "mode": "execute" if execute else "dry_run",
        "repo": _repo_slug(config),
        "issue_target": issue_target,
        "issue_number": issue_number,
        "parent_issue": parent_issue,
        "is_parent_target": is_parent_target,
        "approved_for_execution": bool(execute and approval_marker),
        "blocked": len(blocked_reasons) > 0,
        "blocked_reasons": sorted(set(blocked_reasons)),
        "readiness": readiness,
        "dry_run": {
            "active": dry_run,
            "would_execute": False if dry_run else mutation_attempted,
            "summary": "Dry-run mode only. No GitHub mutation was performed." if dry_run else "Execute mode requested.",
        },
        "mutation_attempted": mutation_attempted,
        "mutation_succeeded": mutation_succeeded,
        "audit_ready_result": {
            "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "mutation_intent": "issue_close",
            "target": {"type": "issue", "number": issue_number},
            "approval_marker": approval_marker,
            "execution_result": "succeeded" if mutation_succeeded else "not_executed_or_failed",
            "command_concept": "execute-github-issue-close",
            "recovery_notes": (
                "Resolve readiness and approval blockers, then retry one targeted issue close."
                if blocked_reasons
                else "No recovery action required."
            ),
            "local_only_audit_artifact_recommended": True,
        },
        "boundary_confirmations": [
            "Single-issue target is required.",
            "Dry-run is default.",
            "Execution requires explicit approval marker.",
            "Bulk issue close is not supported.",
            "Parent close requires explicit parent readiness.",
        ],
        **({"mutation_error": mutation_error} if mutation_error is not None else {}),
    }
    append_github_mutation_audit_log(
        config,
        record={
            "command": "execute-github-issue-close",
            "mutation_intent": "issue_close",
            "dry_run_output": payload.get("dry_run"),
            "approval_marker": approval_marker,
            "execution_result": "succeeded" if mutation_succeeded else "not_executed_or_failed",
            "target": {"type": "issue", "number": issue_number},
            "command_concept": "execute-github-issue-close",
            "recovery_notes": payload["audit_ready_result"]["recovery_notes"],
        },
    )
    return payload


def _parse_issue_target(issue_target: str) -> int | None:
    text = issue_target.strip()
    if not _ISSUE_TARGET_PATTERN.fullmatch(text):
        return None
    value = int(text)
    if value <= 0:
        return None
    return value


def _readiness_for_target(config: AppConfig, *, issue_number: int, is_parent_target: bool) -> dict[str, Any]:
    if is_parent_target:
        parent_payload = inspect_parent_closeout_readiness(config, parent_issue=issue_number)
        closeout = (
            parent_payload.get("closeout_readiness")
            if isinstance(parent_payload.get("closeout_readiness"), dict)
            else {}
        )
        ready = bool(parent_payload.get("ok") and closeout.get("parent_closeout_ready") is True)
        return {
            "type": "parent",
            "ready": ready,
            "blocked_reason": None if ready else "parent_closeout_readiness_not_satisfied",
            "details": parent_payload,
        }

    child_payload = check_issue_evidence_readiness(config, issue_number=issue_number)
    classification = child_payload.get("classification")
    ready = bool(
        child_payload.get("ok") is True
        and isinstance(classification, str)
        and classification in _ACCOUNTED_CLASSIFICATIONS
    )
    return {
        "type": "child",
        "ready": ready,
        "blocked_reason": None if ready else "child_issue_evidence_readiness_not_satisfied",
        "details": child_payload,
    }
