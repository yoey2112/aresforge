import re
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.hub.api import (
    get_bootstrap_plan,
    get_bootstrap_status,
    get_agent,
    get_agents,
    get_docs_status,
    get_escalation_plan,
    get_health,
    get_handoff_preview,
    get_handoff_target,
    get_handoff_targets,
    get_orchestration_plan,
    get_project,
    get_project_repo_github_link,
    get_project_repos,
    get_reports_action_center,
    get_reports_dashboard,
    get_reports_export,
    get_reports_operator_workflows,
    get_reports_readiness,
    get_projects,
    get_queue,
    get_queue_item,
    get_settings,
    get_summary,
    patch_queue_item,
    post_agent,
    post_bootstrap_apply,
    post_escalation_plan,
    post_handoff_target,
    post_orchestration_plan,
    post_project,
    post_project_repo,
    post_queue_item,
)


NAV_LABELS = [
    "Home",
    "Bootstrap",
    "Projects",
    "Repos",
    "Queue",
    "Agents",
    "Handoff",
    "Orchestration",
    "Escalation",
    "Reports",
    "Settings",
]


def _config(tmp_path: Path) -> AppConfig:
    artifact_root = tmp_path / "artifacts"
    return AppConfig(
        repo_root=tmp_path,
        db_host="127.0.0.1",
        db_port=5433,
        db_name="aresforge",
        db_user="aresforge",
        db_password="aresforge",
        ollama_base_url="http://127.0.0.1:11434",
        ollama_model="qwen2.5:32b",
        artifact_root=artifact_root,
        prompts_dir=artifact_root / "prompts" / "generated",
        evidence_dir=artifact_root / "evidence" / "generated",
        codex_handoffs_dir=artifact_root / "codex_handoffs" / "generated",
        github_owner="local",
        github_repo="aresforge",
    )


def _static_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "src" / "aresforge" / "hub" / "static"


def _seed_project(config: AppConfig, project_id: str = "p1") -> None:
    payload = post_project(
        config,
        {
            "project_id": project_id,
            "name": "Project One",
            "root_path": str(config.repo_root),
            "status": "active",
            "default_branch": "main",
            "github_owner": "example-org",
            "github_repo": "sample-repo",
            "github_default_branch": "main",
            "tags": ["local"],
            "notes": "seed",
        },
    )
    assert payload["ok"] is True


def _seed_repo(config: AppConfig, project_id: str = "p1", repo_id: str = "r1") -> None:
    payload = post_project_repo(
        config,
        project_id,
        {
            "repo_id": repo_id,
            "name": "Repo One",
            "path": str(config.repo_root),
            "role": "primary",
            "status": "active",
            "github_owner": "example-org",
            "github_repo": "sample-repo",
            "github_default_branch": "main",
        },
    )
    assert payload["ok"] is True


def _seed_queue_item(config: AppConfig, item_id: str = "q1") -> None:
    _seed_project(config, "p1")
    _seed_repo(config, "p1", "r1")
    payload = post_queue_item(
        config,
        {
            "item_id": item_id,
            "project_id": "p1",
            "repo_id": "r1",
            "title": "Queue Item",
            "status": "ready",
            "priority": "high",
            "item_type": "task",
            "assigned_agent": "agent-a",
        },
    )
    assert payload["ok"] is True


def _seed_agent(config: AppConfig, agent_id: str = "agent-a") -> None:
    payload = post_agent(
        config,
        {
            "agent_id": agent_id,
            "name": "Agent A",
            "role": "implementer",
            "execution_mode": "codex",
            "status": "active",
            "escalation_allowed": True,
            "allowed_item_types": ["task", "feature"],
            "tags": ["m39"],
        },
    )
    assert payload["ok"] is True


def _seed_handoff_target(config: AppConfig, target_id: str = "target-a") -> None:
    payload = post_handoff_target(
        config,
        {
            "target_id": target_id,
            "name": "Target A",
            "target_type": "codex_prompt",
            "status": "active",
            "input_format": "markdown",
            "output_format": "patch",
            "tags": ["m39"],
        },
    )
    assert payload["ok"] is True


