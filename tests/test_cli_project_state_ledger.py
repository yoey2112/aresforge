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


def test_cli_init_inspect_update_project_state(monkeypatch, capsys, tmp_path: Path) -> None:
    monkeypatch.setattr(cli.AppConfig, 'from_env', lambda: _config(tmp_path))

    assert cli.main(['init-project-state']) == 0
    init_payload = json.loads(capsys.readouterr().out)
    assert init_payload['ok'] is True

    assert cli.main(['inspect-project-state']) == 0
    inspect_payload = json.loads(capsys.readouterr().out)
    assert inspect_payload['state']['schema_version'] == '1.0'

    assert (
        cli.main(
            [
                'update-project-state',
                '--current-milestone',
                'M27',
                '--current-phase',
                'Implementation',
                '--current-mode',
                'local-only',
                '--validation-status',
                'pass',
                '--documentation-status',
                'pass',
                '--warning',
                'tracked locally',
            ]
        )
        == 0
    )
    update_payload = json.loads(capsys.readouterr().out)
    assert update_payload['state']['current_milestone'] == 'M27'
    assert 'tracked locally' in update_payload['state']['warnings']


def test_cli_append_and_inspect_operation_log(monkeypatch, capsys, tmp_path: Path) -> None:
    monkeypatch.setattr(cli.AppConfig, 'from_env', lambda: _config(tmp_path))
    assert cli.main(['init-project-state']) == 0
    _ = capsys.readouterr().out

    assert (
        cli.main(
            [
                'append-operation-log',
                '--event-type',
                'milestone_update',
                '--summary',
                'M27 started',
                '--details',
                '{"milestone":"M27"}',
            ]
        )
        == 0
    )
    append_payload = json.loads(capsys.readouterr().out)
    assert append_payload['entry']['event_type'] == 'milestone_update'

    assert cli.main(['inspect-operation-log', '--limit', '1']) == 0
    inspect_payload = json.loads(capsys.readouterr().out)
    assert inspect_payload['entry_count'] == 1
    assert inspect_payload['entries'][0]['summary'] == 'M27 started'


def test_cli_append_operation_log_rejects_invalid_details(monkeypatch, capsys, tmp_path: Path) -> None:
    monkeypatch.setattr(cli.AppConfig, 'from_env', lambda: _config(tmp_path))
    code = cli.main(
        [
            'append-operation-log',
            '--event-type',
            'x',
            '--summary',
            'y',
            '--details',
            '[]',
        ]
    )
    payload = json.loads(capsys.readouterr().out)
    assert code == 1
    assert payload['error'] == 'invalid_details_json'
