from __future__ import annotations

import json
import subprocess
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig

STATE_DIR_RELATIVE = Path('.aresforge') / 'state'
PROJECT_STATE_FILE_NAME = 'project_state.json'
OPERATION_LOG_FILE_NAME = 'operation_log.jsonl'
PROJECT_STATE_SCHEMA_VERSION = '1.0'

_PROJECT_STATE_FIELDS: tuple[str, ...] = (
    'schema_version',
    'project_name',
    'current_phase',
    'current_milestone',
    'current_mode',
    'repo_path',
    'branch',
    'head',
    'active_work',
    'completed_milestones',
    'pending_milestones',
    'known_blockers',
    'validation_status',
    'documentation_status',
    'pending_sync',
    'warnings',
    'updated_at',
)


def init_project_state(config: AppConfig, *, path: str | Path | None = None, force: bool = False) -> dict[str, Any]:
    state_path = resolve_project_state_path(config.repo_root, path)
    if state_path.exists() and not force:
        return _error(
            'project_state_exists',
            {
                'path': str(state_path),
                'message': 'Project state file already exists. Re-run with --force to overwrite.',
            },
        )

    state_path.parent.mkdir(parents=True, exist_ok=True)
    state = _default_project_state(config)
    state_path.write_text(json.dumps(state, indent=2) + '\n', encoding='utf-8')

    return {
        'command': 'init-project-state',
        'ok': True,
        'local_only': True,
        'path': str(state_path),
        'force': force,
        'state': state,
    }


def inspect_project_state(config: AppConfig, *, path: str | Path | None = None) -> dict[str, Any]:
    state_path = resolve_project_state_path(config.repo_root, path)
    if not state_path.exists():
        return _error(
            'project_state_not_found',
            {
                'path': str(state_path),
                'message': 'Project state file is missing. Run init-project-state first.',
            },
        )
    try:
        state = _read_project_state(state_path)
    except ValueError as exc:
        return _error('project_state_invalid_json', {'path': str(state_path), 'message': str(exc)})

    return {
        'command': 'inspect-project-state',
        'ok': True,
        'local_only': True,
        'path': str(state_path),
        'state': state,
    }


def update_project_state(
    config: AppConfig,
    *,
    path: str | Path | None = None,
    current_milestone: str | None = None,
    current_phase: str | None = None,
    current_mode: str | None = None,
    validation_status: str | None = None,
    documentation_status: str | None = None,
    warnings_to_add: list[str] | None = None,
) -> dict[str, Any]:
    state_path = resolve_project_state_path(config.repo_root, path)
    if not state_path.exists():
        return _error(
            'project_state_not_found',
            {
                'path': str(state_path),
                'message': 'Project state file is missing. Run init-project-state first.',
            },
        )
    try:
        state = _read_project_state(state_path)
    except ValueError as exc:
        return _error('project_state_invalid_json', {'path': str(state_path), 'message': str(exc)})

    updates: dict[str, Any] = {}
    if current_milestone is not None:
        updates['current_milestone'] = current_milestone
    if current_phase is not None:
        updates['current_phase'] = current_phase
    if current_mode is not None:
        updates['current_mode'] = current_mode
    if validation_status is not None:
        updates['validation_status'] = validation_status
    if documentation_status is not None:
        updates['documentation_status'] = documentation_status

    for key, value in updates.items():
        state[key] = value

    if warnings_to_add:
        current = state.get('warnings', [])
        if not isinstance(current, list):
            current = []
        for warning in warnings_to_add:
            if warning not in current:
                current.append(warning)
        state['warnings'] = current

    state['updated_at'] = _now_iso()
    state_path.write_text(json.dumps(state, indent=2) + '\n', encoding='utf-8')

    return {
        'command': 'update-project-state',
        'ok': True,
        'local_only': True,
        'path': str(state_path),
        'updated_fields': sorted(list(updates.keys()) + (['warnings'] if warnings_to_add else [])),
        'state': state,
    }


