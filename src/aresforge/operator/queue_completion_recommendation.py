from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.local_project_queue import resolve_project_queue_path

QUEUE_COMPLETION_RECOMMENDATION_VERSION = "m113.1"
COMMAND_NAME = "recommend-queue-completion"

_BOUNDARY_CONFIRMATIONS = (
    "M113 queue completion recommendation is local-only.",
    "M113 reads local queue state and a local dispatch evidence record only.",
    "M113 does not execute Codex, Codex CLI, local LLMs, documentation agents, or external agents.",
    "M113 does not call GitHub APIs, gh, network services, issues, PRs, or workflows.",
    "M113 does not apply patches or mutate repository files.",
    "M113 does not mark queue items complete or start follow-on work.",
)

_PASS_TOKENS = (" passed", "passed ", " pass", "success", "succeeded", "ok", "clean")
_FAIL_TOKENS = (
    "failed",
    "failure",
    "error",
    "errored",
    "not run",
    "did not run",
    "unable",
    "blocked",
    "timeout",
)


def recommend_queue_completion(
    config: AppConfig,
    *,
    item_id: str,
    evidence_path: str | Path,
    queue_path: str | Path | None = None,
    output: str | Path | None = None,
    force: bool = False,
    output_format: str = "markdown",
) -> dict[str, Any]:
    fmt = str(output_format or "markdown").lower().strip()
    if fmt not in {"markdown", "json"}:
        return _error("invalid_format", {"format": output_format, "supported_formats": ["markdown", "json"]})

    normalized_item_id = str(item_id or "").strip()
    item = _load_queue_item(config, item_id=normalized_item_id, queue_path=queue_path)
    resolved_evidence_path = _resolve_path(config.repo_root, evidence_path)
    evidence, evidence_read_errors = _load_evidence(resolved_evidence_path)
    payload = _build_payload(
        item_id=normalized_item_id,
        item=item,
        evidence_path=resolved_evidence_path,
        evidence=evidence,
        evidence_read_errors=evidence_read_errors,
    )
    return _emit_or_write(config=config, payload=payload, output=output, force=force, output_format=fmt)


def _build_payload(
    *,
    item_id: str,
    item: dict[str, Any],
    evidence_path: Path,
    evidence: dict[str, Any],
    evidence_read_errors: list[str],
) -> dict[str, Any]:
    warnings_or_blockers = _dedupe(_list(evidence.get("warnings_or_blockers")))
    tests_reported = _list(evidence.get("tests_reported"))
    smoke_checks_reported = _list(evidence.get("smoke_checks_reported"))
    tests_passed_reported = _reported_passed(tests_reported)
    smoke_checks_passed_reported = _reported_passed(smoke_checks_reported)
    commit_hash = str(evidence.get("commit_hash", "") or "").strip()
    commit_hash_present = bool(commit_hash)
    evidence_valid, evidence_validation_reasons = _validate_evidence(
        item_id=item_id,
        evidence=evidence,
        evidence_path=evidence_path,
        evidence_read_errors=evidence_read_errors,
    )
    missing_evidence = _missing_evidence(
        item=item,
        evidence_valid=evidence_valid,
        tests_passed_reported=tests_passed_reported,
        smoke_checks_passed_reported=smoke_checks_passed_reported,
        commit_hash_present=commit_hash_present,
        evidence=evidence,
    )
    severe_warnings = [entry for entry in warnings_or_blockers if _looks_like_blocker(entry)]
    blocked_reasons = _blocked_reasons(
        item=item,
        evidence_validation_reasons=evidence_validation_reasons,
        missing_evidence=missing_evidence,
        severe_warnings=severe_warnings,
    )
    required_evidence_present = not missing_evidence
    recommended_complete = (
        evidence_valid
        and required_evidence_present
        and tests_passed_reported
        and smoke_checks_passed_reported
        and commit_hash_present
        and not severe_warnings
        and bool(item)
    )
    return {
        "recommendation_record_type": "queue_completion_recommendation",
        "recommendation_version": QUEUE_COMPLETION_RECOMMENDATION_VERSION,
        "recommended_complete": recommended_complete,
        "blocked": not recommended_complete,
        "blocked_reasons": blocked_reasons,
        "item_id": item_id,
        "title": str(item.get("title", "")).strip(),
        "project_id": str(item.get("project_id", "")).strip(),
        "milestone": _milestone(item),
        "evidence_path": str(evidence_path),
        "evidence_valid": evidence_valid,
        "required_evidence_present": required_evidence_present,
        "missing_evidence": missing_evidence,
        "tests_passed_reported": tests_passed_reported,
        "smoke_checks_passed_reported": smoke_checks_passed_reported,
        "warnings_or_blockers": warnings_or_blockers,
        "commit_hash_present": commit_hash_present,
        "confidence": _confidence(
            recommended_complete=recommended_complete,
            evidence_valid=evidence_valid,
            missing_evidence=missing_evidence,
            tests_passed_reported=tests_passed_reported,
            smoke_checks_passed_reported=smoke_checks_passed_reported,
            commit_hash_present=commit_hash_present,
            severe_warnings=severe_warnings,
        ),
        "operator_decision_required": True,
        "queue_mutation_performed": False,
        "local_only": True,
        "execution_allowed": False,
        "recorded_at": _now_iso(),
        "next_safe_action": _next_safe_action(recommended_complete=recommended_complete, blocked_reasons=blocked_reasons),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }


