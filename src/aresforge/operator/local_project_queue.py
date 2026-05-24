from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
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


def _normalize_list(values: list[str]) -> list[str]:
    normalized: list[str] = []
    for value in values:
        item = str(value).strip()
        if item and item not in normalized:
            normalized.append(item)
    return normalized


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
