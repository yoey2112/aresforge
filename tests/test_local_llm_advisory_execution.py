import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.local_llm_advisory_execution import run_local_llm_advisory_execution
from aresforge.operator.local_project_factory import update_local_llm_environment_contract
from aresforge.operator.local_project_queue import add_queue_item, init_project_queue


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


def _seed(config: AppConfig, *, dependency_done: bool = True) -> None:
    assert init_project_queue(config)["ok"] is True
    assert add_queue_item(
        config,
        item_id="m133-documentation-agent-autonomous-apply-for-docs-only-patches",
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M133 dependency",
        status="done" if dependency_done else "ready",
        priority="high",
        item_type="documentation",
    )["ok"] is True
    assert add_queue_item(
        config,
        item_id="m134-local-llm-advisory-execution",
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M134 Local LLM Advisory Execution",
        description="Execute local LLM advisory requests when machine gates pass.",
        status="ready",
        priority="high",
        item_type="feature",
        tags=["milestone:m134", "local-llm-advisory", "local-only"],
        dependencies=["m133-documentation-agent-autonomous-apply-for-docs-only-patches"],
        notes="Validation commands are available for local advisory execution.",
    )["ok"] is True


def _artifact(config: AppConfig, *, item_id: str = "m134-local-llm-advisory-execution") -> Path:
    path = config.repo_root / "artifacts" / "manual" / "sample-local-llm-advisory.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "artifact_type": "local_llm_advisory_request",
                "item_id": item_id,
                "local_only": True,
                "execution_allowed": False,
                "execution_performed": False,
                "local_llm_execution_performed": False,
                "patch_application_allowed": False,
                "advisory_prompt": "Review this M134 implementation boundary. Do not mutate files.",
                "requested_model_profile": "qwen2.5:32b",
                "validation_commands": ["python -m pytest tests/test_local_llm_advisory_execution.py"],
                "tests_reported": ["python -m pytest tests/test_local_llm_advisory_execution.py -> passed"],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


class _FakeProvider:
    provider_name = "ollama"

    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def generate(self, *, model: str, prompt: str, timeout_seconds: int) -> str:
        self.calls.append({"model": model, "prompt": prompt, "timeout_seconds": timeout_seconds})
        return '{"summary":"advisory only","patch_application_allowed":false}'


def _payload(result: dict[str, object]) -> dict[str, object]:
    return result["payload"]  # type: ignore[index]


def test_dry_run_checks_gates_without_provider_call(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed(config)
    artifact = _artifact(config)
    provider = _FakeProvider()

    payload = _payload(
        run_local_llm_advisory_execution(
            config,
            item_id="m134-local-llm-advisory-execution",
            artifact_path=artifact,
            dry_run=True,
            provider_client=provider,
        )
    )

    assert payload["execution_record_type"] == "local_llm_advisory_execution"
    assert payload["dry_run"] is True
    assert payload["executed"] is False
    assert payload["blocked"] is False
    assert payload["machine_gates_checked"] is True
    assert payload["machine_gates_passed"] is True
    assert payload["response_artifact_path"] == ""
    assert payload["advisory_only"] is True
    assert payload["patch_application_performed"] is False
    assert payload["queue_mutation_performed"] is False
    assert provider.calls == []


def test_provider_mock_writes_response_artifact(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed(config)
    artifact = _artifact(config)
    provider = _FakeProvider()

    payload = _payload(
        run_local_llm_advisory_execution(
            config,
            item_id="m134-local-llm-advisory-execution",
            artifact_path=artifact,
            provider_client=provider,
            timeout_seconds=30,
        )
    )
    response_path = Path(str(payload["response_artifact_path"]))
    response = json.loads(response_path.read_text(encoding="utf-8"))

    assert payload["executed"] is True
    assert payload["blocked"] is False
    assert payload["response_summary"].startswith('{"summary"')
    assert response["artifact_type"] == "local_llm_advisory_response"
    assert response["advisory_only"] is True
    assert response["patch_application_performed"] is False
    assert response["queue_mutation_performed"] is False
    assert provider.calls == [
        {
            "model": "qwen2.5:32b",
            "prompt": "Review this M134 implementation boundary. Do not mutate files.",
            "timeout_seconds": 30,
        }
    ]


def test_machine_gate_failure_blocks_execution(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed(config, dependency_done=False)
    artifact = _artifact(config)
    provider = _FakeProvider()

    payload = _payload(
        run_local_llm_advisory_execution(
            config,
            item_id="m134-local-llm-advisory-execution",
            artifact_path=artifact,
            provider_client=provider,
        )
    )

    assert payload["blocked"] is True
    assert payload["executed"] is False
    assert payload["machine_gates_passed"] is False
    assert any("local_llm_execution did not pass" in reason for reason in payload["blocked_reasons"])
    assert provider.calls == []


def test_remote_provider_name_is_blocked(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed(config)
    artifact = _artifact(config)
    provider = _FakeProvider()

    payload = _payload(
        run_local_llm_advisory_execution(
            config,
            item_id="m134-local-llm-advisory-execution",
            artifact_path=artifact,
            provider="openai",
            provider_client=provider,
        )
    )

    assert payload["blocked"] is True
    assert payload["executed"] is False
    assert any("supports only local Ollama" in reason for reason in payload["blocked_reasons"])
    assert provider.calls == []


def test_remote_ollama_url_is_blocked(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed(config)
    artifact = _artifact(config)
    update_local_llm_environment_contract(
        config,
        {
            "local_llm_provider": "ollama",
            "provider_base_url": "https://example.com",
            "reasoning_model": "qwen2.5:32b",
            "operator_gate_required": True,
        },
    )
    provider = _FakeProvider()

    payload = _payload(
        run_local_llm_advisory_execution(
            config,
            item_id="m134-local-llm-advisory-execution",
            artifact_path=artifact,
            provider_client=provider,
        )
    )

    assert payload["blocked"] is True
    assert payload["executed"] is False
    assert any("localhost" in reason for reason in payload["blocked_reasons"])
    assert provider.calls == []
