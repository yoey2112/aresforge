from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.local_project_queue import resolve_project_queue_path
from aresforge.operator.machine_safety_gate_engine import evaluate_machine_safety_gates

COMMAND_NAME = "inspect-autonomy-profile"
RECORD_TYPE = "operator_autonomy_configuration_profile_v1"
PROFILE_VERSION = "m158.1"
DEFAULT_ITEM_ID = "m158-operator-autonomy-configuration-profile"
DEFAULT_PROJECT_ID = "aresforge"
DEFAULT_AUTONOMY_PROFILE = "locked_down"

CAPABILITIES: tuple[str, ...] = (
    "local_read_inspection",
    "local_artifact_write",
    "local_planning",
    "queue_status_mutation",
    "validation_command_execution",
    "local_model_advisory_execution",
    "codex_dry_run",
    "codex_low_risk_execution",
    "github_sync_dry_run",
    "github_issue_sync",
    "github_pr_draft_creation",
    "source_patch_apply_dry_run",
    "source_patch_application",
    "docs_only_patch_application",
    "orchestration_resume_or_retry",
    "automatic_next_item_execution",
)

_PROHIBITED_OPERATIONS: tuple[str, ...] = (
    "merge_pull_request",
    "force_push",
    "update_protected_branch",
    "enable_auto_merge",
    "create_release",
    "modify_github_workflow",
    "bypass_machine_safety_gate",
    "automatic_next_item_execution",
    "apply_source_patch_without_explicit_apply_boundary",
)

_BOUNDARY_CONFIRMATIONS: tuple[str, ...] = (
    "M158 defines inspectable autonomy profiles only; this command does not execute an enabled capability.",
    "The default autonomy profile is locked_down and denies every non-read capability.",
    "Enabled or dry-run-only profile entries still require a separate explicit command, explicit operator intent, and passing machine gates.",
    "GitHub, Codex, local model, source patch, queue mutation, resume, retry, and next-item behavior remain non-executed by this inspector.",
)


def inspect_autonomy_profile(
    config: AppConfig,
    *,
    project_id: str = DEFAULT_PROJECT_ID,
    item_id: str = DEFAULT_ITEM_ID,
    autonomy_profile: str | None = None,
    queue_path: str | Path | None = None,
    output: str | Path | None = None,
    force: bool = False,
    output_format: str = "json",
) -> dict[str, Any]:
    fmt = _text(output_format).lower() or "json"
    if fmt != "json":
        return _error("invalid_format", {"format": output_format, "supported_formats": ["json"]})

    normalized_project_id = _text(project_id) or DEFAULT_PROJECT_ID
    normalized_item_id = _text(item_id) or DEFAULT_ITEM_ID
    selected_profile_id = _text(autonomy_profile) or DEFAULT_AUTONOMY_PROFILE
    queue = _load_queue(config, queue_path=queue_path)
    item = _find_item(queue, normalized_item_id)
    gate_payload = _gate_payload(config, item_id=normalized_item_id, queue_path=queue_path)
    gate_summary = _gate_summary(gate_payload)
    profiles = autonomy_profile_definitions()
    selected_profile = next(
        (profile for profile in profiles if profile["profile_id"] == selected_profile_id),
        {},
    )
    unknown_profile = not bool(selected_profile)
    warnings = _warnings(item=item, gate_payload=gate_payload, project_id=normalized_project_id)
    blocked_reasons = _blocked_reasons(
        item=item,
        gate_payload=gate_payload,
        unknown_profile=unknown_profile,
        selected_profile_id=selected_profile_id,
    )
    blocked = bool(blocked_reasons)

    payload: dict[str, Any] = {
        "record_type": RECORD_TYPE,
        "artifact_type": RECORD_TYPE,
        "profile_version": PROFILE_VERSION,
        "generated": True,
        "generated_at": _now_iso(),
        "project_id": normalized_project_id,
        "item_id": normalized_item_id,
        "run_id": "",
        "status": "blocked" if blocked else "safe_default_ready",
        "blocked": blocked,
        "blocked_reasons": blocked_reasons,
        "warnings": warnings,
        "machine_gates_checked": [gate_summary],
        "machine_gates_passed": bool(gate_summary.get("passed")) and not blocked,
        "autonomy_profile": selected_profile_id,
        "default_autonomy_profile": DEFAULT_AUTONOMY_PROFILE,
        "default_behavior": "safe_deny",
        "available_autonomy_profiles": [profile["profile_id"] for profile in profiles],
        "selected_profile": selected_profile,
        "profiles": profiles,
        "capability_matrix": _capability_matrix(profiles),
        "profile_count": len(profiles),
        "artifacts_created": [],
        "mutation_performed": False,
        "queue_mutation_performed": False,
        "external_execution_performed": False,
        "codex_execution_performed": False,
        "model_execution_performed": False,
        "github_execution_performed": False,
        "patch_application_performed": False,
        "local_only": True,
        "next_safe_action": _next_safe_action(blocked=blocked, selected_profile=selected_profile),
        "queue_item_found": bool(item),
        "queue_item_status": _text(item.get("status")),
        "queue_path": str(resolve_project_queue_path(config.repo_root, queue_path)),
        "prohibited_operations": list(_PROHIBITED_OPERATIONS),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }
    return _emit_or_write(config=config, payload=payload, output=output, force=force)


