from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.agent_registry import build_agent_registry
from aresforge.operator.llm_decision_policy import recommend_llm_decision
from aresforge.operator.local_project_queue import resolve_project_queue_path
from aresforge.operator.machine_safety_gate_engine import evaluate_machine_safety_gates

COMMAND_NAME = "normalize-agent-step-result"
RECORD_TYPE = "agent_step_result_normalization_v1"
NORMALIZATION_VERSION = "m146.1"
DEFAULT_ITEM_ID = "m146-agent-step-result-normalization"
DEFAULT_PROJECT_ID = "aresforge"

_TERMINAL_SUCCESS_STATUSES = frozenset({"completed", "complete", "succeeded", "success", "ok", "ready"})
_BLOCKED_STATUSES = frozenset({"blocked", "gate_blocked", "default_denied", "denied"})
_FAILED_STATUSES = frozenset({"failed", "failure", "error", "errored", "process_nonzero"})
_INTERRUPTED_STATUSES = frozenset({"interrupted", "cancelled", "canceled", "timeout", "timed_out"})

_PROHIBITED_OPERATIONS: tuple[str, ...] = (
    "merge_pull_request",
    "force_push",
    "update_protected_branch",
    "enable_auto_merge",
    "create_release",
    "modify_github_workflow",
    "apply_source_patch_from_generated_output",
    "automatic_next_item_execution",
    "automatic_retry_loop",
    "bypass_machine_safety_gate",
)

_BOUNDARY_CONFIRMATIONS: tuple[str, ...] = (
    "M146 normalizes one local agent step result artifact into a stable orchestrator evaluation schema.",
    "This command performs no agent, Codex, model, GitHub, patch, validation-command, queue, or retry execution.",
    "Top-level execution flags describe the source step result; normalizer_execution_flags describe this command and remain false.",
    "Recovery guidance is advisory and must flow through separate explicit machine-gated commands.",
)


