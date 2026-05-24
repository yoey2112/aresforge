from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.canonical_evidence_markers import create_canonical_evidence_marker
from aresforge.operator.evidence_completeness_checker import check_milestone_evidence_readiness
from aresforge.operator.milestone_state_inspector import inspect_milestone_state
from aresforge.operator.parent_closeout_readiness import inspect_parent_closeout_readiness
from aresforge.operator.pr_mapping_preflight import inspect_pr_mapping_preflight


COMMAND_NAME = "generate-parent-closeout-marker-template"


def generate_parent_closeout_marker_template(
    config: AppConfig,
    *,
    parent_issue: int,
    state_file: str | Path | None = None,
    final_main_head: str | None = None,
    final_validation_results: str | None = None,
    safety_confirmations: str | None = None,
    warnings_deviations: str | None = None,
) -> dict[str, Any]:
    milestone = inspect_milestone_state(config, parent_issue=parent_issue, state_file=state_file)
    readiness = inspect_parent_closeout_readiness(config, parent_issue=parent_issue, state_file=state_file)
    pr_mapping = (
        check_milestone_evidence_readiness(config, parent_issue=parent_issue, state_file=state_file)
        if state_file is not None
        else inspect_pr_mapping_preflight(config, parent_issue=parent_issue)
    )

    child_issue_list = _render_child_issue_list(milestone)
    child_to_pr_mapping = (
        _render_child_to_pr_mapping_from_evidence(milestone=milestone, evidence=pr_mapping)
        if state_file is not None
        else _render_child_to_pr_mapping(pr_mapping)
    )
    offline_final_fields = _offline_final_fields(state_file) if state_file is not None else {}

    parent_closeout_ready = bool((readiness.get("closeout_readiness") or {}).get("parent_closeout_ready"))
    readiness_gate_summary = _render_readiness_summary(readiness)

    if state_file is not None:
        resolved_final_main_head = final_main_head or offline_final_fields.get("final_main_head") or ""
        resolved_final_validation_results = final_validation_results or offline_final_fields.get("final_validation_results") or ""
    else:
        resolved_final_main_head = final_main_head or ("<set-after-final-merge>" if parent_closeout_ready else "")
        resolved_final_validation_results = final_validation_results or (
            "<set-final-validation-results>" if parent_closeout_ready else ""
        )
    resolved_safety_confirmations = safety_confirmations or "read-only generation; targeted operator-approved mutation only"

    marker = create_canonical_evidence_marker(
        marker_type="parent_closeout_evidence",
        required_fields={
            "parent_issue": f"#{parent_issue}",
            "child_issue_list": child_issue_list,
            "child_to_pr_mapping": child_to_pr_mapping,
            "final_main_head": resolved_final_main_head,
            "final_validation_results": resolved_final_validation_results,
            "readiness_gate_summary": readiness_gate_summary,
            "safety_confirmations": resolved_safety_confirmations,
            "closeout_readiness_state": "ready" if parent_closeout_ready else "blocked",
        },
        optional_fields={
            "warnings_deviations": warnings_deviations or _render_warnings(readiness),
        },
    )

    return {
        "command": COMMAND_NAME,
        "ok": True,
        "read_only": True,
        "parent_issue": parent_issue,
        "parent_closeout_ready": parent_closeout_ready,
        "canonical_marker": marker.to_dict(),
        "canonical_marker_text": marker.render(),
        "targeted_parent_closeout_guidance": [
            f"1. Review and complete parent closeout marker fields for issue #{parent_issue}.",
            "2. Post one targeted parent evidence comment with the completed marker text.",
            f"3. Close only parent issue #{parent_issue} after readiness is true and blocked reasons are empty.",
        ],
        "safety_notes": [
            "Read-only marker generation only.",
            "No issue, PR, or closeout mutation was executed by this command.",
            "Use targeted operator-approved mutation commands separately when required.",
        ],
    }


