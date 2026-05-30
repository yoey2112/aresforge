import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.local_project_queue import add_queue_item, init_project_queue
from aresforge.operator.managed_project_registry_local import (
    init_managed_project_registry,
    register_managed_project,
    register_managed_repo,
)
from aresforge.operator.queue_dispatch_preparation import prepare_queue_item_dispatch


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


def _seed_item(config: AppConfig, tmp_path: Path, *, status: str = "ready", item_id: str = "m78-5") -> None:
    assert init_managed_project_registry(config)["ok"] is True
    assert register_managed_project(
        config,
        project_id="aresforge",
        name="AresForge",
        root_path=tmp_path,
        status="active",
        primary_repo_id="aresforge-main",
    )["ok"] is True
    assert register_managed_repo(
        config,
        project_id="aresforge",
        repo_id="aresforge-main",
        name="AresForge Main",
        path=tmp_path,
        role="primary",
        status="active",
    )["ok"] is True
    assert init_project_queue(config)["ok"] is True
    assert add_queue_item(
        config,
        item_id=item_id,
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M78.5 Prompt Builder",
        description="Prepare the operator workflow for dispatch.",
        status=status,
        priority="high",
        item_type="architecture",
    )["ok"] is True


def _queue_item_status(tmp_path: Path, item_id: str) -> str:
    raw = json.loads((tmp_path / ".aresforge" / "queue" / "work_items.json").read_text(encoding="utf-8"))
    return next(item["status"] for item in raw["work_items"] if item["item_id"] == item_id)


def test_workflow_preparation_inspects_readiness_generates_prompt_and_does_not_dispatch(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_item(config, tmp_path, item_id="m78-5")

    result = prepare_queue_item_dispatch(config, item_id="m78-5", target="codex")
    payload = json.loads(result["stdout"])

    assert result["ok"] is True
    assert payload["local_only"] is True
    assert payload["readiness_status"] == "ready"
    assert payload["can_start"] is True
    assert payload["started"] is False
    assert Path(payload["prompt_artifact_path"]).exists()
    assert payload["llm_decision_matrix"]["advisory_only"] is True
    assert payload["llm_decision_matrix"]["execution_allowed"] is False
    assert payload["llm_decision_matrix"]["queue_mutation_allowed"] is False
    assert payload["operator_approval_required"] is True
    assert payload["dispatch_ready"] is True
    assert payload["dispatch_allowed"] is False
    assert payload["automatic_next_item_execution_allowed"] is False
    assert payload["queue_completion_allowed"] is False
    assert payload["dispatch_contract_summary"]["dispatch_allowed"] is False
    assert payload["dispatch_contract_summary"]["codex_cli_invocation_allowed"] is False
    assert not (tmp_path / ".aresforge" / "codex_dispatch" / "runs").exists()
    assert _queue_item_status(tmp_path, "m78-5") == "ready"


def test_workflow_preparation_starts_only_when_explicit_flag_is_supplied(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_item(config, tmp_path, item_id="startable")

    no_start = json.loads(prepare_queue_item_dispatch(config, item_id="startable")["stdout"])
    with_start = json.loads(
        prepare_queue_item_dispatch(config, item_id="startable", start_if_ready=True, force=True)["stdout"]
    )

    assert no_start["started"] is False
    assert with_start["started"] is True
    assert with_start["readiness_status"] == "ready"
    assert with_start["can_start"] is True
    assert with_start["post_start_readiness_status"] == "blocked"
    assert with_start["start_result"]["status"] == "in_progress"
    assert _queue_item_status(tmp_path, "startable") == "in_progress"


def test_workflow_preparation_does_not_approve_complete_or_auto_run_next_item(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_item(config, tmp_path, item_id="safe-item")

    payload = json.loads(prepare_queue_item_dispatch(config, item_id="safe-item", start_if_ready=True)["stdout"])

    assert payload["operator_approval_required"] is True
    assert payload["dispatch_contract_summary"]["operator_approval_status"] == "not_requested"
    assert payload["dispatch_allowed"] is False
    assert payload["queue_completion_allowed"] is False
    assert payload["automatic_next_item_execution_allowed"] is False
    assert "approve-codex-dispatch" in payload["next_safe_action"]
    assert _queue_item_status(tmp_path, "safe-item") == "in_progress"


def test_workflow_preparation_blocks_missing_item_safely(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_project_queue(config)["ok"] is True

    result = prepare_queue_item_dispatch(config, item_id="missing-item")
    payload = json.loads(result["stdout"])

    assert result["ok"] is False
    assert payload["readiness_status"] == "not_found"
    assert payload["can_start"] is False
    assert payload["started"] is False
    assert payload["dispatch_allowed"] is False
    assert any("Queue item not found" in blocker for blocker in payload["blockers"])


def test_workflow_preparation_supports_manual_target_without_codex_approval(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_item(config, tmp_path, item_id="manual-item")

    payload = json.loads(prepare_queue_item_dispatch(config, item_id="manual-item", target="manual")["stdout"])

    assert payload["target"] == "manual"
    assert payload["operator_approval_required"] is False
    assert payload["dispatch_contract_summary"]["operator_approval_status"] == "not_applicable"
    assert payload["dispatch_allowed"] is False
