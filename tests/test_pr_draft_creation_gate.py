import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.github_issue_creation_real_run_gate import LIVE_AUTONOMY_PROFILE
from aresforge.operator.github_link_registry import record_github_link
from aresforge.operator.local_project_queue import add_queue_item, init_project_queue
from aresforge.operator.pr_draft_creation_gate import RECORD_TYPE, create_pr_draft_gate


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
        item_id="m176-pr-draft-branch-planning-contract",
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M176 PR Draft Branch Planning Contract",
        status="done",
        priority="high",
        item_type="sync",
    )["ok"] is True
    assert add_queue_item(
        config,
        item_id="m177-pr-draft-creation-gate",
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M177 PR Draft Creation Gate",
        description="Gate draft PR creation without allowing merges or protected branch updates.",
        status="done",
        priority="high",
        item_type="sync",
        tags=["milestone:m177", "github-loop", "pr-draft", "machine-gated"],
        dependencies=["m176-pr-draft-branch-planning-contract"],
        notes="Draft PR creation gate only; merge and unsafe GitHub operations stay blocked.",
    )["ok"] is True

    raw = json.loads(queue_path.read_text(encoding="utf-8"))
    for item in raw["work_items"]:
        if item["item_id"] == "m177-pr-draft-creation-gate":
            item["github_issue"] = {
                "number": 177,
                "url": "https://github.com/local/aresforge/issues/177",
                "state": "open",
            }
            item["approved_branch_plan"] = True
            item["completed_at"] = "2026-06-02T14:00:00Z"
            item["completed_by"] = "local_operator"
            item["completion_commit"] = "abc177"
            item["validation_summary"] = "M177 targeted validation passed."
            item["tests_run"] = [
                "python -m pytest tests/test_pr_draft_creation_gate.py -> passed",
                "python -m aresforge create-pr-draft-gate --item-id m177-pr-draft-creation-gate --dry-run --format json -> passed",
            ]
            item["evidence_note"] = "Local validation and M176 branch plan evidence support draft PR gate review."
            item["changed_files"] = [
                "src/aresforge/operator/pr_draft_creation_gate.py",
                "tests/test_pr_draft_creation_gate.py",
                "src/aresforge/cli.py",
            ]
            item["artifact_paths"] = [".aresforge/pr_draft_branch_plans/m177.json"]
            item["completion_evidence"] = {
                "record_type": "pr_draft_creation_gate_v1",
                "status": "dry_run_ready",
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
            "id": 177001,
            "number": 177,
            "title": title,
            "html_url": "https://github.test/local/aresforge/pull/177",
            "state": "open",
            "draft": True,
        }


def _payload(result: dict[str, object]) -> dict[str, object]:
    return result["payload"]  # type: ignore[index]


