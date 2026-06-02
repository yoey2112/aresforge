import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.hub.api import get_hub_github_sync_control_panel_data
from aresforge.operator.github_link_registry import record_github_link
from aresforge.operator.hub_github_sync_control_panel import inspect_hub_github_sync_control_panel_data
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


def _seed_queue(config: AppConfig) -> None:
    assert init_project_queue(config)["ok"] is True
    assert add_queue_item(
        config,
        item_id="m179-github-sync-recovery-and-idempotency",
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M179 GitHub Sync Recovery and Idempotency",
        description="Upstream dependency.",
        status="done",
        priority="high",
        item_type="sync",
        tags=["milestone:m179"],
        source="unit-test",
    )["ok"] is True
    assert add_queue_item(
        config,
        item_id="m180-hub-github-sync-control-panel",
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M180 Hub GitHub Sync Control Panel",
        description="Surface local GitHub sync controls.",
        status="ready",
        priority="high",
        item_type="dashboard",
        tags=["milestone:m180", "github-loop"],
        dependencies=["m179-github-sync-recovery-and-idempotency"],
        source="unit-test",
    )["ok"] is True


def _seed_registry(config: AppConfig) -> None:
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


def test_github_sync_control_panel_composes_registry_sync_gates_recovery_and_safe_actions(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    _seed_registry(config)

    payload = inspect_hub_github_sync_control_panel_data(config, project_id="aresforge", repo="local/aresforge")["payload"]

    assert payload["record_type"] == "hub_github_sync_control_panel_v1"
    assert payload["artifact_type"] == "hub_github_sync_control_panel_v1"
    assert payload["project_id"] == "aresforge"
    assert payload["item_id"] == "m180-hub-github-sync-control-panel"
    assert payload["repository"] == "local/aresforge"
    assert payload["sync_status"] == "control_panel_ready"
    assert payload["blocked"] is False
    assert payload["machine_gates_passed"] is True
    assert payload["dry_run"] is True
    assert payload["github_enabled"] is False
    assert payload["github_execution_performed"] is False
    assert payload["mutation_performed"] is False
    assert payload["issue_number"] == 180
    assert payload["pr_number"] == 480
    assert payload["link_registry"]["records"][0]["issue_number"] == 180
    assert payload["issue_sync_plans"]["items"]
    assert payload["status_comments"]["record_type"] == "github_status_comment_durable_sync_v1"
    assert payload["reconciliation"]["record_type"] == "github_issue_state_reconciliation_v1"
    assert payload["closure_gates"]["record_type"] == "github_issue_closure_safe_execution_gate_v1"
    assert payload["pr_draft_plans"]["record_type"] == "pr_draft_branch_planning_contract_v1"
    assert payload["pr_evidence_comments"]["record_type"] == "pr_evidence_comment_sync_v1"
    assert payload["recovery_actions"]["record_type"] == "github_sync_recovery_idempotency_v1"
    assert payload["safety_boundaries"]["unsafe_default_execute_buttons"] is False
    assert payload["pull_request_merge_allowed"] is False
    assert payload["auto_merge_allowed"] is False
    assert payload["force_push_allowed"] is False
    assert payload["workflow_mutation_allowed"] is False
    assert payload["next_safe_actions"]
    assert payload["local_only"] is True


def test_github_sync_control_panel_output_path_writes_local_artifact(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    output = tmp_path / ".aresforge" / "hub_github_sync" / "control-panel.json"

    result = inspect_hub_github_sync_control_panel_data(config, project_id="aresforge", output=output)
    written = json.loads(output.read_text(encoding="utf-8"))

    assert result["ok"] is True
    assert result["wrote_output_file"] is True
    assert written["artifact_type"] == "hub_github_sync_control_panel_v1"
    assert written["artifacts_created"] == [str(output)]


def test_hub_api_exposes_github_sync_control_panel(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)

    payload = get_hub_github_sync_control_panel_data(config, {"project_id": "aresforge"})

    assert payload["ok"] is True
    assert payload["record_type"] == "hub_github_sync_control_panel_v1"
    assert payload["hub_visibility"]["api_endpoint"] == "/api/github-sync/control-panel"
    assert payload["github_execution_performed"] is False
    assert payload["mutation_performed"] is False
    assert payload["local_only"] is True
