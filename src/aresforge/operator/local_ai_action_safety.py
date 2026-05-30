from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig

SAFETY_GATE_ACTION_TYPES: tuple[str, ...] = (
    'local_llm_prompt_preview',
    'local_llm_execute',
    'codex_high_value_prompt',
    'prompt_pack_generate',
    'routing_recommendation',
    'routing_metadata_update',
)

_LOCAL_LLM_ENGINES = {'local_reasoning_llm', 'local_coding_llm'}
_PREVIEW_ONLY_ACTIONS = {
    'local_llm_prompt_preview',
    'codex_high_value_prompt',
    'prompt_pack_generate',
    'routing_recommendation',
}

_PROHIBITED_ACTION_TOKENS = (
    'github',
    'github_api',
    'pull_request',
    'pull-request',
    'pull request',
    'pr_create',
    'pr_update',
    'pr_merge',
    'issue',
    'workflow',
    'codex_execute',
    'codex_execution',
    'agent_execute',
    'agent_execution',
    'repo_mutation',
    'apply_llm_output',
)


def evaluate_ai_action_safety_gate(
    config: AppConfig,
    *,
    action_type: str,
    item_id: str | None = None,
    project_id: str | None = None,
    engine: str | None = None,
    model: str | None = None,
    agent_lane: str | None = None,
    risk_level: str | None = None,
    complexity_level: str | None = None,
    project_ai_mode: str | None = None,
    operator_override: bool = False,
    confirm_operator_gate: bool = False,
    dry_run: bool = False,
    queue_path: str | Path | None = None,
) -> dict[str, Any]:
    action = str(action_type or '').strip()
    context = _queue_item_context(config.repo_root, item_id, queue_path)
    item = context.get('item', {}) if isinstance(context.get('item'), dict) else {}
    metadata = item.get('routing_metadata', {}) if isinstance(item.get('routing_metadata'), dict) else {}

    resolved_project_id = str(project_id or item.get('project_id', '')).strip()
    resolved_engine = str(engine or metadata.get('recommended_engine', '')).strip()
    resolved_model = str(model or metadata.get('recommended_model', '')).strip()
    resolved_agent_lane = str(agent_lane or metadata.get('recommended_agent_lane', '')).strip()
    resolved_risk = str(risk_level or metadata.get('risk_level', 'unknown')).strip() or 'unknown'
    resolved_complexity = str(complexity_level or metadata.get('complexity_level', 'unknown')).strip() or 'unknown'
    resolved_project_ai_mode = str(project_ai_mode or metadata.get('project_ai_mode', '')).strip()

    blockers: list[str] = list(context.get('blockers', []))
    warnings: list[str] = list(context.get('warnings', []))
    requires_operator_gate = action in {'local_llm_execute', 'routing_metadata_update'}
    requires_operator_override = False
    override_allowed = True
    execution_allowed = False

    if _is_prohibited_external_or_automatic_action(action):
        blockers.append('GitHub/gh mutation and Codex execution actions are blocked; they are not implemented by AresForge.')
    elif action not in SAFETY_GATE_ACTION_TYPES:
        blockers.append(f'Unsupported AI action type: {action or "(empty)"}.')

    if action in _PREVIEW_ONLY_ACTIONS:
        execution_allowed = False
        if item_id and not item:
            blockers.append('Queue item was not found for preview-only safety gate evaluation.')
        if action == 'local_llm_prompt_preview' and resolved_engine == 'codex_cli':
            blockers.append('codex_cli-routed items cannot use the local LLM prompt preview path.')
        if action == 'local_llm_prompt_preview' and resolved_engine and resolved_engine not in _LOCAL_LLM_ENGINES:
            blockers.append('Local LLM prompt preview requires local_reasoning_llm or local_coding_llm routing.')
    elif action == 'local_llm_execute':
        if not confirm_operator_gate and not dry_run:
            blockers.append('Local LLM execution requires confirm_operator_gate=true for real execution.')
        if resolved_engine == 'codex_cli':
            blockers.append('codex_cli-routed items cannot execute through the local LLM path.')
        elif resolved_engine not in _LOCAL_LLM_ENGINES:
            blockers.append('Local LLM execution requires local_reasoning_llm or local_coding_llm routing.')
        if resolved_risk in {'high', 'critical'} and not operator_override:
            requires_operator_override = True
            blockers.append('High or critical risk local LLM execution requires operator_override=true.')
        if resolved_project_ai_mode == 'manual_only' and not operator_override:
            requires_operator_override = True
            blockers.append('manual_only project mode blocks execution unless operator override is provided.')
        if resolved_project_ai_mode == 'codex_only' and not operator_override:
            requires_operator_override = True
            blockers.append('codex_only project mode blocks local LLM execution unless operator override is provided.')
        execution_allowed = not blockers and not dry_run
    elif action == 'routing_metadata_update':
        if not confirm_operator_gate:
            blockers.append('Routing metadata updates require an explicit operator action confirmation.')
        execution_allowed = False

    if action in _PREVIEW_ONLY_ACTIONS and not blockers:
        decision = 'preview_only'
        allowed = True
    elif blockers:
        if requires_operator_gate and not confirm_operator_gate and not dry_run:
            decision = 'requires_operator_gate'
        elif requires_operator_override:
            decision = 'requires_operator_override'
        else:
            decision = 'blocked'
        allowed = False
    elif warnings:
        decision = 'warning'
        allowed = True
    else:
        decision = 'allowed'
        allowed = True

    if action == 'routing_metadata_update' and allowed:
        decision = 'allowed'
    if action == 'local_llm_execute' and dry_run and allowed:
        decision = 'preview_only'

    blocked_category = _blocked_reason_category(
        action=action,
        blockers=blockers,
        requires_operator_gate=requires_operator_gate,
        confirm_operator_gate=confirm_operator_gate,
        dry_run=dry_run,
        requires_operator_override=requires_operator_override,
    )
    safety_status = 'allowed' if allowed else 'blocked'
    gate_status = _gate_status(
        decision=decision,
        requires_operator_gate=requires_operator_gate,
        confirm_operator_gate=confirm_operator_gate,
        dry_run=dry_run,
    )

    return {
        'ok': True,
        'local_only': True,
        'generated_at': _now_iso(),
        'action_type': action,
        'blocked_action': action if blockers else '',
        'project_id': resolved_project_id,
        'item_id': str(item_id or '').strip(),
        'engine': resolved_engine,
        'model': resolved_model,
        'agent_lane': resolved_agent_lane,
        'risk_level': resolved_risk,
        'complexity_level': resolved_complexity,
        'project_ai_mode': resolved_project_ai_mode,
        'allowed': allowed,
        'requires_operator_gate': requires_operator_gate,
        'operator_gate_confirmed': bool(confirm_operator_gate),
        'requires_operator_override': requires_operator_override,
        'override_allowed': override_allowed,
        'execution_allowed': bool(execution_allowed),
        'decision': decision,
        'safety_status': safety_status,
        'gate_status': gate_status,
        'blocked_reason_category': blocked_category,
        'operator_next_safe_action': _safety_gate_next_safe_action(decision),
        'repo_mutation_allowed': False,
        'external_mutation_allowed': False,
        'automatic_execution_allowed': False,
        'advisory_only': action in _PREVIEW_ONLY_ACTIONS or action == 'local_llm_execute',
        'blockers': sorted(set(blockers)),
        'warnings': sorted(set(warnings)),
        'next_safe_action': _safety_gate_next_safe_action(decision),
        'boundary_confirmations': [
            'AI action safety gate is local-only decision/reporting logic.',
            'No Codex, local LLM, agent, GitHub, gh, issue, PR, workflow, or external execution is performed.',
        ],
    }


