from __future__ import annotations

from datetime import UTC, datetime
import re
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.local_project_dashboard import summarize_local_project_dashboard
from aresforge.operator.local_project_readiness import inspect_local_project_readiness


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

    blockers: list[str] = []
    if not active_project_id:
        blockers.append("No active project selected.")
    if queue_summary["blocked_count"] > 0:
        blockers.append("Queue has blocked items.")
    if documentation_summary["missing_count"] > 0:
        blockers.append("Required documentation is missing.")
    if active_project_readiness and not bool(active_project_readiness.get("ok", True)):
        blockers.append("Active project readiness inspection failed.")

    warnings = sorted(set(str(item) for item in dashboard.get("warnings", []) if str(item).strip()))
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
        "validation_summary": validation_summary,
        "documentation_summary": documentation_summary,
        "blockers": blockers,
        "warnings": warnings,
        "recommended_next_action": recommended_next_action,
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
