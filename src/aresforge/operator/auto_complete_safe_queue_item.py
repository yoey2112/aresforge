from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.local_project_queue import resolve_project_queue_path
from aresforge.operator.machine_safety_gate_engine import evaluate_machine_safety_gates
from aresforge.operator.queue_completion_recommendation import recommend_queue_completion
from aresforge.operator.queue_transaction_log import append_queue_transaction, queue_transaction_warning

COMMAND_NAME = "auto-complete-safe-queue-item"
ACTION_TYPE = "auto_complete_safe_queue_item"
AUTO_COMPLETION_VERSION = "m132.1"

_ALLOWABLE_STATUSES = frozenset({"in_progress"})
_HIGH_RISK_TAGS = frozenset({"high-risk", "high_risk", "risk:high", "risk:critical", "critical-risk"})
_MANUAL_ONLY_TAGS = frozenset({"manual-only", "manual_only", "manual:only"})
_BLOCKER_TOKENS = ("blocker", "blocked", "failed", "failure", "error", "unable", "not run")

_BOUNDARY_CONFIRMATIONS = (
    "M132 auto-completion is local-only and queue-status-only.",
    "M132 requires parsed evidence, deterministic completion recommendation, and queue_status_mutation machine gates.",
    "M132 does not execute Codex, Codex CLI, local LLMs, remote LLMs, agents, GitHub, gh, network services, validation commands, or patches.",
    "M132 never auto-completes high-risk or manual-only tagged items.",
    "M132 does not start follow-on work or execute a next queue item.",
)


def auto_complete_safe_queue_item(
    config: AppConfig,
    *,
    item_id: str,
    evidence_path: str | Path | None = None,
    gate_profile: str = "queue_status_mutation",
    dry_run: bool = False,
    force: bool = False,
    queue_path: str | Path | None = None,
    output: str | Path | None = None,
    output_format: str = "json",
) -> dict[str, Any]:
    fmt = str(output_format or "json").strip().lower()
    if fmt != "json":
        return _error("invalid_format", {"format": output_format, "supported_formats": ["json"]})

    normalized_item_id = str(item_id or "").strip()
    normalized_gate_profile = str(gate_profile or "queue_status_mutation").strip()
    resolved_queue_path = resolve_project_queue_path(config.repo_root, queue_path)
    queue, queue_read_errors = _load_queue(resolved_queue_path)
    raw_item = _find_item(queue, normalized_item_id)
    previous_status = str(raw_item.get("status", "")).strip() if raw_item else ""

    evidence, resolved_evidence_path, evidence_errors = _load_or_find_evidence(
        config,
        item_id=normalized_item_id,
        evidence_path=evidence_path,
    )
    recommendation_result = _recommendation_for_evidence(
        config,
        item_id=normalized_item_id,
        evidence_path=resolved_evidence_path,
        queue_path=queue_path,
    )
    recommendation = recommendation_result.get("payload", {}) if isinstance(recommendation_result, dict) else {}
    gate_result = evaluate_machine_safety_gates(
        config,
        item_id=normalized_item_id,
        gate_profile=normalized_gate_profile,
        queue_path=queue_path,
        output_format="json",
    )
    machine_gate = gate_result.get("payload", {}) if isinstance(gate_result, dict) else {}

    blocked_reasons = _blocked_reasons(
        item=raw_item,
        previous_status=previous_status,
        queue_read_errors=queue_read_errors,
        evidence=evidence,
        evidence_path=resolved_evidence_path,
        evidence_errors=evidence_errors,
        recommendation=recommendation,
        gate_profile=normalized_gate_profile,
        machine_gate=machine_gate,
    )
    blocked = bool(blocked_reasons)
    transaction_log_entry: dict[str, Any] = {}
    transaction_warnings: list[str] = []
    queue_mutation_performed = False
    new_status = previous_status

    if not blocked and not dry_run:
        mutation_result = _perform_queue_mutation(
            config,
            queue=queue,
            item=raw_item,
            queue_path=resolved_queue_path,
            evidence=evidence,
            evidence_path=resolved_evidence_path,
            recommendation=recommendation,
        )
        if mutation_result["ok"]:
            queue_mutation_performed = True
            new_status = "done"
            transaction_log_entry = mutation_result["transaction_log_entry"]
            transaction_warnings = mutation_result["warnings"]
        else:
            blocked = True
            blocked_reasons.extend(mutation_result["blocked_reasons"])
            transaction_warnings = mutation_result["warnings"]

    payload = {
        "action_type": ACTION_TYPE,
        "auto_completion_version": AUTO_COMPLETION_VERSION,
        "item_id": normalized_item_id,
        "previous_status": previous_status,
        "new_status": new_status,
        "auto_completed": queue_mutation_performed,
        "dry_run": bool(dry_run),
        "blocked": blocked,
        "blocked_reasons": _dedupe(blocked_reasons),
        "machine_gates_checked": bool(machine_gate),
        "machine_gates_passed": bool(machine_gate.get("passed")) and not bool(machine_gate.get("blocked")),
        "evidence_used": {
            "path": str(resolved_evidence_path) if resolved_evidence_path else "",
            "evidence_record_type": str(evidence.get("evidence_record_type", "")).strip(),
            "commit_hash": str(evidence.get("commit_hash", "")).strip(),
            "tests_reported": _list(evidence.get("tests_reported")),
            "smoke_checks_reported": _list(evidence.get("smoke_checks_reported")),
            "recommendation_record_type": str(recommendation.get("recommendation_record_type", "")).strip(),
            "recommended_complete": bool(recommendation.get("recommended_complete")),
        },
        "transaction_log_entry": transaction_log_entry,
        "queue_mutation_performed": queue_mutation_performed,
        "local_only": True,
        "external_execution_performed": False,
        "model_execution_performed": False,
        "github_execution_performed": False,
        "patch_application_performed": False,
        "next_safe_action": _next_safe_action(
            blocked=blocked,
            dry_run=bool(dry_run),
            queue_mutation_performed=queue_mutation_performed,
        ),
        "gate_profile": normalized_gate_profile,
        "machine_gate_result": machine_gate,
        "completion_recommendation": recommendation,
        "transaction_warnings": transaction_warnings,
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
        "recorded_at": _now_iso(),
    }
    ok = (not blocked and dry_run) or queue_mutation_performed
    return _emit_or_write(config=config, payload=payload, ok=ok, output=output, force=force)


