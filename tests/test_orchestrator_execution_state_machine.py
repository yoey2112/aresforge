import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.local_project_queue import add_queue_item, init_project_queue
from aresforge.operator.orchestrator_execution_state_machine import (
    DEFAULT_ITEM_ID,
    inspect_orchestrator_state_machine,
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
        item_id="m139-autonomous-sprint-closeout-v1",
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M139 Autonomous Sprint Closeout v1",
        description="Completed predecessor.",
        status="done",
        priority="high",
        item_type="documentation",
        tags=["milestone:m139"],
        source="unit-test",
        notes="Validation evidence present.",
    )["ok"] is True
    assert add_queue_item(
        config,
        item_id=DEFAULT_ITEM_ID,
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M140 Orchestrator Execution State Machine v1",
        description="Define durable orchestration run states.",
        status="ready",
        priority="high",
        item_type="orchestration",
        tags=["milestone:m140", "machine-gated"],
        dependencies=["m139-autonomous-sprint-closeout-v1"],
        source="unit-test",
        notes="Validation evidence present.",
    )["ok"] is True


def test_inspect_orchestrator_state_machine_reports_ready_contract(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)

    payload = inspect_orchestrator_state_machine(config)["payload"]

    assert payload["record_type"] == "orchestrator_execution_state_machine_v1"
    assert payload["artifact_type"] == "orchestrator_execution_state_machine_v1"
    assert payload["item_id"] == DEFAULT_ITEM_ID
    assert payload["project_id"] == "aresforge"
    assert payload["run_id"] == f"{DEFAULT_ITEM_ID}:state-machine-v1"
    assert payload["status"] == "ready"
    assert payload["blocked"] is False
    assert payload["machine_gates_passed"] is True
    assert payload["mutation_performed"] is False
    assert payload["external_execution_performed"] is False
    assert payload["model_execution_performed"] is False
    assert payload["codex_execution_performed"] is False
    assert payload["github_execution_performed"] is False
    assert payload["patch_application_performed"] is False
    assert payload["local_only"] is True
    assert payload["terminal_statuses"] == ["completed", "blocked", "failed", "cancelled"]
    assert any(state["state"] == "recovery" for state in payload["state_machine"]["states"])
    assert any(boundary["boundary_id"] == "machine_gate_boundary" for boundary in payload["validation_boundaries"])


def test_state_machine_blocks_when_queue_item_is_missing(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_project_queue(config)["ok"] is True

    payload = inspect_orchestrator_state_machine(config)["payload"]

    assert payload["status"] == "blocked"
    assert payload["blocked"] is True
    assert payload["machine_gates_passed"] is False
    assert any("Queue item must exist" in reason for reason in payload["blocked_reasons"])
    assert payload["external_execution_performed"] is False


def test_state_machine_output_path_writes_artifact(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    output = tmp_path / ".aresforge" / "orchestrator" / "state-machine.json"

    result = inspect_orchestrator_state_machine(config, output=output)
    written = json.loads(output.read_text(encoding="utf-8"))

    assert result["ok"] is True
    assert result["wrote_output_file"] is True
    assert written["artifact_type"] == "orchestrator_execution_state_machine_v1"
    assert written["artifacts_created"] == [str(output)]
