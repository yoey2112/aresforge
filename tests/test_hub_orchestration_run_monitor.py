import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.hub.api import get_orchestration_run_monitor
from aresforge.operator.local_project_queue import add_queue_item, init_project_queue
from aresforge.operator.multi_agent_orchestrator import run_multi_agent_orchestration
from aresforge.operator.orchestration_run_monitor import inspect_orchestration_run_monitor


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


def _seed_queue(config: AppConfig) -> None:
    assert init_project_queue(config)["ok"] is True
    for item_id, status, dependencies in (
        ("m140-orchestrator-execution-state-machine-v1", "done", []),
        ("m152-end-to-end-codex-loop-real-run-for-low-risk-code", "done", []),
        ("m153-hub-orchestration-run-monitor", "ready", ["m152-end-to-end-codex-loop-real-run-for-low-risk-code"]),
        ("monitor-target", "ready", ["m152-end-to-end-codex-loop-real-run-for-low-risk-code"]),
    ):
        assert add_queue_item(
            config,
            item_id=item_id,
            project_id="aresforge",
            repo_id="aresforge-main",
            title=item_id,
            description="Unit-test orchestration monitor item.",
            status=status,
            priority="high",
            item_type="orchestration",
            tags=["milestone:m153"],
            dependencies=dependencies,
            source="unit-test",
        )["ok"] is True


def _plan(config: AppConfig) -> Path:
    path = config.repo_root / "artifacts" / "plans" / "monitor-target.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "plan_type": "agent_orchestration_plan",
                "item_id": "monitor-target",
                "blocked": False,
                "steps": [
                    {
                        "step_id": "step-01-queue-planner-agent",
                        "sequence": 1,
                        "agent_id": "queue-planner-agent",
                        "forbidden_capabilities": ["execute_codex", "call_github_api", "apply_patch"],
                    },
                    {
                        "step_id": "step-02-validation-agent",
                        "sequence": 2,
                        "agent_id": "validation-agent",
                        "forbidden_capabilities": ["execute_codex", "call_github_api", "apply_patch"],
                    },
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def test_run_monitor_reports_history_recovery_gates_and_steps(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    run_payload = run_multi_agent_orchestration(
        config,
        item_id="monitor-target",
        plan_path=_plan(config),
        max_steps=1,
    )["payload"]

    payload = inspect_orchestration_run_monitor(config, project_id="aresforge")["payload"]

    assert payload["record_type"] == "hub_orchestration_run_monitor_v1"
    assert payload["artifact_type"] == "hub_orchestration_run_monitor_v1"
    assert payload["project_id"] == "aresforge"
    assert payload["run_id"] == run_payload["run_id"]
    assert payload["status"] == "recovery_required"
    assert payload["blocked"] is False
    assert payload["machine_gates_passed"] is True
    assert payload["history_summary"]["history_record_count"] == 1
    assert payload["latest_run"]["status"] == "max_steps_reached"
    assert payload["step_result_summary"]["step_result_count"] == 1
    assert payload["recovery_summary"]["resume_available"] is True
    assert payload["mutation_performed"] is False
    assert payload["external_execution_performed"] is False
    assert payload["model_execution_performed"] is False
    assert payload["codex_execution_performed"] is False
    assert payload["github_execution_performed"] is False
    assert payload["patch_application_performed"] is False
    assert payload["local_only"] is True
    assert "automatic" in payload["next_safe_action"].lower()


def test_run_monitor_output_path_writes_local_artifact(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    output = tmp_path / ".aresforge" / "orchestrator" / "run_monitor" / "monitor.json"

    result = inspect_orchestration_run_monitor(config, project_id="aresforge", output=output)
    written = json.loads(output.read_text(encoding="utf-8"))

    assert result["ok"] is True
    assert result["wrote_output_file"] is True
    assert written["artifact_type"] == "hub_orchestration_run_monitor_v1"
    assert written["artifacts_created"] == [str(output)]


def test_hub_api_exposes_orchestration_run_monitor(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    run_payload = run_multi_agent_orchestration(
        config,
        item_id="monitor-target",
        plan_path=_plan(config),
        max_steps=1,
    )["payload"]

    payload = get_orchestration_run_monitor(config, {"project_id": "aresforge", "run_id": run_payload["run_id"]})

    assert payload["ok"] is True
    assert payload["record_type"] == "hub_orchestration_run_monitor_v1"
    assert payload["run_id"] == run_payload["run_id"]
    assert payload["hub_visibility"]["api_endpoint"] == "/api/orchestration/run-monitor"
    assert payload["local_only"] is True
