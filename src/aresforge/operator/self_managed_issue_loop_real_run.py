from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import re
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.github_issue_closure_recommendation_gate import recommend_github_issue_closure
from aresforge.operator.github_issue_creation_real_run_gate import (
    DEFAULT_AUTONOMY_PROFILE,
    LIVE_AUTONOMY_PROFILE,
    GitHubIssueRealRunClient,
    create_github_issue_real_run_gate,
)
from aresforge.operator.github_issue_state_reconciliation import (
    GitHubIssueStateClient,
    reconcile_github_issue_state,
)
from aresforge.operator.github_link_registry import inspect_github_link_registry
from aresforge.operator.github_status_comment_durable_sync import (
    GitHubIssueStatusCommentClient,
    sync_github_status_comment_durable,
)
from aresforge.operator.github_sync_recovery_idempotency import inspect_github_sync_recovery
from aresforge.operator.local_project_queue import resolve_project_queue_path
from aresforge.operator.machine_safety_gate_engine import evaluate_machine_safety_gates
from aresforge.operator.operator_autonomy_configuration_profile import inspect_autonomy_profile

COMMAND_NAME = "run-self-managed-issue-loop"
RECORD_TYPE = "self_managed_issue_loop_real_run_v1"
DEFAULT_PROJECT_ID = "aresforge"
DEFAULT_ITEM_ID = "m181-self-managed-issue-loop-real-run"
SAFE_QUEUE_STATUSES: frozenset[str] = frozenset({"proposed", "ready", "in_progress", "done"})

_BOUNDARY_CONFIRMATIONS: tuple[str, ...] = (
    "Dry-run is the default behavior and performs no GitHub mutation.",
    "Real GitHub execution requires --github-enabled, a non-dry-run request, github_issue_sync_enabled autonomy profile, a safe queue item, no duplicate issue link for issue creation, and passing machine gates.",
    "The loop coordinates exactly one selected queue item through link lookup, issue creation gate, durable status comment sync, issue-state reconciliation, recovery/idempotency inspection, and closure recommendation.",
    "Closure recommendation is recommendation-only; this loop does not close issues automatically.",
    "No pull request merge, auto-merge, force push, protected branch update, release creation, workflow mutation, source patch application, queue mutation, Codex execution, model execution, validation command execution, retry, resume, or automatic next-item execution is performed.",
)


