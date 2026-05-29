from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.local_active_project import inspect_active_project
from aresforge.operator.local_project_state import resolve_project_state_path
from aresforge.operator.managed_project_registry_local import resolve_managed_project_registry_path

QUEUE_DIR_RELATIVE = Path('.aresforge') / 'queue'
QUEUE_FILE_NAME = 'work_items.json'
QUEUE_SCHEMA_VERSION = '1.0'

QUEUE_STATUSES: tuple[str, ...] = (
    'proposed',
    'ready',
    'in_progress',
    'blocked',
    'done',
    'cancelled',
)
QUEUE_PRIORITIES: tuple[str, ...] = (
    'low',
    'normal',
    'high',
    'urgent',
)
QUEUE_ITEM_TYPES: tuple[str, ...] = (
    'milestone',
    'feature',
    'bug',
    'task',
    'documentation',
    'validation',
    'handoff',
    'orchestration',
    'sync',
    'dashboard',
    'other',
)

_QUEUE_ITEM_READINESS_BOUNDARY_CONFIRMATIONS: tuple[str, ...] = (
    'Local-only queue item readiness inspection.',
    'Read-only local queue inspection.',
    'No GitHub API calls.',
    'No gh calls.',
    'No network service calls.',
    'No mutations performed.',
)
_QUEUE_ITEM_START_BOUNDARY_CONFIRMATIONS: tuple[str, ...] = (
    'Local-only queue item start gate.',
    'File-backed local queue mutation only.',
    'No GitHub API calls.',
    'No gh calls.',
    'No network service calls.',
    'No agent execution.',
    'No model invocation.',
)
_QUEUE_ITEM_COMPLETE_BOUNDARY_CONFIRMATIONS: tuple[str, ...] = (
    'Local-only queue item completion gate.',
    'File-backed local queue mutation only.',
    'No GitHub API calls.',
    'No gh calls.',
    'No network service calls.',
    'No agent execution.',
    'No model invocation.',
    'No remote commit verification.',
)
_STARTABLE_QUEUE_STATUSES: frozenset[str] = frozenset({'proposed', 'ready'})
_COMPLETABLE_QUEUE_STATUSES: frozenset[str] = frozenset({'in_progress'})
_RESOLVED_DEPENDENCY_STATUSES: frozenset[str] = frozenset({'done'})
_BLOCKED_QUEUE_STATUSES: frozenset[str] = frozenset({'blocked'})

_SLUG_NON_ALNUM_RE = re.compile(r'[^a-z0-9]+')


def add_local_queue_item(
    config: AppConfig,
    *,
    title: str,
    description: str | None = None,
    project_id: str | None = None,
    repo_id: str | None = None,
    queue_path: str | Path | None = None,
    registry_path: str | Path | None = None,
    priority: str | None = None,
    item_type: str | None = None,
    assigned_agent: str | None = None,
    target_area: str | None = None,
    acceptance_criteria: list[str] | None = None,
    acceptance_notes: list[str] | None = None,
    validation_notes: list[str] | None = None,
    requested_outcome: str | None = None,
    dependencies: list[str] | None = None,
    tags: list[str] | None = None,
    source: str | None = None,
) -> dict[str, Any]:
    normalized_title = str(title or '').strip()
    if not normalized_title:
        return _error(
            'invalid_local_queue_item_payload',
            {
                'message': 'title is required.',
                'required_fields': ['title'],
            },
        )

    resolved_queue_path = resolve_project_queue_path(config.repo_root, queue_path)
    loaded = _load_queue_required(resolved_queue_path)
    if not loaded.get('ok', False):
        return loaded
    queue = loaded['queue']

    binding = _resolve_local_queue_binding(
        config,
        project_id=project_id,
        repo_id=repo_id,
        registry_path=registry_path,
    )
    if not binding.get('ok', False):
        return binding

    normalized_tags = _normalize_list(tags or [])
    normalized_target_area = str(target_area or '').strip()
    if normalized_target_area:
        normalized_tags = _normalize_list([*normalized_tags, f"area:{_slugify(normalized_target_area)}"])

    item_id = _generate_local_queue_item_id(
        repo_root=config.repo_root,
        queue=queue,
        title=normalized_title,
        project_id=str(binding.get('project_id', '')).strip(),
        repo_id=str(binding.get('repo_id', '')).strip(),
    )
    result = add_queue_item(
        config,
        item_id=item_id,
        project_id=str(binding.get('project_id', '')).strip(),
        repo_id=str(binding.get('repo_id', '')).strip(),
        title=normalized_title,
        queue_path=resolved_queue_path,
        registry_path=registry_path,
        description=description,
        status='proposed',
        priority=priority,
        item_type=item_type,
        tags=normalized_tags,
        dependencies=dependencies,
        blocked_by=None,
        assigned_agent=assigned_agent,
        source=str(source or '').strip() or 'local_cli',
        notes=_compose_intake_notes(
            acceptance_criteria=acceptance_criteria,
            acceptance_notes=acceptance_notes,
            validation_notes=validation_notes,
            requested_outcome=requested_outcome,
        ),
    )
    if not result.get('ok', False):
        return result

    item = result.get('item', {}) if isinstance(result.get('item'), dict) else {}
    return {
        'command': 'add-local-queue-item',
        'ok': True,
        'local_only': True,
        'item_id': str(item.get('item_id', '')).strip(),
        'status': str(item.get('status', '')).strip(),
        'project_id': str(item.get('project_id', '')).strip(),
        'repo_id': str(item.get('repo_id', '')).strip(),
        'source': str(item.get('source', '')).strip(),
        'next_safe_action': (
            'Inspect the queue item locally with '
            f"python -m aresforge inspect-queue-item --item-id {str(item.get('item_id', '')).strip()}"
        ),
        'warnings': sorted(
            {
                str(warning).strip()
                for warning in result.get('warnings', [])
                if str(warning).strip()
            }
        ),
    }


def init_project_queue(
    config: AppConfig,
    *,
    path: str | Path | None = None,
    force: bool = False,
) -> dict[str, Any]:
    queue_path = resolve_project_queue_path(config.repo_root, path)
    if queue_path.exists() and not force:
        return _error(
            'project_queue_exists',
            {
                'path': str(queue_path),
                'message': 'Project queue file already exists. Re-run with --force to overwrite.',
            },
        )

    queue_path.parent.mkdir(parents=True, exist_ok=True)
    queue = _default_queue()
    _write_queue(queue_path, queue)

    return {
        'command': 'init-project-queue',
        'ok': True,
        'local_only': True,
        'path': str(queue_path),
        'force': force,
        'queue': queue,
    }


