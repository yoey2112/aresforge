from __future__ import annotations

from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.qa_closeout_pr import qa_closeout_pr
from aresforge.operator.qa_pr_validation import qa_review_pr

_REQUIRED_OPERATOR_VALIDATION_COMMANDS = (
    "python -m pytest",
    "python -m aresforge qa-review-pr --pr-number <number>",
    "python -m aresforge qa-closeout-pr --pr-number <number> --dry-run",
    "python -m aresforge inspect-repo-governance",
    "git diff --check",
)


def validate_pr_end_to_end(config: AppConfig, pr_number: int) -> dict[str, Any]:
    qa_review = qa_review_pr(config, pr_number)
    closeout_dry_run = qa_closeout_pr(config, pr_number, execute=False)
    qa_decision = str(qa_review.get("qa_decision") or "").lower()
    end_to_end_decision = "pass" if qa_decision == "pass" else "fail"
    ok = end_to_end_decision == "pass"

    failed_gates = qa_review.get("failed_gates")
    if not isinstance(failed_gates, list):
        failed_gates = []

    required_fixes = qa_review.get("required_fixes")
    if not isinstance(required_fixes, list):
        required_fixes = []

    changed_files = qa_review.get("changed_files")
    if not isinstance(changed_files, list):
        changed_files = []

    payload = {
        "command": "validate-pr-end-to-end",
        "ok": ok,
        "inspection_mode": "read_only_end_to_end_pr_validation",
        "repo": qa_review.get("repo"),
        "pr_number": pr_number,
        "qa_review": qa_review,
        "closeout_dry_run": closeout_dry_run,
        "changed_files": changed_files,
        "required_operator_validation_commands": list(
            _REQUIRED_OPERATOR_VALIDATION_COMMANDS
        ),
        "end_to_end_decision": end_to_end_decision,
        "merge_eligible": bool(qa_review.get("merge_eligible") is True and ok),
        "closeout_eligible": bool(qa_review.get("closeout_eligible") is True and ok),
        "required_fixes": required_fixes,
        "recommended_next_action": _recommended_next_action(
            pr_number=pr_number,
            ok=ok,
            failed_gates=failed_gates,
            closeout_dry_run=closeout_dry_run,
        ),
        "boundary_confirmations": _boundary_confirmations(),
    }
    return payload


def _recommended_next_action(
    *,
    pr_number: int,
    ok: bool,
    failed_gates: list[str],
    closeout_dry_run: dict[str, Any],
) -> str:
    closeout_failed_gates = closeout_dry_run.get("failed_gates")
    if not isinstance(closeout_failed_gates, list):
        closeout_failed_gates = []
    if "required_labels_present" in closeout_failed_gates:
        commands = closeout_dry_run.get("human_required_label_commands")
        if isinstance(commands, list) and commands:
            return (
                "Closeout readiness is blocked by missing linked issue labels. "
                f"Run: {commands[0]} then rerun "
                f"python -m aresforge qa-closeout-pr --pr-number {pr_number} --dry-run."
            )

    if ok:
        return (
            f"QA passed. Run required validation commands, then run "
            f"python -m aresforge qa-closeout-pr --pr-number {pr_number} --dry-run."
        )
    if failed_gates:
        return (
            f"QA failed gates: {', '.join(failed_gates)}. Address required fixes, then rerun "
            f"python -m aresforge validate-pr-end-to-end --pr-number {pr_number}."
        )
    return (
        "QA review did not pass. Resolve blockers, then rerun "
        f"python -m aresforge validate-pr-end-to-end --pr-number {pr_number}."
    )


def _boundary_confirmations() -> list[str]:
    return [
        "validate-pr-end-to-end is read-only.",
        "No autonomous GitHub mutation introduced.",
        "qa-review-pr remains read-only.",
        "qa-closeout-pr remains human-triggered and gated.",
        "Issue #39 remains retired historical validation evidence only.",
    ]
