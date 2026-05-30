import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.dispatch_approval_gate import create_dispatch_approval_gate, update_dispatch_approval_gate
from aresforge.operator.local_project_queue import add_queue_item, init_project_queue
from aresforge.operator.manual_codex_dispatch_runner import prepare_manual_codex_dispatch


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


def _seed_item(config: AppConfig, *, status: str = "ready", item_type: str = "feature") -> None:
    assert init_project_queue(config)["ok"] is True
    assert (
        add_queue_item(
            config,
            item_id="m109-target",
            project_id="aresforge",
            repo_id="aresforge-main",
            title="M109 target implementation",
            description="Implement a local-only manual Codex dispatch contract.",
            status=status,
            priority="high",
            item_type=item_type,
            tags=["milestone:m109", "local-only"],
        )["ok"]
        is True
    )


def _artifact(config: AppConfig) -> Path:
    path = config.artifact_root / "codex_prompt_dispatch" / "generated" / "m109-target.txt"
    path.parent.mkdir(parents=True)
    path.write_text("Manual/operator-gated prompt only.\nexecution_allowed=false\n", encoding="utf-8")
    return path


def _approved_gate(config: AppConfig, artifact_path: Path) -> str:
    created = create_dispatch_approval_gate(
        config,
        item_id="m109-target",
        artifact_type="codex_prompt_artifact",
        artifact_path=artifact_path,
        dispatch_lane="codex_prompt_artifact",
        reviewer="operator",
        output_format="json",
    )["payload"]["approval_gate"]
    updated = update_dispatch_approval_gate(
        config,
        approval_id=created["approval_id"],
        status="approved_for_manual_handoff",
        reviewer="operator",
        review_notes="Approved for manual handoff only.",
        output_format="json",
    )["payload"]["approval_gate"]
    return updated["approval_id"]


def _plan(**overrides: object) -> dict[str, object]:
    plan: dict[str, object] = {
        "ok": True,
        "local_only": True,
        "dispatch_plan_version": "m97.1",
        "item_id": "m109-target",
        "title": "M109 target implementation",
        "status": "ready",
        "project_id": "aresforge",
        "repo_id": "aresforge-main",
        "milestone": "m109",
        "selected_lane": "codex_prompt_artifact",
        "blocked": False,
        "blocked_reasons": [],
        "execution_allowed": False,
    }
    plan.update(overrides)
    return plan


def _payload(result: dict[str, object]) -> dict[str, object]:
    return result["payload"]  # type: ignore[index]


