from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.local_project_queue import resolve_project_queue_path
from aresforge.operator.machine_safety_gate_engine import evaluate_machine_safety_gates

COMMAND_NAME = "plan-github-issue-sync"
RECORD_TYPE = "github_issue_sync_plan_from_queue_items_v1"
DEFAULT_PROJECT_ID = "aresforge"
DEFAULT_ITEM_ID = "m162-github-issue-sync-plan-from-queue-items"

_SOURCE_DOCS: tuple[str, ...] = (
    "docs/context/BUILD_STATE.md",
    "docs/context/AGENT_CONTEXT.md",
    "docs/roadmap/ROADMAP.md",
    "docs/operator/LOCAL_OPERATOR_USAGE.md",
    "docs/architecture/RUNNABLE_SKELETON.md",
    "docs/architecture/AGENT_LLM_ROUTING_STRATEGY.md",
    "docs/architecture/LOCAL_LLM_ENVIRONMENT_CONTRACT.md",
    "docs/architecture/DOCUMENTATION_AGENT_CONTRACT.md",
)

_BOUNDARY_CONFIRMATIONS: tuple[str, ...] = (
    "Local-only GitHub issue sync planning from queue items.",
    "No gh commands executed.",
    "No GitHub API calls executed.",
    "No issue, label, milestone, or comment mutation performed.",
    "No pull request merge, protected branch update, force push, auto-merge, release, workflow, Codex, model, source patch, queue mutation, retry, resume, or next-item execution.",
)


def plan_github_issue_sync(
    config: AppConfig,
    *,
    project_id: str = DEFAULT_PROJECT_ID,
    item_id: str = DEFAULT_ITEM_ID,
    queue_path: str | Path | None = None,
    output: str | Path | None = None,
    force: bool = False,
    output_format: str = "json",
) -> dict[str, Any]:
    fmt = _text(output_format).lower() or "json"
    if fmt != "json":
        return _error("invalid_format", {"format": output_format, "supported_formats": ["json"]})

    normalized_project_id = _text(project_id) or DEFAULT_PROJECT_ID
    normalized_item_id = _text(item_id) or DEFAULT_ITEM_ID
    resolved_queue_path = resolve_project_queue_path(config.repo_root, queue_path)
    queue_result = _load_queue(resolved_queue_path)
    queue = queue_result.get("queue") if queue_result.get("ok") else {}
    work_items = queue.get("work_items", []) if isinstance(queue, dict) else []
    if not isinstance(work_items, list):
        work_items = []

    scoped_items = [
        item
        for item in work_items
        if isinstance(item, dict) and _text(item.get("project_id")) == normalized_project_id
    ]
    plan_item = _find_item(work_items, normalized_item_id)
    gate_payload = _gate_payload(config, item_id=normalized_item_id, queue_path=queue_path)
    gate_summary = _gate_summary(gate_payload)

    warnings = _dedupe([*queue_result.get("warnings", []), *_list(gate_payload.get("warnings"))])
    blocked_reasons = _dedupe([*queue_result.get("blocked_reasons", []), *_list(gate_payload.get("blocked_reasons"))])
    if not queue_result.get("ok"):
        blocked_reasons.append("Local queue must be readable before a GitHub issue sync plan can be generated.")
    if not plan_item:
        warnings.append("M162 queue item is not present; generated plan still covers project queue items for operator review.")
    if not scoped_items:
        warnings.append(f"No queue items found for project_id={normalized_project_id}.")

    item_plans = [
        _item_issue_plan(item, project_id=normalized_project_id)
        for item in sorted(scoped_items, key=lambda value: _text(value.get("item_id")))
    ]
    operation_recommendations = [recommendation for item_plan in item_plans for recommendation in item_plan["recommendations"]]
    blocked = bool(blocked_reasons)
    status = "blocked" if blocked else "plan_generated"

    payload: dict[str, Any] = {
        "record_type": RECORD_TYPE,
        "artifact_type": RECORD_TYPE,
        "generated": True,
        "generated_at": _now_iso(),
        "project_id": normalized_project_id,
        "item_id": normalized_item_id,
        "run_id": "",
        "status": status,
        "blocked": blocked,
        "blocked_reasons": blocked_reasons,
        "warnings": _dedupe(warnings),
        "machine_gates_checked": [gate_summary],
        "machine_gates_passed": bool(gate_summary.get("passed")) and not blocked,
        "autonomy_profile": "github_sync_dry_run",
        "artifacts_created": [],
        "mutation_performed": False,
        "queue_mutation_performed": False,
        "codex_execution_performed": False,
        "model_execution_performed": False,
        "github_execution_performed": False,
        "patch_application_performed": False,
        "local_only": True,
        "next_safe_action": _next_safe_action(blocked=blocked, item_plans=item_plans),
        "queue_path": str(resolved_queue_path),
        "queue_item_found": bool(plan_item),
        "queue_item_count": len(scoped_items),
        "issue_mapping_contract": _issue_mapping_contract(),
        "issue_sync_items": item_plans,
        "operation_recommendations": operation_recommendations,
        "operation_counts": _operation_counts(operation_recommendations),
        "source_of_truth_docs_used": _existing_source_docs(config.repo_root),
        "mutation_allowed": False,
        "github_mutation_allowed": False,
        "github_operations_performed": False,
        "explicit_no_github_operations_statement": "No GitHub operations were performed. This is a local-only sync plan.",
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }
    return _emit_or_write(config=config, payload=payload, output=output, force=force)


