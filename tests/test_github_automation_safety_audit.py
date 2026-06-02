import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge import cli
from aresforge.operator.github_automation_safety_audit import (
    DEFAULT_ITEM_ID,
    RECORD_TYPE,
    audit_github_automation_safety,
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


def _seed_queue(config: AppConfig) -> Path:
    result = init_project_queue(config)
    assert result["ok"] is True
    queue_path = Path(str(result["path"]))
    for item_id, title, status in (
        ("m180-hub-github-sync-control-panel", "M180 Hub GitHub Sync Control Panel", "done"),
        ("m182-self-managed-pr-draft-loop-dry-run", "M182 Self-Managed PR Draft Loop Dry Run", "done"),
        (DEFAULT_ITEM_ID, "M183 GitHub Automation Safety Audit", "ready"),
    ):
        assert add_queue_item(
            config,
            item_id=item_id,
            project_id="aresforge",
            repo_id="aresforge-main",
            title=title,
            status=status,
            priority="high",
            item_type="sync",
            tags=["github-loop"],
            source="unit-test",
        )["ok"] is True
    return queue_path


def _seed_registry(config: AppConfig) -> Path:
    registry_path = config.repo_root / ".aresforge" / "github_link_registry" / "links.json"
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
    return registry_path


def test_audit_reports_github_safety_gates_capabilities_and_idempotency(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _touch_expected_tests(tmp_path)
    _seed_queue(config)
    registry_path = _seed_registry(config)

    payload = audit_github_automation_safety(
        config,
        project_id="aresforge",
        registry_path=registry_path,
        repo="local/aresforge",
    )["payload"]

    assert payload["record_type"] == RECORD_TYPE
    assert payload["artifact_type"] == RECORD_TYPE
    assert payload["sync_status"] == "audit_complete"
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
    assert payload["local_only"] is True
    assert payload["capability_counts"]["capabilities_audited"] == 13
    assert payload["capability_counts"]["live_mutation_capable"] == 8
    assert payload["capability_counts"]["targeted_tests_present"] == 13
    assert payload["test_coverage_indicators"]["live_github_required_for_tests"] is False
    assert payload["idempotency_coverage"]["idempotency_status"] == "covered"
    assert "merge_pull_request" in payload["blocked_operations"]
    assert "modify_github_workflow" in payload["blocked_operations"]
    assert payload["safety_boundaries"]["do_not_force_push"] is True
    assert payload["default_behavior"]["live_mutation_requires_explicit_enablement"] is True
    assert all(capability["github_execution_performed"] is False for capability in payload["capabilities"])


def test_audit_warns_when_targeted_test_indicators_are_missing(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)

    payload = audit_github_automation_safety(config, project_id="aresforge")["payload"]

    assert payload["blocked"] is False
    assert payload["test_coverage_indicators"]["capabilities_missing_targeted_test_indicator"] > 0
    assert any("Expected targeted test file not found" in warning for warning in payload["warnings"])
    assert any(risk["risk_id"] == "targeted_test_indicator_gap" for risk in payload["remaining_risks"])
    assert payload["github_execution_performed"] is False


def test_cli_dispatches_audit_github_automation_safety(
    monkeypatch, capsys, tmp_path: Path
) -> None:
    config = _config(tmp_path)
    _touch_expected_tests(tmp_path)
    _seed_queue(config)
    monkeypatch.setattr(cli.AppConfig, "from_env", lambda: config)

    exit_code = cli.main(
        [
            "audit-github-automation-safety",
            "--project-id",
            "aresforge",
            "--repo",
            "local/aresforge",
            "--format",
            "json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["record_type"] == RECORD_TYPE
    assert payload["sync_status"] == "audit_complete"
    assert payload["github_execution_performed"] is False
    assert payload["mutation_performed"] is False
    assert payload["local_only"] is True
