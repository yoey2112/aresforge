from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.local_project_queue import resolve_project_queue_path

COMMAND_NAME = "recommend-agent-route"
RECOMMENDATION_VERSION = "m117.1"

_DOC_MARKERS = (
    "documentation",
    "docs",
    "source-of-truth",
    "operator usage",
    "roadmap",
    "decision record",
    "reconciliation",
)
_LOCAL_LLM_MARKERS = ("local llm", "ollama", "advisory", "reasoning", "model profile")
_CODE_MARKERS = ("implement", "cli", "api", "hub", "dashboard", "test", "tests", "patch", "src/")
_VALIDATION_MARKERS = ("validation", "pytest", "smoke", "evidence", "qa")

_BOUNDARY_CONFIRMATIONS = (
    "M117 agent route recommendation is advisory-only.",
    "M117 reads local queue metadata only.",
    "M117 does not dispatch Codex, invoke Ollama or local LLMs, execute agents, call GitHub or gh, make network calls, apply patches, mutate source files, or mutate queue state.",
    "M117 keeps dispatch_performed=false and execution_allowed=false.",
)


def recommend_agent_route(
    config: AppConfig,
    *,
    item_id: str,
    queue_path: str | Path | None = None,
    output: str | Path | None = None,
    force: bool = False,
    output_format: str = "markdown",
) -> dict[str, Any]:
    fmt = str(output_format or "markdown").strip().lower()
    if fmt not in {"markdown", "json"}:
        return _error("invalid_format", {"format": output_format, "supported_formats": ["markdown", "json"]})

    normalized_item_id = str(item_id or "").strip()
    item = _load_queue_item(config, item_id=normalized_item_id, queue_path=queue_path)
    payload = _build_payload(item_id=normalized_item_id, item=item)
    if output is not None:
        write_result = _write_payload(config=config, payload=payload, output=output, force=force)
        if not write_result["ok"]:
            payload["ok"] = False
            payload["blocked"] = True
            payload["blocked_reasons"] = _dedupe([*payload.get("blocked_reasons", []), write_result["reason"]])
            payload["next_safe_action"] = "Review blocked reasons before writing another route recommendation."
        else:
            payload["output_path"] = str(write_result["path"])
    return _stdout_result(COMMAND_NAME, payload, fmt, _render_markdown(payload))


def _build_payload(*, item_id: str, item: dict[str, Any]) -> dict[str, Any]:
    blocked_reasons = [] if item else [f"Queue item not found: {item_id}"]
    signals = _signals(item)
    route = _select_route(item=item, signals=signals, blocked=bool(blocked_reasons))
    return {
        "ok": bool(item) and not blocked_reasons,
        "recommendation_type": "agent_route_recommendation",
        "recommendation_version": RECOMMENDATION_VERSION,
        "generated_at": _now_iso(),
        "blocked": bool(blocked_reasons),
        "blocked_reasons": blocked_reasons,
        "item_id": item_id,
        "title": str(item.get("title", "")).strip(),
        "project_id": str(item.get("project_id", "")).strip(),
        "milestone": _milestone(item, item_id),
        "queue_status": str(item.get("status", "")).strip(),
        "recommended_lane": route["recommended_lane"],
        "alternative_lanes": route["alternative_lanes"],
        "routing_reasons": route["routing_reasons"],
        "required_artifacts_before_dispatch": route["required_artifacts_before_dispatch"],
        "approval_requirements": route["approval_requirements"],
        "local_llm_suitable": bool(route["local_llm_suitable"]),
        "codex_suitable": bool(route["codex_suitable"]),
        "documentation_agent_suitable": bool(route["documentation_agent_suitable"]),
        "human_operator_required": True,
        "dispatch_performed": False,
        "execution_allowed": False,
        "local_only": True,
        "next_safe_action": _next_safe_action(blocked=bool(blocked_reasons), route=route),
        "routing_signals": signals,
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
        "output_path": "",
    }


def _select_route(*, item: dict[str, Any], signals: dict[str, bool], blocked: bool) -> dict[str, Any]:
    if blocked:
        return _route(
            "human_operator_manual_review",
            ["queue_item_lookup"],
            ["Queue item could not be loaded, so only manual review is safe."],
            ["valid_local_queue_item"],
            ["operator_identifies_or_creates_queue_item"],
            local_llm=False,
            codex=False,
            docs=False,
        )
    if signals["documentation"]:
        return _route(
            "documentation_agent_patch_proposal",
            ["local_llm_advisory", "human_operator_manual_review"],
            ["Queue item is documentation-oriented and should start with a documentation proposal artifact."],
            ["documentation_agent_patch_proposal", "operator_review_checklist", "approval_gate_before_patch_intake"],
            ["human reviews proposed documentation changes", "M111 patch intake requires explicit approval"],
            local_llm=True,
            codex=False,
            docs=True,
        )
    if signals["validation"] and not signals["coding"]:
        return _route(
            "validation_agent_dry_run",
            ["human_operator_manual_review", "local_llm_advisory"],
            ["Queue item is validation/evidence-oriented and should remain deterministic and review-only."],
            ["validation_plan", "reported_test_commands", "operator_review_record"],
            ["human confirms validation evidence before completion"],
            local_llm=False,
            codex=False,
            docs=False,
        )
    if signals["local_llm"] and not signals["coding"]:
        return _route(
            "local_llm_advisory_artifact",
            ["human_operator_manual_review", "codex_prompt_artifact"],
            ["Queue item asks for local LLM advisory reasoning; prepare an advisory artifact only."],
            ["local_llm_advisory_request", "operator_review_checklist", "provider_probe_optional"],
            ["human review required before any future advisory run"],
            local_llm=True,
            codex=False,
            docs=False,
        )
    if signals["coding"]:
        return _route(
            "codex_prompt_artifact",
            ["local_llm_advisory_artifact", "documentation_agent_patch_proposal", "human_operator_manual_review"],
            ["Queue item appears to require CLI/API/UI or repository-aware implementation work."],
            ["queue_dispatch_plan", "codex_prompt_artifact", "human_approval_gate", "validation_plan"],
            ["operator approval required before manual Codex handoff", "human review required before any patch intake or completion"],
            local_llm=signals["local_llm"],
            codex=True,
            docs=signals["documentation"],
        )
    return _route(
        "human_operator_manual_review",
        ["local_llm_advisory_artifact", "validation_agent_dry_run"],
        ["Queue item does not clearly map to an automated advisory lane."],
        ["operator_lane_selection_record", "manual_validation_plan"],
        ["human selects lane before any dispatch artifact is prepared"],
        local_llm=True,
        codex=False,
        docs=False,
    )


