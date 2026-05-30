from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.queue_agent_dispatch_plan import build_queue_agent_dispatch_plan

DOCUMENTATION_DRY_RUN_VERSION = "m100.1"
DOCUMENTATION_AGENT_DRY_RUN_LANE = "documentation_agent_dry_run"

_BOUNDARY_CONFIRMATIONS = (
    "M100 Documentation Agent dry-run review is local-only.",
    "Dry-run review consumes the M97 queue-to-agent dispatch plan.",
    "Dry-run review validates documentation-agent readiness metadata only.",
    "execution_allowed=false is required and preserved.",
    "M100 does not execute documentation agents.",
    "M100 does not call local LLMs or Ollama.",
    "M100 does not execute Codex.",
    "M100 does not call GitHub APIs or gh.",
    "M100 does not make network calls.",
    "M100 does not execute external agents.",
    "M100 does not apply patches or mutate documentation.",
    "M100 does not auto-start, auto-complete, or auto-dispatch queue items.",
)

_SOURCE_DOCS = (
    "docs/context/BUILD_STATE.md",
    "docs/context/AGENT_CONTEXT.md",
    "docs/roadmap/ROADMAP.md",
    "docs/operator/LOCAL_OPERATOR_USAGE.md",
    "docs/architecture/RUNNABLE_SKELETON.md",
    "docs/architecture/DOCUMENTATION_AGENT_CONTRACT.md",
    "docs/architecture/AGENT_LLM_ROUTING_STRATEGY.md",
    "docs/architecture/LOCAL_LLM_ENVIRONMENT_CONTRACT.md",
)

_EXPECTED_DOC_UPDATES = (
    "Record completed milestone behavior in source-of-truth docs when implementation evidence exists.",
    "Preserve current queue status and implementation commit references.",
    "Document new command surfaces and operator workflows.",
    "Clarify safety boundaries and blocked behavior for non-target lanes.",
    "Keep future milestone relationships explicit without authorizing execution.",
)

_STALE_DOC_CHECKS = (
    "Current phase and current goal match the latest completed milestone.",
    "Roadmap status for the milestone matches local queue evidence.",
    "Operator usage includes the new command and safe workflow.",
    "Runnable skeleton describes available command behavior and absent execution paths.",
    "Architecture docs distinguish dry-run review from automatic documentation mutation.",
)

_RECONCILIATION_SCOPE = (
    "source_of_truth_docs_only",
    "local_queue_evidence_summary",
    "operator_workflow_text",
    "safety_boundary_text",
    "future_milestone_relationships",
)

_VALIDATION_EXPECTATIONS = (
    "Confirm the M97 dispatch plan selected documentation_agent_dry_run.",
    "Confirm local_only is true and execution_allowed is false.",
    "Confirm dry-run output lists source docs and stale-doc checks.",
    "Confirm no documentation files are mutated by the dry-run result.",
    "Confirm any future documentation changes require operator approval and separate validation.",
)

_OPERATOR_APPROVAL_GATES = (
    "operator_selects_item_id",
    "operator_reviews_m97_dispatch_plan",
    "operator_confirms_documentation_agent_dry_run_lane",
    "operator_reviews_m100_dry_run_output",
    "operator_confirms_no_agent_execution_or_doc_mutation_occurred",
    "operator_approves_future_documentation_apply_path_in_later_milestone",
)


def validate_documentation_agent_dry_run(
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

    if output is not None:
        rendered = json.dumps(payload, indent=2) if str(output_format).lower().strip() == "json" else _render_markdown(payload)
        write_result = _write_output(config=config, output=output, body=rendered, force=force)
        if not write_result["ok"]:
            payload["ready_for_future_documentation_review"] = False
            payload["blocked"] = True
            payload["blocked_reasons"] = sorted(
                {
                    *[str(reason) for reason in payload.get("blocked_reasons", [])],
                    str(write_result.get("reason", "")),
                }
            )
            payload["next_safe_action"] = "Review blocked reasons before preparing any future documentation-agent review artifact."
        else:
            payload["output_path"] = str(write_result.get("output_path", ""))

    return _stdout_result(
        "validate-documentation-agent-dry-run",
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
        "ready_for_future_documentation_review": ready,
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
        "documentation_review_intent": _documentation_review_intent(artifact_intent=artifact_intent),
        "source_docs_to_review": list(_SOURCE_DOCS),
        "expected_doc_updates": list(_EXPECTED_DOC_UPDATES),
        "stale_doc_checks": list(_STALE_DOC_CHECKS),
        "reconciliation_scope": list(_RECONCILIATION_SCOPE),
        "operator_approval_gates": list(_OPERATOR_APPROVAL_GATES),
        "validation_expectations": list(_VALIDATION_EXPECTATIONS),
        "local_only": True,
        "execution_allowed": False,
        "next_safe_action": _next_safe_action(ready=ready, item_id=item_id),
        "output_path": "",
        "dry_run_validator_version": DOCUMENTATION_DRY_RUN_VERSION,
        "dispatch_plan_version": str(plan.get("dispatch_plan_version", "")).strip(),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }


def _dry_run_blockers(plan: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    selected_lane = str(plan.get("selected_lane", "")).strip()
    if selected_lane != DOCUMENTATION_AGENT_DRY_RUN_LANE:
        blockers.append(
            f"Selected lane is {selected_lane or '<missing>'}; M100 only validates documentation_agent_dry_run readiness."
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


def _documentation_review_intent(*, artifact_intent: dict[str, Any]) -> str:
    intent = str(artifact_intent.get("intent", "")).strip()
    return intent or "Prepare a future non-mutating documentation-agent dry-run review plan."


def _next_safe_action(*, ready: bool, item_id: str) -> str:
    if not ready:
        return "Review blocked reasons before preparing any future documentation-agent review artifact."
    return (
        f"Review the documentation dry-run output for {item_id}, then wait for a later "
        "operator-approved milestone before any documentation-agent apply or doc mutation path."
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
        "# Documentation Agent Dry-Run Validator",
        "",
        f"- dry_run: {payload.get('dry_run')}",
        f"- ready_for_future_documentation_review: {payload.get('ready_for_future_documentation_review')}",
        f"- blocked: {payload.get('blocked')}",
        f"- item_id: {payload.get('item_id', '')}",
        f"- title: {payload.get('title', '')}",
        f"- queue_status: {payload.get('queue_status', '')}",
        f"- selected_lane: {payload.get('selected_lane', '')}",
        f"- confidence: {confidence.get('score', 0)} ({confidence.get('level', '')})",
        f"- documentation_review_intent: {payload.get('documentation_review_intent', '')}",
        f"- local_only: {payload.get('local_only')}",
        f"- execution_allowed: {payload.get('execution_allowed')}",
        f"- next_safe_action: {payload.get('next_safe_action', '')}",
    ]
    blockers = payload.get("blocked_reasons", []) if isinstance(payload.get("blocked_reasons"), list) else []
    if blockers:
        lines.extend(["", "## Blocked Reasons"])
        lines.extend(f"- {reason}" for reason in blockers)
    lines.extend(["", "## Source Docs To Review"])
    lines.extend(f"- {doc}" for doc in payload.get("source_docs_to_review", []) if str(doc).strip())
    lines.extend(["", "## Stale Doc Checks"])
    lines.extend(f"- {check}" for check in payload.get("stale_doc_checks", []) if str(check).strip())
    lines.extend(["", "## Operator Gates"])
    lines.extend(f"- {gate}" for gate in payload.get("operator_approval_gates", []) if str(gate).strip())
    return "\n".join(lines).rstrip()
