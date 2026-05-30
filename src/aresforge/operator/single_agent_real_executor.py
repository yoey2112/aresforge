from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.agent_registry import build_agent_registry
from aresforge.operator.local_project_queue import resolve_project_queue_path
from aresforge.operator.single_agent_dry_run_executor import (
    SUPPORTED_DRY_RUN_AGENTS,
    _agent_outputs,
    _forbidden_capabilities_blocked,
    _list,
    _load_or_build_plan,
    _load_queue_item,
    _resolve_path,
)

COMMAND_NAME = "run-agent"
EXECUTION_RECORD_VERSION = "m130.1"

SUPPORTED_REAL_AGENTS: tuple[str, ...] = SUPPORTED_DRY_RUN_AGENTS

_BLOCKED_REAL_AGENTS: tuple[str, ...] = (
    "codex-dispatch-agent",
    "local-llm-advisory-agent",
    "documentation-agent",
    "github-sync-agent",
    "approval-ledger-agent",
    "transaction-log-agent",
)

_ALLOWED_MUTATION_SCOPES: tuple[str, ...] = ("artifact_only",)

_BOUNDARY_CONFIRMATIONS: tuple[str, ...] = (
    "M130 runs only deterministic low-risk local agents.",
    "M130 real execution may write local execution records and local artifact files only.",
    "M130 does not execute Codex, Codex CLI, Ollama, local LLMs, remote LLMs, GitHub, gh, network services, validation commands, or patches.",
    "M130 does not mutate source files, apply documentation patches, complete queue items, or start follow-on work.",
)


def run_single_agent_real_execution(
    config: AppConfig,
    *,
    agent_id: str,
    item_id: str,
    queue_path: str | Path | None = None,
    output: str | Path | None = None,
    force: bool = False,
    require_machine_gates: bool = False,
    output_format: str = "json",
) -> dict[str, Any]:
    fmt = str(output_format or "json").lower().strip()
    if fmt != "json":
        return _error("invalid_format", {"format": output_format, "supported_formats": ["json"]})

    started_at = _now_iso()
    normalized_agent_id = str(agent_id or "").strip()
    normalized_item_id = str(item_id or "").strip()
    registry = build_agent_registry(config)
    registry_agents = {
        str(agent.get("agent_id", "")).strip(): agent
        for agent in registry.get("agents", [])
        if isinstance(agent, dict) and str(agent.get("agent_id", "")).strip()
    }
    agent = registry_agents.get(normalized_agent_id, {})
    item = _load_queue_item(config, item_id=normalized_item_id, queue_path=queue_path)
    plan, plan_warnings = _load_or_build_plan(
        config,
        item_id=normalized_item_id,
        plan_path=None,
        queue_path=queue_path,
    )
    warnings = list(plan_warnings)
    errors: list[str] = []
    if not item:
        errors.append(f"Queue item not found: {normalized_item_id}")
    if not agent:
        errors.append(f"Agent is not registered: {normalized_agent_id}")
    if normalized_agent_id and normalized_agent_id not in SUPPORTED_REAL_AGENTS:
        errors.append(f"Agent is not supported for M130 real execution: {normalized_agent_id}")
    if normalized_agent_id in _BLOCKED_REAL_AGENTS:
        errors.append(f"Agent is explicitly blocked for M130 real execution: {normalized_agent_id}")

    machine_gates_checked = _machine_gates(
        agent=agent,
        agent_id=normalized_agent_id,
        item=item,
    )
    failed_gates = [
        gate["gate_id"]
        for gate in machine_gates_checked
        if isinstance(gate, dict) and not bool(gate.get("passed"))
    ]
    if failed_gates:
        errors.append("Machine gates failed: " + ", ".join(sorted(failed_gates)))
    if require_machine_gates and not machine_gates_checked:
        errors.append("Machine gates were required but no gates were available.")

    forbidden_blocked = _forbidden_capabilities_blocked(agent)
    status = "blocked" if errors else "completed"
    outputs = (
        _agent_outputs(
            config=config,
            agent_id=normalized_agent_id,
            item=item,
            plan=plan,
            queue_path=queue_path,
        )
        if status == "completed"
        else {"summary": "No real local agent artifact was generated because execution was blocked."}
    )
    completed_at = _now_iso()
    payload = {
        "execution_record_type": "single_agent_real_execution",
        "execution_record_version": EXECUTION_RECORD_VERSION,
        "generated": True,
        "agent_id": normalized_agent_id,
        "item_id": normalized_item_id,
        "project_id": str(item.get("project_id", "")).strip(),
        "dry_run": False,
        "real_execution": True,
        "started_at": started_at,
        "completed_at": completed_at,
        "status": status,
        "machine_gates_checked": machine_gates_checked,
        "machine_gates_passed": not failed_gates,
        "inputs": {
            "queue_path": str(resolve_project_queue_path(config.repo_root, queue_path)),
            "agent_registered": bool(agent),
            "supported_real_agents": list(SUPPORTED_REAL_AGENTS),
            "require_machine_gates": bool(require_machine_gates),
        },
        "outputs": outputs,
        "artifacts_created": [],
        "mutation_performed": False,
        "mutation_scope": "local_execution_record" if status == "completed" else "none",
        "warnings": sorted({warning for warning in warnings if warning}),
        "errors": sorted({error for error in errors if error}),
        "capabilities_used": _capabilities_used(agent),
        "forbidden_capabilities_blocked": forbidden_blocked,
        "external_execution_performed": False,
        "model_execution_performed": False,
        "github_execution_performed": False,
        "patch_application_performed": False,
        "local_only": True,
        "next_safe_action": _next_safe_action(status, normalized_agent_id),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }
    return _write_execution_record(
        config=config,
        payload=payload,
        output=output,
        force=force,
    )


