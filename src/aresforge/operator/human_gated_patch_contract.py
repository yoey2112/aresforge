from __future__ import annotations

import json
from typing import Any

from aresforge.config import AppConfig

PATCH_APPLICATION_CONTRACT_VERSION = "m88.1"
APPROVAL_PHRASE = "APPROVE LOCAL PATCH APPLICATION"

_BOUNDARY_CONFIRMATIONS = (
    "M88 is contract-first and dry-run only.",
    "Patch application is not implemented by this contract inspector.",
    "Generated local coding draft output is non-authoritative until manually reviewed.",
    "A patch may be considered only after explicit operator approval.",
    "No generated patch is applied automatically.",
    "No repository files are mutated automatically.",
    "No queue item status is mutated from patch artifacts.",
    "No queue item is completed from patch artifacts.",
    "No automatic next-item execution.",
    "No GitHub API calls.",
    "No gh calls.",
    "No issues, PRs, workflows, daemons, watchers, schedulers, or external workflow behavior.",
)


def inspect_human_gated_patch_application_contract(
    config: AppConfig,
    *,
    output_format: str = "json",
) -> dict[str, Any]:
    payload = build_human_gated_patch_application_contract(config)
    return _stdout_result(
        "inspect-human-gated-patch-application-contract",
        payload,
        output_format,
        _render_markdown(payload),
    )


def build_human_gated_patch_application_contract(config: AppConfig) -> dict[str, Any]:
    repo_root = str(config.repo_root)
    return {
        "ok": True,
        "local_only": True,
        "read_only": True,
        "contract_name": "human_gated_patch_application_contract",
        "contract_version": PATCH_APPLICATION_CONTRACT_VERSION,
        "milestone": "M88",
        "repo_root": repo_root,
        "contract_first": True,
        "dry_run_only": True,
        "patch_application_implemented": False,
        "patch_artifact_structure": {
            "artifact_kind": "human_gated_local_patch_draft",
            "storage_scope": "local_artifact_only",
            "required_fields": [
                "artifact_kind",
                "contract_version",
                "source_draft_artifact_path",
                "target_item_id",
                "patch_format",
                "target_files",
                "patch_text",
                "rationale",
                "risks",
                "expected_validation",
                "generated_by_provider",
                "generated_model",
                "created_at",
                "draft_is_authoritative",
                "draft_has_been_applied",
                "manual_review_required",
            ],
            "allowed_patch_formats": ["unified_diff", "operator_instructions"],
            "required_boolean_values": {
                "draft_is_authoritative": False,
                "draft_has_been_applied": False,
                "manual_review_required": True,
            },
            "path_requirements": [
                "source_draft_artifact_path must refer to a local artifact produced by the local coding draft flow.",
                "target_files must resolve under the repository root.",
                "target_files must not include path traversal or absolute paths outside the repository root.",
            ],
        },
        "operator_approval_requirements": {
            "explicit_approval_required": True,
            "approval_phrase": APPROVAL_PHRASE,
            "required_approval_fields": [
                "approved_by",
                "approved_at",
                "target_item_id",
                "patch_artifact_path",
                "reviewed_patch_hash",
                "reviewed_target_files",
                "validation_plan",
                "worktree_state_acknowledgement",
            ],
            "operator_must_confirm": [
                "The patch artifact was reviewed manually.",
                "The patch target files are expected and scoped to the current item.",
                "The repository worktree state is understood before any manual application.",
                "The validation plan is acceptable before any manual application.",
                "Queue completion remains a separate explicit evidence action.",
            ],
        },
        "pre_apply_safety_gates": [
            "local_only_operation",
            "explicit_operator_approval_record_present",
            "approval_phrase_matches",
            "patch_artifact_schema_valid",
            "patch_artifact_under_local_artifacts_or_operator_supplied_path",
            "source_draft_artifact_exists",
            "target_files_within_repo_root",
            "no_path_traversal",
            "manual_diff_review_completed",
            "validation_plan_present",
            "no_github_api",
            "no_gh",
            "no_workflow_daemon_watcher_scheduler_or_external_behavior",
        ],
        "post_apply_validation_requirements": [
            "operator_reviews_final_diff",
            "git diff --check",
            "targeted_tests_named_in_validation_plan",
            "relevant_smoke_checks_named_in_validation_plan",
            "inspect-local-project-report when project readiness is affected",
            "queue completion only through separate explicit operator evidence command",
        ],
        "safety_boundary": {
            "local_only": True,
            "read_only_from_this_command": True,
            "dry_run_only": True,
            "patch_application_allowed_from_this_command": False,
            "automatic_patch_application_allowed": False,
            "repo_mutation_allowed": False,
            "automatic_file_mutation_allowed": False,
            "queue_mutation_allowed": False,
            "queue_completion_allowed": False,
            "automatic_next_item_execution_allowed": False,
            "provider_invocation_allowed_from_this_command": False,
            "github_api_allowed": False,
            "gh_allowed": False,
            "external_workflow_allowed": False,
        },
        "forbidden_behaviors": [
            "automatic_patch_application",
            "automatic_file_mutation",
            "automatic_queue_completion",
            "automatic_next_item_execution",
            "github_api_calls",
            "gh_calls",
            "issues_prs_workflows",
            "daemon_watcher_scheduler_external_workflow_behavior",
        ],
        "next_safe_action": "Review this contract; any real patch application must be a separate explicit operator-approved command with validation gates.",
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }


def _stdout_result(command: str, payload: dict[str, Any], output_format: str, markdown: str) -> dict[str, Any]:
    fmt = str(output_format or "json").lower().strip()
    if fmt not in {"json", "markdown"}:
        return {
            "ok": False,
            "local_only": True,
            "error": "invalid_format",
            "details": {"format": output_format, "supported_formats": ["json", "markdown"]},
        }
    return {
        "command": command,
        "ok": bool(payload.get("ok", False)),
        "local_only": True,
        "format": fmt,
        "wrote_output_file": False,
        "stdout": json.dumps(payload, indent=2) if fmt == "json" else markdown,
        "payload": payload,
    }


def _render_markdown(payload: dict[str, Any]) -> str:
    boundary = payload.get("safety_boundary", {}) if isinstance(payload.get("safety_boundary"), dict) else {}
    lines = [
        "# Human-Gated Patch Application Contract",
        "",
        f"- ok: {payload.get('ok')}",
        f"- contract_version: {payload.get('contract_version', '')}",
        f"- dry_run_only: {payload.get('dry_run_only')}",
        f"- patch_application_implemented: {payload.get('patch_application_implemented')}",
        f"- automatic_patch_application_allowed: {boundary.get('automatic_patch_application_allowed')}",
        f"- queue_completion_allowed: {boundary.get('queue_completion_allowed')}",
        f"- next_safe_action: {payload.get('next_safe_action', '')}",
        "",
        "## Boundaries",
    ]
    lines.extend(f"- {entry}" for entry in payload.get("boundary_confirmations", []))
    return "\n".join(lines)
