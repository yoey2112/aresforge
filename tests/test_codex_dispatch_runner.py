import json
import subprocess
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.codex_dispatch_runner import (
    APPROVAL_PHRASE,
    approve_codex_dispatch,
    inspect_codex_dispatch_run,
    list_codex_dispatch_runs,
    run_operator_gated_codex_dispatch,
)
from aresforge.operator.local_project_queue import add_queue_item, init_project_queue, inspect_queue_item
from aresforge.operator.managed_project_registry_local import (
    init_managed_project_registry,
    register_managed_project,
    register_managed_repo,
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


def _seed_project_and_item(config: AppConfig, tmp_path: Path, *, item_id: str = "m78-item") -> None:
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
        item_id=item_id,
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M78",
        description="Prototype one explicitly approved dispatch.",
        status="in_progress",
        priority="high",
        item_type="feature",
    )["ok"] is True


def test_dispatch_requires_operator_approval_before_run(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_project_and_item(config, tmp_path)

    result = run_operator_gated_codex_dispatch(
        config,
        item_id="m78-item",
        run_id="missing-run",
        command=["python", "-c", "print('no approval')"],
    )

    assert result["ok"] is False
    assert result["payload"]["error"] == "codex_dispatch_run_not_found"


def test_approval_record_is_local_only_and_under_codex_dispatch_runs(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_project_and_item(config, tmp_path)

    result = approve_codex_dispatch(
        config,
        item_id="m78-item",
        approved_by="local_operator",
        approval_phrase=APPROVAL_PHRASE,
        run_id="run-one",
    )

    assert result["ok"] is True
    payload = result["payload"]
    assert payload["operator_approval_status"] == "approved"
    assert payload["dispatch_state"] == "approved_pending_dispatch"
    assert payload["queue_completion_allowed"] is False
    assert str(tmp_path / ".aresforge" / "codex_dispatch" / "runs" / "run-one") in payload["stdout_path"]
    assert (tmp_path / ".aresforge" / "codex_dispatch" / "runs" / "run-one" / "run_state.json").exists()
    assert (tmp_path / ".aresforge" / "codex_dispatch" / "runs" / "run-one" / "prompt.txt").exists()


def test_approval_phrase_is_required(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_project_and_item(config, tmp_path)

    result = approve_codex_dispatch(
        config,
        item_id="m78-item",
        approved_by="local_operator",
        approval_phrase="yes please",
        run_id="run-one",
    )

    assert result["ok"] is False
    assert result["payload"]["error"] == "operator_approval_rejected"
    assert not (tmp_path / ".aresforge" / "codex_dispatch" / "runs" / "run-one").exists()


def test_only_one_active_dispatch_run_is_allowed(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_project_and_item(config, tmp_path)

    first = approve_codex_dispatch(
        config,
        item_id="m78-item",
        approved_by="local_operator",
        approval_phrase=APPROVAL_PHRASE,
        run_id="run-one",
    )
    second = approve_codex_dispatch(
        config,
        item_id="m78-item",
        approved_by="local_operator",
        approval_phrase=APPROVAL_PHRASE,
        run_id="run-two",
    )

    assert first["ok"] is True
    assert second["ok"] is False
    assert second["payload"]["error"] == "active_codex_dispatch_run_exists"


def test_successful_dispatch_captures_stdout_stderr_exit_code_and_requires_review(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_project_and_item(config, tmp_path)
    approve = approve_codex_dispatch(
        config,
        item_id="m78-item",
        approved_by="local_operator",
        approval_phrase=APPROVAL_PHRASE,
        run_id="run-one",
    )

    result = run_operator_gated_codex_dispatch(
        config,
        item_id="m78-item",
        run_id=approve["payload"]["run_id"],
        command=["python", "-c", "import sys; print('codex dispatch smoke'); print('stderr smoke', file=sys.stderr)"],
    )
    state = json.loads((tmp_path / ".aresforge" / "codex_dispatch" / "runs" / "run-one" / "run_state.json").read_text())
    queue_item = inspect_queue_item(config, item_id="m78-item")["payload"]["item"]

    assert result["ok"] is True
    assert result["payload"]["dispatch_state"] == "review_required"
    assert result["payload"]["exit_code"] == 0
    assert Path(result["payload"]["stdout_path"]).read_text(encoding="utf-8").strip() == "codex dispatch smoke"
    assert "stderr smoke" in Path(result["payload"]["stderr_path"]).read_text(encoding="utf-8")
    assert state["queue_completion_allowed"] is False
    assert queue_item["status"] == "in_progress"
    assert state["stdin_prompt_handoff"] == "full_prompt_artifact_stdin_utf8"
    assert state["output_decoding"] == "captured_bytes_decoded_as_utf8_sig_with_replacement"


def test_failed_dispatch_records_failed_state_and_error_summary(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_project_and_item(config, tmp_path)
    approve_codex_dispatch(
        config,
        item_id="m78-item",
        approved_by="local_operator",
        approval_phrase=APPROVAL_PHRASE,
        run_id="run-one",
    )

    result = run_operator_gated_codex_dispatch(
        config,
        item_id="m78-item",
        run_id="run-one",
        command=["python", "-c", "import sys; print('boom', file=sys.stderr); sys.exit(7)"],
    )

    assert result["ok"] is False
    assert result["payload"]["dispatch_state"] == "failed"
    assert result["payload"]["exit_code"] == 7
    assert "boom" in result["payload"]["error_summary"]


def test_inspect_and_list_runs_return_stable_json(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_project_and_item(config, tmp_path)
    approve_codex_dispatch(
        config,
        item_id="m78-item",
        approved_by="local_operator",
        approval_phrase=APPROVAL_PHRASE,
        run_id="run-one",
    )

    inspected = inspect_codex_dispatch_run(config, run_id="run-one")
    listed = list_codex_dispatch_runs(config)

    assert inspected["ok"] is True
    assert inspected["payload"]["run_state_validation"]["valid"] is True
    assert listed["ok"] is True
    assert listed["payload"]["run_count"] == 1
    assert listed["payload"]["runs"][0]["run_id"] == "run-one"


def test_injected_runner_does_not_require_codex_cli_installation(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_project_and_item(config, tmp_path)
    approve_codex_dispatch(
        config,
        item_id="m78-item",
        approved_by="local_operator",
        approval_phrase=APPROVAL_PHRASE,
        run_id="run-one",
    )

    def fake_runner(*args, **kwargs):
        return subprocess.CompletedProcess(args=args[0], returncode=0, stdout="fake codex\n", stderr="")

    result = run_operator_gated_codex_dispatch(
        config,
        item_id="m78-item",
        run_id="run-one",
        command=["codex", "--fake"],
        command_runner=fake_runner,
    )

    assert result["ok"] is True
    assert Path(result["payload"]["stdout_path"]).read_text(encoding="utf-8") == "fake codex\n"


def test_dispatch_runner_sends_full_prompt_artifact_to_stdin(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_project_and_item(config, tmp_path)
    prompt_source = tmp_path / ".aresforge" / "codex_dispatch" / "prompts" / "m78-item.prompt.txt"
    prompt_source.parent.mkdir(parents=True, exist_ok=True)
    prompt_source.write_text("first line\nsecond line\nthird line\n", encoding="utf-8")
    approve_codex_dispatch(
        config,
        item_id="m78-item",
        approved_by="local_operator",
        approval_phrase=APPROVAL_PHRASE,
        run_id="run-one",
    )
    seen: dict[str, bytes] = {}

    def fake_runner(*args, **kwargs):
        seen["input"] = kwargs["input"]
        return subprocess.CompletedProcess(args=args[0], returncode=0, stdout=b"ok\n", stderr=b"")

    result = run_operator_gated_codex_dispatch(
        config,
        item_id="m78-item",
        run_id="run-one",
        command=["codex", "--fake"],
        command_runner=fake_runner,
    )

    assert result["ok"] is True
    assert seen["input"].decode("utf-8") == "first line\nsecond line\nthird line\n"
    assert result["payload"]["stdin_prompt_bytes"] == len(seen["input"])
    assert result["payload"]["stdin_prompt_handoff"] == "full_prompt_artifact_stdin_utf8"


def test_dispatch_runner_decodes_non_utf8_output_with_replacement(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_project_and_item(config, tmp_path)
    approve_codex_dispatch(
        config,
        item_id="m78-item",
        approved_by="local_operator",
        approval_phrase=APPROVAL_PHRASE,
        run_id="run-one",
    )

    def fake_runner(*args, **kwargs):
        return subprocess.CompletedProcess(args=args[0], returncode=0, stdout=b"unicode \xe2\x9c\x93 invalid \xff\n", stderr=b"")

    result = run_operator_gated_codex_dispatch(
        config,
        item_id="m78-item",
        run_id="run-one",
        command=["codex", "--fake"],
        command_runner=fake_runner,
    )

    rendered = Path(result["payload"]["stdout_path"]).read_text(encoding="utf-8")
    assert result["ok"] is True
    assert "unicode \u2713 invalid \ufffd" in rendered


def test_run_state_json_reading_accepts_utf8_bom(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_project_and_item(config, tmp_path)
    approve = approve_codex_dispatch(
        config,
        item_id="m78-item",
        approved_by="local_operator",
        approval_phrase=APPROVAL_PHRASE,
        run_id="run-one",
    )
    state_path = tmp_path / ".aresforge" / "codex_dispatch" / "runs" / "run-one" / "run_state.json"
    state_path.write_text(json.dumps(approve["payload"], indent=2) + "\n", encoding="utf-8-sig")

    inspected = inspect_codex_dispatch_run(config, run_id="run-one")

    assert inspected["ok"] is True
    assert inspected["payload"]["run_id"] == "run-one"
