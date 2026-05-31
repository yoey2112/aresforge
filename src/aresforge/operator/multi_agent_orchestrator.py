from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.agent_orchestration_plan_builder import build_agent_orchestration_plan
from aresforge.operator.codex_dispatch_executor import run_codex_dispatch_executor
from aresforge.operator.docs_only_patch_apply import apply_docs_only_patch
from aresforge.operator.github_sync_agent import run_github_sync_agent
from aresforge.operator.local_llm_advisory_execution import run_local_llm_advisory_execution
from aresforge.operator.machine_safety_gate_engine import evaluate_machine_safety_gates
from aresforge.operator.single_agent_dry_run_executor import SUPPORTED_DRY_RUN_AGENTS, run_single_agent_dry_run
from aresforge.operator.single_agent_real_executor import SUPPORTED_REAL_AGENTS, run_single_agent_real_execution

COMMAND_NAME = "run-agent-orchestration"
EXECUTION_RECORD_VERSION = "m138.1"

SUPPORTED_PATTERNS: tuple[str, ...] = (
    "read-only planning chain",
    "docs-only reconciliation chain",
    "Codex dispatch dry-run chain",
    "low-risk validation chain",
    "sprint summary dry-run chain",
)

_LOCAL_LLM_AGENTS = frozenset({"local-llm-advisory-agent"})
_CODEX_AGENTS = frozenset({"codex-dispatch-agent"})
_GITHUB_AGENTS = frozenset({"github-sync-agent"})
_DOCS_PATCH_AGENTS = frozenset({"documentation-agent"})

_FORBIDDEN_CAPABILITIES = (
    "apply_patch",
    "mutate_queue_without_operator",
    "call_github_api",
    "call_gh",
    "call_external_network",
    "create_pr_or_issue",
    "background_daemon",
    "automatic_next_item_execution",
    "execute_codex",
    "execute_ollama_prompt",
    "execute_local_llm",
    "run_validation_commands",
    "merge_pr",
    "force_push",
)

_BOUNDARY_CONFIRMATIONS = (
    "M138 executes one orchestration plan step-by-step with machine gates.",
    "M138 is dry-run by default.",
    "M138 real execution is limited to deterministic low-risk local agents unless a dedicated allow flag is supplied.",
    "M138 stops on the first required gate failure or blocked step.",
    "M138 does not merge PRs, force push, bypass machine gates, or continue after a blocking failure.",
)


