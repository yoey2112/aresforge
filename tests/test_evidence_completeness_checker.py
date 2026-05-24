import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator import evidence_completeness_checker
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


def _issue(
    number: int,
    *,
    state: str = "OPEN",
    title: str = "issue",
    body: str = "",
    impl_refs: list[int] | None = None,
    explicit_refs: list[int] | None = None,
    safety_refs: list[int] | None = None,
    merged_prs: list[dict] | None = None,
) -> dict:
    return {
        "number": number,
        "state": state,
        "title": title,
        "url": f"https://example.test/issues/{number}",
        "body": body,
        "reference_classification": {
            "implementation_issue_numbers": impl_refs or [],
            "explicit_implementation_issue_numbers": explicit_refs or [],
            "safety_or_historical_issue_numbers": safety_refs or [],
            "contains_protected_issue_implementation_link": False,
        },
        "merged_pr_evidence": merged_prs or [],
    }


def test_ready_issue_with_merged_pr_and_mapping(monkeypatch, tmp_path: Path) -> None:
    config = _config(tmp_path)
    monkeypatch.setattr(
        evidence_completeness_checker,
        "fetch_issue_details",
        lambda _config, _issue_number: {
            "ok": True,
            "issue": _issue(
                270,
                body="Implements #270",
                impl_refs=[269],
                explicit_refs=[270],
                merged_prs=[{"number": 400}],
            ),
        },
    )
    payload = evidence_completeness_checker.check_issue_evidence_readiness(config, issue_number=270)
    assert payload["classification"] == "ready"
    assert payload["duplicate_noop_planning"]["new_pr_needed"] is False
    assert payload["duplicate_noop_planning"]["recommendation"] == "reuse_existing_pr_evidence"


def test_not_ready_issue_with_no_merged_pr(monkeypatch, tmp_path: Path) -> None:
    config = _config(tmp_path)
    monkeypatch.setattr(
        evidence_completeness_checker,
        "fetch_issue_details",
        lambda _config, _issue_number: {"ok": True, "issue": _issue(270, impl_refs=[269], explicit_refs=[270])},
    )
    payload = evidence_completeness_checker.check_issue_evidence_readiness(config, issue_number=270)
    assert payload["classification"] == "not_ready"
    assert payload["duplicate_noop_planning"]["new_pr_needed"] is True


def test_ambiguous_issue_with_historical_references(monkeypatch, tmp_path: Path) -> None:
    config = _config(tmp_path)
    monkeypatch.setattr(
        evidence_completeness_checker,
        "fetch_issue_details",
        lambda _config, _issue_number: {
            "ok": True,
            "issue": _issue(270, impl_refs=[269], safety_refs=[39], explicit_refs=[]),
        },
    )
    payload = evidence_completeness_checker.check_issue_evidence_readiness(config, issue_number=270)
    assert payload["classification"] == "ambiguous"


def test_blocked_issue_missing_lineage(monkeypatch, tmp_path: Path) -> None:
    config = _config(tmp_path)
    monkeypatch.setattr(
        evidence_completeness_checker,
        "fetch_issue_details",
        lambda _config, _issue_number: {"ok": True, "issue": _issue(270, impl_refs=[], explicit_refs=[])},
    )
    payload = evidence_completeness_checker.check_issue_evidence_readiness(config, issue_number=270)
    assert payload["classification"] == "blocked"


def test_already_closed_issue_classification(monkeypatch, tmp_path: Path) -> None:
    config = _config(tmp_path)
    monkeypatch.setattr(
        evidence_completeness_checker,
        "fetch_issue_details",
        lambda _config, _issue_number: {"ok": True, "issue": _issue(270, state="CLOSED")},
    )
    payload = evidence_completeness_checker.check_issue_evidence_readiness(config, issue_number=270)
    assert payload["classification"] == "already_closed"


def test_duplicate_noop_with_merged_evidence_recommends_reuse(monkeypatch, tmp_path: Path) -> None:
    config = _config(tmp_path)
    monkeypatch.setattr(
        evidence_completeness_checker,
        "fetch_issue_details",
        lambda _config, _issue_number: {
            "ok": True,
            "issue": _issue(
                274,
                title="duplicate/no-op planner hardening",
                body="Implements #274",
                impl_refs=[269],
                explicit_refs=[274],
                merged_prs=[{"number": 401}],
            ),
        },
    )
    payload = evidence_completeness_checker.check_issue_evidence_readiness(config, issue_number=274)
    assert payload["duplicate_noop_planning"]["duplicate_pr_risk"] is True
    assert payload["duplicate_noop_planning"]["new_pr_needed"] is False


def test_docs_only_reconciliation_sufficient_case(monkeypatch, tmp_path: Path) -> None:
    config = _config(tmp_path)
    monkeypatch.setattr(
        evidence_completeness_checker,
        "fetch_issue_details",
        lambda _config, _issue_number: {
            "ok": True,
            "issue": _issue(
                276,
                title="docs-only reconciliation",
                body="documentation reconciliation Implements #276",
                impl_refs=[269],
                explicit_refs=[276],
                merged_prs=[{"number": 410}],
            ),
        },
    )
    payload = evidence_completeness_checker.check_issue_evidence_readiness(config, issue_number=276)
    assert payload["evidence_signals"]["docs_only_reconciliation"] is True
    assert payload["duplicate_noop_planning"]["new_pr_needed"] is False