def _blocked_reasons(
    *,
    item: dict[str, Any],
    previous_status: str,
    queue_read_errors: list[str],
    evidence: dict[str, Any],
    evidence_path: Path | None,
    evidence_errors: list[str],
    recommendation: dict[str, Any],
    gate_profile: str,
    machine_gate: dict[str, Any],
) -> list[str]:
    reasons: list[str] = []
    reasons.extend(queue_read_errors)
    if not item:
        reasons.append("Queue item was not found.")
    if previous_status not in _ALLOWABLE_STATUSES:
        reasons.append(f"Queue item status is not allowable for auto-completion: {previous_status or 'missing'}.")
    tags = _tags(item)
    if tags.intersection(_HIGH_RISK_TAGS):
        reasons.append("Queue item is tagged high-risk.")
    if tags.intersection(_MANUAL_ONLY_TAGS):
        reasons.append("Queue item is tagged manual-only.")
    risk_level = str(item.get("routing_metadata", {}).get("risk_level", "") if isinstance(item.get("routing_metadata"), dict) else "").strip().lower()
    if risk_level in {"high", "critical"}:
        reasons.append(f"Queue item routing metadata risk_level is {risk_level}.")
    if _list(item.get("blocked_by")):
        reasons.append("Queue item has unresolved blocked_by entries.")
    if not evidence_path:
        reasons.append("Parsed dispatch evidence was not provided and could not be found.")
    reasons.extend(evidence_errors)
    reasons.extend(_evidence_blockers(evidence=evidence, item_id=str(item.get("item_id", "")).strip()))
    if not recommendation:
        reasons.append("Completion recommendation could not be generated.")
    elif recommendation.get("recommended_complete") is not True:
        reasons.append("Completion recommendation did not recommend completion.")
        reasons.extend(_list(recommendation.get("blocked_reasons")))
    if gate_profile != "queue_status_mutation":
        reasons.append("Auto-completion requires gate profile queue_status_mutation.")
    if not machine_gate:
        reasons.append("Machine safety gate result could not be generated.")
    elif machine_gate.get("passed") is not True or machine_gate.get("blocked") is True:
        reasons.append("Machine safety gate profile queue_status_mutation did not pass.")
        reasons.extend(_list(machine_gate.get("blocked_reasons")))
    return _dedupe(reasons)


def _evidence_blockers(*, evidence: dict[str, Any], item_id: str) -> list[str]:
    reasons: list[str] = []
    if not evidence:
        return ["Parsed dispatch evidence is missing."]
    if evidence.get("evidence_record_type") != "dispatch_result_evidence":
        reasons.append("Evidence record type is not dispatch_result_evidence.")
    if str(evidence.get("item_id", "")).strip() != item_id:
        reasons.append("Evidence item_id does not match the queue item.")
    if evidence.get("parsed") is not True:
        reasons.append("Evidence record was not parsed successfully.")
    if evidence.get("blocked") is True:
        reasons.append("Evidence record is blocked.")
    if evidence.get("local_only") is not True or evidence.get("execution_allowed") is not False:
        reasons.append("Evidence record does not preserve local_only=true and execution_allowed=false.")
    if not _reported_passed(_list(evidence.get("tests_reported"))):
        reasons.append("Required tests are not reported as passed.")
    if not _reported_passed(_list(evidence.get("smoke_checks_reported"))):
        reasons.append("Required smoke checks are not reported as passed.")
    if not str(evidence.get("commit_hash", "")).strip():
        reasons.append("Evidence commit_hash is missing.")
    severe = [entry for entry in _list(evidence.get("warnings_or_blockers")) if _looks_like_blocker(entry)]
    reasons.extend(f"Evidence reports blocker: {entry}" for entry in severe)
    return _dedupe(reasons)


