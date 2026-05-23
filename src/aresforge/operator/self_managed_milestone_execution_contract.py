from __future__ import annotations

from typing import Any

from aresforge.config import AppConfig

COMMAND_NAME = "inspect-self-managed-milestone-execution-contract"


def inspect_self_managed_milestone_execution_contract(config: AppConfig) -> dict[str, Any]:
    return {
        "command": COMMAND_NAME,
        "ok": True,
        "read_only": True,
        "repo": f"{config.github_owner}/{config.github_repo}",
        "contract_version": "m21.v1",
        "contract_name": "self_managed_milestone_execution_loop",
        "inputs": {
            "required": [
                "parent_issue_number",
                "ordered_child_issue_sequence",
                "repo_root_path",
                "synced_main_head_sha",
            ],
            "optional": [
                "sequential_run_state_path",
                "operator_approval_token_or_explicit_execute_flag",
                "validation_command_overrides",
            ],
        },
        "outputs": {
            "required": [
                "sequential_execution_plan",
                "per_child_execution_envelope",
                "validation_plan",
                "mutation_plan_dry_run_default",
                "audit_package",
                "handoff_recovery_package",
            ],
            "closeout_gated_outputs": [
                "targeted_child_evidence_comment_payload",
                "targeted_child_closeout_payload",
                "targeted_parent_closeout_payload_after_readiness",
            ],
        },
        "state_transitions": [
            "planned",
            "child_selected",
            "validation_passed",
            "mutation_planned_dry_run",
            "mutation_approved",
            "mutation_executed_targeted",
            "child_closed",
            "handoff_written",
            "parent_readiness_verified",
            "parent_closed_targeted",
        ],
        "safety_boundaries": {
            "dry_run_default": True,
            "explicit_operator_approval_required_for_mutation": True,
            "bulk_closeout_forbidden": True,
            "parent_closeout_before_child_accounting_forbidden": True,
            "final_reconciliation_must_be_last": True,
            "prior_milestone_mutation_forbidden_by_default": True,
            "targeted_mutation_only": [
                "single_issue_comment",
                "single_issue_close",
                "single_pr_body_update",
            ],
        },
        "approval_boundary": {
            "required_for_mutation_execution": True,
            "minimum_controls": [
                "explicit_execute_flag",
                "target_issue_or_pr_id",
                "dry_run_plan_preview",
                "audit_log_intent_and_result",
            ],
        },
        "parent_closeout_readiness_boundary": {
            "required_checks": [
                "all_children_closed_or_accounted_for",
                "milestone_evidence_readiness_ok",
                "parent_closeout_ready_true",
                "blocked_reasons_empty",
            ],
            "prohibited_while_unready": [
                "parent_closeout_mutation",
            ],
        },
        "boundary_confirmations": [
            "Contract inspection is read-only.",
            "No GitHub mutation was performed.",
            "No issues, pull requests, labels, milestones, or branches were modified.",
        ],
    }
