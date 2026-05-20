from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator import repo_bootstrap_contract


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


def test_inspect_repo_bootstrap_contract_summarizes_required_and_recommended_areas(
    monkeypatch,
    tmp_path: Path,
) -> None:
    config = make_config(tmp_path)
    for rel_path in (
        "docs/agents/PR_EVIDENCE_PACKAGE_TEMPLATE.md",
        "docs/agents/CLOSEOUT_EVIDENCE_PACKAGE_TEMPLATE.md",
        "docs/context/BUILD_STATE.md",
        "docs/context/AGENT_CONTEXT.md",
        "docs/roadmap/ROADMAP.md",
        "docs/operator/LOCAL_OPERATOR_USAGE.md",
        "docs/architecture/REPOSITORY_GOVERNANCE_CONTRACT.md",
        "artifacts/prompts/generated/.gitkeep",
        "artifacts/evidence/generated/.gitkeep",
        "artifacts/codex_handoffs/generated/.gitkeep",
    ):
        path = tmp_path / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("ok", encoding="utf-8")

    monkeypatch.setattr(
        repo_bootstrap_contract,
        "inspect_repo_governance",
        lambda _config: {
            "repository_slug": "yoey2112/aresforge",
            "default_branch": "main",
            "required_platform_labels": {
                "available": True,
                "missing": [],
            },
            "optional_platform_labels": {
                "available": True,
                "missing": ["aresforge-generated"],
            },
            "automation_trigger_labels": {
                "available": True,
                "missing": [],
            },
            "milestone_naming_status": {
                "available": True,
                "missing_platform_milestones": [],
                "unknown_platform_like_milestones": [],
                "project_specific_milestones": ["Product - Backlog"],
            },
            "warnings": [],
            "boundary_confirmations": [
                "Read-only governance inspection only.",
                "Issue #39 remains retired historical validation evidence and was not modified.",
            ],
        },
    )

    payload = repo_bootstrap_contract.inspect_repo_bootstrap_contract(config)

    assert payload["command"] == "inspect-repo-bootstrap-contract"
    assert payload["ok"] is True
    assert payload["summary"]["required_attention_needed"] == 0
    assert payload["summary"]["advisory"] >= 1
    assert payload["bootstrap_contract"]["required"]
    assert any(
        area["area"] == "project_specific_milestone_mapping" and area["status"] == "advisory"
        for area in payload["area_evaluation"]
    )
    assert any(
        area["area"] == "default_branch_expectations" and area["status"] == "satisfied"
        for area in payload["area_evaluation"]
    )


def test_inspect_repo_bootstrap_contract_handles_unavailable_governance_data(
    monkeypatch,
    tmp_path: Path,
) -> None:
    config = make_config(tmp_path)

    monkeypatch.setattr(
        repo_bootstrap_contract,
        "inspect_repo_governance",
        lambda _config: {
            "repository_slug": "yoey2112/aresforge",
            "default_branch": None,
            "required_platform_labels": {
                "available": False,
                "missing": [],
            },
            "optional_platform_labels": {
                "available": False,
                "missing": [],
            },
            "automation_trigger_labels": {
                "available": False,
                "missing": [],
            },
            "milestone_naming_status": {
                "available": False,
            },
            "warnings": ["gh command unavailable"],
            "boundary_confirmations": [],
        },
    )

    payload = repo_bootstrap_contract.inspect_repo_bootstrap_contract(config)

    assert payload["ok"] is True
    assert payload["summary"]["unavailable"] >= 3
    assert payload["summary"]["required_attention_needed"] >= 1
    assert "Address attention-needed required bootstrap areas first" in payload["recommended_next_action"]
