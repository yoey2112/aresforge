from __future__ import annotations

from datetime import UTC, datetime
import json
import socket
from pathlib import Path
from typing import Any
from urllib import error, request
from urllib.parse import urlparse

from aresforge.config import AppConfig
from aresforge.operator.local_project_factory import read_local_llm_environment_contract

PROBE_TYPE = "local_ollama_provider_probe"
PROBE_VERSION = "m115.1"
DEFAULT_OLLAMA_BASE_URL = "http://127.0.0.1:11434"
DEFAULT_TIMEOUT_SECONDS = 10

_BOUNDARY_CONFIRMATIONS = (
    "M115 local Ollama provider probe is local-only environment discovery.",
    "The probe may inspect only local configuration and, when allowed, the loopback /api/tags endpoint.",
    "No task prompt is sent to Ollama.",
    "No generation, chat, completion, coding, reasoning, or advisory endpoint is called.",
    "No model output is requested or used.",
    "No Codex, GitHub, gh, agent, workflow, patch, queue mutation, or repository mutation is performed.",
)


def probe_local_ollama_provider(
    config: AppConfig,
    *,
    output: str | Path | None = None,
    force: bool = False,
    no_network: bool = False,
    config_path: str | Path | None = None,
    output_format: str = "markdown",
    urlopen_fn: Any | None = None,
) -> dict[str, Any]:
    environment_contract = _read_environment(config, config_path=config_path)
    env = environment_contract.get("local_llm_environment", {})
    if not isinstance(env, dict):
        env = {}

    payload = _build_probe_payload(
        config=config,
        environment_contract=environment_contract,
        environment=env,
        no_network=no_network,
        urlopen_fn=urlopen_fn,
    )

    if output is not None:
        output_path = _resolve_output_path(config, output)
        write_result = _write_json_output(output_path, payload, force=force)
        if not write_result["ok"]:
            payload["ok"] = False
            payload["probed"] = False
            payload["blocked"] = True
            payload["blocked_reasons"] = sorted(
                {str(reason) for reason in payload.get("blocked_reasons", []) if str(reason).strip()}
                | {str(write_result["reason"])}
            )
            payload["next_safe_action"] = "Review blocked reasons before recording another Ollama provider probe."
        else:
            payload["output_path"] = str(output_path)

    return _stdout_result(
        "probe-local-ollama-provider",
        payload,
        output_format,
        _render_markdown(payload),
    )


def _build_probe_payload(
    *,
    config: AppConfig,
    environment_contract: dict[str, Any],
    environment: dict[str, Any],
    no_network: bool,
    urlopen_fn: Any | None,
) -> dict[str, Any]:
    provider = str(environment.get("local_llm_provider", "") or "").strip() or "unknown"
    provider_base_url = str(environment.get("provider_base_url", "") or "").strip()
    endpoint_base = provider_base_url or str(config.ollama_base_url or DEFAULT_OLLAMA_BASE_URL).strip()
    endpoint = endpoint_base.rstrip("/") + "/api/tags"
    timeout_seconds = _positive_int_or_default(environment.get("request_timeout_seconds"), DEFAULT_TIMEOUT_SECONDS)
    configured_profiles = _configured_model_profiles(environment, config=config)
    blocked_reasons = _probe_blockers(provider=provider, endpoint_base=endpoint_base, no_network=no_network)
    warnings = [str(warning).strip() for warning in environment_contract.get("warnings", []) if str(warning).strip()]

    if no_network:
        probe_method = "config_only_no_network"
    elif provider != "ollama":
        probe_method = "config_only_provider_not_ollama"
    else:
        probe_method = "loopback_ollama_tags"
    available_models: list[dict[str, Any]] = []
    ollama_detected = False
    network_execution_performed = False
    error_summary = ""

    if not blocked_reasons and not no_network and provider == "ollama":
        network_execution_performed = True
        try:
            available_models = _fetch_ollama_tags(endpoint=endpoint, timeout_seconds=timeout_seconds, urlopen_fn=urlopen_fn)
            ollama_detected = True
        except (error.URLError, TimeoutError, socket.timeout, OSError) as exc:
            error_summary = f"Local Ollama tags endpoint unavailable: {exc}"
            warnings.append("Ollama was not detected on loopback; this does not block normal project readiness.")
        except json.JSONDecodeError as exc:
            error_summary = f"Local Ollama tags endpoint returned invalid JSON: {exc}"
            warnings.append("Ollama tags response could not be parsed; no prompt execution was attempted.")

    if provider in {"none", "unknown"} and not blocked_reasons:
        warnings.append("Ollama is not configured as the local LLM provider; probe remains configuration-only.")

    available_names = {
        str(model.get("name") or model.get("model") or "").strip()
        for model in available_models
        if isinstance(model, dict)
    }

    return {
        "ok": not blocked_reasons,
        "probe_type": PROBE_TYPE,
        "probe_version": PROBE_VERSION,
        "generated_at": _now_iso(),
        "probed": not blocked_reasons,
        "blocked": bool(blocked_reasons),
        "blocked_reasons": sorted({reason for reason in blocked_reasons if reason}),
        "ollama_expected": _ollama_expected(provider=provider, endpoint_base=endpoint_base, profiles=configured_profiles),
        "ollama_detected": ollama_detected,
        "probe_method": probe_method,
        "provider": provider,
        "provider_base_url": endpoint_base,
        "probe_endpoint": endpoint,
        "config_path": str(environment_contract.get("environment_path", "")),
        "configured_model_profiles": configured_profiles,
        "available_models": available_models,
        "available_model_count": len(available_models),
        "coding_model_recommendation": _model_recommendation(
            profile_name="coding_model",
            model=str(environment.get("coding_model", "") or "").strip() or str(config.ollama_model or "").strip(),
            available_names=available_names,
            no_network=no_network,
            ollama_detected=ollama_detected,
        ),
        "reasoning_model_recommendation": _model_recommendation(
            profile_name="reasoning_model",
            model=str(environment.get("reasoning_model", "") or "").strip(),
            available_names=available_names,
            no_network=no_network,
            ollama_detected=ollama_detected,
        ),
        "advisory_execution_allowed": False,
        "prompt_execution_performed": False,
        "coding_execution_performed": False,
        "reasoning_execution_performed": False,
        "network_execution_performed": network_execution_performed,
        "local_only": True,
        "execution_allowed": False,
        "output_path": "",
        "error_summary": error_summary,
        "warnings": sorted({warning for warning in warnings if warning}),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
        "next_safe_action": _next_safe_action(
            blocked=bool(blocked_reasons),
            no_network=no_network,
            ollama_detected=ollama_detected,
        ),
    }


