from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator import evidence_completeness_checker


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
        lambda _config, parent_issue: {
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