def normalize_agent_step_result(
    config: AppConfig,
    *,
    result_path: str | Path,
    item_id: str = DEFAULT_ITEM_ID,
    project_id: str = DEFAULT_PROJECT_ID,
    queue_path: str | Path | None = None,
    output: str | Path | None = None,
    force: bool = False,
    output_format: str = "json",
) -> dict[str, Any]:
    fmt = str(output_format or "json").strip().lower()
    if fmt != "json":
        return _error("invalid_format", {"format": output_format, "supported_formats": ["json"]})

    requested_item_id = str(item_id or DEFAULT_ITEM_ID).strip() or DEFAULT_ITEM_ID
    requested_project_id = str(project_id or DEFAULT_PROJECT_ID).strip() or DEFAULT_PROJECT_ID
    resolved_result_path = _resolve(config.repo_root, result_path)
    raw_loaded, artifact_errors = _load_result_artifact(resolved_result_path)
    source = _unwrap_result_payload(raw_loaded)

    effective_item_id = _first_text(
        source.get("item_id"),
        raw_loaded.get("item_id") if isinstance(raw_loaded, dict) else "",
        requested_item_id,
    )
    effective_project_id = _first_text(
        source.get("project_id"),
        raw_loaded.get("project_id") if isinstance(raw_loaded, dict) else "",
        requested_project_id,
    )
    run_id = _first_text(
        source.get("run_id"),
        raw_loaded.get("run_id") if isinstance(raw_loaded, dict) else "",
        f"{effective_item_id}:agent-step-result-normalization-v1",
    )

    gate_payload = _gate_payload(config, item_id=effective_item_id, queue_path=queue_path)
    normalization_gate = _gate_summary(
        gate_payload,
        source="normalization_inspection",
        step_id=_first_text(source.get("step_id"), source.get("id")),
        agent_id=_first_text(source.get("agent_id"), source.get("agent")),
    )
    source_gates = _source_gate_summaries(source)
    machine_gates_checked = [normalization_gate, *source_gates]
    source_gates_passed = _source_machine_gates_passed(source, source_gates)
    machine_gates_passed = bool(normalization_gate.get("passed")) and source_gates_passed

    warnings = _warnings(
        source=source,
        artifact_errors=artifact_errors,
        gate_payload=gate_payload,
        requested_project_id=requested_project_id,
        effective_project_id=effective_project_id,
    )
    source_status = _first_text(source.get("status"), raw_loaded.get("status") if isinstance(raw_loaded, dict) else "")
    normalized_status = _normalized_status(source_status, source=source, artifact_errors=artifact_errors)
    blocked_reasons = _blocked_reasons(
        source=source,
        artifact_errors=artifact_errors,
        gate_payload=gate_payload,
        source_gates=source_gates,
    )
    blocked = bool(blocked_reasons) or normalized_status == "blocked"
    if blocked and normalized_status not in {"blocked", "invalid"}:
        normalized_status = "blocked"

    source_flags = _source_execution_flags(source)
    payload: dict[str, Any] = {
        "record_type": RECORD_TYPE,
        "artifact_type": RECORD_TYPE,
        "normalization_version": NORMALIZATION_VERSION,
        "generated": True,
        "generated_at": _now_iso(),
        "item_id": effective_item_id,
        "project_id": effective_project_id,
        "run_id": run_id,
        "status": normalized_status,
        "blocked": blocked,
        "blocked_reasons": _dedupe(blocked_reasons),
        "warnings": warnings,
        "machine_gates_checked": machine_gates_checked,
        "machine_gates_passed": machine_gates_passed,
        "artifacts_created": _source_artifacts(source),
        "mutation_performed": source_flags["mutation_performed"],
        "external_execution_performed": source_flags["external_execution_performed"],
        "model_execution_performed": source_flags["model_execution_performed"],
        "codex_execution_performed": source_flags["codex_execution_performed"],
        "github_execution_performed": source_flags["github_execution_performed"],
        "patch_application_performed": source_flags["patch_application_performed"],
        "local_only": _source_local_only(source),
        "next_safe_action": _next_safe_action(
            blocked=blocked,
            status=normalized_status,
            source_flags=source_flags,
        ),
        "result_path": str(resolved_result_path),
        "result_artifact_found": resolved_result_path.exists(),
        "result_artifact_valid_json": not artifact_errors and bool(source),
        "source_record_type": _first_text(
            source.get("record_type"),
            source.get("artifact_type"),
            source.get("execution_record_type"),
            raw_loaded.get("command") if isinstance(raw_loaded, dict) else "",
        ),
        "source_status": source_status,
        "step_id": _first_text(source.get("step_id"), source.get("id")),
        "sequence": _optional_int(source.get("sequence"), source.get("step_index"), source.get("index")),
        "agent_id": _first_text(source.get("agent_id"), source.get("agent")),
        "mode": _first_text(source.get("mode"), source.get("execution_mode")),
        "dry_run": bool(source.get("dry_run")),
        "result_summary": _result_summary(source),
        "source_blocked": bool(source.get("blocked")) or source_status.strip().lower() in _BLOCKED_STATUSES,
        "source_blocked_reasons": _dedupe(_list(source.get("blocked_reasons")) + _list(source.get("errors"))),
        "source_warnings": _dedupe(_list(source.get("warnings"))),
        "source_execution_flags": source_flags,
        "normalizer_execution_flags": {
            "mutation_performed": False,
            "external_execution_performed": False,
            "model_execution_performed": False,
            "codex_execution_performed": False,
            "github_execution_performed": False,
            "patch_application_performed": False,
            "queue_mutation_performed": False,
            "validation_command_execution_performed": False,
        },
        "queue_path": str(resolve_project_queue_path(config.repo_root, queue_path)),
        "queue_item_found": _queue_item_found(config, item_id=effective_item_id, queue_path=queue_path),
        "machine_gate_profile_for_inspection": "read_only_agent",
        "agent_registry_summary": _agent_summary(config, agent_id=_first_text(source.get("agent_id"), source.get("agent"))),
        "llm_decision_policy_summary": _llm_decision_summary(
            config,
            item_id=effective_item_id,
            queue_path=queue_path,
        ),
        "orchestrator_evaluation": _orchestrator_evaluation(
            status=normalized_status,
            blocked=blocked,
            machine_gates_passed=machine_gates_passed,
            source_flags=source_flags,
        ),
        "prohibited_operations": list(_PROHIBITED_OPERATIONS),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
        "recommended_normalization_artifact_path": str(
            (config.repo_root / ".aresforge" / "orchestrator" / "step_results" / "m146-normalized-step-result.json").resolve()
        ),
    }
    return _emit_or_write(config=config, payload=payload, output=output, force=force)


