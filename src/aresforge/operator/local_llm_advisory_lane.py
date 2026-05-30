from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.llm_decision_matrix import build_llm_decision_matrix
from aresforge.operator.local_project_factory import read_local_llm_environment_contract
from aresforge.operator.local_project_queue import inspect_local_queue_item_readiness

ADVISORY_LANE_VERSION = "m81.1"

_LOCAL_LLM_ENGINES = {"local_reasoning_llm", "local_coding_llm"}

_BOUNDARY_CONFIRMATIONS = (
    "M81 local LLM advisory/coding lane readiness is local-only.",
    "Readiness inspection is advisory-first and non-executing.",
    "No local LLM provider is invoked.",
    "No prompt is dispatched.",
    "No repository files are mutated.",
    "No queue item status is mutated.",
    "No queue item is completed.",
    "No automatic next-item execution.",
    "No GitHub API calls.",
    "No gh calls.",
    "No GitHub issues, PRs, workflows, or GitHub mutation.",
    "No external workflow execution.",
)


def inspect_local_llm_advisory_lane_readiness(
    config: AppConfig,
    *,
    item_id: str,
    queue_path: str | Path | None = None,
    registry_path: str | Path | None = None,
    output_format: str = "json",
) -> dict[str, Any]:
    payload = build_local_llm_advisory_lane_readiness(
        config,
        item_id=item_id,
        queue_path=queue_path,
        registry_path=registry_path,
    )
    return _stdout_result(
        "inspect-local-llm-advisory-lane-readiness",
        payload,
        output_format,
        _render_markdown(payload),
    )


