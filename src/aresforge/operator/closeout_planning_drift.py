from __future__ import annotations

from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.batch_closeout_planner import plan_batch_closeout
from aresforge.operator.planning_state import load_planning_state
from aresforge.operator.ready_issue_intake import PROTECTED_ISSUE_NUMBER, fetch_issue_batch_for_planning


_PROTECTED_CLASSIFICATIONS = {"protected", "historical", "safety"}


def inspect_closeout_planning_drift(
    config: AppConfig,
    *,
    parent_issue: int,
    planning_state_path: str,
) -> dict[str, Any]:
    loaded = load_planning_state(path=Path(planning_state_path))
    if not loaded.exists:
        return {
            "command": "inspect-closeout-planning-drift",
            "ok": True,
            "inspection_mode": "github_read_only",
            "state_exists": False,
            "planning_state_path": str(loaded.path),
            "parent_issue": parent_issue,
            "planned_child_issues": [],
            "discovered_child_issues": [],
            "matching_child_issues": [],
            "planned_missing_from_discovery": [],
            "discovered_extra_not_planned": [],
            "closed_child_issues": [],
            "open_child_issues": [],
            "unresolved_child_issues": [],
            "protected_or_historical_references_excluded": [],
            "readiness_ok": False,
            "evidence_summary": {
                "status": "planning_state_missing",
                "evidence_blocked_by_drift": True,
                "missing_evidence": ["planning_state_missing"],
                "present_evidence": [],
                "not_applicable_evidence": [],
            },
            "warnings": ["No local planning state file exists."],
        }
    if not loaded.valid or loaded.data is None:
        return {
            "command": "inspect-closeout-planning-drift",
            "ok": False,
            "inspection_mode": "github_read_only",
            "state_exists": True,
            "planning_state_path": str(loaded.path),
            "parent_issue": parent_issue,
            "validation_errors": loaded.errors,
        }

    planned_child_issues, protected_from_planning = _planned_children_for_parent(loaded.data, parent_issue)
    closeout = plan_batch_closeout(config, parent_issue=parent_issue)
    if not bool(closeout.get("ok")):
        return {
            "command": "inspect-closeout-planning-drift",
            "ok": False,
            "inspection_mode": "github_read_only",
            "state_exists": True,
            "planning_state_path": str(loaded.path),
            "parent_issue": parent_issue,
            "planned_child_issues": planned_child_issues,
            "error": "closeout_discovery_unavailable",
            "closeout_error": closeout.get("error"),
            "warnings": closeout.get("warnings", []),
        }

    discovered_child_issues = _ints(closeout.get("child_issue_group", {}).get("discovered_child_issue_numbers"))
    planned_set = set(planned_child_issues)
    discovered_set = set(discovered_child_issues)
    matching = sorted(planned_set & discovered_set)
    planned_missing = sorted(planned_set - discovered_set)
    discovered_extra = sorted(discovered_set - planned_set)

    protected_refs = _protected_references_from_closeout(closeout)
    protected_refs.extend(protected_from_planning)
    protected_refs = _dedupe_refs(protected_refs)

    compared_numbers = sorted(planned_set | discovered_set)
    closed_child_issues: list[int] = []
    open_child_issues: list[int] = []
    unresolved_child_issues: list[int] = []
    if compared_numbers:
        fetched = fetch_issue_batch_for_planning(config, compared_numbers)
        issues = fetched.get("issues") if isinstance(fetched.get("issues"), list) else []
        states: dict[int, str] = {}
        for issue in issues:
            if not isinstance(issue, dict):
                continue
            number = issue.get("number")
            if not isinstance(number, int):
                continue
            states[number] = str(issue.get("state") or "").upper()
        for number in compared_numbers:
            state = states.get(number)
            if state == "CLOSED":
                closed_child_issues.append(number)
            elif state in {"OPEN", "DRAFT"}:
                open_child_issues.append(number)
            else:
                unresolved_child_issues.append(number)

    summary = _build_evidence_summary(
        closeout=closeout,
        planned_missing=planned_missing,
        discovered_extra=discovered_extra,
        unresolved=unresolved_child_issues,
    )

    return {
        "command": "inspect-closeout-planning-drift",
        "ok": True,
        "inspection_mode": "github_read_only",
        "state_exists": True,
        "planning_state_path": str(loaded.path),
        "parent_issue": parent_issue,
        "planned_child_issues": planned_child_issues,
        "discovered_child_issues": discovered_child_issues,
        "matching_child_issues": matching,
        "planned_missing_from_discovery": planned_missing,
        "discovered_extra_not_planned": discovered_extra,
        "closed_child_issues": closed_child_issues,
        "open_child_issues": open_child_issues,
        "unresolved_child_issues": unresolved_child_issues,
        "protected_or_historical_references_excluded": protected_refs,
        "readiness_ok": bool(summary.get("readiness_ok")),
        "evidence_summary": summary,
    }


