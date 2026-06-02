import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge import cli
from aresforge.operator.github_link_registry import record_github_link
from aresforge.operator.live_github_loop_readiness_report import (
    DEFAULT_ITEM_ID,
    RECORD_TYPE,
    SOURCE_OF_TRUTH_DOCS,
    generate_live_github_loop_readiness_report,
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


def _seed_docs(config: AppConfig) -> None:
    milestones = " ".join(f"M{number}" for number in range(170, 185))
    for relative in SOURCE_OF_TRUTH_DOCS:
        path = config.repo_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"# {path.stem}\n\n{milestones}\n", encoding="utf-8")


def _touch_expected_tests(tmp_path: Path) -> None:
    for path in (
        "tests/test_github_link_registry.py",
        "tests/test_github_issue_creation_real_run_gate.py",
        "tests/test_queue_to_github_issue_backfill.py",
        "tests/test_github_status_comment_durable_sync.py",
        "tests/test_github_issue_state_reconciliation.py",
        "tests/test_github_issue_closure_safe_execution_gate.py",
        "tests/test_pr_draft_branch_planning_contract.py",
        "tests/test_pr_draft_creation_gate.py",
        "tests/test_pr_evidence_comment_sync.py",
        "tests/test_github_sync_recovery_idempotency.py",
        "tests/test_hub_github_sync_control_panel.py",
        "tests/test_self_managed_issue_loop_real_run.py",
        "tests/test_self_managed_pr_draft_loop_dry_run.py",
    ):
        full = tmp_path / path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text("# targeted test indicator\n", encoding="utf-8")


def _seed_queue(config: AppConfig) -> None:
    assert init_project_queue(config)["ok"] is True
    names = {
        170: "github-link-registry-for-queue-items",
        171: "github-issue-creation-real-run-gate",
        172: "queue-to-github-issue-backfill",
        173: "github-status-comment-durable-sync",
        174: "github-issue-state-reconciliation",
        175: "github-issue-closure-safe-execution-gate",
        176: "pr-draft-branch-planning-contract",
        177: "pr-draft-creation-gate",
        178: "pr-evidence-comment-sync",
        179: "github-sync-recovery-and-idempotency",
        180: "hub-github-sync-control-panel",
        181: "self-managed-issue-loop-real-run",
        182: "self-managed-pr-draft-loop-dry-run",
        183: "github-automation-safety-audit",
        184: "sprint-closeout-and-live-github-loop-readiness-report",
    }
    for number in range(170, 185):
        item_id = DEFAULT_ITEM_ID if number == 184 else f"m{number}-{names[number]}"
        assert add_queue_item(
            config,
            item_id=item_id,
            project_id="aresforge",
            repo_id="aresforge-main",
            title=f"M{number} {names[number]}",
            description="Milestone implementation.",
            status="done",
            priority="high",
            item_type="sync",
            tags=[f"milestone:m{number}", "github-loop"],
            source="unit-test",
            notes="Validation evidence present.",
        )["ok"] is True
    queue_path = config.repo_root / ".aresforge" / "queue" / "work_items.json"
    queue = json.loads(queue_path.read_text(encoding="utf-8"))
    for item in queue["work_items"]:
        item["completion_commit"] = "abc123"
        item["validation_summary"] = "Targeted validation passed."
        item["tests_run"] = ["python -m pytest tests/test_live_github_loop_readiness_report.py -> passed"]
        item["artifact_paths"] = [".aresforge/live_github_loop_readiness_reports/example.json"]
    queue_path.write_text(json.dumps(queue, indent=2) + "\n", encoding="utf-8")


def _seed_registry(config: AppConfig) -> Path:
    result = record_github_link(
        config,
        queue_item_id="m180-hub-github-sync-control-panel",
        project_id="aresforge",
        item_id="m180-hub-github-sync-control-panel",
        repository="local/aresforge",
        issue_number=180,
        issue_url="https://github.com/local/aresforge/issues/180",
        pr_number=480,
        pr_url="https://github.com/local/aresforge/pull/480",
        sync_status="linked",
        linked_by="unit-test",
        link_source="unit-test",
        output_format="json",
    )
    assert result["ok"] is True
    return config.repo_root / ".aresforge" / "github_link_registry" / "links.json"


