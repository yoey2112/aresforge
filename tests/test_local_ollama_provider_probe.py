import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.local_ollama_provider_probe import probe_local_ollama_provider


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


def _write_environment(tmp_path: Path, **overrides: object) -> Path:
    path = tmp_path / ".aresforge" / "local_llm_environment.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "1.0",
        "local_llm_provider": "ollama",
        "provider_base_url": "http://127.0.0.1:11434",
        "reasoning_model": "qwen-reason",
        "coding_model": "qwen-code",
        "fallback_model": "",
        "max_context_tokens": None,
        "request_timeout_seconds": 5,
        "health_check_enabled": True,
        "execution_enabled": False,
        "operator_gate_required": True,
        "notes": "",
        "updated_at": "2026-05-30T00:00:00+00:00",
    }
    payload.update(overrides)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


class _Response:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")


def _payload(result: dict[str, object]) -> dict[str, object]:
    return result["payload"]  # type: ignore[index]


def test_no_network_probe_reads_configuration_without_http(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _write_environment(tmp_path)
    called = {"http": False}

    payload = _payload(
        probe_local_ollama_provider(
            config,
            no_network=True,
            output_format="json",
            urlopen_fn=lambda *_args, **_kwargs: called.__setitem__("http", True),
        )
    )

    assert called["http"] is False
    assert payload["probe_type"] == "local_ollama_provider_probe"
    assert payload["probed"] is True
    assert payload["blocked"] is False
    assert payload["probe_method"] == "config_only_no_network"
    assert payload["network_execution_performed"] is False
    assert payload["prompt_execution_performed"] is False
    assert payload["coding_execution_performed"] is False
    assert payload["reasoning_execution_performed"] is False
    assert payload["advisory_execution_allowed"] is False
    assert payload["configured_model_profiles"][0]["model"] == "qwen-reason"  # type: ignore[index]


def test_loopback_probe_lists_models_without_prompt_execution(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _write_environment(tmp_path)
    seen: dict[str, object] = {}

    def fake_urlopen(req, timeout):
        seen["url"] = req.full_url
        seen["timeout"] = timeout
        return _Response(
            {
                "models": [
                    {
                        "name": "qwen-reason",
                        "model": "qwen-reason",
                        "details": {"family": "qwen", "parameter_size": "32B"},
                    }
                ]
            }
        )

    payload = _payload(probe_local_ollama_provider(config, output_format="json", urlopen_fn=fake_urlopen))

    assert payload["ok"] is True
    assert payload["ollama_detected"] is True
    assert payload["probe_method"] == "loopback_ollama_tags"
    assert payload["network_execution_performed"] is True
    assert payload["prompt_execution_performed"] is False
    assert payload["available_models"][0]["name"] == "qwen-reason"  # type: ignore[index]
    assert payload["reasoning_model_recommendation"]["status"] == "configured_and_visible"  # type: ignore[index]
    assert seen["url"] == "http://127.0.0.1:11434/api/tags"


def test_non_loopback_url_blocks_network_probe(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _write_environment(tmp_path, provider_base_url="https://example.com:11434")
    called = {"http": False}

    payload = _payload(
        probe_local_ollama_provider(
            config,
            output_format="json",
            urlopen_fn=lambda *_args, **_kwargs: called.__setitem__("http", True),
        )
    )

    assert called["http"] is False
    assert payload["ok"] is False
    assert payload["probed"] is False
    assert payload["blocked"] is True
    assert payload["network_execution_performed"] is False
    assert any("not loopback" in reason for reason in payload["blocked_reasons"])  # type: ignore[union-attr]


def test_output_path_and_no_overwrite(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _write_environment(tmp_path)
    output = tmp_path / "artifacts" / "probes" / "ollama.json"

    first = _payload(probe_local_ollama_provider(config, output=output, no_network=True, output_format="json"))
    duplicate = _payload(probe_local_ollama_provider(config, output=output, no_network=True, output_format="json"))
    forced = _payload(
        probe_local_ollama_provider(config, output=output, no_network=True, output_format="json", force=True)
    )
    written = json.loads(output.read_text(encoding="utf-8"))

    assert first["probed"] is True
    assert first["output_path"] == str(output)
    assert duplicate["probed"] is False
    assert duplicate["blocked"] is True
    assert any("already exists" in reason for reason in duplicate["blocked_reasons"])  # type: ignore[union-attr]
    assert forced["probed"] is True
    assert written["probe_type"] == "local_ollama_provider_probe"


def test_custom_config_path_is_supported(tmp_path: Path) -> None:
    config = _config(tmp_path)
    custom = tmp_path / "operator" / "llm.json"
    custom.parent.mkdir(parents=True, exist_ok=True)
    custom.write_text(
        json.dumps(
            {
                "local_llm_provider": "ollama",
                "provider_base_url": "http://localhost:11434",
                "reasoning_model": "local-reason",
                "coding_model": "local-code",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    payload = _payload(probe_local_ollama_provider(config, config_path=custom, no_network=True, output_format="json"))

    assert payload["config_path"] == str(custom)
    assert payload["provider_base_url"] == "http://localhost:11434"
    assert payload["coding_model_recommendation"]["model"] == "local-code"  # type: ignore[index]
