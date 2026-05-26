from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.local_agent_profiles import resolve_agent_profiles_path
from aresforge.operator.local_project_queue import resolve_project_queue_path

COMMAND_NAME = "plan-llm-escalation"
DEFAULT_OUTPUT_DIR = Path("artifacts") / "escalation"

_VAGUE_TEXT_VALUES = {
    "",
    "todo",
    "tbd",
    "n/a",
    "na",
    "fix",
    "update",
    "work item",
    "task",
}

_BLOCKED_STATUSES = {"blocked"}
_DONE_STATUSES = {"done", "cancelled"}
_ACTIVE_QUEUE_STATUSES = {"proposed", "ready", "in_progress", "blocked"}


def generate_llm_escalation_plan(
    config: AppConfig,
    *,
    item_id: str | None = None,
    project_id: str | None = None,
    repo_id: str | None = None,
    status: str | None = None,
    queue_path: str | Path | None = None,
    profiles_path: str | Path | None = None,
    orchestration_plan: str | Path | None = None,
    output: str | Path | None = None,
    output_format: str = "json",
    force: bool = False,
) -> dict[str, Any]:
    format_name = output_format.lower().strip()
    if format_name not in {"json", "markdown"}:
        return _error("invalid_format", {"format": output_format})

    resolved_queue_path = resolve_project_queue_path(config.repo_root, queue_path)
    resolved_profiles_path = resolve_agent_profiles_path(config.repo_root, profiles_path)
    resolved_orchestration_path = _resolve_optional_path(config.repo_root, orchestration_plan)

    warnings: list[str] = []
    input_files = {
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
        "orchestration_plan": {
            "path": str(resolved_orchestration_path) if resolved_orchestration_path is not None else None,
            "exists": bool(resolved_orchestration_path and resolved_orchestration_path.exists()),
            "provided": orchestration_plan is not None,
        },
    }

    queue_data = _load_json_object(resolved_queue_path, "queue", warnings)
    profiles_data = _load_json_object(resolved_profiles_path, "profiles", warnings)
    orchestration_data = _load_json_object(
        resolved_orchestration_path,
        "orchestration_plan",
        warnings,
    )

    items = _normalize_items(queue_data)
    selected_items = _apply_filters(
        items,
        item_id=item_id,
        project_id=project_id,
        repo_id=repo_id,
        status=status,
    )

    agents, targets = _normalize_profiles(profiles_data)
    orchestration_hints = _build_orchestration_hints(orchestration_data)

    classifications: list[dict[str, Any]] = []
    reasons_by_item: dict[str, list[str]] = {}
    handoff_by_item: dict[str, dict[str, Any]] = {}
    prompt_guidance: list[dict[str, Any]] = []

    for item in selected_items:
        classification, reasons = _classify_item(item, items, orchestration_hints)
        recommended = _recommend_handoff_target(
            item=item,
            classification=classification,
            agents=agents,
            targets=targets,
        )
        if recommended.get("warning"):
            warnings.append(str(recommended["warning"]))
            if classification != "blocked_or_needs_clarification":
                reasons = list(reasons) + ["No suitable handoff target was found for classification."]

        entry = {
            "item_id": item.get("item_id"),
            "project_id": item.get("project_id"),
            "repo_id": item.get("repo_id"),
            "classification": classification,
            "reasons": reasons,
        }
        classifications.append(entry)
        reasons_by_item[str(item.get("item_id"))] = reasons
        handoff_by_item[str(item.get("item_id"))] = recommended
        prompt_guidance.append(
            _build_prompt_guidance(
                item=item,
                classification=classification,
                reasons=reasons,
                recommendation=recommended,
            )
        )

    category_items = {
        "local_llm_suitable": [c for c in classifications if c["classification"] == "local_llm_suitable"],
        "codex_suitable": [c for c in classifications if c["classification"] == "codex_suitable"],
        "cloud_llm_recommended": [c for c in classifications if c["classification"] == "cloud_llm_recommended"],
        "human_required": [c for c in classifications if c["classification"] == "human_required"],
        "blocked_or_needs_clarification": [
            c for c in classifications if c["classification"] == "blocked_or_needs_clarification"
        ],
    }

    available_agents = sorted(agents, key=lambda value: value.get("agent_id", ""))
    recommended_handoff_targets = [
        {
            "item_id": item_id_key,
            **target,
        }
        for item_id_key, target in sorted(handoff_by_item.items(), key=lambda value: value[0])
    ]

    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "local_only": True,
        "plan_only": True,
        "filters": {
            "item_id": item_id,
            "project_id": project_id,
            "repo_id": repo_id,
            "status": status,
        },
        "input_files": input_files,
        "selected_work_items": selected_items,
        "available_agents": available_agents,
        "classifications": classifications,
        "local_llm_suitable": category_items["local_llm_suitable"],
        "codex_suitable": category_items["codex_suitable"],
        "cloud_llm_recommended": category_items["cloud_llm_recommended"],
        "human_required": category_items["human_required"],
        "blocked_or_needs_clarification": category_items["blocked_or_needs_clarification"],
        "escalation_reasons": reasons_by_item,
        "recommended_handoff_targets": recommended_handoff_targets,
        "prompt_guidance": prompt_guidance,
        "risk_warnings": sorted(set(warnings)),
        "next_actions": _build_next_actions(classifications, warnings),
        "boundary_confirmations": [
            "local-only escalation planning",
            "plan-only",
            "no LLM invocation",
            "no local LLM calls",
            "no cloud LLM calls",
            "no Codex execution",
            "no GitHub calls",
            "no gh calls",
            "no network calls",
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


def _resolve_optional_path(repo_root: Path, value: str | Path | None) -> Path | None:
    if value is None:
        return None
    path = Path(value)
    if not path.is_absolute():
        path = (repo_root / path).resolve()
    return path


def _load_json_object(path: Path | None, label: str, warnings: list[str]) -> dict[str, Any] | None:
    if path is None:
        return None
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


def _normalize_profiles(
    profiles_data: dict[str, Any] | None,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    if not isinstance(profiles_data, dict):
        return [], {}

    targets: dict[str, dict[str, Any]] = {}
    raw_targets = profiles_data.get("handoff_targets")
    if isinstance(raw_targets, list):
        for raw_target in raw_targets:
            if not isinstance(raw_target, dict):
                continue
            target_id = str(raw_target.get("target_id", "")).strip()
            if not target_id:
                continue
            targets[target_id] = {
                "target_id": target_id,
                "name": str(raw_target.get("name", "")).strip(),
                "target_type": str(raw_target.get("target_type", "")).strip(),
                "status": str(raw_target.get("status", "")).strip(),
            }

    agents: list[dict[str, Any]] = []
    raw_agents = profiles_data.get("agents")
    if isinstance(raw_agents, list):
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
                    "handoff_target_id": str(raw_agent.get("handoff_target_id", "")).strip(),
                    "escalation_allowed": bool(raw_agent.get("escalation_allowed", False)),
                }
            )
    return agents, targets


