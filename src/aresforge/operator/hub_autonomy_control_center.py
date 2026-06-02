from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.durable_orchestration_run_store import read_orchestration_run_store
from aresforge.operator.github_issue_closure_recommendation_gate import recommend_github_issue_closure
from aresforge.operator.github_issue_sync_plan import plan_github_issue_sync
from aresforge.operator.local_project_queue import resolve_project_queue_path
from aresforge.operator.machine_safety_gate_engine import evaluate_machine_safety_gates
from aresforge.operator.operator_autonomy_configuration_profile import inspect_autonomy_profile
from aresforge.operator.orchestration_run_monitor import inspect_orchestration_run_monitor

COMMAND_NAME = "inspect-hub-autonomy-control-center-data"
RECORD_TYPE = "hub_autonomy_control_center_v1"
DEFAULT_PROJECT_ID = "aresforge"
DEFAULT_ITEM_ID = "m167-hub-autonomy-control-center-v1"
DEFAULT_AUTONOMY_PROFILE = "github_sync_dry_run"

_BOUNDARY_CONFIRMATIONS: tuple[str, ...] = (
    "The Hub Autonomy Control Center is a local read-only status surface unless an explicit output path is supplied.",
    "High-risk actions are surfaced only as dry-run or future-gated recommendations.",
    "No GitHub mutation, PR creation, PR merge, issue closure, Codex execution, model execution, source patch application, queue mutation, retry, resume, release, workflow mutation, force push, protected-branch update, or next-item execution is performed.",
)