def add_queue_item(
    config: AppConfig,
    *,
    item_id: str,
    project_id: str,
    repo_id: str,
    title: str,
    queue_path: str | Path | None = None,
    registry_path: str | Path | None = None,
    description: str | None = None,
    status: str | None = None,
    priority: str | None = None,
    item_type: str | None = None,
    tags: list[str] | None = None,
    dependencies: list[str] | None = None,
    blocked_by: list[str] | None = None,
    assigned_agent: str | None = None,
    source: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    if status is not None and status not in QUEUE_STATUSES:
        return _error(
            'invalid_queue_status',
            {
                'status': status,
                'supported_statuses': list(QUEUE_STATUSES),
                'message': 'Invalid queue status supplied.',
            },
        )
    if priority is not None and priority not in QUEUE_PRIORITIES:
        return _error(
            'invalid_queue_priority',
            {
                'priority': priority,
                'supported_priorities': list(QUEUE_PRIORITIES),
                'message': 'Invalid queue priority supplied.',
            },
        )
    if item_type is not None and item_type not in QUEUE_ITEM_TYPES:
        return _error(
            'invalid_queue_item_type',
            {
                'item_type': item_type,
                'supported_item_types': list(QUEUE_ITEM_TYPES),
                'message': 'Invalid queue item type supplied.',
            },
        )

    resolved_queue_path = resolve_project_queue_path(config.repo_root, queue_path)
    loaded = _load_queue_required(resolved_queue_path)
    if not loaded.get('ok', False):
        return loaded
    queue = loaded['queue']

    registry_validation = _validate_registry_binding(
        repo_root=config.repo_root,
        project_id=project_id,
        repo_id=repo_id,
        registry_path=registry_path,
    )
    if not registry_validation.get('ok', False):
        return registry_validation

    now = _now_iso()
    normalized_item_id = item_id.strip()
    items = queue.get('work_items', [])
    if not isinstance(items, list):
        items = []

    existing = next(
        (
            candidate
            for candidate in items
            if isinstance(candidate, dict) and str(candidate.get('item_id', '')).strip() == normalized_item_id
        ),
        None,
    )
    created = False
    if existing is None:
        existing = {
            'item_id': normalized_item_id,
            'project_id': '',
            'repo_id': '',
            'title': '',
            'description': '',
            'status': 'proposed',
            'priority': 'normal',
            'item_type': 'task',
            'tags': [],
            'dependencies': [],
            'blocked_by': [],
            'assigned_agent': '',
            'source': '',
            'notes': '',
            'started_at': '',
            'started_via': '',
            'previous_status': '',
            'completed_at': '',
            'completed_by': '',
            'completion_commit': '',
            'validation_summary': '',
            'evidence_note': '',
            'tests_run': [],
            'changed_files': [],
            'artifact_paths': [],
            'created_at': now,
            'updated_at': now,
        }
        items.append(existing)
        created = True

    existing['item_id'] = normalized_item_id
    existing['project_id'] = project_id.strip()
    existing['repo_id'] = repo_id.strip()
    existing['title'] = title.strip()

    if description is not None:
        existing['description'] = description.strip()
    elif created:
        existing['description'] = ''
    if status is not None:
        existing['status'] = status
    elif created:
        existing['status'] = 'proposed'
    if priority is not None:
        existing['priority'] = priority
    elif created:
        existing['priority'] = 'normal'
    if item_type is not None:
        existing['item_type'] = item_type
    elif created:
        existing['item_type'] = 'task'
    if tags is not None and len(tags) > 0:
        existing['tags'] = _normalize_list(tags)
    elif created:
        existing['tags'] = []
    if dependencies is not None and len(dependencies) > 0:
        existing['dependencies'] = _normalize_list(dependencies)
    elif created:
        existing['dependencies'] = []
    if blocked_by is not None and len(blocked_by) > 0:
        existing['blocked_by'] = _normalize_list(blocked_by)
    elif created:
        existing['blocked_by'] = []
    if assigned_agent is not None:
        existing['assigned_agent'] = assigned_agent.strip()
    elif created:
        existing['assigned_agent'] = ''
    if source is not None:
        existing['source'] = source.strip()
    elif created:
        existing['source'] = ''
    if notes is not None:
        existing['notes'] = notes.strip()
    elif created:
        existing['notes'] = ''

    if not existing.get('created_at'):
        existing['created_at'] = now
    existing['updated_at'] = now

    queue['work_items'] = items
    queue['updated_at'] = now

    warnings: list[str] = list(registry_validation.get('warnings', []))
    warnings.extend(_dependency_warnings(existing, items))

    _write_queue(resolved_queue_path, queue)

    return {
        'command': 'add-queue-item',
        'ok': True,
        'local_only': True,
        'queue_path': str(resolved_queue_path),
        'created': created,
        'warnings': sorted(set(warnings)),
        'item': _item_view(existing),
    }


def update_queue_item(
    config: AppConfig,
    *,
    item_id: str,
    queue_path: str | Path | None = None,
    status: str | None = None,
    priority: str | None = None,
    item_type: str | None = None,
    title: str | None = None,
    project_id: str | None = None,
    repo_id: str | None = None,
    description: str | None = None,
    tags: list[str] | None = None,
    dependencies: list[str] | None = None,
    blocked_by: list[str] | None = None,
    assigned_agent: str | None = None,
    source: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    if status is not None and status not in QUEUE_STATUSES:
        return _error(
            'invalid_queue_status',
            {
                'status': status,
                'supported_statuses': list(QUEUE_STATUSES),
                'message': 'Invalid queue status supplied.',
            },
        )
    if priority is not None and priority not in QUEUE_PRIORITIES:
        return _error(
            'invalid_queue_priority',
            {
                'priority': priority,
                'supported_priorities': list(QUEUE_PRIORITIES),
                'message': 'Invalid queue priority supplied.',
            },
        )
    if item_type is not None and item_type not in QUEUE_ITEM_TYPES:
        return _error(
            'invalid_queue_item_type',
            {
                'item_type': item_type,
                'supported_item_types': list(QUEUE_ITEM_TYPES),
                'message': 'Invalid queue item type supplied.',
            },
        )

    resolved_queue_path = resolve_project_queue_path(config.repo_root, queue_path)
    loaded = _load_queue_required(resolved_queue_path)
    if not loaded.get('ok', False):
        return loaded
    queue = loaded['queue']

    items = queue.get('work_items', [])
    if not isinstance(items, list):
        items = []

    normalized_item_id = item_id.strip()
    existing = next(
        (
            candidate
            for candidate in items
            if isinstance(candidate, dict) and str(candidate.get('item_id', '')).strip() == normalized_item_id
        ),
        None,
    )
    if existing is None:
        return _error(
            'queue_item_not_found',
            {
                'item_id': normalized_item_id,
                'queue_path': str(resolved_queue_path),
                'message': 'Queue item id was not found in local project queue.',
            },
        )

    updated_fields: list[str] = []

    if project_id is not None:
        existing['project_id'] = project_id.strip()
        updated_fields.append('project_id')
    if repo_id is not None:
        existing['repo_id'] = repo_id.strip()
        updated_fields.append('repo_id')
    if title is not None:
        existing['title'] = title.strip()
        updated_fields.append('title')
    if description is not None:
        existing['description'] = description.strip()
        updated_fields.append('description')
    if status is not None:
        existing['status'] = status
        updated_fields.append('status')
    if priority is not None:
        existing['priority'] = priority
        updated_fields.append('priority')
    if item_type is not None:
        existing['item_type'] = item_type
        updated_fields.append('item_type')
    if tags is not None:
        existing['tags'] = _normalize_list(tags)
        updated_fields.append('tags')
    if dependencies is not None:
        existing['dependencies'] = _normalize_list(dependencies)
        updated_fields.append('dependencies')
    if blocked_by is not None:
        existing['blocked_by'] = _normalize_list(blocked_by)
        updated_fields.append('blocked_by')
    if assigned_agent is not None:
        existing['assigned_agent'] = assigned_agent.strip()
        updated_fields.append('assigned_agent')
    if source is not None:
        existing['source'] = source.strip()
        updated_fields.append('source')
    if notes is not None:
        existing['notes'] = notes.strip()
        updated_fields.append('notes')

    now = _now_iso()
    existing['updated_at'] = now
    if not existing.get('created_at'):
        existing['created_at'] = now

    queue['work_items'] = items
    queue['updated_at'] = now

    warnings = _dependency_warnings(existing, items)

    _write_queue(resolved_queue_path, queue)

    return {
        'command': 'update-queue-item',
        'ok': True,
        'local_only': True,
        'queue_path': str(resolved_queue_path),
        'updated_fields': sorted(updated_fields),
        'warnings': sorted(set(warnings)),
        'item': _item_view(existing),
    }


def inspect_project_queue(
    config: AppConfig,
    *,
    queue_path: str | Path | None = None,
    project_id: str | None = None,
    repo_id: str | None = None,
    status: str | None = None,
    item_type: str | None = None,
    assigned_agent: str | None = None,
    output_format: str = 'json',
) -> dict[str, Any]:
    if status is not None and status not in QUEUE_STATUSES:
        return _error(
            'invalid_queue_status',
            {
                'status': status,
                'supported_statuses': list(QUEUE_STATUSES),
                'message': 'Invalid queue status supplied.',
            },
        )
    if item_type is not None and item_type not in QUEUE_ITEM_TYPES:
        return _error(
            'invalid_queue_item_type',
            {
                'item_type': item_type,
                'supported_item_types': list(QUEUE_ITEM_TYPES),
                'message': 'Invalid queue item type supplied.',
            },
        )

    resolved_queue_path = resolve_project_queue_path(config.repo_root, queue_path)
    loaded = _load_queue_required(resolved_queue_path)
    if not loaded.get('ok', False):
        return loaded
    queue = loaded['queue']

    raw_items = queue.get('work_items', [])
    items = [_item_view(item) for item in raw_items if isinstance(item, dict)]
    filtered: list[dict[str, Any]] = []
    for item in items:
        if project_id is not None and item.get('project_id') != project_id.strip():
            continue
        if repo_id is not None and item.get('repo_id') != repo_id.strip():
            continue
        if status is not None and item.get('status') != status:
            continue
        if item_type is not None and item.get('item_type') != item_type:
            continue
        if assigned_agent is not None and item.get('assigned_agent') != assigned_agent.strip():
            continue
        filtered.append(item)

    payload = {
        'queue_path': str(resolved_queue_path),
        'schema_version': queue.get('schema_version'),
        'updated_at': queue.get('updated_at'),
        'item_count': len(filtered),
        'filters': {
            'project_id': project_id,
            'repo_id': repo_id,
            'status': status,
            'item_type': item_type,
            'assigned_agent': assigned_agent,
        },
        'work_items': filtered,
    }
    return _stdout_result(
        command='inspect-project-queue',
        payload=payload,
        output_format=output_format,
        markdown=_render_queue_markdown(payload),
    )


def inspect_queue_item(
    config: AppConfig,
    *,
    item_id: str,
    queue_path: str | Path | None = None,
    output_format: str = 'json',
) -> dict[str, Any]:
    resolved_queue_path = resolve_project_queue_path(config.repo_root, queue_path)
    loaded = _load_queue_required(resolved_queue_path)
    if not loaded.get('ok', False):
        return loaded
    queue = loaded['queue']

    normalized_item_id = item_id.strip()
    item = next(
        (
            candidate
            for candidate in queue.get('work_items', [])
            if isinstance(candidate, dict) and str(candidate.get('item_id', '')).strip() == normalized_item_id
        ),
        None,
    )
    if item is None:
        return _error(
            'queue_item_not_found',
            {
                'item_id': normalized_item_id,
                'queue_path': str(resolved_queue_path),
                'message': 'Queue item id was not found in local project queue.',
            },
        )

    payload = {
        'queue_path': str(resolved_queue_path),
        'item': _item_view(item),
    }
    return _stdout_result(
        command='inspect-queue-item',
        payload=payload,
        output_format=output_format,
        markdown=_render_queue_item_markdown(payload),
    )


def inspect_local_queue_item_readiness(
    config: AppConfig,
    *,
    item_id: str,
    queue_path: str | Path | None = None,
    registry_path: str | Path | None = None,
) -> dict[str, Any]:
    resolved_queue_path = resolve_project_queue_path(config.repo_root, queue_path)
    loaded = _load_queue_required(resolved_queue_path)
    if not loaded.get('ok', False):
        return loaded
    queue = loaded['queue']

    items = [_item_view(item) for item in queue.get('work_items', []) if isinstance(item, dict)]
    normalized_item_id = str(item_id or '').strip()
    item = next((candidate for candidate in items if candidate.get('item_id') == normalized_item_id), None)
    if item is None:
        return {
            'command': 'inspect-local-queue-item-readiness',
            'ok': False,
            'local_only': True,
            'item_id': normalized_item_id,
            'title': '',
            'status': '',
            'project_id': '',
            'repo_id': '',
            'readiness_status': 'not_found',
            'can_start': False,
            'blockers': [f'Queue item not found: {normalized_item_id}'],
            'warnings': [],
            'missing_fields': [],
            'dependency_summary': _empty_dependency_summary(),
            'recommended_next_action': 'Inspect the local queue and choose a valid item_id.',
            'boundary_confirmations': list(_QUEUE_ITEM_READINESS_BOUNDARY_CONFIRMATIONS),
        }

    return _evaluate_local_queue_item_readiness(
        repo_root=config.repo_root,
        item=item,
        items=items,
        registry_path=registry_path,
    )


def start_local_queue_item(
    config: AppConfig,
    *,
    item_id: str,
    queue_path: str | Path | None = None,
    registry_path: str | Path | None = None,
    started_via: str = 'local_operator',
) -> dict[str, Any]:
    resolved_queue_path = resolve_project_queue_path(config.repo_root, queue_path)
    loaded = _load_queue_required(resolved_queue_path)
    if not loaded.get('ok', False):
        return loaded
    queue = loaded['queue']

    items = queue.get('work_items', [])
    if not isinstance(items, list):
        items = []

    normalized_item_id = str(item_id or '').strip()
    raw_item = next(
        (
            candidate
            for candidate in items
            if isinstance(candidate, dict) and str(candidate.get('item_id', '')).strip() == normalized_item_id
        ),
        None,
    )
    readiness = inspect_local_queue_item_readiness(
        config,
        item_id=normalized_item_id,
        queue_path=resolved_queue_path,
        registry_path=registry_path,
    )
    if raw_item is None or not readiness.get('ok', False) or readiness.get('readiness_status') != 'ready':
        return {
            'command': 'start-local-queue-item',
            'ok': False,
            'local_only': True,
            'item_id': normalized_item_id,
            'previous_status': str((readiness if isinstance(readiness, dict) else {}).get('status', '')).strip(),
            'status': str((readiness if isinstance(readiness, dict) else {}).get('status', '')).strip(),
            'next_safe_action': str(
                (readiness if isinstance(readiness, dict) else {}).get(
                    'recommended_next_action', 'Inspect local queue item readiness and resolve blockers.'
                )
            ).strip(),
            'prompt_recommended': _prompt_recommended((readiness if isinstance(readiness, dict) else {})),
            'warnings': sorted(
                {
                    *[
                        str(warning).strip()
                        for warning in (readiness.get('warnings', []) if isinstance(readiness, dict) else [])
                        if str(warning).strip()
                    ],
                    *[
                        str(blocker).strip()
                        for blocker in (readiness.get('blockers', []) if isinstance(readiness, dict) else [])
                        if str(blocker).strip()
                    ],
                }
            ),
            'readiness': readiness,
            'boundary_confirmations': list(_QUEUE_ITEM_START_BOUNDARY_CONFIRMATIONS),
        }

    item = _item_view(raw_item)
    previous_status = str(item.get('status', '')).strip()
    now = _now_iso()
    raw_item['previous_status'] = previous_status
    raw_item['status'] = 'in_progress'
    raw_item['started_at'] = now
    raw_item['started_via'] = str(started_via or 'local_operator').strip() or 'local_operator'
    raw_item['updated_at'] = now
    queue['work_items'] = items
    queue['updated_at'] = now
    _write_queue(resolved_queue_path, queue)

    started_item = _item_view(raw_item)
    warnings = [
        str(warning).strip()
        for warning in readiness.get('warnings', [])
        if str(warning).strip()
    ]
    return {
        'command': 'start-local-queue-item',
        'ok': True,
        'local_only': True,
        'item_id': normalized_item_id,
        'previous_status': previous_status,
        'status': str(started_item.get('status', '')).strip(),
        'next_safe_action': 'Continue local implementation work and inspect queue summary as needed.',
        'prompt_recommended': _prompt_recommended(started_item),
        'warnings': sorted(set(warnings)),
        'boundary_confirmations': list(_QUEUE_ITEM_START_BOUNDARY_CONFIRMATIONS),
        'item': started_item,
    }


def complete_local_queue_item(
    config: AppConfig,
    *,
    item_id: str,
    commit_hash: str,
    validation_summary: str,
    evidence_note: str | None = None,
    tests_run: list[str] | None = None,
    changed_files: list[str] | None = None,
    artifact_paths: list[str] | None = None,
    completed_by: str = 'local_operator',
    queue_path: str | Path | None = None,
) -> dict[str, Any]:
    resolved_queue_path = resolve_project_queue_path(config.repo_root, queue_path)
    loaded = _load_queue_required(resolved_queue_path)
    if not loaded.get('ok', False):
        return loaded
    queue = loaded['queue']

    items = queue.get('work_items', [])
    if not isinstance(items, list):
        items = []

    normalized_item_id = str(item_id or '').strip()
    normalized_commit_hash = str(commit_hash or '').strip()
    normalized_validation_summary = str(validation_summary or '').strip()
    normalized_completed_by = str(completed_by or 'local_operator').strip() or 'local_operator'
    raw_item = next(
        (
            candidate
            for candidate in items
            if isinstance(candidate, dict) and str(candidate.get('item_id', '')).strip() == normalized_item_id
        ),
        None,
    )
    if raw_item is None:
        return {
            'command': 'complete-local-queue-item',
            'ok': False,
            'local_only': True,
            'item_id': normalized_item_id,
            'previous_status': '',
            'status': '',
            'completion_commit': normalized_commit_hash,
            'validation_summary': normalized_validation_summary,
            'next_safe_action': 'Inspect the local queue and choose a valid item_id.',
            'warnings': [f'Queue item not found: {normalized_item_id}'],
            'boundary_confirmations': list(_QUEUE_ITEM_COMPLETE_BOUNDARY_CONFIRMATIONS),
        }

    previous_status = str(raw_item.get('status', '')).strip()
    warnings: list[str] = []
    if not normalized_commit_hash:
        warnings.append('commit_hash is required to complete a local queue item.')
    if not normalized_validation_summary:
        warnings.append('validation_summary is required to complete a local queue item.')
    if previous_status == 'done':
        warnings.append('Queue item is already done.')
    elif previous_status == 'cancelled':
        warnings.append('Queue item is cancelled.')
    elif previous_status not in _COMPLETABLE_QUEUE_STATUSES:
        warnings.append('Queue item must be in_progress before completion evidence can be recorded.')

    if warnings:
        return {
            'command': 'complete-local-queue-item',
            'ok': False,
            'local_only': True,
            'item_id': normalized_item_id,
            'previous_status': previous_status,
            'status': previous_status,
            'completion_commit': normalized_commit_hash,
            'validation_summary': normalized_validation_summary,
            'next_safe_action': 'Start the queue item, gather validation evidence, and retry completion.',
            'warnings': sorted(set(warnings)),
            'boundary_confirmations': list(_QUEUE_ITEM_COMPLETE_BOUNDARY_CONFIRMATIONS),
        }

    now = _now_iso()
    raw_item['previous_status'] = previous_status
    raw_item['status'] = 'done'
    raw_item['completed_at'] = now
    raw_item['completed_by'] = normalized_completed_by
    raw_item['completion_commit'] = normalized_commit_hash
    raw_item['validation_summary'] = normalized_validation_summary
    raw_item['evidence_note'] = str(evidence_note or '').strip()
    raw_item['tests_run'] = _normalize_list(tests_run or [])
    raw_item['changed_files'] = _normalize_list(changed_files or [])
    raw_item['artifact_paths'] = _normalize_list(artifact_paths or [])
    raw_item['updated_at'] = now
    queue['work_items'] = items
    queue['updated_at'] = now
    _write_queue(resolved_queue_path, queue)

    completed_item = _item_view(raw_item)
    return {
        'command': 'complete-local-queue-item',
        'ok': True,
        'local_only': True,
        'item_id': normalized_item_id,
        'previous_status': previous_status,
        'status': str(completed_item.get('status', '')).strip(),
        'completion_commit': str(completed_item.get('completion_commit', '')).strip(),
        'validation_summary': str(completed_item.get('validation_summary', '')).strip(),
        'next_safe_action': 'Inspect queue summary and reconcile source-of-truth docs as needed.',
        'warnings': [],
        'boundary_confirmations': list(_QUEUE_ITEM_COMPLETE_BOUNDARY_CONFIRMATIONS),
        'item': completed_item,
    }


def generate_local_queue_item_codex_prompt(
    config: AppConfig,
    *,
    item_id: str,
    queue_path: str | Path | None = None,
    registry_path: str | Path | None = None,
    output: str | Path | None = None,
    force: bool = False,
    commit_message: str | None = None,
) -> dict[str, Any]:
    resolved_queue_path = resolve_project_queue_path(config.repo_root, queue_path)
    loaded = _load_queue_required(resolved_queue_path)
    if not loaded.get('ok', False):
        return loaded
    queue = loaded['queue']

    items = [_item_view(item) for item in queue.get('work_items', []) if isinstance(item, dict)]
    normalized_item_id = str(item_id or '').strip()
    item = next((candidate for candidate in items if candidate.get('item_id') == normalized_item_id), None)
    if item is None:
        return {
            'command': 'generate-local-queue-item-codex-prompt',
            'ok': False,
            'local_only': True,
            'item_id': normalized_item_id,
            'prompt': '',
            'readiness_status': 'not_found',
            'warnings': [],
        }

    readiness = _evaluate_local_queue_item_readiness(
        repo_root=config.repo_root,
        item=item,
        items=items,
        registry_path=registry_path,
    )
    parsed_notes = _parse_queue_item_notes(str(item.get('notes', '')).strip())
    prompt = _render_local_queue_item_codex_prompt(
        repo_root=config.repo_root,
        item=item,
        readiness=readiness,
        target_area=_infer_target_area(item),
        acceptance_criteria=parsed_notes['acceptance_criteria'],
        extra_notes=parsed_notes['notes'],
        commit_message=commit_message,
    )

    payload = {
        'command': 'generate-local-queue-item-codex-prompt',
        'ok': True,
        'local_only': True,
        'item_id': normalized_item_id,
        'prompt': prompt,
        'readiness_status': str(readiness.get('readiness_status', '')).strip(),
        'warnings': sorted(
            {
                str(warning).strip()
                for warning in readiness.get('warnings', [])
                if str(warning).strip()
            }
        ),
    }

    if output is None:
        return payload

    output_path = Path(output)
    if output_path.exists() and not force:
        payload['ok'] = False
        payload['output_path'] = str(output_path)
        payload['warnings'] = sorted(
            {
                *payload['warnings'],
                'Output file already exists. Re-run with --force to overwrite.',
            }
        )
        return payload

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(prompt + '\n', encoding='utf-8')
    except OSError as exc:
        payload['ok'] = False
        payload['output_path'] = str(output_path)
        payload['warnings'] = sorted(
            {
                *payload['warnings'],
                f'Failed to write output file: {exc}',
            }
        )
        return payload

    payload['output_path'] = str(output_path)
    return payload


def project_queue_summary_for_handoff(config: AppConfig) -> dict[str, Any] | None:
    queue_path = resolve_project_queue_path(config.repo_root, None)
    if not queue_path.exists():
        return None

    loaded = _load_queue_required(queue_path)
    if not loaded.get('ok', False):
        return {
            'path': str(queue_path),
            'error': str(loaded.get('error', 'unknown')),
        }

    queue = loaded['queue']
    items = [_item_view(item) for item in queue.get('work_items', []) if isinstance(item, dict)]

    status_counts: dict[str, int] = {}
    for value in QUEUE_STATUSES:
        status_counts[value] = 0
    for item in items:
        status_value = str(item.get('status', '')).strip()
        if status_value not in status_counts:
            status_counts[status_value] = 0
        status_counts[status_value] += 1

    return {
        'path': str(queue_path),
        'schema_version': queue.get('schema_version'),
        'updated_at': queue.get('updated_at'),
        'item_count': len(items),
        'status_counts': status_counts,
    }


def resolve_project_queue_path(repo_root: Path, path: str | Path | None) -> Path:
    if path is None:
        return (repo_root / QUEUE_DIR_RELATIVE / QUEUE_FILE_NAME).resolve()
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = (repo_root / candidate).resolve()
    if candidate.suffix.lower() == '.json' or candidate.name.endswith('.json'):
        return candidate
    return candidate / QUEUE_FILE_NAME


def _default_queue() -> dict[str, Any]:
    return {
        'schema_version': QUEUE_SCHEMA_VERSION,
        'updated_at': _now_iso(),
        'work_items': [],
    }


def _load_queue_required(path: Path) -> dict[str, Any]:
    if not path.exists():
        return _error(
            'project_queue_not_found',
            {
                'path': str(path),
                'message': 'Local project queue is missing. Run init-project-queue first.',
            },
        )
    try:
        raw = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as exc:
        return _error(
            'project_queue_invalid_json',
            {
                'path': str(path),
                'message': str(exc),
            },
        )
    if not isinstance(raw, dict):
        return _error(
            'project_queue_invalid_schema',
            {
                'path': str(path),
                'message': 'Queue JSON must decode to an object.',
            },
        )

    queue = {
        'schema_version': str(raw.get('schema_version') or QUEUE_SCHEMA_VERSION),
        'updated_at': str(raw.get('updated_at') or _now_iso()),
        'work_items': raw.get('work_items') if isinstance(raw.get('work_items'), list) else [],
    }
    return {
        'ok': True,
        'queue': queue,
    }


def _write_queue(path: Path, queue: dict[str, Any]) -> None:
    path.write_text(json.dumps(queue, indent=2) + '\n', encoding='utf-8')


def _resolve_local_queue_binding(
    config: AppConfig,
    *,
    project_id: str | None,
    repo_id: str | None,
    registry_path: str | Path | None,
) -> dict[str, Any]:
    normalized_project_id = str(project_id or '').strip()
    normalized_repo_id = str(repo_id or '').strip()
    warnings: list[str] = []
    project: dict[str, Any] | None = None

    if not normalized_project_id:
        active_payload = inspect_active_project(config)
        warnings.extend(
            str(warning).strip()
            for warning in active_payload.get('warnings', [])
            if str(warning).strip()
        )
        normalized_project_id = str(active_payload.get('active_project_id', '')).strip()
        if not normalized_project_id:
            return _error(
                'active_project_required',
                {
                    'message': 'project_id is required when no active project is selected.',
                    'required_fields': ['project_id'],
                    'active_project_selected': False,
                    'warnings': sorted(set(warnings)),
                },
            )
        if isinstance(active_payload.get('active_project'), dict):
            project = active_payload['active_project']
        if not normalized_repo_id:
            normalized_repo_id = str(active_payload.get('active_repo_id', '')).strip()

    registry_lookup = _lookup_registry_project(
        repo_root=config.repo_root,
        project_id=normalized_project_id,
        registry_path=registry_path,
    )
    warnings.extend(registry_lookup.get('warnings', []))
    if not registry_lookup.get('ok', False):
        return registry_lookup
    if isinstance(registry_lookup.get('project'), dict):
        project = registry_lookup['project']

    if not normalized_repo_id and isinstance(project, dict):
        normalized_repo_id = _project_primary_repo_id(project)

    if not normalized_repo_id:
        return _error(
            'repo_id_required',
            {
                'message': 'repo_id is required when no primary repo can be resolved.',
                'required_fields': ['repo_id'],
                'project_id': normalized_project_id,
                'warnings': sorted(set(warnings)),
            },
        )

    validation = _validate_registry_binding(
        repo_root=config.repo_root,
        project_id=normalized_project_id,
        repo_id=normalized_repo_id,
        registry_path=registry_path,
    )
    if not validation.get('ok', False):
        return validation

    warnings.extend(validation.get('warnings', []))
    return {
        'ok': True,
        'project_id': normalized_project_id,
        'repo_id': normalized_repo_id,
        'warnings': sorted(set(str(warning) for warning in warnings if str(warning).strip())),
    }


def _normalize_list(values: list[str]) -> list[str]:
    normalized: list[str] = []
    for value in values:
        item = str(value).strip()
        if item and item not in normalized:
            normalized.append(item)
    return normalized


def _evaluate_local_queue_item_readiness(
    *,
    repo_root: Path,
    item: dict[str, Any],
    items: list[dict[str, Any]],
    registry_path: str | Path | None,
) -> dict[str, Any]:
    blockers: list[str] = []
    warnings: list[str] = []
    missing_fields = _missing_queue_item_fields(item)
    dependency_summary = _dependency_readiness_summary(item, items)

    status = str(item.get('status', '')).strip()
    project_id = str(item.get('project_id', '')).strip()
    repo_id = str(item.get('repo_id', '')).strip()
    title = str(item.get('title', '')).strip()

    if status in _BLOCKED_QUEUE_STATUSES:
        blockers.append('Queue item status is blocked.')
    elif status == 'in_progress':
        blockers.append('Queue item is already in progress.')
    elif status == 'done':
        blockers.append('Queue item is already done.')
    elif status == 'cancelled':
        blockers.append('Queue item is cancelled.')
    elif status not in _STARTABLE_QUEUE_STATUSES:
        warnings.append('Queue item status must be ready before work should start.')

    binding_check = _inspect_registry_binding_readiness(
        repo_root=repo_root,
        project_id=project_id,
        repo_id=repo_id,
        registry_path=registry_path,
    )
    blockers.extend(binding_check['blockers'])
    warnings.extend(binding_check['warnings'])

    blockers.extend(dependency_summary['blockers'])
    warnings.extend(dependency_summary['warnings'])

    can_start = status in _STARTABLE_QUEUE_STATUSES and not blockers and not missing_fields
    if can_start:
        readiness_status = 'ready'
    elif blockers:
        readiness_status = 'blocked'
    else:
        readiness_status = 'needs_attention'

    return {
        'command': 'inspect-local-queue-item-readiness',
        'ok': True,
        'local_only': True,
        'item_id': str(item.get('item_id', '')).strip(),
        'title': title,
        'status': status,
        'project_id': project_id,
        'repo_id': repo_id,
        'readiness_status': readiness_status,
        'can_start': can_start,
        'blockers': sorted(set(blockers)),
        'warnings': sorted(set(warnings)),
        'missing_fields': missing_fields,
        'dependency_summary': dependency_summary['payload'],
        'recommended_next_action': _recommended_queue_item_next_action(
            item_id=str(item.get('item_id', '')).strip(),
            status=status,
            readiness_status=readiness_status,
            missing_fields=missing_fields,
            dependency_payload=dependency_summary['payload'],
            binding_blockers=binding_check['blockers'],
        ),
        'boundary_confirmations': list(_QUEUE_ITEM_READINESS_BOUNDARY_CONFIRMATIONS),
    }


def _missing_queue_item_fields(item: dict[str, Any]) -> list[str]:
    missing_fields: list[str] = []
    if not str(item.get('title', '')).strip():
        missing_fields.append('title')
    if not str(item.get('project_id', '')).strip():
        missing_fields.append('project_id')
    if not str(item.get('repo_id', '')).strip():
        missing_fields.append('repo_id')
    has_execution_context = bool(str(item.get('description', '')).strip() or str(item.get('notes', '')).strip())
    if not has_execution_context:
        missing_fields.append('execution_context')
    return sorted(set(missing_fields))


def _prompt_recommended(item: dict[str, Any]) -> bool:
    return bool(str(item.get('title', '')).strip() and (str(item.get('description', '')).strip() or str(item.get('notes', '')).strip()))


def _empty_dependency_summary() -> dict[str, Any]:
    return {
        'total_dependencies': 0,
        'resolved_dependencies': [],
        'unresolved_dependencies': [],
        'total_blocked_by': 0,
        'unresolved_blockers': [],
    }


def _dependency_readiness_summary(item: dict[str, Any], items: list[dict[str, Any]]) -> dict[str, Any]:
    by_id = {str(candidate.get('item_id', '')).strip(): candidate for candidate in items if str(candidate.get('item_id', '')).strip()}
    dependencies = _normalize_list(item.get('dependencies', []) if isinstance(item.get('dependencies'), list) else [])
    blocked_by = _normalize_list(item.get('blocked_by', []) if isinstance(item.get('blocked_by'), list) else [])
    resolved_dependencies: list[str] = []
    unresolved_dependencies: list[dict[str, str]] = []
    unresolved_blockers: list[dict[str, str]] = []
    blockers: list[str] = []
    warnings: list[str] = []

    for dependency_id in dependencies:
        dependency_item = by_id.get(dependency_id)
        if dependency_item is None:
            unresolved_dependencies.append(
                {'item_id': dependency_id, 'status': 'unknown', 'reason': 'dependency_not_found'}
            )
            blockers.append(f'Dependency item not found in local queue: {dependency_id}')
            continue
        dependency_status = str(dependency_item.get('status', '')).strip()
        if dependency_status in _RESOLVED_DEPENDENCY_STATUSES:
            resolved_dependencies.append(dependency_id)
            continue
        reason = 'dependency_incomplete'
        if dependency_status in _BLOCKED_QUEUE_STATUSES:
            reason = 'dependency_blocked'
        unresolved_dependencies.append(
            {'item_id': dependency_id, 'status': dependency_status or 'unknown', 'reason': reason}
        )
        blockers.append(
            f'Dependency must be done before start: {dependency_id} (status={dependency_status or "unknown"})'
        )

    for blocker_id in blocked_by:
        blocker_item = by_id.get(blocker_id)
        if blocker_item is None:
            unresolved_blockers.append(
                {'item_id': blocker_id, 'status': 'unknown', 'reason': 'blocker_not_found'}
            )
            blockers.append(f'Blocked-by item not found in local queue: {blocker_id}')
            continue
        blocker_status = str(blocker_item.get('status', '')).strip()
        if blocker_status in _RESOLVED_DEPENDENCY_STATUSES:
            continue
        unresolved_blockers.append(
            {'item_id': blocker_id, 'status': blocker_status or 'unknown', 'reason': 'blocker_not_resolved'}
        )
        blockers.append(
            f'Blocked-by item must be resolved before start: {blocker_id} (status={blocker_status or "unknown"})'
        )

    if dependencies and not unresolved_dependencies:
        warnings.append('Dependencies are present and currently resolved.')

    return {
        'payload': {
            'total_dependencies': len(dependencies),
            'resolved_dependencies': resolved_dependencies,
            'unresolved_dependencies': unresolved_dependencies,
            'total_blocked_by': len(blocked_by),
            'unresolved_blockers': unresolved_blockers,
        },
        'blockers': blockers,
        'warnings': warnings,
    }


def _inspect_registry_binding_readiness(
    *,
    repo_root: Path,
    project_id: str,
    repo_id: str,
    registry_path: str | Path | None,
) -> dict[str, list[str]]:
    blockers: list[str] = []
    warnings: list[str] = []

    if not project_id:
        blockers.append('Queue item project_id is missing.')
    if not repo_id:
        blockers.append('Queue item repo_id is missing.')
    if blockers:
        return {'blockers': blockers, 'warnings': warnings}

    project_lookup = _lookup_registry_project(
        repo_root=repo_root,
        project_id=project_id,
        registry_path=registry_path,
    )
    warnings.extend(
        str(warning).strip()
        for warning in project_lookup.get('warnings', [])
        if str(warning).strip()
    )
    if not project_lookup.get('ok', False):
        details = project_lookup.get('details', {}) if isinstance(project_lookup.get('details'), dict) else {}
        blockers.append(str(details.get('message', project_lookup.get('error', 'registry_validation_failed'))))
        return {'blockers': blockers, 'warnings': warnings}
    if project_lookup.get('project') is None:
        warnings.append('Managed project registry is unavailable for project/repo validation.')
        return {'blockers': blockers, 'warnings': warnings}

    binding = _validate_registry_binding(
        repo_root=repo_root,
        project_id=project_id,
        repo_id=repo_id,
        registry_path=registry_path,
    )
    warnings.extend(
        str(warning).strip()
        for warning in binding.get('warnings', [])
        if str(warning).strip()
    )
    if not binding.get('ok', False):
        details = binding.get('details', {}) if isinstance(binding.get('details'), dict) else {}
        blockers.append(str(details.get('message', binding.get('error', 'registry_binding_invalid'))))

    return {
        'blockers': sorted(set(blockers)),
        'warnings': sorted(set(warnings)),
    }


def _recommended_queue_item_next_action(
    *,
    item_id: str,
    status: str,
    readiness_status: str,
    missing_fields: list[str],
    dependency_payload: dict[str, Any],
    binding_blockers: list[str],
) -> str:
    if readiness_status == 'ready':
        return f'Queue item is ready to start. Continue local operator work for {item_id}.'
    if readiness_status == 'not_found':
        return 'Inspect the local queue and choose a valid item_id.'
    if binding_blockers:
        return 'Repair local project/repo registry bindings before starting work.'
    if list(dependency_payload.get('unresolved_dependencies', [])) or list(dependency_payload.get('unresolved_blockers', [])):
        return 'Resolve or complete local queue dependencies before starting work.'
    if missing_fields:
        return 'Fill missing queue item execution fields before starting work.'
    if status == 'proposed':
        return f'Move {item_id} to ready after execution prep is complete.'
    if status == 'in_progress':
        return 'Continue the in-progress item instead of starting it again.'
    if status in {'done', 'cancelled'}:
        return 'No start action is available for completed or cancelled items.'
    if status == 'blocked':
        return 'Resolve the blocked state before attempting to start this queue item.'
    return 'Inspect the queue item and resolve remaining local readiness gaps.'


def _compose_intake_notes(
    *,
    acceptance_criteria: list[str] | None,
    acceptance_notes: list[str] | None,
    validation_notes: list[str] | None,
    requested_outcome: str | None,
) -> str | None:
    criteria = _normalize_list((acceptance_criteria or []) + (acceptance_notes or []))
    validations = _normalize_list(validation_notes or [])
    outcome = str(requested_outcome or '').strip()
    lines: list[str] = []
    if criteria:
        lines.extend(['Acceptance criteria:'] + [f'- {criterion}' for criterion in criteria])
    if outcome:
        if lines:
            lines.append('')
        lines.extend(['Requested outcome:', f'- {outcome}'])
    if validations:
        if lines:
            lines.append('')
        lines.extend(['Validation notes:'] + [f'- {item}' for item in validations])
    if not lines:
        return None
    return '\n'.join(lines)


def _parse_queue_item_notes(notes: str) -> dict[str, Any]:
    stripped = str(notes or '').strip()
    if not stripped:
        return {
            'acceptance_criteria': [],
            'notes': '',
        }

    lines = [line.rstrip() for line in stripped.splitlines()]
    if lines and lines[0].strip().lower() == 'acceptance criteria:':
        acceptance_criteria: list[str] = []
        remaining: list[str] = []
        for line in lines[1:]:
            normalized = line.strip()
            if normalized.startswith('- '):
                criterion = normalized[2:].strip()
                if criterion:
                    acceptance_criteria.append(criterion)
                continue
            if normalized:
                remaining.append(normalized)
        return {
            'acceptance_criteria': _normalize_list(acceptance_criteria),
            'notes': '\n'.join(remaining).strip(),
        }

    return {
        'acceptance_criteria': [],
        'notes': stripped,
    }


def _infer_target_area(item: dict[str, Any]) -> str:
    tags = item.get('tags', []) if isinstance(item.get('tags'), list) else []
    for tag in tags:
        normalized = str(tag).strip()
        if normalized.startswith('area:'):
            return normalized.split(':', 1)[1].strip()
    return ''


def _render_local_queue_item_codex_prompt(
    *,
    repo_root: Path,
    item: dict[str, Any],
    readiness: dict[str, Any],
    target_area: str,
    acceptance_criteria: list[str],
    extra_notes: str,
    commit_message: str | None,
) -> str:
    description = str(item.get('description', '')).strip()
    title = str(item.get('title', '')).strip()
    normalized_commit_message = str(commit_message or '').strip() or f'Implement {title}'
    blockers = [
        str(blocker).strip()
        for blocker in readiness.get('blockers', [])
        if str(blocker).strip()
    ]
    warnings = [
        str(warning).strip()
        for warning in readiness.get('warnings', [])
        if str(warning).strip()
    ]
    dependency_summary = (
        readiness.get('dependency_summary', {}) if isinstance(readiness.get('dependency_summary'), dict) else {}
    )
    unresolved_dependencies = dependency_summary.get('unresolved_dependencies', [])
    unresolved_blockers = dependency_summary.get('unresolved_blockers', [])

    lines = [
        '# Codex Prompt Package',
        '',
        '## Task',
        f"- Queue item ID: {str(item.get('item_id', '')).strip()}",
        f'- Queue item title: {title}',
        f"- Queue item status: {str(item.get('status', '')).strip()}",
        f'- Queue item description: {description or "No explicit description provided."}',
        '',
        '## Repository Context',
        '- Repository: aresforge',
        f'- Repository path: {repo_root}',
        '- Base branch: main',
        '- Working mode: local-first, direct on main',
        '',
        '## Purpose And Boundary',
        '- This prompt package is a review/input artifact only. It does not approve, merge, close, automate, bypass human review, change repository settings, or authorize future automation.',
        '- Work locally first.',
        '- Work directly on main.',
        '- Keep changes small and focused.',
        '- Preserve existing behavior and tests.',
        '- Avoid placeholders.',
        '- Avoid nested markdown fences inside PowerShell here-strings.',
        '',
        '## Required Source-Of-Truth Reading List',
        '- docs/context/AGENT_CONTEXT.md',
        '- docs/context/BUILD_STATE.md',
        '- docs/roadmap/ROADMAP.md',
        '- docs/prompts/CODEX_PROMPT_STANDARD.md',
        '- docs/prompts/CODEX_PROMPT_PACKAGE_TEMPLATE.md',
        '- docs/architecture/LOCAL_OPERATOR_WORKFLOW.md',
        '- docs/learning/ERROR_PATTERNS.md',
        '',
        '## Goal',
        f'- Implement the queue item: {title}.',
        '- Validate the change locally.',
        '- Commit only after all required tests pass.',
        '',
        '## Required Changes',
        f'- Target area: {target_area or "Not explicitly tagged."}',
        f"- Project ID: {str(item.get('project_id', '')).strip()}",
        f"- Repo ID: {str(item.get('repo_id', '')).strip()}",
    ]

    if acceptance_criteria:
        lines.extend([
            '',
            '## Acceptance Criteria',
            *[f'- {criterion}' for criterion in acceptance_criteria],
        ])
    else:
        lines.extend([
            '',
            '## Acceptance Criteria',
            '- No explicit acceptance criteria were stored on the queue item. Derive the narrowest correct implementation from the description and source-of-truth docs.',
        ])

    if extra_notes:
        lines.extend([
            '',
            '## Additional Notes',
            extra_notes,
        ])

    lines.extend([
        '',
        '## Local-Only Constraints',
        '- Do not push.',
        '- Do not use GitHub API, gh, GitHub issues, pull requests, workflow activity, or GitHub mutation.',
        '- Do not implement Hub mutation UI in this task.',
        '- Do not implement automatic Codex execution.',
        '- Do not implement agent execution.',
        '- Do not implement LLM routing.',
        '- Do not implement GitHub sync or GitHub mutation.',
        '- Leave unrelated local changes untouched and stage only files required for this work.',
        '',
        '## Readiness Snapshot',
        f"- Readiness status: {str(readiness.get('readiness_status', '')).strip()}",
    ])
    if blockers:
        lines.extend(['- Current blockers:'] + [f'- {blocker}' for blocker in blockers])
    else:
        lines.append('- Current blockers: none')
    if warnings:
        lines.extend(['- Current warnings:'] + [f'- {warning}' for warning in warnings])
    else:
        lines.append('- Current warnings: none')
    if unresolved_dependencies:
        lines.extend(
            ['- Unresolved dependencies:']
            + [
                f"- {str(entry.get('item_id', '')).strip()} ({str(entry.get('status', '')).strip()} / {str(entry.get('reason', '')).strip()})"
                for entry in unresolved_dependencies
                if isinstance(entry, dict)
            ]
        )
    if unresolved_blockers:
        lines.extend(
            ['- External blockers:']
            + [
                f"- {str(entry.get('item_id', '')).strip()} ({str(entry.get('status', '')).strip()} / {str(entry.get('reason', '')).strip()})"
                for entry in unresolved_blockers
                if isinstance(entry, dict)
            ]
        )

    lines.extend([
        '',
        '## Validation',
        '- Run these commands before committing:',
        '- git diff --check',
        '- python -m pytest tests/test_roadmap_db_control.py tests/test_config_and_migrations.py tests/test_cli.py',
        '- python -m pytest tests/test_local_queue_agent_summary.py tests/test_local_project_dashboard.py tests/test_local_project_report.py',
        '- python -m pytest tests/test_local_project_queue.py tests/test_cli_local_project_queue.py',
        '- Run any narrower targeted tests required for the files you touch.',
        '',
        '## Commit Expectations',
        '- Only commit after all required validation commands succeed.',
        f'- Commit message guidance: {normalized_commit_message}',
        '- Do not amend unrelated work.',
        '- Do not push.',
        '',
        '## Evidence To Report Back',
        '- Changed files.',
        '- Validation commands and outcomes.',
        '- Any smoke checks performed locally.',
        '- Commit hash.',
        '- Current git status.',
    ])

    return '\n'.join(lines).rstrip()


def _generate_local_queue_item_id(
    *,
    repo_root: Path,
    queue: dict[str, Any],
    title: str,
    project_id: str,
    repo_id: str,
) -> str:
    existing_ids = {
        str(item.get('item_id', '')).strip()
        for item in queue.get('work_items', [])
        if isinstance(item, dict) and str(item.get('item_id', '')).strip()
    }
    prefix = _resolve_local_queue_item_prefix(
        repo_root=repo_root,
        queue=queue,
        project_id=project_id,
        repo_id=repo_id,
    )
    base_id = f'{prefix}-{_slugify(title)}' if prefix else _slugify(title)
    candidate = base_id
    suffix = 2
    while candidate in existing_ids:
        candidate = f'{base_id}-{suffix}'
        suffix += 1
    return candidate


def _resolve_local_queue_item_prefix(
    *,
    repo_root: Path,
    queue: dict[str, Any],
    project_id: str,
    repo_id: str,
) -> str:
    current_milestone = _load_current_milestone(repo_root)
    if current_milestone:
        return current_milestone

    scoped_items = [
        item
        for item in queue.get('work_items', [])
        if isinstance(item, dict)
        and str(item.get('project_id', '')).strip() == project_id
        and str(item.get('repo_id', '')).strip() == repo_id
    ]
    inferred = _infer_prefix_from_items(scoped_items)
    if inferred:
        return inferred

    all_items = [item for item in queue.get('work_items', []) if isinstance(item, dict)]
    inferred = _infer_prefix_from_items(all_items)
    if inferred:
        return inferred
    return 'local'


def _load_current_milestone(repo_root: Path) -> str:
    path = resolve_project_state_path(repo_root, None)
    if not path.exists():
        return ''
    try:
        raw = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return ''
    if not isinstance(raw, dict):
        return ''
    current_milestone = str(raw.get('current_milestone', '')).strip()
    if not current_milestone:
        return ''
    return _slugify(current_milestone)


def _infer_prefix_from_items(items: list[dict[str, Any]]) -> str:
    counts: dict[str, int] = {}
    for item in items:
        item_id = str(item.get('item_id', '')).strip()
        if '-' not in item_id:
            continue
        prefix, remainder = item_id.split('-', 1)
        normalized_prefix = _slugify(prefix)
        if not normalized_prefix or not remainder.strip():
            continue
        counts[normalized_prefix] = counts.get(normalized_prefix, 0) + 1
    if not counts:
        return ''
    return sorted(counts.items(), key=lambda entry: (-entry[1], entry[0]))[0][0]


def _slugify(value: str) -> str:
    normalized = _SLUG_NON_ALNUM_RE.sub('-', value.strip().lower()).strip('-')
    return normalized or 'item'


def _lookup_registry_project(
    *,
    repo_root: Path,
    project_id: str,
    registry_path: str | Path | None,
) -> dict[str, Any]:
    warnings: list[str] = []
    should_validate = False
    resolved_registry_path: Path | None = None

    if registry_path is not None:
        should_validate = True
        resolved_registry_path = resolve_managed_project_registry_path(repo_root, registry_path)
    else:
        default_registry = resolve_managed_project_registry_path(repo_root, None)
        if default_registry.exists():
            should_validate = True
            resolved_registry_path = default_registry

    if not should_validate:
        warnings.append('Managed project registry not found. Registry validation was skipped.')
        return {
            'ok': True,
            'project': None,
            'warnings': warnings,
        }

    assert resolved_registry_path is not None
    if not resolved_registry_path.exists():
        return _error(
            'managed_project_registry_not_found',
            {
                'path': str(resolved_registry_path),
                'message': 'Managed project registry is missing for queue validation.',
            },
        )

    try:
        raw = json.loads(resolved_registry_path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as exc:
        return _error(
            'managed_project_registry_invalid_json',
            {
                'path': str(resolved_registry_path),
                'message': str(exc),
            },
        )

    if not isinstance(raw, dict):
        return _error(
            'managed_project_registry_invalid_schema',
            {
                'path': str(resolved_registry_path),
                'message': 'Managed project registry JSON must decode to an object.',
            },
        )

    projects = raw.get('projects', []) if isinstance(raw.get('projects'), list) else []
    project = next(
        (
            candidate
            for candidate in projects
            if isinstance(candidate, dict)
            and str(candidate.get('project_id', '')).strip() == project_id
        ),
        None,
    )
    if project is None:
        return _error(
            'managed_project_not_found',
            {
                'project_id': project_id,
                'registry_path': str(resolved_registry_path),
                'message': 'Project id was not found in managed project registry.',
            },
        )

    return {
        'ok': True,
        'project': project,
        'warnings': warnings,
    }


def _project_primary_repo_id(project: dict[str, Any]) -> str:
    primary_repo_id = str(project.get('primary_repo_id', '')).strip()
    repos = project.get('repos', []) if isinstance(project.get('repos'), list) else []
    if primary_repo_id:
        return primary_repo_id
    for repo in repos:
        if isinstance(repo, dict) and str(repo.get('role', '')).strip() == 'primary':
            return str(repo.get('repo_id', '')).strip()
    first = repos[0] if repos else None
    if isinstance(first, dict):
        return str(first.get('repo_id', '')).strip()
    return ''


def _item_view(item: dict[str, Any]) -> dict[str, Any]:
    return {
        'item_id': str(item.get('item_id', '')).strip(),
        'project_id': str(item.get('project_id', '')).strip(),
        'repo_id': str(item.get('repo_id', '')).strip(),
        'title': str(item.get('title', '')).strip(),
        'description': str(item.get('description', '')).strip(),
        'status': str(item.get('status', '')).strip(),
        'priority': str(item.get('priority', '')).strip(),
        'item_type': str(item.get('item_type', '')).strip(),
        'tags': _normalize_list(item.get('tags', []) if isinstance(item.get('tags'), list) else []),
        'dependencies': _normalize_list(
            item.get('dependencies', []) if isinstance(item.get('dependencies'), list) else []
        ),
        'blocked_by': _normalize_list(item.get('blocked_by', []) if isinstance(item.get('blocked_by'), list) else []),
        'assigned_agent': str(item.get('assigned_agent', '')).strip(),
        'source': str(item.get('source', '')).strip(),
        'notes': str(item.get('notes', '')).strip(),
        'started_at': str(item.get('started_at', '')).strip(),
        'started_via': str(item.get('started_via', '')).strip(),
        'previous_status': str(item.get('previous_status', '')).strip(),
        'completed_at': str(item.get('completed_at', '')).strip(),
        'completed_by': str(item.get('completed_by', '')).strip(),
        'completion_commit': str(item.get('completion_commit', '')).strip(),
        'validation_summary': str(item.get('validation_summary', '')).strip(),
        'evidence_note': str(item.get('evidence_note', '')).strip(),
        'tests_run': _normalize_list(item.get('tests_run', []) if isinstance(item.get('tests_run'), list) else []),
        'changed_files': _normalize_list(
            item.get('changed_files', []) if isinstance(item.get('changed_files'), list) else []
        ),
        'artifact_paths': _normalize_list(
            item.get('artifact_paths', []) if isinstance(item.get('artifact_paths'), list) else []
        ),
        'created_at': str(item.get('created_at', '')).strip(),
        'updated_at': str(item.get('updated_at', '')).strip(),
    }


def _dependency_warnings(item: dict[str, Any], queue_items: list[dict[str, Any]]) -> list[str]:
    existing_ids = {
        str(candidate.get('item_id', '')).strip()
        for candidate in queue_items
        if isinstance(candidate, dict) and str(candidate.get('item_id', '')).strip()
    }
    warnings: list[str] = []
    for field_name in ('dependencies', 'blocked_by'):
        values = item.get(field_name, [])
        if not isinstance(values, list):
            continue
        for value in values:
            normalized = str(value).strip()
            if not normalized:
                continue
            if normalized not in existing_ids:
                warnings.append(
                    f"{field_name} reference not found in queue yet: {normalized}. Saved for future linkage."
                )
    return warnings


def _validate_registry_binding(
    *,
    repo_root: Path,
    project_id: str,
    repo_id: str,
    registry_path: str | Path | None,
) -> dict[str, Any]:
    should_validate = False
    resolved_registry_path: Path | None = None
    warnings: list[str] = []

    if registry_path is not None:
        should_validate = True
        resolved_registry_path = resolve_managed_project_registry_path(repo_root, registry_path)
    else:
        default_registry = resolve_managed_project_registry_path(repo_root, None)
        if default_registry.exists():
            should_validate = True
            resolved_registry_path = default_registry

    if not should_validate:
        warnings.append('Managed project registry not found. Registry validation was skipped.')
        return {
            'ok': True,
            'warnings': warnings,
        }

    assert resolved_registry_path is not None
    if not resolved_registry_path.exists():
        return _error(
            'managed_project_registry_not_found',
            {
                'path': str(resolved_registry_path),
                'message': 'Managed project registry is missing for queue validation.',
            },
        )

    try:
        raw = json.loads(resolved_registry_path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as exc:
        return _error(
            'managed_project_registry_invalid_json',
            {
                'path': str(resolved_registry_path),
                'message': str(exc),
            },
        )

    if not isinstance(raw, dict):
        return _error(
            'managed_project_registry_invalid_schema',
            {
                'path': str(resolved_registry_path),
                'message': 'Managed project registry JSON must decode to an object.',
            },
        )

    normalized_project_id = project_id.strip()
    normalized_repo_id = repo_id.strip()

    projects = raw.get('projects', []) if isinstance(raw.get('projects'), list) else []
    project = next(
        (
            candidate
            for candidate in projects
            if isinstance(candidate, dict)
            and str(candidate.get('project_id', '')).strip() == normalized_project_id
        ),
        None,
    )
    if project is None:
        return _error(
            'managed_project_not_found',
            {
                'project_id': normalized_project_id,
                'registry_path': str(resolved_registry_path),
                'message': 'Project id was not found in managed project registry.',
            },
        )

    repos = project.get('repos', []) if isinstance(project.get('repos'), list) else []
    repo = next(
        (
            candidate
            for candidate in repos
            if isinstance(candidate, dict)
            and str(candidate.get('repo_id', '')).strip() == normalized_repo_id
        ),
        None,
    )
    if repo is None:
        return _error(
            'managed_repo_not_found',
            {
                'project_id': normalized_project_id,
                'repo_id': normalized_repo_id,
                'registry_path': str(resolved_registry_path),
                'message': 'Repo id was not found under supplied project id in managed project registry.',
            },
        )

    return {
        'ok': True,
        'warnings': warnings,
    }


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


def _render_queue_markdown(payload: dict[str, Any]) -> str:
    lines = [
        '# Local Project Queue',
        '',
        f"- queue_path: {payload.get('queue_path')}",
        f"- schema_version: {payload.get('schema_version')}",
        f"- updated_at: {payload.get('updated_at')}",
        f"- item_count: {payload.get('item_count')}",
        '',
        '## Work Items',
    ]
    items = payload.get('work_items', [])
    if not isinstance(items, list) or not items:
        lines.append('- None')
        return '\n'.join(lines)

    for item in items:
        if not isinstance(item, dict):
            continue
        lines.append(
            f"- {item.get('item_id')} | {item.get('title')} | status={item.get('status')} | priority={item.get('priority')} | type={item.get('item_type')}"
        )
    return '\n'.join(lines)


def _render_queue_item_markdown(payload: dict[str, Any]) -> str:
    item = payload.get('item', {}) if isinstance(payload.get('item'), dict) else {}
    return '\n'.join(
        [
            '# Local Queue Item Inspection',
            '',
            f"- queue_path: {payload.get('queue_path')}",
            f"- item_id: {item.get('item_id')}",
            f"- project_id: {item.get('project_id')}",
            f"- repo_id: {item.get('repo_id')}",
            f"- title: {item.get('title')}",
            f"- status: {item.get('status')}",
            f"- priority: {item.get('priority')}",
            f"- item_type: {item.get('item_type')}",
            f"- assigned_agent: {item.get('assigned_agent')}",
            f"- tags: {', '.join(item.get('tags', [])) if isinstance(item.get('tags'), list) else ''}",
            f"- dependencies: {', '.join(item.get('dependencies', [])) if isinstance(item.get('dependencies'), list) else ''}",
            f"- blocked_by: {', '.join(item.get('blocked_by', [])) if isinstance(item.get('blocked_by'), list) else ''}",
            f"- source: {item.get('source')}",
            f"- notes: {item.get('notes')}",
            f"- started_at: {item.get('started_at')}",
            f"- started_via: {item.get('started_via')}",
            f"- previous_status: {item.get('previous_status')}",
            f"- completed_at: {item.get('completed_at')}",
            f"- completed_by: {item.get('completed_by')}",
            f"- completion_commit: {item.get('completion_commit')}",
            f"- validation_summary: {item.get('validation_summary')}",
            f"- evidence_note: {item.get('evidence_note')}",
            f"- tests_run: {', '.join(item.get('tests_run', [])) if isinstance(item.get('tests_run'), list) else ''}",
            f"- changed_files: {', '.join(item.get('changed_files', [])) if isinstance(item.get('changed_files'), list) else ''}",
            f"- artifact_paths: {', '.join(item.get('artifact_paths', [])) if isinstance(item.get('artifact_paths'), list) else ''}",
            f"- created_at: {item.get('created_at')}",
            f"- updated_at: {item.get('updated_at')}",
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