def _load_result_artifact(path: Path) -> tuple[dict[str, Any], list[str]]:
    if not path.exists():
        return {}, [f"Agent step result artifact is missing: {path}"]
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        return {}, [f"Agent step result artifact is not valid JSON: {exc.msg}."]
    except OSError as exc:
        return {}, [f"Agent step result artifact could not be read: {exc}."]
    if not isinstance(raw, dict):
        return {}, ["Agent step result artifact JSON root must be an object."]
    return raw, []


def _unwrap_result_payload(raw: dict[str, Any]) -> dict[str, Any]:
    payload = raw.get("payload")
    if isinstance(payload, dict) and payload:
        return payload
    stdout = raw.get("stdout")
    if isinstance(stdout, str) and stdout.strip().startswith("{"):
        try:
            parsed = json.loads(stdout)
        except json.JSONDecodeError:
            parsed = {}
        if isinstance(parsed, dict):
            return parsed
    return raw if isinstance(raw, dict) else {}


def _source_gate_summaries(source: dict[str, Any]) -> list[dict[str, Any]]:
    raw_gates = source.get("machine_gates_checked")
    gates: list[dict[str, Any]] = []
    if isinstance(raw_gates, list):
        for index, gate in enumerate(raw_gates, start=1):
            if not isinstance(gate, dict):
                continue
            gates.append(_gate_summary(gate, source="source_step_result", fallback_index=index))
    return gates


def _source_machine_gates_passed(source: dict[str, Any], source_gates: list[dict[str, Any]]) -> bool:
    if source_gates:
        return all(bool(gate.get("passed")) and not bool(gate.get("blocked")) for gate in source_gates)
    if "machine_gates_passed" in source:
        return bool(source.get("machine_gates_passed"))
    return True


def _gate_payload(config: AppConfig, *, item_id: str, queue_path: str | Path | None) -> dict[str, Any]:
    result = evaluate_machine_safety_gates(
        config,
        item_id=item_id,
        gate_profile="read_only_agent",
        queue_path=queue_path,
        output_format="json",
    )
    return result.get("payload", {}) if isinstance(result, dict) else {}


def _gate_summary(
    gate_payload: dict[str, Any],
    *,
    source: str,
    step_id: str = "",
    agent_id: str = "",
    fallback_index: int | None = None,
) -> dict[str, Any]:
    checks = gate_payload.get("checks", [])
    failed = [
        str(check.get("check_id", "")).strip()
        for check in checks
        if isinstance(check, dict) and not bool(check.get("passed")) and not bool(check.get("warning_only"))
    ]
    return {
        "source": source,
        "step_id": step_id or str(gate_payload.get("step_id", "")).strip(),
        "agent_id": agent_id or str(gate_payload.get("agent_id", "")).strip(),
        "gate_profile": str(gate_payload.get("gate_profile", "") or gate_payload.get("profile", "") or "read_only_agent").strip(),
        "passed": bool(gate_payload.get("passed")) and not bool(gate_payload.get("blocked")),
        "blocked": bool(gate_payload.get("blocked")),
        "blocked_reasons": _list(gate_payload.get("blocked_reasons")),
        "checks_failed": failed,
        "index": fallback_index,
    }


def _normalized_status(*values: str, source: dict[str, Any], artifact_errors: list[str]) -> str:
    if artifact_errors:
        return "invalid"
    text = _first_text(*values).strip().lower().replace("-", "_")
    if bool(source.get("blocked")) or text in _BLOCKED_STATUSES:
        return "blocked"
    if text in _TERMINAL_SUCCESS_STATUSES or bool(source.get("ok")) is True:
        return "completed"
    if text in _FAILED_STATUSES or bool(source.get("ok")) is False:
        return "failed"
    if text in _INTERRUPTED_STATUSES:
        return "interrupted"
    if not text:
        return "unknown"
    return text


def _blocked_reasons(
    *,
    source: dict[str, Any],
    artifact_errors: list[str],
    gate_payload: dict[str, Any],
    source_gates: list[dict[str, Any]],
) -> list[str]:
    reasons: list[str] = []
    reasons.extend(artifact_errors)
    reasons.extend(_list(gate_payload.get("blocked_reasons")))
    reasons.extend(_list(source.get("blocked_reasons")))
    if bool(source.get("blocked")) and not _list(source.get("blocked_reasons")):
        reasons.append("Source step result reports blocked=true.")
    for gate in source_gates:
        if bool(gate.get("blocked")) or not bool(gate.get("passed")):
            profile = str(gate.get("gate_profile", "")).strip() or "unknown"
            reasons.append(f"Source step machine gate did not pass: {profile}.")
            reasons.extend(_list(gate.get("blocked_reasons")))
    return _dedupe(reasons)


