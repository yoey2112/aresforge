from __future__ import annotations

from datetime import UTC, datetime
import json
import re
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.local_project_dashboard import summarize_local_project_dashboard
from aresforge.operator.local_project_queue import (
    QUEUE_STATUSES,
    inspect_local_queue_item_readiness,
    read_local_project_progress_rollup,
    resolve_project_queue_path,
)
from aresforge.operator.local_project_readiness import inspect_local_project_readiness

_REPORTS_V1_BOUNDARY_CONFIRMATIONS: tuple[str, ...] = (
    "Local-only Reports v1.",
    "Read-only local project and queue reporting.",
    "File-backed local state only.",
    "No GitHub API calls.",
    "No gh calls.",
    "No GitHub workflow activity.",
    "No agent execution.",
    "No Codex execution.",
    "No local LLM execution.",
    "No LLM/model routing execution.",
    "No queue or project mutation.",
)


def inspect_local_project_report(config: AppConfig) -> dict[str, Any]:
    dashboard = summarize_local_project_dashboard(config)
    active_project_id = str(dashboard.get("active_project_id", "")).strip()
    active_project = dashboard.get("active_project") if isinstance(dashboard.get("active_project"), dict) else None

    project_health = {
        "total_projects": int(dashboard.get("total_projects", 0)),
        "active_project_selected": bool(active_project_id),
        "overall_status": str(
            (dashboard.get("validation_summary") or {}).get("overall_status", "needs_attention")
        ).strip(),
        "project_counts_by_status": dict((dashboard.get("project_summary") or {}).get("counts_by_status", {})),
    }

    queue_summary = {
        "item_count": int((dashboard.get("queue_summary") or {}).get("item_count", 0)),
        "counts_by_status": dict((dashboard.get("queue_summary") or {}).get("counts_by_status", {})),
        "blocked_count": len((dashboard.get("queue_summary") or {}).get("blocked_items", [])),
        "ready_count": len((dashboard.get("queue_summary") or {}).get("ready_items", [])),
    }

    documentation_summary = {
        "docs_ready": bool((dashboard.get("docs_summary") or {}).get("docs_ready", False)),
        "missing_docs": list((dashboard.get("docs_summary") or {}).get("missing_docs", [])),
        "present_count": int((dashboard.get("docs_summary") or {}).get("present_count", 0)),
        "missing_count": int((dashboard.get("docs_summary") or {}).get("missing_count", 0)),
    }

    roadmap_summary = _roadmap_summary_from_docs(dashboard)

    validation_summary = dict(dashboard.get("validation_summary", {}))
    active_project_readiness = None
    if active_project_id:
        active_project_readiness = inspect_local_project_readiness(config, project_id=active_project_id)
    queue_items, queue_warnings = _load_report_queue_items(config)
    self_managed_readiness_summary = _self_managed_readiness_summary(
        config=config,
        active_project_id=active_project_id,
        active_project_readiness=active_project_readiness,
        queue_items=queue_items,
    )

    blockers: list[str] = []
    if not active_project_id:
        blockers.append("No active project selected.")
    if queue_summary["blocked_count"] > 0:
        blockers.append("Queue has blocked items.")
    if documentation_summary["missing_count"] > 0:
        blockers.append("Required documentation is missing.")
    if active_project_readiness and not bool(active_project_readiness.get("ok", True)):
        blockers.append("Active project readiness inspection failed.")

    warnings = sorted(
        set(
            [
                *[str(item) for item in dashboard.get("warnings", []) if str(item).strip()],
                *[str(item) for item in queue_warnings if str(item).strip()],
            ]
        )
    )
    recommended_next_action = str(
        dashboard.get("recommended_next_action")
        or "Inspect local dashboard summaries and resolve blockers."
    ).strip()

    return {
        "ok": True,
        "local_only": True,
        "report_type": "local_project_report_summary",
        "generated_at": datetime.now(UTC).isoformat(),
        "active_project": {
            "active_project_id": active_project_id,
            "active_project_name": str((active_project or {}).get("name", "")).strip(),
            "active_project_selected": bool(active_project_id),
        },
        "project_health": project_health,
        "roadmap_summary": roadmap_summary,
        "queue_summary": queue_summary,
        "self_managed_readiness_summary": self_managed_readiness_summary,
        "validation_summary": validation_summary,
        "documentation_summary": documentation_summary,
        "blockers": blockers,
        "warnings": warnings,
        "recommended_next_action": recommended_next_action,
    }


