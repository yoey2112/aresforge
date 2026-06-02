import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.github_issue_closure_recommendation_gate import (
    RECORD_TYPE,
    recommend_github_issue_closure,
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
        item_id="m164-github-issue-status-comment-sync",
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M164 GitHub Issue Status Comment Sync",
        status="done",
        priority="high",
        item_type="sync",
    )["ok"] is True
    assert add_queue_item(
        config,
        item_id="m165-github-issue-closure-recommendation-gate",
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M165 GitHub Issue Closure Recommendation Gate",
        description="Recommend GitHub issue closure from local evidence.",
        status="done",
        priority="high",
        item_type="sync",
        tags=["milestone:m165", "github-issue-sync", "machine-gated"],
        dependencies=["m164-github-issue-status-comment-sync"],
        notes="Closure must remain recommendation-only.",
    )["ok"] is True
    assert add_queue_item(
        config,
        item_id="not-done-item",
        project_id="aresforge",
        repo_id="aresforge-main",
        title="Not done item",
        description="Missing completion evidence.",
        status="in_progress",
        priority="normal",
        item_type="task",
    )["ok"] is True

    raw = json.loads(queue_path.read_text(encoding="utf-8"))
    for item in raw["work_items"]:
        if item["item_id"] == "m165-github-issue-closure-recommendation-gate":
            item["github_issue"] = {
                "number": 165,
                "url": "https://github.com/local/aresforge/issues/165",
                "state": "open",
            }
            item["completed_at"] = "2026-06-02T02:00:00Z"
            item["completed_by"] = "local_operator"
            item["completion_commit"] = "abc1234"
            item["validation_summary"] = "Targeted validation passed."
            item["tests_run"] = ["python -m pytest tests/test_github_issue_closure_recommendation_gate.py -> passed"]
            item["evidence_note"] = "Local validation and artifact bundle evidence support closure review."
            item["artifact_paths"] = [".aresforge/github_issue_closure_recommendations/m165.json"]
            item["completion_evidence"] = {
                "record_type": "github_issue_closure_recommendation_gate_v1",
                "artifacts_created": [".aresforge/github_issue_closure_recommendations/m165.json"],
            }
        if item["item_id"] == "not-done-item":
            item["github_issue"] = {"number": 999, "state": "open"}
    queue_path.write_text(json.dumps(raw, indent=2) + "\n", encoding="utf-8")
    return queue_path


def _payload(result: dict[str, object]) -> dict[str, object]:
    return result["payload"]  # type: ignore[index]


def test_recommends_close_when_queue_validation_artifacts_and_gates_support_it(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)

    payload = _payload(
        recommend_github_issue_closure(
            config,
            item_id="m165-github-issue-closure-recommendation-gate",
        )
    )

    assert payload["record_type"] == RECORD_TYPE
    assert payload["status"] == "close_recommended"
    assert payload["blocked"] is False
    assert payload["closure_recommended"] is True
    assert payload["keep_open_recommended"] is False
    assert payload["issue_closure_recommendation"] == "close"
    assert payload["issue_closure_allowed"] is False
    assert payload["issue_closed"] is False
    assert payload["mutation_performed"] is False
    assert payload["queue_mutation_performed"] is False
    assert payload["codex_execution_performed"] is False
    assert payload["model_execution_performed"] is False
    assert payload["github_execution_performed"] is False
    assert payload["patch_application_performed"] is False
    assert payload["local_only"] is True
    assert payload["machine_gates_passed"] is True
    assert payload["queue_completion"]["done"] is True
    assert payload["validation_evidence"]["present"] is True
    assert payload["artifact_bundle"]["present"] is True
    assert payload["linked_issue"]["issue_number"] == 165
    assert payload["linked_issue_state"] == "open"


def test_recommends_keep_open_when_item_is_not_done(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)

    payload = _payload(
        recommend_github_issue_closure(
            config,
            item_id="not-done-item",
        )
    )

    assert payload["status"] == "keep_open_recommended"
    assert payload["blocked"] is True
    assert payload["closure_recommended"] is False
    assert payload["keep_open_recommended"] is True
    assert payload["issue_closure_allowed"] is False
    assert payload["github_execution_performed"] is False
    assert any("status must be done" in reason for reason in payload["blocked_reasons"])
    assert any("Validation evidence is required" in reason for reason in payload["blocked_reasons"])


def test_already_closed_linked_issue_is_not_recommended_for_closure(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)

    payload = _payload(
        recommend_github_issue_closure(
            config,
            item_id="m165-github-issue-closure-recommendation-gate",
            linked_issue_state="closed",
        )
    )

    assert payload["status"] == "keep_open_recommended"
    assert payload["linked_issue_state"] == "closed"
    assert payload["closure_recommended"] is False
    assert payload["issue_closed"] is False
    assert any("already closed" in reason for reason in payload["blocked_reasons"])


def test_output_path_writes_local_artifact_and_refuses_overwrite(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    output = tmp_path / ".aresforge" / "github_issue_closure_recommendations" / "m165.json"

    first = recommend_github_issue_closure(
        config,
        item_id="m165-github-issue-closure-recommendation-gate",
        output=output,
    )
    second = recommend_github_issue_closure(
        config,
        item_id="m165-github-issue-closure-recommendation-gate",
        output=output,
    )

    assert first["ok"] is True
    written = json.loads(output.read_text(encoding="utf-8"))
    assert str(output) in written["artifacts_created"]
    assert second["ok"] is False
    assert second["payload"]["blocked"] is True
    assert second["payload"]["closure_recommended"] is False
    assert any("Output file already exists" in reason for reason in second["payload"]["blocked_reasons"])
