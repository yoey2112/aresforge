from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.local_project_queue import (
    inspect_local_queue_item_readiness,
    resolve_project_queue_path,
)
from aresforge.operator.queue_agent_dispatch_plan import build_queue_agent_dispatch_plan

COMMAND_NAME = "plan-operator-batch"
PLANNER_VERSION = "m104.1"

_BOUNDARY_CONFIRMATIONS: tuple[str, ...] = (
    "M104 operator batch planning is local-only.",
    "Batch planning is read-only.",
    "No queue items are seeded by default.",
    "No queue mutation performed.",
    "No Codex execution.",
    "No local LLM execution.",
    "No documentation-agent execution.",
    "No GitHub API calls.",
    "No gh calls.",
    "No network service calls.",
    "No automatic next-item execution.",
)

_PLANNABLE_STATUSES = {"ready", "proposed"}


def plan_operator_batch(
    config: AppConfig,
    *,
    project_id: str,
    queue_path: str | Path | None = None,
    registry_path: str | Path | None = None,
    limit: int = 10,
    output_format: str = "markdown",
) -> dict[str, Any]:
    normalized_project_id = str(project_id or "").strip()
    if not normalized_project_id:
        return _error("invalid_project_id", "project_id is required.")
    normalized_limit = max(1, min(int(limit or 10), 100))
    resolved_queue_path = resolve_project_queue_path(config.repo_root, queue_path)
    loaded = _load_queue(resolved_queue_path)
    if not loaded.get("ok", False):
        return loaded

    all_items = loaded["items"]
    project_items = [
        item for item in all_items
        if str(item.get("project_id", "")).strip() == normalized_project_id
    ]
    proposed_items: list[dict[str, Any]] = []
    excluded_items: list[dict[str, Any]] = []
    blocked_items: list[dict[str, Any]] = []
    warnings: list[str] = []
    planned_ids: set[str] = set()
    status_by_id = {
        str(item.get("item_id", "")).strip(): str(item.get("status", "")).strip()
        for item in all_items
        if str(item.get("item_id", "")).strip()
    }

    for item in sorted(project_items, key=_roadmap_sort_key):
        item_id = str(item.get("item_id", "")).strip()
        status = str(item.get("status", "")).strip()
        if not item_id:
            continue
        if status == "done":
            excluded_items.append(_excluded_item(item, reason="done_items_are_excluded"))
            continue
        if status not in _PLANNABLE_STATUSES:
            target = blocked_items if status == "blocked" else excluded_items
            target.append(_excluded_item(item, reason=f"status_{status or 'unknown'}_not_plannable"))
            continue

        dependency_blockers = _dependency_blockers(item, status_by_id=status_by_id, planned_ids=planned_ids)
        readiness = inspect_local_queue_item_readiness(
            config,
            item_id=item_id,
            queue_path=resolved_queue_path,
            registry_path=registry_path,
        )
        readiness_blockers = _filtered_readiness_blockers(item, readiness, planned_ids=planned_ids)
        if dependency_blockers or readiness_blockers:
            blocked_items.append(
                _planned_item(
                    item=item,
                    sequence=None,
                    safety_classification="blocked",
                    blocked_reasons=[*dependency_blockers, *readiness_blockers],
                    dispatch_plan={},
                )
            )
            continue

        dispatch_plan = build_queue_agent_dispatch_plan(
            config,
            item_id=item_id,
            queue_path=resolved_queue_path,
            registry_path=registry_path,
        )
        safety_classification = _safety_classification(dispatch_plan)
        if safety_classification == "blocked":
            blocked_items.append(
                _planned_item(
                    item=item,
                    sequence=None,
                    safety_classification="blocked",
                    blocked_reasons=dispatch_plan.get("blocked_reasons", []),
                    dispatch_plan=dispatch_plan,
                )
            )
            continue

        if len(proposed_items) >= normalized_limit:
            excluded_items.append(_excluded_item(item, reason="limit_reached"))
            continue

        planned_ids.add(item_id)
        proposed_items.append(
            _planned_item(
                item=item,
                sequence=len(proposed_items) + 1,
                safety_classification=safety_classification,
                blocked_reasons=[],
                dispatch_plan=dispatch_plan,
            )
        )

    batch_id = _batch_id(normalized_project_id)
    payload = {
        "ok": True,
        "planner_version": PLANNER_VERSION,
        "batch_id": batch_id,
        "generated_at": datetime.now(UTC).isoformat(),
        "project_id": normalized_project_id,
        "queue_path": str(resolved_queue_path),
        "limit": normalized_limit,
        "proposed_items": proposed_items,
        "excluded_items": excluded_items,
        "blocked_items": blocked_items,
        "warnings": sorted({warning for warning in warnings if warning}),
        "recommended_next_action": _next_action(proposed_items=proposed_items, blocked_items=blocked_items),
        "local_only": True,
        "read_only": True,
        "execution_allowed": False,
        "queue_mutation_allowed": False,
        "automatic_next_item_execution_allowed": False,
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }
    return _stdout_result(
        command=COMMAND_NAME,
        payload=payload,
        output_format=output_format,
        markdown=_render_markdown(payload),
    )


