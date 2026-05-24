from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.automatic_canonical_evidence_emission_contract import (
    inspect_automatic_canonical_evidence_emission_contract,
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


def test_inspect_automatic_canonical_evidence_emission_contract_ok(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    contract_path = (
        config.repo_root / "docs/architecture/AUTOMATIC_CANONICAL_EVIDENCE_EMISSION_CONTRACT.md"
    )
    contract_path.parent.mkdir(parents=True, exist_ok=True)
    contract_path.write_text(
        "\n".join(
            [
                "child closeout evidence bundles",
                "pr evidence bundles",
                "parent closeout evidence bundles",
                "generated closeout comments",
                "required marker completeness",
                "machine-checkable",
                "deterministic",
                "post-hoc marker repair comments should not be required",
                "read-only by default",
                "dry-run/planning by default",
                "operator-approved and targeted",
                "readiness-by-construction",
                "child evidence marker preflight",
                "pr mapping preflight",
                "parent closeout readiness",
                "backward-compatible fallback parsing",
                "canonical marker parsing is preferred",
            ]
        ),
        encoding="utf-8",
    )

    payload = inspect_automatic_canonical_evidence_emission_contract(config)

    assert payload["ok"] is True
    assert payload["read_only"] is True
    assert payload["checks"]["contract_document_exists"] is True
    assert payload["checks"]["artifact_types_defined"] is True
    assert payload["checks"]["marker_completeness_rules_defined"] is True
    assert payload["checks"]["read_only_default_safety_defined"] is True
    assert payload["checks"]["readiness_consumption_defined"] is True
    assert payload["checks"]["backward_compatibility_defined"] is True
    assert payload["warnings"] == []


def test_inspect_automatic_canonical_evidence_emission_contract_missing_doc(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    payload = inspect_automatic_canonical_evidence_emission_contract(config)
    assert payload["ok"] is False
    assert payload["checks"]["contract_document_exists"] is False
    assert "contract document is missing" in payload["warnings"][0].lower()


def test_inspect_automatic_canonical_evidence_emission_contract_reports_missing_terms(
    tmp_path: Path,
) -> None:
    config = make_config(tmp_path)
    contract_path = (
        config.repo_root / "docs/architecture/AUTOMATIC_CANONICAL_EVIDENCE_EMISSION_CONTRACT.md"
    )
    contract_path.parent.mkdir(parents=True, exist_ok=True)
    contract_path.write_text(
        "\n".join(
            [
                "child closeout evidence bundles",
                "pr evidence bundles",
                "parent closeout evidence bundles",
                "generated closeout comments",
                "read-only by default",
            ]
        ),
        encoding="utf-8",
    )

    payload = inspect_automatic_canonical_evidence_emission_contract(config)

    assert payload["ok"] is False
    assert payload["checks"]["marker_completeness_rules_defined"] is False
    assert payload["checks"]["readiness_consumption_defined"] is False
    assert payload["checks"]["backward_compatibility_defined"] is False
    assert (
        "post-hoc marker repair comments should not be required"
        in payload["missing"]["marker_completeness_terms"]
    )
    assert "readiness-by-construction" in payload["missing"]["readiness_consumption_terms"]
