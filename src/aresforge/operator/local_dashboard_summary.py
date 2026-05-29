from __future__ import annotations

from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.local_active_project import inspect_active_project
from aresforge.operator.local_project_queue import inspect_project_queue
from aresforge.operator.local_queue_agent_summary import inspect_local_queue_agent_summary
from aresforge.operator.managed_project_registry_local import (
    inspect_managed_project_registry,
    resolve_managed_project_registry_path,
)


def summarize_hub_home_dashboard(config: AppConfig) -> dict[str, Any]:
    warnings: list[str] = []
    blockers: list[str] = []
    source_summary: list[str] = []

    registry_path = resolve_managed_project_registry_path(config.repo_root, None)
    queue_path = config.repo_root / ".aresforge" / "queue" / "work_items.json"
    active_project_path = config.repo_root / ".aresforge" / "projects" / "active_project.json"
    agent_profiles_path = config.repo_root / ".aresforge" / "agents" / "agents.json"

    source_summary.extend(
        [
            f"managed_project_registry:{registry_path}",
            f"project_queue:{queue_path}",
            f"active_project_state:{active_project_path}",
            f"agent_profiles:{agent_profiles_path}",
        ]
    )

    registry_result = inspect_managed_project_registry(config, output_format="json")
    active_result = inspect_active_project(config)
    queue_result = inspect_project_queue(config, output_format="json")
    lane_result = inspect_local_queue_agent_summary(config)

    projects: list[dict[str, Any]] = []
    if registry_result.get("ok", False):
        payload = registry_result.get("payload", {})
        if isinstance(payload, dict):
            projects = [
                item for item in payload.get("projects", []) if isinstance(item, dict)
            ]
    else:
        warnings.append(
            str(
                registry_result.get("details", {}).get(
                    "message", "Managed project registry unavailable."
                )
            )
        )

    queue_items: list[dict[str, Any]] = []
    if queue_result.get("ok", False):
        payload = queue_result.get("payload", {})
        if isinstance(payload, dict):
            queue_items = [
                item for item in payload.get("work_items", []) if isinstance(item, dict)
            ]
    else:
        warnings.append(
            str(
                queue_result.get("details", {}).get(
                    "message", "Local project queue unavailable."
                )
            )
        )

    counts_by_status: dict[str, int] = {}
    for item in queue_items:
        status = str(item.get("status", "")).strip() or "unknown"
        counts_by_status[status] = counts_by_status.get(status, 0) + 1
    counts_by_status = dict(sorted(counts_by_status.items()))

    active_project_id = str(active_result.get("active_project_id", "")).strip()
    active_project_name = ""
    active_project_status = ""
    active_project = active_result.get("active_project")
    if isinstance(active_project, dict):
        active_project_name = str(active_project.get("name", "")).strip()
        active_project_status = str(active_project.get("status", "")).strip()

    lane_map = (
        lane_result.get("items_by_agent", {})
        if isinstance(lane_result.get("items_by_agent"), dict)
        else {}
    )
    lanes: list[dict[str, Any]] = []
    for lane_id in sorted(lane_map.keys()):
        lane_items = lane_map.get(lane_id, [])
        item_count = len(lane_items) if isinstance(lane_items, list) else 0
        lanes.append(
            {
                "lane_id": str(lane_id).strip() or "unknown",
                "item_count": item_count,
            }
        )

    active_project_selected = bool(active_project_id)
    if not projects:
        blockers.append("No managed projects registered.")
    if not active_project_selected:
        blockers.append("No active project selected.")

    if not queue_items:
        warnings.append("Local queue has no items.")

    repo_status = "unavailable"
    repo_warnings: list[str] = []
    if not projects:
        repo_warnings.append("No project/repo metadata available in managed registry.")
    else:
        repo_status = "available"
        has_repo = any(
            isinstance(project.get("repos"), list) and len(project.get("repos", [])) > 0
            for project in projects
        )
        if not has_repo:
            repo_status = "needs_attention"
            repo_warnings.append("Projects exist but no repos are registered.")
        elif active_project_selected and not str(active_result.get("active_repo_id", "")).strip():
            repo_status = "needs_attention"
            repo_warnings.append("Active project has no resolved active repo.")

    warnings.extend(repo_warnings)
    warnings.extend(list(active_result.get("warnings", [])))
    warnings.extend(list(lane_result.get("warnings", [])))

    next_safe_action = "Refresh dashboard summary."
    if blockers:
        next_safe_action = "Create/select an active local project and retry."
    elif not queue_items:
        next_safe_action = "Add a local queue item for the active project."
    elif any(status in counts_by_status for status in ("blocked",)):
        next_safe_action = "Resolve blocked queue items before starting new work."
    elif "ready" in counts_by_status:
        next_safe_action = "Start with a ready queue item."

    return {
        "ok": True,
        "local_only": True,
        "read_only": True,
        "dashboard_type": "hub_home",
        "project_summary": {
            "total_projects": len(projects),
            "active_project_id": active_project_id,
            "active_project_name": active_project_name,
            "active_project_status": active_project_status,
        },
        "queue_summary": {
            "total_items": len(queue_items),
            "counts_by_status": counts_by_status,
        },
        "agent_lane_summary": {
            "total_lanes": len(lanes),
            "lanes": lanes,
        },
        "repo_summary": {
            "available": bool(projects),
            "status": repo_status,
            "warnings": sorted(set(repo_warnings)),
        },
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(str(item).strip() for item in warnings if str(item).strip())),
        "next_safe_action": next_safe_action,
        "source_summary": source_summary,
    }
