from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.local_project_dashboard import summarize_docs_status, summarize_local_project_dashboard
from aresforge.operator.local_project_queue import (
    QUEUE_ITEM_TYPES,
    QUEUE_PRIORITIES,
    QUEUE_STATUSES,
    add_queue_item,
    init_project_queue,
    resolve_project_queue_path,
    update_queue_item,
)
from aresforge.operator.managed_project_registry_local import (
    PROJECT_STATUSES,
    REPO_ROLES,
    REPO_STATUSES,
    init_managed_project_registry,
    register_managed_project,
    register_managed_repo,
    resolve_managed_project_registry_path,
)

SERVICE_NAME = "aresforge-hub"

_BOUNDARY_CONFIRMATIONS = [
    "Local-only hub endpoint.",
    "No GitHub calls.",
    "No gh calls.",
    "No network service calls.",
    "No local LLM calls.",
    "No cloud LLM calls.",
    "No Codex calls.",
    "No ChatGPT calls.",
    "No Ollama calls.",
    "No external API calls.",
]


def _api_error(
    error: str,
    message: str,
    *,
    details: dict[str, Any] | None = None,
    status: int = 400,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "ok": False,
        "local_only": True,
        "error": error,
        "message": message,
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
        "_status": status,
    }
    if details is not None:
        payload["details"] = details
    return payload


def _load_registry_if_present(config: AppConfig) -> tuple[list[dict[str, Any]], list[str], Path]:
    warnings: list[str] = []
    registry_path = resolve_managed_project_registry_path(config.repo_root, None)
    if not registry_path.exists():
        warnings.append("Managed project registry not found. Returning empty local project list.")
        return [], warnings, registry_path

    try:
        raw = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        warnings.append(f"Managed project registry could not be parsed: {exc}")
        return [], warnings, registry_path

    if not isinstance(raw, dict):
        warnings.append("Managed project registry has invalid schema. Returning empty local project list.")
        return [], warnings, registry_path

    projects = raw.get("projects", [])
    if not isinstance(projects, list):
        warnings.append("Managed project registry contains non-list projects field.")
        return [], warnings, registry_path

    normalized = [project for project in projects if isinstance(project, dict)]
    return normalized, warnings, registry_path


def _normalize_str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        normalized = str(item).strip()
        if normalized and normalized not in result:
            result.append(normalized)
    return result


def _project_view(project: dict[str, Any]) -> dict[str, Any]:
    repos = project.get("repos", []) if isinstance(project.get("repos"), list) else []
    normalized_repos = [_repo_view(repo) for repo in repos if isinstance(repo, dict)]
    return {
        "project_id": str(project.get("project_id", "")).strip(),
        "name": str(project.get("name", "")).strip(),
        "description": str(project.get("description", "")).strip(),
        "root_path": str(project.get("root_path", "")).strip(),
        "status": str(project.get("status", "")).strip(),
        "default_branch": str(project.get("default_branch", "")).strip(),
        "tags": _normalize_str_list(project.get("tags", [])),
        "notes": str(project.get("notes", "")).strip(),
        "created_at": str(project.get("created_at", "")).strip(),
        "updated_at": str(project.get("updated_at", "")).strip(),
        "repos": normalized_repos,
        "repo_count": len(normalized_repos),
    }


def _repo_view(repo: dict[str, Any]) -> dict[str, Any]:
    return {
        "repo_id": str(repo.get("repo_id", "")).strip(),
        "name": str(repo.get("name", "")).strip(),
        "path": str(repo.get("path", "")).strip(),
        "remote_url": str(repo.get("remote_url", "")).strip(),
        "default_branch": str(repo.get("default_branch", "")).strip(),
        "role": str(repo.get("role", "")).strip(),
        "status": str(repo.get("status", "")).strip(),
        "tags": _normalize_str_list(repo.get("tags", [])),
        "notes": str(repo.get("notes", "")).strip(),
        "created_at": str(repo.get("created_at", "")).strip(),
        "updated_at": str(repo.get("updated_at", "")).strip(),
    }


