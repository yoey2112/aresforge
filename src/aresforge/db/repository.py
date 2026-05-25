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


def update_work_item_status(
    conn: Connection,
    work_item_id: str,
    status: str,
    actor: str = "aresforge-cli",
    summary: str | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if status not in WORK_ITEM_ALLOWED_STATUSES:
        return {
            "ok": False,
            "error": "invalid_work_item_status",
            "status": status,
            "allowed_statuses": list(WORK_ITEM_ALLOWED_STATUSES),
        }
    normalized_details = _normalize_roadmap_details(details)
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, project_id, queue_id, status
            FROM work_items
            WHERE id = %s
            """,
            (work_item_id,),
        )
        existing = cur.fetchone()
        if existing is None:
            return {"ok": False, "error": "work_item_not_found", "work_item_id": work_item_id}
        previous_status = existing["status"]
        if previous_status == status:
            return {
                "ok": True,
                "changed": False,
                "previous_status": previous_status,
                "status": status,
                "work_item_id": work_item_id,
                "work_item": inspect_work_item(conn, work_item_id),
            }
        cur.execute(
            """
            UPDATE work_items
            SET status = %s,
                route_status = %s,
                updated_at = NOW()
            WHERE id = %s
            """,
            (status, status, work_item_id),
        )
        audit_event_id = _new_id("audit")
        cur.execute(
            """
            INSERT INTO audit_events (id, project_id, work_item_id, event_type, actor, details)
            VALUES (%s, %s, %s, %s, %s, %s::jsonb)
            """,
            (
                audit_event_id,
                existing["project_id"],
                work_item_id,
                "work_item_status_changed",
                actor,
                json.dumps(
                    {
                        "previous_status": previous_status,
                        "new_status": status,
                        "queue_id": existing["queue_id"],
                        **normalized_details,
                    }
                ),
            ),
        )
        cur.execute(
            """
            SELECT id, roadmap_task_id
            FROM roadmap_work_item_links
            WHERE work_item_id = %s
              AND status = 'active'
            ORDER BY created_at DESC, id DESC
            LIMIT 1
            """,
            (work_item_id,),
        )
        link_row = cur.fetchone()
    work_item = inspect_work_item(conn, work_item_id)
    event_ids = [audit_event_id]
    if link_row is not None:
        roadmap_event = add_roadmap_event(
            conn,
            project_id=existing["project_id"],
            event_type="work_item_status_changed",
            actor=actor,
            summary=summary or f"Work item status changed: {previous_status} -> {status}",
            details={
                "work_item_id": work_item_id,
                "previous_status": previous_status,
                "new_status": status,
                "queue_id": existing["queue_id"],
                "link_id": link_row["id"],
                **normalized_details,
            },
            task_id=link_row["roadmap_task_id"],
        )
        if bool(roadmap_event.get("ok")):
            event_ids.append(roadmap_event["event_id"])
    return {
        "ok": True,
        "changed": True,
        "previous_status": previous_status,
        "status": status,
        "work_item_id": work_item_id,
        "work_item": work_item,
        "event_ids": event_ids,
    }


def start_work_item_if_ready(
    conn: Connection,
    work_item_id: str,
    *,
    actor: str = "local-operator",
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    readiness = inspect_work_item_readiness(conn, work_item_id)
    readiness_status = readiness.get("readiness_status", "missing")
    ready = bool(readiness.get("ready"))
    normalized_details = _normalize_roadmap_details(details)

    if readiness_status == "missing":
        return {
            "ok": False,
            "changed": False,
            "work_item_id": work_item_id,
            "readiness_status": "missing",
            "ready": False,
            "reason": "work_item_not_found",
            "next_safe_action": readiness.get("next_safe_action"),
            "readiness": readiness,
        }
    if readiness_status == "already_active":
        return {
            "ok": True,
            "changed": False,
            "work_item_id": work_item_id,
            "readiness_status": "already_active",
            "ready": False,
            "reason": "already_active",
            "next_safe_action": readiness.get("next_safe_action"),
            "roadmap_links": readiness.get("roadmap_links", []),
            "readiness": readiness,
        }
    if readiness_status == "already_complete":
        return {
            "ok": True,
            "changed": False,
            "work_item_id": work_item_id,
            "readiness_status": "already_complete",
            "ready": False,
            "reason": "already_complete",
            "next_safe_action": readiness.get("next_safe_action"),
            "roadmap_links": readiness.get("roadmap_links", []),
            "readiness": readiness,
        }
    if readiness_status == "cancelled":
        return {
            "ok": True,
            "changed": False,
            "work_item_id": work_item_id,
            "readiness_status": "cancelled",
            "ready": False,
            "reason": "cancelled",
            "next_safe_action": readiness.get("next_safe_action"),
            "roadmap_links": readiness.get("roadmap_links", []),
            "readiness": readiness,
        }
    if not bool(readiness.get("ok")) or not ready or readiness_status != "ready":
        return {
            "ok": False,
            "changed": False,
            "work_item_id": work_item_id,
            "readiness_status": readiness_status,
            "ready": False,
            "blocked": True,
            "reason": "work_item_not_ready",
            "next_safe_action": readiness.get("next_safe_action"),
            "roadmap_links": readiness.get("roadmap_links", []),
            "readiness": readiness,
        }

    status_payload = update_work_item_status(
        conn,
        work_item_id=work_item_id,
        status="active",
        actor=actor,
        summary="Work item started.",
        details=normalized_details,
    )
    if not bool(status_payload.get("ok")):
        return {
            "ok": False,
            "changed": False,
            "work_item_id": work_item_id,
            "readiness_status": "ready",
            "ready": True,
            "reason": "start_work_item_failed",
            "next_safe_action": "Inspect work item lifecycle and events.",
            "readiness": readiness,
            "status_payload": status_payload,
        }

    event_ids = list(status_payload.get("event_ids", []))
    started_event_ids: list[str] = []
    for link in readiness.get("roadmap_links", []):
        roadmap_event = add_roadmap_event(
            conn,
            project_id=readiness.get("project_id", DEFAULT_PROJECT_ID),
            event_type="work_item_started",
            actor=actor,
            summary=f"Work item started: {status_payload.get('previous_status', 'queued')} -> active",
            details={
                "work_item_id": work_item_id,
                "roadmap_task_id": link.get("roadmap_task_id"),
                "previous_status": status_payload.get("previous_status", "queued"),
                "new_status": "active",
                **normalized_details,
            },
            task_id=link.get("roadmap_task_id"),
        )
        if bool(roadmap_event.get("ok")):
            started_event_ids.append(roadmap_event["event_id"])
            event_ids.append(roadmap_event["event_id"])

    return {
        "ok": True,
        "changed": bool(status_payload.get("changed")),
        "work_item_id": work_item_id,
        "previous_status": status_payload.get("previous_status", "queued"),
        "new_status": "active",
        "readiness_status": "ready",
        "ready": True,
        "reason": "started",
        "next_safe_action": "Continue or inspect active work item.",
        "roadmap_links": readiness.get("roadmap_links", []),
        "events": {
            "event_ids": event_ids,
            "status_event_ids": status_payload.get("event_ids", []),
            "started_event_ids": started_event_ids,
        },
        "readiness": readiness,
        "work_item": status_payload.get("work_item"),
    }


def inspect_work_item_lifecycle(conn: Connection, work_item_id: str) -> dict[str, Any]:
    work_item = inspect_work_item(conn, work_item_id)
    if work_item is None:
        return {"ok": False, "error": "work_item_not_found", "work_item_id": work_item_id}
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT rwil.id, rwil.project_id, rwil.roadmap_task_id, rwil.work_item_id, rwil.link_type, rwil.status,
                   rwil.metadata, rwil.created_at, rwil.updated_at,
                   rt.title AS roadmap_task_title, rt.status AS roadmap_task_status
            FROM roadmap_work_item_links rwil
            JOIN roadmap_tasks rt ON rt.id = rwil.roadmap_task_id
            WHERE rwil.work_item_id = %s
            ORDER BY rwil.created_at DESC, rwil.id DESC
            """,
            (work_item_id,),
        )
        roadmap_links = list(cur.fetchall())
        cur.execute(
            """
            SELECT id, project_id, work_item_id, event_type, actor, details, created_at
            FROM audit_events
            WHERE work_item_id = %s
            ORDER BY created_at DESC, id DESC
            """,
            (work_item_id,),
        )
        audit_events = list(cur.fetchall())
        roadmap_events: list[dict[str, Any]] = []
        task_ids = sorted({row["roadmap_task_id"] for row in roadmap_links if row.get("roadmap_task_id")})
        if task_ids:
            cur.execute(
                """
                SELECT id, project_id, area_id, milestone_id, task_id, event_type, actor, summary, details, created_at
                FROM roadmap_events
                WHERE task_id = ANY(%s)
                ORDER BY created_at DESC, id DESC
                """,
                (task_ids,),
            )
            roadmap_events = list(cur.fetchall())
    return {
        "ok": True,
        "work_item_id": work_item_id,
        "work_item": work_item,
        "roadmap_links": roadmap_links,
        "roadmap_events": roadmap_events,
        "audit_events": audit_events,
    }


