from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.local_project_factory import (
    read_codex_cli_model_profile_contract,
    read_local_llm_environment_contract,
)
from aresforge.operator.local_project_queue import (
    default_queue_routing_metadata,
    inspect_local_queue_item_readiness,
    resolve_project_queue_path,
)

DECISION_MATRIX_VERSION = "m80.1"

_CODING_ITEM_TYPES = {"feature", "bug", "task", "dashboard"}
_REASONING_ITEM_TYPES = {"architecture", "documentation", "validation", "handoff", "orchestration", "sync"}
_HIGH_RISK_MARKERS = {
    "dispatch",
    "execution",
    "runner",
    "queue",
    "routing",
    "decision matrix",
    "llm",
    "codex",
    "safety",
    "gate",
    "evidence",
    "completion",
}
_LARGE_TASK_MARKERS = {
    "cross-module",
    "workflow",
    "end-to-end",
    "orchestration",
    "automation",
    "dispatch",
    "execution",
}

_BOUNDARY_CONFIRMATIONS = (
    "M80 LLM Decision Matrix v2 is local-only and advisory.",
    "Decision matrix inspection does not execute prompts.",
    "Decision matrix inspection does not call Codex.",
    "Decision matrix inspection does not invoke local LLMs.",
    "Decision matrix inspection does not mutate queue items or source files.",
    "No automatic prompt dispatch.",
    "No automatic queue completion.",
    "No automatic next-item execution.",
    "No GitHub API calls.",
    "No gh calls.",
    "No GitHub issues, PRs, workflows, or GitHub mutation.",
    "No external workflow execution.",
)


def inspect_llm_decision_matrix(
    config: AppConfig,
    *,
    item_id: str,
    queue_path: str | Path | None = None,
    registry_path: str | Path | None = None,
    output_format: str = "json",
) -> dict[str, Any]:
    payload = build_llm_decision_matrix(
        config,
        item_id=item_id,
        queue_path=queue_path,
        registry_path=registry_path,
    )
    return _stdout_result(
        "inspect-llm-decision-matrix",
        payload,
        output_format,
        _render_markdown(payload),
    )


