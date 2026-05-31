from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.agent_registry import build_agent_registry
from aresforge.operator.llm_decision_policy import recommend_llm_decision
from aresforge.operator.local_project_queue import resolve_project_queue_path
from aresforge.operator.machine_safety_gate_engine import evaluate_machine_safety_gates
from aresforge.operator.orchestration_run_history import (
    inspect_orchestration_run_history,
    resolve_orchestration_history_path,
)

COMMAND_NAME = "inspect-orchestration-resume-plan"
RECORD_TYPE = "orchestrator_resume_from_failure_plan_v1"
RESUME_PLAN_VERSION = "m147.1"
DEFAULT_ITEM_ID = "m147-orchestrator-resume-from-failure"
DEFAULT_PROJECT_ID = "aresforge"

_RECOVERABLE_STATUSES = frozenset({"max_steps_reached", "interrupted", "running"})
_REVIEW_REQUIRED_STATUSES = frozenset({"blocked", "failed"})
_TERMINAL_STATUSES = frozenset({"completed", "cancelled"})

_PROHIBITED_OPERATIONS: tuple[str, ...] = (
    "merge_pull_request",
    "force_push",
    "update_protected_branch",
    "enable_auto_merge",
    "create_release",
    "modify_github_workflow",
    "bypass_machine_safety_gate",
    "automatic_retry_loop",
    "automatic_next_item_execution",
    "execute_codex_without_explicit_allow_flag",
    "apply_source_patch_from_generated_output",
)

_BOUNDARY_CONFIRMATIONS: tuple[str, ...] = (
    "M147 inspects local orchestration history and builds a resume-from-failure plan.",
    "M147 validates checkpoint evidence before recommending any future resume action.",
    "M147 performs no agent, Codex, model, GitHub, patch, validation-command, queue, retry, or resume execution.",
    "Any future resume remains a separate explicit machine-gated orchestration command.",
)


