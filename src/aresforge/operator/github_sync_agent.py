from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
import subprocess
from typing import Any, Protocol

from aresforge.config import AppConfig
from aresforge.operator.machine_safety_gate_engine import evaluate_machine_safety_gates

COMMAND_NAME = "run-github-sync-agent"
EXECUTION_RECORD_TYPE = "github_sync_agent_v1"
EXECUTION_VERSION = "m137.1"

SYNC_MODES: tuple[str, ...] = (
    "issue-comment",
    "issue-update",
    "pr-comment",
    "pr-summary",
)
COMMENT_SYNC_MODES: frozenset[str] = frozenset({"issue-comment", "pr-comment"})
SUMMARY_SYNC_MODES: frozenset[str] = frozenset({"issue-update", "pr-summary"})

FORBIDDEN_OPERATIONS: tuple[str, ...] = (
    "merge-pr",
    "enable-auto-merge",
    "delete-branch",
    "force-push",
    "approve-pr",
    "request-changes",
    "create-release",
    "update-protected-branch",
    "write-repository-files",
    "close-issue",
)

_BOUNDARY_CONFIRMATIONS = (
    "M137 GitHub sync starts with local planning and dry-run by default.",
    "Issue and PR comments require --github-enabled plus passing github_sync machine gates.",
    "Issue and PR metadata summaries write local artifacts only unless GitHub fetch is explicitly enabled.",
    "M137 never merges PRs, enables auto-merge, deletes branches, force-pushes, approves PRs, requests changes, creates releases, updates protected branches, writes repository files, or closes issues.",
)


class GitHubSyncClient(Protocol):
    def comment_issue(self, *, repo: str, issue_number: int, body: str) -> dict[str, Any]:
        ...

    def comment_pr(self, *, repo: str, pr_number: int, body: str) -> dict[str, Any]:
        ...

    def get_issue(self, *, repo: str, issue_number: int) -> dict[str, Any]:
        ...

    def get_pr(self, *, repo: str, pr_number: int) -> dict[str, Any]:
        ...


@dataclass(frozen=True)
class GhCliGitHubSyncClient:
    timeout_seconds: int = 30

    def comment_issue(self, *, repo: str, issue_number: int, body: str) -> dict[str, Any]:
        return self._run_json(
            [
                "gh",
                "api",
                f"repos/{repo}/issues/{issue_number}/comments",
                "-f",
                f"body={body}",
            ]
        )

    def comment_pr(self, *, repo: str, pr_number: int, body: str) -> dict[str, Any]:
        return self.comment_issue(repo=repo, issue_number=pr_number, body=body)

    def get_issue(self, *, repo: str, issue_number: int) -> dict[str, Any]:
        return self._run_json(["gh", "api", f"repos/{repo}/issues/{issue_number}"])

    def get_pr(self, *, repo: str, pr_number: int) -> dict[str, Any]:
        return self._run_json(["gh", "api", f"repos/{repo}/pulls/{pr_number}"])

    def _run_json(self, command: list[str]) -> dict[str, Any]:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=max(1, self.timeout_seconds),
            shell=False,
        )
        if completed.returncode != 0:
            detail = completed.stderr.strip() or completed.stdout.strip() or "gh command failed"
            raise RuntimeError(detail)
        if not completed.stdout.strip():
            return {}
        raw = json.loads(completed.stdout)
        return raw if isinstance(raw, dict) else {"value": raw}


