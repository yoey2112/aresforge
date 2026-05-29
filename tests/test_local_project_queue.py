import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.local_active_project import set_active_project
from aresforge.operator.local_project_queue import (
    add_local_queue_item,
    add_queue_item,
    capture_local_queue_completion_evidence,
    close_local_queue_item,
    complete_local_queue_item,
    generate_local_queue_item_codex_prompt,
    generate_local_queue_prompt_pack,
    init_project_queue,
    inspect_local_queue_item_readiness,
    inspect_project_queue,
    inspect_queue_item,
    read_local_project_progress_rollup,
    resolve_project_queue_path,
    start_local_queue_item,
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
    assert 'Agent Prompt Pack (Local-Only)' in payload['prompt_pack']
    assert 'Final response format:' in payload['prompt_pack']


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
