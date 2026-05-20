from __future__ import annotations

from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.qa_pr_validation import qa_review_pr
from aresforge.operator.ready_issue_intake import (
    PROTECTED_ISSUE_NUMBER,
    _normalize_label_names,
    _parse_json_payload,
    _repo_slug,
    _run_gh_command,
)
from aresforge.operator.service import render_evidence_package

_REQUIRED_LABELS = ("aresforge-ready", "aresforge-automerge")
_ISSUE_VIEW_FIELDS = "number,state,url,labels"
_GATE_ORDER = (
    "pr_exists",
    "pr_open",
    "pr_not_draft",
    "merge_state_clean",
    "linked_issue_present",
    "protected_issue_untouched",
    "required_labels_present",
    "qa_decision_pass",
    "merge_eligible",
    "closeout_eligible",
    "validation_evidence_present",
    "required_tests_passed",
    "forbidden_changes_absent",
    "generated_conventions_respected",
)


def qa_closeout_pr(config: AppConfig, pr_number: int, *, execute: bool = False) -> dict[str, Any]:
    mode = "execute" if execute else "dry_run"
    review_payload = qa_review_pr(config, pr_number)

    linked_issue_number = review_payload.get("linked_issue_number")
    if not isinstance(linked_issue_number, int):
        linked_issue_number = None

    issue_payload = _fetch_issue_details(config, linked_issue_number)
    linked_issue_labels = issue_payload.get("label_names", [])
    if not isinstance(linked_issue_labels, list):
        linked_issue_labels = []
    pr_labels = review_payload.get("pr_labels", [])
    if not isinstance(pr_labels, list):
        pr_labels = []

    missing_linked_issue_labels = [
        label for label in _REQUIRED_LABELS if not _label_present(linked_issue_labels, label)
    ]
    missing_pr_labels = [label for label in _REQUIRED_LABELS if not _label_present(pr_labels, label)]
    required_labels_present = not missing_linked_issue_labels

    gate_results = {
        "pr_exists": bool(review_payload.get("ok") is True),
        "pr_open": _gate_passed(review_payload, "pr_open"),
        "pr_not_draft": _gate_passed(review_payload, "pr_not_draft"),
        "merge_state_clean": _gate_passed(review_payload, "merge_state_clean"),
        "linked_issue_present": linked_issue_number is not None,
        "protected_issue_untouched": _gate_passed(review_payload, "protected_issue_untouched")
        and linked_issue_number != PROTECTED_ISSUE_NUMBER,
        "required_labels_present": required_labels_present,
        "qa_decision_pass": review_payload.get("qa_decision") == "pass",
        "merge_eligible": review_payload.get("merge_eligible") is True,
        "closeout_eligible": review_payload.get("closeout_eligible") is True,
        "validation_evidence_present": _gate_passed(review_payload, "validation_evidence_present"),
        "required_tests_passed": _gate_passed(review_payload, "required_tests_passed"),
        "forbidden_changes_absent": _gate_passed(review_payload, "forbidden_changes_absent"),
        "generated_conventions_respected": _gate_passed(
            review_payload,
            "generated_conventions_respected",
        ),
    }
    passed_gates, failed_gates = _partition_gates(gate_results)

    merge_performed = False
    issue_closed = False
    closeout_comment_created = False
    mutation_attempted = False
    final_evidence_package_path: str | None = None
    mutation_error: dict[str, Any] | None = None

    if execute and not failed_gates:
        mutation_attempted = True
        mutation_result = _execute_closeout_mutations(
            config,
            pr_number=pr_number,
            linked_issue_number=linked_issue_number,
        )
        merge_performed = mutation_result["merge_performed"]
        closeout_comment_created = mutation_result["closeout_comment_created"]
        issue_closed = mutation_result["issue_closed"]
        mutation_error = mutation_result.get("error")

        if merge_performed and closeout_comment_created and issue_closed:
            final_evidence_package_path = _write_final_closeout_evidence(
                config,
                pr_number=pr_number,
                linked_issue_number=linked_issue_number,
                review_payload=review_payload,
            )

    recommended_next_command = _recommended_next_command(
        config=config,
        pr_number=pr_number,
        linked_issue_number=linked_issue_number,
        mode=mode,
        failed_gates=failed_gates,
        missing_linked_issue_labels=missing_linked_issue_labels,
    )
    human_required_label_commands = _human_required_label_commands(
        config=config,
        pr_number=pr_number,
        linked_issue_number=linked_issue_number,
        missing_linked_issue_labels=missing_linked_issue_labels,
        missing_pr_labels=missing_pr_labels,
    )

    payload: dict[str, Any] = {
        "command": "qa-closeout-pr",
        "mode": mode,
        "pr_number": pr_number,
        "linked_issue_number": linked_issue_number,
        "required_label_target": "linked_issue",
        "linked_issue_labels": linked_issue_labels,
        "pr_labels": pr_labels,
        "required_labels_present": required_labels_present,
        "missing_required_labels": missing_linked_issue_labels,
        "missing_linked_issue_labels": missing_linked_issue_labels,
        "missing_pr_labels": missing_pr_labels,
        "human_required_label_commands": human_required_label_commands,
        "qa_decision": review_payload.get("qa_decision"),
        "merge_eligible": review_payload.get("merge_eligible") is True,
        "closeout_eligible": review_payload.get("closeout_eligible") is True,
        "failed_gates": failed_gates,
        "passed_gates": passed_gates,
        "mutation_attempted": mutation_attempted,
        "merge_performed": merge_performed,
        "issue_closed": issue_closed,
        "closeout_comment_created": closeout_comment_created,
        "final_evidence_package_path": final_evidence_package_path,
        "recommended_next_command": recommended_next_command,
        "boundary_confirmations": _boundary_confirmations(mode),
    }

    if mutation_error is not None:
        payload["mutation_error"] = mutation_error

    issue_url = issue_payload.get("url")
    if isinstance(issue_url, str):
        payload["linked_issue_url"] = issue_url

    return payload