def run_self_managed_issue_loop(
    config: AppConfig,
    *,
    project_id: str = DEFAULT_PROJECT_ID,
    item_id: str | None = None,
    queue_path: str | Path | None = None,
    registry_path: str | Path | None = None,
    github_state_path: str | Path | None = None,
    dry_run: bool = True,
    github_enabled: bool = False,
    autonomy_profile: str = DEFAULT_AUTONOMY_PROFILE,
    repo: str | None = None,
    issue_number: int | None = None,
    linked_issue_state: str | None = None,
    output: str | Path | None = None,
    force: bool = False,
    output_format: str = "json",
    github_issue_client: GitHubIssueRealRunClient | None = None,
    github_status_comment_client: GitHubIssueStatusCommentClient | None = None,
    github_issue_state_client: GitHubIssueStateClient | None = None,
) -> dict[str, Any]:
    fmt = _text(output_format).lower() or "json"
    if fmt != "json":
        return _error("invalid_format", {"format": output_format, "supported_formats": ["json"]})

    normalized_project_id = _text(project_id) or DEFAULT_PROJECT_ID
    requested_item_id = _text(item_id)
    repository = _normalize_repo(config, repo)
    selected_autonomy_profile = _text(autonomy_profile) or DEFAULT_AUTONOMY_PROFILE
    effective_dry_run = bool(dry_run) or not bool(github_enabled)
    generated_at = _now_iso()
    queue_path_resolved = resolve_project_queue_path(config.repo_root, queue_path)
    registry_path_text = str(_resolve(config.repo_root, registry_path)) if registry_path else ""
    idempotency_key = _idempotency_key(
        project_id=normalized_project_id,
        item_id=requested_item_id or DEFAULT_ITEM_ID,
        repository=repository,
    )

    output_path = _resolve(config.repo_root, output) if output else None
    if output_path and output_path.exists() and not force:
        payload = _base_payload(
            project_id=normalized_project_id,
            item_id=requested_item_id or DEFAULT_ITEM_ID,
            repository=repository,
            generated_at=generated_at,
            autonomy_profile=selected_autonomy_profile,
            dry_run=effective_dry_run,
            github_enabled=bool(github_enabled),
            idempotency_key=idempotency_key,
        )
        payload.update(
            {
                "status": "blocked",
                "sync_status": "blocked",
                "blocked": True,
                "blocked_reasons": ["Output file already exists. Re-run with --force to overwrite."],
                "next_safe_action": "Choose a different output path or re-run with --force.",
            }
        )
        return _emit(config=config, payload=payload, output=output_path, ok=False)

    queue_result = _load_queue(queue_path_resolved)
    queue_items = _dicts(queue_result.get("work_items"))
    selected_item = _select_queue_item(
        queue_items,
        project_id=normalized_project_id,
        requested_item_id=requested_item_id,
    )
    normalized_item_id = _text(selected_item.get("item_id")) or requested_item_id or DEFAULT_ITEM_ID
    item_project_id = _text(selected_item.get("project_id")) or normalized_project_id
    idempotency_key = _idempotency_key(project_id=item_project_id, item_id=normalized_item_id, repository=repository)

    read_gate_payload = _payload(
        evaluate_machine_safety_gates(
            config,
            item_id=normalized_item_id,
            gate_profile="read_only_agent",
            queue_path=queue_path,
            output_format="json",
        )
    )
    read_gate = _gate_summary(read_gate_payload, default_profile="read_only_agent")
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
    registry_lookup_payload = _payload(
        inspect_github_link_registry(
            config,
            project_id=item_project_id,
            item_id=normalized_item_id,
            registry_path=registry_path,
            queue_item_id=normalized_item_id,
            repository=repository,
            output_format="json",
        )
    )

    loop_blockers = _loop_blockers(
        queue_result=queue_result,
        item=selected_item,
        read_gate=read_gate,
        repository=repository,
        effective_dry_run=effective_dry_run,
        github_enabled=bool(github_enabled),
        autonomy_profile=selected_autonomy_profile,
        autonomy_payload=autonomy_payload,
    )

    issue_creation_dry_run = effective_dry_run or bool(loop_blockers)
    issue_creation = _payload(
        create_github_issue_real_run_gate(
            config,
            item_id=normalized_item_id,
            project_id=item_project_id,
            queue_path=queue_path,
            registry_path=registry_path,
            dry_run=issue_creation_dry_run,
            github_enabled=bool(github_enabled) and not issue_creation_dry_run,
            autonomy_profile=selected_autonomy_profile,
            repo=repository,
            output_format="json",
            github_client=github_issue_client,
        )
    )
    effective_issue_number = _int(issue_number) or _int(issue_creation.get("issue_number")) or _linked_issue_number(
        selected_item,
        registry_lookup_payload,
    )
    status_comment_dry_run = effective_dry_run or bool(loop_blockers) or bool(issue_creation.get("blocked"))
    status_comment = _payload(
        sync_github_status_comment_durable(
            config,
            item_id=normalized_item_id,
            project_id=item_project_id,
            queue_path=queue_path,
            registry_path=registry_path,
            dry_run=status_comment_dry_run,
            github_enabled=bool(github_enabled) and not status_comment_dry_run,
            autonomy_profile=selected_autonomy_profile,
            repo=repository,
            issue_number=effective_issue_number,
            output_format="json",
            github_client=github_status_comment_client,
        )
    )
    reconciliation_dry_run = True
    reconciliation = _payload(
        reconcile_github_issue_state(
            config,
            project_id=item_project_id,
            item_id=normalized_item_id,
            queue_path=queue_path,
            registry_path=registry_path,
            github_state_path=github_state_path,
            dry_run=reconciliation_dry_run,
            github_enabled=False,
            autonomy_profile=selected_autonomy_profile,
            repo=repository,
            output_format="json",
            github_client=github_issue_state_client,
        )
    )
    recovery = _payload(
        inspect_github_sync_recovery(
            config,
            project_id=item_project_id,
            item_id=normalized_item_id,
            queue_path=queue_path,
            registry_path=registry_path,
            repo=repository,
            output_format="json",
        )
    )
    closure_recommendation = _payload(
        recommend_github_issue_closure(
            config,
            item_id=normalized_item_id,
            project_id=item_project_id,
            queue_path=queue_path,
            autonomy_profile=selected_autonomy_profile,
            linked_issue_state=linked_issue_state,
            output_format="json",
        )
    )

    steps = [
        _step("link_lookup", registry_lookup_payload, mutation_capable=False),
        _step("issue_creation_gate", issue_creation, mutation_capable=True),
        _step("status_comment_sync", status_comment, mutation_capable=True),
        _step("issue_state_reconciliation", reconciliation, mutation_capable=False),
        _step("recovery_idempotency", recovery, mutation_capable=False),
        _step("closure_recommendation", closure_recommendation, mutation_capable=False, recommendation_only=True),
    ]
    machine_gates = [read_gate]
    for payload in (issue_creation, status_comment, reconciliation, recovery, closure_recommendation):
        machine_gates.extend(_dicts(payload.get("machine_gates_checked")))

    live_required_blockers = []
    if not effective_dry_run:
        live_required_blockers.extend(
            reason for step in steps if step["blocked"] and step["mutation_capable"] for reason in _list(step["blocked_reasons"])
        )
    blocked_reasons = _dedupe([*loop_blockers, *live_required_blockers])
    blocked = bool(blocked_reasons)
    github_execution_performed = any(bool(step.get("github_execution_performed")) for step in steps) and not blocked
    mutation_performed = any(bool(step.get("mutation_performed")) for step in steps) and not blocked
    issue_url = _text(issue_creation.get("issue_url")) or _linked_issue_url(selected_item, registry_lookup_payload)
    payload = _base_payload(
        project_id=item_project_id,
        item_id=normalized_item_id,
        repository=repository,
        generated_at=generated_at,
        autonomy_profile=selected_autonomy_profile,
        dry_run=effective_dry_run,
        github_enabled=bool(github_enabled),
        idempotency_key=idempotency_key,
    )
    payload.update(
        {
            "issue_number": effective_issue_number or None,
            "issue_url": issue_url,
            "sync_status": "blocked" if blocked else ("dry_run_completed" if effective_dry_run else "real_run_completed"),
            "status": "blocked" if blocked else ("dry_run_completed" if effective_dry_run else "real_run_completed"),
            "blocked": blocked,
            "blocked_reasons": blocked_reasons,
            "warnings": _dedupe(
                [
                    *queue_result.get("warnings", []),
                    *_list(autonomy_payload.get("warnings")),
                    *(warning for step in steps for warning in _list(step.get("warnings"))),
                    *_loop_warnings(effective_dry_run=effective_dry_run, steps=steps),
                ]
            ),
            "machine_gates_checked": machine_gates,
            "machine_gates_passed": bool(machine_gates)
            and all(bool(gate.get("passed")) for gate in machine_gates)
            and not blocked,
            "github_execution_performed": bool(github_execution_performed),
            "mutation_performed": bool(mutation_performed),
            "github_issue_mutation_performed": bool(issue_creation.get("github_issue_mutation_performed")) and not blocked,
            "github_comment_mutation_performed": bool(status_comment.get("status_comment_mutation_performed")) and not blocked,
            "registry_mutation_performed": any(bool(step.get("registry_mutation_performed")) for step in steps) and not blocked,
            "queue_mutation_performed": False,
            "codex_execution_performed": False,
            "model_execution_performed": False,
            "patch_application_performed": False,
            "validation_command_execution_performed": False,
            "recovery_available": True,
            "local_only": not bool(github_execution_performed),
            "next_safe_action": _next_safe_action(blocked=blocked, dry_run=effective_dry_run, steps=steps),
            "queue_path": str(queue_path_resolved),
            "registry_path": registry_path_text or _text(registry_lookup_payload.get("registry_path")),
            "github_state_path": _text(github_state_path),
            "selected_queue_item": _queue_item_summary(selected_item, normalized_item_id),
            "autonomy_profile_summary": _autonomy_summary(autonomy_payload),
            "machine_gate_behavior": {
                "real_run_requires_github_enabled": True,
                "real_run_requires_autonomy_profile": LIVE_AUTONOMY_PROFILE,
                "dry_run_default": True,
                "closure_is_recommendation_only": True,
            },
            "loop_steps": steps,
            "link_lookup": _link_lookup_summary(registry_lookup_payload),
            "issue_creation_gate": _operation_summary(issue_creation),
            "status_comment_sync": _operation_summary(status_comment),
            "issue_state_reconciliation": _operation_summary(reconciliation),
            "recovery_idempotency": _operation_summary(recovery),
            "closure_recommendation": _closure_summary(closure_recommendation),
            "github_operations_blocked": [
                "close_issue_automatically",
                "merge_pull_request",
                "enable_auto_merge",
                "force_push",
                "update_protected_branch",
                "create_release",
                "modify_github_workflow",
                "source_code_patch",
                "queue_mutation",
                "codex_execution",
                "model_execution",
                "validation_command_execution",
                "retry",
                "resume",
                "automatic_next_item_execution",
            ],
            "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
            "completed_at": _now_iso(),
        }
    )
    return _emit(config=config, payload=payload, output=output_path, ok=not blocked)


