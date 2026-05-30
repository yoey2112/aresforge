from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.local_project_queue import resolve_project_queue_path

COMMAND_NAME = "recommend-llm-decision"
LLM_DECISION_POLICY_VERSION = "m127.1"

SUPPORTED_LANES = (
    "no_llm_required",
    "local_llm_reasoning",
    "local_llm_coding_review",
    "codex_coding",
    "codex_reasoning",
    "remote_high_value_reasoning",
    "remote_low_cost_reasoning",
    "documentation_agent",
    "validation_agent",
    "github_sync_agent",
)

_DOC_TYPES = {"documentation", "handoff"}
_CODE_TYPES = {"feature", "bug", "task", "dashboard"}
_VALIDATION_TYPES = {"validation", "test", "qa"}
_GITHUB_TYPES = {"sync", "github", "release"}
_PLANNING_TYPES = {"architecture", "planning", "orchestration"}
_NO_LLM_TYPES = {"chore", "maintenance", "data"}
_RISK_ORDER = {"low": 1, "medium": 2, "high": 3, "critical": 4, "unknown": 2}

_BOUNDARY_CONFIRMATIONS = (
    "M127 LLM Decision Policy v1 is recommendation-only.",
    "M127 does not execute Codex, local LLMs, remote LLMs, agents, GitHub, gh, network services, patches, tests, or validation commands.",
    "M127 may recommend a future lane, provider, or model profile, but execution remains a separate operator-approved workflow.",
    "M127 preserves execution_performed=false for every recommendation.",
)


def recommend_llm_decision(
    config: AppConfig,
    *,
    item_id: str,
    agent_id: str | None = None,
    task_type: str | None = None,
    risk_level: str | None = None,
    mutation_scope: str | None = None,
    queue_path: str | Path | None = None,
    output: str | Path | None = None,
    force: bool = False,
    output_format: str = "json",
) -> dict[str, Any]:
    fmt = str(output_format or "json").lower().strip()
    if fmt != "json":
        return _error("invalid_format", {"format": output_format, "supported_formats": ["json"]})

    normalized_item_id = str(item_id or "").strip()
    queue_item = _load_queue_item(config, item_id=normalized_item_id, queue_path=queue_path)
    payload = _build_payload(
        config=config,
        item_id=normalized_item_id,
        item=queue_item,
        agent_id=agent_id,
        task_type=task_type,
        risk_level=risk_level,
        mutation_scope=mutation_scope,
    )
    return _emit_or_write(config=config, payload=payload, output=output, force=force)


def _build_payload(
    *,
    config: AppConfig,
    item_id: str,
    item: dict[str, Any],
    agent_id: str | None,
    task_type: str | None,
    risk_level: str | None,
    mutation_scope: str | None,
) -> dict[str, Any]:
    features = _classify_features(
        item=item,
        agent_id=agent_id,
        task_type=task_type,
        risk_level=risk_level,
        mutation_scope=mutation_scope,
    )
    decision = _select_lane(features)
    risk = _risk_assessment(features, decision)
    return {
        "recommendation_type": "llm_decision_policy_v1",
        "policy_version": LLM_DECISION_POLICY_VERSION,
        "generated_at": _now_iso(),
        "item_id": item_id,
        "item_found": bool(item),
        "agent_id": features["agent_id"],
        "recommended_lane": decision["lane"],
        "recommended_provider": decision["provider"],
        "recommended_model_profile": decision["model_profile"],
        "alternatives": decision["alternatives"],
        "decision_reasons": decision["reasons"],
        "risk_assessment": risk,
        "autonomy_allowed": _autonomy_allowed(features, risk, decision),
        "machine_gate_required": _machine_gate_required(features, risk, decision),
        "human_review_required": _human_review_required(features, risk, decision),
        "execution_performed": False,
        "local_only": decision["local_only"],
        "next_safe_action": _next_safe_action(bool(item), decision, risk),
        "decision_inputs": features,
        "supported_lanes": list(SUPPORTED_LANES),
        "repo_root": str(config.repo_root),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }


def _classify_features(
    *,
    item: dict[str, Any],
    agent_id: str | None,
    task_type: str | None,
    risk_level: str | None,
    mutation_scope: str | None,
) -> dict[str, Any]:
    routing = item.get("routing_metadata", {}) if isinstance(item.get("routing_metadata"), dict) else {}
    tags = _list(item.get("tags"))
    text = " ".join(
        [
            str(item.get("item_id", "")),
            str(item.get("title", "")),
            str(item.get("description", "")),
            str(item.get("notes", "")),
            " ".join(tags),
            str(routing.get("routing_reason", "")),
            str(routing.get("escalation_reason", "")),
        ]
    ).lower()
    normalized_type = _normalize(task_type) or _normalize(item.get("item_type")) or "unknown"
    normalized_agent = _normalize(agent_id) or _normalize(item.get("assigned_agent")) or _agent_from_type(normalized_type)
    explicit_risk = _normalize(risk_level) or _normalize(routing.get("risk_level"))
    normalized_risk = explicit_risk if explicit_risk in _RISK_ORDER and explicit_risk != "unknown" else _infer_risk(text, normalized_type)
    normalized_mutation = _normalize(mutation_scope) or _infer_mutation_scope(text, normalized_type)
    context_size = _context_size(text)
    repo_aware = normalized_type in _CODE_TYPES or any(token in text for token in ("src/", "tests/", ".py", "implementation", "refactor", "patch"))
    deterministic_validation = normalized_type in _VALIDATION_TYPES or any(token in text for token in ("pytest", "test", "validation", "smoke", "diff check"))
    github_required = normalized_agent == "github-sync-agent" or normalized_type in _GITHUB_TYPES
    local_only = "local-only" in tags or "local_only" in text or not github_required
    tests_can_verify = deterministic_validation or repo_aware or "tests_run" in _list(item.get("completion_requires"))
    autonomous_requested = any(
        token in text for token in ("autonomy allowed", "autonomous allowed", "allow autonomous", "future autonomous")
    ) and "manual_only" not in text
    return {
        "task_type": normalized_type,
        "risk_level": normalized_risk,
        "mutation_scope": normalized_mutation,
        "agent_id": normalized_agent,
        "work_kind": _work_kind(normalized_type, text),
        "context_size": context_size,
        "repo_aware_coding_need": repo_aware,
        "deterministic_validation_need": deterministic_validation,
        "local_only_requirement": local_only,
        "github_or_network_requirement": github_required,
        "tests_can_verify_output": tests_can_verify,
        "autonomous_execution_requested": autonomous_requested,
        "queue_status": _normalize(item.get("status")),
        "source": "queue_metadata_with_cli_overrides",
    }


