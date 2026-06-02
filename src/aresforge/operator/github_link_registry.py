from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.machine_safety_gate_engine import evaluate_machine_safety_gates

COMMAND_INSPECT = "inspect-github-link-registry"
COMMAND_RECORD = "record-github-link"
RECORD_TYPE = "github_link_registry_for_queue_items_v1"
LINK_RECORD_TYPE = "github_link_registry_record_v1"
DEFAULT_PROJECT_ID = "aresforge"
DEFAULT_ITEM_ID = "m170-github-link-registry-for-queue-items"
DEFAULT_REGISTRY_RELATIVE = Path(".aresforge") / "github_link_registry" / "links.json"

SYNC_STATUSES: frozenset[str] = frozenset(
    {
        "unknown",
        "linked",
        "planned",
        "dry_run",
        "synced",
        "blocked",
        "stale",
    }
)

_BOUNDARY_CONFIRMATIONS: tuple[str, ...] = (
    "Durable local GitHub link registry only.",
    "Queue-item-to-issue and queue-item-to-PR links are stored as local metadata.",
    "Inspect and lookup operations do not mutate GitHub.",
    "Record add/update mutates only the local registry file.",
    "No gh command, GitHub API call, issue or PR mutation, merge, auto-merge, force push, protected branch update, release, workflow mutation, Codex execution, model execution, source patch application, queue mutation, retry, resume, or next-item execution is performed.",
)


def inspect_github_link_registry(
    config: AppConfig,
    *,
    project_id: str = DEFAULT_PROJECT_ID,
    item_id: str = DEFAULT_ITEM_ID,
    registry_path: str | Path | None = None,
    queue_item_id: str | None = None,
    repository: str | None = None,
    issue_number: int | None = None,
    pr_number: int | None = None,
    output_format: str = "json",
) -> dict[str, Any]:
    fmt = _text(output_format).lower() or "json"
    if fmt != "json":
        return _error(COMMAND_INSPECT, "invalid_format", {"format": output_format, "supported_formats": ["json"]})

    normalized_project_id = _text(project_id) or DEFAULT_PROJECT_ID
    normalized_item_id = _text(item_id) or DEFAULT_ITEM_ID
    resolved_path = resolve_github_link_registry_path(config.repo_root, registry_path)
    load_result = _load_registry(resolved_path)
    registry = load_result.get("registry") if load_result.get("ok") else _default_registry()
    records = _records(registry)
    filtered = _filter_records(
        records,
        project_id=normalized_project_id,
        queue_item_id=queue_item_id,
        repository=repository,
        issue_number=issue_number,
        pr_number=pr_number,
    )

    gate_payload = _gate_payload(config, item_id=normalized_item_id)
    gate_summary = _gate_summary(gate_payload)
    blocked_reasons = _dedupe([*load_result.get("blocked_reasons", []), *_list(gate_payload.get("blocked_reasons"))])
    warnings = _dedupe([*load_result.get("warnings", []), *_registry_warnings(records), *_list(gate_payload.get("warnings"))])
    blocked = bool(blocked_reasons)

    payload = {
        "record_type": RECORD_TYPE,
        "artifact_type": RECORD_TYPE,
        "generated": True,
        "generated_at": _now_iso(),
        "project_id": normalized_project_id,
        "item_id": normalized_item_id,
        "repository": _text(repository) or "",
        "issue_number": issue_number,
        "issue_url": "",
        "pr_number": pr_number,
        "pr_url": "",
        "sync_status": "blocked" if blocked else "registry_ready",
        "status": "blocked" if blocked else "registry_ready",
        "blocked": blocked,
        "blocked_reasons": blocked_reasons,
        "warnings": warnings,
        "machine_gates_checked": [gate_summary],
        "machine_gates_passed": bool(gate_summary.get("passed")) and not blocked,
        "autonomy_profile": "github_sync_dry_run",
        "dry_run": True,
        "github_enabled": False,
        "github_execution_performed": False,
        "mutation_performed": False,
        "queue_mutation_performed": False,
        "codex_execution_performed": False,
        "model_execution_performed": False,
        "patch_application_performed": False,
        "recovery_available": True,
        "local_only": True,
        "next_safe_action": _next_safe_action(blocked=blocked, filtered=filtered),
        "registry_path": str(resolved_path),
        "registry_exists": bool(resolved_path.exists()),
        "schema_version": _text(registry.get("schema_version")) or "1.0",
        "updated_at": _text(registry.get("updated_at")),
        "record_count": len(records),
        "matched_record_count": len(filtered),
        "lookup": {
            "queue_item_id": _text(queue_item_id),
            "repository": _text(repository),
            "issue_number": issue_number,
            "pr_number": pr_number,
        },
        "records": filtered,
        "records_by_queue_item": {record["queue_item_id"]: record for record in filtered},
        "idempotency_key": _inspect_idempotency_key(
            project_id=normalized_project_id,
            queue_item_id=queue_item_id,
            repository=repository,
            issue_number=issue_number,
            pr_number=pr_number,
        ),
        "github_operations_blocked": [
            "create_issue",
            "update_issue",
            "close_issue",
            "create_pull_request",
            "update_pull_request",
            "merge_pull_request",
            "enable_auto_merge",
            "force_push",
            "update_protected_branch",
            "create_release",
            "modify_github_workflow",
        ],
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }
    return _stdout_result(COMMAND_INSPECT, payload)


