from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig

EXECUTION_AUDIT_DIR_RELATIVE = Path('.aresforge')
EXECUTION_AUDIT_FILE_NAME = 'execution_audit_log.json'
EXECUTION_AUDIT_SCHEMA_VERSION = '1.0'

EXECUTION_AUDIT_ACTION_TYPES: tuple[str, ...] = (
    'local_llm_health_check',
    'local_llm_prompt_preview',
    'local_llm_execute',
    'codex_high_value_prompt',
    'prompt_pack_generate',
    'routing_recommendation',
    'routing_metadata_update',
    'blocked_attempt',
)

_SECRET_PATTERN = re.compile(r'(api[_-]?key|token|secret|password|credential|authorization)', re.IGNORECASE)


def resolve_execution_audit_log_path(repo_root: Path, path: str | Path | None = None) -> Path:
    if path is None:
        return (repo_root / EXECUTION_AUDIT_DIR_RELATIVE / EXECUTION_AUDIT_FILE_NAME).resolve()
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate.resolve()
    return (repo_root / candidate).resolve()


def append_execution_audit_entry(
    config: AppConfig,
    *,
    action_type: str,
    outcome: str,
    summary: str,
    source_function: str,
    project_id: str | None = None,
    item_id: str | None = None,
    engine: str | None = None,
    model: str | None = None,
    agent_lane: str | None = None,
    operator_gate_confirmed: bool = False,
    dry_run: bool = False,
    executed: bool = False,
    execution_allowed: bool = False,
    blockers: list[str] | None = None,
    warnings: list[str] | None = None,
    artifact_path: str | Path | None = None,
    audit_path: str | Path | None = None,
    timestamp: str | None = None,
) -> dict[str, Any]:
    normalized_action = str(action_type or '').strip()
    if normalized_action not in EXECUTION_AUDIT_ACTION_TYPES:
        normalized_action = 'blocked_attempt'
    resolved_path = resolve_execution_audit_log_path(config.repo_root, audit_path)
    loaded = _load_audit_file(resolved_path)
    entries = loaded['entries']
    now = str(timestamp or '').strip() or _now_iso()
    entry = _normalize_audit_entry(
        {
            'audit_id': _make_audit_id(now, normalized_action, len(entries) + 1),
            'timestamp': now,
            'project_id': project_id,
            'item_id': item_id,
            'action_type': normalized_action,
            'engine': engine,
            'model': model,
            'agent_lane': agent_lane,
            'operator_gate_confirmed': operator_gate_confirmed,
            'dry_run': dry_run,
            'executed': executed,
            'execution_allowed': execution_allowed,
            'outcome': outcome,
            'blockers': blockers or [],
            'warnings': warnings or [],
            'artifact_path': str(artifact_path or '').strip(),
            'summary': summary,
            'source_function': source_function,
        }
    )
    entries.append(entry)
    payload = {
        'schema_version': EXECUTION_AUDIT_SCHEMA_VERSION,
        'updated_at': now,
        'entries': entries,
    }
    try:
        resolved_path.parent.mkdir(parents=True, exist_ok=True)
        resolved_path.write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')
    except OSError as exc:
        return {
            'ok': False,
            'local_only': True,
            'audit_path': str(resolved_path),
            'entry': entry,
            'warnings': [f'Failed to write execution audit log: {exc}'],
        }
    return {
        'ok': True,
        'local_only': True,
        'audit_path': str(resolved_path),
        'entry': entry,
        'warnings': list(loaded['warnings']),
    }


