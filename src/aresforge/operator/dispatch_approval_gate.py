from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.queue_agent_dispatch_plan import build_queue_agent_dispatch_plan

APPROVAL_GATE_SCHEMA_VERSION = "m101.1"
APPROVAL_GATE_DIR_RELATIVE = Path(".aresforge")
APPROVAL_GATE_FILE_NAME = "dispatch_approval_gates.json"
APPROVAL_GATE_STATUSES: tuple[str, ...] = (
    "pending_review",
    "approved_for_manual_handoff",
    "rejected",
    "needs_revision",
)

DEFAULT_CHECKLIST: tuple[str, ...] = (
    "operator_reviewed_dispatch_or_dry_run_output",
    "operator_confirmed_artifact_matches_selected_lane",
    "operator_confirmed_local_only_boundary",
    "operator_confirmed_execution_allowed_false",
    "operator_confirmed_no_automatic_handoff_or_execution",
    "operator_recorded_review_notes_before_status_change",
)

_BOUNDARY_CONFIRMATIONS = (
    "M101 dispatch approval gates are local-only file-backed records.",
    "Approval gate records do not execute Codex.",
    "Approval gate records do not invoke Ollama, local LLMs, or documentation agents.",
    "Approval gate records do not call GitHub APIs, gh, network services, or external agents.",
    "Approval gate records do not apply patches or mutate dispatch artifacts.",
    "approved_for_manual_handoff authorizes only manual operator handoff review, not automated execution.",
    "execution_allowed=false is preserved for every gate status.",
)


def resolve_dispatch_approval_gate_path(repo_root: Path, path: str | Path | None = None) -> Path:
    if path is None:
        return (repo_root / APPROVAL_GATE_DIR_RELATIVE / APPROVAL_GATE_FILE_NAME).resolve()
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate.resolve()
    return (repo_root / candidate).resolve()


def create_dispatch_approval_gate(
    config: AppConfig,
    *,
    item_id: str,
    artifact_type: str,
    artifact_path: str | Path | None = None,
    dispatch_lane: str | None = None,
    reviewer: str | None = None,
    review_notes: str | None = None,
    checklist: list[str] | None = None,
    approval_path: str | Path | None = None,
    queue_path: str | Path | None = None,
    registry_path: str | Path | None = None,
    output_format: str = "markdown",
) -> dict[str, Any]:
    normalized_item_id = str(item_id or "").strip()
    normalized_artifact_type = str(artifact_type or "").strip()
    resolved_path = resolve_dispatch_approval_gate_path(config.repo_root, approval_path)
    loaded = _load_gate_file(resolved_path)
    gates = loaded["approval_gates"]
    now = _now_iso()
    warnings = list(loaded["warnings"])
    lane = str(dispatch_lane or "").strip()
    if not lane and normalized_item_id:
        plan = build_queue_agent_dispatch_plan(
            config,
            item_id=normalized_item_id,
            queue_path=queue_path,
            registry_path=registry_path,
        )
        lane = str(plan.get("selected_lane", "")).strip()
        plan_blockers = plan.get("blocked_reasons", []) if isinstance(plan.get("blocked_reasons"), list) else []
        warnings.extend(f"Dispatch plan blocker: {reason}" for reason in plan_blockers if str(reason).strip())
        if bool(plan.get("blocked", False)):
            warnings.append("Dispatch plan is currently blocked; gate record was created for review evidence only.")

    blockers = []
    if not normalized_item_id:
        blockers.append("item_id is required.")
    if not normalized_artifact_type:
        blockers.append("artifact_type is required.")
    if blockers:
        payload = _error_payload("create-dispatch-approval-gate", resolved_path, blockers, output_format)
        return payload

    gate = _normalize_gate(
        {
            "approval_id": _make_approval_id(now, normalized_item_id, len(gates) + 1),
            "item_id": normalized_item_id,
            "artifact_type": normalized_artifact_type,
            "artifact_path": _resolve_optional_path(config.repo_root, artifact_path),
            "dispatch_lane": lane,
            "reviewer": str(reviewer or "").strip(),
            "review_notes": str(review_notes or "").strip(),
            "checklist": _normalize_checklist(checklist),
            "created_at": now,
            "updated_at": now,
            "status": "pending_review",
            "local_only": True,
            "execution_allowed": False,
            "next_safe_action": _next_safe_action("pending_review"),
        }
    )
    gates.append(gate)
    write_result = _write_gate_file(resolved_path, gates, now)
    if not write_result["ok"]:
        return _error_payload(
            "create-dispatch-approval-gate",
            resolved_path,
            [str(write_result["reason"])],
            output_format,
            gate=gate,
        )
    payload = _wrap_payload(
        command="create-dispatch-approval-gate",
        approval_path=resolved_path,
        approval_gate=gate,
        approval_gates=[],
        warnings=warnings,
        output_format=output_format,
    )
    return payload


