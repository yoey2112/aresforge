import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.github_issue_creation_real_run_gate import LIVE_AUTONOMY_PROFILE
from aresforge.operator.local_project_queue import add_queue_item, init_project_queue
from aresforge.operator.self_managed_pr_draft_loop_dry_run import (
    DEFAULT_ITEM_ID,
    RECORD_TYPE,
    run_self_managed_pr_draft_loop,
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
        item_id="m181-self-managed-issue-loop-real-run",
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M181 Self-Managed Issue Loop Real Run",
        status="done",
        priority="high",
        item_type="sync",
    )["ok"] is True
    assert add_queue_item(
        config,
        item_id=DEFAULT_ITEM_ID,
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M182 Self-Managed PR Draft Loop Dry Run",
        description="Coordinate one AresForge item through PR branch planning, draft PR gates, PR evidence comment planning, and recovery/idempotency planning.",
        status=status,
        priority="high",
        item_type="sync",
        tags=["milestone:m182", "github-loop", "pr-draft", "self-managed"],
        dependencies=["m181-self-managed-issue-loop-real-run"],
        notes="Dry-run by default; live draft PR/comment sync remains explicitly gated.",
    )["ok"] is True

    raw = json.loads(queue_path.read_text(encoding="utf-8"))
    for item in raw["work_items"]:
        if item["item_id"] == DEFAULT_ITEM_ID:
            item["github_issue"] = {
                "number": 182,
                "url": "https://github.com/local/aresforge/issues/182",
                "state": "open",
            }
            item["approved_branch_plan"] = True
            item["completed_at"] = "2026-06-02T18:20:00Z"
            item["completed_by"] = "local_operator"
            item["completion_commit"] = "abc182"
            item["validation_summary"] = "M182 PR draft loop dry-run validation passed."
            item["tests_run"] = [
                "python -m pytest tests/test_self_managed_pr_draft_loop_dry_run.py -> passed",
                "python -m aresforge run-self-managed-pr-draft-loop --project-id aresforge --dry-run --format json -> passed",
            ]
            item["evidence_note"] = "Local validation and PR draft loop dry run are available for operator review."
            item["changed_files"] = [
                "src/aresforge/operator/self_managed_pr_draft_loop_dry_run.py",
                "tests/test_self_managed_pr_draft_loop_dry_run.py",
                "src/aresforge/cli.py",
            ]
            item["artifact_paths"] = [".aresforge/self_managed_pr_draft_loop/m182.json"]
            item["completion_evidence"] = {
                "record_type": "self_managed_pr_draft_loop_dry_run_v1",
                "status": "dry_run_completed",
                "approved_branch_plan": True,
                "machine_gates_passed": True,
            }
    queue_path.write_text(json.dumps(raw, indent=2) + "\n", encoding="utf-8")
    return queue_path


class _FakeGitHubPrClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def create_draft_pr(
        self,
        *,
        repo: str,
        title: str,
        body: str,
        base_branch: str,
        head_branch: str,
    ) -> dict[str, object]:
        self.calls.append(
            {
                "repo": repo,
                "title": title,
                "body": body,
                "base_branch": base_branch,
                "head_branch": head_branch,
            }
        )
        return {
            "id": 182001,
            "number": 182,
            "title": title,
            "html_url": "https://github.test/local/aresforge/pull/182",
            "state": "open",
            "draft": True,
        }


class _FakePrEvidenceCommentClient:
    def __init__(self) -> None:
        self.find_calls: list[dict[str, object]] = []
        self.create_calls: list[dict[str, object]] = []
        self.update_calls: list[dict[str, object]] = []

    def find_pr_evidence_comment(self, *, repo: str, pr_number: int, marker: str) -> dict[str, object] | None:
        self.find_calls.append({"repo": repo, "pr_number": pr_number, "marker": marker})
        return None

    def create_pr_comment(self, *, repo: str, pr_number: int, body: str) -> dict[str, object]:
        self.create_calls.append({"repo": repo, "pr_number": pr_number, "body": body})
        return {"id": 1826001, "html_url": "https://github.test/local/aresforge/pull/182#issuecomment-1826001"}

    def update_comment(self, *, repo: str, comment_id: int | str, body: str) -> dict[str, object]:
        self.update_calls.append({"repo": repo, "comment_id": comment_id, "body": body})
        return {"id": comment_id, "html_url": f"https://github.test/local/aresforge/pull/182#issuecomment-{comment_id}"}


