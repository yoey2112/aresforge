from __future__ import annotations

import json
from collections import deque
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.local_agent_profiles import resolve_agent_profiles_path
from aresforge.operator.local_project_queue import resolve_project_queue_path
from aresforge.operator.managed_project_registry_local import resolve_managed_project_registry_path

COMMAND_NAME = "plan-agent-orchestration"
DEFAULT_OUTPUT_DIR = Path("artifacts") / "orchestration"

_RESOLVED_QUEUE_STATUSES = {"done", "cancelled"}
_ACTIVE_QUEUE_STATUSES = {"proposed", "ready", "in_progress", "blocked"}

_ITEM_ROLE_PREFERENCES: dict[str, list[str]] = {
    "documentation": ["documentation", "reviewer", "architect"],
    "validation": ["tester", "reviewer", "implementer"],
    "handoff": ["operator", "coordinator", "reviewer"],
    "orchestration": ["coordinator", "architect", "operator"],
    "bug": ["implementer", "architect", "tester"],
    "feature": ["implementer", "architect", "tester"],
    "sync": ["operator", "reviewer", "coordinator"],
    "dashboard": ["implementer", "architect", "documentation"],
}


def generate_agent_orchestration_plan(
    config: AppConfig,
    *,
    project_id: str | None = None,
    repo_id: str | None = None,
    status: str | None = None,
    queue_path: str | Path | None = None,
    profiles_path: str | Path | None = None,
    registry_path: str | Path | None = None,
    output: str | Path | None = None,
    output_format: str = "json",
    force: bool = False,
) -> dict[str, Any]:
    format_name = output_format.lower().strip()
    if format_name not in {"json", "markdown"}:
        return _error("invalid_format", {"format": output_format})

    resolved_queue_path = resolve_project_queue_path(config.repo_root, queue_path)
    resolved_profiles_path = resolve_agent_profiles_path(config.repo_root, profiles_path)
    resolved_registry_path = resolve_managed_project_registry_path(config.repo_root, registry_path)

    warnings: list[str] = []
    input_files: dict[str, Any] = {
        "queue": {
            "path": str(resolved_queue_path),
            "exists": resolved_queue_path.exists(),
            "provided": queue_path is not None,
        },
        "profiles": {
            "path": str(resolved_profiles_path),
            "exists": resolved_profiles_path.exists(),
            "provided": profiles_path is not None,
        },
        "registry": {
            "path": str(resolved_registry_path),
            "exists": resolved_registry_path.exists(),
            "provided": registry_path is not None,
        },
    }

    queue_data = _load_json_object(resolved_queue_path, "queue", warnings)
    profiles_data = _load_json_object(resolved_profiles_path, "profiles", warnings)
    registry_data = _load_json_object(resolved_registry_path, "registry", warnings)

    items = _normalize_items(queue_data)
    filtered_items = _apply_filters(items, project_id=project_id, repo_id=repo_id, status=status)

    registry_index = _build_registry_index(registry_data)
    _warn_missing_registry_links(filtered_items, registry_index, warnings)

    agents = _normalize_agents(profiles_data)
    agents_by_id = {agent["agent_id"]: agent for agent in agents}

    assignments, unassigned_items = _recommend_assignments(filtered_items, agents_by_id, warnings)

    dependency_order, cycle_warnings, dependency_warnings = _build_dependency_order(
        filtered_items,
        known_item_ids={item["item_id"] for item in items},
    )
    warnings.extend(cycle_warnings)
    warnings.extend(dependency_warnings)

    blocked_items = _detect_blocked_items(filtered_items)

    handoff_prompts = _build_handoff_prompts(assignments)

    next_actions = _build_next_actions(
        filtered_items=filtered_items,
        assignments=assignments,
        blocked_items=blocked_items,
        unassigned_items=unassigned_items,
        warnings=warnings,
    )

    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "local_only": True,
        "plan_only": True,
        "filters": {
            "project_id": project_id,
            "repo_id": repo_id,
            "status": status,
        },
        "input_files": input_files,
        "selected_work_items": filtered_items,
        "available_agents": agents,
        "recommended_assignments": assignments,
        "dependency_order": dependency_order,
        "blocked_items": blocked_items,
        "unassigned_items": unassigned_items,
        "handoff_prompts": handoff_prompts,
        "risk_warnings": sorted(set(warnings)),
        "next_actions": next_actions,
        "boundary_confirmations": [
            "local-only orchestration planning",
            "plan-only",
            "no agent execution",
            "no GitHub calls",
            "no gh calls",
            "no network calls",
            "no LLM calls",
        ],
    }

    rendered_json = json.dumps(payload, indent=2, sort_keys=True)
    rendered_markdown = _render_markdown(payload)

    if output is None:
        return {
            "command": COMMAND_NAME,
            "ok": True,
            "local_only": True,
            "plan_only": True,
            "format": format_name,
            "wrote_output_file": False,
            "stdout": rendered_json if format_name == "json" else rendered_markdown,
            "payload": payload,
        }

    output_path = Path(output)
    if output_path.exists() and not force:
        return _error(
            "output_exists",
            {"path": str(output_path), "hint": "Re-run with --force to overwrite."},
            payload=payload,
        )

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return _error(
            "output_directory_create_failed",
            {"path": str(output_path.parent), "message": str(exc)},
            payload=payload,
        )

    content = rendered_json if format_name == "json" else rendered_markdown
    try:
        output_path.write_text(content + "\n", encoding="utf-8")
    except OSError as exc:
        return _error(
            "output_write_failed",
            {"path": str(output_path), "message": str(exc)},
            payload=payload,
        )

    return {
        "command": COMMAND_NAME,
        "ok": True,
        "local_only": True,
        "plan_only": True,
        "format": format_name,
        "output": str(output_path),
        "force": force,
        "wrote_output_file": True,
        "warnings": payload["risk_warnings"],
        "boundary_confirmations": payload["boundary_confirmations"],
    }


