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
from aresforge.operator.github_link_registry import inspect_github_link_registry, record_github_link
from aresforge.operator.local_project_queue import resolve_project_queue_path
from aresforge.operator.machine_safety_gate_engine import evaluate_machine_safety_gates
from aresforge.operator.operator_autonomy_configuration_profile import inspect_autonomy_profile
from aresforge.operator.pr_draft_branch_planning_contract import plan_pr_draft_branch

COMMAND_NAME = "create-pr-draft-gate"
RECORD_TYPE = "pr_draft_creation_gate_v1"
DEFAULT_PROJECT_ID = "aresforge"
DEFAULT_ITEM_ID = "m177-pr-draft-creation-gate"

_BOUNDARY_CONFIRMATIONS: tuple[str, ...] = (
    "Dry-run is the default behavior and performs no GitHub mutation.",
    "Real draft PR creation requires --github-enabled, a non-dry-run request, github_issue_sync_enabled autonomy profile with github_pr_draft_creation enabled, an approved branch plan, a safe existing branch or explicit safe branch creation enablement, and a passing github_sync machine gate.",
    "Only one queue item and one draft pull request create attempt are considered per command invocation.",
    "Successful real draft PR creation records an idempotent local GitHub link registry entry; it does not merge, update, or auto-merge the pull request.",
    "No pull request merge, auto-merge, force push, protected branch update, release creation, workflow mutation, issue closure, source patch application, queue mutation, Codex execution, model execution, validation command execution, retry, resume, or next-item execution is performed.",
)

_GITHUB_OPERATIONS_BLOCKED: tuple[str, ...] = (
    "merge_pull_request",
    "enable_auto_merge",
    "force_push",
    "update_protected_branch",
    "create_release",
    "modify_github_workflow",
    "close_issue",
    "source_code_patch",
    "queue_status_mutation",
)


class GitHubPrDraftClient(Protocol):
    def create_draft_pr(
        self,
        *,
        repo: str,
        title: str,
        body: str,
        base_branch: str,
        head_branch: str,
    ) -> dict[str, Any]:
        ...


