import json
import subprocess
from pathlib import Path

import pytest

from aresforge.config import AppConfig
from aresforge.operator.codex_dispatch_runner import (
    APPROVAL_PHRASE,
    approve_codex_dispatch,
    inspect_codex_dispatch_run,
    list_codex_dispatch_runs,
    normalize_operator_command,
    parse_codex_cli_token_usage,
    recover_codex_dispatch_run,
    run_operator_gated_codex_dispatch,
)
from aresforge.operator.local_project_queue import add_queue_item, init_project_queue, inspect_queue_item
from aresforge.operator.single_ready_codex_queue_item import run_single_ready_codex_queue_item
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


def _seed_ready_item(config: AppConfig, tmp_path: Path, *, item_id: str = "ready-codex-item", status: str = "ready") -> None:
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
        title=f"{item_id} title",
        description="Ready item with enough execution context.",
        status=status,
        priority="high",
        item_type="feature",
    )["ok"] is True


def _ok_runner(*args, **kwargs):
    return subprocess.CompletedProcess(args=args[0], returncode=0, stdout=b"codex ok\n", stderr=b"")


def _validation_runner(*args, **kwargs):
    return subprocess.CompletedProcess(args=args[0], returncode=0, stdout="validation ok\n", stderr="")


def _git_runner_factory(*, fail_on: str | None = None):
    calls: list[list[str]] = []

    def runner(*args, **kwargs):
        command = list(args[0])
        calls.append(command)
        joined = " ".join(command)
        if fail_on and fail_on in joined:
            return subprocess.CompletedProcess(args=command, returncode=1, stdout="", stderr=f"{joined} failed")
        if command[:2] == ["git", "status"]:
            return subprocess.CompletedProcess(args=command, returncode=0, stdout=" M src/example.py\n", stderr="")
        if command[:2] == ["git", "rev-parse"]:
            return subprocess.CompletedProcess(args=command, returncode=0, stdout=f"commit-{len(calls)}\n", stderr="")
        return subprocess.CompletedProcess(args=command, returncode=0, stdout="ok\n", stderr="")

    runner.calls = calls
    return runner


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


def test_recover_codex_dispatch_run_marks_active_run_failed_without_queue_completion(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_project_and_item(config, tmp_path)
    approve_codex_dispatch(
        config,
        item_id="m78-item",
        approved_by="local_operator",
        approval_phrase=APPROVAL_PHRASE,
        run_id="run-one",
    )

    result = recover_codex_dispatch_run(
        config,
        run_id="run-one",
        recovery_note="operator recovered stale approved run",
    )
    inspected = inspect_codex_dispatch_run(config, run_id="run-one")
    queue_item = inspect_queue_item(config, item_id="m78-item")["payload"]["item"]

    assert result["ok"] is True
    assert result["payload"]["dispatch_state"] == "failed"
    assert result["payload"]["recovery_required"] is True
    assert result["payload"]["queue_completion_allowed"] is False
    assert result["payload"]["automatic_next_item_execution_allowed"] is False
    assert result["payload"]["recovery"]["previous_dispatch_state"] == "approved_pending_dispatch"
    assert inspected["payload"]["run_state_validation"]["valid"] is True
    assert queue_item["status"] == "in_progress"


def test_operator_command_string_uses_windows_argv_rules(monkeypatch: pytest.MonkeyPatch) -> None:
    from aresforge.operator import codex_dispatch_runner

    monkeypatch.setattr(codex_dispatch_runner.os, "name", "nt")

    args = normalize_operator_command(
        '"C:\\Program Files\\Codex\\codex.exe" --cd "C:\\Projects\\aresforge" --flag "two words"'
    )

    assert args == [
        "C:\\Program Files\\Codex\\codex.exe",
        "--cd",
        "C:\\Projects\\aresforge",
        "--flag",
        "two words",
    ]


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


def test_codex_token_usage_parser_extracts_comma_separated_footer() -> None:
    usage = parse_codex_cli_token_usage("work output\n\ntokens used\n221,534\nfinal message\n")

    assert usage == {
        "available": True,
        "source": "codex_cli_transcript_footer",
        "total_tokens": 221534,
        "raw": "tokens used\n221,534",
        "prompt_tokens": None,
        "completion_tokens": None,
        "reasoning_tokens": None,
        "model": None,
        "provider": None,
        "reasoning_effort": None,
    }


def test_codex_token_usage_parser_tolerates_extra_whitespace() -> None:
    usage = parse_codex_cli_token_usage(
        "before\r\n  tokens used  \r\n   221,534   \r\n",
        model="gpt-5-codex",
        provider="openai",
        reasoning_effort="medium",
    )

    assert usage["available"] is True
    assert usage["total_tokens"] == 221534
    assert usage["raw"] == "tokens used\n221,534"
    assert usage["model"] == "gpt-5-codex"
    assert usage["provider"] == "openai"
    assert usage["reasoning_effort"] == "medium"


def test_codex_token_usage_parser_reports_missing_footer() -> None:
    usage = parse_codex_cli_token_usage("codex output without accounting footer\n")

    assert usage["available"] is False
    assert usage["source"] == ""
    assert usage["total_tokens"] is None
    assert usage["raw"] == ""
    assert "tokens used" in usage["extraction_error"]


def test_codex_token_usage_parser_reports_malformed_footer() -> None:
    usage = parse_codex_cli_token_usage("codex output\ntokens used\n22x,534\n")

    assert usage["available"] is False
    assert usage["source"] == ""
    assert usage["total_tokens"] is None
    assert usage["raw"] == "tokens used\n22x,534"
    assert "malformed" in usage["extraction_error"]


def test_successful_dispatch_stores_token_usage_from_stdout_footer(tmp_path: Path) -> None:
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
        return subprocess.CompletedProcess(args=args[0], returncode=0, stdout=b"codex ok\n\ntokens used\n221,534\n", stderr=b"")

    result = run_operator_gated_codex_dispatch(
        config,
        item_id="m78-item",
        run_id="run-one",
        command=["codex", "--fake"],
        command_runner=fake_runner,
    )
    state = json.loads((tmp_path / ".aresforge" / "codex_dispatch" / "runs" / "run-one" / "run_state.json").read_text())
    inspected = inspect_codex_dispatch_run(config, run_id="run-one")

    assert result["ok"] is True
    assert result["payload"]["token_usage"]["available"] is True
    assert result["payload"]["token_usage"]["total_tokens"] == 221534
    assert state["token_usage"]["source"] == "codex_cli_transcript_footer"
    assert inspected["payload"]["token_usage"]["total_tokens"] == 221534


def test_dispatch_stores_unavailable_token_usage_when_footer_missing(tmp_path: Path) -> None:
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
        command=["codex", "--fake"],
        command_runner=_ok_runner,
    )

    assert result["ok"] is True
    assert result["payload"]["token_usage"]["available"] is False
    assert result["payload"]["token_usage"]["total_tokens"] is None
    assert "tokens used" in result["payload"]["token_usage"]["extraction_error"]


