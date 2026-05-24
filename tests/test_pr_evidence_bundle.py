from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator import pr_evidence_bundle


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


def test_generate_pr_evidence_bundle_dry_run(monkeypatch, tmp_path: Path) -> None:
    config = _config(tmp_path)
    monkeypatch.setattr(
        pr_evidence_bundle,
        "fetch_issue_details",
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
    monkeypatch.setattr(
        pr_evidence_bundle,
        "_fetch_pr_details",
        lambda _config, pr_number: {
            "ok": True,
            "pr": {
                "number": pr_number,
                "title": "M22 work",
                "url": f"https://github.com/yoey2112/aresforge/pull/{pr_number}",
                "head_branch": "m22-367-pr-evidence-bundle-integration",
                "merge_commit": None,
                "files_changed": ["src/aresforge/operator/pr_evidence_bundle.py", "src/aresforge/cli.py"],
            },
        },
    )

    payload = pr_evidence_bundle.generate_pr_evidence_bundle(config, issue_number=367, pr_number=376)

    assert payload["ok"] is True
    assert payload["read_only"] is True
    assert payload["mutation"]["attempted"] is False
    assert "### Summary" in payload["pr_body_text"]
    assert "### Issue" in payload["pr_body_text"]
    assert "### Files changed" in payload["pr_body_text"]
    assert "### Validation" in payload["pr_body_text"]
    assert "### Safety posture" in payload["pr_body_text"]
    assert "### Notes/warnings" in payload["pr_body_text"]
    assert "### Canonical Marker" in payload["pr_body_text"]
    assert payload["canonical_marker"]["marker_type"] == "pr_evidence"
    assert "gh pr edit 376 --body-file artifacts/pr-376-body.md" in payload["targeted_pr_update_guidance"][1]


def test_generate_pr_evidence_bundle_invalid_target(tmp_path: Path) -> None:
    payload = pr_evidence_bundle.generate_pr_evidence_bundle(_config(tmp_path), issue_number=0, pr_number=-1)

    assert payload["ok"] is False
    assert payload["error"] == "invalid_target"
    assert "invalid_issue_target" in payload["blocked_reasons"]
    assert "invalid_pr_target" in payload["blocked_reasons"]


def test_generate_pr_evidence_bundle_pr_lookup_failure(monkeypatch, tmp_path: Path) -> None:
    config = _config(tmp_path)
    monkeypatch.setattr(
        pr_evidence_bundle,
        "fetch_issue_details",
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
    monkeypatch.setattr(
        pr_evidence_bundle,
        "_fetch_pr_details",
        lambda _config, pr_number: {
            "ok": False,
            "error": "pr_lookup_failed",
            "details": "not found",
        },
    )

    payload = pr_evidence_bundle.generate_pr_evidence_bundle(config, issue_number=367, pr_number=99999)

    assert payload["ok"] is False
    assert payload["error"] == "pr_lookup_failed"