from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.local_agent_profiles import init_agent_profiles, register_agent_profile, register_handoff_target
from aresforge.operator.local_project_dashboard import KEY_DOCS, summarize_local_project_dashboard
from aresforge.operator.local_project_queue import add_queue_item, init_project_queue
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


def _seed_docs(tmp_path: Path) -> None:
    for relative_path in KEY_DOCS:
        path = tmp_path / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# seeded\n", encoding="utf-8")


def test_dashboard_missing_files_returns_warnings_and_empty_summaries(tmp_path: Path) -> None:
    payload = summarize_local_project_dashboard(_config(tmp_path))

    assert payload["local_only"] is True
    assert payload["report_only"] is True
    assert payload["project_summary"]["project_count"] == 0
    assert payload["repo_summary"]["repo_count"] == 0
    assert payload["queue_summary"]["item_count"] == 0
    assert payload["agent_summary"]["agent_count"] == 0
    assert payload["warnings"]


def test_dashboard_project_repo_and_agent_counts_from_local_state(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_docs(tmp_path)

    assert init_managed_project_registry(config)["ok"] is True
    assert register_managed_project(
        config,
        project_id="p1",
        name="Project One",
        root_path=str(tmp_path),
        status="active",
    )["ok"] is True
    assert register_managed_repo(
        config,
        project_id="p1",
        repo_id="r1",
        name="Repo One",
        path=str(tmp_path),
        status="active",
        role="primary",
    )["ok"] is True

    assert init_agent_profiles(config)["ok"] is True
    assert register_handoff_target(
        config,
        target_id="t1",
        name="Target One",
        target_type="codex_prompt",
        status="active",
    )["ok"] is True
    assert register_agent_profile(
        config,
        agent_id="a1",
        name="Agent One",
        role="implementer",
        execution_mode="codex",
        status="active",
        escalation_allowed=True,
        handoff_target_id="t1",
    )["ok"] is True

    payload = summarize_local_project_dashboard(config)

    assert payload["project_summary"]["project_count"] == 1
    assert payload["repo_summary"]["repo_count"] == 1
    assert payload["agent_summary"]["agent_count"] == 1
    assert payload["agent_summary"]["handoff_target_count"] == 1
    assert payload["agent_summary"]["escalation_enabled_count"] == 1


def test_dashboard_queue_counts_action_center_and_readiness(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_docs(tmp_path)

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
    )["ok"] is True

    assert init_project_queue(config)["ok"] is True
    assert add_queue_item(
        config,
        item_id="q1",
        project_id="p1",
        repo_id="r1",
        title="Urgent Blocked",
        status="blocked",
        priority="urgent",
        item_type="task",
    )["ok"] is True
    assert add_queue_item(
        config,
        item_id="q2",
        project_id="p1",
        repo_id="r1",
        title="High Ready",
        status="ready",
        priority="high",
        item_type="feature",
    )["ok"] is True

    payload = summarize_local_project_dashboard(config)
    queue = payload["queue_summary"]
    action_center = payload["action_center"]

    assert queue["item_count"] == 2
    assert queue["counts_by_status"]["blocked"] == 1
    assert queue["counts_by_status"]["ready"] == 1
    assert queue["counts_by_priority"]["urgent"] == 1
    assert queue["counts_by_priority"]["high"] == 1
    assert len(queue["blocked_items"]) == 1
    assert "q2" in queue["ready_items"]
    assert action_center["blocked_work_items"]
    assert action_center["urgent_or_high_priority_items"]
    assert "overall_status" in payload["readiness_indicators"]


def test_dashboard_docs_workflows_and_boundaries_present(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_docs(tmp_path)

    payload = summarize_local_project_dashboard(config)

    assert payload["docs_summary"]["docs_ready"] is True
    assert payload["docs_summary"]["missing_docs"] == []
    assert payload["operator_workflows"]
    assert any(item["workflow_id"] == "start-new-project" for item in payload["operator_workflows"])
    assert payload["boundary_confirmations"]
    assert any("No GitHub calls" in item for item in payload["boundary_confirmations"])
