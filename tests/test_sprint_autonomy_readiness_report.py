import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.local_project_queue import add_queue_item, init_project_queue
from aresforge.operator.sprint_autonomy_readiness_report import (
    DEFAULT_ITEM_ID,
    SOURCE_OF_TRUTH_DOCS,
    generate_autonomy_readiness_report,
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
    milestones = " ".join(f"M{number}" for number in range(140, 155))
    for relative in SOURCE_OF_TRUTH_DOCS:
        path = config.repo_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"# {path.stem}\n\n{milestones}\n", encoding="utf-8")


def _seed_queue(config: AppConfig) -> None:
    assert init_project_queue(config)["ok"] is True
    for number in range(140, 155):
        item_id = DEFAULT_ITEM_ID if number == 154 else f"m{number}-milestone"
        assert add_queue_item(
            config,
            item_id=item_id,
            project_id="aresforge",
            repo_id="aresforge-main",
            title=f"M{number} milestone",
            description="Milestone implementation.",
            status="done",
            priority="high",
            item_type="documentation" if number == 154 else "orchestration",
            tags=[f"milestone:m{number}"],
            source="unit-test",
            notes="Validation evidence present.",
        )["ok"] is True
    queue_path = config.repo_root / ".aresforge" / "queue" / "work_items.json"
    queue = json.loads(queue_path.read_text(encoding="utf-8"))
    for item in queue["work_items"]:
        item["completion_commit"] = "abc123"
        item["validation_summary"] = "Targeted validation passed."
        item["tests_run"] = ["python -m pytest tests/test_sprint_autonomy_readiness_report.py -> passed"]
        item["artifact_paths"] = [".aresforge/autonomy_readiness_reports/example.json"]
    queue_path.write_text(json.dumps(queue, indent=2) + "\n", encoding="utf-8")


def test_generate_autonomy_readiness_report_reviews_m140_m154(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_docs(config)
    _seed_queue(config)

    result = generate_autonomy_readiness_report(
        config,
        project_id="aresforge",
        sprint_start="M140",
        sprint_end="M154",
    )
    payload = result["payload"]

    assert result["ok"] is True
    assert payload["record_type"] == "autonomy_readiness_report_v1"
    assert payload["artifact_type"] == "autonomy_readiness_report_v1"
    assert payload["generated"] is True
    assert payload["item_id"] == DEFAULT_ITEM_ID
    assert payload["project_id"] == "aresforge"
    assert payload["run_id"] == "aresforge-m140-m154-autonomy-readiness"
    assert payload["status"] in {"ready", "ready_with_warnings"}
    assert payload["blocked"] is False
    assert payload["blocked_reasons"] == []
    assert payload["machine_gates_passed"] is True
    assert payload["mutation_performed"] is False
    assert payload["external_execution_performed"] is False
    assert payload["model_execution_performed"] is False
    assert payload["codex_execution_performed"] is False
    assert payload["github_execution_performed"] is False
    assert payload["patch_application_performed"] is False
    assert payload["local_only"] is True
    assert payload["milestones_reviewed"] == [f"M{number}" for number in range(140, 155)]
    assert payload["sprint_closeout_summary"]["all_milestone_items_complete"] is True
    assert len(payload["capability_summary"]) == 15
    assert payload["queue_summary"]["status_counts"] == {"done": 15}
    assert payload["docs_sync"]["consistent"] is True
    assert payload["execution_boundary"]["real_codex_default_deny"] is True
    assert payload["readiness_summary"]["real_codex_low_risk_loop_ready"] is True


def test_report_writes_optional_artifact(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_docs(config)
    _seed_queue(config)
    output = tmp_path / ".aresforge" / "autonomy_readiness_reports" / "m154.json"

    result = generate_autonomy_readiness_report(
        config,
        project_id="aresforge",
        sprint_start="M140",
        sprint_end="M154",
        output=output,
    )
    written = json.loads(output.read_text(encoding="utf-8"))

    assert result["ok"] is True
    assert result["wrote_output_file"] is True
    assert written["record_type"] == "autonomy_readiness_report_v1"
    assert written["artifacts_created"] == [str(output)]


def test_report_blocks_when_milestone_item_missing(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_docs(config)
    _seed_queue(config)
    queue_path = config.repo_root / ".aresforge" / "queue" / "work_items.json"
    queue = json.loads(queue_path.read_text(encoding="utf-8"))
    queue["work_items"] = [item for item in queue["work_items"] if "milestone:m154" not in item.get("tags", [])]
    queue_path.write_text(json.dumps(queue, indent=2) + "\n", encoding="utf-8")

    payload = generate_autonomy_readiness_report(
        config,
        project_id="aresforge",
        sprint_start="M140",
        sprint_end="M154",
    )["payload"]

    assert payload["blocked"] is True
    assert payload["status"] == "blocked"
    assert any("M154" in reason for reason in payload["blocked_reasons"])
