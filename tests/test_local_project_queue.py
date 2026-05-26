import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.local_active_project import set_active_project
from aresforge.operator.local_project_queue import (
    add_local_queue_item,
    add_queue_item,
    init_project_queue,
    inspect_project_queue,
    inspect_queue_item,
    resolve_project_queue_path,
    update_queue_item,
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
