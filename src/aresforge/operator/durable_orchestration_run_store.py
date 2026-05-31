from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.machine_safety_gate_engine import evaluate_machine_safety_gates

COMMAND_NAME = "inspect-orchestration-run-store"
RUN_STORE_TYPE = "durable_orchestration_run_store_v1"
RUN_STORE_SCHEMA_VERSION = "m155.1"
RUN_STORE_PATH_RELATIVE = Path(".aresforge") / "orchestrator" / "run_history.json"
RUN_RECORD_TYPE = "orchestration_run_history_record"
DEFAULT_ITEM_ID = "m155-durable-orchestration-run-store"
DEFAULT_PROJECT_ID = "aresforge"

_REQUIRED_RECORD_FIELDS: tuple[str, ...] = (
    "record_type",
    "run_id",
    "project_id",
    "status",
    "blocked",
    "blocked_reasons",
    "warnings",
    "machine_gates_checked",
    "machine_gates_passed",
    "artifacts_created",
    "mutation_performed",
    "queue_mutation_performed",
    "external_execution_performed",
    "codex_execution_performed",
    "model_execution_performed",
    "github_execution_performed",
    "patch_application_performed",
    "local_only",
    "next_safe_action",
)

_BOUNDARY_CONFIRMATIONS: tuple[str, ...] = (
    "M155 provides a durable local store for orchestration run metadata.",
    "M155 store inspection may bootstrap the missing local store file, but it never executes agents, Codex, models, GitHub, validation commands, patches, queue progression, or follow-on work.",
    "Append and update operations are local file persistence only and preserve deterministic run_id ordering.",
    "Corrupt store files fail closed with structured errors instead of falling back to unsafe execution.",
)


def resolve_orchestration_run_store_path(repo_root: Path, path: str | Path | None = None) -> Path:
    if path is None:
        return (repo_root / RUN_STORE_PATH_RELATIVE).resolve()
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = repo_root / candidate
    return candidate.resolve()


def bootstrap_orchestration_run_store(
    config: AppConfig,
    *,
    store_path: str | Path | None = None,
    project_id: str = DEFAULT_PROJECT_ID,
) -> dict[str, Any]:
    path = resolve_orchestration_run_store_path(config.repo_root, store_path)
    if path.exists():
        read_result = read_orchestration_run_store(config, store_path=path, bootstrap_missing=False)
        return {
            "ok": bool(read_result.get("ok")),
            "store_path": str(path),
            "bootstrap_performed": False,
            "store": read_result.get("store", {}),
            "warnings": _list(read_result.get("warnings")),
            "errors": _list(read_result.get("errors")),
        }
    payload = _empty_store_payload(project_id=project_id, created_at=_now_iso(), updated_at=_now_iso())
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return {
        "ok": True,
        "store_path": str(path),
        "bootstrap_performed": True,
        "store": payload,
        "warnings": [],
        "errors": [],
    }


def read_orchestration_run_store(
    config: AppConfig,
    *,
    store_path: str | Path | None = None,
    bootstrap_missing: bool = False,
    project_id: str = DEFAULT_PROJECT_ID,
) -> dict[str, Any]:
    path = resolve_orchestration_run_store_path(config.repo_root, store_path)
    if not path.exists():
        if bootstrap_missing:
            bootstrapped = bootstrap_orchestration_run_store(config, store_path=path, project_id=project_id)
            return {
                "ok": bool(bootstrapped.get("ok")),
                "store_path": str(path),
                "store": bootstrapped.get("store", {}),
                "records": _dicts((bootstrapped.get("store") or {}).get("records")),
                "schema_valid": bool(bootstrapped.get("ok")),
                "bootstrap_performed": bool(bootstrapped.get("bootstrap_performed")),
                "warnings": _list(bootstrapped.get("warnings")),
                "errors": _list(bootstrapped.get("errors")),
            }
        return {
            "ok": True,
            "store_path": str(path),
            "store": _empty_store_payload(project_id=project_id, created_at="", updated_at=""),
            "records": [],
            "schema_valid": True,
            "bootstrap_performed": False,
            "warnings": [],
            "errors": [],
        }
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        return _read_error(path, f"Orchestration run store could not be read as valid JSON: {exc}")
    if not isinstance(raw, dict):
        return _read_error(path, "Orchestration run store JSON root must be an object.")
    validation = validate_run_store_payload(raw)
    if not validation["schema_valid"]:
        return {
            "ok": False,
            "store_path": str(path),
            "store": raw,
            "records": [],
            "schema_valid": False,
            "bootstrap_performed": False,
            "warnings": _list(validation.get("warnings")),
            "errors": _list(validation.get("errors")),
        }
    records = [_normalize_record(record) for record in _dicts(raw.get("records"))]
    store = dict(raw)
    store["records"] = _sort_records(records)
    return {
        "ok": True,
        "store_path": str(path),
        "store": store,
        "records": store["records"],
        "schema_valid": True,
        "bootstrap_performed": False,
        "warnings": _list(validation.get("warnings")),
        "errors": [],
    }


