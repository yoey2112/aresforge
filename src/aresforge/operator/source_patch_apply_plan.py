from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.local_project_queue import resolve_project_queue_path
from aresforge.operator.source_patch_risk_classifier import classify_source_patch_risk

COMMAND_NAME = "plan-source-patch-apply"
RECORD_TYPE = "source_patch_apply_plan_v1"
PLANNER_VERSION = "m149.1"
DEFAULT_ITEM_ID = "m149-controlled-source-patch-apply-plan"
DEFAULT_PROJECT_ID = "aresforge"

_PROHIBITED_OPERATIONS: tuple[str, ...] = (
    "merge_pull_request",
    "force_push",
    "update_protected_branch",
    "enable_auto_merge",
    "create_release",
    "modify_github_workflow",
    "bypass_machine_safety_gate",
    "apply_source_patch_from_generated_output_without_explicit_gate",
    "run_validation_commands_from_planner",
    "automatic_next_item_execution",
)

_BOUNDARY_CONFIRMATIONS: tuple[str, ...] = (
    "M149 generates a controlled source patch apply plan without applying the patch.",
    "M149 reuses M148 source patch risk classification and read-only machine gate evidence.",
    "M149 performs no agent, Codex, model, GitHub, validation-command, queue, or patch execution.",
    "Any future source patch apply must use a separate explicit operator command, machine gate, and validation evidence.",
)

_HARD_APPLY_BLOCKERS: frozenset[str] = frozenset(
    {
        "workflow_mutation",
        "protected_config_mutation",
        "queue_state_mutation",
        "binary_patch_application",
        "executable_or_mode_change",
        "outside_repo_path",
    }
)


def plan_source_patch_apply(
    config: AppConfig,
    *,
    patch_path: str | Path,
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
    classification_result = classify_source_patch_risk(
        config,
        patch_path=patch_path,
        item_id=normalized_item_id,
        project_id=normalized_project_id,
        queue_path=queue_path,
        output=None,
        force=False,
        output_format="json",
    )
    classification = classification_result.get("payload", {}) if isinstance(classification_result, dict) else {}
    if not isinstance(classification, dict):
        classification = {}

    detected_operations = [
        entry
        for entry in classification.get("blocked_operations", [])
        if isinstance(entry, dict) and bool(entry.get("detected"))
    ]
    hard_apply_blockers = [
        str(entry.get("operation_id", "")).strip()
        for entry in detected_operations
        if str(entry.get("operation_id", "")).strip() in _HARD_APPLY_BLOCKERS
    ]
    classifier_blocked_reasons = _list(classification.get("blocked_reasons"))
    blocked_reasons = _dedupe(classifier_blocked_reasons)
    command_blocked = bool(blocked_reasons) or not bool(classification)
    future_controlled_apply_eligible = not command_blocked and not hard_apply_blockers
    plan_status = _status(
        command_blocked=command_blocked,
        future_controlled_apply_eligible=future_controlled_apply_eligible,
    )
    validation_profile = str(classification.get("recommended_validation_profile", "")).strip()

    payload: dict[str, Any] = {
        "record_type": RECORD_TYPE,
        "artifact_type": RECORD_TYPE,
        "planner_version": PLANNER_VERSION,
        "generated": True,
        "generated_at": _now_iso(),
        "item_id": normalized_item_id,
        "project_id": normalized_project_id,
        "run_id": f"{normalized_item_id}:source-patch-apply-plan-v1",
        "status": plan_status,
        "blocked": command_blocked,
        "blocked_reasons": blocked_reasons,
        "warnings": _warnings(
            classification=classification,
            detected_operations=detected_operations,
            hard_apply_blockers=hard_apply_blockers,
        ),
        "machine_gates_checked": _list_dicts(classification.get("machine_gates_checked")),
        "machine_gates_passed": bool(classification.get("machine_gates_passed")) and not command_blocked,
        "artifacts_created": [],
        "mutation_performed": False,
        "external_execution_performed": False,
        "model_execution_performed": False,
        "codex_execution_performed": False,
        "github_execution_performed": False,
        "patch_application_performed": False,
        "validation_command_execution_performed": False,
        "local_only": True,
        "next_safe_action": _next_safe_action(
            command_blocked=command_blocked,
            future_controlled_apply_eligible=future_controlled_apply_eligible,
        ),
        "patch_path": str(classification.get("patch_path", _resolve(config.repo_root, patch_path))),
        "patch_file_found": bool(classification.get("patch_file_found")),
        "source_classification": _classification_summary(classification),
        "touched_files": _list(classification.get("touched_files")),
        "touched_file_count": int(classification.get("touched_file_count") or 0),
        "touched_file_details": _list_dicts(classification.get("touched_file_details")),
        "path_classes": _list(classification.get("path_classes")),
        "risk_level": str(classification.get("risk_level", "unknown")).strip() or "unknown",
        "mutation_type": str(classification.get("mutation_type", "unknown_change")).strip() or "unknown_change",
        "mutation_types": _list(classification.get("mutation_types")),
        "blocked_operations": _list_dicts(classification.get("blocked_operations")),
        "hard_apply_blockers": hard_apply_blockers,
        "automatic_apply_allowed": False,
        "controlled_apply_plan_available": future_controlled_apply_eligible,
        "future_controlled_apply_eligible": future_controlled_apply_eligible,
        "future_apply_requires_explicit_operator_command": True,
        "future_apply_requires_machine_gate": True,
        "future_apply_requires_clean_apply_check": True,
        "future_apply_requires_validation": True,
        "patch_application_gate_profile": "future_source_patch_apply",
        "recommended_validation_profile": validation_profile,
        "validation_plan": _validation_plan(classification),
        "pre_apply_checks": _pre_apply_checks(classification, hard_apply_blockers),
        "apply_plan_steps": _apply_plan_steps(
            patch_path=str(classification.get("patch_path", _resolve(config.repo_root, patch_path))),
            validation_profile=validation_profile,
            future_controlled_apply_eligible=future_controlled_apply_eligible,
            hard_apply_blockers=hard_apply_blockers,
        ),
        "rollback_plan": _rollback_plan(
            patch_path=str(classification.get("patch_path", _resolve(config.repo_root, patch_path)))
        ),
        "queue_path": str(resolve_project_queue_path(config.repo_root, queue_path)),
        "classification_command": "classify-source-patch-risk",
        "recommended_plan_artifact_path": str(
            (config.repo_root / ".aresforge" / "source_patch_apply_plans" / "m149-apply-plan.json").resolve()
        ),
        "prohibited_operations": list(_PROHIBITED_OPERATIONS),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }
    return _emit_or_write(config=config, payload=payload, output=output, force=force)


def _classification_summary(classification: dict[str, Any]) -> dict[str, Any]:
    return {
        "record_type": str(classification.get("record_type", "")).strip(),
        "status": str(classification.get("status", "")).strip(),
        "blocked": bool(classification.get("blocked")),
        "blocked_reasons": _list(classification.get("blocked_reasons")),
        "machine_gates_passed": bool(classification.get("machine_gates_passed")),
        "risk_level": str(classification.get("risk_level", "unknown")).strip() or "unknown",
        "mutation_type": str(classification.get("mutation_type", "unknown_change")).strip() or "unknown_change",
        "patch_application_allowed_by_classifier": bool(
            classification.get("patch_application_allowed_by_classifier")
        ),
        "patch_application_performed": bool(classification.get("patch_application_performed")),
    }


def _validation_plan(classification: dict[str, Any]) -> dict[str, Any]:
    requirements = classification.get("test_requirements", {})
    if not isinstance(requirements, dict):
        requirements = {}
    commands = _list(requirements.get("validation_commands"))
    additional = _list(requirements.get("additional_required_checks"))
    return {
        "recommended_validation_profile": str(
            classification.get("recommended_validation_profile")
            or requirements.get("recommended_validation_profile")
            or ""
        ).strip(),
        "validation_commands": commands,
        "additional_required_checks": additional,
        "all_required_checks": _dedupe([*additional, *commands]),
        "planner_runs_validation": False,
        "requires_validation_before_completion": True,
        "requires_operator_diff_review": bool(requirements.get("requires_operator_diff_review", True)),
    }


def _pre_apply_checks(classification: dict[str, Any], hard_apply_blockers: list[str]) -> list[dict[str, Any]]:
    return [
        _planned_check("patch_file_found", bool(classification.get("patch_file_found")), "Patch file must exist."),
        _planned_check(
            "patch_parsed",
            str(classification.get("patch_parse_status", "")).strip() == "parsed",
            "Patch must parse as a unified source patch with target files.",
        ),
        _planned_check(
            "read_only_machine_gate_passed",
            bool(classification.get("machine_gates_passed")),
            "Read-only machine gate must pass before relying on the apply plan.",
        ),
        _planned_check(
            "no_hard_apply_blockers",
            not hard_apply_blockers,
            "Patch must not include workflow, protected config, queue-state, binary, executable-mode, or outside-repo blockers.",
        ),
        _planned_check(
            "separate_apply_gate_required",
            False,
            "A future explicit source patch apply gate is required; M149 intentionally does not satisfy it.",
            warning_only=True,
        ),
    ]


def _planned_check(check_id: str, passed: bool, message: str, *, warning_only: bool = False) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "passed": bool(passed),
        "message": message,
        "warning_only": bool(warning_only),
    }


