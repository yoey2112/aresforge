from pathlib import Path

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
        lambda _config, parent_issue, child_issue: {"ok": True, "canonical_marker_completeness": _ready_marker()},
    )
    monkeypatch.setattr(
        closeout_readiness_by_construction,
        "generate_pr_evidence_bundle",
        lambda _config, issue_number, pr_number: {"ok": True, "canonical_marker_completeness": _ready_marker()},
    )
    monkeypatch.setattr(
        closeout_readiness_by_construction,
        "generate_parent_closeout_evidence_bundle",
        lambda _config, parent_issue: {"ok": True, "canonical_marker_completeness": _ready_marker()},
    )
    monkeypatch.setattr(
        closeout_readiness_by_construction,
        "generate_evidence_comment_template",
        lambda _config, issue_number: {"ok": True, "canonical_marker_completeness": _ready_marker()},
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
        lambda _config, parent_issue, child_issue: {"ok": True, "canonical_marker_completeness": _incomplete_marker(missing=["branch_name"])},
    )
    monkeypatch.setattr(
        closeout_readiness_by_construction,
        "generate_pr_evidence_bundle",
        lambda _config, issue_number, pr_number: {"ok": True, "canonical_marker_completeness": _ready_marker()},
    )
    monkeypatch.setattr(
        closeout_readiness_by_construction,
        "generate_parent_closeout_evidence_bundle",
        lambda _config, parent_issue: {"ok": True, "canonical_marker_completeness": _ready_marker()},
    )
    monkeypatch.setattr(
        closeout_readiness_by_construction,
        "generate_evidence_comment_template",
        lambda _config, issue_number: {"ok": True, "canonical_marker_completeness": _ready_marker()},
    )
    payload = closeout_readiness_by_construction.check_closeout_readiness_by_construction(_config(tmp_path), parent_issue=421)
    assert payload["readiness_by_construction"]["ready"] is False
    assert "branch_name" in payload["missing_required_fields"]


def test_check_closeout_readiness_by_construction_missing_pr_marker(monkeypatch, tmp_path: Path) -> None:
    _mock_common(monkeypatch)
    monkeypatch.setattr(
        closeout_readiness_by_construction,
        "generate_child_closeout_evidence_bundle",
        lambda _config, parent_issue, child_issue: {"ok": True, "canonical_marker_completeness": _ready_marker()},
    )
    monkeypatch.setattr(
        closeout_readiness_by_construction,
        "generate_pr_evidence_bundle",
        lambda _config, issue_number, pr_number: {"ok": True, "canonical_marker_completeness": _incomplete_marker(missing=["merge_commit"])},
    )
    monkeypatch.setattr(
        closeout_readiness_by_construction,
        "generate_parent_closeout_evidence_bundle",
        lambda _config, parent_issue: {"ok": True, "canonical_marker_completeness": _ready_marker()},
    )
    monkeypatch.setattr(
        closeout_readiness_by_construction,
        "generate_evidence_comment_template",
        lambda _config, issue_number: {"ok": True, "canonical_marker_completeness": _ready_marker()},
    )
    payload = closeout_readiness_by_construction.check_closeout_readiness_by_construction(_config(tmp_path), parent_issue=421)
    assert payload["readiness_by_construction"]["ready"] is False
    assert "merge_commit" in payload["missing_required_fields"]


def test_check_closeout_readiness_by_construction_missing_parent_marker(monkeypatch, tmp_path: Path) -> None:
    _mock_common(monkeypatch)
    monkeypatch.setattr(
        closeout_readiness_by_construction,
        "generate_child_closeout_evidence_bundle",
        lambda _config, parent_issue, child_issue: {"ok": True, "canonical_marker_completeness": _ready_marker()},
    )
    monkeypatch.setattr(
        closeout_readiness_by_construction,
        "generate_pr_evidence_bundle",
        lambda _config, issue_number, pr_number: {"ok": True, "canonical_marker_completeness": _ready_marker()},
    )
    monkeypatch.setattr(
        closeout_readiness_by_construction,
        "generate_parent_closeout_evidence_bundle",
        lambda _config, parent_issue: {"ok": True, "canonical_marker_completeness": _incomplete_marker(missing=["final_main_head"])},
    )
    monkeypatch.setattr(
        closeout_readiness_by_construction,
        "generate_evidence_comment_template",
        lambda _config, issue_number: {"ok": True, "canonical_marker_completeness": _ready_marker()},
    )
    payload = closeout_readiness_by_construction.check_closeout_readiness_by_construction(_config(tmp_path), parent_issue=421)
    assert payload["readiness_by_construction"]["ready"] is False
    assert "final_main_head" in payload["missing_required_fields"]