def test_dispatch_stores_unavailable_token_usage_when_footer_is_malformed(tmp_path: Path) -> None:
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
        return subprocess.CompletedProcess(args=args[0], returncode=0, stdout=b"codex ok\ntokens used\n221,abc\n", stderr=b"")

    result = run_operator_gated_codex_dispatch(
        config,
        item_id="m78-item",
        run_id="run-one",
        command=["codex", "--fake"],
        command_runner=fake_runner,
    )

    assert result["ok"] is True
    assert result["payload"]["token_usage"]["available"] is False
    assert result["payload"]["token_usage"]["raw"] == "tokens used\n221,abc"
    assert "malformed" in result["payload"]["token_usage"]["extraction_error"]


def test_inspect_old_run_state_without_token_usage_remains_valid(tmp_path: Path) -> None:
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
    old_state = dict(approve["payload"])
    old_state.pop("ok", None)
    old_state.pop("token_usage", None)
    state_path.write_text(json.dumps(old_state, indent=2) + "\n", encoding="utf-8")

    inspected = inspect_codex_dispatch_run(config, run_id="run-one")

    assert inspected["ok"] is True
    assert inspected["payload"]["run_state_validation"]["valid"] is True
    assert inspected["payload"]["token_usage"]["available"] is False
    assert "predate M79.3" in inspected["payload"]["token_usage"]["extraction_error"]


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


