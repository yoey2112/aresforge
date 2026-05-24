from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.child_closeout_evidence_bundle import generate_child_closeout_evidence_bundle


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


def test_generate_child_closeout_evidence_bundle_is_read_only(monkeypatch, tmp_path: Path) -> None:
    config = _config(tmp_path)
    monkeypatch.setattr(
        "aresforge.operator.child_closeout_evidence_bundle.fetch_issue_details",
        lambda _config, issue_number: {
            "ok": True,
            "issue": {
                "number": issue_number,
                "state": "OPEN",
                "title": "M22 child",
                "url": f"https://github.com/yoey2112/aresforge/issues/{issue_number}",
            },
        },
    )

    payload = generate_child_closeout_evidence_bundle(config, parent_issue=362, child_issue=365)
    assert payload["ok"] is True
    assert payload["read_only"] is True
    assert payload["parent_issue"] == 362
    assert payload["child_issue"] == 365
    assert "### Validation" in payload["evidence_comment_body"]
    assert "### Canonical Marker" in payload["evidence_comment_body"]
    assert payload["canonical_marker"]["marker_type"] == "child_evidence"
    assert payload["canonical_marker_completeness"]["state"] == "incomplete"
    assert payload["canonical_marker_completeness"]["marker_complete"] is False
    assert payload["canonical_marker_completeness"]["post_hoc_marker_repair_required"] is True
    assert "### Safety posture" in payload["evidence_comment_body"]
    assert "```" not in payload["evidence_comment_body"]


def test_generate_child_closeout_evidence_bundle_reports_incomplete_marker_state(
    monkeypatch,
    tmp_path: Path,
) -> None:
    config = _config(tmp_path)
    monkeypatch.setattr(
        "aresforge.operator.child_closeout_evidence_bundle.fetch_issue_details",
        lambda _config, issue_number: {
            "ok": True,
            "issue": {
                "number": issue_number,
                "state": "OPEN",
                "title": "M25 child",
                "url": f"https://github.com/yoey2112/aresforge/issues/{issue_number}",
            },
        },
    )
    monkeypatch.setattr(
        "aresforge.operator.child_closeout_evidence_bundle.generate_child_evidence_marker_template",
        lambda _config, parent_issue, child_issue: {
            "canonical_marker_text": "[ARESFORGE_CANONICAL_EVIDENCE_MARKER]\nmarker_state: incomplete\n[/ARESFORGE_CANONICAL_EVIDENCE_MARKER]\n",
            "canonical_marker": {
                "marker_type": "child_evidence",
                "marker_state": "incomplete",
                "missing_required_fields": ("commit", "pr"),
                "invalid_reasons": (),
            },
        },
    )

    payload = generate_child_closeout_evidence_bundle(config, parent_issue=421, child_issue=423)
    completeness = payload["canonical_marker_completeness"]
    assert completeness["state"] == "incomplete"
    assert completeness["missing_required_fields"] == ["commit", "pr"]
    assert completeness["marker_complete"] is False
    assert completeness["post_hoc_marker_repair_required"] is True

