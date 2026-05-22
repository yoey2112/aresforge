from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator import self_managed_milestone_planner as planner


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
        github_owner="yoey2112",
        github_repo="aresforge",
    )


def _seed_docs(repo_root: Path) -> None:
    for relative in (
        "docs/context/BUILD_STATE.md",
        "docs/context/AGENT_CONTEXT.md",
        "docs/roadmap/ROADMAP.md",
        "docs/operator/LOCAL_OPERATOR_USAGE.md",
        "docs/architecture/SELF_MANAGED_MILESTONE_PLANNING_CONTRACT.md",
    ):
        path = repo_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"# {relative}\n", encoding="utf-8")


def test_plan_is_deterministic_for_same_inputs(monkeypatch, tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_docs(config.repo_root)
    monkeypatch.setattr(planner, "inspect_repo_governance", lambda _config: {"ok": True, "warnings": []})
    monkeypatch.setattr(
        planner,
        "list_ready_issues",
        lambda _config: {"issue_count": 1, "issues": [{"number": 252}]},
    )
    monkeypatch.setattr(
        planner,
        "project_state_summary",
        lambda _config: {"repository": {"working_tree_clean": True}, "github": {"open_issues_count": 1, "open_prs_count": 0}},
    )

    first = planner.plan_self_managed_milestone(config, mode="read-only")
    second = planner.plan_self_managed_milestone(config, mode="read-only")

    assert first["ok"] is True
    assert second["ok"] is True
    assert first["planning"]["target_issue"] == 252
    assert first["planning"]["dependency_order"] == [250, 251, 252, 253]
    assert first["planning"]["issue_sequence"] == second["planning"]["issue_sequence"]


def test_local_write_persists_run_and_steps_without_github_mutation(monkeypatch, tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_docs(config.repo_root)
    captured: dict[str, object] = {}

    monkeypatch.setattr(planner, "inspect_repo_governance", lambda _config: {"ok": True, "warnings": []})
    monkeypatch.setattr(
        planner,
        "list_ready_issues",
        lambda _config: {"issue_count": 1, "issues": [{"number": 252}]},
    )
    monkeypatch.setattr(
        planner,
        "project_state_summary",
        lambda _config: {"repository": {"working_tree_clean": True}, "github": {"open_issues_count": 1, "open_prs_count": 0}},
    )
    monkeypatch.setattr(
        planner,
        "_persist_autonomous_run",
        lambda _conn, **kwargs: captured.setdefault("run", kwargs),
    )
    monkeypatch.setattr(planner, "_load_latest_autonomous_run", lambda _conn: None)
    monkeypatch.setattr(
        planner,
        "_persist_run_steps",
        lambda _conn, **kwargs: captured.setdefault("steps", kwargs),
    )

    class _DummyConn:
        pass

    payload = planner.plan_self_managed_milestone(config, mode="local-write", conn=_DummyConn())

    assert payload["ok"] is True
    assert payload["mode"] == "local-write"
    assert payload["db_write"]["ok"] is True
    assert captured["run"]["run"]["target_issue"] == 252
    assert len(captured["steps"]["steps"]) == 3
    assert payload["planning"]["selected_agent"] == "model-routing-agent"


def test_planner_advances_closed_previous_target_to_new_ready_issue(monkeypatch, tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_docs(config.repo_root)

    monkeypatch.setattr(planner, "inspect_repo_governance", lambda _config: {"ok": True, "warnings": []})
    monkeypatch.setattr(
        planner,
        "list_ready_issues",
        lambda _config: {"issue_count": 1, "issues": [{"number": 252}]},
    )
    monkeypatch.setattr(
        planner,
        "project_state_summary",
        lambda _config: {"repository": {"working_tree_clean": True}, "github": {"open_issues_count": 1, "open_prs_count": 0}},
    )
    monkeypatch.setattr(
        planner,
        "_load_latest_autonomous_run",
        lambda _conn: {"run_id": "run-old", "target_issue": 251},
    )
    monkeypatch.setattr(
        planner,
        "fetch_issue_details",
        lambda _config, _issue: {"ok": True, "issue": {"state": "CLOSED"}},
    )
    monkeypatch.setattr(planner, "_persist_autonomous_run", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(planner, "_persist_run_steps", lambda *_args, **_kwargs: None)

    class _DummyConn:
        pass

    payload = planner.plan_self_managed_milestone(config, mode="local-write", conn=_DummyConn())
    assert payload["ok"] is True
    assert payload["planning"]["previous_target_issue"] == 251
    assert payload["planning"]["closed_previous_target_issues"] == [251]
    assert payload["planning"]["target_issue"] == 252


def test_unsupported_modes_fail_safely(tmp_path: Path) -> None:
    config = _config(tmp_path)
    for mode in ("branch-write", "pr-write", "closeout-write", "full-auto"):
        payload = planner.plan_self_managed_milestone(config, mode=mode)
        assert payload["ok"] is False
        assert payload["error"] == "mode_not_implemented"


def test_local_write_requires_connection(tmp_path: Path) -> None:
    config = _config(tmp_path)
    payload = planner.plan_self_managed_milestone(config, mode="local-write", conn=None)
    assert payload == {
        "command": "plan-self-managed-milestone",
        "ok": False,
        "mode": "local-write",
        "error": "local_write_requires_database_connection",
    }