def autonomy_profile_definitions() -> list[dict[str, Any]]:
    return [
        _profile(
            "locked_down",
            "Locked Down",
            "Default safe-deny posture. Only local inspection is enabled.",
            default=True,
            risk_level="lowest",
            controls={
                "local_read_inspection": "enabled",
            },
            gates=["operator_autonomy_profile"],
            next_safe_action="Use this profile when no autonomous execution should be considered.",
        ),
        _profile(
            "advisory_only",
            "Advisory Only",
            "Allows local inspection, planning, and optional local report artifacts; blocks execution and mutation.",
            risk_level="low",
            controls={
                "local_read_inspection": "enabled",
                "local_artifact_write": "enabled",
                "local_planning": "enabled",
            },
            gates=["read_only_agent", "local_artifact_write"],
            next_safe_action="Generate or review local advisory artifacts; use another explicit profile before any execution path.",
        ),
        _profile(
            "low_risk_local",
            "Low-Risk Local",
            "Allows narrow local-only validation, queue evidence mutation, and docs-only apply boundaries when their gates pass.",
            risk_level="medium",
            controls={
                "local_read_inspection": "enabled",
                "local_artifact_write": "enabled",
                "local_planning": "enabled",
                "queue_status_mutation": "enabled",
                "validation_command_execution": "enabled",
                "docs_only_patch_application": "enabled",
                "source_patch_apply_dry_run": "dry_run_only",
            },
            gates=[
                "read_only_agent",
                "local_artifact_write",
                "queue_status_mutation",
                "docs_only_patch_apply",
                "source_patch_apply_dry_run",
            ],
            next_safe_action="Use only local commands with validation evidence; keep source-code apply, Codex, models, and GitHub blocked.",
        ),
        _profile(
            "codex_dry_run",
            "Codex Dry Run",
            "Allows Codex dispatch planning and dry-run records only; real Codex invocation is blocked.",
            risk_level="medium",
            controls={
                "local_read_inspection": "enabled",
                "local_artifact_write": "enabled",
                "local_planning": "enabled",
                "codex_dry_run": "dry_run_only",
                "validation_command_execution": "dry_run_only",
            },
            gates=["read_only_agent", "codex_dispatch"],
            next_safe_action="Run only dry-run Codex dispatch or end-to-end dry-run loop commands with captured local evidence.",
        ),
        _profile(
            "codex_low_risk_enabled",
            "Codex Low-Risk Enabled",
            "Allows one low-risk Codex path only through explicit flags, declared changed paths, and Codex dispatch gates.",
            risk_level="high",
            controls={
                "local_read_inspection": "enabled",
                "local_artifact_write": "enabled",
                "local_planning": "enabled",
                "validation_command_execution": "enabled",
                "codex_dry_run": "dry_run_only",
                "codex_low_risk_execution": "enabled",
                "source_patch_apply_dry_run": "dry_run_only",
            },
            gates=["codex_dispatch", "source_patch_apply_dry_run"],
            explicit_flags=["--execution-enabled", "--allow-low-risk-code", "--changed-path"],
            next_safe_action="Use the M152 low-risk Codex loop only for declared low-risk paths; do not apply patches or call GitHub from profile output.",
        ),
        _profile(
            "github_sync_dry_run",
            "GitHub Sync Dry Run",
            "Allows GitHub sync planning and dry-run evidence only; live GitHub mutation is blocked.",
            risk_level="medium",
            controls={
                "local_read_inspection": "enabled",
                "local_artifact_write": "enabled",
                "local_planning": "enabled",
                "github_sync_dry_run": "dry_run_only",
            },
            gates=["read_only_agent", "github_sync"],
            next_safe_action="Generate dry-run GitHub sync plans only; review local evidence before any separate live sync command exists.",
        ),
        _profile(
            "github_issue_sync_enabled",
            "GitHub Issue Sync Enabled",
            "Allows narrow issue/comment sync and draft PR creation only through explicit future GitHub gates; PR merge and protected operations stay blocked.",
            risk_level="high",
            controls={
                "local_read_inspection": "enabled",
                "local_artifact_write": "enabled",
                "local_planning": "enabled",
                "github_sync_dry_run": "dry_run_only",
                "github_issue_sync": "enabled",
                "github_pr_draft_creation": "enabled",
            },
            gates=["github_sync"],
            explicit_flags=["--github-enabled", "--execute", "--approval-marker"],
            local_only_profile=False,
            next_safe_action="Use only narrow future issue/comment sync or draft PR creation commands with explicit approval; never merge PRs or update protected branches.",
        ),
        _profile(
            "experimental_full_local",
            "Experimental Full Local",
            "Allows the broadest local-only profile: validation, queue evidence, docs-only patches, local advisory models, and low-risk Codex gates.",
            risk_level="critical",
            controls={
                "local_read_inspection": "enabled",
                "local_artifact_write": "enabled",
                "local_planning": "enabled",
                "queue_status_mutation": "enabled",
                "validation_command_execution": "enabled",
                "local_model_advisory_execution": "enabled",
                "codex_dry_run": "dry_run_only",
                "codex_low_risk_execution": "enabled",
                "source_patch_apply_dry_run": "dry_run_only",
                "docs_only_patch_application": "enabled",
            },
            gates=[
                "local_artifact_write",
                "queue_status_mutation",
                "docs_only_patch_apply",
                "source_patch_apply_dry_run",
                "local_llm_execution",
                "codex_dispatch",
            ],
            explicit_flags=["profile-specific explicit operator approval", "per-command allow flag"],
            next_safe_action="Use only after profile review and per-command gates; GitHub mutation, source patch application, resume/retry, and next-item automation remain blocked.",
        ),
    ]


