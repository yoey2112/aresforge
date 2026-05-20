from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

from psycopg import Connection

from aresforge.config import AppConfig


DEFAULT_PROJECT_ID = "project-aresforge"
DEFAULT_AGENT_ID = "agent-local-operator"
DEFAULT_MODEL_ID = "model-ollama-default"
DEFAULT_AGENT_REGISTRY_VERSION = "m2-v1"
QUEUE_SCHEMA_SOURCE_DOCUMENT = "docs/architecture/QUEUE_REGISTRY_SCHEMA.md"
MODEL_SCHEMA_SOURCE_DOCUMENT = "docs/architecture/MODEL_REGISTRY_SCHEMA.md"
CANONICAL_QUEUE_IDS = (
    "queue-intake",
    "queue-planning",
    "queue-triage",
    "queue-implementation",
    "queue-verification",
    "queue-testing",
    "queue-documentation",
    "queue-closeout",
    "queue-blocked",
    "queue-corrective",
)
DEFAULT_QUEUES = (
    {
        "id": "queue-intake",
        "name": "intake",
        "purpose": "Capture new approved work before detailed planning or triage.",
        "metadata": {
            "lifecycle_stage_mapping": "planning",
            "accepted_work_item_types": [
                "github_issue",
                "documentation_update",
                "closeout_package",
            ],
            "allowed_next_queues": ["queue-planning", "queue-blocked"],
            "human_approval_requirement": "human_review_required",
            "local_operator_visibility_expectations": [
                "visible issue reference",
                "required docs",
                "project",
                "approval posture",
            ],
            "source_document": QUEUE_SCHEMA_SOURCE_DOCUMENT,
        },
    },
    {
        "id": "queue-planning",
        "name": "planning",
        "purpose": "Shape approved work into a bounded issue-scoped execution target.",
        "metadata": {
            "lifecycle_stage_mapping": "planning",
            "accepted_work_item_types": ["github_issue", "documentation_update"],
            "allowed_next_queues": ["queue-triage", "queue-blocked"],
            "human_approval_requirement": "human_review_required",
            "local_operator_visibility_expectations": [
                "visible scope summary",
                "dependency notes",
                "required next queue",
            ],
            "source_document": QUEUE_SCHEMA_SOURCE_DOCUMENT,
        },
    },
    {
        "id": "queue-triage",
        "name": "triage",
        "purpose": "Convert the planning package into a bounded route and execution handoff.",
        "metadata": {
            "lifecycle_stage_mapping": "triage",
            "accepted_work_item_types": ["github_issue", "correction_pass"],
            "allowed_next_queues": ["queue-implementation", "queue-blocked"],
            "human_approval_requirement": "human_review_required",
            "local_operator_visibility_expectations": [
                "visible planned route",
                "next queue",
                "blocked reason",
                "approval posture",
            ],
            "source_document": QUEUE_SCHEMA_SOURCE_DOCUMENT,
        },
    },
    {
        "id": "queue-implementation",
        "name": "implementation",
        "purpose": "Hold issue-scoped repository work while implementation changes are being prepared.",
        "metadata": {
            "lifecycle_stage_mapping": "implementation",
            "accepted_work_item_types": ["github_issue", "correction_pass"],
            "allowed_next_queues": ["queue-verification", "queue-blocked"],
            "human_approval_requirement": "human_review_required",
            "local_operator_visibility_expectations": [
                "visible queue placement",
                "assigned role",
                "changed files",
                "current route status",
            ],
            "source_document": QUEUE_SCHEMA_SOURCE_DOCUMENT,
        },
    },
    {
        "id": "queue-verification",
        "name": "verification",
        "purpose": "Confirm that the implementation matches issue requirements and scope.",
        "metadata": {
            "lifecycle_stage_mapping": "verification",
            "accepted_work_item_types": [
                "github_issue",
                "verification_pass",
                "correction_pass",
            ],
            "allowed_next_queues": [
                "queue-testing",
                "queue-corrective",
                "queue-blocked",
            ],
            "human_approval_requirement": "human_review_required",
            "local_operator_visibility_expectations": [
                "visible findings",
                "pass/fail posture",
                "correction target when failed",
            ],
            "source_document": QUEUE_SCHEMA_SOURCE_DOCUMENT,
        },
    },
    {
        "id": "queue-testing",
        "name": "testing",
        "purpose": "Record issue-appropriate tests, checks, skips, and residual-risk notes before documentation.",
        "metadata": {
            "lifecycle_stage_mapping": "testing",
            "accepted_work_item_types": [
                "github_issue",
                "testing_pass",
                "correction_pass",
            ],
            "allowed_next_queues": [
                "queue-documentation",
                "queue-corrective",
                "queue-blocked",
            ],
            "human_approval_requirement": "human_review_required",
            "local_operator_visibility_expectations": [
                "visible commands or checks run",
                "result posture",
                "skipped-check reasons",
            ],
            "source_document": QUEUE_SCHEMA_SOURCE_DOCUMENT,
        },
    },
    {
        "id": "queue-documentation",
        "name": "documentation",
        "purpose": "Perform documentation-before-closeout review and update impacted source-of-truth documents.",
        "metadata": {
            "lifecycle_stage_mapping": "documentation",
            "accepted_work_item_types": [
                "github_issue",
                "documentation_update",
                "closeout_package",
            ],
            "allowed_next_queues": [
                "queue-closeout",
                "queue-corrective",
                "queue-blocked",
            ],
            "human_approval_requirement": "human_review_required",
            "local_operator_visibility_expectations": [
                "visible touched docs",
                "unresolved freshness findings",
                "documentation gate posture",
            ],
            "source_document": QUEUE_SCHEMA_SOURCE_DOCUMENT,
        },
    },
    {
        "id": "queue-closeout",
        "name": "closeout",
        "purpose": "Confirm that all lifecycle gates passed and prepare final human-reviewed closeout readiness.",
        "metadata": {
            "lifecycle_stage_mapping": "closeout",
            "accepted_work_item_types": ["github_issue", "closeout_package"],
            "allowed_next_queues": ["queue-blocked"],
            "human_approval_requirement": "human_review_required",
            "local_operator_visibility_expectations": [
                "visible gate checklist",
                "final evidence references",
                "final human action required",
            ],
            "source_document": QUEUE_SCHEMA_SOURCE_DOCUMENT,
        },
    },
    {
        "id": "queue-blocked",
        "name": "blocked",
        "purpose": "Represent work that cannot advance safely because approvals, prerequisites, or missing inputs prevent progress.",
        "metadata": {
            "lifecycle_stage_mapping": "blocked",
            "accepted_work_item_types": ["all_canonical_work_item_types"],
            "allowed_next_queues": [
                "queue-intake",
                "queue-planning",
                "queue-triage",
                "queue-implementation",
                "queue-verification",
                "queue-testing",
                "queue-documentation",
                "queue-closeout",
                "queue-corrective",
            ],
            "human_approval_requirement": "human_review_required",
            "local_operator_visibility_expectations": [
                "visible blocked reason",
                "resume condition",
                "prior queue",
                "human decision needed",
            ],
            "source_document": QUEUE_SCHEMA_SOURCE_DOCUMENT,
        },
    },
    {
        "id": "queue-corrective",
        "name": "corrective",
        "purpose": "Hold work that failed a lifecycle gate and needs a bounded corrective pass.",
        "metadata": {
            "lifecycle_stage_mapping": "corrective",
            "accepted_work_item_types": [
                "github_issue",
                "correction_pass",
                "verification_pass",
                "testing_pass",
                "documentation_update",
            ],
            "allowed_next_queues": [
                "queue-implementation",
                "queue-verification",
                "queue-testing",
                "queue-documentation",
                "queue-blocked",
            ],
            "human_approval_requirement": "human_review_required",
            "local_operator_visibility_expectations": [
                "visible failed gate",
                "targeted corrective queue",
                "retry notes",
                "unresolved blockers",
            ],
            "source_document": QUEUE_SCHEMA_SOURCE_DOCUMENT,
        },
    },
)
DEFAULT_AGENT_RECORDS = (
    {
        "id": "agent-planning-next-issue",
        "name": "planning-next-issue-agent",
        "status": "planned",
        "role": "Selects the next approved issue and packages scope and reading inputs.",
        "metadata": {
            "registry_version": DEFAULT_AGENT_REGISTRY_VERSION,
            "agent_name": "Planning / Next-Issue Agent",
            "agent_slug": "planning-next-issue-agent",
            "role_kind": "lifecycle",
            "queue_participation": ["queue-intake", "queue-planning"],
            "allowed_capabilities": [
                "issue_selection_support",
                "sequencing_analysis",
                "source_of_truth_reading_list_preparation",
            ],
            "approval_boundary": "human_review_required",
            "evidence_expectations": [
                "issue recommendation notes",
                "dependency notes",
                "required source-of-truth list",
            ],
        },
    },
    {
        "id": "agent-triage-routing",
        "name": "triage-routing-agent",
        "status": "planned",
        "role": "Converts approved issue scope into a bounded routing and execution handoff.",
        "metadata": {
            "registry_version": DEFAULT_AGENT_REGISTRY_VERSION,
            "agent_name": "Triage / Routing Agent",
            "agent_slug": "triage-routing-agent",
            "role_kind": "lifecycle",
            "queue_participation": ["queue-planning"],
            "allowed_capabilities": [
                "scope_refinement",
                "queue_path_recommendation",
                "validation_requirement_packaging",
            ],
            "approval_boundary": "human_review_required",
            "evidence_expectations": [
                "routing notes",
                "scoped handoff summary",
                "boundary notes",
            ],
        },
    },
    {
        "id": "agent-worker",
        "name": "worker-agent",
        "status": "planned",
        "role": "Performs issue-scoped implementation work under human review.",
        "metadata": {
            "registry_version": DEFAULT_AGENT_REGISTRY_VERSION,
            "agent_name": "Worker Agent",
            "agent_slug": "worker-agent",
            "role_kind": "lifecycle",
            "queue_participation": ["queue-implementation"],
            "allowed_capabilities": [
                "implementation_drafting",
                "local_file_changes",
                "local_validation_support",
            ],
            "approval_boundary": "human_review_required",
            "evidence_expectations": [
                "changed-file summary",
                "implementation notes",
                "initial validation notes",
            ],
        },
    },
    {
        "id": "agent-verification",
        "name": "verification-agent",
        "status": "planned",
        "role": "Confirms that implementation output matches issue scope and requirements.",
        "metadata": {
            "registry_version": DEFAULT_AGENT_REGISTRY_VERSION,
            "agent_name": "Verification Agent",
            "agent_slug": "verification-agent",
            "role_kind": "lifecycle",
            "queue_participation": ["queue-verification"],
            "allowed_capabilities": [
                "requirement_fit_review",
                "scope_control_review",
                "defect_identification",
            ],
            "approval_boundary": "human_review_required",
            "evidence_expectations": [
                "findings summary",
                "requirement coverage notes",
                "scope warnings",
            ],
        },
    },
    {
        "id": "agent-testing",
        "name": "testing-agent",
        "status": "planned",
        "role": "Runs or reports issue-appropriate validation commands and manual checks.",
        "metadata": {
            "registry_version": DEFAULT_AGENT_REGISTRY_VERSION,
            "agent_name": "Testing Agent",
            "agent_slug": "testing-agent",
            "role_kind": "lifecycle",
            "queue_participation": ["queue-verification"],
            "allowed_capabilities": [
                "test_execution_support",
                "validation_reporting",
                "skipped_check_reporting",
            ],
            "approval_boundary": "human_review_required",
            "evidence_expectations": [
                "validation results",
                "skipped-check notes",
                "remaining-risk notes",
            ],
        },
    },
    {
        "id": "agent-debug-routing",
        "name": "debug-routing-agent",
        "status": "planned",
        "role": "Routes failed verification or testing work back to the right corrective path.",
        "metadata": {
            "registry_version": DEFAULT_AGENT_REGISTRY_VERSION,
            "agent_name": "Debug Routing Agent",
            "agent_slug": "debug-routing-agent",
            "role_kind": "lifecycle",
            "queue_participation": ["queue-verification"],
            "allowed_capabilities": [
                "defect_classification",
                "corrective_handoff_preparation",
                "failure_loop_support",
            ],
            "approval_boundary": "human_review_required",
            "evidence_expectations": [
                "defect summary",
                "corrective route notes",
                "retry expectations",
            ],
        },
    },
    {
        "id": "agent-documentation",
        "name": "documentation-agent",
        "status": "active",
        "role": "Performs documentation-before-closeout review and source-of-truth updates.",
        "metadata": {
            "registry_version": DEFAULT_AGENT_REGISTRY_VERSION,
            "agent_name": "Documentation Agent",
            "agent_slug": "documentation-agent",
            "role_kind": "lifecycle",
            "queue_participation": ["queue-documentation"],
            "allowed_capabilities": [
                "documentation_impact_review",
                "documentation_updates",
                "freshness_check_reporting",
                "evidence_package_support",
            ],
            "approval_boundary": "human_review_required",
            "evidence_expectations": [
                "source-of-truth update summary",
                "freshness findings",
                "PR and closeout evidence inputs",
            ],
        },
    },
    {
        "id": "agent-final-closeout",
        "name": "final-closeout-lifecycle-controller-agent",
        "status": "planned",
        "role": "Confirms lifecycle gates passed and prepares final closeout readiness.",
        "metadata": {
            "registry_version": DEFAULT_AGENT_REGISTRY_VERSION,
            "agent_name": "Final Closeout / Lifecycle Controller Agent",
            "agent_slug": "final-closeout-lifecycle-controller-agent",
            "role_kind": "lifecycle",
            "queue_participation": ["queue-documentation"],
            "allowed_capabilities": [
                "closeout_readiness_review",
                "final_gate_confirmation",
                "human_handoff_preparation",
            ],
            "approval_boundary": "human_review_required",
            "evidence_expectations": [
                "closeout readiness summary",
                "unresolved limitation notes",
                "final handoff notes",
            ],
        },
    },
    {
        "id": DEFAULT_AGENT_ID,
        "name": "local-operator",
        "status": "active",
        "role": "Human-triggered operator CLI for local inspection, artifacts, and approved local state actions.",
        "metadata": {
            "registry_version": DEFAULT_AGENT_REGISTRY_VERSION,
            "agent_name": "Local Operator",
            "agent_slug": "local-operator",
            "role_kind": "human",
            "queue_participation": [
                "queue-intake",
                "queue-planning",
                "queue-implementation",
                "queue-verification",
                "queue-documentation",
            ],
            "allowed_capabilities": [
                "local_state_inspection",
                "migration_execution",
                "prompt_package_generation",
                "evidence_package_recording",
                "codex_handoff_preparation",
                "read_only_registry_listing",
            ],
            "approval_boundary": "human_owner",
            "evidence_expectations": [
                "command output",
                "artifact paths",
                "boundary confirmations",
            ],
            "automation_boundary": "No autonomous GitHub state changes.",
        },
    },
)


