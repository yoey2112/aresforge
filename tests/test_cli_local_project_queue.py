import json
from pathlib import Path

from aresforge import cli
from aresforge.config import AppConfig
from aresforge.operator.local_active_project import set_active_project
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


def test_cli_local_project_queue_flow(monkeypatch, capsys, tmp_path: Path) -> None:
    monkeypatch.setattr(cli.AppConfig, 'from_env', lambda: _config(tmp_path))

    assert cli.main(['init-project-queue']) == 0
    init_payload = json.loads(capsys.readouterr().out)
    assert init_payload['ok'] is True

    assert (
        cli.main(
            [
                'add-queue-item',
                '--item-id',
                'm33-1',
                '--project-id',
                'p1',
                '--repo-id',
                'r1',
                '--title',
                'first item',
                '--status',
                'ready',
                '--priority',
                'high',
                '--type',
                'task',
                '--tag',
                'queue',
                '--depends-on',
                'm33-0',
            ]
        )
        == 0
    )
    add_payload = json.loads(capsys.readouterr().out)
    assert add_payload['ok'] is True
    assert add_payload['item']['item_id'] == 'm33-1'

    assert (
        cli.main(
            [
                'update-queue-item',
                '--item-id',
                'm33-1',
                '--status',
                'in_progress',
                '--assigned-agent',
                'agent-alpha',
            ]
        )
        == 0
    )
    update_payload = json.loads(capsys.readouterr().out)
    assert update_payload['ok'] is True
    assert update_payload['item']['status'] == 'in_progress'
    assert update_payload['item']['assigned_agent'] == 'agent-alpha'

    assert cli.main(['inspect-project-queue']) == 0
    queue_payload = json.loads(capsys.readouterr().out)
    assert queue_payload['item_count'] == 1

    assert cli.main(['inspect-queue-item', '--item-id', 'm33-1']) == 0
    item_payload = json.loads(capsys.readouterr().out)
    assert item_payload['item']['item_id'] == 'm33-1'


def test_cli_local_project_queue_markdown_output(monkeypatch, capsys, tmp_path: Path) -> None:
    monkeypatch.setattr(cli.AppConfig, 'from_env', lambda: _config(tmp_path))

    assert cli.main(['init-project-queue']) == 0
    _ = capsys.readouterr().out
    assert (
        cli.main(
            [
                'add-queue-item',
                '--item-id',
                'm33-1',
                '--project-id',
                'p1',
                '--repo-id',
                'r1',
                '--title',
                'first item',
            ]
        )
        == 0
    )
    _ = capsys.readouterr().out

    assert cli.main(['inspect-project-queue', '--format', 'markdown']) == 0
    assert '# Local Project Queue' in capsys.readouterr().out

    assert cli.main(['inspect-queue-item', '--item-id', 'm33-1', '--format', 'markdown']) == 0
    assert '# Local Queue Item Inspection' in capsys.readouterr().out


def test_cli_add_local_queue_item_json_output(monkeypatch, capsys, tmp_path: Path) -> None:
    monkeypatch.setattr(cli.AppConfig, 'from_env', lambda: _config(tmp_path))
    config = _config(tmp_path)
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
    assert cli.main(['init-project-queue']) == 0
    _ = capsys.readouterr().out

    assert (
        cli.main(
            [
                'add-local-queue-item',
                '--title',
                'CLI add local queue item',
                '--description',
                'Validate CLI JSON output.',
                '--type',
                'feature',
                '--priority',
                'high',
                '--tags',
                'queue',
                '--depends-on',
                'future-item',
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload['ok'] is True
    assert payload['project_id'] == 'project-one'
    assert payload['repo_id'] == 'repo-main'
    assert payload['status'] == 'proposed'
    assert payload['item_id'].startswith('local-cli-add-local-queue-item')
    assert 'inspect-queue-item' in payload['next_safe_action']


def test_cli_add_local_queue_item_missing_title_validation(monkeypatch, capsys, tmp_path: Path) -> None:
    monkeypatch.setattr(cli.AppConfig, 'from_env', lambda: _config(tmp_path))

    assert cli.main(['init-project-queue']) == 0
    _ = capsys.readouterr().out
    assert cli.main(['add-local-queue-item', '--title', '   ']) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload['ok'] is False
    assert payload['error'] == 'invalid_local_queue_item_payload'


def test_cli_inspect_local_queue_item_readiness_stable_keys(monkeypatch, capsys, tmp_path: Path) -> None:
    monkeypatch.setattr(cli.AppConfig, 'from_env', lambda: _config(tmp_path))
    config = _config(tmp_path)
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
    assert cli.main(['init-project-queue']) == 0
    _ = capsys.readouterr().out
    assert (
        cli.main(
            [
                'add-queue-item',
                '--item-id',
                'ready-item',
                '--project-id',
                'project-one',
                '--repo-id',
                'repo-main',
                '--title',
                'Ready item',
                '--description',
                'Ready to start.',
                '--status',
                'ready',
            ]
        )
        == 0
    )
    _ = capsys.readouterr().out

    assert cli.main(['inspect-local-queue-item-readiness', '--item-id', 'ready-item']) == 0
    payload = json.loads(capsys.readouterr().out)
    for key in (
        'ok',
        'local_only',
        'item_id',
        'title',
        'status',
        'project_id',
        'repo_id',
        'readiness_status',
        'can_start',
        'blockers',
        'warnings',
        'missing_fields',
        'dependency_summary',
        'recommended_next_action',
        'boundary_confirmations',
    ):
        assert key in payload
    assert payload['item_id'] == 'ready-item'
    assert payload['readiness_status'] == 'ready'
