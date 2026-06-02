import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.local_project_queue import add_queue_item, init_project_queue
from aresforge.operator.production_autonomy_readiness_report import (
    DEFAULT_ITEM_ID,
    SOURCE_OF_TRUTH_DOCS,
    generate_production_autonomy_readiness_report,
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


def _seed_docs(config: AppConfig) -> None:
    milestones = " ".join(f"M{number}" for number in range(155, 170))
    for relative in SOURCE_OF_TRUTH_DOCS:
        path = config.repo_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"# {path.stem}\n\n{milestones}\n", encoding="utf-8")


def _seed_queue(config: AppConfig) -> None:
    assert init_project_queue(config)["ok"] is True
    for number in range(155, 170):
        item_id = DEFAULT_ITEM_ID if number == 169 else f"m{number}-milestone"
        if number == 167:
            item_id = "m167-hub-autonomy-control-center-v1"
        if number == 168:
            item_id = "m168-self-managed-aresforge-project-loop-dry-run"
        assert add_queue_item(
            config,
            item_id=item_id,
            project_id="aresforge",
            repo_id="aresforge-main",
            title=f"M{number} milestone",
            description="Milestone implementation.",
            status="done",
            priority="high",
            item_type="documentation" if number == 169 else "sync",
            tags=[f"milestone:m{number}"],
            source="unit-test",
            notes="Validation evidence present.",
        )["ok"] is True
    queue_path = config.repo_root / ".aresforge" / "queue" / "work_items.json"
    queue = json.loads(queue_path.read_text(encoding="utf-8"))
    for item in queue["work_items"]:
        item["completion_commit"] = "abc123"
        item["validation_summary"] = "Targeted validation passed."
        item["tests_run"] = ["python -m pytest tests/test_production_autonomy_readiness_report.py -> passed"]
        item["artifact_paths"] = [".aresforge/production_autonomy_readiness_reports/example.json"]
    queue_path.write_text(json.dumps(queue, indent=2) + "\n", encoding="utf-8")


def test_generate_production_autonomy_readiness_report_reviews_m155_m169(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_docs(config)
    _seed_queue(config)

    result = generate_production_autonomy_readiness_report(
        config,
        project_id="aresforge",
        sprint_start="M155",
        sprint_end="M169",
    )
    payload = result["payload"]

    assert result["ok"] is True
    assert payload["record_type"] == "production_autonomy_readiness_report_v1"
    assert payload["artifact_type"] == "production_autonomy_readiness_report_v1"
    assert payload["generated"] is True
    assert payload["project_id"] == "aresforge"
    assert payload["item_id"] == DEFAULT_ITEM_ID
    assert payload["run_id"] == "aresforge-m155-m169-production-autonomy-readiness"
    assert payload["status"] in {"ready", "ready_with_warnings"}
    assert payload["blocked"] is False
    assert payload["blocked_reasons"] == []
    assert payload["machine_gates_passed"] is True
    assert payload["autonomy_profile"] == "github_sync_dry_run"
    assert payload["mutation_performed"] is False
    assert payload["queue_mutation_performed"] is False
    assert payload["codex_execution_performed"] is False
    assert payload["model_execution_performed"] is False
    assert payload["github_execution_performed"] is False
    assert payload["patch_application_performed"] is False
    assert payload["local_only"] is True
    assert payload["milestones_reviewed"] == [f"M{number}" for number in range(155, 170)]
    assert payload["sprint_closeout_summary"]["all_milestone_items_complete"] is True
    assert len(payload["capability_summary"]) == 15
    assert payload["queue_summary"]["status_counts"] == {"done": 15}
    assert payload["docs_sync"]["consistent"] is True
    assert payload["codex_pilot_readiness"]["real_codex_allowed_by_report"] is False
    assert payload["github_issue_sync_status"]["live_sync_allowed_by_report"] is False
    assert payload["execution_boundary"]["automatic_next_item_execution_default_deny"] is True


def test_production_report_writes_optional_artifact(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_docs(config)
    _seed_queue(config)
    output = tmp_path / ".aresforge" / "production_autonomy_readiness_reports" / "m169.json"

    result = generate_production_autonomy_readiness_report(
        config,
        project_id="aresforge",
        sprint_start="M155",
        sprint_end="M169",
        output=output,
    )
    written = json.loads(output.read_text(encoding="utf-8"))

    assert result["ok"] is True
    assert result["wrote_output_file"] is True
    assert written["record_type"] == "production_autonomy_readiness_report_v1"
    assert written["artifacts_created"] == [str(output)]


def test_production_report_blocks_when_milestone_item_missing(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_docs(config)
    _seed_queue(config)
    queue_path = config.repo_root / ".aresforge" / "queue" / "work_items.json"
    queue = json.loads(queue_path.read_text(encoding="utf-8"))
    queue["work_items"] = [item for item in queue["work_items"] if "milestone:m169" not in item.get("tags", [])]
    queue_path.write_text(json.dumps(queue, indent=2) + "\n", encoding="utf-8")

    payload = generate_production_autonomy_readiness_report(
        config,
        project_id="aresforge",
        sprint_start="M155",
        sprint_end="M169",
    )["payload"]

    assert payload["blocked"] is True
    assert payload["status"] == "blocked"
    assert any("M169" in reason for reason in payload["blocked_reasons"])