def read_local_project_reports(config: AppConfig) -> dict[str, Any]:
    dashboard = summarize_local_project_dashboard(config)
    foundation = inspect_local_project_report(config)
    active_project = foundation.get("active_project", {}) if isinstance(foundation.get("active_project"), dict) else {}
    active_project_id = str(active_project.get("active_project_id", "")).strip()
    queue_items, queue_warnings = _load_report_queue_items(config)
    queue_counts_by_status = {status: 0 for status in QUEUE_STATUSES}
    queue_counts_by_status.update(_count_by(queue_items, "status"))
    queue_counts_by_type = _count_by(queue_items, "item_type")
    queue_counts_by_lane = _count_by(queue_items, "assigned_agent", empty_label="unassigned")
    evidence_items = [
        item for item in queue_items
        if isinstance(item.get("completion_evidence"), dict) and bool(item.get("completion_evidence"))
    ]
    closeout_eligible_items = [item for item in queue_items if _report_item_closeout_eligible(item)]
    closed_completed_items = [
        item for item in queue_items
        if str(item.get("status", "")).strip() in {"done", "cancelled"}
    ]

    progress_rollup: dict[str, Any] = {}
    progress_warnings: list[str] = []
    if active_project_id:
        progress = read_local_project_progress_rollup(config, project_id=active_project_id)
        if progress.get("ok", False):
            progress_rollup = progress
        else:
            progress_warnings.append(
                str((progress.get("details") or {}).get("message", progress.get("error", "progress_rollup_failed")))
            )

    blockers = _unique_list(
        [
            *[str(item).strip() for item in foundation.get("blockers", []) if str(item).strip()],
            *[
                f"Queue item {str(item.get('item_id', '')).strip()} is blocked."
                for item in queue_items
                if str(item.get("status", "")).strip() == "blocked"
            ],
        ]
    )
    warnings = _unique_list(
        [
            *[str(item).strip() for item in dashboard.get("warnings", []) if str(item).strip()],
            *[str(item).strip() for item in foundation.get("warnings", []) if str(item).strip()],
            *queue_warnings,
            *progress_warnings,
        ]
    )
    latest_activity = _latest_report_activity(queue_items, progress_rollup)

    return {
        "ok": True,
        "local_only": True,
        "read_only": True,
        "report_type": "local_reports_v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "overall_project_count": int((foundation.get("project_health") or {}).get("total_projects", 0)),
        "project_counts_by_status": dict((foundation.get("project_health") or {}).get("project_counts_by_status", {})),
        "active_project_summary": active_project,
        "queue_item_totals": {
            "total": len(queue_items),
            "blocked": len([item for item in queue_items if str(item.get("status", "")).strip() == "blocked"]),
            "ready": len([item for item in queue_items if str(item.get("status", "")).strip() == "ready"]),
            "in_progress": len([item for item in queue_items if str(item.get("status", "")).strip() == "in_progress"]),
            "closed_completed": len(closed_completed_items),
        },
        "queue_item_counts_by_status": dict(sorted(queue_counts_by_status.items())),
        "queue_item_counts_by_type": queue_counts_by_type,
        "queue_item_counts_by_lane": queue_counts_by_lane,
        "evidence_summary": {
            "items_with_evidence_captured": len(evidence_items),
            "item_ids": _item_ids(evidence_items),
        },
        "closeout_summary": {
            "items_eligible_for_closeout": len(closeout_eligible_items),
            "eligible_item_ids": _item_ids(closeout_eligible_items),
            "closed_completed_items": len(closed_completed_items),
            "closed_completed_item_ids": _item_ids(closed_completed_items),
        },
        "latest_activity_summary": {
            "latest_activity_timestamp": latest_activity,
            "available": bool(latest_activity),
        },
        "project_progress_rollup": progress_rollup,
        "local_only_operating_boundary_summary": list(_REPORTS_V1_BOUNDARY_CONFIRMATIONS),
        "next_safe_action": _reports_v1_next_safe_action(
            blockers=blockers,
            closeout_eligible_count=len(closeout_eligible_items),
            ready_count=len([item for item in queue_items if str(item.get("status", "")).strip() == "ready"]),
            total_items=len(queue_items),
            foundation_next_action=str(foundation.get("recommended_next_action", "")).strip(),
        ),
        "blockers": blockers,
        "warnings": warnings,
        "limitations": [
            "Reports v1 is an in-Hub read-only reporting layer.",
            "Reports v1 does not implement PDF, CSV, or external export workflows.",
            "Agent/LLM routing remains future work and is not executed.",
        ],
        "boundary_confirmations": list(_REPORTS_V1_BOUNDARY_CONFIRMATIONS),
    }


