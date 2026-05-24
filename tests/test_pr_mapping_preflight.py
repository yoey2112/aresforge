from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator import pr_mapping_preflight


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


def test_pr_mapping_preflight_complete(monkeypatch, tmp_path: Path) -> None:
    config = _config(tmp_path)
    monkeypatch.setattr(
        pr_mapping_preflight,
        "fetch_issue_details",
        lambda _config, issue_number: {
            "ok": True,
            "issue": {"number": issue_number, "body": "", "comments": []},
        },
    )
    monkeypatch.setattr(
        pr_mapping_preflight,
        "inspect_milestone_state",
        lambda _config, parent_issue: {
            "ok": True,
            "parent_issue": {"issue_number": parent_issue, "state": "OPEN"},
            "child_issues": [
                {"issue_number": 386, "title": "pr mapping", "state": "OPEN", "linked_pr_count": 1, "merged_pr_count": 1}
            ],
        },
    )

    payload = pr_mapping_preflight.inspect_pr_mapping_preflight(config, parent_issue=381)

    assert payload["ok"] is True
    assert payload["read_only"] is True
    assert payload["pr_mapping_summary"]["aggregate_state"] == "ready"


def test_pr_mapping_preflight_missing_mapping(monkeypatch, tmp_path: Path) -> None:
    config = _config(tmp_path)
    monkeypatch.setattr(
        pr_mapping_preflight,
        "fetch_issue_details",
        lambda _config, issue_number: {
            "ok": True,
            "issue": {"number": issue_number, "body": "", "comments": []},
        },
    )
    monkeypatch.setattr(
        pr_mapping_preflight,
        "inspect_milestone_state",
        lambda _config, parent_issue: {
            "ok": True,
            "parent_issue": {"issue_number": parent_issue, "state": "OPEN"},
            "child_issues": [
                {"issue_number": 386, "title": "pr mapping", "state": "OPEN", "linked_pr_count": 0, "merged_pr_count": 0}
            ],
        },
    )

    payload = pr_mapping_preflight.inspect_pr_mapping_preflight(config, parent_issue=381)

    assert payload["pr_mapping_summary"]["aggregate_state"] == "blocked"
    assert "pr.mapping.386:missing" in payload["blocked_reasons"]
    assert payload["children"][0]["missing_pr_mapping"] is True


def test_pr_mapping_preflight_ambiguous_mapping(monkeypatch, tmp_path: Path) -> None:
    config = _config(tmp_path)
    monkeypatch.setattr(
        pr_mapping_preflight,
        "fetch_issue_details",
        lambda _config, issue_number: {
            "ok": True,
            "issue": {"number": issue_number, "body": "", "comments": []},
        },
    )
    monkeypatch.setattr(
        pr_mapping_preflight,
        "inspect_milestone_state",
        lambda _config, parent_issue: {
            "ok": True,
            "parent_issue": {"issue_number": parent_issue, "state": "OPEN"},
            "child_issues": [
                {"issue_number": 386, "title": "pr mapping", "state": "OPEN", "linked_pr_count": 2, "merged_pr_count": 1}
            ],
        },
    )

    payload = pr_mapping_preflight.inspect_pr_mapping_preflight(config, parent_issue=381)

    assert payload["pr_mapping_summary"]["aggregate_state"] == "warning"
    assert "pr.mapping.386:ambiguous" in payload["warning_reasons"]
    assert payload["children"][0]["ambiguous_pr_mapping"] is True


def test_pr_mapping_preflight_unmerged_is_blocked(monkeypatch, tmp_path: Path) -> None:
    config = _config(tmp_path)
    monkeypatch.setattr(
        pr_mapping_preflight,
        "fetch_issue_details",
        lambda _config, issue_number: {
            "ok": True,
            "issue": {"number": issue_number, "body": "", "comments": []},
        },
    )
    monkeypatch.setattr(
        pr_mapping_preflight,
        "inspect_milestone_state",
        lambda _config, parent_issue: {
            "ok": True,
            "parent_issue": {"issue_number": parent_issue, "state": "OPEN"},
            "child_issues": [
                {"issue_number": 386, "title": "pr mapping", "state": "OPEN", "linked_pr_count": 1, "merged_pr_count": 0}
            ],
        },
    )

    payload = pr_mapping_preflight.inspect_pr_mapping_preflight(config, parent_issue=381)

    assert payload["pr_mapping_summary"]["aggregate_state"] == "blocked"
    assert "pr.mapping.386:incomplete" in payload["blocked_reasons"]
    assert payload["children"][0]["unmerged_prs"] is True


def test_pr_mapping_preflight_prefers_canonical_marker_when_present(monkeypatch, tmp_path: Path) -> None:
    config = _config(tmp_path)
    canonical = "\n".join(
        [
            "[ARESFORGE_CANONICAL_EVIDENCE_MARKER]",
            "marker_type: pr_evidence",
            "marker_state: ready",
            "required.issue: #386",
            "required.pr: #500",
            "required.branch: m24-386",
            "required.commit: abc1234",
            "required.changed_files: src/aresforge/cli.py",
            "required.validation_summary: pytest pass",
            "required.merge_status: merged",
            "required.safety_posture: read-only",
            "required.evidence_status: ready",
            "missing_required_fields: <none>",
            "invalid_reasons: <none>",
            "[/ARESFORGE_CANONICAL_EVIDENCE_MARKER]",
        ]
    )
    monkeypatch.setattr(
        pr_mapping_preflight,
        "fetch_issue_details",
        lambda _config, issue_number: {
            "ok": True,
            "issue": {"number": issue_number, "body": canonical, "comments": []},
        },
    )
    monkeypatch.setattr(
        pr_mapping_preflight,
        "inspect_milestone_state",
        lambda _config, parent_issue: {
            "ok": True,
            "parent_issue": {"issue_number": parent_issue, "state": "OPEN"},
            "child_issues": [
                {"issue_number": 386, "title": "pr mapping", "state": "OPEN", "linked_pr_count": 1, "merged_pr_count": 1}
            ],
        },
    )

    payload = pr_mapping_preflight.inspect_pr_mapping_preflight(config, parent_issue=381)

    assert payload["pr_mapping_summary"]["aggregate_state"] == "ready"
    assert payload["children"][0]["mapping_source"] == "canonical_marker"
    assert payload["children"][0]["canonical_preferred"] is True
    assert payload["children"][0]["normalized_pr_number"] == 500
