from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
import json
import re
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.dispatch_approval_gate import (
    resolve_dispatch_approval_gate_path,
)
from aresforge.operator.dispatch_artifact_registry import inspect_artifact_registry
from aresforge.operator.local_project_queue import resolve_project_queue_path
from aresforge.operator.operator_batch_planner import plan_operator_batch

COMMAND_NAME = "plan-operator-batch-v2"
PLAN_TYPE = "operator_batch_sequence_v2"
PLAN_VERSION = "m120.1"

_PLANNABLE_STATUSES = {"proposed", "ready"}
_PRIORITY_RANK = {"urgent": 0, "high": 1, "normal": 2, "low": 3}

_BOUNDARY_CONFIRMATIONS = (
    "M120 operator batch queue sequencing is local-only.",
    "M120 reads local queue, local artifact registry, and local approval gate metadata only.",
    "M120 does not start queue items.",
    "M120 does not execute agents, Codex, Ollama, local LLMs, remote LLMs, GitHub, gh, network services, validation commands, or patches.",
    "M120 does not mutate queue state or external systems.",
    "execution_allowed=false is preserved for the plan payload.",
)

_OPERATOR_CHECKLIST = (
    "Review dependency_warnings before starting any item.",
    "Review approval_warnings and create or update approval gates before manual handoff.",
    "Review artifact_warnings and generate missing advisory artifacts where required.",
    "Start at most one queue item using a separate explicit operator command.",
    "Do not treat this recommendation as execution approval.",
)


