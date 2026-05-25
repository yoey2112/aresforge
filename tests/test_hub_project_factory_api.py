from __future__ import annotations

from pathlib import Path

from aresforge.config import AppConfig
from aresforge.hub.api import (
    get_project_factory_scope_package,
    patch_project_factory_scope_package,
    get_project_factory_dossier,
    post_active_project,
    post_project_factory_new_project,
    post_project_factory_scope_package_approve,
    post_project_factory_scope_package,
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


def test_get_project_factory_dossier_without_project_id_uses_active_project(tmp_path: Path) -> None:
    config = _config(tmp_path)
    created = post_project_factory_new_project(
        config,
        {
            "name": "Dossier Project",
            "root_path": str(tmp_path / "workspace"),
        },
    )
    assert created["ok"] is True

    payload = get_project_factory_dossier(config, {})
    assert payload["ok"] is True
    assert payload["dossier_exists"] is True
    assert payload["project_id"] == created["active_project_id"]


def test_get_project_factory_dossier_missing_state_is_friendly(tmp_path: Path) -> None:
    config = _config(tmp_path)
    payload = get_project_factory_dossier(config, {})
    assert payload["ok"] is True
    assert payload["dossier_exists"] is False
    assert payload["warnings"]


def test_post_project_factory_scope_package_prepares_for_active_project(tmp_path: Path) -> None:
    config = _config(tmp_path)
    created = post_project_factory_new_project(
        config,
        {
            "name": "Scope API Project",
            "root_path": str(tmp_path / "workspace"),
        },
    )
    assert created["ok"] is True

    payload = post_project_factory_scope_package(config, {})
    assert payload["ok"] is True
    assert payload["project_id"] == created["active_project_id"]
    assert payload["scope_package"]["lifecycle_state"] == "scope_package_prepared"


def test_post_project_factory_scope_package_returns_400_with_no_active_project(tmp_path: Path) -> None:
    config = _config(tmp_path)
    payload = post_project_factory_scope_package(config, {})
    assert payload["ok"] is False
    assert payload["_status"] == 400


def test_post_project_factory_scope_package_returns_404_for_missing_dossier(tmp_path: Path) -> None:
    config = _config(tmp_path)
    seed = post_project_factory_new_project(
        config,
        {
            "name": "Seed Project",
            "project_id": "seed-project",
            "root_path": str(tmp_path / "seed-workspace"),
        },
    )
    assert seed["ok"] is True
    post_active_project(config, {"project_id": "seed-project"})

    payload = post_project_factory_scope_package(config, {"project_id": "missing-project"})
    assert payload["ok"] is False
    assert payload["_status"] == 404


def test_get_scope_package_falls_back_to_active_project(tmp_path: Path) -> None:
    config = _config(tmp_path)
    created = post_project_factory_new_project(config, {"name": "Scope Read", "root_path": str(tmp_path / "workspace")})
    assert created["ok"] is True
    post_project_factory_scope_package(config, {})
    payload = get_project_factory_scope_package(config, {})
    assert payload["ok"] is True
    assert payload["scope_package_exists"] is True
    assert payload["project_id"] == created["active_project_id"]


def test_get_scope_package_with_no_active_project_returns_friendly_state(tmp_path: Path) -> None:
    config = _config(tmp_path)
    payload = get_project_factory_scope_package(config, {})
    assert payload["ok"] is True
    assert payload["scope_package_exists"] is False
    assert payload["warnings"]


def test_patch_scope_package_updates_scope(tmp_path: Path) -> None:
    config = _config(tmp_path)
    post_project_factory_new_project(config, {"name": "Scope Patch", "root_path": str(tmp_path / "workspace")})
    post_project_factory_scope_package(config, {})
    payload = patch_project_factory_scope_package(
        config,
        {"requirements": ["r1"], "acceptance_criteria": ["a1"], "notes": "n1"},
    )
    assert payload["ok"] is True
    assert payload["scope_package"]["requirements"] == ["r1"]
    assert payload["scope_package"]["lifecycle_state"] == "scope_draft_updated"


def test_post_scope_approve_validates_required_fields(tmp_path: Path) -> None:
    config = _config(tmp_path)
    post_project_factory_new_project(config, {"name": "Scope Approve", "root_path": str(tmp_path / "workspace")})
    post_project_factory_scope_package(config, {})
    payload = post_project_factory_scope_package_approve(config, {})
    assert payload["ok"] is False
    assert payload["_status"] == 400


def test_post_scope_approve_succeeds_for_valid_scope(tmp_path: Path) -> None:
    config = _config(tmp_path)
    post_project_factory_new_project(config, {"name": "Scope Approve Valid", "root_path": str(tmp_path / "workspace")})
    post_project_factory_scope_package(config, {})
    patch_project_factory_scope_package(config, {"requirements": ["r1"], "acceptance_criteria": ["a1"]})
    payload = post_project_factory_scope_package_approve(config, {})
    assert payload["ok"] is True
    assert payload["scope_package"]["lifecycle_state"] == "scope_approved"