def _route(
    recommended_lane: str,
    alternative_lanes: list[str],
    routing_reasons: list[str],
    required_artifacts_before_dispatch: list[str],
    approval_requirements: list[str],
    *,
    local_llm: bool,
    codex: bool,
    docs: bool,
) -> dict[str, Any]:
    return {
        "recommended_lane": recommended_lane,
        "alternative_lanes": alternative_lanes,
        "routing_reasons": routing_reasons,
        "required_artifacts_before_dispatch": required_artifacts_before_dispatch,
        "approval_requirements": approval_requirements,
        "local_llm_suitable": local_llm,
        "codex_suitable": codex,
        "documentation_agent_suitable": docs,
    }


def _signals(item: dict[str, Any]) -> dict[str, bool]:
    text = " ".join(
        [
            str(item.get("item_id", "")),
            str(item.get("title", "")),
            str(item.get("description", "")),
            str(item.get("notes", "")),
            str(item.get("item_type", "")),
            " ".join(_list(item.get("tags"))),
        ]
    ).lower()
    item_type = str(item.get("item_type", "")).strip().lower()
    return {
        "documentation": item_type in {"documentation", "handoff"} or any(marker in text for marker in _DOC_MARKERS),
        "local_llm": any(marker in text for marker in _LOCAL_LLM_MARKERS),
        "coding": item_type in {"feature", "bug", "task", "dashboard"} or any(marker in text for marker in _CODE_MARKERS),
        "validation": item_type in {"validation", "test", "qa"} or any(marker in text for marker in _VALIDATION_MARKERS),
    }


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


def _write_payload(*, config: AppConfig, payload: dict[str, Any], output: str | Path, force: bool) -> dict[str, Any]:
    path = _resolve_path(config.repo_root, output)
    if path.exists() and not force:
        return {"ok": False, "reason": f"Output already exists: {path}", "path": path}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"ok": True, "path": path}


def _resolve_path(repo_root: Path, path: str | Path) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = repo_root / candidate
    return candidate.resolve()


def _milestone(item: dict[str, Any], item_id: str) -> str:
    for tag in _list(item.get("tags")):
        if tag.lower().startswith("milestone:"):
            return tag.split(":", 1)[1].strip()
    prefix = item_id.split("-", 1)[0].strip()
    return prefix if prefix else ""


def _next_safe_action(*, blocked: bool, route: dict[str, Any]) -> str:
    if blocked:
        return "Resolve queue item lookup before using route recommendations."
    return f"Review the {route['recommended_lane']} recommendation and prepare only the required local artifacts; do not dispatch or execute from this recommendation."


def _stdout_result(command: str, payload: dict[str, Any], output_format: str, markdown: str) -> dict[str, Any]:
    if output_format == "json":
        stdout = json.dumps(payload, indent=2, sort_keys=True)
    else:
        stdout = markdown
    return {
        "command": command,
        "ok": bool(payload.get("ok", False)),
        "local_only": True,
        "format": output_format,
        "wrote_output_file": bool(payload.get("output_path")),
        "stdout": stdout,
        "payload": payload,
    }


def _render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Agent Route Recommendation",
        "",
        f"- recommendation_type: {payload.get('recommendation_type', '-')}",
        f"- item_id: {payload.get('item_id', '-')}",
        f"- recommended_lane: {payload.get('recommended_lane', '-')}",
        f"- local_llm_suitable: {payload.get('local_llm_suitable', False)}",
        f"- codex_suitable: {payload.get('codex_suitable', False)}",
        f"- documentation_agent_suitable: {payload.get('documentation_agent_suitable', False)}",
        f"- dispatch_performed: {payload.get('dispatch_performed', False)}",
        f"- execution_allowed: {payload.get('execution_allowed', False)}",
        f"- next_safe_action: {payload.get('next_safe_action', '-')}",
    ]
    return "\n".join(lines) + "\n"


def _error(error: str, details: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "ok": False,
        "local_only": True,
        "error": error,
        "details": details,
        "execution_allowed": False,
        "dispatch_performed": False,
    }
    return {"command": COMMAND_NAME, "ok": False, "local_only": True, "format": "json", "stdout": json.dumps(payload, indent=2, sort_keys=True), "payload": payload}


def _list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(str(value).strip() for value in values if str(value).strip()))


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()
