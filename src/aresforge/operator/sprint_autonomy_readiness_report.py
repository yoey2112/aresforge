from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.agent_registry import build_agent_registry
from aresforge.operator.llm_decision_policy import recommend_llm_decision
from aresforge.operator.local_project_queue import resolve_project_queue_path
from aresforge.operator.machine_safety_gate_engine import evaluate_machine_safety_gates
from aresforge.operator.orchestration_run_monitor import inspect_orchestration_run_monitor

COMMAND_NAME = "generate-autonomy-readiness-report"
RECORD_TYPE = "autonomy_readiness_report_v1"
REPORT_VERSION = "m154.1"
DEFAULT_ITEM_ID = "m154-sprint-closeout-and-autonomy-readiness-report"
DEFAULT_PROJECT_ID = "aresforge"

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
        "milestone": "M140",
        "title": "Orchestrator Execution State Machine v1",
        "summary": "Defines durable orchestration states, transitions, checkpoints, validation boundaries, and machine-gated execution entry points.",
    },
    {
        "milestone": "M141",
        "title": "Orchestration Run History and Recovery",
        "summary": "Persists local orchestration run history and reports advisory recovery records without retrying or resuming work.",
    },
    {
        "milestone": "M142",
        "title": "Real Codex Execution Enablement Profile",
        "summary": "Documents default-deny Codex execution profiles and the explicit flags and gates required before any real dispatch.",
    },
    {
        "milestone": "M143",
        "title": "Codex Execution Sandbox and Worktree Guard",
        "summary": "Adds read-only guard evidence for dirty worktrees, sandbox limits, and bounded Codex output capture.",
    },
    {
        "milestone": "M144",
        "title": "Codex Validation Profile Expansion",
        "summary": "Maps task type, risk, and changed paths to allowlisted validation profiles without running validation commands.",
    },
    {
        "milestone": "M145",
        "title": "Codex Failure Classification and Retry Policy",
        "summary": "Classifies local Codex failures and reports deterministic stop/manual-retry guidance while automatic retry loops remain blocked.",
    },
    {
        "milestone": "M146",
        "title": "Agent Step Result Normalization",
        "summary": "Normalizes heterogeneous agent step results into stable status, blocker, gate, artifact, and execution-flag evidence.",
    },
    {
        "milestone": "M147",
        "title": "Orchestrator Resume-from-Failure",
        "summary": "Builds checkpoint-based resume plans as advisory evidence for future explicit machine-gated resume commands.",
    },
    {
        "milestone": "M148",
        "title": "Safe Source Patch Detection and Risk Classifier",
        "summary": "Classifies source patch risk, touched paths, mutation types, and blocked automatic-apply operations without applying patches.",
    },
    {
        "milestone": "M149",
        "title": "Controlled Source Patch Apply Plan",
        "summary": "Converts patch classification into a future controlled-apply plan with hard blockers, validation, and rollback guidance.",
    },
    {
        "milestone": "M150",
        "title": "Machine-Gated Source Patch Apply Dry Run",
        "summary": "Runs only git apply --check after planning and source-patch dry-run gates pass, proving applicability without mutation.",
    },
    {
        "milestone": "M151",
        "title": "End-to-End Codex Loop Dry Run",
        "summary": "Routes a queue item through dry-run Codex dispatch, ingestion, validation-profile selection, and completion recommendation.",
    },
    {
        "milestone": "M152",
        "title": "End-to-End Codex Loop Real Run for Low-Risk Code",
        "summary": "Enables real Codex dispatch only for explicitly allowed low-risk code paths with M135 dispatch and M136 validation evidence.",
    },
    {
        "milestone": "M153",
        "title": "Hub Orchestration Run Monitor",
        "summary": "Exposes local orchestration run state, history, recovery, gates, artifacts, and next safe action through CLI and Hub API.",
    },
    {
        "milestone": "M154",
        "title": "Sprint Closeout and Autonomy Readiness Report",
        "summary": "Synchronizes source-of-truth closeout context and emits this local autonomy readiness report for the M140-M154 sprint.",
    },
)

_BOUNDARY_CONFIRMATIONS: tuple[str, ...] = (
    "M154 is a local-first readiness report and source-of-truth closeout checkpoint.",
    "M154 performs no agent, Codex, local LLM/model, GitHub, validation command, source patch, PR merge, force push, protected-branch, workflow, release, retry, resume, or automatic next-item execution.",
    "M154 may optionally write one local JSON report artifact when --output is supplied.",
    "Real Codex execution remains default-deny and limited to separate explicit machine-gated commands.",
)


