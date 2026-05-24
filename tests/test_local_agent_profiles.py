import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.local_agent_profiles import (
    init_agent_profiles,
    inspect_agent_profile,
    inspect_agent_profiles,
    inspect_handoff_target,
    register_agent_profile,
    register_handoff_target,
    resolve_agent_profiles_path,
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


def test_agent_profiles_initialization_creates_default_file_and_schema(tmp_path: Path) -> None:
    config = _config(tmp_path)
    payload = init_agent_profiles(config)
    assert payload['ok'] is True
    profiles_path = resolve_agent_profiles_path(config.repo_root, None)
    assert profiles_path.exists()
    data = json.loads(profiles_path.read_text(encoding='utf-8'))
    assert data['schema_version'] == '1.0'
    assert data['agents'] == []
    assert data['handoff_targets'] == []


def test_agent_profiles_initialization_refuses_overwrite_without_force(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_agent_profiles(config)['ok'] is True
    second = init_agent_profiles(config)
    assert second['ok'] is False
    assert second['error'] == 'agent_profiles_exists'


def test_agent_profiles_initialization_with_defaults(tmp_path: Path) -> None:
    config = _config(tmp_path)
    payload = init_agent_profiles(config, with_defaults=True)
    assert payload['ok'] is True
    data = payload['profiles']
    assert len(data['agents']) >= 8
    assert len(data['handoff_targets']) >= 4


def test_register_agent_profile(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_agent_profiles(config)['ok'] is True
    payload = register_agent_profile(
        config,
        agent_id='architect-a',
        name='Architect A',
        role='architect',
        execution_mode='human',
        status='active',
    )
    assert payload['ok'] is True
    assert payload['created'] is True
    assert payload['agent']['agent_id'] == 'architect-a'


def test_register_agent_profile_is_idempotent_and_updates_existing(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_agent_profiles(config)['ok'] is True
    assert (
        register_agent_profile(
            config,
            agent_id='impl-a',
            name='Implementer A',
            role='implementer',
            execution_mode='codex',
            status='active',
        )['ok']
        is True
    )
    payload = register_agent_profile(
        config,
        agent_id='impl-a',
        name='Implementer Updated',
        role='implementer',
        execution_mode='scripted',
        status='paused',
    )
    assert payload['ok'] is True
    assert payload['created'] is False
    assert payload['agent']['name'] == 'Implementer Updated'
    assert payload['agent']['execution_mode'] == 'scripted'
    assert payload['agent']['status'] == 'paused'


def test_register_handoff_target(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_agent_profiles(config)['ok'] is True
    payload = register_handoff_target(
        config,
        target_id='target-a',
        name='Target A',
        target_type='markdown_packet',
        status='active',
    )
    assert payload['ok'] is True
    assert payload['created'] is True
    assert payload['handoff_target']['target_id'] == 'target-a'


def test_register_handoff_target_is_idempotent_and_updates_existing(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_agent_profiles(config)['ok'] is True
    assert (
        register_handoff_target(
            config,
            target_id='target-a',
            name='Target A',
            target_type='markdown_packet',
            status='active',
        )['ok']
        is True
    )
    payload = register_handoff_target(
        config,
        target_id='target-a',
        name='Target Updated',
        target_type='json_packet',
        status='paused',
    )
    assert payload['ok'] is True
    assert payload['created'] is False
    assert payload['handoff_target']['name'] == 'Target Updated'
    assert payload['handoff_target']['target_type'] == 'json_packet'
    assert payload['handoff_target']['status'] == 'paused'


def test_invalid_role_validation(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_agent_profiles(config)['ok'] is True
    payload = register_agent_profile(
        config,
        agent_id='x',
        name='X',
        role='invalid-role',
    )
    assert payload['ok'] is False
    assert payload['error'] == 'invalid_agent_role'


def test_invalid_execution_mode_validation(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_agent_profiles(config)['ok'] is True
    payload = register_agent_profile(
        config,
        agent_id='x',
        name='X',
        role='operator',
        execution_mode='invalid-mode',
    )
    assert payload['ok'] is False
    assert payload['error'] == 'invalid_execution_mode'


def test_invalid_target_type_validation(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_agent_profiles(config)['ok'] is True
    payload = register_handoff_target(
        config,
        target_id='x',
        name='X',
        target_type='invalid-type',
    )
    assert payload['ok'] is False
    assert payload['error'] == 'invalid_handoff_target_type'


def test_invalid_status_validation(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_agent_profiles(config)['ok'] is True
    payload = register_agent_profile(
        config,
        agent_id='x',
        name='X',
        role='operator',
        status='invalid-status',
    )
    assert payload['ok'] is False
    assert payload['error'] == 'invalid_agent_profile_status'


def test_missing_target_warning_when_agent_references_unknown_target(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_agent_profiles(config)['ok'] is True
    payload = register_agent_profile(
        config,
        agent_id='impl-x',
        name='Implementer X',
        role='implementer',
        handoff_target_id='missing-target',
    )
    assert payload['ok'] is True
    assert any('was not found in handoff_targets' in warning for warning in payload['warnings'])


def test_inspect_profiles_with_filters(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_agent_profiles(config)['ok'] is True
    assert (
        register_agent_profile(
            config,
            agent_id='a1',
            name='A1',
            role='implementer',
            execution_mode='codex',
            status='active',
        )['ok']
        is True
    )
    assert (
        register_agent_profile(
            config,
            agent_id='a2',
            name='A2',
            role='tester',
            execution_mode='scripted',
            status='paused',
        )['ok']
        is True
    )
    payload = inspect_agent_profiles(
        config,
        role='implementer',
        execution_mode='codex',
        status='active',
    )
    assert payload['ok'] is True
    parsed = json.loads(payload['stdout'])
    assert parsed['agent_count'] == 1
    assert parsed['agents'][0]['agent_id'] == 'a1'


def test_inspect_single_profile(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_agent_profiles(config)['ok'] is True
    assert (
        register_agent_profile(
            config,
            agent_id='a1',
            name='A1',
            role='operator',
        )['ok']
        is True
    )
    payload = inspect_agent_profile(config, agent_id='a1')
    assert payload['ok'] is True
    parsed = json.loads(payload['stdout'])
    assert parsed['agent']['agent_id'] == 'a1'


def test_inspect_handoff_target(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_agent_profiles(config)['ok'] is True
    assert (
        register_handoff_target(
            config,
            target_id='t1',
            name='T1',
            target_type='markdown_packet',
        )['ok']
        is True
    )
    payload = inspect_handoff_target(config, target_id='t1')
    assert payload['ok'] is True
    parsed = json.loads(payload['stdout'])
    assert parsed['handoff_target']['target_id'] == 't1'
