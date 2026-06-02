from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
import subprocess
from typing import Any, Protocol

from aresforge.config import AppConfig
from aresforge.operator.github_issue_sync_plan import plan_github_issue_sync
from aresforge.operator.local_project_queue import resolve_project_queue_path
from aresforge.operator.machine_safety_gate_engine import evaluate_machine_safety_gates
from aresforge.operator.operator_autonomy_configuration_profile import inspect_autonomy_profile
from aresforge.operator.orchestration_run_monitor import inspect_orchestration_run_monitor

COMMAND_NAME = "sync-github-issue-status-comment"
RECORD_TYPE = "github_issue_status_comment_sync_v1"
DEFAULT_PROJECT_ID = "aresforge"
DEFAULT_AUTONOMY_PROFILE = "github_sync_dry_run"
LIVE_AUTONOMY_PROFILE = "github_issue_sync_enabled"
STATUS_COMMENT_MARKER = "<!-- aresforge:github-issue-status-comment-sync:v1 -->"
SAFE_QUEUE_STATUSES: frozenset[str] = frozenset({"proposed", "ready", "in_progress", "done"})

_BOUNDARY_CONFIRMATIONS: tuple[str, ...] = (
    "Dry-run is the default behavior and performs no GitHub mutation.",
    "Live status comment sync requires --github-enabled, a non-dry-run request, github_issue_sync_enabled autonomy profile, linked issue metadata, safe queue item status, and a passing github_sync machine gate.",
    "Only one queue item and one issue status comment are considered per command invocation.",
    "The generated comment body contains queue status, run evidence, validation evidence, artifact references, machine gates, and next safe action.",
    "No queue mutation, Codex execution, model execution, source patch application, PR merge, protected branch update, force push, auto-merge, release, workflow mutation, retry, resume, or next-item execution is performed.",
)


class GitHubIssueStatusCommentClient(Protocol):
    def find_status_comment(self, *, repo: str, issue_number: int, marker: str) -> dict[str, Any] | None:
        ...

    def create_comment(self, *, repo: str, issue_number: int, body: str) -> dict[str, Any]:
        ...

    def update_comment(self, *, repo: str, comment_id: int | str, body: str) -> dict[str, Any]:
        ...


@dataclass(frozen=True)
class GhCliGitHubIssueStatusCommentClient:
    timeout_seconds: int = 30

    def find_status_comment(self, *, repo: str, issue_number: int, marker: str) -> dict[str, Any] | None:
        command = [
            "gh",
            "api",
            f"repos/{repo}/issues/{issue_number}/comments",
            "--paginate",
            "--jq",
            ".[] | {id: .id, html_url: .html_url, body: .body, updated_at: .updated_at}",
        ]
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=max(1, self.timeout_seconds),
            shell=False,
        )
        if completed.returncode != 0:
            detail = completed.stderr.strip() or completed.stdout.strip() or "gh issue comment lookup failed"
            raise RuntimeError(detail)
        for line in completed.stdout.splitlines():
            try:
                comment = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(comment, dict) and marker in str(comment.get("body") or ""):
                return comment
        return None

    def create_comment(self, *, repo: str, issue_number: int, body: str) -> dict[str, Any]:
        completed = subprocess.run(
            ["gh", "issue", "comment", str(issue_number), "--repo", repo, "--body", body],
            check=False,
            capture_output=True,
            text=True,
            timeout=max(1, self.timeout_seconds),
            shell=False,
        )
        if completed.returncode != 0:
            detail = completed.stderr.strip() or completed.stdout.strip() or "gh issue comment create failed"
            raise RuntimeError(detail)
        url = completed.stdout.strip()
        return {"html_url": url, "url": url}

    def update_comment(self, *, repo: str, comment_id: int | str, body: str) -> dict[str, Any]:
        completed = subprocess.run(
            ["gh", "api", f"repos/{repo}/issues/comments/{comment_id}", "-X", "PATCH", "-f", f"body={body}"],
            check=False,
            capture_output=True,
            text=True,
            timeout=max(1, self.timeout_seconds),
            shell=False,
        )
        if completed.returncode != 0:
            detail = completed.stderr.strip() or completed.stdout.strip() or "gh issue comment update failed"
            raise RuntimeError(detail)
        try:
            parsed = json.loads(completed.stdout or "{}")
        except json.JSONDecodeError:
            parsed = {}
        return parsed if isinstance(parsed, dict) else {}


