import json
from pathlib import Path
import subprocess
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.codex_validation_profiles import (
    DEFAULT_ITEM_ID,
    inspect_codex_validation_profiles,
    select_codex_validation_profile,
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
        item_id="m143-codex-execution-sandbox-and-worktree-guard",
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M143 Codex Execution Sandbox and Worktree Guard",
        description="Completed predecessor.",
        status="done",
        priority="high",
        item_type="orchestration",
        tags=["milestone:m143"],
        source="unit-test",
        notes="Validation evidence present.",
    )["ok"] is True
    assert add_queue_item(
        config,
        item_id=DEFAULT_ITEM_ID,
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M144 Codex Validation Profile Expansion",
        description="Expand validation profile selection for Codex outputs.",
        status="ready",
        priority="high",
        item_type="orchestration",
        tags=["milestone:m144", "codex-execution", "machine-gated"],
        dependencies=["m143-codex-execution-sandbox-and-worktree-guard"],
        source="unit-test",
        notes="Validation profile inspection only; no validation commands run.",
    )["ok"] is True


def _git_runner(status_stdout: str):
    def run(command: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        if command[1:] == ["status", "--short"]:
            return subprocess.CompletedProcess(command, 0, status_stdout, "")
        raise AssertionError(f"Unexpected command: {command}")

    return run


def test_codex_validation_profiles_selects_by_task_paths_and_risk(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)

    result = inspect_codex_validation_profiles(
        config,
        task_type="orchestration",
        risk_class="medium",
        changed_paths=[
            "src/aresforge/operator/codex_validation_profiles.py",
            "tests/test_codex_validation_profiles.py",
        ],
        command_runner=_git_runner(""),
    )
    payload = result["payload"]

    assert payload["record_type"] == "codex_validation_profile_expansion_v1"
    assert payload["artifact_type"] == "codex_validation_profile_expansion_v1"
    assert payload["item_id"] == DEFAULT_ITEM_ID
    assert payload["status"] == "ready"
    assert payload["blocked"] is False
    assert payload["machine_gates_passed"] is True
    assert payload["selected_profile"] == "codex_orchestration"
    assert payload["changed_path_summary"]["path_classes"] == ["codex_runtime", "tests"]
    assert payload["validation_command_execution_performed"] is False
    assert payload["mutation_performed"] is False
    assert payload["external_execution_performed"] is False
    assert payload["model_execution_performed"] is False
    assert payload["codex_execution_performed"] is False
    assert payload["github_execution_performed"] is False
    assert payload["patch_application_performed"] is False
    assert payload["local_only"] is True
    assert "codex_orchestration" in payload["m136_integration"]["supported_profiles"]


def test_codex_validation_profile_selector_expands_high_risk_to_full_local_safe() -> None:
    selected = select_codex_validation_profile(
        task_type="documentation",
        changed_paths=["docs/context/BUILD_STATE.md"],
        risk_class="high",
    )

    assert selected == "full_local_safe"


def test_codex_validation_profiles_blocks_when_queue_item_missing(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_project_queue(config)["ok"] is True

    payload = inspect_codex_validation_profiles(
        config,
        changed_paths=["docs/context/BUILD_STATE.md"],
        command_runner=_git_runner(""),
    )["payload"]

    assert payload["status"] == "blocked"
    assert payload["blocked"] is True
    assert payload["machine_gates_passed"] is False
    assert any("Queue item must exist" in reason for reason in payload["blocked_reasons"])
    assert payload["validation_command_execution_performed"] is False


def test_codex_validation_profiles_output_path_writes_artifact(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    output = tmp_path / ".aresforge" / "codex_execution" / "validation_profiles" / "profiles.json"

    result = inspect_codex_validation_profiles(
        config,
        changed_paths=["docs/context/BUILD_STATE.md"],
        output=output,
        command_runner=_git_runner(""),
    )
    written = json.loads(output.read_text(encoding="utf-8"))

    assert result["ok"] is True
    assert result["wrote_output_file"] is True
    assert written["artifact_type"] == "codex_validation_profile_expansion_v1"
    assert written["artifacts_created"] == [str(output)]