def _roadmap_summary_from_docs(dashboard: dict[str, Any]) -> dict[str, Any]:
    docs = (dashboard.get("docs_summary") or {}).get("docs", [])
    roadmap_exists = False
    if isinstance(docs, list):
        for item in docs:
            if not isinstance(item, dict):
                continue
            if str(item.get("path", "")).strip() == "docs/roadmap/ROADMAP.md":
                roadmap_exists = bool(item.get("exists", False))
                break

    markdown = ""
    try:
        path = dashboard.get("paths", {}).get("registry_path", "")
        # Reuse repo_root inference from known local path values already in dashboard.
        # registry_path is "<repo>/.aresforge/projects/projects.json"; ROADMAP path is deterministic.
        if path:
            repo_root = re.split(r"[\\/]\.aresforge[\\/]", str(path), maxsplit=1)[0]
            roadmap_file = Path(repo_root) / "docs" / "roadmap" / "ROADMAP.md"
            with roadmap_file.open("r", encoding="utf-8") as handle:
                markdown = handle.read()
    except OSError:
        markdown = ""

    active_milestone = _extract_active_milestone(markdown) if markdown else ""
    return {
        "roadmap_doc_exists": roadmap_exists,
        "active_milestone": active_milestone,
        "status": "available" if roadmap_exists else "missing",
    }


def _extract_active_milestone(markdown: str) -> str:
    match = re.search(r"^###\s+(.+?)\s*$\n+Status:\s+Active\.", markdown, flags=re.MULTILINE)
    if not match:
        return ""
    return match.group(1).strip()


