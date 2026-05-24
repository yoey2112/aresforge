from __future__ import annotations

from pathlib import Path

from aresforge.config import AppConfig
from aresforge.hub.api import post_project_factory_new_project


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


def test_post_project_factory_new_project_returns_expected_payload(tmp_path: Path) -> None:
    config = _config(tmp_path)
    payload = post_project_factory_new_project(
        config,
        {
            "name": "Hub Wizard Project",
            "project_id": "",
            "description": "Local-only wizard bootstrapping",
            "project_type": "automation",
            "preferred_stack": "python",
            "root_path": str(tmp_path / "workspace"),
            "github_owner": "example",
            "github_repo": "hub-wizard-project",
            "github_mode": "create-with-approval-later",
            "default_branch": "main",
            "initial_requirements": "Prepare scope and architecture",
            "tags": "wizard,project-factory",
        },
    )

    assert payload["ok"] is True
    assert payload["local_only"] is True
    assert payload["project"]["project_id"] == "hub-wizard-project"
    assert payload["repo"]["repo_id"] == "hub-wizard-project-primary"
    assert payload["active_project_id"] == "hub-wizard-project"
    assert payload["scope_queue_item"]["source"] == "hub-new-project-wizard"
    assert payload["dossier"]["project_type"] == "automation"
    assert payload["dossier"]["github_mode"] == "create-with-approval-later"
    assert payload["dossier_path"]
    assert payload["boundary_confirmations"]


def test_post_project_factory_new_project_errors_for_invalid_payload(tmp_path: Path) -> None:
    config = _config(tmp_path)
    missing_name = post_project_factory_new_project(
        config,
        {
            "name": " ",
            "root_path": str(tmp_path / "workspace"),
        },
    )
    assert missing_name["ok"] is False
    assert missing_name["error"] == "invalid_project_factory_payload"

    invalid_type = post_project_factory_new_project(
        config,
        {
            "name": "x",
            "root_path": str(tmp_path / "workspace"),
            "project_type": "bad-type",
        },
    )
    assert invalid_type["ok"] is False
    assert invalid_type["error"] == "invalid_project_type"
