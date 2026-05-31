import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.durable_orchestration_run_store import append_orchestration_run_record
from aresforge.operator.local_project_queue import add_queue_item, init_project_queue
from aresforge.operator.orchestration_run_replay_audit import replay_orchestration_run


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
    assert add_queue_item(
        config,
        item_id="m140-orchestrator-execution-state-machine-v1",
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M140 Orchestrator Execution State Machine v1",
        description="Completed state-machine contract for history inspector gates.",
        status="done",
        priority="high",
        item_type="orchestration",
        tags=["milestone:m140"],
        source="unit-test",
    )["ok"] is True
    assert add_queue_item(
        config,
        item_id="m157-run-replay-and-audit-trail",
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M157 Run Replay and Audit Trail",
        description="Unit-test replay item.",
        status="ready",
        priority="high",
        item_type="orchestration",
        tags=["milestone:m157"],
        source="unit-test",
    )["ok"] is True


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _source_run_payload(artifact_path: Path, evidence_path: Path) -> dict[str, object]:
    return {
        "execution_record_type": "multi_agent_orchestration_v1",
        "run_id": "run-a",
        "item_id": "m157-target",
        "project_id": "aresforge",
        "status": "completed",
        "blocked": False,
        "blocked_reasons": [],
        "warnings": [],
        "started_at": "2026-05-31T20:00:00Z",
        "completed_at": "2026-05-31T20:03:00Z",
        "steps_total": 2,
        "steps_attempted": 2,
        "steps_completed": 2,
        "steps_blocked": 0,
        "machine_gates_checked": [{"gate_profile": "read_only_agent", "passed": True}],
        "machine_gates_passed": True,
        "artifacts_created": [str(artifact_path), str(evidence_path)],
        "mutation_performed": False,
        "queue_mutation_performed": False,
        "external_execution_performed": False,
        "codex_execution_performed": False,
        "model_execution_performed": False,
        "github_execution_performed": False,
        "patch_application_performed": False,
        "local_only": True,
        "next_safe_action": "Review completed run.",
        "step_results": [
            {
                "step_id": "step-01-plan",
                "sequence": 1,
                "agent_id": "planner",
                "status": "completed",
                "blocked": False,
                "machine_gates_checked": [{"gate_profile": "read_only_agent", "passed": True, "step_id": "step-01-plan"}],
                "artifacts_created": [str(evidence_path)],
                "mutation_performed": False,
                "queue_mutation_performed": False,
                "external_execution_performed": False,
                "codex_execution_performed": False,
                "model_execution_performed": False,
                "github_execution_performed": False,
                "patch_application_performed": False,
            },
            {
                "step_id": "step-02-validate",
                "sequence": 2,
                "agent_id": "validator",
                "status": "completed",
                "blocked": False,
                "machine_gates_checked": [{"gate_profile": "read_only_agent", "passed": True, "step_id": "step-02-validate"}],
                "mutation_performed": False,
                "queue_mutation_performed": False,
                "external_execution_performed": False,
                "codex_execution_performed": False,
                "model_execution_performed": False,
                "github_execution_performed": False,
                "patch_application_performed": False,
            },
        ],
    }


def _record(artifact_path: Path, evidence_path: Path) -> dict[str, object]:
    return {
        "record_type": "orchestration_run_history_record",
        "generated": True,
        "run_id": "run-a",
        "item_id": "m157-target",
        "project_id": "aresforge",
        "status": "completed",
        "blocked": False,
        "blocked_reasons": [],
        "warnings": [],
        "started_at": "2026-05-31T20:00:00Z",
        "completed_at": "2026-05-31T20:03:00Z",
        "steps_total": 2,
        "steps_attempted": 2,
        "steps_completed": 2,
        "steps_blocked": 0,
        "machine_gates_checked": [{"gate_profile": "read_only_agent", "passed": True}],
        "machine_gates_passed": True,
        "autonomy_profile": "unit_test",
        "artifacts_created": [str(artifact_path), str(evidence_path)],
        "artifact_path": str(artifact_path),
        "mutation_performed": False,
        "queue_mutation_performed": False,
        "external_execution_performed": False,
        "codex_execution_performed": False,
        "model_execution_performed": False,
        "github_execution_performed": False,
        "patch_application_performed": False,
        "local_only": True,
        "next_safe_action": "Review durable run store test record.",
    }