def _item_view(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "item_id": str(item.get("item_id", "")).strip(),
        "project_id": str(item.get("project_id", "")).strip(),
        "repo_id": str(item.get("repo_id", "")).strip(),
        "title": str(item.get("title", "")).strip(),
        "description": str(item.get("description", "")).strip(),
        "status": str(item.get("status", "")).strip(),
        "priority": str(item.get("priority", "")).strip(),
        "item_type": str(item.get("item_type", "")).strip(),
        "tags": _normalize_str_list(item.get("tags", [])),
        "dependencies": _normalize_str_list(item.get("dependencies", [])),
        "blocked_by": _normalize_str_list(item.get("blocked_by", [])),
        "assigned_agent": str(item.get("assigned_agent", "")).strip(),
        "source": str(item.get("source", "")).strip(),
        "notes": str(item.get("notes", "")).strip(),
        "created_at": str(item.get("created_at", "")).strip(),
        "updated_at": str(item.get("updated_at", "")).strip(),
    }


def _load_queue_if_present(config: AppConfig) -> tuple[list[dict[str, Any]], list[str], Path]:
    warnings: list[str] = []
    queue_path = resolve_project_queue_path(config.repo_root, None)
    if not queue_path.exists():
        warnings.append("Local project queue not found. Returning empty local queue list.")
        return [], warnings, queue_path

    try:
        raw = json.loads(queue_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        warnings.append(f"Local project queue could not be parsed: {exc}")
        return [], warnings, queue_path

    if not isinstance(raw, dict):
        warnings.append("Local project queue has invalid schema. Returning empty local queue list.")
        return [], warnings, queue_path

    items = raw.get("work_items", [])
    if not isinstance(items, list):
        warnings.append("Local project queue contains non-list work_items field.")
        return [], warnings, queue_path

    normalized = [_item_view(item) for item in items if isinstance(item, dict)]
    return normalized, warnings, queue_path


def _counts_by(items: list[dict[str, Any]], field: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        value = str(item.get(field, "")).strip() or "unknown"
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def get_health() -> dict[str, Any]:
    return {
        "ok": True,
        "service": SERVICE_NAME,
        "local_only": True,
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS) + ["Default bind host is 127.0.0.1."],
    }


def get_summary(config: AppConfig) -> dict[str, Any]:
    payload = summarize_local_project_dashboard(config)
    payload.update(
        {
            "ok": True,
            "service": SERVICE_NAME,
        }
    )
    return payload


def get_docs_status(config: AppConfig) -> dict[str, Any]:
    payload = summarize_docs_status(config.repo_root)
    payload.update(
        {
            "ok": True,
            "service": SERVICE_NAME,
            "boundary_confirmations": [
                "Local-only docs status inspection.",
                "No network calls.",
                "No GitHub calls.",
            ],
        }
    )
    return payload


def get_projects(config: AppConfig) -> dict[str, Any]:
    projects_raw, warnings, registry_path = _load_registry_if_present(config)
    projects = [_project_view(project) for project in projects_raw]
    return {
        "ok": True,
        "local_only": True,
        "registry_path": str(registry_path),
        "projects": projects,
        "project_count": len(projects),
        "warnings": sorted(set(warnings)),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }


def post_project(config: AppConfig, body: dict[str, Any]) -> dict[str, Any]:
    project_id = str(body.get("project_id", "")).strip()
    name = str(body.get("name", "")).strip()
    root_path = str(body.get("root_path", "")).strip()

    if not project_id or not name or not root_path:
        return _api_error(
            "invalid_project_payload",
            "project_id, name, and root_path are required.",
            details={"required_fields": ["project_id", "name", "root_path"]},
        )

    warnings: list[str] = []
    registry_path = resolve_managed_project_registry_path(config.repo_root, None)
    if not registry_path.exists():
        init_result = init_managed_project_registry(config)
        if not init_result.get("ok", False):
            return _api_error(
                str(init_result.get("error", "managed_project_registry_init_failed")),
                str(init_result.get("details", {}).get("message", "Failed to initialize managed project registry.")),
                details=dict(init_result.get("details", {})),
            )
        warnings.append("Managed project registry was initialized automatically.")

    result = register_managed_project(
        config,
        project_id=project_id,
        name=name,
        root_path=root_path,
        description=body.get("description"),
        status=body.get("status"),
        default_branch=body.get("default_branch"),
        tags=body.get("tags") if isinstance(body.get("tags"), list) else None,
        notes=body.get("notes"),
    )

    if not result.get("ok", False):
        details = dict(result.get("details", {}))
        return _api_error(
            str(result.get("error", "register_managed_project_failed")),
            str(details.get("message", "Failed to create or update project.")),
            details=details,
        )

    project = result.get("project", {}) if isinstance(result.get("project"), dict) else {}
    return {
        "ok": True,
        "local_only": True,
        "created": bool(result.get("created", False)),
        "project": project,
        "warnings": sorted(set(warnings)),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }


def get_project(config: AppConfig, project_id: str) -> dict[str, Any]:
    normalized_project_id = project_id.strip()
    projects_raw, warnings, registry_path = _load_registry_if_present(config)
    if not projects_raw:
        return _api_error(
            "managed_project_not_found",
            "Project id was not found in managed project registry.",
            status=404,
            details={
                "project_id": normalized_project_id,
                "registry_path": str(registry_path),
                "warnings": warnings,
            },
        )

    project = next(
        (
            candidate
            for candidate in projects_raw
            if str(candidate.get("project_id", "")).strip() == normalized_project_id
        ),
        None,
    )
    if project is None:
        return _api_error(
            "managed_project_not_found",
            "Project id was not found in managed project registry.",
            status=404,
            details={
                "project_id": normalized_project_id,
                "registry_path": str(registry_path),
            },
        )

    project_view = _project_view(project)
    return {
        "ok": True,
        "local_only": True,
        "project": {
            key: value for key, value in project_view.items() if key not in {"repos", "repo_count"}
        },
        "repos": list(project_view.get("repos", [])),
        "warnings": sorted(set(warnings)),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }


def get_project_repos(config: AppConfig, project_id: str) -> dict[str, Any]:
    project_payload = get_project(config, project_id)
    if not project_payload.get("ok", False):
        return project_payload
    repos = project_payload.get("repos", []) if isinstance(project_payload.get("repos"), list) else []
    return {
        "ok": True,
        "local_only": True,
        "project_id": project_id.strip(),
        "repos": repos,
        "repo_count": len(repos),
        "warnings": list(project_payload.get("warnings", [])),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }


def post_project_repo(config: AppConfig, project_id: str, body: dict[str, Any]) -> dict[str, Any]:
    normalized_project_id = project_id.strip()
    body_project_id = str(body.get("project_id", "")).strip()
    if body_project_id and body_project_id != normalized_project_id:
        return _api_error(
            "project_id_mismatch",
            "Project id in URL and payload must match.",
            details={"path_project_id": normalized_project_id, "body_project_id": body_project_id},
        )

    repo_id = str(body.get("repo_id", "")).strip()
    name = str(body.get("name", "")).strip()
    path = str(body.get("path", "")).strip()
    if not repo_id or not name or not path:
        return _api_error(
            "invalid_repo_payload",
            "repo_id, name, and path are required.",
            details={"required_fields": ["repo_id", "name", "path"]},
        )

    result = register_managed_repo(
        config,
        project_id=normalized_project_id,
        repo_id=repo_id,
        name=name,
        path=path,
        remote_url=body.get("remote_url"),
        default_branch=body.get("default_branch"),
        role=body.get("role"),
        status=body.get("status"),
        tags=body.get("tags") if isinstance(body.get("tags"), list) else None,
        notes=body.get("notes"),
    )
    if not result.get("ok", False):
        details = dict(result.get("details", {}))
        error = str(result.get("error", "register_managed_repo_failed"))
        status = 404 if error == "managed_project_not_found" else 400
        return _api_error(
            error,
            str(details.get("message", "Failed to create or update managed repo.")),
            details=details,
            status=status,
        )

    repo = result.get("repo", {}) if isinstance(result.get("repo"), dict) else {}
    return {
        "ok": True,
        "local_only": True,
        "project_id": normalized_project_id,
        "created": bool(result.get("created", False)),
        "repo": repo,
        "warnings": [],
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }


def get_queue(config: AppConfig, filters: dict[str, str | None]) -> dict[str, Any]:
    items, warnings, queue_path = _load_queue_if_present(config)

    status_filter = filters.get("status")
    type_filter = filters.get("type")
    project_id_filter = filters.get("project_id")
    repo_id_filter = filters.get("repo_id")
    assigned_agent_filter = filters.get("assigned_agent")

    if status_filter and status_filter not in QUEUE_STATUSES:
        return _api_error(
            "invalid_queue_status",
            "Invalid queue status supplied.",
            details={"status": status_filter, "supported_statuses": list(QUEUE_STATUSES)},
        )
    if type_filter and type_filter not in QUEUE_ITEM_TYPES:
        return _api_error(
            "invalid_queue_item_type",
            "Invalid queue item type supplied.",
            details={"item_type": type_filter, "supported_item_types": list(QUEUE_ITEM_TYPES)},
        )

    filtered: list[dict[str, Any]] = []
    for item in items:
        if project_id_filter and item.get("project_id") != project_id_filter:
            continue
        if repo_id_filter and item.get("repo_id") != repo_id_filter:
            continue
        if status_filter and item.get("status") != status_filter:
            continue
        if type_filter and item.get("item_type") != type_filter:
            continue
        if assigned_agent_filter and item.get("assigned_agent") != assigned_agent_filter:
            continue
        filtered.append(item)

    return {
        "ok": True,
        "local_only": True,
        "queue_path": str(queue_path),
        "filters": {
            "project_id": project_id_filter,
            "repo_id": repo_id_filter,
            "status": status_filter,
            "type": type_filter,
            "assigned_agent": assigned_agent_filter,
        },
        "items": filtered,
        "counts_by_status": _counts_by(filtered, "status"),
        "counts_by_type": _counts_by(filtered, "item_type"),
        "counts_by_priority": _counts_by(filtered, "priority"),
        "warnings": sorted(set(warnings)),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }


def post_queue_item(config: AppConfig, body: dict[str, Any]) -> dict[str, Any]:
    required = {
        "item_id": str(body.get("item_id", "")).strip(),
        "project_id": str(body.get("project_id", "")).strip(),
        "repo_id": str(body.get("repo_id", "")).strip(),
        "title": str(body.get("title", "")).strip(),
    }
    missing_fields = [name for name, value in required.items() if not value]
    if missing_fields:
        return _api_error(
            "invalid_queue_payload",
            "item_id, project_id, repo_id, and title are required.",
            details={"missing_fields": missing_fields},
        )

    warnings: list[str] = []
    queue_path = resolve_project_queue_path(config.repo_root, None)
    if not queue_path.exists():
        init_result = init_project_queue(config)
        if not init_result.get("ok", False):
            return _api_error(
                str(init_result.get("error", "project_queue_init_failed")),
                str(init_result.get("details", {}).get("message", "Failed to initialize local project queue.")),
                details=dict(init_result.get("details", {})),
            )
        warnings.append("Local project queue was initialized automatically.")

    result = add_queue_item(
        config,
        item_id=required["item_id"],
        project_id=required["project_id"],
        repo_id=required["repo_id"],
        title=required["title"],
        description=body.get("description"),
        status=body.get("status"),
        priority=body.get("priority"),
        item_type=body.get("item_type"),
        tags=body.get("tags") if isinstance(body.get("tags"), list) else None,
        dependencies=body.get("dependencies") if isinstance(body.get("dependencies"), list) else None,
        blocked_by=body.get("blocked_by") if isinstance(body.get("blocked_by"), list) else None,
        assigned_agent=body.get("assigned_agent"),
        source=body.get("source"),
        notes=body.get("notes"),
    )
    if not result.get("ok", False):
        details = dict(result.get("details", {}))
        error = str(result.get("error", "add_queue_item_failed"))
        status = 404 if error in {"managed_project_not_found", "managed_repo_not_found"} else 400
        return _api_error(
            error,
            str(details.get("message", "Failed to create or update queue item.")),
            details=details,
            status=status,
        )

    item = result.get("item", {}) if isinstance(result.get("item"), dict) else {}
    warnings.extend(list(result.get("warnings", [])))
    return {
        "ok": True,
        "local_only": True,
        "created": bool(result.get("created", False)),
        "item": item,
        "warnings": sorted(set(warnings)),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }


def get_queue_item(config: AppConfig, item_id: str) -> dict[str, Any]:
    normalized_item_id = item_id.strip()
    items, warnings, queue_path = _load_queue_if_present(config)
    item = next((candidate for candidate in items if candidate.get("item_id") == normalized_item_id), None)
    if item is None:
        return _api_error(
            "queue_item_not_found",
            "Queue item id was not found in local project queue.",
            status=404,
            details={"item_id": normalized_item_id, "queue_path": str(queue_path), "warnings": warnings},
        )
    return {
        "ok": True,
        "local_only": True,
        "item": item,
        "warnings": sorted(set(warnings)),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }


def patch_queue_item(config: AppConfig, item_id: str, body: dict[str, Any]) -> dict[str, Any]:
    allowed_fields = {
        "title",
        "description",
        "status",
        "priority",
        "item_type",
        "tags",
        "dependencies",
        "blocked_by",
        "assigned_agent",
        "source",
        "notes",
    }
    provided_fields = [name for name in body.keys() if name in allowed_fields]
    unsupported_fields = [name for name in body.keys() if name not in allowed_fields]

    if not provided_fields:
        return _api_error(
            "invalid_queue_patch_payload",
            "At least one supported field is required for queue update.",
            details={"supported_fields": sorted(allowed_fields)},
        )
    if unsupported_fields:
        return _api_error(
            "unsupported_queue_patch_fields",
            "Queue patch payload contains unsupported fields.",
            details={"unsupported_fields": sorted(unsupported_fields), "supported_fields": sorted(allowed_fields)},
        )

    result = update_queue_item(
        config,
        item_id=item_id.strip(),
        title=body.get("title"),
        description=body.get("description"),
        status=body.get("status"),
        priority=body.get("priority"),
        item_type=body.get("item_type"),
        tags=body.get("tags") if isinstance(body.get("tags"), list) else None,
        dependencies=body.get("dependencies") if isinstance(body.get("dependencies"), list) else None,
        blocked_by=body.get("blocked_by") if isinstance(body.get("blocked_by"), list) else None,
        assigned_agent=body.get("assigned_agent"),
        source=body.get("source"),
        notes=body.get("notes"),
    )

    if not result.get("ok", False):
        details = dict(result.get("details", {}))
        error = str(result.get("error", "update_queue_item_failed"))
        status = 404 if error == "queue_item_not_found" else 400
        return _api_error(
            error,
            str(details.get("message", "Failed to update queue item.")),
            details=details,
            status=status,
        )

    item = result.get("item", {}) if isinstance(result.get("item"), dict) else {}
    return {
        "ok": True,
        "local_only": True,
        "updated_fields": list(result.get("updated_fields", [])),
        "item": item,
        "warnings": sorted(set(result.get("warnings", []))),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }


def get_settings(config: AppConfig) -> dict[str, Any]:
    return {
        "ok": True,
        "local_only": True,
        "registry_path": str(resolve_managed_project_registry_path(config.repo_root, None)),
        "queue_path": str(resolve_project_queue_path(config.repo_root, None)),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }
