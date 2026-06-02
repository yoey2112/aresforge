from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
import re
import subprocess
from typing import Any, Protocol

from aresforge.config import AppConfig
from aresforge.operator.github_issue_creation_real_run_gate import (
    DEFAULT_AUTONOMY_PROFILE,
    LIVE_AUTONOMY_PROFILE,
)
from aresforge.operator.github_issue_sync_plan import plan_github_issue_sync
from aresforge.operator.github_link_registry import inspect_github_link_registry
from aresforge.operator.local_project_queue import resolve_project_queue_path
from aresforge.operator.machine_safety_gate_engine import evaluate_machine_safety_gates
from aresforge.operator.operator_autonomy_configuration_profile import inspect_autonomy_profile

COMMAND_NAME = "reconcile-github-issue-state"
RECORD_TYPE = "github_issue_state_reconciliation_v1"
DEFAULT_PROJECT_ID = "aresforge"
DEFAULT_ITEM_ID = "m174-github-issue-state-reconciliation"

_BOUNDARY_CONFIRMATIONS: tuple[str, ...] = (
    "Dry-run is the default behavior and performs no GitHub mutation.",
    "Reconciliation compares local queue/link registry state with a supplied or explicitly enabled GitHub issue-state snapshot.",
    "Live GitHub issue-state reads require --github-enabled, non-dry-run behavior, github_issue_sync_enabled autonomy profile, and passing github_sync machine gates.",
    "The command recommends create, update, comment, close, reopen, or skip actions only; it does not execute those actions.",
    "No pull request merge, auto-merge, force push, protected branch update, release creation, workflow mutation, issue closure, source patch application, Codex execution, model execution, validation command execution, queue mutation, retry, resume, or next-item execution is performed.",
)


class GitHubIssueStateClient(Protocol):
    def list_issues(self, *, repo: str, issue_numbers: list[int]) -> list[dict[str, Any]]:
        ...


@dataclass(frozen=True)
class GhCliGitHubIssueStateClient:
    timeout_seconds: int = 30

    def list_issues(self, *, repo: str, issue_numbers: list[int]) -> list[dict[str, Any]]:
        issues: list[dict[str, Any]] = []
        for number in sorted(set(issue_numbers)):
            completed = subprocess.run(
                [
                    "gh",
                    "issue",
                    "view",
                    str(number),
                    "--repo",
                    repo,
                    "--json",
                    "number,title,state,url,labels,milestone,updatedAt",
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=max(1, self.timeout_seconds),
                shell=False,
            )
            if completed.returncode != 0:
                detail = completed.stderr.strip() or completed.stdout.strip() or f"gh issue view failed for issue {number}"
                raise RuntimeError(detail)
            try:
                parsed = json.loads(completed.stdout or "{}")
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"gh issue view returned invalid JSON for issue {number}: {exc}") from exc
            if isinstance(parsed, dict):
                issues.append(parsed)
        return issues