def append_orchestration_run_record(
    config: AppConfig,
    *,
    record: dict[str, Any],
    store_path: str | Path | None = None,
) -> dict[str, Any]:
    normalized = _normalize_record(record)
    validation = validate_run_record(normalized)
    if not validation["schema_valid"]:
        return {
            "ok": False,
            "store_path": str(resolve_orchestration_run_store_path(config.repo_root, store_path)),
            "record": normalized,
            "warnings": _list(validation.get("warnings")),
            "errors": _list(validation.get("errors")),
        }
    loaded = read_orchestration_run_store(
        config,
        store_path=store_path,
        bootstrap_missing=True,
        project_id=str(normalized.get("project_id") or DEFAULT_PROJECT_ID),
    )
    if not loaded["ok"]:
        return {
            "ok": False,
            "store_path": loaded["store_path"],
            "record": normalized,
            "warnings": _list(loaded.get("warnings")),
            "errors": _list(loaded.get("errors")),
        }
    records = [entry for entry in _dicts(loaded.get("records")) if _text(entry.get("run_id")) != _text(normalized.get("run_id"))]
    records.append(normalized)
    write_result = _write_store(config, store_path=loaded["store_path"], records=records, project_id=_text(normalized.get("project_id")))
    write_result["record"] = normalized
    return write_result


def update_orchestration_run_record(
    config: AppConfig,
    *,
    run_id: str,
    updates: dict[str, Any],
    store_path: str | Path | None = None,
) -> dict[str, Any]:
    normalized_run_id = _text(run_id)
    if not normalized_run_id:
        return {
            "ok": False,
            "store_path": str(resolve_orchestration_run_store_path(config.repo_root, store_path)),
            "record": {},
            "warnings": [],
            "errors": ["run_id is required for update-by-run-id."],
        }
    loaded = read_orchestration_run_store(config, store_path=store_path, bootstrap_missing=True)
    if not loaded["ok"]:
        return {
            "ok": False,
            "store_path": loaded["store_path"],
            "record": {},
            "warnings": _list(loaded.get("warnings")),
            "errors": _list(loaded.get("errors")),
        }
    records = _dicts(loaded.get("records"))
    updated_record: dict[str, Any] | None = None
    next_records: list[dict[str, Any]] = []
    for record in records:
        if _text(record.get("run_id")) == normalized_run_id:
            updated_record = _normalize_record({**record, **updates, "run_id": normalized_run_id, "history_updated_at": _now_iso()})
            next_records.append(updated_record)
        else:
            next_records.append(record)
    if updated_record is None:
        return {
            "ok": False,
            "store_path": loaded["store_path"],
            "record": {},
            "warnings": _list(loaded.get("warnings")),
            "errors": [f"No orchestration run record found for run_id: {normalized_run_id}"],
        }
    validation = validate_run_record(updated_record)
    if not validation["schema_valid"]:
        return {
            "ok": False,
            "store_path": loaded["store_path"],
            "record": updated_record,
            "warnings": _list(validation.get("warnings")),
            "errors": _list(validation.get("errors")),
        }
    write_result = _write_store(
        config,
        store_path=loaded["store_path"],
        records=next_records,
        project_id=_text(updated_record.get("project_id")),
    )
    write_result["record"] = updated_record
    return write_result


