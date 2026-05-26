from __future__ import annotations

from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.local_active_project import inspect_active_project
from aresforge.operator.managed_project_registry_local import (
    inspect_managed_project,
    inspect_managed_project_registry,
)

_BOUNDARY_CONFIRMATIONS: tuple[str, ...] = (
    "Local-only project readiness inspection.",
    "Read-only local state inspection.",
    "No GitHub API calls.",
    "No gh calls.",
    "No network service calls.",
    "No mutations performed.",
)


def list_local_projects(config: AppConfig) -> dict[str, Any]:
    registry_result = inspect_managed_project_registry(config, output_format="json")
    active_payload = inspect_active_project(config)
    active_project_id = str(active_payload.get("active_project_id", "")).strip()

    projects: list[dict[str, Any]] = []
    warnings: list[str] = []
    if not bool(registry_result.get("ok", False)):
        warnings.append(str(registry_result.get("details", {}).get("message", "Managed project registry unavailable.")))
    else:
        payload = registry_result.get("payload", {})
        raw_projects = payload.get("projects", []) if isinstance(payload, dict) else []
        for project in sorted(raw_projects, key=lambda item: str((item or {}).get("project_id", ""))):
            if not isinstance(project, dict):
                continue
            primary_repo = _primary_repo(project)
            projects.append(
                {
                    "project_id": str(project.get("project_id", "")).strip(),
                    "project_name": str(project.get("name", "")).strip(),
                    "is_active": str(project.get("project_id", "")).strip() == active_project_id,
                    "repo_path": str((primary_repo or {}).get("path", "")).strip(),
                    "local_path": str(project.get("root_path", "")).strip(),
                    "readiness_status": _project_readiness_status(project),
                }
            )

    return {
        "ok": True,
        "local_only": True,
        "project_count": len(projects),
        "active_project_id": active_project_id,
        "projects": projects,
        "warnings": sorted(set(warnings + list(active_payload.get("warnings", [])))),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }


def inspect_local_project_readiness(config: AppConfig, *, project_id: str) -> dict[str, Any]:
    normalized_project_id = str(project_id or "").strip()
    if not normalized_project_id:
        return {
            "ok": False,
            "local_only": True,
            "error": "invalid_project_id",
            "details": {
                "message": "project_id is required.",
            },
        }

    managed = inspect_managed_project(config, project_id=normalized_project_id, output_format="json")
    active_payload = inspect_active_project(config)
    active_project_id = str(active_payload.get("active_project_id", "")).strip()
    is_active = normalized_project_id == active_project_id

    if not bool(managed.get("ok", False)):
        return {
            "ok": False,
            "local_only": True,
            "error": "managed_project_not_found",
            "project_id": normalized_project_id,
            "project_name": "",
            "is_active": is_active,
            "repo_path": "",
            "local_path": "",
            "readiness_status": "not_found",
            "readiness_summary": "Project was not found in local managed project registry.",
            "blockers": [f"Project not found: {normalized_project_id}"],
            "warnings": sorted(set(list(active_payload.get("warnings", [])))),
            "next_safe_action": "Register the project in local managed project registry first.",
            "artifact_summary": _artifact_summary(config),
            "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
        }

    payload = managed.get("payload", {})
    project = payload.get("project", {}) if isinstance(payload, dict) else {}
    repos = project.get("repos", []) if isinstance(project, dict) else []
    primary_repo = _primary_repo(project) if isinstance(project, dict) else None

    blockers: list[str] = []
    warnings: list[str] = list(active_payload.get("warnings", []))
    if not repos:
        blockers.append("No repos registered for this project.")
    if not str(project.get("root_path", "")).strip():
        blockers.append("Project root_path is missing.")
    if repos and primary_repo is None:
        warnings.append("Project has repos but no primary repo could be resolved.")

    readiness_status = "ready" if not blockers else "needs_attention"
    next_safe_action = (
        "Continue local planning workflows for this project."
        if readiness_status == "ready"
        else "Register/repair local project metadata and repo linkage."
    )

    return {
        "ok": True,
        "local_only": True,
        "project_id": str(project.get("project_id", "")).strip(),
        "project_name": str(project.get("name", "")).strip(),
        "is_active": is_active,
        "repo_path": str((primary_repo or {}).get("path", "")).strip(),
        "local_path": str(project.get("root_path", "")).strip(),
        "readiness_status": readiness_status,
        "readiness_summary": _readiness_summary(readiness_status, blockers),
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "next_safe_action": next_safe_action,
        "artifact_summary": _artifact_summary(config),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }


def _project_readiness_status(project: dict[str, Any]) -> str:
    repos = project.get("repos", []) if isinstance(project.get("repos"), list) else []
    if not str(project.get("root_path", "")).strip():
        return "needs_attention"
    if not repos:
        return "needs_attention"
    return "ready"


def _readiness_summary(readiness_status: str, blockers: list[str]) -> str:
    if readiness_status == "ready":
        return "Local project metadata and primary repo linkage are present."
    return f"Local project needs attention ({len(blockers)} blocker(s))."


def _primary_repo(project: dict[str, Any]) -> dict[str, Any] | None:
    repos = project.get("repos", []) if isinstance(project.get("repos"), list) else []
    primary_repo_id = str(project.get("primary_repo_id", "")).strip()
    if primary_repo_id:
        for repo in repos:
            if isinstance(repo, dict) and str(repo.get("repo_id", "")).strip() == primary_repo_id:
                return repo
    for repo in repos:
        if isinstance(repo, dict) and str(repo.get("role", "")).strip() == "primary":
            return repo
    if repos and isinstance(repos[0], dict):
        return repos[0]
    return None


def _artifact_summary(config: AppConfig) -> dict[str, Any]:
    evidence_dir = config.evidence_dir
    handoff_dir = config.codex_handoffs_dir
    return {
        "evidence_dir": str(evidence_dir),
        "handoff_dir": str(handoff_dir),
        "latest_evidence_artifact": _latest_artifact(evidence_dir),
        "latest_handoff_artifact": _latest_artifact(handoff_dir),
    }


def _latest_artifact(path: Path) -> str | None:
    if not path.exists() or not path.is_dir():
        return None
    latest: Path | None = None
    latest_mtime: float = -1
    for candidate in path.rglob("*"):
        if not candidate.is_file():
            continue
        try:
            mtime = candidate.stat().st_mtime
        except OSError:
            continue
        if mtime > latest_mtime:
            latest = candidate
            latest_mtime = mtime
    return str(latest) if latest is not None else None
