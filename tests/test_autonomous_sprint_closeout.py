import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.autonomous_sprint_closeout import (
    SOURCE_OF_TRUTH_DOCS,
    generate_autonomous_sprint_closeout,
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


def _seed_docs(config: AppConfig) -> None:
    milestones = " ".join(f"M{number}" for number in range(125, 140))
    for relative in SOURCE_OF_TRUTH_DOCS:
        path = config.repo_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"# {path.stem}\n\n{milestones}\n", encoding="utf-8")


def _seed_queue(config: AppConfig) -> None:
    assert init_project_queue(config)["ok"] is True
    for number in range(125, 140):
        item_id = f"m{number}-milestone"
        assert add_queue_item(
            config,
            item_id=item_id,
            project_id="aresforge",
            repo_id="aresforge-main",
            title=f"M{number} milestone",
            description="Milestone implementation.",
            status="done",
            priority="high",
            item_type="feature" if number != 139 else "documentation",
            tags=[f"milestone:m{number}"],
            source="unit-test",
            notes="Validation evidence present.",
        )["ok"] is True
    queue_path = config.repo_root / ".aresforge" / "queue" / "work_items.json"
    queue = json.loads(queue_path.read_text(encoding="utf-8"))
    for item in queue["work_items"]:
        item["completion_commit"] = "abc123"
        item["validation_summary"] = "Targeted validation passed."
        item["tests_run"] = ["python -m pytest tests/test_autonomous_sprint_closeout.py -> passed"]
        item["artifact_paths"] = ["artifacts/autonomous-sprint-closeout/aresforge/example.json"]
    queue_path.write_text(json.dumps(queue, indent=2) + "\n", encoding="utf-8")
    transaction_path = config.repo_root / ".aresforge" / "queue" / "transaction_log.json"
    transaction_path.write_text(
        json.dumps({"transactions": [{"item_id": "m139-milestone", "new_status": "done"}]}, indent=2) + "\n",
        encoding="utf-8",
    )


def test_generate_autonomous_sprint_closeout_reviews_full_sprint(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_docs(config)
    _seed_queue(config)

    result = generate_autonomous_sprint_closeout(
        config,
        project_id="aresforge",
        sprint_start="M125",
        sprint_end="M139",
        dry_run=True,
    )
    payload = result["payload"]

    assert result["ok"] is True
    assert payload["closeout_type"] == "autonomous_sprint_closeout_v1"
    assert payload["project_id"] == "aresforge"
    assert payload["dry_run"] is True
    assert payload["docs_applied"] is False
    assert payload["milestones_reviewed"] == [f"M{number}" for number in range(125, 140)]
    assert len(payload["completed_items"]) == 15
    assert payload["incomplete_items"] == []
    assert payload["blocked_items"] == []
    assert payload["machine_gates_available"]["available"] is True
    assert payload["machine_gates_available"]["read_only_closeout_gate_passed"] is True
    assert payload["agents_available"]["available"] is True
    assert payload["orchestration_available"]["available"] is True
    assert payload["llm_decision_available"]["available"] is True
    assert payload["codex_execution_available"]["available"] is True
    assert payload["local_llm_execution_available"]["available"] is True
    assert payload["github_sync_available"]["available"] is True
    assert payload["docs_consistency"]["consistent"] is True
    assert payload["local_only"] is True
    assert payload["execution_performed"] is False


def test_closeout_reports_docs_consistency_warnings(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_docs(config)
    _seed_queue(config)
    build_state = config.repo_root / "docs" / "context" / "BUILD_STATE.md"
    build_state.write_text("# Build State\n\nM125 M126\n", encoding="utf-8")

    payload = generate_autonomous_sprint_closeout(
        config,
        project_id="aresforge",
        sprint_start="M125",
        sprint_end="M139",
        dry_run=True,
    )["payload"]

    assert payload["docs_consistency"]["consistent"] is False
    assert "docs/context/BUILD_STATE.md" in payload["docs_consistency"]["missing_milestone_mentions"]
    assert any("missing sprint milestone mentions" in warning for warning in payload["warnings"])


def test_closeout_output_path_writes_artifact(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_docs(config)
    _seed_queue(config)
    output = tmp_path / "artifacts" / "autonomous-sprint-closeout" / "m139.json"

    result = generate_autonomous_sprint_closeout(
        config,
        project_id="aresforge",
        sprint_start="M125",
        sprint_end="M139",
        dry_run=True,
        output=output,
    )
    written = json.loads(output.read_text(encoding="utf-8"))

    assert result["ok"] is True
    assert result["wrote_output_file"] is True
    assert written["closeout_type"] == "autonomous_sprint_closeout_v1"
    assert written["closeout_artifact_path"] == str(output)


def test_apply_docs_only_dry_run_does_not_mutate_docs(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_docs(config)
    _seed_queue(config)
    doc_path = config.repo_root / "docs" / "operator" / "LOCAL_OPERATOR_USAGE.md"
    before = doc_path.read_text(encoding="utf-8")

    result = generate_autonomous_sprint_closeout(
        config,
        project_id="aresforge",
        sprint_start="M125",
        sprint_end="M139",
        dry_run=True,
        apply_docs_only=True,
        output=tmp_path / "artifacts" / "closeout.json",
    )
    after = doc_path.read_text(encoding="utf-8")

    assert result["ok"] is False
    assert result["payload"]["docs_applied"] is False
    assert before == after
    assert any("--dry-run" in blocker for blocker in result["payload"]["blockers"])
