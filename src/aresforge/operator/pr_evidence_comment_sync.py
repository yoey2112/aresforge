from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
import re
import subprocess
from typing import Any, Protocol

from aresforge.config import AppConfig
from aresforge.operator.github_issue_creation_real_run_gate import DEFAULT_AUTONOMY_PROFILE, LIVE_AUTONOMY_PROFILE
from aresforge.operator.github_issue_sync_plan import plan_github_issue_sync
from aresforge.operator.github_link_registry import inspect_github_link_registry, record_github_link
from aresforge.operator.local_project_queue import resolve_project_queue_path
from aresforge.operator.machine_safety_gate_engine import evaluate_machine_safety_gates
from aresforge.operator.operator_autonomy_configuration_profile import inspect_autonomy_profile
from aresforge.operator.pull_request_draft_summary_generator import generate_pr_draft_summary

COMMAND_NAME = "sync-pr-evidence-comment"
RECORD_TYPE = "pr_evidence_comment_sync_v1"
DEFAULT_PROJECT_ID = "aresforge"
DEFAULT_ITEM_ID = "m178-pr-evidence-comment-sync"
PR_EVIDENCE_COMMENT_MARKER = "<!-- aresforge:managed-pr-evidence-comment:v1 -->"

_BOUNDARY_CONFIRMATIONS: tuple[str, ...] = (
    "Dry-run is the default behavior and performs no GitHub mutation.",
    "Live PR evidence comment sync requires --github-enabled, a non-dry-run request, github_issue_sync_enabled autonomy profile, a linked PR or --pr-number, and a passing github_sync machine gate.",
    "Only one managed PR evidence comment for one pull request is created or updated per command invocation.",
    "Successful live sync stores the managed comment_id in the local GitHub link registry for idempotent future updates.",
    "No pull request merge, auto-merge, force push, protected branch update, release creation, workflow mutation, issue closure, source patch application, queue mutation, Codex execution, model execution, validation command execution, retry, resume, or next-item execution is performed.",
)


class GitHubPrEvidenceCommentClient(Protocol):
    def find_pr_evidence_comment(self, *, repo: str, pr_number: int, marker: str) -> dict[str, Any] | None:
        ...

    def create_pr_comment(self, *, repo: str, pr_number: int, body: str) -> dict[str, Any]:
        ...

    def update_comment(self, *, repo: str, comment_id: int | str, body: str) -> dict[str, Any]:
        ...


@dataclass(frozen=True)
class GhCliGitHubPrEvidenceCommentClient:
    timeout_seconds: int = 30

    def find_pr_evidence_comment(self, *, repo: str, pr_number: int, marker: str) -> dict[str, Any] | None:
        completed = subprocess.run(
            ["gh", "api", f"repos/{repo}/issues/{pr_number}/comments"],
            check=False,
            capture_output=True,
            text=True,
            timeout=max(1, self.timeout_seconds),
            shell=False,
        )
        if completed.returncode != 0:
            detail = completed.stderr.strip() or completed.stdout.strip() or "gh api issue comments lookup failed"
            raise RuntimeError(detail)
        comments = json.loads(completed.stdout or "[]")
        for comment in comments if isinstance(comments, list) else []:
            if isinstance(comment, dict) and marker in _text(comment.get("body")):
                return comment
        return None

    def create_pr_comment(self, *, repo: str, pr_number: int, body: str) -> dict[str, Any]:
        completed = subprocess.run(
            ["gh", "pr", "comment", str(pr_number), "--repo", repo, "--body", body],
            check=False,
            capture_output=True,
            text=True,
            timeout=max(1, self.timeout_seconds),
            shell=False,
        )
        if completed.returncode != 0:
            detail = completed.stderr.strip() or completed.stdout.strip() or "gh pr comment failed"
            raise RuntimeError(detail)
        url = _last_url(completed.stdout) or completed.stdout.strip()
        return {"html_url": url, "url": url}

    def update_comment(self, *, repo: str, comment_id: int | str, body: str) -> dict[str, Any]:
        completed = subprocess.run(
            ["gh", "api", "--method", "PATCH", f"repos/{repo}/issues/comments/{comment_id}", "-f", f"body={body}"],
            check=False,
            capture_output=True,
            text=True,
            timeout=max(1, self.timeout_seconds),
            shell=False,
        )
        if completed.returncode != 0:
            detail = completed.stderr.strip() or completed.stdout.strip() or "gh api comment update failed"
            raise RuntimeError(detail)
        raw = json.loads(completed.stdout or "{}")
        return raw if isinstance(raw, dict) else {"id": comment_id}