def inspect_queue_work_state(
    conn: Connection,
    queue_id: str | None = None,
    project_id: str = DEFAULT_PROJECT_ID,
) -> dict[str, Any]:
    params: list[Any] = [project_id]
    queue_clause = ""
    if queue_id is not None:
        queue_clause = " AND wi.queue_id = %s"
        params.append(queue_id)
    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT wi.id, wi.project_id, wi.queue_id, wi.title, wi.status, wi.priority, wi.route_status, wi.created_at, wi.updated_at,
                   rwil.id AS link_id, rwil.roadmap_task_id, rt.title AS roadmap_task_title, rt.status AS roadmap_task_status
            FROM work_items wi
            LEFT JOIN roadmap_work_item_links rwil ON rwil.work_item_id = wi.id AND rwil.status = 'active'
            LEFT JOIN roadmap_tasks rt ON rt.id = rwil.roadmap_task_id
            WHERE wi.project_id = %s{queue_clause}
            ORDER BY wi.queue_id ASC, wi.created_at ASC, wi.id ASC
            """,
            params,
        )
        rows = list(cur.fetchall())
    by_queue: dict[str, int] = {}
    by_status: dict[str, int] = {}
    for row in rows:
        by_queue[row["queue_id"]] = by_queue.get(row["queue_id"], 0) + 1
        by_status[row["status"]] = by_status.get(row["status"], 0) + 1
    return {
        "ok": True,
        "project_id": project_id,
        "queue_id": queue_id,
        "counts_by_queue": [{"queue_id": key, "count": by_queue[key]} for key in sorted(by_queue)],
        "counts_by_status": [{"status": key, "count": by_status[key]} for key in sorted(by_status)],
        "work_items": [row for row in rows if row["status"] in ("active", "queued", "blocked")],
    }


def render_work_item_lifecycle_markdown(payload: dict[str, Any]) -> str:
    work_item = payload.get("work_item") or {}
    roadmap_links = payload.get("roadmap_links", [])
    roadmap_events = payload.get("roadmap_events", [])
    audit_events = payload.get("audit_events", [])
    lines = [
        "# Work Item Lifecycle",
        "",
        f"- Work Item ID: `{payload.get('work_item_id', work_item.get('id', ''))}`",
        f"- Status: `{work_item.get('status', '')}`",
        f"- Queue ID: `{work_item.get('queue_id', '')}`",
        f"- Route Status: `{work_item.get('route_status', '')}`",
        f"- Roadmap links: `{len(roadmap_links)}`",
        f"- Roadmap events: `{len(roadmap_events)}`",
        f"- Audit events: `{len(audit_events)}`",
        "",
    ]
    lines.append("## Roadmap Links")
    for link in roadmap_links:
        lines.append(f"- `{link['id']}` task=`{link['roadmap_task_id']}` status=`{link['status']}`")
    lines.append("")
    lines.append("## Audit Events")
    for event in audit_events:
        lines.append(f"- `{event['created_at']}` `{event['event_type']}` by `{event['actor']}`")
    lines.append("")
    lines.append("## Roadmap Events")
    for event in roadmap_events:
        lines.append(f"- `{event['created_at']}` `{event['event_type']}` task=`{event.get('task_id', '')}`")
    return "\n".join(lines).rstrip() + "\n"


def render_queue_work_state_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Queue Work State",
        "",
        f"- Project ID: `{payload.get('project_id', '')}`",
        f"- Queue ID filter: `{payload.get('queue_id') or 'all'}`",
        "",
        "## Counts by Queue",
    ]
    for row in payload.get("counts_by_queue", []):
        lines.append(f"- `{row['queue_id']}`: `{row['count']}`")
    lines.append("")
    lines.append("## Counts by Status")
    for row in payload.get("counts_by_status", []):
        lines.append(f"- `{row['status']}`: `{row['count']}`")
    lines.append("")
    lines.append("## Active Queued Blocked Work Items")
    for item in payload.get("work_items", []):
        lines.append(
            f"- `{item['id']}` queue=`{item['queue_id']}` status=`{item['status']}` title=`{item['title']}`"
        )
    return "\n".join(lines).rstrip() + "\n"


def inspect_work_item_readiness(conn: Connection, work_item_id: str) -> dict[str, Any]:
    work_item = inspect_work_item(conn, work_item_id)
    if work_item is None:
        return {
            "ok": False,
            "work_item_id": work_item_id,
            "project_id": DEFAULT_PROJECT_ID,
            "readiness_status": "missing",
            "ready": False,
            "error": "work_item_not_found",
            "next_safe_action": "Create or inspect the local work item before starting.",
            "blockers": [{"code": "work_item_not_found", "work_item_id": work_item_id}],
            "warnings": [],
            "work_item": None,
            "roadmap_links": [],
            "dependency_summary": {"total_dependencies": 0, "unsatisfied_dependencies": []},
            "related_events": {"audit_event_count": 0, "roadmap_event_count": 0},
        }

    blockers: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    dependency_summary = {"total_dependencies": 0, "unsatisfied_dependencies": []}
    roadmap_links: list[dict[str, Any]] = []
    readiness_status = "not_ready"
    ready = False
    next_safe_action = "Inspect work item readiness blockers."
    related_events = {"audit_event_count": 0, "roadmap_event_count": 0}

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT rwil.id, rwil.project_id, rwil.roadmap_task_id, rwil.work_item_id, rwil.link_type, rwil.status,
                   rwil.metadata, rwil.created_at, rwil.updated_at,
                   rt.title AS roadmap_task_title, rt.status AS roadmap_task_status
            FROM roadmap_work_item_links rwil
            JOIN roadmap_tasks rt ON rt.id = rwil.roadmap_task_id
            WHERE rwil.work_item_id = %s
              AND rwil.status = 'active'
            ORDER BY rwil.created_at DESC, rwil.id DESC
            """,
            (work_item_id,),
        )
        roadmap_links = list(cur.fetchall())
        cur.execute(
            """
            SELECT COUNT(*) AS count
            FROM audit_events
            WHERE work_item_id = %s
            """,
            (work_item_id,),
        )
        related_events["audit_event_count"] = cur.fetchone()["count"]

    task_ids = sorted({row["roadmap_task_id"] for row in roadmap_links if row.get("roadmap_task_id")})
    unsatisfied_dependencies: list[dict[str, Any]] = []
    cancelled_link_present = any(link.get("roadmap_task_status") == "cancelled" for link in roadmap_links)
    if task_ids:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT d.task_id, d.depends_on_task_id, dt.status AS depends_on_task_status
                FROM roadmap_task_dependencies d
                JOIN roadmap_tasks dt ON dt.id = d.depends_on_task_id
                WHERE d.task_id = ANY(%s)
                ORDER BY d.task_id ASC, d.depends_on_task_id ASC
                """,
                (task_ids,),
            )
            dependency_rows = list(cur.fetchall())
            for row in dependency_rows:
                if row["depends_on_task_status"] != "complete":
                    unsatisfied_dependencies.append(
                        {
                            "task_id": row["task_id"],
                            "depends_on_task_id": row["depends_on_task_id"],
                            "status": row["depends_on_task_status"],
                        }
                    )
            dependency_summary = {
                "total_dependencies": len(dependency_rows),
                "unsatisfied_dependencies": unsatisfied_dependencies,
            }
            cur.execute(
                """
                SELECT COUNT(*) AS count
                FROM roadmap_events
                WHERE task_id = ANY(%s)
                """,
                (task_ids,),
            )
            related_events["roadmap_event_count"] = cur.fetchone()["count"]

    status = work_item.get("status")
    if status == "cancelled":
        readiness_status = "cancelled"
        next_safe_action = "No action. Work item is cancelled."
    elif status == "complete":
        readiness_status = "already_complete"
        next_safe_action = "No action. Work item is already complete."
    elif status == "active":
        readiness_status = "already_active"
        next_safe_action = "Continue or inspect active work item."
    elif status == "blocked":
        readiness_status = "blocked"
        blockers.append({"code": "work_item_status_blocked"})
        blocked_reason = (work_item.get("metadata") or {}).get("blocked_reason")
        if blocked_reason:
            blockers.append({"code": "blocked_reason", "message": blocked_reason})
        next_safe_action = "Resolve blockers before starting."
    elif status == "queued":
        if not roadmap_links:
            readiness_status = "not_ready"
            blockers.append({"code": "missing_roadmap_link"})
            next_safe_action = "Create or restore a roadmap work item link before starting."
            return {
                "ok": True,
                "work_item_id": work_item_id,
                "project_id": work_item.get("project_id", DEFAULT_PROJECT_ID),
                "readiness_status": readiness_status,
                "ready": ready,
                "next_safe_action": next_safe_action,
                "blockers": blockers,
                "warnings": warnings,
                "work_item": work_item,
                "roadmap_links": roadmap_links,
                "dependency_summary": dependency_summary,
                "related_events": related_events,
            }

        if cancelled_link_present:
            readiness_status = "cancelled"
            blockers.append({"code": "roadmap_task_cancelled"})
            next_safe_action = "Do not start. Roadmap task is cancelled."
        elif unsatisfied_dependencies:
            readiness_status = "blocked"
            blockers.append(
                {
                    "code": "unsatisfied_roadmap_dependencies",
                    "dependencies": unsatisfied_dependencies,
                }
            )
            next_safe_action = "Complete dependency roadmap tasks before starting."
        else:
            readiness_status = "ready"
            ready = True
            next_safe_action = "Start work item or assign to operator."
    else:
        warnings.append({"code": "unexpected_work_item_status", "status": status})

    return {
        "ok": True,
        "work_item_id": work_item_id,
        "project_id": work_item.get("project_id", DEFAULT_PROJECT_ID),
        "readiness_status": readiness_status,
        "ready": ready,
        "next_safe_action": next_safe_action,
        "blockers": blockers,
        "warnings": warnings,
        "work_item": work_item,
        "roadmap_links": roadmap_links,
        "dependency_summary": dependency_summary,
        "related_events": related_events,
    }


def inspect_queue_readiness(
    conn: Connection,
    queue_id: str | None = None,
    project_id: str = DEFAULT_PROJECT_ID,
) -> dict[str, Any]:
    params: list[Any] = [project_id]
    queue_clause = ""
    if queue_id is not None:
        queue_clause = " AND queue_id = %s"
        params.append(queue_id)
    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT id
            FROM work_items
            WHERE project_id = %s
              AND status IN ('queued', 'active', 'blocked'){queue_clause}
            ORDER BY queue_id ASC, status ASC, created_at ASC, id ASC
            """,
            params,
        )
        ids = [row["id"] for row in cur.fetchall()]

    items = [inspect_work_item_readiness(conn, work_item_id) for work_item_id in ids]
    counts = {status: 0 for status in WORK_ITEM_READINESS_STATUSES}
    for item in items:
        readiness_status = item.get("readiness_status")
        if readiness_status in counts:
            counts[readiness_status] += 1

    return {
        "ok": True,
        "project_id": project_id,
        "queue_id": queue_id,
        "counts": counts,
        "total_items": len(items),
        "work_items": items,
        "next_ready_work_items": [
            item for item in items if item.get("readiness_status") == "ready" and bool(item.get("ready"))
        ],
        "blocked_work_items": [item for item in items if item.get("readiness_status") == "blocked"],
    }