def inspect_hub_autonomy_control_center_data(
    config: AppConfig,
    *,
    project_id: str = DEFAULT_PROJECT_ID,
    item_id: str = DEFAULT_ITEM_ID,
    run_id: str | None = None,
    queue_path: str | Path | None = None,
    history_path: str | Path | None = None,
    artifacts_root: str | Path | None = None,
    autonomy_profile: str = DEFAULT_AUTONOMY_PROFILE,
    output: str | Path | None = None,
    force: bool = False,
    output_format: str = "json",
) -> dict[str, Any]:
    fmt = _text(output_format).lower() or "json"
    if fmt != "json":
        return _error("invalid_format", {"format": output_format, "supported_formats": ["json"]})

    normalized_project_id = _text(project_id) or DEFAULT_PROJECT_ID
    normalized_item_id = _text(item_id) or DEFAULT_ITEM_ID
    normalized_run_id = _text(run_id)
    selected_profile = _text(autonomy_profile) or DEFAULT_AUTONOMY_PROFILE
    resolved_queue_path = resolve_project_queue_path(config.repo_root, queue_path)
    queue_result = _load_queue(resolved_queue_path)
    queue = queue_result.get("queue") if queue_result.get("ok") else {}
    item = _find_item(queue, normalized_item_id)

    autonomy_payload = _payload(
        inspect_autonomy_profile(
            config,
            project_id=normalized_project_id,
            item_id=normalized_item_id,
            autonomy_profile=selected_profile,
            queue_path=queue_path,
            output_format="json",
        )
    )
    run_store = read_orchestration_run_store(
        config,
        store_path=history_path,
        bootstrap_missing=False,
        project_id=normalized_project_id,
    )
    runs = _project_runs(run_store, project_id=normalized_project_id, item_id="", run_id=normalized_run_id)
    run_monitor_payload = _payload(
        inspect_orchestration_run_monitor(
            config,
            project_id=normalized_project_id,
            item_id=normalized_item_id if item else None,
            run_id=normalized_run_id or None,
            queue_path=queue_path,
            history_path=history_path,
            artifacts_root=artifacts_root,
            output_format="json",
        )
    )
    issue_sync_payload = _payload(
        plan_github_issue_sync(
            config,
            project_id=normalized_project_id,
            item_id=normalized_item_id,
            queue_path=queue_path,
            output_format="json",
        )
    )
    closure_payload = _payload(
        recommend_github_issue_closure(
            config,
            item_id=normalized_item_id,
            project_id=normalized_project_id,
            queue_path=queue_path,
            run_id=normalized_run_id,
            autonomy_profile=selected_profile,
            output_format="json",
        )
    )
    gates = [
        _gate_summary(
            _gate_payload(config, item_id=normalized_item_id, gate_profile="read_only_agent", queue_path=queue_path),
            required_for_control_center=True,
        ),
        _gate_summary(
            _gate_payload(
                config,
                item_id=normalized_item_id,
                gate_profile="operator_autonomy_profile",
                queue_path=queue_path,
            ),
            required_for_control_center=True,
        ),
        _gate_summary(
            _gate_payload(config, item_id=normalized_item_id, gate_profile="github_sync", queue_path=queue_path),
            required_for_control_center=False,
        ),
    ]
    required_gates = [gate for gate in gates if bool(gate.get("required_for_control_center"))]
    evidence = _evidence_bundles(config, project_id=normalized_project_id, item_id=normalized_item_id)
    pr_summaries = _pr_draft_summaries(config, project_id=normalized_project_id, item_id=normalized_item_id)
    blocked_reasons = _dedupe(
        [
            *queue_result.get("blocked_reasons", []),
            *_list(autonomy_payload.get("blocked_reasons")),
            *_list(issue_sync_payload.get("blocked_reasons")),
            *(reason for gate in required_gates for reason in _list(gate.get("blocked_reasons"))),
        ]
    )
    warnings = _dedupe(
        [
            *queue_result.get("warnings", []),
            *_list(autonomy_payload.get("warnings")),
            *_list(run_store.get("warnings")),
            *_list(run_monitor_payload.get("warnings")),
            *_list(issue_sync_payload.get("warnings")),
            *_list(closure_payload.get("warnings")),
            *_control_center_warnings(item=item, runs=runs, evidence=evidence, pr_summaries=pr_summaries),
        ]
    )
    blocked = bool(blocked_reasons)
    payload: dict[str, Any] = {
        "record_type": RECORD_TYPE,
        "artifact_type": RECORD_TYPE,
        "generated": True,
        "generated_at": _now_iso(),
        "project_id": normalized_project_id,
        "item_id": normalized_item_id,
        "run_id": normalized_run_id,
        "status": "blocked" if blocked else "control_center_ready",
        "blocked": blocked,
        "blocked_reasons": blocked_reasons,
        "warnings": warnings,
        "machine_gates_checked": gates,
        "machine_gates_passed": bool(required_gates) and all(bool(gate.get("passed")) for gate in required_gates) and not blocked,
        "autonomy_profile": selected_profile,
        "artifacts_created": [],
        "mutation_performed": False,
        "queue_mutation_performed": False,
        "codex_execution_performed": False,
        "model_execution_performed": False,
        "github_execution_performed": False,
        "patch_application_performed": False,
        "local_only": True,
        "next_safe_action": _next_safe_action(blocked=blocked, item=item, evidence=evidence, pr_summaries=pr_summaries),
        "queue_path": str(resolved_queue_path),
        "queue_item": _queue_item_summary(item, normalized_item_id),
        "autonomy_profile_summary": _autonomy_profile_summary(autonomy_payload),
        "run_store_status": _run_store_status(run_store, runs),
        "orchestration_runs": _run_summaries(runs),
        "orchestration_run_monitor": _run_monitor_summary(run_monitor_payload),
        "evidence_bundles": evidence,
        "github_sync_status": _github_sync_status(issue_sync_payload),
        "issue_closure_recommendations": _issue_closure_summary(closure_payload),
        "pr_draft_summaries": pr_summaries,
        "machine_gate_summary": _machine_gate_summary(gates),
        "next_safe_actions": _next_safe_actions(
            blocked=blocked,
            issue_sync_payload=issue_sync_payload,
            closure_payload=closure_payload,
            pr_summaries=pr_summaries,
        ),
        "dry_run_labels": [
            "github_issue_sync_dry_run",
            "issue_closure_recommendation_only",
            "pr_draft_summary_review_only",
            "orchestration_run_monitor_read_only",
        ],
        "unsafe_actions_available": False,
        "github_mutation_allowed": False,
        "codex_execution_allowed": False,
        "model_execution_allowed": False,
        "source_patch_application_allowed": False,
        "queue_mutation_allowed": False,
        "hub_visibility": {
            "api_endpoint": "/api/autonomy/control-center",
            "operator_cli": "python -m aresforge inspect-hub-autonomy-control-center-data --project-id "
            + normalized_project_id
            + " --format json",
            "local_only": True,
        },
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }
    return _emit_or_write(config=config, payload=payload, output=output, force=force)


