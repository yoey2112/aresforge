from __future__ import annotations

from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.evidence_bundle import EvidenceBundleInput, render_evidence_bundle_text
from aresforge.operator.evidence_completeness_checker import check_milestone_evidence_readiness
from aresforge.operator.milestone_state_inspector import inspect_milestone_state
from aresforge.operator.parent_closeout_marker_template import generate_parent_closeout_marker_template
from aresforge.operator.parent_closeout_readiness import inspect_parent_closeout_readiness
from aresforge.operator.validation_summary import ValidationEntryInput, build_validation_summary

COMMAND_NAME = "generate-parent-closeout-evidence-bundle"


def generate_parent_closeout_evidence_bundle(config: AppConfig, *, parent_issue: int) -> dict[str, Any]:
    milestone = inspect_milestone_state(config, parent_issue=parent_issue)
    evidence = check_milestone_evidence_readiness(config, parent_issue=parent_issue)
    readiness = inspect_parent_closeout_readiness(config, parent_issue=parent_issue)

    failures = _collect_failures(milestone=milestone, evidence=evidence, readiness=readiness)
    if failures:
        return {
            "command": COMMAND_NAME,
            "ok": False,
            "read_only": True,
            "parent_issue": parent_issue,
            "error": "parent_closeout_bundle_dependency_failed",
            "failures": failures,
            "targeted_parent_closeout_guidance": [
                "Resolve dependency command failures before generating parent closeout evidence.",
                f"Do not close parent issue #{parent_issue} while dependency failures remain.",
            ],
        }

    parent = milestone.get("parent_issue") if isinstance(milestone.get("parent_issue"), dict) else {}
    child_items = milestone.get("child_issues") if isinstance(milestone.get("child_issues"), list) else []
    child_rows = readiness.get("child_lineage") if isinstance(readiness.get("child_lineage"), list) else []
    blocked_reasons = sorted(
        reason
        for reason in (readiness.get("blocked_reasons") or [])
        if isinstance(reason, str)
    )
    closeout = readiness.get("closeout_readiness") if isinstance(readiness.get("closeout_readiness"), dict) else {}
    parent_closeout_ready = closeout.get("parent_closeout_ready") is True

    closed_count = 0
    accounted_count = 0
    for row in child_rows:
        if not isinstance(row, dict):
            continue
        if row.get("individually_closed") is True:
            closed_count += 1
        if row.get("accounted_for") is True:
            accounted_count += 1

    child_count = len([item for item in child_items if isinstance(item, dict)])
    pr_mappings = _child_pr_mappings(evidence)
    validation_summary = build_validation_summary(
        [
            ValidationEntryInput(command="python -m aresforge inspect-milestone-state", state="pass"),
            ValidationEntryInput(command="python -m aresforge check-milestone-evidence-readiness", state="pass"),
            ValidationEntryInput(
                command="python -m aresforge inspect-parent-closeout-readiness",
                state="pass",
            ),
            ValidationEntryInput(
                command="parent_closeout_ready_gate",
                state="pass" if parent_closeout_ready else "fail",
            ),
            ValidationEntryInput(
                command="blocked_reasons",
                output=(", ".join(blocked_reasons) if blocked_reasons else "none"),
                state="warning" if blocked_reasons else "pass",
            ),
        ]
    )
    canonical = generate_parent_closeout_marker_template(
        config,
        parent_issue=parent_issue,
    )
    canonical_marker_text = str(canonical.get("canonical_marker_text") or "")

    evidence_comment_body = render_evidence_bundle_text(
        EvidenceBundleInput(
            summary_lines=(
                f"- Parent closeout evidence bundle generated for issue #{parent_issue}.",
                f"- Child closure summary: {closed_count}/{child_count} closed.",
                f"- Child accounting summary: {accounted_count}/{child_count} accounted for.",
                (
                    "- Parent closeout readiness: READY."
                    if parent_closeout_ready
                    else "- Parent closeout readiness: BLOCKED (see notes/warnings)."
                ),
            ),
            issue_ref=f"Issue: #{parent_issue}",
            pr_ref="PR: <none>",
            branch_name="<none>",
            commit_sha="<none>",
            files_changed=("Read-only generator command; no repository files changed.",),
            validation_lines=tuple(validation_summary["summary_lines"]),
            safety_notes=(
                "- Read-only by default.",
                "- Parent issue is never closed by this command.",
                "- Targeted closeout requires explicit operator approval.",
                "- Bulk closure is forbidden.",
            ),
            warnings=(
                tuple(f"- Blocked reason: {reason}" for reason in blocked_reasons)
                if blocked_reasons
                else ("- <none>",)
            ),
        )
    )
    evidence_comment_body += "\n### Canonical Marker\n\n"
    evidence_comment_body += canonical_marker_text if canonical_marker_text else "<missing>\n"

    return {
        "command": COMMAND_NAME,
        "ok": True,
        "read_only": True,
        "parent_issue": {
            "issue_number": parent_issue,
            "state": parent.get("state"),
            "title": parent.get("title"),
            "url": parent.get("url"),
        },
        "child_summary": {
            "child_issue_count": child_count,
            "closed_child_issue_count": closed_count,
            "accounted_for_child_issue_count": accounted_count,
        },
        "child_states": _child_state_rows(child_rows),
        "child_pr_mappings": pr_mappings,
        "readiness_gates": {
            "parent_closeout_ready": parent_closeout_ready,
            "blocked_reasons": blocked_reasons,
        },
        "canonical_marker": canonical.get("canonical_marker"),
        "canonical_marker_text": canonical_marker_text,
        "parent_evidence_comment_body": evidence_comment_body,
        "targeted_parent_closeout_guidance": _targeted_guidance(
            parent_issue=parent_issue,
            parent_closeout_ready=parent_closeout_ready,
            blocked_reasons=blocked_reasons,
        ),
        "safety_notes": [
            "Read-only command; no GitHub mutation executed.",
            "Do not close parent issue until readiness gates report parent_closeout_ready=true.",
            "Post evidence comment and close parent as separate targeted operator-approved steps.",
        ],
    }