def _queue_item_context(repo_root: Path, item_id: str | None, queue_path: str | Path | None) -> dict[str, Any]:
    normalized_item_id = str(item_id or '').strip()
    if not normalized_item_id:
        return {'item': {}, 'warnings': [], 'blockers': []}
    path = _resolve_queue_path(repo_root, queue_path)
    if not path.exists():
        return {'item': {}, 'warnings': [], 'blockers': ['Local queue file was not found for safety gate item lookup.']}
    try:
        raw = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as exc:
        return {'item': {}, 'warnings': [], 'blockers': [f'Local queue file could not be read for safety gate item lookup: {exc}']}
    items = raw.get('work_items', []) if isinstance(raw, dict) else []
    if not isinstance(items, list):
        return {'item': {}, 'warnings': [], 'blockers': ['Local queue file has invalid work_items field for safety gate lookup.']}
    item = next(
        (
            candidate for candidate in items
            if isinstance(candidate, dict) and str(candidate.get('item_id', '')).strip() == normalized_item_id
        ),
        {},
    )
    return {'item': item, 'warnings': [], 'blockers': []}


def _resolve_queue_path(repo_root: Path, queue_path: str | Path | None) -> Path:
    if queue_path is None:
        return (repo_root / '.aresforge' / 'queue' / 'work_items.json').resolve()
    candidate = Path(queue_path)
    if not candidate.is_absolute():
        candidate = (repo_root / candidate).resolve()
    if candidate.suffix.lower() == '.json' or candidate.name.endswith('.json'):
        return candidate
    return candidate / 'work_items.json'


