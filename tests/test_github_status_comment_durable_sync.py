import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.github_issue_status_comment_sync import LIVE_AUTONOMY_PROFILE, STATUS_COMMENT_MARKER
from aresforge.operator.github_link_registry import record_github_link
from aresforge.operator.github_status_comment_durable_sync import (
    RECORD_TYPE,
    sync_github_status_comment_durable,
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
    assert add_queue_item(
        config,
        item_id="m172-queue-to-github-issue-backfill",
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M172 Queue-to-GitHub Issue Backfill",
        status="done",
        priority="high",
        item_type="sync",
    )["ok"] is True
    assert add_queue_item(
        config,
        item_id="m173-github-status-comment-durable-sync",
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M173 GitHub Status Comment Durable Sync",
        description="Durably sync one managed GitHub status comment.",
        status="ready",
        priority="high",
        item_type="sync",
        tags=["milestone:m173", "github-issue-sync", "durable"],
        dependencies=["m172-queue-to-github-issue-backfill"],
        notes="Status comment must include queue, run, validation, artifacts, gates, and next safe action.",
    )["ok"] is True
    raw = json.loads(queue_path.read_text(encoding="utf-8"))
    for item in raw["work_items"]:
        if item["item_id"] == "m173-github-status-comment-durable-sync":
            item["github_issue"] = {
                "number": 173,
                "url": "https://github.com/local/aresforge/issues/173",
            }
            item["validation_summary"] = "Durable status comment validation passed."
            item["tests_run"] = ["python -m pytest tests/test_github_status_comment_durable_sync.py -> passed"]
            item["evidence_note"] = "Local durable evidence exists."
            item["artifact_paths"] = [".aresforge/github_status_comment_durable/m173.json"]
    queue_path.write_text(json.dumps(raw, indent=2) + "\n", encoding="utf-8")
    return queue_path


class _FakeStatusCommentClient:
    def __init__(self, existing: dict[str, object] | None = None) -> None:
        self.existing = existing
        self.find_calls: list[dict[str, object]] = []
        self.create_calls: list[dict[str, object]] = []
        self.update_calls: list[dict[str, object]] = []

    def find_status_comment(self, *, repo: str, issue_number: int, marker: str) -> dict[str, object] | None:
        self.find_calls.append({"repo": repo, "issue_number": issue_number, "marker": marker})
        return self.existing

    def create_comment(self, *, repo: str, issue_number: int, body: str) -> dict[str, object]:
        self.create_calls.append({"repo": repo, "issue_number": issue_number, "body": body})
        return {"id": 5001, "html_url": "https://github.test/local/aresforge/issues/173#issuecomment-5001"}

    def update_comment(self, *, repo: str, comment_id: int | str, body: str) -> dict[str, object]:
        self.update_calls.append({"repo": repo, "comment_id": comment_id, "body": body})
        return {"id": comment_id, "html_url": f"https://github.test/local/aresforge/issues/173#issuecomment-{comment_id}"}


def test_dry_run_generates_durable_status_comment_without_github_or_registry_mutation(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    client = _FakeStatusCommentClient()

    payload = _payload(
        sync_github_status_comment_durable(
            config,
            item_id="m173-github-status-comment-durable-sync",
            dry_run=True,
            github_client=client,
        )
    )

    assert payload["record_type"] == RECORD_TYPE
    assert payload["status"] == "dry_run_ready"
    assert payload["sync_status"] == "dry_run_ready"
    assert payload["blocked"] is False
    assert payload["issue_number"] == 173
    assert payload["machine_gates_passed"] is True
    assert payload["dry_run"] is True
    assert payload["github_enabled"] is False
    assert payload["status_comment_synced"] is False
    assert payload["mutation_performed"] is False
    assert payload["registry_mutation_performed"] is False
    assert payload["github_execution_performed"] is False
    assert payload["recovery_available"] is True
    assert payload["local_only"] is True
    assert STATUS_COMMENT_MARKER in payload["status_comment_body"]
    assert "Durable status comment validation passed." in payload["status_comment_body"]
    assert ".aresforge/github_status_comment_durable/m173.json" in payload["status_comment_body"]
    assert client.find_calls == []
    assert client.create_calls == []
    assert client.update_calls == []


def test_mocked_live_create_records_comment_id_in_registry(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    client = _FakeStatusCommentClient()
    registry_path = tmp_path / ".aresforge" / "github_link_registry" / "links.json"

    payload = _payload(
        sync_github_status_comment_durable(
            config,
            item_id="m173-github-status-comment-durable-sync",
            registry_path=registry_path,
            dry_run=False,
            github_enabled=True,
            autonomy_profile=LIVE_AUTONOMY_PROFILE,
            github_client=client,
        )
    )

    assert payload["blocked"] is False
    assert payload["status"] == "status_comment_synced"
    assert payload["sync_status"] == "status_comment_synced"
    assert payload["status_comment_operation"] == "create"
    assert payload["managed_comment_id"] == "5001"
    assert payload["github_execution_performed"] is True
    assert payload["mutation_performed"] is True
    assert payload["registry_mutation_performed"] is True
    assert payload["queue_mutation_performed"] is False
    assert payload["local_only"] is False

    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    record = registry["links"][0]
    assert record["queue_item_id"] == "m173-github-status-comment-durable-sync"
    assert record["issue_number"] == 173
    assert record["comment_id"] == "5001"
    assert record["sync_status"] == "status_comment_synced"


def test_registry_comment_id_drives_idempotent_update_without_find_or_create(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    registry_path = tmp_path / ".aresforge" / "github_link_registry" / "links.json"
    record_github_link(
        config,
        item_id="m173-github-status-comment-durable-sync",
        queue_item_id="m173-github-status-comment-durable-sync",
        repository="local/aresforge",
        registry_path=registry_path,
        issue_number=173,
        issue_url="https://github.com/local/aresforge/issues/173",
        comment_id="777",
        comment_url="https://github.test/local/aresforge/issues/173#issuecomment-777",
        sync_status="status_comment_synced",
    )
    client = _FakeStatusCommentClient()

    payload = _payload(
        sync_github_status_comment_durable(
            config,
            item_id="m173-github-status-comment-durable-sync",
            registry_path=registry_path,
            dry_run=False,
            github_enabled=True,
            autonomy_profile=LIVE_AUTONOMY_PROFILE,
            github_client=client,
        )
    )

    assert payload["blocked"] is False
    assert payload["status_comment_operation"] == "update_by_registry_comment_id"
    assert payload["managed_comment_id"] == "777"
    assert client.find_calls == []
    assert client.create_calls == []
    assert client.update_calls[0]["comment_id"] == "777"


def test_live_sync_requires_live_autonomy_profile(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    client = _FakeStatusCommentClient()

    payload = _payload(
        sync_github_status_comment_durable(
            config,
            item_id="m173-github-status-comment-durable-sync",
            dry_run=False,
            github_enabled=True,
            github_client=client,
        )
    )

    assert payload["blocked"] is True
    assert payload["status_comment_synced"] is False
    assert payload["github_execution_performed"] is False
    assert any("github_issue_sync_enabled" in reason for reason in payload["blocked_reasons"])
    assert client.find_calls == []


def test_output_path_writes_local_artifact_and_refuses_overwrite(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    output = tmp_path / ".aresforge" / "github_status_comment_durable" / "m173.json"

    first = sync_github_status_comment_durable(
        config,
        item_id="m173-github-status-comment-durable-sync",
        dry_run=True,
        output=output,
    )
    second = sync_github_status_comment_durable(
        config,
        item_id="m173-github-status-comment-durable-sync",
        dry_run=True,
        output=output,
    )

    assert first["ok"] is True
    written = json.loads(output.read_text(encoding="utf-8"))
    assert written["record_type"] == RECORD_TYPE
    assert str(output) in written["artifacts_created"]
    assert second["ok"] is False
    assert second["payload"]["blocked"] is True
    assert any("Output file already exists" in reason for reason in second["payload"]["blocked_reasons"])
