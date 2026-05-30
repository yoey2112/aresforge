from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.local_active_project import inspect_active_project
from aresforge.operator.local_project_queue import inspect_project_queue
from aresforge.operator.local_project_readiness import inspect_local_project_readiness
from aresforge.operator.local_project_report import inspect_local_project_report
from aresforge.operator.managed_project_registry_local import inspect_managed_project

_BOUNDARY_CONFIRMATIONS: tuple[str, ...] = (
    "Local-only self-managed project review.",
    "Read-only local project, queue, docs, and git metadata inspection.",
    "No queue mutation performed.",
    "No project registry mutation performed.",
    "No GitHub API calls.",
    "No gh calls.",
    "No network service calls.",
    "No agent execution.",
    "No Codex execution.",
    "No local LLM execution.",
)

_SOURCE_DOCS: tuple[str, ...] = (
    "docs/context/BUILD_STATE.md",
    "docs/context/AGENT_CONTEXT.md",
    "docs/roadmap/ROADMAP.md",
    "docs/operator/LOCAL_OPERATOR_USAGE.md",
    "docs/architecture/RUNNABLE_SKELETON.md",
)


def inspect_self_managed_project(
    config: AppConfig,
    *,
    project_id: str,
    output_format: str = "markdown",
) -> dict[str, Any]:
    normalized_project_id = str(project_id or "").strip()
    if not normalized_project_id:
        return _error("invalid_project_id", "project_id is required.")

    managed = inspect_managed_project(config, project_id=normalized_project_id, output_format="json")
    active = inspect_active_project(config)
    readiness = inspect_local_project_readiness(config, project_id=normalized_project_id)
    local_report = inspect_local_project_report(config)
    queue = inspect_project_queue(config, project_id=normalized_project_id, output_format="json")

    project = _payload_project(managed)
    primary_repo = _primary_repo(project)
    queue_payload = queue.get("payload", {}) if isinstance(queue.get("payload"), dict) else {}
    queue_items = queue_payload.get("work_items", []) if isinstance(queue_payload.get("work_items"), list) else []
    queue_counts = _queue_counts(queue_items)
    docs = _doc_status(config.repo_root)
    branch = _current_branch(config.repo_root)
    active_milestone = str((local_report.get("roadmap_summary") or {}).get("active_milestone", "")).strip()
    next_item = _next_recommended_item(queue_items)
    gaps = _gaps(
        project_id=normalized_project_id,
        project=project,
        primary_repo=primary_repo,
        active_payload=active,
        readiness=readiness,
        branch=branch,
        active_milestone=active_milestone,
        queue_items=queue_items,
        docs=docs,
    )
    warnings = _unique_list(
        [
            *[str(item).strip() for item in managed.get("warnings", []) if str(item).strip()],
            *[str(item).strip() for item in active.get("warnings", []) if str(item).strip()],
            *[str(item).strip() for item in readiness.get("warnings", []) if str(item).strip()],
            *[str(item).strip() for item in local_report.get("warnings", []) if str(item).strip()],
            *gaps,
        ]
    )
    blockers = _unique_list(
        [
            *[str(item).strip() for item in readiness.get("blockers", []) if str(item).strip()],
            *[str(item).strip() for item in local_report.get("blockers", []) if str(item).strip()],
        ]
    )

    payload = {
        "report_type": "self_managed_project_review",
        "generated_at": datetime.now(UTC).isoformat(),
        "local_only": True,
        "read_only": True,
        "project_id": normalized_project_id,
        "project_name": str(project.get("name", "")).strip(),
        "project_status": str(project.get("status", "")).strip(),
        "self_managed": normalized_project_id == "aresforge",
        "active_project": {
            "active_project_selected": bool(active.get("active_project_selected", False)),
            "active_project_id": str(active.get("active_project_id", "")).strip(),
            "matches_requested_project": str(active.get("active_project_id", "")).strip() == normalized_project_id,
        },
        "repo_identity": {
            "repo_id": str(primary_repo.get("repo_id", "")).strip(),
            "repo_path": str(primary_repo.get("path", "")).strip(),
            "registered_default_branch": str(primary_repo.get("default_branch", "")).strip()
            or str(project.get("default_branch", "")).strip(),
            "branch": branch,
            "path_matches_workspace": _same_path(primary_repo.get("path", ""), config.repo_root),
        },
        "roadmap": {
            "active_milestone": active_milestone,
            "roadmap_doc_exists": bool((local_report.get("roadmap_summary") or {}).get("roadmap_doc_exists", False)),
            "stale_or_missing_active_milestone": not bool(active_milestone),
        },
        "queue": {
            "item_count": len(queue_items),
            "counts_by_status": queue_counts,
            "next_recommended_item": next_item,
            "m103_item_status": _item_status(queue_items, "m103-aresforge-self-managed-project-seed-review"),
        },
        "docs": docs,
        "readiness": {
            "status": _readiness_status(gaps=gaps, blockers=blockers),
            "local_project_readiness_status": str(readiness.get("readiness_status", "")).strip(),
            "local_project_report_status": str((local_report.get("validation_summary") or {}).get("overall_status", "")).strip(),
            "gaps": gaps,
            "blockers": blockers,
            "warnings": warnings,
        },
        "unsafe_execution_assumptions": {
            "automatic_next_item_execution_allowed": False,
            "agent_execution_allowed": False,
            "codex_execution_allowed": False,
            "local_llm_execution_allowed": False,
            "github_api_allowed": False,
            "gh_allowed": False,
            "external_network_allowed": False,
        },
        "next_safe_action": _next_safe_action(gaps=gaps, blockers=blockers, next_item=next_item),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }
    return _stdout_result(
        command="inspect-self-managed-project",
        payload=payload,
        output_format=output_format,
        markdown=_render_markdown(payload),
    )