def _run_store_status(run_store: dict[str, Any], runs: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": "ready" if run_store.get("ok") else "blocked",
        "store_path": _text(run_store.get("store_path")),
        "store_schema_valid": bool(run_store.get("schema_valid")),
        "bootstrap_performed": bool(run_store.get("bootstrap_performed")),
        "store_record_count": len(_dicts(run_store.get("records"))),
        "project_run_count": len(runs),
        "errors": _list(run_store.get("errors")),
        "warnings": _list(run_store.get("warnings")),
    }


def _project_runs(run_store: dict[str, Any], *, project_id: str, item_id: str, run_id: str) -> list[dict[str, Any]]:
    records = []
    for record in _dicts(run_store.get("records")):
        if _text(record.get("project_id")) != project_id:
            continue
        if item_id and _text(record.get("item_id")) != item_id:
            continue
        if run_id and _text(record.get("run_id")) != run_id:
            continue
        records.append(record)
    return list(reversed(records))


def _run_summaries(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "record_type": _text(run.get("record_type")) or "orchestration_run_history_record",
            "run_id": _text(run.get("run_id")),
            "item_id": _text(run.get("item_id")),
            "project_id": _text(run.get("project_id")),
            "status": _text(run.get("status")),
            "blocked": bool(run.get("blocked")),
            "blocked_reasons": _list(run.get("blocked_reasons")),
            "machine_gates_passed": bool(run.get("machine_gates_passed")),
            "artifacts_created": _list(run.get("artifacts_created")),
            "next_safe_action": _text(run.get("next_safe_action")),
        }
        for run in runs[:10]
    ]


def _run_monitor_summary(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "record_type": _text(payload.get("record_type")),
        "status": _text(payload.get("status")),
        "run_id": _text(payload.get("run_id")),
        "blocked": bool(payload.get("blocked")),
        "blocked_reasons": _list(payload.get("blocked_reasons")),
        "machine_gates_passed": bool(payload.get("machine_gates_passed")),
        "history_summary": payload.get("history_summary", {}) if isinstance(payload.get("history_summary"), dict) else {},
        "recovery_summary": payload.get("recovery_summary", {}) if isinstance(payload.get("recovery_summary"), dict) else {},
        "next_safe_action": _text(payload.get("next_safe_action")),
    }


def _github_sync_status(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "record_type": _text(payload.get("record_type")),
        "status": _text(payload.get("status")),
        "blocked": bool(payload.get("blocked")),
        "blocked_reasons": _list(payload.get("blocked_reasons")),
        "machine_gates_passed": bool(payload.get("machine_gates_passed")),
        "operation_counts": payload.get("operation_counts", {}) if isinstance(payload.get("operation_counts"), dict) else {},
        "operation_recommendations": _recommendation_summaries(payload.get("operation_recommendations")),
        "mutation_allowed": False,
        "github_execution_performed": False,
        "next_safe_action": _text(payload.get("next_safe_action")),
    }


def _issue_closure_summary(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "record_type": _text(payload.get("record_type")),
        "status": _text(payload.get("status")),
        "blocked": bool(payload.get("blocked")),
        "blocked_reasons": _list(payload.get("blocked_reasons")),
        "closure_recommended": bool(payload.get("closure_recommended")),
        "issue_closure_allowed": False,
        "issue_closed": False,
        "linked_issue": payload.get("linked_issue", {}) if isinstance(payload.get("linked_issue"), dict) else {},
        "linked_issue_state": _text(payload.get("linked_issue_state")),
        "github_execution_performed": False,
        "next_safe_action": _text(payload.get("next_safe_action")),
    }


def _recommendation_summaries(value: Any) -> list[dict[str, Any]]:
    return [
        {
            "item_id": _text(entry.get("item_id")),
            "recommended_action": _text(entry.get("recommended_action")),
            "issue_number": entry.get("issue_number"),
            "reason": _text(entry.get("reason")),
            "dry_run_label": "dry_run_only",
            "github_execution_performed": False,
        }
        for entry in _dicts(value)
    ][:20]


def _evidence_bundles(config: AppConfig, *, project_id: str, item_id: str) -> list[dict[str, Any]]:
    roots = [
        config.repo_root / ".aresforge" / "codex_loop_validation_evidence",
        config.repo_root / ".aresforge" / "github_issue_closure_recommendations",
        config.repo_root / ".aresforge" / "github_issue_status_comments",
    ]
    entries: list[dict[str, Any]] = []
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.json"), key=lambda candidate: candidate.stat().st_mtime, reverse=True):
            summary = _artifact_summary(path, project_id=project_id, item_id=item_id)
            if summary:
                entries.append(summary)
            if len(entries) >= 20:
                return entries
    return entries


