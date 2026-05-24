import json
from pathlib import Path

import pytest

from aresforge.config import AppConfig
from aresforge.operator import closeout_readiness_by_construction


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


def _ready_marker() -> dict:
    return {
        "state": "ready",
        "marker_complete": True,
        "missing_required_fields": [],
        "invalid_reasons": [],
        "post_hoc_marker_repair_required": False,
    }


def _incomplete_marker(*, missing: list[str] | None = None, invalid: list[str] | None = None, post_hoc: bool = True) -> dict:
    return {
        "state": "incomplete",
        "marker_complete": False,
        "missing_required_fields": missing or [],
        "invalid_reasons": invalid or [],
        "post_hoc_marker_repair_required": post_hoc,
    }


def _load_regression_fixtures() -> list[dict]:
    fixture_path = Path(__file__).parent / "fixtures" / "m25-readiness-by-construction-regression.json"
    return json.loads(fixture_path.read_text(encoding="utf-8"))


def _apply_marker_fixture(monkeypatch, scenario: dict) -> None:
    monkeypatch.setattr(
        closeout_readiness_by_construction,
        "generate_child_closeout_evidence_bundle",
        lambda _config, parent_issue, child_issue, marker_context=None: {"ok": True, "canonical_marker_completeness": scenario["child"]},
    )
    monkeypatch.setattr(
        closeout_readiness_by_construction,
        "generate_pr_evidence_bundle",
        lambda _config, issue_number, pr_number, marker_context=None: {"ok": True, "canonical_marker_completeness": scenario["pr"]},
    )
    monkeypatch.setattr(
        closeout_readiness_by_construction,
        "generate_parent_closeout_evidence_bundle",
        lambda _config, parent_issue: {"ok": True, "canonical_marker_completeness": scenario["parent"]},
    )
    monkeypatch.setattr(
        closeout_readiness_by_construction,
        "generate_evidence_comment_template",
        lambda _config, issue_number, parent_issue_override=None, marker_context=None: {"ok": True, "canonical_marker_completeness": scenario["closeout_comment"]},
    )


def _mock_common(monkeypatch) -> None:
    monkeypatch.setattr(
        closeout_readiness_by_construction,
        "inspect_milestone_state",
        lambda _config, parent_issue: {
            "ok": True,
            "child_issues": [{"issue_number": 422}, {"issue_number": 423}],
        },
    )
    monkeypatch.setattr(
        closeout_readiness_by_construction,
        "check_milestone_evidence_readiness",
        lambda _config, parent_issue: {
            "ok": True,
            "milestone_closeout_readiness": {"closeout_ready": True},
        },
    )
    monkeypatch.setattr(
        closeout_readiness_by_construction,
        "fetch_issue_details",
        lambda _config, issue_number: {
            "ok": True,
            "issue": {"merged_pr_evidence": [{"number": 431}]},
        },
    )


def test_check_closeout_readiness_by_construction_all_complete(monkeypatch, tmp_path: Path) -> None:
    _mock_common(monkeypatch)
    monkeypatch.setattr(
        closeout_readiness_by_construction,
        "generate_child_closeout_evidence_bundle",
        lambda _config, parent_issue, child_issue, marker_context=None: {"ok": True, "canonical_marker_completeness": _ready_marker()},
    )
    monkeypatch.setattr(
        closeout_readiness_by_construction,
        "generate_pr_evidence_bundle",
        lambda _config, issue_number, pr_number, marker_context=None: {"ok": True, "canonical_marker_completeness": _ready_marker()},
    )
    monkeypatch.setattr(
        closeout_readiness_by_construction,
        "generate_parent_closeout_evidence_bundle",
        lambda _config, parent_issue: {"ok": True, "canonical_marker_completeness": _ready_marker()},
    )
    monkeypatch.setattr(
        closeout_readiness_by_construction,
        "generate_evidence_comment_template",
        lambda _config, issue_number, parent_issue_override=None, marker_context=None: {"ok": True, "canonical_marker_completeness": _ready_marker()},
    )

    payload = closeout_readiness_by_construction.check_closeout_readiness_by_construction(_config(tmp_path), parent_issue=421)
    assert payload["ok"] is True
    assert payload["readiness_by_construction"]["ready"] is True
    assert payload["post_hoc_marker_repair_required"] is False