def inspect_orchestration_resume_plan(
    config: AppConfig,
    *,
    run_id: str,
    item_id: str = DEFAULT_ITEM_ID,
    project_id: str = DEFAULT_PROJECT_ID,
    queue_path: str | Path | None = None,
    history_path: str | Path | None = None,
    artifacts_root: str | Path | None = None,
    output: str | Path | None = None,
    force: bool = False,
    output_format: str = "json",
) -> dict[str, Any]:
    fmt = str(output_format or "json").strip().lower()
    if fmt != "json":
        return _error("invalid_format", {"format": output_format, "supported_formats": ["json"]})

    normalized_run_id = str(run_id or "").strip()
    normalized_item_id = str(item_id or DEFAULT_ITEM_ID).strip() or DEFAULT_ITEM_ID
    normalized_project_id = str(project_id or DEFAULT_PROJECT_ID).strip() or DEFAULT_PROJECT_ID
    if not normalized_run_id:
        return _error("invalid_run_id", {"message": "run_id is required."})

    history_result = inspect_orchestration_run_history(
        config,
        project_id=normalized_project_id,
        item_id=None,
        run_id=normalized_run_id,
        queue_path=queue_path,
        history_path=history_path,
        artifacts_root=artifacts_root,
        output=None,
        force=False,
        output_format="json",
    )
    history_payload = history_result.get("payload", {}) if isinstance(history_result, dict) else {}
    source_record = _latest_record(history_payload)
    source_run = _load_source_run(source_record)
    effective_item_id = _first_text(source_record.get("item_id"), source_run.get("item_id"), normalized_item_id)
    effective_project_id = _first_text(source_record.get("project_id"), source_run.get("project_id"), normalized_project_id)

    gate_payload = _gate_payload(config, item_id=normalized_item_id, queue_path=queue_path)
    gate_summary = _gate_summary(gate_payload, source="resume_plan_inspection")
    checkpoint = _last_valid_checkpoint(source_record, source_run)
    source_flags = _source_execution_flags(source_record, source_run)
    validation_required = _validation_required_before_resume(source_flags)
    source_gates_passed = _source_machine_gates_passed(source_record, source_run)
    machine_gates_passed = bool(gate_summary.get("passed")) and source_gates_passed
    warnings = _warnings(
        history_payload=history_payload,
        source_record=source_record,
        source_run=source_run,
        checkpoint=checkpoint,
        source_flags=source_flags,
        validation_required=validation_required,
    )
    blocked_reasons = _dedupe(_list(gate_payload.get("blocked_reasons")))
    blocked = bool(blocked_reasons)
    resume_analysis = _resume_analysis(
        source_record=source_record,
        source_run=source_run,
        checkpoint=checkpoint,
        validation_required=validation_required,
        machine_gates_passed=machine_gates_passed,
        blocked=blocked,
    )

    payload: dict[str, Any] = {
        "record_type": RECORD_TYPE,
        "artifact_type": RECORD_TYPE,
        "resume_plan_version": RESUME_PLAN_VERSION,
        "generated": True,
        "generated_at": _now_iso(),
        "item_id": effective_item_id,
        "project_id": effective_project_id,
        "run_id": normalized_run_id,
        "status": resume_analysis["status"],
        "blocked": blocked,
        "blocked_reasons": blocked_reasons,
        "warnings": warnings,
        "machine_gates_checked": [gate_summary, *_source_gate_summaries(source_record, source_run)],
        "machine_gates_passed": machine_gates_passed,
        "artifacts_created": [],
        "mutation_performed": False,
        "external_execution_performed": False,
        "model_execution_performed": False,
        "codex_execution_performed": False,
        "github_execution_performed": False,
        "patch_application_performed": False,
        "local_only": True,
        "next_safe_action": resume_analysis["next_safe_action"],
        "resume_eligible": resume_analysis["resume_eligible"],
        "resume_requires_operator_review": resume_analysis["resume_requires_operator_review"],
        "resume_requires_validation": validation_required,
        "last_valid_checkpoint": checkpoint,
        "resume_target": resume_analysis["resume_target"],
        "resume_command_plan": resume_analysis["resume_command_plan"],
        "source_run_found": bool(source_record),
        "source_run_status": _first_text(source_record.get("status"), source_run.get("status")),
        "source_run_artifact_path": _first_text(source_record.get("artifact_path")),
        "source_run_summary": _source_run_summary(source_record, source_run),
        "source_run_execution_flags": source_flags,
        "history_inspection_summary": _history_summary(history_payload),
        "queue_path": str(resolve_project_queue_path(config.repo_root, queue_path)),
        "history_path": str(resolve_orchestration_history_path(config.repo_root, history_path)),
        "machine_gate_profile_for_inspection": "read_only_agent",
        "agent_registry_summary": _agent_summary(config),
        "llm_decision_policy_summary": _llm_decision_summary(config, item_id=effective_item_id, queue_path=queue_path),
        "pre_resume_checks": _pre_resume_checks(
            checkpoint=checkpoint,
            validation_required=validation_required,
            source_flags=source_flags,
            source_gates_passed=source_gates_passed,
        ),
        "prohibited_operations": list(_PROHIBITED_OPERATIONS),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
        "recommended_resume_plan_artifact_path": str(
            (config.repo_root / ".aresforge" / "orchestrator" / "resume_plans" / "m147-resume-plan.json").resolve()
        ),
    }
    return _emit_or_write(config=config, payload=payload, output=output, force=force)


def _latest_record(history_payload: dict[str, Any]) -> dict[str, Any]:
    latest = history_payload.get("latest_record")
    if isinstance(latest, dict) and latest:
        return latest
    records = history_payload.get("records", [])
    if isinstance(records, list) and records and isinstance(records[0], dict):
        return records[0]
    return {}


def _load_source_run(record: dict[str, Any]) -> dict[str, Any]:
    artifact_path = str(record.get("artifact_path", "") or "").strip()
    if not artifact_path:
        return {}
    path = Path(artifact_path)
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    return raw if isinstance(raw, dict) else {}