def _load_report_queue_items(config: AppConfig) -> tuple[list[dict[str, Any]], list[str]]:
    queue_path = resolve_project_queue_path(config.repo_root, None)
    if not queue_path.exists():
        return [], [f"Project queue not found: {queue_path}"]
    try:
        raw = json.loads(queue_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [], [f"Project queue could not be parsed: {exc}"]
    if not isinstance(raw, dict):
        return [], ["Project queue has invalid schema; expected JSON object."]
    items = raw.get("work_items", [])
    if not isinstance(items, list):
        return [], ["Project queue contains non-list work_items field."]
    return [item for item in items if isinstance(item, dict)], []


def _self_managed_readiness_summary(
    *,
    config: AppConfig,
    active_project_id: str,
    active_project_readiness: dict[str, Any] | None,
    queue_items: list[dict[str, Any]],
) -> dict[str, Any]:
    project_id = "aresforge"
    project_items = [
        item for item in queue_items if str(item.get("project_id", "")).strip() == project_id
    ]
    m81 = _find_item(project_items, "m81-local-llm-advisory-coding-lane-prototype")
    m82 = _find_item(project_items, "m82-self-managed-aresforge-test-run")

    readiness_checks: list[dict[str, Any]] = []
    recovered_runs: list[dict[str, str]] = []
    blocking_runs: list[dict[str, str]] = []
    active_blocking_runs: list[dict[str, str]] = []
    historical_blocking_runs: list[dict[str, str]] = []
    readiness_warnings: list[str] = []
    readiness_blockers: list[str] = []

    for item in sorted(project_items, key=lambda candidate: str(candidate.get("item_id", "")).strip()):
        item_id = str(item.get("item_id", "")).strip()
        if not item_id:
            continue
        readiness = inspect_local_queue_item_readiness(config, item_id=item_id)
        dependency_summary = readiness.get("dependency_summary", {}) if isinstance(readiness, dict) else {}
        item_recovered = _dispatch_entries(dependency_summary, "recovered_dispatch_runs")
        item_blocking = _dispatch_entries(dependency_summary, "dispatch_run_blockers")
        recovered_runs.extend(item_recovered)
        blocking_runs.extend(item_blocking)
        if str(item.get("status", "")).strip() in {"done", "cancelled"}:
            historical_blocking_runs.extend(item_blocking)
        else:
            active_blocking_runs.extend(item_blocking)
        readiness_checks.append(
            {
                "item_id": item_id,
                "status": str(item.get("status", "")).strip(),
                "readiness_status": str(readiness.get("readiness_status", "")).strip(),
                "can_start": bool(readiness.get("can_start", False)),
                "dependency_count": int(dependency_summary.get("total_dependencies", 0) or 0),
                "recovered_dispatch_run_count": len(item_recovered),
                "dispatch_run_blocker_count": len(item_blocking),
            }
        )
        readiness_warnings.extend(
            str(warning).strip()
            for warning in readiness.get("warnings", [])
            if str(warning).strip()
        )
        readiness_blockers.extend(
            str(blocker).strip()
            for blocker in readiness.get("blockers", [])
            if str(blocker).strip() and str(item.get("status", "")).strip() != "done"
        )

    status_counts = _count_by(project_items, "status") if project_items else {}
    active_readiness_status = ""
    if isinstance(active_project_readiness, dict):
        active_readiness_status = str(active_project_readiness.get("readiness_status", "")).strip()

    managed_project_registered = bool(project_items) or (
        isinstance(active_project_readiness, dict)
        and str(active_project_readiness.get("project_id", "")).strip() == project_id
        and bool(active_project_readiness.get("ok", False))
    )
    blocking_runs = _unique_dispatch_entries(blocking_runs)
    active_blocking_runs = _unique_dispatch_entries(active_blocking_runs)
    historical_blocking_runs = _unique_dispatch_entries(historical_blocking_runs)
    recovered_runs = _unique_dispatch_entries(recovered_runs)
    readiness_status = "ready"
    if not managed_project_registered or active_blocking_runs:
        readiness_status = "needs_attention"

    return {
        "project_id": project_id,
        "self_managed": True,
        "read_only": True,
        "local_only": True,
        "managed_project_registered": managed_project_registered,
        "active_project_selected": active_project_id == project_id,
        "active_project_readiness_status": active_readiness_status or "not_inspected",
        "queue_item_count": len(project_items),
        "queue_counts_by_status": status_counts,
        "m81_status": str((m81 or {}).get("status", "")).strip() or "missing",
        "m81_completed": str((m81 or {}).get("status", "")).strip() == "done",
        "m82_status": str((m82 or {}).get("status", "")).strip() or "missing",
        "recovered_dispatch_run_summary": {
            "non_blocking_count": len(recovered_runs),
            "blocking_count": len(active_blocking_runs),
            "historical_blocking_count": len(historical_blocking_runs),
            "non_blocking_runs": recovered_runs,
            "blocking_runs": active_blocking_runs,
            "historical_blocking_runs": historical_blocking_runs,
            "recovered_runs_block_project_readiness": bool(active_blocking_runs),
        },
        "readiness_checks": readiness_checks,
        "readiness_flows_checked": [
            "inspect-managed-project --project-id aresforge",
            "inspect-local-project-readiness --project-id aresforge",
            "inspect-local-project-report",
            "inspect-local-queue-agent-summary",
            "inspect-project-queue --project-id aresforge",
        ],
        "safety_boundary_confirmations": {
            "operator_review_required": True,
            "automatic_next_item_execution_allowed": False,
            "unattended_multi_item_execution_allowed": False,
            "github_api_allowed": False,
            "gh_allowed": False,
            "external_workflow_allowed": False,
            "repo_mutation_allowed": False,
        },
        "readiness_status": readiness_status,
        "summary": _self_managed_summary_text(
            managed_project_registered=managed_project_registered,
            active_project_selected=active_project_id == project_id,
            blocking_run_count=len(active_blocking_runs),
            recovered_run_count=len(recovered_runs),
        ),
        "blockers": _unique_list(readiness_blockers),
        "warnings": _unique_list(readiness_warnings),
    }


def _find_item(items: list[dict[str, Any]], item_id: str) -> dict[str, Any] | None:
    for item in items:
        if str(item.get("item_id", "")).strip() == item_id:
            return item
    return None


def _dispatch_entries(summary: dict[str, Any], field: str) -> list[dict[str, str]]:
    values = summary.get(field, []) if isinstance(summary, dict) else []
    if not isinstance(values, list):
        return []
    entries: list[dict[str, str]] = []
    for value in values:
        if not isinstance(value, dict):
            continue
        entries.append(
            {
                "run_id": str(value.get("run_id", "")).strip(),
                "item_id": str(value.get("item_id", "")).strip(),
                "dispatch_state": str(value.get("dispatch_state", "")).strip(),
                "reason": str(value.get("reason", "")).strip(),
            }
        )
    return entries


def _unique_dispatch_entries(entries: list[dict[str, str]]) -> list[dict[str, str]]:
    unique: list[dict[str, str]] = []
    seen: set[tuple[str, str, str, str]] = set()
    for entry in entries:
        key = (
            str(entry.get("item_id", "")).strip(),
            str(entry.get("run_id", "")).strip(),
            str(entry.get("dispatch_state", "")).strip(),
            str(entry.get("reason", "")).strip(),
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(entry)
    return sorted(unique, key=lambda item: (item.get("item_id", ""), item.get("run_id", "")))


def _self_managed_summary_text(
    *,
    managed_project_registered: bool,
    active_project_selected: bool,
    blocking_run_count: int,
    recovered_run_count: int,
) -> str:
    if not managed_project_registered:
        return "AresForge self-managed project metadata is not registered in local state."
    if blocking_run_count:
        return "AresForge self-managed readiness needs operator attention for blocking dispatch run evidence."
    if recovered_run_count:
        return "AresForge self-managed readiness is inspectable; recovered dispatch runs are audited as non-blocking."
    if active_project_selected:
        return "AresForge self-managed readiness is inspectable through local read-only report flows."
    return "AresForge self-managed readiness is inspectable; select it as active when dogfooding this repo."


def _count_by(items: list[dict[str, Any]], field: str, *, empty_label: str = "unknown") -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        value = str(item.get(field, "")).strip() or empty_label
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def _report_item_closeout_eligible(item: dict[str, Any]) -> bool:
    if str(item.get("status", "")).strip() != "in_progress":
        return False
    evidence = item.get("completion_evidence", {})
    if not isinstance(evidence, dict):
        return False
    validation_results = evidence.get("validation_results", [])
    review_evidence = evidence.get("review_evidence", [])
    return bool(
        str(evidence.get("evidence_summary", "")).strip()
        and isinstance(validation_results, list)
        and any(str(value).strip() for value in validation_results)
        and str(evidence.get("diff_check_result", "")).strip()
        and isinstance(review_evidence, list)
        and any(str(value).strip() for value in review_evidence)
    )


def _item_ids(items: list[dict[str, Any]]) -> list[str]:
    return [
        str(item.get("item_id", "")).strip()
        for item in items
        if str(item.get("item_id", "")).strip()
    ]


def _latest_report_activity(items: list[dict[str, Any]], progress_rollup: dict[str, Any]) -> str:
    timestamps = [str(progress_rollup.get("latest_activity_timestamp", "")).strip()]
    for item in items:
        evidence = item.get("completion_evidence", {})
        timestamps.extend(
            [
                str(item.get("closed_at", "")).strip(),
                str(item.get("completed_at", "")).strip(),
                str(item.get("updated_at", "")).strip(),
                str(item.get("started_at", "")).strip(),
                str(item.get("created_at", "")).strip(),
                str(evidence.get("captured_at", "")).strip() if isinstance(evidence, dict) else "",
            ]
        )
    normalized = [value for value in timestamps if value]
    return max(normalized) if normalized else ""


def _reports_v1_next_safe_action(
    *,
    blockers: list[str],
    closeout_eligible_count: int,
    ready_count: int,
    total_items: int,
    foundation_next_action: str,
) -> str:
    if blockers:
        return "Review Reports v1 blockers and resolve local queue/project issues before new work."
    if closeout_eligible_count:
        return "Review closeout-eligible queue items and close them out explicitly when evidence is sufficient."
    if ready_count:
        return "Inspect readiness and explicitly start the next ready queue item when appropriate."
    if total_items == 0:
        return "Add local queue items or continue project planning before reporting progress."
    return foundation_next_action or "Review Reports v1 and continue the next operator-gated local workflow."


def _unique_list(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        normalized = str(value).strip()
        if normalized and normalized not in result:
            result.append(normalized)
    return result
