from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
import re
import subprocess
from typing import Any, Protocol

from aresforge.config import AppConfig
from aresforge.operator.github_issue_closure_recommendation_gate import recommend_github_issue_closure
from aresforge.operator.github_issue_creation_real_run_gate import (
    DEFAULT_AUTONOMY_PROFILE,
    LIVE_AUTONOMY_PROFILE,
)
from aresforge.operator.github_issue_state_reconciliation import reconcile_github_issue_state
from aresforge.operator.github_link_registry import inspect_github_link_registry, record_github_link
from aresforge.operator.local_project_queue import resolve_project_queue_path
from aresforge.operator.machine_safety_gate_engine import evaluate_machine_safety_gates
from aresforge.operator.operator_autonomy_configuration_profile import inspect_autonomy_profile

COMMAND_NAME = "gate-github-issue-closure"
RECORD_TYPE = "github_issue_closure_safe_execution_gate_v1"
DEFAULT_PROJECT_ID = "aresforge"
DEFAULT_ITEM_ID = "m175-github-issue-closure-safe-execution-gate"

_BOUNDARY_CONFIRMATIONS: tuple[str, ...] = (
    "Dry-run is the default behavior and performs no GitHub mutation.",
    "Real issue closure requires --github-enabled, a non-dry-run request, github_issue_sync_enabled autonomy profile, an open linked issue, complete local evidence, no blockers, and a passing github_sync machine gate.",
    "Only one queue item and one linked issue close attempt are considered per command invocation.",
    "Successful real issue closure may update only the local GitHub link registry sync metadata after GitHub reports success; it does not mutate queue state.",
    "No pull request merge, auto-merge, force push, protected branch update, release creation, workflow mutation, issue creation/update/reopen, source patch application, Codex execution, model execution, validation command execution, retry, resume, or next-item execution is performed.",
)


class GitHubIssueClosureClient(Protocol):
    def close_issue(self, *, repo: str, issue_number: int, reason: str) -> dict[str, Any]:
        ...


