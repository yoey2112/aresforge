import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.github_issue_state_reconciliation import (
    RECORD_TYPE,
    reconcile_github_issue_state,
)
from aresforge.operator.github_link_registry import record_github_link
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


def _payload(result: dict[str, object]) -> dict[str, object]:
    return result["payload"]  # type: ignore[index]


def _seed_queue(config: AppConfig) -> Path:
    result = init_project_queue(config)
    assert result["ok"] is True
    queue_path = Path(str(result["path"]))
    assert add_queue_item(
        config,
        item_id="m174-github-issue-state-reconciliation",
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M174 GitHub Issue State Reconciliation",
        status="ready",
        priority="high",
        item_type="sync",
        tags=["milestone:m174", "github-issue-sync"],
    )["ok"] is True
    assert add_queue_item(
        config,
        item_id="needs-create",
        project_id="aresforge",
        repo_id="aresforge-main",
        title="Needs Create",
        status="ready",
        priority="high",
        item_type="feature",
    )["ok"] is True
    assert add_queue_item(
        config,
        item_id="done-open",
        project_id="aresforge",
        repo_id="aresforge-main",
        title="Done Open",
        status="done",
        priority="normal",
        item_type="feature",
    )["ok"] is True
    assert add_queue_item(
        config,
        item_id="closed-active",
        project_id="aresforge",
        repo_id="aresforge-main",
        title="Closed Active",
        status="ready",
        priority="normal",
        item_type="feature",
    )["ok"] is True
    assert add_queue_item(
        config,
        item_id="drift-comment",
        project_id="aresforge",
        repo_id="aresforge-main",
        title="Drift Comment",
        status="done",
        priority="normal",
        item_type="feature",
    )["ok"] is True
    raw = json.loads(queue_path.read_text(encoding="utf-8"))
    for item in raw["work_items"]:
        if item["item_id"] == "done-open":
            item["github_issue"] = {"number": 10, "url": "https://github.com/local/aresforge/issues/10"}
        if item["item_id"] == "closed-active":
            item["github_issue"] = {"number": 11, "url": "https://github.com/local/aresforge/issues/11"}
        if item["item_id"] == "drift-comment":
            item["github_issue"] = {"number": 12, "url": "https://github.com/local/aresforge/issues/12"}
            item["validation_summary"] = "Validation passed."
            item["tests_run"] = ["python -m pytest tests/test_github_issue_state_reconciliation.py -> passed"]
    queue_path.write_text(json.dumps(raw, indent=2) + "\n", encoding="utf-8")
    return queue_path


