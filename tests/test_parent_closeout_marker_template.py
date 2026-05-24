from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.parent_closeout_marker_template import generate_parent_closeout_marker_template


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


def test_generate_parent_closeout_marker_template_ready(
    monkeypatch,
    tmp_path: Path,
) -> None:
    config = _config(tmp_path)
    monkeypatch.setattr(
        "aresforge.operator.parent_closeout_marker_template.inspect_milestone_state",
        lambda _config, parent_issue, state_file=None: {
            "ok": True,
            "child_issues": [
                {"issue_number": 401},
                {"issue_number": 402},
            ],
        },
    )
    monkeypatch.setattr(
        "aresforge.operator.parent_closeout_marker_template.inspect_pr_mapping_preflight",
        lambda _config, parent_issue: {
            "ok": True,
            "children": [
                {"issue_number": 401, "normalized_pr_number": 411},
                {"issue_number": 402, "normalized_pr_number": 412},
            ],
        },
    )
    monkeypatch.setattr(
        "aresforge.operator.parent_closeout_marker_template.inspect_parent_closeout_readiness",
        lambda _config, parent_issue, state_file=None: {
            "ok": True,
            "closeout_readiness": {"parent_closeout_ready": True},
            "blocked_reasons": [],
            "warnings": [],
        },
    )

    payload = generate_parent_closeout_marker_template(config, parent_issue=400)

    assert payload["ok"] is True
    assert payload["read_only"] is True
    assert payload["parent_closeout_ready"] is True
    assert payload["canonical_marker"]["marker_type"] == "parent_closeout_evidence"
    assert payload["canonical_marker"]["marker_state"] == "ready"
    assert payload["canonical_marker"]["missing_required_fields"] == []
    assert "required.parent_issue: #400" in payload["canonical_marker_text"]
    assert "required.child_issue_list: #401, #402" in payload["canonical_marker_text"]
    assert "required.child_to_pr_mapping: #401->#411, #402->#412" in payload["canonical_marker_text"]
    assert "```" not in payload["canonical_marker_text"]


def test_generate_parent_closeout_marker_template_blocked_incomplete(
    monkeypatch,
    tmp_path: Path,
) -> None:
    config = _config(tmp_path)
    monkeypatch.setattr(
        "aresforge.operator.parent_closeout_marker_template.inspect_milestone_state",
        lambda _config, parent_issue, state_file=None: {
            "ok": True,
            "child_issues": [
                {"issue_number": 401},
                {"issue_number": 402},
            ],
        },
    )
    monkeypatch.setattr(
        "aresforge.operator.parent_closeout_marker_template.inspect_pr_mapping_preflight",
        lambda _config, parent_issue: {
            "ok": True,
            "children": [
                {"issue_number": 401, "normalized_pr_number": 411},
                {"issue_number": 402, "normalized_pr_number": None},
            ],
        },
    )
    monkeypatch.setattr(
        "aresforge.operator.parent_closeout_marker_template.inspect_parent_closeout_readiness",
        lambda _config, parent_issue, state_file=None: {
            "ok": True,
            "closeout_readiness": {"parent_closeout_ready": False},
            "blocked_reasons": ["one_or_more_children_not_closed_or_accounted_for"],
            "warnings": ["missing_milestone_assignment"],
        },
    )

    payload = generate_parent_closeout_marker_template(config, parent_issue=400)

    assert payload["ok"] is True
    assert payload["parent_closeout_ready"] is False
    assert payload["canonical_marker"]["marker_state"] == "incomplete"
    assert "final_main_head" in payload["canonical_marker"]["missing_required_fields"]
    assert "final_validation_results" in payload["canonical_marker"]["missing_required_fields"]
    assert payload["canonical_marker"]["required_fields"]["closeout_readiness_state"] == "blocked"