def build_default_model_metadata(*, model_name: str) -> dict[str, Any]:
    return {
        "default": True,
        "display_name": model_name,
        "model_key": f"ollama/{model_name}",
        "runtime": "ollama_local",
        "execution_location": "local_machine",
        "hosting_posture": "local_only",
        "purpose": "Local drafting, documentation support, and bounded validation evidence review.",
        "allowed_task_classes": [
            "documentation_support",
            "implementation_support",
            "validation_evidence_review",
            "diff_review_support",
            "project_state_summary_support",
        ],
        "default_routing_priority": "primary",
        "fallback_rules": [
            "If unavailable, try another approved local model for the same task class.",
            "If no approved local model is suitable, escalate to the human owner.",
        ],
        "approval_requirements": [
            "Human review remains required for all output.",
            "Human approval is mandatory for any governance-sensitive interpretation or action.",
        ],
        "approval_posture": "local_human_review_required",
        "validation_suitability": "bounded_validation_support",
        "evidence_expectations": [
            "record selected model key",
            "record task class",
            "record routing reason",
            "record limitations relevant to the task",
        ],
        "known_limitations": [
            "May produce useful review evidence without being authoritative.",
            "Must not be treated as approval, merge, or closeout authority.",
        ],
        "restricted_task_classes": [
            "governance_decision",
            "merge_authority",
            "issue_close_authority",
            "repo_mutation",
            "release_mutation",
            "secret_handling",
            "ruleset_mutation",
            "settings_mutation",
        ],
        "governance_sensitive_task_posture": "advisory_only_human_approval_required",
        "source_document": MODEL_SCHEMA_SOURCE_DOCUMENT,
    }


