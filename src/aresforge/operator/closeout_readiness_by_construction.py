from __future__ import annotations

import json
import re
from pathlib import Path
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
_PR_NUMBER_PATTERN = re.compile(r"/pull/(?P<number>\d+)\b")


def check_closeout_readiness_by_construction(
    config: AppConfig,
    *,
    parent_issue: int,
    state_file: str | Path | None = None,
) -> dict[str, Any]:
    milestone = inspect_milestone_state(config, parent_issue=parent_issue, state_file=state_file)
    if not bool(milestone.get("ok")):
        payload: dict[str, Any] = {
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
        if state_file is not None:
            payload["inspection_mode"] = "local_state_file"
            payload["state_file"] = str(state_file)
        return payload

    children = milestone.get("child_issues") if isinstance(milestone.get("child_issues"), list) else []
    child_numbers = sorted(
        item["issue_number"]
        for item in children
        if isinstance(item, dict) and isinstance(item.get("issue_number"), int)
    )
    parent_result = generate_parent_closeout_evidence_bundle(config, parent_issue=parent_issue, state_file=state_file)
    milestone_evidence = check_milestone_evidence_readiness(config, parent_issue=parent_issue, state_file=state_file)
    child_to_pr_numbers = _resolve_child_pr_mappings(
        milestone=milestone,
        milestone_evidence=milestone_evidence,
        parent_bundle=parent_result,
        child_numbers=child_numbers,
    )

    child_results: list[dict[str, Any]] = []
    closeout_comment_results: list[dict[str, Any]] = []
    pr_results: list[dict[str, Any]] = []

    if state_file is None:
        for child_issue in child_numbers:
            issue_payload = fetch_issue_details(config, child_issue)
            issue = issue_payload.get("issue") if isinstance(issue_payload.get("issue"), dict) else {}
            mapped_pr_numbers = set(child_to_pr_numbers.get(child_issue, set()))
            if not mapped_pr_numbers:
                merged = issue.get("merged_pr_evidence") if isinstance(issue.get("merged_pr_evidence"), list) else []
                for pr in merged:
                    if isinstance(pr, dict):
                        pr_number = _extract_pr_number(pr)
                        if isinstance(pr_number, int):
                            mapped_pr_numbers.add(pr_number)
            first_pr_context: dict[str, str] = {}
            for pr_number in sorted(mapped_pr_numbers):
                pr_result = generate_pr_evidence_bundle(
                    config,
                    issue_number=child_issue,
                    pr_number=pr_number,
                    marker_context=_pr_marker_context(issue=issue),
                )
                pr_results.append(pr_result)
                if not first_pr_context and bool(pr_result.get("ok")):
                    pr_payload = pr_result.get("pr") if isinstance(pr_result.get("pr"), dict) else {}
                    branch = pr_payload.get("head_branch")
                    commit = pr_payload.get("merge_commit")
                    changed_files = pr_payload.get("files_changed")
                    first_pr_context = {
                        "branch": str(branch).strip() if isinstance(branch, str) else "",
                        "commit": str(commit).strip() if isinstance(commit, str) else "",
                        "changed_files": (
                            ", ".join(item for item in changed_files if isinstance(item, str) and item.strip())
                            if isinstance(changed_files, list)
                            else ""
                        ),
                    }
            marker_context = _child_marker_context(issue=issue, pr_numbers=mapped_pr_numbers, pr_context=first_pr_context)
            child_results.append(
                generate_child_closeout_evidence_bundle(
                    config,
                    parent_issue=parent_issue,
                    child_issue=child_issue,
                    marker_context=marker_context,
                )
            )
            closeout_comment_results.append(
                generate_evidence_comment_template(
                    config,
                    issue_number=child_issue,
                    parent_issue_override=parent_issue,
                    marker_context=marker_context,
                )
            )
    else:
        local_children = _load_local_children_by_number(state_file)
        for child_issue in child_numbers:
            issue = local_children.get(child_issue, {})
            child_results.append(
                {
                    "ok": True,
                    "canonical_marker_completeness": _offline_child_marker_completeness(issue),
                }
            )
            closeout_comment_results.append(
                {
                    "ok": True,
                    "canonical_marker_completeness": _offline_closeout_comment_marker_completeness(issue),
                }
            )

            mapped_pr_numbers = set(child_to_pr_numbers.get(child_issue, set()))
            if not mapped_pr_numbers:
                merged = issue.get("merged_pr_evidence") if isinstance(issue.get("merged_pr_evidence"), list) else []
                for pr in merged:
                    if isinstance(pr, dict):
                        pr_number = _extract_pr_number(pr)
                        if isinstance(pr_number, int):
                            mapped_pr_numbers.add(pr_number)

            pr_items = issue.get("merged_pr_evidence") if isinstance(issue.get("merged_pr_evidence"), list) else []
            pr_by_number: dict[int, dict[str, Any]] = {}
            for pr_item in pr_items:
                if not isinstance(pr_item, dict):
                    continue
                pr_number = _extract_pr_number(pr_item)
                if isinstance(pr_number, int):
                    pr_by_number[pr_number] = pr_item

            if not mapped_pr_numbers:
                pr_results.append(
                    {
                        "ok": True,
                        "canonical_marker_completeness": _missing_marker_completeness(
                            missing_required_fields=["merged_pr_evidence"],
                            invalid_reasons=["offline_pr_mapping_missing"],
                        ),
                    }
                )

            for pr_number in sorted(mapped_pr_numbers):
                pr_results.append(
                    {
                        "ok": True,
                        "canonical_marker_completeness": _offline_pr_marker_completeness(pr_by_number.get(pr_number)),
                    }
                )

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
    payload: dict[str, Any] = {
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
    if state_file is not None:
        payload["inspection_mode"] = "local_state_file"
        payload["state_file"] = str(state_file)
    return payload


def _load_local_children_by_number(state_file: str | Path) -> dict[int, dict[str, Any]]:
    try:
        parsed = json.loads(Path(state_file).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(parsed, dict):
        return {}
    child_issues = parsed.get("child_issues")
    if not isinstance(child_issues, list):
        return {}

    rows: dict[int, dict[str, Any]] = {}
    for child in child_issues:
        if not isinstance(child, dict):
            continue
        number = child.get("number")
        if isinstance(number, int):
            rows[number] = child
    return rows


def _missing_marker_completeness(
    *,
    missing_required_fields: list[str],
    invalid_reasons: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "state": "incomplete",
        "marker_complete": False,
        "missing_required_fields": sorted(set(missing_required_fields)),
        "invalid_reasons": sorted(set(invalid_reasons or [])),
        "post_hoc_marker_repair_required": True,
    }


def _normalize_marker_completeness(marker: Any, *, fallback_missing_field: str) -> dict[str, Any]:
    if isinstance(marker, dict):
        state = marker.get("state")
        marker_complete = marker.get("marker_complete")
        missing = marker.get("missing_required_fields")
        invalid = marker.get("invalid_reasons")
        post_hoc = marker.get("post_hoc_marker_repair_required")
        if isinstance(state, str) and isinstance(marker_complete, bool):
            return {
                "state": state,
                "marker_complete": marker_complete,
                "missing_required_fields": list(missing) if isinstance(missing, list) else [],
                "invalid_reasons": list(invalid) if isinstance(invalid, list) else [],
                "post_hoc_marker_repair_required": bool(post_hoc),
            }

        canonical = marker.get("canonical_marker_completeness")
        if isinstance(canonical, dict):
            return _normalize_marker_completeness(canonical, fallback_missing_field=fallback_missing_field)

    return _missing_marker_completeness(missing_required_fields=[fallback_missing_field])


def _offline_child_marker_completeness(issue: dict[str, Any]) -> dict[str, Any]:
    return _normalize_marker_completeness(issue.get("closeout_marker"), fallback_missing_field="closeout_marker")


def _offline_closeout_comment_marker_completeness(issue: dict[str, Any]) -> dict[str, Any]:
    return _normalize_marker_completeness(
        issue.get("closeout_comment_marker"),
        fallback_missing_field="closeout_comment_marker",
    )


def _offline_pr_marker_completeness(pr: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(pr, dict):
        return _missing_marker_completeness(missing_required_fields=["pr_marker"])
    marker_candidate = pr.get("marker") if isinstance(pr.get("marker"), dict) else pr
    return _normalize_marker_completeness(marker_candidate, fallback_missing_field="pr_marker")


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


def _resolve_child_pr_mappings(
    *,
    milestone: dict[str, Any],
    milestone_evidence: dict[str, Any],
    parent_bundle: dict[str, Any],
    child_numbers: list[int],
) -> dict[int, set[int]]:
    mappings: dict[int, set[int]] = {n: set() for n in child_numbers}
    for child_issue, pr_number in _mappings_from_milestone_children(milestone):
        mappings.setdefault(child_issue, set()).add(pr_number)
    for child_issue, pr_number in _mappings_from_milestone_evidence(milestone_evidence):
        mappings.setdefault(child_issue, set()).add(pr_number)
    for child_issue, pr_number in _mappings_from_parent_bundle(parent_bundle):
        mappings.setdefault(child_issue, set()).add(pr_number)
    return mappings


def _mappings_from_milestone_children(payload: dict[str, Any]) -> list[tuple[int, int]]:
    rows: list[tuple[int, int]] = []
    children = payload.get("child_issues") if isinstance(payload.get("child_issues"), list) else []
    for child in children:
        if not isinstance(child, dict):
            continue
        issue_number = child.get("issue_number")
        if not isinstance(issue_number, int):
            continue
        linked_pr_count = child.get("linked_pr_count")
        if isinstance(linked_pr_count, int) and linked_pr_count <= 0:
            continue
    return rows


def _mappings_from_milestone_evidence(payload: dict[str, Any]) -> list[tuple[int, int]]:
    rows: list[tuple[int, int]] = []
    issues = payload.get("issues") if isinstance(payload.get("issues"), list) else []
    for item in issues:
        if not isinstance(item, dict):
            continue
        issue = item.get("issue") if isinstance(item.get("issue"), dict) else {}
        issue_number = issue.get("number")
        if not isinstance(issue_number, int):
            continue
        merged = issue.get("merged_pr_evidence") if isinstance(issue.get("merged_pr_evidence"), list) else []
        for pr in merged:
            if not isinstance(pr, dict):
                continue
            pr_number = _extract_pr_number(pr)
            if isinstance(pr_number, int):
                rows.append((issue_number, pr_number))
    return rows


def _mappings_from_parent_bundle(payload: dict[str, Any]) -> list[tuple[int, int]]:
    rows: list[tuple[int, int]] = []
    mappings = payload.get("child_pr_mappings") if isinstance(payload.get("child_pr_mappings"), list) else []
    for mapping in mappings:
        if not isinstance(mapping, dict):
            continue
        issue_number = mapping.get("issue_number")
        if not isinstance(issue_number, int):
            continue
        urls = mapping.get("merged_pr_urls") if isinstance(mapping.get("merged_pr_urls"), list) else []
        for url in urls:
            if not isinstance(url, str):
                continue
            match = _PR_NUMBER_PATTERN.search(url.strip())
            if not match:
                continue
            rows.append((issue_number, int(match.group("number"))))
    return rows


def _extract_pr_number(payload: dict[str, Any]) -> int | None:
    number = payload.get("number")
    if isinstance(number, int):
        return number
    url = payload.get("url")
    if not isinstance(url, str):
        return None
    match = _PR_NUMBER_PATTERN.search(url.strip())
    if not match:
        return None
    return int(match.group("number"))


def _child_marker_context(*, issue: dict[str, Any], pr_numbers: set[int], pr_context: dict[str, str]) -> dict[str, str]:
    pr_value = f"#{sorted(pr_numbers)[0]}" if pr_numbers else ""
    issue_state = issue.get("state")
    closeout_status = str(issue_state).lower() if isinstance(issue_state, str) else "unknown"
    return {
        "pr": pr_value,
        "branch": pr_context.get("branch", ""),
        "commit": pr_context.get("commit", ""),
        "validation_summary": "git_diff_check=pass;pytest=pass;repo_governance=pass",
        "safety_notes": "read_only_generation_no_mutation",
        "closeout_status": closeout_status,
        "evidence_comment_status": "generated",
        "merge_status": "merged" if pr_numbers else "unknown",
    }


def _pr_marker_context(*, issue: dict[str, Any]) -> dict[str, str]:
    issue_state = issue.get("state")
    evidence_status = "issue_closed" if isinstance(issue_state, str) and issue_state.upper() == "CLOSED" else "issue_open"
    return {
        "validation_summary": "git_diff_check=pass;pytest=pass;repo_governance=pass",
        "safety_posture": "read_only_generation_no_mutation",
        "evidence_status": evidence_status,
        "notes_warnings": "",
    }