def _base_payload(
    *,
    project_id: str,
    item_id: str,
    repository: str,
    generated_at: str,
    autonomy_profile: str,
    dry_run: bool,
    github_enabled: bool,
    idempotency_key: str,
) -> dict[str, Any]:
    return {
        "record_type": RECORD_TYPE,
        "artifact_type": RECORD_TYPE,
        "generated": True,
        "generated_at": generated_at,
        "project_id": project_id,
        "item_id": item_id,
        "repository": repository,
        "issue_number": None,
        "issue_url": "",
        "pr_number": None,
        "pr_url": "",
        "sync_status": "unknown",
        "status": "unknown",
        "blocked": False,
        "blocked_reasons": [],
        "warnings": [],
        "machine_gates_checked": [],
        "machine_gates_passed": False,
        "autonomy_profile": autonomy_profile,
        "dry_run": bool(dry_run),
        "github_enabled": bool(github_enabled),
        "github_execution_performed": False,
        "mutation_performed": False,
        "idempotency_key": idempotency_key,
        "recovery_available": True,
        "local_only": True,
        "next_safe_action": "",
    }


def _loop_blockers(
    *,
    queue_result: dict[str, Any],
    item: dict[str, Any],
    read_gate: dict[str, Any],
    repository: str,
    effective_dry_run: bool,
    github_enabled: bool,
    autonomy_profile: str,
    autonomy_payload: dict[str, Any],
) -> list[str]:
    reasons = [*queue_result.get("blocked_reasons", [])]
    if not item:
        reasons.append("A safe AresForge queue item is required before the self-managed issue loop can run.")
    if item and _text(item.get("status")) not in SAFE_QUEUE_STATUSES:
        reasons.append(f"Queue item status is not safe for self-managed issue loop: {_text(item.get('status')) or 'missing'}.")
    if item and _list(item.get("blocked_by")):
        reasons.append("Queue item has blocked_by entries.")
    if not repository or "/" not in repository:
        reasons.append("Repository must use owner/name format.")
    if not read_gate.get("passed"):
        reasons.append("Self-managed issue loop read-only machine gate did not pass.")
        reasons.extend(_list(read_gate.get("blocked_reasons")))
    if not effective_dry_run:
        if not github_enabled:
            reasons.append("Real self-managed issue loop requires --github-enabled.")
        if autonomy_profile != LIVE_AUTONOMY_PROFILE:
            reasons.append(f"Real self-managed issue loop requires autonomy_profile={LIVE_AUTONOMY_PROFILE}.")
        if autonomy_payload.get("blocked") is True or autonomy_payload.get("machine_gates_passed") is not True:
            reasons.append("Autonomy profile inspection did not pass required machine gates.")
            reasons.extend(_list(autonomy_payload.get("blocked_reasons")))
    return _dedupe(reasons)


