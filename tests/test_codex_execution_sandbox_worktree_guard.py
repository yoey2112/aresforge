import json
from pathlib import Path
import subprocess
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.codex_execution_sandbox_worktree_guard import (
    DEFAULT_ITEM_ID,
    inspect_codex_worktree_guard,
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
        item_id="m142-real-codex-execution-enablement-profile",
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M142 Real Codex Execution Enablement Profile",
        description="Completed predecessor.",
        status="done",
        priority="high",
        item_type="orchestration",
        tags=["milestone:m142"],
        source="unit-test",
        notes="Validation evidence present.",
    )["ok"] is True
    assert add_queue_item(
        config,
        item_id=DEFAULT_ITEM_ID,
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M143 Codex Execution Sandbox and Worktree Guard",
        description="Protect Codex execution with sandbox and worktree guards.",
        status="ready",
        priority="high",
        item_type="orchestration",
        tags=["milestone:m143", "codex-execution", "machine-gated"],
        dependencies=["m142-real-codex-execution-enablement-profile"],
        source="unit-test",
        notes="Guard inspection only; no Codex execution.",
    )["ok"] is True


def _git_runner(*, status_stdout: str, branch: str = "feature/test"):
    def run(command: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        if command[:2] != ["git", "status"] and command[:2] != ["git", "branch"] and command[:2] != ["git", "rev-parse"]:
            raise AssertionError(f"Unexpected command: {command}")
        if command[1:] == ["status", "--short", "--branch"]:
            return subprocess.CompletedProcess(command, 0, status_stdout, "")
        if command[1:] == ["branch", "--show-current"]:
            return subprocess.CompletedProcess(command, 0, f"{branch}\n", "")
        if command[1:] == ["rev-parse", "HEAD"]:
            return subprocess.CompletedProcess(command, 0, "abc123\n", "")
        if command[1:] == ["rev-parse", "--show-toplevel"]:
            return subprocess.CompletedProcess(command, 0, "C:/tmp/repo\n", "")
        raise AssertionError(f"Unexpected command: {command}")

    return run


def test_codex_worktree_guard_ready_without_execution(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)

    payload = inspect_codex_worktree_guard(
        config,
        command_runner=_git_runner(status_stdout="## feature/test\n"),
    )["payload"]

    assert payload["record_type"] == "codex_execution_sandbox_worktree_guard_v1"
    assert payload["artifact_type"] == "codex_execution_sandbox_worktree_guard_v1"
    assert payload["item_id"] == DEFAULT_ITEM_ID
    assert payload["status"] == "ready"
    assert payload["blocked"] is False
    assert payload["machine_gates_passed"] is True
    assert payload["dirty_tree_detected"] is False
    assert payload["worktree_safe_for_future_real_codex_execution"] is True
    assert payload["mutation_performed"] is False
    assert payload["external_execution_performed"] is False
    assert payload["model_execution_performed"] is False
    assert payload["codex_execution_performed"] is False
    assert payload["github_execution_performed"] is False
    assert payload["patch_application_performed"] is False
    assert payload["local_only"] is True
    assert payload["codex_execution_guard"]["sandbox_policy"]["shell"] is False
    assert payload["codex_execution_guard"]["output_capture_boundaries"]["stdout_artifact_required"] is True


def test_codex_worktree_guard_reports_dirty_tree_as_guard_warning(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    status_stdout = "\n".join(
        [
            "## feature/test",
            " M src/aresforge/cli.py",
            "?? tests/test_codex_execution_sandbox_worktree_guard.py",
            "?? artifacts/codex_execution/guard.json",
        ]
    )

    payload = inspect_codex_worktree_guard(
        config,
        max_status_lines=2,
        command_runner=_git_runner(status_stdout=status_stdout),
    )["payload"]
    worktree = payload["codex_execution_guard"]["worktree_state"]

    assert payload["status"] == "dirty_worktree_guarded"
    assert payload["blocked"] is False
    assert payload["dirty_tree_detected"] is True
    assert payload["worktree_safe_for_future_real_codex_execution"] is False
    assert worktree["status_line_count"] == 3
    assert worktree["status_lines_truncated"] is True
    assert worktree["status_lines_omitted"] == 1
    assert worktree["dirty_path_summary"]["source_changes"] == 1
    assert worktree["dirty_path_summary"]["test_changes"] == 1
    assert any("Working tree has local changes" in warning for warning in payload["warnings"])


def test_codex_worktree_guard_blocks_when_queue_item_missing(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_project_queue(config)["ok"] is True

    payload = inspect_codex_worktree_guard(
        config,
        command_runner=_git_runner(status_stdout="## feature/test\n"),
    )["payload"]

    assert payload["status"] == "blocked"
    assert payload["blocked"] is True
    assert payload["machine_gates_passed"] is False
    assert any("Queue item must exist" in reason for reason in payload["blocked_reasons"])
    assert payload["codex_execution_performed"] is False


def test_codex_worktree_guard_output_path_writes_artifact(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    output = tmp_path / ".aresforge" / "codex_execution" / "worktree_guard" / "guard.json"

    result = inspect_codex_worktree_guard(
        config,
        output=output,
        command_runner=_git_runner(status_stdout="## feature/test\n"),
    )
    written = json.loads(output.read_text(encoding="utf-8"))

    assert result["ok"] is True
    assert result["wrote_output_file"] is True
    assert written["artifact_type"] == "codex_execution_sandbox_worktree_guard_v1"
    assert written["artifacts_created"] == [str(output)]
