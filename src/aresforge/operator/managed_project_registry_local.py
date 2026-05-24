from __future__ import annotations

import json
import re
import subprocess
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

_BOUNDARY_CONFIRMATIONS: tuple[str, ...] = (
    'Local-only managed project/repo registry operation.',
    'No GitHub API calls.',
    'No gh calls.',
    'No GraphQL/REST calls.',
    'No network service calls.',
    'GitHub link values are parsed/stored locally only.',
)

_GITHUB_HTTPS_RE = re.compile(r'^https://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$', re.IGNORECASE)
_GITHUB_SSH_RE = re.compile(r'^git@github\.com:([^/]+)/([^/]+?)(?:\.git)?$', re.IGNORECASE)


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
    primary_repo_id: str | None = None,
    github_owner: str | None = None,
    github_repo: str | None = None,
    github_url: str | None = None,
    github_default_branch: str | None = None,
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

    warnings: list[str] = []
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
        project = _default_project(normalized_project_id, now)
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
    if github_default_branch is not None:
        project['github_default_branch'] = github_default_branch.strip()

    if not isinstance(project.get('repos'), list):
        project['repos'] = []

    _ensure_project_schema_defaults(project, now)

    identity = _normalize_github_identity(
        github_url=github_url,
        github_owner=github_owner,
        github_repo=github_repo,
        warnings=warnings,
        warning_scope='project',
    )
    _apply_project_github_identity(project, identity)

    if primary_repo_id is not None:
        normalized_primary_repo_id = primary_repo_id.strip()
        if normalized_primary_repo_id:
            project['primary_repo_id'] = normalized_primary_repo_id

    _ensure_project_primary_repo(project, warnings)
    _derive_project_identity_from_primary_repo(project, warnings)
    _refresh_project_connection_status(project)

    if not project.get('created_at'):
        project['created_at'] = now
    project['updated_at'] = now

    if project.get('github_owner') and project.get('github_repo') and not project.get('primary_repo_id'):
        warnings.append(
            'Project has GitHub identity but no primary repo. Register a primary repo to complete linkage.'
        )

    if project.get('github_owner') and project.get('github_repo') and len(project.get('repos', [])) == 0:
        warnings.append(
            'Project has GitHub identity but no repos yet. Register a primary repo for explicit linkage.'
        )

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
        'warnings': sorted(set(warnings)),
        'boundary_confirmations': list(_BOUNDARY_CONFIRMATIONS),
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
    github_owner: str | None = None,
    github_repo: str | None = None,
    github_url: str | None = None,
    github_default_branch: str | None = None,
    inspect_local_git: bool = False,
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

    warnings: list[str] = []
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
        repo = _default_repo(normalized_repo_id, now)
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
    if github_default_branch is not None:
        repo['github_default_branch'] = github_default_branch.strip()

    _ensure_repo_schema_defaults(repo, now)

    identity = _normalize_github_identity(
        github_url=github_url,
        github_owner=github_owner,
        github_repo=github_repo,
        warnings=warnings,
        warning_scope='repo',
    )
    _apply_repo_github_identity(repo, identity)

    if inspect_local_git:
        git_inspection = inspect_local_git_repository(repo['path'])
        repo['local_git_remote_url'] = git_inspection.get('local_git_remote_url', '')
        repo['local_git_branch'] = git_inspection.get('local_git_branch', '')
        repo['local_git_head'] = git_inspection.get('local_git_head', '')
        repo['local_git_status_summary'] = git_inspection.get('local_git_status_summary', '')
        warnings.extend(git_inspection.get('warnings', []))

        inferred_identity = _normalize_github_identity(
            github_url=git_inspection.get('github_url'),
            github_owner=git_inspection.get('github_owner'),
            github_repo=git_inspection.get('github_repo'),
            warnings=warnings,
            warning_scope='repo_inferred_from_local_git',
        )
        if not str(repo.get('github_owner', '')).strip() and inferred_identity['github_owner']:
            repo['github_owner'] = inferred_identity['github_owner']
        if not str(repo.get('github_repo', '')).strip() and inferred_identity['github_repo']:
            repo['github_repo'] = inferred_identity['github_repo']
        if not str(repo.get('github_url', '')).strip() and inferred_identity['github_url']:
            repo['github_url'] = inferred_identity['github_url']
        if not str(repo.get('remote_url', '')).strip() and git_inspection.get('local_git_remote_url'):
            repo['remote_url'] = str(git_inspection['local_git_remote_url'])

    _refresh_repo_connection_status(repo)

    if not repo.get('created_at'):
        repo['created_at'] = now
    repo['updated_at'] = now

    project['repos'] = repos
    _ensure_project_schema_defaults(project, now)
    if str(repo.get('role', '')).strip() == 'primary':
        project['primary_repo_id'] = normalized_repo_id

    _ensure_project_primary_repo(project, warnings)
    _derive_project_identity_from_primary_repo(project, warnings)
    _refresh_project_connection_status(project)
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
        'warnings': sorted(set(warnings)),
        'boundary_confirmations': list(_BOUNDARY_CONFIRMATIONS),
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


