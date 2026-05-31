from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.orchestration_run_history import inspect_orchestration_run_history
from aresforge.operator.orchestrator_resume_from_failure import inspect_orchestration_resume_plan

COMMAND_NAME = "inspect-orchestration-run-monitor"
RECORD_TYPE = "hub_orchestration_run_monitor_v1"
MONITOR_VERSION = "m153.1"
DEFAULT_ITEM_ID = "m153-hub-orchestration-run-monitor"
DEFAULT_PROJECT_ID = "aresforge"

_RECOVERY_STATUSES = frozenset({"blocked", "failed", "max_steps_reached", "interrupted", "running"})

_BOUNDARY_CONFIRMATIONS: tuple[str, ...] = (
    "M153 builds a Hub-visible orchestration run monitor from local run history, recovery, gate, and artifact evidence.",
    "M153 is inspection-only unless an explicit local output artifact path is supplied.",
    "M153 performs no agent, Codex, local LLM/model, GitHub, validation command, patch, queue, retry, resume, or next-item execution.",
    "Recovery and next actions are advisory; future execution remains separate, explicit, and machine-gated.",
)


def inspect_orchestration_run_monitor(
    config: AppConfig,
    *,
    project_id: str = DEFAULT_PROJECT_ID,
    item_id: str | None = None,
    run_id: str | None = None,
    queue_path: str | Path | None = None,
    history_path: str | Path | None = None,
    artifacts_root: str | Path | None = None,
    output: str | Path | None = None,
    force: bool = False,
    output_format: str = "json",
) -> dict[str, Any]:
    fmt = str(output_format or "json").strip().lower()
    if fmt != "json":
        return _error("invalid_format", {"format": output_format, "supported_formats": ["json"]})

    normalized_project_id = str(project_id or DEFAULT_PROJECT_ID).strip() or DEFAULT_PROJECT_ID
    normalized_item_id = str(item_id or "").strip()
    normalized_run_id = str(run_id or "").strip()

    history_result = inspect_orchestration_run_history(
        config,
        project_id=normalized_project_id,
        item_id=normalized_item_id or None,
        run_id=normalized_run_id or None,
        queue_path=queue_path,
        history_path=history_path,
        artifacts_root=artifacts_root,
        output=None,
        force=False,
        output_format="json",
    )
    history_payload = _payload(history_result)
    latest_record = _latest_record(history_payload)
    effective_run_id = normalized_run_id or _text(latest_record.get("run_id"))
    effective_item_id = normalized_item_id or _text(latest_record.get("item_id")) or DEFAULT_ITEM_ID
    source_run = _load_source_run(latest_record)
    step_results = _step_results(source_run)
    recovery_records = _dicts(history_payload.get("recovery_records"))
    matching_recovery = _matching_recovery(recovery_records, effective_run_id)
    resume_payload = _resume_payload(
        config,
        run_id=effective_run_id,
        item_id=effective_item_id,
        project_id=normalized_project_id,
        queue_path=queue_path,
        history_path=history_path,
        artifacts_root=artifacts_root,
    )
    warnings = _dedupe(
        [
            *_list(history_payload.get("warnings")),
            *_list(resume_payload.get("warnings")),
            *_monitor_warnings(history_payload, latest_record, source_run, effective_run_id),
        ]
    )
    blocked_reasons = _dedupe([*_list(history_payload.get("blocked_reasons")), *_list(resume_payload.get("blocked_reasons"))])
    monitor_blocked = bool(blocked_reasons)
    gates_checked = _gate_summaries(history_payload, latest_record, source_run, resume_payload)
    status = _monitor_status(
        blocked=monitor_blocked,
        latest_record=latest_record,
        recovery_record=matching_recovery,
        history_payload=history_payload,
    )

    payload: dict[str, Any] = {
        "record_type": RECORD_TYPE,
        "artifact_type": RECORD_TYPE,
        "monitor_version": MONITOR_VERSION,
        "generated": True,
        "generated_at": _now_iso(),
        "item_id": effective_item_id,
        "project_id": normalized_project_id,
        "run_id": effective_run_id,
        "status": status,
        "blocked": monitor_blocked,
        "blocked_reasons": blocked_reasons,
        "warnings": warnings,
        "machine_gates_checked": gates_checked,
        "machine_gates_passed": bool(gates_checked) and all(bool(gate.get("passed")) for gate in gates_checked),
        "artifacts_created": [],
        "mutation_performed": False,
        "external_execution_performed": False,
        "model_execution_performed": False,
        "codex_execution_performed": False,
        "github_execution_performed": False,
        "patch_application_performed": False,
        "local_only": True,
        "next_safe_action": _next_safe_action(
            blocked=monitor_blocked,
            status=status,
            latest_record=latest_record,
            recovery_record=matching_recovery,
            resume_payload=resume_payload,
        ),
        "history_summary": _history_summary(history_payload),
        "latest_run": _latest_run_summary(latest_record, source_run),
        "step_results": step_results,
        "step_result_summary": _step_result_summary(step_results, latest_record),
        "recovery_summary": _recovery_summary(recovery_records, matching_recovery, resume_payload),
        "resume_plan_summary": _resume_plan_summary(resume_payload),
        "gate_summary": _gate_summary(gates_checked),
        "artifact_references": _artifact_references(history_payload, latest_record, source_run),
        "filters": {
            "project_id": normalized_project_id,
            "item_id": normalized_item_id,
            "run_id": normalized_run_id,
        },
        "history_path": _text(history_payload.get("history_path")),
        "artifact_discovery_root": _text(history_payload.get("artifact_discovery_root")),
        "hub_visibility": {
            "api_endpoint": "/api/orchestration/run-monitor",
            "operator_cli": "python -m aresforge inspect-orchestration-run-monitor --project-id "
            + normalized_project_id
            + " --format json",
            "local_only": True,
        },
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }
    return _emit_or_write(config=config, payload=payload, output=output, force=force)


