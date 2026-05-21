from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.ready_issue_intake import PROTECTED_ISSUE_NUMBER


def report_batch_readiness(
    config: AppConfig,
    *,
    issue_numbers: list[int] | None = None,
    issues_file: str | None = None,
    changed_files: list[str] | None = None,
    validations: list[str] | None = None,
    pr_number: int | None = None,
) -> dict[str, Any]:
    normalized_issues = sorted(set(issue_numbers or []))
    if issues_file:
        normalized_issues = _load_issue_numbers(issues_file)

    touched_files = sorted(set(changed_files or _git_changed_files(config.repo_root)))
    validation_commands = validations or []

    protected_issue_present = PROTECTED_ISSUE_NUMBER in normalized_issues
    docs_changed = any(path.startswith("docs/") for path in touched_files)
    code_changed = any(path.startswith("src/") or path.startswith("tests/") for path in touched_files)

    unresolved_gates: list[str] = []
    if not normalized_issues:
        unresolved_gates.append("missing_issue_coverage")
    if code_changed and not validation_commands:
        unresolved_gates.append("missing_validation_evidence")
    if code_changed and not docs_changed:
        unresolved_gates.append("missing_docs_reconciliation")
    if protected_issue_present:
        unresolved_gates.append("protected_issue_in_scope")

    readiness = "ready_for_human_review" if not unresolved_gates else "not_ready"
    warnings = [
        "Closeout, merge, labels, and issue state changes remain human-triggered.",
        "This report is read-only and does not mutate GitHub or repository state.",
        "Protected historical references remain protected and must stay untouched.",
    ]

    return {
        "command": "report-batch-readiness",
        "ok": True,
        "inspection_mode": "local_read_only",
        "repo": f"{config.github_owner}/{config.github_repo}",
        "pr_number": pr_number,
        "branch": _current_branch(config.repo_root),
        "issue_coverage": {
            "issue_numbers": normalized_issues,
            "issue_count": len(normalized_issues),
            "protected_issue_present": protected_issue_present,
        },
        "changed_file_awareness": {
            "changed_files": touched_files,
            "changed_file_count": len(touched_files),
            "docs_changed": docs_changed,
            "code_changed": code_changed,
        },
        "test_evidence": {
            "validations": validation_commands,
            "validation_count": len(validation_commands),
        },
        "pr_readiness": {
            "readiness": readiness,
            "unresolved_gates": unresolved_gates,
        },
        "closeout_readiness": {
            "human_closeout_required": True,
            "execute_mode_not_run": True,
            "recommended_next_step": "Run qa-closeout-pr --dry-run after human validation review.",
        },
        "warnings": warnings,
    }


def _load_issue_numbers(issues_file: str) -> list[int]:
    payload = json.loads(Path(issues_file).read_text(encoding="utf-8"))
    items = payload.get("issues") if isinstance(payload, dict) else None
    if not isinstance(items, list):
        return []
    numbers: list[int] = []
    for item in items:
        if isinstance(item, dict) and isinstance(item.get("number"), int):
            numbers.append(item["number"])
    return sorted(set(numbers))


def _git_changed_files(repo_root: Path) -> list[str]:
    commands = [
        ["git", "diff", "--name-only"],
        ["git", "diff", "--name-only", "--cached"],
    ]
    files: set[str] = set()
    for args in commands:
        result = subprocess.run(
            args,
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            continue
        for line in result.stdout.splitlines():
            value = line.strip().replace("\\", "/")
            if value:
                files.add(value)
    return sorted(files, key=lambda path: (path.lower(), path))


def _current_branch(repo_root: Path) -> str | None:
    result = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    value = result.stdout.strip()
    return value or None
