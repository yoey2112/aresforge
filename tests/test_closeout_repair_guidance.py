from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator import closeout_repair_guidance


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


def test_generate_closeout_preflight_repair_guidance_sections_and_read_only(
    monkeypatch,
    tmp_path: Path,
) -> None:
    config = _config(tmp_path)
    monkeypatch.setattr(
        closeout_repair_guidance,
        "inspect_parent_child_linkage_preflight",
        lambda _config, parent_issue: {
            "ok": True,
            "blocked_reasons": ["lineage.parent_child.387:missing"],
        },
    )
    monkeypatch.setattr(
        closeout_repair_guidance,
        "inspect_child_evidence_marker_preflight",
        lambda _config, parent_issue: {
            "ok": True,
            "blocked_reasons": ["evidence.child_marker.387:missing"],
            "warning_reasons": [],
            "children": [
                {"issue_number": 387, "missing_fields": ["branch", "commit", "pr", "validation", "safety_notes"]}
            ],
        },
    )
    monkeypatch.setattr(
        closeout_repair_guidance,
        "inspect_pr_mapping_preflight",
        lambda _config, parent_issue: {
            "ok": True,
            "blocked_reasons": ["pr.mapping.387:missing"],
            "warning_reasons": [],
        },
    )

    payload = closeout_repair_guidance.generate_closeout_preflight_repair_guidance(
        config,
        parent_issue=381,
    )

    assert payload["ok"] is True
    assert payload["read_only"] is True
    assert payload["mutation_executed"] is False
    assert "parent_repair" in payload["guidance"]
    assert "child_repair" in payload["guidance"]
    assert "pr_mapping_repair" in payload["guidance"]
    assert "evidence_marker_repair" in payload["guidance"]
    assert "canonical_marker_repair" in payload["guidance"]


def test_generate_closeout_preflight_repair_guidance_is_copy_paste_safe_text(
    monkeypatch,
    tmp_path: Path,
) -> None:
    config = _config(tmp_path)
    monkeypatch.setattr(
        closeout_repair_guidance,
        "inspect_parent_child_linkage_preflight",
        lambda _config, parent_issue: {"ok": True, "blocked_reasons": []},
    )
    monkeypatch.setattr(
        closeout_repair_guidance,
        "inspect_child_evidence_marker_preflight",
        lambda _config, parent_issue: {"ok": True, "blocked_reasons": [], "warning_reasons": [], "children": []},
    )
    monkeypatch.setattr(
        closeout_repair_guidance,
        "inspect_pr_mapping_preflight",
        lambda _config, parent_issue: {"ok": True, "blocked_reasons": [], "warning_reasons": []},
    )

    payload = closeout_repair_guidance.generate_closeout_preflight_repair_guidance(
        config,
        parent_issue=381,
    )
    text = payload["guidance_text"]

    assert "```" not in text
    assert "PowerShell example" in text
    assert "Generate canonical child marker templates" in text
    assert "guidance only, no mutation executed" in text


def test_generate_closeout_preflight_repair_guidance_handles_dependency_failures(
    monkeypatch,
    tmp_path: Path,
) -> None:
    config = _config(tmp_path)
    monkeypatch.setattr(
        closeout_repair_guidance,
        "inspect_parent_child_linkage_preflight",
        lambda _config, parent_issue: {"ok": False, "error": "gh_cli_failed"},
    )
    monkeypatch.setattr(
        closeout_repair_guidance,
        "inspect_child_evidence_marker_preflight",
        lambda _config, parent_issue: {"ok": True},
    )
    monkeypatch.setattr(
        closeout_repair_guidance,
        "inspect_pr_mapping_preflight",
        lambda _config, parent_issue: {"ok": True},
    )

    payload = closeout_repair_guidance.generate_closeout_preflight_repair_guidance(
        config,
        parent_issue=381,
    )

    assert payload["ok"] is False
    assert payload["error"] == "repair_guidance_dependency_failed"
    assert payload["failures"][0]["command"] == "inspect-parent-child-linkage-preflight"
