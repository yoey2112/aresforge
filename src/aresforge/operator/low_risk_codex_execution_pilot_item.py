from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import subprocess
from typing import Any, Callable

from aresforge.config import AppConfig
from aresforge.operator.end_to_end_codex_loop_dry_run import run_end_to_end_codex_loop_dry_run
from aresforge.operator.local_project_queue import resolve_project_queue_path
from aresforge.operator.real_codex_execution_preflight_hardening import preflight_real_codex_execution

COMMAND_NAME = "prepare-low-risk-codex-pilot"
RECORD_TYPE = "low_risk_codex_execution_pilot_item_v1"
PILOT_VERSION = "m160.1"
DEFAULT_ITEM_ID = "m160-low-risk-codex-execution-pilot-item"
DEFAULT_PROJECT_ID = "aresforge"
DEFAULT_AUTONOMY_PROFILE = "codex_low_risk_enabled"
DEFAULT_VALIDATION_PROFILE = "queue_system"
DEFAULT_CODEX_COMMAND = ("codex", "exec")

CommandRunner = Callable[..., subprocess.CompletedProcess[Any]]

_LOW_RISK_TAGS: tuple[str, ...] = (
    "risk:low",
    "low-risk-code",
    "low-risk-codex-pilot",
)

_LOW_RISK_ALLOWED_PREFIXES: tuple[str, ...] = (
    "src/",
    "tests/",
    "docs/",
)

_LOW_RISK_BLOCKED_PREFIXES: tuple[str, ...] = (
    ".github/",
    ".aresforge/queue/",
    "migrations/",
    "scripts/",
    "src/aresforge/operator/codex",
    "src/aresforge/operator/orchestr",
    "src/aresforge/operator/agent",
    "src/aresforge/hub/",
)

_LOW_RISK_BLOCKED_EXACT: tuple[str, ...] = (
    "pyproject.toml",
    "docker-compose.yml",
    "requirements.txt",
    "requirements-dev.txt",
    "setup.py",
    "setup.cfg",
)

_PROHIBITED_OPERATIONS: tuple[str, ...] = (
    "merge_pull_request",
    "force_push",
    "update_protected_branch",
    "enable_auto_merge",
    "create_release",
    "modify_github_workflow",
    "github_push_or_merge_automation",
    "apply_source_patch_from_generated_output",
    "queue_completion_from_pilot",
    "automatic_retry_loop",
    "automatic_next_item_execution",
    "bypass_machine_safety_gate",
)

_BOUNDARY_CONFIRMATIONS: tuple[str, ...] = (
    "M160 prepares one low-risk Codex pilot item and is dry-run by default.",
    "Real Codex execution requires explicit execution flags, low-risk scope, clean preflight evidence, and machine gates.",
    "M160 composes M159 real-Codex preflight and the M152 low-risk Codex loop instead of bypassing existing controls.",
    "M160 stops before GitHub push, PR merge, protected branch updates, releases, queue completion, source patch application, retry, or next-item execution.",
)


