from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import re
import subprocess
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.github_issue_sync_plan import plan_github_issue_sync
from aresforge.operator.github_link_registry import inspect_github_link_registry
from aresforge.operator.local_project_queue import resolve_project_queue_path
from aresforge.operator.machine_safety_gate_engine import evaluate_machine_safety_gates
from aresforge.operator.operator_autonomy_configuration_profile import inspect_autonomy_profile
from aresforge.operator.pull_request_draft_summary_generator import generate_pr_draft_summary

COMMAND_NAME = "plan-pr-draft-branch"
RECORD_TYPE = "pr_draft_branch_planning_contract_v1"
DEFAULT_PROJECT_ID = "aresforge"
DEFAULT_ITEM_ID = "m176-pr-draft-branch-planning-contract"
DEFAULT_AUTONOMY_PROFILE = "github_sync_dry_run"

_BOUNDARY_CONFIRMATIONS: tuple[str, ...] = (
    "This command generates a local PR draft branch plan only.",
    "No branch is created, checked out, pushed, force-pushed, or updated by this command.",
    "No pull request is created, updated, merged, marked auto-merge, or synchronized by this command.",
    "Live GitHub PR or branch mutation remains unavailable in M176 even when --github-enabled is supplied.",
    "No queue mutation, Codex execution, model execution, source patch application, validation command execution, issue closure, release creation, workflow mutation, retry, resume, or next-item execution is performed.",
)

_GITHUB_OPERATIONS_BLOCKED: tuple[str, ...] = (
    "create_branch",
    "checkout_branch",
    "push_branch",
    "force_push",
    "update_protected_branch",
    "create_pull_request",
    "update_pull_request",
    "merge_pull_request",
    "enable_auto_merge",
    "create_release",
    "modify_github_workflow",
    "close_issue",
    "source_code_patch",
)


