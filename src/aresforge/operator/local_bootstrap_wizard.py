from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.local_agent_profiles import (
    _default_profiles,
    init_agent_profiles,
    register_agent_profile,
    register_handoff_target,
    resolve_agent_profiles_path,
)
from aresforge.operator.local_project_queue import add_queue_item, init_project_queue, resolve_project_queue_path
from aresforge.operator.local_project_state import init_project_state, resolve_project_state_path
from aresforge.operator.managed_project_registry_local import (
    init_managed_project_registry,
    inspect_local_git_repository,
    register_managed_project,
    register_managed_repo,
    resolve_managed_project_registry_path,
)

_SAMPLE_QUEUE_ITEMS: tuple[dict[str, str], ...] = (
    {
        "item_id": "m43-hub-stabilization",
        "item_type": "milestone",
        "status": "proposed",
        "priority": "high",
        "title": "Hub stabilization and UX cleanup",
    },
    {
        "item_id": "m44-controlled-execution-gates",
        "item_type": "milestone",
        "status": "proposed",
        "priority": "high",
        "title": "Controlled local execution gates",
    },
    {
        "item_id": "m45-github-sync-planning-ui",
        "item_type": "milestone",
        "status": "proposed",
        "priority": "normal",
        "title": "GitHub sync planning UI",
    },
    {
        "item_id": "m46-local-llm-integration-planning",
        "item_type": "milestone",
        "status": "proposed",
        "priority": "normal",
        "title": "Local LLM integration planning",
    },
)

_BASE_BOUNDARIES: tuple[str, ...] = (
    "Local-only bootstrap operation.",
    "File-backed local state only.",
    "No GitHub API calls.",
    "No gh calls.",
    "No GraphQL/REST calls.",
    "No network service calls.",
    "No local LLM calls.",
    "No cloud LLM calls.",
    "No Codex calls.",
    "No ChatGPT calls.",
    "No Ollama calls.",
    "No external API calls.",
)


def inspect_bootstrap_status(
    config: AppConfig,
    *,
    repo_path: str | Path | None = None,
) -> dict[str, Any]:
    resolved_repo = _resolve_repo_path(config, repo_path)
    snapshot = _bootstrap_snapshot(resolved_repo)
    return {
        "command": "inspect-bootstrap-status",
        "status_name": "bootstrap_status",
        "ok": True,
        "local_only": True,
        "repo_path": str(resolved_repo),
        "bootstrap_ready": bool(snapshot["bootstrap_ready"]),
        "files": snapshot["files"],
        "detected_project": snapshot["detected_project"],
        "detected_git": snapshot["detected_git"],
        "missing_files": snapshot["missing_files"],
        "initialized_files": [],
        "seeded_projects": snapshot["seeded_projects"],
        "seeded_repos": snapshot["seeded_repos"],
        "seeded_agents": snapshot["seeded_agents"],
        "seeded_handoff_targets": snapshot["seeded_handoff_targets"],
        "seeded_queue_items": snapshot["seeded_queue_items"],
        "warnings": snapshot["warnings"],
        "recommended_next_actions": snapshot["recommended_next_actions"],
        "boundary_confirmations": _boundary_confirmations(),
    }


