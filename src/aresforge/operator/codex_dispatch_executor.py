from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import re
import subprocess
from typing import Any, Callable, Sequence

from aresforge.config import AppConfig
from aresforge.operator.local_project_queue import resolve_project_queue_path
from aresforge.operator.machine_safety_gate_engine import evaluate_machine_safety_gates

COMMAND_NAME = "run-codex-dispatch"
EXECUTION_RECORD_TYPE = "codex_dispatch_execution_v1"
EXECUTION_VERSION = "m135.1"
DEFAULT_TIMEOUT_SECONDS = 300

CommandRunner = Callable[..., subprocess.CompletedProcess[Any]]

_READY_STATUS = "ready"
_BOUNDARY_CONFIRMATIONS = (
    "M135 Codex dispatch execution is explicit, local, and one artifact at a time.",
    "Dry-run never invokes Codex.",
    "Non-dry-run execution requires --execution-enabled and passing codex_dispatch machine gates.",
    "AresForge captures stdout, stderr, and an execution record as local artifacts.",
    "AresForge does not apply patches, call GitHub, mutate queue status, mark completion, or start another item.",
)


def run_codex_dispatch_executor(
    config: AppConfig,
    *,
    item_id: str,
    artifact_path: str | Path,
    dry_run: bool = False,
    force: bool = False,
    output: str | Path | None = None,
    timeout_seconds: int | None = None,
    require_clean_worktree: bool = False,
    execution_enabled: bool = False,
    queue_path: str | Path | None = None,
    output_format: str = "json",
    command_runner: CommandRunner | None = None,
) -> dict[str, Any]:
    fmt = str(output_format or "json").strip().lower()
    if fmt != "json":
        return _error("invalid_format", {"format": output_format, "supported_formats": ["json"]})

    normalized_item_id = str(item_id or "").strip()
    resolved_artifact_path = _resolve(config.repo_root, artifact_path)
    resolved_queue_path = resolve_project_queue_path(config.repo_root, queue_path)
    started_at = _now_iso()
    timeout = _positive_int(timeout_seconds) or DEFAULT_TIMEOUT_SECONDS
    result_path = _resolve(config.repo_root, output) if output else _default_result_path(config, normalized_item_id)
    paths = _artifact_paths(config=config, item_id=normalized_item_id, result_path=result_path)

    queue, queue_errors = _load_queue(resolved_queue_path)
    item = _find_item(queue, normalized_item_id)
    artifact, artifact_errors = _load_artifact(resolved_artifact_path)
    command = _extract_command(artifact)
    prompt_input = _extract_prompt(artifact)
    git_status = _git_status(config.repo_root)

    gate_result = evaluate_machine_safety_gates(
        config,
        item_id=normalized_item_id,
        gate_profile="codex_dispatch",
        artifact_path=resolved_artifact_path,
        execution_record=resolved_artifact_path,
        queue_path=queue_path,
        force=bool(dry_run or execution_enabled or force),
        output_format="json",
    )
    machine_gate = gate_result.get("payload", {}) if isinstance(gate_result, dict) else {}

    blocked_reasons = _blocked_reasons(
        queue_errors=queue_errors,
        item=item,
        artifact_errors=artifact_errors,
        artifact=artifact,
        item_id=normalized_item_id,
        command=command,
        machine_gate=machine_gate,
        result_path=result_path,
        force=force,
        dry_run=dry_run,
        execution_enabled=execution_enabled,
        require_clean_worktree=require_clean_worktree,
        git_status=git_status,
    )
    blocked = bool(blocked_reasons)
    executed = False
    exit_code: int | None = None
    stdout = ""
    stderr = ""

    if not blocked and not dry_run:
        runner = command_runner or subprocess.run
        try:
            completed = runner(
                command,
                cwd=str(config.repo_root.resolve()),
                check=False,
                capture_output=True,
                input=prompt_input.encode("utf-8"),
                timeout=max(1, timeout),
                shell=False,
            )
            stdout = _decode_process_output(completed.stdout)
            stderr = _decode_process_output(completed.stderr)
            exit_code = int(completed.returncode)
            executed = True
        except (OSError, subprocess.SubprocessError) as exc:
            stderr = str(exc)
            exit_code = None
            executed = True
    elif dry_run and not blocked:
        stdout = "Dry-run: Codex dispatch command was not invoked.\n"

    completed_at = _now_iso()
    paths["stdout"].parent.mkdir(parents=True, exist_ok=True)
    paths["stdout"].write_text(stdout, encoding="utf-8")
    paths["stderr"].write_text(stderr, encoding="utf-8")

    payload = {
        "execution_record_type": EXECUTION_RECORD_TYPE,
        "execution_version": EXECUTION_VERSION,
        "item_id": normalized_item_id,
        "artifact_path": str(resolved_artifact_path),
        "dry_run": bool(dry_run),
        "execution_enabled": bool(execution_enabled),
        "executed": bool(executed),
        "blocked": blocked,
        "blocked_reasons": _dedupe(blocked_reasons),
        "machine_gates_checked": bool(machine_gate),
        "machine_gates_passed": bool(machine_gate.get("passed")) and not bool(machine_gate.get("blocked")),
        "command_invoked": command if (executed or dry_run) else [],
        "started_at": started_at,
        "completed_at": completed_at,
        "exit_code": exit_code,
        "stdout_artifact_path": str(paths["stdout"]),
        "stderr_artifact_path": str(paths["stderr"]),
        "result_artifact_path": str(result_path),
        "codex_execution_performed": bool(executed),
        "patch_application_performed": False,
        "github_execution_performed": False,
        "queue_mutation_performed": False,
        "next_safe_action": _next_safe_action(blocked=blocked, dry_run=bool(dry_run), executed=bool(executed), exit_code=exit_code),
        "codex_dispatch_executor_version": EXECUTION_VERSION,
        "local_only": True,
        "external_execution_performed": bool(executed),
        "model_execution_performed": False,
        "source_mutation_performed_by_aresforge": False,
        "queue_item_status": str(item.get("status", "")).strip(),
        "queue_path": str(resolved_queue_path),
        "timeout_seconds": timeout,
        "require_clean_worktree": bool(require_clean_worktree),
        "working_tree_dirty": bool(git_status.get("dirty")),
        "artifact_schema_valid": not artifact_errors and _required_safety_flags_present(artifact),
        "required_safety_flags_present": _required_safety_flags_present(artifact),
        "machine_gate_result": machine_gate,
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }
    result_path.parent.mkdir(parents=True, exist_ok=True)
    if result_path.exists() and not force and output:
        payload["blocked"] = True
        payload["executed"] = False
        payload["codex_execution_performed"] = False
        payload["blocked_reasons"] = _dedupe(
            [*payload["blocked_reasons"], "Result artifact already exists. Re-run with --force to overwrite."]
        )
    if not (result_path.exists() and not force and output):
        result_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    ok = not bool(payload["blocked"]) and (bool(dry_run) or (executed and exit_code == 0))
    rendered = json.dumps(payload, indent=2)
    return {
        "command": COMMAND_NAME,
        "ok": ok,
        "local_only": True,
        "format": "json",
        "wrote_output_file": True,
        "output": str(result_path),
        "stdout": rendered,
        "payload": payload,
    }


