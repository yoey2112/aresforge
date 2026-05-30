import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.approval_gated_patch_intake import intake_patch_proposal
from aresforge.operator.dispatch_approval_gate import create_dispatch_approval_gate, update_dispatch_approval_gate
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


def _seed_item(config: AppConfig, *, item_id: str = "m111-patch-intake") -> None:
    assert init_project_queue(config)["ok"] is True
    assert add_queue_item(
        config,
        item_id=item_id,
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M111 Approval-Gated Patch Intake Contract",
        description="Record proposed patch metadata without applying patches.",
        status="ready",
        priority="high",
        item_type="architecture",
        tags=["milestone:m111", "patch-intake", "local-only"],
        notes="Acceptance criteria: patch proposal intake only; patch_application_allowed=false.",
    )["ok"] is True


def _patch(config: AppConfig) -> Path:
    path = config.repo_root / "artifacts" / "manual" / "test.patch"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "diff --git a/docs/example.md b/docs/example.md",
                "--- a/docs/example.md",
                "+++ b/docs/example.md",
                "@@ -1 +1 @@",
                "-old",
                "+new",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def _approval(config: AppConfig, *, item_id: str = "m111-patch-intake", patch_path: Path, status: str) -> str:
    created = create_dispatch_approval_gate(
        config,
        item_id=item_id,
        artifact_type="patch_proposal",
        artifact_path=patch_path,
        dispatch_lane="human_only_manual",
    )["payload"]["approval_gate"]
    approval_id = created["approval_id"]
    if status != "pending_review":
        update_dispatch_approval_gate(config, approval_id=approval_id, status=status, reviewer="operator")
    return approval_id


def _payload(result: dict[str, object]) -> dict[str, object]:
    return result["payload"]  # type: ignore[index]


def test_accepts_patch_for_review_with_approved_gate(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_item(config)
    patch_path = _patch(config)
    approval_id = _approval(config, patch_path=patch_path, status="approved_for_manual_handoff")

    payload = _payload(
        intake_patch_proposal(
            config,
            item_id="m111-patch-intake",
            patch_artifact=patch_path,
            approval_id=approval_id,
        )
    )

    assert payload["intake_record_type"] == "patch_proposal_intake"
    assert payload["accepted_for_review"] is True
    assert payload["blocked"] is False
    assert payload["patch_artifact_exists"] is True
    assert payload["approval_status"] == "approved_for_manual_handoff"
    assert payload["operator_review_required"] is True
    assert payload["patch_application_allowed"] is False
    assert payload["patch_application_performed"] is False
    assert payload["local_only"] is True
    assert payload["execution_allowed"] is False


def test_blocks_missing_queue_item(tmp_path: Path) -> None:
    config = _config(tmp_path)
    patch_path = _patch(config)

    payload = _payload(intake_patch_proposal(config, item_id="missing", patch_artifact=patch_path))

    assert payload["accepted_for_review"] is False
    assert payload["blocked"] is True
    assert "Queue item was not found." in payload["blocked_reasons"]


def test_blocks_missing_patch_artifact(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_item(config)

    payload = _payload(
        intake_patch_proposal(
            config,
            item_id="m111-patch-intake",
            patch_artifact=tmp_path / "artifacts" / "manual" / "missing.patch",
        )
    )

    assert payload["patch_artifact_exists"] is False
    assert payload["blocked"] is True
    assert any("Patch artifact is missing" in reason for reason in payload["blocked_reasons"])


def test_blocks_missing_approval(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_item(config)
    patch_path = _patch(config)

    payload = _payload(intake_patch_proposal(config, item_id="m111-patch-intake", patch_artifact=patch_path))

    assert payload["approval_status"] == "missing"
    assert payload["blocked"] is True
    assert any("Approval gate is missing" in reason for reason in payload["blocked_reasons"])


def test_blocks_rejected_approval(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_item(config)
    patch_path = _patch(config)
    approval_id = _approval(config, patch_path=patch_path, status="rejected")

    payload = _payload(
        intake_patch_proposal(
            config,
            item_id="m111-patch-intake",
            patch_artifact=patch_path,
            approval_id=approval_id,
        )
    )

    assert payload["approval_status"] == "rejected"
    assert payload["accepted_for_review"] is False
    assert any("required approved_for_manual_handoff" in reason for reason in payload["blocked_reasons"])


def test_json_stdout_contains_stable_fields(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_item(config)
    patch_path = _patch(config)
    approval_id = _approval(config, patch_path=patch_path, status="approved_for_manual_handoff")

    result = intake_patch_proposal(
        config,
        item_id="m111-patch-intake",
        patch_artifact=patch_path,
        approval_id=approval_id,
        output_format="json",
    )
    parsed = json.loads(result["stdout"])  # type: ignore[arg-type]

    assert parsed["intake_record_type"] == "patch_proposal_intake"
    assert parsed["accepted_for_review"] is True
    assert parsed["patch_summary"]["format"] == "unified_diff"
    assert parsed["patch_application_allowed"] is False


def test_output_file_no_overwrite_and_force(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_item(config)
    patch_path = _patch(config)
    approval_id = _approval(config, patch_path=patch_path, status="approved_for_manual_handoff")
    output_path = tmp_path / "artifacts" / "patch_intake" / "m111.json"

    first = intake_patch_proposal(
        config,
        item_id="m111-patch-intake",
        patch_artifact=patch_path,
        approval_id=approval_id,
        output=output_path,
        output_format="json",
    )
    duplicate = _payload(
        intake_patch_proposal(
            config,
            item_id="m111-patch-intake",
            patch_artifact=patch_path,
            approval_id=approval_id,
            output=output_path,
            output_format="json",
        )
    )
    forced = intake_patch_proposal(
        config,
        item_id="m111-patch-intake",
        patch_artifact=patch_path,
        approval_id=approval_id,
        output=output_path,
        output_format="json",
        force=True,
    )

    assert first["ok"] is True
    assert output_path.exists()
    assert duplicate["blocked"] is True
    assert any("already exists" in reason for reason in duplicate["blocked_reasons"])
    assert forced["ok"] is True