def _last_valid_checkpoint(record: dict[str, Any], source_run: dict[str, Any]) -> dict[str, Any]:
    if not record:
        return {
            "checkpoint_id": "",
            "checkpoint_valid": False,
            "checkpoint_reason": "No orchestration run record was found for the requested run_id.",
            "last_completed_step_count": 0,
            "last_completed_step_id": "",
            "next_step_index": 1,
            "next_step_id": "",
            "failed_or_blocked_step_id": "",
        }

    step_results = _step_results(source_run)
    completed_steps = [
        step for step in step_results if str(step.get("status", "")).strip() == "completed" and not bool(step.get("blocked"))
    ]
    blocked_step = next((step for step in step_results if bool(step.get("blocked"))), {})
    failed_step = next((step for step in step_results if str(step.get("status", "")).strip() == "failed"), {})
    completed_count = _int(record.get("steps_completed"))
    if completed_steps:
        completed_count = max(completed_count, len(completed_steps))
    last_completed = completed_steps[-1] if completed_steps else {}
    next_step = _next_unattempted_step(source_run, completed_count)
    status = str(record.get("status", "")).strip()

    if completed_count > 0:
        return {
            "checkpoint_id": "post_step_checkpoint",
            "checkpoint_valid": True,
            "checkpoint_reason": "At least one completed step is available as the last safe checkpoint.",
            "last_completed_step_count": completed_count,
            "last_completed_step_id": _first_text(last_completed.get("step_id")),
            "next_step_index": completed_count + 1,
            "next_step_id": _first_text(next_step.get("step_id")),
            "failed_or_blocked_step_id": _first_text(blocked_step.get("step_id"), failed_step.get("step_id")),
        }
    if _int(record.get("steps_total")) > 0 or step_results:
        return {
            "checkpoint_id": "plan_snapshot",
            "checkpoint_valid": status in _RECOVERABLE_STATUSES,
            "checkpoint_reason": "Plan metadata exists but no step completed yet.",
            "last_completed_step_count": 0,
            "last_completed_step_id": "",
            "next_step_index": 1,
            "next_step_id": _first_text(next_step.get("step_id")),
            "failed_or_blocked_step_id": _first_text(blocked_step.get("step_id"), failed_step.get("step_id")),
        }
    return {
        "checkpoint_id": "queue_snapshot",
        "checkpoint_valid": status in _RECOVERABLE_STATUSES,
        "checkpoint_reason": "Only queue/run metadata is available; no plan or post-step checkpoint was found.",
        "last_completed_step_count": 0,
        "last_completed_step_id": "",
        "next_step_index": 1,
        "next_step_id": "",
        "failed_or_blocked_step_id": "",
    }


def _resume_analysis(
    *,
    source_record: dict[str, Any],
    source_run: dict[str, Any],
    checkpoint: dict[str, Any],
    validation_required: bool,
    machine_gates_passed: bool,
    blocked: bool,
) -> dict[str, Any]:
    source_status = _first_text(source_record.get("status"), source_run.get("status"))
    checkpoint_valid = bool(checkpoint.get("checkpoint_valid"))
    source_found = bool(source_record)
    resume_eligible = bool(
        source_found
        and not blocked
        and machine_gates_passed
        and checkpoint_valid
        and source_status in _RECOVERABLE_STATUSES
        and not validation_required
    )
    operator_review = bool(
        not source_found
        or blocked
        or not machine_gates_passed
        or not checkpoint_valid
        or validation_required
        or source_status in _REVIEW_REQUIRED_STATUSES
    )
    status = _status(
        source_found=source_found,
        source_status=source_status,
        resume_eligible=resume_eligible,
        operator_review=operator_review,
        blocked=blocked,
    )
    resume_target = {
        "resume_from_checkpoint": str(checkpoint.get("checkpoint_id", "")).strip(),
        "resume_after_completed_step_count": _int(checkpoint.get("last_completed_step_count")),
        "resume_at_step_index": _int(checkpoint.get("next_step_index")) or 1,
        "resume_at_step_id": str(checkpoint.get("next_step_id", "") or "").strip(),
        "failed_or_blocked_step_id": str(checkpoint.get("failed_or_blocked_step_id", "") or "").strip(),
    }
    return {
        "status": status,
        "resume_eligible": resume_eligible,
        "resume_requires_operator_review": operator_review,
        "resume_target": resume_target,
        "resume_command_plan": _resume_command_plan(
            source_record=source_record,
            source_status=source_status,
            checkpoint=checkpoint,
            resume_eligible=resume_eligible,
            validation_required=validation_required,
        ),
        "next_safe_action": _next_safe_action(
            source_found=source_found,
            source_status=source_status,
            resume_eligible=resume_eligible,
            operator_review=operator_review,
            validation_required=validation_required,
            blocked=blocked,
        ),
    }


