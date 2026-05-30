from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.local_project_dashboard import summarize_docs_status, summarize_local_project_dashboard
from aresforge.operator.local_dashboard_summary import summarize_hub_home_dashboard
from aresforge.operator.local_project_report import inspect_local_project_report, read_local_project_reports
from aresforge.operator.local_project_readiness import list_local_projects
from aresforge.operator.local_queue_agent_summary import inspect_local_queue_agent_summary
from aresforge.operator.local_active_project import inspect_active_project, set_active_project
from aresforge.operator.local_ai_action_safety import evaluate_ai_action_safety_gate
from aresforge.operator.local_ai_artifacts import filter_ai_artifacts
from aresforge.operator.dispatch_approval_gate import inspect_dispatch_approval_gate
from aresforge.operator.hub_dispatch_review import build_hub_dispatch_review_panel
from aresforge.operator.agent_route_recommendation import recommend_agent_route
from aresforge.operator.local_execution_audit import filter_execution_audit_log
from aresforge.operator.local_operator_run_history import read_ai_action_review_panel, read_operator_run_history
from aresforge.operator.local_project_queue import (
    QUEUE_ITEM_TYPES,
    QUEUE_PRIORITIES,
    QUEUE_ROUTING_AGENT_LANES,
    QUEUE_ROUTING_COMPLEXITY_LEVELS,
    QUEUE_ROUTING_ENGINES,
    QUEUE_ROUTING_RISK_LEVELS,
    QUEUE_STATUSES,
    add_local_queue_item,
    add_queue_item,
    capture_local_queue_completion_evidence,
    close_local_queue_item,
    complete_local_queue_item,
    default_queue_routing_metadata,
    execute_local_llm_for_queue_item,
    generate_codex_high_value_lane_prompt,
    generate_local_queue_prompt_pack,
    generate_local_queue_item_codex_prompt,
    generate_local_llm_prompt_preview,
    init_project_queue,
    inspect_local_queue_item_readiness,
    read_local_routed_queue_views,
    read_local_project_progress_rollup,
    resolve_project_queue_path,
    start_local_queue_item,
    update_local_queue_item_routing_metadata,
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
from aresforge.operator.local_project_handoff import generate_local_project_handoff
from aresforge.operator.local_agent_orchestration import generate_agent_orchestration_plan
from aresforge.operator.local_llm_escalation import generate_llm_escalation_plan
from aresforge.operator.local_bootstrap_wizard import (
    apply_bootstrap,
    inspect_bootstrap_status,
    plan_bootstrap,
)
from aresforge.operator.local_project_factory import (
    AGENT_LANE_KEYS,
    AI_ENGINE_KEYS,
    apply_queue_item_routing_recommendation,
    approve_project_documentation_closeout_plan,
    approve_project_execution_phase_approval,
    approve_project_validation_execution_plan,
    approve_project_agent_dispatch_plan,
    approve_project_github_apply_plan,
    GITHUB_MODES,
    PROJECT_AI_MODES,
    PROJECT_TYPES,
    LOCAL_LLM_PROVIDERS,
    approve_project_architecture_contract,
    approve_project_milestone_issue_plan,
    approve_project_scope_package,
    check_local_llm_health,
    inspect_project_factory_dossier,
    read_codex_cli_model_profile_contract,
    prepare_project_architecture_contract,
    prepare_project_documentation_closeout_plan,
    prepare_project_execution_phase_approval,
    prepare_project_agent_dispatch_plan,
    prepare_project_validation_execution_plan,
    prepare_project_github_apply_plan,
    prepare_project_milestone_issue_plan,
    prepare_project_scope_package,
    read_agent_engine_registry,
    recommend_queue_item_routing,
    read_project_architecture_contract,
    read_project_documentation_closeout_plan,
    read_project_execution_readiness,
    read_project_execution_phase_approval,
    read_project_agent_dispatch_plan,
    read_project_ai_settings,
    read_local_llm_environment_contract,
    read_project_validation_execution_plan,
    read_project_github_apply_plan,
    read_project_milestone_issue_plan,
    read_project_scope_package,
    update_project_ai_settings,
    update_local_llm_environment_contract,
    update_codex_cli_model_profile_contract,
    update_project_architecture_contract,
    update_project_documentation_closeout_plan,
    update_project_execution_phase_approval,
    update_project_agent_dispatch_plan,
    update_project_validation_execution_plan,
    update_project_github_apply_plan,
    update_project_milestone_issue_plan,
    update_project_scope_package,
    start_new_project_factory,
)
from aresforge.operator.llm_decision_matrix import build_llm_decision_matrix
from aresforge.operator.managed_project_registry_local import (
    PROJECT_STATUSES,
    REPO_ROLES,
    REPO_STATUSES,
    init_managed_project_registry,
    inspect_managed_repo_github_link,
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
        "primary_repo_id": str(project.get("primary_repo_id", "")).strip(),
        "github_owner": str(project.get("github_owner", "")).strip(),
        "github_repo": str(project.get("github_repo", "")).strip(),
        "github_url": str(project.get("github_url", "")).strip(),
        "github_default_branch": str(project.get("github_default_branch", "")).strip(),
        "github_connection_status": str(project.get("github_connection_status", "")).strip(),
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
        "github_owner": str(repo.get("github_owner", "")).strip(),
        "github_repo": str(repo.get("github_repo", "")).strip(),
        "github_url": str(repo.get("github_url", "")).strip(),
        "github_default_branch": str(repo.get("github_default_branch", "")).strip(),
        "github_connection_status": str(repo.get("github_connection_status", "")).strip(),
        "local_git_branch": str(repo.get("local_git_branch", "")).strip(),
        "local_git_head": str(repo.get("local_git_head", "")).strip(),
        "local_git_remote_url": str(repo.get("local_git_remote_url", "")).strip(),
        "local_git_status_summary": str(repo.get("local_git_status_summary", "")).strip(),
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
        "completion_evidence": item.get("completion_evidence", {}) if isinstance(item.get("completion_evidence"), dict) else {},
        "routing_metadata": default_queue_routing_metadata(
            item.get("routing_metadata", {}) if isinstance(item.get("routing_metadata"), dict) else {}
        ),
        "closed_at": str(item.get("closed_at", "")).strip(),
        "closed_by": str(item.get("closed_by", "")).strip(),
        "closeout_summary": str(item.get("closeout_summary", "")).strip(),
        "closeout_history": item.get("closeout_history", []) if isinstance(item.get("closeout_history"), list) else [],
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


def _require_list_field(body: dict[str, Any], field: str) -> tuple[bool, dict[str, Any] | None]:
    if field not in body or body.get(field) is None:
        return True, None
    if isinstance(body.get(field), list):
        return True, None
    return False, _api_error(
        f"invalid_{field}",
        f"{field} must be a list of strings.",
        details={field: body.get(field)},
    )


def _merge_boundary_confirmations(payload: dict[str, Any], *extra: str) -> list[str]:
    existing = payload.get("boundary_confirmations", [])
    merged = list(existing) if isinstance(existing, list) else []
    merged.extend(_BOUNDARY_CONFIRMATIONS)
    merged.extend([value for value in extra if value])
    return list(dict.fromkeys(merged))


def _status_for_local_queue_result(result: dict[str, Any]) -> int:
    error = str(result.get("error", "")).strip()
    readiness_status = str(result.get("readiness_status", "")).strip()
    warnings = [str(warning).strip().lower() for warning in result.get("warnings", []) if str(warning).strip()]

    if error in {
        "project_queue_not_found",
        "queue_item_not_found",
        "managed_project_not_found",
        "managed_repo_not_found",
    } or readiness_status == "not_found" or any("not found" in warning for warning in warnings):
        return 404

    command = str(result.get("command", "")).strip()
    if command in {
        "start-local-queue-item",
        "complete-local-queue-item",
        "generate-local-queue-item-codex-prompt",
        "close-local-queue-item",
    }:
        return 409
    return 400


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


def get_local_project_dashboard(config: AppConfig) -> dict[str, Any]:
    payload = summarize_local_project_dashboard(config)
    payload.update(
        {
            "ok": True,
            "service": SERVICE_NAME,
        }
    )
    return payload


def get_local_project_report(config: AppConfig) -> dict[str, Any]:
    payload = inspect_local_project_report(config)
    payload.update(
        {
            "ok": True,
            "service": SERVICE_NAME,
        }
    )
    return payload


def get_dashboard_summary(config: AppConfig) -> dict[str, Any]:
    payload = summarize_hub_home_dashboard(config)
    payload.update(
        {
            "ok": True,
            "service": SERVICE_NAME,
        }
    )
    return payload


def get_local_projects_readiness(config: AppConfig) -> dict[str, Any]:
    payload = list_local_projects(config)
    payload.update(
        {
            "ok": True,
            "service": SERVICE_NAME,
        }
    )
    return payload


def get_local_queue_agent_summary(config: AppConfig) -> dict[str, Any]:
    payload = inspect_local_queue_agent_summary(config)
    payload.update(
        {
            "ok": True,
            "service": SERVICE_NAME,
        }
    )
    return payload


def get_execution_audit_log(config: AppConfig, params: dict[str, str | None]) -> dict[str, Any]:
    executed_value = _normalize_optional_str(params.get("executed"))
    executed: bool | None = None
    if executed_value is not None:
        lowered = executed_value.lower()
        if lowered not in {"true", "false"}:
            return _api_error(
                "invalid_executed",
                "executed must be true or false when supplied.",
                details={"executed": executed_value},
            )
        executed = lowered == "true"

    limit_value = _normalize_optional_str(params.get("limit"))
    limit: int | None = None
    if limit_value is not None:
        try:
            limit = int(limit_value)
        except ValueError:
            return _api_error("invalid_limit", "limit must be an integer.", details={"limit": limit_value})
        if limit <= 0:
            return _api_error("invalid_limit", "limit must be greater than zero.", details={"limit": limit_value})

    payload = filter_execution_audit_log(
        config,
        project_id=_normalize_optional_str(params.get("project_id")),
        item_id=_normalize_optional_str(params.get("item_id")),
        action_type=_normalize_optional_str(params.get("action_type")),
        engine=_normalize_optional_str(params.get("engine")),
        executed=executed,
        outcome=_normalize_optional_str(params.get("outcome")),
        limit=limit,
    )
    payload["service"] = SERVICE_NAME
    payload["boundary_confirmations"] = _merge_boundary_confirmations(
        payload,
        "Execution audit log is read-only and does not execute Codex, local LLMs, agents, GitHub, gh, or workflows.",
    )
    return payload


def get_ai_artifacts(config: AppConfig, params: dict[str, str | None]) -> dict[str, Any]:
    exists_value = _normalize_optional_str(params.get("exists"))
    exists: bool | None = None
    if exists_value is not None:
        lowered = exists_value.lower()
        if lowered not in {"true", "false"}:
            return _api_error(
                "invalid_exists",
                "exists must be true or false when supplied.",
                details={"exists": exists_value},
            )
        exists = lowered == "true"

    limit_value = _normalize_optional_str(params.get("limit"))
    limit: int | None = None
    if limit_value is not None:
        try:
            limit = int(limit_value)
        except ValueError:
            return _api_error("invalid_limit", "limit must be an integer.", details={"limit": limit_value})
        if limit <= 0:
            return _api_error("invalid_limit", "limit must be greater than zero.", details={"limit": limit_value})

    payload = filter_ai_artifacts(
        config,
        project_id=_normalize_optional_str(params.get("project_id")),
        item_id=_normalize_optional_str(params.get("item_id")),
        artifact_type=_normalize_optional_str(params.get("artifact_type")),
        source_action=_normalize_optional_str(params.get("source_action")),
        engine=_normalize_optional_str(params.get("engine")),
        exists=exists,
        limit=limit,
    )
    payload["service"] = SERVICE_NAME
    payload["boundary_confirmations"] = _merge_boundary_confirmations(
        payload,
        "AI artifact registry is read-only through the Hub and does not execute actions.",
    )
    return payload


def get_dispatch_approval_gates(config: AppConfig, params: dict[str, str | None]) -> dict[str, Any]:
    limit_value = _normalize_optional_str(params.get("limit"))
    limit: int | None = None
    if limit_value is not None:
        try:
            limit = int(limit_value)
        except ValueError:
            return _api_error("invalid_limit", "limit must be an integer.", details={"limit": limit_value})
        if limit <= 0:
            return _api_error("invalid_limit", "limit must be greater than zero.", details={"limit": limit_value})

    payload = inspect_dispatch_approval_gate(
        config,
        approval_id=_normalize_optional_str(params.get("approval_id")),
        item_id=_normalize_optional_str(params.get("item_id")),
        limit=limit,
        output_format="json",
    )
    gate_payload = payload.get("payload", {}) if isinstance(payload.get("payload"), dict) else {}
    gate_payload["service"] = SERVICE_NAME
    gate_payload["hub_read_only"] = True
    gate_payload["boundary_confirmations"] = _merge_boundary_confirmations(
        gate_payload,
        "Dispatch approval gate Hub panel is read-only and never executes approved artifacts.",
    )
    return gate_payload


def get_dispatch_review_panel(config: AppConfig, params: dict[str, str | None]) -> dict[str, Any]:
    limit_value = _normalize_optional_str(params.get("limit"))
    limit: int | None = None
    if limit_value is not None:
        try:
            limit = int(limit_value)
        except ValueError:
            return _api_error("invalid_limit", "limit must be an integer.", details={"limit": limit_value})
        if limit <= 0:
            return _api_error("invalid_limit", "limit must be greater than zero.", details={"limit": limit_value})

    payload = build_hub_dispatch_review_panel(
        config,
        item_id=_normalize_optional_str(params.get("item_id")),
        limit=limit,
    )
    payload["service"] = SERVICE_NAME
    payload["hub_read_only"] = True
    payload["local_only"] = True
    payload["execution_allowed"] = False
    payload["boundary_confirmations"] = _merge_boundary_confirmations(
        payload,
        "Dispatch review API is read-only and advisory.",
        "No execution endpoints are exposed by this panel.",
    )
    return payload


def get_agent_route_recommendation(config: AppConfig, params: dict[str, str | None]) -> dict[str, Any]:
    item_id = _normalize_optional_str(params.get("item_id"))
    if not item_id:
        return _api_error("missing_item_id", "item_id is required for agent route recommendation.")

    result = recommend_agent_route(
        config,
        item_id=item_id,
        queue_path=_normalize_optional_str(params.get("queue_path")),
        output_format="json",
    )
    payload = result.get("payload", {}) if isinstance(result.get("payload"), dict) else {}
    payload["service"] = SERVICE_NAME
    payload["hub_read_only"] = True
    payload["local_only"] = True
    payload["execution_allowed"] = False
    payload["dispatch_performed"] = False
    payload["boundary_confirmations"] = _merge_boundary_confirmations(
        payload,
        "Agent route recommendation API is read-only and advisory.",
        "No execution endpoint, dispatch endpoint, or apply action is exposed by this panel.",
    )
    return payload


def get_operator_run_history(config: AppConfig, params: dict[str, str | None]) -> dict[str, Any]:
    limit_value = _normalize_optional_str(params.get("limit"))
    limit: int | None = None
    if limit_value is not None:
        try:
            limit = int(limit_value)
        except ValueError:
            return _api_error("invalid_limit", "limit must be an integer.", details={"limit": limit_value})
        if limit <= 0:
            return _api_error("invalid_limit", "limit must be greater than zero.", details={"limit": limit_value})

    payload = read_operator_run_history(
        config,
        project_id=_normalize_optional_str(params.get("project_id")),
        item_id=_normalize_optional_str(params.get("item_id")),
        action_type=_normalize_optional_str(params.get("action_type")),
        artifact_type=_normalize_optional_str(params.get("artifact_type")),
        limit=limit,
    )
    payload["service"] = SERVICE_NAME
    payload["boundary_confirmations"] = _merge_boundary_confirmations(
        payload,
        "Operator run history is read-only and does not execute actions.",
    )
    return payload


def get_ai_action_review(config: AppConfig, params: dict[str, str | None]) -> dict[str, Any]:
    limit_value = _normalize_optional_str(params.get("limit"))
    limit: int | None = None
    if limit_value is not None:
        try:
            limit = int(limit_value)
        except ValueError:
            return _api_error("invalid_limit", "limit must be an integer.", details={"limit": limit_value})
        if limit <= 0:
            return _api_error("invalid_limit", "limit must be greater than zero.", details={"limit": limit_value})

    payload = read_ai_action_review_panel(
        config,
        project_id=_normalize_optional_str(params.get("project_id")),
        item_id=_normalize_optional_str(params.get("item_id")),
        action_type=_normalize_optional_str(params.get("action_type")),
        artifact_type=_normalize_optional_str(params.get("artifact_type")),
        limit=limit,
    )
    payload["service"] = SERVICE_NAME
    payload["boundary_confirmations"] = _merge_boundary_confirmations(
        payload,
        "AI Action Review Panel is read-only and does not execute Codex, local LLMs, agents, GitHub, gh, workflows, or repo mutations.",
    )
    return payload


def post_ai_action_safety_gate(config: AppConfig, body: dict[str, Any]) -> dict[str, Any]:
    for field in ("operator_override", "confirm_operator_gate", "dry_run"):
        valid_bool, bool_error = _require_boolean_field(body, field)
        if not valid_bool:
            return bool_error or _api_error(f"invalid_{field}", f"{field} must be a boolean value.")

    action_type = str(body.get("action_type", "")).strip()
    if not action_type:
        return _api_error(
            "invalid_action_type",
            "action_type is required.",
            details={"required_fields": ["action_type"]},
        )

    payload = evaluate_ai_action_safety_gate(
        config,
        action_type=action_type,
        item_id=_normalize_optional_str(body.get("item_id")),
        project_id=_normalize_optional_str(body.get("project_id")),
        engine=_normalize_optional_str(body.get("engine")),
        model=_normalize_optional_str(body.get("model")),
        agent_lane=_normalize_optional_str(body.get("agent_lane")),
        risk_level=_normalize_optional_str(body.get("risk_level")),
        complexity_level=_normalize_optional_str(body.get("complexity_level")),
        project_ai_mode=_normalize_optional_str(body.get("project_ai_mode")),
        operator_override=bool(body.get("operator_override", False)),
        confirm_operator_gate=bool(body.get("confirm_operator_gate", False)),
        dry_run=bool(body.get("dry_run", False)),
    )
    payload["service"] = SERVICE_NAME
    payload["boundary_confirmations"] = _merge_boundary_confirmations(
        payload,
        "AI action safety gate is decision/reporting logic only and does not execute actions.",
    )
    return payload


def get_bootstrap_status(config: AppConfig) -> dict[str, Any]:
    payload = inspect_bootstrap_status(config, repo_path=config.repo_root)
    payload.update(
        {
            "service": SERVICE_NAME,
            "local_only": True,
            "warnings": payload.get("warnings", []),
            "boundary_confirmations": list(
                dict.fromkeys(list(payload.get("boundary_confirmations", [])) + list(_BOUNDARY_CONFIRMATIONS))
            ),
        }
    )
    return payload


def get_bootstrap_plan(config: AppConfig, params: dict[str, str | None]) -> dict[str, Any]:
    seed_value = str(params.get("seed_sample_work") or "false").strip().lower()
    seed_sample_work = seed_value in {"1", "true", "yes", "on"}
    result = plan_bootstrap(
        config,
        repo_path=config.repo_root,
        seed_sample_work=seed_sample_work,
        output_format="json",
    )
    if not result.get("ok", False):
        details = dict(result.get("details", {}))
        return _api_error(
            str(result.get("error", "bootstrap_plan_failed")),
            str(details.get("message", "Failed to generate bootstrap plan.")),
            details=details,
        )
    payload = result.get("payload", {}) if isinstance(result.get("payload"), dict) else {}
    payload.update(
        {
            "ok": True,
            "service": SERVICE_NAME,
            "local_only": True,
            "plan_only": True,
            "warnings": payload.get("warnings", []),
            "boundary_confirmations": list(
                dict.fromkeys(list(payload.get("boundary_confirmations", [])) + list(_BOUNDARY_CONFIRMATIONS))
            ),
        }
    )
    return payload


def post_bootstrap_apply(config: AppConfig, body: dict[str, Any]) -> dict[str, Any]:
    valid_force, force_error = _require_boolean_field(body, "force")
    if not valid_force:
        return force_error or _api_error("invalid_force", "force must be a boolean value.")
    valid_seed, seed_error = _require_boolean_field(body, "seed_sample_work")
    if not valid_seed:
        return seed_error or _api_error("invalid_seed_sample_work", "seed_sample_work must be a boolean value.")

    result = apply_bootstrap(
        config,
        repo_path=config.repo_root,
        force=bool(body.get("force", False)),
        seed_sample_work=bool(body.get("seed_sample_work", False)),
        output_format="json",
    )
    if not result.get("ok", False):
        details = dict(result.get("details", {}))
        return _api_error(
            str(result.get("error", "bootstrap_apply_failed")),
            str(details.get("message", "Failed to apply bootstrap.")),
            details=details,
        )
    payload = result.get("payload", {}) if isinstance(result.get("payload"), dict) else {}
    payload.update(
        {
            "ok": True,
            "service": SERVICE_NAME,
            "local_only": True,
            "warnings": payload.get("warnings", []),
            "boundary_confirmations": list(
                dict.fromkeys(list(payload.get("boundary_confirmations", [])) + list(_BOUNDARY_CONFIRMATIONS))
            ),
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


def get_reports_local_projects(config: AppConfig) -> dict[str, Any]:
    payload = read_local_project_reports(config)
    payload.update(
        {
            "service": SERVICE_NAME,
            "boundary_confirmations": list(
                dict.fromkeys(list(payload.get("boundary_confirmations", [])) + list(_BOUNDARY_CONFIRMATIONS))
            ),
        }
    )
    return payload


def get_active_project_workspace(config: AppConfig) -> dict[str, Any]:
    dashboard = summarize_local_project_dashboard(config)
    report = inspect_local_project_report(config)

    active_project_summary = dashboard.get("active_project_summary", {})
    active_repo = active_project_summary.get("active_repo") or {}
    repo_status = {
        "available": bool(active_repo),
        "repo_id": str(active_project_summary.get("active_repo_id", "")).strip(),
        "name": str(active_repo.get("name", "")).strip(),
        "role": str(active_repo.get("role", "")).strip(),
        "status": str(active_repo.get("status", "")).strip(),
        "local_git_branch": str(active_repo.get("local_git_branch", "")).strip(),
        "local_git_head": str(active_repo.get("local_git_head", "")).strip(),
        "local_git_status_summary": str(active_repo.get("local_git_status_summary", "")).strip(),
        "message": "Local repo facts available." if active_repo else "No active repo facts available yet.",
    }
    report_status = {
        "overall_status": str((report.get("project_health") or {}).get("overall_status", "needs_attention")).strip()
        or "needs_attention",
        "docs_ready": bool((report.get("documentation_summary") or {}).get("docs_ready", False)),
        "validation_ready": bool((report.get("validation_summary") or {}).get("hub_ready", False)),
        "roadmap_status": str((report.get("roadmap_summary") or {}).get("status", "missing")).strip() or "missing",
        "message": str(report.get("recommended_next_action", "")).strip() or "No report recommendation available.",
    }

    warnings: list[str] = []
    for warning in list(dashboard.get("warnings", [])) + list(report.get("warnings", [])):
        normalized = str(warning).strip()
        if normalized and normalized not in warnings:
            warnings.append(normalized)

    return {
        "ok": True,
        "service": SERVICE_NAME,
        "local_only": True,
        "report_only": True,
        "generated_at": dashboard.get("generated_at") or report.get("generated_at"),
        "active_project_selected": bool(dashboard.get("active_project_selected", False)),
        "active_project_id": str(dashboard.get("active_project_id", "")).strip(),
        "active_repo_id": str(dashboard.get("active_repo_id", "")).strip(),
        "active_project_summary": active_project_summary,
        "current_queue_items": list(dashboard.get("active_project_current_items", [])),
        "recent_completed_queue_items": list(dashboard.get("active_project_recently_completed_items", [])),
        "report_status": report_status,
        "repo_status": repo_status,
        "next_safe_action": str(report.get("recommended_next_action", "")).strip()
        or str(dashboard.get("recommended_next_action", "")).strip()
        or "Select an active project to continue local-only workflow control.",
        "continue_actions": {
            "task_intake_section": "queue",
            "queue_lifecycle_section": "queue",
            "project_selection_section": "projects",
        },
        "warnings": warnings,
        "boundary_confirmations": _merge_boundary_confirmations(
            dashboard,
            "Workspace is local-only.",
            "Workspace reuses existing local report/dashboard data.",
        ),
    }


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


def get_active_project(config: AppConfig) -> dict[str, Any]:
    payload = inspect_active_project(config)
    payload.update(
        {
            "service": SERVICE_NAME,
            "boundary_confirmations": list(
                dict.fromkeys(list(payload.get("boundary_confirmations", [])) + list(_BOUNDARY_CONFIRMATIONS))
            ),
        }
    )
    return payload


def post_active_project(config: AppConfig, body: dict[str, Any]) -> dict[str, Any]:
    project_id = str(body.get("project_id", "")).strip()
    result = set_active_project(config, project_id=project_id)
    if not result.get("ok", False):
        details = dict(result.get("details", {}))
        error = str(result.get("error", "set_active_project_failed"))
        status = 404 if error == "managed_project_not_found" else 400
        return _api_error(
            error,
            str(details.get("message", "Failed to set active project.")),
            details=details,
            status=status,
        )
    result.update(
        {
            "service": SERVICE_NAME,
            "boundary_confirmations": list(
                dict.fromkeys(list(result.get("boundary_confirmations", [])) + list(_BOUNDARY_CONFIRMATIONS))
            ),
        }
    )
    return result


def post_project_factory_new_project(config: AppConfig, body: dict[str, Any]) -> dict[str, Any]:
    name = str(body.get("name", "")).strip()
    root_path = str(body.get("root_path", "")).strip()
    if not name or not root_path:
        return _api_error(
            "invalid_project_factory_payload",
            "name and root_path are required.",
            details={"required_fields": ["name", "root_path"]},
        )

    project_type = str(body.get("project_type", "other")).strip() or "other"
    if project_type not in PROJECT_TYPES:
        return _invalid_choice_error(
            field="project_type",
            value=project_type,
            supported=PROJECT_TYPES,
            label="project type",
        )

    github_mode = str(body.get("github_mode", "create-later")).strip() or "create-later"
    if github_mode not in GITHUB_MODES:
        return _invalid_choice_error(
            field="github_mode",
            value=github_mode,
            supported=GITHUB_MODES,
            label="GitHub mode",
        )

    tags_raw = body.get("tags")
    tags: list[str] = []
    if isinstance(tags_raw, list):
        tags = _normalize_str_list(tags_raw)
    elif isinstance(tags_raw, str):
        tags = _normalize_str_list([item for item in tags_raw.split(",")])

    result = start_new_project_factory(
        config,
        {
            "name": name,
            "project_id": str(body.get("project_id", "")).strip(),
            "description": str(body.get("description", "")).strip(),
            "project_type": project_type,
            "preferred_stack": str(body.get("preferred_stack", "")).strip(),
            "root_path": root_path,
            "github_owner": str(body.get("github_owner", "")).strip(),
            "github_repo": str(body.get("github_repo", "")).strip(),
            "github_mode": github_mode,
            "default_branch": str(body.get("default_branch", "main")).strip() or "main",
            "initial_requirements": str(body.get("initial_requirements", "")).strip(),
            "tags": tags,
        },
    )
    if not result.get("ok", False):
        details = dict(result.get("details", {}))
        return _api_error(
            str(result.get("error", "new_project_factory_failed")),
            str(details.get("message", "Failed to initialize local new project factory state.")),
            details=details,
        )

    return {
        "ok": True,
        "local_only": True,
        "project": result.get("project", {}),
        "repo": result.get("repo", {}),
        "active_project_id": str(result.get("active_project_id", "")).strip(),
        "scope_queue_item": result.get("scope_queue_item", {}),
        "dossier_path": str(result.get("dossier_path", "")).strip(),
        "dossier": result.get("dossier", {}),
        "warnings": result.get("warnings", []),
        "boundary_confirmations": list(
            dict.fromkeys(list(result.get("boundary_confirmations", [])) + list(_BOUNDARY_CONFIRMATIONS))
        ),
    }


def get_project_factory_dossier(config: AppConfig, params: dict[str, str | None]) -> dict[str, Any]:
    requested_project_id = str(params.get("project_id", "") or "").strip()
    warnings: list[str] = []
    project_id = requested_project_id
    if not project_id:
        active_payload = inspect_active_project(config)
        project_id = str(active_payload.get("active_project_id", "")).strip()
        if not project_id:
            warnings.append("No active project selected. Create/select a project to view its factory dossier.")
            return {
                "ok": True,
                "local_only": True,
                "project_id": "",
                "dossier_path": "",
                "dossier_exists": False,
                "dossier": {},
                "lifecycle_state": "not_started",
                "next_recommended_action": "create_project_via_new_project_wizard",
                "safety_boundary": {
                    "local_only": True,
                    "github_mutation_status": "not_requested",
                    "model_execution_status": "not_requested",
                },
                "workflow_steps": [],
                "warnings": sorted(set(warnings + list(active_payload.get("warnings", [])))),
                "boundary_confirmations": list(
                    dict.fromkeys(
                        list(_BOUNDARY_CONFIRMATIONS) + list(active_payload.get("boundary_confirmations", []))
                    )
                ),
            }

    payload = inspect_project_factory_dossier(config, project_id)
    warnings.extend(list(payload.get("warnings", [])))
    if requested_project_id and not payload.get("dossier_exists", False):
        warnings.append(f"Factory dossier not found for requested project: {requested_project_id}")
    payload["warnings"] = sorted(set(warnings))
    payload["boundary_confirmations"] = list(
        dict.fromkeys(list(payload.get("boundary_confirmations", [])) + list(_BOUNDARY_CONFIRMATIONS))
    )
    return payload


def get_project_factory_scope_package(config: AppConfig, params: dict[str, str | None]) -> dict[str, Any]:
    requested_project_id = str(params.get("project_id", "") or "").strip()
    project_id = requested_project_id
    warnings: list[str] = []
    if not project_id:
        active_payload = inspect_active_project(config)
        project_id = str(active_payload.get("active_project_id", "")).strip()
        if not project_id:
            warnings.append("No active project selected. Use Prepare Scope Package first.")
            return {
                "ok": True,
                "local_only": True,
                "project_id": "",
                "scope_package_path": "",
                "scope_package_exists": False,
                "scope_package": {},
                "warnings": sorted(set(warnings + list(active_payload.get("warnings", [])))),
                "boundary_confirmations": list(
                    dict.fromkeys(
                        list(_BOUNDARY_CONFIRMATIONS) + list(active_payload.get("boundary_confirmations", []))
                    )
                ),
            }

    payload = read_project_scope_package(config, project_id)
    payload["warnings"] = sorted(set(list(payload.get("warnings", [])) + warnings))
    payload["boundary_confirmations"] = list(
        dict.fromkeys(list(payload.get("boundary_confirmations", [])) + list(_BOUNDARY_CONFIRMATIONS))
    )
    return payload


def post_project_factory_scope_package(config: AppConfig, body: dict[str, Any]) -> dict[str, Any]:
    requested_project_id = str(body.get("project_id", "")).strip()
    project_id = requested_project_id
    if not project_id:
        active_payload = inspect_active_project(config)
        project_id = str(active_payload.get("active_project_id", "")).strip()
        if not project_id:
            return _api_error(
                "active_project_required",
                "project_id is required when no active project is selected.",
                details={"required_fields": ["project_id"], "active_project_selected": False},
                status=400,
            )

    result = prepare_project_scope_package(config, project_id)
    if not result.get("ok", False):
        error = str(result.get("error", "scope_package_prepare_failed"))
        status = 404 if error == "project_factory_dossier_not_found" else 400
        details = dict(result.get("details", {}))
        return _api_error(
            error,
            str(details.get("message", "Failed to prepare local scope package placeholder.")),
            details=details,
            status=status,
        )

    result["boundary_confirmations"] = list(
        dict.fromkeys(list(result.get("boundary_confirmations", [])) + list(_BOUNDARY_CONFIRMATIONS))
    )
    return result


def patch_project_factory_scope_package(config: AppConfig, body: dict[str, Any]) -> dict[str, Any]:
    requested_project_id = str(body.get("project_id", "")).strip()
    project_id = requested_project_id
    if not project_id:
        active_payload = inspect_active_project(config)
        project_id = str(active_payload.get("active_project_id", "")).strip()
        if not project_id:
            return _api_error(
                "active_project_required",
                "project_id is required when no active project is selected.",
                details={"required_fields": ["project_id"], "active_project_selected": False},
                status=400,
            )

    editable_payload = {
        "requirements": body.get("requirements"),
        "constraints": body.get("constraints"),
        "assumptions": body.get("assumptions"),
        "acceptance_criteria": body.get("acceptance_criteria"),
        "risks": body.get("risks"),
        "out_of_scope": body.get("out_of_scope"),
        "stakeholders": body.get("stakeholders"),
        "notes": body.get("notes"),
    }
    result = update_project_scope_package(config, project_id, editable_payload)
    if not result.get("ok", False):
        error = str(result.get("error", "scope_package_update_failed"))
        details = dict(result.get("details", {}))
        status = 404 if error == "scope_package_not_found" else 400
        return _api_error(
            error,
            str(details.get("message", "Failed to update local scope draft.")),
            details=details,
            status=status,
        )

    result["boundary_confirmations"] = list(
        dict.fromkeys(list(result.get("boundary_confirmations", [])) + list(_BOUNDARY_CONFIRMATIONS))
    )
    return result


def post_project_factory_scope_package_approve(config: AppConfig, body: dict[str, Any]) -> dict[str, Any]:
    requested_project_id = str(body.get("project_id", "")).strip()
    project_id = requested_project_id
    if not project_id:
        active_payload = inspect_active_project(config)
        project_id = str(active_payload.get("active_project_id", "")).strip()
        if not project_id:
            return _api_error(
                "active_project_required",
                "project_id is required when no active project is selected.",
                details={"required_fields": ["project_id"], "active_project_selected": False},
                status=400,
            )

    result = approve_project_scope_package(config, project_id, {"approved_by": body.get("approved_by")})
    if not result.get("ok", False):
        error = str(result.get("error", "scope_package_approval_failed"))
        details = dict(result.get("details", {}))
        status = 404 if error == "scope_package_not_found" else 400
        return _api_error(
            error,
            str(details.get("message", "Failed to approve local scope package.")),
            details=details,
            status=status,
        )

    result["boundary_confirmations"] = list(
        dict.fromkeys(list(result.get("boundary_confirmations", [])) + list(_BOUNDARY_CONFIRMATIONS))
    )
    return result


def get_project_factory_architecture_contract(config: AppConfig, params: dict[str, str | None]) -> dict[str, Any]:
    requested_project_id = str(params.get("project_id", "") or "").strip()
    project_id = requested_project_id
    warnings: list[str] = []
    if not project_id:
        active_payload = inspect_active_project(config)
        project_id = str(active_payload.get("active_project_id", "")).strip()
        if not project_id:
            warnings.append("No active project selected. Select a project and approve scope before architecture authoring.")
            return {
                "ok": True,
                "local_only": True,
                "project_id": "",
                "architecture_contract_path": "",
                "architecture_contract_exists": False,
                "architecture_contract": {},
                "warnings": sorted(set(warnings + list(active_payload.get("warnings", [])))),
                "boundary_confirmations": list(
                    dict.fromkeys(
                        list(_BOUNDARY_CONFIRMATIONS) + list(active_payload.get("boundary_confirmations", []))
                    )
                ),
            }

    payload = read_project_architecture_contract(config, project_id)
    payload["warnings"] = sorted(set(list(payload.get("warnings", [])) + warnings))
    payload["boundary_confirmations"] = list(
        dict.fromkeys(list(payload.get("boundary_confirmations", [])) + list(_BOUNDARY_CONFIRMATIONS))
    )
    return payload


def post_project_factory_architecture_contract(config: AppConfig, body: dict[str, Any]) -> dict[str, Any]:
    requested_project_id = str(body.get("project_id", "")).strip()
    project_id = requested_project_id
    if not project_id:
        active_payload = inspect_active_project(config)
        project_id = str(active_payload.get("active_project_id", "")).strip()
        if not project_id:
            return _api_error(
                "active_project_required",
                "project_id is required when no active project is selected.",
                details={"required_fields": ["project_id"], "active_project_selected": False},
                status=400,
            )

    result = prepare_project_architecture_contract(config, project_id)
    if not result.get("ok", False):
        error = str(result.get("error", "architecture_contract_prepare_failed"))
        details = dict(result.get("details", {}))
        status = 404 if error == "scope_package_not_found" else 409 if error == "scope_not_approved" else 400
        return _api_error(
            error,
            str(details.get("message", "Failed to prepare local architecture contract placeholder.")),
            details=details,
            status=status,
        )

    result["boundary_confirmations"] = list(
        dict.fromkeys(list(result.get("boundary_confirmations", [])) + list(_BOUNDARY_CONFIRMATIONS))
    )
    return result


def patch_project_factory_architecture_contract(config: AppConfig, body: dict[str, Any]) -> dict[str, Any]:
    requested_project_id = str(body.get("project_id", "")).strip()
    project_id = requested_project_id
    if not project_id:
        active_payload = inspect_active_project(config)
        project_id = str(active_payload.get("active_project_id", "")).strip()
        if not project_id:
            return _api_error(
                "active_project_required",
                "project_id is required when no active project is selected.",
                details={"required_fields": ["project_id"], "active_project_selected": False},
                status=400,
            )

    editable_payload = {
        "architecture_summary": body.get("architecture_summary"),
        "system_components": body.get("system_components"),
        "data_model_notes": body.get("data_model_notes"),
        "integration_points": body.get("integration_points"),
        "security_considerations": body.get("security_considerations"),
        "deployment_notes": body.get("deployment_notes"),
        "testing_strategy": body.get("testing_strategy"),
        "documentation_plan": body.get("documentation_plan"),
        "open_questions": body.get("open_questions"),
        "milestone_planning_notes": body.get("milestone_planning_notes"),
    }
    result = update_project_architecture_contract(config, project_id, editable_payload)
    if not result.get("ok", False):
        error = str(result.get("error", "architecture_contract_update_failed"))
        details = dict(result.get("details", {}))
        status = 404 if error == "architecture_contract_not_found" else 400
        return _api_error(
            error,
            str(details.get("message", "Failed to update local architecture draft.")),
            details=details,
            status=status,
        )

    result["boundary_confirmations"] = list(
        dict.fromkeys(list(result.get("boundary_confirmations", [])) + list(_BOUNDARY_CONFIRMATIONS))
    )
    return result


def post_project_factory_architecture_contract_approve(config: AppConfig, body: dict[str, Any]) -> dict[str, Any]:
    requested_project_id = str(body.get("project_id", "")).strip()
    project_id = requested_project_id
    if not project_id:
        active_payload = inspect_active_project(config)
        project_id = str(active_payload.get("active_project_id", "")).strip()
        if not project_id:
            return _api_error(
                "active_project_required",
                "project_id is required when no active project is selected.",
                details={"required_fields": ["project_id"], "active_project_selected": False},
                status=400,
            )

    result = approve_project_architecture_contract(config, project_id, {"approved_by": body.get("approved_by")})
    if not result.get("ok", False):
        error = str(result.get("error", "architecture_contract_approval_failed"))
        details = dict(result.get("details", {}))
        status = 404 if error == "architecture_contract_not_found" else 400
        return _api_error(
            error,
            str(details.get("message", "Failed to approve local architecture contract.")),
            details=details,
            status=status,
        )

    result["boundary_confirmations"] = list(
        dict.fromkeys(list(result.get("boundary_confirmations", [])) + list(_BOUNDARY_CONFIRMATIONS))
    )
    return result


def get_project_factory_milestone_issue_plan(config: AppConfig, params: dict[str, str | None]) -> dict[str, Any]:
    requested_project_id = str(params.get("project_id", "") or "").strip()
    project_id = requested_project_id
    warnings: list[str] = []
    if not project_id:
        active_payload = inspect_active_project(config)
        project_id = str(active_payload.get("active_project_id", "")).strip()
        if not project_id:
            warnings.append("No active project selected. Approve architecture first, then prepare milestone/issue plan.")
            return {
                "ok": True,
                "local_only": True,
                "project_id": "",
                "milestone_issue_plan_path": "",
                "milestone_issue_plan_exists": False,
                "milestone_issue_plan": {},
                "warnings": sorted(set(warnings + list(active_payload.get("warnings", [])))),
                "boundary_confirmations": list(
                    dict.fromkeys(
                        list(_BOUNDARY_CONFIRMATIONS) + list(active_payload.get("boundary_confirmations", []))
                    )
                ),
            }
    payload = read_project_milestone_issue_plan(config, project_id)
    payload["warnings"] = sorted(set(list(payload.get("warnings", [])) + warnings))
    payload["boundary_confirmations"] = list(
        dict.fromkeys(list(payload.get("boundary_confirmations", [])) + list(_BOUNDARY_CONFIRMATIONS))
    )
    return payload


def post_project_factory_milestone_issue_plan(config: AppConfig, body: dict[str, Any]) -> dict[str, Any]:
    requested_project_id = str(body.get("project_id", "")).strip()
    project_id = requested_project_id
    if not project_id:
        active_payload = inspect_active_project(config)
        project_id = str(active_payload.get("active_project_id", "")).strip()
        if not project_id:
            return _api_error(
                "active_project_required",
                "project_id is required when no active project is selected.",
                details={"required_fields": ["project_id"], "active_project_selected": False},
                status=400,
            )
    result = prepare_project_milestone_issue_plan(config, project_id)
    if not result.get("ok", False):
        error = str(result.get("error", "milestone_issue_plan_prepare_failed"))
        details = dict(result.get("details", {}))
        status = 404 if error == "architecture_contract_not_found" else 409 if error == "architecture_not_approved" else 400
        return _api_error(
            error,
            str(details.get("message", "Failed to prepare local milestone/issue plan placeholder.")),
            details=details,
            status=status,
        )
    result["boundary_confirmations"] = list(
        dict.fromkeys(list(result.get("boundary_confirmations", [])) + list(_BOUNDARY_CONFIRMATIONS))
    )
    return result


def patch_project_factory_milestone_issue_plan(config: AppConfig, body: dict[str, Any]) -> dict[str, Any]:
    requested_project_id = str(body.get("project_id", "")).strip()
    project_id = requested_project_id
    if not project_id:
        active_payload = inspect_active_project(config)
        project_id = str(active_payload.get("active_project_id", "")).strip()
        if not project_id:
            return _api_error(
                "active_project_required",
                "project_id is required when no active project is selected.",
                details={"required_fields": ["project_id"], "active_project_selected": False},
                status=400,
            )
    editable_payload = {
        "planning_summary": body.get("planning_summary"),
        "milestones": body.get("milestones"),
        "issues": body.get("issues"),
        "cross_cutting_tasks": body.get("cross_cutting_tasks"),
        "validation_plan": body.get("validation_plan"),
        "documentation_plan": body.get("documentation_plan"),
        "release_notes": body.get("release_notes"),
        "open_questions": body.get("open_questions"),
        "github_apply_notes": body.get("github_apply_notes"),
    }
    result = update_project_milestone_issue_plan(config, project_id, editable_payload)
    if not result.get("ok", False):
        error = str(result.get("error", "milestone_issue_plan_update_failed"))
        details = dict(result.get("details", {}))
        status = 404 if error == "milestone_issue_plan_not_found" else 400
        return _api_error(
            error,
            str(details.get("message", "Failed to update local milestone/issue plan draft.")),
            details=details,
            status=status,
        )
    result["boundary_confirmations"] = list(
        dict.fromkeys(list(result.get("boundary_confirmations", [])) + list(_BOUNDARY_CONFIRMATIONS))
    )
    return result


def post_project_factory_milestone_issue_plan_approve(config: AppConfig, body: dict[str, Any]) -> dict[str, Any]:
    requested_project_id = str(body.get("project_id", "")).strip()
    project_id = requested_project_id
    if not project_id:
        active_payload = inspect_active_project(config)
        project_id = str(active_payload.get("active_project_id", "")).strip()
        if not project_id:
            return _api_error(
                "active_project_required",
                "project_id is required when no active project is selected.",
                details={"required_fields": ["project_id"], "active_project_selected": False},
                status=400,
            )
    result = approve_project_milestone_issue_plan(config, project_id, {"approved_by": body.get("approved_by")})
    if not result.get("ok", False):
        error = str(result.get("error", "milestone_issue_plan_approval_failed"))
        details = dict(result.get("details", {}))
        status = 404 if error == "milestone_issue_plan_not_found" else 400
        return _api_error(
            error,
            str(details.get("message", "Failed to approve local milestone/issue plan.")),
            details=details,
            status=status,
        )
    result["boundary_confirmations"] = list(
        dict.fromkeys(list(result.get("boundary_confirmations", [])) + list(_BOUNDARY_CONFIRMATIONS))
    )
    return result


def get_project_factory_github_apply_plan(config: AppConfig, params: dict[str, str | None]) -> dict[str, Any]:
    requested_project_id = str(params.get("project_id", "") or "").strip()
    project_id = requested_project_id
    warnings: list[str] = []
    if not project_id:
        active_payload = inspect_active_project(config)
        project_id = str(active_payload.get("active_project_id", "")).strip()
        if not project_id:
            warnings.append("No active project selected. Approve milestone/issue plan first, then prepare GitHub apply plan.")
            return {
                "ok": True,
                "local_only": True,
                "project_id": "",
                "github_apply_plan_path": "",
                "github_apply_plan_exists": False,
                "github_apply_plan": {},
                "warnings": sorted(set(warnings + list(active_payload.get("warnings", [])))),
                "boundary_confirmations": list(
                    dict.fromkeys(
                        list(_BOUNDARY_CONFIRMATIONS) + list(active_payload.get("boundary_confirmations", []))
                    )
                ),
            }
    payload = read_project_github_apply_plan(config, project_id)
    payload["warnings"] = sorted(set(list(payload.get("warnings", [])) + warnings))
    payload["boundary_confirmations"] = list(
        dict.fromkeys(list(payload.get("boundary_confirmations", [])) + list(_BOUNDARY_CONFIRMATIONS))
    )
    return payload


def post_project_factory_github_apply_plan(config: AppConfig, body: dict[str, Any]) -> dict[str, Any]:
    requested_project_id = str(body.get("project_id", "")).strip()
    project_id = requested_project_id
    if not project_id:
        active_payload = inspect_active_project(config)
        project_id = str(active_payload.get("active_project_id", "")).strip()
        if not project_id:
            return _api_error(
                "active_project_required",
                "project_id is required when no active project is selected.",
                details={"required_fields": ["project_id"], "active_project_selected": False},
                status=400,
            )
    result = prepare_project_github_apply_plan(config, project_id)
    if not result.get("ok", False):
        error = str(result.get("error", "github_apply_plan_prepare_failed"))
        details = dict(result.get("details", {}))
        status = 404 if error == "milestone_issue_plan_not_found" else 409 if error == "milestone_issue_plan_not_approved" else 400
        return _api_error(
            error,
            str(details.get("message", "Failed to prepare local GitHub apply plan placeholder.")),
            details=details,
            status=status,
        )
    result["boundary_confirmations"] = list(
        dict.fromkeys(list(result.get("boundary_confirmations", [])) + list(_BOUNDARY_CONFIRMATIONS))
    )
    return result


def patch_project_factory_github_apply_plan(config: AppConfig, body: dict[str, Any]) -> dict[str, Any]:
    requested_project_id = str(body.get("project_id", "")).strip()
    project_id = requested_project_id
    if not project_id:
        active_payload = inspect_active_project(config)
        project_id = str(active_payload.get("active_project_id", "")).strip()
        if not project_id:
            return _api_error(
                "active_project_required",
                "project_id is required when no active project is selected.",
                details={"required_fields": ["project_id"], "active_project_selected": False},
                status=400,
            )
    editable_payload = {
        "apply_summary": body.get("apply_summary"),
        "operator_notes": body.get("operator_notes"),
        "labels": body.get("labels"),
        "dry_run_notes": body.get("dry_run_notes"),
        "preflight_checks": body.get("preflight_checks"),
        "approval_conditions": body.get("approval_conditions"),
        "known_risks": body.get("known_risks"),
    }
    result = update_project_github_apply_plan(config, project_id, editable_payload)
    if not result.get("ok", False):
        error = str(result.get("error", "github_apply_plan_update_failed"))
        details = dict(result.get("details", {}))
        status = 404 if error == "github_apply_plan_not_found" else 400
        return _api_error(
            error,
            str(details.get("message", "Failed to update local GitHub apply plan draft.")),
            details=details,
            status=status,
        )
    result["boundary_confirmations"] = list(
        dict.fromkeys(list(result.get("boundary_confirmations", [])) + list(_BOUNDARY_CONFIRMATIONS))
    )
    return result


def post_project_factory_github_apply_plan_approve(config: AppConfig, body: dict[str, Any]) -> dict[str, Any]:
    requested_project_id = str(body.get("project_id", "")).strip()
    project_id = requested_project_id
    if not project_id:
        active_payload = inspect_active_project(config)
        project_id = str(active_payload.get("active_project_id", "")).strip()
        if not project_id:
            return _api_error(
                "active_project_required",
                "project_id is required when no active project is selected.",
                details={"required_fields": ["project_id"], "active_project_selected": False},
                status=400,
            )
    result = approve_project_github_apply_plan(config, project_id, {"approved_by": body.get("approved_by")})
    if not result.get("ok", False):
        error = str(result.get("error", "github_apply_plan_approval_failed"))
        details = dict(result.get("details", {}))
        status = 404 if error == "github_apply_plan_not_found" else 400
        return _api_error(
            error,
            str(details.get("message", "Failed to approve local GitHub apply plan.")),
            details=details,
            status=status,
        )
    result["boundary_confirmations"] = list(
        dict.fromkeys(list(result.get("boundary_confirmations", [])) + list(_BOUNDARY_CONFIRMATIONS))
    )
    return result


def get_project_factory_agent_dispatch_plan(config: AppConfig, params: dict[str, str | None]) -> dict[str, Any]:
    requested_project_id = str(params.get("project_id", "") or "").strip()
    project_id = requested_project_id
    warnings: list[str] = []
    if not project_id:
        active_payload = inspect_active_project(config)
        project_id = str(active_payload.get("active_project_id", "")).strip()
        if not project_id:
            warnings.append("No active project selected. Approve local GitHub apply plan first, then prepare agent dispatch plan.")
            return {
                "ok": True,
                "local_only": True,
                "project_id": "",
                "agent_dispatch_plan_path": "",
                "agent_dispatch_plan_exists": False,
                "agent_dispatch_plan": {},
                "warnings": sorted(set(warnings + list(active_payload.get("warnings", [])))),
                "boundary_confirmations": list(
                    dict.fromkeys(
                        list(_BOUNDARY_CONFIRMATIONS) + list(active_payload.get("boundary_confirmations", []))
                    )
                ),
            }
    payload = read_project_agent_dispatch_plan(config, project_id)
    payload["warnings"] = sorted(set(list(payload.get("warnings", [])) + warnings))
    payload["boundary_confirmations"] = list(
        dict.fromkeys(list(payload.get("boundary_confirmations", [])) + list(_BOUNDARY_CONFIRMATIONS))
    )
    return payload


def post_project_factory_agent_dispatch_plan(config: AppConfig, body: dict[str, Any]) -> dict[str, Any]:
    requested_project_id = str(body.get("project_id", "")).strip()
    project_id = requested_project_id
    if not project_id:
        active_payload = inspect_active_project(config)
        project_id = str(active_payload.get("active_project_id", "")).strip()
        if not project_id:
            return _api_error(
                "active_project_required",
                "project_id is required when no active project is selected.",
                details={"required_fields": ["project_id"], "active_project_selected": False},
                status=400,
            )
    result = prepare_project_agent_dispatch_plan(config, project_id)
    if not result.get("ok", False):
        error = str(result.get("error", "agent_dispatch_plan_prepare_failed"))
        details = dict(result.get("details", {}))
        status = 404 if error == "github_apply_plan_not_found" else 409 if error == "github_apply_plan_not_approved" else 400
        return _api_error(
            error,
            str(details.get("message", "Failed to prepare local agent dispatch plan placeholder.")),
            details=details,
            status=status,
        )
    result["boundary_confirmations"] = list(
        dict.fromkeys(list(result.get("boundary_confirmations", [])) + list(_BOUNDARY_CONFIRMATIONS))
    )
    return result


def patch_project_factory_agent_dispatch_plan(config: AppConfig, body: dict[str, Any]) -> dict[str, Any]:
    requested_project_id = str(body.get("project_id", "")).strip()
    project_id = requested_project_id
    if not project_id:
        active_payload = inspect_active_project(config)
        project_id = str(active_payload.get("active_project_id", "")).strip()
        if not project_id:
            return _api_error(
                "active_project_required",
                "project_id is required when no active project is selected.",
                details={"required_fields": ["project_id"], "active_project_selected": False},
                status=400,
            )
    editable_payload = {
        "dispatch_summary": body.get("dispatch_summary"),
        "operator_notes": body.get("operator_notes"),
        "sequencing_notes": body.get("sequencing_notes"),
        "dependency_notes": body.get("dependency_notes"),
        "approval_conditions": body.get("approval_conditions"),
        "known_risks": body.get("known_risks"),
    }
    result = update_project_agent_dispatch_plan(config, project_id, editable_payload)
    if not result.get("ok", False):
        error = str(result.get("error", "agent_dispatch_plan_update_failed"))
        details = dict(result.get("details", {}))
        status = 404 if error == "agent_dispatch_plan_not_found" else 400
        return _api_error(
            error,
            str(details.get("message", "Failed to update local agent dispatch plan draft.")),
            details=details,
            status=status,
        )
    result["boundary_confirmations"] = list(
        dict.fromkeys(list(result.get("boundary_confirmations", [])) + list(_BOUNDARY_CONFIRMATIONS))
    )
    return result


def post_project_factory_agent_dispatch_plan_approve(config: AppConfig, body: dict[str, Any]) -> dict[str, Any]:
    requested_project_id = str(body.get("project_id", "")).strip()
    project_id = requested_project_id
    if not project_id:
        active_payload = inspect_active_project(config)
        project_id = str(active_payload.get("active_project_id", "")).strip()
        if not project_id:
            return _api_error(
                "active_project_required",
                "project_id is required when no active project is selected.",
                details={"required_fields": ["project_id"], "active_project_selected": False},
                status=400,
            )
    result = approve_project_agent_dispatch_plan(config, project_id, {"approved_by": body.get("approved_by")})
    if not result.get("ok", False):
        error = str(result.get("error", "agent_dispatch_plan_approval_failed"))
        details = dict(result.get("details", {}))
        status = 404 if error == "agent_dispatch_plan_not_found" else 400
        return _api_error(
            error,
            str(details.get("message", "Failed to approve local agent dispatch plan.")),
            details=details,
            status=status,
        )
    result["boundary_confirmations"] = list(
        dict.fromkeys(list(result.get("boundary_confirmations", [])) + list(_BOUNDARY_CONFIRMATIONS))
    )
    return result


def get_project_factory_validation_execution_plan(config: AppConfig, params: dict[str, str | None]) -> dict[str, Any]:
    requested_project_id = str(params.get("project_id", "") or "").strip()
    project_id = requested_project_id
    warnings: list[str] = []
    if not project_id:
        active_payload = inspect_active_project(config)
        project_id = str(active_payload.get("active_project_id", "")).strip()
        if not project_id:
            warnings.append("No active project selected. Approve local Agent Dispatch Plan first, then prepare validation execution plan.")
            return {
                "ok": True,
                "local_only": True,
                "project_id": "",
                "validation_execution_plan_path": "",
                "validation_execution_plan_exists": False,
                "validation_execution_plan": {},
                "warnings": sorted(set(warnings + list(active_payload.get("warnings", [])))),
                "boundary_confirmations": list(
                    dict.fromkeys(list(_BOUNDARY_CONFIRMATIONS) + list(active_payload.get("boundary_confirmations", [])))
                ),
            }
    payload = read_project_validation_execution_plan(config, project_id)
    payload["warnings"] = sorted(set(list(payload.get("warnings", [])) + warnings))
    payload["boundary_confirmations"] = list(dict.fromkeys(list(payload.get("boundary_confirmations", [])) + list(_BOUNDARY_CONFIRMATIONS)))
    return payload


def post_project_factory_validation_execution_plan(config: AppConfig, body: dict[str, Any]) -> dict[str, Any]:
    requested_project_id = str(body.get("project_id", "")).strip()
    project_id = requested_project_id
    if not project_id:
        active_payload = inspect_active_project(config)
        project_id = str(active_payload.get("active_project_id", "")).strip()
        if not project_id:
            return _api_error(
                "active_project_required",
                "project_id is required when no active project is selected.",
                details={"required_fields": ["project_id"], "active_project_selected": False},
                status=400,
            )
    result = prepare_project_validation_execution_plan(config, project_id)
    if not result.get("ok", False):
        error = str(result.get("error", "validation_execution_plan_prepare_failed"))
        details = dict(result.get("details", {}))
        status = 404 if error == "agent_dispatch_plan_not_found" else 409 if error == "agent_dispatch_plan_not_approved" else 400
        return _api_error(
            error,
            str(details.get("message", "Failed to prepare local validation execution plan.")),
            details=details,
            status=status,
        )
    result["boundary_confirmations"] = list(dict.fromkeys(list(result.get("boundary_confirmations", [])) + list(_BOUNDARY_CONFIRMATIONS)))
    return result


def patch_project_factory_validation_execution_plan(config: AppConfig, body: dict[str, Any]) -> dict[str, Any]:
    requested_project_id = str(body.get("project_id", "")).strip()
    project_id = requested_project_id
    if not project_id:
        active_payload = inspect_active_project(config)
        project_id = str(active_payload.get("active_project_id", "")).strip()
        if not project_id:
            return _api_error(
                "active_project_required",
                "project_id is required when no active project is selected.",
                details={"required_fields": ["project_id"], "active_project_selected": False},
                status=400,
            )
    editable_payload = {
        "validation_summary": body.get("validation_summary"),
        "operator_notes": body.get("operator_notes"),
        "sequencing_notes": body.get("sequencing_notes"),
        "dependency_notes": body.get("dependency_notes"),
        "approval_conditions": body.get("approval_conditions"),
        "known_risks": body.get("known_risks"),
        "manual_validation_notes": body.get("manual_validation_notes"),
    }
    result = update_project_validation_execution_plan(config, project_id, editable_payload)
    if not result.get("ok", False):
        error = str(result.get("error", "validation_execution_plan_update_failed"))
        details = dict(result.get("details", {}))
        status = 404 if error == "validation_execution_plan_not_found" else 400
        return _api_error(
            error,
            str(details.get("message", "Failed to update local validation execution plan draft.")),
            details=details,
            status=status,
        )
    result["boundary_confirmations"] = list(dict.fromkeys(list(result.get("boundary_confirmations", [])) + list(_BOUNDARY_CONFIRMATIONS)))
    return result


def post_project_factory_validation_execution_plan_approve(config: AppConfig, body: dict[str, Any]) -> dict[str, Any]:
    requested_project_id = str(body.get("project_id", "")).strip()
    project_id = requested_project_id
    if not project_id:
        active_payload = inspect_active_project(config)
        project_id = str(active_payload.get("active_project_id", "")).strip()
        if not project_id:
            return _api_error(
                "active_project_required",
                "project_id is required when no active project is selected.",
                details={"required_fields": ["project_id"], "active_project_selected": False},
                status=400,
            )
    result = approve_project_validation_execution_plan(config, project_id, {"approved_by": body.get("approved_by")})
    if not result.get("ok", False):
        error = str(result.get("error", "validation_execution_plan_approval_failed"))
        details = dict(result.get("details", {}))
        status = 404 if error == "validation_execution_plan_not_found" else 400
        return _api_error(
            error,
            str(details.get("message", "Failed to approve local validation execution plan.")),
            details=details,
            status=status,
        )
    result["boundary_confirmations"] = list(dict.fromkeys(list(result.get("boundary_confirmations", [])) + list(_BOUNDARY_CONFIRMATIONS)))
    return result


def get_project_factory_documentation_closeout_plan(config: AppConfig, params: dict[str, str | None]) -> dict[str, Any]:
    requested_project_id = str(params.get("project_id", "") or "").strip()
    project_id = requested_project_id
    warnings: list[str] = []
    if not project_id:
        active_payload = inspect_active_project(config)
        project_id = str(active_payload.get("active_project_id", "")).strip()
        if not project_id:
            warnings.append("No active project selected. Approve local Validation Execution Plan first, then prepare documentation closeout plan.")
            return {
                "ok": True,
                "local_only": True,
                "project_id": "",
                "documentation_closeout_plan_path": "",
                "documentation_closeout_plan_exists": False,
                "documentation_closeout_plan": {},
                "warnings": sorted(set(warnings + list(active_payload.get("warnings", [])))),
                "boundary_confirmations": list(
                    dict.fromkeys(list(_BOUNDARY_CONFIRMATIONS) + list(active_payload.get("boundary_confirmations", [])))
                ),
            }
    payload = read_project_documentation_closeout_plan(config, project_id)
    payload["warnings"] = sorted(set(list(payload.get("warnings", [])) + warnings))
    payload["boundary_confirmations"] = list(dict.fromkeys(list(payload.get("boundary_confirmations", [])) + list(_BOUNDARY_CONFIRMATIONS)))
    return payload


def post_project_factory_documentation_closeout_plan(config: AppConfig, body: dict[str, Any]) -> dict[str, Any]:
    requested_project_id = str(body.get("project_id", "")).strip()
    project_id = requested_project_id
    if not project_id:
        active_payload = inspect_active_project(config)
        project_id = str(active_payload.get("active_project_id", "")).strip()
        if not project_id:
            return _api_error(
                "active_project_required",
                "project_id is required when no active project is selected.",
                details={"required_fields": ["project_id"], "active_project_selected": False},
                status=400,
            )
    result = prepare_project_documentation_closeout_plan(config, project_id)
    if not result.get("ok", False):
        error = str(result.get("error", "documentation_closeout_plan_prepare_failed"))
        details = dict(result.get("details", {}))
        status = 404 if error == "validation_execution_plan_not_found" else 409 if error == "validation_execution_plan_not_approved" else 400
        return _api_error(
            error,
            str(details.get("message", "Failed to prepare local documentation closeout plan.")),
            details=details,
            status=status,
        )
    result["boundary_confirmations"] = list(dict.fromkeys(list(result.get("boundary_confirmations", [])) + list(_BOUNDARY_CONFIRMATIONS)))
    return result


def patch_project_factory_documentation_closeout_plan(config: AppConfig, body: dict[str, Any]) -> dict[str, Any]:
    requested_project_id = str(body.get("project_id", "")).strip()
    project_id = requested_project_id
    if not project_id:
        active_payload = inspect_active_project(config)
        project_id = str(active_payload.get("active_project_id", "")).strip()
        if not project_id:
            return _api_error(
                "active_project_required",
                "project_id is required when no active project is selected.",
                details={"required_fields": ["project_id"], "active_project_selected": False},
                status=400,
            )
    editable_payload = {
        "closeout_summary": body.get("closeout_summary"),
        "operator_notes": body.get("operator_notes"),
        "sequencing_notes": body.get("sequencing_notes"),
        "dependency_notes": body.get("dependency_notes"),
        "approval_conditions": body.get("approval_conditions"),
        "known_risks": body.get("known_risks"),
        "documentation_update_notes": body.get("documentation_update_notes"),
        "evidence_collection_notes": body.get("evidence_collection_notes"),
    }
    result = update_project_documentation_closeout_plan(config, project_id, editable_payload)
    if not result.get("ok", False):
        error = str(result.get("error", "documentation_closeout_plan_update_failed"))
        details = dict(result.get("details", {}))
        status = 404 if error == "documentation_closeout_plan_not_found" else 400
        return _api_error(
            error,
            str(details.get("message", "Failed to update local documentation closeout plan draft.")),
            details=details,
            status=status,
        )
    result["boundary_confirmations"] = list(dict.fromkeys(list(result.get("boundary_confirmations", [])) + list(_BOUNDARY_CONFIRMATIONS)))
    return result


def post_project_factory_documentation_closeout_plan_approve(config: AppConfig, body: dict[str, Any]) -> dict[str, Any]:
    requested_project_id = str(body.get("project_id", "")).strip()
    project_id = requested_project_id
    if not project_id:
        active_payload = inspect_active_project(config)
        project_id = str(active_payload.get("active_project_id", "")).strip()
        if not project_id:
            return _api_error(
                "active_project_required",
                "project_id is required when no active project is selected.",
                details={"required_fields": ["project_id"], "active_project_selected": False},
                status=400,
            )
    result = approve_project_documentation_closeout_plan(config, project_id, {"approved_by": body.get("approved_by")})
    if not result.get("ok", False):
        error = str(result.get("error", "documentation_closeout_plan_approval_failed"))
        details = dict(result.get("details", {}))
        status = 404 if error == "documentation_closeout_plan_not_found" else 400
        return _api_error(
            error,
            str(details.get("message", "Failed to approve local documentation closeout plan.")),
            details=details,
            status=status,
        )
    result["boundary_confirmations"] = list(dict.fromkeys(list(result.get("boundary_confirmations", [])) + list(_BOUNDARY_CONFIRMATIONS)))
    return result


def get_project_factory_execution_phase_approval(config: AppConfig, params: dict[str, str | None]) -> dict[str, Any]:
    requested_project_id = str(params.get("project_id", "") or "").strip()
    project_id = requested_project_id
    warnings: list[str] = []
    if not project_id:
        active_payload = inspect_active_project(config)
        project_id = str(active_payload.get("active_project_id", "")).strip()
        if not project_id:
            warnings.append("No active project selected. Approve local Documentation Closeout Plan first, then prepare execution phase approval.")
            return {
                "ok": True,
                "local_only": True,
                "project_id": "",
                "execution_phase_approval_path": "",
                "execution_phase_approval_exists": False,
                "execution_phase_approval": {},
                "warnings": sorted(set(warnings + list(active_payload.get("warnings", [])))),
                "boundary_confirmations": list(
                    dict.fromkeys(list(_BOUNDARY_CONFIRMATIONS) + list(active_payload.get("boundary_confirmations", [])))
                ),
            }
    payload = read_project_execution_phase_approval(config, project_id)
    payload["warnings"] = sorted(set(list(payload.get("warnings", [])) + warnings))
    payload["boundary_confirmations"] = list(dict.fromkeys(list(payload.get("boundary_confirmations", [])) + list(_BOUNDARY_CONFIRMATIONS)))
    return payload


def get_project_factory_execution_readiness(config: AppConfig, params: dict[str, str | None]) -> dict[str, Any]:
    requested_project_id = str(params.get("project_id", "") or "").strip()
    project_id = requested_project_id
    warnings: list[str] = []
    if not project_id:
        active_payload = inspect_active_project(config)
        project_id = str(active_payload.get("active_project_id", "")).strip()
        if not project_id:
            warnings.append("No active project selected. Select or create a project to view execution readiness.")
            return {
                "ok": True,
                "local_only": True,
                "project_id": "",
                "project_name": "",
                "active_project": False,
                "overall_status": "blocked",
                "overall_summary": "Execution readiness is blocked until a project is selected.",
                "next_safe_action": "select_or_create_active_project",
                "blockers": ["No active project is selected."],
                "warnings": sorted(set(warnings + list(active_payload.get("warnings", [])))),
                "artifact_summary": {},
                "lane_summary": {},
                "boundary_confirmations": list(
                    dict.fromkeys(list(_BOUNDARY_CONFIRMATIONS) + list(active_payload.get("boundary_confirmations", [])))
                ),
            }
    payload = read_project_execution_readiness(config, project_id)
    payload["warnings"] = sorted(set(list(payload.get("warnings", [])) + warnings))
    payload["boundary_confirmations"] = list(dict.fromkeys(list(payload.get("boundary_confirmations", [])) + list(_BOUNDARY_CONFIRMATIONS)))
    return payload


def post_project_factory_execution_phase_approval(config: AppConfig, body: dict[str, Any]) -> dict[str, Any]:
    requested_project_id = str(body.get("project_id", "")).strip()
    project_id = requested_project_id
    if not project_id:
        active_payload = inspect_active_project(config)
        project_id = str(active_payload.get("active_project_id", "")).strip()
        if not project_id:
            return _api_error(
                "active_project_required",
                "project_id is required when no active project is selected.",
                details={"required_fields": ["project_id"], "active_project_selected": False},
                status=400,
            )
    result = prepare_project_execution_phase_approval(config, project_id)
    if not result.get("ok", False):
        error = str(result.get("error", "execution_phase_approval_prepare_failed"))
        details = dict(result.get("details", {}))
        status = 404 if error == "documentation_closeout_plan_not_found" else 409 if error == "documentation_closeout_plan_not_approved" else 400
        return _api_error(
            error,
            str(details.get("message", "Failed to prepare local execution phase approval gate.")),
            details=details,
            status=status,
        )
    result["boundary_confirmations"] = list(dict.fromkeys(list(result.get("boundary_confirmations", [])) + list(_BOUNDARY_CONFIRMATIONS)))
    return result


def patch_project_factory_execution_phase_approval(config: AppConfig, body: dict[str, Any]) -> dict[str, Any]:
    requested_project_id = str(body.get("project_id", "")).strip()
    project_id = requested_project_id
    if not project_id:
        active_payload = inspect_active_project(config)
        project_id = str(active_payload.get("active_project_id", "")).strip()
        if not project_id:
            return _api_error(
                "active_project_required",
                "project_id is required when no active project is selected.",
                details={"required_fields": ["project_id"], "active_project_selected": False},
                status=400,
            )
    editable_payload = {
        "approval_summary": body.get("approval_summary"),
        "operator_notes": body.get("operator_notes"),
        "overall_acknowledgement": body.get("overall_acknowledgement"),
        "execution_lanes": body.get("execution_lanes"),
    }
    result = update_project_execution_phase_approval(config, project_id, editable_payload)
    if not result.get("ok", False):
        error = str(result.get("error", "execution_phase_approval_update_failed"))
        details = dict(result.get("details", {}))
        status = 404 if error == "execution_phase_approval_not_found" else 400
        return _api_error(
            error,
            str(details.get("message", "Failed to update local execution phase approval draft.")),
            details=details,
            status=status,
        )
    result["boundary_confirmations"] = list(dict.fromkeys(list(result.get("boundary_confirmations", [])) + list(_BOUNDARY_CONFIRMATIONS)))
    return result


def post_project_factory_execution_phase_approval_approve(config: AppConfig, body: dict[str, Any]) -> dict[str, Any]:
    requested_project_id = str(body.get("project_id", "")).strip()
    project_id = requested_project_id
    if not project_id:
        active_payload = inspect_active_project(config)
        project_id = str(active_payload.get("active_project_id", "")).strip()
        if not project_id:
            return _api_error(
                "active_project_required",
                "project_id is required when no active project is selected.",
                details={"required_fields": ["project_id"], "active_project_selected": False},
                status=400,
            )
    result = approve_project_execution_phase_approval(config, project_id, {"approved_by": body.get("approved_by")})
    if not result.get("ok", False):
        error = str(result.get("error", "execution_phase_approval_approval_failed"))
        details = dict(result.get("details", {}))
        status = 404 if error == "execution_phase_approval_not_found" else 400
        return _api_error(
            error,
            str(details.get("message", "Failed to approve local execution phase approval gate.")),
            details=details,
            status=status,
        )
    result["boundary_confirmations"] = list(dict.fromkeys(list(result.get("boundary_confirmations", [])) + list(_BOUNDARY_CONFIRMATIONS)))
    return result


def get_projects(config: AppConfig) -> dict[str, Any]:
    projects_raw, warnings, registry_path = _load_registry_if_present(config)
    projects = [_project_view(project) for project in projects_raw]
    active_payload = inspect_active_project(config)
    active_project_id = str(active_payload.get("active_project_id", "")).strip()
    for project in projects:
        project["is_active_project"] = bool(project.get("project_id") == active_project_id)
    return {
        "ok": True,
        "local_only": True,
        "registry_path": str(registry_path),
        "projects": projects,
        "project_count": len(projects),
        "active_project_id": active_project_id,
        "active_project_selected": bool(active_project_id),
        "active_project": active_payload.get("active_project"),
        "active_repo_id": active_payload.get("active_repo_id", ""),
        "active_repo": active_payload.get("active_repo"),
        "warnings": sorted(set(warnings + list(active_payload.get("warnings", [])))),
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
        primary_repo_id=body.get("primary_repo_id"),
        github_url=body.get("github_url"),
        github_owner=body.get("github_owner"),
        github_repo=body.get("github_repo"),
        github_default_branch=body.get("github_default_branch"),
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
    warnings.extend(list(result.get("warnings", [])))
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


def get_project_progress_rollup(config: AppConfig, project_id: str) -> dict[str, Any]:
    result = read_local_project_progress_rollup(config, project_id=project_id)
    if not result.get("ok", False):
        details = dict(result.get("details", {}))
        error = str(result.get("error", "project_progress_rollup_failed"))
        status = 404 if error == "managed_project_not_found" else 400
        return _api_error(
            error,
            str(details.get("message", "Failed to read local project progress rollup.")),
            details=details,
            status=status,
        )
    result["service"] = SERVICE_NAME
    result["boundary_confirmations"] = list(
        dict.fromkeys(list(result.get("boundary_confirmations", [])) + list(_BOUNDARY_CONFIRMATIONS))
    )
    return result


def get_project_ai_settings(config: AppConfig, project_id: str) -> dict[str, Any]:
    result = read_project_ai_settings(config, project_id=project_id)
    if not result.get("ok", False):
        details = dict(result.get("details", {}))
        error = str(result.get("error", "project_ai_settings_read_failed"))
        status = 404 if error == "project_factory_dossier_not_found" else 400
        return _api_error(
            error,
            str(details.get("message", "Failed to read project AI settings.")),
            details=details,
            status=status,
        )
    result["service"] = SERVICE_NAME
    result["boundary_confirmations"] = _merge_boundary_confirmations(
        result,
        "Project AI settings are local-only preferences and do not execute routing.",
    )
    return result


def get_agent_engine_registry(config: AppConfig) -> dict[str, Any]:
    result = read_agent_engine_registry(config)
    result["service"] = SERVICE_NAME
    result["supported_agent_lane_keys"] = list(AGENT_LANE_KEYS)
    result["supported_engine_keys"] = list(AI_ENGINE_KEYS)
    result["boundary_confirmations"] = _merge_boundary_confirmations(
        result,
        "Agent and engine registry is read-only and does not execute routing.",
    )
    return result


def get_local_llm_environment(config: AppConfig) -> dict[str, Any]:
    result = read_local_llm_environment_contract(config)
    result["service"] = SERVICE_NAME
    result["supported_local_llm_providers"] = list(LOCAL_LLM_PROVIDERS)
    result["boundary_confirmations"] = _merge_boundary_confirmations(
        result,
        "Local LLM environment is configuration only and does not call Ollama or execute models.",
    )
    return result


def post_local_llm_environment(config: AppConfig, body: dict[str, Any]) -> dict[str, Any]:
    provider = _normalize_optional_str(body.get("local_llm_provider"))
    if provider is not None and provider not in LOCAL_LLM_PROVIDERS:
        return _invalid_choice_error(
            field="local_llm_provider",
            value=provider,
            supported=LOCAL_LLM_PROVIDERS,
            label="local LLM provider",
        )

    for field in ("health_check_enabled", "execution_enabled", "operator_gate_required"):
        valid_bool, bool_error = _require_boolean_field(body, field)
        if not valid_bool:
            return bool_error or _api_error(f"invalid_{field}", f"{field} must be a boolean value.")

    for field in ("max_context_tokens", "request_timeout_seconds"):
        if field not in body or body.get(field) in (None, ""):
            continue
        value = body.get(field)
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            return _api_error(
                f"invalid_{field}",
                f"{field} must be a positive integer when supplied.",
                details={field: value},
            )

    allowed_fields = {
        "local_llm_provider",
        "provider_base_url",
        "reasoning_model",
        "coding_model",
        "fallback_model",
        "max_context_tokens",
        "request_timeout_seconds",
        "health_check_enabled",
        "execution_enabled",
        "operator_gate_required",
        "notes",
    }
    result = update_local_llm_environment_contract(config, payload={key: body[key] for key in allowed_fields if key in body})
    if not result.get("ok", False):
        details = dict(result.get("details", {}))
        return _api_error(
            str(result.get("error", "local_llm_environment_update_failed")),
            str(details.get("message", "Failed to update local LLM environment contract.")),
            details=details,
            status=400,
        )
    result["service"] = SERVICE_NAME
    result["supported_local_llm_providers"] = list(LOCAL_LLM_PROVIDERS)
    result["boundary_confirmations"] = _merge_boundary_confirmations(
        result,
        "Local LLM environment update stores configuration only and does not call Ollama or execute models.",
    )
    return result


def post_local_llm_health_check(config: AppConfig, body: dict[str, Any]) -> dict[str, Any]:
    if body:
        unsupported = sorted(set(body.keys()) - {"explicit_operator_invocation"})
        if unsupported:
            return _api_error(
                "unsupported_local_llm_health_check_fields",
                "Local LLM health check does not accept prompt, execution, or routing payload fields.",
                details={"unsupported_fields": unsupported},
            )
        valid_bool, bool_error = _require_boolean_field(body, "explicit_operator_invocation")
        if not valid_bool:
            return bool_error or _api_error("invalid_explicit_operator_invocation", "explicit_operator_invocation must be boolean.")
        if body.get("explicit_operator_invocation") is False:
            return _api_error(
                "local_llm_health_check_requires_explicit_operator_invocation",
                "Local LLM health check must be explicitly invoked by the operator.",
                status=409,
            )
    result = check_local_llm_health(config)
    result["service"] = SERVICE_NAME
    result["boundary_confirmations"] = _merge_boundary_confirmations(
        result,
        "Local LLM health check does not send prompts or execute inference.",
    )
    if not result.get("ok", False):
        result["_status"] = 400
    return result


def get_codex_cli_model_profiles(config: AppConfig) -> dict[str, Any]:
    result = read_codex_cli_model_profile_contract(config)
    result["service"] = SERVICE_NAME
    result["boundary_confirmations"] = _merge_boundary_confirmations(
        result,
        "Codex CLI model profiles are configuration only and do not execute Codex.",
    )
    return result


def post_codex_cli_model_profiles(config: AppConfig, body: dict[str, Any]) -> dict[str, Any]:
    if "codex_engine_key" in body and str(body.get("codex_engine_key", "")).strip() != "codex_cli":
        return _api_error(
            "invalid_codex_engine_key",
            "codex_engine_key must be codex_cli.",
            details={"codex_engine_key": body.get("codex_engine_key")},
        )
    for field in ("allowed_codex_models",):
        valid_list, list_error = _require_list_field(body, field)
        if not valid_list:
            return list_error or _api_error(f"invalid_{field}", f"{field} must be a list of strings.")
    for field in ("execution_enabled", "operator_gate_required"):
        valid_bool, bool_error = _require_boolean_field(body, field)
        if not valid_bool:
            return bool_error or _api_error(f"invalid_{field}", f"{field} must be a boolean value.")
    allowed_fields = {
        "codex_engine_key",
        "default_codex_model",
        "high_value_codex_model",
        "fast_codex_model",
        "allowed_codex_models",
        "per_project_allowed_models",
        "per_agent_allowed_models",
        "execution_enabled",
        "operator_gate_required",
        "notes",
    }
    result = update_codex_cli_model_profile_contract(config, payload={key: body[key] for key in allowed_fields if key in body})
    if not result.get("ok", False):
        details = dict(result.get("details", {}))
        return _api_error(
            str(result.get("error", "codex_cli_model_profile_update_failed")),
            str(details.get("message", "Failed to update Codex CLI model profile contract.")),
            details=details,
            status=400,
        )
    result["service"] = SERVICE_NAME
    result["boundary_confirmations"] = _merge_boundary_confirmations(
        result,
        "Codex CLI model profile update stores configuration only and does not execute Codex.",
    )
    return result


def post_project_ai_settings(config: AppConfig, project_id: str, body: dict[str, Any]) -> dict[str, Any]:
    mode = _normalize_optional_str(body.get("project_ai_mode"))
    if mode is not None and mode not in PROJECT_AI_MODES:
        return _invalid_choice_error(
            field="project_ai_mode",
            value=mode,
            supported=PROJECT_AI_MODES,
            label="project AI mode",
        )

    for field in ("available_engines", "disabled_engines"):
        valid_list, list_error = _require_list_field(body, field)
        if not valid_list:
            return list_error or _api_error(f"invalid_{field}", f"{field} must be a list of strings.")
        invalid = [engine for engine in _normalize_str_list(body.get(field, [])) if engine not in AI_ENGINE_KEYS]
        if invalid:
            return _api_error(
                f"invalid_{field}",
                f"{field} contains unsupported engine keys.",
                details={
                    field: invalid,
                    "supported_engines": list(AI_ENGINE_KEYS),
                },
            )

    default_engine = _normalize_optional_str(body.get("default_engine"))
    if default_engine is not None and default_engine not in AI_ENGINE_KEYS:
        return _invalid_choice_error(
            field="default_engine",
            value=default_engine,
            supported=AI_ENGINE_KEYS,
            label="default engine",
        )

    valid_bool, bool_error = _require_boolean_field(body, "operator_override_allowed")
    if not valid_bool:
        return bool_error or _api_error("invalid_operator_override_allowed", "operator_override_allowed must be boolean.")

    allowed_fields = {
        "project_ai_mode",
        "available_engines",
        "disabled_engines",
        "default_engine",
        "default_model",
        "operator_override_allowed",
        "notes",
    }
    result = update_project_ai_settings(config, project_id=project_id, payload={key: body[key] for key in allowed_fields if key in body})
    if not result.get("ok", False):
        details = dict(result.get("details", {}))
        error = str(result.get("error", "project_ai_settings_update_failed"))
        status = 404 if error == "project_factory_dossier_not_found" else 400
        return _api_error(
            error,
            str(details.get("message", "Failed to update project AI settings.")),
            details=details,
            status=status,
        )
    result["service"] = SERVICE_NAME
    result["boundary_confirmations"] = _merge_boundary_confirmations(
        result,
        "Project AI settings update stores preferences only and does not execute routing.",
    )
    return result


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

    valid_bool, bool_error = _require_boolean_field(body, "inspect_local_git")
    if not valid_bool:
        return bool_error or _api_error("invalid_inspect_local_git", "inspect_local_git must be a boolean value.")

    result = register_managed_repo(
        config,
        project_id=normalized_project_id,
        repo_id=repo_id,
        name=name,
        path=path,
        remote_url=body.get("remote_url"),
        default_branch=body.get("default_branch"),
        github_url=body.get("github_url"),
        github_owner=body.get("github_owner"),
        github_repo=body.get("github_repo"),
        github_default_branch=body.get("github_default_branch"),
        inspect_local_git=bool(body.get("inspect_local_git", False)),
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
        "warnings": sorted(set(result.get("warnings", []))),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }


def get_project_repo_github_link(
    config: AppConfig,
    project_id: str,
    repo_id: str,
    *,
    inspect_local_git: bool,
) -> dict[str, Any]:
    result = inspect_managed_repo_github_link(
        config,
        project_id=project_id,
        repo_id=repo_id,
        inspect_local_git=inspect_local_git,
        output_format="json",
    )
    if not result.get("ok", False):
        details = dict(result.get("details", {}))
        error = str(result.get("error", "inspect_managed_repo_github_link_failed"))
        status = 404 if error in {"managed_project_not_found", "managed_repo_not_found"} else 400
        return _api_error(
            error,
            str(details.get("message", "Failed to inspect managed repo GitHub link.")),
            details=details,
            status=status,
        )

    payload = result.get("payload", {}) if isinstance(result.get("payload"), dict) else {}
    return {
        "ok": True,
        "local_only": True,
        "project_id": str(payload.get("project_id", "")).strip(),
        "repo_id": str(payload.get("repo_id", "")).strip(),
        "github_owner": str(payload.get("github_owner", "")).strip(),
        "github_repo": str(payload.get("github_repo", "")).strip(),
        "github_url": str(payload.get("github_url", "")).strip(),
        "remote_url": str(payload.get("remote_url", "")).strip(),
        "local_git_remote_url": str(payload.get("local_git_remote_url", "")).strip(),
        "local_git_branch": str(payload.get("local_git_branch", "")).strip(),
        "local_git_head": str(payload.get("local_git_head", "")).strip(),
        "local_git_status_summary": str(payload.get("local_git_status_summary", "")).strip(),
        "github_connection_status": str(payload.get("github_connection_status", "")).strip(),
        "warnings": list(payload.get("warnings", [])),
        "boundary_confirmations": list(payload.get("boundary_confirmations", _BOUNDARY_CONFIRMATIONS)),
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


def get_local_queue_routed_views(config: AppConfig, filters: dict[str, str | None]) -> dict[str, Any]:
    include_unrouted_value = str(filters.get("include_unrouted") or "true").strip().lower()
    include_unrouted = include_unrouted_value not in {"0", "false", "no", "off"}
    result = read_local_routed_queue_views(
        config,
        project_id=_normalize_optional_str(filters.get("project_id")),
        status=_normalize_optional_str(filters.get("status")),
        recommended_agent_lane=_normalize_optional_str(filters.get("agent_lane")),
        recommended_engine=_normalize_optional_str(filters.get("engine")),
        recommended_model=_normalize_optional_str(filters.get("model")),
        fallback_engine=_normalize_optional_str(filters.get("fallback_engine")),
        risk_level=_normalize_optional_str(filters.get("risk_level")),
        complexity_level=_normalize_optional_str(filters.get("complexity_level")),
        project_ai_mode=_normalize_optional_str(filters.get("project_ai_mode")),
        routing_policy_source=_normalize_optional_str(filters.get("routing_policy_source")),
        operator_override=_normalize_optional_str(filters.get("operator_override")),
        group_by=_normalize_optional_str(filters.get("group_by")),
        include_unrouted=include_unrouted,
    )
    if not result.get("ok", False):
        details = dict(result.get("details", {}))
        return _api_error(
            str(result.get("error", "routed_queue_views_failed")),
            str(details.get("message", "Failed to read local routed queue views.")),
            details=details,
            status=400,
        )
    result["service"] = SERVICE_NAME
    result["boundary_confirmations"] = _merge_boundary_confirmations(
        result,
        "Routed queue views are read-only filters over the canonical local queue.",
    )
    return result


def get_local_queue_routing_dashboard(config: AppConfig, filters: dict[str, str | None]) -> dict[str, Any]:
    items, warnings, queue_path = _load_queue_if_present(config)
    project_id_filter = _normalize_optional_str(filters.get("project_id"))
    status_filter = _normalize_optional_str(filters.get("status"))
    repo_id_filter = _normalize_optional_str(filters.get("repo_id"))

    if status_filter and status_filter not in QUEUE_STATUSES:
        return _api_error(
            "invalid_queue_status",
            "Invalid queue status supplied.",
            details={"status": status_filter, "supported_statuses": list(QUEUE_STATUSES)},
        )

    filtered = [
        item
        for item in items
        if (not project_id_filter or item.get("project_id") == project_id_filter)
        and (not repo_id_filter or item.get("repo_id") == repo_id_filter)
        and (not status_filter or item.get("status") == status_filter)
    ]
    rows = [_routing_dashboard_row(config, item, queue_path) for item in filtered]
    confidence_available = [
        row for row in rows if isinstance(row.get("confidence_score"), (int, float)) and row.get("confidence_score") is not None
    ]
    return {
        "ok": True,
        "local_only": True,
        "read_only": True,
        "service": SERVICE_NAME,
        "contract_name": "hub_routing_dashboard_data_contract",
        "contract_version": "m90.1",
        "queue_path": str(queue_path),
        "filters": {
            "project_id": project_id_filter,
            "repo_id": repo_id_filter,
            "status": status_filter,
        },
        "item_count": len(rows),
        "confidence_score_available_count": len(confidence_available),
        "counts_by_status": _counts_by(rows, "status"),
        "counts_by_risk": _counts_by(rows, "risk"),
        "counts_by_task_size": _counts_by(rows, "task_size"),
        "counts_by_recommended_engine": _counts_by(rows, "recommended_engine"),
        "counts_by_recommended_lane": _counts_by(rows, "recommended_lane"),
        "items": rows,
        "warnings": sorted(set(warnings)),
        "safety_boundary": {
            "read_only": True,
            "mutation_endpoints_added": False,
            "prompt_execution_allowed": False,
            "local_llm_invocation_allowed": False,
            "codex_invocation_allowed": False,
            "automatic_next_item_execution_allowed": False,
            "github_api_allowed": False,
            "gh_allowed": False,
            "external_workflow_allowed": False,
        },
        "boundary_confirmations": [
            *_BOUNDARY_CONFIRMATIONS,
            "Routing dashboard data is read-only.",
            "Decision matrix inspection is advisory metadata only.",
            "No prompt execution, local LLM invocation, Codex invocation, queue mutation, or next-item execution.",
        ],
    }


def _routing_dashboard_row(config: AppConfig, item: dict[str, Any], queue_path: Path) -> dict[str, Any]:
    item_id = str(item.get("item_id", "")).strip()
    matrix = build_llm_decision_matrix(config, item_id=item_id, queue_path=queue_path)
    decision = matrix.get("routing_decision", {}) if isinstance(matrix.get("routing_decision"), dict) else {}
    risk = matrix.get("risk_classification", {}) if isinstance(matrix.get("risk_classification"), dict) else {}
    task_sizing = matrix.get("task_sizing", {}) if isinstance(matrix.get("task_sizing"), dict) else {}
    validation = matrix.get("validation_burden", {}) if isinstance(matrix.get("validation_burden"), dict) else {}
    confidence = matrix.get("routing_confidence", {}) if isinstance(matrix.get("routing_confidence"), dict) else {}
    score = confidence.get("score")
    return {
        "item_id": item_id,
        "project_id": str(item.get("project_id", "")).strip(),
        "repo_id": str(item.get("repo_id", "")).strip(),
        "title": str(item.get("title", "")).strip(),
        "status": str(item.get("status", "")).strip(),
        "item_type": str(item.get("item_type", "")).strip(),
        "priority": str(item.get("priority", "")).strip(),
        "risk": str(risk.get("risk_level", "")).strip(),
        "task_size": str(task_sizing.get("task_size", "")).strip(),
        "recommended_engine": str(decision.get("recommended_engine", "")).strip(),
        "recommended_lane": str(decision.get("recommended_lane", "")).strip(),
        "recommended_model": str(decision.get("recommended_model", "")).strip(),
        "confidence_score": score if isinstance(score, (int, float)) else None,
        "confidence_level": str(confidence.get("confidence_level", "")).strip(),
        "validation_burden": str(validation.get("validation_burden", "")).strip(),
        "warnings": list(matrix.get("warnings", [])) if isinstance(matrix.get("warnings"), list) else [],
        "blockers": list(matrix.get("blockers", [])) if isinstance(matrix.get("blockers"), list) else [],
        "execution_allowed": False,
        "prompt_dispatch_allowed": False,
        "local_llm_invocation_allowed": False,
        "codex_invocation_allowed": False,
        "automatic_next_item_execution_allowed": False,
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


def post_local_queue_item_routing_metadata(config: AppConfig, item_id: str, body: dict[str, Any]) -> dict[str, Any]:
    routing_metadata = body.get("routing_metadata", body)
    if not isinstance(routing_metadata, dict):
        return _api_error(
            "invalid_queue_routing_metadata",
            "routing_metadata must be a JSON object.",
            details={"supported_fields": [
                "recommended_agent_lane",
                "recommended_engine",
                "recommended_model",
                "fallback_engine",
                "fallback_model",
                "routing_policy_source",
                "routing_reason",
                "risk_level",
                "complexity_level",
                "escalation_reason",
                "project_ai_mode",
                "operator_override",
            ]},
        )

    agent_lane = _normalize_optional_str(routing_metadata.get("recommended_agent_lane"))
    if agent_lane is not None and agent_lane not in QUEUE_ROUTING_AGENT_LANES:
        return _invalid_choice_error(
            field="recommended_agent_lane",
            value=agent_lane,
            supported=QUEUE_ROUTING_AGENT_LANES,
            label="recommended agent lane",
        )
    for field in ("recommended_engine", "fallback_engine"):
        engine = _normalize_optional_str(routing_metadata.get(field))
        if engine is not None and engine not in QUEUE_ROUTING_ENGINES:
            return _invalid_choice_error(
                field=field,
                value=engine,
                supported=QUEUE_ROUTING_ENGINES,
                label=field,
            )
    risk_level = _normalize_optional_str(routing_metadata.get("risk_level"))
    if risk_level is not None and risk_level not in QUEUE_ROUTING_RISK_LEVELS:
        return _invalid_choice_error(
            field="risk_level",
            value=risk_level,
            supported=QUEUE_ROUTING_RISK_LEVELS,
            label="risk level",
        )
    complexity_level = _normalize_optional_str(routing_metadata.get("complexity_level"))
    if complexity_level is not None and complexity_level not in QUEUE_ROUTING_COMPLEXITY_LEVELS:
        return _invalid_choice_error(
            field="complexity_level",
            value=complexity_level,
            supported=QUEUE_ROUTING_COMPLEXITY_LEVELS,
            label="complexity level",
        )

    operator_override = routing_metadata.get("operator_override")
    if "operator_override" in routing_metadata and not isinstance(operator_override, bool) and not isinstance(operator_override, dict):
        return _api_error(
            "invalid_operator_override",
            "operator_override must be a boolean or structured JSON object.",
            details={"operator_override": operator_override},
        )

    result = update_local_queue_item_routing_metadata(
        config,
        item_id=item_id,
        routing_metadata=routing_metadata,
        queue_path=_normalize_optional_str(body.get("queue_path")),
    )
    payload = dict(result)
    payload["service"] = SERVICE_NAME
    payload["boundary_confirmations"] = _merge_boundary_confirmations(
        payload,
        "Queue routing metadata is non-executing and does not compute routing decisions.",
    )
    if not payload.get("ok", False):
        payload["_status"] = _status_for_local_queue_result(payload)
    return payload


def post_local_queue_item_routing_recommendation(config: AppConfig, item_id: str, body: dict[str, Any]) -> dict[str, Any]:
    for field in ("affected_files",):
        valid, error_payload = _require_list_field(body, field)
        if not valid:
            return error_payload or _api_error(f"invalid_{field}", f"{field} must be a list of strings.")
    valid_bool, bool_error = _require_boolean_field(body, "write_metadata")
    if not valid_bool:
        return bool_error or _api_error("invalid_write_metadata", "write_metadata must be boolean.")

    payload = dict(
        recommend_queue_item_routing(
            config,
            item_id=item_id,
            project_id=_normalize_optional_str(body.get("project_id")),
            operator_override=body.get("operator_override") if "operator_override" in body else None,
            risk_level=_normalize_optional_str(body.get("risk_level")),
            complexity_level=_normalize_optional_str(body.get("complexity_level")),
            affected_files=_normalize_optional_list(body.get("affected_files")),
            validation_burden=_normalize_optional_str(body.get("validation_burden")),
            write_metadata=bool(body.get("write_metadata", False)),
        )
    )
    payload["service"] = SERVICE_NAME
    payload["boundary_confirmations"] = _merge_boundary_confirmations(
        payload,
        "Routing recommendation is advisory and non-executing.",
    )
    if not payload.get("ok", False):
        payload["_status"] = 404 if str(payload.get("error", "")) in {"project_queue_not_found", "queue_item_not_found"} else 409
    return payload


def post_local_queue_item_apply_routing_recommendation(config: AppConfig, item_id: str, body: dict[str, Any]) -> dict[str, Any]:
    for field in ("affected_files",):
        valid, error_payload = _require_list_field(body, field)
        if not valid:
            return error_payload or _api_error(f"invalid_{field}", f"{field} must be a list of strings.")

    payload = dict(
        apply_queue_item_routing_recommendation(
            config,
            item_id=item_id,
            project_id=_normalize_optional_str(body.get("project_id")),
            operator_override=body.get("operator_override") if "operator_override" in body else None,
            risk_level=_normalize_optional_str(body.get("risk_level")),
            complexity_level=_normalize_optional_str(body.get("complexity_level")),
            affected_files=_normalize_optional_list(body.get("affected_files")),
            validation_burden=_normalize_optional_str(body.get("validation_burden")),
        )
    )
    payload["service"] = SERVICE_NAME
    payload["boundary_confirmations"] = _merge_boundary_confirmations(
        payload,
        "Applying routing recommendation writes metadata only and does not execute routing.",
    )
    if not payload.get("ok", False):
        payload["_status"] = 404 if str(payload.get("error", "")) in {"project_queue_not_found", "queue_item_not_found"} else 409
    return payload


def post_local_queue_item(config: AppConfig, body: dict[str, Any]) -> dict[str, Any]:
    title = str(body.get("title", "")).strip()
    if not title:
        return _api_error(
            "invalid_local_queue_item_payload",
            "title is required.",
            details={"required_fields": ["title"]},
        )

    priority = _normalize_optional_str(body.get("priority"))
    if priority is not None and priority not in QUEUE_PRIORITIES:
        return _invalid_choice_error(
            field="priority",
            value=priority,
            supported=QUEUE_PRIORITIES,
            label="priority",
        )

    item_type = _normalize_optional_str(body.get("item_type"))
    if item_type is not None and item_type not in QUEUE_ITEM_TYPES:
        return _invalid_choice_error(
            field="item_type",
            value=item_type,
            supported=QUEUE_ITEM_TYPES,
            label="queue item type",
        )

    for field in ("acceptance_criteria", "acceptance_notes", "validation_notes", "dependencies", "tags"):
        valid, error_payload = _require_list_field(body, field)
        if not valid:
            return error_payload or _api_error(f"invalid_{field}", f"{field} must be a list of strings.")

    queue_path = _normalize_optional_str(body.get("queue_path"))
    registry_path = _normalize_optional_str(body.get("registry_path"))

    warnings: list[str] = []
    resolved_queue_path = resolve_project_queue_path(config.repo_root, queue_path)
    if not resolved_queue_path.exists():
        init_result = init_project_queue(config, path=queue_path)
        if not init_result.get("ok", False):
            payload = dict(init_result)
            payload["boundary_confirmations"] = _merge_boundary_confirmations(payload)
            payload["_status"] = _status_for_local_queue_result(payload)
            return payload
        warnings.append("Local project queue was initialized automatically.")

    payload = dict(
        add_local_queue_item(
            config,
            title=title,
            description=_normalize_optional_str(body.get("description")),
            project_id=_normalize_optional_str(body.get("project_id")),
            repo_id=_normalize_optional_str(body.get("repo_id")),
            queue_path=queue_path,
            registry_path=registry_path,
            priority=priority,
            item_type=item_type,
            assigned_agent=_normalize_optional_str(body.get("assigned_agent")),
            source=_normalize_optional_str(body.get("source")),
            target_area=_normalize_optional_str(body.get("target_area")),
            acceptance_criteria=_normalize_optional_list(body.get("acceptance_criteria")),
            acceptance_notes=_normalize_optional_list(body.get("acceptance_notes")),
            validation_notes=_normalize_optional_list(body.get("validation_notes")),
            requested_outcome=_normalize_optional_str(body.get("requested_outcome")),
            dependencies=_normalize_optional_list(body.get("dependencies")),
            tags=_normalize_optional_list(body.get("tags")),
        )
    )
    payload["warnings"] = sorted(set(warnings + list(payload.get("warnings", []))))
    payload["boundary_confirmations"] = _merge_boundary_confirmations(
        payload,
        "Local queue item addition is local-only and uses file-backed queue state.",
    )
    if not payload.get("ok", False):
        payload["_status"] = _status_for_local_queue_result(payload)
    return payload


def get_local_queue_item_readiness(config: AppConfig, item_id: str, params: dict[str, str | None]) -> dict[str, Any]:
    payload = dict(
        inspect_local_queue_item_readiness(
            config,
            item_id=item_id.strip(),
            queue_path=_normalize_optional_str(params.get("queue_path")),
            registry_path=_normalize_optional_str(params.get("registry_path")),
        )
    )
    payload["boundary_confirmations"] = _merge_boundary_confirmations(payload)
    if not payload.get("ok", False):
        payload["_status"] = _status_for_local_queue_result(payload)
    return payload


def post_local_queue_item_local_llm_prompt_preview(config: AppConfig, item_id: str, body: dict[str, Any]) -> dict[str, Any]:
    for field in ("include_context", "include_validation_expectations", "force"):
        valid_bool, bool_error = _require_boolean_field(body, field)
        if not valid_bool:
            return bool_error or _api_error(f"invalid_{field}", f"{field} must be a boolean value.")
    payload = dict(
        generate_local_llm_prompt_preview(
            config,
            item_id=item_id.strip(),
            prompt_style=_normalize_optional_str(body.get("prompt_style")),
            include_context=bool(body.get("include_context", True)),
            include_validation_expectations=bool(body.get("include_validation_expectations", True)),
            output=_normalize_optional_str(body.get("output")),
            force=bool(body.get("force", False)),
        )
    )
    payload["service"] = SERVICE_NAME
    payload["boundary_confirmations"] = _merge_boundary_confirmations(
        payload,
        "Local LLM prompt preview is preview-only and does not call Ollama or execute inference.",
    )
    if not payload.get("ok", False):
        payload["_status"] = _status_for_local_queue_result(payload)
    return payload


def post_local_queue_item_local_llm_execute(config: AppConfig, item_id: str, body: dict[str, Any]) -> dict[str, Any]:
    for field in ("confirm_operator_gate", "use_preview", "force", "operator_override", "dry_run"):
        valid_bool, bool_error = _require_boolean_field(body, field)
        if not valid_bool:
            return bool_error or _api_error(f"invalid_{field}", f"{field} must be a boolean value.")
    payload = dict(
        execute_local_llm_for_queue_item(
            config,
            item_id=item_id.strip(),
            confirm_operator_gate=bool(body.get("confirm_operator_gate", False)),
            use_preview=bool(body.get("use_preview", True)),
            output=_normalize_optional_str(body.get("output")),
            force=bool(body.get("force", False)),
            operator_override=bool(body.get("operator_override", False)),
            dry_run=bool(body.get("dry_run", False)),
        )
    )
    payload["service"] = SERVICE_NAME
    payload["boundary_confirmations"] = _merge_boundary_confirmations(
        payload,
        "Local LLM execution is explicit, local-only, operator-gated, and advisory only.",
    )
    if not payload.get("ok", False):
        payload["_status"] = _status_for_local_queue_result(payload)
    return payload


def post_local_queue_item_start(config: AppConfig, item_id: str, body: dict[str, Any]) -> dict[str, Any]:
    payload = dict(
        start_local_queue_item(
            config,
            item_id=item_id.strip(),
            queue_path=_normalize_optional_str(body.get("queue_path")),
            registry_path=_normalize_optional_str(body.get("registry_path")),
        )
    )
    payload["boundary_confirmations"] = _merge_boundary_confirmations(payload)
    if not payload.get("ok", False):
        payload["_status"] = _status_for_local_queue_result(payload)
    return payload


def post_local_queue_item_codex_prompt(config: AppConfig, item_id: str, body: dict[str, Any]) -> dict[str, Any]:
    valid_force, force_error = _require_boolean_field(body, "force")
    if not valid_force:
        return force_error or _api_error("invalid_force", "force must be a boolean value.")

    payload = dict(
        generate_local_queue_item_codex_prompt(
            config,
            item_id=item_id.strip(),
            queue_path=_normalize_optional_str(body.get("queue_path")),
            registry_path=_normalize_optional_str(body.get("registry_path")),
            output=_normalize_optional_str(body.get("output")),
            force=bool(body.get("force", False)),
            commit_message=_normalize_optional_str(body.get("commit_message")),
        )
    )
    payload["boundary_confirmations"] = _merge_boundary_confirmations(
        payload,
        "Prompt generation writes local artifacts only and does not execute Codex.",
    )
    if not payload.get("ok", False):
        payload["_status"] = _status_for_local_queue_result(payload)
    return payload


def post_local_queue_item_codex_high_value_prompt(config: AppConfig, item_id: str, body: dict[str, Any]) -> dict[str, Any]:
    for field in (
        "include_context",
        "include_validation_expectations",
        "include_operating_rules",
        "force",
        "operator_override",
    ):
        valid_bool, bool_error = _require_boolean_field(body, field)
        if not valid_bool:
            return bool_error or _api_error(f"invalid_{field}", f"{field} must be a boolean value.")

    payload = dict(
        generate_codex_high_value_lane_prompt(
            config,
            item_id=item_id.strip(),
            include_context=bool(body.get("include_context", True)),
            include_validation_expectations=bool(body.get("include_validation_expectations", True)),
            include_operating_rules=bool(body.get("include_operating_rules", True)),
            output=_normalize_optional_str(body.get("output")),
            force=bool(body.get("force", False)),
            operator_override=bool(body.get("operator_override", False)),
            queue_path=_normalize_optional_str(body.get("queue_path")),
            registry_path=_normalize_optional_str(body.get("registry_path")),
        )
    )
    payload["service"] = SERVICE_NAME
    payload["boundary_confirmations"] = _merge_boundary_confirmations(
        payload,
        "Codex high-value lane prompt generation is preview-only and does not execute Codex, gh, GitHub, issues, PRs, or workflows.",
    )
    if not payload.get("ok", False):
        payload["_status"] = _status_for_local_queue_result(payload)
    return payload


def post_local_queue_prompt_pack(config: AppConfig, body: dict[str, Any]) -> dict[str, Any]:
    valid_force, force_error = _require_boolean_field(body, "force")
    if not valid_force:
        return force_error or _api_error("invalid_force", "force must be a boolean value.")
    valid_include_text, include_text_error = _require_boolean_field(body, "include_prompt_text")
    if not valid_include_text:
        return include_text_error or _api_error("invalid_include_prompt_text", "include_prompt_text must be a boolean value.")
    for field in ("include_routing", "group_by_routing", "include_unrouted", "recommend_missing_routing"):
        valid_bool, bool_error = _require_boolean_field(body, field)
        if not valid_bool:
            return bool_error or _api_error(f"invalid_{field}", f"{field} must be a boolean value.")

    for field in ("item_ids", "statuses"):
        valid, error_payload = _require_list_field(body, field)
        if not valid:
            return error_payload or _api_error(f"invalid_{field}", f"{field} must be a list of strings.")

    payload = dict(
        generate_local_queue_prompt_pack(
            config,
            item_ids=_normalize_optional_list(body.get("item_ids")),
            statuses=_normalize_optional_list(body.get("statuses")),
            queue_path=_normalize_optional_str(body.get("queue_path")),
            registry_path=_normalize_optional_str(body.get("registry_path")),
            output=_normalize_optional_str(body.get("output")),
            force=bool(body.get("force", False)),
            include_routing=bool(body.get("include_routing", True)),
            group_by_routing=bool(body.get("group_by_routing", False)),
            routing_group_by=_normalize_optional_str(body.get("routing_group_by")),
            include_unrouted=bool(body.get("include_unrouted", True)),
            recommend_missing_routing=bool(body.get("recommend_missing_routing", False)),
        )
    )
    if not bool(body.get("include_prompt_text", True)):
        payload.pop("prompt_pack", None)
    payload["boundary_confirmations"] = _merge_boundary_confirmations(
        payload,
        "Prompt pack generation writes local artifacts only and does not execute Codex, local LLMs, agents, prompts, GitHub, or workflows.",
    )
    if not payload.get("ok", False):
        payload["_status"] = _status_for_local_queue_result(payload)
    return payload


def post_local_queue_item_complete(config: AppConfig, item_id: str, body: dict[str, Any]) -> dict[str, Any]:
    for field in ("tests_run", "changed_files", "artifact_paths"):
        valid, error_payload = _require_list_field(body, field)
        if not valid:
            return error_payload or _api_error(f"invalid_{field}", f"{field} must be a list of strings.")

    payload = dict(
        complete_local_queue_item(
            config,
            item_id=item_id.strip(),
            commit_hash=str(body.get("commit_hash", "")).strip(),
            validation_summary=str(body.get("validation_summary", "")).strip(),
            evidence_note=_normalize_optional_str(body.get("evidence_note")),
            tests_run=_normalize_optional_list(body.get("tests_run")),
            changed_files=_normalize_optional_list(body.get("changed_files")),
            artifact_paths=_normalize_optional_list(body.get("artifact_paths")),
            completed_by=str(body.get("completed_by", "local_operator")).strip() or "local_operator",
            queue_path=_normalize_optional_str(body.get("queue_path")),
        )
    )
    payload["boundary_confirmations"] = _merge_boundary_confirmations(payload)
    if not payload.get("ok", False):
        payload["_status"] = _status_for_local_queue_result(payload)
    return payload


def post_local_queue_item_evidence(config: AppConfig, item_id: str, body: dict[str, Any]) -> dict[str, Any]:
    for field in ("validation_commands", "validation_results", "smoke_checks", "files_changed", "review_evidence"):
        valid, error_payload = _require_list_field(body, field)
        if not valid:
            return error_payload or _api_error(f"invalid_{field}", f"{field} must be a list of strings.")

    payload = dict(
        capture_local_queue_completion_evidence(
            config,
            item_id=item_id.strip(),
            evidence_summary=_normalize_optional_str(body.get("evidence_summary")),
            validation_commands=_normalize_optional_list(body.get("validation_commands")),
            validation_results=_normalize_optional_list(body.get("validation_results")),
            smoke_checks=_normalize_optional_list(body.get("smoke_checks")),
            diff_check_result=_normalize_optional_str(body.get("diff_check_result")),
            files_changed=_normalize_optional_list(body.get("files_changed")),
            commit_hash=_normalize_optional_str(body.get("commit_hash")),
            push_result=_normalize_optional_str(body.get("push_result")),
            review_evidence=_normalize_optional_list(body.get("review_evidence")),
            operator_notes=_normalize_optional_str(body.get("operator_notes")),
            queue_path=_normalize_optional_str(body.get("queue_path")),
        )
    )
    payload["boundary_confirmations"] = _merge_boundary_confirmations(
        payload,
        "Evidence capture records local queue metadata only and does not complete the item.",
    )
    if not payload.get("ok", False):
        payload["_status"] = _status_for_local_queue_result(payload)
    return payload


def post_local_queue_item_closeout(config: AppConfig, item_id: str, body: dict[str, Any]) -> dict[str, Any]:
    payload = dict(
        close_local_queue_item(
            config,
            item_id=item_id.strip(),
            closeout_summary=str(body.get("closeout_summary", "")).strip(),
            closed_by=str(body.get("closed_by", "local_operator")).strip() or "local_operator",
            queue_path=_normalize_optional_str(body.get("queue_path")),
        )
    )
    payload["boundary_confirmations"] = _merge_boundary_confirmations(
        payload,
        "Closeout updates local queue state only and does not execute external actions.",
    )
    if not payload.get("ok", False):
        payload["_status"] = _status_for_local_queue_result(payload)
    return payload


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


def post_local_project_handoff(config: AppConfig, body: dict[str, Any]) -> dict[str, Any]:
    for field in ("include_queue", "include_reports", "include_evidence", "force"):
        valid_bool, bool_error = _require_boolean_field(body, field)
        if not valid_bool:
            return bool_error or _api_error(f"invalid_{field}", f"{field} must be a boolean value.")

    payload = dict(
        generate_local_project_handoff(
            config,
            project_id=_normalize_optional_str(body.get("project_id")),
            include_queue=bool(body.get("include_queue", True)),
            include_reports=bool(body.get("include_reports", True)),
            include_evidence=bool(body.get("include_evidence", True)),
            next_milestone=_normalize_optional_str(body.get("next_milestone")),
            next_instruction=_normalize_optional_str(body.get("next_instruction")),
            output=_normalize_optional_str(body.get("output")),
            force=bool(body.get("force", False)),
            latest_commit=_normalize_optional_str(body.get("latest_commit")),
        )
    )
    payload["service"] = SERVICE_NAME
    payload["boundary_confirmations"] = _merge_boundary_confirmations(
        payload,
        "Local project handoff generation does not execute agents, Codex, local LLMs, routing, GitHub, or gh.",
    )
    if not payload.get("ok", False):
        payload["_status"] = 409 if "already exists" in " ".join(payload.get("warnings", [])) else 400
    return payload


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
        "active_project_path": str(inspect_active_project(config).get("active_project_path", "")),
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
            "GitHub links are stored locally; no live validation is performed.",
            "No GitHub APIs, gh, GraphQL, REST, network services, or external API calls.",
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
        "m41_boundary_confirmations": [
            "M41 GitHub link metadata is local-only and file-backed.",
            "M41 uses local git inspection only when requested.",
            "M41 does not call GitHub APIs, gh, GraphQL, REST, or network services.",
            "M41 does not perform live GitHub validation.",
        ],
    }
    prepare_project_agent_dispatch_plan,
    read_project_agent_dispatch_plan,
    update_project_agent_dispatch_plan,
