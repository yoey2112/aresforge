from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.github_issue_sync_plan import plan_github_issue_sync
from aresforge.operator.local_project_queue import resolve_project_queue_path
from aresforge.operator.machine_safety_gate_engine import evaluate_machine_safety_gates
from aresforge.operator.operator_autonomy_configuration_profile import inspect_autonomy_profile

COMMAND_NAME = "recommend-github-issue-closure"
RECORD_TYPE = "github_issue_closure_recommendation_gate_v1"
DEFAULT_PROJECT_ID = "aresforge"
DEFAULT_AUTONOMY_PROFILE = "github_sync_dry_run"

_BOUNDARY_CONFIRMATIONS: tuple[str, ...] = (
    "This command recommends close or keep-open only; it never closes GitHub issues.",
    "Closure recommendation requires local queue done status, validation evidence, artifact evidence, linked issue metadata, and passing machine gates.",
    "Linked issue state is read only from local queue metadata or explicit operator input; no live GitHub lookup is performed.",
    "Future issue closure remains blocked until a separate explicitly enabled close gate exists.",
    "No queue mutation, Codex execution, model execution, source patch application, GitHub mutation, PR merge, protected branch update, force push, auto-merge, release, workflow mutation, retry, resume, or next-item execution is performed.",
)


def recommend_github_issue_closure(
    config: AppConfig,
    *,
    item_id: str,
    project_id: str = DEFAULT_PROJECT_ID,
    queue_path: str | Path | None = None,
    run_id: str | None = None,
    autonomy_profile: str = DEFAULT_AUTONOMY_PROFILE,
    linked_issue_state: str | None = None,
    output: str | Path | None = None,
    force: bool = False,
    output_format: str = "json",
) -> dict[str, Any]:
    fmt = _text(output_format).lower() or "json"
    if fmt != "json":
        return _error("invalid_format", {"format": output_format, "supported_formats": ["json"]})

    normalized_item_id = _text(item_id)
    normalized_project_id = _text(project_id) or DEFAULT_PROJECT_ID
    selected_autonomy_profile = _text(autonomy_profile) or DEFAULT_AUTONOMY_PROFILE
    generated_at = _now_iso()
    resolved_queue_path = resolve_project_queue_path(config.repo_root, queue_path)

    queue_result = _load_queue(resolved_queue_path)
    queue = queue_result.get("queue") if queue_result.get("ok") else {}
    item = _find_item(queue, normalized_item_id)
    item_project_id = _text(item.get("project_id")) or normalized_project_id

    plan_payload = _payload(
        plan_github_issue_sync(
            config,
            project_id=item_project_id,
            item_id=normalized_item_id,
            queue_path=queue_path,
            output_format="json",
        )
    )
    item_plan = _item_plan(plan_payload, normalized_item_id)
    linked_issue = item_plan.get("linked_issue") if isinstance(item_plan.get("linked_issue"), dict) else {}
    local_issue_state = _linked_issue_state(item=item, linked_issue=linked_issue, explicit_state=linked_issue_state)
    validation_evidence = _validation_evidence(item)
    artifact_bundle = _artifact_bundle(item)
    queue_completion = _queue_completion(queue=queue, item=item)

    gate_payload = _payload(
        evaluate_machine_safety_gates(
            config,
            item_id=normalized_item_id,
            gate_profile="read_only_agent",
            queue_path=queue_path,
            output_format="json",
        )
    )
    gate_summary = _gate_summary(gate_payload)
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

    blocked_reasons = _blocked_reasons(
        queue_result=queue_result,
        item=item,
        item_plan=item_plan,
        plan_payload=plan_payload,
        linked_issue=linked_issue,
        local_issue_state=local_issue_state,
        validation_evidence=validation_evidence,
        artifact_bundle=artifact_bundle,
        queue_completion=queue_completion,
        gate_payload=gate_payload,
        autonomy_payload=autonomy_payload,
    )
    warnings = _warnings(
        queue_result=queue_result,
        item=item,
        plan_payload=plan_payload,
        item_plan=item_plan,
        gate_payload=gate_payload,
        autonomy_payload=autonomy_payload,
        artifact_bundle=artifact_bundle,
        local_issue_state=local_issue_state,
    )

    closure_recommended = not blocked_reasons
    already_closed = local_issue_state == "closed"
    recommendation = "close" if closure_recommended else "keep_open"
    status = "close_recommended" if closure_recommended else "keep_open_recommended"

    payload: dict[str, Any] = {
        "record_type": RECORD_TYPE,
        "artifact_type": RECORD_TYPE,
        "generated": True,
        "generated_at": generated_at,
        "project_id": item_project_id,
        "item_id": normalized_item_id,
        "run_id": _text(run_id),
        "status": status,
        "blocked": bool(blocked_reasons),
        "blocked_reasons": _dedupe(blocked_reasons),
        "warnings": _dedupe(warnings),
        "machine_gates_checked": [gate_summary],
        "machine_gates_passed": bool(gate_summary.get("passed")) and not bool(gate_summary.get("blocked")),
        "autonomy_profile": selected_autonomy_profile,
        "artifacts_created": [],
        "mutation_performed": False,
        "queue_mutation_performed": False,
        "codex_execution_performed": False,
        "model_execution_performed": False,
        "github_execution_performed": False,
        "patch_application_performed": False,
        "local_only": True,
        "next_safe_action": _next_safe_action(closure_recommended=closure_recommended, already_closed=already_closed),
        "queue_path": str(resolved_queue_path),
        "queue_item_found": bool(item),
        "queue_completion": queue_completion,
        "validation_evidence": validation_evidence,
        "artifact_bundle": artifact_bundle,
        "linked_issue": linked_issue or {"linked": False, "issue_number": None, "issue_url": "", "metadata_source": ""},
        "linked_issue_state": local_issue_state,
        "issue_closure_recommendation": recommendation,
        "closure_recommended": closure_recommended,
        "keep_open_recommended": not closure_recommended,
        "issue_closure_allowed": False,
        "issue_closed": False,
        "closure_mutation_enabled": False,
        "future_enabled_gate_required": True,
        "recommendation_inputs": {
            "queue_done": bool(queue_completion.get("done")),
            "dependencies_done": bool(queue_completion.get("dependencies_done")),
            "validation_evidence_present": bool(validation_evidence.get("present")),
            "artifact_bundle_present": bool(artifact_bundle.get("present")),
            "linked_issue_present": bool(linked_issue.get("linked")),
            "linked_issue_state": local_issue_state,
            "machine_gates_passed": bool(gate_summary.get("passed")) and not bool(gate_summary.get("blocked")),
            "autonomy_profile_inspected": bool(autonomy_payload),
        },
        "autonomy_profile_summary": _autonomy_summary(autonomy_payload),
        "source_plan_summary": _source_plan_summary(plan_payload, item_plan),
        "github_mutation_scope": "none_recommendation_only",
        "github_operations_blocked": [
            "close_issue",
            "bulk_issue_closure",
            "create_or_update_issue",
            "create_or_update_comment",
            "merge_pull_request",
            "force_push",
            "update_protected_branch",
            "enable_auto_merge",
            "create_release",
            "modify_github_workflow",
        ],
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
        "completed_at": _now_iso(),
    }
    return _emit_or_write(config=config, payload=payload, output=output, force=force)


