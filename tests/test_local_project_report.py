from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.local_agent_profiles import init_agent_profiles
from aresforge.operator.local_active_project import set_active_project
from aresforge.operator.local_project_report import inspect_local_project_report
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


def _seed_active_project_context(config: AppConfig, tmp_path: Path) -> None:
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
    assert init_project_queue(config)["ok"] is True
    assert init_agent_profiles(config, with_defaults=False)["ok"] is True
    assert set_active_project(config, project_id="p1")["ok"] is True


def test_local_project_report_has_stable_sections(tmp_path: Path) -> None:
    payload = inspect_local_project_report(_config(tmp_path))
    for key in (
        "report_type",
        "generated_at",
        "active_project",
        "project_health",
        "roadmap_summary",
        "queue_summary",
        "validation_summary",
        "documentation_summary",
        "blockers",
        "warnings",
        "recommended_next_action",
    ):
        assert key in payload


def test_local_project_report_active_project_awareness(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_active_project_context(config, tmp_path)
    assert add_queue_item(
        config,
        item_id="q1",
        project_id="p1",
        repo_id="r1",
        title="Ready Work",
        status="ready",
        priority="high",
    )["ok"] is True

    payload = inspect_local_project_report(config)
    assert payload["active_project"]["active_project_selected"] is True
    assert payload["active_project"]["active_project_id"] == "p1"
    assert payload["queue_summary"]["item_count"] == 1


def test_local_project_report_excludes_completed_item_assignment_warnings(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_active_project_context(config, tmp_path)
    assert add_queue_item(
        config,
        item_id="done-dashboard",
        project_id="p1",
        repo_id="r1",
        title="Completed dashboard item",
        status="done",
        priority="high",
        item_type="dashboard",
    )["ok"] is True

    payload = inspect_local_project_report(config)
    warnings = payload["warnings"]
    assert not any("No suitable active agent found for item 'done-dashboard'" in warning for warning in warnings)
    assert not any("No recommended handoff target found for item 'done-dashboard'" in warning for warning in warnings)


def test_local_project_report_retains_active_item_assignment_warnings(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_active_project_context(config, tmp_path)
    assert add_queue_item(
        config,
        item_id="ready-dashboard",
        project_id="p1",
        repo_id="r1",
        title="Active dashboard item",
        status="ready",
        priority="high",
        item_type="dashboard",
    )["ok"] is True

    payload = inspect_local_project_report(config)
    warnings = payload["warnings"]
    assert any("No suitable active agent found for item 'ready-dashboard'" in warning for warning in warnings)
    assert any("No recommended handoff target found for item 'ready-dashboard'" in warning for warning in warnings)


def test_local_project_report_graceful_when_state_missing(tmp_path: Path) -> None:
    payload = inspect_local_project_report(_config(tmp_path))
    assert payload["ok"] is True
    assert isinstance(payload["warnings"], list)
    assert isinstance(payload["blockers"], list)