@dataclass(frozen=True)
class GhCliGitHubPrDraftClient:
    timeout_seconds: int = 30

    def create_draft_pr(
        self,
        *,
        repo: str,
        title: str,
        body: str,
        base_branch: str,
        head_branch: str,
    ) -> dict[str, Any]:
        completed = subprocess.run(
            [
                "gh",
                "pr",
                "create",
                "--repo",
                repo,
                "--title",
                title,
                "--body",
                body,
                "--base",
                base_branch,
                "--head",
                head_branch,
                "--draft",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=max(1, self.timeout_seconds),
            shell=False,
        )
        if completed.returncode != 0:
            detail = completed.stderr.strip() or completed.stdout.strip() or "gh pr create --draft failed"
            raise RuntimeError(detail)
        url = _last_url(completed.stdout) or completed.stdout.strip()
        return {"html_url": url, "url": url, "state": "open", "draft": True}


def create_pr_draft_gate(
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
    approved_branch_plan: bool = False,
    safe_branch_creation_enabled: bool = False,
    output: str | Path | None = None,
    force: bool = False,
    output_format: str = "json",
    github_client: GitHubPrDraftClient | None = None,
) -> dict[str, Any]:
    fmt = _text(output_format).lower() or "json"
    if fmt != "json":
        return _error("invalid_format", {"format": output_format, "supported_formats": ["json"]})

    normalized_item_id = _text(item_id) or DEFAULT_ITEM_ID
    normalized_project_id = _text(project_id) or DEFAULT_PROJECT_ID
    normalized_repo = _normalize_repo(config, repo)
    selected_autonomy_profile = _text(autonomy_profile) or DEFAULT_AUTONOMY_PROFILE
    effective_dry_run = bool(dry_run) or not bool(github_enabled)
    generated_at = _now_iso()
    queue_path_resolved = resolve_project_queue_path(config.repo_root, queue_path)

    branch_plan_payload = _payload(
        plan_pr_draft_branch(
            config,
            item_id=normalized_item_id,
            project_id=normalized_project_id,
            queue_path=queue_path,
            registry_path=registry_path,
            run_id=run_id,
            dry_run=True,
            github_enabled=False,
            autonomy_profile=selected_autonomy_profile,
            repo=normalized_repo,
            base_branch=base_branch,
            branch_prefix=branch_prefix,
            evidence_bundle=evidence_bundle,
            output_format="json",
        )
    )
    item_project_id = _text(branch_plan_payload.get("project_id")) or normalized_project_id
    branch_plan = branch_plan_payload.get("branch_plan") if isinstance(branch_plan_payload.get("branch_plan"), dict) else {}
    expected_pr = branch_plan_payload.get("expected_pr") if isinstance(branch_plan_payload.get("expected_pr"), dict) else {}
    issue_number = _int_or_none(branch_plan_payload.get("issue_number"))
    issue_url = _text(branch_plan_payload.get("issue_url"))
    head_branch = _text(expected_pr.get("head_branch")) or _text(branch_plan.get("branch_name"))
    selected_base_branch = _text(expected_pr.get("base_branch")) or _text(branch_plan.get("base_branch")) or _text(base_branch) or "main"
    branch_exists = _branch_exists(config.repo_root, head_branch)
    branch_safe_for_live = branch_exists or bool(safe_branch_creation_enabled)
    branch_plan_approved = bool(approved_branch_plan) or _approved_from_queue(config, queue_path_resolved, normalized_item_id)

    registry_payload = _payload(
        inspect_github_link_registry(
            config,
            project_id=item_project_id,
            item_id=normalized_item_id,
            registry_path=registry_path,
            queue_item_id=normalized_item_id,
            repository=normalized_repo,
            output_format="json",
        )
    )
    registry_duplicate = _registry_pr_duplicate(registry_payload)
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

    idempotency_key = _idempotency_key(
        project_id=item_project_id,
        item_id=normalized_item_id,
        repository=normalized_repo,
        base_branch=selected_base_branch,
        head_branch=head_branch,
    )
    preflight_path: Path | None = None
    if not effective_dry_run and github_enabled:
        preflight_path = _write_preflight_record(
            config=config,
            item_id=normalized_item_id,
            project_id=item_project_id,
            repo=normalized_repo,
            issue_number=issue_number,
            issue_url=issue_url,
            title=_text(expected_pr.get("title")),
            base_branch=selected_base_branch,
            head_branch=head_branch,
            autonomy_profile=selected_autonomy_profile,
            idempotency_key=idempotency_key,
            branch_plan_approved=branch_plan_approved,
            branch_exists=branch_exists,
            safe_branch_creation_enabled=bool(safe_branch_creation_enabled),
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

    blocked_reasons = _blocked_reasons(
        branch_plan_payload=branch_plan_payload,
        registry_payload=registry_payload,
        registry_duplicate=registry_duplicate,
        autonomy_payload=autonomy_payload,
        gate_payload=gate_payload,
        dry_run=effective_dry_run,
        github_enabled=bool(github_enabled),
        autonomy_profile=selected_autonomy_profile,
        repo=normalized_repo,
        branch_plan_approved=branch_plan_approved,
        branch_safe_for_live=branch_safe_for_live,
        head_branch=head_branch,
        base_branch=selected_base_branch,
    )
    warnings = _dedupe(
        [
            *_list(branch_plan_payload.get("warnings")),
            *_list(registry_payload.get("warnings")),
            *_list(autonomy_payload.get("warnings")),
            *_list(gate_payload.get("warnings")),
            *_branch_warnings(head_branch=head_branch, branch_exists=branch_exists, dry_run=effective_dry_run),
        ]
    )

    github_execution_performed = False
    pr_created = False
    created_pr: dict[str, Any] = {}
    operation_error = ""
    registry_record: dict[str, Any] = {}
    registry_mutation_performed = False
    if not blocked_reasons and not effective_dry_run:
        client = github_client or GhCliGitHubPrDraftClient()
        try:
            created_pr = client.create_draft_pr(
                repo=normalized_repo,
                title=_text(expected_pr.get("title")),
                body=_text(expected_pr.get("body")),
                base_branch=selected_base_branch,
                head_branch=head_branch,
            )
            github_execution_performed = True
            pr_created = True
            pr_number = _pr_number(created_pr)
            pr_url = _pr_url(created_pr)
            registry_result = record_github_link(
                config,
                project_id=item_project_id,
                item_id=normalized_item_id,
                registry_path=registry_path,
                queue_item_id=normalized_item_id,
                repository=normalized_repo,
                issue_number=issue_number,
                issue_url=issue_url,
                pr_number=pr_number,
                pr_url=pr_url,
                sync_status="synced",
                last_sync_result=f"{COMMAND_NAME} created draft pull request and recorded local link.",
                linked_by="aresforge-pr-draft-gate",
                link_source=COMMAND_NAME,
                output_format="json",
            )
            registry_payload_after = _payload(registry_result)
            registry_record = registry_payload_after.get("link_record", {})
            registry_mutation_performed = bool(registry_payload_after.get("mutation_performed"))
        except (RuntimeError, OSError, subprocess.SubprocessError) as exc:
            operation_error = str(exc)
            blocked_reasons.append(f"GitHub draft PR creation failed: {exc}")

    blocked = bool(blocked_reasons)
    pr_number = _pr_number(created_pr) if pr_created and not blocked else None
    pr_url = _pr_url(created_pr) if pr_created and not blocked else ""
    status = _status(blocked=blocked, dry_run=effective_dry_run, pr_created=pr_created)
    sync_status = "blocked" if blocked else ("dry_run_ready" if effective_dry_run else "synced")
    payload: dict[str, Any] = {
        "record_type": RECORD_TYPE,
        "artifact_type": RECORD_TYPE,
        "generated": True,
        "generated_at": generated_at,
        "project_id": item_project_id,
        "item_id": normalized_item_id,
        "repository": normalized_repo,
        "repo": normalized_repo,
        "issue_number": issue_number,
        "issue_url": issue_url,
        "pr_number": pr_number,
        "pr_url": pr_url,
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
        "mutation_performed": bool(pr_created and not blocked),
        "github_pr_mutation_performed": bool(pr_created and not blocked),
        "github_branch_mutation_performed": False,
        "branch_creation_performed": False,
        "registry_mutation_performed": bool(registry_mutation_performed and not blocked),
        "queue_mutation_performed": False,
        "codex_execution_performed": False,
        "model_execution_performed": False,
        "patch_application_performed": False,
        "validation_command_execution_performed": False,
        "idempotency_key": idempotency_key,
        "recovery_available": True,
        "local_only": not bool(github_execution_performed and not blocked),
        "next_safe_action": _next_safe_action(blocked=blocked, dry_run=effective_dry_run, pr_created=pr_created),
        "artifacts_created": [str(preflight_path)] if preflight_path else [],
        "queue_path": str(queue_path_resolved),
        "registry_path": _text(registry_payload.get("registry_path")),
        "github_preflight_record_path": str(preflight_path) if preflight_path else "",
        "approved_branch_plan": bool(branch_plan_approved),
        "branch_plan_exists": bool(branch_plan_payload) and not bool(branch_plan_payload.get("blocked")),
        "branch_plan_summary": _branch_plan_summary(branch_plan_payload),
        "branch_exists": bool(branch_exists),
        "safe_branch_creation_enabled": bool(safe_branch_creation_enabled),
        "branch_safe_for_live_pr": bool(branch_safe_for_live),
        "draft_pr_creation_allowed": not blocked and not effective_dry_run,
        "pr_creation_allowed": not blocked and not effective_dry_run,
        "pull_request_created": bool(pr_created and not blocked),
        "pull_request_updated": False,
        "pull_request_merged": False,
        "auto_merge_enabled": False,
        "force_push_performed": False,
        "protected_branch_update_performed": False,
        "release_created": False,
        "workflow_mutation_performed": False,
        "issue_closure_performed": False,
        "expected_pr": expected_pr,
        "created_pr": _summarize_pr(created_pr) if pr_created and not blocked else {},
        "local_registry_record": registry_record if pr_created and not blocked else {},
        "operation_error": operation_error,
        "registry_lookup_summary": _registry_summary(registry_payload),
        "registry_duplicate_pr_blocked": bool(registry_duplicate),
        "autonomy_profile_summary": _autonomy_summary(autonomy_payload),
        "github_mutation_scope": "single_draft_pull_request_create" if not effective_dry_run else "dry_run_only",
        "github_operations_blocked": list(_GITHUB_OPERATIONS_BLOCKED),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
        "completed_at": _now_iso(),
    }
    return _emit_or_write(config=config, payload=payload, output=output, force=force)


def _blocked_reasons(
    *,
    branch_plan_payload: dict[str, Any],
    registry_payload: dict[str, Any],
    registry_duplicate: bool,
    autonomy_payload: dict[str, Any],
    gate_payload: dict[str, Any],
    dry_run: bool,
    github_enabled: bool,
    autonomy_profile: str,
    repo: str,
    branch_plan_approved: bool,
    branch_safe_for_live: bool,
    head_branch: str,
    base_branch: str,
) -> list[str]:
    reasons = [
        *_list(branch_plan_payload.get("blocked_reasons")),
        *_list(registry_payload.get("blocked_reasons")),
        *_list(gate_payload.get("blocked_reasons")),
    ]
    if bool(branch_plan_payload.get("blocked")) or _text(branch_plan_payload.get("status")) != "branch_plan_created":
        reasons.append("Approved PR draft branch plan must exist before draft PR creation can be gated.")
    if bool(registry_payload.get("blocked")):
        reasons.append("GitHub link registry lookup is blocked.")
    if not repo or "/" not in repo:
        reasons.append("Repository must use owner/name format.")
    if not head_branch:
        reasons.append("Head branch is required for draft PR creation.")
    if not base_branch:
        reasons.append("Base branch is required for draft PR creation.")
    if gate_payload.get("passed") is not True or gate_payload.get("blocked") is True:
        reasons.append("PR draft creation machine gate did not pass.")
    if not dry_run:
        if not github_enabled:
            reasons.append("Real draft PR creation requires --github-enabled.")
        if autonomy_profile != LIVE_AUTONOMY_PROFILE:
            reasons.append(f"Real draft PR creation requires autonomy_profile={LIVE_AUTONOMY_PROFILE}.")
        if not _github_pr_draft_capability_enabled(autonomy_payload):
            reasons.append("Selected autonomy profile does not enable github_pr_draft_creation.")
        if autonomy_payload.get("blocked") is True or autonomy_payload.get("machine_gates_passed") is not True:
            reasons.append("Autonomy profile inspection did not pass required machine gates.")
        if not branch_plan_approved:
            reasons.append("Real draft PR creation requires an approved branch plan.")
        if not branch_safe_for_live:
            reasons.append("Head branch must exist or --safe-branch-creation-enabled must be supplied before real draft PR creation.")
        if registry_duplicate:
            reasons.append("Local GitHub link registry already has a PR link for this queue item and repository.")
    return _dedupe(reasons)


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
    title: str,
    base_branch: str,
    head_branch: str,
    autonomy_profile: str,
    idempotency_key: str,
    branch_plan_approved: bool,
    branch_exists: bool,
    safe_branch_creation_enabled: bool,
) -> Path:
    path = config.artifact_root / "pr_draft_creation_gate" / "gates" / f"{_stamp()}-{_safe_id(item_id)}.json"
    payload = {
        "artifact_type": "pr_draft_creation_gate_preflight_v1",
        "execution_record_type": "pr_draft_creation_gate_preflight_v1",
        "item_id": item_id,
        "project_id": project_id,
        "repository": repo,
        "repo": repo,
        "issue_number": issue_number,
        "issue_url": issue_url,
        "title": title,
        "base_branch": base_branch,
        "head_branch": head_branch,
        "draft": True,
        "autonomy_profile": autonomy_profile,
        "idempotency_key": idempotency_key,
        "branch_plan_approved": branch_plan_approved,
        "branch_exists": branch_exists,
        "safe_branch_creation_enabled": safe_branch_creation_enabled,
        "local_only": True,
        "execution_allowed": False,
        "execution_performed": False,
        "external_execution_performed": False,
        "github_execution_performed": False,
        "model_execution_performed": False,
        "codex_execution_performed": False,
        "patch_application_performed": False,
        "queue_mutation_performed": False,
        "forbidden_operations": list(_GITHUB_OPERATIONS_BLOCKED),
        "validation_commands": ["python -m pytest tests/test_pr_draft_creation_gate.py"],
        "tests_reported": ["python -m pytest tests/test_pr_draft_creation_gate.py -> runnable"],
        "capabilities_used": ["read_local_branch_plan", "read_local_github_link_registry", "create_draft_pull_request"],
        "created_at": _now_iso(),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def _approved_from_queue(config: AppConfig, queue_path: Path, item_id: str) -> bool:
    try:
        raw = json.loads(queue_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return False
    for item in raw.get("work_items", []) if isinstance(raw, dict) else []:
        if isinstance(item, dict) and _text(item.get("item_id")) == item_id:
            evidence = item.get("completion_evidence") if isinstance(item.get("completion_evidence"), dict) else {}
            return bool(item.get("approved_branch_plan")) or bool(evidence.get("approved_branch_plan"))
    return False


def _branch_exists(repo_root: Path, branch_name: str) -> bool:
    if not branch_name:
        return False
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "--verify", "--quiet", f"refs/heads/{branch_name}"],
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return completed.returncode == 0


def _branch_warnings(*, head_branch: str, branch_exists: bool, dry_run: bool) -> list[str]:
    if dry_run and head_branch and not branch_exists:
        return ["Head branch does not exist locally; real draft PR creation would require an existing branch or explicit safe branch creation enablement."]
    return []


def _branch_plan_summary(payload: dict[str, Any]) -> dict[str, Any]:
    branch_plan = payload.get("branch_plan") if isinstance(payload.get("branch_plan"), dict) else {}
    return {
        "record_type": _text(payload.get("record_type")),
        "status": _text(payload.get("status")),
        "blocked": bool(payload.get("blocked")),
        "machine_gates_passed": bool(payload.get("machine_gates_passed")),
        "branch_name": _text(branch_plan.get("branch_name")),
        "base_branch": _text(branch_plan.get("base_branch")),
        "changed_file_count": payload.get("changed_file_evidence", {}).get("count")
        if isinstance(payload.get("changed_file_evidence"), dict)
        else 0,
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
        "github_pr_draft_creation_enabled": _github_pr_draft_capability_enabled(payload),
    }


def _github_pr_draft_capability_enabled(autonomy_payload: dict[str, Any]) -> bool:
    selected = autonomy_payload.get("selected_profile")
    controls = selected.get("capability_controls", []) if isinstance(selected, dict) else []
    for control in controls if isinstance(controls, list) else []:
        if isinstance(control, dict) and _text(control.get("capability_id")) == "github_pr_draft_creation":
            return _text(control.get("status")) == "enabled"
    return False


def _registry_pr_duplicate(registry_payload: dict[str, Any]) -> bool:
    for record in _dicts(registry_payload.get("records")):
        if _int(record.get("pr_number")) > 0 or _text(record.get("pr_url")):
            return True
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


def _status(*, blocked: bool, dry_run: bool, pr_created: bool) -> str:
    if blocked:
        return "blocked"
    if dry_run:
        return "dry_run_ready"
    if pr_created:
        return "draft_pr_created"
    return "not_executed"


def _next_safe_action(*, blocked: bool, dry_run: bool, pr_created: bool) -> str:
    if blocked:
        return "Resolve blocked reasons before any live draft PR creation attempt."
    if dry_run:
        return "Review branch plan approval, branch safety, registry lookup, autonomy profile, and machine gates; real draft PR creation requires explicit GitHub enablement."
    if pr_created:
        return "Review the created draft PR and local registry record; merge, auto-merge, protected branch updates, force push, and releases remain blocked."
    return "No GitHub follow-up was performed."


def _summarize_pr(value: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    keys = ("id", "number", "state", "title", "html_url", "url", "draft", "created_at", "updated_at")
    return {key: value[key] for key in keys if key in value}


def _pr_number(value: dict[str, Any]) -> int | None:
    number = _int(value.get("number"))
    if number:
        return number
    match = re.search(r"/pull/(\d+)(?:\D*)?$", _pr_url(value))
    return int(match.group(1)) if match else None


def _pr_url(value: dict[str, Any]) -> str:
    return _text(value.get("html_url") or value.get("url"))


def _last_url(value: str) -> str:
    matches = re.findall(r"https?://\S+", _text(value))
    return matches[-1].rstrip(").,") if matches else ""


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
        blocked["draft_pr_creation_allowed"] = False
        blocked["pr_creation_allowed"] = False
        blocked["pull_request_created"] = False
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


def _idempotency_key(*, project_id: str, item_id: str, repository: str, base_branch: str, head_branch: str) -> str:
    return "pr-draft-create:" + ":".join(
        [_slug(project_id), _slug(item_id), _slug(repository), _slug(base_branch), _slug(head_branch)]
    )


def _resolve(repo_root: Path, value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


def _safe_id(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in _text(value).lower())
    return cleaned.strip("-") or "pr-draft-creation"


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


def _int_or_none(value: Any) -> int | None:
    parsed = _int(value)
    return parsed or None


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
