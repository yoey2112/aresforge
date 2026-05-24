from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig

AGENTS_DIR_RELATIVE = Path('.aresforge') / 'agents'
AGENTS_FILE_NAME = 'agents.json'
AGENT_PROFILES_SCHEMA_VERSION = '1.0'

AGENT_ROLES: tuple[str, ...] = (
    'architect',
    'implementer',
    'tester',
    'documentation',
    'reviewer',
    'operator',
    'coordinator',
    'local_llm',
    'cloud_llm',
    'other',
)

EXECUTION_MODES: tuple[str, ...] = (
    'human',
    'codex',
    'local_llm',
    'cloud_llm',
    'scripted',
    'manual',
    'other',
)

HANDOFF_TARGET_TYPES: tuple[str, ...] = (
    'human_prompt',
    'codex_prompt',
    'local_llm_prompt',
    'cloud_llm_prompt',
    'script_input',
    'markdown_packet',
    'json_packet',
    'other',
)

AGENT_PROFILE_STATUSES: tuple[str, ...] = ('active', 'paused', 'archived', 'planned')


def init_agent_profiles(
    config: AppConfig,
    *,
    path: str | Path | None = None,
    force: bool = False,
    with_defaults: bool = False,
) -> dict[str, Any]:
    profiles_path = resolve_agent_profiles_path(config.repo_root, path)
    if profiles_path.exists() and not force:
        return _error(
            'agent_profiles_exists',
            {
                'path': str(profiles_path),
                'message': 'Agent profiles file already exists. Re-run with --force to overwrite.',
            },
        )

    profiles_path.parent.mkdir(parents=True, exist_ok=True)
    profiles = _default_profiles(with_defaults=with_defaults)
    _write_profiles(profiles_path, profiles)

    return {
        'command': 'init-agent-profiles',
        'ok': True,
        'local_only': True,
        'path': str(profiles_path),
        'force': force,
        'with_defaults': with_defaults,
        'profiles': profiles,
    }


