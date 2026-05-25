from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.local_active_project import set_active_project
from aresforge.operator.local_project_queue import add_queue_item, init_project_queue, resolve_project_queue_path
from aresforge.operator.managed_project_registry_local import (
    init_managed_project_registry,
    register_managed_project,
    register_managed_repo,
    resolve_managed_project_registry_path,
)

PROJECT_TYPES: tuple[str, ...] = (
    "app",
    "automation",
    "website",
    "agent-system",
    "internal-tool",
    "documentation",
    "other",
)
GITHUB_MODES: tuple[str, ...] = (
    "create-later",
    "link-existing",
    "create-with-approval-later",
)

_BOUNDARY_CONFIRMATIONS: tuple[str, ...] = (
    "Local-only project factory operation.",
    "No GitHub API calls.",
    "No gh calls.",
    "No GraphQL/REST calls.",
    "No network service calls.",
    "No agent execution.",
    "No model invocation.",
)


def resolve_project_factory_dossier_path(repo_root: Path, project_id: str) -> Path:
    return (repo_root / ".aresforge" / "projects" / project_id.strip() / "factory_dossier.json").resolve()


def resolve_project_scope_package_path(repo_root: Path, project_id: str) -> Path:
    return (repo_root / ".aresforge" / "projects" / project_id.strip() / "scope_package.json").resolve()


def create_project_factory_dossier(config: AppConfig, payload: dict[str, Any]) -> dict[str, Any]:
    dossier_path = resolve_project_factory_dossier_path(config.repo_root, str(payload.get("project_id", "")).strip())
    dossier_path.parent.mkdir(parents=True, exist_ok=True)
    dossier_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return {
        "ok": True,
        "local_only": True,
        "dossier_path": str(dossier_path),
        "dossier": payload,
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }


def read_project_factory_dossier(config: AppConfig, project_id: str) -> dict[str, Any]:
    normalized_project_id = str(project_id or "").strip()
    dossier_path = resolve_project_factory_dossier_path(config.repo_root, normalized_project_id)
    warnings: list[str] = []
    dossier: dict[str, Any] | None = None
    dossier_exists = dossier_path.exists()

    if dossier_exists:
        try:
            loaded = json.loads(dossier_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            warnings.append(f"Factory dossier could not be parsed: {exc}")
        else:
            if isinstance(loaded, dict):
                dossier = loaded
            else:
                warnings.append("Factory dossier has invalid schema; expected JSON object.")
    else:
        warnings.append(f"Factory dossier not found for project: {normalized_project_id}")

    lifecycle_state = str((dossier or {}).get("lifecycle_state", "")).strip() or "not_started"
    next_recommended_action = str((dossier or {}).get("next_recommended_action", "")).strip()
    if not next_recommended_action:
        if dossier_exists:
            next_recommended_action = "scope_project"
        else:
            next_recommended_action = "create_project_via_new_project_wizard"

    safety_boundary = (dossier or {}).get("safety_boundary")
    if not isinstance(safety_boundary, dict):
        safety_boundary = {
            "local_only": True,
            "github_mutation_status": "not_requested",
            "model_execution_status": "not_requested",
        }

    return {
        "ok": True,
        "local_only": True,
        "project_id": normalized_project_id,
        "dossier_path": str(dossier_path),
        "dossier_exists": dossier_exists and isinstance(dossier, dict),
        "dossier": dossier if isinstance(dossier, dict) else {},
        "lifecycle_state": lifecycle_state,
        "next_recommended_action": next_recommended_action,
        "safety_boundary": safety_boundary,
        "warnings": sorted(set(warnings)),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }


def inspect_project_factory_dossier(config: AppConfig, project_id: str) -> dict[str, Any]:
    payload = read_project_factory_dossier(config, project_id)
    lifecycle_state = str(payload.get("lifecycle_state", "")).strip()
    dossier = payload.get("dossier", {}) if isinstance(payload.get("dossier"), dict) else {}
    github_mode = str(dossier.get("github_mode", "")).strip() or "create-later"
    payload["workflow_steps"] = _build_workflow_steps(lifecycle_state=lifecycle_state, github_mode=github_mode)
    return payload


def prepare_project_scope_package(config: AppConfig, project_id: str) -> dict[str, Any]:
    inspection = inspect_project_factory_dossier(config, project_id)
    normalized_project_id = str(inspection.get("project_id", "")).strip()
    if not inspection.get("dossier_exists", False):
        return _error(
            "project_factory_dossier_not_found",
            {
                "message": "Project factory dossier is required before preparing a scope package.",
                "project_id": normalized_project_id,
                "dossier_path": inspection.get("dossier_path", ""),
            },
        )

    dossier = inspection.get("dossier", {}) if isinstance(inspection.get("dossier"), dict) else {}
    now = _now_iso()
    scope_path = resolve_project_scope_package_path(config.repo_root, normalized_project_id)
    scope_path.parent.mkdir(parents=True, exist_ok=True)
    existing_created_at = ""
    if scope_path.exists():
        try:
            existing_raw = json.loads(scope_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            existing_raw = {}
        if isinstance(existing_raw, dict):
            existing_created_at = str(existing_raw.get("created_at", "")).strip()

    scope_package = {
        "schema_version": "1.0",
        "project_id": normalized_project_id,
        "created_at": existing_created_at or now,
        "updated_at": now,
        "lifecycle_state": "scope_package_prepared",
        "source": "local_project_factory",
        "input": {
            "name": str(dossier.get("name", "")).strip(),
            "description": str(dossier.get("description", "")).strip(),
            "project_type": str(dossier.get("project_type", "")).strip(),
            "preferred_stack": str(dossier.get("preferred_stack", "")).strip(),
            "initial_requirements": str(dossier.get("initial_requirements", "")).strip(),
        },
        "scope_status": "not_started",
        "model_execution_status": "not_requested",
        "github_mutation_status": "not_requested",
        "next_recommended_action": "approve_scope_generation_or_edit_scope_locally",
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }
    scope_path.write_text(json.dumps(scope_package, indent=2) + "\n", encoding="utf-8")

    current_lifecycle_state = str(dossier.get("lifecycle_state", "")).strip()
    if current_lifecycle_state in {"", "intake_created", "scope_project"}:
        dossier["lifecycle_state"] = "scope_package_prepared"
    dossier["next_recommended_action"] = "approve_scope_generation_or_edit_scope_locally"
    dossier["updated_at"] = now
    dossier.setdefault(
        "safety_boundary",
        {
            "local_only": True,
            "github_mutation_status": "not_requested",
            "model_execution_status": "not_requested",
        },
    )
    create_project_factory_dossier(config, dossier)
    updated_inspection = inspect_project_factory_dossier(config, normalized_project_id)

    return {
        "ok": True,
        "local_only": True,
        "project_id": normalized_project_id,
        "dossier": updated_inspection.get("dossier", {}),
        "dossier_path": updated_inspection.get("dossier_path", ""),
        "scope_package": scope_package,
        "scope_package_path": str(scope_path),
        "warnings": sorted(set(updated_inspection.get("warnings", []))),
        "boundary_confirmations": list(
            dict.fromkeys(
                list(_BOUNDARY_CONFIRMATIONS) + list(updated_inspection.get("boundary_confirmations", []))
            )
        ),
    }


def start_new_project_factory(config: AppConfig, payload: dict[str, Any]) -> dict[str, Any]:
    name = str(payload.get("name", "")).strip()
    if not name:
        return _error(
            "invalid_project_factory_payload",
            {
                "message": "project name is required.",
                "required_fields": ["name"],
            },
        )

    project_id = str(payload.get("project_id", "")).strip() or _slugify(name)
    project_type = str(payload.get("project_type", "other")).strip() or "other"
    if project_type not in PROJECT_TYPES:
        return _error(
            "invalid_project_type",
            {
                "project_type": project_type,
                "supported_project_types": list(PROJECT_TYPES),
            },
        )

    github_mode = str(payload.get("github_mode", "create-later")).strip() or "create-later"
    if github_mode not in GITHUB_MODES:
        return _error(
            "invalid_github_mode",
            {
                "github_mode": github_mode,
                "supported_github_modes": list(GITHUB_MODES),
            },
        )

    root_path = str(payload.get("root_path", "")).strip()
    if not root_path:
        return _error(
            "invalid_project_factory_payload",
            {
                "message": "root_path is required.",
                "required_fields": ["name", "root_path"],
            },
        )

    default_branch = str(payload.get("default_branch", "main")).strip() or "main"
    github_owner = str(payload.get("github_owner", "")).strip()
    github_repo = str(payload.get("github_repo", "")).strip()
    description = str(payload.get("description", "")).strip()
    preferred_stack = str(payload.get("preferred_stack", "")).strip()
    initial_requirements = str(payload.get("initial_requirements", "")).strip()
    tags = _normalize_tags(payload.get("tags"))

    warnings: list[str] = []
    if not resolve_managed_project_registry_path(config.repo_root, None).exists():
        init_result = init_managed_project_registry(config)
        if not init_result.get("ok", False):
            return init_result
        warnings.append("Managed project registry was initialized automatically.")
    if not resolve_project_queue_path(config.repo_root, None).exists():
        init_queue_result = init_project_queue(config)
        if not init_queue_result.get("ok", False):
            return init_queue_result
        warnings.append("Local project queue was initialized automatically.")

    repo_id = f"{project_id}-primary"
    remote_url = f"https://github.com/{github_owner}/{github_repo}" if github_owner and github_repo else None

    project_result = register_managed_project(
        config,
        project_id=project_id,
        name=name,
        root_path=root_path,
        description=description,
        status="active",
        default_branch=default_branch,
        tags=tags,
        primary_repo_id=repo_id,
        github_owner=github_owner or None,
        github_repo=github_repo or None,
        github_default_branch=default_branch,
        notes=f"project_factory_type={project_type}; github_mode={github_mode}",
    )
    if not project_result.get("ok", False):
        return project_result

    repo_result = register_managed_repo(
        config,
        project_id=project_id,
        repo_id=repo_id,
        name=github_repo or f"{name} Primary Repo",
        path=root_path,
        remote_url=remote_url,
        default_branch=default_branch,
        role="primary",
        status="planned",
        tags=_normalize_tags(tags + ["project-factory", "new-project-wizard"]),
        github_owner=github_owner or None,
        github_repo=github_repo or None,
        github_default_branch=default_branch,
        notes=f"github_mode={github_mode}",
    )
    if not repo_result.get("ok", False):
        return repo_result

    active_result = set_active_project(config, project_id=project_id)
    if not active_result.get("ok", False):
        return active_result

    scope_item_id = f"{project_id}-scope-project"
    scope_queue_result = add_queue_item(
        config,
        item_id=scope_item_id,
        project_id=project_id,
        repo_id=repo_id,
        title=f"Scope project: {name}",
        description=initial_requirements or description or "Initial project scoping task from New Project Wizard.",
        status="proposed",
        priority="high",
        item_type="task",
        source="hub-new-project-wizard",
        tags=_normalize_tags(tags + ["project-factory", "scope-project", "new-project-wizard"]),
    )
    if not scope_queue_result.get("ok", False):
        return scope_queue_result

    now = _now_iso()
    dossier = {
        "schema_version": "1.0",
        "project_id": project_id,
        "name": name,
        "description": description,
        "project_type": project_type,
        "preferred_stack": preferred_stack,
        "root_path": root_path,
        "github_owner": github_owner,
        "github_repo": github_repo,
        "github_mode": github_mode,
        "default_branch": default_branch,
        "initial_requirements": initial_requirements,
        "tags": tags,
        "created_at": now,
        "updated_at": now,
        "lifecycle_state": "intake_created",
        "next_recommended_action": "scope_project",
        "safety_boundary": {
            "local_only": True,
            "github_mutation_status": "not_requested",
            "model_execution_status": "not_requested",
        },
    }
    dossier_result = create_project_factory_dossier(config, dossier)
    if not dossier_result.get("ok", False):
        return dossier_result

    warnings.extend(list(project_result.get("warnings", [])))
    warnings.extend(list(repo_result.get("warnings", [])))
    warnings.extend(list(scope_queue_result.get("warnings", [])))

    boundary_confirmations = list(
        dict.fromkeys(
            list(_BOUNDARY_CONFIRMATIONS)
            + list(project_result.get("boundary_confirmations", []))
            + list(repo_result.get("boundary_confirmations", []))
            + list(active_result.get("boundary_confirmations", []))
        )
    )

    return {
        "ok": True,
        "local_only": True,
        "project": project_result.get("project", {}),
        "repo": repo_result.get("repo", {}),
        "active_project_id": project_id,
        "scope_queue_item": scope_queue_result.get("item", {}),
        "dossier_path": dossier_result.get("dossier_path", ""),
        "dossier": dossier,
        "warnings": sorted(set(warnings)),
        "boundary_confirmations": boundary_confirmations,
    }


def _slugify(value: str) -> str:
    rendered = re.sub(r"[^a-z0-9]+", "-", str(value or "").strip().lower()).strip("-")
    if not rendered:
        return "project"
    return rendered[:48]


def _normalize_tags(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    tags: list[str] = []
    for item in values:
        normalized = str(item).strip()
        if normalized and normalized not in tags:
            tags.append(normalized)
    return tags


def _error(error: str, details: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": False,
        "local_only": True,
        "error": error,
        "details": details,
    }


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _build_workflow_steps(*, lifecycle_state: str, github_mode: str) -> list[dict[str, Any]]:
    normalized_state = lifecycle_state.strip() or "not_started"
    normalized_github_mode = github_mode.strip() or "create-later"
    repo_step_status = "current" if normalized_state == "intake_created" and normalized_github_mode == "link-existing" else "pending"
    scope_step_status = "current" if normalized_state == "intake_created" else "pending"
    if normalized_state == "scope_package_prepared":
        repo_step_status = "completed" if normalized_github_mode == "link-existing" else "pending"
        scope_step_status = "completed"

    return [
        {
            "step_id": "project_intake",
            "label": "Project Intake",
            "status": "completed" if normalized_state != "not_started" else "pending",
            "local_only": True,
            "gate_type": "none",
            "description": "Local project intake captured in factory dossier.",
        },
        {
            "step_id": "repo_create_or_link",
            "label": "Repo Create or Link",
            "status": repo_step_status,
            "local_only": True,
            "gate_type": "user_approval",
            "description": "Prepare repository create/link intent locally before any GitHub mutation.",
        },
        {
            "step_id": "scope_project",
            "label": "Scope Project",
            "status": scope_step_status,
            "local_only": True,
            "gate_type": "model_execution_approval",
            "description": "Prepare local scope package and approve model scope generation later.",
        },
        {
            "step_id": "architecture_design",
            "label": "Architecture Design",
            "status": "pending",
            "local_only": True,
            "gate_type": "model_execution_approval",
            "description": "Architecture and design planning phase.",
        },
        {
            "step_id": "milestone_issue_plan",
            "label": "Milestone and Issue Plan",
            "status": "pending",
            "local_only": True,
            "gate_type": "user_approval",
            "description": "Define milestones and issue plan locally before apply.",
        },
        {
            "step_id": "github_apply",
            "label": "GitHub Apply",
            "status": "gated",
            "local_only": True,
            "gate_type": "github_approval",
            "description": "GitHub mutations remain gated until explicit approval.",
        },
        {
            "step_id": "agent_dispatch",
            "label": "Agent Dispatch",
            "status": "gated",
            "local_only": True,
            "gate_type": "model_execution_approval",
            "description": "Agent execution remains gated until explicit approval.",
        },
        {
            "step_id": "validation",
            "label": "Validation",
            "status": "pending",
            "local_only": True,
            "gate_type": "none",
            "description": "Run local validation for delivered work.",
        },
        {
            "step_id": "documentation",
            "label": "Documentation",
            "status": "pending",
            "local_only": True,
            "gate_type": "none",
            "description": "Capture docs and evidence updates.",
        },
        {
            "step_id": "closeout",
            "label": "Closeout",
            "status": "pending",
            "local_only": True,
            "gate_type": "none",
            "description": "Finalize project closeout workflow.",
        },
    ]
