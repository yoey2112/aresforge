from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator import self_managed_milestone_simulation as simulation


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


def test_simulation_reports_read_only_next_child_351_and_final_reconciliation_last(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        simulation,
        "inspect_self_managed_milestone_execution_contract",
        lambda _config: {"ok": True},
    )
    monkeypatch.setattr(
        simulation,
        "inspect_milestone_state",
        lambda _config, parent_issue: {
            "ok": True,
            "child_issues": [
                {"issue_number": 346, "state": "CLOSED"},
                {"issue_number": 350, "state": "CLOSED"},
                {"issue_number": 351, "state": "OPEN"},
                {"issue_number": 352, "state": "OPEN"},
                {"issue_number": 353, "state": "OPEN"},
            ],
        },
    )
    monkeypatch.setattr(
        simulation,
        "inspect_milestone_dashboard",
        lambda _config, parent_issue: {
            "ok": True,
            "dashboard": {
                "recommended_next_child_issue": {"issue_number": 351},
                "final_reconciliation_issue": {"issue_number": 353},
                "milestone_closeout_ready": False,
            },
            "execution_queue": {
                "signals": {"final_reconciliation_last_enforced": True},
            },
        },
    )

    payload = simulation.simulate_self_managed_milestone_execution(_config(tmp_path), parent_issue=345)
    assert payload["ok"] is True
    assert payload["read_only"] is True
    assert payload["child_discovery"]["next_open_child_issue"] == 351
    assert payload["child_discovery"]["final_reconciliation_issue"] == 353
    assert payload["sequential_plan"]["final_reconciliation_last_enforced"] is True
    assert payload["safety_checks"]["github_mutation_performed"] is False
    assert payload["safety_checks"]["issue_closure_performed"] is False
    assert payload["safety_checks"]["bulk_closeout_path_generated"] is False
    assert payload["parent_closeout_plan"]["blocked_until_children_accounted_for"] is True


def test_simulation_reports_next_child_352_after_351_closed(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        simulation,
        "inspect_self_managed_milestone_execution_contract",
        lambda _config: {"ok": True},
    )
    monkeypatch.setattr(
        simulation,
        "inspect_milestone_state",
        lambda _config, parent_issue: {
            "ok": True,
            "child_issues": [
                {"issue_number": 346, "state": "CLOSED"},
                {"issue_number": 351, "state": "CLOSED"},
                {"issue_number": 352, "state": "OPEN"},
                {"issue_number": 353, "state": "OPEN"},
            ],
        },
    )
    monkeypatch.setattr(
        simulation,
        "inspect_milestone_dashboard",
        lambda _config, parent_issue: {
            "ok": True,
            "dashboard": {
                "recommended_next_child_issue": {"issue_number": 352},
                "final_reconciliation_issue": {"issue_number": 353},
                "milestone_closeout_ready": False,
            },
            "execution_queue": {
                "signals": {"final_reconciliation_last_enforced": True},
            },
        },
    )

    payload = simulation.simulate_self_managed_milestone_execution(_config(tmp_path), parent_issue=345)
    assert payload["ok"] is True
    assert payload["child_discovery"]["next_open_child_issue"] == 352
    commands = payload["per_child_validation_envelope"]["required_validation_commands"]
    assert any("--child-issue 352" in command for command in commands)
