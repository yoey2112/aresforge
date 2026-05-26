from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.local_active_project import set_active_project
from aresforge.operator.local_project_readiness import (
    inspect_local_project_readiness,
    list_local_projects,
)
from aresforge.operator.managed_project_registry_local import (
    init_managed_project_registry,
    register_managed_project,
    register_managed_repo,
)


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


def test_list_local_projects_includes_active_project_flag(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_managed_project_registry(config)["ok"] is True
    assert register_managed_project(
        config,
        project_id="p1",
        name="Project One",
        root_path=str(tmp_path),
    )["ok"] is True
    assert register_managed_repo(
        config,
        project_id="p1",
        repo_id="r1",
        name="Repo One",
        path=str(tmp_path),
        role="primary",
    )["ok"] is True
    assert set_active_project(config, project_id="p1")["ok"] is True

    payload = list_local_projects(config)

    assert payload["ok"] is True
    assert payload["project_count"] == 1
    assert payload["active_project_id"] == "p1"
    project = payload["projects"][0]
    assert project["project_id"] == "p1"
    assert project["project_name"] == "Project One"
    assert project["is_active"] is True
    assert "readiness_status" in project


def test_inspect_local_project_readiness_payload_keys(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_managed_project_registry(config)["ok"] is True
    assert register_managed_project(
        config,
        project_id="p1",
        name="Project One",
        root_path=str(tmp_path),
    )["ok"] is True
    assert register_managed_repo(
        config,
        project_id="p1",
        repo_id="r1",
        name="Repo One",
        path=str(tmp_path),
        role="primary",
    )["ok"] is True

    payload = inspect_local_project_readiness(config, project_id="p1")

    assert payload["ok"] is True
    for key in (
        "project_id",
        "project_name",
        "is_active",
        "repo_path",
        "local_path",
        "readiness_status",
        "readiness_summary",
        "blockers",
        "warnings",
        "next_safe_action",
        "artifact_summary",
    ):
        assert key in payload


def test_inspect_local_project_readiness_unknown_project(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_managed_project_registry(config)["ok"] is True

    payload = inspect_local_project_readiness(config, project_id="missing")

    assert payload["ok"] is False
    assert payload["error"] == "managed_project_not_found"
    assert payload["readiness_status"] == "not_found"
    assert payload["blockers"]
