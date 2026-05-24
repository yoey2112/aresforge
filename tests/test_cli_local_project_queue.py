import json
from pathlib import Path

from aresforge import cli
from aresforge.config import AppConfig


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
