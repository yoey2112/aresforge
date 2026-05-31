from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.agent_registry import build_agent_registry
from aresforge.operator.agent_runtime_boundary import inspect_agent_runtime_boundary
from aresforge.operator.local_project_queue import resolve_project_queue_path
from aresforge.operator.machine_safety_gate_engine import GATE_PROFILES, evaluate_machine_safety_gates

COMMAND_NAME = "generate-autonomous-sprint-closeout"
CLOSEOUT_VERSION = "m139.1"

SOURCE_OF_TRUTH_DOCS: tuple[str, ...] = (
    "docs/context/BUILD_STATE.md",
    "docs/context/AGENT_CONTEXT.md",
    "docs/roadmap/ROADMAP.md",
    "docs/operator/LOCAL_OPERATOR_USAGE.md",
    "docs/architecture/RUNNABLE_SKELETON.md",
    "docs/architecture/AGENT_LLM_ROUTING_STRATEGY.md",
    "docs/architecture/LOCAL_LLM_ENVIRONMENT_CONTRACT.md",
    "docs/architecture/DOCUMENTATION_AGENT_CONTRACT.md",
)

MILESTONE_SUMMARIES: tuple[dict[str, str], ...] = (
    {
        "milestone": "M125",
        "title": "Agent Runtime Boundary Contract",
        "summary": "Defined local agent runtime schema, capability catalogs, mutation/network/model scopes, evidence requirements, safety classes, and autonomy levels without execution.",
    },
    {
        "milestone": "M126",
        "title": "Agent Registry",
        "summary": "Declared the initial AresForge agent registry with capabilities, scopes, safety classes, autonomy levels, evidence requirements, and dry-run/real eligibility.",
    },
    {
        "milestone": "M127",
        "title": "LLM Decision Policy v1",
        "summary": "Added deterministic LLM/provider/lane recommendation records for queue items and agents without invoking models or mutating state.",
    },
    {
        "milestone": "M128",
        "title": "Agent Orchestration Plan Builder",
        "summary": "Built ordered, non-executing orchestration plans from queue state, registry metadata, and the LLM decision policy.",
    },
    {
        "milestone": "M129",
        "title": "Single-Agent Dry-Run Executor",
        "summary": "Produced single-agent dry-run execution records for deterministic low-risk local agents while blocking external/model/GitHub/patch behavior.",
    },
    {
        "milestone": "M130",
        "title": "Single-Agent Real Executor for Low-Risk Agents",
        "summary": "Enabled real execution only for deterministic low-risk local agents that write local execution records and artifacts.",
    },
    {
        "milestone": "M131",
        "title": "Machine Safety Gate Engine",
        "summary": "Introduced deterministic machine safety gates for read-only agents, local artifact writes, queue status mutation, docs-only patch application, local LLM execution, Codex dispatch, GitHub sync, and orchestration.",
    },
    {
        "milestone": "M132",
        "title": "Auto-Completion for Safe Queue Items",
        "summary": "Allowed low-risk queue completion without human review only when deterministic evidence and queue mutation machine gates pass.",
    },
    {
        "milestone": "M133",
        "title": "Documentation Agent Autonomous Apply for Docs-Only Patches",
        "summary": "Added the first autonomous docs-only Markdown patch apply path behind docs-only machine gates and transaction logging.",
    },
    {
        "milestone": "M134",
        "title": "Local LLM Advisory Execution",
        "summary": "Added a gated local Ollama advisory execution path that writes advisory artifacts only and never applies model output.",
    },
    {
        "milestone": "M135",
        "title": "Codex Dispatch Executor v1",
        "summary": "Added artifact-driven Codex dispatch behind explicit execution enablement and codex_dispatch machine gates.",
    },
    {
        "milestone": "M136",
        "title": "Codex Result Ingestion and Validation Runner",
        "summary": "Added local Codex execution-record ingestion, validation profile execution, evidence generation, and completion handoff artifacts.",
    },
    {
        "milestone": "M137",
        "title": "GitHub PR/Issue Sync Agent",
        "summary": "Added dry-run-first GitHub issue/PR sync with narrow comments and metadata summaries behind explicit GitHub enablement and gates.",
    },
    {
        "milestone": "M138",
        "title": "Multi-Agent Orchestrator v1",
        "summary": "Added step-by-step orchestration with dry-run defaults, per-step machine gates, low-risk real execution, high-risk allow flags, and fail-fast timelines.",
    },
    {
        "milestone": "M139",
        "title": "Autonomous Sprint Closeout v1",
        "summary": "Reconciles the M125-M139 sprint, emits a closeout artifact, and records the transition from human-gated review to machine-gated autonomy.",
    },
)