def _pr_draft_summaries(config: AppConfig, *, project_id: str, item_id: str) -> list[dict[str, Any]]:
    root = config.repo_root / ".aresforge" / "pr_draft_summaries"
    if not root.exists():
        return []
    entries: list[dict[str, Any]] = []
    for path in sorted(root.glob("*.json"), key=lambda candidate: candidate.stat().st_mtime, reverse=True):
        summary = _artifact_summary(path, project_id=project_id, item_id=item_id)
        if summary:
            summary["dry_run_label"] = "review_only_no_pr_created"
            entries.append(summary)
        if len(entries) >= 10:
            break
    return entries


def _artifact_summary(path: Path, *, project_id: str, item_id: str) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(raw, dict):
        return {}
    raw_project = _text(raw.get("project_id"))
    raw_item = _text(raw.get("item_id"))
    if raw_project and raw_project != project_id:
        return {}
    if item_id and raw_item and raw_item != item_id:
        return {}
    return {
        "artifact_type": _text(raw.get("artifact_type") or raw.get("record_type")) or "local_json_artifact",
        "record_type": _text(raw.get("record_type")),
        "path": str(path),
        "project_id": raw_project,
        "item_id": raw_item,
        "run_id": _text(raw.get("run_id")),
        "status": _text(raw.get("status")),
        "blocked": bool(raw.get("blocked")),
        "blocked_reasons": _list(raw.get("blocked_reasons")),
        "machine_gates_passed": bool(raw.get("machine_gates_passed")),
        "github_execution_performed": bool(raw.get("github_execution_performed")),
        "codex_execution_performed": bool(raw.get("codex_execution_performed")),
        "model_execution_performed": bool(raw.get("model_execution_performed")),
        "patch_application_performed": bool(raw.get("patch_application_performed")),
        "local_only": bool(raw.get("local_only", True)),
        "next_safe_action": _text(raw.get("next_safe_action")),
    }


def _queue_item_summary(item: dict[str, Any], item_id: str) -> dict[str, Any]:
    return {
        "item_id": _text(item.get("item_id")) or item_id,
        "found": bool(item),
        "status": _text(item.get("status")),
        "title": _text(item.get("title")),
        "dependencies": _list(item.get("dependencies")) + _list(item.get("depends_on")),
        "blocked_by": _list(item.get("blocked_by")),
        "completion_commit": _text(item.get("completion_commit")),
    }


def _autonomy_profile_summary(payload: dict[str, Any]) -> dict[str, Any]:
    selected = payload.get("selected_profile", {}) if isinstance(payload.get("selected_profile"), dict) else {}
    return {
        "record_type": _text(payload.get("record_type")),
        "status": _text(payload.get("status")),
        "blocked": bool(payload.get("blocked")),
        "machine_gates_passed": bool(payload.get("machine_gates_passed")),
        "autonomy_profile": _text(payload.get("autonomy_profile")),
        "profile_display_name": _text(selected.get("display_name")),
        "risk_level": _text(selected.get("risk_level")),
        "capability_status_counts": selected.get("capability_status_counts", {})
        if isinstance(selected.get("capability_status_counts"), dict)
        else {},
        "next_safe_action": _text(payload.get("next_safe_action")),
    }


