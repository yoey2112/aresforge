from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.machine_safety_gate_engine import evaluate_machine_safety_gates
from aresforge.operator.orchestrator_execution_state_machine import DEFAULT_ITEM_ID as STATE_MACHINE_ITEM_ID

COMMAND_NAME = "inspect-orchestration-run-history"
HISTORY_TYPE = "orchestration_run_history_recovery_v1"
HISTORY_SCHEMA_VERSION = "m141.1"
HISTORY_PATH_RELATIVE = Path(".aresforge") / "orchestrator" / "run_history.json"

_RECOVERY_STATUSES = frozenset({"blocked", "failed", "max_steps_reached", "interrupted", "running"})

_BOUNDARY_CONFIRMATIONS = (
    "M141 inspects persisted local orchestration run history and recovery records.",
    "M141 may append local run-history metadata after an explicit orchestration run, but the inspector is read-only.",
    "M141 does not execute agents, Codex, local LLMs, GitHub, validation commands, patches, queue mutation, or follow-on work.",
    "Recovery records are advisory inspection records only; retry and resume remain separate explicit gated commands.",
)


def append_orchestration_run_history(
    config: AppConfig,
    *,
    run_payload: dict[str, Any],
    artifact_path: str | Path | None = None,
    history_path: str | Path | None = None,
) -> dict[str, Any]:
    resolved_history_path = resolve_orchestration_history_path(config.repo_root, history_path)
    try:
        loaded = _load_history_file(resolved_history_path)
        records = loaded["records"]
        record = _record_from_run_payload(run_payload, artifact_path=artifact_path)
        record["history_recorded_at"] = _now_iso()
        records = _replace_record(records, record)
        _write_history_file(resolved_history_path, records, updated_at=_now_iso())
        return {
            "ok": True,
            "history_path": str(resolved_history_path),
            "record": record,
            "warnings": list(loaded["warnings"]),
        }
    except Exception as exc:  # pragma: no cover - history persistence must not break an explicit run.
        return {
            "ok": False,
            "history_path": str(resolved_history_path),
            "record": {},
            "warnings": [f"Orchestration run history append failed: {exc}"],
        }


