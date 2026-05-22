import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator import sequential_run_state as srs


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


def test_resolve_sequential_run_state_path_default(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    path = srs.resolve_sequential_run_state_path(config=cfg)
    assert path == (tmp_path / ".aresforge" / "sequential-run-state.json").resolve()


def test_inspect_sequential_run_state_read_only(monkeypatch, tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    monkeypatch.setattr(
        srs,
        "inspect_milestone_state",
        lambda _config, parent_issue: {
            "ok": True,
            "child_issues": [
                {"issue_number": 311, "state": "OPEN", "merged_pr_count": 0},
                {"issue_number": 310, "state": "CLOSED", "merged_pr_count": 1},
            ],
        },
    )
    monkeypatch.setattr(
        srs,
        "plan_milestone_execution_queue",
        lambda _config, parent_issue: {
            "ok": True,
            "recommended_order": [
                {"issue_number": 311, "state": "OPEN", "is_final_reconciliation": False}
            ],
            "blocked_items": [],
        },
    )
    monkeypatch.setattr(
        srs,
        "check_milestone_evidence_readiness",
        lambda _config, parent_issue: {
            "ok": True,
            "status_counts": {"ready": 1, "not_ready": 1},
            "milestone_closeout_readiness": {"closeout_ready": False, "operator_review_required": True},
            "issues": [],
        },
    )

    result = srs.inspect_sequential_run_state(
        cfg,
        parent_issue=309,
        state_path=tmp_path / ".aresforge" / "sequential-run-state.json",
        write_local_state=False,
    )
    assert result["ok"] is True
    assert result["read_only"] is True
    assert result["snapshot"]["current_child_issue"] == 311
    assert result["snapshot"]["completed_children"] == [310]
    assert result["local_write"]["performed"] is False


def test_inspect_sequential_run_state_with_local_write(monkeypatch, tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    state_path = tmp_path / ".aresforge" / "sequential-run-state.json"
    monkeypatch.setattr(
        srs,
        "inspect_milestone_state",
        lambda _config, parent_issue: {"ok": True, "child_issues": []},
    )
    monkeypatch.setattr(
        srs,
        "plan_milestone_execution_queue",
        lambda _config, parent_issue: {"ok": True, "recommended_order": [], "blocked_items": []},
    )
    monkeypatch.setattr(
        srs,
        "check_milestone_evidence_readiness",
        lambda _config, parent_issue: {
            "ok": True,
            "status_counts": {},
            "milestone_closeout_readiness": {"closeout_ready": True, "operator_review_required": True},
            "issues": [],
        },
    )

    result = srs.inspect_sequential_run_state(
        cfg,
        parent_issue=309,
        state_path=state_path,
        write_local_state=True,
    )
    assert result["ok"] is True
    assert result["read_only"] is False
    assert result["local_write"]["performed"] is True
    stored = json.loads(state_path.read_text(encoding="utf-8"))
    assert stored["schema_version"] == "1.0"
    assert isinstance(stored["records"], list)