def record_github_link(
    config: AppConfig,
    *,
    queue_item_id: str,
    repository: str,
    project_id: str = DEFAULT_PROJECT_ID,
    item_id: str = DEFAULT_ITEM_ID,
    registry_path: str | Path | None = None,
    issue_number: int | None = None,
    issue_url: str | None = None,
    pr_number: int | None = None,
    pr_url: str | None = None,
    sync_status: str = "linked",
    last_sync_result: str | None = None,
    linked_by: str | None = None,
    link_source: str | None = None,
    warning: list[str] | None = None,
    dry_run: bool = False,
    output_format: str = "json",
) -> dict[str, Any]:
    fmt = _text(output_format).lower() or "json"
    if fmt != "json":
        return _error(COMMAND_RECORD, "invalid_format", {"format": output_format, "supported_formats": ["json"]})

    normalized_project_id = _text(project_id) or DEFAULT_PROJECT_ID
    normalized_item_id = _text(item_id) or DEFAULT_ITEM_ID
    normalized_queue_item_id = _text(queue_item_id)
    normalized_repository = _text(repository)
    normalized_sync_status = _text(sync_status) or "linked"
    resolved_path = resolve_github_link_registry_path(config.repo_root, registry_path)
    gate_payload = _gate_payload(config, item_id=normalized_item_id)
    gate_summary = _gate_summary(gate_payload)

    load_result = _load_registry(resolved_path)
    registry = load_result.get("registry") if load_result.get("ok") else _default_registry()
    records = _records(registry)
    blocked_reasons = _record_blocked_reasons(
        load_result=load_result,
        queue_item_id=normalized_queue_item_id,
        repository=normalized_repository,
        sync_status=normalized_sync_status,
        gate_payload=gate_payload,
    )
    warnings = _dedupe([*load_result.get("warnings", []), *_list(warning), *_url_warnings(issue_number, issue_url, pr_number, pr_url)])
    blocked = bool(blocked_reasons)
    idempotency_key = _link_idempotency_key(
        project_id=normalized_project_id,
        queue_item_id=normalized_queue_item_id,
        repository=normalized_repository,
    )

    existing_index = _find_record_index(records, idempotency_key)
    existing = records[existing_index] if existing_index >= 0 else {}
    record = _build_link_record(
        existing=existing,
        project_id=normalized_project_id,
        queue_item_id=normalized_queue_item_id,
        repository=normalized_repository,
        issue_number=issue_number,
        issue_url=issue_url,
        pr_number=pr_number,
        pr_url=pr_url,
        sync_status=normalized_sync_status,
        last_sync_result=last_sync_result,
        linked_by=linked_by,
        link_source=link_source,
        warnings=warnings,
        idempotency_key=idempotency_key,
    )
    if existing and _record_without_sync_time(existing) == _record_without_sync_time(record):
        record = _normalize_record(existing)
    changed = existing != record
    if not blocked and not dry_run and changed:
        if existing_index >= 0:
            records[existing_index] = record
        else:
            records.append(record)
        registry["schema_version"] = _text(registry.get("schema_version")) or "1.0"
        registry["updated_at"] = _now_iso()
        registry["links"] = sorted(records, key=lambda value: (_text(value.get("project_id")), _text(value.get("queue_item_id")), _text(value.get("repository"))))
        resolved_path.parent.mkdir(parents=True, exist_ok=True)
        resolved_path.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")

    payload = {
        "record_type": RECORD_TYPE,
        "artifact_type": RECORD_TYPE,
        "generated": True,
        "generated_at": _now_iso(),
        "project_id": normalized_project_id,
        "item_id": normalized_item_id,
        "repository": normalized_repository,
        "issue_number": record.get("issue_number"),
        "issue_url": record.get("issue_url"),
        "pr_number": record.get("pr_number"),
        "pr_url": record.get("pr_url"),
        "sync_status": "blocked" if blocked else record.get("sync_status"),
        "status": "blocked" if blocked else ("dry_run_ready" if dry_run else "link_recorded"),
        "blocked": blocked,
        "blocked_reasons": blocked_reasons,
        "warnings": warnings,
        "machine_gates_checked": [gate_summary],
        "machine_gates_passed": bool(gate_summary.get("passed")) and not blocked,
        "autonomy_profile": "github_sync_dry_run",
        "dry_run": bool(dry_run),
        "github_enabled": False,
        "github_execution_performed": False,
        "mutation_performed": bool(changed and not blocked and not dry_run),
        "queue_mutation_performed": False,
        "codex_execution_performed": False,
        "model_execution_performed": False,
        "patch_application_performed": False,
        "recovery_available": True,
        "local_only": True,
        "next_safe_action": "Inspect the local GitHub link registry and use only separate gated GitHub commands for any live sync.",
        "registry_path": str(resolved_path),
        "record_created": bool(existing_index < 0 and changed and not blocked and not dry_run),
        "record_updated": bool(existing_index >= 0 and changed and not blocked and not dry_run),
        "idempotent_noop": bool(existing_index >= 0 and not changed and not blocked),
        "idempotency_key": idempotency_key,
        "link_record": record,
        "github_operations_blocked": [
            "create_issue",
            "update_issue",
            "close_issue",
            "create_pull_request",
            "update_pull_request",
            "merge_pull_request",
            "enable_auto_merge",
            "force_push",
            "update_protected_branch",
            "create_release",
            "modify_github_workflow",
        ],
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }
    return _stdout_result(COMMAND_RECORD, payload)