def inspect_dispatch_approval_gate(
    config: AppConfig,
    *,
    approval_id: str | None = None,
    item_id: str | None = None,
    approval_path: str | Path | None = None,
    limit: int | None = None,
    output_format: str = "markdown",
) -> dict[str, Any]:
    resolved_path = resolve_dispatch_approval_gate_path(config.repo_root, approval_path)
    loaded = _load_gate_file(resolved_path)
    gates = loaded["approval_gates"]
    normalized_approval_id = str(approval_id or "").strip()
    normalized_item_id = str(item_id or "").strip()
    filtered = [
        gate
        for gate in gates
        if (not normalized_approval_id or gate["approval_id"] == normalized_approval_id)
        and (not normalized_item_id or gate["item_id"] == normalized_item_id)
    ]
    if isinstance(limit, int) and limit > 0:
        filtered = filtered[-limit:]
    gate = filtered[0] if normalized_approval_id and filtered else {}
    blockers = []
    if normalized_approval_id and not gate:
        blockers.append(f"Approval gate not found: {normalized_approval_id}")
    payload = _wrap_payload(
        command="inspect-dispatch-approval-gate",
        approval_path=resolved_path,
        approval_gate=gate,
        approval_gates=filtered if not normalized_approval_id else [],
        warnings=loaded["warnings"],
        output_format=output_format,
        blockers=blockers,
    )
    return payload


def update_dispatch_approval_gate(
    config: AppConfig,
    *,
    approval_id: str,
    status: str,
    reviewer: str | None = None,
    review_notes: str | None = None,
    checklist: list[str] | None = None,
    approval_path: str | Path | None = None,
    output_format: str = "markdown",
) -> dict[str, Any]:
    resolved_path = resolve_dispatch_approval_gate_path(config.repo_root, approval_path)
    loaded = _load_gate_file(resolved_path)
    gates = loaded["approval_gates"]
    normalized_approval_id = str(approval_id or "").strip()
    normalized_status = str(status or "").strip()
    blockers = []
    if not normalized_approval_id:
        blockers.append("approval_id is required.")
    if normalized_status not in APPROVAL_GATE_STATUSES:
        blockers.append(
            f"Invalid approval status: {normalized_status or '<missing>'}. Supported statuses: {', '.join(APPROVAL_GATE_STATUSES)}."
        )
    index = next((idx for idx, gate in enumerate(gates) if gate["approval_id"] == normalized_approval_id), None)
    if index is None:
        blockers.append(f"Approval gate not found: {normalized_approval_id}")
    if blockers:
        return _error_payload("update-dispatch-approval-gate", resolved_path, blockers, output_format)

    now = _now_iso()
    gate = dict(gates[index])
    gate["status"] = normalized_status
    if reviewer is not None:
        gate["reviewer"] = str(reviewer or "").strip()
    if review_notes is not None:
        gate["review_notes"] = str(review_notes or "").strip()
    if checklist is not None:
        gate["checklist"] = _normalize_checklist(checklist)
    gate["updated_at"] = now
    gate["local_only"] = True
    gate["execution_allowed"] = False
    gate["next_safe_action"] = _next_safe_action(normalized_status)
    gates[index] = _normalize_gate(gate)
    write_result = _write_gate_file(resolved_path, gates, now)
    if not write_result["ok"]:
        return _error_payload(
            "update-dispatch-approval-gate",
            resolved_path,
            [str(write_result["reason"])],
            output_format,
            gate=gates[index],
        )
    return _wrap_payload(
        command="update-dispatch-approval-gate",
        approval_path=resolved_path,
        approval_gate=gates[index],
        approval_gates=[],
        warnings=loaded["warnings"],
        output_format=output_format,
    )


