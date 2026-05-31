from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.agent_registry import build_agent_registry
from aresforge.operator.codex_validation_profiles import VALIDATION_PROFILE_COMMANDS
from aresforge.operator.llm_decision_policy import recommend_llm_decision
from aresforge.operator.local_project_queue import resolve_project_queue_path
from aresforge.operator.machine_safety_gate_engine import evaluate_machine_safety_gates

COMMAND_NAME = "classify-codex-failure"
RECORD_TYPE = "codex_failure_classification_retry_policy_v1"
POLICY_VERSION = "m145.1"
DEFAULT_ITEM_ID = "m145-codex-failure-classification-and-retry-policy"
DEFAULT_PROJECT_ID = "aresforge"

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

_BOUNDARY_CONFIRMATIONS: tuple[str, ...] = (
    "M145 classifies a local Codex failure artifact and selects a deterministic retry or stop policy.",
    "This command performs no Codex execution, model execution, GitHub execution, patch application, validation command execution, queue mutation, or retry.",
    "Automatic retry loops are disabled; any retry-capable class still requires an explicit future operator command and passing machine gates.",
    "Failure classification is advisory control-plane evidence for downstream recovery, ingestion, validation, or human review.",
)

_CLASS_PRIORITY: tuple[str, ...] = (
    "artifact_invalid",
    "machine_gate_blocked",
    "execution_denied",
    "dirty_worktree",
    "process_timeout",
    "interrupted",
    "validation_failed",
    "process_nonzero",
    "evidence_missing",
    "unknown_failure",
)


