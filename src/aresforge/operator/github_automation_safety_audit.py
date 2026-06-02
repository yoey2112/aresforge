from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import re
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.github_link_registry import inspect_github_link_registry
from aresforge.operator.github_sync_recovery_idempotency import inspect_github_sync_recovery
from aresforge.operator.hub_github_sync_control_panel import inspect_hub_github_sync_control_panel_data
from aresforge.operator.local_project_queue import resolve_project_queue_path
from aresforge.operator.machine_safety_gate_engine import evaluate_machine_safety_gates

COMMAND_NAME = "audit-github-automation-safety"
RECORD_TYPE = "github_automation_safety_audit_v1"
CAPABILITY_RECORD_TYPE = "github_automation_capability_audit_v1"
DEFAULT_PROJECT_ID = "aresforge"
DEFAULT_ITEM_ID = "m183-github-automation-safety-audit"
DEFAULT_AUTONOMY_PROFILE = "github_sync_dry_run"

_DESTRUCTIVE_BLOCKED_OPERATIONS: tuple[str, ...] = (
    "merge_pull_request",
    "enable_auto_merge",
    "force_push",
    "update_protected_branch",
    "create_release",
    "modify_github_workflow",
    "automatic_issue_closure",
    "source_code_patch_application",
)

_GLOBAL_BLOCKED_OPERATIONS: tuple[str, ...] = (
    *_DESTRUCTIVE_BLOCKED_OPERATIONS,
    "queue_status_mutation_from_github_sync",
    "codex_execution_from_github_sync",
    "model_execution_from_github_sync",
    "validation_command_execution_from_github_sync",
    "retry_execution_from_audit",
    "resume_execution_from_audit",
    "automatic_next_item_execution",
)

