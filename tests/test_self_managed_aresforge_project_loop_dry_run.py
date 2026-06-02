import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.durable_orchestration_run_store import read_orchestration_run_store
from aresforge.operator.local_project_queue import add_queue_item, init_project_queue
from aresforge.operator.self_managed_project_loop_dry_run import (
    DEFAULT_ITEM_ID,
    RECORD_TYPE,
    run_self_managed_project_loop_dry_run,
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


def _seed_queue(config: AppConfig, *, status: str = "done") -> None:
    assert init_project_queue(config)["ok"] is True
    assert add_queue_item(
        config,
        item_id="m167-hub-autonomy-control-center-v1",
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M167 Hub Autonomy Control Center v1",
        description="Dependency.",
        status="done",
        priority="high",
        item_type="dashboard",
        tags=["milestone:m167"],
        source="unit-test",
    )["ok"] is True
    assert add_queue_item(
        config,
        item_id=DEFAULT_ITEM_ID,
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M168 Self-Managed AresForge Project Loop Dry Run",
        description="Dry-run AresForge managing its own queue item through gates and GitHub sync planning.",
        status=status,
        priority="high",
        item_type="sync",
        tags=["milestone:m168", "self-managed", "github-loop"],
        dependencies=["m167-hub-autonomy-control-center-v1"],
        source="unit-test",
    )["ok"] is True
    queue_path = config.repo_root / ".aresforge" / "queue" / "work_items.json"
    raw = json.loads(queue_path.read_text(encoding="utf-8"))
    for item in raw["work_items"]:
        if item["item_id"] == DEFAULT_ITEM_ID:
            item["validation_summary"] = "M168 dry-run validation passed."
            item["tests_run"] = [
                "python -m pytest tests/test_self_managed_aresforge_project_loop_dry_run.py -> passed",
                "python -m aresforge run-self-managed-project-loop --project-id aresforge --dry-run --format json -> passed",
            ]
            item["evidence_note"] = "Local dry-run bundle evidence exists."
            item["changed_files"] = [
                "src/aresforge/operator/self_managed_project_loop_dry_run.py",
                "tests/test_self_managed_aresforge_project_loop_dry_run.py",
            ]
            item["artifact_paths"] = [".aresforge/self_managed_project_loop"]
            item["completion_evidence"] = {
                "command": "run-self-managed-project-loop",
                "artifacts_created": [".aresforge/self_managed_project_loop"],
            }
            item["github_issue"] = {
                "number": 168,
                "url": "https://github.com/local/aresforge/issues/168",
                "state": "open",
            }
    queue_path.write_text(json.dumps(raw, indent=2) + "\n", encoding="utf-8")


def test_self_managed_project_loop_dry_run_composes_full_local_bundle(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)

    result = run_self_managed_project_loop_dry_run(
        config,
        project_id="aresforge",
        dry_run=True,
    )
    payload = result["payload"]

    assert result["ok"] is True
    assert payload["record_type"] == RECORD_TYPE
    assert payload["artifact_type"] == RECORD_TYPE
    assert payload["status"] == "dry_run_completed"
    assert payload["project_id"] == "aresforge"
    assert payload["item_id"] == DEFAULT_ITEM_ID
    assert payload["generated"] is True
    assert payload["blocked"] is False
    assert payload["machine_gates_passed"] is True
    assert payload["autonomy_profile"] == "github_sync_dry_run"
    assert payload["selected_queue_item"]["found"] is True
    assert payload["route_decision"]["recommended_execution_target"] == "dry-run"
    assert payload["orchestration_plan"]["step_count"] == 4
    assert payload["orchestration_dry_run"]["status"] == "completed"
    assert payload["codex_loop_dry_run"]["record_type"] == "codex_loop_validation_evidence_bundle_v1"
    assert payload["github_issue_sync_plan"]["github_execution_performed"] is False
    assert payload["pull_request_summary_draft"]["pull_request_created"] is False
    assert payload["closeout_recommendation"]["issue_closure_allowed"] is False
    assert payload["run_store_entry"]["created"] is True
    assert payload["artifacts_created"]
    assert payload["mutation_performed"] is False
    assert payload["queue_mutation_performed"] is False
    assert payload["codex_execution_performed"] is False
    assert payload["model_execution_performed"] is False
    assert payload["github_execution_performed"] is False
    assert payload["patch_application_performed"] is False
    assert payload["local_only"] is True

    store = read_orchestration_run_store(config)
    assert any(record["run_id"] == payload["run_id"] for record in store["records"])


def test_self_managed_project_loop_requires_dry_run(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)

    payload = run_self_managed_project_loop_dry_run(config, project_id="aresforge")["payload"]

    assert payload["status"] == "blocked"
    assert payload["blocked"] is True
    assert "requires --dry-run" in payload["blocked_reasons"][0]
    assert payload["github_execution_performed"] is False
    assert payload["codex_execution_performed"] is False
    assert payload["local_only"] is True


def test_self_managed_project_loop_output_path_refuses_overwrite(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    output = tmp_path / ".aresforge" / "self_managed_project_loop" / "m168.json"

    first = run_self_managed_project_loop_dry_run(
        config,
        project_id="aresforge",
        dry_run=True,
        output=output,
    )
    second = run_self_managed_project_loop_dry_run(
        config,
        project_id="aresforge",
        dry_run=True,
        output=output,
    )

    assert first["ok"] is True
    assert json.loads(output.read_text(encoding="utf-8"))["artifact_type"] == RECORD_TYPE
    assert second["ok"] is False
    assert any("Output file already exists" in reason for reason in second["payload"]["blocked_reasons"])