def inspect_orchestration_run_history(
    config: AppConfig,
    *,
    project_id: str,
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

    normalized_project_id = str(project_id or "").strip()
    if not normalized_project_id:
        return _error("invalid_project_id", {"message": "project_id is required."})
    normalized_item_id = str(item_id or "").strip()
    normalized_run_id = str(run_id or "").strip()
    resolved_history_path = resolve_orchestration_history_path(config.repo_root, history_path)
    resolved_artifacts_root = _resolve_artifacts_root(config, artifacts_root)

    loaded_history = _load_history_file(resolved_history_path)
    artifact_records, artifact_warnings = _discover_artifact_records(resolved_artifacts_root)
    records = _merge_records(
        [*_records_for_project(loaded_history["records"], normalized_project_id), *artifact_records],
        project_id=normalized_project_id,
        item_id=normalized_item_id,
        run_id=normalized_run_id,
    )
    records = sorted(records, key=lambda record: str(record.get("completed_at") or record.get("started_at") or ""), reverse=True)
    latest_record = records[0] if records else {}
    recovery_records = [_recovery_record(record) for record in records if _recovery_required(record)]
    gate_payload = _gate_payload(
        config,
        item_id=normalized_item_id or STATE_MACHINE_ITEM_ID,
        queue_path=queue_path,
    )
    gate_summary = _gate_summary(gate_payload)
    warnings = _dedupe([*loaded_history["warnings"], *artifact_warnings, *_history_warnings(resolved_history_path, records)])
    blocked_reasons = _dedupe(_list(gate_payload.get("blocked_reasons")))
    blocked = bool(blocked_reasons)

    payload: dict[str, Any] = {
        "record_type": HISTORY_TYPE,
        "artifact_type": HISTORY_TYPE,
        "schema_version": HISTORY_SCHEMA_VERSION,
        "generated": True,
        "generated_at": _now_iso(),
        "item_id": normalized_item_id,
        "project_id": normalized_project_id,
        "run_id": normalized_run_id or str(latest_record.get("run_id", "")).strip(),
        "status": _history_status(records=records, recovery_records=recovery_records, blocked=blocked),
        "blocked": blocked,
        "blocked_reasons": blocked_reasons,
        "warnings": warnings,
        "machine_gates_checked": [gate_summary],
        "machine_gates_passed": bool(gate_summary.get("passed")),
        "artifacts_created": [],
        "mutation_performed": False,
        "external_execution_performed": False,
        "model_execution_performed": False,
        "codex_execution_performed": False,
        "github_execution_performed": False,
        "patch_application_performed": False,
        "local_only": True,
        "next_safe_action": _next_safe_action(blocked=blocked, recovery_records=recovery_records, records=records),
        "history_path": str(resolved_history_path),
        "history_record_count": len(records),
        "recovery_record_count": len(recovery_records),
        "records": records,
        "recovery_records": recovery_records,
        "latest_record": latest_record,
        "filters": {
            "project_id": normalized_project_id,
            "item_id": normalized_item_id,
            "run_id": normalized_run_id,
        },
        "artifact_discovery_root": str(resolved_artifacts_root),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }
    return _emit_or_write(config=config, payload=payload, output=output, force=force)


def resolve_orchestration_history_path(repo_root: Path, path: str | Path | None = None) -> Path:
    if path is None:
        return (repo_root / HISTORY_PATH_RELATIVE).resolve()
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = repo_root / candidate
    return candidate.resolve()


def _record_from_run_payload(run_payload: dict[str, Any], *, artifact_path: str | Path | None) -> dict[str, Any]:
    item_id = str(run_payload.get("item_id", "")).strip()
    project_id = str(run_payload.get("project_id", "") or "aresforge").strip()
    run_id = str(run_payload.get("run_id", "")).strip() or _derived_run_id(run_payload, artifact_path=artifact_path)
    status = str(run_payload.get("status", "")).strip() or "unknown"
    blocked_reasons = _list(run_payload.get("blocked_reasons"))
    return {
        "record_type": "orchestration_run_history_record",
        "run_id": run_id,
        "item_id": item_id,
        "project_id": project_id,
        "status": status,
        "blocked": bool(run_payload.get("blocked")),
        "blocked_reasons": blocked_reasons,
        "warnings": _list(run_payload.get("warnings")),
        "started_at": str(run_payload.get("started_at", "")).strip(),
        "completed_at": str(run_payload.get("completed_at", "")).strip(),
        "steps_total": _int(run_payload.get("steps_total")),
        "steps_attempted": _int(run_payload.get("steps_attempted")),
        "steps_completed": _int(run_payload.get("steps_completed")),
        "steps_blocked": _int(run_payload.get("steps_blocked")),
        "machine_gates_checked": _list_or_dicts(run_payload.get("machine_gates_checked")),
        "machine_gates_passed": _machine_gates_passed(run_payload),
        "artifacts_created": _list(run_payload.get("artifacts_created")),
        "artifact_path": str(artifact_path or "").strip(),
        "mutation_performed": bool(run_payload.get("queue_mutation_performed")),
        "external_execution_performed": bool(run_payload.get("external_execution_performed")),
        "model_execution_performed": bool(run_payload.get("model_execution_performed")),
        "codex_execution_performed": bool(run_payload.get("codex_execution_performed")),
        "github_execution_performed": bool(run_payload.get("github_execution_performed")),
        "patch_application_performed": bool(run_payload.get("patch_application_performed")),
        "local_only": bool(run_payload.get("local_only", True)),
        "next_safe_action": str(run_payload.get("next_safe_action", "")).strip() or _record_next_safe_action(status),
    }


def _recovery_record(record: dict[str, Any]) -> dict[str, Any]:
    status = str(record.get("status", "")).strip()
    reasons = _list(record.get("blocked_reasons"))
    if not reasons and status in {"failed", "interrupted", "running"}:
        reasons.append(f"Run status is {status}.")
    if status == "max_steps_reached":
        reasons.append("Run stopped after the configured max step limit before completing all steps.")
    return {
        "record_type": "orchestration_recovery_record",
        "run_id": str(record.get("run_id", "")).strip(),
        "item_id": str(record.get("item_id", "")).strip(),
        "project_id": str(record.get("project_id", "")).strip(),
        "status": status,
        "recovery_required": True,
        "recovery_status": "resume_available" if status == "max_steps_reached" else "operator_review_required",
        "blocked": bool(record.get("blocked")) or status in {"blocked", "failed", "interrupted", "running"},
        "blocked_reasons": _dedupe(reasons),
        "last_completed_step_count": _int(record.get("steps_completed")),
        "steps_attempted": _int(record.get("steps_attempted")),
        "steps_total": _int(record.get("steps_total")),
        "last_checkpoint": _last_checkpoint(record),
        "resume_from_state": "planning" if status == "max_steps_reached" else "recovery",
        "artifact_path": str(record.get("artifact_path", "")).strip(),
        "next_safe_action": _recovery_next_safe_action(status),
        "local_only": True,
        "mutation_performed": False,
        "external_execution_performed": False,
        "model_execution_performed": False,
        "codex_execution_performed": False,
        "github_execution_performed": False,
        "patch_application_performed": False,
    }


def _load_history_file(path: Path) -> dict[str, Any]:
    warnings: list[str] = []
    if not path.exists():
        return {"records": [], "warnings": ["Orchestration run history file does not exist yet."]}
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"records": [], "warnings": [f"Orchestration run history could not be read: {exc}"]}
    if not isinstance(raw, dict):
        return {"records": [], "warnings": ["Orchestration run history JSON root must be an object."]}
    records = raw.get("records", [])
    if not isinstance(records, list):
        warnings.append("Orchestration run history records field is not a list.")
        records = []
    return {"records": [record for record in records if isinstance(record, dict)], "warnings": warnings}


