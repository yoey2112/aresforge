from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.codex_prompt_dispatch_artifact import CODEX_PROMPT_LANE
from aresforge.operator.dispatch_approval_gate import resolve_dispatch_approval_gate_path
from aresforge.operator.dispatch_artifact_report import inspect_dispatch_artifacts
from aresforge.operator.local_project_queue import resolve_project_queue_path
from aresforge.operator.queue_agent_dispatch_plan import build_queue_agent_dispatch_plan

MANUAL_CODEX_DISPATCH_RUNNER_VERSION = "m109.1"
COMMAND_NAME = "prepare-manual-codex-dispatch"
APPROVED_STATUS = "approved_for_manual_handoff"

_UNSAFE_QUEUE_STATUSES = {
    "done",
    "blocked",
    "cancelled",
    "canceled",
    "closed",
    "archived",
}

_MANUAL_DISPATCH_STEPS = (
    "Inspect the queue item and confirm it is still the intended manual Codex target.",
    "Review the M97 dispatch plan and confirm selected_lane is codex_prompt_artifact.",
    "Open the M98 Codex prompt artifact from codex_artifact_path.",
    "Confirm the M101 approval gate status is approved_for_manual_handoff.",
    "Manually copy the prompt artifact into Codex outside AresForge.",
    "After the manual Codex run, collect returned files, validation output, warnings, and any patch proposal as evidence.",
    "Do not apply returned patches until a later approval-gated patch intake contract authorizes that workflow.",
)

_OPERATOR_CHECKLIST = (
    "Queue item is not done, blocked, or lifecycle-unsafe.",
    "Dispatch plan local_only is true.",
    "Dispatch plan execution_allowed is false.",
    "Selected lane is codex_prompt_artifact.",
    "Codex prompt artifact exists locally.",
    "Approval gate is approved_for_manual_handoff.",
    "AresForge did not execute Codex or shell out to Codex CLI.",
    "AresForge did not apply patches or mutate source files.",
)

_EVIDENCE_EXPECTED = (
    "manual Codex run transcript or summary",
    "files Codex proposed to change",
    "patch/diff artifact if Codex produced one",
    "validation commands Codex ran or recommended",
    "operator notes about accepted, rejected, or deferred changes",
    "approval-gated patch intake evidence for M111 or later",
)


