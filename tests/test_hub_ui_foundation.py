import re
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.hub.api import (
    get_docs_status,
    get_health,
    get_project,
    get_project_repos,
    get_projects,
    get_queue,
    get_queue_item,
    get_settings,
    get_summary,
    patch_queue_item,
    post_project,
    post_project_repo,
    post_queue_item,
)


NAV_LABELS = [
    "Home",
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


def test_hub_static_files_exist() -> None:
    static_dir = _static_dir()
    assert (static_dir / "index.html").exists()
    assert (static_dir / "app.js").exists()
    assert (static_dir / "styles.css").exists()


def test_index_contains_required_navigation_labels_and_m38_sections() -> None:
    index_text = (_static_dir() / "index.html").read_text(encoding="utf-8")
    for label in NAV_LABELS:
        assert label in index_text
    assert "Add Or Update Project" in index_text
    assert "Add Or Update Repo" in index_text
    assert "Add Or Update Queue Item" in index_text


def test_app_js_references_m38_api_endpoints_and_forms() -> None:
    app_text = (_static_dir() / "app.js").read_text(encoding="utf-8")
    for endpoint in (
        "/api/projects",
        "/api/projects/",
        "/api/queue",
        "/api/settings",
    ):
        assert endpoint in app_text
    for form_id in ("project-form", "repo-form", "queue-form", "queue-filter-form"):
        assert form_id in app_text


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


def test_get_project_returns_project_details_and_repos(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_project(config, "p1")
    _seed_repo(config, "p1", "r1")

    payload = get_project(config, "p1")

    assert payload["ok"] is True
    assert payload["project"]["project_id"] == "p1"
    assert len(payload["repos"]) == 1
    assert payload["repos"][0]["repo_id"] == "r1"


def test_get_project_repos_returns_repos_for_project(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_project(config, "p1")
    _seed_repo(config, "p1", "r1")

    payload = get_project_repos(config, "p1")

    assert payload["ok"] is True
    assert payload["project_id"] == "p1"
    assert payload["repo_count"] == 1


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
