from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.agent_registry import build_agent_registry
from aresforge.operator.local_project_queue import resolve_project_queue_path
from aresforge.operator.machine_safety_gate_engine import evaluate_machine_safety_gates

COMMAND_NAME = "inspect-orchestrator-state-machine"
STATE_MACHINE_VERSION = "m140.1"
DEFAULT_ITEM_ID = "m140-orchestrator-execution-state-machine-v1"
DEFAULT_PROJECT_ID = "aresforge"

_TERMINAL_STATUSES: tuple[str, ...] = ("completed", "blocked", "failed", "cancelled")

_BOUNDARY_CONFIRMATIONS: tuple[str, ...] = (
    "M140 defines the durable orchestration run state machine and inspects it locally.",
    "M140 does not execute agents, Codex, local LLMs, GitHub, validation commands, patches, queue mutation, or follow-on work.",
    "Every future executable transition must pass its declared machine gate before entering an execution state.",
    "Real Codex execution remains default-deny and requires a later explicit gated execution command.",
)


def inspect_orchestrator_state_machine(
    config: AppConfig,
    *,
    item_id: str = DEFAULT_ITEM_ID,
    project_id: str = DEFAULT_PROJECT_ID,
    queue_path: str | Path | None = None,
    output: str | Path | None = None,
    force: bool = False,
    output_format: str = "json",
) -> dict[str, Any]:
    fmt = str(output_format or "json").strip().lower()
    if fmt != "json":
        return _error("invalid_format", {"format": output_format, "supported_formats": ["json"]})

    normalized_item_id = str(item_id or DEFAULT_ITEM_ID).strip() or DEFAULT_ITEM_ID
    normalized_project_id = str(project_id or DEFAULT_PROJECT_ID).strip() or DEFAULT_PROJECT_ID
    queue = _load_queue(config, queue_path=queue_path)
    item = _find_item(queue, normalized_item_id)
    gate_result = evaluate_machine_safety_gates(
        config,
        item_id=normalized_item_id,
        gate_profile="read_only_agent",
        queue_path=queue_path,
        output_format="json",
    )
    gate_payload = gate_result.get("payload", {}) if isinstance(gate_result, dict) else {}
    gate_summary = _gate_summary(gate_payload)
    warnings = _warnings(item=item, gate_payload=gate_payload, project_id=normalized_project_id)
    blocked_reasons = _blocked_reasons(item=item, gate_payload=gate_payload)
    blocked = bool(blocked_reasons)

    payload: dict[str, Any] = {
        "record_type": "orchestrator_execution_state_machine_v1",
        "artifact_type": "orchestrator_execution_state_machine_v1",
        "state_machine_version": STATE_MACHINE_VERSION,
        "generated": True,
        "generated_at": _now_iso(),
        "item_id": normalized_item_id,
        "project_id": normalized_project_id,
        "run_id": f"{normalized_item_id}:state-machine-v1",
        "status": "blocked" if blocked else "ready",
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
        "next_safe_action": _next_safe_action(blocked=blocked),
        "queue_item_found": bool(item),
        "queue_item_status": str(item.get("status", "")).strip(),
        "queue_path": str(resolve_project_queue_path(config.repo_root, queue_path)),
        "state_machine": _state_machine(),
        "checkpoints": _checkpoints(),
        "validation_boundaries": _validation_boundaries(),
        "terminal_statuses": list(_TERMINAL_STATUSES),
        "agent_runtime_summary": _agent_runtime_summary(config),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
        "recommended_state_artifact_path": str(
            (config.repo_root / ".aresforge" / "orchestrator" / "execution_state_machine_v1.json").resolve()
        ),
    }
    return _emit_or_write(config=config, payload=payload, output=output, force=force)