def plan_bootstrap(
    config: AppConfig,
    *,
    repo_path: str | Path | None = None,
    seed_sample_work: bool = False,
    output_format: str = "json",
) -> dict[str, Any]:
    resolved_repo = _resolve_repo_path(config, repo_path)
    snapshot = _bootstrap_snapshot(resolved_repo)

    actions: list[dict[str, str]] = []
    would_initialize: list[str] = []
    would_seed_projects: list[str] = []
    would_seed_repos: list[str] = []
    would_seed_agents: list[str] = []
    would_seed_handoff_targets: list[str] = []
    would_seed_queue_items: list[str] = []

    if not snapshot["files"]["project_state"]:
        actions.append(_action("init_project_state", "Initialize local project state ledger."))
        would_initialize.append("project_state")
    if not snapshot["files"]["managed_project_registry"]:
        actions.append(_action("init_managed_project_registry", "Initialize local managed project registry."))
        would_initialize.append("managed_project_registry")
    if "aresforge" not in snapshot["seeded_projects"]:
        actions.append(_action("register_aresforge_project", "Register AresForge managed project metadata."))
        would_seed_projects.append("aresforge")
    if "aresforge" not in snapshot["seeded_repos"]:
        actions.append(_action("register_aresforge_repo", "Register AresForge primary managed repo metadata."))
        would_seed_repos.append("aresforge")
    if not snapshot["files"]["project_queue"]:
        actions.append(_action("init_project_queue", "Initialize local project queue storage."))
        would_initialize.append("project_queue")

    queue_has_items = bool(snapshot["seeded_queue_items"])
    if seed_sample_work or not queue_has_items:
        actions.append(
            _action(
                "seed_default_queue_items",
                "Seed default next-phase queue milestones when queue is empty or sample seeding is requested.",
            )
        )
        would_seed_queue_items.extend(item["item_id"] for item in _SAMPLE_QUEUE_ITEMS)

    if not snapshot["files"]["agent_profiles"]:
        actions.append(_action("init_agent_profiles", "Initialize local agent profiles storage."))
        would_initialize.append("agent_profiles")
    if not snapshot["seeded_handoff_targets"]:
        actions.append(_action("seed_default_handoff_targets", "Seed default handoff targets from M34 defaults."))
        would_seed_handoff_targets.append("default_set")
    if not snapshot["seeded_agents"]:
        actions.append(_action("seed_default_agent_profiles", "Seed default agent profiles from M34 defaults."))
        would_seed_agents.append("default_set")

    payload = {
        "generated_at": _now_iso(),
        "local_only": True,
        "plan_only": True,
        "repo_path": str(resolved_repo),
        "actions": actions,
        "would_initialize": sorted(set(would_initialize)),
        "would_seed_projects": sorted(set(would_seed_projects)),
        "would_seed_repos": sorted(set(would_seed_repos)),
        "would_seed_agents": sorted(set(would_seed_agents)),
        "would_seed_handoff_targets": sorted(set(would_seed_handoff_targets)),
        "would_seed_queue_items": sorted(set(would_seed_queue_items)),
        "warnings": snapshot["warnings"],
        "risks": [
            "Queue seeding only adds missing IDs and preserves existing items.",
            "Agent/profile seeding is idempotent and preserves existing entries.",
        ],
        "boundary_confirmations": _boundary_confirmations(plan_only=True),
    }
    return _stdout_result("plan-bootstrap", payload, output_format, _render_plan_markdown(payload))


