from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.agent_registry import build_agent_registry
from aresforge.operator.llm_decision_policy import recommend_llm_decision
from aresforge.operator.local_project_queue import resolve_project_queue_path

COMMAND_NAME = "build-agent-orchestration-plan"
PLAN_VERSION = "m128.1"
SUPPORTED_EXECUTION_TARGETS = ("dry-run", "real")

_BOUNDARY_CONFIRMATIONS = (
    "M128 builds an orchestration plan only.",
    "M128 does not execute agents, Codex, local LLMs, remote LLMs, GitHub, gh, network services, validation commands, patches, queue mutation, or next-item execution.",
    "Every step preserves execution_performed=false and can_run_real=false until a later explicit operator-approved runner exists.",
)


def build_agent_orchestration_plan(
    config: AppConfig,
    *,
    item_id: str,
    agent_id: str | None = None,
    execution_target: str = "dry-run",
    queue_path: str | Path | None = None,
    output: str | Path | None = None,
    force: bool = False,
    output_format: str = "json",
) -> dict[str, Any]:
    fmt = str(output_format or "json").lower().strip()
    if fmt != "json":
        return _error("invalid_format", {"format": output_format, "supported_formats": ["json"]})

    normalized_target = str(execution_target or "dry-run").strip().lower()
    if normalized_target not in SUPPORTED_EXECUTION_TARGETS:
        return _error(
            "invalid_execution_target",
            {
                "execution_target": execution_target,
                "supported_execution_targets": list(SUPPORTED_EXECUTION_TARGETS),
            },
        )

    normalized_item_id = str(item_id or "").strip()
    item = _load_queue_item(config, item_id=normalized_item_id, queue_path=queue_path)
    registry = build_agent_registry(config)
    decision_result = recommend_llm_decision(
        config,
        item_id=normalized_item_id,
        agent_id=agent_id,
        queue_path=queue_path,
        output_format="json",
    )
    decision_policy = (
        decision_result.get("payload", {}) if isinstance(decision_result.get("payload"), dict) else {}
    )
    payload = _build_payload(
        config=config,
        item_id=normalized_item_id,
        item=item,
        registry=registry,
        decision_policy=decision_policy,
        requested_agent_id=agent_id,
        requested_execution_target=normalized_target,
    )
    return _emit_or_write(config=config, payload=payload, output=output, force=force)


def _build_payload(
    *,
    config: AppConfig,
    item_id: str,
    item: dict[str, Any],
    registry: dict[str, Any],
    decision_policy: dict[str, Any],
    requested_agent_id: str | None,
    requested_execution_target: str,
) -> dict[str, Any]:
    agents = {
        str(agent.get("agent_id", "")): agent
        for agent in registry.get("agents", [])
        if isinstance(agent, dict) and str(agent.get("agent_id", "")).strip()
    }
    blocked_reasons: list[str] = []
    if not item:
        blocked_reasons.append(f"Queue item not found: {item_id}")

    selected_agent_id = _select_primary_agent_id(
        item=item,
        decision_policy=decision_policy,
        requested_agent_id=requested_agent_id,
    )
    if selected_agent_id and selected_agent_id not in agents:
        blocked_reasons.append(f"Requested or selected agent is not registered: {selected_agent_id}")

    steps = _build_steps(
        item=item,
        agents=agents,
        decision_policy=decision_policy,
        selected_agent_id=selected_agent_id,
        requested_execution_target=requested_execution_target,
    )
    blocked_reasons.extend(_dependency_blockers(item))
    if requested_execution_target == "real":
        blocked_reasons.append("Real execution is blocked in M128; orchestration plans are non-executing metadata only.")
    blocked_reasons.extend(reason for step in steps for reason in step.get("blocked_reasons", []))
    blocked_reasons = sorted(set(reason for reason in blocked_reasons if reason))
    blocked = bool(blocked_reasons)

    return {
        "plan_type": "agent_orchestration_plan",
        "plan_version": PLAN_VERSION,
        "generated": True,
        "generated_at": _now_iso(),
        "item_id": item_id,
        "item_found": bool(item),
        "title": str(item.get("title", "") if item else ""),
        "project_id": str(item.get("project_id", "") if item else ""),
        "milestone": _milestone(item),
        "requested_execution_target": requested_execution_target,
        "recommended_execution_target": "dry-run",
        "steps": steps,
        "required_artifacts": _required_artifacts(steps),
        "dependency_checks": _dependency_checks(item),
        "machine_gates_required": sorted(
            {step["step_id"] for step in steps if bool(step.get("machine_gate_required"))}
        ),
        "blocked": blocked,
        "blocked_reasons": blocked_reasons,
        "autonomy_level": _autonomy_level(steps),
        "execution_performed": False,
        "local_only": True,
        "next_safe_action": _next_safe_action(blocked, requested_execution_target),
        "repo_root": str(config.repo_root),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }


def _build_steps(
    *,
    item: dict[str, Any],
    agents: dict[str, dict[str, Any]],
    decision_policy: dict[str, Any],
    selected_agent_id: str,
    requested_execution_target: str,
) -> list[dict[str, Any]]:
    if not item:
        return []
    ordered_agent_ids = ["queue-planner-agent"]
    if selected_agent_id and selected_agent_id not in ordered_agent_ids:
        ordered_agent_ids.append(selected_agent_id)
    for tail_agent in _tail_agents(item):
        if tail_agent not in ordered_agent_ids:
            ordered_agent_ids.append(tail_agent)

    steps: list[dict[str, Any]] = []
    for index, agent_id in enumerate(ordered_agent_ids, start=1):
        agent = agents.get(agent_id, {})
        step_blockers = _step_blockers(
            agent=agent,
            item=item,
            requested_execution_target=requested_execution_target,
        )
        steps.append(
            {
                "step_id": f"step-{index:02d}-{agent_id}",
                "sequence": index,
                "agent_id": agent_id,
                "purpose": _purpose(agent_id, item),
                "input_artifacts": _input_artifacts(agent_id),
                "output_artifacts": list(agent.get("produced_artifacts", [])),
                "decision_policy": _step_decision_policy(decision_policy),
                "allowed_capabilities": list(agent.get("allowed_capabilities", [])),
                "forbidden_capabilities": sorted(
                    set(
                        list(agent.get("forbidden_capabilities", []))
                        + [
                            "execute_agent",
                            "execute_codex",
                            "execute_ollama_prompt",
                            "execute_local_llm",
                            "run_validation_commands",
                            "apply_patch",
                            "mutate_queue_without_operator",
                        ]
                    )
                ),
                "machine_gate_required": bool(agent.get("machine_gate_required", False))
                or requested_execution_target == "real",
                "can_run_dry_run": bool(agent.get("can_run_dry_run", False)),
                "can_run_real": False,
                "blocked": bool(step_blockers),
                "blocked_reasons": step_blockers,
            }
        )
    return steps


def _step_blockers(
    *,
    agent: dict[str, Any],
    item: dict[str, Any],
    requested_execution_target: str,
) -> list[str]:
    blockers: list[str] = []
    if not agent:
        blockers.append("Agent is not registered.")
    supported = {str(value) for value in agent.get("supported_item_types", [])}
    item_type = str(item.get("item_type", "")).strip()
    if supported and item_type and item_type not in supported:
        blockers.append(f"Agent does not declare support for item_type={item_type}.")
    if requested_execution_target == "real":
        blockers.append("Real execution target is unavailable; M128 only builds plans.")
    if str(item.get("status", "")).strip() in {"blocked", "cancelled"}:
        blockers.append(f"Queue item status is {item.get('status')}.")
    return blockers


def _select_primary_agent_id(
    *,
    item: dict[str, Any],
    decision_policy: dict[str, Any],
    requested_agent_id: str | None,
) -> str:
    if requested_agent_id:
        return str(requested_agent_id).strip()
    assigned = str(item.get("assigned_agent", "") if item else "").strip()
    if assigned:
        return assigned
    lane = str(decision_policy.get("recommended_lane", "")).strip()
    if lane == "documentation_agent":
        return "documentation-agent"
    if lane == "validation_agent":
        return "validation-agent"
    if lane == "github_sync_agent":
        return "github-sync-agent"
    if lane in {"codex_coding", "codex_reasoning"}:
        return "codex-dispatch-agent"
    if lane in {"local_llm_reasoning", "local_llm_coding_review"}:
        return "local-llm-advisory-agent"
    if lane == "no_llm_required":
        return "validation-agent"
    item_type = str(item.get("item_type", "") if item else "").strip()
    if item_type == "documentation":
        return "documentation-agent"
    if item_type == "validation":
        return "validation-agent"
    return "completion-recommendation-agent"


def _tail_agents(item: dict[str, Any]) -> list[str]:
    item_type = str(item.get("item_type", "")).strip()
    if item_type == "validation":
        return ["completion-recommendation-agent"]
    return ["validation-agent", "completion-recommendation-agent"]


def _purpose(agent_id: str, item: dict[str, Any]) -> str:
    purposes = {
        "queue-planner-agent": "Confirm queue context, dependencies, and safe ordering for this item.",
        "documentation-agent": "Prepare documentation reconciliation or patch proposal metadata without applying changes.",
        "codex-dispatch-agent": "Prepare an operator-gated Codex handoff record without invoking Codex.",
        "local-llm-advisory-agent": "Prepare local advisory request metadata without invoking a local model.",
        "validation-agent": "Plan deterministic validation evidence without running validation commands.",
        "github-sync-agent": "Plan GitHub sync metadata without calling GitHub or gh.",
        "completion-recommendation-agent": "Plan completion evidence review without changing queue status.",
    }
    return purposes.get(agent_id, f"Plan {item.get('title', item.get('item_id', 'queue item'))} step metadata.")