def append_operation_log(
    config: AppConfig,
    *,
    state_path: str | Path | None,
    event_type: str,
    summary: str,
    details: dict[str, Any] | None,
) -> dict[str, Any]:
    resolved_state_path = resolve_project_state_path(config.repo_root, state_path)
    log_path = resolve_operation_log_path(config.repo_root, state_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    entry = {
        'event_id': str(uuid.uuid4()),
        'event_type': event_type,
        'summary': summary,
        'details': details or {},
        'created_at': _now_iso(),
    }
    with log_path.open('a', encoding='utf-8') as handle:
        handle.write(json.dumps(entry) + '\n')

    return {
        'command': 'append-operation-log',
        'ok': True,
        'local_only': True,
        'state_path': str(resolved_state_path),
        'operation_log_path': str(log_path),
        'entry': entry,
    }


def inspect_operation_log(
    config: AppConfig,
    *,
    state_path: str | Path | None,
    limit: int | None,
) -> dict[str, Any]:
    log_path = resolve_operation_log_path(config.repo_root, state_path)
    if not log_path.exists():
        return _error(
            'operation_log_not_found',
            {
                'path': str(log_path),
                'message': 'Operation log file is missing. Append an operation log entry first.',
            },
        )

    entries: list[dict[str, Any]] = []
    try:
        for line in log_path.read_text(encoding='utf-8').splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            raw = json.loads(stripped)
            if isinstance(raw, dict):
                entries.append(raw)
    except json.JSONDecodeError as exc:
        return _error('operation_log_invalid_jsonl', {'path': str(log_path), 'message': str(exc)})

    if limit is not None:
        if limit < 0:
            return _error('invalid_limit', {'limit': limit, 'message': 'Limit must be >= 0.'})
        entries = entries[-limit:]

    return {
        'command': 'inspect-operation-log',
        'ok': True,
        'local_only': True,
        'operation_log_path': str(log_path),
        'entry_count': len(entries),
        'entries': entries,
    }


def resolve_project_state_path(repo_root: Path, path: str | Path | None) -> Path:
    if path is None:
        return (repo_root / STATE_DIR_RELATIVE / PROJECT_STATE_FILE_NAME).resolve()
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = (repo_root / candidate).resolve()
    if candidate.suffix.lower() == '.json' or candidate.name.endswith('.json'):
        return candidate
    return candidate / PROJECT_STATE_FILE_NAME


def resolve_operation_log_path(repo_root: Path, state_path: str | Path | None) -> Path:
    project_state_path = resolve_project_state_path(repo_root, state_path)
    return project_state_path.parent / OPERATION_LOG_FILE_NAME


def project_state_summary_for_handoff(config: AppConfig) -> dict[str, Any] | None:
    state_path = resolve_project_state_path(config.repo_root, None)
    if not state_path.exists():
        return None
    try:
        state = _read_project_state(state_path)
    except ValueError:
        return {
            'path': str(state_path),
            'error': 'project_state_invalid_json',
        }
    return {
        'path': str(state_path),
        'project_name': state.get('project_name'),
        'current_phase': state.get('current_phase'),
        'current_milestone': state.get('current_milestone'),
        'current_mode': state.get('current_mode'),
        'validation_status': state.get('validation_status'),
        'documentation_status': state.get('documentation_status'),
        'pending_sync': state.get('pending_sync'),
        'updated_at': state.get('updated_at'),
        'warnings': state.get('warnings', []),
    }


def _default_project_state(config: AppConfig) -> dict[str, Any]:
    branch, head = _git_branch_and_head(config.repo_root)
    return {
        'schema_version': PROJECT_STATE_SCHEMA_VERSION,
        'project_name': config.repo_root.name,
        'current_phase': '',
        'current_milestone': '',
        'current_mode': '',
        'repo_path': str(config.repo_root),
        'branch': branch,
        'head': head,
        'active_work': [],
        'completed_milestones': [],
        'pending_milestones': [],
        'known_blockers': [],
        'validation_status': 'unknown',
        'documentation_status': 'unknown',
        'pending_sync': False,
        'warnings': [],
        'updated_at': _now_iso(),
    }


def _read_project_state(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(raw, dict):
        raise ValueError('Project state must decode to a JSON object.')
    state: dict[str, Any] = {}
    for field in _PROJECT_STATE_FIELDS:
        state[field] = raw.get(field)
    return state


def _git_branch_and_head(repo_root: Path) -> tuple[str, str]:
    branch = 'unknown'
    head = 'unknown'

    try:
        branch_result = subprocess.run(
            ['git', 'branch', '--show-current'],
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
        )
        if branch_result.returncode == 0:
            value = (branch_result.stdout or '').strip()
            if value:
                branch = value
    except OSError:
        pass

    try:
        head_result = subprocess.run(
            ['git', 'rev-parse', 'HEAD'],
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
        )
        if head_result.returncode == 0:
            value = (head_result.stdout or '').strip()
            if value:
                head = value
    except OSError:
        pass

    return branch, head


def _error(error: str, details: dict[str, Any]) -> dict[str, Any]:
    return {
        'ok': False,
        'local_only': True,
        'error': error,
        'details': details,
    }


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()