def _planned_children_for_parent(data: dict[str, Any], parent_issue: int) -> tuple[list[int], list[dict[str, Any]]]:
    sprint_plans = data.get("sprint_plans") if isinstance(data.get("sprint_plans"), list) else []
    planned: set[int] = set()
    protected_refs: list[dict[str, Any]] = []
    for plan in sprint_plans:
        if not isinstance(plan, dict):
            continue
        parent = plan.get("parent_issue")
        if not isinstance(parent, dict) or parent.get("number") != parent_issue:
            continue
        children = plan.get("children")
        if isinstance(children, list):
            for child in children:
                if not isinstance(child, dict):
                    continue
                number = child.get("number")
                if not isinstance(number, int):
                    continue
                if number == PROTECTED_ISSUE_NUMBER:
                    protected_refs.append(
                        {
                            "child_issue_number": number,
                            "classification": "protected",
                            "reason": "planning_state_child_excluded",
                            "source": "planning_state",
                        }
                    )
                    continue
                planned.add(number)
    return sorted(planned), protected_refs


def _protected_references_from_closeout(closeout: dict[str, Any]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    links = closeout.get("evidence_report", {}).get("discovered_child_links")
    if isinstance(links, list):
        for item in links:
            if not isinstance(item, dict):
                continue
            classification = str(item.get("classification") or "")
            if classification not in _PROTECTED_CLASSIFICATIONS:
                continue
            number = item.get("child_issue_number")
            if not isinstance(number, int):
                continue
            refs.append(
                {
                    "child_issue_number": number,
                    "classification": classification,
                    "reason": item.get("reason"),
                    "source": item.get("source"),
                }
            )
    return refs


def _build_evidence_summary(
    *,
    closeout: dict[str, Any],
    planned_missing: list[int],
    discovered_extra: list[int],
    unresolved: list[int],
) -> dict[str, Any]:
    closeout_plan = closeout.get("closeout_plan") if isinstance(closeout.get("closeout_plan"), dict) else {}
    child_issues = closeout.get("evidence_report", {}).get("child_issues")
    child_issues = child_issues if isinstance(child_issues, list) else []

    merged_count = 0
    missing_by_child_count = 0
    for child in child_issues:
        if not isinstance(child, dict):
            continue
        merged = child.get("merged_pr_evidence")
        if isinstance(merged, list) and merged:
            merged_count += 1
        missing = child.get("missing_evidence")
        if isinstance(missing, list) and missing:
            missing_by_child_count += 1

    missing_evidence = _strings(closeout_plan.get("missing_evidence"))
    if planned_missing:
        missing_evidence.append("planned_children_missing_from_live_discovery")
    if discovered_extra:
        missing_evidence.append("live_discovered_children_not_in_planning_state")
    if unresolved:
        missing_evidence.append("some_child_issue_states_unresolved")
    missing_evidence = sorted(set(missing_evidence))

    blocked_by_drift = bool(planned_missing or discovered_extra or unresolved)
    base_readiness = str(closeout_plan.get("readiness") or "ambiguous")
    status = "drift_blocked" if blocked_by_drift else base_readiness
    readiness_ok = (status == "ready") and not blocked_by_drift

    present = []
    if merged_count:
        present.append("merged_pr_evidence_present")
    if child_issues:
        present.append("child_evidence_rows_present")

    return {
        "status": status,
        "closeout_readiness_from_discovery": base_readiness,
        "readiness_ok": readiness_ok,
        "evidence_blocked_by_drift": blocked_by_drift,
        "present_evidence": sorted(present),
        "missing_evidence": missing_evidence,
        "not_applicable_evidence": [],
        "metrics": {
            "child_issue_count": len(child_issues),
            "merged_pr_evidence_count": merged_count,
            "child_issues_with_missing_evidence_count": missing_by_child_count,
            "planned_missing_count": len(planned_missing),
            "discovered_extra_count": len(discovered_extra),
            "unresolved_child_count": len(unresolved),
        },
    }


def _ints(value: Any) -> list[int]:
    if not isinstance(value, list):
        return []
    return sorted({item for item in value if isinstance(item, int) and item != PROTECTED_ISSUE_NUMBER})


def _strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return sorted({str(item) for item in value if isinstance(item, str) and item.strip()})


def _dedupe_refs(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[Any, Any, Any, Any]] = set()
    deduped: list[dict[str, Any]] = []
    for item in items:
        key = (
            item.get("child_issue_number"),
            item.get("classification"),
            item.get("reason"),
            item.get("source"),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    deduped.sort(
        key=lambda item: (
            int(item.get("child_issue_number")) if isinstance(item.get("child_issue_number"), int) else -1,
            str(item.get("classification", "")),
            str(item.get("reason", "")),
            str(item.get("source", "")),
        )
    )
    return deduped
