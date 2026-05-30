from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.dispatch_approval_gate import resolve_dispatch_approval_gate_path
from aresforge.operator.local_project_queue import resolve_project_queue_path

PATCH_INTAKE_CONTRACT_VERSION = "m111.1"
COMMAND_NAME = "intake-patch-proposal"
APPROVED_STATUS = "approved_for_manual_handoff"
PATCH_ARTIFACT_TYPES = {"patch_proposal", "patch", "manual_patch_proposal", "codex_patch_proposal"}

_BOUNDARY_CONFIRMATIONS = (
    "M111 patch proposal intake is local-only metadata recording.",
    "Patch proposal intake does not apply patches.",
    "Patch proposal intake does not mutate repository files.",
    "Patch proposal intake does not execute Codex, local LLMs, documentation agents, or external agents.",
    "Patch proposal intake does not call GitHub APIs, gh, network services, issues, PRs, or workflows.",
    "Approval only allows review intake; patch application remains blocked.",
    "Queue completion remains a separate explicit operator evidence action.",
)


def intake_patch_proposal(
    config: AppConfig,
    *,
    item_id: str,
    patch_artifact: str | Path,
    approval_id: str | None = None,
    queue_path: str | Path | None = None,
    approval_path: str | Path | None = None,
    output: str | Path | None = None,
    force: bool = False,
    output_format: str = "markdown",
) -> dict[str, Any]:
    fmt = str(output_format or "markdown").lower().strip()
    if fmt not in {"markdown", "json"}:
        return _error("invalid_format", {"format": output_format, "supported_formats": ["markdown", "json"]})

    normalized_item_id = str(item_id or "").strip()
    item = _load_queue_item(config, item_id=normalized_item_id, queue_path=queue_path)
    patch_path = _resolve_path(config.repo_root, patch_artifact)
    gate = _select_approval_gate(
        config=config,
        item_id=normalized_item_id,
        patch_artifact_path=patch_path,
        approval_id=approval_id,
        approval_path=approval_path,
    )
    blocked_reasons = _blocked_reasons(item=item, patch_path=patch_path, gate=gate, requested_approval_id=approval_id)
    accepted = not blocked_reasons
    payload = _build_payload(
        config=config,
        item_id=normalized_item_id,
        item=item,
        patch_path=patch_path,
        gate=gate,
        accepted=accepted,
        blocked_reasons=blocked_reasons,
    )
    return _emit_or_write(config=config, payload=payload, output=output, force=force, output_format=fmt)


def _build_payload(
    *,
    config: AppConfig,
    item_id: str,
    item: dict[str, Any],
    patch_path: Path,
    gate: dict[str, Any],
    accepted: bool,
    blocked_reasons: list[str],
) -> dict[str, Any]:
    return {
        "patch_intake_contract_version": PATCH_INTAKE_CONTRACT_VERSION,
        "intake_record_type": "patch_proposal_intake",
        "accepted_for_review": accepted,
        "blocked": not accepted,
        "blocked_reasons": sorted({reason for reason in blocked_reasons if reason}),
        "item_id": item_id,
        "title": str(item.get("title", "")).strip(),
        "project_id": str(item.get("project_id", "")).strip(),
        "milestone": _milestone(item),
        "patch_artifact_path": str(patch_path),
        "patch_artifact_exists": patch_path.exists(),
        "patch_summary": _patch_summary(patch_path),
        "approval_gate_id": str(gate.get("approval_id", "")).strip(),
        "approval_status": str(gate.get("status", "")).strip() if gate else "missing",
        "operator_review_required": True,
        "patch_application_allowed": False,
        "patch_application_performed": False,
        "local_only": True,
        "execution_allowed": False,
        "recorded_at": _now_iso(),
        "repo_root": str(config.repo_root),
        "next_safe_action": _next_safe_action(accepted=accepted, blocked_reasons=blocked_reasons),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }


def _load_queue_item(config: AppConfig, *, item_id: str, queue_path: str | Path | None) -> dict[str, Any]:
    path = resolve_project_queue_path(config.repo_root, queue_path)
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    items = raw.get("work_items", []) if isinstance(raw, dict) else []
    for item in items:
        if isinstance(item, dict) and str(item.get("item_id", "")).strip() == item_id:
            return item
    return {}


