from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import re
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.github_automation_safety_audit import audit_github_automation_safety
from aresforge.operator.github_link_registry import inspect_github_link_registry
from aresforge.operator.github_sync_recovery_idempotency import inspect_github_sync_recovery
from aresforge.operator.hub_github_sync_control_panel import inspect_hub_github_sync_control_panel_data
from aresforge.operator.local_project_queue import resolve_project_queue_path
from aresforge.operator.machine_safety_gate_engine import evaluate_machine_safety_gates

COMMAND_NAME = "generate-live-github-loop-readiness-report"
RECORD_TYPE = "live_github_loop_readiness_report_v1"
REPORT_VERSION = "m184.1"
DEFAULT_PROJECT_ID = "aresforge"
DEFAULT_ITEM_ID = "m184-sprint-closeout-and-live-github-loop-readiness-report"
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
    {"milestone": "M170", "title": "GitHub Link Registry for Queue Items", "summary": "Durable local issue/PR link records and idempotency anchors."},
    {"milestone": "M171", "title": "GitHub Issue Creation Real-Run Gate", "summary": "One safe issue creation path behind explicit enablement and machine gates."},
    {"milestone": "M172", "title": "Queue-to-GitHub Issue Backfill", "summary": "Dry-run/default-blocked backfill coordinator over safe queue items."},
    {"milestone": "M173", "title": "GitHub Status Comment Durable Sync", "summary": "One managed issue status comment create/update path with durable registry metadata."},
    {"milestone": "M174", "title": "GitHub Issue State Reconciliation", "summary": "Recommendation-only local-vs-GitHub issue state reconciliation."},
    {"milestone": "M175", "title": "GitHub Issue Closure Safe Execution Gate", "summary": "Evidence-driven one-issue closure gate, dry-run by default."},
    {"milestone": "M176", "title": "PR Draft Branch Planning Contract", "summary": "Local branch and draft PR planning without branch or PR mutation."},
    {"milestone": "M177", "title": "PR Draft Creation Gate", "summary": "One draft PR creation path behind explicit enablement, branch safety, and gates."},
    {"milestone": "M178", "title": "PR Evidence Comment Sync", "summary": "One managed PR evidence comment sync path with registry-backed idempotency."},
    {"milestone": "M179", "title": "GitHub Sync Recovery and Idempotency", "summary": "Read-only recovery, repair, resume, and no-op guidance from local evidence."},
    {"milestone": "M180", "title": "Hub GitHub Sync Control Panel", "summary": "Read-only Hub visibility across the GitHub loop."},
    {"milestone": "M181", "title": "Self-Managed Issue Loop Real Run", "summary": "Dry-run-default issue loop coordinator with mocked live path coverage."},
    {"milestone": "M182", "title": "Self-Managed PR Draft Loop Dry Run", "summary": "Dry-run-default PR draft loop coordinator with mocked live path coverage."},
    {"milestone": "M183", "title": "GitHub Automation Safety Audit", "summary": "Read-only audit of implemented GitHub automation gates, boundaries, and risks."},
    {"milestone": "M184", "title": "Sprint Closeout and Live GitHub Loop Readiness Report", "summary": "Source-of-truth closeout and next-sprint readiness report for the live GitHub loop."},
)

_BLOCKED_OPERATIONS: tuple[str, ...] = (
    "merge_pull_request",
    "enable_auto_merge",
    "force_push",
    "update_protected_branch",
    "create_release",
    "modify_github_workflow",
    "automatic_issue_closure",
    "source_code_patch_application_as_part_of_github_sync",
    "queue_status_mutation_from_readiness_report",
    "codex_execution_from_readiness_report",
    "model_execution_from_readiness_report",
    "validation_command_execution_from_readiness_report",
    "retry_or_resume_execution_from_readiness_report",
    "automatic_next_item_execution",
)

