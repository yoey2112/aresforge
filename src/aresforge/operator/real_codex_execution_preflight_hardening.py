from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import subprocess
from typing import Any, Callable

from aresforge.config import AppConfig
from aresforge.operator.codex_execution_sandbox_worktree_guard import inspect_codex_worktree_guard
from aresforge.operator.codex_validation_profiles import inspect_codex_validation_profiles
from aresforge.operator.durable_orchestration_run_store import read_orchestration_run_store
from aresforge.operator.local_project_queue import resolve_project_queue_path
from aresforge.operator.machine_safety_gate_engine import evaluate_machine_safety_gates
from aresforge.operator.operator_autonomy_configuration_profile import inspect_autonomy_profile
from aresforge.operator.orchestration_artifact_retention_policy import inspect_orchestration_artifact_retention

COMMAND_NAME = "preflight-real-codex-execution"
RECORD_TYPE = "real_codex_execution_preflight_hardening_v1"
PREFLIGHT_VERSION = "m159.1"
DEFAULT_ITEM_ID = "m159-real-codex-execution-preflight-hardening"
DEFAULT_PROJECT_ID = "aresforge"
DEFAULT_AUTONOMY_PROFILE = "codex_low_risk_enabled"

CommandRunner = Callable[..., subprocess.CompletedProcess[Any]]

_PROHIBITED_OPERATIONS: tuple[str, ...] = (
    "merge_pull_request",
    "force_push",
    "update_protected_branch",
    "enable_auto_merge",
    "create_release",
    "modify_github_workflow",
    "apply_source_patch_from_generated_output",
    "automatic_next_item_execution",
    "automatic_retry_loop",
    "bypass_machine_safety_gate",
)

_REQUIRED_ARTIFACT_PATHS: tuple[str, ...] = (
    ".aresforge/orchestrator/run_history.json",
    ".aresforge/codex_dispatch",
    "artifacts/codex_dispatch",
    "artifacts/codex_result_ingestion",
)

_BOUNDARY_CONFIRMATIONS: tuple[str, ...] = (
    "M159 performs dry-run preflight hardening only; it never invokes Codex.",
    "Real Codex execution remains a separate explicit command with operator flags and machine gates.",
    "A clean worktree, durable run store, artifact capture readiness, validation profile, retry policy, and source patch policy must all be acceptable before future real execution.",
    "Source patches from Codex output remain default-deny and may only reach a separate dry-run/apply boundary defined by later gates.",
)


