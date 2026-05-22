from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.child_closeout_script_generator import generate_child_closeout_script


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


def test_generate_child_closeout_script_is_read_only_and_single_issue(monkeypatch, tmp_path: Path) -> None:
    config = _config(tmp_path)

    monkeypatch.setattr(
        "aresforge.operator.child_closeout_script_generator.fetch_issue_details",
        lambda _config, issue_number: {
            "ok": True,
            "issue": {
                "number": issue_number,
                "title": "M18 child",
                "state": "OPEN",
                "url": f"https://github.com/yoey2112/aresforge/issues/{issue_number}",
                "reference_classification": {
                    "implementation_issue_numbers": [294, issue_number],
                    "parent_child_references": {
                        "parent_issue_numbers": [294],
                        "linked_issue_numbers": [],
                    },
                },
            },
        },
    )
    monkeypatch.setattr(
        "aresforge.operator.child_closeout_script_generator.check_issue_evidence_readiness",
        lambda _config, issue_number: {
            "ok": True,
            "classification": "not_ready",
            "reasons": ["missing_merged_pr_evidence"],
        },
    )

    payload = generate_child_closeout_script(config, issue_number=296)

    assert payload["ok"] is True
    assert payload["read_only"] is True
    assert payload["target_issue"] == 296
    assert payload["parent_issue"] == 294
    assert payload["script_summary"]["targets_single_issue"] is True
    assert payload["safety_gates"]["target_issue_only"] is True
    assert "gh issue close $TargetIssue" in payload["script"]
    assert "gh issue close 294" not in payload["script"]
    assert "gh issue close 301" not in payload["script"]
    assert "```" not in payload["script"]


def test_generate_child_closeout_script_handles_issue_lookup_failure(monkeypatch, tmp_path: Path) -> None:
    config = _config(tmp_path)

    monkeypatch.setattr(
        "aresforge.operator.child_closeout_script_generator.fetch_issue_details",
        lambda _config, _issue_number: {
            "ok": False,
            "error": "gh_issue_view_failed",
            "details": {"stderr": "not found"},
        },
    )

    payload = generate_child_closeout_script(config, issue_number=296)

    assert payload["ok"] is False
    assert payload["read_only"] is True
    assert payload["target_issue"] == 296
    assert payload["error"] == "gh_issue_view_failed"


def test_generate_child_closeout_script_warns_when_parent_not_detected(monkeypatch, tmp_path: Path) -> None:
    config = _config(tmp_path)

    monkeypatch.setattr(
        "aresforge.operator.child_closeout_script_generator.fetch_issue_details",
        lambda _config, issue_number: {
            "ok": True,
            "issue": {
                "number": issue_number,
                "title": "M18 child",
                "state": "OPEN",
                "url": f"https://github.com/yoey2112/aresforge/issues/{issue_number}",
                "reference_classification": {
                    "implementation_issue_numbers": [issue_number],
                    "parent_child_references": {
                        "parent_issue_numbers": [],
                        "linked_issue_numbers": [],
                    },
                },
            },
        },
    )
    monkeypatch.setattr(
        "aresforge.operator.child_closeout_script_generator.check_issue_evidence_readiness",
        lambda _config, issue_number: {
            "ok": True,
            "classification": "not_ready",
            "reasons": ["missing_merged_pr_evidence"],
        },
    )

    payload = generate_child_closeout_script(config, issue_number=296)

    assert payload["ok"] is True
    assert payload["parent_issue"] is None
    assert any("lineage was not detected" in warning for warning in payload["warnings"])
