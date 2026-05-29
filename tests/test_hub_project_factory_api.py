from __future__ import annotations

from pathlib import Path

from aresforge.config import AppConfig
from aresforge.hub.api import (
    get_project_factory_architecture_contract,
    get_project_factory_agent_dispatch_plan,
    get_project_factory_documentation_closeout_plan,
    get_project_factory_execution_phase_approval,
    get_project_factory_execution_readiness,
    get_project_factory_validation_execution_plan,
    get_project_factory_github_apply_plan,
    get_project_factory_milestone_issue_plan,
    get_project_factory_scope_package,
    get_project_ai_settings,
    patch_project_factory_architecture_contract,
    patch_project_factory_agent_dispatch_plan,
    patch_project_factory_documentation_closeout_plan,
    patch_project_factory_execution_phase_approval,
    patch_project_factory_validation_execution_plan,
    patch_project_factory_github_apply_plan,
    patch_project_factory_milestone_issue_plan,
    patch_project_factory_scope_package,
    get_project_factory_dossier,
    post_active_project,
    post_project_factory_architecture_contract,
    post_project_factory_github_apply_plan,
    post_project_factory_github_apply_plan_approve,
    post_project_factory_agent_dispatch_plan,
    post_project_factory_agent_dispatch_plan_approve,
    post_project_factory_documentation_closeout_plan,
    post_project_factory_documentation_closeout_plan_approve,
    post_project_factory_execution_phase_approval,
    post_project_factory_execution_phase_approval_approve,
    post_project_factory_validation_execution_plan,
    post_project_factory_validation_execution_plan_approve,
    post_project_factory_architecture_contract_approve,
    post_project_factory_milestone_issue_plan,
    post_project_factory_milestone_issue_plan_approve,
    post_project_factory_new_project,
    post_project_factory_scope_package_approve,
    post_project_factory_scope_package,
    post_project_ai_settings,
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
        github_owner="local",
        github_repo="aresforge",
    )


def test_post_project_factory_new_project_returns_expected_payload(tmp_path: Path) -> None:
    config = _config(tmp_path)
    payload = post_project_factory_new_project(
        config,
        {
            "name": "Hub Wizard Project",
            "project_id": "",
            "description": "Local-only wizard bootstrapping",
            "project_type": "automation",
            "preferred_stack": "python",
            "root_path": str(tmp_path / "workspace"),
            "github_owner": "example",
            "github_repo": "hub-wizard-project",
            "github_mode": "create-with-approval-later",
            "default_branch": "main",
            "initial_requirements": "Prepare scope and architecture",
            "tags": "wizard,project-factory",
        },
    )

    assert payload["ok"] is True
    assert payload["local_only"] is True
    assert payload["project"]["project_id"] == "hub-wizard-project"
    assert payload["repo"]["repo_id"] == "hub-wizard-project-primary"
    assert payload["active_project_id"] == "hub-wizard-project"
    assert payload["scope_queue_item"]["source"] == "hub-new-project-wizard"
    assert payload["dossier"]["project_type"] == "automation"
    assert payload["dossier"]["github_mode"] == "create-with-approval-later"
    assert payload["dossier_path"]
    assert payload["boundary_confirmations"]


def test_post_project_factory_new_project_errors_for_invalid_payload(tmp_path: Path) -> None:
    config = _config(tmp_path)
    missing_name = post_project_factory_new_project(
        config,
        {
            "name": " ",
            "root_path": str(tmp_path / "workspace"),
        },
    )
    assert missing_name["ok"] is False
    assert missing_name["error"] == "invalid_project_factory_payload"

    invalid_type = post_project_factory_new_project(
        config,
        {
            "name": "x",
            "root_path": str(tmp_path / "workspace"),
            "project_type": "bad-type",
        },
    )
    assert invalid_type["ok"] is False
    assert invalid_type["error"] == "invalid_project_type"


def test_get_project_factory_dossier_without_project_id_uses_active_project(tmp_path: Path) -> None:
    config = _config(tmp_path)
    created = post_project_factory_new_project(
        config,
        {
            "name": "Dossier Project",
            "root_path": str(tmp_path / "workspace"),
        },
    )
    assert created["ok"] is True

    payload = get_project_factory_dossier(config, {})
    assert payload["ok"] is True
    assert payload["dossier_exists"] is True
    assert payload["project_id"] == created["active_project_id"]