def reconcile_github_issue_state(
    config: AppConfig,
    *,
    project_id: str = DEFAULT_PROJECT_ID,
    item_id: str = DEFAULT_ITEM_ID,
    queue_path: str | Path | None = None,
    registry_path: str | Path | None = None,
    github_state_path: str | Path | None = None,
    dry_run: bool = True,
    github_enabled: bool = False,
    autonomy_profile: str = DEFAULT_AUTONOMY_PROFILE,
    repo: str | None = None,
    output: str | Path | None = None,
    force: bool = False,
    output_format: str = "json",
    github_client: GitHubIssueStateClient | None = None,
) -> dict[str, Any]:
    fmt = _text(output_format).lower() or "json"
    if fmt != "json":
        return _error("invalid_format", {"format": output_format, "supported_formats": ["json"]})

    normalized_project_id = _text(project_id) or DEFAULT_PROJECT_ID
    normalized_item_id = _text(item_id) or DEFAULT_ITEM_ID
    normalized_repo = _normalize_repo(config, repo)
    selected_autonomy_profile = _text(autonomy_profile) or DEFAULT_AUTONOMY_PROFILE
    effective_dry_run = bool(dry_run) or not bool(github_enabled)
    generated_at = _now_iso()
    idempotency_key = _idempotency_key(project_id=normalized_project_id, repository=normalized_repo)

    queue_path_resolved = resolve_project_queue_path(config.repo_root, queue_path)
    plan_payload = _payload(
        plan_github_issue_sync(
            config,
            project_id=normalized_project_id,
            item_id=normalized_item_id,
            queue_path=queue_path,
            output_format="json",
        )
    )
    registry_payload = _payload(
        inspect_github_link_registry(
            config,
            project_id=normalized_project_id,
            item_id=normalized_item_id,
            registry_path=registry_path,
            repository=normalized_repo,
            output_format="json",
        )
    )
    autonomy_payload = _payload(
        inspect_autonomy_profile(
            config,
            project_id=normalized_project_id,
            item_id=normalized_item_id,
            autonomy_profile=selected_autonomy_profile,
            queue_path=queue_path,
            output_format="json",
        )
    )
    gate_payload = _gate_payload(
        config,
        item_id=normalized_item_id,
        queue_path=queue_path,
        dry_run=effective_dry_run,
        github_enabled=bool(github_enabled),
    )
    gate_summary = _gate_summary(gate_payload, default_profile="read_only_agent" if effective_dry_run else "github_sync")

    registry_records = _dicts(registry_payload.get("records"))
    issue_numbers = _local_issue_numbers(plan_payload, registry_records)
    github_state_result = _github_state(
        config=config,
        repo=normalized_repo,
        github_state_path=github_state_path,
        issue_numbers=issue_numbers,
        dry_run=effective_dry_run,
        github_enabled=bool(github_enabled),
        github_client=github_client,
    )
    github_issues = github_state_result["issues_by_number"]

    reconciliation_items = [
        _reconcile_item(
            plan_item=plan_item,
            registry_records=registry_records,
            github_issues=github_issues,
            project_id=normalized_project_id,
            repository=normalized_repo,
            dry_run=effective_dry_run,
            github_enabled=bool(github_enabled),
            autonomy_profile=selected_autonomy_profile,
            github_state_available=bool(github_state_result["state_available"]),
        )
        for plan_item in _dicts(plan_payload.get("issue_sync_items"))
    ]
    operation_counts = _operation_counts(reconciliation_items)
    blocked_reasons = _blocked_reasons(
        plan_payload=plan_payload,
        registry_payload=registry_payload,
        github_state_result=github_state_result,
        gate_payload=gate_payload,
        autonomy_payload=autonomy_payload,
        dry_run=effective_dry_run,
        github_enabled=bool(github_enabled),
        autonomy_profile=selected_autonomy_profile,
        repo=normalized_repo,
    )
    warnings = _dedupe(
        [
            *_list(plan_payload.get("warnings")),
            *_list(registry_payload.get("warnings")),
            *_list(github_state_result.get("warnings")),
            *_list(autonomy_payload.get("warnings")),
            *_list(gate_payload.get("warnings")),
        ]
    )
    blocked = bool(blocked_reasons)

    payload: dict[str, Any] = {
        "record_type": RECORD_TYPE,
        "artifact_type": RECORD_TYPE,
        "generated": True,
        "generated_at": generated_at,
        "project_id": normalized_project_id,
        "item_id": normalized_item_id,
        "repository": normalized_repo,
        "issue_number": None,
        "issue_url": "",
        "pr_number": None,
        "pr_url": "",
        "sync_status": "blocked" if blocked else ("dry_run_ready" if effective_dry_run else "reconciled"),
        "status": "blocked" if blocked else ("dry_run_ready" if effective_dry_run else "reconciled"),
        "blocked": blocked,
        "blocked_reasons": blocked_reasons,
        "warnings": warnings,
        "machine_gates_checked": [gate_summary],
        "machine_gates_passed": bool(gate_summary.get("passed")) and not blocked,
        "autonomy_profile": selected_autonomy_profile,
        "dry_run": bool(effective_dry_run),
        "github_enabled": bool(github_enabled),
        "github_execution_performed": bool(github_state_result.get("github_execution_performed") and not blocked),
        "mutation_performed": False,
        "github_issue_mutation_performed": False,
        "registry_mutation_performed": False,
        "queue_mutation_performed": False,
        "codex_execution_performed": False,
        "model_execution_performed": False,
        "patch_application_performed": False,
        "idempotency_key": idempotency_key,
        "recovery_available": True,
        "local_only": not bool(github_state_result.get("github_execution_performed") and not blocked),
        "next_safe_action": _next_safe_action(blocked=blocked, dry_run=effective_dry_run, operation_counts=operation_counts),
        "artifacts_created": [],
        "queue_path": str(queue_path_resolved),
        "registry_path": _text(registry_payload.get("registry_path")),
        "github_state_path": _text(github_state_result.get("github_state_path")),
        "github_state_source": _text(github_state_result.get("source")),
        "github_state_available": bool(github_state_result["state_available"]),
        "source_plan_record_type": _text(plan_payload.get("record_type")),
        "queue_item_count": len(reconciliation_items),
        "github_issue_state_count": len(github_issues),
        "registry_record_count": _int(registry_payload.get("matched_record_count")),
        "operation_counts": operation_counts,
        "reconciliation_items": reconciliation_items,
        "recommended_actions": [action for item in reconciliation_items for action in _dicts(item.get("recommended_actions"))],
        "autonomy_profile_summary": _autonomy_summary(autonomy_payload),
        "github_mutation_scope": "recommendation_only_issue_state_reconciliation",
        "github_operations_blocked": [
            "create_issue",
            "update_issue",
            "create_comment",
            "close_issue",
            "reopen_issue",
            "merge_pull_request",
            "force_push",
            "update_protected_branch",
            "enable_auto_merge",
            "create_release",
            "modify_github_workflow",
            "source_code_patch",
        ],
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
        "completed_at": _now_iso(),
    }
    return _emit_or_write(config=config, payload=payload, output=output, force=force)


