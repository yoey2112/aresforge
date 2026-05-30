from pathlib import Path
import json

from aresforge.config import AppConfig
from aresforge.operator.local_project_queue import add_queue_item, complete_local_queue_item, init_project_queue
from aresforge.operator.managed_project_registry_local import (
    init_managed_project_registry,
    register_managed_project,
    register_managed_repo,
)
from aresforge.operator.operator_batch_planner import plan_operator_batch


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


def _seed_project(config: AppConfig, tmp_path: Path) -> None:
    assert init_managed_project_registry(config)["ok"] is True
    assert register_managed_project(
        config,
        project_id="aresforge",
        name="AresForge",
        root_path=tmp_path,
        primary_repo_id="aresforge-main",
    )["ok"] is True
    assert register_managed_repo(
        config,
        project_id="aresforge",
        repo_id="aresforge-main",
        name="AresForge Main",
        path=tmp_path,
        role="primary",
    )["ok"] is True
    assert init_project_queue(config)["ok"] is True


def test_operator_batch_planner_returns_ordered_proposed_batch(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_project(config, tmp_path)
    assert add_queue_item(config, item_id="m105-next", project_id="aresforge", repo_id="aresforge-main", title="M105 Next", description="Plan next.", status="proposed")["ok"] is True
    assert add_queue_item(config, item_id="m104-current", project_id="aresforge", repo_id="aresforge-main", title="M104 Current", description="Plan current.", status="ready")["ok"] is True

    result = plan_operator_batch(config, project_id="aresforge", output_format="json")
    payload = json.loads(result["stdout"])

    assert [item["item_id"] for item in payload["proposed_items"]] == ["m104-current", "m105-next"]
    assert payload["proposed_items"][0]["sequence"] == 1
    assert payload["execution_allowed"] is False


def test_operator_batch_planner_excludes_done_and_identifies_blocked(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_project(config, tmp_path)
    assert add_queue_item(config, item_id="m101-done", project_id="aresforge", repo_id="aresforge-main", title="Done", description="Done.", status="in_progress")["ok"] is True
    assert complete_local_queue_item(config, item_id="m101-done", commit_hash="abc123", validation_summary="ok", evidence_note="reviewed")["ok"] is True
    assert add_queue_item(config, item_id="m102-blocked", project_id="aresforge", repo_id="aresforge-main", title="Blocked", description="Blocked.", status="blocked")["ok"] is True

    payload = json.loads(plan_operator_batch(config, project_id="aresforge", output_format="json")["stdout"])

    assert any(item["item_id"] == "m101-done" for item in payload["excluded_items"])
    assert any(item["item_id"] == "m102-blocked" for item in payload["blocked_items"])


def test_operator_batch_planner_respects_dependencies_and_limit(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_project(config, tmp_path)
    assert add_queue_item(config, item_id="m104-parent", project_id="aresforge", repo_id="aresforge-main", title="Parent", description="Parent.", status="ready")["ok"] is True
    assert add_queue_item(config, item_id="m105-child", project_id="aresforge", repo_id="aresforge-main", title="Child", description="Child.", status="ready", dependencies=["m104-parent"])["ok"] is True
    assert add_queue_item(config, item_id="m106-later", project_id="aresforge", repo_id="aresforge-main", title="Later", description="Later.", status="ready")["ok"] is True

    payload = json.loads(plan_operator_batch(config, project_id="aresforge", limit=2, output_format="json")["stdout"])

    assert [item["item_id"] for item in payload["proposed_items"]] == ["m104-parent", "m105-child"]
    assert any(item["item_id"] == "m106-later" and item["reason"] == "limit_reached" for item in payload["excluded_items"])


def test_operator_batch_planner_marks_unsafe_flags_false(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_project(config, tmp_path)
    assert add_queue_item(config, item_id="m104-manual", project_id="aresforge", repo_id="aresforge-main", title="Manual", description="Review manually.", status="ready")["ok"] is True

    payload = json.loads(plan_operator_batch(config, project_id="aresforge", output_format="json")["stdout"])

    assert payload["local_only"] is True
    assert payload["read_only"] is True
    assert payload["execution_allowed"] is False
    assert payload["queue_mutation_allowed"] is False
    assert payload["automatic_next_item_execution_allowed"] is False
