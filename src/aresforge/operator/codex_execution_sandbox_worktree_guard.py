from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import subprocess
from typing import Any, Callable, Sequence

from aresforge.config import AppConfig
from aresforge.operator.local_project_queue import resolve_project_queue_path
from aresforge.operator.machine_safety_gate_engine import evaluate_machine_safety_gates
from aresforge.operator.queue_transaction_log import resolve_queue_transaction_log_path

COMMAND_NAME = "inspect-codex-worktree-guard"
GUARD_TYPE = "codex_execution_sandbox_worktree_guard_v1"
GUARD_VERSION = "m143.1"
DEFAULT_ITEM_ID = "m143-codex-execution-sandbox-and-worktree-guard"
DEFAULT_PROJECT_ID = "aresforge"
DEFAULT_MAX_STATUS_LINES = 50

CommandRunner = Callable[..., subprocess.CompletedProcess[Any]]

_PROTECTED_BRANCHES: tuple[str, ...] = ("main", "master", "release", "production")

_PROHIBITED_OPERATIONS: tuple[str, ...] = (
    "merge_pull_request",
    "force_push",
    "update_protected_branch",
    "enable_auto_merge",
    "create_release",
    "modify_github_workflow",
    "apply_source_patch_from_generated_output",
    "automatic_next_item_execution",
    "bypass_machine_safety_gate",
)

_BOUNDARY_CONFIRMATIONS: tuple[str, ...] = (
    "M143 inspects Codex execution sandbox and worktree guard readiness locally.",
    "This command performs no Codex execution, model execution, GitHub execution, patch application, queue mutation, or validation command execution.",
    "Real Codex execution remains default-deny and must use a separate explicit machine-gated command.",
    "Dirty worktree state is captured as guard evidence and blocks future real Codex execution until an operator reviews or cleans it.",
    "Codex stdout, stderr, and result metadata must be bounded to local artifact paths before any downstream validation.",
)


