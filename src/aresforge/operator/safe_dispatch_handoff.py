from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.dispatch_approval_gate import resolve_dispatch_approval_gate_path
from aresforge.operator.dispatch_artifact_report import inspect_dispatch_artifacts
from aresforge.operator.local_project_queue import inspect_project_queue
from aresforge.operator.local_project_report import inspect_local_project_report
from aresforge.operator.queue_agent_dispatch_plan import build_queue_agent_dispatch_plan

SAFE_DISPATCH_HANDOFF_VERSION = "m107.1"
COMMAND_NAME = "generate-safe-dispatch-handoff"

_BOUNDARY_CONFIRMATIONS = (
    "M107 safe dispatch handoff generation is local-only.",
    "The handoff package is read-only by default; optional --output writes one local file only.",
    "The handoff package does not execute dispatch artifacts.",
    "The handoff package does not execute Codex.",
    "The handoff package does not invoke Ollama, local LLMs, documentation agents, or external agents.",
    "The handoff package does not call GitHub APIs, gh, or network services.",
    "The handoff package does not mutate queue state, approval gates, artifacts, or repository files except explicit output writes.",
    "The handoff package does not apply patches.",
    "execution_allowed=false is preserved.",
)

_MANUAL_APPROVAL_ACTIONS = (
    "Manual operator approval is required before using any dispatch artifact in another tool.",
    "Manual operator approval is required before preparing any handoff package for another chat or human reviewer.",
    "Manual operator approval is required before changing any dispatch approval gate status.",
    "Manual operator approval is required before starting, completing, or dispatching any queue item.",
    "M107 does not authorize automated execution after approval.",
)


def generate_safe_dispatch_handoff(
    config: AppConfig,
    *,
    project_id: str | None = None,
    queue_path: str | Path | None = None,
    registry_path: str | Path | None = None,
    artifact_root: str | Path | None = None,
    approval_path: str | Path | None = None,
    output: str | Path | None = None,
    force: bool = False,
    output_format: str = "markdown",
) -> dict[str, Any]:
    fmt = str(output_format or "markdown").lower().strip()
    if fmt not in {"markdown", "json"}:
        return _error("invalid_format", {"format": output_format, "supported_formats": ["markdown", "json"]})

    normalized_project_id = str(project_id or "aresforge").strip() or "aresforge"
    git_state = _collect_git_state(config.repo_root)
    project_report = inspect_local_project_report(config)
    queue_result = inspect_project_queue(config, queue_path=queue_path, project_id=normalized_project_id)
    queue_report = queue_result.get("payload", queue_result) if isinstance(queue_result.get("payload"), dict) else queue_result
    queue_items = queue_report.get("work_items", []) if isinstance(queue_report.get("work_items"), list) else []
    next_items = _next_recommended_items(queue_items)
    dispatch_plan_summaries = _dispatch_plan_summaries(
        config,
        queue_items=next_items,
        queue_path=queue_path,
        registry_path=registry_path,
    )
    artifact_report = inspect_dispatch_artifacts(
        config,
        project_id=normalized_project_id,
        artifact_root=artifact_root,
        approval_path=approval_path,
        output_format="json",
    )["payload"]
    approval_summary = _approval_gate_summary(config.repo_root, approval_path)
    warnings = sorted(
        {
            *[str(warning) for warning in git_state.get("warnings", []) if str(warning).strip()],
            *[str(warning) for warning in queue_report.get("warnings", []) if str(warning).strip()],
            *[str(warning) for warning in project_report.get("warnings", []) if str(warning).strip()],
            *[str(warning) for warning in artifact_report.get("warnings", []) if str(warning).strip()],
            *[str(warning) for warning in approval_summary.get("warnings", []) if str(warning).strip()],
        }
    )
    blockers = sorted(
        {
            *[str(blocker) for blocker in project_report.get("blockers", []) if str(blocker).strip()],
            *[str(blocker) for blocker in queue_report.get("blockers", []) if str(blocker).strip()],
            *[
                str(reason)
                for plan in dispatch_plan_summaries
                for reason in plan.get("blocked_reasons", [])
                if str(reason).strip()
            ],
        }
    )

    payload: dict[str, Any] = {
        "ok": True,
        "handoff_type": "safe_dispatch_handoff",
        "safe_dispatch_handoff_version": SAFE_DISPATCH_HANDOFF_VERSION,
        "generated_at": datetime.now(UTC).isoformat(),
        "repo_path": str(config.repo_root),
        "branch": git_state["branch"],
        "head": git_state["head"],
        "active_project": project_report.get("active_project", {}),
        "project_id": normalized_project_id,
        "queue_summary": _queue_summary(queue_report),
        "next_recommended_items": next_items,
        "dispatch_plan_summaries": dispatch_plan_summaries,
        "artifact_index_summary": _artifact_index_summary(artifact_report),
        "approval_gate_summary": approval_summary,
        "warnings": warnings,
        "blockers": blockers,
        "local_only": True,
        "read_only_by_default": True,
        "execution_allowed": False,
        "manual_approval_required_for": list(_MANUAL_APPROVAL_ACTIONS),
        "operator_next_actions": _operator_next_actions(artifact_report, approval_summary, blockers),
        "safety_boundary": {
            "local_only": True,
            "read_only_by_default": True,
            "writes_files_by_default": False,
            "explicit_output_write_only": True,
            "executes_dispatch_artifacts": False,
            "executes_codex": False,
            "invokes_local_llm": False,
            "executes_documentation_agent": False,
            "uses_github_api": False,
            "uses_gh": False,
            "uses_network_services": False,
            "applies_patches": False,
            "mutates_queue": False,
            "mutates_approval_gates": False,
            "auto_handoff_allowed": False,
            "auto_starts_next_item": False,
            "auto_completes_queue_items": False,
        },
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }
    return _emit_or_write(payload, output=output, force=force, output_format=fmt)