def prepare_low_risk_codex_pilot(
    config: AppConfig,
    *,
    item_id: str = DEFAULT_ITEM_ID,
    project_id: str = DEFAULT_PROJECT_ID,
    dry_run: bool = True,
    execution_enabled: bool = False,
    allow_low_risk_code: bool = False,
    autonomy_profile: str | None = None,
    validation_profile: str = DEFAULT_VALIDATION_PROFILE,
    changed_paths: list[str] | tuple[str, ...] | None = None,
    codex_command: list[str] | tuple[str, ...] | None = None,
    timeout_seconds: int | None = None,
    queue_path: str | Path | None = None,
    history_path: str | Path | None = None,
    output: str | Path | None = None,
    force: bool = False,
    output_format: str = "json",
    preflight_command_runner: CommandRunner | None = None,
    codex_command_runner: CommandRunner | None = None,
    validation_command_runner: Any | None = None,
) -> dict[str, Any]:
    fmt = _text(output_format).lower() or "json"
    if fmt != "json":
        return _error("invalid_format", {"format": output_format, "supported_formats": ["json"]})

    normalized_item_id = _text(item_id) or DEFAULT_ITEM_ID
    normalized_project_id = _text(project_id) or DEFAULT_PROJECT_ID
    selected_autonomy_profile = _text(autonomy_profile) or DEFAULT_AUTONOMY_PROFILE
    selected_validation_profile = _text(validation_profile) or DEFAULT_VALIDATION_PROFILE
    normalized_changed_paths = _normalize_paths(changed_paths or [])
    real_execution_requested = bool(execution_enabled or allow_low_risk_code or (not dry_run and normalized_changed_paths))
    effective_dry_run = bool(dry_run or not real_execution_requested)
    run_id = f"{_safe_id(normalized_item_id)}-pilot-{datetime.now(UTC).strftime('%Y%m%dT%H%M%S%fZ')}"

    queue = _load_queue(config, queue_path=queue_path)
    item = _find_item(queue, normalized_item_id)
    low_risk_gate = _low_risk_gate(
        queue=queue,
        item=item,
        changed_paths=normalized_changed_paths,
        real_execution_requested=real_execution_requested,
        execution_enabled=execution_enabled,
        allow_low_risk_code=allow_low_risk_code,
    )

    preflight_result = preflight_real_codex_execution(
        config,
        item_id=normalized_item_id,
        project_id=normalized_project_id,
        dry_run=True,
        autonomy_profile=selected_autonomy_profile,
        validation_profile=selected_validation_profile,
        changed_paths=normalized_changed_paths,
        queue_path=queue_path,
        history_path=history_path,
        output_format="json",
        command_runner=preflight_command_runner,
    )
    preflight_payload = _payload(preflight_result)
    preflight_decision = _preflight_decision(preflight_result, preflight_payload)

    pilot_reasons: list[str] = []
    pilot_reasons.extend(_list(low_risk_gate.get("blocked_reasons")))
    if real_execution_requested and not execution_enabled:
        pilot_reasons.append("Real pilot execution requires --execution-enabled.")
    if real_execution_requested and not allow_low_risk_code:
        pilot_reasons.append("Real pilot execution requires --allow-low-risk-code.")
    if real_execution_requested and preflight_payload.get("blocked") is True:
        pilot_reasons.append("M159 real Codex preflight blocked real pilot execution.")
        pilot_reasons.extend(_list(preflight_payload.get("blocked_reasons")))
    if real_execution_requested and preflight_payload.get("real_codex_execution_preflight_passed") is not True:
        pilot_reasons.append("M159 preflight did not report real_codex_execution_preflight_passed=true.")

    pilot_loop_result: dict[str, Any] = {}
    pilot_loop_payload: dict[str, Any] = {}
    execution_attempted = False
    if effective_dry_run or not pilot_reasons:
        execution_attempted = True
        pilot_loop_result = run_end_to_end_codex_loop_dry_run(
            config,
            item_id=normalized_item_id,
            project_id=normalized_project_id,
            dry_run=effective_dry_run,
            execution_enabled=bool(execution_enabled and not effective_dry_run),
            allow_low_risk_code=bool(allow_low_risk_code and not effective_dry_run),
            codex_command=_normalize_command(codex_command),
            changed_paths=normalized_changed_paths,
            timeout_seconds=timeout_seconds,
            validation_profile=selected_validation_profile,
            queue_path=queue_path,
            force=True,
            output_format="json",
            codex_command_runner=codex_command_runner,
            validation_command_runner=validation_command_runner,
        )
        pilot_loop_payload = _payload(pilot_loop_result)
        if real_execution_requested and not effective_dry_run:
            if pilot_loop_result.get("ok") is not True or pilot_loop_payload.get("blocked") is True:
                pilot_reasons.append("Low-risk Codex pilot loop did not pass.")
                pilot_reasons.extend(_list(pilot_loop_payload.get("blocked_reasons")))

    blocked = bool(pilot_reasons) or bool(preflight_payload.get("blocked"))
    if effective_dry_run and not _list(low_risk_gate.get("blocked_reasons")):
        command_ok = True
    else:
        command_ok = not bool(pilot_reasons) and not bool(pilot_loop_payload.get("blocked"))

    machine_gates = _machine_gates(
        low_risk_gate=low_risk_gate,
        preflight_payload=preflight_payload,
        pilot_loop_payload=pilot_loop_payload,
    )
    artifacts_created = _dedupe(
        [
            *_list(pilot_loop_payload.get("artifacts_created")),
            *_list(preflight_payload.get("artifacts_created")),
        ]
    )
    codex_execution_performed = bool(pilot_loop_payload.get("codex_execution_performed"))
    validation_command_execution_performed = bool(pilot_loop_payload.get("validation_command_execution_performed"))

    payload: dict[str, Any] = {
        "record_type": RECORD_TYPE,
        "artifact_type": RECORD_TYPE,
        "pilot_version": PILOT_VERSION,
        "generated": True,
        "generated_at": _now_iso(),
        "project_id": normalized_project_id,
        "item_id": normalized_item_id,
        "run_id": run_id,
        "status": _status(
            effective_dry_run=effective_dry_run,
            real_execution_requested=real_execution_requested,
            blocked=blocked,
            pilot_reasons=pilot_reasons,
            loop_payload=pilot_loop_payload,
        ),
        "blocked": blocked,
        "blocked_reasons": _dedupe([*pilot_reasons, *([] if not effective_dry_run else _list(preflight_payload.get("blocked_reasons")))]),
        "warnings": _warnings(
            item=item,
            low_risk_gate=low_risk_gate,
            preflight_payload=preflight_payload,
            pilot_loop_payload=pilot_loop_payload,
            effective_dry_run=effective_dry_run,
        ),
        "machine_gates_checked": machine_gates,
        "machine_gates_passed": bool(machine_gates) and all(bool(gate.get("passed")) for gate in machine_gates),
        "autonomy_profile": selected_autonomy_profile,
        "artifacts_created": artifacts_created,
        "mutation_performed": False,
        "queue_mutation_performed": False,
        "codex_execution_performed": codex_execution_performed,
        "model_execution_performed": False,
        "github_execution_performed": False,
        "patch_application_performed": False,
        "validation_command_execution_performed": validation_command_execution_performed,
        "external_execution_performed": bool(pilot_loop_payload.get("external_execution_performed")),
        "local_only": True,
        "next_safe_action": _next_safe_action(
            effective_dry_run=effective_dry_run,
            real_execution_requested=real_execution_requested,
            blocked=blocked,
            codex_execution_performed=codex_execution_performed,
        ),
        "dry_run": effective_dry_run,
        "dry_run_defaulted": not real_execution_requested,
        "execution_enabled": bool(execution_enabled),
        "allow_low_risk_code": bool(allow_low_risk_code),
        "real_execution_requested": real_execution_requested,
        "real_execution_allowed": bool(
            real_execution_requested
            and not effective_dry_run
            and not pilot_reasons
            and preflight_payload.get("real_codex_execution_preflight_passed") is True
            and low_risk_gate.get("passed") is True
        ),
        "pilot_item_prepared": True,
        "pilot_execution_attempted": execution_attempted,
        "pilot_execution_performed": codex_execution_performed,
        "codex_execution_would_be_blocked": blocked and not codex_execution_performed,
        "queue_item_found": bool(item),
        "queue_item_status": _text(item.get("status")),
        "queue_path": str(resolve_project_queue_path(config.repo_root, queue_path)),
        "changed_paths_declared": normalized_changed_paths,
        "changed_path_scope_declared": bool(normalized_changed_paths),
        "codex_command": _normalize_command(codex_command),
        "validation_profile": selected_validation_profile,
        "low_risk_verification": low_risk_gate,
        "preflight_decisions": preflight_decision,
        "pilot_loop_result": _loop_summary(pilot_loop_result, pilot_loop_payload),
        "github_stop_boundary": {
            "github_execution_performed": False,
            "push_performed": False,
            "pull_request_created": False,
            "pull_request_merged": False,
            "protected_branch_updated": False,
            "next_safe_action": "Review local pilot evidence; any GitHub sync remains a separate explicit gated workflow.",
        },
        "prohibited_operations": list(_PROHIBITED_OPERATIONS),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }
    return _emit_or_write(config=config, payload=payload, output=output, force=force, command_ok=command_ok)


