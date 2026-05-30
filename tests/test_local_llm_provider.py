import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.local_llm_provider import build_local_llm_provider_contract
from aresforge.operator.local_project_factory import update_local_llm_environment_contract


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


def test_local_llm_provider_contract_reads_ollama_metadata_without_provider_call(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert update_local_llm_environment_contract(
        config,
        {
            "local_llm_provider": "ollama",
            "provider_base_url": "http://127.0.0.1:11434",
            "reasoning_model": "qwen-reasoning-local",
            "coding_model": "qwen-coding-local",
            "fallback_model": "qwen-fallback-local",
            "request_timeout_seconds": 90,
            "health_check_enabled": True,
            "execution_enabled": False,
            "operator_gate_required": True,
        },
    )["ok"] is True

    payload = build_local_llm_provider_contract(config)

    assert payload["ok"] is True
    assert payload["provider_contract_ready"] is True
    assert payload["initial_provider_target"] == "ollama"
    assert payload["provider_base_url"] == "http://127.0.0.1:11434"
    assert payload["request_timeout_seconds"] == 90
    assert payload["health_check_contract"]["allowed_endpoint"] == "/api/tags"
    assert "/api/generate" in payload["health_check_contract"]["forbidden_endpoints"]
    assert payload["health_check_contract"]["inference_tested"] is False
    assert payload["safety_boundary"]["provider_invocation_allowed_from_this_command"] is False
    assert payload["safety_boundary"]["repo_mutation_allowed"] is False
    assert payload["safety_boundary"]["automatic_next_item_execution_allowed"] is False
    models = {model["field"]: model for model in payload["model_selection_contract"]["models"]}
    assert models["reasoning_model"]["model_identifier"] == "qwen-reasoning-local"
    assert models["reasoning_model"]["role"] == "reasoning"
    assert models["coding_model"]["model_identifier"] == "qwen-coding-local"
    assert models["coding_model"]["role"] == "coding"
    assert models["fallback_model"]["may_execute_automatically"] is False


def test_local_llm_provider_contract_rejects_non_local_ollama_url(tmp_path: Path) -> None:
    config = _config(tmp_path)
    environment_path = tmp_path / ".aresforge" / "local_llm_environment.json"
    environment_path.parent.mkdir(parents=True, exist_ok=True)
    environment_path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "local_llm_provider": "ollama",
                "provider_base_url": "https://example.com",
                "reasoning_model": "qwen-reasoning-local",
                "coding_model": "qwen-coding-local",
                "fallback_model": "",
                "max_context_tokens": None,
                "request_timeout_seconds": 90,
                "health_check_enabled": False,
                "execution_enabled": False,
                "operator_gate_required": True,
                "notes": "",
                "updated_at": "",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    payload = build_local_llm_provider_contract(config)

    assert payload["ok"] is True
    assert payload["provider_contract_ready"] is False
    assert any("localhost" in blocker for blocker in payload["blockers"])
    assert payload["safety_boundary"]["github_api_allowed"] is False
    assert payload["safety_boundary"]["gh_allowed"] is False


def test_local_llm_environment_update_marks_non_local_provider_url_unsupported(tmp_path: Path) -> None:
    config = _config(tmp_path)
    payload = update_local_llm_environment_contract(
        config,
        {
            "local_llm_provider": "ollama",
            "provider_base_url": "https://example.com",
            "operator_gate_required": True,
        },
    )

    assert payload["ok"] is True
    assert payload["provider_availability_status"] == "unsupported"
    assert payload["provider_configuration_status"] == "non_local_provider_url"
    assert payload["execution_allowed"] is False