def _item_issue_plan(item: dict[str, Any], *, project_id: str) -> dict[str, Any]:
    item_id = _text(item.get("item_id"))
    linked_issue = _linked_issue(item)
    issue_draft = {
        "title": _issue_title(item),
        "body": _issue_body(item),
        "labels": _issue_labels(item),
        "milestone": _issue_milestone(item),
        "comments": _issue_comments(item),
    }
    blocked_reasons = _item_blocked_reasons(item)
    warnings = _item_warnings(item, linked_issue=linked_issue)
    recommendations = _recommendations(item, linked_issue=linked_issue, issue_draft=issue_draft, blocked_reasons=blocked_reasons)

    return {
        "record_type": "github_issue_sync_item_plan_v1",
        "project_id": project_id,
        "item_id": item_id,
        "queue_status": _text(item.get("status")),
        "blocked": bool(blocked_reasons),
        "blocked_reasons": blocked_reasons,
        "warnings": warnings,
        "linked_issue": linked_issue,
        "issue_draft": issue_draft,
        "recommendations": recommendations,
        "mutation_performed": False,
        "github_execution_performed": False,
        "local_only": True,
        "next_safe_action": "Review this local issue draft before any separate approved GitHub sync command.",
    }


def _issue_title(item: dict[str, Any]) -> str:
    title = _text(item.get("title")) or _text(item.get("item_id")) or "Untitled queue item"
    item_id = _text(item.get("item_id"))
    if item_id and item_id.lower().startswith("m") and item_id.split("-", 1)[0].upper() not in title.upper():
        return f"{item_id.split('-', 1)[0].upper()} {title}"
    return title


def _issue_body(item: dict[str, Any]) -> str:
    lines = [
        "## Queue Item",
        f"- item_id: {_text(item.get('item_id'))}",
        f"- project_id: {_text(item.get('project_id'))}",
        f"- repo_id: {_text(item.get('repo_id'))}",
        f"- status: {_text(item.get('status'))}",
        f"- priority: {_text(item.get('priority'))}",
        f"- item_type: {_text(item.get('item_type'))}",
        "",
        "## Description",
        _text(item.get("description")) or "No description recorded.",
        "",
        "## Dependencies",
    ]
    dependencies = _list(item.get("dependencies")) + _list(item.get("depends_on"))
    lines.extend([f"- {entry}" for entry in dependencies] or ["- None"])
    blocked_by = _list(item.get("blocked_by"))
    lines.extend(["", "## Blocked By"])
    lines.extend([f"- {entry}" for entry in blocked_by] or ["- None"])
    notes = _text(item.get("notes"))
    if notes:
        lines.extend(["", "## Local Notes", notes])
    lines.extend(
        [
            "",
            "## Local Sync Boundary",
            "- Generated from the local AresForge queue.",
            "- This draft did not create or update a GitHub issue.",
        ]
    )
    return "\n".join(lines)


