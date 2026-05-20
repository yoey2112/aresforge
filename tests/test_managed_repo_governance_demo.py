from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator import managed_repo_governance_demo


def make_config(tmp_path: Path) -> AppConfig:
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


def test_demo_managed_repo_governance_includes_end_to_end_sections(monkeypatch, tmp_path: Path) -> None:
    config = make_config(tmp_path)
    monkeypatch.setattr(
        managed_repo_governance_demo,
        "inspect_repo_governance",
        lambda _cfg: {
            "warnings": [],
            "required_platform_labels": {"available": True, "missing": []},
            "automation_trigger_labels": {"available": True, "missing": ["aresforge-automerge"]},
            "milestone_naming_status": {"available": True, "missing_platform_milestones": []},
        },
    )
    monkeypatch.setattr(
        managed_repo_governance_demo,
        "inspect_repo_bootstrap_contract",
        lambda _cfg: {"summary": {"required_attention_needed": 1, "unavailable": 0, "deferred": 1}, "warnings": []},
    )
    monkeypatch.setattr(
        managed_repo_governance_demo,
        "inspect_managed_repos",
        lambda _cfg: {"managed_repository_count": 2, "warnings": []},
    )
    monkeypatch.setattr(
        managed_repo_governance_demo,
        "managed_repo_readiness_report",
        lambda _cfg: {
            "repository_count": 2,
            "repositories": [
                {"repository_slug": "yoey2112/aresforge", "readiness_level": "attention_needed"},
                {
                    "repository_slug": "yoey2112/aresforge-demo-managed-repo",
                    "readiness_level": "degraded",
                },
            ],
            "warnings": [],
        },
    )
    monkeypatch.setattr(
        managed_repo_governance_demo,
        "plan_repo_bootstrap",
        lambda _cfg: {
            "repositories": [{"actions": [{"category": "required", "title": "Create aresforge-automerge"}]}],
            "warnings": [],
        },
    )

    payload = managed_repo_governance_demo.demo_managed_repo_governance(config)

    assert payload["command"] == "demo-managed-repo-governance"
    assert payload["ok"] is True
    assert payload["demo_steps"]
    assert {step["step_id"] for step in payload["demo_steps"]} == {
        "governance_inspection",
        "bootstrap_contract_evaluation",
        "registry_representation",
        "readiness_report",
        "bootstrap_plan",
        "qa_validation_expectations",
        "documentation_expectations",
    }
    assert payload["demo_summary"]["attention_needed_steps"] >= 1
    assert payload["demo_summary"]["repository_count"] == 2
    assert "governance_inspection" in payload
    assert "bootstrap_contract_evaluation" in payload
    assert "registry_representation" in payload
    assert "readiness_report" in payload
    assert "bootstrap_plan" in payload
    assert payload["boundary_confirmations"]


def test_demo_managed_repo_governance_degrades_gracefully_and_preserves_warnings(
    monkeypatch, tmp_path: Path
) -> None:
    config = make_config(tmp_path)
    monkeypatch.setattr(
        managed_repo_governance_demo,
        "inspect_repo_governance",
        lambda _cfg: {
            "warnings": ["gh command unavailable"],
            "required_platform_labels": {"available": False, "missing": []},
            "automation_trigger_labels": {"available": False, "missing": []},
            "milestone_naming_status": {"available": False},
        },
    )
    monkeypatch.setattr(
        managed_repo_governance_demo,
        "inspect_repo_bootstrap_contract",
        lambda _cfg: {"summary": {"required_attention_needed": 0, "unavailable": 2, "deferred": 0}, "warnings": []},
    )
    monkeypatch.setattr(
        managed_repo_governance_demo,
        "inspect_managed_repos",
        lambda _cfg: {"managed_repository_count": 1, "warnings": ["registry warning"]},
    )
    monkeypatch.setattr(
        managed_repo_governance_demo,
        "managed_repo_readiness_report",
        lambda _cfg: {"repositories": [{"readiness_level": "unavailable"}], "warnings": []},
    )
    monkeypatch.setattr(
        managed_repo_governance_demo,
        "plan_repo_bootstrap",
        lambda _cfg: {"repositories": [], "warnings": ["plan warning"]},
    )

    payload = managed_repo_governance_demo.demo_managed_repo_governance(config)
    step_status = {step["step_id"]: step["status"] for step in payload["demo_steps"]}

    assert "gh command unavailable" in payload["warnings"]
    assert "registry warning" in payload["warnings"]
    assert "plan warning" in payload["warnings"]
    assert step_status["governance_inspection"] == "attention_needed"
    assert step_status["readiness_report"] == "attention_needed"
    assert step_status["bootstrap_plan"] == "attention_needed"
    assert "Review attention-needed steps" in payload["recommended_next_action"]
