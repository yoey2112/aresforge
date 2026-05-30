from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Sequence

from aresforge.config import AppConfig
from aresforge.operator.codex_dispatch_runner import (
    APPROVAL_PHRASE,
    approve_codex_dispatch,
    normalize_operator_command,
    run_operator_gated_codex_dispatch,
)
from aresforge.operator.local_project_queue import (
    capture_local_queue_completion_evidence,
    close_local_queue_item,
    inspect_local_queue_item_readiness,
    resolve_project_queue_path,
    start_local_queue_item,
)
from aresforge.operator.queue_dispatch_preparation import prepare_queue_item_dispatch

WorkflowRunner = Callable[..., subprocess.CompletedProcess[Any]]

WORKFLOW_VERSION = "m79.2.1"

_BOUNDARY_CONFIRMATIONS = (
    "Single-item Codex queue automation is local-only and explicit-command only.",
    "No background watcher, daemon, scheduler, polling loop, or file-change trigger is added.",
    "Exactly one ready queue item may be selected per command.",
    "Codex dispatch still requires the M78 explicit operator approval phrase.",
    "No automatic next-item execution is allowed.",
    "Prompt preparation remains artifact-only before dispatch.",
    "Prompt Builder does not execute prompts, call Codex, invoke local LLMs, mutate files, or advance queue items.",
    "No local LLM execution expansion is added.",
    "No GitHub API calls.",
    "No gh calls.",
    "No GitHub issues, PRs, workflows, or GitHub mutation.",
    "Git operations are local git CLI commit/push attempts only after validation gates pass.",
)


