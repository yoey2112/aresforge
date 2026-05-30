import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.local_project_queue import add_queue_item, init_project_queue
from aresforge.operator.managed_project_registry_local import (
    init_managed_project_registry,
    register_managed_project,
    register_managed_repo,
)
from aresforge.operator.prompt_builder_agent import build_prompt_builder_agent_contract


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


def _seed_item(config: AppConfig, tmp_path: Path, *, status: str = "ready") -> None:
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
        item_id="m78-5-operator-workflow-compression-prompt-builder-contract",
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M78.5 Operator Workflow Compression",
        description="Add a Prompt Builder Agent and workflow preparation command.",
        status=status,
        priority="high",
        item_type="architecture",
        tags=["area:operator-workflow"],
        notes="Acceptance criteria:\n- Prompt Builder is artifact-only\n- No automatic dispatch",
    )["ok"] is True


def test_prompt_builder_produces_stable_artifact_only_payload(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_item(config, tmp_path)

    payload = build_prompt_builder_agent_contract(
        config,
        item_id="m78-5-operator-workflow-compression-prompt-builder-contract",
        target="codex",
    )

    assert payload["ok"] is True
    assert payload["local_only"] is True
    assert payload["artifact_only"] is True
    assert payload["item_id"] == "m78-5-operator-workflow-compression-prompt-builder-contract"
    assert payload["project_id"] == "aresforge"
    assert payload["repo_id"] == "aresforge-main"
    assert payload["target"] == "codex"
    assert payload["target_engine"] == "codex_cli"
    assert payload["target_lane"] == "high_value_codex"
    assert payload["prompt_builder_version"].startswith("m78.5")
    assert Path(payload["prompt_artifact_path"]).exists()
    assert "Task" in payload["prompt_preview"]
    assert "Hard boundaries" in payload["prompt_preview"]
    assert "Testing requirements" in Path(payload["prompt_artifact_path"]).read_text(encoding="utf-8")


def test_prompt_builder_includes_safety_validation_smoke_and_final_requirements(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_item(config, tmp_path)

    payload = build_prompt_builder_agent_contract(
        config,
        item_id="m78-5-operator-workflow-compression-prompt-builder-contract",
    )

    rendered = json.dumps(payload)
    assert "Prompt Builder must not execute prompts." in payload["safety_boundaries"]
    assert "Prompt Builder must not call Codex." in payload["safety_boundaries"]
    assert "Prompt Builder must not invoke local LLMs." in payload["safety_boundaries"]
    assert "Prompt Builder must not mutate source files." in payload["safety_boundaries"]
    assert any("pytest" in command for command in payload["validation_plan"])
    assert any("prepare-queue-item-dispatch" in command for command in payload["smoke_checks"])
    assert "Files changed." in payload["final_response_requirements"]
    assert "docs/context/AGENT_CONTEXT.md" in rendered


def test_prompt_builder_does_not_mutate_queue_status_or_create_run_state(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_item(config, tmp_path)
    queue_path = tmp_path / ".aresforge" / "queue" / "work_items.json"
    before = queue_path.read_text(encoding="utf-8")

    payload = build_prompt_builder_agent_contract(
        config,
        item_id="m78-5-operator-workflow-compression-prompt-builder-contract",
    )
    after = queue_path.read_text(encoding="utf-8")

    assert payload["ok"] is True
    assert before == after
    assert not (tmp_path / ".aresforge" / "codex_dispatch" / "runs").exists()
    assert any("No prompt execution was performed." == entry for entry in payload["boundary_confirmations"])


def test_prompt_builder_blocks_missing_item_safely(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_project_queue(config)["ok"] is True

    payload = build_prompt_builder_agent_contract(config, item_id="missing-item")

    assert payload["ok"] is False
    assert payload["local_only"] is True
    assert payload["artifact_only"] is True
    assert any("Queue item not found" in blocker for blocker in payload["blockers"])
    assert "Resolve blockers" in payload["next_safe_action"]


def test_docs_mention_m78_5_prompt_builder_no_execute_boundaries() -> None:
    doc_paths = [
        Path("docs/context/BUILD_STATE.md"),
        Path("docs/context/AGENT_CONTEXT.md"),
        Path("docs/roadmap/ROADMAP.md"),
        Path("docs/architecture/RUNNABLE_SKELETON.md"),
        Path("docs/operator/LOCAL_OPERATOR_USAGE.md"),
        Path("docs/architecture/CODEX_CLI_MODEL_PROFILE_CONTRACT.md"),
    ]

    for path in doc_paths:
        text = path.read_text(encoding="utf-8")
        assert "M78.5" in text
        assert "Prompt Builder" in text
        assert "prepare-queue-item-dispatch" in text
        assert "does not" in text.lower() or "no " in text.lower()
