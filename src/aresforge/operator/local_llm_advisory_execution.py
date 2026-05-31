from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
import socket
from typing import Any, Protocol
from urllib import error, request
from urllib.parse import urlparse

from aresforge.config import AppConfig
from aresforge.operator.local_project_factory import read_local_llm_environment_contract
from aresforge.operator.machine_safety_gate_engine import evaluate_machine_safety_gates

COMMAND_NAME = "run-local-llm-advisory"
EXECUTION_RECORD_TYPE = "local_llm_advisory_execution"
EXECUTION_VERSION = "m134.1"
DEFAULT_OLLAMA_BASE_URL = "http://127.0.0.1:11434"
DEFAULT_TIMEOUT_SECONDS = 60

_BOUNDARY_CONFIRMATIONS = (
    "M134 local LLM advisory execution is local-only.",
    "M134 may submit one advisory prompt only to a supported local provider after local_llm_execution machine gates pass.",
    "M134 supports Ollama only and requires a localhost, 127.0.0.1, or ::1 provider URL.",
    "M134 captures advisory output as a local artifact and never applies it.",
    "M134 does not mutate source files, tests, queue status, project state, GitHub, gh, Codex, agents, workflows, or next items.",
)


class LocalAdvisoryProvider(Protocol):
    provider_name: str

    def generate(self, *, model: str, prompt: str, timeout_seconds: int) -> str:
        ...


