from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.local_agent_orchestration import (
    DEFAULT_OUTPUT_DIR as ORCHESTRATION_OUTPUT_DIR,
    generate_agent_orchestration_plan,
)
from aresforge.operator.local_agent_profiles import (
    resolve_agent_profiles_path,
)
from aresforge.operator.local_handoff_package import generate_handoff_package
from aresforge.operator.local_llm_escalation import (
    DEFAULT_OUTPUT_DIR as ESCALATION_OUTPUT_DIR,
    generate_llm_escalation_plan,
)
from aresforge.operator.local_project_queue import resolve_project_queue_path
from aresforge.operator.managed_project_registry_local import resolve_managed_project_registry_path

KEY_DOCS: tuple[str, ...] = (
    "docs/context/BUILD_STATE.md",
    "docs/context/AGENT_CONTEXT.md",
    "docs/roadmap/ROADMAP.md",
    "docs/architecture/RUNNABLE_SKELETON.md",
    "docs/operator/LOCAL_OPERATOR_USAGE.md",
)


def summarize_docs_status(repo_root: Path) -> dict[str, Any]:
    docs: list[dict[str, Any]] = []
    missing: list[str] = []
    for relative_path in KEY_DOCS:
        exists = (repo_root / relative_path).exists()
        docs.append({"path": relative_path, "exists": exists})
        if not exists:
            missing.append(relative_path)

    return {
        "local_only": True,
        "report_only": True,
        "source_of_truth_docs": list(KEY_DOCS),
        "docs": docs,
        "present_count": len([item for item in docs if item["exists"]]),
        "missing_count": len(missing),
        "missing": missing,
        "missing_docs": missing,
        "docs_ready": not missing,
        "warnings": [f"Missing key doc: {path}" for path in missing],
    }


