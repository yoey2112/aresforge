import json
from pathlib import Path
from aresforge.config import AppConfig
from aresforge.operator import batch_closeout_planner

def _load_fixture(repo_root: Path, name: str) -> dict:
    return json.loads((repo_root / 'tests' / 'fixtures' / name).read_text(encoding='utf-8'))



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
            "explicit_implementation_issue_numbers": [173, 174, 176],
            "implementation_issue_numbers": [173, 174, 176],
        },
    }
    child_173 = {
        "number": 173,
        "title": "Contract",
        "state": "CLOSED",
        "url": "https://example.test/173",
        "labels": ["aresforge-ready"],
        "body": "## Validation\n- python -m pytest\n## Documentation\n- Update source-of-truth docs",
        "merged_pr_evidence": [{"number": 201, "merged_at": "2026-05-21T00:00:00Z"}],
        "reference_classification": {
            "implementation_issue_numbers": [172],
            "explicit_implementation_issue_numbers": [172],
        },
    }
    child_176 = {
        "number": 176,
        "title": "Closeout planner",
        "state": "OPEN",
        "url": "https://example.test/176",
        "labels": ["aresforge-ready"],
        "body": "## Validation\n- python -m pytest",
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
    assert payload["closeout_plan"]["readiness"] == "incomplete"
    assert [item["number"] for item in payload["child_issue_group"]["completed_children"]] == [173]
    assert [item["number"] for item in payload["child_issue_group"]["open_or_blocked_children"]] == [176]
    assert payload["child_issue_group"]["excluded_issues"] == [{"number": 39, "reason": "protected_issue"}]
    assert payload["child_issue_group"]["discovered_child_issue_numbers"] == [173, 174, 176]
    assert any(
        item["source"] == "parent_body" and item["classification"] == "active"
        for item in payload["evidence_report"]["discovered_child_links"]
    )
    assert payload["evidence_report"]["child_issues"][0]["readiness_classification"] == "ready"
    assert payload["evidence_report"]["child_issues"][1]["readiness_classification"] == "incomplete"


def test_plan_batch_closeout_marks_ambiguous_and_blocked_children(monkeypatch, tmp_path: Path) -> None:
    config = make_config(tmp_path)
    parent_issue = {
        "number": 182,
        "title": "M8 parent",
        "state": "OPEN",
        "url": "https://example.test/182",
        "body": "- [ ] #183\n- [ ] #188\n",
        "reference_classification": {"implementation_issue_numbers": [183, 188]},
    }
    child_183 = {
        "number": 183,
        "title": "Linkage hardening",
        "state": "CLOSED",
        "url": "https://example.test/183",
        "labels": [],
        "body": "No implementation line.\n## Validation\n- python -m pytest\n## Documentation\n- docs updated",
        "merged_pr_evidence": [{"number": 209, "merged_at": "2026-05-21T00:00:00Z"}],
        "reference_classification": {"implementation_issue_numbers": []},
    }
    child_188 = {
        "number": 188,
        "title": "Safety validation",
        "state": "CLOSED",
        "url": "https://example.test/188",
        "labels": [],
        "body": "Part of #182\n## Validation\n- python -m pytest\n## Documentation\n- docs updated",
        "merged_pr_evidence": [{"number": 210, "merged_at": "2026-05-21T00:00:00Z"}],
        "reference_classification": {
            "implementation_issue_numbers": [182, 39],
            "explicit_implementation_issue_numbers": [182],
            "contains_protected_issue_implementation_link": True,
        },
    }

    def fake_fetch(_config, numbers):
        if numbers == [182]:
            return {"issues": [parent_issue], "excluded_issues": [], "warnings": []}
        if numbers == [183, 188]:
            return {"issues": [child_183, child_188], "excluded_issues": [], "warnings": []}
        raise AssertionError(f"unexpected numbers: {numbers}")

    monkeypatch.setattr(batch_closeout_planner, "fetch_issue_batch_for_planning", fake_fetch)
    payload = batch_closeout_planner.plan_batch_closeout(config, parent_issue=182)
    by_number = {item["number"]: item for item in payload["evidence_report"]["child_issues"]}
    assert by_number[183]["readiness_classification"] == "ambiguous"
    assert by_number[188]["readiness_classification"] == "blocked"
    assert payload["closeout_plan"]["readiness"] == "blocked"


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


def test_plan_batch_closeout_does_not_write_planning_state_by_default(monkeypatch, tmp_path: Path) -> None:
    config = make_config(tmp_path)
    parent_issue = {
        "number": 200,
        "title": "Parent",
        "state": "OPEN",
        "url": "https://example.test/200",
        "body": "- [ ] #201",
        "reference_classification": {"implementation_issue_numbers": [201]},
    }
    child = {
        "number": 201,
        "title": "Child",
        "state": "OPEN",
        "url": "https://example.test/201",
        "labels": [],
        "body": "## Validation\n- python -m pytest",
        "reference_classification": {"implementation_issue_numbers": [200]},
    }

    def fake_fetch(_config, numbers):
        if numbers == [200]:
            return {"issues": [parent_issue], "excluded_issues": [], "warnings": []}
        return {"issues": [child], "excluded_issues": [], "warnings": []}

    monkeypatch.setattr(batch_closeout_planner, "fetch_issue_batch_for_planning", fake_fetch)
    payload = batch_closeout_planner.plan_batch_closeout(config, parent_issue=200)
    assert payload["ok"] is True
    assert not (tmp_path / ".aresforge" / "planning-state.json").exists()


def test_plan_batch_closeout_can_write_planning_snapshot(monkeypatch, tmp_path: Path) -> None:
    config = make_config(tmp_path)
    parent_issue = {
        "number": 210,
        "title": "Parent",
        "state": "OPEN",
        "url": "https://example.test/210",
        "body": "- [ ] #211",
        "reference_classification": {"implementation_issue_numbers": [211]},
    }
    child = {
        "number": 211,
        "title": "Child",
        "state": "OPEN",
        "url": "https://example.test/211",
        "labels": [],
        "body": "## Validation\n- python -m pytest",
        "reference_classification": {"implementation_issue_numbers": [210]},
    }

    def fake_fetch(_config, numbers):
        if numbers == [210]:
            return {"issues": [parent_issue], "excluded_issues": [], "warnings": []}
        return {"issues": [child], "excluded_issues": [], "warnings": []}

    monkeypatch.setattr(batch_closeout_planner, "fetch_issue_batch_for_planning", fake_fetch)
    state_path = tmp_path / "state" / "planning-state.json"
    payload = batch_closeout_planner.plan_batch_closeout(
        config,
        parent_issue=210,
        write_planning_snapshot=True,
        planning_state_path=str(state_path),
    )
    assert payload["ok"] is True
    assert state_path.exists()
    content = state_path.read_text(encoding="utf-8")
    assert "\"closeout_snapshots\"" in content


def test_plan_batch_closeout_discovers_children_from_parent_comments_m9_regression(monkeypatch, tmp_path: Path) -> None:
    config = make_config(tmp_path)
    parent_issue = {
        "number": 192,
        "title": "M9 parent",
        "state": "OPEN",
        "url": "https://example.test/192",
        "body": "Parent issue for M9 closeout.",
        "reference_classification": {"implementation_issue_numbers": []},
        "comments": [
            {"id": 1, "body": "Initial child issue index:\n- [x] #193\n- [x] #194"},
            {"id": 2, "body": "Corrected child issue index:\n- [x] #193\n- [x] #194\n- [x] #195\n- [x] #196\n- [x] #197\n- [x] #198\n- [x] #199"},
        ],
    }
    children = []
    for number in [193, 194, 195, 196, 197, 198, 199]:
        children.append(
            {
                "number": number,
                "title": f"Child {number}",
                "state": "CLOSED",
                "url": f"https://example.test/{number}",
                "labels": [],
                "body": "Part of #192\n## Validation\n- python -m pytest\n## Documentation\n- docs updated",
                "merged_pr_evidence": [{"number": 300 + number, "merged_at": "2026-05-21T00:00:00Z"}],
                "reference_classification": {
                    "implementation_issue_numbers": [192],
                    "explicit_implementation_issue_numbers": [192],
                },
            }
        )

    def fake_fetch(_config, numbers):
        if numbers == [192]:
            return {"issues": [parent_issue], "excluded_issues": [], "warnings": []}
        if numbers == [193, 194, 195, 196, 197, 198, 199]:
            return {"issues": children, "excluded_issues": [], "warnings": []}
        raise AssertionError(f"unexpected numbers: {numbers}")

    monkeypatch.setattr(batch_closeout_planner, "fetch_issue_batch_for_planning", fake_fetch)
    payload = batch_closeout_planner.plan_batch_closeout(config, parent_issue=192)

    assert payload["child_issue_group"]["requested_child_issue_numbers"] == [193, 194, 195, 196, 197, 198, 199]
    assert payload["closeout_plan"]["readiness"] == "incomplete"
    assert all(item["classification"] == "active" for item in payload["evidence_report"]["discovered_child_links"])
    assert any(item["source"] == "corrected_child_index" for item in payload["evidence_report"]["discovered_child_links"])


def test_plan_batch_closeout_ignores_historical_and_protected_references(monkeypatch, tmp_path: Path) -> None:
    config = make_config(tmp_path)
    parent_issue = {
        "number": 201,
        "title": "M10 parent",
        "state": "OPEN",
        "url": "https://example.test/201",
        "body": (
            "Historical validation evidence only: #39\n"
            "Do not modify Issue #39.\n"
            "Child issue index\n"
            "- [ ] #202"
        ),
        "reference_classification": {"implementation_issue_numbers": [202]},
        "comments": [{"id": 1, "body": "Safety note: Issue #39 remains protected."}],
    }
    child_202 = {
        "number": 202,
        "title": "Child",
        "state": "OPEN",
        "url": "https://example.test/202",
        "labels": [],
        "body": "Parent issue: #201\n## Validation\n- python -m pytest",
        "reference_classification": {
            "implementation_issue_numbers": [201],
            "explicit_implementation_issue_numbers": [201],
        },
        "merged_pr_evidence": [],
    }

    def fake_fetch(_config, numbers):
        if numbers == [201]:
            return {"issues": [parent_issue], "excluded_issues": [], "warnings": []}
        if numbers == [202]:
            return {"issues": [child_202], "excluded_issues": [], "warnings": []}
        raise AssertionError(f"unexpected numbers: {numbers}")

    monkeypatch.setattr(batch_closeout_planner, "fetch_issue_batch_for_planning", fake_fetch)
    payload = batch_closeout_planner.plan_batch_closeout(config, parent_issue=201)

    assert payload["child_issue_group"]["requested_child_issue_numbers"] == [202]
    assert not any(item["child_issue_number"] == 39 and item["classification"] == "active" for item in payload["evidence_report"]["discovered_child_links"])
    assert any(item["classification"] in {"protected", "safety", "historical"} for item in payload["evidence_report"]["discovered_child_links"])


def test_plan_batch_closeout_treats_parent_child_index_entries_as_active_even_with_historical_words(
    monkeypatch, tmp_path: Path
) -> None:
    config = make_config(tmp_path)
    parent_issue = {
        "number": 201,
        "title": "M10 parent",
        "state": "OPEN",
        "url": "https://example.test/201",
        "body": (
            "## Child issue index\n"
            "- #202 Define closeout child-link discovery contract\n"
            "- #203 Parse parent issue body and comments for active child issue references\n"
            "- #204 Parse child issue bodies for parent references\n"
            "- #205 Harden active-vs-historical reference classification for closeout links\n"
            "- #206 Improve evidence report with discovered child issues\n"
            "- #208 Add M9-style closeout planner regression tests\n"
            "- #207 Reconcile source-of-truth documentation\n"
            "- Historical validation evidence only: #39\n"
        ),
        "reference_classification": {"implementation_issue_numbers": []},
    }

    children = []
    for number in [202, 203, 204, 205, 206, 207, 208]:
        children.append(
            {
                "number": number,
                "title": f"M10 child {number}",
                "state": "OPEN",
                "url": f"https://example.test/{number}",
                "labels": [],
                "body": "Parent issue: #201\n## Validation\n- python -m pytest",
                "reference_classification": {
                    "implementation_issue_numbers": [201],
                    "explicit_implementation_issue_numbers": [201],
                },
                "merged_pr_evidence": [],
            }
        )

    def fake_fetch(_config, numbers):
        if numbers == [201]:
            return {"issues": [parent_issue], "excluded_issues": [], "warnings": []}
        if numbers == [202, 203, 204, 205, 206, 207, 208]:
            return {"issues": children, "excluded_issues": [], "warnings": []}
        raise AssertionError(f"unexpected numbers: {numbers}")

    monkeypatch.setattr(batch_closeout_planner, "fetch_issue_batch_for_planning", fake_fetch)
    payload = batch_closeout_planner.plan_batch_closeout(config, parent_issue=201)

    assert payload["child_issue_group"]["requested_child_issue_numbers"] == [202, 203, 204, 205, 206, 207, 208]
    assert payload["child_issue_group"]["discovered_child_issue_numbers"] == [202, 203, 204, 205, 206, 207, 208]
    active_links = [
        item["child_issue_number"]
        for item in payload["evidence_report"]["discovered_child_links"]
        if item["classification"] == "active"
    ]
    assert 205 in active_links
    assert 207 in active_links
    assert 208 in active_links
    assert not any(item["child_issue_number"] == 39 and item["classification"] == "active" for item in payload["evidence_report"]["discovered_child_links"])



def test_plan_batch_closeout_recognizes_m12_style_manual_closeout_comment_evidence(
    monkeypatch, tmp_path: Path
) -> None:
    config = make_config(tmp_path)
    fixture = _load_fixture(Path(__file__).resolve().parents[1], "m12-manual-closeout-comments.json")
    parent_issue = fixture["parent_issue"]
    children = fixture["children"]
    requested_children = [int(item["number"]) for item in children]

    def fake_fetch(_config, numbers):
        if numbers == [222]:
            return {"issues": [parent_issue], "excluded_issues": [], "warnings": []}
        if numbers == requested_children:
            return {"issues": children, "excluded_issues": [], "warnings": []}
        raise AssertionError(f"unexpected numbers: {numbers}")

    monkeypatch.setattr(batch_closeout_planner, "fetch_issue_batch_for_planning", fake_fetch)
    payload = batch_closeout_planner.plan_batch_closeout(config, parent_issue=222)

    assert payload["ok"] is True
    assert payload["closeout_plan"]["readiness"] == "ready"
    assert payload["closeout_plan"]["missing_evidence"] == []
    for child in payload["evidence_report"]["child_issues"]:
        assert child["readiness_classification"] == "ready"
        assert "merged_pr_evidence_missing" not in child["missing_evidence"]
        assert "validation_evidence_missing" not in child["missing_evidence"]
        assert "documentation_reconciliation_evidence_missing" not in child["missing_evidence"]
        assert child["closeout_comment_evidence"]["evidence_comment_count"] >= 1
        assert child["closeout_comment_evidence"]["validation_evidence"]
        assert child["closeout_comment_evidence"]["documentation_reconciliation_evidence"]
        assert child["merged_pr_evidence"]


def test_plan_batch_closeout_does_not_activate_historical_parent_body_references_with_corrected_index(
    monkeypatch, tmp_path: Path
) -> None:
    config = make_config(tmp_path)
    parent_issue = {
        "number": 233,
        "title": "M13 parent",
        "state": "OPEN",
        "url": "https://example.test/233",
        "body": (
            "## Background\n"
            "Historical context from prior milestone: #223 #224 #225 #226 #227 #228 #229\n"
            "## Child issue index\n"
            "- [x] #234\n"
            "- [x] #235\n"
        ),
        "reference_classification": {
            "implementation_issue_numbers": [223, 224, 225, 226, 227, 228, 229, 234, 235],
            "explicit_implementation_issue_numbers": [234, 235],
        },
        "comments": [
            {
                "id": 1,
                "body": "Corrected child issue index:\n- [x] #234\n- [x] #235\n- [x] #236\n- [x] #237\n- [x] #238\n- [x] #239\n- [x] #240\n- [x] #241",
            }
        ],
    }
    children = []
    for number in [234, 235, 236, 237, 238, 239, 240, 241]:
        children.append(
            {
                "number": number,
                "title": f"M13 child {number}",
                "state": "CLOSED",
                "url": f"https://example.test/{number}",
                "labels": [],
                "body": "Parent issue: #233\n## Validation\n- python -m pytest\n## Documentation\n- source-of-truth reconciliation",
                "reference_classification": {
                    "implementation_issue_numbers": [233],
                    "explicit_implementation_issue_numbers": [233],
                },
                "merged_pr_evidence": [{"number": 300 + number, "merged_at": "2026-05-21T00:00:00Z"}],
            }
        )

    def fake_fetch(_config, numbers):
        if numbers == [233]:
            return {"issues": [parent_issue], "excluded_issues": [], "warnings": []}
        if numbers == [234, 235, 236, 237, 238, 239, 240, 241]:
            return {"issues": children, "excluded_issues": [], "warnings": []}
        raise AssertionError(f"unexpected numbers: {numbers}")

    monkeypatch.setattr(batch_closeout_planner, "fetch_issue_batch_for_planning", fake_fetch)
    payload = batch_closeout_planner.plan_batch_closeout(config, parent_issue=233)

    assert payload["child_issue_group"]["requested_child_issue_numbers"] == [234, 235, 236, 237, 238, 239, 240, 241]
    active = {
        item["child_issue_number"]
        for item in payload["evidence_report"]["discovered_child_links"]
        if item["classification"] == "active"
    }
    assert active == {234, 235, 236, 237, 238, 239, 240, 241}
    historical = {
        item["child_issue_number"]
        for item in payload["evidence_report"]["discovered_child_links"]
        if item["classification"] == "historical"
    }
    assert {223, 224, 225, 226, 227, 228, 229}.issubset(historical)