def run_single_ready_codex_queue_item(
    config: AppConfig,
    *,
    item_id: str | None = None,
    queue_path: str | Path | None = None,
    registry_path: str | Path | None = None,
    prompt_output: str | Path | None = None,
    force_prompt: bool = False,
    approved_by: str = "local_operator",
    approval_phrase: str = "",
    run_id: str | None = None,
    command: str | Sequence[str] | None = None,
    timeout_seconds: int = 300,
    validation_commands: list[str] | None = None,
    implementation_commit_message: str = "M79.2 add single-item ready Codex automation",
    queue_evidence_commit_message: str = "Record M79.2 queue evidence",
    closed_by: str = "local_operator",
    command_runner: WorkflowRunner | None = None,
    git_runner: WorkflowRunner | None = None,
    validation_runner: WorkflowRunner | None = None,
    output_format: str = "json",
) -> dict[str, Any]:
    normalized_item_id = str(item_id or "").strip()
    warnings: list[str] = []
    blockers: list[str] = []
    steps: list[dict[str, Any]] = []

    selection = _select_ready_item(
        config,
        item_id=normalized_item_id or None,
        queue_path=queue_path,
        registry_path=registry_path,
    )
    if not selection.get("ok", False):
        payload = _base_payload(
            item_id=normalized_item_id,
            workflow_state="selection_failed",
            warnings=warnings,
            blockers=list(selection.get("blockers", [])),
            steps=steps,
        )
        payload["selection"] = selection
        return _stdout_result("run-single-ready-codex-queue-item", payload, output_format)

    selected_item_id = str(selection["item_id"]).strip()
    readiness = selection["readiness"]
    if str(approval_phrase or "").strip() != APPROVAL_PHRASE:
        payload = _base_payload(
            item_id=selected_item_id,
            workflow_state="approval_rejected",
            warnings=warnings,
            blockers=["The exact M78 approval phrase is required before Codex dispatch."],
            steps=steps,
        )
        payload["required_approval_phrase"] = APPROVAL_PHRASE
        payload["selection"] = selection
        return _stdout_result("run-single-ready-codex-queue-item", payload, output_format)

    normalized_validation_commands = [command for command in _normalize_list(validation_commands or []) if command]
    if not normalized_validation_commands:
        payload = _base_payload(
            item_id=selected_item_id,
            workflow_state="validation_plan_missing",
            warnings=warnings,
            blockers=["At least one validation command is required."],
            steps=steps,
        )
        payload["selection"] = selection
        return _stdout_result("run-single-ready-codex-queue-item", payload, output_format)

    preparation = prepare_queue_item_dispatch(
        config,
        item_id=selected_item_id,
        target="codex",
        queue_path=queue_path,
        registry_path=registry_path,
        output=prompt_output,
        start_if_ready=False,
        force=force_prompt,
        output_format="json",
    )
    preparation_payload = preparation.get("payload", preparation)
    steps.append(_step("prepare_prompt_artifact", bool(preparation.get("ok", False)), preparation_payload))
    if not preparation.get("ok", False):
        payload = _base_payload(
            item_id=selected_item_id,
            workflow_state="preparation_failed",
            warnings=warnings,
            blockers=_collect_blockers(preparation_payload, "Prompt preparation failed."),
            steps=steps,
        )
        payload["selection"] = selection
        payload["readiness"] = readiness
        return _stdout_result("run-single-ready-codex-queue-item", payload, output_format)

    start = start_local_queue_item(
        config,
        item_id=selected_item_id,
        queue_path=queue_path,
        registry_path=registry_path,
        started_via="run-single-ready-codex-queue-item",
    )
    steps.append(_step("start_selected_queue_item", bool(start.get("ok", False)), start))
    if not start.get("ok", False):
        payload = _base_payload(
            item_id=selected_item_id,
            workflow_state="start_failed",
            warnings=warnings,
            blockers=_collect_blockers(start, "Selected queue item could not be started."),
            steps=steps,
        )
        payload["selection"] = selection
        payload["readiness"] = readiness
        return _stdout_result("run-single-ready-codex-queue-item", payload, output_format)

    approval = approve_codex_dispatch(
        config,
        item_id=selected_item_id,
        approved_by=approved_by,
        approval_phrase=approval_phrase,
        queue_path=queue_path,
        registry_path=registry_path,
        run_id=run_id,
        output_format="json",
    )
    approval_payload = approval.get("payload", approval)
    steps.append(_step("approve_codex_dispatch", bool(approval.get("ok", False)), approval_payload))
    if not approval.get("ok", False):
        return _failed_after_start(
            config,
            selected_item_id,
            queue_path,
            "approval_failed",
            steps,
            _collect_blockers(approval_payload, "Codex dispatch approval failed."),
            validation_commands=normalized_validation_commands,
            output_format=output_format,
        )

    selected_run_id = str(approval_payload.get("run_id", "")).strip()
    dispatch = run_operator_gated_codex_dispatch(
        config,
        item_id=selected_item_id,
        run_id=selected_run_id,
        command=command,
        timeout_seconds=timeout_seconds,
        command_runner=command_runner,
        output_format="json",
    )
    dispatch_payload = dispatch.get("payload", dispatch)
    steps.append(_step("run_codex_dispatch", bool(dispatch.get("ok", False)), dispatch_payload))
    if not dispatch.get("ok", False):
        return _failed_after_start(
            config,
            selected_item_id,
            queue_path,
            "codex_failed",
            steps,
            _collect_blockers(dispatch_payload, "Codex dispatch failed."),
            validation_commands=normalized_validation_commands,
            output_format=output_format,
        )

    validation = _run_validation_commands(
        config.repo_root,
        normalized_validation_commands,
        runner=validation_runner or subprocess.run,
    )
    steps.append(_step("run_validation", bool(validation.get("ok", False)), validation))
    if not validation.get("ok", False):
        return _failed_after_start(
            config,
            selected_item_id,
            queue_path,
            "validation_failed",
            steps,
            _collect_blockers(validation, "Validation failed."),
            validation_commands=normalized_validation_commands,
            validation_results=list(validation.get("results", [])),
            dispatch_payload=dispatch_payload,
            output_format=output_format,
        )

    implementation_commit = _git_commit_and_push(
        config.repo_root,
        message=implementation_commit_message,
        runner=git_runner or subprocess.run,
    )
    steps.append(_step("commit_push_implementation", bool(implementation_commit.get("ok", False)), implementation_commit))
    if not implementation_commit.get("ok", False):
        evidence = _capture_recovery_evidence(
            config,
            selected_item_id,
            queue_path,
            workflow_state="implementation_commit_push_failed",
            validation_commands=normalized_validation_commands,
            validation_results=list(validation.get("results", [])),
            dispatch_payload=dispatch_payload,
            commit_result=implementation_commit,
        )
        steps.append(_step("capture_recovery_evidence", bool(evidence.get("ok", False)), evidence))
        payload = _base_payload(
            item_id=selected_item_id,
            workflow_state="implementation_commit_push_failed",
            warnings=list(evidence.get("warnings", [])),
            blockers=_collect_blockers(implementation_commit, "Implementation commit/push failed."),
            steps=steps,
        )
        payload["recovery_required"] = True
        payload["completion_evidence"] = evidence.get("completion_evidence", {})
        payload["commit_hash"] = str(implementation_commit.get("commit_hash", "")).strip()
        payload["push_result"] = str(implementation_commit.get("push_result", "")).strip()
        return _stdout_result("run-single-ready-codex-queue-item", payload, output_format)

    evidence = capture_local_queue_completion_evidence(
        config,
        item_id=selected_item_id,
        evidence_summary="Single-item Codex automation completed dispatch, validation, and implementation commit/push.",
        validation_commands=normalized_validation_commands,
        validation_results=list(validation.get("results", [])),
        smoke_checks=[],
        diff_check_result=_find_result(normalized_validation_commands, validation.get("results", []), "git diff --check"),
        files_changed=list(implementation_commit.get("files_changed", [])),
        commit_hash=str(implementation_commit.get("commit_hash", "")).strip(),
        push_result=str(implementation_commit.get("push_result", "")).strip(),
        review_evidence=[
            f"Codex dispatch run {selected_run_id} reached review_required.",
            f"stdout: {dispatch_payload.get('stdout_path', '')}",
            f"stderr: {dispatch_payload.get('stderr_path', '')}",
        ],
        operator_notes="Workflow processed exactly one queue item and did not start a next item.",
        queue_path=queue_path,
    )
    steps.append(_step("capture_queue_completion_evidence", bool(evidence.get("ok", False)), evidence))
    if not evidence.get("ok", False):
        payload = _base_payload(
            item_id=selected_item_id,
            workflow_state="queue_evidence_capture_failed",
            warnings=list(evidence.get("warnings", [])),
            blockers=_collect_blockers(evidence, "Queue evidence capture failed."),
            steps=steps,
        )
        payload["recovery_required"] = True
        return _stdout_result("run-single-ready-codex-queue-item", payload, output_format)

    closeout = close_local_queue_item(
        config,
        item_id=selected_item_id,
        closeout_summary="M79.2 single-item Codex automation evidence reviewed and recorded.",
        closed_by=closed_by,
        queue_path=queue_path,
    )
    steps.append(_step("complete_queue_item", bool(closeout.get("ok", False)), closeout))
    if not closeout.get("ok", False):
        payload = _base_payload(
            item_id=selected_item_id,
            workflow_state="queue_completion_failed",
            warnings=list(closeout.get("warnings", [])),
            blockers=_collect_blockers(closeout, "Queue item completion failed."),
            steps=steps,
        )
        payload["recovery_required"] = True
        payload["commit_hash"] = str(implementation_commit.get("commit_hash", "")).strip()
        payload["push_result"] = str(implementation_commit.get("push_result", "")).strip()
        return _stdout_result("run-single-ready-codex-queue-item", payload, output_format)

    queue_commit = _git_commit_and_push(
        config.repo_root,
        message=queue_evidence_commit_message,
        runner=git_runner or subprocess.run,
    )
    steps.append(_step("commit_push_queue_evidence", bool(queue_commit.get("ok", False)), queue_commit))
    workflow_state = "completed" if queue_commit.get("ok", False) else "queue_evidence_commit_push_failed"
    payload = _base_payload(
        item_id=selected_item_id,
        workflow_state=workflow_state,
        warnings=[],
        blockers=[] if queue_commit.get("ok", False) else _collect_blockers(queue_commit, "Queue evidence commit/push failed."),
        steps=steps,
    )
    payload.update(
        {
            "ok": bool(queue_commit.get("ok", False)),
            "run_id": selected_run_id,
            "prompt_artifact_path": str(preparation_payload.get("prompt_artifact_path", "")).strip(),
            "dispatch_state": str(dispatch_payload.get("dispatch_state", "")).strip(),
            "validation_results": list(validation.get("results", [])),
            "implementation_commit_hash": str(implementation_commit.get("commit_hash", "")).strip(),
            "implementation_push_result": str(implementation_commit.get("push_result", "")).strip(),
            "queue_evidence_commit_hash": str(queue_commit.get("commit_hash", "")).strip(),
            "queue_evidence_push_result": str(queue_commit.get("push_result", "")).strip(),
            "queue_item_status": str(closeout.get("status", "")).strip(),
            "automatic_next_item_execution_allowed": False,
            "next_item_started": False,
            "recovery_required": not bool(queue_commit.get("ok", False)),
        }
    )
    return _stdout_result("run-single-ready-codex-queue-item", payload, output_format)


