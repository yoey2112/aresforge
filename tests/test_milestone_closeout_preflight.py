from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator import milestone_closeout_preflight


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


def test_inspect_milestone_closeout_preflight_ready(monkeypatch, tmp_path: Path) -> None:
    config = _config(tmp_path)
    monkeypatch.setattr(
        milestone_closeout_preflight,
        "inspect_parent_child_linkage_preflight",
        lambda _config, parent_issue: {
            "ok": True,
            "lineage_summary": {"aggregate_state": "ready", "closeout_ready": True},
            "blocked_reasons": [],
            "warning_reasons": [],
            "unknown_reasons": [],
        },
    )
    monkeypatch.setattr(
        milestone_closeout_preflight,
        "inspect_child_evidence_marker_preflight",
        lambda _config, parent_issue: {
            "ok": True,
            "evidence_summary": {"aggregate_state": "ready", "closeout_ready": True},
            "blocked_reasons": [],
            "warning_reasons": [],
            "unknown_reasons": [],
        },
    )
    monkeypatch.setattr(
        milestone_closeout_preflight,
        "inspect_pr_mapping_preflight",
        lambda _config, parent_issue: {
            "ok": True,
            "pr_mapping_summary": {"aggregate_state": "ready", "closeout_ready": True},
            "blocked_reasons": [],
            "warning_reasons": [],
            "unknown_reasons": [],
        },
    )
    monkeypatch.setattr(
        milestone_closeout_preflight,
        "generate_closeout_preflight_repair_guidance",
        lambda _config, parent_issue: {
            "ok": True,
            "guidance": {
                "parent_repair": [],
                "child_repair": [],
                "pr_mapping_repair": [],
                "evidence_marker_repair": [],
            },
        },
    )

    payload = milestone_closeout_preflight.inspect_milestone_closeout_preflight(config, parent_issue=381)

    assert payload["ok"] is True
    assert payload["read_only"] is True
    assert payload["closeout_preflight"]["aggregate_state"] == "ready"
    assert payload["closeout_preflight"]["closeout_ready"] is True
    assert payload["blocked_reasons"] == []


def test_inspect_milestone_closeout_preflight_blocked(monkeypatch, tmp_path: Path) -> None:
    config = _config(tmp_path)
    monkeypatch.setattr(
        milestone_closeout_preflight,
        "inspect_parent_child_linkage_preflight",
        lambda _config, parent_issue: {
            "ok": True,
            "lineage_summary": {"aggregate_state": "blocked", "closeout_ready": False},
            "blocked_reasons": ["lineage.parent_child.388:missing"],
            "warning_reasons": [],
            "unknown_reasons": [],
        },
    )
    monkeypatch.setattr(
        milestone_closeout_preflight,
        "inspect_child_evidence_marker_preflight",
        lambda _config, parent_issue: {
            "ok": True,
            "evidence_summary": {"aggregate_state": "warning", "closeout_ready": False},
            "blocked_reasons": [],
            "warning_reasons": ["evidence.child_marker.388:incomplete"],
            "unknown_reasons": [],
        },
    )
    monkeypatch.setattr(
        milestone_closeout_preflight,
        "inspect_pr_mapping_preflight",
        lambda _config, parent_issue: {
            "ok": True,
            "pr_mapping_summary": {"aggregate_state": "blocked", "closeout_ready": False},
            "blocked_reasons": ["pr.mapping.388:missing"],
            "warning_reasons": [],
            "unknown_reasons": [],
        },
    )
    monkeypatch.setattr(
        milestone_closeout_preflight,
        "generate_closeout_preflight_repair_guidance",
        lambda _config, parent_issue: {
            "ok": True,
            "guidance": {
                "parent_repair": ["fix-parent"],
                "child_repair": ["fix-child"],
                "pr_mapping_repair": ["fix-pr"],
                "evidence_marker_repair": ["fix-marker"],
            },
        },
    )

    payload = milestone_closeout_preflight.inspect_milestone_closeout_preflight(config, parent_issue=381)

    assert payload["ok"] is True
    assert payload["closeout_preflight"]["aggregate_state"] == "blocked"
    assert payload["closeout_preflight"]["closeout_ready"] is False
    assert "lineage.parent_child.388:missing" in payload["blocked_reasons"]
    assert "evidence.child_marker.388:incomplete" in payload["warning_reasons"]
    assert "fix-pr" in payload["repair_guidance"]