_CAPABILITIES: tuple[dict[str, Any], ...] = (
    {
        "milestone": "M170",
        "capability_id": "github_link_registry",
        "command": "inspect-github-link-registry / record-github-link",
        "implemented": True,
        "default_behavior": "local_read_or_local_registry_write_only",
        "allowed_operations": ["local_registry_inspection", "idempotent_local_link_recording"],
        "live_mutation_capable": False,
        "mutation_scope": "local_registry_only",
        "required_machine_gates": ["read_only_agent"],
        "idempotency_anchor": "queue_item_repository_issue_pr_link",
        "recovery_path": "inspect-github-sync-recovery",
        "test_files": ["tests/test_github_link_registry.py"],
    },
    {
        "milestone": "M171",
        "capability_id": "github_issue_creation_gate",
        "command": "create-github-issue-real-run-gate",
        "implemented": True,
        "default_behavior": "dry_run_or_blocked",
        "allowed_operations": ["single_issue_create_when_explicitly_enabled"],
        "live_mutation_capable": True,
        "mutation_scope": "one_issue_create",
        "required_machine_gates": ["github_sync"],
        "idempotency_anchor": "local_github_link_registry_issue_number",
        "recovery_path": "inspect-github-sync-recovery repair_plan",
        "test_files": ["tests/test_github_issue_creation_real_run_gate.py"],
    },
    {
        "milestone": "M172",
        "capability_id": "queue_to_github_issue_backfill",
        "command": "backfill-queue-items-to-github-issues",
        "implemented": True,
        "default_behavior": "dry_run_or_blocked",
        "allowed_operations": ["bounded_issue_create_via_m171_gate"],
        "live_mutation_capable": True,
        "mutation_scope": "one_or_operator_limited_issue_create_batch",
        "required_machine_gates": ["github_sync"],
        "idempotency_anchor": "queue_metadata_or_registry_issue_link",
        "recovery_path": "inspect-github-sync-recovery",
        "test_files": ["tests/test_queue_to_github_issue_backfill.py"],
    },
    {
        "milestone": "M173",
        "capability_id": "durable_status_comment_sync",
        "command": "sync-github-status-comment-durable",
        "implemented": True,
        "default_behavior": "dry_run_or_blocked",
        "allowed_operations": ["one_managed_issue_comment_create_or_update"],
        "live_mutation_capable": True,
        "mutation_scope": "one_managed_issue_status_comment",
        "required_machine_gates": ["github_sync"],
        "idempotency_anchor": "managed_marker_and_registry_comment_id",
        "recovery_path": "inspect-github-sync-recovery resume_plan",
        "test_files": ["tests/test_github_status_comment_durable_sync.py"],
    },
    {
        "milestone": "M174",
        "capability_id": "issue_state_reconciliation",
        "command": "reconcile-github-issue-state",
        "implemented": True,
        "default_behavior": "dry_run_recommendation_only",
        "allowed_operations": ["mocked_or_gated_issue_state_read", "recommendation_only_actions"],
        "live_mutation_capable": False,
        "mutation_scope": "none",
        "required_machine_gates": ["read_only_agent", "github_sync_for_live_read_only_lookup"],
        "idempotency_anchor": "local_queue_and_registry_state",
        "recovery_path": "recommend_matching_separate_gated_command",
        "test_files": ["tests/test_github_issue_state_reconciliation.py"],
    },
    {
        "milestone": "M175",
        "capability_id": "issue_closure_gate",
        "command": "gate-github-issue-closure",
        "implemented": True,
        "default_behavior": "dry_run_or_blocked",
        "allowed_operations": ["one_linked_issue_close_when_explicitly_enabled"],
        "live_mutation_capable": True,
        "mutation_scope": "one_issue_close",
        "required_machine_gates": ["github_sync"],
        "idempotency_anchor": "linked_issue_state_and_registry_sync_metadata",
        "recovery_path": "inspect-github-sync-recovery repair_plan",
        "test_files": ["tests/test_github_issue_closure_safe_execution_gate.py"],
    },
    {
        "milestone": "M176",
        "capability_id": "pr_draft_branch_planning",
        "command": "plan-pr-draft-branch",
        "implemented": True,
        "default_behavior": "local_planning_only",
        "allowed_operations": ["branch_and_pr_metadata_planning"],
        "live_mutation_capable": False,
        "mutation_scope": "none",
        "required_machine_gates": ["read_only_agent"],
        "idempotency_anchor": "planned_branch_item_repository",
        "recovery_path": "re-run_planning_after_local_evidence_review",
        "test_files": ["tests/test_pr_draft_branch_planning_contract.py"],
    },
    {
        "milestone": "M177",
        "capability_id": "draft_pr_creation_gate",
        "command": "create-pr-draft-gate",
        "implemented": True,
        "default_behavior": "dry_run_or_blocked",
        "allowed_operations": ["one_draft_pull_request_create_when_explicitly_enabled"],
        "live_mutation_capable": True,
        "mutation_scope": "one_draft_pull_request_create",
        "required_machine_gates": ["github_sync"],
        "idempotency_anchor": "local_registry_pr_number",
        "recovery_path": "inspect-github-sync-recovery repair_plan",
        "test_files": ["tests/test_pr_draft_creation_gate.py"],
    },
    {
        "milestone": "M178",
        "capability_id": "pr_evidence_comment_sync",
        "command": "sync-pr-evidence-comment",
        "implemented": True,
        "default_behavior": "dry_run_or_blocked",
        "allowed_operations": ["one_managed_pr_comment_create_or_update"],
        "live_mutation_capable": True,
        "mutation_scope": "one_managed_pr_evidence_comment",
        "required_machine_gates": ["github_sync"],
        "idempotency_anchor": "managed_marker_and_registry_comment_id",
        "recovery_path": "inspect-github-sync-recovery resume_plan",
        "test_files": ["tests/test_pr_evidence_comment_sync.py"],
    },
    {
        "milestone": "M179",
        "capability_id": "github_sync_recovery_idempotency",
        "command": "inspect-github-sync-recovery",
        "implemented": True,
        "default_behavior": "read_only_local_inspection",
        "allowed_operations": ["local_registry_and_preflight_recovery_inspection"],
        "live_mutation_capable": False,
        "mutation_scope": "none",
        "required_machine_gates": ["read_only_agent"],
        "idempotency_anchor": "operation_idempotency_keys_and_registry_completion_anchors",
        "recovery_path": "advisory_only_repair_and_resume_plans",
        "test_files": ["tests/test_github_sync_recovery_idempotency.py"],
    },
    {
        "milestone": "M180",
        "capability_id": "hub_github_sync_control_panel",
        "command": "inspect-hub-github-sync-control-panel-data",
        "implemented": True,
        "default_behavior": "read_only_control_visibility",
        "allowed_operations": ["local_hub_panel_data_aggregation"],
        "live_mutation_capable": False,
        "mutation_scope": "none",
        "required_machine_gates": ["read_only_agent"],
        "idempotency_anchor": "panel_idempotency_key",
        "recovery_path": "link_to_separate_dry_run_or_recovery_commands",
        "test_files": ["tests/test_hub_github_sync_control_panel.py"],
    },
    {
        "milestone": "M181",
        "capability_id": "self_managed_issue_loop",
        "command": "run-self-managed-issue-loop",
        "implemented": True,
        "default_behavior": "dry_run_or_blocked",
        "allowed_operations": ["gated_issue_create", "gated_status_comment_sync"],
        "live_mutation_capable": True,
        "mutation_scope": "one_issue_loop_issue_and_comment_sync",
        "required_machine_gates": ["read_only_agent", "github_sync_for_live_steps"],
        "idempotency_anchor": "issue_link_and_status_comment_registry_metadata",
        "recovery_path": "inspect-github-sync-recovery",
        "test_files": ["tests/test_self_managed_issue_loop_real_run.py"],
    },
    {
        "milestone": "M182",
        "capability_id": "self_managed_pr_draft_loop",
        "command": "run-self-managed-pr-draft-loop",
        "implemented": True,
        "default_behavior": "dry_run_or_blocked",
        "allowed_operations": ["gated_draft_pr_create", "gated_pr_evidence_comment_sync"],
        "live_mutation_capable": True,
        "mutation_scope": "one_draft_pr_and_one_pr_evidence_comment",
        "required_machine_gates": ["read_only_agent", "github_sync_for_live_steps"],
        "idempotency_anchor": "pr_link_and_pr_comment_registry_metadata",
        "recovery_path": "inspect-github-sync-recovery",
        "test_files": ["tests/test_self_managed_pr_draft_loop_dry_run.py"],
    },
)

