import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.local_project_state import (
    append_operation_log,
    init_project_state,
    inspect_operation_log,
    inspect_project_state,
    resolve_project_state_path,
    update_project_state,
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


def test_init_inspect_and_update_project_state(tmp_path: Path) -> None:
    config = _config(tmp_path)
    init_payload = init_project_state(config)
    assert init_payload['ok'] is True

    inspect_payload = inspect_project_state(config)
    assert inspect_payload['ok'] is True
    assert inspect_payload['state']['schema_version'] == '1.0'

    updated = update_project_state(
        config,
        current_milestone='M27',
        current_phase='Implementation',
        current_mode='local-only',
        validation_status='pass',
        documentation_status='in_progress',
        warnings_to_add=['state ledger initialized'],
    )
    assert updated['ok'] is True
    assert updated['state']['current_milestone'] == 'M27'
    assert updated['state']['current_phase'] == 'Implementation'
    assert updated['state']['current_mode'] == 'local-only'
    assert updated['state']['validation_status'] == 'pass'
    assert updated['state']['documentation_status'] == 'in_progress'
    assert 'state ledger initialized' in updated['state']['warnings']


def test_init_project_state_refuses_overwrite_without_force(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_project_state(config)['ok'] is True
    second = init_project_state(config)
    assert second['ok'] is False
    assert second['error'] == 'project_state_exists'


def test_operation_log_append_and_inspect_with_newest_limit(tmp_path: Path) -> None:
    config = _config(tmp_path)
    init_project_state(config)

    append_operation_log(
        config,
        state_path=None,
        event_type='milestone_update',
        summary='M27 started',
        details={'milestone': 'M27'},
    )
    append_operation_log(
        config,
        state_path=None,
        event_type='validation',
        summary='targeted tests pass',
        details={'command': 'pytest -k m27'},
    )

    full = inspect_operation_log(config, state_path=None, limit=None)
    assert full['ok'] is True
    assert full['entry_count'] == 2

    limited = inspect_operation_log(config, state_path=None, limit=1)
    assert limited['ok'] is True
    assert limited['entry_count'] == 1
    assert limited['entries'][0]['event_type'] == 'validation'


def test_inspect_project_state_missing_file_returns_clear_error(tmp_path: Path) -> None:
    config = _config(tmp_path)
    payload = inspect_project_state(config)
    assert payload['ok'] is False
    assert payload['error'] == 'project_state_not_found'


def test_inspect_operation_log_missing_file_returns_clear_error(tmp_path: Path) -> None:
    config = _config(tmp_path)
    payload = inspect_operation_log(config, state_path=None, limit=None)
    assert payload['ok'] is False
    assert payload['error'] == 'operation_log_not_found'


def test_custom_state_path_is_supported(tmp_path: Path) -> None:
    config = _config(tmp_path)
    custom = tmp_path / '.aresforge' / 'state' / 'alt_project_state.json'
    init_project_state(config, path=custom)
    payload = inspect_project_state(config, path=custom)
    assert payload['ok'] is True
    assert Path(payload['path']) == custom

    resolved = resolve_project_state_path(config.repo_root, custom)
    assert resolved == custom
    raw = json.loads(custom.read_text(encoding='utf-8'))
    assert raw['project_name'] == tmp_path.name
