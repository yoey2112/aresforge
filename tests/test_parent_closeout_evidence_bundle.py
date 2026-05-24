from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator import parent_closeout_evidence_bundle


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


def test_generate_parent_closeout_evidence_bundle_ready(monkeypatch, tmp_path: Path) -> None:
    config = _config(tmp_path)
    monkeypatch.setattr(
        parent_closeout_evidence_bundle,
        "inspect_milestone_state",
        lambda _config, parent_issue: {
            "ok": True,
            "parent_issue": {
                "issue_number": parent_issue,
                "state": "OPEN",
                "title": "M22 Parent",
                "url": "https://github.com/yoey2112/aresforge/issues/362",
            },
            "child_issues": [{"issue_number": 366}, {"issue_number": 367}],
        },
    )
    monkeypatch.setattr(
        parent_closeout_evidence_bundle,
        "check_milestone_evidence_readiness",
        lambda _config, parent_issue: {
            "ok": True,
            "issues": [
                {
                    "issue": {
                        "number": 366,
                        "merged_pr_evidence": [{"url": "https://github.com/yoey2112/aresforge/pull/375"}],
                    },
                    "classification": "already_closed",
                },
                {
                    "issue": {
                        "number": 367,
                        "merged_pr_evidence": [{"url": "https://github.com/yoey2112/aresforge/pull/376"}],
                    },
                    "classification": "already_closed",
                },
            ],
        },
    )
    monkeypatch.setattr(
        parent_closeout_evidence_bundle,
        "inspect_parent_closeout_readiness",
        lambda _config, parent_issue: {
            "ok": True,
            "closeout_readiness": {"parent_closeout_ready": True},
            "blocked_reasons": [],
            "child_lineage": [
                {
                    "issue_number": 366,
                    "state": "CLOSED",
                    "classification": "already_closed",
                    "lineage_detected": True,
                    "individually_closed": True,
                    "accounted_for": True,
                },
                {
                    "issue_number": 367,
                    "state": "CLOSED",
                    "classification": "already_closed",
                    "lineage_detected": True,
                    "individually_closed": True,
                    "accounted_for": True,
                },
            ],
        },
    )

    payload = parent_closeout_evidence_bundle.generate_parent_closeout_evidence_bundle(
        config,
        parent_issue=362,
    )

    assert payload["ok"] is True
    assert payload["read_only"] is True
    assert payload["readiness_gates"]["parent_closeout_ready"] is True
    assert payload["child_summary"]["closed_child_issue_count"] == 2
    assert payload["child_pr_mappings"][0]["merged_pr_urls"] == ["https://github.com/yoey2112/aresforge/pull/375"]
    assert payload["canonical_marker"]["marker_type"] == "parent_closeout_evidence"
    assert payload["canonical_marker_completeness"] == {
        "state": "incomplete",
        "marker_type": "parent_closeout_evidence",
        "marker_scope": "parent_closeout_evidence_bundle",
        "missing_required_fields": [
            "child_issue_list",
            "child_to_pr_mapping",
            "final_main_head",
            "final_validation_results",
        ],
        "invalid_reasons": [],
        "marker_complete": False,
        "post_hoc_marker_repair_required": True,
    }
    assert "### Canonical Marker" in payload["parent_evidence_comment_body"]
    assert "### Safety posture" in payload["parent_evidence_comment_body"]
    assert "```" not in payload["parent_evidence_comment_body"]


def test_generate_parent_closeout_evidence_bundle_blocked(monkeypatch, tmp_path: Path) -> None:
    config = _config(tmp_path)
    monkeypatch.setattr(
        parent_closeout_evidence_bundle,
        "inspect_milestone_state",
        lambda _config, parent_issue: {
            "ok": True,
            "parent_issue": {
                "issue_number": parent_issue,
                "state": "OPEN",
                "title": "M22 Parent",
                "url": "https://github.com/yoey2112/aresforge/issues/362",
            },
            "child_issues": [{"issue_number": 366}, {"issue_number": 367}],
        },
    )
    monkeypatch.setattr(
        parent_closeout_evidence_bundle,
        "check_milestone_evidence_readiness",
        lambda _config, parent_issue: {
            "ok": True,
            "issues": [
                {
                    "issue": {"number": 366, "merged_pr_evidence": []},
                    "classification": "not_ready",
                }
            ],
        },
    )
    monkeypatch.setattr(
        parent_closeout_evidence_bundle,
        "inspect_parent_closeout_readiness",
        lambda _config, parent_issue: {
            "ok": True,
            "closeout_readiness": {"parent_closeout_ready": False},
            "blocked_reasons": ["one_or_more_children_not_closed_or_accounted_for"],
            "child_lineage": [
                {
                    "issue_number": 366,
                    "state": "OPEN",
                    "classification": "not_ready",
                    "lineage_detected": True,
                    "individually_closed": False,
                    "accounted_for": False,
                },
                {
                    "issue_number": 367,
                    "state": "CLOSED",
                    "classification": "already_closed",
                    "lineage_detected": True,
                    "individually_closed": True,
                    "accounted_for": True,
                },
            ],
        },
    )

    payload = parent_closeout_evidence_bundle.generate_parent_closeout_evidence_bundle(
        config,
        parent_issue=362,
    )

    assert payload["ok"] is True
    assert payload["read_only"] is True
    assert payload["readiness_gates"]["parent_closeout_ready"] is False
    assert "one_or_more_children_not_closed_or_accounted_for" in payload["readiness_gates"]["blocked_reasons"]
    completeness = payload["canonical_marker_completeness"]
    assert completeness["state"] == "incomplete"
    assert completeness["marker_type"] == "parent_closeout_evidence"
    assert completeness["marker_scope"] == "parent_closeout_evidence_bundle"
    assert completeness["marker_complete"] is False
    assert completeness["post_hoc_marker_repair_required"] is True
    assert "final_main_head" in completeness["missing_required_fields"]
    assert "final_validation_results" in completeness["missing_required_fields"]
    assert payload["targeted_parent_closeout_guidance"][0].startswith("1. Do not close parent issue #362")


def test_generate_parent_closeout_evidence_bundle_dependency_failure(
    monkeypatch,
    tmp_path: Path,
) -> None:
    config = _config(tmp_path)
    monkeypatch.setattr(
        parent_closeout_evidence_bundle,
        "inspect_milestone_state",
        lambda _config, parent_issue: {"ok": False, "error": "gh_cli_failed"},
    )
    monkeypatch.setattr(
        parent_closeout_evidence_bundle,
        "check_milestone_evidence_readiness",
        lambda _config, parent_issue: {"ok": True},
    )
    monkeypatch.setattr(
        parent_closeout_evidence_bundle,
        "inspect_parent_closeout_readiness",
        lambda _config, parent_issue: {"ok": True},
    )

    payload = parent_closeout_evidence_bundle.generate_parent_closeout_evidence_bundle(
        config,
        parent_issue=362,
    )

    assert payload["ok"] is False
    assert payload["error"] == "parent_closeout_bundle_dependency_failed"
    assert payload["failures"][0]["command"] == "inspect-milestone-state"