def _gate_passed(review_payload: dict[str, Any], gate: str) -> bool:
    passed = review_payload.get("passed_gates")
    if not isinstance(passed, list):
        return False
    return gate in passed


def _partition_gates(gate_results: dict[str, bool]) -> tuple[list[str], list[str]]:
    passed: list[str] = []
    failed: list[str] = []
    for gate in _GATE_ORDER:
        if gate_results.get(gate):
            passed.append(gate)
        else:
            failed.append(gate)
    return passed, failed


def _label_present(labels: list[str], target: str) -> bool:
    lowered = {label.lower() for label in labels}
    return target.lower() in lowered


def _fetch_issue_details(config: AppConfig, issue_number: int | None) -> dict[str, Any]:
    if issue_number is None:
        return {"ok": False, "error": "linked_issue_missing", "label_names": []}

    args = [
        "issue",
        "view",
        str(issue_number),
        "--repo",
        _repo_slug(config),
        "--json",
        _ISSUE_VIEW_FIELDS,
    ]
    code, stdout, stderr = _run_gh_command(args)
    if code != 0:
        return {
            "ok": False,
            "error": "gh_cli_failed",
            "details": {"exit_code": code, "stderr": stderr.strip()},
            "label_names": [],
        }

    try:
        issue = _parse_json_payload(stdout)
    except ValueError as exc:
        return {
            "ok": False,
            "error": "gh_cli_invalid_json",
            "details": {"message": str(exc)},
            "label_names": [],
        }
    if not isinstance(issue, dict):
        return {"ok": False, "error": "issue_not_found", "label_names": []}

    return {
        "ok": True,
        "number": issue.get("number"),
        "state": issue.get("state"),
        "url": issue.get("url"),
        "label_names": _normalize_label_names(issue.get("labels")),
    }


def _execute_closeout_mutations(
    config: AppConfig,
    *,
    pr_number: int,
    linked_issue_number: int | None,
) -> dict[str, Any]:
    if linked_issue_number is None:
        return {
            "merge_performed": False,
            "closeout_comment_created": False,
            "issue_closed": False,
            "error": {"step": "preflight", "error": "linked_issue_missing"},
        }

    repo_slug = _repo_slug(config)

    merge_args = [
        "pr",
        "merge",
        str(pr_number),
        "--repo",
        repo_slug,
        "--squash",
        "--delete-branch",
    ]
    code, _stdout, stderr = _run_gh_command(merge_args)
    if code != 0:
        return {
            "merge_performed": False,
            "closeout_comment_created": False,
            "issue_closed": False,
            "error": {
                "step": "merge_pr",
                "exit_code": code,
                "stderr": stderr.strip(),
            },
        }

    comment_body = (
        f"AresForge qa-closeout-pr completed for PR #{pr_number}. "
        "All QA and label gates passed before execute-mode closeout."
    )
    comment_args = [
        "issue",
        "comment",
        str(linked_issue_number),
        "--repo",
        repo_slug,
        "--body",
        comment_body,
    ]
    code, _stdout, stderr = _run_gh_command(comment_args)
    if code != 0:
        return {
            "merge_performed": True,
            "closeout_comment_created": False,
            "issue_closed": False,
            "error": {
                "step": "comment_issue",
                "exit_code": code,
                "stderr": stderr.strip(),
            },
        }

    close_args = [
        "issue",
        "close",
        str(linked_issue_number),
        "--repo",
        repo_slug,
        "--reason",
        "completed",
    ]
    code, _stdout, stderr = _run_gh_command(close_args)
    if code != 0:
        issue_state_after_failure = _fetch_issue_state(config, linked_issue_number)
        recovered_issue_closed = issue_state_after_failure == "closed"
        return {
            "merge_performed": True,
            "closeout_comment_created": True,
            "issue_closed": recovered_issue_closed,
            "error": {
                "step": "close_issue",
                "exit_code": code,
                "stderr": stderr.strip(),
                "issue_state_after_failure": issue_state_after_failure,
                "recovered_issue_closed": recovered_issue_closed,
            },
        }

    return {
        "merge_performed": True,
        "closeout_comment_created": True,
        "issue_closed": True,
    }