@dataclass(frozen=True)
class OllamaAdvisoryProvider:
    base_url: str
    urlopen_fn: Any | None = None

    provider_name: str = "ollama"

    def generate(self, *, model: str, prompt: str, timeout_seconds: int) -> str:
        endpoint = self.base_url.rstrip("/") + "/api/generate"
        body = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode("utf-8")
        req = request.Request(endpoint, data=body, headers={"Content-Type": "application/json"}, method="POST")
        opener = self.urlopen_fn or request.urlopen
        with opener(req, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return str(payload.get("response", "")).strip()


def run_local_llm_advisory_execution(
    config: AppConfig,
    *,
    item_id: str,
    artifact_path: str | Path,
    provider: str = "ollama",
    model: str | None = None,
    dry_run: bool = False,
    output: str | Path | None = None,
    force: bool = False,
    timeout_seconds: int | None = None,
    queue_path: str | Path | None = None,
    output_format: str = "json",
    provider_client: LocalAdvisoryProvider | None = None,
) -> dict[str, Any]:
    fmt = str(output_format or "json").strip().lower()
    if fmt != "json":
        return _error("invalid_format", {"format": output_format, "supported_formats": ["json"]})

    normalized_item_id = str(item_id or "").strip()
    resolved_artifact_path = _resolve(config.repo_root, artifact_path)
    resolved_output = _resolve(config.repo_root, output) if output else None
    preflight_output_blocker = ""
    if resolved_output is not None and resolved_output.exists() and not force:
        preflight_output_blocker = "Output file already exists. Re-run with --force to overwrite."

    artifact, artifact_errors = _load_artifact(resolved_artifact_path)
    prompt = _extract_prompt(artifact)
    environment = read_local_llm_environment_contract(config)
    env = environment.get("local_llm_environment", {})
    if not isinstance(env, dict):
        env = {}

    normalized_provider = str(provider or env.get("local_llm_provider") or "ollama").strip() or "ollama"
    configured_base_url = str(env.get("provider_base_url", "") or "").strip()
    provider_base_url = configured_base_url or str(config.ollama_base_url or DEFAULT_OLLAMA_BASE_URL).strip()
    selected_model = str(model or artifact.get("requested_model_profile") or env.get("reasoning_model") or config.ollama_model or "").strip()
    timeout = _positive_int(timeout_seconds) or _positive_int(env.get("request_timeout_seconds")) or DEFAULT_TIMEOUT_SECONDS

    gate_result = evaluate_machine_safety_gates(
        config,
        item_id=normalized_item_id,
        gate_profile="local_llm_execution",
        artifact_path=resolved_artifact_path,
        execution_record=resolved_artifact_path,
        queue_path=queue_path,
        output_format="json",
    )
    machine_gate = gate_result.get("payload", {}) if isinstance(gate_result, dict) else {}

    blocked_reasons = _blocked_reasons(
        artifact_errors=artifact_errors,
        artifact=artifact,
        item_id=normalized_item_id,
        prompt=prompt,
        provider=normalized_provider,
        provider_base_url=provider_base_url,
        model=selected_model,
        machine_gate=machine_gate,
        preflight_output_blocker=preflight_output_blocker,
    )

    response_artifact_path = ""
    response_summary = "Dry-run: provider invocation skipped." if dry_run and not blocked_reasons else ""
    executed = False

    if not blocked_reasons and not dry_run:
        advisory_provider = provider_client or OllamaAdvisoryProvider(base_url=provider_base_url)
        try:
            response_text = advisory_provider.generate(model=selected_model, prompt=prompt, timeout_seconds=timeout)
        except (error.URLError, TimeoutError, socket.timeout, OSError, json.JSONDecodeError) as exc:
            blocked_reasons.append(f"Local provider advisory generation failed: {exc}")
        else:
            executed = True
            response_payload = _response_payload(
                item_id=normalized_item_id,
                artifact_path=resolved_artifact_path,
                provider=normalized_provider,
                model=selected_model,
                response_text=response_text,
            )
            response_path = _default_response_artifact_path(config, normalized_item_id)
            response_path.parent.mkdir(parents=True, exist_ok=True)
            response_path.write_text(json.dumps(response_payload, indent=2) + "\n", encoding="utf-8")
            response_artifact_path = str(response_path)
            response_summary = _summarize_response(response_text)

    blocked = bool(blocked_reasons)
    payload = {
        "execution_record_type": EXECUTION_RECORD_TYPE,
        "execution_version": EXECUTION_VERSION,
        "item_id": normalized_item_id,
        "artifact_path": str(resolved_artifact_path),
        "provider": normalized_provider,
        "model": selected_model,
        "dry_run": bool(dry_run),
        "executed": bool(executed and not blocked),
        "blocked": blocked,
        "blocked_reasons": _dedupe(blocked_reasons),
        "machine_gates_checked": bool(machine_gate),
        "machine_gates_passed": bool(machine_gate.get("passed")) and not bool(machine_gate.get("blocked")),
        "prompt_tokens_estimated": _estimate_tokens(prompt),
        "response_artifact_path": response_artifact_path if not blocked else "",
        "response_summary": response_summary if not blocked else "",
        "advisory_only": True,
        "patch_application_performed": False,
        "queue_mutation_performed": False,
        "github_execution_performed": False,
        "codex_execution_performed": False,
        "local_only": True,
        "next_safe_action": _next_safe_action(blocked=blocked, dry_run=bool(dry_run), executed=bool(executed and not blocked)),
        "local_provider_endpoint": provider_base_url,
        "timeout_seconds": timeout,
        "provider_boundary": {
            "supported_providers": ["ollama"],
            "provider_url_local_only": _is_local_provider_url(provider_base_url),
            "remote_provider_allowed": False,
            "allowed_endpoint": "/api/generate",
            "remote_network_allowed": False,
        },
        "artifact_type": str(artifact.get("artifact_type", "")),
        "source_advisory_only": bool(artifact.get("execution_allowed") is False),
        "external_execution_performed": False,
        "model_execution_performed": bool(executed and not blocked),
        "source_mutation_performed": False,
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
        "recorded_at": _now_iso(),
        "machine_gate_result": machine_gate,
    }
    return _emit_or_write(config=config, payload=payload, output=resolved_output, force=force)


def _blocked_reasons(
    *,
    artifact_errors: list[str],
    artifact: dict[str, Any],
    item_id: str,
    prompt: str,
    provider: str,
    provider_base_url: str,
    model: str,
    machine_gate: dict[str, Any],
    preflight_output_blocker: str,
) -> list[str]:
    reasons: list[str] = []
    reasons.extend(artifact_errors)
    if preflight_output_blocker:
        reasons.append(preflight_output_blocker)
    if artifact and str(artifact.get("item_id", "")).strip() not in {"", item_id}:
        reasons.append("Advisory artifact item_id does not match the requested queue item.")
    if not prompt:
        reasons.append("Advisory artifact does not contain an advisory_prompt or prompt field.")
    if provider != "ollama":
        reasons.append(f"Unsupported or remote provider requested: {provider}. M134 supports only local Ollama.")
    if provider == "ollama" and not _is_local_provider_url(provider_base_url):
        reasons.append("Ollama provider URL must point to localhost, 127.0.0.1, or ::1.")
    if not model:
        reasons.append("Local Ollama model is not configured or supplied.")
    if machine_gate.get("passed") is not True or machine_gate.get("blocked") is True:
        reasons.append("Machine safety gate profile local_llm_execution did not pass.")
        reasons.extend(_list(machine_gate.get("blocked_reasons")))
    if artifact.get("patch_application_allowed") is True:
        reasons.append("Advisory artifact must not allow patch application.")
    if artifact.get("execution_allowed") is True:
        reasons.append("Source advisory artifact must not authorize execution by itself.")
    return _dedupe(reasons)


def _load_artifact(path: Path) -> tuple[dict[str, Any], list[str]]:
    if not path.exists():
        return {}, [f"Advisory artifact path does not exist: {path}"]
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {}, [f"Advisory artifact is not valid JSON: {exc.msg}."]
    except OSError as exc:
        return {}, [f"Advisory artifact could not be read: {exc}."]
    if not isinstance(raw, dict):
        return {}, ["Advisory artifact JSON root must be an object."]
    return raw, []


def _extract_prompt(artifact: dict[str, Any]) -> str:
    for key in ("advisory_prompt", "prompt", "prompt_text"):
        text = str(artifact.get(key, "") or "").strip()
        if text:
            return text
    return ""


def _response_payload(
    *,
    item_id: str,
    artifact_path: Path,
    provider: str,
    model: str,
    response_text: str,
) -> dict[str, Any]:
    return {
        "artifact_type": "local_llm_advisory_response",
        "item_id": item_id,
        "source_artifact_path": str(artifact_path),
        "provider": provider,
        "model": model,
        "response_text": response_text,
        "advisory_only": True,
        "patch_application_performed": False,
        "queue_mutation_performed": False,
        "github_execution_performed": False,
        "codex_execution_performed": False,
        "local_only": True,
        "recorded_at": _now_iso(),
    }


def _emit_or_write(
    *,
    config: AppConfig,
    payload: dict[str, Any],
    output: Path | None,
    force: bool,
) -> dict[str, Any]:
    rendered = json.dumps(payload, indent=2)
    if output is None:
        return {
            "command": COMMAND_NAME,
            "ok": not bool(payload.get("blocked")),
            "local_only": True,
            "format": "json",
            "wrote_output_file": False,
            "stdout": rendered,
            "payload": payload,
        }
    if output.exists() and not force:
        blocked = dict(payload)
        blocked["blocked"] = True
        blocked["executed"] = False
        blocked["blocked_reasons"] = _dedupe(
            [*_list(blocked.get("blocked_reasons")), "Output file already exists. Re-run with --force to overwrite."]
        )
        rendered = json.dumps(blocked, indent=2)
        return {
            "command": COMMAND_NAME,
            "ok": False,
            "local_only": True,
            "format": "json",
            "output": str(output),
            "force": force,
            "wrote_output_file": False,
            "stdout": rendered,
            "payload": blocked,
        }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered + "\n", encoding="utf-8")
    return {
        "command": COMMAND_NAME,
        "ok": not bool(payload.get("blocked")),
        "local_only": True,
        "format": "json",
        "output": str(output),
        "force": force,
        "wrote_output_file": True,
        "payload": payload,
    }