def prepare_manual_codex_dispatch(
    config: AppConfig,
    *,
    item_id: str,
    artifact_path: str | Path | None = None,
    approval_id: str | None = None,
    queue_path: str | Path | None = None,
    registry_path: str | Path | None = None,
    artifact_root: str | Path | None = None,
    approval_path: str | Path | None = None,
    output: str | Path | None = None,
    force: bool = False,
    output_format: str = "markdown",
    dispatch_plan: dict[str, Any] | None = None,
    artifact_index: dict[str, Any] | None = None,
) -> dict[str, Any]:
    fmt = str(output_format or "markdown").lower().strip()
    if fmt not in {"markdown", "json"}:
        return _error("invalid_format", {"format": output_format, "supported_formats": ["markdown", "json"]})

    normalized_item_id = str(item_id or "").strip()
    plan = dispatch_plan or build_queue_agent_dispatch_plan(
        config,
        item_id=normalized_item_id,
        queue_path=queue_path,
        registry_path=registry_path,
    )
    item = _load_queue_item(config, item_id=normalized_item_id, queue_path=queue_path)
    index_payload = artifact_index or inspect_dispatch_artifacts(
        config,
        project_id=str(plan.get("project_id") or item.get("project_id") or "aresforge"),
        artifact_root=artifact_root,
        approval_path=approval_path,
        output_format="json",
    )["payload"]

    artifact = _select_artifact(
        config=config,
        artifact_path=artifact_path,
        item_id=normalized_item_id,
        artifact_index=index_payload,
    )
    gate = _select_approval_gate(
        config=config,
        approval_id=approval_id,
        approval_path=approval_path,
        item_id=normalized_item_id,
        artifact=artifact,
    )
    blocked_reasons = _blocked_reasons(item=item, plan=plan, artifact=artifact, gate=gate)
    blocked = bool(blocked_reasons)
    prepared = not blocked

    approval_status = str(gate.get("status", "")).strip() if gate else "missing"
    payload: dict[str, Any] = {
        "manual_codex_dispatch_runner_version": MANUAL_CODEX_DISPATCH_RUNNER_VERSION,
        "repo_path": str(config.repo_root),
        "prepared": prepared,
        "blocked": blocked,
        "blocked_reasons": blocked_reasons,
        "item_id": normalized_item_id,
        "title": str(item.get("title") or plan.get("title") or "").strip(),
        "project_id": str(item.get("project_id") or plan.get("project_id") or "").strip(),
        "milestone": str(plan.get("milestone") or _milestone(item)).strip(),
        "queue_status": str(item.get("status") or plan.get("status") or "").strip(),
        "selected_lane": str(plan.get("selected_lane", "")).strip(),
        "codex_artifact_path": str(artifact.get("file_path", "")).strip(),
        "approval_gate_id": str(gate.get("approval_id", "")).strip() if gate else "",
        "approval_status": approval_status,
        "manual_dispatch_steps": list(_MANUAL_DISPATCH_STEPS),
        "operator_checklist": list(_OPERATOR_CHECKLIST),
        "evidence_expected_after_manual_run": list(_EVIDENCE_EXPECTED),
        "local_only": True,
        "execution_allowed": False,
        "codex_execution_performed": False,
        "next_safe_action": _next_safe_action(prepared=prepared, blocked_reasons=blocked_reasons),
        "source_contracts": {
            "dispatch_plan_version": str(plan.get("dispatch_plan_version", "")).strip(),
            "artifact_report_version": str(index_payload.get("dispatch_artifact_report_version", "")).strip(),
            "approval_gate_status_required": APPROVED_STATUS,
        },
        "safety_boundary": {
            "executes_codex": False,
            "shells_out_to_codex_cli": False,
            "invokes_local_llm": False,
            "uses_github_api": False,
            "uses_gh": False,
            "uses_network_services": False,
            "applies_patches": False,
            "mutates_queue": False,
            "codex_execution_performed": False,
            "execution_allowed": False,
        },
    }
    return _emit_or_write(payload, output=output, force=force, output_format=fmt)


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


def _select_artifact(
    *,
    config: AppConfig,
    artifact_path: str | Path | None,
    item_id: str,
    artifact_index: dict[str, Any],
) -> dict[str, Any]:
    artifacts = artifact_index.get("artifacts", []) if isinstance(artifact_index.get("artifacts"), list) else []
    if artifact_path is not None:
        path = Path(artifact_path)
        if not path.is_absolute():
            path = (config.repo_root / path).resolve()
        else:
            path = path.resolve()
        for artifact in artifacts:
            if isinstance(artifact, dict) and str(artifact.get("file_path", "")).strip() == str(path):
                return dict(artifact)
        return {
            "artifact_type": "codex_prompt_dispatch",
            "item_id": item_id,
            "dispatch_lane": CODEX_PROMPT_LANE,
            "file_path": str(path),
            "approval_gate_status": "missing",
            "approval_id": "",
            "local_only": True,
            "execution_allowed": False,
            "exists": path.exists(),
        }
    matches = [
        artifact
        for artifact in artifacts
        if isinstance(artifact, dict)
        and str(artifact.get("item_id", "")).strip() == item_id
        and str(artifact.get("dispatch_lane", "")).strip() == CODEX_PROMPT_LANE
    ]
    if not matches:
        return {}
    return dict(sorted(matches, key=lambda artifact: str(artifact.get("modified_at", "")))[-1])


