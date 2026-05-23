from __future__ import annotations

from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.evidence_mapping_parser import parse_issue_evidence_mapping
from aresforge.operator.github_mutation_audit_log import inspect_github_mutation_audit_log
from aresforge.operator.ready_issue_intake import fetch_issue_details

COMMAND_NAME = "generate-sequential-closeout-execution-package"


def generate_sequential_closeout_execution_package(
    config: AppConfig,
    *,
    parent_issue: int,
    child_issue: int,
    pr_url: str | None = None,
    validation_results: list[str] | None = None,
) -> dict[str, Any]:
    issue_payload = fetch_issue_details(config, child_issue)
    if not issue_payload.get("ok"):
        return {
            "command": COMMAND_NAME,
            "ok": False,
            "read_only": True,
            "error": issue_payload.get("error", "child_issue_lookup_failed"),
            "parent_issue": parent_issue,
            "child_issue": child_issue,
        }

    issue = issue_payload.get("issue")
    if not isinstance(issue, dict):
        return {
            "command": COMMAND_NAME,
            "ok": False,
            "read_only": True,
            "error": "child_issue_lookup_failed",
            "parent_issue": parent_issue,
            "child_issue": child_issue,
        }

    mapping = parse_issue_evidence_mapping(
        issue_number=child_issue,
        issue_body=issue.get("body") if isinstance(issue.get("body"), str) else "",
        comments=issue.get("comments") if isinstance(issue.get("comments"), list) else [],
    )
    audit_log = inspect_github_mutation_audit_log(config, limit=20)
    audit_path = audit_log.get("log_path")
    derived_prs = mapping.get("derived_pr_evidence") if isinstance(mapping.get("derived_pr_evidence"), list) else []
    mapped_pr_number = derived_prs[0].get("number") if derived_prs and isinstance(derived_prs[0], dict) else None

    validations = validation_results or []
    validations = [item.strip() for item in validations if isinstance(item, str) and item.strip()]

    pr_payload = {
        "pr_url": pr_url,
        "mapped_pr_number": mapped_pr_number,
        "mapping_detected": bool(mapping.get("issue_specific_mapping_detected")),
        "mapping_fallback_used": bool((mapping.get("legacy_fallback") or {}).get("matched")),
    }
    comment_payload = {
        "target_issue": child_issue,
        "body_template": (
            f"M21 child #{child_issue} evidence package ready. "
            f"Parent #{parent_issue}. PR: {pr_url or '<fill-pr-url>'}. "
            f"Validation count: {len(validations)}."
        ),
    }
    closeout_payload = {
        "target_issue": child_issue,
        "parent_issue": parent_issue,
        "mode": "targeted_child_only",
        "bulk_closeout_allowed": False,
    }

    return {
        "command": COMMAND_NAME,
        "ok": True,
        "read_only": True,
        "parent_issue": parent_issue,
        "child_issue": child_issue,
        "evidence_payload": {
            "issue_number": child_issue,
            "validation_results": validations,
            "pr_payload": pr_payload,
            "mapping_analysis": mapping,
        },
        "targeted_issue_comment_payload": comment_payload,
        "targeted_closeout_payload": closeout_payload,
        "audit_package": {
            "audit_log_path": audit_path,
            "entry_count": audit_log.get("entry_count"),
            "latest_entries": audit_log.get("entries"),
        },
        "recovery_guidance": {
            "partial_success_plan": [
                "If comment posts but closeout fails, re-run targeted closeout only for the same issue.",
                "If closeout fails due to read-after-write lag, re-check issue state and retry after short delay.",
            ],
            "read_after_write_confirmation": [
                f"gh issue view {child_issue} --json number,state,closedAt,url",
                f"gh issue view {parent_issue} --json number,state,title,url",
            ],
        },
        "safety_checks": {
            "read_only_package_generation": True,
            "dry_run_default_preserved": True,
            "targeted_scope_only": True,
            "bulk_closeout_forbidden": True,
        },
        "boundary_confirmations": [
            "Package generation is read-only.",
            "No GitHub mutation was performed.",
            "Package is child-targeted and does not generate bulk closeout actions.",
        ],
    }