def apply_bootstrap(
    config: AppConfig,
    *,
    repo_path: str | Path | None = None,
    force: bool = False,
    seed_sample_work: bool = False,
    output_format: str = "json",
) -> dict[str, Any]:
    resolved_repo = _resolve_repo_path(config, repo_path)
    effective_config = _config_for_repo(config, resolved_repo)
    before = _bootstrap_snapshot(resolved_repo)

    initialized_files: list[str] = []
    applied_actions: list[str] = []
    already_existing_actions: list[str] = []
    warnings: list[str] = list(before["warnings"])

    project_state_path = resolve_project_state_path(resolved_repo, None)
    registry_path = resolve_managed_project_registry_path(resolved_repo, None)
    queue_path = resolve_project_queue_path(resolved_repo, None)
    agents_path = resolve_agent_profiles_path(resolved_repo, None)

    if not project_state_path.exists():
        state_result = init_project_state(effective_config)
        if state_result.get("ok", False):
            initialized_files.append("project_state")
            applied_actions.append("init_project_state")
        else:
            warnings.append(str(state_result.get("details", {}).get("message", "Failed to initialize project state.")))
    else:
        already_existing_actions.append("init_project_state")

    if not registry_path.exists():
        registry_result = init_managed_project_registry(effective_config)
        if registry_result.get("ok", False):
            initialized_files.append("managed_project_registry")
            applied_actions.append("init_managed_project_registry")
        else:
            warnings.append(
                str(registry_result.get("details", {}).get("message", "Failed to initialize managed project registry."))
            )
    else:
        already_existing_actions.append("init_managed_project_registry")

    project_result = register_managed_project(
        effective_config,
        project_id="aresforge",
        name="AresForge",
        description="Local-first AI project control plane and Hub.",
        root_path=str(resolved_repo),
        status="active",
        default_branch="main",
        github_owner="yoey2112",
        github_repo="aresforge",
        github_url="https://github.com/yoey2112/aresforge",
        github_default_branch="main",
        primary_repo_id="aresforge",
    )
    if project_result.get("ok", False):
        if bool(project_result.get("created", False)):
            applied_actions.append("register_aresforge_project")
        else:
            already_existing_actions.append("register_aresforge_project")
        warnings.extend(project_result.get("warnings", []))
    else:
        warnings.append(str(project_result.get("details", {}).get("message", "Failed to register AresForge project.")))

    git_probe = inspect_local_git_repository(resolved_repo)
    remote_url = str(git_probe.get("local_git_remote_url", "")).strip() or "https://github.com/yoey2112/aresforge"
    repo_result = register_managed_repo(
        effective_config,
        project_id="aresforge",
        repo_id="aresforge",
        name="AresForge",
        path=str(resolved_repo),
        remote_url=remote_url,
        role="primary",
        status="active",
        default_branch="main",
        github_owner="yoey2112",
        github_repo="aresforge",
        github_url="https://github.com/yoey2112/aresforge",
        github_default_branch="main",
        inspect_local_git=True,
    )
    if repo_result.get("ok", False):
        if bool(repo_result.get("created", False)):
            applied_actions.append("register_aresforge_repo")
        else:
            already_existing_actions.append("register_aresforge_repo")
        warnings.extend(repo_result.get("warnings", []))
    else:
        warnings.append(str(repo_result.get("details", {}).get("message", "Failed to register AresForge repo.")))

    if not queue_path.exists():
        queue_result = init_project_queue(effective_config)
        if queue_result.get("ok", False):
            initialized_files.append("project_queue")
            applied_actions.append("init_project_queue")
        else:
            warnings.append(str(queue_result.get("details", {}).get("message", "Failed to initialize project queue.")))
    else:
        already_existing_actions.append("init_project_queue")

    queue_snapshot = _safe_json_obj(queue_path)
    current_items = queue_snapshot.get("work_items", []) if isinstance(queue_snapshot.get("work_items"), list) else []
    should_seed_queue = seed_sample_work or not current_items
    if should_seed_queue:
        for item in _SAMPLE_QUEUE_ITEMS:
            item_result = add_queue_item(
                effective_config,
                item_id=item["item_id"],
                project_id="aresforge",
                repo_id="aresforge",
                title=item["title"],
                status=item["status"],
                priority=item["priority"],
                item_type=item["item_type"],
                source="bootstrap",
            )
            if item_result.get("ok", False):
                if bool(item_result.get("created", False)):
                    applied_actions.append("seed_default_queue_items")
                else:
                    already_existing_actions.append("seed_default_queue_items")
            else:
                warnings.append(str(item_result.get("details", {}).get("message", "Failed to seed sample queue items.")))

    if not agents_path.exists():
        profiles_result = init_agent_profiles(effective_config, with_defaults=True)
        if profiles_result.get("ok", False):
            initialized_files.append("agent_profiles")
            applied_actions.extend(["init_agent_profiles", "seed_default_agent_profiles", "seed_default_handoff_targets"])
        else:
            warnings.append(str(profiles_result.get("details", {}).get("message", "Failed to initialize agent profiles.")))
    else:
        defaults = _default_profiles(with_defaults=True)
        for target in defaults.get("handoff_targets", []):
            if not isinstance(target, dict):
                continue
            seeded_target = register_handoff_target(
                effective_config,
                target_id=str(target.get("target_id", "")).strip(),
                name=str(target.get("name", "")).strip(),
                target_type=str(target.get("target_type", "")).strip() or "other",
                description=str(target.get("description", "")).strip(),
                local_command=str(target.get("local_command", "")).strip(),
                input_format=str(target.get("input_format", "")).strip(),
                output_format=str(target.get("output_format", "")).strip(),
                safety_notes=list(target.get("safety_notes", [])) if isinstance(target.get("safety_notes"), list) else [],
                status=str(target.get("status", "")).strip() or "active",
                tags=list(target.get("tags", [])) if isinstance(target.get("tags"), list) else [],
                notes=str(target.get("notes", "")).strip(),
            )
            if seeded_target.get("ok", False) and bool(seeded_target.get("created", False)):
                applied_actions.append("seed_default_handoff_targets")
            else:
                already_existing_actions.append("seed_default_handoff_targets")

        for agent in defaults.get("agents", []):
            if not isinstance(agent, dict):
                continue
            seeded_agent = register_agent_profile(
                effective_config,
                agent_id=str(agent.get("agent_id", "")).strip(),
                name=str(agent.get("name", "")).strip(),
                role=str(agent.get("role", "")).strip() or "other",
                description=str(agent.get("description", "")).strip(),
                execution_mode=str(agent.get("execution_mode", "")).strip() or "manual",
                model_preference=str(agent.get("model_preference", "")).strip(),
                strengths=list(agent.get("strengths", [])) if isinstance(agent.get("strengths"), list) else [],
                constraints=list(agent.get("constraints", [])) if isinstance(agent.get("constraints"), list) else [],
                allowed_item_types=list(agent.get("allowed_item_types", []))
                if isinstance(agent.get("allowed_item_types"), list)
                else [],
                escalation_allowed=bool(agent.get("escalation_allowed", False)),
                handoff_target_id=str(agent.get("handoff_target_id", "")).strip(),
                status=str(agent.get("status", "")).strip() or "active",
                tags=list(agent.get("tags", [])) if isinstance(agent.get("tags"), list) else [],
                notes=str(agent.get("notes", "")).strip(),
            )
            if seeded_agent.get("ok", False) and bool(seeded_agent.get("created", False)):
                applied_actions.append("seed_default_agent_profiles")
            else:
                already_existing_actions.append("seed_default_agent_profiles")

    if force:
        applied_actions.append("force_requested")

    after = _bootstrap_snapshot(resolved_repo)
    payload = {
        "command": "apply-bootstrap",
        "ok": True,
        "local_only": True,
        "repo_path": str(resolved_repo),
        "force": bool(force),
        "seed_sample_work": bool(seed_sample_work),
        "bootstrap_ready": bool(after["bootstrap_ready"]),
        "files": after["files"],
        "missing_files": after["missing_files"],
        "initialized_files": sorted(set(initialized_files)),
        "seeded_projects": after["seeded_projects"],
        "seeded_repos": after["seeded_repos"],
        "seeded_agents": after["seeded_agents"],
        "seeded_handoff_targets": after["seeded_handoff_targets"],
        "seeded_queue_items": after["seeded_queue_items"],
        "applied_actions": sorted(set(applied_actions)),
        "already_existing_actions": sorted(set(already_existing_actions)),
        "warnings": sorted(set(str(item) for item in warnings if str(item).strip())),
        "recommended_next_actions": after["recommended_next_actions"],
        "boundary_confirmations": _boundary_confirmations(),
    }
    return _stdout_result("apply-bootstrap", payload, output_format, _render_apply_markdown(payload))