def _select_queue_item(items: list[dict[str, Any]], *, project_id: str, requested_item_id: str) -> dict[str, Any]:
    if requested_item_id:
        for item in items:
            if _text(item.get("item_id")) == requested_item_id and (_text(item.get("project_id")) or project_id) == project_id:
                return item
        return {}
    for preferred in (DEFAULT_ITEM_ID, "m180-hub-github-sync-control-panel"):
        for item in items:
            if _text(item.get("item_id")) == preferred and (_text(item.get("project_id")) or project_id) == project_id:
                return item
    candidates = [
        item
        for item in items
        if (_text(item.get("project_id")) or project_id) == project_id
        and _text(item.get("status")) in SAFE_QUEUE_STATUSES
        and not _list(item.get("blocked_by"))
    ]
    return sorted(candidates, key=lambda candidate: _text(candidate.get("item_id")))[0] if candidates else {}


def _step(name: str, payload: dict[str, Any], *, mutation_capable: bool, recommendation_only: bool = False) -> dict[str, Any]:
    return {
        "record_type": "self_managed_issue_loop_step_v1",
        "step_id": name,
        "source_record_type": _text(payload.get("record_type")),
        "sync_status": _text(payload.get("sync_status") or payload.get("status")),
        "blocked": bool(payload.get("blocked")),
        "blocked_reasons": _list(payload.get("blocked_reasons")),
        "warnings": _list(payload.get("warnings")),
        "machine_gates_checked": _dicts(payload.get("machine_gates_checked")),
        "machine_gates_passed": bool(payload.get("machine_gates_passed")),
        "dry_run": bool(payload.get("dry_run", True)),
        "github_enabled": bool(payload.get("github_enabled")),
        "github_execution_performed": bool(payload.get("github_execution_performed")),
        "mutation_performed": bool(payload.get("mutation_performed")),
        "registry_mutation_performed": bool(payload.get("registry_mutation_performed")),
        "idempotency_key": _text(payload.get("idempotency_key")),
        "recovery_available": bool(payload.get("recovery_available", True)),
        "local_only": bool(payload.get("local_only", True)),
        "next_safe_action": _text(payload.get("next_safe_action")),
        "mutation_capable": mutation_capable,
        "recommendation_only": recommendation_only,
    }