def sync_github_issue_status_comment(
    config: AppConfig,
    *,
    item_id: str,
    project_id: str = DEFAULT_PROJECT_ID,
    queue_path: str | Path | None = None,
    run_id: str | None = None,
    dry_run: bool = True,
    github_enabled: bool = False,
    autonomy_profile: str = DEFAULT_AUTONOMY_PROFILE,
    repo: str | None = None,
    issue_number: int | None = None,
    output: str | Path | None = None,
    force: bool = False,
    output_format: str = "json",
    github_client: GitHubIssueStatusCommentClient | None = None,
) -> dict[str, Any]:
    fmt = _text(output_format).lower() or "json"
    if fmt != "json":
        return _error("invalid_format", {"format": output_format, "supported_formats": ["json"]})

    normalized_item_id = _text(item_id)
    normalized_project_id = _text(project_id) or DEFAULT_PROJECT_ID
    normalized_repo = _normalize_repo(config, repo)
    selected_autonomy_profile = _text(autonomy_profile) or DEFAULT_AUTONOMY_PROFILE
    requested_dry_run = bool(dry_run)
    effective_dry_run = requested_dry_run or not bool(github_enabled)
    generated_at = _now_iso()

    queue_path_resolved = resolve_project_queue_path(config.repo_root, queue_path)
    queue_result = _load_queue(queue_path_resolved)
    queue = queue_result.get("queue") if queue_result.get("ok") else {}
    item = _find_item(queue, normalized_item_id)
    item_project_id = _text(item.get("project_id")) or normalized_project_id

    plan_payload = _payload(
        plan_github_issue_sync(
            config,
            project_id=item_project_id,
            item_id=normalized_item_id,
            queue_path=queue_path,
            output_format="json",
        )
    )
    item_plan = _item_plan(plan_payload, normalized_item_id)
    linked_issue = item_plan.get("linked_issue") if isinstance(item_plan.get("linked_issue"), dict) else {}
    effective_issue_number = _int(issue_number) or _int(linked_issue.get("issue_number"))

    monitor_payload = _payload(
        inspect_orchestration_run_monitor(
            config,
            project_id=item_project_id,
            item_id=normalized_item_id,
            run_id=run_id,
            queue_path=queue_path,
            output_format="json",
        )
    )
    autonomy_payload = _payload(
        inspect_autonomy_profile(
            config,
            project_id=item_project_id,
            item_id=normalized_item_id,
            autonomy_profile=selected_autonomy_profile,
            queue_path=queue_path,
            output_format="json",
        )
    )
    comment_body = _status_comment_body(
        item=item,
        item_plan=item_plan,
        monitor_payload=monitor_payload,
        generated_at=generated_at,
        machine_gate_status="pending",
    )

    preflight_path: Path | None = None
    if not effective_dry_run and github_enabled:
        preflight_path = _write_preflight_record(
            config=config,
            item_id=normalized_item_id,
            project_id=item_project_id,
            repo=normalized_repo,
            issue_number=effective_issue_number,
            comment_body=comment_body,
            autonomy_profile=selected_autonomy_profile,
        )
    gate_payload = _gate_payload(
        config,
        item_id=normalized_item_id,
        queue_path=queue_path,
        dry_run=effective_dry_run,
        github_enabled=bool(github_enabled),
        preflight_path=preflight_path,
    )
    gate_summary = _gate_summary(gate_payload, default_profile="read_only_agent" if effective_dry_run else "github_sync")
    comment_body = _status_comment_body(
        item=item,
        item_plan=item_plan,
        monitor_payload=monitor_payload,
        generated_at=generated_at,
        machine_gate_status="passed" if gate_summary.get("passed") else "blocked",
    )

    blocked_reasons = _blocked_reasons(
        queue_result=queue_result,
        item=item,
        item_plan=item_plan,
        plan_payload=plan_payload,
        linked_issue=linked_issue,
        effective_issue_number=effective_issue_number,
        github_enabled=bool(github_enabled),
        effective_dry_run=effective_dry_run,
        selected_autonomy_profile=selected_autonomy_profile,
        autonomy_payload=autonomy_payload,
        gate_payload=gate_payload,
        repo=normalized_repo,
    )
    warnings = _dedupe(
        [
            *queue_result.get("warnings", []),
            *_list(plan_payload.get("warnings")),
            *_list(item_plan.get("warnings")),
            *_list(monitor_payload.get("warnings")),
            *_list(autonomy_payload.get("warnings")),
            *_list(gate_payload.get("warnings")),
        ]
    )

    github_execution_performed = False
    status_comment_synced = False
    operation = "dry_run"
    existing_comment: dict[str, Any] = {}
    synced_comment: dict[str, Any] = {}
    operation_error = ""
    if not blocked_reasons and not effective_dry_run:
        client = github_client or GhCliGitHubIssueStatusCommentClient()
        try:
            existing = client.find_status_comment(repo=normalized_repo, issue_number=effective_issue_number, marker=STATUS_COMMENT_MARKER)
            existing_comment = existing or {}
            if existing:
                synced_comment = client.update_comment(repo=normalized_repo, comment_id=existing.get("id"), body=comment_body)
                operation = "update"
            else:
                synced_comment = client.create_comment(repo=normalized_repo, issue_number=effective_issue_number, body=comment_body)
                operation = "create"
            github_execution_performed = True
            status_comment_synced = True
        except (RuntimeError, OSError, subprocess.SubprocessError) as exc:
            operation_error = str(exc)
            blocked_reasons.append(f"GitHub issue status comment sync failed: {exc}")

    blocked = bool(blocked_reasons)
    payload: dict[str, Any] = {
        "record_type": RECORD_TYPE,
        "artifact_type": RECORD_TYPE,
        "generated": True,
        "generated_at": generated_at,
        "project_id": item_project_id,
        "item_id": normalized_item_id,
        "run_id": _text(run_id) or _text(monitor_payload.get("run_id")),
        "status": _status(blocked=blocked, dry_run=effective_dry_run, synced=status_comment_synced),
        "blocked": blocked,
        "blocked_reasons": _dedupe(blocked_reasons),
        "warnings": warnings,
        "machine_gates_checked": [gate_summary],
        "machine_gates_passed": bool(gate_summary.get("passed")) and not blocked,
        "autonomy_profile": selected_autonomy_profile,
        "artifacts_created": [str(preflight_path)] if preflight_path else [],
        "mutation_performed": bool(status_comment_synced and not blocked),
        "queue_mutation_performed": False,
        "codex_execution_performed": False,
        "model_execution_performed": False,
        "github_execution_performed": bool(github_execution_performed and not blocked),
        "patch_application_performed": False,
        "local_only": not bool(github_execution_performed and not blocked),
        "next_safe_action": _next_safe_action(blocked=blocked, dry_run=effective_dry_run, synced=status_comment_synced),
        "dry_run": bool(effective_dry_run),
        "github_enabled": bool(github_enabled),
        "repo": normalized_repo,
        "issue_number": effective_issue_number,
        "queue_path": str(queue_path_resolved),
        "queue_item_found": bool(item),
        "queue_status": _text(item.get("status")),
        "queue_summary": _queue_summary(item),
        "orchestration_run_summary": _run_summary(monitor_payload),
        "validation_evidence": _validation_evidence(item),
        "artifact_links_or_paths": _artifact_paths(item, monitor_payload),
        "machine_gate_status": gate_summary,
        "linked_issue": linked_issue or {"linked": False, "issue_number": None, "issue_url": "", "metadata_source": ""},
        "status_comment_marker": STATUS_COMMENT_MARKER,
        "status_comment_body": comment_body,
        "status_comment_sync_allowed": not blocked and not effective_dry_run,
        "status_comment_synced": bool(status_comment_synced and not blocked),
        "status_comment_operation": operation if status_comment_synced else ("dry_run" if effective_dry_run else "blocked"),
        "existing_status_comment": _summarize_comment(existing_comment),
        "synced_status_comment": _summarize_comment(synced_comment) if status_comment_synced and not blocked else {},
        "operation_error": operation_error,
        "github_preflight_record_path": str(preflight_path) if preflight_path else "",
        "autonomy_profile_summary": _autonomy_summary(autonomy_payload),
        "source_plan_summary": _source_plan_summary(plan_payload, item_plan),
        "github_mutation_scope": "single_issue_status_comment_create_or_update",
        "github_operations_blocked": [
            "merge_pull_request",
            "force_push",
            "update_protected_branch",
            "enable_auto_merge",
            "create_release",
            "modify_github_workflow",
            "close_issue",
            "bulk_comment_sync",
        ],
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
        "completed_at": _now_iso(),
    }
    return _emit_or_write(config=config, payload=payload, output=output, force=force)


