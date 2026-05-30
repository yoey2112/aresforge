import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.local_project_queue import add_queue_item, init_project_queue
from aresforge.operator.single_agent_real_executor import (
    SUPPORTED_REAL_AGENTS,
    run_single_agent_real_execution,
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


def _seed(config: AppConfig, item_id: str = "m130-real-run") -> None:
    assert init_project_queue(config)["ok"] is True
    assert add_queue_item(
        config,
        item_id=item_id,
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M130 Single-Agent Real Executor",
        description="Create deterministic low-risk local real execution records.",
        status="ready",
        priority="high",
        item_type="feature",
        tags=["milestone:m130", "local-only"],
        completion_requires=["tests_run", "smoke_checks"],
        evidence_required=["commit_hash"],
        notes="Implement real executor without Codex, LLM, GitHub, network, or patches.",
    )["ok"] is True


def _payload(result: dict[str, object]) -> dict[str, object]:
    return result["payload"]  # type: ignore[index]


def test_supported_real_agents_write_local_execution_records_only(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed(config)
    (config.artifact_root / "sample").mkdir(parents=True)
    (config.artifact_root / "sample" / "record.json").write_text('{"ok": true}\n', encoding="utf-8")

    for agent_id in SUPPORTED_REAL_AGENTS:
        result = run_single_agent_real_execution(
            config,
            agent_id=agent_id,
            item_id="m130-real-run",
            require_machine_gates=True,
        )
        payload = _payload(result)

        assert result["ok"] is True
        assert payload["execution_record_type"] == "single_agent_real_execution"
        assert payload["agent_id"] == agent_id
        assert payload["item_id"] == "m130-real-run"
        assert payload["project_id"] == "aresforge"
        assert payload["dry_run"] is False
        assert payload["real_execution"] is True
        assert payload["status"] == "completed"
        assert payload["machine_gates_passed"] is True
        assert all(gate["passed"] for gate in payload["machine_gates_checked"])  # type: ignore[index]
        assert payload["mutation_performed"] is True
        assert payload["mutation_scope"] == "local_execution_record"
        assert payload["artifacts_created"]
        assert Path(payload["artifacts_created"][0]).exists()  # type: ignore[index]
        assert payload["external_execution_performed"] is False
        assert payload["model_execution_performed"] is False
        assert payload["github_execution_performed"] is False
        assert payload["patch_application_performed"] is False
        assert payload["local_only"] is True


def test_blocked_high_risk_agents_do_not_write_execution_records(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed(config)

    for agent_id in (
        "codex-dispatch-agent",
        "local-llm-advisory-agent",
        "documentation-agent",
        "github-sync-agent",
    ):
        result = run_single_agent_real_execution(
            config,
            agent_id=agent_id,
            item_id="m130-real-run",
            require_machine_gates=True,
        )
        payload = _payload(result)

        assert result["ok"] is False
        assert payload["status"] == "blocked"
        assert payload["mutation_performed"] is False
        assert payload["artifacts_created"] == []
        assert payload["external_execution_performed"] is False
        assert payload["model_execution_performed"] is False
        assert payload["github_execution_performed"] is False
        assert payload["patch_application_performed"] is False
        assert payload["machine_gates_passed"] is False


def test_machine_gate_enforcement_blocks_missing_item(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed(config)

    result = run_single_agent_real_execution(
        config,
        agent_id="artifact-registry-agent",
        item_id="missing-item",
        require_machine_gates=True,
    )
    payload = _payload(result)

    assert result["ok"] is False
    assert payload["status"] == "blocked"
    assert payload["machine_gates_passed"] is False
    assert "queue_item_exists" in {
        gate["gate_id"] for gate in payload["machine_gates_checked"] if not gate["passed"]  # type: ignore[index]
    }
    assert payload["mutation_performed"] is False


def test_output_respects_no_overwrite_without_force(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed(config)
    output = tmp_path / "artifacts" / "real-runs" / "m130.json"

    first = run_single_agent_real_execution(
        config,
        agent_id="validation-agent",
        item_id="m130-real-run",
        output=output,
    )
    duplicate = run_single_agent_real_execution(
        config,
        agent_id="validation-agent",
        item_id="m130-real-run",
        output=output,
    )
    forced = run_single_agent_real_execution(
        config,
        agent_id="validation-agent",
        item_id="m130-real-run",
        output=output,
        force=True,
    )
    written = json.loads(output.read_text(encoding="utf-8"))

    assert first["ok"] is True
    assert duplicate["ok"] is False
    assert duplicate["payload"]["mutation_performed"] is False  # type: ignore[index]
    assert any("Output file already exists" in error for error in duplicate["payload"]["errors"])  # type: ignore[index]
    assert forced["ok"] is True
    assert written["execution_record_type"] == "single_agent_real_execution"
    assert written["mutation_performed"] is True