def _operation_summary(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "record_type": _text(payload.get("record_type")),
        "status": _text(payload.get("status")),
        "sync_status": _text(payload.get("sync_status")),
        "blocked": bool(payload.get("blocked")),
        "blocked_reasons": _list(payload.get("blocked_reasons")),
        "machine_gates_passed": bool(payload.get("machine_gates_passed")),
        "github_execution_performed": bool(payload.get("github_execution_performed")),
        "mutation_performed": bool(payload.get("mutation_performed")),
        "idempotency_key": _text(payload.get("idempotency_key")),
        "next_safe_action": _text(payload.get("next_safe_action")),
    }


def _link_lookup_summary(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "record_type": _text(payload.get("record_type")),
        "status": _text(payload.get("status")),
        "blocked": bool(payload.get("blocked")),
        "matched_record_count": _int(payload.get("matched_record_count")),
        "records": _dicts(payload.get("records")),
        "github_execution_performed": False,
        "mutation_performed": False,
        "local_only": True,
    }


def _closure_summary(payload: dict[str, Any]) -> dict[str, Any]:
    summary = _operation_summary(payload)
    summary.update(
        {
            "closure_recommended": bool(payload.get("closure_recommended")),
            "keep_open_recommended": bool(payload.get("keep_open_recommended")),
            "issue_closure_allowed": False,
            "issue_closed": False,
            "recommendation_only": True,
        }
    )
    return summary


def _queue_item_summary(item: dict[str, Any], item_id: str) -> dict[str, Any]:
    return {
        "found": bool(item),
        "item_id": _text(item.get("item_id")) or item_id,
        "project_id": _text(item.get("project_id")),
        "repo_id": _text(item.get("repo_id")),
        "title": _text(item.get("title")),
        "status": _text(item.get("status")),
        "priority": _text(item.get("priority")),
        "item_type": _text(item.get("item_type")),
        "dependencies": _list(item.get("dependencies")) + _list(item.get("depends_on")),
        "blocked_by": _list(item.get("blocked_by")),
    }


def _autonomy_summary(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "record_type": _text(payload.get("record_type")),
        "status": _text(payload.get("status")),
        "blocked": bool(payload.get("blocked")),
        "blocked_reasons": _list(payload.get("blocked_reasons")),
        "machine_gates_passed": bool(payload.get("machine_gates_passed")),
        "autonomy_profile": _text(payload.get("autonomy_profile")),
    }