def _validate_evidence(
    *,
    item_id: str,
    evidence: dict[str, Any],
    evidence_path: Path,
    evidence_read_errors: list[str],
) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if not evidence_path.exists():
        reasons.append(f"Evidence file is missing: {evidence_path}")
    reasons.extend(evidence_read_errors)
    if not evidence:
        return False, _dedupe(reasons or ["Evidence record could not be loaded."])
    if evidence.get("evidence_record_type") != "dispatch_result_evidence":
        reasons.append("Evidence record type is not dispatch_result_evidence.")
    if str(evidence.get("item_id", "")).strip() != item_id:
        reasons.append("Evidence item_id does not match the requested queue item.")
    if evidence.get("parsed") is not True:
        reasons.append("Evidence record was not parsed successfully.")
    if evidence.get("blocked") is True:
        reasons.append("Evidence record is blocked.")
    if evidence.get("local_only") is not True:
        reasons.append("Evidence record does not confirm local_only=true.")
    if evidence.get("execution_allowed") is not False:
        reasons.append("Evidence record does not confirm execution_allowed=false.")
    if evidence.get("human_review_required") is not True:
        reasons.append("Evidence record does not require human review.")
    return not reasons, _dedupe(reasons)


def _missing_evidence(
    *,
    item: dict[str, Any],
    evidence_valid: bool,
    tests_passed_reported: bool,
    smoke_checks_passed_reported: bool,
    commit_hash_present: bool,
    evidence: dict[str, Any],
) -> list[str]:
    missing: list[str] = []
    if not evidence_valid:
        missing.append("valid_dispatch_result_evidence")
    if not _list(evidence.get("files_changed")):
        missing.append("files_changed")
    if not _list(evidence.get("what_changed")):
        missing.append("what_changed")
    if not tests_passed_reported:
        missing.append("tests_passed_reported")
    if not smoke_checks_passed_reported:
        missing.append("smoke_checks_passed_reported")
    if not commit_hash_present:
        missing.append("commit_hash")

    required = [*_list(item.get("completion_requires")), *_list(item.get("evidence_required"))]
    for requirement in required:
        key = _normalize_requirement(requirement)
        if key and not _requirement_present(key, evidence, tests_passed_reported, smoke_checks_passed_reported, commit_hash_present):
            missing.append(key)
    return _dedupe(missing)


