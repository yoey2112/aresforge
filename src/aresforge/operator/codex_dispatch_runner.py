from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Sequence

from aresforge.config import AppConfig
from aresforge.operator.codex_dispatch_contract import (
    RUNS_DIR_RELATIVE,
    build_codex_dispatch_contract,
)

APPROVAL_PHRASE = "APPROVE CODEX DISPATCH"
RUN_STATE_FILE_NAME = "run_state.json"
ACTIVE_DISPATCH_STATES = frozenset({"approved_pending_dispatch", "running"})
ALLOWED_DISPATCH_STATES = (
    "awaiting_operator_approval",
    "approved_pending_dispatch",
    "running",
    "completed",
    "failed",
    "cancelled",
    "review_required",
)
TOKEN_USAGE_SOURCE = "codex_cli_transcript_footer"

CommandRunner = Callable[..., subprocess.CompletedProcess[Any]]

_BOUNDARY_CONFIRMATIONS = (
    "M78 Codex dispatch is local-only and operator-gated.",
    "Only one active dispatch run is allowed at a time.",
    "No automatic next-item execution is allowed.",
    "No queue item status is mutated by Codex dispatch.",
    "Codex output cannot automatically mark queue items complete.",
    "Review evidence is required after dispatch.",
    "Validation evidence is required before queue completion.",
    "No local LLM execution expansion is added.",
    "Local LLM remains local-only, advisory-only, operator-gated, prototype-scoped, and non-mutating.",
    "No GitHub API calls.",
    "No gh calls.",
    "No GitHub issues, PRs, workflows, or GitHub mutation.",
    "No external workflow execution.",
)


def approve_codex_dispatch(
    config: AppConfig,
    *,
    item_id: str,
    approved_by: str,
    approval_phrase: str,
    queue_path: str | Path | None = None,
    registry_path: str | Path | None = None,
    run_id: str | None = None,
    output_format: str = "json",
) -> dict[str, Any]:
    normalized_item_id = str(item_id or "").strip()
    normalized_approved_by = str(approved_by or "").strip()
    normalized_phrase = str(approval_phrase or "").strip()
    normalized_run_id = _safe_path_token(run_id or f"{normalized_item_id}-{_timestamp_token()}")

    if normalized_phrase != APPROVAL_PHRASE:
        return _stdout_result(
            "approve-codex-dispatch",
            _error_payload(
                "operator_approval_rejected",
                {
                    "item_id": normalized_item_id,
                    "required_approval_phrase": APPROVAL_PHRASE,
                    "message": "Explicit operator approval phrase is required before Codex dispatch.",
                },
            ),
            output_format,
        )
    if not normalized_approved_by:
        return _stdout_result(
            "approve-codex-dispatch",
            _error_payload(
                "operator_approval_missing_actor",
                {"item_id": normalized_item_id, "message": "--approved-by is required."},
            ),
            output_format,
        )

    active = _inspect_active_runs(config.repo_root)
    if active["active"]:
        return _stdout_result(
            "approve-codex-dispatch",
            _error_payload(
                "active_codex_dispatch_run_exists",
                {
                    "item_id": normalized_item_id,
                    "active_runs": active["active_runs"],
                    "message": "Another Codex dispatch run is already active.",
                },
            ),
            output_format,
        )

    contract = build_codex_dispatch_contract(
        config,
        item_id=normalized_item_id,
        queue_path=queue_path,
        registry_path=registry_path,
    )
    blockers = list(contract.get("blockers", [])) if isinstance(contract.get("blockers"), list) else []
    if not bool(contract.get("ok", False)) or blockers:
        return _stdout_result(
            "approve-codex-dispatch",
            _error_payload(
                "codex_dispatch_contract_not_ready",
                {
                    "item_id": normalized_item_id,
                    "contract_ok": bool(contract.get("ok", False)),
                    "blockers": blockers,
                    "message": "Codex dispatch approval requires a ready local dispatch contract.",
                },
            ),
            output_format,
        )

    paths = _run_paths(config.repo_root, normalized_run_id)
    if paths["run_dir"].exists():
        return _stdout_result(
            "approve-codex-dispatch",
            _error_payload(
                "codex_dispatch_run_already_exists",
                {"run_id": normalized_run_id, "run_dir": str(paths["run_dir"])},
            ),
            output_format,
        )

    paths["artifact_dir"].mkdir(parents=True, exist_ok=False)
    state = _new_run_state(
        contract=contract,
        run_id=normalized_run_id,
        approved_by=normalized_approved_by,
        approval_phrase=normalized_phrase,
        dispatch_state="approved_pending_dispatch",
        paths=paths,
    )
    paths["prompt_path"].parent.mkdir(parents=True, exist_ok=True)
    paths["prompt_path"].write_text(_prompt_artifact_text(config.repo_root, contract), encoding="utf-8")
    _write_run_state(paths["run_state_path"], state)
    return _stdout_result("approve-codex-dispatch", {"ok": True, **state}, output_format)