def test_check_closeout_readiness_by_construction_missing_closeout_comment_marker(monkeypatch, tmp_path: Path) -> None:
    _mock_common(monkeypatch)
    monkeypatch.setattr(
        closeout_readiness_by_construction,
        "generate_child_closeout_evidence_bundle",
        lambda _config, parent_issue, child_issue: {"ok": True, "canonical_marker_completeness": _ready_marker()},
    )
    monkeypatch.setattr(
        closeout_readiness_by_construction,
        "generate_pr_evidence_bundle",
        lambda _config, issue_number, pr_number: {"ok": True, "canonical_marker_completeness": _ready_marker()},
    )
    monkeypatch.setattr(
        closeout_readiness_by_construction,
        "generate_parent_closeout_evidence_bundle",
        lambda _config, parent_issue: {"ok": True, "canonical_marker_completeness": _ready_marker()},
    )
    monkeypatch.setattr(
        closeout_readiness_by_construction,
        "generate_evidence_comment_template",
        lambda _config, issue_number: {"ok": True, "canonical_marker_completeness": _incomplete_marker(invalid=["parent_issue_lineage_not_detected"])},
    )
    payload = closeout_readiness_by_construction.check_closeout_readiness_by_construction(_config(tmp_path), parent_issue=421)
    assert payload["readiness_by_construction"]["ready"] is False
    assert "parent_issue_lineage_not_detected" in payload["invalid_reasons"]


def test_check_closeout_readiness_by_construction_post_hoc_repair_true_not_ready(monkeypatch, tmp_path: Path) -> None:
    _mock_common(monkeypatch)
    monkeypatch.setattr(
        closeout_readiness_by_construction,
        "generate_child_closeout_evidence_bundle",
        lambda _config, parent_issue, child_issue: {"ok": True, "canonical_marker_completeness": _incomplete_marker(post_hoc=True)},
    )
    monkeypatch.setattr(
        closeout_readiness_by_construction,
        "generate_pr_evidence_bundle",
        lambda _config, issue_number, pr_number: {"ok": True, "canonical_marker_completeness": _ready_marker()},
    )
    monkeypatch.setattr(
        closeout_readiness_by_construction,
        "generate_parent_closeout_evidence_bundle",
        lambda _config, parent_issue: {"ok": True, "canonical_marker_completeness": _ready_marker()},
    )
    monkeypatch.setattr(
        closeout_readiness_by_construction,
        "generate_evidence_comment_template",
        lambda _config, issue_number: {"ok": True, "canonical_marker_completeness": _ready_marker()},
    )
    payload = closeout_readiness_by_construction.check_closeout_readiness_by_construction(_config(tmp_path), parent_issue=421)
    assert payload["post_hoc_marker_repair_required"] is True
    assert payload["readiness_by_construction"]["ready"] is False


def test_check_closeout_readiness_by_construction_remains_read_only(monkeypatch, tmp_path: Path) -> None:
    _mock_common(monkeypatch)
    monkeypatch.setattr(
        closeout_readiness_by_construction,
        "generate_child_closeout_evidence_bundle",
        lambda _config, parent_issue, child_issue: {"ok": True, "canonical_marker_completeness": _ready_marker()},
    )
    monkeypatch.setattr(
        closeout_readiness_by_construction,
        "generate_pr_evidence_bundle",
        lambda _config, issue_number, pr_number: {"ok": True, "canonical_marker_completeness": _ready_marker()},
    )
    monkeypatch.setattr(
        closeout_readiness_by_construction,
        "generate_parent_closeout_evidence_bundle",
        lambda _config, parent_issue: {"ok": True, "canonical_marker_completeness": _ready_marker()},
    )
    monkeypatch.setattr(
        closeout_readiness_by_construction,
        "generate_evidence_comment_template",
        lambda _config, issue_number: {"ok": True, "canonical_marker_completeness": _ready_marker()},
    )
    payload = closeout_readiness_by_construction.check_closeout_readiness_by_construction(_config(tmp_path), parent_issue=421)
    assert payload["read_only"] is True
    assert payload["mutation"]["attempted"] is False
    assert payload["mutation"]["comment_on_issue"] is False
    assert payload["mutation"]["close_issues"] is False
    assert payload["mutation"]["create_pr"] is False
    assert payload["mutation"]["merge_pr"] is False
