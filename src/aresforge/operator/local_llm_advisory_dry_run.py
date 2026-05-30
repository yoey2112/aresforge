from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.queue_agent_dispatch_plan import build_queue_agent_dispatch_plan

DRY_RUN_VALIDATOR_VERSION = "m99.1"
LOCAL_LLM_ADVISORY_LANE = "local_llm_advisory"

_BOUNDARY_CONFIRMATIONS = (
    "M99 Local LLM advisory dry-run validation is local-only.",
    "Dry-run validation consumes the M97 queue-to-agent dispatch plan.",
    "Dry-run validation only prepares advisory-readiness metadata.",
    "execution_allowed=false is required and preserved.",
    "M99 does not call Ollama APIs.",
    "M99 does not execute Ollama or local models.",
    "M99 does not execute Codex.",
    "M99 does not call GitHub APIs or gh.",
    "M99 does not make network calls.",
    "M99 does not execute external agents.",
    "M99 does not apply patches.",
    "M99 does not auto-start, auto-complete, or auto-dispatch queue items.",
)

_CONTEXT_SOURCES = (
    "docs/context/BUILD_STATE.md",
    "docs/context/AGENT_CONTEXT.md",
    "docs/roadmap/ROADMAP.md",
    "docs/operator/LOCAL_OPERATOR_USAGE.md",
    "docs/architecture/RUNNABLE_SKELETON.md",
    "docs/architecture/AGENT_LLM_ROUTING_STRATEGY.md",
    "docs/architecture/LOCAL_LLM_ENVIRONMENT_CONTRACT.md",
    "docs/architecture/DOCUMENTATION_AGENT_CONTRACT.md",
    "M97 queue-to-agent dispatch plan payload",
    "Local queue item title, description, notes, tags, and routing metadata",
)

_PROMPT_SECTIONS = (
    "dry_run_notice",
    "queue_item_identity",
    "dispatch_plan_summary",
    "source_context_to_review",
    "advisory_questions",
    "validation_expectations",
    "safety_boundaries",
    "operator_approval_gates",
    "future_run_is_not_authorized_by_this_dry_run",
)

_VALIDATION_EXPECTATIONS = (
    "Confirm the M97 dispatch plan selected local_llm_advisory.",
    "Confirm local_only is true and execution_allowed is false.",
    "Confirm any future advisory artifact is reviewed by the operator before model invocation.",
    "Confirm local LLM output, if produced by a later milestone, remains advisory and non-mutating.",
    "Confirm no queue completion happens from advisory output alone.",
)

_OPERATOR_APPROVAL_GATES = (
    "operator_selects_item_id",
    "operator_reviews_m97_dispatch_plan",
    "operator_confirms_local_llm_advisory_lane",
    "operator_reviews_m99_dry_run_output",
    "operator_confirms_no_model_execution_occurred",
    "operator_approves_future_advisory_artifact_or_run_in_later_milestone",
)


