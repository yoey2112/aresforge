from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig

PROJECTS_DIR_RELATIVE = Path('.aresforge') / 'projects'
PROJECTS_FILE_NAME = 'projects.json'
REGISTRY_SCHEMA_VERSION = '1.0'

PROJECT_STATUSES: tuple[str, ...] = ('active', 'paused', 'archived', 'planned')
REPO_STATUSES: tuple[str, ...] = ('active', 'paused', 'archived', 'planned')
REPO_ROLES: tuple[str, ...] = (
    'primary',
    'docs',
    'app',
    'api',
    'infrastructure',
    'automation',
    'reference',
    'archive',
    'other',
)


def init_managed_project_registry(
    config: AppConfig,
    *,
    path: str | Path | None = None,
    force: bool = False,
) -> dict[str, Any]:
    registry_path = resolve_managed_project_registry_path(config.repo_root, path)
    if registry_path.exists() and not force:
        return _error(
            'managed_project_registry_exists',
            {
                'path': str(registry_path),
                'message': 'Managed project registry already exists. Re-run with --force to overwrite.',
            },
        )

    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry = _default_registry()
    _write_registry(registry_path, registry)
    return {
        'command': 'init-managed-project-registry',
        'ok': True,
        'local_only': True,
        'path': str(registry_path),
        'force': force,
        'registry': registry,
    }


