from __future__ import annotations

import json
import socket
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib import error, request

from aresforge.config import AppConfig
from aresforge.operator.llm_decision_matrix import build_llm_decision_matrix
from aresforge.operator.local_llm_provider import build_ollama_health_and_model_inspection
from aresforge.operator.local_project_queue import inspect_queue_item, resolve_project_queue_path

ADVISORY_RUN_ARTIFACT_VERSION = "m85.1"

_BOUNDARY_CONFIRMATIONS = (
    "M85 local LLM advisory run artifacts are local-only.",
    "Prompt artifacts are advisory and require operator review.",
    "Model invocation is optional and requires the explicit --run flag.",
    "Only the local Ollama /api/tags and /api/generate endpoints may be used by the explicit run path.",
    "No generated response is applied to repository files.",
    "No queue item status is mutated from advisory output.",
    "No queue item is completed from advisory output.",
    "No automatic next-item execution.",
    "No GitHub API calls.",
    "No gh calls.",
    "No issues, PRs, workflows, daemons, watchers, schedulers, or external workflow behavior.",
)


def prepare_local_llm_advisory_run_artifact(
    config: AppConfig,
    *,
    item_id: str,
    queue_path: str | Path | None = None,
    registry_path: str | Path | None = None,
    model: str | None = None,
    run: bool = False,
    run_id: str | None = None,
    output_format: str = "json",
    force: bool = False,
) -> dict[str, Any]:
    payload = build_local_llm_advisory_run_artifact(
        config,
        item_id=item_id,
        queue_path=queue_path,
        registry_path=registry_path,
        model=model,
        run=run,
        run_id=run_id,
        force=force,
    )
    return _stdout_result(
        "prepare-local-llm-advisory-run",
        payload,
        output_format,
        _render_markdown(payload),
    )


def build_local_llm_advisory_run_artifact(
    config: AppConfig,
    *,
    item_id: str,
    queue_path: str | Path | None = None,
    registry_path: str | Path | None = None,
    model: str | None = None,
    run: bool = False,
    run_id: str | None = None,
    force: bool = False,
    urlopen_fn: Any | None = None,
) -> dict[str, Any]:
    normalized_item_id = str(item_id or "").strip()
    normalized_run_id = _safe_id(run_id or f"{_timestamp()}-{normalized_item_id or 'unknown-item'}")
    artifact_dir = config.artifact_root / "local_llm_advisory" / "generated"
    prompt_path = artifact_dir / f"{normalized_run_id}-prompt.md"
    response_path = artifact_dir / f"{normalized_run_id}-response.txt"
    metadata_path = artifact_dir / f"{normalized_run_id}-metadata.json"

    item_payload = inspect_queue_item(config, item_id=normalized_item_id, queue_path=queue_path)
    item_root = item_payload.get("payload", {}) if isinstance(item_payload.get("payload"), dict) else {}
    item = item_root.get("item", {}) if isinstance(item_root.get("item"), dict) else {}
    matrix = build_llm_decision_matrix(
        config,
        item_id=normalized_item_id,
        queue_path=resolve_project_queue_path(config.repo_root, queue_path),
        registry_path=registry_path,
    )
    decision = matrix.get("routing_decision", {}) if isinstance(matrix.get("routing_decision"), dict) else {}
    selected_model = str(model or decision.get("recommended_model") or config.ollama_model or "").strip()
    provider_base_url = str(config.ollama_base_url or "").rstrip("/")

    blockers = _unique_strings(
        [
            *item_payload.get("blockers", []),
            *([item_payload.get("error", "")] if not item_payload.get("ok", False) else []),
            *matrix.get("blockers", []),
        ]
    )
    warnings = _unique_strings(
        [
            *item_payload.get("warnings", []),
            *matrix.get("warnings", []),
        ]
    )

    prompt_text = _build_prompt_text(
        item=item,
        matrix=matrix,
        item_id=normalized_item_id,
        model=selected_model,
        run_requested=run,
    )

    artifact_dir.mkdir(parents=True, exist_ok=True)
    if prompt_path.exists() and not force:
        blockers.append(f"Prompt artifact already exists: {prompt_path}")
    else:
        prompt_path.write_text(prompt_text, encoding="utf-8")

    run_status = "prepared_not_run"
    response_text = ""
    response_written = False
    provider_available = None
    health = build_ollama_health_and_model_inspection(config, urlopen_fn=urlopen_fn) if run else {}
    if run:
        provider_available = bool(health.get("available", False))
        visible_models = {str(entry.get("name") or entry.get("model") or "").strip() for entry in health.get("models", []) if isinstance(entry, dict)}
        if blockers:
            run_status = "blocked"
        elif not provider_available:
            run_status = "unavailable"
            warnings.append("Local LLM advisory run was not invoked because Ollama is unavailable.")
        elif selected_model and visible_models and selected_model not in visible_models:
            run_status = "unavailable"
            warnings.append(f"Selected model is not visible from Ollama /api/tags: {selected_model}")
        else:
            run_result = _run_ollama_advisory_generation(
                endpoint=f"{provider_base_url}/api/generate",
                model=selected_model,
                prompt=prompt_text,
                timeout_seconds=_health_timeout_seconds(health),
                urlopen_fn=urlopen_fn,
            )
            run_status = str(run_result.get("run_status", "failed"))
            response_text = str(run_result.get("response_text", ""))
            if run_result.get("ok", False):
                response_path.write_text(response_text, encoding="utf-8")
                response_written = True
            else:
                warnings.append(str(run_result.get("error_summary", "Local LLM advisory run failed.")))

    metadata = {
        "ok": not blockers,
        "local_only": True,
        "advisory_only": True,
        "contract_version": ADVISORY_RUN_ARTIFACT_VERSION,
        "item_id": normalized_item_id,
        "run_id": normalized_run_id,
        "run_requested": run,
        "run_status": run_status,
        "prompt_path": str(prompt_path),
        "response_path": str(response_path) if response_written else "",
        "metadata_path": str(metadata_path),
        "provider_model_metadata": {
            "provider": "ollama",
            "endpoint": provider_base_url,
            "model": selected_model,
            "provider_available": provider_available,
            "health_endpoint": health.get("endpoint", "") if isinstance(health, dict) else "",
            "visible_models": health.get("models", []) if isinstance(health, dict) else [],
        },
        "safety_boundary": _safety_boundary(run),
        "warnings": _unique_strings(warnings),
        "blockers": _unique_strings(blockers),
        "next_safe_action": _next_safe_action(run_status, bool(blockers)),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }
    if run:
        metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return metadata