def _state_machine() -> dict[str, Any]:
    states = [
        _state("created", "Run record exists but no plan has been loaded.", terminal=False),
        _state("queued", "Queue item and dependencies have been inspected.", terminal=False),
        _state("planning", "An orchestration plan is loaded or generated.", terminal=False),
        _state("gate_check", "The next transition is being evaluated by a machine safety gate.", terminal=False),
        _state("checkpoint", "Durable checkpoint state has been written before a risky boundary.", terminal=False),
        _state("step_dispatch", "A gated step has been selected for a dry-run or allowed executor.", terminal=False),
        _state("step_running", "A permitted local step executor is running.", terminal=False),
        _state("validation", "Local validation evidence is being collected or inspected.", terminal=False),
        _state("recovery", "A blocked, failed, or interrupted run is being inspected for safe resume.", terminal=False),
        _state("completed", "All selected steps completed and validation boundaries are satisfied.", terminal=True),
        _state("blocked", "A required gate, checkpoint, dependency, or policy check blocked progress.", terminal=True),
        _state("failed", "An allowed executor returned a failure that requires review.", terminal=True),
        _state("cancelled", "The operator explicitly cancelled the run.", terminal=True),
    ]
    transitions = [
        _transition("created", "queued", "queue_item_loaded", "read_only_agent", "queue_snapshot"),
        _transition("queued", "planning", "plan_loaded_or_built", "read_only_agent", "plan_snapshot"),
        _transition("planning", "gate_check", "next_step_selected", "read_only_agent", "step_selection"),
        _transition("gate_check", "checkpoint", "gate_passed", "step_declared_profile", "pre_step_checkpoint"),
        _transition("gate_check", "blocked", "gate_blocked", "step_declared_profile", "blocked_checkpoint"),
        _transition("checkpoint", "step_dispatch", "checkpoint_written", "local_artifact_write", "checkpoint_integrity"),
        _transition("step_dispatch", "step_running", "executor_allowed", "step_declared_profile", "executor_boundary"),
        _transition("step_dispatch", "blocked", "executor_default_denied", "step_declared_profile", "blocked_checkpoint"),
        _transition("step_running", "validation", "step_completed", "local_artifact_write", "post_step_checkpoint"),
        _transition("step_running", "failed", "step_failed", "local_artifact_write", "failure_checkpoint"),
        _transition("validation", "planning", "more_steps_remain", "read_only_agent", "validation_checkpoint"),
        _transition("validation", "completed", "all_steps_validated", "read_only_agent", "completion_checkpoint"),
        _transition("blocked", "recovery", "operator_requests_recovery_plan", "read_only_agent", "recovery_snapshot"),
        _transition("failed", "recovery", "operator_requests_recovery_plan", "read_only_agent", "recovery_snapshot"),
        _transition("recovery", "planning", "resume_checkpoint_validated", "read_only_agent", "resume_checkpoint"),
        _transition("recovery", "cancelled", "operator_cancels_run", "read_only_agent", "cancel_checkpoint"),
    ]
    return {
        "initial_state": "created",
        "states": states,
        "transitions": transitions,
        "resume_supported": True,
        "rollback_model": "checkpoint-first; resume only from validated checkpoints; no automatic rollback mutation in M140",
    }


def _checkpoints() -> list[dict[str, Any]]:
    return [
        {
            "checkpoint_id": "queue_snapshot",
            "state": "queued",
            "required_fields": ["item_id", "project_id", "queue_item_status", "dependencies"],
            "artifact_scope": ".aresforge/orchestrator",
            "validation_boundary": "queue_dependency_boundary",
        },
        {
            "checkpoint_id": "plan_snapshot",
            "state": "planning",
            "required_fields": ["plan_id", "steps_total", "step_ids", "agent_ids"],
            "artifact_scope": "artifacts/orchestration",
            "validation_boundary": "plan_integrity_boundary",
        },
        {
            "checkpoint_id": "pre_step_checkpoint",
            "state": "checkpoint",
            "required_fields": ["step_id", "agent_id", "machine_gate_profile", "machine_gate_result"],
            "artifact_scope": ".aresforge/orchestrator/runs",
            "validation_boundary": "machine_gate_boundary",
        },
        {
            "checkpoint_id": "post_step_checkpoint",
            "state": "validation",
            "required_fields": ["step_id", "status", "artifacts_created", "execution_flags"],
            "artifact_scope": ".aresforge/orchestrator/runs",
            "validation_boundary": "post_step_validation_boundary",
        },
        {
            "checkpoint_id": "terminal_checkpoint",
            "state": "completed|blocked|failed|cancelled",
            "required_fields": ["run_id", "terminal_status", "blocked_reasons", "next_safe_action"],
            "artifact_scope": ".aresforge/orchestrator/runs",
            "validation_boundary": "terminal_status_boundary",
        },
    ]


