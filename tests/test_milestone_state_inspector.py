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


def test_inspect_milestone_state_discovers_checklist_inline_children(monkeypatch, tmp_path: Path) -> None:
    config = _config(tmp_path)

    parent = {
        "number": 309,
        "state": "OPEN",
        "title": "M19 parent",
        "url": "https://example.test/issues/309",
        "milestone": {"title": "M19"},
        "body": "- [ ] Define contract (#310)\n- [ ] Reconciliation (#317)",
        "comments": [],
        "reference_classification": {"implementation_issue_numbers": []},
        "merged_pr_evidence": [],
    }
    child_310 = {
        "number": 310,
        "state": "CLOSED",
        "title": "contract",
        "url": "https://example.test/issues/310",
        "milestone": {"title": "M19"},
        "body": "Parent issue: #309",
        "comments": [],
        "reference_classification": {"implementation_issue_numbers": [309]},
        "merged_pr_evidence": [],
    }
    child_317 = {
        "number": 317,
        "state": "OPEN",
        "title": "reconciliation",
        "url": "https://example.test/issues/317",
        "milestone": {"title": "M19"},
        "body": "Parent issue: #309",
        "comments": [],
        "reference_classification": {"implementation_issue_numbers": [309]},
        "merged_pr_evidence": [],
    }

    def _fetch(_config: AppConfig, issue_number: int) -> dict:
        mapping = {309: parent, 310: child_310, 317: child_317}
        issue = mapping.get(issue_number)
        if issue is None:
            return {"ok": False, "error": "not_found"}
        return {"ok": True, "issue": issue}

    monkeypatch.setattr(milestone_state_inspector, "fetch_issue_details", _fetch)
    payload = milestone_state_inspector.inspect_milestone_state(config, parent_issue=309)
    assert payload["ok"] is True
    assert payload["child_discovery"]["discovered_child_issue_numbers"] == [310, 317]


def test_inspect_milestone_state_discovers_checkbox_prefixed_issue_lines(monkeypatch, tmp_path: Path) -> None:
    config = _config(tmp_path)

    parent = {
        "number": 326,
        "state": "OPEN",
        "title": "M20 parent",
        "url": "https://example.test/issues/326",
        "milestone": {"title": "M20"},
        "body": (
            "- [ ] #327 contract\n"
            "- [ ] #328 planner\n"
            "- [ ] #329 comments\n"
            "- [ ] #330 closeout\n"
            "- [ ] #331 pr helper\n"
            "- [ ] #332 audit\n"
            "- [ ] #333 docs\n"
            "- [ ] #334 source-of-truth reconciliation"
        ),
        "comments": [],
        "reference_classification": {"implementation_issue_numbers": []},
        "merged_pr_evidence": [],
    }

    def _child(issue_number: int, title: str) -> dict:
        return {
            "number": issue_number,
            "state": "CLOSED",
            "title": title,
            "url": f"https://example.test/issues/{issue_number}",
            "milestone": {"title": "M20"},
            "body": "Parent issue: #326",
            "comments": [],
            "reference_classification": {"implementation_issue_numbers": [326]},
            "merged_pr_evidence": [{"number": issue_number + 8, "merged_at": "2026-05-23T00:00:00Z"}],
        }

    children = {
        327: _child(327, "contract"),
        328: _child(328, "planner"),
        329: _child(329, "comments"),
        330: _child(330, "closeout"),
        331: _child(331, "pr helper"),
        332: _child(332, "audit"),
        333: _child(333, "docs"),
        334: _child(334, "source-of-truth reconciliation"),
    }

    def _fetch(_config: AppConfig, issue_number: int) -> dict:
        if issue_number == 326:
            return {"ok": True, "issue": parent}
        issue = children.get(issue_number)
        if issue is None:
            return {"ok": False, "error": "not_found"}
        return {"ok": True, "issue": issue}

    monkeypatch.setattr(milestone_state_inspector, "fetch_issue_details", _fetch)
    payload = milestone_state_inspector.inspect_milestone_state(config, parent_issue=326)

    assert payload["ok"] is True
    assert payload["child_discovery"]["discovered_child_issue_numbers"] == [327, 328, 329, 330, 331, 332, 333, 334]
    assert payload["summary"]["open_child_issue_count"] == 0
    assert payload["summary"]["closed_child_issue_count"] == 8


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

