from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator import self_managed_milestone_handoff as handoff


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


def test_generate_self_managed_milestone_handoff() -> None:
    cfg = _config(Path.cwd())
    milestone_state = {
        "ok": True,
        "parent_issue": {"state": "OPEN", "url": "https://github.com/yoey2112/aresforge/issues/345"},
        "child_issues": [
            {"issue_number": 349, "state": "CLOSED", "title": "child 349", "url": "u349"},
            {"issue_number": 350, "state": "OPEN", "title": "child 350", "url": "u350"},
            {"issue_number": 351, "state": "OPEN", "title": "child 351", "url": "u351"},
            {"issue_number": 353, "state": "OPEN", "title": "child 353", "url": "u353"},
        ],
    }
    dashboard = {
        "ok": True,
        "warnings": ["w1"],
        "final_reconciliation": {"final_reconciliation_issue": {"issue_number": 353}},
    }

    handoff.inspect_milestone_state = lambda _config, parent_issue: milestone_state  # type: ignore[method-assign]
    handoff.inspect_milestone_dashboard = lambda _config, parent_issue: dashboard  # type: ignore[method-assign]
    handoff._current_main_head = lambda _config: "417f2070d68ded0c558cec6fb1cfbffd7c0d3a07"  # type: ignore[method-assign]

    payload = handoff.generate_self_managed_milestone_handoff(
        cfg,
        parent_issue=345,
        completed_child=349,
        validation_results=["python -m pytest: pass"],
    )
    assert payload["ok"] is True
    assert payload["read_only"] is True
    assert payload["next_child"] == 350
    package = payload["package"]
    assert package["current_main_head"] == "417f2070d68ded0c558cec6fb1cfbffd7c0d3a07"
    assert package["next_child"]["issue_number"] == 350
    assert package["next_child"]["is_final_reconciliation"] is False
    assert package["safety_state"]["parent_closeout_blocked_while_children_open"] is True
    assert "Parent issue #345 remains OPEN" in package["parent_status_note"]


def test_generate_self_managed_milestone_handoff_flags_final_reconciliation() -> None:
    cfg = _config(Path.cwd())
    handoff.inspect_milestone_state = lambda _config, parent_issue: {  # type: ignore[method-assign]
        "ok": True,
        "parent_issue": {"state": "OPEN", "url": "u"},
        "child_issues": [
            {"issue_number": 352, "state": "CLOSED", "title": "child 352", "url": "u352"},
            {"issue_number": 353, "state": "OPEN", "title": "child 353", "url": "u353"},
        ],
    }
    handoff.inspect_milestone_dashboard = lambda _config, parent_issue: {  # type: ignore[method-assign]
        "ok": True,
        "warnings": [],
        "final_reconciliation": {"final_reconciliation_issue": {"issue_number": 353}},
    }
    handoff._current_main_head = lambda _config: "head"  # type: ignore[method-assign]
    payload = handoff.generate_self_managed_milestone_handoff(cfg, parent_issue=345, completed_child=352)
    assert payload["ok"] is True
    assert payload["next_child"] == 353
    assert payload["package"]["next_child"]["is_final_reconciliation"] is True
