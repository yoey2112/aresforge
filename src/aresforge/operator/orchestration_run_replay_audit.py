from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.durable_orchestration_run_store import read_orchestration_run_store
from aresforge.operator.machine_safety_gate_engine import evaluate_machine_safety_gates
from aresforge.operator.orchestration_artifact_retention_policy import inspect_orchestration_artifact_retention
from aresforge.operator.orchestration_run_history import inspect_orchestration_run_history
from aresforge.operator.orchestration_run_monitor import inspect_orchestration_run_monitor

COMMAND_NAME = "replay-orchestration-run"
RECORD_TYPE = "orchestration_run_replay_audit_trail_v1"
REPLAY_SCHEMA_VERSION = "m157.1"
DEFAULT_ITEM_ID = "m157-run-replay-and-audit-trail"
DEFAULT_PROJECT_ID = "aresforge"

_BOUNDARY_CONFIRMATIONS: tuple[str, ...] = (
    "M157 reconstructs orchestration run history from local stored records and artifacts only.",
    "Replay is dry-run metadata reconstruction and never re-executes agents, Codex, models, GitHub, validation commands, patches, or queue progression.",
    "Prior source-run execution flags are reported as observed audit evidence; replay command execution flags remain false.",
    "Any future resume, retry, cleanup, validation, or queue completion remains a separate explicit machine-gated command.",
)