def _read_environment(config: AppConfig, *, config_path: str | Path | None) -> dict[str, Any]:
    if config_path is None:
        return read_local_llm_environment_contract(config)

    resolved = _resolve_output_path(config, config_path)
    warnings: list[str] = []
    environment: dict[str, Any] = {}
    if not resolved.exists():
        warnings.append(f"Local LLM config path does not exist: {resolved}")
    else:
        try:
            loaded = json.loads(resolved.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            warnings.append(f"Local LLM config path could not be parsed: {exc}")
        else:
            if isinstance(loaded, dict):
                environment = loaded
            else:
                warnings.append("Local LLM config path must contain a JSON object.")

    return {
        "ok": True,
        "local_only": True,
        "environment_path": str(resolved),
        "environment_exists": resolved.exists(),
        "local_llm_environment": environment,
        "warnings": sorted(set(warnings)),
        "blockers": [],
    }


def _probe_blockers(*, provider: str, endpoint_base: str, no_network: bool) -> list[str]:
    blockers: list[str] = []
    if provider not in {"ollama", "none", "unknown"}:
        blockers.append(f"Unsupported local LLM provider for M115 probe: {provider}")
    if provider == "ollama" and not no_network and not _is_loopback_url(endpoint_base):
        blockers.append("Configured Ollama provider URL is not loopback; refusing network probe.")
    return blockers


def _fetch_ollama_tags(*, endpoint: str, timeout_seconds: int, urlopen_fn: Any | None) -> list[dict[str, Any]]:
    opener = urlopen_fn or request.urlopen
    req = request.Request(endpoint, method="GET")
    with opener(req, timeout=timeout_seconds) as response:
        raw = response.read().decode("utf-8")
    payload = json.loads(raw)
    return _available_models(payload)


def _available_models(payload: Any) -> list[dict[str, Any]]:
    raw_models = payload.get("models", []) if isinstance(payload, dict) else []
    if not isinstance(raw_models, list):
        return []
    models: list[dict[str, Any]] = []
    for model in raw_models:
        if not isinstance(model, dict):
            continue
        name = str(model.get("name") or model.get("model") or "").strip()
        if not name:
            continue
        details = model.get("details", {}) if isinstance(model.get("details"), dict) else {}
        models.append(
            {
                "name": name,
                "model": str(model.get("model") or name).strip(),
                "modified_at": str(model.get("modified_at", "") or "").strip(),
                "size": model.get("size"),
                "digest": str(model.get("digest", "") or "").strip(),
                "family": str(details.get("family", "") or "").strip(),
                "parameter_size": str(details.get("parameter_size", "") or "").strip(),
                "quantization_level": str(details.get("quantization_level", "") or "").strip(),
                "prompt_execution_allowed_from_probe": False,
            }
        )
    return sorted(models, key=lambda item: str(item["name"]))


def _configured_model_profiles(environment: dict[str, Any], *, config: AppConfig) -> list[dict[str, Any]]:
    specs = (
        ("reasoning_model", "reasoning", str(environment.get("reasoning_model", "") or "").strip()),
        ("coding_model", "coding", str(environment.get("coding_model", "") or "").strip() or str(config.ollama_model or "").strip()),
        ("fallback_model", "fallback", str(environment.get("fallback_model", "") or "").strip()),
    )
    return [
        {
            "profile": profile,
            "role": role,
            "model": model,
            "configured": bool(model),
            "automatic_execution_allowed": False,
            "prompt_execution_allowed_from_probe": False,
        }
        for profile, role, model in specs
    ]


def _model_recommendation(
    *,
    profile_name: str,
    model: str,
    available_names: set[str],
    no_network: bool,
    ollama_detected: bool,
) -> dict[str, Any]:
    configured = bool(model)
    if not configured:
        status = "missing_configuration"
    elif no_network:
        status = "configured_unverified_no_network"
    elif not ollama_detected:
        status = "configured_unverified_provider_unavailable"
    elif model in available_names:
        status = "configured_and_visible"
    else:
        status = "configured_not_visible"
    return {
        "profile": profile_name,
        "model": model,
        "status": status,
        "operator_review_required": True,
        "may_execute_from_probe": False,
    }


def _ollama_expected(*, provider: str, endpoint_base: str, profiles: list[dict[str, Any]]) -> bool:
    return provider == "ollama" or bool(endpoint_base) or any(bool(profile.get("configured")) for profile in profiles)


def _next_safe_action(*, blocked: bool, no_network: bool, ollama_detected: bool) -> str:
    if blocked:
        return "Fix the provider configuration or rerun with --no-network before probing local Ollama."
    if no_network:
        return "Review configured model profiles; rerun without --no-network only when a loopback Ollama tags check is desired."
    if ollama_detected:
        return "Review visible model metadata before any separate operator-gated advisory workflow."
    return "Start or configure local Ollama if model metadata is needed; do not treat provider absence as queue completion evidence."


def _positive_int_or_default(value: Any, default: int) -> int:
    if isinstance(value, int) and not isinstance(value, bool) and value > 0:
        return value
    if isinstance(value, str) and value.strip().isdigit():
        parsed = int(value.strip())
        return parsed if parsed > 0 else default
    return default


def _is_loopback_url(url: str) -> bool:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    return parsed.scheme in {"http", "https"} and host in {"localhost", "127.0.0.1", "::1"}


def _default_output_path(config: AppConfig) -> Path:
    timestamp = _now_iso().replace(":", "").replace("-", "")
    return (config.artifact_root / "local_ollama_provider_probes" / f"{timestamp}-ollama-provider-probe.json").resolve()


def _resolve_output_path(config: AppConfig, path: str | Path) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate.resolve()
    return (config.repo_root / candidate).resolve()


def _write_json_output(output_path: Path, payload: dict[str, Any], *, force: bool) -> dict[str, Any]:
    if output_path.exists() and not force:
        return {"ok": False, "reason": f"Output path already exists: {output_path}", "output_path": str(output_path)}
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return {"ok": True, "output_path": str(output_path)}


def _stdout_result(command: str, payload: dict[str, Any], output_format: str, markdown: str) -> dict[str, Any]:
    fmt = str(output_format or "markdown").lower().strip()
    if fmt not in {"json", "markdown"}:
        return {
            "command": command,
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
        "wrote_output_file": bool(payload.get("output_path")),
        "stdout": json.dumps(payload, indent=2) if fmt == "json" else markdown,
        "payload": payload,
    }


def _render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Local Ollama Provider Probe",
        "",
        f"- probe_type: {payload.get('probe_type')}",
        f"- probed: {payload.get('probed')}",
        f"- blocked: {payload.get('blocked')}",
        f"- ollama_expected: {payload.get('ollama_expected')}",
        f"- ollama_detected: {payload.get('ollama_detected')}",
        f"- probe_method: {payload.get('probe_method')}",
        f"- network_execution_performed: {payload.get('network_execution_performed')}",
        f"- prompt_execution_performed: {payload.get('prompt_execution_performed')}",
        f"- next_safe_action: {payload.get('next_safe_action', '')}",
        "",
        "## Configured Model Profiles",
    ]
    for profile in payload.get("configured_model_profiles", []):
        if isinstance(profile, dict):
            lines.append(f"- {profile.get('profile')}: {profile.get('model', '') or '<missing>'}")
    blockers = payload.get("blocked_reasons", []) if isinstance(payload.get("blocked_reasons"), list) else []
    if blockers:
        lines.extend(["", "## Blocked Reasons"])
        lines.extend(f"- {reason}" for reason in blockers)
    warnings = payload.get("warnings", []) if isinstance(payload.get("warnings"), list) else []
    if warnings:
        lines.extend(["", "## Warnings"])
        lines.extend(f"- {warning}" for warning in warnings)
    return "\n".join(lines)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()