def render_work_item_readiness_markdown(payload: dict[str, Any]) -> str:
    work_item = payload.get("work_item") or {}
    lines = [
        "# Work Item Readiness",
        "",
        f"- Work item ID: `{payload.get('work_item_id', work_item.get('id', ''))}`",
        f"- Status: `{work_item.get('status', '')}`",
        f"- Ready: `{payload.get('ready', False)}`",
        f"- Readiness status: `{payload.get('readiness_status', '')}`",
        f"- Next safe action: {payload.get('next_safe_action', '')}",
        "",
        "## Blockers",
    ]
    blockers = payload.get("blockers", [])
    if blockers:
        for blocker in blockers:
            lines.append(f"- `{blocker.get('code', 'unknown')}` {json.dumps(blocker, sort_keys=True)}")
    else:
        lines.append("- none")
    lines.append("")
    lines.append("## Warnings")
    warnings = payload.get("warnings", [])
    if warnings:
        for warning in warnings:
            lines.append(f"- `{warning.get('code', 'warning')}` {json.dumps(warning, sort_keys=True)}")
    else:
        lines.append("- none")
    lines.append("")
    lines.append("## Roadmap Links")
    roadmap_links = payload.get("roadmap_links", [])
    if roadmap_links:
        for link in roadmap_links:
            lines.append(
                f"- `{link['id']}` task=`{link['roadmap_task_id']}` task_status=`{link.get('roadmap_task_status', '')}` link_status=`{link['status']}`"
            )
    else:
        lines.append("- none")
    lines.append("")
    lines.append("## Dependencies")
    dependency_summary = payload.get("dependency_summary", {})
    lines.append(f"- Total dependencies: `{dependency_summary.get('total_dependencies', 0)}`")
    unsatisfied = dependency_summary.get("unsatisfied_dependencies", [])
    if unsatisfied:
        for dependency in unsatisfied:
            lines.append(
                f"- task=`{dependency.get('task_id', '')}` depends_on=`{dependency.get('depends_on_task_id', '')}` status=`{dependency.get('status', '')}`"
            )
    else:
        lines.append("- Unsatisfied dependencies: none")
    return "\n".join(lines).rstrip() + "\n"