def _reconcile_item(
    *,
    plan_item: dict[str, Any],
    registry_records: list[dict[str, Any]],
    github_issues: dict[int, dict[str, Any]],
    project_id: str,
    repository: str,
    dry_run: bool,
    github_enabled: bool,
    autonomy_profile: str,
    github_state_available: bool,
) -> dict[str, Any]:
    item_id = _text(plan_item.get("item_id"))
    linked_issue = plan_item.get("linked_issue") if isinstance(plan_item.get("linked_issue"), dict) else {}
    registry_record = _registry_record_for_item(registry_records, item_id)
    issue_number = _int(registry_record.get("issue_number")) or _int(linked_issue.get("issue_number")) or None
    issue_url = _text(registry_record.get("issue_url")) or _text(linked_issue.get("issue_url"))
    github_issue = github_issues.get(issue_number or -1, {})
    recommended_actions = _recommended_actions(
        plan_item=plan_item,
        registry_record=registry_record,
        github_issue=github_issue,
        issue_number=issue_number,
        github_state_available=github_state_available,
    )
    sync_status = _item_sync_status(recommended_actions)
    return {
        "record_type": "github_issue_state_reconciliation_item_v1",
        "artifact_type": "github_issue_state_reconciliation_item_v1",
        "generated": True,
        "project_id": project_id,
        "item_id": item_id,
        "repository": repository,
        "issue_number": issue_number,
        "issue_url": issue_url or _text(github_issue.get("html_url") or github_issue.get("url")),
        "pr_number": registry_record.get("pr_number"),
        "pr_url": _text(registry_record.get("pr_url")),
        "sync_status": sync_status,
        "blocked": bool(plan_item.get("blocked")),
        "blocked_reasons": _list(plan_item.get("blocked_reasons")),
        "warnings": _dedupe([*_list(plan_item.get("warnings")), *_issue_state_warnings(issue_number, github_issue, github_state_available)]),
        "machine_gates_checked": [],
        "machine_gates_passed": not bool(plan_item.get("blocked")),
        "autonomy_profile": autonomy_profile,
        "dry_run": bool(dry_run),
        "github_enabled": bool(github_enabled),
        "github_execution_performed": False,
        "mutation_performed": False,
        "github_issue_mutation_performed": False,
        "registry_mutation_performed": False,
        "queue_mutation_performed": False,
        "idempotency_key": _item_idempotency_key(project_id=project_id, item_id=item_id, repository=repository),
        "recovery_available": True,
        "local_only": True,
        "next_safe_action": _item_next_safe_action(sync_status),
        "queue_status": _text(plan_item.get("queue_status")),
        "linked_issue": linked_issue or {"linked": False, "issue_number": None, "issue_url": "", "metadata_source": ""},
        "registry_link": _registry_summary(registry_record),
        "github_issue_state": _issue_summary(github_issue),
        "issue_payload": plan_item.get("issue_draft", {}),
        "recommended_actions": recommended_actions,
    }