def _load_gate_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"approval_gates": [], "warnings": []}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"approval_gates": [], "warnings": [f"Dispatch approval gate file could not be parsed: {exc}"]}
    if not isinstance(raw, dict):
        return {"approval_gates": [], "warnings": ["Dispatch approval gate file has invalid schema; expected object."]}
    gates = raw.get("approval_gates", [])
    if not isinstance(gates, list):
        return {"approval_gates": [], "warnings": ["Dispatch approval gate file has invalid approval_gates field."]}
    return {"approval_gates": [_normalize_gate(gate) for gate in gates if isinstance(gate, dict)], "warnings": []}


def _write_gate_file(path: Path, gates: list[dict[str, Any]], updated_at: str) -> dict[str, Any]:
    payload = {
        "schema_version": APPROVAL_GATE_SCHEMA_VERSION,
        "updated_at": updated_at,
        "approval_gates": gates,
    }
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    except OSError as exc:
        return {"ok": False, "reason": f"Failed to write dispatch approval gate file: {exc}"}
    return {"ok": True}


def _normalize_gate(gate: dict[str, Any]) -> dict[str, Any]:
    status = str(gate.get("status", "")).strip()
    if status not in APPROVAL_GATE_STATUSES:
        status = "pending_review"
    return {
        "approval_id": str(gate.get("approval_id", "")).strip(),
        "item_id": str(gate.get("item_id", "")).strip(),
        "artifact_type": str(gate.get("artifact_type", "")).strip(),
        "artifact_path": str(gate.get("artifact_path", "")).strip(),
        "dispatch_lane": str(gate.get("dispatch_lane", "")).strip(),
        "reviewer": str(gate.get("reviewer", "")).strip(),
        "review_notes": str(gate.get("review_notes", "")).strip(),
        "checklist": _normalize_checklist(gate.get("checklist")),
        "created_at": str(gate.get("created_at", "")).strip(),
        "updated_at": str(gate.get("updated_at", "")).strip(),
        "status": status,
        "local_only": True,
        "execution_allowed": False,
        "next_safe_action": str(gate.get("next_safe_action", "")).strip() or _next_safe_action(status),
    }


def _normalize_checklist(value: Any) -> list[str]:
    source = value if isinstance(value, list) else []
    normalized = [str(item).strip() for item in source if str(item).strip()]
    if not normalized:
        normalized = list(DEFAULT_CHECKLIST)
    result: list[str] = []
    for item in normalized:
        if item not in result:
            result.append(item)
    return result


def _resolve_optional_path(repo_root: Path, value: str | Path | None) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    candidate = Path(text)
    if candidate.is_absolute():
        return str(candidate.resolve())
    return str((repo_root / candidate).resolve())


def _make_approval_id(timestamp: str, item_id: str, sequence: int) -> str:
    safe_timestamp = re.sub(r"[^0-9A-Za-z]+", "", timestamp)[:20] or "unknown"
    safe_item = re.sub(r"[^a-z0-9]+", "-", item_id.lower()).strip("-") or "item"
    return f"approval-{safe_timestamp}-{safe_item}-{sequence:04d}"


def _next_safe_action(status: str) -> str:
    if status == "approved_for_manual_handoff":
        return "Manual handoff may be prepared by the operator; automated execution remains blocked."
    if status == "rejected":
        return "Do not use this dispatch artifact or dry-run output; revise or abandon the underlying work."
    if status == "needs_revision":
        return "Revise the dispatch artifact or dry-run output, then create or update approval evidence before handoff."
    return "Review the dispatch artifact or dry-run output and record an explicit approval status before any manual handoff."