def _collect_git_state(repo_root: Path) -> dict[str, Any]:
    commands = {
        "branch": ["git", "branch", "--show-current"],
        "head": ["git", "rev-parse", "HEAD"],
    }
    result: dict[str, Any] = {"branch": "unknown", "head": "unknown", "warnings": []}
    for key, command in commands.items():
        try:
            completed = subprocess.run(command, cwd=repo_root, check=False, capture_output=True, text=True)
        except OSError as exc:
            result["warnings"].append(f"{' '.join(command)}: {exc}")
            continue
        if completed.returncode != 0:
            result["warnings"].append(f"{' '.join(command)}: {(completed.stderr or '').strip() or completed.returncode}")
            continue
        result[key] = (completed.stdout or "").strip() or "unknown"
    return result


def _next_recommended_items(queue_items: list[Any]) -> list[dict[str, Any]]:
    priority_rank = {"urgent": 0, "high": 1, "normal": 2, "low": 3}
    candidates = [
        item
        for item in queue_items
        if isinstance(item, dict) and str(item.get("status", "")).strip() in {"in_progress", "ready", "proposed", "blocked"}
    ]
    sorted_items = sorted(
        candidates,
        key=lambda item: (
            {"in_progress": 0, "ready": 1, "proposed": 2, "blocked": 3}.get(str(item.get("status", "")), 9),
            priority_rank.get(str(item.get("priority", "")), 9),
            str(item.get("created_at", "")),
        ),
    )
    return [_queue_item_summary(item) for item in sorted_items[:8]]


def _queue_item_summary(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "item_id": str(item.get("item_id", "")).strip(),
        "title": str(item.get("title", "")).strip(),
        "status": str(item.get("status", "")).strip(),
        "priority": str(item.get("priority", "")).strip(),
        "item_type": str(item.get("item_type", "")).strip(),
        "project_id": str(item.get("project_id", "")).strip(),
        "repo_id": str(item.get("repo_id", "")).strip(),
        "dependencies": list(item.get("dependencies", [])) if isinstance(item.get("dependencies"), list) else [],
        "blocked_by": list(item.get("blocked_by", [])) if isinstance(item.get("blocked_by"), list) else [],
    }


