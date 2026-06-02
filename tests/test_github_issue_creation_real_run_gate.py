import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.github_issue_creation_real_run_gate import (
    LIVE_AUTONOMY_PROFILE,
    RECORD_TYPE,
    create_github_issue_real_run_gate,
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


def _seed_queue(config: AppConfig) -> Path:
    result = init_project_queue(config)
    assert result["ok"] is True
    queue_path = Path(str(result["path"]))
    assert add_queue_item(
        config,
        item_id="m170-github-link-registry-for-queue-items",
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M170 GitHub Link Registry for Queue Items",
        status="done",
        priority="high",
        item_type="sync",
    )["ok"] is True
    assert add_queue_item(
        config,
        item_id="m171-github-issue-creation-real-run-gate",
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M171 GitHub Issue Creation Real-Run Gate",
        description="Create GitHub issues from safe queue items only when explicit gates pass.",
        status="ready",
        priority="high",
        item_type="sync",
        tags=["milestone:m171", "github-issue-sync", "real-run-gate", "machine-gated"],
        dependencies=["m170-github-link-registry-for-queue-items"],
        notes="Validation commands are available for M171.",
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
        dependencies=["m170-github-link-registry-for-queue-items"],
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
            "id": 171001,
            "number": 171,
            "title": title,
            "html_url": "https://github.test/local/aresforge/issues/171",
            "state": "open",
        }


def _payload(result: dict[str, object]) -> dict[str, object]:
    return result["payload"]  # type: ignore[index]


def test_dry_run_is_default_and_does_not_call_github(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    client = _FakeGitHubIssueClient()

    payload = _payload(
        create_github_issue_real_run_gate(
            config,
            item_id="m171-github-issue-creation-real-run-gate",
            dry_run=True,
            github_client=client,
        )
    )

    assert payload["record_type"] == RECORD_TYPE
    assert payload["status"] == "dry_run_ready"
    assert payload["sync_status"] == "dry_run_ready"
    assert payload["blocked"] is False
    assert payload["generated"] is True
    assert payload["project_id"] == "aresforge"
    assert payload["item_id"] == "m171-github-issue-creation-real-run-gate"
    assert payload["repository"] == "local/aresforge"
    assert payload["issue_number"] is None
    assert payload["issue_url"] == ""
    assert payload["machine_gates_passed"] is True
    assert payload["autonomy_profile"] == "github_sync_dry_run"
    assert payload["dry_run"] is True
    assert payload["github_enabled"] is False
    assert payload["github_execution_performed"] is False
    assert payload["mutation_performed"] is False
    assert payload["registry_mutation_performed"] is False
    assert payload["queue_mutation_performed"] is False
    assert payload["codex_execution_performed"] is False
    assert payload["model_execution_performed"] is False
    assert payload["patch_application_performed"] is False
    assert payload["recovery_available"] is True
    assert payload["local_only"] is True
    assert payload["idempotency_key"].startswith("github-issue-real-run:")
    assert client.calls == []


def test_real_run_requires_live_autonomy_profile(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    client = _FakeGitHubIssueClient()

    payload = _payload(
        create_github_issue_real_run_gate(
            config,
            item_id="m171-github-issue-creation-real-run-gate",
            dry_run=False,
            github_enabled=True,
            github_client=client,
        )
    )

    assert payload["blocked"] is True
    assert payload["sync_status"] == "blocked"
    assert payload["issue_created"] is False
    assert payload["github_execution_performed"] is False
    assert any("github_issue_sync_enabled" in reason for reason in payload["blocked_reasons"])
    assert client.calls == []


def test_mocked_real_run_creates_issue_and_records_local_registry_link(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    client = _FakeGitHubIssueClient()
    registry_path = tmp_path / ".aresforge" / "github_link_registry" / "links.json"

    payload = _payload(
        create_github_issue_real_run_gate(
            config,
            item_id="m171-github-issue-creation-real-run-gate",
            dry_run=False,
            github_enabled=True,
            autonomy_profile=LIVE_AUTONOMY_PROFILE,
            repo="local/aresforge",
            registry_path=registry_path,
            github_client=client,
        )
    )

    assert payload["blocked"] is False
    assert payload["status"] == "issue_created"
    assert payload["sync_status"] == "synced"
    assert payload["machine_gates_checked"][0]["gate_profile"] == "github_sync"
    assert payload["machine_gates_passed"] is True
    assert payload["issue_creation_allowed"] is True
    assert payload["issue_created"] is True
    assert payload["issue_number"] == 171
    assert payload["issue_url"] == "https://github.test/local/aresforge/issues/171"
    assert payload["github_execution_performed"] is True
    assert payload["mutation_performed"] is True
    assert payload["registry_mutation_performed"] is True
    assert payload["queue_mutation_performed"] is False
    assert payload["local_only"] is False
    assert payload["local_registry_record"]["issue_number"] == 171
    assert Path(str(payload["github_preflight_record_path"])).exists()
    assert client.calls[0]["repo"] == "local/aresforge"
    assert registry_path.exists()
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    assert registry["links"][0]["queue_item_id"] == "m171-github-issue-creation-real-run-gate"
    assert registry["links"][0]["sync_status"] == "synced"


def test_duplicate_queue_or_registry_link_blocks_real_run(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    client = _FakeGitHubIssueClient()
    registry_path = tmp_path / ".aresforge" / "github_link_registry" / "links.json"
    record_github_link(
        config,
        queue_item_id="m171-github-issue-creation-real-run-gate",
        repository="local/aresforge",
        registry_path=registry_path,
        issue_number=999,
        issue_url="https://github.test/local/aresforge/issues/999",
    )

    registry_blocked = _payload(
        create_github_issue_real_run_gate(
            config,
            item_id="m171-github-issue-creation-real-run-gate",
            dry_run=False,
            github_enabled=True,
            autonomy_profile=LIVE_AUTONOMY_PROFILE,
            registry_path=registry_path,
            github_client=client,
        )
    )
    queue_blocked = _payload(
        create_github_issue_real_run_gate(
            config,
            item_id="linked-item",
            dry_run=False,
            github_enabled=True,
            autonomy_profile=LIVE_AUTONOMY_PROFILE,
            github_client=client,
        )
    )

    assert registry_blocked["blocked"] is True
    assert registry_blocked["registry_duplicate_link_blocked"] is True
    assert any("registry already has an issue link" in reason for reason in registry_blocked["blocked_reasons"])
    assert queue_blocked["blocked"] is True
    assert queue_blocked["duplicate_linked_issue_blocked"] is True
    assert any("duplicate real issue creation" in reason for reason in queue_blocked["blocked_reasons"])
    assert client.calls == []


def test_output_path_writes_local_artifact_and_refuses_overwrite(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    output = tmp_path / ".aresforge" / "github_issue_creation_real_run_gate" / "m171.json"

    first = create_github_issue_real_run_gate(
        config,
        item_id="m171-github-issue-creation-real-run-gate",
        dry_run=True,
        output=output,
    )
    second = create_github_issue_real_run_gate(
        config,
        item_id="m171-github-issue-creation-real-run-gate",
        dry_run=True,
        output=output,
    )

    assert first["ok"] is True
    written = json.loads(output.read_text(encoding="utf-8"))
    assert str(output) in written["artifacts_created"]
    assert second["ok"] is False
    assert second["payload"]["blocked"] is True
    assert second["payload"]["github_execution_performed"] is False
    assert any("Output file already exists" in reason for reason in second["payload"]["blocked_reasons"])