def test_hub_static_files_exist() -> None:
    static_dir = _static_dir()
    assert (static_dir / "index.html").exists()
    assert (static_dir / "app.js").exists()
    assert (static_dir / "styles.css").exists()


def test_index_contains_required_navigation_labels_and_m39_sections() -> None:
    index_text = (_static_dir() / "index.html").read_text(encoding="utf-8")
    for label in NAV_LABELS:
        assert label in index_text
    assert "Add Or Update Project" in index_text
    assert "Add Or Update Repo" in index_text
    assert "Add Or Update Queue Item" in index_text
    assert "Add Or Update Agent" in index_text
    assert "Add Or Update Handoff Target" in index_text
    assert "Refresh Handoff Preview" in index_text
    assert "Generate/view plan-only orchestration guidance" in index_text
    assert "Generate/view plan-only escalation classification" in index_text
    assert "Action Center Preview" in index_text
    assert "Quick Workflow Cards" in index_text
    assert "Refresh Summary" in index_text
    assert "Refresh Report" in index_text
    assert "Copy Report JSON" in index_text
    assert "Export JSON Text" in index_text
    assert "GitHub URL" in index_text
    assert "GitHub Owner" in index_text
    assert "GitHub Repo" in index_text
    assert "Inspect local git during save" in index_text
    assert "Inspect Local Git Link For Repo ID" in index_text
    assert "Bootstrap Setup" in index_text
    assert "Apply Bootstrap" in index_text
    assert "Seed sample work queue" in index_text
    assert "Force overwrite where safe" in index_text
    assert "Active Project Selector" in index_text
    assert "Set Active Project" in index_text
    assert "Active Project Queue Focus" in index_text
    assert "Use Active Project Defaults" in index_text
    assert "Filter To Active Project" in index_text
    assert "Active Project Report Focus" in index_text
    assert "settings-active-project-path" in index_text


def test_app_js_references_m39_api_endpoints_and_forms() -> None:
    app_text = (_static_dir() / "app.js").read_text(encoding="utf-8")
    for endpoint in (
        "/api/projects",
        "/api/projects/active",
        "/api/projects/",
        "/github-link",
        "/api/bootstrap/status",
        "/api/bootstrap/plan",
        "/api/bootstrap/apply",
        "/api/queue",
        "/api/settings",
        "/api/agents",
        "/api/handoff-targets",
        "/api/handoff/preview",
        "/api/orchestration/plan",
        "/api/escalation/plan",
        "/api/reports/dashboard",
        "/api/reports/action-center",
        "/api/reports/readiness",
        "/api/reports/operator-workflows",
        "/api/reports/export",
    ):
        assert endpoint in app_text
    for form_id in (
        "project-form",
        "repo-form",
        "queue-form",
        "queue-filter-form",
        "agent-form",
        "handoff-target-form",
        "orchestration-form",
        "escalation-form",
    ):
        assert form_id in app_text
    for action_id in (
        "bootstrap-refresh-status",
        "bootstrap-refresh-plan",
        "bootstrap-apply",
        "reports-refresh",
        "reports-copy-json",
        "reports-export-json",
        "reports-generate-handoff",
        "reports-generate-orchestration",
        "reports-generate-escalation",
        "home-refresh-summary",
        "active-project-set",
        "queue-use-active-project",
        "queue-filter-active-project",
    ):
        assert action_id in app_text


def test_bootstrap_api_status_plan_apply(tmp_path: Path) -> None:
    config = _config(tmp_path)

    status = get_bootstrap_status(config)
    assert status["ok"] is True
    assert status["local_only"] is True
    assert "boundary_confirmations" in status

    plan = get_bootstrap_plan(config, {"seed_sample_work": "true"})
    assert plan["ok"] is True
    assert plan["plan_only"] is True
    assert "actions" in plan
    assert "boundary_confirmations" in plan

    applied = post_bootstrap_apply(config, {"force": False, "seed_sample_work": True})
    assert applied["ok"] is True
    assert applied["local_only"] is True
    assert "warnings" in applied
    assert "boundary_confirmations" in applied
    assert "m43-hub-stabilization" in applied["seeded_queue_items"]


