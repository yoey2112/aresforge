from __future__ import annotations

from pathlib import Path
from typing import Any

from aresforge.config import AppConfig


CONTRACT_PATH = Path("docs/architecture/MILESTONE_CLOSEOUT_PREFLIGHT_CONTRACT.md")

REQUIRED_PARENT_CHILD_LINEAGE_SIGNALS: tuple[str, ...] = (
    "parent references all intended children",
    "child references parent",
    "missing lineage",
    "ambiguous lineage",
    "conflicting lineage",
)

REQUIRED_CHILD_EVIDENCE_MAPPING_SIGNALS: tuple[str, ...] = (
    "evidence comment marker",
    "branch",
    "commit",
    "pr",
    "validation",
    "safety notes",
)

REQUIRED_PR_MAPPING_SIGNALS: tuple[str, ...] = (
    "child to pr mapping",
    "pr merge status",
    "missing pr mapping",
    "ambiguous pr mapping",
    "unmerged pr",
)

REQUIRED_PREFLIGHT_STATES: tuple[str, ...] = (
    "ready",
    "blocked",
    "warning",
    "unknown",
)

REQUIRED_RELATED_COMMANDS: tuple[str, ...] = (
    "inspect-milestone-dashboard",
    "inspect-milestone-state",
    "check-milestone-evidence-readiness",
    "inspect-parent-closeout-readiness",
    "generate-parent-closeout-evidence-bundle",
)


def inspect_milestone_closeout_preflight_contract(config: AppConfig) -> dict[str, Any]:
    absolute_contract_path = config.repo_root / CONTRACT_PATH
    exists = absolute_contract_path.exists()
    text = absolute_contract_path.read_text(encoding="utf-8") if exists else ""
    lowered = text.lower()

    checks = {
        "contract_document_exists": exists,
        "required_parent_child_lineage_signals_defined": _contains_all(
            lowered,
            REQUIRED_PARENT_CHILD_LINEAGE_SIGNALS,
        ),
        "required_child_evidence_mapping_signals_defined": _contains_all(
            lowered,
            REQUIRED_CHILD_EVIDENCE_MAPPING_SIGNALS,
        ),
        "required_pr_mapping_signals_defined": _contains_all(lowered, REQUIRED_PR_MAPPING_SIGNALS),
        "required_states_defined": _contains_all(lowered, REQUIRED_PREFLIGHT_STATES),
        "read_only_default_behavior_defined": "read-only by default" in lowered,
        "actionable_repair_guidance_requirements_defined": _contains_any(
            lowered,
            (
                "actionable repair guidance",
                "copy/paste-safe repair guidance",
            ),
        ),
        "existing_command_relationships_defined": _contains_all(lowered, REQUIRED_RELATED_COMMANDS),
    }
    ok = all(checks.values())

    return {
        "command": "inspect-milestone-closeout-preflight-contract",
        "ok": ok,
        "inspection_mode": "local_document_read_only",
        "read_only": True,
        "contract_path": str(CONTRACT_PATH),
        "checks": checks,
        "missing": {
            "parent_child_lineage_signals": _missing_items(lowered, REQUIRED_PARENT_CHILD_LINEAGE_SIGNALS),
            "child_evidence_mapping_signals": _missing_items(lowered, REQUIRED_CHILD_EVIDENCE_MAPPING_SIGNALS),
            "pr_mapping_signals": _missing_items(lowered, REQUIRED_PR_MAPPING_SIGNALS),
            "states": _missing_items(lowered, REQUIRED_PREFLIGHT_STATES),
            "related_commands": _missing_items(lowered, REQUIRED_RELATED_COMMANDS),
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


def _contains_any(text: str, candidates: tuple[str, ...]) -> bool:
    return any(candidate in text for candidate in candidates)


def _missing_items(text: str, required_terms: tuple[str, ...]) -> list[str]:
    return [term for term in required_terms if term not in text]


def _warnings(checks: dict[str, bool], exists: bool) -> list[str]:
    warnings: list[str] = []
    if not exists:
        warnings.append("Milestone closeout preflight contract document is missing.")
        return warnings
    for key, value in checks.items():
        if not value:
            warnings.append(f"Contract check failed: {key}.")
    return warnings
