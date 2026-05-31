import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.github_sync_agent import run_github_sync_agent
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
        github_owner="yoey2112",
        github_repo="aresforge",
    )


def _seed(config: AppConfig, *, dependency_done: bool = True) -> None:
    assert init_project_queue(config)["ok"] is True
    assert add_queue_item(
        config,
        item_id="m136-codex-result-ingestion-and-validation-runner",
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M136 dependency",
        status="done" if dependency_done else "ready",
        priority="high",
        item_type="feature",
    )["ok"] is True
    assert add_queue_item(
        config,
        item_id="m137-github-pr-issue-sync-agent",
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M137 GitHub PR/Issue Sync Agent",
        description="Plan and perform narrow GitHub issue/PR metadata sync behind explicit gates.",
        status="ready",
        priority="high",
        item_type="sync",
        tags=["milestone:m137", "github-sync", "machine-gated"],
        dependencies=["m136-codex-result-ingestion-and-validation-runner"],
        notes="Validation commands are available for GitHub sync agent.",
    )["ok"] is True


def _comment_artifact(config: AppConfig) -> Path:
    path = config.repo_root / "artifacts" / "manual" / "github-sync-comment.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "artifact_type": "github_sync_comment",
                "item_id": "m137-github-pr-issue-sync-agent",
                "comment_body": "M137 mocked GitHub sync comment.",
                "local_only": True,
                "execution_allowed": False,
                "execution_performed": False,
                "external_execution_performed": False,
                "github_execution_performed": False,
                "patch_application_performed": False,
                "queue_mutation_performed": False,
                "validation_commands": ["python -m pytest tests/test_github_sync_agent.py"],
                "tests_reported": ["python -m pytest tests/test_github_sync_agent.py -> passed"],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


class _FakeGitHubClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def comment_issue(self, *, repo: str, issue_number: int, body: str) -> dict[str, object]:
        self.calls.append({"operation": "comment_issue", "repo": repo, "issue_number": issue_number, "body": body})
        return {"id": 101, "html_url": "https://github.test/comment/101"}

    def comment_pr(self, *, repo: str, pr_number: int, body: str) -> dict[str, object]:
        self.calls.append({"operation": "comment_pr", "repo": repo, "pr_number": pr_number, "body": body})
        return {"id": 202, "html_url": "https://github.test/comment/202"}

    def get_issue(self, *, repo: str, issue_number: int) -> dict[str, object]:
        self.calls.append({"operation": "get_issue", "repo": repo, "issue_number": issue_number})
        return {"number": issue_number, "state": "open", "title": "Issue title", "html_url": "https://github.test/issues/1"}

    def get_pr(self, *, repo: str, pr_number: int) -> dict[str, object]:
        self.calls.append({"operation": "get_pr", "repo": repo, "pr_number": pr_number})
        return {"number": pr_number, "state": "open", "title": "PR title", "html_url": "https://github.test/pull/2"}


def _payload(result: dict[str, object]) -> dict[str, object]:
    return result["payload"]  # type: ignore[index]


def test_dry_run_issue_comment_plans_without_github_call(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed(config)
    client = _FakeGitHubClient()

    payload = _payload(
        run_github_sync_agent(
            config,
            item_id="m137-github-pr-issue-sync-agent",
            dry_run=True,
            sync_mode="issue-comment",
            repo="yoey2112/aresforge",
            issue_number=1,
            github_client=client,
        )
    )

    assert payload["execution_record_type"] == "github_sync_agent_v1"
    assert payload["dry_run"] is True
    assert payload["github_enabled"] is False
    assert payload["sync_mode"] == "issue-comment"
    assert payload["machine_gates_checked"] is True
    assert payload["machine_gates_passed"] is True
    assert payload["executed"] is False
    assert payload["blocked"] is False
    assert payload["github_operation_performed"] is False
    assert "merge-pr" in payload["forbidden_operations_blocked"]
    assert client.calls == []


def test_issue_comment_blocks_by_default_without_github_enabled(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed(config)
    client = _FakeGitHubClient()

    payload = _payload(
        run_github_sync_agent(
            config,
            item_id="m137-github-pr-issue-sync-agent",
            sync_mode="issue-comment",
            repo="yoey2112/aresforge",
            issue_number=1,
            artifact_path=_comment_artifact(config),
            github_client=client,
        )
    )

    assert payload["blocked"] is True
    assert payload["executed"] is False
    assert payload["github_operation_performed"] is False
    assert payload["machine_gates_passed"] is False
    assert any("--github-enabled" in reason for reason in payload["blocked_reasons"])
    assert client.calls == []


def test_mocked_issue_comment_runs_only_when_enabled_and_gated(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed(config)
    client = _FakeGitHubClient()

    payload = _payload(
        run_github_sync_agent(
            config,
            item_id="m137-github-pr-issue-sync-agent",
            sync_mode="issue-comment",
            github_enabled=True,
            repo="yoey2112/aresforge",
            issue_number=1,
            artifact_path=_comment_artifact(config),
            github_client=client,
        )
    )

    assert payload["blocked"] is False
    assert payload["executed"] is True
    assert payload["github_operation_performed"] is True
    assert payload["machine_gates_passed"] is True
    assert payload["repository_file_write_performed"] is False
    assert payload["pr_merge_performed"] is False
    assert payload["issue_closed"] is False
    assert client.calls == [
        {
            "operation": "comment_issue",
            "repo": "yoey2112/aresforge",
            "issue_number": 1,
            "body": "M137 mocked GitHub sync comment.",
        }
    ]


def test_pr_summary_writes_local_artifact_with_mocked_metadata(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed(config)
    client = _FakeGitHubClient()

    payload = _payload(
        run_github_sync_agent(
            config,
            item_id="m137-github-pr-issue-sync-agent",
            sync_mode="pr-summary",
            github_enabled=True,
            repo="yoey2112/aresforge",
            pr_number=2,
            github_client=client,
        )
    )
    summary_path = Path(str(payload["artifact_path"]))
    summary = json.loads(summary_path.read_text(encoding="utf-8"))

    assert payload["blocked"] is False
    assert payload["executed"] is True
    assert payload["github_operation_performed"] is True
    assert summary["artifact_type"] == "pr_metadata_summary"
    assert summary["metadata"]["title"] == "PR title"
    assert client.calls == [{"operation": "get_pr", "repo": "yoey2112/aresforge", "pr_number": 2}]


def test_issue_metadata_summary_can_be_local_artifact_only(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed(config)
    client = _FakeGitHubClient()

    payload = _payload(
        run_github_sync_agent(
            config,
            item_id="m137-github-pr-issue-sync-agent",
            sync_mode="issue-update",
            repo="yoey2112/aresforge",
            issue_number=1,
            github_client=client,
        )
    )
    summary_path = Path(str(payload["artifact_path"]))

    assert payload["blocked"] is False
    assert payload["executed"] is True
    assert payload["github_operation_performed"] is False
    assert summary_path.exists()
    assert client.calls == []


def test_forbidden_operation_is_blocked_before_client_call(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed(config)
    client = _FakeGitHubClient()

    payload = _payload(
        run_github_sync_agent(
            config,
            item_id="m137-github-pr-issue-sync-agent",
            sync_mode="merge-pr",
            github_enabled=True,
            repo="yoey2112/aresforge",
            pr_number=2,
            github_client=client,
        )
    )

    assert payload["blocked"] is True
    assert payload["executed"] is False
    assert payload["github_operation_performed"] is False
    assert any("Forbidden GitHub operation" in reason for reason in payload["blocked_reasons"])
    assert client.calls == []