def _run_ollama_advisory_generation(
    *,
    endpoint: str,
    model: str,
    prompt: str,
    timeout_seconds: int,
    urlopen_fn: Any | None,
) -> dict[str, Any]:
    body = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode("utf-8")
    req = request.Request(endpoint, data=body, headers={"Content-Type": "application/json"}, method="POST")
    opener = urlopen_fn or request.urlopen
    try:
        with opener(req, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (error.URLError, TimeoutError, socket.timeout, OSError) as exc:
        return {"ok": False, "run_status": "unavailable", "error_summary": f"Ollama advisory generation unavailable: {exc}"}
    except json.JSONDecodeError as exc:
        return {"ok": False, "run_status": "failed", "error_summary": f"Ollama advisory generation returned invalid JSON: {exc}"}
    text = str(payload.get("response", "")).strip()
    return {"ok": True, "run_status": "completed_advisory", "response_text": text}


def _build_prompt_text(*, item: dict[str, Any], matrix: dict[str, Any], item_id: str, model: str, run_requested: bool) -> str:
    title = str(item.get("title", "")).strip()
    description = str(item.get("description", "")).strip()
    notes = str(item.get("notes", "")).strip()
    decision = matrix.get("routing_decision", {}) if isinstance(matrix.get("routing_decision"), dict) else {}
    validation = matrix.get("validation_burden", {}) if isinstance(matrix.get("validation_burden"), dict) else {}
    return "\n".join(
        [
            "# Local LLM Advisory Prompt",
            "",
            f"Queue item: {item_id}",
            f"Title: {title}",
            f"Description: {description}",
            f"Notes: {notes}",
            "",
            "## Advisory Context",
            f"Recommended engine: {decision.get('recommended_engine', '')}",
            f"Recommended lane: {decision.get('recommended_lane', '')}",
            f"Selected model: {model}",
            f"Validation burden: {validation.get('validation_burden', '')}",
            f"Run requested now: {run_requested}",
            "",
            "## Required Response JSON Fields",
            "- summary",
            "- plan",
            "- risks",
            "- suggested_validation",
            "- manual_review_required",
            "- repo_mutation_allowed",
            "- queue_mutation_allowed",
            "- automatic_next_item_execution_allowed",
            "",
            "## Safety Boundaries",
            "- Advisory output only.",
            "- Do not edit files.",
            "- Do not complete or start queue items.",
            "- Do not call GitHub, gh, workflows, daemons, watchers, schedulers, or external services.",
            "- Set repo_mutation_allowed, queue_mutation_allowed, and automatic_next_item_execution_allowed to false.",
        ]
    )


def _safe_id(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in str(value).strip())
    return cleaned.strip("-") or "local-llm-advisory-run"


def _timestamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def _health_timeout_seconds(health: dict[str, Any]) -> int:
    timeout = health.get("request_timeout_seconds")
    return timeout if isinstance(timeout, int) and timeout > 0 else 60


def _safety_boundary(run_requested: bool) -> dict[str, Any]:
    return {
        "local_only": True,
        "advisory_only": True,
        "prompt_artifact_generation_allowed": True,
        "provider_invocation_allowed_from_this_command": bool(run_requested),
        "operator_explicit_run_required": True,
        "repo_mutation_allowed": False,
        "queue_mutation_allowed": False,
        "queue_completion_allowed": False,
        "automatic_next_item_execution_allowed": False,
        "external_workflow_allowed": False,
        "github_api_allowed": False,
        "gh_allowed": False,
    }


def _next_safe_action(run_status: str, blocked: bool) -> str:
    if blocked:
        return "Resolve advisory artifact blockers; do not invoke a local model or mutate repo files."
    if run_status == "prepared_not_run":
        return "Review the advisory prompt artifact; run local LLM advisory only with an explicit operator command."
    if run_status == "unavailable":
        return "Continue without local LLM advisory output or start/configure Ollama and retry explicitly."
    if run_status == "completed_advisory":
        return "Review advisory response manually; do not auto-apply code or complete queue items from the response."
    return "Review advisory run metadata before taking any manual follow-up."


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
        "# Local LLM Advisory Run Artifact",
        "",
        f"- ok: {payload.get('ok')}",
        f"- item_id: {payload.get('item_id', '')}",
        f"- run_requested: {payload.get('run_requested')}",
        f"- run_status: {payload.get('run_status', '')}",
        f"- prompt_path: {payload.get('prompt_path', '')}",
        f"- response_path: {payload.get('response_path', '')}",
        f"- next_safe_action: {payload.get('next_safe_action', '')}",
        "",
        "## Boundaries",
    ]
    lines.extend(f"- {entry}" for entry in payload.get("boundary_confirmations", []))
    return "\n".join(lines)