@dataclass(frozen=True)
class GhCliGitHubIssueClosureClient:
    timeout_seconds: int = 30

    def close_issue(self, *, repo: str, issue_number: int, reason: str) -> dict[str, Any]:
        completed = subprocess.run(
            [
                "gh",
                "issue",
                "close",
                str(issue_number),
                "--repo",
                repo,
                "--reason",
                reason,
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=max(1, self.timeout_seconds),
            shell=False,
        )
        if completed.returncode != 0:
            detail = completed.stderr.strip() or completed.stdout.strip() or "gh issue close failed"
            raise RuntimeError(detail)
        url = _last_url(completed.stdout) or f"https://github.com/{repo}/issues/{issue_number}"
        return {
            "number": issue_number,
            "state": "closed",
            "html_url": url,
            "url": url,
            "reason": reason,
        }


def gate_github_issue_closure(
    config: AppConfig,
    *,
    item_id: str = DEFAULT_ITEM_ID,
    project_id: str = DEFAULT_PROJECT_ID,
    queue_path: str | Path | None = None,
    registry_path: str | Path | None = None,
    run_id: str | None = None,
    dry_run: bool = True,
    github_enabled: bool = False,
    autonomy_profile: str = DEFAULT_AUTONOMY_PROFILE,
    repo: str | None = None,
    issue_number: int | None = None,
    linked_issue_state: str | None = None,
    close_reason: str = "completed",
    output: str | Path | None = None,
    force: bool = False,
    output_format: str = "json",
    github_client: GitHubIssueClosureClient | None = None,
) -> dict[str, Any]:
    fmt = _text(output_format).lower() or "json"
    if fmt != "json":
        return _error("invalid_format", {"format": output_format, "supported_formats": ["json"]})

    normalized_item_id = _text(item_id) or DEFAULT_ITEM_ID
    normalized_project_id = _text(project_id) or DEFAULT_PROJECT_ID
    normalized_repo = _normalize_repo(config, repo)
    selected_autonomy_profile = _text(autonomy_profile) or DEFAULT_AUTONOMY_PROFILE
    normalized_close_reason = _close_reason(close_reason)
    effective_dry_run = bool(dry_run) or not bool(github_enabled)
    generated_at = _now_iso()
    queue_path_resolved = resolve_project_queue_path(config.repo_root, queue_path)
    recommendation_payload = _payload(
        recommend_github_issue_closure(
            config,
            item_id=normalized_item_id,
            project_id=normalized_project_id,
            queue_path=queue_path,
            run_id=run_id,
            autonomy_profile=selected_autonomy_profile,
            linked_issue_state=linked_issue_state,
            output_format="json",
        )
    )
    item_project_id = _text(recommendation_payload.get("project_id")) or normalized_project_id
    linked_issue = recommendation_payload.get("linked_issue") if isinstance(recommendation_payload.get("linked_issue"), dict) else {}
    selected_issue_number = _int(issue_number) or _int(linked_issue.get("issue_number")) or None
    selected_issue_url = _text(linked_issue.get("issue_url")) or (
        f"https://github.com/{normalized_repo}/issues/{selected_issue_number}" if selected_issue_number else ""
    )
    idempotency_key = _idempotency_key(
        project_id=item_project_id,
        item_id=normalized_item_id,
        repository=normalized_repo,
        issue_number=selected_issue_number,
    )
    issue_state = _text(linked_issue_state).lower() or _text(recommendation_payload.get("linked_issue_state")).lower()

    registry_payload = _payload(
        inspect_github_link_registry(
            config,
            project_id=item_project_id,
            item_id=normalized_item_id,
            registry_path=registry_path,
            queue_item_id=normalized_item_id,
            repository=normalized_repo,
            issue_number=selected_issue_number,
            output_format="json",
        )
    )
    reconciliation_payload = _payload(
        reconcile_github_issue_state(
            config,
            project_id=item_project_id,
            item_id=normalized_item_id,
            queue_path=queue_path,
            registry_path=registry_path,
            dry_run=True,
            github_enabled=False,
            autonomy_profile=selected_autonomy_profile,
            repo=normalized_repo,
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

    preflight_path: Path | None = None
    if not effective_dry_run and github_enabled:
        preflight_path = _write_preflight_record(
            config=config,
            item_id=normalized_item_id,
            project_id=item_project_id,
            repo=normalized_repo,
            issue_number=selected_issue_number,
            issue_url=selected_issue_url,
            autonomy_profile=selected_autonomy_profile,
            close_reason=normalized_close_reason,
            idempotency_key=idempotency_key,
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

    evidence_summary = _evidence_summary(recommendation_payload)
    blocked_reasons = _blocked_reasons(
        recommendation_payload=recommendation_payload,
        registry_payload=registry_payload,
        reconciliation_payload=reconciliation_payload,
        autonomy_payload=autonomy_payload,
        gate_payload=gate_payload,
        dry_run=effective_dry_run,
        github_enabled=bool(github_enabled),
        autonomy_profile=selected_autonomy_profile,
        repo=normalized_repo,
        issue_number=selected_issue_number,
        issue_state=issue_state,
        evidence_summary=evidence_summary,
    )
    warnings = _dedupe(
        [
            *_list(recommendation_payload.get("warnings")),
            *_list(registry_payload.get("warnings")),
            *_list(reconciliation_payload.get("warnings")),
            *_list(autonomy_payload.get("warnings")),
            *_list(gate_payload.get("warnings")),
            *_issue_state_warnings(issue_state, effective_dry_run),
        ]
    )

    github_execution_performed = False
    issue_closed = False
    closed_issue: dict[str, Any] = {}
    operation_error = ""
    registry_record: dict[str, Any] = {}
    registry_mutation_performed = False
    if not blocked_reasons and not effective_dry_run and selected_issue_number:
        client = github_client or GhCliGitHubIssueClosureClient()
        try:
            closed_issue = client.close_issue(
                repo=normalized_repo,
                issue_number=selected_issue_number,
                reason=normalized_close_reason,
            )
            github_execution_performed = True
            issue_closed = True
            registry_result = record_github_link(
                config,
                project_id=item_project_id,
                item_id=normalized_item_id,
                registry_path=registry_path,
                queue_item_id=normalized_item_id,
                repository=normalized_repo,
                issue_number=selected_issue_number,
                issue_url=_issue_url(closed_issue) or selected_issue_url,
                sync_status="synced",
                last_sync_result=f"{COMMAND_NAME} closed GitHub issue with reason={normalized_close_reason}.",
                linked_by="aresforge-issue-closure-gate",
                link_source=COMMAND_NAME,
                output_format="json",
            )
            registry_payload_after = _payload(registry_result)
            registry_record = registry_payload_after.get("link_record", {})
            registry_mutation_performed = bool(registry_payload_after.get("mutation_performed"))
        except (RuntimeError, OSError, subprocess.SubprocessError) as exc:
            operation_error = str(exc)
            blocked_reasons.append(f"GitHub issue closure failed: {exc}")

    blocked = bool(blocked_reasons)
    status = _status(blocked=blocked, dry_run=effective_dry_run, issue_closed=issue_closed)
    sync_status = "blocked" if blocked else ("dry_run_ready" if effective_dry_run else "issue_closed")
    payload: dict[str, Any] = {
        "record_type": RECORD_TYPE,
        "artifact_type": RECORD_TYPE,
        "generated": True,
        "generated_at": generated_at,
        "project_id": item_project_id,
        "item_id": normalized_item_id,
        "repository": normalized_repo,
        "repo": normalized_repo,
        "issue_number": selected_issue_number,
        "issue_url": _issue_url(closed_issue) or selected_issue_url,
        "pr_number": None,
        "pr_url": "",
        "run_id": _text(run_id),
        "sync_status": sync_status,
        "status": status,
        "blocked": blocked,
        "blocked_reasons": _dedupe(blocked_reasons),
        "warnings": warnings,
        "machine_gates_checked": [gate_summary],
        "machine_gates_passed": bool(gate_summary.get("passed")) and not blocked,
        "autonomy_profile": selected_autonomy_profile,
        "dry_run": bool(effective_dry_run),
        "github_enabled": bool(github_enabled),
        "github_execution_performed": bool(github_execution_performed and not blocked),
        "mutation_performed": bool(issue_closed and not blocked),
        "github_issue_mutation_performed": bool(issue_closed and not blocked),
        "registry_mutation_performed": bool(registry_mutation_performed and not blocked),
        "queue_mutation_performed": False,
        "codex_execution_performed": False,
        "model_execution_performed": False,
        "patch_application_performed": False,
        "idempotency_key": idempotency_key,
        "recovery_available": True,
        "local_only": not bool(github_execution_performed and not blocked),
        "next_safe_action": _next_safe_action(blocked=blocked, dry_run=effective_dry_run, issue_closed=issue_closed),
        "artifacts_created": [str(preflight_path)] if preflight_path else [],
        "queue_path": str(queue_path_resolved),
        "registry_path": _text(registry_payload.get("registry_path")),
        "github_preflight_record_path": str(preflight_path) if preflight_path else "",
        "linked_issue": linked_issue or {"linked": False, "issue_number": None, "issue_url": "", "metadata_source": ""},
        "linked_issue_state": issue_state,
        "evidence_summary": evidence_summary,
        "closure_recommended": bool(recommendation_payload.get("closure_recommended")),
        "issue_closure_allowed": not blocked and not effective_dry_run,
        "issue_closed": bool(issue_closed and not blocked),
        "close_reason": normalized_close_reason,
        "closed_issue": _summarize_issue(closed_issue) if issue_closed and not blocked else {},
        "local_registry_record": registry_record if issue_closed and not blocked else {},
        "operation_error": operation_error,
        "recommendation_summary": _recommendation_summary(recommendation_payload),
        "reconciliation_summary": _reconciliation_summary(reconciliation_payload, normalized_item_id),
        "registry_lookup_summary": _registry_summary(registry_payload),
        "autonomy_profile_summary": _autonomy_summary(autonomy_payload),
        "github_mutation_scope": "single_issue_close",
        "github_operations_blocked": [
            "create_issue",
            "update_issue",
            "reopen_issue",
            "bulk_issue_closure",
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


def _blocked_reasons(
    *,
    recommendation_payload: dict[str, Any],
    registry_payload: dict[str, Any],
    reconciliation_payload: dict[str, Any],
    autonomy_payload: dict[str, Any],
    gate_payload: dict[str, Any],
    dry_run: bool,
    github_enabled: bool,
    autonomy_profile: str,
    repo: str,
    issue_number: int | None,
    issue_state: str,
    evidence_summary: dict[str, Any],
) -> list[str]:
    reasons = [
        *_list(recommendation_payload.get("blocked_reasons")),
        *_list(registry_payload.get("blocked_reasons")),
        *_list(reconciliation_payload.get("blocked_reasons")),
        *_list(gate_payload.get("blocked_reasons")),
    ]
    if bool(recommendation_payload.get("blocked")) or recommendation_payload.get("closure_recommended") is not True:
        reasons.append("GitHub issue closure recommendation gate must recommend closure before execution is allowed.")
    if not issue_number:
        reasons.append("Linked GitHub issue number is required before closure can be gated.")
    if issue_state == "closed":
        reasons.append("Linked issue is already closed; no closure mutation is needed.")
    elif issue_state and issue_state not in {"open", "unknown"}:
        reasons.append(f"Linked issue state is not safe for closure: {issue_state}.")
    if not evidence_summary.get("queue_done"):
        reasons.append("Queue item status must be done before issue closure can be gated.")
    if not evidence_summary.get("validation_passed"):
        reasons.append("Validation evidence must be present and passing before issue closure can be gated.")
    if not evidence_summary.get("artifact_bundle_present"):
        reasons.append("Evidence bundle or durable artifact evidence must exist before issue closure can be gated.")
    if not evidence_summary.get("dependencies_done"):
        reasons.append("Queue dependencies must be done before issue closure can be gated.")
    if evidence_summary.get("blockers_remaining"):
        reasons.append("Queue item still has blockers remaining.")
    if bool(registry_payload.get("blocked")):
        reasons.append("GitHub link registry lookup is blocked.")
    if bool(reconciliation_payload.get("blocked")):
        reasons.append("GitHub issue state reconciliation is blocked.")
    if not repo or "/" not in repo:
        reasons.append("Repository must use owner/name format.")
    if gate_payload.get("passed") is not True or gate_payload.get("blocked") is True:
        reasons.append("GitHub issue closure machine gate did not pass.")
    if not dry_run:
        if not github_enabled:
            reasons.append("Real issue closure requires --github-enabled.")
        if autonomy_profile != LIVE_AUTONOMY_PROFILE:
            reasons.append(f"Real issue closure requires autonomy_profile={LIVE_AUTONOMY_PROFILE}.")
        if not _github_issue_sync_capability_enabled(autonomy_payload):
            reasons.append("Selected autonomy profile does not enable github_issue_sync.")
        if autonomy_payload.get("blocked") is True or autonomy_payload.get("machine_gates_passed") is not True:
            reasons.append("Autonomy profile inspection did not pass required machine gates.")
    return _dedupe(reasons)


def _evidence_summary(recommendation_payload: dict[str, Any]) -> dict[str, Any]:
    queue_completion = recommendation_payload.get("queue_completion") if isinstance(recommendation_payload.get("queue_completion"), dict) else {}
    validation = recommendation_payload.get("validation_evidence") if isinstance(recommendation_payload.get("validation_evidence"), dict) else {}
    artifacts = recommendation_payload.get("artifact_bundle") if isinstance(recommendation_payload.get("artifact_bundle"), dict) else {}
    validation_text = " ".join([_text(validation.get("validation_summary")), " ".join(_list(validation.get("tests_run")))]).lower()
    validation_passed = bool(validation.get("present")) and "failed" not in validation_text and "traceback" not in validation_text
    return {
        "queue_done": bool(queue_completion.get("done")),
        "queue_status": _text(queue_completion.get("status")),
        "dependencies_done": bool(queue_completion.get("dependencies_done")),
        "blockers_remaining": _list(queue_completion.get("blocked_by")),
        "completion_commit": _text(queue_completion.get("completion_commit")),
        "validation_evidence_present": bool(validation.get("present")),
        "validation_passed": validation_passed,
        "artifact_bundle_present": bool(artifacts.get("present")),
        "artifact_paths": _list(artifacts.get("artifact_paths")),
        "machine_gates_from_recommendation_passed": bool(recommendation_payload.get("machine_gates_passed")),
    }


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
    issue_number: int | None,
    issue_url: str,
    autonomy_profile: str,
    close_reason: str,
    idempotency_key: str,
) -> Path:
    path = config.artifact_root / "github_issue_closure_safe_execution_gate" / "gates" / f"{_stamp()}-{_safe_id(item_id)}.json"
    payload = {
        "artifact_type": "github_issue_closure_safe_execution_gate_preflight_v1",
        "execution_record_type": "github_issue_closure_safe_execution_gate_preflight_v1",
        "item_id": item_id,
        "project_id": project_id,
        "repository": repo,
        "repo": repo,
        "issue_number": issue_number,
        "issue_url": issue_url,
        "close_reason": close_reason,
        "autonomy_profile": autonomy_profile,
        "idempotency_key": idempotency_key,
        "local_only": True,
        "execution_allowed": False,
        "execution_performed": False,
        "external_execution_performed": False,
        "github_execution_performed": False,
        "model_execution_performed": False,
        "codex_execution_performed": False,
        "patch_application_performed": False,
        "queue_mutation_performed": False,
        "validation_commands": ["python -m pytest tests/test_github_issue_closure_safe_execution_gate.py"],
        "tests_reported": ["python -m pytest tests/test_github_issue_closure_safe_execution_gate.py -> runnable"],
        "capabilities_used": ["read_local_queue", "read_local_closure_recommendation", "read_local_github_link_registry"],
        "created_at": _now_iso(),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def _recommendation_summary(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "record_type": _text(payload.get("record_type")),
        "status": _text(payload.get("status")),
        "blocked": bool(payload.get("blocked")),
        "blocked_reasons": _list(payload.get("blocked_reasons")),
        "closure_recommended": bool(payload.get("closure_recommended")),
        "machine_gates_passed": bool(payload.get("machine_gates_passed")),
    }


def _reconciliation_summary(payload: dict[str, Any], item_id: str) -> dict[str, Any]:
    item_summary: dict[str, Any] = {}
    for entry in _dicts(payload.get("reconciliation_items")):
        if _text(entry.get("item_id")) == item_id:
            item_summary = {
                "sync_status": _text(entry.get("sync_status")),
                "recommended_actions": [
                    _text(action.get("recommended_action")) for action in _dicts(entry.get("recommended_actions"))
                ],
                "blocked": bool(entry.get("blocked")),
            }
            break
    return {
        "record_type": _text(payload.get("record_type")),
        "status": _text(payload.get("status")),
        "blocked": bool(payload.get("blocked")),
        "machine_gates_passed": bool(payload.get("machine_gates_passed")),
        "item": item_summary,
    }


def _registry_summary(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "record_type": _text(payload.get("record_type")),
        "status": _text(payload.get("status")),
        "blocked": bool(payload.get("blocked")),
        "blocked_reasons": _list(payload.get("blocked_reasons")),
        "matched_record_count": _int(payload.get("matched_record_count")),
        "registry_path": _text(payload.get("registry_path")),
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


def _status(*, blocked: bool, dry_run: bool, issue_closed: bool) -> str:
    if blocked:
        return "blocked"
    if dry_run:
        return "dry_run_ready"
    if issue_closed:
        return "issue_closed"
    return "not_executed"


def _next_safe_action(*, blocked: bool, dry_run: bool, issue_closed: bool) -> str:
    if blocked:
        return "Resolve blocked reasons before any live GitHub issue closure attempt."
    if dry_run:
        return "Review closure evidence, registry lookup, autonomy profile, and machine gates; real closure requires --github-enabled with autonomy_profile=github_issue_sync_enabled."
    if issue_closed:
        return "Review the closed GitHub issue and local registry sync metadata; continue only with separate explicit gated commands."
    return "No GitHub follow-up was performed."


def _issue_state_warnings(issue_state: str, dry_run: bool) -> list[str]:
    if dry_run and issue_state == "unknown":
        return ["Linked issue state is unknown from local metadata; dry-run requires operator review before any real closure."]
    return []


def _summarize_issue(value: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    keys = ("id", "number", "state", "title", "html_url", "url", "closed_at", "updated_at", "reason")
    return {key: value[key] for key in keys if key in value}


def _issue_url(value: dict[str, Any]) -> str:
    return _text(value.get("html_url") or value.get("url"))


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
        blocked["sync_status"] = "blocked"
        blocked["blocked"] = True
        blocked["blocked_reasons"] = _dedupe(
            [*_list(blocked.get("blocked_reasons")), "Output file already exists. Re-run with --force to overwrite."]
        )
        blocked["issue_closure_allowed"] = False
        blocked["issue_closed"] = False
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


def _close_reason(value: str) -> str:
    text = _text(value).lower()
    return text if text in {"completed", "not_planned"} else "completed"


def _last_url(value: str) -> str:
    matches = re.findall(r"https?://\S+", _text(value))
    return matches[-1].rstrip(").,") if matches else ""


def _idempotency_key(*, project_id: str, item_id: str, repository: str, issue_number: int | None) -> str:
    issue_part = f"issue-{issue_number}" if issue_number else "issue-linked"
    return "github-issue-closure:" + ":".join([_slug(project_id), _slug(item_id), _slug(repository), issue_part])


def _resolve(repo_root: Path, value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


def _safe_id(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in _text(value).lower())
    return cleaned.strip("-") or "github-issue-closure"


def _stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", _text(value).lower()).strip("-") or "unknown"


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