def resolve_github_link_registry_path(repo_root: Path, registry_path: str | Path | None) -> Path:
    if registry_path is None:
        return (repo_root / DEFAULT_REGISTRY_RELATIVE).resolve()
    path = Path(registry_path)
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


def _default_registry() -> dict[str, Any]:
    return {"schema_version": "1.0", "updated_at": "", "links": []}


def _load_registry(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "ok": True,
            "registry": _default_registry(),
            "warnings": [f"GitHub link registry not found yet: {path}"],
            "blocked_reasons": [],
        }
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "ok": False,
            "registry": _default_registry(),
            "warnings": [],
            "blocked_reasons": [f"GitHub link registry could not be read as JSON: {exc}"],
        }
    if not isinstance(raw, dict):
        return {
            "ok": False,
            "registry": _default_registry(),
            "warnings": [],
            "blocked_reasons": ["GitHub link registry JSON must decode to an object."],
        }
    links = raw.get("links")
    if not isinstance(links, list):
        return {
            "ok": False,
            "registry": _default_registry(),
            "warnings": [],
            "blocked_reasons": ["GitHub link registry must contain a links array."],
        }
    return {"ok": True, "registry": raw, "warnings": [], "blocked_reasons": []}


def _records(registry: dict[str, Any]) -> list[dict[str, Any]]:
    records = registry.get("links", [])
    if not isinstance(records, list):
        return []
    return [_normalize_record(record) for record in records if isinstance(record, dict)]