def build_default_model_seed(config: AppConfig) -> dict[str, Any]:
    return {
        "id": DEFAULT_MODEL_ID,
        "name": config.ollama_model,
        "provider": "ollama",
        "status": "configured",
        "endpoint": config.ollama_base_url,
        "metadata": build_default_model_metadata(model_name=config.ollama_model),
    }


def build_default_model_seed_from_row(row: dict[str, Any]) -> dict[str, Any] | None:
    if row.get("id") != DEFAULT_MODEL_ID or row.get("provider") != "ollama":
        return None
    return {
        "id": DEFAULT_MODEL_ID,
        "name": row["name"],
        "provider": row["provider"],
        "status": row["status"],
        "endpoint": row.get("endpoint"),
        "metadata": build_default_model_metadata(model_name=row["name"]),
    }


@dataclass(frozen=True, slots=True)
class WorkItemCreate:
    project_id: str
    queue_id: str
    title: str
    description: str
    status: str
    priority: str
    route_status: str
    agent_id: str | None
    model_id: str | None
    prompt_id: str | None
    metadata: dict[str, Any]


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:12]}"


def enrich_queue_record(row: dict[str, Any]) -> dict[str, Any]:
    metadata = row.get("metadata") or {}
    return {
        "id": row["id"],
        "name": row["name"],
        "status": row["status"],
        "purpose": row["purpose"],
        "metadata": metadata,
        "lifecycle_stage_mapping": metadata.get("lifecycle_stage_mapping"),
        "accepted_work_item_types": metadata.get("accepted_work_item_types"),
        "allowed_next_queues": metadata.get("allowed_next_queues"),
        "human_approval_requirement": metadata.get("human_approval_requirement"),
        "local_operator_visibility_expectations": metadata.get(
            "local_operator_visibility_expectations"
        ),
        "source_document": metadata.get("source_document"),
    }