def test_generate_live_github_loop_readiness_report_closes_m170_m184(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_docs(config)
    _touch_expected_tests(tmp_path)
    _seed_queue(config)
    registry_path = _seed_registry(config)

    payload = generate_live_github_loop_readiness_report(
        config,
        project_id="aresforge",
        sprint_start="M170",
        sprint_end="M184",
        registry_path=registry_path,
        repo="local/aresforge",
    )["payload"]

    assert payload["record_type"] == RECORD_TYPE
    assert payload["artifact_type"] == RECORD_TYPE
    assert payload["generated"] is True
    assert payload["project_id"] == "aresforge"
    assert payload["item_id"] == DEFAULT_ITEM_ID
    assert payload["repository"] == "local/aresforge"
    assert payload["sync_status"] == "ready_with_warnings"
    assert payload["blocked"] is False
    assert payload["blocked_reasons"] == []
    assert payload["machine_gates_passed"] is True
    assert payload["dry_run"] is True
    assert payload["github_enabled"] is False
    assert payload["github_execution_performed"] is False
    assert payload["mutation_performed"] is False
    assert payload["registry_mutation_performed"] is False
    assert payload["queue_mutation_performed"] is False
    assert payload["local_only"] is True
    assert payload["milestones_reviewed"] == [f"M{number}" for number in range(170, 185)]
    assert payload["sprint_closeout_summary"]["all_milestone_items_complete"] is True
    assert len(payload["capability_summary"]) == 15
    assert payload["queue_summary"]["status_counts"] == {"done": 15}
    assert payload["docs_sync"]["consistent"] is True
    assert payload["readiness_summary"]["live_mutation_capable_surfaces"] == 8
    assert payload["github_safety"]["mutation_performed"] is False
    assert payload["safety_boundaries"]["do_not_force_push"] is True
    assert "merge_pull_request" in payload["safety_boundaries"]["blocked_operations"]
    assert payload["next_sprint_recommendations"]


def test_live_github_loop_readiness_report_blocks_when_milestone_missing(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_docs(config)
    _touch_expected_tests(tmp_path)
    _seed_queue(config)
    queue_path = config.repo_root / ".aresforge" / "queue" / "work_items.json"
    queue = json.loads(queue_path.read_text(encoding="utf-8"))
    queue["work_items"] = [item for item in queue["work_items"] if "milestone:m184" not in item.get("tags", [])]
    queue_path.write_text(json.dumps(queue, indent=2) + "\n", encoding="utf-8")

    payload = generate_live_github_loop_readiness_report(config, project_id="aresforge")["payload"]

    assert payload["blocked"] is True
    assert payload["sync_status"] == "blocked"
    assert any("M184" in reason for reason in payload["blocked_reasons"])
    assert payload["github_execution_performed"] is False
    assert payload["mutation_performed"] is False


def test_cli_dispatches_live_github_loop_readiness_report(monkeypatch, capsys, tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_docs(config)
    _touch_expected_tests(tmp_path)
    _seed_queue(config)
    registry_path = _seed_registry(config)
    monkeypatch.setattr(cli.AppConfig, "from_env", lambda: config)

    exit_code = cli.main(
        [
            "generate-live-github-loop-readiness-report",
            "--project-id",
            "aresforge",
            "--sprint-start",
            "M170",
            "--sprint-end",
            "M184",
            "--registry-path",
            str(registry_path),
            "--repo",
            "local/aresforge",
            "--format",
            "json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["record_type"] == RECORD_TYPE
    assert payload["github_execution_performed"] is False
    assert payload["mutation_performed"] is False
    assert payload["local_only"] is True
