import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.codex_execution_enablement_profile import (
    DEFAULT_ITEM_ID,
    inspect_codex_execution_enablements,
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


def _seed_queue(config: AppConfig) -> None:
    assert init_project_queue(config)["ok"] is True
    assert add_queue_item(
        config,
        item_id="m141-orchestration-run-history-and-recovery",
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M141 Orchestration Run History and Recovery",
        description="Completed predecessor.",
        status="done",
        priority="high",
        item_type="orchestration",
        tags=["milestone:m141"],
        source="unit-test",
        notes="Validation evidence present.",
    )["ok"] is True
    assert add_queue_item(
        config,
        item_id=DEFAULT_ITEM_ID,
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M142 Real Codex Execution Enablement Profile",
        description="Define default-deny machine-gated real Codex execution enablement profiles.",
        status="ready",
        priority="high",
        item_type="orchestration",
        tags=["milestone:m142", "codex-execution", "machine-gated"],
        dependencies=["m141-orchestration-run-history-and-recovery"],
        source="unit-test",
        notes="Profile generation only; no Codex execution.",
    )["ok"] is True


def test_codex_execution_enablements_default_deny_without_execution(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)

    payload = inspect_codex_execution_enablements(config)["payload"]

    assert payload["record_type"] == "codex_execution_enablement_profile_v1"
    assert payload["artifact_type"] == "codex_execution_enablement_profile_v1"
    assert payload["item_id"] == DEFAULT_ITEM_ID
    assert payload["project_id"] == "aresforge"
    assert payload["status"] == "default_denied"
    assert payload["blocked"] is False
    assert payload["machine_gates_passed"] is True
    assert payload["real_codex_execution_default"] == "deny"
    assert payload["real_codex_execution_enabled"] is False
    assert payload["mutation_performed"] is False
    assert payload["external_execution_performed"] is False
    assert payload["model_execution_performed"] is False
    assert payload["codex_execution_performed"] is False
    assert payload["github_execution_performed"] is False
    assert payload["patch_application_performed"] is False
    assert payload["local_only"] is True
    assert "--execution-enabled" in payload["required_explicit_flags"]
    assert any(profile["profile_id"] == "gated_single_codex_dispatch" for profile in payload["enablement_profiles"])
    assert "force_push" in payload["prohibited_operations"]


def test_codex_execution_enablements_block_when_queue_item_missing(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_project_queue(config)["ok"] is True

    payload = inspect_codex_execution_enablements(config)["payload"]

    assert payload["status"] == "blocked"
    assert payload["blocked"] is True
    assert payload["machine_gates_passed"] is False
    assert any("Queue item must exist" in reason for reason in payload["blocked_reasons"])
    assert payload["codex_execution_performed"] is False


def test_codex_execution_enablements_output_path_writes_artifact(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    output = tmp_path / ".aresforge" / "codex_execution" / "enablements" / "profile.json"

    result = inspect_codex_execution_enablements(config, output=output)
    written = json.loads(output.read_text(encoding="utf-8"))

    assert result["ok"] is True
    assert result["wrote_output_file"] is True
    assert written["artifact_type"] == "codex_execution_enablement_profile_v1"
    assert written["artifacts_created"] == [str(output)]
