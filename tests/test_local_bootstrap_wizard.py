import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.local_bootstrap_wizard import apply_bootstrap, inspect_bootstrap_status, plan_bootstrap
from aresforge.operator.local_agent_profiles import resolve_agent_profiles_path
from aresforge.operator.local_project_queue import resolve_project_queue_path
from aresforge.operator.local_project_state import resolve_project_state_path
from aresforge.operator.managed_project_registry_local import resolve_managed_project_registry_path


def _config(tmp_path: Path) -> AppConfig:
    artifact_root = tmp_path / "artifacts"
    return AppConfig(
        repo_root=tmp_path,
        db_host="127.0.0.1",
        db_port=5433,
        db_name="aresforge",
        db_user="aresforge",
        db_password="aresforge",
        ollama_base_url="http://127.0.0.1:11434",
        ollama_model="qwen2.5:32b",
        artifact_root=artifact_root,
        prompts_dir=artifact_root / "prompts" / "generated",
        evidence_dir=artifact_root / "evidence" / "generated",
        codex_handoffs_dir=artifact_root / "codex_handoffs" / "generated",
        github_owner="local",
        github_repo="aresforge",
    )


def test_status_with_no_files_reports_missing_and_not_ready(tmp_path: Path) -> None:
    config = _config(tmp_path)
    payload = inspect_bootstrap_status(config)

    assert payload["ok"] is True
    assert payload["bootstrap_ready"] is False
    assert sorted(payload["missing_files"]) == [
        "agent_profiles",
        "managed_project_registry",
        "project_queue",
        "project_state",
    ]


def test_plan_with_no_files_contains_expected_actions(tmp_path: Path) -> None:
    config = _config(tmp_path)
    planned = plan_bootstrap(config, output_format="json")

    assert planned["ok"] is True
    parsed = planned["payload"]
    action_ids = [item["id"] for item in parsed["actions"]]
    assert "init_project_state" in action_ids
    assert "init_managed_project_registry" in action_ids
    assert "register_aresforge_project" in action_ids
    assert "register_aresforge_repo" in action_ids
    assert "init_project_queue" in action_ids
    assert "init_agent_profiles" in action_ids


def test_apply_creates_missing_files_and_seeds_aresforge(tmp_path: Path) -> None:
    config = _config(tmp_path)
    result = apply_bootstrap(config, output_format="json")

    assert result["ok"] is True
    payload = result["payload"]
    assert payload["bootstrap_ready"] is True
    assert resolve_project_state_path(tmp_path, None).exists()
    assert resolve_managed_project_registry_path(tmp_path, None).exists()
    assert resolve_project_queue_path(tmp_path, None).exists()
    assert resolve_agent_profiles_path(tmp_path, None).exists()
    assert "aresforge" in payload["seeded_projects"]
    assert "aresforge" in payload["seeded_repos"]


def test_apply_seeds_default_agents_when_missing(tmp_path: Path) -> None:
    config = _config(tmp_path)
    result = apply_bootstrap(config, output_format="json")

    assert result["ok"] is True
    payload = result["payload"]
    assert payload["seeded_agents"]
    assert payload["seeded_handoff_targets"]


def test_apply_optionally_seeds_sample_queue_items(tmp_path: Path) -> None:
    config = _config(tmp_path)
    result = apply_bootstrap(config, seed_sample_work=True, output_format="json")

    assert result["ok"] is True
    payload = result["payload"]
    assert "m43-hub-stabilization" in payload["seeded_queue_items"]
    assert "m44-controlled-execution-gates" in payload["seeded_queue_items"]


def test_apply_is_idempotent_when_run_twice(tmp_path: Path) -> None:
    config = _config(tmp_path)
    first = apply_bootstrap(config, output_format="json")
    second = apply_bootstrap(config, output_format="json")

    assert first["ok"] is True
    assert second["ok"] is True
    assert second["payload"]["bootstrap_ready"] is True
    assert second["payload"]["already_existing_actions"]


def test_force_mode_does_not_crash(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert apply_bootstrap(config, output_format="json")["ok"] is True
    forced = apply_bootstrap(config, force=True, output_format="json")

    assert forced["ok"] is True
    assert forced["payload"]["force"] is True


def test_plan_markdown_rendering_supported(tmp_path: Path) -> None:
    config = _config(tmp_path)
    payload = plan_bootstrap(config, output_format="markdown")

    assert payload["ok"] is True
    assert payload["format"] == "markdown"
    assert "# Local Bootstrap Plan" in payload["stdout"]


def test_apply_output_can_be_decoded_from_stdout_json(tmp_path: Path) -> None:
    config = _config(tmp_path)
    payload = apply_bootstrap(config, output_format="json")

    decoded = json.loads(payload["stdout"])
    assert decoded["command"] == "apply-bootstrap"
    assert decoded["local_only"] is True