def _select_approval_gate(
    *,
    config: AppConfig,
    approval_id: str | None,
    approval_path: str | Path | None,
    item_id: str,
    artifact: dict[str, Any],
) -> dict[str, Any]:
    gates = _load_approval_gates(resolve_dispatch_approval_gate_path(config.repo_root, approval_path))
    requested_id = str(approval_id or "").strip()
    if requested_id:
        return next((dict(gate) for gate in gates if str(gate.get("approval_id", "")).strip() == requested_id), {})
    artifact_approval_id = str(artifact.get("approval_id", "")).strip()
    if artifact_approval_id:
        match = next((dict(gate) for gate in gates if str(gate.get("approval_id", "")).strip() == artifact_approval_id), {})
        if match:
            return match
    artifact_path = str(artifact.get("file_path", "")).strip()
    candidates = [
        gate
        for gate in gates
        if str(gate.get("item_id", "")).strip() == item_id
        and str(gate.get("dispatch_lane", "")).strip() in {"", CODEX_PROMPT_LANE}
        and str(gate.get("artifact_type", "")).strip() in {"codex_prompt_artifact", "codex_prompt_dispatch", ""}
    ]
    path_matches = [gate for gate in candidates if artifact_path and str(gate.get("artifact_path", "")).strip() == artifact_path]
    candidates = path_matches or candidates
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


def _blocked_reasons(*, item: dict[str, Any], plan: dict[str, Any], artifact: dict[str, Any], gate: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    if not item:
        reasons.append("Queue item was not found.")
    status = str(item.get("status") or plan.get("status") or "").strip()
    if status in _UNSAFE_QUEUE_STATUSES:
        reasons.append(f"Queue item status is {status}; manual Codex dispatch preparation is lifecycle-blocked.")
    if item.get("blocked_by"):
        reasons.append("Queue item has blocked_by references and requires manual blocker review.")
    plan_blockers = plan.get("blocked_reasons", []) if isinstance(plan.get("blocked_reasons"), list) else []
    reasons.extend(str(reason).strip() for reason in plan_blockers if str(reason).strip())
    if bool(plan.get("blocked", False)):
        reasons.append("M97 dispatch plan is blocked.")
    if str(plan.get("selected_lane", "")).strip() != CODEX_PROMPT_LANE:
        reasons.append("Selected lane must be codex_prompt_artifact for manual Codex dispatch preparation.")
    if plan.get("local_only") is not True:
        reasons.append("Source dispatch plan local_only must be true.")
    if plan.get("execution_allowed") is not False:
        reasons.append("Source dispatch plan execution_allowed must be false.")
    artifact_path = str(artifact.get("file_path", "")).strip()
    if not artifact_path:
        reasons.append("Codex prompt artifact is missing.")
    elif not Path(artifact_path).exists():
        reasons.append(f"Codex prompt artifact is missing: {artifact_path}")
    if artifact and artifact.get("local_only") is not True:
        reasons.append("Source Codex prompt artifact local_only must be true.")
    if artifact and artifact.get("execution_allowed") is not False:
        reasons.append("Source Codex prompt artifact execution_allowed must be false.")
    if not gate:
        reasons.append("Approval gate is missing; status needs_approval before manual handoff.")
    elif str(gate.get("status", "")).strip() != APPROVED_STATUS:
        reasons.append(f"Approval gate status is {str(gate.get('status', '')).strip() or '<missing>'}; required {APPROVED_STATUS}.")
    if gate and gate.get("local_only", True) is not True:
        reasons.append("Approval gate local_only must be true.")
    if gate and gate.get("execution_allowed", False) is not False:
        reasons.append("Approval gate execution_allowed must be false.")
    return sorted({reason for reason in reasons if reason})


def _milestone(item: dict[str, Any]) -> str:
    tags = item.get("tags", []) if isinstance(item.get("tags"), list) else []
    for tag in tags:
        text = str(tag).strip()
        if text.startswith("milestone:"):
            return text.split(":", 1)[1].split(",", 1)[0].strip()
    item_id = str(item.get("item_id", "")).strip()
    return item_id.split("-", 1)[0].upper() if item_id.lower().startswith("m") and "-" in item_id else ""


def _next_safe_action(*, prepared: bool, blocked_reasons: list[str]) -> str:
    if prepared:
        return "Operator may manually run the Codex prompt outside AresForge, then record returned evidence; automated execution remains blocked."
    if any("Approval gate is missing" in reason for reason in blocked_reasons):
        return "Create or approve an M101 dispatch approval gate before preparing manual Codex dispatch."
    if any("Codex prompt artifact is missing" in reason for reason in blocked_reasons):
        return "Generate or locate the M98 Codex prompt artifact before manual dispatch preparation."
    return "Resolve blocked reasons locally before any manual Codex handoff."


def _emit_or_write(payload: dict[str, Any], *, output: str | Path | None, force: bool, output_format: str) -> dict[str, Any]:
    rendered = json.dumps(payload, indent=2) if output_format == "json" else _render_markdown(payload)
    if output is None:
        return {
            "command": COMMAND_NAME,
            "ok": bool(payload.get("prepared")) and not bool(payload.get("blocked")),
            "local_only": True,
            "format": output_format,
            "wrote_output_file": False,
            "stdout": rendered,
            "payload": payload,
        }
    output_path = Path(output)
    if not output_path.is_absolute():
        repo_root = Path(str(payload.get("repo_path", "") or Path.cwd()))
        output_path = (repo_root / output_path).resolve()
    if output_path.exists() and not force:
        return _error("output_exists", {"path": str(output_path), "hint": "Re-run with --force to overwrite."}, payload=payload)
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered.rstrip() + "\n", encoding="utf-8")
    except OSError as exc:
        return _error("output_write_failed", {"path": str(output_path), "message": str(exc)}, payload=payload)
    return {
        "command": COMMAND_NAME,
        "ok": bool(payload.get("prepared")) and not bool(payload.get("blocked")),
        "local_only": True,
        "format": output_format,
        "output": str(output_path),
        "force": force,
        "wrote_output_file": True,
        "payload": payload,
    }