def build_llm_decision_matrix(
    config: AppConfig,
    *,
    item_id: str,
    queue_path: str | Path | None = None,
    registry_path: str | Path | None = None,
) -> dict[str, Any]:
    normalized_item_id = str(item_id or "").strip()
    resolved_queue_path = resolve_project_queue_path(config.repo_root, queue_path)
    loaded = _load_queue_item(resolved_queue_path, normalized_item_id)
    warnings: list[str] = list(loaded.get("warnings", []))
    blockers: list[str] = list(loaded.get("blockers", []))
    item = loaded.get("item", {}) if isinstance(loaded.get("item"), dict) else {}

    readiness = inspect_local_queue_item_readiness(
        config,
        item_id=normalized_item_id,
        queue_path=resolved_queue_path,
        registry_path=registry_path,
    )
    if not readiness.get("ok", False):
        blockers.extend(str(blocker) for blocker in readiness.get("blockers", []) if str(blocker).strip())
    warnings.extend(str(warning) for warning in readiness.get("warnings", []) if str(warning).strip())

    routing_metadata = default_queue_routing_metadata(
        item.get("routing_metadata", {}) if isinstance(item.get("routing_metadata"), dict) else {}
    )
    local_profiles = read_local_llm_environment_contract(config)
    codex_profiles = read_codex_cli_model_profile_contract(config)
    warnings.extend(str(warning) for warning in local_profiles.get("warnings", []) if str(warning).strip())
    warnings.extend(str(warning) for warning in codex_profiles.get("warnings", []) if str(warning).strip())

    risk = _classify_risk(item, routing_metadata)
    task_size = _classify_task_size(item, routing_metadata, risk["risk_level"])
    mode = _classify_work_mode(item, routing_metadata)
    engine = _select_engine(
        item=item,
        routing_metadata=routing_metadata,
        work_mode=mode["work_mode"],
        risk_level=risk["risk_level"],
        task_size=task_size["task_size"],
    )
    lane = _select_lane(item, routing_metadata, mode["work_mode"], engine["recommended_engine"])
    model = _select_model(
        routing_metadata=routing_metadata,
        engine=engine["recommended_engine"],
        lane=lane["recommended_lane"],
        local_profiles=local_profiles,
        codex_profiles=codex_profiles,
        task_size=task_size["task_size"],
    )
    validation = _validation_burden(
        risk_level=risk["risk_level"],
        task_size=task_size["task_size"],
        work_mode=mode["work_mode"],
        engine=engine["recommended_engine"],
    )
    confidence = _routing_confidence_scoring(
        item=item,
        readiness=readiness,
        local_profiles=local_profiles,
        codex_profiles=codex_profiles,
        risk=risk,
        task_size=task_size,
        mode=mode,
        engine=engine,
        lane=lane,
        model=model,
        validation=validation,
    )
    warnings.extend(confidence.get("warnings", []))

    payload: dict[str, Any] = {
        "ok": bool(loaded.get("ok", False)) and not blockers,
        "local_only": True,
        "advisory_only": True,
        "decision_matrix_version": DECISION_MATRIX_VERSION,
        "item_id": normalized_item_id,
        "project_id": str(item.get("project_id", "")).strip(),
        "repo_id": str(item.get("repo_id", "")).strip(),
        "queue_item_status": str(item.get("status", "")).strip(),
        "readiness_status": str(readiness.get("readiness_status", "unknown")).strip(),
        "can_start": bool(readiness.get("can_start", False)),
        "routing_metadata": routing_metadata,
        "work_mode": mode,
        "task_sizing": task_size,
        "risk_classification": risk,
        "engine_recommendation": engine,
        "lane_recommendation": lane,
        "model_profile_selection": model,
        "validation_burden": validation,
        "routing_confidence": confidence,
        "safety_gating": _safety_gating(engine["recommended_engine"], risk["risk_level"]),
        "routing_decision": {
            "recommended_engine": engine["recommended_engine"],
            "recommended_lane": lane["recommended_lane"],
            "recommended_model": model["recommended_model"],
            "fallback_engine": engine["fallback_engine"],
            "fallback_model": model["fallback_model"],
            "routing_policy_source": "m80_llm_decision_matrix_v2",
            "routing_reason": engine["routing_reason"],
        },
        "execution_allowed": False,
        "prompt_dispatch_allowed": False,
        "codex_dispatch_allowed": False,
        "local_llm_invocation_allowed": False,
        "queue_mutation_allowed": False,
        "automatic_next_item_execution_allowed": False,
        "warnings": sorted({str(warning).strip() for warning in warnings if str(warning).strip()}),
        "blockers": sorted({str(blocker).strip() for blocker in blockers if str(blocker).strip()}),
        "next_safe_action": _next_safe_action(bool(loaded.get("ok", False)), bool(blockers), engine["recommended_engine"]),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }
    return payload


def _load_queue_item(queue_path: Path, item_id: str) -> dict[str, Any]:
    if not queue_path.exists():
        return {
            "ok": False,
            "item": {},
            "warnings": [f"Local queue file not found: {queue_path}"],
            "blockers": [f"Queue item not found: {item_id}"],
        }
    try:
        raw = json.loads(queue_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"ok": False, "item": {}, "warnings": [], "blockers": [f"Local queue file could not be read: {exc}"]}
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
        return {"ok": False, "item": {}, "warnings": [], "blockers": [f"Queue item not found: {item_id}"]}
    return {"ok": True, "item": item, "warnings": [], "blockers": []}