def _dispatch_plan_summaries(
    config: AppConfig,
    *,
    queue_items: list[dict[str, Any]],
    queue_path: str | Path | None,
    registry_path: str | Path | None,
) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for item in queue_items:
        item_id = str(item.get("item_id", "")).strip()
        if not item_id:
            continue
        try:
            plan = build_queue_agent_dispatch_plan(config, item_id=item_id, queue_path=queue_path, registry_path=registry_path)
        except Exception as exc:  # Defensive report-only fallback.
            summaries.append(
                {
                    "item_id": item_id,
                    "ok": False,
                    "blocked": True,
                    "blocked_reasons": [f"Dispatch plan could not be built: {exc}"],
                    "selected_lane": "",
                    "confidence": {},
                    "local_only": True,
                    "execution_allowed": False,
                    "next_safe_action": "Inspect the queue item and dispatch plan inputs locally before handoff.",
                }
            )
            continue
        confidence = plan.get("routing_confidence", {}) if isinstance(plan.get("routing_confidence"), dict) else {}
        summaries.append(
            {
                "item_id": item_id,
                "title": str(plan.get("title", "")).strip(),
                "status": str(plan.get("status", "")).strip(),
                "selected_lane": str(plan.get("selected_lane", "")).strip(),
                "selection_reason": str(plan.get("lane_selection_reason", "")).strip(),
                "confidence": {
                    "score": confidence.get("score", 0),
                    "level": str(confidence.get("level", "")).strip(),
                },
                "blocked": bool(plan.get("blocked", False)),
                "blocked_reasons": list(plan.get("blocked_reasons", [])) if isinstance(plan.get("blocked_reasons"), list) else [],
                "local_only": True,
                "execution_allowed": False,
                "next_safe_action": str(plan.get("next_safe_action", "")).strip(),
            }
        )
    return summaries


def _queue_summary(queue_report: dict[str, Any]) -> dict[str, Any]:
    items = queue_report.get("work_items", []) if isinstance(queue_report.get("work_items"), list) else []
    status_counts: dict[str, int] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        status = str(item.get("status", "unknown")).strip() or "unknown"
        status_counts[status] = status_counts.get(status, 0) + 1
    return {
        "queue_path": str(queue_report.get("queue_path", "")),
        "item_count": len(items),
        "status_counts": dict(sorted(status_counts.items())),
        "filters": queue_report.get("filters", {}),
        "local_only": True,
    }


def _artifact_index_summary(artifact_report: dict[str, Any]) -> dict[str, Any]:
    artifacts = artifact_report.get("artifacts", []) if isinstance(artifact_report.get("artifacts"), list) else []
    by_type: dict[str, int] = {}
    by_approval: dict[str, int] = {}
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            continue
        artifact_type = str(artifact.get("artifact_type", "unknown")).strip() or "unknown"
        approval = str(artifact.get("approval_gate_status", "unknown")).strip() or "unknown"
        by_type[artifact_type] = by_type.get(artifact_type, 0) + 1
        by_approval[approval] = by_approval.get(approval, 0) + 1
    return {
        "report_type": artifact_report.get("report_type", "dispatch_artifact_index"),
        "artifact_count": len(artifacts),
        "by_artifact_type": dict(sorted(by_type.items())),
        "by_approval_gate_status": dict(sorted(by_approval.items())),
        "missing_locations": list(artifact_report.get("missing_locations", []))
        if isinstance(artifact_report.get("missing_locations"), list)
        else [],
        "artifacts": artifacts,
        "local_only": True,
        "execution_allowed": False,
        "next_safe_action": str(artifact_report.get("next_safe_action", "")).strip(),
    }


