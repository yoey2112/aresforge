from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.pr_evidence_marker_template import generate_pr_evidence_marker_template


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


def test_generate_pr_evidence_marker_template_incomplete_default(
    monkeypatch,
    tmp_path: Path,
) -> None:
    config = _config(tmp_path)
    monkeypatch.setattr(
        "aresforge.operator.pr_evidence_marker_template.fetch_issue_details",
        lambda _config, issue_number: {
            "ok": True,
            "issue": {
                "number": issue_number,
                "title": "M24 child #404",
                "state": "OPEN",
                "url": f"https://github.com/yoey2112/aresforge/issues/{issue_number}",
            },
        },
    )
    monkeypatch.setattr(
        "aresforge.operator.pr_evidence_marker_template._fetch_pr_details",
        lambda _config, pr_number: {
            "ok": True,
            "pr": {
                "number": pr_number,
                "title": "M24 #404 implementation",
                "url": f"https://github.com/yoey2112/aresforge/pull/{pr_number}",
                "head_branch": "m24-404-pr-marker-template",
                "merge_commit": None,
                "files_changed": ["src/aresforge/cli.py"],
            },
        },
    )

    payload = generate_pr_evidence_marker_template(config, issue_number=404, pr_number=414)

    assert payload["ok"] is True
    assert payload["read_only"] is True
    assert payload["canonical_marker"]["marker_type"] == "pr_evidence"
    assert payload["canonical_marker"]["marker_state"] == "incomplete"
    assert "validation_summary" in payload["canonical_marker"]["missing_required_fields"]
    assert "safety_posture" in payload["canonical_marker"]["missing_required_fields"]
    assert "evidence_status" in payload["canonical_marker"]["missing_required_fields"]
    assert "required.issue: #404" in payload["canonical_marker_text"]
    assert "required.pr: #414" in payload["canonical_marker_text"]
    assert "```" not in payload["canonical_marker_text"]


def test_generate_pr_evidence_marker_template_complete_input(
    monkeypatch,
    tmp_path: Path,
) -> None:
    config = _config(tmp_path)
    monkeypatch.setattr(
        "aresforge.operator.pr_evidence_marker_template.fetch_issue_details",
        lambda _config, issue_number: {
            "ok": True,
            "issue": {
                "number": issue_number,
                "title": "M24 child #404",
                "state": "OPEN",
                "url": f"https://github.com/yoey2112/aresforge/issues/{issue_number}",
            },
        },
    )
    monkeypatch.setattr(
        "aresforge.operator.pr_evidence_marker_template._fetch_pr_details",
        lambda _config, pr_number: {
            "ok": True,
            "pr": {
                "number": pr_number,
                "title": "M24 #404 implementation",
                "url": f"https://github.com/yoey2112/aresforge/pull/{pr_number}",
                "head_branch": "m24-404-pr-marker-template",
                "merge_commit": "def5678",
                "files_changed": ["src/aresforge/cli.py", "tests/test_cli.py"],
            },
        },
    )

    payload = generate_pr_evidence_marker_template(
        config,
        issue_number=404,
        pr_number=414,
        validation_summary="git diff --check=pass; pytest=pass",
        safety_posture="read-only by default",
        evidence_status="ready",
        notes_warnings="none",
    )

    assert payload["ok"] is True
    assert payload["canonical_marker"]["marker_state"] == "ready"
    assert payload["canonical_marker"]["missing_required_fields"] == []
    assert payload["canonical_marker"]["required_fields"]["merge_status"] == "merged"
    assert payload["canonical_marker"]["optional_fields"]["notes_warnings"] == "none"