def _machine_gates(*, agent: dict[str, Any], agent_id: str, item: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _gate("agent_registered", bool(agent), "Agent must exist in the local M126 registry."),
        _gate(
            "agent_allowed_for_m130",
            agent_id in SUPPORTED_REAL_AGENTS,
            "Agent must be one of the deterministic M130 real-execution agents.",
        ),
        _gate(
            "agent_not_explicitly_blocked",
            agent_id not in _BLOCKED_REAL_AGENTS,
            "High-risk, network, model, GitHub, patch, and audit-ledger agents are blocked.",
        ),
        _gate(
            "registry_real_execution_enabled",
            bool(agent.get("can_run_real")) if agent else False,
            "Agent registry must mark the agent as eligible for M130 real execution.",
        ),
        _gate("queue_item_exists", bool(item), "Queue item must be present in the local queue."),
        _gate(
            "network_scope_none",
            str(agent.get("network_scope", "")).strip() == "none",
            "Real execution requires network_scope=none.",
        ),
        _gate(
            "model_scope_none",
            str(agent.get("model_scope", "")).strip() == "none",
            "Real execution requires model_scope=none.",
        ),
        _gate(
            "mutation_scope_artifact_only",
            str(agent.get("mutation_scope", "")).strip() in _ALLOWED_MUTATION_SCOPES,
            "Real execution may write only local execution/artifact records.",
        ),
        _gate(
            "forbidden_capabilities_blocked",
            _forbidden_capability_gate(agent),
            "Forbidden external/model/GitHub/patch capabilities must be declared and blocked.",
        ),
    ]


def _forbidden_capability_gate(agent: dict[str, Any]) -> bool:
    forbidden = set(_list(agent.get("forbidden_capabilities")) if agent else [])
    required = {
        "apply_patch",
        "call_github_api",
        "call_gh",
        "call_external_network",
        "execute_codex",
        "execute_ollama_prompt",
        "execute_local_llm",
    }
    return required.issubset(forbidden)


def _gate(gate_id: str, passed: bool, description: str) -> dict[str, Any]:
    return {
        "gate_id": gate_id,
        "passed": bool(passed),
        "description": description,
    }


def _write_execution_record(
    *,
    config: AppConfig,
    payload: dict[str, Any],
    output: str | Path | None,
    force: bool,
) -> dict[str, Any]:
    output_path = (
        _resolve_path(config.repo_root, output)
        if output is not None
        else _default_output_path(config, payload)
    )
    if output_path.exists() and not force:
        blocked = dict(payload)
        blocked["status"] = "blocked"
        blocked["mutation_performed"] = False
        blocked["mutation_scope"] = "none"
        blocked["errors"] = sorted(
            {*_list(payload.get("errors")), "Output file already exists. Re-run with --force to overwrite."}
        )
        blocked["next_safe_action"] = "Choose a new output path or rerun with --force; no real execution record was written."
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
    if payload.get("status") == "completed":
        artifact_payload = dict(payload)
        artifact_payload["mutation_performed"] = True
        artifact_payload["artifacts_created"] = [str(output_path)]
        rendered = json.dumps(artifact_payload, indent=2)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered + "\n", encoding="utf-8")
        return {
            "command": COMMAND_NAME,
            "ok": True,
            "local_only": True,
            "format": "json",
            "output": str(output_path),
            "force": force,
            "wrote_output_file": True,
            "stdout": rendered,
            "payload": artifact_payload,
        }
    rendered = json.dumps(payload, indent=2)
    return {
        "command": COMMAND_NAME,
        "ok": False,
        "local_only": True,
        "format": "json",
        "output": str(output_path),
        "force": force,
        "wrote_output_file": False,
        "stdout": rendered,
        "payload": payload,
    }


def _default_output_path(config: AppConfig, payload: dict[str, Any]) -> Path:
    item_id = str(payload.get("item_id", "")).strip() or "unknown-item"
    agent_id = str(payload.get("agent_id", "")).strip() or "unknown-agent"
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return (config.artifact_root / "agent-real-executions" / item_id / f"{agent_id}-{stamp}.json").resolve()


def _capabilities_used(agent: dict[str, Any]) -> list[str]:
    allowed = set(_list(agent.get("allowed_capabilities")) if agent else [])
    safe_used = {"read_local_queue", "read_local_artifacts", "generate_plan_artifact", "generate_review_artifact"}
    return sorted(allowed.intersection(safe_used))


def _next_safe_action(status: str, agent_id: str) -> str:
    if status != "completed":
        return "Review errors and machine gates before retrying M130 real execution."
    if agent_id == "validation-agent":
        return "Review the local execution record and run validation commands manually when appropriate."
    return "Review the local execution record and continue only with explicit local operator commands."


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
