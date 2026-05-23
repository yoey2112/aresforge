from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.canonical_evidence_marker_contract import (
    inspect_canonical_evidence_marker_contract,
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


def test_inspect_canonical_evidence_marker_contract_ok(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    contract_path = config.repo_root / "docs/architecture/CANONICAL_EVIDENCE_MARKER_CONTRACT.md"
    contract_path.parent.mkdir(parents=True, exist_ok=True)
    contract_path.write_text(
        "\n".join(
            [
                "child evidence marker",
                "pr evidence marker",
                "parent closeout evidence marker",
                "reconciliation/audit marker",
                "parent issue",
                "child issue",
                "branch",
                "commit",
                "pr",
                "validation summary",
                "safety notes",
                "issue",
                "changed files",
                "merge status",
                "safety posture",
                "child issue list",
                "child-to-pr mapping",
                "final main head",
                "final validation results",
                "readiness gate summary",
                "closeout readiness state",
                "baseline snapshot",
                "post-reconciliation snapshot",
                "snapshot diff",
                "audit classification",
                "warnings/deviations",
                "read-only by default",
                "evidence bundle automation contract",
                "m22",
                "milestone closeout preflight contract",
                "m23",
                "snapshot",
                "diff",
                "no-change",
                "improved",
                "regressed",
                "mixed",
                "copy/paste-safe",
                "avoid nested markdown fences inside powershell here-strings",
            ]
        ),
        encoding="utf-8",
    )

    payload = inspect_canonical_evidence_marker_contract(config)

    assert payload["ok"] is True
    assert payload["read_only"] is True
    assert payload["checks"]["contract_document_exists"] is True
    assert payload["checks"]["marker_types_defined"] is True
    assert payload["checks"]["read_only_default_behavior_defined"] is True
    assert payload["checks"]["m22_relationship_defined"] is True
    assert payload["checks"]["m23_relationship_defined"] is True
    assert payload["checks"]["snapshot_diff_audit_expectations_defined"] is True
    assert payload["checks"]["copy_paste_safety_defined"] is True
    assert payload["warnings"] == []


def test_inspect_canonical_evidence_marker_contract_missing_doc(tmp_path: Path) -> None:
    config = make_config(tmp_path)

    payload = inspect_canonical_evidence_marker_contract(config)

    assert payload["ok"] is False
    assert payload["checks"]["contract_document_exists"] is False
    assert "contract document is missing" in payload["warnings"][0].lower()


def test_inspect_canonical_evidence_marker_contract_reports_missing_required_terms(
    tmp_path: Path,
) -> None:
    config = make_config(tmp_path)
    contract_path = config.repo_root / "docs/architecture/CANONICAL_EVIDENCE_MARKER_CONTRACT.md"
    contract_path.parent.mkdir(parents=True, exist_ok=True)
    contract_path.write_text(
        "\n".join(
            [
                "child evidence marker",
                "pr evidence marker",
                "parent closeout evidence marker",
                "reconciliation/audit marker",
                "parent issue",
                "child issue",
                "branch",
                "commit",
                "pr",
                "validation summary",
                "safety notes",
                "read-only by default",
            ]
        ),
        encoding="utf-8",
    )

    payload = inspect_canonical_evidence_marker_contract(config)

    assert payload["ok"] is False
    assert payload["checks"]["m22_relationship_defined"] is False
    assert payload["checks"]["m23_relationship_defined"] is False
    assert payload["checks"]["snapshot_diff_audit_expectations_defined"] is False
    assert payload["checks"]["copy_paste_safety_defined"] is False
    assert "evidence bundle automation contract" in payload["missing"]["m22_relationship_terms"]
    assert "milestone closeout preflight contract" in payload["missing"]["m23_relationship_terms"]