def render_queue_readiness_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Queue Readiness",
        "",
        f"- Project ID: `{payload.get('project_id', '')}`",
        f"- Queue ID filter: `{payload.get('queue_id') or 'all'}`",
        f"- Total items: `{payload.get('total_items', 0)}`",
        "",
        "## Counts",
    ]
    counts = payload.get("counts", {})
    for status in WORK_ITEM_READINESS_STATUSES:
        lines.append(f"- `{status}`: `{counts.get(status, 0)}`")
    lines.append("")
    lines.append("## Next Ready Work Items")
    ready_items = payload.get("next_ready_work_items", [])
    if ready_items:
        for item in ready_items:
            work_item = item.get("work_item") or {}
            lines.append(
                f"- `{item.get('work_item_id', '')}` queue=`{work_item.get('queue_id', '')}` status=`{work_item.get('status', '')}` next=`{item.get('next_safe_action', '')}`"
            )
    else:
        lines.append("- none")
    lines.append("")
    lines.append("## Blocked Work Items")
    blocked_items = payload.get("blocked_work_items", [])
    if blocked_items:
        for item in blocked_items:
            lines.append(
                f"- `{item.get('work_item_id', '')}` blockers={json.dumps(item.get('blockers', []), sort_keys=True)}"
            )
    else:
        lines.append("- none")
    return "\n".join(lines).rstrip() + "\n"


def render_start_work_item_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Start Work Item",
        "",
        f"- Work item ID: `{payload.get('work_item_id', '')}`",
        f"- Changed: `{payload.get('changed', False)}`",
        f"- Previous status: `{payload.get('previous_status', '')}`",
        f"- New status: `{payload.get('new_status', '')}`",
        f"- Readiness status: `{payload.get('readiness_status', '')}`",
        f"- Reason: `{payload.get('reason', '')}`",
        f"- Next safe action: {payload.get('next_safe_action', '')}",
        "",
        "## Blockers",
    ]
    blockers = (payload.get("readiness") or {}).get("blockers", [])
    if blockers:
        for blocker in blockers:
            lines.append(f"- `{blocker.get('code', 'unknown')}` {json.dumps(blocker, sort_keys=True)}")
    else:
        lines.append("- none")
    lines.append("")
    lines.append("## Roadmap Links")
    roadmap_links = payload.get("roadmap_links", [])
    if roadmap_links:
        for link in roadmap_links:
            lines.append(
                f"- `{link.get('id', '')}` task=`{link.get('roadmap_task_id', '')}` link_status=`{link.get('status', '')}`"
            )
    else:
        lines.append("- none")
    return "\n".join(lines).rstrip() + "\n"


def plan_work_item_queue_transition(
    conn: Connection,
    work_item_id: str,
    target_queue_id: str,
) -> dict[str, Any]:
    work_item = inspect_work_item(conn, work_item_id)
    if work_item is None:
        return {
            "ok": False,
            "work_item_id": work_item_id,
            "project_id": DEFAULT_PROJECT_ID,
            "can_transition": False,
            "changed": False,
            "transition_status": "missing",
            "reason": "work_item_not_found",
            "next_safe_action": "Create or inspect the local work item before moving queues.",
            "blockers": [{"code": "work_item_not_found", "work_item_id": work_item_id}],
            "warnings": [],
            "work_item": None,
            "current_queue": None,
            "target_queue": None,
            "allowed_next_queues": [],
        }

    current_queue_id = work_item.get("queue_id")
    current_queue = inspect_queue(conn, current_queue_id) if current_queue_id else None
    target_queue = inspect_queue(conn, target_queue_id)
    allowed_next_queues = list(work_item.get("queue_allowed_next_queues") or [])
    readiness = inspect_work_item_readiness(conn, work_item_id)

    if target_queue is None:
        return {
            "ok": False,
            "work_item_id": work_item_id,
            "project_id": work_item.get("project_id", DEFAULT_PROJECT_ID),
            "can_transition": False,
            "changed": False,
            "transition_status": "missing_target_queue",
            "reason": "target_queue_not_found",
            "next_safe_action": "Inspect available queues before moving work items.",
            "blockers": [{"code": "target_queue_not_found", "target_queue_id": target_queue_id}],
            "warnings": [],
            "work_item": work_item,
            "current_queue": current_queue,
            "target_queue": None,
            "allowed_next_queues": allowed_next_queues,
            "readiness": readiness,
        }

    status = work_item.get("status")
    if status == "cancelled":
        return {
            "ok": True,
            "work_item_id": work_item_id,
            "project_id": work_item.get("project_id", DEFAULT_PROJECT_ID),
            "can_transition": False,
            "changed": False,
            "transition_status": "cancelled",
            "reason": "work_item_cancelled",
            "next_safe_action": "No queue move. Work item is cancelled.",
            "blockers": [],
            "warnings": [],
            "work_item": work_item,
            "current_queue": current_queue,
            "target_queue": target_queue,
            "allowed_next_queues": allowed_next_queues,
            "readiness": readiness,
        }

    if status == "complete":
        return {
            "ok": True,
            "work_item_id": work_item_id,
            "project_id": work_item.get("project_id", DEFAULT_PROJECT_ID),
            "can_transition": False,
            "changed": False,
            "transition_status": "already_complete",
            "reason": "work_item_complete",
            "next_safe_action": "No queue move. Work item is complete.",
            "blockers": [],
            "warnings": [],
            "work_item": work_item,
            "current_queue": current_queue,
            "target_queue": target_queue,
            "allowed_next_queues": allowed_next_queues,
            "readiness": readiness,
        }

    if current_queue_id == target_queue_id:
        return {
            "ok": True,
            "work_item_id": work_item_id,
            "project_id": work_item.get("project_id", DEFAULT_PROJECT_ID),
            "can_transition": False,
            "changed": False,
            "transition_status": "already_in_target_queue",
            "reason": "already_in_target_queue",
            "next_safe_action": "No queue move needed.",
            "blockers": [],
            "warnings": [],
            "work_item": work_item,
            "current_queue": current_queue,
            "target_queue": target_queue,
            "allowed_next_queues": allowed_next_queues,
            "readiness": readiness,
        }

    if target_queue_id not in allowed_next_queues:
        return {
            "ok": True,
            "work_item_id": work_item_id,
            "project_id": work_item.get("project_id", DEFAULT_PROJECT_ID),
            "can_transition": False,
            "changed": False,
            "transition_status": "blocked",
            "reason": "target_queue_not_allowed",
            "next_safe_action": "Choose one of the allowed next queues.",
            "blockers": [
                {
                    "code": "target_queue_not_allowed",
                    "current_queue_id": current_queue_id,
                    "target_queue_id": target_queue_id,
                }
            ],
            "warnings": [],
            "work_item": work_item,
            "current_queue": current_queue,
            "target_queue": target_queue,
            "allowed_next_queues": allowed_next_queues,
            "readiness": readiness,
        }

    return {
        "ok": True,
        "work_item_id": work_item_id,
        "project_id": work_item.get("project_id", DEFAULT_PROJECT_ID),
        "can_transition": True,
        "changed": False,
        "transition_status": "ready",
        "reason": "transition_allowed",
        "next_safe_action": "Move work item to target queue.",
        "blockers": [],
        "warnings": [],
        "work_item": work_item,
        "current_queue": current_queue,
        "target_queue": target_queue,
        "allowed_next_queues": allowed_next_queues,
        "readiness": readiness,
    }


