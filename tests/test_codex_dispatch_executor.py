import json
import subprocess
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.codex_dispatch_executor import run_codex_dispatch_executor
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


def _seed(config: AppConfig, *, dependency_done: bool = True, status: str = "ready") -> None:
    assert init_project_queue(config)["ok"] is True
    assert add_queue_item(
        config,
        item_id="m134-local-llm-advisory-execution",
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M134 dependency",
        status="done" if dependency_done else "ready",
        priority="high",
        item_type="feature",
    )["ok"] is True
    assert add_queue_item(
        config,
        item_id="m135-codex-dispatch-executor-v1",
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M135 Codex Dispatch Executor v1",
        description="Execute prepared Codex dispatch artifacts behind machine gates.",
        status=status,
        priority="high",
        item_type="feature",
        tags=["milestone:m135", "codex-dispatch", "machine-gated"],
        dependencies=["m134-local-llm-advisory-execution"],
        notes="Validation commands are available for Codex dispatch executor.",
    )["ok"] is True


def _artifact(config: AppConfig, *, command: list[str] | None = None, item_id: str = "m135-codex-dispatch-executor-v1") -> Path:
    path = config.repo_root / "artifacts" / "manual" / "sample-codex-dispatch.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "artifact_type": "codex_dispatch_artifact",
                "item_id": item_id,
                "local_only": True,
                "execution_allowed": False,
                "execution_performed": False,
                "codex_execution_performed": False,
                "patch_application_performed": False,
                "github_execution_performed": False,
                "queue_mutation_performed": False,
                "codex_command": command or ["codex", "exec", "--stdin"],
                "prompt_text": "Implement only the requested M135 task and report validation evidence.",
                "validation_commands": ["python -m pytest tests/test_codex_dispatch_executor.py"],
                "tests_reported": ["python -m pytest tests/test_codex_dispatch_executor.py -> passed"],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def _payload(result: dict[str, object]) -> dict[str, object]:
    return result["payload"]  # type: ignore[index]


def test_dry_run_records_artifacts_without_execution(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed(config)
    artifact = _artifact(config)
    calls: list[object] = []

    def runner(*args, **kwargs):
        calls.append(args)
        return subprocess.CompletedProcess(args=args[0], returncode=0, stdout=b"should not run", stderr=b"")

    payload = _payload(
        run_codex_dispatch_executor(
            config,
            item_id="m135-codex-dispatch-executor-v1",
            artifact_path=artifact,
            dry_run=True,
            command_runner=runner,
        )
    )

    assert payload["execution_record_type"] == "codex_dispatch_execution_v1"
    assert payload["dry_run"] is True
    assert payload["execution_enabled"] is False
    assert payload["executed"] is False
    assert payload["blocked"] is False
    assert payload["machine_gates_checked"] is True
    assert payload["machine_gates_passed"] is True
    assert payload["codex_execution_performed"] is False
    assert payload["patch_application_performed"] is False
    assert payload["github_execution_performed"] is False
    assert payload["queue_mutation_performed"] is False
    assert Path(str(payload["result_artifact_path"])).exists()
    assert Path(str(payload["stdout_artifact_path"])).read_text(encoding="utf-8").startswith("Dry-run")
    assert calls == []


def test_blocked_by_default_without_execution_enabled(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed(config)
    artifact = _artifact(config)

    payload = _payload(
        run_codex_dispatch_executor(
            config,
            item_id="m135-codex-dispatch-executor-v1",
            artifact_path=artifact,
        )
    )

    assert payload["blocked"] is True
    assert payload["executed"] is False
    assert payload["codex_execution_performed"] is False
    assert any("--execution-enabled" in reason for reason in payload["blocked_reasons"])


def test_machine_gate_failure_blocks_execution(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed(config, dependency_done=False)
    artifact = _artifact(config)

    payload = _payload(
        run_codex_dispatch_executor(
            config,
            item_id="m135-codex-dispatch-executor-v1",
            artifact_path=artifact,
            dry_run=True,
        )
    )

    assert payload["blocked"] is True
    assert payload["machine_gates_passed"] is False
    assert any("codex_dispatch did not pass" in reason for reason in payload["blocked_reasons"])


def test_mocked_execution_captures_stdout_stderr_and_exit_code(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed(config)
    artifact = _artifact(config, command=["codex", "--fake"])
    seen: dict[str, object] = {}

    def runner(*args, **kwargs):
        seen["command"] = args[0]
        seen["input"] = kwargs["input"]
        return subprocess.CompletedProcess(args=args[0], returncode=0, stdout=b"codex ok\n", stderr=b"note\n")

    payload = _payload(
        run_codex_dispatch_executor(
            config,
            item_id="m135-codex-dispatch-executor-v1",
            artifact_path=artifact,
            execution_enabled=True,
            command_runner=runner,
        )
    )

    assert payload["executed"] is True
    assert payload["blocked"] is False
    assert payload["exit_code"] == 0
    assert payload["command_invoked"] == ["codex", "--fake"]
    assert seen["input"] == b"Implement only the requested M135 task and report validation evidence.\n"
    assert Path(str(payload["stdout_artifact_path"])).read_text(encoding="utf-8") == "codex ok\n"
    assert Path(str(payload["stderr_artifact_path"])).read_text(encoding="utf-8") == "note\n"
    written = json.loads(Path(str(payload["result_artifact_path"])).read_text(encoding="utf-8"))
    assert written["codex_execution_performed"] is True


def test_output_path_is_recorded_and_not_overwritten_without_force(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed(config)
    artifact = _artifact(config)
    output = tmp_path / "artifacts" / "codex_dispatch" / "executions" / "m135.json"

    first = _payload(
        run_codex_dispatch_executor(
            config,
            item_id="m135-codex-dispatch-executor-v1",
            artifact_path=artifact,
            dry_run=True,
            output=output,
        )
    )
    duplicate = _payload(
        run_codex_dispatch_executor(
            config,
            item_id="m135-codex-dispatch-executor-v1",
            artifact_path=artifact,
            dry_run=True,
            output=output,
        )
    )

    assert first["blocked"] is False
    assert first["result_artifact_path"] == str(output)
    assert duplicate["blocked"] is True
    assert any("already exists" in reason for reason in duplicate["blocked_reasons"])
