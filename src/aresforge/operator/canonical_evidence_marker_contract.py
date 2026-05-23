from __future__ import annotations

from pathlib import Path
from typing import Any

from aresforge.config import AppConfig


CONTRACT_PATH = Path("docs/architecture/CANONICAL_EVIDENCE_MARKER_CONTRACT.md")

REQUIRED_MARKER_TYPES: tuple[str, ...] = (
    "child evidence marker",
    "pr evidence marker",
    "parent closeout evidence marker",
    "reconciliation/audit marker",
)

REQUIRED_CHILD_FIELDS: tuple[str, ...] = (
    "parent issue",
    "child issue",
    "branch",
    "commit",
    "pr",
    "validation summary",
    "safety notes",
)

REQUIRED_PR_FIELDS: tuple[str, ...] = (
    "issue",
    "pr",
    "branch",
    "commit",
    "changed files",
    "validation summary",
    "merge status",
    "safety posture",
)

REQUIRED_PARENT_FIELDS: tuple[str, ...] = (
    "parent issue",
    "child issue list",
    "child-to-pr mapping",
    "final main head",
    "final validation results",
    "readiness gate summary",
    "closeout readiness state",
)

REQUIRED_RECONCILIATION_FIELDS: tuple[str, ...] = (
    "baseline snapshot",
    "post-reconciliation snapshot",
    "snapshot diff",
    "audit classification",
    "warnings/deviations",
)

REQUIRED_M22_RELATIONSHIP_TERMS: tuple[str, ...] = (
    "evidence bundle automation contract",
    "m22",
)

REQUIRED_M23_RELATIONSHIP_TERMS: tuple[str, ...] = (
    "milestone closeout preflight contract",
    "m23",
)

REQUIRED_SNAPSHOT_DIFF_TERMS: tuple[str, ...] = (
    "snapshot",
    "diff",
    "no-change",
    "improved",
    "regressed",
    "mixed",
)

REQUIRED_COPY_PASTE_SAFETY_TERMS: tuple[str, ...] = (
    "copy/paste-safe",
    "avoid nested markdown fences inside powershell here-strings",
)


def inspect_canonical_evidence_marker_contract(config: AppConfig) -> dict[str, Any]:
    absolute_contract_path = config.repo_root / CONTRACT_PATH
    exists = absolute_contract_path.exists()
    text = absolute_contract_path.read_text(encoding="utf-8") if exists else ""
    lowered = text.lower()

    checks = {
        "contract_document_exists": exists,
        "marker_types_defined": _contains_all(lowered, REQUIRED_MARKER_TYPES),
        "child_marker_required_fields_defined": _contains_all(lowered, REQUIRED_CHILD_FIELDS),
        "pr_marker_required_fields_defined": _contains_all(lowered, REQUIRED_PR_FIELDS),
        "parent_marker_required_fields_defined": _contains_all(lowered, REQUIRED_PARENT_FIELDS),
        "reconciliation_marker_required_fields_defined": _contains_all(
            lowered,
            REQUIRED_RECONCILIATION_FIELDS,
        ),
        "read_only_default_behavior_defined": "read-only by default" in lowered,
        "m22_relationship_defined": _contains_all(lowered, REQUIRED_M22_RELATIONSHIP_TERMS),
        "m23_relationship_defined": _contains_all(lowered, REQUIRED_M23_RELATIONSHIP_TERMS),
        "snapshot_diff_audit_expectations_defined": _contains_all(
            lowered,
            REQUIRED_SNAPSHOT_DIFF_TERMS,
        ),
        "copy_paste_safety_defined": _contains_all(lowered, REQUIRED_COPY_PASTE_SAFETY_TERMS),
    }
    ok = all(checks.values())

    return {
        "command": "inspect-canonical-evidence-marker-contract",
        "ok": ok,
        "inspection_mode": "local_document_read_only",
        "read_only": True,
        "contract_path": str(CONTRACT_PATH),
        "checks": checks,
        "missing": {
            "marker_types": _missing_items(lowered, REQUIRED_MARKER_TYPES),
            "child_marker_required_fields": _missing_items(lowered, REQUIRED_CHILD_FIELDS),
            "pr_marker_required_fields": _missing_items(lowered, REQUIRED_PR_FIELDS),
            "parent_marker_required_fields": _missing_items(lowered, REQUIRED_PARENT_FIELDS),
            "reconciliation_marker_required_fields": _missing_items(
                lowered,
                REQUIRED_RECONCILIATION_FIELDS,
            ),
            "m22_relationship_terms": _missing_items(lowered, REQUIRED_M22_RELATIONSHIP_TERMS),
            "m23_relationship_terms": _missing_items(lowered, REQUIRED_M23_RELATIONSHIP_TERMS),
            "snapshot_diff_terms": _missing_items(lowered, REQUIRED_SNAPSHOT_DIFF_TERMS),
            "copy_paste_safety_terms": _missing_items(lowered, REQUIRED_COPY_PASTE_SAFETY_TERMS),
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
        warnings.append("Canonical evidence marker contract document is missing.")
        return warnings
    for key, value in checks.items():
        if not value:
            warnings.append(f"Contract check failed: {key}.")
    return warnings