def test_no_mutation_safety_fields(monkeypatch, tmp_path: Path) -> None:
    config = _config(tmp_path)
    monkeypatch.setattr(
        evidence_completeness_checker,
        "fetch_issue_details",
        lambda _config, _issue_number: {"ok": True, "issue": _issue(270, impl_refs=[269], explicit_refs=[270])},
    )
    payload = evidence_completeness_checker.check_issue_evidence_readiness(config, issue_number=270)
    assert payload["safety"]["mutation_allowed"] is False
    assert payload["safety"]["create_pr"] is False
    assert payload["safety"]["close_issues"] is False


def test_milestone_checker_implemented(monkeypatch, tmp_path: Path) -> None:
    config = _config(tmp_path)
    monkeypatch.setattr(
        evidence_completeness_checker,
        "inspect_milestone_state",
        lambda _config, parent_issue, state_file=None: {
            "ok": True,
            "parent_issue": {"issue_number": parent_issue},
            "child_issues": [
                {"issue_number": 270},
                {"issue_number": 271},
            ],
        },
    )

    def _check_issue(_config: AppConfig, *, issue_number: int) -> dict:
        return {
            "ok": True,
            "classification": "ready" if issue_number == 270 else "not_ready",
            "duplicate_noop_planning": {"new_pr_needed": issue_number != 270},
        }

    monkeypatch.setattr(evidence_completeness_checker, "check_issue_evidence_readiness", _check_issue)
    payload = evidence_completeness_checker.check_milestone_evidence_readiness(config, parent_issue=269)
    assert payload["ok"] is True
    assert payload["child_issue_count"] == 2
    assert payload["status_counts"]["ready"] == 1
    assert payload["status_counts"]["not_ready"] == 1


def test_conflicting_structured_mapping_is_blocked(monkeypatch, tmp_path: Path) -> None:
    config = _config(tmp_path)
    monkeypatch.setattr(
        evidence_completeness_checker,
        "fetch_issue_details",
        lambda _config, _issue_number: {
            "ok": True,
            "issue": {
                **_issue(299, impl_refs=[294], explicit_refs=[]),
                "evidence_mapping_analysis": {
                    "conflicting_structured_blocks_detected": True,
                    "duplicate_structured_blocks_detected": False,
                    "malformed_structured_blocks_detected": 0,
                },
            },
        },
    )
    payload = evidence_completeness_checker.check_issue_evidence_readiness(config, issue_number=299)
    assert payload["classification"] == "blocked"


def test_milestone_checker_offline_mode_uses_local_state_file_data(monkeypatch, tmp_path: Path) -> None:
    config = _config(tmp_path)
    state_file = tmp_path / "offline-state.json"
    state_file.write_text(
        json.dumps(
            {
                "parent_issue": {
                    "number": 421,
                    "state": "OPEN",
                    "title": "M25 Parent",
                    "url": "https://example.test/issues/421",
                    "milestone": {"title": "M25"},
                    "body": "",
                    "comments": [],
                    "merged_pr_evidence": [],
                    "reference_classification": {"implementation_issue_numbers": [422, 423]},
                },
                "child_issues": [
                    {
                        "number": 422,
                        "state": "CLOSED",
                        "title": "closed child",
                        "url": "https://example.test/issues/422",
                        "milestone": {"title": "M25"},
                        "body": "Parent issue: #421 Implements #422",
                        "comments": [],
                        "merged_pr_evidence": [{"number": 9001}],
                        "reference_classification": {
                            "implementation_issue_numbers": [421],
                            "explicit_implementation_issue_numbers": [422],
                            "safety_or_historical_issue_numbers": [],
                            "contains_protected_issue_implementation_link": False,
                        },
                    },
                    {
                        "number": 423,
                        "state": "OPEN",
                        "title": "open child no evidence",
                        "url": "https://example.test/issues/423",
                        "milestone": {"title": "M25"},
                        "body": "Parent issue: #421",
                        "comments": [],
                        "merged_pr_evidence": [],
                        "reference_classification": {
                            "implementation_issue_numbers": [421],
                            "explicit_implementation_issue_numbers": [],
                            "safety_or_historical_issue_numbers": [],
                            "contains_protected_issue_implementation_link": False,
                        },
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        evidence_completeness_checker,
        "fetch_issue_details",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("fetch_issue_details should not be called")),
    )
    monkeypatch.setattr(
        milestone_state_inspector.subprocess,
        "run",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("subprocess.run should not be called")),
    )

    payload = evidence_completeness_checker.check_milestone_evidence_readiness(
        config,
        parent_issue=421,
        state_file=state_file,
    )
    assert payload["ok"] is True
    assert payload["inspection_mode"] == "local_state_file"
    assert payload["state_file"] == str(state_file)
    assert payload["status_counts"]["already_closed"] == 1
    assert payload["status_counts"]["not_ready"] == 1

    by_number = {item["issue"]["number"]: item for item in payload["issues"]}
    assert by_number[422]["classification"] == "already_closed"
    assert by_number[423]["classification"] == "not_ready"


def test_milestone_checker_offline_invalid_state_file_propagates_inspection_failure(
    tmp_path: Path,
) -> None:
    config = _config(tmp_path)
    state_file = tmp_path / "offline-state-invalid.json"
    state_file.write_text("{invalid-json", encoding="utf-8")

    payload = evidence_completeness_checker.check_milestone_evidence_readiness(
        config,
        parent_issue=421,
        state_file=state_file,
    )
    assert payload["ok"] is False
    assert payload["error"] == "milestone_state_inspection_failed"
    assert payload["details"]["inspection_mode"] == "local_state_file"
    assert payload["details"]["error"] == "state_file_invalid_json"

