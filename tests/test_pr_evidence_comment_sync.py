import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.github_issue_creation_real_run_gate import LIVE_AUTONOMY_PROFILE
from aresforge.operator.github_link_registry import record_github_link
from aresforge.operator.local_project_queue import add_queue_item, init_project_queue
from aresforge.operator.pr_evidence_comment_sync import (
    PR_EVIDENCE_COMMENT_MARKER,
    RECORD_TYPE,
    sync_pr_evidence_comment,
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


def _seed_queue(config: AppConfig) -> Path:
    result = init_project_queue(config)
    assert result["ok"] is True
    queue_path = Path(str(result["path"]))
    assert add_queue_item(
        config,
        item_id="m177-pr-draft-creation-gate",
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M177 PR Draft Creation Gate",
        status="done",
        priority="high",
        item_type="sync",
    )["ok"] is True
    assert add_queue_item(
        config,
        item_id="m178-pr-evidence-comment-sync",
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M178 PR Evidence Comment Sync",
        description="Sync PR evidence comments from validation and queue context.",
        status="done",
        priority="high",
        item_type="sync",
        tags=["milestone:m178", "github-loop", "pr-evidence-comment"],
        dependencies=["m177-pr-draft-creation-gate"],
        notes="Evidence comment sync only; merge and unsafe GitHub operations stay blocked.",
    )["ok"] is True

    raw = json.loads(queue_path.read_text(encoding="utf-8"))
    for item in raw["work_items"]:
        if item["item_id"] == "m178-pr-evidence-comment-sync":
            item["github_issue"] = {
                "number": 178,
                "url": "https://github.com/local/aresforge/issues/178",
                "state": "open",
            }
            item["validation_summary"] = "PR evidence comment sync validation passed."
            item["tests_run"] = [
                "python -m pytest tests/test_pr_evidence_comment_sync.py -> passed",
                "python -m aresforge sync-pr-evidence-comment --item-id m178-pr-evidence-comment-sync --dry-run --format json -> passed",
            ]
            item["evidence_note"] = "Local validation and PR evidence sync dry run are available."
            item["changed_files"] = [
                "src/aresforge/operator/pr_evidence_comment_sync.py",
                "tests/test_pr_evidence_comment_sync.py",
                "src/aresforge/cli.py",
            ]
            item["artifact_paths"] = [".aresforge/codex_loop_validation_evidence/m178-pr-evidence-comment-sync/bundle.json"]
    queue_path.write_text(json.dumps(raw, indent=2) + "\n", encoding="utf-8")
    return queue_path


class _FakePrEvidenceCommentClient:
    def __init__(self, existing: dict[str, object] | None = None) -> None:
        self.existing = existing
        self.find_calls: list[dict[str, object]] = []
        self.create_calls: list[dict[str, object]] = []
        self.update_calls: list[dict[str, object]] = []

    def find_pr_evidence_comment(self, *, repo: str, pr_number: int, marker: str) -> dict[str, object] | None:
        self.find_calls.append({"repo": repo, "pr_number": pr_number, "marker": marker})
        return self.existing

    def create_pr_comment(self, *, repo: str, pr_number: int, body: str) -> dict[str, object]:
        self.create_calls.append({"repo": repo, "pr_number": pr_number, "body": body})
        return {"id": 6001, "html_url": "https://github.test/local/aresforge/pull/178#issuecomment-6001"}

    def update_comment(self, *, repo: str, comment_id: int | str, body: str) -> dict[str, object]:
        self.update_calls.append({"repo": repo, "comment_id": comment_id, "body": body})
        return {"id": comment_id, "html_url": f"https://github.test/local/aresforge/pull/178#issuecomment-{comment_id}"}


def _payload(result: dict[str, object]) -> dict[str, object]:
    return result["payload"]  # type: ignore[index]


def test_dry_run_generates_pr_evidence_comment_without_github_mutation(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    client = _FakePrEvidenceCommentClient()

    payload = _payload(
        sync_pr_evidence_comment(
            config,
            item_id="m178-pr-evidence-comment-sync",
            dry_run=True,
            github_client=client,
        )
    )

    assert payload["record_type"] == RECORD_TYPE
    assert payload["status"] == "dry_run_ready"
    assert payload["sync_status"] == "dry_run_ready"
    assert payload["blocked"] is False
    assert payload["project_id"] == "aresforge"
    assert payload["item_id"] == "m178-pr-evidence-comment-sync"
    assert payload["issue_number"] == 178
    assert payload["pr_number"] is None
    assert payload["machine_gates_passed"] is True
    assert payload["dry_run"] is True
    assert payload["github_enabled"] is False
    assert payload["github_execution_performed"] is False
    assert payload["mutation_performed"] is False
    assert payload["pr_evidence_comment_synced"] is False
    assert payload["registry_mutation_performed"] is False
    assert payload["queue_mutation_performed"] is False
    assert payload["patch_application_performed"] is False
    assert payload["validation_command_execution_performed"] is False
    assert payload["recovery_available"] is True
    assert payload["local_only"] is True
    assert payload["idempotency_key"].startswith("pr-evidence-comment:")
    assert PR_EVIDENCE_COMMENT_MARKER in payload["pr_evidence_comment_body"]
    assert "PR evidence comment sync validation passed." in payload["pr_evidence_comment_body"]
    assert "src/aresforge/operator/pr_evidence_comment_sync.py" in payload["pr_evidence_comment_body"]
    assert "merge_pull_request" in payload["github_operations_blocked"]
    assert "force_push" in payload["github_operations_blocked"]
    assert client.find_calls == []
    assert client.create_calls == []
    assert client.update_calls == []


def test_mocked_live_create_records_comment_id_in_registry(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    client = _FakePrEvidenceCommentClient()
    registry_path = tmp_path / ".aresforge" / "github_link_registry" / "links.json"
    record_github_link(
        config,
        item_id="m178-pr-evidence-comment-sync",
        queue_item_id="m178-pr-evidence-comment-sync",
        repository="local/aresforge",
        registry_path=registry_path,
        issue_number=178,
        issue_url="https://github.com/local/aresforge/issues/178",
        pr_number=178,
        pr_url="https://github.test/local/aresforge/pull/178",
    )

    payload = _payload(
        sync_pr_evidence_comment(
            config,
            item_id="m178-pr-evidence-comment-sync",
            registry_path=registry_path,
            dry_run=False,
            github_enabled=True,
            autonomy_profile=LIVE_AUTONOMY_PROFILE,
            github_client=client,
        )
    )

    assert payload["blocked"] is False
    assert payload["status"] == "pr_evidence_comment_synced"
    assert payload["sync_status"] == "pr_evidence_comment_synced"
    assert payload["pr_number"] == 178
    assert payload["pr_evidence_comment_operation"] == "create"
    assert payload["managed_comment_id"] == "6001"
    assert payload["github_execution_performed"] is True
    assert payload["mutation_performed"] is True
    assert payload["registry_mutation_performed"] is True
    assert payload["queue_mutation_performed"] is False
    assert payload["local_only"] is False
    assert client.find_calls[0]["pr_number"] == 178
    assert client.create_calls[0]["pr_number"] == 178

    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    record = registry["links"][0]
    assert record["queue_item_id"] == "m178-pr-evidence-comment-sync"
    assert record["pr_number"] == 178
    assert record["comment_id"] == "6001"
    assert record["sync_status"] == "status_comment_synced"


def test_registry_comment_id_drives_idempotent_update_without_find_or_create(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    registry_path = tmp_path / ".aresforge" / "github_link_registry" / "links.json"
    record_github_link(
        config,
        item_id="m178-pr-evidence-comment-sync",
        queue_item_id="m178-pr-evidence-comment-sync",
        repository="local/aresforge",
        registry_path=registry_path,
        issue_number=178,
        issue_url="https://github.com/local/aresforge/issues/178",
        pr_number=178,
        pr_url="https://github.test/local/aresforge/pull/178",
        comment_id="777",
        comment_url="https://github.test/local/aresforge/pull/178#issuecomment-777",
        sync_status="status_comment_synced",
    )
    client = _FakePrEvidenceCommentClient()

    payload = _payload(
        sync_pr_evidence_comment(
            config,
            item_id="m178-pr-evidence-comment-sync",
            registry_path=registry_path,
            dry_run=False,
            github_enabled=True,
            autonomy_profile=LIVE_AUTONOMY_PROFILE,
            github_client=client,
        )
    )

    assert payload["blocked"] is False
    assert payload["pr_evidence_comment_operation"] == "update_by_registry_comment_id"
    assert payload["managed_comment_id"] == "777"
    assert client.find_calls == []
    assert client.create_calls == []
    assert client.update_calls[0]["comment_id"] == "777"


def test_live_sync_requires_live_autonomy_profile_and_pr_number(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    client = _FakePrEvidenceCommentClient()

    payload = _payload(
        sync_pr_evidence_comment(
            config,
            item_id="m178-pr-evidence-comment-sync",
            dry_run=False,
            github_enabled=True,
            github_client=client,
        )
    )

    assert payload["blocked"] is True
    assert payload["pr_evidence_comment_synced"] is False
    assert payload["github_execution_performed"] is False
    assert any("github_issue_sync_enabled" in reason for reason in payload["blocked_reasons"])
    assert any("PR link" in reason or "pr-number" in reason for reason in payload["blocked_reasons"])
    assert client.find_calls == []


def test_output_path_writes_local_artifact_and_refuses_overwrite(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    output = tmp_path / ".aresforge" / "pr_evidence_comment_sync" / "m178.json"

    first = sync_pr_evidence_comment(config, item_id="m178-pr-evidence-comment-sync", dry_run=True, output=output)
    second = sync_pr_evidence_comment(config, item_id="m178-pr-evidence-comment-sync", dry_run=True, output=output)

    assert first["ok"] is True
    written = json.loads(output.read_text(encoding="utf-8"))
    assert written["record_type"] == RECORD_TYPE
    assert str(output) in written["artifacts_created"]
    assert second["ok"] is False
    assert second["payload"]["blocked"] is True
    assert any("Output file already exists" in reason for reason in second["payload"]["blocked_reasons"])