def _issue_labels(item: dict[str, Any]) -> list[str]:
    labels = ["aresforge-queue", f"status:{_slug(_text(item.get('status')) or 'unknown')}"]
    item_type = _text(item.get("item_type"))
    priority = _text(item.get("priority"))
    if item_type:
        labels.append(f"type:{_slug(item_type)}")
    if priority:
        labels.append(f"priority:{_slug(priority)}")
    for tag in _list(item.get("tags")):
        labels.append(_label_from_tag(tag))
    return _dedupe(labels)


def _issue_milestone(item: dict[str, Any]) -> str:
    for tag in _list(item.get("tags")):
        normalized = tag.strip()
        if normalized.lower().startswith("milestone:"):
            value = normalized.split(":", 1)[1].strip()
            return value.upper() if value.lower().startswith("m") else value
    item_id = _text(item.get("item_id"))
    if item_id.lower().startswith("m") and "-" in item_id:
        return item_id.split("-", 1)[0].upper()
    return ""


def _issue_comments(item: dict[str, Any]) -> list[dict[str, Any]]:
    comments: list[dict[str, Any]] = []
    if _text(item.get("validation_summary")) or _list(item.get("tests_run")):
        comments.append(
            {
                "comment_type": "validation_evidence",
                "body": _validation_comment_body(item),
            }
        )
    if _text(item.get("evidence_note")):
        comments.append(
            {
                "comment_type": "evidence_note",
                "body": _text(item.get("evidence_note")),
            }
        )
    return comments


def _validation_comment_body(item: dict[str, Any]) -> str:
    lines = ["## Local Validation Evidence"]
    summary = _text(item.get("validation_summary"))
    if summary:
        lines.extend(["", summary])
    tests = _list(item.get("tests_run"))
    if tests:
        lines.extend(["", "## Tests Run"])
        lines.extend(f"- {entry}" for entry in tests)
    return "\n".join(lines)


def _linked_issue(item: dict[str, Any]) -> dict[str, Any]:
    candidates: list[Any] = [
        item.get("github_issue"),
        item.get("github"),
        item.get("github_metadata"),
        item.get("issue"),
    ]
    for key in ("github_issue_number", "issue_number", "github_issue_url", "issue_url", "url"):
        if item.get(key):
            candidates.append({key: item.get(key)})
    external_links = item.get("external_links")
    if isinstance(external_links, list):
        candidates.extend(external_links)

    for candidate in candidates:
        parsed = _parse_issue_candidate(candidate)
        if parsed["linked"]:
            return parsed
    return {
        "linked": False,
        "issue_number": None,
        "issue_url": "",
        "metadata_source": "",
    }


def _parse_issue_candidate(candidate: Any) -> dict[str, Any]:
    if isinstance(candidate, int):
        return {"linked": True, "issue_number": candidate, "issue_url": "", "metadata_source": "number"}
    if isinstance(candidate, str):
        number = _extract_issue_number(candidate)
        return {
            "linked": bool(number),
            "issue_number": number,
            "issue_url": candidate if number else "",
            "metadata_source": "string_url" if number else "",
        }
    if not isinstance(candidate, dict):
        return {"linked": False, "issue_number": None, "issue_url": "", "metadata_source": ""}
    for key in ("number", "issue_number", "github_issue_number"):
        value = candidate.get(key)
        if isinstance(value, int):
            return {
                "linked": True,
                "issue_number": value,
                "issue_url": _text(candidate.get("url") or candidate.get("issue_url")),
                "metadata_source": key,
            }
        if _text(value).isdigit():
            return {
                "linked": True,
                "issue_number": int(_text(value)),
                "issue_url": _text(candidate.get("url") or candidate.get("issue_url")),
                "metadata_source": key,
            }
    for key in ("url", "issue_url", "github_issue_url"):
        url = _text(candidate.get(key))
        number = _extract_issue_number(url)
        if number:
            return {"linked": True, "issue_number": number, "issue_url": url, "metadata_source": key}
    return {"linked": False, "issue_number": None, "issue_url": "", "metadata_source": ""}


