from __future__ import annotations

import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.local_project_factory import (
    resolve_project_factory_dossier_path,
    start_new_project_factory,
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


def _payload(tmp_path: Path) -> dict[str, object]:
    return {
        "name": "Ares Wizard Project",
        "description": "Ship a local-first project-factory starter.",
        "project_type": "app",
        "preferred_stack": "python,fastapi",
        "root_path": str(tmp_path / "workspace"),
        "github_owner": "example-org",
        "github_repo": "ares-wizard-project",
        "github_mode": "create-later",
        "default_branch": "main",
        "initial_requirements": "Define scope and architecture before coding.",
        "tags": ["alpha", "wizard"],
    }


def test_start_new_project_factory_creates_expected_local_state(tmp_path: Path) -> None:
    config = _config(tmp_path)
    result = start_new_project_factory(config, _payload(tmp_path))

    assert result["ok"] is True
    assert result["local_only"] is True
    assert result["project"]["project_id"] == "ares-wizard-project"
    assert result["repo"]["repo_id"] == "ares-wizard-project-primary"
    assert result["active_project_id"] == "ares-wizard-project"
    assert result["scope_queue_item"]["title"] == "Scope project: Ares Wizard Project"
    assert result["scope_queue_item"]["item_type"] == "task"
    assert result["scope_queue_item"]["priority"] == "high"
    assert result["scope_queue_item"]["source"] == "hub-new-project-wizard"
    assert "project-factory" in result["scope_queue_item"]["tags"]
    assert "scope-project" in result["scope_queue_item"]["tags"]
    assert "new-project-wizard" in result["scope_queue_item"]["tags"]
    assert Path(str(result["dossier_path"])).exists()
    assert result["dossier"]["lifecycle_state"] == "intake_created"
    assert result["dossier"]["next_recommended_action"] == "scope_project"
    assert result["dossier"]["safety_boundary"]["local_only"] is True
    assert result["dossier"]["safety_boundary"]["github_mutation_status"] == "not_requested"
    assert result["dossier"]["safety_boundary"]["model_execution_status"] == "not_requested"


def test_start_new_project_factory_rejects_missing_project_name(tmp_path: Path) -> None:
    config = _config(tmp_path)
    payload = _payload(tmp_path)
    payload["name"] = " "

    result = start_new_project_factory(config, payload)

    assert result["ok"] is False
    assert result["error"] == "invalid_project_factory_payload"


def test_start_new_project_factory_auto_generates_project_id(tmp_path: Path) -> None:
    config = _config(tmp_path)
    payload = _payload(tmp_path)
    payload["project_id"] = ""
    payload["name"] = "My Cool New App"

    result = start_new_project_factory(config, payload)

    assert result["ok"] is True
    assert result["project"]["project_id"] == "my-cool-new-app"


def test_resolve_project_factory_dossier_path_uses_local_file_backed_location(tmp_path: Path) -> None:
    path = resolve_project_factory_dossier_path(tmp_path, "p1")
    normalized = str(path).replace("\\", "/")
    assert normalized.endswith(".aresforge/projects/p1/factory_dossier.json")


def test_start_new_project_factory_writes_dossier_json(tmp_path: Path) -> None:
    config = _config(tmp_path)
    result = start_new_project_factory(config, _payload(tmp_path))

    dossier_path = Path(str(result["dossier_path"]))
    rendered = json.loads(dossier_path.read_text(encoding="utf-8"))
    assert rendered["project_id"] == result["project"]["project_id"]
    assert rendered["name"] == "Ares Wizard Project"
    assert rendered["github_mode"] == "create-later"