def _status(
    *,
    source_found: bool,
    source_status: str,
    resume_eligible: bool,
    operator_review: bool,
    blocked: bool,
) -> str:
    if blocked:
        return "blocked"
    if not source_found:
        return "no_resume_record"
    if resume_eligible:
        return "resume_available"
    if source_status in _TERMINAL_STATUSES:
        return "resume_not_required"
    if operator_review:
        return "recovery_review_required"
    return "resume_not_available"


def _resume_command_plan(
    *,
    source_record: dict[str, Any],
    source_status: str,
    checkpoint: dict[str, Any],
    resume_eligible: bool,
    validation_required: bool,
) -> dict[str, Any]:
    item_id = _first_text(source_record.get("item_id"), DEFAULT_ITEM_ID)
    base_command = f"python -m aresforge run-agent-orchestration --item-id {item_id} --format json"
    return {
        "resume_command_available_in_m147": False,
        "automatic_resume_performed": False,
        "recommended_operator_command": base_command if resume_eligible else "",
        "recommended_initial_mode": "dry_run",
        "requires_explicit_future_resume_flag": True,
        "requires_machine_gate_before_execution": True,
        "requires_validation_before_resume": validation_required,
        "resume_scope": _resume_scope(source_status, checkpoint),
    }


def _resume_scope(source_status: str, checkpoint: dict[str, Any]) -> str:
    if source_status == "max_steps_reached":
        return "continue_from_next_unattempted_step"
    if source_status == "interrupted":
        return "resume_from_last_valid_checkpoint"
    if source_status == "running":
        return "operator_confirm_interruption_then_resume"
    if source_status in _REVIEW_REQUIRED_STATUSES:
        return "classify_or_resolve_failed_step_before_retry"
    if source_status in _TERMINAL_STATUSES:
        return "no_resume_needed"
    if not checkpoint.get("checkpoint_valid"):
        return "no_valid_checkpoint"
    return "operator_review_required"


def _next_safe_action(
    *,
    source_found: bool,
    source_status: str,
    resume_eligible: bool,
    operator_review: bool,
    validation_required: bool,
    blocked: bool,
) -> str:
    if blocked:
        return "Resolve read-only machine-gate blockers before relying on this resume plan."
    if not source_found:
        return "No run record was found; inspect orchestration history or run an explicit gated orchestration command to create checkpoint evidence."
    if validation_required:
        return "Run explicit local validation or result ingestion before any resume attempt."
    if resume_eligible:
        return "Resume is available only through a future explicit machine-gated orchestration command; M147 has not resumed execution."
    if source_status in _REVIEW_REQUIRED_STATUSES:
        return "Classify or resolve the failed/blocked step, then regenerate the resume plan before any explicit retry."
    if source_status in _TERMINAL_STATUSES:
        return "No resume is required for this terminal run; review artifacts before any follow-on work."
    if operator_review:
        return "Review checkpoint evidence and regenerate this plan after resolving recovery blockers."
    return "Inspect run history and checkpoint evidence before any further orchestration action."


def _source_execution_flags(record: dict[str, Any], source_run: dict[str, Any]) -> dict[str, bool]:
    return {
        "mutation_performed": bool(record.get("mutation_performed") or source_run.get("mutation_performed")),
        "external_execution_performed": bool(record.get("external_execution_performed") or source_run.get("external_execution_performed")),
        "model_execution_performed": bool(record.get("model_execution_performed") or source_run.get("model_execution_performed")),
        "codex_execution_performed": bool(record.get("codex_execution_performed") or source_run.get("codex_execution_performed")),
        "github_execution_performed": bool(record.get("github_execution_performed") or source_run.get("github_execution_performed")),
        "patch_application_performed": bool(record.get("patch_application_performed") or source_run.get("patch_application_performed")),
        "queue_mutation_performed": bool(source_run.get("queue_mutation_performed")),
    }