def inspect_managed_repo_github_link(
    config: AppConfig,
    *,
    project_id: str,
    repo_id: str,
    registry_path: str | Path | None = None,
    inspect_local_git: bool = False,
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

    warnings: list[str] = []
    payload: dict[str, Any] = {
        'project_id': normalized_project_id,
        'repo_id': normalized_repo_id,
        'github_owner': str(repo.get('github_owner', '')).strip(),
        'github_repo': str(repo.get('github_repo', '')).strip(),
        'github_url': str(repo.get('github_url', '')).strip(),
        'remote_url': str(repo.get('remote_url', '')).strip(),
        'github_connection_status': str(repo.get('github_connection_status', '')).strip(),
        'warnings': [],
        'boundary_confirmations': list(_BOUNDARY_CONFIRMATIONS),
    }

    if inspect_local_git:
        local_inspection = inspect_local_git_repository(str(repo.get('path', '')).strip())
        payload['local_git_remote_url'] = local_inspection.get('local_git_remote_url', '')
        payload['local_git_branch'] = local_inspection.get('local_git_branch', '')
        payload['local_git_head'] = local_inspection.get('local_git_head', '')
        payload['local_git_status_summary'] = local_inspection.get('local_git_status_summary', '')
        warnings.extend(local_inspection.get('warnings', []))

        if not payload['github_owner'] and local_inspection.get('github_owner'):
            payload['github_owner'] = str(local_inspection.get('github_owner', '')).strip()
        if not payload['github_repo'] and local_inspection.get('github_repo'):
            payload['github_repo'] = str(local_inspection.get('github_repo', '')).strip()
        if not payload['github_url'] and local_inspection.get('github_url'):
            payload['github_url'] = str(local_inspection.get('github_url', '')).strip()

        if not payload['remote_url'] and local_inspection.get('local_git_remote_url'):
            payload['remote_url'] = str(local_inspection.get('local_git_remote_url', '')).strip()

    payload['github_connection_status'] = _github_connection_status(
        payload.get('github_owner'),
        payload.get('github_repo'),
        payload.get('github_url'),
    )
    payload['warnings'] = sorted(set(warnings))

    return _stdout_result(
        command='inspect-managed-repo-github-link',
        payload=payload,
        output_format=output_format,
        markdown=_render_repo_github_link_markdown(payload),
    )


def inspect_local_git_repository(path: str | Path) -> dict[str, Any]:
    local_path = Path(path)
    warnings: list[str] = []
    payload: dict[str, Any] = {
        'local_git_remote_url': '',
        'local_git_branch': '',
        'local_git_head': '',
        'local_git_status_summary': '',
        'github_owner': '',
        'github_repo': '',
        'github_url': '',
        'warnings': warnings,
    }

    if not local_path.exists() or not local_path.is_dir():
        warnings.append(f'Path is not a local directory: {local_path}')
        payload['local_git_status_summary'] = 'path_not_directory'
        return payload

    remote_result = _run_git_command(local_path, ['remote', 'get-url', 'origin'])
    if remote_result['ok']:
        payload['local_git_remote_url'] = remote_result['stdout']
        parsed = _parse_github_url(remote_result['stdout'])
        if parsed['ok']:
            payload['github_owner'] = parsed['github_owner']
            payload['github_repo'] = parsed['github_repo']
            payload['github_url'] = parsed['github_url']
        else:
            warnings.extend(parsed['warnings'])
    else:
        warnings.append('Could not read origin remote URL via local git command.')

    branch_result = _run_git_command(local_path, ['branch', '--show-current'])
    if branch_result['ok']:
        payload['local_git_branch'] = branch_result['stdout']
    else:
        warnings.append('Could not read current local git branch.')

    head_result = _run_git_command(local_path, ['rev-parse', 'HEAD'])
    if head_result['ok']:
        payload['local_git_head'] = head_result['stdout']
    else:
        warnings.append('Could not read local git HEAD revision.')

    status_result = _run_git_command(local_path, ['status', '--short'])
    if status_result['ok']:
        lines = [line for line in status_result['stdout'].splitlines() if line.strip()]
        if not lines:
            payload['local_git_status_summary'] = 'clean'
        else:
            preview = '; '.join(lines[:3])
            payload['local_git_status_summary'] = f'{len(lines)} change(s): {preview}'
    else:
        warnings.append('Could not read local git status summary.')

    if not remote_result['ok'] and not branch_result['ok'] and not head_result['ok'] and not status_result['ok']:
        warnings.append('Path appears to be non-git or inaccessible for local git inspection.')
        if not payload['local_git_status_summary']:
            payload['local_git_status_summary'] = 'non_git_or_unavailable'

    return payload


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
                'github_connection_status': str(project.get('github_connection_status', '')).strip(),
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


def _default_project(project_id: str, now: str) -> dict[str, Any]:
    return {
        'project_id': project_id,
        'name': '',
        'description': '',
        'root_path': '',
        'status': 'active',
        'default_branch': 'main',
        'tags': [],
        'repos': [],
        'primary_repo_id': '',
        'github_owner': '',
        'github_repo': '',
        'github_url': '',
        'github_default_branch': '',
        'github_connection_status': 'unlinked',
        'notes': '',
        'created_at': now,
        'updated_at': now,
    }


def _default_repo(repo_id: str, now: str) -> dict[str, Any]:
    return {
        'repo_id': repo_id,
        'name': '',
        'path': '',
        'remote_url': '',
        'default_branch': 'main',
        'role': 'other',
        'status': 'active',
        'tags': [],
        'github_owner': '',
        'github_repo': '',
        'github_url': '',
        'github_default_branch': '',
        'github_connection_status': 'unlinked',
        'local_git_branch': '',
        'local_git_head': '',
        'local_git_remote_url': '',
        'local_git_status_summary': '',
        'notes': '',
        'created_at': now,
        'updated_at': now,
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
    projects_raw = raw.get('projects') if isinstance(raw.get('projects'), list) else []
    now = _now_iso()
    projects: list[dict[str, Any]] = []
    for project in projects_raw:
        if not isinstance(project, dict):
            continue
        _ensure_project_schema_defaults(project, now)
        repos = project.get('repos', [])
        if not isinstance(repos, list):
            repos = []
        fixed_repos: list[dict[str, Any]] = []
        for repo in repos:
            if not isinstance(repo, dict):
                continue
            _ensure_repo_schema_defaults(repo, now)
            fixed_repos.append(repo)
        project['repos'] = fixed_repos
        _derive_project_identity_from_primary_repo(project, [])
        _refresh_project_connection_status(project)
        projects.append(project)

    registry = {
        'schema_version': str(raw.get('schema_version') or REGISTRY_SCHEMA_VERSION),
        'updated_at': str(raw.get('updated_at') or now),
        'projects': projects,
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


def _normalize_github_identity(
    *,
    github_url: str | None,
    github_owner: str | None,
    github_repo: str | None,
    warnings: list[str],
    warning_scope: str,
) -> dict[str, str]:
    owner = str(github_owner or '').strip()
    repo = str(github_repo or '').strip()
    url = str(github_url or '').strip()

    if url:
        parsed = _parse_github_url(url)
        if parsed['ok']:
            parsed_owner = parsed['github_owner']
            parsed_repo = parsed['github_repo']
            parsed_url = parsed['github_url']
            if owner and owner != parsed_owner:
                warnings.append(
                    f'{warning_scope} github_owner differs from github_url owner; keeping explicit github_owner value.'
                )
            if repo and repo != parsed_repo:
                warnings.append(
                    f'{warning_scope} github_repo differs from github_url repo; keeping explicit github_repo value.'
                )
            if not owner:
                owner = parsed_owner
            if not repo:
                repo = parsed_repo
            url = parsed_url
        else:
            warnings.extend(parsed['warnings'])

    if owner and repo and not url:
        url = f'https://github.com/{owner}/{repo}'

    if (owner and not repo) or (repo and not owner):
        warnings.append(f'{warning_scope} GitHub identity is incomplete; both github_owner and github_repo are required.')

    return {
        'github_owner': owner,
        'github_repo': repo,
        'github_url': url,
    }


def _parse_github_url(url: str) -> dict[str, Any]:
    text = str(url).strip()
    warnings: list[str] = []
    if not text:
        return {
            'ok': False,
            'github_owner': '',
            'github_repo': '',
            'github_url': '',
            'warnings': ['GitHub URL is empty.'],
        }

    match = _GITHUB_HTTPS_RE.match(text)
    if match is None:
        match = _GITHUB_SSH_RE.match(text)

    if match is None:
        warnings.append('Provided URL is not a supported GitHub HTTPS/SSH remote format.')
        return {
            'ok': False,
            'github_owner': '',
            'github_repo': '',
            'github_url': text,
            'warnings': warnings,
        }

    owner = match.group(1).strip()
    repo = match.group(2).strip()
    normalized_url = f'https://github.com/{owner}/{repo}'
    return {
        'ok': True,
        'github_owner': owner,
        'github_repo': repo,
        'github_url': normalized_url,
        'warnings': [],
    }


def _apply_project_github_identity(project: dict[str, Any], identity: dict[str, str]) -> None:
    if identity['github_owner']:
        project['github_owner'] = identity['github_owner']
    if identity['github_repo']:
        project['github_repo'] = identity['github_repo']
    if identity['github_url']:
        project['github_url'] = identity['github_url']


def _apply_repo_github_identity(repo: dict[str, Any], identity: dict[str, str]) -> None:
    if identity['github_owner']:
        repo['github_owner'] = identity['github_owner']
    if identity['github_repo']:
        repo['github_repo'] = identity['github_repo']
    if identity['github_url']:
        repo['github_url'] = identity['github_url']


def _ensure_project_schema_defaults(project: dict[str, Any], now: str) -> None:
    project.setdefault('description', '')
    project.setdefault('root_path', '')
    project.setdefault('status', 'active')
    project.setdefault('default_branch', 'main')
    project['tags'] = _normalize_tags(project.get('tags', []) if isinstance(project.get('tags'), list) else [])
    if not isinstance(project.get('repos'), list):
        project['repos'] = []
    project.setdefault('primary_repo_id', '')
    project.setdefault('github_owner', '')
    project.setdefault('github_repo', '')
    project.setdefault('github_url', '')
    project.setdefault('github_default_branch', '')
    project.setdefault('github_connection_status', 'unlinked')
    project.setdefault('notes', '')
    project.setdefault('created_at', now)
    project.setdefault('updated_at', now)


def _ensure_repo_schema_defaults(repo: dict[str, Any], now: str) -> None:
    repo.setdefault('name', '')
    repo.setdefault('path', '')
    repo.setdefault('remote_url', '')
    repo.setdefault('default_branch', 'main')
    repo.setdefault('role', 'other')
    repo.setdefault('status', 'active')
    repo['tags'] = _normalize_tags(repo.get('tags', []) if isinstance(repo.get('tags'), list) else [])
    repo.setdefault('github_owner', '')
    repo.setdefault('github_repo', '')
    repo.setdefault('github_url', '')
    repo.setdefault('github_default_branch', '')
    repo.setdefault('github_connection_status', 'unlinked')
    repo.setdefault('local_git_branch', '')
    repo.setdefault('local_git_head', '')
    repo.setdefault('local_git_remote_url', '')
    repo.setdefault('local_git_status_summary', '')
    repo.setdefault('notes', '')
    repo.setdefault('created_at', now)
    repo.setdefault('updated_at', now)
    _refresh_repo_connection_status(repo)


def _ensure_project_primary_repo(project: dict[str, Any], warnings: list[str]) -> None:
    repos = project.get('repos', []) if isinstance(project.get('repos'), list) else []
    if not repos:
        project['primary_repo_id'] = ''
        return

    existing_primary_repo_id = str(project.get('primary_repo_id', '')).strip()
    if existing_primary_repo_id and any(
        isinstance(repo, dict) and str(repo.get('repo_id', '')).strip() == existing_primary_repo_id
        for repo in repos
    ):
        return

    role_primary = next(
        (
            repo
            for repo in repos
            if isinstance(repo, dict)
            and str(repo.get('repo_id', '')).strip()
            and str(repo.get('role', '')).strip() == 'primary'
        ),
        None,
    )
    if role_primary is not None:
        project['primary_repo_id'] = str(role_primary.get('repo_id', '')).strip()
        return

    first_repo = next((repo for repo in repos if isinstance(repo, dict)), None)
    if first_repo is not None:
        project['primary_repo_id'] = str(first_repo.get('repo_id', '')).strip()
        warnings.append('Project had repos but no valid primary repo id. Assigned first repo as primary.')


def _derive_project_identity_from_primary_repo(project: dict[str, Any], warnings: list[str]) -> None:
    repos = project.get('repos', []) if isinstance(project.get('repos'), list) else []
    primary_repo_id = str(project.get('primary_repo_id', '')).strip()
    if not primary_repo_id:
        return

    primary_repo = next(
        (
            repo
            for repo in repos
            if isinstance(repo, dict) and str(repo.get('repo_id', '')).strip() == primary_repo_id
        ),
        None,
    )
    if primary_repo is None:
        return

    if str(primary_repo.get('role', '')).strip() != 'primary':
        warnings.append('Primary repo id points to a repo whose role is not primary.')

    if not str(project.get('github_owner', '')).strip() and str(primary_repo.get('github_owner', '')).strip():
        project['github_owner'] = str(primary_repo.get('github_owner', '')).strip()
    if not str(project.get('github_repo', '')).strip() and str(primary_repo.get('github_repo', '')).strip():
        project['github_repo'] = str(primary_repo.get('github_repo', '')).strip()
    if not str(project.get('github_url', '')).strip() and str(primary_repo.get('github_url', '')).strip():
        project['github_url'] = str(primary_repo.get('github_url', '')).strip()


def _refresh_project_connection_status(project: dict[str, Any]) -> None:
    project['github_connection_status'] = _github_connection_status(
        project.get('github_owner'),
        project.get('github_repo'),
        project.get('github_url'),
    )


def _refresh_repo_connection_status(repo: dict[str, Any]) -> None:
    repo['github_connection_status'] = _github_connection_status(
        repo.get('github_owner'),
        repo.get('github_repo'),
        repo.get('github_url'),
    )


def _github_connection_status(github_owner: Any, github_repo: Any, github_url: Any) -> str:
    owner = str(github_owner or '').strip()
    repo = str(github_repo or '').strip()
    url = str(github_url or '').strip()
    if owner and repo and url:
        return 'linked'
    if owner or repo or url:
        return 'partial'
    return 'unlinked'


def _run_git_command(path: Path, args: list[str]) -> dict[str, Any]:
    command = ['git', '-C', str(path), *args]
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (subprocess.SubprocessError, OSError):
        return {'ok': False, 'stdout': '', 'stderr': ''}

    if completed.returncode != 0:
        return {
            'ok': False,
            'stdout': str(completed.stdout or '').strip(),
            'stderr': str(completed.stderr or '').strip(),
        }
    return {
        'ok': True,
        'stdout': str(completed.stdout or '').strip(),
        'stderr': str(completed.stderr or '').strip(),
    }


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
        'primary_repo_id': str(project.get('primary_repo_id', '')).strip(),
        'github_owner': str(project.get('github_owner', '')).strip(),
        'github_repo': str(project.get('github_repo', '')).strip(),
        'github_url': str(project.get('github_url', '')).strip(),
        'github_default_branch': str(project.get('github_default_branch', '')).strip(),
        'github_connection_status': str(project.get('github_connection_status', '')).strip(),
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
        'github_owner': str(repo.get('github_owner', '')).strip(),
        'github_repo': str(repo.get('github_repo', '')).strip(),
        'github_url': str(repo.get('github_url', '')).strip(),
        'github_default_branch': str(repo.get('github_default_branch', '')).strip(),
        'github_connection_status': str(repo.get('github_connection_status', '')).strip(),
        'local_git_branch': str(repo.get('local_git_branch', '')).strip(),
        'local_git_head': str(repo.get('local_git_head', '')).strip(),
        'local_git_remote_url': str(repo.get('local_git_remote_url', '')).strip(),
        'local_git_status_summary': str(repo.get('local_git_status_summary', '')).strip(),
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
            f"- {project.get('project_id')} | {project.get('name')} | status={project.get('status')} | github={project.get('github_connection_status')} | repos={len(project.get('repos', []))}"
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
        f"- primary_repo_id: {project.get('primary_repo_id')}",
        f"- github_owner: {project.get('github_owner')}",
        f"- github_repo: {project.get('github_repo')}",
        f"- github_url: {project.get('github_url')}",
        f"- github_connection_status: {project.get('github_connection_status')}",
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
            f"- {repo.get('repo_id')} | {repo.get('name')} | role={repo.get('role')} | status={repo.get('status')} | github={repo.get('github_connection_status')}"
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
            f"- github_owner: {repo.get('github_owner')}",
            f"- github_repo: {repo.get('github_repo')}",
            f"- github_url: {repo.get('github_url')}",
            f"- github_connection_status: {repo.get('github_connection_status')}",
            f"- local_git_branch: {repo.get('local_git_branch')}",
            f"- local_git_head: {repo.get('local_git_head')}",
            f"- local_git_remote_url: {repo.get('local_git_remote_url')}",
            f"- local_git_status_summary: {repo.get('local_git_status_summary')}",
        ]
    )


def _render_repo_github_link_markdown(payload: dict[str, Any]) -> str:
    warnings = payload.get('warnings', []) if isinstance(payload.get('warnings'), list) else []
    lines = [
        '# Managed Repo GitHub Link Inspection',
        '',
        f"- project_id: {payload.get('project_id')}",
        f"- repo_id: {payload.get('repo_id')}",
        f"- github_owner: {payload.get('github_owner')}",
        f"- github_repo: {payload.get('github_repo')}",
        f"- github_url: {payload.get('github_url')}",
        f"- remote_url: {payload.get('remote_url')}",
        f"- local_git_remote_url: {payload.get('local_git_remote_url', '')}",
        f"- local_git_branch: {payload.get('local_git_branch', '')}",
        f"- local_git_head: {payload.get('local_git_head', '')}",
        f"- github_connection_status: {payload.get('github_connection_status')}",
        '',
        '## Warnings',
    ]
    if warnings:
        lines.extend(f'- {warning}' for warning in warnings)
    else:
        lines.append('- None')
    lines.extend(['', '## Boundary Confirmations'])
    lines.extend(f"- {item}" for item in payload.get('boundary_confirmations', []))
    return '\n'.join(lines)


def _error(error: str, details: dict[str, Any]) -> dict[str, Any]:
    return {
        'ok': False,
        'local_only': True,
        'error': error,
        'details': details,
    }


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()
