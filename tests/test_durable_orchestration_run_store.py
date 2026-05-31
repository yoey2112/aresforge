import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.durable_orchestration_run_store import (
    append_orchestration_run_record,
    inspect_orchestration_run_store,
    read_orchestration_run_store,
    resolve_orchestration_run_store_path,
    update_orchestration_run_record,
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
        item_id="m155-durable-orchestration-run-store",
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M155 Durable Orchestration Run Store",
        description="Unit-test durable orchestration run store item.",
        status="ready",
        priority="high",
        item_type="orchestration",
        tags=["milestone:m155"],
        source="unit-test",
    )["ok"] is True


def _record(run_id: str, *, completed_at: str, status: str = "completed") -> dict[str, object]:
    return {
        "record_type": "orchestration_run_history_record",
        "generated": True,
        "run_id": run_id,
        "item_id": "m155-target",
        "project_id": "aresforge",
        "status": status,
        "blocked": status == "blocked",
        "blocked_reasons": ["blocked by test"] if status == "blocked" else [],
        "warnings": [],
        "started_at": "2026-05-31T20:00:00Z",
        "completed_at": completed_at,
        "machine_gates_checked": [{"gate_profile": "read_only_agent", "passed": True}],
        "machine_gates_passed": True,
        "autonomy_profile": "unit_test",
        "artifacts_created": [],
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


def test_store_inspection_bootstraps_missing_file_with_stable_fields(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    store_path = resolve_orchestration_run_store_path(config.repo_root)

    payload = inspect_orchestration_run_store(config, project_id="aresforge")["payload"]

    assert store_path.exists()
    assert payload["record_type"] == "durable_orchestration_run_store_v1"
    assert payload["artifact_type"] == "durable_orchestration_run_store_v1"
    assert payload["project_id"] == "aresforge"
    assert payload["status"] == "empty"
    assert payload["blocked"] is False
    assert payload["blocked_reasons"] == []
    assert payload["machine_gates_passed"] is True
    assert payload["bootstrap_performed"] is True
    assert payload["mutation_performed"] is True
    assert payload["queue_mutation_performed"] is False
    assert payload["external_execution_performed"] is False
    assert payload["codex_execution_performed"] is False
    assert payload["model_execution_performed"] is False
    assert payload["github_execution_performed"] is False
    assert payload["patch_application_performed"] is False
    assert payload["local_only"] is True


def test_store_append_read_update_by_run_id_and_deterministic_order(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)

    assert append_orchestration_run_record(
        config,
        record=_record("run-b", completed_at="2026-05-31T20:02:00Z"),
    )["ok"] is True
    assert append_orchestration_run_record(
        config,
        record=_record("run-a", completed_at="2026-05-31T20:01:00Z"),
    )["ok"] is True

    read_payload = read_orchestration_run_store(config)
    assert read_payload["ok"] is True
    assert [record["run_id"] for record in read_payload["records"]] == ["run-a", "run-b"]

    update_payload = update_orchestration_run_record(
        config,
        run_id="run-a",
        updates={"status": "blocked", "blocked": True, "blocked_reasons": ["updated blocker"]},
    )
    assert update_payload["ok"] is True

    inspected = inspect_orchestration_run_store(config, project_id="aresforge", run_id="run-a")["payload"]
    assert inspected["filtered_record_count"] == 1
    assert inspected["records"][0]["run_id"] == "run-a"
    assert inspected["records"][0]["status"] == "blocked"
    assert inspected["records"][0]["blocked_reasons"] == ["updated blocker"]


def test_store_reports_corrupt_json_without_traceback(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    store_path = resolve_orchestration_run_store_path(config.repo_root)
    store_path.parent.mkdir(parents=True, exist_ok=True)
    store_path.write_text("{not json", encoding="utf-8")

    result = inspect_orchestration_run_store(config, project_id="aresforge")
    payload = result["payload"]

    assert result["ok"] is False
    assert payload["status"] == "blocked"
    assert payload["blocked"] is True
    assert any("valid JSON" in reason for reason in payload["blocked_reasons"])


def test_store_output_path_writes_inspection_artifact(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    output = tmp_path / ".aresforge" / "orchestrator" / "store-inspection.json"

    result = inspect_orchestration_run_store(config, project_id="aresforge", output=output)
    written = json.loads(output.read_text(encoding="utf-8"))

    assert result["ok"] is True
    assert result["wrote_output_file"] is True
    assert written["artifact_type"] == "durable_orchestration_run_store_v1"
    assert written["artifacts_created"] == [str(output)]
