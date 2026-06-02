import json
from pathlib import Path
import subprocess
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.local_project_queue import add_queue_item, init_project_queue
from aresforge.operator.real_codex_execution_preflight_hardening import (
    DEFAULT_ITEM_ID,
    preflight_real_codex_execution,
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


def _seed_queue(config: AppConfig) -> None:
    assert init_project_queue(config)["ok"] is True
    assert add_queue_item(
        config,
        item_id="m158-operator-autonomy-configuration-profile",
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M158 Operator Autonomy Configuration Profile",
        status="done",
        priority="high",
        item_type="orchestration",
        tags=["milestone:m158", "machine-gated"],
    )["ok"] is True
    assert add_queue_item(
        config,
        item_id=DEFAULT_ITEM_ID,
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M159 Real Codex Execution Preflight Hardening",
        status="ready",
        priority="high",
        item_type="orchestration",
        tags=["milestone:m159", "codex-execution", "machine-gated"],
        dependencies=["m158-operator-autonomy-configuration-profile"],
    )["ok"] is True


def _seed_artifacts(config: AppConfig) -> None:
    (config.repo_root / ".aresforge" / "orchestrator").mkdir(parents=True, exist_ok=True)
    (config.repo_root / ".aresforge" / "codex_dispatch").mkdir(parents=True, exist_ok=True)
    (config.repo_root / "artifacts" / "codex_dispatch").mkdir(parents=True, exist_ok=True)
    (config.repo_root / "artifacts" / "codex_result_ingestion").mkdir(parents=True, exist_ok=True)
    (config.repo_root / ".aresforge" / "orchestrator" / "run_history.json").write_text(
        json.dumps(
            {
                "record_type": "durable_orchestration_run_store_v1",
                "artifact_type": "durable_orchestration_run_store_v1",
                "schema_version": "m155.1",
                "generated": True,
                "project_id": "aresforge",
                "created_at": "2026-06-01T00:00:00Z",
                "updated_at": "2026-06-01T00:00:00Z",
                "records": [],
            }
        )
        + "\n",
        encoding="utf-8",
    )


def _git_runner(*, status_stdout: str, branch: str = "codex/m159"):
    def run(command: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        if command[1:] == ["status", "--short", "--branch"]:
            return subprocess.CompletedProcess(command, 0, status_stdout, "")
        if command[1:] == ["status", "--short"]:
            return subprocess.CompletedProcess(command, 0, "\n".join(status_stdout.splitlines()[1:]), "")
        if command[1:] == ["branch", "--show-current"]:
            return subprocess.CompletedProcess(command, 0, f"{branch}\n", "")
        if command[1:] == ["rev-parse", "HEAD"]:
            return subprocess.CompletedProcess(command, 0, "abc123\n", "")
        if command[1:] == ["rev-parse", "--show-toplevel"]:
            return subprocess.CompletedProcess(command, 0, "C:/tmp/repo\n", "")
        raise AssertionError(f"Unexpected command: {command}")

    return run


def test_preflight_real_codex_execution_reports_ready_without_running_codex(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    _seed_artifacts(config)

    result = preflight_real_codex_execution(
        config,
        dry_run=True,
        changed_paths=["src/aresforge/operator/real_codex_execution_preflight_hardening.py"],
        command_runner=_git_runner(status_stdout="## codex/m159\n"),
    )
    payload = result["payload"]

    assert result["ok"] is True
    assert payload["record_type"] == "real_codex_execution_preflight_hardening_v1"
    assert payload["artifact_type"] == "real_codex_execution_preflight_hardening_v1"
    assert payload["status"] == "ready_for_explicit_gated_real_codex"
    assert payload["blocked"] is False
    assert payload["real_codex_execution_preflight_passed"] is True
    assert payload["machine_gates_passed"] is True
    assert {gate["gate_profile"] for gate in payload["machine_gates_checked"]} == {
        "read_only_agent",
        "operator_autonomy_profile",
    }
    assert payload["autonomy_profile"] == "codex_low_risk_enabled"
    assert payload["worktree_guard_summary"]["dirty_tree_detected"] is False
    assert payload["run_store_readiness"]["schema_valid"] is True
    assert payload["artifact_readiness"]["all_required_paths_present"] is True
    assert payload["retry_policy"]["automatic_retry_allowed"] is False
    assert payload["source_patch_risk_policy"]["source_patch_application_allowed"] is False
    assert payload["codex_execution_performed"] is False
    assert payload["model_execution_performed"] is False
    assert payload["github_execution_performed"] is False
    assert payload["patch_application_performed"] is False
    assert payload["local_only"] is True


def test_preflight_blocks_future_codex_on_dirty_tree_but_command_succeeds(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    _seed_artifacts(config)
    status_stdout = "\n".join(
        [
            "## codex/m159",
            " M src/aresforge/cli.py",
            "?? artifacts/codex_dispatch/run.json",
        ]
    )

    result = preflight_real_codex_execution(
        config,
        dry_run=True,
        changed_paths=["src/aresforge/cli.py"],
        command_runner=_git_runner(status_stdout=status_stdout),
    )
    payload = result["payload"]

    assert result["ok"] is True
    assert payload["status"] == "blocked"
    assert payload["blocked"] is True
    assert payload["codex_execution_would_be_blocked"] is True
    assert any("clean worktree" in reason for reason in payload["blocked_reasons"])
    assert payload["worktree_guard_summary"]["dirty_tree_detected"] is True
    assert payload["codex_execution_performed"] is False


def test_preflight_requires_dry_run_without_execution(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    _seed_artifacts(config)

    result = preflight_real_codex_execution(config, dry_run=False)
    payload = result["payload"]

    assert result["ok"] is False
    assert payload["status"] == "blocked"
    assert payload["blocked"] is True
    assert any("--dry-run" in reason for reason in payload["blocked_reasons"])
    assert payload["codex_execution_performed"] is False


def test_preflight_output_path_writes_local_artifact(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    _seed_artifacts(config)
    output = tmp_path / ".aresforge" / "codex_execution" / "preflight" / "m159-preflight.json"

    result = preflight_real_codex_execution(
        config,
        dry_run=True,
        output=output,
        command_runner=_git_runner(status_stdout="## codex/m159\n"),
    )
    written = json.loads(output.read_text(encoding="utf-8"))

    assert result["ok"] is True
    assert result["wrote_output_file"] is True
    assert written["artifact_type"] == "real_codex_execution_preflight_hardening_v1"
    assert written["artifacts_created"] == [str(output)]
