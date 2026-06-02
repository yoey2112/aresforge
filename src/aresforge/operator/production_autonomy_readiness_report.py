from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.durable_orchestration_run_store import read_orchestration_run_store
from aresforge.operator.github_issue_sync_plan import plan_github_issue_sync
from aresforge.operator.hub_autonomy_control_center import inspect_hub_autonomy_control_center_data
from aresforge.operator.local_project_queue import resolve_project_queue_path
from aresforge.operator.machine_safety_gate_engine import evaluate_machine_safety_gates
from aresforge.operator.operator_autonomy_configuration_profile import inspect_autonomy_profile
from aresforge.operator.orchestration_artifact_retention_policy import inspect_orchestration_artifact_retention
from aresforge.operator.orchestration_run_monitor import inspect_orchestration_run_monitor

COMMAND_NAME = "generate-production-autonomy-readiness-report"
RECORD_TYPE = "production_autonomy_readiness_report_v1"
REPORT_VERSION = "m169.1"
DEFAULT_ITEM_ID = "m169-sprint-closeout-and-production-autonomy-readiness-report"
DEFAULT_PROJECT_ID = "aresforge"
DEFAULT_AUTONOMY_PROFILE = "github_sync_dry_run"

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
        "milestone": "M155",
        "title": "Durable Orchestration Run Store",
        "summary": "Adds the durable local run-history store that future orchestration recovery and audit paths can inspect.",
    },
    {
        "milestone": "M156",
        "title": "Orchestration Artifact Retention Policy",
        "summary": "Indexes local orchestration, Codex, validation, documentation, and autonomy artifacts with dry-run cleanup guidance.",
    },
    {
        "milestone": "M157",
        "title": "Run Replay and Audit Trail",
        "summary": "Reconstructs prior run metadata, gates, artifacts, and decisions from local durable evidence without execution.",
    },
    {
        "milestone": "M158",
        "title": "Operator Autonomy Configuration Profile",
        "summary": "Defines safe-deny autonomy profiles and capability controls for read-only, dry-run, GitHub-sync, Codex, and local-only paths.",
    },
    {
        "milestone": "M159",
        "title": "Real Codex Execution Preflight Hardening",
        "summary": "Reports future real-Codex readiness from worktree, gate, artifact, run-store, retry, and source-patch policy evidence.",
    },
    {
        "milestone": "M160",
        "title": "Low-Risk Codex Execution Pilot Item",
        "summary": "Coordinates a dry-run-default, explicitly gated low-risk Codex pilot boundary.",
    },
    {
        "milestone": "M161",
        "title": "Codex Loop Validation Evidence Bundle",
        "summary": "Bundles Codex loop validation evidence, gate status, artifacts, risk classifications, and completion recommendation.",
    },
    {
        "milestone": "M162",
        "title": "GitHub Issue Sync Plan from Queue Items",
        "summary": "Maps local queue records to future GitHub issue create/update/comment recommendations without calling GitHub.",
    },
    {
        "milestone": "M163",
        "title": "GitHub Issue Creation for Safe Queue Items",
        "summary": "Adds a dry-run-default, one-item issue creation gate with explicit future live-sync requirements.",
    },
    {
        "milestone": "M164",
        "title": "GitHub Issue Status Comment Sync",
        "summary": "Adds dry-run-default status comment composition and a narrow future machine-gated live comment path.",
    },
    {
        "milestone": "M165",
        "title": "GitHub Issue Closure Recommendation Gate",
        "summary": "Recommends issue closure from local evidence only while issue closure remains disabled.",
    },
    {
        "milestone": "M166",
        "title": "Pull Request Draft Summary Generator",
        "summary": "Generates local PR summary artifacts without PR creation, update, merge, or GitHub mutation.",
    },
    {
        "milestone": "M167",
        "title": "Hub Autonomy Control Center v1",
        "summary": "Surfaces autonomy profile, run-store, evidence, GitHub sync, PR draft, gate, and next-action status in CLI/API/UI.",
    },
    {
        "milestone": "M168",
        "title": "Self-Managed AresForge Project Loop Dry Run",
        "summary": "Dry-runs the self-managed queue-to-evidence-to-GitHub-plan-to-PR-summary loop and records local run-store evidence.",
    },
    {
        "milestone": "M169",
        "title": "Sprint Closeout and Production Autonomy Readiness Report",
        "summary": "Closes M155-M169 with production autonomy readiness evidence, blockers, warnings, and next-sprint recommendations.",
    },
)