def _select_lane(features: dict[str, Any]) -> dict[str, Any]:
    reasons: list[str] = []
    alternatives: list[dict[str, str]] = []
    task_type = features["task_type"]
    risk_level = features["risk_level"]
    mutation_scope = features["mutation_scope"]
    work_kind = features["work_kind"]
    local_only = bool(features["local_only_requirement"])
    github_required = bool(features["github_or_network_requirement"])
    repo_aware = bool(features["repo_aware_coding_need"])
    deterministic_validation = bool(features["deterministic_validation_need"])

    if github_required:
        return _decision(
            "github_sync_agent",
            "agent_registry",
            "github_sync_metadata_only",
            ["GitHub or network synchronization is part of the task context."],
            [{"lane": "remote_high_value_reasoning", "reason": "Use only after a separate network-enabled sync milestone exists."}],
            local_only=False,
        )
    if task_type in _VALIDATION_TYPES or features["agent_id"] == "validation-agent" or (
        deterministic_validation and not repo_aware
    ):
        return _decision(
            "validation_agent",
            "agent_registry",
            "deterministic_validation_plan",
            ["Deterministic validation evidence is the primary need."],
            [{"lane": "no_llm_required", "reason": "Use when validation commands are already known and no plan is needed."}],
            local_only=True,
        )
    if task_type in _NO_LLM_TYPES and mutation_scope in {"none", "read_only"}:
        return _decision(
            "no_llm_required",
            "none",
            "not_applicable",
            ["Task appears deterministic and read-only, so no LLM is required."],
            [{"lane": "validation_agent", "reason": "Use if deterministic checks still need a recorded plan."}],
            local_only=True,
        )
    if work_kind == "documentation":
        return _decision(
            "documentation_agent",
            "agent_registry",
            "documentation_reconciliation_plan",
            ["Documentation-oriented work should use the documentation agent recommendation lane."],
            [{"lane": "local_llm_reasoning", "reason": "Use for advisory source-of-truth reasoning before doc patch planning."}],
            local_only=True,
        )
    if repo_aware and risk_level in {"high", "critical"}:
        return _decision(
            "codex_coding",
            "codex",
            "codex_high_value",
            ["Repo-aware coding with high risk should use an operator-reviewed Codex coding handoff."],
            [{"lane": "local_llm_coding_review", "reason": "Use only for advisory review when local-only constraints forbid Codex handoff."}],
            local_only=False,
        )
    if repo_aware:
        return _decision(
            "local_llm_coding_review",
            "local",
            "local_coding_review",
            ["Repo-aware coding is present but risk does not require the high-value Codex lane."],
            [{"lane": "codex_coding", "reason": "Use when validation burden, blast radius, or operator confidence requires Codex."}],
            local_only=True,
        )
    if risk_level in {"high", "critical"} and not local_only:
        return _decision(
            "remote_high_value_reasoning",
            "remote",
            "high_value_reasoning",
            ["High-risk reasoning with network allowance can be escalated to a future high-value remote reasoning lane."],
            [{"lane": "codex_reasoning", "reason": "Use when repo-aware context or Codex handoff is preferred."}],
            local_only=False,
        )
    if risk_level in {"high", "critical"}:
        return _decision(
            "codex_reasoning",
            "codex",
            "codex_reasoning",
            ["High-risk local reasoning should use an operator-reviewed Codex reasoning handoff."],
            [{"lane": "local_llm_reasoning", "reason": "Use for local-only advisory reasoning with human review."}],
            local_only=False,
        )
    if work_kind == "planning" and not local_only:
        return _decision(
            "remote_low_cost_reasoning",
            "remote",
            "low_cost_reasoning",
            ["Planning/reasoning work may use a low-cost future remote reasoning lane when network use is allowed."],
            [{"lane": "local_llm_reasoning", "reason": "Use when local-only operation is preferred."}],
            local_only=False,
        )
    reasons.append("Defaulting planning and advisory work to local reasoning.")
    alternatives.append({"lane": "codex_reasoning", "reason": "Use for high-risk, large-context, or operator-critical reasoning."})
    return _decision("local_llm_reasoning", "local", "local_reasoning", reasons, alternatives, local_only=True)


def _decision(
    lane: str,
    provider: str,
    model_profile: str,
    reasons: list[str],
    alternatives: list[dict[str, str]],
    *,
    local_only: bool,
) -> dict[str, Any]:
    return {
        "lane": lane,
        "provider": provider,
        "model_profile": model_profile,
        "reasons": reasons,
        "alternatives": alternatives,
        "local_only": local_only,
    }