def _select_ready_item(
    config: AppConfig,
    *,
    item_id: str | None,
    queue_path: str | Path | None,
    registry_path: str | Path | None,
) -> dict[str, Any]:
    resolved_queue_path = resolve_project_queue_path(config.repo_root, queue_path)
    loaded = _load_queue_items(resolved_queue_path)
    if not loaded.get("ok", False):
        return loaded

    items = loaded["work_items"]
    if item_id:
        item = next((candidate for candidate in items if candidate.get("item_id") == item_id), None)
        if item is None:
            return {"ok": False, "item_id": item_id, "blockers": [f"Queue item not found: {item_id}"], "warnings": []}
        readiness = inspect_local_queue_item_readiness(
            config,
            item_id=item_id,
            queue_path=resolved_queue_path,
            registry_path=registry_path,
        )
        if str(item.get("status", "")).strip() != "ready" or not readiness.get("can_start", False):
            return {
                "ok": False,
                "item_id": item_id,
                "status": str(item.get("status", "")).strip(),
                "readiness": readiness,
                "blockers": ["Selected queue item must be ready and startable."],
                "warnings": [],
            }
        return {"ok": True, "item_id": item_id, "status": "ready", "readiness": readiness, "warnings": []}

    ready: list[dict[str, Any]] = []
    for item in items:
        candidate_id = str(item.get("item_id", "")).strip()
        if str(item.get("status", "")).strip() != "ready":
            continue
        readiness = inspect_local_queue_item_readiness(
            config,
            item_id=candidate_id,
            queue_path=resolved_queue_path,
            registry_path=registry_path,
        )
        if readiness.get("can_start", False):
            ready.append({"item": item, "readiness": readiness})

    if not ready:
        return {"ok": False, "item_id": "", "blockers": ["No ready/startable queue item found."], "warnings": []}
    if len(ready) > 1:
        return {
            "ok": False,
            "item_id": "",
            "ready_item_ids": [entry["item"]["item_id"] for entry in ready],
            "blockers": ["More than one ready/startable queue item found; provide --item-id."],
            "warnings": [],
        }
    only = ready[0]
    return {
        "ok": True,
        "item_id": only["item"]["item_id"],
        "status": "ready",
        "readiness": only["readiness"],
        "warnings": [],
    }