def classify_codex_failure(
    config: AppConfig,
    *,
    failure_artifact: str | Path,
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
    artifact_path = _resolve(config.repo_root, failure_artifact)
    failure_data, artifact_errors = _load_failure_artifact(artifact_path)
    artifact_item_id = str(failure_data.get("item_id", "")).strip()
    effective_item_id = artifact_item_id or normalized_item_id
    effective_project_id = str(failure_data.get("project_id", "")).strip() or normalized_project_id
    effective_run_id = str(failure_data.get("run_id", "")).strip() or f"{effective_item_id}:codex-failure-classification-v1"

    queue = _load_queue(config, queue_path=queue_path)
    item = _find_item(queue, effective_item_id) or _find_item(queue, normalized_item_id)
    gate_payload = _gate_payload(config, item_id=effective_item_id, queue_path=queue_path)
    gate_summary = _gate_summary(gate_payload)
    detected_classes = _detected_failure_classes(failure_data=failure_data, artifact_errors=artifact_errors)
    primary_class = _primary_failure_class(detected_classes)
    retry_policy = _retry_policy(primary_class)

    warnings = _warnings(
        failure_data=failure_data,
        artifact_errors=artifact_errors,
        item=item,
        gate_payload=gate_payload,
        requested_project_id=normalized_project_id,
        effective_project_id=effective_project_id,
    )
    blocked_reasons = _blocked_reasons(artifact_errors=artifact_errors, gate_payload=gate_payload)
    blocked = bool(blocked_reasons)
    status = "blocked" if blocked else "classified"

    payload: dict[str, Any] = {
        "record_type": RECORD_TYPE,
        "artifact_type": RECORD_TYPE,
        "policy_version": POLICY_VERSION,
        "generated": True,
        "generated_at": _now_iso(),
        "item_id": effective_item_id,
        "project_id": effective_project_id,
        "run_id": effective_run_id,
        "status": status,
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
        "validation_command_execution_performed": False,
        "local_only": True,
        "next_safe_action": _next_safe_action(blocked=blocked, retry_policy=retry_policy, primary_class=primary_class),
        "failure_artifact_path": str(artifact_path),
        "failure_artifact_found": artifact_path.exists(),
        "failure_artifact_valid_json": not artifact_errors and bool(failure_data),
        "queue_item_found": bool(item),
        "queue_item_status": str(item.get("status", "")).strip(),
        "queue_path": str(resolve_project_queue_path(config.repo_root, queue_path)),
        "primary_failure_class": primary_class,
        "detected_failure_classes": detected_classes,
        "retry_policy": retry_policy,
        "retry_policy_matrix": _retry_policy_matrix(),
        "failure_summary": _failure_summary(failure_data, primary_class=primary_class),
        "observed_execution_flags": _observed_execution_flags(failure_data),
        "machine_gate_profile_for_inspection": "read_only_agent",
        "m136_validation_profiles_available": sorted(VALIDATION_PROFILE_COMMANDS),
        "codex_agent_summary": _codex_agent_summary(config),
        "llm_decision_policy_summary": _llm_decision_summary(config, item_id=effective_item_id, queue_path=queue_path),
        "prohibited_operations": list(_PROHIBITED_OPERATIONS),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
        "recommended_policy_artifact_path": str(
            (config.repo_root / ".aresforge" / "codex_execution" / "failure_policy" / "m145-classification.json").resolve()
        ),
    }
    return _emit_or_write(config=config, payload=payload, output=output, force=force)


def _detected_failure_classes(*, failure_data: dict[str, Any], artifact_errors: list[str]) -> list[str]:
    detected: list[str] = []
    text = _failure_text(failure_data, artifact_errors)
    status = str(failure_data.get("status", "")).strip().lower()
    exit_code = _exit_code(failure_data)
    if artifact_errors:
        detected.append("artifact_invalid")
    if _machine_gate_blocked(failure_data, text):
        detected.append("machine_gate_blocked")
    if _execution_denied(failure_data, text):
        detected.append("execution_denied")
    if _dirty_worktree(failure_data, text):
        detected.append("dirty_worktree")
    if _timed_out(failure_data, text, exit_code):
        detected.append("process_timeout")
    if status in {"interrupted", "cancelled", "canceled"} or "keyboardinterrupt" in text:
        detected.append("interrupted")
    if _validation_failed(failure_data, text):
        detected.append("validation_failed")
    if exit_code is not None and exit_code != 0:
        detected.append("process_nonzero")
    if _evidence_missing(failure_data, text):
        detected.append("evidence_missing")
    if not detected:
        detected.append("unknown_failure")
    return [failure_class for failure_class in _CLASS_PRIORITY if failure_class in set(detected)]


def _primary_failure_class(detected: list[str]) -> str:
    for failure_class in _CLASS_PRIORITY:
        if failure_class in detected:
            return failure_class
    return "unknown_failure"


def _retry_policy(primary_class: str) -> dict[str, Any]:
    policies = {
        "artifact_invalid": {
            "policy_id": "stop_repair_failure_artifact",
            "decision": "stop",
            "automatic_retry_allowed": False,
            "max_retry_attempts": 0,
            "requires_operator_approval": True,
            "requires_machine_gate": "read_only_agent",
            "safe_recovery_command": "classify-codex-failure --failure-artifact <valid-json> --format json",
            "stop_reason": "Failure artifact must be valid local JSON before retry decisions can be trusted.",
        },
        "machine_gate_blocked": {
            "policy_id": "stop_until_machine_gate_passes",
            "decision": "stop",
            "automatic_retry_allowed": False,
            "max_retry_attempts": 0,
            "requires_operator_approval": True,
            "requires_machine_gate": "blocking gate from failure artifact",
            "safe_recovery_command": "evaluate-machine-safety-gates --item-id <item> --gate-profile <profile> --format json",
            "stop_reason": "Machine-gate blockers must be resolved before another Codex attempt.",
        },
        "execution_denied": {
            "policy_id": "stop_until_explicit_codex_enablement",
            "decision": "stop",
            "automatic_retry_allowed": False,
            "max_retry_attempts": 0,
            "requires_operator_approval": True,
            "requires_machine_gate": "codex_dispatch",
            "safe_recovery_command": "inspect-codex-execution-enablements --format json",
            "stop_reason": "Real Codex execution remains default-deny without explicit flags and gates.",
        },
        "dirty_worktree": {
            "policy_id": "stop_until_worktree_reviewed",
            "decision": "stop",
            "automatic_retry_allowed": False,
            "max_retry_attempts": 0,
            "requires_operator_approval": True,
            "requires_machine_gate": "read_only_agent",
            "safe_recovery_command": "inspect-codex-worktree-guard --format json",
            "stop_reason": "Dirty worktree state requires operator review before any future real Codex run.",
        },
        "process_timeout": {
            "policy_id": "single_manual_retry_after_timeout_triage",
            "decision": "manual_retry_capable",
            "automatic_retry_allowed": False,
            "max_retry_attempts": 1,
            "requires_operator_approval": True,
            "requires_machine_gate": "codex_dispatch",
            "safe_recovery_command": "run-codex-dispatch --dry-run --format json",
            "stop_reason": "Timeouts may be retried once only after preflight review; no automatic loop is allowed.",
        },
        "interrupted": {
            "policy_id": "stop_record_interruption_and_recover_manually",
            "decision": "stop",
            "automatic_retry_allowed": False,
            "max_retry_attempts": 0,
            "requires_operator_approval": True,
            "requires_machine_gate": "read_only_agent",
            "safe_recovery_command": "inspect-orchestration-run-history --project-id aresforge --format json",
            "stop_reason": "Interrupted runs require checkpoint review before any explicit resume or rerun.",
        },
        "validation_failed": {
            "policy_id": "stop_fix_then_revalidate",
            "decision": "stop",
            "automatic_retry_allowed": False,
            "max_retry_attempts": 0,
            "requires_operator_approval": True,
            "requires_machine_gate": "queue_status_mutation before completion only",
            "safe_recovery_command": "ingest-codex-result-and-validate --item-id <item> --execution-record <record> --format json",
            "stop_reason": "Validation failures require code or evidence repair, then explicit revalidation.",
        },
        "process_nonzero": {
            "policy_id": "single_manual_retry_after_process_triage",
            "decision": "manual_retry_capable",
            "automatic_retry_allowed": False,
            "max_retry_attempts": 1,
            "requires_operator_approval": True,
            "requires_machine_gate": "codex_dispatch",
            "safe_recovery_command": "run-codex-dispatch --dry-run --format json",
            "stop_reason": "A nonzero process exit may be retried once only after stderr/result triage.",
        },
        "evidence_missing": {
            "policy_id": "stop_reconstruct_local_evidence",
            "decision": "stop",
            "automatic_retry_allowed": False,
            "max_retry_attempts": 0,
            "requires_operator_approval": True,
            "requires_machine_gate": "read_only_agent",
            "safe_recovery_command": "recover-codex-dispatch-run --run-id <run> --format json",
            "stop_reason": "Missing evidence must be recovered locally before retry or completion decisions.",
        },
        "unknown_failure": {
            "policy_id": "stop_human_review_unknown_failure",
            "decision": "stop",
            "automatic_retry_allowed": False,
            "max_retry_attempts": 0,
            "requires_operator_approval": True,
            "requires_machine_gate": "read_only_agent",
            "safe_recovery_command": "classify-codex-failure --failure-artifact <artifact> --format json",
            "stop_reason": "Unknown failures require human review and richer local evidence.",
        },
    }
    return dict(policies.get(primary_class, policies["unknown_failure"]))


def _retry_policy_matrix() -> list[dict[str, Any]]:
    return [
        {"failure_class": failure_class, **_retry_policy(failure_class)}
        for failure_class in _CLASS_PRIORITY
    ]


def _failure_summary(failure_data: dict[str, Any], *, primary_class: str) -> dict[str, Any]:
    return {
        "primary_failure_class": primary_class,
        "reported_status": str(failure_data.get("status", "")).strip(),
        "reported_failure_type": str(failure_data.get("failure_type", failure_data.get("error_type", ""))).strip(),
        "exit_code": _exit_code(failure_data),
        "blocked": bool(failure_data.get("blocked")),
        "blocked_reasons": _list(failure_data.get("blocked_reasons")),
        "warnings": _list(failure_data.get("warnings")),
        "stderr_excerpt": str(failure_data.get("stderr", "") or "")[:500],
        "stdout_excerpt": str(failure_data.get("stdout", "") or "")[:500],
    }


def _observed_execution_flags(failure_data: dict[str, Any]) -> dict[str, bool]:
    return {
        "artifact_reports_external_execution": bool(failure_data.get("external_execution_performed")),
        "artifact_reports_model_execution": bool(failure_data.get("model_execution_performed")),
        "artifact_reports_codex_execution": bool(failure_data.get("codex_execution_performed")),
        "artifact_reports_github_execution": bool(failure_data.get("github_execution_performed")),
        "artifact_reports_patch_application": bool(failure_data.get("patch_application_performed")),
        "artifact_reports_mutation": bool(failure_data.get("mutation_performed") or failure_data.get("queue_mutation_performed")),
    }


def _gate_payload(config: AppConfig, *, item_id: str, queue_path: str | Path | None) -> dict[str, Any]:
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


def _codex_agent_summary(config: AppConfig) -> dict[str, Any]:
    registry = build_agent_registry(config, agent_id="codex-dispatch-agent")
    agents = registry.get("agents", []) if isinstance(registry, dict) else []
    agent = agents[0] if agents and isinstance(agents[0], dict) else {}
    return {
        "agent_id": str(agent.get("agent_id", "codex-dispatch-agent")).strip() or "codex-dispatch-agent",
        "can_run_real": bool(agent.get("can_run_real")),
        "can_run_dry_run": bool(agent.get("can_run_dry_run")),
        "machine_gate_required": bool(agent.get("machine_gate_required", True)),
        "default_execution_mode": str(agent.get("default_execution_mode", "")).strip(),
        "forbidden_capabilities": _list(agent.get("forbidden_capabilities")),
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


def _warnings(
    *,
    failure_data: dict[str, Any],
    artifact_errors: list[str],
    item: dict[str, Any],
    gate_payload: dict[str, Any],
    requested_project_id: str,
    effective_project_id: str,
) -> list[str]:
    warnings = _list(gate_payload.get("warnings"))
    warnings.extend(_list(failure_data.get("warnings")))
    if artifact_errors:
        warnings.extend(artifact_errors)
    if item and str(item.get("project_id", "")).strip() != effective_project_id:
        warnings.append("Queue item project_id does not match the failure artifact project_id.")
    if requested_project_id != effective_project_id:
        warnings.append("Failure artifact project_id overrides the requested project_id.")
    if _observed_execution_flags(failure_data)["artifact_reports_github_execution"]:
        warnings.append("Failure artifact reports GitHub execution; treat as manual-review-only evidence.")
    return _dedupe(warnings)


def _blocked_reasons(*, artifact_errors: list[str], gate_payload: dict[str, Any]) -> list[str]:
    reasons = _list(gate_payload.get("blocked_reasons"))
    reasons.extend(artifact_errors)
    return _dedupe(reasons)


def _next_safe_action(*, blocked: bool, retry_policy: dict[str, Any], primary_class: str) -> str:
    if blocked:
        return "Resolve classifier input or read-only machine gate blockers before relying on retry policy output."
    decision = str(retry_policy.get("decision", "stop")).strip()
    if decision == "manual_retry_capable":
        return (
            f"Failure classified as {primary_class}; do not auto-retry. "
            "An operator may perform at most one explicit gated retry after triage."
        )
    return f"Failure classified as {primary_class}; stop automatic execution and follow the reported safe recovery command."


def _machine_gate_blocked(failure_data: dict[str, Any], text: str) -> bool:
    gate = failure_data.get("machine_gate_result")
    if isinstance(gate, dict) and (gate.get("blocked") is True or gate.get("passed") is False):
        return True
    gates = failure_data.get("machine_gates_checked")
    if isinstance(gates, list):
        for entry in gates:
            if isinstance(entry, dict) and (entry.get("blocked") is True or entry.get("passed") is False):
                return True
    return "machine gate" in text or "gate blocked" in text or "gate_profile" in text and "blocked" in text


def _execution_denied(failure_data: dict[str, Any], text: str) -> bool:
    return (
        failure_data.get("execution_allowed") is False
        or failure_data.get("real_codex_execution_enabled") is False
        or "default-deny" in text
        or "default deny" in text
        or "execution-enabled" in text
        or "explicit allow" in text
    )


def _dirty_worktree(failure_data: dict[str, Any], text: str) -> bool:
    return failure_data.get("dirty_tree_detected") is True or "dirty worktree" in text or "working tree has local changes" in text


def _timed_out(failure_data: dict[str, Any], text: str, exit_code: int | None) -> bool:
    return failure_data.get("timed_out") is True or exit_code == 124 or "timed out" in text or "timeout" in text


def _validation_failed(failure_data: dict[str, Any], text: str) -> bool:
    if failure_data.get("validation_passed") is False:
        return True
    validation_run = failure_data.get("validation_run")
    if isinstance(validation_run, list):
        return any(isinstance(entry, dict) and entry.get("passed") is False for entry in validation_run)
    return "validation failed" in text or "pytest" in text and "failed" in text


def _evidence_missing(failure_data: dict[str, Any], text: str) -> bool:
    if failure_data.get("evidence_missing") is True:
        return True
    if failure_data.get("result_artifact_missing") is True:
        return True
    return "missing evidence" in text or "no stdout" in text or "result artifact" in text and "missing" in text


def _failure_text(failure_data: dict[str, Any], artifact_errors: list[str]) -> str:
    chunks: list[str] = []
    for key in (
        "failure_type",
        "error_type",
        "error",
        "status",
        "stderr",
        "stdout",
        "result_text",
        "next_safe_action",
    ):
        value = failure_data.get(key)
        if value:
            chunks.append(str(value))
    chunks.extend(_list(failure_data.get("blocked_reasons")))
    chunks.extend(_list(failure_data.get("warnings")))
    chunks.extend(artifact_errors)
    return "\n".join(chunks).lower()


def _exit_code(failure_data: dict[str, Any]) -> int | None:
    value = failure_data.get("exit_code", failure_data.get("returncode"))
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, str):
        text = value.strip()
        if text.startswith("-"):
            return int(text) if text[1:].isdigit() else None
        return int(text) if text.isdigit() else None
    return None


def _load_failure_artifact(path: Path) -> tuple[dict[str, Any], list[str]]:
    if not path.exists():
        return {}, [f"Failure artifact is missing: {path}"]
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        return {}, [f"Failure artifact is not valid JSON: {exc.msg}."]
    except OSError as exc:
        return {}, [f"Failure artifact could not be read: {exc}."]
    if not isinstance(raw, dict):
        return {}, ["Failure artifact JSON root must be an object."]
    return raw, []


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
