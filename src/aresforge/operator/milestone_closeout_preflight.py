from __future__ import annotations

from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.child_evidence_marker_preflight import inspect_child_evidence_marker_preflight
from aresforge.operator.closeout_repair_guidance import generate_closeout_preflight_repair_guidance
from aresforge.operator.parent_child_linkage_preflight import inspect_parent_child_linkage_preflight
from aresforge.operator.pr_mapping_preflight import inspect_pr_mapping_preflight


COMMAND_NAME = "inspect-milestone-closeout-preflight"


def inspect_milestone_closeout_preflight(config: AppConfig, *, parent_issue: int) -> dict[str, Any]:
    linkage = inspect_parent_child_linkage_preflight(config, parent_issue=parent_issue)
    evidence = inspect_child_evidence_marker_preflight(config, parent_issue=parent_issue)
    pr_mapping = inspect_pr_mapping_preflight(config, parent_issue=parent_issue)
    repair = generate_closeout_preflight_repair_guidance(config, parent_issue=parent_issue)

    failures = _collect_failures(linkage=linkage, evidence=evidence, pr_mapping=pr_mapping, repair=repair)
    if failures:
        return {
            "command": COMMAND_NAME,
            "ok": False,
            "read_only": True,
            "error": "milestone_closeout_preflight_dependency_failed",
            "parent_issue": parent_issue,
            "failures": failures,
            "required_operator_actions": [
                "Resolve dependency command failures before relying on milestone closeout preflight readiness.",
            ],
        }

    blocked_reasons = _combine_reasons(
        linkage.get("blocked_reasons"),
        evidence.get("blocked_reasons"),
        pr_mapping.get("blocked_reasons"),
    )
    warning_reasons = _combine_reasons(
        linkage.get("warning_reasons"),
        evidence.get("warning_reasons"),
        pr_mapping.get("warning_reasons"),
    )
    unknown_reasons = _combine_reasons(
        linkage.get("unknown_reasons"),
        evidence.get("unknown_reasons"),
        pr_mapping.get("unknown_reasons"),
    )
    repair_guidance = _combine_reasons(repair.get("guidance", {}).get("parent_repair"), repair.get("guidance", {}).get("child_repair"), repair.get("guidance", {}).get("pr_mapping_repair"), repair.get("guidance", {}).get("evidence_marker_repair"))

    if blocked_reasons:
        aggregate_state = "blocked"
    elif warning_reasons:
        aggregate_state = "warning"
    elif unknown_reasons:
        aggregate_state = "unknown"
    else:
        aggregate_state = "ready"

    closeout_ready = len(blocked_reasons) == 0 and len(warning_reasons) == 0 and len(unknown_reasons) == 0

    return {
        "command": COMMAND_NAME,
        "ok": True,
        "read_only": True,
        "parent_issue": parent_issue,
        "closeout_preflight": {
            "aggregate_state": aggregate_state,
            "closeout_ready": closeout_ready,
            "blocked_reason_count": len(blocked_reasons),
            "warning_reason_count": len(warning_reasons),
            "unknown_reason_count": len(unknown_reasons),
        },
        "blocked_reasons": blocked_reasons,
        "warning_reasons": warning_reasons,
        "unknown_reasons": unknown_reasons,
        "repair_guidance": repair_guidance,
        "preflight_checks": {
            "parent_child_linkage": linkage.get("lineage_summary"),
            "child_evidence_markers": evidence.get("evidence_summary"),
            "pr_mapping": pr_mapping.get("pr_mapping_summary"),
        },
        "required_operator_actions": _required_actions(
            closeout_ready=closeout_ready,
            blocked_reasons=blocked_reasons,
            warning_reasons=warning_reasons,
            unknown_reasons=unknown_reasons,
        ),
        "boundary_confirmations": [
            "Read-only orchestration command only.",
            "No GitHub mutation was executed.",
            "Repair guidance is copy/paste guidance only and does not execute mutation.",
        ],
    }


def _collect_failures(
    *,
    linkage: dict[str, Any],
    evidence: dict[str, Any],
    pr_mapping: dict[str, Any],
    repair: dict[str, Any],
) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    for command, payload in (
        ("inspect-parent-child-linkage-preflight", linkage),
        ("inspect-child-evidence-marker-preflight", evidence),
        ("inspect-pr-mapping-preflight", pr_mapping),
        ("generate-closeout-preflight-repair-guidance", repair),
    ):
        if bool(payload.get("ok")):
            continue
        failures.append({"command": command, "error": payload.get("error", "unknown_error")})
    return failures


def _combine_reasons(*groups: Any) -> list[str]:
    merged: list[str] = []
    for group in groups:
        if not isinstance(group, list):
            continue
        merged.extend(item for item in group if isinstance(item, str))
    return sorted(set(merged))


def _required_actions(
    *,
    closeout_ready: bool,
    blocked_reasons: list[str],
    warning_reasons: list[str],
    unknown_reasons: list[str],
) -> list[str]:
    if closeout_ready:
        return [
            "Milestone closeout preflight is ready; proceed to parent closeout readiness and evidence bundle generation.",
        ]

    actions: list[str] = []
    if blocked_reasons:
        actions.append("Resolve blocked preflight findings before parent closeout.")
    if warning_reasons:
        actions.append("Resolve warning preflight findings before parent closeout.")
    if unknown_reasons:
        actions.append("Resolve unknown preflight findings before parent closeout.")
    return actions