def test_reports_and_settings_sections_contain_m40_concepts() -> None:
    index_text = (_static_dir() / "index.html").read_text(encoding="utf-8")
    assert "Project/Repo Summary" in index_text
    assert "Queue Summary" in index_text
    assert "Agent Summary" in index_text
    assert "Orchestration Summary" in index_text
    assert "Escalation Summary" in index_text
    assert "Docs Summary" in index_text
    assert "Readiness Indicators" in index_text
    assert "Action Center" in index_text
    assert "Operator Workflows" in index_text
    assert "GitHub Linkage" in index_text
    assert "Known limitations" in index_text
    assert "Next milestone scope" in index_text


def test_static_assets_do_not_reference_external_resources() -> None:
    external_patterns = [
        r"https?://",
        r"cdn",
        r"fonts\.googleapis",
        r"fonts\.gstatic",
        r"unpkg",
        r"jsdelivr",
    ]
    pattern = re.compile("|".join(external_patterns), re.IGNORECASE)

    for name in ("index.html", "app.js", "styles.css"):
        content = (_static_dir() / name).read_text(encoding="utf-8")
        assert not pattern.search(content)


def test_settings_and_boundary_notice_present_in_static_markup() -> None:
    index_text = (_static_dir() / "index.html").read_text(encoding="utf-8")
    assert "Local-only boundary" in index_text
    assert "settings-registry-path" in index_text
    assert "settings-queue-path" in index_text
    assert "settings-agents-path" in index_text
    assert "settings-handoff-artifacts-path" in index_text
    assert "settings-orchestration-artifacts-path" in index_text
    assert "settings-escalation-artifacts-path" in index_text
    assert "settings-dashboard-artifacts-path" in index_text
    assert "settings-m41-boundaries" in index_text
    assert "GitHub link boundary note" in index_text
    assert "plan-only" in index_text


def test_api_health_response_contains_boundaries() -> None:
    payload = get_health()

    assert payload["ok"] is True
    assert payload["local_only"] is True
    assert payload["service"] == "aresforge-hub"
    assert any("No GitHub calls" in item for item in payload["boundary_confirmations"])


def test_api_summary_with_missing_files_returns_empty_state(tmp_path: Path) -> None:
    payload = get_summary(_config(tmp_path))

    assert payload["ok"] is True
    assert payload["local_only"] is True
    assert payload["report_only"] is True
    assert payload["project_count"] == 0
    assert payload["repo_count"] == 0
    assert payload["queue_status_counts"] == {}
    assert payload["agent_count"] == 0
    assert payload["warnings"]
    assert payload["next_recommended_actions"]
    assert payload["project_management_readiness"]
    assert any("No network service calls" in item for item in payload["boundary_confirmations"])


def test_api_docs_status_response(tmp_path: Path) -> None:
    payload = get_docs_status(_config(tmp_path))

    assert payload["ok"] is True
    assert payload["local_only"] is True
    assert payload["report_only"] is True
    assert isinstance(payload["docs"], list)
    assert payload["missing_count"] >= 0
    assert "boundary_confirmations" in payload


def test_reports_dashboard_with_missing_files_returns_report_and_warnings(tmp_path: Path) -> None:
    payload = get_reports_dashboard(_config(tmp_path))

    assert payload["ok"] is True
    assert payload["local_only"] is True
    assert payload["report_only"] is True
    assert "project_summary" in payload
    assert "queue_summary" in payload
    assert "agent_summary" in payload
    assert "docs_summary" in payload
    assert payload["warnings"]
    assert payload["boundary_confirmations"]


