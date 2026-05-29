from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig

AI_ARTIFACT_REGISTRY_DIR_RELATIVE = Path('.aresforge')
AI_ARTIFACT_REGISTRY_FILE_NAME = 'ai_artifact_registry.json'
AI_ARTIFACT_REGISTRY_SCHEMA_VERSION = '1.0'

AI_ARTIFACT_TYPES: tuple[str, ...] = (
    'prompt_pack',
    'handoff',
    'local_llm_prompt_preview',
    'local_llm_execution_result',
    'codex_high_value_prompt',
    'report',
    'audit_export',
    'other',
)

_SECRET_PATTERN = re.compile(r'(api[_-]?key|token|secret|password|credential|authorization)', re.IGNORECASE)


def resolve_ai_artifact_registry_path(repo_root: Path, path: str | Path | None = None) -> Path:
    if path is None:
        return (repo_root / AI_ARTIFACT_REGISTRY_DIR_RELATIVE / AI_ARTIFACT_REGISTRY_FILE_NAME).resolve()
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate.resolve()
    return (repo_root / candidate).resolve()


def register_ai_artifact(
    config: AppConfig,
    *,
    artifact_type: str,
    artifact_path: str | Path,
    source_action: str,
    summary: str,
    project_id: str | None = None,
    item_id: str | None = None,
    engine: str | None = None,
    model: str | None = None,
    agent_lane: str | None = None,
    warnings: list[str] | None = None,
    registry_path: str | Path | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    normalized_type = str(artifact_type or '').strip()
    if normalized_type not in AI_ARTIFACT_TYPES:
        normalized_type = 'other'
    resolved_registry_path = resolve_ai_artifact_registry_path(config.repo_root, registry_path)
    loaded = _load_registry_file(config.repo_root, resolved_registry_path)
    artifacts = loaded['artifacts']
    now = str(created_at or '').strip() or _now_iso()
    normalized_path = _resolve_artifact_path(config.repo_root, artifact_path)
    entry = _normalize_artifact(
        config.repo_root,
        {
            'artifact_id': _make_artifact_id(now, normalized_type, len(artifacts) + 1),
            'created_at': now,
            'project_id': project_id,
            'item_id': item_id,
            'artifact_type': normalized_type,
            'artifact_path': str(normalized_path),
            'source_action': source_action,
            'engine': engine,
            'model': model,
            'agent_lane': agent_lane,
            'summary': summary,
            'checksum': _checksum_file(normalized_path),
            'exists': normalized_path.exists(),
            'warnings': warnings or [],
        },
    )
    artifacts.append(entry)
    payload = {
        'schema_version': AI_ARTIFACT_REGISTRY_SCHEMA_VERSION,
        'updated_at': now,
        'artifacts': artifacts,
    }
    try:
        resolved_registry_path.parent.mkdir(parents=True, exist_ok=True)
        resolved_registry_path.write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')
    except OSError as exc:
        return {
            'ok': False,
            'local_only': True,
            'registry_path': str(resolved_registry_path),
            'artifact': entry,
            'warnings': [f'Failed to write AI artifact registry: {exc}'],
        }
    return {
        'ok': True,
        'local_only': True,
        'registry_path': str(resolved_registry_path),
        'artifact': entry,
        'warnings': list(loaded['warnings']),
    }


def read_ai_artifact_registry(
    config: AppConfig,
    *,
    registry_path: str | Path | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    resolved_path = resolve_ai_artifact_registry_path(config.repo_root, registry_path)
    loaded = _load_registry_file(config.repo_root, resolved_path)
    artifacts = loaded['artifacts']
    return {
        'ok': True,
        'local_only': True,
        'generated_at': _now_iso(),
        'registry_path': str(resolved_path),
        'artifacts': _apply_limit(artifacts, limit),
        'total_artifacts': len(artifacts),
        'filters': {},
        'next_safe_action': 'Review local artifact records; registry reads do not execute anything.',
        'warnings': loaded['warnings'],
        'blockers': [],
    }


def filter_ai_artifacts(
    config: AppConfig,
    *,
    project_id: str | None = None,
    item_id: str | None = None,
    artifact_type: str | None = None,
    source_action: str | None = None,
    engine: str | None = None,
    exists: bool | None = None,
    limit: int | None = None,
    registry_path: str | Path | None = None,
) -> dict[str, Any]:
    resolved_path = resolve_ai_artifact_registry_path(config.repo_root, registry_path)
    loaded = _load_registry_file(config.repo_root, resolved_path)
    filters = {
        'project_id': str(project_id or '').strip(),
        'item_id': str(item_id or '').strip(),
        'artifact_type': str(artifact_type or '').strip(),
        'source_action': str(source_action or '').strip(),
        'engine': str(engine or '').strip(),
        'exists': exists,
        'limit': limit,
    }
    artifacts = [
        artifact for artifact in loaded['artifacts']
        if _artifact_matches(artifact, filters)
    ]
    return {
        'ok': True,
        'local_only': True,
        'generated_at': _now_iso(),
        'registry_path': str(resolved_path),
        'artifacts': _apply_limit(artifacts, limit),
        'total_artifacts': len(artifacts),
        'filters': filters,
        'next_safe_action': 'Review local artifact records; registry reads do not execute anything.',
        'warnings': loaded['warnings'],
        'blockers': [],
    }


def verify_ai_artifact_exists(config: AppConfig, artifact_path: str | Path) -> dict[str, Any]:
    resolved_path = _resolve_artifact_path(config.repo_root, artifact_path)
    return {
        'ok': True,
        'local_only': True,
        'artifact_path': str(resolved_path),
        'exists': resolved_path.exists(),
        'checksum': _checksum_file(resolved_path),
        'warnings': [] if resolved_path.exists() else ['Artifact file does not exist.'],
        'blockers': [],
    }


def artifact_warning(registry_result: dict[str, Any]) -> list[str]:
    if registry_result.get('ok', False):
        return []
    return [str(warning) for warning in registry_result.get('warnings', []) if str(warning).strip()]


def _load_registry_file(repo_root: Path, path: Path) -> dict[str, Any]:
    if not path.exists():
        return {'artifacts': [], 'warnings': []}
    try:
        raw = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as exc:
        return {'artifacts': [], 'warnings': [f'AI artifact registry could not be parsed: {exc}']}
    if not isinstance(raw, dict):
        return {'artifacts': [], 'warnings': ['AI artifact registry has invalid schema; expected JSON object.']}
    artifacts_raw = raw.get('artifacts', [])
    if not isinstance(artifacts_raw, list):
        return {'artifacts': [], 'warnings': ['AI artifact registry has invalid artifacts field; expected list.']}
    return {
        'artifacts': [_normalize_artifact(repo_root, artifact) for artifact in artifacts_raw if isinstance(artifact, dict)],
        'warnings': [],
    }


def _normalize_artifact(repo_root: Path, artifact: dict[str, Any]) -> dict[str, Any]:
    path_text = _redact_text(artifact.get('artifact_path'))
    resolved_path = _resolve_artifact_path(repo_root, path_text) if path_text else Path()
    exists = resolved_path.exists() if path_text else bool(artifact.get('exists', False))
    checksum = _checksum_file(resolved_path) if path_text and exists else _redact_text(artifact.get('checksum'))
    artifact_type = _redact_text(artifact.get('artifact_type')) or 'other'
    if artifact_type not in AI_ARTIFACT_TYPES:
        artifact_type = 'other'
    return {
        'artifact_id': _redact_text(artifact.get('artifact_id')),
        'created_at': _redact_text(artifact.get('created_at')),
        'project_id': _redact_text(artifact.get('project_id')),
        'item_id': _redact_text(artifact.get('item_id')),
        'artifact_type': artifact_type,
        'artifact_path': path_text,
        'source_action': _redact_text(artifact.get('source_action')),
        'engine': _redact_text(artifact.get('engine')),
        'model': _redact_text(artifact.get('model')),
        'agent_lane': _redact_text(artifact.get('agent_lane')),
        'summary': _redact_text(artifact.get('summary')),
        'checksum': checksum,
        'exists': bool(exists),
        'warnings': _redact_list(artifact.get('warnings')),
    }


def _artifact_matches(artifact: dict[str, Any], filters: dict[str, Any]) -> bool:
    for field in ('project_id', 'item_id', 'artifact_type', 'source_action', 'engine'):
        value = str(filters.get(field) or '').strip()
        if value and str(artifact.get(field, '')).strip() != value:
            return False
    exists = filters.get('exists')
    if exists is not None and bool(artifact.get('exists', False)) is not bool(exists):
        return False
    return True


def _apply_limit(artifacts: list[dict[str, Any]], limit: int | None) -> list[dict[str, Any]]:
    if not isinstance(limit, int) or limit <= 0:
        return list(artifacts)
    return list(artifacts[-limit:])


def _resolve_artifact_path(repo_root: Path, artifact_path: str | Path) -> Path:
    candidate = Path(artifact_path)
    if candidate.is_absolute():
        return candidate.resolve()
    return (repo_root / candidate).resolve()


def _checksum_file(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ''
    digest = hashlib.sha256()
    try:
        with path.open('rb') as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b''):
                digest.update(chunk)
    except OSError:
        return ''
    return f'sha256:{digest.hexdigest()}'


def _make_artifact_id(timestamp: str, artifact_type: str, sequence: int) -> str:
    safe_timestamp = re.sub(r'[^0-9A-Za-z]+', '', timestamp)[:20] or 'unknown'
    safe_type = re.sub(r'[^a-z0-9]+', '-', artifact_type.lower()).strip('-') or 'artifact'
    return f'artifact-{safe_timestamp}-{safe_type}-{sequence:04d}'


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
