from __future__ import annotations

from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.ready_issue_intake import (
    PROTECTED_ISSUE_NUMBER,
    READY_TRIGGER_LABEL,
    list_ready_issues,
)
from aresforge.operator.ready_issue_batch import BATCH_AUTOMERGE_LABEL


def automation_readiness_report(config: AppConfig) -> dict[str, Any]:
    ready_listing = list_ready_issues(config)
    ready_issue_count = 0
    if bool(ready_listing.get("ok")):
        issues = ready_listing.get("issues")
        ready_issue_count = len(issues) if isinstance(issues, list) else 0

    return {
        "command": "automation-readiness-report",
        "repo": f"{config.github_owner}/{config.github_repo}",
        "available_automation_commands": [
            "python -m aresforge list-ready-issues",
            "python -m aresforge inspect-ready-issue --issue-number <number>",
            "python -m aresforge plan-ready-issue --issue-number <number>",
            "python -m aresforge run-ready-issue-pipeline --issue-number <number> --plan-only",
            "python -m aresforge run-ready-issue-batch --plan-only",
            "python -m aresforge qa-review-pr --pr-number <number>",
            "python -m aresforge qa-closeout-pr --pr-number <number>",
        ],
        "ready_issue_count": ready_issue_count,
        "protected_issue_handling": {
            "issue_number": PROTECTED_ISSUE_NUMBER,
            "policy": "protected and excluded from planning and closeout mutation",
        },
        "required_labels": {
            "ready_intake": READY_TRIGGER_LABEL,
            "closeout_gate": BATCH_AUTOMERGE_LABEL,
        },
        "closeout_gates": [
            "qa-review-pr decision must pass",
            "linked issue must include aresforge-ready and aresforge-automerge labels",
            "linked issue must not be a protected historical reference",
            "execute mode must be explicit through qa-closeout-pr --execute",
        ],
        "mutation_boundaries": [
            "Batch planning and readiness reporting are read-only with respect to GitHub state.",
            "GitHub mutation is not permitted from run-ready-issue-batch or automation-readiness-report.",
            "Any closeout mutation remains gated through qa-closeout-pr execute mode only.",
        ],
        "local_only_behavior": [
            "Commands are human-triggered from the local operator CLI.",
            "No scheduler, daemon, polling loop, or background job is used.",
            "No remote paid/API LLM calls are used by default behavior.",
        ],
        "known_blocked_conditions": [
            "protected_issue",
            "missing_ready_label:aresforge-ready",
            "missing_automerge_label",
            "issue_not_open",
            "missing_pr_number for review/closeout modes",
            "qa_review_failed_gate",
        ],
        "recommended_human_workflow": [
            "Run list-ready-issues and inspect-ready-issue for candidates.",
            "Run run-ready-issue-batch --plan-only for deterministic batch planning artifacts.",
            "Run run-ready-issue-pipeline --plan-only per issue before PR work.",
            "Run qa-review-pr for each candidate PR.",
            "Run qa-closeout-pr in dry-run mode before any execute mode request.",
            "Use qa-closeout-pr --execute only after all gates pass and human approval is explicit.",
        ],
        "boundary_confirmations": [
            "Protected historical references remain excluded.",
            "No GitHub mutation was performed by this report command.",
            "No background jobs or polling were performed.",
        ],
    }
