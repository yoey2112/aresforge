from __future__ import annotations

from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.local_agent_profiles import agent_profiles_summary_for_handoff
from aresforge.operator.local_project_queue import project_queue_summary_for_handoff
from aresforge.operator.managed_project_registry_local import managed_project_registry_summary_for_handoff

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
        "docs": docs,
        "present_count": len([item for item in docs if item["exists"]]),
        "missing_count": len(missing),
        "missing": missing,
        "warnings": [f"Missing key doc: {path}" for path in missing],
    }


def summarize_local_project_dashboard(config: AppConfig) -> dict[str, Any]:
    warnings: list[str] = []

    project_count = 0
    repo_count = 0
    queue_status_counts: dict[str, int] = {}
    agent_count = 0
    handoff_target_count = 0

    registry_summary = managed_project_registry_summary_for_handoff(config)
    if registry_summary is None:
        warnings.append("Managed project registry not found. Initialize with init-managed-project-registry.")
    elif isinstance(registry_summary, dict) and registry_summary.get("error"):
        warnings.append(
            "Managed project registry exists but could not be parsed. "
            + str(registry_summary.get("error", "unknown_error"))
        )
    else:
        project_count = int(registry_summary.get("project_count", 0))
        repo_count = int(registry_summary.get("repo_count", 0))

    queue_summary = project_queue_summary_for_handoff(config)
    if queue_summary is None:
        warnings.append("Project queue not found. Initialize with init-project-queue.")
    elif isinstance(queue_summary, dict) and queue_summary.get("error"):
        warnings.append(
            "Project queue exists but could not be parsed. "
            + str(queue_summary.get("error", "unknown_error"))
        )
    else:
        queue_status_counts = dict(queue_summary.get("status_counts", {}))

    agent_summary = agent_profiles_summary_for_handoff(config)
    if agent_summary is None:
        warnings.append("Agent profiles not found. Initialize with init-agent-profiles.")
    elif isinstance(agent_summary, dict) and agent_summary.get("error"):
        warnings.append(
            "Agent profiles exist but could not be parsed. "
            + str(agent_summary.get("error", "unknown_error"))
        )
    else:
        agent_count = int(agent_summary.get("agent_count", 0))
        handoff_target_count = int(agent_summary.get("handoff_target_count", 0))

    docs_status = summarize_docs_status(config.repo_root)
    warnings.extend(list(docs_status.get("warnings", [])))

    next_actions: list[str] = []
    readiness_hints: list[str] = []
    if project_count == 0:
        next_actions.append("Register at least one managed project and repo.")
        readiness_hints.append("Project management: initialize the managed project registry and add a project.")
    else:
        readiness_hints.append("Project management: ready.")
    if repo_count == 0:
        readiness_hints.append("Repo management: register at least one repo under a project.")
    else:
        readiness_hints.append("Repo management: ready.")
    if not queue_status_counts:
        next_actions.append("Initialize local project queue to track work items.")
        readiness_hints.append("Queue management: initialize queue and add at least one item.")
    else:
        readiness_hints.append("Queue management: ready.")
    if agent_count == 0:
        next_actions.append("Initialize agent profiles for handoff/orchestration planning.")
    if handoff_target_count == 0:
        next_actions.append("Register at least one handoff target for escalation and handoff routing.")
    if int(docs_status.get("missing_count", 0)) > 0:
        next_actions.append("Restore missing source-of-truth docs used by local planning.")
    if not next_actions:
        next_actions.append("Continue with M38 screens for project/repo/queue workflows.")

    orchestration_readiness_hint = (
        "ready" if queue_status_counts and agent_count > 0 else "needs queue items and active agent profiles"
    )
    escalation_readiness_hint = (
        "ready"
        if queue_status_counts and (agent_count > 0 or handoff_target_count > 0)
        else "needs queue context and handoff/agent metadata"
    )

    return {
        "local_only": True,
        "report_only": True,
        "project_count": project_count,
        "repo_count": repo_count,
        "queue_status_counts": queue_status_counts,
        "agent_count": agent_count,
        "handoff_target_count": handoff_target_count,
        "docs_status": docs_status,
        "warnings": sorted(set(warnings)),
        "next_recommended_actions": next_actions,
        "project_management_readiness": readiness_hints,
        "orchestration_readiness_hint": orchestration_readiness_hint,
        "escalation_readiness_hint": escalation_readiness_hint,
        "plan_only_boundary_hints": [
            "Orchestration remains plan-only and does not execute agents.",
            "Escalation remains plan-only and does not invoke local/cloud/Codex/ChatGPT/Ollama models.",
            "Handoff preview is local-only and does not post anywhere.",
        ],
        "boundary_confirmations": [
            "Local-first control-plane summary only.",
            "No GitHub calls.",
            "No gh calls.",
            "No network service calls.",
            "No local LLM calls.",
            "No cloud LLM calls.",
            "No Codex calls.",
            "No ChatGPT calls.",
            "No Ollama calls.",
            "No external API calls.",
            "No agent execution.",
            "No live GitHub sync.",
        ],
    }