def plan_pr_draft_branch(
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
    base_branch: str | None = None,
    branch_prefix: str = "codex",
    evidence_bundle: str | Path | None = None,
    output: str | Path | None = None,
    force: bool = False,
    output_format: str = "json",
) -> dict[str, Any]:
    fmt = _text(output_format).lower() or "json"
    if fmt != "json":
        return _error("invalid_format", {"format": output_format, "supported_formats": ["json"]})

    normalized_item_id = _text(item_id) or DEFAULT_ITEM_ID
    normalized_project_id = _text(project_id) or DEFAULT_PROJECT_ID
    selected_autonomy_profile = _text(autonomy_profile) or DEFAULT_AUTONOMY_PROFILE
    normalized_repo = _normalize_repo(config, repo)
    selected_base_branch = _text(base_branch) or _current_branch(config.repo_root) or "main"
    effective_dry_run = True
    queue_path_resolved = resolve_project_queue_path(config.repo_root, queue_path)
    output_path = _resolve(config.repo_root, output) if output else None

    if output_path and output_path.exists() and not force:
        payload = _base_payload(
            project_id=normalized_project_id,
            item_id=normalized_item_id,
            repository=normalized_repo,
            generated_at=_now_iso(),
            autonomy_profile=selected_autonomy_profile,
            dry_run=effective_dry_run,
            github_enabled=bool(github_enabled),
        )
        payload.update(
            {
                "status": "blocked",
                "sync_status": "blocked",
                "blocked": True,
                "blocked_reasons": ["Output file already exists. Re-run with --force to overwrite."],
                "next_safe_action": "Re-run with --force or choose a different output path.",
            }
        )
        return _emit_or_write(config=config, payload=payload, output=output_path, force=force)

    queue_result = _load_queue(queue_path_resolved)
    queue = queue_result.get("queue") if queue_result.get("ok") else {}
    item = _find_item(queue, normalized_item_id)
    item_project_id = _text(item.get("project_id")) or normalized_project_id
    branch_name = _branch_name(branch_prefix=branch_prefix, item_id=normalized_item_id)

    issue_plan_payload = _payload(
        plan_github_issue_sync(
            config,
            project_id=item_project_id,
            item_id=normalized_item_id,
            queue_path=queue_path,
            output_format="json",
        )
    )
    item_issue_plan = _item_plan(issue_plan_payload, normalized_item_id)
    linked_issue = _linked_issue(item=item, item_issue_plan=item_issue_plan)
    registry_payload = _payload(
        inspect_github_link_registry(
            config,
            project_id=item_project_id,
            item_id=normalized_item_id,
            registry_path=registry_path,
            queue_item_id=normalized_item_id,
            repository=normalized_repo,
            issue_number=_int_or_none(linked_issue.get("issue_number")),
            output_format="json",
        )
    )
    draft_payload = _payload(
        generate_pr_draft_summary(
            config,
            item_id=normalized_item_id,
            project_id=item_project_id,
            queue_path=queue_path,
            run_id=run_id,
            autonomy_profile=selected_autonomy_profile,
            evidence_bundle=evidence_bundle,
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
    gate_payload = _gate_payload(config, item_id=normalized_item_id, queue_path=queue_path, github_enabled=bool(github_enabled))
    gate_summary = _gate_summary(gate_payload, default_profile="read_only_agent" if effective_dry_run else "github_sync")

    changed_files = _changed_files(config=config, item=item, draft_payload=draft_payload)
    expected_title = _expected_title(item=item, item_id=normalized_item_id)
    expected_body = _expected_body(
        item=item,
        linked_issue=linked_issue,
        draft_payload=draft_payload,
        branch_name=branch_name,
        base_branch=selected_base_branch,
        changed_files=changed_files,
    )
    safety_gates = _safety_gates(
        gate_summary=gate_summary,
        autonomy_payload=autonomy_payload,
        dry_run=effective_dry_run,
        github_enabled=bool(github_enabled),
    )
    blocked_reasons = _blocked_reasons(
        queue_result=queue_result,
        item=item,
        registry_payload=registry_payload,
        draft_payload=draft_payload,
        issue_plan_payload=issue_plan_payload,
        autonomy_payload=autonomy_payload,
        gate_payload=gate_payload,
        repo=normalized_repo,
        base_branch=selected_base_branch,
        changed_files=changed_files,
    )
    warnings = _warnings(
        queue_result=queue_result,
        item=item,
        registry_payload=registry_payload,
        draft_payload=draft_payload,
        issue_plan_payload=issue_plan_payload,
        autonomy_payload=autonomy_payload,
        gate_payload=gate_payload,
        github_enabled=bool(github_enabled),
        dry_run=effective_dry_run,
    )
    blocked = bool(blocked_reasons)
    status = "blocked" if blocked else "branch_plan_created"
    sync_status = "blocked" if blocked else "dry_run_ready"
    idempotency_key = _idempotency_key(
        project_id=item_project_id,
        item_id=normalized_item_id,
        repository=normalized_repo,
        base_branch=selected_base_branch,
        branch_name=branch_name,
    )

    payload = _base_payload(
        project_id=item_project_id,
        item_id=normalized_item_id,
        repository=normalized_repo,
        generated_at=_now_iso(),
        autonomy_profile=selected_autonomy_profile,
        dry_run=effective_dry_run,
        github_enabled=bool(github_enabled),
    )
    payload.update(
        {
            "run_id": _text(run_id),
            "status": status,
            "sync_status": sync_status,
            "blocked": blocked,
            "blocked_reasons": blocked_reasons,
            "warnings": warnings,
            "machine_gates_checked": [gate_summary],
            "machine_gates_passed": bool(gate_summary.get("passed")) and not blocked,
            "issue_number": _int_or_none(linked_issue.get("issue_number")),
            "issue_url": _text(linked_issue.get("issue_url")),
            "pr_number": None,
            "pr_url": "",
            "idempotency_key": idempotency_key,
            "recovery_available": True,
            "next_safe_action": _next_safe_action(blocked=blocked),
            "queue_path": str(queue_path_resolved),
            "registry_path": _text(registry_payload.get("registry_path")),
            "queue_item_found": bool(item),
            "linked_queue_items": _linked_queue_items(item),
            "linked_issues": [linked_issue] if linked_issue.get("linked") else [],
            "changed_file_evidence": {
                "changed_files": changed_files,
                "source": _changed_file_source(item=item, draft_payload=draft_payload),
                "count": len(changed_files),
            },
            "branch_plan": {
                "branch_name": branch_name,
                "base_branch": selected_base_branch,
                "repository": normalized_repo,
                "branch_prefix": _text(branch_prefix) or "codex",
                "branch_creation_allowed": False,
                "branch_created": False,
                "branch_pushed": False,
                "protected_branch_update_allowed": False,
                "force_push_allowed": False,
            },
            "expected_pr": {
                "title": expected_title,
                "body": expected_body,
                "base_branch": selected_base_branch,
                "head_branch": branch_name,
                "draft": True,
                "create_allowed": False,
                "created": False,
                "merge_allowed": False,
                "auto_merge_allowed": False,
            },
            "safety_gates": safety_gates,
            "source_plan_summary": _source_plan_summary(issue_plan_payload, item_issue_plan),
            "draft_summary_source": _draft_summary_source(draft_payload),
            "registry_lookup_summary": _registry_summary(registry_payload),
            "autonomy_profile_summary": _autonomy_summary(autonomy_payload),
            "github_mutation_scope": "none_branch_and_pr_planning_only",
            "github_operations_blocked": list(_GITHUB_OPERATIONS_BLOCKED),
            "branch_creation_allowed": False,
            "branch_created": False,
            "branch_pushed": False,
            "pr_creation_allowed": False,
            "pull_request_created": False,
            "pull_request_updated": False,
            "pull_request_merged": False,
            "auto_merge_enabled": False,
            "github_pr_mutation_performed": False,
            "github_branch_mutation_performed": False,
            "queue_mutation_performed": False,
            "codex_execution_performed": False,
            "model_execution_performed": False,
            "patch_application_performed": False,
            "validation_command_execution_performed": False,
            "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
            "completed_at": _now_iso(),
        }
    )
    return _emit_or_write(config=config, payload=payload, output=output_path, force=force)


def _base_payload(
    *,
    project_id: str,
    item_id: str,
    repository: str,
    generated_at: str,
    autonomy_profile: str,
    dry_run: bool,
    github_enabled: bool,
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
        "idempotency_key": "",
        "recovery_available": True,
        "local_only": True,
        "next_safe_action": "",
    }


def _blocked_reasons(
    *,
    queue_result: dict[str, Any],
    item: dict[str, Any],
    registry_payload: dict[str, Any],
    draft_payload: dict[str, Any],
    issue_plan_payload: dict[str, Any],
    autonomy_payload: dict[str, Any],
    gate_payload: dict[str, Any],
    repo: str,
    base_branch: str,
    changed_files: list[str],
) -> list[str]:
    reasons = [
        *queue_result.get("blocked_reasons", []),
        *_list(registry_payload.get("blocked_reasons")),
        *_list(issue_plan_payload.get("blocked_reasons")),
        *_list(gate_payload.get("blocked_reasons")),
    ]
    if not queue_result.get("ok"):
        reasons.append("Local queue must be readable before a PR draft branch plan can be generated.")
    if not item:
        reasons.append("Queue item must exist before a PR draft branch plan can be generated.")
    if item and _list(item.get("blocked_by")):
        reasons.append("Queue item has blocked_by entries.")
    if not repo or "/" not in repo:
        reasons.append("Repository must use owner/name format.")
    if not base_branch:
        reasons.append("Base branch is required.")
    if not changed_files:
        reasons.append("Changed file evidence is required before a complete PR draft branch plan can be generated.")
    if bool(draft_payload.get("blocked")):
        reasons.append("PR draft summary source is blocked.")
        reasons.extend(_list(draft_payload.get("blocked_reasons")))
    if bool(registry_payload.get("blocked")):
        reasons.append("GitHub link registry lookup is blocked.")
    if bool(issue_plan_payload.get("blocked")):
        reasons.append("GitHub issue sync planning source is blocked.")
    if bool(autonomy_payload.get("blocked")):
        reasons.append("Autonomy profile inspection is blocked.")
        reasons.extend(_list(autonomy_payload.get("blocked_reasons")))
    if gate_payload.get("passed") is not True or gate_payload.get("blocked") is True:
        reasons.append("PR draft branch planning machine gate did not pass.")
    return _dedupe(reasons)


def _warnings(
    *,
    queue_result: dict[str, Any],
    item: dict[str, Any],
    registry_payload: dict[str, Any],
    draft_payload: dict[str, Any],
    issue_plan_payload: dict[str, Any],
    autonomy_payload: dict[str, Any],
    gate_payload: dict[str, Any],
    github_enabled: bool,
    dry_run: bool,
) -> list[str]:
    warnings = [
        *queue_result.get("warnings", []),
        *_list(registry_payload.get("warnings")),
        *_list(draft_payload.get("warnings")),
        *_list(issue_plan_payload.get("warnings")),
        *_list(autonomy_payload.get("warnings")),
        *_list(gate_payload.get("warnings")),
        "PR draft branch planning does not create branches, push branches, or create pull requests.",
    ]
    if github_enabled and dry_run:
        warnings.append("--github-enabled was supplied, but branch and PR mutation remains disabled for M176.")
    if item and _text(item.get("status")) != "done":
        warnings.append("Queue item is not done; generated PR draft branch plan may be preliminary.")
    return _dedupe(warnings)


def _expected_title(*, item: dict[str, Any], item_id: str) -> str:
    title = _text(item.get("title")) or item_id
    if re.match(r"^m\d+\b", title, flags=re.IGNORECASE):
        return title
    return f"M176 {title}"


def _expected_body(
    *,
    item: dict[str, Any],
    linked_issue: dict[str, Any],
    draft_payload: dict[str, Any],
    branch_name: str,
    base_branch: str,
    changed_files: list[str],
) -> str:
    source_body = _text(draft_payload.get("draft_pr_body_markdown"))
    summary = _text(draft_payload.get("summary")) or _text(item.get("validation_summary")) or _text(item.get("description"))
    issue_line = ""
    if linked_issue.get("linked"):
        issue_number = _text(linked_issue.get("issue_number"))
        issue_url = _text(linked_issue.get("issue_url"))
        issue_line = f"\nLinked issue: #{issue_number} {issue_url}".strip()
    lines = [
        f"Branch plan: {branch_name} from {base_branch}",
        "",
        "Summary:",
        summary or "No summary recorded yet.",
        issue_line,
        "",
        "Changed files:",
        *_bullets(changed_files),
        "",
        "Safety:",
        "- Draft PR creation remains disabled by M176.",
        "- Branch creation and pushing remain disabled by M176.",
    ]
    if source_body:
        lines.extend(["", "Draft summary source:", source_body])
    return "\n".join(line for line in lines if line is not None)


def _safety_gates(*, gate_summary: dict[str, Any], autonomy_payload: dict[str, Any], dry_run: bool, github_enabled: bool) -> list[dict[str, Any]]:
    return [
        {
            "gate_id": "branch_creation_disabled",
            "passed": True,
            "required_for_live_mutation": True,
            "message": "Branch creation is not implemented or allowed in M176.",
        },
        {
            "gate_id": "pr_creation_disabled",
            "passed": True,
            "required_for_live_mutation": True,
            "message": "Pull request creation is not implemented or allowed in M176.",
        },
        {
            "gate_id": "dry_run_default",
            "passed": bool(dry_run),
            "required_for_live_mutation": False,
            "message": "Default operation is dry-run/local planning.",
        },
        {
            "gate_id": "github_enablement_advisory",
            "passed": not bool(github_enabled) or bool(dry_run),
            "required_for_live_mutation": False,
            "message": "GitHub enablement is advisory only for this planning command.",
        },
        {
            "gate_id": "machine_gate",
            "passed": bool(gate_summary.get("passed")),
            "required_for_live_mutation": False,
            "message": _text(gate_summary.get("gate_profile")) or "read_only_agent",
        },
        {
            "gate_id": "autonomy_profile_inspected",
            "passed": not bool(autonomy_payload.get("blocked")),
            "required_for_live_mutation": False,
            "message": _text(autonomy_payload.get("autonomy_profile")),
        },
    ]


def _linked_queue_items(item: dict[str, Any]) -> list[dict[str, Any]]:
    if not item:
        return []
    links = [
        {"item_id": _text(item.get("item_id")), "relationship": "primary", "status": _text(item.get("status"))},
    ]
    for dep in _dedupe([*_list(item.get("dependencies")), *_list(item.get("depends_on"))]):
        links.append({"item_id": dep, "relationship": "dependency", "status": "unknown"})
    return links


def _linked_issue(*, item: dict[str, Any], item_issue_plan: dict[str, Any]) -> dict[str, Any]:
    plan_issue = item_issue_plan.get("linked_issue") if isinstance(item_issue_plan.get("linked_issue"), dict) else {}
    queue_issue = item.get("github_issue") if isinstance(item.get("github_issue"), dict) else {}
    issue_number = _int_or_none(plan_issue.get("issue_number")) or _int_or_none(queue_issue.get("number"))
    issue_url = _text(plan_issue.get("issue_url")) or _text(queue_issue.get("url"))
    return {
        "linked": bool(issue_number or issue_url),
        "issue_number": issue_number,
        "issue_url": issue_url,
        "state": _text(queue_issue.get("state")) or _text(plan_issue.get("state")) or "unknown",
        "metadata_source": _text(plan_issue.get("metadata_source")) or ("queue.github_issue" if queue_issue else ""),
    }


def _changed_files(*, config: AppConfig, item: dict[str, Any], draft_payload: dict[str, Any]) -> list[str]:
    return _dedupe(
        path.replace("\\", "/")
        for path in [
            *_list(item.get("changed_files")),
            *_list(draft_payload.get("changed_files")),
            *_git_diff_files(config.repo_root),
        ]
    )


def _changed_file_source(*, item: dict[str, Any], draft_payload: dict[str, Any]) -> list[str]:
    sources: list[str] = []
    if _list(item.get("changed_files")):
        sources.append("queue.changed_files")
    if _list(draft_payload.get("changed_files")):
        sources.append("pr_draft_summary.changed_files")
    sources.append("git.diff.head")
    return _dedupe(sources)


def _source_plan_summary(plan_payload: dict[str, Any], item_plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "record_type": _text(plan_payload.get("record_type")),
        "status": _text(plan_payload.get("status")),
        "blocked": bool(plan_payload.get("blocked")),
        "machine_gates_passed": bool(plan_payload.get("machine_gates_passed")),
        "item_recommendations": item_plan.get("recommendations", []),
    }


def _draft_summary_source(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "record_type": _text(payload.get("record_type")),
        "status": _text(payload.get("status")),
        "blocked": bool(payload.get("blocked")),
        "blocked_reasons": _list(payload.get("blocked_reasons")),
        "machine_gates_passed": bool(payload.get("machine_gates_passed")),
        "pr_creation_allowed": bool(payload.get("pr_creation_allowed")),
        "pull_request_created": bool(payload.get("pull_request_created")),
    }


def _registry_summary(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "record_type": _text(payload.get("record_type")),
        "status": _text(payload.get("status")),
        "blocked": bool(payload.get("blocked")),
        "matched_record_count": _int_or_none(payload.get("matched_record_count")) or 0,
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
    }


def _gate_payload(config: AppConfig, *, item_id: str, queue_path: str | Path | None, github_enabled: bool) -> dict[str, Any]:
    result = evaluate_machine_safety_gates(
        config,
        item_id=item_id,
        gate_profile="read_only_agent",
        queue_path=queue_path,
        output_format="json",
        force=bool(github_enabled),
    )
    return _payload(result)


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


def _item_plan(plan_payload: dict[str, Any], item_id: str) -> dict[str, Any]:
    for entry in plan_payload.get("issue_sync_items", []):
        if isinstance(entry, dict) and _text(entry.get("item_id")) == item_id:
            return entry
    return {}


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
            "local_only": True,
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
        blocked["mutation_performed"] = False
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
        "local_only": True,
        "format": "json",
        "output": str(output_path),
        "force": force,
        "wrote_output_file": True,
        "stdout": json.dumps(artifact_payload, indent=2),
        "payload": artifact_payload,
    }


def _normalize_repo(config: AppConfig, repo: str | None) -> str:
    raw = _text(repo)
    if raw:
        return raw
    return f"{config.github_owner}/{config.github_repo}"


def _branch_name(*, branch_prefix: str, item_id: str) -> str:
    prefix = _slug(branch_prefix or "codex")
    return f"{prefix}/{_slug(item_id)}"


def _current_branch(repo_root: Path) -> str:
    try:
        completed = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    if completed.returncode != 0:
        return ""
    return _text(completed.stdout)


def _git_diff_files(repo_root: Path) -> list[str]:
    try:
        completed = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    if completed.returncode != 0:
        return []
    return _dedupe(line.strip().replace("\\", "/") for line in completed.stdout.splitlines() if line.strip())


def _payload(result: dict[str, Any]) -> dict[str, Any]:
    payload = result.get("payload", {}) if isinstance(result, dict) else {}
    return payload if isinstance(payload, dict) else {}


def _next_safe_action(*, blocked: bool) -> str:
    if blocked:
        return "Resolve branch-plan blockers and regenerate the local plan; do not create branches or PRs from this command."
    return "Review the local branch plan; any future branch or PR creation must use a separate explicit machine-gated command."


def _idempotency_key(*, project_id: str, item_id: str, repository: str, base_branch: str, branch_name: str) -> str:
    return "pr-draft-branch-plan:" + ":".join(
        [_slug(project_id), _slug(item_id), _slug(repository), _slug(base_branch), _slug(branch_name)]
    )


def _resolve(repo_root: Path, value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


def _bullets(values: Any) -> list[str]:
    entries = _list(values)
    return [f"- {entry}" for entry in entries] if entries else ["- None recorded."]


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", _text(value).lower()).strip("-") or "unknown"


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


def _int_or_none(value: Any) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    text = _text(value)
    return int(text) if text.isdigit() else None


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