def inspect_orchestration_run_store(
    config: AppConfig,
    *,
    project_id: str = DEFAULT_PROJECT_ID,
    item_id: str | None = None,
    run_id: str | None = None,
    history_path: str | Path | None = None,
    queue_path: str | Path | None = None,
    output: str | Path | None = None,
    force: bool = False,
    output_format: str = "json",
) -> dict[str, Any]:
    fmt = _text(output_format).lower() or "json"
    if fmt != "json":
        return _error("invalid_format", {"format": output_format, "supported_formats": ["json"]})
    normalized_project_id = _text(project_id) or DEFAULT_PROJECT_ID
    normalized_item_id = _text(item_id)
    normalized_run_id = _text(run_id)
    loaded = read_orchestration_run_store(
        config,
        store_path=history_path,
        bootstrap_missing=True,
        project_id=normalized_project_id,
    )
    records = _filter_records(
        _dicts(loaded.get("records")),
        project_id=normalized_project_id,
        item_id=normalized_item_id,
        run_id=normalized_run_id,
    )
    gate_payload = _gate_payload(config, item_id=normalized_item_id or DEFAULT_ITEM_ID, queue_path=queue_path)
    gate_summary = _gate_summary(gate_payload)
    blocked_reasons = _dedupe([*_list(loaded.get("errors")), *_list(gate_payload.get("blocked_reasons"))])
    blocked = bool(blocked_reasons)
    warnings = _dedupe([*_list(loaded.get("warnings")), *_store_warnings(records=records, run_id=normalized_run_id)])
    payload: dict[str, Any] = {
        "record_type": RUN_STORE_TYPE,
        "artifact_type": RUN_STORE_TYPE,
        "schema_version": RUN_STORE_SCHEMA_VERSION,
        "generated": True,
        "generated_at": _now_iso(),
        "project_id": normalized_project_id,
        "item_id": normalized_item_id,
        "run_id": normalized_run_id,
        "status": _status(blocked=blocked, records=records, schema_valid=bool(loaded.get("schema_valid"))),
        "blocked": blocked,
        "blocked_reasons": blocked_reasons,
        "warnings": warnings,
        "machine_gates_checked": [gate_summary],
        "machine_gates_passed": bool(gate_summary.get("passed")) and not blocked,
        "autonomy_profile": "local_durable_run_store_inspection",
        "artifacts_created": [],
        "mutation_performed": bool(loaded.get("bootstrap_performed")),
        "queue_mutation_performed": False,
        "external_execution_performed": False,
        "codex_execution_performed": False,
        "model_execution_performed": False,
        "github_execution_performed": False,
        "patch_application_performed": False,
        "local_only": True,
        "next_safe_action": _next_safe_action(
            blocked=blocked,
            bootstrap_performed=bool(loaded.get("bootstrap_performed")),
            records=records,
        ),
        "store_path": _text(loaded.get("store_path")),
        "history_path": _text(loaded.get("store_path")),
        "store_schema_valid": bool(loaded.get("schema_valid")),
        "bootstrap_performed": bool(loaded.get("bootstrap_performed")),
        "store_record_count": len(_dicts(loaded.get("records"))),
        "filtered_record_count": len(records),
        "records": records,
        "filters": {
            "project_id": normalized_project_id,
            "item_id": normalized_item_id,
            "run_id": normalized_run_id,
        },
        "capabilities": {
            "append_supported": True,
            "read_supported": True,
            "update_by_run_id_supported": True,
            "deterministic_ordering": "completed_at_or_started_at_then_run_id",
            "missing_file_bootstrap": True,
            "corruption_safe_errors": True,
        },
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }
    return _emit_or_write(config=config, payload=payload, output=output, force=force)