def _is_prohibited_external_or_automatic_action(action: str) -> bool:
    lowered = action.lower()
    if lowered == 'gh' or lowered.startswith(('gh_', 'gh-', 'pr_', 'pr-')):
        return True
    return any(token in lowered for token in _PROHIBITED_ACTION_TOKENS)


def _blocked_reason_category(
    *,
    action: str,
    blockers: list[str],
    requires_operator_gate: bool,
    confirm_operator_gate: bool,
    dry_run: bool,
    requires_operator_override: bool,
) -> str:
    if not blockers:
        return ''
    lowered_action = action.lower()
    lowered_blockers = ' '.join(blockers).lower()
    if _is_prohibited_external_or_automatic_action(lowered_action):
        return 'policy_blocked'
    if requires_operator_gate and not confirm_operator_gate and not dry_run:
        return 'missing_operator_approval'
    if requires_operator_override:
        return 'gate_blocked'
    if any(token in lowered_blockers for token in ('github', 'gh ', 'codex execution', 'agent execution', 'workflow')):
        return 'policy_blocked'
    if any(token in lowered_blockers for token in ('requires', 'must be', 'cannot', 'blocks', 'blocked')):
        return 'gate_blocked'
    return 'invalid_state'


def _gate_status(
    *,
    decision: str,
    requires_operator_gate: bool,
    confirm_operator_gate: bool,
    dry_run: bool,
) -> str:
    if decision == 'preview_only':
        return 'preview_only'
    if decision == 'requires_operator_override':
        return 'requires_operator_override'
    if requires_operator_gate and not confirm_operator_gate and not dry_run:
        return 'missing_operator_approval'
    if decision == 'blocked':
        return 'blocked'
    if requires_operator_gate and confirm_operator_gate:
        return 'operator_gate_confirmed'
    return 'not_required'


def _safety_gate_next_safe_action(decision: str) -> str:
    if decision == 'allowed':
        return 'Proceed only through the existing explicit operator-gated workflow.'
    if decision == 'preview_only':
        return 'Review the preview/advisory output; no execution is authorized by this gate.'
    if decision == 'requires_operator_gate':
        return 'Confirm the explicit operator gate before attempting the existing gated workflow.'
    if decision == 'requires_operator_override':
        return 'Provide an explicit operator override only if the operator accepts the risk.'
    if decision == 'warning':
        return 'Review warnings before proceeding through existing local-only controls.'
    return 'Resolve blockers before proceeding.'


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()