def generate_autonomous_sprint_closeout(
    config: AppConfig,
    *,
    project_id: str,
    sprint_start: str = "M125",
    sprint_end: str = "M139",
    dry_run: bool = False,
    apply_docs_only: bool = False,
    queue_path: str | Path | None = None,
    output: str | Path | None = None,
    force: bool = False,
    output_format: str = "json",
) -> dict[str, Any]:
    fmt = str(output_format or "json").strip().lower()
    if fmt != "json":
        return _error("invalid_format", {"format": output_format, "supported_formats": ["json"]})

    normalized_project_id = str(project_id or "").strip()
    normalized_start = _normalize_milestone(sprint_start) or "M125"
    normalized_end = _normalize_milestone(sprint_end) or "M139"
    queue = _load_queue(config, queue_path)
    items = _milestone_items(queue, normalized_project_id, normalized_start, normalized_end)
    registry = build_agent_registry(config)
    runtime_boundary = inspect_agent_runtime_boundary(config, output_format="json").get("payload", {})
    docs_status = _inspect_docs(config.repo_root, normalized_start, normalized_end)
    artifacts = _inspect_artifacts(config.artifact_root)
    transaction_log = _inspect_transaction_log(config.repo_root)
    gate_status = _inspect_machine_gates(config, normalized_project_id, queue, queue_path)

    docs_updated: list[str] = []
    docs_applied = False
    docs_apply_blockers: list[str] = []
    if apply_docs_only:
        if dry_run:
            docs_apply_blockers.append("Docs-only application requested with --dry-run; no documentation files were changed.")
        elif not gate_status["docs_only_apply_gate_passed"]:
            docs_apply_blockers.append("Docs-only application gate did not pass.")
        else:
            docs_updated = _apply_docs_marker(config.repo_root)
            docs_applied = bool(docs_updated)

    completed_items = [item for item in items if item["status"] == "done"]
    incomplete_items = [item for item in items if item["status"] not in {"done", "cancelled"}]
    blocked_items = [item for item in items if item["status"] == "blocked" or item.get("blocked_by")]
    warnings = _warnings(
        docs_status=docs_status,
        missing_milestones=_missing_milestones(items, normalized_start, normalized_end),
        docs_apply_blockers=docs_apply_blockers,
    )
    blockers = _blockers(normalized_project_id, docs_apply_blockers)

    payload = {
        "closeout_type": "autonomous_sprint_closeout_v1",
        "closeout_version": CLOSEOUT_VERSION,
        "project_id": normalized_project_id,
        "sprint_start": normalized_start,
        "sprint_end": normalized_end,
        "generated": _now_iso(),
        "dry_run": bool(dry_run),
        "docs_applied": docs_applied,
        "milestones_reviewed": _milestones(normalized_start, normalized_end),
        "completed_items": completed_items,
        "incomplete_items": incomplete_items,
        "blocked_items": blocked_items,
        "implemented_capabilities": _implemented_capabilities(normalized_start, normalized_end),
        "autonomy_capabilities": _autonomy_capabilities(),
        "remaining_human_gates": _remaining_human_gates(),
        "machine_gates_available": gate_status,
        "agents_available": {
            "available": bool(registry.get("agent_count")),
            "agent_count": registry.get("agent_count", 0),
            "executable_agents": registry.get("executable_agents", []),
            "dry_run_only_agents": registry.get("dry_run_only_agents", []),
        },
        "orchestration_available": {
            "available": True,
            "command": "python -m aresforge run-agent-orchestration --item-id <item_id> --format json",
            "default": "dry_run",
        },
        "llm_decision_available": {
            "available": True,
            "command": "python -m aresforge recommend-llm-decision --item-id <item_id> --format json",
            "execution_performed": False,
        },
        "codex_execution_available": {
            "available": True,
            "requires": ["--execution-enabled", "codex_dispatch machine gate", "M136 validation before completion"],
            "command": "python -m aresforge run-codex-dispatch --item-id <item_id> --artifact-path <path> --format json",
        },
        "local_llm_execution_available": {
            "available": True,
            "requires": ["local provider", "local_llm_execution machine gate", "advisory-only output"],
            "command": "python -m aresforge run-local-llm-advisory --item-id <item_id> --artifact-path <path> --format json",
        },
        "github_sync_available": {
            "available": True,
            "requires": ["--github-enabled", "github_sync machine gate", "narrow issue/PR sync mode"],
            "command": "python -m aresforge run-github-sync-agent --item-id <item_id> --format json",
        },
        "docs_updated": docs_updated,
        "docs_consistency": docs_status,
        "artifacts": artifacts,
        "transaction_log": transaction_log,
        "runtime_boundary_available": bool(runtime_boundary),
        "next_sprint_recommendations": _next_sprint_recommendations(),
        "warnings": warnings,
        "blockers": blockers,
        "local_only": True,
        "execution_performed": False,
        "model_execution_performed": False,
        "codex_execution_performed": False,
        "github_execution_performed": False,
        "queue_mutation_performed": False,
        "next_safe_action": _next_safe_action(blockers, docs_status),
    }
    return _emit_or_write(config=config, payload=payload, output=output, force=force)