def _load_json_object(path: Path, label: str, warnings: list[str]) -> dict[str, Any] | None:
    if not path.exists():
        warnings.append(f"{label} file not found: {path}")
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        warnings.append(f"{label} file could not be parsed: {path} ({exc})")
        return None
    if not isinstance(raw, dict):
        warnings.append(f"{label} file did not decode to an object: {path}")
        return None
    return raw


def _normalize_items(queue_data: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(queue_data, dict):
        return []
    raw_items = queue_data.get("work_items")
    if not isinstance(raw_items, list):
        return []

    items: list[dict[str, Any]] = []
    for raw_item in raw_items:
        if not isinstance(raw_item, dict):
            continue
        item = {
            "item_id": str(raw_item.get("item_id", "")).strip(),
            "project_id": str(raw_item.get("project_id", "")).strip(),
            "repo_id": str(raw_item.get("repo_id", "")).strip(),
            "title": str(raw_item.get("title", "")).strip(),
            "description": str(raw_item.get("description", "")).strip(),
            "status": str(raw_item.get("status", "")).strip(),
            "priority": str(raw_item.get("priority", "")).strip(),
            "item_type": str(raw_item.get("item_type", "")).strip() or "other",
            "assigned_agent": str(raw_item.get("assigned_agent", "")).strip(),
            "dependencies": _as_string_list(raw_item.get("dependencies")),
            "blocked_by": _as_string_list(raw_item.get("blocked_by")),
            "tags": _as_string_list(raw_item.get("tags")),
            "source": str(raw_item.get("source", "")).strip(),
            "notes": str(raw_item.get("notes", "")).strip(),
            "created_at": str(raw_item.get("created_at", "")).strip(),
            "updated_at": str(raw_item.get("updated_at", "")).strip(),
        }
        if item["item_id"]:
            items.append(item)
    return items


def _normalize_agents(profiles_data: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(profiles_data, dict):
        return []
    raw_agents = profiles_data.get("agents")
    if not isinstance(raw_agents, list):
        return []

    agents: list[dict[str, Any]] = []
    for raw_agent in raw_agents:
        if not isinstance(raw_agent, dict):
            continue
        agent_id = str(raw_agent.get("agent_id", "")).strip()
        if not agent_id:
            continue
        agents.append(
            {
                "agent_id": agent_id,
                "name": str(raw_agent.get("name", "")).strip(),
                "role": str(raw_agent.get("role", "other")).strip() or "other",
                "status": str(raw_agent.get("status", "")).strip(),
                "execution_mode": str(raw_agent.get("execution_mode", "")).strip(),
                "allowed_item_types": _as_string_list(raw_agent.get("allowed_item_types")),
                "constraints": _as_string_list(raw_agent.get("constraints")),
                "handoff_target_id": str(raw_agent.get("handoff_target_id", "")).strip(),
            }
        )
    return sorted(agents, key=lambda item: item["agent_id"])


def _build_registry_index(registry_data: dict[str, Any] | None) -> dict[str, set[str]]:
    index: dict[str, set[str]] = {}
    if not isinstance(registry_data, dict):
        return index
    projects = registry_data.get("projects")
    if not isinstance(projects, list):
        return index
    for project in projects:
        if not isinstance(project, dict):
            continue
        project_key = str(project.get("project_id", "")).strip()
        if not project_key:
            continue
        repos: set[str] = set()
        for repo in project.get("repos", []):
            if not isinstance(repo, dict):
                continue
            repo_id = str(repo.get("repo_id", "")).strip()
            if repo_id:
                repos.add(repo_id)
        index[project_key] = repos
    return index


def _warn_missing_registry_links(
    items: list[dict[str, Any]],
    registry_index: dict[str, set[str]],
    warnings: list[str],
) -> None:
    if not registry_index:
        return
    for item in items:
        item_id = item["item_id"]
        project_key = item.get("project_id", "")
        repo_key = item.get("repo_id", "")
        if project_key not in registry_index:
            warnings.append(
                f"Item '{item_id}' references unknown project_id '{project_key}' in managed registry."
            )
            continue
        if repo_key and repo_key not in registry_index[project_key]:
            warnings.append(
                f"Item '{item_id}' references unknown repo_id '{repo_key}' under project '{project_key}'."
            )


def _apply_filters(
    items: list[dict[str, Any]],
    *,
    project_id: str | None,
    repo_id: str | None,
    status: str | None,
) -> list[dict[str, Any]]:
    project_value = project_id.strip() if isinstance(project_id, str) and project_id.strip() else None
    repo_value = repo_id.strip() if isinstance(repo_id, str) and repo_id.strip() else None
    status_value = status.strip() if isinstance(status, str) and status.strip() else None

    filtered: list[dict[str, Any]] = []
    for item in items:
        if project_value is not None and item.get("project_id") != project_value:
            continue
        if repo_value is not None and item.get("repo_id") != repo_value:
            continue
        item_status = str(item.get("status", "")).strip()
        if status_value is not None and item_status != status_value:
            continue
        if status_value is None and item_status not in _ACTIVE_QUEUE_STATUSES:
            continue
        filtered.append(item)
    return filtered


def _recommend_assignments(
    items: list[dict[str, Any]],
    agents_by_id: dict[str, dict[str, Any]],
    warnings: list[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    assignments: list[dict[str, Any]] = []
    unassigned: list[dict[str, Any]] = []
    active_agents = [agent for agent in agents_by_id.values() if agent.get("status") == "active"]

    for item in items:
        item_id = item["item_id"]
        item_type = item.get("item_type", "other")
        assigned_agent = item.get("assigned_agent", "")

        if assigned_agent:
            existing = agents_by_id.get(assigned_agent)
            if existing is not None:
                assignment = _build_assignment(
                    item=item,
                    agent=existing,
                    source="existing_assigned_agent",
                    confidence="high",
                )
                assignments.append(assignment)
                continue
            warnings.append(
                f"Item '{item_id}' has assigned_agent '{assigned_agent}' but that agent is missing from profiles."
            )
            unassigned.append(
                {
                    "item_id": item_id,
                    "project_id": item.get("project_id"),
                    "repo_id": item.get("repo_id"),
                    "item_type": item_type,
                    "reason": "assigned_agent_missing_from_profiles",
                }
            )
            continue

        recommendation = _recommend_agent_for_item(item, active_agents)
        if recommendation is None:
            warnings.append(f"No suitable active agent found for item '{item_id}' ({item_type}).")
            unassigned.append(
                {
                    "item_id": item_id,
                    "project_id": item.get("project_id"),
                    "repo_id": item.get("repo_id"),
                    "item_type": item_type,
                    "reason": "no_suitable_agent",
                }
            )
            continue

        assignments.append(
            _build_assignment(
                item=item,
                agent=recommendation["agent"],
                source="recommended_by_item_type",
                confidence=recommendation["confidence"],
            )
        )

    return assignments, unassigned


def _recommend_agent_for_item(
    item: dict[str, Any],
    active_agents: list[dict[str, Any]],
) -> dict[str, Any] | None:
    item_type = item.get("item_type", "other")
    preferred_roles = _ITEM_ROLE_PREFERENCES.get(item_type, ["implementer", "architect", "operator", "other"])

    for role in preferred_roles:
        candidates = [
            agent for agent in active_agents if agent.get("role") == role and _agent_accepts_item_type(agent, item_type)
        ]
        if candidates:
            return {"agent": sorted(candidates, key=lambda value: value["agent_id"])[0], "confidence": "high"}

    allowed_candidates = [
        agent for agent in active_agents if _agent_accepts_item_type(agent, item_type)
    ]
    if allowed_candidates:
        return {"agent": sorted(allowed_candidates, key=lambda value: value["agent_id"])[0], "confidence": "medium"}

    if active_agents:
        fallback = sorted(active_agents, key=lambda value: value["agent_id"])[0]
        if item_type == "other":
            return {"agent": fallback, "confidence": "low"}
    return None


def _agent_accepts_item_type(agent: dict[str, Any], item_type: str) -> bool:
    allowed_item_types = agent.get("allowed_item_types", [])
    if not isinstance(allowed_item_types, list) or not allowed_item_types:
        return True
    return item_type in allowed_item_types


def _build_assignment(
    *,
    item: dict[str, Any],
    agent: dict[str, Any],
    source: str,
    confidence: str,
) -> dict[str, Any]:
    return {
        "item_id": item.get("item_id"),
        "project_id": item.get("project_id"),
        "repo_id": item.get("repo_id"),
        "item_type": item.get("item_type"),
        "title": item.get("title"),
        "description": item.get("description"),
        "recommended_agent_id": agent.get("agent_id"),
        "recommended_agent_name": agent.get("name"),
        "recommended_agent_role": agent.get("role"),
        "handoff_target_id": agent.get("handoff_target_id"),
        "assignment_source": source,
        "confidence": confidence,
        "constraints": agent.get("constraints", []),
        "expected_output": _expected_output_for_item_type(item.get("item_type", "other")),
    }


def _build_dependency_order(
    items: list[dict[str, Any]],
    *,
    known_item_ids: set[str] | None = None,
) -> tuple[list[str], list[str], list[str]]:
    item_ids = {item["item_id"] for item in items}
    known_ids = known_item_ids or item_ids
    graph: dict[str, set[str]] = {item["item_id"]: set() for item in items}
    indegree: dict[str, int] = {item["item_id"]: 0 for item in items}
    dependency_warnings: list[str] = []

    for item in items:
        item_id = item["item_id"]
        for dep in item.get("dependencies", []):
            dep_id = str(dep).strip()
            if not dep_id:
                continue
            if dep_id not in known_ids:
                dependency_warnings.append(
                    f"Item '{item_id}' depends on missing item '{dep_id}'."
                )
                continue
            if dep_id not in graph:
                continue
            if item_id in graph[dep_id]:
                continue
            graph[dep_id].add(item_id)
            indegree[item_id] += 1

    queue = deque(sorted([item_id for item_id, degree in indegree.items() if degree == 0]))
    ordered: list[str] = []

    while queue:
        current = queue.popleft()
        ordered.append(current)
        for nxt in sorted(graph[current]):
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                queue.append(nxt)

    cycle_warnings: list[str] = []
    if len(ordered) != len(items):
        remaining = sorted([item_id for item_id in item_ids if item_id not in ordered])
        ordered.extend(remaining)
        cycle_warnings.append(
            "Circular dependency detected among queue items: " + ", ".join(remaining)
        )

    return ordered, cycle_warnings, dependency_warnings


def _detect_blocked_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = {item["item_id"]: item for item in items}
    blocked: list[dict[str, Any]] = []
    for item in items:
        unresolved_blockers: list[dict[str, Any]] = []
        for blocker in item.get("blocked_by", []):
            blocker_id = str(blocker).strip()
            if not blocker_id:
                continue
            blocker_item = by_id.get(blocker_id)
            if blocker_item is None:
                unresolved_blockers.append(
                    {"item_id": blocker_id, "reason": "missing_blocker_item", "status": "unknown"}
                )
                continue
            blocker_status = str(blocker_item.get("status", "")).strip()
            if blocker_status not in _RESOLVED_QUEUE_STATUSES:
                unresolved_blockers.append(
                    {
                        "item_id": blocker_id,
                        "reason": "blocker_not_resolved",
                        "status": blocker_status,
                    }
                )

        if unresolved_blockers:
            blocked.append(
                {
                    "item_id": item.get("item_id"),
                    "project_id": item.get("project_id"),
                    "repo_id": item.get("repo_id"),
                    "status": item.get("status"),
                    "blocked_by": unresolved_blockers,
                }
            )

    return blocked


def _build_handoff_prompts(assignments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    prompts: list[dict[str, Any]] = []
    for assignment in assignments:
        prompt_lines = [
            f"agent role/name: {assignment.get('recommended_agent_role')} / {assignment.get('recommended_agent_name')}",
            f"project_id: {assignment.get('project_id')}",
            f"repo_id: {assignment.get('repo_id')}",
            f"item_id: {assignment.get('item_id')}",
            f"title: {assignment.get('title', '')}",
            f"description: {assignment.get('description', '')}",
            "constraints:",
        ]
        constraints = assignment.get("constraints", [])
        if isinstance(constraints, list) and constraints:
            for constraint in constraints:
                prompt_lines.append(f"- {constraint}")
        else:
            prompt_lines.append("- preserve local-only and plan-only operation")

        prompt_lines.extend(
            [
                f"expected output: {assignment.get('expected_output')}",
                "local-only boundaries: local planning and local file changes only, no execution orchestration",
                "Do not make any GitHub/API/LLM/network calls unless later explicitly allowed.",
            ]
        )

        prompts.append(
            {
                "item_id": assignment.get("item_id"),
                "agent_id": assignment.get("recommended_agent_id"),
                "agent_role": assignment.get("recommended_agent_role"),
                "prompt": "\n".join(prompt_lines),
            }
        )
    return prompts


def _build_next_actions(
    *,
    filtered_items: list[dict[str, Any]],
    assignments: list[dict[str, Any]],
    blocked_items: list[dict[str, Any]],
    unassigned_items: list[dict[str, Any]],
    warnings: list[str],
) -> list[str]:
    actions = [
        "Review recommended assignments and confirm ownership per queue item.",
        "Use generated handoff prompts to prepare copy/paste local instructions per assigned item.",
    ]
    if blocked_items:
        actions.append("Resolve blocked_by dependencies before scheduling blocked items.")
    if unassigned_items:
        actions.append("Register or activate additional agent profiles for unassigned work items.")
    if not filtered_items:
        actions.append("No queue items matched current filters; adjust filters or add queue items.")
    if warnings:
        actions.append("Address risk warnings, then regenerate plan-agent-orchestration for an updated plan.")
    return actions


def _render_markdown(payload: dict[str, Any]) -> str:
    lines: list[str] = [
        "# AresForge Local Agent Orchestration Plan",
        "",
        f"- generated_at: {payload.get('generated_at')}",
        f"- local_only: {payload.get('local_only')}",
        f"- plan_only: {payload.get('plan_only')}",
        "",
        "## Filters",
        f"- project_id: {payload.get('filters', {}).get('project_id')}",
        f"- repo_id: {payload.get('filters', {}).get('repo_id')}",
        f"- status: {payload.get('filters', {}).get('status')}",
        "",
        "## Input Files",
    ]
    input_files = payload.get("input_files", {})
    if isinstance(input_files, dict):
        for name in ("queue", "profiles", "registry"):
            record = input_files.get(name)
            if not isinstance(record, dict):
                continue
            lines.append(
                f"- {name}: path={record.get('path')} exists={record.get('exists')} provided={record.get('provided')}"
            )

    lines.extend(["", "## Selected Work Items"])
    selected = payload.get("selected_work_items", [])
    if isinstance(selected, list) and selected:
        for item in selected:
            lines.append(
                f"- {item.get('item_id')} | type={item.get('item_type')} | status={item.get('status')} | agent={item.get('assigned_agent') or 'unassigned'}"
            )
    else:
        lines.append("- None")

    lines.extend(["", "## Recommended Assignments"])
    assignments = payload.get("recommended_assignments", [])
    if isinstance(assignments, list) and assignments:
        for item in assignments:
            lines.append(
                f"- {item.get('item_id')} -> {item.get('recommended_agent_id')} ({item.get('recommended_agent_role')}) source={item.get('assignment_source')}"
            )
    else:
        lines.append("- None")

    lines.extend(["", "## Dependency Order"])
    order = payload.get("dependency_order", [])
    if isinstance(order, list) and order:
        for item_id in order:
            lines.append(f"- {item_id}")
    else:
        lines.append("- None")

    lines.extend(["", "## Blocked Items"])
    blocked = payload.get("blocked_items", [])
    if isinstance(blocked, list) and blocked:
        for item in blocked:
            blockers = item.get("blocked_by", [])
            if isinstance(blockers, list):
                blocker_text = ", ".join(
                    f"{entry.get('item_id')}({entry.get('status')}:{entry.get('reason')})"
                    for entry in blockers
                    if isinstance(entry, dict)
                )
            else:
                blocker_text = ""
            lines.append(f"- {item.get('item_id')} blocked_by={blocker_text}")
    else:
        lines.append("- None")

    lines.extend(["", "## Unassigned Items"])
    unassigned = payload.get("unassigned_items", [])
    if isinstance(unassigned, list) and unassigned:
        for item in unassigned:
            lines.append(f"- {item.get('item_id')} reason={item.get('reason')}")
    else:
        lines.append("- None")

    lines.extend(["", "## Risk Warnings"])
    warnings = payload.get("risk_warnings", [])
    if isinstance(warnings, list) and warnings:
        lines.extend(f"- {warning}" for warning in warnings)
    else:
        lines.append("- None")

    lines.extend(["", "## Next Actions"])
    next_actions = payload.get("next_actions", [])
    if isinstance(next_actions, list) and next_actions:
        lines.extend(f"- {action}" for action in next_actions)
    else:
        lines.append("- None")

    lines.extend(["", "## Boundary Confirmations"])
    boundary = payload.get("boundary_confirmations", [])
    if isinstance(boundary, list) and boundary:
        lines.extend(f"- {entry}" for entry in boundary)
    else:
        lines.append("- None")

    return "\n".join(lines)


def _expected_output_for_item_type(item_type: str) -> str:
    if item_type == "documentation":
        return "updated documentation patch and short reconciliation summary"
    if item_type == "validation":
        return "targeted validation report with pass/fail details"
    if item_type == "handoff":
        return "copy/paste handoff packet with next-step instructions"
    if item_type == "orchestration":
        return "refined sequencing plan and dependency notes"
    if item_type in {"bug", "feature", "dashboard"}:
        return "code change set with targeted tests"
    if item_type == "sync":
        return "plan-only sync checklist and risk notes"
    return "scoped local deliverable with validation notes"


def _as_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for entry in value:
        normalized = str(entry).strip()
        if normalized and normalized not in result:
            result.append(normalized)
    return result


def _error(error: str, details: dict[str, Any], payload: dict[str, Any] | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "command": COMMAND_NAME,
        "ok": False,
        "local_only": True,
        "plan_only": True,
        "error": error,
        "details": details,
    }
    if payload is not None:
        result["payload"] = payload
    return result
