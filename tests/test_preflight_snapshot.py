import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.preflight_snapshot import (
    diff_preflight_snapshots,
    generate_preflight_baseline_snapshot,
)


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


def test_generate_preflight_baseline_snapshot_writes_file(monkeypatch, tmp_path: Path) -> None:
    config = _config(tmp_path)
    monkeypatch.setattr(
        "aresforge.operator.preflight_snapshot.inspect_milestone_state",
        lambda _config, parent_issue: {
            "ok": True,
            "summary": {"state_summary": "ready", "child_issue_count": 10},
        },
    )
    monkeypatch.setattr(
        "aresforge.operator.preflight_snapshot.inspect_child_evidence_marker_preflight",
        lambda _config, parent_issue: {
            "ok": True,
            "evidence_summary": {"aggregate_state": "ready"},
        },
    )
    monkeypatch.setattr(
        "aresforge.operator.preflight_snapshot.inspect_pr_mapping_preflight",
        lambda _config, parent_issue: {
            "ok": True,
            "pr_mapping_summary": {"aggregate_state": "ready"},
        },
    )
    monkeypatch.setattr(
        "aresforge.operator.preflight_snapshot.inspect_parent_closeout_readiness",
        lambda _config, parent_issue: {
            "ok": True,
            "closeout_readiness": {"parent_closeout_ready": True},
        },
    )
    monkeypatch.setattr(
        "aresforge.operator.preflight_snapshot.inspect_milestone_closeout_preflight",
        lambda _config, parent_issue: {
            "ok": True,
            "closeout_preflight": {"aggregate_state": "ready", "closeout_ready": True},
            "blocked_reasons": [],
            "warning_reasons": [],
            "unknown_reasons": [],
        },
    )

    output = tmp_path / "snapshot.json"
    payload = generate_preflight_baseline_snapshot(
        config,
        parent_issue=400,
        output_path=str(output),
    )

    assert payload["ok"] is True
    assert payload["snapshot_path"] == str(output)
    assert output.exists()
    snapshot = json.loads(output.read_text(encoding="utf-8"))
    assert snapshot["schema_version"] == "m24.v1"
    assert snapshot["parent_issue"] == 400
    assert snapshot["closeout_preflight_state"] == "ready"


def test_diff_preflight_snapshots_no_change(tmp_path: Path) -> None:
    before = tmp_path / "before.json"
    after = tmp_path / "after.json"
    payload = {
        "schema_version": "m24.v1",
        "lineage_state": "ready",
        "child_evidence_state": "ready",
        "pr_mapping_state": "ready",
        "readiness_state": "ready",
        "closeout_preflight_state": "ready",
        "blocked_reasons": [],
        "warning_reasons": [],
        "unknown_reasons": [],
    }
    before.write_text(json.dumps(payload), encoding="utf-8")
    after.write_text(json.dumps(payload), encoding="utf-8")

    diff = diff_preflight_snapshots(before_path=str(before), after_path=str(after))

    assert diff["ok"] is True
    assert diff["classification"] == "no-change"


def test_diff_preflight_snapshots_improved(tmp_path: Path) -> None:
    before = tmp_path / "before.json"
    after = tmp_path / "after.json"
    before.write_text(
        json.dumps(
            {
                "schema_version": "m24.v1",
                "lineage_state": "blocked",
                "child_evidence_state": "warning",
                "pr_mapping_state": "blocked",
                "readiness_state": "blocked",
                "closeout_preflight_state": "warning",
                "blocked_reasons": ["a", "b"],
                "warning_reasons": ["c"],
                "unknown_reasons": ["d"],
            }
        ),
        encoding="utf-8",
    )
    after.write_text(
        json.dumps(
            {
                "schema_version": "m24.v1",
                "lineage_state": "ready",
                "child_evidence_state": "ready",
                "pr_mapping_state": "ready",
                "readiness_state": "ready",
                "closeout_preflight_state": "ready",
                "blocked_reasons": [],
                "warning_reasons": [],
                "unknown_reasons": [],
            }
        ),
        encoding="utf-8",
    )

    diff = diff_preflight_snapshots(before_path=str(before), after_path=str(after))

    assert diff["ok"] is True
    assert diff["classification"] == "improved"


def test_diff_preflight_snapshots_regressed(tmp_path: Path) -> None:
    before = tmp_path / "before.json"
    after = tmp_path / "after.json"
    before.write_text(
        json.dumps(
            {
                "schema_version": "m24.v1",
                "lineage_state": "ready",
                "child_evidence_state": "ready",
                "pr_mapping_state": "ready",
                "readiness_state": "ready",
                "closeout_preflight_state": "ready",
                "blocked_reasons": [],
                "warning_reasons": [],
                "unknown_reasons": [],
            }
        ),
        encoding="utf-8",
    )
    after.write_text(
        json.dumps(
            {
                "schema_version": "m24.v1",
                "lineage_state": "blocked",
                "child_evidence_state": "warning",
                "pr_mapping_state": "blocked",
                "readiness_state": "blocked",
                "closeout_preflight_state": "blocked",
                "blocked_reasons": ["a"],
                "warning_reasons": ["b"],
                "unknown_reasons": ["c"],
            }
        ),
        encoding="utf-8",
    )

    diff = diff_preflight_snapshots(before_path=str(before), after_path=str(after))

    assert diff["ok"] is True
    assert diff["classification"] == "regressed"


def test_diff_preflight_snapshots_mixed(tmp_path: Path) -> None:
    before = tmp_path / "before.json"
    after = tmp_path / "after.json"
    before.write_text(
        json.dumps(
            {
                "schema_version": "m24.v1",
                "lineage_state": "blocked",
                "child_evidence_state": "ready",
                "pr_mapping_state": "warning",
                "readiness_state": "blocked",
                "closeout_preflight_state": "warning",
                "blocked_reasons": ["a"],
                "warning_reasons": [],
                "unknown_reasons": [],
            }
        ),
        encoding="utf-8",
    )
    after.write_text(
        json.dumps(
            {
                "schema_version": "m24.v1",
                "lineage_state": "ready",
                "child_evidence_state": "blocked",
                "pr_mapping_state": "ready",
                "readiness_state": "blocked",
                "closeout_preflight_state": "warning",
                "blocked_reasons": ["a", "b"],
                "warning_reasons": [],
                "unknown_reasons": [],
            }
        ),
        encoding="utf-8",
    )

    diff = diff_preflight_snapshots(before_path=str(before), after_path=str(after))

    assert diff["ok"] is True
    assert diff["classification"] == "mixed"