def _validation_required_before_resume(flags: dict[str, bool]) -> bool:
    return bool(
        flags["mutation_performed"]
        or flags["codex_execution_performed"]
        or flags["github_execution_performed"]
        or flags["patch_application_performed"]
        or flags["queue_mutation_performed"]
    )


def _source_machine_gates_passed(record: dict[str, Any], source_run: dict[str, Any]) -> bool:
    if not record:
        return True
    gates = _source_gate_summaries(record, source_run)
    if gates:
        return all(bool(gate.get("passed")) and not bool(gate.get("blocked")) for gate in gates)
    if "machine_gates_passed" in record:
        return bool(record.get("machine_gates_passed"))
    if "machine_gates_passed" in source_run:
        return bool(source_run.get("machine_gates_passed"))
    return True


def _source_gate_summaries(record: dict[str, Any], source_run: dict[str, Any]) -> list[dict[str, Any]]:
    gates: list[dict[str, Any]] = []
    for raw in [record.get("machine_gates_checked"), source_run.get("machine_gates_checked")]:
        if not isinstance(raw, list):
            continue
        for gate in raw:
            if isinstance(gate, dict):
                gates.append(_gate_summary(gate, source="source_orchestration_run"))
    return gates


def _gate_payload(config: AppConfig, *, item_id: str, queue_path: str | Path | None) -> dict[str, Any]:
    result = evaluate_machine_safety_gates(
        config,
        item_id=item_id,
        gate_profile="read_only_agent",
        queue_path=queue_path,
        output_format="json",
    )
    return result.get("payload", {}) if isinstance(result, dict) else {}


def _gate_summary(gate_payload: dict[str, Any], *, source: str) -> dict[str, Any]:
    checks = gate_payload.get("checks", [])
    failed = [
        str(check.get("check_id", "")).strip()
        for check in checks
        if isinstance(check, dict) and not bool(check.get("passed")) and not bool(check.get("warning_only"))
    ]
    return {
        "source": source,
        "gate_profile": str(gate_payload.get("gate_profile", "") or gate_payload.get("profile", "") or "read_only_agent").strip(),
        "passed": bool(gate_payload.get("passed")) and not bool(gate_payload.get("blocked")),
        "blocked": bool(gate_payload.get("blocked")),
        "blocked_reasons": _list(gate_payload.get("blocked_reasons")),
        "checks_failed": failed,
    }


def _pre_resume_checks(
    *,
    checkpoint: dict[str, Any],
    validation_required: bool,
    source_flags: dict[str, bool],
    source_gates_passed: bool,
) -> list[dict[str, Any]]:
    return [
        {
            "check_id": "source_run_record_found",
            "passed": bool(checkpoint.get("checkpoint_id")),
            "required": True,
            "message": "A local orchestration run record must exist.",
        },
        {
            "check_id": "last_checkpoint_valid",
            "passed": bool(checkpoint.get("checkpoint_valid")),
            "required": True,
            "message": "The last checkpoint must be valid before resuming.",
        },
        {
            "check_id": "source_machine_gates_passed",
            "passed": source_gates_passed,
            "required": True,
            "message": "Previous run gate evidence must not contain failed required gates.",
        },
        {
            "check_id": "validation_before_resume",
            "passed": not validation_required,
            "required": validation_required,
            "message": "Mutating, Codex, GitHub, patch, or queue effects require explicit validation before resume.",
        },
        {
            "check_id": "external_execution_default_denied",
            "passed": not bool(source_flags["external_execution_performed"]),
            "required": bool(source_flags["external_execution_performed"]),
            "message": "External execution evidence requires operator review before resume.",
        },
    ]