_BOUNDARY_CONFIRMATIONS: tuple[str, ...] = (
    "GitHub automation safety audit is read-only, local-only, and dry-run by default.",
    "The audit inspects implemented GitHub coordination capabilities and existing local safety evidence.",
    "The audit does not execute GitHub operations, gh, queue mutation, registry mutation, retries, resumes, Codex, models, validation commands, source patches, workflow changes, branch updates, merges, releases, or next-item execution.",
    "Live GitHub mutation remains limited to separate commands that require explicit enablement, github_issue_sync_enabled where applicable, idempotency checks, and passing machine gates.",
)


def audit_github_automation_safety(
    config: AppConfig,
    *,
    project_id: str = DEFAULT_PROJECT_ID,
    item_id: str = DEFAULT_ITEM_ID,
    queue_path: str | Path | None = None,
    registry_path: str | Path | None = None,
    repo: str | None = None,
    autonomy_profile: str = DEFAULT_AUTONOMY_PROFILE,
    output_format: str = "json",
) -> dict[str, Any]:
    fmt = _text(output_format).lower() or "json"
    if fmt != "json":
        return _error("invalid_format", {"format": output_format, "supported_formats": ["json"]})

    normalized_project_id = _text(project_id) or DEFAULT_PROJECT_ID
    normalized_item_id = _text(item_id) or DEFAULT_ITEM_ID
    selected_profile = _text(autonomy_profile) or DEFAULT_AUTONOMY_PROFILE
    repository = _normalize_repo(config, repo)
    resolved_queue_path = resolve_project_queue_path(config.repo_root, queue_path)
    queue_result = _load_queue(resolved_queue_path)
    queue = queue_result.get("queue") if queue_result.get("ok") else {}
    queue_items = [
        item
        for item in _dicts(queue.get("work_items"))
        if (_text(item.get("project_id")) or normalized_project_id) == normalized_project_id
    ]

    read_only_gate = _gate_payload(config, item_id=normalized_item_id, queue_path=queue_path, gate_profile="read_only_agent")
    github_sync_gate = _gate_payload(config, item_id=normalized_item_id, queue_path=queue_path, gate_profile="github_sync")
    machine_gates = [
        _gate_summary(read_only_gate, required_for_audit=True),
        _gate_summary(github_sync_gate, required_for_audit=False),
    ]

    registry_payload = _payload(
        inspect_github_link_registry(
            config,
            project_id=normalized_project_id,
            item_id=normalized_item_id,
            registry_path=registry_path,
            repository=repository,
            output_format="json",
        )
    )
    recovery_payload = _payload(
        inspect_github_sync_recovery(
            config,
            project_id=normalized_project_id,
            item_id=normalized_item_id,
            queue_path=queue_path,
            registry_path=registry_path,
            repo=repository,
            output_format="json",
        )
    )
    control_panel_payload = _payload(
        inspect_hub_github_sync_control_panel_data(
            config,
            project_id=normalized_project_id,
            item_id="m180-hub-github-sync-control-panel",
            queue_path=queue_path,
            registry_path=registry_path,
            repo=repository,
            autonomy_profile=selected_profile,
            output_format="json",
        )
    )

    capability_audits = [_capability_audit(config, capability, normalized_project_id, repository) for capability in _CAPABILITIES]
    capability_counts = _capability_counts(capability_audits)
    blocked_reasons = _dedupe(
        [
            *queue_result.get("blocked_reasons", []),
            *(_list(read_only_gate.get("blocked_reasons")) if not _gate_passed(read_only_gate) else []),
            *_list(registry_payload.get("blocked_reasons")),
            *_list(recovery_payload.get("blocked_reasons")),
            *_list(control_panel_payload.get("blocked_reasons")),
        ]
    )
    if not _gate_passed(read_only_gate):
        blocked_reasons.append("Read-only audit machine gate did not pass.")
    blocked = bool(blocked_reasons)
    warnings = _dedupe(
        [
            *queue_result.get("warnings", []),
            *_list(registry_payload.get("warnings")),
            *_list(recovery_payload.get("warnings")),
            *_list(control_panel_payload.get("warnings")),
            *_coverage_warnings(capability_audits),
            "Audit conclusions are based on local implementation and registry evidence; no live GitHub verification was performed.",
        ]
    )

    issue_number = _first_int(registry_payload, "issue_number")
    pr_number = _first_int(registry_payload, "pr_number")
    payload: dict[str, Any] = {
        "record_type": RECORD_TYPE,
        "artifact_type": RECORD_TYPE,
        "generated": True,
        "generated_at": _now_iso(),
        "project_id": normalized_project_id,
        "item_id": normalized_item_id,
        "repository": repository,
        "issue_number": issue_number,
        "issue_url": _first_text(registry_payload, "issue_url"),
        "pr_number": pr_number,
        "pr_url": _first_text(registry_payload, "pr_url"),
        "sync_status": "blocked" if blocked else "audit_complete",
        "status": "blocked" if blocked else "audit_complete",
        "blocked": blocked,
        "blocked_reasons": blocked_reasons,
        "warnings": warnings,
        "machine_gates_checked": machine_gates,
        "machine_gates_passed": _gate_passed(read_only_gate) and not blocked,
        "autonomy_profile": selected_profile,
        "dry_run": True,
        "github_enabled": False,
        "github_execution_performed": False,
        "mutation_performed": False,
        "github_issue_mutation_performed": False,
        "github_comment_mutation_performed": False,
        "github_pr_mutation_performed": False,
        "registry_mutation_performed": False,
        "queue_mutation_performed": False,
        "codex_execution_performed": False,
        "model_execution_performed": False,
        "patch_application_performed": False,
        "validation_command_execution_performed": False,
        "idempotency_key": _audit_idempotency_key(
            project_id=normalized_project_id,
            item_id=normalized_item_id,
            repository=repository,
        ),
        "recovery_available": bool(recovery_payload.get("recovery_available", True)),
        "local_only": True,
        "next_safe_action": _next_safe_action(blocked=blocked, capability_counts=capability_counts, recovery_payload=recovery_payload),
        "queue_path": str(resolved_queue_path),
        "queue_item_count": len(queue_items),
        "registry_health": _registry_health(registry_payload),
        "recovery_health": _recovery_health(recovery_payload),
        "control_panel_health": _control_panel_health(control_panel_payload),
        "capability_counts": capability_counts,
        "capabilities": capability_audits,
        "allowed_operations": _allowed_operations(capability_audits),
        "blocked_operations": list(_GLOBAL_BLOCKED_OPERATIONS),
        "default_behavior": {
            "record_type": "github_automation_default_behavior_audit_v1",
            "dry_run_default": True,
            "github_enabled_default": False,
            "live_mutation_requires_explicit_enablement": True,
            "live_mutation_requires_machine_gates": True,
            "live_mutation_requires_autonomy_profile": "github_issue_sync_enabled where mutation-capable GitHub sync commands require it",
            "github_execution_performed": False,
            "mutation_performed": False,
            "local_only": True,
        },
        "machine_gate_coverage": _machine_gate_coverage(capability_audits, machine_gates),
        "idempotency_coverage": _idempotency_coverage(capability_audits, registry_payload, recovery_payload),
        "test_coverage_indicators": _test_coverage_indicators(capability_audits),
        "registry_health_summary": _registry_health(registry_payload),
        "remaining_risks": _remaining_risks(capability_audits, recovery_payload),
        "safety_boundaries": {
            "record_type": "github_automation_safety_boundaries_audit_v1",
            "do_not_merge_pull_requests": True,
            "do_not_enable_auto_merge": True,
            "do_not_force_push": True,
            "do_not_update_protected_branches": True,
            "do_not_create_releases": True,
            "do_not_mutate_github_workflows": True,
            "do_not_close_issues_automatically": True,
            "do_not_apply_source_patches_as_part_of_github_sync": True,
            "do_not_bypass_autonomy_profiles_or_machine_gates": True,
            "local_only": True,
        },
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
        "completed_at": _now_iso(),
    }
    return _stdout_result(payload)


