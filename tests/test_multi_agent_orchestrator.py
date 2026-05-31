import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.local_project_queue import add_queue_item, init_project_queue
from aresforge.operator.multi_agent_orchestrator import run_multi_agent_orchestration


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


def _seed(config: AppConfig, *, item_id: str = "m138-orchestration", item_type: str = "feature") -> None:
    assert init_project_queue(config)["ok"] is True
    assert add_queue_item(
        config,
        item_id=item_id,
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M138 Multi-Agent Orchestrator v1",
        description="Run multi-agent orchestration plans step by step.",
        status="ready",
        priority="high",
        item_type=item_type,
        tags=["milestone:m138", "local-only"],
        completion_requires=["tests_run", "smoke_checks"],
        evidence_required=["commit_hash"],
        notes="Validation evidence present.",
    )["ok"] is True


def _plan(config: AppConfig, item_id: str, agents: list[str]) -> Path:
    path = config.repo_root / "artifacts" / "plans" / f"{item_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "plan_type": "agent_orchestration_plan",
                "item_id": item_id,
                "blocked": False,
                "steps": [
                    {
                        "step_id": f"step-{index:02d}-{agent_id}",
                        "sequence": index,
                        "agent_id": agent_id,
                        "forbidden_capabilities": ["execute_codex", "call_github_api", "apply_patch"],
                    }
                    for index, agent_id in enumerate(agents, start=1)
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def _payload(result: dict[str, object]) -> dict[str, object]:
    return result["payload"]  # type: ignore[index]


def test_dry_run_orchestration_completes_plan_without_real_execution(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed(config, item_type="documentation")
    plan = _plan(
        config,
        "m138-orchestration",
        ["queue-planner-agent", "documentation-agent", "validation-agent"],
    )

    payload = _payload(
        run_multi_agent_orchestration(config, item_id="m138-orchestration", plan_path=plan)
    )

    assert payload["execution_record_type"] == "multi_agent_orchestration_v1"
    assert payload["dry_run"] is True
    assert payload["status"] == "completed"
    assert payload["steps_total"] == 3
    assert payload["steps_attempted"] == 3
    assert payload["steps_completed"] == 3
    assert payload["steps_blocked"] == 0
    assert payload["local_llm_execution_performed"] is False
    assert payload["codex_execution_performed"] is False
    assert payload["github_execution_performed"] is False
    assert payload["patch_application_performed"] is False
    assert payload["queue_mutation_performed"] is False
    assert payload["artifacts_created"]


def test_low_risk_real_orchestration_writes_local_execution_records(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed(config, item_type="validation")
    plan = _plan(config, "m138-orchestration", ["queue-planner-agent", "validation-agent"])

    payload = _payload(
        run_multi_agent_orchestration(
            config,
            item_id="m138-orchestration",
            plan_path=plan,
            allow_low_risk_real=True,
        )
    )

    assert payload["dry_run"] is False
    assert payload["status"] == "completed"
    assert payload["steps_attempted"] == 2
    assert payload["steps_completed"] == 2
    assert all(result["mode"] == "low_risk_real" for result in payload["step_results"])  # type: ignore[index]
    assert len(payload["artifacts_created"]) >= 3
    assert payload["queue_mutation_performed"] is False


def test_high_risk_real_step_blocks_without_specific_allow_flag(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed(config)
    plan = _plan(config, "m138-orchestration", ["queue-planner-agent", "codex-dispatch-agent", "validation-agent"])

    payload = _payload(
        run_multi_agent_orchestration(
            config,
            item_id="m138-orchestration",
            plan_path=plan,
            allow_low_risk_real=True,
        )
    )

    assert payload["status"] == "blocked"
    assert payload["blocked"] is True
    assert payload["steps_attempted"] == 2
    assert payload["steps_completed"] == 1
    assert payload["steps_blocked"] == 1
    assert payload["step_results"][1]["agent_id"] == "codex-dispatch-agent"  # type: ignore[index]
    assert payload["codex_execution_performed"] is False


def test_orchestration_stops_on_first_gate_failure(tmp_path: Path) -> None:
    config = _config(tmp_path)
    plan = _plan(config, "missing-item", ["queue-planner-agent", "validation-agent"])

    payload = _payload(
        run_multi_agent_orchestration(config, item_id="missing-item", plan_path=plan)
    )

    assert payload["status"] == "blocked"
    assert payload["steps_attempted"] == 1
    assert payload["steps_completed"] == 0
    assert payload["steps_blocked"] == 1
    assert "queue_item_exists" in payload["step_results"][0]["machine_gates_checked"][0]["checks_failed"]  # type: ignore[index]


def test_max_steps_limits_attempted_timeline(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed(config)
    plan = _plan(
        config,
        "m138-orchestration",
        ["queue-planner-agent", "artifact-registry-agent", "validation-agent"],
    )

    payload = _payload(
        run_multi_agent_orchestration(
            config,
            item_id="m138-orchestration",
            plan_path=plan,
            max_steps=2,
        )
    )

    assert payload["status"] == "max_steps_reached"
    assert payload["steps_total"] == 3
    assert payload["steps_attempted"] == 2
    assert payload["steps_completed"] == 2
    assert payload["blocked"] is False


def test_output_path_writes_orchestration_artifact(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed(config)
    plan = _plan(config, "m138-orchestration", ["queue-planner-agent"])
    output = tmp_path / "artifacts" / "multi-agent" / "m138.json"

    result = run_multi_agent_orchestration(
        config,
        item_id="m138-orchestration",
        plan_path=plan,
        output=output,
    )
    written = json.loads(output.read_text(encoding="utf-8"))

    assert result["ok"] is True
    assert result["wrote_output_file"] is True
    assert written["execution_record_type"] == "multi_agent_orchestration_v1"
    assert written["artifacts_created"] == [str(output)]
