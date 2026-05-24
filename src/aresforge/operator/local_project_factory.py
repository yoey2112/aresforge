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