def _render_child_issue_list(milestone: dict[str, Any]) -> str:
    children = milestone.get("child_issues") if isinstance(milestone.get("child_issues"), list) else []
    numbers = [
        int(item.get("issue_number"))
        for item in children
        if isinstance(item, dict) and isinstance(item.get("issue_number"), int)
    ]
    if not numbers:
        return ""
    return ", ".join(f"#{number}" for number in sorted(set(numbers)))


def _render_child_to_pr_mapping(pr_mapping: dict[str, Any]) -> str:
    children = pr_mapping.get("children") if isinstance(pr_mapping.get("children"), list) else []
    rows: list[str] = []
    for item in children:
        if not isinstance(item, dict):
            continue
        issue_number = item.get("issue_number")
        pr_number = item.get("normalized_pr_number")
        if not isinstance(issue_number, int):
            continue
        if isinstance(pr_number, int):
            rows.append(f"#{issue_number}->#{pr_number}")
        else:
            rows.append(f"#{issue_number}-><missing>")
    return ", ".join(rows)


def _render_child_to_pr_mapping_from_evidence(*, milestone: dict[str, Any], evidence: dict[str, Any]) -> str:
    child_numbers = [
        int(item.get("issue_number"))
        for item in (milestone.get("child_issues") or [])
        if isinstance(item, dict) and isinstance(item.get("issue_number"), int)
    ]
    evidence_rows = evidence.get("issues") if isinstance(evidence.get("issues"), list) else []
    issues_by_number: dict[int, dict[str, Any]] = {}
    for item in evidence_rows:
        if not isinstance(item, dict):
            continue
        issue = item.get("issue")
        if not isinstance(issue, dict):
            continue
        number = issue.get("number")
        if isinstance(number, int):
            issues_by_number[number] = issue

    rows: list[str] = []
    for issue_number in sorted(set(child_numbers)):
        issue_payload = issues_by_number.get(issue_number, {})
        pr_number = _resolve_pr_number(issue_payload)
        rows.append(f"#{issue_number}->#{pr_number}" if isinstance(pr_number, int) else f"#{issue_number}-><missing>")
    return ", ".join(rows)


def _resolve_pr_number(issue_payload: dict[str, Any]) -> int | None:
    merged_prs = issue_payload.get("merged_pr_evidence")
    if not isinstance(merged_prs, list):
        return None
    for item in merged_prs:
        if not isinstance(item, dict):
            continue
        number = item.get("number")
        if isinstance(number, int):
            return number
        url = item.get("url")
        if not isinstance(url, str):
            continue
        match = re.search(r"/pull/(?P<number>\d+)\b", url)
        if match:
            return int(match.group("number"))
    return None


def _offline_final_fields(state_file: str | Path) -> dict[str, str]:
    try:
        parsed = json.loads(Path(state_file).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(parsed, dict):
        return {}

    payload: dict[str, str] = {}
    final_main_head = parsed.get("final_main_head")
    if isinstance(final_main_head, str):
        payload["final_main_head"] = final_main_head
    final_validation_results = parsed.get("final_validation_results")
    if isinstance(final_validation_results, str):
        payload["final_validation_results"] = final_validation_results
    return payload


def _render_readiness_summary(readiness: dict[str, Any]) -> str:
    closeout = readiness.get("closeout_readiness") if isinstance(readiness.get("closeout_readiness"), dict) else {}
    parent_ready = closeout.get("parent_closeout_ready") is True
    blocked = readiness.get("blocked_reasons") if isinstance(readiness.get("blocked_reasons"), list) else []
    blocked_rows = [value for value in blocked if isinstance(value, str)]
    blocked_text = "none" if not blocked_rows else ", ".join(sorted(set(blocked_rows)))
    return f"parent_closeout_ready={str(parent_ready).lower()}; blocked_reasons={blocked_text}"


def _render_warnings(readiness: dict[str, Any]) -> str:
    warnings = readiness.get("warnings") if isinstance(readiness.get("warnings"), list) else []
    rows = [value for value in warnings if isinstance(value, str)]
    if not rows:
        return ""
    return "; ".join(sorted(set(rows)))
