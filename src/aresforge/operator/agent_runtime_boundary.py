from __future__ import annotations

import json
from typing import Any

from aresforge.config import AppConfig

AGENT_RUNTIME_BOUNDARY_VERSION = "m125.1"
COMMAND_NAME = "inspect-agent-runtime-boundary"

SUPPORTED_EXECUTION_MODES: tuple[str, ...] = (
    "inspect_only",
    "plan_only",
    "artifact_generation",
    "operator_gated_local_execution",
    "human_handoff",
)

SUPPORTED_AUTONOMY_LEVELS: tuple[str, ...] = (
    "manual_only",
    "recommendation_only",
    "operator_approved_single_step",
    "operator_approved_bounded_run",
)

SUPPORTED_SAFETY_CLASSES: tuple[str, ...] = (
    "read_only",
    "local_file_write",
    "local_provider_probe",
    "operator_gated_local_provider_execution",
    "external_mutation_prohibited",
)

_BOUNDARY_CONFIRMATIONS: tuple[str, ...] = (
    "M125 defines the runtime boundary only.",
    "Agent runtime boundary inspection is local-only and read-only.",
    "No agent execution is created by this contract.",
    "No Codex, Ollama, local LLM, GitHub, gh, network service, patch application, or workflow execution is performed.",
    "Future agents must declare capabilities, scopes, evidence requirements, limits, and autonomy level before execution.",
    "Execution remains denied unless a future milestone adds a separate operator-approved runner.",
)


def inspect_agent_runtime_boundary(
    config: AppConfig,
    *,
    output_format: str = "json",
) -> dict[str, Any]:
    payload = build_agent_runtime_boundary_contract(config)
    return _stdout_result(
        COMMAND_NAME,
        payload,
        output_format,
        _render_markdown(payload),
    )


def build_agent_runtime_boundary_contract(config: AppConfig) -> dict[str, Any]:
    return {
        "contract_type": "agent_runtime_boundary",
        "generated": True,
        "agent_boundary_version": AGENT_RUNTIME_BOUNDARY_VERSION,
        "repo_root": str(config.repo_root),
        "supported_execution_modes": list(SUPPORTED_EXECUTION_MODES),
        "supported_autonomy_levels": list(SUPPORTED_AUTONOMY_LEVELS),
        "supported_safety_classes": list(SUPPORTED_SAFETY_CLASSES),
        "runtime_boundary_model": {
            "purpose": "Define what an AresForge agent is allowed to receive, decide, emit, and affect before any runtime execution exists.",
            "agent_definition": "An AresForge agent is a declared local control-plane actor with an agent_id, agent_type, bounded inputs, declared outputs, explicit capability catalogs, scoped side effects, evidence requirements, runtime limits, safety class, and autonomy level.",
            "execution_enforcement": [
                "deny execution by default",
                "validate agent_id and agent_type before runtime planning",
                "intersect requested capabilities with allowed_capabilities",
                "block any forbidden_capabilities",
                "constrain file mutation to mutation_scope",
                "constrain provider or network use to network_scope and model_scope",
                "require timeout_policy and retry_policy before any future runner may start",
                "require evidence_requirements before completion or handoff",
                "require operator approval for autonomy above recommendation_only",
            ],
        },
        "field_definitions": _field_definitions(),
        "allowed_capability_catalog": _allowed_capability_catalog(),
        "forbidden_capability_catalog": _forbidden_capability_catalog(),
        "mutation_scope_catalog": _mutation_scope_catalog(),
        "network_scope_catalog": _network_scope_catalog(),
        "model_scope_catalog": _model_scope_catalog(),
        "evidence_requirements": _evidence_requirements(),
        "default_runtime_limits": {
            "execution_allowed_by_this_contract": False,
            "max_single_run_seconds": 900,
            "max_retry_attempts": 0,
            "max_items_per_run": 1,
            "requires_operator_confirmation": True,
            "requires_active_queue_item": True,
            "requires_clean_boundary_validation": True,
            "background_execution_allowed": False,
            "automatic_next_item_execution_allowed": False,
        },
        "default_timeout_policy": {
            "required": True,
            "default_seconds": 900,
            "hard_stop_required": True,
            "timeout_result_state": "blocked_timeout",
        },
        "default_retry_policy": {
            "required": True,
            "automatic_retries_allowed": False,
            "default_max_attempts": 0,
            "retry_requires_operator_review": True,
        },
        "local_only": True,
        "read_only": True,
        "execution_allowed": False,
        "execution_performed": False,
        "next_safe_action": "Use this boundary as schema input for future agent profiles, planners, dry-runs, and operator-gated runners; do not execute agents until a later explicit execution milestone exists.",
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }


def _field_definitions() -> dict[str, dict[str, Any]]:
    return {
        "agent_id": {
            "type": "string",
            "required": True,
            "description": "Stable local identifier for one declared agent profile or runtime actor.",
            "constraints": ["non_empty", "unique_within_local_agent_registry", "no_runtime_privilege_by_itself"],
            "example": "documentation_agent_v1",
        },
        "agent_type": {
            "type": "string",
            "required": True,
            "description": "Functional category for policy and routing decisions.",
            "allowed_values": ["operator", "planner", "implementer", "reviewer", "tester", "documentation", "local_llm_advisory", "codex_handoff"],
        },
        "execution_mode": {
            "type": "string",
            "required": True,
            "description": "The highest runtime behavior the agent may request.",
            "allowed_values": list(SUPPORTED_EXECUTION_MODES),
        },
        "input_contract": {
            "type": "object",
            "required": True,
            "description": "Declared local inputs an agent may read.",
            "required_fields": ["schema_version", "source_refs", "queue_item_ref", "operator_intent", "safety_context"],
        },
        "output_contract": {
            "type": "object",
            "required": True,
            "description": "Declared outputs the agent may produce.",
            "required_fields": ["schema_version", "artifact_type", "summary", "evidence", "next_safe_action"],
        },
        "allowed_capabilities": {
            "type": "array[string]",
            "required": True,
            "description": "Positive capability allow-list selected from the allowed capability catalog.",
        },
        "forbidden_capabilities": {
            "type": "array[string]",
            "required": True,
            "description": "Capability deny-list that must block execution even if another layer requests it.",
        },
        "mutation_scope": {
            "type": "string",
            "required": True,
            "description": "Maximum filesystem or local state mutation boundary.",
            "allowed_values": list(_mutation_scope_catalog().keys()),
        },
        "network_scope": {
            "type": "string",
            "required": True,
            "description": "Maximum network/provider contact boundary.",
            "allowed_values": list(_network_scope_catalog().keys()),
        },
        "model_scope": {
            "type": "string",
            "required": True,
            "description": "Maximum model/provider invocation boundary.",
            "allowed_values": list(_model_scope_catalog().keys()),
        },
        "timeout_policy": {
            "type": "object",
            "required": True,
            "description": "Hard-stop policy for any future bounded runtime.",
            "required_fields": ["timeout_seconds", "hard_stop_required", "timeout_result_state"],
        },
        "retry_policy": {
            "type": "object",
            "required": True,
            "description": "Retry policy for failed or blocked attempts.",
            "required_fields": ["automatic_retries_allowed", "max_attempts", "operator_review_required"],
        },
        "evidence_requirements": {
            "type": "array[string]",
            "required": True,
            "description": "Evidence required before handoff, completion recommendation, or future queue mutation.",
        },
        "safety_class": {
            "type": "string",
            "required": True,
            "description": "Safety tier used to choose enforcement gates.",
            "allowed_values": list(SUPPORTED_SAFETY_CLASSES),
        },
        "autonomy_level": {
            "type": "string",
            "required": True,
            "description": "Maximum independent decision authority.",
            "allowed_values": list(SUPPORTED_AUTONOMY_LEVELS),
        },
    }


def _allowed_capability_catalog() -> dict[str, dict[str, Any]]:
    return {
        "read_local_queue": {"description": "Read local queue records.", "requires_operator_gate": False},
        "read_source_docs": {"description": "Read source-of-truth documentation.", "requires_operator_gate": False},
        "read_local_artifacts": {"description": "Read local artifacts and approval records.", "requires_operator_gate": False},
        "inspect_local_git_state": {"description": "Inspect local git branch, HEAD, and status with approved read commands.", "requires_operator_gate": False},
        "generate_plan_artifact": {"description": "Write a local plan or request artifact when explicitly requested.", "requires_operator_gate": True},
        "generate_review_artifact": {"description": "Write a local review or handoff artifact when explicitly requested.", "requires_operator_gate": True},
        "local_provider_health_probe": {"description": "Call an allowed localhost health endpoint only.", "requires_operator_gate": True},
        "operator_gated_local_provider_prompt": {"description": "Run a local prompt only through a future explicit operator-gated runner.", "requires_operator_gate": True},
    }


