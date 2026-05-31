import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.local_project_queue import add_queue_item, init_project_queue
from aresforge.operator.multi_agent_orchestrator import run_multi_agent_orchestration
from aresforge.operator.orchestration_run_history import (
    inspect_orchestration_run_history,
    resolve_orchestration_history_path,
)
from aresforge.operator.orchestrator_execution_state_machine import DEFAULT_ITEM_ID as STATE_MACHINE_ITEM_ID


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


def _seed(config: AppConfig, *, item_id: str = "m141-history") -> None:
    assert init_project_queue(config)["ok"] is True
    assert add_queue_item(
        config,
        item_id=STATE_MACHINE_ITEM_ID,
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M140 Orchestrator Execution State Machine v1",
        description="Completed state-machine contract.",
        status="done",
        priority="high",
        item_type="orchestration",
        tags=["milestone:m140"],
        source="unit-test",
    )["ok"] is True
    assert add_queue_item(
        config,
        item_id=item_id,
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M141 Orchestration Run History and Recovery",
        description="Persist orchestration run history and recovery records.",
        status="ready",
        priority="high",
        item_type="orchestration",
        tags=["milestone:m141", "machine-gated"],
        dependencies=[STATE_MACHINE_ITEM_ID],
        source="unit-test",
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


def test_orchestration_run_persists_history_and_recovery_record(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed(config)
    plan = _plan(config, "m141-history", ["queue-planner-agent", "validation-agent"])

    run_payload = run_multi_agent_orchestration(
        config,
        item_id="m141-history",
        plan_path=plan,
        max_steps=1,
    )["payload"]
    history_path = resolve_orchestration_history_path(config.repo_root)

    assert history_path.exists()
    assert run_payload["status"] == "max_steps_reached"

    payload = inspect_orchestration_run_history(config, project_id="aresforge")["payload"]

    assert payload["record_type"] == "orchestration_run_history_recovery_v1"
    assert payload["artifact_type"] == "orchestration_run_history_recovery_v1"
    assert payload["status"] == "recovery_required"
    assert payload["blocked"] is False
    assert payload["machine_gates_passed"] is True
    assert payload["history_record_count"] == 1
    assert payload["recovery_record_count"] == 1
    assert payload["records"][0]["run_id"] == run_payload["run_id"]
    assert payload["recovery_records"][0]["recovery_status"] == "resume_available"
    assert payload["mutation_performed"] is False
    assert payload["external_execution_performed"] is False
    assert payload["model_execution_performed"] is False
    assert payload["codex_execution_performed"] is False
    assert payload["github_execution_performed"] is False
    assert payload["patch_application_performed"] is False
    assert payload["local_only"] is True


def test_history_inspector_discovers_legacy_orchestration_artifacts(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed(config)
    artifact = config.artifact_root / "multi-agent-orchestration" / "legacy-item" / "legacy.json"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text(
        json.dumps(
            {
                "execution_record_type": "multi_agent_orchestration_v1",
                "run_id": "legacy-run",
                "item_id": "legacy-item",
                "project_id": "aresforge",
                "started_at": "2026-05-31T00:00:00Z",
                "completed_at": "2026-05-31T00:01:00Z",
                "status": "failed",
                "blocked": False,
                "blocked_reasons": ["Validation failed."],
                "steps_total": 2,
                "steps_attempted": 2,
                "steps_completed": 1,
                "steps_blocked": 0,
                "machine_gates_checked": [{"passed": True}],
                "artifacts_created": [str(artifact)],
                "local_only": True,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    payload = inspect_orchestration_run_history(config, project_id="aresforge", run_id="legacy-run")["payload"]

    assert payload["history_record_count"] == 1
    assert payload["recovery_record_count"] == 1
    assert payload["records"][0]["artifact_path"] == str(artifact)
    assert payload["recovery_records"][0]["status"] == "failed"
    assert any("history file does not exist" in warning for warning in payload["warnings"])


def test_history_inspector_output_path_writes_artifact(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed(config)
    output = tmp_path / ".aresforge" / "orchestrator" / "history-inspection.json"

    result = inspect_orchestration_run_history(config, project_id="aresforge", output=output)
    written = json.loads(output.read_text(encoding="utf-8"))

    assert result["ok"] is True
    assert result["wrote_output_file"] is True
    assert written["artifact_type"] == "orchestration_run_history_recovery_v1"
    assert written["artifacts_created"] == [str(output)]