def sync_pr_evidence_comment(
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
    pr_number: int | None = None,
    evidence_bundle: str | Path | None = None,
    output: str | Path | None = None,
    force: bool = False,
    output_format: str = "json",
    github_client: GitHubPrEvidenceCommentClient | None = None,
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
    queue_result = _load_queue(queue_path_resolved)
    queue = queue_result.get("queue") if queue_result.get("ok") else {}
    item = _find_item(queue, normalized_item_id)
    item_project_id = _text(item.get("project_id")) or normalized_project_id

    issue_plan_payload = _payload(plan_github_issue_sync(config, project_id=item_project_id, item_id=normalized_item_id, queue_path=queue_path, output_format="json"))
    item_plan = _item_plan(issue_plan_payload, normalized_item_id)
    linked_issue = item_plan.get("linked_issue") if isinstance(item_plan.get("linked_issue"), dict) else {}
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
    registry_record = _first_record(registry_payload)
    effective_issue_number = _int(issue_number) or _int(registry_record.get("issue_number")) or _int(linked_issue.get("issue_number"))
    effective_issue_url = _text(registry_record.get("issue_url")) or _text(linked_issue.get("issue_url"))
    effective_pr_number = _int(pr_number) or _int(registry_record.get("pr_number"))
    effective_pr_url = _text(registry_record.get("pr_url")) or _pr_url_from_number(normalized_repo, effective_pr_number)
    registry_comment_id = _text(registry_record.get("comment_id"))

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
    changed_files = _changed_files(config=config, item=item, draft_payload=draft_payload)
    tests = _list(draft_payload.get("tests")) or _list(item.get("tests_run"))
    smoke_checks = _list(draft_payload.get("smoke_checks")) or _smoke_checks(item)
    risks = _risk_classification(item=item, draft_payload=draft_payload)
    blockers = _remaining_blockers(item=item, draft_payload=draft_payload)
    comment_body = _comment_body(
        item=item,
        item_id=normalized_item_id,
        generated_at=generated_at,
        validation_bundle=_validation_bundle_summary(config=config, item_id=normalized_item_id, explicit_path=evidence_bundle, draft_payload=draft_payload),
        changed_files=changed_files,
        tests=tests,
        smoke_checks=smoke_checks,
        risk=risks,
        linked_issue={"issue_number": effective_issue_number or None, "issue_url": effective_issue_url},
        blockers=blockers,
        next_safe_action="Review the dry-run PR evidence comment; live sync requires explicit GitHub enablement and passing machine gates.",
    )
    idempotency_key = _idempotency_key(project_id=item_project_id, item_id=normalized_item_id, repository=normalized_repo, pr_number=effective_pr_number)
    preflight_path: Path | None = None
    if not effective_dry_run and github_enabled:
        preflight_path = _write_preflight_record(
            config=config,
            project_id=item_project_id,
            item_id=normalized_item_id,
            repository=normalized_repo,
            issue_number=effective_issue_number,
            pr_number=effective_pr_number,
            autonomy_profile=selected_autonomy_profile,
            idempotency_key=idempotency_key,
            comment_body=comment_body,
        )
    gate_payload = _gate_payload(config, item_id=normalized_item_id, queue_path=queue_path, dry_run=effective_dry_run, github_enabled=bool(github_enabled), preflight_path=preflight_path)
    gate_summary = _gate_summary(gate_payload, default_profile="read_only_agent" if effective_dry_run else "github_sync")

    blocked_reasons = _blocked_reasons(
        queue_result=queue_result,
        item=item,
        item_plan=item_plan,
        issue_plan_payload=issue_plan_payload,
        registry_payload=registry_payload,
        draft_payload=draft_payload,
        autonomy_payload=autonomy_payload,
        gate_payload=gate_payload,
        repo=normalized_repo,
        pr_number=effective_pr_number,
        dry_run=effective_dry_run,
        github_enabled=bool(github_enabled),
        autonomy_profile=selected_autonomy_profile,
    )
    warnings = _dedupe(
        [
            *queue_result.get("warnings", []),
            *_list(issue_plan_payload.get("warnings")),
            *_list(item_plan.get("warnings")),
            *_list(registry_payload.get("warnings")),
            *_list(draft_payload.get("warnings")),
            *_list(autonomy_payload.get("warnings")),
            *_list(gate_payload.get("warnings")),
            *_dry_run_warnings(effective_pr_number=effective_pr_number, dry_run=effective_dry_run),
        ]
    )

    github_execution_performed = False
    comment_synced = False
    registry_mutation_performed = False
    operation = "dry_run" if effective_dry_run else "blocked"
    existing_comment: dict[str, Any] = {}
    synced_comment: dict[str, Any] = {}
    local_registry_record: dict[str, Any] = {}
    operation_error = ""
    if not blocked_reasons and not effective_dry_run:
        client = github_client or GhCliGitHubPrEvidenceCommentClient()
        try:
            if registry_comment_id:
                synced_comment = client.update_comment(repo=normalized_repo, comment_id=registry_comment_id, body=comment_body)
                operation = "update_by_registry_comment_id"
            else:
                existing_comment = client.find_pr_evidence_comment(repo=normalized_repo, pr_number=effective_pr_number, marker=PR_EVIDENCE_COMMENT_MARKER) or {}
                if existing_comment:
                    synced_comment = client.update_comment(repo=normalized_repo, comment_id=existing_comment.get("id"), body=comment_body)
                    operation = "update_by_marker"
                else:
                    synced_comment = client.create_pr_comment(repo=normalized_repo, pr_number=effective_pr_number, body=comment_body)
                    operation = "create"
            github_execution_performed = True
            comment_synced = True
            comment_id = _comment_id(synced_comment, fallback=registry_comment_id or existing_comment.get("id"))
            comment_url = _text(synced_comment.get("html_url") or synced_comment.get("url") or existing_comment.get("html_url"))
            registry_result = record_github_link(
                config,
                project_id=item_project_id,
                item_id=normalized_item_id,
                registry_path=registry_path,
                queue_item_id=normalized_item_id,
                repository=normalized_repo,
                issue_number=effective_issue_number or None,
                issue_url=effective_issue_url,
                pr_number=effective_pr_number,
                pr_url=effective_pr_url,
                comment_id=comment_id,
                comment_url=comment_url,
                sync_status="status_comment_synced",
                last_sync_result=f"{COMMAND_NAME} {operation}.",
                linked_by="aresforge-pr-evidence-comment-sync",
                link_source=COMMAND_NAME,
                output_format="json",
            )
            registry_payload_after = _payload(registry_result)
            local_registry_record = registry_payload_after.get("link_record", {})
            registry_mutation_performed = bool(registry_payload_after.get("mutation_performed"))
        except (RuntimeError, OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
            operation_error = str(exc)
            blocked_reasons.append(f"PR evidence comment sync failed: {exc}")

    blocked = bool(blocked_reasons)
    payload: dict[str, Any] = {
        "record_type": RECORD_TYPE,
        "artifact_type": RECORD_TYPE,
        "generated": True,
        "generated_at": generated_at,
        "project_id": item_project_id,
        "item_id": normalized_item_id,
        "repository": normalized_repo,
        "repo": normalized_repo,
        "issue_number": effective_issue_number or None,
        "issue_url": effective_issue_url,
        "pr_number": effective_pr_number or None,
        "pr_url": effective_pr_url,
        "sync_status": "blocked" if blocked else ("dry_run_ready" if effective_dry_run else "pr_evidence_comment_synced"),
        "status": "blocked" if blocked else ("dry_run_ready" if effective_dry_run else "pr_evidence_comment_synced"),
        "blocked": blocked,
        "blocked_reasons": _dedupe(blocked_reasons),
        "warnings": warnings,
        "machine_gates_checked": [gate_summary],
        "machine_gates_passed": bool(gate_summary.get("passed")) and not blocked,
        "autonomy_profile": selected_autonomy_profile,
        "dry_run": bool(effective_dry_run),
        "github_enabled": bool(github_enabled),
        "github_execution_performed": bool(github_execution_performed and not blocked),
        "mutation_performed": bool(comment_synced and not blocked),
        "pr_evidence_comment_mutation_performed": bool(comment_synced and not blocked),
        "registry_mutation_performed": bool(registry_mutation_performed and not blocked),
        "queue_mutation_performed": False,
        "codex_execution_performed": False,
        "model_execution_performed": False,
        "patch_application_performed": False,
        "validation_command_execution_performed": False,
        "idempotency_key": idempotency_key,
        "recovery_available": True,
        "local_only": not bool(github_execution_performed and not blocked),
        "next_safe_action": _next_safe_action(blocked=blocked, dry_run=effective_dry_run, synced=comment_synced),
        "artifacts_created": [str(preflight_path)] if preflight_path else [],
        "github_preflight_record_path": str(preflight_path) if preflight_path else "",
        "queue_path": str(queue_path_resolved),
        "registry_path": _text(registry_payload.get("registry_path")),
        "queue_item_found": bool(item),
        "queue_status": _text(item.get("status")),
        "validation_bundle": _validation_bundle_summary(config=config, item_id=normalized_item_id, explicit_path=evidence_bundle, draft_payload=draft_payload),
        "changed_files": changed_files,
        "tests": tests,
        "smoke_checks": smoke_checks,
        "risk_classification": risks,
        "linked_issues": [{"issue_number": effective_issue_number or None, "issue_url": effective_issue_url}] if (effective_issue_number or effective_issue_url) else [],
        "remaining_blockers": blockers,
        "machine_gate_status": gate_summary,
        "registry_lookup_summary": _registry_summary(registry_payload, registry_record),
        "source_plan_summary": _source_plan_summary(issue_plan_payload, item_plan),
        "draft_summary_source": _draft_summary_source(draft_payload),
        "autonomy_profile_summary": _autonomy_summary(autonomy_payload),
        "pr_evidence_comment_marker": PR_EVIDENCE_COMMENT_MARKER,
        "pr_evidence_comment_body": comment_body,
        "pr_evidence_comment_sync_allowed": not blocked and not effective_dry_run,
        "pr_evidence_comment_synced": bool(comment_synced and not blocked),
        "pr_evidence_comment_operation": operation if comment_synced and not blocked else ("dry_run" if effective_dry_run else "blocked"),
        "managed_comment_id": _comment_id(synced_comment, fallback=registry_comment_id) if comment_synced and not blocked else registry_comment_id,
        "existing_pr_evidence_comment": _summarize_comment(existing_comment),
        "synced_pr_evidence_comment": _summarize_comment(synced_comment) if comment_synced and not blocked else {},
        "local_registry_record": local_registry_record,
        "operation_error": operation_error,
        "github_mutation_scope": "single_pr_managed_evidence_comment_create_or_update",
        "github_operations_blocked": [
            "merge_pull_request",
            "enable_auto_merge",
            "force_push",
            "update_protected_branch",
            "create_release",
            "modify_github_workflow",
            "close_issue",
            "source_code_patch",
            "queue_status_mutation",
        ],
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
        "completed_at": _now_iso(),
    }
    return _emit_or_write(config=config, payload=payload, output=output, force=force)


def _comment_body(
    *,
    item: dict[str, Any],
    item_id: str,
    generated_at: str,
    validation_bundle: dict[str, Any],
    changed_files: list[str],
    tests: list[str],
    smoke_checks: list[str],
    risk: dict[str, Any],
    linked_issue: dict[str, Any],
    blockers: list[str],
    next_safe_action: str,
) -> str:
    issue_number = _text(linked_issue.get("issue_number"))
    issue_url = _text(linked_issue.get("issue_url"))
    lines = [
        PR_EVIDENCE_COMMENT_MARKER,
        f"# AresForge PR Evidence: {_text(item.get('title')) or item_id}",
        "",
        f"Generated: {generated_at}",
        f"Queue item: {item_id}",
        f"Queue status: {_text(item.get('status')) or 'unknown'}",
        "",
        "## Validation Bundle",
        f"- Present: {bool(validation_bundle.get('found'))}",
        f"- Source: {_text(validation_bundle.get('source_path')) or 'not found'}",
        f"- Status: {_text(validation_bundle.get('status')) or 'unknown'}",
        f"- Summary: {_text(item.get('validation_summary')) or 'No validation summary recorded.'}",
        "",
        "## Changed Files",
        *_bullets(changed_files),
        "",
        "## Tests",
        *_bullets(tests),
        "",
        "## Smoke Checks",
        *_bullets(smoke_checks),
        "",
        "## Risk Classification",
        f"- Level: {risk.get('level')}",
        *_bullets(risk.get("reasons")),
        "",
        "## Linked Issues",
        *_bullets([f"#{issue_number} {issue_url}".strip()] if issue_number or issue_url else []),
        "",
        "## Blockers",
        *_bullets(blockers),
        "",
        "## Next Safe Action",
        next_safe_action,
    ]
    return "\n".join(lines)


def _blocked_reasons(
    *,
    queue_result: dict[str, Any],
    item: dict[str, Any],
    item_plan: dict[str, Any],
    issue_plan_payload: dict[str, Any],
    registry_payload: dict[str, Any],
    draft_payload: dict[str, Any],
    autonomy_payload: dict[str, Any],
    gate_payload: dict[str, Any],
    repo: str,
    pr_number: int,
    dry_run: bool,
    github_enabled: bool,
    autonomy_profile: str,
) -> list[str]:
    reasons = [*queue_result.get("blocked_reasons", [])]
    if not queue_result.get("ok"):
        reasons.append("Local queue must be readable before PR evidence comment sync can be considered.")
    if not item:
        reasons.append("Queue item must exist before PR evidence comment sync can be considered.")
    if item and _list(item.get("blocked_by")):
        reasons.append("Queue item has blocked_by entries.")
    if not item_plan:
        reasons.append("Queue item was not present in the GitHub issue sync plan.")
    if bool(item_plan.get("blocked")):
        reasons.extend(_list(item_plan.get("blocked_reasons")))
    if bool(issue_plan_payload.get("blocked")):
        reasons.extend(_list(issue_plan_payload.get("blocked_reasons")))
    if bool(registry_payload.get("blocked")):
        reasons.append("GitHub link registry lookup is blocked.")
        reasons.extend(_list(registry_payload.get("blocked_reasons")))
    if bool(draft_payload.get("blocked")) and not dry_run:
        reasons.append("PR draft summary source is blocked.")
        reasons.extend(_list(draft_payload.get("blocked_reasons")))
    if not repo or "/" not in repo:
        reasons.append("Repository must use owner/name format.")
    if not dry_run:
        if not github_enabled:
            reasons.append("Live PR evidence comment sync requires --github-enabled.")
        if pr_number <= 0:
            reasons.append("Live PR evidence comment sync requires a local registry PR link or --pr-number.")
        if autonomy_profile != LIVE_AUTONOMY_PROFILE:
            reasons.append(f"Live PR evidence comment sync requires autonomy_profile={LIVE_AUTONOMY_PROFILE}.")
        if not _github_issue_sync_capability_enabled(autonomy_payload):
            reasons.append("Selected autonomy profile does not enable github_issue_sync.")
        if autonomy_payload.get("blocked") is True or autonomy_payload.get("machine_gates_passed") is not True:
            reasons.append("Autonomy profile inspection did not pass required machine gates.")
        if gate_payload.get("passed") is not True or gate_payload.get("blocked") is True:
            reasons.append("PR evidence comment sync machine gate did not pass.")
            reasons.extend(_list(gate_payload.get("blocked_reasons")))
    elif gate_payload.get("passed") is not True or gate_payload.get("blocked") is True:
        reasons.append("Dry-run read-only machine gate did not pass.")
        reasons.extend(_list(gate_payload.get("blocked_reasons")))
    return _dedupe(reasons)


def _write_preflight_record(
    *,
    config: AppConfig,
    project_id: str,
    item_id: str,
    repository: str,
    issue_number: int,
    pr_number: int,
    autonomy_profile: str,
    idempotency_key: str,
    comment_body: str,
) -> Path:
    path = config.artifact_root / "pr_evidence_comment_sync" / "gates" / f"{_stamp()}-{_slug(item_id)}.json"
    payload = {
        "artifact_type": "pr_evidence_comment_sync_preflight_v1",
        "execution_record_type": "pr_evidence_comment_sync_preflight_v1",
        "project_id": project_id,
        "item_id": item_id,
        "repository": repository,
        "issue_number": issue_number or None,
        "pr_number": pr_number or None,
        "comment_marker": PR_EVIDENCE_COMMENT_MARKER,
        "comment_body_sha_hint": str(len(comment_body)),
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
        "validation_commands": ["python -m pytest tests/test_pr_evidence_comment_sync.py"],
        "tests_reported": ["python -m pytest tests/test_pr_evidence_comment_sync.py -> runnable"],
        "capabilities_used": ["read_local_queue", "read_local_pr_summary", "read_local_github_link_registry", "sync_pr_comment"],
        "created_at": _now_iso(),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def _gate_payload(config: AppConfig, *, item_id: str, queue_path: str | Path | None, dry_run: bool, github_enabled: bool, preflight_path: Path | None) -> dict[str, Any]:
    if dry_run:
        result = evaluate_machine_safety_gates(config, item_id=item_id, gate_profile="read_only_agent", queue_path=queue_path, output_format="json")
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


def _gate_summary(gate_payload: dict[str, Any], *, default_profile: str) -> dict[str, Any]:
    checks = gate_payload.get("checks", [])
    failed = [_text(check.get("check_id")) for check in checks if isinstance(check, dict) and not bool(check.get("passed")) and not bool(check.get("warning_only"))]
    return {
        "gate_profile": _text(gate_payload.get("gate_profile")) or default_profile,
        "passed": bool(gate_payload.get("passed")) and not bool(gate_payload.get("blocked")),
        "blocked": bool(gate_payload.get("blocked")),
        "blocked_reasons": _list(gate_payload.get("blocked_reasons")),
        "checks_failed": failed,
    }


def _validation_bundle_summary(*, config: AppConfig, item_id: str, explicit_path: str | Path | None, draft_payload: dict[str, Any]) -> dict[str, Any]:
    draft_bundle = draft_payload.get("codex_evidence_bundle") if isinstance(draft_payload.get("codex_evidence_bundle"), dict) else {}
    path = _resolve(config.repo_root, explicit_path) if explicit_path else _latest_evidence_bundle(config, item_id)
    return {
        "found": bool(path and path.exists()) or bool(draft_bundle.get("found")),
        "source_path": str(path) if path else _text(draft_bundle.get("source_path")),
        "record_type": _text(draft_bundle.get("record_type")),
        "status": _text(draft_bundle.get("status")),
        "artifacts_created": _list(draft_bundle.get("artifacts_created")),
    }


def _latest_evidence_bundle(config: AppConfig, item_id: str) -> Path | None:
    root = config.repo_root / ".aresforge" / "codex_loop_validation_evidence" / _safe_id(item_id)
    if not root.exists():
        return None
    direct = root / "bundle.json"
    if direct.exists():
        return direct
    candidates = sorted(root.glob("*/codex-loop-validation-evidence-bundle.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    return candidates[0] if candidates else None


def _changed_files(*, config: AppConfig, item: dict[str, Any], draft_payload: dict[str, Any]) -> list[str]:
    return _dedupe(path.replace("\\", "/") for path in [*_list(item.get("changed_files")), *_list(draft_payload.get("changed_files")), *_git_diff_files(config.repo_root)])


def _smoke_checks(item: dict[str, Any]) -> list[str]:
    tests = _list(item.get("tests_run"))
    return _dedupe(entry for entry in tests if "aresforge" in entry and "pytest" not in entry)


def _risk_classification(*, item: dict[str, Any], draft_payload: dict[str, Any]) -> dict[str, Any]:
    risks = _dedupe([*_list(item.get("risk_notes")), *_list(draft_payload.get("risks"))])
    blockers = _remaining_blockers(item=item, draft_payload=draft_payload)
    level = "blocked" if blockers else ("medium" if risks else "low")
    return {"level": level, "reasons": risks or ["No additional PR evidence sync risks recorded beyond gated GitHub comment mutation."]}


def _remaining_blockers(*, item: dict[str, Any], draft_payload: dict[str, Any]) -> list[str]:
    blockers = _dedupe([*_list(item.get("blocked_by")), *_list(draft_payload.get("remaining_blockers"))])
    return blockers


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


def _github_issue_sync_capability_enabled(autonomy_payload: dict[str, Any]) -> bool:
    selected = autonomy_payload.get("selected_profile")
    controls = selected.get("capability_controls", []) if isinstance(selected, dict) else []
    for control in controls if isinstance(controls, list) else []:
        if isinstance(control, dict) and _text(control.get("capability_id")) == "github_issue_sync":
            return _text(control.get("status")) == "enabled"
    return False


def _registry_summary(registry_payload: dict[str, Any], registry_record: dict[str, Any]) -> dict[str, Any]:
    return {
        "record_type": _text(registry_payload.get("record_type")),
        "status": _text(registry_payload.get("status")),
        "blocked": bool(registry_payload.get("blocked")),
        "blocked_reasons": _list(registry_payload.get("blocked_reasons")),
        "matched_record_count": _int(registry_payload.get("matched_record_count")),
        "registry_path": _text(registry_payload.get("registry_path")),
        "comment_id": _text(registry_record.get("comment_id")),
        "pr_number": _int(registry_record.get("pr_number")) or None,
    }


def _first_record(registry_payload: dict[str, Any]) -> dict[str, Any]:
    records = registry_payload.get("records")
    if isinstance(records, list) and records and isinstance(records[0], dict):
        return records[0]
    return {}


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
    for item in items if isinstance(items, list) else []:
        if isinstance(item, dict) and _text(item.get("item_id")) == item_id:
            return item
    return {}


def _item_plan(plan_payload: dict[str, Any], item_id: str) -> dict[str, Any]:
    for entry in plan_payload.get("issue_sync_items", []):
        if isinstance(entry, dict) and _text(entry.get("item_id")) == item_id:
            return entry
    return {}


def _git_diff_files(repo_root: Path) -> list[str]:
    try:
        completed = subprocess.run(["git", "diff", "--name-only", "HEAD"], cwd=repo_root, check=False, capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return []
    if completed.returncode != 0:
        return []
    return _dedupe(line.strip().replace("\\", "/") for line in completed.stdout.splitlines() if line.strip())


def _emit_or_write(*, config: AppConfig, payload: dict[str, Any], output: str | Path | None, force: bool) -> dict[str, Any]:
    if output is None:
        return {"command": COMMAND_NAME, "ok": not bool(payload.get("blocked")), "local_only": bool(payload.get("local_only")), "format": "json", "wrote_output_file": False, "stdout": json.dumps(payload, indent=2), "payload": payload}
    output_path = _resolve(config.repo_root, output)
    if output_path.exists() and not force:
        blocked = dict(payload)
        blocked["status"] = "blocked"
        blocked["sync_status"] = "blocked"
        blocked["blocked"] = True
        blocked["blocked_reasons"] = _dedupe([*_list(blocked.get("blocked_reasons")), "Output file already exists. Re-run with --force to overwrite."])
        blocked["pr_evidence_comment_sync_allowed"] = False
        blocked["pr_evidence_comment_synced"] = False
        blocked["github_execution_performed"] = False
        blocked["mutation_performed"] = False
        return {"command": COMMAND_NAME, "ok": False, "local_only": True, "format": "json", "output": str(output_path), "force": force, "wrote_output_file": False, "stdout": json.dumps(blocked, indent=2), "payload": blocked}
    artifact_payload = dict(payload)
    artifact_payload["artifacts_created"] = _dedupe([*_list(payload.get("artifacts_created")), str(output_path)])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact_payload, indent=2) + "\n", encoding="utf-8")
    return {"command": COMMAND_NAME, "ok": not bool(artifact_payload.get("blocked")), "local_only": bool(artifact_payload.get("local_only")), "format": "json", "output": str(output_path), "force": force, "wrote_output_file": True, "payload": artifact_payload}


def _next_safe_action(*, blocked: bool, dry_run: bool, synced: bool) -> str:
    if blocked:
        return "Resolve blocked reasons before any live PR evidence comment sync attempt."
    if dry_run:
        return "Review the generated PR evidence comment; live sync requires --github-enabled with autonomy_profile=github_issue_sync_enabled and a linked PR."
    if synced:
        return "Review the synced PR evidence comment and durable registry comment_id before any separate gated follow-up."
    return "No GitHub follow-up was performed."


def _dry_run_warnings(*, effective_pr_number: int, dry_run: bool) -> list[str]:
    if dry_run and effective_pr_number <= 0:
        return ["No PR number found; dry-run generated a reviewable comment body, but live sync would require a local registry PR link or --pr-number."]
    return []


def _pr_url_from_number(repo: str, pr_number: int) -> str:
    return f"https://github.com/{repo}/pull/{pr_number}" if pr_number > 0 and "/" in repo else ""


def _comment_id(value: dict[str, Any], *, fallback: Any = "") -> str:
    return _text(value.get("id") or fallback)


def _summarize_comment(value: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {key: value[key] for key in ("id", "node_id", "html_url", "url", "created_at", "updated_at") if key in value}


def _normalize_repo(config: AppConfig, repo: str | None) -> str:
    return _text(repo) or f"{config.github_owner}/{config.github_repo}"


def _idempotency_key(*, project_id: str, item_id: str, repository: str, pr_number: int) -> str:
    return "pr-evidence-comment:" + ":".join([_slug(project_id), _slug(item_id), _slug(repository), f"pr-{pr_number or 'unlinked'}"])


def _last_url(value: str) -> str:
    matches = re.findall(r"https?://\S+", _text(value))
    return matches[-1].rstrip(").,") if matches else ""


def _resolve(repo_root: Path, value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


def _bullets(values: Any) -> list[str]:
    entries = _list(values)
    return [f"- {entry}" for entry in entries] if entries else ["- None recorded."]


def _payload(result: dict[str, Any]) -> dict[str, Any]:
    payload = result.get("payload", {}) if isinstance(result, dict) else {}
    return payload if isinstance(payload, dict) else {}


def _safe_id(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in _text(value).lower())
    return cleaned.strip("-") or "pr-evidence-comment"


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", _text(value).lower()).strip("-") or "unknown"


def _stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")


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
    return {"command": COMMAND_NAME, "ok": False, "local_only": True, "error": error, "details": details}