def _load_queue(config: AppConfig, queue_path: str | Path | None) -> dict[str, Any]:
    path = resolve_project_queue_path(config.repo_root, queue_path)
    if not path.exists():
        return {"work_items": [], "queue_path": str(path), "warnings": [f"Queue file missing: {path}"]}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"work_items": [], "queue_path": str(path), "warnings": [f"Queue file could not be read: {exc}"]}
    if not isinstance(data, dict):
        return {"work_items": [], "queue_path": str(path), "warnings": ["Queue JSON root is not an object."]}
    data["queue_path"] = str(path)
    return data


def _milestone_items(
    queue: dict[str, Any],
    project_id: str,
    sprint_start: str,
    sprint_end: str,
) -> list[dict[str, Any]]:
    milestones = set(_milestones(sprint_start, sprint_end))
    items = []
    for item in queue.get("work_items", []):
        if not isinstance(item, dict):
            continue
        if project_id and str(item.get("project_id", "")).strip() != project_id:
            continue
        milestone = _item_milestone(item)
        if milestone not in milestones:
            continue
        items.append(
            {
                "milestone": milestone,
                "item_id": str(item.get("item_id", "")).strip(),
                "title": str(item.get("title", "")).strip(),
                "status": str(item.get("status", "")).strip(),
                "completion_commit": str(item.get("completion_commit", "")).strip(),
                "validation_summary": str(item.get("validation_summary", "")).strip(),
                "tests_run": _list(item.get("tests_run")),
                "artifact_paths": _list(item.get("artifact_paths")),
                "blocked_by": _list(item.get("blocked_by")),
            }
        )
    return sorted(items, key=lambda item: (_milestone_number(item["milestone"]), item["item_id"]))


def _item_milestone(item: dict[str, Any]) -> str:
    for tag in _list(item.get("tags")):
        if tag.lower().startswith("milestone:m"):
            return _normalize_milestone(tag.split(":", 1)[1]) or ""
    item_id = str(item.get("item_id", "")).strip().lower()
    if item_id.startswith("m") and "-" in item_id:
        return _normalize_milestone(item_id.split("-", 1)[0]) or ""
    return ""