def _profile(
    profile_id: str,
    display_name: str,
    description: str,
    *,
    controls: dict[str, str],
    gates: list[str],
    next_safe_action: str,
    risk_level: str,
    default: bool = False,
    explicit_flags: list[str] | None = None,
    local_only_profile: bool = True,
) -> dict[str, Any]:
    capability_controls = [
        {
            "capability_id": capability,
            "status": controls.get(capability, "blocked"),
            "required_machine_gate_profile": _capability_gate(capability),
            "requires_explicit_operator_flag": controls.get(capability, "blocked") != "blocked"
            and capability not in {"local_read_inspection", "local_planning"},
            "mutation_allowed": capability
            in {
                "queue_status_mutation",
                "docs_only_patch_application",
                "github_issue_sync",
                "github_pr_draft_creation",
            }
            and controls.get(capability) == "enabled",
            "execution_available_from_inspector": False,
        }
        for capability in CAPABILITIES
    ]
    return {
        "profile_id": profile_id,
        "display_name": display_name,
        "description": description,
        "enabled_by_default": default,
        "default_safe_profile": default,
        "local_only_profile": local_only_profile,
        "risk_level": risk_level,
        "profile_status": "default_safe_deny" if default else "explicit_selection_required",
        "required_machine_gate_profiles": gates,
        "required_explicit_flags": explicit_flags or [],
        "capability_controls": capability_controls,
        "capability_status_counts": _status_counts(capability_controls),
        "blocked_operations": list(_PROHIBITED_OPERATIONS),
        "next_safe_action": next_safe_action,
    }


