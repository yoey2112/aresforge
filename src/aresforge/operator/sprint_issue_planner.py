from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REQUIRED_BODY_SECTIONS = (
    "## Safety Posture",
    "## Acceptance Criteria",
    "## Validation",
)

REQUIRED_SAFETY_PHRASES = (
    "human-triggered",
    "read-only",
    "no autonomous",
)

COMMAND_NAME = "plan-sprint-issues"


@dataclass(frozen=True)
class PlannedIssue:
    title: str
    body: str


@dataclass(frozen=True)
class SprintIssuePlan:
    sprint_id: str
    repo: str
    parent: PlannedIssue
    children: tuple[PlannedIssue, ...]


def plan_sprint_issues(*, definition_path: str) -> dict[str, Any]:
    source = Path(definition_path)
    if not source.exists():
        return {
            "command": COMMAND_NAME,
            "ok": False,
            "error": "definition_file_not_found",
            "definition": str(source),
        }

    try:
        payload = json.loads(source.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        return {
            "command": COMMAND_NAME,
            "ok": False,
            "error": "definition_invalid_json",
            "definition": str(source),
            "details": {"message": str(exc)},
        }

    errors = validate_sprint_issue_plan_definition(payload)
    if errors:
        return {
            "command": COMMAND_NAME,
            "ok": False,
            "error": "definition_validation_failed",
            "definition": str(source),
            "validation_errors": errors,
        }

    plan = normalize_sprint_issue_plan(payload)
    rendered = render_sprint_issue_plan(plan)

    return {
        "command": COMMAND_NAME,
        "ok": True,
        "inspection_mode": "read_only_generated_plan",
        "definition": str(source),
        "mutation_posture": "human_gated_output_only",
        "safety_warnings": [
            "Generated content includes mutation commands for human copy/paste execution only.",
            "AresForge did not call gh and did not mutate repository or GitHub state.",
            "Do not proceed with implementation until post-creation verification reports PASS.",
        ],
        "plan": {
            "sprint_id": plan.sprint_id,
            "repo": plan.repo,
            "parent_title": plan.parent.title,
            "child_titles": [child.title for child in plan.children],
            "child_count": len(plan.children),
        },
        "rendered": rendered,
    }


def validate_sprint_issue_plan_definition(payload: Any) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    if not isinstance(payload, dict):
        return [{"field": "root", "message": "Definition must be a JSON object."}]

    for field in ("sprint_id", "repo", "parent", "children"):
        if field not in payload:
            errors.append({"field": field, "message": "Missing required root field."})

    sprint_id = payload.get("sprint_id")
    if not isinstance(sprint_id, str) or not sprint_id.strip():
        errors.append({"field": "sprint_id", "message": "Field is required and must be non-empty."})

    repo = payload.get("repo")
    if not isinstance(repo, str) or not repo.strip():
        errors.append({"field": "repo", "message": "Field is required and must be non-empty."})

    parent = payload.get("parent")
    if not isinstance(parent, dict):
        errors.append({"field": "parent", "message": "Parent must be an object."})
    else:
        errors.extend(_validate_issue_block("parent", parent, require_part_of=False))

    children = payload.get("children")
    if not isinstance(children, list) or not children:
        errors.append({"field": "children", "message": "At least one child issue is required."})
    else:
        for idx, child in enumerate(children):
            if not isinstance(child, dict):
                errors.append({"field": f"children[{idx}]", "message": "Child issue must be an object."})
                continue
            errors.extend(_validate_issue_block(f"children[{idx}]", child, require_part_of=True))

    return errors


def normalize_sprint_issue_plan(payload: dict[str, Any]) -> SprintIssuePlan:
    children = tuple(
        PlannedIssue(title=child["title"].strip(), body=_normalize_body(child["body"]))
        for child in payload["children"]
        if isinstance(child, dict)
    )
    return SprintIssuePlan(
        sprint_id=payload["sprint_id"].strip(),
        repo=payload["repo"].strip(),
        parent=PlannedIssue(
            title=payload["parent"]["title"].strip(),
            body=_normalize_body(payload["parent"]["body"]),
        ),
        children=children,
    )


def render_sprint_issue_plan(plan: SprintIssuePlan) -> dict[str, Any]:
    parent_body = plan.parent.body
    child_bodies = [{"title": child.title, "body": child.body} for child in plan.children]

    verification_block = _render_verification_block(plan)

    return {
        "parent_issue_body": parent_body,
        "child_issue_bodies": child_bodies,
        "powershell_issue_creation_block": _render_powershell_creation_block(plan, verification_block),
        "parent_child_index_update": _render_parent_child_index_update(plan),
        "final_post_creation_verification_block": verification_block,
    }


def evaluate_issue_creation_verification(
    *,
    plan: SprintIssuePlan,
    actual_parent_title: str,
    actual_child_titles: list[str],
    parent_body_after_update: str,
    body_by_child_title: dict[str, str],
) -> dict[str, Any]:
    expected_titles = [child.title for child in plan.children]
    missing_titles = [title for title in expected_titles if title not in actual_child_titles]
    unexpected_titles = [title for title in actual_child_titles if title not in expected_titles]

    index_missing = [title for title in expected_titles if title not in parent_body_after_update]

    body_section_failures: list[str] = []
    safety_failures: list[str] = []
    for title in expected_titles:
        body = body_by_child_title.get(title, "")
        lowered = body.lower()
        if not all(section.lower() in lowered for section in REQUIRED_BODY_SECTIONS):
            body_section_failures.append(title)
        if not all(snippet in lowered for snippet in REQUIRED_SAFETY_PHRASES):
            safety_failures.append(title)

    pass_status = (
        actual_parent_title == plan.parent.title
        and len(actual_child_titles) == len(expected_titles)
        and not missing_titles
        and not unexpected_titles
        and not index_missing
        and not body_section_failures
        and not safety_failures
    )

    return {
        "expected_parent_issue_title": plan.parent.title,
        "actual_parent_issue_title": actual_parent_title,
        "expected_child_count": len(expected_titles),
        "actual_child_count": len(actual_child_titles),
        "missing_expected_child_titles": missing_titles,
        "unexpected_child_titles": unexpected_titles,
        "parent_child_index_complete": not index_missing,
        "parent_child_index_missing_titles": index_missing,
        "required_body_section_complete": not body_section_failures,
        "required_body_section_failures": body_section_failures,
        "safety_boundary_text_present": not safety_failures,
        "safety_boundary_text_failures": safety_failures,
        "verification_status": "pass" if pass_status else "fail",
        "failure_guidance": (
            "Do not continue implementation. Review mismatch report. "
            "Run the generated human-gated repair block or manually reconcile parent/child issue state."
            if not pass_status
            else "Verification passed."
        ),
    }


def _validate_issue_block(prefix: str, issue: dict[str, Any], *, require_part_of: bool) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    for field in ("title", "body"):
        value = issue.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append({"field": f"{prefix}.{field}", "message": "Field is required and must be non-empty."})

    body = issue.get("body") if isinstance(issue.get("body"), str) else ""
    body_lower = body.lower()

    for section in REQUIRED_BODY_SECTIONS:
        if section.lower() not in body_lower:
            errors.append({"field": f"{prefix}.body", "message": f"Missing required '{section}' section."})

    if require_part_of and "part of #" not in body_lower:
        errors.append(
            {
                "field": f"{prefix}.body",
                "message": "Missing required child linkage line (for example 'Part of #<parent>').",
            }
        )

    if "```" in body:
        errors.append(
            {
                "field": f"{prefix}.body",
                "message": "Nested markdown fences are not allowed inside generated PowerShell here-strings.",
            }
        )

    for snippet in REQUIRED_SAFETY_PHRASES:
        if snippet not in body_lower:
            errors.append({"field": f"{prefix}.body", "message": f"Missing safety boundary phrase: '{snippet}'."})

    return errors


def _normalize_body(body: str) -> str:
    lines = [line.rstrip() for line in body.replace("\r\n", "\n").split("\n")]
    return "\n".join(lines).strip()


def _ps_here(text: str) -> str:
    return text.replace("'@", "' + '@")


def _render_parent_child_index_update(plan: SprintIssuePlan) -> str:
    lines = [
        "## Child Implementation Index",
        "",
    ]
    for child in plan.children:
        lines.append(f"- [ ] {child.title} (issue #<child_number>)")
    return "\n".join(lines)


def _render_verification_block(plan: SprintIssuePlan) -> str:
    expected_titles = "\n".join([f"  '{child.title}'" for child in plan.children])
    return "\n".join(
        [
            "# Final Post-Creation Verification (Human-Gated)",
            "$ExpectedParentTitle = @'",
            plan.parent.title,
            "'@",
            "$ExpectedChildTitles = @(",
            expected_titles,
            ")",
            "$ExpectedChildCount = " + str(len(plan.children)),
            "",
            "Write-Host '[VERIFY] Compare expected plan against live GitHub issue state before implementation.'",
            "# Check expected parent issue title vs actual parent issue title",
            "# Check expected child count vs actual child count",
            "# Check missing expected child titles / unexpected child titles",
            "# Check parent child-index completeness",
            "# Check required body-section completeness",
            "# Check safety-boundary text presence",
            "# Set overall pass/fail",
            "Write-Host '[FAILURE ACTION] Do not continue implementation on fail.'",
            "Write-Host '[FAILURE ACTION] Review mismatch report.'",
            "Write-Host '[FAILURE ACTION] Run generated human-gated repair block or manually reconcile parent/child issue state.'",
        ]
    )


def _render_powershell_creation_block(plan: SprintIssuePlan, verification_block: str) -> str:
    lines = [
        "# HUMAN-GATED MUTATION SCRIPT",
        "# WARNING: Copy/paste and run manually. AresForge did not execute these commands.",
        "Set-StrictMode -Version Latest",
        '$ErrorActionPreference = "Stop"',
        f'$Repo = "{plan.repo}"',
        f'$SprintId = "{plan.sprint_id}"',
        "$CreatedChildren = @()",
        "",
        "$ParentTitle = @'",
        plan.parent.title,
        "'@",
        "$ParentBody = @'",
        _ps_here(plan.parent.body),
        "'@",
        "$ParentUrl = gh issue create --repo $Repo --title $ParentTitle --body $ParentBody",
        "if ($ParentUrl -notmatch '/issues/(\\d+)$') { throw 'Unable to parse parent issue number from URL.' }",
        "$ParentIssueNumber = [int]$Matches[1]",
        "",
    ]

    for child in plan.children:
        lines.extend(
            [
                f"# Child: {child.title}",
                "$ChildTitle = @'",
                child.title,
                "'@",
                "$ChildBody = @'",
                _ps_here(child.body),
                "'@",
                "$ChildBody = $ChildBody -replace '{{PARENT_ISSUE_NUMBER}}', $ParentIssueNumber",
                "$ChildUrl = gh issue create --repo $Repo --title $ChildTitle --body $ChildBody",
                "if ($ChildUrl -notmatch '/issues/(\\d+)$') { throw 'Unable to parse child issue number from URL.' }",
                "$CreatedChildren += [pscustomobject]@{ Title = $ChildTitle; Number = [int]$Matches[1]; Url = $ChildUrl }",
                "",
            ]
        )

    lines.extend(
        [
            "# Parent child-index update (human review required before execution)",
            "$ParentIndexUpdate = @'",
            _ps_here(_render_parent_child_index_update(plan)),
            "'@",
            "Write-Host '[NEXT] Update parent issue body child index with created child numbers.'",
            "",
            verification_block,
            "",
            "# Human-gated repair guidance (text only)",
            "Write-Host '[REPAIR] If verification fails: do not continue implementation.'",
            "Write-Host '[REPAIR] Review mismatches, repair parent/child bodies, then re-run verification manually.'",
        ]
    )

    return "\n".join(lines) + "\n"