def test_check_closeout_readiness_by_construction_missing_child_marker(monkeypatch, tmp_path: Path) -> None:
    _mock_common(monkeypatch)
    monkeypatch.setattr(
        closeout_readiness_by_construction,
        "generate_child_closeout_evidence_bundle",
        lambda _config, parent_issue, child_issue, marker_context=None: {"ok": True, "canonical_marker_completeness": _incomplete_marker(missing=["branch_name"])},
    )
    monkeypatch.setattr(
        closeout_readiness_by_construction,
        "generate_pr_evidence_bundle",
        lambda _config, issue_number, pr_number, marker_context=None: {"ok": True, "canonical_marker_completeness": _ready_marker()},
    )
    monkeypatch.setattr(
        closeout_readiness_by_construction,
        "generate_parent_closeout_evidence_bundle",
        lambda _config, parent_issue: {"ok": True, "canonical_marker_completeness": _ready_marker()},
    )
    monkeypatch.setattr(
        closeout_readiness_by_construction,
        "generate_evidence_comment_template",
        lambda _config, issue_number, parent_issue_override=None, marker_context=None: {"ok": True, "canonical_marker_completeness": _ready_marker()},
    )
    payload = closeout_readiness_by_construction.check_closeout_readiness_by_construction(_config(tmp_path), parent_issue=421)
    assert payload["readiness_by_construction"]["ready"] is False
    assert "branch_name" in payload["missing_required_fields"]


def test_check_closeout_readiness_by_construction_missing_pr_marker(monkeypatch, tmp_path: Path) -> None:
    _mock_common(monkeypatch)
    monkeypatch.setattr(
        closeout_readiness_by_construction,
        "generate_child_closeout_evidence_bundle",
        lambda _config, parent_issue, child_issue, marker_context=None: {"ok": True, "canonical_marker_completeness": _ready_marker()},
    )
    monkeypatch.setattr(
        closeout_readiness_by_construction,
        "generate_pr_evidence_bundle",
        lambda _config, issue_number, pr_number, marker_context=None: {"ok": True, "canonical_marker_completeness": _incomplete_marker(missing=["merge_commit"])},
    )
    monkeypatch.setattr(
        closeout_readiness_by_construction,
        "generate_parent_closeout_evidence_bundle",
        lambda _config, parent_issue: {"ok": True, "canonical_marker_completeness": _ready_marker()},
    )
    monkeypatch.setattr(
        closeout_readiness_by_construction,
        "generate_evidence_comment_template",
        lambda _config, issue_number, parent_issue_override=None, marker_context=None: {"ok": True, "canonical_marker_completeness": _ready_marker()},
    )
    payload = closeout_readiness_by_construction.check_closeout_readiness_by_construction(_config(tmp_path), parent_issue=421)
    assert payload["readiness_by_construction"]["ready"] is False
    assert "merge_commit" in payload["missing_required_fields"]


