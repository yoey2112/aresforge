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


def resolve_project_factory_dossier_path(repo_root: Path, project_id: str) -> Path:
    return (repo_root / ".aresforge" / "projects" / project_id.strip() / "factory_dossier.json").resolve()


def resolve_project_scope_package_path(repo_root: Path, project_id: str) -> Path:
    return (repo_root / ".aresforge" / "projects" / project_id.strip() / "scope_package.json").resolve()


def resolve_project_architecture_contract_path(repo_root: Path, project_id: str) -> Path:
    return (repo_root / ".aresforge" / "projects" / project_id.strip() / "architecture_contract.json").resolve()


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