def _load_queue(queue_path: Path) -> dict[str, Any]:
    if not queue_path.exists():
        return _error("queue_not_found", f"Local queue file not found: {queue_path}")
    try:
        raw = json.loads(queue_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return _error("queue_unreadable", f"Local queue could not be read: {exc}")
    items = raw.get("work_items", []) if isinstance(raw, dict) else []
    if not isinstance(items, list):
        return _error("queue_invalid_schema", "Local queue work_items must be a list.")
    return {"ok": True, "items": [item for item in items if isinstance(item, dict)]}


def _dependency_blockers(item: dict[str, Any], *, status_by_id: dict[str, str], planned_ids: set[str]) -> list[str]:
    blockers: list[str] = []
    dependencies = _list_values(item, "dependencies") + _list_values(item, "depends_on")
    for dependency_id in sorted(set(dependencies)):
        dependency_status = status_by_id.get(dependency_id, "")
        if dependency_status == "done" or dependency_id in planned_ids:
            continue
        if not dependency_status:
            blockers.append(f"Dependency not found: {dependency_id}")
        else:
            blockers.append(f"Dependency is not done or earlier in the planned batch: {dependency_id} (status={dependency_status})")
    for blocker_id in sorted(set(_list_values(item, "blocked_by"))):
        blocker_status = status_by_id.get(blocker_id, "")
        if blocker_status == "done" or blocker_id in planned_ids:
            continue
        blockers.append(f"Blocked-by item is unresolved: {blocker_id} (status={blocker_status or 'unknown'})")
    return blockers


def _filtered_readiness_blockers(
    item: dict[str, Any],
    readiness: dict[str, Any],
    *,
    planned_ids: set[str],
) -> list[str]:
    dependency_ids = set(_list_values(item, "dependencies") + _list_values(item, "depends_on"))
    blocked_by_ids = set(_list_values(item, "blocked_by"))
    blockers: list[str] = []
    for blocker in readiness.get("blockers", []):
        text = str(blocker).strip()
        if not text:
            continue
        if any(dependency_id in planned_ids and dependency_id in text for dependency_id in dependency_ids):
            continue
        if any(blocker_id in planned_ids and blocker_id in text for blocker_id in blocked_by_ids):
            continue
        blockers.append(text)
    return blockers


def _list_values(item: dict[str, Any], field_name: str) -> list[str]:
    values = item.get(field_name, [])
    if not isinstance(values, list):
        return []
    return [str(value).strip() for value in values if str(value).strip()]


def _roadmap_sort_key(item: dict[str, Any]) -> tuple[int, int, str]:
    status_rank = {"ready": 0, "proposed": 1, "blocked": 2}.get(str(item.get("status", "")).strip(), 3)
    milestone = _milestone_number(item)
    return (milestone if milestone >= 0 else 999999, status_rank, str(item.get("item_id", "")).strip())


def _milestone_number(item: dict[str, Any]) -> int:
    text = " ".join(
        [
            str(item.get("item_id", "")),
            str(item.get("title", "")),
            " ".join(_list_values(item, "tags")),
        ]
    )
    match = re.search(r"\bm(\d+)\b", text, flags=re.IGNORECASE)
    return int(match.group(1)) if match else -1


def _safety_classification(dispatch_plan: dict[str, Any]) -> str:
    if bool(dispatch_plan.get("blocked", False)) or not bool(dispatch_plan.get("ok", False)):
        return "blocked"
    lane = str(dispatch_plan.get("selected_lane", "")).strip()
    if lane == "codex_prompt_artifact":
        return "codex_artifact_possible"
    if lane in {"local_llm_advisory", "local_llm_coding_draft"}:
        return "local_llm_dry_run_possible"
    if lane == "documentation_agent_dry_run":
        return "documentation_dry_run_possible"
    return "manual_only"


def _planned_item(
    *,
    item: dict[str, Any],
    sequence: int | None,
    safety_classification: str,
    blocked_reasons: list[Any],
    dispatch_plan: dict[str, Any],
) -> dict[str, Any]:
    return {
        "sequence": sequence,
        "item_id": str(item.get("item_id", "")).strip(),
        "title": str(item.get("title", "")).strip(),
        "status": str(item.get("status", "")).strip(),
        "project_id": str(item.get("project_id", "")).strip(),
        "repo_id": str(item.get("repo_id", "")).strip(),
        "milestone": f"M{_milestone_number(item)}" if _milestone_number(item) >= 0 else "",
        "safety_classification": safety_classification,
        "selected_lane": str(dispatch_plan.get("selected_lane", "")).strip(),
        "blocked_reasons": sorted({str(reason).strip() for reason in blocked_reasons if str(reason).strip()}),
        "execution_allowed": False,
        "next_safe_action": _item_next_action(safety_classification),
    }


def _excluded_item(item: dict[str, Any], *, reason: str) -> dict[str, str]:
    return {
        "item_id": str(item.get("item_id", "")).strip(),
        "title": str(item.get("title", "")).strip(),
        "status": str(item.get("status", "")).strip(),
        "reason": reason,
    }


def _item_next_action(safety_classification: str) -> str:
    if safety_classification == "codex_artifact_possible":
        return "Inspect dispatch plan and generate a Codex prompt artifact only after operator review."
    if safety_classification == "local_llm_dry_run_possible":
        return "Inspect dispatch plan and run the matching local LLM dry-run validator only."
    if safety_classification == "documentation_dry_run_possible":
        return "Inspect dispatch plan and run the documentation-agent dry-run validator only."
    if safety_classification == "blocked":
        return "Resolve blockers before adding this item to an operator batch."
    return "Review manually before any handoff or lifecycle change."


def _batch_id(project_id: str) -> str:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    slug = re.sub(r"[^a-z0-9]+", "-", project_id.lower()).strip("-") or "project"
    return f"operator-batch-{slug}-{stamp}"


def _next_action(*, proposed_items: list[dict[str, Any]], blocked_items: list[dict[str, Any]]) -> str:
    if proposed_items:
        return "Review the proposed batch order, inspect each dispatch plan, and start only one approved queue item at a time."
    if blocked_items:
        return "Resolve blocked queue items before planning an operator batch."
    return "Add or mark queue items ready/proposed before planning an operator batch."


def _stdout_result(command: str, payload: dict[str, Any], output_format: str, markdown: str) -> dict[str, Any]:
    fmt = str(output_format or "markdown").lower().strip()
    if fmt not in {"json", "markdown"}:
        return _error("invalid_format", "Output format must be json or markdown.")
    return {
        "command": command,
        "ok": True,
        "local_only": True,
        "read_only": True,
        "format": fmt,
        "wrote_output_file": False,
        "stdout": json.dumps(payload, indent=2) if fmt == "json" else markdown,
        "payload": payload,
    }


def _error(code: str, message: str) -> dict[str, Any]:
    return {
        "command": COMMAND_NAME,
        "ok": False,
        "local_only": True,
        "read_only": True,
        "error": code,
        "details": {"message": message},
    }


def _render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Operator Batch Plan",
        "",
        f"- batch_id: {payload.get('batch_id')}",
        f"- project_id: {payload.get('project_id')}",
        f"- proposed_count: {len(payload.get('proposed_items', [])) if isinstance(payload.get('proposed_items'), list) else 0}",
        f"- blocked_count: {len(payload.get('blocked_items', [])) if isinstance(payload.get('blocked_items'), list) else 0}",
        f"- execution_allowed: {payload.get('execution_allowed')}",
        "",
        "## Proposed Items",
    ]
    proposed = payload.get("proposed_items", [])
    if isinstance(proposed, list) and proposed:
        for item in proposed:
            if not isinstance(item, dict):
                continue
            lines.append(
                f"- {item.get('sequence')}. {item.get('item_id')} | {item.get('safety_classification')} | {item.get('status')}"
            )
    else:
        lines.append("- None")
    lines.extend(["", "## Blocked Items"])
    blocked = payload.get("blocked_items", [])
    if isinstance(blocked, list) and blocked:
        for item in blocked:
            if not isinstance(item, dict):
                continue
            reasons = item.get("blocked_reasons", [])
            lines.append(f"- {item.get('item_id')} | reasons={'; '.join(reasons) if isinstance(reasons, list) else ''}")
    else:
        lines.append("- None")
    lines.extend(["", f"- recommended_next_action: {payload.get('recommended_next_action')}"])
    return "\n".join(lines)