def enrich_model_record(row: dict[str, Any]) -> dict[str, Any]:
    default_seed = build_default_model_seed_from_row(row)
    metadata = {
        **((default_seed or {}).get("metadata") or {}),
        **(row.get("metadata") or {}),
    }
    return {
        "id": row["id"],
        "name": row["name"],
        "display_name": metadata.get("display_name") or row["name"],
        "provider": row["provider"],
        "runtime": metadata.get("runtime"),
        "status": row["status"],
        "endpoint": row.get("endpoint"),
        "local_endpoint": metadata.get("local_endpoint") or row.get("endpoint"),
        "model_key": metadata.get("model_key"),
        "execution_location": metadata.get("execution_location"),
        "hosting_posture": metadata.get("hosting_posture"),
        "purpose": metadata.get("purpose"),
        "allowed_task_classes": metadata.get("allowed_task_classes"),
        "default_routing_priority": metadata.get("default_routing_priority"),
        "fallback_rules": metadata.get("fallback_rules"),
        "approval_requirements": metadata.get("approval_requirements"),
        "approval_posture": metadata.get("approval_posture"),
        "validation_suitability": metadata.get("validation_suitability"),
        "evidence_expectations": metadata.get("evidence_expectations"),
        "known_limitations": metadata.get("known_limitations"),
        "restricted_task_classes": metadata.get("restricted_task_classes"),
        "governance_sensitive_task_posture": metadata.get(
            "governance_sensitive_task_posture"
        ),
        "source_document": metadata.get("source_document"),
        "metadata": metadata,
        "updated_at": row["updated_at"],
    }