def test_check_closeout_readiness_by_construction_missing_parent_marker(monkeypatch, tmp_path: Path) -> None:
    _mock_common(monkeypatch)
    monkeypatch.setattr(
        closeout_readiness_by_construction,
        "generate_child_closeout_evidence_bundle",
        lambda _config, parent_issue, child_issue, marker_context=None: {"ok": True, "canonical_marker_completeness": _ready_marker()},
    )
    monkeypatch.setattr(
        closeout_readiness_by_construction,
        "generate_pr_evidence_bundle",
        lambda _config, issue_number, pr_number, marker_context=None: {"ok": True, "canonical_marker_completeness": _ready_marker()},
    )
    monkeypatch.setattr(
        closeout_readiness_by_construction,
        "generate_parent_closeout_evidence_bundle",
        lambda _config, parent_issue: {"ok": True, "canonical_marker_completeness": _incomplete_marker(missing=["final_main_head"])},
    )
    monkeypatch.setattr(
        closeout_readiness_by_construction,
        "generate_evidence_comment_template",
        lambda _config, issue_number, parent_issue_override=None, marker_context=None: {"ok": True, "canonical_marker_completeness": _ready_marker()},
    )
    payload = closeout_readiness_by_construction.check_closeout_readiness_by_construction(_config(tmp_path), parent_issue=421)
    assert payload["readiness_by_construction"]["ready"] is False
    assert "final_main_head" in payload["missing_required_fields"]


def test_check_closeout_readiness_by_construction_missing_closeout_comment_marker(monkeypatch, tmp_path: Path) -> None:
    _mock_common(monkeypatch)
    monkeypatch.setattr(
        closeout_readiness_by_construction,
        "generate_child_closeout_evidence_bundle",
        lambda _config, parent_issue, child_issue, marker_context=None: {"ok": True, "canonical_marker_completeness": _ready_marker()},
    )
    monkeypatch.setattr(
        closeout_readiness_by_construction,
        "generate_pr_evidence_bundle",
        lambda _config, issue_number, pr_number, marker_context=None: {"ok": True, "canonical_marker_completeness": _ready_marker()},
    )
    monkeypatch.setattr(
        closeout_readiness_by_construction,
        "generate_parent_closeout_evidence_bundle",
        lambda _config, parent_issue: {"ok": True, "canonical_marker_completeness": _ready_marker()},
    )
    monkeypatch.setattr(
        closeout_readiness_by_construction,
        "generate_evidence_comment_template",
        lambda _config, issue_number, parent_issue_override=None, marker_context=None: {"ok": True, "canonical_marker_completeness": _incomplete_marker(invalid=["parent_issue_lineage_not_detected"])},
    )
    payload = closeout_readiness_by_construction.check_closeout_readiness_by_construction(_config(tmp_path), parent_issue=421)
    assert payload["readiness_by_construction"]["ready"] is False
    assert "parent_issue_lineage_not_detected" in payload["invalid_reasons"]


def test_check_closeout_readiness_by_construction_post_hoc_repair_true_not_ready(monkeypatch, tmp_path: Path) -> None:
    _mock_common(monkeypatch)
    monkeypatch.setattr(
        closeout_readiness_by_construction,
        "generate_child_closeout_evidence_bundle",
        lambda _config, parent_issue, child_issue, marker_context=None: {"ok": True, "canonical_marker_completeness": _incomplete_marker(post_hoc=True)},
    )
    monkeypatch.setattr(
        closeout_readiness_by_construction,
        "generate_pr_evidence_bundle",
        lambda _config, issue_number, pr_number, marker_context=None: {"ok": True, "canonical_marker_completeness": _ready_marker()},
    )
    monkeypatch.setattr(
        closeout_readiness_by_construction,
        "generate_parent_closeout_evidence_bundle",
        lambda _config, parent_issue: {"ok": True, "canonical_marker_completeness": _ready_marker()},
    )
    monkeypatch.setattr(
        closeout_readiness_by_construction,
        "generate_evidence_comment_template",
        lambda _config, issue_number, parent_issue_override=None, marker_context=None: {"ok": True, "canonical_marker_completeness": _ready_marker()},
    )
    payload = closeout_readiness_by_construction.check_closeout_readiness_by_construction(_config(tmp_path), parent_issue=421)
    assert payload["post_hoc_marker_repair_required"] is True
    assert payload["readiness_by_construction"]["ready"] is False