def _requirement_present(
    key: str,
    evidence: dict[str, Any],
    tests_passed_reported: bool,
    smoke_checks_passed_reported: bool,
    commit_hash_present: bool,
) -> bool:
    if key in {"tests_run", "tests_reported", "validation_results", "tests_passed_reported"}:
        return tests_passed_reported
    if key in {"smoke_checks", "smoke_checks_reported", "smoke_checks_passed_reported"}:
        return smoke_checks_passed_reported
    if key in {"commit", "commit_hash", "completion_commit"}:
        return commit_hash_present
    if key in {"changed_files", "files_changed"}:
        return bool(_list(evidence.get("files_changed")))
    if key in {"change_summary", "what_changed", "validation_summary"}:
        return bool(_list(evidence.get("what_changed")))
    if key in {"dispatch_result_evidence", "parsed_dispatch_evidence"}:
        return evidence.get("evidence_record_type") == "dispatch_result_evidence"
    if key in {"review_evidence", "human_review_required"}:
        return evidence.get("human_review_required") is True
    return bool(evidence.get(key))


def _reported_passed(values: list[str]) -> bool:
    if not values:
        return False
    any_pass = False
    for value in values:
        lower = f" {value.lower()} "
        if any(token in lower for token in _FAIL_TOKENS):
            return False
        if any(token in lower for token in _PASS_TOKENS):
            any_pass = True
    return any_pass


def _blocked_reasons(
    *,
    item: dict[str, Any],
    evidence_validation_reasons: list[str],
    missing_evidence: list[str],
    severe_warnings: list[str],
) -> list[str]:
    reasons: list[str] = []
    if not item:
        reasons.append("Queue item was not found.")
    reasons.extend(evidence_validation_reasons)
    reasons.extend(f"Required evidence is missing: {entry}" for entry in missing_evidence)
    reasons.extend(f"Evidence reports warning or blocker: {entry}" for entry in severe_warnings)
    return _dedupe(reasons)


def _confidence(
    *,
    recommended_complete: bool,
    evidence_valid: bool,
    missing_evidence: list[str],
    tests_passed_reported: bool,
    smoke_checks_passed_reported: bool,
    commit_hash_present: bool,
    severe_warnings: list[str],
) -> str:
    if not evidence_valid or severe_warnings:
        return "blocked"
    if recommended_complete:
        return "high"
    if tests_passed_reported and smoke_checks_passed_reported and commit_hash_present:
        return "medium"
    if missing_evidence:
        return "low"
    return "medium"


def _looks_like_blocker(entry: str) -> bool:
    lower = entry.lower()
    if "no blocker" in lower or "no blockers" in lower:
        return False
    return any(token in lower for token in ("blocker", "blocked", "failed", "failure", "error", "unable", "not run"))


def _load_queue_item(config: AppConfig, *, item_id: str, queue_path: str | Path | None) -> dict[str, Any]:
    path = resolve_project_queue_path(config.repo_root, queue_path)
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    items = raw.get("work_items", []) if isinstance(raw, dict) else []
    for item in items:
        if isinstance(item, dict) and str(item.get("item_id", "")).strip() == item_id:
            return item
    return {}


def _load_evidence(path: Path) -> tuple[dict[str, Any], list[str]]:
    if not path.exists():
        return {}, []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {}, [f"Evidence file is not valid JSON: {exc.msg}."]
    except OSError as exc:
        return {}, [f"Evidence file could not be read: {exc}."]
    if not isinstance(raw, dict):
        return {}, ["Evidence file JSON root must be an object."]
    return raw, []


def _emit_or_write(
    *,
    config: AppConfig,
    payload: dict[str, Any],
    output: str | Path | None,
    force: bool,
    output_format: str,
) -> dict[str, Any]:
    rendered = json.dumps(payload, indent=2) if output_format == "json" else _render_markdown(payload)
    ok = bool(payload.get("recommended_complete")) and not bool(payload.get("blocked"))
    if output is None:
        return {
            "command": COMMAND_NAME,
            "ok": ok,
            "local_only": True,
            "format": output_format,
            "wrote_output_file": False,
            "stdout": rendered,
            "payload": payload,
        }
    output_path = _resolve_path(config.repo_root, output)
    if output_path.exists() and not force:
        payload = dict(payload)
        payload["recommended_complete"] = False
        payload["blocked"] = True
        payload["blocked_reasons"] = _dedupe(
            [*payload.get("blocked_reasons", []), "Output file already exists. Re-run with --force to overwrite."]
        )
        rendered = json.dumps(payload, indent=2) if output_format == "json" else _render_markdown(payload)
        ok = False
    else:
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(rendered.rstrip() + "\n", encoding="utf-8")
        except OSError as exc:
            return _error("output_write_failed", {"path": str(output_path), "message": str(exc)}, payload=payload)
    return {
        "command": COMMAND_NAME,
        "ok": ok,
        "local_only": True,
        "format": output_format,
        "output": str(output_path),
        "force": force,
        "wrote_output_file": ok,
        "stdout": rendered,
        "payload": payload,
    }


