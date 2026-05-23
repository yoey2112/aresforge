from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

ALLOWED_MUTATION_TYPES = {
    "issue_comment",
    "issue_close",
    "pr_body_update",
    "audit_log_write",
}


def plan_github_mutation(
    *,
    mutation_type: str,
    planned_action: str,
    target_issue: int | None = None,
    target_pr: int | None = None,
    approval_marker: str | None = None,
) -> dict[str, Any]:
    normalized_type = mutation_type.strip().lower()
    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    blocked_reasons: list[str] = []

    if normalized_type not in ALLOWED_MUTATION_TYPES:
        blocked_reasons.append("unsupported_mutation_type")

    if normalized_type in {"issue_comment", "issue_close"} and target_issue is None:
        blocked_reasons.append("target_issue_required")

    if normalized_type == "pr_body_update" and target_pr is None:
        blocked_reasons.append("target_pr_required")

    if normalized_type in {"issue_comment", "issue_close"} and target_pr is not None:
        blocked_reasons.append("target_pr_not_allowed_for_issue_mutation")

    if normalized_type == "pr_body_update" and target_issue is not None:
        blocked_reasons.append("target_issue_not_allowed_for_pr_mutation")

    if normalized_type == "audit_log_write" and (target_issue is not None or target_pr is not None):
        blocked_reasons.append("audit_log_write_does_not_accept_github_targets")

    if not planned_action.strip():
        blocked_reasons.append("planned_action_required")

    required_approvals = [
        "explicit_operator_approval_required_for_execution",
        "single_target_confirmation_required",
    ]
    if normalized_type == "issue_close":
        required_approvals.append("issue_close_readiness_checks_required")

    safety_checks = [
        {"name": "dry_run_default", "passed": True},
        {"name": "bulk_mutation_disallowed", "passed": True},
        {"name": "single_target_scope_enforced", "passed": not any(
            reason in blocked_reasons
            for reason in {
                "target_issue_required",
                "target_pr_required",
                "target_pr_not_allowed_for_issue_mutation",
                "target_issue_not_allowed_for_pr_mutation",
                "audit_log_write_does_not_accept_github_targets",
            }
        )},
    ]

    ok = len(blocked_reasons) == 0
    return {
        "command": "plan-github-mutation",
        "ok": ok,
        "mutation_type": normalized_type,
        "target_issue": target_issue,
        "target_pr": target_pr,
        "planned_action": planned_action,
        "required_approvals": required_approvals,
        "safety_checks": safety_checks,
        "blocked": not ok,
        "blocked_reasons": blocked_reasons,
        "dry_run": {
            "would_execute": False,
            "execution_mode": "planning_only",
            "summary": (
                "Dry-run planning only. No GitHub mutation was performed."
                if ok
                else "Planning blocked by safety validation. No GitHub mutation was performed."
            ),
        },
        "audit_metadata_preview": {
            "timestamp": now,
            "command_concept": "plan-github-mutation",
            "approval_marker": approval_marker,
            "target": _target_descriptor(target_issue=target_issue, target_pr=target_pr),
            "local_only": True,
        },
        "boundary_confirmations": [
            "Planning-only command; no GitHub mutation performed.",
            "Dry-run default posture is enforced.",
            "Bulk mutation is not permitted.",
            "Operator approval remains required for any execution command.",
        ],
    }


def _target_descriptor(*, target_issue: int | None, target_pr: int | None) -> dict[str, Any]:
    if target_issue is not None:
        return {"type": "issue", "number": target_issue}
    if target_pr is not None:
        return {"type": "pr", "number": target_pr}
    return {"type": "none", "number": None}
