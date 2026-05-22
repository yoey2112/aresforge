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
        lambda *_args, **_kwargs: {
            "ok": True,
            "pr_number": 401,
            "pr_url": "https://github.com/yoey2112/aresforge/pull/401",
        },
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
    assert payload["run"]["pr_url"] == "https://github.com/yoey2112/aresforge/pull/401"
    pr_step = next(item for item in payload["run_steps"] if item["step_type"] == "gh_pr_create")
    assert pr_step["outputs"]["pr_url"] == "https://github.com/yoey2112/aresforge/pull/401"


def test_closeout_gate_requires_pr_url() -> None:
    gate = autonomous_cycle._evaluate_closeout_gate(
        run={"validation_status": "passed", "target_issue": 263, "pr_number": 266}
    )

    assert gate["ok"] is False
    assert "pr_url_missing" in gate["failed_gates"]


def test_create_pr_extracts_number_and_url_from_create_stdout(monkeypatch, tmp_path: Path) -> None:
    class _Result:
        def __init__(self, returncode: int, stdout: str, stderr: str = "") -> None:
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = stderr

    calls = {"count": 0}

    def _fake_run(*_args, **_kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            return _Result(
                0,
                "https://github.com/yoey2112/aresforge/pull/266\n",
                "",
            )
        return _Result(1, "", "view unavailable")

    monkeypatch.setattr(autonomous_cycle.subprocess, "run", _fake_run)

    payload = autonomous_cycle._create_pr(
        repo_slug="yoey2112/aresforge",
        title="t",
        body="b",
        base="main",
        head="codex/m16-262",
        cwd=tmp_path,
    )

    assert payload["ok"] is True
    assert payload["pr_number"] == 266
    assert payload["pr_url"] == "https://github.com/yoey2112/aresforge/pull/266"


def test_create_pr_treats_existing_pr_detection_as_success(monkeypatch, tmp_path: Path) -> None:
    class _Result:
        def __init__(self, returncode: int, stdout: str, stderr: str = "") -> None:
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = stderr

    calls = {"count": 0}

    def _fake_run(*_args, **_kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            return _Result(
                1,
                "",
                'a pull request for branch "codex/m16-261-real-success-path" into branch "main" already exists:\n'
                "https://github.com/yoey2112/aresforge/pull/266",
            )
        return _Result(
            0,
            '{"number":266,"url":"https://github.com/yoey2112/aresforge/pull/266"}',
            "",
        )

    monkeypatch.setattr(autonomous_cycle.subprocess, "run", _fake_run)

    payload = autonomous_cycle._create_pr(
        repo_slug="yoey2112/aresforge",
        title="t",
        body="b",
        base="main",
        head="codex/m16-262",
        cwd=tmp_path,
    )

    assert payload["ok"] is True
    assert payload["existing_pr_detected"] is True
    assert payload["pr_number"] == 266
    assert payload["pr_url"] == "https://github.com/yoey2112/aresforge/pull/266"


def test_closeout_eligible_fails_closed_when_pr_not_merged(monkeypatch, tmp_path: Path) -> None:
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
        lambda *_args, **_kwargs: {"ok": True, "branch": "codex/m16-262"},
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
        "_resolve_closeout_pr_binding",
        lambda *_args, **_kwargs: {
            "ok": True,
            "pr_number": 267,
            "pr_url": "https://github.com/yoey2112/aresforge/pull/267",
            "links_target_issue": True,
        },
    )
    monkeypatch.setattr(
        autonomous_cycle,
        "_inspect_pr_merge_state",
        lambda *_args, **_kwargs: {
            "ok": True,
            "pr_number": 267,
            "pr_url": "https://github.com/yoey2112/aresforge/pull/267",
            "state": "OPEN",
            "merged_at": None,
            "merged": False,
            "links_target_issue": True,
        },
    )
    close_called = {"called": False}

    def _close_issue(*_args, **_kwargs):
        close_called["called"] = True
        return {"ok": True}

    monkeypatch.setattr(autonomous_cycle, "_close_issue", _close_issue)

    payload = autonomous_cycle.run_autonomous_cycle(
        config,
        conn=_DummyConn(),
        mode=autonomous_cycle.MODE_CLOSEOUT_ELIGIBLE,
        parent_issue=258,
        target_issue=262,
        branch_name="codex/m16-262",
        commit_message="m16 closeout",
        pr_title="m16 pr",
        pr_number=267,
        validation_commands=["python -m pytest"],
    )

    assert payload["ok"] is False
    assert payload["error"] == "closeout_gate_failed"
    assert close_called["called"] is False
    close_gate = next(
        item for item in payload["run_steps"] if item["step_type"] == "evaluate_closeout_eligibility"
    )
    assert "pr_not_merged" in close_gate["outputs"]["failed_gates"]


def test_closeout_eligible_closes_only_target_issue_when_pr_merged(monkeypatch, tmp_path: Path) -> None:
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
        lambda *_args, **_kwargs: {"ok": True, "branch": "codex/m16-262"},
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
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("closeout-eligible must not create PRs")
        ),
    )
    monkeypatch.setattr(
        autonomous_cycle,
        "_resolve_closeout_pr_binding",
        lambda *_args, **_kwargs: {
            "ok": True,
            "pr_number": 266,
            "pr_url": "https://github.com/yoey2112/aresforge/pull/266",
            "links_target_issue": True,
        },
    )
    monkeypatch.setattr(
        autonomous_cycle,
        "_inspect_pr_merge_state",
        lambda *_args, **_kwargs: {
            "ok": True,
            "pr_number": 266,
            "pr_url": "https://github.com/yoey2112/aresforge/pull/266",
            "state": "MERGED",
            "merged_at": "2026-05-22T00:00:00Z",
            "merged": True,
            "links_target_issue": True,
        },
    )
    closed_issue = {"issue": None}

    def _close_issue(*, repo_slug: str, issue_number: int, cwd: Path):
        _ = repo_slug
        _ = cwd
        closed_issue["issue"] = issue_number
        return {"ok": True, "stdout": "closed", "stderr": ""}

    monkeypatch.setattr(autonomous_cycle, "_close_issue", _close_issue)

    payload = autonomous_cycle.run_autonomous_cycle(
        config,
        conn=_DummyConn(),
        mode=autonomous_cycle.MODE_CLOSEOUT_ELIGIBLE,
        parent_issue=258,
        target_issue=262,
        branch_name="codex/m16-262",
        commit_message="m16 closeout",
        pr_title="m16 pr",
        pr_number=266,
        validation_commands=["python -m pytest"],
    )

    assert payload["ok"] is True
    assert closed_issue["issue"] == 262
    merge_step = next(item for item in payload["run_steps"] if item["step_type"] == "inspect_pr_merge_state")
    assert merge_step["outputs"]["merged"] is True