def _status_comment_body(
    *,
    item: dict[str, Any],
    item_plan: dict[str, Any],
    monitor_payload: dict[str, Any],
    generated_at: str,
    machine_gate_status: str,
) -> str:
    validation = _validation_evidence(item)
    artifacts = _artifact_paths(item, monitor_payload)
    run_summary = _run_summary(monitor_payload)
    lines = [
        STATUS_COMMENT_MARKER,
        "## AresForge Queue Status",
        f"- generated_at: {generated_at}",
        f"- item_id: {_text(item.get('item_id'))}",
        f"- project_id: {_text(item.get('project_id'))}",
        f"- queue_status: {_text(item.get('status')) or 'missing'}",
        f"- blocked: {str(bool(item_plan.get('blocked') or _text(item.get('status')) == 'blocked')).lower()}",
        f"- blocked_reasons: {_join_or_none(_list(item_plan.get('blocked_reasons')) + _list(item.get('blocked_by')))}",
        "",
        "## Orchestration Run Summary",
        f"- run_id: {run_summary['run_id'] or 'none'}",
        f"- status: {run_summary['status'] or 'no_runs'}",
        f"- steps: {run_summary['steps_completed']}/{run_summary['steps_total']}",
        f"- next_safe_action: {run_summary['next_safe_action'] or 'Review local queue and run evidence before any gated follow-up.'}",
        "",
        "## Validation Evidence",
        f"- validation_summary: {validation['validation_summary'] or 'None recorded.'}",
        f"- tests_run: {_join_or_none(validation['tests_run'])}",
        f"- evidence_note: {validation['evidence_note'] or 'None recorded.'}",
        "",
        "## Artifact Links Or Paths",
    ]
    lines.extend([f"- {entry}" for entry in artifacts] or ["- None recorded."])
    lines.extend(
        [
            "",
            "## Machine Gate Status",
            f"- status_comment_sync_gate: {machine_gate_status}",
            "- live_sync_requires: --github-enabled, github_issue_sync_enabled autonomy profile, linked issue metadata, safe queue status, and github_sync gate pass",
            "",
            "## Next Safe Action",
            _next_comment_action(item=item, item_plan=item_plan, monitor_payload=monitor_payload),
        ]
    )
    return "\n".join(lines)


