from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator import milestone_reconciliation_planner


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


def test_not_ready_while_implementation_children_unaccounted(monkeypatch, tmp_path: Path) -> None:
    config = _config(tmp_path)
    monkeypatch.setattr(
        milestone_reconciliation_planner,
        "inspect_milestone_state",
        lambda _config, parent_issue: {
            "ok": True,
            "parent_issue": {"issue_number": parent_issue, "state": "OPEN"},
            "child_issues": [
                {"issue_number": 270, "title": "contract", "state": "OPEN", "lineage_detected": True, "merged_pr_count": 0},
                {"issue_number": 271, "title": "inspector", "state": "CLOSED", "lineage_detected": True, "merged_pr_count": 1},
                {"issue_number": 276, "title": "Reconcile source-of-truth docs", "state": "OPEN", "lineage_detected": True, "merged_pr_count": 0},
            ],
        },
    )
    monkeypatch.setattr(
        milestone_reconciliation_planner,
        "check_issue_evidence_readiness",
        lambda _config, issue_number: {
            "classification": "not_ready" if issue_number == 270 else "already_closed",
            "duplicate_noop_planning": {"duplicate_pr_risk": False},
        },
    )
    monkeypatch.setattr(
        milestone_reconciliation_planner,
        "check_milestone_evidence_readiness",
        lambda _config, parent_issue: {"ok": True, "status_counts": {"ready": 1, "not_ready": 1}},
    )
    monkeypatch.setattr(
        milestone_reconciliation_planner,
        "fetch_issue_details",
        lambda _config, issue_number: {"ok": True, "issue": {"number": issue_number, "title": "docs-only reconciliation", "body": "documentation reconciliation"}},
    )

    payload = milestone_reconciliation_planner.plan_milestone_final_reconciliation(config, parent_issue=269)
    assert payload["ok"] is True
    assert payload["ready_for_final_reconciliation"] is False
    assert payload["unaccounted_children"][0]["issue_number"] == 270
    assert payload["parent_should_remain_open"] is True
    assert payload["evidence_mapping_expectations"]["milestone_readiness_summary"]["ok"] is True


def test_ready_when_implementation_children_are_closed_or_accounted(monkeypatch, tmp_path: Path) -> None:
    config = _config(tmp_path)
    monkeypatch.setattr(
        milestone_reconciliation_planner,
        "inspect_milestone_state",
        lambda _config, parent_issue: {
            "ok": True,
            "parent_issue": {"issue_number": parent_issue, "state": "OPEN"},
            "child_issues": [
                {"issue_number": 270, "title": "contract", "state": "CLOSED", "lineage_detected": True, "merged_pr_count": 1},
                {"issue_number": 271, "title": "inspector", "state": "OPEN", "lineage_detected": True, "merged_pr_count": 1},
                {"issue_number": 276, "title": "Reconcile source-of-truth docs", "state": "OPEN", "lineage_detected": True, "merged_pr_count": 0},
            ],
        },
    )
    monkeypatch.setattr(
        milestone_reconciliation_planner,
        "check_issue_evidence_readiness",
        lambda _config, issue_number: {
            "classification": "ready",
            "duplicate_noop_planning": {"duplicate_pr_risk": False},
        },
    )
    monkeypatch.setattr(
        milestone_reconciliation_planner,
        "check_milestone_evidence_readiness",
        lambda _config, parent_issue: {"ok": True, "status_counts": {"ready": 2, "not_ready": 0}},
    )
    monkeypatch.setattr(
        milestone_reconciliation_planner,
        "fetch_issue_details",
        lambda _config, issue_number: {"ok": True, "issue": {"number": issue_number, "title": "M17 docs-only", "body": "documentation reconciliation"}},
    )

    payload = milestone_reconciliation_planner.plan_milestone_final_reconciliation(config, parent_issue=269)
    assert payload["ready_for_final_reconciliation"] is True
    assert payload["unaccounted_children"] == []
    assert payload["safety_signals"]["final_reconciliation_should_be_last"] is True
    assert payload["docs_only_expected"] is True
    assert payload["safety_signals"]["no_generated_evidence_artifact_changes_expected"] is True