def validate_local_llm_advisory_dry_run(
    config: AppConfig,
    *,
    item_id: str,
    queue_path: str | Path | None = None,
    registry_path: str | Path | None = None,
    output: str | Path | None = None,
    force: bool = False,
    output_format: str = "markdown",
    dispatch_plan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_item_id = str(item_id or "").strip()
    plan = (
        dispatch_plan
        if dispatch_plan is not None
        else build_queue_agent_dispatch_plan(
            config,
            item_id=normalized_item_id,
            queue_path=queue_path,
            registry_path=registry_path,
        )
    )

    blocked_reasons = _dry_run_blockers(plan)
    blocked = bool(blocked_reasons)
    payload = _build_payload(
        item_id=normalized_item_id,
        plan=plan,
        blocked=blocked,
        blocked_reasons=blocked_reasons,
    )

    output_path = ""
    if output is not None:
        rendered = json.dumps(payload, indent=2) if str(output_format).lower().strip() == "json" else _render_markdown(payload)
        write_result = _write_output(config=config, output=output, body=rendered, force=force)
        output_path = str(write_result.get("output_path", ""))
        if not write_result["ok"]:
            payload["ready_for_future_advisory_run"] = False
            payload["blocked"] = True
            payload["blocked_reasons"] = sorted(
                {
                    *[str(reason) for reason in payload.get("blocked_reasons", [])],
                    str(write_result.get("reason", "")),
                }
            )
            payload["next_safe_action"] = "Review blocked reasons before preparing any future local LLM advisory artifact."
        else:
            payload["output_path"] = output_path

    return _stdout_result(
        "validate-local-llm-advisory-dry-run",
        payload,
        output_format,
        _render_markdown(payload),
    )


def _build_payload(*, item_id: str, plan: dict[str, Any], blocked: bool, blocked_reasons: list[str]) -> dict[str, Any]:
    confidence = plan.get("routing_confidence", {}) if isinstance(plan.get("routing_confidence"), dict) else {}
    artifact_intent = plan.get("planned_artifact_intent", {}) if isinstance(plan.get("planned_artifact_intent"), dict) else {}
    ready = not blocked
    return {
        "ok": ready,
        "dry_run": True,
        "ready_for_future_advisory_run": ready,
        "blocked": blocked,
        "blocked_reasons": sorted({reason for reason in blocked_reasons if reason}),
        "item_id": item_id or str(plan.get("item_id", "")).strip(),
        "title": str(plan.get("title", "")).strip(),
        "project_id": str(plan.get("project_id", "")).strip(),
        "milestone": str(plan.get("milestone", "")).strip(),
        "queue_status": str(plan.get("status", "")).strip(),
        "selected_lane": str(plan.get("selected_lane", "")).strip(),
        "confidence": {
            "score": confidence.get("score", 0) if isinstance(confidence.get("score", 0), int) else 0,
            "level": str(confidence.get("level", "")).strip(),
            "reason": str(confidence.get("reason", "")).strip(),
        },
        "selection_reason": str(plan.get("lane_selection_reason", "")).strip(),
        "local_only": True,
        "execution_allowed": False,
        "advisory_intent": _advisory_intent(plan=plan, artifact_intent=artifact_intent),
        "recommended_model_role": "reasoning/advisory",
        "context_sources_to_review": list(_CONTEXT_SOURCES),
        "prompt_sections": list(_PROMPT_SECTIONS),
        "prompt_outline": "Dry-run only outline for a future local LLM advisory artifact; no final model prompt is generated by M99.",
        "validation_expectations": list(_VALIDATION_EXPECTATIONS),
        "operator_approval_gates": list(_OPERATOR_APPROVAL_GATES),
        "next_safe_action": _next_safe_action(ready=ready, item_id=item_id),
        "output_path": "",
        "dry_run_validator_version": DRY_RUN_VALIDATOR_VERSION,
        "dispatch_plan_version": str(plan.get("dispatch_plan_version", "")).strip(),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }


def _dry_run_blockers(plan: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    selected_lane = str(plan.get("selected_lane", "")).strip()
    if selected_lane != LOCAL_LLM_ADVISORY_LANE:
        blockers.append(
            f"Selected lane is {selected_lane or '<missing>'}; M99 only validates local_llm_advisory dry-run readiness."
        )
    plan_blockers = plan.get("blocked_reasons", [])
    if isinstance(plan_blockers, list):
        blockers.extend(str(reason).strip() for reason in plan_blockers if str(reason).strip())
    if bool(plan.get("blocked", False)):
        blockers.append("Dispatch plan is blocked.")
    if plan.get("local_only") is not True:
        blockers.append("Dispatch plan local_only must be true.")
    if plan.get("execution_allowed") is not False:
        blockers.append("Dispatch plan execution_allowed must be false.")
    return sorted({blocker for blocker in blockers if blocker})


def _advisory_intent(*, plan: dict[str, Any], artifact_intent: dict[str, Any]) -> str:
    intent = str(artifact_intent.get("intent", "")).strip()
    if intent:
        return intent
    title = str(plan.get("title", "")).strip()
    return f"Prepare future local reasoning advisory review readiness for {title or 'the selected queue item'}."


def _next_safe_action(*, ready: bool, item_id: str) -> str:
    if not ready:
        return "Review blocked reasons before preparing any future local LLM advisory artifact."
    return (
        f"Review the dry-run output for {item_id}, then wait for a later operator-approved milestone "
        "before creating or running any local LLM advisory artifact."
    )


def _write_output(*, config: AppConfig, output: str | Path, body: str, force: bool) -> dict[str, Any]:
    output_path = Path(output)
    if not output_path.is_absolute():
        output_path = (config.repo_root / output_path).resolve()
    if output_path.exists() and not force:
        return {
            "ok": False,
            "output_path": str(output_path),
            "reason": "Output file already exists. Re-run with --force to overwrite.",
        }
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(body.rstrip() + "\n", encoding="utf-8")
    except OSError as exc:
        return {
            "ok": False,
            "output_path": str(output_path),
            "reason": f"Failed to write output file: {exc}",
        }
    return {"ok": True, "output_path": str(output_path)}


def _stdout_result(command: str, payload: dict[str, Any], output_format: str, markdown: str) -> dict[str, Any]:
    fmt = str(output_format or "markdown").lower().strip()
    if fmt not in {"json", "markdown"}:
        return {
            "command": command,
            "ok": False,
            "local_only": True,
            "error": "invalid_format",
            "details": {"format": output_format, "supported_formats": ["json", "markdown"]},
        }
    return {
        "command": command,
        "ok": bool(payload.get("ok", False)),
        "local_only": True,
        "format": fmt,
        "wrote_output_file": bool(payload.get("output_path")),
        "stdout": json.dumps(payload, indent=2) if fmt == "json" else markdown,
        "payload": payload,
    }


def _render_markdown(payload: dict[str, Any]) -> str:
    confidence = payload.get("confidence", {}) if isinstance(payload.get("confidence"), dict) else {}
    lines = [
        "# Local LLM Advisory Dry-Run Validator",
        "",
        f"- dry_run: {payload.get('dry_run')}",
        f"- ready_for_future_advisory_run: {payload.get('ready_for_future_advisory_run')}",
        f"- blocked: {payload.get('blocked')}",
        f"- item_id: {payload.get('item_id', '')}",
        f"- title: {payload.get('title', '')}",
        f"- queue_status: {payload.get('queue_status', '')}",
        f"- selected_lane: {payload.get('selected_lane', '')}",
        f"- confidence: {confidence.get('score', 0)} ({confidence.get('level', '')})",
        f"- advisory_intent: {payload.get('advisory_intent', '')}",
        f"- local_only: {payload.get('local_only')}",
        f"- execution_allowed: {payload.get('execution_allowed')}",
        f"- next_safe_action: {payload.get('next_safe_action', '')}",
    ]
    blockers = payload.get("blocked_reasons", []) if isinstance(payload.get("blocked_reasons"), list) else []
    if blockers:
        lines.extend(["", "## Blocked Reasons"])
        lines.extend(f"- {reason}" for reason in blockers)
    lines.extend(["", "## Operator Gates"])
    lines.extend(f"- {gate}" for gate in payload.get("operator_approval_gates", []) if str(gate).strip())
    lines.extend(["", "## Validation Expectations"])
    lines.extend(f"- {entry}" for entry in payload.get("validation_expectations", []) if str(entry).strip())
    return "\n".join(lines).rstrip()