def _recommendations(
    item: dict[str, Any],
    *,
    linked_issue: dict[str, Any],
    issue_draft: dict[str, Any],
    blocked_reasons: list[str],
) -> list[dict[str, Any]]:
    item_id = _text(item.get("item_id"))
    status = _text(item.get("status"))
    if blocked_reasons:
        return [_recommendation("skip", item_id, "Queue item has local blockers that should be resolved before GitHub issue sync.")]
    if status in {"cancelled"}:
        return [_recommendation("skip", item_id, "Cancelled queue items should not create or update GitHub issues by default.")]
    if not linked_issue.get("linked"):
        return [_recommendation("create", item_id, "No linked GitHub issue metadata was found.", issue_draft=issue_draft)]
    recommendations = [
        _recommendation(
            "update",
            item_id,
            "Linked GitHub issue metadata exists; review title/body/labels/milestone drift before any future update.",
            issue_number=linked_issue.get("issue_number"),
            issue_draft=issue_draft,
        )
    ]
    if issue_draft.get("comments"):
        recommendations.append(
            _recommendation(
                "comment",
                item_id,
                "Local validation or evidence notes are available for a future issue comment.",
                issue_number=linked_issue.get("issue_number"),
                comments=issue_draft.get("comments"),
            )
        )
    elif status == "done":
        recommendations.append(
            _recommendation(
                "skip",
                item_id,
                "Item is done but has no local comment evidence to sync.",
                issue_number=linked_issue.get("issue_number"),
            )
        )
    return recommendations


def _recommendation(
    action: str,
    item_id: str,
    reason: str,
    *,
    issue_number: Any = None,
    issue_draft: dict[str, Any] | None = None,
    comments: Any = None,
) -> dict[str, Any]:
    return {
        "record_type": "github_issue_sync_recommendation_v1",
        "item_id": item_id,
        "recommended_action": action,
        "issue_number": issue_number,
        "reason": reason,
        "issue_draft": issue_draft or {},
        "comments": comments or [],
        "mutation_performed": False,
        "github_execution_performed": False,
        "local_only": True,
    }


def _item_blocked_reasons(item: dict[str, Any]) -> list[str]:
    reasons = []
    if _list(item.get("blocked_by")):
        reasons.append("Queue item has blocked_by entries.")
    if _text(item.get("status")) == "blocked":
        reasons.append("Queue item status is blocked.")
    return reasons


def _item_warnings(item: dict[str, Any], *, linked_issue: dict[str, Any]) -> list[str]:
    warnings = []
    if not _text(item.get("title")):
        warnings.append("Queue item title is missing; issue title falls back to item_id.")
    if not _text(item.get("description")):
        warnings.append("Queue item description is missing; issue body will be sparse.")
    if linked_issue.get("linked") and not linked_issue.get("issue_url"):
        warnings.append("Linked issue number found without an issue URL.")
    return warnings


def _issue_mapping_contract() -> dict[str, Any]:
    return {
        "title_fields": ["title", "item_id fallback"],
        "body_fields": ["item_id", "project_id", "repo_id", "status", "priority", "item_type", "description", "dependencies", "blocked_by", "notes"],
        "label_fields": ["status", "priority", "item_type", "tags"],
        "milestone_fields": ["milestone:* tag", "item_id milestone prefix fallback"],
        "comment_fields": ["validation_summary", "tests_run", "evidence_note"],
        "linked_issue_detection_fields": [
            "github_issue",
            "github",
            "github_metadata",
            "issue",
            "github_issue_number",
            "issue_number",
            "github_issue_url",
            "issue_url",
            "external_links",
        ],
    }