def run_operator_gated_codex_dispatch(
    config: AppConfig,
    *,
    item_id: str,
    run_id: str,
    command: str | Sequence[str] | None = None,
    timeout_seconds: int = 300,
    command_runner: CommandRunner | None = None,
    output_format: str = "json",
) -> dict[str, Any]:
    normalized_run_id = _safe_path_token(run_id)
    paths = _run_paths(config.repo_root, normalized_run_id)
    loaded = _load_run_state(paths["run_state_path"])
    if not loaded.get("ok", False):
        return _stdout_result("run-codex-dispatch", loaded, output_format)
    state = loaded["run_state"]
    normalized_item_id = str(item_id or "").strip()
    if str(state.get("item_id", "")).strip() != normalized_item_id:
        return _stdout_result(
            "run-codex-dispatch",
            _error_payload(
                "codex_dispatch_item_mismatch",
                {"run_id": normalized_run_id, "item_id": normalized_item_id, "run_item_id": state.get("item_id", "")},
            ),
            output_format,
        )
    if str(state.get("dispatch_state", "")).strip() != "approved_pending_dispatch":
        return _stdout_result(
            "run-codex-dispatch",
            _error_payload(
                "codex_dispatch_not_approved_pending_dispatch",
                {"run_id": normalized_run_id, "dispatch_state": state.get("dispatch_state", "")},
            ),
            output_format,
        )

    active = _inspect_active_runs(config.repo_root, exclude_run_id=normalized_run_id)
    if active["active"]:
        return _stdout_result(
            "run-codex-dispatch",
            _error_payload(
                "active_codex_dispatch_run_exists",
                {"run_id": normalized_run_id, "active_runs": active["active_runs"]},
            ),
            output_format,
        )

    try:
        command_args = normalize_operator_command(command)
    except ValueError as exc:
        return _stdout_result(
            "run-codex-dispatch",
            _error_payload(
                "codex_dispatch_command_invalid",
                {"run_id": normalized_run_id, "message": str(exc)},
            ),
            output_format,
        )
    if not command_args:
        return _stdout_result(
            "run-codex-dispatch",
            _error_payload(
                "codex_dispatch_command_required",
                {
                    "run_id": normalized_run_id,
                    "message": "M78 requires an explicit operator-provided --command for dispatch.",
                },
            ),
            output_format,
        )

    started_at = _now_iso()
    prompt_input = _read_prompt_input(paths["prompt_path"])
    state.update(
        {
            "dispatch_state": "running",
            "started_at": started_at,
            "codex_cli_invocation_allowed": True,
            "codex_cli_invoked": True,
            "codex_cli_command": command_args,
            "stdin_prompt_path": str(paths["prompt_path"]),
            "stdin_prompt_bytes": len(prompt_input.encode("utf-8")),
            "stdin_prompt_handoff": "full_prompt_artifact_stdin_utf8",
            "output_decoding": "captured_bytes_decoded_as_utf8_sig_with_replacement",
            "next_safe_action": "Wait for dispatch completion, then inspect captured stdout/stderr and review evidence.",
        }
    )
    _write_run_state(paths["run_state_path"], state)

    runner = command_runner or subprocess.run
    try:
        completed = runner(
            command_args,
            cwd=str(Path(state["working_directory"]).resolve()),
            check=False,
            capture_output=True,
            input=prompt_input.encode("utf-8"),
            timeout=max(1, int(timeout_seconds)),
            shell=False,
        )
        stdout = _decode_process_output(completed.stdout)
        stderr = _decode_process_output(completed.stderr)
        exit_code = int(completed.returncode)
        error_summary = "" if exit_code == 0 else (stderr.strip() or f"Command exited with code {exit_code}.")
        final_state = "review_required" if exit_code == 0 else "failed"
    except (OSError, subprocess.SubprocessError) as exc:
        stdout = ""
        stderr = str(exc)
        exit_code = None
        error_summary = str(exc)
        final_state = "failed"

    paths["stdout_path"].write_text(stdout, encoding="utf-8")
    paths["stderr_path"].write_text(stderr, encoding="utf-8")
    token_usage = parse_codex_cli_token_usage(
        _codex_cli_transcript_text(stdout=stdout, stderr=stderr),
        model=state.get("model") or state.get("codex_model"),
        provider=state.get("provider") or state.get("codex_provider"),
        reasoning_effort=state.get("reasoning_effort") or state.get("codex_reasoning_effort"),
    )
    state.update(
        {
            "dispatch_state": final_state,
            "completed_at": _now_iso(),
            "stdout_path": str(paths["stdout_path"]),
            "stderr_path": str(paths["stderr_path"]),
            "exit_code": exit_code,
            "error_summary": error_summary,
            "token_usage": token_usage,
            "review_required": True,
            "review_evidence_required": True,
            "validation_evidence_required": True,
            "queue_completion_allowed": False,
            "automatic_next_item_execution_allowed": False,
            "next_safe_action": (
                "Review captured Codex output and run local validation before queue completion."
                if final_state == "review_required"
                else "Inspect stderr/error summary, fix or cancel explicitly, and do not advance the queue automatically."
            ),
        }
    )
    _write_run_state(paths["run_state_path"], state)
    return _stdout_result("run-codex-dispatch", {"ok": final_state == "review_required", **state}, output_format)


