from __future__ import annotations

import json
from typing import Any

from aresforge.artifacts.store import write_markdown_json_bundle
from aresforge.config import AppConfig
from aresforge.operator.ready_issue_intake import (
    PROTECTED_ISSUE_NUMBER,
    READY_TRIGGER_LABEL,
    inspect_ready_issue,
    list_ready_issues,
)
from aresforge.operator.ready_issue_planning import plan_ready_issue
from aresforge.operator.service import render_codex_handoff

BATCH_AUTOMERGE_LABEL = "aresforge-automerge"


def run_ready_issue_batch(
    config: AppConfig,
    *,
    plan_only: bool = True,
    write_selected_handoffs: bool = False,
    timestamp_override: str | None = None,
) -> dict[str, Any]:
    ready_listing = list_ready_issues(config)
    listing_ok = bool(ready_listing.get("ok"))
    listed_issues = ready_listing.get("issues") if isinstance(ready_listing.get("issues"), list) else []

    summaries: list[dict[str, Any]] = []
    selected_handoffs: list[dict[str, Any]] = []
    excluded_issues: list[dict[str, Any]] = []

    for listed_issue in listed_issues:
        issue_number = listed_issue.get("number")
        if not isinstance(issue_number, int):
            continue
        if issue_number == PROTECTED_ISSUE_NUMBER:
            excluded_issues.append({"number": issue_number, "reason": "protected_issue"})
            continue

        inspection = inspect_ready_issue(config, issue_number)
        plan = plan_ready_issue(config, issue_number)

        issue_title = _coerce_str(plan.get("issue_title")) or _coerce_str(listed_issue.get("title"))
        issue_labels = _normalize_labels(inspection, listed_issue)
        inspect_ok = bool(inspection.get("ok"))
        blocked_reasons = _collect_blocked_reasons(inspection, plan)
        blocked = bool(plan.get("blocked")) or bool(blocked_reasons)

        closeout_automation_eligible = (
            inspect_ok
            and issue_number != PROTECTED_ISSUE_NUMBER
            and not blocked
            and _label_present(issue_labels, READY_TRIGGER_LABEL)
            and _label_present(issue_labels, BATCH_AUTOMERGE_LABEL)
        )

        model_tier = _coerce_str(plan.get("selected_model_tier"))
        handoff_json_path: str | None = None
        if write_selected_handoffs and model_tier in {"copilot", "codex"} and inspect_ok and not blocked:
            handoff_bundle = render_codex_handoff(
                config=config,
                title=f"Issue {issue_number} batch implementation handoff",
                summary=(
                    f"Batch-selected implementation handoff for Issue #{issue_number}: "
                    f"{issue_title or 'Untitled issue'}"
                ),
                work_item_id=None,
                route_plan=None,
                requested_output=(
                    f"Implement Issue #{issue_number} using the planned agent/model routing "
                    "and QA safety gates."
                ),
                latest_review_package=None,
            )
            handoff_json_path = str(handoff_bundle.json_path)
            selected_handoffs.append(
                {
                    "issue_number": issue_number,
                    "model_tier": model_tier,
                    "handoff_json_path": handoff_json_path,
                }
            )

        summaries.append(
            {
                "issue_number": issue_number,
                "issue_title": issue_title,
                "ready_status": inspect_ok,
                "blocked": blocked,
                "blocked_reasons": blocked_reasons,
                "selected_primary_agent": _coerce_str(plan.get("selected_primary_agent")),
                "selected_qa_agent": _coerce_str(plan.get("selected_qa_agent")),
                "selected_documentation_agent": _coerce_str(
                    plan.get("selected_documentation_agent")
                ),
                "model_tier": model_tier,
                "routing_reason": _coerce_str(plan.get("model_routing_reason")),
                "confidence": _coerce_str(plan.get("confidence")),
                "required_labels": [READY_TRIGGER_LABEL, BATCH_AUTOMERGE_LABEL],
                "closeout_automation_eligible": closeout_automation_eligible,
                "recommended_next_command": _recommended_next_command(
                    issue_number=issue_number,
                    closeout_automation_eligible=closeout_automation_eligible,
                    fallback=_coerce_str(plan.get("recommended_next_command")),
                ),
                "implementation_handoff_json_path": handoff_json_path,
            }
        )

    summaries.sort(key=lambda issue: issue["issue_number"])

    payload: dict[str, Any] = {
        "command": "run-ready-issue-batch",
        "mode": "plan-only" if plan_only else "unsupported",
        "ok": listing_ok,
        "repo": f"{config.github_owner}/{config.github_repo}",
        "ready_issue_count": len(summaries),
        "issues": summaries,
        "excluded_issues": excluded_issues,
        "selected_handoffs": selected_handoffs,
        "protected_issue": PROTECTED_ISSUE_NUMBER,
        "required_labels": [READY_TRIGGER_LABEL, BATCH_AUTOMERGE_LABEL],
        "boundary_confirmations": [
            "Batch planning is human-triggered and read-only with respect to GitHub state.",
            "Issue #39 is always excluded and never targeted for mutation.",
            "No background jobs, polling, or schedulers were used.",
            "No paid/API model calls were initiated.",
            "Any future closeout mutation remains gated through qa-closeout-pr execute mode.",
        ],
    }

    markdown = _render_batch_markdown(payload)
    bundle = write_markdown_json_bundle(
        config.artifact_root / "ready_issue_batches" / "generated",
        title="ready issue batch",
        markdown=markdown,
        payload=payload,
        timestamp_override=timestamp_override,
    )
    payload["markdown_path"] = str(bundle.markdown_path)
    payload["json_path"] = str(bundle.json_path)
    return payload