def generate_autonomy_readiness_report(
    config: AppConfig,
    *,
    project_id: str = DEFAULT_PROJECT_ID,
    sprint_start: str = "M140",
    sprint_end: str = "M154",
    item_id: str = DEFAULT_ITEM_ID,
    queue_path: str | Path | None = None,
    output: str | Path | None = None,
    force: bool = False,
    output_format: str = "json",
) -> dict[str, Any]:
    fmt = str(output_format or "json").strip().lower()
    if fmt != "json":
        return _error("invalid_format", {"format": output_format, "supported_formats": ["json"]})

    normalized_project_id = str(project_id or DEFAULT_PROJECT_ID).strip() or DEFAULT_PROJECT_ID
    normalized_start = _normalize_milestone(sprint_start) or "M140"
    normalized_end = _normalize_milestone(sprint_end) or "M154"
    normalized_item_id = str(item_id or DEFAULT_ITEM_ID).strip() or DEFAULT_ITEM_ID
    run_id = f"{_safe_id(normalized_project_id)}-{normalized_start.lower()}-{normalized_end.lower()}-autonomy-readiness"

    queue = _load_queue(config, queue_path)
    items = _milestone_items(queue, normalized_project_id, normalized_start, normalized_end)
    docs_status = _inspect_docs(config.repo_root, normalized_start, normalized_end)
    gate_payload = _read_only_gate(config, normalized_item_id, queue_path)
    llm_payload = _llm_policy(config, normalized_item_id, queue_path)
    monitor_payload = _monitor(config, normalized_project_id, queue_path)
    registry = build_agent_registry(config)

    missing_milestones = _missing_milestones(items, normalized_start, normalized_end)
    incomplete_items = [item for item in items if item["status"] not in {"done", "cancelled"}]
    blocked_items = [item for item in items if item["status"] == "blocked" or item.get("blocked_by")]
    machine_gates = [_gate_summary(gate_payload)]
    blocked_reasons = _blocked_reasons(
        project_id=normalized_project_id,
        gate_payload=gate_payload,
        missing_milestones=missing_milestones,
        incomplete_items=incomplete_items,
        blocked_items=blocked_items,
    )
    warnings = _warnings(
        queue=queue,
        docs_status=docs_status,
        gate_payload=gate_payload,
        monitor_payload=monitor_payload,
    )
    status = _status(blocked_reasons, warnings, docs_status)

    payload: dict[str, Any] = {
        "record_type": RECORD_TYPE,
        "artifact_type": RECORD_TYPE,
        "report_version": REPORT_VERSION,
        "generated": True,
        "generated_at": _now_iso(),
        "item_id": normalized_item_id,
        "project_id": normalized_project_id,
        "run_id": run_id,
        "status": status,
        "blocked": bool(blocked_reasons),
        "blocked_reasons": blocked_reasons,
        "warnings": warnings,
        "machine_gates_checked": machine_gates,
        "machine_gates_passed": bool(machine_gates) and all(bool(gate.get("passed")) for gate in machine_gates),
        "artifacts_created": [],
        "mutation_performed": False,
        "external_execution_performed": False,
        "model_execution_performed": False,
        "codex_execution_performed": False,
        "github_execution_performed": False,
        "patch_application_performed": False,
        "validation_command_execution_performed": False,
        "queue_mutation_performed": False,
        "local_only": True,
        "next_safe_action": _next_safe_action(blocked_reasons, docs_status),
        "sprint_start": normalized_start,
        "sprint_end": normalized_end,
        "milestones_reviewed": _milestones(normalized_start, normalized_end),
        "sprint_closeout_summary": _sprint_closeout_summary(items, normalized_start, normalized_end),
        "capability_summary": _capability_summary(normalized_start, normalized_end),
        "readiness_summary": _readiness_summary(
            registry=registry,
            gate_payload=gate_payload,
            llm_payload=llm_payload,
            monitor_payload=monitor_payload,
        ),
        "queue_summary": _queue_summary(items, missing_milestones),
        "docs_sync": docs_status,
        "artifact_summary": _inspect_artifacts(config),
        "remaining_blockers": _remaining_blockers(),
        "next_sprint_recommendations": _next_sprint_recommendations(),
        "machine_gate_behavior": _machine_gate_behavior(gate_payload),
        "execution_boundary": {
            "real_codex_default_deny": True,
            "local_llm_advisory_only": True,
            "github_live_mutation_default_deny": True,
            "source_patch_application_default_deny": True,
            "automatic_next_item_execution_default_deny": True,
            "report_execution_performed": False,
        },
        "llm_decision_policy_summary": _llm_summary(llm_payload),
        "orchestration_monitor_summary": _monitor_summary(monitor_payload),
        "agent_registry_summary": _agent_registry_summary(registry),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
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


def _milestone_items(queue: dict[str, Any], project_id: str, sprint_start: str, sprint_end: str) -> list[dict[str, Any]]:
    milestones = set(_milestones(sprint_start, sprint_end))
    items: list[dict[str, Any]] = []
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
        "docs_mutation_performed": False,
    }


