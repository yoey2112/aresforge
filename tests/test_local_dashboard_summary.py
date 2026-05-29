from __future__ import annotations

from pathlib import Path

from aresforge.config import AppConfig
from aresforge.hub.api import post_active_project, post_project, post_project_repo, post_queue_item
from aresforge.operator.local_dashboard_summary import summarize_hub_home_dashboard


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


def test_dashboard_summary_contract_is_stable_for_empty_local_state(tmp_path: Path) -> None:
    payload = summarize_hub_home_dashboard(_config(tmp_path))

    assert payload["ok"] is True
    assert payload["dashboard_type"] == "hub_home"
    assert set(payload.keys()) >= {
        "ok",
        "dashboard_type",
        "project_summary",
        "queue_summary",
        "agent_lane_summary",
        "repo_summary",
        "blockers",
        "warnings",
        "next_safe_action",
        "source_summary",
    }
    assert payload["project_summary"]["active_project_id"] == ""
    assert payload["queue_summary"]["total_items"] == 0
    assert payload["queue_summary"]["counts_by_status"] == {}
    assert isinstance(payload["blockers"], list)
    assert isinstance(payload["warnings"], list)
    assert isinstance(payload["source_summary"], list)
    assert isinstance(payload["next_safe_action"], str)
    assert payload["next_safe_action"]


def test_dashboard_summary_contract_reports_seeded_local_state(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert post_project(
        config,
        {
            "project_id": "aresforge",
            "name": "AresForge",
            "root_path": str(tmp_path),
            "status": "active",
        },
    )["ok"]
    assert post_project_repo(
        config,
        "aresforge",
        {
            "repo_id": "aresforge-primary",
            "name": "AresForge Repo",
            "path": str(tmp_path),
            "role": "primary",
            "status": "active",
        },
    )["ok"]
    assert post_active_project(config, {"project_id": "aresforge"})["ok"]
    assert post_queue_item(
        config,
        {
            "item_id": "q-ready",
            "project_id": "aresforge",
            "repo_id": "aresforge-primary",
            "title": "Ready task",
            "status": "ready",
            "priority": "normal",
            "item_type": "task",
            "assigned_agent": "agent-a",
        },
    )["ok"]

    payload = summarize_hub_home_dashboard(config)

    assert payload["ok"] is True
    assert payload["project_summary"]["total_projects"] == 1
    assert payload["project_summary"]["active_project_id"] == "aresforge"
    assert payload["queue_summary"]["total_items"] == 1
    assert payload["queue_summary"]["counts_by_status"]["ready"] == 1
    assert payload["agent_lane_summary"]["total_lanes"] >= 1
    assert payload["repo_summary"]["available"] is True
    assert isinstance(payload["blockers"], list)
    assert isinstance(payload["warnings"], list)
    assert isinstance(payload["next_safe_action"], str)
    assert payload["next_safe_action"]