_BOUNDARY_CONFIRMATIONS: tuple[str, ...] = (
    "M184 is a closeout and readiness report for the M170-M184 live GitHub loop sprint.",
    "M184 is local-only, read-only, and dry-run by default.",
    "M184 performs no GitHub execution, gh invocation, registry mutation, queue mutation, Codex/model execution, validation command execution, source patch application, retry/resume, PR merge, auto-merge, force push, protected branch update, release creation, workflow mutation, or automatic next-item execution.",
    "Real GitHub mutation remains limited to separate commands with explicit enablement, autonomy profile allowance, idempotency checks, and passing machine gates.",
)


def generate_live_github_loop_readiness_report(
    config: AppConfig,
    *,
    project_id: str = DEFAULT_PROJECT_ID,
    sprint_start: str = "M170",
    sprint_end: str = "M184",
    item_id: str = DEFAULT_ITEM_ID,
    queue_path: str | Path | None = None,
    registry_path: str | Path | None = None,
    repo: str | None = None,
    autonomy_profile: str = DEFAULT_AUTONOMY_PROFILE,
    output: str | Path | None = None,
    force: bool = False,
    output_format: str = "json",
) -> dict[str, Any]:
    fmt = _text(output_format).lower() or "json"
    if fmt != "json":
        return _error("invalid_format", {"format": output_format, "supported_formats": ["json"]})

    normalized_project_id = _text(project_id) or DEFAULT_PROJECT_ID
    normalized_item_id = _text(item_id) or DEFAULT_ITEM_ID
    normalized_start = _normalize_milestone(sprint_start) or "M170"
    normalized_end = _normalize_milestone(sprint_end) or "M184"
    selected_profile = _text(autonomy_profile) or DEFAULT_AUTONOMY_PROFILE
    repository = _normalize_repo(config, repo)
    queue_result = _load_queue(config, queue_path)
    queue = queue_result.get("queue", {}) if queue_result.get("ok") else {}
    items = _milestone_items(queue, normalized_project_id, normalized_start, normalized_end)
    docs_status = _inspect_docs(config.repo_root, normalized_start, normalized_end)
    read_only_gate = _gate_payload(config, item_id=normalized_item_id, queue_path=queue_path, gate_profile="read_only_agent")
    github_sync_gate = _gate_payload(config, item_id=normalized_item_id, queue_path=queue_path, gate_profile="github_sync")
    machine_gates = [
        _gate_summary(read_only_gate, required_for_readiness=True),
        _gate_summary(github_sync_gate, required_for_readiness=False),
    ]
    registry_payload = _payload(
        inspect_github_link_registry(
            config,
            project_id=normalized_project_id,
            item_id=normalized_item_id,
            registry_path=registry_path,
            repository=repository,
            output_format="json",
        )
    )
    recovery_payload = _payload(
        inspect_github_sync_recovery(
            config,
            project_id=normalized_project_id,
            item_id=normalized_item_id,
            queue_path=queue_path,
            registry_path=registry_path,
            repo=repository,
            output_format="json",
        )
    )
    control_panel_payload = _payload(
        inspect_hub_github_sync_control_panel_data(
            config,
            project_id=normalized_project_id,
            item_id="m180-hub-github-sync-control-panel",
            queue_path=queue_path,
            registry_path=registry_path,
            repo=repository,
            autonomy_profile=selected_profile,
            output_format="json",
        )
    )
    audit_payload = _payload(
        audit_github_automation_safety(
            config,
            project_id=normalized_project_id,
            item_id="m183-github-automation-safety-audit",
            queue_path=queue_path,
            registry_path=registry_path,
            repo=repository,
            autonomy_profile=selected_profile,
            output_format="json",
        )
    )

    missing_milestones = _missing_milestones(items, normalized_start, normalized_end)
    incomplete_items = [item for item in items if item["status"] not in {"done", "cancelled"}]
    blocked_items = [item for item in items if item["status"] == "blocked" or item.get("blocked_by")]
    blocked_reasons = _dedupe(
        [
            *queue_result.get("blocked_reasons", []),
            *(_list(read_only_gate.get("blocked_reasons")) if not _gate_passed(read_only_gate) else []),
            *_list(registry_payload.get("blocked_reasons")),
            *_list(recovery_payload.get("blocked_reasons")),
            *_list(control_panel_payload.get("blocked_reasons")),
            *_list(audit_payload.get("blocked_reasons")),
            *[f"Queue item missing for {milestone}." for milestone in missing_milestones],
            *[f"Queue item not complete: {item['item_id']}." for item in incomplete_items],
            *[f"Queue item blocked: {item['item_id']}." for item in blocked_items],
        ]
    )
    warnings = _dedupe(
        [
            *queue_result.get("warnings", []),
            *_list(registry_payload.get("warnings")),
            *_list(recovery_payload.get("warnings")),
            *_list(control_panel_payload.get("warnings")),
            *_list(audit_payload.get("warnings")),
            *[f"Missing source-of-truth doc: {path}." for path in docs_status.get("missing_docs", [])],
            *(["One or more source-of-truth docs are missing sprint milestone mentions."] if docs_status.get("missing_milestone_mentions") else []),
            "No live GitHub verification was performed by this readiness report.",
        ]
    )
    blocked = bool(blocked_reasons)
    status = "blocked" if blocked else ("docs_sync_required" if not docs_status.get("consistent") else "ready_with_warnings")
    issue_number = _first_int(registry_payload, "issue_number")
    pr_number = _first_int(registry_payload, "pr_number")
    payload: dict[str, Any] = {
        "record_type": RECORD_TYPE,
        "artifact_type": RECORD_TYPE,
        "report_version": REPORT_VERSION,
        "generated": True,
        "generated_at": _now_iso(),
        "project_id": normalized_project_id,
        "item_id": normalized_item_id,
        "repository": repository,
        "issue_number": issue_number,
        "issue_url": _first_text(registry_payload, "issue_url"),
        "pr_number": pr_number,
        "pr_url": _first_text(registry_payload, "pr_url"),
        "sync_status": status,
        "status": status,
        "blocked": blocked,
        "blocked_reasons": blocked_reasons,
        "warnings": warnings,
        "machine_gates_checked": machine_gates,
        "machine_gates_passed": _gate_passed(read_only_gate) and not blocked,
        "autonomy_profile": selected_profile,
        "dry_run": True,
        "github_enabled": False,
        "github_execution_performed": False,
        "mutation_performed": False,
        "registry_mutation_performed": False,
        "queue_mutation_performed": False,
        "codex_execution_performed": False,
        "model_execution_performed": False,
        "patch_application_performed": False,
        "validation_command_execution_performed": False,
        "idempotency_key": _idempotency_key(normalized_project_id, normalized_item_id, repository, normalized_start, normalized_end),
        "recovery_available": bool(recovery_payload.get("recovery_available", True)),
        "local_only": True,
        "next_safe_action": _next_safe_action(blocked=blocked, docs_status=docs_status, recovery_payload=recovery_payload),
        "sprint_start": normalized_start,
        "sprint_end": normalized_end,
        "milestones_reviewed": _milestones(normalized_start, normalized_end),
        "sprint_closeout_summary": _sprint_closeout_summary(items, normalized_start, normalized_end),
        "capability_summary": _capability_summary(normalized_start, normalized_end),
        "readiness_summary": _readiness_summary(audit_payload, registry_payload, recovery_payload, control_panel_payload),
        "docs_sync": docs_status,
        "queue_summary": _queue_summary(items, missing_milestones),
        "github_safety": _github_safety_summary(audit_payload),
        "machine_gate_behavior": _machine_gate_behavior(machine_gates),
        "registry_health": _registry_health(registry_payload),
        "recovery_health": _recovery_health(recovery_payload),
        "hub_control_panel_health": _control_panel_health(control_panel_payload),
        "warnings_and_blockers": {
            "blocked": blocked,
            "blocked_reasons": blocked_reasons,
            "warnings": warnings,
            "remaining_risks": _list_risks(audit_payload),
        },
        "safety_boundaries": {
            "do_not_merge_pull_requests": True,
            "do_not_enable_auto_merge": True,
            "do_not_force_push": True,
            "do_not_update_protected_branches": True,
            "do_not_create_releases": True,
            "do_not_mutate_github_workflows": True,
            "do_not_close_issues_automatically": True,
            "do_not_apply_source_patches_as_part_of_github_sync": True,
            "do_not_bypass_autonomy_profiles_or_machine_gates": True,
            "blocked_operations": list(_BLOCKED_OPERATIONS),
        },
        "next_sprint_recommendations": _next_sprint_recommendations(),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }
    return _emit_or_write(config=config, payload=payload, output=output, force=force)