def _inspect_docs(repo_root: Path, sprint_start: str, sprint_end: str) -> dict[str, Any]:
    milestones = _milestones(sprint_start, sprint_end)
    docs: list[dict[str, Any]] = []
    missing_docs: list[str] = []
    missing_mentions: dict[str, list[str]] = {}
    for relative in SOURCE_OF_TRUTH_DOCS:
        path = repo_root / relative
        if not path.exists():
            missing_docs.append(relative)
            docs.append({"path": relative, "exists": False, "mentions": []})
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        mentions = [milestone for milestone in milestones if milestone in text]
        docs.append({"path": relative, "exists": True, "mentions": mentions})
        missing = [milestone for milestone in milestones if milestone not in text]
        if missing:
            missing_mentions[relative] = missing
    return {
        "source_docs": docs,
        "missing_docs": missing_docs,
        "missing_milestone_mentions": missing_mentions,
        "consistent": not missing_docs and not missing_mentions,
    }


def _inspect_artifacts(artifact_root: Path) -> dict[str, Any]:
    roots = (
        "agent-executions",
        "auto-completion",
        "codex_dispatch",
        "codex_result_ingestion",
        "documentation_agent",
        "github_sync_agent",
        "local_llm_advisory",
        "multi-agent-orchestration",
        "orchestration",
    )
    by_root: dict[str, int] = {}
    latest_by_root: dict[str, str] = {}
    for root in roots:
        path = artifact_root / root
        files = sorted(candidate for candidate in path.rglob("*") if candidate.is_file()) if path.exists() else []
        by_root[root] = len(files)
        latest_by_root[root] = str(max(files, key=lambda candidate: candidate.stat().st_mtime)) if files else ""
    return {
        "artifact_root": str(artifact_root),
        "inspected_roots": list(roots),
        "file_counts": by_root,
        "latest_artifacts": latest_by_root,
    }


def _inspect_transaction_log(repo_root: Path) -> dict[str, Any]:
    path = repo_root / ".aresforge" / "queue" / "transaction_log.json"
    if not path.exists():
        return {"path": str(path), "exists": False, "transaction_count": 0, "latest_transaction": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"path": str(path), "exists": True, "transaction_count": 0, "warnings": [str(exc)], "latest_transaction": {}}
    transactions = data.get("transactions", []) if isinstance(data, dict) else []
    transactions = [entry for entry in transactions if isinstance(entry, dict)]
    return {
        "path": str(path),
        "exists": True,
        "transaction_count": len(transactions),
        "latest_transaction": transactions[-1] if transactions else {},
    }


def _inspect_machine_gates(
    config: AppConfig,
    project_id: str,
    queue: dict[str, Any],
    queue_path: str | Path | None,
) -> dict[str, Any]:
    closeout_item = _find_closeout_item(queue, project_id)
    item_id = str(closeout_item.get("item_id", "")).strip()
    gate_result = {}
    if item_id:
        gate_result = evaluate_machine_safety_gates(
            config,
            item_id=item_id,
            gate_profile="read_only_agent",
            queue_path=queue_path,
            output_format="json",
        ).get("payload", {})
    return {
        "available": True,
        "gate_profiles": list(GATE_PROFILES),
        "closeout_item_id": item_id,
        "read_only_closeout_gate_passed": bool(gate_result.get("passed")) and not bool(gate_result.get("blocked")),
        "read_only_closeout_gate_blocked_reasons": _list(gate_result.get("blocked_reasons")),
        "docs_only_apply_gate_passed": bool(closeout_item) and _has_validation_evidence(closeout_item),
        "replaces_human_review_for": [
            "read-only agent inspection",
            "local artifact writes",
            "low-risk queue status mutation",
            "docs-only Markdown patch application",
            "local LLM advisory execution",
            "Codex dispatch",
            "GitHub issue/PR sync",
            "multi-agent orchestration",
        ],
    }


