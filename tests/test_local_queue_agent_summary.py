from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.local_queue_agent_summary import inspect_local_queue_agent_summary
from aresforge.operator.local_project_queue import add_queue_item, init_project_queue


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


def test_queue_agent_summary_keys_are_stable(tmp_path: Path) -> None:
    payload = inspect_local_queue_agent_summary(_config(tmp_path))
    for key in (
        "queue_totals",
        "items_by_status",
        "items_by_agent",
        "blocked_items",
        "next_ready_items",
        "active_project",
        "next_safe_action",
    ):
        assert key in payload


def test_queue_agent_summary_groups_status_and_agents(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_project_queue(config)["ok"] is True
    assert add_queue_item(
        config,
        item_id="q1",
        project_id="p1",
        repo_id="r1",
        title="Blocked work",
        status="blocked",
        priority="urgent",
        assigned_agent="agent-a",
    )["ok"] is True
    assert add_queue_item(
        config,
        item_id="q2",
        project_id="p1",
        repo_id="r1",
        title="Ready work",
        status="ready",
        priority="high",
        assigned_agent="",
    )["ok"] is True

    payload = inspect_local_queue_agent_summary(config)
    assert payload["queue_totals"]["item_count"] == 2
    assert payload["queue_totals"]["status_counts"]["blocked"] == 1
    assert payload["queue_totals"]["status_counts"]["ready"] == 1
    assert payload["items_by_status"]["blocked"][0]["item_id"] == "q1"
    assert payload["items_by_status"]["ready"][0]["item_id"] == "q2"
    assert payload["items_by_agent"]["agent-a"][0]["item_id"] == "q1"
    assert payload["items_by_agent"]["unassigned"][0]["item_id"] == "q2"
    assert payload["blocked_items"][0]["item_id"] == "q1"
    assert payload["next_ready_items"][0]["item_id"] == "q2"