def preflight_real_codex_execution(
    config: AppConfig,
    *,
    item_id: str = DEFAULT_ITEM_ID,
    project_id: str = DEFAULT_PROJECT_ID,
    dry_run: bool = False,
    autonomy_profile: str | None = None,
    validation_profile: str | None = None,
    changed_paths: list[str] | tuple[str, ...] | None = None,
    queue_path: str | Path | None = None,
    history_path: str | Path | None = None,
    output: str | Path | None = None,
    force: bool = False,
    output_format: str = "json",
    command_runner: CommandRunner | None = None,
) -> dict[str, Any]:
    fmt = _text(output_format).lower() or "json"
    if fmt != "json":
        return _error("invalid_format", {"format": output_format, "supported_formats": ["json"]})

    normalized_item_id = _text(item_id) or DEFAULT_ITEM_ID
    normalized_project_id = _text(project_id) or DEFAULT_PROJECT_ID
    selected_autonomy_profile = _text(autonomy_profile) or DEFAULT_AUTONOMY_PROFILE

    if not dry_run:
        payload = _base_payload(
            config,
            item_id=normalized_item_id,
            project_id=normalized_project_id,
            autonomy_profile=selected_autonomy_profile,
            dry_run=False,
        )
        payload["status"] = "blocked"
        payload["blocked"] = True
        payload["blocked_reasons"] = ["M159 preflight requires --dry-run and never runs real Codex."]
        payload["next_safe_action"] = "Re-run with --dry-run to generate non-executing preflight evidence."
        return _emit_or_write(config=config, payload=payload, output=output, force=force, command_ok=False)

    queue = _load_queue(config, queue_path=queue_path)
    item = _find_item(queue, normalized_item_id)
    read_only_gate = _gate_summary(
        _gate_payload(config, item_id=normalized_item_id, gate_profile="read_only_agent", queue_path=queue_path)
    )
    autonomy_gate = _gate_summary(
        _gate_payload(
            config,
            item_id=normalized_item_id,
            gate_profile="operator_autonomy_profile",
            queue_path=queue_path,
        )
    )
    autonomy_payload = _payload(
        inspect_autonomy_profile(
            config,
            project_id=normalized_project_id,
            item_id=normalized_item_id,
            autonomy_profile=selected_autonomy_profile,
            queue_path=queue_path,
            output_format="json",
        )
    )
    worktree_payload = _payload(
        inspect_codex_worktree_guard(
            config,
            item_id=normalized_item_id,
            project_id=normalized_project_id,
            queue_path=queue_path,
            output_format="json",
            command_runner=command_runner,
        )
    )
    validation_payload = _payload(
        inspect_codex_validation_profiles(
            config,
            item_id=normalized_item_id,
            project_id=normalized_project_id,
            queue_path=queue_path,
            task_type=_text(item.get("item_type") or item.get("type")) or "orchestration",
            risk_class=_risk_class(item),
            changed_paths=list(changed_paths or []),
            output_format="json",
            command_runner=command_runner,
        )
    )
    store = read_orchestration_run_store(
        config,
        store_path=history_path,
        bootstrap_missing=False,
        project_id=normalized_project_id,
    )
    retention_payload = _payload(
        inspect_orchestration_artifact_retention(
            config,
            project_id=normalized_project_id,
            item_id=normalized_item_id,
            history_path=history_path,
            queue_path=queue_path,
            output_format="json",
        )
    )

    artifact_readiness = _artifact_readiness(config)
    retry_policy = _retry_policy_summary()
    source_patch_policy = _source_patch_risk_policy()
    validation_profile_id = _text(validation_profile) or _text(validation_payload.get("selected_profile")) or "full_local_safe"
    validation_summary = _validation_summary(validation_payload, selected_profile=validation_profile_id)
    readiness_checks = _readiness_checks(
        item=item,
        read_only_gate=read_only_gate,
        autonomy_gate=autonomy_gate,
        autonomy_payload=autonomy_payload,
        worktree_payload=worktree_payload,
        validation_payload=validation_payload,
        store=store,
        artifact_readiness=artifact_readiness,
        retry_policy=retry_policy,
        source_patch_policy=source_patch_policy,
        validation_profile=validation_summary,
    )
    blocked_reasons = _blocked_reasons(readiness_checks)
    warnings = _warnings(
        autonomy_payload=autonomy_payload,
        worktree_payload=worktree_payload,
        validation_payload=validation_payload,
        retention_payload=retention_payload,
        store=store,
        item=item,
    )
    blocked = bool(blocked_reasons)
    machine_gates = [read_only_gate, autonomy_gate]

    payload = _base_payload(
        config,
        item_id=normalized_item_id,
        project_id=normalized_project_id,
        autonomy_profile=selected_autonomy_profile,
        dry_run=True,
    )
    payload.update(
        {
            "status": "blocked" if blocked else "ready_for_explicit_gated_real_codex",
            "blocked": blocked,
            "blocked_reasons": blocked_reasons,
            "warnings": warnings,
            "machine_gates_checked": machine_gates,
            "machine_gates_passed": all(bool(gate.get("passed")) for gate in machine_gates),
            "next_safe_action": _next_safe_action(blocked=blocked),
            "queue_item_found": bool(item),
            "queue_item_status": _text(item.get("status")),
            "queue_path": str(resolve_project_queue_path(config.repo_root, queue_path)),
            "real_codex_execution_preflight_passed": not blocked,
            "codex_execution_would_be_blocked": blocked,
            "codex_execution_allowed_by_this_command": False,
            "candidate_future_command": "run-end-to-end-codex-loop --execution-enabled --allow-low-risk-code --changed-path <path>",
            "required_explicit_flags_for_future_real_codex": [
                "--execution-enabled",
                "--allow-low-risk-code",
                "--changed-path",
            ],
            "readiness_checks": readiness_checks,
            "preflight_components": {
                "autonomy_profile": _component_summary(autonomy_payload),
                "worktree_guard": _component_summary(worktree_payload),
                "validation_profile": _component_summary(validation_payload),
                "artifact_retention": _component_summary(retention_payload),
            },
            "worktree_guard_summary": _worktree_summary(worktree_payload),
            "run_store_readiness": _run_store_readiness(store),
            "artifact_readiness": artifact_readiness,
            "validation_profile": validation_summary,
            "retry_policy": retry_policy,
            "source_patch_risk_policy": source_patch_policy,
            "future_machine_gates_required": [
                "codex_dispatch",
                "queue_status_mutation before completion",
                "source_patch_apply_dry_run only if reviewing a generated source patch",
            ],
            "prohibited_operations": list(_PROHIBITED_OPERATIONS),
            "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
        }
    )
    return _emit_or_write(config=config, payload=payload, output=output, force=force, command_ok=True)


