import json
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
        lambda _config, parent_issue, state_file=None: {
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
        lambda _config, parent_issue, state_file=None: {
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
        lambda _config, parent_issue, state_file=None: {
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
        lambda _config, parent_issue, state_file=None: {
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
        lambda _config, parent_issue, state_file=None: {
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
        lambda _config, parent_issue, state_file=None: {
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
        lambda _config, parent_issue, state_file=None: {"ok": False, "error": "gh_cli_failed"},
    )
    monkeypatch.setattr(
        parent_closeout_evidence_bundle,
        "check_milestone_evidence_readiness",
        lambda _config, parent_issue, state_file=None: {"ok": True},
    )
    monkeypatch.setattr(
        parent_closeout_evidence_bundle,
        "inspect_parent_closeout_readiness",
        lambda _config, parent_issue, state_file=None: {"ok": True},
    )

    payload = parent_closeout_evidence_bundle.generate_parent_closeout_evidence_bundle(
        config,
        parent_issue=362,
    )

    assert payload["ok"] is False
    assert payload["error"] == "parent_closeout_bundle_dependency_failed"
    assert payload["failures"][0]["command"] == "inspect-milestone-state"


def test_generate_parent_closeout_evidence_bundle_offline_uses_local_state_and_no_subprocess(
    monkeypatch,
    tmp_path: Path,
) -> None:
    config = _config(tmp_path)
    state_file = tmp_path / "offline-state.json"
    state_file.write_text(
        json.dumps(
            {
                "parent_issue": {
                    "number": 421,
                    "state": "OPEN",
                    "title": "M25 Parent",
                    "url": "https://github.com/yoey2112/aresforge/issues/421",
                    "milestone": {"title": "M25"},
                    "reference_classification": {"implementation_issue_numbers": [430, 431]},
                },
                "child_issues": [
                    {
                        "number": 430,
                        "state": "CLOSED",
                        "title": "Child A",
                        "url": "https://github.com/yoey2112/aresforge/issues/430",
                        "body": "Implements #430\nParent issue: #421",
                        "reference_classification": {
                            "implementation_issue_numbers": [421],
                            "explicit_implementation_issue_numbers": [430],
                        },
                        "merged_pr_evidence": [
                            {"url": "https://github.com/yoey2112/aresforge/pull/501"}
                        ],
                    },
                    {
                        "number": 431,
                        "state": "CLOSED",
                        "title": "Child B",
                        "url": "https://github.com/yoey2112/aresforge/issues/431",
                        "body": "Fixes #431\nParent issue: #421",
                        "reference_classification": {
                            "implementation_issue_numbers": [421],
                            "explicit_implementation_issue_numbers": [431],
                        },
                        "merged_pr_evidence": [
                            {"url": "https://github.com/yoey2112/aresforge/pull/502"}
                        ],
                    },
                ],
                "final_reconciliation": {
                    "ready_for_final_reconciliation": True,
                    "final_reconciliation_issue": 432,
                    "parent_should_remain_open": False,
                    "unaccounted_children": [],
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "aresforge.operator.milestone_state_inspector.subprocess.run",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("subprocess.run must not be called in offline mode")),
    )
    monkeypatch.setattr(
        "aresforge.operator.parent_closeout_marker_template.inspect_pr_mapping_preflight",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("inspect_pr_mapping_preflight must not be called in offline mode")),
    )

    payload = parent_closeout_evidence_bundle.generate_parent_closeout_evidence_bundle(
        config,
        parent_issue=421,
        state_file=state_file,
    )

    assert payload["ok"] is True
    assert payload["inspection_mode"] == "local_state_file"
    assert payload["state_file"] == str(state_file)
    assert payload["child_summary"] == {
        "child_issue_count": 2,
        "closed_child_issue_count": 2,
        "accounted_for_child_issue_count": 2,
    }
    assert payload["readiness_gates"] == {"parent_closeout_ready": True, "blocked_reasons": []}
    assert payload["child_states"] == [
        {
            "issue_number": 430,
            "state": "CLOSED",
            "classification": "already_closed",
            "lineage_detected": True,
            "individually_closed": True,
            "accounted_for": True,
        },
        {
            "issue_number": 431,
            "state": "CLOSED",
            "classification": "already_closed",
            "lineage_detected": True,
            "individually_closed": True,
            "accounted_for": True,
        },
    ]
    assert payload["child_pr_mappings"] == [
        {
            "issue_number": 430,
            "classification": "already_closed",
            "merged_pr_count": 1,
            "merged_pr_urls": ["https://github.com/yoey2112/aresforge/pull/501"],
        },
        {
            "issue_number": 431,
            "classification": "already_closed",
            "merged_pr_count": 1,
            "merged_pr_urls": ["https://github.com/yoey2112/aresforge/pull/502"],
        },
    ]
    assert payload["canonical_marker_completeness"]["missing_required_fields"] == [
        "final_main_head",
        "final_validation_results",
    ]
    assert payload["canonical_marker_completeness"]["marker_complete"] is False


def test_generate_parent_closeout_evidence_bundle_offline_can_be_marker_complete(
    monkeypatch,
    tmp_path: Path,
) -> None:
    config = _config(tmp_path)
    state_file = tmp_path / "offline-state-complete.json"
    state_file.write_text(
        json.dumps(
            {
                "parent_issue": {
                    "number": 421,
                    "state": "OPEN",
                    "title": "M25 Parent",
                    "url": "https://github.com/yoey2112/aresforge/issues/421",
                    "milestone": {"title": "M25"},
                    "reference_classification": {"implementation_issue_numbers": [430]},
                },
                "child_issues": [
                    {
                        "number": 430,
                        "state": "CLOSED",
                        "title": "Child A",
                        "url": "https://github.com/yoey2112/aresforge/issues/430",
                        "body": "Implements #430\nParent issue: #421",
                        "reference_classification": {
                            "implementation_issue_numbers": [421],
                            "explicit_implementation_issue_numbers": [430],
                        },
                        "merged_pr_evidence": [
                            {"url": "https://github.com/yoey2112/aresforge/pull/501"}
                        ],
                    }
                ],
                "final_reconciliation": {
                    "ready_for_final_reconciliation": True,
                    "parent_should_remain_open": False,
                    "unaccounted_children": [],
                },
                "final_main_head": "abc1234",
                "final_validation_results": "git diff --check: pass; pytest: pass",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "aresforge.operator.parent_closeout_marker_template.inspect_pr_mapping_preflight",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("inspect_pr_mapping_preflight must not be called in offline mode")),
    )

    payload = parent_closeout_evidence_bundle.generate_parent_closeout_evidence_bundle(
        config,
        parent_issue=421,
        state_file=state_file,
    )

    assert payload["ok"] is True
    assert payload["canonical_marker_completeness"]["missing_required_fields"] == []
    assert payload["canonical_marker_completeness"]["marker_complete"] is True