def move_work_item_queue_if_allowed(
    conn: Connection,
    work_item_id: str,
    target_queue_id: str,
    *,
    actor: str = "local-operator",
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    plan = plan_work_item_queue_transition(conn, work_item_id, target_queue_id)
    if not bool(plan.get("ok")) or not bool(plan.get("can_transition")):
        return {
            "ok": bool(plan.get("ok")),
            "changed": False,
            "work_item_id": work_item_id,
            "target_queue_id": target_queue_id,
            "transition_status": plan.get("transition_status", "blocked"),
            "reason": plan.get("reason", "transition_not_allowed"),
            "next_safe_action": plan.get("next_safe_action"),
            "blockers": plan.get("blockers", []),
            "plan": plan,
        }

    normalized_details = _normalize_roadmap_details(details)
    project_id = str(plan.get("project_id") or DEFAULT_PROJECT_ID)
    previous_queue_id = str((plan.get("work_item") or {}).get("queue_id") or "")
    audit_event_id = _new_id("audit")
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE work_items
            SET queue_id = %s,
                updated_at = NOW()
            WHERE id = %s
            """,
            (target_queue_id, work_item_id),
        )
        cur.execute(
            """
            INSERT INTO audit_events (id, project_id, work_item_id, event_type, actor, details)
            VALUES (%s, %s, %s, %s, %s, %s::jsonb)
            """,
            (
                audit_event_id,
                project_id,
                work_item_id,
                "work_item_queue_changed",
                actor,
                json.dumps(
                    {
                        "work_item_id": work_item_id,
                        "previous_queue_id": previous_queue_id,
                        "new_queue_id": target_queue_id,
                        **normalized_details,
                    }
                ),
            ),
        )
        cur.execute(
            """
            SELECT id, roadmap_task_id
            FROM roadmap_work_item_links
            WHERE work_item_id = %s
              AND status = 'active'
            ORDER BY created_at DESC, id DESC
            LIMIT 1
            """,
            (work_item_id,),
        )
        link_row = cur.fetchone()

    roadmap_event_ids: list[str] = []
    if link_row is not None:
        roadmap_event = add_roadmap_event(
            conn,
            project_id=project_id,
            event_type="work_item_queue_changed",
            actor=actor,
            summary=f"Work item queue changed: {previous_queue_id} -> {target_queue_id}",
            details={
                "work_item_id": work_item_id,
                "roadmap_task_id": link_row["roadmap_task_id"],
                "previous_queue_id": previous_queue_id,
                "new_queue_id": target_queue_id,
                **normalized_details,
            },
            task_id=link_row["roadmap_task_id"],
        )
        if bool(roadmap_event.get("ok")):
            roadmap_event_ids.append(roadmap_event["event_id"])

    return {
        "ok": True,
        "changed": True,
        "work_item_id": work_item_id,
        "previous_queue_id": previous_queue_id,
        "new_queue_id": target_queue_id,
        "transition_status": "moved",
        "reason": "transition_applied",
        "next_safe_action": "Inspect queue readiness or continue work item lifecycle.",
        "blockers": [],
        "event_ids": {
            "audit_event_ids": [audit_event_id],
            "roadmap_event_ids": roadmap_event_ids,
        },
        "plan": plan,
    }


def render_work_item_queue_transition_plan_markdown(payload: dict[str, Any]) -> str:
    current_queue = payload.get("current_queue") or {}
    target_queue = payload.get("target_queue") or {}
    lines = [
        "# Queue Transition Plan",
        "",
        f"- Work item ID: `{payload.get('work_item_id', '')}`",
        f"- Current queue: `{current_queue.get('id', '')}`",
        f"- Target queue: `{target_queue.get('id', '')}`",
        f"- Can transition: `{payload.get('can_transition', False)}`",
        f"- Transition status: `{payload.get('transition_status', '')}`",
        f"- Reason: `{payload.get('reason', '')}`",
        f"- Next safe action: {payload.get('next_safe_action', '')}",
        "",
        "## Blockers",
    ]
    blockers = payload.get("blockers", [])
    if blockers:
        for blocker in blockers:
            lines.append(f"- `{blocker.get('code', 'unknown')}` {json.dumps(blocker, sort_keys=True)}")
    else:
        lines.append("- none")
    lines.extend(["", "## Allowed Next Queues"])
    allowed = payload.get("allowed_next_queues", [])
    if allowed:
        for queue_id in allowed:
            lines.append(f"- `{queue_id}`")
    else:
        lines.append("- none")
    lines.extend(["", "## Readiness"])
    readiness = payload.get("readiness") or {}
    lines.append(f"- Status: `{readiness.get('readiness_status', 'missing')}`")
    lines.append(f"- Ready: `{readiness.get('ready', False)}`")
    lines.append(f"- Next safe action: {readiness.get('next_safe_action', '')}")
    return "\n".join(lines).rstrip() + "\n"


def render_move_work_item_queue_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Move Work Item Queue",
        "",
        f"- Work item ID: `{payload.get('work_item_id', '')}`",
        f"- Changed: `{payload.get('changed', False)}`",
        f"- Previous queue: `{payload.get('previous_queue_id', '')}`",
        f"- New queue: `{payload.get('new_queue_id', payload.get('target_queue_id', ''))}`",
        f"- Transition status: `{payload.get('transition_status', '')}`",
        f"- Reason: `{payload.get('reason', '')}`",
        f"- Next safe action: {payload.get('next_safe_action', '')}",
        "",
        "## Blockers",
    ]
    blockers = payload.get("blockers", [])
    if blockers:
        for blocker in blockers:
            lines.append(f"- `{blocker.get('code', 'unknown')}` {json.dumps(blocker, sort_keys=True)}")
    else:
        lines.append("- none")
    return "\n".join(lines).rstrip() + "\n"


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


ROADMAP_SEED_AREAS: tuple[dict[str, Any], ...] = (
    {"id": "ra-recovery-reconciliation", "name": "Recovery and Source-of-Truth Reconciliation"},
    {"id": "ra-state-authority-lifecycle", "name": "State Authority and Lifecycle Model"},
    {"id": "ra-managed-standardization", "name": "Managed Project Standardization"},
    {"id": "ra-hub-command-center", "name": "Hub Command Center"},
    {"id": "ra-local-queue-intake", "name": "Local Queue and Work Intake"},
    {"id": "ra-agent-execution-runtime", "name": "Agent Execution Runtime"},
    {"id": "ra-validation-doc-agents", "name": "Validation and Documentation Agents"},
    {"id": "ra-agent-handoff", "name": "Agent-to-Agent Handoff"},
    {"id": "ra-llm-provider-routing", "name": "LLM Provider Routing"},
    {"id": "ra-github-sync-mutation", "name": "GitHub Sync and Mutation"},
    {"id": "ra-reporting-audit", "name": "Reporting, Audit, and Completion Tracking"},
    {"id": "ra-production-hardening", "name": "Production Hardening"},
)

ROADMAP_SEED_MILESTONES: tuple[dict[str, Any], ...] = (
    {"id": "rm-01-audit-baseline", "name": "Audit baseline acceptance and source-of-truth reconciliation", "area_id": "ra-recovery-reconciliation"},
    {"id": "rm-02-state-authority", "name": "State authority matrix and lifecycle contract", "area_id": "ra-state-authority-lifecycle"},
    {"id": "rm-03-standardization", "name": "Managed-project standardization generator and verifier", "area_id": "ra-managed-standardization"},
    {"id": "rm-04-hub-workbench", "name": "Hub roadmap visibility and active-project workbench alignment", "area_id": "ra-hub-command-center"},
    {"id": "rm-05-queue-to-execution", "name": "Local queue-to-agent execution MVP using mock provider first", "area_id": "ra-agent-execution-runtime"},
    {"id": "rm-06-validation-gates", "name": "Validation and documentation post-run gates", "area_id": "ra-validation-doc-agents"},
    {"id": "rm-07-handoff-protocol", "name": "Agent-to-agent context handoff protocol", "area_id": "ra-agent-handoff"},
    {"id": "rm-08-routing-contract", "name": "Provider-neutral LLM routing contract", "area_id": "ra-llm-provider-routing"},
    {"id": "rm-09-github-gates", "name": "Optional GitHub sync/mutation reintroduction behind gates", "area_id": "ra-github-sync-mutation"},
    {"id": "rm-10-production-ready", "name": "Production hardening and release readiness", "area_id": "ra-production-hardening"},
)
ROADMAP_ALLOWED_STATUSES: tuple[str, ...] = (
    "planned",
    "active",
    "blocked",
    "complete",
    "cancelled",
)
WORK_ITEM_ALLOWED_STATUSES: tuple[str, ...] = (
    "queued",
    "active",
    "blocked",
    "complete",
    "cancelled",
)
WORK_ITEM_READINESS_STATUSES: tuple[str, ...] = (
    "ready",
    "not_ready",
    "blocked",
    "already_active",
    "already_complete",
    "cancelled",
    "missing",
)


def _roadmap_seed_tasks() -> list[dict[str, Any]]:
    return [
        {
            "id": f"rt-{index:02d}-starter",
            "milestone_id": milestone["id"],
            "title": f"Define starter scope for {milestone['name']}",
            "description": "Capture the high-level implementation and acceptance boundaries for this milestone.",
            "status": "planned",
            "priority": "normal",
        }
        for index, milestone in enumerate(ROADMAP_SEED_MILESTONES, start=1)
    ]


def seed_aresforge_roadmap(conn: Connection) -> dict[str, Any]:
    tasks = _roadmap_seed_tasks()
    with conn.cursor() as cur:
        for sort_order, area in enumerate(ROADMAP_SEED_AREAS, start=1):
            cur.execute(
                """
                INSERT INTO roadmap_areas (id, project_id, name, status, sort_order, metadata)
                VALUES (%s, %s, %s, %s, %s, %s::jsonb)
                ON CONFLICT (id) DO UPDATE
                SET project_id = EXCLUDED.project_id,
                    name = EXCLUDED.name,
                    status = EXCLUDED.status,
                    sort_order = EXCLUDED.sort_order,
                    updated_at = NOW()
                """,
                (area["id"], DEFAULT_PROJECT_ID, area["name"], "planned", sort_order, json.dumps({})),
            )
        for sort_order, milestone in enumerate(ROADMAP_SEED_MILESTONES, start=1):
            cur.execute(
                """
                INSERT INTO roadmap_milestones (id, project_id, area_id, name, status, sort_order, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
                ON CONFLICT (id) DO UPDATE
                SET project_id = EXCLUDED.project_id,
                    area_id = EXCLUDED.area_id,
                    name = EXCLUDED.name,
                    status = EXCLUDED.status,
                    sort_order = EXCLUDED.sort_order,
                    updated_at = NOW()
                """,
                (
                    milestone["id"],
                    DEFAULT_PROJECT_ID,
                    milestone["area_id"],
                    milestone["name"],
                    "planned",
                    sort_order,
                    json.dumps({}),
                ),
            )
        for sort_order, task in enumerate(tasks, start=1):
            cur.execute(
                """
                INSERT INTO roadmap_tasks (
                    id, project_id, milestone_id, title, description, status, priority, sort_order, metadata
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                ON CONFLICT (id) DO UPDATE
                SET project_id = EXCLUDED.project_id,
                    milestone_id = EXCLUDED.milestone_id,
                    title = EXCLUDED.title,
                    description = EXCLUDED.description,
                    status = EXCLUDED.status,
                    priority = EXCLUDED.priority,
                    sort_order = EXCLUDED.sort_order,
                    updated_at = NOW()
                """,
                (
                    task["id"],
                    DEFAULT_PROJECT_ID,
                    task["milestone_id"],
                    task["title"],
                    task["description"],
                    task["status"],
                    task["priority"],
                    sort_order,
                    json.dumps({}),
                ),
            )
        cur.execute(
            """
            INSERT INTO roadmap_events (id, project_id, event_type, actor, summary, details)
            VALUES (%s, %s, %s, %s, %s, %s::jsonb)
            ON CONFLICT (id) DO UPDATE
            SET summary = EXCLUDED.summary,
                details = EXCLUDED.details
            """,
            (
                "roadmap-event-seed-aresforge",
                DEFAULT_PROJECT_ID,
                "roadmap_seed",
                "aresforge-cli",
                "Seeded foundational roadmap control entities.",
                json.dumps(
                    {
                        "area_ids": [item["id"] for item in ROADMAP_SEED_AREAS],
                        "milestone_ids": [item["id"] for item in ROADMAP_SEED_MILESTONES],
                        "task_ids": [item["id"] for item in tasks],
                    }
                ),
            ),
        )

    return {
        "ok": True,
        "project_id": DEFAULT_PROJECT_ID,
        "seeded": {
            "areas": len(ROADMAP_SEED_AREAS),
            "milestones": len(ROADMAP_SEED_MILESTONES),
            "tasks": len(tasks),
        },
        "seeded_ids": {
            "areas": [item["id"] for item in ROADMAP_SEED_AREAS],
            "milestones": [item["id"] for item in ROADMAP_SEED_MILESTONES],
            "tasks": [item["id"] for item in tasks],
        },
        "event_id": "roadmap-event-seed-aresforge",
    }


def inspect_roadmap_db(conn: Connection) -> dict[str, Any]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, project_id, name, description, status, sort_order, metadata, created_at, updated_at
            FROM roadmap_areas
            ORDER BY sort_order, id
            """
        )
        areas = list(cur.fetchall())
        cur.execute(
            """
            SELECT id, project_id, area_id, name, description, status, sort_order, metadata, created_at, updated_at
            FROM roadmap_milestones
            ORDER BY sort_order, id
            """
        )
        milestones = list(cur.fetchall())
        cur.execute(
            """
            SELECT id, project_id, milestone_id, title, description, status, priority, sort_order, metadata, created_at, updated_at
            FROM roadmap_tasks
            ORDER BY sort_order, id
            """
        )
        tasks = list(cur.fetchall())
        cur.execute(
            """
            SELECT task_id, depends_on_task_id, dependency_type, metadata, created_at
            FROM roadmap_task_dependencies
            ORDER BY task_id, depends_on_task_id
            """
        )
        dependencies = list(cur.fetchall())
        cur.execute(
            """
            SELECT id, project_id, area_id, milestone_id, task_id, event_type, actor, summary, details, created_at
            FROM roadmap_events
            ORDER BY created_at DESC, id DESC
            LIMIT 50
            """
        )
        events = list(cur.fetchall())
        cur.execute("SELECT to_regclass('public.roadmap_work_item_links') AS table_name")
        links_table = cur.fetchone()
        if links_table is not None and links_table.get("table_name"):
            cur.execute(
                """
                SELECT id
                FROM roadmap_work_item_links
                """
            )
            links = list(cur.fetchall())
        else:
            links = []
    return {
        "ok": True,
        "project_id": DEFAULT_PROJECT_ID,
        "counts": {
            "areas": len(areas),
            "milestones": len(milestones),
            "tasks": len(tasks),
            "task_dependencies": len(dependencies),
            "events": len(events),
            "roadmap_work_item_links": len(links),
        },
        "areas": areas,
        "milestones": milestones,
        "tasks": tasks,
        "task_dependencies": dependencies,
        "events": events,
    }


def _normalize_roadmap_details(details: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(details, dict):
        return {}
    return details


def _invalid_status_payload(status: str) -> dict[str, Any]:
    return {
        "ok": False,
        "error": "invalid_status",
        "status": status,
        "allowed_statuses": list(ROADMAP_ALLOWED_STATUSES),
    }


def add_roadmap_event(
    conn: Connection,
    project_id: str,
    event_type: str,
    actor: str = "aresforge-cli",
    summary: str = "",
    details: dict[str, Any] | None = None,
    area_id: str | None = None,
    milestone_id: str | None = None,
    task_id: str | None = None,
) -> dict[str, Any]:
    normalized_details = _normalize_roadmap_details(details)
    with conn.cursor() as cur:
        if area_id is not None:
            cur.execute("SELECT id FROM roadmap_areas WHERE id = %s", (area_id,))
            if cur.fetchone() is None:
                return {"ok": False, "error": "area_not_found", "area_id": area_id}
        if milestone_id is not None:
            cur.execute("SELECT id FROM roadmap_milestones WHERE id = %s", (milestone_id,))
            if cur.fetchone() is None:
                return {"ok": False, "error": "milestone_not_found", "milestone_id": milestone_id}
        if task_id is not None:
            cur.execute("SELECT id FROM roadmap_tasks WHERE id = %s", (task_id,))
            if cur.fetchone() is None:
                return {"ok": False, "error": "task_not_found", "task_id": task_id}

        event_id = _new_id("roadmap-event")
        cur.execute(
            """
            INSERT INTO roadmap_events (
                id, project_id, area_id, milestone_id, task_id, event_type, actor, summary, details
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
            RETURNING id, project_id, area_id, milestone_id, task_id, event_type, actor, summary, details, created_at
            """,
            (
                event_id,
                project_id,
                area_id,
                milestone_id,
                task_id,
                event_type,
                actor,
                summary,
                json.dumps(normalized_details),
            ),
        )
        event_row = cur.fetchone()

    return {"ok": True, "event_id": event_id, "event": event_row}


def _update_roadmap_entity_status(
    conn: Connection,
    *,
    entity_type: str,
    entity_id: str,
    status: str,
    actor: str,
    summary: str | None,
    details: dict[str, Any] | None,
) -> dict[str, Any]:
    table_map = {
        "area": "roadmap_areas",
        "milestone": "roadmap_milestones",
        "task": "roadmap_tasks",
    }
    event_type_map = {
        "area": "roadmap_area_status_changed",
        "milestone": "roadmap_milestone_status_changed",
        "task": "roadmap_task_status_changed",
    }
    not_found_error_map = {
        "area": "area_not_found",
        "milestone": "milestone_not_found",
        "task": "task_not_found",
    }
    if status not in ROADMAP_ALLOWED_STATUSES:
        return _invalid_status_payload(status)

    table_name = table_map[entity_type]
    id_column = "id"
    normalized_details = _normalize_roadmap_details(details)
    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT id, project_id, status, updated_at
            FROM {table_name}
            WHERE {id_column} = %s
            """,
            (entity_id,),
        )
        existing = cur.fetchone()
        if existing is None:
            return {"ok": False, "error": not_found_error_map[entity_type], f"{entity_type}_id": entity_id}

        previous_status = existing["status"]
        if previous_status == status:
            return {
                "ok": True,
                "changed": False,
                "previous_status": previous_status,
                "status": status,
                f"{entity_type}_id": entity_id,
            }

        cur.execute(
            f"""
            UPDATE {table_name}
            SET status = %s,
                updated_at = NOW()
            WHERE {id_column} = %s
            RETURNING id, project_id, status, updated_at
            """,
            (status, entity_id),
        )
        updated = cur.fetchone()

        event_details = {
            "previous_status": previous_status,
            "new_status": status,
            "target_id": entity_id,
            "target_type": entity_type,
            **normalized_details,
        }
        event_summary = summary or f"{entity_type.capitalize()} status changed: {previous_status} -> {status}"
        event_payload = add_roadmap_event(
            conn,
            project_id=updated["project_id"],
            event_type=event_type_map[entity_type],
            actor=actor,
            summary=event_summary,
            details=event_details,
            area_id=entity_id if entity_type == "area" else None,
            milestone_id=entity_id if entity_type == "milestone" else None,
            task_id=entity_id if entity_type == "task" else None,
        )
        if not bool(event_payload.get("ok")):
            return event_payload

    return {
        "ok": True,
        "changed": True,
        "previous_status": previous_status,
        "status": status,
        "event_id": event_payload["event_id"],
        entity_type: updated,
    }


def update_roadmap_task_status(
    conn: Connection,
    task_id: str,
    status: str,
    actor: str = "aresforge-cli",
    summary: str | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _update_roadmap_entity_status(
        conn,
        entity_type="task",
        entity_id=task_id,
        status=status,
        actor=actor,
        summary=summary,
        details=details,
    )


def update_roadmap_milestone_status(
    conn: Connection,
    milestone_id: str,
    status: str,
    actor: str = "aresforge-cli",
    summary: str | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _update_roadmap_entity_status(
        conn,
        entity_type="milestone",
        entity_id=milestone_id,
        status=status,
        actor=actor,
        summary=summary,
        details=details,
    )


def update_roadmap_area_status(
    conn: Connection,
    area_id: str,
    status: str,
    actor: str = "aresforge-cli",
    summary: str | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _update_roadmap_entity_status(
        conn,
        entity_type="area",
        entity_id=area_id,
        status=status,
        actor=actor,
        summary=summary,
        details=details,
    )


def inspect_roadmap_events(
    conn: Connection,
    project_id: str = DEFAULT_PROJECT_ID,
    limit: int = 20,
) -> dict[str, Any]:
    if limit < 1:
        return {"ok": False, "error": "invalid_limit", "limit": limit}
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, project_id, area_id, milestone_id, task_id, event_type, actor, summary, details, created_at
            FROM roadmap_events
            WHERE project_id = %s
            ORDER BY created_at DESC, id DESC
            LIMIT %s
            """,
            (project_id, limit),
        )
        events = list(cur.fetchall())
    return {
        "ok": True,
        "project_id": project_id,
        "event_count": len(events),
        "events": events,
    }


def create_work_item_from_roadmap_task(
    conn: Connection,
    roadmap_task_id: str,
    queue_id: str | None = None,
    priority: str = "normal",
    actor: str = "aresforge-cli",
    summary: str | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_details = _normalize_roadmap_details(details)
    candidate_queue_ids = [queue_id] if queue_id else ["queue-planning", "queue-intake"]

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, project_id, milestone_id, title, description, status, priority, sort_order, metadata, created_at, updated_at
            FROM roadmap_tasks
            WHERE id = %s
            """,
            (roadmap_task_id,),
        )
        task = cur.fetchone()
        if task is None:
            return {"ok": False, "error": "roadmap_task_not_found", "roadmap_task_id": roadmap_task_id}
        if task["status"] == "cancelled":
            return {"ok": False, "error": "roadmap_task_cancelled", "roadmap_task_id": roadmap_task_id}

        cur.execute(
            """
            SELECT rwil.id, rwil.project_id, rwil.roadmap_task_id, rwil.work_item_id, rwil.link_type, rwil.status, rwil.metadata, rwil.created_at, rwil.updated_at,
                   wi.queue_id
            FROM roadmap_work_item_links rwil
            JOIN work_items wi ON wi.id = rwil.work_item_id
            WHERE rwil.roadmap_task_id = %s
              AND rwil.status = 'active'
            ORDER BY rwil.created_at DESC, rwil.id DESC
            LIMIT 1
            """,
            (roadmap_task_id,),
        )
        existing_link = cur.fetchone()
        if existing_link is not None:
            return {
                "ok": True,
                "created": False,
                "existing": True,
                "roadmap_task_id": roadmap_task_id,
                "work_item_id": existing_link["work_item_id"],
                "link_id": existing_link["id"],
                "queue_id": existing_link["queue_id"],
            }

        resolved_queue_id: str | None = None
        for candidate_queue_id in candidate_queue_ids:
            if candidate_queue_id is None:
                continue
            cur.execute("SELECT id FROM queues WHERE id = %s", (candidate_queue_id,))
            queue_row = cur.fetchone()
            if queue_row is not None:
                resolved_queue_id = queue_row["id"]
                break
        if resolved_queue_id is None:
            return {
                "ok": False,
                "error": "queue_not_found",
                "queue_id": queue_id or "queue-planning",
            }

        work_item_id = _new_id("work")
        work_item_metadata = {
            "source": "roadmap_task",
            "roadmap_task_id": task["id"],
            "roadmap_milestone_id": task["milestone_id"],
            "roadmap_task_status": task["status"],
        }
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
                      title, description, status, priority, route_status, metadata, created_at, updated_at
            """,
            (
                work_item_id,
                task["project_id"],
                resolved_queue_id,
                None,
                None,
                None,
                task["title"],
                task["description"],
                "queued",
                priority,
                "queued",
                json.dumps(work_item_metadata),
            ),
        )
        work_item = cur.fetchone()

        link_id = _new_id("roadmap-work-link")
        cur.execute(
            """
            INSERT INTO roadmap_work_item_links (
                id, project_id, roadmap_task_id, work_item_id, link_type, status, metadata
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
            RETURNING id, project_id, roadmap_task_id, work_item_id, link_type, status, metadata, created_at, updated_at
            """,
            (
                link_id,
                task["project_id"],
                task["id"],
                work_item_id,
                "implements",
                "active",
                json.dumps({}),
            ),
        )
        link = cur.fetchone()

        event_summary = summary or "Created local work item from roadmap task."
        event_details: dict[str, Any] = {
            "roadmap_task_id": task["id"],
            "work_item_id": work_item_id,
            "queue_id": resolved_queue_id,
            "link_id": link_id,
            **normalized_details,
        }
        event_payload = add_roadmap_event(
            conn,
            project_id=task["project_id"],
            event_type="roadmap_task_work_item_created",
            actor=actor,
            summary=event_summary,
            details=event_details,
            milestone_id=task["milestone_id"],
            task_id=task["id"],
        )
        if not bool(event_payload.get("ok")):
            return event_payload

    return {
        "ok": True,
        "created": True,
        "existing": False,
        "project_id": task["project_id"],
        "roadmap_task_id": task["id"],
        "work_item_id": work_item_id,
        "link_id": link_id,
        "queue_id": resolved_queue_id,
        "event_id": event_payload["event_id"],
        "work_item": work_item,
        "link": link,
    }


def inspect_roadmap_work_item_links(
    conn: Connection,
    project_id: str = DEFAULT_PROJECT_ID,
    roadmap_task_id: str | None = None,
    work_item_id: str | None = None,
) -> dict[str, Any]:
    conditions = ["rwil.project_id = %s"]
    params: list[Any] = [project_id]
    if roadmap_task_id:
        conditions.append("rwil.roadmap_task_id = %s")
        params.append(roadmap_task_id)
    if work_item_id:
        conditions.append("rwil.work_item_id = %s")
        params.append(work_item_id)
    where_clause = " AND ".join(conditions)

    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT rwil.id, rwil.project_id, rwil.roadmap_task_id, rwil.work_item_id, rwil.link_type, rwil.status,
                   rwil.metadata, rwil.created_at, rwil.updated_at,
                   rt.title AS roadmap_task_title, rt.status AS roadmap_task_status,
                   wi.title AS work_item_title, wi.status AS work_item_status, wi.queue_id
            FROM roadmap_work_item_links rwil
            JOIN roadmap_tasks rt ON rt.id = rwil.roadmap_task_id
            JOIN work_items wi ON wi.id = rwil.work_item_id
            WHERE {where_clause}
            ORDER BY rwil.created_at DESC, rwil.id DESC
            """,
            params,
        )
        links = list(cur.fetchall())

    return {
        "ok": True,
        "project_id": project_id,
        "roadmap_task_id": roadmap_task_id,
        "work_item_id": work_item_id,
        "link_count": len(links),
        "links": links,
    }


def render_roadmap_work_item_links_markdown(payload: dict[str, Any]) -> str:
    links = payload.get("links", [])
    lines = [
        "# Roadmap Work Item Links",
        "",
        f"- Project ID: `{payload.get('project_id', '')}`",
        f"- Link count: `{payload.get('link_count', len(links))}`",
        "",
    ]
    for link in links:
        lines.append(
            f"- `{link['id']}` task=`{link['roadmap_task_id']}` -> work_item=`{link['work_item_id']}` status=`{link['status']}` queue=`{link.get('queue_id', '')}`"
        )
        if link.get("roadmap_task_title"):
            lines.append(f"  - Task: {link['roadmap_task_title']}")
        if link.get("work_item_title"):
            lines.append(f"  - Work Item: {link['work_item_title']}")
    return "\n".join(lines).rstrip() + "\n"


def render_roadmap_markdown(payload: dict[str, Any]) -> str:
    areas = payload.get("areas", [])
    milestones = payload.get("milestones", [])
    tasks = payload.get("tasks", [])
    milestones_by_area: dict[str, list[dict[str, Any]]] = {}
    tasks_by_milestone: dict[str, list[dict[str, Any]]] = {}
    for milestone in milestones:
        milestones_by_area.setdefault(milestone.get("area_id") or "", []).append(milestone)
    for task in tasks:
        tasks_by_milestone.setdefault(task.get("milestone_id") or "", []).append(task)

    lines = [
        "# Roadmap DB Inspection",
        "",
        f"- Project ID: `{payload.get('project_id', '')}`",
        f"- Areas: `{payload.get('counts', {}).get('areas', 0)}`",
        f"- Milestones: `{payload.get('counts', {}).get('milestones', 0)}`",
        f"- Tasks: `{payload.get('counts', {}).get('tasks', 0)}`",
        "",
    ]
    for area in areas:
        lines.append(f"## Area: {area['name']} ({area['id']})")
        lines.append(f"- Status: `{area['status']}`")
        area_milestones = sorted(
            milestones_by_area.get(area["id"], []),
            key=lambda item: (item.get("sort_order", 0), item["id"]),
        )
        for milestone in area_milestones:
            lines.append(f"### Milestone: {milestone['name']} ({milestone['id']})")
            lines.append(f"- Status: `{milestone['status']}`")
            milestone_tasks = sorted(
                tasks_by_milestone.get(milestone["id"], []),
                key=lambda item: (item.get("sort_order", 0), item["id"]),
            )
            for task in milestone_tasks:
                lines.append(f"- Task: {task['title']} ({task['id']}) [{task['status']}]")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_roadmap_events_markdown(payload: dict[str, Any]) -> str:
    events = payload.get("events", [])
    lines = [
        "# Roadmap Events",
        "",
        f"- Project ID: `{payload.get('project_id', '')}`",
        f"- Event count: `{payload.get('event_count', len(events))}`",
        "",
    ]
    for event in events:
        target_bits = [
            f"area={event['area_id']}" if event.get("area_id") else None,
            f"milestone={event['milestone_id']}" if event.get("milestone_id") else None,
            f"task={event['task_id']}" if event.get("task_id") else None,
        ]
        target_text = ", ".join(item for item in target_bits if item) or "project"
        lines.append(
            f"- `{event['created_at']}` `{event['event_type']}` by `{event['actor']}` ({target_text})"
        )
        if event.get("summary"):
            lines.append(f"  - {event['summary']}")
    return "\n".join(lines).rstrip() + "\n"
