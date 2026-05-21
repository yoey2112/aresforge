from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator import batch_closeout_planner


def make_config(tmp_path: Path) -> AppConfig:
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


def test_plan_batch_closeout_read_only_parent_child_summary(monkeypatch, tmp_path: Path) -> None:
    config = make_config(tmp_path)

    parent_issue = {
        "number": 172,
        "title": "M7 parent",
        "state": "OPEN",
        "url": "https://example.test/172",
        "body": "- [x] #173\n- [x] #174\n- [ ] #176\nDo not modify Issue #39.",
        "reference_classification": {
            "implementation_issue_numbers": [173, 174, 176],
        },
    }
    child_173 = {
        "number": 173,
        "title": "Contract",
        "state": "CLOSED",
        "url": "https://example.test/173",
        "labels": ["aresforge-ready"],
        "reference_classification": {"implementation_issue_numbers": [172]},
    }
    child_176 = {
        "number": 176,
        "title": "Closeout planner",
        "state": "OPEN",
        "url": "https://example.test/176",
        "labels": ["aresforge-ready"],
        "reference_classification": {"implementation_issue_numbers": [172]},
    }

    def fake_fetch(_config, numbers):
        if numbers == [172]:
            return {"issues": [parent_issue], "excluded_issues": [], "warnings": []}
        if numbers == [173, 174, 176]:
            return {
                "issues": [child_173, child_176],
                "excluded_issues": [{"number": 39, "reason": "protected_issue"}],
                "warnings": [],
            }
        raise AssertionError(f"unexpected numbers: {numbers}")

    monkeypatch.setattr(batch_closeout_planner, "fetch_issue_batch_for_planning", fake_fetch)
    payload = batch_closeout_planner.plan_batch_closeout(config, parent_issue=172)

    assert payload["ok"] is True
    assert payload["closeout_plan"]["mutation_posture"] == "planning_only_no_close_or_comment"
    assert payload["closeout_plan"]["readiness"] == "not_ready"
    assert [item["number"] for item in payload["child_issue_group"]["completed_children"]] == [173]
    assert [item["number"] for item in payload["child_issue_group"]["open_or_blocked_children"]] == [176]
    assert payload["child_issue_group"]["excluded_issues"] == [{"number": 39, "reason": "protected_issue"}]


def test_plan_batch_closeout_fails_when_parent_missing(monkeypatch, tmp_path: Path) -> None:
    config = make_config(tmp_path)
    monkeypatch.setattr(
        batch_closeout_planner,
        "fetch_issue_batch_for_planning",
        lambda _config, _numbers: {"issues": [], "excluded_issues": [], "warnings": []},
    )

    payload = batch_closeout_planner.plan_batch_closeout(config, parent_issue=172)
    assert payload["ok"] is False
    assert payload["error"] == "parent_issue_unavailable"