def _bootstrap_snapshot(repo_path: Path) -> dict[str, Any]:
    project_state_path = resolve_project_state_path(repo_path, None)
    registry_path = resolve_managed_project_registry_path(repo_path, None)
    queue_path = resolve_project_queue_path(repo_path, None)
    agents_path = resolve_agent_profiles_path(repo_path, None)

    files = {
        "project_state": project_state_path.exists(),
        "managed_project_registry": registry_path.exists(),
        "project_queue": queue_path.exists(),
        "agent_profiles": agents_path.exists(),
    }
    missing_files = [name for name, exists in files.items() if not exists]

    warnings: list[str] = []
    seeded_projects: list[str] = []
    seeded_repos: list[str] = []
    seeded_agents: list[str] = []
    seeded_handoff_targets: list[str] = []
    seeded_queue_items: list[str] = []

    detected_project = {
        "project_id": repo_path.name.strip() or "aresforge",
        "name": "AresForge" if repo_path.name.strip().lower() == "aresforge" else repo_path.name.strip(),
        "repo_path": str(repo_path),
    }

    git_probe = inspect_local_git_repository(repo_path)
    detected_git = {
        "is_git_repo": bool(str(git_probe.get("local_git_head", "")).strip() or str(git_probe.get("local_git_remote_url", "")).strip()),
        "local_git_remote_url": str(git_probe.get("local_git_remote_url", "")).strip(),
        "local_git_branch": str(git_probe.get("local_git_branch", "")).strip(),
        "local_git_head": str(git_probe.get("local_git_head", "")).strip(),
        "github_owner": str(git_probe.get("github_owner", "")).strip(),
        "github_repo": str(git_probe.get("github_repo", "")).strip(),
        "github_url": str(git_probe.get("github_url", "")).strip(),
        "warnings": list(git_probe.get("warnings", [])) if isinstance(git_probe.get("warnings"), list) else [],
    }
    warnings.extend(detected_git["warnings"])

    registry_data = _safe_json_obj(registry_path)
    for project in registry_data.get("projects", []):
        if not isinstance(project, dict):
            continue
        project_id = str(project.get("project_id", "")).strip()
        if project_id:
            seeded_projects.append(project_id)
        for repo in project.get("repos", []):
            if isinstance(repo, dict):
                repo_id = str(repo.get("repo_id", "")).strip()
                if repo_id:
                    seeded_repos.append(repo_id)

    queue_data = _safe_json_obj(queue_path)
    for item in queue_data.get("work_items", []):
        if isinstance(item, dict):
            item_id = str(item.get("item_id", "")).strip()
            if item_id:
                seeded_queue_items.append(item_id)

    agent_data = _safe_json_obj(agents_path)
    for agent in agent_data.get("agents", []):
        if isinstance(agent, dict):
            agent_id = str(agent.get("agent_id", "")).strip()
            if agent_id:
                seeded_agents.append(agent_id)
    for target in agent_data.get("handoff_targets", []):
        if isinstance(target, dict):
            target_id = str(target.get("target_id", "")).strip()
            if target_id:
                seeded_handoff_targets.append(target_id)

    aresforge_project = _find_project(registry_data, "aresforge")
    aresforge_repo = _find_repo(registry_data, "aresforge", "aresforge")
    github_link_present = False
    if aresforge_project is not None:
        github_link_present = bool(
            str(aresforge_project.get("github_owner", "")).strip()
            and str(aresforge_project.get("github_repo", "")).strip()
            and str(aresforge_project.get("github_url", "")).strip()
        )
    if not github_link_present and aresforge_repo is not None:
        github_link_present = bool(
            str(aresforge_repo.get("github_owner", "")).strip()
            and str(aresforge_repo.get("github_repo", "")).strip()
            and str(aresforge_repo.get("github_url", "")).strip()
        )

    recommended_next_actions: list[str] = []
    if missing_files:
        recommended_next_actions.append("Run apply-bootstrap to initialize missing local state files.")
    if "aresforge" not in seeded_projects or "aresforge" not in seeded_repos:
        recommended_next_actions.append("Register AresForge managed project/repo in local registry.")
    if not seeded_agents or not seeded_handoff_targets:
        recommended_next_actions.append("Seed default agent profiles and handoff targets.")
    if not seeded_queue_items:
        recommended_next_actions.append("Seed initial queue milestones for next work phase.")
    if not github_link_present:
        recommended_next_actions.append("Populate local GitHub identity fields for AresForge metadata.")
    if not recommended_next_actions:
        recommended_next_actions.append("Bootstrap is ready. Continue in Projects, Queue, Agents, and Reports.")

    bootstrap_ready = (
        not missing_files
        and ("aresforge" in seeded_projects)
        and ("aresforge" in seeded_repos)
        and bool(seeded_agents)
        and bool(seeded_handoff_targets)
        and github_link_present
    )

    return {
        "repo_path": str(repo_path),
        "files": files,
        "missing_files": missing_files,
        "detected_project": detected_project,
        "detected_git": detected_git,
        "seeded_projects": sorted(set(seeded_projects)),
        "seeded_repos": sorted(set(seeded_repos)),
        "seeded_agents": sorted(set(seeded_agents)),
        "seeded_handoff_targets": sorted(set(seeded_handoff_targets)),
        "seeded_queue_items": sorted(set(seeded_queue_items)),
        "bootstrap_ready": bootstrap_ready,
        "warnings": sorted(set(str(item) for item in warnings if str(item).strip())),
        "recommended_next_actions": recommended_next_actions,
    }