def _base_payload(
    config: AppConfig,
    *,
    item_id: str,
    project_id: str,
    autonomy_profile: str,
    dry_run: bool,
) -> dict[str, Any]:
    return {
        "record_type": RECORD_TYPE,
        "artifact_type": RECORD_TYPE,
        "preflight_version": PREFLIGHT_VERSION,
        "generated": True,
        "generated_at": _now_iso(),
        "project_id": project_id,
        "item_id": item_id,
        "run_id": f"{item_id}:real-codex-preflight-v1",
        "status": "unknown",
        "blocked": False,
        "blocked_reasons": [],
        "warnings": [],
        "machine_gates_checked": [],
        "machine_gates_passed": False,
        "autonomy_profile": autonomy_profile,
        "dry_run": bool(dry_run),
        "artifacts_created": [],
        "mutation_performed": False,
        "queue_mutation_performed": False,
        "codex_execution_performed": False,
        "model_execution_performed": False,
        "github_execution_performed": False,
        "patch_application_performed": False,
        "validation_command_execution_performed": False,
        "external_execution_performed": False,
        "local_only": True,
        "recommended_preflight_artifact_path": str(
            (config.repo_root / ".aresforge" / "codex_execution" / "preflight" / "m159-preflight.json").resolve()
        ),
        "next_safe_action": "",
    }


def _readiness_checks(
    *,
    item: dict[str, Any],
    read_only_gate: dict[str, Any],
    autonomy_gate: dict[str, Any],
    autonomy_payload: dict[str, Any],
    worktree_payload: dict[str, Any],
    validation_payload: dict[str, Any],
    store: dict[str, Any],
    artifact_readiness: dict[str, Any],
    retry_policy: dict[str, Any],
    source_patch_policy: dict[str, Any],
    validation_profile: dict[str, Any],
) -> list[dict[str, Any]]:
    selected_controls = _controls(autonomy_payload)
    return [
        _check("dry_run_required", True, "Preflight is running in dry-run mode."),
        _check("queue_item_exists", bool(item), "Queue item exists in the local queue."),
        _check("read_only_machine_gate_passed", bool(read_only_gate.get("passed")), "Read-only machine gate passed."),
        _check(
            "operator_autonomy_machine_gate_passed",
            bool(autonomy_gate.get("passed")),
            "Operator autonomy profile machine gate passed.",
        ),
        _check(
            "autonomy_profile_allows_low_risk_codex",
            selected_controls.get("codex_low_risk_execution") == "enabled",
            "Selected autonomy profile must enable low-risk Codex execution for a future explicit command.",
        ),
        _check(
            "real_codex_command_still_separate",
            bool(autonomy_payload) and not bool(autonomy_payload.get("codex_execution_performed")),
            "Autonomy profile inspection did not execute Codex.",
        ),
        _check(
            "clean_worktree_for_real_codex",
            not bool(worktree_payload.get("dirty_tree_detected")),
            "Real Codex execution requires a clean worktree.",
        ),
        _check(
            "worktree_guard_ready",
            bool(worktree_payload.get("worktree_safe_for_future_real_codex_execution")),
            "Worktree guard must report future real Codex execution as safe to consider.",
        ),
        _check(
            "run_store_schema_ready",
            bool(store.get("ok")) and bool(store.get("schema_valid")),
            "Durable run store is readable and schema-valid.",
        ),
        _check(
            "artifact_capture_paths_present",
            bool(artifact_readiness.get("all_required_paths_present")),
            "Required local artifact capture roots are present.",
        ),
        _check(
            "validation_profile_selected",
            bool(validation_profile.get("profile_id")) and bool(validation_profile.get("validation_commands")),
            "Validation profile is selected with allowlisted commands.",
        ),
        _check(
            "validation_inspector_non_executing",
            not bool(validation_payload.get("validation_command_execution_performed")),
            "Validation profile inspector did not run validation commands.",
        ),
        _check(
            "automatic_retry_disabled",
            not bool(retry_policy.get("automatic_retry_allowed")),
            "Automatic retry loops are disabled.",
        ),
        _check(
            "source_patch_application_default_deny",
            not bool(source_patch_policy.get("source_patch_application_allowed")),
            "Source patch application remains default-deny.",
        ),
    ]