def _run_validation_commands(repo_root: Path, commands: list[str], *, runner: WorkflowRunner) -> dict[str, Any]:
    results: list[str] = []
    details: list[dict[str, Any]] = []
    blockers: list[str] = []
    for command in commands:
        try:
            args = normalize_operator_command(command)
        except ValueError as exc:
            results.append(f"{command} -> fail")
            details.append({"command": command, "exit_code": None, "stdout": "", "stderr": str(exc)})
            blockers.append(f"Validation command failed: {command}: {exc}")
            continue
        if not args:
            blockers.append("Empty validation command supplied.")
            continue
        try:
            completed = runner(args, cwd=str(repo_root), check=False, capture_output=True, text=True, shell=False)
            exit_code = int(completed.returncode)
            state = "pass" if exit_code == 0 else "fail"
            stdout = _decode(completed.stdout).strip()
            stderr = _decode(completed.stderr).strip()
            results.append(f"{command} -> {state}")
            details.append({"command": command, "exit_code": exit_code, "stdout": stdout, "stderr": stderr})
            if exit_code != 0:
                blockers.append(f"Validation command failed: {command}")
        except (OSError, subprocess.SubprocessError) as exc:
            results.append(f"{command} -> fail")
            details.append({"command": command, "exit_code": None, "stdout": "", "stderr": str(exc)})
            blockers.append(f"Validation command failed: {command}: {exc}")
    return {"ok": not blockers, "results": results, "details": details, "blockers": blockers}


