from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.db.connection import connect
from aresforge.db.migrations import apply_migrations, discover_migrations, plan_migrations
from aresforge.db.repository import (
    DEFAULT_AGENT_ID,
    DEFAULT_MODEL_ID,
    DEFAULT_PROJECT_ID,
    bootstrap_reference_data,
    inspect_model,
    create_work_item,
    inspect_project,
    inspect_queue,
    inspect_state,
    inspect_work_item,
    list_agents,
    list_models,
    list_projects,
    list_queues,
    list_work_items,
    inspect_roadmap_db,
    inspect_roadmap_events,
    inspect_roadmap_task_dependencies,
    inspect_roadmap_work_item_links,
    inspect_queue_work_state,
    inspect_project_queue_dashboard,
    inspect_queue_readiness,
    inspect_work_item_readiness,
    inspect_work_item_lifecycle,
    build_work_item_execution_dossier,
    export_work_item_operator_prompt,
    archive_work_item_operator_packet,
    recommend_next_work_item_action,
    handoff_work_item_to_implementation,
    start_work_item_if_ready,
    complete_work_item_if_ready,
    plan_work_item_queue_transition,
    move_work_item_queue_if_allowed,
    request_work_item_queue_approval,
    approve_work_item_queue_approval,
    inspect_work_item_queue_approval_state,
    render_roadmap_markdown,
    render_roadmap_events_markdown,
    render_roadmap_task_dependencies_markdown,
    render_add_roadmap_task_dependency_markdown,
    render_remove_roadmap_task_dependency_markdown,
    render_queue_readiness_markdown,
    render_roadmap_work_item_links_markdown,
    render_queue_work_state_markdown,
    render_project_queue_dashboard_markdown,
    render_work_item_readiness_markdown,
    render_work_item_lifecycle_markdown,
    render_work_item_execution_dossier_markdown,
    render_export_work_item_operator_prompt_markdown,
    render_archive_work_item_operator_packet_markdown,
    render_next_work_item_action_recommendation_markdown,
    render_implementation_handoff_markdown,
    render_start_work_item_markdown,
    render_work_item_completion_markdown,
    render_work_item_queue_transition_plan_markdown,
    render_move_work_item_queue_markdown,
    render_work_item_queue_approval_markdown,
    seed_aresforge_roadmap,
    add_roadmap_event,
    add_roadmap_task_dependency,
    remove_roadmap_task_dependency,
    create_work_item_from_roadmap_task,
    update_work_item_status,
    update_roadmap_area_status,
    update_roadmap_milestone_status,
    update_roadmap_task_status,
    store_evidence_record,
    store_prompt_record,
    WorkItemCreate,
)
from aresforge.integrations.ollama import test_generate
from aresforge.operator.artifact_discovery import (
    discover_local_artifacts,
    discover_local_evidence_packages,
    discover_local_review_packages,
    inspect_local_artifact,
    inspect_local_evidence_package,
    inspect_local_review_package,
    latest_local_review_package_summary,
)
from aresforge.operator.agent_queue_planning import plan_agent_queue
from aresforge.operator.automation_readiness_report import automation_readiness_report
from aresforge.operator.batch_readiness_report import report_batch_readiness
from aresforge.operator.batch_closeout_planner import plan_batch_closeout
from aresforge.operator.closeout_planning_drift import inspect_closeout_planning_drift
from aresforge.operator.sprint_issue_script_generator import generate_sprint_issue_script
from aresforge.operator.child_closeout_script_generator import generate_child_closeout_script
from aresforge.operator.child_closeout_evidence_bundle import (
    generate_child_closeout_evidence_bundle,
)
from aresforge.operator.child_evidence_marker_template import generate_child_evidence_marker_template
from aresforge.operator.parent_closeout_evidence_bundle import (
    generate_parent_closeout_evidence_bundle,
)
from aresforge.operator.parent_closeout_marker_template import generate_parent_closeout_marker_template
from aresforge.operator.pr_evidence_bundle import generate_pr_evidence_bundle
from aresforge.operator.pr_evidence_marker_template import generate_pr_evidence_marker_template
from aresforge.operator.evidence_bundle_simulation import simulate_evidence_bundle_generation
from aresforge.operator.evidence_comment_template_generator import generate_evidence_comment_template
from aresforge.operator.child_execution_gates import inspect_child_execution_gates
from aresforge.operator.self_managed_issue_script_generator import generate_self_managed_issue_script
from aresforge.operator.sprint_issue_planner import plan_sprint_issues
from aresforge.operator.planning_state import (
    compare_planning_state,
    inspect_planning_state,
    resolve_planning_state_path,
)
from aresforge.operator.inspection_reports import (
    render_queue_inspection_report,
    render_work_item_inspection_report,
)
from aresforge.operator.local_review import LocalReviewOptions, run_local_review
from aresforge.operator.managed_repo_readiness_report import managed_repo_readiness_report
from aresforge.operator.managed_repo_governance_demo import demo_managed_repo_governance
from aresforge.operator.managed_repo_registry import inspect_managed_repos
from aresforge.operator.ready_issue_batch import run_ready_issue_batch
from aresforge.operator.registry_inspection import inspect_local_registries
from aresforge.operator.ready_issue_intake import (
    inspect_ready_issue,
    list_ready_issues,
)
from aresforge.operator.ready_issue_planning import plan_ready_issue
from aresforge.operator.ready_issue_pipeline import (
    MODE_CLOSEOUT_WHEN_ELIGIBLE,
    MODE_PLAN_ONLY,
    MODE_REVIEW_PR,
    run_ready_issue_pipeline,
)
from aresforge.operator.autonomous_cycle import (
    MODE_BRANCH_WRITE as AUTONOMOUS_MODE_BRANCH_WRITE,
    MODE_CLOSEOUT_ELIGIBLE as AUTONOMOUS_MODE_CLOSEOUT_ELIGIBLE,
    MODE_DRY_RUN as AUTONOMOUS_MODE_DRY_RUN,
    MODE_LOCAL_WRITE as AUTONOMOUS_MODE_LOCAL_WRITE,
    MODE_PUSH_PR as AUTONOMOUS_MODE_PUSH_PR,
    inspect_autonomous_run,
    run_autonomous_cycle,
)
from aresforge.operator.milestone_state_inspector import inspect_milestone_state
from aresforge.operator.milestone_execution_queue_planner import plan_milestone_execution_queue
from aresforge.operator.evidence_completeness_checker import (
    check_issue_evidence_readiness,
    check_milestone_evidence_readiness,
)
from aresforge.operator.milestone_dashboard import inspect_milestone_dashboard
from aresforge.operator.parent_closeout_readiness import inspect_parent_closeout_readiness
from aresforge.operator.parent_child_linkage_preflight import inspect_parent_child_linkage_preflight
from aresforge.operator.child_evidence_marker_preflight import inspect_child_evidence_marker_preflight
from aresforge.operator.pr_mapping_preflight import inspect_pr_mapping_preflight
from aresforge.operator.closeout_repair_guidance import generate_closeout_preflight_repair_guidance
from aresforge.operator.milestone_closeout_preflight import inspect_milestone_closeout_preflight
from aresforge.operator.closeout_readiness_by_construction import check_closeout_readiness_by_construction
from aresforge.operator.offline_state_template import generate_offline_closeout_state_template
from aresforge.operator.local_handoff_package import generate_handoff_package
from aresforge.operator.local_doc_reconciliation import generate_doc_reconciliation_plan
from aresforge.operator.local_github_sync_planner import generate_github_sync_plan
from aresforge.operator.github_issue_sync_plan import plan_github_issue_sync
from aresforge.operator.github_issue_creation_for_safe_queue_items import (
    create_github_issue_for_safe_queue_item,
)
from aresforge.operator.local_milestone_lifecycle import (
    check_local_milestone_readiness,
    generate_local_milestone_closeout,
    generate_local_milestone_template,
    inspect_local_milestone,
)
from aresforge.operator.local_project_state import (
    append_operation_log,
    init_project_state,
    inspect_operation_log,
    inspect_project_state as inspect_local_project_state,
    update_project_state,
)
from aresforge.operator.managed_project_registry_local import (
    PROJECT_STATUSES,
    REPO_ROLES,
    REPO_STATUSES,
    init_managed_project_registry,
    inspect_managed_project,
    inspect_managed_project_registry,
    inspect_managed_repo,
    inspect_managed_repo_github_link,
    register_managed_project,
    register_managed_repo,
)
from aresforge.operator.local_project_queue import (
    QUEUE_ITEM_TYPES,
    QUEUE_PRIORITIES,
    QUEUE_STATUSES,
    add_local_queue_item,
    add_queue_item,
    complete_local_queue_item,
    generate_local_queue_item_codex_prompt,
    init_project_queue,
    inspect_queue_consistency,
    inspect_local_queue_item_readiness,
    inspect_project_queue,
    inspect_queue_item,
    start_local_queue_item,
    update_queue_item,
)
from aresforge.operator.codex_dispatch_contract import (
    inspect_codex_dispatch_contract,
    prepare_codex_dispatch_dry_run,
)
from aresforge.operator.codex_dispatch_runner import (
    approve_codex_dispatch,
    cancel_codex_dispatch_run,
    inspect_codex_dispatch_run,
    list_codex_dispatch_runs,
    recover_codex_dispatch_run,
    run_operator_gated_codex_dispatch,
)
from aresforge.operator.codex_dispatch_executor import run_codex_dispatch_executor
from aresforge.operator.codex_result_ingestion_validation import (
    VALIDATION_PROFILES as CODEX_RESULT_VALIDATION_PROFILES,
    ingest_codex_result_and_validate,
)
from aresforge.operator.autonomous_sprint_closeout import generate_autonomous_sprint_closeout
from aresforge.operator.sprint_autonomy_readiness_report import generate_autonomy_readiness_report
from aresforge.operator.durable_orchestration_run_store import inspect_orchestration_run_store
from aresforge.operator.orchestrator_execution_state_machine import inspect_orchestrator_state_machine
from aresforge.operator.orchestration_run_history import inspect_orchestration_run_history
from aresforge.operator.orchestrator_resume_from_failure import inspect_orchestration_resume_plan
from aresforge.operator.orchestration_run_monitor import inspect_orchestration_run_monitor
from aresforge.operator.orchestration_artifact_retention_policy import inspect_orchestration_artifact_retention
from aresforge.operator.orchestration_run_replay_audit import replay_orchestration_run
from aresforge.operator.operator_autonomy_configuration_profile import inspect_autonomy_profile
from aresforge.operator.codex_execution_enablement_profile import inspect_codex_execution_enablements
from aresforge.operator.codex_execution_sandbox_worktree_guard import inspect_codex_worktree_guard
from aresforge.operator.codex_validation_profiles import inspect_codex_validation_profiles
from aresforge.operator.codex_failure_classification_retry_policy import classify_codex_failure
from aresforge.operator.agent_step_result_normalization import normalize_agent_step_result
from aresforge.operator.source_patch_risk_classifier import classify_source_patch_risk
from aresforge.operator.source_patch_apply_plan import plan_source_patch_apply
from aresforge.operator.source_patch_apply_dry_run import dry_run_source_patch_apply
from aresforge.operator.end_to_end_codex_loop_dry_run import run_end_to_end_codex_loop_dry_run
from aresforge.operator.real_codex_execution_preflight_hardening import preflight_real_codex_execution
from aresforge.operator.low_risk_codex_execution_pilot_item import prepare_low_risk_codex_pilot
from aresforge.operator.codex_loop_validation_evidence_bundle import bundle_codex_loop_validation_evidence
from aresforge.operator.github_sync_agent import run_github_sync_agent
from aresforge.operator.multi_agent_orchestrator import run_multi_agent_orchestration
from aresforge.operator.llm_decision_matrix import inspect_llm_decision_matrix
from aresforge.operator.local_coding_draft import prepare_local_coding_draft_artifact
from aresforge.operator.documentation_agent_contract import inspect_documentation_agent_contract
from aresforge.operator.human_gated_patch_contract import inspect_human_gated_patch_application_contract
from aresforge.operator.local_llm_advisory import prepare_local_llm_advisory_run_artifact
from aresforge.operator.local_llm_advisory_lane import inspect_local_llm_advisory_lane_readiness
from aresforge.operator.local_llm_provider import (
    inspect_local_llm_provider_contract,
    inspect_ollama_health_and_models,
)
from aresforge.operator.local_ollama_provider_probe import probe_local_ollama_provider
from aresforge.operator.queue_dispatch_preparation import prepare_queue_item_dispatch
from aresforge.operator.queue_agent_dispatch_plan import inspect_queue_agent_dispatch_plan
from aresforge.operator.codex_prompt_dispatch_artifact import generate_codex_prompt_dispatch_artifact
from aresforge.operator.local_llm_advisory_dry_run import validate_local_llm_advisory_dry_run
from aresforge.operator.local_llm_advisory_artifact import generate_local_llm_advisory_artifact
from aresforge.operator.local_llm_advisory_execution import run_local_llm_advisory_execution
from aresforge.operator.documentation_agent_dry_run import validate_documentation_agent_dry_run
from aresforge.operator.documentation_agent_patch_proposal import generate_documentation_agent_patch_proposal
from aresforge.operator.approval_gated_patch_intake import intake_patch_proposal
from aresforge.operator.dispatch_result_evidence_parser import parse_dispatch_result_evidence
from aresforge.operator.queue_completion_recommendation import recommend_queue_completion
from aresforge.operator.agent_route_recommendation import recommend_agent_route
from aresforge.operator.dispatch_approval_gate import (
    APPROVAL_GATE_STATUSES,
    create_dispatch_approval_gate,
    inspect_dispatch_approval_gate,
    update_dispatch_approval_gate,
)
from aresforge.operator.dispatch_artifact_report import inspect_dispatch_artifacts
from aresforge.operator.dispatch_artifact_registry import inspect_artifact_registry
from aresforge.operator.human_approval_review_ledger import inspect_approval_ledger, record_artifact_review
from aresforge.operator.safe_dispatch_handoff import generate_safe_dispatch_handoff
from aresforge.operator.manual_codex_dispatch_runner import prepare_manual_codex_dispatch
from aresforge.operator.agent_runtime_boundary import inspect_agent_runtime_boundary
from aresforge.operator.agent_registry import inspect_agent_registry
from aresforge.operator.agent_orchestration_plan_builder import build_agent_orchestration_plan
from aresforge.operator.llm_decision_policy import recommend_llm_decision
from aresforge.operator.single_agent_dry_run_executor import run_single_agent_dry_run
from aresforge.operator.single_agent_real_executor import run_single_agent_real_execution
from aresforge.operator.machine_safety_gate_engine import evaluate_machine_safety_gates
from aresforge.operator.auto_complete_safe_queue_item import auto_complete_safe_queue_item
from aresforge.operator.docs_only_patch_apply import apply_docs_only_patch
from aresforge.operator.single_ready_codex_queue_item import run_single_ready_codex_queue_item
from aresforge.operator.local_agent_profiles import (
    AGENT_PROFILE_STATUSES,
    AGENT_ROLES,
    EXECUTION_MODES,
    HANDOFF_TARGET_TYPES,
    init_agent_profiles,
    inspect_agent_profile,
    inspect_agent_profiles,
    inspect_handoff_target,
    register_agent_profile,
    register_handoff_target,
)
from aresforge.operator.local_agent_orchestration import generate_agent_orchestration_plan
from aresforge.operator.local_llm_escalation import generate_llm_escalation_plan
from aresforge.operator.local_bootstrap_wizard import (
    apply_bootstrap,
    inspect_bootstrap_status,
    plan_bootstrap,
)
from aresforge.operator.local_project_dashboard import summarize_local_project_dashboard
from aresforge.operator.local_project_readiness import (
    inspect_local_project_readiness,
    list_local_projects,
)
from aresforge.operator.local_queue_agent_summary import inspect_local_queue_agent_summary
from aresforge.operator.local_project_report import inspect_local_project_report
from aresforge.operator.self_managed_project_report import inspect_self_managed_project
from aresforge.operator.model_usage_report import inspect_model_usage_report
from aresforge.operator.sprint_batch_report import inspect_sprint_batch_report
from aresforge.operator.operator_batch_planner import plan_operator_batch
from aresforge.operator.operator_batch_queue_sequencer_v2 import plan_operator_batch_v2
from aresforge.operator.queue_transaction_log import inspect_queue_transaction_log
from aresforge.operator.self_seed import seed_aresforge_self_project
from aresforge.hub.server import serve_hub
from aresforge.operator.milestone_reconciliation_planner import plan_milestone_final_reconciliation
from aresforge.operator.preflight_snapshot import (
    diff_preflight_snapshots,
    generate_preflight_baseline_snapshot,
)
from aresforge.operator.sequential_run_state import (
    inspect_sequential_run_state,
    resolve_sequential_run_state_path,
)
from aresforge.operator.sequential_recovery_planner import plan_sequential_run_recovery
from aresforge.operator.sequential_handoff_package import generate_sequential_handoff_package
from aresforge.operator.sequential_child_closeout_flow import run_sequential_child_closeout_flow
from aresforge.operator.sequential_closeout_execution_package import (
    generate_sequential_closeout_execution_package,
)
from aresforge.operator.project_state_summary import project_state_summary
from aresforge.operator.self_managed_milestone_planner import plan_self_managed_milestone
from aresforge.operator.self_managed_milestone_execution_contract import (
    inspect_self_managed_milestone_execution_contract,
)
from aresforge.operator.self_managed_milestone_handoff import (
    generate_self_managed_milestone_handoff,
)
from aresforge.operator.self_managed_milestone_simulation import (
    simulate_self_managed_milestone_execution,
)
from aresforge.operator.repo_bootstrap_contract import inspect_repo_bootstrap_contract
from aresforge.operator.repo_bootstrap_plan import plan_repo_bootstrap
from aresforge.operator.repo_governance import inspect_repo_governance
from aresforge.operator.repo_assessment import AssessmentOptions, assess_repository
from aresforge.operator.evidence_bundle_automation_contract import (
    inspect_evidence_bundle_automation_contract,
)
from aresforge.operator.milestone_closeout_preflight_contract import (
    inspect_milestone_closeout_preflight_contract,
)
from aresforge.operator.canonical_evidence_marker_contract import (
    inspect_canonical_evidence_marker_contract,
)
from aresforge.operator.automatic_canonical_evidence_emission_contract import (
    inspect_automatic_canonical_evidence_emission_contract,
)
from aresforge.operator.github_mutation_planner import plan_github_mutation
from aresforge.operator.github_issue_comment_executor import (
    execute_github_issue_comment,
    load_comment_body,
)
from aresforge.operator.github_issue_close_executor import execute_github_issue_close
from aresforge.operator.pr_body_update_helper import prepare_pr_body_update
from aresforge.operator.github_mutation_audit_log import inspect_github_mutation_audit_log
from aresforge.operator.qa_closeout_pr import qa_closeout_pr
from aresforge.operator.qa_pr_validation import qa_review_pr
from aresforge.operator.validate_pr_end_to_end import validate_pr_end_to_end
from aresforge.operator.service import (
    render_codex_handoff,
    render_evidence_package,
    render_prompt_package,
)
from aresforge.routing.routes import build_route_plan
from aresforge.validation import validate_registry_seed_data


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aresforge", description="AresForge local operator CLI.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("validate-config", help="Validate local configuration and artifact paths.")
    subparsers.add_parser(
        "validate-registries",
        help="Validate seeded queue and agent registry data without mutating local state.",
    )

    migrate_parser = subparsers.add_parser("migrate", help="Apply PostgreSQL migrations.")
    migrate_parser.add_argument(
        "--plan",
        action="store_true",
        help="List pending migration files without applying them.",
    )
    subparsers.add_parser(
        "init-roadmap-schema",
        help="Apply migrations and bootstrap reference data for roadmap schema foundation.",
    )
    subparsers.add_parser(
        "seed-aresforge-roadmap",
        help="Apply migrations, bootstrap references, and seed roadmap control data.",
    )
    inspect_roadmap_db_parser = subparsers.add_parser(
        "inspect-roadmap-db",
        help="Inspect DB-backed roadmap control state without mutation.",
    )
    inspect_roadmap_db_parser.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="json",
    )
    update_roadmap_task_parser = subparsers.add_parser(
        "update-roadmap-task-status",
        help="Update one roadmap task status and append a roadmap event when changed.",
    )
    update_roadmap_task_parser.add_argument("--task-id", required=True)
    update_roadmap_task_parser.add_argument("--status", required=True)
    update_roadmap_task_parser.add_argument("--summary")
    update_roadmap_task_parser.add_argument("--details-json")
    update_roadmap_task_parser.add_argument("--details-file")
    update_roadmap_milestone_parser = subparsers.add_parser(
        "update-roadmap-milestone-status",
        help="Update one roadmap milestone status and append a roadmap event when changed.",
    )
    update_roadmap_milestone_parser.add_argument("--milestone-id", required=True)
    update_roadmap_milestone_parser.add_argument("--status", required=True)
    update_roadmap_milestone_parser.add_argument("--summary")
    update_roadmap_milestone_parser.add_argument("--details-json")
    update_roadmap_milestone_parser.add_argument("--details-file")
    update_roadmap_area_parser = subparsers.add_parser(
        "update-roadmap-area-status",
        help="Update one roadmap area status and append a roadmap event when changed.",
    )
    update_roadmap_area_parser.add_argument("--area-id", required=True)
    update_roadmap_area_parser.add_argument("--status", required=True)
    update_roadmap_area_parser.add_argument("--summary")
    update_roadmap_area_parser.add_argument("--details-json")
    update_roadmap_area_parser.add_argument("--details-file")
    add_roadmap_event_parser = subparsers.add_parser(
        "add-roadmap-event",
        help="Append one roadmap event without mutating roadmap status.",
    )
    add_roadmap_event_parser.add_argument("--event-type", required=True)
    add_roadmap_event_parser.add_argument("--summary", required=True)
    add_roadmap_event_parser.add_argument("--project-id", default=DEFAULT_PROJECT_ID)
    add_roadmap_event_parser.add_argument("--area-id")
    add_roadmap_event_parser.add_argument("--milestone-id")
    add_roadmap_event_parser.add_argument("--task-id")
    add_roadmap_event_parser.add_argument("--details-json")
    add_roadmap_event_parser.add_argument("--details-file")
    inspect_roadmap_events_parser = subparsers.add_parser(
        "inspect-roadmap-events",
        help="Inspect roadmap events without mutating state.",
    )
    inspect_roadmap_events_parser.add_argument("--project-id", default=DEFAULT_PROJECT_ID)
    inspect_roadmap_events_parser.add_argument("--limit", type=int, default=20)
    inspect_roadmap_events_parser.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="json",
    )
    add_roadmap_task_dependency_parser = subparsers.add_parser(
        "add-roadmap-task-dependency",
        help="Add one local roadmap task dependency.",
    )
    add_roadmap_task_dependency_parser.add_argument("--task-id", required=True)
    add_roadmap_task_dependency_parser.add_argument("--depends-on-task-id", required=True)
    add_roadmap_task_dependency_parser.add_argument("--dependency-type", default="blocks")
    add_roadmap_task_dependency_parser.add_argument("--actor", default="local-operator")
    add_roadmap_task_dependency_parser.add_argument("--details-file")
    add_roadmap_task_dependency_parser.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="json",
    )
    remove_roadmap_task_dependency_parser = subparsers.add_parser(
        "remove-roadmap-task-dependency",
        help="Remove one local roadmap task dependency.",
    )
    remove_roadmap_task_dependency_parser.add_argument("--task-id", required=True)
    remove_roadmap_task_dependency_parser.add_argument("--depends-on-task-id", required=True)
    remove_roadmap_task_dependency_parser.add_argument("--actor", default="local-operator")
    remove_roadmap_task_dependency_parser.add_argument("--details-file")
    remove_roadmap_task_dependency_parser.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="json",
    )
    inspect_roadmap_task_dependencies_parser = subparsers.add_parser(
        "inspect-roadmap-task-dependencies",
        help="Inspect local roadmap task dependencies.",
    )
    inspect_roadmap_task_dependencies_parser.add_argument("--task-id")
    inspect_roadmap_task_dependencies_parser.add_argument("--project-id", default=DEFAULT_PROJECT_ID)
    inspect_roadmap_task_dependencies_parser.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="json",
    )
    create_work_item_from_roadmap_task_parser = subparsers.add_parser(
        "create-work-item-from-roadmap-task",
        help="Create and link one local work item from a roadmap task.",
    )
    create_work_item_from_roadmap_task_parser.add_argument("--task-id", required=True)
    create_work_item_from_roadmap_task_parser.add_argument("--queue-id")
    create_work_item_from_roadmap_task_parser.add_argument("--priority", default="normal")
    create_work_item_from_roadmap_task_parser.add_argument("--summary")
    create_work_item_from_roadmap_task_parser.add_argument("--details-json")
    create_work_item_from_roadmap_task_parser.add_argument("--details-file")
    update_work_item_status_parser = subparsers.add_parser(
        "update-work-item-status",
        help="Update one local work item lifecycle status with audit and linked roadmap event logging.",
    )
    update_work_item_status_parser.add_argument("--work-item-id", required=True)
    update_work_item_status_parser.add_argument("--status", required=True)
    update_work_item_status_parser.add_argument("--summary")
    update_work_item_status_parser.add_argument("--details-json")
    update_work_item_status_parser.add_argument("--details-file")
    start_work_item_parser = subparsers.add_parser(
        "start-work-item",
        help="Start one local work item only when readiness gates pass.",
    )
    start_work_item_parser.add_argument("--work-item-id", required=True)
    start_work_item_parser.add_argument("--actor", default="local-operator")
    start_work_item_parser.add_argument("--details-file")
    start_work_item_parser.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="json",
    )
    complete_work_item_parser = subparsers.add_parser(
        "complete-work-item-if-ready",
        help="Complete one local work item only when completion gates pass.",
    )
    complete_work_item_parser.add_argument("--work-item-id", required=True)
    complete_work_item_parser.add_argument("--actor", required=True)
    complete_work_item_parser.add_argument("--details-file")
    complete_work_item_parser.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="json",
    )
    plan_queue_transition_parser = subparsers.add_parser(
        "plan-work-item-queue-transition",
        help="Plan a local queue transition for one work item without mutation.",
    )
    plan_queue_transition_parser.add_argument("--work-item-id", required=True)
    plan_queue_transition_parser.add_argument("--target-queue-id", required=True)
    plan_queue_transition_parser.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="json",
    )
    move_queue_parser = subparsers.add_parser(
        "move-work-item-queue",
        help="Move one local work item queue only when transition planning allows it.",
    )
    move_queue_parser.add_argument("--work-item-id", required=True)
    move_queue_parser.add_argument("--target-queue-id", required=True)
    move_queue_parser.add_argument("--actor", default="local-operator")
    move_queue_parser.add_argument("--details-file")
    move_queue_parser.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="json",
    )
    request_queue_approval_parser = subparsers.add_parser(
        "request-work-item-queue-approval",
        help="Request a local approval gate for moving one work item to a target queue.",
    )
    request_queue_approval_parser.add_argument("--work-item-id", required=True)
    request_queue_approval_parser.add_argument("--target-queue-id", required=True)
    request_queue_approval_parser.add_argument("--actor", required=True)
    request_queue_approval_parser.add_argument("--details-file")
    request_queue_approval_parser.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="json",
    )
    approve_queue_approval_parser = subparsers.add_parser(
        "approve-work-item-queue-approval",
        help="Approve a local approval gate for moving one work item to a target queue.",
    )
    approve_queue_approval_parser.add_argument("--work-item-id", required=True)
    approve_queue_approval_parser.add_argument("--target-queue-id", required=True)
    approve_queue_approval_parser.add_argument("--actor", required=True)
    approve_queue_approval_parser.add_argument("--details-file")
    approve_queue_approval_parser.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="json",
    )
    inspect_queue_approval_parser = subparsers.add_parser(
        "inspect-work-item-queue-approval",
        help="Inspect local approval gate state for a work item and target queue.",
    )
    inspect_queue_approval_parser.add_argument("--work-item-id", required=True)
    inspect_queue_approval_parser.add_argument("--target-queue-id", required=True)
    inspect_queue_approval_parser.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="json",
    )
    handoff_implementation_parser = subparsers.add_parser(
        "handoff-work-item-to-implementation",
        help="Move one local work item to implementation when transition gates allow it, then return an execution dossier.",
    )
    handoff_implementation_parser.add_argument("--work-item-id", required=True)
    handoff_implementation_parser.add_argument("--actor", default="local-operator")
    handoff_implementation_parser.add_argument("--details-file")
    handoff_implementation_parser.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="json",
    )
    inspect_work_item_lifecycle_parser = subparsers.add_parser(
        "inspect-work-item-lifecycle",
        help="Inspect one local work item lifecycle with links and events.",
    )
    inspect_work_item_lifecycle_parser.add_argument("--work-item-id", required=True)
    inspect_work_item_lifecycle_parser.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="json",
    )
    build_execution_dossier_parser = subparsers.add_parser(
        "build-work-item-execution-dossier",
        help="Build a read-only local execution dossier for one work item.",
    )
    build_execution_dossier_parser.add_argument("--work-item-id", required=True)
    build_execution_dossier_parser.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="json",
    )
    export_operator_prompt_parser = subparsers.add_parser(
        "export-work-item-operator-prompt",
        help="Export a work item execution dossier suggested operator prompt to a local UTF-8 file.",
    )
    export_operator_prompt_parser.add_argument("--work-item-id", required=True)
    export_operator_prompt_parser.add_argument("--output", required=True)
    export_operator_prompt_parser.add_argument("--force", action="store_true")
    export_operator_prompt_parser.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="json",
    )
    archive_operator_packet_parser = subparsers.add_parser(
        "archive-work-item-operator-packet",
        help="Archive a local operator packet with dossier and prompt for one work item.",
    )
    archive_operator_packet_parser.add_argument("--work-item-id", required=True)
    archive_operator_packet_parser.add_argument("--output-dir", required=True)
    archive_operator_packet_parser.add_argument("--actor", required=True)
    archive_operator_packet_parser.add_argument("--force", action="store_true")
    archive_operator_packet_parser.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="json",
    )
    recommend_next_work_item_action_parser = subparsers.add_parser(
        "recommend-next-work-item-action",
        help="Recommend the safest next local CLI action for one work item using read-only state.",
    )
    recommend_next_work_item_action_parser.add_argument("--work-item-id", required=True)
    recommend_next_work_item_action_parser.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="json",
    )
    inspect_queue_work_state_parser = subparsers.add_parser(
        "inspect-queue-work-state",
        help="Inspect queue-local work state grouped by queue and status.",
    )
    inspect_queue_work_state_parser.add_argument("--project-id", default=DEFAULT_PROJECT_ID)
    inspect_queue_work_state_parser.add_argument("--queue-id")
    inspect_queue_work_state_parser.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="json",
    )
    inspect_work_item_readiness_parser = subparsers.add_parser(
        "inspect-work-item-readiness",
        help="Inspect local work item readiness gates without mutating state.",
    )
    inspect_work_item_readiness_parser.add_argument("--work-item-id", required=True)
    inspect_work_item_readiness_parser.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="json",
    )
    inspect_queue_readiness_parser = subparsers.add_parser(
        "inspect-queue-readiness",
        help="Inspect queue-local readiness gates without mutating state.",
    )
    inspect_queue_readiness_parser.add_argument("--project-id", default=DEFAULT_PROJECT_ID)
    inspect_queue_readiness_parser.add_argument("--queue-id")
    inspect_queue_readiness_parser.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="json",
    )
    inspect_project_queue_dashboard_parser = subparsers.add_parser(
        "inspect-project-queue-dashboard",
        help="Inspect a read-only local project and queue dashboard summary.",
    )
    inspect_project_queue_dashboard_parser.add_argument("--project-id", default=DEFAULT_PROJECT_ID)
    inspect_project_queue_dashboard_parser.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="json",
    )
    inspect_roadmap_work_item_links_parser = subparsers.add_parser(
        "inspect-roadmap-work-item-links",
        help="Inspect roadmap-to-work-item bridge links without mutating state.",
    )
    inspect_roadmap_work_item_links_parser.add_argument("--project-id", default=DEFAULT_PROJECT_ID)
    inspect_roadmap_work_item_links_parser.add_argument("--task-id")
    inspect_roadmap_work_item_links_parser.add_argument("--work-item-id")
    inspect_roadmap_work_item_links_parser.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="json",
    )

    subparsers.add_parser("inspect-db-state", help="Show local database state summary.")
    inspect_project_parser = subparsers.add_parser(
        "inspect-project", help="Inspect one local project record with expanded metadata."
    )
    inspect_project_parser.add_argument("--project-id", required=True)
    subparsers.add_parser(
        "inspect-registries",
        help="Summarize documented local registry and lifecycle sources in the repo.",
    )
    subparsers.add_parser(
        "list-artifacts",
        help="Summarize generated local artifacts under the configured artifact root.",
    )
    subparsers.add_parser(
        "list-review-packages",
        help="Summarize generated local review packages under the configured review package root.",
    )
    run_local_review_parser = subparsers.add_parser(
        "run-local-review",
        help="Run a bounded deterministic local review orchestration over existing operator checks.",
    )
    run_local_review_parser.add_argument("--project-id", default=DEFAULT_PROJECT_ID)
    run_local_review_parser.add_argument("--model-id", default=DEFAULT_MODEL_ID)
    run_local_review_parser.add_argument(
        "--include-artifacts",
        action="store_true",
        help="Include a read-only list-artifacts summary in the local review.",
    )
    run_local_review_parser.add_argument(
        "--artifact-path",
        help="Inspect one explicit safe artifact path under the configured artifact root.",
    )
    run_local_review_parser.add_argument(
        "--include-evidence-packages",
        action="store_true",
        help="Include a read-only list-evidence-packages summary in the local review.",
    )
    run_local_review_parser.add_argument(
        "--evidence-path",
        help="Inspect one explicit safe evidence path under the configured evidence root.",
    )
    run_local_review_parser.add_argument(
        "--write-review-package",
        action="store_true",
        help="Write a local review package artifact while still emitting JSON.",
    )
    subparsers.add_parser(
        "list-evidence-packages",
        help="Summarize generated local evidence packages under the configured evidence root.",
    )
    subparsers.add_parser(
        "list-ready-issues",
        help="List GitHub issues labeled for ready intake without mutating GitHub state.",
    )
    inspect_ready_issue_parser = subparsers.add_parser(
        "inspect-ready-issue",
        help="Inspect one GitHub issue labeled for ready intake without mutating GitHub state.",
    )
    inspect_ready_issue_parser.add_argument("--issue-number", type=int, required=True)
    plan_ready_issue_parser = subparsers.add_parser(
        "plan-ready-issue",
        help="Plan agent and model routing for a ready issue without mutating GitHub state.",
    )
    plan_ready_issue_parser.add_argument("--issue-number", type=int, required=True)
    ready_pipeline_parser = subparsers.add_parser(
        "run-ready-issue-pipeline",
        help="Run reusable ready issue orchestration with safe non-mutating defaults.",
    )
    ready_pipeline_parser.add_argument("--issue-number", type=int, required=True)
    ready_pipeline_parser.add_argument("--pr-number", type=int)
    mode_group = ready_pipeline_parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        "--plan-only",
        action="store_true",
        help="Inspect and plan one ready issue without PR validation or closeout.",
    )
    mode_group.add_argument(
        "--review-pr",
        action="store_true",
        help="Run planning plus qa-review-pr for one issue/PR pair.",
    )
    mode_group.add_argument(
        "--closeout-when-eligible",
        action="store_true",
        help="Delegate closeout eligibility through qa-closeout-pr after all gates pass.",
    )
    ready_pipeline_parser.add_argument(
        "--execute-closeout",
        action="store_true",
        help="Enable execute mode delegation to qa-closeout-pr in closeout mode only.",
    )
    ready_pipeline_parser.add_argument(
        "--write-review-package",
        action="store_true",
        help="Optionally write a local review package artifact during review/closeout modes.",
    )
    ready_pipeline_parser.add_argument(
        "--write-evidence-package",
        action="store_true",
        help="Optionally write an evidence package artifact for review/closeout modes.",
    )
    ready_pipeline_parser.add_argument(
        "--write-implementation-handoff",
        action="store_true",
        help="Optionally write a Codex handoff artifact for plan-only mode.",
    )
    ready_batch_parser = subparsers.add_parser(
        "run-ready-issue-batch",
        help="Run read-only batch planning for ready issues and write local batch artifacts.",
    )
    ready_batch_parser.add_argument(
        "--plan-only",
        action="store_true",
        help="Required safety mode for this command.",
    )
    ready_batch_parser.add_argument(
        "--write-selected-handoffs",
        action="store_true",
        help="Optionally write local handoff packages for Copilot/Codex-selected issues.",
    )
    ready_batch_parser.add_argument(
        "--timestamp-override",
        help="Optional artifact timestamp override for deterministic tests (YYYYMMDDTHHMMSSZ).",
    )
    subparsers.add_parser(
        "automation-readiness-report",
        help="Emit a read-only automation readiness dashboard summary.",
    )
    plan_agent_queue_parser = subparsers.add_parser(
        "plan-agent-queue",
        help="Generate a read-only queue-driven execution plan for eligible issues.",
    )
    plan_agent_queue_parser.add_argument(
        "--issue-number",
        type=int,
        action="append",
        default=[],
        help="Optional issue number to include. May be provided multiple times.",
    )
    plan_agent_queue_parser.add_argument(
        "--issues-file",
        help="Optional JSON file with an `issues` array for deterministic local planning input.",
    )
    batch_readiness_parser = subparsers.add_parser(
        "report-batch-readiness",
        help="Generate a read-only multi-issue batch validation and closeout readiness summary.",
    )
    batch_readiness_parser.add_argument("--pr-number", type=int)
    batch_readiness_parser.add_argument(
        "--issue-number",
        type=int,
        action="append",
        default=[],
        help="Optional issue number to include. May be provided multiple times.",
    )
    batch_readiness_parser.add_argument(
        "--issues-file",
        help="Optional JSON file with an `issues` array for deterministic issue coverage input.",
    )
    batch_readiness_parser.add_argument(
        "--changed-file",
        action="append",
        default=[],
        help="Optional changed file path override. May be provided multiple times.",
    )
    batch_readiness_parser.add_argument(
        "--validation",
        action="append",
        default=[],
        help="Validation command evidence entry. May be provided multiple times.",
    )
    batch_closeout_parser = subparsers.add_parser(
        "plan-batch-closeout",
        help="Generate a read-only parent/child issue closeout readiness plan.",
    )
    batch_closeout_parser.add_argument("--parent-issue", type=int, required=True)
    batch_closeout_parser.add_argument(
        "--write-planning-snapshot",
        action="store_true",
        help="Explicitly persist this closeout planning snapshot to local planning state.",
    )
    batch_closeout_parser.add_argument(
        "--planning-state-path",
        help="Optional local planning state path override (defaults to .aresforge/planning-state.json).",
    )
    sprint_issue_script_parser = subparsers.add_parser(
        "generate-sprint-issue-script",
        help="Generate a read-only PowerShell sprint issue creation script from a local JSON definition.",
    )
    sprint_issue_script_parser.add_argument("--definition", required=True)
    sprint_issue_script_parser.add_argument("--output")
    sprint_issue_script_parser.add_argument(
        "--write-planning-state",
        action="store_true",
        help="Explicitly persist sprint planning metadata to local planning state.",
    )
    sprint_issue_script_parser.add_argument(
        "--planning-state-path",
        help="Optional local planning state path override (defaults to .aresforge/planning-state.json).",
    )
    sprint_issue_plan_parser = subparsers.add_parser(
        "plan-sprint-issues",
        help="Render a read-only, human-gated sprint issue creation plan from a local JSON definition.",
    )
    sprint_issue_plan_parser.add_argument("--definition", required=True)
    self_managed_milestone_parser = subparsers.add_parser(
        "plan-self-managed-milestone",
        help="Plan deterministic self-managed milestone sequencing with read-only default and local-write run queue initialization.",
    )
    self_managed_milestone_parser.add_argument(
        "--mode",
        default="read-only",
        choices=[
            "read-only",
            "local-write",
            "branch-write",
            "pr-write",
            "closeout-write",
            "full-auto",
        ],
    )
    subparsers.add_parser(
        "inspect-self-managed-milestone-execution-contract",
        help="Inspect the read-only M21 self-managed milestone execution contract.",
    )
    self_managed_simulation_parser = subparsers.add_parser(
        "simulate-self-managed-milestone-execution",
        help="Run a read-only dry-run simulation of M21 self-managed milestone execution.",
    )
    self_managed_simulation_parser.add_argument("--parent-issue", type=int, required=True)
    self_managed_handoff_parser = subparsers.add_parser(
        "generate-self-managed-milestone-handoff",
        help="Generate deterministic read-only M21 recovery/handoff package after a completed child.",
    )
    self_managed_handoff_parser.add_argument("--parent-issue", type=int, required=True)
    self_managed_handoff_parser.add_argument("--completed-child", type=int, required=True)
    self_managed_handoff_parser.add_argument("--next-child", type=int)
    self_managed_handoff_parser.add_argument("--pr-url")
    self_managed_handoff_parser.add_argument("--evidence-comment-url")
    self_managed_handoff_parser.add_argument("--validation-result", action="append", default=[])
    self_managed_handoff_parser.add_argument("--warning", action="append", default=[])
    self_managed_issue_script_parser = subparsers.add_parser(
        "generate-self-managed-issue-script",
        help="Generate human-gated PowerShell issue guidance from self-managed milestone run queue state.",
    )
    self_managed_issue_script_parser.add_argument(
        "--run-id",
        help="Optional autonomous run identifier to use as the script source.",
    )
    self_managed_issue_script_parser.add_argument(
        "--target-issue",
        type=int,
        help="Optional explicit target issue override.",
    )
    self_managed_issue_script_parser.add_argument(
        "--mode",
        default="read-only",
        choices=[
            "read-only",
            "local-write",
            "branch-write",
            "pr-write",
            "closeout-write",
            "full-auto",
        ],
    )
    child_closeout_script_parser = subparsers.add_parser(
        "generate-child-closeout-script",
        help="Generate read-only, operator-reviewed PowerShell closeout commands for one child issue.",
    )
    child_closeout_script_parser.add_argument("--issue", type=int, required=True)
    child_closeout_bundle_parser = subparsers.add_parser(
        "generate-child-closeout-evidence-bundle",
        help="Generate read-only child closeout evidence bundle text and closeout guidance.",
    )
    child_closeout_bundle_parser.add_argument("--parent-issue", type=int, required=True)
    child_closeout_bundle_parser.add_argument("--child-issue", type=int, required=True)
    child_marker_template_parser = subparsers.add_parser(
        "generate-child-evidence-marker-template",
        help="Generate read-only canonical child evidence marker template text.",
    )
    child_marker_template_parser.add_argument("--parent-issue", type=int, required=True)
    child_marker_template_parser.add_argument("--child-issue", type=int, required=True)
    parent_closeout_bundle_parser = subparsers.add_parser(
        "generate-parent-closeout-evidence-bundle",
        help="Generate read-only parent closeout evidence bundle text and targeted closeout guidance.",
    )
    parent_closeout_bundle_parser.add_argument("--parent-issue", type=int, required=True)
    parent_closeout_bundle_parser.add_argument(
        "--state-file",
        help="Optional local JSON state file for offline parent closeout evidence bundle generation.",
    )
    parent_marker_template_parser = subparsers.add_parser(
        "generate-parent-closeout-marker-template",
        help="Generate read-only canonical parent closeout evidence marker template text.",
    )
    parent_marker_template_parser.add_argument("--parent-issue", type=int, required=True)
    pr_evidence_bundle_parser = subparsers.add_parser(
        "generate-pr-evidence-bundle",
        help="Generate read-only deterministic PR evidence body text and targeted update guidance.",
    )
    pr_evidence_bundle_parser.add_argument("--issue", type=int, required=True)
    pr_evidence_bundle_parser.add_argument("--pr", type=int, required=True)
    pr_marker_template_parser = subparsers.add_parser(
        "generate-pr-evidence-marker-template",
        help="Generate read-only canonical PR evidence marker template text.",
    )
    pr_marker_template_parser.add_argument("--issue", type=int, required=True)
    pr_marker_template_parser.add_argument("--pr", type=int, required=True)
    evidence_bundle_simulation_parser = subparsers.add_parser(
        "simulate-evidence-bundle-generation",
        help="Run read-only dry-run simulation for milestone evidence bundle generation flows.",
    )
    evidence_bundle_simulation_parser.add_argument("--parent-issue", type=int, required=True)
    evidence_comment_template_parser = subparsers.add_parser(
        "generate-evidence-comment-template",
        help="Generate a read-only issue-specific evidence comment template for operator review.",
    )
    evidence_comment_template_parser.add_argument("--issue", type=int, required=True)
    autonomous_cycle_parser = subparsers.add_parser(
        "run-autonomous-cycle",
        help="Run controlled autonomous execution with explicit safety-gated modes.",
    )
    autonomous_cycle_parser.add_argument(
        "--mode",
        required=True,
        choices=[
            AUTONOMOUS_MODE_DRY_RUN,
            AUTONOMOUS_MODE_LOCAL_WRITE,
            AUTONOMOUS_MODE_BRANCH_WRITE,
            AUTONOMOUS_MODE_PUSH_PR,
            AUTONOMOUS_MODE_CLOSEOUT_ELIGIBLE,
        ],
    )
    autonomous_cycle_parser.add_argument("--parent-issue", type=int, required=True)
    autonomous_cycle_parser.add_argument("--target-issue", type=int, required=True)
    autonomous_cycle_parser.add_argument("--title")
    autonomous_cycle_parser.add_argument("--branch-name")
    autonomous_cycle_parser.add_argument("--commit-message")
    autonomous_cycle_parser.add_argument("--pr-title")
    autonomous_cycle_parser.add_argument("--pr-body")
    autonomous_cycle_parser.add_argument(
        "--validation-command",
        action="append",
        default=[],
        help="Validation command for gate/evidence tracking. May be provided multiple times.",
    )
    autonomous_cycle_parser.add_argument(
        "--allow-empty-commit",
        action="store_true",
        help="Allow an empty commit in branch-write or higher modes.",
    )
    inspect_autonomous_run_parser = subparsers.add_parser(
        "inspect-autonomous-run",
        help="Inspect one DB-backed autonomous run and recorded steps.",
    )
    inspect_autonomous_run_parser.add_argument("--run-id", required=True)
    inspect_milestone_state_parser = subparsers.add_parser(
        "inspect-milestone-state",
        help="Inspect milestone parent/child issue state in read-only mode.",
    )
    inspect_milestone_state_parser.add_argument("--parent-issue", type=int, required=True)
    inspect_milestone_state_parser.add_argument(
        "--state-file",
        help="Optional local JSON state file for offline milestone inspection.",
    )
    milestone_queue_parser = subparsers.add_parser(
        "plan-milestone-execution-queue",
        help="Plan milestone child issue execution order in read-only mode.",
    )
    milestone_queue_parser.add_argument("--parent-issue", type=int, required=True)
    issue_evidence_parser = subparsers.add_parser(
        "check-issue-evidence-readiness",
        help="Check issue evidence completeness for closeout readiness in read-only mode.",
    )
    issue_evidence_parser.add_argument("--issue", type=int, required=True)
    milestone_evidence_parser = subparsers.add_parser(
        "check-milestone-evidence-readiness",
        help="Check milestone child issue evidence completeness in read-only mode.",
    )
    milestone_evidence_parser.add_argument("--parent-issue", type=int, required=True)
    milestone_evidence_parser.add_argument(
        "--state-file",
        help="Optional local JSON state file for offline milestone evidence readiness checks.",
    )
    milestone_final_reconciliation_parser = subparsers.add_parser(
        "plan-milestone-final-reconciliation",
        help="Plan milestone final reconciliation readiness in read-only mode.",
    )
    milestone_final_reconciliation_parser.add_argument("--parent-issue", type=int, required=True)
    milestone_dashboard_parser = subparsers.add_parser(
        "inspect-milestone-dashboard",
        help="Inspect a unified read-only milestone execution dashboard.",
    )
    milestone_dashboard_parser.add_argument("--parent-issue", type=int, required=True)
    parent_closeout_readiness_parser = subparsers.add_parser(
        "inspect-parent-closeout-readiness",
        help="Inspect parent closeout readiness with explicit child lineage in read-only mode.",
    )
    parent_closeout_readiness_parser.add_argument("--parent-issue", type=int, required=True)
    parent_closeout_readiness_parser.add_argument(
        "--state-file",
        help="Optional local JSON state file for offline parent closeout readiness checks.",
    )
    parent_child_linkage_preflight_parser = subparsers.add_parser(
        "inspect-parent-child-linkage-preflight",
        help="Inspect parent-child lineage detectability in read-only preflight mode.",
    )
    parent_child_linkage_preflight_parser.add_argument("--parent-issue", type=int, required=True)
    child_evidence_marker_preflight_parser = subparsers.add_parser(
        "inspect-child-evidence-marker-preflight",
        help="Inspect child evidence marker completeness in read-only preflight mode.",
    )
    child_evidence_marker_preflight_parser.add_argument("--parent-issue", type=int, required=True)
    pr_mapping_preflight_parser = subparsers.add_parser(
        "inspect-pr-mapping-preflight",
        help="Inspect child-to-PR mapping and merge evidence in read-only preflight mode.",
    )
    pr_mapping_preflight_parser.add_argument("--parent-issue", type=int, required=True)
    closeout_repair_guidance_parser = subparsers.add_parser(
        "generate-closeout-preflight-repair-guidance",
        help="Generate copy/paste-safe read-only repair guidance from milestone preflight findings.",
    )
    closeout_repair_guidance_parser.add_argument("--parent-issue", type=int, required=True)
    milestone_closeout_preflight_parser = subparsers.add_parser(
        "inspect-milestone-closeout-preflight",
        help="Run read-only milestone closeout preflight orchestration across lineage, evidence, and PR mapping.",
    )
    milestone_closeout_preflight_parser.add_argument("--parent-issue", type=int, required=True)
    readiness_by_construction_parser = subparsers.add_parser(
        "check-closeout-readiness-by-construction",
        help="Validate read-only canonical marker completeness readiness across closeout evidence emission domains.",
    )
    readiness_by_construction_parser.add_argument("--parent-issue", type=int, required=True)
    readiness_by_construction_parser.add_argument(
        "--state-file",
        help="Optional local JSON state file for offline closeout-readiness-by-construction checks.",
    )
    offline_state_template_parser = subparsers.add_parser(
        "generate-offline-closeout-state-template",
        help="Generate a local-only editable offline closeout state-file template.",
    )
    offline_state_template_parser.add_argument("--parent-issue", type=int, required=True)
    offline_state_template_parser.add_argument(
        "--children",
        required=True,
        help="Comma-separated child issue numbers (example: 422,423,424).",
    )
    offline_state_template_parser.add_argument("--output", required=True)
    offline_state_template_parser.add_argument("--parent-title")
    offline_state_template_parser.add_argument("--milestone-title")
    offline_state_template_parser.add_argument("--final-main-head")
    offline_state_template_parser.add_argument("--final-validation-results")
    offline_state_template_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing output file.",
    )
    handoff_package_parser = subparsers.add_parser(
        "generate-handoff-package",
        help="Generate a local-only handoff package from repo state and source-of-truth docs.",
    )
    handoff_package_parser.add_argument("--output")
    handoff_package_parser.add_argument(
        "--format",
        choices=["markdown", "json"],
        default="markdown",
        help="Output format for file writes or stdout rendering.",
    )
    handoff_package_parser.add_argument(
        "--include-doc-excerpts",
        action="store_true",
        help="Include short excerpts from source-of-truth docs.",
    )
    handoff_package_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing output file.",
    )
    safe_dispatch_handoff_parser = subparsers.add_parser(
        "generate-safe-dispatch-handoff",
        help="Generate a local-only safe dispatch handoff package from queue, dispatch, artifact, and approval state.",
    )
    safe_dispatch_handoff_parser.add_argument("--project-id", default="aresforge")
    safe_dispatch_handoff_parser.add_argument("--queue-path")
    safe_dispatch_handoff_parser.add_argument("--registry-path")
    safe_dispatch_handoff_parser.add_argument("--artifact-root")
    safe_dispatch_handoff_parser.add_argument("--approval-path")
    safe_dispatch_handoff_parser.add_argument("--output")
    safe_dispatch_handoff_parser.add_argument("--force", action="store_true")
    safe_dispatch_handoff_parser.add_argument(
        "--format",
        choices=["markdown", "json"],
        default="markdown",
        help="Output format for file writes or stdout rendering.",
    )
    doc_reconciliation_parser = subparsers.add_parser(
        "plan-doc-reconciliation",
        help="Generate a local-only, plan-only documentation reconciliation plan.",
    )
    doc_reconciliation_parser.add_argument("--output")
    doc_reconciliation_parser.add_argument(
        "--format",
        choices=["markdown", "json"],
        default="markdown",
        help="Output format for file writes or stdout rendering.",
    )
    doc_reconciliation_parser.add_argument(
        "--include-git-state",
        action="store_true",
        help="Collect local git state using the approved command subset.",
    )
    doc_reconciliation_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing output file.",
    )
    github_sync_plan_parser = subparsers.add_parser(
        "plan-github-sync",
        help="Generate a local-only, plan-only offline-to-GitHub sync plan.",
    )
    github_sync_plan_parser.add_argument(
        "--state-file",
        help="Optional offline closeout state file path.",
    )
    github_sync_plan_parser.add_argument(
        "--project-state",
        help="Optional project state file path (defaults to .aresforge/state/project_state.json).",
    )
    github_sync_plan_parser.add_argument("--output")
    github_sync_plan_parser.add_argument(
        "--format",
        choices=["markdown", "json"],
        default="markdown",
        help="Output format for file writes or stdout rendering.",
    )
    github_sync_plan_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing output file.",
    )
    github_issue_sync_plan_parser = subparsers.add_parser(
        "plan-github-issue-sync",
        help="Generate a local-only GitHub issue sync plan from queue items.",
    )
    github_issue_sync_plan_parser.add_argument("--project-id", default="aresforge")
    github_issue_sync_plan_parser.add_argument(
        "--item-id",
        default="m162-github-issue-sync-plan-from-queue-items",
    )
    github_issue_sync_plan_parser.add_argument("--queue-path")
    github_issue_sync_plan_parser.add_argument("--output")
    github_issue_sync_plan_parser.add_argument("--force", action="store_true")
    github_issue_sync_plan_parser.add_argument(
        "--format",
        choices=["json"],
        default="json",
        help="Output format for file writes or stdout rendering.",
    )
    github_issue_creation_parser = subparsers.add_parser(
        "create-github-issue-for-safe-queue-item",
        help="Create one GitHub issue for a safe queue item only when explicit gates pass; dry-run by default.",
    )
    github_issue_creation_parser.add_argument("--item-id", required=True)
    github_issue_creation_parser.add_argument("--project-id", default="aresforge")
    github_issue_creation_parser.add_argument("--queue-path")
    github_issue_creation_parser.add_argument("--dry-run", action="store_true")
    github_issue_creation_parser.add_argument("--github-enabled", action="store_true")
    github_issue_creation_parser.add_argument("--autonomy-profile", default="github_sync_dry_run")
    github_issue_creation_parser.add_argument("--repo")
    github_issue_creation_parser.add_argument("--output")
    github_issue_creation_parser.add_argument("--force", action="store_true")
    github_issue_creation_parser.add_argument(
        "--format",
        choices=["json"],
        default="json",
        help="Output format for file writes or stdout rendering.",
    )
    local_milestone_template_parser = subparsers.add_parser(
        "generate-local-milestone-template",
        help="Generate a local milestone definition template file.",
    )
    local_milestone_template_parser.add_argument("--milestone-id", required=True)
    local_milestone_template_parser.add_argument("--output", required=True)
    local_milestone_template_parser.add_argument("--title")
    local_milestone_template_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing output file.",
    )
    inspect_local_milestone_parser = subparsers.add_parser(
        "inspect-local-milestone",
        help="Inspect one local milestone definition file.",
    )
    inspect_local_milestone_parser.add_argument("--definition", required=True)
    inspect_local_milestone_parser.add_argument(
        "--format",
        choices=["markdown", "json"],
        default="markdown",
    )
    check_local_milestone_readiness_parser = subparsers.add_parser(
        "check-local-milestone-readiness",
        help="Run local-only readiness checks for a milestone definition file.",
    )
    check_local_milestone_readiness_parser.add_argument("--definition", required=True)
    check_local_milestone_readiness_parser.add_argument("--project-state")
    check_local_milestone_readiness_parser.add_argument(
        "--format",
        choices=["markdown", "json"],
        default="markdown",
    )
    generate_local_milestone_closeout_parser = subparsers.add_parser(
        "generate-local-milestone-closeout",
        help="Generate a local-only milestone closeout package from a definition file.",
    )
    generate_local_milestone_closeout_parser.add_argument("--definition", required=True)
    generate_local_milestone_closeout_parser.add_argument("--output", required=True)
    generate_local_milestone_closeout_parser.add_argument(
        "--format",
        choices=["markdown", "json"],
        default="markdown",
    )
    generate_local_milestone_closeout_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing output file.",
    )
    init_project_state_parser = subparsers.add_parser(
        "init-project-state",
        help="Initialize local project state ledger under .aresforge/state.",
    )
    init_project_state_parser.add_argument("--path")
    init_project_state_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing project state file.",
    )
    inspect_project_state_parser = subparsers.add_parser(
        "inspect-project-state",
        help="Inspect local project state ledger JSON.",
    )
    inspect_project_state_parser.add_argument("--path")
    update_project_state_parser = subparsers.add_parser(
        "update-project-state",
        help="Update selected fields in local project state ledger JSON.",
    )
    update_project_state_parser.add_argument("--path")
    update_project_state_parser.add_argument("--current-milestone")
    update_project_state_parser.add_argument("--current-phase")
    update_project_state_parser.add_argument("--current-mode")
    update_project_state_parser.add_argument("--validation-status")
    update_project_state_parser.add_argument("--documentation-status")
    update_project_state_parser.add_argument("--warning", action="append", default=[])
    append_operation_log_parser = subparsers.add_parser(
        "append-operation-log",
        help="Append one local operation event to .aresforge/state/operation_log.jsonl.",
    )
    append_operation_log_parser.add_argument("--state-path")
    append_operation_log_parser.add_argument("--event-type", required=True)
    append_operation_log_parser.add_argument("--summary", required=True)
    append_operation_log_parser.add_argument(
        "--details",
        help="Optional JSON object string for structured event details.",
    )
    inspect_operation_log_parser = subparsers.add_parser(
        "inspect-operation-log",
        help="Inspect local operation log JSONL entries.",
    )
    inspect_operation_log_parser.add_argument("--state-path")
    inspect_operation_log_parser.add_argument("--limit", type=int)
    init_managed_project_registry_parser = subparsers.add_parser(
        "init-managed-project-registry",
        help="Initialize local managed-project registry under .aresforge/projects.",
    )
    init_managed_project_registry_parser.add_argument("--path")
    init_managed_project_registry_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing managed-project registry file.",
    )
    register_managed_project_parser = subparsers.add_parser(
        "register-managed-project",
        help="Register or update one managed project in local managed-project registry.",
    )
    register_managed_project_parser.add_argument("--project-id", required=True)
    register_managed_project_parser.add_argument("--name", required=True)
    register_managed_project_parser.add_argument("--root-path", required=True)
    register_managed_project_parser.add_argument("--registry-path")
    register_managed_project_parser.add_argument("--description")
    register_managed_project_parser.add_argument("--status", choices=list(PROJECT_STATUSES))
    register_managed_project_parser.add_argument("--default-branch")
    register_managed_project_parser.add_argument("--github-url")
    register_managed_project_parser.add_argument("--github-owner")
    register_managed_project_parser.add_argument("--github-repo")
    register_managed_project_parser.add_argument("--github-default-branch")
    register_managed_project_parser.add_argument("--primary-repo-id")
    register_managed_project_parser.add_argument("--tag", action="append", default=[])
    register_managed_project_parser.add_argument("--notes")
    register_managed_repo_parser = subparsers.add_parser(
        "register-managed-repo",
        help="Register or update one repo under a managed project in local managed-project registry.",
    )
    register_managed_repo_parser.add_argument("--project-id", required=True)
    register_managed_repo_parser.add_argument("--repo-id", required=True)
    register_managed_repo_parser.add_argument("--name", required=True)
    register_managed_repo_parser.add_argument("--path", required=True)
    register_managed_repo_parser.add_argument("--registry-path")
    register_managed_repo_parser.add_argument("--remote-url")
    register_managed_repo_parser.add_argument("--default-branch")
    register_managed_repo_parser.add_argument("--github-url")
    register_managed_repo_parser.add_argument("--github-owner")
    register_managed_repo_parser.add_argument("--github-repo")
    register_managed_repo_parser.add_argument("--github-default-branch")
    register_managed_repo_parser.add_argument("--inspect-local-git", action="store_true")
    register_managed_repo_parser.add_argument("--role", choices=list(REPO_ROLES))
    register_managed_repo_parser.add_argument("--status", choices=list(REPO_STATUSES))
    register_managed_repo_parser.add_argument("--tag", action="append", default=[])
    register_managed_repo_parser.add_argument("--notes")
    inspect_managed_project_registry_parser = subparsers.add_parser(
        "inspect-managed-project-registry",
        help="Inspect local managed-project registry.",
    )
    inspect_managed_project_registry_parser.add_argument("--registry-path")
    inspect_managed_project_registry_parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="json",
    )
    inspect_managed_project_parser = subparsers.add_parser(
        "inspect-managed-project",
        help="Inspect one managed project from local managed-project registry.",
    )
    inspect_managed_project_parser.add_argument("--project-id", required=True)
    inspect_managed_project_parser.add_argument("--registry-path")
    inspect_managed_project_parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="json",
    )
    inspect_managed_repo_parser = subparsers.add_parser(
        "inspect-managed-repo",
        help="Inspect one managed repo from local managed-project registry.",
    )
    inspect_managed_repo_parser.add_argument("--project-id", required=True)
    inspect_managed_repo_parser.add_argument("--repo-id", required=True)
    inspect_managed_repo_parser.add_argument("--registry-path")
    inspect_managed_repo_parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="json",
    )
    inspect_managed_repo_github_link_parser = subparsers.add_parser(
        "inspect-managed-repo-github-link",
        help="Inspect one managed repo GitHub-link posture with optional local git inspection.",
    )
    inspect_managed_repo_github_link_parser.add_argument("--project-id", required=True)
    inspect_managed_repo_github_link_parser.add_argument("--repo-id", required=True)
    inspect_managed_repo_github_link_parser.add_argument("--registry-path")
    inspect_managed_repo_github_link_parser.add_argument("--inspect-local-git", action="store_true")
    inspect_managed_repo_github_link_parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="json",
    )
    seed_aresforge_self_project_parser = subparsers.add_parser(
        "seed-aresforge-self-project",
        help="Idempotently seed AresForge as its own local managed project and queue next milestones.",
    )
    seed_aresforge_self_project_parser.add_argument("--project-id", default="aresforge")
    seed_aresforge_self_project_parser.add_argument("--repo-id", default="aresforge-main")
    seed_aresforge_self_project_parser.add_argument("--root-path")
    seed_aresforge_self_project_parser.add_argument("--queue-path")
    seed_aresforge_self_project_parser.add_argument("--registry-path")
    seed_aresforge_self_project_parser.add_argument("--set-active", action="store_true")
    seed_aresforge_self_project_parser.add_argument(
        "--seed-next-milestones",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    seed_aresforge_self_project_parser.add_argument("--force-update", action="store_true")
    seed_aresforge_self_project_parser.add_argument(
        "--format",
        choices=["json"],
        default="json",
    )
    init_project_queue_parser = subparsers.add_parser(
        "init-project-queue",
        help="Initialize local project queue under .aresforge/queue.",
    )
    init_project_queue_parser.add_argument("--path")
    init_project_queue_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing project queue file.",
    )
    add_queue_item_parser = subparsers.add_parser(
        "add-queue-item",
        help="Add or update one local project queue item by item_id.",
    )
    add_queue_item_parser.add_argument("--item-id", required=True)
    add_queue_item_parser.add_argument("--project-id", required=True)
    add_queue_item_parser.add_argument("--repo-id", required=True)
    add_queue_item_parser.add_argument("--title", required=True)
    add_queue_item_parser.add_argument("--queue-path")
    add_queue_item_parser.add_argument("--registry-path")
    add_queue_item_parser.add_argument("--description")
    add_queue_item_parser.add_argument("--status", choices=list(QUEUE_STATUSES))
    add_queue_item_parser.add_argument("--priority", choices=list(QUEUE_PRIORITIES))
    add_queue_item_parser.add_argument("--type", choices=list(QUEUE_ITEM_TYPES))
    add_queue_item_parser.add_argument("--tag", action="append", default=[])
    add_queue_item_parser.add_argument("--depends-on", action="append", default=[])
    add_queue_item_parser.add_argument("--blocked-by", action="append", default=[])
    add_queue_item_parser.add_argument("--assigned-agent")
    add_queue_item_parser.add_argument("--source")
    add_queue_item_parser.add_argument("--notes")
    add_local_queue_item_parser = subparsers.add_parser(
        "add-local-queue-item",
        help="Add one local queue item using active-project and primary-repo defaults.",
    )
    add_local_queue_item_parser.add_argument("--title", required=True)
    add_local_queue_item_parser.add_argument("--description")
    add_local_queue_item_parser.add_argument("--project-id")
    add_local_queue_item_parser.add_argument("--repo-id")
    add_local_queue_item_parser.add_argument("--queue-path")
    add_local_queue_item_parser.add_argument("--registry-path")
    add_local_queue_item_parser.add_argument("--priority", choices=list(QUEUE_PRIORITIES))
    add_local_queue_item_parser.add_argument("--type", choices=list(QUEUE_ITEM_TYPES))
    add_local_queue_item_parser.add_argument("--assigned-agent")
    add_local_queue_item_parser.add_argument("--target-area")
    add_local_queue_item_parser.add_argument("--acceptance-criteria", action="append", default=[])
    add_local_queue_item_parser.add_argument("--depends-on", action="append", default=[])
    add_local_queue_item_parser.add_argument("--tags", action="append", default=[])
    update_queue_item_parser = subparsers.add_parser(
        "update-queue-item",
        help="Update selected fields for one local project queue item.",
    )
    update_queue_item_parser.add_argument("--item-id", required=True)
    update_queue_item_parser.add_argument("--queue-path")
    update_queue_item_parser.add_argument("--project-id")
    update_queue_item_parser.add_argument("--repo-id")
    update_queue_item_parser.add_argument("--status", choices=list(QUEUE_STATUSES))
    update_queue_item_parser.add_argument("--priority", choices=list(QUEUE_PRIORITIES))
    update_queue_item_parser.add_argument("--type", choices=list(QUEUE_ITEM_TYPES))
    update_queue_item_parser.add_argument("--title")
    update_queue_item_parser.add_argument("--description")
    update_queue_item_parser.add_argument("--tag", action="append")
    update_queue_item_parser.add_argument("--depends-on", action="append")
    update_queue_item_parser.add_argument("--blocked-by", action="append")
    update_queue_item_parser.add_argument("--assigned-agent")
    update_queue_item_parser.add_argument("--source")
    update_queue_item_parser.add_argument("--notes")
    inspect_project_queue_parser = subparsers.add_parser(
        "inspect-project-queue",
        help="Inspect local project queue with optional filtering.",
    )
    inspect_project_queue_parser.add_argument("--queue-path")
    inspect_project_queue_parser.add_argument("--project-id")
    inspect_project_queue_parser.add_argument("--repo-id")
    inspect_project_queue_parser.add_argument("--status", choices=list(QUEUE_STATUSES))
    inspect_project_queue_parser.add_argument("--type", choices=list(QUEUE_ITEM_TYPES))
    inspect_project_queue_parser.add_argument("--assigned-agent")
    inspect_project_queue_parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="json",
    )
    inspect_queue_consistency_parser = subparsers.add_parser(
        "inspect-queue-consistency",
        help="Inspect local queue dependency and completion locks without mutating the queue.",
    )
    inspect_queue_consistency_parser.add_argument("--queue-path")
    inspect_queue_consistency_parser.add_argument("--project-id")
    inspect_queue_consistency_parser.add_argument("--repo-id")
    inspect_queue_consistency_parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="json",
    )
    inspect_queue_item_parser = subparsers.add_parser(
        "inspect-queue-item",
        help="Inspect one local project queue item by item_id.",
    )
    inspect_queue_item_parser.add_argument("--item-id", required=True)
    inspect_queue_item_parser.add_argument("--queue-path")
    inspect_queue_item_parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="json",
    )
    inspect_local_queue_item_readiness_parser = subparsers.add_parser(
        "inspect-local-queue-item-readiness",
        help="Inspect whether one local queue item is ready to start.",
    )
    inspect_local_queue_item_readiness_parser.add_argument("--item-id", required=True)
    inspect_local_queue_item_readiness_parser.add_argument("--queue-path")
    inspect_local_queue_item_readiness_parser.add_argument("--registry-path")
    start_local_queue_item_parser = subparsers.add_parser(
        "start-local-queue-item",
        help="Start one local queue item when local readiness gates pass.",
    )
    start_local_queue_item_parser.add_argument("--item-id", required=True)
    start_local_queue_item_parser.add_argument("--queue-path")
    start_local_queue_item_parser.add_argument("--registry-path")
    complete_local_queue_item_parser = subparsers.add_parser(
        "complete-local-queue-item",
        help="Complete one local queue item with validation evidence.",
    )
    complete_local_queue_item_parser.add_argument("--item-id", required=True)
    complete_local_queue_item_parser.add_argument("--commit-hash", required=True)
    complete_local_queue_item_parser.add_argument("--validation-summary", required=True)
    complete_local_queue_item_parser.add_argument("--evidence-note")
    complete_local_queue_item_parser.add_argument("--tests-run", action="append", default=[])
    complete_local_queue_item_parser.add_argument("--changed-files", action="append", default=[])
    complete_local_queue_item_parser.add_argument("--artifact-path", action="append", default=[])
    complete_local_queue_item_parser.add_argument("--completed-by", default="local_operator")
    complete_local_queue_item_parser.add_argument("--queue-path")
    generate_local_queue_item_codex_prompt_parser = subparsers.add_parser(
        "generate-local-queue-item-codex-prompt",
        help="Generate a local-only Codex implementation prompt for one queue item.",
    )
    generate_local_queue_item_codex_prompt_parser.add_argument("--item-id", required=True)
    generate_local_queue_item_codex_prompt_parser.add_argument("--queue-path")
    generate_local_queue_item_codex_prompt_parser.add_argument("--registry-path")
    generate_local_queue_item_codex_prompt_parser.add_argument("--output")
    generate_local_queue_item_codex_prompt_parser.add_argument("--commit-message")
    generate_local_queue_item_codex_prompt_parser.add_argument("--force", action="store_true")
    inspect_codex_dispatch_contract_parser = subparsers.add_parser(
        "inspect-codex-dispatch-contract",
        help="Inspect the M77 local-only Codex CLI dispatch contract for one queue item.",
    )
    inspect_codex_dispatch_contract_parser.add_argument("--item-id", required=True)
    inspect_codex_dispatch_contract_parser.add_argument("--queue-path")
    inspect_codex_dispatch_contract_parser.add_argument("--registry-path")
    inspect_codex_dispatch_contract_parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="json",
    )
    prepare_codex_dispatch_dry_run_parser = subparsers.add_parser(
        "prepare-codex-dispatch-dry-run",
        help="Prepare a M77 dry-run/no-execute Codex dispatch contract for one queue item.",
    )
    prepare_codex_dispatch_dry_run_parser.add_argument("--item-id", required=True)
    prepare_codex_dispatch_dry_run_parser.add_argument("--queue-path")
    prepare_codex_dispatch_dry_run_parser.add_argument("--registry-path")
    prepare_codex_dispatch_dry_run_parser.add_argument("--output")
    prepare_codex_dispatch_dry_run_parser.add_argument("--force", action="store_true")
    prepare_codex_dispatch_dry_run_parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="json",
    )
    prepare_queue_item_dispatch_parser = subparsers.add_parser(
        "prepare-queue-item-dispatch",
        help="Prepare one queue item for operator-reviewed dispatch without executing or approving it.",
    )
    prepare_queue_item_dispatch_parser.add_argument("--item-id", required=True)
    prepare_queue_item_dispatch_parser.add_argument(
        "--target",
        choices=["codex", "local-llm", "manual"],
        default="codex",
    )
    prepare_queue_item_dispatch_parser.add_argument("--queue-path")
    prepare_queue_item_dispatch_parser.add_argument("--registry-path")
    prepare_queue_item_dispatch_parser.add_argument("--output")
    prepare_queue_item_dispatch_parser.add_argument("--start-if-ready", action="store_true")
    prepare_queue_item_dispatch_parser.add_argument("--force", action="store_true")
    prepare_queue_item_dispatch_parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="json",
    )
    inspect_queue_dispatch_plan_parser = subparsers.add_parser(
        "inspect-queue-dispatch-plan",
        help="Inspect the M97 local-only queue-to-agent advisory dispatch plan for one queue item.",
    )
    inspect_queue_dispatch_plan_parser.add_argument("--item-id", required=True)
    inspect_queue_dispatch_plan_parser.add_argument("--queue-path")
    inspect_queue_dispatch_plan_parser.add_argument("--registry-path")
    inspect_queue_dispatch_plan_parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="markdown",
    )
    generate_codex_dispatch_artifact_parser = subparsers.add_parser(
        "generate-codex-dispatch-artifact",
        help="Generate a local-only manual Codex prompt artifact from an M97 dispatch plan.",
    )
    generate_codex_dispatch_artifact_parser.add_argument("--item-id", required=True)
    generate_codex_dispatch_artifact_parser.add_argument("--queue-path")
    generate_codex_dispatch_artifact_parser.add_argument("--registry-path")
    generate_codex_dispatch_artifact_parser.add_argument("--output")
    generate_codex_dispatch_artifact_parser.add_argument("--force", action="store_true")
    generate_codex_dispatch_artifact_parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="markdown",
    )
    validate_local_llm_advisory_dry_run_parser = subparsers.add_parser(
        "validate-local-llm-advisory-dry-run",
        help="Validate local-only dry-run readiness for the M97 local_llm_advisory lane.",
    )
    validate_local_llm_advisory_dry_run_parser.add_argument("--item-id", required=True)
    validate_local_llm_advisory_dry_run_parser.add_argument("--queue-path")
    validate_local_llm_advisory_dry_run_parser.add_argument("--registry-path")
    validate_local_llm_advisory_dry_run_parser.add_argument("--output")
    validate_local_llm_advisory_dry_run_parser.add_argument("--force", action="store_true")
    validate_local_llm_advisory_dry_run_parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="markdown",
    )
    generate_local_llm_advisory_artifact_parser = subparsers.add_parser(
        "generate-local-llm-advisory-artifact",
        help="Generate a local-only Local LLM advisory request artifact from an M97 dispatch plan.",
    )
    generate_local_llm_advisory_artifact_parser.add_argument("--item-id", required=True)
    generate_local_llm_advisory_artifact_parser.add_argument("--queue-path")
    generate_local_llm_advisory_artifact_parser.add_argument("--registry-path")
    generate_local_llm_advisory_artifact_parser.add_argument("--output")
    generate_local_llm_advisory_artifact_parser.add_argument("--force", action="store_true")
    generate_local_llm_advisory_artifact_parser.add_argument("--model-profile")
    generate_local_llm_advisory_artifact_parser.add_argument("--reasoning-scope")
    generate_local_llm_advisory_artifact_parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="markdown",
    )
    run_local_llm_advisory_parser = subparsers.add_parser(
        "run-local-llm-advisory",
        help="Run one machine-gated local LLM advisory request against a local provider without applying output.",
    )
    run_local_llm_advisory_parser.add_argument("--item-id", required=True)
    run_local_llm_advisory_parser.add_argument("--artifact-path", required=True)
    run_local_llm_advisory_parser.add_argument("--provider", default="ollama")
    run_local_llm_advisory_parser.add_argument("--model")
    run_local_llm_advisory_parser.add_argument("--queue-path")
    run_local_llm_advisory_parser.add_argument("--dry-run", action="store_true")
    run_local_llm_advisory_parser.add_argument("--output")
    run_local_llm_advisory_parser.add_argument("--force", action="store_true")
    run_local_llm_advisory_parser.add_argument("--timeout-seconds", type=int)
    run_local_llm_advisory_parser.add_argument(
        "--format",
        choices=["json"],
        default="json",
    )
    validate_documentation_agent_dry_run_parser = subparsers.add_parser(
        "validate-documentation-agent-dry-run",
        help="Validate local-only dry-run readiness for the M97 documentation_agent_dry_run lane.",
    )
    validate_documentation_agent_dry_run_parser.add_argument("--item-id", required=True)
    validate_documentation_agent_dry_run_parser.add_argument("--queue-path")
    validate_documentation_agent_dry_run_parser.add_argument("--registry-path")
    validate_documentation_agent_dry_run_parser.add_argument("--output")
    validate_documentation_agent_dry_run_parser.add_argument("--force", action="store_true")
    validate_documentation_agent_dry_run_parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="markdown",
    )
    generate_doc_agent_patch_proposal_parser = subparsers.add_parser(
        "generate-doc-agent-patch-proposal",
        help="Generate a local-only documentation patch proposal artifact without applying patches.",
    )
    generate_doc_agent_patch_proposal_parser.add_argument("--item-id", required=True)
    generate_doc_agent_patch_proposal_parser.add_argument("--queue-path")
    generate_doc_agent_patch_proposal_parser.add_argument("--output")
    generate_doc_agent_patch_proposal_parser.add_argument("--force", action="store_true")
    generate_doc_agent_patch_proposal_parser.add_argument("--include-roadmap", action="store_true")
    generate_doc_agent_patch_proposal_parser.add_argument("--include-context", action="store_true")
    generate_doc_agent_patch_proposal_parser.add_argument("--include-operator-docs", action="store_true")
    generate_doc_agent_patch_proposal_parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="markdown",
    )
    recommend_agent_route_parser = subparsers.add_parser(
        "recommend-agent-route",
        help="Recommend an advisory agent/executor lane for one queue item without dispatch or execution.",
    )
    recommend_agent_route_parser.add_argument("--item-id", required=True)
    recommend_agent_route_parser.add_argument("--queue-path")
    recommend_agent_route_parser.add_argument("--output")
    recommend_agent_route_parser.add_argument("--force", action="store_true")
    recommend_agent_route_parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="markdown",
    )
    create_dispatch_approval_gate_parser = subparsers.add_parser(
        "create-dispatch-approval-gate",
        help="Create a local-only human approval gate record for a dispatch artifact or dry-run output.",
    )
    create_dispatch_approval_gate_parser.add_argument("--item-id", required=True)
    create_dispatch_approval_gate_parser.add_argument("--artifact-type", required=True)
    create_dispatch_approval_gate_parser.add_argument("--artifact-path")
    create_dispatch_approval_gate_parser.add_argument("--dispatch-lane")
    create_dispatch_approval_gate_parser.add_argument("--reviewer")
    create_dispatch_approval_gate_parser.add_argument("--review-notes")
    create_dispatch_approval_gate_parser.add_argument("--checklist", action="append", default=[])
    create_dispatch_approval_gate_parser.add_argument("--approval-path")
    create_dispatch_approval_gate_parser.add_argument("--queue-path")
    create_dispatch_approval_gate_parser.add_argument("--registry-path")
    create_dispatch_approval_gate_parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="markdown",
    )
    inspect_dispatch_approval_gate_parser = subparsers.add_parser(
        "inspect-dispatch-approval-gate",
        help="Inspect local-only dispatch approval gate records.",
    )
    inspect_dispatch_approval_gate_parser.add_argument("--approval-id")
    inspect_dispatch_approval_gate_parser.add_argument("--item-id")
    inspect_dispatch_approval_gate_parser.add_argument("--approval-path")
    inspect_dispatch_approval_gate_parser.add_argument("--limit", type=int)
    inspect_dispatch_approval_gate_parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="markdown",
    )
    update_dispatch_approval_gate_parser = subparsers.add_parser(
        "update-dispatch-approval-gate",
        help="Update a local-only dispatch approval gate status without authorizing execution.",
    )
    update_dispatch_approval_gate_parser.add_argument("--approval-id", required=True)
    update_dispatch_approval_gate_parser.add_argument("--status", choices=APPROVAL_GATE_STATUSES, required=True)
    update_dispatch_approval_gate_parser.add_argument("--reviewer")
    update_dispatch_approval_gate_parser.add_argument("--review-notes")
    update_dispatch_approval_gate_parser.add_argument("--checklist", action="append", default=[])
    update_dispatch_approval_gate_parser.add_argument("--approval-path")
    update_dispatch_approval_gate_parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="markdown",
    )
    inspect_dispatch_artifacts_parser = subparsers.add_parser(
        "inspect-dispatch-artifacts",
        help="Inspect local-only dispatch artifacts and approval gate status without execution.",
    )
    inspect_dispatch_artifacts_parser.add_argument("--project-id", default="aresforge")
    inspect_dispatch_artifacts_parser.add_argument("--artifact-root")
    inspect_dispatch_artifacts_parser.add_argument("--approval-path")
    inspect_dispatch_artifacts_parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="markdown",
    )
    inspect_artifact_registry_parser = subparsers.add_parser(
        "inspect-artifact-registry",
        help="Inspect the local dispatch artifact registry v2 without execution.",
    )
    inspect_artifact_registry_parser.add_argument("--project-id", default="aresforge")
    inspect_artifact_registry_parser.add_argument("--item-id")
    inspect_artifact_registry_parser.add_argument("--artifact-type")
    inspect_artifact_registry_parser.add_argument("--output")
    inspect_artifact_registry_parser.add_argument("--force", action="store_true")
    inspect_artifact_registry_parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="json",
    )
    inspect_approval_ledger_parser = subparsers.add_parser(
        "inspect-approval-ledger",
        help="Inspect the local human approval review ledger for artifacts and queue items.",
    )
    inspect_approval_ledger_parser.add_argument("--project-id", required=True)
    inspect_approval_ledger_parser.add_argument("--item-id")
    inspect_approval_ledger_parser.add_argument("--artifact-path")
    inspect_approval_ledger_parser.add_argument("--output")
    inspect_approval_ledger_parser.add_argument("--force", action="store_true")
    inspect_approval_ledger_parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="markdown",
    )
    inspect_queue_transaction_log_parser = subparsers.add_parser(
        "inspect-queue-transaction-log",
        help="Inspect the local queue mutation transaction log without mutating queue state.",
    )
    inspect_queue_transaction_log_parser.add_argument("--project-id", required=True)
    inspect_queue_transaction_log_parser.add_argument("--item-id")
    inspect_queue_transaction_log_parser.add_argument("--output")
    inspect_queue_transaction_log_parser.add_argument("--force", action="store_true")
    inspect_queue_transaction_log_parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="json",
    )
    record_artifact_review_parser = subparsers.add_parser(
        "record-artifact-review",
        help="Record a local human review decision for one artifact without applying or executing it.",
    )
    record_artifact_review_parser.add_argument("--item-id", required=True)
    record_artifact_review_parser.add_argument("--artifact-path", required=True)
    record_artifact_review_parser.add_argument("--decision", required=True, choices=["approved", "rejected", "needs_changes"])
    record_artifact_review_parser.add_argument("--reviewer")
    record_artifact_review_parser.add_argument("--review-notes")
    record_artifact_review_parser.add_argument("--output")
    record_artifact_review_parser.add_argument("--force", action="store_true")
    record_artifact_review_parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="markdown",
    )
    prepare_manual_codex_dispatch_parser = subparsers.add_parser(
        "prepare-manual-codex-dispatch",
        help="Prepare a local-only manual Codex dispatch run record without executing Codex.",
    )
    prepare_manual_codex_dispatch_parser.add_argument("--item-id", required=True)
    prepare_manual_codex_dispatch_parser.add_argument("--artifact-path")
    prepare_manual_codex_dispatch_parser.add_argument("--approval-id")
    prepare_manual_codex_dispatch_parser.add_argument("--queue-path")
    prepare_manual_codex_dispatch_parser.add_argument("--registry-path")
    prepare_manual_codex_dispatch_parser.add_argument("--artifact-root")
    prepare_manual_codex_dispatch_parser.add_argument("--approval-path")
    prepare_manual_codex_dispatch_parser.add_argument("--output")
    prepare_manual_codex_dispatch_parser.add_argument("--force", action="store_true")
    prepare_manual_codex_dispatch_parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="markdown",
    )
    intake_patch_proposal_parser = subparsers.add_parser(
        "intake-patch-proposal",
        help="Record a local-only approval-gated patch proposal intake without applying patches.",
    )
    intake_patch_proposal_parser.add_argument("--item-id", required=True)
    intake_patch_proposal_parser.add_argument("--patch-artifact", required=True)
    intake_patch_proposal_parser.add_argument("--approval-id")
    intake_patch_proposal_parser.add_argument("--queue-path")
    intake_patch_proposal_parser.add_argument("--approval-path")
    intake_patch_proposal_parser.add_argument("--output")
    intake_patch_proposal_parser.add_argument("--force", action="store_true")
    intake_patch_proposal_parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="markdown",
    )
    parse_dispatch_result_evidence_parser = subparsers.add_parser(
        "parse-dispatch-result-evidence",
        help="Parse a local human-pasted Codex result file into structured evidence without execution.",
    )
    parse_dispatch_result_evidence_parser.add_argument("--item-id", required=True)
    parse_dispatch_result_evidence_parser.add_argument("--result-path", required=True)
    parse_dispatch_result_evidence_parser.add_argument("--queue-path")
    parse_dispatch_result_evidence_parser.add_argument("--output")
    parse_dispatch_result_evidence_parser.add_argument("--force", action="store_true")
    parse_dispatch_result_evidence_parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="markdown",
    )
    recommend_queue_completion_parser = subparsers.add_parser(
        "recommend-queue-completion",
        help="Recommend whether an operator may complete a queue item from local dispatch evidence without mutating the queue.",
    )
    recommend_queue_completion_parser.add_argument("--item-id", required=True)
    recommend_queue_completion_parser.add_argument("--evidence-path", required=True)
    recommend_queue_completion_parser.add_argument("--queue-path")
    recommend_queue_completion_parser.add_argument("--output")
    recommend_queue_completion_parser.add_argument("--force", action="store_true")
    recommend_queue_completion_parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="markdown",
    )
    inspect_agent_runtime_boundary_parser = subparsers.add_parser(
        "inspect-agent-runtime-boundary",
        help="Inspect the M125 local-only agent runtime boundary contract without executing agents.",
    )
    inspect_agent_runtime_boundary_parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="json",
    )
    inspect_agent_registry_parser = subparsers.add_parser(
        "inspect-agent-registry",
        help="Inspect the M126 local-only declarative agent registry without executing agents.",
    )
    inspect_agent_registry_parser.add_argument("--agent-id")
    inspect_agent_registry_parser.add_argument("--safety-class")
    inspect_agent_registry_parser.add_argument("--autonomy-level")
    inspect_agent_registry_parser.add_argument("--output")
    inspect_agent_registry_parser.add_argument("--force", action="store_true")
    inspect_agent_registry_parser.add_argument(
        "--format",
        choices=["json"],
        default="json",
    )
    recommend_llm_decision_parser = subparsers.add_parser(
        "recommend-llm-decision",
        help="Recommend an LLM/provider/lane decision for one queue item without executing anything.",
    )
    recommend_llm_decision_parser.add_argument("--item-id", required=True)
    recommend_llm_decision_parser.add_argument("--agent-id")
    recommend_llm_decision_parser.add_argument("--task-type")
    recommend_llm_decision_parser.add_argument("--risk-level")
    recommend_llm_decision_parser.add_argument("--mutation-scope")
    recommend_llm_decision_parser.add_argument("--queue-path")
    recommend_llm_decision_parser.add_argument("--output")
    recommend_llm_decision_parser.add_argument("--force", action="store_true")
    recommend_llm_decision_parser.add_argument(
        "--format",
        choices=["json"],
        default="json",
    )
    build_agent_orchestration_plan_parser = subparsers.add_parser(
        "build-agent-orchestration-plan",
        help="Build an M128 non-executing agent orchestration plan for one queue item.",
    )
    build_agent_orchestration_plan_parser.add_argument("--item-id", required=True)
    build_agent_orchestration_plan_parser.add_argument("--agent-id")
    build_agent_orchestration_plan_parser.add_argument(
        "--execution-target",
        choices=["dry-run", "real"],
        default="dry-run",
    )
    build_agent_orchestration_plan_parser.add_argument("--queue-path")
    build_agent_orchestration_plan_parser.add_argument("--output")
    build_agent_orchestration_plan_parser.add_argument("--force", action="store_true")
    build_agent_orchestration_plan_parser.add_argument(
        "--format",
        choices=["json"],
        default="json",
    )
    run_agent_dry_run_parser = subparsers.add_parser(
        "run-agent-dry-run",
        help="Run one deterministic local AresForge agent in dry-run mode only.",
    )
    run_agent_dry_run_parser.add_argument("--agent-id", required=True)
    run_agent_dry_run_parser.add_argument("--item-id", required=True)
    run_agent_dry_run_parser.add_argument("--plan-path")
    run_agent_dry_run_parser.add_argument("--queue-path")
    run_agent_dry_run_parser.add_argument("--output")
    run_agent_dry_run_parser.add_argument("--force", action="store_true")
    run_agent_dry_run_parser.add_argument(
        "--format",
        choices=["json"],
        default="json",
    )
    run_agent_parser = subparsers.add_parser(
        "run-agent",
        help="Run one deterministic low-risk local AresForge agent with M130 real execution gates.",
    )
    run_agent_parser.add_argument("--agent-id", required=True)
    run_agent_parser.add_argument("--item-id", required=True)
    run_agent_parser.add_argument("--queue-path")
    run_agent_parser.add_argument("--output")
    run_agent_parser.add_argument("--force", action="store_true")
    run_agent_parser.add_argument("--require-machine-gates", action="store_true")
    run_agent_parser.add_argument(
        "--format",
        choices=["json"],
        default="json",
    )
    evaluate_machine_safety_gates_parser = subparsers.add_parser(
        "evaluate-machine-safety-gates",
        help="Evaluate M131 machine safety gates for one queue item without execution or mutation.",
    )
    evaluate_machine_safety_gates_parser.add_argument("--item-id", required=True)
    evaluate_machine_safety_gates_parser.add_argument("--gate-profile", default="read_only_agent")
    evaluate_machine_safety_gates_parser.add_argument("--artifact-path")
    evaluate_machine_safety_gates_parser.add_argument("--patch-path")
    evaluate_machine_safety_gates_parser.add_argument("--execution-record")
    evaluate_machine_safety_gates_parser.add_argument("--queue-path")
    evaluate_machine_safety_gates_parser.add_argument("--output")
    evaluate_machine_safety_gates_parser.add_argument("--force", action="store_true")
    evaluate_machine_safety_gates_parser.add_argument(
        "--format",
        choices=["json"],
        default="json",
    )
    auto_complete_safe_queue_item_parser = subparsers.add_parser(
        "auto-complete-safe-queue-item",
        help="Auto-complete one safe queue item only when deterministic evidence and machine gates pass.",
    )
    auto_complete_safe_queue_item_parser.add_argument("--item-id", required=True)
    auto_complete_safe_queue_item_parser.add_argument("--evidence-path")
    auto_complete_safe_queue_item_parser.add_argument("--gate-profile", default="queue_status_mutation")
    auto_complete_safe_queue_item_parser.add_argument("--queue-path")
    auto_complete_safe_queue_item_parser.add_argument("--dry-run", action="store_true")
    auto_complete_safe_queue_item_parser.add_argument("--force", action="store_true")
    auto_complete_safe_queue_item_parser.add_argument("--output")
    auto_complete_safe_queue_item_parser.add_argument(
        "--format",
        choices=["json"],
        default="json",
    )
    apply_docs_only_patch_parser = subparsers.add_parser(
        "apply-docs-only-patch",
        help="Apply one machine-gated docs-only Markdown patch with local transaction logging.",
    )
    apply_docs_only_patch_parser.add_argument("--item-id", required=True)
    apply_docs_only_patch_parser.add_argument("--patch-path", required=True)
    apply_docs_only_patch_parser.add_argument("--queue-path")
    apply_docs_only_patch_parser.add_argument("--dry-run", action="store_true")
    apply_docs_only_patch_parser.add_argument("--force", action="store_true")
    apply_docs_only_patch_parser.add_argument("--output")
    apply_docs_only_patch_parser.add_argument(
        "--format",
        choices=["json"],
        default="json",
    )
    probe_local_ollama_provider_parser = subparsers.add_parser(
        "probe-local-ollama-provider",
        help="Probe local Ollama provider configuration and loopback model metadata without prompt execution.",
    )
    probe_local_ollama_provider_parser.add_argument("--output")
    probe_local_ollama_provider_parser.add_argument("--force", action="store_true")
    probe_local_ollama_provider_parser.add_argument("--no-network", action="store_true")
    probe_local_ollama_provider_parser.add_argument("--config")
    probe_local_ollama_provider_parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="markdown",
    )
    inspect_llm_decision_matrix_parser = subparsers.add_parser(
        "inspect-llm-decision-matrix",
        help="Inspect the M80 advisory LLM decision matrix for one queue item without executing models.",
    )
    inspect_llm_decision_matrix_parser.add_argument("--item-id", required=True)
    inspect_llm_decision_matrix_parser.add_argument("--queue-path")
    inspect_llm_decision_matrix_parser.add_argument("--registry-path")
    inspect_llm_decision_matrix_parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="json",
    )
    inspect_local_llm_advisory_lane_parser = subparsers.add_parser(
        "inspect-local-llm-advisory-lane-readiness",
        help="Inspect M81 local LLM advisory/coding lane readiness without invoking a provider.",
    )
    inspect_local_llm_advisory_lane_parser.add_argument("--item-id", required=True)
    inspect_local_llm_advisory_lane_parser.add_argument("--queue-path")
    inspect_local_llm_advisory_lane_parser.add_argument("--registry-path")
    inspect_local_llm_advisory_lane_parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="json",
    )
    inspect_local_llm_provider_contract_parser = subparsers.add_parser(
        "inspect-local-llm-provider-contract",
        help="Inspect the M83 local LLM provider contract without invoking a provider.",
    )
    inspect_local_llm_provider_contract_parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="json",
    )
    prepare_local_llm_advisory_run_parser = subparsers.add_parser(
        "prepare-local-llm-advisory-run",
        help="Generate a local LLM advisory prompt artifact and optionally run explicit local advisory output.",
    )
    prepare_local_llm_advisory_run_parser.add_argument("--item-id", required=True)
    prepare_local_llm_advisory_run_parser.add_argument("--queue-path")
    prepare_local_llm_advisory_run_parser.add_argument("--registry-path")
    prepare_local_llm_advisory_run_parser.add_argument("--model")
    prepare_local_llm_advisory_run_parser.add_argument("--run-id")
    prepare_local_llm_advisory_run_parser.add_argument("--run", action="store_true")
    prepare_local_llm_advisory_run_parser.add_argument("--force", action="store_true")
    prepare_local_llm_advisory_run_parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="json",
    )
    prepare_local_coding_draft_parser = subparsers.add_parser(
        "prepare-local-coding-draft",
        help="Generate a local coding draft prompt artifact and optionally run explicit draft output.",
    )
    prepare_local_coding_draft_parser.add_argument("--item-id", required=True)
    prepare_local_coding_draft_parser.add_argument("--queue-path")
    prepare_local_coding_draft_parser.add_argument("--registry-path")
    prepare_local_coding_draft_parser.add_argument("--model")
    prepare_local_coding_draft_parser.add_argument("--run-id")
    prepare_local_coding_draft_parser.add_argument("--run", action="store_true")
    prepare_local_coding_draft_parser.add_argument("--force", action="store_true")
    prepare_local_coding_draft_parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="json",
    )
    inspect_human_gated_patch_contract_parser = subparsers.add_parser(
        "inspect-human-gated-patch-application-contract",
        help="Inspect the M88 human-gated patch application contract without applying patches.",
    )
    inspect_human_gated_patch_contract_parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="json",
    )
    inspect_model_usage_report_parser = subparsers.add_parser(
        "inspect-model-usage-report",
        help="Inspect local model usage, Codex token accounting, and local LLM run metadata.",
    )
    inspect_model_usage_report_parser.add_argument("--output")
    inspect_model_usage_report_parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="json",
    )
    inspect_sprint_batch_report_parser = subparsers.add_parser(
        "inspect-sprint-batch-report",
        help="Inspect a local overnight sprint batch summary from git, queue, and dispatch evidence.",
    )
    inspect_sprint_batch_report_parser.add_argument("--since-commit")
    inspect_sprint_batch_report_parser.add_argument("--commit-count", type=int, default=20)
    inspect_sprint_batch_report_parser.add_argument("--output")
    inspect_sprint_batch_report_parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="json",
    )
    plan_operator_batch_parser = subparsers.add_parser(
        "plan-operator-batch",
        help="Plan a local-only sequential operator sprint batch from project queue state.",
    )
    plan_operator_batch_parser.add_argument("--project-id", required=True)
    plan_operator_batch_parser.add_argument("--queue-path")
    plan_operator_batch_parser.add_argument("--registry-path")
    plan_operator_batch_parser.add_argument("--limit", type=int, default=10)
    plan_operator_batch_parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="markdown",
    )
    plan_operator_batch_v2_parser = subparsers.add_parser(
        "plan-operator-batch-v2",
        help="Recommend a local-only operator batch sequence with prerequisites and review warnings.",
    )
    plan_operator_batch_v2_parser.add_argument("--project-id", required=True)
    plan_operator_batch_v2_parser.add_argument("--queue-path")
    plan_operator_batch_v2_parser.add_argument("--registry-path")
    plan_operator_batch_v2_parser.add_argument("--approval-path")
    plan_operator_batch_v2_parser.add_argument("--limit", type=int, default=10)
    plan_operator_batch_v2_parser.add_argument("--include-blocked", action="store_true")
    plan_operator_batch_v2_parser.add_argument("--output")
    plan_operator_batch_v2_parser.add_argument("--force", action="store_true")
    plan_operator_batch_v2_parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="markdown",
    )
    inspect_documentation_agent_contract_parser = subparsers.add_parser(
        "inspect-documentation-agent-contract",
        help="Inspect the M91 Documentation Agent v1 contract without mutating docs.",
    )
    inspect_documentation_agent_contract_parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="json",
    )
    run_single_ready_codex_queue_item_parser = subparsers.add_parser(
        "run-single-ready-codex-queue-item",
        help="Run one manually ready queue item through operator-approved Codex dispatch, validation, git, and queue evidence.",
    )
    run_single_ready_codex_queue_item_parser.add_argument("--item-id")
    run_single_ready_codex_queue_item_parser.add_argument("--queue-path")
    run_single_ready_codex_queue_item_parser.add_argument("--registry-path")
    run_single_ready_codex_queue_item_parser.add_argument("--prompt-output")
    run_single_ready_codex_queue_item_parser.add_argument("--force-prompt", action="store_true")
    run_single_ready_codex_queue_item_parser.add_argument("--approved-by", default="local_operator")
    run_single_ready_codex_queue_item_parser.add_argument("--approval-phrase", required=True)
    run_single_ready_codex_queue_item_parser.add_argument("--run-id")
    run_single_ready_codex_queue_item_parser.add_argument("--command", dest="codex_command")
    run_single_ready_codex_queue_item_parser.add_argument("--command-arg", action="append", default=[])
    run_single_ready_codex_queue_item_parser.add_argument("--timeout-seconds", type=int, default=300)
    run_single_ready_codex_queue_item_parser.add_argument("--validation-command", action="append", default=[])
    run_single_ready_codex_queue_item_parser.add_argument(
        "--implementation-commit-message",
        default="M79.2 add single-item ready Codex automation",
    )
    run_single_ready_codex_queue_item_parser.add_argument(
        "--queue-evidence-commit-message",
        default="Record M79.2 queue evidence",
    )
    run_single_ready_codex_queue_item_parser.add_argument("--closed-by", default="local_operator")
    run_single_ready_codex_queue_item_parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="json",
    )
    approve_codex_dispatch_parser = subparsers.add_parser(
        "approve-codex-dispatch",
        help="Approve one M78 operator-gated Codex dispatch run without executing it.",
    )
    approve_codex_dispatch_parser.add_argument("--item-id", required=True)
    approve_codex_dispatch_parser.add_argument("--approved-by", required=True)
    approve_codex_dispatch_parser.add_argument("--approval-phrase", required=True)
    approve_codex_dispatch_parser.add_argument("--run-id")
    approve_codex_dispatch_parser.add_argument("--queue-path")
    approve_codex_dispatch_parser.add_argument("--registry-path")
    approve_codex_dispatch_parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="json",
    )
    run_codex_dispatch_parser = subparsers.add_parser(
        "run-codex-dispatch",
        help="Run one prepared Codex dispatch artifact when M135 gates and explicit execution controls pass.",
    )
    run_codex_dispatch_parser.add_argument("--item-id", required=True)
    run_codex_dispatch_parser.add_argument("--artifact-path")
    run_codex_dispatch_parser.add_argument("--run-id")
    run_codex_dispatch_parser.add_argument("--command", dest="codex_command")
    run_codex_dispatch_parser.add_argument("--command-arg", action="append", default=[])
    run_codex_dispatch_parser.add_argument("--timeout-seconds", type=int, default=300)
    run_codex_dispatch_parser.add_argument("--dry-run", action="store_true")
    run_codex_dispatch_parser.add_argument("--force", action="store_true")
    run_codex_dispatch_parser.add_argument("--output")
    run_codex_dispatch_parser.add_argument("--queue-path")
    run_codex_dispatch_parser.add_argument("--require-clean-worktree", action="store_true")
    run_codex_dispatch_parser.add_argument("--execution-enabled", action="store_true")
    run_codex_dispatch_parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="json",
    )
    ingest_codex_result_parser = subparsers.add_parser(
        "ingest-codex-result-and-validate",
        help="Ingest a Codex execution record, run local validation, and generate completion handoff evidence.",
    )
    ingest_codex_result_parser.add_argument("--item-id", required=True)
    ingest_codex_result_parser.add_argument("--execution-record", required=True)
    ingest_codex_result_parser.add_argument("--dry-run", action="store_true")
    ingest_codex_result_parser.add_argument(
        "--validation-profile",
        choices=sorted(CODEX_RESULT_VALIDATION_PROFILES),
        default="code_unit_tests",
    )
    ingest_codex_result_parser.add_argument("--queue-path")
    ingest_codex_result_parser.add_argument("--output")
    ingest_codex_result_parser.add_argument("--force", action="store_true")
    ingest_codex_result_parser.add_argument(
        "--format",
        choices=["json"],
        default="json",
    )
    github_sync_agent_parser = subparsers.add_parser(
        "run-github-sync-agent",
        help="Run a dry-run-first GitHub issue/PR sync agent with narrow explicit GitHub gates.",
    )
    github_sync_agent_parser.add_argument("--item-id", required=True)
    github_sync_agent_parser.add_argument("--dry-run", action="store_true")
    github_sync_agent_parser.add_argument(
        "--sync-mode",
        choices=["issue-comment", "issue-update", "pr-comment", "pr-summary"],
        default="issue-comment",
    )
    github_sync_agent_parser.add_argument("--github-enabled", action="store_true")
    github_sync_agent_parser.add_argument("--repo")
    github_sync_agent_parser.add_argument("--issue-number", type=int)
    github_sync_agent_parser.add_argument("--pr-number", type=int)
    github_sync_agent_parser.add_argument("--artifact-path")
    github_sync_agent_parser.add_argument("--queue-path")
    github_sync_agent_parser.add_argument("--output")
    github_sync_agent_parser.add_argument("--force", action="store_true")
    github_sync_agent_parser.add_argument(
        "--format",
        choices=["json"],
        default="json",
    )
    run_agent_orchestration_parser = subparsers.add_parser(
        "run-agent-orchestration",
        help="Run an M138 multi-agent orchestration plan step-by-step with machine gates.",
    )
    run_agent_orchestration_parser.add_argument("--item-id", required=True)
    run_agent_orchestration_parser.add_argument("--plan-path")
    run_agent_orchestration_parser.add_argument("--dry-run", action="store_true")
    run_agent_orchestration_parser.add_argument("--max-steps", type=int)
    run_agent_orchestration_parser.add_argument("--allow-low-risk-real", action="store_true")
    run_agent_orchestration_parser.add_argument("--allow-local-llm", action="store_true")
    run_agent_orchestration_parser.add_argument("--allow-codex", action="store_true")
    run_agent_orchestration_parser.add_argument("--allow-github-sync", action="store_true")
    run_agent_orchestration_parser.add_argument("--queue-path")
    run_agent_orchestration_parser.add_argument("--output")
    run_agent_orchestration_parser.add_argument("--force", action="store_true")
    run_agent_orchestration_parser.add_argument(
        "--format",
        choices=["json"],
        default="json",
    )
    autonomous_sprint_closeout_parser = subparsers.add_parser(
        "generate-autonomous-sprint-closeout",
        help="Generate the M139 autonomous sprint closeout artifact without running Codex, LLMs, or GitHub.",
    )
    autonomous_sprint_closeout_parser.add_argument("--project-id", required=True)
    autonomous_sprint_closeout_parser.add_argument("--sprint-start", default="M125")
    autonomous_sprint_closeout_parser.add_argument("--sprint-end", default="M139")
    autonomous_sprint_closeout_parser.add_argument("--dry-run", action="store_true")
    autonomous_sprint_closeout_parser.add_argument("--apply-docs-only", action="store_true")
    autonomous_sprint_closeout_parser.add_argument("--queue-path")
    autonomous_sprint_closeout_parser.add_argument("--output")
    autonomous_sprint_closeout_parser.add_argument("--force", action="store_true")
    autonomous_sprint_closeout_parser.add_argument(
        "--format",
        choices=["json"],
        default="json",
    )
    autonomy_readiness_report_parser = subparsers.add_parser(
        "generate-autonomy-readiness-report",
        help="Generate the M154 sprint closeout and autonomy readiness report without executing agents, models, Codex, or GitHub.",
    )
    autonomy_readiness_report_parser.add_argument("--project-id", default="aresforge")
    autonomy_readiness_report_parser.add_argument("--sprint-start", default="M140")
    autonomy_readiness_report_parser.add_argument("--sprint-end", default="M154")
    autonomy_readiness_report_parser.add_argument(
        "--item-id",
        default="m154-sprint-closeout-and-autonomy-readiness-report",
    )
    autonomy_readiness_report_parser.add_argument("--queue-path")
    autonomy_readiness_report_parser.add_argument("--output")
    autonomy_readiness_report_parser.add_argument("--force", action="store_true")
    autonomy_readiness_report_parser.add_argument(
        "--format",
        choices=["json"],
        default="json",
    )
    inspect_orchestrator_state_machine_parser = subparsers.add_parser(
        "inspect-orchestrator-state-machine",
        help="Inspect the M140 durable orchestrator execution state machine without executing agents.",
    )
    inspect_orchestrator_state_machine_parser.add_argument(
        "--item-id",
        default="m140-orchestrator-execution-state-machine-v1",
    )
    inspect_orchestrator_state_machine_parser.add_argument("--project-id", default="aresforge")
    inspect_orchestrator_state_machine_parser.add_argument("--queue-path")
    inspect_orchestrator_state_machine_parser.add_argument("--output")
    inspect_orchestrator_state_machine_parser.add_argument("--force", action="store_true")
    inspect_orchestrator_state_machine_parser.add_argument(
        "--format",
        choices=["json"],
        default="json",
    )
    inspect_orchestration_run_history_parser = subparsers.add_parser(
        "inspect-orchestration-run-history",
        help="Inspect persisted M141 orchestration run history and recovery records without execution.",
    )
    inspect_orchestration_run_history_parser.add_argument("--project-id", required=True)
    inspect_orchestration_run_history_parser.add_argument("--item-id")
    inspect_orchestration_run_history_parser.add_argument("--run-id")
    inspect_orchestration_run_history_parser.add_argument("--queue-path")
    inspect_orchestration_run_history_parser.add_argument("--history-path")
    inspect_orchestration_run_history_parser.add_argument("--artifacts-root")
    inspect_orchestration_run_history_parser.add_argument("--output")
    inspect_orchestration_run_history_parser.add_argument("--force", action="store_true")
    inspect_orchestration_run_history_parser.add_argument(
        "--format",
        choices=["json"],
        default="json",
    )
    inspect_orchestration_run_store_parser = subparsers.add_parser(
        "inspect-orchestration-run-store",
        help="Inspect and bootstrap the M155 durable orchestration run store without executing work.",
    )
    inspect_orchestration_run_store_parser.add_argument("--project-id", default="aresforge")
    inspect_orchestration_run_store_parser.add_argument("--item-id")
    inspect_orchestration_run_store_parser.add_argument("--run-id")
    inspect_orchestration_run_store_parser.add_argument("--history-path")
    inspect_orchestration_run_store_parser.add_argument("--queue-path")
    inspect_orchestration_run_store_parser.add_argument("--output")
    inspect_orchestration_run_store_parser.add_argument("--force", action="store_true")
    inspect_orchestration_run_store_parser.add_argument(
        "--format",
        choices=["json"],
        default="json",
    )
    inspect_orchestration_resume_plan_parser = subparsers.add_parser(
        "inspect-orchestration-resume-plan",
        help="Inspect the M147 resume-from-failure plan for one local orchestration run without resuming execution.",
    )
    inspect_orchestration_resume_plan_parser.add_argument("--run-id", required=True)
    inspect_orchestration_resume_plan_parser.add_argument(
        "--item-id",
        default="m147-orchestrator-resume-from-failure",
    )
    inspect_orchestration_resume_plan_parser.add_argument("--project-id", default="aresforge")
    inspect_orchestration_resume_plan_parser.add_argument("--queue-path")
    inspect_orchestration_resume_plan_parser.add_argument("--history-path")
    inspect_orchestration_resume_plan_parser.add_argument("--artifacts-root")
    inspect_orchestration_resume_plan_parser.add_argument("--output")
    inspect_orchestration_resume_plan_parser.add_argument("--force", action="store_true")
    inspect_orchestration_resume_plan_parser.add_argument(
        "--format",
        choices=["json"],
        default="json",
    )
    inspect_orchestration_run_monitor_parser = subparsers.add_parser(
        "inspect-orchestration-run-monitor",
        help="Inspect the M153 Hub orchestration run monitor without executing or resuming work.",
    )
    inspect_orchestration_run_monitor_parser.add_argument("--project-id", default="aresforge")
    inspect_orchestration_run_monitor_parser.add_argument("--item-id")
    inspect_orchestration_run_monitor_parser.add_argument("--run-id")
    inspect_orchestration_run_monitor_parser.add_argument("--queue-path")
    inspect_orchestration_run_monitor_parser.add_argument("--history-path")
    inspect_orchestration_run_monitor_parser.add_argument("--artifacts-root")
    inspect_orchestration_run_monitor_parser.add_argument("--output")
    inspect_orchestration_run_monitor_parser.add_argument("--force", action="store_true")
    inspect_orchestration_run_monitor_parser.add_argument(
        "--format",
        choices=["json"],
        default="json",
    )
    inspect_orchestration_artifact_retention_parser = subparsers.add_parser(
        "inspect-orchestration-artifact-retention",
        help="Inspect the M156 local orchestration artifact retention/indexing policy without deleting artifacts.",
    )
    inspect_orchestration_artifact_retention_parser.add_argument("--project-id", default="aresforge")
    inspect_orchestration_artifact_retention_parser.add_argument(
        "--item-id",
        default="m156-orchestration-artifact-retention-policy",
    )
    inspect_orchestration_artifact_retention_parser.add_argument("--history-path")
    inspect_orchestration_artifact_retention_parser.add_argument("--queue-path")
    inspect_orchestration_artifact_retention_parser.add_argument("--output")
    inspect_orchestration_artifact_retention_parser.add_argument("--force", action="store_true")
    inspect_orchestration_artifact_retention_parser.add_argument(
        "--format",
        choices=["json"],
        default="json",
    )
    replay_orchestration_run_parser = subparsers.add_parser(
        "replay-orchestration-run",
        help="Replay an orchestration run as dry-run metadata reconstruction and audit evidence without execution.",
    )
    replay_orchestration_run_parser.add_argument("--run-id", required=True)
    replay_orchestration_run_parser.add_argument("--project-id", default="aresforge")
    replay_orchestration_run_parser.add_argument(
        "--item-id",
        default="m157-run-replay-and-audit-trail",
    )
    replay_orchestration_run_parser.add_argument("--dry-run", action="store_true")
    replay_orchestration_run_parser.add_argument("--history-path")
    replay_orchestration_run_parser.add_argument("--artifacts-root")
    replay_orchestration_run_parser.add_argument("--queue-path")
    replay_orchestration_run_parser.add_argument("--output")
    replay_orchestration_run_parser.add_argument("--force", action="store_true")
    replay_orchestration_run_parser.add_argument(
        "--format",
        choices=["json"],
        default="json",
    )
    inspect_autonomy_profile_parser = subparsers.add_parser(
        "inspect-autonomy-profile",
        help="Inspect M158 operator autonomy configuration profiles without executing autonomous capabilities.",
    )
    inspect_autonomy_profile_parser.add_argument("--project-id", default="aresforge")
    inspect_autonomy_profile_parser.add_argument(
        "--item-id",
        default="m158-operator-autonomy-configuration-profile",
    )
    inspect_autonomy_profile_parser.add_argument("--autonomy-profile")
    inspect_autonomy_profile_parser.add_argument("--queue-path")
    inspect_autonomy_profile_parser.add_argument("--output")
    inspect_autonomy_profile_parser.add_argument("--force", action="store_true")
    inspect_autonomy_profile_parser.add_argument(
        "--format",
        choices=["json"],
        default="json",
    )
    inspect_codex_execution_enablements_parser = subparsers.add_parser(
        "inspect-codex-execution-enablements",
        help="Inspect M142 machine-gated real Codex execution enablement profiles without executing Codex.",
    )
    inspect_codex_execution_enablements_parser.add_argument(
        "--item-id",
        default="m142-real-codex-execution-enablement-profile",
    )
    inspect_codex_execution_enablements_parser.add_argument("--project-id", default="aresforge")
    inspect_codex_execution_enablements_parser.add_argument("--queue-path")
    inspect_codex_execution_enablements_parser.add_argument("--output")
    inspect_codex_execution_enablements_parser.add_argument("--force", action="store_true")
    inspect_codex_execution_enablements_parser.add_argument(
        "--format",
        choices=["json"],
        default="json",
    )
    inspect_codex_worktree_guard_parser = subparsers.add_parser(
        "inspect-codex-worktree-guard",
        help="Inspect M143 Codex execution sandbox and worktree guards without executing Codex.",
    )
    inspect_codex_worktree_guard_parser.add_argument(
        "--item-id",
        default="m143-codex-execution-sandbox-and-worktree-guard",
    )
    inspect_codex_worktree_guard_parser.add_argument("--project-id", default="aresforge")
    inspect_codex_worktree_guard_parser.add_argument("--queue-path")
    inspect_codex_worktree_guard_parser.add_argument("--output")
    inspect_codex_worktree_guard_parser.add_argument("--force", action="store_true")
    inspect_codex_worktree_guard_parser.add_argument(
        "--format",
        choices=["json"],
        default="json",
    )
    inspect_codex_validation_profiles_parser = subparsers.add_parser(
        "inspect-codex-validation-profiles",
        help="Inspect M144 Codex validation profiles by task type, changed paths, and risk without running validation.",
    )
    inspect_codex_validation_profiles_parser.add_argument(
        "--item-id",
        default="m144-codex-validation-profile-expansion",
    )
    inspect_codex_validation_profiles_parser.add_argument("--project-id", default="aresforge")
    inspect_codex_validation_profiles_parser.add_argument("--queue-path")
    inspect_codex_validation_profiles_parser.add_argument("--task-type")
    inspect_codex_validation_profiles_parser.add_argument("--risk-class")
    inspect_codex_validation_profiles_parser.add_argument("--changed-path", action="append", default=[])
    inspect_codex_validation_profiles_parser.add_argument("--output")
    inspect_codex_validation_profiles_parser.add_argument("--force", action="store_true")
    inspect_codex_validation_profiles_parser.add_argument(
        "--format",
        choices=["json"],
        default="json",
    )
    classify_codex_failure_parser = subparsers.add_parser(
        "classify-codex-failure",
        help="Classify a local Codex failure artifact and report deterministic retry/stop policy without retrying.",
    )
    classify_codex_failure_parser.add_argument("--failure-artifact", required=True)
    classify_codex_failure_parser.add_argument(
        "--item-id",
        default="m145-codex-failure-classification-and-retry-policy",
    )
    classify_codex_failure_parser.add_argument("--project-id", default="aresforge")
    classify_codex_failure_parser.add_argument("--queue-path")
    classify_codex_failure_parser.add_argument("--output")
    classify_codex_failure_parser.add_argument("--force", action="store_true")
    classify_codex_failure_parser.add_argument(
        "--format",
        choices=["json"],
        default="json",
    )
    normalize_agent_step_result_parser = subparsers.add_parser(
        "normalize-agent-step-result",
        help="Normalize one local agent step result artifact into a stable orchestrator evaluation schema.",
    )
    normalize_agent_step_result_parser.add_argument("--result-path", required=True)
    normalize_agent_step_result_parser.add_argument(
        "--item-id",
        default="m146-agent-step-result-normalization",
    )
    normalize_agent_step_result_parser.add_argument("--project-id", default="aresforge")
    normalize_agent_step_result_parser.add_argument("--queue-path")
    normalize_agent_step_result_parser.add_argument("--output")
    normalize_agent_step_result_parser.add_argument("--force", action="store_true")
    normalize_agent_step_result_parser.add_argument(
        "--format",
        choices=["json"],
        default="json",
    )
    classify_source_patch_risk_parser = subparsers.add_parser(
        "classify-source-patch-risk",
        help="Classify a local source patch by touched files, risk, mutation type, blocked operations, and validation needs.",
    )
    classify_source_patch_risk_parser.add_argument("--patch-path", required=True)
    classify_source_patch_risk_parser.add_argument(
        "--item-id",
        default="m148-safe-source-patch-detection-and-risk-classifier",
    )
    classify_source_patch_risk_parser.add_argument("--project-id", default="aresforge")
    classify_source_patch_risk_parser.add_argument("--queue-path")
    classify_source_patch_risk_parser.add_argument("--output")
    classify_source_patch_risk_parser.add_argument("--force", action="store_true")
    classify_source_patch_risk_parser.add_argument(
        "--format",
        choices=["json"],
        default="json",
    )
    plan_source_patch_apply_parser = subparsers.add_parser(
        "plan-source-patch-apply",
        help="Generate a controlled source patch apply plan without applying source-code changes.",
    )
    plan_source_patch_apply_parser.add_argument("--patch-path", required=True)
    plan_source_patch_apply_parser.add_argument(
        "--item-id",
        default="m149-controlled-source-patch-apply-plan",
    )
    plan_source_patch_apply_parser.add_argument("--project-id", default="aresforge")
    plan_source_patch_apply_parser.add_argument("--queue-path")
    plan_source_patch_apply_parser.add_argument("--output")
    plan_source_patch_apply_parser.add_argument("--force", action="store_true")
    plan_source_patch_apply_parser.add_argument(
        "--format",
        choices=["json"],
        default="json",
    )
    dry_run_source_patch_apply_parser = subparsers.add_parser(
        "dry-run-source-patch-apply",
        help="Prove source patch applicability with git apply --check under machine gates without applying the patch.",
    )
    dry_run_source_patch_apply_parser.add_argument("--patch-path", required=True)
    dry_run_source_patch_apply_parser.add_argument(
        "--item-id",
        default="m150-machine-gated-source-patch-apply-dry-run",
    )
    dry_run_source_patch_apply_parser.add_argument("--project-id", default="aresforge")
    dry_run_source_patch_apply_parser.add_argument("--queue-path")
    dry_run_source_patch_apply_parser.add_argument("--output")
    dry_run_source_patch_apply_parser.add_argument("--force", action="store_true")
    dry_run_source_patch_apply_parser.add_argument(
        "--format",
        choices=["json"],
        default="json",
    )
    preflight_real_codex_execution_parser = subparsers.add_parser(
        "preflight-real-codex-execution",
        help="Dry-run hardening preflight for future real Codex execution without invoking Codex.",
    )
    preflight_real_codex_execution_parser.add_argument(
        "--item-id",
        default="m159-real-codex-execution-preflight-hardening",
    )
    preflight_real_codex_execution_parser.add_argument("--project-id", default="aresforge")
    preflight_real_codex_execution_parser.add_argument("--dry-run", action="store_true")
    preflight_real_codex_execution_parser.add_argument("--autonomy-profile")
    preflight_real_codex_execution_parser.add_argument(
        "--validation-profile",
        choices=sorted(CODEX_RESULT_VALIDATION_PROFILES),
    )
    preflight_real_codex_execution_parser.add_argument("--changed-path", action="append", default=[])
    preflight_real_codex_execution_parser.add_argument("--queue-path")
    preflight_real_codex_execution_parser.add_argument("--history-path")
    preflight_real_codex_execution_parser.add_argument("--output")
    preflight_real_codex_execution_parser.add_argument("--force", action="store_true")
    preflight_real_codex_execution_parser.add_argument(
        "--format",
        choices=["json"],
        default="json",
    )
    low_risk_codex_pilot_parser = subparsers.add_parser(
        "prepare-low-risk-codex-pilot",
        help="Prepare and optionally execute one low-risk Codex pilot item under M159/M152 machine gates.",
    )
    low_risk_codex_pilot_parser.add_argument(
        "--item-id",
        default="m160-low-risk-codex-execution-pilot-item",
    )
    low_risk_codex_pilot_parser.add_argument("--project-id", default="aresforge")
    low_risk_codex_pilot_parser.add_argument("--dry-run", action="store_true")
    low_risk_codex_pilot_parser.add_argument("--execution-enabled", action="store_true")
    low_risk_codex_pilot_parser.add_argument("--allow-low-risk-code", action="store_true")
    low_risk_codex_pilot_parser.add_argument("--autonomy-profile")
    low_risk_codex_pilot_parser.add_argument(
        "--validation-profile",
        choices=sorted(CODEX_RESULT_VALIDATION_PROFILES),
        default="queue_system",
    )
    low_risk_codex_pilot_parser.add_argument("--changed-path", action="append", default=[])
    low_risk_codex_pilot_parser.add_argument("--codex-command-arg", action="append", default=[])
    low_risk_codex_pilot_parser.add_argument("--timeout-seconds", type=int)
    low_risk_codex_pilot_parser.add_argument("--queue-path")
    low_risk_codex_pilot_parser.add_argument("--history-path")
    low_risk_codex_pilot_parser.add_argument("--output")
    low_risk_codex_pilot_parser.add_argument("--force", action="store_true")
    low_risk_codex_pilot_parser.add_argument(
        "--format",
        choices=["json"],
        default="json",
    )
    codex_loop_validation_evidence_parser = subparsers.add_parser(
        "bundle-codex-loop-validation-evidence",
        help="Bundle local Codex loop execution, validation, gates, classifications, and completion recommendation evidence.",
    )
    codex_loop_validation_evidence_parser.add_argument(
        "--item-id",
        default="m161-codex-loop-validation-evidence-bundle",
    )
    codex_loop_validation_evidence_parser.add_argument("--project-id", default="aresforge")
    codex_loop_validation_evidence_parser.add_argument("--dry-run", action="store_true")
    codex_loop_validation_evidence_parser.add_argument("--autonomy-profile")
    codex_loop_validation_evidence_parser.add_argument(
        "--validation-profile",
        choices=sorted(CODEX_RESULT_VALIDATION_PROFILES),
        default="queue_system",
    )
    codex_loop_validation_evidence_parser.add_argument("--changed-path", action="append", default=[])
    codex_loop_validation_evidence_parser.add_argument("--patch-path")
    codex_loop_validation_evidence_parser.add_argument("--queue-path")
    codex_loop_validation_evidence_parser.add_argument("--output")
    codex_loop_validation_evidence_parser.add_argument("--force", action="store_true")
    codex_loop_validation_evidence_parser.add_argument(
        "--format",
        choices=["json"],
        default="json",
    )
    end_to_end_codex_loop_parser = subparsers.add_parser(
        "run-end-to-end-codex-loop",
        help="Run the Codex-backed orchestration loop through dispatch, validation, and completion recommendation gates.",
    )
    end_to_end_codex_loop_parser.add_argument(
        "--item-id",
        default="m151-end-to-end-codex-loop-dry-run",
    )
    end_to_end_codex_loop_parser.add_argument("--project-id", default="aresforge")
    end_to_end_codex_loop_parser.add_argument("--dry-run", action="store_true")
    end_to_end_codex_loop_parser.add_argument("--execution-enabled", action="store_true")
    end_to_end_codex_loop_parser.add_argument("--allow-low-risk-code", action="store_true")
    end_to_end_codex_loop_parser.add_argument("--changed-path", action="append", default=[])
    end_to_end_codex_loop_parser.add_argument("--codex-command-arg", action="append", default=[])
    end_to_end_codex_loop_parser.add_argument("--timeout-seconds", type=int)
    end_to_end_codex_loop_parser.add_argument(
        "--validation-profile",
        choices=sorted(CODEX_RESULT_VALIDATION_PROFILES),
        default="queue_system",
    )
    end_to_end_codex_loop_parser.add_argument("--queue-path")
    end_to_end_codex_loop_parser.add_argument("--output")
    end_to_end_codex_loop_parser.add_argument("--force", action="store_true")
    end_to_end_codex_loop_parser.add_argument(
        "--format",
        choices=["json"],
        default="json",
    )
    inspect_codex_dispatch_run_parser = subparsers.add_parser(
        "inspect-codex-dispatch-run",
        help="Inspect one local M78 Codex dispatch run-state record.",
    )
    inspect_codex_dispatch_run_parser.add_argument("--run-id", required=True)
    inspect_codex_dispatch_run_parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="json",
    )
    list_codex_dispatch_runs_parser = subparsers.add_parser(
        "list-codex-dispatch-runs",
        help="List local M78 Codex dispatch run-state records.",
    )
    list_codex_dispatch_runs_parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="json",
    )
    cancel_codex_dispatch_run_parser = subparsers.add_parser(
        "cancel-codex-dispatch-run",
        help="Cancel one approved-but-not-running local M78 Codex dispatch run.",
    )
    cancel_codex_dispatch_run_parser.add_argument("--run-id", required=True)
    cancel_codex_dispatch_run_parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="json",
    )
    recover_codex_dispatch_run_parser = subparsers.add_parser(
        "recover-codex-dispatch-run",
        help="Mark one local Codex dispatch run as recovery-required without completing queue work.",
    )
    recover_codex_dispatch_run_parser.add_argument("--run-id", required=True)
    recover_codex_dispatch_run_parser.add_argument("--recovery-note", default="")
    recover_codex_dispatch_run_parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="json",
    )
    inspect_local_project_dashboard_parser = subparsers.add_parser(
        "inspect-local-project-dashboard",
        help="Inspect read-only local project dashboard contract payload.",
    )
    inspect_local_project_dashboard_parser.add_argument(
        "--format",
        choices=["json"],
        default="json",
    )
    list_local_projects_parser = subparsers.add_parser(
        "list-local-projects",
        help="List read-only local managed projects with active-project and readiness hints.",
    )
    list_local_projects_parser.add_argument(
        "--format",
        choices=["json"],
        default="json",
    )
    inspect_local_project_readiness_parser = subparsers.add_parser(
        "inspect-local-project-readiness",
        help="Inspect read-only local readiness contract for one managed project.",
    )
    inspect_local_project_readiness_parser.add_argument("--project-id", required=True)
    inspect_local_project_readiness_parser.add_argument(
        "--format",
        choices=["json"],
        default="json",
    )
    inspect_local_queue_agent_summary_parser = subparsers.add_parser(
        "inspect-local-queue-agent-summary",
        help="Inspect read-only local queue and agent workload summary contract.",
    )
    inspect_local_queue_agent_summary_parser.add_argument(
        "--format",
        choices=["json"],
        default="json",
    )
    inspect_local_project_report_parser = subparsers.add_parser(
        "inspect-local-project-report",
        help="Inspect read-only local project report summary contract.",
    )
    inspect_local_project_report_parser.add_argument(
        "--format",
        choices=["json"],
        default="json",
    )
    inspect_self_managed_project_parser = subparsers.add_parser(
        "inspect-self-managed-project",
        help="Inspect read-only self-managed project seed readiness and consistency.",
    )
    inspect_self_managed_project_parser.add_argument("--project-id", required=True)
    inspect_self_managed_project_parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="markdown",
    )
    init_agent_profiles_parser = subparsers.add_parser(
        "init-agent-profiles",
        help="Initialize local agent profiles under .aresforge/agents.",
    )
    init_agent_profiles_parser.add_argument("--path")
    init_agent_profiles_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing agent profiles file.",
    )
    init_agent_profiles_parser.add_argument(
        "--with-defaults",
        action="store_true",
        help="Seed default local-first agent profiles and handoff targets.",
    )
    register_agent_profile_parser = subparsers.add_parser(
        "register-agent-profile",
        help="Register or update one local agent profile by agent_id.",
    )
    register_agent_profile_parser.add_argument("--agent-id", required=True)
    register_agent_profile_parser.add_argument("--name", required=True)
    register_agent_profile_parser.add_argument("--role", required=True, choices=list(AGENT_ROLES))
    register_agent_profile_parser.add_argument("--profiles-path")
    register_agent_profile_parser.add_argument("--description")
    register_agent_profile_parser.add_argument("--execution-mode", choices=list(EXECUTION_MODES))
    register_agent_profile_parser.add_argument("--model-preference")
    register_agent_profile_parser.add_argument("--strength", action="append", default=[])
    register_agent_profile_parser.add_argument("--constraint", action="append", default=[])
    register_agent_profile_parser.add_argument("--allowed-type", action="append", default=[])
    register_agent_profile_parser.add_argument("--escalation-allowed")
    register_agent_profile_parser.add_argument("--handoff-target-id")
    register_agent_profile_parser.add_argument("--status", choices=list(AGENT_PROFILE_STATUSES))
    register_agent_profile_parser.add_argument("--tag", action="append", default=[])
    register_agent_profile_parser.add_argument("--notes")
    register_handoff_target_parser = subparsers.add_parser(
        "register-handoff-target",
        help="Register or update one local handoff target by target_id.",
    )
    register_handoff_target_parser.add_argument("--target-id", required=True)
    register_handoff_target_parser.add_argument("--name", required=True)
    register_handoff_target_parser.add_argument(
        "--target-type", required=True, choices=list(HANDOFF_TARGET_TYPES)
    )
    register_handoff_target_parser.add_argument("--profiles-path")
    register_handoff_target_parser.add_argument("--description")
    register_handoff_target_parser.add_argument("--local-command")
    register_handoff_target_parser.add_argument("--input-format")
    register_handoff_target_parser.add_argument("--output-format")
    register_handoff_target_parser.add_argument("--safety-note", action="append", default=[])
    register_handoff_target_parser.add_argument("--status", choices=list(AGENT_PROFILE_STATUSES))
    register_handoff_target_parser.add_argument("--tag", action="append", default=[])
    register_handoff_target_parser.add_argument("--notes")
    inspect_agent_profiles_parser = subparsers.add_parser(
        "inspect-agent-profiles",
        help="Inspect local agent profiles with optional filtering.",
    )
    inspect_agent_profiles_parser.add_argument("--profiles-path")
    inspect_agent_profiles_parser.add_argument("--role", choices=list(AGENT_ROLES))
    inspect_agent_profiles_parser.add_argument("--execution-mode", choices=list(EXECUTION_MODES))
    inspect_agent_profiles_parser.add_argument("--status", choices=list(AGENT_PROFILE_STATUSES))
    inspect_agent_profiles_parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="json",
    )
    inspect_agent_profile_parser = subparsers.add_parser(
        "inspect-agent-profile",
        help="Inspect one local agent profile by agent_id.",
    )
    inspect_agent_profile_parser.add_argument("--agent-id", required=True)
    inspect_agent_profile_parser.add_argument("--profiles-path")
    inspect_agent_profile_parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="json",
    )
    inspect_handoff_target_parser = subparsers.add_parser(
        "inspect-handoff-target",
        help="Inspect one local handoff target by target_id.",
    )
    inspect_handoff_target_parser.add_argument("--target-id", required=True)
    inspect_handoff_target_parser.add_argument("--profiles-path")
    inspect_handoff_target_parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="json",
    )
    plan_agent_orchestration_parser = subparsers.add_parser(
        "plan-agent-orchestration",
        help="Generate a local-only, plan-only multi-agent orchestration plan from queue, profiles, and registry data.",
    )
    plan_agent_orchestration_parser.add_argument("--project-id")
    plan_agent_orchestration_parser.add_argument("--repo-id")
    plan_agent_orchestration_parser.add_argument("--status", choices=list(QUEUE_STATUSES))
    plan_agent_orchestration_parser.add_argument("--queue-path")
    plan_agent_orchestration_parser.add_argument("--profiles-path")
    plan_agent_orchestration_parser.add_argument("--registry-path")
    plan_agent_orchestration_parser.add_argument("--output")
    plan_agent_orchestration_parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="json",
        help="Output format for file writes or stdout rendering.",
    )
    plan_agent_orchestration_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing output file.",
    )
    plan_llm_escalation_parser = subparsers.add_parser(
        "plan-llm-escalation",
        help="Generate a local-only, plan-only LLM escalation plan from queue/profiles/orchestration context.",
    )
    plan_llm_escalation_parser.add_argument("--item-id")
    plan_llm_escalation_parser.add_argument("--project-id")
    plan_llm_escalation_parser.add_argument("--repo-id")
    plan_llm_escalation_parser.add_argument("--status", choices=list(QUEUE_STATUSES))
    plan_llm_escalation_parser.add_argument("--queue-path")
    plan_llm_escalation_parser.add_argument("--profiles-path")
    plan_llm_escalation_parser.add_argument("--orchestration-plan")
    plan_llm_escalation_parser.add_argument("--output")
    plan_llm_escalation_parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="json",
        help="Output format for file writes or stdout rendering.",
    )
    plan_llm_escalation_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing output file.",
    )
    inspect_bootstrap_status_parser = subparsers.add_parser(
        "inspect-bootstrap-status",
        help="Inspect first-run local bootstrap readiness and state coverage.",
    )
    inspect_bootstrap_status_parser.add_argument("--repo-path")

    plan_bootstrap_parser = subparsers.add_parser(
        "plan-bootstrap",
        help="Generate a local-only bootstrap action plan.",
    )
    plan_bootstrap_parser.add_argument("--repo-path")
    plan_bootstrap_parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="json",
    )
    plan_bootstrap_parser.add_argument(
        "--seed-sample-work",
        action="store_true",
        help="Include sample queue milestone seeds in plan output.",
    )

    apply_bootstrap_parser = subparsers.add_parser(
        "apply-bootstrap",
        help="Apply first-run local bootstrap initialization and seeding actions.",
    )
    apply_bootstrap_parser.add_argument("--repo-path")
    apply_bootstrap_parser.add_argument(
        "--force",
        action="store_true",
        help="Enable force mode for bootstrap apply safeguards.",
    )
    apply_bootstrap_parser.add_argument(
        "--seed-sample-work",
        action="store_true",
        help="Seed sample queue milestones even when queue already has items.",
    )
    apply_bootstrap_parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="json",
    )

    serve_hub_parser = subparsers.add_parser(
        "serve-hub",
        help="Serve the local AresForge Hub UI and local API shell.",
    )
    serve_hub_parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Local bind host (defaults to 127.0.0.1).",
    )
    serve_hub_parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="Local bind port (defaults to 8765).",
    )
    serve_hub_parser.add_argument(
        "--open-browser",
        action="store_true",
        help="Open the local Hub URL in a browser after server startup.",
    )
    preflight_snapshot_parser = subparsers.add_parser(
        "generate-preflight-baseline-snapshot",
        help="Generate read-only baseline snapshot payload for closeout preflight reconciliation audits.",
    )
    preflight_snapshot_parser.add_argument("--parent-issue", type=int, required=True)
    preflight_snapshot_parser.add_argument(
        "--output",
        help="Optional output path for snapshot JSON; defaults to artifacts evidence directory.",
    )
    preflight_snapshot_diff_parser = subparsers.add_parser(
        "diff-preflight-snapshots",
        help="Diff two preflight snapshot JSON files in read-only mode.",
    )
    preflight_snapshot_diff_parser.add_argument("--before", required=True)
    preflight_snapshot_diff_parser.add_argument("--after", required=True)
    child_execution_gates_parser = subparsers.add_parser(
        "inspect-child-execution-gates",
        help="Inspect start/PR/merge/close gates for one child issue in read-only mode.",
    )
    child_execution_gates_parser.add_argument("--issue", type=int, required=True)
    child_execution_gates_parser.add_argument("--parent-issue", type=int)
    inspect_planning_parser = subparsers.add_parser(
        "inspect-planning-state",
        help="Inspect local planning state without writing local files or mutating GitHub.",
    )
    inspect_planning_parser.add_argument(
        "--planning-state-path",
        help="Optional local planning state path override (defaults to .aresforge/planning-state.json).",
    )
    compare_planning_parser = subparsers.add_parser(
        "compare-planning-state",
        help="Compare local planning state for drift without writing local files or mutating GitHub.",
    )
    compare_planning_parser.add_argument(
        "--planning-state-path",
        help="Optional local planning state path override (defaults to .aresforge/planning-state.json).",
    )
    inspect_sequential_run_state_parser = subparsers.add_parser(
        "inspect-sequential-run-state",
        help="Inspect sequential milestone run-state with read-only default and optional local state persistence.",
    )
    inspect_sequential_run_state_parser.add_argument("--parent-issue", type=int, required=True)
    inspect_sequential_run_state_parser.add_argument(
        "--sequential-run-state-path",
        help="Optional local sequential run-state path override (defaults to .aresforge/sequential-run-state.json).",
    )
    inspect_sequential_run_state_parser.add_argument(
        "--write-local-state",
        action="store_true",
        help="Explicitly persist the generated sequential run-state snapshot locally.",
    )
    plan_sequential_recovery_parser = subparsers.add_parser(
        "plan-sequential-run-recovery",
        help="Plan read-only recovery actions from persisted sequential run-state plus current repo/GitHub posture.",
    )
    plan_sequential_recovery_parser.add_argument("--parent-issue", type=int, required=True)
    plan_sequential_recovery_parser.add_argument(
        "--sequential-run-state-path",
        help="Optional local sequential run-state path override (defaults to .aresforge/sequential-run-state.json).",
    )
    sequential_handoff_parser = subparsers.add_parser(
        "generate-sequential-handoff-package",
        help="Generate a structured sequential execution handoff/evidence package with read-only default.",
    )
    sequential_handoff_parser.add_argument("--parent-issue", type=int, required=True)
    sequential_handoff_parser.add_argument("--issue", type=int, help="Optional single child issue scope.")
    sequential_handoff_parser.add_argument(
        "--write-package",
        action="store_true",
        help="Explicitly write local markdown/json package artifacts under evidence_dir.",
    )
    sequential_child_closeout_flow_parser = subparsers.add_parser(
        "run-sequential-child-closeout-flow",
        help="Plan dry-run default targeted child evidence comment plus child closeout with optional approved execution.",
    )
    sequential_child_closeout_flow_parser.add_argument("--parent-issue", type=int, required=True)
    sequential_child_closeout_flow_parser.add_argument("--child-issue", type=int, required=True)
    sequential_child_closeout_flow_parser.add_argument(
        "--comment-body",
        required=True,
        help="Evidence comment body to post to the target child issue when executing.",
    )
    sequential_child_closeout_flow_parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute targeted mutation steps. Without this flag, command runs in dry-run mode only.",
    )
    sequential_child_closeout_flow_parser.add_argument(
        "--approval-marker",
        help="Required for execute mode. Captured in audit-ready output.",
    )
    sequential_closeout_package_parser = subparsers.add_parser(
        "generate-sequential-closeout-execution-package",
        help="Generate read-only audit-backed evidence/comment/closeout package for one child issue.",
    )
    sequential_closeout_package_parser.add_argument("--parent-issue", type=int, required=True)
    sequential_closeout_package_parser.add_argument("--child-issue", type=int, required=True)
    sequential_closeout_package_parser.add_argument("--pr-url")
    sequential_closeout_package_parser.add_argument("--validation-result", action="append", default=[])
    closeout_planning_drift_parser = subparsers.add_parser(
        "inspect-closeout-planning-drift",
        help="Compare planned child issues against live closeout discovery without mutating local or GitHub state.",
    )
    closeout_planning_drift_parser.add_argument("--parent-issue", type=int, required=True)
    closeout_planning_drift_parser.add_argument(
        "--planning-state-path",
        help="Optional local planning state path override (defaults to .aresforge/planning-state.json).",
    )
    github_mutation_plan_parser = subparsers.add_parser(
        "plan-github-mutation",
        help="Plan one explicit GitHub mutation intent in dry-run mode without executing mutation.",
    )
    github_mutation_plan_parser.add_argument(
        "--mutation-type",
        required=True,
        choices=["issue_comment", "issue_close", "pr_body_update", "audit_log_write"],
    )
    github_mutation_plan_parser.add_argument(
        "--planned-action",
        required=True,
        help="Human-readable action description for this mutation intent.",
    )
    github_mutation_plan_parser.add_argument("--target-issue", type=int)
    github_mutation_plan_parser.add_argument("--target-pr", type=int)
    github_mutation_plan_parser.add_argument(
        "--approval-marker",
        help="Optional operator approval marker captured in audit metadata preview.",
    )
    issue_comment_executor_parser = subparsers.add_parser(
        "execute-github-issue-comment",
        help="Run targeted issue comment mutation with dry-run default and explicit execution approval gate.",
    )
    issue_comment_executor_parser.add_argument("--issue", type=int, required=True)
    comment_body_group = issue_comment_executor_parser.add_mutually_exclusive_group(required=True)
    comment_body_group.add_argument("--comment-body")
    comment_body_group.add_argument("--comment-file")
    issue_comment_executor_parser.add_argument("--parent-issue", type=int)
    issue_comment_executor_parser.add_argument(
        "--allow-parent-target",
        action="store_true",
        help="Explicitly permit targeting the parent issue number when --parent-issue matches --issue.",
    )
    issue_comment_executor_parser.add_argument(
        "--approval-marker",
        help="Required for execute mode. Captured in audit-ready output.",
    )
    issue_comment_executor_parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute comment mutation. Without this flag, command runs in dry-run mode only.",
    )
    issue_close_executor_parser = subparsers.add_parser(
        "execute-github-issue-close",
        help="Run targeted issue close mutation with dry-run default and readiness/approval gates.",
    )
    issue_close_executor_parser.add_argument(
        "--issue-target",
        required=True,
        help="Single issue number target as plain digits. Lists/ranges are not allowed.",
    )
    issue_close_executor_parser.add_argument("--parent-issue", type=int)
    issue_close_executor_parser.add_argument(
        "--approval-marker",
        help="Required for execute mode. Captured in audit-ready output.",
    )
    issue_close_executor_parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute issue close mutation. Without this flag, command runs in dry-run mode only.",
    )
    pr_body_helper_parser = subparsers.add_parser(
        "prepare-pr-body-update",
        help="Prepare or optionally execute a targeted PR body update with dry-run default.",
    )
    pr_body_helper_parser.add_argument("--pr-number", type=int, required=True)
    pr_body_helper_parser.add_argument("--target-issue", type=int)
    pr_body_helper_parser.add_argument("--scope-summary", required=True)
    pr_body_helper_parser.add_argument("--file-changed", action="append", default=[])
    pr_body_helper_parser.add_argument("--validation-result", action="append", default=[])
    pr_body_helper_parser.add_argument("--safety-note", action="append", default=[])
    pr_body_helper_parser.add_argument("--approval-marker")
    pr_body_helper_parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute PR body update. Without this flag, command runs in dry-run mode only.",
    )
    inspect_mutation_audit_log_parser = subparsers.add_parser(
        "inspect-github-mutation-audit-log",
        help="Inspect local-only GitHub mutation audit log entries in read-only mode.",
    )
    inspect_mutation_audit_log_parser.add_argument("--limit", type=int, default=20)
    subparsers.add_parser(
        "project-state-summary",
        help="Emit a local-first read-only project state summary with graceful degradation.",
    )
    subparsers.add_parser(
        "inspect-repo-governance",
        help="Inspect reusable label and milestone governance for the configured repository.",
    )
    assess_repo_parser = subparsers.add_parser(
        "assess-repo",
        help="Run local-only read-only repository architecture and file-role assessment.",
    )
    assess_repo_parser.add_argument(
        "--repo-path",
        help="Repository path to assess. Defaults to AppConfig repo_root.",
    )
    assess_repo_parser.add_argument(
        "--output",
        default="docs/audit",
        help="Output directory for assessment artifacts (default: docs/audit).",
    )
    assess_repo_parser.add_argument(
        "--format",
        choices=["json", "markdown", "both"],
        default="both",
        help="Output format (default: both).",
    )
    assess_repo_parser.add_argument(
        "--include-tests",
        type=parse_boolean_flag,
        default=True,
        help="Include tests/ files (true|false). Default true.",
    )
    assess_repo_parser.add_argument(
        "--include-docs",
        type=parse_boolean_flag,
        default=True,
        help="Include docs/ files (true|false). Default true.",
    )
    assess_repo_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite assessment outputs if they already exist.",
    )
    subparsers.add_parser(
        "inspect-evidence-bundle-automation-contract",
        help="Inspect read-only evidence bundle automation contract coverage and safety boundaries.",
    )
    subparsers.add_parser(
        "inspect-milestone-closeout-preflight-contract",
        help="Inspect read-only milestone closeout preflight contract coverage and safety boundaries.",
    )
    subparsers.add_parser(
        "inspect-canonical-evidence-marker-contract",
        help="Inspect canonical evidence marker contract coverage and safety boundaries.",
    )
    subparsers.add_parser(
        "inspect-automatic-canonical-evidence-emission-contract",
        help="Inspect M25 automatic canonical evidence emission contract coverage and safety boundaries.",
    )
    subparsers.add_parser(
        "inspect-repo-bootstrap-contract",
        help="Inspect reusable managed repository bootstrap contract readiness without mutation.",
    )
    subparsers.add_parser(
        "inspect-managed-repos",
        help="Inspect read-only managed repository registry posture across configured repositories.",
    )
    subparsers.add_parser(
        "managed-repo-readiness-report",
        help="Summarize read-only managed repository readiness for safe automation usage.",
    )
    subparsers.add_parser(
        "plan-repo-bootstrap",
        help="Generate a read-only deterministic bootstrap setup plan for managed repositories.",
    )
    subparsers.add_parser(
        "demo-managed-repo-governance",
        help="Run a deterministic read-only end-to-end managed repository governance demo.",
    )
    qa_review_parser = subparsers.add_parser(
        "qa-review-pr",
        help="Validate a pull request without mutating GitHub state.",
    )
    qa_review_parser.add_argument("--pr-number", type=int, required=True)
    qa_closeout_parser = subparsers.add_parser(
        "qa-closeout-pr",
        help="Run QA-gated PR merge and linked issue closeout with dry-run default.",
    )
    qa_closeout_parser.add_argument("--pr-number", type=int, required=True)
    closeout_mode = qa_closeout_parser.add_mutually_exclusive_group()
    closeout_mode.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate all closeout gates without mutating GitHub state (default mode).",
    )
    closeout_mode.add_argument(
        "--execute",
        action="store_true",
        help="Execute merge and issue closeout only when all gates pass.",
    )
    validate_end_to_end_parser = subparsers.add_parser(
        "validate-pr-end-to-end",
        help="Run end-to-end read-only PR validation orchestration without GitHub mutation.",
    )
    validate_end_to_end_parser.add_argument("--pr-number", type=int, required=True)
    inspect_review_parser = subparsers.add_parser(
        "inspect-review-package",
        help="Inspect one generated local review package under the configured review package root.",
    )
    inspect_review_parser.add_argument("--review-path", required=True)
    inspect_artifact_parser = subparsers.add_parser(
        "inspect-artifact",
        help="Inspect one generated local artifact under the configured artifact root.",
    )
    inspect_artifact_parser.add_argument("--artifact-path", required=True)
    inspect_evidence_parser = subparsers.add_parser(
        "inspect-evidence-package",
        help="Inspect one generated local evidence package under the configured evidence root.",
    )
    inspect_evidence_parser.add_argument("--evidence-path", required=True)
    subparsers.add_parser("list-projects", help="List registered projects.")
    subparsers.add_parser("list-agents", help="List registered agent roles.")
    subparsers.add_parser("list-models", help="List registered local model records.")
    inspect_model_parser = subparsers.add_parser(
        "inspect-model", help="Inspect one local model record with expanded metadata."
    )
    inspect_model_parser.add_argument("--model-id", required=True)
    subparsers.add_parser("list-queues", help="List known queues.")
    inspect_queue_parser = subparsers.add_parser(
        "inspect-queue", help="Inspect one queue with registry-aware metadata interpretation."
    )
    inspect_queue_parser.add_argument("--queue-id", required=True)
    inspect_queue_parser.add_argument(
        "--write-artifact",
        action="store_true",
        help="Write a local Markdown and JSON inspection report artifact while still emitting JSON.",
    )
    inspect_work_item_parser = subparsers.add_parser(
        "inspect-work-item", help="Inspect one work item with registry-aware queue context."
    )
    inspect_work_item_parser.add_argument("--work-item-id", required=True)
    inspect_work_item_parser.add_argument(
        "--write-artifact",
        action="store_true",
        help="Write a local Markdown and JSON inspection report artifact while still emitting JSON.",
    )

    create_work = subparsers.add_parser("create-work-item", help="Create a local work item.")
    create_work.add_argument("--title", required=True)
    create_work.add_argument("--description", default="")
    create_work.add_argument("--project-id", default=DEFAULT_PROJECT_ID)
    create_work.add_argument("--queue-id", required=True)
    create_work.add_argument("--status", default="queued")
    create_work.add_argument("--priority", default="normal")
    create_work.add_argument("--route-status", default="queued")
    create_work.add_argument("--agent-id", default=DEFAULT_AGENT_ID)
    create_work.add_argument("--model-id", default=DEFAULT_MODEL_ID)
    create_work.add_argument("--prompt-id")
    create_work.add_argument(
        "--metadata-json",
        default="{}",
        help="JSON object with additional work item metadata.",
    )
    create_work.add_argument(
        "--metadata",
        action="append",
        default=[],
        help="Additional metadata entries in key=value form. May be repeated.",
    )

    list_work = subparsers.add_parser("list-work-items", help="List work items.")
    list_work.add_argument("--status")

    prompt_parser = subparsers.add_parser(
        "generate-prompt-package",
        help="Generate a human-reviewable prompt package artifact.",
    )
    prompt_parser.add_argument("--title", required=True)
    prompt_parser.add_argument("--objective", required=True)
    prompt_parser.add_argument("--work-item-id")
    prompt_parser.add_argument("--queue-id", default="queue-planning")
    prompt_parser.add_argument("--agent-id", default=DEFAULT_AGENT_ID)
    prompt_parser.add_argument("--model-id", default=DEFAULT_MODEL_ID)
    prompt_parser.add_argument("--route-status", default="ready")
    prompt_parser.add_argument("--notes", default="")
    prompt_parser.add_argument("--store-db", action="store_true")

    evidence_parser = subparsers.add_parser(
        "record-evidence-package",
        help="Record evidence package metadata and write a local artifact.",
    )
    evidence_parser.add_argument("--title", required=True)
    evidence_parser.add_argument("--work-item-id")
    evidence_parser.add_argument("--files-changed", nargs="*", default=[])
    evidence_parser.add_argument("--validations-run", nargs="*", default=[])
    evidence_parser.add_argument("--skipped-checks", nargs="*", default=[])
    evidence_parser.add_argument("--protected-issue-checks", nargs="*", default=[])
    evidence_parser.add_argument(
        "--automation-boundary-confirmation",
        default="No autonomous GitHub or repository state changes were performed.",
    )
    evidence_parser.add_argument(
        "--include-artifact-discovery",
        action="store_true",
        help="Embed a deterministic local list-artifacts snapshot in the evidence package.",
    )
    evidence_parser.add_argument(
        "--include-latest-review-package",
        action="store_true",
        help="Embed a deterministic summary of the latest generated local review package.",
    )
    evidence_parser.add_argument("--store-db", action="store_true")

    ollama_parser = subparsers.add_parser("test-ollama", help="Inspect local Ollama health and visible models without generation.")
    ollama_parser.add_argument(
        "--prompt",
        default="Return one short sentence confirming that the local AresForge skeleton check reached Ollama.",
        help="Deprecated; ignored by the non-generative M84 health/model inspection.",
    )
    ollama_parser.add_argument(
        "--format",
        choices=["json"],
        default="json",
    )
    inspect_ollama_health_parser = subparsers.add_parser(
        "inspect-ollama-health",
        help="Inspect local Ollama health and visible models without invoking generation.",
    )
    inspect_ollama_health_parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="json",
    )

    handoff_parser = subparsers.add_parser(
        "prepare-codex-handoff",
        help="Generate a Codex handoff file without invoking Codex.",
    )
    handoff_parser.add_argument("--title", required=True)
    handoff_parser.add_argument("--summary", required=True)
    handoff_parser.add_argument("--requested-output", required=True)
    handoff_parser.add_argument("--work-item-id")
    handoff_parser.add_argument("--queue-id", default="queue-implementation")
    handoff_parser.add_argument("--agent-id", default=DEFAULT_AGENT_ID)
    handoff_parser.add_argument("--model-id", default=DEFAULT_MODEL_ID)
    handoff_parser.add_argument("--route-status", default="ready")
    handoff_parser.add_argument(
        "--include-latest-review-package",
        action="store_true",
        help="Embed a deterministic summary of the latest generated local review package.",
    )

    return parser


