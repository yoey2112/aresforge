from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.self_managed_milestone_execution_contract import (
    inspect_self_managed_milestone_execution_contract,
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
        github_owner="yoey2112",
        github_repo="aresforge",
    )


def test_contract_surface_is_read_only_and_contains_m21_safety_boundaries(tmp_path: Path) -> None:
    payload = inspect_self_managed_milestone_execution_contract(_config(tmp_path))

    assert payload["ok"] is True
    assert payload["read_only"] is True
    assert payload["contract_version"] == "m21.v1"
    assert payload["safety_boundaries"]["dry_run_default"] is True
    assert payload["safety_boundaries"]["bulk_closeout_forbidden"] is True
    assert payload["safety_boundaries"]["final_reconciliation_must_be_last"] is True
    assert payload["approval_boundary"]["required_for_mutation_execution"] is True
    assert payload["parent_closeout_readiness_boundary"]["required_checks"] == [
        "all_children_closed_or_accounted_for",
        "milestone_evidence_readiness_ok",
        "parent_closeout_ready_true",
        "blocked_reasons_empty",
    ]
