from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.llm_decision_matrix import build_llm_decision_matrix
from aresforge.operator.local_project_queue import (
    inspect_local_queue_item_readiness,
    resolve_project_queue_path,
)

DISPATCH_PLAN_VERSION = "m97.1"
SUPPORTED_DISPATCH_LANES: tuple[str, ...] = (
    "codex_prompt_artifact",
    "local_llm_advisory",
    "local_llm_coding_draft",
    "documentation_agent_dry_run",
    "human_only_manual",
)

_STARTABLE_STATUSES = {"proposed", "ready"}
_DOCUMENTATION_MARKERS = {
    "documentation",
    "docs",
    "reconciliation",
    "source-of-truth",
    "source of truth",
    "handoff",
    "documentation agent",
    "operator usage",
}
_CODING_MARKERS = {
    "implement",
    "implementation",
    "build",
    "add",
    "fix",
    "feature",
    "bug",
    "contract",
    "cli",
    "test",
    "tests",
    "operator-layer",
}

_BOUNDARY_CONFIRMATIONS = (
    "M97 queue-to-agent dispatch planning is local-only.",
    "Dispatch plans are advisory contract data only.",
    "Dispatch planning does not generate the full Codex prompt artifact.",
    "Dispatch planning does not execute Codex.",
    "Dispatch planning does not invoke Ollama or local LLMs.",
    "Dispatch planning does not execute documentation agents.",
    "Dispatch planning does not call GitHub APIs or gh.",
    "Dispatch planning does not make network calls.",
    "Dispatch planning does not mutate repository files or queue state.",
    "Future dispatch requires explicit operator approval outside M97.",
)

_APPROVAL_GATES = (
    "operator_selects_item_id",
    "operator_reviews_dispatch_plan",
    "operator_confirms_lane",
    "operator_reviews_planned_artifact_intent",
    "operator_confirms_local_only_boundaries",
    "operator_runs_required_validation",
    "operator_records_review_evidence_before_completion",
)


def inspect_queue_agent_dispatch_plan(
    config: AppConfig,
    *,
    item_id: str,
    queue_path: str | Path | None = None,
    registry_path: str | Path | None = None,
    output_format: str = "markdown",
) -> dict[str, Any]:
    payload = build_queue_agent_dispatch_plan(
        config,
        item_id=item_id,
        queue_path=queue_path,
        registry_path=registry_path,
    )
    return _stdout_result(
        "inspect-queue-dispatch-plan",
        payload,
        output_format,
        _render_markdown(payload),
    )


