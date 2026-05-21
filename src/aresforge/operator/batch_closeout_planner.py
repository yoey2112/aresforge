from __future__ import annotations

import subprocess
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.ready_issue_intake import (
    PROTECTED_ISSUE_NUMBER,
    fetch_issue_batch_for_planning,
)
from aresforge.operator.planning_state import persist_closeout_snapshot, resolve_planning_state_path

READY = "ready"
PARTIALLY_READY = "partially_ready"
BLOCKED = "blocked"
INCOMPLETE = "incomplete"
AMBIGUOUS = "ambiguous"


def plan_batch_closeout(
    config: AppConfig,
    *,
    parent_issue: int,
    write_planning_snapshot: bool = False,
    planning_state_path: str | None = None,
) -> dict[str, Any]:
    parent_payload = fetch_issue_batch_for_planning(config, [parent_issue])
    parent_issues = parent_payload.get("issues") if isinstance(parent_payload.get("issues"), list) else []
    if not parent_issues:
        return {
            "command": "plan-batch-closeout",
            "ok": False,
            "inspection_mode": "github_read_only",
            "repo": f"{config.github_owner}/{config.github_repo}",
            "error": "parent_issue_unavailable",
            "parent_issue": parent_issue,
            "warnings": parent_payload.get("warnings", []),
            "excluded_issues": parent_payload.get("excluded_issues", []),
        }

    parent = parent_issues[0]
    child_candidates = _collect_child_issue_numbers(parent)

    children_payload = fetch_issue_batch_for_planning(config, child_candidates)
    children = children_payload.get("issues") if isinstance(children_payload.get("issues"), list) else []

    excluded_issues: list[dict[str, Any]] = []
    if isinstance(children_payload.get("excluded_issues"), list):
        excluded_issues.extend(
            item for item in children_payload["excluded_issues"] if isinstance(item, dict)
        )

    child_evidence_report: list[dict[str, Any]] = []
    completed_children: list[dict[str, Any]] = []
    open_or_blocked_children: list[dict[str, Any]] = []

    for issue in children:
        number = issue.get("number")
        if not isinstance(number, int):
            continue
        if number == PROTECTED_ISSUE_NUMBER:
            excluded_issues.append({"number": number, "reason": "protected_issue"})
            continue

        item = _build_child_evidence_item(issue)
        child_evidence_report.append(item)
        if item["current_issue_state"] == "CLOSED":
            completed_children.append(
                {
                    "number": number,
                    "title": item["title"],
                    "state": item["current_issue_state"],
                    "url": item["url"],
                    "labels": issue.get("labels", []),
                    "pr_merge_evidence": item["merged_pr_evidence"],
                }
            )
        else:
            open_or_blocked_children.append(
                {
                    "number": number,
                    "title": item["title"],
                    "state": item["current_issue_state"],
                    "url": item["url"],
                    "labels": issue.get("labels", []),
                    "pr_merge_evidence": item["merged_pr_evidence"],
                }
            )

    child_evidence_report.sort(key=lambda item: item["number"])
    completed_children.sort(key=lambda item: item["number"])
    open_or_blocked_children.sort(key=lambda item: item["number"])
    excluded_issues = sorted(
        {
            (item.get("number"), item.get("reason")): item
            for item in excluded_issues
            if isinstance(item.get("number"), int)
        }.values(),
        key=lambda item: (item["number"], str(item.get("reason", ""))),
    )

    parent_readiness = _classify_parent_readiness(parent, child_evidence_report)

    response = {
        "command": "plan-batch-closeout",
        "ok": True,
        "inspection_mode": "github_read_only",
        "repo": f"{config.github_owner}/{config.github_repo}",
        "parent_issue": {
            "number": parent.get("number"),
            "title": parent.get("title"),
            "state": parent.get("state"),
            "url": parent.get("url"),
        },
        "child_issue_group": {
            "requested_child_issue_numbers": child_candidates,
            "completed_children": completed_children,
            "open_or_blocked_children": open_or_blocked_children,
            "excluded_issues": excluded_issues,
        },
        "evidence_report": {
            "mutation_posture": "planning_only_no_close_or_comment",
            "child_issues": child_evidence_report,
        },
        "closeout_plan": {
            "readiness": parent_readiness["readiness"],
            "readiness_signals": parent_readiness["signals"],
            "missing_evidence": parent_readiness["missing_evidence"],
            "human_actions_required": parent_readiness["actions"],
            "mutation_posture": "planning_only_no_close_or_comment",
        },
        "warnings": [
            "This command is read-only and does not close or comment on issues.",
            "Labels, milestones, PR state, and issue state were not mutated.",
            "Issue #39 remains protected historical evidence and is excluded from active closeout planning.",
        ],
    }
    if write_planning_snapshot:
        state_path = resolve_planning_state_path(config=config, path_override=planning_state_path)
        response["planning_state_write"] = persist_closeout_snapshot(
            path=state_path,
            snapshot=_build_closeout_snapshot(response),
            command_name="plan-batch-closeout",
        )
    return response


