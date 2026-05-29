from __future__ import annotations

import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.local_project_factory import (
    AGENT_LANE_KEYS,
    AI_ENGINE_KEYS,
    approve_project_documentation_closeout_plan,
    approve_project_execution_phase_approval,
    approve_project_validation_execution_plan,
    approve_project_agent_dispatch_plan,
    approve_project_architecture_contract,
    approve_project_github_apply_plan,
    approve_project_milestone_issue_plan,
    approve_project_scope_package,
    read_agent_engine_registry,
    read_project_ai_settings,
    inspect_project_factory_dossier,
    prepare_project_architecture_contract,
    prepare_project_documentation_closeout_plan,
    prepare_project_execution_phase_approval,
    prepare_project_agent_dispatch_plan,
    prepare_project_validation_execution_plan,
    prepare_project_github_apply_plan,
    prepare_project_milestone_issue_plan,
    prepare_project_scope_package,
    read_project_architecture_contract,
    read_project_agent_dispatch_plan,
    read_project_factory_dossier,
    read_project_documentation_closeout_plan,
    read_project_execution_phase_approval,
    read_project_execution_readiness,
    read_project_github_apply_plan,
    read_project_validation_execution_plan,
    read_project_milestone_issue_plan,
    read_project_scope_package,
    resolve_project_architecture_contract_path,
    resolve_project_agent_dispatch_plan_path,
    resolve_project_factory_dossier_path,
    resolve_project_documentation_closeout_plan_path,
    resolve_project_execution_phase_approval_path,
    resolve_project_ai_settings_path,
    resolve_project_github_apply_plan_path,
    resolve_project_milestone_issue_plan_path,
    resolve_project_validation_execution_plan_path,
    resolve_project_scope_package_path,
    start_new_project_factory,
    update_project_ai_settings,
    update_project_architecture_contract,
    update_project_documentation_closeout_plan,
    update_project_execution_phase_approval,
    update_project_agent_dispatch_plan,
    update_project_github_apply_plan,
    update_project_milestone_issue_plan,
    update_project_validation_execution_plan,
    update_project_scope_package,
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


def _payload(tmp_path: Path) -> dict[str, object]:
    return {
        "name": "Ares Wizard Project",
        "description": "Ship a local-first project-factory starter.",
        "project_type": "app",
        "preferred_stack": "python,fastapi",
        "root_path": str(tmp_path / "workspace"),
        "github_owner": "example-org",
        "github_repo": "ares-wizard-project",
        "github_mode": "create-later",
        "default_branch": "main",
        "initial_requirements": "Define scope and architecture before coding.",
        "tags": ["alpha", "wizard"],
    }


def test_start_new_project_factory_creates_expected_local_state(tmp_path: Path) -> None:
    config = _config(tmp_path)
    result = start_new_project_factory(config, _payload(tmp_path))

    assert result["ok"] is True
    assert result["local_only"] is True
    assert result["project"]["project_id"] == "ares-wizard-project"
    assert result["repo"]["repo_id"] == "ares-wizard-project-primary"
    assert result["active_project_id"] == "ares-wizard-project"
    assert result["scope_queue_item"]["title"] == "Scope project: Ares Wizard Project"
    assert result["scope_queue_item"]["item_type"] == "task"
    assert result["scope_queue_item"]["priority"] == "high"
    assert result["scope_queue_item"]["source"] == "hub-new-project-wizard"
    assert "project-factory" in result["scope_queue_item"]["tags"]
    assert "scope-project" in result["scope_queue_item"]["tags"]
    assert "new-project-wizard" in result["scope_queue_item"]["tags"]
    assert Path(str(result["dossier_path"])).exists()
    assert result["dossier"]["lifecycle_state"] == "intake_created"
    assert result["dossier"]["next_recommended_action"] == "scope_project"
    assert result["dossier"]["safety_boundary"]["local_only"] is True
    assert result["dossier"]["safety_boundary"]["github_mutation_status"] == "not_requested"
    assert result["dossier"]["safety_boundary"]["model_execution_status"] == "not_requested"


def test_start_new_project_factory_rejects_missing_project_name(tmp_path: Path) -> None:
    config = _config(tmp_path)
    payload = _payload(tmp_path)
    payload["name"] = " "

    result = start_new_project_factory(config, payload)

    assert result["ok"] is False
    assert result["error"] == "invalid_project_factory_payload"


def test_start_new_project_factory_auto_generates_project_id(tmp_path: Path) -> None:
    config = _config(tmp_path)
    payload = _payload(tmp_path)
    payload["project_id"] = ""
    payload["name"] = "My Cool New App"

    result = start_new_project_factory(config, payload)

    assert result["ok"] is True
    assert result["project"]["project_id"] == "my-cool-new-app"


def test_resolve_project_factory_dossier_path_uses_local_file_backed_location(tmp_path: Path) -> None:
    path = resolve_project_factory_dossier_path(tmp_path, "p1")
    normalized = str(path).replace("\\", "/")
    assert normalized.endswith(".aresforge/projects/p1/factory_dossier.json")


def test_start_new_project_factory_writes_dossier_json(tmp_path: Path) -> None:
    config = _config(tmp_path)
    result = start_new_project_factory(config, _payload(tmp_path))

    dossier_path = Path(str(result["dossier_path"]))
    rendered = json.loads(dossier_path.read_text(encoding="utf-8"))
    assert rendered["project_id"] == result["project"]["project_id"]
    assert rendered["name"] == "Ares Wizard Project"
    assert rendered["github_mode"] == "create-later"


def test_read_project_factory_dossier_missing_returns_friendly_payload(tmp_path: Path) -> None:
    config = _config(tmp_path)
    payload = read_project_factory_dossier(config, "missing-project")
    assert payload["ok"] is True
    assert payload["dossier_exists"] is False
    assert payload["project_id"] == "missing-project"
    assert payload["warnings"]


def test_read_project_factory_dossier_existing_returns_dossier(tmp_path: Path) -> None:
    config = _config(tmp_path)
    created = start_new_project_factory(config, _payload(tmp_path))
    payload = read_project_factory_dossier(config, str(created["project"]["project_id"]))
    assert payload["ok"] is True
    assert payload["dossier_exists"] is True
    assert payload["dossier"]["project_id"] == created["project"]["project_id"]


def test_read_agent_engine_registry_returns_required_non_executing_contract(tmp_path: Path) -> None:
    config = _config(tmp_path)
    payload = read_agent_engine_registry(config)

    assert payload["ok"] is True
    assert payload["execution_allowed"] is False
    lane_keys = {lane["key"] for lane in payload["agent_lanes"]}
    engine_keys = {engine["key"] for engine in payload["engines"]}
    assert lane_keys == set(AGENT_LANE_KEYS)
    assert engine_keys == set(AI_ENGINE_KEYS)
    assert all(lane["routing_only"] is True for lane in payload["agent_lanes"])
    assert all(lane["execution_allowed"] is False for lane in payload["agent_lanes"])
    assert all(engine["execution_allowed"] is False for engine in payload["engines"])
    assert all(engine["operator_gate_required"] is True for engine in payload["engines"])

    codex = next(engine for engine in payload["engines"] if engine["key"] == "codex_cli")
    assert codex["model_profiles"]["placeholder_only"] is True
    assert "default Codex model" in codex["model_profiles"]["future_fields"]
    assert payload["next_safe_action"] == "use_registry_for_future_routing_contract_validation_only"


def test_read_project_ai_settings_returns_default_contract_without_writing(tmp_path: Path) -> None:
    config = _config(tmp_path)
    created = start_new_project_factory(config, _payload(tmp_path))
    project_id = str(created["project"]["project_id"])

    payload = read_project_ai_settings(config, project_id)

    assert payload["ok"] is True
    assert payload["settings_exists"] is False
    assert payload["project_ai_settings"]["project_ai_mode"] == "balanced"
    assert payload["project_ai_settings"]["default_engine"] == "local_coding_llm"
    assert "codex_cli" in payload["project_ai_settings"]["available_engines"]
    assert payload["validation"]["valid"] is True
    assert payload["next_safe_action"] == "review_project_ai_settings_before_future_routing"
    assert not resolve_project_ai_settings_path(tmp_path, project_id).exists()


def test_update_project_ai_settings_writes_valid_local_contract(tmp_path: Path) -> None:
    config = _config(tmp_path)
    created = start_new_project_factory(config, _payload(tmp_path))
    project_id = str(created["project"]["project_id"])

    payload = update_project_ai_settings(
        config,
        project_id,
        {
            "project_ai_mode": "local_only",
            "available_engines": ["local_reasoning_llm", "local_coding_llm"],
            "disabled_engines": ["codex_cli"],
            "default_engine": "local_coding_llm",
            "default_model": "local-code-model",
            "operator_override_allowed": True,
            "notes": "Prefer local coding model.",
        },
    )

    assert payload["ok"] is True
    settings = payload["project_ai_settings"]
    assert settings["project_ai_mode"] == "local_only"
    assert settings["default_model"] == "local-code-model"
    assert settings["updated_at"]
    settings_path = resolve_project_ai_settings_path(tmp_path, project_id)
    assert settings_path.exists()
    rendered = json.loads(settings_path.read_text(encoding="utf-8"))
    assert rendered["disabled_engines"] == ["codex_cli"]


def test_project_ai_settings_reject_invalid_mode_and_engine(tmp_path: Path) -> None:
    config = _config(tmp_path)
    created = start_new_project_factory(config, _payload(tmp_path))
    project_id = str(created["project"]["project_id"])

    invalid_mode = update_project_ai_settings(config, project_id, {"project_ai_mode": "turbo_magic"})
    assert invalid_mode["ok"] is False
    assert invalid_mode["error"] == "project_ai_settings_validation_failed"

    invalid_engine = update_project_ai_settings(
        config,
        project_id,
        {"available_engines": ["local_coding_llm", "mystery_engine"]},
    )
    assert invalid_engine["ok"] is False
    assert invalid_engine["error"] == "project_ai_settings_validation_failed"


def test_project_ai_settings_reject_default_disabled_or_wrong_mode(tmp_path: Path) -> None:
    config = _config(tmp_path)
    created = start_new_project_factory(config, _payload(tmp_path))
    project_id = str(created["project"]["project_id"])

    disabled_default = update_project_ai_settings(
        config,
        project_id,
        {"default_engine": "local_coding_llm", "disabled_engines": ["local_coding_llm"]},
    )
    assert disabled_default["ok"] is False

    local_codex = update_project_ai_settings(
        config,
        project_id,
        {"project_ai_mode": "local_only", "default_engine": "codex_cli"},
    )
    assert local_codex["ok"] is False

    codex_local = update_project_ai_settings(
        config,
        project_id,
        {"project_ai_mode": "codex_only", "default_engine": "local_coding_llm"},
    )
    assert codex_local["ok"] is False


def test_project_ai_settings_manual_only_can_omit_default_engine(tmp_path: Path) -> None:
    config = _config(tmp_path)
    created = start_new_project_factory(config, _payload(tmp_path))
    project_id = str(created["project"]["project_id"])

    payload = update_project_ai_settings(
        config,
        project_id,
        {
            "project_ai_mode": "manual_only",
            "available_engines": ["local_reasoning_llm", "local_coding_llm", "codex_cli"],
            "disabled_engines": [],
            "default_engine": "",
        },
    )

    assert payload["ok"] is True
    assert payload["project_ai_settings"]["project_ai_mode"] == "manual_only"
    assert payload["project_ai_settings"]["default_engine"] == ""


def test_inspect_project_factory_dossier_includes_workflow_steps(tmp_path: Path) -> None:
    config = _config(tmp_path)
    created = start_new_project_factory(config, _payload(tmp_path))
    payload = inspect_project_factory_dossier(config, str(created["project"]["project_id"]))
    step_ids = [step["step_id"] for step in payload["workflow_steps"]]
    assert "project_intake" in step_ids
    assert "scope_project" in step_ids
    assert "github_apply" in step_ids
    assert "agent_dispatch" in step_ids
    assert "execution_phase_approval" in step_ids


def test_prepare_project_scope_package_writes_scope_package_and_updates_dossier(tmp_path: Path) -> None:
    config = _config(tmp_path)
    created = start_new_project_factory(config, _payload(tmp_path))
    project_id = str(created["project"]["project_id"])
    payload = prepare_project_scope_package(config, project_id)
    assert payload["ok"] is True

    scope_path = resolve_project_scope_package_path(tmp_path, project_id)
    rendered_scope = json.loads(scope_path.read_text(encoding="utf-8"))
    assert rendered_scope["project_id"] == project_id
    assert rendered_scope["scope_status"] == "not_started"
    assert rendered_scope["model_execution_status"] == "not_requested"
    assert rendered_scope["github_mutation_status"] == "not_requested"
    assert rendered_scope["next_recommended_action"] == "approve_scope_generation_or_edit_scope_locally"

    dossier = read_project_factory_dossier(config, project_id)
    assert dossier["dossier"]["lifecycle_state"] == "scope_package_prepared"
    assert dossier["dossier"]["next_recommended_action"] == "approve_scope_generation_or_edit_scope_locally"


def test_prepare_project_scope_package_rejects_missing_dossier(tmp_path: Path) -> None:
    config = _config(tmp_path)
    payload = prepare_project_scope_package(config, "missing")
    assert payload["ok"] is False
    assert payload["error"] == "project_factory_dossier_not_found"


def test_read_missing_scope_package_returns_friendly_payload(tmp_path: Path) -> None:
    config = _config(tmp_path)
    payload = read_project_scope_package(config, "missing-project")
    assert payload["ok"] is True
    assert payload["scope_package_exists"] is False


def test_update_scope_package_writes_fields_audit_and_lifecycle(tmp_path: Path) -> None:
    config = _config(tmp_path)
    created = start_new_project_factory(config, _payload(tmp_path))
    project_id = str(created["project"]["project_id"])
    prepare_project_scope_package(config, project_id)
    payload = update_project_scope_package(
        config,
        project_id,
        {
            "requirements": ["r1"],
            "acceptance_criteria": ["a1"],
            "notes": "local notes",
        },
    )
    assert payload["ok"] is True
    scope = payload["scope_package"]
    assert scope["requirements"] == ["r1"]
    assert scope["acceptance_criteria"] == ["a1"]
    assert scope["notes"] == "local notes"
    assert scope["lifecycle_state"] == "scope_draft_updated"
    assert any(entry.get("event_type") == "scope_draft_updated" for entry in scope.get("audit_trail", []))


def test_approve_scope_fails_without_requirements(tmp_path: Path) -> None:
    config = _config(tmp_path)
    created = start_new_project_factory(config, _payload(tmp_path))
    project_id = str(created["project"]["project_id"])
    prepare_project_scope_package(config, project_id)
    update_project_scope_package(config, project_id, {"acceptance_criteria": ["a1"]})
    payload = approve_project_scope_package(config, project_id, {})
    assert payload["ok"] is False
    assert payload["error"] == "scope_approval_validation_failed"


def test_approve_scope_fails_without_acceptance_criteria(tmp_path: Path) -> None:
    config = _config(tmp_path)
    created = start_new_project_factory(config, _payload(tmp_path))
    project_id = str(created["project"]["project_id"])
    prepare_project_scope_package(config, project_id)
    update_project_scope_package(config, project_id, {"requirements": ["r1"]})
    payload = approve_project_scope_package(config, project_id, {})
    assert payload["ok"] is False
    assert payload["error"] == "scope_approval_validation_failed"


def test_approve_scope_succeeds_and_transitions_scope_and_dossier(tmp_path: Path) -> None:
    config = _config(tmp_path)
    created = start_new_project_factory(config, _payload(tmp_path))
    project_id = str(created["project"]["project_id"])
    prepare_project_scope_package(config, project_id)
    update_project_scope_package(config, project_id, {"requirements": ["r1"], "acceptance_criteria": ["a1"]})
    payload = approve_project_scope_package(config, project_id, {})
    assert payload["ok"] is True
    assert payload["scope_package"]["lifecycle_state"] == "scope_approved"
    dossier = read_project_factory_dossier(config, project_id)
    assert dossier["dossier"]["lifecycle_state"] == "scope_approved"
    assert dossier["dossier"]["next_recommended_action"] == "prepare_architecture_contract"


def test_scope_audit_trail_preserves_existing_entries(tmp_path: Path) -> None:
    config = _config(tmp_path)
    created = start_new_project_factory(config, _payload(tmp_path))
    project_id = str(created["project"]["project_id"])
    prepare_project_scope_package(config, project_id)
    first_update = update_project_scope_package(config, project_id, {"requirements": ["r1"]})
    first_count = len(first_update["scope_package"].get("audit_trail", []))
    second_update = update_project_scope_package(config, project_id, {"acceptance_criteria": ["a1"]})
    second_count = len(second_update["scope_package"].get("audit_trail", []))
    assert second_count > first_count


def test_read_missing_architecture_contract_returns_friendly_payload(tmp_path: Path) -> None:
    config = _config(tmp_path)
    payload = read_project_architecture_contract(config, "missing-project")
    assert payload["ok"] is True
    assert payload["architecture_contract_exists"] is False


def test_prepare_architecture_contract_fails_without_scope_package(tmp_path: Path) -> None:
    config = _config(tmp_path)
    created = start_new_project_factory(config, _payload(tmp_path))
    payload = prepare_project_architecture_contract(config, str(created["project"]["project_id"]))
    assert payload["ok"] is False
    assert payload["error"] == "scope_package_not_found"


def test_prepare_architecture_contract_fails_when_scope_not_approved(tmp_path: Path) -> None:
    config = _config(tmp_path)
    created = start_new_project_factory(config, _payload(tmp_path))
    project_id = str(created["project"]["project_id"])
    prepare_project_scope_package(config, project_id)
    payload = prepare_project_architecture_contract(config, project_id)
    assert payload["ok"] is False
    assert payload["error"] == "scope_not_approved"


def test_prepare_architecture_contract_succeeds_and_writes_file(tmp_path: Path) -> None:
    config = _config(tmp_path)
    created = start_new_project_factory(config, _payload(tmp_path))
    project_id = str(created["project"]["project_id"])
    prepare_project_scope_package(config, project_id)
    update_project_scope_package(config, project_id, {"requirements": ["r1"], "acceptance_criteria": ["a1"]})
    approve_project_scope_package(config, project_id, {})
    payload = prepare_project_architecture_contract(config, project_id)
    assert payload["ok"] is True
    architecture_path = resolve_project_architecture_contract_path(tmp_path, project_id)
    rendered = json.loads(architecture_path.read_text(encoding="utf-8"))
    assert rendered["lifecycle_state"] == "architecture_contract_prepared"
    assert rendered["model_execution_status"] == "not_requested"
    assert rendered["github_mutation_status"] == "not_requested"
    dossier = read_project_factory_dossier(config, project_id)
    assert dossier["dossier"]["lifecycle_state"] == "architecture_contract_prepared"
    assert dossier["dossier"]["next_recommended_action"] == "edit_architecture_contract"


def test_update_architecture_contract_writes_fields_and_audit_and_transitions(tmp_path: Path) -> None:
    config = _config(tmp_path)
    created = start_new_project_factory(config, _payload(tmp_path))
    project_id = str(created["project"]["project_id"])
    prepare_project_scope_package(config, project_id)
    update_project_scope_package(config, project_id, {"requirements": ["r1"], "acceptance_criteria": ["a1"]})
    approve_project_scope_package(config, project_id, {})
    prepare_project_architecture_contract(config, project_id)
    payload = update_project_architecture_contract(
        config,
        project_id,
        {
            "architecture_summary": "summary",
            "system_components": ["api"],
            "testing_strategy": ["unit tests"],
            "milestone_planning_notes": "notes",
        },
    )
    assert payload["ok"] is True
    architecture = payload["architecture_contract"]
    assert architecture["lifecycle_state"] == "architecture_draft_updated"
    assert architecture["architecture_summary"] == "summary"
    assert architecture["system_components"] == ["api"]
    assert architecture["testing_strategy"] == ["unit tests"]
    assert any(entry.get("event_type") == "architecture_draft_updated" for entry in architecture.get("audit_trail", []))


def test_approve_architecture_fails_without_required_fields(tmp_path: Path) -> None:
    config = _config(tmp_path)
    created = start_new_project_factory(config, _payload(tmp_path))
    project_id = str(created["project"]["project_id"])
    prepare_project_scope_package(config, project_id)
    update_project_scope_package(config, project_id, {"requirements": ["r1"], "acceptance_criteria": ["a1"]})
    approve_project_scope_package(config, project_id, {})
    prepare_project_architecture_contract(config, project_id)

    missing_summary = approve_project_architecture_contract(config, project_id, {})
    assert missing_summary["ok"] is False
    assert missing_summary["error"] == "architecture_approval_validation_failed"

    update_project_architecture_contract(config, project_id, {"architecture_summary": "summary"})
    missing_components = approve_project_architecture_contract(config, project_id, {})
    assert missing_components["ok"] is False

    update_project_architecture_contract(config, project_id, {"system_components": ["api"]})
    missing_testing = approve_project_architecture_contract(config, project_id, {})
    assert missing_testing["ok"] is False


def test_approve_architecture_succeeds_and_preserves_audit_entries(tmp_path: Path) -> None:
    config = _config(tmp_path)
    created = start_new_project_factory(config, _payload(tmp_path))
    project_id = str(created["project"]["project_id"])
    prepare_project_scope_package(config, project_id)
    update_project_scope_package(config, project_id, {"requirements": ["r1"], "acceptance_criteria": ["a1"]})
    approve_project_scope_package(config, project_id, {})
    prepared = prepare_project_architecture_contract(config, project_id)
    first_count = len(prepared["architecture_contract"].get("audit_trail", []))
    update_project_architecture_contract(
        config,
        project_id,
        {"architecture_summary": "summary", "system_components": ["api"], "testing_strategy": ["unit tests"]},
    )
    approved = approve_project_architecture_contract(config, project_id, {})
    assert approved["ok"] is True
    assert approved["architecture_contract"]["lifecycle_state"] == "architecture_approved"
    assert len(approved["architecture_contract"].get("audit_trail", [])) > first_count
    dossier = read_project_factory_dossier(config, project_id)
    assert dossier["dossier"]["lifecycle_state"] == "architecture_approved"
    assert dossier["dossier"]["next_recommended_action"] == "prepare_milestone_issue_plan"


def _seed_architecture_approved(config: AppConfig, tmp_path: Path) -> str:
    created = start_new_project_factory(config, _payload(tmp_path))
    project_id = str(created["project"]["project_id"])
    prepare_project_scope_package(config, project_id)
    update_project_scope_package(config, project_id, {"requirements": ["r1"], "acceptance_criteria": ["a1"]})
    approve_project_scope_package(config, project_id, {})
    prepare_project_architecture_contract(config, project_id)
    update_project_architecture_contract(
        config,
        project_id,
        {"architecture_summary": "summary", "system_components": ["api"], "testing_strategy": ["unit tests"]},
    )
    approve_project_architecture_contract(config, project_id, {})
    return project_id


def test_read_missing_milestone_issue_plan_returns_friendly_payload(tmp_path: Path) -> None:
    config = _config(tmp_path)
    payload = read_project_milestone_issue_plan(config, "missing-project")
    assert payload["ok"] is True
    assert payload["milestone_issue_plan_exists"] is False


def test_prepare_milestone_issue_plan_fails_without_architecture_contract(tmp_path: Path) -> None:
    config = _config(tmp_path)
    created = start_new_project_factory(config, _payload(tmp_path))
    payload = prepare_project_milestone_issue_plan(config, str(created["project"]["project_id"]))
    assert payload["ok"] is False
    assert payload["error"] == "architecture_contract_not_found"


def test_prepare_milestone_issue_plan_fails_when_architecture_not_approved(tmp_path: Path) -> None:
    config = _config(tmp_path)
    created = start_new_project_factory(config, _payload(tmp_path))
    project_id = str(created["project"]["project_id"])
    prepare_project_scope_package(config, project_id)
    update_project_scope_package(config, project_id, {"requirements": ["r1"], "acceptance_criteria": ["a1"]})
    approve_project_scope_package(config, project_id, {})
    prepare_project_architecture_contract(config, project_id)
    payload = prepare_project_milestone_issue_plan(config, project_id)
    assert payload["ok"] is False
    assert payload["error"] == "architecture_not_approved"


def test_prepare_milestone_issue_plan_succeeds_and_writes_file(tmp_path: Path) -> None:
    config = _config(tmp_path)
    project_id = _seed_architecture_approved(config, tmp_path)
    payload = prepare_project_milestone_issue_plan(config, project_id)
    assert payload["ok"] is True
    plan_path = resolve_project_milestone_issue_plan_path(tmp_path, project_id)
    rendered = json.loads(plan_path.read_text(encoding="utf-8"))
    assert rendered["lifecycle_state"] == "milestone_issue_plan_prepared"
    assert rendered["model_execution_status"] == "not_requested"
    assert rendered["github_mutation_status"] == "not_requested"
    assert rendered["milestones"]
    assert rendered["issues"]
    dossier = read_project_factory_dossier(config, project_id)
    assert dossier["dossier"]["lifecycle_state"] == "milestone_issue_plan_prepared"
    assert dossier["dossier"]["next_recommended_action"] == "edit_milestone_issue_plan"


def test_update_milestone_issue_plan_writes_fields_and_audit_and_transitions(tmp_path: Path) -> None:
    config = _config(tmp_path)
    project_id = _seed_architecture_approved(config, tmp_path)
    prepare_project_milestone_issue_plan(config, project_id)
    payload = update_project_milestone_issue_plan(
        config,
        project_id,
        {"planning_summary": "Plan summary", "cross_cutting_tasks": ["ct1"], "validation_plan": ["pytest -q"]},
    )
    assert payload["ok"] is True
    plan = payload["milestone_issue_plan"]
    assert plan["lifecycle_state"] == "milestone_issue_plan_draft_updated"
    assert plan["planning_summary"] == "Plan summary"
    assert any(entry.get("event_type") == "milestone_issue_plan_draft_updated" for entry in plan.get("audit_trail", []))
    dossier = read_project_factory_dossier(config, project_id)
    assert dossier["dossier"]["lifecycle_state"] == "milestone_issue_plan_draft_updated"


def test_approve_milestone_issue_plan_validates_required_fields(tmp_path: Path) -> None:
    config = _config(tmp_path)
    project_id = _seed_architecture_approved(config, tmp_path)
    prepare_project_milestone_issue_plan(config, project_id)

    missing_summary = approve_project_milestone_issue_plan(config, project_id, {})
    assert missing_summary["ok"] is False

    update_project_milestone_issue_plan(config, project_id, {"planning_summary": "summary", "milestones": []})
    missing_milestones = approve_project_milestone_issue_plan(config, project_id, {})
    assert missing_milestones["ok"] is False

    prepare_project_milestone_issue_plan(config, project_id)
    update_project_milestone_issue_plan(config, project_id, {"planning_summary": "summary", "issues": []})
    missing_issues = approve_project_milestone_issue_plan(config, project_id, {})
    assert missing_issues["ok"] is False


def test_approve_milestone_issue_plan_fails_when_issue_references_missing_milestone(tmp_path: Path) -> None:
    config = _config(tmp_path)
    project_id = _seed_architecture_approved(config, tmp_path)
    prepare_project_milestone_issue_plan(config, project_id)
    update_project_milestone_issue_plan(
        config,
        project_id,
        {
            "planning_summary": "summary",
            "issues": [
                {
                    "issue_id": "I1",
                    "milestone_id": "missing",
                    "title": "x",
                    "description": "x",
                    "issue_type": "task",
                    "priority": "normal",
                    "agent_type": "backend",
                }
            ],
        },
    )
    payload = approve_project_milestone_issue_plan(config, project_id, {})
    assert payload["ok"] is False


def test_approve_milestone_issue_plan_succeeds_and_preserves_audit_entries(tmp_path: Path) -> None:
    config = _config(tmp_path)
    project_id = _seed_architecture_approved(config, tmp_path)
    prepared = prepare_project_milestone_issue_plan(config, project_id)
    first_count = len(prepared["milestone_issue_plan"].get("audit_trail", []))
    draft = update_project_milestone_issue_plan(config, project_id, {"planning_summary": "summary"})
    approved = approve_project_milestone_issue_plan(config, project_id, {})
    assert approved["ok"] is True
    assert approved["milestone_issue_plan"]["lifecycle_state"] == "milestone_issue_plan_approved"
    assert len(approved["milestone_issue_plan"].get("audit_trail", [])) > first_count
    assert len(approved["milestone_issue_plan"].get("audit_trail", [])) > len(draft["milestone_issue_plan"].get("audit_trail", [])) - 1
    dossier = read_project_factory_dossier(config, project_id)
    assert dossier["dossier"]["lifecycle_state"] == "milestone_issue_plan_approved"
    assert dossier["dossier"]["next_recommended_action"] == "prepare_github_apply_plan"


def _seed_milestone_issue_plan_approved(config: AppConfig, tmp_path: Path) -> str:
    project_id = _seed_architecture_approved(config, tmp_path)
    prepare_project_milestone_issue_plan(config, project_id)
    update_project_milestone_issue_plan(config, project_id, {"planning_summary": "summary"})
    approve_project_milestone_issue_plan(config, project_id, {})
    return project_id


def test_read_missing_github_apply_plan_returns_friendly_payload(tmp_path: Path) -> None:
    config = _config(tmp_path)
    payload = read_project_github_apply_plan(config, "missing-project")
    assert payload["ok"] is True
    assert payload["github_apply_plan_exists"] is False


def test_prepare_github_apply_plan_validations_and_success(tmp_path: Path) -> None:
    config = _config(tmp_path)
    created = start_new_project_factory(config, _payload(tmp_path))
    project_id = str(created["project"]["project_id"])
    missing = prepare_project_github_apply_plan(config, project_id)
    assert missing["ok"] is False
    assert missing["error"] == "milestone_issue_plan_not_found"

    project_id = _seed_architecture_approved(config, tmp_path)
    prepare_project_milestone_issue_plan(config, project_id)
    unapproved = prepare_project_github_apply_plan(config, project_id)
    assert unapproved["ok"] is False
    assert unapproved["error"] == "milestone_issue_plan_not_approved"

    project_id = _seed_milestone_issue_plan_approved(config, tmp_path)
    payload = prepare_project_github_apply_plan(config, project_id)
    assert payload["ok"] is True
    plan_path = resolve_project_github_apply_plan_path(tmp_path, project_id)
    rendered = json.loads(plan_path.read_text(encoding="utf-8"))
    assert rendered["lifecycle_state"] == "github_apply_plan_prepared"
    assert rendered["mutation_intent"]["create_milestones"]
    assert rendered["mutation_intent"]["create_issues"]
    assert "Local plan only; not executed." in rendered["mutation_intent"]["create_issues"][0]["body"]
    labels = rendered["mutation_intent"]["create_issues"][0]["labels"]
    assert any(label.startswith("issue-type:") for label in labels)
    assert any(label.startswith("priority:") for label in labels)
    assert any(label.startswith("agent:") for label in labels)
    dossier = read_project_factory_dossier(config, project_id)
    assert dossier["dossier"]["lifecycle_state"] == "github_apply_plan_prepared"


def test_update_and_approve_github_apply_plan_lifecycle_and_audit(tmp_path: Path) -> None:
    config = _config(tmp_path)
    project_id = _seed_milestone_issue_plan_approved(config, tmp_path)
    prepared = prepare_project_github_apply_plan(config, project_id)
    first_count = len(prepared["github_apply_plan"].get("audit_trail", []))
    updated = update_project_github_apply_plan(
        config,
        project_id,
        {
            "apply_summary": "Ready for local apply review",
            "approval_conditions": ["Approval is required before any execution; keep execution gated."],
            "dry_run_notes": ["No execution performed."],
        },
    )
    assert updated["ok"] is True
    assert updated["github_apply_plan"]["lifecycle_state"] == "github_apply_plan_draft_updated"
    assert len(updated["github_apply_plan"].get("audit_trail", [])) > first_count

    project_id_for_validation = _seed_milestone_issue_plan_approved(config, tmp_path)
    prepare_project_github_apply_plan(config, project_id_for_validation)
    missing_summary = approve_project_github_apply_plan(config, project_id_for_validation, {})
    assert missing_summary["ok"] is False

    update_project_github_apply_plan(config, project_id_for_validation, {"apply_summary": "summary", "approval_conditions": ["needs review"]})
    missing_condition = approve_project_github_apply_plan(config, project_id_for_validation, {})
    assert missing_condition["ok"] is False

    update_project_github_apply_plan(
        config,
        project_id_for_validation,
        {
            "apply_summary": "Approved local apply plan",
            "approval_conditions": ["Explicit approval required; execution remains gated until approved."],
        },
    )
    approved = approve_project_github_apply_plan(config, project_id_for_validation, {})
    assert approved["ok"] is True
    assert approved["github_apply_plan"]["lifecycle_state"] == "github_apply_plan_approved"
    assert approved["github_apply_plan"]["github_execution_status"] == "not_executed"
    dossier = read_project_factory_dossier(config, project_id_for_validation)
    assert dossier["dossier"]["lifecycle_state"] == "github_apply_plan_approved"


def _seed_github_apply_plan_approved(config: AppConfig, tmp_path: Path) -> str:
    project_id = _seed_milestone_issue_plan_approved(config, tmp_path)
    prepare_project_github_apply_plan(config, project_id)
    update_project_github_apply_plan(
        config,
        project_id,
        {"apply_summary": "summary", "approval_conditions": ["Explicit approval required; execution remains gated until approved."]},
    )
    approve_project_github_apply_plan(config, project_id, {})
    return project_id


def test_agent_dispatch_plan_lifecycle_and_validations(tmp_path: Path) -> None:
    config = _config(tmp_path)
    missing = read_project_agent_dispatch_plan(config, "missing-project")
    assert missing["ok"] is True
    assert missing["agent_dispatch_plan_exists"] is False

    created = start_new_project_factory(config, _payload(tmp_path))
    missing_apply = prepare_project_agent_dispatch_plan(config, str(created["project"]["project_id"]))
    assert missing_apply["ok"] is False
    assert missing_apply["error"] == "github_apply_plan_not_found"

    project_id = _seed_milestone_issue_plan_approved(config, tmp_path)
    prepare_project_github_apply_plan(config, project_id)
    unapproved = prepare_project_agent_dispatch_plan(config, project_id)
    assert unapproved["ok"] is False
    assert unapproved["error"] == "github_apply_plan_not_approved"

    project_id = _seed_github_apply_plan_approved(config, tmp_path)
    prepared = prepare_project_agent_dispatch_plan(config, project_id)
    assert prepared["ok"] is True
    plan_path = resolve_project_agent_dispatch_plan_path(tmp_path, project_id)
    rendered = json.loads(plan_path.read_text(encoding="utf-8"))
    assert rendered["lifecycle_state"] == "agent_dispatch_plan_prepared"
    assert rendered["dispatch_plan"]["dispatch_items"]
    assert rendered["dispatch_plan"]["agent_queues"]
    assert rendered["dispatch_plan"]["dispatch_items"][0]["execution_status"] == "not_executed"
    assert rendered["agent_execution_status"] == "not_requested"
    assert rendered["model_execution_status"] == "not_requested"

    first_count = len(prepared["agent_dispatch_plan"].get("audit_trail", []))
    updated = update_project_agent_dispatch_plan(
        config,
        project_id,
        {"dispatch_summary": "dispatch summary", "sequencing_notes": ["s1"], "approval_conditions": ["Agent execution approval is required before run."]},
    )
    assert updated["ok"] is True
    assert updated["agent_dispatch_plan"]["lifecycle_state"] == "agent_dispatch_plan_draft_updated"
    assert len(updated["agent_dispatch_plan"].get("audit_trail", [])) > first_count

    project_id_for_validation = _seed_github_apply_plan_approved(config, tmp_path)
    prepare_project_agent_dispatch_plan(config, project_id_for_validation)
    missing_summary = approve_project_agent_dispatch_plan(config, project_id_for_validation, {})
    assert missing_summary["ok"] is False
    assert missing_summary["error"] == "agent_dispatch_plan_approval_validation_failed"

    update_project_agent_dispatch_plan(config, project_id_for_validation, {"dispatch_summary": "summary"})
    missing_condition = approve_project_agent_dispatch_plan(config, project_id_for_validation, {})
    assert missing_condition["ok"] is False

    refreshed = prepare_project_agent_dispatch_plan(config, project_id_for_validation)
    invalid_no_items = update_project_agent_dispatch_plan(
        config,
        project_id_for_validation,
        {"dispatch_summary": "summary", "approval_conditions": ["Model execution approval is required."], "known_risks": ["r1"]},
    )
    invalid_no_items["agent_dispatch_plan"]["dispatch_plan"]["dispatch_items"] = []
    resolve_project_agent_dispatch_plan_path(tmp_path, project_id_for_validation).write_text(
        json.dumps(invalid_no_items["agent_dispatch_plan"], indent=2) + "\n",
        encoding="utf-8",
    )
    no_items = approve_project_agent_dispatch_plan(config, project_id_for_validation, {})
    assert no_items["ok"] is False

    refreshed_item_plan = refreshed["agent_dispatch_plan"]
    refreshed_item_plan["dispatch_summary"] = "summary"
    refreshed_item_plan["approval_conditions"] = ["Agent execution approval is required before dispatch run."]
    refreshed_item_plan["dispatch_plan"]["dispatch_items"][0]["execution_status"] = "executed"
    resolve_project_agent_dispatch_plan_path(tmp_path, project_id_for_validation).write_text(
        json.dumps(refreshed_item_plan, indent=2) + "\n",
        encoding="utf-8",
    )
    invalid_executed = approve_project_agent_dispatch_plan(config, project_id_for_validation, {})
    assert invalid_executed["ok"] is False

    prepare_project_agent_dispatch_plan(config, project_id_for_validation)
    update_project_agent_dispatch_plan(
        config,
        project_id_for_validation,
        {
            "dispatch_summary": "Approved dispatch plan",
            "approval_conditions": ["Agent execution approval is required before run."],
            "sequencing_notes": ["s1"],
            "dependency_notes": ["d1"],
        },
    )
    approved = approve_project_agent_dispatch_plan(config, project_id_for_validation, {})
    assert approved["ok"] is True
    assert approved["agent_dispatch_plan"]["lifecycle_state"] == "agent_dispatch_plan_approved"
    dossier = read_project_factory_dossier(config, project_id_for_validation)
    assert dossier["dossier"]["lifecycle_state"] == "agent_dispatch_plan_approved"
    assert dossier["dossier"]["next_recommended_action"] == "prepare_validation_execution_plan"


def test_validation_execution_plan_lifecycle_and_validations(tmp_path: Path) -> None:
    config = _config(tmp_path)
    missing = read_project_validation_execution_plan(config, "missing-project")
    assert missing["ok"] is True
    assert missing["validation_execution_plan_exists"] is False

    created = start_new_project_factory(config, _payload(tmp_path))
    missing_dispatch = prepare_project_validation_execution_plan(config, str(created["project"]["project_id"]))
    assert missing_dispatch["ok"] is False
    assert missing_dispatch["error"] == "agent_dispatch_plan_not_found"

    project_id = _seed_github_apply_plan_approved(config, tmp_path)
    prepare_project_agent_dispatch_plan(config, project_id)
    unapproved_dispatch = prepare_project_validation_execution_plan(config, project_id)
    assert unapproved_dispatch["ok"] is False
    assert unapproved_dispatch["error"] == "agent_dispatch_plan_not_approved"

    update_project_agent_dispatch_plan(
        config,
        project_id,
        {"dispatch_summary": "summary", "approval_conditions": ["Agent execution approval is required before run."]},
    )
    approve_project_agent_dispatch_plan(config, project_id, {})
    prepared = prepare_project_validation_execution_plan(config, project_id)
    assert prepared["ok"] is True
    plan_path = resolve_project_validation_execution_plan_path(tmp_path, project_id)
    rendered = json.loads(plan_path.read_text(encoding="utf-8"))
    assert rendered["lifecycle_state"] == "validation_execution_plan_prepared"
    assert rendered["validation_plan"]["validation_items"]
    assert rendered["validation_plan"]["validation_groups"]
    assert rendered["validation_plan"]["evidence_expectations"]
    assert rendered["validation_plan"]["validation_items"][0]["execution_status"] == "not_executed"
    assert rendered["validation_plan"]["validation_items"][0]["evidence_status"] == "not_collected"

    first_count = len(prepared["validation_execution_plan"].get("audit_trail", []))
    updated = update_project_validation_execution_plan(
        config,
        project_id,
        {
            "validation_summary": "validation summary",
            "approval_conditions": ["Validation execution approval is required before run."],
            "manual_validation_notes": ["manual note"],
        },
    )
    assert updated["ok"] is True
    assert updated["validation_execution_plan"]["lifecycle_state"] == "validation_execution_plan_draft_updated"
    assert len(updated["validation_execution_plan"].get("audit_trail", [])) > first_count
    dossier = read_project_factory_dossier(config, project_id)
    assert dossier["dossier"]["lifecycle_state"] == "validation_execution_plan_draft_updated"

    missing_summary = approve_project_validation_execution_plan(config, project_id, {})
    assert missing_summary["ok"] is True
    assert missing_summary["validation_execution_plan"]["lifecycle_state"] == "validation_execution_plan_approved"

    bad_project = _seed_github_apply_plan_approved(config, tmp_path)
    prepare_project_agent_dispatch_plan(config, bad_project)
    update_project_agent_dispatch_plan(
        config,
        bad_project,
        {"dispatch_summary": "summary", "approval_conditions": ["Agent execution approval is required before run."]},
    )
    approve_project_agent_dispatch_plan(config, bad_project, {})
    prepare_project_validation_execution_plan(config, bad_project)
    no_summary = approve_project_validation_execution_plan(config, bad_project, {})
    assert no_summary["ok"] is False
    assert no_summary["error"] == "validation_execution_plan_approval_validation_failed"
    update_project_validation_execution_plan(config, bad_project, {"validation_summary": "summary", "approval_conditions": ["needs review"]})
    missing_condition = approve_project_validation_execution_plan(config, bad_project, {})
    assert missing_condition["ok"] is False

    path = resolve_project_validation_execution_plan_path(tmp_path, bad_project)
    raw = json.loads(path.read_text(encoding="utf-8"))
    raw["validation_summary"] = "summary"
    raw["approval_conditions"] = ["Validation execution approval is required before run."]
    raw["validation_plan"]["validation_items"] = []
    path.write_text(json.dumps(raw, indent=2) + "\n", encoding="utf-8")
    no_items = approve_project_validation_execution_plan(config, bad_project, {})
    assert no_items["ok"] is False

    prepare_project_validation_execution_plan(config, bad_project)
    updated_valid = update_project_validation_execution_plan(
        config,
        bad_project,
        {"validation_summary": "summary", "approval_conditions": ["Validation execution approval is required before run."]},
    )
    tampered = updated_valid["validation_execution_plan"]
    tampered["validation_plan"]["validation_items"][0]["execution_status"] = "executed"
    path.write_text(json.dumps(tampered, indent=2) + "\n", encoding="utf-8")
    executed_fail = approve_project_validation_execution_plan(config, bad_project, {})
    assert executed_fail["ok"] is False

    prepare_project_validation_execution_plan(config, bad_project)
    updated_valid = update_project_validation_execution_plan(
        config,
        bad_project,
        {"validation_summary": "summary", "approval_conditions": ["Validation execution approval is required before run."]},
    )
    tampered = updated_valid["validation_execution_plan"]
    tampered["validation_plan"]["validation_items"][0]["evidence_status"] = "collected"
    path.write_text(json.dumps(tampered, indent=2) + "\n", encoding="utf-8")
    evidence_fail = approve_project_validation_execution_plan(config, bad_project, {})
    assert evidence_fail["ok"] is False

    prepare_project_validation_execution_plan(config, bad_project)
    update_project_validation_execution_plan(
        config,
        bad_project,
        {
            "validation_summary": "Approved validation plan",
            "approval_conditions": ["Validation execution approval is required before run."],
            "sequencing_notes": ["s1"],
            "dependency_notes": ["d1"],
        },
    )
    approved = approve_project_validation_execution_plan(config, bad_project, {})
    assert approved["ok"] is True
    assert approved["validation_execution_plan"]["lifecycle_state"] == "validation_execution_plan_approved"
    assert approved["validation_execution_plan"]["local_only"] is True
    assert approved["validation_execution_plan"]["validation_execution_status"] == "not_requested"
    assert approved["validation_execution_plan"]["audit_trail"]
    dossier = read_project_factory_dossier(config, bad_project)
    assert dossier["dossier"]["lifecycle_state"] == "validation_execution_plan_approved"
    assert dossier["dossier"]["next_recommended_action"] == "prepare_documentation_closeout_plan"


def test_documentation_closeout_plan_lifecycle_and_validations(tmp_path: Path) -> None:
    config = _config(tmp_path)
    missing = read_project_documentation_closeout_plan(config, "missing-project")
    assert missing["ok"] is True
    assert missing["documentation_closeout_plan_exists"] is False

    created = start_new_project_factory(config, _payload(tmp_path))
    missing_validation = prepare_project_documentation_closeout_plan(config, str(created["project"]["project_id"]))
    assert missing_validation["ok"] is False
    assert missing_validation["error"] == "validation_execution_plan_not_found"

    project_id = _seed_github_apply_plan_approved(config, tmp_path)
    prepare_project_agent_dispatch_plan(config, project_id)
    update_project_agent_dispatch_plan(
        config,
        project_id,
        {"dispatch_summary": "summary", "approval_conditions": ["Agent execution approval is required before run."]},
    )
    approve_project_agent_dispatch_plan(config, project_id, {})
    prepare_project_validation_execution_plan(config, project_id)
    unapproved_validation = prepare_project_documentation_closeout_plan(config, project_id)
    assert unapproved_validation["ok"] is False
    assert unapproved_validation["error"] == "validation_execution_plan_not_approved"

    update_project_validation_execution_plan(
        config,
        project_id,
        {"validation_summary": "summary", "approval_conditions": ["Validation execution approval is required before run."]},
    )
    approve_project_validation_execution_plan(config, project_id, {})
    prepared = prepare_project_documentation_closeout_plan(config, project_id)
    assert prepared["ok"] is True
    plan_path = resolve_project_documentation_closeout_plan_path(tmp_path, project_id)
    rendered = json.loads(plan_path.read_text(encoding="utf-8"))
    assert rendered["lifecycle_state"] == "documentation_closeout_plan_prepared"
    assert rendered["documentation_plan"]["documentation_items"]
    assert rendered["documentation_plan"]["evidence_packages"] or rendered["input"]["evidence_expectations"] == []
    assert rendered["documentation_plan"]["closeout_checks"]
    assert any("BUILD_STATE" in str(item.get("title", "")) for item in rendered["documentation_plan"]["documentation_items"])
    assert any("AGENT_CONTEXT" in str(item.get("title", "")) for item in rendered["documentation_plan"]["documentation_items"])
    assert any("ROADMAP" in str(item.get("title", "")) for item in rendered["documentation_plan"]["documentation_items"])
    assert any("LOCAL_OPERATOR_USAGE" in str(item.get("title", "")) for item in rendered["documentation_plan"]["documentation_items"])
    assert rendered["documentation_plan"]["documentation_items"][0]["execution_status"] == "not_executed"
    assert rendered["documentation_plan"]["documentation_items"][0]["evidence_status"] == "not_collected"

    first_count = len(prepared["documentation_closeout_plan"].get("audit_trail", []))
    updated = update_project_documentation_closeout_plan(
        config,
        project_id,
        {
            "closeout_summary": "closeout summary",
            "approval_conditions": ["Documentation execution and project closeout require explicit operator approval."],
        },
    )
    assert updated["ok"] is True
    assert updated["documentation_closeout_plan"]["lifecycle_state"] == "documentation_closeout_plan_draft_updated"
    assert len(updated["documentation_closeout_plan"].get("audit_trail", [])) > first_count
    dossier = read_project_factory_dossier(config, project_id)
    assert dossier["dossier"]["lifecycle_state"] == "documentation_closeout_plan_draft_updated"

    bad_project = _seed_github_apply_plan_approved(config, tmp_path)
    prepare_project_agent_dispatch_plan(config, bad_project)
    update_project_agent_dispatch_plan(
        config,
        bad_project,
        {"dispatch_summary": "summary", "approval_conditions": ["Agent execution approval is required before run."]},
    )
    approve_project_agent_dispatch_plan(config, bad_project, {})
    prepare_project_validation_execution_plan(config, bad_project)
    update_project_validation_execution_plan(
        config,
        bad_project,
        {"validation_summary": "summary", "approval_conditions": ["Validation execution approval is required before run."]},
    )
    approve_project_validation_execution_plan(config, bad_project, {})
    prepare_project_documentation_closeout_plan(config, bad_project)
    no_summary = approve_project_documentation_closeout_plan(config, bad_project, {})
    assert no_summary["ok"] is False

    path = resolve_project_documentation_closeout_plan_path(tmp_path, bad_project)
    raw = json.loads(path.read_text(encoding="utf-8"))
    raw["closeout_summary"] = "summary"
    raw["approval_conditions"] = ["Documentation execution and project closeout require explicit operator approval."]
    raw["documentation_plan"]["documentation_items"] = []
    path.write_text(json.dumps(raw, indent=2) + "\n", encoding="utf-8")
    assert approve_project_documentation_closeout_plan(config, bad_project, {})["ok"] is False

    prepare_project_documentation_closeout_plan(config, bad_project)
    updated_valid = update_project_documentation_closeout_plan(
        config,
        bad_project,
        {
            "closeout_summary": "summary",
            "approval_conditions": ["Documentation execution and project closeout require explicit operator approval."],
        },
    )
    tampered = updated_valid["documentation_closeout_plan"]
    tampered["documentation_plan"]["evidence_packages"] = []
    tampered["evidence_collection_notes"] = []
    path.write_text(json.dumps(tampered, indent=2) + "\n", encoding="utf-8")
    assert approve_project_documentation_closeout_plan(config, bad_project, {})["ok"] is False

    tampered = updated_valid["documentation_closeout_plan"]
    tampered["documentation_plan"]["documentation_items"][0]["execution_status"] = "executed"
    path.write_text(json.dumps(tampered, indent=2) + "\n", encoding="utf-8")
    assert approve_project_documentation_closeout_plan(config, bad_project, {})["ok"] is False

    tampered = updated_valid["documentation_closeout_plan"]
    tampered["documentation_plan"]["documentation_items"][0]["execution_status"] = "not_executed"
    if not tampered["documentation_plan"]["evidence_packages"]:
        prepare_project_documentation_closeout_plan(config, bad_project)
        updated_valid = update_project_documentation_closeout_plan(
            config,
            bad_project,
            {
                "closeout_summary": "summary",
                "approval_conditions": ["Documentation execution and project closeout require explicit operator approval."],
            },
        )
        tampered = updated_valid["documentation_closeout_plan"]
    tampered["documentation_plan"]["evidence_packages"][0]["status"] = "collected"
    path.write_text(json.dumps(tampered, indent=2) + "\n", encoding="utf-8")
    assert approve_project_documentation_closeout_plan(config, bad_project, {})["ok"] is False

    prepare_project_documentation_closeout_plan(config, bad_project)
    update_project_documentation_closeout_plan(
        config,
        bad_project,
        {
            "closeout_summary": "Approved closeout plan",
            "approval_conditions": ["Documentation execution and project closeout require explicit operator approval."],
            "sequencing_notes": ["s1"],
            "dependency_notes": ["d1"],
        },
    )
    approved = approve_project_documentation_closeout_plan(config, bad_project, {})
    assert approved["ok"] is True
    assert approved["documentation_closeout_plan"]["lifecycle_state"] == "documentation_closeout_plan_approved"
    assert approved["documentation_closeout_plan"]["local_only"] is True
    assert approved["documentation_closeout_plan"]["documentation_execution_status"] == "not_requested"
    assert approved["documentation_closeout_plan"]["audit_trail"]
    dossier = read_project_factory_dossier(config, bad_project)
    assert dossier["dossier"]["lifecycle_state"] == "documentation_closeout_plan_approved"
    assert dossier["dossier"]["next_recommended_action"] == "await_explicit_execution_phase_approval"


def test_execution_phase_approval_lifecycle_and_validations(tmp_path: Path) -> None:
    config = _config(tmp_path)
    missing = read_project_execution_phase_approval(config, "missing-project")
    assert missing["ok"] is True
    assert missing["execution_phase_approval_exists"] is False

    created = start_new_project_factory(config, _payload(tmp_path))
    missing_closeout = prepare_project_execution_phase_approval(config, str(created["project"]["project_id"]))
    assert missing_closeout["ok"] is False
    assert missing_closeout["error"] == "documentation_closeout_plan_not_found"

    project_id = _seed_github_apply_plan_approved(config, tmp_path)
    prepare_project_agent_dispatch_plan(config, project_id)
    update_project_agent_dispatch_plan(config, project_id, {"dispatch_summary": "summary", "approval_conditions": ["Agent execution approval is required before run."]})
    approve_project_agent_dispatch_plan(config, project_id, {})
    prepare_project_validation_execution_plan(config, project_id)
    update_project_validation_execution_plan(config, project_id, {"validation_summary": "summary", "approval_conditions": ["Validation execution approval is required before run."]})
    approve_project_validation_execution_plan(config, project_id, {})
    prepare_project_documentation_closeout_plan(config, project_id)
    unapproved_closeout = prepare_project_execution_phase_approval(config, project_id)
    assert unapproved_closeout["ok"] is False
    assert unapproved_closeout["error"] == "documentation_closeout_plan_not_approved"

    update_project_documentation_closeout_plan(
        config,
        project_id,
        {"closeout_summary": "Approved closeout plan", "approval_conditions": ["Documentation execution and project closeout require explicit operator approval."]},
    )
    approve_project_documentation_closeout_plan(config, project_id, {})

    prepared = prepare_project_execution_phase_approval(config, project_id)
    assert prepared["ok"] is True
    approval_path = resolve_project_execution_phase_approval_path(tmp_path, project_id)
    rendered = json.loads(approval_path.read_text(encoding="utf-8"))
    assert rendered["lifecycle_state"] == "execution_phase_approval_prepared"
    assert all(lane["status"] == "blocked" for lane in rendered["execution_lanes"])

    updated = update_project_execution_phase_approval(
        config,
        project_id,
        {
            "overall_acknowledgement": "No execution lanes approved yet.",
            "execution_lanes": [{"lane_id": "github_mutation_execution", "status": "approved", "acknowledgement_text": ""}],
        },
    )
    assert updated["ok"] is True
    assert updated["execution_phase_approval"]["lifecycle_state"] == "execution_phase_approval_draft_updated"

    invalid = approve_project_execution_phase_approval(config, project_id, {})
    assert invalid["ok"] is False
    assert invalid["error"] == "execution_phase_approval_validation_failed"

    update_project_execution_phase_approval(
        config,
        project_id,
        {
            "execution_lanes": [{"lane_id": "github_mutation_execution", "status": "approved", "acknowledgement_text": "Acknowledged and intentionally approved."}],
        },
    )
    approved = approve_project_execution_phase_approval(config, project_id, {})
    assert approved["ok"] is True
    assert approved["execution_phase_approval"]["lifecycle_state"] == "execution_phase_approval_approved"
    dossier = read_project_factory_dossier(config, project_id)
    assert dossier["dossier"]["lifecycle_state"] == "execution_phase_approval_approved"


def test_execution_readiness_reports_blocked_when_required_artifacts_missing(tmp_path: Path) -> None:
    config = _config(tmp_path)
    created = start_new_project_factory(config, _payload(tmp_path))
    project_id = str(created["project"]["project_id"])
    payload = read_project_execution_readiness(config, project_id)
    assert payload["ok"] is True
    assert payload["overall_status"] == "blocked"
    assert "artifact_summary" in payload
    assert "lane_summary" in payload


def test_execution_readiness_reports_pending_approval_when_execution_gate_missing_or_not_approved(tmp_path: Path) -> None:
    config = _config(tmp_path)
    project_id = _seed_github_apply_plan_approved(config, tmp_path)
    prepare_project_agent_dispatch_plan(config, project_id)
    update_project_agent_dispatch_plan(
        config,
        project_id,
        {"dispatch_summary": "summary", "approval_conditions": ["Agent execution approval required."]},
    )
    approve_project_agent_dispatch_plan(config, project_id, {})
    prepare_project_validation_execution_plan(config, project_id)
    update_project_validation_execution_plan(
        config,
        project_id,
        {"validation_summary": "summary", "approval_conditions": ["Validation execution approval required."]},
    )
    approve_project_validation_execution_plan(config, project_id, {})
    prepare_project_documentation_closeout_plan(config, project_id)
    update_project_documentation_closeout_plan(config, project_id, {"closeout_summary": "summary", "approval_conditions": ["closeout approval"]})
    approve_project_documentation_closeout_plan(config, project_id, {})
    payload = read_project_execution_readiness(config, project_id)
    assert payload["overall_status"] == "pending_approval"
    prepare_project_execution_phase_approval(config, project_id)
    payload_after_prepare = read_project_execution_readiness(config, project_id)
    assert payload_after_prepare["overall_status"] == "pending_approval"


def test_execution_readiness_reports_plan_only_approved_when_all_lanes_blocked(tmp_path: Path) -> None:
    config = _config(tmp_path)
    project_id = _seed_github_apply_plan_approved(config, tmp_path)
    prepare_project_agent_dispatch_plan(config, project_id)
    update_project_agent_dispatch_plan(
        config,
        project_id,
        {"dispatch_summary": "summary", "approval_conditions": ["Agent execution approval required."]},
    )
    approve_project_agent_dispatch_plan(config, project_id, {})
    prepare_project_validation_execution_plan(config, project_id)
    update_project_validation_execution_plan(
        config,
        project_id,
        {"validation_summary": "summary", "approval_conditions": ["Validation execution approval required."]},
    )
    approve_project_validation_execution_plan(config, project_id, {})
    prepare_project_documentation_closeout_plan(config, project_id)
    update_project_documentation_closeout_plan(config, project_id, {"closeout_summary": "summary", "approval_conditions": ["closeout approval"]})
    approve_project_documentation_closeout_plan(config, project_id, {})
    prepare_project_execution_phase_approval(config, project_id)
    update_project_execution_phase_approval(config, project_id, {"overall_acknowledgement": "All lanes remain blocked."})
    approve_project_execution_phase_approval(config, project_id, {})
    payload = read_project_execution_readiness(config, project_id)
    assert payload["overall_status"] == "plan_only_approved"


def test_execution_readiness_reports_execution_lanes_approved_with_expected_keys(tmp_path: Path) -> None:
    config = _config(tmp_path)
    project_id = _seed_github_apply_plan_approved(config, tmp_path)
    prepare_project_agent_dispatch_plan(config, project_id)
    update_project_agent_dispatch_plan(
        config,
        project_id,
        {"dispatch_summary": "summary", "approval_conditions": ["Agent execution approval required."]},
    )
    approve_project_agent_dispatch_plan(config, project_id, {})
    prepare_project_validation_execution_plan(config, project_id)
    update_project_validation_execution_plan(
        config,
        project_id,
        {"validation_summary": "summary", "approval_conditions": ["Validation execution approval required."]},
    )
    approve_project_validation_execution_plan(config, project_id, {})
    prepare_project_documentation_closeout_plan(config, project_id)
    update_project_documentation_closeout_plan(config, project_id, {"closeout_summary": "summary", "approval_conditions": ["closeout approval"]})
    approve_project_documentation_closeout_plan(config, project_id, {})
    prepare_project_execution_phase_approval(config, project_id)
    update_project_execution_phase_approval(
        config,
        project_id,
        {"execution_lanes": [{"lane_id": "github_mutation_execution", "status": "approved", "acknowledgement_text": "Approved lane acknowledgement."}]},
    )
    approve_project_execution_phase_approval(config, project_id, {})
    payload = read_project_execution_readiness(config, project_id)
    assert payload["overall_status"] == "execution_lanes_approved"
    assert set(payload["artifact_summary"].keys()) == {
        "factory_dossier",
        "scope_package",
        "architecture_contract",
        "milestone_issue_plan",
        "github_apply_plan",
        "agent_dispatch_plan",
        "validation_execution_plan",
        "documentation_closeout_plan",
        "execution_phase_approval",
    }
    assert set(payload["lane_summary"].keys()) == {
        "github_mutation_execution",
        "validation_command_execution",
        "documentation_update_execution",
        "agent_model_execution",
        "project_closeout_execution",
    }