def build_queue_agent_dispatch_plan(
    config: AppConfig,
    *,
    item_id: str,
    queue_path: str | Path | None = None,
    registry_path: str | Path | None = None,
) -> dict[str, Any]:
    normalized_item_id = str(item_id or "").strip()
    resolved_queue_path = resolve_project_queue_path(config.repo_root, queue_path)
    loaded = _load_queue_item(resolved_queue_path, normalized_item_id)
    item = loaded.get("item", {}) if isinstance(loaded.get("item"), dict) else {}
    warnings = [str(warning) for warning in loaded.get("warnings", []) if str(warning).strip()]
    blocked_reasons = [str(blocker) for blocker in loaded.get("blockers", []) if str(blocker).strip()]

    readiness = inspect_local_queue_item_readiness(
        config,
        item_id=normalized_item_id,
        queue_path=resolved_queue_path,
        registry_path=registry_path,
    )
    if not readiness.get("ok", False):
        blocked_reasons.extend(str(blocker) for blocker in readiness.get("blockers", []) if str(blocker).strip())
    warnings.extend(str(warning) for warning in readiness.get("warnings", []) if str(warning).strip())

    decision_matrix = build_llm_decision_matrix(
        config,
        item_id=normalized_item_id,
        queue_path=resolved_queue_path,
        registry_path=registry_path,
    )
    if not decision_matrix.get("ok", False):
        blocked_reasons.extend(str(blocker) for blocker in decision_matrix.get("blockers", []) if str(blocker).strip())
    warnings.extend(str(warning) for warning in decision_matrix.get("warnings", []) if str(warning).strip())

    missing_fields = _missing_required_fields(item)
    blocked_reasons.extend(f"Missing required queue item field: {field}" for field in missing_fields)
    status = str(item.get("status", "")).strip()
    if status and status not in _STARTABLE_STATUSES:
        blocked_reasons.append(f"Queue item status is {status}; dispatch planning is only startable for proposed or ready items.")
    if item.get("blocked_by"):
        blocked_reasons.append("Queue item has blocked_by references and requires manual blocker review.")

    routing = _select_dispatch_lane(item=item, decision_matrix=decision_matrix, blocked_reasons=blocked_reasons)
    lane = routing["lane"]
    confidence = routing["confidence"]
    confidence_score = int(confidence.get("score", 0))
    if confidence_score < 60 and lane != "human_only_manual":
        warnings.append("Routing confidence is below 60; using human_only_manual safe fallback.")
        lane = "human_only_manual"
        confidence = {
            "score": confidence_score,
            "level": str(confidence.get("level", "low")),
            "reason": "Low routing confidence requires manual-only dispatch planning.",
        }

    blocked_reasons = sorted({str(reason).strip() for reason in blocked_reasons if str(reason).strip()})
    warnings = sorted({str(warning).strip() for warning in warnings if str(warning).strip()})
    blocked = bool(blocked_reasons)

    return {
        "ok": bool(loaded.get("ok", False)) and not blocked,
        "local_only": True,
        "advisory_only": True,
        "dispatch_plan_version": DISPATCH_PLAN_VERSION,
        "generated_at": _generated_at(item, loaded.get("queue", {})),
        "item_id": normalized_item_id,
        "title": str(item.get("title", "")).strip(),
        "status": status,
        "project_id": str(item.get("project_id", "")).strip(),
        "repo_id": str(item.get("repo_id", "")).strip(),
        "milestone": _milestone(item),
        "selected_lane": lane,
        "supported_lanes": list(SUPPORTED_DISPATCH_LANES),
        "routing_confidence": confidence,
        "lane_selection_reason": routing["reason"],
        "planned_artifact_intent": _planned_artifact_intent(lane, item),
        "approval_gates": _approval_gates(lane),
        "blocked": blocked,
        "blocked_reasons": blocked_reasons,
        "warnings": warnings,
        "execution_allowed": False,
        "prompt_dispatch_allowed": False,
        "codex_execution_allowed": False,
        "local_llm_invocation_allowed": False,
        "documentation_agent_execution_allowed": False,
        "github_api_allowed": False,
        "gh_allowed": False,
        "network_allowed": False,
        "repo_mutation_allowed": False,
        "queue_mutation_allowed": False,
        "automatic_next_item_execution_allowed": False,
        "next_safe_action": _next_safe_action(lane=lane, blocked=blocked, item_id=normalized_item_id),
        "readiness_summary": {
            "readiness_status": str(readiness.get("readiness_status", "unknown")).strip(),
            "can_start": bool(readiness.get("can_start", False)),
        },
        "decision_matrix_summary": _decision_matrix_summary(decision_matrix),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }


def _load_queue_item(queue_path: Path, item_id: str) -> dict[str, Any]:
    if not queue_path.exists():
        return {
            "ok": False,
            "queue": {},
            "item": {},
            "warnings": [f"Local queue file not found: {queue_path}"],
            "blockers": [f"Queue item not found: {item_id}"],
        }
    try:
        raw = json.loads(queue_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "ok": False,
            "queue": {},
            "item": {},
            "warnings": [],
            "blockers": [f"Local queue file could not be read: {exc}"],
        }
    items = raw.get("work_items", []) if isinstance(raw, dict) else []
    item = next(
        (
            candidate
            for candidate in items
            if isinstance(candidate, dict) and str(candidate.get("item_id", "")).strip() == item_id
        ),
        None,
    )
    if item is None:
        return {"ok": False, "queue": raw if isinstance(raw, dict) else {}, "item": {}, "warnings": [], "blockers": [f"Queue item not found: {item_id}"]}
    return {"ok": True, "queue": raw if isinstance(raw, dict) else {}, "item": item, "warnings": [], "blockers": []}