def _recommended_actions(
    *,
    plan_item: dict[str, Any],
    registry_record: dict[str, Any],
    github_issue: dict[str, Any],
    issue_number: int | None,
    github_state_available: bool,
) -> list[dict[str, Any]]:
    item_id = _text(plan_item.get("item_id"))
    if bool(plan_item.get("blocked")):
        return [_action("skip", item_id, "Queue item has local blockers.")]
    queue_status = _text(plan_item.get("queue_status"))
    issue_draft = plan_item.get("issue_draft") if isinstance(plan_item.get("issue_draft"), dict) else {}
    plan_recommendations = _dicts(plan_item.get("recommendations"))
    has_local_link = bool(issue_number or _text(registry_record.get("issue_url")))
    has_github_issue = bool(github_issue)
    github_state = _text(github_issue.get("state")).lower()

    if not has_local_link:
        return [_action("create", item_id, "No local queue metadata or registry issue link exists.", issue_draft=issue_draft)]
    if github_state_available and not has_github_issue:
        return [_action("create", item_id, "Local link exists but the GitHub issue was absent from the observed issue-state snapshot.", issue_number=issue_number, issue_draft=issue_draft)]
    if not github_state_available:
        return [_action("skip", item_id, "GitHub issue state was not supplied or fetched; linked issue cannot be reconciled beyond local metadata.", issue_number=issue_number)]
    if github_state in {"closed", "closed_completed", "closed_not_planned"} and queue_status not in {"done", "cancelled"}:
        return [_action("reopen", item_id, "GitHub issue is closed while the local queue item is not complete or cancelled.", issue_number=issue_number)]

    actions: list[dict[str, Any]] = []
    if github_state == "open" and queue_status == "done":
        actions.append(_action("close", item_id, "Local queue item is done while the GitHub issue remains open.", issue_number=issue_number))
    if _title_drift(issue_draft, github_issue) or _label_drift(issue_draft, github_issue):
        actions.append(_action("update", item_id, "Local issue draft differs from the observed GitHub title or labels.", issue_number=issue_number, issue_draft=issue_draft))
    if any(_text(recommendation.get("recommended_action")) == "comment" for recommendation in plan_recommendations):
        comments = [comment for comment in _list_dicts(issue_draft.get("comments"))]
        actions.append(_action("comment", item_id, "Local validation or evidence comments are available for the linked issue.", issue_number=issue_number, comments=comments))
    if not actions:
        actions.append(_action("skip", item_id, "Local and observed GitHub issue state do not require a safe follow-up recommendation.", issue_number=issue_number))
    return actions