def _perform_queue_mutation(
    config: AppConfig,
    *,
    queue: dict[str, Any],
    item: dict[str, Any],
    queue_path: Path,
    evidence: dict[str, Any],
    evidence_path: Path | None,
    recommendation: dict[str, Any],
) -> dict[str, Any]:
    try:
        previous_status = str(item.get("status", "")).strip()
        now = _now_iso()
        commit_hash = str(evidence.get("commit_hash", "")).strip()
        tests_run = _list(evidence.get("tests_reported"))
        changed_files = _list(evidence.get("files_changed"))
        artifact_paths = [str(evidence_path)] if evidence_path else []
        item["previous_status"] = previous_status
        item["status"] = "done"
        item["completed_at"] = now
        item["completed_by"] = ACTION_TYPE
        item["completion_commit"] = commit_hash
        item["validation_summary"] = _validation_summary(evidence)
        item["evidence_note"] = "Auto-completed from deterministic parsed evidence, completion recommendation, and queue_status_mutation machine gates."
        item["tests_run"] = tests_run
        item["changed_files"] = changed_files
        item["artifact_paths"] = _dedupe([*_list(item.get("artifact_paths")), *artifact_paths])
        item["updated_at"] = now
        queue["updated_at"] = now
        queue_path.write_text(json.dumps(queue, indent=2) + "\n", encoding="utf-8")
        transaction_result = append_queue_transaction(
            config,
            project_id=str(item.get("project_id", "")).strip(),
            item_id=str(item.get("item_id", "")).strip(),
            title=str(item.get("title", "")).strip(),
            previous_status=previous_status,
            new_status="done",
            mutation_type=ACTION_TYPE,
            actor=ACTION_TYPE,
            source=COMMAND_NAME,
            evidence_summary=item["validation_summary"],
            reason="Machine-gated auto-completion from deterministic local evidence.",
            queue_path=queue_path,
            metadata={
                "evidence_path": str(evidence_path) if evidence_path else "",
                "recommendation_record_type": str(recommendation.get("recommendation_record_type", "")).strip(),
                "commit_hash": commit_hash,
                "tests_run": tests_run,
                "changed_files": changed_files,
            },
        )
        warnings = queue_transaction_warning(transaction_result)
        if not transaction_result.get("ok"):
            return {
                "ok": False,
                "blocked_reasons": ["Transaction log could not record the mutation."],
                "warnings": warnings,
                "transaction_log_entry": {},
            }
        return {
            "ok": True,
            "blocked_reasons": [],
            "warnings": warnings,
            "transaction_log_entry": transaction_result.get("transaction", {}),
        }
    except OSError as exc:
        return {
            "ok": False,
            "blocked_reasons": [f"Queue mutation could not be written: {exc}"],
            "warnings": [],
            "transaction_log_entry": {},
        }


def _recommendation_for_evidence(
    config: AppConfig,
    *,
    item_id: str,
    evidence_path: Path | None,
    queue_path: str | Path | None,
) -> dict[str, Any]:
    if evidence_path is None:
        return {}
    return recommend_queue_completion(
        config,
        item_id=item_id,
        evidence_path=evidence_path,
        queue_path=queue_path,
        output_format="json",
    )


def _load_or_find_evidence(
    config: AppConfig,
    *,
    item_id: str,
    evidence_path: str | Path | None,
) -> tuple[dict[str, Any], Path | None, list[str]]:
    path = _resolve(config.repo_root, evidence_path) if evidence_path else _find_latest_evidence(config, item_id=item_id)
    if path is None:
        return {}, None, []
    if not path.exists():
        return {}, path, [f"Evidence file is missing: {path}"]
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {}, path, [f"Evidence file is not valid JSON: {exc.msg}."]
    except OSError as exc:
        return {}, path, [f"Evidence file could not be read: {exc}."]
    if not isinstance(raw, dict):
        return {}, path, ["Evidence file JSON root must be an object."]
    return raw, path, []