def _capability_audit(config: AppConfig, capability: dict[str, Any], project_id: str, repository: str) -> dict[str, Any]:
    test_files = _list(capability.get("test_files"))
    existing_tests = [path for path in test_files if (config.repo_root / path).exists()]
    live_capable = bool(capability.get("live_mutation_capable"))
    blocked_operations = list(_DESTRUCTIVE_BLOCKED_OPERATIONS)
    if capability.get("capability_id") != "issue_closure_gate":
        blocked_operations.append("issue_closure")
    if not live_capable:
        blocked_operations.extend(["github_mutation", "registry_mutation"])
    missing_tests = [path for path in test_files if path not in existing_tests]
    warnings = [f"Expected targeted test file not found: {path}." for path in missing_tests]
    return {
        "record_type": CAPABILITY_RECORD_TYPE,
        "artifact_type": CAPABILITY_RECORD_TYPE,
        "generated": True,
        "project_id": project_id,
        "item_id": DEFAULT_ITEM_ID,
        "repository": repository,
        "issue_number": None,
        "issue_url": "",
        "pr_number": None,
        "pr_url": "",
        "milestone": _text(capability.get("milestone")),
        "capability_id": _text(capability.get("capability_id")),
        "command": _text(capability.get("command")),
        "implemented": bool(capability.get("implemented")),
        "sync_status": "implemented_with_tests" if not missing_tests else "implemented_test_indicator_missing",
        "blocked": False,
        "blocked_reasons": [],
        "warnings": warnings,
        "machine_gates_checked": list(capability.get("required_machine_gates", [])),
        "machine_gates_passed": True,
        "autonomy_profile": DEFAULT_AUTONOMY_PROFILE,
        "dry_run": True,
        "github_enabled": False,
        "github_execution_performed": False,
        "mutation_performed": False,
        "local_only": True,
        "idempotency_key": _capability_idempotency_key(project_id=project_id, capability_id=_text(capability.get("capability_id")), repository=repository),
        "recovery_available": bool(capability.get("recovery_path")),
        "next_safe_action": "Use the named command in dry-run/read-only mode first; live mutation requires separate explicit gates when this capability is mutation-capable.",
        "default_behavior": _text(capability.get("default_behavior")),
        "allowed_operations": _list(capability.get("allowed_operations")),
        "blocked_operations": _dedupe(blocked_operations),
        "live_mutation_capable": live_capable,
        "mutation_scope": _text(capability.get("mutation_scope")),
        "required_machine_gates": list(capability.get("required_machine_gates", [])),
        "idempotency_anchor": _text(capability.get("idempotency_anchor")),
        "recovery_path": _text(capability.get("recovery_path")),
        "test_files": test_files,
        "targeted_tests_present": bool(test_files) and not missing_tests,
    }


