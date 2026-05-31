from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import subprocess
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.local_project_queue import resolve_project_queue_path
from aresforge.operator.machine_safety_gate_engine import evaluate_machine_safety_gates
from aresforge.operator.source_patch_apply_plan import plan_source_patch_apply

COMMAND_NAME = "dry-run-source-patch-apply"
RECORD_TYPE = "source_patch_apply_dry_run_v1"
DRY_RUN_VERSION = "m150.1"
DEFAULT_ITEM_ID = "m150-machine-gated-source-patch-apply-dry-run"
DEFAULT_PROJECT_ID = "aresforge"

_PROHIBITED_OPERATIONS: tuple[str, ...] = (
    "merge_pull_request",
    "force_push",
    "update_protected_branch",
    "enable_auto_merge",
    "create_release",
    "modify_github_workflow",
    "bypass_machine_safety_gate",
    "apply_source_patch",
    "run_validation_commands_from_dry_run",
    "automatic_next_item_execution",
)

_BOUNDARY_CONFIRMATIONS: tuple[str, ...] = (
    "M150 proves source patch applicability with git apply --check only.",
    "M150 requires M149 apply-plan eligibility and the source_patch_apply_dry_run machine gate.",
    "M150 performs no repository mutation, queue mutation, validation command execution, Codex execution, model execution, or GitHub execution.",
    "A passing M150 dry run is evidence only; actual source patch apply remains a separate future explicit gated command.",
)