def _operation_counts(recommendations: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"create": 0, "update": 0, "comment": 0, "skip": 0}
    for recommendation in recommendations:
        action = _text(recommendation.get("recommended_action"))
        if action in counts:
            counts[action] += 1
    return counts


def _gate_payload(config: AppConfig, *, item_id: str, queue_path: str | Path | None) -> dict[str, Any]:
    result = evaluate_machine_safety_gates(
        config,
        item_id=item_id,
        gate_profile="read_only_agent",
        queue_path=queue_path,
        output_format="json",
    )
    return result.get("payload", {}) if isinstance(result, dict) else {}


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


def _load_queue(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "ok": False,
            "queue": {},
            "warnings": [],
            "blocked_reasons": [f"Project queue not found: {path}"],
        }
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "ok": False,
            "queue": {},
            "warnings": [],
            "blocked_reasons": [f"Project queue could not be read as JSON: {exc}"],
        }
    if not isinstance(raw, dict):
        return {
            "ok": False,
            "queue": {},
            "warnings": [],
            "blocked_reasons": ["Project queue JSON must decode to an object."],
        }
    return {"ok": True, "queue": raw, "warnings": [], "blocked_reasons": []}


def _find_item(items: list[Any], item_id: str) -> dict[str, Any]:
    for item in items:
        if isinstance(item, dict) and _text(item.get("item_id")) == item_id:
            return item
    return {}


def _existing_source_docs(repo_root: Path) -> list[str]:
    return [str((repo_root / path).resolve()) for path in _SOURCE_DOCS if (repo_root / path).exists()]


def _label_from_tag(tag: str) -> str:
    text = tag.strip()
    if not text:
        return ""
    if ":" in text:
        left, right = text.split(":", 1)
        return f"{_slug(left)}:{_slug(right)}"
    return _slug(text)


def _extract_issue_number(value: str) -> int | None:
    text = value.strip()
    if not text:
        return None
    match = re.search(r"/issues/(\d+)(?:\b|$)", text)
    if match:
        return int(match.group(1))
    if text.isdigit():
        return int(text)
    return None


def _next_safe_action(*, blocked: bool, item_plans: list[dict[str, Any]]) -> str:
    if blocked:
        return "Resolve local queue or machine-gate blockers before relying on this GitHub issue sync plan."
    if not item_plans:
        return "Add or inspect local queue items before preparing a future GitHub issue sync."
    return "Review create/update/comment/skip recommendations locally; use only a separate future approved GitHub sync command for mutation."


def _emit_or_write(
    *,
    config: AppConfig,
    payload: dict[str, Any],
    output: str | Path | None,
    force: bool,
) -> dict[str, Any]:
    rendered = json.dumps(payload, indent=2)
    if output is None:
        return {
            "command": COMMAND_NAME,
            "ok": not bool(payload.get("blocked")),
            "local_only": True,
            "format": "json",
            "wrote_output_file": False,
            "stdout": rendered,
            "payload": payload,
        }
    output_path = _resolve(config.repo_root, output)
    if output_path.exists() and not force:
        blocked_payload = dict(payload)
        blocked_payload["status"] = "blocked"
        blocked_payload["blocked"] = True
        blocked_payload["blocked_reasons"] = _dedupe(
            [*_list(blocked_payload.get("blocked_reasons")), "Output file already exists. Re-run with --force to overwrite."]
        )
        return {
            "command": COMMAND_NAME,
            "ok": False,
            "local_only": True,
            "format": "json",
            "output": str(output_path),
            "force": force,
            "wrote_output_file": False,
            "stdout": json.dumps(blocked_payload, indent=2),
            "payload": blocked_payload,
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
        "payload": artifact_payload,
    }


def _resolve(repo_root: Path, value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-") or "unknown"


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