def inspect_codex_worktree_guard(
    config: AppConfig,
    *,
    item_id: str = DEFAULT_ITEM_ID,
    project_id: str = DEFAULT_PROJECT_ID,
    queue_path: str | Path | None = None,
    output: str | Path | None = None,
    force: bool = False,
    output_format: str = "json",
    max_status_lines: int = DEFAULT_MAX_STATUS_LINES,
    command_runner: CommandRunner | None = None,
) -> dict[str, Any]:
    fmt = str(output_format or "json").strip().lower()
    if fmt != "json":
        return _error("invalid_format", {"format": output_format, "supported_formats": ["json"]})

    normalized_item_id = str(item_id or DEFAULT_ITEM_ID).strip() or DEFAULT_ITEM_ID
    normalized_project_id = str(project_id or DEFAULT_PROJECT_ID).strip() or DEFAULT_PROJECT_ID
    queue = _load_queue(config, queue_path=queue_path)
    item = _find_item(queue, normalized_item_id)
    git_snapshot = _git_snapshot(
        config.repo_root,
        max_status_lines=max_status_lines,
        command_runner=command_runner,
    )
    gate_payload = _gate_payload(
        config,
        item_id=normalized_item_id,
        queue_path=queue_path,
    )
    gate_summary = _gate_summary(gate_payload)

    warnings = _warnings(
        item=item,
        gate_payload=gate_payload,
        project_id=normalized_project_id,
        git_snapshot=git_snapshot,
    )
    blocked_reasons = _blocked_reasons(item=item, gate_payload=gate_payload)
    blocked = bool(blocked_reasons)
    dirty = bool(git_snapshot.get("dirty"))

    payload: dict[str, Any] = {
        "record_type": GUARD_TYPE,
        "artifact_type": GUARD_TYPE,
        "guard_version": GUARD_VERSION,
        "generated": True,
        "generated_at": _now_iso(),
        "item_id": normalized_item_id,
        "project_id": normalized_project_id,
        "run_id": f"{normalized_item_id}:codex-worktree-guard-v1",
        "status": _status(blocked=blocked, dirty=dirty),
        "blocked": blocked,
        "blocked_reasons": blocked_reasons,
        "warnings": warnings,
        "machine_gates_checked": [gate_summary],
        "machine_gates_passed": bool(gate_summary.get("passed")),
        "artifacts_created": [],
        "mutation_performed": False,
        "external_execution_performed": False,
        "model_execution_performed": False,
        "codex_execution_performed": False,
        "github_execution_performed": False,
        "patch_application_performed": False,
        "local_only": True,
        "next_safe_action": _next_safe_action(blocked=blocked, dirty=dirty),
        "queue_item_found": bool(item),
        "queue_item_status": str(item.get("status", "")).strip(),
        "queue_path": str(resolve_project_queue_path(config.repo_root, queue_path)),
        "dirty_tree_detected": dirty,
        "clean_worktree_required_for_real_execution": True,
        "real_codex_execution_default": "deny",
        "real_codex_execution_allowed_by_this_command": False,
        "worktree_safe_for_future_real_codex_execution": bool(not blocked and not dirty and git_snapshot.get("available")),
        "codex_execution_guard": {
            "preflight_checks": _preflight_checks(
                item=item,
                gate_summary=gate_summary,
                git_snapshot=git_snapshot,
                dirty=dirty,
            ),
            "sandbox_policy": _sandbox_policy(config),
            "worktree_state": git_snapshot,
            "output_capture_boundaries": _output_capture_boundaries(config, normalized_item_id),
            "transaction_log_summary": _transaction_log_summary(config, item_id=normalized_item_id),
            "orchestration_boundary": _orchestration_boundary_summary(),
        },
        "prohibited_operations": list(_PROHIBITED_OPERATIONS),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
        "recommended_guard_artifact_path": str(
            (config.repo_root / ".aresforge" / "codex_execution" / "worktree_guard" / "m143-guard.json").resolve()
        ),
    }
    return _emit_or_write(config=config, payload=payload, output=output, force=force)


def _gate_payload(
    config: AppConfig,
    *,
    item_id: str,
    queue_path: str | Path | None,
) -> dict[str, Any]:
    result = evaluate_machine_safety_gates(
        config,
        item_id=item_id,
        gate_profile="read_only_agent",
        queue_path=queue_path,
        output_format="json",
    )
    return result.get("payload", {}) if isinstance(result, dict) else {}


def _gate_summary(gate_payload: dict[str, Any]) -> dict[str, Any]:
    checks = gate_payload.get("checks", [])
    failed = [
        str(check.get("check_id", "")).strip()
        for check in checks
        if isinstance(check, dict) and not bool(check.get("passed")) and not bool(check.get("warning_only"))
    ]
    return {
        "gate_profile": str(gate_payload.get("gate_profile", "read_only_agent")).strip() or "read_only_agent",
        "passed": bool(gate_payload.get("passed")) and not bool(gate_payload.get("blocked")),
        "blocked": bool(gate_payload.get("blocked")),
        "blocked_reasons": _list(gate_payload.get("blocked_reasons")),
        "checks_failed": failed,
    }


