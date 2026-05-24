from __future__ import annotations

from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.child_closeout_evidence_bundle import generate_child_closeout_evidence_bundle
from aresforge.operator.evidence_comment_template_generator import generate_evidence_comment_template
from aresforge.operator.evidence_completeness_checker import check_milestone_evidence_readiness
from aresforge.operator.milestone_state_inspector import inspect_milestone_state
from aresforge.operator.parent_closeout_evidence_bundle import generate_parent_closeout_evidence_bundle
from aresforge.operator.pr_evidence_bundle import generate_pr_evidence_bundle
from aresforge.operator.ready_issue_intake import fetch_issue_details

COMMAND_NAME = "check-closeout-readiness-by-construction"


def check_closeout_readiness_by_construction(config: AppConfig, *, parent_issue: int) -> dict[str, Any]:
    milestone = inspect_milestone_state(config, parent_issue=parent_issue)
    if not bool(milestone.get("ok")):
        return {
            "command": COMMAND_NAME,
            "ok": False,
            "read_only": True,
            "parent_issue": parent_issue,
            "error": "milestone_state_inspection_failed",
            "details": milestone,
            "blocked_reasons": ["milestone_state_inspection_failed"],
            "recommended_actions": [
                f"Re-run inspect-milestone-state for parent #{parent_issue} and resolve lookup failures.",
            ],
            "mutation": _mutation_fields(),
        }

    children = milestone.get("child_issues") if isinstance(milestone.get("child_issues"), list) else []
    child_numbers = sorted(
        item["issue_number"]
        for item in children
        if isinstance(item, dict) and isinstance(item.get("issue_number"), int)
    )
    child_results = [generate_child_closeout_evidence_bundle(config, parent_issue=parent_issue, child_issue=n) for n in child_numbers]
    closeout_comment_results = [generate_evidence_comment_template(config, issue_number=n) for n in child_numbers]

    pr_results: list[dict[str, Any]] = []
    for child_issue in child_numbers:
        issue_payload = fetch_issue_details(config, child_issue)
        issue = issue_payload.get("issue") if isinstance(issue_payload.get("issue"), dict) else {}
        merged = issue.get("merged_pr_evidence") if isinstance(issue.get("merged_pr_evidence"), list) else []
        for pr in merged:
            if not isinstance(pr, dict) or not isinstance(pr.get("number"), int):
                continue
            pr_results.append(generate_pr_evidence_bundle(config, issue_number=child_issue, pr_number=pr["number"]))

    parent_result = generate_parent_closeout_evidence_bundle(config, parent_issue=parent_issue)
    milestone_evidence = check_milestone_evidence_readiness(config, parent_issue=parent_issue)

    child_domain = _domain_summary(
        "child_bundle_canonical_marker_completeness",
        child_results,
        "canonical_marker_completeness",
    )
    pr_domain = _domain_summary("pr_bundle_canonical_marker_completeness", pr_results, "canonical_marker_completeness")
    parent_domain = _domain_summary(
        "parent_bundle_canonical_marker_completeness",
        [parent_result],
        "canonical_marker_completeness",
    )
    closeout_comment_domain = _domain_summary(
        "closeout_comment_canonical_marker_completeness",
        closeout_comment_results,
        "canonical_marker_completeness",
    )

    blocked_reasons: list[str] = []
    if not child_numbers:
        blocked_reasons.append("no_child_issue_targets_detected")
    blocked_reasons.extend(child_domain["blocked_reasons"])
    blocked_reasons.extend(pr_domain["blocked_reasons"])
    blocked_reasons.extend(parent_domain["blocked_reasons"])
    blocked_reasons.extend(closeout_comment_domain["blocked_reasons"])
    blocked_reasons.extend(_milestone_blockers(milestone_evidence))
    blocked_reasons = sorted(set(blocked_reasons))

    missing_required_fields = sorted(
        set(
            child_domain["missing_required_fields"]
            + pr_domain["missing_required_fields"]
            + parent_domain["missing_required_fields"]
            + closeout_comment_domain["missing_required_fields"]
        )
    )
    invalid_reasons = sorted(
        set(
            child_domain["invalid_reasons"]
            + pr_domain["invalid_reasons"]
            + parent_domain["invalid_reasons"]
            + closeout_comment_domain["invalid_reasons"]
        )
    )
    post_hoc_marker_repair_required = any(
        domain["post_hoc_marker_repair_required"]
        for domain in (child_domain, pr_domain, parent_domain, closeout_comment_domain)
    )
    marker_emission_ready = not post_hoc_marker_repair_required and not missing_required_fields and not invalid_reasons
    milestone_execution_ready = _milestone_execution_ready(milestone_evidence)
    readiness_by_construction_ready = marker_emission_ready and milestone_execution_ready

    recommended_actions = _recommended_actions(
        parent_issue=parent_issue,
        marker_emission_ready=marker_emission_ready,
        milestone_execution_ready=milestone_execution_ready,
        blocked_reasons=blocked_reasons,
    )
    return {
        "command": COMMAND_NAME,
        "ok": True,
        "read_only": True,
        "parent_issue": parent_issue,
        "readiness_by_construction": {
            "ready": readiness_by_construction_ready,
            "marker_emission_ready": marker_emission_ready,
            "milestone_execution_ready": milestone_execution_ready,
        },
        "marker_emission_domains_checked": [
            child_domain["domain"],
            pr_domain["domain"],
            parent_domain["domain"],
            closeout_comment_domain["domain"],
        ],
        "child_bundle_marker_completeness": child_domain,
        "pr_bundle_marker_completeness": pr_domain,
        "parent_bundle_marker_completeness": parent_domain,
        "closeout_comment_marker_completeness": closeout_comment_domain,
        "missing_required_fields": missing_required_fields,
        "invalid_reasons": invalid_reasons,
        "post_hoc_marker_repair_required": post_hoc_marker_repair_required,
        "blocked_reasons": blocked_reasons,
        "recommended_actions": recommended_actions,
        "mutation": _mutation_fields(),
    }