def _github_state(
    *,
    config: AppConfig,
    repo: str,
    github_state_path: str | Path | None,
    issue_numbers: list[int],
    dry_run: bool,
    github_enabled: bool,
    github_client: GitHubIssueStateClient | None,
) -> dict[str, Any]:
    if github_state_path:
        path = _resolve(config.repo_root, github_state_path)
        load_result = _load_github_state_file(path)
        return {
            "source": "mocked_state_file",
            "github_state_path": str(path),
            "state_available": load_result.get("ok", False),
            "issues_by_number": _issues_by_number(_dicts(load_result.get("issues"))),
            "warnings": load_result.get("warnings", []),
            "blocked_reasons": load_result.get("blocked_reasons", []),
            "github_execution_performed": False,
        }
    if not dry_run and github_enabled:
        try:
            client = github_client or GhCliGitHubIssueStateClient()
            issues = client.list_issues(repo=repo, issue_numbers=issue_numbers)
            return {
                "source": "live_github_read",
                "github_state_path": "",
                "state_available": True,
                "issues_by_number": _issues_by_number(issues),
                "warnings": [],
                "blocked_reasons": [],
                "github_execution_performed": True,
            }
        except (RuntimeError, OSError, subprocess.SubprocessError) as exc:
            return {
                "source": "live_github_read_failed",
                "github_state_path": "",
                "state_available": False,
                "issues_by_number": {},
                "warnings": [],
                "blocked_reasons": [f"GitHub issue state read failed: {exc}"],
                "github_execution_performed": False,
            }
    return {
        "source": "not_requested",
        "github_state_path": "",
        "state_available": False,
        "issues_by_number": {},
        "warnings": ["No GitHub issue-state snapshot supplied; reconciliation is based on local queue and registry state only."],
        "blocked_reasons": [],
        "github_execution_performed": False,
    }


def _load_github_state_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"ok": False, "issues": [], "warnings": [], "blocked_reasons": [f"GitHub state file not found: {path}"]}
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"ok": False, "issues": [], "warnings": [], "blocked_reasons": [f"GitHub state file could not be read as JSON: {exc}"]}
    if isinstance(raw, list):
        return {"ok": True, "issues": raw, "warnings": [], "blocked_reasons": []}
    if isinstance(raw, dict):
        issues = raw.get("issues", raw.get("github_issues", []))
        if isinstance(issues, list):
            return {"ok": True, "issues": issues, "warnings": _list(raw.get("warnings")), "blocked_reasons": []}
    return {"ok": False, "issues": [], "warnings": [], "blocked_reasons": ["GitHub state file must contain an issues array."]}


def _blocked_reasons(
    *,
    plan_payload: dict[str, Any],
    registry_payload: dict[str, Any],
    github_state_result: dict[str, Any],
    gate_payload: dict[str, Any],
    autonomy_payload: dict[str, Any],
    dry_run: bool,
    github_enabled: bool,
    autonomy_profile: str,
    repo: str,
) -> list[str]:
    reasons = [
        *_list(plan_payload.get("blocked_reasons")),
        *_list(registry_payload.get("blocked_reasons")),
        *_list(github_state_result.get("blocked_reasons")),
        *_list(gate_payload.get("blocked_reasons")),
    ]
    if bool(plan_payload.get("blocked")):
        reasons.append("GitHub issue sync source plan is blocked.")
    if bool(registry_payload.get("blocked")):
        reasons.append("GitHub link registry lookup is blocked.")
    if not repo or "/" not in repo:
        reasons.append("Repository must use owner/name format.")
    if gate_payload.get("passed") is not True or gate_payload.get("blocked") is True:
        reasons.append("GitHub issue state reconciliation machine gate did not pass.")
    if not dry_run and not github_enabled:
        reasons.append("Live GitHub issue-state reconciliation requires --github-enabled.")
    if not dry_run:
        if autonomy_profile != LIVE_AUTONOMY_PROFILE:
            reasons.append(f"Live GitHub issue-state reconciliation requires autonomy_profile={LIVE_AUTONOMY_PROFILE}.")
        if not _github_issue_sync_capability_enabled(autonomy_payload):
            reasons.append("Selected autonomy profile does not enable github_issue_sync.")
        if autonomy_payload.get("blocked") is True or autonomy_payload.get("machine_gates_passed") is not True:
            reasons.append("Autonomy profile inspection did not pass required machine gates.")
    return _dedupe(reasons)


