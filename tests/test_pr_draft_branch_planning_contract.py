import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.local_project_queue import add_queue_item, init_project_queue
from aresforge.operator.pr_draft_branch_planning_contract import (
    RECORD_TYPE,
    plan_pr_draft_branch,
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
        item_id="m175-github-issue-closure-safe-execution-gate",
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M175 GitHub Issue Closure Safe Execution Gate",
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
        description="Generate a PR draft branch plan without creating branches or pull requests.",
        status="done",
        priority="high",
        item_type="sync",
        tags=["milestone:m176", "pr-draft-branch", "github-loop", "machine-gated"],
        dependencies=["m175-github-issue-closure-safe-execution-gate"],
        notes="Branch and PR planning only; no live mutation.",
    )["ok"] is True
    assert add_queue_item(
        config,
        item_id="m176-incomplete",
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M176 incomplete",
        status="in_progress",
        priority="normal",
        item_type="sync",
    )["ok"] is True

    raw = json.loads(queue_path.read_text(encoding="utf-8"))
    for item in raw["work_items"]:
        if item["item_id"] == "m176-pr-draft-branch-planning-contract":
            item["github_issue"] = {
                "number": 176,
                "url": "https://github.com/local/aresforge/issues/176",
                "state": "open",
            }
            item["completed_at"] = "2026-06-02T13:00:00Z"
            item["completed_by"] = "local_operator"
            item["completion_commit"] = "abc176"
            item["validation_summary"] = "M176 targeted validation passed."
            item["tests_run"] = [
                "python -m pytest tests/test_pr_draft_branch_planning_contract.py -> passed",
                "python -m aresforge plan-pr-draft-branch --item-id m176-pr-draft-branch-planning-contract --format json -> passed",
            ]
            item["evidence_note"] = "Local validation and changed-file evidence support branch planning review."
            item["changed_files"] = [
                "src/aresforge/operator/pr_draft_branch_planning_contract.py",
                "tests/test_pr_draft_branch_planning_contract.py",
                "src/aresforge/cli.py",
            ]
            item["artifact_paths"] = [".aresforge/pr_draft_branch_plans/m176.json"]
            item["completion_evidence"] = {
                "record_type": "pr_draft_branch_planning_contract_v1",
                "status": "branch_plan_created",
                "machine_gates_passed": True,
                "artifacts_created": [".aresforge/pr_draft_branch_plans/m176.json"],
            }
    queue_path.write_text(json.dumps(raw, indent=2) + "\n", encoding="utf-8")
    return queue_path


def _payload(result: dict[str, object]) -> dict[str, object]:
    return result["payload"]  # type: ignore[index]


def test_generates_pr_draft_branch_plan_without_branch_or_pr_mutation(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)

    payload = _payload(
        plan_pr_draft_branch(
            config,
            item_id="m176-pr-draft-branch-planning-contract",
            base_branch="main",
        )
    )

    assert payload["record_type"] == RECORD_TYPE
    assert payload["status"] == "branch_plan_created"
    assert payload["sync_status"] == "dry_run_ready"
    assert payload["blocked"] is False
    assert payload["project_id"] == "aresforge"
    assert payload["item_id"] == "m176-pr-draft-branch-planning-contract"
    assert payload["repository"] == "local/aresforge"
    assert payload["issue_number"] == 176
    assert payload["issue_url"] == "https://github.com/local/aresforge/issues/176"
    assert payload["pr_number"] is None
    assert payload["pr_url"] == ""
    assert payload["machine_gates_passed"] is True
    assert payload["dry_run"] is True
    assert payload["github_enabled"] is False
    assert payload["github_execution_performed"] is False
    assert payload["mutation_performed"] is False
    assert payload["github_branch_mutation_performed"] is False
    assert payload["github_pr_mutation_performed"] is False
    assert payload["branch_creation_allowed"] is False
    assert payload["branch_created"] is False
    assert payload["branch_pushed"] is False
    assert payload["pr_creation_allowed"] is False
    assert payload["pull_request_created"] is False
    assert payload["pull_request_merged"] is False
    assert payload["auto_merge_enabled"] is False
    assert payload["queue_mutation_performed"] is False
    assert payload["codex_execution_performed"] is False
    assert payload["model_execution_performed"] is False
    assert payload["patch_application_performed"] is False
    assert payload["validation_command_execution_performed"] is False
    assert payload["recovery_available"] is True
    assert payload["local_only"] is True
    assert payload["idempotency_key"].startswith("pr-draft-branch-plan:")
    assert payload["branch_plan"]["branch_name"] == "codex/m176-pr-draft-branch-planning-contract"
    assert payload["branch_plan"]["base_branch"] == "main"
    assert payload["expected_pr"]["title"] == "M176 PR Draft Branch Planning Contract"
    assert payload["expected_pr"]["draft"] is True
    assert "src/aresforge/operator/pr_draft_branch_planning_contract.py" in payload["changed_file_evidence"]["changed_files"]
    assert payload["linked_queue_items"][0]["item_id"] == "m176-pr-draft-branch-planning-contract"
    assert payload["linked_issues"][0]["issue_number"] == 176
    assert "create_pull_request" in payload["github_operations_blocked"]
    assert "push_branch" in payload["github_operations_blocked"]