def plan_operator_batch_v2(
    config: AppConfig,
    *,
    project_id: str,
    limit: int = 10,
    include_blocked: bool = False,
    output: str | Path | None = None,
    force: bool = False,
    output_format: str = "markdown",
    queue_path: str | Path | None = None,
    registry_path: str | Path | None = None,
    approval_path: str | Path | None = None,
) -> dict[str, Any]:
    fmt = str(output_format or "markdown").strip().lower()
    if fmt not in {"json", "markdown"}:
        return _error("invalid_format", {"format": output_format, "supported_formats": ["json", "markdown"]})

    normalized_project_id = str(project_id or "").strip()
    if not normalized_project_id:
        return _error("invalid_project_id", {"message": "project_id is required."})

    normalized_limit = max(1, min(int(limit or 10), 100))
    resolved_queue_path = resolve_project_queue_path(config.repo_root, queue_path)
    queue_loaded = _load_queue(resolved_queue_path)
    if not queue_loaded["ok"]:
        return _error("queue_unreadable", queue_loaded)

    items = [
        item
        for item in queue_loaded["items"]
        if str(item.get("project_id", "")).strip() == normalized_project_id
    ]
    status_by_id = {
        str(item.get("item_id", "")).strip(): str(item.get("status", "")).strip()
        for item in queue_loaded["items"]
        if str(item.get("item_id", "")).strip()
    }
    artifact_index = _artifact_index(config, project_id=normalized_project_id)
    approvals = _approval_index(config, approval_path=approval_path)
    base_plan = plan_operator_batch(
        config,
        project_id=normalized_project_id,
        queue_path=resolved_queue_path,
        registry_path=registry_path,
        limit=normalized_limit,
        output_format="json",
    )
    base_payload = _base_payload(base_plan)

    candidates = [
        item
        for item in items
        if str(item.get("status", "")).strip() in _PLANNABLE_STATUSES
        or (include_blocked and str(item.get("status", "")).strip() == "blocked")
    ]
    ordered_candidates = sorted(candidates, key=_candidate_sort_key)

    dependency_warnings: list[dict[str, Any]] = []
    approval_warnings: list[dict[str, Any]] = []
    artifact_warnings: list[dict[str, Any]] = []
    blocked_entries: list[dict[str, Any]] = []
    sequence: list[dict[str, Any]] = []
    sequenced_ids: set[str] = set()
    pending = list(ordered_candidates)

    while pending and len(sequence) < normalized_limit:
        progressed = False
        for item in list(pending):
            if str(item.get("status", "")).strip() == "blocked":
                continue
            item_id = _item_id(item)
            blockers = _dependency_blockers(item, status_by_id=status_by_id, sequenced_ids=sequenced_ids)
            if blockers:
                continue
            pending.remove(item)
            entry = _sequence_entry(
                item,
                sequence=len(sequence) + 1,
                artifacts=artifact_index.get(item_id, []),
                approvals=approvals.get(item_id, []),
            )
            sequence.append(entry)
            sequenced_ids.add(item_id)
            _append_review_warnings(entry, approval_warnings=approval_warnings, artifact_warnings=artifact_warnings)
            progressed = True
            if len(sequence) >= normalized_limit:
                break
        if not progressed:
            break

    for item in pending:
        item_id = _item_id(item)
        reasons = _dependency_blockers(item, status_by_id=status_by_id, sequenced_ids=sequenced_ids)
        if str(item.get("status", "")).strip() == "blocked":
            reasons.append("Queue item status is blocked.")
        if not reasons:
            reasons.append("Item was not sequenced before the limit or ordering pass completed.")
        warning = {
            "item_id": item_id,
            "title": str(item.get("title", "")).strip(),
            "status": str(item.get("status", "")).strip(),
            "reasons": sorted({reason for reason in reasons if reason}),
        }
        dependency_warnings.append(warning)
        blocked_entries.append(warning)

    if include_blocked and len(sequence) < normalized_limit:
        for warning in blocked_entries:
            if len(sequence) >= normalized_limit:
                break
            if any(entry["item_id"] == warning["item_id"] for entry in sequence):
                continue
            item = next((candidate for candidate in ordered_candidates if _item_id(candidate) == warning["item_id"]), {})
            entry = _sequence_entry(
                item,
                sequence=None,
                artifacts=artifact_index.get(warning["item_id"], []),
                approvals=approvals.get(warning["item_id"], []),
                blocked=True,
                blocked_reasons=warning["reasons"],
            )
            sequence.append(entry)
            _append_review_warnings(entry, approval_warnings=approval_warnings, artifact_warnings=artifact_warnings)

    lane_grouping = _lane_grouping(sequence)
    payload: dict[str, Any] = {
        "ok": True,
        "plan_type": PLAN_TYPE,
        "plan_version": PLAN_VERSION,
        "project_id": normalized_project_id,
        "generated": True,
        "generated_at": _now_iso(),
        "queue_path": str(resolved_queue_path),
        "limit": normalized_limit,
        "include_blocked": bool(include_blocked),
        "proposed_count": sum(1 for item in items if str(item.get("status", "")).strip() in _PLANNABLE_STATUSES),
        "blocked_count": len(blocked_entries) + sum(1 for item in items if str(item.get("status", "")).strip() == "blocked"),
        "recommended_sequence": sequence,
        "blocked_items": blocked_entries,
        "dependency_warnings": _dedupe_records(dependency_warnings),
        "approval_warnings": _dedupe_records(approval_warnings),
        "artifact_warnings": _dedupe_records(artifact_warnings),
        "lane_grouping": lane_grouping,
        "operator_checklist": list(_OPERATOR_CHECKLIST),
        "base_planner_summary": {
            "planner_version": str(base_payload.get("planner_version", "")),
            "proposed_count": len(base_payload.get("proposed_items", [])) if isinstance(base_payload.get("proposed_items"), list) else 0,
            "blocked_count": len(base_payload.get("blocked_items", [])) if isinstance(base_payload.get("blocked_items"), list) else 0,
        },
        "execution_performed": False,
        "queue_mutation_performed": False,
        "local_only": True,
        "execution_allowed": False,
        "next_safe_action": _next_safe_action(sequence=sequence, blocked_entries=blocked_entries),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }
    return _emit_or_write(config=config, payload=payload, output=output, force=force, output_format=fmt)


def _load_queue(queue_path: Path) -> dict[str, Any]:
    if not queue_path.exists():
        return {"ok": False, "message": f"Local queue file not found: {queue_path}"}
    try:
        raw = json.loads(queue_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"ok": False, "message": f"Local queue could not be read: {exc}"}
    items = raw.get("work_items", []) if isinstance(raw, dict) else []
    if not isinstance(items, list):
        return {"ok": False, "message": "Local queue work_items must be a list."}
    return {"ok": True, "items": [item for item in items if isinstance(item, dict)]}


def _artifact_index(config: AppConfig, *, project_id: str) -> dict[str, list[dict[str, Any]]]:
    result = inspect_artifact_registry(config, project_id=project_id, output_format="json")
    payload = result.get("payload", result)
    artifacts = payload.get("artifacts", []) if isinstance(payload, dict) else []
    index: dict[str, list[dict[str, Any]]] = defaultdict(list)
    if isinstance(artifacts, list):
        for artifact in artifacts:
            if not isinstance(artifact, dict):
                continue
            item_id = str(artifact.get("item_id", "")).strip()
            if item_id:
                index[item_id].append(artifact)
    return dict(index)