def inspect_codex_dispatch_run(
    config: AppConfig,
    *,
    run_id: str,
    output_format: str = "json",
) -> dict[str, Any]:
    paths = _run_paths(config.repo_root, _safe_path_token(run_id))
    loaded = _load_run_state(paths["run_state_path"])
    if not loaded.get("ok", False):
        return _stdout_result("inspect-codex-dispatch-run", loaded, output_format)
    run_state = dict(loaded["run_state"])
    if "token_usage" not in run_state:
        run_state["token_usage"] = unavailable_token_usage(
            "token_usage field is not present in this run_state.json; it may predate M79.3."
        )
    validation = validate_codex_dispatch_run_state(run_state, repo_root=config.repo_root)
    return _stdout_result(
        "inspect-codex-dispatch-run",
        {"ok": validation["valid"], **run_state, "run_state_validation": validation},
        output_format,
    )


def list_codex_dispatch_runs(config: AppConfig, *, output_format: str = "json") -> dict[str, Any]:
    runs_root = (config.repo_root / RUNS_DIR_RELATIVE).resolve()
    runs: list[dict[str, Any]] = []
    if runs_root.exists():
        for path in sorted(runs_root.glob(f"*/{RUN_STATE_FILE_NAME}")):
            loaded = _load_run_state(path)
            if loaded.get("ok", False):
                state = loaded["run_state"]
                runs.append(
                    {
                        "run_id": state.get("run_id", ""),
                        "item_id": state.get("item_id", ""),
                        "dispatch_state": state.get("dispatch_state", ""),
                        "created_at": state.get("created_at", ""),
                        "started_at": state.get("started_at", ""),
                        "completed_at": state.get("completed_at", ""),
                        "run_state_path": str(path),
                    }
                )
    payload = {
        "ok": True,
        "local_only": True,
        "runs_root": str(runs_root),
        "run_count": len(runs),
        "active_run_count": len([run for run in runs if run["dispatch_state"] in ACTIVE_DISPATCH_STATES]),
        "runs": runs,
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }
    return _stdout_result("list-codex-dispatch-runs", payload, output_format)


