from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.human_gated_patch_contract import (
    APPROVAL_PHRASE,
    build_human_gated_patch_application_contract,
    inspect_human_gated_patch_application_contract,
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


def test_human_gated_patch_contract_is_dry_run_only(tmp_path: Path) -> None:
    payload = build_human_gated_patch_application_contract(_config(tmp_path))

    assert payload["ok"] is True
    assert payload["local_only"] is True
    assert payload["read_only"] is True
    assert payload["dry_run_only"] is True
    assert payload["patch_application_implemented"] is False
    assert payload["operator_approval_requirements"]["approval_phrase"] == APPROVAL_PHRASE

    boundary = payload["safety_boundary"]
    assert boundary["patch_application_allowed_from_this_command"] is False
    assert boundary["automatic_patch_application_allowed"] is False
    assert boundary["repo_mutation_allowed"] is False
    assert boundary["automatic_file_mutation_allowed"] is False
    assert boundary["queue_completion_allowed"] is False
    assert boundary["automatic_next_item_execution_allowed"] is False
    assert boundary["github_api_allowed"] is False
    assert boundary["gh_allowed"] is False


def test_human_gated_patch_contract_defines_patch_artifact_and_gates(tmp_path: Path) -> None:
    payload = build_human_gated_patch_application_contract(_config(tmp_path))

    structure = payload["patch_artifact_structure"]
    required_fields = set(structure["required_fields"])
    assert {
        "source_draft_artifact_path",
        "target_item_id",
        "patch_format",
        "target_files",
        "patch_text",
        "expected_validation",
        "draft_has_been_applied",
        "manual_review_required",
    }.issubset(required_fields)
    assert structure["required_boolean_values"]["draft_is_authoritative"] is False
    assert structure["required_boolean_values"]["draft_has_been_applied"] is False
    assert structure["required_boolean_values"]["manual_review_required"] is True
    assert "explicit_operator_approval_record_present" in payload["pre_apply_safety_gates"]
    assert "git diff --check" in payload["post_apply_validation_requirements"]


def test_inspect_human_gated_patch_contract_outputs_json(tmp_path: Path) -> None:
    result = inspect_human_gated_patch_application_contract(_config(tmp_path), output_format="json")

    assert result["ok"] is True
    assert result["local_only"] is True
    assert result["wrote_output_file"] is False
    assert '"dry_run_only": true' in result["stdout"]
    assert '"automatic_patch_application_allowed": false' in result["stdout"]