def replay_orchestration_run(
    config: AppConfig,
    *,
    run_id: str,
    project_id: str = DEFAULT_PROJECT_ID,
    item_id: str | None = None,
    dry_run: bool = False,
    history_path: str | Path | None = None,
    artifacts_root: str | Path | None = None,
    queue_path: str | Path | None = None,
    output: str | Path | None = None,
    force: bool = False,
    output_format: str = "json",
) -> dict[str, Any]:
    fmt = _text(output_format).lower() or "json"
    if fmt != "json":
        return _error("invalid_format", {"format": output_format, "supported_formats": ["json"]})

    normalized_run_id = _text(run_id)
    normalized_project_id = _text(project_id) or DEFAULT_PROJECT_ID
    normalized_item_id = _text(item_id) or DEFAULT_ITEM_ID
    gate_payload = _gate_payload(config, item_id=normalized_item_id, queue_path=queue_path)
    primary_gate = _gate_summary(gate_payload, source="replay_inspection_gate")

    if not normalized_run_id:
        payload = _base_payload(
            project_id=normalized_project_id,
            item_id=normalized_item_id,
            run_id=normalized_run_id,
            dry_run=dry_run,
            status="blocked",
            blocked=True,
            blocked_reasons=["run_id is required."],
            warnings=[],
            machine_gates_checked=[primary_gate],
        )
        return _emit_or_write(config=config, payload=payload, output=output, force=force)

    if not dry_run:
        payload = _base_payload(
            project_id=normalized_project_id,
            item_id=normalized_item_id,
            run_id=normalized_run_id,
            dry_run=False,
            status="blocked",
            blocked=True,
            blocked_reasons=[
                "Replay requires --dry-run; M157 only reconstructs metadata and never executes run steps."
            ],
            warnings=[],
            machine_gates_checked=[primary_gate],
        )
        payload["next_safe_action"] = "Re-run with --dry-run to inspect local run evidence without execution."
        return _emit_or_write(config=config, payload=payload, output=output, force=force)

    store = read_orchestration_run_store(
        config,
        store_path=history_path,
        bootstrap_missing=False,
        project_id=normalized_project_id,
    )
    history_payload = _payload(
        inspect_orchestration_run_history(
            config,
            project_id=normalized_project_id,
            item_id=None,
            run_id=normalized_run_id,
            queue_path=queue_path,
            history_path=history_path,
            artifacts_root=artifacts_root,
            output=None,
            force=False,
            output_format="json",
        )
    )
    monitor_payload = _payload(
        inspect_orchestration_run_monitor(
            config,
            project_id=normalized_project_id,
            item_id=None,
            run_id=normalized_run_id,
            queue_path=queue_path,
            history_path=history_path,
            artifacts_root=artifacts_root,
            output=None,
            force=False,
            output_format="json",
        )
    )
    retention_payload = _payload(
        inspect_orchestration_artifact_retention(
            config,
            project_id=normalized_project_id,
            item_id=normalized_item_id,
            history_path=history_path,
            queue_path=queue_path,
            output=None,
            force=False,
            output_format="json",
        )
    )

    durable_record = _matching_record(_dicts(store.get("records")), normalized_run_id, normalized_project_id)
    history_record = _matching_record(_dicts(history_payload.get("records")), normalized_run_id, normalized_project_id)
    monitor_record = _monitor_record(monitor_payload, normalized_run_id, normalized_project_id)
    artifact_paths = _candidate_artifact_paths(
        config.repo_root,
        run_id=normalized_run_id,
        records=[durable_record, history_record, monitor_record],
        retention_payload=retention_payload,
    )
    loaded_artifacts = [_load_artifact(config.repo_root, path) for path in artifact_paths]
    source_runs = [artifact.get("json", {}) for artifact in loaded_artifacts if isinstance(artifact.get("json"), dict)]
    source_run = _best_source_run(source_runs, normalized_run_id)
    step_records = _step_records(source_run)
    gate_records = _gate_records(
        primary_gate=primary_gate,
        component_payloads=[history_payload, monitor_payload, retention_payload],
        source_records=[durable_record, history_record, source_run, *step_records],
    )
    source_execution_flags = _source_execution_flags([durable_record, history_record, monitor_record, source_run, *step_records])
    warnings = _dedupe(
        [
            *_list(store.get("warnings")),
            *_list(history_payload.get("warnings")),
            *_list(monitor_payload.get("warnings")),
            *_artifact_warnings(loaded_artifacts),
            *_missing_run_warnings(
                run_id=normalized_run_id,
                durable_record=durable_record,
                history_record=history_record,
                source_run=source_run,
            ),
        ]
    )
    blocked_reasons = _dedupe(
        [
            *_list(gate_payload.get("blocked_reasons")),
            *_store_blockers(store),
        ]
    )
    blocked = bool(blocked_reasons)
    reconstructed = bool(durable_record or history_record or source_run)
    status = _status(blocked=blocked, reconstructed=reconstructed)

    payload = _base_payload(
        project_id=normalized_project_id,
        item_id=normalized_item_id,
        run_id=normalized_run_id,
        dry_run=True,
        status=status,
        blocked=blocked,
        blocked_reasons=blocked_reasons,
        warnings=warnings,
        machine_gates_checked=[primary_gate],
    )
    payload.update(
        {
            "next_safe_action": _next_safe_action(blocked=blocked, reconstructed=reconstructed),
            "history_path": _text(store.get("store_path")) or _text(history_payload.get("history_path")),
            "artifact_discovery_root": _text(history_payload.get("artifact_discovery_root")),
            "replay_scope": {
                "dry_run": True,
                "metadata_reconstruction_only": True,
                "run_id": normalized_run_id,
                "project_id": normalized_project_id,
                "history_path": _text(store.get("store_path")) or _text(history_payload.get("history_path")),
                "artifact_discovery_root": _text(history_payload.get("artifact_discovery_root")),
                "retention_index_used": bool(retention_payload),
            },
            "replay_summary": {
                "reconstructed": reconstructed,
                "durable_record_found": bool(durable_record),
                "history_record_found": bool(history_record),
                "source_artifact_count": len(loaded_artifacts),
                "source_run_artifact_found": bool(source_run),
                "step_count": len(step_records),
                "audit_event_count": 0,
                "source_execution_flags": source_execution_flags,
            },
            "reconstructed_machine_gates_checked": gate_records,
            "reconstructed_machine_gates_passed": bool(gate_records)
            and all(bool(gate.get("passed")) for gate in gate_records),
            "source_records": {
                "durable_run_store_record": _strip_empty(durable_record),
                "history_record": _strip_empty(history_record),
                "monitor_latest_run": _strip_empty(monitor_record),
            },
            "source_artifacts": [_artifact_summary(artifact) for artifact in loaded_artifacts],
            "step_records": step_records,
            "decision_timeline": _decision_timeline(
                durable_record=durable_record,
                history_record=history_record,
                source_run=source_run,
                step_records=step_records,
            ),
            "audit_trail": _audit_trail(
                run_id=normalized_run_id,
                reconstructed=reconstructed,
                records=[durable_record, history_record, monitor_record],
                artifacts=loaded_artifacts,
                gates=gate_records,
                step_records=step_records,
            ),
            "component_summaries": {
                "history": _component_summary(history_payload),
                "monitor": _component_summary(monitor_payload),
                "retention": _component_summary(retention_payload),
            },
            "replay_safety": {
                "metadata_reconstruction_only": True,
                "agent_execution_performed": False,
                "codex_execution_performed": False,
                "model_execution_performed": False,
                "github_execution_performed": False,
                "validation_command_execution_performed": False,
                "patch_application_performed": False,
                "queue_mutation_performed": False,
                "artifact_cleanup_performed": False,
                "replay_command_reexecuted_source_run": False,
            },
            "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
        }
    )
    payload["replay_summary"]["audit_event_count"] = len(_dicts(payload.get("audit_trail")))
    return _emit_or_write(config=config, payload=payload, output=output, force=force)