def run_multi_agent_orchestration(
    config: AppConfig,
    *,
    item_id: str,
    plan_path: str | Path | None = None,
    dry_run: bool = False,
    max_steps: int | None = None,
    allow_low_risk_real: bool = False,
    allow_local_llm: bool = False,
    allow_codex: bool = False,
    allow_github_sync: bool = False,
    queue_path: str | Path | None = None,
    output: str | Path | None = None,
    force: bool = False,
    output_format: str = "json",
) -> dict[str, Any]:
    fmt = str(output_format or "json").strip().lower()
    if fmt != "json":
        return _error("invalid_format", {"format": output_format, "supported_formats": ["json"]})

    normalized_item_id = str(item_id or "").strip()
    started_at = _now_iso()
    effective_dry_run = bool(dry_run) or not any(
        (allow_low_risk_real, allow_local_llm, allow_codex, allow_github_sync)
    )
    resolved_plan_path = _resolve(config.repo_root, plan_path) if plan_path else None
    plan, plan_errors = _load_or_build_plan(
        config,
        item_id=normalized_item_id,
        plan_path=resolved_plan_path,
        queue_path=queue_path,
    )
    steps = _steps_from_plan(plan)
    limit = _positive_int(max_steps)
    selected_steps = steps[:limit] if limit is not None else steps

    artifacts_created: list[str] = []
    step_results: list[dict[str, Any]] = []
    machine_gates_checked: list[dict[str, Any]] = []
    forbidden_capabilities_blocked = set(_FORBIDDEN_CAPABILITIES)
    blocked_reasons: list[str] = list(plan_errors)

    performed = {
        "local_llm": False,
        "codex": False,
        "github": False,
        "patch": False,
        "queue": False,
    }

    if not normalized_item_id:
        blocked_reasons.append("Item id is required.")
    if not plan:
        blocked_reasons.append("No orchestration plan could be loaded or built.")

    for index, step in enumerate(selected_steps, start=1):
        if blocked_reasons:
            break
        result = _run_step(
            config,
            item_id=normalized_item_id,
            step=step,
            step_index=index,
            dry_run=effective_dry_run,
            allow_low_risk_real=allow_low_risk_real,
            allow_local_llm=allow_local_llm,
            allow_codex=allow_codex,
            allow_github_sync=allow_github_sync,
            queue_path=queue_path,
            force=force,
        )
        step_results.append(result)
        machine_gates_checked.extend(result.get("machine_gates_checked", []))
        artifacts_created.extend(_list(result.get("artifacts_created")))
        forbidden_capabilities_blocked.update(_list(result.get("forbidden_capabilities_blocked")))
        performed["local_llm"] = performed["local_llm"] or bool(result.get("local_llm_execution_performed"))
        performed["codex"] = performed["codex"] or bool(result.get("codex_execution_performed"))
        performed["github"] = performed["github"] or bool(result.get("github_execution_performed"))
        performed["patch"] = performed["patch"] or bool(result.get("patch_application_performed"))
        performed["queue"] = performed["queue"] or bool(result.get("queue_mutation_performed"))
        if bool(result.get("blocked")):
            blocked_reasons.extend(_list(result.get("blocked_reasons")))
            break

    blocked = bool(blocked_reasons)
    steps_attempted = len(step_results)
    steps_blocked = sum(1 for result in step_results if bool(result.get("blocked")))
    steps_completed = sum(1 for result in step_results if str(result.get("status", "")).strip() == "completed")
    status = _status(
        blocked=blocked,
        steps_total=len(steps),
        steps_attempted=steps_attempted,
        max_steps=limit,
    )
    completed_at = _now_iso()

    payload = {
        "execution_record_type": "multi_agent_orchestration_v1",
        "execution_record_version": EXECUTION_RECORD_VERSION,
        "item_id": normalized_item_id,
        "plan_path": str(resolved_plan_path) if resolved_plan_path else "",
        "dry_run": bool(effective_dry_run),
        "started_at": started_at,
        "completed_at": completed_at,
        "status": status,
        "steps_total": len(steps),
        "steps_attempted": steps_attempted,
        "steps_completed": steps_completed,
        "steps_blocked": steps_blocked,
        "step_results": step_results,
        "artifacts_created": sorted(set(artifacts_created)),
        "machine_gates_checked": machine_gates_checked,
        "forbidden_capabilities_blocked": sorted(forbidden_capabilities_blocked),
        "local_llm_execution_performed": performed["local_llm"],
        "codex_execution_performed": performed["codex"],
        "github_execution_performed": performed["github"],
        "patch_application_performed": performed["patch"],
        "queue_mutation_performed": performed["queue"],
        "blocked": blocked,
        "blocked_reasons": _dedupe(blocked_reasons),
        "next_safe_action": _next_safe_action(
            blocked=blocked,
            status=status,
            max_steps=limit,
            steps_total=len(steps),
            steps_attempted=steps_attempted,
        ),
        "supported_patterns": list(SUPPORTED_PATTERNS),
        "allow_flags": {
            "allow_low_risk_real": bool(allow_low_risk_real),
            "allow_local_llm": bool(allow_local_llm),
            "allow_codex": bool(allow_codex),
            "allow_github_sync": bool(allow_github_sync),
        },
        "local_only": not (performed["github"] or performed["codex"]),
        "external_execution_performed": bool(performed["github"] or performed["codex"]),
        "model_execution_performed": bool(performed["local_llm"]),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }
    return _emit_or_write(config=config, payload=payload, output=output, force=force)