def _blocked_reasons(
    *,
    queue_result: dict[str, Any],
    item: dict[str, Any],
    item_plan: dict[str, Any],
    plan_payload: dict[str, Any],
    linked_issue: dict[str, Any],
    local_issue_state: str,
    validation_evidence: dict[str, Any],
    artifact_bundle: dict[str, Any],
    queue_completion: dict[str, Any],
    gate_payload: dict[str, Any],
    autonomy_payload: dict[str, Any],
) -> list[str]:
    reasons = [*queue_result.get("blocked_reasons", [])]
    if not queue_result.get("ok"):
        reasons.append("Local queue must be readable before issue closure can be recommended.")
    if not item:
        reasons.append("Queue item must exist before issue closure can be recommended.")
    if item and not queue_completion.get("done"):
        reasons.append("Queue item status must be done before issue closure can be recommended.")
    if item and not queue_completion.get("dependencies_done"):
        reasons.append("All queue dependencies must be done before issue closure can be recommended.")
    if item and _list(item.get("blocked_by")):
        reasons.append("Queue item has blocked_by entries.")
    if not validation_evidence.get("present"):
        reasons.append("Validation evidence is required before issue closure can be recommended.")
    if not artifact_bundle.get("present"):
        reasons.append("Artifact bundle or artifact evidence is required before issue closure can be recommended.")
    if not item_plan:
        reasons.append("Queue item must be present in the GitHub issue sync plan.")
    if bool(item_plan.get("blocked")):
        reasons.extend(_list(item_plan.get("blocked_reasons")))
    if bool(plan_payload.get("blocked")):
        reasons.extend(_list(plan_payload.get("blocked_reasons")))
    if not linked_issue.get("linked"):
        reasons.append("Linked GitHub issue metadata is required before issue closure can be recommended.")
    if local_issue_state in {"closed"}:
        reasons.append("Linked issue is already closed; no closure recommendation is needed.")
    elif local_issue_state not in {"open", "unknown"}:
        reasons.append(f"Linked issue state is not safe for closure recommendation: {local_issue_state or 'missing'}.")
    if gate_payload.get("passed") is not True or gate_payload.get("blocked") is True:
        reasons.append("Issue closure recommendation machine gate did not pass.")
        reasons.extend(_list(gate_payload.get("blocked_reasons")))
    if autonomy_payload.get("blocked") is True or autonomy_payload.get("machine_gates_passed") is not True:
        reasons.append("Autonomy profile inspection did not pass required machine gates.")
        reasons.extend(_list(autonomy_payload.get("blocked_reasons")))
    return _dedupe(reasons)