def _git_commit_and_push(repo_root: Path, *, message: str, runner: WorkflowRunner) -> dict[str, Any]:
    commands = [
        ["git", "status", "--short"],
        ["git", "add", "-A"],
        ["git", "commit", "-m", message],
        ["git", "rev-parse", "HEAD"],
        ["git", "push"],
    ]
    details: list[dict[str, Any]] = []
    commit_hash = ""
    files_changed: list[str] = []
    for index, command in enumerate(commands):
        try:
            completed = runner(command, cwd=str(repo_root), check=False, capture_output=True, text=True, shell=False)
            exit_code = int(completed.returncode)
            stdout = _decode(completed.stdout).strip()
            stderr = _decode(completed.stderr).strip()
        except (OSError, subprocess.SubprocessError) as exc:
            return {
                "ok": False,
                "command": " ".join(command),
                "commit_hash": commit_hash,
                "push_result": f"recovery_required: {exc}",
                "files_changed": files_changed,
                "details": details,
                "blockers": [f"Git command failed: {' '.join(command)}: {exc}"],
            }
        details.append({"command": " ".join(command), "exit_code": exit_code, "stdout": stdout, "stderr": stderr})
        if index == 0:
            files_changed = [line.strip() for line in stdout.splitlines() if line.strip()]
        if exit_code != 0:
            return {
                "ok": False,
                "command": " ".join(command),
                "commit_hash": commit_hash,
                "push_result": f"recovery_required: {' '.join(command)} failed",
                "files_changed": files_changed,
                "details": details,
                "blockers": [f"Git command failed: {' '.join(command)}"],
            }
        if command[:2] == ["git", "rev-parse"]:
            commit_hash = stdout.splitlines()[0].strip() if stdout else ""
    return {
        "ok": True,
        "commit_hash": commit_hash,
        "push_result": "git push -> pass",
        "files_changed": files_changed,
        "details": details,
        "blockers": [],
    }


def _failed_after_start(
    config: AppConfig,
    item_id: str,
    queue_path: str | Path | None,
    workflow_state: str,
    steps: list[dict[str, Any]],
    blockers: list[str],
    *,
    validation_commands: list[str],
    validation_results: list[str] | None = None,
    dispatch_payload: dict[str, Any] | None = None,
    output_format: str = "json",
) -> dict[str, Any]:
    evidence = capture_local_queue_completion_evidence(
        config,
        item_id=item_id,
        evidence_summary=f"Recovery required: {workflow_state}.",
        validation_commands=validation_commands,
        validation_results=validation_results or [],
        diff_check_result="not completed",
        files_changed=[],
        commit_hash="",
        push_result="recovery_required",
        review_evidence=[
            str(dispatch_payload.get("error_summary", "")).strip()
            for dispatch_payload in [dispatch_payload or {}]
            if str(dispatch_payload.get("error_summary", "")).strip()
        ],
        operator_notes="Workflow stopped before queue completion and did not start a next item.",
        queue_path=queue_path,
    )
    steps.append(_step("capture_recovery_evidence", bool(evidence.get("ok", False)), evidence))
    payload = _base_payload(
        item_id=item_id,
        workflow_state=workflow_state,
        warnings=list(evidence.get("warnings", [])),
        blockers=blockers,
        steps=steps,
    )
    payload["recovery_required"] = True
    payload["completion_evidence"] = evidence.get("completion_evidence", {})
    return _stdout_result("run-single-ready-codex-queue-item", payload, output_format)


def _capture_recovery_evidence(
    config: AppConfig,
    item_id: str,
    queue_path: str | Path | None,
    *,
    workflow_state: str,
    validation_commands: list[str],
    validation_results: list[str],
    dispatch_payload: dict[str, Any],
    commit_result: dict[str, Any],
) -> dict[str, Any]:
    return capture_local_queue_completion_evidence(
        config,
        item_id=item_id,
        evidence_summary=f"Recovery required: {workflow_state}.",
        validation_commands=validation_commands,
        validation_results=validation_results,
        diff_check_result=_find_result(validation_commands, validation_results, "git diff --check"),
        files_changed=list(commit_result.get("files_changed", [])),
        commit_hash=str(commit_result.get("commit_hash", "")).strip(),
        push_result=str(commit_result.get("push_result", "recovery_required")).strip(),
        review_evidence=[f"Codex dispatch state: {dispatch_payload.get('dispatch_state', '')}"],
        operator_notes="Commit/push failed after validation; queue item was not completed.",
        queue_path=queue_path,
    )