def enrich_project_record(row: dict[str, Any]) -> dict[str, Any]:
    metadata = row.get("metadata") or {}
    return {
        "id": row["id"],
        "slug": row["slug"],
        "name": row["name"],
        "status": row["status"],
        "repo_owner": row["repo_owner"],
        "repo_name": row["repo_name"],
        "default_branch": row["default_branch"],
        "local_path": row["local_path"],
        "metadata": metadata,
        "autonomy_level": metadata.get("autonomy_level"),
        "protected_issue": metadata.get("protected_issue"),
        "active_issue": metadata.get("active_issue"),
        "completed_issue": metadata.get("completed_issue"),
        "updated_at": row["updated_at"],
    }


def enrich_work_item_record(row: dict[str, Any]) -> dict[str, Any]:
    metadata = row.get("metadata") or {}
    queue_metadata = row.get("queue_metadata") or {}
    return {
        "id": row["id"],
        "title": row["title"],
        "description": row["description"],
        "status": row["status"],
        "priority": row["priority"],
        "route_status": row["route_status"],
        "queue_id": row["queue_id"],
        "queue_name": row["queue_name"],
        "queue_purpose": row["queue_purpose"],
        "queue_lifecycle_stage_mapping": queue_metadata.get("lifecycle_stage_mapping"),
        "queue_accepted_work_item_types": queue_metadata.get("accepted_work_item_types"),
        "queue_allowed_next_queues": queue_metadata.get("allowed_next_queues"),
        "queue_human_approval_requirement": queue_metadata.get("human_approval_requirement"),
        "queue_local_operator_visibility_expectations": queue_metadata.get(
            "local_operator_visibility_expectations"
        ),
        "agent_id": row.get("agent_id"),
        "agent_name": row.get("agent_name"),
        "model_id": row.get("model_id"),
        "model_name": row.get("model_name"),
        "model_provider": row.get("model_provider"),
        "prompt_id": row.get("prompt_id"),
        "metadata": metadata,
        "lifecycle_state": metadata.get("lifecycle_state"),
        "approval_state": metadata.get("approval_state"),
        "blocked_reason": metadata.get("blocked_reason"),
        "failure_reason": metadata.get("failure_reason"),
        "retry_or_correction_context": metadata.get("retry_or_correction_context"),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def bootstrap_reference_data(conn: Connection, config: AppConfig) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO projects (
                id, slug, name, status, repo_owner, repo_name, default_branch, local_path, metadata
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
            ON CONFLICT (id) DO UPDATE
            SET status = EXCLUDED.status,
                repo_owner = EXCLUDED.repo_owner,
                repo_name = EXCLUDED.repo_name,
                local_path = EXCLUDED.local_path,
                metadata = EXCLUDED.metadata,
                updated_at = NOW()
            """,
            (
                DEFAULT_PROJECT_ID,
                "aresforge",
                "AresForge",
                "active",
                config.github_owner,
                config.github_repo,
                "main",
                str(config.repo_root),
                json.dumps(
                    {
                        "autonomy_level": "human_triggered_local_only",
                        "protected_issue": 39,
                        "active_issue": 97,
                        "completed_issue": 96,
                    }
                ),
            ),
        )
        for record in DEFAULT_AGENT_RECORDS:
            cur.execute(
                """
                INSERT INTO agents (id, name, status, role, metadata)
                VALUES (%s, %s, %s, %s, %s::jsonb)
                ON CONFLICT (id) DO UPDATE
                SET name = EXCLUDED.name,
                    status = EXCLUDED.status,
                    role = EXCLUDED.role,
                    metadata = EXCLUDED.metadata,
                    updated_at = NOW()
                """,
                (
                    record["id"],
                    record["name"],
                    record["status"],
                    record["role"],
                    json.dumps(record["metadata"]),
                ),
            )
        model_record = build_default_model_seed(config)
        cur.execute(
            """
            INSERT INTO models (id, name, provider, status, endpoint, metadata)
            VALUES (%s, %s, %s, %s, %s, %s::jsonb)
            ON CONFLICT (id) DO UPDATE
            SET name = EXCLUDED.name,
                endpoint = EXCLUDED.endpoint,
                metadata = EXCLUDED.metadata,
                updated_at = NOW()
            """,
            (
                model_record["id"],
                model_record["name"],
                model_record["provider"],
                model_record["status"],
                model_record["endpoint"],
                json.dumps(model_record["metadata"]),
            ),
        )
        for record in DEFAULT_QUEUES:
            cur.execute(
                """
                INSERT INTO queues (id, name, status, purpose, metadata)
                VALUES (%s, %s, %s, %s, %s::jsonb)
                ON CONFLICT (id) DO UPDATE
                SET status = EXCLUDED.status,
                    purpose = EXCLUDED.purpose,
                    metadata = EXCLUDED.metadata,
                    updated_at = NOW()
                """,
                (
                    record["id"],
                    record["name"],
                    "active",
                    record["purpose"],
                    json.dumps(record["metadata"]),
                ),
            )
        cur.execute(
            """
            INSERT INTO audit_events (id, project_id, event_type, actor, details)
            VALUES (%s, %s, %s, %s, %s::jsonb)
            """,
            (
                _new_id("audit"),
                DEFAULT_PROJECT_ID,
                "bootstrap_reference_data",
                "aresforge-cli",
                json.dumps({"model": config.ollama_model}),
            ),
        )


def list_projects(conn: Connection) -> list[dict[str, Any]]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, slug, name, status, repo_owner, repo_name, updated_at
            FROM projects
            ORDER BY name
            """
        )
        return list(cur.fetchall())


def inspect_project(conn: Connection, project_id: str) -> dict[str, Any] | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                id,
                slug,
                name,
                status,
                repo_owner,
                repo_name,
                default_branch,
                local_path,
                metadata,
                updated_at
            FROM projects
            WHERE id = %s
            """,
            (project_id,),
        )
        row = cur.fetchone()
    if row is None:
        return None
    return enrich_project_record(row)


def list_queues(conn: Connection) -> list[dict[str, Any]]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, name, status, purpose, updated_at
            FROM queues
            ORDER BY name
            """
        )
        return list(cur.fetchall())


