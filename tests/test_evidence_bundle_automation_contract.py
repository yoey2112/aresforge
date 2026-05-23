from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.evidence_bundle_automation_contract import (
    inspect_evidence_bundle_automation_contract,
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


def test_inspect_evidence_bundle_automation_contract_ok(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    contract_path = config.repo_root / "docs/architecture/EVIDENCE_BUNDLE_AUTOMATION_CONTRACT.md"
    contract_path.parent.mkdir(parents=True, exist_ok=True)
    contract_path.write_text(
        "\n".join(
            [
                "child_closeout_evidence_bundle",
                "parent_closeout_evidence_bundle",
                "pr_evidence_bundle",
                "validation_summary_bundle",
                "handoff_summary_bundle",
                "documentation_reconciliation_bundle",
                "generation logic and mutation execution are separated",
                "read-only by default",
                "requires explicit operator approval",
            ]
        ),
        encoding="utf-8",
    )

    payload = inspect_evidence_bundle_automation_contract(config)

    assert payload["ok"] is True
    assert payload["checks"]["contract_document_exists"] is True
    assert payload["checks"]["expected_bundle_types_named"] is True
    assert payload["checks"]["generation_mutation_separated"] is True
    assert payload["checks"]["read_only_default_preserved"] is True
    assert payload["checks"]["targeted_mutation_requires_explicit_operator_approval"] is True
    assert payload["warnings"] == []


def test_inspect_evidence_bundle_automation_contract_missing_doc(tmp_path: Path) -> None:
    config = make_config(tmp_path)

    payload = inspect_evidence_bundle_automation_contract(config)

    assert payload["ok"] is False
    assert payload["checks"]["contract_document_exists"] is False
    assert "contract document is missing" in payload["warnings"][0].lower()