def _run_step(
    config: AppConfig,
    *,
    item_id: str,
    step: dict[str, Any],
    step_index: int,
    dry_run: bool,
    allow_low_risk_real: bool,
    allow_local_llm: bool,
    allow_codex: bool,
    allow_github_sync: bool,
    queue_path: str | Path | None,
    force: bool,
) -> dict[str, Any]:
    agent_id = str(step.get("agent_id", "")).strip()
    step_id = str(step.get("step_id", "")).strip() or f"step-{step_index:02d}-{agent_id or 'unknown-agent'}"
    mode = _step_mode(
        agent_id=agent_id,
        step=step,
        dry_run=dry_run,
        allow_low_risk_real=allow_low_risk_real,
        allow_local_llm=allow_local_llm,
        allow_codex=allow_codex,
        allow_github_sync=allow_github_sync,
    )
    gate_profile = _gate_profile(agent_id=agent_id, step=step, mode=mode)
    artifact_path = _optional_path(_step_artifact_path(step))
    patch_path = _optional_path(_step_patch_path(step))
    execution_record = _optional_path(_step_execution_record(step)) or artifact_path
    gate_result = evaluate_machine_safety_gates(
        config,
        item_id=item_id,
        gate_profile=gate_profile,
        artifact_path=artifact_path,
        patch_path=patch_path,
        execution_record=execution_record,
        queue_path=queue_path,
        force=bool(mode in {"codex_real", "github_real"} or force),
        output_format="json",
    )
    machine_gate = gate_result.get("payload", {}) if isinstance(gate_result, dict) else {}
    gate_summary = _gate_summary(step_id=step_id, agent_id=agent_id, machine_gate=machine_gate)
    if machine_gate.get("passed") is not True or machine_gate.get("blocked") is True:
        return _blocked_step(
            step_id=step_id,
            agent_id=agent_id,
            mode=mode,
            gate_profile=gate_profile,
            machine_gate=gate_summary,
            reasons=[
                f"Machine safety gate profile {gate_profile} did not pass.",
                *_list(machine_gate.get("blocked_reasons")),
            ],
        )

    if mode == "dry_run":
        result = _run_dry_step(
            config,
            item_id=item_id,
            agent_id=agent_id,
            step=step,
            queue_path=queue_path,
        )
    elif mode == "low_risk_real":
        result = run_single_agent_real_execution(
            config,
            agent_id=agent_id,
            item_id=item_id,
            queue_path=queue_path,
            force=force,
            require_machine_gates=True,
            output_format="json",
        )
    elif mode == "docs_patch_apply":
        result = apply_docs_only_patch(
            config,
            item_id=item_id,
            patch_path=_step_patch_path(step) or "",
            dry_run=False,
            force=force,
            queue_path=queue_path,
            output_format="json",
        )
    elif mode == "local_llm_real":
        result = run_local_llm_advisory_execution(
            config,
            item_id=item_id,
            artifact_path=_step_artifact_path(step) or "",
            dry_run=False,
            force=force,
            queue_path=queue_path,
            output_format="json",
        )
    elif mode == "codex_real":
        result = run_codex_dispatch_executor(
            config,
            item_id=item_id,
            artifact_path=_step_artifact_path(step) or "",
            dry_run=False,
            execution_enabled=True,
            force=force,
            queue_path=queue_path,
            output_format="json",
        )
    elif mode == "github_real":
        result = run_github_sync_agent(
            config,
            item_id=item_id,
            sync_mode=str(step.get("sync_mode", "issue-comment")),
            dry_run=False,
            github_enabled=True,
            repo=str(step.get("repo", "") or ""),
            issue_number=step.get("issue_number"),
            pr_number=step.get("pr_number"),
            artifact_path=_step_artifact_path(step),
            force=force,
            queue_path=queue_path,
            output_format="json",
        )
    else:
        result = {"ok": False, "payload": {"blocked": True, "blocked_reasons": [f"Step mode is not allowed: {mode}"]}}

    payload = result.get("payload", {}) if isinstance(result, dict) else {}
    blocked = _step_payload_blocked(payload, result)
    return {
        "step_id": step_id,
        "sequence": step_index,
        "agent_id": agent_id,
        "mode": mode,
        "dry_run": mode == "dry_run",
        "status": "blocked" if blocked else "completed",
        "blocked": blocked,
        "blocked_reasons": _blocked_reasons_from_step(payload, result),
        "machine_gate_profile": gate_profile,
        "machine_gates_checked": [gate_summary],
        "machine_gates_passed": True,
        "artifacts_created": _step_artifacts(payload),
        "forbidden_capabilities_blocked": _forbidden_from_step(step, payload),
        "local_llm_execution_performed": bool(payload.get("model_execution_performed")),
        "codex_execution_performed": bool(payload.get("codex_execution_performed")),
        "github_execution_performed": bool(payload.get("github_operation_performed") or payload.get("github_execution_performed")),
        "patch_application_performed": bool(payload.get("patch_application_performed")),
        "queue_mutation_performed": bool(payload.get("queue_mutation_performed")),
        "result_summary": _result_summary(agent_id=agent_id, mode=mode, payload=payload),
    }


