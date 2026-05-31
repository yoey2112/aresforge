import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.local_project_queue import add_queue_item, init_project_queue
from aresforge.operator.orchestrator_resume_from_failure import (
    DEFAULT_ITEM_ID,
    inspect_orchestration_resume_plan,
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


def _seed_queue(config: AppConfig) -> None:
    assert init_project_queue(config)["ok"] is True
    assert add_queue_item(
        config,
        item_id="m146-agent-step-result-normalization",
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M146 Agent Step Result Normalization",
        description="Completed predecessor.",
        status="done",
        priority="high",
        item_type="orchestration",
        tags=["milestone:m146"],
        source="unit-test",
        notes="Predecessor evidence present.",
    )["ok"] is True
    assert add_queue_item(
        config,
        item_id=DEFAULT_ITEM_ID,
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M147 Orchestrator Resume-from-Failure",
        description="Inspect safe resume plans from the last valid checkpoint.",
        status="ready",
        priority="high",
        item_type="orchestration",
        tags=["milestone:m147", "machine-gated"],
        dependencies=["m146-agent-step-result-normalization"],
        source="unit-test",
        notes="Read-only resume planning only.",
    )["ok"] is True


def _write_run(config: AppConfig, payload: dict) -> Path:
    artifact = config.artifact_root / "multi-agent-orchestration" / payload["item_id"] / f"{payload['run_id']}.json"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    history = config.repo_root / ".aresforge" / "orchestrator" / "run_history.json"
    history.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "record_type": "orchestration_run_history_record",
        "run_id": payload["run_id"],
        "item_id": payload["item_id"],
        "project_id": payload["project_id"],
        "status": payload["status"],
        "blocked": payload.get("blocked", False),
        "blocked_reasons": payload.get("blocked_reasons", []),
        "warnings": payload.get("warnings", []),
        "started_at": payload.get("started_at", ""),
        "completed_at": payload.get("completed_at", ""),
        "steps_total": payload.get("steps_total", 0),
        "steps_attempted": payload.get("steps_attempted", 0),
        "steps_completed": payload.get("steps_completed", 0),
        "steps_blocked": payload.get("steps_blocked", 0),
        "machine_gates_checked": payload.get("machine_gates_checked", []),
        "machine_gates_passed": payload.get("machine_gates_passed", True),
        "artifacts_created": [str(artifact)],
        "artifact_path": str(artifact),
        "mutation_performed": payload.get("mutation_performed", False),
        "external_execution_performed": payload.get("external_execution_performed", False),
        "model_execution_performed": payload.get("model_execution_performed", False),
        "codex_execution_performed": payload.get("codex_execution_performed", False),
        "github_execution_performed": payload.get("github_execution_performed", False),
        "patch_application_performed": payload.get("patch_application_performed", False),
        "local_only": True,
        "next_safe_action": payload.get("next_safe_action", ""),
    }
    history.write_text(
        json.dumps(
            {
                "schema_version": "m141.1",
                "artifact_type": "orchestration_run_history_recovery_v1",
                "updated_at": "2026-05-31T00:00:00Z",
                "records": [record],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return artifact


def test_resume_plan_reports_last_valid_checkpoint_for_interrupted_run(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    _write_run(
        config,
        {
            "execution_record_type": "multi_agent_orchestration_v1",
            "run_id": "resume-run",
            "item_id": "resume-item",
            "project_id": "aresforge",
            "status": "max_steps_reached",
            "started_at": "2026-05-31T00:00:00Z",
            "completed_at": "2026-05-31T00:01:00Z",
            "steps_total": 2,
            "steps_attempted": 1,
            "steps_completed": 1,
            "steps_blocked": 0,
            "step_results": [
                {
                    "step_id": "step-01-queue-planner",
                    "sequence": 1,
                    "status": "completed",
                    "blocked": False,
                    "machine_gates_checked": [{"gate_profile": "read_only_agent", "passed": True, "blocked": False}],
                }
            ],
            "machine_gates_checked": [{"gate_profile": "read_only_agent", "passed": True, "blocked": False}],
            "machine_gates_passed": True,
            "local_only": True,
        },
    )

    payload = inspect_orchestration_resume_plan(config, run_id="resume-run")["payload"]

    assert payload["record_type"] == "orchestrator_resume_from_failure_plan_v1"
    assert payload["artifact_type"] == "orchestrator_resume_from_failure_plan_v1"
    assert payload["run_id"] == "resume-run"
    assert payload["status"] == "resume_available"
    assert payload["blocked"] is False
    assert payload["machine_gates_passed"] is True
    assert payload["resume_eligible"] is True
    assert payload["last_valid_checkpoint"]["checkpoint_id"] == "post_step_checkpoint"
    assert payload["last_valid_checkpoint"]["last_completed_step_count"] == 1
    assert payload["resume_target"]["resume_at_step_index"] == 2
    assert payload["resume_command_plan"]["automatic_resume_performed"] is False
    assert payload["mutation_performed"] is False
    assert payload["external_execution_performed"] is False
    assert payload["model_execution_performed"] is False
    assert payload["codex_execution_performed"] is False
    assert payload["github_execution_performed"] is False
    assert payload["patch_application_performed"] is False
    assert payload["local_only"] is True


def test_resume_plan_requires_review_for_failed_codex_run(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    _write_run(
        config,
        {
            "execution_record_type": "multi_agent_orchestration_v1",
            "run_id": "failed-run",
            "item_id": "resume-item",
            "project_id": "aresforge",
            "status": "failed",
            "blocked": False,
            "blocked_reasons": ["Codex dispatch failed."],
            "steps_total": 2,
            "steps_attempted": 2,
            "steps_completed": 1,
            "steps_blocked": 0,
            "step_results": [
                {"step_id": "step-01-planner", "sequence": 1, "status": "completed", "blocked": False},
                {"step_id": "step-02-codex", "sequence": 2, "status": "failed", "blocked": False},
            ],
            "machine_gates_checked": [{"gate_profile": "codex_dispatch", "passed": True, "blocked": False}],
            "machine_gates_passed": True,
            "external_execution_performed": True,
            "codex_execution_performed": True,
            "local_only": True,
        },
    )

    payload = inspect_orchestration_resume_plan(config, run_id="failed-run")["payload"]

    assert payload["status"] == "recovery_review_required"
    assert payload["resume_eligible"] is False
    assert payload["resume_requires_operator_review"] is True
    assert payload["resume_requires_validation"] is True
    assert payload["source_run_execution_flags"]["codex_execution_performed"] is True
    assert payload["resume_command_plan"]["recommended_operator_command"] == ""
    assert "validation" in payload["next_safe_action"].lower()


def test_resume_plan_handles_missing_run_as_advisory(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)

    result = inspect_orchestration_resume_plan(config, run_id="missing-run")
    payload = result["payload"]

    assert result["ok"] is True
    assert payload["status"] == "no_resume_record"
    assert payload["source_run_found"] is False
    assert payload["resume_eligible"] is False
    assert payload["blocked"] is False
    assert any("No orchestration run record" in warning for warning in payload["warnings"])


def test_resume_plan_output_path_writes_artifact(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    output = tmp_path / ".aresforge" / "orchestrator" / "resume_plans" / "resume.json"

    result = inspect_orchestration_resume_plan(config, run_id="missing-run", output=output)
    written = json.loads(output.read_text(encoding="utf-8"))

    assert result["ok"] is True
    assert result["wrote_output_file"] is True
    assert written["artifact_type"] == "orchestrator_resume_from_failure_plan_v1"
    assert str(output) in written["artifacts_created"]