def _approval_index(config: AppConfig, *, approval_path: str | Path | None) -> dict[str, list[dict[str, Any]]]:
    path = resolve_dispatch_approval_gate_path(config.repo_root, approval_path)
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    gates = raw.get("approval_gates", []) if isinstance(raw, dict) else []
    index: dict[str, list[dict[str, Any]]] = defaultdict(list)
    if isinstance(gates, list):
        for gate in gates:
            if not isinstance(gate, dict):
                continue
            item_id = str(gate.get("item_id", "")).strip()
            if item_id:
                index[item_id].append(gate)
    return dict(index)


def _base_payload(base_plan: dict[str, Any]) -> dict[str, Any]:
    payload = base_plan.get("payload")
    if isinstance(payload, dict):
        return payload
    stdout = base_plan.get("stdout")
    if isinstance(stdout, str):
        try:
            decoded = json.loads(stdout)
        except json.JSONDecodeError:
            return {}
        return decoded if isinstance(decoded, dict) else {}
    return {}


def _candidate_sort_key(item: dict[str, Any]) -> tuple[int, int, int, str]:
    priority = _PRIORITY_RANK.get(str(item.get("priority", "normal")).strip(), 2)
    dependency_count = len(_list_values(item, "dependencies")) + len(_list_values(item, "depends_on"))
    milestone = _milestone_number(item)
    return (priority, dependency_count, milestone if milestone >= 0 else 999999, _item_id(item))


def _dependency_blockers(item: dict[str, Any], *, status_by_id: dict[str, str], sequenced_ids: set[str]) -> list[str]:
    blockers: list[str] = []
    for dependency_id in sorted(set(_list_values(item, "dependencies") + _list_values(item, "depends_on"))):
        status = status_by_id.get(dependency_id, "")
        if status == "done" or dependency_id in sequenced_ids:
            continue
        blockers.append(
            f"Dependency is not done or earlier in the recommended sequence: {dependency_id} (status={status or 'missing'})"
        )
    for blocker_id in sorted(set(_list_values(item, "blocked_by"))):
        status = status_by_id.get(blocker_id, "")
        if status == "done" or blocker_id in sequenced_ids:
            continue
        blockers.append(f"Blocked-by item is unresolved: {blocker_id} (status={status or 'missing'})")
    return blockers


def _sequence_entry(
    item: dict[str, Any],
    *,
    sequence: int | None,
    artifacts: list[dict[str, Any]],
    approvals: list[dict[str, Any]],
    blocked: bool = False,
    blocked_reasons: list[str] | None = None,
) -> dict[str, Any]:
    lane = _lane(item)
    approval_statuses = sorted({str(gate.get("status", "")).strip() for gate in approvals if str(gate.get("status", "")).strip()})
    approved = "approved_for_manual_handoff" in approval_statuses
    artifact_types = sorted({str(artifact.get("artifact_type", "")).strip() for artifact in artifacts if str(artifact.get("artifact_type", "")).strip()})
    return {
        "sequence": sequence,
        "item_id": _item_id(item),
        "title": str(item.get("title", "")).strip(),
        "project_id": str(item.get("project_id", "")).strip(),
        "repo_id": str(item.get("repo_id", "")).strip(),
        "status": str(item.get("status", "")).strip(),
        "priority": str(item.get("priority", "normal")).strip() or "normal",
        "milestone": f"M{_milestone_number(item)}" if _milestone_number(item) >= 0 else "",
        "recommended_lane": lane,
        "dependency_ids": sorted(set(_list_values(item, "dependencies") + _list_values(item, "depends_on"))),
        "artifact_ready": bool(artifact_types),
        "artifact_types": artifact_types,
        "approval_statuses": approval_statuses,
        "approval_ready": approved,
        "blocked": bool(blocked),
        "blocked_reasons": sorted({str(reason).strip() for reason in (blocked_reasons or []) if str(reason).strip()}),
        "execution_allowed": False,
        "next_safe_action": "Review prerequisites, then start this item only with a separate explicit local queue command.",
    }


def _append_review_warnings(
    entry: dict[str, Any],
    *,
    approval_warnings: list[dict[str, Any]],
    artifact_warnings: list[dict[str, Any]],
) -> None:
    if not entry.get("artifact_ready"):
        artifact_warnings.append(
            {
                "item_id": entry["item_id"],
                "warning": "No supported local dispatch/review artifact was found for this item.",
                "recommended_lane": entry["recommended_lane"],
            }
        )
    if not entry.get("approval_ready"):
        approval_warnings.append(
            {
                "item_id": entry["item_id"],
                "warning": "No approved dispatch approval gate was found for this item.",
                "approval_statuses": entry.get("approval_statuses", []),
            }
        )


