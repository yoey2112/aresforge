from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator import evidence_bundle_simulation


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


def test_simulate_evidence_bundle_generation_blocked(monkeypatch, tmp_path: Path) -> None:
    config = _config(tmp_path)
    monkeypatch.setattr(
        evidence_bundle_simulation,
        "inspect_milestone_state",
        lambda _config, parent_issue: {
            "ok": True,
            "parent_issue": {"issue_number": parent_issue, "state": "OPEN"},
            "child_issues": [
                {"issue_number": 366, "state": "CLOSED"},
                {"issue_number": 371, "state": "OPEN"},
            ],
        },
    )
    monkeypatch.setattr(
        evidence_bundle_simulation,
        "plan_milestone_execution_queue",
        lambda _config, parent_issue: {
            "ok": True,
            "recommended_order": [
                {"issue_number": 366, "is_final_reconciliation": False},
                {"issue_number": 371, "is_final_reconciliation": True},
            ],
        },
    )
    monkeypatch.setattr(
        evidence_bundle_simulation,
        "inspect_parent_closeout_readiness",
        lambda _config, parent_issue: {
            "ok": True,
            "closeout_readiness": {"parent_closeout_ready": False},
            "blocked_reasons": ["final_source_of_truth_reconciliation_incomplete"],
        },
    )
    monkeypatch.setattr(
        evidence_bundle_simulation,
        "generate_child_closeout_evidence_bundle",
        lambda _config, parent_issue, child_issue: {
            "ok": True,
            "read_only": True,
            "evidence_comment_body": f"child {child_issue}",
        },
    )
    monkeypatch.setattr(
        evidence_bundle_simulation,
        "generate_parent_closeout_evidence_bundle",
        lambda _config, parent_issue: {
            "ok": True,
            "read_only": True,
            "readiness_gates": {
                "parent_closeout_ready": False,
                "blocked_reasons": ["final_source_of_truth_reconciliation_incomplete"],
            },
        },
    )

    payload = evidence_bundle_simulation.simulate_evidence_bundle_generation(config, parent_issue=362)

    assert payload["ok"] is True
    assert payload["read_only"] is True
    assert payload["dry_run"] is True
    assert payload["mutation"]["attempted"] is False
    assert payload["simulation"]["final_reconciliation_last"] is True
    assert payload["simulation"]["parent_bundle_blocked_state"]["parent_closeout_ready"] is False


def test_simulate_evidence_bundle_generation_ready_fixture(monkeypatch, tmp_path: Path) -> None:
    config = _config(tmp_path)
    monkeypatch.setattr(
        evidence_bundle_simulation,
        "inspect_milestone_state",
        lambda _config, parent_issue: {
            "ok": True,
            "parent_issue": {"issue_number": parent_issue, "state": "OPEN"},
            "child_issues": [
                {"issue_number": 366, "state": "CLOSED"},
                {"issue_number": 367, "state": "CLOSED"},
                {"issue_number": 371, "state": "CLOSED"},
            ],
        },
    )
    monkeypatch.setattr(
        evidence_bundle_simulation,
        "plan_milestone_execution_queue",
        lambda _config, parent_issue: {
            "ok": True,
            "recommended_order": [
                {"issue_number": 366, "is_final_reconciliation": False},
                {"issue_number": 367, "is_final_reconciliation": False},
                {"issue_number": 371, "is_final_reconciliation": True},
            ],
        },
    )
    monkeypatch.setattr(
        evidence_bundle_simulation,
        "inspect_parent_closeout_readiness",
        lambda _config, parent_issue: {
            "ok": True,
            "closeout_readiness": {"parent_closeout_ready": True},
            "blocked_reasons": [],
        },
    )
    monkeypatch.setattr(
        evidence_bundle_simulation,
        "generate_child_closeout_evidence_bundle",
        lambda _config, parent_issue, child_issue: {
            "ok": True,
            "read_only": True,
            "evidence_comment_body": f"child {child_issue}",
        },
    )
    monkeypatch.setattr(
        evidence_bundle_simulation,
        "generate_parent_closeout_evidence_bundle",
        lambda _config, parent_issue: {
            "ok": True,
            "read_only": True,
            "readiness_gates": {
                "parent_closeout_ready": True,
                "blocked_reasons": [],
            },
        },
    )

    payload = evidence_bundle_simulation.simulate_evidence_bundle_generation(config, parent_issue=362)

    assert payload["ok"] is True
    assert payload["simulation"]["multi_child_milestone"] is True
    assert payload["simulation"]["final_reconciliation_last"] is True
    assert payload["simulation"]["parent_bundle_ready_state_fixture"]["parent_closeout_ready"] is True
    assert payload["simulation"]["validation_summary_reuse"]["overall_state"] == "pass"