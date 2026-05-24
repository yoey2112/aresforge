from __future__ import annotations

from pathlib import Path
from typing import Any

from aresforge.config import AppConfig


CONTRACT_PATH = Path("docs/architecture/AUTOMATIC_CANONICAL_EVIDENCE_EMISSION_CONTRACT.md")

REQUIRED_ARTIFACT_TYPES: tuple[str, ...] = (
    "child closeout evidence bundles",
    "pr evidence bundles",
    "parent closeout evidence bundles",
    "generated closeout comments",
)

REQUIRED_COMPLETENESS_TERMS: tuple[str, ...] = (
    "required marker completeness",
    "machine-checkable",
    "deterministic",
    "post-hoc marker repair comments should not be required",
)

REQUIRED_SAFETY_TERMS: tuple[str, ...] = (
    "read-only by default",
    "dry-run/planning by default",
    "operator-approved and targeted",
)

REQUIRED_READINESS_CONSUMPTION_TERMS: tuple[str, ...] = (
    "readiness-by-construction",
    "child evidence marker preflight",
    "pr mapping preflight",
    "parent closeout readiness",
)

REQUIRED_COMPATIBILITY_TERMS: tuple[str, ...] = (
    "backward-compatible fallback parsing",
    "canonical marker parsing is preferred",
)


def inspect_automatic_canonical_evidence_emission_contract(config: AppConfig) -> dict[str, Any]:
    absolute_contract_path = config.repo_root / CONTRACT_PATH
    exists = absolute_contract_path.exists()
    text = absolute_contract_path.read_text(encoding="utf-8") if exists else ""
    lowered = text.lower()

    checks = {
        "contract_document_exists": exists,
        "artifact_types_defined": _contains_all(lowered, REQUIRED_ARTIFACT_TYPES),
        "marker_completeness_rules_defined": _contains_all(lowered, REQUIRED_COMPLETENESS_TERMS),
        "read_only_default_safety_defined": _contains_all(lowered, REQUIRED_SAFETY_TERMS),
        "readiness_consumption_defined": _contains_all(lowered, REQUIRED_READINESS_CONSUMPTION_TERMS),
        "backward_compatibility_defined": _contains_all(lowered, REQUIRED_COMPATIBILITY_TERMS),
    }
    ok = all(checks.values())

    return {
        "command": "inspect-automatic-canonical-evidence-emission-contract",
        "ok": ok,
        "inspection_mode": "local_document_read_only",
        "read_only": True,
        "contract_path": str(CONTRACT_PATH),
        "checks": checks,
        "missing": {
            "artifact_types": _missing_items(lowered, REQUIRED_ARTIFACT_TYPES),
            "marker_completeness_terms": _missing_items(lowered, REQUIRED_COMPLETENESS_TERMS),
            "safety_terms": _missing_items(lowered, REQUIRED_SAFETY_TERMS),
            "readiness_consumption_terms": _missing_items(lowered, REQUIRED_READINESS_CONSUMPTION_TERMS),
            "backward_compatibility_terms": _missing_items(lowered, REQUIRED_COMPATIBILITY_TERMS),
        },
        "warnings": [] if ok else _warnings(checks, exists),
        "boundary_confirmations": [
            "Read-only contract inspection only.",
            "No GitHub mutation was executed.",
            "No issue, PR, branch, label, milestone, or repository file mutation was executed by this command.",
        ],
    }


def _contains_all(text: str, required_terms: tuple[str, ...]) -> bool:
    return all(term in text for term in required_terms)


def _missing_items(text: str, required_terms: tuple[str, ...]) -> list[str]:
    return [term for term in required_terms if term not in text]


def _warnings(checks: dict[str, bool], exists: bool) -> list[str]:
    warnings: list[str] = []
    if not exists:
        warnings.append("Automatic canonical evidence emission contract document is missing.")
        return warnings
    for key, value in checks.items():
        if not value:
            warnings.append(f"Contract check failed: {key}.")
    return warnings