def _resolve(repo_root: Path, value: str | Path | None) -> Path:
    if value is None:
        raise ValueError("Path value is required.")
    path = Path(value)
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


def _default_response_artifact_path(config: AppConfig, item_id: str) -> Path:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    return config.artifact_root / "local_llm_advisory" / "responses" / f"{stamp}-{_safe_id(item_id)}-response.json"


def _is_local_provider_url(provider_base_url: str) -> bool:
    parsed = urlparse(provider_base_url)
    host = (parsed.hostname or "").lower()
    return parsed.scheme in {"http", "https"} and host in {"localhost", "127.0.0.1", "::1"}


def _estimate_tokens(prompt: str) -> int:
    text = str(prompt or "")
    if not text:
        return 0
    return max(1, (len(text) + 3) // 4)


def _summarize_response(response_text: str) -> str:
    text = " ".join(str(response_text or "").split())
    if len(text) <= 240:
        return text
    return text[:237].rstrip() + "..."


def _positive_int(value: Any) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool) and value > 0:
        return value
    if isinstance(value, str) and value.strip().isdigit():
        parsed = int(value.strip())
        return parsed if parsed > 0 else None
    return None


def _safe_id(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in str(value or "").strip().lower())
    return cleaned.strip("-") or "local-llm-advisory"


def _next_safe_action(*, blocked: bool, dry_run: bool, executed: bool) -> str:
    if blocked:
        return "Resolve blocked reasons before any local LLM advisory execution."
    if dry_run:
        return "Dry-run passed; review the execution record before any explicit non-dry-run local advisory request."
    if executed:
        return "Review the advisory response artifact manually; do not apply patches or complete queue items from it."
    return "No provider execution was performed."


def _list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(entry).strip() for entry in value if str(entry).strip()]
    if value in (None, ""):
        return []
    return [str(value).strip()]


def _dedupe(values: list[Any] | tuple[Any, ...] | Any) -> list[str]:
    deduped: list[str] = []
    for value in values:
        text = str(value).strip()
        if text and text not in deduped:
            deduped.append(text)
    return deduped


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _error(error_name: str, details: dict[str, Any]) -> dict[str, Any]:
    return {
        "command": COMMAND_NAME,
        "ok": False,
        "local_only": True,
        "error": error_name,
        "details": details,
    }
