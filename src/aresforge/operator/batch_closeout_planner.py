from __future__ import annotations

import re
import subprocess
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.planning_state import persist_closeout_snapshot, resolve_planning_state_path
from aresforge.operator.ready_issue_intake import PROTECTED_ISSUE_NUMBER, fetch_issue_batch_for_planning

READY = "ready"
PARTIALLY_READY = "partially_ready"
BLOCKED = "blocked"
INCOMPLETE = "incomplete"
AMBIGUOUS = "ambiguous"
DISCOVERY_SOURCE_PRIORITY = {
    "corrected_child_index": 0,
    "parent_comments": 1,
    "parent_body": 2,
    "child_body": 3,
}
_ISSUE_NUMBER_PATTERN = re.compile(r"#(?P<number>\d+)\b")
_CORRECTION_HINT_PATTERN = re.compile(
    r"\b(?:corrected|correction|updated|reposted|supersedes|replace|latest)\b",
    re.IGNORECASE,
)
_CHILD_INDEX_HINT_PATTERN = re.compile(r"\bchild\s+issue\s+index\b", re.IGNORECASE)
_PARENT_REF_LINE_PATTERN = re.compile(
    r"\b(?:parent\s+issue|parent)\s*:\s*#(?P<number>\d+)\b|\b(?:part\s+of|child\s+of)\s+#(?P<number2>\d+)\b",
    re.IGNORECASE,
)


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
    child_candidates, discovery_evidence = _collect_child_issue_numbers(parent)

    children_payload = fetch_issue_batch_for_planning(config, child_candidates)
    children = children_payload.get("issues") if isinstance(children_payload.get("issues"), list) else []

    child_parent_matches = _collect_child_parent_references(children, parent.get("number"))
    for number, evidence in child_parent_matches.items():
        discovery_evidence.setdefault(number, []).append(evidence)

    excluded_issues: list[dict[str, Any]] = []
    if isinstance(children_payload.get("excluded_issues"), list):
        excluded_issues.extend(item for item in children_payload["excluded_issues"] if isinstance(item, dict))

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
    flattened_discovery = _flatten_discovery_evidence(discovery_evidence)

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
            "discovered_child_issue_numbers": child_candidates,
            "discovery_evidence": flattened_discovery,
            "completed_children": completed_children,
            "open_or_blocked_children": open_or_blocked_children,
            "excluded_issues": excluded_issues,
        },
        "evidence_report": {
            "mutation_posture": "planning_only_no_close_or_comment",
            "discovered_child_links": flattened_discovery,
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


def _collect_child_issue_numbers(parent_issue: dict[str, Any]) -> tuple[list[int], dict[int, list[dict[str, Any]]]]:
    numbers: set[int] = set()
    evidence_by_child: dict[int, list[dict[str, Any]]] = {}
    references = parent_issue.get("reference_classification")
    if isinstance(references, dict):
        explicit = references.get("explicit_implementation_issue_numbers")
        if isinstance(explicit, list):
            for item in explicit:
                if isinstance(item, int):
                    numbers.add(item)
                    evidence_by_child.setdefault(item, []).append(
                        _discovery_entry("parent_body", "active", "reference_classification_explicit")
                    )
        impl = references.get("implementation_issue_numbers")
        if isinstance(impl, list):
            for item in impl:
                if isinstance(item, int):
                    numbers.add(item)
                    evidence_by_child.setdefault(item, []).append(
                        _discovery_entry("parent_body", "active", "reference_classification_implementation")
                    )

    body = parent_issue.get("body")
    if isinstance(body, str):
        _merge_text_discovery(
            text=body,
            source="parent_body",
            parent_number=parent_issue.get("number"),
            numbers=numbers,
            evidence_by_child=evidence_by_child,
            corrected=False,
        )

    comments = parent_issue.get("comments")
    if isinstance(comments, list):
        corrected_ids = _choose_corrected_child_index_comments(comments)
        for idx, comment in enumerate(comments):
            if not isinstance(comment, dict):
                continue
            comment_body = comment.get("body")
            if not isinstance(comment_body, str):
                continue
            comment_id = comment.get("id")
            fallback_id = idx
            marker = comment_id if isinstance(comment_id, int) else fallback_id
            is_corrected = marker in corrected_ids
            _merge_text_discovery(
                text=comment_body,
                source="corrected_child_index" if is_corrected else "parent_comments",
                parent_number=parent_issue.get("number"),
                numbers=numbers,
                evidence_by_child=evidence_by_child,
                corrected=is_corrected,
            )

    numbers.discard(PROTECTED_ISSUE_NUMBER)
    parent_number = parent_issue.get("number")
    if isinstance(parent_number, int):
        numbers.discard(parent_number)
        evidence_by_child.pop(parent_number, None)
    return sorted(numbers), evidence_by_child


def _collect_child_parent_references(children: list[dict[str, Any]], parent_number: Any) -> dict[int, dict[str, Any]]:
    if not isinstance(parent_number, int):
        return {}
    matches: dict[int, dict[str, Any]] = {}
    for issue in children:
        if not isinstance(issue, dict):
            continue
        number = issue.get("number")
        if not isinstance(number, int):
            continue
        body = issue.get("body")
        if not isinstance(body, str):
            continue
        if _child_body_links_parent(body, parent_number):
            matches[number] = _discovery_entry("child_body", "active", "child_body_parent_reference")
    return matches


def _child_body_links_parent(body: str, parent_number: int) -> bool:
    for raw_line in body.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if re.search(rf"\bparent\s+issue\s*:\s*#{parent_number}\b", line, re.IGNORECASE):
            return True
        if re.search(rf"\bparent\s*:\s*#{parent_number}\b", line, re.IGNORECASE):
            return True
        if re.search(rf"\bpart\s+of\s+#{parent_number}\b", line, re.IGNORECASE):
            return True
        if re.search(rf"\bchild\s+of\s+#{parent_number}\b", line, re.IGNORECASE):
            return True
    return False


def _merge_text_discovery(
    *,
    text: str,
    source: str,
    parent_number: Any,
    numbers: set[int],
    evidence_by_child: dict[int, list[dict[str, Any]]],
    corrected: bool,
) -> None:
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if "#" not in line:
            continue
        classification = _classify_line_for_discovery(line, source=source, parent_number=parent_number)
        for match in _ISSUE_NUMBER_PATTERN.finditer(line):
            number = int(match.group("number"))
            if classification == "active":
                numbers.add(number)
                evidence_by_child.setdefault(number, []).append(
                    _discovery_entry(
                        source,
                        classification,
                        "corrected_child_index_line" if corrected else "active_child_reference_line",
                    )
                )
            elif classification in {"historical", "safety", "protected"}:
                evidence_by_child.setdefault(number, []).append(
                    _discovery_entry(source, classification, "ignored_non_active_reference_line")
                )


def _classify_line_for_discovery(line: str, *, source: str, parent_number: Any) -> str:
    lower = line.lower()
    if "issue #39" in lower and ("protected" in lower or "historical" in lower or "do not modify" in lower):
        return "protected"
    if "historical" in lower or "retired" in lower:
        return "historical"
    if "do not modify" in lower or "must remain protected" in lower or "safety" in lower:
        return "safety"
    if source in {"parent_body", "parent_comments", "corrected_child_index"}:
        if "- [" in line and _ISSUE_NUMBER_PATTERN.search(line):
            return "active"
        if _CHILD_INDEX_HINT_PATTERN.search(line):
            return "active"
        if re.search(r"\bchild(?:ren)?\b", line, re.IGNORECASE) and _ISSUE_NUMBER_PATTERN.search(line):
            return "active"
    if isinstance(parent_number, int) and _PARENT_REF_LINE_PATTERN.search(line):
        if re.search(rf"#{parent_number}\b", line):
            return "active"
    return "incidental"


def _choose_corrected_child_index_comments(comments: list[dict[str, Any]]) -> set[int]:
    index_positions: list[tuple[int, int]] = []
    for idx, comment in enumerate(comments):
        if not isinstance(comment, dict):
            continue
        body = comment.get("body")
        if not isinstance(body, str):
            continue
        if _CHILD_INDEX_HINT_PATTERN.search(body) or re.search(r"-\s*\[[ xX]\]\s*#\d+", body):
            comment_id = comment.get("id")
            marker = comment_id if isinstance(comment_id, int) else idx
            index_positions.append((idx, marker))
    if not index_positions:
        return set()

    explicit_corrections = [
        item for item in index_positions if _CORRECTION_HINT_PATTERN.search(str(comments[item[0]].get("body") or ""))
    ]
    if explicit_corrections:
        return {item[1] for item in explicit_corrections}

    latest = max(index_positions, key=lambda item: item[0])
    return {latest[1]}


def _discovery_entry(source: str, classification: str, reason: str) -> dict[str, Any]:
    return {"source": source, "classification": classification, "reason": reason}


def _flatten_discovery_evidence(evidence_by_child: dict[int, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    flattened: list[dict[str, Any]] = []
    for child in sorted(evidence_by_child):
        evidence_items = evidence_by_child[child]
        if not isinstance(evidence_items, list):
            continue
        chosen = sorted(
            [item for item in evidence_items if isinstance(item, dict)],
            key=lambda item: (
                DISCOVERY_SOURCE_PRIORITY.get(str(item.get("source")), 999),
                str(item.get("classification", "")),
                str(item.get("reason", "")),
            ),
        )
        for item in chosen:
            flattened.append(
                {
                    "child_issue_number": child,
                    "source": item.get("source"),
                    "classification": item.get("classification"),
                    "reason": item.get("reason"),
                }
            )
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[Any, Any, Any, Any]] = set()
    for item in flattened:
        key = (
            item.get("child_issue_number"),
            item.get("source"),
            item.get("classification"),
            item.get("reason"),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


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