def _classification_text(item: dict[str, Any], routing_metadata: dict[str, Any]) -> str:
    return " ".join(
        [
            str(item.get("item_id", "")),
            str(item.get("title", "")),
            str(item.get("description", "")),
            str(item.get("notes", "")),
            " ".join(str(value) for value in item.get("tags", []) if isinstance(item.get("tags", []), list)),
            str(routing_metadata.get("routing_reason", "")),
            str(routing_metadata.get("escalation_reason", "")),
        ]
    ).lower()


def _classify_risk(item: dict[str, Any], routing_metadata: dict[str, Any]) -> dict[str, Any]:
    explicit = str(routing_metadata.get("risk_level", "unknown") or "unknown").strip()
    if explicit != "unknown":
        return {"risk_level": explicit, "source": "routing_metadata", "reasons": [f"routing_metadata risk_level is {explicit}"]}
    text = _classification_text(item, routing_metadata)
    matched = sorted(marker for marker in _HIGH_RISK_MARKERS if marker in text)
    item_type = str(item.get("item_type", "")).strip()
    if matched:
        return {"risk_level": "high", "source": "m80_text_classification", "reasons": [f"matched high-risk markers: {', '.join(matched)}"]}
    if item_type in {"documentation", "handoff"}:
        return {"risk_level": "low", "source": "m80_item_type_classification", "reasons": [f"item_type is {item_type}"]}
    return {"risk_level": "medium", "source": "m80_default", "reasons": ["No explicit risk metadata; defaulting to medium."]}


def _classify_task_size(item: dict[str, Any], routing_metadata: dict[str, Any], risk_level: str) -> dict[str, Any]:
    complexity = str(routing_metadata.get("complexity_level", "unknown") or "unknown").strip()
    if complexity == "high":
        return {"task_size": "large", "source": "routing_metadata", "reasons": ["complexity_level is high"]}
    if complexity == "medium":
        return {"task_size": "medium", "source": "routing_metadata", "reasons": ["complexity_level is medium"]}
    if complexity == "low":
        return {"task_size": "small", "source": "routing_metadata", "reasons": ["complexity_level is low"]}
    text = _classification_text(item, routing_metadata)
    matched = sorted(marker for marker in _LARGE_TASK_MARKERS if marker in text)
    if risk_level in {"critical", "high"} and matched:
        return {"task_size": "large", "source": "m80_text_classification", "reasons": [f"matched large-task markers: {', '.join(matched)}"]}
    if len(text.split()) > 80:
        return {"task_size": "medium", "source": "m80_text_classification", "reasons": ["queue item context is moderately detailed"]}
    return {"task_size": "small", "source": "m80_default", "reasons": ["No large-task indicators found."]}


def _classify_work_mode(item: dict[str, Any], routing_metadata: dict[str, Any]) -> dict[str, Any]:
    lane = str(routing_metadata.get("recommended_agent_lane", "")).strip()
    item_type = str(item.get("item_type", "")).strip()
    if lane in {"coding", "test"} or item_type in _CODING_ITEM_TYPES:
        return {"work_mode": "coding", "source": "queue_metadata", "reasons": [f"lane={lane or '-'} item_type={item_type or '-'}"]}
    if lane in {"architect_planner", "reviewer_validator", "documentation", "local_operator_assistant"} or item_type in _REASONING_ITEM_TYPES:
        return {"work_mode": "reasoning", "source": "queue_metadata", "reasons": [f"lane={lane or '-'} item_type={item_type or '-'}"]}
    return {"work_mode": "reasoning", "source": "m80_default", "reasons": ["Defaulting unrouted work to reasoning/advisory review."]}