def _collect_failures(
    *,
    milestone: dict[str, Any],
    evidence: dict[str, Any],
    readiness: dict[str, Any],
) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    for command, payload in (
        ("inspect-milestone-state", milestone),
        ("check-milestone-evidence-readiness", evidence),
        ("inspect-parent-closeout-readiness", readiness),
    ):
        if bool(payload.get("ok")):
            continue
        failures.append(
            {
                "command": command,
                "error": payload.get("error", "unknown_error"),
                "details": payload,
            }
        )
    return failures


def _child_pr_mappings(evidence_payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    issues = evidence_payload.get("issues") if isinstance(evidence_payload.get("issues"), list) else []
    for item in issues:
        if not isinstance(item, dict):
            continue
        issue = item.get("issue") if isinstance(item.get("issue"), dict) else {}
        number = issue.get("number")
        if not isinstance(number, int):
            continue
        merged_pr_evidence = issue.get("merged_pr_evidence")
        pr_urls: list[str] = []
        if isinstance(merged_pr_evidence, list):
            for candidate in merged_pr_evidence:
                if isinstance(candidate, dict):
                    url = candidate.get("url")
                    if isinstance(url, str) and url.strip():
                        pr_urls.append(url.strip())
        rows.append(
            {
                "issue_number": number,
                "classification": item.get("classification"),
                "merged_pr_count": len(pr_urls),
                "merged_pr_urls": sorted(set(pr_urls)),
            }
        )
    rows.sort(key=lambda row: int(row["issue_number"]))
    return rows


def _child_state_rows(child_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in child_rows:
        if not isinstance(row, dict):
            continue
        issue_number = row.get("issue_number")
        if not isinstance(issue_number, int):
            continue
        rows.append(
            {
                "issue_number": issue_number,
                "state": row.get("state"),
                "classification": row.get("classification"),
                "lineage_detected": bool(row.get("lineage_detected")),
                "individually_closed": bool(row.get("individually_closed")),
                "accounted_for": bool(row.get("accounted_for")),
            }
        )
    rows.sort(key=lambda row: int(row["issue_number"]))
    return rows
def _targeted_guidance(*, parent_issue: int, parent_closeout_ready: bool, blocked_reasons: list[str]) -> list[str]:
    if not parent_closeout_ready:
        reason_text = ", ".join(blocked_reasons) if blocked_reasons else "unknown_blocker"
        return [
            f"1. Do not close parent issue #{parent_issue}; readiness is blocked.",
            f"2. Resolve blocked reasons: {reason_text}.",
            f"3. Re-run: python -m aresforge {COMMAND_NAME} --parent-issue {parent_issue}",
        ]
    return [
        f"1. Post parent evidence comment to issue #{parent_issue} after operator review.",
        f"2. Targeted closeout (separate explicit step): gh issue close {parent_issue} --comment \"Parent closeout executed after readiness confirmation.\"",
        f"3. Confirm parent issue #{parent_issue} is CLOSED and all child issues remain accounted for.",
    ]