def _base_payload(
    *,
    project_id: str,
    item_id: str,
    run_id: str,
    dry_run: bool,
    status: str,
    blocked: bool,
    blocked_reasons: list[str],
    warnings: list[str],
    machine_gates_checked: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "record_type": RECORD_TYPE,
        "artifact_type": RECORD_TYPE,
        "schema_version": REPLAY_SCHEMA_VERSION,
        "generated": True,
        "generated_at": _now_iso(),
        "project_id": project_id,
        "item_id": item_id,
        "run_id": run_id,
        "status": status,
        "blocked": blocked,
        "blocked_reasons": blocked_reasons,
        "warnings": warnings,
        "machine_gates_checked": machine_gates_checked,
        "machine_gates_passed": bool(machine_gates_checked)
        and all(bool(gate.get("passed")) for gate in machine_gates_checked)
        and not blocked,
        "autonomy_profile": "local_orchestration_run_replay_audit",
        "artifacts_created": [],
        "mutation_performed": False,
        "queue_mutation_performed": False,
        "external_execution_performed": False,
        "codex_execution_performed": False,
        "model_execution_performed": False,
        "github_execution_performed": False,
        "patch_application_performed": False,
        "local_only": True,
        "dry_run": bool(dry_run),
        "replay_metadata_reconstruction_performed": bool(dry_run),
        "replay_execution_performed": False,
        "next_safe_action": "Replay local evidence only; use separate explicit gated commands for any follow-on action.",
    }


def _payload(result: dict[str, Any]) -> dict[str, Any]:
    payload = result.get("payload", {}) if isinstance(result, dict) else {}
    return payload if isinstance(payload, dict) else {}


def _matching_record(records: list[dict[str, Any]], run_id: str, project_id: str) -> dict[str, Any]:
    for record in records:
        if _text(record.get("run_id")) == run_id and _text(record.get("project_id")) == project_id:
            return record
    return {}


def _monitor_record(payload: dict[str, Any], run_id: str, project_id: str) -> dict[str, Any]:
    latest = payload.get("latest_run")
    if isinstance(latest, dict) and _text(latest.get("run_id")) == run_id and _text(latest.get("project_id")) == project_id:
        return latest
    return {}


def _candidate_artifact_paths(
    repo_root: Path,
    *,
    run_id: str,
    records: list[dict[str, Any]],
    retention_payload: dict[str, Any],
) -> list[str]:
    paths: list[str] = []
    for record in records:
        if not record:
            continue
        paths.extend([_text(record.get("artifact_path")), *_list(record.get("artifacts_created"))])
    for index in _dicts(retention_payload.get("retention_index")):
        for path in _list(index.get("artifact_paths")):
            if run_id and run_id in path:
                paths.append(path)
    deduped: list[str] = []
    for path in paths:
        text = _text(path)
        if not text:
            continue
        canonical = _canonical_path(repo_root, text)
        if canonical not in deduped:
            deduped.append(canonical)
    return deduped