def test_single_ready_codex_workflow_zero_ready_items_fails_safely(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_ready_item(config, tmp_path, status="proposed")

    result = run_single_ready_codex_queue_item(
        config,
        approval_phrase=APPROVAL_PHRASE,
        command=["codex", "--fake"],
        validation_commands=["git diff --check"],
    )

    assert result["ok"] is False
    assert result["payload"]["workflow_state"] == "selection_failed"
    assert result["payload"]["next_item_started"] is False
    assert any("No ready/startable" in blocker for blocker in result["payload"]["blockers"])


def test_single_ready_codex_workflow_multiple_ready_items_requires_explicit_item_id(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_ready_item(config, tmp_path, item_id="ready-one")
    assert add_queue_item(
        config,
        item_id="ready-two",
        project_id="aresforge",
        repo_id="aresforge-main",
        title="Ready two",
        description="Second ready item.",
        status="ready",
    )["ok"] is True

    result = run_single_ready_codex_queue_item(
        config,
        approval_phrase=APPROVAL_PHRASE,
        command=["codex", "--fake"],
        validation_commands=["git diff --check"],
    )

    assert result["ok"] is False
    assert result["payload"]["workflow_state"] == "selection_failed"
    assert result["payload"]["selection"]["ready_item_ids"] == ["ready-one", "ready-two"]


def test_single_ready_codex_workflow_explicit_item_processes_only_that_item(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_ready_item(config, tmp_path, item_id="target-ready")
    assert add_queue_item(
        config,
        item_id="other-ready",
        project_id="aresforge",
        repo_id="aresforge-main",
        title="Other ready",
        description="Should remain ready.",
        status="ready",
    )["ok"] is True
    git_runner = _git_runner_factory()

    result = run_single_ready_codex_queue_item(
        config,
        item_id="target-ready",
        approval_phrase=APPROVAL_PHRASE,
        run_id="single-run",
        command=["codex", "--fake"],
        validation_commands=["git diff --check"],
        command_runner=_ok_runner,
        validation_runner=_validation_runner,
        git_runner=git_runner,
    )
    target = inspect_queue_item(config, item_id="target-ready")["payload"]["item"]
    other = inspect_queue_item(config, item_id="other-ready")["payload"]["item"]

    assert result["ok"] is True
    assert result["payload"]["workflow_state"] == "completed"
    assert result["payload"]["next_item_started"] is False
    assert result["payload"]["queue_item_status"] == "done"
    assert target["status"] == "done"
    assert other["status"] == "ready"
    assert sum(1 for call in git_runner.calls if call[:2] == ["git", "push"]) == 2


def test_single_ready_codex_workflow_selected_not_ready_fails_safely(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_ready_item(config, tmp_path, item_id="not-ready", status="in_progress")

    result = run_single_ready_codex_queue_item(
        config,
        item_id="not-ready",
        approval_phrase=APPROVAL_PHRASE,
        command=["codex", "--fake"],
        validation_commands=["git diff --check"],
    )

    assert result["ok"] is False
    assert result["payload"]["workflow_state"] == "selection_failed"
    assert any("ready and startable" in blocker for blocker in result["payload"]["selection"]["blockers"])


def test_single_ready_codex_workflow_failed_codex_does_not_complete_item(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_ready_item(config, tmp_path)

    def failed_codex(*args, **kwargs):
        return subprocess.CompletedProcess(args=args[0], returncode=9, stdout=b"", stderr=b"codex failed")

    result = run_single_ready_codex_queue_item(
        config,
        item_id="ready-codex-item",
        approval_phrase=APPROVAL_PHRASE,
        run_id="failed-codex",
        command=["codex", "--fake"],
        validation_commands=["git diff --check"],
        command_runner=failed_codex,
    )
    item = inspect_queue_item(config, item_id="ready-codex-item")["payload"]["item"]

    assert result["ok"] is False
    assert result["payload"]["workflow_state"] == "codex_failed"
    assert item["status"] == "in_progress"
    assert item["completion_evidence"]["push_result"] == "recovery_required"


def test_single_ready_codex_workflow_failed_validation_does_not_complete_item(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_ready_item(config, tmp_path)

    def failed_validation(*args, **kwargs):
        return subprocess.CompletedProcess(args=args[0], returncode=1, stdout="", stderr="tests failed")

    result = run_single_ready_codex_queue_item(
        config,
        item_id="ready-codex-item",
        approval_phrase=APPROVAL_PHRASE,
        run_id="failed-validation",
        command=["codex", "--fake"],
        validation_commands=["python -m pytest tests/test_codex_dispatch_runner.py"],
        command_runner=_ok_runner,
        validation_runner=failed_validation,
    )
    item = inspect_queue_item(config, item_id="ready-codex-item")["payload"]["item"]

    assert result["ok"] is False
    assert result["payload"]["workflow_state"] == "validation_failed"
    assert item["status"] == "in_progress"
    assert item["closed_at"] == ""


def test_single_ready_codex_workflow_commit_push_failure_records_recovery_required(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_ready_item(config, tmp_path)
    git_runner = _git_runner_factory(fail_on="git commit")

    result = run_single_ready_codex_queue_item(
        config,
        item_id="ready-codex-item",
        approval_phrase=APPROVAL_PHRASE,
        run_id="commit-fail",
        command=["codex", "--fake"],
        validation_commands=["git diff --check"],
        command_runner=_ok_runner,
        validation_runner=_validation_runner,
        git_runner=git_runner,
    )
    item = inspect_queue_item(config, item_id="ready-codex-item")["payload"]["item"]

    assert result["ok"] is False
    assert result["payload"]["workflow_state"] == "implementation_commit_push_failed"
    assert result["payload"]["recovery_required"] is True
    assert item["status"] == "in_progress"
    assert item["completion_evidence"]["push_result"].startswith("recovery_required")