def _domain_summary(domain: str, rows: list[dict[str, Any]], completeness_field: str) -> dict[str, Any]:
    markers: list[dict[str, Any]] = []
    missing_required_fields: list[str] = []
    invalid_reasons: list[str] = []
    blocked_reasons: list[str] = []
    post_hoc_required = False
    for row in rows:
        if not bool(row.get("ok")):
            blocked_reasons.append(f"{domain}_generation_failed")
            continue
        completeness = row.get(completeness_field) if isinstance(row.get(completeness_field), dict) else {}
        state = completeness.get("state")
        marker_complete = completeness.get("marker_complete")
        missing = completeness.get("missing_required_fields") if isinstance(completeness.get("missing_required_fields"), list) else []
        invalid = completeness.get("invalid_reasons") if isinstance(completeness.get("invalid_reasons"), list) else []
        post_hoc = bool(completeness.get("post_hoc_marker_repair_required"))
        if missing:
            missing_required_fields.extend(str(item) for item in missing)
        if invalid:
            invalid_reasons.extend(str(item) for item in invalid)
        if post_hoc:
            post_hoc_required = True
        if marker_complete is not True:
            blocked_reasons.append(f"{domain}_marker_incomplete")
        markers.append(
            {
                "state": state,
                "marker_complete": marker_complete is True,
                "missing_required_fields": list(missing),
                "invalid_reasons": list(invalid),
                "post_hoc_marker_repair_required": post_hoc,
            }
        )
    return {
        "domain": domain,
        "checked_count": len(rows),
        "marker_complete_count": len([item for item in markers if item["marker_complete"]]),
        "marker_incomplete_count": len([item for item in markers if not item["marker_complete"]]),
        "marker_complete": bool(rows) and len([item for item in markers if not item["marker_complete"]]) == 0,
        "missing_required_fields": sorted(set(missing_required_fields)),
        "invalid_reasons": sorted(set(invalid_reasons)),
        "post_hoc_marker_repair_required": post_hoc_required or (bool(rows) and len([item for item in markers if not item["marker_complete"]]) > 0),
        "blocked_reasons": sorted(set(blocked_reasons)),
    }


def _milestone_execution_ready(payload: dict[str, Any]) -> bool:
    readiness = payload.get("milestone_closeout_readiness") if isinstance(payload.get("milestone_closeout_readiness"), dict) else {}
    return readiness.get("closeout_ready") is True


def _milestone_blockers(payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if not bool(payload.get("ok")):
        blockers.append("milestone_evidence_readiness_check_failed")
        return blockers
    readiness = payload.get("milestone_closeout_readiness") if isinstance(payload.get("milestone_closeout_readiness"), dict) else {}
    closeout_ready = readiness.get("closeout_ready")
    if closeout_ready is True:
        return blockers
    if closeout_ready == "ambiguous":
        blockers.append("milestone_evidence_readiness_ambiguous")
    else:
        blockers.append("milestone_evidence_readiness_not_ready")
    return blockers


def _recommended_actions(
    *,
    parent_issue: int,
    marker_emission_ready: bool,
    milestone_execution_ready: bool,
    blocked_reasons: list[str],
) -> list[str]:
    actions: list[str] = []
    if not marker_emission_ready:
        actions.append("Regenerate affected evidence artifacts/comments to restore canonical marker completeness before closeout.")
    if not milestone_execution_ready:
        actions.append(f"Resolve milestone execution blockers, then re-run {COMMAND_NAME} for parent #{parent_issue}.")
    if "no_child_issue_targets_detected" in blocked_reasons:
        actions.append("Repair parent-child linkage discoverability so child issue targets can be checked.")
    if not actions:
        actions.append("Readiness by construction is satisfied; proceed with standard human-gated closeout flow.")
    return actions


def _mutation_fields() -> dict[str, Any]:
    return {
        "attempted": False,
        "read_only": True,
        "comment_on_issue": False,
        "close_issues": False,
        "create_pr": False,
        "merge_pr": False,
        "mutation_allowed": False,
    }
