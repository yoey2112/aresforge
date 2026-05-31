import json
from pathlib import Path
import subprocess

from aresforge.config import AppConfig
from aresforge.operator.end_to_end_codex_loop_dry_run import run_end_to_end_codex_loop_dry_run
from aresforge.operator.local_project_queue import add_queue_item, init_project_queue


ITEM_ID = "m152-end-to-end-codex-loop-real-run-for-low-risk-code"


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
        item_id=ITEM_ID,
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M152 End-to-End Codex Loop Real Run for Low-Risk Code",
        description="Run the machine-gated real Codex loop for low-risk code only.",
        status="ready",
        priority="high",
        item_type="orchestration",
        tags=["milestone:m152", "codex-loop", "low-risk-code", "risk:low"],
        completion_requires=["tests_run", "smoke_checks", "commit_hash"],
        evidence_required=["dispatch_result_evidence", "validation_results"],
    )["ok"] is True
    transaction_log = config.repo_root / ".aresforge" / "queue" / "transaction_log.json"
    transaction_log.parent.mkdir(parents=True, exist_ok=True)
    transaction_log.write_text(json.dumps({"schema_version": "1.0", "transactions": []}), encoding="utf-8")


def _payload(result: dict[str, object]) -> dict[str, object]:
    return result["payload"]  # type: ignore[index]


def test_real_low_risk_loop_dry_run_reports_default_deny_boundaries(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)

    payload = _payload(
        run_end_to_end_codex_loop_dry_run(
            config,
            item_id=ITEM_ID,
            dry_run=True,
            output_format="json",
        )
    )

    assert payload["record_type"] == "end_to_end_codex_loop_real_low_risk_v1"
    assert payload["generated"] is True
    assert payload["status"] == "dry_run_completed"
    assert payload["blocked"] is False
    assert payload["machine_gates_passed"] is True
    assert {gate["gate_profile"] for gate in payload["machine_gates_checked"]} == {
        "codex_dispatch",
        "low_risk_code_scope",
    }
    assert payload["mutation_performed"] is False
    assert payload["external_execution_performed"] is False
    assert payload["model_execution_performed"] is False
    assert payload["codex_execution_performed"] is False
    assert payload["github_execution_performed"] is False
    assert payload["patch_application_performed"] is False
    assert payload["local_only"] is True
    assert payload["real_execution_allowed"] is False
    assert all(Path(path).exists() for path in payload["artifacts_created"])


def test_real_low_risk_loop_blocks_without_explicit_real_flags(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)

    payload = _payload(
        run_end_to_end_codex_loop_dry_run(
            config,
            item_id=ITEM_ID,
            dry_run=False,
            output_format="json",
        )
    )

    assert payload["status"] == "blocked"
    assert payload["blocked"] is True
    assert any("--execution-enabled" in reason for reason in payload["blocked_reasons"])
    assert any("--allow-low-risk-code" in reason for reason in payload["blocked_reasons"])
    assert payload["codex_execution_performed"] is False
    assert payload["github_execution_performed"] is False
    assert payload["patch_application_performed"] is False


def test_real_low_risk_loop_executes_mocked_codex_and_validation(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)

    def fake_codex_runner(command, **kwargs):  # type: ignore[no-untyped-def]
        stdout = """# Codex Loop Real Run Result

**Files Changed**
- src/aresforge/low_risk_widget.py

**What Changed**
- Implemented a mocked low-risk code change.

**Tests Run And Results**
- python -m pytest tests/test_cli.py -> passed

**Smoke Checks Run And Results**
- python -m aresforge run-end-to-end-codex-loop --item-id m152-end-to-end-codex-loop-real-run-for-low-risk-code --dry-run --format json -> passed

**Warnings Or Blockers**
- No blockers.

**Commit Hash**
- uncommitted-local-real-run
"""
        return subprocess.CompletedProcess(command, 0, stdout=stdout.encode("utf-8"), stderr=b"")

    def fake_validation_runner(command: str, cwd: Path, timeout_seconds: int) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 0, stdout="passed", stderr="")

    payload = _payload(
        run_end_to_end_codex_loop_dry_run(
            config,
            item_id=ITEM_ID,
            dry_run=False,
            execution_enabled=True,
            allow_low_risk_code=True,
            codex_command=["codex", "exec", "--mock"],
            changed_paths=["src/aresforge/low_risk_widget.py"],
            validation_profile="queue_system",
            output_format="json",
            codex_command_runner=fake_codex_runner,
            validation_command_runner=fake_validation_runner,
        )
    )

    assert payload["record_type"] == "end_to_end_codex_loop_real_low_risk_v1"
    assert payload["status"] == "real_run_validated"
    assert payload["blocked"] is False
    assert payload["machine_gates_passed"] is True
    assert payload["real_execution_allowed"] is True
    assert payload["external_execution_performed"] is True
    assert payload["codex_execution_performed"] is True
    assert payload["validation_command_execution_performed"] is True
    assert payload["github_execution_performed"] is False
    assert payload["patch_application_performed"] is False
    assert payload["queue_mutation_performed"] is False
    assert payload["local_only"] is True
    assert payload["low_risk_code_gate"]["passed"] is True
    assert Path(payload["dispatch_execution_record_path"]).exists()
    assert Path(payload["ingestion_record_path"]).exists()


def test_real_low_risk_loop_blocks_high_risk_changed_path(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)

    payload = _payload(
        run_end_to_end_codex_loop_dry_run(
            config,
            item_id=ITEM_ID,
            dry_run=False,
            execution_enabled=True,
            allow_low_risk_code=True,
            changed_paths=[".github/workflows/ci.yml"],
            output_format="json",
        )
    )

    assert payload["status"] == "blocked"
    assert payload["blocked"] is True
    assert payload["low_risk_code_gate"]["blocked"] is True
    assert any("outside the M152 low-risk code scope" in reason for reason in payload["blocked_reasons"])
    assert payload["codex_execution_performed"] is False
