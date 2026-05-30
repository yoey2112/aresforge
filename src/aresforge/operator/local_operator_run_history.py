from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.local_ai_artifacts import filter_ai_artifacts
from aresforge.operator.local_ai_action_safety import SAFETY_GATE_ACTION_TYPES
from aresforge.operator.local_execution_audit import filter_execution_audit_log
from aresforge.operator.local_project_queue import inspect_project_queue


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


def read_ai_action_review_panel(
    config: AppConfig,
    *,
    project_id: str | None = None,
    item_id: str | None = None,
    action_type: str | None = None,
    artifact_type: str | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    history = read_operator_run_history(
        config,
        project_id=project_id,
        item_id=item_id,
        action_type=action_type,
        artifact_type=artifact_type,
        limit=limit,
    )
    audit_entries = history.get('audit_entries', []) if isinstance(history.get('audit_entries'), list) else []
    artifacts = history.get('artifacts', []) if isinstance(history.get('artifacts'), list) else []
    timeline = history.get('timeline', []) if isinstance(history.get('timeline'), list) else []
    queue_actions, queue_warnings = _read_queue_ai_actions(
        config,
        project_id=project_id,
        item_id=item_id,
        limit=limit,
    )

    artifact_refs_by_key = _artifact_refs_by_key(artifacts)
    audit_refs_by_key = _audit_refs_by_key(audit_entries)
    action_reviews = [
        _review_from_timeline_entry(
            entry,
            artifact_refs=artifact_refs_by_key.get(_review_key(entry), []),
            audit_refs=audit_refs_by_key.get(_review_key(entry), []),
        )
        for entry in timeline
        if isinstance(entry, dict)
    ]
    blocked_actions = [
        review for review in action_reviews
        if review.get('safety_status') == 'blocked'
        or bool(str(review.get('blocked_reason_category', '')).strip())
        or bool(str(review.get('blocked_reason', '')).strip())
    ]

    warnings = [
        *[str(warning) for warning in history.get('warnings', []) if str(warning).strip()],
        *queue_warnings,
    ]
    return {
        'ok': True,
        'local_only': True,
        'read_only': True,
        'review_only': True,
        'generated_at': _now_iso(),
        'supported_safety_gate_actions': list(SAFETY_GATE_ACTION_TYPES),
        'action_reviews': action_reviews,
        'blocked_actions': blocked_actions,
        'queue_ai_actions': queue_actions,
        'artifact_references': _artifact_references(artifacts),
        'audit_references': _audit_references(audit_entries),
        'run_history_timeline': timeline,
        'counts': {
            'action_review_count': len(action_reviews),
            'blocked_action_count': len(blocked_actions),
            'artifact_reference_count': len(artifacts),
            'audit_reference_count': len(audit_entries),
            'run_history_timeline_count': len(timeline),
            'queue_ai_action_count': len(queue_actions),
        },
        'empty_states': {
            'no_recent_ai_actions': 'No recent AI actions found in local audit, artifact, or run-history data.',
            'no_artifacts_found': 'No AI artifacts found for the current filters.',
            'no_blocked_actions_found': 'No blocked AI-adjacent actions found for the current filters.',
            'no_audit_entries_found': 'No execution audit entries found for the current filters.',
        },
        'filters': dict(history.get('filters', {})),
        'next_safe_action': 'Review local AI action metadata only; use existing explicit operator-gated controls for any future action.',
        'warnings': sorted(set(warnings)),
        'blockers': [],
        'boundary_confirmations': [
            'AI Action Review Panel is read-only local review evidence.',
            'No execution controls are exposed by this review payload.',
            'No Codex, local LLM, agent, GitHub, gh, issue, PR, workflow, or external execution is performed.',
            'No repository mutation is performed from AI output.',
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
        'safety_status': str(entry.get('safety_status', '')).strip(),
        'gate_status': str(entry.get('gate_status', '')).strip(),
        'blocked_reason_category': str(entry.get('blocked_reason_category', '')).strip(),
        'summary': str(entry.get('summary', '')).strip(),
        'artifact_path': str(entry.get('artifact_path', '')).strip(),
        'executed': bool(entry.get('executed', False)),
        'execution_allowed': bool(entry.get('execution_allowed', False)),
        'repo_mutation_allowed': False,
        'external_mutation_allowed': False,
        'automatic_execution_allowed': False,
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
        'safety_status': str(artifact.get('safety_status', 'advisory_artifact')).strip() or 'advisory_artifact',
        'gate_status': str(artifact.get('gate_status', 'artifact_only')).strip() or 'artifact_only',
        'blocked_reason_category': '',
        'summary': str(artifact.get('summary', '')).strip(),
        'artifact_path': str(artifact.get('artifact_path', '')).strip(),
        'executed': False,
        'execution_allowed': False,
        'repo_mutation_allowed': False,
        'external_mutation_allowed': False,
        'automatic_execution_allowed': False,
    }


def _read_queue_ai_actions(
    config: AppConfig,
    *,
    project_id: str | None,
    item_id: str | None,
    limit: int | None,
) -> tuple[list[dict[str, Any]], list[str]]:
    result = inspect_project_queue(config, project_id=project_id, output_format='json')
    warnings: list[str] = []
    if not result.get('ok', False):
        details = result.get('details', {}) if isinstance(result.get('details'), dict) else {}
        message = str(details.get('message') or result.get('error') or 'Local queue was not available for review.')
        return [], [message]
    payload = result.get('payload', {}) if isinstance(result.get('payload'), dict) else {}
    items = payload.get('work_items', []) if isinstance(payload.get('work_items'), list) else []
    queue_actions: list[dict[str, Any]] = []
    normalized_item_id = str(item_id or '').strip()
    for item in items:
        if not isinstance(item, dict):
            continue
        if normalized_item_id and str(item.get('item_id', '')).strip() != normalized_item_id:
            continue
        metadata = item.get('routing_metadata', {}) if isinstance(item.get('routing_metadata'), dict) else {}
        if not _is_ai_adjacent_queue_item(metadata):
            continue
        queue_actions.append(
            {
                'item_id': str(item.get('item_id', '')).strip(),
                'project_id': str(item.get('project_id', '')).strip(),
                'title': str(item.get('title', '')).strip(),
                'status': str(item.get('status', '')).strip(),
                'action_name': str(metadata.get('recommended_engine') or metadata.get('recommended_agent_lane') or 'queue_routing_metadata').strip(),
                'safety_status': 'advisory_queue_metadata',
                'gate_status': 'operator_review_only',
                'blocked_action': str(item.get('title', '')).strip() if str(item.get('status', '')).strip() == 'blocked' else '',
                'blocked_reason_category': 'queue_blocked' if str(item.get('status', '')).strip() == 'blocked' else '',
                'blocked_reason': ', '.join(_as_list(item.get('blocked_by'))),
                'recommended_engine': str(metadata.get('recommended_engine', '')).strip(),
                'recommended_model': str(metadata.get('recommended_model', '')).strip(),
                'recommended_agent_lane': str(metadata.get('recommended_agent_lane', '')).strip(),
                'risk_level': str(metadata.get('risk_level', '')).strip(),
                'complexity_level': str(metadata.get('complexity_level', '')).strip(),
                'project_ai_mode': str(metadata.get('project_ai_mode', '')).strip(),
                'no_automatic_execution_flag': True,
                'no_repo_mutation_flag': True,
                'next_safe_operator_action': 'Review routing metadata; use existing explicit operator-gated workflows only.',
            }
        )
    if isinstance(limit, int) and limit > 0:
        queue_actions = queue_actions[:limit]
    return queue_actions, warnings


def _is_ai_adjacent_queue_item(metadata: dict[str, Any]) -> bool:
    return any(
        str(metadata.get(field, '')).strip()
        for field in (
            'recommended_agent_lane',
            'recommended_engine',
            'recommended_model',
            'fallback_engine',
            'fallback_model',
            'project_ai_mode',
            'routing_policy_source',
        )
    )


def _review_from_timeline_entry(
    entry: dict[str, Any],
    *,
    artifact_refs: list[dict[str, str]],
    audit_refs: list[dict[str, str]],
) -> dict[str, Any]:
    action_name = str(entry.get('action_type') or entry.get('artifact_type') or entry.get('kind') or '').strip()
    blocked_category = str(entry.get('blocked_reason_category', '')).strip()
    safety_status = str(entry.get('safety_status', '')).strip()
    return {
        'timestamp': str(entry.get('timestamp', '')).strip(),
        'kind': str(entry.get('kind', '')).strip(),
        'project_id': str(entry.get('project_id', '')).strip(),
        'item_id': str(entry.get('item_id', '')).strip(),
        'action_name': action_name,
        'safety_status': safety_status,
        'gate_status': str(entry.get('gate_status', '')).strip(),
        'blocked_action': action_name if safety_status == 'blocked' or blocked_category else '',
        'blocked_reason_category': blocked_category,
        'blocked_reason': str(entry.get('summary', '')).strip() if safety_status == 'blocked' or blocked_category else '',
        'no_automatic_execution_flag': not bool(entry.get('automatic_execution_allowed', False)),
        'no_repo_mutation_flag': not bool(entry.get('repo_mutation_allowed', False)),
        'artifact_references': artifact_refs,
        'audit_references': audit_refs,
        'run_history_timeline_entries': [entry],
        'next_safe_operator_action': 'Review this local evidence entry; no execution is available from the review panel.',
    }


def _artifact_references(artifacts: list[dict[str, Any]]) -> list[dict[str, str]]:
    return [
        {
            'artifact_id': str(artifact.get('artifact_id', '')).strip(),
            'artifact_type': str(artifact.get('artifact_type', '')).strip(),
            'artifact_path': str(artifact.get('artifact_path', '')).strip(),
            'source_action': str(artifact.get('source_action', '')).strip(),
            'item_id': str(artifact.get('item_id', '')).strip(),
        }
        for artifact in artifacts
        if isinstance(artifact, dict)
    ]


def _audit_references(entries: list[dict[str, Any]]) -> list[dict[str, str]]:
    return [
        {
            'audit_id': str(entry.get('audit_id', '')).strip(),
            'action_type': str(entry.get('action_type', '')).strip(),
            'outcome': str(entry.get('outcome', '')).strip(),
            'item_id': str(entry.get('item_id', '')).strip(),
        }
        for entry in entries
        if isinstance(entry, dict)
    ]


def _artifact_refs_by_key(artifacts: list[dict[str, Any]]) -> dict[tuple[str, str], list[dict[str, str]]]:
    refs: dict[tuple[str, str], list[dict[str, str]]] = {}
    for ref in _artifact_references(artifacts):
        refs.setdefault((ref.get('item_id', ''), ref.get('source_action', '')), []).append(ref)
    return refs


def _audit_refs_by_key(entries: list[dict[str, Any]]) -> dict[tuple[str, str], list[dict[str, str]]]:
    refs: dict[tuple[str, str], list[dict[str, str]]] = {}
    for ref in _audit_references(entries):
        refs.setdefault((ref.get('item_id', ''), ref.get('action_type', '')), []).append(ref)
    return refs


def _review_key(entry: dict[str, Any]) -> tuple[str, str]:
    return (
        str(entry.get('item_id', '')).strip(),
        str(entry.get('action_type', '')).strip(),
    )


def _as_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()
