import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.github_issue_status_comment_sync import (
    LIVE_AUTONOMY_PROFILE,
    RECORD_TYPE,
    STATUS_COMMENT_MARKER,
    sync_github_issue_status_comment,
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
        item_id="m163-github-issue-creation-for-safe-queue-items",
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M163 GitHub Issue Creation for Safe Queue Items",
        status="done",
        priority="high",
        item_type="sync",
    )["ok"] is True
    assert add_queue_item(
        config,
        item_id="m164-github-issue-status-comment-sync",
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M164 GitHub Issue Status Comment Sync",
        description="Post or update GitHub issue status comments.",
        status="ready",
        priority="high",
        item_type="sync",
        tags=["milestone:m164", "github-issue-sync", "machine-gated"],
        dependencies=["m163-github-issue-creation-for-safe-queue-items"],
        notes="Status comment sync should include gates and validation evidence.",
    )["ok"] is True
    assert add_queue_item(
        config,
        item_id="blocked-item",
        project_id="aresforge",
        repo_id="aresforge-main",
        title="Blocked item",
        status="blocked",
        priority="normal",
        item_type="task",
        blocked_by=["missing-upstream"],
    )["ok"] is True

    raw = json.loads(queue_path.read_text(encoding="utf-8"))
    for item in raw["work_items"]:
        if item["item_id"] == "m164-github-issue-status-comment-sync":
            item["github_issue"] = {
                "number": 164,
                "url": "https://github.com/local/aresforge/issues/164",
            }
            item["validation_summary"] = "Targeted validation passed."
            item["tests_run"] = ["python -m pytest tests/test_github_issue_status_comment_sync.py -> passed"]
            item["evidence_note"] = "Local evidence exists for status comment sync."
            item["artifact_paths"] = [".aresforge/github_issue_status_comments/m164.json"]
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
        return {"id": 1001, "html_url": "https://github.test/local/aresforge/issues/164#issuecomment-1001"}

    def update_comment(self, *, repo: str, comment_id: int | str, body: str) -> dict[str, object]:
        self.update_calls.append({"repo": repo, "comment_id": comment_id, "body": body})
        return {"id": comment_id, "html_url": "https://github.test/local/aresforge/issues/164#issuecomment-42"}


def _payload(result: dict[str, object]) -> dict[str, object]:
    return result["payload"]  # type: ignore[index]


def test_dry_run_generates_status_comment_body_without_github_call(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    client = _FakeStatusCommentClient()

    payload = _payload(
        sync_github_issue_status_comment(
            config,
            item_id="m164-github-issue-status-comment-sync",
            dry_run=True,
            github_client=client,
        )
    )

    assert payload["record_type"] == RECORD_TYPE
    assert payload["status"] == "dry_run_ready"
    assert payload["blocked"] is False
    assert payload["generated"] is True
    assert payload["project_id"] == "aresforge"
    assert payload["item_id"] == "m164-github-issue-status-comment-sync"
    assert payload["issue_number"] == 164
    assert payload["machine_gates_passed"] is True
    assert payload["autonomy_profile"] == "github_sync_dry_run"
    assert payload["dry_run"] is True
    assert payload["status_comment_sync_allowed"] is False
    assert payload["status_comment_synced"] is False
    assert payload["mutation_performed"] is False
    assert payload["queue_mutation_performed"] is False
    assert payload["codex_execution_performed"] is False
    assert payload["model_execution_performed"] is False
    assert payload["github_execution_performed"] is False
    assert payload["patch_application_performed"] is False
    assert payload["local_only"] is True
    assert STATUS_COMMENT_MARKER in payload["status_comment_body"]
    assert "Targeted validation passed." in payload["status_comment_body"]
    assert ".aresforge/github_issue_status_comments/m164.json" in payload["status_comment_body"]
    assert client.find_calls == []
    assert client.create_calls == []
    assert client.update_calls == []


def test_live_sync_requires_live_autonomy_profile(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    client = _FakeStatusCommentClient()

    payload = _payload(
        sync_github_issue_status_comment(
            config,
            item_id="m164-github-issue-status-comment-sync",
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


def test_mocked_live_sync_creates_status_comment_when_enabled_and_gated(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    client = _FakeStatusCommentClient()

    payload = _payload(
        sync_github_issue_status_comment(
            config,
            item_id="m164-github-issue-status-comment-sync",
            dry_run=False,
            github_enabled=True,
            autonomy_profile=LIVE_AUTONOMY_PROFILE,
            repo="local/aresforge",
            github_client=client,
        )
    )

    assert payload["blocked"] is False
    assert payload["status"] == "status_comment_synced"
    assert payload["machine_gates_checked"][0]["gate_profile"] == "github_sync"
    assert payload["machine_gates_passed"] is True
    assert payload["status_comment_sync_allowed"] is True
    assert payload["status_comment_synced"] is True
    assert payload["status_comment_operation"] == "create"
    assert payload["github_execution_performed"] is True
    assert payload["queue_mutation_performed"] is False
    assert Path(str(payload["github_preflight_record_path"])).exists()
    assert client.find_calls[0]["issue_number"] == 164
    assert client.create_calls[0]["repo"] == "local/aresforge"
    assert STATUS_COMMENT_MARKER in str(client.create_calls[0]["body"])


def test_mocked_live_sync_updates_existing_status_comment(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    client = _FakeStatusCommentClient(
        existing={
            "id": 42,
            "html_url": "https://github.test/local/aresforge/issues/164#issuecomment-42",
            "body": STATUS_COMMENT_MARKER,
        }
    )

    payload = _payload(
        sync_github_issue_status_comment(
            config,
            item_id="m164-github-issue-status-comment-sync",
            dry_run=False,
            github_enabled=True,
            autonomy_profile=LIVE_AUTONOMY_PROFILE,
            github_client=client,
        )
    )

    assert payload["blocked"] is False
    assert payload["status_comment_operation"] == "update"
    assert payload["existing_status_comment"]["id"] == 42
    assert payload["synced_status_comment"]["id"] == 42
    assert client.create_calls == []
    assert client.update_calls[0]["comment_id"] == 42


def test_blocked_items_do_not_sync_status_comment(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    client = _FakeStatusCommentClient()

    payload = _payload(
        sync_github_issue_status_comment(
            config,
            item_id="blocked-item",
            dry_run=False,
            github_enabled=True,
            autonomy_profile=LIVE_AUTONOMY_PROFILE,
            issue_number=999,
            github_client=client,
        )
    )

    assert payload["blocked"] is True
    assert payload["status_comment_synced"] is False
    assert any("not safe" in reason or "blocked_by" in reason for reason in payload["blocked_reasons"])
    assert client.find_calls == []
    assert client.create_calls == []
    assert client.update_calls == []


def test_output_path_writes_local_artifact_and_refuses_overwrite(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    output = tmp_path / ".aresforge" / "github_issue_status_comments" / "m164.json"

    first = sync_github_issue_status_comment(
        config,
        item_id="m164-github-issue-status-comment-sync",
        dry_run=True,
        output=output,
    )
    second = sync_github_issue_status_comment(
        config,
        item_id="m164-github-issue-status-comment-sync",
        dry_run=True,
        output=output,
    )

    assert first["ok"] is True
    written = json.loads(output.read_text(encoding="utf-8"))
    assert str(output) in written["artifacts_created"]
    assert second["ok"] is False
    assert second["payload"]["blocked"] is True
    assert any("Output file already exists" in reason for reason in second["payload"]["blocked_reasons"])
