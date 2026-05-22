from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator import autonomous_cycle


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
    ):
        path = repo_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("ok\n", encoding="utf-8")


class _DummyConn:
    pass


def test_dry_run_is_non_mutating_and_completes(monkeypatch, tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_docs(config.repo_root)

    monkeypatch.setattr(autonomous_cycle, "_upsert_run", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(autonomous_cycle, "_persist_step_results", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        autonomous_cycle,
        "_write_evidence",
        lambda *_args, **_kwargs: {"markdown_path": "m.md", "json_path": "m.json"},
    )
    monkeypatch.setattr(
        autonomous_cycle,
        "_run_validations",
        lambda *_args, **_kwargs: [{"command": "python -m pytest", "ok": True, "exit_code": 0}],
    )

    payload = autonomous_cycle.run_autonomous_cycle(
        config,
        conn=_DummyConn(),
        mode=autonomous_cycle.MODE_DRY_RUN,
        parent_issue=258,
        target_issue=259,
        validation_commands=["python -m pytest"],
    )

    assert payload["ok"] is True
    assert payload["mode"] == autonomous_cycle.MODE_DRY_RUN
    assert payload["run"]["status"] == "completed"
    assert all("gh_" not in step["step_type"] for step in payload["run_steps"])


def test_branch_write_requires_inputs_and_fails_closed(monkeypatch, tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_docs(config.repo_root)
    monkeypatch.setattr(autonomous_cycle, "_upsert_run", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(autonomous_cycle, "_persist_step_results", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        autonomous_cycle,
        "_write_evidence",
        lambda *_args, **_kwargs: {"markdown_path": "m.md", "json_path": "m.json"},
    )

    payload = autonomous_cycle.run_autonomous_cycle(
        config,
        conn=_DummyConn(),
        mode=autonomous_cycle.MODE_BRANCH_WRITE,
        parent_issue=258,
        target_issue=261,
        validation_commands=["python -m pytest"],
    )

    assert payload["ok"] is False
    assert payload["error"] == "safety_gates_failed"
    assert payload["run_steps"][0]["step_type"] == "evaluate_safety_gates"
    assert "branch_name_required" in payload["run_steps"][0]["outputs"]["failed_gates"]


def test_push_pr_mode_records_pr_step(monkeypatch, tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_docs(config.repo_root)
    monkeypatch.setattr(autonomous_cycle, "_upsert_run", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(autonomous_cycle, "_persist_step_results", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        autonomous_cycle,
        "_write_evidence",
        lambda *_args, **_kwargs: {"markdown_path": "m.md", "json_path": "m.json"},
    )
    monkeypatch.setattr(
        autonomous_cycle,
        "_run_validations",
        lambda *_args, **_kwargs: [{"command": "python -m pytest", "ok": True, "exit_code": 0}],
    )
    monkeypatch.setattr(
        autonomous_cycle,
        "_ensure_branch",
        lambda *_args, **_kwargs: {"ok": True, "branch": "codex/m16-261"},
    )
    monkeypatch.setattr(
        autonomous_cycle,
        "_create_commit",
        lambda *_args, **_kwargs: {"ok": True, "commit_hash": "abc123"},
    )
    monkeypatch.setattr(
        autonomous_cycle,
        "_push_branch",
        lambda *_args, **_kwargs: {"ok": True},
    )
    monkeypatch.setattr(
        autonomous_cycle,
        "_create_pr",
        lambda *_args, **_kwargs: {"ok": True, "pr_number": 401},
    )

    payload = autonomous_cycle.run_autonomous_cycle(
        config,
        conn=_DummyConn(),
        mode=autonomous_cycle.MODE_PUSH_PR,
        parent_issue=258,
        target_issue=262,
        branch_name="codex/m16-262",
        commit_message="m16 push-pr",
        pr_title="m16 pr",
        validation_commands=["python -m pytest"],
    )

    assert payload["ok"] is True
    steps = [item["step_type"] for item in payload["run_steps"]]
    assert "git_push_branch" in steps
    assert "gh_pr_create" in steps
    assert payload["run"]["pr_number"] == 401