def _gate_payload(
    config: AppConfig,
    *,
    item_id: str,
    queue_path: str | Path | None,
    dry_run: bool,
    github_enabled: bool,
    preflight_path: Path | None,
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
            artifact_path=preflight_path,
            execution_record=preflight_path,
            queue_path=queue_path,
            force=bool(github_enabled),
            output_format="json",
        )
    return _payload(result)


def _write_preflight_record(
    *,
    config: AppConfig,
    item_id: str,
    project_id: str,
    repo: str,
    issue_number: int,
    comment_body: str,
    autonomy_profile: str,
) -> Path:
    path = config.artifact_root / "github_issue_status_comment_sync" / "gates" / f"{_stamp()}-{_safe_id(item_id)}.json"
    payload = {
        "artifact_type": "github_issue_status_comment_sync_preflight_v1",
        "execution_record_type": "github_issue_status_comment_sync_preflight_v1",
        "item_id": item_id,
        "project_id": project_id,
        "repo": repo,
        "issue_number": issue_number,
        "status_comment_marker": STATUS_COMMENT_MARKER,
        "comment_body_sha_hint": str(len(comment_body)),
        "autonomy_profile": autonomy_profile,
        "local_only": True,
        "execution_allowed": False,
        "execution_performed": False,
        "external_execution_performed": False,
        "github_execution_performed": False,
        "model_execution_performed": False,
        "codex_execution_performed": False,
        "patch_application_performed": False,
        "queue_mutation_performed": False,
        "validation_commands": ["python -m pytest tests/test_github_issue_status_comment_sync.py"],
        "tests_reported": ["python -m pytest tests/test_github_issue_status_comment_sync.py -> runnable"],
        "capabilities_used": ["read_local_queue", "read_local_run_monitor", "read_local_issue_sync_plan"],
        "created_at": _now_iso(),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def _blocked_reasons(
    *,
    queue_result: dict[str, Any],
    item: dict[str, Any],
    item_plan: dict[str, Any],
    plan_payload: dict[str, Any],
    linked_issue: dict[str, Any],
    effective_issue_number: int,
    github_enabled: bool,
    effective_dry_run: bool,
    selected_autonomy_profile: str,
    autonomy_payload: dict[str, Any],
    gate_payload: dict[str, Any],
    repo: str,
) -> list[str]:
    reasons = [*queue_result.get("blocked_reasons", [])]
    if not queue_result.get("ok"):
        reasons.append("Local queue must be readable before GitHub issue status comment sync can be considered.")
    if not item:
        reasons.append("Queue item must exist before GitHub issue status comment sync can be considered.")
    status = _text(item.get("status"))
    if item and status not in SAFE_QUEUE_STATUSES:
        reasons.append(f"Queue item status is not safe for status comment sync: {status or 'missing'}.")
    if _list(item.get("blocked_by")):
        reasons.append("Queue item has blocked_by entries.")
    if not item_plan:
        reasons.append("Queue item was not present in the GitHub issue sync plan.")
    if bool(item_plan.get("blocked")):
        reasons.extend(_list(item_plan.get("blocked_reasons")))
    if bool(plan_payload.get("blocked")):
        reasons.extend(_list(plan_payload.get("blocked_reasons")))
    if not repo or "/" not in repo:
        reasons.append("Repository must use owner/name format.")
    if not effective_dry_run and not github_enabled:
        reasons.append("Live status comment sync requires --github-enabled.")
    if not effective_dry_run:
        if effective_issue_number <= 0:
            reasons.append("Live status comment sync requires linked GitHub issue metadata or --issue-number.")
        if selected_autonomy_profile != LIVE_AUTONOMY_PROFILE:
            reasons.append(f"Live status comment sync requires autonomy_profile={LIVE_AUTONOMY_PROFILE}.")
        if not _github_issue_sync_capability_enabled(autonomy_payload):
            reasons.append("Selected autonomy profile does not enable github_issue_sync.")
        if autonomy_payload.get("blocked") is True or autonomy_payload.get("machine_gates_passed") is not True:
            reasons.append("Autonomy profile inspection did not pass required machine gates.")
        if gate_payload.get("passed") is not True or gate_payload.get("blocked") is True:
            reasons.append("GitHub issue status comment sync machine gate did not pass.")
            reasons.extend(_list(gate_payload.get("blocked_reasons")))
    elif gate_payload.get("passed") is not True or gate_payload.get("blocked") is True:
        reasons.append("Dry-run read-only machine gate did not pass.")
        reasons.extend(_list(gate_payload.get("blocked_reasons")))
    return _dedupe(reasons)


def _github_issue_sync_capability_enabled(autonomy_payload: dict[str, Any]) -> bool:
    selected = autonomy_payload.get("selected_profile")
    controls = selected.get("capability_controls", []) if isinstance(selected, dict) else []
    if not isinstance(controls, list):
        return False
    for control in controls:
        if isinstance(control, dict) and control.get("capability_id") == "github_issue_sync":
            return _text(control.get("status")) == "enabled"
    return False


def _payload(result: dict[str, Any]) -> dict[str, Any]:
    payload = result.get("payload", {}) if isinstance(result, dict) else {}
    return payload if isinstance(payload, dict) else {}


def _item_plan(plan_payload: dict[str, Any], item_id: str) -> dict[str, Any]:
    for entry in plan_payload.get("issue_sync_items", []):
        if isinstance(entry, dict) and _text(entry.get("item_id")) == item_id:
            return entry
    return {}


def _queue_summary(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": _text(item.get("status")),
        "priority": _text(item.get("priority")),
        "item_type": _text(item.get("item_type")),
        "dependencies": _list(item.get("dependencies")) + _list(item.get("depends_on")),
        "blocked_by": _list(item.get("blocked_by")),
    }


def _run_summary(payload: dict[str, Any]) -> dict[str, Any]:
    latest = payload.get("latest_run", {}) if isinstance(payload.get("latest_run"), dict) else {}
    step_summary = payload.get("step_result_summary", {}) if isinstance(payload.get("step_result_summary"), dict) else {}
    return {
        "record_type": _text(payload.get("record_type")),
        "run_id": _text(payload.get("run_id") or latest.get("run_id")),
        "status": _text(payload.get("status") or latest.get("status")),
        "blocked": bool(payload.get("blocked") or latest.get("blocked")),
        "blocked_reasons": _list(payload.get("blocked_reasons")) + _list(latest.get("blocked_reasons")),
        "steps_total": _int(step_summary.get("steps_total") or latest.get("steps_total")),
        "steps_completed": _int(step_summary.get("steps_completed") or latest.get("steps_completed")),
        "next_safe_action": _text(payload.get("next_safe_action") or latest.get("next_safe_action")),
    }


def _validation_evidence(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "validation_summary": _text(item.get("validation_summary")),
        "tests_run": _list(item.get("tests_run")),
        "evidence_note": _text(item.get("evidence_note")),
    }


def _artifact_paths(item: dict[str, Any], monitor_payload: dict[str, Any]) -> list[str]:
    artifacts = _list(item.get("artifact_paths"))
    refs = monitor_payload.get("artifact_references", {})
    if isinstance(refs, dict):
        artifacts.extend(_list(refs.get("latest_run_artifact_path")))
        artifacts.extend(_list(refs.get("latest_run_artifacts_created")))
        artifacts.extend(_list(refs.get("history_path")))
    return _dedupe(artifacts)


def _source_plan_summary(plan_payload: dict[str, Any], item_plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "record_type": _text(plan_payload.get("record_type")),
        "status": _text(plan_payload.get("status")),
        "machine_gates_passed": bool(plan_payload.get("machine_gates_passed")),
        "operation_counts": plan_payload.get("operation_counts", {}),
        "item_recommendations": item_plan.get("recommendations", []),
    }


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


def _status(*, blocked: bool, dry_run: bool, synced: bool) -> str:
    if blocked:
        return "blocked"
    if dry_run:
        return "dry_run_ready"
    if synced:
        return "status_comment_synced"
    return "not_executed"


def _next_safe_action(*, blocked: bool, dry_run: bool, synced: bool) -> str:
    if blocked:
        return "Resolve blocked reasons before any GitHub status comment sync attempt."
    if dry_run:
        return "Review the generated status comment and gates; live sync requires --github-enabled with autonomy_profile=github_issue_sync_enabled."
    if synced:
        return "Review the synced GitHub status comment and continue only with separate explicit gated queue or GitHub follow-up commands."
    return "No GitHub follow-up was performed."


def _next_comment_action(*, item: dict[str, Any], item_plan: dict[str, Any], monitor_payload: dict[str, Any]) -> str:
    if item_plan.get("blocked") or _text(item.get("status")) == "blocked":
        return "Resolve local queue blockers before any GitHub status comment sync."
    run_action = _text(monitor_payload.get("next_safe_action"))
    if run_action:
        return run_action
    return "Review this local status comment body before any separate approved GitHub sync command."


def _summarize_comment(value: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    keys = ("id", "node_id", "html_url", "url", "created_at", "updated_at")
    return {key: value[key] for key in keys if key in value}


def _emit_or_write(
    *,
    config: AppConfig,
    payload: dict[str, Any],
    output: str | Path | None,
    force: bool,
) -> dict[str, Any]:
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
        blocked["blocked"] = True
        blocked["blocked_reasons"] = _dedupe(
            [*_list(blocked.get("blocked_reasons")), "Output file already exists. Re-run with --force to overwrite."]
        )
        blocked["status_comment_sync_allowed"] = False
        blocked["status_comment_synced"] = False
        blocked["github_execution_performed"] = False
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


def _load_queue(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"ok": False, "queue": {}, "warnings": [], "blocked_reasons": [f"Project queue not found: {path}"]}
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"ok": False, "queue": {}, "warnings": [], "blocked_reasons": [f"Project queue could not be read as JSON: {exc}"]}
    if not isinstance(raw, dict):
        return {"ok": False, "queue": {}, "warnings": [], "blocked_reasons": ["Project queue JSON must decode to an object."]}
    return {"ok": True, "queue": raw, "warnings": [], "blocked_reasons": []}


def _find_item(queue: dict[str, Any], item_id: str) -> dict[str, Any]:
    items = queue.get("work_items", []) if isinstance(queue, dict) else []
    if not isinstance(items, list):
        return {}
    for item in items:
        if isinstance(item, dict) and _text(item.get("item_id")) == item_id:
            return item
    return {}


def _normalize_repo(config: AppConfig, repo: str | None) -> str:
    raw = _text(repo)
    if raw:
        return raw
    return f"{config.github_owner}/{config.github_repo}"


def _resolve(repo_root: Path, value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


def _safe_id(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in _text(value).lower())
    return cleaned.strip("-") or "github-issue-status-comment"


def _stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")


def _join_or_none(values: list[str]) -> str:
    return ", ".join(_dedupe(values)) if values else "None"


def _text(value: Any) -> str:
    return str(value or "").strip()


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
