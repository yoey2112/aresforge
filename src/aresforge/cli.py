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
from aresforge.operator.parent_closeout_evidence_bundle import (
    generate_parent_closeout_evidence_bundle,
)
from aresforge.operator.pr_evidence_bundle import generate_pr_evidence_bundle
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
from aresforge.operator.milestone_reconciliation_planner import plan_milestone_final_reconciliation
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
from aresforge.operator.evidence_bundle_automation_contract import (
    inspect_evidence_bundle_automation_contract,
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

    subparsers.add_parser("inspect-project-state", help="Show local database state summary.")
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
    parent_closeout_bundle_parser = subparsers.add_parser(
        "generate-parent-closeout-evidence-bundle",
        help="Generate read-only parent closeout evidence bundle text and targeted closeout guidance.",
    )
    parent_closeout_bundle_parser.add_argument("--parent-issue", type=int, required=True)
    pr_evidence_bundle_parser = subparsers.add_parser(
        "generate-pr-evidence-bundle",
        help="Generate read-only deterministic PR evidence body text and targeted update guidance.",
    )
    pr_evidence_bundle_parser.add_argument("--issue", type=int, required=True)
    pr_evidence_bundle_parser.add_argument("--pr", type=int, required=True)
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
    subparsers.add_parser(
        "inspect-evidence-bundle-automation-contract",
        help="Inspect read-only evidence bundle automation contract coverage and safety boundaries.",
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

    ollama_parser = subparsers.add_parser("test-ollama", help="Send a small prompt to Ollama.")
    ollama_parser.add_argument(
        "--prompt",
        default="Return one short sentence confirming that the local AresForge skeleton check reached Ollama.",
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

    if args.command == "inspect-project-state":
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

    if args.command == "generate-parent-closeout-evidence-bundle":
        payload = generate_parent_closeout_evidence_bundle(
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
        payload = inspect_milestone_state(config, parent_issue=args.parent_issue)
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
        payload = check_milestone_evidence_readiness(config, parent_issue=args.parent_issue)
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
        payload = inspect_parent_closeout_readiness(config, parent_issue=args.parent_issue)
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

    if args.command == "inspect-evidence-bundle-automation-contract":
        payload = inspect_evidence_bundle_automation_contract(config)
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
        result = test_generate(config, args.prompt)
        emit_json(
            {
                "ok": result.ok,
                "message": result.message,
                "response_text": result.response_text,
            }
        )
        return 0 if result.ok else 1

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