def test_get_project_factory_dossier_missing_state_is_friendly(tmp_path: Path) -> None:
    config = _config(tmp_path)
    payload = get_project_factory_dossier(config, {})
    assert payload["ok"] is True
    assert payload["dossier_exists"] is False
    assert payload["warnings"]


def test_project_ai_settings_api_reads_default_and_updates_contract(tmp_path: Path) -> None:
    config = _config(tmp_path)
    created = post_project_factory_new_project(
        config,
        {
            "name": "AI Settings API",
            "root_path": str(tmp_path / "workspace"),
        },
    )
    project_id = str(created["active_project_id"])

    default_payload = get_project_ai_settings(config, project_id)
    assert default_payload["ok"] is True
    assert default_payload["settings_exists"] is False
    assert default_payload["project_ai_settings"]["project_ai_mode"] == "balanced"
    assert default_payload["validation"]["valid"] is True

    updated = post_project_ai_settings(
        config,
        project_id,
        {
            "project_ai_mode": "codex_only",
            "available_engines": ["codex_cli"],
            "disabled_engines": ["local_reasoning_llm", "local_coding_llm"],
            "default_engine": "codex_cli",
            "operator_override_allowed": True,
            "notes": "Codex-only preference contract.",
        },
    )
    assert updated["ok"] is True
    assert updated["project_ai_settings"]["project_ai_mode"] == "codex_only"
    assert updated["project_ai_settings"]["default_engine"] == "codex_cli"
    assert updated["next_safe_action"] == "use_settings_for_future_advisory_routing_contract_only"


def test_project_ai_settings_api_rejects_invalid_inputs(tmp_path: Path) -> None:
    config = _config(tmp_path)
    created = post_project_factory_new_project(
        config,
        {
            "name": "AI Settings Invalid API",
            "root_path": str(tmp_path / "workspace"),
        },
    )
    project_id = str(created["active_project_id"])

    invalid_mode = post_project_ai_settings(config, project_id, {"project_ai_mode": "bad-mode"})
    assert invalid_mode["ok"] is False
    assert invalid_mode["error"] == "invalid_project_ai_mode"

    invalid_engine = post_project_ai_settings(
        config,
        project_id,
        {"available_engines": ["local_coding_llm", "bad_engine"]},
    )
    assert invalid_engine["ok"] is False
    assert invalid_engine["error"] == "invalid_available_engines"

    invalid_bool = post_project_ai_settings(config, project_id, {"operator_override_allowed": "yes"})
    assert invalid_bool["ok"] is False
    assert invalid_bool["error"] == "invalid_operator_override_allowed"

    invalid_cross_field = post_project_ai_settings(
        config,
        project_id,
        {"project_ai_mode": "local_only", "default_engine": "codex_cli"},
    )
    assert invalid_cross_field["ok"] is False
    assert invalid_cross_field["error"] == "project_ai_settings_validation_failed"
    assert invalid_cross_field["_status"] == 400


def test_project_ai_settings_api_returns_404_for_missing_project(tmp_path: Path) -> None:
    config = _config(tmp_path)
    payload = get_project_ai_settings(config, "missing-project")
    assert payload["ok"] is False
    assert payload["_status"] == 404


def test_post_project_factory_scope_package_prepares_for_active_project(tmp_path: Path) -> None:
    config = _config(tmp_path)
    created = post_project_factory_new_project(
        config,
        {
            "name": "Scope API Project",
            "root_path": str(tmp_path / "workspace"),
        },
    )
    assert created["ok"] is True

    payload = post_project_factory_scope_package(config, {})
    assert payload["ok"] is True
    assert payload["project_id"] == created["active_project_id"]
    assert payload["scope_package"]["lifecycle_state"] == "scope_package_prepared"


def test_post_project_factory_scope_package_returns_400_with_no_active_project(tmp_path: Path) -> None:
    config = _config(tmp_path)
    payload = post_project_factory_scope_package(config, {})
    assert payload["ok"] is False
    assert payload["_status"] == 400


def test_post_project_factory_scope_package_returns_404_for_missing_dossier(tmp_path: Path) -> None:
    config = _config(tmp_path)
    seed = post_project_factory_new_project(
        config,
        {
            "name": "Seed Project",
            "project_id": "seed-project",
            "root_path": str(tmp_path / "seed-workspace"),
        },
    )
    assert seed["ok"] is True
    post_active_project(config, {"project_id": "seed-project"})

    payload = post_project_factory_scope_package(config, {"project_id": "missing-project"})
    assert payload["ok"] is False
    assert payload["_status"] == 404