def _capability_counts(capabilities: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "capabilities_audited": len(capabilities),
        "implemented": sum(1 for capability in capabilities if capability.get("implemented") is True),
        "live_mutation_capable": sum(1 for capability in capabilities if capability.get("live_mutation_capable") is True),
        "dry_run_or_read_only_default": sum(
            1
            for capability in capabilities
            if _text(capability.get("default_behavior")) in {"dry_run_or_blocked", "dry_run_recommendation_only", "read_only_local_inspection", "read_only_control_visibility", "local_planning_only", "local_read_or_local_registry_write_only"}
        ),
        "targeted_tests_present": sum(1 for capability in capabilities if capability.get("targeted_tests_present") is True),
        "idempotency_anchors": sum(1 for capability in capabilities if _text(capability.get("idempotency_anchor"))),
        "recovery_paths": sum(1 for capability in capabilities if capability.get("recovery_available") is True),
    }


def _registry_health(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "record_type": "github_automation_registry_health_audit_v1",
        "sync_status": _text(payload.get("sync_status") or payload.get("status")) or "unknown",
        "blocked": bool(payload.get("blocked")),
        "blocked_reasons": _list(payload.get("blocked_reasons")),
        "warnings": _list(payload.get("warnings")),
        "registry_path": _text(payload.get("registry_path")),
        "record_count": int(payload.get("record_count") or 0),
        "matched_record_count": int(payload.get("matched_record_count") or 0),
        "machine_gates_passed": bool(payload.get("machine_gates_passed", True)),
        "dry_run": True,
        "github_enabled": False,
        "github_execution_performed": False,
        "mutation_performed": False,
        "local_only": True,
        "next_safe_action": "Use registry records as local idempotency evidence before any separate gated GitHub command.",
    }


