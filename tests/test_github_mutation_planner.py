from __future__ import annotations

from aresforge.operator.github_mutation_planner import plan_github_mutation


def test_plan_github_mutation_issue_comment_success() -> None:
    payload = plan_github_mutation(
        mutation_type="issue_comment",
        planned_action="Post evidence comment for child issue",
        target_issue=328,
        approval_marker="operator-approved",
    )

    assert payload["ok"] is True
    assert payload["blocked"] is False
    assert payload["mutation_type"] == "issue_comment"
    assert payload["target_issue"] == 328
    assert payload["target_pr"] is None
    assert payload["dry_run"]["would_execute"] is False
    assert payload["audit_metadata_preview"]["local_only"] is True


def test_plan_github_mutation_blocks_missing_issue_target() -> None:
    payload = plan_github_mutation(
        mutation_type="issue_close",
        planned_action="Close child issue after readiness checks",
    )

    assert payload["ok"] is False
    assert payload["blocked"] is True
    assert "target_issue_required" in payload["blocked_reasons"]


def test_plan_github_mutation_blocks_invalid_target_mix() -> None:
    payload = plan_github_mutation(
        mutation_type="pr_body_update",
        planned_action="Update PR template body",
        target_issue=328,
        target_pr=336,
    )

    assert payload["ok"] is False
    assert payload["blocked"] is True
    assert "target_issue_not_allowed_for_pr_mutation" in payload["blocked_reasons"]

