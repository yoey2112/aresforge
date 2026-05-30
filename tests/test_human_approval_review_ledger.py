from __future__ import annotations

import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.dispatch_approval_gate import create_dispatch_approval_gate, update_dispatch_approval_gate
from aresforge.operator.human_approval_review_ledger import inspect_approval_ledger, record_artifact_review
from aresforge.operator.local_project_queue import add_queue_item, init_project_queue
from aresforge.operator.managed_project_registry_local import (
    init_managed_project_registry,
    register_managed_project,
    register_managed_repo,
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


def _add_item(config: AppConfig, item_id: str) -> None:
    assert add_queue_item(
        config,
        item_id=item_id,
        project_id="aresforge",
        repo_id="aresforge-main",
        title=item_id,
        description="Local item.",
        status="proposed",
    )["ok"] is True


def _write_artifact(config: AppConfig, item_id: str, *, name: str | None = None) -> Path:
    target = config.repo_root / "artifacts" / "local_llm_advisory" / "requests" / f"{name or item_id}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(
            {
                "artifact_type": "local_llm_advisory_request",
                "item_id": item_id,
                "project_id": "aresforge",
                "local_only": True,
                "execution_allowed": False,
            }
        ),
        encoding="utf-8",
    )
    return target


def test_approval_ledger_lists_unreviewed_artifacts(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_project(config, tmp_path)
    _add_item(config, "m121")
    artifact = _write_artifact(config, "m121")

    payload = json.loads(inspect_approval_ledger(config, project_id="aresforge", output_format="json")["stdout"])

    assert payload["ledger_type"] == "human_approval_review_ledger"
    assert payload["reviewed_artifacts"] == []
    assert payload["unreviewed_artifacts"][0]["artifact_path"] == str(artifact.resolve())
    assert payload["approval_gaps"][0]["reason"] == "no_human_review_decision_recorded"
    assert payload["execution_allowed"] is False


def test_record_artifact_review_approved_moves_artifact_to_approved(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_project(config, tmp_path)
    _add_item(config, "m121")
    artifact = _write_artifact(config, "m121")

    record = json.loads(
        record_artifact_review(
            config,
            item_id="m121",
            artifact_path=artifact,
            decision="approved",
            reviewer="operator",
            review_notes="reviewed",
            output_format="json",
        )["stdout"]
    )
    payload = json.loads(inspect_approval_ledger(config, project_id="aresforge", output_format="json")["stdout"])

    assert record["review_record"]["decision"] == "approved"
    assert record["review_record"]["execution_allowed"] is False
    assert payload["approved_artifacts"][0]["item_id"] == "m121"
    assert payload["unreviewed_artifacts"] == []


def test_approval_ledger_reuses_existing_approval_gate_records(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_project(config, tmp_path)
    _add_item(config, "m121")
    artifact = _write_artifact(config, "m121")
    gate = create_dispatch_approval_gate(
        config,
        item_id="m121",
        artifact_type="local_llm_advisory_request",
        artifact_path=artifact,
        dispatch_lane="manual",
    )["payload"]["approval_gate"]
    update_dispatch_approval_gate(
        config,
        approval_id=gate["approval_id"],
        status="needs_revision",
        reviewer="operator",
    )

    payload = json.loads(inspect_approval_ledger(config, project_id="aresforge", output_format="json")["stdout"])

    assert payload["needs_changes_artifacts"][0]["item_id"] == "m121"
    assert payload["review_records"][0]["source"] == "dispatch_approval_gate"
    assert payload["review_records"][0]["decision"] == "needs_changes"


def test_approval_ledger_filters_and_output_no_overwrite(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_project(config, tmp_path)
    _add_item(config, "m121-a")
    _add_item(config, "m121-b")
    first = _write_artifact(config, "m121-a")
    _write_artifact(config, "m121-b")
    output = tmp_path / "ledger.json"
    output.write_text("existing", encoding="utf-8")

    filtered = json.loads(
        inspect_approval_ledger(
            config,
            project_id="aresforge",
            item_id="m121-a",
            artifact_path=first,
            output_format="json",
        )["stdout"]
    )
    blocked = inspect_approval_ledger(config, project_id="aresforge", output=output, output_format="json")
    written = inspect_approval_ledger(config, project_id="aresforge", output=output, force=True, output_format="json")

    assert len(filtered["unreviewed_artifacts"]) == 1
    assert filtered["unreviewed_artifacts"][0]["item_id"] == "m121-a"
    assert blocked["ok"] is False
    assert blocked["payload"]["blocked"] is True
    assert written["ok"] is True
    assert json.loads(output.read_text(encoding="utf-8"))["ledger_type"] == "human_approval_review_ledger"


def test_record_artifact_review_rejects_invalid_decision(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_project(config, tmp_path)

    result = record_artifact_review(
        config,
        item_id="m121",
        artifact_path="artifacts/missing.json",
        decision="maybe",
        output_format="json",
    )
    payload = json.loads(result["stdout"])

    assert result["ok"] is False
    assert payload["blocked"] is True
    assert "decision must be one of" in payload["blocked_reasons"][0]