def _git_snapshot(
    repo_root: Path,
    *,
    max_status_lines: int,
    command_runner: CommandRunner | None,
) -> dict[str, Any]:
    runner = command_runner or subprocess.run
    status = _run_git(runner, repo_root, ("status", "--short", "--branch"))
    branch = _run_git(runner, repo_root, ("branch", "--show-current"))
    head = _run_git(runner, repo_root, ("rev-parse", "HEAD"))
    top_level = _run_git(runner, repo_root, ("rev-parse", "--show-toplevel"))
    available = bool(status.get("returncode") == 0)
    raw_status_lines = [line for line in str(status.get("stdout", "")).splitlines() if line.strip()]
    status_lines = [line for line in raw_status_lines if not line.startswith("## ")]
    max_lines = _positive_int(max_status_lines) or DEFAULT_MAX_STATUS_LINES
    truncated_lines = status_lines[:max_lines]
    categorized = _categorize_status_lines(status_lines)
    warnings = _dedupe(
        [
            *_list(status.get("stderr")),
            *_list(branch.get("stderr")),
            *_list(head.get("stderr")),
            *_list(top_level.get("stderr")),
        ]
    )
    branch_name = str(branch.get("stdout", "")).strip()
    return {
        "available": available,
        "repo_root": str(repo_root.resolve()),
        "git_top_level": str(top_level.get("stdout", "")).strip(),
        "branch": branch_name,
        "head": str(head.get("stdout", "")).strip(),
        "protected_branch": branch_name in _PROTECTED_BRANCHES,
        "dirty": bool(status_lines),
        "status_line_count": len(status_lines),
        "status_lines": truncated_lines,
        "status_lines_truncated": len(status_lines) > len(truncated_lines),
        "status_lines_omitted": max(0, len(status_lines) - len(truncated_lines)),
        "dirty_path_summary": categorized,
        "warnings": warnings,
    }


def _run_git(runner: CommandRunner, repo_root: Path, args: Sequence[str]) -> dict[str, Any]:
    try:
        completed = runner(
            ["git", *args],
            cwd=str(repo_root.resolve()),
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {"returncode": 1, "stdout": "", "stderr": str(exc)}
    return {
        "returncode": int(getattr(completed, "returncode", 1)),
        "stdout": _decode_output(getattr(completed, "stdout", "")),
        "stderr": _decode_output(getattr(completed, "stderr", "")),
    }


def _categorize_status_lines(status_lines: list[str]) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "tracked_changes": 0,
        "untracked_changes": 0,
        "docs_changes": 0,
        "source_changes": 0,
        "test_changes": 0,
        "queue_changes": 0,
        "artifact_changes": 0,
        "workflow_changes": 0,
        "protected_config_changes": 0,
    }
    for line in status_lines:
        path = _status_path(line)
        normalized = path.replace("\\", "/")
        if line.startswith("?? "):
            summary["untracked_changes"] += 1
        else:
            summary["tracked_changes"] += 1
        if normalized.startswith("docs/"):
            summary["docs_changes"] += 1
        if normalized.startswith("src/"):
            summary["source_changes"] += 1
        if normalized.startswith("tests/"):
            summary["test_changes"] += 1
        if normalized.startswith(".aresforge/queue/"):
            summary["queue_changes"] += 1
        if normalized.startswith("artifacts/") or normalized.startswith(".aresforge/codex_execution/"):
            summary["artifact_changes"] += 1
        if normalized.startswith(".github/workflows/"):
            summary["workflow_changes"] += 1
        if normalized in {"pyproject.toml", "setup.py", "setup.cfg"} or normalized.startswith(".github/"):
            summary["protected_config_changes"] += 1
    return summary


def _status_path(line: str) -> str:
    text = str(line).rstrip()
    if len(text) <= 3:
        return text.strip()
    path = text[3:].strip()
    if " -> " in path:
        path = path.split(" -> ", 1)[1].strip()
    return path


def _preflight_checks(
    *,
    item: dict[str, Any],
    gate_summary: dict[str, Any],
    git_snapshot: dict[str, Any],
    dirty: bool,
) -> list[dict[str, Any]]:
    return [
        _check("queue_item_exists", bool(item), "Queue item exists in the local queue."),
        _check("read_only_machine_gate_passed", bool(gate_summary.get("passed")), "Read-only machine safety gate passed."),
        _check("git_worktree_state_captured", bool(git_snapshot.get("available")), "Git worktree state was captured.", warning_only=True),
        _check("clean_worktree_for_real_codex", not dirty, "Real Codex execution requires a clean worktree.", warning_only=True),
        _check("sandbox_cwd_repo_root", True, "Future Codex execution cwd is constrained to the configured repo root."),
        _check("shell_invocation_disabled", True, "Future Codex subprocess execution must use shell=False command arrays."),
        _check("output_capture_bounded", True, "Future Codex stdout, stderr, and result metadata must be captured to bounded local artifacts."),
        _check("patch_application_disabled", True, "AresForge must not apply generated source patches from Codex output."),
        _check("github_execution_disabled", True, "GitHub execution is outside this guard command and remains separately gated."),
        _check("protected_branch_update_blocked", True, "Protected branch update operations remain blocked."),
    ]