def _apply_plan_steps(
    *,
    patch_path: str,
    validation_profile: str,
    future_controlled_apply_eligible: bool,
    hard_apply_blockers: list[str],
) -> list[dict[str, Any]]:
    blocked_note = "; ".join(hard_apply_blockers)
    return [
        _step(
            "01_review_classification",
            "Review M148 classification and touched-file summary.",
            "review",
            command=f"python -m aresforge classify-source-patch-risk --patch-path {patch_path} --format json",
            allowed_now=True,
        ),
        _step(
            "02_operator_diff_review",
            "Review the patch diff and confirm intent before any apply command exists.",
            "operator_review",
            command="manual diff review",
            allowed_now=True,
        ),
        _step(
            "03_future_apply_gate",
            "Evaluate the future source patch apply machine gate.",
            "machine_gate",
            command="future explicit source patch apply gate",
            allowed_now=False,
            blocked_reason=blocked_note or "M149 is plan-only and does not enable source patch application.",
        ),
        _step(
            "04_clean_apply_check",
            "Run a clean apply check in the future apply command before mutation.",
            "dry_run_check",
            command=f"git apply --check {patch_path}",
            allowed_now=False,
            blocked_reason="M149 does not run git apply checks.",
        ),
        _step(
            "05_controlled_patch_apply",
            "Apply the patch only through a future explicit controlled apply path.",
            "patch_apply",
            command=f"git apply {patch_path}",
            allowed_now=False,
            blocked_reason="Source patch application is not performed by M149.",
        ),
        _step(
            "06_post_apply_validation",
            "Run the recommended local validation profile after a future apply.",
            "validation",
            command=f"python -m aresforge ingest-codex-result-and-validate --validation-profile {validation_profile or '<profile>'}",
            allowed_now=False,
            blocked_reason="M149 does not run validation commands.",
        ),
        _step(
            "07_completion_evidence",
            "Capture validation evidence before any queue completion decision.",
            "evidence",
            command="complete-local-queue-item or auto-complete-safe-queue-item after validation evidence",
            allowed_now=False,
            blocked_reason="M149 does not mutate queue state.",
        ),
    ]


def _step(
    step_id: str,
    description: str,
    action_type: str,
    *,
    command: str,
    allowed_now: bool,
    blocked_reason: str = "",
) -> dict[str, Any]:
    return {
        "step_id": step_id,
        "description": description,
        "action_type": action_type,
        "command": command,
        "allowed_by_m149": bool(allowed_now),
        "executed": False,
        "mutation_performed": False,
        "patch_application_performed": False,
        "blocked_reason": blocked_reason,
    }


def _rollback_plan(*, patch_path: str) -> dict[str, Any]:
    return {
        "rollback_required_before_apply": True,
        "planner_executes_rollback": False,
        "required_before_future_apply": [
            "Capture clean git status and HEAD before applying.",
            "Keep the original patch artifact immutable.",
            "Record touched files and validation plan in local evidence.",
        ],
        "future_reversal_command": f"git apply -R {patch_path}",
        "future_reversal_requires_operator_review": True,
        "future_reversal_requires_validation": True,
    }


def _warnings(
    *,
    classification: dict[str, Any],
    detected_operations: list[dict[str, Any]],
    hard_apply_blockers: list[str],
) -> list[str]:
    warnings = _list(classification.get("warnings"))
    if detected_operations:
        warnings.append("Patch contains operations that block automatic apply.")
    if hard_apply_blockers:
        warnings.append("Patch contains hard blockers for future controlled source patch apply.")
    warnings.append("M149 generated a plan only; no patch apply, validation command, queue mutation, or external execution was performed.")
    return _dedupe(warnings)


def _status(*, command_blocked: bool, future_controlled_apply_eligible: bool) -> str:
    if command_blocked:
        return "blocked"
    if future_controlled_apply_eligible:
        return "planned"
    return "apply_blocked"


def _next_safe_action(*, command_blocked: bool, future_controlled_apply_eligible: bool) -> str:
    if command_blocked:
        return "Resolve patch, queue, or read-only machine-gate blockers before relying on this apply plan."
    if not future_controlled_apply_eligible:
        return "Treat this plan as blocked-for-apply evidence; do not apply the patch without operator redesign or expanded gates."
    return "Review the plan as local evidence; any source patch apply remains a separate explicit future command with machine gates and validation."


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


def _list_dicts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [entry for entry in value if isinstance(entry, dict)]


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
