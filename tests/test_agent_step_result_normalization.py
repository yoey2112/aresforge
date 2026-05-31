import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.agent_step_result_normalization import (
    DEFAULT_ITEM_ID,
    normalize_agent_step_result,
)
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


def _seed_queue(config: AppConfig) -> None:
    assert init_project_queue(config)["ok"] is True
    assert add_queue_item(
        config,
        item_id="m145-codex-failure-classification-and-retry-policy",
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M145 Codex Failure Classification and Retry Policy",
        description="Completed predecessor.",
        status="done",
        priority="high",
        item_type="orchestration",
        tags=["milestone:m145"],
        source="unit-test",
        notes="Predecessor evidence present.",
    )["ok"] is True
    assert add_queue_item(
        config,
        item_id=DEFAULT_ITEM_ID,
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M146 Agent Step Result Normalization",
        description="Normalize agent step outputs for orchestrator evaluation and recovery.",
        status="ready",
        priority="high",
        item_type="orchestration",
        tags=["milestone:m146", "agent-step-results", "machine-gated"],
        dependencies=["m145-codex-failure-classification-and-retry-policy"],
        source="unit-test",
        notes="Normalization only; no agent execution.",
    )["ok"] is True


def test_normalize_completed_step_result(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    result_path = tmp_path / "artifacts" / "manual" / "step-result.json"
    result_path.parent.mkdir(parents=True)
    result_path.write_text(
        json.dumps(
            {
                "artifact_type": "sample_agent_step_result_v1",
                "step_id": "step-01-validation-agent",
                "sequence": 1,
                "agent_id": "validation-agent",
                "item_id": DEFAULT_ITEM_ID,
                "project_id": "aresforge",
                "run_id": "unit-run-1",
                "status": "completed",
                "blocked": False,
                "blocked_reasons": [],
                "warnings": ["sample warning"],
                "machine_gates_checked": [
                    {
                        "gate_profile": "read_only_agent",
                        "passed": True,
                        "blocked": False,
                        "blocked_reasons": [],
                    }
                ],
                "artifacts_created": ["artifacts/manual/step-output.json"],
                "mutation_performed": False,
                "external_execution_performed": False,
                "model_execution_performed": False,
                "codex_execution_performed": False,
                "github_execution_performed": False,
                "patch_application_performed": False,
                "local_only": True,
                "result_summary": "Validation-agent dry run completed.",
            }
        ),
        encoding="utf-8",
    )

    payload = normalize_agent_step_result(config, result_path=result_path)["payload"]

    assert payload["record_type"] == "agent_step_result_normalization_v1"
    assert payload["artifact_type"] == "agent_step_result_normalization_v1"
    assert payload["item_id"] == DEFAULT_ITEM_ID
    assert payload["project_id"] == "aresforge"
    assert payload["run_id"] == "unit-run-1"
    assert payload["status"] == "completed"
    assert payload["blocked"] is False
    assert payload["blocked_reasons"] == []
    assert payload["machine_gates_passed"] is True
    assert len(payload["machine_gates_checked"]) == 2
    assert payload["artifacts_created"] == ["artifacts/manual/step-output.json"]
    assert payload["mutation_performed"] is False
    assert payload["external_execution_performed"] is False
    assert payload["model_execution_performed"] is False
    assert payload["codex_execution_performed"] is False
    assert payload["github_execution_performed"] is False
    assert payload["patch_application_performed"] is False
    assert payload["local_only"] is True
    assert payload["normalizer_execution_flags"]["codex_execution_performed"] is False
    assert payload["orchestrator_evaluation"]["safe_for_automatic_next_step"] is True


def test_normalize_failed_codex_step_requires_recovery(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    result_path = tmp_path / "artifacts" / "manual" / "failed-step.json"
    result_path.parent.mkdir(parents=True)
    result_path.write_text(
        json.dumps(
            {
                "payload": {
                    "item_id": DEFAULT_ITEM_ID,
                    "project_id": "aresforge",
                    "run_id": "unit-run-2",
                    "step_id": "step-02-codex",
                    "agent_id": "codex-dispatch-agent",
                    "status": "failed",
                    "blocked": False,
                    "errors": ["Codex process exited nonzero."],
                    "machine_gates_passed": True,
                    "local_only": True,
                    "codex_execution_performed": True,
                    "external_execution_performed": True,
                    "mutation_performed": False,
                }
            }
        ),
        encoding="utf-8",
    )

    payload = normalize_agent_step_result(config, result_path=result_path)["payload"]

    assert payload["status"] == "failed"
    assert payload["blocked"] is False
    assert payload["codex_execution_performed"] is True
    assert payload["external_execution_performed"] is True
    assert payload["source_execution_flags"]["codex_execution_performed"] is True
    assert payload["normalizer_execution_flags"]["codex_execution_performed"] is False
    assert payload["orchestrator_evaluation"]["recovery_required"] is True
    assert "failure classification" in payload["next_safe_action"].lower()


def test_normalize_blocks_when_result_missing(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)

    payload = normalize_agent_step_result(config, result_path=tmp_path / "missing.json")["payload"]

    assert payload["status"] == "invalid"
    assert payload["blocked"] is True
    assert any("missing" in reason.lower() for reason in payload["blocked_reasons"])
    assert payload["result_artifact_found"] is False
    assert payload["result_artifact_valid_json"] is False


def test_normalize_output_path_writes_artifact(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    result_path = tmp_path / "artifacts" / "manual" / "step-result.json"
    result_path.parent.mkdir(parents=True)
    result_path.write_text(
        json.dumps(
            {
                "item_id": DEFAULT_ITEM_ID,
                "project_id": "aresforge",
                "status": "completed",
                "local_only": True,
            }
        ),
        encoding="utf-8",
    )
    output = tmp_path / ".aresforge" / "orchestrator" / "step_results" / "normalized.json"

    result = normalize_agent_step_result(config, result_path=result_path, output=output)
    written = json.loads(output.read_text(encoding="utf-8"))

    assert result["ok"] is True
    assert result["wrote_output_file"] is True
    assert written["artifact_type"] == "agent_step_result_normalization_v1"
    assert str(output) in written["artifacts_created"]
