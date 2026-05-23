from __future__ import annotations

from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator import pr_body_update_helper
from aresforge.operator.pr_body_update_helper import prepare_pr_body_update


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


def test_prepare_pr_body_update_dry_run(tmp_path: Path) -> None:
    payload = prepare_pr_body_update(
        _config(tmp_path),
        pr_number=339,
        target_issue=331,
        scope_summary="Summarize changes for child #331.",
        files_changed=["src/aresforge/cli.py"],
        validation_results=["python -m pytest -> pass"],
        safety_notes=["Dry-run default enforced."],
    )
    assert payload["ok"] is True
    assert payload["mode"] == "dry_run"
    assert "Target PR: #339" in payload["dry_run_rendered_body"]
    assert "```" not in payload["dry_run_rendered_body"]


def test_prepare_pr_body_update_execute_requires_approval(tmp_path: Path) -> None:
    payload = prepare_pr_body_update(
        _config(tmp_path),
        pr_number=339,
        target_issue=331,
        scope_summary="Summary",
        files_changed=[],
        validation_results=[],
        safety_notes=[],
        execute=True,
    )
    assert payload["ok"] is False
    assert "approval_marker_required_for_execution" in payload["blocked_reasons"]


def test_prepare_pr_body_update_execute_success(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(pr_body_update_helper, "_run_gh_command", lambda _args: (0, "", ""))
    payload = prepare_pr_body_update(
        _config(tmp_path),
        pr_number=339,
        target_issue=331,
        scope_summary="Summary",
        files_changed=["src/aresforge/cli.py"],
        validation_results=["python -m pytest -> pass"],
        safety_notes=["Dry-run default enforced."],
        execute=True,
        approval_marker="operator-approved",
    )
    assert payload["ok"] is True
    assert payload["mutation_attempted"] is True
    assert payload["mutation_succeeded"] is True

