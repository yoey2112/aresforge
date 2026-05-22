from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator import child_execution_gates as gates


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


def test_inspect_child_execution_gates_ready(monkeypatch, tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    monkeypatch.setattr(
        gates,
        "fetch_issue_details",
        lambda _config, issue_number: {
            "ok": True,
            "issue": {
                "number": issue_number,
                "state": "OPEN",
                "title": "M19: Child",
                "body": "Parent issue: #309",
                "merged_pr_evidence": [{"number": 900}],
            },
        },
    )
    monkeypatch.setattr(
        gates,
        "check_issue_evidence_readiness",
        lambda _config, issue_number: {"classification": "ready"},
    )
    monkeypatch.setattr(gates, "_git_branch", lambda _config: "m19/312-child-execution-gates")
    monkeypatch.setattr(gates, "_git_dirty", lambda _config: False)
    monkeypatch.setattr(gates, "_find_open_pr_for_issue", lambda _config, issue_number: None)

    payload = gates.inspect_child_execution_gates(cfg, issue_number=312, parent_issue=309)
    assert payload["ok"] is True
    assert payload["gate_status"]["safe_to_start"] is True
    assert payload["gate_status"]["safe_to_pr"] is True
    assert payload["gate_status"]["safe_to_merge"] is False
    assert payload["gate_status"]["safe_to_close"] is True


def test_inspect_child_execution_gates_blocked_dirty(monkeypatch, tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    monkeypatch.setattr(
        gates,
        "fetch_issue_details",
        lambda _config, issue_number: {
            "ok": True,
            "issue": {"number": issue_number, "state": "OPEN", "body": "Parent issue: #309", "merged_pr_evidence": []},
        },
    )
    monkeypatch.setattr(
        gates,
        "check_issue_evidence_readiness",
        lambda _config, issue_number: {"classification": "not_ready"},
    )
    monkeypatch.setattr(gates, "_git_branch", lambda _config: "main")
    monkeypatch.setattr(gates, "_git_dirty", lambda _config: True)
    monkeypatch.setattr(gates, "_find_open_pr_for_issue", lambda _config, issue_number: None)
    payload = gates.inspect_child_execution_gates(cfg, issue_number=312, parent_issue=309)
    assert payload["gate_status"]["blocked"] is True
    reasons = {item["reason"] for item in payload["blockers"]}
    assert "dirty_worktree" in reasons
    assert "missing_open_pr" in reasons


def test_inspect_child_execution_gates_already_closed(monkeypatch, tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    monkeypatch.setattr(
        gates,
        "fetch_issue_details",
        lambda _config, issue_number: {"ok": True, "issue": {"number": issue_number, "state": "CLOSED", "body": ""}},
    )
    monkeypatch.setattr(gates, "check_issue_evidence_readiness", lambda _config, issue_number: {"classification": "already_closed"})
    monkeypatch.setattr(gates, "_git_branch", lambda _config: "main")
    monkeypatch.setattr(gates, "_git_dirty", lambda _config: False)
    monkeypatch.setattr(gates, "_find_open_pr_for_issue", lambda _config, issue_number: None)
    payload = gates.inspect_child_execution_gates(cfg, issue_number=312, parent_issue=309)
    assert payload["gate_status"]["already_closed"] is True
    assert payload["blockers"] == []


def test_inspect_child_execution_gates_missing_pr_evidence(monkeypatch, tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    monkeypatch.setattr(
        gates,
        "fetch_issue_details",
        lambda _config, issue_number: {
            "ok": True,
            "issue": {"number": issue_number, "state": "OPEN", "body": "Parent issue: #309", "merged_pr_evidence": []},
        },
    )
    monkeypatch.setattr(
        gates,
        "check_issue_evidence_readiness",
        lambda _config, issue_number: {"classification": "not_ready"},
    )
    monkeypatch.setattr(gates, "_git_branch", lambda _config: "m19/312-child-execution-gates")
    monkeypatch.setattr(gates, "_git_dirty", lambda _config: False)
    monkeypatch.setattr(gates, "_find_open_pr_for_issue", lambda _config, issue_number: None)
    payload = gates.inspect_child_execution_gates(cfg, issue_number=312, parent_issue=309)
    assert payload["gate_status"]["safe_to_close"] is False
    reasons = {item["reason"] for item in payload["blockers"]}
    assert "missing_merged_pr_evidence" in reasons