_BOUNDARY_CONFIRMATIONS: tuple[str, ...] = (
    "M169 is a local production-autonomy readiness report and source-of-truth closeout checkpoint.",
    "M169 performs no live Codex, model, GitHub, source patch, validation command, queue mutation, retry, resume, PR merge, protected-branch update, force push, auto-merge, release, workflow mutation, or automatic next-item execution.",
    "M169 may optionally write one local JSON report artifact when --output is supplied.",
    "Production autonomy remains gated: live GitHub mutation, source-code patch application, automatic retry/resume, and automatic next-item execution require separate future milestones.",
)


def generate_production_autonomy_readiness_report(
    config: AppConfig,
    *,
    project_id: str = DEFAULT_PROJECT_ID,
    sprint_start: str = "M155",
    sprint_end: str = "M169",
    item_id: str = DEFAULT_ITEM_ID,
    queue_path: str | Path | None = None,
    history_path: str | Path | None = None,
    artifacts_root: str | Path | None = None,
    autonomy_profile: str = DEFAULT_AUTONOMY_PROFILE,
    output: str | Path | None = None,
    force: bool = False,
    output_format: str = "json",
) -> dict[str, Any]:
    fmt = _text(output_format).lower() or "json"
    if fmt != "json":
        return _error("invalid_format", {"format": output_format, "supported_formats": ["json"]})

    normalized_project_id = _text(project_id) or DEFAULT_PROJECT_ID
    normalized_start = _normalize_milestone(sprint_start) or "M155"
    normalized_end = _normalize_milestone(sprint_end) or "M169"
    normalized_item_id = _text(item_id) or DEFAULT_ITEM_ID
    selected_profile = _text(autonomy_profile) or DEFAULT_AUTONOMY_PROFILE
    run_id = f"{_safe_id(normalized_project_id)}-{normalized_start.lower()}-{normalized_end.lower()}-production-autonomy-readiness"

    queue = _load_queue(config, queue_path)
    items = _milestone_items(queue, normalized_project_id, normalized_start, normalized_end)
    docs_status = _inspect_docs(config.repo_root, normalized_start, normalized_end)
    read_only_gate = _gate_summary(
        _gate_payload(config, item_id=normalized_item_id, gate_profile="read_only_agent", queue_path=queue_path),
        source="m169_read_only_closeout_gate",
    )
    profile_gate = _gate_summary(
        _gate_payload(
            config,
            item_id=normalized_item_id,
            gate_profile="operator_autonomy_profile",
            queue_path=queue_path,
        ),
        source="m169_operator_autonomy_profile_gate",
    )
    machine_gates = [read_only_gate, profile_gate]
    run_store = read_orchestration_run_store(
        config,
        store_path=history_path,
        bootstrap_missing=False,
        project_id=normalized_project_id,
    )
    retention_payload = _payload(
        inspect_orchestration_artifact_retention(
            config,
            project_id=normalized_project_id,
            item_id=normalized_item_id,
            history_path=history_path,
            queue_path=queue_path,
            output_format="json",
        )
    )
    autonomy_payload = _payload(
        inspect_autonomy_profile(
            config,
            project_id=normalized_project_id,
            item_id=normalized_item_id,
            autonomy_profile=selected_profile,
            queue_path=queue_path,
            output_format="json",
        )
    )
    issue_sync_payload = _payload(
        plan_github_issue_sync(
            config,
            project_id=normalized_project_id,
            queue_path=queue_path,
            output_format="json",
        )
    )
    monitor_payload = _payload(
        inspect_orchestration_run_monitor(
            config,
            project_id=normalized_project_id,
            item_id=normalized_item_id,
            history_path=history_path,
            artifacts_root=artifacts_root,
            queue_path=queue_path,
            output_format="json",
        )
    )
    hub_payload = _payload(
        inspect_hub_autonomy_control_center_data(
            config,
            project_id=normalized_project_id,
            item_id="m167-hub-autonomy-control-center-v1",
            queue_path=queue_path,
            history_path=history_path,
            artifacts_root=artifacts_root,
            autonomy_profile=selected_profile,
            output_format="json",
        )
    )

    missing_milestones = _missing_milestones(items, normalized_start, normalized_end)
    incomplete_items = [item for item in items if item["status"] not in {"done", "cancelled"}]
    blocked_items = [item for item in items if item["status"] == "blocked" or item.get("blocked_by")]
    blocked_reasons = _blocked_reasons(
        project_id=normalized_project_id,
        gates=machine_gates,
        missing_milestones=missing_milestones,
        incomplete_items=incomplete_items,
        blocked_items=blocked_items,
        run_store=run_store,
    )
    warnings = _warnings(
        queue=queue,
        docs_status=docs_status,
        gates=machine_gates,
        run_store=run_store,
        retention_payload=retention_payload,
        autonomy_payload=autonomy_payload,
        issue_sync_payload=issue_sync_payload,
        monitor_payload=monitor_payload,
        hub_payload=hub_payload,
    )
    status = _status(blocked_reasons=blocked_reasons, warnings=warnings, docs_status=docs_status)
    payload: dict[str, Any] = {
        "record_type": RECORD_TYPE,
        "artifact_type": RECORD_TYPE,
        "report_version": REPORT_VERSION,
        "generated": True,
        "generated_at": _now_iso(),
        "project_id": normalized_project_id,
        "item_id": normalized_item_id,
        "run_id": run_id,
        "status": status,
        "blocked": bool(blocked_reasons),
        "blocked_reasons": blocked_reasons,
        "warnings": warnings,
        "machine_gates_checked": machine_gates,
        "machine_gates_passed": bool(machine_gates) and all(bool(gate.get("passed")) for gate in machine_gates) and not bool(blocked_reasons),
        "autonomy_profile": selected_profile,
        "artifacts_created": [],
        "mutation_performed": False,
        "queue_mutation_performed": False,
        "codex_execution_performed": False,
        "model_execution_performed": False,
        "github_execution_performed": False,
        "patch_application_performed": False,
        "validation_command_execution_performed": False,
        "local_only": True,
        "next_safe_action": _next_safe_action(blocked_reasons=blocked_reasons, docs_status=docs_status),
        "sprint_start": normalized_start,
        "sprint_end": normalized_end,
        "milestones_reviewed": _milestones(normalized_start, normalized_end),
        "sprint_closeout_summary": _sprint_closeout_summary(items, normalized_start, normalized_end),
        "capability_summary": _capability_summary(normalized_start, normalized_end),
        "queue_summary": _queue_summary(items, missing_milestones),
        "docs_sync": docs_status,
        "run_store_summary": _run_store_summary(run_store, normalized_project_id),
        "artifact_retention_summary": _retention_summary(retention_payload),
        "autonomy_profile_summary": _autonomy_summary(autonomy_payload),
        "codex_pilot_readiness": _codex_pilot_readiness(items),
        "github_issue_sync_status": _github_issue_sync_summary(issue_sync_payload),
        "hub_control_center_summary": _hub_summary(hub_payload),
        "self_managed_dry_run_summary": _self_managed_summary(config, run_store, normalized_project_id),
        "production_autonomy_readiness": _production_readiness_summary(
            run_store=run_store,
            retention_payload=retention_payload,
            autonomy_payload=autonomy_payload,
            issue_sync_payload=issue_sync_payload,
            monitor_payload=monitor_payload,
            hub_payload=hub_payload,
        ),
        "remaining_blockers": _remaining_blockers(),
        "next_sprint_recommendations": _next_sprint_recommendations(),
        "machine_gate_behavior": _machine_gate_behavior(machine_gates),
        "execution_boundary": {
            "live_codex_default_deny": True,
            "local_llm_advisory_only": True,
            "live_github_mutation_default_deny": True,
            "source_patch_application_default_deny": True,
            "automatic_retry_resume_default_deny": True,
            "automatic_next_item_execution_default_deny": True,
            "report_execution_performed": False,
        },
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }
    return _emit_or_write(config=config, payload=payload, output=output, force=force)


