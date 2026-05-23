from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator import parent_child_linkage_preflight


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


def test_parent_child_linkage_preflight_ready(monkeypatch, tmp_path: Path) -> None:
    config = _config(tmp_path)
    monkeypatch.setattr(
        parent_child_linkage_preflight,
        "inspect_milestone_state",
        lambda _config, parent_issue: {
            "ok": True,
            "parent_issue": {"issue_number": parent_issue, "state": "OPEN", "title": "M23 parent"},
            "child_issues": [
                {
                    "issue_number": 382,
                    "state": "CLOSED",
                    "title": "contract",
                    "lineage_detected": True,
                    "lineage_sources": ["reference_classification"],
                }
            ],
        },
    )
    monkeypatch.setattr(
        parent_child_linkage_preflight,
        "fetch_issue_details",
        lambda _config, issue_number: {
            "ok": True,
            "issue": {
                "number": issue_number,
                "reference_classification": {"implementation_issue_numbers": [381]},
            },
        },
    )

    payload = parent_child_linkage_preflight.inspect_parent_child_linkage_preflight(config, parent_issue=381)

    assert payload["ok"] is True
    assert payload["read_only"] is True
    assert payload["lineage_summary"]["aggregate_state"] == "ready"
    assert payload["lineage_summary"]["closeout_ready"] is True
    assert payload["blocked_reasons"] == []


def test_parent_child_linkage_preflight_missing_lineage_is_blocked_with_guidance(
    monkeypatch,
    tmp_path: Path,
) -> None:
    config = _config(tmp_path)
    monkeypatch.setattr(
        parent_child_linkage_preflight,
        "inspect_milestone_state",
        lambda _config, parent_issue: {
            "ok": True,
            "parent_issue": {"issue_number": parent_issue, "state": "OPEN", "title": "M23 parent"},
            "child_issues": [
                {
                    "issue_number": 384,
                    "state": "OPEN",
                    "title": "linkage inspector",
                    "lineage_detected": False,
                    "lineage_sources": [],
                }
            ],
        },
    )
    monkeypatch.setattr(
        parent_child_linkage_preflight,
        "fetch_issue_details",
        lambda _config, issue_number: {
            "ok": True,
            "issue": {
                "number": issue_number,
                "reference_classification": {"implementation_issue_numbers": []},
            },
        },
    )

    payload = parent_child_linkage_preflight.inspect_parent_child_linkage_preflight(config, parent_issue=381)

    assert payload["ok"] is True
    assert payload["lineage_summary"]["aggregate_state"] == "blocked"
    assert "lineage.parent_child.384:missing" in payload["blocked_reasons"]
    assert any("Add explicit parent lineage reference" in item for item in payload["repair_guidance"])


def test_parent_child_linkage_preflight_conflicting_parent_reference_is_blocked(
    monkeypatch,
    tmp_path: Path,
) -> None:
    config = _config(tmp_path)
    monkeypatch.setattr(
        parent_child_linkage_preflight,
        "inspect_milestone_state",
        lambda _config, parent_issue: {
            "ok": True,
            "parent_issue": {"issue_number": parent_issue, "state": "OPEN", "title": "M23 parent"},
            "child_issues": [
                {
                    "issue_number": 385,
                    "state": "OPEN",
                    "title": "marker preflight",
                    "lineage_detected": True,
                    "lineage_sources": ["reference_classification"],
                }
            ],
        },
    )
    monkeypatch.setattr(
        parent_child_linkage_preflight,
        "fetch_issue_details",
        lambda _config, issue_number: {
            "ok": True,
            "issue": {
                "number": issue_number,
                "reference_classification": {"implementation_issue_numbers": [381, 999]},
            },
        },
    )

    payload = parent_child_linkage_preflight.inspect_parent_child_linkage_preflight(config, parent_issue=381)

    assert payload["ok"] is True
    assert payload["lineage_summary"]["aggregate_state"] == "blocked"
    assert "lineage.parent_child.385:conflicting" in payload["blocked_reasons"]
    assert payload["children"][0]["conflicting_parent_issues"] == [999]
