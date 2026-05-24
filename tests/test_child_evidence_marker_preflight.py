from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator import child_evidence_marker_preflight


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


def test_child_evidence_marker_preflight_complete(monkeypatch, tmp_path: Path) -> None:
    config = _config(tmp_path)
    monkeypatch.setattr(
        child_evidence_marker_preflight,
        "inspect_milestone_state",
        lambda _config, parent_issue: {
            "ok": True,
            "parent_issue": {"issue_number": parent_issue, "state": "OPEN"},
            "child_issues": [{"issue_number": 385, "title": "evidence", "state": "OPEN"}],
        },
    )
    monkeypatch.setattr(
        child_evidence_marker_preflight,
        "fetch_issue_details",
        lambda _config, issue_number: {
            "ok": True,
            "issue": {
                "number": issue_number,
                "body": "Evidence\nBranch: feature/m23\nCommit: abcdef1234567\nPR: #393\nValidation: python -m pytest\nSafety notes: read-only no mutation",
                "comments": [],
            },
        },
    )

    payload = child_evidence_marker_preflight.inspect_child_evidence_marker_preflight(config, parent_issue=381)

    assert payload["ok"] is True
    assert payload["read_only"] is True
    assert payload["evidence_summary"]["aggregate_state"] == "ready"
    assert payload["evidence_summary"]["closeout_ready"] is True
    assert payload["children"][0]["missing_fields"] == []


def test_child_evidence_marker_preflight_missing(monkeypatch, tmp_path: Path) -> None:
    config = _config(tmp_path)
    monkeypatch.setattr(
        child_evidence_marker_preflight,
        "inspect_milestone_state",
        lambda _config, parent_issue: {
            "ok": True,
            "parent_issue": {"issue_number": parent_issue, "state": "OPEN"},
            "child_issues": [{"issue_number": 385, "title": "evidence", "state": "OPEN"}],
        },
    )
    monkeypatch.setattr(
        child_evidence_marker_preflight,
        "fetch_issue_details",
        lambda _config, issue_number: {
            "ok": True,
            "issue": {
                "number": issue_number,
                "body": "No markers",
                "comments": [],
            },
        },
    )

    payload = child_evidence_marker_preflight.inspect_child_evidence_marker_preflight(config, parent_issue=381)

    assert payload["ok"] is True
    assert payload["evidence_summary"]["aggregate_state"] == "blocked"
    assert "evidence.child_marker.385:missing" in payload["blocked_reasons"]
    assert any("Add child evidence marker block" in item for item in payload["repair_guidance"])


def test_child_evidence_marker_preflight_incomplete(monkeypatch, tmp_path: Path) -> None:
    config = _config(tmp_path)
    monkeypatch.setattr(
        child_evidence_marker_preflight,
        "inspect_milestone_state",
        lambda _config, parent_issue: {
            "ok": True,
            "parent_issue": {"issue_number": parent_issue, "state": "OPEN"},
            "child_issues": [{"issue_number": 385, "title": "evidence", "state": "OPEN"}],
        },
    )
    monkeypatch.setattr(
        child_evidence_marker_preflight,
        "fetch_issue_details",
        lambda _config, issue_number: {
            "ok": True,
            "issue": {
                "number": issue_number,
                "body": "Evidence\nBranch: feature/m23\nPR: #393",
                "comments": [],
            },
        },
    )

    payload = child_evidence_marker_preflight.inspect_child_evidence_marker_preflight(config, parent_issue=381)

    assert payload["ok"] is True
    assert payload["evidence_summary"]["aggregate_state"] == "warning"
    assert "evidence.child_marker.385:incomplete" in payload["warning_reasons"]
    assert set(payload["children"][0]["missing_fields"]) == {"commit", "safety_notes", "validation"}


def test_child_evidence_marker_preflight_prefers_canonical_marker_when_present(
    monkeypatch,
    tmp_path: Path,
) -> None:
    config = _config(tmp_path)
    canonical = "\n".join(
        [
            "[ARESFORGE_CANONICAL_EVIDENCE_MARKER]",
            "marker_type: child_evidence",
            "marker_state: ready",
            "required.parent_issue: #381",
            "required.child_issue: #385",
            "required.branch: m24-385",
            "required.commit: abc1234",
            "required.pr: #393",
            "required.validation_summary: pytest pass",
            "required.safety_notes: read-only",
            "missing_required_fields: <none>",
            "invalid_reasons: <none>",
            "[/ARESFORGE_CANONICAL_EVIDENCE_MARKER]",
        ]
    )
    monkeypatch.setattr(
        child_evidence_marker_preflight,
        "inspect_milestone_state",
        lambda _config, parent_issue: {
            "ok": True,
            "parent_issue": {"issue_number": parent_issue, "state": "OPEN"},
            "child_issues": [{"issue_number": 385, "title": "evidence", "state": "OPEN"}],
        },
    )
    monkeypatch.setattr(
        child_evidence_marker_preflight,
        "fetch_issue_details",
        lambda _config, issue_number: {
            "ok": True,
            "issue": {"number": issue_number, "body": canonical, "comments": []},
        },
    )

    payload = child_evidence_marker_preflight.inspect_child_evidence_marker_preflight(config, parent_issue=381)

    assert payload["evidence_summary"]["aggregate_state"] == "ready"
    assert payload["children"][0]["marker_source"] == "canonical_marker"