def _load_queue(config: AppConfig, queue_path: str | Path | None) -> dict[str, Any]:
    path = resolve_project_queue_path(config.repo_root, queue_path)
    if not path.exists():
        return {"ok": False, "queue": {}, "warnings": [], "blocked_reasons": [f"Project queue not found: {path}"]}
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"ok": False, "queue": {}, "warnings": [], "blocked_reasons": [f"Project queue could not be read as JSON: {exc}"]}
    if not isinstance(raw, dict):
        return {"ok": False, "queue": {}, "warnings": [], "blocked_reasons": ["Project queue JSON must decode to an object."]}
    return {"ok": True, "queue": raw, "warnings": [], "blocked_reasons": []}


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


def _gate_payload(config: AppConfig, *, item_id: str, queue_path: str | Path | None, gate_profile: str) -> dict[str, Any]:
    return _payload(
        evaluate_machine_safety_gates(
            config,
            item_id=item_id,
            gate_profile=gate_profile,
            queue_path=queue_path,
            output_format="json",
        )
    )


def _gate_summary(payload: dict[str, Any], *, required_for_readiness: bool) -> dict[str, Any]:
    checks = _dicts(payload.get("checks"))
    return {
        "gate_profile": _text(payload.get("gate_profile")) or "read_only_agent",
        "passed": _gate_passed(payload),
        "blocked": bool(payload.get("blocked")),
        "blocked_reasons": _list(payload.get("blocked_reasons")),
        "warnings": _list(payload.get("warnings")),
        "checks_failed": [
            _text(check.get("check_id"))
            for check in checks
            if not bool(check.get("passed")) and not bool(check.get("warning_only"))
        ],
        "required_for_readiness": required_for_readiness,
        "dry_run_label": "required_read_only_closeout_gate" if required_for_readiness else "future_live_sync_gate_status_only",
    }