def _warnings(
    *,
    queue_result: dict[str, Any],
    item: dict[str, Any],
    plan_payload: dict[str, Any],
    item_plan: dict[str, Any],
    gate_payload: dict[str, Any],
    autonomy_payload: dict[str, Any],
    artifact_bundle: dict[str, Any],
    local_issue_state: str,
) -> list[str]:
    warnings = [
        *queue_result.get("warnings", []),
        *_list(plan_payload.get("warnings")),
        *_list(item_plan.get("warnings")),
        *_list(gate_payload.get("warnings")),
        *_list(autonomy_payload.get("warnings")),
        *_list(artifact_bundle.get("warnings")),
    ]
    if local_issue_state == "unknown":
        warnings.append("Linked issue state is unknown from local metadata; recommendation assumes the issue is still open and requires operator review.")
    if item and not _text(item.get("completion_commit")):
        warnings.append("Queue item has no completion_commit recorded.")
    return _dedupe(warnings)


def _queue_completion(*, queue: dict[str, Any], item: dict[str, Any]) -> dict[str, Any]:
    dependencies = _list(item.get("dependencies")) + _list(item.get("depends_on"))
    by_id = {
        _text(candidate.get("item_id")): candidate
        for candidate in queue.get("work_items", [])
        if isinstance(candidate, dict)
    }
    dependency_states = [
        {"item_id": dep, "status": _text(by_id.get(dep, {}).get("status")) or "missing"}
        for dep in dependencies
    ]
    dependencies_done = all(entry["status"] == "done" for entry in dependency_states)
    return {
        "status": _text(item.get("status")),
        "done": _text(item.get("status")) == "done",
        "completed_at": _text(item.get("completed_at")),
        "completed_by": _text(item.get("completed_by")),
        "completion_commit": _text(item.get("completion_commit")),
        "dependencies": dependency_states,
        "dependencies_done": dependencies_done,
        "blocked_by": _list(item.get("blocked_by")),
    }


