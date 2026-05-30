from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.dispatch_approval_gate import resolve_dispatch_approval_gate_path
from aresforge.operator.dispatch_artifact_registry import inspect_artifact_registry
from aresforge.operator.local_project_queue import resolve_project_queue_path

COMMAND_INSPECT = "inspect-approval-ledger"
COMMAND_RECORD = "record-artifact-review"
LEDGER_TYPE = "human_approval_review_ledger"
LEDGER_SCHEMA_VERSION = "m121.1"
LEDGER_PATH_RELATIVE = Path(".aresforge") / "approval_review_ledger.json"
REVIEW_DECISIONS = ("approved", "rejected", "needs_changes")

_GATE_DECISION_BY_STATUS = {
    "approved_for_manual_handoff": "approved",
    "rejected": "rejected",
    "needs_revision": "needs_changes",
}

_BOUNDARY_CONFIRMATIONS = (
    "M121 approval review ledger is local-only.",
    "M121 records human review metadata only.",
    "M121 does not approve artifacts automatically.",
    "M121 does not execute Codex, agents, Ollama, local LLMs, remote LLMs, GitHub, gh, network services, validation commands, or patches.",
    "M121 does not apply patches, start queue items, complete queue items, or mutate external systems.",
    "execution_allowed=false is preserved for ledger payloads.",
)


def inspect_approval_ledger(
    config: AppConfig,
    *,
    project_id: str,
    item_id: str | None = None,
    artifact_path: str | Path | None = None,
    output: str | Path | None = None,
    force: bool = False,
    output_format: str = "markdown",
    ledger_path: str | Path | None = None,
    approval_path: str | Path | None = None,
    queue_path: str | Path | None = None,
) -> dict[str, Any]:
    fmt = _format(output_format)
    if fmt not in {"json", "markdown"}:
        return _error(COMMAND_INSPECT, "invalid_format", {"format": output_format, "supported_formats": ["json", "markdown"]})
    normalized_project_id = str(project_id or "").strip()
    if not normalized_project_id:
        return _error(COMMAND_INSPECT, "invalid_project_id", {"message": "project_id is required."})

    normalized_item_id = str(item_id or "").strip()
    normalized_artifact_path = _normalized_optional_path(config.repo_root, artifact_path)
    artifacts = _load_artifacts(
        config,
        project_id=normalized_project_id,
        item_id=normalized_item_id,
        artifact_path=normalized_artifact_path,
        queue_path=queue_path,
    )
    records = _combined_review_records(
        config,
        ledger_path=ledger_path,
        approval_path=approval_path,
        item_id=normalized_item_id,
        artifact_path=normalized_artifact_path,
    )
    records_by_artifact = _records_by_artifact(records)

    reviewed_artifacts: list[dict[str, Any]] = []
    unreviewed_artifacts: list[dict[str, Any]] = []
    approval_gaps: list[dict[str, Any]] = []

    for artifact in artifacts:
        key = _artifact_key(str(artifact.get("artifact_path", "")))
        artifact_records = records_by_artifact.get(key, [])
        latest = artifact_records[-1] if artifact_records else {}
        entry = _artifact_review_entry(artifact, artifact_records, latest)
        if latest and latest.get("decision") in REVIEW_DECISIONS:
            reviewed_artifacts.append(entry)
        else:
            unreviewed_artifacts.append(entry)
            approval_gaps.append(
                {
                    "item_id": entry["item_id"],
                    "artifact_path": entry["artifact_path"],
                    "artifact_type": entry["artifact_type"],
                    "reason": "no_human_review_decision_recorded",
                }
            )

    # Include review records for explicit artifact filters even when the artifact is no longer discoverable.
    if normalized_artifact_path and not artifacts:
        matching_records = [record for record in records if _same_path(record.get("artifact_path", ""), normalized_artifact_path)]
        if not matching_records:
            approval_gaps.append(
                {
                    "item_id": normalized_item_id,
                    "artifact_path": normalized_artifact_path,
                    "artifact_type": "",
                    "reason": "artifact_not_found_and_no_review_record",
                }
            )

    payload: dict[str, Any] = {
        "ok": True,
        "ledger_type": LEDGER_TYPE,
        "ledger_schema_version": LEDGER_SCHEMA_VERSION,
        "generated": True,
        "generated_at": _now_iso(),
        "project_id": normalized_project_id,
        "item_id": normalized_item_id,
        "artifact_path": normalized_artifact_path,
        "ledger_path": str(_resolve_ledger_path(config.repo_root, ledger_path)),
        "reviewed_artifacts": reviewed_artifacts,
        "unreviewed_artifacts": unreviewed_artifacts,
        "approved_artifacts": [entry for entry in reviewed_artifacts if entry.get("latest_decision") == "approved"],
        "rejected_artifacts": [entry for entry in reviewed_artifacts if entry.get("latest_decision") == "rejected"],
        "needs_changes_artifacts": [entry for entry in reviewed_artifacts if entry.get("latest_decision") == "needs_changes"],
        "review_records": records,
        "approval_gaps": approval_gaps,
        "local_only": True,
        "execution_allowed": False,
        "next_safe_action": _next_safe_action(reviewed_artifacts, approval_gaps),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }
    return _emit_or_write(config=config, command=COMMAND_INSPECT, payload=payload, output=output, force=force, output_format=fmt)