def cancel_codex_dispatch_run(
    config: AppConfig,
    *,
    run_id: str,
    output_format: str = "json",
) -> dict[str, Any]:
    paths = _run_paths(config.repo_root, _safe_path_token(run_id))
    loaded = _load_run_state(paths["run_state_path"])
    if not loaded.get("ok", False):
        return _stdout_result("cancel-codex-dispatch-run", loaded, output_format)
    state = loaded["run_state"]
    if str(state.get("dispatch_state", "")) == "running":
        return _stdout_result(
            "cancel-codex-dispatch-run",
            _error_payload(
                "codex_dispatch_running_cancel_not_supported",
                {"run_id": run_id, "message": "M78 cannot terminate a live subprocess after this CLI returns."},
            ),
            output_format,
        )
    state.update(
        {
            "dispatch_state": "cancelled",
            "cancelled_at": _now_iso(),
            "next_safe_action": "Inspect or create a fresh approved run; no queue item was advanced automatically.",
        }
    )
    _write_run_state(paths["run_state_path"], state)
    return _stdout_result("cancel-codex-dispatch-run", {"ok": True, **state}, output_format)


def recover_codex_dispatch_run(
    config: AppConfig,
    *,
    run_id: str,
    recovery_note: str = "",
    output_format: str = "json",
) -> dict[str, Any]:
    normalized_run_id = _safe_path_token(run_id)
    paths = _run_paths(config.repo_root, normalized_run_id)
    loaded = _load_run_state(paths["run_state_path"])
    if not loaded.get("ok", False):
        return _stdout_result("recover-codex-dispatch-run", loaded, output_format)

    state = loaded["run_state"]
    previous_state = str(state.get("dispatch_state", "")).strip()
    normalized_note = str(recovery_note or "").strip()
    recovered_at = _now_iso()
    if previous_state in ACTIVE_DISPATCH_STATES:
        state["dispatch_state"] = "failed"
    state.update(
        {
            "completed_at": str(state.get("completed_at") or recovered_at),
            "error_summary": str(state.get("error_summary") or "Dispatch recovery marked this run for operator review.").strip(),
            "recovery_required": True,
            "recovery": {
                "recovered_at": recovered_at,
                "previous_dispatch_state": previous_state,
                "recovery_note": normalized_note,
                "recovered_by_command": "recover-codex-dispatch-run",
            },
            "review_required": True,
            "review_evidence_required": True,
            "validation_evidence_required": True,
            "queue_completion_allowed": False,
            "automatic_next_item_execution_allowed": False,
            "next_safe_action": (
                "Review recovered run output/state, capture validation evidence separately, "
                "and do not advance the queue automatically."
            ),
        }
    )
    _write_run_state(paths["run_state_path"], state)
    return _stdout_result("recover-codex-dispatch-run", {"ok": True, **state}, output_format)