def _machine_gate_summary(gates: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [gate for gate in gates if not bool(gate.get("passed"))]
    return {
        "gate_count": len(gates),
        "gates_passed": len(gates) - len(failed),
        "gates_failed": len(failed),
        "failed_gate_profiles": _dedupe(_text(gate.get("gate_profile")) for gate in failed),
        "blocked_reasons": _dedupe(reason for gate in gates for reason in _list(gate.get("blocked_reasons"))),
    }


def _next_safe_actions(
    *,
    blocked: bool,
    issue_sync_payload: dict[str, Any],
    closure_payload: dict[str, Any],
    pr_summaries: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    actions = [
        {
            "action_id": "review_autonomy_profile",
            "label": "Review autonomy profile",
            "dry_run": True,
            "safe": True,
            "command": "python -m aresforge inspect-autonomy-profile --project-id aresforge --format json",
        },
        {
            "action_id": "review_github_issue_sync_plan",
            "label": "Review GitHub issue sync plan",
            "dry_run": True,
            "safe": True,
            "command": "python -m aresforge plan-github-issue-sync --project-id aresforge --format json",
        },
    ]
    if closure_payload:
        actions.append(
            {
                "action_id": "review_issue_closure_recommendation",
                "label": "Review issue closure recommendation",
                "dry_run": True,
                "safe": True,
                "command": "python -m aresforge recommend-github-issue-closure --item-id "
                + _text(closure_payload.get("item_id"))
                + " --format json",
            }
        )
    if pr_summaries:
        actions.append(
            {
                "action_id": "review_latest_pr_draft_summary",
                "label": "Review latest PR draft summary artifact",
                "dry_run": True,
                "safe": True,
                "artifact_path": pr_summaries[0].get("path", ""),
            }
        )
    elif not blocked:
        actions.append(
            {
                "action_id": "generate_pr_draft_summary_artifact",
                "label": "Generate PR draft summary artifact",
                "dry_run": True,
                "safe": True,
                "command": "python -m aresforge generate-pr-draft-summary --item-id <item-id> --format json",
            }
        )
    if issue_sync_payload.get("blocked"):
        actions.append(
            {
                "action_id": "resolve_github_sync_plan_blockers",
                "label": "Resolve GitHub sync plan blockers",
                "dry_run": True,
                "safe": True,
                "blocked_reasons": _list(issue_sync_payload.get("blocked_reasons")),
            }
        )
    return actions


def _next_safe_action(
    *,
    blocked: bool,
    item: dict[str, Any],
    evidence: list[dict[str, Any]],
    pr_summaries: list[dict[str, Any]],
) -> str:
    if blocked:
        return "Resolve control-center machine gate or local queue blockers before relying on autonomy recommendations."
    if not item:
        return "Add or inspect the M167 queue item, then refresh the control center."
    if not evidence:
        return "Review dry-run autonomy and GitHub sync status; create local evidence through explicit milestone commands only."
    if not pr_summaries:
        return "Generate or review a local PR draft summary artifact; PR creation remains blocked."
    return "Review local evidence, gates, and dry-run recommendations before any separate explicitly gated action."


def _control_center_warnings(
    *,
    item: dict[str, Any],
    runs: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
    pr_summaries: list[dict[str, Any]],
) -> list[str]:
    warnings = ["Autonomy Control Center recommendations are status-only and do not authorize mutation."]
    if not item:
        warnings.append("Requested queue item was not found; control center still reports project-level autonomy status.")
    if not runs:
        warnings.append("No durable orchestration runs were found for the selected project/run filter.")
    if not evidence:
        warnings.append("No local evidence bundles were discovered for the selected item.")
    if not pr_summaries:
        warnings.append("No PR draft summary artifacts were discovered for the selected item.")
    return warnings


def _gate_payload(config: AppConfig, *, item_id: str, gate_profile: str, queue_path: str | Path | None) -> dict[str, Any]:
    return _payload(
        evaluate_machine_safety_gates(
            config,
            item_id=item_id,
            gate_profile=gate_profile,
            queue_path=queue_path,
            output_format="json",
        )
    )


def _gate_summary(gate_payload: dict[str, Any], *, required_for_control_center: bool) -> dict[str, Any]:
    checks = gate_payload.get("checks", [])
    failed = [
        _text(check.get("check_id"))
        for check in checks
        if isinstance(check, dict) and not bool(check.get("passed")) and not bool(check.get("warning_only"))
    ]
    return {
        "gate_profile": _text(gate_payload.get("gate_profile") or gate_payload.get("profile")) or "read_only_agent",
        "passed": bool(gate_payload.get("passed")) and not bool(gate_payload.get("blocked")),
        "blocked": bool(gate_payload.get("blocked")),
        "blocked_reasons": _list(gate_payload.get("blocked_reasons")),
        "checks_failed": failed,
        "required_for_control_center": required_for_control_center,
        "dry_run_label": "required_read_only_gate" if required_for_control_center else "future_action_gate_status_only",
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
    for item in _dicts(queue.get("work_items")):
        if _text(item.get("item_id")) == item_id:
            return item
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
        blocked["blocked"] = True
        blocked["blocked_reasons"] = _dedupe(
            [*_list(blocked.get("blocked_reasons")), "Output file already exists. Re-run with --force to overwrite."]
        )
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
        "payload": artifact_payload,
    }


def _payload(result: dict[str, Any]) -> dict[str, Any]:
    payload = result.get("payload", {}) if isinstance(result, dict) else {}
    return payload if isinstance(payload, dict) else {}


def _resolve(repo_root: Path, value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


def _text(value: Any) -> str:
    return str(value or "").strip()


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
