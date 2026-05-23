from __future__ import annotations

from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.github_mutation_audit_log import (
    append_github_mutation_audit_log,
    inspect_github_mutation_audit_log,
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
        github_owner="yoey2112",
        github_repo="aresforge",
    )


def test_inspect_mutation_audit_log_empty(tmp_path: Path) -> None:
    payload = inspect_github_mutation_audit_log(_config(tmp_path), limit=10)
    assert payload["ok"] is True
    assert payload["entry_count"] == 0


def test_append_and_inspect_mutation_audit_log(tmp_path: Path) -> None:
    config = _config(tmp_path)
    append_github_mutation_audit_log(
        config,
        record={
            "command": "plan-github-mutation",
            "mutation_intent": "issue_comment",
            "execution_result": "not_executed",
        },
    )
    append_github_mutation_audit_log(
        config,
        record={
            "command": "execute-github-issue-comment",
            "mutation_intent": "issue_comment",
            "execution_result": "succeeded",
        },
    )
    payload = inspect_github_mutation_audit_log(config, limit=1)
    assert payload["ok"] is True
    assert payload["entry_count"] == 2
    assert len(payload["entries"]) == 1
    latest = payload["entries"][0]
    assert latest["record"]["command"] == "execute-github-issue-comment"