def _select_approval_gate(
    *,
    config: AppConfig,
    item_id: str,
    patch_artifact_path: Path,
    approval_id: str | None,
    approval_path: str | Path | None,
) -> dict[str, Any]:
    gates = _load_approval_gates(resolve_dispatch_approval_gate_path(config.repo_root, approval_path))
    requested_id = str(approval_id or "").strip()
    if requested_id:
        return next((dict(gate) for gate in gates if str(gate.get("approval_id", "")).strip() == requested_id), {})
    candidates = [
        gate
        for gate in gates
        if str(gate.get("item_id", "")).strip() == item_id
        and str(gate.get("artifact_type", "")).strip() in PATCH_ARTIFACT_TYPES
    ]
    exact_path = [
        gate for gate in candidates if str(gate.get("artifact_path", "")).strip() == str(patch_artifact_path)
    ]
    candidates = exact_path or candidates
    if not candidates:
        return {}
    return dict(sorted(candidates, key=lambda gate: str(gate.get("updated_at") or gate.get("created_at") or ""))[-1])


def _load_approval_gates(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    gates = raw.get("approval_gates", []) if isinstance(raw, dict) else []
    return [gate for gate in gates if isinstance(gate, dict)]


def _blocked_reasons(
    *,
    item: dict[str, Any],
    patch_path: Path,
    gate: dict[str, Any],
    requested_approval_id: str | None,
) -> list[str]:
    reasons: list[str] = []
    if not item:
        reasons.append("Queue item was not found.")
    if not patch_path.exists():
        reasons.append(f"Patch artifact is missing: {patch_path}")
    if requested_approval_id and not gate:
        reasons.append(f"Approval gate not found: {str(requested_approval_id).strip()}")
    elif not gate:
        reasons.append("Approval gate is missing; explicit human approval is required before patch intake.")
    else:
        status = str(gate.get("status", "")).strip()
        if status != APPROVED_STATUS:
            reasons.append(f"Approval gate status is {status or '<missing>'}; required {APPROVED_STATUS}.")
        if gate.get("local_only", True) is not True:
            reasons.append("Approval gate local_only must be true.")
        if gate.get("execution_allowed", False) is not False:
            reasons.append("Approval gate execution_allowed must be false.")
    return sorted({reason for reason in reasons if reason})


def _patch_summary(patch_path: Path) -> dict[str, Any]:
    if not patch_path.exists():
        return {
            "format": "missing",
            "line_count": 0,
            "files_touched": [],
            "additions": 0,
            "deletions": 0,
            "sha256_available": False,
        }
    try:
        text = patch_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = patch_path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    files: list[str] = []
    additions = 0
    deletions = 0
    for line in lines:
        if line.startswith("+++ ") or line.startswith("--- "):
            candidate = line[4:].strip()
            if candidate and candidate != "/dev/null":
                cleaned = candidate[2:] if candidate.startswith(("a/", "b/")) else candidate
                if cleaned not in files:
                    files.append(cleaned)
        elif line.startswith("+") and not line.startswith("+++"):
            additions += 1
        elif line.startswith("-") and not line.startswith("---"):
            deletions += 1
    return {
        "format": "unified_diff" if any(line.startswith("diff --git ") or line.startswith("@@") for line in lines) else "unknown",
        "line_count": len(lines),
        "files_touched": files,
        "additions": additions,
        "deletions": deletions,
        "sha256_available": True,
        "sha256": _sha256(patch_path),
    }


def _sha256(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _resolve_path(repo_root: Path, value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


def _milestone(item: dict[str, Any]) -> str:
    tags = item.get("tags", []) if isinstance(item.get("tags"), list) else []
    for tag in tags:
        text = str(tag).strip()
        if text.startswith("milestone:"):
            return text.split(":", 1)[1].split(",", 1)[0].strip()
    item_id = str(item.get("item_id", "")).strip()
    return item_id.split("-", 1)[0].upper() if item_id.lower().startswith("m") and "-" in item_id else ""


def _next_safe_action(*, accepted: bool, blocked_reasons: list[str]) -> str:
    if accepted:
        return "Record human review notes and validation evidence; patch application remains blocked until a separate explicit apply workflow exists."
    if any("Approval gate" in reason for reason in blocked_reasons):
        return "Create or approve a local human approval gate for this patch proposal before review intake."
    if any("Patch artifact is missing" in reason for reason in blocked_reasons):
        return "Provide a local patch artifact path before patch proposal intake."
    return "Resolve blocked reasons before patch proposal intake."


def _emit_or_write(
    *,
    config: AppConfig,
    payload: dict[str, Any],
    output: str | Path | None,
    force: bool,
    output_format: str,
) -> dict[str, Any]:
    rendered = json.dumps(payload, indent=2) if output_format == "json" else _render_markdown(payload)
    ok = bool(payload.get("accepted_for_review")) and not bool(payload.get("blocked"))
    if output is None:
        return {
            "command": COMMAND_NAME,
            "ok": ok,
            "local_only": True,
            "format": output_format,
            "wrote_output_file": False,
            "stdout": rendered,
            "payload": payload,
        }
    output_path = _resolve_path(config.repo_root, output)
    if output_path.exists() and not force:
        payload = dict(payload)
        payload["accepted_for_review"] = False
        payload["blocked"] = True
        payload["blocked_reasons"] = sorted({*payload.get("blocked_reasons", []), "Output file already exists. Re-run with --force to overwrite."})
        rendered = json.dumps(payload, indent=2) if output_format == "json" else _render_markdown(payload)
        ok = False
    else:
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(rendered.rstrip() + "\n", encoding="utf-8")
        except OSError as exc:
            return _error("output_write_failed", {"path": str(output_path), "message": str(exc)}, payload=payload)
    return {
        "command": COMMAND_NAME,
        "ok": ok,
        "local_only": True,
        "format": output_format,
        "output": str(output_path),
        "force": force,
        "wrote_output_file": ok,
        "stdout": rendered,
        "payload": payload,
    }


def _render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Patch Proposal Intake",
        "",
        f"- intake_record_type: {payload.get('intake_record_type', '')}",
        f"- accepted_for_review: {payload.get('accepted_for_review')}",
        f"- blocked: {payload.get('blocked')}",
        f"- item_id: {payload.get('item_id', '')}",
        f"- title: {payload.get('title', '')}",
        f"- patch_artifact_path: {payload.get('patch_artifact_path', '')}",
        f"- patch_artifact_exists: {payload.get('patch_artifact_exists')}",
        f"- approval_gate_id: {payload.get('approval_gate_id', '') or '-'}",
        f"- approval_status: {payload.get('approval_status', '')}",
        f"- operator_review_required: {payload.get('operator_review_required')}",
        f"- patch_application_allowed: {payload.get('patch_application_allowed')}",
        f"- patch_application_performed: {payload.get('patch_application_performed')}",
        f"- local_only: {payload.get('local_only')}",
        f"- execution_allowed: {payload.get('execution_allowed')}",
        f"- next_safe_action: {payload.get('next_safe_action', '')}",
    ]
    blockers = payload.get("blocked_reasons", []) if isinstance(payload.get("blocked_reasons"), list) else []
    if blockers:
        lines.extend(["", "## Blocked Reasons"])
        lines.extend(f"- {reason}" for reason in blockers)
    summary = payload.get("patch_summary", {}) if isinstance(payload.get("patch_summary"), dict) else {}
    lines.extend(
        [
            "",
            "## Patch Summary",
            f"- format: {summary.get('format', '')}",
            f"- line_count: {summary.get('line_count', 0)}",
            f"- files_touched: {', '.join(summary.get('files_touched', [])) if isinstance(summary.get('files_touched'), list) else ''}",
            f"- additions: {summary.get('additions', 0)}",
            f"- deletions: {summary.get('deletions', 0)}",
        ]
    )
    return "\n".join(lines).rstrip()


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _error(error: str, details: dict[str, Any], payload: dict[str, Any] | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "command": COMMAND_NAME,
        "ok": False,
        "local_only": True,
        "error": error,
        "details": details,
    }
    if payload is not None:
        result["payload"] = payload
    return result
