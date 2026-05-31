import json
import subprocess
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.codex_result_ingestion_validation import (
    VALIDATION_PROFILES,
    ingest_codex_result_and_validate,
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


def _seed(config: AppConfig, *, item_id: str = "m136-codex-result-ingestion-and-validation-runner") -> None:
    assert init_project_queue(config)["ok"] is True
    assert add_queue_item(
        config,
        item_id=item_id,
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M136 Codex Result Ingestion and Validation Runner",
        description="Ingest Codex execution records and run local validation.",
        status="in_progress",
        priority="high",
        item_type="feature",
        tags=["milestone:m136", "codex-result-ingestion", "local-only"],
        completion_requires=["tests_run", "smoke_checks", "commit_hash"],
        evidence_required=["dispatch_result_evidence", "validation_results"],
    )["ok"] is True
    transaction_log = config.repo_root / ".aresforge" / "queue" / "transaction_log.json"
    transaction_log.parent.mkdir(parents=True, exist_ok=True)
    transaction_log.write_text(json.dumps({"schema_version": "1.0", "transactions": []}), encoding="utf-8")


def _result_text() -> str:
    return """# Codex Result

**Files Changed**
- src/aresforge/operator/codex_result_ingestion_validation.py
- tests/test_codex_result_ingestion_validation.py

**What Changed**
- Added a local-only Codex result ingestion and validation runner.

**Tests Run And Results**
- python -m pytest tests/test_codex_result_ingestion_validation.py -> passed

**Smoke Checks Run And Results**
- python -m aresforge ingest-codex-result-and-validate --item-id m136-codex-result-ingestion-and-validation-runner --execution-record artifacts/manual/sample-codex-execution-record.json --dry-run --format json -> passed

**Warnings Or Blockers**
- No blockers.

**Commit Hash**
- abc1234
"""


def _execution_record(config: AppConfig, *, item_id: str = "m136-codex-result-ingestion-and-validation-runner") -> Path:
    stdout_path = config.repo_root / "artifacts" / "manual" / "sample-codex-output.md"
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    stdout_path.write_text(_result_text(), encoding="utf-8")
    record_path = config.repo_root / "artifacts" / "manual" / "sample-codex-execution-record.json"
    record_path.write_text(
        json.dumps(
            {
                "execution_record_type": "codex_dispatch_execution_v1",
                "item_id": item_id,
                "dry_run": False,
                "executed": True,
                "exit_code": 0,
                "stdout_artifact_path": str(stdout_path),
                "stderr_artifact_path": "",
                "result_artifact_path": "",
                "changed_files": ["src/aresforge/operator/codex_result_ingestion_validation.py"],
                "commit_hash": "abc1234",
                "local_only": True,
                "github_execution_performed": False,
                "queue_mutation_performed": False,
                "patch_application_performed": False,
                "external_execution_performed": True,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return record_path


def _payload(result: dict[str, object]) -> dict[str, object]:
    return result["payload"]  # type: ignore[index]


def test_dry_run_ingests_fixture_record_without_running_validation(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed(config)
    record_path = _execution_record(config)
    calls: list[str] = []

    def runner(command: str, cwd: Path, timeout_seconds: int) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        return subprocess.CompletedProcess(args=command, returncode=0, stdout="ok", stderr="")

    payload = _payload(
        ingest_codex_result_and_validate(
            config,
            item_id="m136-codex-result-ingestion-and-validation-runner",
            execution_record=record_path,
            validation_profile="full_local_safe",
            dry_run=True,
            command_runner=runner,
        )
    )

    assert payload["ingestion_record_type"] == "codex_result_ingestion_validation"
    assert payload["dry_run"] is True
    assert payload["blocked"] is False
    assert payload["validation_commands"] == list(VALIDATION_PROFILES["full_local_safe"])
    assert all(entry["skipped"] for entry in payload["validation_run"])
    assert payload["validation_passed"] is False
    assert calls == []
    assert Path(payload["evidence_artifact_path"]).exists()
    assert Path(payload["completion_recommendation_path"]).exists()
    assert Path(payload["machine_gate_result_path"]).exists()
    assert payload["queue_mutation_performed"] is False
    assert payload["github_execution_performed"] is False
    assert payload["local_only"] is True


def test_validation_profile_selection_uses_docs_only_allowlist(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed(config)
    record_path = _execution_record(config)

    payload = _payload(
        ingest_codex_result_and_validate(
            config,
            item_id="m136-codex-result-ingestion-and-validation-runner",
            execution_record=record_path,
            validation_profile="docs_only",
            dry_run=True,
        )
    )

    assert payload["validation_profile"] == "docs_only"
    assert payload["validation_commands"] == ["git diff --check"]


def test_mocked_validation_runner_captures_success_output(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed(config)
    record_path = _execution_record(config)
    seen: list[tuple[str, Path, int]] = []

    def runner(command: str, cwd: Path, timeout_seconds: int) -> subprocess.CompletedProcess[str]:
        seen.append((command, cwd, timeout_seconds))
        return subprocess.CompletedProcess(args=command, returncode=0, stdout=f"{command} ok\n", stderr="")

    payload = _payload(
        ingest_codex_result_and_validate(
            config,
            item_id="m136-codex-result-ingestion-and-validation-runner",
            execution_record=record_path,
            validation_profile="docs_only",
            command_runner=runner,
            timeout_seconds=12,
        )
    )

    assert payload["blocked"] is False
    assert payload["validation_passed"] is True
    assert payload["validation_run"][0]["stdout"] == "git diff --check ok\n"
    assert seen == [("git diff --check", config.repo_root, 12)]
    assert payload["completion_recommendation"]["recommended_complete"] is True


def test_validation_failure_blocks_completion_handoff(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed(config)
    record_path = _execution_record(config)

    def runner(command: str, cwd: Path, timeout_seconds: int) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args=command, returncode=1, stdout="", stderr="failed\n")

    payload = _payload(
        ingest_codex_result_and_validate(
            config,
            item_id="m136-codex-result-ingestion-and-validation-runner",
            execution_record=record_path,
            validation_profile="docs_only",
            command_runner=runner,
        )
    )

    assert payload["blocked"] is True
    assert payload["validation_passed"] is False
    assert payload["validation_run"][0]["stderr"] == "failed\n"
    assert any("Validation command failed: git diff --check" in reason for reason in payload["blocked_reasons"])


def test_missing_execution_record_blocks_without_crashing(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed(config)

    payload = _payload(
        ingest_codex_result_and_validate(
            config,
            item_id="m136-codex-result-ingestion-and-validation-runner",
            execution_record=config.repo_root / "artifacts" / "manual" / "missing.json",
            validation_profile="docs_only",
            dry_run=True,
        )
    )

    assert payload["blocked"] is True
    assert any("Execution record is missing" in reason for reason in payload["blocked_reasons"])
