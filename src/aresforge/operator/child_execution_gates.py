from __future__ import annotations

import json
import subprocess
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.evidence_completeness_checker import check_issue_evidence_readiness
from aresforge.operator.ready_issue_intake import fetch_issue_details

COMMAND_NAME = "inspect-child-execution-gates"
BRANCH_PREFIX = "m19/"


def inspect_child_execution_gates(
    config: AppConfig,
    *,
    issue_number: int,
    parent_issue: int | None = None,
) -> dict[str, Any]:
    issue_payload = fetch_issue_details(config, issue_number)
    if not issue_payload.get("ok"):
        return {
            "command": COMMAND_NAME,
            "ok": False,
            "read_only": True,
            "issue_number": issue_number,
            "error": "issue_lookup_failed",
            "details": issue_payload,
            "boundary_confirmations": _boundaries(),
        }

    issue = issue_payload.get("issue")
    if not isinstance(issue, dict):
        return {
            "command": COMMAND_NAME,
            "ok": False,
            "read_only": True,
            "issue_number": issue_number,
            "error": "issue_lookup_failed",
            "boundary_confirmations": _boundaries(),
        }

    state = str(issue.get("state", "")).upper()
    lineage_ok = _lineage_ok(issue=issue, parent_issue=parent_issue)
    branch_name = _git_branch(config)
    dirty = _git_dirty(config)
    open_pr = _find_open_pr_for_issue(config, issue_number=issue_number)
    evidence = check_issue_evidence_readiness(config, issue_number=issue_number)
    evidence_classification = evidence.get("classification")
    merged_prs = issue.get("merged_pr_evidence") if isinstance(issue.get("merged_pr_evidence"), list) else []
    merged_pr_count = len(merged_prs)

    safe_to_start = state == "OPEN" and lineage_ok and not dirty and open_pr is None
    safe_to_pr = state == "OPEN" and lineage_ok and not dirty and _branch_name_ok(branch_name, issue_number)
    safe_to_merge = state == "OPEN" and open_pr is not None and not dirty
    safe_to_close = state == "OPEN" and merged_pr_count > 0 and evidence_classification in {"ready", "already_closed"}
    already_closed = state == "CLOSED"

    blockers = _collect_blockers(
        issue_number=issue_number,
        state=state,
        lineage_ok=lineage_ok,
        dirty=dirty,
        branch_name=branch_name,
        open_pr=open_pr,
        evidence_classification=evidence_classification,
        merged_pr_count=merged_pr_count,
    )

    return {
        "command": COMMAND_NAME,
        "ok": True,
        "read_only": True,
        "issue": {
            "number": issue.get("number"),
            "title": issue.get("title"),
            "state": issue.get("state"),
            "url": issue.get("url"),
        },
        "parent_issue": parent_issue,
        "gate_status": {
            "safe_to_start": safe_to_start,
            "safe_to_pr": safe_to_pr,
            "safe_to_merge": safe_to_merge,
            "safe_to_close": safe_to_close,
            "already_closed": already_closed,
            "blocked": len(blockers) > 0 and not already_closed,
        },
        "checks": {
            "lineage_ok": lineage_ok,
            "current_branch": branch_name,
            "branch_name_ok": _branch_name_ok(branch_name, issue_number),
            "dirty_worktree": dirty,
            "open_pr": open_pr,
            "merged_pr_count": merged_pr_count,
            "evidence_classification": evidence_classification,
        },
        "blockers": blockers,
        "next_recommended_action": _next_action(blockers=blockers, already_closed=already_closed, issue_number=issue_number),
        "boundary_confirmations": _boundaries(),
    }


def _lineage_ok(*, issue: dict[str, Any], parent_issue: int | None) -> bool:
    if parent_issue is None:
        return True
    refs = (issue.get("reference_classification") or {}).get("implementation_issue_numbers")
    if isinstance(refs, list) and parent_issue in refs:
        return True
    body = issue.get("body")
    if isinstance(body, str) and f"Parent issue: #{parent_issue}" in body:
        return True
    return False


def _git_branch(config: AppConfig) -> str | None:
    result = _run(["git", "branch", "--show-current"], config)
    if not result["ok"]:
        return None
    return result["stdout"].strip() or None


def _git_dirty(config: AppConfig) -> bool:
    result = _run(["git", "status", "--short"], config)
    if not result["ok"]:
        return True
    return bool(result["stdout"].strip())


def _find_open_pr_for_issue(config: AppConfig, *, issue_number: int) -> dict[str, Any] | None:
    query = f"{issue_number} in:title state:open"
    result = _run(
        [
            "gh",
            "pr",
            "list",
            "--repo",
            f"{config.github_owner}/{config.github_repo}",
            "--search",
            query,
            "--json",
            "number,state,url,title",
            "--limit",
            "1",
        ],
        config,
    )
    if not result["ok"]:
        return None
    try:
        payload = json.loads(result["stdout"])
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, list) or not payload:
        return None
    first = payload[0]
    if not isinstance(first, dict):
        return None
    return {
        "number": first.get("number"),
        "state": first.get("state"),
        "url": first.get("url"),
        "title": first.get("title"),
    }


def _branch_name_ok(branch_name: str | None, issue_number: int) -> bool:
    if not isinstance(branch_name, str):
        return False
    return branch_name.startswith(BRANCH_PREFIX) and str(issue_number) in branch_name


def _collect_blockers(
    *,
    issue_number: int,
    state: str,
    lineage_ok: bool,
    dirty: bool,
    branch_name: str | None,
    open_pr: dict[str, Any] | None,
    evidence_classification: Any,
    merged_pr_count: int,
) -> list[dict[str, Any]]:
    if state == "CLOSED":
        return []
    blockers: list[dict[str, Any]] = []
    if not lineage_ok:
        blockers.append({"gate": "lineage", "reason": "missing_parent_lineage"})
    if dirty:
        blockers.append({"gate": "start", "reason": "dirty_worktree"})
    if branch_name is not None and not _branch_name_ok(branch_name, issue_number):
        blockers.append({"gate": "pr", "reason": "branch_name_not_m19_issue_specific"})
    if open_pr is None:
        blockers.append({"gate": "merge", "reason": "missing_open_pr"})
    if merged_pr_count <= 0:
        blockers.append({"gate": "close", "reason": "missing_merged_pr_evidence"})
    if evidence_classification not in {"ready", "already_closed"}:
        blockers.append({"gate": "close", "reason": f"evidence_not_ready:{evidence_classification}"})
    return blockers


def _next_action(*, blockers: list[dict[str, Any]], already_closed: bool, issue_number: int) -> str:
    if already_closed:
        return f"Issue #{issue_number} is already closed; do not reopen without explicit operator intent."
    if not blockers:
        return f"Issue #{issue_number} appears gate-ready; proceed with the next targeted execution step."
    first = blockers[0]
    return f"Resolve blocker '{first.get('reason')}' before advancing issue #{issue_number}."


def _run(args: list[str], config: AppConfig) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            args,
            cwd=config.repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return {"ok": False, "stdout": "", "stderr": "command_not_available"}
    return {"ok": completed.returncode == 0, "stdout": completed.stdout, "stderr": completed.stderr}


def _boundaries() -> list[str]:
    return [
        "read_only: true",
        "No issues were closed.",
        "No pull requests were created or merged.",
        "No comments were added.",
        "No GitHub state was edited.",
    ]