def _check(check_id: str, passed: bool, message: str, *, warning_only: bool = False) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "passed": bool(passed),
        "message": message,
        "warning_only": bool(warning_only),
    }


def _sandbox_policy(config: AppConfig) -> dict[str, Any]:
    return {
        "cwd": str(config.repo_root.resolve()),
        "local_only": True,
        "shell": False,
        "background_process_allowed": False,
        "network_assumption": "AresForge does not grant network or GitHub permission from this guard.",
        "default_timeout_seconds": 300,
        "one_item_at_a_time": True,
        "allowed_write_roots": [
            str((config.repo_root / ".aresforge" / "codex_dispatch").resolve()),
            str((config.repo_root / ".aresforge" / "codex_execution").resolve()),
            str((config.artifact_root / "codex_dispatch").resolve()),
            str((config.artifact_root / "codex_execution").resolve()),
        ],
        "source_patch_application_allowed": False,
        "queue_mutation_allowed": False,
    }


def _output_capture_boundaries(config: AppConfig, item_id: str) -> dict[str, Any]:
    root = config.artifact_root / "codex_execution" / "sandbox" / _safe_id(item_id)
    return {
        "artifact_root": str(root.resolve()),
        "stdout_artifact_required": True,
        "stderr_artifact_required": True,
        "result_json_required": True,
        "max_inline_status_lines": DEFAULT_MAX_STATUS_LINES,
        "capture_paths_must_remain_local": True,
        "recommended_stdout_path": str((root / "stdout.txt").resolve()),
        "recommended_stderr_path": str((root / "stderr.txt").resolve()),
        "recommended_result_path": str((root / "execution-record.json").resolve()),
    }


def _transaction_log_summary(config: AppConfig, *, item_id: str) -> dict[str, Any]:
    path = resolve_queue_transaction_log_path(config.repo_root)
    if not path.exists():
        return {"path": str(path), "exists": False, "matching_transaction_count": 0, "latest_transaction": {}}
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "path": str(path),
            "exists": True,
            "matching_transaction_count": 0,
            "latest_transaction": {},
            "warnings": [f"Transaction log could not be read: {exc}"],
        }
    transactions = raw.get("transactions", []) if isinstance(raw, dict) else []
    matches = [
        transaction
        for transaction in transactions
        if isinstance(transaction, dict) and str(transaction.get("item_id", "")).strip() == item_id
    ]
    latest = matches[-1] if matches else {}
    return {
        "path": str(path),
        "exists": True,
        "matching_transaction_count": len(matches),
        "latest_transaction": latest,
    }


def _orchestration_boundary_summary() -> dict[str, Any]:
    return {
        "real_codex_single_dispatch_command": "run-codex-dispatch --execution-enabled",
        "real_codex_orchestration_command": "run-agent-orchestration --allow-codex",
        "guard_command_executes_or_resumes_orchestration": False,
        "requires_m136_validation_after_codex": True,
        "automatic_next_item_execution_allowed": False,
    }


