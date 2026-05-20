from pathlib import Path

import pytest

from aresforge.config import AppConfig
from aresforge.operator import validate_pr_end_to_end as module
from aresforge.operator.validate_pr_end_to_end import validate_pr_end_to_end


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


def test_validate_pr_end_to_end_passes_when_qa_review_passes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config = make_config(tmp_path)
    monkeypatch.setattr(
        module,
        "qa_review_pr",
        lambda _config, _pr: {
            "repo": "yoey2112/aresforge",
            "qa_decision": "pass",
            "merge_eligible": True,
            "closeout_eligible": True,
            "changed_files": ["src/aresforge/cli.py", "docs/operator/LOCAL_OPERATOR_USAGE.md"],
            "failed_gates": [],
            "required_fixes": [],
        },
    )

    payload = validate_pr_end_to_end(config, 149)

    assert payload["command"] == "validate-pr-end-to-end"
    assert payload["ok"] is True
    assert payload["end_to_end_decision"] == "pass"
    assert payload["merge_eligible"] is True
    assert payload["closeout_eligible"] is True


def test_validate_pr_end_to_end_fails_when_qa_review_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config = make_config(tmp_path)
    monkeypatch.setattr(
        module,
        "qa_review_pr",
        lambda _config, _pr: {
            "repo": "yoey2112/aresforge",
            "qa_decision": "fail",
            "merge_eligible": False,
            "closeout_eligible": False,
            "changed_files": ["src/aresforge/cli.py"],
            "failed_gates": ["validation_evidence_present", "required_tests_passed"],
            "required_fixes": ["Add explicit validation command and pass signal evidence."],
        },
    )

    payload = validate_pr_end_to_end(config, 149)

    assert payload["ok"] is False
    assert payload["end_to_end_decision"] == "fail"
    assert payload["merge_eligible"] is False
    assert payload["closeout_eligible"] is False
    assert payload["required_fixes"] == ["Add explicit validation command and pass signal evidence."]


def test_validate_pr_end_to_end_includes_boundary_confirmations_and_commands(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config = make_config(tmp_path)
    monkeypatch.setattr(
        module,
        "qa_review_pr",
        lambda _config, _pr: {
            "repo": "yoey2112/aresforge",
            "qa_decision": "fail",
            "merge_eligible": False,
            "closeout_eligible": False,
            "changed_files": [],
            "failed_gates": ["validation_evidence_present"],
            "required_fixes": ["Add validation evidence."],
        },
    )

    payload = validate_pr_end_to_end(config, 149)

    assert "validate-pr-end-to-end is read-only." in payload["boundary_confirmations"]
    assert "No autonomous GitHub mutation introduced." in payload["boundary_confirmations"]
    assert "python -m pytest" in payload["required_operator_validation_commands"]
    assert "inspect-repo-governance" in " ".join(payload["required_operator_validation_commands"])
    assert "recommended_next_action" in payload


def test_validate_pr_end_to_end_does_not_call_mutation_paths(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config = make_config(tmp_path)
    monkeypatch.setattr(
        module,
        "qa_review_pr",
        lambda _config, _pr: {
            "repo": "yoey2112/aresforge",
            "qa_decision": "pass",
            "merge_eligible": True,
            "closeout_eligible": True,
            "changed_files": [],
            "failed_gates": [],
            "required_fixes": [],
        },
    )
    monkeypatch.setattr(
        module,
        "_recommended_next_action",
        lambda **kwargs: "ok",
    )

    payload = validate_pr_end_to_end(config, 149)

    assert payload["ok"] is True
