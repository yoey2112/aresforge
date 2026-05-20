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
DEFAULT_QUEUES = {
    "queue-intake": ("intake", "New work waiting for classification."),
    "queue-planning": ("planning", "Work being prepared for implementation."),
    "queue-implementation": ("implementation", "Active implementation work."),
    "queue-verification": ("verification", "Validation and review work."),
    "queue-documentation": ("documentation", "Documentation and evidence closeout."),
}
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
                        "active_issue": 83,
                        "completed_issue": 81,
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
                DEFAULT_MODEL_ID,
                config.ollama_model,
                "ollama",
                "configured",
                config.ollama_base_url,
                json.dumps({"default": True}),
            ),
        )
        for queue_id, (name, purpose) in DEFAULT_QUEUES.items():
            cur.execute(
                """
                INSERT INTO queues (id, name, status, purpose, metadata)
                VALUES (%s, %s, %s, %s, %s::jsonb)
                ON CONFLICT (id) DO UPDATE
                SET status = EXCLUDED.status,
                    purpose = EXCLUDED.purpose,
                    updated_at = NOW()
                """,
                (queue_id, name, "active", purpose, "{}"),
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
