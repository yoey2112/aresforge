import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.github_issue_creation_for_safe_queue_items import (
    LIVE_AUTONOMY_PROFILE,
    RECORD_TYPE,
    create_github_issue_for_safe_queue_item,
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
        item_id="m162-github-issue-sync-plan-from-queue-items",
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M162 GitHub Issue Sync Plan from Queue Items",
        status="done",
        priority="high",
        item_type="sync",
    )["ok"] is True
    assert add_queue_item(
        config,
        item_id="m163-github-issue-creation-for-safe-queue-items",
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M163 GitHub Issue Creation for Safe Queue Items",
        description="Create GitHub issues only for safe queue items.",
        status="ready",
        priority="high",
        item_type="sync",
        tags=["milestone:m163", "github-issue-sync", "machine-gated"],
        dependencies=["m162-github-issue-sync-plan-from-queue-items"],
        notes="Validation commands are available for M163.",
    )["ok"] is True
    assert add_queue_item(
        config,
        item_id="linked-item",
        project_id="aresforge",
        repo_id="aresforge-main",
        title="Linked item",
        description="Already has a GitHub issue.",
        status="ready",
        priority="normal",
        item_type="feature",
        dependencies=["m162-github-issue-sync-plan-from-queue-items"],
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
        if item["item_id"] == "linked-item":
            item["github_issue"] = {
                "number": 42,
                "url": "https://github.com/local/aresforge/issues/42",
            }
    queue_path.write_text(json.dumps(raw, indent=2) + "\n", encoding="utf-8")
    return queue_path


class _FakeGitHubIssueClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def create_issue(
        self,
        *,
        repo: str,
        title: str,
        body: str,
        labels: list[str],
        milestone: str,
    ) -> dict[str, object]:
        self.calls.append(
            {
                "repo": repo,
                "title": title,
                "body": body,
                "labels": labels,
                "milestone": milestone,
            }
        )
        return {
            "id": 1001,
            "number": 163,
            "title": title,
            "html_url": "https://github.test/local/aresforge/issues/163",
            "state": "open",
        }


def _payload(result: dict[str, object]) -> dict[str, object]:
    return result["payload"]  # type: ignore[index]


def test_dry_run_prepares_issue_creation_without_github_call(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    client = _FakeGitHubIssueClient()

    payload = _payload(
        create_github_issue_for_safe_queue_item(
            config,
            item_id="m163-github-issue-creation-for-safe-queue-items",
            dry_run=True,
            github_client=client,
        )
    )

    assert payload["record_type"] == RECORD_TYPE
    assert payload["status"] == "dry_run_ready"
    assert payload["blocked"] is False
    assert payload["generated"] is True
    assert payload["project_id"] == "aresforge"
    assert payload["item_id"] == "m163-github-issue-creation-for-safe-queue-items"
    assert payload["machine_gates_passed"] is True
    assert payload["autonomy_profile"] == "github_sync_dry_run"
    assert payload["dry_run"] is True
    assert payload["github_enabled"] is False
    assert payload["issue_creation_allowed"] is False
    assert payload["issue_created"] is False
    assert payload["mutation_performed"] is False
    assert payload["queue_mutation_performed"] is False
    assert payload["codex_execution_performed"] is False
    assert payload["model_execution_performed"] is False
    assert payload["github_execution_performed"] is False
    assert payload["patch_application_performed"] is False
    assert payload["local_only"] is True
    assert payload["issue_draft"]["title"] == "M163 GitHub Issue Creation for Safe Queue Items"
    assert client.calls == []


def test_real_issue_creation_requires_live_autonomy_profile(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    client = _FakeGitHubIssueClient()

    payload = _payload(
        create_github_issue_for_safe_queue_item(
            config,
            item_id="m163-github-issue-creation-for-safe-queue-items",
            dry_run=False,
            github_enabled=True,
            github_client=client,
        )
    )

    assert payload["blocked"] is True
    assert payload["issue_created"] is False
    assert payload["github_execution_performed"] is False
    assert any("github_issue_sync_enabled" in reason for reason in payload["blocked_reasons"])
    assert client.calls == []


def test_mocked_issue_creation_runs_only_when_enabled_and_gated(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    client = _FakeGitHubIssueClient()

    payload = _payload(
        create_github_issue_for_safe_queue_item(
            config,
            item_id="m163-github-issue-creation-for-safe-queue-items",
            dry_run=False,
            github_enabled=True,
            autonomy_profile=LIVE_AUTONOMY_PROFILE,
            repo="local/aresforge",
            github_client=client,
        )
    )

    assert payload["blocked"] is False
    assert payload["status"] == "issue_created"
    assert payload["machine_gates_checked"][0]["gate_profile"] == "github_sync"
    assert payload["machine_gates_passed"] is True
    assert payload["issue_creation_allowed"] is True
    assert payload["issue_created"] is True
    assert payload["github_execution_performed"] is True
    assert payload["queue_mutation_performed"] is False
    assert payload["created_issue"]["number"] == 163
    assert Path(str(payload["github_preflight_record_path"])).exists()
    assert client.calls[0]["repo"] == "local/aresforge"
    assert client.calls[0]["milestone"] == "M163"


def test_linked_or_blocked_items_do_not_create_duplicate_issues(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    client = _FakeGitHubIssueClient()

    linked = _payload(
        create_github_issue_for_safe_queue_item(
            config,
            item_id="linked-item",
            dry_run=False,
            github_enabled=True,
            autonomy_profile=LIVE_AUTONOMY_PROFILE,
            github_client=client,
        )
    )
    blocked = _payload(
        create_github_issue_for_safe_queue_item(
            config,
            item_id="blocked-item",
            dry_run=True,
            github_client=client,
        )
    )

    assert linked["blocked"] is True
    assert linked["duplicate_linked_issue_blocked"] is True
    assert any("duplicate issue creation" in reason for reason in linked["blocked_reasons"])
    assert blocked["blocked"] is True
    assert any("not safe" in reason or "blocked_by" in reason for reason in blocked["blocked_reasons"])
    assert client.calls == []


def test_output_path_writes_local_artifact_and_refuses_overwrite(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    output = tmp_path / ".aresforge" / "github_issue_creation" / "m163.json"

    first = create_github_issue_for_safe_queue_item(
        config,
        item_id="m163-github-issue-creation-for-safe-queue-items",
        dry_run=True,
        output=output,
    )
    second = create_github_issue_for_safe_queue_item(
        config,
        item_id="m163-github-issue-creation-for-safe-queue-items",
        dry_run=True,
        output=output,
    )

    assert first["ok"] is True
    written = json.loads(output.read_text(encoding="utf-8"))
    assert str(output) in written["artifacts_created"]
    assert second["ok"] is False
    assert second["payload"]["blocked"] is True
    assert any("Output file already exists" in reason for reason in second["payload"]["blocked_reasons"])
