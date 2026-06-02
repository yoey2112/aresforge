import json
from pathlib import Path
import subprocess
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.local_project_queue import add_queue_item, init_project_queue
from aresforge.operator.low_risk_codex_execution_pilot_item import (
    DEFAULT_ITEM_ID,
    prepare_low_risk_codex_pilot,
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


def _seed_queue(config: AppConfig, *, pilot_tags: list[str] | None = None) -> None:
    assert init_project_queue(config)["ok"] is True
    assert add_queue_item(
        config,
        item_id="m159-real-codex-execution-preflight-hardening",
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M159 Real Codex Execution Preflight Hardening",
        status="done",
        priority="high",
        item_type="orchestration",
        tags=["milestone:m159", "codex-execution", "machine-gated"],
    )["ok"] is True
    assert add_queue_item(
        config,
        item_id=DEFAULT_ITEM_ID,
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M160 Low-Risk Codex Execution Pilot Item",
        description="Prepare and optionally execute one low-risk Codex pilot under machine gates.",
        status="ready",
        priority="high",
        item_type="orchestration",
        tags=pilot_tags or ["milestone:m160", "low-risk-codex-pilot", "risk:low", "machine-gated"],
        dependencies=["m159-real-codex-execution-preflight-hardening"],
        completion_requires=["tests_run", "smoke_checks", "commit_hash"],
        evidence_required=["preflight_decisions", "pilot_loop_result"],
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


def _git_runner(*, status_stdout: str, branch: str = "codex/m160"):
    def run(command: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        if command[1:] == ["status", "--short", "--branch"]:
            return subprocess.CompletedProcess(command, 0, status_stdout, "")
        if command[1:] == ["status", "--short"]:
            return subprocess.CompletedProcess(command, 0, "\n".join(status_stdout.splitlines()[1:]), "")
        if command[1:] == ["branch", "--show-current"]:
            return subprocess.CompletedProcess(command, 0, f"{branch}\n", "")
        if command[1:] == ["rev-parse", "HEAD"]:
            return subprocess.CompletedProcess(command, 0, "abc160\n", "")
        if command[1:] == ["rev-parse", "--show-toplevel"]:
            return subprocess.CompletedProcess(command, 0, "C:/tmp/repo\n", "")
        raise AssertionError(f"Unexpected command: {command}")

    return run


def _payload(result: dict[str, object]) -> dict[str, object]:
    return result["payload"]  # type: ignore[index]


def test_low_risk_codex_pilot_dry_run_prepares_without_real_codex(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    _seed_artifacts(config)

    payload = _payload(
        prepare_low_risk_codex_pilot(
            config,
            dry_run=True,
            preflight_command_runner=_git_runner(status_stdout="## codex/m160\n"),
        )
    )

    assert payload["record_type"] == "low_risk_codex_execution_pilot_item_v1"
    assert payload["status"] == "dry_run_prepared"
    assert payload["blocked"] is False
    assert payload["pilot_item_prepared"] is True
    assert payload["dry_run"] is True
    assert payload["low_risk_verification"]["passed"] is True
    assert payload["preflight_decisions"]["real_codex_execution_preflight_passed"] is True
    assert payload["pilot_loop_result"]["attempted"] is True
    assert payload["codex_execution_performed"] is False
    assert payload["model_execution_performed"] is False
    assert payload["github_execution_performed"] is False
    assert payload["patch_application_performed"] is False
    assert payload["queue_mutation_performed"] is False
    assert payload["local_only"] is True


def test_low_risk_codex_pilot_dry_run_reports_preflight_blockers_without_execution(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    _seed_artifacts(config)
    status_stdout = "\n".join(
        [
            "## codex/m160",
            " M src/aresforge/cli.py",
            "?? artifacts/codex_dispatch/run.json",
        ]
    )

    payload = _payload(
        prepare_low_risk_codex_pilot(
            config,
            dry_run=True,
            preflight_command_runner=_git_runner(status_stdout=status_stdout),
        )
    )

    assert payload["status"] == "dry_run_prepared_real_execution_blocked"
    assert payload["blocked"] is True
    assert payload["preflight_decisions"]["blocked"] is True
    assert payload["codex_execution_performed"] is False
    assert any("clean worktree" in reason for reason in payload["blocked_reasons"])


def test_low_risk_codex_pilot_blocks_real_execution_for_high_risk_path(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    _seed_artifacts(config)

    payload = _payload(
        prepare_low_risk_codex_pilot(
            config,
            dry_run=False,
            execution_enabled=True,
            allow_low_risk_code=True,
            changed_paths=[".github/workflows/ci.yml"],
            preflight_command_runner=_git_runner(status_stdout="## codex/m160\n"),
        )
    )

    assert payload["status"] == "blocked"
    assert payload["blocked"] is True
    assert payload["pilot_execution_attempted"] is False
    assert payload["low_risk_verification"]["blocked"] is True
    assert any("outside the M160 low-risk Codex pilot scope" in reason for reason in payload["blocked_reasons"])
    assert payload["codex_execution_performed"] is False
    assert payload["github_execution_performed"] is False


def test_low_risk_codex_pilot_executes_mocked_codex_only_when_gates_pass(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    _seed_artifacts(config)

    def fake_codex_runner(command, **kwargs):  # type: ignore[no-untyped-def]
        stdout = """# M160 Mocked Codex Pilot Result

**Files Changed**
- src/aresforge/low_risk_pilot.py

**What Changed**
- Simulated a low-risk local pilot change.

**Tests Run And Results**
- python -m pytest tests/test_low_risk_codex_execution_pilot_item.py -> passed

**Smoke Checks Run And Results**
- python -m aresforge prepare-low-risk-codex-pilot --item-id m160-low-risk-codex-execution-pilot-item --dry-run --format json -> passed

**Warnings Or Blockers**
- No blockers.

**Commit Hash**
- uncommitted-local-real-run
"""
        return subprocess.CompletedProcess(command, 0, stdout=stdout.encode("utf-8"), stderr=b"")

    def fake_validation_runner(command: str, cwd: Path, timeout_seconds: int) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 0, stdout="passed", stderr="")

    payload = _payload(
        prepare_low_risk_codex_pilot(
            config,
            dry_run=False,
            execution_enabled=True,
            allow_low_risk_code=True,
            codex_command=["codex", "exec", "--mock"],
            changed_paths=["src/aresforge/low_risk_pilot.py"],
            validation_profile="queue_system",
            preflight_command_runner=_git_runner(status_stdout="## codex/m160\n"),
            codex_command_runner=fake_codex_runner,
            validation_command_runner=fake_validation_runner,
        )
    )

    assert payload["status"] == "real_pilot_validated"
    assert payload["blocked"] is False
    assert payload["real_execution_allowed"] is True
    assert payload["codex_execution_performed"] is True
    assert payload["validation_command_execution_performed"] is True
    assert payload["github_execution_performed"] is False
    assert payload["patch_application_performed"] is False
    assert payload["queue_mutation_performed"] is False
    assert payload["pilot_loop_result"]["record_type"] == "end_to_end_codex_loop_real_low_risk_v1"
    assert payload["github_stop_boundary"]["pull_request_merged"] is False