def _render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Queue Completion Recommendation",
        "",
        f"- recommendation_record_type: {payload.get('recommendation_record_type', '')}",
        f"- recommended_complete: {payload.get('recommended_complete')}",
        f"- blocked: {payload.get('blocked')}",
        f"- item_id: {payload.get('item_id', '')}",
        f"- title: {payload.get('title', '')}",
        f"- evidence_path: {payload.get('evidence_path', '')}",
        f"- evidence_valid: {payload.get('evidence_valid')}",
        f"- required_evidence_present: {payload.get('required_evidence_present')}",
        f"- tests_passed_reported: {payload.get('tests_passed_reported')}",
        f"- smoke_checks_passed_reported: {payload.get('smoke_checks_passed_reported')}",
        f"- commit_hash_present: {payload.get('commit_hash_present')}",
        f"- confidence: {payload.get('confidence', '')}",
        f"- operator_decision_required: {payload.get('operator_decision_required')}",
        f"- queue_mutation_performed: {payload.get('queue_mutation_performed')}",
        f"- local_only: {payload.get('local_only')}",
        f"- execution_allowed: {payload.get('execution_allowed')}",
        f"- next_safe_action: {payload.get('next_safe_action', '')}",
    ]
    for key, title in (
        ("blocked_reasons", "Blocked Reasons"),
        ("missing_evidence", "Missing Evidence"),
        ("warnings_or_blockers", "Warnings Or Blockers"),
    ):
        values = payload.get(key, []) if isinstance(payload.get(key), list) else []
        if values:
            lines.extend(["", f"## {title}"])
            lines.extend(f"- {value}" for value in values)
    return "\n".join(lines).rstrip()


def _next_safe_action(*, recommended_complete: bool, blocked_reasons: list[str]) -> str:
    if recommended_complete:
        return "Operator may review this recommendation and explicitly complete the queue item with validation evidence."
    if any("Evidence file is missing" in reason for reason in blocked_reasons):
        return "Provide a local dispatch evidence JSON record before requesting a completion recommendation."
    return "Resolve blocked reasons and re-run the recommendation before any queue completion decision."


def _milestone(item: dict[str, Any]) -> str:
    tags = item.get("tags", []) if isinstance(item.get("tags"), list) else []
    for tag in tags:
        text = str(tag).strip()
        if text.startswith("milestone:"):
            return text.split(":", 1)[1].split(",", 1)[0].strip()
    item_id = str(item.get("item_id", "")).strip()
    return item_id.split("-", 1)[0].upper() if item_id.lower().startswith("m") and "-" in item_id else ""


def _resolve_path(repo_root: Path, value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


def _list(value: Any) -> list[str]:
    if isinstance(value, list):
        return _dedupe(value)
    if value in (None, ""):
        return []
    return [str(value).strip()]


def _normalize_requirement(value: str) -> str:
    text = str(value or "").strip().lower()
    for char in ("-", " ", "."):
        text = text.replace(char, "_")
    return text.strip("_")


def _dedupe(values: list[Any] | tuple[Any, ...] | Any) -> list[str]:
    deduped: list[str] = []
    for value in values:
        text = str(value).strip()
        if text and text not in deduped:
            deduped.append(text)
    return deduped


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _error(error: str, details: dict[str, Any], payload: dict[str, Any] | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "command": COMMAND_NAME,
        "ok": False,
        "local_only": True,
        "error": error,
        "details": details,
    }
    if payload is not None:
        result["payload"] = payload
    return result