def _select_dispatch_lane(*, item: dict[str, Any], decision_matrix: dict[str, Any], blocked_reasons: list[str]) -> dict[str, Any]:
    confidence = _confidence(decision_matrix)
    if blocked_reasons or not item:
        return {
            "lane": "human_only_manual",
            "confidence": confidence,
            "reason": "Dispatch planning is unsafe or incomplete, so the manual-only fallback lane was selected.",
        }

    text = _item_text(item)
    item_type = str(item.get("item_type", "")).strip()
    decision = decision_matrix.get("routing_decision", {}) if isinstance(decision_matrix.get("routing_decision"), dict) else {}
    engine = str(decision.get("recommended_engine", "")).strip()

    coding_type = item_type in {"feature", "bug", "task", "dashboard"}
    if item_type in {"documentation", "handoff"} or (not coding_type and any(marker in text for marker in _DOCUMENTATION_MARKERS)):
        return {
            "lane": "documentation_agent_dry_run",
            "confidence": confidence,
            "reason": "Queue item is documentation or reconciliation oriented; dry-run documentation review is the safest lane.",
        }
    if engine == "codex_cli" or coding_type or any(marker in text for marker in _CODING_MARKERS):
        return {
            "lane": "codex_prompt_artifact",
            "confidence": confidence,
            "reason": "Queue item appears to require implementation or coding-oriented artifact preparation.",
        }
    if engine == "local_coding_llm":
        return {
            "lane": "local_llm_coding_draft",
            "confidence": confidence,
            "reason": "Decision matrix recommends the local coding draft lane.",
        }
    if engine == "local_reasoning_llm":
        return {
            "lane": "local_llm_advisory",
            "confidence": confidence,
            "reason": "Decision matrix recommends local reasoning advisory review.",
        }
    return {
        "lane": "human_only_manual",
        "confidence": confidence,
        "reason": "No clear dispatch lane matched; manual-only fallback selected.",
    }


def _confidence(decision_matrix: dict[str, Any]) -> dict[str, Any]:
    raw = decision_matrix.get("routing_confidence", {}) if isinstance(decision_matrix.get("routing_confidence"), dict) else {}
    score = raw.get("score", 0)
    if not isinstance(score, int) or isinstance(score, bool):
        score = 0
    return {
        "score": max(0, min(100, score)),
        "level": str(raw.get("confidence_level", "low")).strip() or "low",
        "reason": "; ".join(str(value) for value in raw.get("rationale", []) if str(value).strip())
        if isinstance(raw.get("rationale"), list)
        else "Routing confidence unavailable.",
    }


def _planned_artifact_intent(lane: str, item: dict[str, Any]) -> dict[str, Any]:
    title = str(item.get("title", "")).strip()
    if lane == "codex_prompt_artifact":
        return {
            "artifact_type": "codex_prompt_dispatch_plan",
            "generator_milestone": "M98",
            "intent": f"Prepare a future Codex prompt artifact outline for {title or 'the queue item'} without generating the full prompt in M97.",
            "full_prompt_generated": False,
        }
    if lane == "documentation_agent_dry_run":
        return {
            "artifact_type": "documentation_agent_dry_run_plan",
            "generator_milestone": "M100",
            "intent": "Prepare a future non-mutating documentation review plan.",
            "full_prompt_generated": False,
        }
    if lane == "local_llm_coding_draft":
        return {
            "artifact_type": "local_llm_coding_draft_plan",
            "generator_milestone": "M99",
            "intent": "Prepare a future local coding draft dry-run validation plan.",
            "full_prompt_generated": False,
        }
    if lane == "local_llm_advisory":
        return {
            "artifact_type": "local_llm_advisory_plan",
            "generator_milestone": "M99",
            "intent": "Prepare a future local advisory dry-run validation plan.",
            "full_prompt_generated": False,
        }
    return {
        "artifact_type": "manual_review_plan",
        "generator_milestone": "",
        "intent": "Keep the item in manual operator review until requirements and safety posture are clear.",
        "full_prompt_generated": False,
    }


def _approval_gates(lane: str) -> list[str]:
    gates = list(_APPROVAL_GATES)
    if lane == "codex_prompt_artifact":
        gates.append("operator_must_approve_m98_codex_prompt_artifact_before_any_codex_dispatch")
    elif lane in {"local_llm_advisory", "local_llm_coding_draft"}:
        gates.append("operator_must_approve_any_future_local_llm_run")
    elif lane == "documentation_agent_dry_run":
        gates.append("operator_must_approve_documentation_dry_run_before_any_apply_mode_exists")
    else:
        gates.append("operator_must_clarify_requirements_before_artifact_generation")
    return gates


def _missing_required_fields(item: dict[str, Any]) -> list[str]:
    if not item:
        return ["item_id", "title", "status"]
    missing = []
    for field in ("item_id", "title", "status"):
        if not str(item.get(field, "")).strip():
            missing.append(field)
    return missing


def _milestone(item: dict[str, Any]) -> str:
    tags = item.get("tags", []) if isinstance(item.get("tags"), list) else []
    for tag in tags:
        normalized = str(tag).strip()
        if normalized.startswith("milestone:"):
            return normalized.split(":", 1)[1].strip()
    item_id = str(item.get("item_id", "")).strip()
    return item_id.split("-", 1)[0].upper() if item_id.lower().startswith("m") and "-" in item_id else ""