def _state_file(tmp_path: Path) -> Path:
    path = tmp_path / "github-state.json"
    path.write_text(
        json.dumps(
            {
                "issues": [
                    {
                        "number": 10,
                        "title": "Done Open",
                        "state": "open",
                        "url": "https://github.com/local/aresforge/issues/10",
                        "labels": ["aresforge-queue", "status:done", "type:feature", "priority:normal"],
                    },
                    {
                        "number": 11,
                        "title": "Closed Active",
                        "state": "closed",
                        "url": "https://github.com/local/aresforge/issues/11",
                        "labels": ["aresforge-queue"],
                    },
                    {
                        "number": 12,
                        "title": "Old Drift Comment",
                        "state": "open",
                        "url": "https://github.com/local/aresforge/issues/12",
                        "labels": ["aresforge-queue"],
                    },
                ]
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def test_dry_run_recommends_create_close_reopen_update_and_comment_from_mocked_state(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    state_path = _state_file(tmp_path)

    payload = _payload(
        reconcile_github_issue_state(
            config,
            project_id="aresforge",
            github_state_path=state_path,
            dry_run=True,
        )
    )
    items = {item["item_id"]: item for item in payload["reconciliation_items"]}  # type: ignore[index]
    actions = {
        item_id: {action["recommended_action"] for action in item["recommended_actions"]}
        for item_id, item in items.items()
    }

    assert payload["record_type"] == RECORD_TYPE
    assert payload["status"] == "dry_run_ready"
    assert payload["sync_status"] == "dry_run_ready"
    assert payload["blocked"] is False
    assert payload["generated"] is True
    assert payload["project_id"] == "aresforge"
    assert payload["repository"] == "local/aresforge"
    assert payload["issue_number"] is None
    assert payload["issue_url"] == ""
    assert payload["pr_number"] is None
    assert payload["pr_url"] == ""
    assert payload["machine_gates_passed"] is True
    assert payload["autonomy_profile"] == "github_sync_dry_run"
    assert payload["dry_run"] is True
    assert payload["github_enabled"] is False
    assert payload["github_execution_performed"] is False
    assert payload["mutation_performed"] is False
    assert payload["github_issue_mutation_performed"] is False
    assert payload["queue_mutation_performed"] is False
    assert payload["recovery_available"] is True
    assert payload["local_only"] is True
    assert payload["github_state_source"] == "mocked_state_file"
    assert payload["github_state_available"] is True
    assert "create" in actions["needs-create"]
    assert "close" in actions["done-open"]
    assert "reopen" in actions["closed-active"]
    assert {"update", "comment", "close"}.issubset(actions["drift-comment"])
    assert payload["operation_counts"]["create"] >= 1  # type: ignore[index]
    assert payload["operation_counts"]["close"] >= 2  # type: ignore[index]
    assert payload["operation_counts"]["reopen"] == 1  # type: ignore[index]


def test_dry_run_without_github_state_skips_linked_items_but_plans_unlinked_create(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)

    payload = _payload(reconcile_github_issue_state(config, project_id="aresforge", dry_run=True))
    items = {item["item_id"]: item for item in payload["reconciliation_items"]}  # type: ignore[index]

    assert payload["blocked"] is False
    assert payload["github_state_source"] == "not_requested"
    assert payload["github_state_available"] is False
    assert items["needs-create"]["sync_status"] == "create_recommended"
    assert items["done-open"]["sync_status"] == "skip_recommended"
    assert items["done-open"]["recommended_actions"][0]["recommended_action"] == "skip"
    assert payload["github_execution_performed"] is False
    assert payload["mutation_performed"] is False


def test_registry_link_is_used_when_queue_metadata_has_no_issue(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    registry_path = tmp_path / ".aresforge" / "github_link_registry" / "links.json"
    record_github_link(
        config,
        item_id="needs-create",
        queue_item_id="needs-create",
        repository="local/aresforge",
        registry_path=registry_path,
        issue_number=44,
        issue_url="https://github.com/local/aresforge/issues/44",
    )
    state_path = tmp_path / "github-state.json"
    state_path.write_text(
        json.dumps({"issues": [{"number": 44, "title": "Needs Create", "state": "open", "labels": ["aresforge-queue"]}]})
        + "\n",
        encoding="utf-8",
    )

    payload = _payload(
        reconcile_github_issue_state(
            config,
            project_id="aresforge",
            registry_path=registry_path,
            github_state_path=state_path,
            dry_run=True,
        )
    )
    items = {item["item_id"]: item for item in payload["reconciliation_items"]}  # type: ignore[index]

    assert items["needs-create"]["issue_number"] == 44
    assert items["needs-create"]["registry_link"]["issue_number"] == 44
    assert items["needs-create"]["recommended_actions"][0]["recommended_action"] in {"update", "skip"}


def test_output_path_writes_reconciliation_and_refuses_overwrite(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    output = tmp_path / ".aresforge" / "github_issue_state_reconciliation" / "m174.json"

    first = reconcile_github_issue_state(config, project_id="aresforge", output=output)
    second = reconcile_github_issue_state(config, project_id="aresforge", output=output)

    assert first["ok"] is True
    written = json.loads(output.read_text(encoding="utf-8"))
    assert written["record_type"] == RECORD_TYPE
    assert str(output) in written["artifacts_created"]
    assert second["ok"] is False
    assert second["payload"]["blocked"] is True
    assert second["payload"]["github_execution_performed"] is False
    assert second["payload"]["mutation_performed"] is False
    assert any("Output file already exists" in reason for reason in second["payload"]["blocked_reasons"])