def _read_only_gate(config: AppConfig, item_id: str, queue_path: str | Path | None) -> dict[str, Any]:
    result = evaluate_machine_safety_gates(
        config,
        item_id=item_id,
        gate_profile="read_only_agent",
        queue_path=queue_path,
        output_format="json",
    )
    payload = result.get("payload", {}) if isinstance(result, dict) else {}
    return payload if isinstance(payload, dict) else {}


def _llm_policy(config: AppConfig, item_id: str, queue_path: str | Path | None) -> dict[str, Any]:
    result = recommend_llm_decision(
        config,
        item_id=item_id,
        task_type="documentation",
        risk_level="low",
        mutation_scope="read_only",
        queue_path=queue_path,
        output_format="json",
    )
    payload = result.get("payload", {}) if isinstance(result, dict) else {}
    return payload if isinstance(payload, dict) else {}


def _monitor(config: AppConfig, project_id: str, queue_path: str | Path | None) -> dict[str, Any]:
    result = inspect_orchestration_run_monitor(
        config,
        project_id=project_id,
        queue_path=queue_path,
        output_format="json",
    )
    payload = result.get("payload", {}) if isinstance(result, dict) else {}
    return payload if isinstance(payload, dict) else {}


def _gate_summary(gate_payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": "m154_read_only_closeout_gate",
        "gate_profile": _text(gate_payload.get("gate_profile")) or "read_only_agent",
        "passed": bool(gate_payload.get("passed")) and not bool(gate_payload.get("blocked")),
        "blocked": bool(gate_payload.get("blocked")),
        "blocked_reasons": _list(gate_payload.get("blocked_reasons")),
        "warnings": _list(gate_payload.get("warnings")),
        "check_count": len([check for check in gate_payload.get("checks", []) if isinstance(check, dict)]),
    }


def _blocked_reasons(
    *,
    project_id: str,
    gate_payload: dict[str, Any],
    missing_milestones: list[str],
    incomplete_items: list[dict[str, Any]],
    blocked_items: list[dict[str, Any]],
) -> list[str]:
    reasons: list[str] = []
    if not project_id:
        reasons.append("project_id is required.")
    reasons.extend(_list(gate_payload.get("blocked_reasons")))
    reasons.extend(f"Queue item missing for {milestone}." for milestone in missing_milestones)
    reasons.extend(f"Queue item not complete: {item['item_id']}." for item in incomplete_items)
    reasons.extend(f"Queue item blocked: {item['item_id']}." for item in blocked_items)
    return sorted(set(reasons))


def _warnings(
    *,
    queue: dict[str, Any],
    docs_status: dict[str, Any],
    gate_payload: dict[str, Any],
    monitor_payload: dict[str, Any],
) -> list[str]:
    warnings: list[str] = []
    warnings.extend(_list(queue.get("warnings")))
    warnings.extend(_list(gate_payload.get("warnings")))
    warnings.extend(_list(monitor_payload.get("warnings")))
    warnings.extend(f"Missing source-of-truth doc: {path}." for path in docs_status.get("missing_docs", []))
    if docs_status.get("missing_milestone_mentions"):
        warnings.append("One or more source-of-truth docs are missing sprint milestone mentions.")
    return sorted(set(warnings))


def _status(blocked_reasons: list[str], warnings: list[str], docs_status: dict[str, Any]) -> str:
    if blocked_reasons:
        return "blocked"
    if not docs_status.get("consistent"):
        return "docs_sync_required"
    if warnings:
        return "ready_with_warnings"
    return "ready"


