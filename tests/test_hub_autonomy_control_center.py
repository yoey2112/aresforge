import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.hub.api import get_hub_autonomy_control_center_data
from aresforge.operator.durable_orchestration_run_store import append_orchestration_run_record
from aresforge.operator.hub_autonomy_control_center import inspect_hub_autonomy_control_center_data
from aresforge.operator.local_project_queue import add_queue_item, init_project_queue


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
        item_id="m166-pull-request-draft-summary-generator",
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M166 Pull Request Draft Summary Generator",
        description="Upstream dependency.",
        status="done",
        priority="high",
        item_type="sync",
        tags=["milestone:m166"],
        source="unit-test",
    )["ok"] is True
    assert add_queue_item(
        config,
        item_id="m167-hub-autonomy-control-center-v1",
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M167 Hub Autonomy Control Center v1",
        description="Surface autonomy status and safe next actions.",
        status="ready",
        priority="high",
        item_type="dashboard",
        tags=["milestone:m167"],
        dependencies=["m166-pull-request-draft-summary-generator"],
        source="unit-test",
    )["ok"] is True


def _seed_artifacts(config: AppConfig) -> None:
    evidence = config.repo_root / ".aresforge" / "codex_loop_validation_evidence" / "m167-hub-a-center-v1" / "20260602T000000Z"
    evidence.mkdir(parents=True, exist_ok=True)
    (evidence / "codex-loop-validation-evidence-bundle.json").write_text(
        json.dumps(
            {
                "record_type": "codex_loop_validation_evidence_bundle_v1",
                "artifact_type": "codex_loop_validation_evidence_bundle_v1",
                "project_id": "aresforge",
                "item_id": "m167-hub-autonomy-control-center-v1",
                "run_id": "run-m167",
                "status": "dry_run_completed",
                "blocked": False,
                "blocked_reasons": [],
                "machine_gates_passed": True,
                "github_execution_performed": False,
                "codex_execution_performed": False,
                "model_execution_performed": False,
                "patch_application_performed": False,
                "local_only": True,
                "next_safe_action": "Review evidence.",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    pr_root = config.repo_root / ".aresforge" / "pr_draft_summaries"
    pr_root.mkdir(parents=True, exist_ok=True)
    (pr_root / "m167.json").write_text(
        json.dumps(
            {
                "record_type": "pull_request_draft_summary_generator_v1",
                "artifact_type": "pull_request_draft_summary_generator_v1",
                "project_id": "aresforge",
                "item_id": "m167-hub-autonomy-control-center-v1",
                "status": "draft_summary_created",
                "blocked": False,
                "blocked_reasons": [],
                "machine_gates_passed": True,
                "github_execution_performed": False,
                "codex_execution_performed": False,
                "model_execution_performed": False,
                "patch_application_performed": False,
                "local_only": True,
                "next_safe_action": "Review PR draft.",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _seed_run_store(config: AppConfig) -> None:
    result = append_orchestration_run_record(
        config,
        record={
            "record_type": "orchestration_run_history_record",
            "project_id": "aresforge",
            "item_id": "m167-hub-autonomy-control-center-v1",
            "run_id": "run-m167",
            "status": "completed",
            "blocked": False,
            "blocked_reasons": [],
            "warnings": [],
            "machine_gates_checked": [{"gate_profile": "read_only_agent", "passed": True}],
            "machine_gates_passed": True,
            "artifacts_created": [],
            "mutation_performed": False,
            "queue_mutation_performed": False,
            "external_execution_performed": False,
            "codex_execution_performed": False,
            "model_execution_performed": False,
            "github_execution_performed": False,
            "patch_application_performed": False,
            "local_only": True,
            "next_safe_action": "Review completed run artifacts.",
        },
    )
    assert result["ok"] is True


def test_control_center_composes_autonomy_runs_evidence_github_and_gates(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    _seed_artifacts(config)
    _seed_run_store(config)

    payload = inspect_hub_autonomy_control_center_data(config, project_id="aresforge")["payload"]

    assert payload["record_type"] == "hub_autonomy_control_center_v1"
    assert payload["artifact_type"] == "hub_autonomy_control_center_v1"
    assert payload["project_id"] == "aresforge"
    assert payload["item_id"] == "m167-hub-autonomy-control-center-v1"
    assert payload["status"] == "control_center_ready"
    assert payload["blocked"] is False
    assert payload["machine_gates_passed"] is True
    assert payload["autonomy_profile"] == "github_sync_dry_run"
    assert payload["run_store_status"]["project_run_count"] == 1
    assert payload["orchestration_runs"][0]["run_id"] == "run-m167"
    assert payload["evidence_bundles"]
    assert payload["pr_draft_summaries"]
    assert payload["github_sync_status"]["mutation_allowed"] is False
    assert payload["issue_closure_recommendations"]["issue_closure_allowed"] is False
    assert payload["unsafe_actions_available"] is False
    assert payload["mutation_performed"] is False
    assert payload["queue_mutation_performed"] is False
    assert payload["codex_execution_performed"] is False
    assert payload["model_execution_performed"] is False
    assert payload["github_execution_performed"] is False
    assert payload["patch_application_performed"] is False
    assert payload["local_only"] is True
    assert payload["next_safe_actions"]


def test_control_center_output_path_writes_local_artifact(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    output = tmp_path / ".aresforge" / "hub_autonomy" / "control-center.json"

    result = inspect_hub_autonomy_control_center_data(config, project_id="aresforge", output=output)
    written = json.loads(output.read_text(encoding="utf-8"))

    assert result["ok"] is True
    assert result["wrote_output_file"] is True
    assert written["artifact_type"] == "hub_autonomy_control_center_v1"
    assert written["artifacts_created"] == [str(output)]


def test_hub_api_exposes_autonomy_control_center(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)

    payload = get_hub_autonomy_control_center_data(config, {"project_id": "aresforge"})

    assert payload["ok"] is True
    assert payload["record_type"] == "hub_autonomy_control_center_v1"
    assert payload["hub_visibility"]["api_endpoint"] == "/api/autonomy/control-center"
    assert payload["github_execution_performed"] is False
    assert payload["local_only"] is True
