import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.github_sync_recovery_idempotency import (
    RECORD_TYPE,
    inspect_github_sync_recovery,
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


def _payload(result: dict[str, object]) -> dict[str, object]:
    return result["payload"]  # type: ignore[index]


def _seed_queue(config: AppConfig) -> Path:
    result = init_project_queue(config)
    assert result["ok"] is True
    queue_path = Path(str(result["path"]))
    for item_id, title, status in (
        ("m179-github-sync-recovery-and-idempotency", "M179 GitHub Sync Recovery and Idempotency", "ready"),
        ("completed-issue-sync", "Completed issue sync", "done"),
        ("partial-issue-sync", "Partial issue sync", "ready"),
        ("partial-pr-evidence-sync", "Partial PR evidence sync", "done"),
    ):
        assert add_queue_item(
            config,
            item_id=item_id,
            project_id="aresforge",
            repo_id="aresforge-main",
            title=title,
            status=status,
            priority="high",
            item_type="sync",
        )["ok"] is True
    raw = json.loads(queue_path.read_text(encoding="utf-8"))
    for item in raw["work_items"]:
        if item["item_id"] == "partial-pr-evidence-sync":
            item["github_issue"] = {
                "number": 77,
                "url": "https://github.com/local/aresforge/issues/77",
                "state": "open",
            }
    queue_path.write_text(json.dumps(raw, indent=2) + "\n", encoding="utf-8")
    return queue_path


def _write_preflight(config: AppConfig, artifact_dir: str, item_id: str, command: str) -> Path:
    path = config.artifact_root / artifact_dir / "gates" / f"{item_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "artifact_type": f"{artifact_dir}_preflight_v1",
                "item_id": item_id,
                "project_id": "aresforge",
                "repository": "local/aresforge",
                "idempotency_key": f"preflight:{item_id}:{command}",
                "github_execution_performed": False,
                "mutation_performed": False,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def _write_registry(registry_path: Path, records: list[dict[str, object]]) -> None:
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    normalized = []
    for record in records:
        queue_item_id = str(record["queue_item_id"])
        repository = str(record.get("repository", "local/aresforge"))
        normalized.append(
            {
                "record_type": "github_link_registry_record_v1",
                "project_id": "aresforge",
                "queue_item_id": queue_item_id,
                "repository": repository,
                "issue_number": record.get("issue_number"),
                "issue_url": record.get("issue_url", ""),
                "pr_number": record.get("pr_number"),
                "pr_url": record.get("pr_url", ""),
                "comment_id": record.get("comment_id", ""),
                "comment_url": record.get("comment_url", ""),
                "sync_status": record.get("sync_status", "synced"),
                "last_sync_time": "2026-06-02T00:00:00Z",
                "last_sync_result": record.get("last_sync_result", ""),
                "linked_by": "test",
                "link_source": record.get("link_source", ""),
                "warnings": [],
                "idempotency_key": f"link:aresforge:{queue_item_id}:local-aresforge",
                "blocked": False,
                "blocked_reasons": [],
                "github_execution_performed": False,
                "mutation_performed": False,
                "local_only": True,
            }
        )
    registry_path.write_text(
        json.dumps({"schema_version": "1.0", "updated_at": "2026-06-02T00:00:00Z", "links": normalized}, indent=2)
        + "\n",
        encoding="utf-8",
    )


def test_recovery_inspection_skips_registry_completed_issue_creation(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    registry_path = tmp_path / ".aresforge" / "github_link_registry" / "links.json"
    _write_registry(
        registry_path,
        [
            {
                "queue_item_id": "completed-issue-sync",
                "issue_number": 42,
                "issue_url": "https://github.com/local/aresforge/issues/42",
                "link_source": "create-github-issue-real-run-gate",
            }
        ],
    )
    _write_preflight(
        config,
        "github_issue_creation_real_run_gate",
        "completed-issue-sync",
        "create-github-issue-real-run-gate",
    )

    payload = _payload(inspect_github_sync_recovery(config, registry_path=registry_path))
    completed = next(item for item in payload["recovery_items"] if item["item_id"] == "completed-issue-sync")
    issue_creation = next(op for op in completed["operations"] if op["operation_type"] == "issue_creation")

    assert payload["record_type"] == RECORD_TYPE
    assert payload["sync_status"] == "recovery_inspected"
    assert payload["dry_run"] is True
    assert payload["github_enabled"] is False
    assert payload["github_execution_performed"] is False
    assert payload["mutation_performed"] is False
    assert payload["local_only"] is True
    assert payload["machine_gates_passed"] is True
    assert issue_creation["sync_status"] == "complete"
    assert issue_creation["registry_completion_proves_noop"] is True
    assert issue_creation["recovery_available"] is False
    assert "Skip this mutation" in issue_creation["next_safe_action"]


def test_preflight_without_registry_completion_gets_repair_plan(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    preflight = _write_preflight(
        config,
        "github_issue_creation_real_run_gate",
        "partial-issue-sync",
        "create-github-issue-real-run-gate",
    )

    payload = _payload(inspect_github_sync_recovery(config))
    partial = next(item for item in payload["recovery_items"] if item["item_id"] == "partial-issue-sync")
    issue_creation = next(op for op in partial["operations"] if op["operation_type"] == "issue_creation")

    assert partial["sync_status"] == "partial_recovery_available"
    assert partial["recovery_available"] is True
    assert issue_creation["sync_status"] == "partial"
    assert issue_creation["preflight_artifacts"] == [str(preflight)]
    assert issue_creation["registry_completion_proves_noop"] is False
    assert "record the issue link locally" in issue_creation["next_safe_action"]
    assert payload["operation_counts"]["operations_partial"] == 1
    assert payload["repair_plan"][0]["operation_type"] == "issue_creation"
    assert payload["repair_plan"][0]["github_execution_performed"] is False


def test_pr_evidence_partial_can_resume_when_pr_link_exists(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    registry_path = tmp_path / ".aresforge" / "github_link_registry" / "links.json"
    _write_registry(
        registry_path,
        [
            {
                "queue_item_id": "partial-pr-evidence-sync",
                "issue_number": 77,
                "issue_url": "https://github.com/local/aresforge/issues/77",
                "pr_number": 177,
                "pr_url": "https://github.com/local/aresforge/pull/177",
                "link_source": "create-pr-draft-gate",
            }
        ],
    )
    _write_preflight(
        config,
        "pr_evidence_comment_sync",
        "partial-pr-evidence-sync",
        "sync-pr-evidence-comment",
    )

    payload = _payload(inspect_github_sync_recovery(config, registry_path=registry_path))
    resume = next(plan for plan in payload["resume_plan"] if plan["operation_type"] == "pr_evidence_comment_sync")
    item = next(item for item in payload["recovery_items"] if item["item_id"] == "partial-pr-evidence-sync")
    operation = next(op for op in item["operations"] if op["operation_type"] == "pr_evidence_comment_sync")

    assert operation["sync_status"] == "partial"
    assert operation["pr_number"] == 177
    assert operation["recovery_available"] is True
    assert resume["sync_status"] == "resume_available"
    assert resume["pr_number"] == 177
    assert resume["dry_run"] is True
    assert resume["mutation_performed"] is False
