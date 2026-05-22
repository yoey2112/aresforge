from __future__ import annotations

from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.evidence_completeness_checker import check_issue_evidence_readiness
from aresforge.operator.ready_issue_intake import PROTECTED_ISSUE_NUMBER, fetch_issue_details

COMMAND_NAME = "generate-child-closeout-script"


def generate_child_closeout_script(config: AppConfig, *, issue_number: int) -> dict[str, Any]:
    issue_payload = fetch_issue_details(config, issue_number)
    if not issue_payload.get("ok"):
        return {
            "command": COMMAND_NAME,
            "ok": False,
            "read_only": True,
            "target_issue": issue_number,
            "error": issue_payload.get("error", "issue_lookup_failed"),
            "details": issue_payload.get("details"),
            "boundary_confirmations": _boundaries(),
        }

    issue = issue_payload.get("issue")
    if not isinstance(issue, dict):
        return {
            "command": COMMAND_NAME,
            "ok": False,
            "read_only": True,
            "target_issue": issue_number,
            "error": "issue_lookup_failed",
            "boundary_confirmations": _boundaries(),
        }

    target_issue = issue.get("number") if isinstance(issue.get("number"), int) else issue_number
    parent_issue = _resolve_parent_issue(issue=issue, target_issue=target_issue)
    readiness = check_issue_evidence_readiness(config, issue_number=target_issue)

    return {
        "command": COMMAND_NAME,
        "ok": True,
        "read_only": True,
        "inspection_mode": "github_read_only_script_generation",
        "repo": f"{config.github_owner}/{config.github_repo}",
        "target_issue": target_issue,
        "parent_issue": parent_issue,
        "issue_state": issue.get("state"),
        "issue_title": issue.get("title"),
        "issue_url": issue.get("url"),
        "evidence_readiness": {
            "ok": bool(readiness.get("ok")),
            "classification": readiness.get("classification"),
            "reasons": readiness.get("reasons") if isinstance(readiness.get("reasons"), list) else [],
        },
        "script": _render_script(
            repo=f"{config.github_owner}/{config.github_repo}",
            target_issue=target_issue,
            parent_issue=parent_issue,
        ),
        "script_summary": {
            "targets_single_issue": True,
            "includes_pre_close_validation": True,
            "includes_evidence_comment_generation": True,
            "includes_targeted_issue_close": True,
            "includes_post_close_validation": True,
            "includes_operator_review_instructions": True,
        },
        "safety_gates": {
            "read_only": True,
            "mutation_performed": False,
            "script_execution_required": True,
            "close_issues": False,
            "bulk_closeout_allowed": False,
            "target_issue_only": True,
            "operator_review_required": True,
        },
        "required_operator_actions": _required_operator_actions(parent_issue=parent_issue),
        "boundary_confirmations": _boundaries(),
        "warnings": _warnings(target_issue=target_issue, parent_issue=parent_issue),
    }


def _resolve_parent_issue(*, issue: dict[str, Any], target_issue: int) -> int | None:
    refs = issue.get("reference_classification")
    if not isinstance(refs, dict):
        return None

    parent_child = refs.get("parent_child_references")
    if isinstance(parent_child, dict):
        parent_numbers = parent_child.get("parent_issue_numbers")
        if isinstance(parent_numbers, list):
            normalized = [
                number
                for number in parent_numbers
                if isinstance(number, int) and number not in (target_issue, PROTECTED_ISSUE_NUMBER)
            ]
            if normalized:
                return min(normalized)

    implementation_numbers = refs.get("implementation_issue_numbers")
    if isinstance(implementation_numbers, list):
        normalized = [
            number
            for number in implementation_numbers
            if isinstance(number, int) and number not in (target_issue, PROTECTED_ISSUE_NUMBER)
        ]
        if normalized:
            return min(normalized)

    return None