def _blocked_reasons(
    *,
    queue_errors: list[str],
    item: dict[str, Any],
    artifact_errors: list[str],
    artifact: dict[str, Any],
    item_id: str,
    command: list[str],
    machine_gate: dict[str, Any],
    result_path: Path,
    force: bool,
    dry_run: bool,
    execution_enabled: bool,
    require_clean_worktree: bool,
    git_status: dict[str, Any],
) -> list[str]:
    reasons: list[str] = []
    reasons.extend(queue_errors)
    if not item:
        reasons.append("Queue item was not found.")
    elif str(item.get("status", "")).strip() != _READY_STATUS:
        reasons.append("Queue item must be ready before Codex dispatch execution.")
    reasons.extend(_dependency_blockers(item=item))
    reasons.extend(artifact_errors)
    if artifact and str(artifact.get("item_id", "")).strip() not in {"", item_id}:
        reasons.append("Codex dispatch artifact item_id does not match the requested queue item.")
    if artifact and not _required_safety_flags_present(artifact):
        reasons.append("Codex dispatch artifact is missing required local-only safety flags.")
    if not command:
        reasons.append("Codex dispatch artifact must include a non-empty codex_command or command list.")
    if result_path.exists() and not force:
        reasons.append("Result artifact already exists. Re-run with --force to overwrite.")
    if not dry_run and not execution_enabled:
        reasons.append("Codex dispatch execution is disabled by default; pass --execution-enabled for non-dry-run execution.")
    if machine_gate.get("passed") is not True or machine_gate.get("blocked") is True:
        reasons.append("Machine safety gate profile codex_dispatch did not pass.")
        reasons.extend(_list(machine_gate.get("blocked_reasons")))
    if require_clean_worktree and git_status.get("dirty"):
        reasons.append("Working tree has local changes and --require-clean-worktree was supplied.")
    return _dedupe(reasons)


def _dependency_blockers(*, item: dict[str, Any]) -> list[str]:
    if not item:
        return []
    blockers = []
    if _list(item.get("blocked_by")):
        blockers.append("Queue item blocked_by must be empty.")
    return blockers


