import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.managed_project_registry_local import (
    init_managed_project_registry,
    inspect_managed_project,
    inspect_managed_project_registry,
    inspect_managed_repo,
    register_managed_project,
    register_managed_repo,
    resolve_managed_project_registry_path,
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


def test_registry_initialization_creates_default_file_and_schema(tmp_path: Path) -> None:
    config = _config(tmp_path)
    payload = init_managed_project_registry(config)
    assert payload['ok'] is True
    registry_path = resolve_managed_project_registry_path(config.repo_root, None)
    assert registry_path.exists()
    data = json.loads(registry_path.read_text(encoding='utf-8'))
    assert data['schema_version'] == '1.0'
    assert data['projects'] == []


def test_registry_initialization_refuses_overwrite_without_force(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_managed_project_registry(config)['ok'] is True
    second = init_managed_project_registry(config)
    assert second['ok'] is False
    assert second['error'] == 'managed_project_registry_exists'


def test_project_registration_and_update_are_idempotent(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_managed_project_registry(config)['ok'] is True

    first = register_managed_project(
        config,
        project_id='aresforge-main',
        name='AresForge',
        root_path=str(tmp_path),
        status='active',
        default_branch='main',
        tags=['control-plane'],
    )
    assert first['ok'] is True
    assert first['created'] is True

    second = register_managed_project(
        config,
        project_id='aresforge-main',
        name='AresForge Core',
        root_path=str(tmp_path),
        description='Updated description',
        status='paused',
        tags=['control-plane', 'local-first'],
    )
    assert second['ok'] is True
    assert second['created'] is False

    inspected = inspect_managed_project_registry(config)
    assert inspected['ok'] is True
    payload = inspected['payload']
    assert payload['project_count'] == 1
    project = payload['projects'][0]
    assert project['name'] == 'AresForge Core'
    assert project['status'] == 'paused'
    assert project['tags'] == ['control-plane', 'local-first']


def test_repo_registration_and_update_are_idempotent(tmp_path: Path) -> None:
    config = _config(tmp_path)
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

    first = register_managed_repo(
        config,
        project_id='project-one',
        repo_id='repo-main',
        name='Main Repo',
        path=str(tmp_path),
        role='primary',
        status='active',
    )
    assert first['ok'] is True
    assert first['created'] is True

    second = register_managed_repo(
        config,
        project_id='project-one',
        repo_id='repo-main',
        name='Main Repository',
        path=str(tmp_path),
        role='automation',
        status='paused',
        tags=['bot'],
    )
    assert second['ok'] is True
    assert second['created'] is False

    inspected_project = inspect_managed_project(config, project_id='project-one')
    assert inspected_project['ok'] is True
    project = inspected_project['payload']['project']
    assert len(project['repos']) == 1
    repo = project['repos'][0]
    assert repo['name'] == 'Main Repository'
    assert repo['role'] == 'automation'
    assert repo['status'] == 'paused'


def test_invalid_status_and_role_validation(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_managed_project_registry(config)['ok'] is True

    invalid_project = register_managed_project(
        config,
        project_id='x',
        name='X',
        root_path=str(tmp_path),
        status='invalid-status',
    )
    assert invalid_project['ok'] is False
    assert invalid_project['error'] == 'invalid_project_status'

    assert (
        register_managed_project(
            config,
            project_id='x',
            name='X',
            root_path=str(tmp_path),
        )['ok']
        is True
    )

    invalid_repo_status = register_managed_repo(
        config,
        project_id='x',
        repo_id='r',
        name='R',
        path=str(tmp_path),
        status='bad',
    )
    assert invalid_repo_status['ok'] is False
    assert invalid_repo_status['error'] == 'invalid_repo_status'

    invalid_repo_role = register_managed_repo(
        config,
        project_id='x',
        repo_id='r',
        name='R',
        path=str(tmp_path),
        role='bad-role',
    )
    assert invalid_repo_role['ok'] is False
    assert invalid_repo_role['error'] == 'invalid_repo_role'


def test_register_repo_fails_when_project_missing(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_managed_project_registry(config)['ok'] is True
    payload = register_managed_repo(
        config,
        project_id='missing',
        repo_id='repo-one',
        name='Repo One',
        path=str(tmp_path),
    )
    assert payload['ok'] is False
    assert payload['error'] == 'managed_project_not_found'


def test_registry_project_and_repo_inspection(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_managed_project_registry(config)['ok'] is True
    assert (
        register_managed_project(
            config,
            project_id='aresforge-main',
            name='AresForge',
            root_path=str(tmp_path),
        )['ok']
        is True
    )
    assert (
        register_managed_repo(
            config,
            project_id='aresforge-main',
            repo_id='docs',
            name='Docs',
            path=str(tmp_path / 'docs'),
            role='docs',
            status='active',
        )['ok']
        is True
    )

    registry_json = inspect_managed_project_registry(config)
    assert registry_json['ok'] is True
    assert registry_json['format'] == 'json'
    parsed = json.loads(registry_json['stdout'])
    assert parsed['project_count'] == 1
    assert parsed['repo_count'] == 1

    project_markdown = inspect_managed_project(
        config,
        project_id='aresforge-main',
        output_format='markdown',
    )
    assert project_markdown['ok'] is True
    assert '# Managed Project Inspection' in project_markdown['stdout']

    repo_markdown = inspect_managed_repo(
        config,
        project_id='aresforge-main',
        repo_id='docs',
        output_format='markdown',
    )
    assert repo_markdown['ok'] is True
    assert '# Managed Repo Inspection' in repo_markdown['stdout']