def _approval_gate_summary(repo_root: Path, approval_path: str | Path | None) -> dict[str, Any]:
    path = resolve_dispatch_approval_gate_path(repo_root, approval_path)
    if not path.exists():
        return {
            "approval_path": str(path),
            "approval_gate_count": 0,
            "status_counts": {},
            "approval_gates": [],
            "warnings": [],
            "local_only": True,
            "execution_allowed": False,
        }
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "approval_path": str(path),
            "approval_gate_count": 0,
            "status_counts": {},
            "approval_gates": [],
            "warnings": [f"Dispatch approval gate file could not be read: {exc}"],
            "local_only": True,
            "execution_allowed": False,
        }
    gates = raw.get("approval_gates", []) if isinstance(raw, dict) else []
    gates = [gate for gate in gates if isinstance(gate, dict)]
    status_counts: dict[str, int] = {}
    summaries = []
    for gate in gates:
        status = str(gate.get("status", "unknown")).strip() or "unknown"
        status_counts[status] = status_counts.get(status, 0) + 1
        summaries.append(
            {
                "approval_id": str(gate.get("approval_id", "")).strip(),
                "item_id": str(gate.get("item_id", "")).strip(),
                "artifact_type": str(gate.get("artifact_type", "")).strip(),
                "dispatch_lane": str(gate.get("dispatch_lane", "")).strip(),
                "status": status,
                "local_only": True,
                "execution_allowed": False,
                "next_safe_action": str(gate.get("next_safe_action", "")).strip(),
            }
        )
    return {
        "approval_path": str(path),
        "approval_gate_count": len(summaries),
        "status_counts": dict(sorted(status_counts.items())),
        "approval_gates": summaries,
        "warnings": [],
        "local_only": True,
        "execution_allowed": False,
    }


def _operator_next_actions(
    artifact_report: dict[str, Any],
    approval_summary: dict[str, Any],
    blockers: list[str],
) -> list[str]:
    actions = [
        "Review this safe dispatch handoff package as local-only context.",
        "Inspect each dispatch plan summary before deciding whether an artifact or dry-run belongs in a new chat handoff.",
        "Confirm manual approval gates before copying any artifact content into another tool or chat.",
        "Keep execution_allowed=false; do not run Codex, local LLMs, documentation agents, GitHub commands, or patches from this handoff.",
    ]
    if blockers:
        actions.insert(1, "Resolve listed blockers before preparing any manual dispatch handoff.")
    if int(artifact_report.get("artifact_count", 0)) == 0:
        actions.append("No dispatch artifacts were found; generate artifacts or dry-runs with existing local-only commands if the operator needs handoff material.")
    if int(approval_summary.get("approval_gate_count", 0)) == 0:
        actions.append("No approval gates were found for dispatch artifacts; create M101 approval gates before manual handoff.")
    return actions


def _emit_or_write(payload: dict[str, Any], *, output: str | Path | None, force: bool, output_format: str) -> dict[str, Any]:
    markdown = _render_markdown(payload)
    rendered = json.dumps(payload, indent=2) if output_format == "json" else markdown
    if output is None:
        return {
            "command": COMMAND_NAME,
            "ok": True,
            "local_only": True,
            "format": output_format,
            "wrote_output_file": False,
            "stdout": rendered,
            "payload": payload,
        }
    output_path = Path(output)
    if not output_path.is_absolute():
        output_path = Path(payload["repo_path"]) / output_path
    output_path = output_path.resolve()
    if output_path.exists() and not force:
        return _error("output_exists", {"path": str(output_path), "hint": "Re-run with --force to overwrite."}, payload=payload)
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered.rstrip() + "\n", encoding="utf-8")
    except OSError as exc:
        return _error("output_write_failed", {"path": str(output_path), "message": str(exc)}, payload=payload)
    return {
        "command": COMMAND_NAME,
        "ok": True,
        "local_only": True,
        "format": output_format,
        "output": str(output_path),
        "force": force,
        "wrote_output_file": True,
        "safe_dispatch_handoff_version": payload["safe_dispatch_handoff_version"],
        "warnings": payload["warnings"],
        "blockers": payload["blockers"],
        "safety_boundary": payload["safety_boundary"],
        "operator_next_actions": payload["operator_next_actions"],
        "boundary_confirmations": payload["boundary_confirmations"],
    }