def _base_payload(
    *,
    item_id: str,
    workflow_state: str,
    warnings: list[str],
    blockers: list[str],
    steps: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "ok": workflow_state == "completed",
        "local_only": True,
        "workflow_version": WORKFLOW_VERSION,
        "item_id": item_id,
        "workflow_state": workflow_state,
        "automatic_next_item_execution_allowed": False,
        "next_item_started": False,
        "warnings": sorted({str(warning).strip() for warning in warnings if str(warning).strip()}),
        "blockers": sorted({str(blocker).strip() for blocker in blockers if str(blocker).strip()}),
        "steps": steps,
        "next_safe_action": _next_safe_action(workflow_state),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }


def _load_queue_items(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"ok": False, "item_id": "", "blockers": [f"Local project queue not found: {path}"], "warnings": []}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"ok": False, "item_id": "", "blockers": [f"Local project queue could not be read: {exc}"], "warnings": []}
    items = raw.get("work_items", []) if isinstance(raw, dict) else []
    normalized = [
        {**candidate, "item_id": str(candidate.get("item_id", "")).strip()}
        for candidate in items
        if isinstance(candidate, dict) and str(candidate.get("item_id", "")).strip()
    ]
    return {"ok": True, "work_items": normalized, "warnings": []}


def _step(name: str, ok: bool, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": name,
        "ok": ok,
        "state": str(payload.get("workflow_state") or payload.get("dispatch_state") or payload.get("status") or "").strip(),
        "error": str(payload.get("error", "")).strip(),
        "blockers": _collect_blockers(payload, ""),
    }


def _collect_blockers(payload: dict[str, Any], fallback: str) -> list[str]:
    values: list[str] = []
    for key in ("blockers", "warnings"):
        raw = payload.get(key, [])
        if isinstance(raw, list):
            values.extend(str(entry).strip() for entry in raw if str(entry).strip())
    details = payload.get("details", {})
    if isinstance(details, dict):
        raw = details.get("blockers", [])
        if isinstance(raw, list):
            values.extend(str(entry).strip() for entry in raw if str(entry).strip())
        message = str(details.get("message", "")).strip()
        if message:
            values.append(message)
    error = str(payload.get("error", "")).strip()
    if error:
        values.append(error)
    if not values and fallback:
        values.append(fallback)
    return sorted(set(values))


def _find_result(commands: list[str], results: list[str], needle: str) -> str:
    for command, result in zip(commands, results):
        if needle in command:
            return result
    return ""


def _normalize_list(values: list[str]) -> list[str]:
    return [str(value).strip() for value in values if str(value).strip()]


def _decode(value: bytes | str | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8-sig", errors="replace")
    return str(value)


def _next_safe_action(workflow_state: str) -> str:
    if workflow_state == "completed":
        return "Inspect queue evidence and do not start the next item automatically."
    if workflow_state in {"selection_failed", "approval_rejected", "validation_plan_missing"}:
        return "Resolve blockers and rerun explicitly for one ready queue item."
    if workflow_state.endswith("failed") or "failed" in workflow_state:
        return "Review recovery evidence, fix the failed step, and rerun explicitly for one item only."
    return "Resolve blockers and rerun explicitly for one ready queue item."


def _stdout_result(command: str, payload: dict[str, Any], output_format: str) -> dict[str, Any]:
    fmt = str(output_format or "json").lower().strip()
    if fmt not in {"json", "markdown"}:
        return {
            "ok": False,
            "local_only": True,
            "error": "invalid_format",
            "details": {"format": output_format, "supported_formats": ["json", "markdown"]},
        }
    return {
        "command": command,
        "ok": bool(payload.get("ok", False)),
        "local_only": True,
        "format": fmt,
        "wrote_output_file": False,
        "stdout": json.dumps(payload, indent=2) if fmt == "json" else _render_markdown(payload),
        "payload": payload,
    }


def _render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Single Ready Codex Queue Item",
        "",
        f"- ok: {payload.get('ok')}",
        f"- item_id: {payload.get('item_id', '')}",
        f"- workflow_state: {payload.get('workflow_state', '')}",
        f"- next_item_started: {payload.get('next_item_started')}",
        f"- next_safe_action: {payload.get('next_safe_action', '')}",
        "",
        "## Boundaries",
    ]
    lines.extend(f"- {entry}" for entry in payload.get("boundary_confirmations", []))
    blockers = payload.get("blockers", []) if isinstance(payload.get("blockers"), list) else []
    if blockers:
        lines.extend(["", "## Blockers"])
        lines.extend(f"- {entry}" for entry in blockers)
    return "\n".join(lines)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()