def test_github_enabled_still_remains_planning_only(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)

    payload = _payload(
        plan_pr_draft_branch(
            config,
            item_id="m176-pr-draft-branch-planning-contract",
            github_enabled=True,
            dry_run=False,
            autonomy_profile="github_issue_sync_enabled",
            base_branch="main",
        )
    )

    assert payload["blocked"] is False
    assert payload["dry_run"] is True
    assert payload["github_enabled"] is True
    assert payload["github_execution_performed"] is False
    assert payload["mutation_performed"] is False
    assert payload["branch_created"] is False
    assert payload["pull_request_created"] is False
    assert payload["branch_plan"]["branch_creation_allowed"] is False
    assert payload["expected_pr"]["create_allowed"] is False
    assert any("mutation remains disabled" in warning for warning in payload["warnings"])


def test_blocks_when_changed_file_evidence_is_missing(tmp_path: Path) -> None:
    config = _config(tmp_path)
    queue_path = _seed_queue(config)
    raw = json.loads(queue_path.read_text(encoding="utf-8"))
    for item in raw["work_items"]:
        if item["item_id"] == "m176-pr-draft-branch-planning-contract":
            item["changed_files"] = []
    queue_path.write_text(json.dumps(raw, indent=2) + "\n", encoding="utf-8")

    payload = _payload(
        plan_pr_draft_branch(
            config,
            item_id="m176-pr-draft-branch-planning-contract",
            base_branch="main",
        )
    )

    assert payload["status"] == "blocked"
    assert payload["github_execution_performed"] is False
    assert payload["mutation_performed"] is False
    assert any("Changed file evidence" in reason for reason in payload["blocked_reasons"])


def test_output_path_writes_local_artifact_and_refuses_overwrite(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    output = tmp_path / ".aresforge" / "pr_draft_branch_plans" / "m176.json"

    first = plan_pr_draft_branch(
        config,
        item_id="m176-pr-draft-branch-planning-contract",
        base_branch="main",
        output=output,
    )
    second = plan_pr_draft_branch(
        config,
        item_id="m176-pr-draft-branch-planning-contract",
        base_branch="main",
        output=output,
    )

    assert first["ok"] is True
    written = json.loads(output.read_text(encoding="utf-8"))
    assert str(output) in written["artifacts_created"]
    assert written["branch_created"] is False
    assert written["pull_request_created"] is False
    assert second["ok"] is False
    assert second["payload"]["blocked"] is True
    assert second["payload"]["github_execution_performed"] is False
    assert second["payload"]["mutation_performed"] is False
    assert any("Output file already exists" in reason for reason in second["payload"]["blocked_reasons"])
