from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.milestone_closeout_preflight_contract import (
    inspect_milestone_closeout_preflight_contract,
)


def make_config(tmp_path: Path) -> AppConfig:
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


def test_inspect_milestone_closeout_preflight_contract_ok(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    contract_path = config.repo_root / "docs/architecture/MILESTONE_CLOSEOUT_PREFLIGHT_CONTRACT.md"
    contract_path.parent.mkdir(parents=True, exist_ok=True)
    contract_path.write_text(
        "\n".join(
            [
                "read-only by default",
                "parent references all intended children",
                "child references parent",
                "missing lineage",
                "ambiguous lineage",
                "conflicting lineage",
                "evidence comment marker",
                "branch",
                "commit",
                "pr",
                "validation",
                "safety notes",
                "child to pr mapping",
                "pr merge status",
                "missing pr mapping",
                "ambiguous pr mapping",
                "unmerged pr",
                "ready",
                "blocked",
                "warning",
                "unknown",
                "actionable repair guidance",
                "inspect-milestone-dashboard",
                "inspect-milestone-state",
                "check-milestone-evidence-readiness",
                "inspect-parent-closeout-readiness",
                "generate-parent-closeout-evidence-bundle",
            ]
        ),
        encoding="utf-8",
    )

    payload = inspect_milestone_closeout_preflight_contract(config)

    assert payload["ok"] is True
    assert payload["read_only"] is True
    assert payload["checks"]["contract_document_exists"] is True
    assert payload["checks"]["required_parent_child_lineage_signals_defined"] is True
    assert payload["checks"]["required_child_evidence_mapping_signals_defined"] is True
    assert payload["checks"]["required_pr_mapping_signals_defined"] is True
    assert payload["checks"]["required_states_defined"] is True
    assert payload["checks"]["read_only_default_behavior_defined"] is True
    assert payload["checks"]["actionable_repair_guidance_requirements_defined"] is True
    assert payload["checks"]["existing_command_relationships_defined"] is True
    assert payload["warnings"] == []


def test_inspect_milestone_closeout_preflight_contract_missing_doc(tmp_path: Path) -> None:
    config = make_config(tmp_path)

    payload = inspect_milestone_closeout_preflight_contract(config)

    assert payload["ok"] is False
    assert payload["checks"]["contract_document_exists"] is False
    assert "contract document is missing" in payload["warnings"][0].lower()


def test_inspect_milestone_closeout_preflight_contract_reports_missing_required_terms(
    tmp_path: Path,
) -> None:
    config = make_config(tmp_path)
    contract_path = config.repo_root / "docs/architecture/MILESTONE_CLOSEOUT_PREFLIGHT_CONTRACT.md"
    contract_path.parent.mkdir(parents=True, exist_ok=True)
    contract_path.write_text(
        "\n".join(
            [
                "read-only by default",
                "parent references all intended children",
                "child references parent",
                "ready",
                "blocked",
                "warning",
                "unknown",
                "inspect-milestone-dashboard",
                "inspect-milestone-state",
                "check-milestone-evidence-readiness",
                "inspect-parent-closeout-readiness",
                "generate-parent-closeout-evidence-bundle",
            ]
        ),
        encoding="utf-8",
    )

    payload = inspect_milestone_closeout_preflight_contract(config)

    assert payload["ok"] is False
    assert payload["checks"]["required_child_evidence_mapping_signals_defined"] is False
    assert payload["checks"]["required_pr_mapping_signals_defined"] is False
    assert payload["checks"]["actionable_repair_guidance_requirements_defined"] is False
    assert "evidence comment marker" in payload["missing"]["child_evidence_mapping_signals"]
    assert "child to pr mapping" in payload["missing"]["pr_mapping_signals"]