def _build_closeout_snapshot(payload: dict[str, Any]) -> dict[str, Any]:
    parent_issue = payload.get("parent_issue", {})
    number = parent_issue.get("number")
    snapshot_id = f"parent-{number}" if isinstance(number, int) else "parent-unknown"
    child_group = payload.get("child_issue_group", {})
    completed = child_group.get("completed_children")
    blocked = child_group.get("open_or_blocked_children")
    observed_children: list[dict[str, Any]] = []
    for item in (completed if isinstance(completed, list) else []):
        if isinstance(item, dict):
            observed_children.append({"number": item.get("number"), "title": item.get("title"), "state": item.get("state")})
    for item in (blocked if isinstance(blocked, list) else []):
        if isinstance(item, dict):
            observed_children.append({"number": item.get("number"), "title": item.get("title"), "state": item.get("state")})
    observed_children.sort(key=lambda entry: int(entry["number"]) if isinstance(entry.get("number"), int) else -1)
    return {
        "snapshot_id": snapshot_id,
        "parent_issue": number,
        "command": "plan-batch-closeout",
        "closeout_plan": payload.get("closeout_plan"),
        "evidence_report": payload.get("evidence_report"),
        "observed_children": observed_children,
    }


def _build_child_evidence_item(issue: dict[str, Any]) -> dict[str, Any]:
    number = int(issue.get("number"))
    state = str(issue.get("state") or "").upper()
    refs = issue.get("reference_classification")
    if not isinstance(refs, dict):
        refs = {}

    explicit_links = refs.get("explicit_implementation_issue_numbers")
    if not isinstance(explicit_links, list):
        explicit_links = []
    impl_links = refs.get("implementation_issue_numbers")
    if not isinstance(impl_links, list):
        impl_links = []
    safety_links = refs.get("safety_or_historical_issue_numbers")
    if not isinstance(safety_links, list):
        safety_links = []

    merged_pr_evidence = issue.get("merged_pr_evidence")
    if not isinstance(merged_pr_evidence, list):
        merged_pr_evidence = []

    validation_evidence = _extract_section_commands(issue.get("body"), "Validation")
    docs_evidence = _extract_section_commands(issue.get("body"), "Documentation")

    missing: list[str] = []
    signals: list[str] = []

    if state == "CLOSED":
        signals.append("issue_state_closed")
    else:
        missing.append("issue_not_closed")

    if explicit_links:
        signals.append("explicit_implementation_linkage_detected")
    elif impl_links:
        signals.append("implementation_linkage_detected_non_explicit")
        missing.append("explicit_linkage_line_not_detected")
    else:
        missing.append("implementation_linkage_missing")

    if merged_pr_evidence:
        signals.append("merged_pr_evidence_detected")
    else:
        missing.append("merged_pr_evidence_missing")

    if validation_evidence:
        signals.append("validation_evidence_detected")
    else:
        missing.append("validation_evidence_missing")

    if docs_evidence:
        signals.append("documentation_reconciliation_evidence_detected")
    else:
        missing.append("documentation_reconciliation_evidence_missing")

    protected_misuse = bool(refs.get("contains_protected_issue_implementation_link"))
    if protected_misuse:
        signals.append("protected_issue_implementation_link_detected")
        missing.append("protected_reference_safety_violation")

    classification = READY
    if protected_misuse:
        classification = BLOCKED
    elif "implementation_linkage_missing" in missing:
        classification = AMBIGUOUS
    elif any(item.startswith("documentation_") or item.startswith("validation_") for item in missing):
        classification = INCOMPLETE
    elif "issue_not_closed" in missing:
        classification = PARTIALLY_READY

    return {
        "number": number,
        "title": issue.get("title"),
        "url": issue.get("url"),
        "current_issue_state": state,
        "merged_pr_evidence": merged_pr_evidence,
        "validation_or_documentation_evidence": {
            "validation": validation_evidence,
            "documentation_reconciliation": docs_evidence,
        },
        "reference_classification": {
            "implementation_issue_numbers": impl_links,
            "explicit_implementation_issue_numbers": explicit_links,
            "safety_or_historical_issue_numbers": safety_links,
        },
        "missing_evidence": sorted(set(missing)),
        "readiness_classification": classification,
        "readiness_signals": sorted(set(signals)),
        "human_closeout_required": True,
    }


