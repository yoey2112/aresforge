import json
import os
from pathlib import Path
from datetime import UTC, datetime, timedelta

from aresforge.config import AppConfig
from aresforge.operator.durable_orchestration_run_store import append_orchestration_run_record
from aresforge.operator.local_project_queue import add_queue_item, init_project_queue
from aresforge.operator.orchestration_artifact_retention_policy import (
    inspect_orchestration_artifact_retention,
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
        item_id="m156-orchestration-artifact-retention-policy",
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M156 Orchestration Artifact Retention Policy",
        description="Unit-test retention policy item.",
        status="ready",
        priority="high",
        item_type="orchestration",
        tags=["milestone:m156"],
        source="unit-test",
    )["ok"] is True


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _record(run_id: str, artifact_path: str) -> dict[str, object]:
    return {
        "record_type": "orchestration_run_history_record",
        "generated": True,
        "run_id": run_id,
        "item_id": "m156-target",
        "project_id": "aresforge",
        "status": "completed",
        "blocked": False,
        "blocked_reasons": [],
        "warnings": [],
        "started_at": "2026-05-31T20:00:00Z",
        "completed_at": "2026-05-31T20:01:00Z",
        "machine_gates_checked": [{"gate_profile": "read_only_agent", "passed": True}],
        "machine_gates_passed": True,
        "autonomy_profile": "unit_test",
        "artifacts_created": [artifact_path],
        "artifact_path": artifact_path,
        "mutation_performed": False,
        "queue_mutation_performed": False,
        "external_execution_performed": False,
        "codex_execution_performed": False,
        "model_execution_performed": False,
        "github_execution_performed": False,
        "patch_application_performed": False,
        "local_only": True,
        "next_safe_action": "Review retention test record.",
    }


def _category(payload: dict[str, object], category_id: str) -> dict[str, object]:
    categories = payload["category_summaries"]
    assert isinstance(categories, list)
    for category in categories:
        if isinstance(category, dict) and category.get("category_id") == category_id:
            return category
    raise AssertionError(f"Missing category {category_id}")


def test_retention_policy_reports_categories_counts_and_orphans(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    referenced = Path("artifacts/multi-agent-orchestration/run-a/run.json")
    orphan = Path("artifacts/multi-agent-orchestration/run-b/run.json")
    _write_json(config.repo_root / referenced, {"execution_record_type": "multi_agent_orchestration_v1", "run_id": "run-a"})
    _write_json(config.repo_root / orphan, {"execution_record_type": "multi_agent_orchestration_v1", "run_id": "run-b"})
    _write_json(
        config.repo_root / "artifacts/codex_result_ingestion/m156/validation.json",
        {"record_type": "codex_result_ingestion_validation_v1"},
    )
    assert append_orchestration_run_record(config, record=_record("run-a", str(referenced)))["ok"] is True

    payload = inspect_orchestration_artifact_retention(config, project_id="aresforge")["payload"]
    orchestration_runs = _category(payload, "orchestration_runs")

    assert payload["record_type"] == "orchestration_artifact_retention_policy_v1"
    assert payload["artifact_type"] == "orchestration_artifact_retention_policy_v1"
    assert payload["project_id"] == "aresforge"
    assert payload["status"] == "review_required"
    assert payload["blocked"] is False
    assert payload["machine_gates_passed"] is True
    assert payload["artifact_count_summary"]["total_artifact_count"] >= 4
    assert orchestration_runs["file_count"] == 2
    assert orchestration_runs["orphan_count"] == 1
    assert payload["orphan_detection"]["orphan_count"] == 1
    assert payload["dry_run_cleanup_plan"][0]["destructive_action_performed"] is False
    assert payload["mutation_performed"] is False
    assert payload["queue_mutation_performed"] is False
    assert payload["codex_execution_performed"] is False
    assert payload["model_execution_performed"] is False
    assert payload["github_execution_performed"] is False
    assert payload["patch_application_performed"] is False
    assert payload["local_only"] is True
    assert (config.repo_root / orphan).exists()


def test_retention_policy_warns_on_stale_artifacts_without_deleting(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    stale_path = Path("artifacts/codex_result_ingestion/m156/old-validation.json")
    _write_json(config.repo_root / stale_path, {"record_type": "codex_result_ingestion_validation_v1"})
    old = (datetime.now(UTC) - timedelta(days=120)).timestamp()
    os.utime(config.repo_root / stale_path, (old, old))

    payload = inspect_orchestration_artifact_retention(config, project_id="aresforge")["payload"]
    validation = _category(payload, "validation_evidence")

    assert payload["status"] == "review_required"
    assert validation["stale_count"] == 1
    assert any(entry["artifact_path"] == stale_path.as_posix() for entry in payload["stale_artifact_warnings"])
    assert any(entry["reason"] == "stale_artifact" for entry in payload["dry_run_cleanup_plan"])
    assert payload["cleanup_performed"] is False
    assert payload["artifact_deletion_performed"] is False
    assert (config.repo_root / stale_path).exists()


def test_retention_policy_output_path_writes_local_artifact(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    output = tmp_path / ".aresforge" / "orchestrator" / "artifact-retention.json"

    result = inspect_orchestration_artifact_retention(config, project_id="aresforge", output=output)
    written = json.loads(output.read_text(encoding="utf-8"))

    assert result["ok"] is True
    assert result["wrote_output_file"] is True
    assert written["artifact_type"] == "orchestration_artifact_retention_policy_v1"
    assert written["artifacts_created"] == [str(output)]
    assert written["cleanup_performed"] is False
