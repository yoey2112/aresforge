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


def test_cli_register_project_and_repo_with_github_fields(monkeypatch, capsys, tmp_path: Path) -> None:
    monkeypatch.setattr(cli.AppConfig, 'from_env', lambda: _config(tmp_path))

    assert cli.main(['init-managed-project-registry']) == 0
    _ = capsys.readouterr().out

    assert (
        cli.main(
            [
                'register-managed-project',
                '--project-id',
                'p1',
                '--name',
                'Project One',
                '--root-path',
                str(tmp_path),
                '--github-owner',
                'example-org',
                '--github-repo',
                'sample-repo',
                '--github-default-branch',
                'main',
            ]
        )
        == 0
    )
    project_payload = json.loads(capsys.readouterr().out)
    assert project_payload['ok'] is True
    assert project_payload['project']['github_url'] == 'https://github.com/example-org/sample-repo'

    non_git_dir = tmp_path / 'non-git-repo-dir'
    non_git_dir.mkdir(parents=True, exist_ok=True)
    assert (
        cli.main(
            [
                'register-managed-repo',
                '--project-id',
                'p1',
                '--repo-id',
                'r1',
                '--name',
                'Repo One',
                '--path',
                str(non_git_dir),
                '--role',
                'primary',
                '--github-url',
                'https://github.com/example-org/sample-repo.git',
                '--inspect-local-git',
            ]
        )
        == 0
    )
    repo_payload = json.loads(capsys.readouterr().out)
    assert repo_payload['ok'] is True
    assert repo_payload['repo']['github_owner'] == 'example-org'
    assert repo_payload['repo']['github_repo'] == 'sample-repo'
    assert repo_payload['warnings']


def test_cli_inspect_managed_repo_github_link_json_and_markdown(monkeypatch, capsys, tmp_path: Path) -> None:
    monkeypatch.setattr(cli.AppConfig, 'from_env', lambda: _config(tmp_path))

    assert cli.main(['init-managed-project-registry']) == 0
    _ = capsys.readouterr().out
    assert (
        cli.main(
            [
                'register-managed-project',
                '--project-id',
                'p1',
                '--name',
                'Project One',
                '--root-path',
                str(tmp_path),
            ]
        )
        == 0
    )
    _ = capsys.readouterr().out

    non_git_dir = tmp_path / 'non-git-repo-dir'
    non_git_dir.mkdir(parents=True, exist_ok=True)
    assert (
        cli.main(
            [
                'register-managed-repo',
                '--project-id',
                'p1',
                '--repo-id',
                'r1',
                '--name',
                'Repo One',
                '--path',
                str(non_git_dir),
                '--github-owner',
                'example-org',
                '--github-repo',
                'sample-repo',
            ]
        )
        == 0
    )
    _ = capsys.readouterr().out

    assert (
        cli.main(
            [
                'inspect-managed-repo-github-link',
                '--project-id',
                'p1',
                '--repo-id',
                'r1',
                '--inspect-local-git',
                '--format',
                'json',
            ]
        )
        == 0
    )
    json_payload = json.loads(capsys.readouterr().out)
    assert json_payload['project_id'] == 'p1'
    assert json_payload['repo_id'] == 'r1'
    assert 'github_connection_status' in json_payload
    assert isinstance(json_payload['warnings'], list)

    assert (
        cli.main(
            [
                'inspect-managed-repo-github-link',
                '--project-id',
                'p1',
                '--repo-id',
                'r1',
                '--format',
                'markdown',
            ]
        )
        == 0
    )
    markdown_output = capsys.readouterr().out
    assert '# Managed Repo GitHub Link Inspection' in markdown_output