def test_reports_action_center_readiness_workflows_and_export_endpoints(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_project(config, "p1")
    _seed_repo(config, "p1", "r1")
    _seed_queue_item(config, "q1")
    _seed_agent(config, "agent-a")
    _seed_handoff_target(config, "target-a")

    action_center = get_reports_action_center(config)
    readiness = get_reports_readiness(config)
    workflows = get_reports_operator_workflows(config)
    exported = get_reports_export(config, {"format": "json"})

    assert action_center["ok"] is True
    assert "action_center" in action_center
    assert action_center["boundary_confirmations"]

    assert readiness["ok"] is True
    assert "readiness_indicators" in readiness
    assert "overall_status" in readiness["readiness_indicators"]
    assert readiness["boundary_confirmations"]

    assert workflows["ok"] is True
    assert isinstance(workflows["operator_workflows"], list)
    assert workflows["operator_workflows"]
    assert workflows["boundary_confirmations"]

    assert exported["ok"] is True
    assert exported["report_only"] is True
    assert "report" in exported
    assert "content" in exported
    assert exported["write_performed"] is False
    assert exported["boundary_confirmations"]


def test_get_projects_returns_empty_state_when_registry_missing(tmp_path: Path) -> None:
    config = _config(tmp_path)
    payload = get_projects(config)

    assert payload["ok"] is True
    assert payload["local_only"] is True
    assert payload["projects"] == []
    assert payload["project_count"] == 0
    assert payload["warnings"]
    assert payload["boundary_confirmations"]


def test_post_project_creates_and_updates_project(tmp_path: Path) -> None:
    config = _config(tmp_path)

    created = post_project(
        config,
        {
            "project_id": "p1",
            "name": "Project One",
            "root_path": str(tmp_path),
            "status": "active",
            "default_branch": "main",
            "github_owner": "example-org",
            "github_repo": "sample-repo",
            "github_default_branch": "main",
            "tags": ["m38"],
            "notes": "initial",
        },
    )
    assert created["ok"] is True
    assert created["created"] is True

    updated = post_project(
        config,
        {
            "project_id": "p1",
            "name": "Project One Updated",
            "root_path": str(tmp_path),
            "status": "paused",
            "tags": ["m38", "updated"],
        },
    )
    assert updated["ok"] is True
    assert updated["created"] is False
    assert updated["project"]["name"] == "Project One Updated"
    assert updated["project"]["status"] == "paused"
    assert updated["project"]["github_url"] == "https://github.com/example-org/sample-repo"


def test_get_project_returns_project_details_and_repos(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_project(config, "p1")
    _seed_repo(config, "p1", "r1")

    payload = get_project(config, "p1")

    assert payload["ok"] is True
    assert payload["project"]["project_id"] == "p1"
    assert payload["project"]["github_owner"] == "example-org"
    assert payload["project"]["github_repo"] == "sample-repo"
    assert payload["project"]["github_url"] == "https://github.com/example-org/sample-repo"
    assert len(payload["repos"]) == 1
    assert payload["repos"][0]["repo_id"] == "r1"
    assert payload["repos"][0]["github_owner"] == "example-org"
    assert payload["repos"][0]["github_repo"] == "sample-repo"


def test_get_project_repos_returns_repos_for_project(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_project(config, "p1")
    _seed_repo(config, "p1", "r1")

    payload = get_project_repos(config, "p1")

    assert payload["ok"] is True
    assert payload["project_id"] == "p1"
    assert payload["repo_count"] == 1
    assert payload["repos"][0]["github_url"] == "https://github.com/example-org/sample-repo"


def test_post_project_repo_creates_and_updates_repo(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_project(config, "p1")

    created = post_project_repo(
        config,
        "p1",
        {
            "repo_id": "r1",
            "name": "Repo One",
            "path": str(tmp_path),
            "role": "primary",
            "status": "active",
            "github_url": "https://github.com/example-org/sample-repo",
        },
    )
    assert created["ok"] is True
    assert created["created"] is True

    updated = post_project_repo(
        config,
        "p1",
        {
            "repo_id": "r1",
            "name": "Repo One Updated",
            "path": str(tmp_path),
            "role": "automation",
            "status": "paused",
            "tags": ["x"],
        },
    )
    assert updated["ok"] is True
    assert updated["created"] is False
    assert updated["repo"]["name"] == "Repo One Updated"
    assert updated["repo"]["role"] == "automation"


def test_get_project_repo_github_link_returns_local_only_payload(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_project(config, "p1")
    non_git_dir = tmp_path / "non-git"
    non_git_dir.mkdir(parents=True, exist_ok=True)
    created = post_project_repo(
        config,
        "p1",
        {
            "repo_id": "r1",
            "name": "Repo One",
            "path": str(non_git_dir),
            "role": "primary",
            "github_owner": "example-org",
            "github_repo": "sample-repo",
        },
    )
    assert created["ok"] is True

    payload = get_project_repo_github_link(config, "p1", "r1", inspect_local_git=True)
    assert payload["ok"] is True
    assert payload["local_only"] is True
    assert payload["project_id"] == "p1"
    assert payload["repo_id"] == "r1"
    assert payload["github_owner"] == "example-org"
    assert payload["github_repo"] == "sample-repo"
    assert payload["github_url"] == "https://github.com/example-org/sample-repo"
    assert isinstance(payload["warnings"], list)
    assert payload["boundary_confirmations"]


def test_post_repo_fails_clearly_when_project_missing(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_project(config, "p1")
    payload = post_project_repo(
        config,
        "missing",
        {
            "repo_id": "r1",
            "name": "Repo One",
            "path": str(tmp_path),
        },
    )

    assert payload["ok"] is False
    assert payload["error"] == "managed_project_not_found"
    assert payload["_status"] == 404


def test_get_queue_returns_empty_state_when_queue_missing(tmp_path: Path) -> None:
    config = _config(tmp_path)
    payload = get_queue(config, {})

    assert payload["ok"] is True
    assert payload["local_only"] is True
    assert payload["items"] == []
    assert payload["counts_by_status"] == {}
    assert payload["counts_by_type"] == {}
    assert payload["counts_by_priority"] == {}
    assert payload["warnings"]


def test_post_queue_creates_and_updates_item(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_project(config, "p1")
    _seed_repo(config, "p1", "r1")

    created = post_queue_item(
        config,
        {
            "item_id": "q1",
            "project_id": "p1",
            "repo_id": "r1",
            "title": "Queue One",
            "status": "ready",
            "priority": "high",
            "item_type": "task",
            "dependencies": ["future-item"],
        },
    )
    assert created["ok"] is True
    assert created["created"] is True
    assert any("reference not found" in warning for warning in created["warnings"])

    updated = post_queue_item(
        config,
        {
            "item_id": "q1",
            "project_id": "p1",
            "repo_id": "r1",
            "title": "Queue One Updated",
            "status": "in_progress",
            "priority": "urgent",
            "item_type": "feature",
        },
    )
    assert updated["ok"] is True
    assert updated["created"] is False
    assert updated["item"]["status"] == "in_progress"
    assert updated["item"]["priority"] == "urgent"


def test_get_queue_item_returns_item_details(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue_item(config, "q1")

    payload = get_queue_item(config, "q1")

    assert payload["ok"] is True
    assert payload["item"]["item_id"] == "q1"


def test_patch_queue_updates_only_supplied_fields(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue_item(config, "q1")

    payload = patch_queue_item(
        config,
        "q1",
        {
            "status": "blocked",
            "notes": "waiting",
        },
    )

    assert payload["ok"] is True
    assert payload["item"]["status"] == "blocked"
    assert payload["item"]["notes"] == "waiting"
    assert payload["item"]["priority"] == "high"


def test_patch_queue_missing_item_fails_clearly(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue_item(config, "q1")
    payload = patch_queue_item(config, "missing", {"status": "ready"})

    assert payload["ok"] is False
    assert payload["error"] == "queue_item_not_found"
    assert payload["_status"] == 404


def test_queue_filters_for_project_repo_status_type_and_assigned_agent(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue_item(config, "q1")
    post_queue_item(
        config,
        {
            "item_id": "q2",
            "project_id": "p1",
            "repo_id": "r1",
            "title": "Queue Two",
            "status": "blocked",
            "priority": "normal",
            "item_type": "bug",
            "assigned_agent": "agent-b",
        },
    )

    payload = get_queue(
        config,
        {
            "project_id": "p1",
            "repo_id": "r1",
            "status": "ready",
            "type": "task",
            "assigned_agent": "agent-a",
        },
    )

    assert payload["ok"] is True
    assert len(payload["items"]) == 1
    assert payload["items"][0]["item_id"] == "q1"


def test_invalid_project_repo_queue_values_return_json_errors(tmp_path: Path) -> None:
    config = _config(tmp_path)

    invalid_project = post_project(
        config,
        {
            "project_id": "p1",
            "name": "Project One",
            "root_path": str(tmp_path),
            "status": "bad-status",
        },
    )
    assert invalid_project["ok"] is False
    assert invalid_project["error"] == "invalid_project_status"

    _seed_project(config, "p1")

    invalid_repo = post_project_repo(
        config,
        "p1",
        {
            "repo_id": "r1",
            "name": "Repo One",
            "path": str(tmp_path),
            "role": "bad-role",
        },
    )
    assert invalid_repo["ok"] is False
    assert invalid_repo["error"] == "invalid_repo_role"

    invalid_queue = post_queue_item(
        config,
        {
            "item_id": "q1",
            "project_id": "p1",
            "repo_id": "r1",
            "title": "Queue One",
            "priority": "bad-priority",
        },
    )
    assert invalid_queue["ok"] is False
    assert invalid_queue["error"] == "invalid_queue_priority"


def test_boundary_confirmations_remain_present_for_m38_endpoints(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue_item(config, "q1")

    projects = get_projects(config)
    queue = get_queue(config, {})
    settings = get_settings(config)

    for payload in (projects, queue, settings):
        assert payload["local_only"] is True
        assert payload["boundary_confirmations"]
    assert settings["m41_boundary_confirmations"]


def test_get_agents_returns_empty_state_when_profiles_missing(tmp_path: Path) -> None:
    payload = get_agents(_config(tmp_path))
    assert payload["ok"] is True
    assert payload["agents"] == []
    assert payload["agent_count"] == 0
    assert payload["counts_by_role"] == {}
    assert payload["counts_by_execution_mode"] == {}
    assert payload["counts_by_status"] == {}
    assert payload["warnings"]
    assert payload["boundary_confirmations"]


def test_post_agent_creates_and_updates_profile(tmp_path: Path) -> None:
    config = _config(tmp_path)
    created = post_agent(
        config,
        {
            "agent_id": "agent-a",
            "name": "Agent A",
            "role": "implementer",
            "execution_mode": "codex",
            "status": "active",
            "escalation_allowed": True,
            "allowed_item_types": ["task"],
        },
    )
    assert created["ok"] is True
    assert created["created"] is True

    updated = post_agent(
        config,
        {
            "agent_id": "agent-a",
            "name": "Agent A Updated",
            "role": "implementer",
            "execution_mode": "scripted",
            "status": "paused",
            "escalation_allowed": False,
        },
    )
    assert updated["ok"] is True
    assert updated["created"] is False
    assert updated["agent"]["name"] == "Agent A Updated"
    assert updated["agent"]["execution_mode"] == "scripted"


def test_get_agent_returns_details_and_linked_target_when_available(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_handoff_target(config, "target-a")
    post_agent(
        config,
        {
            "agent_id": "agent-a",
            "name": "Agent A",
            "role": "implementer",
            "handoff_target_id": "target-a",
        },
    )

    payload = get_agent(config, "agent-a")
    assert payload["ok"] is True
    assert payload["agent"]["agent_id"] == "agent-a"
    assert payload["linked_handoff_target"]["target_id"] == "target-a"


def test_post_agent_rejects_invalid_role_execution_mode_status_and_escalation_flag(tmp_path: Path) -> None:
    config = _config(tmp_path)

    invalid_role = post_agent(config, {"agent_id": "a", "name": "A", "role": "invalid"})
    assert invalid_role["ok"] is False
    assert invalid_role["error"] == "invalid_role"

    invalid_mode = post_agent(
        config,
        {"agent_id": "a", "name": "A", "role": "operator", "execution_mode": "invalid"},
    )
    assert invalid_mode["ok"] is False
    assert invalid_mode["error"] == "invalid_execution_mode"

    invalid_status = post_agent(
        config,
        {"agent_id": "a", "name": "A", "role": "operator", "status": "invalid"},
    )
    assert invalid_status["ok"] is False
    assert invalid_status["error"] == "invalid_status"

    invalid_escalation = post_agent(
        config,
        {
            "agent_id": "a",
            "name": "A",
            "role": "operator",
            "escalation_allowed": "yes",
        },
    )
    assert invalid_escalation["ok"] is False
    assert invalid_escalation["error"] == "invalid_escalation_allowed"


def test_get_handoff_targets_returns_empty_state_when_profiles_missing(tmp_path: Path) -> None:
    payload = get_handoff_targets(_config(tmp_path))
    assert payload["ok"] is True
    assert payload["handoff_targets"] == []
    assert payload["target_count"] == 0
    assert payload["counts_by_target_type"] == {}
    assert payload["counts_by_status"] == {}
    assert payload["warnings"]


def test_post_handoff_target_creates_and_updates_target(tmp_path: Path) -> None:
    config = _config(tmp_path)
    created = post_handoff_target(
        config,
        {
            "target_id": "target-a",
            "name": "Target A",
            "target_type": "markdown_packet",
            "status": "active",
        },
    )
    assert created["ok"] is True
    assert created["created"] is True

    updated = post_handoff_target(
        config,
        {
            "target_id": "target-a",
            "name": "Target A Updated",
            "target_type": "json_packet",
            "status": "paused",
        },
    )
    assert updated["ok"] is True
    assert updated["created"] is False
    assert updated["handoff_target"]["target_type"] == "json_packet"


def test_get_handoff_target_returns_target_details(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_handoff_target(config, "target-a")
    payload = get_handoff_target(config, "target-a")
    assert payload["ok"] is True
    assert payload["handoff_target"]["target_id"] == "target-a"


def test_post_handoff_target_rejects_invalid_type_and_status(tmp_path: Path) -> None:
    config = _config(tmp_path)
    invalid_type = post_handoff_target(
        config,
        {"target_id": "t", "name": "T", "target_type": "invalid"},
    )
    assert invalid_type["ok"] is False
    assert invalid_type["error"] == "invalid_target_type"

    invalid_status = post_handoff_target(
        config,
        {
            "target_id": "t",
            "name": "T",
            "target_type": "markdown_packet",
            "status": "invalid",
        },
    )
    assert invalid_status["ok"] is False
    assert invalid_status["error"] == "invalid_status"


def test_get_handoff_preview_returns_local_only_response(tmp_path: Path) -> None:
    payload = get_handoff_preview(_config(tmp_path))
    assert payload["ok"] is True
    assert payload["local_only"] is True
    assert payload["preview_format"] == "markdown"
    assert isinstance(payload["preview"], str)
    assert payload["boundary_confirmations"]


def test_get_orchestration_plan_returns_plan_only_with_empty_inputs(tmp_path: Path) -> None:
    payload = get_orchestration_plan(_config(tmp_path))
    assert payload["ok"] is True
    assert payload["local_only"] is True
    assert payload["plan_only"] is True
    assert isinstance(payload["selected_work_items"], list)
    assert "recommended_assignments" in payload
    assert payload["boundary_confirmations"]


def test_post_orchestration_plan_supports_filters(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue_item(config, "q1")
    _seed_agent(config, "agent-a")
    payload = post_orchestration_plan(
        config,
        {"project_id": "p1", "repo_id": "r1", "status": "ready", "format": "json"},
    )
    assert payload["ok"] is True
    assert payload["filters"]["project_id"] == "p1"
    assert payload["plan_only"] is True


def test_get_escalation_plan_returns_plan_only_with_empty_inputs(tmp_path: Path) -> None:
    payload = get_escalation_plan(_config(tmp_path))
    assert payload["ok"] is True
    assert payload["local_only"] is True
    assert payload["plan_only"] is True
    assert "classifications" in payload
    assert "prompt_guidance" in payload
    assert payload["boundary_confirmations"]


def test_post_escalation_plan_supports_filters(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue_item(config, "q1")
    _seed_agent(config, "agent-a")
    _seed_handoff_target(config, "target-a")
    payload = post_escalation_plan(
        config,
        {
            "item_id": "q1",
            "project_id": "p1",
            "repo_id": "r1",
            "status": "ready",
            "format": "json",
        },
    )
    assert payload["ok"] is True
    assert payload["filters"]["item_id"] == "q1"
    assert payload["plan_only"] is True


def test_boundary_confirmations_remain_present_for_m39_endpoints(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue_item(config, "q1")
    _seed_agent(config, "agent-a")

    for payload in (
        get_agents(config),
        get_handoff_targets(config),
        get_handoff_preview(config),
        get_orchestration_plan(config),
        get_escalation_plan(config),
    ):
        assert payload["local_only"] is True
        assert payload["boundary_confirmations"]