def emit_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, default=str))


def parse_metadata(raw_json: str) -> dict[str, Any]:
    value = json.loads(raw_json)
    if not isinstance(value, dict):
        raise ValueError("metadata-json must decode to a JSON object.")
    return value


def parse_metadata_pairs(items: list[str]) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for item in items:
        if "=" not in item:
            raise ValueError(f"metadata entries must use key=value form: {item}")
        key, value = item.split("=", 1)
        parsed[key.strip()] = value.strip()
    return parsed


def parse_json_object(raw_json: str) -> dict[str, Any]:
    candidates = [raw_json, raw_json.strip()]
    stripped = raw_json.strip()
    if len(stripped) >= 2 and stripped[0] == stripped[-1] and stripped[0] in ("'", '"'):
        candidates.append(stripped[1:-1])

    last_decode_error: json.JSONDecodeError | None = None
    decoded_non_object = False
    seen: set[str] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        try:
            value: Any = json.loads(candidate)
        except json.JSONDecodeError as exc:
            last_decode_error = exc
            continue

        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError as exc:
                last_decode_error = exc
                continue

        if isinstance(value, dict):
            return value
        decoded_non_object = True

    if decoded_non_object:
        raise ValueError("details must decode to a JSON object.")
    if last_decode_error is not None:
        raise last_decode_error
    raise ValueError("details must decode to a JSON object.")