def test_final_reconciliation_must_remain_last(monkeypatch, tmp_path: Path) -> None:
    config = _config(tmp_path)
    monkeypatch.setattr(
        milestone_reconciliation_planner,
        "inspect_milestone_state",
        lambda _config, parent_issue: {
            "ok": True,
            "parent_issue": {"issue_number": parent_issue, "state": "OPEN"},
            "child_issues": [
                {"issue_number": 276, "title": "Reconcile source-of-truth docs", "state": "OPEN", "lineage_detected": True, "merged_pr_count": 0},
                {"issue_number": 279, "title": "late implementation", "state": "OPEN", "lineage_detected": True, "merged_pr_count": 0},
            ],
        },
    )
    monkeypatch.setattr(
        milestone_reconciliation_planner,
        "check_issue_evidence_readiness",
        lambda _config, issue_number: {
            "classification": "ready",
            "duplicate_noop_planning": {"duplicate_pr_risk": False},
        },
    )
    monkeypatch.setattr(
        milestone_reconciliation_planner,
        "check_milestone_evidence_readiness",
        lambda _config, parent_issue: {"ok": True, "status_counts": {}},
    )
    monkeypatch.setattr(
        milestone_reconciliation_planner,
        "fetch_issue_details",
        lambda _config, issue_number: {"ok": True, "issue": {"number": issue_number, "title": "docs-only", "body": "documentation"}},
    )

    payload = milestone_reconciliation_planner.plan_milestone_final_reconciliation(config, parent_issue=269)
    assert payload["safety_signals"]["final_reconciliation_should_be_last"] is False
    assert payload["ready_for_final_reconciliation"] is False


def test_parent_remains_open_until_final_reconciliation_complete(monkeypatch, tmp_path: Path) -> None:
    config = _config(tmp_path)
    monkeypatch.setattr(
        milestone_reconciliation_planner,
        "inspect_milestone_state",
        lambda _config, parent_issue: {
            "ok": True,
            "parent_issue": {"issue_number": parent_issue, "state": "OPEN"},
            "child_issues": [
                {"issue_number": 270, "title": "contract", "state": "CLOSED", "lineage_detected": True, "merged_pr_count": 1},
                {"issue_number": 276, "title": "Reconcile source-of-truth docs", "state": "CLOSED", "lineage_detected": True, "merged_pr_count": 1},
            ],
        },
    )
    monkeypatch.setattr(
        milestone_reconciliation_planner,
        "check_issue_evidence_readiness",
        lambda _config, issue_number: {
            "classification": "already_closed",
            "duplicate_noop_planning": {"duplicate_pr_risk": False},
        },
    )
    monkeypatch.setattr(
        milestone_reconciliation_planner,
        "check_milestone_evidence_readiness",
        lambda _config, parent_issue: {"ok": True, "status_counts": {}},
    )
    monkeypatch.setattr(
        milestone_reconciliation_planner,
        "fetch_issue_details",
        lambda _config, issue_number: {"ok": True, "issue": {"number": issue_number, "title": "docs-only", "body": "documentation"}},
    )

    payload = milestone_reconciliation_planner.plan_milestone_final_reconciliation(config, parent_issue=269)
    assert payload["parent_should_remain_open"] is False
    assert payload["close_issues"] is False
    assert payload["create_pr"] is False
    assert payload["comment_on_issue"] is False
    assert payload["mutation_allowed"] is False


def test_planner_fails_cleanly_when_inspection_fails(monkeypatch, tmp_path: Path) -> None:
    config = _config(tmp_path)
    monkeypatch.setattr(
        milestone_reconciliation_planner,
        "inspect_milestone_state",
        lambda _config, parent_issue: {"ok": False, "error": "gh_cli_failed", "parent_issue": parent_issue},
    )
    payload = milestone_reconciliation_planner.plan_milestone_final_reconciliation(config, parent_issue=269)
    assert payload["ok"] is False
    assert payload["read_only"] is True
    assert payload["mutation_allowed"] is False