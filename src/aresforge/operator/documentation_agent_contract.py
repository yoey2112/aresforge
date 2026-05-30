from __future__ import annotations

import json
from typing import Any

from aresforge.config import AppConfig

DOCUMENTATION_AGENT_CONTRACT_VERSION = "m91.1"
APPLY_APPROVAL_PHRASE = "APPROVE DOCUMENTATION AGENT APPLY"

SOURCE_OF_TRUTH_DOCS = [
    "docs/context/BUILD_STATE.md",
    "docs/context/AGENT_CONTEXT.md",
    "docs/roadmap/ROADMAP.md",
    "docs/architecture/RUNNABLE_SKELETON.md",
    "docs/operator/LOCAL_OPERATOR_USAGE.md",
]

_BOUNDARY_CONFIRMATIONS = (
    "M91 Documentation Agent v1 is contract-first.",
    "Documentation Agent v1 is local-only.",
    "Plan mode is read-only and non-mutating.",
    "Future apply mode requires an explicit operator approval gate.",
    "Model output cannot automatically update documentation.",
    "Documentation updates require validation evidence before apply.",
    "No queue item is completed from documentation agent output.",
    "No automatic next-item execution.",
    "No GitHub API calls.",
    "No gh calls.",
    "No issues, PRs, workflows, daemons, watchers, schedulers, or external workflow behavior.",
)


def inspect_documentation_agent_contract(
    config: AppConfig,
    *,
    output_format: str = "json",
) -> dict[str, Any]:
    payload = build_documentation_agent_contract(config)
    return _stdout_result(
        "inspect-documentation-agent-contract",
        payload,
        output_format,
        _render_markdown(payload),
    )


def build_documentation_agent_contract(config: AppConfig) -> dict[str, Any]:
    return {
        "ok": True,
        "local_only": True,
        "read_only": True,
        "contract_first": True,
        "contract_name": "documentation_agent_v1_contract",
        "contract_version": DOCUMENTATION_AGENT_CONTRACT_VERSION,
        "milestone": "M91",
        "repo_root": str(config.repo_root),
        "agent_scope": {
            "agent_id": "documentation_agent_v1",
            "purpose": "Reconcile source-of-truth documentation after validated local changes.",
            "allowed_work": [
                "inspect changed files and queue evidence",
                "prepare a documentation reconciliation plan",
                "identify source-of-truth docs requiring updates",
                "summarize evidence required before documentation updates",
                "prepare future operator-reviewed doc patches after validation evidence exists",
            ],
            "forbidden_work": [
                "automatic documentation mutation from model output",
                "automatic queue completion",
                "automatic next-item execution",
                "GitHub API calls",
                "gh calls",
                "issues, PRs, workflows, daemons, watchers, schedulers, or external workflow behavior",
            ],
        },
        "source_docs_to_update": list(SOURCE_OF_TRUTH_DOCS),
        "evidence_required_before_docs_are_updated": [
            "implementation commit hash or local diff summary",
            "queue item id and milestone identifier",
            "validation commands and results",
            "smoke checks and results",
            "git diff --check result",
            "files changed summary",
            "operator statement that documentation reconciliation is required",
            "explicit source docs selected for update",
        ],
        "plan_mode": {
            "mode": "plan_only",
            "available_now": True,
            "mutates_files": False,
            "provider_invocation_required": False,
            "output": "documentation_reconciliation_plan",
            "allowed_outputs": [
                "docs_to_review",
                "evidence_gaps",
                "recommended_doc_updates",
                "blocked_reasons",
                "next_safe_action",
            ],
        },
        "future_gated_apply_mode": {
            "available_now": False,
            "requires_future_milestone": True,
            "explicit_operator_approval_required": True,
            "approval_phrase": APPLY_APPROVAL_PHRASE,
            "required_gates": [
                "plan_mode_completed",
                "validation_evidence_present",
                "selected_source_docs_confirmed",
                "operator_approval_phrase_matches",
                "worktree_state_reviewed",
                "post_apply_validation_plan_present",
            ],
            "post_apply_validation_required": [
                "operator reviews documentation diff",
                "git diff --check",
                "targeted documentation or CLI tests when affected",
                "inspect-local-project-report",
                "queue completion remains a separate explicit evidence command",
            ],
        },
        "safety_boundary": {
            "local_only": True,
            "read_only_from_this_command": True,
            "plan_mode_mutates_files": False,
            "apply_mode_available_now": False,
            "automatic_doc_updates_allowed": False,
            "model_output_can_mutate_docs": False,
            "queue_mutation_allowed": False,
            "queue_completion_allowed": False,
            "automatic_next_item_execution_allowed": False,
            "github_api_allowed": False,
            "gh_allowed": False,
            "external_workflow_allowed": False,
        },
        "next_safe_action": "Use this contract to guide manual documentation reconciliation; future apply requires a separate explicit gated milestone.",
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }


def _stdout_result(command: str, payload: dict[str, Any], output_format: str, markdown: str) -> dict[str, Any]:
    fmt = str(output_format or "json").lower().strip()
    if fmt not in {"json", "markdown"}:
        return {
            "ok": False,
            "local_only": True,
            "error": "invalid_format",
            "details": {"format": output_format, "supported_formats": ["json", "markdown"]},
        }
    return {
        "command": command,
        "ok": bool(payload.get("ok", False)),
        "local_only": True,
        "format": fmt,
        "wrote_output_file": False,
        "stdout": json.dumps(payload, indent=2) if fmt == "json" else markdown,
        "payload": payload,
    }


def _render_markdown(payload: dict[str, Any]) -> str:
    safety = payload.get("safety_boundary", {}) if isinstance(payload.get("safety_boundary"), dict) else {}
    lines = [
        "# Documentation Agent v1 Contract",
        "",
        f"- ok: {payload.get('ok')}",
        f"- contract_version: {payload.get('contract_version', '')}",
        f"- contract_first: {payload.get('contract_first')}",
        f"- plan_mode_mutates_files: {safety.get('plan_mode_mutates_files')}",
        f"- apply_mode_available_now: {safety.get('apply_mode_available_now')}",
        f"- automatic_doc_updates_allowed: {safety.get('automatic_doc_updates_allowed')}",
        f"- next_safe_action: {payload.get('next_safe_action', '')}",
        "",
        "## Source Docs",
    ]
    lines.extend(f"- {path}" for path in payload.get("source_docs_to_update", []))
    return "\n".join(lines)
