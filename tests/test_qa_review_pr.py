import json
from pathlib import Path

import pytest

from aresforge.config import AppConfig
from aresforge.operator import qa_pr_validation
from aresforge.operator.qa_pr_validation import qa_review_pr


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


def _pr_payload(**overrides: object) -> dict[str, object]:
    base = {
        "number": 118,
        "title": "M2 sprint: QA agent validation contract for pull requests",
        "state": "OPEN",
        "isDraft": False,
        "mergeStateStatus": "CLEAN",
        "baseRefName": "main",
        "headRefName": "m2/sprint-118-qa-pr-validation-contract",
        "url": "https://github.com/yoey2112/aresforge/pull/118",
        "body": "Closes #118",
        "files": [
            {"path": "src/aresforge/cli.py"},
            {"path": "docs/context/BUILD_STATE.md"},
        ],
        "closingIssuesReferences": [{"number": 118}],
        "mergeable": "MERGEABLE",
    }
    base.update(overrides)
    return base


def _stub_pr_view(monkeypatch: pytest.MonkeyPatch, payload: dict[str, object]) -> None:
    def fake_run(_args: list[str]) -> tuple[int, str, str]:
        return 0, json.dumps(payload), ""

    monkeypatch.setattr(qa_pr_validation, "_run_gh_command", fake_run)


def _write_evidence(tmp_path: Path, filename: str, content: str) -> None:
    evidence_dir = tmp_path / "artifacts" / "evidence" / "generated"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    (evidence_dir / filename).write_text(content, encoding="utf-8")


def test_qa_review_pr_passes_with_evidence_and_docs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config = make_config(tmp_path)
    _write_evidence(tmp_path, "20260520T120001Z-issue-118-evidence.json", "issue #118")
    _stub_pr_view(monkeypatch, _pr_payload())

    payload = qa_review_pr(config, 118)

    assert payload["qa_decision"] == "pass"
    assert payload["documentation_update_required"] is True
    assert payload["documentation_update_detected"] is True
    assert payload["validation_evidence_found"] is True


