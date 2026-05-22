from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator import milestone_dashboard


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


def test_dashboard_combines_read_only_signals(monkeypatch, tmp_path: Path) -> None:
    config = _config(tmp_path)

    monkeypatch.setattr(
        milestone_dashboard,
        "inspect_milestone_state",
        lambda _config, parent_issue: {
            "ok": True,
            "read_only": True,
            "parent_issue": {"issue_number": parent_issue, "state": "OPEN", "title": "parent"},
            "child_issues": [
                {"issue_number": 295, "state": "OPEN", "title": "dashboard"},
                {"issue_number": 296, "state": "OPEN", "title": "scripts"},
                {"issue_number": 301, "state": "OPEN", "title": "Reconcile source-of-truth docs"},
            ],
            "warnings": ["Parent issue does not have a milestone assigned."],
            "boundary_confirmations": ["read_only: true"],
        },
    )
    monkeypatch.setattr(
        milestone_dashboard,
        "plan_milestone_execution_queue",
        lambda _config, parent_issue: {
            "ok": True,
            "read_only": True,
            "recommended_order": [
                {
                    "position": 1,
                    "issue_number": 295,
                    "title": "dashboard",
                    "state": "OPEN",
                    "is_final_reconciliation": False,
                },
                {
                    "position": 2,
                    "issue_number": 296,
                    "title": "scripts",
                    "state": "OPEN",
                    "is_final_reconciliation": False,
                },
                {
                    "position": 3,
                    "issue_number": 301,
                    "title": "Reconcile source-of-truth docs",
                    "state": "OPEN",
                    "is_final_reconciliation": True,
                },
            ],
            "blocked_items": [],
            "signals": {"final_reconciliation_last_enforced": True},
            "required_operator_actions": ["Execute child issues one-by-one in recommended order."],
            "safety_gates": {
                "execution_enabled": False,
                "close_issues": False,
                "bulk_closeout_allowed": False,
                "operator_review_required": True,
                "parent_closeout_allowed": False,
            },
            "boundary_confirmations": ["execution_enabled: false"],
        },
    )
    monkeypatch.setattr(
        milestone_dashboard,
        "check_milestone_evidence_readiness",
        lambda _config, parent_issue: {
            "ok": True,
            "read_only": True,
            "status_counts": {"ready": 0, "not_ready": 3, "ambiguous": 0, "blocked": 0, "already_closed": 0},
            "milestone_closeout_readiness": {"closeout_ready": False, "operator_review_required": True},
            "issues": [
                {"issue": {"number": 295}, "classification": "not_ready"},
                {"issue": {"number": 296}, "classification": "not_ready"},
                {"issue": {"number": 301}, "classification": "not_ready"},
            ],
            "boundary_confirmations": ["mutation_allowed: false"],
        },
    )
    monkeypatch.setattr(
        milestone_dashboard,
        "plan_milestone_final_reconciliation",
        lambda _config, parent_issue: {
            "ok": True,
            "read_only": True,
            "final_reconciliation_issue": {"issue_number": 301, "state": "OPEN"},
            "implementation_children": [
                {"issue_number": 295, "state": "OPEN"},
                {"issue_number": 296, "state": "OPEN"},
            ],
            "unaccounted_children": [
                {"issue_number": 295, "state": "OPEN", "classification": "not_ready"},
                {"issue_number": 296, "state": "OPEN", "classification": "not_ready"},
            ],
            "ready_for_final_reconciliation": False,
            "parent_should_remain_open": True,
            "docs_only_expected": True,
            "required_operator_actions": ["Close or evidence-account all implementation children before final reconciliation."],
            "operator_review_required": True,
            "boundary_confirmations": ["close_issues: false"],
        },
    )

    payload = milestone_dashboard.inspect_milestone_dashboard(config, parent_issue=294)

    assert payload["ok"] is True
    assert payload["read_only"] is True
    assert payload["dashboard"]["parent_state"] == "OPEN"
    assert payload["dashboard"]["child_issue_count"] == 3
    assert payload["dashboard"]["open_child_issue_count"] == 3
    assert payload["dashboard"]["closed_child_issue_count"] == 0
    assert payload["dashboard"]["recommended_next_child_issue"]["issue_number"] == 295
    assert payload["dashboard"]["final_reconciliation_issue"]["issue_number"] == 301
    assert payload["dashboard"]["milestone_closeout_ready"] is False
    assert payload["dashboard"]["parent_should_remain_open"] is True
    assert payload["dashboard"]["execution_mutation_disabled"] is True
    assert payload["dashboard"]["operator_review_required"] is True
    assert payload["safety_gates"]["execution_enabled"] is False
    assert payload["safety_gates"]["mutation_allowed"] is False


def test_dashboard_fails_when_dependency_command_fails(monkeypatch, tmp_path: Path) -> None:
    config = _config(tmp_path)

    monkeypatch.setattr(
        milestone_dashboard,
        "inspect_milestone_state",
        lambda _config, parent_issue: {"ok": False, "error": "gh_cli_failed", "parent_issue": parent_issue},
    )
    monkeypatch.setattr(
        milestone_dashboard,
        "plan_milestone_execution_queue",
        lambda _config, parent_issue: {"ok": True},
    )
    monkeypatch.setattr(
        milestone_dashboard,
        "check_milestone_evidence_readiness",
        lambda _config, parent_issue: {"ok": True},
    )
    monkeypatch.setattr(
        milestone_dashboard,
        "plan_milestone_final_reconciliation",
        lambda _config, parent_issue: {"ok": True},
    )

    payload = milestone_dashboard.inspect_milestone_dashboard(config, parent_issue=294)
    assert payload["ok"] is False
    assert payload["read_only"] is True
    assert payload["error"] == "dashboard_dependency_failed"
    assert payload["failures"][0]["command"] == "inspect-milestone-state"
    assert payload["safety_gates"]["mutation_allowed"] is False