def test_prepared_for_valid_codex_artifact_item_with_approved_gate(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_item(config)
    artifact = _artifact(config)
    approval_id = _approved_gate(config, artifact)

    payload = _payload(
        prepare_manual_codex_dispatch(
            config,
            item_id="m109-target",
            artifact_path=artifact,
            approval_id=approval_id,
            dispatch_plan=_plan(),
            output_format="json",
        )
    )

    assert payload["prepared"] is True
    assert payload["blocked"] is False
    assert payload["selected_lane"] == "codex_prompt_artifact"
    assert payload["codex_artifact_path"] == str(artifact.resolve())
    assert payload["approval_status"] == "approved_for_manual_handoff"
    assert payload["execution_allowed"] is False
    assert payload["codex_execution_performed"] is False
    assert "manual Codex run transcript or summary" in payload["evidence_expected_after_manual_run"]


def test_blocks_when_selected_lane_is_not_codex_prompt_artifact(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_item(config)
    artifact = _artifact(config)
    approval_id = _approved_gate(config, artifact)

    payload = _payload(
        prepare_manual_codex_dispatch(
            config,
            item_id="m109-target",
            artifact_path=artifact,
            approval_id=approval_id,
            dispatch_plan=_plan(selected_lane="documentation_agent_dry_run"),
        )
    )

    assert payload["prepared"] is False
    assert any("Selected lane must be codex_prompt_artifact" in reason for reason in payload["blocked_reasons"])


def test_blocks_when_prompt_artifact_is_missing(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_item(config)
    missing = tmp_path / "artifacts" / "codex_prompt_dispatch" / "generated" / "missing.txt"

    payload = _payload(
        prepare_manual_codex_dispatch(
            config,
            item_id="m109-target",
            artifact_path=missing,
            dispatch_plan=_plan(),
        )
    )

    assert payload["blocked"] is True
    assert any("Codex prompt artifact is missing" in reason for reason in payload["blocked_reasons"])


def test_blocks_when_approval_gate_is_missing_or_not_approved(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_item(config)
    artifact = _artifact(config)

    missing_gate = _payload(
        prepare_manual_codex_dispatch(config, item_id="m109-target", artifact_path=artifact, dispatch_plan=_plan())
    )
    assert any("Approval gate is missing" in reason for reason in missing_gate["blocked_reasons"])

    created = create_dispatch_approval_gate(
        config,
        item_id="m109-target",
        artifact_type="codex_prompt_artifact",
        artifact_path=artifact,
        dispatch_lane="codex_prompt_artifact",
    )["payload"]["approval_gate"]
    pending_gate = _payload(
        prepare_manual_codex_dispatch(
            config,
            item_id="m109-target",
            artifact_path=artifact,
            approval_id=created["approval_id"],
            dispatch_plan=_plan(),
        )
    )
    assert any("required approved_for_manual_handoff" in reason for reason in pending_gate["blocked_reasons"])


def test_blocks_when_queue_item_is_done(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_item(config, status="done")
    artifact = _artifact(config)
    approval_id = _approved_gate(config, artifact)

    payload = _payload(
        prepare_manual_codex_dispatch(
            config,
            item_id="m109-target",
            artifact_path=artifact,
            approval_id=approval_id,
            dispatch_plan=_plan(status="done"),
        )
    )

    assert payload["blocked"] is True
    assert any("lifecycle-blocked" in reason for reason in payload["blocked_reasons"])


def test_blocks_when_local_only_false_or_execution_allowed_true(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_item(config)
    artifact = _artifact(config)
    approval_id = _approved_gate(config, artifact)

    not_local = _payload(
        prepare_manual_codex_dispatch(
            config,
            item_id="m109-target",
            artifact_path=artifact,
            approval_id=approval_id,
            dispatch_plan=_plan(local_only=False),
        )
    )
    executable = _payload(
        prepare_manual_codex_dispatch(
            config,
            item_id="m109-target",
            artifact_path=artifact,
            approval_id=approval_id,
            dispatch_plan=_plan(execution_allowed=True),
        )
    )

    assert "Source dispatch plan local_only must be true." in not_local["blocked_reasons"]
    assert "Source dispatch plan execution_allowed must be false." in executable["blocked_reasons"]
    assert not_local["codex_execution_performed"] is False
    assert executable["execution_allowed"] is False


def test_readable_and_json_output_work(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_item(config)
    artifact = _artifact(config)
    approval_id = _approved_gate(config, artifact)

    readable = prepare_manual_codex_dispatch(
        config,
        item_id="m109-target",
        artifact_path=artifact,
        approval_id=approval_id,
        dispatch_plan=_plan(),
    )
    json_result = prepare_manual_codex_dispatch(
        config,
        item_id="m109-target",
        artifact_path=artifact,
        approval_id=approval_id,
        dispatch_plan=_plan(),
        output_format="json",
    )
    parsed = json.loads(json_result["stdout"])

    assert "# Manual Codex Dispatch Preparation" in readable["stdout"]
    assert "codex_execution_performed: False" in readable["stdout"]
    assert parsed["prepared"] is True
    assert parsed["execution_allowed"] is False


def test_output_file_refuses_overwrite_without_force(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_item(config)
    artifact = _artifact(config)
    approval_id = _approved_gate(config, artifact)
    output = tmp_path / "artifacts" / "manual_codex_dispatch" / "prepared" / "m109.json"

    first = prepare_manual_codex_dispatch(
        config,
        item_id="m109-target",
        artifact_path=artifact,
        approval_id=approval_id,
        dispatch_plan=_plan(),
        output=output,
        output_format="json",
    )
    second = prepare_manual_codex_dispatch(
        config,
        item_id="m109-target",
        artifact_path=artifact,
        approval_id=approval_id,
        dispatch_plan=_plan(),
        output=output,
        output_format="json",
    )

    assert first["ok"] is True
    assert output.exists()
    assert second["ok"] is False
    assert second["error"] == "output_exists"