def _select_engine(
    *,
    item: dict[str, Any],
    routing_metadata: dict[str, Any],
    work_mode: str,
    risk_level: str,
    task_size: str,
) -> dict[str, str]:
    explicit = str(routing_metadata.get("recommended_engine", "")).strip()
    if explicit:
        fallback = "codex_cli" if explicit != "codex_cli" and risk_level in {"high", "critical"} else "local_reasoning_llm"
        return {
            "recommended_engine": explicit,
            "fallback_engine": str(routing_metadata.get("fallback_engine") or fallback).strip(),
            "routing_reason": str(routing_metadata.get("routing_reason") or f"Preserved explicit queue routing to {explicit}.").strip(),
            "source": "routing_metadata",
        }
    item_type = str(item.get("item_type", "")).strip()
    if work_mode == "coding" and (risk_level in {"high", "critical"} or task_size == "large"):
        return {
            "recommended_engine": "codex_cli",
            "fallback_engine": "local_reasoning_llm",
            "routing_reason": "High-risk or large coding work should use Codex as an operator-reviewed handoff path.",
            "source": "m80_policy",
        }
    if work_mode == "coding":
        return {
            "recommended_engine": "local_coding_llm",
            "fallback_engine": "local_reasoning_llm",
            "routing_reason": "Low/medium-risk coding work can use the local coding lane as advisory context.",
            "source": "m80_policy",
        }
    if item_type == "documentation":
        return {
            "recommended_engine": "local_reasoning_llm",
            "fallback_engine": "manual",
            "routing_reason": "Documentation work is best treated as reasoning/review unless coding changes are required.",
            "source": "m80_policy",
        }
    return {
        "recommended_engine": "local_reasoning_llm",
        "fallback_engine": "codex_cli" if risk_level in {"high", "critical"} else "manual",
        "routing_reason": "Architecture, planning, validation, and safety work default to local reasoning advisory review.",
        "source": "m80_policy",
    }


def _select_lane(item: dict[str, Any], routing_metadata: dict[str, Any], work_mode: str, engine: str) -> dict[str, str]:
    explicit = str(routing_metadata.get("recommended_agent_lane", "")).strip()
    if explicit:
        return {"recommended_lane": explicit, "source": "routing_metadata"}
    if engine == "codex_cli":
        return {"recommended_lane": "high_value_codex", "source": "m80_policy"}
    if work_mode == "coding":
        return {"recommended_lane": "coding", "source": "m80_policy"}
    item_type = str(item.get("item_type", "")).strip()
    if item_type == "validation":
        return {"recommended_lane": "reviewer_validator", "source": "m80_policy"}
    if item_type == "documentation":
        return {"recommended_lane": "documentation", "source": "m80_policy"}
    return {"recommended_lane": "architect_planner", "source": "m80_policy"}


def _select_model(
    *,
    routing_metadata: dict[str, Any],
    engine: str,
    lane: str,
    local_profiles: dict[str, Any],
    codex_profiles: dict[str, Any],
    task_size: str,
) -> dict[str, str]:
    explicit = str(routing_metadata.get("recommended_model", "")).strip()
    fallback = str(routing_metadata.get("fallback_model", "")).strip()
    if explicit:
        return {
            "recommended_model": explicit,
            "fallback_model": fallback,
            "model_selection_source": "routing_metadata",
            "profile_status": "advisory_existing_metadata",
        }
    if engine in {"local_reasoning_llm", "local_coding_llm"}:
        environment = local_profiles.get("local_llm_environment", {}) if isinstance(local_profiles.get("local_llm_environment"), dict) else {}
        field = "coding_model" if engine == "local_coding_llm" else "reasoning_model"
        model = str(environment.get(field, "")).strip()
        return {
            "recommended_model": model,
            "fallback_model": fallback or str(environment.get("fallback_model", "")).strip(),
            "model_selection_source": "local_llm_environment_contract",
            "profile_status": str(local_profiles.get("provider_configuration_status", "unknown")).strip(),
        }
    if engine == "codex_cli":
        profiles = codex_profiles.get("codex_cli_model_profiles", {}) if isinstance(codex_profiles.get("codex_cli_model_profiles"), dict) else {}
        preferred = "high_value_codex_model" if lane == "high_value_codex" or task_size == "large" else "default_codex_model"
        model = str(profiles.get(preferred, "") or profiles.get("default_codex_model", "") or profiles.get("fast_codex_model", "")).strip()
        return {
            "recommended_model": model,
            "fallback_model": fallback or str(profiles.get("fast_codex_model", "")).strip(),
            "model_selection_source": "codex_cli_model_profile_contract",
            "profile_status": "configured" if model else "missing_configuration",
        }
    return {
        "recommended_model": "",
        "fallback_model": fallback,
        "model_selection_source": "manual_or_unconfigured",
        "profile_status": "not_applicable",
    }


