import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.local_ai_action_safety import evaluate_ai_action_safety_gate
from aresforge.operator.local_ai_artifacts import (
    filter_ai_artifacts,
    read_ai_artifact_registry,
    register_ai_artifact,
)
from aresforge.operator.local_execution_audit import (
    append_execution_audit_entry,
    filter_execution_audit_log,
    read_execution_audit_log,
)
from aresforge.operator.local_operator_run_history import read_operator_run_history
from aresforge.operator.local_active_project import set_active_project
from aresforge.operator.local_project_queue import (
    add_local_queue_item,
    add_queue_item,
    capture_local_queue_completion_evidence,
    close_local_queue_item,
    complete_local_queue_item,
    execute_local_llm_for_queue_item,
    generate_codex_high_value_lane_prompt,
    generate_local_llm_prompt_preview,
    generate_local_queue_item_codex_prompt,
    generate_local_queue_prompt_pack,
    init_project_queue,
    inspect_local_queue_item_readiness,
    inspect_project_queue,
    inspect_queue_item,
    read_local_project_progress_rollup,
    read_local_routed_queue_views,
    resolve_project_queue_path,
    start_local_queue_item,
    update_local_queue_item_routing_metadata,
    update_queue_item,
    validate_queue_routing_metadata,
)
from aresforge.operator.managed_project_registry_local import (
    init_managed_project_registry,
    register_managed_project,
    register_managed_repo,
)


def _config(tmp_path: Path) -> AppConfig:
    artifact_root = tmp_path / 'artifacts'
    return AppConfig(
        repo_root=tmp_path,
        db_host='127.0.0.1',
        db_port=5433,
        db_name='aresforge',
        db_user='aresforge',
        db_password='aresforge',
        ollama_base_url='http://127.0.0.1:11434',
        ollama_model='qwen2.5:32b',
        artifact_root=artifact_root,
        prompts_dir=artifact_root / 'prompts' / 'generated',
        evidence_dir=artifact_root / 'evidence' / 'generated',
        codex_handoffs_dir=artifact_root / 'codex_handoffs' / 'generated',
        github_owner='local',
        github_repo='aresforge',
    )


def _write_local_llm_environment(repo_root: Path, *, reasoning_model: str = 'local-reason', coding_model: str = 'local-code', execution_enabled: bool = False) -> Path:
    path = repo_root / '.aresforge' / 'local_llm_environment.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                'schema_version': '1.0',
                'local_llm_provider': 'ollama',
                'provider_base_url': 'http://127.0.0.1:11434',
                'reasoning_model': reasoning_model,
                'coding_model': coding_model,
                'fallback_model': '',
                'health_check_enabled': False,
                'execution_enabled': execution_enabled,
                'operator_gate_required': True,
                'notes': '',
                'updated_at': '',
            },
            indent=2,
        )
        + '\n',
        encoding='utf-8',
    )
    return path


def _seed_preview_item(config: AppConfig, *, item_id: str, engine: str, model: str = '') -> None:
    assert init_project_queue(config)['ok'] is True
    assert add_queue_item(
        config,
        item_id=item_id,
        project_id='p1',
        repo_id='r1',
        title='Preview task',
        description='Generate a local LLM prompt preview.',
        status='ready',
        priority='normal',
        item_type='task',
        notes='Acceptance criteria:\n- Preserve local-only boundaries',
    )['ok'] is True
    assert update_local_queue_item_routing_metadata(
        config,
        item_id=item_id,
        routing_metadata={
            'recommended_agent_lane': 'coding',
            'recommended_engine': engine,
            'recommended_model': model,
            'routing_policy_source': 'test',
            'routing_reason': 'Preview route.',
            'risk_level': 'low',
            'complexity_level': 'low',
            'project_ai_mode': 'balanced',
        },
    )['ok'] is True


def test_ai_artifact_registry_reads_empty_registers_and_filters(tmp_path: Path) -> None:
    config = _config(tmp_path)
    artifact_path = tmp_path / 'artifacts' / 'prompt_packs' / 'pack.txt'
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text('local prompt pack\n', encoding='utf-8')

    empty = read_ai_artifact_registry(config)
    registered = register_ai_artifact(
        config,
        artifact_type='prompt_pack',
        artifact_path=artifact_path,
        source_action='prompt_pack_generate',
        project_id='p1',
        item_id='q1',
        engine='prompt_pack',
        summary='Generated prompt pack without secret token details.',
        warnings=['api_key must be redacted'],
        created_at='2026-05-29T00:00:00+00:00',
    )
    by_item = filter_ai_artifacts(config, item_id='q1')
    by_type = filter_ai_artifacts(config, artifact_type='prompt_pack')

    assert empty['ok'] is True
    assert empty['artifacts'] == []
    assert registered['ok'] is True
    assert registered['artifact']['artifact_id'] == 'artifact-20260529T0000000000-prompt-pack-0001'
    assert registered['artifact']['exists'] is True
    assert registered['artifact']['checksum'].startswith('sha256:')
    assert registered['artifact']['summary'] == '[redacted]'
    assert registered['artifact']['warnings'] == ['[redacted]']
    assert by_item['total_artifacts'] == 1
    assert by_type['total_artifacts'] == 1
    assert registered['artifact']['advisory_only'] is True
    assert registered['artifact']['repo_mutation_allowed'] is False
    assert registered['artifact']['external_mutation_allowed'] is False
    assert registered['artifact']['automatic_execution_allowed'] is False
    assert registered['artifact']['safety_status'] == 'advisory_artifact'


def test_ai_artifact_registry_marks_missing_artifact_false(tmp_path: Path) -> None:
    config = _config(tmp_path)
    missing_path = tmp_path / 'artifacts' / 'missing' / 'result.txt'

    registered = register_ai_artifact(
        config,
        artifact_type='local_llm_execution_result',
        artifact_path=missing_path,
        source_action='local_llm_execute',
        item_id='q-missing-artifact',
        summary='Missing artifact record for verification.',
        created_at='2026-05-29T00:00:00+00:00',
    )
    loaded = filter_ai_artifacts(config, exists=False)

    assert registered['ok'] is True
    assert registered['artifact']['exists'] is False
    assert registered['artifact']['checksum'] == ''
    assert loaded['total_artifacts'] == 1
    assert loaded['artifacts'][0]['artifact_path'] == str(missing_path)


def test_operator_run_history_empty_state_and_combined_timeline(tmp_path: Path) -> None:
    config = _config(tmp_path)
    artifact_path = tmp_path / 'artifacts' / 'codex' / 'prompt.txt'
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text('prompt\n', encoding='utf-8')

    empty = read_operator_run_history(config)
    assert append_execution_audit_entry(
        config,
        action_type='codex_high_value_prompt',
        project_id='p1',
        item_id='q-history',
        engine='codex_cli',
        outcome='prompt_generated',
        dry_run=True,
        executed=False,
        execution_allowed=False,
        blockers=[],
        warnings=[],
        summary='Audit entry for run history.',
        source_function='test',
        timestamp='2026-05-29T00:00:01+00:00',
    )['ok'] is True
    assert register_ai_artifact(
        config,
        artifact_type='codex_high_value_prompt',
        artifact_path=artifact_path,
        source_action='codex_high_value_prompt',
        project_id='p1',
        item_id='q-history',
        engine='codex_cli',
        summary='Artifact entry for run history.',
        created_at='2026-05-29T00:00:02+00:00',
    )['ok'] is True

    history = read_operator_run_history(config)

    assert empty['ok'] is True
    assert empty['timeline'] == []
    assert history['total_audit_entries'] == 1
    assert history['total_artifacts'] == 1
    assert [entry['kind'] for entry in history['timeline']] == ['artifact', 'audit']
    assert history['timeline'][0]['timestamp'] == '2026-05-29T00:00:02+00:00'
    assert history['timeline'][0]['artifact_path'] == str(artifact_path)
    assert history['timeline'][1]['outcome'] == 'prompt_generated'


def test_operator_run_history_filters_by_item_and_project(tmp_path: Path) -> None:
    config = _config(tmp_path)
    artifact_path = tmp_path / 'artifacts' / 'prompt_packs' / 'pack.txt'
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text('pack\n', encoding='utf-8')
    assert append_execution_audit_entry(
        config,
        action_type='prompt_pack_generate',
        project_id='p-filter',
        item_id='q-filter',
        engine='prompt_pack',
        outcome='generated',
        summary='Filtered audit entry.',
        source_function='test',
        timestamp='2026-05-29T00:00:01+00:00',
    )['ok'] is True
    assert register_ai_artifact(
        config,
        artifact_type='prompt_pack',
        artifact_path=artifact_path,
        source_action='prompt_pack_generate',
        project_id='p-filter',
        item_id='q-filter',
        engine='prompt_pack',
        summary='Filtered artifact entry.',
        created_at='2026-05-29T00:00:02+00:00',
    )['ok'] is True

    by_item = read_operator_run_history(config, item_id='q-filter')
    by_project = read_operator_run_history(config, project_id='p-filter')
    missing = read_operator_run_history(config, item_id='q-other')

    assert len(by_item['timeline']) == 2
    assert len(by_project['timeline']) == 2
    assert missing['timeline'] == []


def test_execution_audit_log_reads_empty_and_appends_entry(tmp_path: Path) -> None:
    config = _config(tmp_path)

    empty = read_execution_audit_log(config)
    appended = append_execution_audit_entry(
        config,
        action_type='local_llm_prompt_preview',
        project_id='p1',
        item_id='q1',
        engine='local_reasoning_llm',
        model='local-reason',
        agent_lane='reviewer_validator',
        operator_gate_confirmed=False,
        dry_run=True,
        executed=False,
        execution_allowed=False,
        outcome='preview_generated',
        blockers=[],
        warnings=[],
        summary='Prompt preview generated without execution.',
        source_function='test',
        timestamp='2026-05-29T00:00:00+00:00',
    )
    loaded = read_execution_audit_log(config)

    assert empty['ok'] is True
    assert empty['entries'] == []
    assert appended['ok'] is True
    assert appended['entry']['audit_id'] == 'audit-20260529T0000000000-local-llm-prompt-preview-0001'
    assert loaded['total_entries'] == 1
    assert loaded['entries'][0]['action_type'] == 'local_llm_prompt_preview'
    assert loaded['entries'][0]['execution_allowed'] is False
    assert loaded['entries'][0]['safety_status'] == 'allowed'
    assert loaded['entries'][0]['gate_status'] == 'preview_only'
    assert loaded['entries'][0]['repo_mutation_allowed'] is False
    assert loaded['entries'][0]['external_mutation_allowed'] is False
    assert loaded['entries'][0]['automatic_execution_allowed'] is False