def _safe_json_obj(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _find_project(registry: dict[str, Any], project_id: str) -> dict[str, Any] | None:
    for project in registry.get("projects", []):
        if isinstance(project, dict) and str(project.get("project_id", "")).strip() == project_id:
            return project
    return None


def _find_repo(registry: dict[str, Any], project_id: str, repo_id: str) -> dict[str, Any] | None:
    project = _find_project(registry, project_id)
    if project is None:
        return None
    for repo in project.get("repos", []):
        if isinstance(repo, dict) and str(repo.get("repo_id", "")).strip() == repo_id:
            return repo
    return None


def _resolve_repo_path(config: AppConfig, repo_path: str | Path | None) -> Path:
    if repo_path is None:
        return config.repo_root.resolve()
    candidate = Path(repo_path)
    if not candidate.is_absolute():
        candidate = (config.repo_root / candidate).resolve()
    return candidate.resolve()


def _config_for_repo(config: AppConfig, repo_root: Path) -> AppConfig:
    return AppConfig(
        repo_root=repo_root,
        db_host=config.db_host,
        db_port=config.db_port,
        db_name=config.db_name,
        db_user=config.db_user,
        db_password=config.db_password,
        ollama_base_url=config.ollama_base_url,
        ollama_model=config.ollama_model,
        artifact_root=(repo_root / "artifacts"),
        prompts_dir=(repo_root / "artifacts" / "prompts" / "generated"),
        evidence_dir=(repo_root / "artifacts" / "evidence" / "generated"),
        codex_handoffs_dir=(repo_root / "artifacts" / "codex_handoffs" / "generated"),
        github_owner=config.github_owner,
        github_repo=config.github_repo,
    )


def _action(action_id: str, description: str) -> dict[str, str]:
    return {"id": action_id, "description": description}


def _boundary_confirmations(*, plan_only: bool = False) -> list[str]:
    result = list(_BASE_BOUNDARIES)
    if plan_only:
        result.append("Plan-only response.")
    return result


def _stdout_result(command: str, payload: dict[str, Any], output_format: str, markdown: str) -> dict[str, Any]:
    fmt = str(output_format or "json").strip().lower()
    if fmt not in {"json", "markdown"}:
        return {
            "command": command,
            "ok": False,
            "local_only": True,
            "error": "invalid_format",
            "details": {
                "format": output_format,
                "supported_formats": ["json", "markdown"],
                "message": "format must be json or markdown.",
            },
            "boundary_confirmations": _boundary_confirmations(),
        }

    rendered = markdown if fmt == "markdown" else json.dumps(payload, indent=2, sort_keys=True)
    return {
        "command": command,
        "ok": True,
        "local_only": True,
        "format": fmt,
        "payload": payload,
        "stdout": rendered,
        "wrote_output_file": False,
        "boundary_confirmations": payload.get("boundary_confirmations", _boundary_confirmations()),
    }


def _render_plan_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Local Bootstrap Plan",
        "",
        f"- generated_at: {payload.get('generated_at', '')}",
        f"- local_only: {payload.get('local_only', True)}",
        f"- plan_only: {payload.get('plan_only', True)}",
        f"- repo_path: {payload.get('repo_path', '')}",
        "",
        "## Actions",
    ]
    actions = payload.get("actions", []) if isinstance(payload.get("actions"), list) else []
    if not actions:
        lines.append("- none")
    for action in actions:
        if isinstance(action, dict):
            lines.append(f"- {action.get('id', '')}: {action.get('description', '')}")

    lines.extend(
        [
            "",
            "## Would Initialize",
            *_render_markdown_list(payload.get("would_initialize", [])),
            "",
            "## Would Seed Projects",
            *_render_markdown_list(payload.get("would_seed_projects", [])),
            "",
            "## Would Seed Repos",
            *_render_markdown_list(payload.get("would_seed_repos", [])),
            "",
            "## Would Seed Agents",
            *_render_markdown_list(payload.get("would_seed_agents", [])),
            "",
            "## Would Seed Handoff Targets",
            *_render_markdown_list(payload.get("would_seed_handoff_targets", [])),
            "",
            "## Would Seed Queue Items",
            *_render_markdown_list(payload.get("would_seed_queue_items", [])),
            "",
            "## Warnings",
            *_render_markdown_list(payload.get("warnings", [])),
            "",
            "## Risks",
            *_render_markdown_list(payload.get("risks", [])),
            "",
            "## Boundary Confirmations",
            *_render_markdown_list(payload.get("boundary_confirmations", [])),
        ]
    )
    return "\n".join(lines)