def _artifact_readiness(config: AppConfig) -> dict[str, Any]:
    entries = []
    for relative in _REQUIRED_ARTIFACT_PATHS:
        path = (config.repo_root / relative).resolve()
        entries.append(
            {
                "path": relative,
                "absolute_path": str(path),
                "exists": path.exists(),
                "is_directory": path.is_dir(),
                "is_file": path.is_file(),
            }
        )
    return {
        "required_paths": entries,
        "all_required_paths_present": all(bool(entry["exists"]) for entry in entries),
        "stdout_capture_required": True,
        "stderr_capture_required": True,
        "result_json_capture_required": True,
        "artifact_write_performed": False,
    }


def _run_store_readiness(store: dict[str, Any]) -> dict[str, Any]:
    return {
        "store_path": _text(store.get("store_path")),
        "ok": bool(store.get("ok")),
        "schema_valid": bool(store.get("schema_valid")),
        "bootstrap_performed": bool(store.get("bootstrap_performed")),
        "record_count": len(_dicts(store.get("records"))),
        "errors": _list(store.get("errors")),
        "warnings": _list(store.get("warnings")),
    }


def _validation_summary(payload: dict[str, Any], *, selected_profile: str) -> dict[str, Any]:
    profiles = _dicts(payload.get("validation_profiles"))
    selected = next((profile for profile in profiles if _text(profile.get("profile_id")) == selected_profile), {})
    commands = _list(selected.get("validation_commands"))
    if not commands:
        for candidate in _dicts(payload.get("recommended_validation_profiles")):
            if _text(candidate.get("profile_id")) == selected_profile:
                commands = _list(candidate.get("validation_commands"))
                break
    return {
        "profile_id": selected_profile,
        "selected_by_inspector": _text(payload.get("selected_profile")),
        "validation_commands": commands,
        "validation_commands_execute_in_preflight": False,
        "inspector_status": _text(payload.get("status")),
    }


def _retry_policy_summary() -> dict[str, Any]:
    return {
        "policy_id": "m159_preflight_no_automatic_retry",
        "automatic_retry_allowed": False,
        "max_retry_attempts": 0,
        "manual_retry_requires": [
            "classified failure artifact",
            "operator approval",
            "fresh preflight",
            "codex_dispatch machine gate",
        ],
        "safe_recovery_command": "classify-codex-failure --failure-artifact <artifact> --format json",
    }


def _source_patch_risk_policy() -> dict[str, Any]:
    return {
        "source_patch_application_allowed": False,
        "source_patch_apply_dry_run_allowed": True,
        "requires_risk_classification": True,
        "requires_apply_plan": True,
        "requires_git_apply_check": True,
        "source_patch_apply_command_runs_in_preflight": False,
        "blocked_operations": ["apply_source_patch_from_generated_output"],
    }


def _worktree_summary(payload: dict[str, Any]) -> dict[str, Any]:
    guard = payload.get("codex_execution_guard", {}) if isinstance(payload.get("codex_execution_guard"), dict) else {}
    worktree = guard.get("worktree_state", {}) if isinstance(guard.get("worktree_state"), dict) else {}
    return {
        "dirty_tree_detected": bool(payload.get("dirty_tree_detected")),
        "worktree_safe_for_future_real_codex_execution": bool(
            payload.get("worktree_safe_for_future_real_codex_execution")
        ),
        "status_line_count": _int(worktree.get("status_line_count")),
        "dirty_path_summary": worktree.get("dirty_path_summary", {}) if isinstance(worktree, dict) else {},
    }


def _component_summary(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "record_type": _text(payload.get("record_type")),
        "status": _text(payload.get("status")),
        "blocked": bool(payload.get("blocked")),
        "blocked_reasons": _list(payload.get("blocked_reasons")),
        "warnings": _list(payload.get("warnings")),
        "codex_execution_performed": bool(payload.get("codex_execution_performed")),
        "model_execution_performed": bool(payload.get("model_execution_performed")),
        "github_execution_performed": bool(payload.get("github_execution_performed")),
        "patch_application_performed": bool(payload.get("patch_application_performed")),
    }


def _blocked_reasons(checks: list[dict[str, Any]]) -> list[str]:
    return _dedupe(
        check["message"]
        for check in checks
        if not bool(check.get("passed")) and not bool(check.get("warning_only"))
    )


