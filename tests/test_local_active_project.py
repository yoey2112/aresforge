from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.local_active_project import (
    inspect_active_project,
    resolve_active_project_path,
    set_active_project,
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


def _seed_project_with_repo(config: AppConfig, tmp_path: Path) -> None:
    assert init_managed_project_registry(config)["ok"] is True
    assert register_managed_project(
        config,
        project_id="p1",
        name="Project One",
        root_path=str(tmp_path),
        status="active",
        github_owner="example-org",
        github_repo="sample-repo",
    )["ok"] is True
    assert register_managed_repo(
        config,
        project_id="p1",
        repo_id="r1",
        name="Repo One",
        path=str(tmp_path),
        role="primary",
        status="active",
        github_owner="example-org",
        github_repo="sample-repo",
    )["ok"] is True


def test_inspect_active_project_returns_empty_state_when_missing(tmp_path: Path) -> None:
    config = _config(tmp_path)

    payload = inspect_active_project(config)

    assert payload["ok"] is True
    assert payload["local_only"] is True
    assert payload["active_project_selected"] is False
    assert payload["active_project_id"] == ""
    assert payload["active_project"] is None
    assert payload["active_repo_id"] == ""
    assert payload["warnings"]
    assert payload["boundary_confirmations"]
    assert payload["active_project_path"] == str(resolve_active_project_path(tmp_path))


def test_set_active_project_writes_file_backed_state(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_project_with_repo(config, tmp_path)

    payload = set_active_project(config, project_id="p1")

    assert payload["ok"] is True
    assert payload["active_project_selected"] is True
    assert payload["active_project_id"] == "p1"
    assert payload["active_project"]["name"] == "Project One"
    assert payload["active_repo_id"] == "r1"
    assert payload["active_repo"]["repo_id"] == "r1"
    assert Path(payload["active_project_path"]).exists()

    inspected = inspect_active_project(config)
    assert inspected["active_project_id"] == "p1"
    assert inspected["active_project"]["project_id"] == "p1"
    assert inspected["active_repo_id"] == "r1"


def test_set_active_project_rejects_missing_project(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_managed_project_registry(config)["ok"] is True

    payload = set_active_project(config, project_id="missing")

    assert payload["ok"] is False
    assert payload["local_only"] is True
    assert payload["error"] == "managed_project_not_found"
    assert payload["details"]["project_id"] == "missing"


def test_set_active_project_rejects_empty_project_id(tmp_path: Path) -> None:
    payload = set_active_project(_config(tmp_path), project_id=" ")

    assert payload["ok"] is False
    assert payload["error"] == "invalid_active_project_payload"
    assert "project_id" in payload["details"]["required_fields"]
