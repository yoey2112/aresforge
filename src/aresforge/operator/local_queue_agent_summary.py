from __future__ import annotations

from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.local_active_project import inspect_active_project
from aresforge.operator.local_project_queue import QUEUE_STATUSES, inspect_project_queue


def inspect_local_queue_agent_summary(config: AppConfig) -> dict[str, Any]:
    queue_result = inspect_project_queue(config, output_format="json")
    active_result = inspect_active_project(config)

    warnings: list[str] = list(active_result.get("warnings", []))
    items: list[dict[str, Any]] = []
    if bool(queue_result.get("ok", False)):
        payload = queue_result.get("payload", {})
        raw_items = payload.get("work_items", []) if isinstance(payload, dict) else []
        items = [item for item in raw_items if isinstance(item, dict)]
    else:
        warnings.append(str(queue_result.get("details", {}).get("message", "Local queue unavailable.")))

    queue_totals = {
        "item_count": len(items),
        "status_counts": _status_counts(items),
        "agent_group_count": len(_items_by_agent(items)),
    }
    items_by_status = _items_by_status(items)
    items_by_agent = _items_by_agent(items)
    blocked_items = [
        _item_card(item)
        for item in items
        if str(item.get("status", "")).strip() == "blocked" or bool(item.get("blocked_by"))
    ]
    next_ready_items = [
        _item_card(item)
        for item in items
        if str(item.get("status", "")).strip() == "ready"
    ]
    next_ready_items.sort(key=lambda item: (item["priority"], item["item_id"]))

    active_project_id = str(active_result.get("active_project_id", "")).strip()
    next_safe_action = "Inspect queue readiness and continue local planning."
    if not items:
        next_safe_action = "Initialize or populate local queue with at least one item."
    elif blocked_items:
        next_safe_action = "Resolve blocked items or dependency blockers before starting new work."
    elif next_ready_items:
        next_safe_action = f"Start with ready item: {next_ready_items[0]['item_id']}"

    return {
        "ok": True,
        "local_only": True,
        "queue_totals": queue_totals,
        "items_by_status": items_by_status,
        "items_by_agent": items_by_agent,
        "blocked_items": blocked_items,
        "next_ready_items": next_ready_items,
        "active_project": {
            "active_project_selected": bool(active_project_id),
            "active_project_id": active_project_id,
            "active_project_name": str((active_result.get("active_project") or {}).get("name", "")).strip()
            if isinstance(active_result.get("active_project"), dict)
            else "",
        },
        "next_safe_action": next_safe_action,
        "warnings": sorted(set(warnings)),
    }


def _status_counts(items: list[dict[str, Any]]) -> dict[str, int]:
    counts = {status: 0 for status in QUEUE_STATUSES}
    for item in items:
        status = str(item.get("status", "")).strip()
        if status not in counts:
            counts[status] = 0
        counts[status] += 1
    return counts


def _items_by_status(items: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {status: [] for status in QUEUE_STATUSES}
    for item in items:
        status = str(item.get("status", "")).strip()
        if status not in grouped:
            grouped[status] = []
        grouped[status].append(_item_card(item))
    for key in grouped:
        grouped[key] = sorted(grouped[key], key=lambda value: value["item_id"])
    return grouped


def _items_by_agent(items: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        label = str(item.get("assigned_agent", "")).strip() or "unassigned"
        grouped.setdefault(label, []).append(_item_card(item))
    for key in grouped:
        grouped[key] = sorted(grouped[key], key=lambda value: value["item_id"])
    return dict(sorted(grouped.items(), key=lambda pair: pair[0]))


def _priority_sort_key(value: str) -> int:
    return {"urgent": 0, "high": 1, "normal": 2, "low": 3}.get(value, 4)


def _item_card(item: dict[str, Any]) -> dict[str, Any]:
    priority = str(item.get("priority", "")).strip()
    return {
        "item_id": str(item.get("item_id", "")).strip(),
        "project_id": str(item.get("project_id", "")).strip(),
        "repo_id": str(item.get("repo_id", "")).strip(),
        "title": str(item.get("title", "")).strip(),
        "status": str(item.get("status", "")).strip(),
        "priority": priority,
        "priority_rank": _priority_sort_key(priority),
        "assigned_agent": str(item.get("assigned_agent", "")).strip() or "unassigned",
        "blocked_by": [
            str(value).strip()
            for value in item.get("blocked_by", [])
            if str(value).strip()
        ]
        if isinstance(item.get("blocked_by"), list)
        else [],
    }
