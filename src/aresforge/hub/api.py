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
    resolve_agent_profiles_path,
)
from aresforge.operator.local_handoff_package import generate_handoff_package
from aresforge.operator.local_agent_orchestration import generate_agent_orchestration_plan
from aresforge.operator.local_llm_escalation import generate_llm_escalation_plan
from aresforge.operator.managed_project_registry_local import (
    PROJECT_STATUSES,
    REPO_ROLES,
    REPO_STATUSES,
    init_managed_project_registry,
    register_managed_project,
    register_managed_repo,
    resolve_managed_project_registry_path,
)
from aresforge.operator.local_agent_orchestration import DEFAULT_OUTPUT_DIR as ORCHESTRATION_OUTPUT_DIR
from aresforge.operator.local_llm_escalation import DEFAULT_OUTPUT_DIR as ESCALATION_OUTPUT_DIR

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

_PLAN_ONLY_CONFIRMATIONS = [
    "Plan-only response.",
    "No agent execution.",
    "No model invocation.",
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


def _load_profiles_if_present(config: AppConfig) -> tuple[dict[str, Any], list[str], Path]:
    warnings: list[str] = []
    profiles_path = resolve_agent_profiles_path(config.repo_root, None)
    if not profiles_path.exists():
        warnings.append("Local agent profiles not found. Returning empty profile and handoff target lists.")
        return {"agents": [], "handoff_targets": []}, warnings, profiles_path

    try:
        raw = json.loads(profiles_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        warnings.append(f"Local agent profiles could not be parsed: {exc}")
        return {"agents": [], "handoff_targets": []}, warnings, profiles_path

    if not isinstance(raw, dict):
        warnings.append("Local agent profiles have invalid schema. Returning empty profile and handoff target lists.")
        return {"agents": [], "handoff_targets": []}, warnings, profiles_path

    agents = raw.get("agents", [])
    targets = raw.get("handoff_targets", [])
    if not isinstance(agents, list):
        warnings.append("Local agent profiles contain non-list agents field.")
        agents = []
    if not isinstance(targets, list):
        warnings.append("Local agent profiles contain non-list handoff_targets field.")
        targets = []

    normalized_agents: list[dict[str, Any]] = []
    for agent in agents:
        if not isinstance(agent, dict):
            continue
        normalized_agents.append(
            {
                "agent_id": str(agent.get("agent_id", "")).strip(),
                "name": str(agent.get("name", "")).strip(),
                "role": str(agent.get("role", "")).strip(),
                "description": str(agent.get("description", "")).strip(),
                "execution_mode": str(agent.get("execution_mode", "")).strip(),
                "model_preference": str(agent.get("model_preference", "")).strip(),
                "strengths": _normalize_str_list(agent.get("strengths", [])),
                "constraints": _normalize_str_list(agent.get("constraints", [])),
                "allowed_item_types": _normalize_str_list(agent.get("allowed_item_types", [])),
                "escalation_allowed": bool(agent.get("escalation_allowed", False)),
                "handoff_target_id": str(agent.get("handoff_target_id", "")).strip(),
                "status": str(agent.get("status", "")).strip(),
                "tags": _normalize_str_list(agent.get("tags", [])),
                "notes": str(agent.get("notes", "")).strip(),
                "created_at": str(agent.get("created_at", "")).strip(),
                "updated_at": str(agent.get("updated_at", "")).strip(),
            }
        )

    normalized_targets: list[dict[str, Any]] = []
    for target in targets:
        if not isinstance(target, dict):
            continue
        normalized_targets.append(
            {
                "target_id": str(target.get("target_id", "")).strip(),
                "name": str(target.get("name", "")).strip(),
                "target_type": str(target.get("target_type", "")).strip(),
                "description": str(target.get("description", "")).strip(),
                "local_command": str(target.get("local_command", "")).strip(),
                "input_format": str(target.get("input_format", "")).strip(),
                "output_format": str(target.get("output_format", "")).strip(),
                "safety_notes": _normalize_str_list(target.get("safety_notes", [])),
                "status": str(target.get("status", "")).strip(),
                "tags": _normalize_str_list(target.get("tags", [])),
                "notes": str(target.get("notes", "")).strip(),
                "created_at": str(target.get("created_at", "")).strip(),
                "updated_at": str(target.get("updated_at", "")).strip(),
            }
        )

    return {
        "agents": normalized_agents,
        "handoff_targets": normalized_targets,
    }, warnings, profiles_path


def _counts_by(items: list[dict[str, Any]], field: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        value = str(item.get(field, "")).strip() or "unknown"
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def _normalize_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_optional_list(value: Any) -> list[str] | None:
    if value is None:
        return None
    if not isinstance(value, list):
        return None
    normalized = _normalize_str_list(value)
    return normalized


def _extract_operator_payload(result: dict[str, Any]) -> dict[str, Any]:
    payload = result.get("payload")
    if isinstance(payload, dict):
        return payload

    stdout = result.get("stdout")
    if isinstance(stdout, str):
        try:
            decoded = json.loads(stdout)
        except json.JSONDecodeError:
            return {}
        if isinstance(decoded, dict):
            return decoded
    return {}


def _invalid_choice_error(
    *,
    field: str,
    value: Any,
    supported: tuple[str, ...] | list[str],
    label: str,
) -> dict[str, Any]:
    return _api_error(
        f"invalid_{field}",
        f"Invalid {label} supplied.",
        details={
            field: value,
            f"supported_{field}s": list(supported),
        },
    )


def _require_boolean_field(body: dict[str, Any], field: str) -> tuple[bool, dict[str, Any] | None]:
    if field not in body:
        return True, None
    if isinstance(body.get(field), bool):
        return True, None
    return False, _api_error(
        f"invalid_{field}",
        f"{field} must be a boolean value.",
        details={field: body.get(field)},
    )


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


def _report_payload(config: AppConfig) -> dict[str, Any]:
    return summarize_local_project_dashboard(config)


def get_reports_dashboard(config: AppConfig) -> dict[str, Any]:
    payload = _report_payload(config)
    payload.update(
        {
            "ok": True,
            "service": SERVICE_NAME,
        }
    )
    return payload


def get_reports_action_center(config: AppConfig) -> dict[str, Any]:
    report = _report_payload(config)
    return {
        "ok": True,
        "service": SERVICE_NAME,
        "local_only": True,
        "report_only": True,
        "generated_at": report.get("generated_at"),
        "action_center": report.get("action_center", {}),
        "warnings": report.get("warnings", []),
        "risks": report.get("risks", []),
        "recommended_next_actions": report.get("recommended_next_actions", []),
        "boundary_confirmations": report.get("boundary_confirmations", list(_BOUNDARY_CONFIRMATIONS)),
    }


def get_reports_readiness(config: AppConfig) -> dict[str, Any]:
    report = _report_payload(config)
    return {
        "ok": True,
        "service": SERVICE_NAME,
        "local_only": True,
        "report_only": True,
        "generated_at": report.get("generated_at"),
        "readiness_indicators": report.get("readiness_indicators", {}),
        "warnings": report.get("warnings", []),
        "boundary_confirmations": report.get("boundary_confirmations", list(_BOUNDARY_CONFIRMATIONS)),
    }


def get_reports_operator_workflows(config: AppConfig) -> dict[str, Any]:
    report = _report_payload(config)
    return {
        "ok": True,
        "service": SERVICE_NAME,
        "local_only": True,
        "report_only": True,
        "generated_at": report.get("generated_at"),
        "operator_workflows": report.get("operator_workflows", []),
        "warnings": report.get("warnings", []),
        "boundary_confirmations": report.get("boundary_confirmations", list(_BOUNDARY_CONFIRMATIONS)),
    }


def get_reports_export(config: AppConfig, params: dict[str, str | None]) -> dict[str, Any]:
    report = _report_payload(config)
    format_name = str(params.get("format") or "json").strip().lower()
    if format_name not in {"json", "markdown"}:
        return _api_error(
            "invalid_export_format",
            "format must be json or markdown.",
            details={"format": format_name, "supported_formats": ["json", "markdown"]},
        )

    if format_name == "markdown":
        lines = [
            "# AresForge Hub Dashboard Report",
            "",
            f"- generated_at: {report.get('generated_at')}",
            f"- overall_status: {report.get('readiness_indicators', {}).get('overall_status', 'unknown')}",
            "",
            "## Recommended Next Actions",
        ]
        actions = report.get("recommended_next_actions", [])
        if isinstance(actions, list) and actions:
            lines.extend(f"- {action}" for action in actions)
        else:
            lines.append("- None")
        lines.extend(["", "## Boundary Confirmations"])
        boundaries = report.get("boundary_confirmations", [])
        if isinstance(boundaries, list) and boundaries:
            lines.extend(f"- {item}" for item in boundaries)
        else:
            lines.append("- Local-only")
        export_content = "\n".join(lines)
    else:
        export_content = json.dumps(report, indent=2, sort_keys=True)

    return {
        "ok": True,
        "service": SERVICE_NAME,
        "local_only": True,
        "report_only": True,
        "format": format_name,
        "generated_at": report.get("generated_at"),
        "report": report,
        "content": export_content,
        "warnings": report.get("warnings", []),
        "boundary_confirmations": report.get("boundary_confirmations", list(_BOUNDARY_CONFIRMATIONS)),
        "write_supported": False,
        "write_performed": False,
    }


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


def get_agents(config: AppConfig) -> dict[str, Any]:
    snapshot, warnings, profiles_path = _load_profiles_if_present(config)
    agents = snapshot.get("agents", []) if isinstance(snapshot.get("agents"), list) else []
    return {
        "ok": True,
        "local_only": True,
        "profiles_path": str(profiles_path),
        "agents": agents,
        "agent_count": len(agents),
        "counts_by_role": _counts_by(agents, "role"),
        "counts_by_execution_mode": _counts_by(agents, "execution_mode"),
        "counts_by_status": _counts_by(agents, "status"),
        "warnings": sorted(set(warnings)),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }


def post_agent(config: AppConfig, body: dict[str, Any]) -> dict[str, Any]:
    agent_id = str(body.get("agent_id", "")).strip()
    name = str(body.get("name", "")).strip()
    role = str(body.get("role", "")).strip()
    if not agent_id or not name or not role:
        return _api_error(
            "invalid_agent_payload",
            "agent_id, name, and role are required.",
            details={"required_fields": ["agent_id", "name", "role"]},
        )
    if role not in AGENT_ROLES:
        return _invalid_choice_error(field="role", value=role, supported=AGENT_ROLES, label="role")

    execution_mode = _normalize_optional_str(body.get("execution_mode"))
    if execution_mode is not None and execution_mode not in EXECUTION_MODES:
        return _invalid_choice_error(
            field="execution_mode",
            value=execution_mode,
            supported=EXECUTION_MODES,
            label="execution mode",
        )

    status = _normalize_optional_str(body.get("status"))
    if status is not None and status not in AGENT_PROFILE_STATUSES:
        return _invalid_choice_error(
            field="status",
            value=status,
            supported=AGENT_PROFILE_STATUSES,
            label="status",
        )

    valid_bool, bool_error = _require_boolean_field(body, "escalation_allowed")
    if not valid_bool:
        return bool_error or _api_error("invalid_escalation_allowed", "escalation_allowed must be boolean.")

    warnings: list[str] = []
    profiles_path = resolve_agent_profiles_path(config.repo_root, None)
    if not profiles_path.exists():
        init_result = init_agent_profiles(config)
        if not init_result.get("ok", False):
            return _api_error(
                str(init_result.get("error", "agent_profiles_init_failed")),
                "Failed to initialize agent profiles storage.",
                details=dict(init_result.get("details", {})),
            )
        warnings.append("Local agent profiles were initialized automatically.")

    result = register_agent_profile(
        config,
        agent_id=agent_id,
        name=name,
        role=role,
        description=_normalize_optional_str(body.get("description")),
        execution_mode=execution_mode,
        model_preference=_normalize_optional_str(body.get("model_preference")),
        strengths=_normalize_optional_list(body.get("strengths")),
        constraints=_normalize_optional_list(body.get("constraints")),
        allowed_item_types=_normalize_optional_list(body.get("allowed_item_types")),
        escalation_allowed=body.get("escalation_allowed") if "escalation_allowed" in body else None,
        handoff_target_id=_normalize_optional_str(body.get("handoff_target_id")),
        status=status,
        tags=_normalize_optional_list(body.get("tags")),
        notes=_normalize_optional_str(body.get("notes")),
    )
    if not result.get("ok", False):
        details = dict(result.get("details", {}))
        return _api_error(
            str(result.get("error", "register_agent_profile_failed")),
            str(details.get("message", "Failed to create or update agent profile.")),
            details=details,
        )

    warnings.extend(list(result.get("warnings", [])))
    return {
        "ok": True,
        "local_only": True,
        "created": bool(result.get("created", False)),
        "agent": result.get("agent", {}),
        "warnings": sorted(set(warnings)),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }


def get_agent(config: AppConfig, agent_id: str) -> dict[str, Any]:
    normalized_agent_id = agent_id.strip()
    result = inspect_agent_profile(config, agent_id=normalized_agent_id, output_format="json")
    if not result.get("ok", False):
        details = dict(result.get("details", {}))
        error = str(result.get("error", "agent_profile_not_found"))
        status = 404 if error in {"agent_profile_not_found", "agent_profiles_not_found"} else 400
        return _api_error(
            error,
            str(details.get("message", "Agent profile was not found.")),
            details=details,
            status=status,
        )

    payload = _extract_operator_payload(result)
    agent = payload.get("agent", {}) if isinstance(payload.get("agent"), dict) else {}

    warnings: list[str] = []
    linked_target: dict[str, Any] | None = None
    target_id = str(agent.get("handoff_target_id", "")).strip()
    if target_id:
        target_result = inspect_handoff_target(config, target_id=target_id, output_format="json")
        if target_result.get("ok", False):
            target_payload = _extract_operator_payload(target_result)
            candidate = target_payload.get("handoff_target")
            if isinstance(candidate, dict):
                linked_target = candidate
        else:
            warnings.append(
                f"Referenced handoff target '{target_id}' is not currently available in local profiles."
            )
    else:
        warnings.append("Agent has no linked handoff target.")

    return {
        "ok": True,
        "local_only": True,
        "agent": agent,
        "linked_handoff_target": linked_target,
        "warnings": sorted(set(warnings)),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }


def get_handoff_targets(config: AppConfig) -> dict[str, Any]:
    snapshot, warnings, profiles_path = _load_profiles_if_present(config)
    targets = (
        snapshot.get("handoff_targets", []) if isinstance(snapshot.get("handoff_targets"), list) else []
    )
    return {
        "ok": True,
        "local_only": True,
        "profiles_path": str(profiles_path),
        "handoff_targets": targets,
        "target_count": len(targets),
        "counts_by_target_type": _counts_by(targets, "target_type"),
        "counts_by_status": _counts_by(targets, "status"),
        "warnings": sorted(set(warnings)),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }


def post_handoff_target(config: AppConfig, body: dict[str, Any]) -> dict[str, Any]:
    target_id = str(body.get("target_id", "")).strip()
    name = str(body.get("name", "")).strip()
    target_type = str(body.get("target_type", "")).strip()
    if not target_id or not name or not target_type:
        return _api_error(
            "invalid_handoff_target_payload",
            "target_id, name, and target_type are required.",
            details={"required_fields": ["target_id", "name", "target_type"]},
        )
    if target_type not in HANDOFF_TARGET_TYPES:
        return _invalid_choice_error(
            field="target_type",
            value=target_type,
            supported=HANDOFF_TARGET_TYPES,
            label="target type",
        )

    status = _normalize_optional_str(body.get("status"))
    if status is not None and status not in AGENT_PROFILE_STATUSES:
        return _invalid_choice_error(
            field="status",
            value=status,
            supported=AGENT_PROFILE_STATUSES,
            label="status",
        )

    warnings: list[str] = []
    profiles_path = resolve_agent_profiles_path(config.repo_root, None)
    if not profiles_path.exists():
        init_result = init_agent_profiles(config)
        if not init_result.get("ok", False):
            return _api_error(
                str(init_result.get("error", "agent_profiles_init_failed")),
                "Failed to initialize agent profiles storage.",
                details=dict(init_result.get("details", {})),
            )
        warnings.append("Local agent profiles were initialized automatically.")

    result = register_handoff_target(
        config,
        target_id=target_id,
        name=name,
        target_type=target_type,
        description=_normalize_optional_str(body.get("description")),
        local_command=_normalize_optional_str(body.get("local_command")),
        input_format=_normalize_optional_str(body.get("input_format")),
        output_format=_normalize_optional_str(body.get("output_format")),
        safety_notes=_normalize_optional_list(body.get("safety_notes")),
        status=status,
        tags=_normalize_optional_list(body.get("tags")),
        notes=_normalize_optional_str(body.get("notes")),
    )
    if not result.get("ok", False):
        details = dict(result.get("details", {}))
        return _api_error(
            str(result.get("error", "register_handoff_target_failed")),
            str(details.get("message", "Failed to create or update handoff target.")),
            details=details,
        )

    return {
        "ok": True,
        "local_only": True,
        "created": bool(result.get("created", False)),
        "handoff_target": result.get("handoff_target", {}),
        "warnings": sorted(set(warnings)),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }


def get_handoff_target(config: AppConfig, target_id: str) -> dict[str, Any]:
    normalized_target_id = target_id.strip()
    result = inspect_handoff_target(config, target_id=normalized_target_id, output_format="json")
    if not result.get("ok", False):
        details = dict(result.get("details", {}))
        error = str(result.get("error", "handoff_target_not_found"))
        status = 404 if error in {"handoff_target_not_found", "agent_profiles_not_found"} else 400
        return _api_error(
            error,
            str(details.get("message", "Handoff target was not found.")),
            details=details,
            status=status,
        )

    payload = _extract_operator_payload(result)
    target = payload.get("handoff_target", {}) if isinstance(payload.get("handoff_target"), dict) else {}
    return {
        "ok": True,
        "local_only": True,
        "handoff_target": target,
        "warnings": [],
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }


def get_handoff_preview(config: AppConfig) -> dict[str, Any]:
    result = generate_handoff_package(config, output=None, output_format="markdown", include_doc_excerpts=False)
    if not result.get("ok", False):
        details = dict(result.get("details", {}))
        return _api_error(
            str(result.get("error", "handoff_preview_failed")),
            str(details.get("message", "Failed to generate local handoff preview.")),
            details=details,
        )

    payload = result.get("payload", {}) if isinstance(result.get("payload"), dict) else {}
    warnings = payload.get("warnings", []) if isinstance(payload.get("warnings"), list) else []
    return {
        "ok": True,
        "local_only": True,
        "preview_format": "markdown",
        "preview": str(result.get("stdout", "")),
        "warnings": sorted(set(str(item) for item in warnings)),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS)
        + [
            "Handoff preview is local-only and does not post anywhere.",
        ],
    }


def _validate_plan_request_filters(body: dict[str, Any], *, allow_item_id: bool) -> dict[str, Any] | None:
    status = _normalize_optional_str(body.get("status"))
    if status is not None and status not in QUEUE_STATUSES:
        return _invalid_choice_error(
            field="status",
            value=status,
            supported=QUEUE_STATUSES,
            label="status",
        )

    if allow_item_id and "item_id" in body:
        item_id = body.get("item_id")
        if item_id is not None and not str(item_id).strip():
            return _api_error("invalid_item_id", "item_id cannot be empty when provided.")

    for key in ("project_id", "repo_id"):
        if key in body and body.get(key) is not None and not str(body.get(key)).strip():
            return _api_error(f"invalid_{key}", f"{key} cannot be empty when provided.")
    return None


def _plan_payload(base_payload: dict[str, Any]) -> dict[str, Any]:
    payload = dict(base_payload)
    payload["ok"] = True
    payload["local_only"] = True
    payload["plan_only"] = True
    payload["boundary_confirmations"] = list(
        dict.fromkeys(
            list(payload.get("boundary_confirmations", []))
            + list(_BOUNDARY_CONFIRMATIONS)
            + list(_PLAN_ONLY_CONFIRMATIONS)
        )
    )
    return payload


def post_orchestration_plan(config: AppConfig, body: dict[str, Any]) -> dict[str, Any]:
    validation_error = _validate_plan_request_filters(body, allow_item_id=False)
    if validation_error is not None:
        return validation_error

    output_format = _normalize_optional_str(body.get("format")) or "json"
    if output_format not in {"json", "markdown"}:
        return _api_error(
            "invalid_format",
            "format must be json or markdown.",
            details={"format": output_format, "supported_formats": ["json", "markdown"]},
        )

    result = generate_agent_orchestration_plan(
        config,
        project_id=_normalize_optional_str(body.get("project_id")),
        repo_id=_normalize_optional_str(body.get("repo_id")),
        status=_normalize_optional_str(body.get("status")),
        output_format=output_format,
    )
    if not result.get("ok", False):
        details = dict(result.get("details", {}))
        return _api_error(
            str(result.get("error", "orchestration_plan_failed")),
            str(details.get("message", "Failed to generate local orchestration plan.")),
            details=details,
        )
    return _plan_payload(result.get("payload", {}))


def get_orchestration_plan(config: AppConfig) -> dict[str, Any]:
    result = generate_agent_orchestration_plan(config, output_format="json")
    if not result.get("ok", False):
        details = dict(result.get("details", {}))
        return _api_error(
            str(result.get("error", "orchestration_plan_failed")),
            str(details.get("message", "Failed to generate local orchestration plan.")),
            details=details,
        )
    return _plan_payload(result.get("payload", {}))


def post_escalation_plan(config: AppConfig, body: dict[str, Any]) -> dict[str, Any]:
    validation_error = _validate_plan_request_filters(body, allow_item_id=True)
    if validation_error is not None:
        return validation_error

    output_format = _normalize_optional_str(body.get("format")) or "json"
    if output_format not in {"json", "markdown"}:
        return _api_error(
            "invalid_format",
            "format must be json or markdown.",
            details={"format": output_format, "supported_formats": ["json", "markdown"]},
        )

    result = generate_llm_escalation_plan(
        config,
        item_id=_normalize_optional_str(body.get("item_id")),
        project_id=_normalize_optional_str(body.get("project_id")),
        repo_id=_normalize_optional_str(body.get("repo_id")),
        status=_normalize_optional_str(body.get("status")),
        output_format=output_format,
    )
    if not result.get("ok", False):
        details = dict(result.get("details", {}))
        return _api_error(
            str(result.get("error", "escalation_plan_failed")),
            str(details.get("message", "Failed to generate local escalation plan.")),
            details=details,
        )
    return _plan_payload(result.get("payload", {}))


def get_escalation_plan(config: AppConfig) -> dict[str, Any]:
    result = generate_llm_escalation_plan(config, output_format="json")
    if not result.get("ok", False):
        details = dict(result.get("details", {}))
        return _api_error(
            str(result.get("error", "escalation_plan_failed")),
            str(details.get("message", "Failed to generate local escalation plan.")),
            details=details,
        )
    return _plan_payload(result.get("payload", {}))


def get_settings(config: AppConfig) -> dict[str, Any]:
    return {
        "ok": True,
        "local_only": True,
        "report_only": True,
        "registry_path": str(resolve_managed_project_registry_path(config.repo_root, None)),
        "queue_path": str(resolve_project_queue_path(config.repo_root, None)),
        "agents_path": str(resolve_agent_profiles_path(config.repo_root, None)),
        "default_registry_path": str(resolve_managed_project_registry_path(config.repo_root, None)),
        "default_queue_path": str(resolve_project_queue_path(config.repo_root, None)),
        "default_agent_profiles_path": str(resolve_agent_profiles_path(config.repo_root, None)),
        "default_artifact_paths": {
            "handoff": str(config.artifact_root / "handoff"),
            "orchestration": str(config.repo_root / ORCHESTRATION_OUTPUT_DIR),
            "escalation": str(config.repo_root / ESCALATION_OUTPUT_DIR),
            "dashboard": str(config.artifact_root / "dashboard"),
        },
        "hub_server": {
            "default_host": "127.0.0.1",
            "default_port": 8765,
            "current_host_hint": "127.0.0.1",
            "current_port_hint": 8765,
        },
        "known_limitations": [
            "Local-only and report/plan-only workflows.",
            "No agent execution.",
            "No local/cloud/Codex/ChatGPT/Ollama model invocation.",
            "No GitHub, gh, network services, or external API calls.",
            "Live GitHub sync is not implemented.",
            "Authentication and production deployment are not implemented.",
        ],
        "next_milestone_scope": [
            "Richer UI workflow depth and guided operator flows.",
            "Optional execution gates with explicit user approval.",
            "Authentication and deployment hardening if exposed beyond localhost.",
            "Controlled GitHub sync execution with safety gates.",
            "Optional LLM execution behind explicit user-approved gates.",
        ],
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
        "m39_boundary_confirmations": [
            "M39 screens are local-only and file-backed.",
            "Orchestration and escalation are plan-only.",
            "No agents are executed.",
            "No local/cloud/Codex/ChatGPT/Ollama model invocation.",
        ],
        "m40_boundary_confirmations": [
            "M40 reports/workflows are local-only and report/plan-only.",
            "No agents are executed.",
            "No local/cloud/Codex/ChatGPT/Ollama model invocation.",
            "No GitHub, gh, network, or external API calls.",
            "No live GitHub sync execution.",
        ],
    }