def _capability_gate(capability: str) -> str:
    return {
        "local_artifact_write": "local_artifact_write",
        "queue_status_mutation": "queue_status_mutation",
        "validation_command_execution": "profile-specific validation allowlist",
        "local_model_advisory_execution": "local_llm_execution",
        "codex_dry_run": "codex_dispatch",
        "codex_low_risk_execution": "codex_dispatch",
        "github_sync_dry_run": "github_sync",
        "github_issue_sync": "github_sync",
        "github_pr_draft_creation": "github_sync",
        "source_patch_apply_dry_run": "source_patch_apply_dry_run",
        "source_patch_application": "future explicit source patch apply gate",
        "docs_only_patch_application": "docs_only_patch_apply",
        "orchestration_resume_or_retry": "future explicit resume/retry gate",
        "automatic_next_item_execution": "blocked_no_gate",
    }.get(capability, "read_only_agent")


def _status_counts(capability_controls: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"enabled": 0, "dry_run_only": 0, "blocked": 0}
    for control in capability_controls:
        status = _text(control.get("status"))
        if status in counts:
            counts[status] += 1
    return counts


def _capability_matrix(profiles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "profile_id": _text(profile.get("profile_id")),
            "capabilities": {
                _text(control.get("capability_id")): _text(control.get("status"))
                for control in _dicts(profile.get("capability_controls"))
            },
        }
        for profile in profiles
    ]


def _gate_payload(config: AppConfig, *, item_id: str, queue_path: str | Path | None) -> dict[str, Any]:
    result = evaluate_machine_safety_gates(
        config,
        item_id=item_id,
        gate_profile="operator_autonomy_profile",
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
        "gate_profile": _text(gate_payload.get("gate_profile")) or "operator_autonomy_profile",
        "passed": bool(gate_payload.get("passed")) and not bool(gate_payload.get("blocked")),
        "blocked": bool(gate_payload.get("blocked")),
        "blocked_reasons": _list(gate_payload.get("blocked_reasons")),
        "checks_failed": failed,
    }


def _warnings(*, item: dict[str, Any], gate_payload: dict[str, Any], project_id: str) -> list[str]:
    warnings = _list(gate_payload.get("warnings"))
    if item and _text(item.get("project_id")) != project_id:
        warnings.append("Queue item project_id does not match the requested project_id.")
    if item and _text(item.get("status")) == "done":
        warnings.append("Queue item is already done; autonomy profile inspection remains valid as a capability contract.")
    warnings.append("Profile entries are policy metadata only and do not execute the capabilities they describe.")
    return _dedupe(warnings)


def _blocked_reasons(
    *,
    item: dict[str, Any],
    gate_payload: dict[str, Any],
    unknown_profile: bool,
    selected_profile_id: str,
) -> list[str]:
    reasons = _list(gate_payload.get("blocked_reasons"))
    if not item:
        reasons.append("Queue item must exist before autonomy profiles can be used as milestone capability evidence.")
    if unknown_profile:
        reasons.append(f"Unknown autonomy profile: {selected_profile_id}.")
    return _dedupe(reasons)


def _next_safe_action(*, blocked: bool, selected_profile: dict[str, Any]) -> str:
    if blocked:
        return "Resolve autonomy profile inspection blockers before relying on this configuration record."
    if selected_profile:
        return _text(selected_profile.get("next_safe_action"))
    return "Use locked_down until a known autonomy profile is explicitly selected and reviewed."


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