def test_get_scope_package_falls_back_to_active_project(tmp_path: Path) -> None:
    config = _config(tmp_path)
    created = post_project_factory_new_project(config, {"name": "Scope Read", "root_path": str(tmp_path / "workspace")})
    assert created["ok"] is True
    post_project_factory_scope_package(config, {})
    payload = get_project_factory_scope_package(config, {})
    assert payload["ok"] is True
    assert payload["scope_package_exists"] is True
    assert payload["project_id"] == created["active_project_id"]


def test_get_scope_package_with_no_active_project_returns_friendly_state(tmp_path: Path) -> None:
    config = _config(tmp_path)
    payload = get_project_factory_scope_package(config, {})
    assert payload["ok"] is True
    assert payload["scope_package_exists"] is False
    assert payload["warnings"]


def test_patch_scope_package_updates_scope(tmp_path: Path) -> None:
    config = _config(tmp_path)
    post_project_factory_new_project(config, {"name": "Scope Patch", "root_path": str(tmp_path / "workspace")})
    post_project_factory_scope_package(config, {})
    payload = patch_project_factory_scope_package(
        config,
        {"requirements": ["r1"], "acceptance_criteria": ["a1"], "notes": "n1"},
    )
    assert payload["ok"] is True
    assert payload["scope_package"]["requirements"] == ["r1"]
    assert payload["scope_package"]["lifecycle_state"] == "scope_draft_updated"


def test_post_scope_approve_validates_required_fields(tmp_path: Path) -> None:
    config = _config(tmp_path)
    post_project_factory_new_project(config, {"name": "Scope Approve", "root_path": str(tmp_path / "workspace")})
    post_project_factory_scope_package(config, {})
    payload = post_project_factory_scope_package_approve(config, {})
    assert payload["ok"] is False
    assert payload["_status"] == 400


def test_post_scope_approve_succeeds_for_valid_scope(tmp_path: Path) -> None:
    config = _config(tmp_path)
    post_project_factory_new_project(config, {"name": "Scope Approve Valid", "root_path": str(tmp_path / "workspace")})
    post_project_factory_scope_package(config, {})
    patch_project_factory_scope_package(config, {"requirements": ["r1"], "acceptance_criteria": ["a1"]})
    payload = post_project_factory_scope_package_approve(config, {})
    assert payload["ok"] is True
    assert payload["scope_package"]["lifecycle_state"] == "scope_approved"


def test_get_architecture_contract_falls_back_to_active_project(tmp_path: Path) -> None:
    config = _config(tmp_path)
    post_project_factory_new_project(config, {"name": "Arch Read", "root_path": str(tmp_path / "workspace")})
    post_project_factory_scope_package(config, {})
    patch_project_factory_scope_package(config, {"requirements": ["r1"], "acceptance_criteria": ["a1"]})
    post_project_factory_scope_package_approve(config, {})
    post_project_factory_architecture_contract(config, {})
    payload = get_project_factory_architecture_contract(config, {})
    assert payload["ok"] is True
    assert payload["architecture_contract_exists"] is True


def test_get_architecture_contract_no_active_project_returns_friendly_state(tmp_path: Path) -> None:
    config = _config(tmp_path)
    payload = get_project_factory_architecture_contract(config, {})
    assert payload["ok"] is True
    assert payload["architecture_contract_exists"] is False
    assert payload["warnings"]


def test_post_architecture_prepare_validates_scope_approval(tmp_path: Path) -> None:
    config = _config(tmp_path)
    post_project_factory_new_project(config, {"name": "Arch Gate", "root_path": str(tmp_path / "workspace")})
    missing_scope = post_project_factory_architecture_contract(config, {})
    assert missing_scope["ok"] is False
    assert missing_scope["_status"] == 404
    post_project_factory_scope_package(config, {})
    unapproved_scope = post_project_factory_architecture_contract(config, {})
    assert unapproved_scope["ok"] is False
    assert unapproved_scope["_status"] == 409


