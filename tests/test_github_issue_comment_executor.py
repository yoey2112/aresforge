from __future__ import annotations

from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator import github_issue_comment_executor
from aresforge.operator.github_issue_comment_executor import (
    execute_github_issue_comment,
    load_comment_body,
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
        github_owner="yoey2112",
        github_repo="aresforge",
        ollama_model="qwen2.5:32b",
        artifact_root=artifact_root,
        prompts_dir=artifact_root / "prompts" / "generated",
        evidence_dir=artifact_root / "evidence" / "generated",
        codex_handoffs_dir=artifact_root / "codex_handoffs" / "generated",
    )


def test_execute_github_issue_comment_dry_run_default(tmp_path: Path) -> None:
    payload = execute_github_issue_comment(
        _config(tmp_path),
        issue_number=329,
        comment_body="Validation evidence scoped to #329.",
    )
    assert payload["ok"] is True
    assert payload["mode"] == "dry_run"
    assert payload["mutation_attempted"] is False
    assert payload["mutation_succeeded"] is False


def test_execute_github_issue_comment_blocks_parent_target_without_override(tmp_path: Path) -> None:
    payload = execute_github_issue_comment(
        _config(tmp_path),
        issue_number=326,
        parent_issue=326,
        comment_body="Should not target parent implicitly.",
    )
    assert payload["ok"] is False
    assert "parent_target_blocked_without_explicit_override" in payload["blocked_reasons"]


def test_execute_github_issue_comment_execute_requires_approval(tmp_path: Path) -> None:
    payload = execute_github_issue_comment(
        _config(tmp_path),
        issue_number=329,
        comment_body="Ready to execute without marker should fail.",
        execute=True,
    )
    assert payload["ok"] is False
    assert "approval_marker_required_for_execution" in payload["blocked_reasons"]


def test_execute_github_issue_comment_execute_mutates_when_approved(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        github_issue_comment_executor,
        "_run_gh_command",
        lambda _args: (0, "https://github.com/yoey2112/aresforge/issues/329#issuecomment-1\n", ""),
    )
    payload = execute_github_issue_comment(
        _config(tmp_path),
        issue_number=329,
        comment_body="Approved comment mutation.",
        execute=True,
        approval_marker="operator-approved",
    )
    assert payload["ok"] is True
    assert payload["mutation_attempted"] is True
    assert payload["mutation_succeeded"] is True
    assert "issuecomment-1" in str(payload["comment_url"])


def test_load_comment_body_from_file(tmp_path: Path) -> None:
    p = tmp_path / "comment.txt"
    p.write_text("Comment body from file.", encoding="utf-8")
    assert load_comment_body(inline_body=None, body_file=str(p)) == "Comment body from file."