def _recovery_health(payload: dict[str, Any]) -> dict[str, Any]:
    counts = payload.get("operation_counts") if isinstance(payload.get("operation_counts"), dict) else {}
    return {
        "record_type": "github_automation_recovery_health_audit_v1",
        "sync_status": _text(payload.get("sync_status") or payload.get("status")) or "unknown",
        "blocked": bool(payload.get("blocked")),
        "blocked_reasons": _list(payload.get("blocked_reasons")),
        "warnings": _list(payload.get("warnings")),
        "operations_complete_noop": int(counts.get("operations_complete_noop") or 0),
        "operations_partial": int(counts.get("operations_partial") or 0),
        "resume_recommended": int(counts.get("resume_recommended") or 0),
        "repair_recommended": int(counts.get("repair_recommended") or 0),
        "recovery_available": bool(payload.get("recovery_available", True)),
        "dry_run": True,
        "github_enabled": False,
        "github_execution_performed": False,
        "mutation_performed": False,
        "local_only": True,
        "next_safe_action": _text(payload.get("next_safe_action")),
    }


def _control_panel_health(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "record_type": "github_automation_control_panel_health_audit_v1",
        "sync_status": _text(payload.get("sync_status") or payload.get("status")) or "unknown",
        "blocked": bool(payload.get("blocked")),
        "blocked_reasons": _list(payload.get("blocked_reasons")),
        "warnings": _list(payload.get("warnings")),
        "unsafe_actions_available": bool(payload.get("unsafe_actions_available")),
        "github_mutation_allowed": bool(payload.get("github_mutation_allowed")),
        "dry_run": True,
        "github_enabled": False,
        "github_execution_performed": False,
        "mutation_performed": False,
        "local_only": True,
        "next_safe_action": _text(payload.get("next_safe_action")),
    }


def _machine_gate_coverage(capabilities: list[dict[str, Any]], machine_gates: list[dict[str, Any]]) -> dict[str, Any]:
    profiles = sorted({_text(gate) for capability in capabilities for gate in _list(capability.get("required_machine_gates")) if _text(gate)})
    return {
        "record_type": "github_automation_machine_gate_coverage_audit_v1",
        "required_gate_profiles": profiles,
        "audit_gates_checked": machine_gates,
        "capabilities_with_gate_requirements": sum(1 for capability in capabilities if _list(capability.get("required_machine_gates"))),
        "capabilities_without_gate_requirements": sum(1 for capability in capabilities if not _list(capability.get("required_machine_gates"))),
        "machine_gates_passed": all(bool(gate.get("passed")) for gate in machine_gates if bool(gate.get("required_for_audit"))),
        "local_only": True,
    }