def test_dry_run_gates_pr_draft_without_github_mutation(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    client = _FakeGitHubPrClient()

    payload = _payload(
        create_pr_draft_gate(
            config,
            item_id="m177-pr-draft-creation-gate",
            base_branch="main",
            dry_run=True,
            github_client=client,
        )
    )

    assert payload["record_type"] == RECORD_TYPE
    assert payload["status"] == "dry_run_ready"
    assert payload["sync_status"] == "dry_run_ready"
    assert payload["blocked"] is False
    assert payload["project_id"] == "aresforge"
    assert payload["item_id"] == "m177-pr-draft-creation-gate"
    assert payload["repository"] == "local/aresforge"
    assert payload["issue_number"] == 177
    assert payload["issue_url"] == "https://github.com/local/aresforge/issues/177"
    assert payload["pr_number"] is None
    assert payload["pr_url"] == ""
    assert payload["machine_gates_passed"] is True
    assert payload["dry_run"] is True
    assert payload["github_enabled"] is False
    assert payload["github_execution_performed"] is False
    assert payload["mutation_performed"] is False
    assert payload["github_pr_mutation_performed"] is False
    assert payload["github_branch_mutation_performed"] is False
    assert payload["queue_mutation_performed"] is False
    assert payload["patch_application_performed"] is False
    assert payload["validation_command_execution_performed"] is False
    assert payload["draft_pr_creation_allowed"] is False
    assert payload["pull_request_created"] is False
    assert payload["pull_request_merged"] is False
    assert payload["auto_merge_enabled"] is False
    assert payload["force_push_performed"] is False
    assert payload["protected_branch_update_performed"] is False
    assert payload["release_created"] is False
    assert payload["workflow_mutation_performed"] is False
    assert payload["recovery_available"] is True
    assert payload["local_only"] is True
    assert payload["idempotency_key"].startswith("pr-draft-create:")
    assert payload["approved_branch_plan"] is True
    assert payload["branch_plan_exists"] is True
    assert "merge_pull_request" in payload["github_operations_blocked"]
    assert "force_push" in payload["github_operations_blocked"]
    assert client.calls == []


def test_live_path_requires_explicit_live_autonomy_profile(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    client = _FakeGitHubPrClient()

    payload = _payload(
        create_pr_draft_gate(
            config,
            item_id="m177-pr-draft-creation-gate",
            dry_run=False,
            github_enabled=True,
            approved_branch_plan=True,
            safe_branch_creation_enabled=True,
            github_client=client,
        )
    )

    assert payload["blocked"] is True
    assert payload["sync_status"] == "blocked"
    assert payload["pull_request_created"] is False
    assert payload["github_execution_performed"] is False
    assert any("github_issue_sync_enabled" in reason for reason in payload["blocked_reasons"])
    assert client.calls == []


def test_mocked_live_path_creates_draft_pr_and_records_registry_link(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    client = _FakeGitHubPrClient()
    registry_path = tmp_path / ".aresforge" / "github_link_registry" / "links.json"

    payload = _payload(
        create_pr_draft_gate(
            config,
            item_id="m177-pr-draft-creation-gate",
            dry_run=False,
            github_enabled=True,
            autonomy_profile=LIVE_AUTONOMY_PROFILE,
            repo="local/aresforge",
            base_branch="main",
            registry_path=registry_path,
            approved_branch_plan=True,
            safe_branch_creation_enabled=True,
            github_client=client,
        )
    )

    assert payload["blocked"] is False
    assert payload["status"] == "draft_pr_created"
    assert payload["sync_status"] == "synced"
    assert payload["machine_gates_checked"][0]["gate_profile"] == "github_sync"
    assert payload["machine_gates_passed"] is True
    assert payload["draft_pr_creation_allowed"] is True
    assert payload["pull_request_created"] is True
    assert payload["pr_number"] == 177
    assert payload["pr_url"] == "https://github.test/local/aresforge/pull/177"
    assert payload["github_execution_performed"] is True
    assert payload["mutation_performed"] is True
    assert payload["registry_mutation_performed"] is True
    assert payload["queue_mutation_performed"] is False
    assert payload["pull_request_merged"] is False
    assert payload["auto_merge_enabled"] is False
    assert payload["local_only"] is False
    assert payload["local_registry_record"]["pr_number"] == 177
    assert Path(str(payload["github_preflight_record_path"])).exists()
    assert client.calls[0]["repo"] == "local/aresforge"
    assert client.calls[0]["base_branch"] == "main"
    assert registry_path.exists()
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    assert registry["links"][0]["queue_item_id"] == "m177-pr-draft-creation-gate"
    assert registry["links"][0]["pr_number"] == 177


def test_live_path_blocks_duplicate_registry_pr_link(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    client = _FakeGitHubPrClient()
    registry_path = tmp_path / ".aresforge" / "github_link_registry" / "links.json"
    record_github_link(
        config,
        queue_item_id="m177-pr-draft-creation-gate",
        repository="local/aresforge",
        registry_path=registry_path,
        pr_number=999,
        pr_url="https://github.test/local/aresforge/pull/999",
    )

    payload = _payload(
        create_pr_draft_gate(
            config,
            item_id="m177-pr-draft-creation-gate",
            dry_run=False,
            github_enabled=True,
            autonomy_profile=LIVE_AUTONOMY_PROFILE,
            registry_path=registry_path,
            approved_branch_plan=True,
            safe_branch_creation_enabled=True,
            github_client=client,
        )
    )

    assert payload["blocked"] is True
    assert payload["registry_duplicate_pr_blocked"] is True
    assert any("registry already has a PR link" in reason for reason in payload["blocked_reasons"])
    assert payload["pull_request_created"] is False
    assert payload["github_execution_performed"] is False
    assert client.calls == []


def test_output_path_writes_local_artifact_and_refuses_overwrite(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    output = tmp_path / ".aresforge" / "pr_draft_creation_gate" / "m177.json"

    first = create_pr_draft_gate(
        config,
        item_id="m177-pr-draft-creation-gate",
        dry_run=True,
        output=output,
    )
    second = create_pr_draft_gate(
        config,
        item_id="m177-pr-draft-creation-gate",
        dry_run=True,
        output=output,
    )

    assert first["ok"] is True
    written = json.loads(output.read_text(encoding="utf-8"))
    assert str(output) in written["artifacts_created"]
    assert written["pull_request_created"] is False
    assert second["ok"] is False
    assert second["payload"]["blocked"] is True
    assert second["payload"]["github_execution_performed"] is False
    assert any("Output file already exists" in reason for reason in second["payload"]["blocked_reasons"])