def register_agent_profile(
    config: AppConfig,
    *,
    agent_id: str,
    name: str,
    role: str,
    profiles_path: str | Path | None = None,
    description: str | None = None,
    execution_mode: str | None = None,
    model_preference: str | None = None,
    strengths: list[str] | None = None,
    constraints: list[str] | None = None,
    allowed_item_types: list[str] | None = None,
    escalation_allowed: bool | None = None,
    handoff_target_id: str | None = None,
    status: str | None = None,
    tags: list[str] | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    if role not in AGENT_ROLES:
        return _error(
            'invalid_agent_role',
            {
                'role': role,
                'supported_roles': list(AGENT_ROLES),
                'message': 'Invalid agent role supplied.',
            },
        )
    if execution_mode is not None and execution_mode not in EXECUTION_MODES:
        return _error(
            'invalid_execution_mode',
            {
                'execution_mode': execution_mode,
                'supported_execution_modes': list(EXECUTION_MODES),
                'message': 'Invalid execution mode supplied.',
            },
        )
    if status is not None and status not in AGENT_PROFILE_STATUSES:
        return _error(
            'invalid_agent_profile_status',
            {
                'status': status,
                'supported_statuses': list(AGENT_PROFILE_STATUSES),
                'message': 'Invalid status supplied.',
            },
        )

    path = resolve_agent_profiles_path(config.repo_root, profiles_path)
    loaded = _load_profiles_required(path)
    if not loaded.get('ok', False):
        return loaded
    profiles = loaded['profiles']

    now = _now_iso()
    normalized_agent_id = agent_id.strip()
    agents = profiles.get('agents', [])
    if not isinstance(agents, list):
        agents = []

    agent = next(
        (
            item
            for item in agents
            if isinstance(item, dict) and str(item.get('agent_id', '')).strip() == normalized_agent_id
        ),
        None,
    )
    created = False
    if agent is None:
        agent = {
            'agent_id': normalized_agent_id,
            'name': '',
            'role': 'other',
            'description': '',
            'execution_mode': 'manual',
            'model_preference': '',
            'strengths': [],
            'constraints': [],
            'allowed_item_types': [],
            'escalation_allowed': False,
            'handoff_target_id': '',
            'status': 'active',
            'tags': [],
            'notes': '',
            'created_at': now,
            'updated_at': now,
        }
        agents.append(agent)
        created = True

    agent['agent_id'] = normalized_agent_id
    agent['name'] = name.strip()
    agent['role'] = role
    if description is not None:
        agent['description'] = description.strip()
    elif created:
        agent['description'] = ''
    if execution_mode is not None:
        agent['execution_mode'] = execution_mode
    elif created:
        agent['execution_mode'] = 'manual'
    if model_preference is not None:
        agent['model_preference'] = model_preference.strip()
    elif created:
        agent['model_preference'] = ''
    if strengths is not None and len(strengths) > 0:
        agent['strengths'] = _normalize_list(strengths)
    elif created:
        agent['strengths'] = []
    if constraints is not None and len(constraints) > 0:
        agent['constraints'] = _normalize_list(constraints)
    elif created:
        agent['constraints'] = []
    if allowed_item_types is not None and len(allowed_item_types) > 0:
        agent['allowed_item_types'] = _normalize_list(allowed_item_types)
    elif created:
        agent['allowed_item_types'] = []
    if escalation_allowed is not None:
        agent['escalation_allowed'] = bool(escalation_allowed)
    elif created:
        agent['escalation_allowed'] = False
    if handoff_target_id is not None:
        agent['handoff_target_id'] = handoff_target_id.strip()
    elif created:
        agent['handoff_target_id'] = ''
    if status is not None:
        agent['status'] = status
    elif created:
        agent['status'] = 'active'
    if tags is not None and len(tags) > 0:
        agent['tags'] = _normalize_list(tags)
    elif created:
        agent['tags'] = []
    if notes is not None:
        agent['notes'] = notes.strip()
    elif created:
        agent['notes'] = ''

    if not agent.get('created_at'):
        agent['created_at'] = now
    agent['updated_at'] = now

    profiles['agents'] = agents
    profiles['updated_at'] = now

    warnings: list[str] = []
    target_value = str(agent.get('handoff_target_id', '')).strip()
    if target_value and not _handoff_target_exists(profiles, target_value):
        warnings.append(
            f"handoff_target_id '{target_value}' was not found in handoff_targets. Profile was saved for future linkage."
        )

    _write_profiles(path, profiles)

    return {
        'command': 'register-agent-profile',
        'ok': True,
        'local_only': True,
        'profiles_path': str(path),
        'created': created,
        'warnings': warnings,
        'agent': _agent_view(agent),
    }


def register_handoff_target(
    config: AppConfig,
    *,
    target_id: str,
    name: str,
    target_type: str,
    profiles_path: str | Path | None = None,
    description: str | None = None,
    local_command: str | None = None,
    input_format: str | None = None,
    output_format: str | None = None,
    safety_notes: list[str] | None = None,
    status: str | None = None,
    tags: list[str] | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    if target_type not in HANDOFF_TARGET_TYPES:
        return _error(
            'invalid_handoff_target_type',
            {
                'target_type': target_type,
                'supported_target_types': list(HANDOFF_TARGET_TYPES),
                'message': 'Invalid handoff target type supplied.',
            },
        )
    if status is not None and status not in AGENT_PROFILE_STATUSES:
        return _error(
            'invalid_agent_profile_status',
            {
                'status': status,
                'supported_statuses': list(AGENT_PROFILE_STATUSES),
                'message': 'Invalid status supplied.',
            },
        )

    path = resolve_agent_profiles_path(config.repo_root, profiles_path)
    loaded = _load_profiles_required(path)
    if not loaded.get('ok', False):
        return loaded
    profiles = loaded['profiles']

    now = _now_iso()
    normalized_target_id = target_id.strip()
    targets = profiles.get('handoff_targets', [])
    if not isinstance(targets, list):
        targets = []

    target = next(
        (
            item
            for item in targets
            if isinstance(item, dict) and str(item.get('target_id', '')).strip() == normalized_target_id
        ),
        None,
    )
    created = False
    if target is None:
        target = {
            'target_id': normalized_target_id,
            'name': '',
            'target_type': 'other',
            'description': '',
            'local_command': '',
            'input_format': '',
            'output_format': '',
            'safety_notes': [],
            'status': 'active',
            'tags': [],
            'notes': '',
            'created_at': now,
            'updated_at': now,
        }
        targets.append(target)
        created = True

    target['target_id'] = normalized_target_id
    target['name'] = name.strip()
    target['target_type'] = target_type
    if description is not None:
        target['description'] = description.strip()
    elif created:
        target['description'] = ''
    if local_command is not None:
        target['local_command'] = local_command.strip()
    elif created:
        target['local_command'] = ''
    if input_format is not None:
        target['input_format'] = input_format.strip()
    elif created:
        target['input_format'] = ''
    if output_format is not None:
        target['output_format'] = output_format.strip()
    elif created:
        target['output_format'] = ''
    if safety_notes is not None and len(safety_notes) > 0:
        target['safety_notes'] = _normalize_list(safety_notes)
    elif created:
        target['safety_notes'] = []
    if status is not None:
        target['status'] = status
    elif created:
        target['status'] = 'active'
    if tags is not None and len(tags) > 0:
        target['tags'] = _normalize_list(tags)
    elif created:
        target['tags'] = []
    if notes is not None:
        target['notes'] = notes.strip()
    elif created:
        target['notes'] = ''

    if not target.get('created_at'):
        target['created_at'] = now
    target['updated_at'] = now

    profiles['handoff_targets'] = targets
    profiles['updated_at'] = now
    _write_profiles(path, profiles)

    return {
        'command': 'register-handoff-target',
        'ok': True,
        'local_only': True,
        'profiles_path': str(path),
        'created': created,
        'handoff_target': _handoff_target_view(target),
    }


def inspect_agent_profiles(
    config: AppConfig,
    *,
    profiles_path: str | Path | None = None,
    role: str | None = None,
    execution_mode: str | None = None,
    status: str | None = None,
    output_format: str = 'json',
) -> dict[str, Any]:
    if role is not None and role not in AGENT_ROLES:
        return _error(
            'invalid_agent_role',
            {
                'role': role,
                'supported_roles': list(AGENT_ROLES),
                'message': 'Invalid agent role supplied.',
            },
        )
    if execution_mode is not None and execution_mode not in EXECUTION_MODES:
        return _error(
            'invalid_execution_mode',
            {
                'execution_mode': execution_mode,
                'supported_execution_modes': list(EXECUTION_MODES),
                'message': 'Invalid execution mode supplied.',
            },
        )
    if status is not None and status not in AGENT_PROFILE_STATUSES:
        return _error(
            'invalid_agent_profile_status',
            {
                'status': status,
                'supported_statuses': list(AGENT_PROFILE_STATUSES),
                'message': 'Invalid status supplied.',
            },
        )

    path = resolve_agent_profiles_path(config.repo_root, profiles_path)
    loaded = _load_profiles_required(path)
    if not loaded.get('ok', False):
        return loaded
    profiles = loaded['profiles']

    agents = [_agent_view(item) for item in profiles.get('agents', []) if isinstance(item, dict)]
    filtered: list[dict[str, Any]] = []
    for item in agents:
        if role is not None and item.get('role') != role:
            continue
        if execution_mode is not None and item.get('execution_mode') != execution_mode:
            continue
        if status is not None and item.get('status') != status:
            continue
        filtered.append(item)

    payload = {
        'profiles_path': str(path),
        'schema_version': profiles.get('schema_version'),
        'updated_at': profiles.get('updated_at'),
        'agent_count': len(filtered),
        'handoff_target_count': len(
            [item for item in profiles.get('handoff_targets', []) if isinstance(item, dict)]
        ),
        'filters': {
            'role': role,
            'execution_mode': execution_mode,
            'status': status,
        },
        'agents': filtered,
    }
    return _stdout_result(
        command='inspect-agent-profiles',
        payload=payload,
        output_format=output_format,
        markdown=_render_agent_profiles_markdown(payload),
    )


def inspect_agent_profile(
    config: AppConfig,
    *,
    agent_id: str,
    profiles_path: str | Path | None = None,
    output_format: str = 'json',
) -> dict[str, Any]:
    path = resolve_agent_profiles_path(config.repo_root, profiles_path)
    loaded = _load_profiles_required(path)
    if not loaded.get('ok', False):
        return loaded
    profiles = loaded['profiles']

    normalized_agent_id = agent_id.strip()
    agent = next(
        (
            item
            for item in profiles.get('agents', [])
            if isinstance(item, dict) and str(item.get('agent_id', '')).strip() == normalized_agent_id
        ),
        None,
    )
    if agent is None:
        return _error(
            'agent_profile_not_found',
            {
                'agent_id': normalized_agent_id,
                'profiles_path': str(path),
                'message': 'Agent profile id was not found in local agent profiles.',
            },
        )

    payload = {
        'profiles_path': str(path),
        'agent': _agent_view(agent),
    }
    return _stdout_result(
        command='inspect-agent-profile',
        payload=payload,
        output_format=output_format,
        markdown=_render_agent_profile_markdown(payload),
    )


def inspect_handoff_target(
    config: AppConfig,
    *,
    target_id: str,
    profiles_path: str | Path | None = None,
    output_format: str = 'json',
) -> dict[str, Any]:
    path = resolve_agent_profiles_path(config.repo_root, profiles_path)
    loaded = _load_profiles_required(path)
    if not loaded.get('ok', False):
        return loaded
    profiles = loaded['profiles']

    normalized_target_id = target_id.strip()
    target = next(
        (
            item
            for item in profiles.get('handoff_targets', [])
            if isinstance(item, dict) and str(item.get('target_id', '')).strip() == normalized_target_id
        ),
        None,
    )
    if target is None:
        return _error(
            'handoff_target_not_found',
            {
                'target_id': normalized_target_id,
                'profiles_path': str(path),
                'message': 'Handoff target id was not found in local agent profiles.',
            },
        )

    payload = {
        'profiles_path': str(path),
        'handoff_target': _handoff_target_view(target),
    }
    return _stdout_result(
        command='inspect-handoff-target',
        payload=payload,
        output_format=output_format,
        markdown=_render_handoff_target_markdown(payload),
    )


def agent_profiles_summary_for_handoff(config: AppConfig) -> dict[str, Any] | None:
    path = resolve_agent_profiles_path(config.repo_root, None)
    if not path.exists():
        return None

    loaded = _load_profiles_required(path)
    if not loaded.get('ok', False):
        return {
            'path': str(path),
            'error': str(loaded.get('error', 'unknown')),
        }

    profiles = loaded['profiles']
    agents = [_agent_view(item) for item in profiles.get('agents', []) if isinstance(item, dict)]
    targets = [
        _handoff_target_view(item) for item in profiles.get('handoff_targets', []) if isinstance(item, dict)
    ]

    status_counts: dict[str, int] = {}
    for value in AGENT_PROFILE_STATUSES:
        status_counts[value] = 0
    for agent in agents:
        status_value = str(agent.get('status', '')).strip()
        if status_value not in status_counts:
            status_counts[status_value] = 0
        status_counts[status_value] += 1

    return {
        'path': str(path),
        'schema_version': profiles.get('schema_version'),
        'updated_at': profiles.get('updated_at'),
        'agent_count': len(agents),
        'handoff_target_count': len(targets),
        'status_counts': status_counts,
        'agents': [
            {
                'agent_id': item.get('agent_id'),
                'name': item.get('name'),
                'role': item.get('role'),
                'execution_mode': item.get('execution_mode'),
                'status': item.get('status'),
                'handoff_target_id': item.get('handoff_target_id'),
            }
            for item in agents
        ],
    }


def resolve_agent_profiles_path(repo_root: Path, path: str | Path | None) -> Path:
    if path is None:
        return (repo_root / AGENTS_DIR_RELATIVE / AGENTS_FILE_NAME).resolve()
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = (repo_root / candidate).resolve()
    if candidate.suffix.lower() == '.json' or candidate.name.endswith('.json'):
        return candidate
    return candidate / AGENTS_FILE_NAME


def _default_profiles(*, with_defaults: bool) -> dict[str, Any]:
    root = {
        'schema_version': AGENT_PROFILES_SCHEMA_VERSION,
        'updated_at': _now_iso(),
        'agents': [],
        'handoff_targets': [],
    }
    if not with_defaults:
        return root

    now = _now_iso()
    root['handoff_targets'] = [
        {
            'target_id': 'human-review',
            'name': 'Human Review Prompt',
            'target_type': 'human_prompt',
            'description': 'Structured prompt packet for human operator review and action.',
            'local_command': '',
            'input_format': 'markdown checklist',
            'output_format': 'approved notes',
            'safety_notes': ['Human confirmation required before any mutation command.'],
            'status': 'active',
            'tags': ['local-first', 'review'],
            'notes': 'Default local handoff target.',
            'created_at': now,
            'updated_at': now,
        },
        {
            'target_id': 'codex-local',
            'name': 'Codex Prompt Packet',
            'target_type': 'codex_prompt',
            'description': 'Prompt packet intended for local Codex-driven implementation sessions.',
            'local_command': '',
            'input_format': 'markdown handoff',
            'output_format': 'patch plan',
            'safety_notes': ['Advisory only. Execution remains human-triggered.'],
            'status': 'active',
            'tags': ['local-first', 'implementation'],
            'notes': 'No automatic execution.',
            'created_at': now,
            'updated_at': now,
        },
        {
            'target_id': 'local-llm-generic',
            'name': 'Local LLM Prompt Packet',
            'target_type': 'local_llm_prompt',
            'description': 'Prompt template for optional future local LLM routing.',
            'local_command': '',
            'input_format': 'markdown prompt',
            'output_format': 'analysis summary',
            'safety_notes': ['No local LLM invocation in M34.'],
            'status': 'planned',
            'tags': ['local-llm', 'planned'],
            'notes': 'Descriptive only in M34.',
            'created_at': now,
            'updated_at': now,
        },
        {
            'target_id': 'cloud-escalation-advisory',
            'name': 'Cloud Escalation Advisory Packet',
            'target_type': 'cloud_llm_prompt',
            'description': 'Escalation packet definition for future cloud escalation planning.',
            'local_command': '',
            'input_format': 'json packet',
            'output_format': 'triage recommendation',
            'safety_notes': ['Advisory only. No cloud calls in M34.'],
            'status': 'planned',
            'tags': ['cloud', 'advisory'],
            'notes': 'Use only as a planning placeholder.',
            'created_at': now,
            'updated_at': now,
        },
    ]

    root['agents'] = [
        {
            'agent_id': 'architect',
            'name': 'Architecture Planner',
            'role': 'architect',
            'description': 'Shapes implementation plans and dependency boundaries.',
            'execution_mode': 'human',
            'model_preference': '',
            'strengths': ['system design', 'risk framing', 'scope decomposition'],
            'constraints': ['no direct mutation without operator approval'],
            'allowed_item_types': ['milestone', 'feature', 'documentation'],
            'escalation_allowed': False,
            'handoff_target_id': 'human-review',
            'status': 'active',
            'tags': ['planning'],
            'notes': '',
            'created_at': now,
            'updated_at': now,
        },
        {
            'agent_id': 'implementer',
            'name': 'Implementation Driver',
            'role': 'implementer',
            'description': 'Owns coding and refactoring tasks under explicit operator guidance.',
            'execution_mode': 'codex',
            'model_preference': '',
            'strengths': ['code changes', 'targeted tests'],
            'constraints': ['must preserve local-only and safety boundaries'],
            'allowed_item_types': ['feature', 'bug', 'task'],
            'escalation_allowed': False,
            'handoff_target_id': 'codex-local',
            'status': 'active',
            'tags': ['delivery'],
            'notes': '',
            'created_at': now,
            'updated_at': now,
        },
        {
            'agent_id': 'tester',
            'name': 'Validation Specialist',
            'role': 'tester',
            'description': 'Designs and runs scoped local validation plans.',
            'execution_mode': 'scripted',
            'model_preference': '',
            'strengths': ['test planning', 'regression detection'],
            'constraints': ['avoid network-dependent validation unless explicitly required'],
            'allowed_item_types': ['validation', 'task', 'bug'],
            'escalation_allowed': False,
            'handoff_target_id': 'human-review',
            'status': 'active',
            'tags': ['quality'],
            'notes': '',
            'created_at': now,
            'updated_at': now,
        },
        {
            'agent_id': 'documentation',
            'name': 'Documentation Reconciler',
            'role': 'documentation',
            'description': 'Keeps source-of-truth docs aligned with delivered behavior.',
            'execution_mode': 'manual',
            'model_preference': '',
            'strengths': ['doc updates', 'command references'],
            'constraints': ['prefer concise, source-backed updates'],
            'allowed_item_types': ['documentation', 'handoff'],
            'escalation_allowed': False,
            'handoff_target_id': 'human-review',
            'status': 'active',
            'tags': ['docs'],
            'notes': '',
            'created_at': now,
            'updated_at': now,
        },
        {
            'agent_id': 'reviewer',
            'name': 'Review Gate',
            'role': 'reviewer',
            'description': 'Performs safety and quality review before approval.',
            'execution_mode': 'human',
            'model_preference': '',
            'strengths': ['risk review', 'checklist enforcement'],
            'constraints': ['cannot approve unknown evidence paths'],
            'allowed_item_types': ['validation', 'handoff', 'documentation'],
            'escalation_allowed': False,
            'handoff_target_id': 'human-review',
            'status': 'active',
            'tags': ['review'],
            'notes': '',
            'created_at': now,
            'updated_at': now,
        },
        {
            'agent_id': 'operator',
            'name': 'Local Operator',
            'role': 'operator',
            'description': 'Coordinates local workflow checkpoints and execution gating.',
            'execution_mode': 'human',
            'model_preference': '',
            'strengths': ['workflow control', 'safety boundaries'],
            'constraints': ['human-triggered actions only'],
            'allowed_item_types': ['milestone', 'orchestration', 'sync'],
            'escalation_allowed': True,
            'handoff_target_id': 'human-review',
            'status': 'active',
            'tags': ['control-plane'],
            'notes': '',
            'created_at': now,
            'updated_at': now,
        },
        {
            'agent_id': 'local-llm-general',
            'name': 'Local LLM Generalist (Advisory)',
            'role': 'local_llm',
            'description': 'Placeholder profile for future local LLM analysis routing.',
            'execution_mode': 'local_llm',
            'model_preference': '',
            'strengths': ['context summarization', 'draft planning'],
            'constraints': ['no local LLM invocation in M34'],
            'allowed_item_types': ['task', 'documentation', 'handoff'],
            'escalation_allowed': False,
            'handoff_target_id': 'local-llm-generic',
            'status': 'planned',
            'tags': ['planned', 'advisory'],
            'notes': 'Configuration only.',
            'created_at': now,
            'updated_at': now,
        },
        {
            'agent_id': 'cloud-escalation',
            'name': 'Cloud Escalation Planner (Advisory)',
            'role': 'cloud_llm',
            'description': 'Placeholder profile to describe potential cloud escalation handoff.',
            'execution_mode': 'cloud_llm',
            'model_preference': '',
            'strengths': ['escalation routing', 'complexity triage'],
            'constraints': ['advisory only; no cloud calls in M34'],
            'allowed_item_types': ['orchestration', 'handoff', 'other'],
            'escalation_allowed': True,
            'handoff_target_id': 'cloud-escalation-advisory',
            'status': 'planned',
            'tags': ['planned', 'cloud', 'advisory'],
            'notes': 'No execution path yet.',
            'created_at': now,
            'updated_at': now,
        },
    ]
    return root


def _load_profiles_required(path: Path) -> dict[str, Any]:
    if not path.exists():
        return _error(
            'agent_profiles_not_found',
            {
                'path': str(path),
                'message': 'Local agent profiles are missing. Run init-agent-profiles first.',
            },
        )
    try:
        raw = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as exc:
        return _error(
            'agent_profiles_invalid_json',
            {
                'path': str(path),
                'message': str(exc),
            },
        )
    if not isinstance(raw, dict):
        return _error(
            'agent_profiles_invalid_schema',
            {
                'path': str(path),
                'message': 'Agent profiles JSON must decode to an object.',
            },
        )

    profiles = {
        'schema_version': str(raw.get('schema_version') or AGENT_PROFILES_SCHEMA_VERSION),
        'updated_at': str(raw.get('updated_at') or _now_iso()),
        'agents': raw.get('agents') if isinstance(raw.get('agents'), list) else [],
        'handoff_targets': raw.get('handoff_targets') if isinstance(raw.get('handoff_targets'), list) else [],
    }
    return {
        'ok': True,
        'profiles': profiles,
    }


def _write_profiles(path: Path, profiles: dict[str, Any]) -> None:
    path.write_text(json.dumps(profiles, indent=2) + '\n', encoding='utf-8')


def _normalize_list(values: list[str]) -> list[str]:
    normalized: list[str] = []
    for value in values:
        item = str(value).strip()
        if item and item not in normalized:
            normalized.append(item)
    return normalized


def _agent_view(agent: dict[str, Any]) -> dict[str, Any]:
    return {
        'agent_id': str(agent.get('agent_id', '')).strip(),
        'name': str(agent.get('name', '')).strip(),
        'role': str(agent.get('role', '')).strip(),
        'description': str(agent.get('description', '')).strip(),
        'execution_mode': str(agent.get('execution_mode', '')).strip(),
        'model_preference': str(agent.get('model_preference', '')).strip(),
        'strengths': _normalize_list(agent.get('strengths', []) if isinstance(agent.get('strengths'), list) else []),
        'constraints': _normalize_list(
            agent.get('constraints', []) if isinstance(agent.get('constraints'), list) else []
        ),
        'allowed_item_types': _normalize_list(
            agent.get('allowed_item_types', []) if isinstance(agent.get('allowed_item_types'), list) else []
        ),
        'escalation_allowed': bool(agent.get('escalation_allowed', False)),
        'handoff_target_id': str(agent.get('handoff_target_id', '')).strip(),
        'status': str(agent.get('status', '')).strip(),
        'tags': _normalize_list(agent.get('tags', []) if isinstance(agent.get('tags'), list) else []),
        'notes': str(agent.get('notes', '')).strip(),
        'created_at': str(agent.get('created_at', '')),
        'updated_at': str(agent.get('updated_at', '')),
    }


def _handoff_target_view(target: dict[str, Any]) -> dict[str, Any]:
    return {
        'target_id': str(target.get('target_id', '')).strip(),
        'name': str(target.get('name', '')).strip(),
        'target_type': str(target.get('target_type', '')).strip(),
        'description': str(target.get('description', '')).strip(),
        'local_command': str(target.get('local_command', '')).strip(),
        'input_format': str(target.get('input_format', '')).strip(),
        'output_format': str(target.get('output_format', '')).strip(),
        'safety_notes': _normalize_list(
            target.get('safety_notes', []) if isinstance(target.get('safety_notes'), list) else []
        ),
        'status': str(target.get('status', '')).strip(),
        'tags': _normalize_list(target.get('tags', []) if isinstance(target.get('tags'), list) else []),
        'notes': str(target.get('notes', '')).strip(),
        'created_at': str(target.get('created_at', '')),
        'updated_at': str(target.get('updated_at', '')),
    }


def _handoff_target_exists(profiles: dict[str, Any], target_id: str) -> bool:
    normalized_target_id = target_id.strip()
    if not normalized_target_id:
        return False
    for target in profiles.get('handoff_targets', []):
        if not isinstance(target, dict):
            continue
        if str(target.get('target_id', '')).strip() == normalized_target_id:
            return True
    return False


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


def _render_agent_profiles_markdown(payload: dict[str, Any]) -> str:
    lines = [
        '# Local Agent Profiles',
        '',
        f"- profiles_path: {payload.get('profiles_path')}",
        f"- schema_version: {payload.get('schema_version')}",
        f"- updated_at: {payload.get('updated_at')}",
        f"- agent_count: {payload.get('agent_count')}",
        f"- handoff_target_count: {payload.get('handoff_target_count')}",
        '',
        '## Agents',
    ]
    agents = payload.get('agents', [])
    if not isinstance(agents, list) or not agents:
        lines.append('- None')
        return '\n'.join(lines)

    for agent in agents:
        if not isinstance(agent, dict):
            continue
        lines.append(
            f"- {agent.get('agent_id')} | {agent.get('name')} | role={agent.get('role')} | mode={agent.get('execution_mode')} | status={agent.get('status')}"
        )
    return '\n'.join(lines)


def _render_agent_profile_markdown(payload: dict[str, Any]) -> str:
    agent = payload.get('agent', {}) if isinstance(payload.get('agent'), dict) else {}
    return '\n'.join(
        [
            '# Local Agent Profile Inspection',
            '',
            f"- profiles_path: {payload.get('profiles_path')}",
            f"- agent_id: {agent.get('agent_id')}",
            f"- name: {agent.get('name')}",
            f"- role: {agent.get('role')}",
            f"- execution_mode: {agent.get('execution_mode')}",
            f"- model_preference: {agent.get('model_preference')}",
            f"- status: {agent.get('status')}",
            f"- handoff_target_id: {agent.get('handoff_target_id')}",
            f"- escalation_allowed: {agent.get('escalation_allowed')}",
            f"- strengths: {', '.join(agent.get('strengths', [])) if isinstance(agent.get('strengths'), list) else ''}",
            f"- constraints: {', '.join(agent.get('constraints', [])) if isinstance(agent.get('constraints'), list) else ''}",
            f"- allowed_item_types: {', '.join(agent.get('allowed_item_types', [])) if isinstance(agent.get('allowed_item_types'), list) else ''}",
            f"- tags: {', '.join(agent.get('tags', [])) if isinstance(agent.get('tags'), list) else ''}",
            f"- notes: {agent.get('notes')}",
            f"- created_at: {agent.get('created_at')}",
            f"- updated_at: {agent.get('updated_at')}",
        ]
    )


def _render_handoff_target_markdown(payload: dict[str, Any]) -> str:
    target = payload.get('handoff_target', {}) if isinstance(payload.get('handoff_target'), dict) else {}
    return '\n'.join(
        [
            '# Local Handoff Target Inspection',
            '',
            f"- profiles_path: {payload.get('profiles_path')}",
            f"- target_id: {target.get('target_id')}",
            f"- name: {target.get('name')}",
            f"- target_type: {target.get('target_type')}",
            f"- status: {target.get('status')}",
            f"- local_command: {target.get('local_command')}",
            f"- input_format: {target.get('input_format')}",
            f"- output_format: {target.get('output_format')}",
            f"- safety_notes: {', '.join(target.get('safety_notes', [])) if isinstance(target.get('safety_notes'), list) else ''}",
            f"- tags: {', '.join(target.get('tags', [])) if isinstance(target.get('tags'), list) else ''}",
            f"- notes: {target.get('notes')}",
            f"- created_at: {target.get('created_at')}",
            f"- updated_at: {target.get('updated_at')}",
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