def _generated_at(item: dict[str, Any], queue: Any) -> str:
    if isinstance(item, dict) and str(item.get("updated_at", "")).strip():
        return str(item.get("updated_at", "")).strip()
    if isinstance(queue, dict) and str(queue.get("updated_at", "")).strip():
        return str(queue.get("updated_at", "")).strip()
    return ""


def _item_text(item: dict[str, Any]) -> str:
    tags = item.get("tags", []) if isinstance(item.get("tags"), list) else []
    return " ".join(
        [
            str(item.get("item_id", "")),
            str(item.get("title", "")),
            str(item.get("description", "")),
            str(item.get("item_type", "")),
            str(item.get("notes", "")),
            " ".join(str(tag) for tag in tags),
        ]
    ).lower()


def _decision_matrix_summary(decision_matrix: dict[str, Any]) -> dict[str, Any]:
    decision = decision_matrix.get("routing_decision", {}) if isinstance(decision_matrix.get("routing_decision"), dict) else {}
    confidence = decision_matrix.get("routing_confidence", {}) if isinstance(decision_matrix.get("routing_confidence"), dict) else {}
    return {
        "recommended_engine": str(decision.get("recommended_engine", "")).strip(),
        "recommended_lane": str(decision.get("recommended_lane", "")).strip(),
        "recommended_model": str(decision.get("recommended_model", "")).strip(),
        "confidence_score": confidence.get("score", 0) if isinstance(confidence.get("score", 0), int) else 0,
        "confidence_level": str(confidence.get("confidence_level", "")).strip(),
    }


def _next_safe_action(*, lane: str, blocked: bool, item_id: str) -> str:
    if blocked:
        return "Resolve blocked reasons or clarify the queue item before preparing any dispatch artifact."
    if lane == "codex_prompt_artifact":
        return f"Review this plan, then use the future M98 artifact generator for item {item_id}; do not dispatch Codex from M97."
    if lane == "documentation_agent_dry_run":
        return f"Review this plan, then use a future documentation-agent dry-run workflow for item {item_id}; do not apply documentation changes from M97."
    if lane in {"local_llm_advisory", "local_llm_coding_draft"}:
        return f"Review this plan and wait for a future dry-run validator before any local LLM invocation for item {item_id}."
    return "Keep the item human-only until requirements, lane, and approval gates are clear."


def _stdout_result(command: str, payload: dict[str, Any], output_format: str, markdown: str) -> dict[str, Any]:
    fmt = str(output_format or "markdown").lower().strip()
    if fmt not in {"json", "markdown"}:
        return {
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
        "wrote_output_file": False,
        "stdout": json.dumps(payload, indent=2) if fmt == "json" else markdown,
        "payload": payload,
    }


def _render_markdown(payload: dict[str, Any]) -> str:
    confidence = payload.get("routing_confidence", {}) if isinstance(payload.get("routing_confidence"), dict) else {}
    lines = [
        "# Queue-to-Agent Dispatch Plan",
        "",
        f"- ok: {payload.get('ok')}",
        f"- item_id: {payload.get('item_id', '')}",
        f"- title: {payload.get('title', '')}",
        f"- status: {payload.get('status', '')}",
        f"- selected_lane: {payload.get('selected_lane', '')}",
        f"- routing_confidence: {confidence.get('score', 0)} ({confidence.get('level', '')})",
        f"- execution_allowed: {payload.get('execution_allowed')}",
        f"- next_safe_action: {payload.get('next_safe_action', '')}",
        "",
        "## Planned Artifact Intent",
        f"- artifact_type: {(payload.get('planned_artifact_intent') or {}).get('artifact_type', '') if isinstance(payload.get('planned_artifact_intent'), dict) else ''}",
        f"- full_prompt_generated: {(payload.get('planned_artifact_intent') or {}).get('full_prompt_generated', False) if isinstance(payload.get('planned_artifact_intent'), dict) else False}",
        "",
        "## Approval Gates",
    ]
    lines.extend(f"- {gate}" for gate in payload.get("approval_gates", []) if str(gate).strip())
    blockers = payload.get("blocked_reasons", []) if isinstance(payload.get("blocked_reasons"), list) else []
    if blockers:
        lines.extend(["", "## Blocked Reasons"])
        lines.extend(f"- {entry}" for entry in blockers)
    lines.extend(["", "## Boundaries"])
    lines.extend(f"- {entry}" for entry in payload.get("boundary_confirmations", []) if str(entry).strip())
    return "\n".join(lines)