def _payload(result: dict[str, Any]) -> dict[str, Any]:
    payload = result.get("payload", {}) if isinstance(result, dict) else {}
    return payload if isinstance(payload, dict) else {}


def _resume_payload(
    config: AppConfig,
    *,
    run_id: str,
    item_id: str,
    project_id: str,
    queue_path: str | Path | None,
    history_path: str | Path | None,
    artifacts_root: str | Path | None,
) -> dict[str, Any]:
    if not run_id:
        return {}
    result = inspect_orchestration_resume_plan(
        config,
        run_id=run_id,
        item_id=item_id,
        project_id=project_id,
        queue_path=queue_path,
        history_path=history_path,
        artifacts_root=artifacts_root,
        output=None,
        force=False,
        output_format="json",
    )
    return _payload(result)


def _latest_record(history_payload: dict[str, Any]) -> dict[str, Any]:
    latest = history_payload.get("latest_record")
    if isinstance(latest, dict) and latest:
        return latest
    records = _dicts(history_payload.get("records"))
    return records[0] if records else {}


def _load_source_run(record: dict[str, Any]) -> dict[str, Any]:
    artifact_path = _text(record.get("artifact_path"))
    if not artifact_path:
        return {}
    path = Path(artifact_path)
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    return raw if isinstance(raw, dict) else {}


def _step_results(source_run: dict[str, Any]) -> list[dict[str, Any]]:
    steps = source_run.get("step_results", [])
    if not isinstance(steps, list):
        return []
    return [_step_summary(step) for step in steps if isinstance(step, dict)]


def _step_summary(step: dict[str, Any]) -> dict[str, Any]:
    return {
        "step_id": _text(step.get("step_id")),
        "sequence": _int(step.get("sequence") or step.get("step_index")),
        "agent_id": _text(step.get("agent_id")),
        "status": _text(step.get("status")),
        "blocked": bool(step.get("blocked")),
        "blocked_reasons": _list(step.get("blocked_reasons")),
        "warnings": _list(step.get("warnings")),
        "machine_gates_checked": _dicts(step.get("machine_gates_checked")),
        "artifacts_created": _list(step.get("artifacts_created")),
        "mutation_performed": bool(step.get("mutation_performed") or step.get("queue_mutation_performed")),
        "external_execution_performed": bool(step.get("external_execution_performed")),
        "model_execution_performed": bool(step.get("model_execution_performed") or step.get("local_llm_execution_performed")),
        "codex_execution_performed": bool(step.get("codex_execution_performed")),
        "github_execution_performed": bool(step.get("github_execution_performed")),
        "patch_application_performed": bool(step.get("patch_application_performed")),
        "next_safe_action": _text(step.get("next_safe_action")),
    }


def _matching_recovery(records: list[dict[str, Any]], run_id: str) -> dict[str, Any]:
    if not run_id:
        return records[0] if records else {}
    for record in records:
        if _text(record.get("run_id")) == run_id:
            return record
    return {}


def _gate_summaries(
    history_payload: dict[str, Any],
    latest_record: dict[str, Any],
    source_run: dict[str, Any],
    resume_payload: dict[str, Any],
) -> list[dict[str, Any]]:
    gates: list[dict[str, Any]] = []
    for source, value in (
        ("monitor_history_inspection", history_payload.get("machine_gates_checked")),
        ("latest_run_history_record", latest_record.get("machine_gates_checked")),
        ("latest_source_run", source_run.get("machine_gates_checked")),
        ("resume_plan_inspection", resume_payload.get("machine_gates_checked")),
    ):
        for gate in _dicts(value):
            gates.append(_normalize_gate(gate, source=source))
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str]] = set()
    for gate in gates:
        key = (
            _text(gate.get("source")),
            _text(gate.get("gate_profile")),
            _text(gate.get("step_id")),
            _text(gate.get("agent_id")),
        )
        if key not in seen:
            seen.add(key)
            deduped.append(gate)
    return deduped