def _sprint_closeout_summary(items: list[dict[str, Any]], sprint_start: str, sprint_end: str) -> dict[str, Any]:
    milestones = _milestones(sprint_start, sprint_end)
    done = [item for item in items if item["status"] == "done"]
    return {
        "title": "M170-M184 live self-managed GitHub loop sprint closeout",
        "scope": "Gated, idempotent GitHub issue/PR coordination for AresForge itself with destructive operations blocked.",
        "milestone_count_expected": len(milestones),
        "milestone_item_count": len(items),
        "completed_item_count": len(done),
        "all_milestone_items_complete": len(items) == len(milestones) and len(done) == len(items),
        "live_mutation_authorized_by_report": False,
    }


def _capability_summary(sprint_start: str, sprint_end: str) -> list[dict[str, str]]:
    milestones = set(_milestones(sprint_start, sprint_end))
    return [dict(summary) for summary in MILESTONE_SUMMARIES if summary["milestone"] in milestones]


def _queue_summary(items: list[dict[str, Any]], missing_milestones: list[str]) -> dict[str, Any]:
    counts: dict[str, int] = {}
    for item in items:
        counts[item["status"]] = counts.get(item["status"], 0) + 1
    return {
        "items": items,
        "status_counts": counts,
        "missing_milestones": missing_milestones,
        "validation_evidence_item_count": sum(1 for item in items if item["validation_summary"] and item["tests_run"]),
    }