def _idempotency_coverage(capabilities: list[dict[str, Any]], registry_payload: dict[str, Any], recovery_payload: dict[str, Any]) -> dict[str, Any]:
    counts = recovery_payload.get("operation_counts") if isinstance(recovery_payload.get("operation_counts"), dict) else {}
    return {
        "record_type": "github_automation_idempotency_coverage_audit_v1",
        "capabilities_with_idempotency_anchor": sum(1 for capability in capabilities if _text(capability.get("idempotency_anchor"))),
        "registry_record_count": int(registry_payload.get("record_count") or 0),
        "registry_matched_record_count": int(registry_payload.get("matched_record_count") or 0),
        "operations_complete_noop": int(counts.get("operations_complete_noop") or 0),
        "operations_partial": int(counts.get("operations_partial") or 0),
        "idempotency_status": "covered" if all(_text(capability.get("idempotency_anchor")) for capability in capabilities) else "coverage_gap",
        "dry_run": True,
        "github_enabled": False,
        "github_execution_performed": False,
        "mutation_performed": False,
        "local_only": True,
        "next_safe_action": "Treat registry completion anchors as no-op evidence and repair partial preflight-only attempts before retry.",
    }


def _test_coverage_indicators(capabilities: list[dict[str, Any]]) -> dict[str, Any]:
    missing = [capability for capability in capabilities if not capability.get("targeted_tests_present")]
    return {
        "record_type": "github_automation_test_coverage_indicator_audit_v1",
        "capabilities_audited": len(capabilities),
        "capabilities_with_targeted_tests": len(capabilities) - len(missing),
        "capabilities_missing_targeted_test_indicator": len(missing),
        "missing_test_indicators": [
            {
                "capability_id": capability.get("capability_id"),
                "test_files": capability.get("test_files"),
            }
            for capability in missing
        ],
        "live_github_required_for_tests": False,
        "mocked_github_operations_required": True,
        "local_only": True,
    }


def _remaining_risks(capabilities: list[dict[str, Any]], recovery_payload: dict[str, Any]) -> list[dict[str, Any]]:
    counts = recovery_payload.get("operation_counts") if isinstance(recovery_payload.get("operation_counts"), dict) else {}
    risks: list[dict[str, Any]] = [
        _risk("live_remote_state_not_verified", "Audit uses local queue, registry, and preflight evidence only; live GitHub state must be verified by separate gated commands when needed."),
        _risk("mutation_capability_requires_operator_attention", "Mutation-capable commands exist and remain safe only when explicit enablement, autonomy profile, idempotency, and machine gates are preserved."),
        _risk("destructive_operations_remain_blocked", "Merge, auto-merge, force push, protected branch update, release, workflow mutation, source patch application, and automatic issue closure must remain outside GitHub sync automation."),
    ]
    if int(counts.get("operations_partial") or 0) > 0:
        risks.append(_risk("partial_preflight_recovery_needed", "One or more preflight artifacts lack durable registry completion; verify remote state and repair registry evidence before retry."))
    if any(not capability.get("targeted_tests_present") for capability in capabilities):
        risks.append(_risk("targeted_test_indicator_gap", "One or more implemented capabilities did not have the expected targeted test file path."))
    return risks


def _risk(risk_id: str, summary: str) -> dict[str, Any]:
    return {
        "record_type": "github_automation_remaining_risk_v1",
        "risk_id": risk_id,
        "summary": summary,
        "blocked": False,
        "blocked_reasons": [],
        "warnings": [summary],
        "dry_run": True,
        "github_enabled": False,
        "github_execution_performed": False,
        "mutation_performed": False,
        "recovery_available": True,
        "local_only": True,
        "next_safe_action": "Keep this risk under operator review before any separate live GitHub sync command.",
    }


def _allowed_operations(capabilities: list[dict[str, Any]]) -> list[str]:
    return _dedupe(operation for capability in capabilities for operation in _list(capability.get("allowed_operations")))


def _coverage_warnings(capabilities: list[dict[str, Any]]) -> list[str]:
    return _dedupe(warning for capability in capabilities for warning in _list(capability.get("warnings")))


def _next_safe_action(*, blocked: bool, capability_counts: dict[str, int], recovery_payload: dict[str, Any]) -> str:
    if blocked:
        return "Resolve audit blockers before relying on GitHub automation safety conclusions."
    counts = recovery_payload.get("operation_counts") if isinstance(recovery_payload.get("operation_counts"), dict) else {}
    if int(counts.get("operations_partial") or 0) > 0:
        return "Review recovery repair/resume plans and repair local registry evidence before any separate gated retry."
    if capability_counts.get("targeted_tests_present", 0) < capability_counts.get("capabilities_audited", 0):
        return "Review missing targeted test indicators, then keep using separate dry-run/gated GitHub commands only."
    return "GitHub automation safety audit is complete; continue with separate dry-run/default-blocked commands and explicit machine gates for any live GitHub sync."