def test_patch_architecture_contract_updates_fields(tmp_path: Path) -> None:
    config = _config(tmp_path)
    post_project_factory_new_project(config, {"name": "Arch Patch", "root_path": str(tmp_path / "workspace")})
    post_project_factory_scope_package(config, {})
    patch_project_factory_scope_package(config, {"requirements": ["r1"], "acceptance_criteria": ["a1"]})
    post_project_factory_scope_package_approve(config, {})
    post_project_factory_architecture_contract(config, {})
    payload = patch_project_factory_architecture_contract(
        config,
        {
            "architecture_summary": "summary",
            "system_components": ["api"],
            "testing_strategy": ["unit tests"],
        },
    )
    assert payload["ok"] is True
    assert payload["architecture_contract"]["lifecycle_state"] == "architecture_draft_updated"


def test_post_architecture_approve_validates_required_fields(tmp_path: Path) -> None:
    config = _config(tmp_path)
    post_project_factory_new_project(config, {"name": "Arch Approve", "root_path": str(tmp_path / "workspace")})
    post_project_factory_scope_package(config, {})
    patch_project_factory_scope_package(config, {"requirements": ["r1"], "acceptance_criteria": ["a1"]})
    post_project_factory_scope_package_approve(config, {})
    post_project_factory_architecture_contract(config, {})
    payload = post_project_factory_architecture_contract_approve(config, {})
    assert payload["ok"] is False
    assert payload["_status"] == 400


def test_post_architecture_approve_succeeds_for_valid_contract(tmp_path: Path) -> None:
    config = _config(tmp_path)
    post_project_factory_new_project(config, {"name": "Arch Approve Valid", "root_path": str(tmp_path / "workspace")})
    post_project_factory_scope_package(config, {})
    patch_project_factory_scope_package(config, {"requirements": ["r1"], "acceptance_criteria": ["a1"]})
    post_project_factory_scope_package_approve(config, {})
    post_project_factory_architecture_contract(config, {})
    patch_project_factory_architecture_contract(
        config,
        {
            "architecture_summary": "summary",
            "system_components": ["api"],
            "testing_strategy": ["unit tests"],
        },
    )
    payload = post_project_factory_architecture_contract_approve(config, {})
    assert payload["ok"] is True
    assert payload["architecture_contract"]["lifecycle_state"] == "architecture_approved"


def _seed_architecture_approved(config: AppConfig, tmp_path: Path) -> None:
    post_project_factory_new_project(config, {"name": "MIP Seed", "root_path": str(tmp_path / "workspace")})
    post_project_factory_scope_package(config, {})
    patch_project_factory_scope_package(config, {"requirements": ["r1"], "acceptance_criteria": ["a1"]})
    post_project_factory_scope_package_approve(config, {})
    post_project_factory_architecture_contract(config, {})
    patch_project_factory_architecture_contract(
        config,
        {"architecture_summary": "summary", "system_components": ["api"], "testing_strategy": ["unit tests"]},
    )
    post_project_factory_architecture_contract_approve(config, {})