def validate_run_store_payload(payload: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(payload, dict):
        return {"schema_valid": False, "errors": ["Run store payload must be an object."], "warnings": []}
    records = payload.get("records")
    if records is None:
        errors.append("Run store payload is missing records.")
    elif not isinstance(records, list):
        errors.append("Run store records must be a list.")
    else:
        seen: set[str] = set()
        for index, record in enumerate(records):
            if not isinstance(record, dict):
                errors.append(f"Run store record at index {index} must be an object.")
                continue
            validation = validate_run_record(_normalize_record(record))
            for error in validation["errors"]:
                errors.append(f"Record {index}: {error}")
            run_id = _text(record.get("run_id"))
            if run_id in seen:
                errors.append(f"Record {index}: duplicate run_id {run_id}.")
            if run_id:
                seen.add(run_id)
    if _text(payload.get("artifact_type")) and _text(payload.get("artifact_type")) != RUN_STORE_TYPE:
        warnings.append("Run store artifact_type differs from the current durable run store type.")
    return {"schema_valid": not errors, "errors": errors, "warnings": warnings}


def validate_run_record(record: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    for field in _REQUIRED_RECORD_FIELDS:
        if field not in record:
            errors.append(f"Missing required field: {field}.")
    if not _text(record.get("run_id")):
        errors.append("run_id is required.")
    if not _text(record.get("project_id")):
        errors.append("project_id is required.")
    for field in ("blocked_reasons", "warnings", "machine_gates_checked", "artifacts_created"):
        if field in record and not isinstance(record.get(field), list):
            errors.append(f"{field} must be a list.")
    return {"schema_valid": not errors, "errors": errors, "warnings": []}


def _write_store(
    config: AppConfig,
    *,
    store_path: str | Path,
    records: list[dict[str, Any]],
    project_id: str,
) -> dict[str, Any]:
    path = resolve_orchestration_run_store_path(config.repo_root, store_path)
    store = _empty_store_payload(project_id=project_id or DEFAULT_PROJECT_ID, created_at="", updated_at=_now_iso())
    existing = read_orchestration_run_store(config, store_path=path, bootstrap_missing=False)
    existing_store = existing.get("store", {}) if existing.get("ok") else {}
    if isinstance(existing_store, dict):
        store["created_at"] = _text(existing_store.get("created_at")) or _now_iso()
    store["records"] = _sort_records([_normalize_record(record) for record in records])
    validation = validate_run_store_payload(store)
    if not validation["schema_valid"]:
        return {
            "ok": False,
            "store_path": str(path),
            "store": store,
            "records": store["records"],
            "warnings": _list(validation.get("warnings")),
            "errors": _list(validation.get("errors")),
        }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(store, indent=2) + "\n", encoding="utf-8")
    return {
        "ok": True,
        "store_path": str(path),
        "store": store,
        "records": store["records"],
        "warnings": _list(existing.get("warnings")),
        "errors": [],
    }


def _empty_store_payload(*, project_id: str, created_at: str, updated_at: str) -> dict[str, Any]:
    return {
        "record_type": RUN_STORE_TYPE,
        "artifact_type": RUN_STORE_TYPE,
        "schema_version": RUN_STORE_SCHEMA_VERSION,
        "generated": True,
        "project_id": project_id or DEFAULT_PROJECT_ID,
        "created_at": created_at,
        "updated_at": updated_at,
        "records": [],
    }


def _normalize_record(record: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(record)
    normalized["record_type"] = _text(normalized.get("record_type")) or RUN_RECORD_TYPE
    normalized["generated"] = bool(normalized.get("generated", True))
    normalized["project_id"] = _text(normalized.get("project_id")) or DEFAULT_PROJECT_ID
    normalized["item_id"] = _text(normalized.get("item_id"))
    normalized["run_id"] = _text(normalized.get("run_id"))
    normalized["status"] = _text(normalized.get("status")) or "unknown"
    normalized["blocked"] = bool(normalized.get("blocked"))
    normalized["blocked_reasons"] = _list(normalized.get("blocked_reasons"))
    normalized["warnings"] = _list(normalized.get("warnings"))
    normalized["machine_gates_checked"] = _dicts_or_strings(normalized.get("machine_gates_checked"))
    normalized["machine_gates_passed"] = bool(normalized.get("machine_gates_passed"))
    normalized["autonomy_profile"] = _text(normalized.get("autonomy_profile")) or "orchestration_run_history"
    normalized["artifacts_created"] = _list(normalized.get("artifacts_created"))
    normalized["mutation_performed"] = bool(normalized.get("mutation_performed"))
    normalized["queue_mutation_performed"] = bool(normalized.get("queue_mutation_performed") or normalized.get("mutation_performed"))
    normalized["external_execution_performed"] = bool(normalized.get("external_execution_performed"))
    normalized["codex_execution_performed"] = bool(normalized.get("codex_execution_performed"))
    normalized["model_execution_performed"] = bool(normalized.get("model_execution_performed"))
    normalized["github_execution_performed"] = bool(normalized.get("github_execution_performed"))
    normalized["patch_application_performed"] = bool(normalized.get("patch_application_performed"))
    normalized["local_only"] = bool(normalized.get("local_only", True))
    normalized["next_safe_action"] = _text(normalized.get("next_safe_action")) or "Review the run record before any explicit gated follow-on command."
    return normalized


def _sort_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        records,
        key=lambda record: (
            _text(record.get("completed_at") or record.get("started_at") or record.get("generated_at") or record.get("history_recorded_at")),
            _text(record.get("run_id")),
        ),
    )


def _filter_records(
    records: list[dict[str, Any]],
    *,
    project_id: str,
    item_id: str,
    run_id: str,
) -> list[dict[str, Any]]:
    filtered: list[dict[str, Any]] = []
    for record in records:
        if _text(record.get("project_id")) != project_id:
            continue
        if item_id and _text(record.get("item_id")) != item_id:
            continue
        if run_id and _text(record.get("run_id")) != run_id:
            continue
        filtered.append(record)
    return list(reversed(filtered))


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
        _text(check.get("check_id"))
        for check in checks
        if isinstance(check, dict) and not bool(check.get("passed")) and not bool(check.get("warning_only"))
    ]
    return {
        "gate_profile": _text(gate_payload.get("gate_profile") or gate_payload.get("profile")) or "read_only_agent",
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


def _read_error(path: Path, message: str) -> dict[str, Any]:
    return {
        "ok": False,
        "store_path": str(path),
        "store": {},
        "records": [],
        "schema_valid": False,
        "bootstrap_performed": False,
        "warnings": [],
        "errors": [message],
    }


def _store_warnings(*, records: list[dict[str, Any]], run_id: str) -> list[str]:
    if run_id and not records:
        return [f"No durable orchestration run record matched run_id: {run_id}"]
    return []


def _status(*, blocked: bool, records: list[dict[str, Any]], schema_valid: bool) -> str:
    if blocked:
        return "blocked"
    if not schema_valid:
        return "invalid"
    if records:
        return "ready"
    return "empty"


def _next_safe_action(*, blocked: bool, bootstrap_performed: bool, records: list[dict[str, Any]]) -> str:
    if blocked:
        return "Repair or restore the durable run store before relying on orchestration recovery state."
    if bootstrap_performed:
        return "Durable run store was bootstrapped locally; future explicit orchestration runs can append records."
    if records:
        return "Use durable run records as local evidence; execute follow-on work only through explicit gated commands."
    return "Run an explicit gated orchestration command when ready to create durable run records."


def _resolve(repo_root: Path, value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


def _text(value: Any) -> str:
    return str(value or "").strip()


def _dicts(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [entry for entry in value if isinstance(entry, dict)]
    return []


def _dicts_or_strings(value: Any) -> list[Any]:
    if isinstance(value, list):
        return [entry for entry in value if isinstance(entry, (dict, str))]
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