def _gate_payload(config: AppConfig, *, item_id: str, queue_path: str | Path | None, gate_profile: str) -> dict[str, Any]:
    return _payload(
        evaluate_machine_safety_gates(
            config,
            item_id=item_id,
            gate_profile=gate_profile,
            queue_path=queue_path,
            output_format="json",
        )
    )


def _gate_summary(gate_payload: dict[str, Any], *, required_for_audit: bool) -> dict[str, Any]:
    checks = gate_payload.get("checks", [])
    failed = [
        _text(check.get("check_id"))
        for check in checks
        if isinstance(check, dict) and not bool(check.get("passed")) and not bool(check.get("warning_only"))
    ]
    return {
        "gate_profile": _text(gate_payload.get("gate_profile")) or "read_only_agent",
        "passed": _gate_passed(gate_payload),
        "blocked": bool(gate_payload.get("blocked")),
        "blocked_reasons": _list(gate_payload.get("blocked_reasons")),
        "warnings": _list(gate_payload.get("warnings")),
        "checks_failed": failed,
        "required_for_audit": required_for_audit,
        "dry_run_label": "required_read_only_audit_gate" if required_for_audit else "future_live_sync_gate_status_only",
    }


def _gate_passed(payload: dict[str, Any]) -> bool:
    return bool(payload.get("passed")) and not bool(payload.get("blocked"))


def _stdout_result(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "command": COMMAND_NAME,
        "ok": not bool(payload.get("blocked")),
        "local_only": True,
        "format": "json",
        "wrote_output_file": False,
        "stdout": json.dumps(payload, indent=2),
        "payload": payload,
    }


def _load_queue(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"ok": False, "queue": {}, "warnings": [], "blocked_reasons": [f"Project queue not found: {path}"]}
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"ok": False, "queue": {}, "warnings": [], "blocked_reasons": [f"Project queue could not be read as JSON: {exc}"]}
    if not isinstance(raw, dict):
        return {"ok": False, "queue": {}, "warnings": [], "blocked_reasons": ["Project queue JSON must decode to an object."]}
    return {"ok": True, "queue": raw, "warnings": [], "blocked_reasons": []}


def _first_int(payload: dict[str, Any], key: str) -> int | None:
    value = _int_or_none(payload.get(key))
    if value is not None:
        return value
    for record in _dicts(payload.get("records")):
        value = _int_or_none(record.get(key))
        if value is not None:
            return value
    return None


def _first_text(payload: dict[str, Any], key: str) -> str:
    value = _text(payload.get(key))
    if value:
        return value
    for record in _dicts(payload.get("records")):
        value = _text(record.get(key))
        if value:
            return value
    return ""


def _payload(result: dict[str, Any]) -> dict[str, Any]:
    payload = result.get("payload", {}) if isinstance(result, dict) else {}
    return payload if isinstance(payload, dict) else {}


def _dicts(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [entry for entry in value if isinstance(entry, dict)]
    return []


def _list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [_text(entry) for entry in value if _text(entry)]
    if isinstance(value, tuple):
        return [_text(entry) for entry in value if _text(entry)]
    if value in (None, ""):
        return []
    return [_text(value)]


def _dedupe(values: Any) -> list[str]:
    deduped: list[str] = []
    for value in values:
        text = _text(value)
        if text and text not in deduped:
            deduped.append(text)
    return deduped


def _int_or_none(value: Any) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    text = _text(value)
    return int(text) if text.isdigit() else None


def _normalize_repo(config: AppConfig, repo: str | None) -> str:
    raw = _text(repo)
    if raw:
        return raw
    return f"{config.github_owner}/{config.github_repo}"


def _audit_idempotency_key(*, project_id: str, item_id: str, repository: str) -> str:
    return "github-automation-safety-audit:" + ":".join([_slug(project_id), _slug(item_id), _slug(repository)])


def _capability_idempotency_key(*, project_id: str, capability_id: str, repository: str) -> str:
    return "github-automation-capability-audit:" + ":".join([_slug(project_id), _slug(capability_id), _slug(repository)])


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", _text(value).lower()).strip("-") or "unknown"


def _text(value: Any) -> str:
    return str(value or "").strip()


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _error(error: str, details: dict[str, Any]) -> dict[str, Any]:
    return {
        "command": COMMAND_NAME,
        "ok": False,
        "local_only": True,
        "error": error,
        "details": details,
    }
