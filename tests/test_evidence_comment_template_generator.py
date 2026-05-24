from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.evidence_comment_template_generator import generate_evidence_comment_template


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


def test_generate_evidence_comment_template_is_read_only_and_issue_specific(
    monkeypatch, tmp_path: Path
) -> None:
    config = _config(tmp_path)

    monkeypatch.setattr(
        "aresforge.operator.evidence_comment_template_generator.fetch_issue_details",
        lambda _config, issue_number: {
            "ok": True,
            "issue": {
                "number": issue_number,
                "title": "M18 child #297",
                "state": "OPEN",
                "url": f"https://github.com/yoey2112/aresforge/issues/{issue_number}",
                "body": "Parent issue: #294\n- Add deterministic output\n- Avoid nested markdown fences",
                "reference_classification": {
                    "implementation_issue_numbers": [294, issue_number],
                    "parent_child_references": {
                        "parent_issue_numbers": [294],
                        "linked_issue_numbers": [],
                    },
                },
                "merged_pr_evidence": [
                    {
                        "number": 303,
                        "url": "https://github.com/yoey2112/aresforge/pull/303",
                        "title": "M18 implementation",
                        "state": "MERGED",
                        "merged_at": "2026-05-22T12:00:00Z",
                    }
                ],
            },
        },
    )
    monkeypatch.setattr(
        "aresforge.operator.evidence_comment_template_generator.check_issue_evidence_readiness",
        lambda _config, issue_number: {
            "ok": True,
            "classification": "not_ready",
            "reasons": ["missing_merged_pr_evidence"],
            "duplicate_noop_planning": {"closeout_ready": False},
            "issue": {"number": issue_number},
        },
    )
    monkeypatch.setattr(
        "aresforge.operator.evidence_comment_template_generator.inspect_milestone_dashboard",
        lambda _config, parent_issue: {
            "ok": True,
            "parent_issue": {
                "issue_number": parent_issue,
                "state": "OPEN",
                "title": "M18 Parent",
                "url": f"https://github.com/yoey2112/aresforge/issues/{parent_issue}",
            },
            "dashboard": {
                "recommended_next_child_issue": {"issue_number": 297},
                "parent_should_remain_open": True,
                "milestone_closeout_ready": False,
            },
            "final_reconciliation": {
                "final_reconciliation_issue": {
                    "issue_number": 301,
                    "state": "OPEN",
                    "title": "Final reconciliation",
                    "url": "https://github.com/yoey2112/aresforge/issues/301",
                }
            },
            "child_summary": {
                "open_child_issue_numbers": [297, 298, 299, 300, 301],
                "closed_child_issue_numbers": [295, 296],
                "accounted_for_child_issue_numbers": [295, 296],
            },
        },
    )
    monkeypatch.setattr(
        "aresforge.operator.evidence_comment_template_generator._fetch_pr_details",
        lambda repo, pr_number: {
            "merge_commit": "abc123",
            "files": ["src/aresforge/cli.py", "tests/test_cli.py"],
        },
    )
    monkeypatch.setattr(
        "aresforge.operator.evidence_comment_template_generator.generate_child_evidence_marker_template",
        lambda _config, parent_issue, child_issue: {
            "canonical_marker_text": (
                "[ARESFORGE_CANONICAL_EVIDENCE_MARKER]\n"
                "marker_type: child_evidence\n"
                "marker_state: ready\n"
                "[/ARESFORGE_CANONICAL_EVIDENCE_MARKER]\n"
            ),
            "canonical_marker": {
                "marker_type": "child_evidence",
                "marker_state": "ready",
                "missing_required_fields": (),
                "invalid_reasons": (),
            },
        },
    )

    payload = generate_evidence_comment_template(config, issue_number=297)

    assert payload["ok"] is True
    assert payload["read_only"] is True
    assert payload["target_issue"]["number"] == 297
    assert payload["parent_issue"] == 294
    assert payload["safety_gates"]["close_issues"] is False
    assert payload["evidence_status"]["classification"] == "not_ready"
    assert payload["template_summary"]["issue_specific"] is True
    assert payload["template_summary"]["includes_canonical_marker_completeness_section"] is True
    assert payload["template_summary"]["contains_nested_markdown_fences"] is False
    assert payload["closeout_comment_ready"] is True
    assert payload["canonical_marker_completeness"]["marker_complete"] is True
    assert payload["canonical_marker_completeness"]["post_hoc_marker_repair_required"] is False
    assert payload["canonical_marker_completeness"]["marker_scope"] == "generated_closeout_comment"
    assert "### Issue-Specific Evidence Mapping" in payload["template"]
    assert "Implementation evidence:" in payload["template"]
    assert "Validation evidence:" in payload["template"]
    assert "Canonical marker completeness:" in payload["template"]
    assert "marker_complete: True" in payload["template"]
    assert "Canonical marker (copy/paste-safe):" in payload["template"]
    assert "Final reconciliation issue: #301 (state: OPEN)" in payload["template"]
    assert "```" not in payload["template"]


def test_generate_evidence_comment_template_handles_issue_lookup_failure(
    monkeypatch, tmp_path: Path
) -> None:
    config = _config(tmp_path)

    monkeypatch.setattr(
        "aresforge.operator.evidence_comment_template_generator.fetch_issue_details",
        lambda _config, _issue_number: {
            "ok": False,
            "error": "gh_issue_view_failed",
            "details": {"stderr": "not found"},
        },
    )

    payload = generate_evidence_comment_template(config, issue_number=297)

    assert payload["ok"] is False
    assert payload["read_only"] is True
    assert payload["target_issue"] == 297
    assert payload["error"] == "gh_issue_view_failed"


def test_generate_evidence_comment_template_reports_incomplete_marker_state_without_parent_lineage(
    monkeypatch, tmp_path: Path
) -> None:
    config = _config(tmp_path)

    monkeypatch.setattr(
        "aresforge.operator.evidence_comment_template_generator.fetch_issue_details",
        lambda _config, issue_number: {
            "ok": True,
            "issue": {
                "number": issue_number,
                "title": "M25 child #426",
                "state": "OPEN",
                "url": f"https://github.com/yoey2112/aresforge/issues/{issue_number}",
                "body": "- Add closeout comment generation checks",
                "reference_classification": {},
                "merged_pr_evidence": [],
            },
        },
    )
    monkeypatch.setattr(
        "aresforge.operator.evidence_comment_template_generator.check_issue_evidence_readiness",
        lambda _config, issue_number: {
            "ok": True,
            "classification": "ready",
            "reasons": [],
            "duplicate_noop_planning": {"closeout_ready": True},
            "issue": {"number": issue_number},
        },
    )

    payload = generate_evidence_comment_template(config, issue_number=426)

    assert payload["ok"] is True
    assert payload["parent_issue"] is None
    assert payload["closeout_comment_ready"] is False
    assert payload["canonical_marker_completeness"]["state"] == "incomplete"
    assert payload["canonical_marker_completeness"]["marker_complete"] is False
    assert payload["canonical_marker_completeness"]["missing_required_fields"] == ["parent_issue"]
    assert payload["canonical_marker_completeness"]["invalid_reasons"] == ["parent_issue_lineage_not_detected"]
    assert payload["canonical_marker_completeness"]["post_hoc_marker_repair_required"] is True
    assert (
        "Canonical marker completeness is not ready; missing/invalid marker fields must be resolved before closeout comment posting."
        in payload["warnings"]
    )