def _readiness_summary(
    audit_payload: dict[str, Any],
    registry_payload: dict[str, Any],
    recovery_payload: dict[str, Any],
    control_panel_payload: dict[str, Any],
) -> dict[str, Any]:
    capability_counts = audit_payload.get("capability_counts") if isinstance(audit_payload.get("capability_counts"), dict) else {}
    return {
        "ready_for": [
            "local link registry coordination",
            "dry-run issue creation/backfill/comment/reconciliation/closure review",
            "dry-run PR branch planning, draft PR gating, and PR evidence comment review",
            "operator-reviewed recovery/idempotency decisions",
            "Hub GitHub Sync Control Panel inspection",
            "separate explicitly enabled low-risk live GitHub sync commands after gates pass",
        ],
        "not_ready_for": [
            "automatic PR merge or auto-merge",
            "force push or protected branch update",
            "release or workflow mutation",
            "automatic issue closure from loop coordinators",
            "source-code patch application as part of GitHub sync",
            "automatic next-item execution",
        ],
        "capabilities_audited": int(capability_counts.get("capabilities_audited") or 0),
        "live_mutation_capable_surfaces": int(capability_counts.get("live_mutation_capable") or 0),
        "registry_record_count": int(registry_payload.get("record_count") or 0),
        "recovery_available": bool(recovery_payload.get("recovery_available", True)),
        "control_panel_ready": not bool(control_panel_payload.get("blocked")),
    }


def _github_safety_summary(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "record_type": _text(payload.get("record_type")),
        "sync_status": _text(payload.get("sync_status") or payload.get("status")),
        "blocked": bool(payload.get("blocked")),
        "machine_gates_passed": bool(payload.get("machine_gates_passed")),
        "capability_counts": payload.get("capability_counts") if isinstance(payload.get("capability_counts"), dict) else {},
        "blocked_operations": _list(payload.get("blocked_operations")) or list(_BLOCKED_OPERATIONS),
        "github_execution_performed": False,
        "mutation_performed": False,
        "local_only": True,
    }


