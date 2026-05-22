import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator import sequential_recovery_planner as planner


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


def test_plan_sequential_run_recovery_states(monkeypatch, tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    state_path = tmp_path / ".aresforge" / "sequential-run-state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "records": [
                    {
                        "parent_issue": 309,
                        "current_child_issue": 313,
                        "failed_step": "validation_failed",
                        "current_branch": "m19/313-old-branch",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        planner,
        "inspect_milestone_dashboard",
        lambda _config, parent_issue: {
            "ok": True,
            "dashboard": {"recommended_next_child_issue": {"issue_number": 314}},
        },
    )
    monkeypatch.setattr(
        planner,
        "inspect_child_execution_gates",
        lambda _config, issue_number, parent_issue: {
            "gate_status": {"already_closed": False},
            "checks": {
                "open_pr": {"number": 321},
                "merged_pr_count": 1,
                "evidence_classification": "not_ready",
                "current_branch": "m19/313-new-branch",
                "dirty_worktree": True,
            },
        },
    )
    payload = planner.plan_sequential_run_recovery(cfg, parent_issue=309, state_path=state_path)
    assert payload["ok"] is True
    states = payload["recovery_states"]
    assert states["failed_validation"]["active"] is True
    assert states["unmerged_pr"]["active"] is True
    assert states["merged_pr_missing_evidence"]["active"] is True
    assert states["stale_branch"]["active"] is True
    assert states["dirty_tree"]["active"] is True
    assert states["dashboard_mismatch"]["active"] is True


def test_plan_sequential_run_recovery_closed_child(monkeypatch, tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    state_path = tmp_path / ".aresforge" / "sequential-run-state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "records": [{"parent_issue": 309, "current_child_issue": 313}],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        planner,
        "inspect_milestone_dashboard",
        lambda _config, parent_issue: {"ok": True, "dashboard": {"recommended_next_child_issue": None}},
    )
    monkeypatch.setattr(
        planner,
        "inspect_child_execution_gates",
        lambda _config, issue_number, parent_issue: {
            "gate_status": {"already_closed": True},
            "checks": {
                "open_pr": None,
                "merged_pr_count": 1,
                "evidence_classification": "ready",
                "current_branch": "main",
                "dirty_worktree": False,
            },
        },
    )
    payload = planner.plan_sequential_run_recovery(
        cfg,
        parent_issue=309,
        state_path=state_path,
    )
    assert payload["ok"] is True
    assert payload["recovery_states"]["closed_child"]["active"] is True