def _warnings(
    *,
    source: dict[str, Any],
    artifact_errors: list[str],
    gate_payload: dict[str, Any],
    requested_project_id: str,
    effective_project_id: str,
) -> list[str]:
    warnings = _list(gate_payload.get("warnings"))
    warnings.extend(_list(source.get("warnings")))
    warnings.extend(artifact_errors)
    if requested_project_id != effective_project_id:
        warnings.append("Agent step result project_id overrides the requested project_id.")
    if not _source_local_only(source):
        warnings.append("Source step result does not explicitly report local_only=true.")
    return _dedupe(warnings)


def _source_execution_flags(source: dict[str, Any]) -> dict[str, bool]:
    github = bool(source.get("github_execution_performed") or source.get("github_operation_performed"))
    queue_mutation = bool(source.get("queue_mutation_performed"))
    mutation = bool(source.get("mutation_performed") or queue_mutation)
    return {
        "mutation_performed": mutation,
        "queue_mutation_performed": queue_mutation,
        "external_execution_performed": bool(source.get("external_execution_performed") or github or source.get("codex_execution_performed")),
        "model_execution_performed": bool(source.get("model_execution_performed") or source.get("local_llm_execution_performed")),
        "codex_execution_performed": bool(source.get("codex_execution_performed")),
        "github_execution_performed": github,
        "patch_application_performed": bool(source.get("patch_application_performed")),
        "validation_command_execution_performed": bool(source.get("validation_command_execution_performed")),
    }


def _source_artifacts(source: dict[str, Any]) -> list[str]:
    artifacts = _list(source.get("artifacts_created"))
    for key in ("artifact_path", "result_artifact_path", "response_artifact_path", "summary_artifact_path", "output"):
        value = str(source.get(key, "") or "").strip()
        if value:
            artifacts.append(value)
    return _dedupe(artifacts)


def _source_local_only(source: dict[str, Any]) -> bool:
    if "local_only" in source:
        return bool(source.get("local_only"))
    flags = _source_execution_flags(source)
    return not bool(flags["external_execution_performed"] or flags["github_execution_performed"])


def _result_summary(source: dict[str, Any]) -> str:
    for key in ("result_summary", "response_summary", "summary", "message"):
        text = str(source.get(key, "") or "").strip()
        if text:
            return text[:1000]
    outputs = source.get("outputs")
    if isinstance(outputs, dict):
        text = str(outputs.get("summary", "") or "").strip()
        if text:
            return text[:1000]
    return "No source result summary was provided."


def _agent_summary(config: AppConfig, *, agent_id: str) -> dict[str, Any]:
    target_agent = agent_id or "unknown-agent"
    registry = build_agent_registry(config, agent_id=target_agent if agent_id else None)
    agents = registry.get("agents", []) if isinstance(registry, dict) else []
    agent = agents[0] if agents and isinstance(agents[0], dict) else {}
    return {
        "agent_id": target_agent,
        "agent_found": bool(agent_id and agent),
        "can_run_real": bool(agent.get("can_run_real")),
        "can_run_dry_run": bool(agent.get("can_run_dry_run")),
        "machine_gate_required": bool(agent.get("machine_gate_required", True)),
        "default_execution_mode": str(agent.get("default_execution_mode", "")).strip(),
        "forbidden_capabilities": _list(agent.get("forbidden_capabilities")),
    }


def _llm_decision_summary(config: AppConfig, *, item_id: str, queue_path: str | Path | None) -> dict[str, Any]:
    result = recommend_llm_decision(
        config,
        item_id=item_id,
        queue_path=queue_path,
        output_format="json",
    )
    payload = result.get("payload", {}) if isinstance(result, dict) else {}
    return {
        "recommendation_type": str(payload.get("recommendation_type", "")).strip(),
        "item_found": bool(payload.get("item_found")),
        "recommended_lane": str(payload.get("recommended_lane", "")).strip(),
        "recommended_provider": str(payload.get("recommended_provider", "")).strip(),
        "machine_gate_required": bool(payload.get("machine_gate_required")),
        "execution_performed": bool(payload.get("execution_performed")),
        "next_safe_action": str(payload.get("next_safe_action", "")).strip(),
    }