def _render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Safe Dispatch Handoff Package",
        "",
        f"- safe_dispatch_handoff_version: {payload.get('safe_dispatch_handoff_version')}",
        f"- generated_at: {payload.get('generated_at')}",
        f"- repo_path: {payload.get('repo_path')}",
        f"- branch: {payload.get('branch')}",
        f"- head: {payload.get('head')}",
        f"- project_id: {payload.get('project_id')}",
        f"- local_only: {payload.get('local_only')}",
        f"- read_only_by_default: {payload.get('read_only_by_default')}",
        f"- execution_allowed: {payload.get('execution_allowed')}",
        "",
        "## Queue Summary",
    ]
    queue = payload.get("queue_summary", {}) if isinstance(payload.get("queue_summary"), dict) else {}
    lines.append(f"- item_count: {queue.get('item_count', 0)}")
    status_counts = queue.get("status_counts", {}) if isinstance(queue.get("status_counts"), dict) else {}
    for status, count in status_counts.items():
        lines.append(f"- {status}: {count}")

    lines.extend(["", "## Next Recommended Items"])
    next_items = payload.get("next_recommended_items", []) if isinstance(payload.get("next_recommended_items"), list) else []
    if next_items:
        lines.extend(f"- {item.get('item_id')} ({item.get('status')}): {item.get('title')}" for item in next_items)
    else:
        lines.append("- none")

    lines.extend(["", "## Dispatch Plan Summaries"])
    plans = payload.get("dispatch_plan_summaries", []) if isinstance(payload.get("dispatch_plan_summaries"), list) else []
    if plans:
        lines.extend(
            (
                f"- {plan.get('item_id')} | lane={plan.get('selected_lane')} | "
                f"blocked={plan.get('blocked')} | execution_allowed={plan.get('execution_allowed')}"
            )
            for plan in plans
        )
    else:
        lines.append("- none")

    artifact_summary = payload.get("artifact_index_summary", {}) if isinstance(payload.get("artifact_index_summary"), dict) else {}
    lines.extend(
        [
            "",
            "## Artifact Index Summary",
            f"- artifact_count: {artifact_summary.get('artifact_count', 0)}",
            f"- next_safe_action: {artifact_summary.get('next_safe_action', '')}",
        ]
    )

    approval = payload.get("approval_gate_summary", {}) if isinstance(payload.get("approval_gate_summary"), dict) else {}
    lines.extend(["", "## Approval Gate Summary", f"- approval_gate_count: {approval.get('approval_gate_count', 0)}"])
    approval_status_counts = approval.get("status_counts", {}) if isinstance(approval.get("status_counts"), dict) else {}
    for status, count in approval_status_counts.items():
        lines.append(f"- {status}: {count}")

    lines.extend(["", "## Manual Approval Required For"])
    lines.extend(f"- {item}" for item in payload.get("manual_approval_required_for", []))

    lines.extend(["", "## Operator Next Actions"])
    lines.extend(f"- {item}" for item in payload.get("operator_next_actions", []))

    lines.extend(["", "## Safety Boundary"])
    safety = payload.get("safety_boundary", {}) if isinstance(payload.get("safety_boundary"), dict) else {}
    for key in sorted(safety.keys()):
        lines.append(f"- {key}: {safety.get(key)}")

    blockers = payload.get("blockers", []) if isinstance(payload.get("blockers"), list) else []
    if blockers:
        lines.extend(["", "## Blockers"])
        lines.extend(f"- {item}" for item in blockers)
    warnings = payload.get("warnings", []) if isinstance(payload.get("warnings"), list) else []
    if warnings:
        lines.extend(["", "## Warnings"])
        lines.extend(f"- {item}" for item in warnings)
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
