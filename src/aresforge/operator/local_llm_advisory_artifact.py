from __future__ import annotations

from datetime import UTC, datetime
import json
import re
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.local_project_queue import resolve_project_queue_path
from aresforge.operator.queue_agent_dispatch_plan import build_queue_agent_dispatch_plan

ADVISORY_ARTIFACT_GENERATOR_VERSION = "m110.1"
LOCAL_LLM_ADVISORY_LANE = "local_llm_advisory"
ARTIFACT_TYPE = "local_llm_advisory_request"

_SOURCE_DOCUMENTS = (
    "docs/context/BUILD_STATE.md",
    "docs/context/AGENT_CONTEXT.md",
    "docs/roadmap/ROADMAP.md",
    "docs/operator/LOCAL_OPERATOR_USAGE.md",
    "docs/architecture/LOCAL_LLM_ENVIRONMENT_CONTRACT.md",
    "docs/architecture/AGENT_LLM_ROUTING_STRATEGY.md",
    "docs/architecture/RUNNABLE_SKELETON.md",
    "M97 queue-to-agent dispatch plan payload",
    ".aresforge/queue/work_items.json queue item context",
)

_OPERATOR_REVIEW_CHECKLIST = (
    "Confirm the queue item is the intended advisory target.",
    "Confirm the M97 selected lane is local_llm_advisory.",
    "Confirm local_only=true and execution_allowed=false are present.",
    "Confirm the generated prompt asks only for advisory review.",
    "Confirm no model invocation occurred while generating this artifact.",
    "Confirm no patch application, queue mutation, GitHub, Codex, or network action occurred.",
    "Create or review a separate approval gate before any later local LLM invocation milestone.",
)

_BOUNDARY_CONFIRMATIONS = (
    "M110 local LLM advisory request artifact generation is local-only.",
    "M110 prepares a request package only; it does not invoke Ollama or local LLMs.",
    "M110 does not execute Codex or Codex CLI.",
    "M110 does not call GitHub APIs, gh, network services, external agents, or documentation agents.",
    "M110 does not apply patches or mutate source files from model output.",
    "M110 does not auto-start, auto-complete, auto-dispatch, or mutate queue items.",
    "Any later local LLM invocation requires explicit operator approval outside M110.",
)