def _normalize_record(record: dict[str, Any]) -> dict[str, Any]:
    project_id = _text(record.get("project_id")) or DEFAULT_PROJECT_ID
    queue_item_id = _text(record.get("queue_item_id") or record.get("item_id"))
    repository = _text(record.get("repository"))
    issue_number = _int_or_none(record.get("issue_number"))
    pr_number = _int_or_none(record.get("pr_number"))
    idempotency_key = _text(record.get("idempotency_key")) or _link_idempotency_key(
        project_id=project_id,
        queue_item_id=queue_item_id,
        repository=repository,
    )
    return {
        "record_type": LINK_RECORD_TYPE,
        "project_id": project_id,
        "queue_item_id": queue_item_id,
        "repository": repository,
        "issue_number": issue_number,
        "issue_url": _text(record.get("issue_url")),
        "pr_number": pr_number,
        "pr_url": _text(record.get("pr_url")),
        "sync_status": _text(record.get("sync_status")) or "unknown",
        "last_sync_time": _text(record.get("last_sync_time")),
        "last_sync_result": _text(record.get("last_sync_result")),
        "linked_by": _text(record.get("linked_by")),
        "link_source": _text(record.get("link_source")),
        "warnings": _list(record.get("warnings")),
        "idempotency_key": idempotency_key,
        "blocked": False,
        "blocked_reasons": [],
        "github_execution_performed": False,
        "mutation_performed": False,
        "local_only": True,
    }


def _filter_records(
    records: list[dict[str, Any]],
    *,
    project_id: str,
    queue_item_id: str | None,
    repository: str | None,
    issue_number: int | None,
    pr_number: int | None,
) -> list[dict[str, Any]]:
    normalized_queue_item_id = _text(queue_item_id)
    normalized_repository = _text(repository)
    filtered: list[dict[str, Any]] = []
    for record in records:
        if _text(record.get("project_id")) != project_id:
            continue
        if normalized_queue_item_id and _text(record.get("queue_item_id")) != normalized_queue_item_id:
            continue
        if normalized_repository and _text(record.get("repository")) != normalized_repository:
            continue
        if issue_number is not None and record.get("issue_number") != issue_number:
            continue
        if pr_number is not None and record.get("pr_number") != pr_number:
            continue
        filtered.append(record)
    return sorted(filtered, key=lambda value: (_text(value.get("queue_item_id")), _text(value.get("repository"))))


def _build_link_record(
    *,
    existing: dict[str, Any],
    project_id: str,
    queue_item_id: str,
    repository: str,
    issue_number: int | None,
    issue_url: str | None,
    pr_number: int | None,
    pr_url: str | None,
    sync_status: str,
    last_sync_result: str | None,
    linked_by: str | None,
    link_source: str | None,
    warnings: list[str],
    idempotency_key: str,
) -> dict[str, Any]:
    normalized = _normalize_record(existing) if existing else {}
    return {
        "record_type": LINK_RECORD_TYPE,
        "project_id": project_id,
        "queue_item_id": queue_item_id,
        "repository": repository,
        "issue_number": issue_number if issue_number is not None else normalized.get("issue_number"),
        "issue_url": _text(issue_url) or _text(normalized.get("issue_url")),
        "pr_number": pr_number if pr_number is not None else normalized.get("pr_number"),
        "pr_url": _text(pr_url) or _text(normalized.get("pr_url")),
        "sync_status": sync_status,
        "last_sync_time": _now_iso(),
        "last_sync_result": _text(last_sync_result) or _text(normalized.get("last_sync_result")),
        "linked_by": _text(linked_by) or _text(normalized.get("linked_by")) or "local_operator",
        "link_source": _text(link_source) or _text(normalized.get("link_source")) or COMMAND_RECORD,
        "warnings": _dedupe([*_list(normalized.get("warnings")), *warnings]),
        "idempotency_key": idempotency_key,
        "blocked": False,
        "blocked_reasons": [],
        "github_execution_performed": False,
        "mutation_performed": False,
        "local_only": True,
    }


