from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator import sequential_child_closeout_flow


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


def test_child_closeout_flow_is_dry_run_default(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        sequential_child_closeout_flow,
        "inspect_milestone_state",
        lambda _config, parent_issue: {
            "ok": True,
            "child_issues": [{"issue_number": 348, "state": "OPEN"}],
            "parent_issue": {"issue_number": parent_issue},
        },
    )
    payload = sequential_child_closeout_flow.run_sequential_child_closeout_flow(
        _config(tmp_path),
        parent_issue=345,
        child_issue=348,
        comment_body="evidence",
    )
    assert payload["ok"] is True
    assert payload["mode"] == "dry_run"
    assert payload["execution_results"]["issue_comment"] is None
    assert payload["execution_results"]["issue_close"] is None


def test_child_closeout_flow_blocks_parent_target(tmp_path: Path) -> None:
    payload = sequential_child_closeout_flow.run_sequential_child_closeout_flow(
        _config(tmp_path),
        parent_issue=345,
        child_issue=345,
        comment_body="blocked",
    )
    assert payload["ok"] is False
    assert "parent_target_forbidden_for_child_closeout_flow" in payload["blocked_reasons"]


def test_child_closeout_flow_execute_requires_approval(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        sequential_child_closeout_flow,
        "inspect_milestone_state",
        lambda _config, parent_issue: {
            "ok": True,
            "child_issues": [{"issue_number": 348, "state": "OPEN"}],
        },
    )
    payload = sequential_child_closeout_flow.run_sequential_child_closeout_flow(
        _config(tmp_path),
        parent_issue=345,
        child_issue=348,
        comment_body="evidence",
        execute=True,
    )
    assert payload["ok"] is False
    assert "approval_marker_required_for_execution" in payload["blocked_reasons"]


def test_child_closeout_flow_executes_targeted_comment_then_close(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        sequential_child_closeout_flow,
        "inspect_milestone_state",
        lambda _config, parent_issue: {
            "ok": True,
            "child_issues": [{"issue_number": 348, "state": "OPEN"}],
        },
    )
    monkeypatch.setattr(
        sequential_child_closeout_flow,
        "execute_github_issue_comment",
        lambda _config, **_kwargs: {"ok": True, "mutation_succeeded": True},
    )
    monkeypatch.setattr(
        sequential_child_closeout_flow,
        "execute_github_issue_close",
        lambda _config, **_kwargs: {"ok": True, "mutation_succeeded": True},
    )
    payload = sequential_child_closeout_flow.run_sequential_child_closeout_flow(
        _config(tmp_path),
        parent_issue=345,
        child_issue=348,
        comment_body="evidence",
        execute=True,
        approval_marker="operator-approved",
    )
    assert payload["ok"] is True
    assert payload["execution_results"]["issue_comment"]["ok"] is True
    assert payload["execution_results"]["issue_close"]["ok"] is True
