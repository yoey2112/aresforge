from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.local_active_project import inspect_active_project, set_active_project
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
PROJECT_AI_MODES: tuple[str, ...] = (
    "balanced",
    "local_only",
    "codex_only",
    "cost_saver",
    "high_confidence",
    "manual_only",
)
AI_ENGINE_KEYS: tuple[str, ...] = (
    "local_reasoning_llm",
    "local_coding_llm",
    "codex_cli",
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
_SCOPE_EDITABLE_LIST_FIELDS: tuple[str, ...] = (
    "requirements",
    "constraints",
    "assumptions",
    "acceptance_criteria",
    "risks",
    "out_of_scope",
    "stakeholders",
)
_ARCHITECTURE_EDITABLE_LIST_FIELDS: tuple[str, ...] = (
    "system_components",
    "data_model_notes",
    "integration_points",
    "security_considerations",
    "deployment_notes",
    "testing_strategy",
    "documentation_plan",
    "open_questions",
)
_MILESTONE_ISSUE_TYPES: tuple[str, ...] = (
    "task",
    "feature",
    "bug",
    "documentation",
    "validation",
    "architecture",
    "infrastructure",
)
_MILESTONE_ISSUE_PRIORITIES: tuple[str, ...] = ("low", "normal", "high", "urgent")
_MILESTONE_ISSUE_AGENT_TYPES: tuple[str, ...] = (
    "architect",
    "backend",
    "frontend",
    "test",
    "docs",
    "validation",
    "release",
    "operator",
)
_EXECUTION_READINESS_ARTIFACTS: tuple[tuple[str, str], ...] = (
    ("factory_dossier", "factory_dossier"),
    ("scope_package", "scope_package"),
    ("architecture_contract", "architecture_contract"),
    ("milestone_issue_plan", "milestone_issue_plan"),
    ("github_apply_plan", "github_apply_plan"),
    ("agent_dispatch_plan", "agent_dispatch_plan"),
    ("validation_execution_plan", "validation_execution_plan"),
    ("documentation_closeout_plan", "documentation_closeout_plan"),
    ("execution_phase_approval", "execution_phase_approval"),
)
_EXECUTION_READINESS_LANES: tuple[str, ...] = (
    "github_mutation_execution",
    "validation_command_execution",
    "documentation_update_execution",
    "agent_model_execution",
    "project_closeout_execution",
)


def resolve_project_factory_dossier_path(repo_root: Path, project_id: str) -> Path:
    return (repo_root / ".aresforge" / "projects" / project_id.strip() / "factory_dossier.json").resolve()


def resolve_project_scope_package_path(repo_root: Path, project_id: str) -> Path:
    return (repo_root / ".aresforge" / "projects" / project_id.strip() / "scope_package.json").resolve()


def resolve_project_architecture_contract_path(repo_root: Path, project_id: str) -> Path:
    return (repo_root / ".aresforge" / "projects" / project_id.strip() / "architecture_contract.json").resolve()


def resolve_project_milestone_issue_plan_path(repo_root: Path, project_id: str) -> Path:
    return (repo_root / ".aresforge" / "projects" / project_id.strip() / "milestone_issue_plan.json").resolve()


def resolve_project_github_apply_plan_path(repo_root: Path, project_id: str) -> Path:
    return (repo_root / ".aresforge" / "projects" / project_id.strip() / "github_apply_plan.json").resolve()


def resolve_project_agent_dispatch_plan_path(repo_root: Path, project_id: str) -> Path:
    return (repo_root / ".aresforge" / "projects" / project_id.strip() / "agent_dispatch_plan.json").resolve()


def resolve_project_validation_execution_plan_path(repo_root: Path, project_id: str) -> Path:
    return (repo_root / ".aresforge" / "projects" / project_id.strip() / "validation_execution_plan.json").resolve()


def resolve_project_documentation_closeout_plan_path(repo_root: Path, project_id: str) -> Path:
    return (repo_root / ".aresforge" / "projects" / project_id.strip() / "documentation_closeout_plan.json").resolve()


def resolve_project_execution_phase_approval_path(repo_root: Path, project_id: str) -> Path:
    return (repo_root / ".aresforge" / "projects" / project_id.strip() / "execution_phase_approval.json").resolve()


def resolve_project_ai_settings_path(repo_root: Path, project_id: str) -> Path:
    return (repo_root / ".aresforge" / "projects" / project_id.strip() / "ai_settings.json").resolve()


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
    scope_lifecycle_state = ""
    scope_payload = read_project_scope_package(config, project_id)
    if scope_payload.get("scope_package_exists", False):
        scope_package = scope_payload.get("scope_package", {})
        if isinstance(scope_package, dict):
            scope_lifecycle_state = str(scope_package.get("lifecycle_state", "")).strip()
    architecture_lifecycle_state = ""
    architecture_payload = read_project_architecture_contract(config, project_id)
    if architecture_payload.get("architecture_contract_exists", False):
        architecture_contract = architecture_payload.get("architecture_contract", {})
        if isinstance(architecture_contract, dict):
            architecture_lifecycle_state = str(architecture_contract.get("lifecycle_state", "")).strip()
    effective_lifecycle_state = lifecycle_state
    if scope_lifecycle_state == "scope_approved" and lifecycle_state != "scope_approved":
        effective_lifecycle_state = "scope_approved"
    if architecture_lifecycle_state in {
        "architecture_contract_prepared",
        "architecture_draft_updated",
        "architecture_approved",
    }:
        effective_lifecycle_state = architecture_lifecycle_state
    milestone_issue_plan_payload = read_project_milestone_issue_plan(config, project_id)
    milestone_issue_plan_lifecycle_state = ""
    if milestone_issue_plan_payload.get("milestone_issue_plan_exists", False):
        milestone_issue_plan = milestone_issue_plan_payload.get("milestone_issue_plan", {})
        if isinstance(milestone_issue_plan, dict):
            milestone_issue_plan_lifecycle_state = str(milestone_issue_plan.get("lifecycle_state", "")).strip()
    if milestone_issue_plan_lifecycle_state in {
        "milestone_issue_plan_prepared",
        "milestone_issue_plan_draft_updated",
        "milestone_issue_plan_approved",
    }:
        effective_lifecycle_state = milestone_issue_plan_lifecycle_state
    github_apply_plan_payload = read_project_github_apply_plan(config, project_id)
    github_apply_plan_lifecycle_state = ""
    if github_apply_plan_payload.get("github_apply_plan_exists", False):
        github_apply_plan = github_apply_plan_payload.get("github_apply_plan", {})
        if isinstance(github_apply_plan, dict):
            github_apply_plan_lifecycle_state = str(github_apply_plan.get("lifecycle_state", "")).strip()
    if github_apply_plan_lifecycle_state in {
        "github_apply_plan_prepared",
        "github_apply_plan_draft_updated",
        "github_apply_plan_approved",
    }:
        effective_lifecycle_state = github_apply_plan_lifecycle_state
    agent_dispatch_plan_payload = read_project_agent_dispatch_plan(config, project_id)
    agent_dispatch_plan_lifecycle_state = ""
    if agent_dispatch_plan_payload.get("agent_dispatch_plan_exists", False):
        agent_dispatch_plan = agent_dispatch_plan_payload.get("agent_dispatch_plan", {})
        if isinstance(agent_dispatch_plan, dict):
            agent_dispatch_plan_lifecycle_state = str(agent_dispatch_plan.get("lifecycle_state", "")).strip()
    if agent_dispatch_plan_lifecycle_state in {
        "agent_dispatch_plan_prepared",
        "agent_dispatch_plan_draft_updated",
        "agent_dispatch_plan_approved",
    }:
        effective_lifecycle_state = agent_dispatch_plan_lifecycle_state
    validation_execution_plan_payload = read_project_validation_execution_plan(config, project_id)
    validation_execution_plan_lifecycle_state = ""
    if validation_execution_plan_payload.get("validation_execution_plan_exists", False):
        validation_execution_plan = validation_execution_plan_payload.get("validation_execution_plan", {})
        if isinstance(validation_execution_plan, dict):
            validation_execution_plan_lifecycle_state = str(validation_execution_plan.get("lifecycle_state", "")).strip()
    if validation_execution_plan_lifecycle_state in {
        "validation_execution_plan_prepared",
        "validation_execution_plan_draft_updated",
        "validation_execution_plan_approved",
    }:
        effective_lifecycle_state = validation_execution_plan_lifecycle_state
    documentation_closeout_plan_payload = read_project_documentation_closeout_plan(config, project_id)
    documentation_closeout_plan_lifecycle_state = ""
    if documentation_closeout_plan_payload.get("documentation_closeout_plan_exists", False):
        documentation_closeout_plan = documentation_closeout_plan_payload.get("documentation_closeout_plan", {})
        if isinstance(documentation_closeout_plan, dict):
            documentation_closeout_plan_lifecycle_state = str(documentation_closeout_plan.get("lifecycle_state", "")).strip()
    if documentation_closeout_plan_lifecycle_state in {
        "documentation_closeout_plan_prepared",
        "documentation_closeout_plan_draft_updated",
        "documentation_closeout_plan_approved",
    }:
        effective_lifecycle_state = documentation_closeout_plan_lifecycle_state
    execution_phase_approval_payload = read_project_execution_phase_approval(config, project_id)
    execution_phase_approval_lifecycle_state = ""
    if execution_phase_approval_payload.get("execution_phase_approval_exists", False):
        execution_phase_approval = execution_phase_approval_payload.get("execution_phase_approval", {})
        if isinstance(execution_phase_approval, dict):
            execution_phase_approval_lifecycle_state = str(execution_phase_approval.get("lifecycle_state", "")).strip()
    if execution_phase_approval_lifecycle_state in {
        "execution_phase_approval_prepared",
        "execution_phase_approval_draft_updated",
        "execution_phase_approval_approved",
    }:
        effective_lifecycle_state = execution_phase_approval_lifecycle_state
    payload["workflow_steps"] = _build_workflow_steps(
        lifecycle_state=effective_lifecycle_state,
        github_mode=github_mode,
    )
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
        "requirements": [],
        "constraints": [],
        "assumptions": [],
        "acceptance_criteria": [],
        "risks": [],
        "out_of_scope": [],
        "stakeholders": [],
        "notes": "",
        "model_execution_status": "not_requested",
        "github_mutation_status": "not_requested",
        "next_recommended_action": "approve_scope_generation_or_edit_scope_locally",
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
        "audit_trail": [],
    }
    _append_scope_audit_entry(
        scope_package,
        event_type="scope_package_prepared",
        lifecycle_state="scope_package_prepared",
        summary="Scope package prepared locally from project factory dossier.",
    )
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