def _render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Manual Codex Dispatch Preparation",
        "",
        f"- prepared: {payload.get('prepared')}",
        f"- blocked: {payload.get('blocked')}",
        f"- item_id: {payload.get('item_id', '')}",
        f"- title: {payload.get('title', '')}",
        f"- queue_status: {payload.get('queue_status', '')}",
        f"- selected_lane: {payload.get('selected_lane', '')}",
        f"- codex_artifact_path: {payload.get('codex_artifact_path', '') or '-'}",
        f"- approval_status: {payload.get('approval_status', '') or '-'}",
        f"- local_only: {payload.get('local_only')}",
        f"- execution_allowed: {payload.get('execution_allowed')}",
        f"- codex_execution_performed: {payload.get('codex_execution_performed')}",
        f"- next_safe_action: {payload.get('next_safe_action', '')}",
    ]
    blocked_reasons = payload.get("blocked_reasons", []) if isinstance(payload.get("blocked_reasons"), list) else []
    if blocked_reasons:
        lines.extend(["", "## Blocked Reasons"])
        lines.extend(f"- {reason}" for reason in blocked_reasons)
    lines.extend(["", "## Manual Dispatch Steps"])
    lines.extend(f"- {step}" for step in payload.get("manual_dispatch_steps", []) if str(step).strip())
    lines.extend(["", "## Operator Checklist"])
    lines.extend(f"- {item}" for item in payload.get("operator_checklist", []) if str(item).strip())
    lines.extend(["", "## Evidence Expected After Manual Run"])
    lines.extend(f"- {item}" for item in payload.get("evidence_expected_after_manual_run", []) if str(item).strip())
    return "\n".join(lines).rstrip()


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


def default_manual_codex_dispatch_record_path(config: AppConfig, item_id: str) -> Path:
    return config.artifact_root / "manual_codex_dispatch" / "prepared" / f"{_slug(item_id)}.json"


def _slug(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", str(value or "").lower()).strip("-")
    return normalized or "manual-codex-dispatch"
