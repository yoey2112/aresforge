import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.codex_failure_classification_retry_policy import (
    DEFAULT_ITEM_ID,
    classify_codex_failure,
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
        item_id="m144-codex-validation-profile-expansion",
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M144 Codex Validation Profile Expansion",
        description="Completed predecessor.",
        status="done",
        priority="high",
        item_type="orchestration",
        tags=["milestone:m144"],
        source="unit-test",
        notes="Validation evidence present.",
    )["ok"] is True
    assert add_queue_item(
        config,
        item_id=DEFAULT_ITEM_ID,
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M145 Codex Failure Classification and Retry Policy",
        description="Classify Codex failures and deterministic retry/stop policies.",
        status="ready",
        priority="high",
        item_type="orchestration",
        tags=["milestone:m145", "codex-execution", "machine-gated"],
        dependencies=["m144-codex-validation-profile-expansion"],
        source="unit-test",
        notes="Classification only; no retry or execution.",
    )["ok"] is True


def test_codex_failure_classifies_nonzero_without_retry_loop(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    failure = tmp_path / "artifacts" / "manual" / "sample-codex-failure.json"
    failure.parent.mkdir(parents=True)
    failure.write_text(
        json.dumps(
            {
                "item_id": DEFAULT_ITEM_ID,
                "project_id": "aresforge",
                "run_id": "unit-run-1",
                "status": "failed",
                "exit_code": 1,
                "stderr": "Codex process exited with code 1 after tool failure.",
                "local_only": True,
                "codex_execution_performed": True,
                "github_execution_performed": False,
                "patch_application_performed": False,
            }
        ),
        encoding="utf-8",
    )

    payload = classify_codex_failure(config, failure_artifact=failure)["payload"]

    assert payload["record_type"] == "codex_failure_classification_retry_policy_v1"
    assert payload["artifact_type"] == "codex_failure_classification_retry_policy_v1"
    assert payload["item_id"] == DEFAULT_ITEM_ID
    assert payload["status"] == "classified"
    assert payload["blocked"] is False
    assert payload["machine_gates_passed"] is True
    assert payload["primary_failure_class"] == "process_nonzero"
    assert payload["retry_policy"]["policy_id"] == "single_manual_retry_after_process_triage"
    assert payload["retry_policy"]["automatic_retry_allowed"] is False
    assert payload["retry_policy"]["max_retry_attempts"] == 1
    assert payload["mutation_performed"] is False
    assert payload["external_execution_performed"] is False
    assert payload["model_execution_performed"] is False
    assert payload["codex_execution_performed"] is False
    assert payload["github_execution_performed"] is False
    assert payload["patch_application_performed"] is False
    assert payload["local_only"] is True
    assert payload["observed_execution_flags"]["artifact_reports_codex_execution"] is True
    assert "automatic_retry_loop" in payload["prohibited_operations"]


def test_codex_failure_machine_gate_blocks_auto_retry(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    failure = tmp_path / "artifacts" / "manual" / "gate-failure.json"
    failure.parent.mkdir(parents=True)
    failure.write_text(
        json.dumps(
            {
                "item_id": DEFAULT_ITEM_ID,
                "project_id": "aresforge",
                "status": "blocked",
                "blocked": True,
                "blocked_reasons": ["Machine gate blocked: dependencies must be satisfied."],
                "local_only": True,
            }
        ),
        encoding="utf-8",
    )

    payload = classify_codex_failure(config, failure_artifact=failure)["payload"]

    assert payload["status"] == "classified"
    assert payload["primary_failure_class"] == "machine_gate_blocked"
    assert payload["retry_policy"]["decision"] == "stop"
    assert payload["retry_policy"]["max_retry_attempts"] == 0
    assert payload["retry_policy"]["automatic_retry_allowed"] is False


def test_codex_failure_blocks_when_artifact_missing(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)

    payload = classify_codex_failure(config, failure_artifact=tmp_path / "missing.json")["payload"]

    assert payload["status"] == "blocked"
    assert payload["blocked"] is True
    assert payload["primary_failure_class"] == "artifact_invalid"
    assert payload["retry_policy"]["decision"] == "stop"
    assert any("Failure artifact is missing" in reason for reason in payload["blocked_reasons"])


def test_codex_failure_output_path_writes_artifact(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    failure = tmp_path / "artifacts" / "manual" / "timeout.json"
    failure.parent.mkdir(parents=True)
    failure.write_text(
        json.dumps(
            {
                "item_id": DEFAULT_ITEM_ID,
                "project_id": "aresforge",
                "status": "failed",
                "timed_out": True,
                "local_only": True,
            }
        ),
        encoding="utf-8",
    )
    output = tmp_path / ".aresforge" / "codex_execution" / "failure_policy" / "classification.json"

    result = classify_codex_failure(config, failure_artifact=failure, output=output)
    written = json.loads(output.read_text(encoding="utf-8"))

    assert result["ok"] is True
    assert result["wrote_output_file"] is True
    assert written["artifact_type"] == "codex_failure_classification_retry_policy_v1"
    assert written["artifacts_created"] == [str(output)]
    assert written["primary_failure_class"] == "process_timeout"