def test_check_closeout_readiness_by_construction_remains_read_only(monkeypatch, tmp_path: Path) -> None:
    _mock_common(monkeypatch)
    monkeypatch.setattr(
        closeout_readiness_by_construction,
        "generate_child_closeout_evidence_bundle",
        lambda _config, parent_issue, child_issue, marker_context=None: {"ok": True, "canonical_marker_completeness": _ready_marker()},
    )
    monkeypatch.setattr(
        closeout_readiness_by_construction,
        "generate_pr_evidence_bundle",
        lambda _config, issue_number, pr_number, marker_context=None: {"ok": True, "canonical_marker_completeness": _ready_marker()},
    )
    monkeypatch.setattr(
        closeout_readiness_by_construction,
        "generate_parent_closeout_evidence_bundle",
        lambda _config, parent_issue: {"ok": True, "canonical_marker_completeness": _ready_marker()},
    )
    monkeypatch.setattr(
        closeout_readiness_by_construction,
        "generate_evidence_comment_template",
        lambda _config, issue_number, parent_issue_override=None, marker_context=None: {"ok": True, "canonical_marker_completeness": _ready_marker()},
    )
    payload = closeout_readiness_by_construction.check_closeout_readiness_by_construction(_config(tmp_path), parent_issue=421)
    assert payload["read_only"] is True
    assert payload["mutation"]["attempted"] is False
    assert payload["mutation"]["comment_on_issue"] is False
    assert payload["mutation"]["close_issues"] is False
    assert payload["mutation"]["create_pr"] is False
    assert payload["mutation"]["merge_pr"] is False


@pytest.mark.parametrize("scenario", _load_regression_fixtures(), ids=lambda item: item["name"])
def test_m25_regression_fixtures_no_post_hoc_marker_repair_needed(monkeypatch, tmp_path: Path, scenario: dict) -> None:
    _mock_common(monkeypatch)
    _apply_marker_fixture(monkeypatch, scenario)

    payload = closeout_readiness_by_construction.check_closeout_readiness_by_construction(_config(tmp_path), parent_issue=421)

    assert payload["ok"] is True
    assert payload["read_only"] is True
    assert payload["readiness_by_construction"]["ready"] is scenario["expected_ready"]
    assert payload["post_hoc_marker_repair_required"] is scenario["expected_post_hoc"]

    for expected_reason in scenario["expected_blocked_reasons"]:
        assert expected_reason in payload["blocked_reasons"]

    if scenario["expected_ready"]:
        assert payload["readiness_by_construction"]["marker_emission_ready"] is True
        assert payload["missing_required_fields"] == []
        assert payload["invalid_reasons"] == []
        assert payload["recommended_actions"] == [
            "Readiness by construction is satisfied; proceed with standard human-gated closeout flow."
        ]
    else:
        assert payload["readiness_by_construction"]["marker_emission_ready"] is False
        assert any("Regenerate affected evidence artifacts/comments" in action for action in payload["recommended_actions"])