def _write_final_closeout_evidence(
    config: AppConfig,
    *,
    pr_number: int,
    linked_issue_number: int | None,
    review_payload: dict[str, Any],
) -> str | None:
    files_changed = review_payload.get("changed_files")
    if not isinstance(files_changed, list):
        files_changed = []

    title = f"Issue {linked_issue_number} final closeout evidence PR {pr_number}"
    bundle = render_evidence_package(
        config=config,
        title=title,
        work_item_id=f"issue-{linked_issue_number}" if linked_issue_number is not None else None,
        files_changed=[str(item) for item in files_changed],
        validations_run=[
            f"qa-review-pr --pr-number {pr_number}",
            f"qa-closeout-pr --pr-number {pr_number} --execute",
        ],
        skipped_checks=[],
        protected_issue_checks=["Issue #39 confirmed untouched and not linked."],
        automation_boundary_confirmation=(
            "GitHub mutation was executed only for the target PR and linked issue after all QA and "
            "label gates passed with explicit execute mode."
        ),
    )
    return _to_repo_relative_path(config, bundle.json_path)


def _to_repo_relative_path(config: AppConfig, path: Path) -> str:
    try:
        return path.resolve().relative_to(config.repo_root.resolve()).as_posix()
    except ValueError:
        return str(path)


def _recommended_next_command(
    *,
    config: AppConfig,
    pr_number: int,
    linked_issue_number: int | None,
    mode: str,
    failed_gates: list[str],
    missing_linked_issue_labels: list[str],
) -> str:
    if missing_linked_issue_labels:
        linked_issue_label_command = _build_label_edit_command(
            resource_type="issue",
            number=linked_issue_number,
            repo_slug=_repo_slug(config),
            missing_labels=missing_linked_issue_labels,
        )
        if linked_issue_label_command is not None:
            return linked_issue_label_command

    if mode == "dry_run":
        if failed_gates:
            return f"qa-review-pr --pr-number {pr_number}"
        return f"qa-closeout-pr --pr-number {pr_number} --execute"

    if failed_gates:
        return f"qa-closeout-pr --pr-number {pr_number} --dry-run"
    return f"qa-review-pr --pr-number {pr_number}"


def _boundary_confirmations(mode: str) -> list[str]:
    boundaries = [
        "Human-triggered command. No background polling or scheduled behavior.",
        "Issue #39 was not modified.",
        "No unrelated PR, issue, repository settings, release, tag, milestone, or GitHub Project mutation was performed.",
    ]
    if mode == "dry_run":
        boundaries.insert(1, "Dry-run mode performed no GitHub mutation.")
    else:
        boundaries.insert(
            1,
            "Execute mode only allows mutation after all QA and required-label gates pass.",
        )
    return boundaries


def _human_required_label_commands(
    *,
    config: AppConfig,
    pr_number: int,
    linked_issue_number: int | None,
    missing_linked_issue_labels: list[str],
    missing_pr_labels: list[str],
) -> list[str]:
    commands: list[str] = []
    repo_slug = _repo_slug(config)

    linked_issue_command = _build_label_edit_command(
        resource_type="issue",
        number=linked_issue_number,
        repo_slug=repo_slug,
        missing_labels=missing_linked_issue_labels,
    )
    if linked_issue_command is not None:
        commands.append(linked_issue_command)

    pr_command = _build_label_edit_command(
        resource_type="pr",
        number=pr_number,
        repo_slug=repo_slug,
        missing_labels=missing_pr_labels,
    )
    if pr_command is not None:
        commands.append(pr_command)

    return commands


def _build_label_edit_command(
    *,
    resource_type: str,
    number: int | None,
    repo_slug: str,
    missing_labels: list[str],
) -> str | None:
    if number is None or not missing_labels:
        return None
    command = f"gh {resource_type} edit {number} --repo {repo_slug}"
    for label in missing_labels:
        command += f' --add-label "{label}"'
    return command


def _fetch_issue_state(config: AppConfig, issue_number: int) -> str | None:
    args = [
        "issue",
        "view",
        str(issue_number),
        "--repo",
        _repo_slug(config),
        "--json",
        "state",
    ]
    code, stdout, _stderr = _run_gh_command(args)
    if code != 0:
        return None
    try:
        payload = _parse_json_payload(stdout)
    except ValueError:
        return None
    if not isinstance(payload, dict):
        return None
    state = payload.get("state")
    if isinstance(state, str):
        return state.lower()
    return None
