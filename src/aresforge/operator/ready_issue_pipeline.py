from __future__ import annotations

from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.local_review import LocalReviewOptions, run_local_review
from aresforge.operator.qa_closeout_pr import qa_closeout_pr
from aresforge.operator.qa_pr_validation import qa_review_pr
from aresforge.operator.ready_issue_intake import PROTECTED_ISSUE_NUMBER, inspect_ready_issue
from aresforge.operator.ready_issue_planning import plan_ready_issue
from aresforge.operator.service import render_codex_handoff, render_evidence_package


MODE_PLAN_ONLY = "plan-only"
MODE_REVIEW_PR = "review-pr"
MODE_CLOSEOUT_WHEN_ELIGIBLE = "closeout-when-eligible"


def run_ready_issue_pipeline(
    config: AppConfig,
    *,
    issue_number: int,
    mode: str,
    pr_number: int | None = None,
    execute_closeout: bool = False,
    write_review_package: bool = False,
    write_evidence_package: bool = False,
    write_implementation_handoff: bool = False,
) -> dict[str, Any]:
    issue_title: str | None = None
    selected_agent: str | None = None
    selected_model_tier: str | None = None
    model_routing_decision: dict[str, Any] | None = None
    implementation_handoff_path: str | None = None
    review_package_path: str | None = None
    evidence_package_path: str | None = None
    qa_decision: str | None = None
    closeout_attempted = False
    closeout_completed = False
    failed_gates: list[str] = []

    if issue_number == PROTECTED_ISSUE_NUMBER:
        failed_gates.append("protected_issue_blocked")

    issue_inspection = inspect_ready_issue(config, issue_number)
    if issue_inspection.get("ok") is True:
        issue_data = issue_inspection.get("issue")
        if isinstance(issue_data, dict):
            issue_title = _safe_str(issue_data.get("title"))
            labels = issue_data.get("labels")
            normalized_labels = labels if isinstance(labels, list) else []
    else:
        normalized_labels = []
        error = _safe_str(issue_inspection.get("error"))
        if error == "issue_not_ready":
            failed_gates.append("missing_ready_label")
        elif error == "protected_issue":
            failed_gates.append("protected_issue_blocked")
        else:
            failed_gates.append("issue_not_inspectable")

    plan_payload = plan_ready_issue(config, issue_number)
    issue_title = issue_title or _safe_str(plan_payload.get("issue_title"))
    selected_agent = _safe_str(plan_payload.get("selected_primary_agent"))
    selected_model_tier = _safe_str(plan_payload.get("selected_model_tier"))
    model_routing_decision = {
        "selected_model_tier": selected_model_tier,
        "model_routing_reason": _safe_str(plan_payload.get("model_routing_reason")),
        "lower_tiers_sufficient": bool(plan_payload.get("lower_tiers_sufficient")),
        "codex_justified": bool(plan_payload.get("codex_justified")),
        "paid_use_blocked": bool(plan_payload.get("paid_use_blocked")),
    }

    if not bool(plan_payload.get("automation_eligible")):
        blocked_reason = _safe_str(plan_payload.get("blocked_reason"))
        if blocked_reason == "protected_issue":
            failed_gates.append("protected_issue_blocked")
        elif blocked_reason and blocked_reason.startswith("missing_ready_label"):
            failed_gates.append("missing_ready_label")

    automation_eligible = not failed_gates

    if mode in (MODE_REVIEW_PR, MODE_CLOSEOUT_WHEN_ELIGIBLE) and pr_number is None:
        failed_gates.append("missing_pr_number")

    if mode == MODE_CLOSEOUT_WHEN_ELIGIBLE and not _label_present(
        normalized_labels,
        "aresforge-automerge",
    ):
        failed_gates.append("missing_automerge_label")

    if mode == MODE_PLAN_ONLY and write_implementation_handoff and automation_eligible:
        handoff_bundle = render_codex_handoff(
            config=config,
            title=f"Issue {issue_number} ready implementation handoff",
            summary=(
                f"Automation-ready handoff for Issue #{issue_number}: "
                f"{issue_title or 'Untitled issue'}"
            ),
            work_item_id=None,
            route_plan=None,
            requested_output=(
                f"Implement Issue #{issue_number} using the selected routing and QA policy."
            ),
            latest_review_package=None,
        )
        implementation_handoff_path = str(handoff_bundle.json_path)

    review_payload: dict[str, Any] | None = None
    closeout_payload: dict[str, Any] | None = None

    if mode in (MODE_REVIEW_PR, MODE_CLOSEOUT_WHEN_ELIGIBLE) and pr_number is not None:
        review_payload = qa_review_pr(config, pr_number)
        qa_decision = _safe_str(review_payload.get("qa_decision"))
        failed_gates.extend(_safe_gate_list(review_payload.get("failed_gates")))

        if write_review_package:
            local_review_payload = run_local_review(
                config,
                options=LocalReviewOptions(
                    project_id="project-aresforge",
                    model_id="model-ollama-default",
                    write_review_package=True,
                ),
            )
            review_package_path = _safe_str(local_review_payload.get("output_package_path"))

    if (
        mode == MODE_CLOSEOUT_WHEN_ELIGIBLE
        and pr_number is not None
        and not failed_gates
        and review_payload is not None
        and review_payload.get("qa_decision") == "pass"
    ):
        closeout_attempted = True
        closeout_payload = qa_closeout_pr(config, pr_number, execute=execute_closeout)
        qa_decision = _safe_str(closeout_payload.get("qa_decision")) or qa_decision
        failed_gates.extend(_safe_gate_list(closeout_payload.get("failed_gates")))
        closeout_completed = bool(
            closeout_payload.get("merge_performed") and closeout_payload.get("issue_closed")
        )

    if write_evidence_package and mode in (MODE_REVIEW_PR, MODE_CLOSEOUT_WHEN_ELIGIBLE):
        validations_run = [
            "python -m aresforge inspect-ready-issue",
            "python -m aresforge plan-ready-issue",
        ]
        if pr_number is not None:
            validations_run.append("python -m aresforge qa-review-pr")
        if closeout_attempted:
            validations_run.append("python -m aresforge qa-closeout-pr")

        evidence_bundle = render_evidence_package(
            config=config,
            title=(
                f"Issue {issue_number} ready issue pipeline {mode} "
                f"{'execute' if execute_closeout else 'dry-run'}"
            ),
            work_item_id=None,
            files_changed=[],
            validations_run=validations_run,
            skipped_checks=[],
            protected_issue_checks=[
                "Issue #39 remains protected and excluded from pipeline mutation targets."
            ],
            automation_boundary_confirmation=(
                "Pipeline is human-triggered, does not poll in background, and allows GitHub "
                "mutation only through qa-closeout-pr execute mode when all gates pass."
            ),
            artifact_discovery=None,
            latest_review_package=None,
        )
        evidence_package_path = str(evidence_bundle.json_path)

    failed_gates = sorted(set(failed_gates))
    automation_eligible = automation_eligible and not failed_gates

    return {
        "command": "run-ready-issue-pipeline",
        "mode": mode,
        "issue_number": issue_number,
        "issue_title": issue_title,
        "automation_eligible": automation_eligible,
        "selected_agent": selected_agent,
        "selected_model_tier": selected_model_tier,
        "model_routing_decision": model_routing_decision,
        "implementation_handoff_path": implementation_handoff_path,
        "review_package_path": review_package_path,
        "evidence_package_path": evidence_package_path,
        "qa_decision": qa_decision,
        "closeout_attempted": closeout_attempted,
        "closeout_completed": closeout_completed,
        "failed_gates": failed_gates,
        "next_recommended_action": _next_recommended_action(
            issue_number=issue_number,
            pr_number=pr_number,
            mode=mode,
            failed_gates=failed_gates,
            execute_closeout=execute_closeout,
        ),
        "boundary_confirmations": _boundary_confirmations(
            mode=mode,
            execute_closeout=execute_closeout,
        ),
    }


