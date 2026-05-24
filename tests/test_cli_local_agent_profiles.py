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


def test_cli_local_agent_profiles_flow(monkeypatch, capsys, tmp_path: Path) -> None:
    monkeypatch.setattr(cli.AppConfig, 'from_env', lambda: _config(tmp_path))

    assert cli.main(['init-agent-profiles']) == 0
    init_payload = json.loads(capsys.readouterr().out)
    assert init_payload['ok'] is True

    assert (
        cli.main(
            [
                'register-handoff-target',
                '--target-id',
                'human-default',
                '--name',
                'Human Default',
                '--target-type',
                'human_prompt',
                '--status',
                'active',
            ]
        )
        == 0
    )
    target_payload = json.loads(capsys.readouterr().out)
    assert target_payload['ok'] is True

    assert (
        cli.main(
            [
                'register-agent-profile',
                '--agent-id',
                'architect-a',
                '--name',
                'Architect A',
                '--role',
                'architect',
                '--execution-mode',
                'human',
                '--status',
                'active',
                '--escalation-allowed',
                'true',
                '--handoff-target-id',
                'human-default',
                '--strength',
                'planning',
                '--constraint',
                'local-only',
                '--allowed-type',
                'milestone',
            ]
        )
        == 0
    )
    agent_payload = json.loads(capsys.readouterr().out)
    assert agent_payload['ok'] is True
    assert agent_payload['agent']['agent_id'] == 'architect-a'
    assert agent_payload['agent']['escalation_allowed'] is True

    assert cli.main(['inspect-agent-profiles']) == 0
    profiles_payload = json.loads(capsys.readouterr().out)
    assert profiles_payload['agent_count'] == 1

    assert cli.main(['inspect-agent-profile', '--agent-id', 'architect-a']) == 0
    profile_payload = json.loads(capsys.readouterr().out)
    assert profile_payload['agent']['agent_id'] == 'architect-a'

    assert cli.main(['inspect-handoff-target', '--target-id', 'human-default']) == 0
    handoff_payload = json.loads(capsys.readouterr().out)
    assert handoff_payload['handoff_target']['target_id'] == 'human-default'


def test_cli_init_agent_profiles_with_defaults(monkeypatch, capsys, tmp_path: Path) -> None:
    monkeypatch.setattr(cli.AppConfig, 'from_env', lambda: _config(tmp_path))

    assert cli.main(['init-agent-profiles', '--with-defaults']) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload['ok'] is True
    assert payload['with_defaults'] is True
    assert len(payload['profiles']['agents']) >= 8


def test_cli_agent_profiles_markdown_output(monkeypatch, capsys, tmp_path: Path) -> None:
    monkeypatch.setattr(cli.AppConfig, 'from_env', lambda: _config(tmp_path))

    assert cli.main(['init-agent-profiles']) == 0
    _ = capsys.readouterr().out

    assert (
        cli.main(
            [
                'register-agent-profile',
                '--agent-id',
                'review-a',
                '--name',
                'Review A',
                '--role',
                'reviewer',
            ]
        )
        == 0
    )
    _ = capsys.readouterr().out

    assert cli.main(['inspect-agent-profiles', '--format', 'markdown']) == 0
    assert '# Local Agent Profiles' in capsys.readouterr().out

    assert cli.main(['inspect-agent-profile', '--agent-id', 'review-a', '--format', 'markdown']) == 0
    assert '# Local Agent Profile Inspection' in capsys.readouterr().out


def test_cli_escalation_allowed_parsing(monkeypatch, capsys, tmp_path: Path) -> None:
    monkeypatch.setattr(cli.AppConfig, 'from_env', lambda: _config(tmp_path))

    assert cli.main(['init-agent-profiles']) == 0
    _ = capsys.readouterr().out

    assert (
        cli.main(
            [
                'register-agent-profile',
                '--agent-id',
                'op-a',
                '--name',
                'Operator A',
                '--role',
                'operator',
                '--escalation-allowed',
                'not-bool',
            ]
        )
        == 1
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload['ok'] is False
    assert payload['error'] == 'invalid_escalation_allowed'