def _validation_burden(*, risk_level: str, task_size: str, work_mode: str, engine: str) -> dict[str, Any]:
    burden = "medium"
    reasons: list[str] = []
    if risk_level in {"high", "critical"}:
        burden = "high"
        reasons.append(f"risk_level is {risk_level}")
    if task_size == "large":
        burden = "high"
        reasons.append("task_size is large")
    if engine == "codex_cli":
        burden = "high"
        reasons.append("Codex handoff requires review and validation evidence")
    if work_mode == "coding" and burden != "high":
        reasons.append("coding work requires targeted tests and diff checks")
    if burden == "medium" and not reasons:
        reasons.append("default validation burden for advisory reasoning work")
    return {
        "validation_burden": burden,
        "review_evidence_required": True,
        "local_validation_required": True,
        "diff_check_required": True,
        "recommended_validation_focus": _validation_focus(burden, work_mode, engine),
        "reasons": reasons,
    }


def _validation_focus(burden: str, work_mode: str, engine: str) -> list[str]:
    focus = ["git diff --check", "targeted pytest for touched modules"]
    if burden == "high":
        focus.append("source-of-truth doc review")
        focus.append("queue readiness and dispatch-preparation smoke checks")
    if work_mode == "coding":
        focus.append("regression tests for changed behavior")
    if engine == "codex_cli":
        focus.append("operator review of Codex output before queue completion")
    return focus


def _routing_confidence_scoring(
    *,
    item: dict[str, Any],
    readiness: dict[str, Any],
    local_profiles: dict[str, Any],
    codex_profiles: dict[str, Any],
    risk: dict[str, Any],
    task_size: dict[str, Any],
    mode: dict[str, Any],
    engine: dict[str, str],
    lane: dict[str, str],
    model: dict[str, str],
    validation: dict[str, Any],
) -> dict[str, Any]:
    risk_level = str(risk.get("risk_level", "unknown")).strip() or "unknown"
    size = str(task_size.get("task_size", "unknown")).strip() or "unknown"
    work_mode = str(mode.get("work_mode", "unknown")).strip() or "unknown"
    item_type = str(item.get("item_type", "")).strip() or "unknown"
    validation_burden = str(validation.get("validation_burden", "medium")).strip() or "medium"
    dependency_summary = readiness.get("dependency_summary", {}) if isinstance(readiness.get("dependency_summary"), dict) else {}
    dependency_count = _int_value(dependency_summary.get("total_dependencies"))
    unresolved_dependency_count = len(dependency_summary.get("unresolved_dependencies", [])) if isinstance(dependency_summary.get("unresolved_dependencies"), list) else 0
    recovered_count = len(dependency_summary.get("recovered_dispatch_runs", [])) if isinstance(dependency_summary.get("recovered_dispatch_runs"), list) else 0
    dispatch_blocker_count = len(dependency_summary.get("dispatch_run_blockers", [])) if isinstance(dependency_summary.get("dispatch_run_blockers"), list) else 0
    provider_status = str(local_profiles.get("provider_availability_status", "unknown")).strip() or "unknown"
    provider_config_status = str(local_profiles.get("provider_configuration_status", "unknown")).strip() or "unknown"
    local_model_available = _local_model_available(local_profiles=local_profiles, engine=engine["recommended_engine"], model_name=model["recommended_model"])
    codex_model_available = bool(str(model.get("recommended_model", "")).strip()) if engine["recommended_engine"] == "codex_cli" else _codex_profile_has_model(codex_profiles)

    factors = {
        "risk": risk_level,
        "task_size": size,
        "work_mode": work_mode,
        "item_type": item_type,
        "dependency_count": dependency_count,
        "unresolved_dependency_count": unresolved_dependency_count,
        "validation_burden": validation_burden,
        "provider_availability": provider_status,
        "provider_configuration": provider_config_status,
        "local_model_profile_available": local_model_available,
        "codex_model_profile_available": codex_model_available,
        "recovered_dispatch_run_count": recovered_count,
        "dispatch_run_blocker_count": dispatch_blocker_count,
    }
    lane_scores = {
        "codex": _score_codex_lane(factors),
        "local_llm_advisory": _score_local_advisory_lane(factors),
        "local_coding_draft": _score_local_coding_lane(factors),
        "manual_only": _score_manual_lane(factors),
    }
    selected_lane = _confidence_lane_for_engine(engine["recommended_engine"])
    selected_score = lane_scores[selected_lane]["score"]
    warnings: list[str] = []
    if selected_score < 60:
        warnings.append(f"Routing confidence for {selected_lane} is below 60; operator review should treat this route as low confidence.")
    if unresolved_dependency_count:
        warnings.append("Unresolved dependencies reduce routing confidence.")
    if dispatch_blocker_count:
        warnings.append("Dispatch run blockers reduce routing confidence.")

    return {
        "scoring_version": "m86.1",
        "advisory_only": True,
        "execution_allowed": False,
        "recommended_lane": selected_lane,
        "recommended_engine": engine["recommended_engine"],
        "recommended_agent_lane": lane["recommended_lane"],
        "score": selected_score,
        "confidence_level": _confidence_level(selected_score),
        "rationale": lane_scores[selected_lane]["rationale"],
        "warnings": warnings,
        "scores": lane_scores,
        "factors": factors,
        "safety_boundary": {
            "advisory_only": True,
            "execution_allowed": False,
            "queue_mutation_allowed": False,
            "automatic_next_item_execution_allowed": False,
            "github_api_allowed": False,
            "gh_allowed": False,
            "external_workflow_allowed": False,
        },
    }


