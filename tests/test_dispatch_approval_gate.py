import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.dispatch_approval_gate import (
    create_dispatch_approval_gate,
    inspect_dispatch_approval_gate,
    update_dispatch_approval_gate,
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


def _gate(result: dict[str, object]) -> dict[str, object]:
    payload = result["payload"]  # type: ignore[index]
    return payload["approval_gate"]  # type: ignore[index]


def test_creates_approval_gate_record(tmp_path: Path) -> None:
    config = _config(tmp_path)

    result = create_dispatch_approval_gate(
        config,
        item_id="m101",
        artifact_type="documentation_agent_dry_run",
        artifact_path="artifacts/m101.md",
        dispatch_lane="documentation_agent_dry_run",
        reviewer="operator",
        checklist=["reviewed", "local_only_confirmed"],
    )
    gate = _gate(result)

    assert result["ok"] is True
    assert gate["approval_id"]
    assert gate["item_id"] == "m101"
    assert gate["artifact_type"] == "documentation_agent_dry_run"
    assert gate["dispatch_lane"] == "documentation_agent_dry_run"
    assert gate["status"] == "pending_review"
    assert gate["local_only"] is True
    assert gate["execution_allowed"] is False
    assert gate["checklist"] == ["reviewed", "local_only_confirmed"]


def test_reads_approval_gate_record(tmp_path: Path) -> None:
    config = _config(tmp_path)
    created = _gate(create_dispatch_approval_gate(config, item_id="m101", artifact_type="codex_prompt_artifact"))

    read = inspect_dispatch_approval_gate(config, approval_id=str(created["approval_id"]))
    gate = _gate(read)

    assert read["ok"] is True
    assert gate["approval_id"] == created["approval_id"]
    assert gate["item_id"] == "m101"
    assert gate["execution_allowed"] is False


def test_updates_approval_gate_to_approved_for_manual_handoff(tmp_path: Path) -> None:
    config = _config(tmp_path)
    created = _gate(create_dispatch_approval_gate(config, item_id="m101", artifact_type="local_llm_advisory"))

    updated = _gate(
        update_dispatch_approval_gate(
            config,
            approval_id=str(created["approval_id"]),
            status="approved_for_manual_handoff",
            reviewer="operator",
            review_notes="Ready for manual handoff only.",
        )
    )

    assert updated["status"] == "approved_for_manual_handoff"
    assert updated["reviewer"] == "operator"
    assert updated["review_notes"] == "Ready for manual handoff only."
    assert updated["local_only"] is True
    assert updated["execution_allowed"] is False
    assert "automated execution remains blocked" in updated["next_safe_action"]


def test_updates_approval_gate_to_rejected(tmp_path: Path) -> None:
    config = _config(tmp_path)
    created = _gate(create_dispatch_approval_gate(config, item_id="m101", artifact_type="codex_prompt_artifact"))

    updated = _gate(
        update_dispatch_approval_gate(
            config,
            approval_id=str(created["approval_id"]),
            status="rejected",
            review_notes="Artifact is stale.",
        )
    )

    assert updated["status"] == "rejected"
    assert updated["review_notes"] == "Artifact is stale."
    assert updated["execution_allowed"] is False


def test_invalid_status_is_blocked(tmp_path: Path) -> None:
    config = _config(tmp_path)
    created = _gate(create_dispatch_approval_gate(config, item_id="m101", artifact_type="codex_prompt_artifact"))

    result = update_dispatch_approval_gate(
        config,
        approval_id=str(created["approval_id"]),
        status="execute_now",
    )
    payload = result["payload"]  # type: ignore[index]

    assert result["ok"] is False
    assert payload["blocked"] is True
    assert any("Invalid approval status" in reason for reason in payload["blocked_reasons"])


def test_execution_and_local_flags_remain_stable_after_update(tmp_path: Path) -> None:
    config = _config(tmp_path)
    created = _gate(create_dispatch_approval_gate(config, item_id="m101", artifact_type="documentation_agent_dry_run"))

    updated = _gate(
        update_dispatch_approval_gate(
            config,
            approval_id=str(created["approval_id"]),
            status="needs_revision",
        )
    )

    assert updated["local_only"] is True
    assert updated["execution_allowed"] is False


def test_json_stdout_contains_stable_fields(tmp_path: Path) -> None:
    config = _config(tmp_path)

    result = create_dispatch_approval_gate(
        config,
        item_id="m101",
        artifact_type="codex_prompt_artifact",
        dispatch_lane="codex_prompt_artifact",
        output_format="json",
    )
    parsed = json.loads(result["stdout"])  # type: ignore[arg-type]
    gate = parsed["approval_gate"]

    assert parsed["ok"] is True
    assert parsed["local_only"] is True
    assert parsed["execution_allowed"] is False
    assert gate["approval_id"]
    assert gate["status"] == "pending_review"
    assert gate["local_only"] is True
    assert gate["execution_allowed"] is False
