from pathlib import Path

from aresforge.config import AppConfig
from aresforge.hub.api import get_active_project, get_projects, get_settings, post_active_project, post_project, post_project_repo


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


def _seed_project(config: AppConfig, tmp_path: Path) -> None:
    created = post_project(
        config,
        {
            "project_id": "p1",
            "name": "Project One",
            "root_path": str(tmp_path),
            "status": "active",
            "github_owner": "example-org",
            "github_repo": "sample-repo",
        },
    )
    assert created["ok"] is True
    repo = post_project_repo(
        config,
        "p1",
        {
            "repo_id": "r1",
            "name": "Repo One",
            "path": str(tmp_path),
            "role": "primary",
            "status": "active",
            "github_owner": "example-org",
            "github_repo": "sample-repo",
        },
    )
    assert repo["ok"] is True


def test_get_active_project_empty_state_is_local_only(tmp_path: Path) -> None:
    payload = get_active_project(_config(tmp_path))

    assert payload["ok"] is True
    assert payload["local_only"] is True
    assert payload["service"] == "aresforge-hub"
    assert payload["active_project_selected"] is False
    assert payload["active_project_id"] == ""
    assert payload["boundary_confirmations"]


def test_post_active_project_sets_project_and_get_projects_marks_it(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_project(config, tmp_path)

    posted = post_active_project(config, {"project_id": "p1"})

    assert posted["ok"] is True
    assert posted["active_project_id"] == "p1"
    assert posted["active_project"]["project_id"] == "p1"
    assert posted["active_repo_id"] == "r1"

    active = get_active_project(config)
    assert active["active_project_id"] == "p1"
    assert active["active_repo_id"] == "r1"

    projects = get_projects(config)
    assert projects["active_project_id"] == "p1"
    assert projects["active_project_selected"] is True
    assert projects["active_repo_id"] == "r1"
    assert projects["projects"][0]["is_active_project"] is True


def test_post_active_project_returns_api_error_for_missing_project(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_project(config, tmp_path)

    payload = post_active_project(config, {"project_id": "missing"})

    assert payload["ok"] is False
    assert payload["error"] == "managed_project_not_found"
    assert payload["_status"] == 404
    assert payload["boundary_confirmations"]


def test_settings_exposes_active_project_path(tmp_path: Path) -> None:
    payload = get_settings(_config(tmp_path))

    assert payload["ok"] is True
    normalized_path = payload["active_project_path"].replace("\\", "/")
    assert normalized_path.endswith(".aresforge/projects/active_project.json")