def _find_latest_evidence(config: AppConfig, *, item_id: str) -> Path | None:
    candidates: list[Path] = []
    for directory in (
        config.artifact_root / "dispatch_result_evidence",
        config.repo_root / "artifacts" / "dispatch_result_evidence",
        config.repo_root / ".aresforge" / "queue" / "evidence",
    ):
        if directory.exists():
            candidates.extend(path for path in directory.glob("*.json") if path.is_file())
    matching: list[Path] = []
    for path in candidates:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(raw, dict) and str(raw.get("item_id", "")).strip() == item_id and raw.get("evidence_record_type") == "dispatch_result_evidence":
            matching.append(path)
    if not matching:
        return None
    return sorted(matching, key=lambda path: path.stat().st_mtime, reverse=True)[0].resolve()


def _load_queue(path: Path) -> tuple[dict[str, Any], list[str]]:
    if not path.exists():
        return {}, [f"Queue file is missing: {path}"]
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {}, [f"Queue file is not valid JSON: {exc.msg}."]
    except OSError as exc:
        return {}, [f"Queue file could not be read: {exc}."]
    if not isinstance(raw, dict):
        return {}, ["Queue file JSON root must be an object."]
    return raw, []


def _find_item(queue: dict[str, Any], item_id: str) -> dict[str, Any]:
    items = queue.get("work_items", []) if isinstance(queue, dict) else []
    if not isinstance(items, list):
        return {}
    for item in items:
        if isinstance(item, dict) and str(item.get("item_id", "")).strip() == item_id:
            return item
    return {}


def _validation_summary(evidence: dict[str, Any]) -> str:
    changes = _list(evidence.get("what_changed"))
    tests = _list(evidence.get("tests_reported"))
    smoke = _list(evidence.get("smoke_checks_reported"))
    pieces = []
    if changes:
        pieces.append("Changes: " + "; ".join(changes))
    if tests:
        pieces.append("Tests: " + "; ".join(tests))
    if smoke:
        pieces.append("Smoke: " + "; ".join(smoke))
    return " ".join(pieces).strip() or "Deterministic evidence reported passing validation and smoke checks."


def _reported_passed(values: list[str]) -> bool:
    if not values:
        return False
    any_pass = False
    for value in values:
        lower = f" {value.lower()} "
        if any(token in lower for token in _BLOCKER_TOKENS):
            return False
        if any(token in lower for token in (" passed", "passed ", " pass", "success", "succeeded", "ok", "clean")):
            any_pass = True
    return any_pass


def _looks_like_blocker(value: str) -> bool:
    lower = value.lower()
    if "no blocker" in lower or "no blockers" in lower:
        return False
    return any(token in lower for token in _BLOCKER_TOKENS)


def _tags(item: dict[str, Any]) -> set[str]:
    return {str(tag).strip().lower() for tag in _list(item.get("tags"))}


def _list(value: Any) -> list[str]:
    if isinstance(value, list):
        return _dedupe(value)
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


def _resolve(repo_root: Path, value: str | Path | None) -> Path:
    path = Path(value or "")
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


def _next_safe_action(*, blocked: bool, dry_run: bool, queue_mutation_performed: bool) -> str:
    if queue_mutation_performed:
        return "Inspect the queue and transaction log before any further operator-gated action."
    if blocked:
        return "Resolve blocked reasons and re-run auto-completion in dry-run before mutating queue status."
    if dry_run:
        return "Dry-run passed; re-run without --dry-run to auto-complete this safe queue item."
    return "No queue mutation was performed."


def _emit_or_write(
    *,
    config: AppConfig,
    payload: dict[str, Any],
    ok: bool,
    output: str | Path | None,
    force: bool,
) -> dict[str, Any]:
    rendered = json.dumps(payload, indent=2)
    if output is None:
        return {
            "command": COMMAND_NAME,
            "ok": bool(ok),
            "local_only": True,
            "format": "json",
            "wrote_output_file": False,
            "stdout": rendered,
            "payload": payload,
        }
    output_path = _resolve(config.repo_root, output)
    if output_path.exists() and not force:
        blocked = dict(payload)
        blocked["blocked"] = True
        blocked["blocked_reasons"] = _dedupe(
            [*_list(blocked.get("blocked_reasons")), "Output file already exists. Re-run with --force to overwrite."]
        )
        rendered = json.dumps(blocked, indent=2)
        return {
            "command": COMMAND_NAME,
            "ok": False,
            "local_only": True,
            "format": "json",
            "output": str(output_path),
            "force": force,
            "wrote_output_file": False,
            "stdout": rendered,
            "payload": blocked,
        }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered + "\n", encoding="utf-8")
    return {
        "command": COMMAND_NAME,
        "ok": bool(ok),
        "local_only": True,
        "format": "json",
        "output": str(output_path),
        "force": force,
        "wrote_output_file": True,
        "payload": payload,
    }


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