def list_models(conn: Connection) -> list[dict[str, Any]]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, name, provider, status, endpoint, metadata, updated_at
            FROM models
            ORDER BY LOWER(name), id
            """
        )
        return [enrich_model_record(row) for row in cur.fetchall()]


def inspect_model(conn: Connection, model_id: str) -> dict[str, Any] | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, name, provider, status, endpoint, metadata, updated_at
            FROM models
            WHERE id = %s
            """,
            (model_id,),
        )
        row = cur.fetchone()
    if row is None:
        return None
    return enrich_model_record(row)


def inspect_queue(conn: Connection, queue_id: str) -> dict[str, Any] | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, name, status, purpose, metadata
            FROM queues
            WHERE id = %s
            """,
            (queue_id,),
        )
        row = cur.fetchone()
    if row is None:
        return None
    return enrich_queue_record(row)


def list_agents(conn: Connection) -> list[dict[str, Any]]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, name, status, role, metadata, updated_at
            FROM agents
            ORDER BY name
            """
        )
        return list(cur.fetchall())


def create_work_item(conn: Connection, payload: WorkItemCreate) -> dict[str, Any]:
    work_item_id = _new_id("work")
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO work_items (
                id, project_id, queue_id, agent_id, model_id, prompt_id,
                title, description, status, priority, route_status, metadata
            ) VALUES (
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s::jsonb
            )
            RETURNING id, project_id, queue_id, agent_id, model_id, prompt_id,
                      title, status, priority, route_status, created_at
            """,
            (
                work_item_id,
                payload.project_id,
                payload.queue_id,
                payload.agent_id,
                payload.model_id,
                payload.prompt_id,
                payload.title,
                payload.description,
                payload.status,
                payload.priority,
                payload.route_status,
                json.dumps(payload.metadata),
            ),
        )
        row = cur.fetchone()
        cur.execute(
            """
            INSERT INTO audit_events (id, project_id, work_item_id, event_type, actor, details)
            VALUES (%s, %s, %s, %s, %s, %s::jsonb)
            """,
            (
                _new_id("audit"),
                payload.project_id,
                work_item_id,
                "work_item_created",
                "aresforge-cli",
                json.dumps(
                    {
                        "queue_id": payload.queue_id,
                        "route_status": payload.route_status,
                    }
                ),
            ),
        )
    return row


def list_work_items(conn: Connection, status: str | None = None) -> list[dict[str, Any]]:
    query = """
        SELECT
            wi.id,
            wi.title,
            wi.status,
            wi.priority,
            wi.route_status,
            q.name AS queue_name,
            COALESCE(a.name, '') AS agent_name,
            COALESCE(m.name, '') AS model_name,
            wi.created_at
        FROM work_items wi
        JOIN queues q ON q.id = wi.queue_id
        LEFT JOIN agents a ON a.id = wi.agent_id
        LEFT JOIN models m ON m.id = wi.model_id
    """
    params: list[Any] = []
    if status:
        query += " WHERE wi.status = %s"
        params.append(status)
    query += " ORDER BY wi.created_at DESC"
    with conn.cursor() as cur:
        cur.execute(query, params)
        return list(cur.fetchall())


def inspect_work_item(conn: Connection, work_item_id: str) -> dict[str, Any] | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                wi.id,
                wi.title,
                wi.description,
                wi.status,
                wi.priority,
                wi.route_status,
                wi.queue_id,
                wi.agent_id,
                wi.model_id,
                wi.prompt_id,
                wi.metadata,
                wi.created_at,
                wi.updated_at,
                q.name AS queue_name,
                q.purpose AS queue_purpose,
                q.metadata AS queue_metadata,
                a.name AS agent_name,
                m.name AS model_name,
                m.provider AS model_provider
            FROM work_items wi
            JOIN queues q ON q.id = wi.queue_id
            LEFT JOIN agents a ON a.id = wi.agent_id
            LEFT JOIN models m ON m.id = wi.model_id
            WHERE wi.id = %s
            """,
            (work_item_id,),
        )
        row = cur.fetchone()
    if row is None:
        return None
    return enrich_work_item_record(row)


