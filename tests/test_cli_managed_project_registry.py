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


def test_cli_managed_project_registry_flow(monkeypatch, capsys, tmp_path: Path) -> None:
    monkeypatch.setattr(cli.AppConfig, 'from_env', lambda: _config(tmp_path))

    assert cli.main(['init-managed-project-registry']) == 0
    init_payload = json.loads(capsys.readouterr().out)
    assert init_payload['ok'] is True

    assert (
        cli.main(
            [
                'register-managed-project',
                '--project-id',
                'aresforge-main',
                '--name',
                'AresForge',
                '--root-path',
                str(tmp_path),
                '--status',
                'active',
                '--default-branch',
                'main',
                '--tag',
                'control-plane',
            ]
        )
        == 0
    )
    project_payload = json.loads(capsys.readouterr().out)
    assert project_payload['ok'] is True

    assert (
        cli.main(
            [
                'register-managed-repo',
                '--project-id',
                'aresforge-main',
                '--repo-id',
                'docs',
                '--name',
                'Docs Repo',
                '--path',
                str(tmp_path / 'docs'),
                '--role',
                'docs',
                '--status',
                'active',
            ]
        )
        == 0
    )
    repo_payload = json.loads(capsys.readouterr().out)
    assert repo_payload['ok'] is True

    assert cli.main(['inspect-managed-project-registry']) == 0
    registry = json.loads(capsys.readouterr().out)
    assert registry['project_count'] == 1
    assert registry['repo_count'] == 1

    assert cli.main(['inspect-managed-project', '--project-id', 'aresforge-main']) == 0
    project = json.loads(capsys.readouterr().out)
    assert project['project']['project_id'] == 'aresforge-main'

    assert cli.main(['inspect-managed-repo', '--project-id', 'aresforge-main', '--repo-id', 'docs']) == 0
    repo = json.loads(capsys.readouterr().out)
    assert repo['repo']['repo_id'] == 'docs'


def test_cli_managed_project_registry_markdown_output(monkeypatch, capsys, tmp_path: Path) -> None:
    monkeypatch.setattr(cli.AppConfig, 'from_env', lambda: _config(tmp_path))

    assert cli.main(['init-managed-project-registry']) == 0
    _ = capsys.readouterr().out
    assert (
        cli.main(
            [
                'register-managed-project',
                '--project-id',
                'project-one',
                '--name',
                'Project One',
                '--root-path',
                str(tmp_path),
            ]
        )
        == 0
    )
    _ = capsys.readouterr().out

    assert cli.main(['inspect-managed-project-registry', '--format', 'markdown']) == 0
    assert '# Managed Project Registry' in capsys.readouterr().out