def test_execution_audit_log_filters_and_redacts_secret_like_values(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert append_execution_audit_entry(
        config,
        action_type='local_llm_execute',
        item_id='q-sensitive',
        engine='local_coding_llm',
        outcome='blocked',
        blockers=['api_key should never be recorded'],
        warnings=['safe warning'],
        summary='password should not be stored',
        source_function='test',
        timestamp='2026-05-29T00:00:00+00:00',
    )['ok'] is True
    assert append_execution_audit_entry(
        config,
        action_type='codex_high_value_prompt',
        item_id='q-codex',
        engine='codex_cli',
        outcome='prompt_generated',
        summary='Codex prompt generated.',
        source_function='test',
        timestamp='2026-05-29T00:01:00+00:00',
    )['ok'] is True

    by_item = filter_execution_audit_log(config, item_id='q-sensitive')
    by_action = filter_execution_audit_log(config, action_type='codex_high_value_prompt')

    assert by_item['total_entries'] == 1
    assert by_item['entries'][0]['blockers'] == ['[redacted]']
    assert by_item['entries'][0]['summary'] == '[redacted]'
    assert 'api_key' not in json.dumps(by_item)
    assert 'password' not in json.dumps(by_item)
    assert by_action['total_entries'] == 1
    assert by_action['entries'][0]['item_id'] == 'q-codex'


def test_ai_action_safety_gate_local_preview_allowed_as_preview_only(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_preview_item(config, item_id='q-gate-preview', engine='local_coding_llm', model='local-code')

    payload = evaluate_ai_action_safety_gate(
        config,
        action_type='local_llm_prompt_preview',
        item_id='q-gate-preview',
    )

    assert payload['ok'] is True
    assert payload['allowed'] is True
    assert payload['decision'] == 'preview_only'
    assert payload['execution_allowed'] is False
    assert payload['safety_status'] == 'allowed'
    assert payload['gate_status'] == 'preview_only'
    assert payload['blocked_reason_category'] == ''
    assert payload['repo_mutation_allowed'] is False
    assert payload['external_mutation_allowed'] is False
    assert payload['automatic_execution_allowed'] is False


def test_ai_action_safety_gate_local_execute_requires_gate_and_local_routing(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_preview_item(config, item_id='q-gate-execute', engine='local_coding_llm', model='local-code')

    blocked = evaluate_ai_action_safety_gate(
        config,
        action_type='local_llm_execute',
        item_id='q-gate-execute',
        dry_run=False,
    )
    allowed = evaluate_ai_action_safety_gate(
        config,
        action_type='local_llm_execute',
        item_id='q-gate-execute',
        confirm_operator_gate=True,
        dry_run=False,
    )

    assert blocked['allowed'] is False
    assert blocked['decision'] == 'requires_operator_gate'
    assert blocked['safety_status'] == 'blocked'
    assert blocked['gate_status'] == 'missing_operator_approval'
    assert blocked['blocked_reason_category'] == 'missing_operator_approval'
    assert any('confirm_operator_gate' in blocker for blocker in blocked['blockers'])
    assert allowed['allowed'] is True
    assert allowed['decision'] == 'allowed'
    assert allowed['execution_allowed'] is True


def test_ai_action_safety_gate_high_risk_requires_override_and_codex_cli_blocks_local_execute(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_preview_item(config, item_id='q-gate-risk', engine='local_reasoning_llm', model='local-reason')
    assert update_local_queue_item_routing_metadata(
        config,
        item_id='q-gate-risk',
        routing_metadata={
            'recommended_engine': 'local_reasoning_llm',
            'recommended_model': 'local-reason',
            'risk_level': 'high',
            'complexity_level': 'high',
            'project_ai_mode': 'balanced',
        },
    )['ok'] is True
    assert add_queue_item(
        config,
        item_id='q-gate-codex',
        project_id='p1',
        repo_id='r1',
        title='Codex routed task',
        description='Codex-routed task should not execute locally.',
        status='ready',
    )['ok'] is True
    assert update_local_queue_item_routing_metadata(
        config,
        item_id='q-gate-codex',
        routing_metadata={
            'recommended_engine': 'codex_cli',
            'recommended_model': 'gpt-5-codex',
            'risk_level': 'low',
            'complexity_level': 'low',
        },
    )['ok'] is True

    risk_blocked = evaluate_ai_action_safety_gate(
        config,
        action_type='local_llm_execute',
        item_id='q-gate-risk',
        confirm_operator_gate=True,
    )
    risk_allowed = evaluate_ai_action_safety_gate(
        config,
        action_type='local_llm_execute',
        item_id='q-gate-risk',
        confirm_operator_gate=True,
        operator_override=True,
    )
    codex_blocked = evaluate_ai_action_safety_gate(
        config,
        action_type='local_llm_execute',
        item_id='q-gate-codex',
        confirm_operator_gate=True,
    )

    assert risk_blocked['decision'] == 'requires_operator_override'
    assert risk_blocked['requires_operator_override'] is True
    assert risk_allowed['allowed'] is True
    assert codex_blocked['allowed'] is False
    assert any('codex_cli' in blocker for blocker in codex_blocked['blockers'])


def test_ai_action_safety_gate_blocks_codex_execution_and_github_actions(tmp_path: Path) -> None:
    config = _config(tmp_path)

    codex = evaluate_ai_action_safety_gate(config, action_type='codex_execute', engine='codex_cli')
    github = evaluate_ai_action_safety_gate(config, action_type='github_pr_create', engine='github')
    pull_request = evaluate_ai_action_safety_gate(config, action_type='pr_create', engine='github')

    for payload in (codex, github, pull_request):
        assert payload['allowed'] is False
        assert payload['decision'] == 'blocked'
        assert payload['blocked_reason_category'] == 'policy_blocked'
        assert payload['execution_allowed'] is False
        assert payload['repo_mutation_allowed'] is False
        assert payload['external_mutation_allowed'] is False
        assert payload['automatic_execution_allowed'] is False


def test_ai_action_safety_gate_blocks_automatic_agent_and_repo_mutation_paths(tmp_path: Path) -> None:
    config = _config(tmp_path)

    agent = evaluate_ai_action_safety_gate(config, action_type='agent_execute', engine='local_coding_llm')
    repo_mutation = evaluate_ai_action_safety_gate(config, action_type='apply_llm_output_to_repo', engine='local_coding_llm')

    assert agent['allowed'] is False
    assert repo_mutation['allowed'] is False
    assert agent['blocked_reason_category'] == 'policy_blocked'
    assert repo_mutation['blocked_reason_category'] == 'policy_blocked'
    assert agent['automatic_execution_allowed'] is False
    assert repo_mutation['repo_mutation_allowed'] is False


def test_ai_action_safety_gate_routing_metadata_update_requires_explicit_action(tmp_path: Path) -> None:
    config = _config(tmp_path)

    blocked = evaluate_ai_action_safety_gate(config, action_type='routing_metadata_update')
    allowed = evaluate_ai_action_safety_gate(
        config,
        action_type='routing_metadata_update',
        confirm_operator_gate=True,
    )

    assert blocked['allowed'] is False
    assert blocked['decision'] == 'requires_operator_gate'
    assert allowed['allowed'] is True
    assert allowed['decision'] == 'allowed'
    assert allowed['execution_allowed'] is False


def test_blocked_local_llm_execution_does_not_call_provider_or_mutate_repo(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _write_local_llm_environment(tmp_path, execution_enabled=True)
    _seed_preview_item(config, item_id='q-no-auto-llm', engine='local_coding_llm', model='local-code')
    queue_path = tmp_path / '.aresforge' / 'queue' / 'work_items.json'
    before_queue = queue_path.read_text(encoding='utf-8')
    called = {'provider': False}

    def provider_generate_fn(**_: object) -> str:
        called['provider'] = True
        raise AssertionError('provider must not be called without operator gate')

    payload = execute_local_llm_for_queue_item(
        config,
        item_id='q-no-auto-llm',
        confirm_operator_gate=False,
        dry_run=False,
        provider_generate_fn=provider_generate_fn,
    )
    after_queue = queue_path.read_text(encoding='utf-8')
    audit = filter_execution_audit_log(config, item_id='q-no-auto-llm')
    history = read_operator_run_history(config, item_id='q-no-auto-llm')

    assert payload['ok'] is False
    assert payload['executed'] is False
    assert payload['execution_allowed'] is False
    assert payload['advisory_only'] is True
    assert payload['repo_mutation_allowed'] is False
    assert payload['automatic_execution_allowed'] is False
    assert payload['gate_status'] == 'missing_operator_approval'
    assert payload['blocked_reason_category'] == 'missing_operator_approval'
    assert called['provider'] is False
    assert before_queue == after_queue
    assert audit['entries'][-1]['outcome'] == 'blocked'
    assert audit['entries'][-1]['safety_status'] == 'blocked'
    assert history['timeline'][0]['gate_status'] == 'missing_operator_approval'


def test_codex_high_value_lane_is_prompt_handoff_only_and_does_not_mutate_repo(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_preview_item(config, item_id='q-codex-handoff-only', engine='codex_cli', model='gpt-5-codex')
    assert update_local_queue_item_routing_metadata(
        config,
        item_id='q-codex-handoff-only',
        routing_metadata={
            'recommended_agent_lane': 'high_value_codex',
            'recommended_engine': 'codex_cli',
            'recommended_model': 'gpt-5-codex',
            'risk_level': 'high',
            'complexity_level': 'high',
            'project_ai_mode': 'high_confidence',
        },
    )['ok'] is True
    before_queue = (tmp_path / '.aresforge' / 'queue' / 'work_items.json').read_text(encoding='utf-8')

    payload = generate_codex_high_value_lane_prompt(config, item_id='q-codex-handoff-only')
    after_queue = (tmp_path / '.aresforge' / 'queue' / 'work_items.json').read_text(encoding='utf-8')
    audit = filter_execution_audit_log(config, item_id='q-codex-handoff-only')

    assert payload['ok'] is True
    assert payload['execution_allowed'] is False
    assert payload['executed'] is False
    assert payload['advisory_only'] is True
    assert payload['repo_mutation_allowed'] is False
    assert payload['external_mutation_allowed'] is False
    assert payload['automatic_execution_allowed'] is False
    assert 'AresForge must not automatically execute Codex.' in payload['prompt_preview']
    assert before_queue == after_queue
    assert audit['entries'][-1]['action_type'] == 'codex_high_value_prompt'
    assert audit['entries'][-1]['executed'] is False
    assert audit['entries'][-1]['execution_allowed'] is False


def test_codex_high_value_artifact_registry_and_run_history_are_consistent(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_preview_item(config, item_id='q-codex-artifact-consistency', engine='codex_cli', model='gpt-5-codex')
    assert update_local_queue_item_routing_metadata(
        config,
        item_id='q-codex-artifact-consistency',
        routing_metadata={
            'recommended_agent_lane': 'high_value_codex',
            'recommended_engine': 'codex_cli',
            'recommended_model': 'gpt-5-codex',
            'risk_level': 'medium',
            'complexity_level': 'high',
            'project_ai_mode': 'balanced',
        },
    )['ok'] is True
    output = tmp_path / 'artifacts' / 'codex' / 'handoff.txt'

    payload = generate_codex_high_value_lane_prompt(config, item_id='q-codex-artifact-consistency', output=output)
    artifacts = filter_ai_artifacts(config, item_id='q-codex-artifact-consistency')
    history = read_operator_run_history(config, item_id='q-codex-artifact-consistency')

    assert payload['ok'] is True
    assert output.exists()
    assert artifacts['total_artifacts'] == 1
    assert artifacts['artifacts'][0]['artifact_type'] == 'codex_high_value_prompt'
    assert artifacts['artifacts'][0]['safety_status'] == 'allowed'
    assert artifacts['artifacts'][0]['gate_status'] == 'preview_only'
    assert artifacts['artifacts'][0]['advisory_only'] is True
    assert history['timeline'][0]['kind'] == 'artifact'
    assert history['timeline'][0]['item_id'] == 'q-codex-artifact-consistency'
    assert history['timeline'][0]['execution_allowed'] is False


def test_queue_initialization_creates_default_file_and_schema(tmp_path: Path) -> None:
    config = _config(tmp_path)
    payload = init_project_queue(config)
    assert payload['ok'] is True
    queue_path = resolve_project_queue_path(config.repo_root, None)
    assert queue_path.exists()
    rendered = json.loads(queue_path.read_text(encoding='utf-8'))
    assert rendered['schema_version'] == '1.0'
    assert rendered['work_items'] == []


def test_queue_initialization_refuses_overwrite_without_force(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_project_queue(config)['ok'] is True
    second = init_project_queue(config)
    assert second['ok'] is False
    assert second['error'] == 'project_queue_exists'


def test_add_queue_item(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_project_queue(config)['ok'] is True
    payload = add_queue_item(
        config,
        item_id='m33-1',
        project_id='aresforge-main',
        repo_id='core',
        title='Create queue module',
    )
    assert payload['ok'] is True
    assert payload['created'] is True
    assert payload['item']['status'] == 'proposed'
    assert payload['item']['routing_metadata']['risk_level'] == 'unknown'
    assert payload['item']['routing_metadata']['recommended_engine'] == ''


def test_queue_routing_metadata_handles_existing_items_without_metadata(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_project_queue(config)['ok'] is True
    queue_path = resolve_project_queue_path(config.repo_root, None)
    queue = json.loads(queue_path.read_text(encoding='utf-8'))
    queue['work_items'].append(
        {
            'item_id': 'legacy-item',
            'project_id': 'aresforge-main',
            'repo_id': 'core',
            'title': 'Legacy item',
            'status': 'ready',
        }
    )
    queue_path.write_text(json.dumps(queue, indent=2) + '\n', encoding='utf-8')

    payload = inspect_queue_item(config, item_id='legacy-item')
    item = payload['payload']['item']
    assert item['routing_metadata']['risk_level'] == 'unknown'
    assert item['routing_metadata']['complexity_level'] == 'unknown'
    assert item['routing_metadata']['operator_override'] is False


def test_validate_queue_routing_metadata_accepts_empty_and_rejects_invalid_values() -> None:
    empty = validate_queue_routing_metadata({})
    assert empty['valid'] is True
    assert empty['warnings']

    invalid_lane = validate_queue_routing_metadata({'recommended_agent_lane': 'wizard'})
    assert invalid_lane['valid'] is False

    invalid_engine = validate_queue_routing_metadata({'recommended_engine': 'cloud_magic'})
    assert invalid_engine['valid'] is False

    invalid_levels = validate_queue_routing_metadata({'risk_level': 'extreme', 'complexity_level': 'tiny'})
    assert invalid_levels['valid'] is False


def test_update_local_queue_item_routing_metadata_succeeds_for_valid_metadata(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_project_queue(config)['ok'] is True
    assert add_queue_item(
        config,
        item_id='m53-routing',
        project_id='aresforge-main',
        repo_id='core',
        title='Add routing metadata',
    )['ok'] is True

    payload = update_local_queue_item_routing_metadata(
        config,
        item_id='m53-routing',
        routing_metadata={
            'recommended_agent_lane': 'coding',
            'recommended_engine': 'local_coding_llm',
            'recommended_model': 'future-local-code',
            'fallback_engine': 'codex_cli',
            'routing_policy_source': 'project_ai_settings',
            'routing_reason': 'Low-risk coding task placeholder.',
            'risk_level': 'low',
            'complexity_level': 'medium',
            'project_ai_mode': 'balanced',
            'operator_override': False,
        },
    )

    assert payload['ok'] is True
    assert payload['routing_metadata']['recommended_agent_lane'] == 'coding'
    assert payload['routing_metadata']['recommended_engine'] == 'local_coding_llm'
    assert payload['validation']['valid'] is True
    assert payload['item']['status'] == 'proposed'


def test_update_local_queue_item_routing_metadata_rejects_invalid_metadata(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_project_queue(config)['ok'] is True
    assert add_queue_item(
        config,
        item_id='m53-invalid-routing',
        project_id='aresforge-main',
        repo_id='core',
        title='Invalid routing metadata',
    )['ok'] is True

    invalid_lane = update_local_queue_item_routing_metadata(
        config,
        item_id='m53-invalid-routing',
        routing_metadata={'recommended_agent_lane': 'invalid_lane'},
    )
    assert invalid_lane['ok'] is False
    assert invalid_lane['error'] == 'queue_routing_metadata_validation_failed'

    invalid_engine = update_local_queue_item_routing_metadata(
        config,
        item_id='m53-invalid-routing',
        routing_metadata={'recommended_engine': 'invalid_engine'},
    )
    assert invalid_engine['ok'] is False

    invalid_level = update_local_queue_item_routing_metadata(
        config,
        item_id='m53-invalid-routing',
        routing_metadata={'risk_level': 'extreme'},
    )
    assert invalid_level['ok'] is False


def _seed_routed_view_items(config: AppConfig) -> None:
    assert init_project_queue(config)['ok'] is True
    assert add_queue_item(config, item_id='routed-coding', project_id='p1', repo_id='r1', title='Coding routed', status='ready')['ok'] is True
    assert add_queue_item(config, item_id='routed-review', project_id='p1', repo_id='r1', title='Review routed', status='blocked')['ok'] is True
    assert add_queue_item(config, item_id='unrouted-item', project_id='p1', repo_id='r1', title='Unrouted item', status='proposed')['ok'] is True
    assert update_local_queue_item_routing_metadata(
        config,
        item_id='routed-coding',
        routing_metadata={
            'recommended_agent_lane': 'coding',
            'recommended_engine': 'local_coding_llm',
            'recommended_model': 'code-model',
            'risk_level': 'low',
            'complexity_level': 'medium',
            'project_ai_mode': 'balanced',
            'routing_policy_source': 'test_policy',
        },
    )['ok'] is True
    assert update_local_queue_item_routing_metadata(
        config,
        item_id='routed-review',
        routing_metadata={
            'recommended_agent_lane': 'reviewer_validator',
            'recommended_engine': 'local_reasoning_llm',
            'risk_level': 'high',
            'complexity_level': 'high',
            'project_ai_mode': 'high_confidence',
            'routing_policy_source': 'test_policy',
            'operator_override': True,
        },
    )['ok'] is True


def test_routed_queue_views_success_with_mixed_items_and_canonical_queue_read_only(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_routed_view_items(config)
    queue_path = resolve_project_queue_path(config.repo_root, None)
    before = queue_path.read_text(encoding='utf-8')

    payload = read_local_routed_queue_views(config)

    assert payload['ok'] is True
    assert payload['execution_allowed'] is False
    assert payload['total_items'] == 3
    assert payload['routed_items_count'] == 2
    assert payload['unrouted_items_count'] == 1
    assert 'coding' in payload['groups']
    assert 'unrouted' in payload['groups']
    assert queue_path.read_text(encoding='utf-8') == before


def test_routed_queue_views_filters_and_groups(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_routed_view_items(config)

    by_lane = read_local_routed_queue_views(config, recommended_agent_lane='coding', include_unrouted=False)
    assert by_lane['total_items'] == 1
    assert by_lane['items'][0]['item_id'] == 'routed-coding'

    by_engine = read_local_routed_queue_views(config, recommended_engine='local_reasoning_llm', include_unrouted=False)
    assert by_engine['total_items'] == 1
    assert by_engine['items'][0]['item_id'] == 'routed-review'

    by_risk = read_local_routed_queue_views(config, risk_level='high', include_unrouted=False)
    assert by_risk['total_items'] == 1

    by_complexity = read_local_routed_queue_views(config, complexity_level='medium', include_unrouted=False)
    assert by_complexity['items'][0]['item_id'] == 'routed-coding'

    by_override = read_local_routed_queue_views(config, operator_override='present', include_unrouted=False)
    assert by_override['total_items'] == 1
    assert by_override['items'][0]['item_id'] == 'routed-review'

    group_engine = read_local_routed_queue_views(config, group_by='by_engine')
    assert 'local_coding_llm' in group_engine['groups']
    assert 'local_reasoning_llm' in group_engine['groups']

    group_status = read_local_routed_queue_views(config, group_by='by_status')
    assert group_status['groups']['ready']['count'] == 1
    assert group_status['groups']['blocked']['count'] == 1


def test_routed_queue_views_empty_queue_is_stable(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_project_queue(config)['ok'] is True

    payload = read_local_routed_queue_views(config)

    assert payload['ok'] is True
    assert payload['total_items'] == 0
    assert payload['groups'] == {}
    assert payload['items'] == []


def test_add_queue_item_is_idempotent_and_updates_existing_item(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_project_queue(config)['ok'] is True
    assert (
        add_queue_item(
            config,
            item_id='m33-1',
            project_id='aresforge-main',
            repo_id='core',
            title='Original title',
        )['ok']
        is True
    )
    second = add_queue_item(
        config,
        item_id='m33-1',
        project_id='aresforge-main',
        repo_id='core',
        title='Updated title',
        status='ready',
        priority='high',
        item_type='feature',
    )
    assert second['ok'] is True
    assert second['created'] is False
    assert second['item']['title'] == 'Updated title'
    assert second['item']['status'] == 'ready'
    assert second['item']['priority'] == 'high'
    assert second['item']['item_type'] == 'feature'


def test_update_queue_item_only_supplied_fields(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_project_queue(config)['ok'] is True
    assert (
        add_queue_item(
            config,
            item_id='m33-1',
            project_id='aresforge-main',
            repo_id='core',
            title='Queue task',
            status='proposed',
            priority='normal',
            item_type='task',
        )['ok']
        is True
    )
    updated = update_queue_item(
        config,
        item_id='m33-1',
        status='in_progress',
        notes='started',
    )
    assert updated['ok'] is True
    assert updated['item']['status'] == 'in_progress'
    assert updated['item']['notes'] == 'started'
    assert updated['item']['priority'] == 'normal'


def test_update_queue_item_missing_item_fails_clearly(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_project_queue(config)['ok'] is True
    payload = update_queue_item(config, item_id='missing', status='ready')
    assert payload['ok'] is False
    assert payload['error'] == 'queue_item_not_found'


def test_invalid_status_validation(tmp_path: Path) -> None:
    config = _config(tmp_path)
    payload = add_queue_item(
        config,
        item_id='m33-1',
        project_id='p',
        repo_id='r',
        title='x',
        status='bad-status',
    )
    assert payload['ok'] is False
    assert payload['error'] == 'invalid_queue_status'


def test_invalid_priority_validation(tmp_path: Path) -> None:
    config = _config(tmp_path)
    payload = add_queue_item(
        config,
        item_id='m33-1',
        project_id='p',
        repo_id='r',
        title='x',
        priority='bad-priority',
    )
    assert payload['ok'] is False
    assert payload['error'] == 'invalid_queue_priority'


def test_invalid_type_validation(tmp_path: Path) -> None:
    config = _config(tmp_path)
    payload = add_queue_item(
        config,
        item_id='m33-1',
        project_id='p',
        repo_id='r',
        title='x',
        item_type='bad-type',
    )
    assert payload['ok'] is False
    assert payload['error'] == 'invalid_queue_item_type'


def test_inspect_all_items(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_project_queue(config)['ok'] is True
    assert (
        add_queue_item(
            config,
            item_id='a',
            project_id='p1',
            repo_id='r1',
            title='A',
            status='ready',
            item_type='task',
        )['ok']
        is True
    )
    assert (
        add_queue_item(
            config,
            item_id='b',
            project_id='p2',
            repo_id='r2',
            title='B',
            status='blocked',
            item_type='bug',
        )['ok']
        is True
    )
    inspected = inspect_project_queue(config)
    assert inspected['ok'] is True
    parsed = json.loads(inspected['stdout'])
    assert parsed['item_count'] == 2


def test_inspect_filters(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_project_queue(config)['ok'] is True
    assert (
        add_queue_item(
            config,
            item_id='a',
            project_id='project-one',
            repo_id='repo-a',
            title='A',
            status='ready',
            item_type='task',
            assigned_agent='agent-a',
        )['ok']
        is True
    )
    assert (
        add_queue_item(
            config,
            item_id='b',
            project_id='project-one',
            repo_id='repo-b',
            title='B',
            status='blocked',
            item_type='bug',
            assigned_agent='agent-b',
        )['ok']
        is True
    )
    filtered = inspect_project_queue(
        config,
        project_id='project-one',
        repo_id='repo-a',
        status='ready',
        item_type='task',
        assigned_agent='agent-a',
    )
    assert filtered['ok'] is True
    parsed = json.loads(filtered['stdout'])
    assert parsed['item_count'] == 1
    assert parsed['work_items'][0]['item_id'] == 'a'


def test_inspect_single_item(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_project_queue(config)['ok'] is True
    assert (
        add_queue_item(
            config,
            item_id='m33-1',
            project_id='p',
            repo_id='r',
            title='Single',
        )['ok']
        is True
    )
    payload = inspect_queue_item(config, item_id='m33-1')
    assert payload['ok'] is True
    parsed = json.loads(payload['stdout'])
    assert parsed['item']['item_id'] == 'm33-1'


def test_dependency_warning_when_dependency_missing(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_project_queue(config)['ok'] is True
    payload = add_queue_item(
        config,
        item_id='m33-1',
        project_id='p',
        repo_id='r',
        title='With dependency',
        dependencies=['future-item'],
    )
    assert payload['ok'] is True
    assert any('reference not found in queue yet' in warning for warning in payload['warnings'])


def test_registry_validation_success(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_project_queue(config)['ok'] is True
    assert init_managed_project_registry(config)['ok'] is True
    assert (
        register_managed_project(
            config,
            project_id='project-one',
            name='Project One',
            root_path=str(tmp_path),
        )['ok']
        is True
    )
    assert (
        register_managed_repo(
            config,
            project_id='project-one',
            repo_id='repo-main',
            name='Repo Main',
            path=str(tmp_path),
        )['ok']
        is True
    )
    payload = add_queue_item(
        config,
        item_id='m33-1',
        project_id='project-one',
        repo_id='repo-main',
        title='validated item',
    )
    assert payload['ok'] is True


def test_registry_validation_fails_when_project_or_repo_missing(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_project_queue(config)['ok'] is True
    assert init_managed_project_registry(config)['ok'] is True
    missing_project = add_queue_item(
        config,
        item_id='m33-1',
        project_id='missing-project',
        repo_id='repo-main',
        title='x',
    )
    assert missing_project['ok'] is False
    assert missing_project['error'] == 'managed_project_not_found'

    assert (
        register_managed_project(
            config,
            project_id='project-one',
            name='Project One',
            root_path=str(tmp_path),
        )['ok']
        is True
    )
    missing_repo = add_queue_item(
        config,
        item_id='m33-2',
        project_id='project-one',
        repo_id='missing-repo',
        title='x',
    )
    assert missing_repo['ok'] is False
    assert missing_repo['error'] == 'managed_repo_not_found'


def test_registry_validation_skipped_warning_when_no_registry_exists(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_project_queue(config)['ok'] is True
    payload = add_queue_item(
        config,
        item_id='m33-1',
        project_id='project-one',
        repo_id='repo-main',
        title='x',
    )
    assert payload['ok'] is True
    assert any('validation was skipped' in warning.lower() for warning in payload['warnings'])


def test_generate_local_queue_prompt_pack_groups_and_writes_artifact(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_project_queue(config)['ok'] is True
    assert add_queue_item(
        config,
        item_id='q-ready',
        project_id='p1',
        repo_id='r1',
        title='Ready task',
        description='Queue item ready for local execution prep.',
        status='ready',
        priority='high',
        item_type='feature',
        notes='Acceptance criteria:\n- Preserve local-only boundaries',
    )['ok'] is True
    assert add_queue_item(
        config,
        item_id='q-progress',
        project_id='p1',
        repo_id='r1',
        title='In progress task',
        description='Already started.',
        status='in_progress',
        priority='normal',
        item_type='task',
    )['ok'] is True

    output = tmp_path / 'artifacts' / 'prompt_packs' / 'pack.txt'
    payload = generate_local_queue_prompt_pack(config, output=output)
    assert payload['ok'] is True
    assert payload['local_only'] is True
    assert payload['item_count'] == 2
    assert payload['output_path'] == str(output)
    assert output.exists()
    assert payload['artifact_registry']['artifact_type'] == 'prompt_pack'
    assert payload['artifact_registry']['artifact_path'] == str(output)
    assert payload['artifact_registry']['exists'] is True
    assert filter_ai_artifacts(config, artifact_type='prompt_pack')['total_artifacts'] == 1
    assert 'Agent Prompt Pack (Local-Only)' in payload['prompt_pack']
    assert payload['include_routing'] is True
    assert payload['execution_allowed'] is False
    assert '- recommended_agent_lane: unrouted' in payload['prompt_pack']
    assert 'Manual routing required; this queue item is unrouted' in payload['prompt_pack']
    assert '- execution_allowed: false' in payload['prompt_pack']
    assert 'Final response format:' in payload['prompt_pack']

    duplicate = generate_local_queue_prompt_pack(config, output=output)
    assert duplicate['ok'] is False
    assert any('already exists' in warning for warning in duplicate['warnings'])


def test_generate_local_queue_prompt_pack_includes_routing_metadata_and_groups_by_agent_lane(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_project_queue(config)['ok'] is True
    assert add_queue_item(
        config,
        item_id='q-routed-codex',
        project_id='p1',
        repo_id='r1',
        title='High value backend change',
        description='Backend lifecycle change that should be reviewed carefully.',
        status='ready',
        priority='high',
        item_type='feature',
        blocked_by=['q-design'],
    )['ok'] is True
    assert update_local_queue_item_routing_metadata(
        config,
        item_id='q-routed-codex',
        routing_metadata={
            'recommended_agent_lane': 'high_value_codex',
            'recommended_engine': 'codex_cli',
            'recommended_model': 'codex-high',
            'fallback_engine': 'local_reasoning_llm',
            'fallback_model': 'local-reason',
            'routing_policy_source': 'm54_decision_matrix_v1',
            'routing_reason': 'High-value backend/operator lifecycle change.',
            'risk_level': 'high',
            'complexity_level': 'high',
            'escalation_reason': 'Operator lifecycle change.',
            'project_ai_mode': 'high_confidence',
            'operator_override': True,
        },
    )['ok'] is True

    payload = generate_local_queue_prompt_pack(
        config,
        statuses=['ready'],
        group_by_routing=True,
        routing_group_by='by_agent_lane',
    )

    assert payload['ok'] is True
    assert payload['groups'] == ['by_agent_lane: high_value_codex']
    assert payload['items'][0]['dependencies'] == ['q-design']
    assert payload['items'][0]['execution_allowed'] is False
    assert payload['items'][0]['routing_metadata']['recommended_engine'] == 'codex_cli'
    assert 'recommended_agent_lane: high_value_codex' in payload['prompt_pack']
    assert 'recommended_engine: codex_cli' in payload['prompt_pack']
    assert 'Codex CLI is recommended for operator review, but AresForge does not execute Codex.' in payload['prompt_pack']
    assert 'Dependencies: q-design' in payload['prompt_pack']


def test_generate_local_queue_prompt_pack_groups_by_engine_and_marks_local_llm_recommendation_only(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_project_queue(config)['ok'] is True
    assert add_queue_item(
        config,
        item_id='q-routed-local',
        project_id='p1',
        repo_id='r1',
        title='Simple UI copy change',
        description='Small wording update.',
        status='ready',
        priority='normal',
        item_type='task',
    )['ok'] is True
    assert update_local_queue_item_routing_metadata(
        config,
        item_id='q-routed-local',
        routing_metadata={
            'recommended_agent_lane': 'coding',
            'recommended_engine': 'local_coding_llm',
            'recommended_model': 'local-code',
            'routing_policy_source': 'm54_decision_matrix_v1',
            'routing_reason': 'Simple UI wording task.',
            'risk_level': 'low',
            'complexity_level': 'low',
            'project_ai_mode': 'cost_saver',
        },
    )['ok'] is True

    payload = generate_local_queue_prompt_pack(
        config,
        statuses=['ready'],
        group_by_routing=True,
        routing_group_by='by_engine',
    )

    assert payload['ok'] is True
    assert payload['groups'] == ['by_engine: local_coding_llm']
    assert 'local_coding_llm is recommended for operator review, but AresForge does not execute local LLMs.' in payload['prompt_pack']


def test_generate_local_llm_prompt_preview_succeeds_for_local_coding_llm_and_writes_artifact(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _write_local_llm_environment(tmp_path, coding_model='local-code')
    _seed_preview_item(config, item_id='q-local-code', engine='local_coding_llm', model='local-code')
    output = tmp_path / 'artifacts' / 'local_llm_previews' / 'preview.txt'

    payload = generate_local_llm_prompt_preview(config, item_id='q-local-code', output=output)

    assert payload['ok'] is True
    assert payload['preview_allowed'] is True
    assert payload['execution_allowed'] is False
    assert payload['recommended_engine'] == 'local_coding_llm'
    assert payload['recommended_model'] == 'local-code'
    assert 'Local LLM Prompt Preview (No Execution)' in payload['prompt_preview']
    assert 'recommended_engine: local_coding_llm' in payload['prompt_preview']
    assert 'No GitHub API, no gh, and no GitHub mutation.' in payload['prompt_preview']
    assert 'The local LLM must not claim execution' in payload['prompt_preview']
    assert output.exists()
    assert payload['artifact_registry']['artifact_type'] == 'local_llm_prompt_preview'
    assert payload['artifact_registry']['item_id'] == 'q-local-code'
    assert filter_ai_artifacts(config, item_id='q-local-code', artifact_type='local_llm_prompt_preview')['total_artifacts'] == 1

    duplicate = generate_local_llm_prompt_preview(config, item_id='q-local-code', output=output)
    assert duplicate['ok'] is False
    assert any('already exists' in warning for warning in duplicate['warnings'])


def test_generate_local_llm_prompt_preview_succeeds_for_local_reasoning_llm_with_environment_model(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _write_local_llm_environment(tmp_path, reasoning_model='local-reason')
    _seed_preview_item(config, item_id='q-local-reason', engine='local_reasoning_llm', model='')

    payload = generate_local_llm_prompt_preview(config, item_id='q-local-reason')

    assert payload['ok'] is True
    assert payload['recommended_engine'] == 'local_reasoning_llm'
    assert payload['recommended_model'] == 'local-reason'
    assert payload['execution_allowed'] is False
    assert 'recommended_model: local-reason' in payload['prompt_preview']


def test_generate_local_llm_prompt_preview_blocks_codex_and_unrouted_items(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _write_local_llm_environment(tmp_path)
    _seed_preview_item(config, item_id='q-codex', engine='codex_cli', model='codex-model')

    codex = generate_local_llm_prompt_preview(config, item_id='q-codex')
    assert codex['ok'] is False
    assert codex['preview_allowed'] is False
    assert codex['execution_allowed'] is False
    assert any('codex_cli' in blocker for blocker in codex['blockers'])

    assert add_queue_item(
        config,
        item_id='q-unrouted',
        project_id='p1',
        repo_id='r1',
        title='Unrouted task',
        description='Missing routing metadata.',
        status='ready',
    )['ok'] is True
    unrouted = generate_local_llm_prompt_preview(config, item_id='q-unrouted')
    assert unrouted['ok'] is False
    assert any('unrouted' in blocker.lower() for blocker in unrouted['blockers'])


def test_generate_local_llm_prompt_preview_blocks_missing_environment_and_manual_only(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_preview_item(config, item_id='q-manual', engine='local_coding_llm', model='local-code')
    settings_path = tmp_path / '.aresforge' / 'projects' / 'p1' / 'ai_settings.json'
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(json.dumps({'project_ai_mode': 'manual_only'}, indent=2) + '\n', encoding='utf-8')
    assert update_local_queue_item_routing_metadata(
        config,
        item_id='q-manual',
        routing_metadata={'project_ai_mode': 'manual_only'},
    )['ok'] is True

    payload = generate_local_llm_prompt_preview(config, item_id='q-manual')

    assert payload['ok'] is False
    assert any('environment contract' in blocker for blocker in payload['blockers'])
    assert any('manual_only' in blocker for blocker in payload['blockers'])


def _healthy_local_llm_payload(*, model: str = 'local-code') -> dict[str, object]:
    return {
        'ok': True,
        'provider': 'ollama',
        'provider_base_url': 'http://127.0.0.1:11434',
        'provider_reachable': True,
        'available_models': [model, 'local-reason'],
        'warnings': [],
        'blockers': [],
    }


def test_execute_local_llm_for_queue_item_dry_run_does_not_call_provider(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _write_local_llm_environment(tmp_path, coding_model='local-code', execution_enabled=True)
    _seed_preview_item(config, item_id='q-execute-dry-run', engine='local_coding_llm', model='local-code')
    called = {'provider': False}

    payload = execute_local_llm_for_queue_item(
        config,
        item_id='q-execute-dry-run',
        dry_run=True,
        health_check_fn=lambda _config: _healthy_local_llm_payload(),
        provider_generate_fn=lambda **_kwargs: called.__setitem__('provider', True),
    )

    assert payload['ok'] is True
    assert payload['dry_run'] is True
    assert payload['executed'] is False
    assert payload['execution_allowed'] is False
    assert called['provider'] is False
    audit = filter_execution_audit_log(config, item_id='q-execute-dry-run', action_type='local_llm_execute')
    assert audit['total_entries'] == 1
    assert audit['entries'][0]['outcome'] == 'dry_run'
    assert audit['entries'][0]['executed'] is False


def test_execute_local_llm_for_queue_item_blocks_without_confirmation_codex_and_unrouted(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _write_local_llm_environment(tmp_path, execution_enabled=True)
    _seed_preview_item(config, item_id='q-execute-no-confirm', engine='local_coding_llm', model='local-code')

    no_confirm = execute_local_llm_for_queue_item(
        config,
        item_id='q-execute-no-confirm',
        health_check_fn=lambda _config: _healthy_local_llm_payload(),
        provider_generate_fn=lambda **_kwargs: 'unused',
    )
    assert no_confirm['ok'] is False
    assert no_confirm['executed'] is False
    assert any('confirm_operator_gate' in blocker for blocker in no_confirm['blockers'])

    assert update_local_queue_item_routing_metadata(
        config,
        item_id='q-execute-no-confirm',
        routing_metadata={'recommended_engine': 'codex_cli', 'recommended_model': 'default-codex'},
    )['ok'] is True
    codex = execute_local_llm_for_queue_item(
        config,
        item_id='q-execute-no-confirm',
        confirm_operator_gate=True,
        health_check_fn=lambda _config: _healthy_local_llm_payload(),
        provider_generate_fn=lambda **_kwargs: 'unused',
    )
    assert codex['ok'] is False
    assert any('codex_cli' in blocker for blocker in codex['blockers'])

    assert add_queue_item(
        config,
        item_id='q-execute-unrouted',
        project_id='p1',
        repo_id='r1',
        title='Unrouted execution',
        description='Should block.',
        status='ready',
    )['ok'] is True
    unrouted = execute_local_llm_for_queue_item(
        config,
        item_id='q-execute-unrouted',
        confirm_operator_gate=True,
        health_check_fn=lambda _config: _healthy_local_llm_payload(),
        provider_generate_fn=lambda **_kwargs: 'unused',
    )
    assert unrouted['ok'] is False
    assert any('unrouted' in blocker.lower() for blocker in unrouted['blockers'])
    blocked_audit = filter_execution_audit_log(config, item_id='q-execute-no-confirm', outcome='blocked')
    assert blocked_audit['total_entries'] >= 1
    assert any(entry['action_type'] == 'blocked_attempt' for entry in blocked_audit['entries'])


def test_execute_local_llm_for_queue_item_with_mocked_provider_succeeds_and_preserves_queue(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _write_local_llm_environment(tmp_path, coding_model='local-code', execution_enabled=True)
    _seed_preview_item(config, item_id='q-execute-success', engine='local_coding_llm', model='local-code')
    output = tmp_path / 'artifacts' / 'local_llm_results' / 'result.json'

    payload = execute_local_llm_for_queue_item(
        config,
        item_id='q-execute-success',
        confirm_operator_gate=True,
        output=output,
        health_check_fn=lambda _config: _healthy_local_llm_payload(),
        provider_generate_fn=lambda **kwargs: f"advisory response for {kwargs['model']}",
    )

    assert payload['ok'] is True
    assert payload['execution_allowed'] is True
    assert payload['executed'] is True
    assert payload['response_text'] == 'advisory response for local-code'
    assert payload['result_artifact_path'] == str(output)
    assert output.exists()
    assert payload['artifact_registry']['artifact_type'] == 'local_llm_execution_result'
    assert payload['artifact_registry']['item_id'] == 'q-execute-success'
    assert filter_ai_artifacts(config, artifact_type='local_llm_execution_result')['total_artifacts'] == 1
    detail = inspect_queue_item(config, item_id='q-execute-success')
    assert detail['payload']['item']['status'] == 'ready'
    assert not (tmp_path / 'unexpected_repo_mutation.txt').exists()

    duplicate = execute_local_llm_for_queue_item(
        config,
        item_id='q-execute-success',
        confirm_operator_gate=True,
        output=output,
        health_check_fn=lambda _config: _healthy_local_llm_payload(),
        provider_generate_fn=lambda **_kwargs: 'second response',
    )
    assert duplicate['ok'] is False
    assert any('already exists' in warning for warning in duplicate['warnings'])


def test_execute_local_llm_for_queue_item_high_risk_requires_override(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _write_local_llm_environment(tmp_path, reasoning_model='local-reason', execution_enabled=True)
    _seed_preview_item(config, item_id='q-execute-risk', engine='local_reasoning_llm', model='local-reason')
    assert update_local_queue_item_routing_metadata(
        config,
        item_id='q-execute-risk',
        routing_metadata={
            'recommended_agent_lane': 'coding',
            'recommended_engine': 'local_reasoning_llm',
            'recommended_model': 'local-reason',
            'routing_policy_source': 'test',
            'routing_reason': 'High-risk local reasoning prototype.',
            'risk_level': 'high',
            'complexity_level': 'high',
            'project_ai_mode': 'balanced',
        },
    )['ok'] is True

    blocked = execute_local_llm_for_queue_item(
        config,
        item_id='q-execute-risk',
        confirm_operator_gate=True,
        health_check_fn=lambda _config: _healthy_local_llm_payload(model='local-reason'),
        provider_generate_fn=lambda **_kwargs: 'blocked',
    )
    assert blocked['ok'] is False
    assert any('High or critical risk' in blocker for blocker in blocked['blockers'])

    allowed = execute_local_llm_for_queue_item(
        config,
        item_id='q-execute-risk',
        confirm_operator_gate=True,
        operator_override=True,
        health_check_fn=lambda _config: _healthy_local_llm_payload(model='local-reason'),
        provider_generate_fn=lambda **_kwargs: 'override advisory response',
    )
    assert allowed['ok'] is True
    assert allowed['executed'] is True
    assert allowed['response_text'] == 'override advisory response'


def test_add_local_queue_item_with_explicit_project_and_repo(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_project_queue(config)['ok'] is True
    assert init_managed_project_registry(config)['ok'] is True
    assert register_managed_project(
        config,
        project_id='project-one',
        name='Project One',
        root_path=str(tmp_path),
        primary_repo_id='repo-main',
    )['ok'] is True
    assert register_managed_repo(
        config,
        project_id='project-one',
        repo_id='repo-main',
        name='Repo Main',
        path=str(tmp_path),
        role='primary',
    )['ok'] is True

    payload = add_local_queue_item(
        config,
        title='Build local queue add flow',
        description='Create a queue item from the local CLI.',
        project_id='project-one',
        repo_id='repo-main',
        item_type='feature',
        priority='high',
        assigned_agent='agent-alpha',
        dependencies=['future-item'],
        tags=['queue'],
    )

    assert payload['ok'] is True
    assert payload['project_id'] == 'project-one'
    assert payload['repo_id'] == 'repo-main'
    assert payload['status'] == 'proposed'
    assert payload['item_id'].startswith('local-build-local-queue-add-flow')


def test_add_local_queue_item_uses_active_project_defaults(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_project_queue(config)['ok'] is True
    assert init_managed_project_registry(config)['ok'] is True
    assert register_managed_project(
        config,
        project_id='project-one',
        name='Project One',
        root_path=str(tmp_path),
        primary_repo_id='repo-main',
    )['ok'] is True
    assert register_managed_repo(
        config,
        project_id='project-one',
        repo_id='repo-main',
        name='Repo Main',
        path=str(tmp_path),
        role='primary',
    )['ok'] is True
    assert set_active_project(config, project_id='project-one')['ok'] is True

    payload = add_local_queue_item(
        config,
        title='Review active defaults',
        item_type='task',
        priority='normal',
    )

    assert payload['ok'] is True
    assert payload['project_id'] == 'project-one'
    assert payload['repo_id'] == 'repo-main'
    item_payload = inspect_queue_item(config, item_id=payload['item_id'])
    assert item_payload['ok'] is True
    parsed = json.loads(item_payload['stdout'])
    assert parsed['item']['source'] == 'local_cli'


def test_add_local_queue_item_requires_title(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_project_queue(config)['ok'] is True

    payload = add_local_queue_item(config, title='   ')

    assert payload['ok'] is False
    assert payload['error'] == 'invalid_local_queue_item_payload'


def test_add_local_queue_item_rejects_unknown_project(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_project_queue(config)['ok'] is True
    assert init_managed_project_registry(config)['ok'] is True

    payload = add_local_queue_item(
        config,
        title='Unknown project item',
        project_id='missing-project',
    )

    assert payload['ok'] is False
    assert payload['error'] == 'managed_project_not_found'


def test_add_local_queue_item_infers_existing_prefix_when_state_milestone_missing(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_project_queue(config)['ok'] is True
    assert add_queue_item(
        config,
        item_id='m15-existing-item',
        project_id='project-one',
        repo_id='repo-main',
        title='Existing item',
    )['ok'] is True

    payload = add_local_queue_item(
        config,
        title='Infer queue prefix',
        project_id='project-one',
        repo_id='repo-main',
    )

    assert payload['ok'] is True
    assert payload['item_id'].startswith('m15-infer-queue-prefix')


def test_inspect_local_queue_item_readiness_ready_item(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_project_queue(config)['ok'] is True
    assert init_managed_project_registry(config)['ok'] is True
    assert register_managed_project(
        config,
        project_id='project-one',
        name='Project One',
        root_path=str(tmp_path),
        primary_repo_id='repo-main',
    )['ok'] is True
    assert register_managed_repo(
        config,
        project_id='project-one',
        repo_id='repo-main',
        name='Repo Main',
        path=str(tmp_path),
        role='primary',
    )['ok'] is True
    assert add_queue_item(
        config,
        item_id='dep-done',
        project_id='project-one',
        repo_id='repo-main',
        title='Done dependency',
        description='Already complete.',
        status='done',
    )['ok'] is True
    assert add_queue_item(
        config,
        item_id='ready-item',
        project_id='project-one',
        repo_id='repo-main',
        title='Ready item',
        description='Ready to start.',
        status='ready',
        dependencies=['dep-done'],
    )['ok'] is True

    payload = inspect_local_queue_item_readiness(config, item_id='ready-item')

    assert payload['ok'] is True
    assert payload['readiness_status'] == 'ready'
    assert payload['can_start'] is True
    assert payload['missing_fields'] == []
    assert payload['dependency_summary']['resolved_dependencies'] == ['dep-done']


def test_inspect_local_queue_item_readiness_missing_item(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_project_queue(config)['ok'] is True

    payload = inspect_local_queue_item_readiness(config, item_id='missing-item')

    assert payload['ok'] is False
    assert payload['readiness_status'] == 'not_found'
    assert payload['can_start'] is False


def test_inspect_local_queue_item_readiness_missing_required_field(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_project_queue(config)['ok'] is True
    assert init_managed_project_registry(config)['ok'] is True
    assert register_managed_project(
        config,
        project_id='project-one',
        name='Project One',
        root_path=str(tmp_path),
        primary_repo_id='repo-main',
    )['ok'] is True
    assert register_managed_repo(
        config,
        project_id='project-one',
        repo_id='repo-main',
        name='Repo Main',
        path=str(tmp_path),
        role='primary',
    )['ok'] is True
    assert add_queue_item(
        config,
        item_id='missing-context',
        project_id='project-one',
        repo_id='repo-main',
        title='Missing context',
        status='ready',
    )['ok'] is True

    payload = inspect_local_queue_item_readiness(config, item_id='missing-context')

    assert payload['ok'] is True
    assert payload['readiness_status'] == 'needs_attention'
    assert payload['can_start'] is False
    assert 'execution_context' in payload['missing_fields']


def test_inspect_local_queue_item_readiness_blocked_by_dependency(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_project_queue(config)['ok'] is True
    assert init_managed_project_registry(config)['ok'] is True
    assert register_managed_project(
        config,
        project_id='project-one',
        name='Project One',
        root_path=str(tmp_path),
        primary_repo_id='repo-main',
    )['ok'] is True
    assert register_managed_repo(
        config,
        project_id='project-one',
        repo_id='repo-main',
        name='Repo Main',
        path=str(tmp_path),
        role='primary',
    )['ok'] is True
    assert add_queue_item(
        config,
        item_id='blocked-dependency',
        project_id='project-one',
        repo_id='repo-main',
        title='Blocked dependency',
        description='Still blocked.',
        status='blocked',
    )['ok'] is True
    assert add_queue_item(
        config,
        item_id='waiting-item',
        project_id='project-one',
        repo_id='repo-main',
        title='Waiting item',
        description='Depends on blocked work.',
        status='ready',
        dependencies=['blocked-dependency'],
    )['ok'] is True

    payload = inspect_local_queue_item_readiness(config, item_id='waiting-item')

    assert payload['ok'] is True
    assert payload['readiness_status'] == 'blocked'
    assert payload['can_start'] is False
    assert payload['dependency_summary']['unresolved_dependencies'][0]['item_id'] == 'blocked-dependency'


def test_inspect_local_queue_item_readiness_is_read_only(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_project_queue(config)['ok'] is True
    assert add_queue_item(
        config,
        item_id='readonly-item',
        project_id='p1',
        repo_id='r1',
        title='Read only',
        description='Do not mutate queue file.',
        status='ready',
    )['ok'] is True
    queue_path = resolve_project_queue_path(config.repo_root, None)
    before = queue_path.read_text(encoding='utf-8')

    payload = inspect_local_queue_item_readiness(config, item_id='readonly-item')

    after = queue_path.read_text(encoding='utf-8')
    assert payload['ok'] is True
    assert before == after


def test_start_local_queue_item_from_proposed_when_ready(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_project_queue(config)['ok'] is True
    assert init_managed_project_registry(config)['ok'] is True
    assert register_managed_project(
        config,
        project_id='project-one',
        name='Project One',
        root_path=str(tmp_path),
        primary_repo_id='repo-main',
    )['ok'] is True
    assert register_managed_repo(
        config,
        project_id='project-one',
        repo_id='repo-main',
        name='Repo Main',
        path=str(tmp_path),
        role='primary',
    )['ok'] is True
    assert add_queue_item(
        config,
        item_id='startable-proposed',
        project_id='project-one',
        repo_id='repo-main',
        title='Startable proposed item',
        description='Ready to begin local work.',
        status='proposed',
    )['ok'] is True

    payload = start_local_queue_item(config, item_id='startable-proposed')

    assert payload['ok'] is True
    assert payload['previous_status'] == 'proposed'
    assert payload['status'] == 'in_progress'
    item_payload = inspect_queue_item(config, item_id='startable-proposed')
    parsed = json.loads(item_payload['stdout'])
    assert parsed['item']['status'] == 'in_progress'
    assert parsed['item']['previous_status'] == 'proposed'
    assert parsed['item']['started_via'] == 'local_operator'
    assert parsed['item']['started_at']


def test_start_local_queue_item_cannot_start_missing_item(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_project_queue(config)['ok'] is True

    payload = start_local_queue_item(config, item_id='missing-item')

    assert payload['ok'] is False
    assert payload['item_id'] == 'missing-item'


def test_start_local_queue_item_cannot_start_not_ready_item(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_project_queue(config)['ok'] is True
    assert init_managed_project_registry(config)['ok'] is True
    assert register_managed_project(
        config,
        project_id='project-one',
        name='Project One',
        root_path=str(tmp_path),
        primary_repo_id='repo-main',
    )['ok'] is True
    assert register_managed_repo(
        config,
        project_id='project-one',
        repo_id='repo-main',
        name='Repo Main',
        path=str(tmp_path),
        role='primary',
    )['ok'] is True
    assert add_queue_item(
        config,
        item_id='blocked-item',
        project_id='project-one',
        repo_id='repo-main',
        title='Blocked item',
        description='Blocked on dependency.',
        status='blocked',
    )['ok'] is True

    payload = start_local_queue_item(config, item_id='blocked-item')

    assert payload['ok'] is False
    assert payload['status'] == 'blocked'
    item_payload = inspect_queue_item(config, item_id='blocked-item')
    parsed = json.loads(item_payload['stdout'])
    assert parsed['item']['status'] == 'blocked'


def test_start_local_queue_item_cannot_restart_in_progress_or_done(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_project_queue(config)['ok'] is True
    assert add_queue_item(
        config,
        item_id='active-item',
        project_id='p1',
        repo_id='r1',
        title='Active item',
        description='Already running.',
        status='in_progress',
    )['ok'] is True
    assert add_queue_item(
        config,
        item_id='done-item',
        project_id='p1',
        repo_id='r1',
        title='Done item',
        description='Already finished.',
        status='done',
    )['ok'] is True

    active_payload = start_local_queue_item(config, item_id='active-item')
    done_payload = start_local_queue_item(config, item_id='done-item')

    assert active_payload['ok'] is False
    assert done_payload['ok'] is False


def test_start_local_queue_item_persists_status_transition(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_project_queue(config)['ok'] is True
    assert add_queue_item(
        config,
        item_id='persist-item',
        project_id='p1',
        repo_id='r1',
        title='Persisted start',
        description='Persist start metadata.',
        status='ready',
    )['ok'] is True
    queue_path = resolve_project_queue_path(config.repo_root, None)

    payload = start_local_queue_item(config, item_id='persist-item')

    rendered = json.loads(queue_path.read_text(encoding='utf-8'))
    persisted = next(item for item in rendered['work_items'] if item['item_id'] == 'persist-item')
    assert payload['ok'] is True
    assert persisted['status'] == 'in_progress'
    assert persisted['previous_status'] == 'ready'
    assert persisted['started_via'] == 'local_operator'


def test_generate_local_queue_item_codex_prompt_for_valid_item(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_project_queue(config)['ok'] is True
    assert add_queue_item(
        config,
        item_id='ready-item',
        project_id='project-one',
        repo_id='repo-main',
        title='Prepare queue prompt generation',
        description='Generate a Codex prompt from the local queue item.',
        status='ready',
        tags=['area:queue'],
        notes='Acceptance criteria:\n- Prompt includes local-only constraints\n- Prompt includes validation commands',
    )['ok'] is True

    payload = generate_local_queue_item_codex_prompt(config, item_id='ready-item')

    assert payload['ok'] is True
    assert payload['local_only'] is True
    assert payload['item_id'] == 'ready-item'
    assert payload['readiness_status'] == 'ready'
    assert 'Repository path: ' in payload['prompt']
    assert str(config.repo_root) in payload['prompt']
    assert 'Queue item title: Prepare queue prompt generation' in payload['prompt']
    assert 'Target area: queue' in payload['prompt']
    assert 'Prompt includes local-only constraints' in payload['prompt']
    assert 'Do not push.' in payload['prompt']
    assert 'Do not use GitHub API, gh, GitHub issues, pull requests, workflow activity, or GitHub mutation.' in payload['prompt']
    assert 'git diff --check' in payload['prompt']
    assert 'python -m pytest tests/test_roadmap_db_control.py tests/test_config_and_migrations.py tests/test_cli.py' in payload['prompt']


def test_generate_local_queue_item_codex_prompt_missing_item_returns_safe_failure(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_project_queue(config)['ok'] is True

    payload = generate_local_queue_item_codex_prompt(config, item_id='missing-item')

    assert payload['ok'] is False
    assert payload['local_only'] is True
    assert payload['item_id'] == 'missing-item'
    assert payload['readiness_status'] == 'not_found'
    assert payload['prompt'] == ''
    assert payload['warnings'] == []


def test_generate_local_queue_item_codex_prompt_writes_output_file(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_project_queue(config)['ok'] is True
    assert add_queue_item(
        config,
        item_id='ready-item',
        project_id='project-one',
        repo_id='repo-main',
        title='Write queue prompt artifact',
        description='Persist a prompt artifact locally.',
        status='ready',
    )['ok'] is True
    output_path = tmp_path / 'artifacts' / 'local_queue_prompts' / 'prompt.txt'

    payload = generate_local_queue_item_codex_prompt(
        config,
        item_id='ready-item',
        output=output_path,
        commit_message='Custom commit guidance',
    )

    assert payload['ok'] is True
    assert payload['output_path'] == str(output_path)
    assert output_path.exists()
    rendered = output_path.read_text(encoding='utf-8')
    assert 'Commit message guidance: Custom commit guidance' in rendered


def test_generate_codex_high_value_lane_prompt_for_codex_cli_route(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_preview_item(config, item_id='q-codex-cli', engine='codex_cli', model='gpt-5-codex')

    payload = generate_codex_high_value_lane_prompt(config, item_id='q-codex-cli')

    assert payload['ok'] is True
    assert payload['eligible_for_codex_lane'] is True
    assert payload['recommended_engine'] == 'codex_cli'
    assert payload['recommended_model'] == 'gpt-5-codex'
    assert payload['execution_allowed'] is False
    assert 'recommended_engine is codex_cli' in payload['codex_lane_reason']
    assert 'AresForge must not automatically execute Codex.' in payload['prompt_preview']
    assert 'No GitHub API.' in payload['prompt_preview']
    assert 'python -m pytest tests/test_local_project_queue.py tests/test_hub_local_queue_lifecycle_api.py tests/test_hub_ui_foundation.py tests/test_local_project_factory.py tests/test_hub_project_factory_api.py' in payload['prompt_preview']
    assert 'git diff --check' in payload['prompt_preview']


def test_generate_codex_high_value_lane_prompt_for_high_value_lane(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_preview_item(config, item_id='q-high-value-lane', engine='local_reasoning_llm', model='local-reason')
    assert update_local_queue_item_routing_metadata(
        config,
        item_id='q-high-value-lane',
        routing_metadata={
            'recommended_agent_lane': 'high_value_codex',
            'recommended_engine': 'local_reasoning_llm',
            'recommended_model': 'local-reason',
            'routing_policy_source': 'test',
            'routing_reason': 'Route to Codex review for backend API route.',
            'risk_level': 'medium',
            'complexity_level': 'medium',
            'project_ai_mode': 'balanced',
        },
    )['ok'] is True

    payload = generate_codex_high_value_lane_prompt(config, item_id='q-high-value-lane')

    assert payload['ok'] is True
    assert payload['eligible_for_codex_lane'] is True
    assert 'recommended_agent_lane is high_value_codex' in payload['codex_lane_reason']
    assert payload['execution_allowed'] is False


def test_generate_codex_high_value_lane_prompt_for_high_risk_item(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_preview_item(config, item_id='q-high-risk', engine='local_reasoning_llm', model='local-reason')
    assert update_local_queue_item_routing_metadata(
        config,
        item_id='q-high-risk',
        routing_metadata={
            'recommended_agent_lane': 'reviewer_validator',
            'recommended_engine': 'local_reasoning_llm',
            'recommended_model': 'local-reason',
            'risk_level': 'high',
            'complexity_level': 'low',
            'project_ai_mode': 'balanced',
        },
    )['ok'] is True

    payload = generate_codex_high_value_lane_prompt(config, item_id='q-high-risk')

    assert payload['ok'] is True
    assert payload['eligible_for_codex_lane'] is True
    assert 'risk_level is high' in payload['codex_lane_reason']


def test_generate_codex_high_value_lane_prompt_low_risk_local_llm_requires_override(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_preview_item(config, item_id='q-low-local', engine='local_coding_llm', model='local-code')

    blocked = generate_codex_high_value_lane_prompt(config, item_id='q-low-local')
    allowed = generate_codex_high_value_lane_prompt(config, item_id='q-low-local', operator_override=True)

    assert blocked['ok'] is False
    assert blocked['eligible_for_codex_lane'] is False
    assert blocked['prompt_preview'] == ''
    assert blocked['execution_allowed'] is False
    assert blocked['blockers']
    assert allowed['ok'] is True
    assert allowed['eligible_for_codex_lane'] is True
    assert 'operator override requests Codex' in allowed['codex_lane_reason']


def test_generate_codex_high_value_lane_prompt_artifact_non_overwrite(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_preview_item(config, item_id='q-codex-artifact', engine='codex_cli', model='gpt-5-codex')
    output_path = tmp_path / 'artifacts' / 'codex_high_value' / 'prompt.txt'

    first = generate_codex_high_value_lane_prompt(config, item_id='q-codex-artifact', output=output_path)
    duplicate = generate_codex_high_value_lane_prompt(config, item_id='q-codex-artifact', output=output_path)
    forced = generate_codex_high_value_lane_prompt(config, item_id='q-codex-artifact', output=output_path, force=True)

    assert first['ok'] is True
    assert output_path.exists()
    assert first['artifact_registry']['artifact_type'] == 'codex_high_value_prompt'
    assert first['artifact_registry']['item_id'] == 'q-codex-artifact'
    assert duplicate['ok'] is False
    assert 'Output file already exists. Re-run with force=true to overwrite.' in duplicate['warnings']
    assert forced['ok'] is True
    assert filter_ai_artifacts(config, item_id='q-codex-artifact', artifact_type='codex_high_value_prompt')['total_artifacts'] == 2
    assert output_path.read_text(encoding='utf-8').startswith('Codex CLI High-Value Lane Prompt')


def test_generate_codex_high_value_lane_prompt_creates_audit_entry(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_preview_item(config, item_id='q-codex-audit', engine='codex_cli', model='gpt-5-codex')

    payload = generate_codex_high_value_lane_prompt(config, item_id='q-codex-audit')
    audit = filter_execution_audit_log(config, item_id='q-codex-audit', action_type='codex_high_value_prompt')

    assert payload['ok'] is True
    assert audit['total_entries'] == 1
    entry = audit['entries'][0]
    assert entry['engine'] == 'codex_cli'
    assert entry['outcome'] == 'prompt_generated'
    assert entry['executed'] is False
    assert entry['execution_allowed'] is False


def test_complete_local_queue_item_in_progress_with_evidence(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_project_queue(config)['ok'] is True
    assert add_queue_item(
        config,
        item_id='complete-item',
        project_id='project-one',
        repo_id='repo-main',
        title='Complete item',
        description='Complete local implementation with evidence.',
        status='in_progress',
    )['ok'] is True

    payload = complete_local_queue_item(
        config,
        item_id='complete-item',
        commit_hash='abc123def',
        validation_summary='Targeted tests passed locally.',
        evidence_note='Manual smoke checks passed.',
        tests_run=['python -m pytest tests/test_local_project_queue.py'],
        changed_files=['src/aresforge/operator/local_project_queue.py'],
        artifact_paths=['artifacts/evidence/local-complete.md'],
    )

    assert payload['ok'] is True
    assert payload['previous_status'] == 'in_progress'
    assert payload['status'] == 'done'
    assert payload['completion_commit'] == 'abc123def'
    assert payload['validation_summary'] == 'Targeted tests passed locally.'


def test_complete_local_queue_item_cannot_complete_missing_item(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_project_queue(config)['ok'] is True

    payload = complete_local_queue_item(
        config,
        item_id='missing-item',
        commit_hash='abc123def',
        validation_summary='Targeted tests passed locally.',
    )

    assert payload['ok'] is False
    assert payload['item_id'] == 'missing-item'
    assert payload['status'] == ''


def test_complete_local_queue_item_cannot_complete_proposed_item(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_project_queue(config)['ok'] is True
    assert add_queue_item(
        config,
        item_id='proposed-item',
        project_id='project-one',
        repo_id='repo-main',
        title='Proposed item',
        description='Not started yet.',
        status='proposed',
    )['ok'] is True

    payload = complete_local_queue_item(
        config,
        item_id='proposed-item',
        commit_hash='abc123def',
        validation_summary='Targeted tests passed locally.',
    )

    assert payload['ok'] is False
    assert payload['status'] == 'proposed'
    assert any('in_progress' in warning for warning in payload['warnings'])


def test_complete_local_queue_item_requires_commit_hash(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_project_queue(config)['ok'] is True
    assert add_queue_item(
        config,
        item_id='complete-item',
        project_id='project-one',
        repo_id='repo-main',
        title='Complete item',
        description='Complete local implementation with evidence.',
        status='in_progress',
    )['ok'] is True

    payload = complete_local_queue_item(
        config,
        item_id='complete-item',
        commit_hash='   ',
        validation_summary='Targeted tests passed locally.',
    )

    assert payload['ok'] is False
    assert any('commit_hash is required' in warning for warning in payload['warnings'])


def test_complete_local_queue_item_requires_validation_summary(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_project_queue(config)['ok'] is True
    assert add_queue_item(
        config,
        item_id='complete-item',
        project_id='project-one',
        repo_id='repo-main',
        title='Complete item',
        description='Complete local implementation with evidence.',
        status='in_progress',
    )['ok'] is True

    payload = complete_local_queue_item(
        config,
        item_id='complete-item',
        commit_hash='abc123def',
        validation_summary='   ',
    )

    assert payload['ok'] is False
    assert any('validation_summary is required' in warning for warning in payload['warnings'])


def test_complete_local_queue_item_persists_completion_metadata(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_project_queue(config)['ok'] is True
    assert add_queue_item(
        config,
        item_id='persist-complete-item',
        project_id='project-one',
        repo_id='repo-main',
        title='Persist completion item',
        description='Persist completion metadata.',
        status='in_progress',
    )['ok'] is True
    queue_path = resolve_project_queue_path(config.repo_root, None)

    payload = complete_local_queue_item(
        config,
        item_id='persist-complete-item',
        commit_hash='abc123def',
        validation_summary='All targeted validation passed.',
        evidence_note='Smoke verified.',
        tests_run=['python -m pytest tests/test_local_project_queue.py'],
        changed_files=['src/aresforge/cli.py'],
        artifact_paths=['artifacts/evidence/complete.json'],
        completed_by='local_operator',
    )

    rendered = json.loads(queue_path.read_text(encoding='utf-8'))
    persisted = next(item for item in rendered['work_items'] if item['item_id'] == 'persist-complete-item')
    assert payload['ok'] is True
    assert persisted['status'] == 'done'
    assert persisted['completed_by'] == 'local_operator'
    assert persisted['completion_commit'] == 'abc123def'
    assert persisted['validation_summary'] == 'All targeted validation passed.'
    assert persisted['evidence_note'] == 'Smoke verified.'
    assert persisted['tests_run'] == ['python -m pytest tests/test_local_project_queue.py']
    assert persisted['changed_files'] == ['src/aresforge/cli.py']
    assert persisted['artifact_paths'] == ['artifacts/evidence/complete.json']
    assert persisted['completed_at']


def test_capture_local_queue_completion_evidence_records_evidence_without_completing(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_project_queue(config)['ok'] is True
    assert add_queue_item(
        config,
        item_id='evidence-item',
        project_id='project-one',
        repo_id='repo-main',
        title='Evidence item',
        description='Capture local evidence before closeout.',
        status='in_progress',
        priority='high',
        item_type='validation',
    )['ok'] is True

    payload = capture_local_queue_completion_evidence(
        config,
        item_id='evidence-item',
        evidence_summary='Targeted validation passed locally.',
        validation_commands=['python -m pytest tests/test_local_project_queue.py'],
        validation_results=['1 passed'],
        smoke_checks=['python -m aresforge inspect-local-project-report -> ok'],
        diff_check_result='git diff --check -> pass',
        files_changed=['src/aresforge/operator/local_project_queue.py'],
        commit_hash='abc123def',
        push_result='not pushed yet',
        operator_notes='Ready for future closeout review.',
    )

    assert payload['ok'] is True
    assert payload['local_only'] is True
    assert payload['status'] == 'in_progress'
    assert payload['closeout_eligible'] is True
    assert payload['completion_evidence']['evidence_summary'] == 'Targeted validation passed locally.'
    assert payload['completion_evidence']['validation_commands'] == ['python -m pytest tests/test_local_project_queue.py']
    assert payload['completion_evidence']['files_changed'] == ['src/aresforge/operator/local_project_queue.py']
    assert payload['completion_evidence']['captured_at']
    assert any('No queue item completion is performed' in entry for entry in payload['boundary_confirmations'])

    item_payload = inspect_queue_item(config, item_id='evidence-item')
    parsed = json.loads(item_payload['stdout'])
    persisted = parsed['item']
    assert persisted['status'] == 'in_progress'
    assert persisted['completed_at'] == ''
    assert persisted['completion_commit'] == ''
    assert persisted['priority'] == 'high'
    assert persisted['item_type'] == 'validation'
    assert persisted['completion_evidence']['commit_hash'] == 'abc123def'


def test_capture_local_queue_completion_evidence_missing_item_fails(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_project_queue(config)['ok'] is True

    payload = capture_local_queue_completion_evidence(
        config,
        item_id='missing-item',
        evidence_summary='Evidence exists.',
    )

    assert payload['ok'] is False
    assert payload['local_only'] is True
    assert payload['item_id'] == 'missing-item'
    assert payload['closeout_eligible'] is False
    assert any('Queue item not found' in warning for warning in payload['warnings'])


def test_capture_local_queue_completion_evidence_requires_meaningful_content(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_project_queue(config)['ok'] is True
    assert add_queue_item(
        config,
        item_id='empty-evidence-item',
        project_id='project-one',
        repo_id='repo-main',
        title='Empty evidence item',
        description='No evidence should fail.',
        status='in_progress',
    )['ok'] is True

    payload = capture_local_queue_completion_evidence(
        config,
        item_id='empty-evidence-item',
        evidence_summary='   ',
        validation_commands=[],
        validation_results=[],
        smoke_checks=[],
        diff_check_result='   ',
        files_changed=[],
        commit_hash='   ',
        push_result='   ',
        operator_notes='   ',
    )

    assert payload['ok'] is False
    assert payload['status'] == 'in_progress'
    assert payload['closeout_eligible'] is False
    assert any('meaningful evidence field' in warning for warning in payload['warnings'])
    item_payload = inspect_queue_item(config, item_id='empty-evidence-item')
    parsed = json.loads(item_payload['stdout'])
    assert parsed['item']['completion_evidence'] == {}


def test_capture_local_queue_completion_evidence_preserves_non_closeout_status(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_project_queue(config)['ok'] is True
    assert add_queue_item(
        config,
        item_id='proposed-evidence-item',
        project_id='project-one',
        repo_id='repo-main',
        title='Proposed evidence item',
        description='Evidence can be attached before start but not closeout eligible.',
        status='proposed',
    )['ok'] is True

    payload = capture_local_queue_completion_evidence(
        config,
        item_id='proposed-evidence-item',
        evidence_summary='Operator captured planning validation notes.',
    )

    assert payload['ok'] is True
    assert payload['status'] == 'proposed'
    assert payload['closeout_eligible'] is False
    item_payload = inspect_queue_item(config, item_id='proposed-evidence-item')
    parsed = json.loads(item_payload['stdout'])
    assert parsed['item']['status'] == 'proposed'
    assert parsed['item']['completion_evidence']['evidence_summary'] == 'Operator captured planning validation notes.'


def test_close_local_queue_item_with_evidence_transitions_to_done(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_project_queue(config)['ok'] is True
    assert add_queue_item(
        config,
        item_id='closeout-item',
        project_id='project-one',
        repo_id='repo-main',
        title='Closeout item',
        description='Close out after evidence.',
        status='in_progress',
    )['ok'] is True
    assert capture_local_queue_completion_evidence(
        config,
        item_id='closeout-item',
        evidence_summary='Validation passed locally.',
        validation_results=['python -m pytest tests/test_local_project_queue.py -> passed'],
        diff_check_result='git diff --check -> pass',
        files_changed=['src/aresforge/operator/local_project_queue.py'],
    )['ok'] is True

    payload = close_local_queue_item(
        config,
        item_id='closeout-item',
        closeout_summary='Evidence reviewed and item is ready to close.',
        closed_by='local_operator',
    )

    assert payload['ok'] is True
    assert payload['local_only'] is True
    assert payload['previous_status'] == 'in_progress'
    assert payload['status'] == 'done'
    assert payload['closed_at']
    assert payload['closed_by'] == 'local_operator'
    assert payload['closeout_summary'] == 'Evidence reviewed and item is ready to close.'
    assert any('No prompt generation or execution' in entry for entry in payload['boundary_confirmations'])

    item_payload = inspect_queue_item(config, item_id='closeout-item')
    parsed = json.loads(item_payload['stdout'])
    persisted = parsed['item']
    assert persisted['status'] == 'done'
    assert persisted['completion_evidence']['evidence_summary'] == 'Validation passed locally.'
    assert persisted['closeout_history'][0]['completion_evidence']['diff_check_result'] == 'git diff --check -> pass'


def test_close_local_queue_item_missing_item_fails(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_project_queue(config)['ok'] is True

    payload = close_local_queue_item(
        config,
        item_id='missing-closeout-item',
        closeout_summary='Close it.',
    )

    assert payload['ok'] is False
    assert payload['status'] == ''
    assert any('Queue item not found' in warning for warning in payload['warnings'])


def test_close_local_queue_item_requires_evidence(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_project_queue(config)['ok'] is True
    assert add_queue_item(
        config,
        item_id='no-evidence-closeout-item',
        project_id='project-one',
        repo_id='repo-main',
        title='No evidence item',
        description='Cannot close without evidence.',
        status='in_progress',
    )['ok'] is True

    payload = close_local_queue_item(
        config,
        item_id='no-evidence-closeout-item',
        closeout_summary='Close it.',
    )

    assert payload['ok'] is False
    assert payload['status'] == 'in_progress'
    assert any('Completion evidence is required' in warning for warning in payload['warnings'])


def test_close_local_queue_item_requires_eligible_status(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_project_queue(config)['ok'] is True
    assert add_queue_item(
        config,
        item_id='proposed-closeout-item',
        project_id='project-one',
        repo_id='repo-main',
        title='Proposed closeout item',
        description='Cannot close before start.',
        status='proposed',
    )['ok'] is True
    assert capture_local_queue_completion_evidence(
        config,
        item_id='proposed-closeout-item',
        evidence_summary='Validation notes exist.',
        validation_results=['manual validation noted'],
        diff_check_result='git diff --check -> pass',
    )['ok'] is True

    payload = close_local_queue_item(
        config,
        item_id='proposed-closeout-item',
        closeout_summary='Close it.',
    )

    assert payload['ok'] is False
    assert payload['status'] == 'proposed'
    assert any('in_progress' in warning for warning in payload['warnings'])


def test_close_local_queue_item_requires_required_evidence_fields(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_project_queue(config)['ok'] is True
    assert add_queue_item(
        config,
        item_id='partial-evidence-closeout-item',
        project_id='project-one',
        repo_id='repo-main',
        title='Partial evidence item',
        description='Cannot close with partial evidence.',
        status='in_progress',
    )['ok'] is True
    assert capture_local_queue_completion_evidence(
        config,
        item_id='partial-evidence-closeout-item',
        evidence_summary='Evidence exists but no validation result.',
    )['ok'] is True

    payload = close_local_queue_item(
        config,
        item_id='partial-evidence-closeout-item',
        closeout_summary='Close it.',
    )

    assert payload['ok'] is False
    assert payload['status'] == 'in_progress'
    assert any('evidence_summary, validation_results, and diff_check_result' in warning for warning in payload['warnings'])


def test_read_local_project_progress_rollup_counts_status_evidence_and_closeout(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_managed_project_registry(config)['ok'] is True
    assert register_managed_project(
        config,
        project_id='project-one',
        name='Project One',
        root_path=tmp_path,
        status='active',
    )['ok'] is True
    assert register_managed_repo(
        config,
        project_id='project-one',
        repo_id='repo-main',
        name='Repo Main',
        path=tmp_path,
        role='primary',
        status='active',
    )['ok'] is True
    assert set_active_project(config, project_id='project-one')['ok'] is True
    assert init_project_queue(config)['ok'] is True

    for item_id, status, item_type, assigned_agent in (
        ('ready-item', 'ready', 'task', 'coding-agent'),
        ('blocked-item', 'blocked', 'bug', 'reviewer-agent'),
        ('eligible-item', 'in_progress', 'validation', 'test-agent'),
        ('closeout-item', 'in_progress', 'documentation', 'documentation-agent'),
    ):
        assert add_queue_item(
            config,
            item_id=item_id,
            project_id='project-one',
            repo_id='repo-main',
            title=f'{item_id} title',
            description=f'{item_id} description',
            status=status,
            item_type=item_type,
            assigned_agent=assigned_agent,
        )['ok'] is True

    assert capture_local_queue_completion_evidence(
        config,
        item_id='eligible-item',
        evidence_summary='Eligible evidence.',
        validation_results=['pytest -> passed'],
        diff_check_result='git diff --check -> pass',
    )['ok'] is True
    assert capture_local_queue_completion_evidence(
        config,
        item_id='closeout-item',
        evidence_summary='Closeout evidence.',
        validation_results=['pytest -> passed'],
        diff_check_result='git diff --check -> pass',
    )['ok'] is True
    assert close_local_queue_item(
        config,
        item_id='closeout-item',
        closeout_summary='Evidence reviewed for closeout.',
    )['ok'] is True

    rollup = read_local_project_progress_rollup(config, project_id='project-one')

    assert rollup['ok'] is True
    assert rollup['local_only'] is True
    assert rollup['read_only'] is True
    assert rollup['project_id'] == 'project-one'
    assert rollup['project_name'] == 'Project One'
    assert rollup['active_project'] is True
    assert rollup['total_queue_items'] == 4
    assert rollup['items_by_status']['ready'] == 1
    assert rollup['items_by_status']['blocked'] == 1
    assert rollup['items_by_status']['in_progress'] == 1
    assert rollup['items_by_status']['done'] == 1
    assert rollup['items_by_type']['validation'] == 1
    assert rollup['items_by_lane']['test-agent'] == 1
    assert rollup['ready_item_count'] == 1
    assert rollup['blocked_item_count'] == 1
    assert rollup['in_progress_item_count'] == 1
    assert rollup['items_with_evidence_captured_count'] == 2
    assert rollup['items_eligible_for_closeout_count'] == 1
    assert rollup['closed_completed_item_count'] == 1
    assert rollup['latest_activity_timestamp']
    assert rollup['blockers'] == ['Queue item blocked-item is blocked: blocked-item title']
    assert rollup['future_routing_metadata']['implemented'] is False
    assert any('Read-only local queue' in entry for entry in rollup['boundary_confirmations'])


def test_read_local_project_progress_rollup_handles_empty_queue_state(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_managed_project_registry(config)['ok'] is True
    assert register_managed_project(
        config,
        project_id='empty-project',
        name='Empty Project',
        root_path=tmp_path,
    )['ok'] is True

    rollup = read_local_project_progress_rollup(config, project_id='empty-project')

    assert rollup['ok'] is True
    assert rollup['project_id'] == 'empty-project'
    assert rollup['total_queue_items'] == 0
    assert rollup['ready_item_count'] == 0
    assert rollup['blocked_item_count'] == 0
    assert rollup['items_with_evidence_captured_count'] == 0
    assert rollup['items_eligible_for_closeout_count'] == 0
    assert rollup['closed_completed_item_count'] == 0
    assert rollup['items_by_status']['ready'] == 0
    assert rollup['next_safe_action'] == 'Add local queue items for this project when the next milestone is ready.'
    assert any('queue not found' in warning.lower() for warning in rollup['warnings'])


def test_read_local_project_progress_rollup_missing_project_fails_when_registry_exists(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_managed_project_registry(config)['ok'] is True

    rollup = read_local_project_progress_rollup(config, project_id='missing-project')

    assert rollup['ok'] is False
    assert rollup['error'] == 'managed_project_not_found'