def inspect_state(conn: Connection) -> dict[str, Any]:
    with conn.cursor() as cur:
        counts: dict[str, int] = {}
        for table in (
            "projects",
            "agents",
            "models",
            "queues",
            "work_items",
            "prompts",
            "evidence_packages",
            "audit_events",
        ):
            cur.execute(f"SELECT COUNT(*) AS count FROM {table}")
            counts[table] = cur.fetchone()["count"]
        cur.execute(
            """
            SELECT id, title, status, route_status, created_at
            FROM work_items
            ORDER BY created_at DESC
            LIMIT 5
            """
        )
        recent_work_items = list(cur.fetchall())
    return {"counts": counts, "recent_work_items": recent_work_items}


def store_prompt_record(
    conn: Connection,
    *,
    project_id: str,
    work_item_id: str | None,
    title: str,
    artifact_path: Path,
    summary: str,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    prompt_id = _new_id("prompt")
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO prompts (id, project_id, work_item_id, title, artifact_path, format, summary, metadata)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb)
            RETURNING id, title, artifact_path, created_at
            """,
            (
                prompt_id,
                project_id,
                work_item_id,
                title,
                str(artifact_path),
                "markdown+json",
                summary,
                json.dumps(metadata),
            ),
        )
        return cur.fetchone()


def store_evidence_record(
    conn: Connection,
    *,
    project_id: str,
    work_item_id: str | None,
    title: str,
    artifact_path: Path,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    evidence_id = _new_id("evidence")
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO evidence_packages (id, project_id, work_item_id, title, artifact_path, status, metadata)
            VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
            RETURNING id, title, artifact_path, created_at
            """,
            (
                evidence_id,
                project_id,
                work_item_id,
                title,
                str(artifact_path),
                "recorded",
                json.dumps(metadata),
            ),
        )
        return cur.fetchone()