def _find_closeout_item(queue: dict[str, Any], project_id: str) -> dict[str, Any]:
    for item in queue.get("work_items", []):
        if not isinstance(item, dict):
            continue
        if project_id and str(item.get("project_id", "")).strip() != project_id:
            continue
        if _item_milestone(item) == "M139":
            return item
    return {}


def _has_validation_evidence(item: dict[str, Any]) -> bool:
    return bool(
        _list(item.get("tests_run"))
        or _list(item.get("artifact_paths"))
        or str(item.get("validation_summary", "")).strip()
        or str(item.get("evidence_note", "")).strip()
    )


def _apply_docs_marker(repo_root: Path) -> list[str]:
    marker = "\n\n<!-- M139 autonomous sprint closeout docs-only marker: applied -->\n"
    changed: list[str] = []
    for relative in SOURCE_OF_TRUTH_DOCS:
        path = repo_root / relative
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if marker.strip() in text:
            continue
        path.write_text(text.rstrip() + marker, encoding="utf-8")
        changed.append(relative)
    return changed


def _implemented_capabilities(sprint_start: str, sprint_end: str) -> list[dict[str, str]]:
    milestones = set(_milestones(sprint_start, sprint_end))
    return [dict(summary) for summary in MILESTONE_SUMMARIES if summary["milestone"] in milestones]


def _autonomy_capabilities() -> list[dict[str, str]]:
    return [
        {
            "capability": "machine_safety_gates",
            "description": "Machine gates can replace human review for deterministic local checks when every profile requirement passes.",
        },
        {
            "capability": "safe_queue_auto_completion",
            "description": "Low-risk queue items can be completed automatically from passing evidence and queue mutation gates.",
        },
        {
            "capability": "docs_only_autonomous_apply",
            "description": "Markdown-only documentation patches can be applied without human review when docs-only gates and transaction logging pass.",
        },
        {
            "capability": "low_risk_agent_real_execution",
            "description": "Deterministic local agents can write execution records/artifacts without model, network, GitHub, or source mutation.",
        },
        {
            "capability": "stepwise_multi_agent_orchestration",
            "description": "Orchestration can execute safe steps with per-step gates, dry-run defaults, high-risk allow flags, and fail-fast behavior.",
        },
    ]


def _remaining_human_gates() -> list[str]:
    return [
        "Codex execution still requires explicit --execution-enabled and later validation before completion.",
        "Local LLM execution remains advisory-only and requires explicit local provider support and gates.",
        "GitHub live sync requires explicit --github-enabled and narrow issue/PR sync mode.",
        "PR merge, force push, protected branch updates, releases, workflow changes, and automatic issue closure remain blocked.",
        "Source-code patch application and high-risk multi-file mutations still require human-reviewed implementation paths.",
        "Production daemon/scheduler/background autonomy, rollback automation, and Hub control-center execution remain future work.",
    ]


def _next_sprint_recommendations() -> list[str]:
    return [
        "Harden the M138 orchestrator for resume, rollback, retry policy, and clearer partial-run recovery.",
        "Improve real Codex loop reliability across M135/M136 with stronger result schemas, clean-tree strategy, and validation profile selection.",
        "Compare local LLM model quality for advisory and coding-review tasks while preserving advisory-only apply boundaries.",
        "Expand GitHub PR automation carefully beyond comments/metadata only after dedicated gates and rollback plans exist.",
        "Build a Hub agent control center for inspecting gates, plans, artifacts, timelines, and next safe actions.",
        "Add rollback/recovery models for queue mutation, docs-only apply, Codex dispatch failure, and orchestrator interruption.",
        "Add agent metrics and telemetry for gate failures, execution duration, artifact quality, and validation outcomes.",
        "Start self-managed project issue automation only after issue lifecycle gates, audit logs, and operator recovery views are production-hardened.",
    ]