def generate_local_llm_advisory_artifact(
    config: AppConfig,
    *,
    item_id: str,
    queue_path: str | Path | None = None,
    registry_path: str | Path | None = None,
    output: str | Path | None = None,
    force: bool = False,
    output_format: str = "markdown",
    model_profile: str | None = None,
    reasoning_scope: str | None = None,
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
    item = _load_queue_item(config, item_id=normalized_item_id, queue_path=queue_path)
    blocked_reasons = _generation_blockers(plan)
    generated = not blocked_reasons
    payload = _build_payload(
        item_id=normalized_item_id,
        item=item,
        plan=plan,
        generated=generated,
        blocked_reasons=blocked_reasons,
        model_profile=model_profile,
        reasoning_scope=reasoning_scope,
    )

    if generated:
        output_path = _default_output_path(config, normalized_item_id) if output is None else _resolve_output_path(config, output)
        write_result = _write_artifact(output_path=output_path, payload=payload, force=force)
        if not write_result["ok"]:
            payload["ok"] = False
            payload["generated"] = False
            payload["blocked"] = True
            payload["blocked_reasons"] = sorted({str(write_result.get("reason", ""))})
            payload["output_path"] = str(write_result.get("output_path", ""))
            payload["next_safe_action"] = "Review blocked reasons before preparing any local LLM advisory request artifact."
        else:
            payload["output_path"] = str(write_result["output_path"])
    return _stdout_result(
        "generate-local-llm-advisory-artifact",
        payload,
        output_format,
        _render_markdown(payload),
    )


def _build_payload(
    *,
    item_id: str,
    item: dict[str, Any],
    plan: dict[str, Any],
    generated: bool,
    blocked_reasons: list[str],
    model_profile: str | None,
    reasoning_scope: str | None,
) -> dict[str, Any]:
    confidence = plan.get("routing_confidence", {}) if isinstance(plan.get("routing_confidence"), dict) else {}
    requested_model_profile = str(model_profile or "").strip() or _recommended_model(plan) or "local-reasoning-advisory"
    scope = str(reasoning_scope or "").strip() or "implementation_advisory_review"
    queue_context = _queue_context(item=item, plan=plan, confidence=confidence)
    advisory_prompt = _advisory_prompt(
        item_id=item_id,
        title=str(plan.get("title", "")).strip(),
        requested_model_profile=requested_model_profile,
        reasoning_scope=scope,
        queue_context=queue_context,
    )
    return {
        "ok": generated,
        "artifact_type": ARTIFACT_TYPE,
        "generated": generated,
        "generated_at": _now_iso(),
        "blocked": not generated,
        "blocked_reasons": sorted({reason for reason in blocked_reasons if reason}),
        "item_id": item_id or str(plan.get("item_id", "")).strip(),
        "title": str(plan.get("title", "")).strip(),
        "project_id": str(plan.get("project_id", "")).strip(),
        "milestone": str(plan.get("milestone", "")).strip(),
        "queue_status": str(plan.get("status", "")).strip(),
        "requested_model_profile": requested_model_profile,
        "reasoning_scope": scope,
        "source_documents": list(_SOURCE_DOCUMENTS),
        "queue_context": queue_context,
        "advisory_prompt": advisory_prompt if generated else "",
        "expected_response_shape": _expected_response_shape(),
        "operator_review_checklist": list(_OPERATOR_REVIEW_CHECKLIST),
        "local_only": True,
        "execution_allowed": False,
        "local_llm_execution_performed": False,
        "codex_execution_performed": False,
        "network_execution_performed": False,
        "patch_application_allowed": False,
        "output_path": "",
        "selected_lane": str(plan.get("selected_lane", "")).strip(),
        "dispatch_plan_version": str(plan.get("dispatch_plan_version", "")).strip(),
        "advisory_artifact_generator_version": ADVISORY_ARTIFACT_GENERATOR_VERSION,
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
        "next_safe_action": _next_safe_action(generated=generated, item_id=item_id),
    }


def _generation_blockers(plan: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    selected_lane = str(plan.get("selected_lane", "")).strip()
    if selected_lane != LOCAL_LLM_ADVISORY_LANE:
        blockers.append(
            f"Selected lane is {selected_lane or '<missing>'}; M110 only generates artifacts for local_llm_advisory."
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


def _load_queue_item(config: AppConfig, *, item_id: str, queue_path: str | Path | None) -> dict[str, Any]:
    resolved_queue_path = resolve_project_queue_path(config.repo_root, queue_path)
    if not resolved_queue_path.exists():
        return {}
    try:
        raw = json.loads(resolved_queue_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    items = raw.get("work_items", []) if isinstance(raw, dict) else []
    item = next(
        (
            candidate
            for candidate in items
            if isinstance(candidate, dict) and str(candidate.get("item_id", "")).strip() == item_id
        ),
        {},
    )
    return item if isinstance(item, dict) else {}


def _queue_context(*, item: dict[str, Any], plan: dict[str, Any], confidence: dict[str, Any]) -> dict[str, Any]:
    tags = item.get("tags", []) if isinstance(item.get("tags"), list) else []
    dependencies = item.get("dependencies", []) if isinstance(item.get("dependencies"), list) else []
    blocked_by = item.get("blocked_by", []) if isinstance(item.get("blocked_by"), list) else []
    return {
        "item_id": str(plan.get("item_id", "")).strip(),
        "title": str(plan.get("title", "")).strip(),
        "description": str(item.get("description", "")).strip(),
        "notes": str(item.get("notes", "")).strip(),
        "tags": [str(tag) for tag in tags],
        "priority": str(item.get("priority", "")).strip(),
        "item_type": str(item.get("item_type", "")).strip(),
        "dependencies": [str(dep) for dep in dependencies],
        "blocked_by": [str(blocker) for blocker in blocked_by],
        "selected_lane": str(plan.get("selected_lane", "")).strip(),
        "lane_selection_reason": str(plan.get("lane_selection_reason", "")).strip(),
        "routing_confidence": {
            "score": confidence.get("score", 0) if isinstance(confidence.get("score", 0), int) else 0,
            "level": str(confidence.get("level", "")).strip(),
            "reason": str(confidence.get("reason", "")).strip(),
        },
        "planned_artifact_intent": plan.get("planned_artifact_intent", {})
        if isinstance(plan.get("planned_artifact_intent"), dict)
        else {},
        "readiness_summary": plan.get("readiness_summary", {}) if isinstance(plan.get("readiness_summary"), dict) else {},
        "decision_matrix_summary": plan.get("decision_matrix_summary", {})
        if isinstance(plan.get("decision_matrix_summary"), dict)
        else {},
    }


def _advisory_prompt(
    *,
    item_id: str,
    title: str,
    requested_model_profile: str,
    reasoning_scope: str,
    queue_context: dict[str, Any],
) -> str:
    lines = [
        "AresForge Local LLM Advisory Request",
        "",
        "This is an operator-reviewed advisory request package only.",
        "Do not mutate files, apply patches, execute commands, call tools, call network services, or mark queue work complete.",
        "",
        f"Item: {item_id}",
        f"Title: {title}",
        f"Requested model profile: {requested_model_profile}",
        f"Reasoning scope: {reasoning_scope}",
        f"Selected lane: {queue_context.get('selected_lane', '')}",
        f"Lane selection reason: {queue_context.get('lane_selection_reason', '')}",
        "",
        "Review focus:",
        "- Identify design risks, missing validation, and safety concerns.",
        "- Suggest operator-reviewed implementation or review considerations.",
        "- Keep recommendations advisory and non-mutating.",
        "- Preserve execution_allowed=false and local-only boundaries.",
        "",
        "Source documents to consider:",
    ]
    lines.extend(f"- {document}" for document in _SOURCE_DOCUMENTS)
    lines.extend(
        [
            "",
            "Return a structured advisory response with the expected response shape embedded in this artifact.",
        ]
    )
    return "\n".join(lines).rstrip()


def _expected_response_shape() -> dict[str, Any]:
    return {
        "summary": "string",
        "risks": ["string"],
        "recommendations": ["string"],
        "validation_suggestions": ["string"],
        "files_to_inspect": ["string"],
        "questions_for_operator": ["string"],
        "mutation_allowed": False,
        "execution_allowed": False,
        "patch_application_allowed": False,
    }


def _recommended_model(plan: dict[str, Any]) -> str:
    decision = plan.get("decision_matrix_summary", {}) if isinstance(plan.get("decision_matrix_summary"), dict) else {}
    return str(decision.get("recommended_model", "")).strip()


def _resolve_output_path(config: AppConfig, output: str | Path) -> Path:
    output_path = Path(output)
    if not output_path.is_absolute():
        output_path = (config.repo_root / output_path).resolve()
    return output_path


def _default_output_path(config: AppConfig, item_id: str) -> Path:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    return config.artifact_root / "local_llm_advisory" / "requests" / f"{stamp}-{_slug(item_id)}.json"


def _write_artifact(*, output_path: Path, payload: dict[str, Any], force: bool) -> dict[str, Any]:
    if output_path.exists() and not force:
        return {
            "ok": False,
            "output_path": str(output_path),
            "reason": "Output file already exists. Re-run with --force to overwrite.",
        }
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    except OSError as exc:
        return {
            "ok": False,
            "output_path": str(output_path),
            "reason": f"Failed to write output file: {exc}",
        }
    return {"ok": True, "output_path": str(output_path)}


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _slug(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", str(value or "").lower()).strip("-")
    return normalized or "local-llm-advisory-request"


def _next_safe_action(*, generated: bool, item_id: str) -> str:
    if not generated:
        return "Review blocked reasons before preparing any local LLM advisory request artifact."
    return (
        f"Review the advisory request artifact for {item_id}; do not invoke a local LLM until a separate "
        "operator-approved execution milestone authorizes it."
    )


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
    lines = [
        "# Local LLM Advisory Request Artifact",
        "",
        f"- artifact_type: {payload.get('artifact_type', '')}",
        f"- generated: {payload.get('generated')}",
        f"- blocked: {payload.get('blocked')}",
        f"- item_id: {payload.get('item_id', '')}",
        f"- title: {payload.get('title', '')}",
        f"- queue_status: {payload.get('queue_status', '')}",
        f"- selected_lane: {payload.get('selected_lane', '')}",
        f"- requested_model_profile: {payload.get('requested_model_profile', '')}",
        f"- reasoning_scope: {payload.get('reasoning_scope', '')}",
        f"- output_path: {payload.get('output_path', '') or '-'}",
        f"- local_only: {payload.get('local_only')}",
        f"- execution_allowed: {payload.get('execution_allowed')}",
        f"- local_llm_execution_performed: {payload.get('local_llm_execution_performed')}",
        f"- codex_execution_performed: {payload.get('codex_execution_performed')}",
        f"- network_execution_performed: {payload.get('network_execution_performed')}",
        f"- patch_application_allowed: {payload.get('patch_application_allowed')}",
        f"- next_safe_action: {payload.get('next_safe_action', '')}",
    ]
    blockers = payload.get("blocked_reasons", []) if isinstance(payload.get("blocked_reasons"), list) else []
    if blockers:
        lines.extend(["", "## Blocked Reasons"])
        lines.extend(f"- {reason}" for reason in blockers)
    lines.extend(["", "## Operator Review Checklist"])
    lines.extend(f"- {entry}" for entry in payload.get("operator_review_checklist", []) if str(entry).strip())
    return "\n".join(lines).rstrip()