def record_artifact_review(
    config: AppConfig,
    *,
    item_id: str,
    artifact_path: str | Path,
    decision: str,
    reviewer: str | None = None,
    review_notes: str | None = None,
    output: str | Path | None = None,
    force: bool = False,
    output_format: str = "markdown",
    ledger_path: str | Path | None = None,
) -> dict[str, Any]:
    fmt = _format(output_format)
    if fmt not in {"json", "markdown"}:
        return _error(COMMAND_RECORD, "invalid_format", {"format": output_format, "supported_formats": ["json", "markdown"]})

    normalized_item_id = str(item_id or "").strip()
    normalized_artifact_path = _normalized_optional_path(config.repo_root, artifact_path)
    normalized_decision = str(decision or "").strip()
    blockers: list[str] = []
    if not normalized_item_id:
        blockers.append("item_id is required.")
    if not normalized_artifact_path:
        blockers.append("artifact_path is required.")
    if normalized_decision not in REVIEW_DECISIONS:
        blockers.append(f"decision must be one of: {', '.join(REVIEW_DECISIONS)}.")
    artifact_exists = bool(normalized_artifact_path and Path(normalized_artifact_path).exists())
    if blockers:
        return _record_payload(
            ok=False,
            blocked_reasons=blockers,
            record={},
            ledger_path=_resolve_ledger_path(config.repo_root, ledger_path),
            output_format=fmt,
        )

    resolved_ledger_path = _resolve_ledger_path(config.repo_root, ledger_path)
    loaded = _load_ledger_file(resolved_ledger_path)
    records = loaded["review_records"]
    now = _now_iso()
    record = {
        "review_id": _review_id(normalized_item_id, normalized_artifact_path, now, len(records) + 1),
        "item_id": normalized_item_id,
        "artifact_path": normalized_artifact_path,
        "artifact_exists": artifact_exists,
        "artifact_type": _infer_artifact_type(config, normalized_artifact_path),
        "decision": normalized_decision,
        "reviewer": str(reviewer or "local_operator").strip() or "local_operator",
        "review_notes": str(review_notes or "").strip(),
        "recorded_at": now,
        "source": "record-artifact-review",
        "local_only": True,
        "execution_allowed": False,
        "patch_application_allowed": False,
        "patch_application_performed": False,
        "queue_mutation_performed": False,
        "next_safe_action": _record_next_safe_action(normalized_decision),
    }
    records.append(record)
    write_result = _write_ledger_file(resolved_ledger_path, records, now)
    if not write_result["ok"]:
        return _record_payload(
            ok=False,
            blocked_reasons=[write_result["reason"]],
            record=record,
            ledger_path=resolved_ledger_path,
            output_format=fmt,
        )
    payload = _record_payload(
        ok=True,
        blocked_reasons=[],
        record=record,
        ledger_path=resolved_ledger_path,
        output_format=fmt,
    )
    if output:
        return _emit_or_write(config=config, command=COMMAND_RECORD, payload=payload["payload"], output=output, force=force, output_format=fmt)
    return payload