def validate_codex_dispatch_run_state(run_state: dict[str, Any], *, repo_root: Path) -> dict[str, Any]:
    required = [
        "run_id",
        "item_id",
        "project_id",
        "repo_id",
        "dispatch_state",
        "created_at",
        "approved_at",
        "approved_by",
        "approval_token_or_phrase",
        "operator_approval_required",
        "operator_approval_status",
        "one_item_at_a_time_required",
        "automatic_next_item_execution_allowed",
        "codex_cli_invocation_allowed",
        "codex_cli_invoked",
        "codex_cli_command",
        "working_directory",
        "prompt_artifact_path",
        "stdout_path",
        "stderr_path",
        "artifact_dir",
        "exit_code",
        "error_summary",
        "stdin_prompt_path",
        "stdin_prompt_bytes",
        "stdin_prompt_handoff",
        "output_decoding",
        "review_required",
        "review_evidence_required",
        "validation_evidence_required",
        "queue_completion_allowed",
        "next_safe_action",
        "boundary_confirmations",
    ]
    missing = [field for field in required if field not in run_state]
    blockers: list[str] = []
    if run_state.get("dispatch_state") not in ALLOWED_DISPATCH_STATES:
        blockers.append("dispatch_state is not allowed.")
    if run_state.get("operator_approval_required") is not True:
        blockers.append("operator_approval_required must be true.")
    if run_state.get("one_item_at_a_time_required") is not True:
        blockers.append("one_item_at_a_time_required must be true.")
    if run_state.get("automatic_next_item_execution_allowed") is not False:
        blockers.append("automatic_next_item_execution_allowed must be false.")
    if run_state.get("queue_completion_allowed") is not False:
        blockers.append("queue_completion_allowed must be false for dispatch output.")
    token_usage = run_state.get("token_usage")
    if token_usage is not None and not isinstance(token_usage, dict):
        blockers.append("token_usage must be an object when present.")
    root = repo_root.resolve()
    for key in ("prompt_artifact_path", "stdout_path", "stderr_path", "artifact_dir"):
        value = str(run_state.get(key, "")).strip()
        if not value:
            continue
        try:
            Path(value).resolve().relative_to(root)
        except ValueError:
            blockers.append(f"{key} must stay inside the repository root.")
    return {"valid": not missing and not blockers, "missing_fields": missing, "blockers": blockers}


def parse_codex_cli_token_usage(
    transcript_text: str,
    *,
    model: Any | None = None,
    provider: Any | None = None,
    reasoning_effort: Any | None = None,
) -> dict[str, Any]:
    lines = str(transcript_text or "").splitlines()
    marker_index: int | None = None
    for index, line in enumerate(lines):
        if line.strip().lower() == "tokens used":
            marker_index = index
    if marker_index is None:
        return unavailable_token_usage('Codex CLI token usage footer "tokens used" was not found.')

    value_line = ""
    for line in lines[marker_index + 1 :]:
        if line.strip():
            value_line = line
            break
    raw = f"{lines[marker_index].strip()}\n{value_line.strip()}" if value_line else lines[marker_index].strip()
    if not value_line:
        return unavailable_token_usage("Codex CLI token usage footer did not include a numeric line.", raw=raw)

    normalized_value = value_line.strip()
    if not re.fullmatch(r"\d[\d,]*", normalized_value):
        return unavailable_token_usage(
            f"Codex CLI token usage value is malformed: {normalized_value}",
            raw=raw,
        )

    return {
        "available": True,
        "source": TOKEN_USAGE_SOURCE,
        "total_tokens": int(normalized_value.replace(",", "")),
        "raw": raw,
        "prompt_tokens": None,
        "completion_tokens": None,
        "reasoning_tokens": None,
        "model": _optional_metadata_value(model),
        "provider": _optional_metadata_value(provider),
        "reasoning_effort": _optional_metadata_value(reasoning_effort),
    }


def unavailable_token_usage(extraction_error: str, *, raw: str = "") -> dict[str, Any]:
    return {
        "available": False,
        "source": "",
        "total_tokens": None,
        "raw": raw,
        "extraction_error": extraction_error,
    }


