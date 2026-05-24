from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.managed_project_registry_local import resolve_managed_project_registry_path

ACTIVE_PROJECT_DIR_RELATIVE = Path(".aresforge") / "projects"
ACTIVE_PROJECT_FILE_NAME = "active_project.json"
ACTIVE_PROJECT_SCHEMA_VERSION = "1.0"

_BOUNDARY_CONFIRMATIONS: tuple[str, ...] = (
    "Local-only active project operation.",
    "File-backed active project state.",
    "No GitHub API calls.",
    "No gh calls.",
    "No GraphQL/REST calls.",
    "No network service calls.",
    "No agent execution.",
    "No model invocation.",
)


def resolve_active_project_path(repo_root: Path, path: str | Path | None = None) -> Path:
    if path is None:
        return (repo_root / ACTIVE_PROJECT_DIR_RELATIVE / ACTIVE_PROJECT_FILE_NAME).resolve()
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = (repo_root / candidate).resolve()
    if candidate.suffix.lower() == ".json" or candidate.name.endswith(".json"):
        return candidate
    return candidate / ACTIVE_PROJECT_FILE_NAME


def inspect_active_project(
    config: AppConfig,
    *,
    path: str | Path | None = None,
) -> dict[str, Any]:
    active_path = resolve_active_project_path(config.repo_root, path)
    warnings: list[str] = []
    active_project_id = ""

    if not active_path.exists():
        warnings.append("Active project state file not found. No active project is selected.")
        return _payload(
            active_path=active_path,
            active_project_id="",
            active_project=None,
            warnings=warnings,
        )

    loaded = _load_active_project_file(active_path)
    if not loaded.get("ok", False):
        return _payload(
            active_path=active_path,
            active_project_id="",
            active_project=None,
            warnings=[str(loaded.get("message", "Active project state could not be read."))],
        )

    active_project_id = str(loaded.get("active_project_id", "")).strip()
    if not active_project_id:
        warnings.append("Active project state file exists but no active project id is selected.")
        return _payload(
            active_path=active_path,
            active_project_id="",
            active_project=None,
            warnings=warnings,
        )

    project = _find_project(config.repo_root, active_project_id, warnings)
    if project is None:
        warnings.append(f"Active project id is not present in managed project registry: {active_project_id}")

    return _payload(
        active_path=active_path,
        active_project_id=active_project_id,
        active_project=project,
        warnings=warnings,
    )


def set_active_project(
    config: AppConfig,
    *,
    project_id: str,
    path: str | Path | None = None,
) -> dict[str, Any]:
    normalized_project_id = str(project_id or "").strip()
    if not normalized_project_id:
        return {
            "ok": False,
            "local_only": True,
            "error": "invalid_active_project_payload",
            "details": {
                "message": "project_id is required.",
                "required_fields": ["project_id"],
            },
        }

    active_path = resolve_active_project_path(config.repo_root, path)
    warnings: list[str] = []
    project = _find_project(config.repo_root, normalized_project_id, warnings)
    if project is None:
        return {
            "ok": False,
            "local_only": True,
            "error": "managed_project_not_found",
            "details": {
                "message": "Project id was not found in managed project registry.",
                "project_id": normalized_project_id,
                "active_project_path": str(active_path),
                "warnings": warnings,
            },
        }

    active_path.parent.mkdir(parents=True, exist_ok=True)
    state = {
        "schema_version": ACTIVE_PROJECT_SCHEMA_VERSION,
        "active_project_id": normalized_project_id,
        "updated_at": _now_iso(),
    }
    active_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

    return _payload(
        active_path=active_path,
        active_project_id=normalized_project_id,
        active_project=project,
        warnings=warnings,
    )


def active_project_summary_for_handoff(config: AppConfig) -> dict[str, Any] | None:
    payload = inspect_active_project(config)
    return {
        "path": payload.get("active_project_path"),
        "active_project_id": payload.get("active_project_id", ""),
        "active_project_selected": payload.get("active_project_selected", False),
        "active_project_name": (payload.get("active_project") or {}).get("name", "")
        if isinstance(payload.get("active_project"), dict)
        else "",
    }


def _payload(
    *,
    active_path: Path,
    active_project_id: str,
    active_project: dict[str, Any] | None,
    warnings: list[str],
) -> dict[str, Any]:
    primary_repo = _primary_repo(active_project)
    return {
        "ok": True,
        "local_only": True,
        "active_project_path": str(active_path),
        "active_project_id": active_project_id,
        "active_project_selected": bool(active_project_id),
        "active_project": active_project,
        "active_repo_id": str(primary_repo.get("repo_id", "")).strip() if primary_repo else "",
        "active_repo": primary_repo,
        "warnings": sorted(set(warnings)),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }


def _load_active_project_file(path: Path) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "ok": False,
            "message": str(exc),
        }
    if not isinstance(raw, dict):
        return {
            "ok": False,
            "message": "Active project JSON must decode to an object.",
        }
    return {
        "ok": True,
        "active_project_id": str(raw.get("active_project_id", "")).strip(),
    }


def _find_project(repo_root: Path, project_id: str, warnings: list[str]) -> dict[str, Any] | None:
    registry_path = resolve_managed_project_registry_path(repo_root, None)
    if not registry_path.exists():
        warnings.append(f"Managed project registry not found: {registry_path}")
        return None

    try:
        raw = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        warnings.append(f"Managed project registry could not be parsed: {exc}")
        return None

    if not isinstance(raw, dict):
        warnings.append("Managed project registry has invalid schema; expected JSON object.")
        return None

    projects = raw.get("projects", [])
    if not isinstance(projects, list):
        warnings.append("Managed project registry contains non-list projects field.")
        return None

    for project in projects:
        if not isinstance(project, dict):
            continue
        if str(project.get("project_id", "")).strip() == project_id:
            return _project_view(project)
    return None


def _project_view(project: dict[str, Any]) -> dict[str, Any]:
    repos = project.get("repos", []) if isinstance(project.get("repos"), list) else []
    normalized_repos = [_repo_view(repo) for repo in repos if isinstance(repo, dict)]
    return {
        "project_id": str(project.get("project_id", "")).strip(),
        "name": str(project.get("name", "")).strip(),
        "description": str(project.get("description", "")).strip(),
        "root_path": str(project.get("root_path", "")).strip(),
        "status": str(project.get("status", "")).strip(),
        "default_branch": str(project.get("default_branch", "")).strip(),
        "tags": _normalize_str_list(project.get("tags", [])),
        "primary_repo_id": str(project.get("primary_repo_id", "")).strip(),
        "github_owner": str(project.get("github_owner", "")).strip(),
        "github_repo": str(project.get("github_repo", "")).strip(),
        "github_url": str(project.get("github_url", "")).strip(),
        "github_default_branch": str(project.get("github_default_branch", "")).strip(),
        "github_connection_status": str(project.get("github_connection_status", "")).strip(),
        "notes": str(project.get("notes", "")).strip(),
        "created_at": str(project.get("created_at", "")).strip(),
        "updated_at": str(project.get("updated_at", "")).strip(),
        "repos": normalized_repos,
        "repo_count": len(normalized_repos),
    }


def _repo_view(repo: dict[str, Any]) -> dict[str, Any]:
    return {
        "repo_id": str(repo.get("repo_id", "")).strip(),
        "name": str(repo.get("name", "")).strip(),
        "path": str(repo.get("path", "")).strip(),
        "remote_url": str(repo.get("remote_url", "")).strip(),
        "default_branch": str(repo.get("default_branch", "")).strip(),
        "role": str(repo.get("role", "")).strip(),
        "status": str(repo.get("status", "")).strip(),
        "tags": _normalize_str_list(repo.get("tags", [])),
        "github_owner": str(repo.get("github_owner", "")).strip(),
        "github_repo": str(repo.get("github_repo", "")).strip(),
        "github_url": str(repo.get("github_url", "")).strip(),
        "github_default_branch": str(repo.get("github_default_branch", "")).strip(),
        "github_connection_status": str(repo.get("github_connection_status", "")).strip(),
        "local_git_branch": str(repo.get("local_git_branch", "")).strip(),
        "local_git_head": str(repo.get("local_git_head", "")).strip(),
        "local_git_remote_url": str(repo.get("local_git_remote_url", "")).strip(),
        "local_git_status_summary": str(repo.get("local_git_status_summary", "")).strip(),
        "notes": str(repo.get("notes", "")).strip(),
        "created_at": str(repo.get("created_at", "")).strip(),
        "updated_at": str(repo.get("updated_at", "")).strip(),
    }


def _primary_repo(project: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(project, dict):
        return None
    repos = project.get("repos", [])
    if not isinstance(repos, list) or not repos:
        return None
    primary_repo_id = str(project.get("primary_repo_id", "")).strip()
    if primary_repo_id:
        for repo in repos:
            if isinstance(repo, dict) and str(repo.get("repo_id", "")).strip() == primary_repo_id:
                return repo
    for repo in repos:
        if isinstance(repo, dict) and str(repo.get("role", "")).strip() == "primary":
            return repo
    first = repos[0]
    return first if isinstance(first, dict) else None


def _normalize_str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        normalized = str(item).strip()
        if normalized and normalized not in result:
            result.append(normalized)
    return result


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()