def _normalize_gate(gate: dict[str, Any], *, source: str) -> dict[str, Any]:
    return {
        "source": _text(gate.get("source")) or source,
        "step_id": _text(gate.get("step_id")),
        "agent_id": _text(gate.get("agent_id")),
        "gate_profile": _text(gate.get("gate_profile") or gate.get("profile")) or "read_only_agent",
        "passed": bool(gate.get("passed")) and not bool(gate.get("blocked")),
        "blocked": bool(gate.get("blocked")),
        "blocked_reasons": _list(gate.get("blocked_reasons")),
        "checks_failed": _list(gate.get("checks_failed")),
    }


def _monitor_status(
    *,
    blocked: bool,
    latest_record: dict[str, Any],
    recovery_record: dict[str, Any],
    history_payload: dict[str, Any],
) -> str:
    if blocked:
        return "blocked"
    if not latest_record:
        return "no_runs"
    run_status = _text(latest_record.get("status"))
    if recovery_record or run_status in _RECOVERY_STATUSES:
        return "recovery_required"
    if run_status == "completed":
        return "completed"
    if _int(history_payload.get("history_record_count")) > 0:
        return "monitor_ready"
    return "no_runs"


def _history_summary(history_payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": _text(history_payload.get("status")),
        "history_record_count": _int(history_payload.get("history_record_count")),
        "recovery_record_count": _int(history_payload.get("recovery_record_count")),
        "latest_run_id": _text(history_payload.get("run_id")),
        "history_path": _text(history_payload.get("history_path")),
    }


def _latest_run_summary(record: dict[str, Any], source_run: dict[str, Any]) -> dict[str, Any]:
    return {
        "run_id": _first_text(record.get("run_id"), source_run.get("run_id")),
        "item_id": _first_text(record.get("item_id"), source_run.get("item_id")),
        "project_id": _first_text(record.get("project_id"), source_run.get("project_id")),
        "status": _first_text(record.get("status"), source_run.get("status")),
        "blocked": bool(record.get("blocked") or source_run.get("blocked")),
        "blocked_reasons": _dedupe([*_list(record.get("blocked_reasons")), *_list(source_run.get("blocked_reasons"))]),
        "warnings": _dedupe([*_list(record.get("warnings")), *_list(source_run.get("warnings"))]),
        "started_at": _first_text(record.get("started_at"), source_run.get("started_at")),
        "completed_at": _first_text(record.get("completed_at"), source_run.get("completed_at")),
        "steps_total": _int(record.get("steps_total") or source_run.get("steps_total")),
        "steps_attempted": _int(record.get("steps_attempted") or source_run.get("steps_attempted")),
        "steps_completed": _int(record.get("steps_completed") or source_run.get("steps_completed")),
        "steps_blocked": _int(record.get("steps_blocked") or source_run.get("steps_blocked")),
        "artifact_path": _first_text(record.get("artifact_path")),
        "next_safe_action": _first_text(record.get("next_safe_action"), source_run.get("next_safe_action")),
    }


def _step_result_summary(step_results: list[dict[str, Any]], latest_record: dict[str, Any]) -> dict[str, Any]:
    blocked_steps = [step for step in step_results if bool(step.get("blocked"))]
    failed_steps = [step for step in step_results if _text(step.get("status")) == "failed"]
    return {
        "step_result_count": len(step_results),
        "steps_total": _int(latest_record.get("steps_total")),
        "steps_attempted": _int(latest_record.get("steps_attempted")) or len(step_results),
        "steps_completed": _int(latest_record.get("steps_completed")),
        "steps_blocked": _int(latest_record.get("steps_blocked")) or len(blocked_steps),
        "blocked_step_ids": [_text(step.get("step_id")) for step in blocked_steps if _text(step.get("step_id"))],
        "failed_step_ids": [_text(step.get("step_id")) for step in failed_steps if _text(step.get("step_id"))],
    }


def _recovery_summary(
    recovery_records: list[dict[str, Any]],
    matching_recovery: dict[str, Any],
    resume_payload: dict[str, Any],
) -> dict[str, Any]:
    return {
        "recovery_record_count": len(recovery_records),
        "recovery_required": bool(matching_recovery) or bool(resume_payload.get("resume_requires_operator_review")),
        "recovery_status": _text(matching_recovery.get("recovery_status")) or _text(resume_payload.get("status")),
        "resume_available": bool(resume_payload.get("resume_eligible"))
        or _text(matching_recovery.get("recovery_status")) == "resume_available",
        "resume_requires_operator_review": bool(resume_payload.get("resume_requires_operator_review")),
        "resume_requires_validation": bool(resume_payload.get("resume_requires_validation")),
        "blocked_reasons": _dedupe([*_list(matching_recovery.get("blocked_reasons")), *_list(resume_payload.get("blocked_reasons"))]),
        "next_safe_action": _first_text(matching_recovery.get("next_safe_action"), resume_payload.get("next_safe_action")),
    }


