from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator import milestone_state_inspector


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


def test_inspect_milestone_state_discovers_children_and_reports_read_only(monkeypatch, tmp_path: Path) -> None:
    config = _config(tmp_path)

    parent = {
        "number": 269,
        "state": "OPEN",
        "title": "M17 parent",
        "url": "https://example.test/issues/269",
        "milestone": {"title": "M17"},
        "body": "- #270\n- #271",
        "comments": [],
        "reference_classification": {"implementation_issue_numbers": [270, 271]},
        "merged_pr_evidence": [],
    }
    child_270 = {
        "number": 270,
        "state": "OPEN",
        "title": "contract",
        "url": "https://example.test/issues/270",
        "milestone": {"title": "M17"},
        "body": "Parent issue: #269",
        "comments": [],
        "reference_classification": {"implementation_issue_numbers": [269]},
        "merged_pr_evidence": [],
    }
    child_271 = {
        "number": 271,
        "state": "OPEN",
        "title": "inspector",
        "url": "https://example.test/issues/271",
        "milestone": {"title": "M17"},
        "body": "",
        "comments": [],
        "reference_classification": {"implementation_issue_numbers": []},
        "merged_pr_evidence": [{"number": 300, "merged_at": "2026-05-22T00:00:00Z"}],
    }

    def _fetch(_config: AppConfig, issue_number: int) -> dict:
        if issue_number == 269:
            return {"ok": True, "issue": parent}
        if issue_number == 270:
            return {"ok": True, "issue": child_270}
        if issue_number == 271:
            return {"ok": True, "issue": child_271}
        return {"ok": False, "error": "not_found"}

    monkeypatch.setattr(milestone_state_inspector, "fetch_issue_details", _fetch)

    payload = milestone_state_inspector.inspect_milestone_state(config, parent_issue=269)

    assert payload["ok"] is True
    assert payload["read_only"] is True
    assert payload["child_discovery"]["discovered_child_issue_numbers"] == [270, 271]
    assert payload["summary"]["child_issue_count"] == 2
    assert payload["evidence_hints"]["child_issues_with_merged_pr_evidence"] == [271]
    assert payload["lineage_hints"]["missing_parent_lineage_issue_numbers"] == [271]
    assert "No issues were closed." in payload["boundary_confirmations"]


def test_inspect_milestone_state_bubbles_parent_lookup_error(monkeypatch, tmp_path: Path) -> None:
    config = _config(tmp_path)
    monkeypatch.setattr(
        milestone_state_inspector,
        "fetch_issue_details",
        lambda _config, _issue_number: {"ok": False, "error": "gh_cli_failed", "details": {"exit_code": 1}},
    )

    payload = milestone_state_inspector.inspect_milestone_state(config, parent_issue=269)
    assert payload["ok"] is False
    assert payload["read_only"] is True
    assert payload["error"] == "gh_cli_failed"