def _lane(item: dict[str, Any]) -> str:
    routing = item.get("routing_metadata", {})
    if isinstance(routing, dict):
        lane = str(routing.get("recommended_agent_lane", "")).strip()
        if lane:
            return lane
    item_type = str(item.get("item_type", "")).strip().lower()
    tags = {tag.lower() for tag in _list_values(item, "tags")}
    if item_type == "documentation" or any("documentation" in tag for tag in tags):
        return "documentation"
    if item_type == "dashboard":
        return "dashboard"
    if item_type == "architecture":
        return "architect_planner"
    if item_type in {"validation", "test"}:
        return "reviewer_validator"
    if "codex" in " ".join(tags):
        return "high_value_codex"
    return "local_operator_assistant"


def _lane_grouping(sequence: list[dict[str, Any]]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = defaultdict(list)
    for entry in sequence:
        grouped[str(entry.get("recommended_lane", "")).strip() or "unclassified"].append(str(entry.get("item_id", "")).strip())
    return dict(sorted(grouped.items()))


def _list_values(item: dict[str, Any], field_name: str) -> list[str]:
    values = item.get(field_name, [])
    if not isinstance(values, list):
        return []
    return [str(value).strip() for value in values if str(value).strip()]


def _item_id(item: dict[str, Any]) -> str:
    return str(item.get("item_id", "")).strip()


def _milestone_number(item: dict[str, Any]) -> int:
    text = " ".join([_item_id(item), str(item.get("title", "")), " ".join(_list_values(item, "tags"))])
    match = re.search(r"\bm(\d+)\b", text, flags=re.IGNORECASE)
    return int(match.group(1)) if match else -1


def _dedupe_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for record in records:
        key = json.dumps(record, sort_keys=True)
        if key in seen:
            continue
        seen.add(key)
        result.append(record)
    return result


def _next_safe_action(*, sequence: list[dict[str, Any]], blocked_entries: list[dict[str, Any]]) -> str:
    actionable = [entry for entry in sequence if not entry.get("blocked")]
    if actionable:
        return "Review the recommended sequence and prerequisites, then start only the first approved item with a separate local command."
    if blocked_entries:
        return "Resolve dependency, approval, or artifact warnings before starting a batch."
    return "Add proposed or ready queue items before planning an operator batch."


def _emit_or_write(
    *,
    config: AppConfig,
    payload: dict[str, Any],
    output: str | Path | None,
    force: bool,
    output_format: str,
) -> dict[str, Any]:
    rendered = json.dumps(payload, indent=2) if output_format == "json" else _render_markdown(payload)
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
                "command": COMMAND_NAME,
                "ok": False,
                "local_only": True,
                "format": output_format,
                "wrote_output_file": False,
                "output_path": str(target),
                "stdout": json.dumps(blocked_payload, indent=2) if output_format == "json" else _render_markdown(blocked_payload),
                "payload": blocked_payload,
            }
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(rendered + "\n", encoding="utf-8")
        payload = dict(payload)
        payload["output_path"] = str(target)
        return {
            "command": COMMAND_NAME,
            "ok": True,
            "local_only": True,
            "format": output_format,
            "wrote_output_file": True,
            "output_path": str(target),
            "stdout": json.dumps(payload, indent=2) if output_format == "json" else _render_markdown(payload),
            "payload": payload,
        }
    return {
        "command": COMMAND_NAME,
        "ok": True,
        "local_only": True,
        "format": output_format,
        "wrote_output_file": False,
        "stdout": rendered,
        "payload": payload,
    }


def _render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Operator Batch Sequence v2",
        "",
        f"- plan_type: {payload.get('plan_type')}",
        f"- project_id: {payload.get('project_id')}",
        f"- proposed_count: {payload.get('proposed_count')}",
        f"- blocked_count: {payload.get('blocked_count')}",
        f"- execution_allowed: {payload.get('execution_allowed')}",
        "",
        "## Recommended Sequence",
    ]
    sequence = payload.get("recommended_sequence", [])
    if isinstance(sequence, list) and sequence:
        for entry in sequence:
            if isinstance(entry, dict):
                marker = entry.get("sequence") if entry.get("sequence") is not None else "blocked"
                lines.append(f"- {marker}. {entry.get('item_id')} | {entry.get('recommended_lane')} | {entry.get('priority')}")
    else:
        lines.append("- None")
    lines.extend(["", "## Operator Checklist"])
    lines.extend(f"- {item}" for item in payload.get("operator_checklist", []) if str(item).strip())
    lines.extend(["", f"- next_safe_action: {payload.get('next_safe_action')}"])
    return "\n".join(lines).rstrip()


def _error(code: str, details: dict[str, Any]) -> dict[str, Any]:
    return {
        "command": COMMAND_NAME,
        "ok": False,
        "local_only": True,
        "execution_allowed": False,
        "error": code,
        "details": details,
    }


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()