def _render_script(*, repo: str, target_issue: int, parent_issue: int | None) -> str:
    parent_literal = str(parent_issue) if isinstance(parent_issue, int) else "$null"
    parent_validation_cmd = (
        "python -m aresforge inspect-milestone-dashboard --parent-issue $ParentIssue"
        if isinstance(parent_issue, int)
        else "Write-Host 'Parent issue is not detectable from issue lineage; set $ParentIssue manually before running parent-scoped checks.'"
    )
    parent_queue_cmd = (
        "python -m aresforge plan-milestone-execution-queue --parent-issue $ParentIssue"
        if isinstance(parent_issue, int)
        else "Write-Host 'Skipping parent queue planning command until $ParentIssue is set.'"
    )

    lines: list[str] = [
        "Set-StrictMode -Version Latest",
        '$ErrorActionPreference = "Stop"',
        f'$Repo = "{repo}"',
        f"$TargetIssue = {target_issue}",
        f"$ParentIssue = {parent_literal}",
        "",
        "Write-Host 'Operator review required: inspect every command before executing.'",
        "Write-Host 'This script is generated guidance only; generation performed no GitHub mutation.'",
        "Write-Host 'Safety boundary: target exactly one issue and do not mutate parent or sibling issues.'",
        "",
        "# Pre-close validation commands",
        "git fetch origin",
        "git checkout main",
        "git pull --ff-only origin main",
        "git diff --check",
        "python -m pytest",
        "python -m aresforge inspect-repo-governance",
        "python -m aresforge check-issue-evidence-readiness --issue $TargetIssue",
        parent_validation_cmd,
        "",
        "# Generate issue-specific evidence body file for manual review before posting",
        "$EvidencePath = \"artifacts/issue-$TargetIssue-closeout-evidence.md\"",
        "$EvidenceBody = @'",
        "### Issue-Specific Evidence Mapping",
        "",
        "- Target issue: #{{TARGET_ISSUE}}",
        "- Implemented by: PR #<fill-after-merge>",
        "- Merged main commit: <fill-main-head>",
        "",
        "Validation results:",
        "- git diff --check: pass",
        "- python -m pytest: pass",
        "- python -m aresforge inspect-repo-governance: ok true",
        "- python -m aresforge check-issue-evidence-readiness --issue {{TARGET_ISSUE}}: review output",
        "",
        "Safety and boundary confirmations:",
        "- No issue was closed before this evidence comment was posted.",
        "- Generated script targets exactly one issue closeout.",
        "- No bulk close commands are used.",
        "- Parent and sibling issues are not mutated by this script.",
        "- Parent #294 must remain open unless explicitly targeted in a future run.",
        "- Final reconciliation issue #301 must remain open unless it is the explicit target in a future run.",
        "'@",
        "$EvidenceBody = $EvidenceBody -replace '{{TARGET_ISSUE}}', [string]$TargetIssue",
        "Set-Content -Path $EvidencePath -Value $EvidenceBody",
        "",
        "# Post evidence comment only after manual review",
        "gh issue comment $TargetIssue --repo $Repo --body-file $EvidencePath",
        "",
        "# Targeted closeout command: exactly one issue",
        "gh issue close $TargetIssue --repo $Repo --comment \"Issue-specific evidence mapping has been posted. Closing #$TargetIssue.\"",
        "",
        "# Post-close validation commands",
        "python -m aresforge check-issue-evidence-readiness --issue $TargetIssue",
        parent_validation_cmd,
        parent_queue_cmd,
        "python -m aresforge plan-milestone-final-reconciliation --parent-issue 294",
    ]
    return "\n".join(lines) + "\n"


def _required_operator_actions(*, parent_issue: int | None) -> list[str]:
    actions = [
        "Review and edit placeholders in the generated evidence body before posting.",
        "Execute pre-close validations and confirm healthy outputs before posting evidence.",
        "Post the evidence comment first, then run the single gh issue close command for the target issue.",
        "Run post-close validations and capture outputs for operator audit trail.",
    ]
    if parent_issue is None:
        actions.append("Manually set parent issue context before running parent-scoped validation commands.")
    return actions


def _warnings(*, target_issue: int, parent_issue: int | None) -> list[str]:
    warnings = [
        "Script generation is read-only; no mutation was performed by this command.",
        "Do not run bulk issue close commands.",
        "Do not mutate parent issue #294 or sibling issues during child closeout.",
        "Do not close issue #301 unless it is the explicit target in a dedicated final reconciliation run.",
    ]
    if target_issue == 301:
        warnings.append("Target issue is #301 final reconciliation; ensure explicit operator authorization before closure.")
    if parent_issue is None:
        warnings.append("Parent issue lineage was not detected automatically from issue metadata.")
    return warnings


def _boundaries() -> list[str]:
    return [
        "read_only: true",
        "mutation_performed: false",
        "close_issues: false",
        "bulk_closeout_allowed: false",
        "operator_review_required: true",
        "Generated output is script text only; any mutation requires explicit human execution.",
    ]