def test_get_milestone_issue_plan_falls_back_to_active_project(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_architecture_approved(config, tmp_path)
    post_project_factory_milestone_issue_plan(config, {})
    payload = get_project_factory_milestone_issue_plan(config, {})
    assert payload["ok"] is True
    assert payload["milestone_issue_plan_exists"] is True


def test_get_milestone_issue_plan_no_active_project_returns_friendly_state(tmp_path: Path) -> None:
    config = _config(tmp_path)
    payload = get_project_factory_milestone_issue_plan(config, {})
    assert payload["ok"] is True
    assert payload["milestone_issue_plan_exists"] is False
    assert payload["warnings"]


def test_post_milestone_issue_plan_prepare_validates_approved_architecture(tmp_path: Path) -> None:
    config = _config(tmp_path)
    post_project_factory_new_project(config, {"name": "MIP Gate", "root_path": str(tmp_path / "workspace")})
    missing_arch = post_project_factory_milestone_issue_plan(config, {})
    assert missing_arch["ok"] is False
    assert missing_arch["_status"] == 404
    post_project_factory_scope_package(config, {})
    patch_project_factory_scope_package(config, {"requirements": ["r1"], "acceptance_criteria": ["a1"]})
    post_project_factory_scope_package_approve(config, {})
    post_project_factory_architecture_contract(config, {})
    unapproved_arch = post_project_factory_milestone_issue_plan(config, {})
    assert unapproved_arch["ok"] is False
    assert unapproved_arch["_status"] == 409


def test_patch_milestone_issue_plan_updates_fields(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_architecture_approved(config, tmp_path)
    post_project_factory_milestone_issue_plan(config, {})
    payload = patch_project_factory_milestone_issue_plan(
        config,
        {"planning_summary": "summary", "cross_cutting_tasks": ["ct1"]},
    )
    assert payload["ok"] is True
    assert payload["milestone_issue_plan"]["lifecycle_state"] == "milestone_issue_plan_draft_updated"


def test_post_milestone_issue_plan_approve_validates_fields(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_architecture_approved(config, tmp_path)
    post_project_factory_milestone_issue_plan(config, {})
    payload = post_project_factory_milestone_issue_plan_approve(config, {})
    assert payload["ok"] is False
    assert payload["_status"] == 400


def test_post_milestone_issue_plan_approve_succeeds_for_valid_plan(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_architecture_approved(config, tmp_path)
    post_project_factory_milestone_issue_plan(config, {})
    patch_project_factory_milestone_issue_plan(config, {"planning_summary": "summary"})
    payload = post_project_factory_milestone_issue_plan_approve(config, {})
    assert payload["ok"] is True
    assert payload["milestone_issue_plan"]["lifecycle_state"] == "milestone_issue_plan_approved"


def test_get_github_apply_plan_falls_back_to_active_project(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_architecture_approved(config, tmp_path)
    post_project_factory_milestone_issue_plan(config, {})
    patch_project_factory_milestone_issue_plan(config, {"planning_summary": "summary"})
    post_project_factory_milestone_issue_plan_approve(config, {})
    post_project_factory_github_apply_plan(config, {})
    payload = get_project_factory_github_apply_plan(config, {})
    assert payload["ok"] is True
    assert payload["github_apply_plan_exists"] is True


def test_get_github_apply_plan_no_active_project_returns_friendly_state(tmp_path: Path) -> None:
    config = _config(tmp_path)
    payload = get_project_factory_github_apply_plan(config, {})
    assert payload["ok"] is True
    assert payload["github_apply_plan_exists"] is False
    assert payload["warnings"]


def test_post_patch_approve_github_apply_plan(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_architecture_approved(config, tmp_path)
    post_project_factory_milestone_issue_plan(config, {})
    missing_approval = post_project_factory_github_apply_plan(config, {})
    assert missing_approval["ok"] is False
    assert missing_approval["_status"] == 409
    patch_project_factory_milestone_issue_plan(config, {"planning_summary": "summary"})
    post_project_factory_milestone_issue_plan_approve(config, {})
    prepared = post_project_factory_github_apply_plan(config, {})
    assert prepared["ok"] is True
    invalid_approve = post_project_factory_github_apply_plan_approve(config, {})
    assert invalid_approve["ok"] is False
    assert invalid_approve["_status"] == 400
    patched = patch_project_factory_github_apply_plan(
        config,
        {
            "apply_summary": "apply summary",
            "approval_conditions": ["Explicit approval required; execution remains gated."],
        },
    )
    assert patched["ok"] is True
    approved = post_project_factory_github_apply_plan_approve(config, {})
    assert approved["ok"] is True
    assert approved["github_apply_plan"]["lifecycle_state"] == "github_apply_plan_approved"
    assert approved["github_apply_plan"]["local_only"] is True
    assert approved["github_apply_plan"]["github_execution_status"] == "not_executed"


def test_agent_dispatch_plan_api_flows(tmp_path: Path) -> None:
    config = _config(tmp_path)
    friendly = get_project_factory_agent_dispatch_plan(config, {})
    assert friendly["ok"] is True
    assert friendly["agent_dispatch_plan_exists"] is False
    assert friendly["warnings"]

    _seed_architecture_approved(config, tmp_path)
    post_project_factory_milestone_issue_plan(config, {})
    patch_project_factory_milestone_issue_plan(config, {"planning_summary": "summary"})
    post_project_factory_milestone_issue_plan_approve(config, {})
    post_project_factory_github_apply_plan(config, {})
    gate = post_project_factory_agent_dispatch_plan(config, {})
    assert gate["ok"] is False
    assert gate["_status"] == 409

    patch_project_factory_github_apply_plan(
        config,
        {"apply_summary": "apply summary", "approval_conditions": ["Explicit approval required; execution remains gated."]},
    )
    post_project_factory_github_apply_plan_approve(config, {})
    prepared = post_project_factory_agent_dispatch_plan(config, {})
    assert prepared["ok"] is True

    fetched = get_project_factory_agent_dispatch_plan(config, {})
    assert fetched["ok"] is True
    assert fetched["agent_dispatch_plan_exists"] is True

    patched = patch_project_factory_agent_dispatch_plan(
        config,
        {"dispatch_summary": "dispatch summary", "approval_conditions": ["Agent execution approval is required before run."]},
    )
    assert patched["ok"] is True

    invalid_approve = post_project_factory_agent_dispatch_plan_approve(config, {})
    assert invalid_approve["ok"] is True
    assert invalid_approve["agent_dispatch_plan"]["lifecycle_state"] == "agent_dispatch_plan_approved"
    assert invalid_approve["agent_dispatch_plan"]["local_only"] is True
    assert invalid_approve["agent_dispatch_plan"]["agent_execution_status"] == "not_requested"


def test_validation_execution_plan_api_flows(tmp_path: Path) -> None:
    config = _config(tmp_path)
    friendly = get_project_factory_validation_execution_plan(config, {})
    assert friendly["ok"] is True
    assert friendly["validation_execution_plan_exists"] is False
    assert friendly["warnings"]

    _seed_architecture_approved(config, tmp_path)
    post_project_factory_milestone_issue_plan(config, {})
    patch_project_factory_milestone_issue_plan(config, {"planning_summary": "summary"})
    post_project_factory_milestone_issue_plan_approve(config, {})
    post_project_factory_github_apply_plan(config, {})
    patch_project_factory_github_apply_plan(
        config,
        {"apply_summary": "apply summary", "approval_conditions": ["Explicit approval required; execution remains gated."]},
    )
    post_project_factory_github_apply_plan_approve(config, {})
    post_project_factory_agent_dispatch_plan(config, {})
    gate = post_project_factory_validation_execution_plan(config, {})
    assert gate["ok"] is False
    assert gate["_status"] == 409

    patch_project_factory_agent_dispatch_plan(
        config,
        {"dispatch_summary": "dispatch summary", "approval_conditions": ["Agent execution approval is required before run."]},
    )
    post_project_factory_agent_dispatch_plan_approve(config, {})
    prepared = post_project_factory_validation_execution_plan(config, {})
    assert prepared["ok"] is True

    fetched = get_project_factory_validation_execution_plan(config, {})
    assert fetched["ok"] is True
    assert fetched["validation_execution_plan_exists"] is True

    patched = patch_project_factory_validation_execution_plan(
        config,
        {"validation_summary": "validation summary", "approval_conditions": ["Validation execution approval is required before run."]},
    )
    assert patched["ok"] is True

    approved = post_project_factory_validation_execution_plan_approve(config, {})
    assert approved["ok"] is True
    assert approved["validation_execution_plan"]["lifecycle_state"] == "validation_execution_plan_approved"
    assert approved["validation_execution_plan"]["local_only"] is True
    assert approved["validation_execution_plan"]["validation_execution_status"] == "not_requested"


def test_documentation_closeout_plan_api_flows(tmp_path: Path) -> None:
    config = _config(tmp_path)
    friendly = get_project_factory_documentation_closeout_plan(config, {})
    assert friendly["ok"] is True
    assert friendly["documentation_closeout_plan_exists"] is False
    assert friendly["warnings"]

    _seed_architecture_approved(config, tmp_path)
    post_project_factory_milestone_issue_plan(config, {})
    patch_project_factory_milestone_issue_plan(config, {"planning_summary": "summary"})
    post_project_factory_milestone_issue_plan_approve(config, {})
    post_project_factory_github_apply_plan(config, {})
    patch_project_factory_github_apply_plan(
        config,
        {"apply_summary": "apply summary", "approval_conditions": ["Explicit approval required; execution remains gated."]},
    )
    post_project_factory_github_apply_plan_approve(config, {})
    post_project_factory_agent_dispatch_plan(config, {})
    patch_project_factory_agent_dispatch_plan(
        config,
        {"dispatch_summary": "dispatch summary", "approval_conditions": ["Agent execution approval is required before run."]},
    )
    post_project_factory_agent_dispatch_plan_approve(config, {})
    post_project_factory_validation_execution_plan(config, {})
    gate = post_project_factory_documentation_closeout_plan(config, {})
    assert gate["ok"] is False
    assert gate["_status"] == 409

    patch_project_factory_validation_execution_plan(
        config,
        {"validation_summary": "validation summary", "approval_conditions": ["Validation execution approval is required before run."]},
    )
    post_project_factory_validation_execution_plan_approve(config, {})
    prepared = post_project_factory_documentation_closeout_plan(config, {})
    assert prepared["ok"] is True

    fetched = get_project_factory_documentation_closeout_plan(config, {})
    assert fetched["ok"] is True
    assert fetched["documentation_closeout_plan_exists"] is True

    patched = patch_project_factory_documentation_closeout_plan(
        config,
        {"closeout_summary": "closeout summary", "approval_conditions": ["Documentation execution and project closeout require explicit operator approval."]},
    )
    assert patched["ok"] is True

    approved = post_project_factory_documentation_closeout_plan_approve(config, {})
    assert approved["ok"] is True
    assert approved["documentation_closeout_plan"]["lifecycle_state"] == "documentation_closeout_plan_approved"
    assert approved["documentation_closeout_plan"]["local_only"] is True
    assert approved["documentation_closeout_plan"]["documentation_execution_status"] == "not_requested"


def test_execution_phase_approval_api_flows(tmp_path: Path) -> None:
    config = _config(tmp_path)
    friendly = get_project_factory_execution_phase_approval(config, {})
    assert friendly["ok"] is True
    assert friendly["execution_phase_approval_exists"] is False
    assert friendly["warnings"]

    _seed_architecture_approved(config, tmp_path)
    post_project_factory_milestone_issue_plan(config, {})
    patch_project_factory_milestone_issue_plan(config, {"planning_summary": "summary"})
    post_project_factory_milestone_issue_plan_approve(config, {})
    post_project_factory_github_apply_plan(config, {})
    patch_project_factory_github_apply_plan(config, {"apply_summary": "apply summary", "approval_conditions": ["Explicit approval required; execution remains gated."]})
    post_project_factory_github_apply_plan_approve(config, {})
    post_project_factory_agent_dispatch_plan(config, {})
    patch_project_factory_agent_dispatch_plan(config, {"dispatch_summary": "dispatch summary", "approval_conditions": ["Agent execution approval is required before run."]})
    post_project_factory_agent_dispatch_plan_approve(config, {})
    post_project_factory_validation_execution_plan(config, {})
    patch_project_factory_validation_execution_plan(config, {"validation_summary": "validation summary", "approval_conditions": ["Validation execution approval is required before run."]})
    post_project_factory_validation_execution_plan_approve(config, {})
    post_project_factory_documentation_closeout_plan(config, {})
    gate = post_project_factory_execution_phase_approval(config, {})
    assert gate["ok"] is False
    assert gate["_status"] == 409

    patch_project_factory_documentation_closeout_plan(
        config,
        {"closeout_summary": "closeout summary", "approval_conditions": ["Documentation execution and project closeout require explicit operator approval."]},
    )
    post_project_factory_documentation_closeout_plan_approve(config, {})
    prepared = post_project_factory_execution_phase_approval(config, {})
    assert prepared["ok"] is True

    fetched = get_project_factory_execution_phase_approval(config, {})
    assert fetched["ok"] is True
    assert fetched["execution_phase_approval_exists"] is True

    patched = patch_project_factory_execution_phase_approval(
        config,
        {
            "execution_lanes": [{"lane_id": "github_mutation_execution", "status": "approved", "acknowledgement_text": "Acknowledged."}],
            "approval_summary": "execution gate draft",
        },
    )
    assert patched["ok"] is True

    approved = post_project_factory_execution_phase_approval_approve(config, {})
    assert approved["ok"] is True
    assert approved["execution_phase_approval"]["lifecycle_state"] == "execution_phase_approval_approved"


def test_execution_readiness_api_route_returns_stable_json(tmp_path: Path) -> None:
    config = _config(tmp_path)
    no_active = get_project_factory_execution_readiness(config, {})
    assert no_active["ok"] is True
    assert no_active["overall_status"] == "blocked"
    post_project_factory_new_project(config, {"name": "Readiness API", "root_path": str(tmp_path / "workspace")})
    payload = get_project_factory_execution_readiness(config, {})
    assert payload["ok"] is True
    assert "artifact_summary" in payload
    assert "lane_summary" in payload