def _render_apply_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Local Bootstrap Apply Result",
        "",
        f"- repo_path: {payload.get('repo_path', '')}",
        f"- bootstrap_ready: {payload.get('bootstrap_ready', False)}",
        f"- force: {payload.get('force', False)}",
        f"- seed_sample_work: {payload.get('seed_sample_work', False)}",
        "",
        "## Initialized Files",
        *_render_markdown_list(payload.get("initialized_files", [])),
        "",
        "## Applied Actions",
        *_render_markdown_list(payload.get("applied_actions", [])),
        "",
        "## Already Existing Actions",
        *_render_markdown_list(payload.get("already_existing_actions", [])),
        "",
        "## Seeded Projects",
        *_render_markdown_list(payload.get("seeded_projects", [])),
        "",
        "## Seeded Repos",
        *_render_markdown_list(payload.get("seeded_repos", [])),
        "",
        "## Seeded Agents",
        *_render_markdown_list(payload.get("seeded_agents", [])),
        "",
        "## Seeded Handoff Targets",
        *_render_markdown_list(payload.get("seeded_handoff_targets", [])),
        "",
        "## Seeded Queue Items",
        *_render_markdown_list(payload.get("seeded_queue_items", [])),
        "",
        "## Warnings",
        *_render_markdown_list(payload.get("warnings", [])),
        "",
        "## Recommended Next Actions",
        *_render_markdown_list(payload.get("recommended_next_actions", [])),
        "",
        "## Boundary Confirmations",
        *_render_markdown_list(payload.get("boundary_confirmations", [])),
    ]
    return "\n".join(lines)


def _render_markdown_list(values: Any) -> list[str]:
    if not isinstance(values, list) or not values:
        return ["- none"]
    return [f"- {item}" for item in values]


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


__all__ = ["apply_bootstrap", "inspect_bootstrap_status", "plan_bootstrap"]