def _gate_payload(
    config: AppConfig,
    *,
    item_id: str,
    queue_path: str | Path | None,
    dry_run: bool,
    github_enabled: bool,
) -> dict[str, Any]:
    if dry_run:
        result = evaluate_machine_safety_gates(
            config,
            item_id=item_id,
            gate_profile="read_only_agent",
            queue_path=queue_path,
            output_format="json",
        )
    else:
        result = evaluate_machine_safety_gates(
            config,
            item_id=item_id,
            gate_profile="github_sync",
            queue_path=queue_path,
            force=bool(github_enabled),
            output_format="json",
        )
    return _payload(result)


def _local_issue_numbers(plan_payload: dict[str, Any], registry_records: list[dict[str, Any]]) -> list[int]:
    numbers: list[int] = []
    for record in registry_records:
        number = _int(record.get("issue_number"))
        if number:
            numbers.append(number)
    for plan_item in _dicts(plan_payload.get("issue_sync_items")):
        linked = plan_item.get("linked_issue") if isinstance(plan_item.get("linked_issue"), dict) else {}
        number = _int(linked.get("issue_number"))
        if number:
            numbers.append(number)
    return sorted(set(numbers))


def _registry_record_for_item(records: list[dict[str, Any]], item_id: str) -> dict[str, Any]:
    for record in records:
        if _text(record.get("queue_item_id")) == item_id:
            return record
    return {}


def _operation_counts(items: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"create": 0, "update": 0, "comment": 0, "close": 0, "reopen": 0, "skip": 0}
    for item in items:
        for action in _dicts(item.get("recommended_actions")):
            recommended_action = _text(action.get("recommended_action"))
            if recommended_action in counts:
                counts[recommended_action] += 1
    return counts


def _item_sync_status(actions: list[dict[str, Any]]) -> str:
    non_skip = [_text(action.get("recommended_action")) for action in actions if _text(action.get("recommended_action")) != "skip"]
    if not non_skip:
        return "skip_recommended"
    if "create" in non_skip:
        return "create_recommended"
    if "reopen" in non_skip:
        return "reopen_recommended"
    if "close" in non_skip:
        return "close_recommended"
    if "update" in non_skip or "comment" in non_skip:
        return "sync_recommended"
    return "skip_recommended"


def _title_drift(issue_draft: dict[str, Any], github_issue: dict[str, Any]) -> bool:
    return bool(_text(issue_draft.get("title")) and _text(github_issue.get("title")) and _text(issue_draft.get("title")) != _text(github_issue.get("title")))


def _label_drift(issue_draft: dict[str, Any], github_issue: dict[str, Any]) -> bool:
    local_labels = set(_list(issue_draft.get("labels")))
    github_labels = set(_github_labels(github_issue))
    return bool(local_labels and github_labels and not local_labels.issubset(github_labels))


def _github_labels(github_issue: dict[str, Any]) -> list[str]:
    labels = github_issue.get("labels")
    if isinstance(labels, list):
        result: list[str] = []
        for label in labels:
            if isinstance(label, dict):
                result.append(_text(label.get("name")))
            else:
                result.append(_text(label))
        return [label for label in result if label]
    return []


def _action(
    action: str,
    item_id: str,
    reason: str,
    *,
    issue_number: int | None = None,
    issue_draft: dict[str, Any] | None = None,
    comments: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "record_type": "github_issue_state_reconciliation_action_v1",
        "item_id": item_id,
        "issue_number": issue_number,
        "recommended_action": action,
        "reason": reason,
        "issue_draft": issue_draft or {},
        "comments": comments or [],
        "github_execution_performed": False,
        "mutation_performed": False,
        "local_only": True,
    }