def _step_mode(
    *,
    agent_id: str,
    step: dict[str, Any],
    dry_run: bool,
    allow_low_risk_real: bool,
    allow_local_llm: bool,
    allow_codex: bool,
    allow_github_sync: bool,
) -> str:
    if dry_run:
        return "dry_run"
    if agent_id in _LOCAL_LLM_AGENTS:
        return "local_llm_real" if allow_local_llm else "blocked_high_risk"
    if agent_id in _CODEX_AGENTS:
        return "codex_real" if allow_codex else "blocked_high_risk"
    if agent_id in _GITHUB_AGENTS:
        return "github_real" if allow_github_sync else "blocked_high_risk"
    if agent_id in _DOCS_PATCH_AGENTS and _step_patch_path(step):
        return "docs_patch_apply" if allow_low_risk_real else "blocked_high_risk"
    if agent_id in SUPPORTED_REAL_AGENTS and allow_low_risk_real:
        return "low_risk_real"
    return "dry_run"


def _gate_profile(*, agent_id: str, step: dict[str, Any], mode: str) -> str:
    if mode == "low_risk_real":
        return "local_artifact_write"
    if mode == "docs_patch_apply":
        return "docs_only_patch_apply"
    if mode == "local_llm_real":
        return "local_llm_execution"
    if mode == "codex_real":
        return "codex_dispatch"
    if mode == "github_real":
        return "github_sync"
    if agent_id in _DOCS_PATCH_AGENTS and _step_patch_path(step) and mode == "dry_run":
        return "docs_only_patch_apply"
    return "read_only_agent"


def _run_dry_step(
    config: AppConfig,
    *,
    item_id: str,
    agent_id: str,
    step: dict[str, Any],
    queue_path: str | Path | None,
) -> dict[str, Any]:
    if agent_id in _DOCS_PATCH_AGENTS and _step_patch_path(step):
        return apply_docs_only_patch(
            config,
            item_id=item_id,
            patch_path=_step_patch_path(step) or "",
            dry_run=True,
            queue_path=queue_path,
            output_format="json",
        )
    if agent_id in SUPPORTED_DRY_RUN_AGENTS:
        return run_single_agent_dry_run(
            config,
            agent_id=agent_id,
            item_id=item_id,
            queue_path=queue_path,
            output_format="json",
        )
    payload = {
        "execution_record_type": "multi_agent_step_dry_run",
        "agent_id": agent_id,
        "item_id": item_id,
        "dry_run": True,
        "status": "completed",
        "blocked": False,
        "blocked_reasons": [],
        "artifacts_created": [],
        "forbidden_capabilities_blocked": _forbidden_from_step(step, {}),
        "local_only": True,
        "external_execution_performed": False,
        "model_execution_performed": False,
        "github_execution_performed": False,
        "codex_execution_performed": False,
        "patch_application_performed": False,
        "queue_mutation_performed": False,
        "result_summary": "Dry-run planning step completed without invoking the high-risk agent.",
    }
    return {"ok": True, "payload": payload}