def _forbidden_capability_catalog() -> dict[str, str]:
    return {
        "execute_codex": "No Codex or Codex CLI execution is allowed by this boundary inspector.",
        "execute_ollama_prompt": "No Ollama prompt or inference endpoint is allowed by this boundary inspector.",
        "execute_local_llm": "No local model inference is allowed by this boundary inspector.",
        "execute_documentation_agent": "No documentation-agent runtime or apply mode is allowed by this boundary inspector.",
        "apply_patch": "No patch application or repository mutation from generated output is allowed.",
        "mutate_queue_without_operator": "Queue state must not be mutated automatically.",
        "call_github_api": "No GitHub REST or GraphQL calls are allowed.",
        "call_gh": "No gh CLI calls are allowed.",
        "call_external_network": "No external network services are allowed.",
        "create_pr_or_issue": "No issue, PR, workflow, or remote mutation is allowed.",
        "background_daemon": "No daemon, watcher, scheduler, polling loop, or unattended worker is allowed.",
        "automatic_next_item_execution": "A future runner must never start the next queue item automatically.",
    }


def _mutation_scope_catalog() -> dict[str, dict[str, Any]]:
    return {
        "none": {"may_write_files": False, "description": "Read-only inspection only."},
        "artifact_only": {"may_write_files": True, "description": "May write only operator-requested files under approved artifact paths."},
        "queue_metadata_only": {"may_write_files": True, "description": "May update local queue metadata only through explicit lifecycle commands."},
        "source_patch_prohibited": {"may_write_files": False, "description": "Generated patches may be recorded for review but not applied."},
    }


def _network_scope_catalog() -> dict[str, dict[str, Any]]:
    return {
        "none": {"network_allowed": False, "description": "No network or provider calls."},
        "localhost_health_only": {"network_allowed": True, "description": "Only approved localhost health/model-list endpoints."},
        "localhost_operator_gated_provider": {"network_allowed": True, "description": "Only future explicit operator-gated local provider prompt calls."},
        "external_network_forbidden": {"network_allowed": False, "description": "External network services remain forbidden."},
    }


def _model_scope_catalog() -> dict[str, dict[str, Any]]:
    return {
        "none": {"model_invocation_allowed": False, "description": "No model invocation."},
        "metadata_only": {"model_invocation_allowed": False, "description": "Model names and routing metadata only."},
        "local_health_probe_only": {"model_invocation_allowed": False, "description": "Local provider visibility checks only; no prompts."},
        "operator_gated_local_advisory": {"model_invocation_allowed": True, "description": "Reserved for a separate explicit local advisory runner."},
        "codex_handoff_only": {"model_invocation_allowed": False, "description": "Generate handoff artifacts only; AresForge does not execute Codex."},
    }


def _evidence_requirements() -> dict[str, Any]:
    return {
        "required_before_runtime_handoff": [
            "agent_id",
            "agent_type",
            "queue_item_id",
            "operator_intent",
            "input_contract",
            "output_contract",
            "allowed_capabilities",
            "forbidden_capabilities",
            "mutation_scope",
            "network_scope",
            "model_scope",
            "timeout_policy",
            "retry_policy",
            "safety_class",
            "autonomy_level",
        ],
        "required_after_future_bounded_run": [
            "run_id",
            "started_at",
            "completed_at_or_blocked_at",
            "execution_mode",
            "capabilities_used",
            "artifacts_written",
            "validation_commands",
            "stdout_stderr_summary",
            "blocked_reasons_or_result",
            "operator_review_status",
            "next_safe_action",
        ],
        "completion_evidence_never_implied": True,
    }


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
        "ok": bool(payload.get("generated", False)),
        "local_only": True,
        "format": fmt,
        "wrote_output_file": False,
        "stdout": json.dumps(payload, indent=2) if fmt == "json" else markdown,
        "payload": payload,
    }


def _render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Agent Runtime Boundary Contract",
        "",
        f"- contract_type: {payload.get('contract_type', '')}",
        f"- agent_boundary_version: {payload.get('agent_boundary_version', '')}",
        f"- local_only: {payload.get('local_only')}",
        f"- execution_performed: {payload.get('execution_performed')}",
        f"- next_safe_action: {payload.get('next_safe_action', '')}",
        "",
        "## Execution Modes",
    ]
    lines.extend(f"- {mode}" for mode in payload.get("supported_execution_modes", []))
    lines.extend(["", "## Autonomy Levels"])
    lines.extend(f"- {level}" for level in payload.get("supported_autonomy_levels", []))
    lines.extend(["", "## Safety Classes"])
    lines.extend(f"- {safety_class}" for safety_class in payload.get("supported_safety_classes", []))
    lines.extend(["", "## Boundaries"])
    lines.extend(f"- {entry}" for entry in payload.get("boundary_confirmations", []))
    return "\n".join(lines)