def _new_run_state(
    *,
    contract: dict[str, Any],
    run_id: str,
    approved_by: str,
    approval_phrase: str,
    dispatch_state: str,
    paths: dict[str, Path],
) -> dict[str, Any]:
    now = _now_iso()
    return {
        "run_id": run_id,
        "item_id": str(contract.get("item_id", "")).strip(),
        "project_id": str(contract.get("project_id", "")).strip(),
        "repo_id": str(contract.get("repo_id", "")).strip(),
        "dispatch_state": dispatch_state,
        "created_at": now,
        "approved_at": now,
        "started_at": "",
        "completed_at": "",
        "cancelled_at": "",
        "approved_by": approved_by,
        "approval_token_or_phrase": approval_phrase,
        "operator_approval_required": True,
        "operator_approval_status": "approved",
        "one_item_at_a_time_required": True,
        "automatic_next_item_execution_allowed": False,
        "codex_cli_invocation_allowed": False,
        "codex_cli_invoked": False,
        "codex_cli_command": [],
        "working_directory": str(Path(str(contract.get("working_directory") or paths["run_dir"].parent)).resolve()),
        "prompt_artifact_path": str(paths["prompt_path"]),
        "stdin_prompt_path": str(paths["prompt_path"]),
        "stdin_prompt_bytes": 0,
        "stdin_prompt_handoff": "pending_full_prompt_artifact_stdin_utf8",
        "output_decoding": "captured_bytes_decoded_as_utf8_sig_with_replacement",
        "stdout_path": str(paths["stdout_path"]),
        "stderr_path": str(paths["stderr_path"]),
        "artifact_dir": str(paths["artifact_dir"]),
        "exit_code": None,
        "error_summary": "",
        "token_usage": unavailable_token_usage("Codex dispatch has not completed; token usage has not been captured yet."),
        "review_required": True,
        "review_evidence_required": True,
        "validation_evidence_required": True,
        "review_evidence": [],
        "validation_evidence": [],
        "queue_completion_allowed": False,
        "next_safe_action": "Run the approved dispatch explicitly, or cancel this run. Do not auto-run another item.",
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }


def _inspect_active_runs(repo_root: Path, *, exclude_run_id: str | None = None) -> dict[str, Any]:
    runs_root = (repo_root / RUNS_DIR_RELATIVE).resolve()
    active_runs: list[dict[str, str]] = []
    if runs_root.exists():
        for path in sorted(runs_root.glob(f"*/{RUN_STATE_FILE_NAME}")):
            loaded = _load_run_state(path)
            if not loaded.get("ok", False):
                continue
            state = loaded["run_state"]
            run_id = str(state.get("run_id", "")).strip()
            if exclude_run_id and run_id == exclude_run_id:
                continue
            dispatch_state = str(state.get("dispatch_state", "")).strip()
            if dispatch_state in ACTIVE_DISPATCH_STATES:
                active_runs.append({"run_id": run_id, "item_id": state.get("item_id", ""), "dispatch_state": dispatch_state})
    return {"active": bool(active_runs), "active_runs": active_runs}


def _run_paths(repo_root: Path, run_id: str) -> dict[str, Path]:
    run_dir = (repo_root / RUNS_DIR_RELATIVE / _safe_path_token(run_id)).resolve()
    return {
        "run_dir": run_dir,
        "run_state_path": run_dir / RUN_STATE_FILE_NAME,
        "stdout_path": run_dir / "stdout.txt",
        "stderr_path": run_dir / "stderr.txt",
        "prompt_path": run_dir / "prompt.txt",
        "artifact_dir": run_dir / "artifacts",
    }


def _load_run_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return _error_payload("codex_dispatch_run_not_found", {"run_state_path": str(path)})
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        return _error_payload("codex_dispatch_run_state_invalid", {"run_state_path": str(path), "message": str(exc)})
    if not isinstance(raw, dict):
        return _error_payload("codex_dispatch_run_state_invalid", {"run_state_path": str(path), "message": "Run state must be a JSON object."})
    return {"ok": True, "local_only": True, "run_state": raw}


def _write_run_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def normalize_operator_command(command: str | Sequence[str] | None) -> list[str]:
    if command is None:
        return []
    if isinstance(command, str):
        return _split_operator_command_string(command)
    return [str(part) for part in command if str(part).strip()]


def _split_operator_command_string(command: str) -> list[str]:
    normalized = str(command or "").strip()
    if not normalized:
        return []
    if os.name != "nt":
        return shlex.split(normalized)
    return _windows_command_line_to_argv(normalized)