def _issue_state_warnings(issue_number: int | None, github_issue: dict[str, Any], github_state_available: bool) -> list[str]:
    if issue_number and not github_state_available:
        return ["Linked issue state was not available; no live or mocked GitHub comparison was performed for this item."]
    if issue_number and github_state_available and not github_issue:
        return ["Linked issue was not found in the observed GitHub issue-state snapshot."]
    return []


def _issue_summary(value: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict) or not value:
        return {}
    return {
        "number": _int(value.get("number")) or None,
        "title": _text(value.get("title")),
        "state": _text(value.get("state")),
        "url": _text(value.get("html_url") or value.get("url")),
        "labels": _github_labels(value),
        "updated_at": _text(value.get("updatedAt") or value.get("updated_at")),
    }


def _registry_summary(value: dict[str, Any]) -> dict[str, Any]:
    if not value:
        return {}
    return {
        "queue_item_id": _text(value.get("queue_item_id")),
        "repository": _text(value.get("repository")),
        "issue_number": value.get("issue_number"),
        "issue_url": _text(value.get("issue_url")),
        "sync_status": _text(value.get("sync_status")),
        "comment_id": _text(value.get("comment_id")),
        "idempotency_key": _text(value.get("idempotency_key")),
    }


def _issues_by_number(issues: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    result: dict[int, dict[str, Any]] = {}
    for issue in issues:
        number = _int(issue.get("number"))
        if number:
            result[number] = issue
    return result


def _autonomy_summary(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "record_type": _text(payload.get("record_type")),
        "status": _text(payload.get("status")),
        "blocked": bool(payload.get("blocked")),
        "blocked_reasons": _list(payload.get("blocked_reasons")),
        "machine_gates_passed": bool(payload.get("machine_gates_passed")),
        "autonomy_profile": _text(payload.get("autonomy_profile")),
        "github_issue_sync_enabled": _github_issue_sync_capability_enabled(payload),
    }


def _github_issue_sync_capability_enabled(autonomy_payload: dict[str, Any]) -> bool:
    selected = autonomy_payload.get("selected_profile")
    controls = selected.get("capability_controls", []) if isinstance(selected, dict) else []
    if not isinstance(controls, list):
        return False
    for control in controls:
        if isinstance(control, dict) and control.get("capability_id") == "github_issue_sync":
            return _text(control.get("status")) == "enabled"
    return False


def _gate_summary(gate_payload: dict[str, Any], *, default_profile: str) -> dict[str, Any]:
    checks = gate_payload.get("checks", [])
    failed = [
        _text(check.get("check_id"))
        for check in checks
        if isinstance(check, dict) and not bool(check.get("passed")) and not bool(check.get("warning_only"))
    ]
    return {
        "gate_profile": _text(gate_payload.get("gate_profile")) or default_profile,
        "passed": bool(gate_payload.get("passed")) and not bool(gate_payload.get("blocked")),
        "blocked": bool(gate_payload.get("blocked")),
        "blocked_reasons": _list(gate_payload.get("blocked_reasons")),
        "checks_failed": failed,
    }


def _next_safe_action(*, blocked: bool, dry_run: bool, operation_counts: dict[str, int]) -> str:
    if blocked:
        return "Resolve reconciliation blockers before relying on GitHub issue-state recommendations."
    if dry_run:
        return "Review create/update/comment/close/reopen/skip recommendations; any live mutation requires a separate explicit gated command."
    if any(operation_counts.get(action, 0) for action in ("create", "update", "comment", "close", "reopen")):
        return "Review recommendations and use only separate gated GitHub commands for any mutation."
    return "No GitHub follow-up is recommended from this reconciliation snapshot."


def _item_next_safe_action(sync_status: str) -> str:
    if sync_status == "create_recommended":
        return "Review the issue draft before any separate gated issue creation command."
    if sync_status == "sync_recommended":
        return "Review update/comment recommendations before any separate gated issue sync command."
    if sync_status == "close_recommended":
        return "Review closure evidence; issue closure remains a separate gated path and is not performed here."
    if sync_status == "reopen_recommended":
        return "Review local queue state before any separate gated issue reopen path."
    return "No live GitHub action is safe from this recommendation record alone."


def _emit_or_write(*, config: AppConfig, payload: dict[str, Any], output: str | Path | None, force: bool) -> dict[str, Any]:
    if output is None:
        return {
            "command": COMMAND_NAME,
            "ok": not bool(payload.get("blocked")),
            "local_only": bool(payload.get("local_only")),
            "format": "json",
            "wrote_output_file": False,
            "stdout": json.dumps(payload, indent=2),
            "payload": payload,
        }
    output_path = _resolve(config.repo_root, output)
    if output_path.exists() and not force:
        blocked = dict(payload)
        blocked["status"] = "blocked"
        blocked["sync_status"] = "blocked"
        blocked["blocked"] = True
        blocked["blocked_reasons"] = _dedupe([*_list(blocked.get("blocked_reasons")), "Output file already exists. Re-run with --force to overwrite."])
        blocked["github_execution_performed"] = False
        blocked["mutation_performed"] = False
        return {
            "command": COMMAND_NAME,
            "ok": False,
            "local_only": True,
            "format": "json",
            "output": str(output_path),
            "force": force,
            "wrote_output_file": False,
            "stdout": json.dumps(blocked, indent=2),
            "payload": blocked,
        }
    artifact_payload = dict(payload)
    artifact_payload["artifacts_created"] = _dedupe([*_list(payload.get("artifacts_created")), str(output_path)])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact_payload, indent=2) + "\n", encoding="utf-8")
    return {
        "command": COMMAND_NAME,
        "ok": not bool(artifact_payload.get("blocked")),
        "local_only": bool(artifact_payload.get("local_only")),
        "format": "json",
        "output": str(output_path),
        "force": force,
        "wrote_output_file": True,
        "payload": artifact_payload,
    }


