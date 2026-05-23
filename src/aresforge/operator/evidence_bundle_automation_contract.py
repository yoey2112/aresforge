from __future__ import annotations

from pathlib import Path
from typing import Any

from aresforge.config import AppConfig


EXPECTED_BUNDLE_TYPES: tuple[str, ...] = (
    "child_closeout_evidence_bundle",
    "parent_closeout_evidence_bundle",
    "pr_evidence_bundle",
    "validation_summary_bundle",
    "handoff_summary_bundle",
    "documentation_reconciliation_bundle",
)

CONTRACT_PATH = Path("docs/architecture/EVIDENCE_BUNDLE_AUTOMATION_CONTRACT.md")


def inspect_evidence_bundle_automation_contract(config: AppConfig) -> dict[str, Any]:
    absolute_contract_path = config.repo_root / CONTRACT_PATH
    exists = absolute_contract_path.exists()
    text = absolute_contract_path.read_text(encoding="utf-8") if exists else ""
    lowered = text.lower()

    generation_mutation_separated = (
        "generation logic and mutation execution are separated" in lowered
        or "generation and mutation are separated" in lowered
    )
    read_only_default_preserved = "read-only by default" in lowered
    explicit_approval_required = (
        "require explicit operator approval" in lowered
        or "requires explicit operator approval" in lowered
        or "operator-approved" in lowered
    )
    missing_bundle_types = [name for name in EXPECTED_BUNDLE_TYPES if name not in lowered]

    checks = {
        "contract_document_exists": exists,
        "expected_bundle_types_named": not missing_bundle_types,
        "generation_mutation_separated": generation_mutation_separated,
        "read_only_default_preserved": read_only_default_preserved,
        "targeted_mutation_requires_explicit_operator_approval": explicit_approval_required,
    }
    ok = all(checks.values())

    return {
        "command": "inspect-evidence-bundle-automation-contract",
        "ok": ok,
        "inspection_mode": "local_document_read_only",
        "contract_path": str(CONTRACT_PATH),
        "checks": checks,
        "missing_bundle_types": missing_bundle_types,
        "warnings": [] if ok else _warnings(checks, exists),
    }


def _warnings(checks: dict[str, bool], exists: bool) -> list[str]:
    warnings: list[str] = []
    if not exists:
        warnings.append("Evidence bundle automation contract document is missing.")
        return warnings
    for key, value in checks.items():
        if not value:
            warnings.append(f"Contract check failed: {key}.")
    return warnings