def _windows_command_line_to_argv(command: str) -> list[str]:
    args: list[str] = []
    current: list[str] = []
    in_quotes = False
    arg_started = False
    index = 0
    length = len(command)
    while index < length:
        char = command[index]
        if char in {" ", "\t"} and not in_quotes:
            if arg_started:
                args.append("".join(current))
                current = []
                arg_started = False
            index += 1
            continue
        if char == "\\":
            slash_start = index
            while index < length and command[index] == "\\":
                index += 1
            slash_count = index - slash_start
            if index < length and command[index] == '"':
                current.extend("\\" * (slash_count // 2))
                if slash_count % 2 == 0:
                    in_quotes = not in_quotes
                    arg_started = True
                else:
                    current.append('"')
                    arg_started = True
                index += 1
            else:
                current.extend("\\" * slash_count)
                arg_started = True
            continue
        if char == '"':
            in_quotes = not in_quotes
            arg_started = True
            index += 1
            continue
        current.append(char)
        arg_started = True
        index += 1
    if in_quotes:
        raise ValueError("Windows command string has an unterminated quote.")
    if arg_started:
        args.append("".join(current))
    return [arg for arg in args if arg]


def _prompt_artifact_text(repo_root: Path, contract: dict[str, Any]) -> str:
    source = Path(str(contract.get("prompt_artifact_path", "")).strip())
    if source:
        try:
            source.resolve().relative_to(repo_root.resolve())
            if source.exists() and source.is_file():
                return source.read_text(encoding="utf-8-sig")
        except (OSError, ValueError):
            pass
    return "\n".join(
        [
            "M78 Operator-Gated Codex Dispatch Prompt Artifact",
            "",
            f"item_id: {contract.get('item_id', '')}",
            f"project_id: {contract.get('project_id', '')}",
            f"repo_id: {contract.get('repo_id', '')}",
            "",
            "Operator boundaries:",
            "- Explicit approval was captured before dispatch.",
            "- One item at a time only.",
            "- No automatic next-item execution.",
            "- Review and validation evidence remain required before queue completion.",
        ]
    ).rstrip() + "\n"


def _read_prompt_input(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except OSError:
        return ""


def _decode_process_output(value: bytes | str | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8-sig", errors="replace")
    return str(value)


def _codex_cli_transcript_text(*, stdout: str, stderr: str) -> str:
    if stdout and stderr:
        return f"{stdout.rstrip()}\n{stderr.lstrip()}"
    return stdout or stderr or ""


def _optional_metadata_value(value: Any | None) -> str | None:
    normalized = str(value or "").strip()
    return normalized or None


def _stdout_result(command: str, payload: dict[str, Any], output_format: str) -> dict[str, Any]:
    fmt = output_format.lower().strip()
    if fmt not in {"json", "markdown"}:
        return _error_payload("invalid_format", {"format": output_format, "supported_formats": ["json", "markdown"]})
    stdout = json.dumps(payload, indent=2) if fmt == "json" else _render_markdown(payload)
    return {
        "command": command,
        "ok": bool(payload.get("ok", False)),
        "local_only": True,
        "format": fmt,
        "wrote_output_file": False,
        "stdout": stdout,
        "payload": payload,
    }


def _render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Codex Dispatch Run",
        "",
        f"- ok: {payload.get('ok')}",
        f"- run_id: {payload.get('run_id', '')}",
        f"- item_id: {payload.get('item_id', '')}",
        f"- dispatch_state: {payload.get('dispatch_state', '')}",
        f"- next_safe_action: {payload.get('next_safe_action', '')}",
    ]
    blockers = payload.get("details", {}).get("blockers", []) if isinstance(payload.get("details"), dict) else []
    if blockers:
        lines.extend(["", "## Blockers", *[f"- {blocker}" for blocker in blockers]])
    return "\n".join(lines)


def _error_payload(error: str, details: dict[str, Any]) -> dict[str, Any]:
    return {"ok": False, "local_only": True, "error": error, "details": details}


def _safe_path_token(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in str(value).strip()) or "unknown-run"


def _timestamp_token() -> str:
    return datetime.now(UTC).strftime("%Y%m%d%H%M%S%f")


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()
