import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.local_project_queue import add_queue_item, init_project_queue
from aresforge.operator.operator_autonomy_configuration_profile import (
    DEFAULT_AUTONOMY_PROFILE,
    inspect_autonomy_profile,
)


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


def _seed_queue(config: AppConfig) -> None:
    assert init_project_queue(config)["ok"] is True
    assert add_queue_item(
        config,
        item_id="m157-run-replay-and-audit-trail",
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M157 dependency",
        status="done",
        priority="high",
        item_type="orchestration",
    )["ok"] is True
    assert add_queue_item(
        config,
        item_id="m158-operator-autonomy-configuration-profile",
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M158 Operator Autonomy Configuration Profile",
        status="ready",
        priority="high",
        item_type="orchestration",
        dependencies=["m157-run-replay-and-audit-trail"],
    )["ok"] is True


def test_inspect_autonomy_profile_defaults_to_locked_down_safe_deny(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)

    result = inspect_autonomy_profile(config, project_id="aresforge")
    payload = result["payload"]

    assert result["ok"] is True
    assert payload["record_type"] == "operator_autonomy_configuration_profile_v1"
    assert payload["project_id"] == "aresforge"
    assert payload["autonomy_profile"] == DEFAULT_AUTONOMY_PROFILE
    assert payload["default_behavior"] == "safe_deny"
    assert payload["blocked"] is False
    assert payload["machine_gates_passed"] is True
    assert payload["machine_gates_checked"][0]["gate_profile"] == "operator_autonomy_profile"
    assert "locked_down" in payload["available_autonomy_profiles"]
    assert "experimental_full_local" in payload["available_autonomy_profiles"]
    assert payload["mutation_performed"] is False
    assert payload["queue_mutation_performed"] is False
    assert payload["codex_execution_performed"] is False
    assert payload["model_execution_performed"] is False
    assert payload["github_execution_performed"] is False
    assert payload["patch_application_performed"] is False
    assert payload["local_only"] is True

    selected = payload["selected_profile"]
    controls = {control["capability_id"]: control["status"] for control in selected["capability_controls"]}
    assert controls["local_read_inspection"] == "enabled"
    assert controls["codex_low_risk_execution"] == "blocked"
    assert controls["github_issue_sync"] == "blocked"
    assert controls["source_patch_application"] == "blocked"


def test_explicit_profiles_are_inspectable_with_enabled_and_dry_run_controls(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)

    result = inspect_autonomy_profile(
        config,
        project_id="aresforge",
        autonomy_profile="codex_low_risk_enabled",
    )
    payload = result["payload"]
    controls = {
        control["capability_id"]: control
        for control in payload["selected_profile"]["capability_controls"]
    }

    assert result["ok"] is True
    assert payload["autonomy_profile"] == "codex_low_risk_enabled"
    assert controls["codex_low_risk_execution"]["status"] == "enabled"
    assert controls["codex_dry_run"]["status"] == "dry_run_only"
    assert controls["github_issue_sync"]["status"] == "blocked"
    assert controls["source_patch_application"]["status"] == "blocked"
    assert payload["selected_profile"]["required_machine_gate_profiles"] == [
        "codex_dispatch",
        "source_patch_apply_dry_run",
    ]
    assert payload["selected_profile"]["capability_status_counts"]["enabled"] >= 1
    assert payload["selected_profile"]["capability_status_counts"]["dry_run_only"] >= 1


def test_unknown_autonomy_profile_blocks_without_execution(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)

    result = inspect_autonomy_profile(
        config,
        project_id="aresforge",
        autonomy_profile="future_unreviewed_profile",
    )
    payload = result["payload"]

    assert result["ok"] is False
    assert payload["status"] == "blocked"
    assert payload["blocked"] is True
    assert any("Unknown autonomy profile" in reason for reason in payload["blocked_reasons"])
    assert payload["mutation_performed"] is False
    assert payload["codex_execution_performed"] is False
    assert payload["github_execution_performed"] is False


def test_output_path_writes_local_artifact_and_refuses_overwrite(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    output = tmp_path / ".aresforge" / "autonomy_profiles" / "profile.json"

    first = inspect_autonomy_profile(config, output=output)
    second = inspect_autonomy_profile(config, output=output)

    assert first["ok"] is True
    written = json.loads(output.read_text(encoding="utf-8"))
    assert written["artifacts_created"] == [str(output)]
    assert second["ok"] is False
    assert second["payload"]["blocked"] is True
    assert any("Output file already exists" in reason for reason in second["payload"]["blocked_reasons"])
