from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.child_evidence_marker_template import generate_child_evidence_marker_template


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


def test_generate_child_evidence_marker_template_incomplete_default(
    monkeypatch,
    tmp_path: Path,
) -> None:
    config = _config(tmp_path)
    monkeypatch.setattr(
        "aresforge.operator.child_evidence_marker_template.fetch_issue_details",
        lambda _config, issue_number: {
            "ok": True,
            "issue": {
                "number": issue_number,
                "state": "OPEN",
                "title": "M24 child #403",
                "url": f"https://github.com/yoey2112/aresforge/issues/{issue_number}",
            },
        },
    )

    payload = generate_child_evidence_marker_template(config, parent_issue=400, child_issue=403)

    assert payload["ok"] is True
    assert payload["read_only"] is True
    assert payload["canonical_marker"]["marker_type"] == "child_evidence"
    assert payload["canonical_marker"]["marker_state"] == "incomplete"
    assert "branch" in payload["canonical_marker"]["missing_required_fields"]
    assert "pr" in payload["canonical_marker"]["missing_required_fields"]
    assert "required.parent_issue: #400" in payload["canonical_marker_text"]
    assert "required.child_issue: #403" in payload["canonical_marker_text"]
    assert "```" not in payload["canonical_marker_text"]


def test_generate_child_evidence_marker_template_complete_input(
    monkeypatch,
    tmp_path: Path,
) -> None:
    config = _config(tmp_path)
    monkeypatch.setattr(
        "aresforge.operator.child_evidence_marker_template.fetch_issue_details",
        lambda _config, issue_number: {
            "ok": True,
            "issue": {
                "number": issue_number,
                "state": "OPEN",
                "title": "M24 child #403",
                "url": f"https://github.com/yoey2112/aresforge/issues/{issue_number}",
            },
        },
    )

    payload = generate_child_evidence_marker_template(
        config,
        parent_issue=400,
        child_issue=403,
        branch="m24-403-child-marker-template",
        commit="abc1234",
        pr="#413",
        validation_summary="git diff --check=pass; pytest=pass",
        safety_notes="read-only by default",
        closeout_status="open",
        evidence_comment_status="posted",
        merge_status="merged",
    )

    assert payload["ok"] is True
    assert payload["canonical_marker"]["marker_state"] == "ready"
    assert payload["canonical_marker"]["missing_required_fields"] == []
    assert payload["canonical_marker"]["optional_fields"]["closeout_status"] == "open"
    assert payload["canonical_marker"]["optional_fields"]["evidence_comment_status"] == "posted"
    assert payload["canonical_marker"]["optional_fields"]["merge_status"] == "merged"