def _load_artifact(repo_root: Path, path_text: str) -> dict[str, Any]:
    path = Path(path_text)
    if not path.is_absolute():
        path = repo_root / path
    resolved = path.resolve()
    if not resolved.exists():
        return {
            "artifact_path": _relative_path(repo_root, resolved),
            "absolute_path": str(resolved),
            "exists": False,
            "json": {},
            "warnings": ["Referenced artifact is missing."],
        }
    try:
        raw_bytes = resolved.read_bytes()
    except OSError as exc:
        return {
            "artifact_path": _relative_path(repo_root, resolved),
            "absolute_path": str(resolved),
            "exists": True,
            "json": {},
            "warnings": [f"Referenced artifact could not be read: {exc}"],
        }
    parsed: Any = {}
    warnings: list[str] = []
    if resolved.suffix.lower() == ".json":
        try:
            loaded = json.loads(raw_bytes.decode("utf-8-sig"))
            parsed = loaded if isinstance(loaded, dict) else {}
            if not isinstance(loaded, dict):
                warnings.append("Referenced JSON artifact root is not an object.")
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            warnings.append(f"Referenced JSON artifact could not be parsed: {exc}")
    return {
        "artifact_path": _relative_path(repo_root, resolved),
        "absolute_path": str(resolved),
        "exists": True,
        "size_bytes": len(raw_bytes),
        "sha256": hashlib.sha256(raw_bytes).hexdigest(),
        "json": parsed,
        "warnings": warnings,
    }


def _best_source_run(source_runs: list[dict[str, Any]], run_id: str) -> dict[str, Any]:
    for source in source_runs:
        if _text(source.get("run_id")) == run_id:
            return source
    return {}


def _step_records(source_run: dict[str, Any]) -> list[dict[str, Any]]:
    steps = source_run.get("step_results")
    if not isinstance(steps, list):
        return []
    records: list[dict[str, Any]] = []
    for step in steps:
        if not isinstance(step, dict):
            continue
        records.append(
            {
                "record_type": "orchestration_replay_step_record",
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
                "queue_mutation_performed": bool(step.get("queue_mutation_performed")),
                "external_execution_performed": bool(step.get("external_execution_performed")),
                "codex_execution_performed": bool(step.get("codex_execution_performed")),
                "model_execution_performed": bool(step.get("model_execution_performed") or step.get("local_llm_execution_performed")),
                "github_execution_performed": bool(step.get("github_execution_performed")),
                "patch_application_performed": bool(step.get("patch_application_performed")),
                "next_safe_action": _text(step.get("next_safe_action")),
            }
        )
    return records