def test_qa_review_pr_blocks_draft_pr(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config = make_config(tmp_path)
    _stub_pr_view(monkeypatch, _pr_payload(isDraft=True))

    payload = qa_review_pr(config, 118)

    assert payload["qa_decision"] == "blocked"
    assert "pr_not_draft" in payload["failed_gates"]


def test_qa_review_pr_blocks_unclean_pr(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config = make_config(tmp_path)
    _stub_pr_view(monkeypatch, _pr_payload(mergeStateStatus="DIRTY"))

    payload = qa_review_pr(config, 118)

    assert payload["qa_decision"] == "blocked"
    assert "merge_state_clean" in payload["failed_gates"]


def test_qa_review_pr_blocks_missing_linked_issue(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config = make_config(tmp_path)
    _stub_pr_view(monkeypatch, _pr_payload(body="No issue reference", closingIssuesReferences=[]))

    payload = qa_review_pr(config, 118)

    assert payload["qa_decision"] == "blocked"
    assert payload["linked_issue_number"] is None


def test_qa_review_pr_fails_when_evidence_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config = make_config(tmp_path)
    _stub_pr_view(monkeypatch, _pr_payload())

    payload = qa_review_pr(config, 118)

    assert payload["qa_decision"] == "fail"
    assert "validation_evidence_present" in payload["failed_gates"]
    assert "required_tests_passed" in payload["failed_gates"]


def test_qa_review_pr_fails_when_docs_required_but_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config = make_config(tmp_path)
    _write_evidence(tmp_path, "20260520T120002Z-issue-118-evidence.json", "issue #118")
    _stub_pr_view(
        monkeypatch,
        _pr_payload(files=[{"path": "src/aresforge/cli.py"}]),
    )

    payload = qa_review_pr(config, 118)

    assert payload["documentation_update_required"] is True
    assert payload["documentation_update_detected"] is False
    assert payload["qa_decision"] == "fail"


def test_qa_review_pr_flags_protected_issue_risk(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config = make_config(tmp_path)
    _write_evidence(tmp_path, "20260520T120003Z-issue-118-evidence.json", "issue #118")
    _stub_pr_view(
        monkeypatch,
        _pr_payload(closingIssuesReferences=[{"number": 39}], body="Closes #39"),
    )

    payload = qa_review_pr(config, 118)

    assert payload["protected_issue_status"] == "linked_to_protected_issue"
    assert "protected_issue_untouched" in payload["failed_gates"]


def test_qa_review_pr_payload_is_deterministic_json(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config = make_config(tmp_path)
    _stub_pr_view(monkeypatch, _pr_payload())

    payload = qa_review_pr(config, 118)

    assert json.loads(json.dumps(payload)) == payload


def test_qa_review_pr_accepts_pr_body_validation_evidence_without_local_packages(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config = make_config(tmp_path)
    body = """
## Summary
Docs-only reconciliation.

## Validation evidence
- python -m pytest
- Result: passed
- Passed: 194 passed
- python -m aresforge inspect-repo-governance
- python -m aresforge managed-repo-readiness-report
- python -m aresforge plan-repo-bootstrap
- python -m aresforge demo-managed-repo-governance
"""
    _stub_pr_view(monkeypatch, _pr_payload(number=150, body=body, closingIssuesReferences=[{"number": 146}]))

    payload = qa_review_pr(config, 150)

    assert payload["validation_evidence_found"] is True
    assert payload["validation_heading_found"] is True
    assert payload["validation_command_evidence_found"] is True
    assert payload["validation_pass_signal_found"] is True
    assert "validation_evidence_present" in payload["passed_gates"]
    assert "required_tests_passed" in payload["passed_gates"]
    assert "validation_evidence_present" not in payload["failed_gates"]
    assert "required_tests_passed" not in payload["failed_gates"]


def test_qa_review_pr_rejects_heading_without_command_evidence(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config = make_config(tmp_path)
    body = """
## Validation evidence
Result: passed
"""
    _stub_pr_view(monkeypatch, _pr_payload(body=body))

    payload = qa_review_pr(config, 118)

    assert payload["validation_heading_found"] is True
    assert payload["validation_command_evidence_found"] is False
    assert payload["validation_pass_signal_found"] is True
    assert payload["validation_evidence_found"] is False
    assert "validation_evidence_present" in payload["failed_gates"]
    assert "required_tests_passed" in payload["failed_gates"]


def test_qa_review_pr_rejects_command_without_pass_signal(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config = make_config(tmp_path)
    body = """
## Required tests
- python -m pytest
"""
    _stub_pr_view(monkeypatch, _pr_payload(body=body))

    payload = qa_review_pr(config, 118)

    assert payload["validation_heading_found"] is True
    assert payload["validation_command_evidence_found"] is True
    assert payload["validation_pass_signal_found"] is False
    assert payload["validation_evidence_found"] is False
    assert "validation_evidence_present" in payload["failed_gates"]
    assert "required_tests_passed" in payload["failed_gates"]


def test_qa_review_pr_rejects_vague_pass_claim_without_command(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config = make_config(tmp_path)
    body = """
## Test evidence
All tests are fine.
"""
    _stub_pr_view(monkeypatch, _pr_payload(body=body))

    payload = qa_review_pr(config, 118)

    assert payload["validation_heading_found"] is True
    assert payload["validation_command_evidence_found"] is False
    assert payload["validation_pass_signal_found"] is False
    assert payload["validation_evidence_found"] is False
    assert "validation_evidence_present" in payload["failed_gates"]
    assert "required_tests_passed" in payload["failed_gates"]


def test_qa_review_pr_uses_read_only_pr_view(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config = make_config(tmp_path)
    calls: list[list[str]] = []

    def fake_run(args: list[str]) -> tuple[int, str, str]:
        calls.append(args)
        return 0, json.dumps(_pr_payload()), ""

    monkeypatch.setattr(qa_pr_validation, "_run_gh_command", fake_run)

    qa_review_pr(config, 118)

    assert calls
    assert calls[0][:2] == ["pr", "view"]
