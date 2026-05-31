import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.end_to_end_codex_loop_dry_run import run_end_to_end_codex_loop_dry_run
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


def _seed_queue(config: AppConfig, *, item_id: str = "m151-end-to-end-codex-loop-dry-run") -> None:
    assert init_project_queue(config)["ok"] is True
    assert add_queue_item(
        config,
        item_id=item_id,
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M151 End-to-End Codex Loop Dry Run",
        description="Run the dry-run Codex orchestration loop through completion recommendation.",
        status="ready",
        priority="high",
        item_type="orchestration",
        tags=["milestone:m151", "codex-loop", "machine-gated"],
        completion_requires=["tests_run", "smoke_checks", "commit_hash"],
        evidence_required=["dispatch_result_evidence", "validation_results"],
    )["ok"] is True
    transaction_log = config.repo_root / ".aresforge" / "queue" / "transaction_log.json"
    transaction_log.parent.mkdir(parents=True, exist_ok=True)
    transaction_log.write_text(json.dumps({"schema_version": "1.0", "transactions": []}), encoding="utf-8")


def _payload(result: dict[str, object]) -> dict[str, object]:
    return result["payload"]  # type: ignore[index]


def test_end_to_end_codex_loop_dry_run_reaches_completion_recommendation(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)

    payload = _payload(
        run_end_to_end_codex_loop_dry_run(
            config,
            item_id="m151-end-to-end-codex-loop-dry-run",
            dry_run=True,
            output_format="json",
        )
    )

    assert payload["record_type"] == "end_to_end_codex_loop_dry_run_v1"
    assert payload["generated"] is True
    assert payload["status"] == "dry_run_completed"
    assert payload["blocked"] is False
    assert payload["blocked_reasons"] == []
    assert payload["machine_gates_passed"] is True
    assert {gate["gate_profile"] for gate in payload["machine_gates_checked"]} == {"codex_dispatch"}
    assert payload["completion_queue_gate_result"]["gate_profile"] == "queue_status_mutation"
    assert payload["completion_recommended"] is True
    assert payload["completion_recommendation"]["recommended_complete"] is True
    assert payload["mutation_performed"] is False
    assert payload["external_execution_performed"] is False
    assert payload["model_execution_performed"] is False
    assert payload["codex_execution_performed"] is False
    assert payload["github_execution_performed"] is False
    assert payload["patch_application_performed"] is False
    assert payload["local_only"] is True
    assert Path(payload["dispatch_artifact_path"]).exists()
    assert Path(payload["dispatch_execution_record_path"]).exists()
    assert Path(payload["ingestion_execution_record_path"]).exists()
    assert Path(payload["ingestion_record_path"]).exists()
    assert all(Path(path).exists() for path in payload["artifacts_created"])


def test_end_to_end_codex_loop_blocks_without_dry_run(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)

    payload = _payload(
        run_end_to_end_codex_loop_dry_run(
            config,
            item_id="m151-end-to-end-codex-loop-dry-run",
            dry_run=False,
            output_format="json",
        )
    )

    assert payload["status"] == "blocked"
    assert payload["blocked"] is True
    assert any("--dry-run" in reason for reason in payload["blocked_reasons"])
    assert payload["codex_execution_performed"] is False
    assert payload["mutation_performed"] is False


def test_end_to_end_codex_loop_blocks_missing_queue_item(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_project_queue(config)["ok"] is True

    payload = _payload(
        run_end_to_end_codex_loop_dry_run(
            config,
            item_id="missing-m151",
            dry_run=True,
            output_format="json",
        )
    )

    assert payload["status"] == "blocked"
    assert payload["blocked"] is True
    assert "Queue item was not found." in payload["blocked_reasons"]
    assert payload["machine_gates_checked"] == []
    assert payload["local_only"] is True