def dry_run_source_patch_apply(
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
    resolved_patch_path = _resolve(config.repo_root, patch_path)
    resolved_queue_path = resolve_project_queue_path(config.repo_root, queue_path)

    plan_result = plan_source_patch_apply(
        config,
        patch_path=resolved_patch_path,
        item_id=normalized_item_id,
        project_id=normalized_project_id,
        queue_path=queue_path,
        output=None,
        force=False,
        output_format="json",
    )
    plan = plan_result.get("payload", {}) if isinstance(plan_result, dict) else {}
    if not isinstance(plan, dict):
        plan = {}

    gate_result = evaluate_machine_safety_gates(
        config,
        item_id=normalized_item_id,
        gate_profile="source_patch_apply_dry_run",
        patch_path=resolved_patch_path,
        queue_path=queue_path,
        output_format="json",
    )
    gate_payload = gate_result.get("payload", {}) if isinstance(gate_result, dict) else {}
    gate_summary = _gate_summary(gate_payload)

    blocked_reasons = _blocked_reasons(plan=plan, gate_payload=gate_payload)
    dry_run_check = _not_run_check()
    dry_run_performed = False
    if not blocked_reasons:
        dry_run_check = _git_apply_check(config.repo_root, resolved_patch_path)
        dry_run_performed = True
        if not dry_run_check["passed"]:
            blocked_reasons.extend(_list(dry_run_check.get("blocked_reasons")))
            if not dry_run_check.get("blocked_reasons"):
                blocked_reasons.append("Patch did not pass git apply --check.")

    blocked = bool(blocked_reasons)
    status = _status(blocked=blocked, dry_run_performed=dry_run_performed, dry_run_check=dry_run_check)
    payload: dict[str, Any] = {
        "record_type": RECORD_TYPE,
        "artifact_type": RECORD_TYPE,
        "dry_run_version": DRY_RUN_VERSION,
        "generated": True,
        "generated_at": _now_iso(),
        "item_id": normalized_item_id,
        "project_id": normalized_project_id,
        "run_id": f"{normalized_item_id}:source-patch-apply-dry-run-v1",
        "status": status,
        "blocked": blocked,
        "blocked_reasons": _dedupe(blocked_reasons),
        "warnings": _warnings(plan=plan, gate_payload=gate_payload, dry_run_performed=dry_run_performed),
        "machine_gates_checked": [gate_summary],
        "machine_gates_passed": bool(gate_summary.get("passed")) and bool(plan.get("machine_gates_passed")) and not blocked,
        "artifacts_created": [],
        "mutation_performed": False,
        "external_execution_performed": False,
        "model_execution_performed": False,
        "codex_execution_performed": False,
        "github_execution_performed": False,
        "patch_application_performed": False,
        "patch_application_dry_run_performed": dry_run_performed,
        "validation_command_execution_performed": False,
        "local_only": True,
        "next_safe_action": _next_safe_action(status=status),
        "patch_path": str(resolved_patch_path),
        "queue_path": str(resolved_queue_path),
        "source_apply_plan": _plan_summary(plan),
        "touched_files": _list(plan.get("touched_files")),
        "touched_file_count": int(plan.get("touched_file_count") or 0),
        "risk_level": str(plan.get("risk_level", "unknown")).strip() or "unknown",
        "mutation_type": str(plan.get("mutation_type", "unknown_change")).strip() or "unknown_change",
        "hard_apply_blockers": _list(plan.get("hard_apply_blockers")),
        "dry_run_apply_check": dry_run_check,
        "clean_apply_check_performed": dry_run_performed,
        "dry_run_command": f"git apply --check {resolved_patch_path}",
        "controlled_apply_plan_available": bool(plan.get("controlled_apply_plan_available")),
        "future_controlled_apply_eligible": bool(plan.get("future_controlled_apply_eligible")),
        "actual_apply_allowed_by_m150": False,
        "future_apply_requires_explicit_operator_command": True,
        "future_apply_requires_machine_gate": True,
        "future_apply_requires_validation": True,
        "recommended_validation_profile": str(plan.get("recommended_validation_profile", "")).strip(),
        "recommended_dry_run_artifact_path": str(
            (config.repo_root / ".aresforge" / "source_patch_apply_dry_runs" / "m150-dry-run.json").resolve()
        ),
        "machine_gate_profile": "source_patch_apply_dry_run",
        "prohibited_operations": list(_PROHIBITED_OPERATIONS),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }
    return _emit_or_write(config=config, payload=payload, output=output, force=force)


def _blocked_reasons(*, plan: dict[str, Any], gate_payload: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    reasons.extend(_list(plan.get("blocked_reasons")))
    if not plan:
        reasons.append("Source patch apply plan could not be generated.")
    if plan.get("blocked") is True:
        reasons.append("Source patch apply plan is blocked.")
    if plan.get("controlled_apply_plan_available") is not True:
        reasons.append("Source patch apply plan is not eligible for controlled apply dry run.")
    if _list(plan.get("hard_apply_blockers")):
        reasons.append("Source patch apply plan reports hard apply blockers.")
    if gate_payload.get("passed") is not True or gate_payload.get("blocked") is True:
        reasons.append("Machine safety gate profile source_patch_apply_dry_run did not pass.")
        reasons.extend(_list(gate_payload.get("blocked_reasons")))
    return _dedupe(reasons)


def _gate_summary(gate_payload: dict[str, Any]) -> dict[str, Any]:
    checks = gate_payload.get("checks", [])
    failed = [
        str(check.get("check_id", "")).strip()
        for check in checks
        if isinstance(check, dict) and not bool(check.get("passed")) and not bool(check.get("warning_only"))
    ]
    return {
        "gate_profile": str(gate_payload.get("gate_profile", "source_patch_apply_dry_run")).strip()
        or "source_patch_apply_dry_run",
        "passed": bool(gate_payload.get("passed")) and not bool(gate_payload.get("blocked")),
        "blocked": bool(gate_payload.get("blocked")),
        "blocked_reasons": _list(gate_payload.get("blocked_reasons")),
        "checks_failed": failed,
    }


def _plan_summary(plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "record_type": str(plan.get("record_type", "")).strip(),
        "status": str(plan.get("status", "")).strip(),
        "blocked": bool(plan.get("blocked")),
        "blocked_reasons": _list(plan.get("blocked_reasons")),
        "machine_gates_passed": bool(plan.get("machine_gates_passed")),
        "controlled_apply_plan_available": bool(plan.get("controlled_apply_plan_available")),
        "future_controlled_apply_eligible": bool(plan.get("future_controlled_apply_eligible")),
        "patch_application_performed": bool(plan.get("patch_application_performed")),
    }


def _git_apply_check(repo_root: Path, patch_path: Path) -> dict[str, Any]:
    try:
        result = subprocess.run(
            ["git", "apply", "--check", str(patch_path)],
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "checked": True,
            "performed": True,
            "passed": False,
            "returncode": 1,
            "stdout": "",
            "stderr": str(exc),
            "blocked_reasons": [f"git apply --check failed to run: {exc}"],
        }
    stdout = result.stdout.strip()
    stderr = result.stderr.strip()
    return {
        "checked": True,
        "performed": True,
        "passed": result.returncode == 0,
        "returncode": result.returncode,
        "stdout": stdout,
        "stderr": stderr,
        "blocked_reasons": [text for text in (stderr, stdout) if text] if result.returncode != 0 else [],
    }


def _not_run_check() -> dict[str, Any]:
    return {
        "checked": False,
        "performed": False,
        "passed": False,
        "returncode": None,
        "stdout": "",
        "stderr": "",
        "blocked_reasons": [],
    }


def _status(*, blocked: bool, dry_run_performed: bool, dry_run_check: dict[str, Any]) -> str:
    if blocked and dry_run_performed:
        return "dry_run_failed"
    if blocked:
        return "blocked"
    if dry_run_check.get("passed") is True:
        return "dry_run_passed"
    return "dry_run_not_run"


def _warnings(*, plan: dict[str, Any], gate_payload: dict[str, Any], dry_run_performed: bool) -> list[str]:
    warnings = [*_list(plan.get("warnings")), *_list(gate_payload.get("warnings"))]
    if dry_run_performed:
        warnings.append("M150 ran git apply --check only; no patch application or repository mutation was performed.")
    else:
        warnings.append("M150 did not run git apply --check because a machine gate or apply-plan blocker stopped the dry run.")
    return _dedupe(warnings)


def _next_safe_action(*, status: str) -> str:
    if status == "dry_run_passed":
        return "Record this as applicability evidence only; actual source patch apply remains a separate explicit gated command with validation."
    if status == "dry_run_failed":
        return "Review the git apply --check errors and refresh or redesign the patch before any future apply attempt."
    if status == "blocked":
        return "Resolve machine-gate or apply-plan blockers before re-running the source patch apply dry run."
    return "No source patch dry run was performed."


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