def test_check_closeout_readiness_by_construction_uses_parent_child_pr_mapping(monkeypatch, tmp_path: Path) -> None:
    _mock_common(monkeypatch)
    monkeypatch.setattr(
        closeout_readiness_by_construction,
        "check_milestone_evidence_readiness",
        lambda _config, parent_issue: {
            "ok": True,
            "issues": [
                {"issue": {"number": 422, "merged_pr_evidence": []}},
                {"issue": {"number": 423, "merged_pr_evidence": []}},
            ],
            "milestone_closeout_readiness": {"closeout_ready": True},
        },
    )
    monkeypatch.setattr(
        closeout_readiness_by_construction,
        "generate_parent_closeout_evidence_bundle",
        lambda _config, parent_issue: {
            "ok": True,
            "canonical_marker_completeness": _ready_marker(),
            "child_pr_mappings": [
                {"issue_number": 422, "merged_pr_urls": ["https://github.com/yoey2112/aresforge/pull/431"]},
                {"issue_number": 423, "merged_pr_urls": ["https://github.com/yoey2112/aresforge/pull/432"]},
            ],
        },
    )
    monkeypatch.setattr(
        closeout_readiness_by_construction,
        "fetch_issue_details",
        lambda _config, issue_number: {
            "ok": True,
            "issue": {"state": "CLOSED", "merged_pr_evidence": []},
        },
    )
    monkeypatch.setattr(
        closeout_readiness_by_construction,
        "generate_child_closeout_evidence_bundle",
        lambda _config, parent_issue, child_issue, marker_context=None: {"ok": True, "canonical_marker_completeness": _ready_marker()},
    )
    monkeypatch.setattr(
        closeout_readiness_by_construction,
        "generate_evidence_comment_template",
        lambda _config, issue_number, parent_issue_override=None, marker_context=None: {"ok": True, "canonical_marker_completeness": _ready_marker()},
    )

    observed_pairs: set[tuple[int, int]] = set()

    def _pr_bundle(_config, issue_number, pr_number, marker_context=None):
        observed_pairs.add((issue_number, pr_number))
        return {
            "ok": True,
            "pr": {"head_branch": "m25/test", "merge_commit": "abc123", "files_changed": ["src/file.py"]},
            "canonical_marker_completeness": _ready_marker(),
        }

    monkeypatch.setattr(closeout_readiness_by_construction, "generate_pr_evidence_bundle", _pr_bundle)

    payload = closeout_readiness_by_construction.check_closeout_readiness_by_construction(_config(tmp_path), parent_issue=421)
    assert payload["readiness_by_construction"]["ready"] is True
    assert observed_pairs == {(422, 431), (423, 432)}


def test_check_closeout_readiness_by_construction_stays_blocked_when_pr_mapping_missing(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _mock_common(monkeypatch)
    monkeypatch.setattr(
        closeout_readiness_by_construction,
        "fetch_issue_details",
        lambda _config, issue_number: {
            "ok": True,
            "issue": {"state": "CLOSED", "merged_pr_evidence": []},
        },
    )

    def _child_bundle(_config, parent_issue, child_issue, marker_context=None):
        marker_context = marker_context or {}
        if marker_context.get("pr"):
            return {"ok": True, "canonical_marker_completeness": _ready_marker()}
        return {"ok": True, "canonical_marker_completeness": _incomplete_marker(missing=["pr"])}

    monkeypatch.setattr(closeout_readiness_by_construction, "generate_child_closeout_evidence_bundle", _child_bundle)
    monkeypatch.setattr(
        closeout_readiness_by_construction,
        "generate_pr_evidence_bundle",
        lambda _config, issue_number, pr_number, marker_context=None: {"ok": True, "canonical_marker_completeness": _ready_marker()},
    )
    monkeypatch.setattr(
        closeout_readiness_by_construction,
        "generate_parent_closeout_evidence_bundle",
        lambda _config, parent_issue: {"ok": True, "canonical_marker_completeness": _ready_marker(), "child_pr_mappings": []},
    )
    monkeypatch.setattr(
        closeout_readiness_by_construction,
        "generate_evidence_comment_template",
        lambda _config, issue_number, parent_issue_override=None, marker_context=None: {"ok": True, "canonical_marker_completeness": _ready_marker()},
    )
    monkeypatch.setattr(
        closeout_readiness_by_construction,
        "check_milestone_evidence_readiness",
        lambda _config, parent_issue: {
            "ok": True,
            "issues": [{"issue": {"number": 422, "merged_pr_evidence": []}}],
            "milestone_closeout_readiness": {"closeout_ready": True},
        },
    )

    payload = closeout_readiness_by_construction.check_closeout_readiness_by_construction(_config(tmp_path), parent_issue=421)
    assert payload["readiness_by_construction"]["ready"] is False
    assert "pr" in payload["missing_required_fields"]
