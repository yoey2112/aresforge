import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.local_project_queue import add_queue_item, init_project_queue
from aresforge.operator.single_agent_dry_run_executor import (
    SUPPORTED_DRY_RUN_AGENTS,
    run_single_agent_dry_run,
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


def _seed(config: AppConfig, item_id: str = "m129-dry-run") -> None:
    assert init_project_queue(config)["ok"] is True
    assert add_queue_item(
        config,
        item_id=item_id,
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M129 Single-Agent Dry-Run Executor",
        description="Create deterministic local dry-run execution records.",
        status="ready",
        priority="high",
        item_type="feature",
        tags=["milestone:m129", "local-only"],
        completion_requires=["tests_run", "smoke_checks"],
        evidence_required=["commit_hash"],
        notes="Implement dry-run executor without Codex, LLM, GitHub, network, or patches.",
    )["ok"] is True


def _payload(result: dict[str, object]) -> dict[str, object]:
    return result["payload"]  # type: ignore[index]


def test_supported_dry_run_agents_complete_without_external_execution(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed(config)
    (config.artifact_root / "sample").mkdir(parents=True)
    (config.artifact_root / "sample" / "record.json").write_text('{"ok": true}\n', encoding="utf-8")

    for agent_id in SUPPORTED_DRY_RUN_AGENTS:
        payload = _payload(
            run_single_agent_dry_run(config, agent_id=agent_id, item_id="m129-dry-run")
        )

        assert payload["execution_record_type"] == "single_agent_dry_run"
        assert payload["agent_id"] == agent_id
        assert payload["item_id"] == "m129-dry-run"
        assert payload["project_id"] == "aresforge"
        assert payload["dry_run"] is True
        assert payload["real_execution"] is False
        assert payload["status"] == "completed"
        assert payload["mutation_performed"] is False
        assert payload["external_execution_performed"] is False
        assert payload["model_execution_performed"] is False
        assert payload["github_execution_performed"] is False
        assert payload["patch_application_performed"] is False
        assert payload["local_only"] is True
        assert "execute_codex" in payload["forbidden_capabilities_blocked"]
        assert "apply_patch" in payload["forbidden_capabilities_blocked"]


def test_blocked_agent_does_not_produce_successful_execution(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed(config)

    result = run_single_agent_dry_run(
        config,
        agent_id="codex-dispatch-agent",
        item_id="m129-dry-run",
    )
    payload = _payload(result)

    assert result["ok"] is False
    assert payload["status"] == "blocked"
    assert any("not supported" in error for error in payload["errors"])
    assert payload["external_execution_performed"] is False
    assert payload["model_execution_performed"] is False
    assert payload["github_execution_performed"] is False
    assert payload["patch_application_performed"] is False


def test_unknown_agent_and_missing_item_are_blocked(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed(config)

    payload = _payload(
        run_single_agent_dry_run(config, agent_id="unknown-agent", item_id="missing-item")
    )

    assert payload["status"] == "blocked"
    assert "Queue item not found: missing-item" in payload["errors"]
    assert "Agent is not registered: unknown-agent" in payload["errors"]


def test_output_writes_only_dry_run_artifact_and_respects_force(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed(config)
    output = tmp_path / "artifacts" / "dry-runs" / "m129.json"

    first = run_single_agent_dry_run(
        config,
        agent_id="validation-agent",
        item_id="m129-dry-run",
        output=output,
    )
    duplicate = run_single_agent_dry_run(
        config,
        agent_id="validation-agent",
        item_id="m129-dry-run",
        output=output,
    )
    forced = run_single_agent_dry_run(
        config,
        agent_id="validation-agent",
        item_id="m129-dry-run",
        output=output,
        force=True,
    )
    written = json.loads(output.read_text(encoding="utf-8"))

    assert first["ok"] is True
    assert first["payload"]["mutation_performed"] is True  # type: ignore[index]
    assert first["payload"]["artifacts_created"] == [str(output)]  # type: ignore[index]
    assert duplicate["ok"] is False
    assert duplicate["payload"]["mutation_performed"] is False  # type: ignore[index]
    assert any("Output file already exists" in error for error in duplicate["payload"]["errors"])  # type: ignore[index]
    assert forced["ok"] is True
    assert written["execution_record_type"] == "single_agent_dry_run"
    assert written["mutation_performed"] is True


def test_plan_path_is_loaded_for_queue_planner_agent(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed(config)
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(
        json.dumps(
            {
                "plan_type": "agent_orchestration_plan",
                "blocked": False,
                "steps": [
                    {"agent_id": "queue-planner-agent"},
                    {"agent_id": "validation-agent"},
                ],
            }
        ),
        encoding="utf-8",
    )

    payload = _payload(
        run_single_agent_dry_run(
            config,
            agent_id="queue-planner-agent",
            item_id="m129-dry-run",
            plan_path=plan_path,
        )
    )

    assert payload["status"] == "completed"
    assert payload["inputs"]["plan_loaded"] is True  # type: ignore[index]
    assert payload["outputs"]["planned_steps"] == ["queue-planner-agent", "validation-agent"]  # type: ignore[index]