def _low_risk_gate(
    *,
    queue: dict[str, Any],
    item: dict[str, Any],
    changed_paths: list[str],
    real_execution_requested: bool,
    execution_enabled: bool,
    allow_low_risk_code: bool,
) -> dict[str, Any]:
    blocked_reasons: list[str] = []
    warnings: list[str] = []
    tags = set(_list(item.get("tags"))) if item else set()

    if not item:
        blocked_reasons.append("Pilot queue item must exist before a low-risk Codex pilot can be prepared.")
    if item and not tags.intersection(_LOW_RISK_TAGS):
        blocked_reasons.append("Pilot queue item must declare risk:low, low-risk-code, or low-risk-codex-pilot.")
    if item and not _dependencies_done(queue, item):
        blocked_reasons.append("Pilot queue item dependencies must be done and blocked_by must be empty.")

    if real_execution_requested:
        if not execution_enabled:
            blocked_reasons.append("Real pilot execution requires --execution-enabled.")
        if not allow_low_risk_code:
            blocked_reasons.append("Real pilot execution requires --allow-low-risk-code.")
        if not changed_paths:
            blocked_reasons.append("Real pilot execution requires at least one --changed-path.")
        blocked_reasons.extend(_blocked_changed_paths(changed_paths))
    elif not changed_paths:
        warnings.append("No changed paths were declared; dry-run preparation remains non-executing.")
    else:
        blocked_reasons.extend(_blocked_changed_paths(changed_paths))

    blocked = bool(blocked_reasons)
    return {
        "gate_profile": "low_risk_codex_pilot_scope",
        "passed": not blocked,
        "blocked": blocked,
        "blocked_reasons": _dedupe(blocked_reasons),
        "warnings": _dedupe(warnings),
        "checks_failed": ["low_risk_pilot_scope"] if blocked else [],
        "item_tags": sorted(tags),
        "changed_paths": changed_paths,
        "allowed_prefixes": list(_LOW_RISK_ALLOWED_PREFIXES),
        "blocked_prefixes": list(_LOW_RISK_BLOCKED_PREFIXES),
        "real_execution_requested": real_execution_requested,
    }


