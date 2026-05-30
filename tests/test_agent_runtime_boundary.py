import json

from aresforge.config import AppConfig
from aresforge.operator.agent_runtime_boundary import (
    AGENT_RUNTIME_BOUNDARY_VERSION,
    build_agent_runtime_boundary_contract,
    inspect_agent_runtime_boundary,
)


def _config(tmp_path):
    return AppConfig(
        repo_root=tmp_path,
        db_host="127.0.0.1",
        db_port=5433,
        db_name="aresforge",
        db_user="aresforge",
        db_password="aresforge",
        ollama_base_url="http://127.0.0.1:11434",
        ollama_model="qwen2.5:32b",
        artifact_root=tmp_path / "artifacts",
        prompts_dir=tmp_path / "artifacts" / "prompts",
        evidence_dir=tmp_path / "artifacts" / "evidence",
        codex_handoffs_dir=tmp_path / "artifacts" / "codex-handoffs",
        github_owner="",
        github_repo="",
    )


def test_agent_runtime_boundary_contract_has_stable_top_level_fields(tmp_path):
    config = _config(tmp_path)
    payload = build_agent_runtime_boundary_contract(config)

    assert list(payload.keys()) == [
        "contract_type",
        "generated",
        "agent_boundary_version",
        "repo_root",
        "supported_execution_modes",
        "supported_autonomy_levels",
        "supported_safety_classes",
        "runtime_boundary_model",
        "field_definitions",
        "allowed_capability_catalog",
        "forbidden_capability_catalog",
        "mutation_scope_catalog",
        "network_scope_catalog",
        "model_scope_catalog",
        "evidence_requirements",
        "default_runtime_limits",
        "default_timeout_policy",
        "default_retry_policy",
        "local_only",
        "read_only",
        "execution_allowed",
        "execution_performed",
        "next_safe_action",
        "boundary_confirmations",
    ]
    assert payload["contract_type"] == "agent_runtime_boundary"
    assert payload["generated"] is True
    assert payload["agent_boundary_version"] == AGENT_RUNTIME_BOUNDARY_VERSION
    assert payload["local_only"] is True
    assert payload["read_only"] is True
    assert payload["execution_allowed"] is False
    assert payload["execution_performed"] is False


def test_agent_runtime_boundary_defines_required_schema_terms(tmp_path):
    config = _config(tmp_path)
    payload = build_agent_runtime_boundary_contract(config)

    field_definitions = payload["field_definitions"]
    for field in (
        "agent_id",
        "agent_type",
        "execution_mode",
        "input_contract",
        "output_contract",
        "allowed_capabilities",
        "forbidden_capabilities",
        "mutation_scope",
        "network_scope",
        "model_scope",
        "timeout_policy",
        "retry_policy",
        "evidence_requirements",
        "safety_class",
        "autonomy_level",
    ):
        assert field in field_definitions
        assert field_definitions[field]["required"] is True


def test_agent_runtime_boundary_blocks_execution_capabilities(tmp_path):
    config = _config(tmp_path)
    payload = build_agent_runtime_boundary_contract(config)

    forbidden = payload["forbidden_capability_catalog"]
    for capability in (
        "execute_codex",
        "execute_ollama_prompt",
        "execute_local_llm",
        "execute_documentation_agent",
        "apply_patch",
        "call_github_api",
        "call_gh",
        "call_external_network",
        "automatic_next_item_execution",
    ):
        assert capability in forbidden

    assert payload["default_runtime_limits"]["execution_allowed_by_this_contract"] is False
    assert payload["default_runtime_limits"]["max_items_per_run"] == 1
    assert payload["default_retry_policy"]["automatic_retries_allowed"] is False


def test_agent_runtime_boundary_json_output_is_parseable_and_deterministic(tmp_path):
    config = _config(tmp_path)
    first = inspect_agent_runtime_boundary(config, output_format="json")
    second = inspect_agent_runtime_boundary(config, output_format="json")

    assert first["ok"] is True
    assert first["stdout"] == second["stdout"]
    parsed = json.loads(first["stdout"])
    assert parsed["contract_type"] == "agent_runtime_boundary"
    assert parsed["supported_autonomy_levels"] == [
        "manual_only",
        "recommendation_only",
        "operator_approved_single_step",
        "operator_approved_bounded_run",
    ]
    assert parsed["supported_safety_classes"] == [
        "read_only",
        "local_file_write",
        "local_provider_probe",
        "operator_gated_local_provider_execution",
        "external_mutation_prohibited",
    ]


def test_agent_runtime_boundary_rejects_unknown_format(tmp_path):
    config = _config(tmp_path)
    result = inspect_agent_runtime_boundary(config, output_format="yaml")

    assert result["ok"] is False
    assert result["error"] == "invalid_format"
