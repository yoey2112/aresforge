from __future__ import annotations

from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator import github_issue_close_executor
from aresforge.operator.github_issue_close_executor import execute_github_issue_close


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


def test_execute_github_issue_close_dry_run_child_ready(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        github_issue_close_executor,
        "check_issue_evidence_readiness",
        lambda _config, issue_number: {"ok": True, "classification": "ready", "issue": {"number": issue_number}},
    )
    payload = execute_github_issue_close(
        _config(tmp_path),
        issue_target="330",
        parent_issue=326,
    )
    assert payload["ok"] is True
    assert payload["mode"] == "dry_run"
    assert payload["mutation_attempted"] is False


def test_execute_github_issue_close_blocks_range_targets(tmp_path: Path) -> None:
    payload = execute_github_issue_close(
        _config(tmp_path),
        issue_target="330-334",
        parent_issue=326,
    )
    assert payload["ok"] is False
    assert "invalid_issue_target_format" in payload["blocked_reasons"]


def test_execute_github_issue_close_blocks_unready_child(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        github_issue_close_executor,
        "check_issue_evidence_readiness",
        lambda _config, issue_number: {"ok": True, "classification": "not_ready", "issue": {"number": issue_number}},
    )
    payload = execute_github_issue_close(
        _config(tmp_path),
        issue_target="330",
        parent_issue=326,
    )
    assert payload["ok"] is False
    assert "child_issue_evidence_readiness_not_satisfied" in payload["blocked_reasons"]


def test_execute_github_issue_close_parent_requires_parent_readiness(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        github_issue_close_executor,
        "inspect_parent_closeout_readiness",
        lambda _config, parent_issue: {
            "ok": True,
            "closeout_readiness": {"parent_closeout_ready": False},
            "parent_issue": {"issue_number": parent_issue},
        },
    )
    payload = execute_github_issue_close(
        _config(tmp_path),
        issue_target="326",
        parent_issue=326,
    )
    assert payload["ok"] is False
    assert "parent_closeout_readiness_not_satisfied" in payload["blocked_reasons"]


def test_execute_github_issue_close_execute_requires_approval(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        github_issue_close_executor,
        "check_issue_evidence_readiness",
        lambda _config, issue_number: {"ok": True, "classification": "ready", "issue": {"number": issue_number}},
    )
    payload = execute_github_issue_close(
        _config(tmp_path),
        issue_target="330",
        parent_issue=326,
        execute=True,
    )
    assert payload["ok"] is False
    assert "approval_marker_required_for_execution" in payload["blocked_reasons"]


def test_execute_github_issue_close_execute_success(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        github_issue_close_executor,
        "check_issue_evidence_readiness",
        lambda _config, issue_number: {"ok": True, "classification": "ready", "issue": {"number": issue_number}},
    )
    monkeypatch.setattr(github_issue_close_executor, "_run_gh_command", lambda _args: (0, "", ""))
    payload = execute_github_issue_close(
        _config(tmp_path),
        issue_target="330",
        parent_issue=326,
        execute=True,
        approval_marker="operator-approved",
    )
    assert payload["ok"] is True
    assert payload["mutation_attempted"] is True
    assert payload["mutation_succeeded"] is True