def _resume_plan_summary(resume_payload: dict[str, Any]) -> dict[str, Any]:
    if not resume_payload:
        return {
            "resume_plan_available": False,
            "resume_eligible": False,
            "automatic_resume_performed": False,
            "next_safe_action": "No run record is available for resume planning.",
        }
    command_plan = resume_payload.get("resume_command_plan", {})
    command_plan = command_plan if isinstance(command_plan, dict) else {}
    return {
        "resume_plan_available": True,
        "status": _text(resume_payload.get("status")),
        "resume_eligible": bool(resume_payload.get("resume_eligible")),
        "resume_requires_operator_review": bool(resume_payload.get("resume_requires_operator_review")),
        "resume_requires_validation": bool(resume_payload.get("resume_requires_validation")),
        "automatic_resume_performed": bool(command_plan.get("automatic_resume_performed")),
        "recommended_operator_command": _text(command_plan.get("recommended_operator_command")),
        "resume_target": resume_payload.get("resume_target", {}) if isinstance(resume_payload.get("resume_target"), dict) else {},
        "next_safe_action": _text(resume_payload.get("next_safe_action")),
    }


def _gate_summary(gates: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [gate for gate in gates if not bool(gate.get("passed"))]
    return {
        "gate_count": len(gates),
        "gates_passed": len(gates) - len(failed),
        "gates_failed": len(failed),
        "failed_gate_profiles": _dedupe([_text(gate.get("gate_profile")) for gate in failed]),
        "blocked_reasons": _dedupe(reason for gate in gates for reason in _list(gate.get("blocked_reasons"))),
    }


def _artifact_references(history_payload: dict[str, Any], latest_record: dict[str, Any], source_run: dict[str, Any]) -> dict[str, Any]:
    return {
        "latest_run_artifact_path": _text(latest_record.get("artifact_path")),
        "latest_run_artifacts_created": _dedupe(
            [*_list(latest_record.get("artifacts_created")), *_list(source_run.get("artifacts_created"))]
        ),
        "history_path": _text(history_payload.get("history_path")),
        "artifact_discovery_root": _text(history_payload.get("artifact_discovery_root")),
    }


def _monitor_warnings(
    history_payload: dict[str, Any],
    latest_record: dict[str, Any],
    source_run: dict[str, Any],
    run_id: str,
) -> list[str]:
    warnings: list[str] = []
    if not latest_record:
        warnings.append("No orchestration run record is available for monitor display.")
    if latest_record and not source_run and _text(latest_record.get("artifact_path")):
        warnings.append("Latest orchestration source artifact could not be loaded; step result details may be reduced.")
    if run_id and _text(history_payload.get("run_id")) and _text(history_payload.get("run_id")) != run_id:
        warnings.append("Requested run_id differs from the latest history payload run_id.")
    return warnings


def _next_safe_action(
    *,
    blocked: bool,
    status: str,
    latest_record: dict[str, Any],
    recovery_record: dict[str, Any],
    resume_payload: dict[str, Any],
) -> str:
    if blocked:
        return "Resolve read-only monitor gate blockers before relying on orchestration run state."
    if not latest_record:
        return "Run an explicit gated orchestration command to create local run evidence, or inspect the M140 state machine."
    if recovery_record:
        return "Review recovery details and use only explicit machine-gated recovery or resume commands; no automatic retry was performed."
    if resume_payload.get("resume_eligible") is True:
        return "Resume is available only through an explicit future machine-gated orchestration command; no execution was performed."
    if status == "completed":
        return "Review completed run artifacts before any separate gated queue completion or follow-on work."
    return _text(resume_payload.get("next_safe_action")) or _text(latest_record.get("next_safe_action")) or "Review local run evidence before any explicit gated follow-on command."


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
        text = _text(value)
        if text:
            return text
    return ""


def _text(value: Any) -> str:
    return str(value or "").strip()


def _dicts(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [entry for entry in value if isinstance(entry, dict)]
    return []


def _list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [_text(entry) for entry in value if _text(entry)]
    if isinstance(value, tuple):
        return [_text(entry) for entry in value if _text(entry)]
    if value in (None, ""):
        return []
    return [_text(value)]


def _dedupe(values: Any) -> list[str]:
    deduped: list[str] = []
    for value in values:
        text = _text(value)
        if text and text not in deduped:
            deduped.append(text)
    return deduped


def _int(value: Any) -> int:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    text = _text(value)
    return int(text) if text.isdigit() else 0


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