def _required_safety_flags_present(artifact: dict[str, Any]) -> bool:
    required = {
        "local_only": True,
        "execution_allowed": False,
        "execution_performed": False,
        "codex_execution_performed": False,
        "patch_application_performed": False,
        "github_execution_performed": False,
        "queue_mutation_performed": False,
    }
    return all(artifact.get(key) is expected for key, expected in required.items())


def _extract_command(artifact: dict[str, Any]) -> list[str]:
    for key in ("codex_command", "command", "command_invoked"):
        value = artifact.get(key)
        if isinstance(value, list):
            return [str(part) for part in value if str(part).strip()]
        if isinstance(value, str) and value.strip():
            return _split_simple_command(value)
    return []


def _split_simple_command(command: str) -> list[str]:
    return [part for part in re.split(r"\s+", command.strip()) if part]


def _extract_prompt(artifact: dict[str, Any]) -> str:
    for key in ("prompt_text", "prompt", "codex_prompt", "dispatch_prompt"):
        text = str(artifact.get(key, "") or "").strip()
        if text:
            return text + "\n"
    return ""


def _load_queue(path: Path) -> tuple[dict[str, Any], list[str]]:
    if not path.exists():
        return {}, [f"Queue file is missing: {path}"]
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {}, [f"Queue file is not valid JSON: {exc.msg}."]
    except OSError as exc:
        return {}, [f"Queue file could not be read: {exc}."]
    if not isinstance(raw, dict):
        return {}, ["Queue file JSON root must be an object."]
    return raw, []


def _find_item(queue: dict[str, Any], item_id: str) -> dict[str, Any]:
    items = queue.get("work_items", []) if isinstance(queue, dict) else []
    if not isinstance(items, list):
        return {}
    for item in items:
        if isinstance(item, dict) and str(item.get("item_id", "")).strip() == item_id:
            return item
    return {}


def _load_artifact(path: Path) -> tuple[dict[str, Any], list[str]]:
    if not path.exists():
        return {}, [f"Codex dispatch artifact path does not exist: {path}"]
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        return {}, [f"Codex dispatch artifact is not valid JSON: {exc.msg}."]
    except OSError as exc:
        return {}, [f"Codex dispatch artifact could not be read: {exc}."]
    if not isinstance(raw, dict):
        return {}, ["Codex dispatch artifact JSON root must be an object."]
    return raw, []


def _artifact_paths(*, config: AppConfig, item_id: str, result_path: Path) -> dict[str, Path]:
    stamp = result_path.stem
    root = config.artifact_root / "codex_dispatch" / "executions" / stamp
    return {
        "stdout": root / f"{_safe_id(item_id)}-stdout.txt",
        "stderr": root / f"{_safe_id(item_id)}-stderr.txt",
    }


def _default_result_path(config: AppConfig, item_id: str) -> Path:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    return config.artifact_root / "codex_dispatch" / "executions" / f"{stamp}-{_safe_id(item_id)}.json"


def _git_status(repo_root: Path) -> dict[str, Any]:
    try:
        result = subprocess.run(
            ["git", "status", "--short"],
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"available": False, "dirty": False, "status_lines": [], "warnings": [str(exc)]}
    return {
        "available": result.returncode == 0,
        "dirty": bool(result.stdout.strip()),
        "status_lines": [line for line in result.stdout.splitlines() if line.strip()],
        "warnings": [result.stderr.strip()] if result.stderr.strip() else [],
    }


def _resolve(repo_root: Path, value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


def _decode_process_output(value: bytes | str | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8-sig", errors="replace")
    return str(value)


def _positive_int(value: Any) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool) and value > 0:
        return value
    if isinstance(value, str) and value.strip().isdigit():
        parsed = int(value.strip())
        return parsed if parsed > 0 else None
    return None


def _next_safe_action(*, blocked: bool, dry_run: bool, executed: bool, exit_code: int | None) -> str:
    if blocked:
        return "Resolve blocked reasons before any Codex dispatch execution."
    if dry_run:
        return "Dry-run passed; review the execution record before explicitly enabling Codex dispatch."
    if executed and exit_code == 0:
        return "Review captured Codex output manually; M136 should validate the result before any completion decision."
    return "Inspect captured stderr/output and do not advance queue state automatically."


def _safe_id(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in str(value or "").strip().lower())
    return cleaned.strip("-") or "codex-dispatch"


def _list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(entry).strip() for entry in value if str(entry).strip()]
    if value in (None, ""):
        return []
    return [str(value).strip()]


def _dedupe(values: list[Any] | tuple[Any, ...] | Any) -> list[str]:
    deduped: list[str] = []
    for value in values:
        text = str(value).strip()
        if text and text not in deduped:
            deduped.append(text)
    return deduped


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _error(error_name: str, details: dict[str, Any]) -> dict[str, Any]:
    return {
        "command": COMMAND_NAME,
        "ok": False,
        "local_only": True,
        "error": error_name,
        "details": details,
    }