def parse_details_json(raw: Any) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    if raw is None or raw == "":
        return {}, None
    if isinstance(raw, dict):
        return raw, None
    if not isinstance(raw, str):
        return None, {"ok": False, "error": "invalid_details_json"}
    try:
        parsed = parse_json_object(raw)
    except (ValueError, json.JSONDecodeError):
        return None, {"ok": False, "error": "invalid_details_json"}
    return parsed, None


def parse_details_input(
    details_json: str | None, details_file: str | None
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    if details_json and details_file:
        return None, {"ok": False, "error": "conflicting_details_input"}
    if details_json:
        return parse_details_json(details_json)
    if details_file:
        try:
            raw = Path(details_file).read_text(encoding="utf-8-sig")
        except OSError:
            return None, {"ok": False, "error": "details_file_not_readable"}
        return parse_details_json(raw)
    return {}, None


def parse_boolean_flag(raw_value: str) -> bool:
    normalized = raw_value.strip().lower()
    if normalized == 'true':
        return True
    if normalized == 'false':
        return False
    raise ValueError('expected true or false')


def command_requires_directories(args: argparse.Namespace) -> bool:
    if args.command == "validate-config":
        return True
    if args.command in (
        "generate-prompt-package",
        "record-evidence-package",
        "prepare-codex-handoff",
    ):
        return True
    if args.command == "run-local-review":
        return bool(getattr(args, "write_review_package", False))
    if args.command == "run-ready-issue-batch":
        return True
    if args.command in ("inspect-queue", "inspect-work-item"):
        return bool(getattr(args, "write_artifact", False))
    return False


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    config = AppConfig.from_env()
    if command_requires_directories(args):
        config.ensure_directories()

    if args.command == "validate-config":
        errors = config.validate()
        payload = {"ok": not errors, "errors": errors, "config": config.summary()}
        emit_json(payload)
        return 0 if not errors else 1

    if args.command == "validate-registries":
        report = validate_registry_seed_data()
        payload = {
            "ok": report.ok,
            "findings": [asdict(finding) for finding in report.findings],
        }
        emit_json(payload)
        has_error = any(finding.severity == "error" for finding in report.findings)
        return 1 if has_error else 0

    if args.command == "migrate":
        migrations_dir = config.repo_root / "migrations"
        if args.plan:
            with connect(config) as conn:
                pending = plan_migrations(conn, migrations_dir)
            emit_json({"pending_migrations": [item.path.name for item in pending]})
            return 0
        with connect(config) as conn:
            applied = apply_migrations(conn, migrations_dir)
            bootstrap_reference_data(conn, config)
        emit_json({"applied_migrations": applied, "bootstrap": "ok"})
        return 0

    if args.command == "init-roadmap-schema":
        migrations_dir = config.repo_root / "migrations"
        with connect(config) as conn:
            applied = apply_migrations(conn, migrations_dir)
            bootstrap_reference_data(conn, config)
        emit_json({"ok": True, "applied_migrations": applied, "bootstrap": "ok"})
        return 0

    if args.command == "seed-aresforge-roadmap":
        migrations_dir = config.repo_root / "migrations"
        with connect(config) as conn:
            applied = apply_migrations(conn, migrations_dir)
            bootstrap_reference_data(conn, config)
            seed_summary = seed_aresforge_roadmap(conn)
        emit_json(
            {
                "ok": True,
                "applied_migrations": applied,
                "bootstrap": "ok",
                "seed": seed_summary,
            }
        )
        return 0

    if args.command in (
        "update-roadmap-task-status",
        "update-roadmap-milestone-status",
        "update-roadmap-area-status",
        "add-roadmap-event",
        "create-work-item-from-roadmap-task",
        "update-work-item-status",
    ):
        details, details_error = parse_details_input(
            getattr(args, "details_json", None),
            getattr(args, "details_file", None),
        )
        if details_error is not None:
            emit_json(details_error)
            return 1
        assert details is not None
        migrations_dir = config.repo_root / "migrations"
        with connect(config) as conn:
            applied = apply_migrations(conn, migrations_dir)
            bootstrap_reference_data(conn, config)
            if args.command == "update-roadmap-task-status":
                payload = update_roadmap_task_status(
                    conn,
                    task_id=args.task_id,
                    status=args.status,
                    summary=args.summary,
                    details=details,
                )
            elif args.command == "update-roadmap-milestone-status":
                payload = update_roadmap_milestone_status(
                    conn,
                    milestone_id=args.milestone_id,
                    status=args.status,
                    summary=args.summary,
                    details=details,
                )
            elif args.command == "update-roadmap-area-status":
                payload = update_roadmap_area_status(
                    conn,
                    area_id=args.area_id,
                    status=args.status,
                    summary=args.summary,
                    details=details,
                )
            else:
                if args.command == "add-roadmap-event":
                    payload = add_roadmap_event(
                        conn,
                        project_id=args.project_id,
                        event_type=args.event_type,
                        summary=args.summary,
                        details=details,
                        area_id=args.area_id,
                        milestone_id=args.milestone_id,
                        task_id=args.task_id,
                    )
                else:
                    if args.command == "create-work-item-from-roadmap-task":
                        payload = create_work_item_from_roadmap_task(
                            conn,
                            roadmap_task_id=args.task_id,
                            queue_id=args.queue_id,
                            priority=args.priority,
                            summary=args.summary,
                            details=details,
                        )
                    else:
                        payload = update_work_item_status(
                            conn,
                            work_item_id=args.work_item_id,
                            status=args.status,
                            summary=args.summary,
                            details=details,
                        )
        emit_json({"ok": bool(payload.get("ok")), "applied_migrations": applied, "bootstrap": "ok", **payload})
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "inspect-roadmap-db":
        with connect(config) as conn:
            payload = inspect_roadmap_db(conn)
        if args.format == "markdown":
            print(render_roadmap_markdown(payload))
            return 0
        emit_json(payload)
        return 0

    if args.command == "inspect-roadmap-events":
        with connect(config) as conn:
            payload = inspect_roadmap_events(conn, project_id=args.project_id, limit=args.limit)
        if not bool(payload.get("ok")):
            emit_json(payload)
            return 1
        if args.format == "markdown":
            print(render_roadmap_events_markdown(payload))
            return 0
        emit_json(payload)
        return 0

    if args.command == "add-roadmap-task-dependency":
        details, details_error = parse_details_input(None, getattr(args, "details_file", None))
        if details_error is not None:
            emit_json(details_error)
            return 1
        assert details is not None
        with connect(config) as conn:
            payload = add_roadmap_task_dependency(
                conn,
                args.task_id,
                args.depends_on_task_id,
                dependency_type=args.dependency_type,
                actor=args.actor,
                details=details,
            )
        if args.format == "markdown":
            print(render_add_roadmap_task_dependency_markdown(payload))
            return 0 if bool(payload.get("ok")) else 1
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "remove-roadmap-task-dependency":
        details, details_error = parse_details_input(None, getattr(args, "details_file", None))
        if details_error is not None:
            emit_json(details_error)
            return 1
        assert details is not None
        with connect(config) as conn:
            payload = remove_roadmap_task_dependency(
                conn,
                args.task_id,
                args.depends_on_task_id,
                actor=args.actor,
                details=details,
            )
        if args.format == "markdown":
            print(render_remove_roadmap_task_dependency_markdown(payload))
            return 0 if bool(payload.get("ok")) else 1
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "inspect-roadmap-task-dependencies":
        with connect(config) as conn:
            payload = inspect_roadmap_task_dependencies(
                conn,
                task_id=args.task_id,
                project_id=args.project_id,
            )
        if args.format == "markdown":
            print(render_roadmap_task_dependencies_markdown(payload))
            return 0
        emit_json(payload)
        return 0

    if args.command == "inspect-roadmap-work-item-links":
        with connect(config) as conn:
            payload = inspect_roadmap_work_item_links(
                conn,
                project_id=args.project_id,
                roadmap_task_id=args.task_id,
                work_item_id=args.work_item_id,
            )
        if args.format == "markdown":
            print(render_roadmap_work_item_links_markdown(payload))
            return 0
        emit_json(payload)
        return 0

    if args.command == "inspect-work-item-lifecycle":
        with connect(config) as conn:
            payload = inspect_work_item_lifecycle(conn, args.work_item_id)
        if not bool(payload.get("ok")):
            emit_json(payload)
            return 1
        if args.format == "markdown":
            print(render_work_item_lifecycle_markdown(payload))
            return 0
        emit_json(payload)
        return 0

    if args.command == "build-work-item-execution-dossier":
        with connect(config) as conn:
            payload = build_work_item_execution_dossier(conn, args.work_item_id)
        if args.format == "markdown":
            print(render_work_item_execution_dossier_markdown(payload))
            return 0 if bool(payload.get("ok")) else 1
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "export-work-item-operator-prompt":
        with connect(config) as conn:
            payload = export_work_item_operator_prompt(
                conn,
                args.work_item_id,
                args.output,
                force=bool(args.force),
            )
        if args.format == "markdown":
            print(render_export_work_item_operator_prompt_markdown(payload))
            return 0 if bool(payload.get("ok")) else 1
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "archive-work-item-operator-packet":
        with connect(config) as conn:
            payload = archive_work_item_operator_packet(
                conn,
                args.work_item_id,
                args.output_dir,
                actor=args.actor,
                force=bool(args.force),
            )
        if args.format == "markdown":
            print(render_archive_work_item_operator_packet_markdown(payload))
            return 0 if bool(payload.get("ok")) else 1
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "recommend-next-work-item-action":
        with connect(config) as conn:
            payload = recommend_next_work_item_action(conn, args.work_item_id)
        if args.format == "markdown":
            print(render_next_work_item_action_recommendation_markdown(payload))
            return 0 if bool(payload.get("ok")) else 1
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "inspect-queue-work-state":
        with connect(config) as conn:
            payload = inspect_queue_work_state(
                conn,
                queue_id=args.queue_id,
                project_id=args.project_id,
            )
        if args.format == "markdown":
            print(render_queue_work_state_markdown(payload))
            return 0
        emit_json(payload)
        return 0

    if args.command == "inspect-work-item-readiness":
        with connect(config) as conn:
            payload = inspect_work_item_readiness(conn, args.work_item_id)
        if args.format == "markdown":
            print(render_work_item_readiness_markdown(payload))
            return 0
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "start-work-item":
        details, details_error = parse_details_input(None, getattr(args, "details_file", None))
        if details_error is not None:
            emit_json(details_error)
            return 1
        assert details is not None
        with connect(config) as conn:
            payload = start_work_item_if_ready(
                conn,
                args.work_item_id,
                actor=args.actor,
                details=details,
            )
        if args.format == "markdown":
            print(render_start_work_item_markdown(payload))
            return 0 if bool(payload.get("ok")) else 1
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "complete-work-item-if-ready":
        details, details_error = parse_details_input(None, getattr(args, "details_file", None))
        if details_error is not None:
            emit_json(details_error)
            return 1
        assert details is not None
        with connect(config) as conn:
            payload = complete_work_item_if_ready(
                conn,
                args.work_item_id,
                actor=args.actor,
                details=details,
            )
        if args.format == "markdown":
            print(render_work_item_completion_markdown(payload))
            return 0 if bool(payload.get("ok")) else 1
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "plan-work-item-queue-transition":
        with connect(config) as conn:
            payload = plan_work_item_queue_transition(
                conn,
                args.work_item_id,
                args.target_queue_id,
            )
        if args.format == "markdown":
            print(render_work_item_queue_transition_plan_markdown(payload))
            return 0 if bool(payload.get("ok")) else 1
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "move-work-item-queue":
        details, details_error = parse_details_input(None, getattr(args, "details_file", None))
        if details_error is not None:
            emit_json(details_error)
            return 1
        assert details is not None
        with connect(config) as conn:
            payload = move_work_item_queue_if_allowed(
                conn,
                args.work_item_id,
                args.target_queue_id,
                actor=args.actor,
                details=details,
            )
        if args.format == "markdown":
            print(render_move_work_item_queue_markdown(payload))
            return 0 if bool(payload.get("ok")) else 1
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "request-work-item-queue-approval":
        details, details_error = parse_details_input(None, getattr(args, "details_file", None))
        if details_error is not None:
            emit_json(details_error)
            return 1
        assert details is not None
        with connect(config) as conn:
            payload = request_work_item_queue_approval(
                conn,
                work_item_id=args.work_item_id,
                target_queue_id=args.target_queue_id,
                actor=args.actor,
                details=details,
            )
        if args.format == "markdown":
            print(render_work_item_queue_approval_markdown(payload))
            return 0 if bool(payload.get("ok")) else 1
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "approve-work-item-queue-approval":
        details, details_error = parse_details_input(None, getattr(args, "details_file", None))
        if details_error is not None:
            emit_json(details_error)
            return 1
        assert details is not None
        with connect(config) as conn:
            payload = approve_work_item_queue_approval(
                conn,
                work_item_id=args.work_item_id,
                target_queue_id=args.target_queue_id,
                actor=args.actor,
                details=details,
            )
        if args.format == "markdown":
            print(render_work_item_queue_approval_markdown(payload))
            return 0 if bool(payload.get("ok")) else 1
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "inspect-work-item-queue-approval":
        with connect(config) as conn:
            payload = inspect_work_item_queue_approval_state(
                conn,
                work_item_id=args.work_item_id,
                target_queue_id=args.target_queue_id,
            )
        if args.format == "markdown":
            print(render_work_item_queue_approval_markdown(payload))
            return 0 if bool(payload.get("ok")) else 1
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "handoff-work-item-to-implementation":
        details, details_error = parse_details_input(None, getattr(args, "details_file", None))
        if details_error is not None:
            emit_json(details_error)
            return 1
        assert details is not None
        with connect(config) as conn:
            payload = handoff_work_item_to_implementation(
                conn,
                args.work_item_id,
                actor=args.actor,
                details=details,
            )
        if args.format == "markdown":
            print(render_implementation_handoff_markdown(payload))
            return 0 if bool(payload.get("ok")) else 1
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "inspect-queue-readiness":
        with connect(config) as conn:
            payload = inspect_queue_readiness(
                conn,
                queue_id=args.queue_id,
                project_id=args.project_id,
            )
        if args.format == "markdown":
            print(render_queue_readiness_markdown(payload))
            return 0
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "inspect-project-queue-dashboard":
        with connect(config) as conn:
            payload = inspect_project_queue_dashboard(conn, project_id=args.project_id)
        if args.format == "markdown":
            print(render_project_queue_dashboard_markdown(payload))
            return 0 if bool(payload.get("ok")) else 1
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "inspect-db-state":
        with connect(config) as conn:
            emit_json(inspect_state(conn))
        return 0

    if args.command == "inspect-project":
        with connect(config) as conn:
            project_record = inspect_project(conn, args.project_id)
        if project_record is None:
            emit_json(
                {"ok": False, "error": "project_not_found", "project_id": args.project_id}
            )
            return 1
        emit_json({"ok": True, "project": project_record})
        return 0

    if args.command == "inspect-registries":
        payload = inspect_local_registries(config.repo_root)
        emit_json(payload)
        return 0 if payload["ok"] else 1

    if args.command == "list-artifacts":
        emit_json(discover_local_artifacts(config))
        return 0

    if args.command == "list-review-packages":
        emit_json(discover_local_review_packages(config))
        return 0

    if args.command == "run-local-review":
        payload = run_local_review(
            config,
            options=LocalReviewOptions(
                project_id=args.project_id,
                model_id=args.model_id,
                include_artifacts=args.include_artifacts,
                artifact_path=args.artifact_path,
                include_evidence_packages=args.include_evidence_packages,
                evidence_path=args.evidence_path,
                write_review_package=args.write_review_package,
            ),
        )
        emit_json(payload)
        return 0 if payload["ok"] else 1

    if args.command == "list-evidence-packages":
        emit_json(discover_local_evidence_packages(config))
        return 0

    if args.command == "list-ready-issues":
        emit_json(list_ready_issues(config))
        return 0

    if args.command == "inspect-ready-issue":
        emit_json(inspect_ready_issue(config, args.issue_number))
        return 0

    if args.command == "plan-ready-issue":
        emit_json(plan_ready_issue(config, args.issue_number))
        return 0

    if args.command == "run-ready-issue-pipeline":
        if args.execute_closeout and not args.closeout_when_eligible:
            emit_json(
                {
                    "command": "run-ready-issue-pipeline",
                    "ok": False,
                    "error": "execute_closeout_requires_closeout_mode",
                    "failed_gates": ["invalid_mode_combination"],
                }
            )
            return 1

        mode = MODE_PLAN_ONLY
        if args.review_pr:
            mode = MODE_REVIEW_PR
        elif args.closeout_when_eligible:
            mode = MODE_CLOSEOUT_WHEN_ELIGIBLE

        payload = run_ready_issue_pipeline(
            config,
            issue_number=args.issue_number,
            pr_number=args.pr_number,
            mode=mode,
            execute_closeout=bool(args.execute_closeout),
            write_review_package=bool(args.write_review_package),
            write_evidence_package=bool(args.write_evidence_package),
            write_implementation_handoff=bool(args.write_implementation_handoff),
        )
        emit_json(payload)
        return 0 if not payload["failed_gates"] else 1

    if args.command == "run-ready-issue-batch":
        if not bool(args.plan_only):
            emit_json(
                {
                    "command": "run-ready-issue-batch",
                    "ok": False,
                    "error": "plan_only_required",
                    "failed_gates": ["missing_plan_only_flag"],
                }
            )
            return 1
        payload = run_ready_issue_batch(
            config,
            plan_only=True,
            write_selected_handoffs=bool(args.write_selected_handoffs),
            timestamp_override=args.timestamp_override,
        )
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "automation-readiness-report":
        emit_json(automation_readiness_report(config))
        return 0

    if args.command == "plan-agent-queue":
        emit_json(
            plan_agent_queue(
                config,
                issue_numbers=args.issue_number,
                issues_file=args.issues_file,
            )
        )
        return 0

    if args.command == "report-batch-readiness":
        emit_json(
            report_batch_readiness(
                config,
                issue_numbers=args.issue_number,
                issues_file=args.issues_file,
                changed_files=args.changed_file,
                validations=args.validation,
                pr_number=args.pr_number,
            )
        )
        return 0

    if args.command == "plan-batch-closeout":
        payload = plan_batch_closeout(
            config,
            parent_issue=args.parent_issue,
            write_planning_snapshot=bool(args.write_planning_snapshot),
            planning_state_path=args.planning_state_path,
        )
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "generate-sprint-issue-script":
        payload = generate_sprint_issue_script(
            definition_path=args.definition,
            output_path=args.output,
            write_planning_state=bool(args.write_planning_state),
            planning_state_path=args.planning_state_path,
            repo_root=config.repo_root,
        )
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "plan-sprint-issues":
        payload = plan_sprint_issues(definition_path=args.definition)
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "plan-self-managed-milestone":
        if args.mode == "local-write":
            with connect(config) as conn:
                payload = plan_self_managed_milestone(config, mode=args.mode, conn=conn)
        else:
            payload = plan_self_managed_milestone(config, mode=args.mode)
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "inspect-self-managed-milestone-execution-contract":
        payload = inspect_self_managed_milestone_execution_contract(config)
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "simulate-self-managed-milestone-execution":
        payload = simulate_self_managed_milestone_execution(config, parent_issue=args.parent_issue)
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "generate-self-managed-milestone-handoff":
        payload = generate_self_managed_milestone_handoff(
            config,
            parent_issue=args.parent_issue,
            completed_child=args.completed_child,
            next_child=args.next_child,
            pr_url=args.pr_url,
            validation_results=list(args.validation_result),
            evidence_comment_url=args.evidence_comment_url,
            warning=list(args.warning),
        )
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "generate-self-managed-issue-script":
        if args.run_id is not None:
            with connect(config) as conn:
                payload = generate_self_managed_issue_script(
                    config,
                    mode=args.mode,
                    run_id=args.run_id,
                    target_issue=args.target_issue,
                    conn=conn,
                )
        else:
            payload = generate_self_managed_issue_script(
                config,
                mode=args.mode,
                run_id=None,
                target_issue=args.target_issue,
                conn=None,
            )
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "generate-child-closeout-script":
        payload = generate_child_closeout_script(config, issue_number=args.issue)
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "generate-child-closeout-evidence-bundle":
        payload = generate_child_closeout_evidence_bundle(
            config,
            parent_issue=args.parent_issue,
            child_issue=args.child_issue,
        )
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "generate-child-evidence-marker-template":
        payload = generate_child_evidence_marker_template(
            config,
            parent_issue=args.parent_issue,
            child_issue=args.child_issue,
        )
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "generate-parent-closeout-evidence-bundle":
        payload = generate_parent_closeout_evidence_bundle(
            config,
            parent_issue=args.parent_issue,
            state_file=args.state_file,
        )
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "generate-parent-closeout-marker-template":
        payload = generate_parent_closeout_marker_template(
            config,
            parent_issue=args.parent_issue,
        )
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "generate-pr-evidence-bundle":
        payload = generate_pr_evidence_bundle(
            config,
            issue_number=args.issue,
            pr_number=args.pr,
        )
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "generate-pr-evidence-marker-template":
        payload = generate_pr_evidence_marker_template(
            config,
            issue_number=args.issue,
            pr_number=args.pr,
        )
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "simulate-evidence-bundle-generation":
        payload = simulate_evidence_bundle_generation(
            config,
            parent_issue=args.parent_issue,
        )
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "generate-evidence-comment-template":
        payload = generate_evidence_comment_template(config, issue_number=args.issue)
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "run-autonomous-cycle":
        with connect(config) as conn:
            payload = run_autonomous_cycle(
                config,
                conn=conn,
                mode=args.mode,
                parent_issue=args.parent_issue,
                target_issue=args.target_issue,
                title=args.title,
                branch_name=args.branch_name,
                commit_message=args.commit_message,
                pr_title=args.pr_title,
                pr_body=args.pr_body,
                validation_commands=args.validation_command,
                allow_empty_commit=bool(args.allow_empty_commit),
            )
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "inspect-autonomous-run":
        with connect(config) as conn:
            payload = inspect_autonomous_run(conn, run_id=args.run_id)
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "inspect-milestone-state":
        payload = inspect_milestone_state(
            config,
            parent_issue=args.parent_issue,
            state_file=args.state_file,
        )
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "plan-milestone-execution-queue":
        payload = plan_milestone_execution_queue(config, parent_issue=args.parent_issue)
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "check-issue-evidence-readiness":
        payload = check_issue_evidence_readiness(config, issue_number=args.issue)
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "check-milestone-evidence-readiness":
        payload = check_milestone_evidence_readiness(
            config,
            parent_issue=args.parent_issue,
            state_file=args.state_file,
        )
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "plan-milestone-final-reconciliation":
        payload = plan_milestone_final_reconciliation(config, parent_issue=args.parent_issue)
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "inspect-milestone-dashboard":
        payload = inspect_milestone_dashboard(config, parent_issue=args.parent_issue)
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "inspect-parent-closeout-readiness":
        payload = inspect_parent_closeout_readiness(
            config,
            parent_issue=args.parent_issue,
            state_file=args.state_file,
        )
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "inspect-parent-child-linkage-preflight":
        payload = inspect_parent_child_linkage_preflight(config, parent_issue=args.parent_issue)
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "inspect-child-evidence-marker-preflight":
        payload = inspect_child_evidence_marker_preflight(config, parent_issue=args.parent_issue)
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "inspect-pr-mapping-preflight":
        payload = inspect_pr_mapping_preflight(config, parent_issue=args.parent_issue)
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "generate-closeout-preflight-repair-guidance":
        payload = generate_closeout_preflight_repair_guidance(config, parent_issue=args.parent_issue)
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "inspect-milestone-closeout-preflight":
        payload = inspect_milestone_closeout_preflight(config, parent_issue=args.parent_issue)
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "check-closeout-readiness-by-construction":
        payload = check_closeout_readiness_by_construction(
            config,
            parent_issue=args.parent_issue,
            state_file=args.state_file,
        )
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "generate-offline-closeout-state-template":
        payload = generate_offline_closeout_state_template(
            config,
            parent_issue=args.parent_issue,
            children=args.children,
            output=args.output,
            parent_title=args.parent_title,
            milestone_title=args.milestone_title,
            final_main_head=args.final_main_head,
            final_validation_results=args.final_validation_results,
            force=bool(args.force),
        )
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "generate-handoff-package":
        payload = generate_handoff_package(
            config,
            output=args.output,
            output_format=args.format,
            include_doc_excerpts=bool(args.include_doc_excerpts),
            force=bool(args.force),
        )
        if bool(payload.get("ok")) and not bool(payload.get("wrote_output_file")):
            print(payload["stdout"])
            return 0
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "generate-safe-dispatch-handoff":
        payload = generate_safe_dispatch_handoff(
            config,
            project_id=args.project_id,
            queue_path=args.queue_path,
            registry_path=args.registry_path,
            artifact_root=args.artifact_root,
            approval_path=args.approval_path,
            output=args.output,
            force=bool(args.force),
            output_format=args.format,
        )
        if bool(payload.get("ok")) and not bool(payload.get("wrote_output_file")):
            print(payload["stdout"])
            return 0
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "plan-doc-reconciliation":
        payload = generate_doc_reconciliation_plan(
            config,
            output=args.output,
            output_format=args.format,
            include_git_state=bool(args.include_git_state),
            force=bool(args.force),
        )
        if bool(payload.get("ok")) and not bool(payload.get("wrote_output_file")):
            print(payload["stdout"])
            return 0
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "plan-github-sync":
        payload = generate_github_sync_plan(
            config,
            state_file=args.state_file,
            project_state=args.project_state,
            output=args.output,
            output_format=args.format,
            force=bool(args.force),
        )
        if bool(payload.get("ok")) and not bool(payload.get("wrote_output_file")):
            print(payload["stdout"])
            return 0
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "plan-github-issue-sync":
        payload = plan_github_issue_sync(
            config,
            project_id=args.project_id,
            item_id=args.item_id,
            queue_path=args.queue_path,
            output=args.output,
            force=bool(args.force),
            output_format=args.format,
        )
        if "stdout" in payload:
            print(payload["stdout"])
            return 0 if bool(payload.get("ok")) else 1
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "create-github-issue-for-safe-queue-item":
        payload = create_github_issue_for_safe_queue_item(
            config,
            item_id=args.item_id,
            project_id=args.project_id,
            queue_path=args.queue_path,
            dry_run=bool(args.dry_run) or not bool(args.github_enabled),
            github_enabled=bool(args.github_enabled),
            autonomy_profile=args.autonomy_profile,
            repo=args.repo,
            output=args.output,
            force=bool(args.force),
            output_format=args.format,
        )
        if "stdout" in payload:
            print(payload["stdout"])
            return 0 if bool(payload.get("ok")) else 1
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "generate-local-milestone-template":
        payload = generate_local_milestone_template(
            config,
            milestone_id=args.milestone_id,
            output=args.output,
            title=args.title,
            force=bool(args.force),
        )
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "inspect-local-milestone":
        payload = inspect_local_milestone(
            config,
            definition=args.definition,
            output_format=args.format,
        )
        if bool(payload.get("ok")) and not bool(payload.get("wrote_output_file")):
            print(payload["stdout"])
            return 0
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "check-local-milestone-readiness":
        payload = check_local_milestone_readiness(
            config,
            definition=args.definition,
            project_state=args.project_state,
            output_format=args.format,
        )
        if bool(payload.get("ok")) and not bool(payload.get("wrote_output_file")):
            print(payload["stdout"])
            return 0
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "generate-local-milestone-closeout":
        payload = generate_local_milestone_closeout(
            config,
            definition=args.definition,
            output=args.output,
            output_format=args.format,
            force=bool(args.force),
        )
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "init-project-state":
        payload = init_project_state(
            config,
            path=args.path,
            force=bool(args.force),
        )
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "inspect-project-state":
        payload = inspect_local_project_state(config, path=args.path)
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "update-project-state":
        payload = update_project_state(
            config,
            path=args.path,
            current_milestone=args.current_milestone,
            current_phase=args.current_phase,
            current_mode=args.current_mode,
            validation_status=args.validation_status,
            documentation_status=args.documentation_status,
            warnings_to_add=list(args.warning),
        )
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "append-operation-log":
        details: dict[str, Any] | None = None
        if args.details is not None:
            try:
                details = parse_json_object(args.details)
            except ValueError as exc:
                emit_json(
                    {
                        "ok": False,
                        "local_only": True,
                        "error": "invalid_details_json",
                        "details": {"message": str(exc)},
                    }
                )
                return 1
        payload = append_operation_log(
            config,
            state_path=args.state_path,
            event_type=args.event_type,
            summary=args.summary,
            details=details,
        )
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "inspect-operation-log":
        payload = inspect_operation_log(
            config,
            state_path=args.state_path,
            limit=args.limit,
        )
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "init-managed-project-registry":
        payload = init_managed_project_registry(
            config,
            path=args.path,
            force=bool(args.force),
        )
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "register-managed-project":
        payload = register_managed_project(
            config,
            project_id=args.project_id,
            name=args.name,
            root_path=args.root_path,
            registry_path=args.registry_path,
            description=args.description,
            status=args.status,
            default_branch=args.default_branch,
            github_url=args.github_url,
            github_owner=args.github_owner,
            github_repo=args.github_repo,
            github_default_branch=args.github_default_branch,
            primary_repo_id=args.primary_repo_id,
            tags=list(args.tag),
            notes=args.notes,
        )
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "register-managed-repo":
        payload = register_managed_repo(
            config,
            project_id=args.project_id,
            repo_id=args.repo_id,
            name=args.name,
            path=args.path,
            registry_path=args.registry_path,
            remote_url=args.remote_url,
            default_branch=args.default_branch,
            github_url=args.github_url,
            github_owner=args.github_owner,
            github_repo=args.github_repo,
            github_default_branch=args.github_default_branch,
            inspect_local_git=bool(args.inspect_local_git),
            role=args.role,
            status=args.status,
            tags=list(args.tag),
            notes=args.notes,
        )
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "inspect-managed-project-registry":
        payload = inspect_managed_project_registry(
            config,
            registry_path=args.registry_path,
            output_format=args.format,
        )
        if bool(payload.get("ok")) and not bool(payload.get("wrote_output_file")):
            print(payload["stdout"])
            return 0
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "inspect-managed-project":
        payload = inspect_managed_project(
            config,
            project_id=args.project_id,
            registry_path=args.registry_path,
            output_format=args.format,
        )
        if bool(payload.get("ok")) and not bool(payload.get("wrote_output_file")):
            print(payload["stdout"])
            return 0
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "inspect-managed-repo":
        payload = inspect_managed_repo(
            config,
            project_id=args.project_id,
            repo_id=args.repo_id,
            registry_path=args.registry_path,
            output_format=args.format,
        )
        if bool(payload.get("ok")) and not bool(payload.get("wrote_output_file")):
            print(payload["stdout"])
            return 0
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "inspect-managed-repo-github-link":
        payload = inspect_managed_repo_github_link(
            config,
            project_id=args.project_id,
            repo_id=args.repo_id,
            registry_path=args.registry_path,
            inspect_local_git=bool(args.inspect_local_git),
            output_format=args.format,
        )
        if bool(payload.get("ok")) and not bool(payload.get("wrote_output_file")):
            print(payload["stdout"])
            return 0
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "seed-aresforge-self-project":
        payload = seed_aresforge_self_project(
            config,
            project_id=args.project_id,
            repo_id=args.repo_id,
            root_path=args.root_path,
            queue_path=args.queue_path,
            registry_path=args.registry_path,
            set_active=bool(args.set_active),
            seed_next_milestones=bool(args.seed_next_milestones),
            force_update=bool(args.force_update),
        )
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "init-project-queue":
        payload = init_project_queue(
            config,
            path=args.path,
            force=bool(args.force),
        )
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "add-queue-item":
        payload = add_queue_item(
            config,
            item_id=args.item_id,
            project_id=args.project_id,
            repo_id=args.repo_id,
            title=args.title,
            queue_path=args.queue_path,
            registry_path=args.registry_path,
            description=args.description,
            status=args.status,
            priority=args.priority,
            item_type=args.type,
            tags=list(args.tag),
            dependencies=list(args.depends_on),
            blocked_by=list(args.blocked_by),
            assigned_agent=args.assigned_agent,
            source=args.source,
            notes=args.notes,
        )
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "add-local-queue-item":
        payload = add_local_queue_item(
            config,
            title=args.title,
            description=args.description,
            project_id=args.project_id,
            repo_id=args.repo_id,
            queue_path=args.queue_path,
            registry_path=args.registry_path,
            priority=args.priority,
            item_type=args.type,
            assigned_agent=args.assigned_agent,
            target_area=args.target_area,
            acceptance_criteria=list(args.acceptance_criteria),
            dependencies=list(args.depends_on),
            tags=list(args.tags),
        )
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "update-queue-item":
        payload = update_queue_item(
            config,
            item_id=args.item_id,
            queue_path=args.queue_path,
            project_id=args.project_id,
            repo_id=args.repo_id,
            status=args.status,
            priority=args.priority,
            item_type=args.type,
            title=args.title,
            description=args.description,
            tags=list(args.tag) if args.tag is not None else None,
            dependencies=list(args.depends_on) if args.depends_on is not None else None,
            blocked_by=list(args.blocked_by) if args.blocked_by is not None else None,
            assigned_agent=args.assigned_agent,
            source=args.source,
            notes=args.notes,
        )
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "inspect-project-queue":
        payload = inspect_project_queue(
            config,
            queue_path=args.queue_path,
            project_id=args.project_id,
            repo_id=args.repo_id,
            status=args.status,
            item_type=args.type,
            assigned_agent=args.assigned_agent,
            output_format=args.format,
        )
        if bool(payload.get("ok")) and not bool(payload.get("wrote_output_file")):
            print(payload["stdout"])
            return 0
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "inspect-queue-consistency":
        payload = inspect_queue_consistency(
            config,
            queue_path=args.queue_path,
            project_id=args.project_id,
            repo_id=args.repo_id,
            output_format=args.format,
        )
        if bool(payload.get("ok")) and not bool(payload.get("wrote_output_file")):
            print(payload["stdout"])
            return 0
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "inspect-queue-item":
        payload = inspect_queue_item(
            config,
            item_id=args.item_id,
            queue_path=args.queue_path,
            output_format=args.format,
        )
        if bool(payload.get("ok")) and not bool(payload.get("wrote_output_file")):
            print(payload["stdout"])
            return 0
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "inspect-local-queue-item-readiness":
        payload = inspect_local_queue_item_readiness(
            config,
            item_id=args.item_id,
            queue_path=args.queue_path,
            registry_path=args.registry_path,
        )
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "start-local-queue-item":
        payload = start_local_queue_item(
            config,
            item_id=args.item_id,
            queue_path=args.queue_path,
            registry_path=args.registry_path,
        )
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "complete-local-queue-item":
        payload = complete_local_queue_item(
            config,
            item_id=args.item_id,
            commit_hash=args.commit_hash,
            validation_summary=args.validation_summary,
            evidence_note=args.evidence_note,
            tests_run=list(args.tests_run),
            changed_files=list(args.changed_files),
            artifact_paths=list(args.artifact_path),
            completed_by=args.completed_by,
            queue_path=args.queue_path,
        )
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "generate-local-queue-item-codex-prompt":
        payload = generate_local_queue_item_codex_prompt(
            config,
            item_id=args.item_id,
            queue_path=args.queue_path,
            registry_path=args.registry_path,
            output=args.output,
            force=bool(args.force),
            commit_message=args.commit_message,
        )
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "inspect-codex-dispatch-contract":
        payload = inspect_codex_dispatch_contract(
            config,
            item_id=args.item_id,
            queue_path=args.queue_path,
            registry_path=args.registry_path,
            output_format=args.format,
        )
        if bool(payload.get("ok")) and not bool(payload.get("wrote_output_file")):
            print(payload["stdout"])
            return 0
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "prepare-codex-dispatch-dry-run":
        payload = prepare_codex_dispatch_dry_run(
            config,
            item_id=args.item_id,
            queue_path=args.queue_path,
            registry_path=args.registry_path,
            output=args.output,
            force=bool(args.force),
            output_format=args.format,
        )
        if bool(payload.get("ok")) and not bool(payload.get("wrote_output_file")):
            print(payload["stdout"])
            return 0
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "prepare-queue-item-dispatch":
        payload = prepare_queue_item_dispatch(
            config,
            item_id=args.item_id,
            target=args.target,
            queue_path=args.queue_path,
            registry_path=args.registry_path,
            output=args.output,
            start_if_ready=bool(args.start_if_ready),
            force=bool(args.force),
            output_format=args.format,
        )
        if bool(payload.get("ok")) and not bool(payload.get("wrote_output_file")):
            print(payload["stdout"])
            return 0
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "inspect-queue-dispatch-plan":
        payload = inspect_queue_agent_dispatch_plan(
            config,
            item_id=args.item_id,
            queue_path=args.queue_path,
            registry_path=args.registry_path,
            output_format=args.format,
        )
        if bool(payload.get("ok")) and not bool(payload.get("wrote_output_file")):
            print(payload["stdout"])
            return 0
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "generate-codex-dispatch-artifact":
        payload = generate_codex_prompt_dispatch_artifact(
            config,
            item_id=args.item_id,
            queue_path=args.queue_path,
            registry_path=args.registry_path,
            output=args.output,
            force=bool(args.force),
            output_format=args.format,
        )
        if "stdout" in payload:
            print(payload["stdout"])
            return 0 if bool(payload.get("ok")) else 1
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "validate-local-llm-advisory-dry-run":
        payload = validate_local_llm_advisory_dry_run(
            config,
            item_id=args.item_id,
            queue_path=args.queue_path,
            registry_path=args.registry_path,
            output=args.output,
            force=bool(args.force),
            output_format=args.format,
        )
        if "stdout" in payload:
            print(payload["stdout"])
            return 0 if bool(payload.get("ok")) else 1
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "generate-local-llm-advisory-artifact":
        payload = generate_local_llm_advisory_artifact(
            config,
            item_id=args.item_id,
            queue_path=args.queue_path,
            registry_path=args.registry_path,
            output=args.output,
            force=bool(args.force),
            output_format=args.format,
            model_profile=args.model_profile,
            reasoning_scope=args.reasoning_scope,
        )
        if "stdout" in payload:
            print(payload["stdout"])
            return 0 if bool(payload.get("ok")) else 1
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "run-local-llm-advisory":
        payload = run_local_llm_advisory_execution(
            config,
            item_id=args.item_id,
            artifact_path=args.artifact_path,
            provider=args.provider,
            model=args.model,
            queue_path=args.queue_path,
            dry_run=bool(args.dry_run),
            output=args.output,
            force=bool(args.force),
            timeout_seconds=args.timeout_seconds,
            output_format=args.format,
        )
        if "stdout" in payload:
            print(payload["stdout"])
            return 0 if bool(payload.get("ok")) else 1
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "validate-documentation-agent-dry-run":
        payload = validate_documentation_agent_dry_run(
            config,
            item_id=args.item_id,
            queue_path=args.queue_path,
            registry_path=args.registry_path,
            output=args.output,
            force=bool(args.force),
            output_format=args.format,
        )
        if "stdout" in payload:
            print(payload["stdout"])
            return 0 if bool(payload.get("ok")) else 1
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "generate-doc-agent-patch-proposal":
        payload = generate_documentation_agent_patch_proposal(
            config,
            item_id=args.item_id,
            queue_path=args.queue_path,
            output=args.output,
            force=bool(args.force),
            include_roadmap=bool(args.include_roadmap),
            include_context=bool(args.include_context),
            include_operator_docs=bool(args.include_operator_docs),
            output_format=args.format,
        )
        if "stdout" in payload:
            print(payload["stdout"])
            return 0 if bool(payload.get("ok")) else 1
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "recommend-agent-route":
        payload = recommend_agent_route(
            config,
            item_id=args.item_id,
            queue_path=args.queue_path,
            output=args.output,
            force=bool(args.force),
            output_format=args.format,
        )
        if "stdout" in payload:
            print(payload["stdout"])
            return 0 if bool(payload.get("ok")) else 1
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "create-dispatch-approval-gate":
        payload = create_dispatch_approval_gate(
            config,
            item_id=args.item_id,
            artifact_type=args.artifact_type,
            artifact_path=args.artifact_path,
            dispatch_lane=args.dispatch_lane,
            reviewer=args.reviewer,
            review_notes=args.review_notes,
            checklist=list(args.checklist or []),
            approval_path=args.approval_path,
            queue_path=args.queue_path,
            registry_path=args.registry_path,
            output_format=args.format,
        )
        if "stdout" in payload:
            print(payload["stdout"])
            return 0 if bool(payload.get("ok")) else 1
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "inspect-dispatch-approval-gate":
        payload = inspect_dispatch_approval_gate(
            config,
            approval_id=args.approval_id,
            item_id=args.item_id,
            approval_path=args.approval_path,
            limit=args.limit,
            output_format=args.format,
        )
        if "stdout" in payload:
            print(payload["stdout"])
            return 0 if bool(payload.get("ok")) else 1
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "update-dispatch-approval-gate":
        payload = update_dispatch_approval_gate(
            config,
            approval_id=args.approval_id,
            status=args.status,
            reviewer=args.reviewer,
            review_notes=args.review_notes,
            checklist=list(args.checklist or []) if args.checklist else None,
            approval_path=args.approval_path,
            output_format=args.format,
        )
        if "stdout" in payload:
            print(payload["stdout"])
            return 0 if bool(payload.get("ok")) else 1
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "inspect-dispatch-artifacts":
        payload = inspect_dispatch_artifacts(
            config,
            project_id=args.project_id,
            artifact_root=args.artifact_root,
            approval_path=args.approval_path,
            output_format=args.format,
        )
        if "stdout" in payload:
            print(payload["stdout"])
            return 0 if bool(payload.get("ok")) else 1
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "inspect-artifact-registry":
        payload = inspect_artifact_registry(
            config,
            project_id=args.project_id,
            item_id=args.item_id,
            artifact_type=args.artifact_type,
            output=args.output,
            force=bool(args.force),
            output_format=args.format,
        )
        if "stdout" in payload:
            print(payload["stdout"])
            return 0 if bool(payload.get("ok")) else 1
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "inspect-approval-ledger":
        payload = inspect_approval_ledger(
            config,
            project_id=args.project_id,
            item_id=args.item_id,
            artifact_path=args.artifact_path,
            output=args.output,
            force=args.force,
            output_format=args.format,
        )
        if bool(payload.get("ok")) and not bool(payload.get("wrote_output_file")):
            print(payload["stdout"])
            return 0
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "inspect-queue-transaction-log":
        payload = inspect_queue_transaction_log(
            config,
            project_id=args.project_id,
            item_id=args.item_id,
            output=args.output,
            force=args.force,
            output_format=args.format,
        )
        if bool(payload.get("ok")) and not bool(payload.get("wrote_output_file")):
            print(payload["stdout"])
            return 0
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "record-artifact-review":
        payload = record_artifact_review(
            config,
            item_id=args.item_id,
            artifact_path=args.artifact_path,
            decision=args.decision,
            reviewer=args.reviewer,
            review_notes=args.review_notes,
            output=args.output,
            force=args.force,
            output_format=args.format,
        )
        if bool(payload.get("ok")) and not bool(payload.get("wrote_output_file")):
            print(payload["stdout"])
            return 0
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "prepare-manual-codex-dispatch":
        payload = prepare_manual_codex_dispatch(
            config,
            item_id=args.item_id,
            artifact_path=args.artifact_path,
            approval_id=args.approval_id,
            queue_path=args.queue_path,
            registry_path=args.registry_path,
            artifact_root=args.artifact_root,
            approval_path=args.approval_path,
            output=args.output,
            force=bool(args.force),
            output_format=args.format,
        )
        if "stdout" in payload:
            print(payload["stdout"])
            return 0 if bool(payload.get("ok")) else 1
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "intake-patch-proposal":
        payload = intake_patch_proposal(
            config,
            item_id=args.item_id,
            patch_artifact=args.patch_artifact,
            approval_id=args.approval_id,
            queue_path=args.queue_path,
            approval_path=args.approval_path,
            output=args.output,
            force=bool(args.force),
            output_format=args.format,
        )
        if "stdout" in payload:
            print(payload["stdout"])
            return 0 if bool(payload.get("ok")) else 1
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "parse-dispatch-result-evidence":
        payload = parse_dispatch_result_evidence(
            config,
            item_id=args.item_id,
            result_path=args.result_path,
            queue_path=args.queue_path,
            output=args.output,
            force=bool(args.force),
            output_format=args.format,
        )
        if "stdout" in payload:
            print(payload["stdout"])
            return 0 if bool(payload.get("ok")) else 1
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "recommend-queue-completion":
        payload = recommend_queue_completion(
            config,
            item_id=args.item_id,
            evidence_path=args.evidence_path,
            queue_path=args.queue_path,
            output=args.output,
            force=bool(args.force),
            output_format=args.format,
        )
        if "stdout" in payload:
            print(payload["stdout"])
            return 0 if bool(payload.get("ok")) else 1
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "inspect-agent-registry":
        payload = inspect_agent_registry(
            config,
            agent_id=args.agent_id,
            safety_class=args.safety_class,
            autonomy_level=args.autonomy_level,
            output=args.output,
            force=bool(args.force),
            output_format=args.format,
        )
        if "stdout" in payload:
            print(payload["stdout"])
            return 0 if bool(payload.get("ok")) else 1
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "recommend-llm-decision":
        payload = recommend_llm_decision(
            config,
            item_id=args.item_id,
            agent_id=args.agent_id,
            task_type=args.task_type,
            risk_level=args.risk_level,
            mutation_scope=args.mutation_scope,
            queue_path=args.queue_path,
            output=args.output,
            force=bool(args.force),
            output_format=args.format,
        )
        if "stdout" in payload:
            print(payload["stdout"])
            return 0 if bool(payload.get("ok")) else 1
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "build-agent-orchestration-plan":
        payload = build_agent_orchestration_plan(
            config,
            item_id=args.item_id,
            agent_id=args.agent_id,
            execution_target=args.execution_target,
            queue_path=args.queue_path,
            output=args.output,
            force=bool(args.force),
            output_format=args.format,
        )
        if "stdout" in payload:
            print(payload["stdout"])
            return 0 if bool(payload.get("ok")) else 1
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "run-agent-dry-run":
        payload = run_single_agent_dry_run(
            config,
            agent_id=args.agent_id,
            item_id=args.item_id,
            plan_path=args.plan_path,
            queue_path=args.queue_path,
            output=args.output,
            force=bool(args.force),
            output_format=args.format,
        )
        if "stdout" in payload:
            print(payload["stdout"])
            return 0 if bool(payload.get("ok")) else 1
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "run-agent":
        payload = run_single_agent_real_execution(
            config,
            agent_id=args.agent_id,
            item_id=args.item_id,
            queue_path=args.queue_path,
            output=args.output,
            force=bool(args.force),
            require_machine_gates=bool(args.require_machine_gates),
            output_format=args.format,
        )
        if "stdout" in payload:
            print(payload["stdout"])
            return 0 if bool(payload.get("ok")) else 1
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "evaluate-machine-safety-gates":
        payload = evaluate_machine_safety_gates(
            config,
            item_id=args.item_id,
            gate_profile=args.gate_profile,
            artifact_path=args.artifact_path,
            patch_path=args.patch_path,
            execution_record=args.execution_record,
            queue_path=args.queue_path,
            output=args.output,
            force=bool(args.force),
            output_format=args.format,
        )
        if "stdout" in payload:
            print(payload["stdout"])
            return 0 if bool(payload.get("ok")) else 1
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "auto-complete-safe-queue-item":
        payload = auto_complete_safe_queue_item(
            config,
            item_id=args.item_id,
            evidence_path=args.evidence_path,
            gate_profile=args.gate_profile,
            queue_path=args.queue_path,
            dry_run=bool(args.dry_run),
            force=bool(args.force),
            output=args.output,
            output_format=args.format,
        )
        if "stdout" in payload:
            print(payload["stdout"])
            return 0 if bool(payload.get("ok")) else 1
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "apply-docs-only-patch":
        payload = apply_docs_only_patch(
            config,
            item_id=args.item_id,
            patch_path=args.patch_path,
            queue_path=args.queue_path,
            dry_run=bool(args.dry_run),
            force=bool(args.force),
            output=args.output,
            output_format=args.format,
        )
        if "stdout" in payload:
            print(payload["stdout"])
            return 0 if bool(payload.get("ok")) else 1
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "probe-local-ollama-provider":
        payload = probe_local_ollama_provider(
            config,
            output=args.output,
            force=bool(args.force),
            no_network=bool(args.no_network),
            config_path=args.config,
            output_format=args.format,
        )
        if "stdout" in payload:
            print(payload["stdout"])
            return 0 if bool(payload.get("ok")) else 1
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "inspect-llm-decision-matrix":
        payload = inspect_llm_decision_matrix(
            config,
            item_id=args.item_id,
            queue_path=args.queue_path,
            registry_path=args.registry_path,
            output_format=args.format,
        )
        if bool(payload.get("ok")) and not bool(payload.get("wrote_output_file")):
            print(payload["stdout"])
            return 0
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "inspect-local-llm-advisory-lane-readiness":
        payload = inspect_local_llm_advisory_lane_readiness(
            config,
            item_id=args.item_id,
            queue_path=args.queue_path,
            registry_path=args.registry_path,
            output_format=args.format,
        )
        if bool(payload.get("ok")) and not bool(payload.get("wrote_output_file")):
            print(payload["stdout"])
            return 0
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "inspect-local-llm-provider-contract":
        payload = inspect_local_llm_provider_contract(config, output_format=args.format)
        if bool(payload.get("ok")) and not bool(payload.get("wrote_output_file")):
            print(payload["stdout"])
            return 0
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "prepare-local-llm-advisory-run":
        payload = prepare_local_llm_advisory_run_artifact(
            config,
            item_id=args.item_id,
            queue_path=args.queue_path,
            registry_path=args.registry_path,
            model=args.model,
            run=bool(args.run),
            run_id=args.run_id,
            output_format=args.format,
            force=bool(args.force),
        )
        if bool(payload.get("ok")) and not bool(payload.get("wrote_output_file")):
            print(payload["stdout"])
            return 0
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "prepare-local-coding-draft":
        payload = prepare_local_coding_draft_artifact(
            config,
            item_id=args.item_id,
            queue_path=args.queue_path,
            registry_path=args.registry_path,
            model=args.model,
            run=bool(args.run),
            run_id=args.run_id,
            output_format=args.format,
            force=bool(args.force),
        )
        if bool(payload.get("ok")) and not bool(payload.get("wrote_output_file")):
            print(payload["stdout"])
            return 0
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "inspect-human-gated-patch-application-contract":
        payload = inspect_human_gated_patch_application_contract(config, output_format=args.format)
        if bool(payload.get("ok")) and not bool(payload.get("wrote_output_file")):
            print(payload["stdout"])
            return 0
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "inspect-model-usage-report":
        payload = inspect_model_usage_report(config, output=args.output, output_format=args.format)
        if bool(payload.get("ok")) and not bool(payload.get("wrote_output_file")):
            print(payload["stdout"])
            return 0
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "inspect-sprint-batch-report":
        payload = inspect_sprint_batch_report(
            config,
            since_commit=args.since_commit,
            commit_count=args.commit_count,
            output=args.output,
            output_format=args.format,
        )
        if bool(payload.get("ok")) and not bool(payload.get("wrote_output_file")):
            print(payload["stdout"])
            return 0
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "plan-operator-batch":
        payload = plan_operator_batch(
            config,
            project_id=args.project_id,
            queue_path=args.queue_path,
            registry_path=args.registry_path,
            limit=args.limit,
            output_format=args.format,
        )
        if bool(payload.get("ok")) and not bool(payload.get("wrote_output_file")):
            print(payload["stdout"])
            return 0
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "plan-operator-batch-v2":
        payload = plan_operator_batch_v2(
            config,
            project_id=args.project_id,
            queue_path=args.queue_path,
            registry_path=args.registry_path,
            approval_path=args.approval_path,
            limit=args.limit,
            include_blocked=args.include_blocked,
            output=args.output,
            force=args.force,
            output_format=args.format,
        )
        if bool(payload.get("ok")) and not bool(payload.get("wrote_output_file")):
            print(payload["stdout"])
            return 0
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "inspect-documentation-agent-contract":
        payload = inspect_documentation_agent_contract(config, output_format=args.format)
        if bool(payload.get("ok")) and not bool(payload.get("wrote_output_file")):
            print(payload["stdout"])
            return 0
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "inspect-agent-runtime-boundary":
        payload = inspect_agent_runtime_boundary(config, output_format=args.format)
        if bool(payload.get("ok")) and not bool(payload.get("wrote_output_file")):
            print(payload["stdout"])
            return 0
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "run-single-ready-codex-queue-item":
        payload = run_single_ready_codex_queue_item(
            config,
            item_id=args.item_id,
            queue_path=args.queue_path,
            registry_path=args.registry_path,
            prompt_output=args.prompt_output,
            force_prompt=bool(args.force_prompt),
            approved_by=args.approved_by,
            approval_phrase=args.approval_phrase,
            run_id=args.run_id,
            command=args.command_arg or args.codex_command,
            timeout_seconds=args.timeout_seconds,
            validation_commands=list(args.validation_command),
            implementation_commit_message=args.implementation_commit_message,
            queue_evidence_commit_message=args.queue_evidence_commit_message,
            closed_by=args.closed_by,
            output_format=args.format,
        )
        if bool(payload.get("ok")) and not bool(payload.get("wrote_output_file")):
            print(payload["stdout"])
            return 0
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "approve-codex-dispatch":
        payload = approve_codex_dispatch(
            config,
            item_id=args.item_id,
            approved_by=args.approved_by,
            approval_phrase=args.approval_phrase,
            queue_path=args.queue_path,
            registry_path=args.registry_path,
            run_id=args.run_id,
            output_format=args.format,
        )
        if bool(payload.get("ok")) and not bool(payload.get("wrote_output_file")):
            print(payload["stdout"])
            return 0
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "run-codex-dispatch":
        if args.artifact_path:
            payload = run_codex_dispatch_executor(
                config,
                item_id=args.item_id,
                artifact_path=args.artifact_path,
                dry_run=bool(args.dry_run),
                force=bool(args.force),
                output=args.output,
                timeout_seconds=args.timeout_seconds,
                require_clean_worktree=bool(args.require_clean_worktree),
                execution_enabled=bool(args.execution_enabled),
                queue_path=args.queue_path,
                output_format=args.format,
            )
        elif args.run_id:
            payload = run_operator_gated_codex_dispatch(
                config,
                item_id=args.item_id,
                run_id=args.run_id,
                command=args.command_arg or args.codex_command,
                timeout_seconds=args.timeout_seconds,
                output_format=args.format,
            )
        else:
            payload = {
                "command": "run-codex-dispatch",
                "ok": False,
                "local_only": True,
                "error": "codex_dispatch_target_required",
                "details": {
                    "message": "Provide --artifact-path for M135 dispatch execution or --run-id for the legacy M78 run path."
                },
            }
        if args.artifact_path and "stdout" in payload:
            print(payload["stdout"])
            return 0 if bool(payload.get("ok")) else 1
        if bool(payload.get("ok")) and not bool(payload.get("wrote_output_file")):
            print(payload["stdout"])
            return 0
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "ingest-codex-result-and-validate":
        payload = ingest_codex_result_and_validate(
            config,
            item_id=args.item_id,
            execution_record=args.execution_record,
            validation_profile=args.validation_profile,
            dry_run=bool(args.dry_run),
            queue_path=args.queue_path,
            output=args.output,
            force=bool(args.force),
            output_format=args.format,
        )
        if "stdout" in payload:
            print(payload["stdout"])
            return 0 if bool(payload.get("ok")) else 1
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "run-github-sync-agent":
        payload = run_github_sync_agent(
            config,
            item_id=args.item_id,
            sync_mode=args.sync_mode,
            dry_run=bool(args.dry_run),
            github_enabled=bool(args.github_enabled),
            repo=args.repo,
            issue_number=args.issue_number,
            pr_number=args.pr_number,
            artifact_path=args.artifact_path,
            queue_path=args.queue_path,
            output=args.output,
            force=bool(args.force),
            output_format=args.format,
        )
        if "stdout" in payload:
            print(payload["stdout"])
            return 0 if bool(payload.get("ok")) else 1
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "run-agent-orchestration":
        payload = run_multi_agent_orchestration(
            config,
            item_id=args.item_id,
            plan_path=args.plan_path,
            dry_run=bool(args.dry_run),
            max_steps=args.max_steps,
            allow_low_risk_real=bool(args.allow_low_risk_real),
            allow_local_llm=bool(args.allow_local_llm),
            allow_codex=bool(args.allow_codex),
            allow_github_sync=bool(args.allow_github_sync),
            queue_path=args.queue_path,
            output=args.output,
            force=bool(args.force),
            output_format=args.format,
        )
        if "stdout" in payload:
            print(payload["stdout"])
            return 0 if bool(payload.get("ok")) else 1
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "generate-autonomous-sprint-closeout":
        payload = generate_autonomous_sprint_closeout(
            config,
            project_id=args.project_id,
            sprint_start=args.sprint_start,
            sprint_end=args.sprint_end,
            dry_run=bool(args.dry_run),
            apply_docs_only=bool(args.apply_docs_only),
            queue_path=args.queue_path,
            output=args.output,
            force=bool(args.force),
            output_format=args.format,
        )
        if "stdout" in payload:
            print(payload["stdout"])
            return 0 if bool(payload.get("ok")) else 1
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "generate-autonomy-readiness-report":
        payload = generate_autonomy_readiness_report(
            config,
            project_id=args.project_id,
            sprint_start=args.sprint_start,
            sprint_end=args.sprint_end,
            item_id=args.item_id,
            queue_path=args.queue_path,
            output=args.output,
            force=bool(args.force),
            output_format=args.format,
        )
        if "stdout" in payload:
            print(payload["stdout"])
            return 0 if bool(payload.get("ok")) else 1
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "inspect-orchestrator-state-machine":
        payload = inspect_orchestrator_state_machine(
            config,
            item_id=args.item_id,
            project_id=args.project_id,
            queue_path=args.queue_path,
            output=args.output,
            force=bool(args.force),
            output_format=args.format,
        )
        if "stdout" in payload:
            print(payload["stdout"])
            return 0 if bool(payload.get("ok")) else 1
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "inspect-orchestration-run-history":
        payload = inspect_orchestration_run_history(
            config,
            project_id=args.project_id,
            item_id=args.item_id,
            run_id=args.run_id,
            queue_path=args.queue_path,
            history_path=args.history_path,
            artifacts_root=args.artifacts_root,
            output=args.output,
            force=bool(args.force),
            output_format=args.format,
        )
        if "stdout" in payload:
            print(payload["stdout"])
            return 0 if bool(payload.get("ok")) else 1
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "inspect-orchestration-run-store":
        payload = inspect_orchestration_run_store(
            config,
            project_id=args.project_id,
            item_id=args.item_id,
            run_id=args.run_id,
            history_path=args.history_path,
            queue_path=args.queue_path,
            output=args.output,
            force=bool(args.force),
            output_format=args.format,
        )
        if "stdout" in payload:
            print(payload["stdout"])
            return 0 if bool(payload.get("ok")) else 1
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "inspect-orchestration-resume-plan":
        payload = inspect_orchestration_resume_plan(
            config,
            run_id=args.run_id,
            item_id=args.item_id,
            project_id=args.project_id,
            queue_path=args.queue_path,
            history_path=args.history_path,
            artifacts_root=args.artifacts_root,
            output=args.output,
            force=bool(args.force),
            output_format=args.format,
        )
        if "stdout" in payload:
            print(payload["stdout"])
            return 0 if bool(payload.get("ok")) else 1
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "inspect-orchestration-run-monitor":
        payload = inspect_orchestration_run_monitor(
            config,
            project_id=args.project_id,
            item_id=args.item_id,
            run_id=args.run_id,
            queue_path=args.queue_path,
            history_path=args.history_path,
            artifacts_root=args.artifacts_root,
            output=args.output,
            force=bool(args.force),
            output_format=args.format,
        )
        if "stdout" in payload:
            print(payload["stdout"])
            return 0 if bool(payload.get("ok")) else 1
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "inspect-orchestration-artifact-retention":
        payload = inspect_orchestration_artifact_retention(
            config,
            project_id=args.project_id,
            item_id=args.item_id,
            history_path=args.history_path,
            queue_path=args.queue_path,
            output=args.output,
            force=bool(args.force),
            output_format=args.format,
        )
        if "stdout" in payload:
            print(payload["stdout"])
            return 0 if bool(payload.get("ok")) else 1
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "replay-orchestration-run":
        payload = replay_orchestration_run(
            config,
            run_id=args.run_id,
            project_id=args.project_id,
            item_id=args.item_id,
            dry_run=bool(args.dry_run),
            history_path=args.history_path,
            artifacts_root=args.artifacts_root,
            queue_path=args.queue_path,
            output=args.output,
            force=bool(args.force),
            output_format=args.format,
        )
        if "stdout" in payload:
            print(payload["stdout"])
            return 0 if bool(payload.get("ok")) else 1
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "inspect-autonomy-profile":
        payload = inspect_autonomy_profile(
            config,
            project_id=args.project_id,
            item_id=args.item_id,
            autonomy_profile=args.autonomy_profile,
            queue_path=args.queue_path,
            output=args.output,
            force=bool(args.force),
            output_format=args.format,
        )
        if "stdout" in payload:
            print(payload["stdout"])
            return 0 if bool(payload.get("ok")) else 1
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "inspect-codex-execution-enablements":
        payload = inspect_codex_execution_enablements(
            config,
            item_id=args.item_id,
            project_id=args.project_id,
            queue_path=args.queue_path,
            output=args.output,
            force=bool(args.force),
            output_format=args.format,
        )
        if "stdout" in payload:
            print(payload["stdout"])
            return 0 if bool(payload.get("ok")) else 1
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "inspect-codex-worktree-guard":
        payload = inspect_codex_worktree_guard(
            config,
            item_id=args.item_id,
            project_id=args.project_id,
            queue_path=args.queue_path,
            output=args.output,
            force=bool(args.force),
            output_format=args.format,
        )
        if "stdout" in payload:
            print(payload["stdout"])
            return 0 if bool(payload.get("ok")) else 1
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "inspect-codex-validation-profiles":
        payload = inspect_codex_validation_profiles(
            config,
            item_id=args.item_id,
            project_id=args.project_id,
            queue_path=args.queue_path,
            task_type=args.task_type,
            risk_class=args.risk_class,
            changed_paths=args.changed_path,
            output=args.output,
            force=bool(args.force),
            output_format=args.format,
        )
        if "stdout" in payload:
            print(payload["stdout"])
            return 0 if bool(payload.get("ok")) else 1
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "classify-codex-failure":
        payload = classify_codex_failure(
            config,
            failure_artifact=args.failure_artifact,
            item_id=args.item_id,
            project_id=args.project_id,
            queue_path=args.queue_path,
            output=args.output,
            force=bool(args.force),
            output_format=args.format,
        )
        if "stdout" in payload:
            print(payload["stdout"])
            return 0 if bool(payload.get("ok")) else 1
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "normalize-agent-step-result":
        payload = normalize_agent_step_result(
            config,
            result_path=args.result_path,
            item_id=args.item_id,
            project_id=args.project_id,
            queue_path=args.queue_path,
            output=args.output,
            force=bool(args.force),
            output_format=args.format,
        )
        if "stdout" in payload:
            print(payload["stdout"])
            return 0 if bool(payload.get("ok")) else 1
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "classify-source-patch-risk":
        payload = classify_source_patch_risk(
            config,
            patch_path=args.patch_path,
            item_id=args.item_id,
            project_id=args.project_id,
            queue_path=args.queue_path,
            output=args.output,
            force=bool(args.force),
            output_format=args.format,
        )
        if "stdout" in payload:
            print(payload["stdout"])
            return 0 if bool(payload.get("ok")) else 1
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "plan-source-patch-apply":
        payload = plan_source_patch_apply(
            config,
            patch_path=args.patch_path,
            item_id=args.item_id,
            project_id=args.project_id,
            queue_path=args.queue_path,
            output=args.output,
            force=bool(args.force),
            output_format=args.format,
        )
        if "stdout" in payload:
            print(payload["stdout"])
            return 0 if bool(payload.get("ok")) else 1
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "dry-run-source-patch-apply":
        payload = dry_run_source_patch_apply(
            config,
            patch_path=args.patch_path,
            item_id=args.item_id,
            project_id=args.project_id,
            queue_path=args.queue_path,
            output=args.output,
            force=bool(args.force),
            output_format=args.format,
        )
        if "stdout" in payload:
            print(payload["stdout"])
            return 0 if bool(payload.get("ok")) else 1
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "preflight-real-codex-execution":
        payload = preflight_real_codex_execution(
            config,
            item_id=args.item_id,
            project_id=args.project_id,
            dry_run=bool(args.dry_run),
            autonomy_profile=args.autonomy_profile,
            validation_profile=args.validation_profile,
            changed_paths=args.changed_path,
            queue_path=args.queue_path,
            history_path=args.history_path,
            output=args.output,
            force=bool(args.force),
            output_format=args.format,
        )
        if "stdout" in payload:
            print(payload["stdout"])
            return 0 if bool(payload.get("ok")) else 1
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "prepare-low-risk-codex-pilot":
        payload = prepare_low_risk_codex_pilot(
            config,
            item_id=args.item_id,
            project_id=args.project_id,
            dry_run=bool(args.dry_run) or not bool(args.execution_enabled),
            execution_enabled=bool(args.execution_enabled),
            allow_low_risk_code=bool(args.allow_low_risk_code),
            autonomy_profile=args.autonomy_profile,
            validation_profile=args.validation_profile,
            changed_paths=args.changed_path,
            codex_command=args.codex_command_arg or None,
            timeout_seconds=args.timeout_seconds,
            queue_path=args.queue_path,
            history_path=args.history_path,
            output=args.output,
            force=bool(args.force),
            output_format=args.format,
        )
        if "stdout" in payload:
            print(payload["stdout"])
            return 0 if bool(payload.get("ok")) else 1
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "bundle-codex-loop-validation-evidence":
        payload = bundle_codex_loop_validation_evidence(
            config,
            item_id=args.item_id,
            project_id=args.project_id,
            dry_run=bool(args.dry_run),
            autonomy_profile=args.autonomy_profile,
            validation_profile=args.validation_profile,
            changed_paths=args.changed_path,
            patch_path=args.patch_path,
            queue_path=args.queue_path,
            output=args.output,
            force=bool(args.force),
            output_format=args.format,
        )
        if "stdout" in payload:
            print(payload["stdout"])
            return 0 if bool(payload.get("ok")) else 1
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "run-end-to-end-codex-loop":
        payload = run_end_to_end_codex_loop_dry_run(
            config,
            item_id=args.item_id,
            project_id=args.project_id,
            dry_run=bool(args.dry_run),
            execution_enabled=bool(args.execution_enabled),
            allow_low_risk_code=bool(args.allow_low_risk_code),
            codex_command=args.codex_command_arg or None,
            changed_paths=args.changed_path,
            timeout_seconds=args.timeout_seconds,
            validation_profile=args.validation_profile,
            queue_path=args.queue_path,
            output=args.output,
            force=bool(args.force),
            output_format=args.format,
        )
        if "stdout" in payload:
            print(payload["stdout"])
            return 0 if bool(payload.get("ok")) else 1
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "inspect-codex-dispatch-run":
        payload = inspect_codex_dispatch_run(
            config,
            run_id=args.run_id,
            output_format=args.format,
        )
        if bool(payload.get("ok")) and not bool(payload.get("wrote_output_file")):
            print(payload["stdout"])
            return 0
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "list-codex-dispatch-runs":
        payload = list_codex_dispatch_runs(config, output_format=args.format)
        if bool(payload.get("ok")) and not bool(payload.get("wrote_output_file")):
            print(payload["stdout"])
            return 0
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "cancel-codex-dispatch-run":
        payload = cancel_codex_dispatch_run(
            config,
            run_id=args.run_id,
            output_format=args.format,
        )
        if bool(payload.get("ok")) and not bool(payload.get("wrote_output_file")):
            print(payload["stdout"])
            return 0
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "recover-codex-dispatch-run":
        payload = recover_codex_dispatch_run(
            config,
            run_id=args.run_id,
            recovery_note=args.recovery_note,
            output_format=args.format,
        )
        if bool(payload.get("ok")) and not bool(payload.get("wrote_output_file")):
            print(payload["stdout"])
            return 0
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "inspect-local-project-dashboard":
        emit_json(summarize_local_project_dashboard(config))
        return 0

    if args.command == "list-local-projects":
        emit_json(list_local_projects(config))
        return 0

    if args.command == "inspect-local-project-readiness":
        payload = inspect_local_project_readiness(config, project_id=args.project_id)
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "inspect-local-queue-agent-summary":
        emit_json(inspect_local_queue_agent_summary(config))
        return 0

    if args.command == "inspect-local-project-report":
        emit_json(inspect_local_project_report(config))
        return 0

    if args.command == "inspect-self-managed-project":
        payload = inspect_self_managed_project(
            config,
            project_id=args.project_id,
            output_format=args.format,
        )
        if bool(payload.get("ok")) and not bool(payload.get("wrote_output_file")):
            print(payload["stdout"])
            return 0
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "init-agent-profiles":
        payload = init_agent_profiles(
            config,
            path=args.path,
            force=bool(args.force),
            with_defaults=bool(args.with_defaults),
        )
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "register-agent-profile":
        escalation_allowed: bool | None = None
        if args.escalation_allowed is not None:
            try:
                escalation_allowed = parse_boolean_flag(args.escalation_allowed)
            except ValueError:
                emit_json(
                    {
                        "ok": False,
                        "local_only": True,
                        "error": "invalid_escalation_allowed",
                        "details": {
                            "value": args.escalation_allowed,
                            "message": "--escalation-allowed must be true or false.",
                        },
                    }
                )
                return 1

        payload = register_agent_profile(
            config,
            agent_id=args.agent_id,
            name=args.name,
            role=args.role,
            profiles_path=args.profiles_path,
            description=args.description,
            execution_mode=args.execution_mode,
            model_preference=args.model_preference,
            strengths=list(args.strength),
            constraints=list(args.constraint),
            allowed_item_types=list(args.allowed_type),
            escalation_allowed=escalation_allowed,
            handoff_target_id=args.handoff_target_id,
            status=args.status,
            tags=list(args.tag),
            notes=args.notes,
        )
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "register-handoff-target":
        payload = register_handoff_target(
            config,
            target_id=args.target_id,
            name=args.name,
            target_type=args.target_type,
            profiles_path=args.profiles_path,
            description=args.description,
            local_command=args.local_command,
            input_format=args.input_format,
            output_format=args.output_format,
            safety_notes=list(args.safety_note),
            status=args.status,
            tags=list(args.tag),
            notes=args.notes,
        )
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "inspect-agent-profiles":
        payload = inspect_agent_profiles(
            config,
            profiles_path=args.profiles_path,
            role=args.role,
            execution_mode=args.execution_mode,
            status=args.status,
            output_format=args.format,
        )
        if bool(payload.get("ok")) and not bool(payload.get("wrote_output_file")):
            print(payload["stdout"])
            return 0
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "inspect-agent-profile":
        payload = inspect_agent_profile(
            config,
            agent_id=args.agent_id,
            profiles_path=args.profiles_path,
            output_format=args.format,
        )
        if bool(payload.get("ok")) and not bool(payload.get("wrote_output_file")):
            print(payload["stdout"])
            return 0
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "inspect-handoff-target":
        payload = inspect_handoff_target(
            config,
            target_id=args.target_id,
            profiles_path=args.profiles_path,
            output_format=args.format,
        )
        if bool(payload.get("ok")) and not bool(payload.get("wrote_output_file")):
            print(payload["stdout"])
            return 0
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "plan-agent-orchestration":
        payload = generate_agent_orchestration_plan(
            config,
            project_id=args.project_id,
            repo_id=args.repo_id,
            status=args.status,
            queue_path=args.queue_path,
            profiles_path=args.profiles_path,
            registry_path=args.registry_path,
            output=args.output,
            output_format=args.format,
            force=bool(args.force),
        )
        if bool(payload.get("ok")) and not bool(payload.get("wrote_output_file")):
            print(payload["stdout"])
            return 0
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "plan-llm-escalation":
        payload = generate_llm_escalation_plan(
            config,
            item_id=args.item_id,
            project_id=args.project_id,
            repo_id=args.repo_id,
            status=args.status,
            queue_path=args.queue_path,
            profiles_path=args.profiles_path,
            orchestration_plan=args.orchestration_plan,
            output=args.output,
            output_format=args.format,
            force=bool(args.force),
        )
        if bool(payload.get("ok")) and not bool(payload.get("wrote_output_file")):
            print(payload["stdout"])
            return 0
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "inspect-bootstrap-status":
        payload = inspect_bootstrap_status(
            config,
            repo_path=args.repo_path,
        )
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "plan-bootstrap":
        payload = plan_bootstrap(
            config,
            repo_path=args.repo_path,
            seed_sample_work=bool(args.seed_sample_work),
            output_format=args.format,
        )
        if bool(payload.get("ok")) and not bool(payload.get("wrote_output_file")):
            print(payload["stdout"])
            return 0
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "apply-bootstrap":
        payload = apply_bootstrap(
            config,
            repo_path=args.repo_path,
            force=bool(args.force),
            seed_sample_work=bool(args.seed_sample_work),
            output_format=args.format,
        )
        if bool(payload.get("ok")) and not bool(payload.get("wrote_output_file")):
            print(payload["stdout"])
            return 0
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "serve-hub":
        payload = serve_hub(
            config,
            host=args.host,
            port=args.port,
            open_browser=bool(args.open_browser),
        )
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "generate-preflight-baseline-snapshot":
        payload = generate_preflight_baseline_snapshot(
            config,
            parent_issue=args.parent_issue,
            output_path=args.output,
        )
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "diff-preflight-snapshots":
        payload = diff_preflight_snapshots(before_path=args.before, after_path=args.after)
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "inspect-child-execution-gates":
        payload = inspect_child_execution_gates(
            config,
            issue_number=args.issue,
            parent_issue=args.parent_issue,
        )
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "inspect-planning-state":
        path = resolve_planning_state_path(config=config, path_override=args.planning_state_path)
        payload = inspect_planning_state(path=path)
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "compare-planning-state":
        path = resolve_planning_state_path(config=config, path_override=args.planning_state_path)
        payload = compare_planning_state(path=path)
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "inspect-sequential-run-state":
        path = resolve_sequential_run_state_path(config=config, path_override=args.sequential_run_state_path)
        payload = inspect_sequential_run_state(
            config,
            parent_issue=args.parent_issue,
            state_path=path,
            write_local_state=bool(args.write_local_state),
        )
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "plan-sequential-run-recovery":
        path = resolve_sequential_run_state_path(config=config, path_override=args.sequential_run_state_path)
        payload = plan_sequential_run_recovery(config, parent_issue=args.parent_issue, state_path=path)
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "generate-sequential-handoff-package":
        payload = generate_sequential_handoff_package(
            config,
            parent_issue=args.parent_issue,
            child_issue=args.issue,
            write_package=bool(args.write_package),
        )
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "run-sequential-child-closeout-flow":
        payload = run_sequential_child_closeout_flow(
            config,
            parent_issue=args.parent_issue,
            child_issue=args.child_issue,
            comment_body=args.comment_body,
            execute=bool(args.execute),
            approval_marker=args.approval_marker,
        )
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "generate-sequential-closeout-execution-package":
        payload = generate_sequential_closeout_execution_package(
            config,
            parent_issue=args.parent_issue,
            child_issue=args.child_issue,
            pr_url=args.pr_url,
            validation_results=list(args.validation_result),
        )
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "inspect-closeout-planning-drift":
        path = resolve_planning_state_path(config=config, path_override=args.planning_state_path)
        payload = inspect_closeout_planning_drift(
            config,
            parent_issue=args.parent_issue,
            planning_state_path=str(path),
        )
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "plan-github-mutation":
        payload = plan_github_mutation(
            config=config,
            mutation_type=args.mutation_type,
            planned_action=args.planned_action,
            target_issue=args.target_issue,
            target_pr=args.target_pr,
            approval_marker=args.approval_marker,
        )
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "execute-github-issue-comment":
        body = load_comment_body(inline_body=args.comment_body, body_file=args.comment_file)
        payload = execute_github_issue_comment(
            config,
            issue_number=args.issue,
            comment_body=body,
            execute=bool(args.execute),
            parent_issue=args.parent_issue,
            allow_parent_target=bool(args.allow_parent_target),
            approval_marker=args.approval_marker,
        )
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "execute-github-issue-close":
        payload = execute_github_issue_close(
            config,
            issue_target=args.issue_target,
            parent_issue=args.parent_issue,
            execute=bool(args.execute),
            approval_marker=args.approval_marker,
        )
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "prepare-pr-body-update":
        payload = prepare_pr_body_update(
            config,
            pr_number=args.pr_number,
            target_issue=args.target_issue,
            scope_summary=args.scope_summary,
            files_changed=list(args.file_changed),
            validation_results=list(args.validation_result),
            safety_notes=list(args.safety_note),
            execute=bool(args.execute),
            approval_marker=args.approval_marker,
        )
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "inspect-github-mutation-audit-log":
        payload = inspect_github_mutation_audit_log(config, limit=args.limit)
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "project-state-summary":
        emit_json(project_state_summary(config))
        return 0

    if args.command == "inspect-repo-governance":
        emit_json(inspect_repo_governance(config))
        return 0

    if args.command == "assess-repo":
        repo_path = Path(args.repo_path).resolve() if args.repo_path else config.repo_root
        output_path = Path(args.output)
        if not output_path.is_absolute():
            output_path = (repo_path / output_path).resolve()
        payload = assess_repository(
            config,
            options=AssessmentOptions(
                repo_path=repo_path,
                output_path=output_path,
                format=args.format,
                include_tests=bool(args.include_tests),
                include_docs=bool(args.include_docs),
                force=bool(args.force),
            ),
        )
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "inspect-evidence-bundle-automation-contract":
        payload = inspect_evidence_bundle_automation_contract(config)
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "inspect-milestone-closeout-preflight-contract":
        payload = inspect_milestone_closeout_preflight_contract(config)
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "inspect-canonical-evidence-marker-contract":
        payload = inspect_canonical_evidence_marker_contract(config)
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "inspect-automatic-canonical-evidence-emission-contract":
        payload = inspect_automatic_canonical_evidence_emission_contract(config)
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "inspect-repo-bootstrap-contract":
        emit_json(inspect_repo_bootstrap_contract(config))
        return 0

    if args.command == "inspect-managed-repos":
        emit_json(inspect_managed_repos(config))
        return 0

    if args.command == "managed-repo-readiness-report":
        emit_json(managed_repo_readiness_report(config))
        return 0

    if args.command == "plan-repo-bootstrap":
        emit_json(plan_repo_bootstrap(config))
        return 0

    if args.command == "demo-managed-repo-governance":
        emit_json(demo_managed_repo_governance(config))
        return 0

    if args.command == "qa-review-pr":
        emit_json(qa_review_pr(config, args.pr_number))
        return 0

    if args.command == "qa-closeout-pr":
        payload = qa_closeout_pr(config, args.pr_number, execute=bool(args.execute))
        emit_json(payload)
        return 0 if not payload["failed_gates"] else 1

    if args.command == "validate-pr-end-to-end":
        payload = validate_pr_end_to_end(config, args.pr_number)
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "inspect-review-package":
        payload = inspect_local_review_package(config, args.review_path)
        emit_json(payload)
        return 0 if payload["ok"] else 1

    if args.command == "inspect-artifact":
        payload = inspect_local_artifact(config, args.artifact_path)
        emit_json(payload)
        return 0 if payload["ok"] else 1

    if args.command == "inspect-evidence-package":
        payload = inspect_local_evidence_package(config, args.evidence_path)
        emit_json(payload)
        return 0 if payload["ok"] else 1

    if args.command == "list-projects":
        with connect(config) as conn:
            emit_json({"projects": list_projects(conn)})
        return 0

    if args.command == "list-agents":
        with connect(config) as conn:
            emit_json({"agents": list_agents(conn)})
        return 0

    if args.command == "list-models":
        with connect(config) as conn:
            emit_json({"models": list_models(conn)})
        return 0

    if args.command == "inspect-model":
        with connect(config) as conn:
            model_record = inspect_model(conn, args.model_id)
        if model_record is None:
            emit_json({"ok": False, "error": "model_not_found", "model_id": args.model_id})
            return 1
        emit_json({"ok": True, "model": model_record})
        return 0

    if args.command == "list-queues":
        with connect(config) as conn:
            emit_json({"queues": list_queues(conn)})
        return 0

    if args.command == "inspect-queue":
        with connect(config) as conn:
            queue_record = inspect_queue(conn, args.queue_id)
        if queue_record is None:
            emit_json({"ok": False, "error": "queue_not_found", "queue_id": args.queue_id})
            return 1
        response: dict[str, Any] = {"ok": True, "queue": queue_record}
        if args.write_artifact:
            bundle = render_queue_inspection_report(
                config=config,
                inspection_payload=queue_record,
            )
            response["inspection_payload"] = queue_record
            response["markdown_path"] = str(bundle.markdown_path)
            response["json_path"] = str(bundle.json_path)
        emit_json(response)
        return 0

    if args.command == "create-work-item":
        metadata = parse_metadata(args.metadata_json)
        metadata.update(parse_metadata_pairs(args.metadata))
        payload = WorkItemCreate(
            project_id=args.project_id,
            queue_id=args.queue_id,
            title=args.title,
            description=args.description,
            status=args.status,
            priority=args.priority,
            route_status=args.route_status,
            agent_id=args.agent_id,
            model_id=args.model_id,
            prompt_id=args.prompt_id,
            metadata=metadata,
        )
        with connect(config) as conn:
            emit_json({"work_item": create_work_item(conn, payload)})
        return 0

    if args.command == "list-work-items":
        with connect(config) as conn:
            emit_json({"work_items": list_work_items(conn, status=args.status)})
        return 0

    if args.command == "inspect-work-item":
        with connect(config) as conn:
            work_item = inspect_work_item(conn, args.work_item_id)
        if work_item is None:
            emit_json({"ok": False, "error": "work_item_not_found", "work_item_id": args.work_item_id})
            return 1
        response: dict[str, Any] = {"ok": True, "work_item": work_item}
        if args.write_artifact:
            bundle = render_work_item_inspection_report(
                config=config,
                inspection_payload=work_item,
            )
            response["inspection_payload"] = work_item
            response["markdown_path"] = str(bundle.markdown_path)
            response["json_path"] = str(bundle.json_path)
        emit_json(response)
        return 0

    if args.command == "generate-prompt-package":
        route_plan = build_route_plan(
            work_item_id=args.work_item_id,
            queue_id=args.queue_id,
            agent_id=args.agent_id,
            model_id=args.model_id,
            prompt_package=None,
            route_status=args.route_status,
        )
        bundle = render_prompt_package(
            config=config,
            title=args.title,
            objective=args.objective,
            work_item_id=args.work_item_id,
            route_plan=route_plan,
            notes=args.notes,
        )
        response: dict[str, Any] = {
            "markdown_path": str(bundle.markdown_path),
            "json_path": str(bundle.json_path),
        }
        if args.store_db:
            with connect(config) as conn:
                response["db_record"] = store_prompt_record(
                    conn,
                    project_id=DEFAULT_PROJECT_ID,
                    work_item_id=args.work_item_id,
                    title=args.title,
                    artifact_path=bundle.markdown_path,
                    summary=args.objective,
                    metadata=bundle.payload,
                )
        emit_json(response)
        return 0

    if args.command == "record-evidence-package":
        artifact_discovery = (
            discover_local_artifacts(config) if args.include_artifact_discovery else None
        )
        latest_review_package = (
            latest_local_review_package_summary(config)
            if args.include_latest_review_package
            else None
        )
        bundle = render_evidence_package(
            config=config,
            title=args.title,
            work_item_id=args.work_item_id,
            files_changed=args.files_changed,
            validations_run=args.validations_run,
            skipped_checks=args.skipped_checks,
            protected_issue_checks=args.protected_issue_checks,
            automation_boundary_confirmation=args.automation_boundary_confirmation,
            artifact_discovery=artifact_discovery,
            latest_review_package=latest_review_package,
        )
        response = {
            "markdown_path": str(bundle.markdown_path),
            "json_path": str(bundle.json_path),
        }
        if args.store_db:
            with connect(config) as conn:
                response["db_record"] = store_evidence_record(
                    conn,
                    project_id=DEFAULT_PROJECT_ID,
                    work_item_id=args.work_item_id,
                    title=args.title,
                    artifact_path=bundle.markdown_path,
                    metadata=bundle.payload,
                )
        emit_json(response)
        return 0

    if args.command == "test-ollama":
        payload = inspect_ollama_health_and_models(config, output_format=args.format)
        if bool(payload.get("ok")) and not bool(payload.get("wrote_output_file")):
            print(payload["stdout"])
            return 0
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "inspect-ollama-health":
        payload = inspect_ollama_health_and_models(config, output_format=args.format)
        if bool(payload.get("ok")) and not bool(payload.get("wrote_output_file")):
            print(payload["stdout"])
            return 0
        emit_json(payload)
        return 0 if bool(payload.get("ok")) else 1

    if args.command == "prepare-codex-handoff":
        route_plan = build_route_plan(
            work_item_id=args.work_item_id,
            queue_id=args.queue_id,
            agent_id=args.agent_id,
            model_id=args.model_id,
            prompt_package=None,
            route_status=args.route_status,
        )
        latest_review_package = (
            latest_local_review_package_summary(config)
            if args.include_latest_review_package
            else None
        )
        bundle = render_codex_handoff(
            config=config,
            title=args.title,
            summary=args.summary,
            work_item_id=args.work_item_id,
            route_plan=route_plan,
            requested_output=args.requested_output,
            latest_review_package=latest_review_package,
        )
        emit_json(
            {
                "markdown_path": str(bundle.markdown_path),
                "json_path": str(bundle.json_path),
            }
        )
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2