def _score_codex_lane(factors: dict[str, Any]) -> dict[str, Any]:
    score = 50
    rationale: list[str] = ["base codex confidence 50"]
    score, rationale = _adjust(score, rationale, 20, factors["risk"] in {"high", "critical"}, "high/critical risk favors Codex review")
    score, rationale = _adjust(score, rationale, 15, factors["task_size"] == "large", "large task favors Codex")
    score, rationale = _adjust(score, rationale, 8, factors["work_mode"] == "coding", "coding work can benefit from Codex")
    score, rationale = _adjust(score, rationale, 8, factors["validation_burden"] == "high", "high validation burden favors Codex")
    score, rationale = _adjust(score, rationale, 10, bool(factors["codex_model_profile_available"]), "Codex model profile is available")
    score, rationale = _adjust(score, rationale, -12, not bool(factors["codex_model_profile_available"]), "Codex model profile is missing")
    score, rationale = _adjust(score, rationale, -8, factors["risk"] == "low", "low risk does not require Codex")
    score, rationale = _adjust(score, rationale, -8, bool(factors["unresolved_dependency_count"]), "unresolved dependencies reduce Codex confidence")
    score, rationale = _adjust(score, rationale, -10, bool(factors["dispatch_run_blocker_count"]), "dispatch blockers reduce Codex confidence")
    return {"score": _clamp_score(score), "confidence_level": _confidence_level(score), "rationale": rationale}


