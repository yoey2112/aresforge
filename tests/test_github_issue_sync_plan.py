import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.github_issue_sync_plan import (
    DEFAULT_ITEM_ID,
    RECORD_TYPE,
    plan_github_issue_sync,
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


def _seed_queue(config: AppConfig) -> Path:
    result = init_project_queue(config)
    assert result["ok"] is True
    queue_path = Path(str(result["path"]))
    assert add_queue_item(
        config,
        item_id="m161-codex-loop-validation-evidence-bundle",
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M161 Codex Loop Validation Evidence Bundle",
        status="done",
        priority="high",
        item_type="orchestration",
        tags=["milestone:m161"],
    )["ok"] is True
    assert add_queue_item(
        config,
        item_id=DEFAULT_ITEM_ID,
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M162 GitHub Issue Sync Plan from Queue Items",
        description="Generate a local-only GitHub issue sync plan from queue items.",
        status="ready",
        priority="high",
        item_type="sync",
        tags=["milestone:m162", "github-issue-sync", "local-only"],
        dependencies=["m161-codex-loop-validation-evidence-bundle"],
    )["ok"] is True
    assert add_queue_item(
        config,
        item_id="feature-unlinked",
        project_id="aresforge",
        repo_id="aresforge-main",
        title="Unlinked queue feature",
        description="Create an issue draft for this item.",
        status="ready",
        priority="normal",
        item_type="feature",
        tags=["area:queue", "milestone:m162"],
        dependencies=["m161-codex-loop-validation-evidence-bundle"],
    )["ok"] is True
    assert add_queue_item(
        config,
        item_id="linked-done",
        project_id="aresforge",
        repo_id="aresforge-main",
        title="Linked completed item",
        description="Update linked issue metadata and add evidence comments.",
        status="done",
        priority="high",
        item_type="documentation",
        tags=["milestone:m162"],
        evidence_required=["validation_evidence"],
    )["ok"] is True
    assert add_queue_item(
        config,
        item_id="blocked-item",
        project_id="aresforge",
        repo_id="aresforge-main",
        title="Blocked item",
        description="This should be skipped while locally blocked.",
        status="blocked",
        priority="normal",
        item_type="task",
        blocked_by=["missing-upstream"],
    )["ok"] is True

    raw = json.loads(queue_path.read_text(encoding="utf-8"))
    for item in raw["work_items"]:
        if item["item_id"] == "linked-done":
            item["github_issue"] = {
                "number": 912,
                "url": "https://github.com/local/aresforge/issues/912",
            }
            item["validation_summary"] = "Targeted validation passed."
            item["tests_run"] = ["python -m pytest tests/test_github_issue_sync_plan.py -> passed"]
            item["evidence_note"] = "Local evidence exists for future issue comment."
    queue_path.write_text(json.dumps(raw, indent=2) + "\n", encoding="utf-8")
    return queue_path


def _payload(result: dict[str, object]) -> dict[str, object]:
    return result["payload"]  # type: ignore[index]


def test_plan_github_issue_sync_maps_queue_items_to_issue_fields(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)

    result = plan_github_issue_sync(config, project_id="aresforge")
    payload = _payload(result)

    assert result["ok"] is True
    assert payload["record_type"] == RECORD_TYPE
    assert payload["status"] == "plan_generated"
    assert payload["blocked"] is False
    assert payload["generated"] is True
    assert payload["project_id"] == "aresforge"
    assert payload["item_id"] == DEFAULT_ITEM_ID
    assert payload["machine_gates_passed"] is True
    assert payload["local_only"] is True
    assert payload["github_execution_performed"] is False
    assert payload["mutation_performed"] is False
    assert payload["queue_mutation_performed"] is False
    assert payload["codex_execution_performed"] is False
    assert payload["model_execution_performed"] is False
    assert payload["patch_application_performed"] is False

    by_id = {entry["item_id"]: entry for entry in payload["issue_sync_items"]}
    unlinked = by_id["feature-unlinked"]
    assert unlinked["issue_draft"]["title"] == "Unlinked queue feature"
    assert "Create an issue draft" in unlinked["issue_draft"]["body"]
    assert "type:feature" in unlinked["issue_draft"]["labels"]
    assert unlinked["issue_draft"]["milestone"] == "M162"
    assert unlinked["recommendations"][0]["recommended_action"] == "create"


def test_plan_detects_linked_issues_and_recommends_update_and_comment(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)

    payload = _payload(plan_github_issue_sync(config, project_id="aresforge"))
    by_id = {entry["item_id"]: entry for entry in payload["issue_sync_items"]}
    linked = by_id["linked-done"]
    actions = [entry["recommended_action"] for entry in linked["recommendations"]]

    assert linked["linked_issue"]["linked"] is True
    assert linked["linked_issue"]["issue_number"] == 912
    assert actions == ["update", "comment"]
    assert linked["issue_draft"]["comments"][0]["comment_type"] == "validation_evidence"
    assert payload["operation_counts"]["update"] >= 1
    assert payload["operation_counts"]["comment"] >= 1


def test_plan_skips_locally_blocked_items_without_mutation(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)

    payload = _payload(plan_github_issue_sync(config, project_id="aresforge"))
    by_id = {entry["item_id"]: entry for entry in payload["issue_sync_items"]}
    blocked = by_id["blocked-item"]

    assert blocked["blocked"] is True
    assert blocked["recommendations"][0]["recommended_action"] == "skip"
    assert blocked["github_execution_performed"] is False
    assert payload["github_operations_performed"] is False
    assert payload["github_mutation_allowed"] is False


def test_plan_output_path_writes_local_artifact_and_refuses_overwrite(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    output = tmp_path / ".aresforge" / "github_issue_sync" / "plan.json"

    first = plan_github_issue_sync(config, project_id="aresforge", output=output)
    second = plan_github_issue_sync(config, project_id="aresforge", output=output)

    assert first["ok"] is True
    written = json.loads(output.read_text(encoding="utf-8"))
    assert written["artifacts_created"] == [str(output)]
    assert second["ok"] is False
    assert second["payload"]["blocked"] is True
    assert any("Output file already exists" in reason for reason in second["payload"]["blocked_reasons"])