def _sprint_closeout_summary(items: list[dict[str, Any]], sprint_start: str, sprint_end: str) -> dict[str, Any]:
    completed = [item for item in items if item["status"] == "done"]
    return {
        "title": "M140-M154 orchestrator hardening and real Codex loop sprint closeout",
        "scope": "Route, execute, validate, recover, monitor, and report on low-risk work while preserving machine-gated safety.",
        "milestone_count_expected": len(_milestones(sprint_start, sprint_end)),
        "milestone_item_count": len(items),
        "completed_item_count": len(completed),
        "all_milestone_items_complete": len(items) == len(_milestones(sprint_start, sprint_end)) and len(completed) == len(items),
    }


def _capability_summary(sprint_start: str, sprint_end: str) -> list[dict[str, str]]:
    milestones = set(_milestones(sprint_start, sprint_end))
    return [dict(summary) for summary in MILESTONE_SUMMARIES if summary["milestone"] in milestones]


def _readiness_summary(
    *,
    registry: dict[str, Any],
    gate_payload: dict[str, Any],
    llm_payload: dict[str, Any],
    monitor_payload: dict[str, Any],
) -> dict[str, Any]:
    return {
        "orchestrator_state_ready": True,
        "run_history_recovery_ready": True,
        "real_codex_low_risk_loop_ready": True,
        "source_patch_apply_ready": "dry_run_only",
        "hub_monitor_ready": bool(monitor_payload),
        "agent_registry_available": bool(registry.get("agent_count")),
        "machine_gate_available": bool(gate_payload),
        "llm_policy_available": bool(llm_payload),
        "autonomy_ready_for": [
            "read-only reporting",
            "dry-run orchestration",
            "low-risk local-agent execution",
            "docs-only gated apply",
            "local LLM advisory evidence",
            "explicit low-risk Codex dispatch with validation",
        ],
        "autonomy_not_ready_for": _remaining_blockers(),
    }


def _queue_summary(items: list[dict[str, Any]], missing_milestones: list[str]) -> dict[str, Any]:
    statuses: dict[str, int] = {}
    for item in items:
        statuses[item["status"]] = statuses.get(item["status"], 0) + 1
    return {
        "items": items,
        "status_counts": statuses,
        "missing_milestones": missing_milestones,
    }


def _inspect_artifacts(config: AppConfig) -> dict[str, Any]:
    roots = (
        ".aresforge/orchestrator",
        ".aresforge/codex_dispatch",
        ".aresforge/codex_loop_dry_runs",
        ".aresforge/codex_loop_real_runs",
        ".aresforge/source_patch_apply_dry_runs",
        "artifacts/codex_result_ingestion",
        "artifacts/multi-agent-orchestration",
    )
    counts: dict[str, int] = {}
    latest: dict[str, str] = {}
    for root in roots:
        path = config.repo_root / root
        files = sorted(candidate for candidate in path.rglob("*") if candidate.is_file()) if path.exists() else []
        counts[root] = len(files)
        latest[root] = _repo_relative(config.repo_root, max(files, key=lambda candidate: candidate.stat().st_mtime)) if files else ""
    return {"inspected_roots": list(roots), "file_counts": counts, "latest_artifacts": latest}


def _remaining_blockers() -> list[str]:
    return [
        "Real Codex execution remains default-deny and requires explicit machine-gated low-risk scope.",
        "Source-code patch application is still limited to classification, planning, and dry-run applicability evidence.",
        "Automatic retry/resume loops remain blocked; recovery and resume are advisory until a separate gated command runs.",
        "GitHub execution remains narrow and gated; PR merge, force push, protected branch updates, auto-merge, releases, and workflow mutation remain prohibited.",
        "Local LLM output remains advisory evidence and is not automatically applied.",
        "Background daemon/scheduler autonomy and automatic next-item execution remain out of scope.",
    ]


def _next_sprint_recommendations() -> list[str]:
    return [
        "Implement explicit orchestrator resume execution with checkpoint validation, operator flags, and rollback evidence.",
        "Add a controlled low-risk source patch apply path with clean-apply proof, validation profiles, and transaction logging.",
        "Promote the Hub run monitor into an operator control center with gate drilldowns and recovery workflows.",
        "Harden Codex result ingestion for real low-risk code with richer diff, validation, and completion evidence.",
        "Add repeatable telemetry for gate failures, recovery outcomes, Codex dispatch duration, and validation results.",
        "Design GitHub sync expansion only after audit logs, rollback plans, and protected-operation deny rules are complete.",
    ]


