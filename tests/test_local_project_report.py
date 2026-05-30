import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.local_agent_profiles import init_agent_profiles
from aresforge.operator.local_active_project import set_active_project
from aresforge.operator.local_project_report import inspect_local_project_report
from aresforge.operator.local_project_queue import add_queue_item, complete_local_queue_item, init_project_queue
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


def _seed_self_managed_project_context(config: AppConfig, tmp_path: Path) -> None:
    assert init_managed_project_registry(config)["ok"] is True
    assert register_managed_project(
        config,
        project_id="aresforge",
        name="AresForge",
        root_path=str(tmp_path),
    )["ok"] is True
    assert register_managed_repo(
        config,
        project_id="aresforge",
        repo_id="aresforge-main",
        name="AresForge main",
        path=str(tmp_path),
        role="primary",
    )["ok"] is True
    assert init_project_queue(config)["ok"] is True
    assert init_agent_profiles(config, with_defaults=False)["ok"] is True
    assert set_active_project(config, project_id="aresforge")["ok"] is True


def _write_codex_run_state(
    repo_root: Path,
    *,
    item_id: str,
    run_id: str,
    dispatch_state: str,
    recovery: dict[str, str] | None = None,
) -> Path:
    run_dir = repo_root / ".aresforge" / "codex_dispatch" / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / "run_state.json"
    state = {
        "run_id": run_id,
        "item_id": item_id,
        "dispatch_state": dispatch_state,
        "review_evidence": [],
        "validation_evidence": [],
    }
    if recovery is not None:
        state["recovery"] = recovery
    path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    return path


def _valid_recovery() -> dict[str, str]:
    return {
        "recovered_at": "2026-05-30T04:30:00Z",
        "recovery_note": "Operator reviewed recovered dispatch state and completed queue evidence manually.",
    }


def test_local_project_report_has_stable_sections(tmp_path: Path) -> None:
    payload = inspect_local_project_report(_config(tmp_path))
    for key in (
        "report_type",
        "generated_at",
        "active_project",
        "project_health",
        "roadmap_summary",
        "queue_summary",
        "self_managed_readiness_summary",
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


def test_self_managed_report_treats_recovered_dispatch_runs_as_non_blocking(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_self_managed_project_context(config, tmp_path)
    assert add_queue_item(
        config,
        item_id="m81-local-llm-advisory-coding-lane-prototype",
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M81 Local LLM Advisory/Coding Lane Prototype",
        description="Completed advisory-only local LLM prototype.",
        status="in_progress",
        priority="normal",
        item_type="feature",
    )["ok"] is True
    assert complete_local_queue_item(
        config,
        item_id="m81-local-llm-advisory-coding-lane-prototype",
        commit_hash="abc123def",
        validation_summary="M81 validation passed locally.",
        evidence_note="Operator reviewed advisory-only local LLM evidence.",
        tests_run=["python -m pytest tests/test_cli.py tests/test_local_project_queue.py"],
    )["ok"] is True
    assert add_queue_item(
        config,
        item_id="m82-self-managed-aresforge-test-run",
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M82 Self-Managed AresForge Test Run",
        description="Dogfood AresForge local report and readiness flows.",
        status="ready",
        priority="normal",
        item_type="validation",
        dependencies=["m81-local-llm-advisory-coding-lane-prototype"],
    )["ok"] is True
    _write_codex_run_state(
        tmp_path,
        item_id="m81-local-llm-advisory-coding-lane-prototype",
        run_id="m81-recovered-run",
        dispatch_state="failed",
        recovery=_valid_recovery(),
    )

    payload = inspect_local_project_report(config)
    summary = payload["self_managed_readiness_summary"]

    assert summary["project_id"] == "aresforge"
    assert summary["managed_project_registered"] is True
    assert summary["active_project_selected"] is True
    assert summary["readiness_status"] == "ready"
    assert summary["m81_completed"] is True
    assert summary["m82_status"] == "ready"
    assert summary["recovered_dispatch_run_summary"]["non_blocking_count"] == 1
    assert summary["recovered_dispatch_run_summary"]["blocking_count"] == 0
    assert summary["recovered_dispatch_run_summary"]["recovered_runs_block_project_readiness"] is False
    assert summary["safety_boundary_confirmations"]["automatic_next_item_execution_allowed"] is False
    assert summary["safety_boundary_confirmations"]["unattended_multi_item_execution_allowed"] is False
    assert summary["safety_boundary_confirmations"]["github_api_allowed"] is False
    assert summary["safety_boundary_confirmations"]["gh_allowed"] is False
    assert summary["safety_boundary_confirmations"]["repo_mutation_allowed"] is False


def test_local_project_report_graceful_when_state_missing(tmp_path: Path) -> None:
    payload = inspect_local_project_report(_config(tmp_path))
    assert payload["ok"] is True
    assert isinstance(payload["warnings"], list)
    assert isinstance(payload["blockers"], list)