def register_managed_project(
    config: AppConfig,
    *,
    project_id: str,
    name: str,
    root_path: str | Path,
    registry_path: str | Path | None = None,
    description: str | None = None,
    status: str | None = None,
    default_branch: str | None = None,
    tags: list[str] | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    if status is not None and status not in PROJECT_STATUSES:
        return _error(
            'invalid_project_status',
            {
                'status': status,
                'supported_statuses': list(PROJECT_STATUSES),
                'message': 'Invalid project status supplied.',
            },
        )

    path = resolve_managed_project_registry_path(config.repo_root, registry_path)
    loaded = _load_registry_required(path)
    if not loaded.get('ok', False):
        return loaded
    registry = loaded['registry']

    normalized_project_id = project_id.strip()
    now = _now_iso()
    projects = registry.get('projects', [])
    if not isinstance(projects, list):
        projects = []

    project = next(
        (
            item
            for item in projects
            if isinstance(item, dict) and str(item.get('project_id', '')).strip() == normalized_project_id
        ),
        None,
    )
    created = False
    if project is None:
        project = {
            'project_id': normalized_project_id,
            'name': '',
            'description': '',
            'root_path': '',
            'status': 'active',
            'default_branch': 'main',
            'tags': [],
            'repos': [],
            'notes': '',
            'created_at': now,
            'updated_at': now,
        }
        projects.append(project)
        created = True

    project['project_id'] = normalized_project_id
    project['name'] = name.strip()
    project['root_path'] = str(root_path).strip()
    if description is not None:
        project['description'] = description.strip()
    elif created:
        project['description'] = ''
    if status is not None:
        project['status'] = status
    elif created:
        project['status'] = 'active'
    if default_branch is not None:
        project['default_branch'] = default_branch.strip()
    elif created:
        project['default_branch'] = 'main'
    if tags is not None and len(tags) > 0:
        project['tags'] = _normalize_tags(tags)
    elif created:
        project['tags'] = []
    if notes is not None:
        project['notes'] = notes.strip()
    elif created:
        project['notes'] = ''

    if not isinstance(project.get('repos'), list):
        project['repos'] = []
    if not project.get('created_at'):
        project['created_at'] = now
    project['updated_at'] = now

    registry['projects'] = projects
    registry['updated_at'] = now
    _write_registry(path, registry)

    return {
        'command': 'register-managed-project',
        'ok': True,
        'local_only': True,
        'registry_path': str(path),
        'created': created,
        'project': _project_view(project),
    }


def register_managed_repo(
    config: AppConfig,
    *,
    project_id: str,
    repo_id: str,
    name: str,
    path: str | Path,
    registry_path: str | Path | None = None,
    remote_url: str | None = None,
    default_branch: str | None = None,
    role: str | None = None,
    status: str | None = None,
    tags: list[str] | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    if status is not None and status not in REPO_STATUSES:
        return _error(
            'invalid_repo_status',
            {
                'status': status,
                'supported_statuses': list(REPO_STATUSES),
                'message': 'Invalid repo status supplied.',
            },
        )
    if role is not None and role not in REPO_ROLES:
        return _error(
            'invalid_repo_role',
            {
                'role': role,
                'supported_roles': list(REPO_ROLES),
                'message': 'Invalid repo role supplied.',
            },
        )

    registry_file = resolve_managed_project_registry_path(config.repo_root, registry_path)
    loaded = _load_registry_required(registry_file)
    if not loaded.get('ok', False):
        return loaded
    registry = loaded['registry']

    normalized_project_id = project_id.strip()
    project = next(
        (
            item
            for item in registry.get('projects', [])
            if isinstance(item, dict) and str(item.get('project_id', '')).strip() == normalized_project_id
        ),
        None,
    )
    if project is None:
        return _error(
            'managed_project_not_found',
            {
                'project_id': normalized_project_id,
                'registry_path': str(registry_file),
                'message': 'Project id was not found in managed project registry. Register the project first.',
            },
        )

    repos = project.get('repos', [])
    if not isinstance(repos, list):
        repos = []

    normalized_repo_id = repo_id.strip()
    now = _now_iso()
    repo = next(
        (
            item
            for item in repos
            if isinstance(item, dict) and str(item.get('repo_id', '')).strip() == normalized_repo_id
        ),
        None,
    )
    created = False
    if repo is None:
        repo = {
            'repo_id': normalized_repo_id,
            'name': '',
            'path': '',
            'remote_url': '',
            'default_branch': 'main',
            'role': 'other',
            'status': 'active',
            'tags': [],
            'notes': '',
            'created_at': now,
            'updated_at': now,
        }
        repos.append(repo)
        created = True

    repo['repo_id'] = normalized_repo_id
    repo['name'] = name.strip()
    repo['path'] = str(path).strip()
    if remote_url is not None:
        repo['remote_url'] = remote_url.strip()
    elif created:
        repo['remote_url'] = ''
    if default_branch is not None:
        repo['default_branch'] = default_branch.strip()
    elif created:
        repo['default_branch'] = 'main'
    if role is not None:
        repo['role'] = role
    elif created:
        repo['role'] = 'other'
    if status is not None:
        repo['status'] = status
    elif created:
        repo['status'] = 'active'
    if tags is not None and len(tags) > 0:
        repo['tags'] = _normalize_tags(tags)
    elif created:
        repo['tags'] = []
    if notes is not None:
        repo['notes'] = notes.strip()
    elif created:
        repo['notes'] = ''
    if not repo.get('created_at'):
        repo['created_at'] = now
    repo['updated_at'] = now

    project['repos'] = repos
    project['updated_at'] = now
    registry['updated_at'] = now
    _write_registry(registry_file, registry)

    return {
        'command': 'register-managed-repo',
        'ok': True,
        'local_only': True,
        'registry_path': str(registry_file),
        'project_id': normalized_project_id,
        'created': created,
        'repo': _repo_view(repo),
    }


def inspect_managed_project_registry(
    config: AppConfig,
    *,
    registry_path: str | Path | None = None,
    output_format: str = 'json',
) -> dict[str, Any]:
    path = resolve_managed_project_registry_path(config.repo_root, registry_path)
    loaded = _load_registry_required(path)
    if not loaded.get('ok', False):
        return loaded
    registry = loaded['registry']
    payload = {
        'registry_path': str(path),
        'schema_version': registry.get('schema_version'),
        'updated_at': registry.get('updated_at'),
        'project_count': len(registry.get('projects', [])),
        'repo_count': _repo_count(registry),
        'projects': [_project_view(project) for project in registry.get('projects', []) if isinstance(project, dict)],
    }
    return _stdout_result(
        command='inspect-managed-project-registry',
        payload=payload,
        output_format=output_format,
        markdown=_render_registry_markdown(payload),
    )


def inspect_managed_project(
    config: AppConfig,
    *,
    project_id: str,
    registry_path: str | Path | None = None,
    output_format: str = 'json',
) -> dict[str, Any]:
    path = resolve_managed_project_registry_path(config.repo_root, registry_path)
    loaded = _load_registry_required(path)
    if not loaded.get('ok', False):
        return loaded
    normalized_project_id = project_id.strip()
    registry = loaded['registry']
    project = next(
        (
            item
            for item in registry.get('projects', [])
            if isinstance(item, dict) and str(item.get('project_id', '')).strip() == normalized_project_id
        ),
        None,
    )
    if project is None:
        return _error(
            'managed_project_not_found',
            {
                'project_id': normalized_project_id,
                'registry_path': str(path),
                'message': 'Project id was not found in managed project registry.',
            },
        )
    payload = {
        'registry_path': str(path),
        'project': _project_view(project),
    }
    return _stdout_result(
        command='inspect-managed-project',
        payload=payload,
        output_format=output_format,
        markdown=_render_project_markdown(payload),
    )


def inspect_managed_repo(
    config: AppConfig,
    *,
    project_id: str,
    repo_id: str,
    registry_path: str | Path | None = None,
    output_format: str = 'json',
) -> dict[str, Any]:
    path = resolve_managed_project_registry_path(config.repo_root, registry_path)
    loaded = _load_registry_required(path)
    if not loaded.get('ok', False):
        return loaded
    normalized_project_id = project_id.strip()
    normalized_repo_id = repo_id.strip()
    registry = loaded['registry']
    project = next(
        (
            item
            for item in registry.get('projects', [])
            if isinstance(item, dict) and str(item.get('project_id', '')).strip() == normalized_project_id
        ),
        None,
    )
    if project is None:
        return _error(
            'managed_project_not_found',
            {
                'project_id': normalized_project_id,
                'registry_path': str(path),
                'message': 'Project id was not found in managed project registry.',
            },
        )
    repo = next(
        (
            item
            for item in project.get('repos', [])
            if isinstance(item, dict) and str(item.get('repo_id', '')).strip() == normalized_repo_id
        ),
        None,
    )
    if repo is None:
        return _error(
            'managed_repo_not_found',
            {
                'project_id': normalized_project_id,
                'repo_id': normalized_repo_id,
                'registry_path': str(path),
                'message': 'Repo id was not found under the supplied project id.',
            },
        )
    payload = {
        'registry_path': str(path),
        'project_id': normalized_project_id,
        'repo': _repo_view(repo),
    }
    return _stdout_result(
        command='inspect-managed-repo',
        payload=payload,
        output_format=output_format,
        markdown=_render_repo_markdown(payload),
    )


def managed_project_registry_summary_for_handoff(config: AppConfig) -> dict[str, Any] | None:
    path = resolve_managed_project_registry_path(config.repo_root, None)
    if not path.exists():
        return None
    loaded = _load_registry_required(path)
    if not loaded.get('ok', False):
        return {
            'path': str(path),
            'error': str(loaded.get('error', 'unknown')),
        }
    registry = loaded['registry']
    projects = [project for project in registry.get('projects', []) if isinstance(project, dict)]
    return {
        'path': str(path),
        'schema_version': registry.get('schema_version'),
        'updated_at': registry.get('updated_at'),
        'project_count': len(projects),
        'repo_count': _repo_count(registry),
        'projects': [
            {
                'project_id': str(project.get('project_id', '')).strip(),
                'name': str(project.get('name', '')).strip(),
                'status': str(project.get('status', '')).strip(),
                'repo_count': len([repo for repo in project.get('repos', []) if isinstance(repo, dict)]),
            }
            for project in projects
        ],
    }


def resolve_managed_project_registry_path(repo_root: Path, path: str | Path | None) -> Path:
    if path is None:
        return (repo_root / PROJECTS_DIR_RELATIVE / PROJECTS_FILE_NAME).resolve()
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = (repo_root / candidate).resolve()
    if candidate.suffix.lower() == '.json' or candidate.name.endswith('.json'):
        return candidate
    return candidate / PROJECTS_FILE_NAME


def _default_registry() -> dict[str, Any]:
    return {
        'schema_version': REGISTRY_SCHEMA_VERSION,
        'updated_at': _now_iso(),
        'projects': [],
    }


def _load_registry_required(path: Path) -> dict[str, Any]:
    if not path.exists():
        return _error(
            'managed_project_registry_not_found',
            {
                'path': str(path),
                'message': 'Managed project registry is missing. Run init-managed-project-registry first.',
            },
        )
    try:
        raw = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as exc:
        return _error(
            'managed_project_registry_invalid_json',
            {
                'path': str(path),
                'message': str(exc),
            },
        )
    if not isinstance(raw, dict):
        return _error(
            'managed_project_registry_invalid_schema',
            {
                'path': str(path),
                'message': 'Registry JSON must decode to an object.',
            },
        )
    registry = {
        'schema_version': str(raw.get('schema_version') or REGISTRY_SCHEMA_VERSION),
        'updated_at': str(raw.get('updated_at') or _now_iso()),
        'projects': raw.get('projects') if isinstance(raw.get('projects'), list) else [],
    }
    return {
        'ok': True,
        'registry': registry,
    }


def _write_registry(path: Path, registry: dict[str, Any]) -> None:
    path.write_text(json.dumps(registry, indent=2) + '\n', encoding='utf-8')


def _normalize_tags(tags: list[str]) -> list[str]:
    result: list[str] = []
    for tag in tags:
        normalized = str(tag).strip()
        if normalized and normalized not in result:
            result.append(normalized)
    return result


def _project_view(project: dict[str, Any]) -> dict[str, Any]:
    repos = [repo for repo in project.get('repos', []) if isinstance(repo, dict)]
    return {
        'project_id': str(project.get('project_id', '')).strip(),
        'name': str(project.get('name', '')).strip(),
        'description': str(project.get('description', '')).strip(),
        'root_path': str(project.get('root_path', '')).strip(),
        'status': str(project.get('status', '')).strip(),
        'default_branch': str(project.get('default_branch', '')).strip(),
        'tags': _normalize_tags(project.get('tags', []) if isinstance(project.get('tags'), list) else []),
        'repos': [_repo_view(repo) for repo in repos],
        'notes': str(project.get('notes', '')).strip(),
        'created_at': str(project.get('created_at', '')),
        'updated_at': str(project.get('updated_at', '')),
    }


def _repo_view(repo: dict[str, Any]) -> dict[str, Any]:
    return {
        'repo_id': str(repo.get('repo_id', '')).strip(),
        'name': str(repo.get('name', '')).strip(),
        'path': str(repo.get('path', '')).strip(),
        'remote_url': str(repo.get('remote_url', '')).strip(),
        'default_branch': str(repo.get('default_branch', '')).strip(),
        'role': str(repo.get('role', '')).strip(),
        'status': str(repo.get('status', '')).strip(),
        'tags': _normalize_tags(repo.get('tags', []) if isinstance(repo.get('tags'), list) else []),
        'notes': str(repo.get('notes', '')).strip(),
        'created_at': str(repo.get('created_at', '')),
        'updated_at': str(repo.get('updated_at', '')),
    }


def _repo_count(registry: dict[str, Any]) -> int:
    total = 0
    for project in registry.get('projects', []):
        if not isinstance(project, dict):
            continue
        repos = project.get('repos', [])
        if isinstance(repos, list):
            total += len([repo for repo in repos if isinstance(repo, dict)])
    return total


def _stdout_result(command: str, payload: dict[str, Any], output_format: str, markdown: str) -> dict[str, Any]:
    fmt = output_format.lower().strip()
    if fmt not in {'json', 'markdown'}:
        return _error(
            'invalid_format',
            {
                'format': output_format,
                'supported_formats': ['json', 'markdown'],
                'message': 'Output format must be json or markdown.',
            },
        )
    return {
        'command': command,
        'ok': True,
        'local_only': True,
        'format': fmt,
        'wrote_output_file': False,
        'stdout': json.dumps(payload, indent=2) if fmt == 'json' else markdown,
        'payload': payload,
    }


def _render_registry_markdown(payload: dict[str, Any]) -> str:
    lines = [
        '# Managed Project Registry',
        '',
        f"- registry_path: {payload.get('registry_path')}",
        f"- schema_version: {payload.get('schema_version')}",
        f"- updated_at: {payload.get('updated_at')}",
        f"- project_count: {payload.get('project_count')}",
        f"- repo_count: {payload.get('repo_count')}",
        '',
        '## Projects',
    ]
    projects = payload.get('projects', [])
    if not isinstance(projects, list) or not projects:
        lines.append('- None')
        return '\n'.join(lines)
    for project in projects:
        if not isinstance(project, dict):
            continue
        lines.append(
            f"- {project.get('project_id')} | {project.get('name')} | status={project.get('status')} | repos={len(project.get('repos', []))}"
        )
    return '\n'.join(lines)


def _render_project_markdown(payload: dict[str, Any]) -> str:
    project = payload.get('project', {}) if isinstance(payload.get('project'), dict) else {}
    lines = [
        '# Managed Project Inspection',
        '',
        f"- registry_path: {payload.get('registry_path')}",
        f"- project_id: {project.get('project_id')}",
        f"- name: {project.get('name')}",
        f"- status: {project.get('status')}",
        f"- root_path: {project.get('root_path')}",
        f"- default_branch: {project.get('default_branch')}",
        '',
        '## Repos',
    ]
    repos = project.get('repos', []) if isinstance(project.get('repos'), list) else []
    if not repos:
        lines.append('- None')
        return '\n'.join(lines)
    for repo in repos:
        if not isinstance(repo, dict):
            continue
        lines.append(
            f"- {repo.get('repo_id')} | {repo.get('name')} | role={repo.get('role')} | status={repo.get('status')}"
        )
    return '\n'.join(lines)


def _render_repo_markdown(payload: dict[str, Any]) -> str:
    repo = payload.get('repo', {}) if isinstance(payload.get('repo'), dict) else {}
    return '\n'.join(
        [
            '# Managed Repo Inspection',
            '',
            f"- registry_path: {payload.get('registry_path')}",
            f"- project_id: {payload.get('project_id')}",
            f"- repo_id: {repo.get('repo_id')}",
            f"- name: {repo.get('name')}",
            f"- path: {repo.get('path')}",
            f"- role: {repo.get('role')}",
            f"- status: {repo.get('status')}",
            f"- default_branch: {repo.get('default_branch')}",
            f"- remote_url: {repo.get('remote_url')}",
        ]
    )


def _error(error: str, details: dict[str, Any]) -> dict[str, Any]:
    return {
        'ok': False,
        'local_only': True,
        'error': error,
        'details': details,
    }


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()