def _write_history_file(path: Path, records: list[dict[str, Any]], *, updated_at: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": HISTORY_SCHEMA_VERSION,
        "artifact_type": HISTORY_TYPE,
        "updated_at": updated_at,
        "records": records,
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _discover_artifact_records(root: Path) -> tuple[list[dict[str, Any]], list[str]]:
    if not root.exists():
        return [], [f"Orchestration artifact root does not exist: {root}"]
    records: list[dict[str, Any]] = []
    warnings: list[str] = []
    for path in sorted(root.glob("*/*.json")):
        try:
            raw = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError) as exc:
            warnings.append(f"Orchestration artifact could not be read: {path}: {exc}")
            continue
        if isinstance(raw, dict) and raw.get("execution_record_type") == "multi_agent_orchestration_v1":
            records.append(_record_from_run_payload(raw, artifact_path=path))
    return records, warnings


def _merge_records(
    records: list[dict[str, Any]],
    *,
    project_id: str,
    item_id: str,
    run_id: str,
) -> list[dict[str, Any]]:
    by_run_id: dict[str, dict[str, Any]] = {}
    for record in records:
        if str(record.get("project_id", "")).strip() != project_id:
            continue
        if item_id and str(record.get("item_id", "")).strip() != item_id:
            continue
        if run_id and str(record.get("run_id", "")).strip() != run_id:
            continue
        key = str(record.get("run_id", "")).strip() or _derived_run_id(record, artifact_path=record.get("artifact_path"))
        existing = by_run_id.get(key, {})
        merged = {**record, **{k: v for k, v in existing.items() if k == "history_recorded_at"}}
        by_run_id[key] = merged
    return list(by_run_id.values())


def _records_for_project(records: list[dict[str, Any]], project_id: str) -> list[dict[str, Any]]:
    return [record for record in records if str(record.get("project_id", "")).strip() == project_id]


def _replace_record(records: list[dict[str, Any]], record: dict[str, Any]) -> list[dict[str, Any]]:
    run_id = str(record.get("run_id", "")).strip()
    kept = [existing for existing in records if str(existing.get("run_id", "")).strip() != run_id]
    kept.append(record)
    return sorted(kept, key=lambda entry: str(entry.get("completed_at") or entry.get("started_at") or ""))


def _gate_payload(config: AppConfig, *, item_id: str, queue_path: str | Path | None) -> dict[str, Any]:
    result = evaluate_machine_safety_gates(
        config,
        item_id=item_id,
        gate_profile="read_only_agent",
        queue_path=queue_path,
        output_format="json",
    )
    return result.get("payload", {}) if isinstance(result, dict) else {}


def _gate_summary(gate_payload: dict[str, Any]) -> dict[str, Any]:
    checks = gate_payload.get("checks", [])
    failed = [
        str(check.get("check_id", "")).strip()
        for check in checks
        if isinstance(check, dict) and not bool(check.get("passed")) and not bool(check.get("warning_only"))
    ]
    return {
        "gate_profile": str(gate_payload.get("gate_profile", "read_only_agent")).strip() or "read_only_agent",
        "passed": bool(gate_payload.get("passed")) and not bool(gate_payload.get("blocked")),
        "blocked": bool(gate_payload.get("blocked")),
        "blocked_reasons": _list(gate_payload.get("blocked_reasons")),
        "checks_failed": failed,
    }