def _machine_gate_behavior(gates: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [gate for gate in gates if not bool(gate.get("passed"))]
    return {
        "gate_count": len(gates),
        "gates_passed": len(gates) - len(failed),
        "gates_failed": len(failed),
        "failed_gate_profiles": [_text(gate.get("gate_profile")) for gate in failed],
        "gate_bypass_performed": False,
        "github_enabled": False,
        "github_execution_performed": False,
        "mutation_performed": False,
    }


def _registry_health(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "record_type": _text(payload.get("record_type")),
        "sync_status": _text(payload.get("sync_status") or payload.get("status")) or "unknown",
        "blocked": bool(payload.get("blocked")),
        "record_count": int(payload.get("record_count") or 0),
        "matched_record_count": int(payload.get("matched_record_count") or 0),
        "registry_path": _text(payload.get("registry_path")),
        "github_execution_performed": False,
        "mutation_performed": False,
        "local_only": True,
    }


def _recovery_health(payload: dict[str, Any]) -> dict[str, Any]:
    counts = payload.get("operation_counts") if isinstance(payload.get("operation_counts"), dict) else {}
    return {
        "record_type": _text(payload.get("record_type")),
        "sync_status": _text(payload.get("sync_status") or payload.get("status")) or "unknown",
        "blocked": bool(payload.get("blocked")),
        "operations_complete_noop": int(counts.get("operations_complete_noop") or 0),
        "operations_partial": int(counts.get("operations_partial") or 0),
        "recovery_available": bool(payload.get("recovery_available", True)),
        "github_execution_performed": False,
        "mutation_performed": False,
        "local_only": True,
    }


def _control_panel_health(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "record_type": _text(payload.get("record_type")),
        "sync_status": _text(payload.get("sync_status") or payload.get("status")) or "unknown",
        "blocked": bool(payload.get("blocked")),
        "unsafe_actions_available": bool(payload.get("unsafe_actions_available")),
        "github_mutation_allowed": bool(payload.get("github_mutation_allowed")),
        "github_execution_performed": False,
        "mutation_performed": False,
        "local_only": True,
    }


def _next_sprint_recommendations() -> list[str]:
    return [
        "Run a narrowly scoped, operator-approved live GitHub issue/comment sync pilot for one already-safe queue item, using existing M171/M173 gates and mocked-test parity.",
        "Add append-only live GitHub mutation audit evidence before widening beyond one issue or one comment per invocation.",
        "Add operator recovery views for partial preflight-only or remote-success/local-registry-failure cases.",
        "Keep closure, PR merge, protected branch updates, releases, workflow mutation, and source patch application outside automatic GitHub sync.",
        "Promote Hub GitHub Sync visibility into a step-by-step operator checklist before any broader live loop execution.",
    ]


def _next_safe_action(*, blocked: bool, docs_status: dict[str, Any], recovery_payload: dict[str, Any]) -> str:
    if blocked:
        return "Resolve M184 closeout blockers, then rerun this readiness report."
    counts = recovery_payload.get("operation_counts") if isinstance(recovery_payload.get("operation_counts"), dict) else {}
    if int(counts.get("operations_partial") or 0) > 0:
        return "Review recovery repair/resume guidance before any separate live GitHub sync command."
    if not docs_status.get("consistent"):
        return "Update source-of-truth docs for M170-M184, then rerun this report."
    return "Use this report as sprint closeout evidence and start the next sprint only through a separate queued milestone."


def _emit_or_write(*, config: AppConfig, payload: dict[str, Any], output: str | Path | None, force: bool) -> dict[str, Any]:
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
        blocked["sync_status"] = "blocked"
        blocked["blocked"] = True
        blocked["blocked_reasons"] = _dedupe([*_list(blocked.get("blocked_reasons")), "Output file already exists. Re-run with --force to overwrite."])
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


def _list_risks(payload: dict[str, Any]) -> list[str]:
    risks: list[str] = []
    for entry in _dicts(payload.get("remaining_risks")):
        summary = _text(entry.get("summary"))
        if summary:
            risks.append(summary)
    return _dedupe(risks)


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


def _gate_passed(payload: dict[str, Any]) -> bool:
    return bool(payload.get("passed")) and not bool(payload.get("blocked"))


def _payload(result: dict[str, Any]) -> dict[str, Any]:
    payload = result.get("payload", {}) if isinstance(result, dict) else {}
    return payload if isinstance(payload, dict) else {}


def _first_int(payload: dict[str, Any], key: str) -> int | None:
    value = _int_or_none(payload.get(key))
    if value is not None:
        return value
    for record in _dicts(payload.get("records")):
        value = _int_or_none(record.get(key))
        if value is not None:
            return value
    return None


def _first_text(payload: dict[str, Any], key: str) -> str:
    value = _text(payload.get(key))
    if value:
        return value
    for record in _dicts(payload.get("records")):
        value = _text(record.get(key))
        if value:
            return value
    return ""


def _resolve(repo_root: Path, value: str | Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = repo_root / path
    return path.resolve()


def _normalize_repo(config: AppConfig, repo: str | None) -> str:
    raw = _text(repo)
    if raw:
        return raw
    return f"{config.github_owner}/{config.github_repo}"


def _idempotency_key(project_id: str, item_id: str, repository: str, sprint_start: str, sprint_end: str) -> str:
    return "live-github-loop-readiness:" + ":".join([_slug(project_id), _slug(item_id), _slug(repository), sprint_start.lower(), sprint_end.lower()])


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", _text(value).lower()).strip("-") or "unknown"


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


def _int_or_none(value: Any) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    text = _text(value)
    return int(text) if text.isdigit() else None


def _text(value: Any) -> str:
    return str(value or "").strip()


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _error(error: str, details: dict[str, Any]) -> dict[str, Any]:
    return {"command": COMMAND_NAME, "ok": False, "local_only": True, "error": error, "details": details}