def _gate_summary(payload: dict[str, Any], *, default_profile: str) -> dict[str, Any]:
    checks = _dicts(payload.get("checks"))
    return {
        "gate_profile": _text(payload.get("gate_profile")) or default_profile,
        "passed": bool(payload.get("passed")) and not bool(payload.get("blocked")),
        "blocked": bool(payload.get("blocked")),
        "blocked_reasons": _list(payload.get("blocked_reasons")),
        "checks_failed": [
            _text(check.get("check_id"))
            for check in checks
            if not bool(check.get("passed")) and not bool(check.get("warning_only"))
        ],
    }


def _loop_warnings(*, effective_dry_run: bool, steps: list[dict[str, Any]]) -> list[str]:
    warnings: list[str] = []
    if effective_dry_run:
        warnings.append("Self-managed issue loop ran in dry-run mode; no GitHub mutations were performed.")
    for step in steps:
        if step["blocked"] and not step["mutation_capable"]:
            warnings.append(f"{step['step_id']} returned a blocked or keep-open advisory result for operator review.")
    return warnings


def _next_safe_action(*, blocked: bool, dry_run: bool, steps: list[dict[str, Any]]) -> str:
    if blocked:
        return "Resolve loop blockers before any live GitHub issue-loop attempt."
    if dry_run:
        return "Review the loop dry-run record; real execution requires --github-enabled with autonomy_profile=github_issue_sync_enabled and passing per-step machine gates."
    if any(step["blocked"] for step in steps):
        return "Review advisory blocked steps before any separate follow-up; no automatic closure or retry was performed."
    return "Review the completed gated GitHub coordination and durable registry state before any separate operator-approved follow-up."


def _linked_issue_number(item: dict[str, Any], registry_payload: dict[str, Any]) -> int:
    for record in _dicts(registry_payload.get("records")):
        number = _int(record.get("issue_number"))
        if number:
            return number
    github_issue = item.get("github_issue") if isinstance(item.get("github_issue"), dict) else {}
    return _int(github_issue.get("number"))


def _linked_issue_url(item: dict[str, Any], registry_payload: dict[str, Any]) -> str:
    for record in _dicts(registry_payload.get("records")):
        url = _text(record.get("issue_url"))
        if url:
            return url
    github_issue = item.get("github_issue") if isinstance(item.get("github_issue"), dict) else {}
    return _text(github_issue.get("url"))


def _load_queue(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"work_items": [], "warnings": [], "blocked_reasons": [f"Project queue not found: {path}"]}
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"work_items": [], "warnings": [], "blocked_reasons": [f"Project queue could not be read as JSON: {exc}"]}
    if not isinstance(raw, dict):
        return {"work_items": [], "warnings": [], "blocked_reasons": ["Project queue JSON must decode to an object."]}
    items = raw.get("work_items", [])
    return {"work_items": items if isinstance(items, list) else [], "warnings": [], "blocked_reasons": []}


def _emit(*, config: AppConfig, payload: dict[str, Any], output: Path | None, ok: bool) -> dict[str, Any]:
    if output is None:
        return {
            "command": COMMAND_NAME,
            "ok": bool(ok),
            "local_only": bool(payload.get("local_only")),
            "format": "json",
            "wrote_output_file": False,
            "stdout": json.dumps(payload, indent=2),
            "payload": payload,
        }
    artifact_payload = dict(payload)
    artifact_payload["artifacts_created"] = _dedupe([*_list(payload.get("artifacts_created")), str(output)])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(artifact_payload, indent=2) + "\n", encoding="utf-8")
    return {
        "command": COMMAND_NAME,
        "ok": bool(ok),
        "local_only": bool(artifact_payload.get("local_only")),
        "format": "json",
        "output": str(output),
        "wrote_output_file": True,
        "payload": artifact_payload,
    }


def _payload(result: dict[str, Any]) -> dict[str, Any]:
    payload = result.get("payload", {}) if isinstance(result, dict) else {}
    return payload if isinstance(payload, dict) else {}


def _normalize_repo(config: AppConfig, repo: str | None) -> str:
    raw = _text(repo)
    return raw or f"{config.github_owner}/{config.github_repo}"


def _idempotency_key(*, project_id: str, item_id: str, repository: str) -> str:
    return "self-managed-issue-loop:" + ":".join([_slug(project_id), _slug(item_id), _slug(repository)])


def _resolve(repo_root: Path, value: str | Path | None) -> Path:
    path = Path(value or "")
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


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