def _load_artifacts(
    config: AppConfig,
    *,
    project_id: str,
    item_id: str,
    artifact_path: str,
    queue_path: str | Path | None,
) -> list[dict[str, Any]]:
    result = inspect_artifact_registry(
        config,
        project_id=project_id,
        item_id=item_id or None,
        output_format="json",
        queue_path=queue_path,
    )
    payload = result.get("payload", result)
    artifacts = payload.get("artifacts", []) if isinstance(payload, dict) else []
    if not isinstance(artifacts, list):
        return []
    normalized = [artifact for artifact in artifacts if isinstance(artifact, dict)]
    if artifact_path:
        normalized = [artifact for artifact in normalized if _same_path(str(artifact.get("artifact_path", "")), artifact_path)]
    return normalized


def _combined_review_records(
    config: AppConfig,
    *,
    ledger_path: str | Path | None,
    approval_path: str | Path | None,
    item_id: str,
    artifact_path: str,
) -> list[dict[str, Any]]:
    ledger_records = _load_ledger_file(_resolve_ledger_path(config.repo_root, ledger_path))["review_records"]
    gate_records = _approval_gate_records(config, approval_path=approval_path)
    records = [*ledger_records, *gate_records]
    if item_id:
        records = [record for record in records if str(record.get("item_id", "")).strip() == item_id]
    if artifact_path:
        records = [record for record in records if _same_path(record.get("artifact_path", ""), artifact_path)]
    return sorted(records, key=lambda record: str(record.get("recorded_at", "") or record.get("updated_at", "")))


def _approval_gate_records(config: AppConfig, *, approval_path: str | Path | None) -> list[dict[str, Any]]:
    path = resolve_dispatch_approval_gate_path(config.repo_root, approval_path)
    if not path.exists():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    gates = raw.get("approval_gates", []) if isinstance(raw, dict) else []
    records: list[dict[str, Any]] = []
    if not isinstance(gates, list):
        return records
    for gate in gates:
        if not isinstance(gate, dict):
            continue
        status = str(gate.get("status", "")).strip()
        decision = _GATE_DECISION_BY_STATUS.get(status)
        if not decision:
            continue
        artifact_path = str(gate.get("artifact_path", "")).strip()
        records.append(
            {
                "review_id": str(gate.get("approval_id", "")).strip(),
                "item_id": str(gate.get("item_id", "")).strip(),
                "artifact_path": artifact_path,
                "artifact_exists": bool(artifact_path and Path(artifact_path).exists()),
                "artifact_type": str(gate.get("artifact_type", "")).strip(),
                "decision": decision,
                "approval_status": status,
                "reviewer": str(gate.get("reviewer", "")).strip(),
                "review_notes": str(gate.get("review_notes", "")).strip(),
                "recorded_at": str(gate.get("updated_at", "") or gate.get("created_at", "")).strip(),
                "source": "dispatch_approval_gate",
                "local_only": True,
                "execution_allowed": False,
                "patch_application_allowed": False,
                "patch_application_performed": False,
                "queue_mutation_performed": False,
                "next_safe_action": str(gate.get("next_safe_action", "")).strip(),
            }
        )
    return records


def _load_ledger_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"review_records": [], "warnings": []}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"review_records": [], "warnings": [f"Approval review ledger could not be parsed: {exc}"]}
    if not isinstance(raw, dict):
        return {"review_records": [], "warnings": ["Approval review ledger has invalid schema; expected object."]}
    records = raw.get("review_records", [])
    if not isinstance(records, list):
        return {"review_records": [], "warnings": ["Approval review ledger review_records must be a list."]}
    return {"review_records": [_normalize_review_record(record) for record in records if isinstance(record, dict)], "warnings": []}


def _write_ledger_file(path: Path, records: list[dict[str, Any]], updated_at: str) -> dict[str, Any]:
    payload = {
        "schema_version": LEDGER_SCHEMA_VERSION,
        "ledger_type": LEDGER_TYPE,
        "updated_at": updated_at,
        "review_records": records,
        "local_only": True,
        "execution_allowed": False,
    }
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    except OSError as exc:
        return {"ok": False, "reason": f"Failed to write approval review ledger: {exc}"}
    return {"ok": True}


