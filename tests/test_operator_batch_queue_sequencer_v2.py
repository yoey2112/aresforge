from __future__ import annotations

import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.local_project_queue import add_queue_item, complete_local_queue_item, init_project_queue
from aresforge.operator.managed_project_registry_local import (
    init_managed_project_registry,
    register_managed_project,
    register_managed_repo,
)
from aresforge.operator.operator_batch_queue_sequencer_v2 import plan_operator_batch_v2


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


def _seed_project(config: AppConfig, tmp_path: Path) -> None:
    assert init_managed_project_registry(config)["ok"] is True
    assert register_managed_project(
        config,
        project_id="aresforge",
        name="AresForge",
        root_path=tmp_path,
        primary_repo_id="aresforge-main",
    )["ok"] is True
    assert register_managed_repo(
        config,
        project_id="aresforge",
        repo_id="aresforge-main",
        name="AresForge Main",
        path=tmp_path,
        role="primary",
    )["ok"] is True
    assert init_project_queue(config)["ok"] is True


def _add_item(config: AppConfig, item_id: str, *, status: str = "proposed", **overrides: object) -> None:
    payload = {
        "item_id": item_id,
        "project_id": "aresforge",
        "repo_id": "aresforge-main",
        "title": item_id.replace("-", " ").title(),
        "description": "Local queue item.",
        "status": status,
    }
    payload.update(overrides)
    assert add_queue_item(config, **payload)["ok"] is True


def _write_artifact(config: AppConfig, item_id: str, artifact_type: str = "local_llm_advisory_request") -> None:
    target = config.repo_root / "artifacts" / "local_llm_advisory" / "requests" / f"{item_id}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(
            {
                "artifact_type": artifact_type,
                "item_id": item_id,
                "project_id": "aresforge",
                "local_only": True,
                "execution_allowed": False,
            }
        ),
        encoding="utf-8",
    )


def _write_approval(config: AppConfig, item_id: str, status: str = "approved_for_manual_handoff") -> None:
    target = config.repo_root / ".aresforge" / "dispatch_approval_gates.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(
            {
                "schema_version": "m101.1",
                "approval_gates": [
                    {
                        "approval_id": f"approval-{item_id}",
                        "item_id": item_id,
                        "artifact_type": "local_llm_advisory_request",
                        "status": status,
                        "local_only": True,
                        "execution_allowed": False,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def test_batch_v2_sequences_dependencies_before_dependents(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_project(config, tmp_path)
    _add_item(config, "m120-parent", priority="high", item_type="architecture")
    _add_item(config, "m121-child", priority="urgent", dependencies=["m120-parent"], item_type="feature")

    payload = json.loads(plan_operator_batch_v2(config, project_id="aresforge", output_format="json")["stdout"])

    assert payload["plan_type"] == "operator_batch_sequence_v2"
    assert [entry["item_id"] for entry in payload["recommended_sequence"]] == ["m120-parent", "m121-child"]
    assert payload["execution_performed"] is False
    assert payload["queue_mutation_performed"] is False


def test_batch_v2_reports_blocked_items_without_including_them_by_default(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_project(config, tmp_path)
    _add_item(config, "m120-blocked", status="blocked", item_type="feature")
    _add_item(config, "m121-open", status="proposed", dependencies=["m120-missing"], item_type="feature")

    payload = json.loads(plan_operator_batch_v2(config, project_id="aresforge", output_format="json")["stdout"])

    assert payload["recommended_sequence"] == []
    assert payload["blocked_count"] >= 1
    assert any(warning["item_id"] == "m121-open" for warning in payload["dependency_warnings"])


def test_batch_v2_include_blocked_adds_blocked_entries_as_advisory_only(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_project(config, tmp_path)
    _add_item(config, "m120-blocked", status="blocked", item_type="feature")

    payload = json.loads(
        plan_operator_batch_v2(config, project_id="aresforge", include_blocked=True, output_format="json")["stdout"]
    )

    assert payload["recommended_sequence"][0]["item_id"] == "m120-blocked"
    assert payload["recommended_sequence"][0]["blocked"] is True
    assert payload["recommended_sequence"][0]["execution_allowed"] is False


def test_batch_v2_respects_limit_and_groups_lanes(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_project(config, tmp_path)
    _add_item(config, "m120-docs", priority="urgent", item_type="documentation")
    _add_item(config, "m121-dashboard", priority="high", item_type="dashboard")
    _add_item(config, "m122-architecture", priority="normal", item_type="architecture")

    payload = json.loads(plan_operator_batch_v2(config, project_id="aresforge", limit=2, output_format="json")["stdout"])

    assert [entry["item_id"] for entry in payload["recommended_sequence"]] == ["m120-docs", "m121-dashboard"]
    assert payload["lane_grouping"] == {
        "dashboard": ["m121-dashboard"],
        "documentation": ["m120-docs"],
    }


def test_batch_v2_reports_artifact_and_approval_readiness(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_project(config, tmp_path)
    _add_item(config, "m120-ready", item_type="feature")
    _write_artifact(config, "m120-ready")
    _write_approval(config, "m120-ready")

    payload = json.loads(plan_operator_batch_v2(config, project_id="aresforge", output_format="json")["stdout"])
    entry = payload["recommended_sequence"][0]

    assert entry["artifact_ready"] is True
    assert entry["approval_ready"] is True
    assert payload["artifact_warnings"] == []
    assert payload["approval_warnings"] == []


def test_batch_v2_output_path_refuses_overwrite_without_force(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_project(config, tmp_path)
    _add_item(config, "m120-output", item_type="feature")
    output = tmp_path / "batch.json"
    output.write_text("existing", encoding="utf-8")

    blocked = plan_operator_batch_v2(config, project_id="aresforge", output=output, output_format="json")
    written = plan_operator_batch_v2(config, project_id="aresforge", output=output, force=True, output_format="json")

    assert blocked["ok"] is False
    assert blocked["payload"]["blocked"] is True
    assert written["ok"] is True
    assert written["wrote_output_file"] is True
    assert json.loads(output.read_text(encoding="utf-8"))["plan_type"] == "operator_batch_sequence_v2"
