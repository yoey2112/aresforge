import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.closeout_planning_drift import inspect_closeout_planning_drift
from aresforge.operator.planning_state import persist_sprint_plan


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


def test_inspect_closeout_planning_drift_handles_missing_state(tmp_path: Path) -> None:
    config = _config(tmp_path)
    payload = inspect_closeout_planning_drift(
        config,
        parent_issue=210,
        planning_state_path=str(tmp_path / ".aresforge" / "planning-state.json"),
    )
    assert payload["ok"] is True
    assert payload["state_exists"] is False
    assert payload["evidence_summary"]["status"] == "planning_state_missing"


def test_inspect_closeout_planning_drift_compares_planned_and_discovered(monkeypatch, tmp_path: Path) -> None:
    from aresforge.operator import closeout_planning_drift

    config = _config(tmp_path)
    state_path = tmp_path / "planning-state.json"
    persist_sprint_plan(
        path=state_path,
        command_name="generate-sprint-issue-script",
        sprint_plan={
            "sprint_id": "M11",
            "parent_issue": {"number": 210, "title": "M11 Parent"},
            "children": [{"number": 211, "title": "A"}, {"number": 212, "title": "B"}, {"number": 39, "title": "Protected"}],
            "relationships": [],
        },
    )

    monkeypatch.setattr(
        closeout_planning_drift,
        "plan_batch_closeout",
        lambda _config, parent_issue: {
            "ok": True,
            "closeout_plan": {"readiness": "incomplete", "missing_evidence": ["validation_or_documentation_evidence_missing"]},
            "child_issue_group": {"discovered_child_issue_numbers": [211, 213]},
            "evidence_report": {
                "child_issues": [
                    {"number": 211, "merged_pr_evidence": [{"number": 901}], "missing_evidence": [], "readiness_classification": "ready"},
                    {"number": 213, "merged_pr_evidence": [], "missing_evidence": ["validation_evidence_missing"], "readiness_classification": "incomplete"},
                ],
                "discovered_child_links": [
                    {"child_issue_number": 39, "classification": "protected", "reason": "ignored_non_active_reference_line", "source": "parent_body"}
                ],
            },
        },
    )
    monkeypatch.setattr(
        closeout_planning_drift,
        "fetch_issue_batch_for_planning",
        lambda _config, numbers: {
            "issues": [
                {"number": 211, "state": "CLOSED"},
                {"number": 212, "state": "OPEN"},
            ],
            "excluded_issues": [],
            "warnings": [],
        },
    )

    payload = inspect_closeout_planning_drift(config, parent_issue=210, planning_state_path=str(state_path))
    assert payload["planned_child_issues"] == [211, 212]
    assert payload["discovered_child_issues"] == [211, 213]
    assert payload["matching_child_issues"] == [211]
    assert payload["planned_missing_from_discovery"] == [212]
    assert payload["discovered_extra_not_planned"] == [213]
    assert payload["closed_child_issues"] == [211]
    assert payload["open_child_issues"] == [212]
    assert payload["unresolved_child_issues"] == [213]
    assert payload["readiness_ok"] is False
    assert payload["evidence_summary"]["status"] == "drift_blocked"
    assert "planned_children_missing_from_live_discovery" in payload["evidence_summary"]["missing_evidence"]
    assert any(item["child_issue_number"] == 39 for item in payload["protected_or_historical_references_excluded"])


def test_inspect_closeout_planning_drift_payload_is_json_serializable(monkeypatch, tmp_path: Path) -> None:
    from aresforge.operator import closeout_planning_drift

    config = _config(tmp_path)
    state_path = tmp_path / "planning-state.json"
    persist_sprint_plan(
        path=state_path,
        command_name="generate-sprint-issue-script",
        sprint_plan={
            "sprint_id": "M11",
            "parent_issue": {"number": 210, "title": "M11 Parent"},
            "children": [{"number": 211, "title": "A"}],
            "relationships": [],
        },
    )
    monkeypatch.setattr(
        closeout_planning_drift,
        "plan_batch_closeout",
        lambda _config, parent_issue: {
            "ok": True,
            "closeout_plan": {"readiness": "ready", "missing_evidence": []},
            "child_issue_group": {"discovered_child_issue_numbers": [211]},
            "evidence_report": {"child_issues": [], "discovered_child_links": []},
        },
    )
    monkeypatch.setattr(
        closeout_planning_drift,
        "fetch_issue_batch_for_planning",
        lambda _config, numbers: {"issues": [{"number": 211, "state": "CLOSED"}], "excluded_issues": [], "warnings": []},
    )
    payload = inspect_closeout_planning_drift(config, parent_issue=210, planning_state_path=str(state_path))
    json.dumps(payload)