def _dependencies_done(queue: dict[str, Any], item: dict[str, Any]) -> bool:
    if _list(item.get("blocked_by")):
        return False
    by_id = {
        _text(candidate.get("item_id")): candidate
        for candidate in queue.get("work_items", [])
        if isinstance(candidate, dict)
    }
    for dependency in [*_list(item.get("dependencies")), *_list(item.get("depends_on"))]:
        if _text(by_id.get(dependency, {}).get("status")) != "done":
            return False
    return True


def _blocked_changed_paths(paths: list[str]) -> list[str]:
    reasons: list[str] = []
    for path in paths:
        normalized = path.replace("\\", "/").lstrip("/")
        if normalized in _LOW_RISK_BLOCKED_EXACT or any(
            normalized.startswith(prefix) for prefix in _LOW_RISK_BLOCKED_PREFIXES
        ):
            reasons.append(f"Path is outside the M160 low-risk Codex pilot scope: {normalized}")
            continue
        if any(normalized.startswith(prefix) for prefix in _LOW_RISK_ALLOWED_PREFIXES):
            continue
        reasons.append(f"Path is outside the M160 low-risk Codex pilot scope: {normalized}")
    return _dedupe(reasons)


def _preflight_decision(result: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "command": result.get("command", "preflight-real-codex-execution"),
        "ok": bool(result.get("ok")),
        "record_type": _text(payload.get("record_type")),
        "status": _text(payload.get("status")),
        "blocked": bool(payload.get("blocked")),
        "blocked_reasons": _list(payload.get("blocked_reasons")),
        "warnings": _list(payload.get("warnings")),
        "machine_gates_checked": payload.get("machine_gates_checked", []),
        "machine_gates_passed": bool(payload.get("machine_gates_passed")),
        "real_codex_execution_preflight_passed": bool(payload.get("real_codex_execution_preflight_passed")),
        "codex_execution_performed": bool(payload.get("codex_execution_performed")),
        "model_execution_performed": bool(payload.get("model_execution_performed")),
        "github_execution_performed": bool(payload.get("github_execution_performed")),
        "patch_application_performed": bool(payload.get("patch_application_performed")),
        "next_safe_action": _text(payload.get("next_safe_action")),
    }