def _warnings(
    *,
    history_payload: dict[str, Any],
    source_record: dict[str, Any],
    source_run: dict[str, Any],
    checkpoint: dict[str, Any],
    source_flags: dict[str, bool],
    validation_required: bool,
) -> list[str]:
    warnings = _list(history_payload.get("warnings"))
    if not source_record:
        warnings.append("No orchestration run record matched the requested run_id.")
    if source_record and not checkpoint.get("checkpoint_valid"):
        warnings.append("No valid resume checkpoint was found for this run.")
    if validation_required:
        warnings.append("Source run reports effects that require validation before any resume.")
    if bool(source_flags["external_execution_performed"]):
        warnings.append("Source run reports external execution; resume must remain explicit and machine-gated.")
    if source_record and not source_run and str(source_record.get("artifact_path", "")).strip():
        warnings.append("Source run artifact path was present but could not be loaded.")
    return _dedupe(warnings)


def _history_summary(history_payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "history_record_count": _int(history_payload.get("history_record_count")),
        "recovery_record_count": _int(history_payload.get("recovery_record_count")),
        "history_status": str(history_payload.get("status", "")).strip(),
        "history_path": str(history_payload.get("history_path", "")).strip(),
    }


def _source_run_summary(record: dict[str, Any], source_run: dict[str, Any]) -> dict[str, Any]:
    return {
        "run_id": _first_text(record.get("run_id"), source_run.get("run_id")),
        "item_id": _first_text(record.get("item_id"), source_run.get("item_id")),
        "project_id": _first_text(record.get("project_id"), source_run.get("project_id")),
        "status": _first_text(record.get("status"), source_run.get("status")),
        "steps_total": _int(record.get("steps_total") or source_run.get("steps_total")),
        "steps_attempted": _int(record.get("steps_attempted") or source_run.get("steps_attempted")),
        "steps_completed": _int(record.get("steps_completed") or source_run.get("steps_completed")),
        "steps_blocked": _int(record.get("steps_blocked") or source_run.get("steps_blocked")),
        "started_at": _first_text(record.get("started_at"), source_run.get("started_at")),
        "completed_at": _first_text(record.get("completed_at"), source_run.get("completed_at")),
    }


def _agent_summary(config: AppConfig) -> dict[str, Any]:
    registry = build_agent_registry(config)
    return {
        "agent_registry_version": str(registry.get("agent_registry_version", "")),
        "agent_count": int(registry.get("agent_count", 0)),
        "executable_agents": _list(registry.get("executable_agents")),
        "dry_run_only_agents": _list(registry.get("dry_run_only_agents")),
    }


def _llm_decision_summary(config: AppConfig, *, item_id: str, queue_path: str | Path | None) -> dict[str, Any]:
    result = recommend_llm_decision(
        config,
        item_id=item_id,
        queue_path=queue_path,
        output_format="json",
    )
    payload = result.get("payload", {}) if isinstance(result, dict) else {}
    return {
        "recommendation_type": str(payload.get("recommendation_type", "")).strip(),
        "item_found": bool(payload.get("item_found")),
        "recommended_lane": str(payload.get("recommended_lane", "")).strip(),
        "recommended_provider": str(payload.get("recommended_provider", "")).strip(),
        "machine_gate_required": bool(payload.get("machine_gate_required")),
        "execution_performed": bool(payload.get("execution_performed")),
        "next_safe_action": str(payload.get("next_safe_action", "")).strip(),
    }


def _step_results(source_run: dict[str, Any]) -> list[dict[str, Any]]:
    steps = source_run.get("step_results", [])
    if not isinstance(steps, list):
        return []
    return [step for step in steps if isinstance(step, dict)]


def _next_unattempted_step(source_run: dict[str, Any], completed_count: int) -> dict[str, Any]:
    steps = _step_results(source_run)
    for step in steps:
        sequence = _int(step.get("sequence"))
        if sequence and sequence == completed_count + 1 and not bool(step.get("blocked")):
            return step
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
    artifact_payload["artifacts_created"] = _dedupe([*_list(payload.get("artifacts_created")), str(output_path)])
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


def _first_text(*values: Any) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""


def _int(value: Any) -> int:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    text = str(value or "").strip()
    return int(text) if text.isdigit() else 0


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
