from pathlib import Path
from datetime import datetime

from aresforge.config import AppConfig
from aresforge.hub.api import get_active_project_workspace, post_project, post_project_repo, post_queue_item, post_active_project


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


def test_workspace_endpoint_empty(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    payload = get_active_project_workspace(cfg)
    assert payload.get("ok") is True
    # local-only and report-only flags
    assert payload.get("local_only") is True
    assert payload.get("report_only") is True
    # active project not selected initially
    assert bool(payload.get("active_project_selected")) is False
    assert payload.get("active_project_id", "") == ""
    # payload shape
    assert isinstance(payload.get("active_project_summary"), dict)
    assert isinstance(payload.get("current_queue_items"), list)
    assert isinstance(payload.get("recent_completed_queue_items"), list)
    assert isinstance(payload.get("report_status"), dict)
    assert isinstance(payload.get("repo_status"), dict)
    assert isinstance(payload.get("next_safe_action"), str)


def test_workspace_endpoint_with_active_project_and_queue(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    # create a project and repo
    proj = {
        "project_id": "p1",
        "name": "Project One",
        "root_path": str(cfg.repo_root),
        "status": "active",
        "default_branch": "main",
    }
    r = post_project(cfg, proj)
    assert r.get("ok") is True

    repo = {
        "repo_id": "r1",
        "name": "Repo One",
        "path": str(cfg.repo_root),
        "role": "primary",
        "status": "active",
    }
    rr = post_project_repo(cfg, "p1", repo)
    assert rr.get("ok") is True

    # seed a couple of queue items
    q1 = {
        "item_id": "q1",
        "project_id": "p1",
        "repo_id": "r1",
        "title": "Open Item",
        "status": "ready",
        "priority": "normal",
        "item_type": "task",
    }
    q2 = {
        "item_id": "q2",
        "project_id": "p1",
        "repo_id": "r1",
        "title": "Completed Item",
        "status": "done",
        "priority": "low",
        "item_type": "task",
        "updated_at": datetime.utcnow().isoformat(),
    }
    assert post_queue_item(cfg, q1).get("ok") is True
    assert post_queue_item(cfg, q2).get("ok") is True

    # set the created project as the active project
    assert post_active_project(cfg, {"project_id": "p1"}).get("ok") is True

    payload = get_active_project_workspace(cfg)
    assert payload.get("ok") is True
    # Active project should now be selected
    assert payload.get("active_project_selected") is True
    assert payload.get("active_project_id") == "p1"
    # current items should include q1
    current = payload.get("current_queue_items", [])
    assert any(item.get("item_id") == "q1" for item in current)
    # recently completed should include q2
    recent = payload.get("recent_completed_queue_items", [])
    assert any(item.get("item_id") == "q2" for item in recent)
    # next safe action exists
    assert isinstance(payload.get("next_safe_action"), str)