def run_github_sync_agent(
    config: AppConfig,
    *,
    item_id: str,
    sync_mode: str = "issue-comment",
    dry_run: bool = False,
    github_enabled: bool = False,
    repo: str | None = None,
    issue_number: int | str | None = None,
    pr_number: int | str | None = None,
    artifact_path: str | Path | None = None,
    output: str | Path | None = None,
    force: bool = False,
    queue_path: str | Path | None = None,
    output_format: str = "json",
    github_client: GitHubSyncClient | None = None,
) -> dict[str, Any]:
    fmt = str(output_format or "json").strip().lower()
    if fmt != "json":
        return _error("invalid_format", {"format": output_format, "supported_formats": ["json"]})

    normalized_item_id = str(item_id or "").strip()
    normalized_mode = str(sync_mode or "").strip().lower()
    normalized_repo = _normalize_repo(config, repo)
    normalized_issue = _positive_int(issue_number)
    normalized_pr = _positive_int(pr_number)
    resolved_artifact_path = _resolve(config.repo_root, artifact_path) if artifact_path else None
    resolved_output = _resolve(config.repo_root, output) if output else None
    started_at = _now_iso()
    forbidden_requested = normalized_mode in FORBIDDEN_OPERATIONS

    preflight_path: Path | None = None
    if _needs_preflight_artifact(normalized_mode, dry_run=dry_run, github_enabled=github_enabled):
        preflight_path = _write_preflight_artifact(
            config=config,
            item_id=normalized_item_id,
            sync_mode=normalized_mode,
            repo=normalized_repo,
            issue_number=normalized_issue,
            pr_number=normalized_pr,
        )

    gate_profile = _gate_profile(normalized_mode, dry_run=dry_run, github_enabled=github_enabled)
    gate_artifact = resolved_artifact_path or preflight_path
    gate_result = evaluate_machine_safety_gates(
        config,
        item_id=normalized_item_id,
        gate_profile=gate_profile,
        artifact_path=gate_artifact,
        execution_record=gate_artifact,
        queue_path=queue_path,
        force=bool(github_enabled or force),
        output_format="json",
    )
    machine_gate = gate_result.get("payload", {}) if isinstance(gate_result, dict) else {}

    blocked_reasons = _blocked_reasons(
        sync_mode=normalized_mode,
        forbidden_requested=forbidden_requested,
        repo=normalized_repo,
        issue_number=normalized_issue,
        pr_number=normalized_pr,
        artifact_path=resolved_artifact_path,
        output=resolved_output,
        force=force,
        dry_run=dry_run,
        github_enabled=github_enabled,
        machine_gate=machine_gate,
    )

    executed = False
    github_operation_performed = False
    operation_result: dict[str, Any] = {}
    summary_artifact_path = ""
    result_summary = _planned_summary(normalized_mode, normalized_repo, normalized_issue, normalized_pr)

    if not blocked_reasons and not dry_run:
        client = github_client or GhCliGitHubSyncClient()
        try:
            if normalized_mode == "issue-comment":
                body = _comment_body(normalized_item_id, normalized_mode, resolved_artifact_path)
                operation_result = client.comment_issue(repo=normalized_repo, issue_number=normalized_issue or 0, body=body)
                executed = True
                github_operation_performed = True
                result_summary = f"Posted issue comment to {normalized_repo}#{normalized_issue}."
            elif normalized_mode == "pr-comment":
                body = _comment_body(normalized_item_id, normalized_mode, resolved_artifact_path)
                operation_result = client.comment_pr(repo=normalized_repo, pr_number=normalized_pr or 0, body=body)
                executed = True
                github_operation_performed = True
                result_summary = f"Posted PR comment to {normalized_repo}#{normalized_pr}."
            elif normalized_mode == "issue-update":
                if github_enabled:
                    operation_result = client.get_issue(repo=normalized_repo, issue_number=normalized_issue or 0)
                    github_operation_performed = True
                summary_artifact_path = str(
                    _write_summary_artifact(
                        config=config,
                        item_id=normalized_item_id,
                        summary_kind="issue_metadata_summary",
                        repo=normalized_repo,
                        number=normalized_issue or 0,
                        metadata=operation_result,
                        github_enabled=github_enabled,
                    )
                )
                executed = True
                result_summary = "Wrote local issue metadata summary artifact."
            elif normalized_mode == "pr-summary":
                if github_enabled:
                    operation_result = client.get_pr(repo=normalized_repo, pr_number=normalized_pr or 0)
                    github_operation_performed = True
                summary_artifact_path = str(
                    _write_summary_artifact(
                        config=config,
                        item_id=normalized_item_id,
                        summary_kind="pr_metadata_summary",
                        repo=normalized_repo,
                        number=normalized_pr or 0,
                        metadata=operation_result,
                        github_enabled=github_enabled,
                    )
                )
                executed = True
                result_summary = "Wrote local PR metadata summary artifact."
        except (RuntimeError, OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
            blocked_reasons.append(f"GitHub sync operation failed: {exc}")

    blocked = bool(blocked_reasons)
    artifact_path_for_record = summary_artifact_path or (str(resolved_artifact_path) if resolved_artifact_path else "")
    payload = {
        "execution_record_type": EXECUTION_RECORD_TYPE,
        "execution_version": EXECUTION_VERSION,
        "item_id": normalized_item_id,
        "dry_run": bool(dry_run),
        "github_enabled": bool(github_enabled),
        "sync_mode": normalized_mode,
        "repo": normalized_repo,
        "issue_number": normalized_issue,
        "pr_number": normalized_pr,
        "artifact_path": artifact_path_for_record,
        "machine_gates_checked": bool(machine_gate),
        "machine_gates_passed": bool(machine_gate.get("passed")) and not bool(machine_gate.get("blocked")),
        "executed": bool(executed and not blocked),
        "blocked": blocked,
        "blocked_reasons": _dedupe(blocked_reasons),
        "github_operation_performed": bool(github_operation_performed and not blocked),
        "forbidden_operations_blocked": list(FORBIDDEN_OPERATIONS),
        "result_summary": result_summary if not blocked else "GitHub sync agent blocked before execution.",
        "next_safe_action": _next_safe_action(blocked=blocked, dry_run=bool(dry_run), github_enabled=bool(github_enabled), sync_mode=normalized_mode),
        "github_sync_agent_version": EXECUTION_VERSION,
        "github_operation_result": _summarize_operation_result(operation_result) if not blocked else {},
        "machine_gate_profile": gate_profile,
        "machine_gate_result": machine_gate,
        "machine_gate_artifact_path": str(gate_artifact) if gate_artifact else "",
        "started_at": started_at,
        "completed_at": _now_iso(),
        "local_only": not bool(github_operation_performed and not blocked),
        "external_execution_performed": bool(github_operation_performed and not blocked),
        "model_execution_performed": False,
        "patch_application_performed": False,
        "queue_mutation_performed": False,
        "repository_file_write_performed": False,
        "pr_merge_performed": False,
        "auto_merge_enabled": False,
        "branch_delete_performed": False,
        "force_push_performed": False,
        "pr_review_performed": False,
        "release_created": False,
        "protected_branch_updated": False,
        "issue_closed": False,
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }
    return _emit_or_write(payload=payload, output=resolved_output, force=force)


def _blocked_reasons(
    *,
    sync_mode: str,
    forbidden_requested: bool,
    repo: str,
    issue_number: int | None,
    pr_number: int | None,
    artifact_path: Path | None,
    output: Path | None,
    force: bool,
    dry_run: bool,
    github_enabled: bool,
    machine_gate: dict[str, Any],
) -> list[str]:
    reasons: list[str] = []
    if not sync_mode:
        reasons.append("Sync mode is required.")
    elif forbidden_requested:
        reasons.append(f"Forbidden GitHub operation requested and blocked: {sync_mode}.")
    elif sync_mode not in SYNC_MODES:
        reasons.append(f"Unsupported sync mode: {sync_mode}.")
    if not repo or "/" not in repo:
        reasons.append("Repository must use owner/name format.")
    if sync_mode in {"issue-comment", "issue-update"} and not issue_number:
        reasons.append("Issue sync modes require --issue-number.")
    if sync_mode in {"pr-comment", "pr-summary"} and not pr_number:
        reasons.append("PR sync modes require --pr-number.")
    if sync_mode in COMMENT_SYNC_MODES and not github_enabled and not dry_run:
        reasons.append("GitHub comment sync is disabled by default; pass --github-enabled to allow a narrow comment operation.")
    if artifact_path and not artifact_path.exists():
        reasons.append(f"Artifact path does not exist: {artifact_path}")
    if output and output.exists() and not force:
        reasons.append("Output file already exists. Re-run with --force to overwrite.")
    if machine_gate.get("passed") is not True or machine_gate.get("blocked") is True:
        reasons.append(f"Machine safety gate profile {machine_gate.get('gate_profile', 'unknown')} did not pass.")
        reasons.extend(_list(machine_gate.get("blocked_reasons")))
    return _dedupe(reasons)


def _needs_preflight_artifact(sync_mode: str, *, dry_run: bool, github_enabled: bool) -> bool:
    if dry_run:
        return False
    if sync_mode in COMMENT_SYNC_MODES:
        return True
    return bool(github_enabled and sync_mode in SUMMARY_SYNC_MODES)


def _gate_profile(sync_mode: str, *, dry_run: bool, github_enabled: bool) -> str:
    if dry_run:
        return "read_only_agent"
    if sync_mode in COMMENT_SYNC_MODES or github_enabled:
        return "github_sync"
    return "local_artifact_write"


def _write_preflight_artifact(
    *,
    config: AppConfig,
    item_id: str,
    sync_mode: str,
    repo: str,
    issue_number: int | None,
    pr_number: int | None,
) -> Path:
    path = config.artifact_root / "github_sync_agent" / "gates" / f"{_stamp()}-{_safe_id(item_id)}-{sync_mode}.json"
    payload = {
        "artifact_type": "github_sync_agent_preflight",
        "item_id": item_id,
        "sync_mode": sync_mode,
        "repo": repo,
        "issue_number": issue_number,
        "pr_number": pr_number,
        "local_only": True,
        "execution_allowed": False,
        "execution_performed": False,
        "external_execution_performed": False,
        "github_execution_performed": False,
        "patch_application_performed": False,
        "queue_mutation_performed": False,
        "validation_commands": ["python -m pytest tests/test_github_sync_agent.py"],
        "tests_reported": ["python -m pytest tests/test_github_sync_agent.py -> runnable"],
        "capabilities_used": ["read_local_queue", "read_local_artifacts"],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def _write_summary_artifact(
    *,
    config: AppConfig,
    item_id: str,
    summary_kind: str,
    repo: str,
    number: int,
    metadata: dict[str, Any],
    github_enabled: bool,
) -> Path:
    path = config.artifact_root / "github_sync_agent" / "summaries" / f"{_stamp()}-{_safe_id(item_id)}-{summary_kind}.json"
    payload = {
        "artifact_type": summary_kind,
        "item_id": item_id,
        "repo": repo,
        "number": number,
        "github_enabled": bool(github_enabled),
        "metadata": _summarize_operation_result(metadata),
        "local_only": not bool(github_enabled),
        "github_operation_performed": bool(github_enabled),
        "repository_file_write_performed": False,
        "patch_application_performed": False,
        "queue_mutation_performed": False,
        "recorded_at": _now_iso(),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def _comment_body(item_id: str, sync_mode: str, artifact_path: Path | None) -> str:
    if artifact_path:
        try:
            if artifact_path.suffix.lower() == ".json":
                raw = json.loads(artifact_path.read_text(encoding="utf-8-sig"))
                if isinstance(raw, dict):
                    for key in ("comment_body", "body", "summary", "result_summary"):
                        text = str(raw.get(key, "") or "").strip()
                        if text:
                            return text
            text = artifact_path.read_text(encoding="utf-8-sig").strip()
            if text:
                return text
        except (OSError, json.JSONDecodeError):
            pass
    return f"AresForge M137 {sync_mode} sync note for {item_id}. Operator-enabled metadata sync only."


def _planned_summary(sync_mode: str, repo: str, issue_number: int | None, pr_number: int | None) -> str:
    if sync_mode == "issue-comment":
        return f"Dry-run plan: would post one issue comment to {repo}#{issue_number} if --github-enabled is supplied."
    if sync_mode == "pr-comment":
        return f"Dry-run plan: would post one PR comment to {repo}#{pr_number} if --github-enabled is supplied."
    if sync_mode == "issue-update":
        return f"Plan: write local issue metadata summary artifact for {repo}#{issue_number}."
    if sync_mode == "pr-summary":
        return f"Plan: write local PR metadata summary artifact for {repo}#{pr_number}."
    return "Unsupported or forbidden GitHub sync mode was requested."


def _next_safe_action(*, blocked: bool, dry_run: bool, github_enabled: bool, sync_mode: str) -> str:
    if blocked:
        return "Resolve blocked reasons before any GitHub sync operation."
    if dry_run:
        return "Review the dry-run plan; add --github-enabled only for the narrow issue/PR metadata operation you intend."
    if github_enabled and sync_mode in COMMENT_SYNC_MODES:
        return "Review the posted comment and keep all merge, review, branch, release, and issue-close actions manual."
    if sync_mode in SUMMARY_SYNC_MODES:
        return "Review the local metadata summary artifact before deciding on any separate manual GitHub action."
    return "No further automatic GitHub action is allowed in M137."


def _summarize_operation_result(value: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict) or not value:
        return {}
    keys = ("id", "number", "state", "title", "html_url", "url", "created_at", "updated_at")
    return {key: value[key] for key in keys if key in value}


def _normalize_repo(config: AppConfig, repo: str | None) -> str:
    raw = str(repo or "").strip()
    if raw:
        return raw
    return f"{config.github_owner}/{config.github_repo}"


def _positive_int(value: int | str | None) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool) and value > 0:
        return value
    text = str(value or "").strip()
    if text.isdigit() and int(text) > 0:
        return int(text)
    return None


def _emit_or_write(*, payload: dict[str, Any], output: Path | None, force: bool) -> dict[str, Any]:
    rendered = json.dumps(payload, indent=2)
    if output is None:
        return {
            "command": COMMAND_NAME,
            "ok": not bool(payload.get("blocked")),
            "local_only": not bool(payload.get("github_operation_performed")),
            "format": "json",
            "wrote_output_file": False,
            "stdout": rendered,
            "payload": payload,
        }
    if output.exists() and not force:
        blocked = dict(payload)
        blocked["blocked"] = True
        blocked["executed"] = False
        blocked["github_operation_performed"] = False
        blocked["blocked_reasons"] = _dedupe([*_list(blocked.get("blocked_reasons")), "Output file already exists. Re-run with --force to overwrite."])
        rendered = json.dumps(blocked, indent=2)
        return {
            "command": COMMAND_NAME,
            "ok": False,
            "local_only": True,
            "format": "json",
            "output": str(output),
            "force": force,
            "wrote_output_file": False,
            "stdout": rendered,
            "payload": blocked,
        }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered + "\n", encoding="utf-8")
    return {
        "command": COMMAND_NAME,
        "ok": not bool(payload.get("blocked")),
        "local_only": not bool(payload.get("github_operation_performed")),
        "format": "json",
        "output": str(output),
        "force": force,
        "wrote_output_file": True,
        "payload": payload,
    }


def _resolve(repo_root: Path, value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


def _safe_id(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in str(value or "").strip().lower())
    return cleaned.strip("-") or "github-sync"


def _stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")


def _list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(entry).strip() for entry in value if str(entry).strip()]
    if value in (None, ""):
        return []
    return [str(value).strip()]


def _dedupe(values: list[Any] | tuple[Any, ...] | Any) -> list[str]:
    deduped: list[str] = []
    for value in values:
        text = str(value).strip()
        if text and text not in deduped:
            deduped.append(text)
    return deduped


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