def _risk_assessment(features: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
    risk_level = features["risk_level"]
    score = _RISK_ORDER.get(risk_level, 2)
    if features["mutation_scope"] not in {"none", "read_only", "docs_only"}:
        score += 1
    if features["github_or_network_requirement"]:
        score += 1
    if decision["lane"] in {"codex_coding", "remote_high_value_reasoning", "github_sync_agent"}:
        score += 1
    effective = "critical" if score >= 5 else "high" if score >= 4 else "medium" if score >= 2 else "low"
    return {
        "declared_risk_level": risk_level,
        "effective_risk_level": effective,
        "mutation_scope": features["mutation_scope"],
        "context_size": features["context_size"],
        "tests_can_verify_output": features["tests_can_verify_output"],
        "risk_reasons": _risk_reasons(features, decision),
    }


def _risk_reasons(features: dict[str, Any], decision: dict[str, Any]) -> list[str]:
    reasons = [f"selected_lane={decision['lane']}", f"risk_level={features['risk_level']}"]
    if features["mutation_scope"] not in {"none", "read_only"}:
        reasons.append(f"mutation_scope={features['mutation_scope']}")
    if features["github_or_network_requirement"]:
        reasons.append("github_or_network_requirement=true")
    if not features["tests_can_verify_output"]:
        reasons.append("tests_can_verify_output=false")
    return reasons


def _autonomy_allowed(features: dict[str, Any], risk: dict[str, Any], decision: dict[str, Any]) -> bool:
    if decision["lane"] in {"no_llm_required", "validation_agent"}:
        return bool(features["tests_can_verify_output"]) and risk["effective_risk_level"] in {"low", "medium"}
    return (
        bool(features["autonomous_execution_requested"])
        and bool(features["tests_can_verify_output"])
        and risk["effective_risk_level"] == "low"
        and decision["lane"] in {"local_llm_reasoning", "documentation_agent"}
    )


def _machine_gate_required(features: dict[str, Any], risk: dict[str, Any], decision: dict[str, Any]) -> bool:
    return decision["lane"] != "no_llm_required" or risk["effective_risk_level"] in {"high", "critical"} or features["mutation_scope"] != "none"


def _human_review_required(features: dict[str, Any], risk: dict[str, Any], decision: dict[str, Any]) -> bool:
    return decision["lane"] != "no_llm_required" or risk["effective_risk_level"] in {"medium", "high", "critical"} or features["mutation_scope"] != "none"


def _next_safe_action(item_found: bool, decision: dict[str, Any], risk: dict[str, Any]) -> str:
    if not item_found:
        return "Add or select a valid local queue item before using this recommendation."
    if decision["lane"] == "no_llm_required":
        return "Proceed with deterministic local validation or operator review; no model execution is recommended."
    if decision["lane"] in {"codex_coding", "codex_reasoning"}:
        return "Generate or review an operator-gated Codex handoff artifact; do not execute Codex from this command."
    if decision["lane"].startswith("remote_") or decision["lane"] == "github_sync_agent":
        return "Treat this as future escalation metadata only; use a separate approved network/GitHub workflow before execution."
    if risk["effective_risk_level"] in {"high", "critical"}:
        return "Require human review and machine-gate evidence before any future execution milestone uses this lane."
    return "Review the recommendation and generate only local artifacts from explicit follow-on commands."


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


def _agent_from_type(task_type: str) -> str:
    if task_type in _DOC_TYPES:
        return "documentation-agent"
    if task_type in _VALIDATION_TYPES:
        return "validation-agent"
    if task_type in _GITHUB_TYPES:
        return "github-sync-agent"
    return ""


def _work_kind(task_type: str, text: str) -> str:
    if task_type in _DOC_TYPES:
        return "documentation"
    if task_type in _CODE_TYPES or any(token in text for token in ("code", "implementation", "refactor", "src/", "tests/")):
        return "code"
    if task_type in _VALIDATION_TYPES:
        return "validation"
    if task_type in _GITHUB_TYPES:
        return "github"
    if task_type in _PLANNING_TYPES:
        return "planning"
    return "planning"


def _infer_risk(text: str, task_type: str) -> str:
    if any(token in text for token in ("critical", "credential", "secret", "production", "runner", "execution", "dispatch")):
        return "critical"
    if any(token in text for token in ("high risk", "github", "network", "mutation", "patch", "queue", "llm", "codex")):
        return "high"
    if task_type in _DOC_TYPES or task_type in _NO_LLM_TYPES:
        return "low"
    return "medium"


def _infer_mutation_scope(text: str, task_type: str) -> str:
    if task_type in _DOC_TYPES:
        return "docs_only"
    if task_type in _NO_LLM_TYPES:
        return "none"
    if "read-only" in text or "read_only" in text:
        return "read_only"
    if task_type in _CODE_TYPES:
        return "source_code"
    if task_type in _GITHUB_TYPES:
        return "external_metadata"
    return "artifact_only"


def _context_size(text: str) -> str:
    words = text.split()
    if len(words) > 120:
        return "large"
    if len(words) > 45:
        return "medium"
    return "small"


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
            "ok": bool(payload.get("item_found")),
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
        "ok": bool(payload.get("item_found")),
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


def _normalize(value: Any) -> str:
    return str(value or "").strip().lower().replace(" ", "_")


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