def _warnings(
    *,
    item: dict[str, Any],
    gate_payload: dict[str, Any],
    project_id: str,
    git_snapshot: dict[str, Any],
) -> list[str]:
    warnings = _list(gate_payload.get("warnings"))
    warnings.extend(_list(git_snapshot.get("warnings")))
    if item and str(item.get("project_id", "")).strip() != project_id:
        warnings.append("Queue item project_id does not match the requested project_id.")
    if bool(git_snapshot.get("dirty")):
        warnings.append("Working tree has local changes; real Codex execution should remain blocked until reviewed or clean.")
    if bool(git_snapshot.get("protected_branch")):
        warnings.append("Current branch is protected by policy; protected branch updates remain prohibited.")
    return _dedupe(warnings)


def _blocked_reasons(*, item: dict[str, Any], gate_payload: dict[str, Any]) -> list[str]:
    reasons = _list(gate_payload.get("blocked_reasons"))
    if not item:
        reasons.append("Queue item must exist before this Codex worktree guard can be used as local capability evidence.")
    return _dedupe(reasons)


def _status(*, blocked: bool, dirty: bool) -> str:
    if blocked:
        return "blocked"
    if dirty:
        return "dirty_worktree_guarded"
    return "ready"


def _next_safe_action(*, blocked: bool, dirty: bool) -> str:
    if blocked:
        return "Resolve read-only machine gate blockers before relying on Codex sandbox or worktree guard evidence."
    if dirty:
        return "Review or clean the dirty worktree before any explicit real Codex execution command."
    return "Keep real Codex execution default-deny; use only a separate explicit gated command for one reviewed dispatch."


def _load_queue(config: AppConfig, *, queue_path: str | Path | None) -> dict[str, Any]:
    path = resolve_project_queue_path(config.repo_root, queue_path)
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    return raw if isinstance(raw, dict) else {}


def _find_item(queue: dict[str, Any], item_id: str) -> dict[str, Any]:
    items = queue.get("work_items", []) if isinstance(queue, dict) else []
    if not isinstance(items, list):
        return {}
    for item in items:
        if isinstance(item, dict) and str(item.get("item_id", "")).strip() == item_id:
            return item
    return {}


def _emit_or_write(
    *,
    config: AppConfig,
    payload: dict[str, Any],
    output: str | Path | None,
    force: bool,
) -> dict[str, Any]:
    if output is None:
        return {
            "command": COMMAND_NAME,
            "ok": not bool(payload.get("blocked")),
            "local_only": True,
            "format": "json",
            "wrote_output_file": False,
            "stdout": json.dumps(payload, indent=2),
            "payload": payload,
        }

    output_path = _resolve(config.repo_root, output)
    if output_path.exists() and not force:
        blocked = dict(payload)
        blocked["status"] = "blocked"
        blocked["blocked"] = True
        blocked["blocked_reasons"] = _dedupe(
            [*_list(blocked.get("blocked_reasons")), "Output file already exists. Re-run with --force to overwrite."]
        )
        return {
            "command": COMMAND_NAME,
            "ok": False,
            "local_only": True,
            "format": "json",
            "output": str(output_path),
            "force": force,
            "wrote_output_file": False,
            "stdout": json.dumps(blocked, indent=2),
            "payload": blocked,
        }

    artifact_payload = dict(payload)
    artifact_payload["artifacts_created"] = [str(output_path)]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact_payload, indent=2) + "\n", encoding="utf-8")
    return {
        "command": COMMAND_NAME,
        "ok": not bool(artifact_payload.get("blocked")),
        "local_only": True,
        "format": "json",
        "output": str(output_path),
        "force": force,
        "wrote_output_file": True,
        "payload": artifact_payload,
    }


def _resolve(repo_root: Path, value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


def _decode_output(value: bytes | str | None) -> str:
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


def _safe_id(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in str(value or "").strip().lower())
    return cleaned.strip("-") or "codex-worktree-guard"


def _list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(entry).strip() for entry in value if str(entry).strip()]
    if isinstance(value, tuple):
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


def _error(error: str, details: dict[str, Any]) -> dict[str, Any]:
    return {
        "command": COMMAND_NAME,
        "ok": False,
        "local_only": True,
        "error": error,
        "details": details,
    }
