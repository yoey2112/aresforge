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

COMMAND_NAME = "inspect-codex-execution-enablements"
PROFILE_TYPE = "codex_execution_enablement_profile_v1"
PROFILE_VERSION = "m142.1"
DEFAULT_ITEM_ID = "m142-real-codex-execution-enablement-profile"
DEFAULT_PROJECT_ID = "aresforge"

_BOUNDARY_CONFIRMATIONS: tuple[str, ...] = (
    "M142 inspects machine-gated enablement profiles for real Codex execution.",
    "Real Codex execution is default-deny from this command.",
    "This command does not invoke Codex, run models, apply patches, call GitHub, mutate queue state, or start another item.",
    "Future real Codex execution must use a separate explicit command, explicit allow flag, prepared local artifact, and passing machine gate.",
)

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


def inspect_codex_execution_enablements(
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

    read_gate = _gate_payload(
        config,
        item_id=normalized_item_id,
        gate_profile="read_only_agent",
        queue_path=queue_path,
    )
    gate_summary = _gate_summary(read_gate)
    llm_decision = _llm_decision_summary(
        config,
        item_id=normalized_item_id,
        queue_path=queue_path,
    )
    codex_agent = _codex_agent_summary(config)

    warnings = _warnings(item=item, gate_payload=read_gate, project_id=normalized_project_id)
    blocked_reasons = _blocked_reasons(item=item, gate_payload=read_gate)
    blocked = bool(blocked_reasons)

    payload: dict[str, Any] = {
        "record_type": PROFILE_TYPE,
        "artifact_type": PROFILE_TYPE,
        "profile_version": PROFILE_VERSION,
        "generated": True,
        "generated_at": _now_iso(),
        "item_id": normalized_item_id,
        "project_id": normalized_project_id,
        "run_id": f"{normalized_item_id}:codex-enablement-profile-v1",
        "status": "blocked" if blocked else "default_denied",
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
        "real_codex_execution_default": "deny",
        "real_codex_execution_enabled": False,
        "required_machine_gate_profiles": ["codex_dispatch", "multi_agent_orchestration"],
        "required_explicit_flags": ["--execution-enabled", "--allow-codex"],
        "required_artifacts": [
            "prepared Codex dispatch artifact",
            "local execution record with safety flags",
            "post-execution M136 validation evidence before completion",
        ],
        "enablement_profiles": _enablement_profiles(),
        "codex_agent_summary": codex_agent,
        "llm_decision_policy_summary": llm_decision,
        "prohibited_operations": list(_PROHIBITED_OPERATIONS),
        "recommended_profile_artifact_path": str(
            (config.repo_root / ".aresforge" / "codex_execution" / "enablements" / "m142-profile.json").resolve()
        ),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }
    return _emit_or_write(config=config, payload=payload, output=output, force=force)


def _enablement_profiles() -> list[dict[str, Any]]:
    return [
        {
            "profile_id": "real_codex_default_deny",
            "description": "Default inspection profile. It documents requirements and performs no Codex execution.",
            "enabled_by_default": True,
            "real_codex_execution_allowed": False,
            "machine_gate_profile": "read_only_agent",
            "required_explicit_flags": [],
            "allowed_actions": ["inspect_enablement_profile"],
            "blocked_actions": ["invoke_codex", "apply_patch", "call_github", "complete_queue_item"],
            "next_safe_action": "Review the profile; select a separate explicit gated command for any future Codex dispatch.",
        },
        {
            "profile_id": "codex_dispatch_dry_run",
            "description": "Prepared dispatch artifact inspection and dry-run capture without invoking Codex.",
            "enabled_by_default": False,
            "real_codex_execution_allowed": False,
            "machine_gate_profile": "codex_dispatch",
            "required_explicit_flags": ["--dry-run"],
            "allowed_actions": ["validate_dispatch_artifact", "write_local_dry_run_record"],
            "blocked_actions": ["invoke_codex", "apply_patch", "call_github", "complete_queue_item"],
            "next_safe_action": "Use run-codex-dispatch --dry-run with a reviewed artifact before considering real execution.",
        },
        {
            "profile_id": "gated_single_codex_dispatch",
            "description": "One prepared Codex dispatch may run only through M135 after explicit enablement and passing gates.",
            "enabled_by_default": False,
            "real_codex_execution_allowed": True,
            "machine_gate_profile": "codex_dispatch",
            "required_explicit_flags": ["--execution-enabled"],
            "required_inputs": [
                "ready queue item",
                "satisfied dependencies",
                "prepared local dispatch artifact",
                "required local-only safety flags",
            ],
            "post_execution_requirements": [
                "capture stdout and stderr as local artifacts",
                "run M136 ingestion and validation before any completion decision",
                "preserve manual/operator review for source changes",
            ],
            "blocked_actions": ["apply_patch_by_aresforge", "call_github", "complete_queue_item", "start_next_item"],
            "next_safe_action": "Run only a single prepared dispatch through run-codex-dispatch --execution-enabled after gates pass.",
        },
        {
            "profile_id": "gated_orchestrated_codex_step",
            "description": "A Codex step inside orchestration remains blocked unless orchestration supplies --allow-codex and each step gate passes.",
            "enabled_by_default": False,
            "real_codex_execution_allowed": True,
            "machine_gate_profile": "multi_agent_orchestration",
            "required_explicit_flags": ["--allow-codex"],
            "required_inputs": ["orchestration plan", "step-declared machine gate", "checkpointed run history"],
            "post_execution_requirements": ["record timeline", "stop on first blocked or failed step", "validate through M136"],
            "blocked_actions": ["continue_after_failed_gate", "queue_completion", "automatic_next_item_execution"],
            "next_safe_action": "Use run-agent-orchestration --allow-codex only for an explicit plan and review every generated artifact.",
        },
    ]


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


def _llm_decision_summary(
    config: AppConfig,
    *,
    item_id: str,
    queue_path: str | Path | None,
) -> dict[str, Any]:
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
    if item and str(item.get("status", "")).strip() == "done":
        warnings.append("Queue item is already done; this profile remains useful as a stable capability contract.")
    return _dedupe(warnings)


def _blocked_reasons(*, item: dict[str, Any], gate_payload: dict[str, Any]) -> list[str]:
    reasons = _list(gate_payload.get("blocked_reasons"))
    if not item:
        reasons.append("Queue item must exist before this enablement profile can be used as local capability evidence.")
    return _dedupe(reasons)


def _next_safe_action(*, blocked: bool) -> str:
    if blocked:
        return "Resolve read-only machine gate blockers before relying on Codex execution enablement metadata."
    return "Keep real Codex execution disabled by default; use only separate explicit gated commands for one reviewed dispatch."


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
