import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.batch_readiness_report import report_batch_readiness


def make_config(tmp_path: Path) -> AppConfig:
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


def test_report_batch_readiness_with_explicit_inputs(tmp_path: Path) -> None:
    config = make_config(tmp_path)

    payload = report_batch_readiness(
        config,
        issue_numbers=[165, 166, 169, 170],
        changed_files=["src/aresforge/cli.py", "docs/context/BUILD_STATE.md"],
        validations=["python -m pytest", "python -m aresforge inspect-repo-governance"],
        pr_number=200,
    )

    assert payload["ok"] is True
    assert payload["pr_number"] == 200
    assert payload["pr_readiness"]["readiness"] == "ready_for_human_review"
    assert payload["pr_readiness"]["unresolved_gates"] == []
    assert json.loads(json.dumps(payload)) == payload


def test_report_batch_readiness_flags_missing_gates_and_protected_issue(tmp_path: Path) -> None:
    config = make_config(tmp_path)

    payload = report_batch_readiness(
        config,
        issue_numbers=[39, 170],
        changed_files=["src/aresforge/cli.py"],
        validations=[],
    )

    gates = payload["pr_readiness"]["unresolved_gates"]
    assert "protected_issue_in_scope" in gates
    assert "missing_validation_evidence" in gates
    assert "missing_docs_reconciliation" in gates
    assert payload["pr_readiness"]["readiness"] == "not_ready"