def _count_by(items: list[dict[str, Any]], field: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        value = str(item.get(field, "")).strip() or "unknown"
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def _is_linked(owner: Any, repo: Any, url: Any) -> bool:
    return bool(str(owner or '').strip() and str(repo or '').strip() and str(url or '').strip())


def _load_json_file(path: Path, *, label: str, warnings: list[str]) -> dict[str, Any] | None:
    if not path.exists():
        warnings.append(f"{label} not found: {path}")
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        warnings.append(f"{label} could not be parsed: {exc}")
        return None
    if not isinstance(raw, dict):
        warnings.append(f"{label} has invalid schema; expected JSON object.")
        return None
    return raw


def _latest_artifact(path: Path) -> str | None:
    if not path.exists() or not path.is_dir():
        return None
    latest: Path | None = None
    latest_mtime: float = -1
    for candidate in path.rglob("*"):
        if not candidate.is_file():
            continue
        try:
            mtime = candidate.stat().st_mtime
        except OSError:
            continue
        if mtime > latest_mtime:
            latest = candidate
            latest_mtime = mtime
    return str(latest) if latest is not None else None


def _operator_workflows() -> list[dict[str, Any]]:
    return [
        {
            "workflow_id": "start-new-project",
            "title": "Start new project",
            "description": "Create or update a local managed project entry and establish baseline metadata.",
            "related_hub_section": "Projects",
            "required_inputs": ["project_id", "name", "root_path"],
            "local_only": True,
            "execution_status": "report_only",
            "notes": "Creates local registry metadata only; no network calls.",
        },
        {
            "workflow_id": "add-repo-to-project",
            "title": "Add repo to project",
            "description": "Register a repository under a managed project for local planning and tracking.",
            "related_hub_section": "Repos",
            "required_inputs": ["project_id", "repo_id", "name", "path"],
            "local_only": True,
            "execution_status": "report_only",
            "notes": "Adds repo metadata only; does not clone, sync, or call GitHub.",
        },
        {
            "workflow_id": "add-queue-item",
            "title": "Add queue item",
            "description": "Capture work as local queue items with status, priority, and dependency fields.",
            "related_hub_section": "Queue",
            "required_inputs": ["item_id", "project_id", "repo_id", "title"],
            "local_only": True,
            "execution_status": "report_only",
            "notes": "Queue state is local file-backed planning data.",
        },
        {
            "workflow_id": "assign-agent",
            "title": "Assign agent",
            "description": "Link queue items to local agent profiles for orchestration and escalation planning.",
            "related_hub_section": "Agents",
            "required_inputs": ["item_id", "assigned_agent"],
            "local_only": True,
            "execution_status": "report_only",
            "notes": "Assignments are metadata only; no agent execution occurs.",
        },
        {
            "workflow_id": "generate-handoff-preview",
            "title": "Generate handoff preview",
            "description": "Render a local handoff preview package for operator review.",
            "related_hub_section": "Handoff",
            "required_inputs": ["local state files"],
            "local_only": True,
            "execution_status": "report_only",
            "notes": "Preview does not post to GitHub or any external service.",
        },
        {
            "workflow_id": "generate-orchestration-plan",
            "title": "Generate orchestration plan",
            "description": "Build plan-only recommendations for assignment, dependency ordering, and risk handling.",
            "related_hub_section": "Orchestration",
            "required_inputs": ["queue", "agent profiles", "registry"],
            "local_only": True,
            "execution_status": "plan_only",
            "notes": "No agents or models are executed.",
        },
        {
            "workflow_id": "generate-escalation-plan",
            "title": "Generate escalation plan",
            "description": "Classify items into local_llm/codex/cloud/human/blocked buckets for operator routing.",
            "related_hub_section": "Escalation",
            "required_inputs": ["queue", "agent profiles"],
            "local_only": True,
            "execution_status": "plan_only",
            "notes": "No local/cloud/Codex/ChatGPT/Ollama invocation.",
        },
        {
            "workflow_id": "review-reports",
            "title": "Review reports",
            "description": "Inspect readiness, risks, and action-center guidance from local report endpoints.",
            "related_hub_section": "Reports",
            "required_inputs": ["dashboard report"],
            "local_only": True,
            "execution_status": "report_only",
            "notes": "Use export/copy action for local handoff notes.",
        },
        {
            "workflow_id": "prepare-final-validation",
            "title": "Prepare final validation",
            "description": "Review warnings, missing docs, and blocked items before final validation checks.",
            "related_hub_section": "Home",
            "required_inputs": ["action center", "readiness indicators"],
            "local_only": True,
            "execution_status": "operator_review_required",
            "notes": "Validation execution remains operator-triggered.",
        },
        {
            "workflow_id": "prepare-handoff-next-chat",
            "title": "Prepare handoff to next chat",
            "description": "Export local report JSON and handoff preview notes for continuity.",
            "related_hub_section": "Reports",
            "required_inputs": ["report export", "handoff preview"],
            "local_only": True,
            "execution_status": "report_only",
            "notes": "No external posting; local copy/export only.",
        },
    ]


def summarize_local_project_dashboard(config: AppConfig) -> dict[str, Any]:
    warnings: list[str] = []

    registry_path = resolve_managed_project_registry_path(config.repo_root, None)
    queue_path = resolve_project_queue_path(config.repo_root, None)
    agents_path = resolve_agent_profiles_path(config.repo_root, None)

    registry_data = _load_json_file(registry_path, label="Managed project registry", warnings=warnings)
    queue_data = _load_json_file(queue_path, label="Project queue", warnings=warnings)
    agents_data = _load_json_file(agents_path, label="Agent profiles", warnings=warnings)

    projects_raw = []
    repos_raw = []
    if isinstance(registry_data, dict):
        projects_raw = [item for item in registry_data.get("projects", []) if isinstance(item, dict)]
        for project in projects_raw:
            for repo in project.get("repos", []):
                if isinstance(repo, dict):
                    repos_raw.append(repo)

    queue_items = []
    if isinstance(queue_data, dict):
        queue_items = [item for item in queue_data.get("work_items", []) if isinstance(item, dict)]

    agents = []
    handoff_targets = []
    if isinstance(agents_data, dict):
        agents = [item for item in agents_data.get("agents", []) if isinstance(item, dict)]
        handoff_targets = [
            item for item in agents_data.get("handoff_targets", []) if isinstance(item, dict)
        ]

    project_summary = {
        "project_count": len(projects_raw),
        "counts_by_status": _count_by(projects_raw, "status"),
        "active_projects": [str(item.get("project_id", "")).strip() for item in projects_raw if str(item.get("status", "")).strip() == "active"],
        "paused_projects": [str(item.get("project_id", "")).strip() for item in projects_raw if str(item.get("status", "")).strip() == "paused"],
        "archived_projects": [str(item.get("project_id", "")).strip() for item in projects_raw if str(item.get("status", "")).strip() == "archived"],
        "planned_projects": [str(item.get("project_id", "")).strip() for item in projects_raw if str(item.get("status", "")).strip() == "planned"],
    }

    repo_summary = {
        "repo_count": len(repos_raw),
        "counts_by_status": _count_by(repos_raw, "status"),
        "counts_by_role": _count_by(repos_raw, "role"),
    }

    projects_missing_github_link = [
        str(item.get("project_id", "")).strip()
        for item in projects_raw
        if not _is_linked(item.get("github_owner"), item.get("github_repo"), item.get("github_url"))
    ]
    repos_missing_github_link = [
        str(item.get("repo_id", "")).strip()
        for item in repos_raw
        if not _is_linked(item.get("github_owner"), item.get("github_repo"), item.get("github_url"))
    ]
    missing_primary_repo_projects = [
        str(item.get("project_id", "")).strip()
        for item in projects_raw
        if len([repo for repo in item.get("repos", []) if isinstance(repo, dict)]) > 0
        and not str(item.get("primary_repo_id", "")).strip()
    ]
    github_warnings = [
        f"Project missing GitHub link: {project_id}" for project_id in projects_missing_github_link
    ] + [
        f"Repo missing GitHub link: {repo_id}" for repo_id in repos_missing_github_link
    ] + [
        f"Project missing primary repo: {project_id}" for project_id in missing_primary_repo_projects
    ]

    github_summary = {
        "linked_project_count": len(projects_raw) - len(projects_missing_github_link),
        "linked_repo_count": len(repos_raw) - len(repos_missing_github_link),
        "unlinked_project_count": len(projects_missing_github_link),
        "unlinked_repo_count": len(repos_missing_github_link),
        "missing_primary_repo_count": len(missing_primary_repo_projects),
        "projects_missing_github_link": projects_missing_github_link,
        "repos_missing_github_link": repos_missing_github_link,
        "warnings": github_warnings,
    }

    blocked_items = [
        {
            "item_id": str(item.get("item_id", "")).strip(),
            "title": str(item.get("title", "")).strip(),
            "status": str(item.get("status", "")).strip(),
        }
        for item in queue_items
        if str(item.get("status", "")).strip() == "blocked" or bool(item.get("blocked_by"))
    ]
    ready_items = [str(item.get("item_id", "")).strip() for item in queue_items if str(item.get("status", "")).strip() == "ready"]
    in_progress_items = [
        str(item.get("item_id", "")).strip()
        for item in queue_items
        if str(item.get("status", "")).strip() == "in_progress"
    ]
    high_priority_items = [
        str(item.get("item_id", "")).strip()
        for item in queue_items
        if str(item.get("priority", "")).strip() == "high"
    ]
    urgent_items = [
        str(item.get("item_id", "")).strip()
        for item in queue_items
        if str(item.get("priority", "")).strip() == "urgent"
    ]
    recently_completed_items = [
        {
            "item_id": str(item.get("item_id", "")).strip(),
            "title": str(item.get("title", "")).strip(),
            "updated_at": str(item.get("updated_at", "")).strip(),
        }
        for item in sorted(queue_items, key=lambda value: str(value.get("updated_at", "")), reverse=True)
        if str(item.get("status", "")).strip() in {"done", "cancelled"}
    ][:10]

    queue_summary = {
        "item_count": len(queue_items),
        "counts_by_status": _count_by(queue_items, "status"),
        "counts_by_priority": _count_by(queue_items, "priority"),
        "counts_by_type": _count_by(queue_items, "item_type"),
        "blocked_items": blocked_items,
        "ready_items": ready_items,
        "in_progress_items": in_progress_items,
        "high_priority_items": high_priority_items,
        "urgent_items": urgent_items,
        "recently_completed_items": recently_completed_items,
    }

    agent_summary = {
        "agent_count": len(agents),
        "handoff_target_count": len(handoff_targets),
        "counts_by_role": _count_by(agents, "role"),
        "counts_by_execution_mode": _count_by(agents, "execution_mode"),
        "counts_by_status": _count_by(agents, "status"),
        "escalation_enabled_count": len([item for item in agents if bool(item.get("escalation_allowed", False))]),
    }

    handoff_warnings: list[str] = []
    handoff_preview_available = False
    handoff_result = generate_handoff_package(
        config,
        output=None,
        output_format="markdown",
        include_doc_excerpts=False,
    )
    if bool(handoff_result.get("ok", False)):
        handoff_preview_available = bool(str(handoff_result.get("stdout", "")).strip())
    else:
        handoff_warnings.append(
            str(handoff_result.get("details", {}).get("message", handoff_result.get("error", "handoff_preview_failed")))
        )

    handoff_summary = {
        "handoff_available": True,
        "handoff_preview_available": handoff_preview_available,
        "latest_handoff_artifact": _latest_artifact(config.artifact_root / "handoff")
        or _latest_artifact(config.codex_handoffs_dir),
        "warnings": sorted(set(handoff_warnings)),
    }

    orchestration_warnings: list[str] = []
    orchestration_assigned_count = 0
    orchestration_unassigned_count = 0
    orchestration_blocked_count = 0
    orchestration_risk_count = 0
    orchestration_result = generate_agent_orchestration_plan(config, output_format="json")
    if bool(orchestration_result.get("ok", False)):
        orchestration_payload = orchestration_result.get("payload", {})
        if isinstance(orchestration_payload, dict):
            recommendations = orchestration_payload.get("recommended_assignments", [])
            unassigned = orchestration_payload.get("unassigned_items", [])
            blocked = orchestration_payload.get("blocked_items", [])
            risks = orchestration_payload.get("risk_warnings", [])
            orchestration_assigned_count = len(
                [item for item in recommendations if isinstance(item, dict) and str(item.get("recommended_agent_id", "")).strip()]
            )
            orchestration_unassigned_count = len(unassigned) if isinstance(unassigned, list) else 0
            orchestration_blocked_count = len(blocked) if isinstance(blocked, list) else 0
            orchestration_risk_count = len(risks) if isinstance(risks, list) else 0
            if isinstance(risks, list):
                orchestration_warnings.extend(str(item) for item in risks)
    else:
        orchestration_warnings.append(
            str(
                orchestration_result.get("details", {}).get(
                    "message", orchestration_result.get("error", "orchestration_plan_failed")
                )
            )
        )

    orchestration_summary = {
        "orchestration_available": True,
        "assigned_count": orchestration_assigned_count,
        "unassigned_count": orchestration_unassigned_count,
        "blocked_count": orchestration_blocked_count,
        "risk_count": orchestration_risk_count,
        "latest_orchestration_artifact": _latest_artifact(config.repo_root / ORCHESTRATION_OUTPUT_DIR),
        "warnings": sorted(set(orchestration_warnings)),
    }

    escalation_warnings: list[str] = []
    escalation_result = generate_llm_escalation_plan(config, output_format="json")
    escalation_counts = {
        "local_llm_suitable_count": 0,
        "codex_suitable_count": 0,
        "cloud_llm_recommended_count": 0,
        "human_required_count": 0,
        "blocked_or_needs_clarification_count": 0,
    }
    if bool(escalation_result.get("ok", False)):
        escalation_payload = escalation_result.get("payload", {})
        if isinstance(escalation_payload, dict):
            escalation_counts = {
                "local_llm_suitable_count": len(escalation_payload.get("local_llm_suitable", []))
                if isinstance(escalation_payload.get("local_llm_suitable"), list)
                else 0,
                "codex_suitable_count": len(escalation_payload.get("codex_suitable", []))
                if isinstance(escalation_payload.get("codex_suitable"), list)
                else 0,
                "cloud_llm_recommended_count": len(escalation_payload.get("cloud_llm_recommended", []))
                if isinstance(escalation_payload.get("cloud_llm_recommended"), list)
                else 0,
                "human_required_count": len(escalation_payload.get("human_required", []))
                if isinstance(escalation_payload.get("human_required"), list)
                else 0,
                "blocked_or_needs_clarification_count": len(
                    escalation_payload.get("blocked_or_needs_clarification", [])
                )
                if isinstance(escalation_payload.get("blocked_or_needs_clarification"), list)
                else 0,
            }
            risks = escalation_payload.get("risk_warnings", [])
            if isinstance(risks, list):
                escalation_warnings.extend(str(item) for item in risks)
    else:
        escalation_warnings.append(
            str(
                escalation_result.get("details", {}).get(
                    "message", escalation_result.get("error", "escalation_plan_failed")
                )
            )
        )

    escalation_summary = {
        "escalation_available": True,
        **escalation_counts,
        "latest_escalation_artifact": _latest_artifact(config.repo_root / ESCALATION_OUTPUT_DIR),
        "warnings": sorted(set(escalation_warnings)),
    }

    docs_summary = summarize_docs_status(config.repo_root)

    missing_local_state_files = [
        str(path)
        for path in (registry_path, queue_path, agents_path)
        if not path.exists()
    ]
    missing_docs = list(docs_summary.get("missing_docs", []))

    recommended_next_actions: list[str] = []
    if project_summary["project_count"] == 0:
        recommended_next_actions.append("Register at least one managed project.")
    if repo_summary["repo_count"] == 0:
        recommended_next_actions.append("Register at least one repo under a managed project.")
    if queue_summary["item_count"] == 0:
        recommended_next_actions.append("Initialize or populate the local queue with at least one item.")
    if agent_summary["agent_count"] == 0:
        recommended_next_actions.append("Register local agent profiles for orchestration planning.")
    if agent_summary["handoff_target_count"] == 0:
        recommended_next_actions.append("Register at least one handoff target for escalation routing.")
    if missing_docs:
        recommended_next_actions.append("Restore missing source-of-truth docs.")
    if queue_summary["blocked_items"]:
        recommended_next_actions.append("Resolve blocked queue items and dependency blockers.")
    if github_summary["unlinked_project_count"] > 0:
        recommended_next_actions.append("Link projects to GitHub owner/repo/url metadata.")
    if github_summary["missing_primary_repo_count"] > 0:
        recommended_next_actions.append("Assign primary repo IDs for projects with repos.")
    if not recommended_next_actions:
        recommended_next_actions.append("Review reports and continue local plan-only workflows.")

    readiness_indicators = {
        "registry_ready": bool(project_summary["project_count"] > 0 and repo_summary["repo_count"] > 0),
        "queue_ready": bool(queue_summary["item_count"] > 0),
        "agents_ready": bool(agent_summary["agent_count"] > 0 and agent_summary["handoff_target_count"] > 0),
        "handoff_ready": bool(handoff_summary["handoff_preview_available"]),
        "orchestration_ready": bool(queue_summary["item_count"] > 0 and agent_summary["agent_count"] > 0),
        "escalation_ready": bool(queue_summary["item_count"] > 0 and (agent_summary["agent_count"] > 0 or agent_summary["handoff_target_count"] > 0)),
        "docs_ready": bool(docs_summary.get("docs_ready", False)),
        "github_links_ready": bool(
            github_summary["unlinked_project_count"] == 0
            and github_summary["unlinked_repo_count"] == 0
            and github_summary["missing_primary_repo_count"] == 0
        ),
        "hub_ready": False,
        "overall_status": "needs_attention",
    }
    readiness_indicators["hub_ready"] = bool(
        readiness_indicators["registry_ready"]
        and readiness_indicators["queue_ready"]
        and readiness_indicators["agents_ready"]
        and readiness_indicators["docs_ready"]
    )
    if readiness_indicators["hub_ready"] and not queue_summary["blocked_items"]:
        readiness_indicators["overall_status"] = "ready"
    elif queue_summary["blocked_items"]:
        readiness_indicators["overall_status"] = "blocked"

    action_center = {
        "blocked_work_items": blocked_items,
        "urgent_or_high_priority_items": sorted(
            set(queue_summary["urgent_items"] + queue_summary["high_priority_items"])
        ),
        "unassigned_queue_items": [
            str(item.get("item_id", "")).strip()
            for item in queue_items
            if not str(item.get("assigned_agent", "")).strip()
        ],
        "cloud_escalation_candidates": escalation_counts["cloud_llm_recommended_count"],
        "human_required_items": escalation_counts["human_required_count"],
        "missing_docs": missing_docs,
        "missing_local_state_files": missing_local_state_files,
        "projects_missing_github_link": projects_missing_github_link,
        "projects_missing_primary_repo": missing_primary_repo_projects,
        "repos_missing_github_identity": repos_missing_github_link,
        "local_git_inspection_warnings": github_summary["warnings"],
        "recommended_operator_actions": recommended_next_actions,
    }

    component_warnings = (
        list(docs_summary.get("warnings", []))
        + list(handoff_summary.get("warnings", []))
        + list(orchestration_summary.get("warnings", []))
        + list(escalation_summary.get("warnings", []))
        + list(github_summary.get("warnings", []))
    )
    warnings.extend(component_warnings)
    risks = sorted(
        set(
            list(orchestration_summary.get("warnings", []))
            + list(escalation_summary.get("warnings", []))
            + [
                "Blocked queue items require operator intervention."
                if queue_summary["blocked_items"]
                else ""
            ]
        )
    )
    risks = [item for item in risks if item]

    boundary_confirmations = [
        "Local-only reporting and workflow guidance.",
        "Report-only and plan-only surfaces.",
        "No agent execution.",
        "No model invocation.",
        "No local LLM calls.",
        "No cloud LLM calls.",
        "No Codex calls.",
        "No ChatGPT calls.",
        "No Ollama calls.",
        "No GitHub calls.",
        "No gh calls.",
        "No network service calls.",
        "No external API calls.",
        "No live GitHub sync.",
    ]

    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "local_only": True,
        "report_only": True,
        "project_summary": project_summary,
        "repo_summary": repo_summary,
        "github_summary": github_summary,
        "queue_summary": queue_summary,
        "agent_summary": agent_summary,
        "handoff_summary": handoff_summary,
        "orchestration_summary": orchestration_summary,
        "escalation_summary": escalation_summary,
        "docs_summary": {
            "source_of_truth_docs": list(KEY_DOCS),
            "docs_ready": bool(docs_summary.get("docs_ready", False)),
            "missing_docs": missing_docs,
            "present_count": docs_summary.get("present_count", 0),
            "missing_count": docs_summary.get("missing_count", 0),
            "docs": docs_summary.get("docs", []),
        },
        "readiness_indicators": readiness_indicators,
        "action_center": action_center,
        "warnings": sorted(set(warnings)),
        "risks": risks,
        "recommended_next_actions": recommended_next_actions,
        "operator_workflows": _operator_workflows(),
        "boundary_confirmations": boundary_confirmations,
        "paths": {
            "registry_path": str(registry_path),
            "queue_path": str(queue_path),
            "agents_path": str(agents_path),
        },
    }

    # Compatibility aliases for M37-M39 surfaces/tests that still read summary-era keys.
    report["project_count"] = project_summary["project_count"]
    report["repo_count"] = repo_summary["repo_count"]
    report["queue_status_counts"] = dict(queue_summary["counts_by_status"])
    report["agent_count"] = agent_summary["agent_count"]
    report["handoff_target_count"] = agent_summary["handoff_target_count"]
    report["docs_status"] = docs_summary
    report["next_recommended_actions"] = recommended_next_actions
    report["project_management_readiness"] = [
        f"Registry ready: {readiness_indicators['registry_ready']}",
        f"Queue ready: {readiness_indicators['queue_ready']}",
        f"Agents ready: {readiness_indicators['agents_ready']}",
        f"GitHub links ready: {readiness_indicators['github_links_ready']}",
        f"Docs ready: {readiness_indicators['docs_ready']}",
    ]
    report["orchestration_readiness_hint"] = (
        "ready" if readiness_indicators["orchestration_ready"] else "needs queue items and active agent profiles"
    )
    report["escalation_readiness_hint"] = (
        "ready"
        if readiness_indicators["escalation_ready"]
        else "needs queue context and handoff/agent metadata"
    )
    report["plan_only_boundary_hints"] = [
        "Orchestration remains plan-only and does not execute agents.",
        "Escalation remains plan-only and does not invoke local/cloud/Codex/ChatGPT/Ollama models.",
        "Handoff preview is local-only and does not post anywhere.",
    ]
    return report