def test_dry_run_default_composes_pr_loop_without_github_mutation(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    pr_client = _FakeGitHubPrClient()
    comment_client = _FakePrEvidenceCommentClient()

    result = run_self_managed_pr_draft_loop(
        config,
        project_id="aresforge",
        dry_run=True,
        github_pr_client=pr_client,
        github_pr_comment_client=comment_client,
    )
    payload = result["payload"]

    assert result["ok"] is True
    assert payload["record_type"] == RECORD_TYPE
    assert payload["artifact_type"] == RECORD_TYPE
    assert payload["status"] == "dry_run_completed"
    assert payload["sync_status"] == "dry_run_completed"
    assert payload["project_id"] == "aresforge"
    assert payload["item_id"] == DEFAULT_ITEM_ID
    assert payload["issue_number"] == 182
    assert payload["pr_number"] is None
    assert payload["blocked"] is False
    assert payload["machine_gates_passed"] is True
    assert payload["dry_run"] is True
    assert payload["github_enabled"] is False
    assert payload["github_execution_performed"] is False
    assert payload["mutation_performed"] is False
    assert payload["queue_mutation_performed"] is False
    assert payload["codex_execution_performed"] is False
    assert payload["model_execution_performed"] is False
    assert payload["patch_application_performed"] is False
    assert payload["validation_command_execution_performed"] is False
    assert payload["recovery_available"] is True
    assert payload["local_only"] is True
    assert payload["idempotency_key"].startswith("self-managed-pr-draft-loop:")
    assert [step["step_id"] for step in payload["loop_steps"]] == [
        "link_lookup",
        "branch_planning",
        "draft_pr_gate",
        "pr_evidence_comment_planning",
        "recovery_idempotency_planning",
    ]
    assert payload["branch_planning"]["sync_status"] == "dry_run_ready"
    assert payload["draft_pr_gate"]["sync_status"] == "dry_run_ready"
    assert payload["pr_evidence_comment_planning"]["sync_status"] == "dry_run_ready"
    assert "merge_pull_request" in payload["github_operations_blocked"]
    assert "force_push" in payload["github_operations_blocked"]
    assert pr_client.calls == []
    assert comment_client.find_calls == []
    assert comment_client.create_calls == []


def test_real_run_requires_live_autonomy_profile_before_github_calls(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    pr_client = _FakeGitHubPrClient()
    comment_client = _FakePrEvidenceCommentClient()

    payload = run_self_managed_pr_draft_loop(
        config,
        project_id="aresforge",
        dry_run=False,
        github_enabled=True,
        approved_branch_plan=True,
        safe_branch_creation_enabled=True,
        github_pr_client=pr_client,
        github_pr_comment_client=comment_client,
    )["payload"]

    assert payload["blocked"] is True
    assert payload["sync_status"] == "blocked"
    assert payload["github_execution_performed"] is False
    assert payload["mutation_performed"] is False
    assert any("github_issue_sync_enabled" in reason for reason in payload["blocked_reasons"])
    assert pr_client.calls == []
    assert comment_client.create_calls == []


def test_mocked_real_run_creates_draft_pr_and_plans_evidence_comment(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    pr_client = _FakeGitHubPrClient()
    comment_client = _FakePrEvidenceCommentClient()
    registry_path = tmp_path / ".aresforge" / "github_link_registry" / "links.json"

    payload = run_self_managed_pr_draft_loop(
        config,
        project_id="aresforge",
        registry_path=registry_path,
        dry_run=False,
        github_enabled=True,
        autonomy_profile=LIVE_AUTONOMY_PROFILE,
        repo="local/aresforge",
        approved_branch_plan=True,
        safe_branch_creation_enabled=True,
        github_pr_client=pr_client,
        github_pr_comment_client=comment_client,
    )["payload"]

    assert payload["blocked"] is False
    assert payload["status"] == "real_run_completed"
    assert payload["sync_status"] == "real_run_completed"
    assert payload["issue_number"] == 182
    assert payload["pr_number"] == 182
    assert payload["pr_url"] == "https://github.test/local/aresforge/pull/182"
    assert payload["dry_run"] is False
    assert payload["github_enabled"] is True
    assert payload["github_execution_performed"] is True
    assert payload["mutation_performed"] is True
    assert payload["github_pr_mutation_performed"] is True
    assert payload["pr_evidence_comment_mutation_performed"] is True
    assert payload["registry_mutation_performed"] is True
    assert payload["queue_mutation_performed"] is False
    assert payload["local_only"] is False
    assert payload["draft_pr_gate"]["sync_status"] == "synced"
    assert payload["pr_evidence_comment_planning"]["sync_status"] == "pr_evidence_comment_synced"
    assert pr_client.calls[0]["repo"] == "local/aresforge"
    assert comment_client.create_calls[0]["pr_number"] == 182

    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    record = registry["links"][0]
    assert record["queue_item_id"] == DEFAULT_ITEM_ID
    assert record["pr_number"] == 182
    assert record["comment_id"] == "1826001"


def test_output_path_writes_local_artifact_and_refuses_overwrite(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    output = tmp_path / ".aresforge" / "self_managed_pr_draft_loop" / "m182.json"

    first = run_self_managed_pr_draft_loop(config, project_id="aresforge", dry_run=True, output=output)
    second = run_self_managed_pr_draft_loop(config, project_id="aresforge", dry_run=True, output=output)

    assert first["ok"] is True
    written = json.loads(output.read_text(encoding="utf-8"))
    assert written["record_type"] == RECORD_TYPE
    assert str(output) in written["artifacts_created"]
    assert second["ok"] is False
    assert second["payload"]["blocked"] is True
    assert second["payload"]["github_execution_performed"] is False
    assert any("Output file already exists" in reason for reason in second["payload"]["blocked_reasons"])
