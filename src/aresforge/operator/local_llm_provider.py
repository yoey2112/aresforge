from __future__ import annotations

import json
from urllib.parse import urlparse
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.local_project_factory import read_local_llm_environment_contract

PROVIDER_CONTRACT_VERSION = "m83.1"
DEFAULT_OLLAMA_BASE_URL = "http://127.0.0.1:11434"
DEFAULT_REQUEST_TIMEOUT_SECONDS = 60
SUPPORTED_PROVIDER_TARGETS = ("ollama",)

_BOUNDARY_CONFIRMATIONS: tuple[str, ...] = (
    "M83 local LLM provider contract is local-only.",
    "Provider contract inspection is read-only and non-executing.",
    "Ollama is the initial provider target.",
    "Only explicit local health checks may call the provider tags endpoint.",
    "No prompts are sent.",
    "No inference, generation, chat, or completion endpoint is called.",
    "No repository files are mutated from provider output.",
    "No queue item status is mutated from provider output.",
    "No automatic prompt execution.",
    "No automatic next-item execution.",
    "No GitHub API calls.",
    "No gh calls.",
    "No issues, PRs, workflows, daemons, watchers, schedulers, or external workflow behavior.",
)


def inspect_local_llm_provider_contract(
    config: AppConfig,
    *,
    output_format: str = "json",
) -> dict[str, Any]:
    payload = build_local_llm_provider_contract(config)
    return _stdout_result(
        "inspect-local-llm-provider-contract",
        payload,
        output_format,
        _render_markdown(payload),
    )


def build_local_llm_provider_contract(config: AppConfig) -> dict[str, Any]:
    environment = read_local_llm_environment_contract(config)
    env = environment.get("local_llm_environment", {})
    if not isinstance(env, dict):
        env = {}

    provider = str(env.get("local_llm_provider", "unknown") or "unknown").strip() or "unknown"
    provider_base_url = str(env.get("provider_base_url", "") or "").strip()
    configured_base_url = provider_base_url or (DEFAULT_OLLAMA_BASE_URL if provider == "ollama" else "")
    timeout_seconds = _positive_int_or_default(
        env.get("request_timeout_seconds"),
        DEFAULT_REQUEST_TIMEOUT_SECONDS,
    )
    provider_state = environment.get("provider_state", {})
    if not isinstance(provider_state, dict):
        provider_state = {}

    blockers: list[str] = []
    warnings: list[str] = [str(value).strip() for value in environment.get("warnings", []) if str(value).strip()]
    if provider not in {"ollama", "none", "unknown"}:
        blockers.append(f"Unsupported local LLM provider: {provider}")
    if provider == "ollama" and provider_base_url and not _is_local_provider_url(provider_base_url):
        blockers.append("Ollama provider_base_url must point to localhost, 127.0.0.1, or ::1.")
    if provider in {"none", "unknown"}:
        warnings.append("Local LLM provider is not configured; contract remains inspectable but provider readiness is unavailable.")

    model_contracts = _model_contracts(
        provider=provider,
        environment=env,
        provider_configuration_status=str(environment.get("provider_configuration_status", "unknown")).strip(),
    )
    contract_ready = provider == "ollama" and not blockers and bool(configured_base_url)

    return {
        "ok": True,
        "local_only": True,
        "read_only": True,
        "contract_version": PROVIDER_CONTRACT_VERSION,
        "provider_contract_ready": contract_ready,
        "provider": provider,
        "supported_provider_targets": list(SUPPORTED_PROVIDER_TARGETS),
        "initial_provider_target": "ollama",
        "provider_base_url": configured_base_url,
        "provider_url_source": "local_llm_environment_contract" if provider_base_url else "default_for_ollama" if provider == "ollama" else "not_configured",
        "request_timeout_seconds": timeout_seconds,
        "timeout_expectations": {
            "default_request_timeout_seconds": DEFAULT_REQUEST_TIMEOUT_SECONDS,
            "configured_request_timeout_seconds": env.get("request_timeout_seconds"),
            "health_check_timeout_seconds": timeout_seconds,
            "inference_timeout_seconds": timeout_seconds,
            "timeouts_are_operator_configuration": True,
        },
        "health_check_contract": {
            "explicit_operator_command_required": True,
            "health_check_enabled": bool(env.get("health_check_enabled", False)),
            "allowed_endpoint": "/api/tags",
            "forbidden_endpoints": ["/api/generate", "/api/chat", "/api/completions", "/v1/chat/completions"],
            "inference_tested": False,
            "execution_allowed": False,
            "requires_local_url": True,
            "provider_reachability_is_metadata_only": True,
        },
        "model_selection_contract": {
            "supports_reasoning_model_selection": True,
            "supports_coding_model_selection": True,
            "automatic_fallback_selection_allowed": False,
            "model_identifier_fields": ["reasoning_model", "coding_model", "fallback_model"],
            "models": model_contracts,
        },
        "provider_state": provider_state,
        "provider_availability_status": str(environment.get("provider_availability_status", "unknown")).strip(),
        "provider_configuration_status": str(environment.get("provider_configuration_status", "unknown")).strip(),
        "provider_execution_mode": str(environment.get("provider_execution_mode", "unknown")).strip(),
        "fallback_behavior": environment.get("fallback_behavior", ""),
        "safety_boundary": {
            "local_only": True,
            "operator_gate_required": True,
            "provider_invocation_allowed_from_this_command": False,
            "prompt_execution_allowed_from_this_command": False,
            "repo_mutation_allowed": False,
            "queue_mutation_allowed": False,
            "queue_completion_allowed": False,
            "automatic_next_item_execution_allowed": False,
            "external_workflow_allowed": False,
            "github_api_allowed": False,
            "gh_allowed": False,
        },
        "warnings": sorted(set(warnings)),
        "blockers": sorted(set(blockers)),
        "next_safe_action": (
            "Run the explicit local health check before any separate operator-gated local LLM prototype invocation."
            if contract_ready
            else "Configure local Ollama provider metadata before health checks or provider-gated advisory workflows."
        ),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }


def _model_contracts(
    *,
    provider: str,
    environment: dict[str, Any],
    provider_configuration_status: str,
) -> list[dict[str, Any]]:
    specs = (
        (
            "reasoning_model",
            "local_reasoning_llm",
            "reasoning",
            ["planning", "review", "summarization", "risk analysis", "operator advisory"],
        ),
        (
            "coding_model",
            "local_coding_llm",
            "coding",
            ["implementation planning", "patch suggestions", "test suggestions", "code review advisory"],
        ),
        (
            "fallback_model",
            "fallback",
            "fallback",
            ["manual fallback reference only"],
        ),
    )
    contracts: list[dict[str, Any]] = []
    for field, lane, role, capabilities in specs:
        model_identifier = str(environment.get(field, "") or "").strip()
        contracts.append(
            {
                "field": field,
                "provider": provider,
                "model_identifier": model_identifier,
                "role": role,
                "intended_lane": lane,
                "capabilities": capabilities,
                "status": "configured" if model_identifier and provider_configuration_status == "configured" else "missing_configuration" if not model_identifier else provider_configuration_status or "unknown",
                "selection_policy": "operator_reviewed_configuration",
                "may_mutate_repo": False,
                "may_advance_queue": False,
                "may_execute_automatically": False,
            }
        )
    return contracts


def _positive_int_or_default(value: Any, default: int) -> int:
    if isinstance(value, int) and not isinstance(value, bool) and value > 0:
        return value
    if isinstance(value, str) and value.strip().isdigit():
        parsed = int(value.strip())
        return parsed if parsed > 0 else default
    return default


def _is_local_provider_url(provider_base_url: str) -> bool:
    parsed = urlparse(provider_base_url)
    host = (parsed.hostname or "").lower()
    return parsed.scheme in {"http", "https"} and host in {"localhost", "127.0.0.1", "::1"}


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
        "# Local LLM Provider Contract",
        "",
        f"- ok: {payload.get('ok')}",
        f"- provider: {payload.get('provider', '')}",
        f"- provider_base_url: {payload.get('provider_base_url', '')}",
        f"- provider_contract_ready: {payload.get('provider_contract_ready')}",
        f"- request_timeout_seconds: {payload.get('request_timeout_seconds')}",
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