def _payload_project(result: dict[str, Any]) -> dict[str, Any]:
    payload = result.get("payload", {}) if isinstance(result.get("payload"), dict) else {}
    project = payload.get("project", {}) if isinstance(payload.get("project"), dict) else {}
    return project


def _primary_repo(project: dict[str, Any]) -> dict[str, Any]:
    repos = project.get("repos", []) if isinstance(project.get("repos"), list) else []
    primary_repo_id = str(project.get("primary_repo_id", "")).strip()
    for repo in repos:
        if isinstance(repo, dict) and primary_repo_id and str(repo.get("repo_id", "")).strip() == primary_repo_id:
            return repo
    for repo in repos:
        if isinstance(repo, dict) and str(repo.get("role", "")).strip() == "primary":
            return repo
    return repos[0] if repos and isinstance(repos[0], dict) else {}


def _queue_counts(items: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        status = str(item.get("status", "")).strip() or "unknown"
        counts[status] = counts.get(status, 0) + 1
    return dict(sorted(counts.items()))


def _next_recommended_item(items: list[dict[str, Any]]) -> dict[str, str]:
    for status in ("ready", "proposed", "in_progress"):
        candidates = [
            item for item in items
            if str(item.get("status", "")).strip() == status and str(item.get("item_id", "")).strip()
        ]
        if candidates:
            item = sorted(candidates, key=lambda value: str(value.get("item_id", "")).strip())[0]
            return {
                "item_id": str(item.get("item_id", "")).strip(),
                "title": str(item.get("title", "")).strip(),
                "status": status,
            }
    return {"item_id": "", "title": "", "status": ""}


def _doc_status(repo_root: Path) -> dict[str, Any]:
    docs: list[dict[str, Any]] = []
    missing: list[str] = []
    for rel_path in _SOURCE_DOCS:
        exists = (repo_root / rel_path).exists()
        docs.append({"path": rel_path, "exists": exists})
        if not exists:
            missing.append(rel_path)
    return {
        "required_docs": docs,
        "missing_docs": missing,
        "docs_ready": not missing,
    }


def _current_branch(repo_root: Path) -> str:
    head_path = repo_root / ".git" / "HEAD"
    try:
        text = head_path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""
    prefix = "ref: refs/heads/"
    if text.startswith(prefix):
        return text[len(prefix):].strip()
    return "detached" if text else ""


def _gaps(
    *,
    project_id: str,
    project: dict[str, Any],
    primary_repo: dict[str, Any],
    active_payload: dict[str, Any],
    readiness: dict[str, Any],
    branch: str,
    active_milestone: str,
    queue_items: list[dict[str, Any]],
    docs: dict[str, Any],
) -> list[str]:
    gaps: list[str] = []
    if not project:
        gaps.append(f"Managed project metadata missing for {project_id}.")
    if str(active_payload.get("active_project_id", "")).strip() != project_id:
        gaps.append("Requested project is not the selected active project.")
    if not primary_repo:
        gaps.append("No primary repo metadata is registered.")
    if not str(primary_repo.get("path", "")).strip():
        gaps.append("Primary repo path is missing.")
    if not branch:
        gaps.append("Current local git branch could not be read.")
    if branch and str(primary_repo.get("default_branch", "")).strip() and branch != str(primary_repo.get("default_branch", "")).strip():
        gaps.append("Current local branch differs from registered default branch.")
    if not active_milestone:
        gaps.append("Roadmap has no explicit active milestone marker.")
    if not queue_items:
        gaps.append("No queue items are registered for the project.")
    if not bool(docs.get("docs_ready", False)):
        gaps.append("Required source-of-truth docs are missing.")
    if str(readiness.get("readiness_status", "")).strip() not in {"ready", ""}:
        gaps.append("Local project readiness is not ready.")
    return _unique_list(gaps)


def _item_status(items: list[dict[str, Any]], item_id: str) -> str:
    for item in items:
        if str(item.get("item_id", "")).strip() == item_id:
            return str(item.get("status", "")).strip()
    return "missing"


def _readiness_status(*, gaps: list[str], blockers: list[str]) -> str:
    if blockers:
        return "blocked"
    if gaps:
        return "needs_attention"
    return "ready"


def _next_safe_action(*, gaps: list[str], blockers: list[str], next_item: dict[str, str]) -> str:
    if blockers:
        return "Resolve local metadata blockers before using this project for self-managed workflows."
    if gaps:
        return "Review self-managed project gaps and apply safe docs/data corrections before M104 batch planning."
    item_id = str(next_item.get("item_id", "")).strip()
    if item_id:
        return f"Review queue item {item_id} as the next local operator-gated action."
    return "Add or review local queue items before planning the next batch."


def _same_path(path_value: Any, repo_root: Path) -> bool:
    candidate = str(path_value or "").strip()
    if not candidate:
        return False
    try:
        return Path(candidate).resolve() == repo_root.resolve()
    except OSError:
        return False


def _unique_list(values: list[str]) -> list[str]:
    return sorted({value for value in values if value})


def _stdout_result(command: str, payload: dict[str, Any], output_format: str, markdown: str) -> dict[str, Any]:
    fmt = str(output_format or "markdown").lower().strip()
    if fmt not in {"json", "markdown"}:
        return _error("invalid_format", "Output format must be json or markdown.")
    return {
        "command": command,
        "ok": True,
        "local_only": True,
        "read_only": True,
        "format": fmt,
        "wrote_output_file": False,
        "stdout": json.dumps(payload, indent=2) if fmt == "json" else markdown,
        "payload": payload,
    }


def _error(code: str, message: str) -> dict[str, Any]:
    return {
        "command": "inspect-self-managed-project",
        "ok": False,
        "local_only": True,
        "read_only": True,
        "error": code,
        "details": {"message": message},
    }


def _render_markdown(payload: dict[str, Any]) -> str:
    readiness = payload.get("readiness", {}) if isinstance(payload.get("readiness"), dict) else {}
    repo = payload.get("repo_identity", {}) if isinstance(payload.get("repo_identity"), dict) else {}
    queue = payload.get("queue", {}) if isinstance(payload.get("queue"), dict) else {}
    next_item = queue.get("next_recommended_item", {}) if isinstance(queue.get("next_recommended_item"), dict) else {}
    lines = [
        "# Self-Managed Project Review",
        "",
        f"- project_id: {payload.get('project_id')}",
        f"- project_name: {payload.get('project_name')}",
        f"- readiness: {readiness.get('status')}",
        f"- repo_path: {repo.get('repo_path')}",
        f"- branch: {repo.get('branch')}",
        f"- active_milestone: {payload.get('roadmap', {}).get('active_milestone') if isinstance(payload.get('roadmap'), dict) else ''}",
        f"- queue_items: {queue.get('item_count')}",
        f"- next_recommended_item: {next_item.get('item_id', '')} ({next_item.get('status', '')})",
        "",
        "## Gaps",
    ]
    gaps = readiness.get("gaps", [])
    if isinstance(gaps, list) and gaps:
        lines.extend(f"- {gap}" for gap in gaps)
    else:
        lines.append("- None")
    lines.extend(["", f"- next_safe_action: {payload.get('next_safe_action')}"])
    return "\n".join(lines)
