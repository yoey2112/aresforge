from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator import milestone_execution_queue_planner


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


def test_planner_orders_children_and_enforces_reconciliation_last(monkeypatch, tmp_path: Path) -> None:
    config = _config(tmp_path)
    monkeypatch.setattr(
        milestone_execution_queue_planner,
        "inspect_milestone_state",
        lambda _config, parent_issue: {
            "ok": True,
            "parent_issue": {"issue_number": parent_issue, "state": "OPEN"},
            "child_issues": [
                {"issue_number": 276, "title": "M17: Reconcile source-of-truth docs", "state": "OPEN", "lineage_detected": True, "merged_pr_count": 0},
                {"issue_number": 272, "title": "queue planner", "state": "OPEN", "lineage_detected": True, "merged_pr_count": 0},
                {"issue_number": 270, "title": "contract", "state": "OPEN", "lineage_detected": True, "merged_pr_count": 1},
            ],
        },
    )
    monkeypatch.setattr(
        milestone_execution_queue_planner,
        "check_issue_evidence_readiness",
        lambda _config, issue_number: {"ok": True, "classification": "ready", "duplicate_noop_planning": {"duplicate_pr_risk": False}},
    )

    payload = milestone_execution_queue_planner.plan_milestone_execution_queue(config, parent_issue=269)
    assert payload["ok"] is True
    assert [item["issue_number"] for item in payload["recommended_order"]] == [270, 272, 276]
    assert payload["recommended_order"][-1]["is_final_reconciliation"] is True


def test_planner_disables_execution_and_closeout_paths(monkeypatch, tmp_path: Path) -> None:
    config = _config(tmp_path)
    monkeypatch.setattr(
        milestone_execution_queue_planner,
        "inspect_milestone_state",
        lambda _config, parent_issue: {
            "ok": True,
            "parent_issue": {"issue_number": parent_issue, "state": "OPEN"},
            "child_issues": [{"issue_number": 272, "title": "queue planner", "state": "OPEN", "lineage_detected": True, "merged_pr_count": 0}],
        },
    )
    monkeypatch.setattr(
        milestone_execution_queue_planner,
        "check_issue_evidence_readiness",
        lambda _config, issue_number: {"ok": True, "classification": "not_ready", "duplicate_noop_planning": {"duplicate_pr_risk": False}},
    )

    payload = milestone_execution_queue_planner.plan_milestone_execution_queue(config, parent_issue=269)
    gates = payload["safety_gates"]
    assert gates["execution_enabled"] is False
    assert gates["close_issues"] is False
    assert gates["bulk_closeout_allowed"] is False
    assert gates["operator_review_required"] is True
    assert gates["parent_closeout_allowed"] is False


def test_planner_surfaces_lineage_blockers(monkeypatch, tmp_path: Path) -> None:
    config = _config(tmp_path)
    monkeypatch.setattr(
        milestone_execution_queue_planner,
        "inspect_milestone_state",
        lambda _config, parent_issue: {
            "ok": True,
            "parent_issue": {"issue_number": parent_issue, "state": "OPEN"},
            "child_issues": [{"issue_number": 272, "title": "queue planner", "state": "OPEN", "lineage_detected": False, "merged_pr_count": 0}],
        },
    )
    monkeypatch.setattr(
        milestone_execution_queue_planner,
        "check_issue_evidence_readiness",
        lambda _config, issue_number: {"ok": True, "classification": "blocked", "duplicate_noop_planning": {"duplicate_pr_risk": False}},
    )
    payload = milestone_execution_queue_planner.plan_milestone_execution_queue(config, parent_issue=269)
    assert payload["signals"]["missing_parent_child_lineage"] == [272]
    assert any(item["type"] == "missing_parent_child_lineage" for item in payload["blocked_items"])


def test_planner_parent_not_eligible_before_children_closed(monkeypatch, tmp_path: Path) -> None:
    config = _config(tmp_path)
    monkeypatch.setattr(
        milestone_execution_queue_planner,
        "inspect_milestone_state",
        lambda _config, parent_issue: {
            "ok": True,
            "parent_issue": {"issue_number": parent_issue, "state": "OPEN"},
            "child_issues": [
                {"issue_number": 270, "title": "contract", "state": "CLOSED", "lineage_detected": True, "merged_pr_count": 1},
                {"issue_number": 271, "title": "inspector", "state": "OPEN", "lineage_detected": True, "merged_pr_count": 0},
            ],
        },
    )
    monkeypatch.setattr(
        milestone_execution_queue_planner,
        "check_issue_evidence_readiness",
        lambda _config, issue_number: {"ok": True, "classification": "ready", "duplicate_noop_planning": {"duplicate_pr_risk": False}},
    )
    payload = milestone_execution_queue_planner.plan_milestone_execution_queue(config, parent_issue=269)
    assert payload["safety_gates"]["parent_closeout_allowed"] is False


def test_planner_fails_cleanly_when_inspection_fails(monkeypatch, tmp_path: Path) -> None:
    config = _config(tmp_path)
    monkeypatch.setattr(
        milestone_execution_queue_planner,
        "inspect_milestone_state",
        lambda _config, parent_issue: {"ok": False, "error": "gh_cli_failed", "parent_issue": parent_issue},
    )
    payload = milestone_execution_queue_planner.plan_milestone_execution_queue(config, parent_issue=269)
    assert payload["ok"] is False
    assert payload["execution_enabled"] is False


def test_planner_uses_evidence_checker_duplicate_risk(monkeypatch, tmp_path: Path) -> None:
    config = _config(tmp_path)
    monkeypatch.setattr(
        milestone_execution_queue_planner,
        "inspect_milestone_state",
        lambda _config, parent_issue: {
            "ok": True,
            "parent_issue": {"issue_number": parent_issue, "state": "OPEN"},
            "child_issues": [{"issue_number": 274, "title": "duplicate/no-op", "state": "OPEN", "lineage_detected": True, "merged_pr_count": 0}],
        },
    )
    monkeypatch.setattr(
        milestone_execution_queue_planner,
        "check_issue_evidence_readiness",
        lambda _config, issue_number: {
            "ok": True,
            "classification": "ready",
            "duplicate_noop_planning": {
                "duplicate_pr_risk": True,
                "recommendation": "reuse_existing_pr_evidence",
            },
        },
    )
    payload = milestone_execution_queue_planner.plan_milestone_execution_queue(config, parent_issue=269)
    assert payload["signals"]["duplicate_or_noop_pr_risks"][0]["risk"] == "evidence_checker_duplicate_or_noop_risk"
