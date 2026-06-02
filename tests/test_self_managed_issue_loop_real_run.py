import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.github_issue_creation_real_run_gate import LIVE_AUTONOMY_PROFILE
from aresforge.operator.local_project_queue import add_queue_item, init_project_queue
from aresforge.operator.self_managed_issue_loop_real_run import (
    DEFAULT_ITEM_ID,
    RECORD_TYPE,
    run_self_managed_issue_loop,
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


def _seed_queue(config: AppConfig, *, status: str = "ready") -> Path:
    result = init_project_queue(config)
    assert result["ok"] is True
    queue_path = Path(str(result["path"]))
    assert add_queue_item(
        config,
        item_id="m180-hub-github-sync-control-panel",
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M180 Hub GitHub Sync Control Panel",
        status="done",
        priority="high",
        item_type="dashboard",
    )["ok"] is True
    assert add_queue_item(
        config,
        item_id=DEFAULT_ITEM_ID,
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M181 Self-Managed Issue Loop Real Run",
        description="Coordinate one AresForge queue item through gated GitHub issue sync.",
        status=status,
        priority="high",
        item_type="sync",
        tags=["milestone:m181", "github-loop", "self-managed", "machine-gated"],
        dependencies=["m180-hub-github-sync-control-panel"],
        notes="Real run remains explicitly gated.",
    )["ok"] is True
    return queue_path


class _FakeIssueClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def create_issue(self, *, repo: str, title: str, body: str, labels: list[str], milestone: str) -> dict[str, object]:
        self.calls.append({"repo": repo, "title": title, "body": body, "labels": labels, "milestone": milestone})
        return {
            "id": 181001,
            "number": 181,
            "title": title,
            "html_url": "https://github.test/local/aresforge/issues/181",
            "state": "open",
        }


class _FakeStatusCommentClient:
    def __init__(self) -> None:
        self.find_calls: list[dict[str, object]] = []
        self.create_calls: list[dict[str, object]] = []
        self.update_calls: list[dict[str, object]] = []

    def find_status_comment(self, *, repo: str, issue_number: int, marker: str) -> dict[str, object] | None:
        self.find_calls.append({"repo": repo, "issue_number": issue_number, "marker": marker})
        return None

    def create_comment(self, *, repo: str, issue_number: int, body: str) -> dict[str, object]:
        self.create_calls.append({"repo": repo, "issue_number": issue_number, "body": body})
        return {"id": 1815001, "html_url": "https://github.test/local/aresforge/issues/181#issuecomment-1815001"}

    def update_comment(self, *, repo: str, comment_id: int | str, body: str) -> dict[str, object]:
        self.update_calls.append({"repo": repo, "comment_id": comment_id, "body": body})
        return {"id": comment_id, "html_url": f"https://github.test/local/aresforge/issues/181#issuecomment-{comment_id}"}


class _FakeIssueStateClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def list_issues(self, *, repo: str, issue_numbers: list[int]) -> list[dict[str, object]]:
        self.calls.append({"repo": repo, "issue_numbers": issue_numbers})
        return [
            {
                "number": number,
                "title": "M181 Self-Managed Issue Loop Real Run",
                "state": "open",
                "url": f"https://github.test/local/aresforge/issues/{number}",
                "labels": [{"name": "milestone:m181"}, {"name": "github-loop"}],
            }
            for number in issue_numbers
        ]


def test_dry_run_default_runs_full_loop_without_github_mutation(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    issue_client = _FakeIssueClient()
    comment_client = _FakeStatusCommentClient()
    state_client = _FakeIssueStateClient()

    result = run_self_managed_issue_loop(
        config,
        project_id="aresforge",
        dry_run=True,
        github_issue_client=issue_client,
        github_status_comment_client=comment_client,
        github_issue_state_client=state_client,
    )
    payload = result["payload"]

    assert result["ok"] is True
    assert payload["record_type"] == RECORD_TYPE
    assert payload["artifact_type"] == RECORD_TYPE
    assert payload["status"] == "dry_run_completed"
    assert payload["sync_status"] == "dry_run_completed"
    assert payload["project_id"] == "aresforge"
    assert payload["item_id"] == DEFAULT_ITEM_ID
    assert payload["repository"] == "local/aresforge"
    assert payload["blocked"] is False
    assert payload["machine_gates_passed"] is True
    assert payload["dry_run"] is True
    assert payload["github_enabled"] is False
    assert payload["github_execution_performed"] is False
    assert payload["mutation_performed"] is False
    assert payload["registry_mutation_performed"] is False
    assert payload["queue_mutation_performed"] is False
    assert payload["codex_execution_performed"] is False
    assert payload["model_execution_performed"] is False
    assert payload["patch_application_performed"] is False
    assert payload["validation_command_execution_performed"] is False
    assert payload["recovery_available"] is True
    assert payload["local_only"] is True
    assert payload["idempotency_key"].startswith("self-managed-issue-loop:")
    assert [step["step_id"] for step in payload["loop_steps"]] == [
        "link_lookup",
        "issue_creation_gate",
        "status_comment_sync",
        "issue_state_reconciliation",
        "recovery_idempotency",
        "closure_recommendation",
    ]
    assert payload["issue_creation_gate"]["sync_status"] == "dry_run_ready"
    assert payload["status_comment_sync"]["sync_status"] == "dry_run_ready"
    assert payload["issue_state_reconciliation"]["sync_status"] == "dry_run_ready"
    assert payload["closure_recommendation"]["recommendation_only"] is True
    assert issue_client.calls == []
    assert comment_client.find_calls == []
    assert comment_client.create_calls == []
    assert state_client.calls == []


def test_real_run_requires_live_autonomy_profile_before_github_calls(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    issue_client = _FakeIssueClient()
    comment_client = _FakeStatusCommentClient()
    state_client = _FakeIssueStateClient()

    payload = run_self_managed_issue_loop(
        config,
        project_id="aresforge",
        dry_run=False,
        github_enabled=True,
        github_issue_client=issue_client,
        github_status_comment_client=comment_client,
        github_issue_state_client=state_client,
    )["payload"]

    assert payload["blocked"] is True
    assert payload["sync_status"] == "blocked"
    assert payload["github_execution_performed"] is False
    assert payload["mutation_performed"] is False
    assert any("github_issue_sync_enabled" in reason for reason in payload["blocked_reasons"])
    assert issue_client.calls == []
    assert comment_client.create_calls == []
    assert state_client.calls == []


def test_mocked_real_run_creates_issue_syncs_comment_and_reconciles(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    issue_client = _FakeIssueClient()
    comment_client = _FakeStatusCommentClient()
    state_client = _FakeIssueStateClient()
    registry_path = tmp_path / ".aresforge" / "github_link_registry" / "links.json"

    payload = run_self_managed_issue_loop(
        config,
        project_id="aresforge",
        registry_path=registry_path,
        dry_run=False,
        github_enabled=True,
        autonomy_profile=LIVE_AUTONOMY_PROFILE,
        repo="local/aresforge",
        github_issue_client=issue_client,
        github_status_comment_client=comment_client,
        github_issue_state_client=state_client,
    )["payload"]

    assert payload["blocked"] is False
    assert payload["status"] == "real_run_completed"
    assert payload["sync_status"] == "real_run_completed"
    assert payload["issue_number"] == 181
    assert payload["issue_url"] == "https://github.test/local/aresforge/issues/181"
    assert payload["dry_run"] is False
    assert payload["github_enabled"] is True
    assert payload["github_execution_performed"] is True
    assert payload["mutation_performed"] is True
    assert payload["github_issue_mutation_performed"] is True
    assert payload["github_comment_mutation_performed"] is True
    assert payload["registry_mutation_performed"] is True
    assert payload["queue_mutation_performed"] is False
    assert payload["local_only"] is False
    assert payload["issue_creation_gate"]["sync_status"] == "synced"
    assert payload["status_comment_sync"]["sync_status"] == "status_comment_synced"
    assert payload["issue_state_reconciliation"]["sync_status"] == "dry_run_ready"
    assert payload["closure_recommendation"]["recommendation_only"] is True
    assert issue_client.calls[0]["repo"] == "local/aresforge"
    assert comment_client.create_calls[0]["issue_number"] == 181
    assert state_client.calls == []

    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    record = registry["links"][0]
    assert record["queue_item_id"] == DEFAULT_ITEM_ID
    assert record["issue_number"] == 181
    assert record["comment_id"] == "1815001"


def test_output_path_writes_local_artifact_and_refuses_overwrite(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    output = tmp_path / ".aresforge" / "self_managed_issue_loop" / "m181.json"

    first = run_self_managed_issue_loop(config, project_id="aresforge", dry_run=True, output=output)
    second = run_self_managed_issue_loop(config, project_id="aresforge", dry_run=True, output=output)

    assert first["ok"] is True
    written = json.loads(output.read_text(encoding="utf-8"))
    assert written["record_type"] == RECORD_TYPE
    assert str(output) in written["artifacts_created"]
    assert second["ok"] is False
    assert second["payload"]["blocked"] is True
    assert second["payload"]["github_execution_performed"] is False
    assert any("Output file already exists" in reason for reason in second["payload"]["blocked_reasons"])
