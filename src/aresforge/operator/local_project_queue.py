from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from aresforge.config import AppConfig
from aresforge.operator.local_ai_action_safety import evaluate_ai_action_safety_gate
from aresforge.operator.local_ai_artifacts import artifact_warning, register_ai_artifact
from aresforge.operator.local_execution_audit import append_execution_audit_entry, audit_warning
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
    'architecture',
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
QUEUE_ROUTING_AGENT_LANES: tuple[str, ...] = (
    'architect_planner',
    'coding',
    'reviewer_validator',
    'documentation',
    'test',
    'local_operator_assistant',
    'high_value_codex',
)
QUEUE_ROUTING_ENGINES: tuple[str, ...] = (
    'local_reasoning_llm',
    'local_coding_llm',
    'codex_cli',
)
QUEUE_ROUTING_RISK_LEVELS: tuple[str, ...] = (
    'low',
    'medium',
    'high',
    'critical',
    'unknown',
)
QUEUE_ROUTING_COMPLEXITY_LEVELS: tuple[str, ...] = (
    'low',
    'medium',
    'high',
    'unknown',
)
QUEUE_ROUTING_METADATA_FIELDS: tuple[str, ...] = (
    'recommended_agent_lane',
    'recommended_engine',
    'recommended_model',
    'fallback_engine',
    'fallback_model',
    'routing_policy_source',
    'routing_reason',
    'risk_level',
    'complexity_level',
    'escalation_reason',
    'project_ai_mode',
    'operator_override',
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
_QUEUE_ITEM_EVIDENCE_BOUNDARY_CONFIRMATIONS: tuple[str, ...] = (
    'Local-only queue item completion evidence capture.',
    'File-backed local queue evidence mutation only.',
    'No queue item completion is performed.',
    'No GitHub API calls.',
    'No gh calls.',
    'No network service calls.',
    'No agent execution.',
    'No model invocation.',
    'No remote commit or push verification.',
)
_QUEUE_ITEM_CLOSEOUT_BOUNDARY_CONFIRMATIONS: tuple[str, ...] = (
    'Local-only queue item closeout workflow.',
    'File-backed local queue mutation only.',
    'Requires captured completion evidence.',
    'No GitHub API calls.',
    'No gh calls.',
    'No network service calls.',
    'No agent execution.',
    'No model invocation.',
    'No prompt generation or execution.',
)
_PROJECT_PROGRESS_ROLLUP_BOUNDARY_CONFIRMATIONS: tuple[str, ...] = (
    'Local-only project progress rollup.',
    'Read-only local queue and project inspection.',
    'No GitHub API calls.',
    'No gh calls.',
    'No network service calls.',
    'No agent execution.',
    'No model invocation.',
    'No prompt generation or execution.',
    'No queue mutation performed.',
)
_QUEUE_CONSISTENCY_BOUNDARY_CONFIRMATIONS: tuple[str, ...] = (
    'Local-only queue consistency inspection.',
    'Read-only dependency and completion lock inspection.',
    'No queue mutation performed.',
    'No GitHub API calls.',
    'No gh calls.',
    'No network service calls.',
    'No agent execution.',
    'No model invocation.',
)
_ROUTED_QUEUE_VIEWS_BOUNDARY_CONFIRMATIONS: tuple[str, ...] = (
    'Local-only routed queue views.',
    'Read-only filtered view over the canonical local queue.',
    'No queue storage split.',
    'No queue mutation performed.',
    'No prompt generation or execution.',
    'No GitHub API calls.',
    'No gh calls.',
    'No network service calls.',
    'No agent execution.',
    'No model invocation.',
)
_QUEUE_ROUTING_METADATA_BOUNDARY_CONFIRMATIONS: tuple[str, ...] = (
    'Local-only queue routing metadata contract.',
    'File-backed local queue metadata mutation only.',
    'No routing decision is computed.',
    'No prompt generation or execution.',
    'No GitHub API calls.',
    'No gh calls.',
    'No network service calls.',
    'No agent execution.',
    'No model invocation.',
)
_CODEX_HIGH_VALUE_LANE_BOUNDARY_CONFIRMATIONS: tuple[str, ...] = (
    'Local-only Codex CLI high-value lane prompt generation.',
    'Canonical local queue remains the source of truth.',
    'Prompt output is advisory and copy/paste/operator-controlled.',
    'No automatic Codex execution.',
    'No Codex CLI command is executed.',
    'No GitHub API calls.',
    'No gh calls.',
    'No GitHub issues, PRs, workflows, or mutation.',
    'No repository files are mutated from Codex output.',
    'No local LLM execution is changed or performed.',
)
_STARTABLE_QUEUE_STATUSES: frozenset[str] = frozenset({'proposed', 'ready'})
_COMPLETABLE_QUEUE_STATUSES: frozenset[str] = frozenset({'in_progress'})
_RESOLVED_DEPENDENCY_STATUSES: frozenset[str] = frozenset({'done'})
_BLOCKED_QUEUE_STATUSES: frozenset[str] = frozenset({'blocked'})
_CODEX_DISPATCH_RUNS_RELATIVE = Path('.aresforge') / 'codex_dispatch' / 'runs'
_CODEX_DISPATCH_RUN_STATE_FILE_NAME = 'run_state.json'
_BLOCKING_DISPATCH_STATES: frozenset[str] = frozenset(
    {
        'awaiting_operator_approval',
        'approved_pending_dispatch',
        'running',
        'review_required',
    }
)
_DISPATCH_STATES_REQUIRING_REVIEW_EVIDENCE: frozenset[str] = frozenset({'completed', 'failed'})

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
    depends_on: list[str] | None = None,
    blocked_by: list[str] | None = None,
    completion_requires: list[str] | None = None,
    evidence_required: list[str] | None = None,
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
            'depends_on': [],
            'blocked_by': [],
            'completion_requires': [],
            'evidence_required': [],
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
            'completion_evidence': {},
            'routing_metadata': default_queue_routing_metadata(),
            'closed_at': '',
            'closed_by': '',
            'closeout_summary': '',
            'closeout_history': [],
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
    if depends_on is not None and len(depends_on) > 0:
        existing['depends_on'] = _normalize_list(depends_on)
    elif created:
        existing['depends_on'] = []
    if blocked_by is not None and len(blocked_by) > 0:
        existing['blocked_by'] = _normalize_list(blocked_by)
    elif created:
        existing['blocked_by'] = []
    if completion_requires is not None and len(completion_requires) > 0:
        existing['completion_requires'] = _normalize_list(completion_requires)
    elif created:
        existing['completion_requires'] = []
    if evidence_required is not None and len(evidence_required) > 0:
        existing['evidence_required'] = _normalize_list(evidence_required)
    elif created:
        existing['evidence_required'] = []
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
    if 'routing_metadata' not in existing or not isinstance(existing.get('routing_metadata'), dict):
        existing['routing_metadata'] = default_queue_routing_metadata()
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
    depends_on: list[str] | None = None,
    blocked_by: list[str] | None = None,
    completion_requires: list[str] | None = None,
    evidence_required: list[str] | None = None,
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
    if depends_on is not None:
        existing['depends_on'] = _normalize_list(depends_on)
        updated_fields.append('depends_on')
    if blocked_by is not None:
        existing['blocked_by'] = _normalize_list(blocked_by)
        updated_fields.append('blocked_by')
    if completion_requires is not None:
        existing['completion_requires'] = _normalize_list(completion_requires)
        updated_fields.append('completion_requires')
    if evidence_required is not None:
        existing['evidence_required'] = _normalize_list(evidence_required)
        updated_fields.append('evidence_required')
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


def update_local_queue_item_routing_metadata(
    config: AppConfig,
    *,
    item_id: str,
    routing_metadata: dict[str, Any],
    queue_path: str | Path | None = None,
) -> dict[str, Any]:
    if not isinstance(routing_metadata, dict):
        return _error(
            'invalid_queue_routing_metadata',
            {
                'message': 'routing_metadata must be a JSON object.',
                'supported_fields': list(QUEUE_ROUTING_METADATA_FIELDS),
            },
        )

    normalized_metadata = default_queue_routing_metadata(routing_metadata)
    validation = validate_queue_routing_metadata(normalized_metadata)
    if not validation.get('valid', False):
        return _error(
            'queue_routing_metadata_validation_failed',
            {
                'message': 'Queue routing metadata failed validation.',
                'item_id': str(item_id or '').strip(),
                'routing_metadata': normalized_metadata,
                'validation': validation,
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

    normalized_item_id = str(item_id or '').strip()
    item = next(
        (
            candidate
            for candidate in items
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

    now = _now_iso()
    item['routing_metadata'] = normalized_metadata
    item['updated_at'] = now
    if not item.get('created_at'):
        item['created_at'] = now
    queue['work_items'] = items
    queue['updated_at'] = now
    _write_queue(resolved_queue_path, queue)

    audit_result = append_execution_audit_entry(
        config,
        action_type='routing_metadata_update',
        project_id=str(item.get('project_id', '')).strip(),
        item_id=normalized_item_id,
        engine=str(normalized_metadata.get('recommended_engine', '')).strip(),
        model=str(normalized_metadata.get('recommended_model', '')).strip(),
        agent_lane=str(normalized_metadata.get('recommended_agent_lane', '')).strip(),
        operator_gate_confirmed=True,
        dry_run=False,
        executed=False,
        execution_allowed=False,
        outcome='updated',
        blockers=[],
        warnings=list(validation.get('warnings', [])),
        summary='Routing metadata updated locally; no routing execution or model invocation performed.',
        source_function='update_local_queue_item_routing_metadata',
    )

    return {
        'command': 'update-local-queue-item-routing-metadata',
        'ok': True,
        'local_only': True,
        'queue_path': str(resolved_queue_path),
        'item_id': normalized_item_id,
        'routing_metadata': normalized_metadata,
        'validation': validation,
        'next_safe_action': 'review_routing_metadata_as_non_executing_queue_context',
        'warnings': sorted(set(list(validation.get('warnings', [])) + audit_warning(audit_result))),
        'blockers': [],
        'item': _item_view(item),
        'boundary_confirmations': list(_QUEUE_ROUTING_METADATA_BOUNDARY_CONFIRMATIONS),
    }


def generate_local_llm_prompt_preview(
    config: AppConfig,
    *,
    item_id: str,
    prompt_style: str | None = None,
    include_context: bool = True,
    include_validation_expectations: bool = True,
    queue_path: str | Path | None = None,
    registry_path: str | Path | None = None,
    output: str | Path | None = None,
    force: bool = False,
) -> dict[str, Any]:
    normalized_item_id = str(item_id or '').strip()
    resolved_queue_path = resolve_project_queue_path(config.repo_root, queue_path)
    loaded = _load_queue_required(resolved_queue_path)
    if not loaded.get('ok', False):
        return loaded

    queue = loaded['queue']
    items = [_item_view(item) for item in queue.get('work_items', []) if isinstance(item, dict)]
    item = next((candidate for candidate in items if candidate.get('item_id') == normalized_item_id), None)
    if item is None:
        return _error(
            'queue_item_not_found',
            {
                'item_id': normalized_item_id,
                'message': 'Queue item was not found for local LLM prompt preview.',
            },
        )

    routing_metadata = default_queue_routing_metadata(item.get('routing_metadata', {}))
    recommended_engine = str(routing_metadata.get('recommended_engine', '')).strip()
    recommended_model = str(routing_metadata.get('recommended_model', '')).strip()
    project_id = str(item.get('project_id', '')).strip()
    warnings: list[str] = []
    blockers: list[str] = []

    environment = _read_local_llm_environment_for_preview(config.repo_root)
    if not environment.get('exists', False):
        blockers.append('Local LLM environment contract is required before generating a local LLM prompt preview.')
    local_environment = environment.get('environment', {}) if isinstance(environment.get('environment'), dict) else {}
    if environment.get('warnings'):
        warnings.extend([str(warning) for warning in environment.get('warnings', [])])
        blockers.append('Local LLM environment contract must be readable before generating a local LLM prompt preview.')
    if environment.get('exists', False) and local_environment:
        local_provider = str(local_environment.get('local_llm_provider', '')).strip()
        if local_provider in {'', 'none', 'unknown'}:
            blockers.append('Local LLM provider must be configured before generating a local LLM prompt preview.')
        if not isinstance(local_environment.get('execution_enabled'), bool):
            blockers.append('Local LLM environment execution_enabled must be boolean for prompt preview.')
        elif local_environment.get('execution_enabled') is True:
            warnings.append('Local LLM execution is enabled for the M62 operator-gated prototype; prompt preview remains non-executing.')
        if local_environment.get('operator_gate_required') is not True:
            blockers.append('Local LLM environment operator_gate_required must remain true for prompt preview.')

    project_ai_settings = _read_project_ai_settings_for_preview(config.repo_root, project_id)
    project_ai_mode = str(routing_metadata.get('project_ai_mode') or project_ai_settings.get('project_ai_mode', '')).strip()
    operator_override = routing_metadata.get('operator_override')
    risk_level = str(routing_metadata.get('risk_level', 'unknown')).strip() or 'unknown'
    complexity_level = str(routing_metadata.get('complexity_level', 'unknown')).strip() or 'unknown'

    if not _is_routed_metadata(routing_metadata):
        blockers.append('Queue item is unrouted; manual routing metadata is required for local LLM prompt preview.')
    if recommended_engine == 'codex_cli':
        blockers.append('Queue item is routed to codex_cli; use Codex prompt workflows instead of local LLM preview.')
    if recommended_engine and recommended_engine not in {'local_reasoning_llm', 'local_coding_llm'}:
        blockers.append('Queue item is not routed to a supported local LLM engine.')
    if not recommended_engine:
        blockers.append('Queue item routing metadata does not include a recommended local LLM engine.')
    if not recommended_model:
        if recommended_engine == 'local_reasoning_llm':
            recommended_model = str(local_environment.get('reasoning_model', '')).strip()
        elif recommended_engine == 'local_coding_llm':
            recommended_model = str(local_environment.get('coding_model', '')).strip()
    if recommended_engine in {'local_reasoning_llm', 'local_coding_llm'} and not recommended_model:
        blockers.append('Recommended local LLM model is missing from routing metadata and environment configuration.')
    if project_ai_mode == 'manual_only' and not operator_override:
        blockers.append('Project AI mode is manual_only; operator override is required before local LLM prompt preview.')
    if project_ai_mode == 'high_confidence' and risk_level in {'high', 'critical'}:
        warnings.append('High-confidence project policy with high-risk work may require Codex review before local LLM use.')
    if risk_level in {'high', 'critical'} and recommended_engine != 'local_reasoning_llm':
        warnings.append('High-risk local LLM preview should prefer local_reasoning_llm or Codex review.')

    preview_allowed = not blockers
    readiness = _evaluate_local_queue_item_readiness(
        repo_root=config.repo_root,
        item=item,
        items=items,
        registry_path=registry_path,
    )
    local_only_rules = [
        'Local-first only.',
        'Prompt preview only; do not execute this prompt from AresForge.',
        'No GitHub API, no gh, and no GitHub mutation.',
        'No Codex CLI execution.',
        'No local LLM inference or generation in this milestone.',
        'No agent execution.',
        'The local LLM must not claim execution if only reviewing or planning.',
    ]
    validation_expectations = [
        'Run targeted local pytest for touched areas.',
        'Run: python -m aresforge inspect-local-queue-agent-summary',
        'Run: python -m aresforge inspect-local-project-report',
        'Run: git diff --check',
    ] if include_validation_expectations else []
    final_response_format = [
        'Files changed',
        'What was changed',
        'Tests updated and why',
        'Validation results',
        'Smoke check results',
        'Diff check result',
        'Commit hash',
        'Push result',
    ]
    prompt_preview = _build_local_llm_prompt_preview_text(
        item=item,
        routing_metadata=routing_metadata,
        readiness=readiness,
        prompt_style=str(prompt_style or 'implementation_planning').strip() or 'implementation_planning',
        include_context=include_context,
        local_only_rules=local_only_rules,
        validation_expectations=validation_expectations,
        final_response_format=final_response_format,
        recommended_engine=recommended_engine,
        recommended_model=recommended_model,
        project_ai_mode=project_ai_mode,
    ) if preview_allowed else ''

    payload: dict[str, Any] = {
        'command': 'generate-local-llm-prompt-preview',
        'ok': preview_allowed,
        'local_only': True,
        'item_id': normalized_item_id,
        'recommended_engine': recommended_engine,
        'recommended_model': recommended_model,
        'preview_allowed': preview_allowed,
        'execution_allowed': False,
        'prompt_preview': prompt_preview,
        'local_only_rules': local_only_rules,
        'validation_expectations': validation_expectations,
        'final_response_format': final_response_format,
        'next_safe_action': 'Copy the preview manually only after operator review; no execution occurs.' if preview_allowed else 'Resolve blockers before generating a local LLM prompt preview.',
        'warnings': sorted(set(warnings)),
        'blockers': sorted(set(blockers)),
        'routing_metadata': routing_metadata,
        'environment_path': str(environment.get('path', '')),
        'boundary_confirmations': [
            'Local LLM prompt preview is local-only and non-executing.',
            'No Ollama call, local LLM call, Codex call, agent execution, prompt execution, GitHub API, gh, or external workflow is performed.',
        ],
    }

    if output is None:
        audit_result = append_execution_audit_entry(
            config,
            action_type='local_llm_prompt_preview' if preview_allowed else 'blocked_attempt',
            project_id=project_id,
            item_id=normalized_item_id,
            engine=recommended_engine,
            model=recommended_model,
            agent_lane=str(routing_metadata.get('recommended_agent_lane', '')).strip(),
            operator_gate_confirmed=False,
            dry_run=True,
            executed=False,
            execution_allowed=False,
            outcome='preview_generated' if preview_allowed else 'blocked',
            blockers=blockers,
            warnings=warnings,
            summary='Local LLM prompt preview generated.' if preview_allowed else 'Local LLM prompt preview blocked by local gates.',
            source_function='generate_local_llm_prompt_preview',
        )
        payload['warnings'] = sorted(set(payload['warnings'] + audit_warning(audit_result)))
        return payload
    output_path = Path(output)
    if output_path.exists() and not force:
        payload['ok'] = False
        payload['output_path'] = str(output_path)
        payload['warnings'] = sorted({*payload['warnings'], 'Output file already exists. Re-run with force=true to overwrite.'})
        audit_result = append_execution_audit_entry(
            config,
            action_type='blocked_attempt',
            project_id=project_id,
            item_id=normalized_item_id,
            engine=recommended_engine,
            model=recommended_model,
            agent_lane=str(routing_metadata.get('recommended_agent_lane', '')).strip(),
            dry_run=True,
            executed=False,
            execution_allowed=False,
            outcome='blocked',
            blockers=['Output file already exists.'],
            warnings=payload['warnings'],
            artifact_path=output_path,
            summary='Local LLM prompt preview artifact write blocked by non-overwrite gate.',
            source_function='generate_local_llm_prompt_preview',
        )
        payload['warnings'] = sorted(set(payload['warnings'] + audit_warning(audit_result)))
        return payload
    if not preview_allowed:
        payload['output_path'] = str(output_path)
        audit_result = append_execution_audit_entry(
            config,
            action_type='blocked_attempt',
            project_id=project_id,
            item_id=normalized_item_id,
            engine=recommended_engine,
            model=recommended_model,
            agent_lane=str(routing_metadata.get('recommended_agent_lane', '')).strip(),
            dry_run=True,
            executed=False,
            execution_allowed=False,
            outcome='blocked',
            blockers=blockers,
            warnings=warnings,
            artifact_path=output_path,
            summary='Local LLM prompt preview blocked by local gates.',
            source_function='generate_local_llm_prompt_preview',
        )
        payload['warnings'] = sorted(set(payload['warnings'] + audit_warning(audit_result)))
        return payload
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(prompt_preview + '\n', encoding='utf-8')
    except OSError as exc:
        payload['ok'] = False
        payload['output_path'] = str(output_path)
        payload['warnings'] = sorted({*payload['warnings'], f'Failed to write output file: {exc}'})
        audit_result = append_execution_audit_entry(
            config,
            action_type='blocked_attempt',
            project_id=project_id,
            item_id=normalized_item_id,
            engine=recommended_engine,
            model=recommended_model,
            agent_lane=str(routing_metadata.get('recommended_agent_lane', '')).strip(),
            dry_run=True,
            executed=False,
            execution_allowed=False,
            outcome='blocked',
            blockers=[f'Failed to write output file: {exc}'],
            warnings=payload['warnings'],
            artifact_path=output_path,
            summary='Local LLM prompt preview artifact write failed.',
            source_function='generate_local_llm_prompt_preview',
        )
        payload['warnings'] = sorted(set(payload['warnings'] + audit_warning(audit_result)))
        return payload
    payload['output_path'] = str(output_path)
    artifact_result = register_ai_artifact(
        config,
        artifact_type='local_llm_prompt_preview',
        artifact_path=output_path,
        source_action='local_llm_prompt_preview',
        project_id=project_id,
        item_id=normalized_item_id,
        engine=recommended_engine,
        model=recommended_model,
        agent_lane=str(routing_metadata.get('recommended_agent_lane', '')).strip(),
        summary='Local LLM prompt preview artifact generated for manual operator review.',
        warnings=warnings,
    )
    payload['artifact_registry'] = artifact_result.get('artifact', {})
    audit_result = append_execution_audit_entry(
        config,
        action_type='local_llm_prompt_preview',
        project_id=project_id,
        item_id=normalized_item_id,
        engine=recommended_engine,
        model=recommended_model,
        agent_lane=str(routing_metadata.get('recommended_agent_lane', '')).strip(),
        dry_run=True,
        executed=False,
        execution_allowed=False,
        outcome='preview_generated',
        blockers=[],
        warnings=warnings,
        artifact_path=output_path,
        summary='Local LLM prompt preview generated and written to a local artifact.',
        source_function='generate_local_llm_prompt_preview',
    )
    payload['warnings'] = sorted(set(payload['warnings'] + audit_warning(audit_result) + artifact_warning(artifact_result)))
    return payload


def execute_local_llm_for_queue_item(
    config: AppConfig,
    *,
    item_id: str,
    confirm_operator_gate: bool = False,
    use_preview: bool = True,
    output: str | Path | None = None,
    force: bool = False,
    operator_override: bool = False,
    dry_run: bool = False,
    queue_path: str | Path | None = None,
    registry_path: str | Path | None = None,
    health_check_fn: Any | None = None,
    provider_generate_fn: Any | None = None,
) -> dict[str, Any]:
    normalized_item_id = str(item_id or '').strip()
    captured_at = _now_iso()
    warnings: list[str] = []
    blockers: list[str] = []
    response_text = ''
    prompt_used = ''

    preview = generate_local_llm_prompt_preview(
        config,
        item_id=normalized_item_id,
        include_context=True,
        include_validation_expectations=True,
        queue_path=queue_path,
        registry_path=registry_path,
    )
    if preview.get('error') == 'queue_item_not_found':
        return _error(
            'queue_item_not_found',
            {
                'item_id': normalized_item_id,
                'message': 'Queue item was not found for local LLM execution.',
            },
        )
    warnings.extend([str(warning) for warning in preview.get('warnings', [])])
    blockers.extend([str(blocker) for blocker in preview.get('blockers', [])])
    if use_preview:
        prompt_used = str(preview.get('prompt_preview', ''))
    if not prompt_used and not blockers:
        blockers.append('Prompt preview is required before local LLM execution.')

    routing_metadata = preview.get('routing_metadata', {}) if isinstance(preview.get('routing_metadata'), dict) else {}
    recommended_engine = str(preview.get('recommended_engine', '')).strip()
    model = str(preview.get('recommended_model', '')).strip()
    risk_level = str(routing_metadata.get('risk_level', 'unknown')).strip() or 'unknown'
    project_ai_mode = str(routing_metadata.get('project_ai_mode', '')).strip()
    safety_gate = evaluate_ai_action_safety_gate(
        config,
        action_type='local_llm_execute',
        item_id=normalized_item_id,
        engine=recommended_engine,
        model=model,
        agent_lane=str(routing_metadata.get('recommended_agent_lane', '')).strip(),
        risk_level=risk_level,
        complexity_level=str(routing_metadata.get('complexity_level', 'unknown')).strip() or 'unknown',
        project_ai_mode=project_ai_mode,
        operator_override=operator_override,
        confirm_operator_gate=confirm_operator_gate,
        dry_run=dry_run,
        queue_path=queue_path,
    )
    blockers.extend([str(blocker) for blocker in safety_gate.get('blockers', [])])
    warnings.extend([str(warning) for warning in safety_gate.get('warnings', [])])

    environment = _read_local_llm_environment_for_preview(config.repo_root)
    local_environment = environment.get('environment', {}) if isinstance(environment.get('environment'), dict) else {}
    provider = str(local_environment.get('local_llm_provider', 'unknown')).strip() or 'unknown'
    provider_base_url = str(local_environment.get('provider_base_url', '')).strip()
    if provider != 'ollama':
        blockers.append('Only local provider ollama is supported for the M62 execution prototype.')
    if provider_base_url and not _is_local_llm_provider_url(provider_base_url):
        blockers.append('provider_base_url must point to localhost, 127.0.0.1, or ::1 for local LLM execution.')
    if local_environment.get('execution_enabled') is not True:
        blockers.append('Local LLM environment execution_enabled must be true for the M62 execution prototype.')
    if local_environment.get('operator_gate_required') is not True:
        blockers.append('Local LLM environment operator_gate_required must remain true for local LLM execution.')
    if project_ai_mode in {'codex_only', 'manual_only'} and not operator_override:
        blockers.append(f'Project AI mode {project_ai_mode} does not allow local execution without operator override.')
    if risk_level in {'high', 'critical'} and not operator_override:
        blockers.append('High or critical risk local LLM execution requires operator_override=true.')
    if recommended_engine not in {'local_reasoning_llm', 'local_coding_llm'}:
        blockers.append('Queue item must be routed to local_reasoning_llm or local_coding_llm for local LLM execution.')
    if not dry_run and not confirm_operator_gate:
        blockers.append('confirm_operator_gate must be true for real local LLM execution.')

    health_payload: dict[str, Any] = {}
    if not blockers and not dry_run:
        from aresforge.operator.local_project_factory import check_local_llm_health

        checker = health_check_fn or check_local_llm_health
        try:
            health_payload = checker(config)
        except TypeError:
            health_payload = checker()
        if not isinstance(health_payload, dict):
            blockers.append('Local LLM health check did not return a stable payload.')
        else:
            warnings.extend([str(warning) for warning in health_payload.get('warnings', [])])
            if not health_payload.get('provider_reachable', False):
                blockers.append('Local LLM provider health check must be reachable before execution.')
            available_models = health_payload.get('available_models', [])
            if isinstance(available_models, list) and model and model not in [str(value) for value in available_models]:
                blockers.append('Recommended local LLM model is not available according to the health check.')

    execution_allowed = not blockers and not dry_run
    executed = False
    if execution_allowed:
        generator = provider_generate_fn or _call_ollama_generate_for_queue_item
        try:
            response_text = generator(
                provider_base_url=provider_base_url,
                model=model,
                prompt=prompt_used,
                timeout_seconds=local_environment.get('request_timeout_seconds') if isinstance(local_environment.get('request_timeout_seconds'), int) else 60,
            )
        except (HTTPError, URLError, OSError, TimeoutError, ValueError) as exc:
            blockers.append(f'Local LLM provider execution failed: {exc}')
            execution_allowed = False
        else:
            executed = True

    payload: dict[str, Any] = {
        'command': 'execute-local-llm-for-queue-item',
        'ok': not blockers,
        'local_only': True,
        'item_id': normalized_item_id,
        'project_id': str(preview.get('project_id', '')).strip(),
        'provider': provider,
        'provider_base_url': provider_base_url,
        'model': model,
        'prompt_used': prompt_used,
        'response_text': response_text,
        'execution_allowed': execution_allowed,
        'executed': executed,
        'dry_run': bool(dry_run),
        'advisory_only': True,
        'repo_mutation_allowed': False,
        'external_mutation_allowed': False,
        'automatic_execution_allowed': False,
        'safety_status': 'allowed' if not blockers else 'blocked',
        'gate_status': str(safety_gate.get('gate_status', '')).strip() or ('operator_gate_confirmed' if confirm_operator_gate else 'preview_only' if dry_run else 'blocked'),
        'blocked_reason_category': str(safety_gate.get('blocked_reason_category', '')).strip() if blockers else '',
        'blocked_action': 'local_llm_execute' if blockers else '',
        'captured_at': captured_at,
        'next_safe_action': 'Review advisory local LLM output manually; do not apply changes automatically.' if executed else 'Resolve blockers before local LLM execution.',
        'warnings': sorted(set(warnings)),
        'blockers': sorted(set(blockers)),
        'safety_gate': safety_gate,
        'health_check': health_payload,
        'boundary_confirmations': [
            'Local LLM execution is explicit and operator-gated.',
            'Output is advisory only and is not applied to repo files, queue status, project state, GitHub, gh, Codex, agents, or workflows.',
        ],
    }

    if output is None:
        audit_result = append_execution_audit_entry(
            config,
            action_type='local_llm_execute' if executed or dry_run else 'blocked_attempt',
            item_id=normalized_item_id,
            engine=recommended_engine,
            model=model,
            agent_lane=str(routing_metadata.get('recommended_agent_lane', '')).strip(),
            operator_gate_confirmed=bool(confirm_operator_gate),
            dry_run=bool(dry_run),
            executed=executed,
            execution_allowed=execution_allowed,
            outcome='executed' if executed else ('dry_run' if dry_run and not blockers else 'blocked'),
            blockers=blockers,
            warnings=warnings,
            safety_status=payload['safety_status'],
            gate_status=payload['gate_status'],
            blocked_reason_category=payload['blocked_reason_category'],
            summary='Local LLM execution prototype completed as advisory output.' if executed else ('Local LLM execution dry run completed without provider call.' if dry_run and not blockers else 'Local LLM execution attempt blocked by local gates.'),
            source_function='execute_local_llm_for_queue_item',
        )
        payload['warnings'] = sorted(set(payload['warnings'] + audit_warning(audit_result)))
        return payload
    output_path = Path(output)
    payload['result_artifact_path'] = str(output_path)
    if output_path.exists() and not force:
        payload['ok'] = False
        payload['execution_allowed'] = False
        payload['warnings'] = sorted({*payload['warnings'], 'Output file already exists. Re-run with force=true to overwrite.'})
        audit_result = append_execution_audit_entry(
            config,
            action_type='blocked_attempt',
            item_id=normalized_item_id,
            engine=recommended_engine,
            model=model,
            agent_lane=str(routing_metadata.get('recommended_agent_lane', '')).strip(),
            operator_gate_confirmed=bool(confirm_operator_gate),
            dry_run=bool(dry_run),
            executed=executed,
            execution_allowed=False,
            outcome='blocked',
            blockers=['Output file already exists.'],
            warnings=payload['warnings'],
            artifact_path=output_path,
            safety_status='blocked',
            gate_status=payload['gate_status'],
            blocked_reason_category='gate_blocked',
            summary='Local LLM execution result artifact write blocked by non-overwrite gate.',
            source_function='execute_local_llm_for_queue_item',
        )
        payload['warnings'] = sorted(set(payload['warnings'] + audit_warning(audit_result)))
        return payload
    if not executed and not dry_run:
        audit_result = append_execution_audit_entry(
            config,
            action_type='blocked_attempt',
            item_id=normalized_item_id,
            engine=recommended_engine,
            model=model,
            agent_lane=str(routing_metadata.get('recommended_agent_lane', '')).strip(),
            operator_gate_confirmed=bool(confirm_operator_gate),
            dry_run=bool(dry_run),
            executed=False,
            execution_allowed=False,
            outcome='blocked',
            blockers=blockers,
            warnings=warnings,
            artifact_path=output_path,
            safety_status='blocked',
            gate_status=payload['gate_status'],
            blocked_reason_category=payload['blocked_reason_category'] or 'gate_blocked',
            summary='Local LLM execution attempt blocked by local gates.',
            source_function='execute_local_llm_for_queue_item',
        )
        payload['warnings'] = sorted(set(payload['warnings'] + audit_warning(audit_result)))
        return payload
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(_json_safe(payload), indent=2) + '\n', encoding='utf-8')
    except OSError as exc:
        payload['ok'] = False
        payload['execution_allowed'] = False
        payload['warnings'] = sorted({*payload['warnings'], f'Failed to write result artifact: {exc}'})
        audit_result = append_execution_audit_entry(
            config,
            action_type='blocked_attempt',
            item_id=normalized_item_id,
            engine=recommended_engine,
            model=model,
            agent_lane=str(routing_metadata.get('recommended_agent_lane', '')).strip(),
            operator_gate_confirmed=bool(confirm_operator_gate),
            dry_run=bool(dry_run),
            executed=executed,
            execution_allowed=False,
            outcome='blocked',
            blockers=[f'Failed to write result artifact: {exc}'],
            warnings=payload['warnings'],
            artifact_path=output_path,
            safety_status='blocked',
            gate_status=payload['gate_status'],
            blocked_reason_category='invalid_state',
            summary='Local LLM execution result artifact write failed.',
            source_function='execute_local_llm_for_queue_item',
        )
        payload['warnings'] = sorted(set(payload['warnings'] + audit_warning(audit_result)))
        return payload
    audit_result = append_execution_audit_entry(
        config,
        action_type='local_llm_execute',
        item_id=normalized_item_id,
        engine=recommended_engine,
        model=model,
        agent_lane=str(routing_metadata.get('recommended_agent_lane', '')).strip(),
        operator_gate_confirmed=bool(confirm_operator_gate),
        dry_run=bool(dry_run),
        executed=executed,
        execution_allowed=execution_allowed,
        outcome='executed' if executed else 'dry_run',
        blockers=blockers,
        warnings=warnings,
        artifact_path=output_path,
        safety_status=payload['safety_status'],
        gate_status=payload['gate_status'],
        blocked_reason_category=payload['blocked_reason_category'],
        summary='Local LLM execution audit recorded with local result artifact.' if executed else 'Local LLM dry run audit recorded with local result artifact.',
        source_function='execute_local_llm_for_queue_item',
    )
    artifact_result = register_ai_artifact(
        config,
        artifact_type='local_llm_execution_result',
        artifact_path=output_path,
        source_action='local_llm_execute',
        item_id=normalized_item_id,
        engine=recommended_engine,
        model=model,
        agent_lane=str(routing_metadata.get('recommended_agent_lane', '')).strip(),
        safety_status=payload['safety_status'],
        gate_status=payload['gate_status'],
        summary='Local LLM advisory execution result artifact generated.',
        warnings=warnings,
    )
    payload['artifact_registry'] = artifact_result.get('artifact', {})
    payload['warnings'] = sorted(set(payload['warnings'] + audit_warning(audit_result) + artifact_warning(artifact_result)))
    return payload


def read_local_routed_queue_views(
    config: AppConfig,
    *,
    queue_path: str | Path | None = None,
    project_id: str | None = None,
    status: str | None = None,
    recommended_agent_lane: str | None = None,
    recommended_engine: str | None = None,
    recommended_model: str | None = None,
    fallback_engine: str | None = None,
    risk_level: str | None = None,
    complexity_level: str | None = None,
    project_ai_mode: str | None = None,
    routing_policy_source: str | None = None,
    operator_override: str | bool | None = None,
    group_by: str | None = None,
    include_unrouted: bool = True,
) -> dict[str, Any]:
    resolved_queue_path = resolve_project_queue_path(config.repo_root, queue_path)
    loaded = _load_queue_required(resolved_queue_path)
    if not loaded.get('ok', False):
        if loaded.get('error') == 'project_queue_not_found':
            return {
                'command': 'read-local-routed-queue-views',
                'ok': True,
                'local_only': True,
                'generated_at': _now_iso(),
                'source_queue': str(resolved_queue_path),
                'filters': _routed_view_filters(
                    project_id=project_id,
                    status=status,
                    recommended_agent_lane=recommended_agent_lane,
                    recommended_engine=recommended_engine,
                    recommended_model=recommended_model,
                    fallback_engine=fallback_engine,
                    risk_level=risk_level,
                    complexity_level=complexity_level,
                    project_ai_mode=project_ai_mode,
                    routing_policy_source=routing_policy_source,
                    operator_override=operator_override,
                    include_unrouted=include_unrouted,
                ),
                'group_by': group_by or 'by_agent_lane',
                'total_items': 0,
                'routed_items_count': 0,
                'unrouted_items_count': 0,
                'groups': {},
                'items': [],
                'next_safe_action': 'Initialize or add local queue items before reviewing routed views.',
                'warnings': ['Local project queue not found. Returning empty routed views.'],
                'blockers': [],
                'execution_allowed': False,
                'boundary_confirmations': list(_ROUTED_QUEUE_VIEWS_BOUNDARY_CONFIRMATIONS),
            }
        return loaded

    queue = loaded['queue']
    raw_items = queue.get('work_items', [])
    items = [_item_view(item) for item in raw_items if isinstance(item, dict)]
    normalized_group_by = str(group_by or 'by_agent_lane').strip() or 'by_agent_lane'
    supported_groups = {
        'by_agent_lane': 'recommended_agent_lane',
        'by_engine': 'recommended_engine',
        'by_model': 'recommended_model',
        'by_project_policy': 'project_ai_mode',
        'by_risk_level': 'risk_level',
        'by_complexity_level': 'complexity_level',
        'by_status': 'status',
    }
    warnings: list[str] = []
    if normalized_group_by not in supported_groups:
        warnings.append(f"Unsupported group_by '{normalized_group_by}' supplied. Falling back to by_agent_lane.")
        normalized_group_by = 'by_agent_lane'

    filtered: list[dict[str, Any]] = []
    for item in items:
        metadata = default_queue_routing_metadata(item.get('routing_metadata', {}))
        routed = _is_routed_metadata(metadata)
        if not include_unrouted and not routed:
            continue
        if project_id and item.get('project_id') != project_id.strip():
            continue
        if status and item.get('status') != status.strip():
            continue
        if recommended_agent_lane and metadata.get('recommended_agent_lane') != recommended_agent_lane.strip():
            continue
        if recommended_engine and metadata.get('recommended_engine') != recommended_engine.strip():
            continue
        if recommended_model and metadata.get('recommended_model') != recommended_model.strip():
            continue
        if fallback_engine and metadata.get('fallback_engine') != fallback_engine.strip():
            continue
        if risk_level and metadata.get('risk_level') != risk_level.strip():
            continue
        if complexity_level and metadata.get('complexity_level') != complexity_level.strip():
            continue
        if project_ai_mode and metadata.get('project_ai_mode') != project_ai_mode.strip():
            continue
        if routing_policy_source and metadata.get('routing_policy_source') != routing_policy_source.strip():
            continue
        if operator_override is not None and not _operator_override_matches(metadata.get('operator_override'), operator_override):
            continue
        view = dict(item)
        view['routing_metadata'] = metadata
        view['routed'] = routed
        filtered.append(view)

    groups = _group_routed_items(filtered, supported_groups[normalized_group_by])
    routed_count = sum(1 for item in filtered if item.get('routed'))
    return {
        'command': 'read-local-routed-queue-views',
        'ok': True,
        'local_only': True,
        'generated_at': _now_iso(),
        'source_queue': str(resolved_queue_path),
        'filters': _routed_view_filters(
            project_id=project_id,
            status=status,
            recommended_agent_lane=recommended_agent_lane,
            recommended_engine=recommended_engine,
            recommended_model=recommended_model,
            fallback_engine=fallback_engine,
            risk_level=risk_level,
            complexity_level=complexity_level,
            project_ai_mode=project_ai_mode,
            routing_policy_source=routing_policy_source,
            operator_override=operator_override,
            include_unrouted=include_unrouted,
        ),
        'group_by': normalized_group_by,
        'total_items': len(filtered),
        'routed_items_count': routed_count,
        'unrouted_items_count': len(filtered) - routed_count,
        'groups': groups,
        'items': filtered,
        'next_safe_action': 'Review routed queue views as read-only filters over the canonical local queue.',
        'warnings': sorted(set(warnings)),
        'blockers': [],
        'execution_allowed': False,
        'boundary_confirmations': list(_ROUTED_QUEUE_VIEWS_BOUNDARY_CONFIRMATIONS),
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


def inspect_queue_consistency(
    config: AppConfig,
    *,
    queue_path: str | Path | None = None,
    project_id: str | None = None,
    repo_id: str | None = None,
    output_format: str = 'json',
) -> dict[str, Any]:
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
        filtered.append(item)

    inspected_items: list[dict[str, Any]] = []
    blocked_items: list[dict[str, Any]] = []
    dependency_block_count = 0
    completion_block_count = 0
    for item in filtered:
        status = str(item.get('status', '')).strip()
        dependency_summary = _dependency_readiness_summary(item, items, repo_root=config.repo_root)
        completion_lock = _completion_lock_summary(item)
        dependency_blocked = bool(dependency_summary['blockers']) and status != 'done'
        lock_blocked_reasons = sorted(
            {
                *[
                    str(reason).strip()
                    for reason in dependency_summary['blockers']
                    if str(reason).strip() and status != 'done'
                ],
                *[str(reason).strip() for reason in completion_lock['blocked_reasons'] if str(reason).strip()],
            }
        )
        completion_blocked = bool(completion_lock['blocked'])
        if dependency_blocked:
            dependency_block_count += 1
        if completion_blocked:
            completion_block_count += 1
        inspected = {
            'item_id': item.get('item_id', ''),
            'title': item.get('title', ''),
            'project_id': item.get('project_id', ''),
            'repo_id': item.get('repo_id', ''),
            'status': item.get('status', ''),
            'dependencies': _queue_dependency_ids(item),
            'blocked_by': item.get('blocked_by', []),
            'completion_requires': item.get('completion_requires', []),
            'evidence_required': item.get('evidence_required', []),
            'dependency_lock': {
                'blocked': dependency_blocked,
                'blocked_reasons': sorted(set(dependency_summary['blockers'])) if status != 'done' else [],
                'historical_findings': sorted(set(dependency_summary['blockers'])) if status == 'done' else [],
                **dependency_summary['payload'],
            },
            'completion_lock': completion_lock,
            'lock_blocked_reasons': lock_blocked_reasons,
        }
        inspected_items.append(inspected)
        if lock_blocked_reasons:
            blocked_items.append(
                {
                    'item_id': item.get('item_id', ''),
                    'status': item.get('status', ''),
                    'blocked_reasons': lock_blocked_reasons,
                }
            )

    payload = {
        'queue_path': str(resolved_queue_path),
        'schema_version': queue.get('schema_version'),
        'updated_at': queue.get('updated_at'),
        'project_id': project_id,
        'repo_id': repo_id,
        'item_count': len(filtered),
        'ok_to_start_or_complete_without_review': False,
        'dependency_lock_summary': {
            'blocked_item_count': dependency_block_count,
            'locked': dependency_block_count > 0,
        },
        'completion_lock_summary': {
            'blocked_item_count': completion_block_count,
            'locked': completion_block_count > 0,
        },
        'blocked_items': blocked_items,
        'items': inspected_items,
        'next_safe_action': (
            'Resolve dependency and evidence blockers before starting or completing locked queue items.'
            if blocked_items
            else 'Queue locks are consistent for the selected scope; continue explicit local lifecycle commands.'
        ),
        'boundary_confirmations': list(_QUEUE_CONSISTENCY_BOUNDARY_CONFIRMATIONS),
    }
    return _stdout_result(
        command='inspect-queue-consistency',
        payload=payload,
        output_format=output_format,
        markdown=_render_queue_consistency_markdown(payload),
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
    if not str(evidence_note or '').strip():
        warnings.append('review evidence is required to complete a local queue item.')
    if previous_status == 'done':
        warnings.append('Queue item is already done.')
    elif previous_status == 'cancelled':
        warnings.append('Queue item is cancelled.')
    elif previous_status not in _COMPLETABLE_QUEUE_STATUSES:
        warnings.append('Queue item must be in_progress before completion evidence can be recorded.')
    item_view = _item_view(raw_item)
    dependency_summary = _dependency_readiness_summary(item_view, [_item_view(item) for item in items if isinstance(item, dict)], repo_root=config.repo_root)
    warnings.extend(dependency_summary['blockers'])
    missing_required_evidence = _missing_required_completion_evidence(
        item_view,
        completion_commit=normalized_commit_hash,
        validation_summary=normalized_validation_summary,
        evidence_note=str(evidence_note or '').strip(),
        tests_run=tests_run or [],
        changed_files=changed_files or [],
        artifact_paths=artifact_paths or [],
    )
    warnings.extend(
        f'Required completion evidence is missing: {field_name}'
        for field_name in missing_required_evidence
    )

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
            'dependency_summary': dependency_summary['payload'],
            'missing_required_evidence': missing_required_evidence,
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
        'dependency_summary': dependency_summary['payload'],
        'missing_required_evidence': [],
        'boundary_confirmations': list(_QUEUE_ITEM_COMPLETE_BOUNDARY_CONFIRMATIONS),
        'item': completed_item,
    }


def capture_local_queue_completion_evidence(
    config: AppConfig,
    *,
    item_id: str,
    evidence_summary: str | None = None,
    validation_commands: list[str] | None = None,
    validation_results: list[str] | None = None,
    smoke_checks: list[str] | None = None,
    diff_check_result: str | None = None,
    files_changed: list[str] | None = None,
    commit_hash: str | None = None,
    push_result: str | None = None,
    review_evidence: list[str] | None = None,
    operator_notes: str | None = None,
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
            'command': 'capture-local-queue-completion-evidence',
            'ok': False,
            'local_only': True,
            'item_id': normalized_item_id,
            'status': '',
            'completion_evidence': {},
            'closeout_eligible': False,
            'next_safe_action': 'Inspect the local queue and choose a valid item_id before capturing evidence.',
            'warnings': [f'Queue item not found: {normalized_item_id}'],
            'boundary_confirmations': list(_QUEUE_ITEM_EVIDENCE_BOUNDARY_CONFIRMATIONS),
        }

    normalized_evidence = {
        'evidence_summary': str(evidence_summary or '').strip(),
        'validation_commands': _normalize_list(validation_commands or []),
        'validation_results': _normalize_list(validation_results or []),
        'smoke_checks': _normalize_list(smoke_checks or []),
        'diff_check_result': str(diff_check_result or '').strip(),
        'files_changed': _normalize_list(files_changed or []),
        'commit_hash': str(commit_hash or '').strip(),
        'push_result': str(push_result or '').strip(),
        'review_evidence': _normalize_list(review_evidence or []),
        'operator_notes': str(operator_notes or '').strip(),
    }
    if not _completion_evidence_has_meaningful_content(normalized_evidence):
        return {
            'command': 'capture-local-queue-completion-evidence',
            'ok': False,
            'local_only': True,
            'item_id': normalized_item_id,
            'status': str(raw_item.get('status', '')).strip(),
            'completion_evidence': {},
            'closeout_eligible': False,
            'next_safe_action': 'Add evidence summary, validation results, smoke checks, diff check, files changed, commit hash, push result, review evidence, or operator notes before retrying.',
            'warnings': ['At least one meaningful evidence field is required.'],
            'boundary_confirmations': list(_QUEUE_ITEM_EVIDENCE_BOUNDARY_CONFIRMATIONS),
        }

    now = _now_iso()
    previous_status = str(raw_item.get('status', '')).strip()
    evidence = {
        **normalized_evidence,
        'captured_at': now,
    }
    raw_item['completion_evidence'] = evidence
    raw_item['updated_at'] = now
    queue['work_items'] = items
    queue['updated_at'] = now
    _write_queue(resolved_queue_path, queue)

    captured_item = _item_view(raw_item)
    closeout_eligible = _completion_evidence_closeout_eligible(captured_item)
    return {
        'command': 'capture-local-queue-completion-evidence',
        'ok': True,
        'local_only': True,
        'item_id': normalized_item_id,
        'previous_status': previous_status,
        'status': str(captured_item.get('status', '')).strip(),
        'completion_evidence': evidence,
        'captured_at': now,
        'closeout_eligible': closeout_eligible,
        'next_safe_action': (
            'Review captured evidence and run the future closeout workflow when available.'
            if closeout_eligible
            else 'Continue local validation or start the item before closeout.'
        ),
        'warnings': [],
        'boundary_confirmations': list(_QUEUE_ITEM_EVIDENCE_BOUNDARY_CONFIRMATIONS),
        'item': captured_item,
    }


def close_local_queue_item(
    config: AppConfig,
    *,
    item_id: str,
    closeout_summary: str,
    closed_by: str = 'local_operator',
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
    normalized_summary = str(closeout_summary or '').strip()
    normalized_closed_by = str(closed_by or 'local_operator').strip() or 'local_operator'
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
            'command': 'close-local-queue-item',
            'ok': False,
            'local_only': True,
            'item_id': normalized_item_id,
            'previous_status': '',
            'status': '',
            'closeout_eligible': False,
            'closed_at': '',
            'next_safe_action': 'Inspect the local queue and choose a valid item_id before closeout.',
            'warnings': [f'Queue item not found: {normalized_item_id}'],
            'boundary_confirmations': list(_QUEUE_ITEM_CLOSEOUT_BOUNDARY_CONFIRMATIONS),
        }

    previous_status = str(raw_item.get('status', '')).strip()
    evidence = raw_item.get('completion_evidence', {})
    warnings: list[str] = []
    if previous_status != 'in_progress':
        warnings.append('Queue item must be in_progress before local closeout.')
    if not isinstance(evidence, dict) or not evidence:
        warnings.append('Completion evidence is required before local closeout.')
    elif not _completion_evidence_has_required_closeout_fields(evidence):
        warnings.append('Completion evidence must include evidence_summary, validation_results, diff_check_result, and review_evidence before closeout.')
    if not normalized_summary:
        warnings.append('closeout_summary is required for local closeout.')

    if warnings:
        return {
            'command': 'close-local-queue-item',
            'ok': False,
            'local_only': True,
            'item_id': normalized_item_id,
            'previous_status': previous_status,
            'status': previous_status,
            'closeout_eligible': False,
            'closed_at': str(raw_item.get('closed_at', '')).strip(),
            'next_safe_action': 'Capture required evidence, keep the item in progress, and retry closeout explicitly.',
            'warnings': sorted(set(warnings)),
            'boundary_confirmations': list(_QUEUE_ITEM_CLOSEOUT_BOUNDARY_CONFIRMATIONS),
        }

    now = _now_iso()
    closeout_entry = {
        'closed_at': now,
        'closed_by': normalized_closed_by,
        'closeout_summary': normalized_summary,
        'previous_status': previous_status,
        'status': 'done',
        'completion_evidence': evidence,
    }
    history = raw_item.get('closeout_history', [])
    if not isinstance(history, list):
        history = []
    history.append(closeout_entry)

    raw_item['previous_status'] = previous_status
    raw_item['status'] = 'done'
    raw_item['closed_at'] = now
    raw_item['closed_by'] = normalized_closed_by
    raw_item['closeout_summary'] = normalized_summary
    raw_item['closeout_history'] = history
    raw_item['updated_at'] = now
    queue['work_items'] = items
    queue['updated_at'] = now
    _write_queue(resolved_queue_path, queue)

    closed_item = _item_view(raw_item)
    return {
        'command': 'close-local-queue-item',
        'ok': True,
        'local_only': True,
        'item_id': normalized_item_id,
        'previous_status': previous_status,
        'status': str(closed_item.get('status', '')).strip(),
        'closed_at': now,
        'closed_by': normalized_closed_by,
        'closeout_summary': normalized_summary,
        'closeout_eligible': False,
        'next_safe_action': 'Inspect local queue and project reports for updated progress rollup.',
        'warnings': [],
        'boundary_confirmations': list(_QUEUE_ITEM_CLOSEOUT_BOUNDARY_CONFIRMATIONS),
        'item': closed_item,
    }


def read_local_project_progress_rollup(
    config: AppConfig,
    *,
    project_id: str,
    queue_path: str | Path | None = None,
    registry_path: str | Path | None = None,
) -> dict[str, Any]:
    normalized_project_id = str(project_id or '').strip()
    if not normalized_project_id:
        return _error(
            'invalid_project_progress_rollup_payload',
            {
                'message': 'project_id is required.',
                'required_fields': ['project_id'],
            },
        )

    resolved_queue_path = resolve_project_queue_path(config.repo_root, queue_path)
    resolved_registry_path = resolve_managed_project_registry_path(config.repo_root, registry_path)
    registry_projects, registry_warnings = _load_registry_projects_for_rollup(resolved_registry_path)
    registry_available = resolved_registry_path.exists() and not registry_warnings
    if registry_available and normalized_project_id not in {
        str(project.get('project_id', '')).strip()
        for project in registry_projects
        if isinstance(project, dict)
    }:
        return _error(
            'managed_project_not_found',
            {
                'message': 'Project id was not found in managed project registry.',
                'project_id': normalized_project_id,
                'registry_path': str(resolved_registry_path),
            },
        )

    project = next(
        (
            candidate
            for candidate in registry_projects
            if isinstance(candidate, dict)
            and str(candidate.get('project_id', '')).strip() == normalized_project_id
        ),
        {},
    )
    queue_items, queue_updated_at, queue_warnings = _load_queue_items_for_rollup(resolved_queue_path)
    project_items = [
        item
        for item in queue_items
        if str(item.get('project_id', '')).strip() == normalized_project_id
    ]
    item_views = [_item_view(item) for item in project_items]

    active_payload = inspect_active_project(config)
    active_project_id = str(active_payload.get('active_project_id', '')).strip()
    items_by_status = {status: 0 for status in QUEUE_STATUSES}
    items_by_status.update(_count_items_by(item_views, 'status'))
    items_by_type = _count_items_by(item_views, 'item_type')
    items_by_lane = _count_items_by(item_views, 'assigned_agent')

    ready_items = [_rollup_item_summary(item) for item in item_views if item.get('status') == 'ready']
    blocked_items = [_rollup_item_summary(item) for item in item_views if item.get('status') == 'blocked']
    in_progress_items = [_rollup_item_summary(item) for item in item_views if item.get('status') == 'in_progress']
    evidence_items = [
        _rollup_item_summary(item)
        for item in item_views
        if isinstance(item.get('completion_evidence'), dict) and bool(item.get('completion_evidence'))
    ]
    closeout_eligible_items = [
        _rollup_item_summary(item)
        for item in item_views
        if _completion_evidence_closeout_eligible(item)
    ]
    closed_completed_items = [
        _rollup_item_summary(item)
        for item in item_views
        if item.get('status') == 'done'
    ]
    blockers = [
        f"Queue item {item.get('item_id')} is blocked: {item.get('title') or '-'}"
        for item in blocked_items
    ]
    latest_activity_timestamp = _latest_rollup_activity(project, project_items, queue_updated_at)
    warnings = sorted(
        {
            *registry_warnings,
            *queue_warnings,
            *[
                str(warning).strip()
                for warning in active_payload.get('warnings', [])
                if str(warning).strip()
                and normalized_project_id == active_project_id
            ],
        }
    )

    return {
        'command': 'read-local-project-progress-rollup',
        'ok': True,
        'local_only': True,
        'read_only': True,
        'project_id': normalized_project_id,
        'project_name': str(project.get('name', '')).strip(),
        'active_project': normalized_project_id == active_project_id,
        'queue_path': str(resolved_queue_path),
        'registry_path': str(resolved_registry_path),
        'total_queue_items': len(item_views),
        'items_by_status': dict(sorted(items_by_status.items())),
        'items_by_type': items_by_type,
        'items_by_lane': items_by_lane,
        'ready_item_count': len(ready_items),
        'ready_items': ready_items,
        'blocked_item_count': len(blocked_items),
        'blocked_items': blocked_items,
        'in_progress_item_count': len(in_progress_items),
        'in_progress_items': in_progress_items,
        'items_with_evidence_captured_count': len(evidence_items),
        'items_with_evidence_captured': evidence_items,
        'items_eligible_for_closeout_count': len(closeout_eligible_items),
        'items_eligible_for_closeout': closeout_eligible_items,
        'closed_completed_item_count': len(closed_completed_items),
        'closed_completed_items': closed_completed_items,
        'latest_activity_timestamp': latest_activity_timestamp,
        'next_safe_action': _project_progress_next_safe_action(
            total_items=len(item_views),
            ready_count=len(ready_items),
            blocked_count=len(blocked_items),
            in_progress_count=len(in_progress_items),
            closeout_eligible_count=len(closeout_eligible_items),
            closed_completed_count=len(closed_completed_items),
        ),
        'blockers': blockers,
        'warnings': warnings,
        'future_routing_metadata': {
            'implemented': False,
            'status': 'future_not_implemented',
            'note': 'Agent/LLM routing metadata remains future work and is not used by this read-only rollup.',
        },
        'boundary_confirmations': list(_PROJECT_PROGRESS_ROLLUP_BOUNDARY_CONFIRMATIONS),
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


def generate_codex_high_value_lane_prompt(
    config: AppConfig,
    *,
    item_id: str,
    include_context: bool = True,
    include_validation_expectations: bool = True,
    include_operating_rules: bool = True,
    output: str | Path | None = None,
    force: bool = False,
    operator_override: bool = False,
    queue_path: str | Path | None = None,
    registry_path: str | Path | None = None,
) -> dict[str, Any]:
    normalized_item_id = str(item_id or '').strip()
    resolved_queue_path = resolve_project_queue_path(config.repo_root, queue_path)
    loaded = _load_queue_required(resolved_queue_path)
    if not loaded.get('ok', False):
        return loaded

    queue = loaded['queue']
    items = [_item_view(item) for item in queue.get('work_items', []) if isinstance(item, dict)]
    item = next((candidate for candidate in items if candidate.get('item_id') == normalized_item_id), None)
    if item is None:
        return _error(
            'queue_item_not_found',
            {
                'item_id': normalized_item_id,
                'message': 'Queue item was not found for Codex high-value lane prompt generation.',
            },
        )

    routing_metadata = default_queue_routing_metadata(item.get('routing_metadata', {}))
    project_id = str(item.get('project_id', '')).strip()
    project_ai_settings = _read_project_ai_settings_for_preview(config.repo_root, project_id)
    project_ai_mode = str(
        routing_metadata.get('project_ai_mode') or project_ai_settings.get('project_ai_mode', '')
    ).strip()
    if project_ai_mode:
        routing_metadata['project_ai_mode'] = project_ai_mode

    eligibility = _evaluate_codex_high_value_lane_eligibility(
        item=item,
        routing_metadata=routing_metadata,
        operator_override=operator_override,
    )
    eligible = bool(eligibility['eligible'])
    recommended_engine = str(routing_metadata.get('recommended_engine', '')).strip()
    recommended_model = str(routing_metadata.get('recommended_model', '')).strip()
    if eligible and not recommended_engine:
        recommended_engine = 'codex_cli'

    warnings: list[str] = []
    blockers: list[str] = []
    if not eligible:
        blockers.append(
            'Queue item does not meet Codex high-value lane eligibility; use local routing, local LLM preview, or set operator_override for manual Codex review.'
        )
    if recommended_engine and recommended_engine != 'codex_cli' and not operator_override:
        warnings.append(
            f'Queue item is currently routed to {recommended_engine}; Codex prompt generation remains advisory only.'
        )
    safety_gate = evaluate_ai_action_safety_gate(
        config,
        action_type='codex_high_value_prompt',
        item_id=normalized_item_id,
        project_id=project_id,
        engine=recommended_engine,
        model=recommended_model,
        agent_lane=str(routing_metadata.get('recommended_agent_lane', '')).strip(),
        risk_level=str(routing_metadata.get('risk_level', 'unknown')).strip() or 'unknown',
        complexity_level=str(routing_metadata.get('complexity_level', 'unknown')).strip() or 'unknown',
        project_ai_mode=project_ai_mode,
        operator_override=operator_override,
        confirm_operator_gate=False,
        dry_run=True,
        queue_path=queue_path,
    )
    blockers.extend([str(blocker) for blocker in safety_gate.get('blockers', [])])
    warnings.extend([str(warning) for warning in safety_gate.get('warnings', [])])

    readiness = _evaluate_local_queue_item_readiness(
        repo_root=config.repo_root,
        item=item,
        items=items,
        registry_path=registry_path,
    )
    prompt_preview = ''
    if eligible:
        prompt_preview = _build_codex_high_value_lane_prompt_preview(
            repo_root=config.repo_root,
            item=item,
            readiness=readiness,
            routing_metadata=routing_metadata,
            codex_lane_reason=str(eligibility['reason']),
            include_context=include_context,
            include_validation_expectations=include_validation_expectations,
            include_operating_rules=include_operating_rules,
        )

    payload: dict[str, Any] = {
        'command': 'generate-codex-high-value-lane-prompt',
        'ok': eligible,
        'local_only': True,
        'item_id': normalized_item_id,
        'eligible_for_codex_lane': eligible,
        'recommended_engine': recommended_engine,
        'recommended_model': recommended_model,
        'codex_lane_reason': str(eligibility['reason']),
        'execution_allowed': False,
        'executed': False,
        'advisory_only': True,
        'repo_mutation_allowed': False,
        'external_mutation_allowed': False,
        'automatic_execution_allowed': False,
        'safety_status': 'allowed' if eligible else 'blocked',
        'gate_status': str(safety_gate.get('gate_status', 'preview_only')).strip() or 'preview_only',
        'blocked_reason_category': str(safety_gate.get('blocked_reason_category', '')).strip() if not eligible else '',
        'blocked_action': 'codex_high_value_prompt' if not eligible else '',
        'prompt_preview': prompt_preview,
        'output_path': '',
        'next_safe_action': (
            'Copy the prompt manually into Codex only if the operator chooses to start a Codex session.'
            if eligible
            else 'Keep this item in the local lane or explicitly request Codex with operator_override.'
        ),
        'warnings': sorted(set(warnings)),
        'blockers': sorted(set(blockers)),
        'safety_gate': safety_gate,
        'eligibility_reasons': eligibility['reasons'],
        'routing_metadata': routing_metadata,
        'boundary_confirmations': list(_CODEX_HIGH_VALUE_LANE_BOUNDARY_CONFIRMATIONS),
    }

    if output is None:
        audit_result = append_execution_audit_entry(
            config,
            action_type='codex_high_value_prompt' if eligible else 'blocked_attempt',
            project_id=str(item.get('project_id', '')).strip(),
            item_id=normalized_item_id,
            engine=recommended_engine,
            model=recommended_model,
            agent_lane=str(routing_metadata.get('recommended_agent_lane', '')).strip(),
            operator_gate_confirmed=bool(operator_override),
            dry_run=True,
            executed=False,
            execution_allowed=False,
            outcome='prompt_generated' if eligible else 'blocked',
            blockers=blockers,
            warnings=warnings,
            safety_status=payload['safety_status'],
            gate_status=payload['gate_status'],
            blocked_reason_category=payload['blocked_reason_category'],
            summary='Codex high-value prompt generated for manual operator copy/paste.' if eligible else 'Codex high-value prompt generation blocked by eligibility gates.',
            source_function='generate_codex_high_value_lane_prompt',
        )
        payload['warnings'] = sorted(set(payload['warnings'] + audit_warning(audit_result)))
        return payload

    output_path = Path(output)
    payload['output_path'] = str(output_path)
    if output_path.exists() and not force:
        payload['ok'] = False
        payload['warnings'] = sorted({*payload['warnings'], 'Output file already exists. Re-run with force=true to overwrite.'})
        audit_result = append_execution_audit_entry(
            config,
            action_type='blocked_attempt',
            project_id=str(item.get('project_id', '')).strip(),
            item_id=normalized_item_id,
            engine=recommended_engine,
            model=recommended_model,
            agent_lane=str(routing_metadata.get('recommended_agent_lane', '')).strip(),
            operator_gate_confirmed=bool(operator_override),
            dry_run=True,
            executed=False,
            execution_allowed=False,
            outcome='blocked',
            blockers=['Output file already exists.'],
            warnings=payload['warnings'],
            artifact_path=output_path,
            safety_status='blocked',
            gate_status=payload['gate_status'],
            blocked_reason_category='gate_blocked',
            summary='Codex high-value prompt artifact write blocked by non-overwrite gate.',
            source_function='generate_codex_high_value_lane_prompt',
        )
        payload['warnings'] = sorted(set(payload['warnings'] + audit_warning(audit_result)))
        return payload
    if not eligible:
        audit_result = append_execution_audit_entry(
            config,
            action_type='blocked_attempt',
            project_id=str(item.get('project_id', '')).strip(),
            item_id=normalized_item_id,
            engine=recommended_engine,
            model=recommended_model,
            agent_lane=str(routing_metadata.get('recommended_agent_lane', '')).strip(),
            operator_gate_confirmed=bool(operator_override),
            dry_run=True,
            executed=False,
            execution_allowed=False,
            outcome='blocked',
            blockers=blockers,
            warnings=warnings,
            artifact_path=output_path,
            safety_status='blocked',
            gate_status=payload['gate_status'],
            blocked_reason_category=payload['blocked_reason_category'] or 'gate_blocked',
            summary='Codex high-value prompt generation blocked by eligibility gates.',
            source_function='generate_codex_high_value_lane_prompt',
        )
        payload['warnings'] = sorted(set(payload['warnings'] + audit_warning(audit_result)))
        return payload
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(prompt_preview + '\n', encoding='utf-8')
    except OSError as exc:
        payload['ok'] = False
        payload['warnings'] = sorted({*payload['warnings'], f'Failed to write output file: {exc}'})
        audit_result = append_execution_audit_entry(
            config,
            action_type='blocked_attempt',
            project_id=str(item.get('project_id', '')).strip(),
            item_id=normalized_item_id,
            engine=recommended_engine,
            model=recommended_model,
            agent_lane=str(routing_metadata.get('recommended_agent_lane', '')).strip(),
            operator_gate_confirmed=bool(operator_override),
            dry_run=True,
            executed=False,
            execution_allowed=False,
            outcome='blocked',
            blockers=[f'Failed to write output file: {exc}'],
            warnings=payload['warnings'],
            artifact_path=output_path,
            safety_status='blocked',
            gate_status=payload['gate_status'],
            blocked_reason_category='invalid_state',
            summary='Codex high-value prompt artifact write failed.',
            source_function='generate_codex_high_value_lane_prompt',
        )
        payload['warnings'] = sorted(set(payload['warnings'] + audit_warning(audit_result)))
        return payload
    audit_result = append_execution_audit_entry(
        config,
        action_type='codex_high_value_prompt',
        project_id=str(item.get('project_id', '')).strip(),
        item_id=normalized_item_id,
        engine=recommended_engine,
        model=recommended_model,
        agent_lane=str(routing_metadata.get('recommended_agent_lane', '')).strip(),
        operator_gate_confirmed=bool(operator_override),
        dry_run=True,
        executed=False,
        execution_allowed=False,
        outcome='prompt_generated',
        blockers=[],
        warnings=warnings,
        artifact_path=output_path,
        safety_status='allowed',
        gate_status=payload['gate_status'],
        blocked_reason_category='',
        summary='Codex high-value prompt generated and written to a local artifact.',
        source_function='generate_codex_high_value_lane_prompt',
    )
    artifact_result = register_ai_artifact(
        config,
        artifact_type='codex_high_value_prompt',
        artifact_path=output_path,
        source_action='codex_high_value_prompt',
        project_id=str(item.get('project_id', '')).strip(),
        item_id=normalized_item_id,
        engine=recommended_engine,
        model=recommended_model,
        agent_lane=str(routing_metadata.get('recommended_agent_lane', '')).strip(),
        safety_status='allowed',
        gate_status=payload['gate_status'],
        summary='Codex high-value prompt artifact generated for manual operator copy/paste.',
        warnings=warnings,
    )
    payload['artifact_registry'] = artifact_result.get('artifact', {})
    payload['warnings'] = sorted(set(payload['warnings'] + audit_warning(audit_result) + artifact_warning(artifact_result)))
    return payload


def generate_local_queue_prompt_pack(
    config: AppConfig,
    *,
    item_ids: list[str] | None = None,
    statuses: list[str] | None = None,
    queue_path: str | Path | None = None,
    registry_path: str | Path | None = None,
    output: str | Path | None = None,
    force: bool = False,
    include_routing: bool = True,
    group_by_routing: bool = False,
    routing_group_by: str | None = None,
    include_unrouted: bool = True,
    recommend_missing_routing: bool = False,
) -> dict[str, Any]:
    resolved_queue_path = resolve_project_queue_path(config.repo_root, queue_path)
    loaded = _load_queue_required(resolved_queue_path)
    if not loaded.get('ok', False):
        return loaded
    queue = loaded['queue']
    items = [_item_view(item) for item in queue.get('work_items', []) if isinstance(item, dict)]
    by_id = {str(item.get('item_id', '')).strip(): item for item in items if str(item.get('item_id', '')).strip()}

    normalized_item_ids = _normalize_list(item_ids or [])
    supported_statuses = set(QUEUE_STATUSES)
    normalized_statuses = _normalize_list(statuses or ['ready', 'in_progress', 'proposed'])
    invalid_statuses = [value for value in normalized_statuses if value not in supported_statuses]
    if invalid_statuses:
        return _error(
            'invalid_queue_status_filter',
            {
                'message': 'One or more status filters are invalid.',
                'invalid_statuses': invalid_statuses,
                'supported_statuses': list(QUEUE_STATUSES),
            },
        )

    warnings: list[str] = []
    selected: list[dict[str, Any]] = []
    if normalized_item_ids:
        missing_ids = [value for value in normalized_item_ids if value not in by_id]
        if missing_ids:
            warnings.append(f"Ignored missing queue item ids: {', '.join(missing_ids)}")
        for value in normalized_item_ids:
            if value in by_id:
                selected.append(by_id[value])
    else:
        selected = [
            item for item in items
            if str(item.get('status', '')).strip() in set(normalized_statuses)
            and _prompt_recommended(item)
        ]

    readiness_by_id: dict[str, dict[str, Any]] = {}
    for item in selected:
        item_id = str(item.get('item_id', '')).strip()
        readiness_by_id[item_id] = _evaluate_local_queue_item_readiness(
            repo_root=config.repo_root,
            item=item,
            items=items,
            registry_path=registry_path,
        )

    routing_group_fields = {
        'by_agent_lane': 'recommended_agent_lane',
        'by_engine': 'recommended_engine',
        'by_model': 'recommended_model',
        'by_risk_level': 'risk_level',
        'by_complexity_level': 'complexity_level',
        'by_status': 'status',
    }
    normalized_routing_group_by = str(routing_group_by or 'by_agent_lane').strip() or 'by_agent_lane'
    if normalized_routing_group_by not in routing_group_fields:
        warnings.append(f"Unsupported routing_group_by '{normalized_routing_group_by}' supplied. Falling back to by_agent_lane.")
        normalized_routing_group_by = 'by_agent_lane'
    if recommend_missing_routing:
        warnings.append('recommend_missing_routing is preview-only and not applied by prompt-pack generation.')

    groups: dict[str, list[dict[str, Any]]] = {}
    for item in selected:
        routing_metadata = default_queue_routing_metadata(item.get('routing_metadata', {}))
        routed = _is_routed_metadata(routing_metadata)
        if include_routing and group_by_routing:
            if not include_unrouted and not routed:
                continue
            group_field = routing_group_fields[normalized_routing_group_by]
            if group_field == 'status':
                group_value = str(item.get('status', '')).strip()
            else:
                group_value = str(routing_metadata.get(group_field, '')).strip()
            if group_value == 'unknown' and group_field in {'risk_level', 'complexity_level'} and not routed:
                group_value = ''
            lane = f'{normalized_routing_group_by}: {group_value or "unrouted"}'
        else:
            project_id = str(item.get('project_id', '')).strip() or 'unknown-project'
            priority = str(item.get('priority', '')).strip() or 'normal'
            item_type = str(item.get('item_type', '')).strip() or 'task'
            lane = f'{project_id} | {priority} | {item_type}'
        groups.setdefault(lane, []).append(item)

    group_keys = sorted(groups.keys())
    sequence = 1
    pack_lines: list[str] = [
        'Agent Prompt Pack (Local-Only)',
        '',
        'This output is a local copy/paste prompt pack only.',
        'It does not execute Codex, Codex CLI, agents, local LLMs, models, prompts, GitHub actions, workflows, or network calls.',
        'Routing recommendations are metadata only and execution_allowed is always false.',
        'Operator must manually copy prompts into external tools if desired.',
        'Local LLM output must never automatically mutate repository files.',
        '',
    ]
    item_summaries: list[dict[str, Any]] = []
    for lane in group_keys:
        pack_lines.extend([f'=== Lane: {lane} ===', ''])
        for item in groups[lane]:
            item_id = str(item.get('item_id', '')).strip()
            readiness = readiness_by_id.get(item_id, {})
            parsed_notes = _parse_queue_item_notes(str(item.get('notes', '')).strip())
            routing_metadata = default_queue_routing_metadata(item.get('routing_metadata', {}))
            routed = _is_routed_metadata(routing_metadata)
            routing_guidance = _prompt_pack_routing_guidance(routing_metadata, routed)
            lane_guidance = _prompt_pack_lane_guidance(routing_metadata, routed)
            task_size_guidance = _prompt_pack_task_size_guidance(item, routing_metadata, routed)
            model_recommendation = _prompt_pack_model_recommendation(routing_metadata, routed)
            dependencies = _normalize_list(item.get('blocked_by', []))
            prompt_header_lines = [
                f'--- Prompt {sequence}: {item_id} ---',
                f'Sequence: {sequence}',
                f'Dependencies: {", ".join(dependencies) if dependencies else "-"}',
                f'Queue Item ID: {item_id}',
                f'Title: {str(item.get("title", "")).strip()}',
                f'Project ID: {str(item.get("project_id", "")).strip() or "-"}',
                f'Repo ID: {str(item.get("repo_id", "")).strip() or "-"}',
                f'Status: {str(item.get("status", "")).strip() or "-"}',
                f'Priority: {str(item.get("priority", "")).strip() or "-"}',
                f'Type: {str(item.get("item_type", "")).strip() or "-"}',
                f'Source: {str(item.get("source", "")).strip() or "-"}',
                f'Readiness: {str(readiness.get("readiness_status", "")).strip() or "unknown"}',
                f'Next safe action: {str(readiness.get("recommended_next_action", "")).strip() or "Inspect readiness locally."}',
                '',
            ]
            if include_routing:
                prompt_header_lines.extend(
                    [
                        'Routing metadata:',
                        f'- recommended_agent_lane: {routing_metadata.get("recommended_agent_lane") or "unrouted"}',
                        f'- recommended_engine: {routing_metadata.get("recommended_engine") or "unrouted"}',
                        f'- recommended_model: {routing_metadata.get("recommended_model") or "-"}',
                        f'- fallback_engine: {routing_metadata.get("fallback_engine") or "-"}',
                        f'- fallback_model: {routing_metadata.get("fallback_model") or "-"}',
                        f'- routing_policy_source: {routing_metadata.get("routing_policy_source") or "manual_required"}',
                        f'- routing_reason: {routing_metadata.get("routing_reason") or routing_guidance}',
                        f'- risk_level: {routing_metadata.get("risk_level") or "unknown"}',
                        f'- complexity_level: {routing_metadata.get("complexity_level") or "unknown"}',
                        f'- escalation_reason: {routing_metadata.get("escalation_reason") or "-"}',
                        f'- project_ai_mode: {routing_metadata.get("project_ai_mode") or "-"}',
                        f'- operator_override: {routing_metadata.get("operator_override")}',
                        '- execution_allowed: false',
                        f'- guidance: {routing_guidance}',
                        f'- lane_guidance: {lane_guidance}',
                        f'- task_size: {task_size_guidance}',
                        f'- model_engine_recommendation: {model_recommendation}',
                        '- recommendation_is_advisory_only: true',
                        '',
                    ]
                )
            else:
                prompt_header_lines.extend(
                    [
                        f'Lane-specific guidance: {lane_guidance}',
                        f'Task sizing guidance: {task_size_guidance}',
                        f'Model/engine recommendation: {model_recommendation}',
                        '',
                    ]
                )
            pack_lines.extend(
                [
                    *prompt_header_lines,
                    'Task summary/details:',
                    str(item.get('description', '')).strip() or 'No description supplied.',
                    '',
                    'Acceptance criteria:',
                ]
            )
            acceptance = parsed_notes.get('acceptance_criteria', []) if isinstance(parsed_notes, dict) else []
            if isinstance(acceptance, list) and acceptance:
                pack_lines.extend([f'- {entry}' for entry in acceptance if str(entry).strip()])
            else:
                pack_lines.append('- No explicit acceptance criteria recorded.')
            extra_notes = str(parsed_notes.get('notes', '')).strip() if isinstance(parsed_notes, dict) else ''
            pack_lines.extend(
                [
                    '',
                    'Validation/smoke expectations:',
                    '- Run targeted local pytest for touched areas.',
                    '- Run: python -m aresforge inspect-local-queue-agent-summary',
                    '- Run: python -m aresforge inspect-local-project-report',
                    '- Run: git diff --check',
                    '- Run: git status --short before any requested commit or push.',
                    '- Do not claim validation, smoke checks, commits, or pushes unless they actually happened.',
                    '',
                    'Operating rules:',
                    '- Local-first only.',
                    '- Prompt pack is an artifact/preview only.',
                    '- No automatic execution.',
                    '- No GitHub API, no gh, no GitHub mutation.',
                    '- No Codex execution, no Codex CLI execution unless a future approved milestone explicitly permits it, and no agent execution from this prompt.',
                    '- No prompt execution.',
                    '- No local LLM execution and no routing execution.',
                    '- No repo mutation from local LLM output.',
                    '- No external dependencies/services.',
                    '- Do not auto-start or auto-complete queue items.',
                    '- Operator must review, apply, validate, commit, and push manually when explicitly requested.',
                    '',
                    'Final response format:',
                    '- Files changed',
                    '- What was changed',
                    '- Tests updated and why',
                    '- Validation results',
                    '- Smoke check results',
                    '- Diff check result',
                    '- Commit hash',
                    '- Push result',
                ]
            )
            if extra_notes:
                pack_lines.extend(['', 'Additional notes:', extra_notes])
            pack_lines.extend(['', '--- End Prompt ---', ''])
            item_summaries.append(
                {
                    'sequence': sequence,
                    'item_id': item_id,
                    'title': str(item.get('title', '')).strip(),
                    'status': str(item.get('status', '')).strip(),
                    'priority': str(item.get('priority', '')).strip(),
                    'item_type': str(item.get('item_type', '')).strip(),
                    'project_id': str(item.get('project_id', '')).strip(),
                    'source': str(item.get('source', '')).strip(),
                    'readiness_status': str(readiness.get('readiness_status', '')).strip(),
                    'next_safe_action': str(readiness.get('recommended_next_action', '')).strip(),
                    'lane': lane,
                    'dependencies': dependencies,
                    'routing_metadata': routing_metadata if include_routing else {},
                    'routing_guidance': routing_guidance if include_routing else '',
                    'lane_guidance': lane_guidance,
                    'task_size_guidance': task_size_guidance,
                    'model_engine_recommendation': model_recommendation,
                    'execution_allowed': False,
                }
            )
            sequence += 1

    if not item_summaries:
        warnings.append('No eligible queue items found for prompt pack generation.')
    prompt_pack_text = '\n'.join(pack_lines).rstrip()
    payload: dict[str, Any] = {
        'command': 'generate-local-queue-prompt-pack',
        'ok': True,
        'local_only': True,
        'item_count': len(item_summaries),
        'selected_item_ids': normalized_item_ids,
        'status_filter': normalized_statuses,
        'groups': group_keys,
        'include_routing': bool(include_routing),
        'group_by_routing': bool(group_by_routing),
        'routing_group_by': normalized_routing_group_by if group_by_routing else '',
        'include_unrouted': bool(include_unrouted),
        'recommend_missing_routing': bool(recommend_missing_routing),
        'execution_allowed': False,
        'items': item_summaries,
        'prompt_pack': prompt_pack_text,
        'next_safe_action': 'Copy prompt text manually into your operator workflow. No automatic execution occurs.',
        'warnings': sorted(set(warnings)),
    }

    if output is None:
        audit_result = append_execution_audit_entry(
            config,
            action_type='prompt_pack_generate',
            engine='prompt_pack',
            dry_run=True,
            executed=False,
            execution_allowed=False,
            outcome='generated' if item_summaries else 'empty',
            blockers=[],
            warnings=warnings,
            summary=f'Local prompt pack generated for {len(item_summaries)} queue item(s).',
            source_function='generate_local_queue_prompt_pack',
        )
        payload['warnings'] = sorted(set(payload['warnings'] + audit_warning(audit_result)))
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
        audit_result = append_execution_audit_entry(
            config,
            action_type='blocked_attempt',
            engine='prompt_pack',
            dry_run=True,
            executed=False,
            execution_allowed=False,
            outcome='blocked',
            blockers=['Output file already exists.'],
            warnings=payload['warnings'],
            artifact_path=output_path,
            summary='Local prompt pack artifact write blocked by non-overwrite gate.',
            source_function='generate_local_queue_prompt_pack',
        )
        payload['warnings'] = sorted(set(payload['warnings'] + audit_warning(audit_result)))
        return payload
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(prompt_pack_text + '\n', encoding='utf-8')
    except OSError as exc:
        payload['ok'] = False
        payload['output_path'] = str(output_path)
        payload['warnings'] = sorted(
            {
                *payload['warnings'],
                f'Failed to write output file: {exc}',
            }
        )
        audit_result = append_execution_audit_entry(
            config,
            action_type='blocked_attempt',
            engine='prompt_pack',
            dry_run=True,
            executed=False,
            execution_allowed=False,
            outcome='blocked',
            blockers=[f'Failed to write output file: {exc}'],
            warnings=payload['warnings'],
            artifact_path=output_path,
            summary='Local prompt pack artifact write failed.',
            source_function='generate_local_queue_prompt_pack',
        )
        payload['warnings'] = sorted(set(payload['warnings'] + audit_warning(audit_result)))
        return payload

    payload['output_path'] = str(output_path)
    artifact_result = register_ai_artifact(
        config,
        artifact_type='prompt_pack',
        artifact_path=output_path,
        source_action='prompt_pack_generate',
        engine='prompt_pack',
        summary=f'Local prompt pack artifact generated for {len(item_summaries)} queue item(s).',
        warnings=warnings,
    )
    payload['artifact_registry'] = artifact_result.get('artifact', {})
    audit_result = append_execution_audit_entry(
        config,
        action_type='prompt_pack_generate',
        engine='prompt_pack',
        dry_run=True,
        executed=False,
        execution_allowed=False,
        outcome='generated' if item_summaries else 'empty',
        blockers=[],
        warnings=warnings,
        artifact_path=output_path,
        summary=f'Local prompt pack generated for {len(item_summaries)} queue item(s) and written to artifact.',
        source_function='generate_local_queue_prompt_pack',
    )
    payload['warnings'] = sorted(set(payload['warnings'] + audit_warning(audit_result) + artifact_warning(artifact_result)))
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
    dependency_summary = _dependency_readiness_summary(item, items, repo_root=repo_root)

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


def _completion_evidence_has_meaningful_content(evidence: dict[str, Any]) -> bool:
    for field_name in (
        'evidence_summary',
        'diff_check_result',
        'commit_hash',
        'push_result',
        'operator_notes',
    ):
        if str(evidence.get(field_name, '')).strip():
            return True
    for field_name in (
        'validation_commands',
        'validation_results',
        'smoke_checks',
        'files_changed',
        'review_evidence',
    ):
        values = evidence.get(field_name, [])
        if isinstance(values, list) and any(str(value).strip() for value in values):
            return True
    return False


def _completion_evidence_closeout_eligible(item: dict[str, Any]) -> bool:
    status = str(item.get('status', '')).strip()
    evidence = item.get('completion_evidence', {})
    if not isinstance(evidence, dict):
        return False
    return status == 'in_progress' and _completion_evidence_has_required_closeout_fields(evidence)


def _completion_evidence_has_required_closeout_fields(evidence: dict[str, Any]) -> bool:
    evidence_summary = str(evidence.get('evidence_summary', '')).strip()
    validation_results = evidence.get('validation_results', [])
    diff_check_result = str(evidence.get('diff_check_result', '')).strip()
    review_evidence = evidence.get('review_evidence', [])
    return bool(
        evidence_summary
        and isinstance(validation_results, list)
        and any(str(value).strip() for value in validation_results)
        and diff_check_result
        and isinstance(review_evidence, list)
        and any(str(value).strip() for value in review_evidence)
    )


def _explicit_completion_requirements(item: dict[str, Any]) -> list[str]:
    requirements: list[str] = []
    for field_name in ('completion_requires', 'evidence_required'):
        values = item.get(field_name, [])
        if isinstance(values, list):
            requirements.extend(str(value).strip() for value in values)
    return _normalize_list(requirements)


def _missing_required_completion_evidence(
    item: dict[str, Any],
    *,
    completion_commit: str = '',
    validation_summary: str = '',
    evidence_note: str = '',
    tests_run: list[str] | None = None,
    changed_files: list[str] | None = None,
    artifact_paths: list[str] | None = None,
) -> list[str]:
    requirements = _explicit_completion_requirements(item)
    if not requirements:
        return []

    evidence = item.get('completion_evidence', {})
    if not isinstance(evidence, dict):
        evidence = {}
    values = {
        'commit_hash': completion_commit or str(evidence.get('commit_hash', '')).strip() or str(item.get('completion_commit', '')).strip(),
        'completion_commit': completion_commit or str(item.get('completion_commit', '')).strip(),
        'validation_summary': validation_summary or str(item.get('validation_summary', '')).strip(),
        'evidence_note': evidence_note or str(item.get('evidence_note', '')).strip(),
        'review_evidence': evidence_note or _list_has_content(evidence.get('review_evidence', [])),
        'tests_run': _list_has_content(tests_run or []) or _list_has_content(item.get('tests_run', [])),
        'changed_files': _list_has_content(changed_files or []) or _list_has_content(item.get('changed_files', [])),
        'files_changed': _list_has_content(changed_files or []) or _list_has_content(evidence.get('files_changed', [])),
        'artifact_paths': _list_has_content(artifact_paths or []) or _list_has_content(item.get('artifact_paths', [])),
        'completion_evidence': _completion_evidence_has_meaningful_content(evidence),
        'evidence_summary': str(evidence.get('evidence_summary', '')).strip(),
        'validation_results': _list_has_content(evidence.get('validation_results', [])),
        'diff_check_result': str(evidence.get('diff_check_result', '')).strip(),
        'smoke_checks': _list_has_content(evidence.get('smoke_checks', [])),
    }
    missing: list[str] = []
    for requirement in requirements:
        normalized = requirement.strip()
        if not normalized:
            continue
        if not bool(values.get(normalized)):
            missing.append(normalized)
    return sorted(set(missing))


def _completion_lock_summary(item: dict[str, Any]) -> dict[str, Any]:
    status = str(item.get('status', '')).strip()
    requirements = _explicit_completion_requirements(item)
    missing = _missing_required_completion_evidence(item)
    blocked_reasons = [
        f'Required completion evidence is missing: {field_name}'
        for field_name in missing
    ]
    if status == 'done' and not requirements:
        lock_status = 'historical_done_not_rechecked'
        blocked_reasons = []
    elif status == 'done':
        lock_status = 'done_with_explicit_requirements' if not missing else 'done_missing_explicit_evidence'
    elif requirements and missing:
        lock_status = 'missing_required_evidence'
    elif requirements:
        lock_status = 'required_evidence_satisfied'
    else:
        lock_status = 'no_explicit_evidence_requirements'
    return {
        'blocked': bool(blocked_reasons and status != 'done'),
        'status': lock_status,
        'completion_requires': requirements,
        'missing_required_evidence': missing,
        'blocked_reasons': sorted(set(blocked_reasons if status != 'done' else [])),
    }


def _list_has_content(values: Any) -> bool:
    return isinstance(values, list) and any(str(value).strip() for value in values)


def _load_registry_projects_for_rollup(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    if not path.exists():
        return [], ['Managed project registry not found. Project name and active-project validation may be unavailable.']
    try:
        raw = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as exc:
        return [], [f'Managed project registry could not be parsed: {exc}']
    if not isinstance(raw, dict):
        return [], ['Managed project registry has invalid schema. Project name may be unavailable.']
    projects = raw.get('projects', [])
    if not isinstance(projects, list):
        return [], ['Managed project registry contains non-list projects field. Project name may be unavailable.']
    return [project for project in projects if isinstance(project, dict)], []


def _load_queue_items_for_rollup(path: Path) -> tuple[list[dict[str, Any]], str, list[str]]:
    if not path.exists():
        return [], '', ['Local project queue not found. Progress rollup is empty.']
    try:
        raw = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as exc:
        return [], '', [f'Local project queue could not be parsed: {exc}']
    if not isinstance(raw, dict):
        return [], '', ['Local project queue has invalid schema. Progress rollup is empty.']
    items = raw.get('work_items', [])
    if not isinstance(items, list):
        return [], str(raw.get('updated_at', '')).strip(), ['Local project queue contains non-list work_items field. Progress rollup is empty.']
    return [item for item in items if isinstance(item, dict)], str(raw.get('updated_at', '')).strip(), []


def _count_items_by(items: list[dict[str, Any]], field: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        if field == 'assigned_agent':
            value = str(item.get(field, '')).strip() or 'unassigned'
        else:
            value = str(item.get(field, '')).strip() or 'unknown'
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def _rollup_item_summary(item: dict[str, Any]) -> dict[str, str]:
    return {
        'item_id': str(item.get('item_id', '')).strip(),
        'title': str(item.get('title', '')).strip(),
        'status': str(item.get('status', '')).strip(),
        'priority': str(item.get('priority', '')).strip(),
        'item_type': str(item.get('item_type', '')).strip(),
        'assigned_agent': str(item.get('assigned_agent', '')).strip(),
    }


def _latest_rollup_activity(project: dict[str, Any], items: list[dict[str, Any]], queue_updated_at: str) -> str:
    timestamps: list[str] = [
        str(project.get('updated_at', '')).strip(),
        str(project.get('created_at', '')).strip(),
        str(queue_updated_at or '').strip(),
    ]
    for item in items:
        evidence = item.get('completion_evidence', {})
        timestamps.extend(
            [
                str(item.get('closed_at', '')).strip(),
                str(item.get('completed_at', '')).strip(),
                str(item.get('updated_at', '')).strip(),
                str(item.get('started_at', '')).strip(),
                str(item.get('created_at', '')).strip(),
                str(evidence.get('captured_at', '')).strip() if isinstance(evidence, dict) else '',
            ]
        )
    normalized = [value for value in timestamps if value]
    return max(normalized) if normalized else ''


def _project_progress_next_safe_action(
    *,
    total_items: int,
    ready_count: int,
    blocked_count: int,
    in_progress_count: int,
    closeout_eligible_count: int,
    closed_completed_count: int,
) -> str:
    if blocked_count:
        return 'Review blocked local queue items and resolve blockers before starting more work.'
    if closeout_eligible_count:
        return 'Review closeout-eligible queue items and close them out explicitly when the operator is satisfied.'
    if in_progress_count:
        return 'Capture or review completion evidence for in-progress queue items.'
    if ready_count:
        return 'Inspect readiness and explicitly start the next ready queue item when appropriate.'
    if total_items == 0:
        return 'Add local queue items for this project when the next milestone is ready.'
    if closed_completed_count == total_items:
        return 'Review project progress and prepare the next local planning/reporting milestone.'
    return 'Inspect local queue status and choose the next operator-gated action.'


def _empty_dependency_summary() -> dict[str, Any]:
    return {
        'total_dependencies': 0,
        'resolved_dependencies': [],
        'unresolved_dependencies': [],
        'total_blocked_by': 0,
        'unresolved_blockers': [],
        'dispatch_run_blockers': [],
        'recovered_dispatch_runs': [],
    }


def _dependency_readiness_summary(item: dict[str, Any], items: list[dict[str, Any]], *, repo_root: Path) -> dict[str, Any]:
    by_id = {str(candidate.get('item_id', '')).strip(): candidate for candidate in items if str(candidate.get('item_id', '')).strip()}
    dependencies = _queue_dependency_ids(item)
    blocked_by = _normalize_list(item.get('blocked_by', []) if isinstance(item.get('blocked_by'), list) else [])
    resolved_dependencies: list[str] = []
    unresolved_dependencies: list[dict[str, str]] = []
    unresolved_blockers: list[dict[str, str]] = []
    dispatch_run_blockers: list[dict[str, str]] = []
    recovered_dispatch_runs: list[dict[str, str]] = []
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
        dependency_resolution = _dependency_completion_resolution(
            repo_root=repo_root,
            item_id=dependency_id,
            dependency_item=dependency_item,
        )
        dispatch_run_blockers.extend(dependency_resolution['dispatch_run_blockers'])
        recovered_dispatch_runs.extend(dependency_resolution['recovered_dispatch_runs'])
        warnings.extend(dependency_resolution['warnings'])
        if dependency_status in _RESOLVED_DEPENDENCY_STATUSES and dependency_resolution['resolved']:
            resolved_dependencies.append(dependency_id)
            continue
        reason = 'dependency_incomplete'
        if dependency_status in _BLOCKED_QUEUE_STATUSES:
            reason = 'dependency_blocked'
        elif dependency_status in _RESOLVED_DEPENDENCY_STATUSES:
            reason = dependency_resolution['reason']
        unresolved_dependencies.append(
            {'item_id': dependency_id, 'status': dependency_status or 'unknown', 'reason': reason}
        )
        if dependency_status in _RESOLVED_DEPENDENCY_STATUSES:
            blockers.append(f'Dependency completion evidence is incomplete: {dependency_id} ({reason})')
        else:
            blockers.append(
                f'Dependency must be done before start: {dependency_id} (status={dependency_status or "unknown"})'
            )
        blockers.extend(dependency_resolution['blockers'])

    for blocker_id in blocked_by:
        blocker_item = by_id.get(blocker_id)
        if blocker_item is None:
            unresolved_blockers.append(
                {'item_id': blocker_id, 'status': 'unknown', 'reason': 'blocker_not_found'}
            )
            blockers.append(f'Blocked-by item not found in local queue: {blocker_id}')
            continue
        blocker_status = str(blocker_item.get('status', '')).strip()
        blocker_resolution = _dependency_completion_resolution(
            repo_root=repo_root,
            item_id=blocker_id,
            dependency_item=blocker_item,
        )
        dispatch_run_blockers.extend(blocker_resolution['dispatch_run_blockers'])
        recovered_dispatch_runs.extend(blocker_resolution['recovered_dispatch_runs'])
        warnings.extend(blocker_resolution['warnings'])
        if blocker_status in _RESOLVED_DEPENDENCY_STATUSES and blocker_resolution['resolved']:
            continue
        reason = 'blocker_not_resolved'
        if blocker_status in _RESOLVED_DEPENDENCY_STATUSES:
            reason = blocker_resolution['reason']
        unresolved_blockers.append(
            {'item_id': blocker_id, 'status': blocker_status or 'unknown', 'reason': reason}
        )
        if blocker_status in _RESOLVED_DEPENDENCY_STATUSES:
            blockers.append(f'Blocked-by completion evidence is incomplete: {blocker_id} ({reason})')
        else:
            blockers.append(
                f'Blocked-by item must be resolved before start: {blocker_id} (status={blocker_status or "unknown"})'
            )
        blockers.extend(blocker_resolution['blockers'])

    if dependencies and not unresolved_dependencies:
        warnings.append('Dependencies are present and currently resolved.')

    return {
        'payload': {
            'total_dependencies': len(dependencies),
            'resolved_dependencies': resolved_dependencies,
            'unresolved_dependencies': unresolved_dependencies,
            'total_blocked_by': len(blocked_by),
            'unresolved_blockers': unresolved_blockers,
            'dispatch_run_blockers': dispatch_run_blockers,
            'recovered_dispatch_runs': recovered_dispatch_runs,
        },
        'blockers': blockers,
        'warnings': warnings,
    }


def _queue_dependency_ids(item: dict[str, Any]) -> list[str]:
    dependencies: list[str] = []
    for field_name in ('dependencies', 'depends_on'):
        values = item.get(field_name, [])
        if isinstance(values, list):
            dependencies.extend(str(value).strip() for value in values)
    return _normalize_list(dependencies)


def _dependency_completion_resolution(
    *,
    repo_root: Path,
    item_id: str,
    dependency_item: dict[str, Any],
) -> dict[str, Any]:
    status = str(dependency_item.get('status', '')).strip()
    dispatch_summary = _dispatch_run_blocking_summary(
        repo_root=repo_root,
        item_id=item_id,
        dependency_item=dependency_item,
    )
    if status not in _RESOLVED_DEPENDENCY_STATUSES:
        return {
            'resolved': False,
            'reason': 'dependency_not_done',
            'blockers': dispatch_summary['blockers'],
            'dispatch_run_blockers': dispatch_summary['blocking_runs'],
            'recovered_dispatch_runs': dispatch_summary['recovered_runs'],
            'warnings': dispatch_summary['warnings'],
        }
    if dispatch_summary['blocking_runs']:
        return {
            'resolved': False,
            'reason': 'dispatch_run_state_unreviewed_or_incomplete',
            'blockers': dispatch_summary['blockers'],
            'dispatch_run_blockers': dispatch_summary['blocking_runs'],
            'recovered_dispatch_runs': dispatch_summary['recovered_runs'],
            'warnings': dispatch_summary['warnings'],
        }
    if not _queue_item_has_required_completion_evidence(dependency_item):
        return {
            'resolved': False,
            'reason': 'required_completion_review_validation_or_queue_evidence_missing',
            'blockers': [],
            'dispatch_run_blockers': [],
            'recovered_dispatch_runs': dispatch_summary['recovered_runs'],
            'warnings': dispatch_summary['warnings'],
        }
    return {
        'resolved': True,
        'reason': 'resolved',
        'blockers': [],
        'dispatch_run_blockers': [],
        'recovered_dispatch_runs': dispatch_summary['recovered_runs'],
        'warnings': dispatch_summary['warnings'],
    }


def _dispatch_run_blocking_summary(*, repo_root: Path, item_id: str, dependency_item: dict[str, Any]) -> dict[str, Any]:
    blocking_runs: list[dict[str, str]] = []
    recovered_runs: list[dict[str, str]] = []
    blockers: list[str] = []
    warnings: list[str] = []
    runs_root = (repo_root / _CODEX_DISPATCH_RUNS_RELATIVE).resolve()
    if not runs_root.exists():
        return {'blocking_runs': blocking_runs, 'recovered_runs': recovered_runs, 'blockers': blockers, 'warnings': warnings}
    for path in sorted(runs_root.glob(f'*/{_CODEX_DISPATCH_RUN_STATE_FILE_NAME}')):
        try:
            raw = json.loads(path.read_text(encoding='utf-8-sig'))
        except (OSError, json.JSONDecodeError) as exc:
            blocking_runs.append(
                {
                    'run_id': path.parent.name,
                    'item_id': item_id,
                    'dispatch_state': 'unknown',
                    'reason': 'run_state_unreadable',
                }
            )
            blockers.append(f'Dependency dispatch run state could not be inspected for {item_id}: {exc}')
            continue
        if not isinstance(raw, dict) or str(raw.get('item_id', '')).strip() != item_id:
            continue
        dispatch_state = str(raw.get('dispatch_state', '')).strip()
        run_id = str(raw.get('run_id', path.parent.name)).strip() or path.parent.name
        reason = ''
        if dispatch_state in _BLOCKING_DISPATCH_STATES:
            reason = f'dispatch_state_{dispatch_state}'
        elif dispatch_state == 'failed' and _dispatch_run_has_recovery_metadata(raw):
            if _recovered_failed_dispatch_run_is_non_blocking(raw, dependency_item):
                recovered_runs.append(
                    {
                        'run_id': run_id,
                        'item_id': item_id,
                        'dispatch_state': dispatch_state,
                        'reason': 'failed_dispatch_recovered_and_audited',
                    }
                )
                warnings.append(
                    f'Recovered failed dependency dispatch run audited as non-blocking: {item_id}/{run_id}'
                )
                continue
            reason = 'dispatch_state_failed_recovered_without_dependency_completion_evidence'
        elif dispatch_state in _DISPATCH_STATES_REQUIRING_REVIEW_EVIDENCE and not _dispatch_run_has_review_and_validation_evidence(raw):
            reason = f'dispatch_state_{dispatch_state}_missing_review_or_validation_evidence'
        if reason:
            blocking_runs.append(
                {
                    'run_id': run_id,
                    'item_id': item_id,
                    'dispatch_state': dispatch_state or 'unknown',
                    'reason': reason,
                }
            )
            blockers.append(f'Dependency dispatch run blocks sequencing: {item_id}/{run_id} ({reason})')
    return {
        'blocking_runs': blocking_runs,
        'recovered_runs': recovered_runs,
        'blockers': blockers,
        'warnings': warnings,
    }


def _dispatch_run_has_recovery_metadata(run_state: dict[str, Any]) -> bool:
    recovery = run_state.get('recovery', {})
    return bool(
        isinstance(recovery, dict)
        and str(recovery.get('recovered_at', '')).strip()
        and str(recovery.get('recovery_note', '')).strip()
    )


def _recovered_failed_dispatch_run_is_non_blocking(run_state: dict[str, Any], dependency_item: dict[str, Any]) -> bool:
    return bool(
        str(run_state.get('dispatch_state', '')).strip() == 'failed'
        and _dispatch_run_has_recovery_metadata(run_state)
        and str(dependency_item.get('status', '')).strip() in _RESOLVED_DEPENDENCY_STATUSES
        and str(dependency_item.get('completion_commit', '')).strip()
        and str(dependency_item.get('validation_summary', '')).strip()
        and isinstance(dependency_item.get('tests_run', []), list)
        and any(str(value).strip() for value in dependency_item.get('tests_run', []))
    )


def _dispatch_run_has_review_and_validation_evidence(run_state: dict[str, Any]) -> bool:
    review_evidence = run_state.get('review_evidence', [])
    validation_evidence = run_state.get('validation_evidence', [])
    return (
        isinstance(review_evidence, list)
        and any(str(value).strip() for value in review_evidence)
        and isinstance(validation_evidence, list)
        and any(str(value).strip() for value in validation_evidence)
    )


def _queue_item_has_required_completion_evidence(item: dict[str, Any]) -> bool:
    closeout_history = item.get('closeout_history', [])
    if isinstance(closeout_history, list) and closeout_history:
        latest = closeout_history[-1]
        if isinstance(latest, dict):
            evidence = latest.get('completion_evidence', {})
            if isinstance(evidence, dict) and _completion_evidence_has_required_closeout_fields(evidence):
                return bool(str(latest.get('closed_at', '')).strip() and str(latest.get('closeout_summary', '')).strip())
    evidence = item.get('completion_evidence', {})
    if isinstance(evidence, dict) and _completion_evidence_has_required_closeout_fields(evidence):
        return bool(str(item.get('closed_at', '')).strip() or str(evidence.get('captured_at', '')).strip())
    return bool(
        str(item.get('completed_at', '')).strip()
        and str(item.get('completion_commit', '')).strip()
        and str(item.get('validation_summary', '')).strip()
        and str(item.get('evidence_note', '')).strip()
    )


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
        'depends_on': _normalize_list(item.get('depends_on', []) if isinstance(item.get('depends_on'), list) else []),
        'blocked_by': _normalize_list(item.get('blocked_by', []) if isinstance(item.get('blocked_by'), list) else []),
        'completion_requires': _normalize_list(
            item.get('completion_requires', []) if isinstance(item.get('completion_requires'), list) else []
        ),
        'evidence_required': _normalize_list(
            item.get('evidence_required', []) if isinstance(item.get('evidence_required'), list) else []
        ),
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
        'completion_evidence': item.get('completion_evidence', {}) if isinstance(item.get('completion_evidence'), dict) else {},
        'routing_metadata': default_queue_routing_metadata(
            item.get('routing_metadata', {}) if isinstance(item.get('routing_metadata'), dict) else {}
        ),
        'closed_at': str(item.get('closed_at', '')).strip(),
        'closed_by': str(item.get('closed_by', '')).strip(),
        'closeout_summary': str(item.get('closeout_summary', '')).strip(),
        'closeout_history': item.get('closeout_history', []) if isinstance(item.get('closeout_history'), list) else [],
        'created_at': str(item.get('created_at', '')).strip(),
        'updated_at': str(item.get('updated_at', '')).strip(),
    }


def default_queue_routing_metadata(values: dict[str, Any] | None = None) -> dict[str, Any]:
    raw = values if isinstance(values, dict) else {}
    metadata = {
        'recommended_agent_lane': str(raw.get('recommended_agent_lane', '') or '').strip(),
        'recommended_engine': str(raw.get('recommended_engine', '') or '').strip(),
        'recommended_model': str(raw.get('recommended_model', '') or '').strip(),
        'fallback_engine': str(raw.get('fallback_engine', '') or '').strip(),
        'fallback_model': str(raw.get('fallback_model', '') or '').strip(),
        'routing_policy_source': str(raw.get('routing_policy_source', '') or '').strip(),
        'routing_reason': str(raw.get('routing_reason', '') or '').strip(),
        'risk_level': str(raw.get('risk_level', 'unknown') or 'unknown').strip(),
        'complexity_level': str(raw.get('complexity_level', 'unknown') or 'unknown').strip(),
        'escalation_reason': str(raw.get('escalation_reason', '') or '').strip(),
        'project_ai_mode': str(raw.get('project_ai_mode', '') or '').strip(),
        'operator_override': raw.get('operator_override', False),
    }
    if not isinstance(metadata['operator_override'], bool) and not isinstance(metadata['operator_override'], dict):
        metadata['operator_override'] = bool(metadata['operator_override'])
    return metadata


def validate_queue_routing_metadata(metadata: dict[str, Any] | None) -> dict[str, Any]:
    normalized = default_queue_routing_metadata(metadata)
    blockers: list[str] = []
    warnings: list[str] = []

    agent_lane = normalized.get('recommended_agent_lane', '')
    if agent_lane and agent_lane not in QUEUE_ROUTING_AGENT_LANES:
        blockers.append('recommended_agent_lane must be one of the supported M52 agent lanes.')

    for field in ('recommended_engine', 'fallback_engine'):
        engine = str(normalized.get(field, '')).strip()
        if engine and engine not in QUEUE_ROUTING_ENGINES:
            blockers.append(f'{field} must be one of the supported M52 engine keys.')

    risk_level = str(normalized.get('risk_level', '')).strip() or 'unknown'
    if risk_level not in QUEUE_ROUTING_RISK_LEVELS:
        blockers.append('risk_level must be low, medium, high, critical, or unknown.')

    complexity_level = str(normalized.get('complexity_level', '')).strip() or 'unknown'
    if complexity_level not in QUEUE_ROUTING_COMPLEXITY_LEVELS:
        blockers.append('complexity_level must be low, medium, high, or unknown.')

    operator_override = normalized.get('operator_override')
    if not isinstance(operator_override, bool) and not isinstance(operator_override, dict):
        blockers.append('operator_override must be a boolean or structured JSON object.')

    if not any(
        value
        for key, value in normalized.items()
        if key != 'operator_override' and str(value or '').strip() and str(value or '').strip() != 'unknown'
    ) and normalized.get('operator_override') is False:
        warnings.append('Routing metadata is empty/unassigned and will not affect queue behavior.')

    return {
        'valid': not blockers,
        'routing_execution_status': 'not_implemented',
        'blockers': sorted(set(blockers)),
        'warnings': sorted(set(warnings)),
        'supported_agent_lanes': list(QUEUE_ROUTING_AGENT_LANES),
        'supported_engines': list(QUEUE_ROUTING_ENGINES),
        'supported_risk_levels': list(QUEUE_ROUTING_RISK_LEVELS),
        'supported_complexity_levels': list(QUEUE_ROUTING_COMPLEXITY_LEVELS),
    }


def _is_routed_metadata(metadata: dict[str, Any]) -> bool:
    normalized = default_queue_routing_metadata(metadata)
    override = normalized.get('operator_override')
    has_routing_value = any(
        str(value or '').strip() and str(value or '').strip() != 'unknown'
        for key, value in normalized.items()
        if key != 'operator_override'
    )
    return has_routing_value or (override not in (False, None, '') and override != {})


def _operator_override_matches(value: Any, expected: str | bool) -> bool:
    if isinstance(expected, bool):
        return bool(value) is expected
    normalized = str(expected or '').strip().lower()
    if normalized == 'present':
        return value not in (False, None, '') and value != {}
    if normalized == 'true':
        return bool(value) is True
    if normalized == 'false':
        return bool(value) is False
    return True


def _routed_view_filters(
    *,
    project_id: str | None,
    status: str | None,
    recommended_agent_lane: str | None,
    recommended_engine: str | None,
    recommended_model: str | None,
    fallback_engine: str | None,
    risk_level: str | None,
    complexity_level: str | None,
    project_ai_mode: str | None,
    routing_policy_source: str | None,
    operator_override: str | bool | None,
    include_unrouted: bool,
) -> dict[str, Any]:
    return {
        'project_id': str(project_id or '').strip(),
        'status': str(status or '').strip(),
        'recommended_agent_lane': str(recommended_agent_lane or '').strip(),
        'recommended_engine': str(recommended_engine or '').strip(),
        'recommended_model': str(recommended_model or '').strip(),
        'fallback_engine': str(fallback_engine or '').strip(),
        'risk_level': str(risk_level or '').strip(),
        'complexity_level': str(complexity_level or '').strip(),
        'project_ai_mode': str(project_ai_mode or '').strip(),
        'routing_policy_source': str(routing_policy_source or '').strip(),
        'operator_override': operator_override,
        'include_unrouted': bool(include_unrouted),
    }


def _group_routed_items(items: list[dict[str, Any]], field: str) -> dict[str, dict[str, Any]]:
    groups: dict[str, dict[str, Any]] = {}
    for item in items:
        metadata = item.get('routing_metadata', {}) if isinstance(item.get('routing_metadata'), dict) else {}
        if field == 'status':
            value = str(item.get('status', '')).strip()
        else:
            value = str(metadata.get(field, '')).strip()
        group_key = value or 'unrouted'
        if group_key == 'unknown' and field in {'risk_level', 'complexity_level'} and not item.get('routed'):
            group_key = 'unrouted'
        entry = groups.setdefault(group_key, {'count': 0, 'items': []})
        entry['count'] += 1
        entry['items'].append(
            {
                'item_id': item.get('item_id', ''),
                'title': item.get('title', ''),
                'status': item.get('status', ''),
                'project_id': item.get('project_id', ''),
                'recommended_agent_lane': metadata.get('recommended_agent_lane', ''),
                'recommended_engine': metadata.get('recommended_engine', ''),
                'risk_level': metadata.get('risk_level', 'unknown'),
                'complexity_level': metadata.get('complexity_level', 'unknown'),
                'routed': bool(item.get('routed', False)),
            }
        )
    return dict(sorted(groups.items()))


def _prompt_pack_routing_guidance(metadata: dict[str, Any], routed: bool) -> str:
    engine = str(metadata.get('recommended_engine', '')).strip()
    if not routed:
        return 'Manual routing required; this queue item is unrouted and no engine is executed by AresForge.'
    if engine == 'codex_cli':
        return 'Codex CLI is recommended for operator review, but AresForge does not execute Codex; this is prompt-generation/operator-handoff only.'
    if engine in {'local_reasoning_llm', 'local_coding_llm'}:
        return f'{engine} is recommended for operator review, but AresForge does not execute local LLMs and local LLM output must not mutate repo files.'
    return 'Routing metadata is advisory only; no engine, model, agent, prompt, or workflow is executed by AresForge.'


def _prompt_pack_lane_guidance(metadata: dict[str, Any], routed: bool) -> str:
    lane = str(metadata.get('recommended_agent_lane', '')).strip()
    engine = str(metadata.get('recommended_engine', '')).strip()
    project_ai_mode = str(metadata.get('project_ai_mode', '')).strip()
    if not routed or project_ai_mode == 'manual_only':
        return 'Operator-only/manual lane: inspect routing locally, decompose if needed, and do not dispatch prompts automatically.'
    if lane == 'high_value_codex' or engine == 'codex_cli':
        return 'High-value Codex lane: prompt-generation/operator-handoff only; do not invoke Codex CLI or apply changes automatically.'
    if engine in {'local_reasoning_llm', 'local_coding_llm'}:
        return 'Local LLM advisory lane: local-only advisory review only; no automatic execution and no repo mutation from local LLM output.'
    if lane in {'documentation', 'reviewer_validator', 'review', 'docs'}:
        return 'Documentation/review lane: review or documentation guidance only; operator applies any accepted changes manually.'
    return 'Routing lane is advisory metadata only; operator keeps execution, validation, mutation, commit, and push decisions manual.'


def _prompt_pack_task_size_guidance(item: dict[str, Any], metadata: dict[str, Any], routed: bool) -> str:
    complexity = str(metadata.get('complexity_level', '')).strip().lower()
    risk = str(metadata.get('risk_level', '')).strip().lower()
    description = str(item.get('description', '')).strip()
    dependencies = _normalize_list(item.get('blocked_by', []))
    if not routed and not description:
        return 'too broad/requires decomposition - missing routing and description; operator should clarify scope before handoff.'
    if complexity in {'critical', 'high'} or risk in {'critical', 'high'}:
        return 'high-value/complex - use careful operator review, targeted validation, and explicit handoff boundaries.'
    if complexity in {'medium', 'moderate'} or risk in {'medium', 'moderate'} or dependencies:
        return 'medium - confirm dependencies and run targeted local validation before closeout.'
    if complexity in {'low', 'small'} or risk in {'low'}:
        return 'small - suitable for narrow manual handoff with focused validation.'
    if len(description) > 800:
        return 'too broad/requires decomposition - long or ambiguous task text should be split before execution.'
    return 'medium - routing metadata is incomplete, so operator should size conservatively.'


def _prompt_pack_model_recommendation(metadata: dict[str, Any], routed: bool) -> str:
    if not routed:
        return 'No model or engine recommendation; manual routing review required before copy/paste handoff.'
    engine = str(metadata.get('recommended_engine', '')).strip() or 'unrouted'
    model = str(metadata.get('recommended_model', '')).strip() or 'unspecified model'
    fallback_engine = str(metadata.get('fallback_engine', '')).strip()
    fallback_model = str(metadata.get('fallback_model', '')).strip()
    policy_source = str(metadata.get('routing_policy_source', '')).strip() or 'manual_required'
    fallback = 'No automatic fallback is selected.'
    if fallback_engine or fallback_model:
        fallback = f'Fallback metadata: {fallback_engine or "unspecified engine"} / {fallback_model or "unspecified model"}; operator must choose manually.'
    return f'Advisory only: {engine} / {model} from {policy_source}. {fallback}'


def _read_local_llm_environment_for_preview(repo_root: Path) -> dict[str, Any]:
    path = (repo_root / '.aresforge' / 'local_llm_environment.json').resolve()
    if not path.exists():
        return {'exists': False, 'path': str(path), 'environment': {}, 'warnings': []}
    try:
        loaded = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as exc:
        return {'exists': True, 'path': str(path), 'environment': {}, 'warnings': [f'Local LLM environment could not be parsed: {exc}']}
    if not isinstance(loaded, dict):
        return {'exists': True, 'path': str(path), 'environment': {}, 'warnings': ['Local LLM environment has invalid schema; expected JSON object.']}
    return {'exists': True, 'path': str(path), 'environment': loaded, 'warnings': []}


def _read_project_ai_settings_for_preview(repo_root: Path, project_id: str) -> dict[str, Any]:
    if not project_id:
        return {}
    path = (repo_root / '.aresforge' / 'projects' / project_id / 'ai_settings.json').resolve()
    if not path.exists():
        return {}
    try:
        loaded = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _is_local_llm_provider_url(provider_base_url: str) -> bool:
    parsed = urlparse(provider_base_url)
    host = (parsed.hostname or '').lower()
    return parsed.scheme in {'http', 'https'} and host in {'localhost', '127.0.0.1', '::1'}


def _call_ollama_generate_for_queue_item(
    *,
    provider_base_url: str,
    model: str,
    prompt: str,
    timeout_seconds: int,
) -> str:
    if not _is_local_llm_provider_url(provider_base_url):
        raise ValueError('provider_base_url must be local for Ollama execution.')
    if not model:
        raise ValueError('model is required for Ollama execution.')
    body = json.dumps({'model': model, 'prompt': prompt, 'stream': False}).encode('utf-8')
    request = Request(
        provider_base_url.rstrip('/') + '/api/generate',
        data=body,
        method='POST',
        headers={'Content-Type': 'application/json'},
    )
    with urlopen(request, timeout=timeout_seconds) as response:
        raw = response.read()
    parsed = json.loads(raw.decode('utf-8'))
    if not isinstance(parsed, dict):
        raise ValueError('Ollama generate response must be a JSON object.')
    return str(parsed.get('response', '')).strip()


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(child) for key, child in value.items()}
    if isinstance(value, list):
        return [_json_safe(child) for child in value]
    try:
        json.dumps(value)
    except TypeError:
        return str(value)
    return value


def _build_local_llm_prompt_preview_text(
    *,
    item: dict[str, Any],
    routing_metadata: dict[str, Any],
    readiness: dict[str, Any],
    prompt_style: str,
    include_context: bool,
    local_only_rules: list[str],
    validation_expectations: list[str],
    final_response_format: list[str],
    recommended_engine: str,
    recommended_model: str,
    project_ai_mode: str,
) -> str:
    parsed_notes = _parse_queue_item_notes(str(item.get('notes', '')).strip())
    acceptance = parsed_notes.get('acceptance_criteria', []) if isinstance(parsed_notes, dict) else []
    extra_notes = str(parsed_notes.get('notes', '')).strip() if isinstance(parsed_notes, dict) else ''
    lines: list[str] = [
        'Local LLM Prompt Preview (No Execution)',
        '',
        'Use this as a copy/paste prompt only after operator review.',
        'Do not claim execution, file changes, validation, commits, pushes, or external actions unless they were actually performed outside this preview.',
        '',
        '## Routing',
        f'- recommended_engine: {recommended_engine}',
        f'- recommended_model: {recommended_model}',
        f'- recommended_agent_lane: {routing_metadata.get("recommended_agent_lane") or "unrouted"}',
        f'- routing_policy_source: {routing_metadata.get("routing_policy_source") or "-"}',
        f'- routing_reason: {routing_metadata.get("routing_reason") or "-"}',
        f'- risk_level: {routing_metadata.get("risk_level") or "unknown"}',
        f'- complexity_level: {routing_metadata.get("complexity_level") or "unknown"}',
        f'- project_ai_mode: {project_ai_mode or "-"}',
        '- execution_allowed: false',
        '',
        '## Task',
        f'- item_id: {item.get("item_id", "")}',
        f'- title: {item.get("title", "")}',
        f'- project_id: {item.get("project_id", "") or "-"}',
        f'- repo_id: {item.get("repo_id", "") or "-"}',
        f'- status: {item.get("status", "") or "-"}',
        f'- priority: {item.get("priority", "") or "-"}',
        f'- type: {item.get("item_type", "") or "-"}',
        f'- readiness: {readiness.get("readiness_status", "unknown")}',
        f'- next_safe_action: {readiness.get("recommended_next_action", "Inspect readiness locally.")}',
        '',
        '## Summary',
        str(item.get('description', '')).strip() or 'No description supplied.',
        '',
    ]
    if include_context:
        lines.extend(
            [
                '## Context',
                f'- source: {item.get("source", "") or "-"}',
                f'- assigned_agent: {item.get("assigned_agent", "") or "unassigned"}',
                f'- blocked_by: {", ".join(_normalize_list(item.get("blocked_by", []))) or "-"}',
                '',
            ]
        )
    lines.extend(['## Acceptance Criteria'])
    if isinstance(acceptance, list) and acceptance:
        lines.extend([f'- {entry}' for entry in acceptance if str(entry).strip()])
    else:
        lines.append('- No explicit acceptance criteria recorded.')
    if extra_notes:
        lines.extend(['', '## Additional Notes', extra_notes])
    lines.extend(['', '## Local-Only Rules'])
    lines.extend([f'- {rule}' for rule in local_only_rules])
    if validation_expectations:
        lines.extend(['', '## Validation Expectations'])
        lines.extend([f'- {entry}' for entry in validation_expectations])
    lines.extend(['', '## Requested Work', f'- prompt_style: {prompt_style}', '- Provide a plan or implementation guidance for the task above.', '- Do not execute commands, mutate files, call services, or claim validation unless explicitly performed outside this prompt preview.'])
    lines.extend(['', '## Final Response Format'])
    lines.extend([f'- {entry}' for entry in final_response_format])
    return '\n'.join(lines).rstrip()


def _evaluate_codex_high_value_lane_eligibility(
    *,
    item: dict[str, Any],
    routing_metadata: dict[str, Any],
    operator_override: bool,
) -> dict[str, Any]:
    reasons: list[str] = []
    recommended_engine = str(routing_metadata.get('recommended_engine', '')).strip()
    recommended_agent_lane = str(routing_metadata.get('recommended_agent_lane', '')).strip()
    risk_level = str(routing_metadata.get('risk_level', 'unknown')).strip()
    complexity_level = str(routing_metadata.get('complexity_level', 'unknown')).strip()
    project_ai_mode = str(routing_metadata.get('project_ai_mode', '')).strip()
    routing_reason = str(routing_metadata.get('routing_reason', '')).strip()
    escalation_reason = str(routing_metadata.get('escalation_reason', '')).strip()

    if recommended_engine == 'codex_cli':
        reasons.append('recommended_engine is codex_cli')
    if recommended_agent_lane == 'high_value_codex':
        reasons.append('recommended_agent_lane is high_value_codex')
    if risk_level in {'high', 'critical'}:
        reasons.append(f'risk_level is {risk_level}')
    if complexity_level == 'high':
        reasons.append('complexity_level is high')
    if project_ai_mode in {'codex_only', 'high_confidence'}:
        reasons.append(f'project_ai_mode is {project_ai_mode}')
    if operator_override or bool(routing_metadata.get('operator_override')):
        reasons.append('operator override requests Codex')

    area_text = ' '.join(
        [
            str(item.get('title', '')),
            str(item.get('description', '')),
            str(item.get('notes', '')),
            ' '.join(_normalize_list(item.get('tags', []) if isinstance(item.get('tags'), list) else [])),
            routing_reason,
            escalation_reason,
        ]
    ).lower()
    high_value_area_markers = {
        'backend',
        'operator lifecycle',
        'data contract',
        'data contracts',
        'api route',
        'api routes',
        'queue lifecycle',
        'routing matrix',
        'execution path',
        'evidence',
        'closeout',
        'source-of-truth',
        'source of truth',
        'reconciliation',
    }
    matched_areas = sorted(marker for marker in high_value_area_markers if marker in area_text)
    if matched_areas:
        reasons.append(f'affected area includes {", ".join(matched_areas)}')
    if 'validation burden' in area_text and 'high' in area_text:
        reasons.append('validation burden is high')
    if 'high validation' in area_text or 'validation: high' in area_text:
        reasons.append('validation burden is high')

    return {
        'eligible': bool(reasons),
        'reason': '; '.join(reasons) if reasons else 'No high-value Codex lane eligibility criteria matched.',
        'reasons': reasons,
    }


def _build_codex_high_value_lane_prompt_preview(
    *,
    repo_root: Path,
    item: dict[str, Any],
    readiness: dict[str, Any],
    routing_metadata: dict[str, Any],
    codex_lane_reason: str,
    include_context: bool,
    include_validation_expectations: bool,
    include_operating_rules: bool,
) -> str:
    parsed_notes = _parse_queue_item_notes(str(item.get('notes', '')).strip())
    acceptance = parsed_notes.get('acceptance_criteria', []) if isinstance(parsed_notes, dict) else []
    extra_notes = str(parsed_notes.get('notes', '')).strip() if isinstance(parsed_notes, dict) else ''
    validation_commands = [
        'python -m pytest tests/test_local_project_queue.py tests/test_hub_local_queue_lifecycle_api.py tests/test_hub_ui_foundation.py tests/test_local_project_factory.py tests/test_hub_project_factory_api.py',
        'python -m aresforge inspect-local-queue-agent-summary',
        'python -m aresforge inspect-local-project-report',
        'git diff --check',
        'git status --short',
    ]
    files_to_inspect = [
        'src/aresforge/operator/local_project_queue.py',
        'src/aresforge/operator/local_project_factory.py',
        'src/aresforge/hub/api.py',
        'src/aresforge/hub/server.py',
        'src/aresforge/hub/static/index.html',
        'src/aresforge/hub/static/js/sections/queue.js',
        'tests/test_local_project_queue.py',
        'tests/test_hub_local_queue_lifecycle_api.py',
        'tests/test_hub_ui_foundation.py',
        'docs/context/BUILD_STATE.md',
        'docs/context/AGENT_CONTEXT.md',
        'docs/roadmap/ROADMAP.md',
    ]
    lines: list[str] = [
        'Codex CLI High-Value Lane Prompt (Manual Operator Copy/Paste Only)',
        '',
        f'Milestone/task title: {item.get("title", "") or item.get("item_id", "")}',
        f'Repo path: {repo_root}',
        '',
        'Important boundary:',
        '- Codex may perform coding only when the human operator manually provides this prompt to Codex.',
        '- AresForge must not automatically execute Codex.',
        '- AresForge must not call GitHub API, gh, issues, PRs, or workflows.',
        '- Codex output must be validated locally before commit/push.',
        '',
    ]
    if include_operating_rules:
        lines.extend(
            [
                'Operating rules:',
                '- Local-first.',
                '- File-backed.',
                '- Operator-gated.',
                '- One canonical local queue remains the source of truth.',
                '- No GitHub API.',
                '- No gh.',
                '- No GitHub issues.',
                '- No GitHub PRs.',
                '- No GitHub workflow activity.',
                '- No GitHub mutation from the app.',
                '- No automatic agent execution.',
                '- No automatic Codex execution.',
                '- No external workflow execution.',
                '- Codex lane output is advisory/copy-paste/operator-controlled.',
                '- Keep changes small and focused.',
                '- Use targeted validation.',
                '',
            ]
        )
    if include_context:
        lines.extend(
            [
                'Queue item context:',
                f'- item_id: {item.get("item_id", "")}',
                f'- project_id: {item.get("project_id", "") or "-"}',
                f'- repo_id: {item.get("repo_id", "") or "-"}',
                f'- status: {item.get("status", "") or "-"}',
                f'- priority: {item.get("priority", "") or "-"}',
                f'- item_type: {item.get("item_type", "") or "-"}',
                f'- readiness_status: {readiness.get("readiness_status", "unknown")}',
                f'- recommended_engine: {routing_metadata.get("recommended_engine") or "-"}',
                f'- recommended_model: {routing_metadata.get("recommended_model") or "-"}',
                f'- recommended_agent_lane: {routing_metadata.get("recommended_agent_lane") or "-"}',
                f'- risk_level: {routing_metadata.get("risk_level") or "unknown"}',
                f'- complexity_level: {routing_metadata.get("complexity_level") or "unknown"}',
                f'- project_ai_mode: {routing_metadata.get("project_ai_mode") or "-"}',
                f'- codex_lane_reason: {codex_lane_reason}',
                '',
                'Implementation goal:',
                str(item.get('description', '')).strip() or 'Implement the queue item conservatively.',
                '',
            ]
        )
    lines.extend(['Files to inspect:'])
    lines.extend([f'- {path}' for path in files_to_inspect])
    lines.extend(
        [
            '',
            'Pre-check commands:',
            '- git status --short',
            '- git branch --show-current',
            '- git log -1 --oneline',
            '',
            'Constraints:',
            '- Do not execute Codex from AresForge.',
            '- Do not use GitHub API, gh, issues, PRs, workflows, or GitHub mutation.',
            '- Do not mutate repository files from generated Codex output without local human/operator control.',
            '- Preserve M62 local LLM execution gates and do not weaken local LLM safety checks.',
            '- Avoid nested markdown fences inside PowerShell here-string bodies or generated prompt bodies.',
            '',
            'Acceptance criteria:',
        ]
    )
    if isinstance(acceptance, list) and acceptance:
        lines.extend([f'- {entry}' for entry in acceptance if str(entry).strip()])
    else:
        lines.append('- Implement the requested item with focused local changes and tests.')
    if extra_notes:
        lines.extend(['', 'Additional notes:', extra_notes])
    if include_validation_expectations:
        lines.extend(['', 'Validation commands:'])
        lines.extend([f'- {command}' for command in validation_commands])
        lines.extend(
            [
                '',
                'Smoke checks:',
                '- python -m aresforge inspect-local-queue-agent-summary',
                '- python -m aresforge inspect-local-project-report',
                '',
                'Diff check:',
                '- git diff --check',
            ]
        )
    lines.extend(
        [
            '',
            'Commit and push instructions only after validation:',
            '- git add .',
            '- git commit -m "<operator-approved message>"',
            '- git push origin main',
            '- git log -1 --oneline',
            '- git status --short',
            '',
            'Required final response format:',
            '- Files changed',
            '- What was changed',
            '- Tests updated and why',
            '- Validation results',
            '- Smoke check results',
            '- Diff check result',
            '- Commit hash',
            '- Push result',
        ]
    )
    return '\n'.join(lines).rstrip()


def _dependency_warnings(item: dict[str, Any], queue_items: list[dict[str, Any]]) -> list[str]:
    existing_ids = {
        str(candidate.get('item_id', '')).strip()
        for candidate in queue_items
        if isinstance(candidate, dict) and str(candidate.get('item_id', '')).strip()
    }
    warnings: list[str] = []
    for field_name in ('dependencies', 'depends_on', 'blocked_by'):
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


def _render_queue_consistency_markdown(payload: dict[str, Any]) -> str:
    lines = [
        '# Local Queue Consistency',
        '',
        f"- queue_path: {payload.get('queue_path')}",
        f"- project_id: {payload.get('project_id') or ''}",
        f"- repo_id: {payload.get('repo_id') or ''}",
        f"- item_count: {payload.get('item_count')}",
        f"- dependency_blocked_item_count: {payload.get('dependency_lock_summary', {}).get('blocked_item_count') if isinstance(payload.get('dependency_lock_summary'), dict) else 0}",
        f"- completion_blocked_item_count: {payload.get('completion_lock_summary', {}).get('blocked_item_count') if isinstance(payload.get('completion_lock_summary'), dict) else 0}",
        '',
        '## Blocked Items',
    ]
    blocked_items = payload.get('blocked_items', [])
    if not isinstance(blocked_items, list) or not blocked_items:
        lines.append('- None')
    else:
        for item in blocked_items:
            if not isinstance(item, dict):
                continue
            reasons = item.get('blocked_reasons', [])
            lines.append(
                f"- {item.get('item_id')} | status={item.get('status')} | reasons={'; '.join(reasons) if isinstance(reasons, list) else ''}"
            )
    lines.extend(['', f"- next_safe_action: {payload.get('next_safe_action')}"])
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