def build_local_llm_advisory_lane_readiness(
    config: AppConfig,
    *,
    item_id: str,
    queue_path: str | Path | None = None,
    registry_path: str | Path | None = None,
) -> dict[str, Any]:
    normalized_item_id = str(item_id or "").strip()
    readiness = inspect_local_queue_item_readiness(
        config,
        item_id=normalized_item_id,
        queue_path=queue_path,
        registry_path=registry_path,
    )
    matrix = build_llm_decision_matrix(
        config,
        item_id=normalized_item_id,
        queue_path=queue_path,
        registry_path=registry_path,
    )
    environment = read_local_llm_environment_contract(config)

    warnings = _unique_strings(
        [
            *readiness.get("warnings", []),
            *matrix.get("warnings", []),
            *environment.get("warnings", []),
        ]
    )
    blockers = _unique_strings(
        [
            *readiness.get("blockers", []),
            *matrix.get("blockers", []),
            *environment.get("blockers", []),
        ]
    )

    decision = matrix.get("routing_decision", {}) if isinstance(matrix.get("routing_decision"), dict) else {}
    engine = str(decision.get("recommended_engine", "")).strip()
    lane = str(decision.get("recommended_lane", "")).strip()
    selected_model = _select_local_model(
        engine=engine,
        decision=decision,
        environment=environment,
    )

    if engine and engine not in _LOCAL_LLM_ENGINES:
        blockers.append(f"Decision matrix recommends {engine}; local LLM advisory lane accepts only local_reasoning_llm or local_coding_llm.")
    if not engine:
        blockers.append("Decision matrix did not recommend a local LLM engine.")
    if engine in _LOCAL_LLM_ENGINES and not selected_model["model_name"]:
        blockers.append("Local LLM advisory lane has no configured model for the recommended local engine.")

    provider_state = environment.get("provider_state", {}) if isinstance(environment.get("provider_state"), dict) else {}
    local_provider = _environment_value(environment, "local_llm_provider") or "unknown"
    if local_provider in {"none", "unknown"}:
        blockers.append("Local LLM provider is not configured for advisory lane readiness.")

    advisory_plan = _build_advisory_plan(
        item_id=normalized_item_id,
        engine=engine,
        lane=lane,
        model_name=selected_model["model_name"],
        work_mode=str((matrix.get("work_mode") or {}).get("work_mode", "")).strip()
        if isinstance(matrix.get("work_mode"), dict)
        else "",
        risk_level=str((matrix.get("risk_classification") or {}).get("risk_level", "unknown")).strip()
        if isinstance(matrix.get("risk_classification"), dict)
        else "unknown",
        validation_burden=str((matrix.get("validation_burden") or {}).get("validation_burden", "medium")).strip()
        if isinstance(matrix.get("validation_burden"), dict)
        else "medium",
    )

    advisory_lane_ready = (
        bool(readiness.get("ok", False))
        and bool(matrix.get("ok", False))
        and engine in _LOCAL_LLM_ENGINES
        and bool(selected_model["model_name"])
        and not blockers
    )

    return {
        "ok": bool(readiness.get("ok", False)) and bool(matrix.get("ok", False)),
        "local_only": True,
        "advisory_only": True,
        "advisory_lane_ready": advisory_lane_ready,
        "advisory_lane_version": ADVISORY_LANE_VERSION,
        "item_id": normalized_item_id,
        "project_id": str(matrix.get("project_id", "")).strip(),
        "repo_id": str(matrix.get("repo_id", "")).strip(),
        "readiness_status": str(readiness.get("readiness_status", "unknown")).strip(),
        "can_start": bool(readiness.get("can_start", False)),
        "recommended_engine": engine,
        "recommended_lane": lane,
        "selected_model": selected_model,
        "provider_metadata": {
            "provider": local_provider,
            "provider_base_url": _environment_value(environment, "provider_base_url"),
            "provider_availability_status": str(environment.get("provider_availability_status", "unknown")).strip(),
            "provider_configuration_status": str(environment.get("provider_configuration_status", "unknown")).strip(),
            "provider_execution_mode": str(environment.get("provider_execution_mode", "unknown")).strip(),
            "provider_state": provider_state,
            "local_model_profiles": environment.get("local_model_profiles", []),
            "fallback_behavior": environment.get("fallback_behavior", {}),
        },
        "decision_matrix_summary": {
            "decision_matrix_version": str(matrix.get("decision_matrix_version", "")).strip(),
            "work_mode": matrix.get("work_mode", {}),
            "task_sizing": matrix.get("task_sizing", {}),
            "risk_classification": matrix.get("risk_classification", {}),
            "validation_burden": matrix.get("validation_burden", {}),
            "routing_decision": decision,
        },
        "advisory_plan": advisory_plan,
        "safety_boundary": {
            "operator_gate_required_for_invocation": True,
            "provider_invocation_allowed_from_this_command": False,
            "prompt_dispatch_allowed": False,
            "repo_mutation_allowed": False,
            "queue_mutation_allowed": False,
            "queue_completion_allowed": False,
            "automatic_next_item_execution_allowed": False,
            "external_workflow_allowed": False,
            "github_api_allowed": False,
            "gh_allowed": False,
        },
        "execution_allowed": False,
        "local_llm_invocation_allowed": False,
        "repo_mutation_allowed": False,
        "queue_mutation_allowed": False,
        "automatic_next_item_execution_allowed": False,
        "warnings": _unique_strings(warnings),
        "blockers": _unique_strings(blockers),
        "next_safe_action": (
            "Generate a local LLM prompt preview only after operator review; keep any model output advisory and manually reviewed."
            if advisory_lane_ready
            else "Resolve local LLM advisory lane readiness blockers before any explicit operator-gated preview or invocation."
        ),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }


def _select_local_model(*, engine: str, decision: dict[str, Any], environment: dict[str, Any]) -> dict[str, str]:
    explicit_model = str(decision.get("recommended_model", "")).strip()
    env = environment.get("local_llm_environment", {}) if isinstance(environment.get("local_llm_environment"), dict) else {}
    field = "coding_model" if engine == "local_coding_llm" else "reasoning_model"
    model = explicit_model or str(env.get(field, "")).strip()
    return {
        "model_name": model,
        "engine": engine,
        "source": "decision_matrix" if explicit_model else "local_llm_environment_contract",
        "fallback_model": str(decision.get("fallback_model", "") or env.get("fallback_model", "")).strip(),
        "profile_status": str(environment.get("provider_configuration_status", "unknown")).strip(),
    }