def _blocked_step(
    *,
    step_id: str,
    agent_id: str,
    mode: str,
    gate_profile: str,
    machine_gate: dict[str, Any],
    reasons: list[str],
) -> dict[str, Any]:
    return {
        "step_id": step_id,
        "sequence": _sequence_from_step_id(step_id),
        "agent_id": agent_id,
        "mode": mode,
        "dry_run": mode == "dry_run",
        "status": "blocked",
        "blocked": True,
        "blocked_reasons": _dedupe(reasons),
        "machine_gate_profile": gate_profile,
        "machine_gates_checked": [machine_gate],
        "machine_gates_passed": False,
        "artifacts_created": [],
        "forbidden_capabilities_blocked": sorted(_FORBIDDEN_CAPABILITIES),
        "local_llm_execution_performed": False,
        "codex_execution_performed": False,
        "github_execution_performed": False,
        "patch_application_performed": False,
        "queue_mutation_performed": False,
        "result_summary": "Step blocked before execution.",
    }


def _load_or_build_plan(
    config: AppConfig,
    *,
    item_id: str,
    plan_path: Path | None,
    queue_path: str | Path | None,
) -> tuple[dict[str, Any], list[str]]:
    if plan_path is not None:
        if not plan_path.exists():
            return {}, [f"Plan path does not exist: {plan_path}"]
        try:
            raw = json.loads(plan_path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError) as exc:
            return {}, [f"Plan path could not be parsed as JSON: {exc}"]
        if not isinstance(raw, dict):
            return {}, ["Plan path JSON root must be an object."]
        return raw, []
    result = build_agent_orchestration_plan(
        config,
        item_id=item_id,
        queue_path=queue_path,
        output_format="json",
    )
    payload = result.get("payload", {}) if isinstance(result, dict) else {}
    warnings = []
    if not payload:
        warnings.append("No generated orchestration plan payload was returned.")
    return payload, warnings


def _steps_from_plan(plan: dict[str, Any]) -> list[dict[str, Any]]:
    steps = plan.get("steps", []) if isinstance(plan, dict) else []
    if not isinstance(steps, list):
        return []
    return [step for step in steps if isinstance(step, dict)]


def _gate_summary(*, step_id: str, agent_id: str, machine_gate: dict[str, Any]) -> dict[str, Any]:
    return {
        "step_id": step_id,
        "agent_id": agent_id,
        "gate_profile": str(machine_gate.get("gate_profile", "")),
        "passed": bool(machine_gate.get("passed")) and not bool(machine_gate.get("blocked")),
        "blocked": bool(machine_gate.get("blocked")),
        "blocked_reasons": _list(machine_gate.get("blocked_reasons")),
        "checks_failed": [
            str(check.get("check_id", ""))
            for check in machine_gate.get("checks", [])
            if isinstance(check, dict) and not bool(check.get("passed")) and not bool(check.get("warning_only"))
        ],
    }


def _step_payload_blocked(payload: dict[str, Any], result: dict[str, Any]) -> bool:
    if result.get("ok") is False:
        return True
    if payload.get("blocked") is True:
        return True
    return str(payload.get("status", "")).strip() == "blocked"


def _blocked_reasons_from_step(payload: dict[str, Any], result: dict[str, Any]) -> list[str]:
    reasons = _list(payload.get("blocked_reasons"))
    reasons.extend(_list(payload.get("errors")))
    if result.get("ok") is False and not reasons:
        reasons.append("Step executor returned ok=false.")
    return _dedupe(reasons)


def _step_artifacts(payload: dict[str, Any]) -> list[str]:
    artifacts = _list(payload.get("artifacts_created"))
    for key in ("response_artifact_path", "result_artifact_path", "summary_artifact_path"):
        value = str(payload.get(key, "") or "").strip()
        if value:
            artifacts.append(value)
    return _dedupe(artifacts)


