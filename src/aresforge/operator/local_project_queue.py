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
_STARTABLE_QUEUE_STATUSES: frozenset[str] = frozenset({'ready'})
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
    dependencies: list[str] | None = None,
    tags: list[str] | None = None,
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
        source='local_cli',
        notes=_compose_notes_with_acceptance_criteria(acceptance_criteria),
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
        blockers.append('Managed project registry is unavailable for project/repo validation.')
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


def _compose_notes_with_acceptance_criteria(acceptance_criteria: list[str] | None) -> str | None:
    criteria = _normalize_list(acceptance_criteria or [])
    if not criteria:
        return None
    return '\n'.join(['Acceptance criteria:'] + [f'- {criterion}' for criterion in criteria])


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