def test_closeout_eligible_fails_when_bound_merged_pr_does_not_link_target_issue(
    monkeypatch, tmp_path: Path
) -> None:
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
        "_resolve_closeout_pr_binding",
        lambda *_args, **_kwargs: {
            "ok": True,
            "pr_number": 500,
            "pr_url": "https://github.com/yoey2112/aresforge/pull/500",
            "links_target_issue": False,
        },
    )
    monkeypatch.setattr(
        autonomous_cycle,
        "_inspect_pr_merge_state",
        lambda *_args, **_kwargs: {
            "ok": True,
            "pr_number": 500,
            "pr_url": "https://github.com/yoey2112/aresforge/pull/500",
            "state": "MERGED",
            "merged_at": "2026-05-22T00:00:00Z",
            "merged": True,
            "links_target_issue": False,
        },
    )
    monkeypatch.setattr(
        autonomous_cycle,
        "_close_issue",
        lambda *_args, **_kwargs: {"ok": True},
    )

    payload = autonomous_cycle.run_autonomous_cycle(
        config,
        conn=_DummyConn(),
        mode=autonomous_cycle.MODE_CLOSEOUT_ELIGIBLE,
        parent_issue=258,
        target_issue=262,
        pr_number=500,
        validation_commands=["python -m pytest"],
    )

    assert payload["ok"] is False
    close_gate = next(
        item for item in payload["run_steps"] if item["step_type"] == "evaluate_closeout_eligibility"
    )
    assert "pr_target_link_missing" in close_gate["outputs"]["failed_gates"]