def _forbidden_from_step(step: dict[str, Any], payload: dict[str, Any]) -> list[str]:
    forbidden = set(_FORBIDDEN_CAPABILITIES)
    forbidden.update(_list(step.get("forbidden_capabilities")))
    forbidden.update(_list(payload.get("forbidden_capabilities_blocked")))
    return sorted(forbidden)


def _result_summary(*, agent_id: str, mode: str, payload: dict[str, Any]) -> str:
    for key in ("result_summary", "response_summary"):
        text = str(payload.get(key, "") or "").strip()
        if text:
            return text
    outputs = payload.get("outputs")
    if isinstance(outputs, dict) and str(outputs.get("summary", "")).strip():
        return str(outputs.get("summary", "")).strip()
    return f"{agent_id} completed in {mode} mode."


def _step_artifact_path(step: dict[str, Any]) -> str:
    for key in ("artifact_path", "input_artifact_path", "advisory_artifact_path", "codex_artifact_path"):
        value = str(step.get(key, "") or "").strip()
        if value:
            return value
    return ""


def _step_patch_path(step: dict[str, Any]) -> str:
    return str(step.get("patch_path", "") or "").strip()


def _step_execution_record(step: dict[str, Any]) -> str:
    return str(step.get("execution_record", "") or step.get("execution_record_path", "") or "").strip()


def _optional_path(value: str) -> str | None:
    text = str(value or "").strip()
    return text or None


def _status(*, blocked: bool, steps_total: int, steps_attempted: int, max_steps: int | None) -> str:
    if blocked:
        return "blocked"
    if max_steps is not None and steps_attempted < steps_total:
        return "max_steps_reached"
    return "completed"


def _next_safe_action(
    *,
    blocked: bool,
    status: str,
    max_steps: int | None,
    steps_total: int,
    steps_attempted: int,
) -> str:
    if blocked:
        return "Resolve the first blocked step before rerunning; do not continue later orchestration steps."
    if max_steps is not None and steps_attempted < steps_total:
        return "Review the partial timeline and rerun without --max-steps when ready to continue from the next safe step."
    if status == "completed":
        return "Review the orchestration result artifact and proceed only through explicit gated follow-on commands."
    return "Review the orchestration timeline before any further action."


def _emit_or_write(
    *,
    config: AppConfig,
    payload: dict[str, Any],
    output: str | Path | None,
    force: bool,
) -> dict[str, Any]:
    output_path = _resolve(config.repo_root, output) if output else _default_output_path(config, payload)
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
    artifact_payload["artifacts_created"] = sorted(
        set([*_list(payload.get("artifacts_created")), str(output_path)])
    )
    rendered = json.dumps(artifact_payload, indent=2)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered + "\n", encoding="utf-8")
    return {
        "command": COMMAND_NAME,
        "ok": not bool(artifact_payload.get("blocked")),
        "local_only": bool(artifact_payload.get("local_only", True)),
        "format": "json",
        "output": str(output_path),
        "force": force,
        "wrote_output_file": True,
        "stdout": rendered,
        "payload": artifact_payload,
    }


def _default_output_path(config: AppConfig, payload: dict[str, Any]) -> Path:
    item_id = str(payload.get("item_id", "") or "unknown-item").strip()
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    return (config.artifact_root / "multi-agent-orchestration" / _safe_id(item_id) / f"{stamp}.json").resolve()


def _resolve(repo_root: Path, value: str | Path | None) -> Path:
    path = Path(str(value or ""))
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


def _positive_int(value: Any) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool) and value > 0:
        return value
    text = str(value or "").strip()
    if text.isdigit() and int(text) > 0:
        return int(text)
    return None


def _sequence_from_step_id(step_id: str) -> int:
    parts = str(step_id or "").split("-")
    for part in parts:
        if part.isdigit():
            return int(part)
    return 0


def _safe_id(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in str(value or "").strip().lower())
    return cleaned.strip("-") or "multi-agent-orchestration"


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