def _machine_gate_behavior(gate_payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "gate_profile": _text(gate_payload.get("gate_profile")) or "read_only_agent",
        "passed": bool(gate_payload.get("passed")) and not bool(gate_payload.get("blocked")),
        "autonomy_allowed_for_report": bool(gate_payload.get("autonomy_allowed")) and not bool(gate_payload.get("blocked")),
        "human_review_required": bool(gate_payload.get("human_review_required")),
        "report_performed_gate_bypass": False,
        "gate_evaluation_execution_performed": bool(gate_payload.get("execution_performed")),
        "gate_evaluation_mutation_performed": bool(gate_payload.get("mutation_performed")),
        "next_safe_action": _text(gate_payload.get("next_safe_action")),
    }


def _llm_summary(llm_payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "recommendation_type": _text(llm_payload.get("recommendation_type")),
        "recommended_lane": _text(llm_payload.get("recommended_lane")),
        "recommended_provider": _text(llm_payload.get("recommended_provider")),
        "machine_gate_required": bool(llm_payload.get("machine_gate_required")),
        "execution_performed": bool(llm_payload.get("execution_performed")),
        "local_only": bool(llm_payload.get("local_only")),
    }


def _monitor_summary(monitor_payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "record_type": _text(monitor_payload.get("record_type")),
        "status": _text(monitor_payload.get("status")),
        "blocked": bool(monitor_payload.get("blocked")),
        "machine_gates_passed": bool(monitor_payload.get("machine_gates_passed")),
        "next_safe_action": _text(monitor_payload.get("next_safe_action")),
    }


def _agent_registry_summary(registry: dict[str, Any]) -> dict[str, Any]:
    return {
        "agent_count": registry.get("agent_count", 0),
        "executable_agents": registry.get("executable_agents", []),
        "dry_run_only_agents": registry.get("dry_run_only_agents", []),
    }


def _next_safe_action(blocked_reasons: list[str], docs_status: dict[str, Any]) -> str:
    if blocked_reasons:
        return "Resolve blockers, then rerun the autonomy readiness report before planning the next sprint."
    if not docs_status.get("consistent"):
        return "Update source-of-truth docs for the M140-M154 sprint, then rerun the report."
    return "Use this report as M154 closeout evidence and plan the next sprint without starting follow-on execution automatically."


def _emit_or_write(
    *,
    config: AppConfig,
    payload: dict[str, Any],
    output: str | Path | None,
    force: bool,
) -> dict[str, Any]:
    if output is None:
        return {
            "command": COMMAND_NAME,
            "ok": not bool(payload.get("blocked")),
            "local_only": True,
            "format": "json",
            "wrote_output_file": False,
            "stdout": json.dumps(payload, indent=2),
            "payload": payload,
        }
    output_path = _resolve(config.repo_root, output)
    if output_path.exists() and not force:
        blocked = dict(payload)
        blocked["status"] = "blocked"
        blocked["blocked"] = True
        blocked["blocked_reasons"] = sorted(
            set([*_list(blocked.get("blocked_reasons")), "Output file already exists. Re-run with --force to overwrite."])
        )
        return {
            "command": COMMAND_NAME,
            "ok": False,
            "local_only": True,
            "format": "json",
            "output": str(output_path),
            "force": force,
            "wrote_output_file": False,
            "stdout": json.dumps(blocked, indent=2),
            "payload": blocked,
        }
    artifact_payload = dict(payload)
    artifact_payload["artifacts_created"] = sorted(set([*_list(payload.get("artifacts_created")), str(output_path)]))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact_payload, indent=2) + "\n", encoding="utf-8")
    return {
        "command": COMMAND_NAME,
        "ok": not bool(artifact_payload.get("blocked")),
        "local_only": True,
        "format": "json",
        "output": str(output_path),
        "force": force,
        "wrote_output_file": True,
        "payload": artifact_payload,
    }


def _missing_milestones(items: list[dict[str, Any]], sprint_start: str, sprint_end: str) -> list[str]:
    found = {item["milestone"] for item in items}
    return [milestone for milestone in _milestones(sprint_start, sprint_end) if milestone not in found]


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


def _resolve(repo_root: Path, value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


def _repo_relative(repo_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _safe_id(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in value.lower())
    return cleaned.strip("-") or "autonomy-readiness"


def _text(value: Any) -> str:
    return str(value or "").strip()


def _list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [_text(entry) for entry in value if _text(entry)]
    if isinstance(value, tuple):
        return [_text(entry) for entry in value if _text(entry)]
    if value in (None, ""):
        return []
    return [_text(value)]


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
