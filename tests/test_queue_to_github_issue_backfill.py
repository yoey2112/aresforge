import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.github_issue_creation_real_run_gate import LIVE_AUTONOMY_PROFILE
from aresforge.operator.github_link_registry import record_github_link
from aresforge.operator.local_project_queue import add_queue_item, init_project_queue
from aresforge.operator.queue_to_github_issue_backfill import (
    RECORD_TYPE,
    backfill_queue_items_to_github_issues,
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
        status="ready",
        priority="high",
        item_type="sync",
        tags=["milestone:m172", "github-issue-sync"],
    )["ok"] is True
    assert add_queue_item(
        config,
        item_id="candidate-one",
        project_id="aresforge",
        repo_id="aresforge-main",
        title="Candidate One",
        description="Needs a GitHub issue.",
        status="ready",
        priority="high",
        item_type="feature",
    )["ok"] is True
    assert add_queue_item(
        config,
        item_id="linked-item",
        project_id="aresforge",
        repo_id="aresforge-main",
        title="Linked Item",
        description="Already linked in queue metadata.",
        status="ready",
        priority="normal",
        item_type="feature",
    )["ok"] is True
    assert add_queue_item(
        config,
        item_id="blocked-item",
        project_id="aresforge",
        repo_id="aresforge-main",
        title="Blocked Item",
        description="Has a queue blocker.",
        status="blocked",
        priority="normal",
        item_type="feature",
        blocked_by=["candidate-one"],
    )["ok"] is True

    raw = json.loads(queue_path.read_text(encoding="utf-8"))
    for item in raw["work_items"]:
        if item["item_id"] == "linked-item":
            item["github_issue"] = {
                "number": 12,
                "url": "https://github.com/local/aresforge/issues/12",
            }
    queue_path.write_text(json.dumps(raw, indent=2) + "\n", encoding="utf-8")
    return queue_path


class _FakeGitHubIssueClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []
        self.next_number = 200

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
        number = self.next_number
        self.next_number += 1
        return {
            "id": number,
            "number": number,
            "title": title,
            "html_url": f"https://github.test/local/aresforge/issues/{number}",
            "state": "open",
        }


def test_dry_run_plans_candidates_and_skips_already_linked_items(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    registry_path = tmp_path / ".aresforge" / "github_link_registry" / "links.json"
    record_github_link(
        config,
        queue_item_id="registry-linked-item",
        repository="local/aresforge",
        registry_path=registry_path,
        issue_number=44,
        issue_url="https://github.com/local/aresforge/issues/44",
    )

    payload = _payload(
        backfill_queue_items_to_github_issues(
            config,
            project_id="aresforge",
            registry_path=registry_path,
            dry_run=True,
        )
    )
    items = {item["item_id"]: item for item in payload["backfill_items"]}  # type: ignore[index]

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
    assert payload["recovery_available"] is True
    assert payload["local_only"] is True
    assert payload["operation_counts"]["create_planned"] >= 2  # type: ignore[index]
    assert items["candidate-one"]["sync_status"] == "dry_run_ready"
    assert items["linked-item"]["sync_status"] == "already_linked"
    assert items["linked-item"]["skip_reason"] == "already_linked_queue_metadata"
    assert items["blocked-item"]["sync_status"] == "blocked"
    assert items["candidate-one"]["issue_payload"]["title"] == "Candidate One"


def test_mocked_live_backfill_creates_one_issue_and_records_registry_link(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    client = _FakeGitHubIssueClient()
    registry_path = tmp_path / ".aresforge" / "github_link_registry" / "links.json"

    payload = _payload(
        backfill_queue_items_to_github_issues(
            config,
            project_id="aresforge",
            registry_path=registry_path,
            dry_run=False,
            github_enabled=True,
            autonomy_profile=LIVE_AUTONOMY_PROFILE,
            max_creations=1,
            github_client=client,
        )
    )

    assert payload["blocked"] is False
    assert payload["status"] == "completed"
    assert payload["sync_status"] == "completed"
    assert payload["dry_run"] is False
    assert payload["github_enabled"] is True
    assert payload["github_execution_performed"] is True
    assert payload["mutation_performed"] is True
    assert payload["registry_mutation_performed"] is True
    assert payload["queue_mutation_performed"] is False
    assert payload["local_only"] is False
    assert payload["operation_counts"]["issue_created"] == 1  # type: ignore[index]
    assert len(client.calls) == 1

    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    issue_records = [record for record in registry["links"] if record.get("issue_number") == 200]
    assert len(issue_records) == 1
    assert issue_records[0]["sync_status"] == "synced"


def test_second_live_backfill_is_idempotent_from_registry_link(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    client = _FakeGitHubIssueClient()
    registry_path = tmp_path / ".aresforge" / "github_link_registry" / "links.json"

    first = _payload(
        backfill_queue_items_to_github_issues(
            config,
            project_id="aresforge",
            registry_path=registry_path,
            dry_run=False,
            github_enabled=True,
            autonomy_profile=LIVE_AUTONOMY_PROFILE,
            max_creations=1,
            github_client=client,
        )
    )
    second = _payload(
        backfill_queue_items_to_github_issues(
            config,
            project_id="aresforge",
            registry_path=registry_path,
            dry_run=False,
            github_enabled=True,
            autonomy_profile=LIVE_AUTONOMY_PROFILE,
            max_creations=1,
            github_client=client,
        )
    )

    assert first["operation_counts"]["issue_created"] == 1  # type: ignore[index]
    assert second["operation_counts"]["issue_created"] == 1  # type: ignore[index]
    assert len(client.calls) == 2
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    assert len([record for record in registry["links"] if record.get("issue_number")]) == 2


def test_output_path_writes_plan_and_refuses_overwrite(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    output = tmp_path / ".aresforge" / "github_issue_backfill" / "m172.json"

    first = backfill_queue_items_to_github_issues(config, project_id="aresforge", output=output)
    second = backfill_queue_items_to_github_issues(config, project_id="aresforge", output=output)

    assert first["ok"] is True
    written = json.loads(output.read_text(encoding="utf-8"))
    assert written["record_type"] == RECORD_TYPE
    assert str(output) in written["artifacts_created"]
    assert second["ok"] is False
    assert second["payload"]["blocked"] is True
    assert second["payload"]["github_execution_performed"] is False
    assert any("Output file already exists" in reason for reason in second["payload"]["blocked_reasons"])