def test_replay_reconstructs_run_steps_gates_artifacts_and_outcome(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    artifact = config.artifact_root / "multi-agent-orchestration" / "m157-target" / "run-a.json"
    evidence = config.repo_root / "artifacts" / "codex_result_ingestion" / "run-a" / "validation.json"
    _write_json(artifact, _source_run_payload(artifact, evidence))
    _write_json(evidence, {"record_type": "validation_evidence", "run_id": "run-a"})
    assert append_orchestration_run_record(config, record=_record(artifact, evidence))["ok"] is True

    payload = replay_orchestration_run(config, run_id="run-a", dry_run=True)["payload"]

    assert payload["record_type"] == "orchestration_run_replay_audit_trail_v1"
    assert payload["artifact_type"] == "orchestration_run_replay_audit_trail_v1"
    assert payload["project_id"] == "aresforge"
    assert payload["run_id"] == "run-a"
    assert payload["status"] == "replay_reconstructed"
    assert payload["blocked"] is False
    assert payload["machine_gates_passed"] is True
    assert payload["replay_summary"]["reconstructed"] is True
    assert payload["replay_summary"]["durable_record_found"] is True
    assert payload["replay_summary"]["source_run_artifact_found"] is True
    assert payload["replay_summary"]["step_count"] == 2
    assert payload["source_records"]["durable_run_store_record"]["run_id"] == "run-a"
    assert payload["step_records"][0]["step_id"] == "step-01-plan"
    assert any(event["event_type"] == "step_reconstructed" for event in payload["audit_trail"])
    assert any(artifact["sha256"] for artifact in payload["source_artifacts"])
    assert payload["mutation_performed"] is False
    assert payload["queue_mutation_performed"] is False
    assert payload["codex_execution_performed"] is False
    assert payload["model_execution_performed"] is False
    assert payload["github_execution_performed"] is False
    assert payload["patch_application_performed"] is False
    assert payload["replay_safety"]["replay_command_reexecuted_source_run"] is False
    assert payload["local_only"] is True


def test_replay_missing_run_is_non_mutating_audit_result(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)

    payload = replay_orchestration_run(config, run_id="sample-run", dry_run=True)["payload"]

    assert payload["status"] == "no_replay_record"
    assert payload["blocked"] is False
    assert payload["replay_summary"]["reconstructed"] is False
    assert any("sample-run" in warning for warning in payload["warnings"])
    assert payload["mutation_performed"] is False
    assert payload["local_only"] is True


def test_replay_requires_dry_run_and_blocks_without_execution(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)

    result = replay_orchestration_run(config, run_id="run-a", dry_run=False)
    payload = result["payload"]

    assert result["ok"] is False
    assert payload["status"] == "blocked"
    assert payload["blocked"] is True
    assert payload["dry_run"] is False
    assert any("--dry-run" in reason for reason in payload["blocked_reasons"])
    assert payload["codex_execution_performed"] is False
    assert payload["model_execution_performed"] is False
    assert payload["github_execution_performed"] is False
    assert payload["patch_application_performed"] is False


def test_replay_output_path_writes_local_audit_artifact(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    output = tmp_path / ".aresforge" / "orchestrator" / "replay" / "sample-run.json"

    result = replay_orchestration_run(config, run_id="sample-run", dry_run=True, output=output)
    written = json.loads(output.read_text(encoding="utf-8"))

    assert result["ok"] is True
    assert result["wrote_output_file"] is True
    assert written["artifact_type"] == "orchestration_run_replay_audit_trail_v1"
    assert written["artifacts_created"] == [str(output)]
    assert written["mutation_performed"] is False