def _validation_boundaries() -> list[dict[str, Any]]:
    return [
        _boundary("queue_dependency_boundary", "read_only_agent", "Queue item must exist and dependencies must be done before planning."),
        _boundary("plan_integrity_boundary", "read_only_agent", "Plan steps must be stable, ordered, and locally inspectable."),
        _boundary("machine_gate_boundary", "step_declared_profile", "Every execution or artifact transition must pass its declared machine gate."),
        _boundary("external_execution_boundary", "codex_dispatch|github_sync", "Codex and GitHub remain default-deny unless an explicit future command supplies flags and passes gates."),
        _boundary("model_execution_boundary", "local_llm_execution", "Local model execution remains advisory-only and must pass the local LLM execution gate."),
        _boundary("patch_application_boundary", "docs_only_patch_apply", "Patch application is limited to docs-only Markdown paths and dedicated apply commands."),
        _boundary("terminal_status_boundary", "read_only_agent", "Terminal status must include blockers, warnings, artifacts, and the next safe action."),
    ]


def _state(state_id: str, description: str, *, terminal: bool) -> dict[str, Any]:
    return {"state": state_id, "description": description, "terminal": bool(terminal)}


def _transition(
    from_state: str,
    to_state: str,
    trigger: str,
    gate_profile: str,
    checkpoint: str,
) -> dict[str, Any]:
    return {
        "from_state": from_state,
        "to_state": to_state,
        "trigger": trigger,
        "machine_gate_profile": gate_profile,
        "checkpoint_required": checkpoint,
    }


def _boundary(boundary_id: str, gate_profile: str, description: str) -> dict[str, Any]:
    return {
        "boundary_id": boundary_id,
        "machine_gate_profile": gate_profile,
        "description": description,
        "bypass_allowed": False,
    }


def _agent_runtime_summary(config: AppConfig) -> dict[str, Any]:
    registry = build_agent_registry(config)
    return {
        "agent_registry_version": str(registry.get("agent_registry_version", "")),
        "agent_count": int(registry.get("agent_count", 0)),
        "executable_agents": _list(registry.get("executable_agents")),
        "dry_run_only_agents": _list(registry.get("dry_run_only_agents")),
    }


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


def _warnings(*, item: dict[str, Any], gate_payload: dict[str, Any], project_id: str) -> list[str]:
    warnings = _list(gate_payload.get("warnings"))
    if item and str(item.get("project_id", "")).strip() != project_id:
        warnings.append("Queue item project_id does not match the requested project_id.")
    return sorted(set(warnings))


def _blocked_reasons(*, item: dict[str, Any], gate_payload: dict[str, Any]) -> list[str]:
    reasons = _list(gate_payload.get("blocked_reasons"))
    if not item:
        reasons.append("Queue item must exist before this state machine can be used as a durable run contract.")
    return _dedupe(reasons)


def _next_safe_action(*, blocked: bool) -> str:
    if blocked:
        return "Resolve the read-only machine gate blockers before starting or resuming orchestration."
    return "Use this state machine as the durable run contract; execute only through explicit gated orchestration commands."


def _load_queue(config: AppConfig, *, queue_path: str | Path | None) -> dict[str, Any]:
    path = resolve_project_queue_path(config.repo_root, queue_path)
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
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
        rendered = json.dumps(payload, indent=2)
        return {
            "command": COMMAND_NAME,
            "ok": not bool(payload.get("blocked")),
            "local_only": True,
            "format": "json",
            "wrote_output_file": False,
            "stdout": rendered,
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
        rendered = json.dumps(blocked, indent=2)
        return {
            "command": COMMAND_NAME,
            "ok": False,
            "local_only": True,
            "format": "json",
            "output": str(output_path),
            "force": force,
            "wrote_output_file": False,
            "stdout": rendered,
            "payload": blocked,
        }

    artifact_payload = dict(payload)
    artifact_payload["artifacts_created"] = [str(output_path)]
    rendered = json.dumps(artifact_payload, indent=2)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered + "\n", encoding="utf-8")
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