def _emit_or_write(
    *,
    config: AppConfig,
    payload: dict[str, Any],
    output: str | Path | None,
    force: bool,
) -> dict[str, Any]:
    if output is None:
        rendered = json.dumps(payload, indent=2)
        return {
            "command": COMMAND_NAME,
            "ok": not bool(payload.get("blocked")),
            "local_only": True,
            "format": "json",
            "wrote_output_file": False,
            "stdout": rendered,
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
    artifact_payload["artifacts_created"] = [str(output_path)]
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


def _resolve_artifacts_root(config: AppConfig, artifacts_root: str | Path | None) -> Path:
    if artifacts_root is None:
        return (config.artifact_root / "multi-agent-orchestration").resolve()
    return _resolve(config.repo_root, artifacts_root)


def _resolve(repo_root: Path, value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


def _history_status(*, records: list[dict[str, Any]], recovery_records: list[dict[str, Any]], blocked: bool) -> str:
    if blocked:
        return "blocked"
    if recovery_records:
        return "recovery_required"
    if records:
        return "ready"
    return "empty"


def _history_warnings(path: Path, records: list[dict[str, Any]]) -> list[str]:
    warnings: list[str] = []
    if not path.exists() and not records:
        warnings.append("No persisted history records or orchestration artifacts were found.")
    return warnings


def _next_safe_action(*, blocked: bool, recovery_records: list[dict[str, Any]], records: list[dict[str, Any]]) -> str:
    if blocked:
        return "Resolve read-only machine gate blockers before relying on orchestration history."
    if recovery_records:
        return "Review recovery records and resume only through a future explicit gated orchestration recovery command."
    if not records:
        return "Run an explicit gated orchestration command to create history, or inspect the M140 state machine contract."
    return "Review orchestration history as local evidence; execute follow-on work only through explicit gated commands."


def _recovery_required(record: dict[str, Any]) -> bool:
    status = str(record.get("status", "")).strip()
    return bool(record.get("blocked")) or status in _RECOVERY_STATUSES


def _last_checkpoint(record: dict[str, Any]) -> str:
    status = str(record.get("status", "")).strip()
    if status == "max_steps_reached":
        return "post_step_checkpoint"
    if status in {"blocked", "failed"}:
        return "terminal_checkpoint"
    return "recovery_snapshot"


def _recovery_next_safe_action(status: str) -> str:
    if status == "max_steps_reached":
        return "Review the partial timeline and resume from the next unattempted step only through explicit gated orchestration recovery."
    return "Inspect the failed or blocked step, preserve artifacts, and rerun only after the blocking reason is resolved."


def _record_next_safe_action(status: str) -> str:
    if status in _RECOVERY_STATUSES:
        return _recovery_next_safe_action(status)
    return "Review the run artifact before any explicit follow-on command."


def _derived_run_id(run_payload: dict[str, Any], *, artifact_path: str | Path | None) -> str:
    seed = "|".join(
        [
            str(run_payload.get("item_id", "")).strip(),
            str(run_payload.get("started_at", "")).strip(),
            str(run_payload.get("completed_at", "")).strip(),
            str(artifact_path or "").strip(),
        ]
    )
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12]
    item = _safe_id(str(run_payload.get("item_id", "")).strip() or "unknown-item")
    return f"{item}-{digest}"


def _machine_gates_passed(run_payload: dict[str, Any]) -> bool:
    gates = run_payload.get("machine_gates_checked", [])
    if isinstance(gates, list) and gates:
        return all(bool(gate.get("passed")) for gate in gates if isinstance(gate, dict))
    return not bool(run_payload.get("blocked"))


def _list_or_dicts(value: Any) -> list[Any]:
    if isinstance(value, list):
        return [entry for entry in value if isinstance(entry, (dict, str))]
    return []


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


def _int(value: Any) -> int:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    text = str(value or "").strip()
    return int(text) if text.isdigit() else 0


def _safe_id(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in str(value or "").strip().lower())
    return cleaned.strip("-") or "orchestration-run"


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