def _score_local_advisory_lane(factors: dict[str, Any]) -> dict[str, Any]:
    score = 50
    rationale: list[str] = ["base local advisory confidence 50"]
    score, rationale = _adjust(score, rationale, 15, factors["work_mode"] == "reasoning", "reasoning work favors local advisory")
    score, rationale = _adjust(score, rationale, 10, factors["risk"] in {"low", "medium"}, "low/medium risk fits advisory review")
    score, rationale = _adjust(score, rationale, 10, factors["task_size"] in {"small", "medium"}, "small/medium task size fits advisory review")
    score, rationale = _adjust(score, rationale, 8, factors["provider_configuration"] == "configured", "local provider configuration is present")
    score, rationale = _adjust(score, rationale, 12, bool(factors["local_model_profile_available"]), "local model profile is available")
    score, rationale = _adjust(score, rationale, -15, factors["risk"] in {"high", "critical"}, "high/critical risk lowers local advisory confidence")
    score, rationale = _adjust(score, rationale, -10, factors["task_size"] == "large", "large tasks lower local advisory confidence")
    score, rationale = _adjust(score, rationale, -12, not bool(factors["local_model_profile_available"]), "local model profile is missing")
    score, rationale = _adjust(score, rationale, -8, bool(factors["unresolved_dependency_count"]), "unresolved dependencies reduce advisory confidence")
    score, rationale = _adjust(score, rationale, -6, bool(factors["recovered_dispatch_run_count"]), "recovery history lowers advisory confidence")
    return {"score": _clamp_score(score), "confidence_level": _confidence_level(score), "rationale": rationale}


def _score_local_coding_lane(factors: dict[str, Any]) -> dict[str, Any]:
    score = 45
    rationale: list[str] = ["base local coding draft confidence 45"]
    score, rationale = _adjust(score, rationale, 20, factors["work_mode"] == "coding", "coding work is required for local coding drafts")
    score, rationale = _adjust(score, rationale, 15, factors["risk"] == "low", "low risk supports local coding draft")
    score, rationale = _adjust(score, rationale, 8, factors["risk"] == "medium", "medium risk can support local coding draft with review")
    score, rationale = _adjust(score, rationale, 10, factors["task_size"] in {"small", "medium"}, "small/medium task size supports local coding draft")
    score, rationale = _adjust(score, rationale, 12, bool(factors["local_model_profile_available"]), "local coding model profile is available")
    score, rationale = _adjust(score, rationale, -25, factors["risk"] in {"high", "critical"}, "high/critical risk blocks confidence in local coding draft")
    score, rationale = _adjust(score, rationale, -15, factors["task_size"] == "large", "large task lowers local coding draft confidence")
    score, rationale = _adjust(score, rationale, -10, factors["validation_burden"] == "high", "high validation burden lowers local coding draft confidence")
    score, rationale = _adjust(score, rationale, -12, not bool(factors["local_model_profile_available"]), "local coding model profile is missing")
    return {"score": _clamp_score(score), "confidence_level": _confidence_level(score), "rationale": rationale}


def _score_manual_lane(factors: dict[str, Any]) -> dict[str, Any]:
    score = 35
    rationale: list[str] = ["base manual-only confidence 35"]
    score, rationale = _adjust(score, rationale, 20, bool(factors["unresolved_dependency_count"]), "unresolved dependencies favor manual handling")
    score, rationale = _adjust(score, rationale, 20, bool(factors["dispatch_run_blocker_count"]), "dispatch blockers favor manual handling")
    score, rationale = _adjust(score, rationale, 15, not bool(factors["local_model_profile_available"]) and not bool(factors["codex_model_profile_available"]), "missing model profiles favor manual handling")
    score, rationale = _adjust(score, rationale, 10, factors["risk"] in {"high", "critical"}, "high/critical risk may require manual review")
    score, rationale = _adjust(score, rationale, 8, factors["provider_configuration"] in {"missing_provider", "unknown", "unsupported"}, "provider configuration uncertainty favors manual handling")
    score, rationale = _adjust(score, rationale, -10, factors["risk"] == "low" and factors["task_size"] == "small", "small low-risk work does not require manual-only routing")
    return {"score": _clamp_score(score), "confidence_level": _confidence_level(score), "rationale": rationale}