def _wrap_payload(
    *,
    command: str,
    approval_path: Path,
    approval_gate: dict[str, Any],
    approval_gates: list[dict[str, Any]],
    warnings: list[str],
    output_format: str,
    blockers: list[str] | None = None,
) -> dict[str, Any]:
    normalized_blockers = sorted({str(blocker).strip() for blocker in (blockers or []) if str(blocker).strip()})
    payload = {
        "ok": not normalized_blockers,
        "local_only": True,
        "execution_allowed": False,
        "approval_gate_schema_version": APPROVAL_GATE_SCHEMA_VERSION,
        "approval_path": str(approval_path),
        "approval_gate": approval_gate,
        "approval_gates": approval_gates,
        "approval_statuses": list(APPROVAL_GATE_STATUSES),
        "blocked": bool(normalized_blockers),
        "blocked_reasons": normalized_blockers,
        "warnings": sorted({str(warning).strip() for warning in warnings if str(warning).strip()}),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
        "next_safe_action": approval_gate.get("next_safe_action") if approval_gate else "Review approval gate records; no execution is authorized.",
    }
    return _stdout_result(command, payload, output_format, _render_markdown(command, payload))


def _error_payload(
    command: str,
    approval_path: Path,
    blockers: list[str],
    output_format: str,
    *,
    gate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _wrap_payload(
        command=command,
        approval_path=approval_path,
        approval_gate=gate or {},
        approval_gates=[],
        warnings=[],
        output_format=output_format,
        blockers=blockers,
    )


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
        "wrote_output_file": False,
        "stdout": json.dumps(payload, indent=2) if fmt == "json" else markdown,
        "payload": payload,
    }


def _render_markdown(command: str, payload: dict[str, Any]) -> str:
    gate = payload.get("approval_gate", {}) if isinstance(payload.get("approval_gate"), dict) else {}
    gates = payload.get("approval_gates", []) if isinstance(payload.get("approval_gates"), list) else []
    lines = [
        "# Dispatch Approval Gate",
        "",
        f"- command: {command}",
        f"- ok: {payload.get('ok')}",
        f"- local_only: {payload.get('local_only')}",
        f"- execution_allowed: {payload.get('execution_allowed')}",
        f"- approval_path: {payload.get('approval_path', '')}",
    ]
    if gate:
        lines.extend(
            [
                f"- approval_id: {gate.get('approval_id', '')}",
                f"- item_id: {gate.get('item_id', '')}",
                f"- artifact_type: {gate.get('artifact_type', '')}",
                f"- dispatch_lane: {gate.get('dispatch_lane', '')}",
                f"- status: {gate.get('status', '')}",
                f"- reviewer: {gate.get('reviewer', '') or '-'}",
                f"- next_safe_action: {gate.get('next_safe_action', '')}",
                "",
                "## Checklist",
            ]
        )
        lines.extend(f"- {item}" for item in gate.get("checklist", []) if str(item).strip())
    elif gates:
        lines.extend(["", "## Approval Gates"])
        lines.extend(
            f"- {entry.get('approval_id', '')} | {entry.get('status', '')} | {entry.get('item_id', '')} | {entry.get('artifact_type', '')}"
            for entry in gates
            if isinstance(entry, dict)
        )
    blockers = payload.get("blocked_reasons", []) if isinstance(payload.get("blocked_reasons"), list) else []
    if blockers:
        lines.extend(["", "## Blocked Reasons"])
        lines.extend(f"- {reason}" for reason in blockers)
    warnings = payload.get("warnings", []) if isinstance(payload.get("warnings"), list) else []
    if warnings:
        lines.extend(["", "## Warnings"])
        lines.extend(f"- {warning}" for warning in warnings)
    return "\n".join(lines).rstrip()


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()
