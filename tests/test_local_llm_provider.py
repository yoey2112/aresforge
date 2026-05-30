import json
from pathlib import Path
from urllib import error, request

from aresforge.config import AppConfig
from aresforge.operator.local_llm_provider import (
    build_local_llm_provider_contract,
    build_ollama_health_and_model_inspection,
)
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


class _FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")


def test_ollama_health_model_inspection_lists_models_without_generation(tmp_path: Path) -> None:
    config = _config(tmp_path)
    seen: dict[str, object] = {}

    def fake_urlopen(req: request.Request, timeout: int) -> _FakeResponse:
        seen["url"] = req.full_url
        seen["method"] = req.get_method()
        seen["timeout"] = timeout
        return _FakeResponse(
            {
                "models": [
                    {
                        "name": "qwen2.5:32b",
                        "model": "qwen2.5:32b",
                        "modified_at": "2026-05-30T00:00:00Z",
                        "size": 123,
                        "digest": "abc",
                        "details": {
                            "family": "qwen2",
                            "parameter_size": "32B",
                            "quantization_level": "Q4_K_M",
                        },
                    }
                ]
            }
        )

    payload = build_ollama_health_and_model_inspection(config, urlopen_fn=fake_urlopen)

    assert payload["ok"] is True
    assert payload["available"] is True
    assert payload["endpoint"].endswith("/api/tags")
    assert seen["url"].endswith("/api/tags")
    assert seen["method"] == "GET"
    assert payload["models"][0]["name"] == "qwen2.5:32b"
    assert payload["models"][0]["may_generate_from_this_inspection"] is False
    assert payload["model_inspection_contract"]["generation_invoked"] is False
    assert payload["safety_boundary"]["generation_allowed"] is False
    assert payload["safety_boundary"]["repo_mutation_allowed"] is False


def test_ollama_health_model_inspection_handles_offline_without_blocking(tmp_path: Path) -> None:
    config = _config(tmp_path)

    def fake_urlopen(_req: request.Request, timeout: int) -> _FakeResponse:
        raise error.URLError("connection refused")

    payload = build_ollama_health_and_model_inspection(config, urlopen_fn=fake_urlopen)

    assert payload["ok"] is True
    assert payload["available"] is False
    assert payload["models"] == []
    assert "unavailable" in payload["error_summary"]
    assert payload["blockers"] == []
    assert "normal project readiness remains unaffected" in payload["warnings"][0]
    assert payload["safety_boundary"]["automatic_next_item_execution_allowed"] is False