def _normalize_review_record(record: dict[str, Any]) -> dict[str, Any]:
    decision = str(record.get("decision", "")).strip()
    if decision not in REVIEW_DECISIONS:
        decision = "needs_changes"
    return {
        "review_id": str(record.get("review_id", "")).strip(),
        "item_id": str(record.get("item_id", "")).strip(),
        "artifact_path": str(record.get("artifact_path", "")).strip(),
        "artifact_exists": bool(record.get("artifact_exists", False)),
        "artifact_type": str(record.get("artifact_type", "")).strip(),
        "decision": decision,
        "reviewer": str(record.get("reviewer", "")).strip(),
        "review_notes": str(record.get("review_notes", "")).strip(),
        "recorded_at": str(record.get("recorded_at", "")).strip(),
        "source": str(record.get("source", "record-artifact-review")).strip() or "record-artifact-review",
        "local_only": True,
        "execution_allowed": False,
        "patch_application_allowed": False,
        "patch_application_performed": False,
        "queue_mutation_performed": False,
        "next_safe_action": str(record.get("next_safe_action", "") or _record_next_safe_action(decision)).strip(),
    }


def _artifact_review_entry(
    artifact: dict[str, Any],
    records: list[dict[str, Any]],
    latest: dict[str, Any],
) -> dict[str, Any]:
    return {
        "artifact_id": str(artifact.get("artifact_id", "")).strip(),
        "artifact_type": str(artifact.get("artifact_type", "")).strip(),
        "item_id": str(artifact.get("item_id", "")).strip(),
        "project_id": str(artifact.get("project_id", "")).strip(),
        "artifact_path": str(artifact.get("artifact_path", "")).strip(),
        "relative_path": str(artifact.get("relative_path", "")).strip(),
        "latest_decision": str(latest.get("decision", "")).strip(),
        "latest_review_id": str(latest.get("review_id", "")).strip(),
        "review_record_count": len(records),
        "local_only": True,
        "execution_allowed": False,
    }