def read_execution_audit_log(
    config: AppConfig,
    *,
    audit_path: str | Path | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    resolved_path = resolve_execution_audit_log_path(config.repo_root, audit_path)
    loaded = _load_audit_file(resolved_path)
    entries = loaded['entries']
    limited = _apply_limit(entries, limit)
    return {
        'ok': True,
        'local_only': True,
        'generated_at': _now_iso(),
        'audit_path': str(resolved_path),
        'entries': limited,
        'total_entries': len(entries),
        'filters': {},
        'next_safe_action': 'Review local audit entries; audit log is read-only and does not execute anything.',
        'warnings': loaded['warnings'],
        'blockers': [],
    }


def filter_execution_audit_log(
    config: AppConfig,
    *,
    project_id: str | None = None,
    item_id: str | None = None,
    action_type: str | None = None,
    engine: str | None = None,
    executed: bool | None = None,
    outcome: str | None = None,
    limit: int | None = None,
    audit_path: str | Path | None = None,
) -> dict[str, Any]:
    resolved_path = resolve_execution_audit_log_path(config.repo_root, audit_path)
    loaded = _load_audit_file(resolved_path)
    filters = {
        'project_id': str(project_id or '').strip(),
        'item_id': str(item_id or '').strip(),
        'action_type': str(action_type or '').strip(),
        'engine': str(engine or '').strip(),
        'executed': executed,
        'outcome': str(outcome or '').strip(),
        'limit': limit,
    }
    entries = [
        entry for entry in loaded['entries']
        if _audit_entry_matches(entry, filters)
    ]
    return {
        'ok': True,
        'local_only': True,
        'generated_at': _now_iso(),
        'audit_path': str(resolved_path),
        'entries': _apply_limit(entries, limit),
        'total_entries': len(entries),
        'filters': filters,
        'next_safe_action': 'Review local audit entries; audit log is read-only and does not execute anything.',
        'warnings': loaded['warnings'],
        'blockers': [],
    }


def audit_warning(audit_result: dict[str, Any]) -> list[str]:
    if audit_result.get('ok', False):
        return []
    return [str(warning) for warning in audit_result.get('warnings', []) if str(warning).strip()]


def _load_audit_file(path: Path) -> dict[str, Any]:
    warnings: list[str] = []
    if not path.exists():
        return {'entries': [], 'warnings': warnings}
    try:
        raw = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as exc:
        return {'entries': [], 'warnings': [f'Execution audit log could not be parsed: {exc}']}
    if not isinstance(raw, dict):
        return {'entries': [], 'warnings': ['Execution audit log has invalid schema; expected JSON object.']}
    entries_raw = raw.get('entries', [])
    if not isinstance(entries_raw, list):
        return {'entries': [], 'warnings': ['Execution audit log has invalid entries field; expected list.']}
    return {
        'entries': [_normalize_audit_entry(entry) for entry in entries_raw if isinstance(entry, dict)],
        'warnings': warnings,
    }


def _normalize_audit_entry(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        'audit_id': _redact_text(entry.get('audit_id')),
        'timestamp': _redact_text(entry.get('timestamp')),
        'project_id': _redact_text(entry.get('project_id')),
        'item_id': _redact_text(entry.get('item_id')),
        'action_type': _redact_text(entry.get('action_type')),
        'engine': _redact_text(entry.get('engine')),
        'model': _redact_text(entry.get('model')),
        'agent_lane': _redact_text(entry.get('agent_lane')),
        'operator_gate_confirmed': bool(entry.get('operator_gate_confirmed', False)),
        'dry_run': bool(entry.get('dry_run', False)),
        'executed': bool(entry.get('executed', False)),
        'execution_allowed': bool(entry.get('execution_allowed', False)),
        'outcome': _redact_text(entry.get('outcome')),
        'blockers': _redact_list(entry.get('blockers')),
        'warnings': _redact_list(entry.get('warnings')),
        'artifact_path': _redact_text(entry.get('artifact_path')),
        'summary': _redact_text(entry.get('summary')),
        'source_function': _redact_text(entry.get('source_function')),
    }


def _audit_entry_matches(entry: dict[str, Any], filters: dict[str, Any]) -> bool:
    for field in ('project_id', 'item_id', 'action_type', 'engine', 'outcome'):
        value = str(filters.get(field) or '').strip()
        if value and str(entry.get(field, '')).strip() != value:
            return False
    executed = filters.get('executed')
    if executed is not None and bool(entry.get('executed', False)) is not bool(executed):
        return False
    return True


def _apply_limit(entries: list[dict[str, Any]], limit: int | None) -> list[dict[str, Any]]:
    if not isinstance(limit, int) or limit <= 0:
        return list(entries)
    return list(entries[-limit:])


def _make_audit_id(timestamp: str, action_type: str, sequence: int) -> str:
    safe_timestamp = re.sub(r'[^0-9A-Za-z]+', '', timestamp)[:20] or 'unknown'
    safe_action = re.sub(r'[^a-z0-9]+', '-', action_type.lower()).strip('-') or 'event'
    return f'audit-{safe_timestamp}-{safe_action}-{sequence:04d}'


def _redact_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [_redact_text(item) for item in value if str(item).strip()]


def _redact_text(value: Any) -> str:
    text = str(value or '').strip()
    if not text:
        return ''
    if _SECRET_PATTERN.search(text):
        return '[redacted]'
    return text


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()