def _payload(result: dict[str, Any]) -> dict[str, Any]:
    payload = result.get("payload", {}) if isinstance(result, dict) else {}
    return payload if isinstance(payload, dict) else {}


def _normalize_repo(config: AppConfig, repo: str | None) -> str:
    raw = _text(repo)
    if raw:
        return raw
    return f"{config.github_owner}/{config.github_repo}"


def _idempotency_key(*, project_id: str, repository: str) -> str:
    return "github-issue-state-reconciliation:" + ":".join([_slug(project_id), _slug(repository)])


def _item_idempotency_key(*, project_id: str, item_id: str, repository: str) -> str:
    return "github-issue-state-reconciliation-item:" + ":".join([_slug(project_id), _slug(item_id), _slug(repository)])


def _resolve(repo_root: Path, value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


def _list_dicts(value: Any) -> list[dict[str, Any]]:
    return _dicts(value)


def _dicts(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [entry for entry in value if isinstance(entry, dict)]
    return []


def _list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [_text(entry) for entry in value if _text(entry)]
    if isinstance(value, tuple):
        return [_text(entry) for entry in value if _text(entry)]
    if value in (None, ""):
        return []
    return [_text(value)]


def _dedupe(values: Any) -> list[str]:
    deduped: list[str] = []
    for value in values:
        text = _text(value)
        if text and text not in deduped:
            deduped.append(text)
    return deduped


def _int(value: Any) -> int:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    text = _text(value)
    return int(text) if text.isdigit() else 0


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", _text(value).lower()).strip("-") or "unknown"


def _text(value: Any) -> str:
    return str(value or "").strip()


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _error(error: str, details: dict[str, Any]) -> dict[str, Any]:
    return {
        "command": COMMAND_NAME,
        "ok": False,
        "local_only": True,
        "error": error,
        "details": details,
    }