def _gate_records(
    *,
    primary_gate: dict[str, Any],
    component_payloads: list[dict[str, Any]],
    source_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    gates = [primary_gate]
    for payload in component_payloads:
        for gate in _dicts(payload.get("machine_gates_checked")):
            gates.append(_gate_summary(gate, source=_text(payload.get("record_type")) or "component_inspection"))
    for record in source_records:
        for gate in _dicts(record.get("machine_gates_checked")):
            gates.append(_gate_summary(gate, source="source_run_evidence"))
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


def _gate_payload(config: AppConfig, *, item_id: str, queue_path: str | Path | None) -> dict[str, Any]:
    result = evaluate_machine_safety_gates(
        config,
        item_id=item_id,
        gate_profile="read_only_agent",
        queue_path=queue_path,
        output_format="json",
    )
    return result.get("payload", {}) if isinstance(result, dict) else {}


def _gate_summary(gate_payload: dict[str, Any], *, source: str) -> dict[str, Any]:
    checks = gate_payload.get("checks", [])
    failed = [
        _text(check.get("check_id"))
        for check in checks
        if isinstance(check, dict) and not bool(check.get("passed")) and not bool(check.get("warning_only"))
    ]
    return {
        "source": _text(gate_payload.get("source")) or source,
        "step_id": _text(gate_payload.get("step_id")),
        "agent_id": _text(gate_payload.get("agent_id")),
        "gate_profile": _text(gate_payload.get("gate_profile") or gate_payload.get("profile")) or "read_only_agent",
        "passed": bool(gate_payload.get("passed")) and not bool(gate_payload.get("blocked")),
        "blocked": bool(gate_payload.get("blocked")),
        "blocked_reasons": _list(gate_payload.get("blocked_reasons")),
        "checks_failed": failed or _list(gate_payload.get("checks_failed")),
    }


def _source_execution_flags(records: list[dict[str, Any]]) -> dict[str, bool]:
    return {
        "source_mutation_performed": any(bool(record.get("mutation_performed")) for record in records),
        "source_queue_mutation_performed": any(bool(record.get("queue_mutation_performed")) for record in records),
        "source_external_execution_performed": any(bool(record.get("external_execution_performed")) for record in records),
        "source_codex_execution_performed": any(bool(record.get("codex_execution_performed")) for record in records),
        "source_model_execution_performed": any(bool(record.get("model_execution_performed")) for record in records),
        "source_github_execution_performed": any(bool(record.get("github_execution_performed")) for record in records),
        "source_patch_application_performed": any(bool(record.get("patch_application_performed")) for record in records),
    }


def _decision_timeline(
    *,
    durable_record: dict[str, Any],
    history_record: dict[str, Any],
    source_run: dict[str, Any],
    step_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    timeline: list[dict[str, Any]] = []
    record = source_run or history_record or durable_record
    if record:
        timeline.append(
            {
                "event_type": "run_started",
                "timestamp": _text(record.get("started_at")),
                "run_id": _text(record.get("run_id")),
                "status": _text(record.get("status")),
            }
        )
    for step in sorted(step_records, key=lambda entry: _int(entry.get("sequence"))):
        timeline.append(
            {
                "event_type": "step_result",
                "timestamp": _text(step.get("completed_at")),
                "step_id": _text(step.get("step_id")),
                "sequence": _int(step.get("sequence")),
                "agent_id": _text(step.get("agent_id")),
                "status": _text(step.get("status")),
                "blocked": bool(step.get("blocked")),
            }
        )
    if record:
        timeline.append(
            {
                "event_type": "run_outcome",
                "timestamp": _text(record.get("completed_at")),
                "run_id": _text(record.get("run_id")),
                "status": _text(record.get("status")),
                "blocked": bool(record.get("blocked")),
                "blocked_reasons": _list(record.get("blocked_reasons")),
            }
        )
    return timeline


def _audit_trail(
    *,
    run_id: str,
    reconstructed: bool,
    records: list[dict[str, Any]],
    artifacts: list[dict[str, Any]],
    gates: list[dict[str, Any]],
    step_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = [
        {
            "record_type": "orchestration_replay_audit_event",
            "event_type": "replay_started",
            "run_id": run_id,
            "status": "metadata_reconstruction_only",
            "mutation_performed": False,
        }
    ]
    for source, record in zip(("durable_store", "history", "monitor"), records, strict=False):
        events.append(
            {
                "record_type": "orchestration_replay_audit_event",
                "event_type": "source_record_inspected",
                "source": source,
                "run_id": run_id,
                "found": bool(record),
                "status": _text(record.get("status")),
                "mutation_performed": False,
            }
        )
    for artifact in artifacts:
        events.append(
            {
                "record_type": "orchestration_replay_audit_event",
                "event_type": "artifact_inspected",
                "artifact_path": _text(artifact.get("artifact_path")),
                "exists": bool(artifact.get("exists")),
                "sha256": _text(artifact.get("sha256")),
                "mutation_performed": False,
            }
        )
    for gate in gates:
        events.append(
            {
                "record_type": "orchestration_replay_audit_event",
                "event_type": "machine_gate_reconstructed",
                "source": _text(gate.get("source")),
                "gate_profile": _text(gate.get("gate_profile")),
                "step_id": _text(gate.get("step_id")),
                "passed": bool(gate.get("passed")),
                "blocked": bool(gate.get("blocked")),
                "mutation_performed": False,
            }
        )
    for step in step_records:
        events.append(
            {
                "record_type": "orchestration_replay_audit_event",
                "event_type": "step_reconstructed",
                "step_id": _text(step.get("step_id")),
                "sequence": _int(step.get("sequence")),
                "status": _text(step.get("status")),
                "mutation_performed": False,
            }
        )
    events.append(
        {
            "record_type": "orchestration_replay_audit_event",
            "event_type": "replay_completed",
            "run_id": run_id,
            "status": "reconstructed" if reconstructed else "no_replay_record",
            "mutation_performed": False,
            "codex_execution_performed": False,
            "model_execution_performed": False,
            "github_execution_performed": False,
            "patch_application_performed": False,
        }
    )
    return events


def _component_summary(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "record_type": _text(payload.get("record_type")),
        "status": _text(payload.get("status")),
        "blocked": bool(payload.get("blocked")),
        "blocked_reasons": _list(payload.get("blocked_reasons")),
        "warnings": _list(payload.get("warnings")),
        "machine_gates_passed": bool(payload.get("machine_gates_passed")),
        "local_only": bool(payload.get("local_only", True)),
    }


def _artifact_summary(artifact: dict[str, Any]) -> dict[str, Any]:
    raw = artifact.get("json", {})
    payload = raw if isinstance(raw, dict) else {}
    return {
        "artifact_path": _text(artifact.get("artifact_path")),
        "absolute_path": _text(artifact.get("absolute_path")),
        "exists": bool(artifact.get("exists")),
        "size_bytes": _int(artifact.get("size_bytes")),
        "sha256": _text(artifact.get("sha256")),
        "record_type": _text(payload.get("record_type")),
        "artifact_type": _text(payload.get("artifact_type")),
        "execution_record_type": _text(payload.get("execution_record_type")),
        "run_id": _text(payload.get("run_id")),
        "item_id": _text(payload.get("item_id")),
        "project_id": _text(payload.get("project_id")),
        "status": _text(payload.get("status")),
        "warnings": _list(artifact.get("warnings")),
    }


def _artifact_warnings(artifacts: list[dict[str, Any]]) -> list[str]:
    warnings: list[str] = []
    for artifact in artifacts:
        for warning in _list(artifact.get("warnings")):
            warnings.append(f"{_text(artifact.get('artifact_path'))}: {warning}")
    return warnings


def _missing_run_warnings(
    *,
    run_id: str,
    durable_record: dict[str, Any],
    history_record: dict[str, Any],
    source_run: dict[str, Any],
) -> list[str]:
    if durable_record or history_record or source_run:
        return []
    return [f"No orchestration run evidence matched run_id: {run_id}"]


def _store_blockers(store: dict[str, Any]) -> list[str]:
    if store.get("ok") is False:
        return _list(store.get("errors"))
    return []


def _status(*, blocked: bool, reconstructed: bool) -> str:
    if blocked:
        return "blocked"
    if reconstructed:
        return "replay_reconstructed"
    return "no_replay_record"


def _next_safe_action(*, blocked: bool, reconstructed: bool) -> str:
    if blocked:
        return "Resolve replay inspection blockers before relying on reconstructed audit evidence."
    if reconstructed:
        return "Review the reconstructed audit trail; any resume, retry, validation, cleanup, or queue completion must use a separate explicit gated command."
    return "No matching run evidence was found; inspect run history or create a new explicit gated orchestration run when ready."


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


def _canonical_path(repo_root: Path, value: str) -> str:
    path = Path(value)
    if not path.is_absolute():
        path = repo_root / path
    try:
        return str(path.resolve())
    except OSError:
        return str(path)


def _relative_path(repo_root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo_root.resolve())).replace("\\", "/")
    except ValueError:
        return str(path.resolve())


def _resolve(repo_root: Path, value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


def _strip_empty(value: dict[str, Any]) -> dict[str, Any]:
    return dict(value) if value else {}


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