def _loop_summary(result: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    if not payload:
        return {
            "attempted": False,
            "ok": False,
            "record_type": "",
            "status": "not_run",
            "blocked": False,
            "blocked_reasons": [],
            "codex_execution_performed": False,
        }
    return {
        "attempted": True,
        "ok": bool(result.get("ok")),
        "record_type": _text(payload.get("record_type")),
        "status": _text(payload.get("status")),
        "blocked": bool(payload.get("blocked")),
        "blocked_reasons": _list(payload.get("blocked_reasons")),
        "warnings": _list(payload.get("warnings")),
        "machine_gates_checked": payload.get("machine_gates_checked", []),
        "machine_gates_passed": bool(payload.get("machine_gates_passed")),
        "artifacts_created": _list(payload.get("artifacts_created")),
        "codex_execution_performed": bool(payload.get("codex_execution_performed")),
        "validation_command_execution_performed": bool(payload.get("validation_command_execution_performed")),
        "github_execution_performed": bool(payload.get("github_execution_performed")),
        "patch_application_performed": bool(payload.get("patch_application_performed")),
        "queue_mutation_performed": bool(payload.get("queue_mutation_performed")),
        "next_safe_action": _text(payload.get("next_safe_action")),
    }


def _machine_gates(
    *,
    low_risk_gate: dict[str, Any],
    preflight_payload: dict[str, Any],
    pilot_loop_payload: dict[str, Any],
) -> list[dict[str, Any]]:
    gates = [low_risk_gate]
    for gate in _dicts(preflight_payload.get("machine_gates_checked")):
        gates.append(dict(gate, source="preflight-real-codex-execution"))
    for gate in _dicts(pilot_loop_payload.get("machine_gates_checked")):
        gates.append(dict(gate, source="run-end-to-end-codex-loop"))
    return gates


def _warnings(
    *,
    item: dict[str, Any],
    low_risk_gate: dict[str, Any],
    preflight_payload: dict[str, Any],
    pilot_loop_payload: dict[str, Any],
    effective_dry_run: bool,
) -> list[str]:
    warnings = [
        *_list(low_risk_gate.get("warnings")),
        *_list(preflight_payload.get("warnings")),
        *_list(pilot_loop_payload.get("warnings")),
    ]
    if item and _text(item.get("status")) == "done":
        warnings.append("Pilot queue item is already done; command remains valid as reproducible M160 evidence.")
    if effective_dry_run:
        warnings.append("M160 dry-run did not invoke real Codex.")
    return _dedupe(warnings)


def _status(
    *,
    effective_dry_run: bool,
    real_execution_requested: bool,
    blocked: bool,
    pilot_reasons: list[str],
    loop_payload: dict[str, Any],
) -> str:
    if effective_dry_run and blocked:
        return "dry_run_prepared_real_execution_blocked"
    if effective_dry_run:
        return "dry_run_prepared"
    if pilot_reasons or blocked:
        return "blocked"
    if loop_payload.get("codex_execution_performed") is True:
        return "real_pilot_validated"
    if real_execution_requested:
        return "real_pilot_prepared_needs_review"
    return "dry_run_prepared"


def _next_safe_action(
    *,
    effective_dry_run: bool,
    real_execution_requested: bool,
    blocked: bool,
    codex_execution_performed: bool,
) -> str:
    if effective_dry_run and blocked:
        return "Review dry-run and preflight blockers before any explicit real low-risk Codex pilot execution."
    if effective_dry_run:
        return "Review local pilot artifacts; real execution requires explicit flags, low-risk changed paths, and passing preflight."
    if blocked:
        return "Resolve pilot blockers before retrying real execution."
    if codex_execution_performed:
        return "Review captured local Codex and validation artifacts; stop before GitHub push, merge, or queue completion."
    return "Review pilot preparation evidence before any further explicit gated action."


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


def _normalize_command(value: list[str] | tuple[str, ...] | None) -> list[str]:
    parts = [_text(part) for part in (value or DEFAULT_CODEX_COMMAND) if _text(part)]
    return parts or list(DEFAULT_CODEX_COMMAND)


def _normalize_paths(values: list[str] | tuple[str, ...]) -> list[str]:
    return _dedupe([_text(value).replace("\\", "/").lstrip("/") for value in values if _text(value)])


def _safe_id(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in _text(value).lower())
    return cleaned.strip("-") or "low-risk-codex-pilot"


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