def _warnings(
    *,
    autonomy_payload: dict[str, Any],
    worktree_payload: dict[str, Any],
    validation_payload: dict[str, Any],
    retention_payload: dict[str, Any],
    store: dict[str, Any],
    item: dict[str, Any],
) -> list[str]:
    warnings = [
        *_list(autonomy_payload.get("warnings")),
        *_list(worktree_payload.get("warnings")),
        *_list(validation_payload.get("warnings")),
        *_list(retention_payload.get("warnings")),
        *_list(store.get("warnings")),
    ]
    if item and _text(item.get("status")) == "done":
        warnings.append("Queue item is already done; preflight remains useful as reproducible M159 evidence.")
    warnings.append("M159 generated preflight evidence only and did not execute Codex.")
    return _dedupe(warnings)


def _next_safe_action(*, blocked: bool) -> str:
    if blocked:
        return "Resolve preflight blockers before any explicit real Codex execution command."
    return "Real Codex may be considered only through a separate explicit low-risk command with required flags and captured validation evidence."


def _gate_payload(
    config: AppConfig,
    *,
    item_id: str,
    gate_profile: str,
    queue_path: str | Path | None,
) -> dict[str, Any]:
    result = evaluate_machine_safety_gates(
        config,
        item_id=item_id,
        gate_profile=gate_profile,
        queue_path=queue_path,
        output_format="json",
    )
    return result.get("payload", {}) if isinstance(result, dict) else {}


def _gate_summary(gate_payload: dict[str, Any]) -> dict[str, Any]:
    checks = gate_payload.get("checks", [])
    failed = [
        _text(check.get("check_id"))
        for check in checks
        if isinstance(check, dict) and not bool(check.get("passed")) and not bool(check.get("warning_only"))
    ]
    return {
        "gate_profile": _text(gate_payload.get("gate_profile")) or "read_only_agent",
        "passed": bool(gate_payload.get("passed")) and not bool(gate_payload.get("blocked")),
        "blocked": bool(gate_payload.get("blocked")),
        "blocked_reasons": _list(gate_payload.get("blocked_reasons")),
        "checks_failed": failed,
    }


def _controls(payload: dict[str, Any]) -> dict[str, str]:
    selected = payload.get("selected_profile", {}) if isinstance(payload.get("selected_profile"), dict) else {}
    return {
        _text(control.get("capability_id")): _text(control.get("status"))
        for control in _dicts(selected.get("capability_controls"))
    }


def _risk_class(item: dict[str, Any]) -> str:
    routing = item.get("routing_metadata", {}) if isinstance(item, dict) else {}
    if isinstance(routing, dict) and _text(routing.get("risk_level")):
        return _text(routing.get("risk_level"))
    tags = " ".join(_list(item.get("tags"))).lower() if isinstance(item, dict) else ""
    if "critical" in tags:
        return "critical"
    if "machine-gated" in tags or "codex" in tags or "orchestration" in tags:
        return "high"
    return "unknown"


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
        if isinstance(item, dict) and _text(item.get("item_id")) == item_id:
            return item
    return {}


def _payload(result: dict[str, Any]) -> dict[str, Any]:
    payload = result.get("payload", {}) if isinstance(result, dict) else {}
    return payload if isinstance(payload, dict) else {}


def _check(check_id: str, passed: bool, message: str, *, warning_only: bool = False) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "passed": bool(passed),
        "message": message,
        "warning_only": bool(warning_only),
    }


def _emit_or_write(
    *,
    config: AppConfig,
    payload: dict[str, Any],
    output: str | Path | None,
    force: bool,
    command_ok: bool,
) -> dict[str, Any]:
    if output is None:
        return {
            "command": COMMAND_NAME,
            "ok": bool(command_ok),
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
    artifact_payload["artifacts_created"] = _dedupe([*_list(payload.get("artifacts_created")), str(output_path)])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact_payload, indent=2) + "\n", encoding="utf-8")
    return {
        "command": COMMAND_NAME,
        "ok": bool(command_ok),
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


def _text(value: Any) -> str:
    return str(value or "").strip()


def _dicts(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [entry for entry in value if isinstance(entry, dict)]
    return []


def _list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [_text(entry) for entry in value if _text(entry)]
    if isinstance(value, tuple):
        return [_text(entry) for entry in value if _text(entry)]
    if value in (None, ""):
        return []
    return [_text(value)]


def _int(value: Any) -> int:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    text = _text(value)
    return int(text) if text.isdigit() else 0


def _dedupe(values: Any) -> list[str]:
    deduped: list[str] = []
    for value in values:
        text = _text(value)
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