def _records_by_artifact(records: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        key = _artifact_key(str(record.get("artifact_path", "")))
        if not key:
            continue
        result.setdefault(key, []).append(record)
    return result


def _resolve_ledger_path(repo_root: Path, path: str | Path | None) -> Path:
    if path is None:
        return (repo_root / LEDGER_PATH_RELATIVE).resolve()
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate.resolve()
    return (repo_root / candidate).resolve()


def _normalized_optional_path(repo_root: Path, path: str | Path | None) -> str:
    text = str(path or "").strip()
    if not text:
        return ""
    candidate = Path(text)
    if candidate.is_absolute():
        return str(candidate.resolve())
    return str((repo_root / candidate).resolve())


def _same_path(left: Any, right: Any) -> bool:
    return _artifact_key(str(left or "")) == _artifact_key(str(right or ""))


def _artifact_key(path: str) -> str:
    text = str(path or "").strip()
    if not text:
        return ""
    try:
        return str(Path(text).resolve()).lower()
    except OSError:
        return text.lower()


def _infer_artifact_type(config: AppConfig, artifact_path: str) -> str:
    result = inspect_artifact_registry(config, output_format="json")
    payload = result.get("payload", result)
    artifacts = payload.get("artifacts", []) if isinstance(payload, dict) else []
    if isinstance(artifacts, list):
        for artifact in artifacts:
            if isinstance(artifact, dict) and _same_path(artifact.get("artifact_path", ""), artifact_path):
                return str(artifact.get("artifact_type", "")).strip()
    return ""


def _review_id(item_id: str, artifact_path: str, timestamp: str, sequence: int) -> str:
    digest = hashlib.sha256(f"{item_id}|{artifact_path}|{timestamp}|{sequence}".encode("utf-8")).hexdigest()[:12]
    return f"review-{digest}"


def _next_safe_action(reviewed: list[dict[str, Any]], gaps: list[dict[str, Any]]) -> str:
    if gaps:
        return "Record human review decisions for approval gaps before manual handoff, patch intake, or completion."
    if reviewed:
        return "Review approved/rejected/needs_changes artifacts and proceed only through separate operator-gated commands."
    return "Generate local artifacts or record artifact reviews before relying on approval inventory."


def _record_next_safe_action(decision: str) -> str:
    if decision == "approved":
        return "Approval is recorded for review only; use a separate operator-gated command for any follow-on action."
    if decision == "rejected":
        return "Do not use this artifact for handoff or completion unless a new review supersedes it."
    return "Revise the artifact and record a new review before handoff or completion."


def _record_payload(
    *,
    ok: bool,
    blocked_reasons: list[str],
    record: dict[str, Any],
    ledger_path: Path,
    output_format: str,
) -> dict[str, Any]:
    payload = {
        "ok": ok,
        "ledger_type": LEDGER_TYPE,
        "generated": True,
        "review_record": record,
        "blocked": bool(blocked_reasons),
        "blocked_reasons": blocked_reasons,
        "ledger_path": str(ledger_path),
        "local_only": True,
        "execution_allowed": False,
        "next_safe_action": record.get("next_safe_action", "Fix blocked reasons before recording review.") if record else "Fix blocked reasons before recording review.",
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }
    return {
        "command": COMMAND_RECORD,
        "ok": ok,
        "local_only": True,
        "format": output_format,
        "wrote_output_file": False,
        "stdout": json.dumps(payload, indent=2) if output_format == "json" else _render_record_markdown(payload),
        "payload": payload,
    }


def _emit_or_write(
    *,
    config: AppConfig,
    command: str,
    payload: dict[str, Any],
    output: str | Path | None,
    force: bool,
    output_format: str,
) -> dict[str, Any]:
    rendered = json.dumps(payload, indent=2) if output_format == "json" else _render_ledger_markdown(payload)
    if output:
        target = Path(output)
        if not target.is_absolute():
            target = config.repo_root / target
        target = target.resolve()
        if target.exists() and not force:
            blocked_payload = dict(payload)
            blocked_payload["ok"] = False
            blocked_payload["blocked"] = True
            blocked_payload["blocked_reasons"] = [f"Output already exists: {target}"]
            blocked_payload["next_safe_action"] = "Choose a new output path or rerun with --force after operator review."
            return {
                "command": command,
                "ok": False,
                "local_only": True,
                "format": output_format,
                "wrote_output_file": False,
                "output_path": str(target),
                "stdout": json.dumps(blocked_payload, indent=2) if output_format == "json" else _render_ledger_markdown(blocked_payload),
                "payload": blocked_payload,
            }
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(rendered + "\n", encoding="utf-8")
        payload = dict(payload)
        payload["output_path"] = str(target)
        return {
            "command": command,
            "ok": True,
            "local_only": True,
            "format": output_format,
            "wrote_output_file": True,
            "output_path": str(target),
            "stdout": json.dumps(payload, indent=2) if output_format == "json" else _render_ledger_markdown(payload),
            "payload": payload,
        }
    return {
        "command": command,
        "ok": True,
        "local_only": True,
        "format": output_format,
        "wrote_output_file": False,
        "stdout": rendered,
        "payload": payload,
    }


def _render_ledger_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Human Approval Review Ledger",
        "",
        f"- ledger_type: {payload.get('ledger_type')}",
        f"- project_id: {payload.get('project_id')}",
        f"- reviewed_count: {len(payload.get('reviewed_artifacts', [])) if isinstance(payload.get('reviewed_artifacts'), list) else 0}",
        f"- unreviewed_count: {len(payload.get('unreviewed_artifacts', [])) if isinstance(payload.get('unreviewed_artifacts'), list) else 0}",
        f"- execution_allowed: {payload.get('execution_allowed')}",
        "",
        "## Approval Gaps",
    ]
    gaps = payload.get("approval_gaps", [])
    if isinstance(gaps, list) and gaps:
        lines.extend(f"- {gap.get('item_id')} | {gap.get('artifact_type')} | {gap.get('reason')}" for gap in gaps if isinstance(gap, dict))
    else:
        lines.append("- None")
    lines.extend(["", f"- next_safe_action: {payload.get('next_safe_action')}"])
    return "\n".join(lines).rstrip()


def _render_record_markdown(payload: dict[str, Any]) -> str:
    record = payload.get("review_record", {}) if isinstance(payload.get("review_record"), dict) else {}
    return "\n".join(
        [
            "# Artifact Review Record",
            "",
            f"- ok: {payload.get('ok')}",
            f"- ledger_type: {payload.get('ledger_type')}",
            f"- review_id: {record.get('review_id', '')}",
            f"- item_id: {record.get('item_id', '')}",
            f"- decision: {record.get('decision', '')}",
            f"- execution_allowed: {payload.get('execution_allowed')}",
            f"- next_safe_action: {payload.get('next_safe_action')}",
        ]
    ).rstrip()


def _error(command: str, code: str, details: dict[str, Any]) -> dict[str, Any]:
    return {
        "command": command,
        "ok": False,
        "local_only": True,
        "execution_allowed": False,
        "error": code,
        "details": details,
    }


def _format(output_format: str) -> str:
    return str(output_format or "markdown").strip().lower()


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()