def read_project_scope_package(config: AppConfig, project_id: str) -> dict[str, Any]:
    normalized_project_id = str(project_id or "").strip()
    scope_path = resolve_project_scope_package_path(config.repo_root, normalized_project_id)
    warnings: list[str] = []
    if not scope_path.exists():
        warnings.append(f"Scope package not found for project: {normalized_project_id}")
        return {
            "ok": True,
            "local_only": True,
            "project_id": normalized_project_id,
            "scope_package_path": str(scope_path),
            "scope_package_exists": False,
            "scope_package": {},
            "warnings": warnings,
            "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
        }

    try:
        loaded = json.loads(scope_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        warnings.append(f"Scope package could not be parsed: {exc}")
        loaded = {}

    if not isinstance(loaded, dict):
        warnings.append("Scope package has invalid schema; expected JSON object.")
        loaded = {}

    return {
        "ok": True,
        "local_only": True,
        "project_id": normalized_project_id,
        "scope_package_path": str(scope_path),
        "scope_package_exists": bool(loaded),
        "scope_package": loaded,
        "warnings": sorted(set(warnings)),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }


def update_project_scope_package(config: AppConfig, project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    scope_result = read_project_scope_package(config, project_id)
    normalized_project_id = str(scope_result.get("project_id", "")).strip()
    if not scope_result.get("scope_package_exists", False):
        return _error(
            "scope_package_not_found",
            {
                "message": "Scope package must be prepared before updating scope draft fields.",
                "project_id": normalized_project_id,
                "scope_package_path": scope_result.get("scope_package_path", ""),
            },
        )

    scope_package = dict(scope_result.get("scope_package", {}))
    now = _now_iso()
    for field in _SCOPE_EDITABLE_LIST_FIELDS:
        if field in payload:
            scope_package[field] = _normalize_text_list(payload.get(field))
    if "notes" in payload:
        scope_package["notes"] = str(payload.get("notes", "")).strip()

    scope_package["lifecycle_state"] = "scope_draft_updated"
    scope_package["updated_at"] = now
    scope_package["model_execution_status"] = "not_requested"
    scope_package["github_mutation_status"] = "not_requested"
    scope_package["next_recommended_action"] = "approve_scope_or_continue_editing"
    _append_scope_audit_entry(
        scope_package,
        event_type="scope_draft_updated",
        lifecycle_state="scope_draft_updated",
        summary="Scope draft fields were updated locally.",
    )

    scope_path = resolve_project_scope_package_path(config.repo_root, normalized_project_id)
    scope_path.write_text(json.dumps(scope_package, indent=2) + "\n", encoding="utf-8")

    dossier_result = read_project_factory_dossier(config, normalized_project_id)
    dossier = dict(dossier_result.get("dossier", {})) if dossier_result.get("dossier_exists", False) else {}
    if dossier:
        dossier["lifecycle_state"] = "scope_draft_updated"
        dossier["next_recommended_action"] = "approve_scope_or_continue_editing"
        dossier["updated_at"] = now
        create_project_factory_dossier(config, dossier)

    return {
        "ok": True,
        "local_only": True,
        "project_id": normalized_project_id,
        "scope_package": scope_package,
        "scope_package_path": str(scope_path),
        "dossier_path": str(resolve_project_factory_dossier_path(config.repo_root, normalized_project_id)),
        "warnings": sorted(set(scope_result.get("warnings", []))),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }


def approve_project_scope_package(config: AppConfig, project_id: str, approval_payload: dict[str, Any]) -> dict[str, Any]:
    scope_result = read_project_scope_package(config, project_id)
    normalized_project_id = str(scope_result.get("project_id", "")).strip()
    if not scope_result.get("scope_package_exists", False):
        return _error(
            "scope_package_not_found",
            {
                "message": "Scope package must be prepared before approval.",
                "project_id": normalized_project_id,
                "scope_package_path": scope_result.get("scope_package_path", ""),
            },
        )

    scope_package = dict(scope_result.get("scope_package", {}))
    requirements = _normalize_text_list(scope_package.get("requirements"))
    acceptance_criteria = _normalize_text_list(scope_package.get("acceptance_criteria"))
    if not requirements:
        return _error(
            "scope_approval_validation_failed",
            {"message": "Scope approval requires at least one requirement."},
        )
    if not acceptance_criteria:
        return _error(
            "scope_approval_validation_failed",
            {"message": "Scope approval requires at least one acceptance criterion."},
        )

    now = _now_iso()
    scope_package["requirements"] = requirements
    scope_package["acceptance_criteria"] = acceptance_criteria
    scope_package["lifecycle_state"] = "scope_approved"
    scope_package["scope_status"] = "approved"
    scope_package["updated_at"] = now
    scope_package["approved_at"] = now
    scope_package["approved_by"] = str(approval_payload.get("approved_by", "")).strip() or "local_operator"
    scope_package["model_execution_status"] = "not_requested"
    scope_package["github_mutation_status"] = "not_requested"
    scope_package["next_recommended_action"] = "prepare_architecture_contract"
    _append_scope_audit_entry(
        scope_package,
        event_type="scope_approved",
        lifecycle_state="scope_approved",
        summary="Scope package approved locally and ready for architecture contract preparation.",
    )

    scope_path = resolve_project_scope_package_path(config.repo_root, normalized_project_id)
    scope_path.write_text(json.dumps(scope_package, indent=2) + "\n", encoding="utf-8")

    dossier_result = read_project_factory_dossier(config, normalized_project_id)
    dossier = dict(dossier_result.get("dossier", {})) if dossier_result.get("dossier_exists", False) else {}
    if dossier:
        dossier["lifecycle_state"] = "scope_approved"
        dossier["next_recommended_action"] = "prepare_architecture_contract"
        dossier["updated_at"] = now
        create_project_factory_dossier(config, dossier)

    return {
        "ok": True,
        "local_only": True,
        "project_id": normalized_project_id,
        "scope_package": scope_package,
        "scope_package_path": str(scope_path),
        "dossier_path": str(resolve_project_factory_dossier_path(config.repo_root, normalized_project_id)),
        "warnings": sorted(set(scope_result.get("warnings", []))),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }


def read_project_architecture_contract(config: AppConfig, project_id: str) -> dict[str, Any]:
    normalized_project_id = str(project_id or "").strip()
    architecture_path = resolve_project_architecture_contract_path(config.repo_root, normalized_project_id)
    warnings: list[str] = []
    if not architecture_path.exists():
        warnings.append(f"Architecture contract not found for project: {normalized_project_id}")
        return {
            "ok": True,
            "local_only": True,
            "project_id": normalized_project_id,
            "architecture_contract_path": str(architecture_path),
            "architecture_contract_exists": False,
            "architecture_contract": {},
            "warnings": warnings,
            "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
        }

    try:
        loaded = json.loads(architecture_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        warnings.append(f"Architecture contract could not be parsed: {exc}")
        loaded = {}

    if not isinstance(loaded, dict):
        warnings.append("Architecture contract has invalid schema; expected JSON object.")
        loaded = {}

    return {
        "ok": True,
        "local_only": True,
        "project_id": normalized_project_id,
        "architecture_contract_path": str(architecture_path),
        "architecture_contract_exists": bool(loaded),
        "architecture_contract": loaded,
        "warnings": sorted(set(warnings)),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }


def prepare_project_architecture_contract(config: AppConfig, project_id: str) -> dict[str, Any]:
    normalized_project_id = str(project_id or "").strip()
    scope_result = read_project_scope_package(config, normalized_project_id)
    if not scope_result.get("scope_package_exists", False):
        return _error(
            "scope_package_not_found",
            {
                "message": "Scope package must exist before preparing architecture contract.",
                "project_id": normalized_project_id,
                "scope_package_path": scope_result.get("scope_package_path", ""),
            },
        )
    scope_package = dict(scope_result.get("scope_package", {}))
    if str(scope_package.get("lifecycle_state", "")).strip() != "scope_approved":
        return _error(
            "scope_not_approved",
            {
                "message": "Scope must be approved before preparing architecture contract.",
                "project_id": normalized_project_id,
            },
        )

    now = _now_iso()
    architecture_path = resolve_project_architecture_contract_path(config.repo_root, normalized_project_id)
    architecture_path.parent.mkdir(parents=True, exist_ok=True)
    existing_created_at = ""
    if architecture_path.exists():
        try:
            existing_raw = json.loads(architecture_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            existing_raw = {}
        if isinstance(existing_raw, dict):
            existing_created_at = str(existing_raw.get("created_at", "")).strip()

    architecture_contract = {
        "schema_version": "1.0",
        "project_id": normalized_project_id,
        "created_at": existing_created_at or now,
        "updated_at": now,
        "lifecycle_state": "architecture_contract_prepared",
        "source": "local_project_factory",
        "input": {
            "approved_scope_summary": str(scope_package.get("notes", "")).strip(),
            "requirements": _normalize_text_list(scope_package.get("requirements")),
            "constraints": _normalize_text_list(scope_package.get("constraints")),
            "assumptions": _normalize_text_list(scope_package.get("assumptions")),
            "acceptance_criteria": _normalize_text_list(scope_package.get("acceptance_criteria")),
            "risks": _normalize_text_list(scope_package.get("risks")),
            "out_of_scope": _normalize_text_list(scope_package.get("out_of_scope")),
            "stakeholders": _normalize_text_list(scope_package.get("stakeholders")),
            "preferred_stack": str(scope_package.get("input", {}).get("preferred_stack", "")).strip()
            if isinstance(scope_package.get("input"), dict)
            else "",
            "project_type": str(scope_package.get("input", {}).get("project_type", "")).strip()
            if isinstance(scope_package.get("input"), dict)
            else "",
        },
        "architecture_summary": "",
        "system_components": [],
        "data_model_notes": [],
        "integration_points": [],
        "security_considerations": [],
        "deployment_notes": [],
        "testing_strategy": [],
        "documentation_plan": [],
        "open_questions": [],
        "milestone_planning_notes": "",
        "model_execution_status": "not_requested",
        "github_mutation_status": "not_requested",
        "next_recommended_action": "edit_architecture_contract",
        "audit_trail": [],
    }
    _append_architecture_audit_entry(
        architecture_contract,
        event_type="architecture_contract_prepared",
        lifecycle_state="architecture_contract_prepared",
        summary="Architecture contract prepared locally from approved scope package.",
    )
    architecture_path.write_text(json.dumps(architecture_contract, indent=2) + "\n", encoding="utf-8")

    dossier_result = read_project_factory_dossier(config, normalized_project_id)
    dossier = dict(dossier_result.get("dossier", {})) if dossier_result.get("dossier_exists", False) else {}
    if dossier:
        dossier["lifecycle_state"] = "architecture_contract_prepared"
        dossier["next_recommended_action"] = "edit_architecture_contract"
        dossier["updated_at"] = now
        create_project_factory_dossier(config, dossier)

    return {
        "ok": True,
        "local_only": True,
        "project_id": normalized_project_id,
        "architecture_contract": architecture_contract,
        "architecture_contract_path": str(architecture_path),
        "dossier_path": str(resolve_project_factory_dossier_path(config.repo_root, normalized_project_id)),
        "warnings": sorted(set(scope_result.get("warnings", []))),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }


def update_project_architecture_contract(config: AppConfig, project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    architecture_result = read_project_architecture_contract(config, project_id)
    normalized_project_id = str(architecture_result.get("project_id", "")).strip()
    if not architecture_result.get("architecture_contract_exists", False):
        return _error(
            "architecture_contract_not_found",
            {
                "message": "Architecture contract must be prepared before updating draft fields.",
                "project_id": normalized_project_id,
                "architecture_contract_path": architecture_result.get("architecture_contract_path", ""),
            },
        )

    architecture_contract = dict(architecture_result.get("architecture_contract", {}))
    now = _now_iso()
    if "architecture_summary" in payload:
        architecture_contract["architecture_summary"] = str(payload.get("architecture_summary", "")).strip()
    for field in _ARCHITECTURE_EDITABLE_LIST_FIELDS:
        if field in payload:
            architecture_contract[field] = _normalize_text_list(payload.get(field))
    if "milestone_planning_notes" in payload:
        architecture_contract["milestone_planning_notes"] = str(payload.get("milestone_planning_notes", "")).strip()

    architecture_contract["lifecycle_state"] = "architecture_draft_updated"
    architecture_contract["updated_at"] = now
    architecture_contract["model_execution_status"] = "not_requested"
    architecture_contract["github_mutation_status"] = "not_requested"
    architecture_contract["next_recommended_action"] = "approve_architecture_or_continue_editing"
    _append_architecture_audit_entry(
        architecture_contract,
        event_type="architecture_draft_updated",
        lifecycle_state="architecture_draft_updated",
        summary="Architecture draft fields were updated locally.",
    )

    architecture_path = resolve_project_architecture_contract_path(config.repo_root, normalized_project_id)
    architecture_path.write_text(json.dumps(architecture_contract, indent=2) + "\n", encoding="utf-8")

    dossier_result = read_project_factory_dossier(config, normalized_project_id)
    dossier = dict(dossier_result.get("dossier", {})) if dossier_result.get("dossier_exists", False) else {}
    if dossier:
        dossier["lifecycle_state"] = "architecture_draft_updated"
        dossier["next_recommended_action"] = "approve_architecture_or_continue_editing"
        dossier["updated_at"] = now
        create_project_factory_dossier(config, dossier)

    return {
        "ok": True,
        "local_only": True,
        "project_id": normalized_project_id,
        "architecture_contract": architecture_contract,
        "architecture_contract_path": str(architecture_path),
        "dossier_path": str(resolve_project_factory_dossier_path(config.repo_root, normalized_project_id)),
        "warnings": sorted(set(architecture_result.get("warnings", []))),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }


def approve_project_architecture_contract(config: AppConfig, project_id: str, approval_payload: dict[str, Any]) -> dict[str, Any]:
    architecture_result = read_project_architecture_contract(config, project_id)
    normalized_project_id = str(architecture_result.get("project_id", "")).strip()
    if not architecture_result.get("architecture_contract_exists", False):
        return _error(
            "architecture_contract_not_found",
            {
                "message": "Architecture contract must be prepared before approval.",
                "project_id": normalized_project_id,
                "architecture_contract_path": architecture_result.get("architecture_contract_path", ""),
            },
        )

    architecture_contract = dict(architecture_result.get("architecture_contract", {}))
    architecture_summary = str(architecture_contract.get("architecture_summary", "")).strip()
    system_components = _normalize_text_list(architecture_contract.get("system_components"))
    testing_strategy = _normalize_text_list(architecture_contract.get("testing_strategy"))
    if not architecture_summary:
        return _error(
            "architecture_approval_validation_failed",
            {"message": "Architecture approval requires a non-empty architecture summary."},
        )
    if not system_components:
        return _error(
            "architecture_approval_validation_failed",
            {"message": "Architecture approval requires at least one system component."},
        )
    if not testing_strategy:
        return _error(
            "architecture_approval_validation_failed",
            {"message": "Architecture approval requires at least one testing strategy item."},
        )

    now = _now_iso()
    architecture_contract["architecture_summary"] = architecture_summary
    architecture_contract["system_components"] = system_components
    architecture_contract["testing_strategy"] = testing_strategy
    architecture_contract["lifecycle_state"] = "architecture_approved"
    architecture_contract["updated_at"] = now
    architecture_contract["approved_at"] = now
    architecture_contract["approved_by"] = str(approval_payload.get("approved_by", "")).strip() or "local_operator"
    architecture_contract["model_execution_status"] = "not_requested"
    architecture_contract["github_mutation_status"] = "not_requested"
    architecture_contract["next_recommended_action"] = "prepare_milestone_issue_plan"
    _append_architecture_audit_entry(
        architecture_contract,
        event_type="architecture_approved",
        lifecycle_state="architecture_approved",
        summary="Architecture contract approved locally and ready for milestone planning.",
    )

    architecture_path = resolve_project_architecture_contract_path(config.repo_root, normalized_project_id)
    architecture_path.write_text(json.dumps(architecture_contract, indent=2) + "\n", encoding="utf-8")

    dossier_result = read_project_factory_dossier(config, normalized_project_id)
    dossier = dict(dossier_result.get("dossier", {})) if dossier_result.get("dossier_exists", False) else {}
    if dossier:
        dossier["lifecycle_state"] = "architecture_approved"
        dossier["next_recommended_action"] = "prepare_milestone_issue_plan"
        dossier["updated_at"] = now
        create_project_factory_dossier(config, dossier)

    return {
        "ok": True,
        "local_only": True,
        "project_id": normalized_project_id,
        "architecture_contract": architecture_contract,
        "architecture_contract_path": str(architecture_path),
        "dossier_path": str(resolve_project_factory_dossier_path(config.repo_root, normalized_project_id)),
        "warnings": sorted(set(architecture_result.get("warnings", []))),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }


def read_project_milestone_issue_plan(config: AppConfig, project_id: str) -> dict[str, Any]:
    normalized_project_id = str(project_id or "").strip()
    plan_path = resolve_project_milestone_issue_plan_path(config.repo_root, normalized_project_id)
    warnings: list[str] = []
    if not plan_path.exists():
        warnings.append(f"Milestone/issue plan not found for project: {normalized_project_id}")
        return {
            "ok": True,
            "local_only": True,
            "project_id": normalized_project_id,
            "milestone_issue_plan_path": str(plan_path),
            "milestone_issue_plan_exists": False,
            "milestone_issue_plan": {},
            "warnings": warnings,
            "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
        }
    try:
        loaded = json.loads(plan_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        warnings.append(f"Milestone/issue plan could not be parsed: {exc}")
        loaded = {}
    if not isinstance(loaded, dict):
        warnings.append("Milestone/issue plan has invalid schema; expected JSON object.")
        loaded = {}
    return {
        "ok": True,
        "local_only": True,
        "project_id": normalized_project_id,
        "milestone_issue_plan_path": str(plan_path),
        "milestone_issue_plan_exists": bool(loaded),
        "milestone_issue_plan": loaded,
        "warnings": sorted(set(warnings)),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }


def prepare_project_milestone_issue_plan(config: AppConfig, project_id: str) -> dict[str, Any]:
    normalized_project_id = str(project_id or "").strip()
    architecture_result = read_project_architecture_contract(config, normalized_project_id)
    if not architecture_result.get("architecture_contract_exists", False):
        return _error(
            "architecture_contract_not_found",
            {
                "message": "Architecture contract must exist before preparing milestone/issue plan.",
                "project_id": normalized_project_id,
                "architecture_contract_path": architecture_result.get("architecture_contract_path", ""),
            },
        )
    architecture_contract = dict(architecture_result.get("architecture_contract", {}))
    if str(architecture_contract.get("lifecycle_state", "")).strip() != "architecture_approved":
        return _error(
            "architecture_not_approved",
            {
                "message": "Architecture contract must be approved before preparing milestone/issue plan.",
                "project_id": normalized_project_id,
            },
        )

    scope_result = read_project_scope_package(config, normalized_project_id)
    scope_package = dict(scope_result.get("scope_package", {}))
    now = _now_iso()
    plan_path = resolve_project_milestone_issue_plan_path(config.repo_root, normalized_project_id)
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    existing_created_at = ""
    if plan_path.exists():
        try:
            existing_raw = json.loads(plan_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            existing_raw = {}
        if isinstance(existing_raw, dict):
            existing_created_at = str(existing_raw.get("created_at", "")).strip()

    milestones = [
        {
            "milestone_id": "M1",
            "title": "M1 Foundation",
            "description": "Establish project foundations aligned with approved architecture.",
            "target_state": "Foundational structure and contracts are in place.",
            "depends_on": [],
            "status": "planned",
        },
        {
            "milestone_id": "M2",
            "title": "M2 Core Implementation",
            "description": "Implement primary feature workflows and component interactions.",
            "target_state": "Core capabilities implemented with local validation evidence.",
            "depends_on": ["M1"],
            "status": "planned",
        },
        {
            "milestone_id": "M3",
            "title": "M3 Validation and Documentation",
            "description": "Complete validation, documentation, and closeout readiness.",
            "target_state": "Validation and documentation are complete for GitHub apply planning.",
            "depends_on": ["M2"],
            "status": "planned",
        },
    ]
    issues = [
        {
            "issue_id": "I1",
            "milestone_id": "M1",
            "title": "Confirm project architecture",
            "description": "Confirm architecture assumptions and component boundaries before implementation.",
            "issue_type": "architecture",
            "priority": "high",
            "agent_type": "architect",
            "acceptance_criteria": ["Architecture assumptions are reviewed and captured."],
            "validation_commands": [],
            "status": "planned",
            "github_issue_number": None,
        },
        {
            "issue_id": "I2",
            "milestone_id": "M1",
            "title": "Implement foundation skeleton",
            "description": "Create baseline project skeleton matching approved architecture contract.",
            "issue_type": "task",
            "priority": "normal",
            "agent_type": "backend",
            "acceptance_criteria": ["Project skeleton reflects approved architecture components."],
            "validation_commands": [],
            "status": "planned",
            "github_issue_number": None,
        },
        {
            "issue_id": "I3",
            "milestone_id": "M2",
            "title": "Implement core feature set",
            "description": "Deliver core functionality defined by approved scope and architecture.",
            "issue_type": "feature",
            "priority": "high",
            "agent_type": "backend",
            "acceptance_criteria": ["Core feature set meets approved acceptance criteria."],
            "validation_commands": [],
            "status": "planned",
            "github_issue_number": None,
        },
        {
            "issue_id": "I4",
            "milestone_id": "M3",
            "title": "Add tests and validation",
            "description": "Add local test coverage and validation command mapping.",
            "issue_type": "validation",
            "priority": "normal",
            "agent_type": "test",
            "acceptance_criteria": ["Validation coverage is documented and repeatable locally."],
            "validation_commands": [],
            "status": "planned",
            "github_issue_number": None,
        },
        {
            "issue_id": "I5",
            "milestone_id": "M3",
            "title": "Update documentation",
            "description": "Update docs to reflect architecture and implementation decisions.",
            "issue_type": "documentation",
            "priority": "normal",
            "agent_type": "docs",
            "acceptance_criteria": ["Documentation reflects current implementation and validation."],
            "validation_commands": [],
            "status": "planned",
            "github_issue_number": None,
        },
        {
            "issue_id": "I6",
            "milestone_id": "M3",
            "title": "Prepare closeout evidence",
            "description": "Collect final evidence and release readiness notes for handoff.",
            "issue_type": "task",
            "priority": "normal",
            "agent_type": "release",
            "acceptance_criteria": ["Closeout evidence package is complete and locally verifiable."],
            "validation_commands": [],
            "status": "planned",
            "github_issue_number": None,
        },
    ]
    plan = {
        "schema_version": "1.0",
        "project_id": normalized_project_id,
        "created_at": existing_created_at or now,
        "updated_at": now,
        "lifecycle_state": "milestone_issue_plan_prepared",
        "source": "local_project_factory",
        "input": {
            "approved_scope_summary": str(scope_package.get("notes", "")).strip(),
            "approved_architecture_summary": str(architecture_contract.get("architecture_summary", "")).strip(),
            "requirements": _normalize_text_list(scope_package.get("requirements")),
            "acceptance_criteria": _normalize_text_list(scope_package.get("acceptance_criteria")),
            "architecture_summary": str(architecture_contract.get("architecture_summary", "")).strip(),
            "system_components": _normalize_text_list(architecture_contract.get("system_components")),
            "testing_strategy": _normalize_text_list(architecture_contract.get("testing_strategy")),
            "documentation_plan": _normalize_text_list(architecture_contract.get("documentation_plan")),
            "milestone_planning_notes": str(architecture_contract.get("milestone_planning_notes", "")).strip(),
        },
        "planning_summary": "",
        "milestones": milestones,
        "issues": issues,
        "cross_cutting_tasks": [],
        "validation_plan": [],
        "documentation_plan": [],
        "release_notes": [],
        "open_questions": [],
        "github_apply_notes": "",
        "model_execution_status": "not_requested",
        "github_mutation_status": "not_requested",
        "next_recommended_action": "edit_milestone_issue_plan",
        "audit_trail": [],
    }
    _append_milestone_issue_plan_audit_entry(
        plan,
        event_type="milestone_issue_plan_prepared",
        lifecycle_state="milestone_issue_plan_prepared",
        summary="Milestone/issue plan prepared locally from approved architecture contract.",
    )
    plan_path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")

    dossier_result = read_project_factory_dossier(config, normalized_project_id)
    dossier = dict(dossier_result.get("dossier", {})) if dossier_result.get("dossier_exists", False) else {}
    if dossier:
        dossier["lifecycle_state"] = "milestone_issue_plan_prepared"
        dossier["next_recommended_action"] = "edit_milestone_issue_plan"
        dossier["updated_at"] = now
        create_project_factory_dossier(config, dossier)

    return {
        "ok": True,
        "local_only": True,
        "project_id": normalized_project_id,
        "milestone_issue_plan": plan,
        "milestone_issue_plan_path": str(plan_path),
        "dossier_path": str(resolve_project_factory_dossier_path(config.repo_root, normalized_project_id)),
        "warnings": sorted(set(architecture_result.get("warnings", []) + scope_result.get("warnings", []))),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }


def update_project_milestone_issue_plan(config: AppConfig, project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    plan_result = read_project_milestone_issue_plan(config, project_id)
    normalized_project_id = str(plan_result.get("project_id", "")).strip()
    if not plan_result.get("milestone_issue_plan_exists", False):
        return _error(
            "milestone_issue_plan_not_found",
            {
                "message": "Milestone/issue plan must be prepared before updating draft fields.",
                "project_id": normalized_project_id,
                "milestone_issue_plan_path": plan_result.get("milestone_issue_plan_path", ""),
            },
        )
    plan = dict(plan_result.get("milestone_issue_plan", {}))
    now = _now_iso()
    if "planning_summary" in payload:
        plan["planning_summary"] = str(payload.get("planning_summary", "")).strip()
    for field in (
        "cross_cutting_tasks",
        "validation_plan",
        "documentation_plan",
        "release_notes",
        "open_questions",
    ):
        if field in payload:
            plan[field] = _normalize_text_list(payload.get(field))
    if "github_apply_notes" in payload:
        plan["github_apply_notes"] = str(payload.get("github_apply_notes", "")).strip()
    if "milestones" in payload and isinstance(payload.get("milestones"), list):
        plan["milestones"] = [item for item in payload.get("milestones", []) if isinstance(item, dict)]
    if "issues" in payload and isinstance(payload.get("issues"), list):
        plan["issues"] = [item for item in payload.get("issues", []) if isinstance(item, dict)]

    plan["lifecycle_state"] = "milestone_issue_plan_draft_updated"
    plan["updated_at"] = now
    plan["model_execution_status"] = "not_requested"
    plan["github_mutation_status"] = "not_requested"
    plan["next_recommended_action"] = "approve_milestone_issue_plan_or_continue_editing"
    _append_milestone_issue_plan_audit_entry(
        plan,
        event_type="milestone_issue_plan_draft_updated",
        lifecycle_state="milestone_issue_plan_draft_updated",
        summary="Milestone/issue plan draft fields were updated locally.",
    )
    plan_path = resolve_project_milestone_issue_plan_path(config.repo_root, normalized_project_id)
    plan_path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")

    dossier_result = read_project_factory_dossier(config, normalized_project_id)
    dossier = dict(dossier_result.get("dossier", {})) if dossier_result.get("dossier_exists", False) else {}
    if dossier:
        dossier["lifecycle_state"] = "milestone_issue_plan_draft_updated"
        dossier["next_recommended_action"] = "approve_milestone_issue_plan_or_continue_editing"
        dossier["updated_at"] = now
        create_project_factory_dossier(config, dossier)
    return {
        "ok": True,
        "local_only": True,
        "project_id": normalized_project_id,
        "milestone_issue_plan": plan,
        "milestone_issue_plan_path": str(plan_path),
        "dossier_path": str(resolve_project_factory_dossier_path(config.repo_root, normalized_project_id)),
        "warnings": sorted(set(plan_result.get("warnings", []))),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }


def approve_project_milestone_issue_plan(config: AppConfig, project_id: str, approval_payload: dict[str, Any]) -> dict[str, Any]:
    plan_result = read_project_milestone_issue_plan(config, project_id)
    normalized_project_id = str(plan_result.get("project_id", "")).strip()
    if not plan_result.get("milestone_issue_plan_exists", False):
        return _error(
            "milestone_issue_plan_not_found",
            {
                "message": "Milestone/issue plan must be prepared before approval.",
                "project_id": normalized_project_id,
                "milestone_issue_plan_path": plan_result.get("milestone_issue_plan_path", ""),
            },
        )
    plan = dict(plan_result.get("milestone_issue_plan", {}))
    planning_summary = str(plan.get("planning_summary", "")).strip()
    milestones = [item for item in plan.get("milestones", []) if isinstance(item, dict)]
    issues = [item for item in plan.get("issues", []) if isinstance(item, dict)]
    if not planning_summary:
        return _error("milestone_issue_plan_approval_validation_failed", {"message": "Plan approval requires a non-empty planning summary."})
    if not milestones:
        return _error("milestone_issue_plan_approval_validation_failed", {"message": "Plan approval requires at least one milestone."})
    if not issues:
        return _error("milestone_issue_plan_approval_validation_failed", {"message": "Plan approval requires at least one issue."})
    milestone_ids = {str(item.get("milestone_id", "")).strip() for item in milestones if str(item.get("milestone_id", "")).strip()}
    for issue in issues:
        milestone_id = str(issue.get("milestone_id", "")).strip()
        if not str(issue.get("title", "")).strip() or not str(issue.get("description", "")).strip() or not milestone_id:
            return _error("milestone_issue_plan_approval_validation_failed", {"message": "Each issue must include title, description, and milestone_id."})
        if milestone_id not in milestone_ids:
            return _error("milestone_issue_plan_approval_validation_failed", {"message": f"Issue references unknown milestone_id: {milestone_id}"})
        if str(issue.get("issue_type", "")).strip() not in _MILESTONE_ISSUE_TYPES:
            return _error("milestone_issue_plan_approval_validation_failed", {"message": "Each issue must include a valid issue_type."})
        if str(issue.get("priority", "")).strip() not in _MILESTONE_ISSUE_PRIORITIES:
            return _error("milestone_issue_plan_approval_validation_failed", {"message": "Each issue must include a valid priority."})
        if str(issue.get("agent_type", "")).strip() not in _MILESTONE_ISSUE_AGENT_TYPES:
            return _error("milestone_issue_plan_approval_validation_failed", {"message": "Each issue must include a valid agent_type."})

    now = _now_iso()
    plan["planning_summary"] = planning_summary
    plan["milestones"] = milestones
    plan["issues"] = issues
    plan["lifecycle_state"] = "milestone_issue_plan_approved"
    plan["updated_at"] = now
    plan["approved_at"] = now
    plan["approved_by"] = str(approval_payload.get("approved_by", "")).strip() or "local_operator"
    plan["model_execution_status"] = "not_requested"
    plan["github_mutation_status"] = "not_requested"
    plan["next_recommended_action"] = "prepare_github_apply_plan"
    _append_milestone_issue_plan_audit_entry(
        plan,
        event_type="milestone_issue_plan_approved",
        lifecycle_state="milestone_issue_plan_approved",
        summary="Milestone/issue plan approved locally and ready for GitHub apply planning gate.",
    )
    plan_path = resolve_project_milestone_issue_plan_path(config.repo_root, normalized_project_id)
    plan_path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")

    dossier_result = read_project_factory_dossier(config, normalized_project_id)
    dossier = dict(dossier_result.get("dossier", {})) if dossier_result.get("dossier_exists", False) else {}
    if dossier:
        dossier["lifecycle_state"] = "milestone_issue_plan_approved"
        dossier["next_recommended_action"] = "prepare_github_apply_plan"
        dossier["updated_at"] = now
        create_project_factory_dossier(config, dossier)
    return {
        "ok": True,
        "local_only": True,
        "project_id": normalized_project_id,
        "milestone_issue_plan": plan,
        "milestone_issue_plan_path": str(plan_path),
        "dossier_path": str(resolve_project_factory_dossier_path(config.repo_root, normalized_project_id)),
        "warnings": sorted(set(plan_result.get("warnings", []))),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }


def read_project_github_apply_plan(config: AppConfig, project_id: str) -> dict[str, Any]:
    normalized_project_id = str(project_id or "").strip()
    plan_path = resolve_project_github_apply_plan_path(config.repo_root, normalized_project_id)
    warnings: list[str] = []
    if not plan_path.exists():
        warnings.append(f"GitHub apply plan not found for project: {normalized_project_id}")
        return {
            "ok": True,
            "local_only": True,
            "project_id": normalized_project_id,
            "github_apply_plan_path": str(plan_path),
            "github_apply_plan_exists": False,
            "github_apply_plan": {},
            "warnings": warnings,
            "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
        }
    try:
        loaded = json.loads(plan_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        warnings.append(f"GitHub apply plan could not be parsed: {exc}")
        loaded = {}
    if not isinstance(loaded, dict):
        warnings.append("GitHub apply plan has invalid schema; expected JSON object.")
        loaded = {}
    return {
        "ok": True,
        "local_only": True,
        "project_id": normalized_project_id,
        "github_apply_plan_path": str(plan_path),
        "github_apply_plan_exists": bool(loaded),
        "github_apply_plan": loaded,
        "warnings": sorted(set(warnings)),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }


def prepare_project_github_apply_plan(config: AppConfig, project_id: str) -> dict[str, Any]:
    normalized_project_id = str(project_id or "").strip()
    milestone_plan_result = read_project_milestone_issue_plan(config, normalized_project_id)
    if not milestone_plan_result.get("milestone_issue_plan_exists", False):
        return _error(
            "milestone_issue_plan_not_found",
            {
                "message": "Milestone/issue plan must exist before preparing GitHub apply plan.",
                "project_id": normalized_project_id,
                "milestone_issue_plan_path": milestone_plan_result.get("milestone_issue_plan_path", ""),
            },
        )
    milestone_plan = dict(milestone_plan_result.get("milestone_issue_plan", {}))
    if str(milestone_plan.get("lifecycle_state", "")).strip() != "milestone_issue_plan_approved":
        return _error(
            "milestone_issue_plan_not_approved",
            {
                "message": "Milestone/issue plan must be approved before preparing GitHub apply plan.",
                "project_id": normalized_project_id,
            },
        )
    dossier_result = read_project_factory_dossier(config, normalized_project_id)
    dossier = dict(dossier_result.get("dossier", {})) if dossier_result.get("dossier_exists", False) else {}
    now = _now_iso()
    plan_path = resolve_project_github_apply_plan_path(config.repo_root, normalized_project_id)
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    existing_created_at = ""
    if plan_path.exists():
        try:
            existing_raw = json.loads(plan_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            existing_raw = {}
        if isinstance(existing_raw, dict):
            existing_created_at = str(existing_raw.get("created_at", "")).strip()

    milestones = [item for item in milestone_plan.get("milestones", []) if isinstance(item, dict)]
    issues = [item for item in milestone_plan.get("issues", []) if isinstance(item, dict)]
    owner = str((dossier.get("github_owner", "") if dossier else "") or milestone_plan.get("github_owner", "")).strip()
    repo = str((dossier.get("github_repo", "") if dossier else "") or milestone_plan.get("github_repo", "")).strip()
    github_url = str((dossier.get("github_url", "") if dossier else "") or milestone_plan.get("github_url", "")).strip()
    default_branch = str((dossier.get("default_branch", "") if dossier else "") or "main").strip() or "main"
    github_mode = str((dossier.get("github_mode", "") if dossier else "") or "create-later").strip() or "create-later"
    default_labels = ["aresforge", "project-factory", "local-only-plan"]

    milestone_intents = [
        {
            "local_milestone_id": str(item.get("milestone_id", "")).strip(),
            "title": str(item.get("title", "")).strip(),
            "description": str(item.get("description", "")).strip(),
            "target_state": str(item.get("target_state", "")).strip(),
            "planned_action": "create_milestone",
            "github_milestone_number": None,
            "execution_status": "not_executed",
        }
        for item in milestones
    ]
    issue_intents: list[dict[str, Any]] = []
    labels: list[str] = []
    for issue in issues:
        issue_type = str(issue.get("issue_type", "")).strip() or "task"
        priority = str(issue.get("priority", "")).strip() or "normal"
        agent_type = str(issue.get("agent_type", "")).strip() or "operator"
        issue_labels = [
            "project-factory",
            "aresforge",
            f"issue-type:{issue_type}",
            f"priority:{priority}",
            f"agent:{agent_type}",
        ]
        for label in issue_labels + default_labels:
            if label not in labels:
                labels.append(label)
        description = str(issue.get("description", "")).strip()
        acceptance_criteria = _normalize_text_list(issue.get("acceptance_criteria"))
        validation_commands = _normalize_text_list(issue.get("validation_commands"))
        body_sections = [
            "## Description",
            description or "(not provided)",
            "",
            "## Issue Metadata",
            f"- issue_type: {issue_type}",
            f"- priority: {priority}",
            f"- agent_type: {agent_type}",
            "",
            "## Acceptance Criteria",
        ]
        if acceptance_criteria:
            body_sections.extend([f"- {item}" for item in acceptance_criteria])
        else:
            body_sections.append("- (none provided)")
        body_sections.extend(["", "## Validation Commands"])
        if validation_commands:
            body_sections.extend([f"- {item}" for item in validation_commands])
        else:
            body_sections.append("- (none provided)")
        body_sections.extend(["", "## Safety", "- Local plan only; not executed."])
        issue_intents.append(
            {
                "local_issue_id": str(issue.get("issue_id", "")).strip(),
                "local_milestone_id": str(issue.get("milestone_id", "")).strip(),
                "title": str(issue.get("title", "")).strip(),
                "body": "\n".join(body_sections).strip(),
                "labels": issue_labels,
                "issue_type": issue_type,
                "priority": priority,
                "agent_type": agent_type,
                "planned_action": "create_issue",
                "github_issue_number": None,
                "execution_status": "not_executed",
            }
        )
    plan = {
        "schema_version": "1.0",
        "project_id": normalized_project_id,
        "created_at": existing_created_at or now,
        "updated_at": now,
        "lifecycle_state": "github_apply_plan_prepared",
        "source": "local_project_factory",
        "input": {
            "approved_milestone_issue_plan_summary": str(milestone_plan.get("planning_summary", "")).strip(),
            "milestones": milestones,
            "issues": issues,
            "github_owner": owner,
            "github_repo": repo,
            "github_url": github_url,
            "default_branch": default_branch,
            "github_mode": github_mode,
        },
        "mutation_intent": {
            "create_milestones": milestone_intents,
            "create_issues": issue_intents,
            "labels": labels,
            "issue_body_template_version": "1.0",
            "milestone_body_template_version": "1.0",
        },
        "apply_summary": "",
        "operator_notes": "",
        "labels": labels,
        "dry_run_notes": [],
        "preflight_checks": list(_BOUNDARY_CONFIRMATIONS),
        "approval_conditions": ["Execution requires explicit approval and remains gated until requested."],
        "known_risks": [],
        "local_only": True,
        "github_mutation_status": "not_requested",
        "github_execution_status": "not_executed",
        "model_execution_status": "not_requested",
        "requires_explicit_github_approval": True,
        "next_recommended_action": "review_github_apply_plan",
        "audit_trail": [],
    }
    _append_github_apply_plan_audit_entry(
        plan,
        event_type="github_apply_plan_prepared",
        lifecycle_state="github_apply_plan_prepared",
        summary="GitHub apply plan prepared locally from approved milestone/issue plan.",
    )
    plan_path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    if dossier:
        dossier["lifecycle_state"] = "github_apply_plan_prepared"
        dossier["next_recommended_action"] = "review_github_apply_plan"
        dossier["updated_at"] = now
        create_project_factory_dossier(config, dossier)
    return {
        "ok": True,
        "local_only": True,
        "project_id": normalized_project_id,
        "github_apply_plan": plan,
        "github_apply_plan_path": str(plan_path),
        "dossier_path": str(resolve_project_factory_dossier_path(config.repo_root, normalized_project_id)),
        "warnings": sorted(set(milestone_plan_result.get("warnings", []))),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }


def update_project_github_apply_plan(config: AppConfig, project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    plan_result = read_project_github_apply_plan(config, project_id)
    normalized_project_id = str(plan_result.get("project_id", "")).strip()
    if not plan_result.get("github_apply_plan_exists", False):
        return _error(
            "github_apply_plan_not_found",
            {
                "message": "GitHub apply plan must be prepared before updating draft fields.",
                "project_id": normalized_project_id,
                "github_apply_plan_path": plan_result.get("github_apply_plan_path", ""),
            },
        )
    plan = dict(plan_result.get("github_apply_plan", {}))
    now = _now_iso()
    if "apply_summary" in payload:
        plan["apply_summary"] = str(payload.get("apply_summary", "")).strip()
    if "operator_notes" in payload:
        plan["operator_notes"] = str(payload.get("operator_notes", "")).strip()
    for field in ("labels", "dry_run_notes", "preflight_checks", "approval_conditions", "known_risks"):
        if field in payload:
            if field == "labels":
                plan[field] = _normalize_tags(payload.get(field))
            else:
                plan[field] = _normalize_text_list(payload.get(field))
    plan["lifecycle_state"] = "github_apply_plan_draft_updated"
    plan["updated_at"] = now
    plan["local_only"] = True
    plan["github_mutation_status"] = "not_requested"
    plan["github_execution_status"] = "not_executed"
    plan["model_execution_status"] = "not_requested"
    plan["requires_explicit_github_approval"] = True
    plan["next_recommended_action"] = "approve_github_apply_plan_or_continue_editing"
    _append_github_apply_plan_audit_entry(
        plan,
        event_type="github_apply_plan_draft_updated",
        lifecycle_state="github_apply_plan_draft_updated",
        summary="GitHub apply plan draft fields were updated locally.",
    )
    plan_path = resolve_project_github_apply_plan_path(config.repo_root, normalized_project_id)
    plan_path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    dossier_result = read_project_factory_dossier(config, normalized_project_id)
    dossier = dict(dossier_result.get("dossier", {})) if dossier_result.get("dossier_exists", False) else {}
    if dossier:
        dossier["lifecycle_state"] = "github_apply_plan_draft_updated"
        dossier["next_recommended_action"] = "approve_github_apply_plan_or_continue_editing"
        dossier["updated_at"] = now
        create_project_factory_dossier(config, dossier)
    return {
        "ok": True,
        "local_only": True,
        "project_id": normalized_project_id,
        "github_apply_plan": plan,
        "github_apply_plan_path": str(plan_path),
        "dossier_path": str(resolve_project_factory_dossier_path(config.repo_root, normalized_project_id)),
        "warnings": sorted(set(plan_result.get("warnings", []))),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }


def approve_project_github_apply_plan(config: AppConfig, project_id: str, approval_payload: dict[str, Any]) -> dict[str, Any]:
    plan_result = read_project_github_apply_plan(config, project_id)
    normalized_project_id = str(plan_result.get("project_id", "")).strip()
    if not plan_result.get("github_apply_plan_exists", False):
        return _error(
            "github_apply_plan_not_found",
            {
                "message": "GitHub apply plan must be prepared before approval.",
                "project_id": normalized_project_id,
                "github_apply_plan_path": plan_result.get("github_apply_plan_path", ""),
            },
        )
    plan = dict(plan_result.get("github_apply_plan", {}))
    apply_summary = str(plan.get("apply_summary", "")).strip()
    mutation_intent = plan.get("mutation_intent", {}) if isinstance(plan.get("mutation_intent"), dict) else {}
    milestone_intents = [item for item in mutation_intent.get("create_milestones", []) if isinstance(item, dict)]
    issue_intents = [item for item in mutation_intent.get("create_issues", []) if isinstance(item, dict)]
    input_payload = plan.get("input", {}) if isinstance(plan.get("input"), dict) else {}
    github_mode = str(input_payload.get("github_mode", "")).strip()
    github_owner = str(input_payload.get("github_owner", "")).strip()
    github_repo = str(input_payload.get("github_repo", "")).strip()
    approval_conditions = _normalize_text_list(plan.get("approval_conditions"))
    if not apply_summary:
        return _error("github_apply_plan_approval_validation_failed", {"message": "Apply plan approval requires a non-empty apply_summary."})
    if not milestone_intents and not issue_intents:
        return _error("github_apply_plan_approval_validation_failed", {"message": "Apply plan approval requires at least one milestone or issue intent."})
    if not ((github_owner and github_repo) or github_mode in {"create-later", "create-with-approval-later"}):
        return _error("github_apply_plan_approval_validation_failed", {"message": "Apply plan approval requires github owner/repo or github_mode set to create-later/create-with-approval-later."})
    if not any(("approval" in item.lower() or "gated" in item.lower()) for item in approval_conditions):
        return _error("github_apply_plan_approval_validation_failed", {"message": "Apply plan approval_conditions must include an explicit approval or gated execution condition."})

    now = _now_iso()
    plan["approval_conditions"] = approval_conditions
    plan["lifecycle_state"] = "github_apply_plan_approved"
    plan["updated_at"] = now
    plan["approved_at"] = now
    plan["approved_by"] = str(approval_payload.get("approved_by", "")).strip() or "local_operator"
    plan["local_only"] = True
    plan["github_mutation_status"] = "not_requested"
    plan["github_execution_status"] = "not_executed"
    plan["model_execution_status"] = "not_requested"
    plan["requires_explicit_github_approval"] = True
    plan["next_recommended_action"] = "prepare_agent_dispatch_plan"
    _append_github_apply_plan_audit_entry(
        plan,
        event_type="github_apply_plan_approved",
        lifecycle_state="github_apply_plan_approved",
        summary="GitHub apply plan approved locally; no GitHub execution performed.",
    )
    plan_path = resolve_project_github_apply_plan_path(config.repo_root, normalized_project_id)
    plan_path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    dossier_result = read_project_factory_dossier(config, normalized_project_id)
    dossier = dict(dossier_result.get("dossier", {})) if dossier_result.get("dossier_exists", False) else {}
    if dossier:
        dossier["lifecycle_state"] = "github_apply_plan_approved"
        dossier["next_recommended_action"] = "prepare_agent_dispatch_plan"
        dossier["updated_at"] = now
        create_project_factory_dossier(config, dossier)
    return {
        "ok": True,
        "local_only": True,
        "project_id": normalized_project_id,
        "github_apply_plan": plan,
        "github_apply_plan_path": str(plan_path),
        "dossier_path": str(resolve_project_factory_dossier_path(config.repo_root, normalized_project_id)),
        "warnings": sorted(set(plan_result.get("warnings", []))),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }


def read_project_agent_dispatch_plan(config: AppConfig, project_id: str) -> dict[str, Any]:
    normalized_project_id = str(project_id or "").strip()
    plan_path = resolve_project_agent_dispatch_plan_path(config.repo_root, normalized_project_id)
    warnings: list[str] = []
    if not plan_path.exists():
        warnings.append(f"Agent dispatch plan not found for project: {normalized_project_id}")
        return {
            "ok": True,
            "local_only": True,
            "project_id": normalized_project_id,
            "agent_dispatch_plan_path": str(plan_path),
            "agent_dispatch_plan_exists": False,
            "agent_dispatch_plan": {},
            "warnings": warnings,
            "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
        }
    try:
        loaded = json.loads(plan_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        warnings.append(f"Agent dispatch plan could not be parsed: {exc}")
        loaded = {}
    if not isinstance(loaded, dict):
        warnings.append("Agent dispatch plan has invalid schema; expected JSON object.")
        loaded = {}
    return {
        "ok": True,
        "local_only": True,
        "project_id": normalized_project_id,
        "agent_dispatch_plan_path": str(plan_path),
        "agent_dispatch_plan_exists": bool(loaded),
        "agent_dispatch_plan": loaded,
        "warnings": sorted(set(warnings)),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }


def prepare_project_agent_dispatch_plan(config: AppConfig, project_id: str) -> dict[str, Any]:
    normalized_project_id = str(project_id or "").strip()
    github_apply_result = read_project_github_apply_plan(config, normalized_project_id)
    if not github_apply_result.get("github_apply_plan_exists", False):
        return _error(
            "github_apply_plan_not_found",
            {
                "message": "GitHub apply plan must exist before preparing agent dispatch plan.",
                "project_id": normalized_project_id,
                "github_apply_plan_path": github_apply_result.get("github_apply_plan_path", ""),
            },
        )
    github_apply_plan = dict(github_apply_result.get("github_apply_plan", {}))
    if str(github_apply_plan.get("lifecycle_state", "")).strip() != "github_apply_plan_approved":
        return _error(
            "github_apply_plan_not_approved",
            {
                "message": "GitHub apply plan must be approved before preparing agent dispatch plan.",
                "project_id": normalized_project_id,
            },
        )
    now = _now_iso()
    plan_path = resolve_project_agent_dispatch_plan_path(config.repo_root, normalized_project_id)
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    existing_created_at = ""
    if plan_path.exists():
        try:
            existing_raw = json.loads(plan_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            existing_raw = {}
        if isinstance(existing_raw, dict):
            existing_created_at = str(existing_raw.get("created_at", "")).strip()

    mutation_intent = github_apply_plan.get("mutation_intent", {}) if isinstance(github_apply_plan.get("mutation_intent"), dict) else {}
    milestone_intents = [item for item in mutation_intent.get("create_milestones", []) if isinstance(item, dict)]
    issue_intents = [item for item in mutation_intent.get("create_issues", []) if isinstance(item, dict)]
    dispatch_items: list[dict[str, Any]] = []
    for index, issue in enumerate(issue_intents, start=1):
        dispatch_items.append(
            {
                "dispatch_id": f"D{index}",
                "local_issue_id": str(issue.get("local_issue_id", "")).strip(),
                "local_milestone_id": str(issue.get("local_milestone_id", "")).strip(),
                "title": str(issue.get("title", "")).strip(),
                "issue_type": str(issue.get("issue_type", "")).strip() or "task",
                "priority": str(issue.get("priority", "")).strip() or "normal",
                "agent_type": str(issue.get("agent_type", "")).strip() or "operator",
                "assigned_agent_profile_id": None,
                "queue_status": "planned",
                "execution_status": "not_executed",
                "model_execution_status": "not_requested",
                "github_issue_number": None,
                "acceptance_criteria": _normalize_text_list(issue.get("acceptance_criteria")),
                "validation_commands": _normalize_text_list(issue.get("validation_commands")),
                "dependencies": _normalize_text_list(issue.get("dependencies")),
                "planned_artifacts": [],
                "safety_notes": ["Local dispatch plan only; no execution performed."],
            }
        )
    queue_map: dict[str, dict[str, Any]] = {}
    for item in dispatch_items:
        agent_type = str(item.get("agent_type", "")).strip() or "operator"
        bucket = queue_map.setdefault(
            agent_type,
            {"agent_type": agent_type, "item_count": 0, "high_priority_count": 0, "urgent_priority_count": 0, "dispatch_ids": []},
        )
        bucket["item_count"] += 1
        priority = str(item.get("priority", "")).strip()
        if priority == "high":
            bucket["high_priority_count"] += 1
        if priority == "urgent":
            bucket["urgent_priority_count"] += 1
        bucket["dispatch_ids"].append(str(item.get("dispatch_id", "")).strip())
    agent_queues = list(queue_map.values())
    input_payload = github_apply_plan.get("input", {}) if isinstance(github_apply_plan.get("input"), dict) else {}
    plan = {
        "schema_version": "1.0",
        "project_id": normalized_project_id,
        "created_at": existing_created_at or now,
        "updated_at": now,
        "lifecycle_state": "agent_dispatch_plan_prepared",
        "source": "local_project_factory",
        "input": {
            "approved_github_apply_plan_summary": str(github_apply_plan.get("apply_summary", "")).strip(),
            "issue_intents": issue_intents,
            "milestone_intents": milestone_intents,
            "repo_project_metadata": {
                "github_owner": str(input_payload.get("github_owner", "")).strip(),
                "github_repo": str(input_payload.get("github_repo", "")).strip(),
                "github_url": str(input_payload.get("github_url", "")).strip(),
                "default_branch": str(input_payload.get("default_branch", "")).strip(),
                "github_mode": str(input_payload.get("github_mode", "")).strip(),
            },
        },
        "dispatch_plan": {
            "dispatch_items": dispatch_items,
            "agent_queues": agent_queues,
            "sequencing_notes": [],
            "dependency_notes": [],
        },
        "dispatch_summary": "",
        "operator_notes": "",
        "sequencing_notes": [],
        "dependency_notes": [],
        "approval_conditions": ["Agent/model execution requires explicit operator approval."],
        "known_risks": [],
        "local_only": True,
        "agent_execution_status": "not_requested",
        "model_execution_status": "not_requested",
        "github_mutation_status": "not_requested",
        "requires_explicit_agent_execution_approval": True,
        "next_recommended_action": "review_agent_dispatch_plan",
        "audit_trail": [],
    }
    _append_agent_dispatch_plan_audit_entry(
        plan,
        event_type="agent_dispatch_plan_prepared",
        lifecycle_state="agent_dispatch_plan_prepared",
        summary="Agent dispatch plan prepared locally from approved GitHub apply plan.",
    )
    plan_path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    dossier_result = read_project_factory_dossier(config, normalized_project_id)
    dossier = dict(dossier_result.get("dossier", {})) if dossier_result.get("dossier_exists", False) else {}
    if dossier:
        dossier["lifecycle_state"] = "agent_dispatch_plan_prepared"
        dossier["next_recommended_action"] = "review_agent_dispatch_plan"
        dossier["updated_at"] = now
        create_project_factory_dossier(config, dossier)
    return {
        "ok": True,
        "local_only": True,
        "project_id": normalized_project_id,
        "agent_dispatch_plan": plan,
        "agent_dispatch_plan_path": str(plan_path),
        "dossier_path": str(resolve_project_factory_dossier_path(config.repo_root, normalized_project_id)),
        "warnings": sorted(set(github_apply_result.get("warnings", []))),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }


def update_project_agent_dispatch_plan(config: AppConfig, project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    plan_result = read_project_agent_dispatch_plan(config, project_id)
    normalized_project_id = str(plan_result.get("project_id", "")).strip()
    if not plan_result.get("agent_dispatch_plan_exists", False):
        return _error(
            "agent_dispatch_plan_not_found",
            {
                "message": "Agent dispatch plan must be prepared before updating draft fields.",
                "project_id": normalized_project_id,
                "agent_dispatch_plan_path": plan_result.get("agent_dispatch_plan_path", ""),
            },
        )
    plan = dict(plan_result.get("agent_dispatch_plan", {}))
    now = _now_iso()
    for field in ("dispatch_summary", "operator_notes"):
        if field in payload:
            plan[field] = str(payload.get(field, "")).strip()
    for field in ("sequencing_notes", "dependency_notes", "approval_conditions", "known_risks"):
        if field in payload:
            plan[field] = _normalize_text_list(payload.get(field))
    plan["lifecycle_state"] = "agent_dispatch_plan_draft_updated"
    plan["updated_at"] = now
    plan["local_only"] = True
    plan["agent_execution_status"] = "not_requested"
    plan["model_execution_status"] = "not_requested"
    plan["github_mutation_status"] = "not_requested"
    plan["requires_explicit_agent_execution_approval"] = True
    dispatch_plan = plan.get("dispatch_plan", {}) if isinstance(plan.get("dispatch_plan"), dict) else {}
    dispatch_plan["sequencing_notes"] = _normalize_text_list(plan.get("sequencing_notes"))
    dispatch_plan["dependency_notes"] = _normalize_text_list(plan.get("dependency_notes"))
    plan["dispatch_plan"] = dispatch_plan
    plan["next_recommended_action"] = "approve_agent_dispatch_plan_or_continue_editing"
    _append_agent_dispatch_plan_audit_entry(
        plan,
        event_type="agent_dispatch_plan_draft_updated",
        lifecycle_state="agent_dispatch_plan_draft_updated",
        summary="Agent dispatch plan draft fields were updated locally.",
    )
    plan_path = resolve_project_agent_dispatch_plan_path(config.repo_root, normalized_project_id)
    plan_path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    dossier_result = read_project_factory_dossier(config, normalized_project_id)
    dossier = dict(dossier_result.get("dossier", {})) if dossier_result.get("dossier_exists", False) else {}
    if dossier:
        dossier["lifecycle_state"] = "agent_dispatch_plan_draft_updated"
        dossier["next_recommended_action"] = "approve_agent_dispatch_plan_or_continue_editing"
        dossier["updated_at"] = now
        create_project_factory_dossier(config, dossier)
    return {
        "ok": True,
        "local_only": True,
        "project_id": normalized_project_id,
        "agent_dispatch_plan": plan,
        "agent_dispatch_plan_path": str(plan_path),
        "dossier_path": str(resolve_project_factory_dossier_path(config.repo_root, normalized_project_id)),
        "warnings": sorted(set(plan_result.get("warnings", []))),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }


def approve_project_agent_dispatch_plan(config: AppConfig, project_id: str, approval_payload: dict[str, Any]) -> dict[str, Any]:
    plan_result = read_project_agent_dispatch_plan(config, project_id)
    normalized_project_id = str(plan_result.get("project_id", "")).strip()
    if not plan_result.get("agent_dispatch_plan_exists", False):
        return _error(
            "agent_dispatch_plan_not_found",
            {
                "message": "Agent dispatch plan must be prepared before approval.",
                "project_id": normalized_project_id,
                "agent_dispatch_plan_path": plan_result.get("agent_dispatch_plan_path", ""),
            },
        )
    plan = dict(plan_result.get("agent_dispatch_plan", {}))
    dispatch_summary = str(plan.get("dispatch_summary", "")).strip()
    dispatch_plan = plan.get("dispatch_plan", {}) if isinstance(plan.get("dispatch_plan"), dict) else {}
    dispatch_items = [item for item in dispatch_plan.get("dispatch_items", []) if isinstance(item, dict)]
    approval_conditions = _normalize_text_list(plan.get("approval_conditions"))
    if not dispatch_summary:
        return _error("agent_dispatch_plan_approval_validation_failed", {"message": "Dispatch plan approval requires a non-empty dispatch_summary."})
    if not dispatch_items:
        return _error("agent_dispatch_plan_approval_validation_failed", {"message": "Dispatch plan approval requires at least one dispatch item."})
    required_item_fields = ("dispatch_id", "title", "agent_type", "priority", "queue_status", "execution_status")
    for item in dispatch_items:
        for field in required_item_fields:
            if not str(item.get(field, "")).strip():
                return _error("agent_dispatch_plan_approval_validation_failed", {"message": f"Dispatch item is missing required field: {field}."})
        if str(item.get("execution_status", "")).strip() != "not_executed":
            return _error("agent_dispatch_plan_approval_validation_failed", {"message": "All dispatch item execution_status values must remain not_executed."})
    if not any(("agent execution approval" in value.lower() or "model execution approval" in value.lower()) for value in approval_conditions):
        return _error(
            "agent_dispatch_plan_approval_validation_failed",
            {"message": "Approval conditions must explicitly mention agent execution approval or model execution approval."},
        )
    now = _now_iso()
    plan["dispatch_summary"] = dispatch_summary
    plan["approval_conditions"] = approval_conditions
    plan["lifecycle_state"] = "agent_dispatch_plan_approved"
    plan["updated_at"] = now
    plan["approved_at"] = now
    plan["approved_by"] = str(approval_payload.get("approved_by", "")).strip() or "local_operator"
    plan["local_only"] = True
    plan["agent_execution_status"] = "not_requested"
    plan["model_execution_status"] = "not_requested"
    plan["github_mutation_status"] = "not_requested"
    plan["requires_explicit_agent_execution_approval"] = True
    plan["next_recommended_action"] = "prepare_validation_execution_plan"
    _append_agent_dispatch_plan_audit_entry(
        plan,
        event_type="agent_dispatch_plan_approved",
        lifecycle_state="agent_dispatch_plan_approved",
        summary="Agent dispatch plan approved locally; no agent/model execution performed.",
    )
    plan_path = resolve_project_agent_dispatch_plan_path(config.repo_root, normalized_project_id)
    plan_path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    dossier_result = read_project_factory_dossier(config, normalized_project_id)
    dossier = dict(dossier_result.get("dossier", {})) if dossier_result.get("dossier_exists", False) else {}
    if dossier:
        dossier["lifecycle_state"] = "agent_dispatch_plan_approved"
        dossier["next_recommended_action"] = "prepare_validation_execution_plan"
        dossier["updated_at"] = now
        create_project_factory_dossier(config, dossier)
    return {
        "ok": True,
        "local_only": True,
        "project_id": normalized_project_id,
        "agent_dispatch_plan": plan,
        "agent_dispatch_plan_path": str(plan_path),
        "dossier_path": str(resolve_project_factory_dossier_path(config.repo_root, normalized_project_id)),
        "warnings": sorted(set(plan_result.get("warnings", []))),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }


def read_project_validation_execution_plan(config: AppConfig, project_id: str) -> dict[str, Any]:
    normalized_project_id = str(project_id or "").strip()
    plan_path = resolve_project_validation_execution_plan_path(config.repo_root, normalized_project_id)
    warnings: list[str] = []
    if not plan_path.exists():
        warnings.append(f"Validation execution plan not found for project: {normalized_project_id}")
        return {
            "ok": True,
            "local_only": True,
            "project_id": normalized_project_id,
            "validation_execution_plan_path": str(plan_path),
            "validation_execution_plan_exists": False,
            "validation_execution_plan": {},
            "warnings": warnings,
            "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
        }
    try:
        loaded = json.loads(plan_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        warnings.append(f"Validation execution plan could not be parsed: {exc}")
        loaded = {}
    if not isinstance(loaded, dict):
        warnings.append("Validation execution plan has invalid schema; expected JSON object.")
        loaded = {}
    return {
        "ok": True,
        "local_only": True,
        "project_id": normalized_project_id,
        "validation_execution_plan_path": str(plan_path),
        "validation_execution_plan_exists": bool(loaded),
        "validation_execution_plan": loaded,
        "warnings": sorted(set(warnings)),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }


def prepare_project_validation_execution_plan(config: AppConfig, project_id: str) -> dict[str, Any]:
    normalized_project_id = str(project_id or "").strip()
    dispatch_result = read_project_agent_dispatch_plan(config, normalized_project_id)
    if not dispatch_result.get("agent_dispatch_plan_exists", False):
        return _error(
            "agent_dispatch_plan_not_found",
            {
                "message": "Agent dispatch plan must be approved before preparing validation execution plan.",
                "project_id": normalized_project_id,
                "agent_dispatch_plan_path": dispatch_result.get("agent_dispatch_plan_path", ""),
            },
        )
    dispatch_plan = dict(dispatch_result.get("agent_dispatch_plan", {}))
    if str(dispatch_plan.get("lifecycle_state", "")).strip() != "agent_dispatch_plan_approved":
        return _error(
            "agent_dispatch_plan_not_approved",
            {
                "message": "Agent dispatch plan must be approved before preparing validation execution plan.",
                "project_id": normalized_project_id,
            },
        )
    now = _now_iso()
    plan_path = resolve_project_validation_execution_plan_path(config.repo_root, normalized_project_id)
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    existing_created_at = ""
    if plan_path.exists():
        try:
            existing_raw = json.loads(plan_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            existing_raw = {}
        if isinstance(existing_raw, dict):
            existing_created_at = str(existing_raw.get("created_at", "")).strip()

    dispatch_core = dispatch_plan.get("dispatch_plan", {}) if isinstance(dispatch_plan.get("dispatch_plan"), dict) else {}
    dispatch_items = [item for item in dispatch_core.get("dispatch_items", []) if isinstance(item, dict)]
    agent_queues = [item for item in dispatch_core.get("agent_queues", []) if isinstance(item, dict)]
    input_payload = dispatch_plan.get("input", {}) if isinstance(dispatch_plan.get("input"), dict) else {}
    metadata = input_payload.get("repo_project_metadata", {}) if isinstance(input_payload.get("repo_project_metadata"), dict) else {}
    validation_items: list[dict[str, Any]] = []
    for index, dispatch_item in enumerate(dispatch_items, start=1):
        commands = _normalize_text_list(dispatch_item.get("validation_commands"))
        validation_type = "manual_review"
        if commands:
            first = commands[0].lower()
            if "pytest" in first or "unit" in first:
                validation_type = "unit_tests"
            elif "integration" in first:
                validation_type = "integration_tests"
            elif "lint" in first:
                validation_type = "lint"
            elif "format" in first or "black" in first or "prettier" in first:
                validation_type = "formatting"
        validation_items.append(
            {
                "validation_id": f"V{index}",
                "dispatch_id": str(dispatch_item.get("dispatch_id", "")).strip(),
                "local_issue_id": str(dispatch_item.get("local_issue_id", "")).strip(),
                "title": str(dispatch_item.get("title", "")).strip(),
                "validation_type": validation_type,
                "priority": str(dispatch_item.get("priority", "")).strip() or "normal",
                "validation_commands": commands,
                "acceptance_criteria": _normalize_text_list(dispatch_item.get("acceptance_criteria")),
                "expected_evidence": [
                    "Command output logs captured locally." if commands else "Manual reviewer notes captured locally.",
                    "Acceptance criteria checklist confirmation.",
                ],
                "execution_status": "not_executed",
                "evidence_status": "not_collected",
                "safety_notes": ["Local validation plan only; no validation execution performed."],
            }
        )
    group_map: dict[str, dict[str, Any]] = {}
    for item in validation_items:
        validation_type = str(item.get("validation_type", "")).strip() or "manual_review"
        group = group_map.setdefault(
            validation_type,
            {"group_id": f"G-{validation_type}", "title": validation_type.replace("_", " ").title(), "validation_type": validation_type, "item_count": 0, "validation_ids": []},
        )
        group["item_count"] += 1
        group["validation_ids"].append(str(item.get("validation_id", "")).strip())
    evidence_expectations: list[dict[str, Any]] = []
    for item in validation_items:
        validation_id = str(item.get("validation_id", "")).strip()
        evidence_expectations.append(
            {
                "evidence_id": f"E-{validation_id}",
                "validation_id": validation_id,
                "evidence_type": "validation_record",
                "description": f"Collect local evidence for {validation_id}.",
                "required": True,
                "status": "not_collected",
            }
        )
    plan = {
        "schema_version": "1.0",
        "project_id": normalized_project_id,
        "created_at": existing_created_at or now,
        "updated_at": now,
        "lifecycle_state": "validation_execution_plan_prepared",
        "source": "local_project_factory",
        "input": {
            "approved_agent_dispatch_plan_summary": str(dispatch_plan.get("dispatch_summary", "")).strip(),
            "dispatch_items": dispatch_items,
            "agent_queues": agent_queues,
            "repo_project_metadata": {
                "github_owner": str(metadata.get("github_owner", "")).strip(),
                "github_repo": str(metadata.get("github_repo", "")).strip(),
                "github_url": str(metadata.get("github_url", "")).strip(),
                "default_branch": str(metadata.get("default_branch", "")).strip(),
                "github_mode": str(metadata.get("github_mode", "")).strip(),
            },
        },
        "validation_plan": {
            "validation_items": validation_items,
            "validation_groups": list(group_map.values()),
            "evidence_expectations": evidence_expectations,
            "sequencing_notes": [],
            "dependency_notes": [],
        },
        "validation_summary": "",
        "operator_notes": "",
        "sequencing_notes": [],
        "dependency_notes": [],
        "approval_conditions": ["Validation execution requires explicit operator approval."],
        "known_risks": [],
        "manual_validation_notes": [],
        "local_only": True,
        "validation_execution_status": "not_requested",
        "agent_execution_status": "not_requested",
        "model_execution_status": "not_requested",
        "github_mutation_status": "not_requested",
        "requires_explicit_validation_execution_approval": True,
        "next_recommended_action": "review_validation_execution_plan",
        "audit_trail": [],
    }
    _append_validation_execution_plan_audit_entry(
        plan,
        event_type="validation_execution_plan_prepared",
        lifecycle_state="validation_execution_plan_prepared",
        summary="Validation execution plan prepared locally from approved agent dispatch plan.",
    )
    plan_path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    dossier_result = read_project_factory_dossier(config, normalized_project_id)
    dossier = dict(dossier_result.get("dossier", {})) if dossier_result.get("dossier_exists", False) else {}
    if dossier:
        dossier["lifecycle_state"] = "validation_execution_plan_prepared"
        dossier["next_recommended_action"] = "review_validation_execution_plan"
        dossier["updated_at"] = now
        create_project_factory_dossier(config, dossier)
    return {
        "ok": True,
        "local_only": True,
        "project_id": normalized_project_id,
        "validation_execution_plan": plan,
        "validation_execution_plan_path": str(plan_path),
        "dossier_path": str(resolve_project_factory_dossier_path(config.repo_root, normalized_project_id)),
        "warnings": sorted(set(dispatch_result.get("warnings", []))),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }


def update_project_validation_execution_plan(config: AppConfig, project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    plan_result = read_project_validation_execution_plan(config, project_id)
    normalized_project_id = str(plan_result.get("project_id", "")).strip()
    if not plan_result.get("validation_execution_plan_exists", False):
        return _error(
            "validation_execution_plan_not_found",
            {
                "message": "Validation execution plan must be prepared before updating draft fields.",
                "project_id": normalized_project_id,
                "validation_execution_plan_path": plan_result.get("validation_execution_plan_path", ""),
            },
        )
    plan = dict(plan_result.get("validation_execution_plan", {}))
    now = _now_iso()
    for field in ("validation_summary", "operator_notes"):
        if field in payload:
            plan[field] = str(payload.get(field, "")).strip()
    for field in ("sequencing_notes", "dependency_notes", "approval_conditions", "known_risks", "manual_validation_notes"):
        if field in payload:
            plan[field] = _normalize_text_list(payload.get(field))
    plan["lifecycle_state"] = "validation_execution_plan_draft_updated"
    plan["updated_at"] = now
    plan["local_only"] = True
    plan["validation_execution_status"] = "not_requested"
    plan["agent_execution_status"] = "not_requested"
    plan["model_execution_status"] = "not_requested"
    plan["github_mutation_status"] = "not_requested"
    plan["requires_explicit_validation_execution_approval"] = True
    validation_plan = plan.get("validation_plan", {}) if isinstance(plan.get("validation_plan"), dict) else {}
    validation_plan["sequencing_notes"] = _normalize_text_list(plan.get("sequencing_notes"))
    validation_plan["dependency_notes"] = _normalize_text_list(plan.get("dependency_notes"))
    plan["validation_plan"] = validation_plan
    plan["next_recommended_action"] = "approve_validation_execution_plan_or_continue_editing"
    _append_validation_execution_plan_audit_entry(
        plan,
        event_type="validation_execution_plan_draft_updated",
        lifecycle_state="validation_execution_plan_draft_updated",
        summary="Validation execution plan draft fields were updated locally.",
    )
    plan_path = resolve_project_validation_execution_plan_path(config.repo_root, normalized_project_id)
    plan_path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    dossier_result = read_project_factory_dossier(config, normalized_project_id)
    dossier = dict(dossier_result.get("dossier", {})) if dossier_result.get("dossier_exists", False) else {}
    if dossier:
        dossier["lifecycle_state"] = "validation_execution_plan_draft_updated"
        dossier["next_recommended_action"] = "approve_validation_execution_plan_or_continue_editing"
        dossier["updated_at"] = now
        create_project_factory_dossier(config, dossier)
    return {
        "ok": True,
        "local_only": True,
        "project_id": normalized_project_id,
        "validation_execution_plan": plan,
        "validation_execution_plan_path": str(plan_path),
        "dossier_path": str(resolve_project_factory_dossier_path(config.repo_root, normalized_project_id)),
        "warnings": sorted(set(plan_result.get("warnings", []))),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }


def approve_project_validation_execution_plan(config: AppConfig, project_id: str, approval_payload: dict[str, Any]) -> dict[str, Any]:
    plan_result = read_project_validation_execution_plan(config, project_id)
    normalized_project_id = str(plan_result.get("project_id", "")).strip()
    if not plan_result.get("validation_execution_plan_exists", False):
        return _error(
            "validation_execution_plan_not_found",
            {
                "message": "Validation execution plan must be prepared before approval.",
                "project_id": normalized_project_id,
                "validation_execution_plan_path": plan_result.get("validation_execution_plan_path", ""),
            },
        )
    plan = dict(plan_result.get("validation_execution_plan", {}))
    summary = str(plan.get("validation_summary", "")).strip()
    validation_plan = plan.get("validation_plan", {}) if isinstance(plan.get("validation_plan"), dict) else {}
    validation_items = [item for item in validation_plan.get("validation_items", []) if isinstance(item, dict)]
    evidence_expectations = [item for item in validation_plan.get("evidence_expectations", []) if isinstance(item, dict)]
    approval_conditions = _normalize_text_list(plan.get("approval_conditions"))
    if not summary:
        return _error("validation_execution_plan_approval_validation_failed", {"message": "Validation plan approval requires a non-empty validation_summary."})
    if not validation_items:
        return _error("validation_execution_plan_approval_validation_failed", {"message": "Validation plan approval requires at least one validation item."})
    required_item_fields = ("validation_id", "dispatch_id", "title", "validation_type", "execution_status")
    for item in validation_items:
        for field in required_item_fields:
            if not str(item.get(field, "")).strip():
                return _error("validation_execution_plan_approval_validation_failed", {"message": f"Validation item is missing required field: {field}."})
        if str(item.get("execution_status", "")).strip() != "not_executed":
            return _error("validation_execution_plan_approval_validation_failed", {"message": "All validation item execution_status values must remain not_executed."})
        if str(item.get("evidence_status", "")).strip() != "not_collected":
            return _error("validation_execution_plan_approval_validation_failed", {"message": "All validation item evidence_status values must remain not_collected."})
    for item in evidence_expectations:
        if str(item.get("status", "")).strip() != "not_collected":
            return _error("validation_execution_plan_approval_validation_failed", {"message": "All evidence expectation statuses must remain not_collected."})
    if not any("validation execution approval" in value.lower() or "validation execution requires explicit operator approval" in value.lower() for value in approval_conditions):
        return _error(
            "validation_execution_plan_approval_validation_failed",
            {"message": "Approval conditions must explicitly mention validation execution approval."},
        )
    now = _now_iso()
    plan["validation_summary"] = summary
    plan["approval_conditions"] = approval_conditions
    plan["lifecycle_state"] = "validation_execution_plan_approved"
    plan["updated_at"] = now
    plan["approved_at"] = now
    plan["approved_by"] = str(approval_payload.get("approved_by", "")).strip() or "local_operator"
    plan["local_only"] = True
    plan["validation_execution_status"] = "not_requested"
    plan["agent_execution_status"] = "not_requested"
    plan["model_execution_status"] = "not_requested"
    plan["github_mutation_status"] = "not_requested"
    plan["requires_explicit_validation_execution_approval"] = True
    plan["next_recommended_action"] = "prepare_documentation_closeout_plan"
    _append_validation_execution_plan_audit_entry(
        plan,
        event_type="validation_execution_plan_approved",
        lifecycle_state="validation_execution_plan_approved",
        summary="Validation execution plan approved locally; no validation commands or execution performed.",
    )
    plan_path = resolve_project_validation_execution_plan_path(config.repo_root, normalized_project_id)
    plan_path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    dossier_result = read_project_factory_dossier(config, normalized_project_id)
    dossier = dict(dossier_result.get("dossier", {})) if dossier_result.get("dossier_exists", False) else {}
    if dossier:
        dossier["lifecycle_state"] = "validation_execution_plan_approved"
        dossier["next_recommended_action"] = "prepare_documentation_closeout_plan"
        dossier["updated_at"] = now
        create_project_factory_dossier(config, dossier)
    return {
        "ok": True,
        "local_only": True,
        "project_id": normalized_project_id,
        "validation_execution_plan": plan,
        "validation_execution_plan_path": str(plan_path),
        "dossier_path": str(resolve_project_factory_dossier_path(config.repo_root, normalized_project_id)),
        "warnings": sorted(set(plan_result.get("warnings", []))),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }


def read_project_documentation_closeout_plan(config: AppConfig, project_id: str) -> dict[str, Any]:
    normalized_project_id = str(project_id or "").strip()
    plan_path = resolve_project_documentation_closeout_plan_path(config.repo_root, normalized_project_id)
    warnings: list[str] = []
    if not plan_path.exists():
        warnings.append(f"Documentation closeout plan not found for project: {normalized_project_id}")
        return {
            "ok": True,
            "local_only": True,
            "project_id": normalized_project_id,
            "documentation_closeout_plan_path": str(plan_path),
            "documentation_closeout_plan_exists": False,
            "documentation_closeout_plan": {},
            "warnings": warnings,
            "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
        }
    try:
        loaded = json.loads(plan_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        warnings.append(f"Documentation closeout plan could not be parsed: {exc}")
        loaded = {}
    if not isinstance(loaded, dict):
        warnings.append("Documentation closeout plan has invalid schema; expected JSON object.")
        loaded = {}
    return {
        "ok": True,
        "local_only": True,
        "project_id": normalized_project_id,
        "documentation_closeout_plan_path": str(plan_path),
        "documentation_closeout_plan_exists": bool(loaded),
        "documentation_closeout_plan": loaded,
        "warnings": sorted(set(warnings)),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }


def prepare_project_documentation_closeout_plan(config: AppConfig, project_id: str) -> dict[str, Any]:
    normalized_project_id = str(project_id or "").strip()
    validation_result = read_project_validation_execution_plan(config, normalized_project_id)
    if not validation_result.get("validation_execution_plan_exists", False):
        return _error(
            "validation_execution_plan_not_found",
            {
                "message": "Validation execution plan must be approved before preparing documentation closeout plan.",
                "project_id": normalized_project_id,
                "validation_execution_plan_path": validation_result.get("validation_execution_plan_path", ""),
            },
        )
    validation_plan = dict(validation_result.get("validation_execution_plan", {}))
    if str(validation_plan.get("lifecycle_state", "")).strip() != "validation_execution_plan_approved":
        return _error(
            "validation_execution_plan_not_approved",
            {
                "message": "Validation execution plan must be approved before preparing documentation closeout plan.",
                "project_id": normalized_project_id,
            },
        )
    now = _now_iso()
    plan_path = resolve_project_documentation_closeout_plan_path(config.repo_root, normalized_project_id)
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    validation_core = validation_plan.get("validation_plan", {}) if isinstance(validation_plan.get("validation_plan"), dict) else {}
    validation_items = [item for item in validation_core.get("validation_items", []) if isinstance(item, dict)]
    validation_groups = [item for item in validation_core.get("validation_groups", []) if isinstance(item, dict)]
    evidence_expectations = [item for item in validation_core.get("evidence_expectations", []) if isinstance(item, dict)]
    validation_input = validation_plan.get("input", {}) if isinstance(validation_plan.get("input"), dict) else {}
    metadata = validation_input.get("repo_project_metadata", {}) if isinstance(validation_input.get("repo_project_metadata"), dict) else {}
    documentation_items = [
        {"documentation_id": "D1", "title": "BUILD_STATE update", "documentation_type": "build_state", "target_path": "BUILD_STATE.md", "description": "Capture the current local build state and summary notes.", "required": True, "execution_status": "not_executed", "evidence_status": "not_collected", "safety_notes": ["Local plan only; no documentation files are updated automatically."]},
        {"documentation_id": "D2", "title": "AGENT_CONTEXT update", "documentation_type": "agent_context", "target_path": "AGENT_CONTEXT.md", "description": "Record final agent context and handoff notes for closeout.", "required": True, "execution_status": "not_executed", "evidence_status": "not_collected", "safety_notes": ["Local plan only; no agent execution performed."]},
        {"documentation_id": "D3", "title": "ROADMAP update", "documentation_type": "roadmap", "target_path": "ROADMAP.md", "description": "Refresh roadmap status for completed local planning gates.", "required": True, "execution_status": "not_executed", "evidence_status": "not_collected", "safety_notes": ["Local plan only; roadmap is not changed by this operator gate."]},
        {"documentation_id": "D4", "title": "LOCAL_OPERATOR_USAGE update", "documentation_type": "operator_usage", "target_path": "LOCAL_OPERATOR_USAGE.md", "description": "Document local operation instructions and boundaries for closeout.", "required": True, "execution_status": "not_executed", "evidence_status": "not_collected", "safety_notes": ["Local-only boundary remains enforced."]},
        {"documentation_id": "D5", "title": "Validation summary", "documentation_type": "validation_summary", "target_path": "VALIDATION_SUMMARY.md", "description": "Summarize approved validation plan scope and expected results.", "required": True, "execution_status": "not_executed", "evidence_status": "not_collected", "safety_notes": ["Validation remains not executed in this milestone."]},
        {"documentation_id": "D6", "title": "Evidence index", "documentation_type": "evidence_index", "target_path": "EVIDENCE_INDEX.md", "description": "Index expected evidence artifacts and validation references.", "required": True, "execution_status": "not_executed", "evidence_status": "not_collected", "safety_notes": ["Evidence collection is not performed by this gate."]},
        {"documentation_id": "D7", "title": "Closeout summary", "documentation_type": "closeout_summary", "target_path": "CLOSEOUT_SUMMARY.md", "description": "Capture final closeout narrative and remaining gated approvals.", "required": True, "execution_status": "not_executed", "evidence_status": "not_collected", "safety_notes": ["Closeout execution requires explicit approval outside this gate."]},
    ]
    evidence_packages = [
        {
            "evidence_package_id": f"EP{idx}",
            "title": str(evidence.get("description", "")).strip() or f"Evidence package {idx}",
            "source_validation_ids": [str(evidence.get("validation_id", "")).strip()] if str(evidence.get("validation_id", "")).strip() else [],
            "expected_evidence": [str(evidence.get("description", "")).strip()] if str(evidence.get("description", "")).strip() else [],
            "status": "not_collected",
            "required": bool(evidence.get("required", True)),
        }
        for idx, evidence in enumerate(evidence_expectations, start=1)
    ]
    closeout_checks = [
        {"check_id": "C1", "title": "Validation plan approved", "description": "Validation execution plan is approved as a local plan-only prerequisite.", "status": "pending", "required": True},
        {"check_id": "C2", "title": "Evidence expectations identified", "description": "Evidence expectations are captured for local closeout planning.", "status": "pending", "required": True},
        {"check_id": "C3", "title": "Documentation targets identified", "description": "Documentation targets required for closeout are listed.", "status": "pending", "required": True},
        {"check_id": "C4", "title": "GitHub execution not performed", "description": "GitHub mutations remain gated and not executed unless explicitly approved elsewhere.", "status": "pending", "required": True},
        {"check_id": "C5", "title": "Agent/model execution not performed", "description": "Agent/model execution remains gated and not executed unless explicitly approved elsewhere.", "status": "pending", "required": True},
    ]
    plan = {
        "schema_version": "1.0",
        "project_id": normalized_project_id,
        "created_at": now,
        "updated_at": now,
        "lifecycle_state": "documentation_closeout_plan_prepared",
        "source": "local_project_factory",
        "input": {
            "approved_validation_execution_plan_summary": str(validation_plan.get("validation_summary", "")).strip(),
            "validation_items": validation_items,
            "validation_groups": validation_groups,
            "evidence_expectations": evidence_expectations,
            "repo_project_metadata": {
                "github_owner": str(metadata.get("github_owner", "")).strip(),
                "github_repo": str(metadata.get("github_repo", "")).strip(),
                "github_url": str(metadata.get("github_url", "")).strip(),
                "default_branch": str(metadata.get("default_branch", "")).strip(),
                "github_mode": str(metadata.get("github_mode", "")).strip(),
            },
        },
        "documentation_plan": {
            "documentation_items": documentation_items,
            "evidence_packages": evidence_packages,
            "closeout_checks": closeout_checks,
            "sequencing_notes": [],
            "dependency_notes": [],
        },
        "closeout_summary": "",
        "operator_notes": "",
        "sequencing_notes": [],
        "dependency_notes": [],
        "approval_conditions": ["Documentation execution and project closeout require explicit operator approval."],
        "known_risks": [],
        "documentation_update_notes": [],
        "evidence_collection_notes": [],
        "local_only": True,
        "documentation_execution_status": "not_requested",
        "validation_execution_status": "not_requested",
        "agent_execution_status": "not_requested",
        "model_execution_status": "not_requested",
        "github_mutation_status": "not_requested",
        "requires_explicit_documentation_execution_approval": True,
        "requires_explicit_closeout_approval": True,
        "next_recommended_action": "review_documentation_closeout_plan",
        "audit_trail": [],
    }
    _append_documentation_closeout_plan_audit_entry(
        plan,
        event_type="documentation_closeout_plan_prepared",
        lifecycle_state="documentation_closeout_plan_prepared",
        summary="Documentation closeout plan prepared locally from approved validation execution plan.",
    )
    plan_path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    dossier_result = read_project_factory_dossier(config, normalized_project_id)
    dossier = dict(dossier_result.get("dossier", {})) if dossier_result.get("dossier_exists", False) else {}
    if dossier:
        dossier["lifecycle_state"] = "documentation_closeout_plan_prepared"
        dossier["next_recommended_action"] = "review_documentation_closeout_plan"
        dossier["updated_at"] = now
        create_project_factory_dossier(config, dossier)
    return {
        "ok": True,
        "local_only": True,
        "project_id": normalized_project_id,
        "documentation_closeout_plan": plan,
        "documentation_closeout_plan_path": str(plan_path),
        "dossier_path": str(resolve_project_factory_dossier_path(config.repo_root, normalized_project_id)),
        "warnings": sorted(set(validation_result.get("warnings", []))),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }


def update_project_documentation_closeout_plan(config: AppConfig, project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    plan_result = read_project_documentation_closeout_plan(config, project_id)
    normalized_project_id = str(plan_result.get("project_id", "")).strip()
    if not plan_result.get("documentation_closeout_plan_exists", False):
        return _error(
            "documentation_closeout_plan_not_found",
            {
                "message": "Documentation closeout plan must be prepared before updating draft fields.",
                "project_id": normalized_project_id,
                "documentation_closeout_plan_path": plan_result.get("documentation_closeout_plan_path", ""),
            },
        )
    plan = dict(plan_result.get("documentation_closeout_plan", {}))
    now = _now_iso()
    for field in ("closeout_summary", "operator_notes"):
        if field in payload:
            plan[field] = str(payload.get(field, "")).strip()
    for field in ("sequencing_notes", "dependency_notes", "approval_conditions", "known_risks", "documentation_update_notes", "evidence_collection_notes"):
        if field in payload:
            plan[field] = _normalize_text_list(payload.get(field))
    plan["lifecycle_state"] = "documentation_closeout_plan_draft_updated"
    plan["updated_at"] = now
    plan["documentation_execution_status"] = "not_requested"
    plan["validation_execution_status"] = "not_requested"
    plan["agent_execution_status"] = "not_requested"
    plan["model_execution_status"] = "not_requested"
    plan["github_mutation_status"] = "not_requested"
    plan["next_recommended_action"] = "approve_documentation_closeout_plan_or_continue_editing"
    _append_documentation_closeout_plan_audit_entry(
        plan,
        event_type="documentation_closeout_plan_draft_updated",
        lifecycle_state="documentation_closeout_plan_draft_updated",
        summary="Documentation closeout plan draft fields were updated locally.",
    )
    plan_path = resolve_project_documentation_closeout_plan_path(config.repo_root, normalized_project_id)
    plan_path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    dossier_result = read_project_factory_dossier(config, normalized_project_id)
    dossier = dict(dossier_result.get("dossier", {})) if dossier_result.get("dossier_exists", False) else {}
    if dossier:
        dossier["lifecycle_state"] = "documentation_closeout_plan_draft_updated"
        dossier["next_recommended_action"] = "approve_documentation_closeout_plan_or_continue_editing"
        dossier["updated_at"] = now
        create_project_factory_dossier(config, dossier)
    return {
        "ok": True,
        "local_only": True,
        "project_id": normalized_project_id,
        "documentation_closeout_plan": plan,
        "documentation_closeout_plan_path": str(plan_path),
        "dossier_path": str(resolve_project_factory_dossier_path(config.repo_root, normalized_project_id)),
        "warnings": sorted(set(plan_result.get("warnings", []))),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }


def approve_project_documentation_closeout_plan(config: AppConfig, project_id: str, approval_payload: dict[str, Any]) -> dict[str, Any]:
    plan_result = read_project_documentation_closeout_plan(config, project_id)
    normalized_project_id = str(plan_result.get("project_id", "")).strip()
    if not plan_result.get("documentation_closeout_plan_exists", False):
        return _error(
            "documentation_closeout_plan_not_found",
            {
                "message": "Documentation closeout plan must be prepared before approval.",
                "project_id": normalized_project_id,
                "documentation_closeout_plan_path": plan_result.get("documentation_closeout_plan_path", ""),
            },
        )
    plan = dict(plan_result.get("documentation_closeout_plan", {}))
    closeout_summary = str(plan.get("closeout_summary", "")).strip()
    documentation_plan = plan.get("documentation_plan", {}) if isinstance(plan.get("documentation_plan"), dict) else {}
    documentation_items = [item for item in documentation_plan.get("documentation_items", []) if isinstance(item, dict)]
    evidence_packages = [item for item in documentation_plan.get("evidence_packages", []) if isinstance(item, dict)]
    closeout_checks = [item for item in documentation_plan.get("closeout_checks", []) if isinstance(item, dict)]
    approval_conditions = _normalize_text_list(plan.get("approval_conditions"))
    if not closeout_summary:
        return _error("documentation_closeout_plan_approval_validation_failed", {"message": "Closeout plan approval requires a non-empty closeout_summary."})
    if not documentation_items:
        return _error("documentation_closeout_plan_approval_validation_failed", {"message": "Closeout plan approval requires at least one documentation item."})
    if not closeout_checks:
        return _error("documentation_closeout_plan_approval_validation_failed", {"message": "Closeout plan approval requires at least one closeout check."})
    if not evidence_packages and not any("no evidence package" in note.lower() for note in _normalize_text_list(plan.get("evidence_collection_notes"))):
        return _error("documentation_closeout_plan_approval_validation_failed", {"message": "Closeout plan approval requires at least one evidence package or an explicit note explaining no evidence package is required."})
    if not all(str(item.get("execution_status", "")).strip() == "not_executed" for item in documentation_items):
        return _error("documentation_closeout_plan_approval_validation_failed", {"message": "All documentation item execution_status values must remain not_executed."})
    if not all(str(item.get("evidence_status", "")).strip() == "not_collected" for item in documentation_items):
        return _error("documentation_closeout_plan_approval_validation_failed", {"message": "All documentation item evidence_status values must remain not_collected."})
    if not all(str(item.get("status", "")).strip() == "not_collected" for item in evidence_packages):
        return _error("documentation_closeout_plan_approval_validation_failed", {"message": "All evidence package statuses must remain not_collected."})
    if not any(("documentation execution approval" in value.lower() or "closeout approval" in value.lower() or "explicit operator approval" in value.lower()) for value in approval_conditions):
        return _error("documentation_closeout_plan_approval_validation_failed", {"message": "Approval conditions must explicitly mention documentation execution approval or closeout approval."})
    now = _now_iso()
    plan["lifecycle_state"] = "documentation_closeout_plan_approved"
    plan["updated_at"] = now
    plan["approved_at"] = now
    plan["approved_by"] = str(approval_payload.get("approved_by", "")).strip() or "local_operator"
    plan["documentation_execution_status"] = "not_requested"
    plan["validation_execution_status"] = "not_requested"
    plan["agent_execution_status"] = "not_requested"
    plan["model_execution_status"] = "not_requested"
    plan["github_mutation_status"] = "not_requested"
    plan["next_recommended_action"] = "await_explicit_execution_phase_approval"
    _append_documentation_closeout_plan_audit_entry(
        plan,
        event_type="documentation_closeout_plan_approved",
        lifecycle_state="documentation_closeout_plan_approved",
        summary="Documentation closeout plan approved locally; no documentation or execution actions performed.",
    )
    plan_path = resolve_project_documentation_closeout_plan_path(config.repo_root, normalized_project_id)
    plan_path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    dossier_result = read_project_factory_dossier(config, normalized_project_id)
    dossier = dict(dossier_result.get("dossier", {})) if dossier_result.get("dossier_exists", False) else {}
    if dossier:
        dossier["lifecycle_state"] = "documentation_closeout_plan_approved"
        dossier["next_recommended_action"] = "await_explicit_execution_phase_approval"
        dossier["updated_at"] = now
        create_project_factory_dossier(config, dossier)
    return {
        "ok": True,
        "local_only": True,
        "project_id": normalized_project_id,
        "documentation_closeout_plan": plan,
        "documentation_closeout_plan_path": str(plan_path),
        "dossier_path": str(resolve_project_factory_dossier_path(config.repo_root, normalized_project_id)),
        "warnings": sorted(set(plan_result.get("warnings", []))),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }


def read_project_execution_phase_approval(config: AppConfig, project_id: str) -> dict[str, Any]:
    normalized_project_id = str(project_id or "").strip()
    approval_path = resolve_project_execution_phase_approval_path(config.repo_root, normalized_project_id)
    warnings: list[str] = []
    if not approval_path.exists():
        warnings.append(f"Execution phase approval not found for project: {normalized_project_id}")
        return {
            "ok": True,
            "local_only": True,
            "project_id": normalized_project_id,
            "execution_phase_approval_path": str(approval_path),
            "execution_phase_approval_exists": False,
            "execution_phase_approval": {},
            "warnings": warnings,
            "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
        }
    try:
        loaded = json.loads(approval_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        warnings.append(f"Execution phase approval could not be parsed: {exc}")
        loaded = {}
    if not isinstance(loaded, dict):
        warnings.append("Execution phase approval has invalid schema; expected JSON object.")
        loaded = {}
    return {
        "ok": True,
        "local_only": True,
        "project_id": normalized_project_id,
        "execution_phase_approval_path": str(approval_path),
        "execution_phase_approval_exists": bool(loaded),
        "execution_phase_approval": loaded,
        "warnings": sorted(set(warnings)),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }


def read_project_execution_readiness(config: AppConfig, project_id: str) -> dict[str, Any]:
    normalized_project_id = str(project_id or "").strip()
    active_payload = inspect_active_project(config)
    active_project_id = str(active_payload.get("active_project_id", "")).strip()
    active_project = active_payload.get("active_project", {}) if isinstance(active_payload.get("active_project"), dict) else {}

    dossier_payload = read_project_factory_dossier(config, normalized_project_id)
    scope_payload = read_project_scope_package(config, normalized_project_id)
    architecture_payload = read_project_architecture_contract(config, normalized_project_id)
    milestone_payload = read_project_milestone_issue_plan(config, normalized_project_id)
    github_payload = read_project_github_apply_plan(config, normalized_project_id)
    dispatch_payload = read_project_agent_dispatch_plan(config, normalized_project_id)
    validation_payload = read_project_validation_execution_plan(config, normalized_project_id)
    closeout_payload = read_project_documentation_closeout_plan(config, normalized_project_id)
    execution_payload = read_project_execution_phase_approval(config, normalized_project_id)

    artifact_summary = {
        "factory_dossier": _artifact_summary_entry(
            key="factory_dossier",
            exists=bool(dossier_payload.get("dossier_exists", False)),
            lifecycle_state=str((dossier_payload.get("dossier", {}) or {}).get("lifecycle_state", "")).strip(),
            approved=False,
            path=str(dossier_payload.get("dossier_path", "")),
        ),
        "scope_package": _artifact_summary_entry(
            key="scope_package",
            exists=bool(scope_payload.get("scope_package_exists", False)),
            lifecycle_state=str((scope_payload.get("scope_package", {}) or {}).get("lifecycle_state", "")).strip(),
            approved=str((scope_payload.get("scope_package", {}) or {}).get("lifecycle_state", "")).strip() == "scope_approved",
            path=str(scope_payload.get("scope_package_path", "")),
        ),
        "architecture_contract": _artifact_summary_entry(
            key="architecture_contract",
            exists=bool(architecture_payload.get("architecture_contract_exists", False)),
            lifecycle_state=str((architecture_payload.get("architecture_contract", {}) or {}).get("lifecycle_state", "")).strip(),
            approved=str((architecture_payload.get("architecture_contract", {}) or {}).get("lifecycle_state", "")).strip() == "architecture_approved",
            path=str(architecture_payload.get("architecture_contract_path", "")),
        ),
        "milestone_issue_plan": _artifact_summary_entry(
            key="milestone_issue_plan",
            exists=bool(milestone_payload.get("milestone_issue_plan_exists", False)),
            lifecycle_state=str((milestone_payload.get("milestone_issue_plan", {}) or {}).get("lifecycle_state", "")).strip(),
            approved=str((milestone_payload.get("milestone_issue_plan", {}) or {}).get("lifecycle_state", "")).strip() == "milestone_issue_plan_approved",
            path=str(milestone_payload.get("milestone_issue_plan_path", "")),
        ),
        "github_apply_plan": _artifact_summary_entry(
            key="github_apply_plan",
            exists=bool(github_payload.get("github_apply_plan_exists", False)),
            lifecycle_state=str((github_payload.get("github_apply_plan", {}) or {}).get("lifecycle_state", "")).strip(),
            approved=str((github_payload.get("github_apply_plan", {}) or {}).get("lifecycle_state", "")).strip() == "github_apply_plan_approved",
            path=str(github_payload.get("github_apply_plan_path", "")),
        ),
        "agent_dispatch_plan": _artifact_summary_entry(
            key="agent_dispatch_plan",
            exists=bool(dispatch_payload.get("agent_dispatch_plan_exists", False)),
            lifecycle_state=str((dispatch_payload.get("agent_dispatch_plan", {}) or {}).get("lifecycle_state", "")).strip(),
            approved=str((dispatch_payload.get("agent_dispatch_plan", {}) or {}).get("lifecycle_state", "")).strip() == "agent_dispatch_plan_approved",
            path=str(dispatch_payload.get("agent_dispatch_plan_path", "")),
        ),
        "validation_execution_plan": _artifact_summary_entry(
            key="validation_execution_plan",
            exists=bool(validation_payload.get("validation_execution_plan_exists", False)),
            lifecycle_state=str((validation_payload.get("validation_execution_plan", {}) or {}).get("lifecycle_state", "")).strip(),
            approved=str((validation_payload.get("validation_execution_plan", {}) or {}).get("lifecycle_state", "")).strip() == "validation_execution_plan_approved",
            path=str(validation_payload.get("validation_execution_plan_path", "")),
        ),
        "documentation_closeout_plan": _artifact_summary_entry(
            key="documentation_closeout_plan",
            exists=bool(closeout_payload.get("documentation_closeout_plan_exists", False)),
            lifecycle_state=str((closeout_payload.get("documentation_closeout_plan", {}) or {}).get("lifecycle_state", "")).strip(),
            approved=str((closeout_payload.get("documentation_closeout_plan", {}) or {}).get("lifecycle_state", "")).strip() == "documentation_closeout_plan_approved",
            path=str(closeout_payload.get("documentation_closeout_plan_path", "")),
        ),
        "execution_phase_approval": _artifact_summary_entry(
            key="execution_phase_approval",
            exists=bool(execution_payload.get("execution_phase_approval_exists", False)),
            lifecycle_state=str((execution_payload.get("execution_phase_approval", {}) or {}).get("lifecycle_state", "")).strip(),
            approved=str((execution_payload.get("execution_phase_approval", {}) or {}).get("lifecycle_state", "")).strip() == "execution_phase_approval_approved",
            path=str(execution_payload.get("execution_phase_approval_path", "")),
        ),
    }

    lane_summary = _build_lane_summary(execution_payload.get("execution_phase_approval", {}))
    blockers: list[str] = []
    warnings: list[str] = []
    required_missing = [key for key in ("factory_dossier", "scope_package", "architecture_contract", "milestone_issue_plan", "github_apply_plan", "agent_dispatch_plan", "validation_execution_plan", "documentation_closeout_plan") if not artifact_summary[key]["exists"]]
    if required_missing:
        blockers.append(f"Missing required artifacts: {', '.join(required_missing)}.")
    for artifact in artifact_summary.values():
        blockers.extend(list(artifact.get("blockers", [])))
        warnings.extend(list(artifact.get("warnings", [])))
    for lane in lane_summary.values():
        blockers.extend(list(lane.get("blockers", [])))
        warnings.extend(list(lane.get("warnings", [])))

    execution_artifact = artifact_summary["execution_phase_approval"]
    lane_approved_count = sum(1 for lane in lane_summary.values() if lane.get("approved", False))
    if required_missing:
        overall_status = "blocked"
        overall_summary = "Execution readiness is blocked because required planning artifacts are missing."
        next_safe_action = "prepare_missing_factory_artifacts"
    elif not execution_artifact["exists"] or not execution_artifact["approved"]:
        overall_status = "pending_approval"
        overall_summary = "Execution readiness is pending execution phase approval."
        next_safe_action = "prepare_or_approve_execution_phase_approval"
    elif lane_approved_count == 0:
        overall_status = "plan_only_approved"
        overall_summary = "Execution phase approval is approved, but all execution lanes remain blocked."
        next_safe_action = "approve_at_least_one_execution_lane_or_keep_plan_only"
    else:
        overall_status = "execution_lanes_approved"
        overall_summary = "Execution readiness includes one or more approved execution lanes."
        next_safe_action = "execute_only_explicitly_approved_lanes"

    return {
        "ok": True,
        "local_only": True,
        "project_id": normalized_project_id,
        "project_name": str(active_project.get("name", "")).strip() if str(active_project_id) == normalized_project_id else str((dossier_payload.get("dossier", {}) or {}).get("name", "")).strip(),
        "active_project": bool(active_project_id and active_project_id == normalized_project_id),
        "overall_status": overall_status,
        "overall_summary": overall_summary,
        "next_safe_action": next_safe_action,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "artifact_summary": artifact_summary,
        "lane_summary": lane_summary,
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }


def prepare_project_execution_phase_approval(config: AppConfig, project_id: str) -> dict[str, Any]:
    normalized_project_id = str(project_id or "").strip()
    closeout_result = read_project_documentation_closeout_plan(config, normalized_project_id)
    if not closeout_result.get("documentation_closeout_plan_exists", False):
        return _error(
            "documentation_closeout_plan_not_found",
            {
                "message": "Documentation closeout plan must be approved before preparing execution phase approval.",
                "project_id": normalized_project_id,
                "documentation_closeout_plan_path": closeout_result.get("documentation_closeout_plan_path", ""),
            },
        )
    closeout_plan = dict(closeout_result.get("documentation_closeout_plan", {}))
    if str(closeout_plan.get("lifecycle_state", "")).strip() != "documentation_closeout_plan_approved":
        return _error(
            "documentation_closeout_plan_not_approved",
            {
                "message": "Documentation closeout plan must be approved before preparing execution phase approval.",
                "project_id": normalized_project_id,
            },
        )
    now = _now_iso()
    approval_path = resolve_project_execution_phase_approval_path(config.repo_root, normalized_project_id)
    approval_path.parent.mkdir(parents=True, exist_ok=True)
    lanes = [
        {
            "lane_id": "github_mutation_execution",
            "status": "blocked",
            "summary": "GitHub milestone/issue mutations remain blocked until explicitly approved.",
            "warnings": ["No GitHub API or gh mutations are executed by this gate."],
            "required_acknowledgement": "Acknowledge GitHub mutation execution remains disabled unless explicitly approved.",
            "acknowledgement_text": "",
        },
        {
            "lane_id": "validation_command_execution",
            "status": "blocked",
            "summary": "Validation command execution remains blocked until explicitly approved.",
            "warnings": ["No validation commands are executed by this gate."],
            "required_acknowledgement": "Acknowledge validation command execution remains disabled unless explicitly approved.",
            "acknowledgement_text": "",
        },
        {
            "lane_id": "documentation_update_execution",
            "status": "blocked",
            "summary": "Documentation updates remain blocked until explicitly approved.",
            "warnings": ["No documentation files are changed by this gate."],
            "required_acknowledgement": "Acknowledge documentation updates remain disabled unless explicitly approved.",
            "acknowledgement_text": "",
        },
        {
            "lane_id": "agent_model_execution",
            "status": "blocked",
            "summary": "Agent/model execution remains blocked until explicitly approved.",
            "warnings": ["No local/cloud model or agent execution is performed by this gate."],
            "required_acknowledgement": "Acknowledge agent/model execution remains disabled unless explicitly approved.",
            "acknowledgement_text": "",
        },
        {
            "lane_id": "project_closeout_execution",
            "status": "blocked",
            "summary": "Project closeout execution remains blocked until explicitly approved.",
            "warnings": ["No closeout execution is performed by this gate."],
            "required_acknowledgement": "Acknowledge project closeout execution remains disabled unless explicitly approved.",
            "acknowledgement_text": "",
        },
    ]
    approval = {
        "schema_version": "1.0",
        "project_id": normalized_project_id,
        "created_at": now,
        "updated_at": now,
        "lifecycle_state": "execution_phase_approval_prepared",
        "source": "local_project_factory",
        "input": {
            "approved_documentation_closeout_plan_summary": str(closeout_plan.get("closeout_summary", "")).strip(),
            "documentation_plan_items_count": len((closeout_plan.get("documentation_plan", {}) or {}).get("documentation_items", [])),
            "evidence_package_count": len((closeout_plan.get("documentation_plan", {}) or {}).get("evidence_packages", [])),
            "closeout_check_count": len((closeout_plan.get("documentation_plan", {}) or {}).get("closeout_checks", [])),
        },
        "execution_lanes": lanes,
        "overall_acknowledgement": "",
        "approval_summary": "",
        "operator_notes": "",
        "local_only": True,
        "github_mutation_status": "not_requested",
        "validation_execution_status": "not_requested",
        "documentation_execution_status": "not_requested",
        "agent_execution_status": "not_requested",
        "model_execution_status": "not_requested",
        "project_closeout_status": "not_requested",
        "next_recommended_action": "review_execution_phase_approval",
        "audit_trail": [],
    }
    _append_execution_phase_approval_audit_entry(
        approval,
        event_type="execution_phase_approval_prepared",
        lifecycle_state="execution_phase_approval_prepared",
        summary="Execution phase approval prepared locally from approved documentation closeout plan.",
    )
    approval_path.write_text(json.dumps(approval, indent=2) + "\n", encoding="utf-8")
    dossier_result = read_project_factory_dossier(config, normalized_project_id)
    dossier = dict(dossier_result.get("dossier", {})) if dossier_result.get("dossier_exists", False) else {}
    if dossier:
        dossier["lifecycle_state"] = "execution_phase_approval_prepared"
        dossier["next_recommended_action"] = "review_execution_phase_approval"
        dossier["updated_at"] = now
        create_project_factory_dossier(config, dossier)
    return {
        "ok": True,
        "local_only": True,
        "project_id": normalized_project_id,
        "execution_phase_approval": approval,
        "execution_phase_approval_path": str(approval_path),
        "dossier_path": str(resolve_project_factory_dossier_path(config.repo_root, normalized_project_id)),
        "warnings": sorted(set(closeout_result.get("warnings", []))),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }


def update_project_execution_phase_approval(config: AppConfig, project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    approval_result = read_project_execution_phase_approval(config, project_id)
    normalized_project_id = str(approval_result.get("project_id", "")).strip()
    if not approval_result.get("execution_phase_approval_exists", False):
        return _error(
            "execution_phase_approval_not_found",
            {
                "message": "Execution phase approval must be prepared before updating draft fields.",
                "project_id": normalized_project_id,
                "execution_phase_approval_path": approval_result.get("execution_phase_approval_path", ""),
            },
        )
    approval = dict(approval_result.get("execution_phase_approval", {}))
    now = _now_iso()
    if "approval_summary" in payload:
        approval["approval_summary"] = str(payload.get("approval_summary", "")).strip()
    if "operator_notes" in payload:
        approval["operator_notes"] = str(payload.get("operator_notes", "")).strip()
    if "overall_acknowledgement" in payload:
        approval["overall_acknowledgement"] = str(payload.get("overall_acknowledgement", "")).strip()
    raw_lanes = payload.get("execution_lanes")
    existing_lanes = [item for item in approval.get("execution_lanes", []) if isinstance(item, dict)]
    if isinstance(raw_lanes, list):
        lane_map = {str(item.get("lane_id", "")).strip(): dict(item) for item in existing_lanes}
        for lane_update in raw_lanes:
            if not isinstance(lane_update, dict):
                continue
            lane_id = str(lane_update.get("lane_id", "")).strip()
            if not lane_id or lane_id not in lane_map:
                continue
            lane = dict(lane_map[lane_id])
            if "status" in lane_update:
                status = str(lane_update.get("status", "")).strip().lower()
                if status in {"blocked", "approved"}:
                    lane["status"] = status
            for field in ("summary", "required_acknowledgement", "acknowledgement_text"):
                if field in lane_update:
                    lane[field] = str(lane_update.get(field, "")).strip()
            if "warnings" in lane_update:
                lane["warnings"] = _normalize_text_list(lane_update.get("warnings"))
            lane_map[lane_id] = lane
        approval["execution_lanes"] = [lane_map[str(item.get("lane_id", "")).strip()] for item in existing_lanes if str(item.get("lane_id", "")).strip() in lane_map]
    approval["lifecycle_state"] = "execution_phase_approval_draft_updated"
    approval["updated_at"] = now
    approval["next_recommended_action"] = "approve_execution_phase_approval_or_continue_editing"
    _append_execution_phase_approval_audit_entry(
        approval,
        event_type="execution_phase_approval_draft_updated",
        lifecycle_state="execution_phase_approval_draft_updated",
        summary="Execution phase approval draft fields were updated locally.",
    )
    approval_path = resolve_project_execution_phase_approval_path(config.repo_root, normalized_project_id)
    approval_path.write_text(json.dumps(approval, indent=2) + "\n", encoding="utf-8")
    dossier_result = read_project_factory_dossier(config, normalized_project_id)
    dossier = dict(dossier_result.get("dossier", {})) if dossier_result.get("dossier_exists", False) else {}
    if dossier:
        dossier["lifecycle_state"] = "execution_phase_approval_draft_updated"
        dossier["next_recommended_action"] = "approve_execution_phase_approval_or_continue_editing"
        dossier["updated_at"] = now
        create_project_factory_dossier(config, dossier)
    return {
        "ok": True,
        "local_only": True,
        "project_id": normalized_project_id,
        "execution_phase_approval": approval,
        "execution_phase_approval_path": str(approval_path),
        "dossier_path": str(resolve_project_factory_dossier_path(config.repo_root, normalized_project_id)),
        "warnings": sorted(set(approval_result.get("warnings", []))),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }


def approve_project_execution_phase_approval(config: AppConfig, project_id: str, approval_payload: dict[str, Any]) -> dict[str, Any]:
    approval_result = read_project_execution_phase_approval(config, project_id)
    normalized_project_id = str(approval_result.get("project_id", "")).strip()
    if not approval_result.get("execution_phase_approval_exists", False):
        return _error(
            "execution_phase_approval_not_found",
            {
                "message": "Execution phase approval must be prepared before approval.",
                "project_id": normalized_project_id,
                "execution_phase_approval_path": approval_result.get("execution_phase_approval_path", ""),
            },
        )
    approval = dict(approval_result.get("execution_phase_approval", {}))
    lanes = [item for item in approval.get("execution_lanes", []) if isinstance(item, dict)]
    approved_lanes = [lane for lane in lanes if str(lane.get("status", "")).strip() == "approved"]
    for lane in approved_lanes:
        if not str(lane.get("acknowledgement_text", "")).strip():
            return _error(
                "execution_phase_approval_validation_failed",
                {"message": f"Lane '{str(lane.get('lane_id', '')).strip()}' is approved but missing acknowledgement_text."},
            )
    if not approved_lanes and not str(approval.get("overall_acknowledgement", "")).strip():
        return _error(
            "execution_phase_approval_validation_failed",
            {"message": "Provide overall_acknowledgement when all execution lanes remain blocked."},
        )
    now = _now_iso()
    approval["lifecycle_state"] = "execution_phase_approval_approved"
    approval["updated_at"] = now
    approval["approved_at"] = now
    approval["approved_by"] = str(approval_payload.get("approved_by", "")).strip() or "local_operator"
    approval["next_recommended_action"] = "execution_phase_gate_ready"
    _append_execution_phase_approval_audit_entry(
        approval,
        event_type="execution_phase_approval_approved",
        lifecycle_state="execution_phase_approval_approved",
        summary="Execution phase approval gate approved locally; execution lanes remain explicit and operator-controlled.",
    )
    approval_path = resolve_project_execution_phase_approval_path(config.repo_root, normalized_project_id)
    approval_path.write_text(json.dumps(approval, indent=2) + "\n", encoding="utf-8")
    dossier_result = read_project_factory_dossier(config, normalized_project_id)
    dossier = dict(dossier_result.get("dossier", {})) if dossier_result.get("dossier_exists", False) else {}
    if dossier:
        dossier["lifecycle_state"] = "execution_phase_approval_approved"
        dossier["next_recommended_action"] = "execution_phase_gate_ready"
        dossier["updated_at"] = now
        create_project_factory_dossier(config, dossier)
    return {
        "ok": True,
        "local_only": True,
        "project_id": normalized_project_id,
        "execution_phase_approval": approval,
        "execution_phase_approval_path": str(approval_path),
        "dossier_path": str(resolve_project_factory_dossier_path(config.repo_root, normalized_project_id)),
        "warnings": sorted(set(approval_result.get("warnings", []))),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }


def validate_project_ai_settings(settings: dict[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    warnings: list[str] = []

    project_ai_mode = str(settings.get("project_ai_mode", "")).strip()
    if project_ai_mode not in PROJECT_AI_MODES:
        blockers.append("project_ai_mode must be one of the supported values.")

    available_raw = settings.get("available_engines", [])
    disabled_raw = settings.get("disabled_engines", [])
    if not isinstance(available_raw, list):
        blockers.append("available_engines must be a list of supported engine keys.")
        available_engines: list[str] = []
    else:
        available_engines = _normalize_text_list(available_raw)
    if not isinstance(disabled_raw, list):
        blockers.append("disabled_engines must be a list of supported engine keys.")
        disabled_engines: list[str] = []
    else:
        disabled_engines = _normalize_text_list(disabled_raw)

    invalid_available = [engine for engine in available_engines if engine not in AI_ENGINE_KEYS]
    invalid_disabled = [engine for engine in disabled_engines if engine not in AI_ENGINE_KEYS]
    if invalid_available:
        blockers.append(f"available_engines contains unsupported engine keys: {', '.join(invalid_available)}.")
    if invalid_disabled:
        blockers.append(f"disabled_engines contains unsupported engine keys: {', '.join(invalid_disabled)}.")

    default_engine = str(settings.get("default_engine", "")).strip()
    if default_engine:
        if default_engine not in AI_ENGINE_KEYS:
            blockers.append("default_engine must be a supported engine key.")
        if project_ai_mode != "manual_only" and default_engine not in available_engines:
            blockers.append("default_engine must be included in available_engines unless project_ai_mode is manual_only.")
        if default_engine in disabled_engines:
            blockers.append("default_engine must not be included in disabled_engines.")
        if project_ai_mode == "local_only" and default_engine == "codex_cli":
            blockers.append("local_only mode must not default to codex_cli.")
        if project_ai_mode == "codex_only" and default_engine in {"local_reasoning_llm", "local_coding_llm"}:
            blockers.append("codex_only mode must not default to a local LLM engine.")
    elif project_ai_mode != "manual_only":
        blockers.append("default_engine is required unless project_ai_mode is manual_only.")

    overlap = sorted(set(available_engines).intersection(disabled_engines))
    if overlap:
        warnings.append(f"Engines listed as both available and disabled are treated as unavailable for future routing: {', '.join(overlap)}.")
    if project_ai_mode == "cost_saver":
        warnings.append("cost_saver is a preference contract only; no routing execution is performed.")
    if project_ai_mode == "high_confidence":
        warnings.append("high_confidence is a preference contract only; no routing execution is performed.")

    return {
        "valid": not blockers,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "supported_project_ai_modes": list(PROJECT_AI_MODES),
        "supported_engines": list(AI_ENGINE_KEYS),
        "routing_execution_status": "not_implemented",
    }


def read_project_ai_settings(config: AppConfig, project_id: str) -> dict[str, Any]:
    normalized_project_id = str(project_id or "").strip()
    dossier_payload = read_project_factory_dossier(config, normalized_project_id)
    if not dossier_payload.get("dossier_exists", False):
        return _error(
            "project_factory_dossier_not_found",
            {
                "message": "Project factory dossier is required before reading project AI settings.",
                "project_id": normalized_project_id,
                "dossier_path": dossier_payload.get("dossier_path", ""),
            },
        )

    dossier = dossier_payload.get("dossier", {}) if isinstance(dossier_payload.get("dossier"), dict) else {}
    settings_path = resolve_project_ai_settings_path(config.repo_root, normalized_project_id)
    warnings: list[str] = []
    settings_exists = settings_path.exists()
    settings = _default_project_ai_settings()
    if settings_exists:
        try:
            loaded = json.loads(settings_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            warnings.append(f"Project AI settings could not be parsed: {exc}")
        else:
            if isinstance(loaded, dict):
                settings.update(_normalize_project_ai_settings_payload(loaded))
            else:
                warnings.append("Project AI settings have invalid schema; expected JSON object.")

    validation = validate_project_ai_settings(settings)
    warnings.extend(list(validation.get("warnings", [])))
    return {
        "ok": True,
        "local_only": True,
        "project_id": normalized_project_id,
        "project_name": str(dossier.get("name", "")).strip(),
        "settings_path": str(settings_path),
        "settings_exists": settings_exists,
        "project_ai_settings": settings,
        "validation": validation,
        "next_safe_action": "review_project_ai_settings_before_future_routing",
        "warnings": sorted(set(warnings)),
        "blockers": list(validation.get("blockers", [])),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS)
        + [
            "Project AI settings are non-executing routing preferences.",
            "No routing decision, model invocation, agent execution, Codex execution, or local LLM execution is performed.",
        ],
    }


def update_project_ai_settings(config: AppConfig, project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    current = read_project_ai_settings(config, project_id)
    if not current.get("ok", False):
        return current

    settings = dict(current.get("project_ai_settings", {}))
    for key in (
        "project_ai_mode",
        "available_engines",
        "disabled_engines",
        "default_engine",
        "default_model",
        "operator_override_allowed",
        "notes",
    ):
        if key not in payload:
            continue
        value = payload.get(key)
        if key in {"available_engines", "disabled_engines"}:
            settings[key] = _normalize_text_list(value) if isinstance(value, list) else value
        elif key == "operator_override_allowed":
            settings[key] = value
        else:
            settings[key] = str(value or "").strip()

    settings["updated_at"] = _now_iso()
    settings = _normalize_project_ai_settings_payload(settings)
    validation = validate_project_ai_settings(settings)
    if not validation.get("valid", False):
        return _error(
            "project_ai_settings_validation_failed",
            {
                "message": "Project AI settings failed validation.",
                "project_id": current.get("project_id", ""),
                "project_ai_settings": settings,
                "validation": validation,
            },
        )

    settings_path = resolve_project_ai_settings_path(config.repo_root, str(current.get("project_id", "")))
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
    return {
        "ok": True,
        "local_only": True,
        "project_id": current.get("project_id", ""),
        "project_name": current.get("project_name", ""),
        "settings_path": str(settings_path),
        "settings_exists": True,
        "project_ai_settings": settings,
        "validation": validation,
        "next_safe_action": "use_settings_for_future_advisory_routing_contract_only",
        "warnings": list(validation.get("warnings", [])),
        "blockers": [],
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS)
        + [
            "Project AI settings update is local-only and non-executing.",
            "No routing decision, model invocation, agent execution, Codex execution, or local LLM execution is performed.",
        ],
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


def _normalize_text_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    normalized: list[str] = []
    for value in values:
        item = str(value).strip()
        if item and item not in normalized:
            normalized.append(item)
    return normalized


def _append_scope_audit_entry(
    scope_package: dict[str, Any],
    *,
    event_type: str,
    lifecycle_state: str,
    summary: str,
) -> None:
    audit_entries = scope_package.get("audit_trail")
    if not isinstance(audit_entries, list):
        audit_entries = []
    audit_entries.append(
        {
            "timestamp": _now_iso(),
            "event_type": event_type,
            "lifecycle_state": lifecycle_state,
            "actor": "local_operator",
            "summary": summary,
            "local_only": True,
            "github_mutation_status": "not_requested",
            "model_execution_status": "not_requested",
        }
    )
    scope_package["audit_trail"] = audit_entries


def _append_architecture_audit_entry(
    architecture_contract: dict[str, Any],
    *,
    event_type: str,
    lifecycle_state: str,
    summary: str,
) -> None:
    audit_entries = architecture_contract.get("audit_trail")
    if not isinstance(audit_entries, list):
        audit_entries = []
    audit_entries.append(
        {
            "timestamp": _now_iso(),
            "event_type": event_type,
            "lifecycle_state": lifecycle_state,
            "actor": "local_operator",
            "summary": summary,
            "local_only": True,
            "github_mutation_status": "not_requested",
            "model_execution_status": "not_requested",
        }
    )
    architecture_contract["audit_trail"] = audit_entries


def _append_milestone_issue_plan_audit_entry(
    milestone_issue_plan: dict[str, Any],
    *,
    event_type: str,
    lifecycle_state: str,
    summary: str,
) -> None:
    audit_entries = milestone_issue_plan.get("audit_trail")
    if not isinstance(audit_entries, list):
        audit_entries = []
    audit_entries.append(
        {
            "timestamp": _now_iso(),
            "event_type": event_type,
            "lifecycle_state": lifecycle_state,
            "actor": "local_operator",
            "summary": summary,
            "local_only": True,
            "github_mutation_status": "not_requested",
            "model_execution_status": "not_requested",
        }
    )
    milestone_issue_plan["audit_trail"] = audit_entries


def _append_github_apply_plan_audit_entry(
    github_apply_plan: dict[str, Any],
    *,
    event_type: str,
    lifecycle_state: str,
    summary: str,
) -> None:
    audit_entries = github_apply_plan.get("audit_trail")
    if not isinstance(audit_entries, list):
        audit_entries = []
    audit_entries.append(
        {
            "timestamp": _now_iso(),
            "event_type": event_type,
            "lifecycle_state": lifecycle_state,
            "actor": "local_operator",
            "summary": summary,
            "local_only": True,
            "github_mutation_status": "not_requested",
            "github_execution_status": "not_executed",
            "model_execution_status": "not_requested",
        }
    )
    github_apply_plan["audit_trail"] = audit_entries


def _append_agent_dispatch_plan_audit_entry(
    agent_dispatch_plan: dict[str, Any],
    *,
    event_type: str,
    lifecycle_state: str,
    summary: str,
) -> None:
    audit_entries = agent_dispatch_plan.get("audit_trail")
    if not isinstance(audit_entries, list):
        audit_entries = []
    audit_entries.append(
        {
            "timestamp": _now_iso(),
            "event_type": event_type,
            "lifecycle_state": lifecycle_state,
            "actor": "local_operator",
            "summary": summary,
            "local_only": True,
            "agent_execution_status": "not_requested",
            "model_execution_status": "not_requested",
            "github_mutation_status": "not_requested",
        }
    )
    agent_dispatch_plan["audit_trail"] = audit_entries


def _append_validation_execution_plan_audit_entry(
    validation_execution_plan: dict[str, Any],
    *,
    event_type: str,
    lifecycle_state: str,
    summary: str,
) -> None:
    audit_entries = validation_execution_plan.get("audit_trail")
    if not isinstance(audit_entries, list):
        audit_entries = []
    audit_entries.append(
        {
            "timestamp": _now_iso(),
            "event_type": event_type,
            "lifecycle_state": lifecycle_state,
            "actor": "local_operator",
            "summary": summary,
            "local_only": True,
            "validation_execution_status": "not_requested",
            "agent_execution_status": "not_requested",
            "model_execution_status": "not_requested",
            "github_mutation_status": "not_requested",
        }
    )
    validation_execution_plan["audit_trail"] = audit_entries


def _append_documentation_closeout_plan_audit_entry(
    documentation_closeout_plan: dict[str, Any],
    *,
    event_type: str,
    lifecycle_state: str,
    summary: str,
) -> None:
    audit_entries = documentation_closeout_plan.get("audit_trail")
    if not isinstance(audit_entries, list):
        audit_entries = []
    audit_entries.append(
        {
            "timestamp": _now_iso(),
            "event_type": event_type,
            "lifecycle_state": lifecycle_state,
            "actor": "local_operator",
            "summary": summary,
            "local_only": True,
            "documentation_execution_status": "not_requested",
            "validation_execution_status": "not_requested",
            "agent_execution_status": "not_requested",
            "model_execution_status": "not_requested",
            "github_mutation_status": "not_requested",
        }
    )
    documentation_closeout_plan["audit_trail"] = audit_entries


def _append_execution_phase_approval_audit_entry(
    execution_phase_approval: dict[str, Any],
    *,
    event_type: str,
    lifecycle_state: str,
    summary: str,
) -> None:
    audit_entries = execution_phase_approval.get("audit_trail")
    if not isinstance(audit_entries, list):
        audit_entries = []
    audit_entries.append(
        {
            "timestamp": _now_iso(),
            "event_type": event_type,
            "lifecycle_state": lifecycle_state,
            "actor": "local_operator",
            "summary": summary,
            "local_only": True,
            "github_mutation_status": "not_requested",
            "validation_execution_status": "not_requested",
            "documentation_execution_status": "not_requested",
            "agent_execution_status": "not_requested",
            "model_execution_status": "not_requested",
            "project_closeout_status": "not_requested",
        }
    )
    execution_phase_approval["audit_trail"] = audit_entries


def _artifact_summary_entry(*, key: str, exists: bool, lifecycle_state: str, approved: bool, path: str) -> dict[str, Any]:
    blockers: list[str] = []
    warnings: list[str] = []
    if not exists:
        blockers.append(f"{key} artifact is missing.")
    elif key == "execution_phase_approval" and not approved:
        warnings.append("Execution phase approval exists but is not approved yet.")
    return {
        "exists": bool(exists),
        "lifecycle_state": lifecycle_state,
        "approved": bool(approved),
        "path": path,
        "blockers": blockers,
        "warnings": warnings,
    }


def _build_lane_summary(execution_phase_approval: Any) -> dict[str, dict[str, Any]]:
    approval = execution_phase_approval if isinstance(execution_phase_approval, dict) else {}
    lanes = [item for item in approval.get("execution_lanes", []) if isinstance(item, dict)]
    lane_map = {str(lane.get("lane_id", "")).strip(): lane for lane in lanes}
    summary: dict[str, dict[str, Any]] = {}
    for lane_id in _EXECUTION_READINESS_LANES:
        lane = lane_map.get(lane_id, {})
        status = str(lane.get("status", "")).strip() or "blocked"
        approved = status == "approved"
        acknowledgement_present = bool(str(lane.get("acknowledgement_text", "")).strip())
        blockers: list[str] = []
        warnings: list[str] = _normalize_text_list(lane.get("warnings"))
        if not lane:
            blockers.append("Lane entry missing from execution phase approval.")
        elif approved and not acknowledgement_present:
            blockers.append("Lane is approved but acknowledgement_text is missing.")
        next_safe_action = "add_lane_and_keep_blocked" if not lane else ("execute_lane_with_controls" if approved else "keep_lane_blocked_or_explicitly_approve")
        summary[lane_id] = {
            "status": status,
            "approved": approved,
            "acknowledgement_present": acknowledgement_present,
            "summary": str(lane.get("summary", "")).strip(),
            "warnings": sorted(set(warnings)),
            "blockers": sorted(set(blockers)),
            "next_safe_action": next_safe_action,
        }
    return summary


def _error(error: str, details: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": False,
        "local_only": True,
        "error": error,
        "details": details,
    }


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _default_project_ai_settings() -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "project_ai_mode": "balanced",
        "available_engines": list(AI_ENGINE_KEYS),
        "disabled_engines": [],
        "default_engine": "local_coding_llm",
        "default_model": "",
        "operator_override_allowed": True,
        "notes": "",
        "updated_at": "",
    }


def _normalize_project_ai_settings_payload(payload: dict[str, Any]) -> dict[str, Any]:
    default_settings = _default_project_ai_settings()
    normalized = {
        "schema_version": str(payload.get("schema_version", default_settings["schema_version"])).strip() or "1.0",
        "project_ai_mode": str(payload.get("project_ai_mode", default_settings["project_ai_mode"])).strip(),
        "available_engines": _normalize_text_list(payload.get("available_engines"))
        if isinstance(payload.get("available_engines"), list)
        else payload.get("available_engines", default_settings["available_engines"]),
        "disabled_engines": _normalize_text_list(payload.get("disabled_engines"))
        if isinstance(payload.get("disabled_engines"), list)
        else payload.get("disabled_engines", default_settings["disabled_engines"]),
        "default_engine": str(payload.get("default_engine", default_settings["default_engine"]) or "").strip(),
        "default_model": str(payload.get("default_model", default_settings["default_model"]) or "").strip(),
        "operator_override_allowed": payload.get(
            "operator_override_allowed",
            default_settings["operator_override_allowed"],
        ),
        "notes": str(payload.get("notes", default_settings["notes"]) or "").strip(),
        "updated_at": str(payload.get("updated_at", default_settings["updated_at"]) or "").strip(),
    }
    if not isinstance(normalized["operator_override_allowed"], bool):
        normalized["operator_override_allowed"] = bool(normalized["operator_override_allowed"])
    return normalized


def _build_workflow_steps(*, lifecycle_state: str, github_mode: str) -> list[dict[str, Any]]:
    normalized_state = lifecycle_state.strip() or "not_started"
    normalized_github_mode = github_mode.strip() or "create-later"
    repo_step_status = "current" if normalized_state == "intake_created" and normalized_github_mode == "link-existing" else "pending"
    scope_step_status = "current" if normalized_state == "intake_created" else "pending"
    if normalized_state == "scope_package_prepared":
        repo_step_status = "completed" if normalized_github_mode == "link-existing" else "pending"
        scope_step_status = "completed"
    if normalized_state == "scope_approved":
        repo_step_status = "completed" if normalized_github_mode == "link-existing" else "pending"
        scope_step_status = "completed"
    if normalized_state in {"architecture_contract_prepared", "architecture_draft_updated", "architecture_approved"}:
        repo_step_status = "completed" if normalized_github_mode == "link-existing" else "pending"
        scope_step_status = "completed"
    architecture_step_status = "pending"
    milestone_step_status = "pending"
    if normalized_state == "scope_approved":
        architecture_step_status = "current"
    if normalized_state in {"architecture_contract_prepared", "architecture_draft_updated"}:
        architecture_step_status = "current"
        milestone_step_status = "pending"
    if normalized_state == "architecture_approved":
        architecture_step_status = "completed"
        milestone_step_status = "current"
    if normalized_state in {"milestone_issue_plan_prepared", "milestone_issue_plan_draft_updated"}:
        architecture_step_status = "completed"
        milestone_step_status = "current"
    if normalized_state == "milestone_issue_plan_approved":
        architecture_step_status = "completed"
        milestone_step_status = "completed"
    github_apply_status = "gated"
    agent_dispatch_status = "gated"
    validation_status = "pending"
    if normalized_state in {"github_apply_plan_prepared", "github_apply_plan_draft_updated"}:
        github_apply_status = "current"
    if normalized_state == "github_apply_plan_approved":
        github_apply_status = "completed"
        agent_dispatch_status = "current"
    if normalized_state in {"agent_dispatch_plan_prepared", "agent_dispatch_plan_draft_updated"}:
        github_apply_status = "completed"
        agent_dispatch_status = "current"
    documentation_status = "pending"
    execution_phase_approval_status = "pending"
    closeout_status = "pending"
    if normalized_state == "agent_dispatch_plan_approved":
        github_apply_status = "completed"
        agent_dispatch_status = "completed"
        validation_status = "current"
    if normalized_state in {"validation_execution_plan_prepared", "validation_execution_plan_draft_updated"}:
        github_apply_status = "completed"
        agent_dispatch_status = "completed"
        validation_status = "current"
        documentation_status = "pending"
    if normalized_state == "validation_execution_plan_approved":
        github_apply_status = "completed"
        agent_dispatch_status = "completed"
        validation_status = "completed"
        documentation_status = "current"
        closeout_status = "gated"
    if normalized_state in {"documentation_closeout_plan_prepared", "documentation_closeout_plan_draft_updated"}:
        github_apply_status = "completed"
        agent_dispatch_status = "completed"
        validation_status = "completed"
        documentation_status = "current"
        execution_phase_approval_status = "pending"
        closeout_status = "pending"
    if normalized_state == "documentation_closeout_plan_approved":
        github_apply_status = "completed"
        agent_dispatch_status = "completed"
        validation_status = "completed"
        documentation_status = "completed"
        execution_phase_approval_status = "current"
        closeout_status = "gated"
    if normalized_state in {"execution_phase_approval_prepared", "execution_phase_approval_draft_updated"}:
        github_apply_status = "completed"
        agent_dispatch_status = "completed"
        validation_status = "completed"
        documentation_status = "completed"
        execution_phase_approval_status = "current"
        closeout_status = "gated"
    if normalized_state == "execution_phase_approval_approved":
        github_apply_status = "completed"
        agent_dispatch_status = "completed"
        validation_status = "completed"
        documentation_status = "completed"
        execution_phase_approval_status = "completed"
        closeout_status = "current"
    elif normalized_state == "milestone_issue_plan_approved":
        github_apply_status = "current"
        agent_dispatch_status = "gated"
    elif normalized_state in {"scope_approved", "architecture_contract_prepared", "architecture_draft_updated", "architecture_approved", "milestone_issue_plan_prepared", "milestone_issue_plan_draft_updated"}:
        agent_dispatch_status = "gated"
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
            "status": architecture_step_status,
            "local_only": True,
            "gate_type": "model_execution_approval",
            "description": "Architecture and design planning phase.",
        },
        {
            "step_id": "milestone_issue_plan",
            "label": "Milestone and Issue Plan",
            "status": milestone_step_status,
            "local_only": True,
            "gate_type": "user_approval",
            "description": "Define milestones and issue plan locally before apply.",
        },
        {
            "step_id": "github_apply",
            "label": "GitHub Apply",
            "status": github_apply_status,
            "local_only": True,
            "gate_type": "github_approval",
            "description": "GitHub apply plan is local-only and gated; no GitHub mutations are executed here.",
        },
        {
            "step_id": "agent_dispatch",
            "label": "Agent Dispatch",
            "status": agent_dispatch_status,
            "local_only": True,
            "gate_type": "model_execution_approval",
            "description": "Agent execution remains gated until explicit approval.",
        },
        {
            "step_id": "validation",
            "label": "Validation",
            "status": validation_status,
            "local_only": True,
            "gate_type": "none",
            "description": "Validation planning is local-only and approved as plan-only unless explicitly executed later.",
        },
        {
            "step_id": "documentation",
            "label": "Documentation",
            "status": documentation_status,
            "local_only": True,
            "gate_type": "none",
            "description": "Documentation is tracked as local approved planning only; no updates are executed in this gate.",
        },
        {
            "step_id": "execution_phase_approval",
            "label": "Execution Phase Approval",
            "status": execution_phase_approval_status,
            "local_only": True,
            "gate_type": "user_approval",
            "description": "Explicit local approval gate for future execution lanes; this gate executes nothing.",
        },
        {
            "step_id": "closeout",
            "label": "Closeout",
            "status": closeout_status,
            "local_only": True,
            "gate_type": "none",
            "description": "Closeout remains gated and not executed until explicit execution-phase approvals.",
        },
    ]