def _safe_str(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _label_present(labels: list[str], target: str) -> bool:
    return target.lower() in {label.lower() for label in labels if isinstance(label, str)}


def _safe_gate_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [gate for gate in value if isinstance(gate, str)]


def _next_recommended_action(
    *,
    issue_number: int,
    pr_number: int | None,
    mode: str,
    failed_gates: list[str],
    execute_closeout: bool,
) -> str:
    if "protected_issue_blocked" in failed_gates:
        return "Issue #39 is protected. Select a different issue number."
    if "missing_ready_label" in failed_gates:
        return "Add the aresforge-ready label, then rerun plan-only mode."
    if "missing_pr_number" in failed_gates:
        return (
            "Provide --pr-number for review-pr or closeout-when-eligible mode."
        )
    if "missing_automerge_label" in failed_gates:
        return "Add the aresforge-automerge label before attempting closeout mode."
    if mode == MODE_PLAN_ONLY:
        return (
            f"python -m aresforge run-ready-issue-pipeline --issue-number {issue_number} "
            "--pr-number <number> --review-pr"
        )
    if mode == MODE_REVIEW_PR:
        return (
            f"python -m aresforge run-ready-issue-pipeline --issue-number {issue_number} "
            f"--pr-number {pr_number or '<number>'} --closeout-when-eligible"
        )
    if failed_gates:
        return "Resolve failed QA and label gates, then rerun closeout-when-eligible mode."
    if execute_closeout:
        return "Closeout executed through qa-closeout-pr; verify post-merge and issue state."
    return (
        f"Ready for explicit execute mode: python -m aresforge run-ready-issue-pipeline "
        f"--issue-number {issue_number} --pr-number {pr_number or '<number>'} "
        "--closeout-when-eligible --execute-closeout"
    )


def _boundary_confirmations(*, mode: str, execute_closeout: bool) -> list[str]:
    return [
        "Human-triggered orchestration only.",
        "No background jobs, schedulers, or autonomous polling were performed.",
        "Issue #39 is always excluded from pipeline automation.",
        "Plan-only and review-pr modes do not perform GitHub mutation.",
        (
            "Closeout behavior delegates only through qa-closeout-pr with explicit "
            "closeout mode selection."
        ),
        (
            "No paid/API model routing is permitted without documented routing approval "
            "and explicit user-approved configuration."
        ),
        (
            "GitHub mutation is disabled unless closeout-when-eligible is selected with "
            "--execute-closeout and qa-closeout-pr gates pass."
            if mode == MODE_CLOSEOUT_WHEN_ELIGIBLE and execute_closeout
            else "No GitHub mutation was performed by this pipeline invocation."
        ),
    ]