def _orchestrator_evaluation(
    *,
    status: str,
    blocked: bool,
    machine_gates_passed: bool,
    source_flags: dict[str, bool],
) -> dict[str, Any]:
    recovery_required = blocked or status in {"failed", "interrupted", "invalid", "unknown"} or not machine_gates_passed
    validation_required = bool(
        source_flags["mutation_performed"]
        or source_flags["codex_execution_performed"]
        or source_flags["patch_application_performed"]
        or source_flags["github_execution_performed"]
    )
    return {
        "normalized_status": status,
        "recovery_required": recovery_required,
        "validation_required_before_completion": validation_required,
        "safe_for_automatic_next_step": status == "completed"
        and not blocked
        and machine_gates_passed
        and not validation_required,
        "requires_operator_review": recovery_required or validation_required,
    }


def _next_safe_action(*, blocked: bool, status: str, source_flags: dict[str, bool]) -> str:
    if blocked:
        return "Resolve result-artifact or machine-gate blockers before using this step result for orchestration recovery."
    if status == "failed":
        return "Use failure classification or orchestration run history inspection before any explicit retry."
    if status in {"invalid", "unknown"}:
        return "Capture a valid local agent step result artifact before recovery or completion decisions."
    if status == "interrupted":
        return "Inspect orchestration run history and recover from the last safe checkpoint."
    if source_flags["codex_execution_performed"] or source_flags["mutation_performed"] or source_flags["patch_application_performed"]:
        return "Run explicit local validation and review evidence before queue completion or follow-on execution."
    return "Use this normalized step result for orchestrator evaluation; continue only through the next explicit gated step."


def _queue_item_found(config: AppConfig, *, item_id: str, queue_path: str | Path | None) -> bool:
    path = resolve_project_queue_path(config.repo_root, queue_path)
    if not path.exists():
        return False
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return False
    items = raw.get("work_items", []) if isinstance(raw, dict) else []
    return any(isinstance(item, dict) and str(item.get("item_id", "")).strip() == item_id for item in items)


def _emit_or_write(
    *,
    config: AppConfig,
    payload: dict[str, Any],
    output: str | Path | None,
    force: bool,
) -> dict[str, Any]:
    if output is None:
        return {
            "command": COMMAND_NAME,
            "ok": not bool(payload.get("blocked")),
            "local_only": True,
            "format": "json",
            "wrote_output_file": False,
            "stdout": json.dumps(payload, indent=2),
            "payload": payload,
        }
    output_path = _resolve(config.repo_root, output)
    if output_path.exists() and not force:
        blocked = dict(payload)
        blocked["status"] = "blocked"
        blocked["blocked"] = True
        blocked["blocked_reasons"] = _dedupe(
            [*_list(blocked.get("blocked_reasons")), "Output file already exists. Re-run with --force to overwrite."]
        )
        return {
            "command": COMMAND_NAME,
            "ok": False,
            "local_only": True,
            "format": "json",
            "output": str(output_path),
            "force": force,
            "wrote_output_file": False,
            "stdout": json.dumps(blocked, indent=2),
            "payload": blocked,
        }
    artifact_payload = dict(payload)
    artifact_payload["artifacts_created"] = _dedupe([*_list(payload.get("artifacts_created")), str(output_path)])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact_payload, indent=2) + "\n", encoding="utf-8")
    return {
        "command": COMMAND_NAME,
        "ok": not bool(artifact_payload.get("blocked")),
        "local_only": True,
        "format": "json",
        "output": str(output_path),
        "force": force,
        "wrote_output_file": True,
        "payload": artifact_payload,
    }


def _resolve(repo_root: Path, value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


def _first_text(*values: Any) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""


def _optional_int(*values: Any) -> int | None:
    for value in values:
        if isinstance(value, int) and not isinstance(value, bool):
            return value
        text = str(value or "").strip()
        if text.isdigit():
            return int(text)
    return None


def _list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(entry).strip() for entry in value if str(entry).strip()]
    if isinstance(value, tuple):
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


def _error(error: str, details: dict[str, Any]) -> dict[str, Any]:
    return {
        "command": COMMAND_NAME,
        "ok": False,
        "local_only": True,
        "error": error,
        "details": details,
    }
