from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator import sequential_closeout_execution_package


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


def test_generate_execution_package_is_read_only_and_targeted(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        sequential_closeout_execution_package,
        "fetch_issue_details",
        lambda _config, issue_number: {
            "ok": True,
            "issue": {
                "number": issue_number,
                "body": "Parent issue: #345",
                "comments": [{"body": "Issue #349\nImplemented by PR #400\nMerged main commit after PR merge: abcdef1234567"}],
            },
        },
    )
    monkeypatch.setattr(
        sequential_closeout_execution_package,
        "inspect_github_mutation_audit_log",
        lambda _config, limit=20: {"log_path": "C:/tmp/audit.jsonl", "entry_count": 3, "entries": []},
    )
    payload = sequential_closeout_execution_package.generate_sequential_closeout_execution_package(
        _config(tmp_path),
        parent_issue=345,
        child_issue=349,
        pr_url="https://github.com/yoey2112/aresforge/pull/400",
        validation_results=["python -m pytest: pass"],
    )
    assert payload["ok"] is True
    assert payload["read_only"] is True
    assert payload["targeted_closeout_payload"]["target_issue"] == 349
    assert payload["targeted_closeout_payload"]["bulk_closeout_allowed"] is False
    assert payload["evidence_payload"]["pr_payload"]["mapped_pr_number"] == 400


def test_generate_execution_package_fails_when_issue_lookup_fails(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        sequential_closeout_execution_package,
        "fetch_issue_details",
        lambda _config, _issue_number: {"ok": False, "error": "gh_cli_failed"},
    )
    payload = sequential_closeout_execution_package.generate_sequential_closeout_execution_package(
        _config(tmp_path),
        parent_issue=345,
        child_issue=349,
    )
    assert payload["ok"] is False
    assert payload["error"] == "gh_cli_failed"