def _load_queue(config: AppConfig, queue_path: str | Path | None) -> dict[str, Any]:
    path = resolve_project_queue_path(config.repo_root, queue_path)
    if not path.exists():
        return {"work_items": [], "queue_path": str(path), "warnings": [f"Queue file missing: {path}"]}
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"work_items": [], "queue_path": str(path), "warnings": [f"Queue file could not be read: {exc}"]}
    if not isinstance(data, dict):
        return {"work_items": [], "queue_path": str(path), "warnings": ["Queue JSON root is not an object."]}
    data["queue_path"] = str(path)
    return data


def _milestone_items(queue: dict[str, Any], project_id: str, sprint_start: str, sprint_end: str) -> list[dict[str, Any]]:
    milestones = set(_milestones(sprint_start, sprint_end))
    items: list[dict[str, Any]] = []
    for item in _dicts(queue.get("work_items")):
        if project_id and _text(item.get("project_id")) != project_id:
            continue
        milestone = _item_milestone(item)
        if milestone not in milestones:
            continue
        items.append(
            {
                "milestone": milestone,
                "item_id": _text(item.get("item_id")),
                "title": _text(item.get("title")),
                "status": _text(item.get("status")),
                "completion_commit": _text(item.get("completion_commit")),
                "validation_summary": _text(item.get("validation_summary")),
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
    item_id = _text(item.get("item_id")).lower()
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


def _gate_payload(config: AppConfig, *, item_id: str, gate_profile: str, queue_path: str | Path | None) -> dict[str, Any]:
    result = evaluate_machine_safety_gates(
        config,
        item_id=item_id,
        gate_profile=gate_profile,
        queue_path=queue_path,
        output_format="json",
    )
    return _payload(result)


def _gate_summary(gate_payload: dict[str, Any], *, source: str) -> dict[str, Any]:
    checks = _dicts(gate_payload.get("checks"))
    return {
        "source": source,
        "gate_profile": _text(gate_payload.get("gate_profile") or gate_payload.get("profile")) or "read_only_agent",
        "passed": bool(gate_payload.get("passed")) and not bool(gate_payload.get("blocked")),
        "blocked": bool(gate_payload.get("blocked")),
        "blocked_reasons": _list(gate_payload.get("blocked_reasons")),
        "warnings": _list(gate_payload.get("warnings")),
        "check_count": len(checks),
        "checks_failed": [
            _text(check.get("check_id"))
            for check in checks
            if not bool(check.get("passed")) and not bool(check.get("warning_only"))
        ],
    }


def _blocked_reasons(
    *,
    project_id: str,
    gates: list[dict[str, Any]],
    missing_milestones: list[str],
    incomplete_items: list[dict[str, Any]],
    blocked_items: list[dict[str, Any]],
    run_store: dict[str, Any],
) -> list[str]:
    reasons: list[str] = []
    if not project_id:
        reasons.append("project_id is required.")
    reasons.extend(reason for gate in gates for reason in _list(gate.get("blocked_reasons")))
    reasons.extend(_list(run_store.get("errors")))
    reasons.extend(f"Queue item missing for {milestone}." for milestone in missing_milestones)
    reasons.extend(f"Queue item not complete: {item['item_id']}." for item in incomplete_items)
    reasons.extend(f"Queue item blocked: {item['item_id']}." for item in blocked_items)
    return _dedupe(sorted(reasons))


def _warnings(
    *,
    queue: dict[str, Any],
    docs_status: dict[str, Any],
    gates: list[dict[str, Any]],
    run_store: dict[str, Any],
    retention_payload: dict[str, Any],
    autonomy_payload: dict[str, Any],
    issue_sync_payload: dict[str, Any],
    monitor_payload: dict[str, Any],
    hub_payload: dict[str, Any],
) -> list[str]:
    warnings: list[str] = []
    warnings.extend(_list(queue.get("warnings")))
    warnings.extend(reason for gate in gates for reason in _list(gate.get("warnings")))
    warnings.extend(_list(run_store.get("warnings")))
    warnings.extend(_list(retention_payload.get("warnings")))
    warnings.extend(_list(autonomy_payload.get("warnings")))
    warnings.extend(_list(issue_sync_payload.get("warnings")))
    warnings.extend(_list(monitor_payload.get("warnings")))
    warnings.extend(_list(hub_payload.get("warnings")))
    warnings.extend(f"Missing source-of-truth doc: {path}." for path in docs_status.get("missing_docs", []))
    if docs_status.get("missing_milestone_mentions"):
        warnings.append("One or more source-of-truth docs are missing sprint milestone mentions.")
    return _dedupe(sorted(warnings))


def _status(*, blocked_reasons: list[str], warnings: list[str], docs_status: dict[str, Any]) -> str:
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
        "title": "M155-M169 production autonomy hardening and self-managed GitHub-loop sprint closeout",
        "scope": "Durable audit, retention, autonomy profiles, Codex pilot readiness, GitHub issue planning, Hub control center, and self-managed dry-run evidence.",
        "milestone_count_expected": len(_milestones(sprint_start, sprint_end)),
        "milestone_item_count": len(items),
        "completed_item_count": len(completed),
        "all_milestone_items_complete": len(items) == len(_milestones(sprint_start, sprint_end)) and len(completed) == len(items),
    }


def _capability_summary(sprint_start: str, sprint_end: str) -> list[dict[str, str]]:
    milestones = set(_milestones(sprint_start, sprint_end))
    return [dict(summary) for summary in MILESTONE_SUMMARIES if summary["milestone"] in milestones]


def _queue_summary(items: list[dict[str, Any]], missing_milestones: list[str]) -> dict[str, Any]:
    statuses: dict[str, int] = {}
    for item in items:
        statuses[item["status"]] = statuses.get(item["status"], 0) + 1
    return {
        "items": items,
        "status_counts": statuses,
        "missing_milestones": missing_milestones,
        "validation_evidence_item_count": sum(1 for item in items if item["validation_summary"] and item["tests_run"]),
    }


def _run_store_summary(run_store: dict[str, Any], project_id: str) -> dict[str, Any]:
    records = [record for record in _dicts(run_store.get("records")) if _text(record.get("project_id")) == project_id]
    return {
        "status": "ready" if run_store.get("ok") else "blocked",
        "store_path": _text(run_store.get("store_path")),
        "store_schema_valid": bool(run_store.get("schema_valid")),
        "store_record_count": len(_dicts(run_store.get("records"))),
        "project_run_count": len(records),
        "latest_run_id": _text(records[-1].get("run_id")) if records else "",
        "bootstrap_performed": bool(run_store.get("bootstrap_performed")),
        "mutation_performed": False,
    }


def _retention_summary(payload: dict[str, Any]) -> dict[str, Any]:
    counts = payload.get("artifact_count_summary", {}) if isinstance(payload.get("artifact_count_summary"), dict) else {}
    return {
        "record_type": _text(payload.get("record_type")),
        "status": _text(payload.get("status")),
        "blocked": bool(payload.get("blocked")),
        "machine_gates_passed": bool(payload.get("machine_gates_passed")),
        "total_artifact_count": counts.get("total_artifact_count", 0),
        "orphan_count": counts.get("orphan_count", 0),
        "stale_count": counts.get("stale_count", 0),
        "cleanup_performed": False,
        "dry_run_cleanup_plan_count": len(_dicts(payload.get("dry_run_cleanup_plan"))),
        "next_safe_action": _text(payload.get("next_safe_action")),
    }


def _autonomy_summary(payload: dict[str, Any]) -> dict[str, Any]:
    selected = payload.get("selected_profile", {}) if isinstance(payload.get("selected_profile"), dict) else {}
    return {
        "record_type": _text(payload.get("record_type")),
        "status": _text(payload.get("status")),
        "blocked": bool(payload.get("blocked")),
        "machine_gates_passed": bool(payload.get("machine_gates_passed")),
        "autonomy_profile": _text(payload.get("autonomy_profile")),
        "profile_display_name": _text(selected.get("display_name")),
        "risk_level": _text(selected.get("risk_level")),
        "capability_status_counts": selected.get("capability_status_counts", {}) if isinstance(selected.get("capability_status_counts"), dict) else {},
        "next_safe_action": _text(payload.get("next_safe_action")),
    }


def _codex_pilot_readiness(items: list[dict[str, Any]]) -> dict[str, Any]:
    by_milestone = {item["milestone"]: item for item in items}
    supporting = ["M159", "M160", "M161", "M168"]
    return {
        "status": "dry_run_ready" if all(by_milestone.get(milestone, {}).get("status") == "done" for milestone in supporting) else "evidence_incomplete",
        "supporting_milestones": supporting,
        "real_codex_allowed_by_report": False,
        "dry_run_boundary_ready": all(by_milestone.get(milestone, {}).get("status") == "done" for milestone in supporting),
        "low_risk_real_execution_requires_separate_command": True,
    }


def _github_issue_sync_summary(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "record_type": _text(payload.get("record_type")),
        "status": _text(payload.get("status")),
        "blocked": bool(payload.get("blocked")),
        "machine_gates_passed": bool(payload.get("machine_gates_passed")),
        "operation_counts": payload.get("operation_counts", {}) if isinstance(payload.get("operation_counts"), dict) else {},
        "github_execution_performed": False,
        "live_sync_allowed_by_report": False,
        "next_safe_action": _text(payload.get("next_safe_action")),
    }


def _hub_summary(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "record_type": _text(payload.get("record_type")),
        "status": _text(payload.get("status")),
        "blocked": bool(payload.get("blocked")),
        "machine_gates_passed": bool(payload.get("machine_gates_passed")),
        "unsafe_actions_available": bool(payload.get("unsafe_actions_available")),
        "hub_api_endpoint": (payload.get("hub_visibility", {}) if isinstance(payload.get("hub_visibility"), dict) else {}).get("api_endpoint", ""),
        "next_safe_action": _text(payload.get("next_safe_action")),
    }


def _self_managed_summary(config: AppConfig, run_store: dict[str, Any], project_id: str) -> dict[str, Any]:
    records = [
        record
        for record in _dicts(run_store.get("records"))
        if _text(record.get("project_id")) == project_id and _text(record.get("run_id")).startswith("self-managed-loop-")
    ]
    root = config.repo_root / ".aresforge" / "self_managed_project_loop"
    artifacts = sorted(root.rglob("*.json")) if root.exists() else []
    return {
        "status": "dry_run_evidence_present" if records or artifacts else "no_dry_run_evidence_found",
        "run_store_record_count": len(records),
        "artifact_count": len(artifacts),
        "latest_run_id": _text(records[-1].get("run_id")) if records else "",
        "self_managed_execution_performed": False,
        "queue_mutation_performed": False,
        "github_execution_performed": False,
    }


def _production_readiness_summary(
    *,
    run_store: dict[str, Any],
    retention_payload: dict[str, Any],
    autonomy_payload: dict[str, Any],
    issue_sync_payload: dict[str, Any],
    monitor_payload: dict[str, Any],
    hub_payload: dict[str, Any],
) -> dict[str, Any]:
    return {
        "ready_for": [
            "local production-autonomy reporting",
            "durable run-store inspection",
            "artifact retention review",
            "autonomy profile inspection",
            "GitHub issue sync planning and dry-run evidence",
            "PR draft summary review",
            "Hub autonomy control-center visibility",
            "self-managed project-loop dry runs",
        ],
        "not_ready_for": _remaining_blockers(),
        "evidence_sources": {
            "run_store_ready": bool(run_store.get("ok")),
            "artifact_retention_ready": bool(retention_payload) and not bool(retention_payload.get("blocked")),
            "autonomy_profile_ready": bool(autonomy_payload) and not bool(autonomy_payload.get("blocked")),
            "github_issue_sync_plan_available": bool(issue_sync_payload),
            "orchestration_monitor_available": bool(monitor_payload),
            "hub_control_center_available": bool(hub_payload),
        },
        "production_autonomy_status": "review_ready",
    }


def _remaining_blockers() -> list[str]:
    return [
        "Live GitHub issue/comment sync remains explicitly gated and does not authorize PR merge, protected branch update, force push, auto-merge, releases, or workflow mutation.",
        "Real Codex execution remains limited to separate explicit low-risk gates; this report performs no Codex dispatch.",
        "Source-code patch application remains default-deny outside explicit future apply boundaries.",
        "Automatic retry/resume and automatic next-item execution remain blocked.",
        "Local LLM/model execution remains advisory/prototype-scoped unless a separate command and machine gates explicitly allow it.",
        "Production deployment, authentication hardening, background scheduling, and cross-machine coordination remain future work.",
    ]


def _next_sprint_recommendations() -> list[str]:
    return [
        "Add an explicit, audited queue-completion gate that consumes M161/M166/M168 evidence and records validation without starting the next item.",
        "Harden the GitHub issue/comment sync path with append-only audit logs, rollback notes, duplicate prevention, and operator recovery views.",
        "Promote self-managed dry-run evidence into a repeatable control-center workflow with run selection, evidence comparison, and failed-gate drilldowns.",
        "Design the next low-risk Codex pilot around clean worktree enforcement, bounded changed paths, validation profiles, and artifact retention references.",
        "Add a non-destructive artifact retention review command that can reconcile orphan references before any future cleanup path exists.",
        "Keep PR creation, merge, protected branch updates, releases, workflow mutation, and automatic next-item execution as explicit future deny-by-default gates.",
    ]


def _machine_gate_behavior(gates: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [gate for gate in gates if not bool(gate.get("passed"))]
    return {
        "gate_count": len(gates),
        "gates_passed": len(gates) - len(failed),
        "gates_failed": len(failed),
        "failed_gate_profiles": [_text(gate.get("gate_profile")) for gate in failed],
        "gate_bypass_performed": False,
        "execution_performed": False,
        "mutation_performed": False,
    }


def _next_safe_action(*, blocked_reasons: list[str], docs_status: dict[str, Any]) -> str:
    if blocked_reasons:
        return "Resolve M169 closeout blockers, then rerun the production autonomy readiness report."
    if not docs_status.get("consistent"):
        return "Update source-of-truth docs for M155-M169, then rerun this report."
    return "Use this report as M169 closeout evidence; start any next sprint only through a separate explicit queue item."


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
        blocked["blocked_reasons"] = _dedupe(
            [*_list(blocked.get("blocked_reasons")), "Output file already exists. Re-run with --force to overwrite."]
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
    artifact_payload["artifacts_created"] = _dedupe([*_list(payload.get("artifacts_created")), str(output_path)])
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
    text = _text(value).upper()
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
    if start_number <= 0 or end_number < start_number:
        return []
    return [f"M{number}" for number in range(start_number, end_number + 1)]


def _payload(result: dict[str, Any]) -> dict[str, Any]:
    payload = result.get("payload", {}) if isinstance(result, dict) else {}
    return payload if isinstance(payload, dict) else {}


def _resolve(repo_root: Path, value: str | Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = repo_root / path
    return path.resolve()


def _safe_id(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in _text(value).lower())
    return cleaned.strip("-") or "production-autonomy-readiness"


def _text(value: Any) -> str:
    return str(value or "").strip()


def _dicts(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [entry for entry in value if isinstance(entry, dict)]
    return []


def _list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [_text(entry) for entry in value if _text(entry)]
    if isinstance(value, tuple):
        return [_text(entry) for entry in value if _text(entry)]
    if value in (None, ""):
        return []
    return [_text(value)]


def _dedupe(values: Any) -> list[str]:
    deduped: list[str] = []
    for value in values:
        text = _text(value)
        if text and text not in deduped:
            deduped.append(text)
    return deduped


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