def _build_advisory_plan(
    *,
    item_id: str,
    engine: str,
    lane: str,
    model_name: str,
    work_mode: str,
    risk_level: str,
    validation_burden: str,
) -> dict[str, Any]:
    return {
        "artifact_kind": "local_llm_advisory_plan",
        "structured_json_output_required": True,
        "target_item_id": item_id,
        "target_engine": engine,
        "target_lane": lane,
        "target_model": model_name,
        "advisory_mode": "coding_advisory" if work_mode == "coding" else "reasoning_advisory",
        "risk_level": risk_level or "unknown",
        "validation_burden": validation_burden or "medium",
        "allowed_outputs": [
            "reasoning summary",
            "implementation plan",
            "risk notes",
            "suggested tests",
            "manual patch guidance",
        ],
        "forbidden_outputs": [
            "automatic file edits",
            "automatic queue status changes",
            "automatic queue completion",
            "automatic next-item execution",
            "GitHub API calls",
            "gh calls",
            "workflow execution",
        ],
        "required_output_fields": [
            "summary",
            "plan",
            "risks",
            "suggested_validation",
            "manual_review_required",
            "repo_mutation_allowed",
            "queue_mutation_allowed",
            "automatic_next_item_execution_allowed",
        ],
        "safety_boundary_confirmations": {
            "manual_review_required": True,
            "repo_mutation_allowed": False,
            "queue_mutation_allowed": False,
            "automatic_next_item_execution_allowed": False,
            "provider_invocation_requires_separate_operator_gate": True,
        },
    }


def _environment_value(environment: dict[str, Any], field: str) -> str:
    env = environment.get("local_llm_environment", {}) if isinstance(environment.get("local_llm_environment"), dict) else {}
    return str(env.get(field, "")).strip()


def _unique_strings(values: list[Any]) -> list[str]:
    return sorted({str(value).strip() for value in values if str(value).strip()})


def _stdout_result(command: str, payload: dict[str, Any], output_format: str, markdown: str) -> dict[str, Any]:
    fmt = str(output_format or "json").lower().strip()
    if fmt not in {"json", "markdown"}:
        return {
            "ok": False,
            "local_only": True,
            "error": "invalid_format",
            "details": {"format": output_format, "supported_formats": ["json", "markdown"]},
        }
    return {
        "command": command,
        "ok": bool(payload.get("ok", False)),
        "local_only": True,
        "format": fmt,
        "wrote_output_file": False,
        "stdout": json.dumps(payload, indent=2) if fmt == "json" else markdown,
        "payload": payload,
    }


def _render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Local LLM Advisory Lane Readiness",
        "",
        f"- ok: {payload.get('ok')}",
        f"- item_id: {payload.get('item_id', '')}",
        f"- recommended_engine: {payload.get('recommended_engine', '')}",
        f"- recommended_lane: {payload.get('recommended_lane', '')}",
        f"- selected_model: {(payload.get('selected_model') or {}).get('model_name', '') if isinstance(payload.get('selected_model'), dict) else ''}",
        f"- execution_allowed: {payload.get('execution_allowed')}",
        f"- next_safe_action: {payload.get('next_safe_action', '')}",
        "",
        "## Boundaries",
    ]
    lines.extend(f"- {entry}" for entry in payload.get("boundary_confirmations", []))
    blockers = payload.get("blockers", []) if isinstance(payload.get("blockers"), list) else []
    if blockers:
        lines.extend(["", "## Blockers"])
        lines.extend(f"- {entry}" for entry in blockers)
    return "\n".join(lines)