def _record_blocked_reasons(
    *,
    load_result: dict[str, Any],
    queue_item_id: str,
    repository: str,
    sync_status: str,
    gate_payload: dict[str, Any],
) -> list[str]:
    reasons = [*load_result.get("blocked_reasons", [])]
    if not queue_item_id:
        reasons.append("queue_item_id is required.")
    if not repository or "/" not in repository:
        reasons.append("repository must use owner/name format.")
    if sync_status not in SYNC_STATUSES:
        reasons.append(f"sync_status must be one of: {', '.join(sorted(SYNC_STATUSES))}.")
    if gate_payload.get("passed") is not True or gate_payload.get("blocked") is True:
        reasons.append("Local registry write machine gate did not pass.")
        reasons.extend(_list(gate_payload.get("blocked_reasons")))
    return _dedupe(reasons)


def _find_record_index(records: list[dict[str, Any]], idempotency_key: str) -> int:
    for index, record in enumerate(records):
        if _text(record.get("idempotency_key")) == idempotency_key:
            return index
    return -1


def _record_without_sync_time(record: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(_normalize_record(record))
    normalized.pop("last_sync_time", None)
    return normalized


def _registry_warnings(records: list[dict[str, Any]]) -> list[str]:
    warnings: list[str] = []
    seen: set[str] = set()
    for record in records:
        key = _text(record.get("idempotency_key"))
        if key in seen:
            warnings.append(f"Duplicate registry idempotency key detected: {key}.")
        seen.add(key)
        warnings.extend(_list(record.get("warnings")))
    return _dedupe(warnings)


def _url_warnings(issue_number: int | None, issue_url: str | None, pr_number: int | None, pr_url: str | None) -> list[str]:
    warnings: list[str] = []
    if issue_number is not None and not _text(issue_url):
        warnings.append("issue_number was recorded without issue_url.")
    if pr_number is not None and not _text(pr_url):
        warnings.append("pr_number was recorded without pr_url.")
    return warnings


def _gate_payload(config: AppConfig, *, item_id: str) -> dict[str, Any]:
    result = evaluate_machine_safety_gates(
        config,
        item_id=item_id,
        gate_profile="read_only_agent",
        output_format="json",
    )
    payload = result.get("payload", {}) if isinstance(result, dict) else {}
    return payload if isinstance(payload, dict) else {}


def _gate_summary(gate_payload: dict[str, Any]) -> dict[str, Any]:
    checks = gate_payload.get("checks", [])
    failed = [
        _text(check.get("check_id"))
        for check in checks
        if isinstance(check, dict) and not bool(check.get("passed")) and not bool(check.get("warning_only"))
    ]
    return {
        "gate_profile": _text(gate_payload.get("gate_profile")) or "read_only_agent",
        "passed": bool(gate_payload.get("passed")) and not bool(gate_payload.get("blocked")),
        "blocked": bool(gate_payload.get("blocked")),
        "blocked_reasons": _list(gate_payload.get("blocked_reasons")),
        "checks_failed": failed,
    }


def _stdout_result(command: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "command": command,
        "ok": not bool(payload.get("blocked")),
        "local_only": True,
        "format": "json",
        "wrote_output_file": False,
        "stdout": json.dumps(payload, indent=2),
        "payload": payload,
    }


def _error(command: str, error: str, details: dict[str, Any]) -> dict[str, Any]:
    return {
        "command": command,
        "ok": False,
        "local_only": True,
        "error": error,
        "details": details,
    }


def _next_safe_action(*, blocked: bool, filtered: list[dict[str, Any]]) -> str:
    if blocked:
        return "Repair the local GitHub link registry or machine-gate blockers before relying on link lookups."
    if filtered:
        return "Use these local links as review metadata only; live GitHub work remains separate and gated."
    return "Record queue item links locally with record-github-link after operator review."


def _inspect_idempotency_key(
    *,
    project_id: str,
    queue_item_id: str | None,
    repository: str | None,
    issue_number: int | None,
    pr_number: int | None,
) -> str:
    parts = [
        _slug(project_id),
        _slug(queue_item_id or "all-items"),
        _slug(repository or "all-repositories"),
        f"issue-{issue_number}" if issue_number is not None else "all-issues",
        f"pr-{pr_number}" if pr_number is not None else "all-prs",
    ]
    return "inspect:" + ":".join(parts)


def _link_idempotency_key(*, project_id: str, queue_item_id: str, repository: str) -> str:
    return "link:" + ":".join([_slug(project_id), _slug(queue_item_id), _slug(repository)])


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