def _validation_evidence(item: dict[str, Any]) -> dict[str, Any]:
    tests_run = _list(item.get("tests_run"))
    summary = _text(item.get("validation_summary"))
    evidence_note = _text(item.get("evidence_note"))
    completion = item.get("completion_evidence") if isinstance(item.get("completion_evidence"), dict) else {}
    present = bool(summary and tests_run) or bool(completion.get("validation_evidence")) or bool(completion.get("tests_run"))
    return {
        "present": present,
        "validation_summary": summary,
        "tests_run": tests_run,
        "evidence_note": evidence_note,
        "completion_evidence_keys": sorted(str(key) for key in completion.keys()),
    }


def _artifact_bundle(item: dict[str, Any]) -> dict[str, Any]:
    paths = _list(item.get("artifact_paths"))
    completion = item.get("completion_evidence") if isinstance(item.get("completion_evidence"), dict) else {}
    artifacts_created = _list(completion.get("artifacts_created"))
    if not artifacts_created and _text(completion.get("artifact_path")):
        artifacts_created = [_text(completion.get("artifact_path"))]
    warnings: list[str] = []
    if paths and not any("bundle" in path.lower() or ".aresforge" in path.lower() or "artifacts/" in path.lower() for path in paths):
        warnings.append("Artifact paths are present but do not look like a durable local evidence bundle.")
    return {
        "present": bool(paths or artifacts_created),
        "artifact_paths": _dedupe([*paths, *artifacts_created]),
        "warnings": warnings,
    }


def _linked_issue_state(*, item: dict[str, Any], linked_issue: dict[str, Any], explicit_state: str | None) -> str:
    candidates = [
        explicit_state,
        linked_issue.get("state"),
        item.get("github_issue_state"),
        item.get("issue_state"),
    ]
    github_issue = item.get("github_issue")
    if isinstance(github_issue, dict):
        candidates.extend([github_issue.get("state"), github_issue.get("issue_state")])
    github = item.get("github")
    if isinstance(github, dict):
        candidates.extend([github.get("state"), github.get("issue_state")])
    for candidate in candidates:
        text = _text(candidate).lower()
        if text:
            return text
    return "unknown"


def _payload(result: dict[str, Any]) -> dict[str, Any]:
    payload = result.get("payload", {}) if isinstance(result, dict) else {}
    return payload if isinstance(payload, dict) else {}


def _item_plan(plan_payload: dict[str, Any], item_id: str) -> dict[str, Any]:
    for entry in plan_payload.get("issue_sync_items", []):
        if isinstance(entry, dict) and _text(entry.get("item_id")) == item_id:
            return entry
    return {}


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


def _source_plan_summary(plan_payload: dict[str, Any], item_plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "record_type": _text(plan_payload.get("record_type")),
        "status": _text(plan_payload.get("status")),
        "machine_gates_passed": bool(plan_payload.get("machine_gates_passed")),
        "item_recommendations": item_plan.get("recommendations", []),
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


def _next_safe_action(*, closure_recommended: bool, already_closed: bool) -> str:
    if already_closed:
        return "No issue closure is needed; linked issue metadata says the issue is already closed."
    if closure_recommended:
        return "Operator may review this recommendation; actual issue closure requires a future explicit machine-gated close command."
    return "Keep the issue open and resolve blocked reasons before considering any separate issue closure path."


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
            "ok": True,
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
        blocked["blocked"] = True
        blocked["blocked_reasons"] = _dedupe(
            [*_list(blocked.get("blocked_reasons")), "Output file already exists. Re-run with --force to overwrite."]
        )
        blocked["closure_recommended"] = False
        blocked["keep_open_recommended"] = True
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
        "ok": True,
        "local_only": True,
        "format": "json",
        "output": str(output_path),
        "force": force,
        "wrote_output_file": True,
        "payload": artifact_payload,
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


def _resolve(repo_root: Path, value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


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