def _warnings(
    *,
    docs_status: dict[str, Any],
    missing_milestones: list[str],
    docs_apply_blockers: list[str],
) -> list[str]:
    warnings: list[str] = []
    warnings.extend(f"Queue item missing for {milestone}." for milestone in missing_milestones)
    warnings.extend(f"Missing source-of-truth doc: {path}." for path in docs_status.get("missing_docs", []))
    missing_mentions = docs_status.get("missing_milestone_mentions", {})
    if isinstance(missing_mentions, dict) and missing_mentions:
        warnings.append("One or more source-of-truth docs are missing sprint milestone mentions.")
    warnings.extend(docs_apply_blockers)
    return sorted(set(warnings))


def _blockers(project_id: str, docs_apply_blockers: list[str]) -> list[str]:
    blockers: list[str] = []
    if not project_id:
        blockers.append("project_id is required.")
    blockers.extend(docs_apply_blockers)
    return sorted(set(blockers))


def _missing_milestones(items: list[dict[str, Any]], sprint_start: str, sprint_end: str) -> list[str]:
    found = {item["milestone"] for item in items}
    return [milestone for milestone in _milestones(sprint_start, sprint_end) if milestone not in found]


def _next_safe_action(blockers: list[str], docs_status: dict[str, Any]) -> str:
    if blockers:
        return "Resolve blockers before applying docs-only updates or using the closeout for automated follow-on decisions."
    if not docs_status.get("consistent"):
        return "Review docs consistency warnings, update source-of-truth docs, then rerun the closeout dry-run."
    return "Use this closeout artifact as the sprint handoff, then plan the next hardening sprint without starting it automatically."


def _emit_or_write(
    *,
    config: AppConfig,
    payload: dict[str, Any],
    output: str | Path | None,
    force: bool,
) -> dict[str, Any]:
    output_path = _resolve(config.repo_root, output) if output else _default_output_path(config, payload)
    rendered = json.dumps(payload, indent=2)
    if output_path.exists() and not force:
        blocked = dict(payload)
        blocked["blockers"] = [*_list(blocked.get("blockers")), "Output file already exists. Re-run with --force to overwrite."]
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
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered + "\n", encoding="utf-8")
    payload_with_artifact = dict(payload)
    payload_with_artifact["closeout_artifact_path"] = str(output_path)
    rendered = json.dumps(payload_with_artifact, indent=2)
    output_path.write_text(rendered + "\n", encoding="utf-8")
    return {
        "command": COMMAND_NAME,
        "ok": not bool(payload_with_artifact.get("blockers")),
        "local_only": True,
        "format": "json",
        "output": str(output_path),
        "force": force,
        "wrote_output_file": True,
        "stdout": rendered,
        "payload": payload_with_artifact,
    }


def _default_output_path(config: AppConfig, payload: dict[str, Any]) -> Path:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    project_id = _safe_id(str(payload.get("project_id", "") or "project"))
    return (config.artifact_root / "autonomous-sprint-closeout" / project_id / f"{stamp}.json").resolve()


def _resolve(repo_root: Path, value: str | Path | None) -> Path:
    path = Path(str(value or ""))
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


def _normalize_milestone(value: str | None) -> str:
    text = str(value or "").strip().upper()
    if text.startswith("M") and text[1:].isdigit():
        return f"M{int(text[1:])}"
    if text.isdigit():
        return f"M{int(text)}"
    return ""


def _milestone_number(value: str) -> int:
    normalized = _normalize_milestone(value)
    return int(normalized[1:]) if normalized else 0


def _milestones(start: str, end: str) -> list[str]:
    start_number = _milestone_number(start)
    end_number = _milestone_number(end)
    if start_number <= 0 or end_number <= 0 or end_number < start_number:
        return []
    return [f"M{number}" for number in range(start_number, end_number + 1)]


def _safe_id(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in value.lower())
    return cleaned.strip("-") or "autonomous-sprint-closeout"


def _list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(entry).strip() for entry in value if str(entry).strip()]
    if isinstance(value, tuple):
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
