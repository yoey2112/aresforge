from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REQUIRED_SAFETY_SNIPPETS = (
    "human-triggered",
    "read-only",
    "no autonomous",
)


def generate_sprint_issue_script(*, definition_path: str, output_path: str | None = None) -> dict[str, Any]:
    source = Path(definition_path)
    if not source.exists():
        return {
            "command": "generate-sprint-issue-script",
            "ok": False,
            "error": "definition_file_not_found",
            "definition": str(source),
        }

    try:
        payload = json.loads(source.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        return {
            "command": "generate-sprint-issue-script",
            "ok": False,
            "error": "definition_invalid_json",
            "definition": str(source),
            "details": {"message": str(exc)},
        }

    errors = validate_sprint_definition(payload)
    if errors:
        return {
            "command": "generate-sprint-issue-script",
            "ok": False,
            "error": "definition_validation_failed",
            "definition": str(source),
            "validation_errors": errors,
        }

    script_text = _render_script(payload)
    target = Path(output_path) if output_path else source.with_suffix(".ps1")
    target.write_text(script_text, encoding="utf-8")

    return {
        "command": "generate-sprint-issue-script",
        "ok": True,
        "inspection_mode": "local_output_only",
        "definition": str(source),
        "script_path": str(target),
        "child_issue_count": len(payload["children"]),
        "mutation_posture": "output_only_human_execution_required",
        "boundary_confirmations": [
            "This command generates a local script artifact only.",
            "AresForge did not call gh issue create or mutate GitHub state.",
            "Human execution remains required for any GitHub mutation.",
        ],
    }


def validate_sprint_definition(payload: Any) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    if not isinstance(payload, dict):
        return [{"field": "root", "message": "Definition must be a JSON object."}]

    required_root = ["sprint_id", "repo", "parent", "children"]
    for field in required_root:
        if field not in payload:
            errors.append({"field": field, "message": "Missing required root field."})

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


def _validate_issue_block(prefix: str, issue: dict[str, Any], *, require_part_of: bool) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    for field in ("title", "body"):
        value = issue.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append({"field": f"{prefix}.{field}", "message": "Field is required and must be non-empty."})

    body = issue.get("body") if isinstance(issue.get("body"), str) else ""
    body_lower = body.lower()

    if "## safety posture" not in body_lower:
        errors.append({"field": f"{prefix}.body", "message": "Missing required '## Safety Posture' section."})
    if "## acceptance criteria" not in body_lower:
        errors.append({"field": f"{prefix}.body", "message": "Missing required '## Acceptance Criteria' section."})
    if "## validation" not in body_lower:
        errors.append({"field": f"{prefix}.body", "message": "Missing required '## Validation' section."})
    if require_part_of and "part of #" not in body_lower:
        errors.append({"field": f"{prefix}.body", "message": "Missing required child linkage line (for example 'Part of #<parent>')."})

    if "```" in body:
        errors.append({"field": f"{prefix}.body", "message": "Nested markdown fences are not allowed inside generated PowerShell here-strings."})

    if "#39" in body and "historical" not in body_lower and "protected" not in body_lower:
        errors.append({"field": f"{prefix}.body", "message": "Issue #39 reference must be explicitly classified as protected historical evidence only."})

    if "linked issue" in body_lower and "implementation" not in body_lower and "part of" not in body_lower:
        errors.append({"field": f"{prefix}.body", "message": "Ambiguous linked-issue wording detected; use explicit implementation linkage language."})

    for snippet in REQUIRED_SAFETY_SNIPPETS:
        if snippet not in body_lower:
            errors.append({"field": f"{prefix}.body", "message": f"Missing safety boundary phrase: '{snippet}'."})

    return errors


def _render_script(payload: dict[str, Any]) -> str:
    sprint_id = payload["sprint_id"]
    repo = payload["repo"]
    parent_title = payload["parent"]["title"]
    parent_body = _ps_here(payload["parent"]["body"])

    lines: list[str] = [
        "Set-StrictMode -Version Latest",
        '$ErrorActionPreference = "Stop"',
        f'$Repo = "{repo}"',
        f'$SprintId = "{sprint_id}"',
        "$CreatedChildren = @()",
        "",
        "$ParentTitle = @'",
        parent_title,
        "'@",
        "$ParentBody = @'",
        parent_body,
        "'@",
        '$ParentUrl = gh issue create --repo $Repo --title $ParentTitle --body $ParentBody',
        'if ($ParentUrl -notmatch "/issues/(\\d+)$") { throw "Unable to parse parent issue number from URL." }',
        "$ParentIssueNumber = [int]$Matches[1]",
        "",
    ]

    for child in payload["children"]:
        key = _safe_key(child["title"])
        lines.extend(
            [
                f"# Child: {child['title']}",
                "$ChildTitle = @'",
                child["title"],
                "'@",
                "$ChildBody = @'",
                _ps_here(child["body"]),
                "'@",
                "$ChildBody = $ChildBody -replace \"{{PARENT_ISSUE_NUMBER}}\", $ParentIssueNumber",
                '$ChildUrl = gh issue create --repo $Repo --title $ChildTitle --body $ChildBody',
                'if ($ChildUrl -notmatch "/issues/(\\d+)$") { throw "Unable to parse child issue number from URL." }',
                "$CreatedChildren += [pscustomobject]@{",
                f"  Key = '{key}'",
                "  Number = [int]$Matches[1]",
                "  Url = $ChildUrl",
                "  Title = $ChildTitle",
                "}",
                "",
            ]
        )

    lines.extend(
        [
            "Write-Host \"Generated sprint issue set successfully.\"",
            "Write-Host \"Human review and execution remain required for all GitHub mutations.\"",
        ]
    )
    return "\n".join(lines) + "\n"


def _safe_key(title: str) -> str:
    key = "".join(ch.lower() if ch.isalnum() else "-" for ch in title).strip("-")
    while "--" in key:
        key = key.replace("--", "-")
    return key[:64] or "issue"


def _ps_here(text: str) -> str:
    # Escape here-string closing marker to keep generated script parse-safe.
    return text.replace("'@", "' + '@")