def _build_orchestration_hints(orchestration_data: dict[str, Any] | None) -> dict[str, Any]:
    hints: dict[str, Any] = {
        "blocked_item_ids": set(),
        "unassigned_item_ids": set(),
    }
    if not isinstance(orchestration_data, dict):
        return hints

    for item in orchestration_data.get("blocked_items", []):
        if isinstance(item, dict):
            item_id = str(item.get("item_id", "")).strip()
            if item_id:
                hints["blocked_item_ids"].add(item_id)
    for item in orchestration_data.get("unassigned_items", []):
        if isinstance(item, dict):
            item_id = str(item.get("item_id", "")).strip()
            if item_id:
                hints["unassigned_item_ids"].add(item_id)
    return hints


def _apply_filters(
    items: list[dict[str, Any]],
    *,
    item_id: str | None,
    project_id: str | None,
    repo_id: str | None,
    status: str | None,
) -> list[dict[str, Any]]:
    item_value = item_id.strip() if isinstance(item_id, str) and item_id.strip() else None
    project_value = project_id.strip() if isinstance(project_id, str) and project_id.strip() else None
    repo_value = repo_id.strip() if isinstance(repo_id, str) and repo_id.strip() else None
    status_value = status.strip() if isinstance(status, str) and status.strip() else None

    filtered: list[dict[str, Any]] = []
    for item in items:
        if item_value is not None and item.get("item_id") != item_value:
            continue
        if project_value is not None and item.get("project_id") != project_value:
            continue
        if repo_value is not None and item.get("repo_id") != repo_value:
            continue
        item_status = str(item.get("status", "")).strip().lower()
        if status_value is not None and item_status != status_value:
            continue
        if status_value is None and item_status not in _ACTIVE_QUEUE_STATUSES:
            continue
        filtered.append(item)
    return filtered


