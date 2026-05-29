from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.local_ai_artifacts import filter_ai_artifacts
from aresforge.operator.local_execution_audit import filter_execution_audit_log


def read_operator_run_history(
    config: AppConfig,
    *,
    project_id: str | None = None,
    item_id: str | None = None,
    action_type: str | None = None,
    artifact_type: str | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    audit_payload = filter_execution_audit_log(
        config,
        project_id=project_id,
        item_id=item_id,
        action_type=action_type,
        limit=limit,
    )
    artifact_payload = filter_ai_artifacts(
        config,
        project_id=project_id,
        item_id=item_id,
        artifact_type=artifact_type,
        limit=limit,
    )
    audit_entries = audit_payload.get('entries', []) if isinstance(audit_payload.get('entries'), list) else []
    artifacts = artifact_payload.get('artifacts', []) if isinstance(artifact_payload.get('artifacts'), list) else []
    timeline = [_timeline_from_audit(entry) for entry in audit_entries if isinstance(entry, dict)]
    timeline.extend(_timeline_from_artifact(artifact) for artifact in artifacts if isinstance(artifact, dict))
    timeline = sorted(timeline, key=lambda item: str(item.get('timestamp', '')), reverse=True)
    if isinstance(limit, int) and limit > 0:
        timeline = timeline[:limit]
    warnings = [
        *[str(warning) for warning in audit_payload.get('warnings', []) if str(warning).strip()],
        *[str(warning) for warning in artifact_payload.get('warnings', []) if str(warning).strip()],
    ]
    return {
        'ok': True,
        'local_only': True,
        'generated_at': _now_iso(),
        'audit_entries': audit_entries,
        'artifacts': artifacts,
        'timeline': timeline,
        'total_audit_entries': int(audit_payload.get('total_entries', len(audit_entries))),
        'total_artifacts': int(artifact_payload.get('total_artifacts', len(artifacts))),
        'filters': {
            'project_id': str(project_id or '').strip(),
            'item_id': str(item_id or '').strip(),
            'action_type': str(action_type or '').strip(),
            'artifact_type': str(artifact_type or '').strip(),
            'limit': limit,
        },
        'next_safe_action': 'Review operator run history as read-only local evidence; no execution is available from this panel.',
        'warnings': sorted(set(warnings)),
        'blockers': [],
        'boundary_confirmations': [
            'Operator run history is read-only local evidence.',
            'No Codex, local LLM, agent, GitHub, gh, issue, PR, workflow, or external execution is performed.',
        ],
    }


def _timeline_from_audit(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        'timestamp': str(entry.get('timestamp', '')).strip(),
        'kind': 'audit',
        'project_id': str(entry.get('project_id', '')).strip(),
        'item_id': str(entry.get('item_id', '')).strip(),
        'action_type': str(entry.get('action_type', '')).strip(),
        'artifact_type': '',
        'outcome': str(entry.get('outcome', '')).strip(),
        'summary': str(entry.get('summary', '')).strip(),
        'artifact_path': str(entry.get('artifact_path', '')).strip(),
        'executed': bool(entry.get('executed', False)),
        'execution_allowed': bool(entry.get('execution_allowed', False)),
    }


def _timeline_from_artifact(artifact: dict[str, Any]) -> dict[str, Any]:
    return {
        'timestamp': str(artifact.get('created_at', '')).strip(),
        'kind': 'artifact',
        'project_id': str(artifact.get('project_id', '')).strip(),
        'item_id': str(artifact.get('item_id', '')).strip(),
        'action_type': str(artifact.get('source_action', '')).strip(),
        'artifact_type': str(artifact.get('artifact_type', '')).strip(),
        'outcome': 'exists' if artifact.get('exists', False) else 'missing',
        'summary': str(artifact.get('summary', '')).strip(),
        'artifact_path': str(artifact.get('artifact_path', '')).strip(),
        'executed': False,
        'execution_allowed': False,
    }


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()
