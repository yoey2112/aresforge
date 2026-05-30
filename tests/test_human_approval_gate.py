from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.dispatch_approval_gate import create_dispatch_approval_gate, update_dispatch_approval_gate


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


def test_human_approval_gate_keeps_execution_disabled_for_patch_proposal(tmp_path: Path) -> None:
    config = _config(tmp_path)
    created = create_dispatch_approval_gate(
        config,
        item_id="m111",
        artifact_type="patch_proposal",
        artifact_path="artifacts/manual/test.patch",
        dispatch_lane="human_only_manual",
    )["payload"]["approval_gate"]

    updated = update_dispatch_approval_gate(
        config,
        approval_id=created["approval_id"],
        status="approved_for_manual_handoff",
        reviewer="operator",
    )["payload"]["approval_gate"]

    assert updated["status"] == "approved_for_manual_handoff"
    assert updated["local_only"] is True
    assert updated["execution_allowed"] is False
    assert "automated execution remains blocked" in updated["next_safe_action"]