def _render_batch_markdown(payload: dict[str, Any]) -> str:
    issues = payload.get("issues")
    issue_lines: list[str] = []
    if isinstance(issues, list) and issues:
        for issue in issues:
            issue_lines.extend(
                [
                    f"### Issue #{issue['issue_number']}: {issue.get('issue_title') or 'Untitled issue'}",
                    f"- Ready status: {issue.get('ready_status')}",
                    f"- Blocked: {issue.get('blocked')}",
                    f"- Blocked reasons: {', '.join(issue.get('blocked_reasons') or ['none'])}",
                    f"- Selected primary agent: {issue.get('selected_primary_agent')}",
                    f"- Selected QA agent: {issue.get('selected_qa_agent')}",
                    f"- Selected documentation agent: {issue.get('selected_documentation_agent')}",
                    f"- Model tier: {issue.get('model_tier')}",
                    f"- Routing reason: {issue.get('routing_reason')}",
                    f"- Confidence: {issue.get('confidence')}",
                    f"- Required labels: {', '.join(issue.get('required_labels') or [])}",
                    (
                        "- Closeout automation eligibility: "
                        f"{issue.get('closeout_automation_eligible')}"
                    ),
                    f"- Recommended next command: {issue.get('recommended_next_command')}",
                    "",
                ]
            )
    else:
        issue_lines = ["No ready issues found.", ""]

    return "\n".join(
        [
            "# Ready Issue Batch Plan",
            "",
            "## Summary",
            f"- Repo: {payload.get('repo')}",
            f"- Ready issue count: {payload.get('ready_issue_count')}",
            f"- Protected issue: #{payload.get('protected_issue')}",
            "",
            "## Planned Issues",
            *issue_lines,
            "## Selected Implementation Handoffs",
            "```json",
            json.dumps(payload.get("selected_handoffs"), indent=2, sort_keys=True),
            "```",
            "",
            "## Automation Boundary",
            "- Read-only planning only; no GitHub mutation performed.",
            "- Issue #39 excluded from all batch planning operations.",
            "- Closeout mutation remains gated through qa-closeout-pr execute mode only.",
        ]
    )


def _collect_blocked_reasons(
    inspection: dict[str, Any],
    plan: dict[str, Any],
) -> list[str]:
    reasons: list[str] = []
    if not bool(inspection.get("ok")):
        inspect_error = _coerce_str(inspection.get("error"))
        if inspect_error:
            reasons.append(inspect_error)
    if bool(plan.get("blocked")):
        blocked_reason = _coerce_str(plan.get("blocked_reason"))
        if blocked_reason:
            reasons.append(blocked_reason)
    return sorted(set(reasons))


def _normalize_labels(inspection: dict[str, Any], listed_issue: dict[str, Any]) -> list[str]:
    labels = listed_issue.get("labels")
    if isinstance(labels, list) and all(isinstance(item, str) for item in labels):
        return sorted(set(labels), key=lambda item: (item.lower(), item))

    issue_payload = inspection.get("issue")
    if isinstance(issue_payload, dict):
        issue_labels = issue_payload.get("labels")
        if isinstance(issue_labels, list):
            normalized = [item for item in issue_labels if isinstance(item, str)]
            return sorted(set(normalized), key=lambda item: (item.lower(), item))
    return []


def _coerce_str(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _label_present(labels: list[str], target: str) -> bool:
    return target.lower() in {label.lower() for label in labels if isinstance(label, str)}


def _recommended_next_command(
    *,
    issue_number: int,
    closeout_automation_eligible: bool,
    fallback: str | None,
) -> str:
    if closeout_automation_eligible:
        return (
            "python -m aresforge run-ready-issue-pipeline "
            f"--issue-number {issue_number} --pr-number <number> --closeout-when-eligible"
        )
    if fallback:
        return fallback
    return f"python -m aresforge plan-ready-issue --issue-number {issue_number}"