def _classify_item(
    item: dict[str, Any],
    all_items: list[dict[str, Any]],
    orchestration_hints: dict[str, Any],
) -> tuple[str, list[str]]:
    reasons: list[str] = []
    item_id = str(item.get("item_id", "")).strip()
    item_type = str(item.get("item_type", "other")).strip().lower() or "other"
    status = str(item.get("status", "")).strip().lower()
    title = str(item.get("title", "")).strip()
    description = str(item.get("description", "")).strip()
    summary_text = f"{title} {description} {' '.join(item.get('tags', []))} {item.get('notes', '')}".lower()

    missing_context = (
        not item_id
        or not str(item.get("project_id", "")).strip()
        or not str(item.get("repo_id", "")).strip()
    )
    unresolved_deps = _has_unresolved_dependencies(item, all_items)
    vague_scope = _is_vague_scope(title, description)
    blocked_hint = item_id in orchestration_hints.get("blocked_item_ids", set())
    unassigned_hint = item_id in orchestration_hints.get("unassigned_item_ids", set())

    if missing_context:
        reasons.append("Required project/repo/item context is missing.")
    if status in _BLOCKED_STATUSES:
        reasons.append("Item status is blocked.")
    if unresolved_deps:
        reasons.append("Dependencies are unresolved.")
    if vague_scope:
        reasons.append("Title/description is too vague for reliable planning.")
    if blocked_hint:
        reasons.append("Orchestration plan already marks this item as blocked.")
    if unassigned_hint and item_type in {"orchestration", "handoff"}:
        reasons.append("Orchestration plan shows missing ownership for this coordination work.")
    if reasons:
        return "blocked_or_needs_clarification", reasons

    if _needs_human(summary_text, item_type):
        return "human_required", ["Business, approval, access, or policy judgment is required."]

    if _recommend_cloud(summary_text, item_type):
        return "cloud_llm_recommended", [
            "High-reasoning synthesis or cross-scope planning is indicated; cloud escalation is advisory only."
        ]

    if _recommend_codex(summary_text, item_type):
        return "codex_suitable", ["Deterministic repository-local implementation/test work is indicated."]

    if _recommend_local_llm(summary_text, item_type):
        return "local_llm_suitable", ["Low-risk summarization, formatting, or documentation work is indicated."]

    return "codex_suitable", ["Defaulted to codex_suitable for scoped repo-local execution planning."]