def _input_artifacts(agent_id: str) -> list[str]:
    common = ["queue_item", "agent_registry", "llm_decision_policy", "runtime_boundary_contract"]
    extras = {
        "documentation-agent": ["source_documents"],
        "codex-dispatch-agent": ["codex_prompt_artifact_or_future_handoff"],
        "local-llm-advisory-agent": ["local_llm_environment_contract"],
        "validation-agent": ["planned_changed_files", "validation_contract"],
        "completion-recommendation-agent": ["dispatch_result_evidence"],
        "github-sync-agent": ["offline_sync_context"],
    }
    return common + extras.get(agent_id, [])


def _step_decision_policy(decision_policy: dict[str, Any]) -> dict[str, Any]:
    return {
        "recommendation_type": decision_policy.get("recommendation_type", "llm_decision_policy_v1"),
        "recommended_lane": decision_policy.get("recommended_lane", ""),
        "recommended_provider": decision_policy.get("recommended_provider", ""),
        "recommended_model_profile": decision_policy.get("recommended_model_profile", ""),
        "machine_gate_required": bool(decision_policy.get("machine_gate_required", True)),
        "human_review_required": bool(decision_policy.get("human_review_required", True)),
        "execution_performed": False,
    }


def _required_artifacts(steps: list[dict[str, Any]]) -> list[str]:
    artifacts: set[str] = {"agent_orchestration_plan", "queue_item_snapshot", "llm_decision_policy"}
    for step in steps:
        artifacts.update(str(value) for value in step.get("output_artifacts", []) if str(value).strip())
    return sorted(artifacts)


def _dependency_checks(item: dict[str, Any]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    for field_name in ("dependencies", "depends_on", "blocked_by"):
        for value in _list(item.get(field_name) if item else []):
            checks.append(
                {
                    "dependency_id": value,
                    "field": field_name,
                    "satisfied": field_name != "blocked_by",
                    "reason": "Dependency is declared for ordering metadata only."
                    if field_name != "blocked_by"
                    else "blocked_by dependency must be cleared before execution.",
                }
            )
    return checks


def _dependency_blockers(item: dict[str, Any]) -> list[str]:
    blockers = []
    for value in _list(item.get("blocked_by") if item else []):
        blockers.append(f"Queue item is blocked_by {value}.")
    return blockers


def _milestone(item: dict[str, Any]) -> str:
    for tag in _list(item.get("tags") if item else []):
        if tag.startswith("milestone:"):
            return tag.split(":", 1)[1]
    item_id = str(item.get("item_id", "") if item else "")
    if "-" in item_id:
        return item_id.split("-", 1)[0]
    return ""


def _autonomy_level(steps: list[dict[str, Any]]) -> str:
    if any(step.get("machine_gate_required") for step in steps):
        return "operator_approved_single_step"
    return "recommendation_only"


def _next_safe_action(blocked: bool, requested_execution_target: str) -> str:
    if requested_execution_target == "real":
        return "Review the blocked reasons and rerun with --execution-target dry-run; real execution requires a later approved runner."
    if blocked:
        return "Resolve blocked reasons, then rebuild the plan; do not execute agents from this command."
    return "Review the dry-run orchestration plan and generate follow-on local artifacts only through explicit non-executing commands."


def _load_queue_item(config: AppConfig, *, item_id: str, queue_path: str | Path | None) -> dict[str, Any]:
    path = resolve_project_queue_path(config.repo_root, queue_path)
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    items = raw.get("work_items", []) if isinstance(raw, dict) else []
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
    rendered = json.dumps(payload, indent=2)
    if output is None:
        return {
            "command": COMMAND_NAME,
            "ok": bool(payload.get("item_found")) and not bool(payload.get("blocked")),
            "local_only": True,
            "format": "json",
            "wrote_output_file": False,
            "stdout": rendered,
            "payload": payload,
        }
    output_path = _resolve_path(config.repo_root, output)
    if output_path.exists() and not force:
        return _error("output_exists", {"output": str(output_path), "message": "Refusing to overwrite output without --force."})
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered + "\n", encoding="utf-8")
    return {
        "command": COMMAND_NAME,
        "ok": bool(payload.get("item_found")) and not bool(payload.get("blocked")),
        "local_only": True,
        "format": "json",
        "output": str(output_path),
        "force": force,
        "wrote_output_file": True,
        "payload": payload,
    }


def _resolve_path(repo_root: Path, value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


def _list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(entry).strip() for entry in value if str(entry).strip()]
    if value in (None, ""):
        return []
    return [str(value).strip()]


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