def _extract_section_commands(body: Any, heading: str) -> list[str]:
    if not isinstance(body, str) or not body.strip():
        return []
    lines = body.splitlines()
    in_section = False
    found: list[str] = []
    heading_lower = heading.lower()
    for raw in lines:
        line = raw.strip()
        if line.startswith("## "):
            current = line[3:].strip().lower()
            in_section = current == heading_lower
            continue
        if in_section and line.startswith("- "):
            found.append(line[2:].strip())
    return sorted(set(item for item in found if item))


def _classify_parent_readiness(parent: dict[str, Any], children: list[dict[str, Any]]) -> dict[str, Any]:
    signals = ["human_gated_closeout_required"]
    missing: list[str] = []
    actions = [
        "Review child issue evidence report and resolve missing evidence.",
        "Confirm final parent issue narrative and reconciliation details.",
        "Run human-triggered PR merge/issue closeout only after review.",
    ]

    if not children:
        return {
            "readiness": AMBIGUOUS,
            "signals": signals,
            "missing_evidence": ["child_issues_unavailable_or_unlinked"],
            "actions": actions,
        }

    child_states = {item["readiness_classification"] for item in children}

    if BLOCKED in child_states:
        signals.append("blocked_child_detected")
        missing.append("protected_reference_or_safety_blockers_present")
        readiness = BLOCKED
    elif AMBIGUOUS in child_states:
        signals.append("ambiguous_child_linkage_detected")
        missing.append("explicit_implementation_linkage_required")
        readiness = AMBIGUOUS
    elif INCOMPLETE in child_states:
        signals.append("incomplete_child_evidence_detected")
        missing.append("validation_or_documentation_evidence_missing")
        readiness = INCOMPLETE
    elif PARTIALLY_READY in child_states:
        signals.append("open_or_unclosed_children_detected")
        missing.append("all_child_issues_must_be_closed")
        readiness = PARTIALLY_READY
    else:
        signals.append("all_child_evidence_ready")
        readiness = READY

    parent_body = parent.get("body") if isinstance(parent.get("body"), str) else ""
    if "reconciliation" not in parent_body.lower() and "source-of-truth" not in parent_body.lower():
        missing.append("parent_reconciliation_expectation_not_detected")
        if readiness == READY:
            readiness = INCOMPLETE

    return {
        "readiness": readiness,
        "signals": sorted(set(signals)),
        "missing_evidence": sorted(set(missing)),
        "actions": actions,
    }


def _collect_child_issue_numbers(parent_issue: dict[str, Any]) -> list[int]:
    numbers: set[int] = set()
    references = parent_issue.get("reference_classification")
    if isinstance(references, dict):
        explicit = references.get("explicit_implementation_issue_numbers")
        if isinstance(explicit, list):
            for item in explicit:
                if isinstance(item, int):
                    numbers.add(item)
        impl = references.get("implementation_issue_numbers")
        if isinstance(impl, list):
            for item in impl:
                if isinstance(item, int):
                    numbers.add(item)

    body = parent_issue.get("body")
    if isinstance(body, str):
        for raw_line in body.splitlines():
            line = raw_line.strip()
            if "#" not in line:
                continue
            if "- [" not in line and "child" not in line.lower() and "part of" not in line.lower():
                continue
            for token in line.split():
                if token.startswith("#") and token[1:].rstrip(",.)").isdigit():
                    numbers.add(int(token[1:].rstrip(",.)")))

    numbers.discard(PROTECTED_ISSUE_NUMBER)
    parent_number = parent_issue.get("number")
    if isinstance(parent_number, int):
        numbers.discard(parent_number)
    return sorted(numbers)


def current_branch(repo_root: str) -> str | None:
    result = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    value = result.stdout.strip()
    return value or None