def _recommend_handoff_target(
    *,
    item: dict[str, Any],
    classification: str,
    agents: list[dict[str, Any]],
    targets: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    preferred_modes: list[str] = []
    preferred_roles: list[str] = []
    if classification == "local_llm_suitable":
        preferred_modes = ["local_llm"]
        preferred_roles = ["local_llm", "documentation", "reviewer"]
    elif classification == "codex_suitable":
        preferred_modes = ["codex"]
        preferred_roles = ["implementer", "tester", "architect"]
    elif classification == "cloud_llm_recommended":
        preferred_modes = ["cloud_llm"]
        preferred_roles = ["cloud_llm", "architect", "coordinator"]
    elif classification == "human_required":
        preferred_modes = ["human", "manual"]
        preferred_roles = ["operator", "reviewer", "architect"]

    active_agents = [
        agent
        for agent in agents
        if str(agent.get("status", "")).strip() in {"", "active", "planned"}
    ]
    if classification == "cloud_llm_recommended":
        active_agents = [
            agent
            for agent in active_agents
            if str(agent.get("execution_mode", "")).strip() == "cloud_llm"
            or str(agent.get("role", "")).strip() == "cloud_llm"
        ]

    candidates = [
        agent
        for agent in active_agents
        if str(agent.get("execution_mode", "")).strip() in preferred_modes
        and _agent_accepts_item_type(agent, str(item.get("item_type", "other")))
    ]
    if not candidates and preferred_roles:
        candidates = [
            agent
            for agent in active_agents
            if str(agent.get("role", "")).strip() in preferred_roles
            and _agent_accepts_item_type(agent, str(item.get("item_type", "other")))
        ]

    chosen = sorted(candidates, key=lambda value: str(value.get("agent_id", "")))[0] if candidates else None
    if chosen is None:
        return {
            "classification": classification,
            "recommended_agent_id": None,
            "recommended_agent_name": None,
            "recommended_execution_mode": None,
            "recommended_target_id": None,
            "recommended_target_type": None,
            "warning": f"No recommended handoff target found for item '{item.get('item_id')}' with classification '{classification}'.",
        }

    target_id = str(chosen.get("handoff_target_id", "")).strip()
    target = targets.get(target_id) if target_id else None
    target_type = str(target.get("target_type", "")).strip() if isinstance(target, dict) else None
    warning: str | None = None
    if target_id and target is None:
        warning = (
            f"Agent '{chosen.get('agent_id')}' references missing handoff target '{target_id}'."
        )

    return {
        "classification": classification,
        "recommended_agent_id": chosen.get("agent_id"),
        "recommended_agent_name": chosen.get("name"),
        "recommended_execution_mode": chosen.get("execution_mode"),
        "recommended_target_id": target_id or None,
        "recommended_target_type": target_type,
        "warning": warning,
    }


def _agent_accepts_item_type(agent: dict[str, Any], item_type: str) -> bool:
    allowed = agent.get("allowed_item_types")
    if not isinstance(allowed, list) or not allowed:
        return True
    return item_type in {str(value).strip() for value in allowed}


def _build_prompt_guidance(
    *,
    item: dict[str, Any],
    classification: str,
    reasons: list[str],
    recommendation: dict[str, Any],
) -> dict[str, Any]:
    target_text = recommendation.get("recommended_target_id") or recommendation.get("recommended_agent_id")
    actor = recommendation.get("recommended_agent_name") or "operator"
    boundary = "local-only planning boundary"
    if classification == "cloud_llm_recommended":
        boundary = "advisory cloud escalation boundary (no cloud calls executed in M36)"
    elif classification == "human_required":
        boundary = "human approval boundary"

    safe_prompt = (
        "You are assisting with local-only, plan-only escalation preparation. "
        "Do not run commands, mutate external systems, or call network services."
    )

    required_context = [
        f"item_id={item.get('item_id')}",
        f"project_id={item.get('project_id')}",
        f"repo_id={item.get('repo_id')}",
        f"title={item.get('title')}",
        f"description={item.get('description')}",
        f"status={item.get('status')}",
        f"item_type={item.get('item_type')}",
    ]

    expected_output = {
        "local_llm_suitable": "Clean summary or formatted draft with clear local action checklist.",
        "codex_suitable": "Deterministic implementation plan with file-level changes and tests.",
        "cloud_llm_recommended": "Advisory architecture/design synthesis and tradeoff analysis only.",
        "human_required": "Explicit decision, approval, or policy direction recorded by operator.",
        "blocked_or_needs_clarification": "Clarifying questions and missing-context checklist.",
    }.get(classification, "Scoped plan guidance.")

    return {
        "item_id": item.get("item_id"),
        "classification": classification,
        "reason": reasons[0] if reasons else "No explicit reason captured.",
        "recommended_actor_or_target": target_text,
        "safe_prompt_starter": safe_prompt,
        "required_context_to_include": required_context,
        "expected_output": expected_output,
        "local_only_or_escalation_boundary": boundary,
        "external_call_policy": (
            "No external calls should be made unless later explicitly authorized."
        ),
        "recommended_actor": actor,
    }


def _build_next_actions(classifications: list[dict[str, Any]], warnings: list[str]) -> list[str]:
    if not classifications:
        return [
            "No queue items matched current filters; adjust filters or add queue items before re-planning.",
        ]

    actions = [
        "Review classification rationale per item and confirm intended escalation path.",
        "Use prompt_guidance entries as copy/paste-ready planning prompts for the selected target.",
    ]
    if any(item.get("classification") == "blocked_or_needs_clarification" for item in classifications):
        actions.append("Resolve missing context, blockers, and vague requirements before escalation.")
    if warnings:
        actions.append("Address risk warnings, then re-run plan-llm-escalation for an updated plan.")
    return actions


def _has_unresolved_dependencies(item: dict[str, Any], all_items: list[dict[str, Any]]) -> bool:
    dependency_ids = [value for value in _as_string_list(item.get("dependencies")) if value]
    if not dependency_ids:
        return False

    index = {str(entry.get("item_id", "")).strip(): entry for entry in all_items}
    for dep_id in dependency_ids:
        dep = index.get(dep_id)
        if dep is None:
            return True
        dep_status = str(dep.get("status", "")).strip().lower()
        if dep_status not in _DONE_STATUSES:
            return True
    return False


def _is_vague_scope(title: str, description: str) -> bool:
    title_value = title.strip().lower()
    description_value = description.strip().lower()
    if title_value in _VAGUE_TEXT_VALUES:
        return True
    if description_value in _VAGUE_TEXT_VALUES:
        return True
    if len(title_value) < 6 and len(description_value) < 12:
        return True
    return False


def _needs_human(summary_text: str, item_type: str) -> bool:
    if item_type in {"milestone"}:
        return True
    keywords = [
        "priority",
        "business",
        "approval",
        "legal",
        "ethic",
        "ethics",
        "policy",
        "secret",
        "credential",
        "access",
        "irreversible",
        "user preference",
        "manual decision",
    ]
    return any(token in summary_text for token in keywords)


def _recommend_cloud(summary_text: str, item_type: str) -> bool:
    if item_type in {"orchestration", "dashboard"}:
        return True
    keywords = [
        "architecture",
        "cross-project",
        "cross project",
        "cross-repo",
        "cross repo",
        "ambiguous",
        "tradeoff",
        "security",
        "data model",
        "schema design",
        "multi-agent",
        "long-context",
        "long context",
        "complex debugging",
        "deep synthesis",
    ]
    return any(token in summary_text for token in keywords)


def _recommend_codex(summary_text: str, item_type: str) -> bool:
    if item_type in {"feature", "bug", "task", "validation", "sync"}:
        return True
    keywords = [
        "implement",
        "refactor",
        "test",
        "cli",
        "operator",
        "module",
        "deterministic",
        "repo-local",
        "known files",
    ]
    return any(token in summary_text for token in keywords)


def _recommend_local_llm(summary_text: str, item_type: str) -> bool:
    if item_type in {"documentation", "handoff"}:
        return True
    keywords = [
        "documentation",
        "summar",
        "format",
        "cleanup",
        "draft",
        "low-risk",
        "local-only analysis",
    ]
    return any(token in summary_text for token in keywords)


def _as_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for entry in value:
        normalized = str(entry).strip()
        if normalized and normalized not in result:
            result.append(normalized)
    return result


def _render_markdown(payload: dict[str, Any]) -> str:
    lines: list[str] = [
        "# AresForge Local LLM Escalation Plan",
        "",
        f"- generated_at: {payload.get('generated_at')}",
        f"- local_only: {payload.get('local_only')}",
        f"- plan_only: {payload.get('plan_only')}",
        "",
        "## Filters",
        f"- item_id: {payload.get('filters', {}).get('item_id')}",
        f"- project_id: {payload.get('filters', {}).get('project_id')}",
        f"- repo_id: {payload.get('filters', {}).get('repo_id')}",
        f"- status: {payload.get('filters', {}).get('status')}",
        "",
        "## Classification Counts",
    ]

    for key in (
        "local_llm_suitable",
        "codex_suitable",
        "cloud_llm_recommended",
        "human_required",
        "blocked_or_needs_clarification",
    ):
        entries = payload.get(key, [])
        count = len(entries) if isinstance(entries, list) else 0
        lines.append(f"- {key}: {count}")

    lines.extend(["", "## Classifications"])
    classifications = payload.get("classifications", [])
    if isinstance(classifications, list) and classifications:
        for entry in classifications:
            lines.append(
                f"- {entry.get('item_id')} -> {entry.get('classification')} ({'; '.join(entry.get('reasons', []))})"
            )
    else:
        lines.append("- None")

    lines.extend(["", "## Recommended Handoff Targets"])
    recommended = payload.get("recommended_handoff_targets", [])
    if isinstance(recommended, list) and recommended:
        for entry in recommended:
            lines.append(
                "- "
                + f"{entry.get('item_id')} -> "
                + f"agent={entry.get('recommended_agent_id')} "
                + f"mode={entry.get('recommended_execution_mode')} "
                + f"target={entry.get('recommended_target_id')}"
            )
    else:
        lines.append("- None")

    lines.extend(["", "## Prompt Guidance"])
    guidance = payload.get("prompt_guidance", [])
    if isinstance(guidance, list) and guidance:
        for entry in guidance:
            lines.append(
                f"- {entry.get('item_id')} | {entry.get('classification')} | actor_or_target={entry.get('recommended_actor_or_target')}"
            )
    else:
        lines.append("- None")

    lines.extend(["", "## Risk Warnings"])
    warnings = payload.get("risk_warnings", [])
    if isinstance(warnings, list) and warnings:
        lines.extend(f"- {item}" for item in warnings)
    else:
        lines.append("- None")

    lines.extend(["", "## Next Actions"])
    actions = payload.get("next_actions", [])
    if isinstance(actions, list) and actions:
        lines.extend(f"- {item}" for item in actions)
    else:
        lines.append("- None")

    lines.extend(["", "## Boundary Confirmations"])
    boundary = payload.get("boundary_confirmations", [])
    if isinstance(boundary, list) and boundary:
        lines.extend(f"- {item}" for item in boundary)
    else:
        lines.append("- None")

    return "\n".join(lines)


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