def _local_model_available(*, local_profiles: dict[str, Any], engine: str, model_name: str) -> bool:
    if engine not in {"local_reasoning_llm", "local_coding_llm"}:
        return bool(str(model_name or "").strip())
    if not str(model_name or "").strip():
        return False
    status = str(local_profiles.get("provider_configuration_status", "")).strip()
    return status == "configured"


def _codex_profile_has_model(codex_profiles: dict[str, Any]) -> bool:
    profiles = codex_profiles.get("codex_cli_model_profiles", {}) if isinstance(codex_profiles.get("codex_cli_model_profiles"), dict) else {}
    return any(str(profiles.get(field, "")).strip() for field in ("high_value_codex_model", "default_codex_model", "fast_codex_model"))


def _confidence_lane_for_engine(engine: str) -> str:
    if engine == "codex_cli":
        return "codex"
    if engine == "local_coding_llm":
        return "local_coding_draft"
    if engine == "local_reasoning_llm":
        return "local_llm_advisory"
    return "manual_only"


def _adjust(score: int, rationale: list[str], delta: int, condition: bool, reason: str) -> tuple[int, list[str]]:
    if condition:
        rationale.append(f"{delta:+d}: {reason}")
        return score + delta, rationale
    return score, rationale


def _clamp_score(score: int) -> int:
    return max(0, min(100, int(score)))


def _confidence_level(score: int) -> str:
    clamped = _clamp_score(score)
    if clamped >= 80:
        return "high"
    if clamped >= 60:
        return "medium"
    return "low"


def _int_value(value: Any) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def _safety_gating(engine: str, risk_level: str) -> dict[str, Any]:
    return {
        "operator_review_required": True,
        "prompt_builder_artifact_only": True,
        "prompt_execution_allowed": False,
        "codex_operator_approval_required": engine == "codex_cli",
        "codex_dispatch_requires_m78_runner": engine == "codex_cli",
        "local_llm_advisory_only": engine in {"local_reasoning_llm", "local_coding_llm"},
        "local_llm_repo_mutation_allowed": False,
        "queue_completion_requires_review_and_validation": True,
        "high_risk_requires_extra_review": risk_level in {"high", "critical"},
    }


def _next_safe_action(item_found: bool, has_blockers: bool, engine: str) -> str:
    if not item_found:
        return "Inspect the local queue and choose a valid item_id."
    if has_blockers:
        return "Resolve readiness or matrix blockers before using the advisory routing output."
    if engine == "codex_cli":
        return "Review the advisory decision, then use prepare-queue-item-dispatch and the M78 approval runner if Codex handoff is desired."
    return "Review the advisory decision before generating any prompt artifact; do not invoke a model from this command."


def _stdout_result(command: str, payload: dict[str, Any], output_format: str, markdown: str) -> dict[str, Any]:
    fmt = str(output_format or "json").lower().strip()
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
    decision = payload.get("routing_decision", {}) if isinstance(payload.get("routing_decision"), dict) else {}
    validation = payload.get("validation_burden", {}) if isinstance(payload.get("validation_burden"), dict) else {}
    lines = [
        "# LLM Decision Matrix v2",
        "",
        f"- ok: {payload.get('ok')}",
        f"- item_id: {payload.get('item_id', '')}",
        f"- recommended_engine: {decision.get('recommended_engine', '')}",
        f"- recommended_lane: {decision.get('recommended_lane', '')}",
        f"- recommended_model: {decision.get('recommended_model', '')}",
        f"- validation_burden: {validation.get('validation_burden', '')}",
        f"- execution_allowed: {payload.get('execution_allowed')}",
        f"- next_safe_action: {payload.get('next_safe_action', '')}",
        "",
        "## Boundaries",
    ]
    lines.extend(f"- {entry}" for entry in payload.get("boundary_confirmations", []))
    blockers = payload.get("blockers", []) if isinstance(payload.get("blockers"), list) else []
    if blockers:
        lines.extend(["", "## Blockers"])
        lines.extend(f"- {entry}" for entry in blockers)
    return "\n".join(lines)
