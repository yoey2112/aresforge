from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.codex_loop_validation_evidence_bundle import bundle_codex_loop_validation_evidence
from aresforge.operator.durable_orchestration_run_store import append_orchestration_run_record
from aresforge.operator.github_issue_closure_recommendation_gate import recommend_github_issue_closure
from aresforge.operator.github_issue_sync_plan import plan_github_issue_sync
from aresforge.operator.local_project_queue import resolve_project_queue_path
from aresforge.operator.machine_safety_gate_engine import evaluate_machine_safety_gates
from aresforge.operator.multi_agent_orchestrator import run_multi_agent_orchestration
from aresforge.operator.operator_autonomy_configuration_profile import inspect_autonomy_profile
from aresforge.operator.pull_request_draft_summary_generator import generate_pr_draft_summary

COMMAND_NAME = "run-self-managed-project-loop"
RECORD_TYPE = "self_managed_aresforge_project_loop_dry_run_v1"
DEFAULT_PROJECT_ID = "aresforge"
DEFAULT_ITEM_ID = "m168-self-managed-aresforge-project-loop-dry-run"
DEFAULT_AUTONOMY_PROFILE = "github_sync_dry_run"

_BOUNDARY_CONFIRMATIONS: tuple[str, ...] = (
    "M168 dry-runs the self-managed AresForge project loop from local queue evidence only.",
    "The dry run may write local evidence artifacts and a durable local run-store entry.",
    "No live Codex, local LLM/model, GitHub, gh, source patch application, validation command execution, queue mutation, PR creation, PR merge, protected branch update, force push, auto-merge, release, workflow mutation, retry, resume, or automatic next-item execution is performed.",
)


def run_self_managed_project_loop_dry_run(
    config: AppConfig,
    *,
    project_id: str = DEFAULT_PROJECT_ID,
    item_id: str | None = None,
    queue_path: str | Path | None = None,
    dry_run: bool = False,
    autonomy_profile: str = DEFAULT_AUTONOMY_PROFILE,
    output: str | Path | None = None,
    force: bool = False,
    output_format: str = "json",
) -> dict[str, Any]:
    fmt = _text(output_format).lower() or "json"
    if fmt != "json":
        return _error("invalid_format", {"format": output_format, "supported_formats": ["json"]})

    normalized_project_id = _text(project_id) or DEFAULT_PROJECT_ID
    requested_item_id = _text(item_id)
    selected_profile = _text(autonomy_profile) or DEFAULT_AUTONOMY_PROFILE
    started_at = _now_iso()
    run_id = f"self-managed-loop-{_safe_id(normalized_project_id)}-{datetime.now(UTC).strftime('%Y%m%dT%H%M%S%fZ')}"
    run_root = config.repo_root / ".aresforge" / "self_managed_project_loop" / run_id
    output_path = _resolve(config.repo_root, output) if output else run_root / "self-managed-project-loop-dry-run.json"

    if output_path.exists() and not force:
        payload = _base_payload(
            project_id=normalized_project_id,
            item_id=requested_item_id or DEFAULT_ITEM_ID,
            run_id=run_id,
            started_at=started_at,
            autonomy_profile=selected_profile,
        )
        payload.update(
            {
                "status": "blocked",
                "blocked": True,
                "blocked_reasons": ["Output file already exists. Re-run with --force to overwrite."],
                "next_safe_action": "Choose a different output path or re-run with --force.",
            }
        )
        return _emit(config=config, payload=payload, output_path=output_path, ok=False)

    if not dry_run:
        payload = _base_payload(
            project_id=normalized_project_id,
            item_id=requested_item_id or DEFAULT_ITEM_ID,
            run_id=run_id,
            started_at=started_at,
            autonomy_profile=selected_profile,
        )
        payload.update(
            {
                "status": "blocked",
                "blocked": True,
                "blocked_reasons": ["M168 self-managed project loop requires --dry-run."],
                "next_safe_action": "Re-run with --dry-run to create local review artifacts.",
            }
        )
        return _emit(config=config, payload=payload, output_path=output_path, ok=False)

    queue_result = _load_queue(config, queue_path=queue_path)
    queue_items = _dicts(queue_result.get("work_items"))
    selected_item = _select_queue_item(
        queue_items,
        project_id=normalized_project_id,
        requested_item_id=requested_item_id,
    )
    normalized_item_id = _text(selected_item.get("item_id")) or requested_item_id or DEFAULT_ITEM_ID
    run_root.mkdir(parents=True, exist_ok=True)

    read_only_gate = _gate_summary(
        _gate_payload(config, item_id=normalized_item_id, gate_profile="read_only_agent", queue_path=queue_path)
    )
    artifact_gate = _gate_summary(
        _gate_payload(config, item_id=normalized_item_id, gate_profile="local_artifact_write", queue_path=queue_path)
    )
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
    route_decision = _route_decision(selected_item=selected_item, autonomy_payload=autonomy_payload)

    orchestration_plan_path = run_root / "orchestration-plan.json"
    orchestration_plan = _orchestration_plan(
        project_id=normalized_project_id,
        item=selected_item,
        route_decision=route_decision,
        run_id=run_id,
    )
    orchestration_plan_path.write_text(json.dumps(orchestration_plan, indent=2) + "\n", encoding="utf-8")
    orchestration_result = _payload(
        run_multi_agent_orchestration(
            config,
            item_id=normalized_item_id,
            plan_path=orchestration_plan_path,
            dry_run=True,
            queue_path=queue_path,
            output=run_root / "multi-agent-orchestration-dry-run.json",
            force=True,
            output_format="json",
        )
    )
    codex_bundle = _payload(
        bundle_codex_loop_validation_evidence(
            config,
            item_id=normalized_item_id,
            project_id=normalized_project_id,
            dry_run=True,
            autonomy_profile="codex_dry_run",
            queue_path=queue_path,
            output=run_root / "codex-loop-validation-evidence-bundle.json",
            force=True,
            output_format="json",
        )
    )
    github_sync_plan = _payload(
        plan_github_issue_sync(
            config,
            project_id=normalized_project_id,
            item_id=normalized_item_id,
            queue_path=queue_path,
            output=run_root / "github-issue-sync-plan.json",
            force=True,
            output_format="json",
        )
    )
    pr_summary = _payload(
        generate_pr_draft_summary(
            config,
            item_id=normalized_item_id,
            project_id=normalized_project_id,
            queue_path=queue_path,
            run_id=run_id,
            autonomy_profile=selected_profile,
            evidence_bundle=run_root / "codex-loop-validation-evidence-bundle.json",
            output=run_root / "pull-request-draft-summary.json",
            force=True,
            output_format="json",
        )
    )
    closure_recommendation = _payload(
        recommend_github_issue_closure(
            config,
            item_id=normalized_item_id,
            project_id=normalized_project_id,
            queue_path=queue_path,
            run_id=run_id,
            autonomy_profile=selected_profile,
            output_format="json",
        )
    )

    machine_gates = [
        read_only_gate,
        artifact_gate,
        *_dicts(orchestration_result.get("machine_gates_checked")),
        *_dicts(codex_bundle.get("machine_gates_checked")),
        *_dicts(github_sync_plan.get("machine_gates_checked")),
        *_dicts(pr_summary.get("machine_gates_checked")),
        *_dicts(closure_recommendation.get("machine_gates_checked")),
    ]
    artifacts_created = _dedupe(
        [
            str(orchestration_plan_path),
            *_list(orchestration_result.get("artifacts_created")),
            *_list(codex_bundle.get("artifacts_created")),
            *_list(github_sync_plan.get("artifacts_created")),
            *_list(pr_summary.get("artifacts_created")),
            str(output_path),
        ]
    )
    blocked_reasons = _dedupe(
        [
            *queue_result.get("blocked_reasons", []),
            *([] if selected_item else ["No eligible local queue item was found for the self-managed loop dry run."]),
            *(reason for gate in (read_only_gate, artifact_gate) for reason in _list(gate.get("blocked_reasons"))),
            *_list(orchestration_result.get("blocked_reasons")),
            *_list(codex_bundle.get("blocked_reasons")),
            *_list(github_sync_plan.get("blocked_reasons")),
            *_list(pr_summary.get("blocked_reasons")),
        ]
    )
    warnings = _dedupe(
        [
            *queue_result.get("warnings", []),
            *_list(autonomy_payload.get("warnings")),
            *_list(orchestration_result.get("warnings")),
            *_list(codex_bundle.get("warnings")),
            *_list(github_sync_plan.get("warnings")),
            *_list(pr_summary.get("warnings")),
            *_loop_warnings(selected_item, closure_recommendation),
        ]
    )
    blocked = bool(blocked_reasons)
    completed_at = _now_iso()
    payload = _base_payload(
        project_id=normalized_project_id,
        item_id=normalized_item_id,
        run_id=run_id,
        started_at=started_at,
        autonomy_profile=selected_profile,
    )
    payload.update(
        {
            "completed_at": completed_at,
            "status": "blocked" if blocked else "dry_run_completed",
            "blocked": blocked,
            "blocked_reasons": blocked_reasons,
            "warnings": warnings,
            "machine_gates_checked": machine_gates,
            "machine_gates_passed": bool(machine_gates)
            and all(bool(gate.get("passed")) for gate in machine_gates if _gate_required(gate))
            and not blocked,
            "artifacts_created": artifacts_created,
            "next_safe_action": _next_safe_action(blocked=blocked),
            "queue_path": str(resolve_project_queue_path(config.repo_root, queue_path)),
            "selected_queue_item": _queue_item_summary(selected_item, normalized_item_id),
            "route_decision": route_decision,
            "orchestration_plan": {
                "artifact_path": str(orchestration_plan_path),
                "step_count": len(_dicts(orchestration_plan.get("steps"))),
                "status": "planned",
                "execution_performed": False,
            },
            "orchestration_dry_run": _execution_summary(orchestration_result),
            "run_store_entry": {
                "created": False,
                "store_path": "",
                "record_type": "orchestration_run_history_record",
            },
            "codex_loop_dry_run": _execution_summary(codex_bundle),
            "evidence_bundle": _artifact_summary(codex_bundle),
            "github_issue_sync_plan": _github_sync_summary(github_sync_plan),
            "pull_request_summary_draft": _pr_summary(pr_summary),
            "closeout_recommendation": _closeout_recommendation(selected_item, closure_recommendation, blocked=blocked),
            "dry_run": True,
            "mutation_performed": False,
            "queue_mutation_performed": False,
            "codex_execution_performed": False,
            "model_execution_performed": False,
            "github_execution_performed": False,
            "patch_application_performed": False,
            "validation_command_execution_performed": False,
            "local_only": True,
            "github_mutation_allowed": False,
            "codex_execution_allowed": False,
            "model_execution_allowed": False,
            "source_patch_application_allowed": False,
            "queue_mutation_allowed": False,
            "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
        }
    )

    run_store_record = _run_store_record(payload)
    run_store_result = append_orchestration_run_record(config, record=run_store_record)
    payload["run_store_entry"] = {
        "created": bool(run_store_result.get("ok")),
        "store_path": _text(run_store_result.get("store_path")),
        "record_type": "orchestration_run_history_record",
        "errors": _list(run_store_result.get("errors")),
        "warnings": _list(run_store_result.get("warnings")),
    }
    if not run_store_result.get("ok"):
        payload["status"] = "blocked"
        payload["blocked"] = True
        payload["blocked_reasons"] = _dedupe(
            [*_list(payload.get("blocked_reasons")), *_list(run_store_result.get("errors"))]
        )
        payload["machine_gates_passed"] = False
    output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return _emit(config=config, payload=payload, output_path=output_path, ok=not bool(payload.get("blocked")))


def _base_payload(
    *,
    project_id: str,
    item_id: str,
    run_id: str,
    started_at: str,
    autonomy_profile: str,
) -> dict[str, Any]:
    return {
        "record_type": RECORD_TYPE,
        "artifact_type": RECORD_TYPE,
        "generated": True,
        "generated_at": started_at,
        "started_at": started_at,
        "completed_at": "",
        "project_id": project_id,
        "item_id": item_id,
        "run_id": run_id,
        "status": "unknown",
        "blocked": False,
        "blocked_reasons": [],
        "warnings": [],
        "machine_gates_checked": [],
        "machine_gates_passed": False,
        "autonomy_profile": autonomy_profile,
        "artifacts_created": [],
        "mutation_performed": False,
        "queue_mutation_performed": False,
        "codex_execution_performed": False,
        "model_execution_performed": False,
        "github_execution_performed": False,
        "patch_application_performed": False,
        "local_only": True,
        "next_safe_action": "",
    }


def _load_queue(config: AppConfig, *, queue_path: str | Path | None) -> dict[str, Any]:
    path = resolve_project_queue_path(config.repo_root, queue_path)
    if not path.exists():
        return {"work_items": [], "warnings": [], "blocked_reasons": [f"Project queue not found: {path}"]}
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"work_items": [], "warnings": [], "blocked_reasons": [f"Project queue could not be read as JSON: {exc}"]}
    if not isinstance(raw, dict):
        return {"work_items": [], "warnings": [], "blocked_reasons": ["Project queue JSON must decode to an object."]}
    items = raw.get("work_items", [])
    return {"work_items": items if isinstance(items, list) else [], "warnings": [], "blocked_reasons": []}


def _select_queue_item(items: list[dict[str, Any]], *, project_id: str, requested_item_id: str) -> dict[str, Any]:
    if requested_item_id:
        for item in items:
            if _text(item.get("item_id")) == requested_item_id and _text(item.get("project_id")) == project_id:
                return item
        return {}
    for preferred in (DEFAULT_ITEM_ID,):
        for item in items:
            if _text(item.get("item_id")) == preferred and _text(item.get("project_id")) == project_id:
                return item
    candidates = [
        item
        for item in items
        if _text(item.get("project_id")) == project_id and _text(item.get("status")) in {"ready", "in_progress", "done"}
    ]
    return sorted(candidates, key=lambda item: _text(item.get("item_id")))[0] if candidates else {}


def _route_decision(*, selected_item: dict[str, Any], autonomy_payload: dict[str, Any]) -> dict[str, Any]:
    item_type = _text(selected_item.get("item_type"))
    lane = {
        "documentation": "documentation_agent",
        "validation": "validation_agent",
        "sync": "github_sync_planning",
        "dashboard": "hub_status_review",
    }.get(item_type, "orchestration_dry_run")
    return {
        "record_type": "self_managed_route_decision_v1",
        "item_id": _text(selected_item.get("item_id")),
        "item_type": item_type,
        "queue_status": _text(selected_item.get("status")),
        "recommended_lane": lane,
        "recommended_execution_target": "dry-run",
        "autonomy_profile": _text(autonomy_payload.get("autonomy_profile")) or DEFAULT_AUTONOMY_PROFILE,
        "machine_gate_required": True,
        "execution_performed": False,
        "reason": "Self-managed loop dry run keeps route decisions advisory and local-only.",
    }


def _orchestration_plan(*, project_id: str, item: dict[str, Any], route_decision: dict[str, Any], run_id: str) -> dict[str, Any]:
    item_id = _text(item.get("item_id"))
    steps = [
        ("queue-planner-agent", "Confirm queue item, dependencies, and self-managed ordering."),
        ("validation-agent", "Plan validation evidence without running validation commands."),
        ("artifact-registry-agent", "Inspect local artifact/evidence roots without external calls."),
        ("completion-recommendation-agent", "Prepare closeout recommendation without mutating queue state."),
    ]
    return {
        "plan_type": "self_managed_project_loop_orchestration_plan",
        "record_type": "self_managed_project_loop_orchestration_plan_v1",
        "generated": True,
        "generated_at": _now_iso(),
        "project_id": project_id,
        "item_id": item_id,
        "run_id": run_id,
        "route_decision": route_decision,
        "blocked": False,
        "blocked_reasons": [],
        "steps": [
            {
                "step_id": f"step-{index:02d}-{agent_id}",
                "sequence": index,
                "agent_id": agent_id,
                "purpose": purpose,
                "forbidden_capabilities": [
                    "execute_codex",
                    "execute_local_llm",
                    "call_github_api",
                    "call_gh",
                    "apply_patch",
                    "run_validation_commands",
                    "mutate_queue_without_operator",
                    "automatic_next_item_execution",
                ],
            }
            for index, (agent_id, purpose) in enumerate(steps, start=1)
        ],
        "execution_performed": False,
        "local_only": True,
    }


def _run_store_record(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "record_type": "orchestration_run_history_record",
        "run_id": _text(payload.get("run_id")),
        "project_id": _text(payload.get("project_id")),
        "item_id": _text(payload.get("item_id")),
        "status": _text(payload.get("status")),
        "blocked": bool(payload.get("blocked")),
        "blocked_reasons": _list(payload.get("blocked_reasons")),
        "warnings": _list(payload.get("warnings")),
        "machine_gates_checked": _dicts(payload.get("machine_gates_checked")),
        "machine_gates_passed": bool(payload.get("machine_gates_passed")),
        "artifacts_created": _list(payload.get("artifacts_created")),
        "mutation_performed": False,
        "queue_mutation_performed": False,
        "external_execution_performed": False,
        "codex_execution_performed": False,
        "model_execution_performed": False,
        "github_execution_performed": False,
        "patch_application_performed": False,
        "local_only": True,
        "next_safe_action": _text(payload.get("next_safe_action")),
    }


def _queue_item_summary(item: dict[str, Any], item_id: str) -> dict[str, Any]:
    return {
        "item_id": _text(item.get("item_id")) or item_id,
        "found": bool(item),
        "project_id": _text(item.get("project_id")),
        "repo_id": _text(item.get("repo_id")),
        "title": _text(item.get("title")),
        "status": _text(item.get("status")),
        "priority": _text(item.get("priority")),
        "item_type": _text(item.get("item_type")),
        "dependencies": _list(item.get("dependencies")) + _list(item.get("depends_on")),
        "blocked_by": _list(item.get("blocked_by")),
        "validation_evidence_present": bool(_text(item.get("validation_summary")) and _list(item.get("tests_run"))),
    }


def _execution_summary(payload: dict[str, Any]) -> dict[str, Any]:
    gates = _dicts(payload.get("machine_gates_checked"))
    gates_passed = bool(payload.get("machine_gates_passed"))
    if "machine_gates_passed" not in payload and gates:
        gates_passed = all(bool(gate.get("passed")) for gate in gates)
    return {
        "record_type": _text(payload.get("record_type") or payload.get("execution_record_type")),
        "status": _text(payload.get("status")),
        "run_id": _text(payload.get("run_id")),
        "blocked": bool(payload.get("blocked")),
        "blocked_reasons": _list(payload.get("blocked_reasons")),
        "machine_gates_passed": gates_passed,
        "artifacts_created": _list(payload.get("artifacts_created")),
        "codex_execution_performed": bool(payload.get("codex_execution_performed")),
        "model_execution_performed": bool(payload.get("model_execution_performed")),
        "github_execution_performed": bool(payload.get("github_execution_performed")),
        "patch_application_performed": bool(payload.get("patch_application_performed")),
        "queue_mutation_performed": bool(payload.get("queue_mutation_performed")),
        "local_only": bool(payload.get("local_only", True)),
        "next_safe_action": _text(payload.get("next_safe_action")),
    }


def _artifact_summary(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "artifact_type": _text(payload.get("artifact_type") or payload.get("record_type")),
        "status": _text(payload.get("status")),
        "blocked": bool(payload.get("blocked")),
        "artifacts_created": _list(payload.get("artifacts_created")),
        "completion_recommended": bool(payload.get("completion_recommended")),
        "local_only": bool(payload.get("local_only", True)),
    }


def _github_sync_summary(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "record_type": _text(payload.get("record_type")),
        "status": _text(payload.get("status")),
        "blocked": bool(payload.get("blocked")),
        "operation_counts": payload.get("operation_counts", {}) if isinstance(payload.get("operation_counts"), dict) else {},
        "github_execution_performed": False,
        "mutation_allowed": False,
        "artifact_paths": _list(payload.get("artifacts_created")),
        "next_safe_action": _text(payload.get("next_safe_action")),
    }


def _pr_summary(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "record_type": _text(payload.get("record_type")),
        "status": _text(payload.get("status")),
        "blocked": bool(payload.get("blocked")),
        "pr_creation_allowed": False,
        "pull_request_created": False,
        "github_execution_performed": False,
        "artifact_paths": _list(payload.get("artifacts_created")),
        "summary": _text(payload.get("summary")),
        "next_safe_action": _text(payload.get("next_safe_action")),
    }


def _closeout_recommendation(item: dict[str, Any], closure_payload: dict[str, Any], *, blocked: bool) -> dict[str, Any]:
    done = _text(item.get("status")) == "done"
    validation_present = bool(_text(item.get("validation_summary")) and _list(item.get("tests_run")))
    recommend = (not blocked) and done and validation_present
    return {
        "record_type": "self_managed_loop_closeout_recommendation_v1",
        "queue_completion_recommended": recommend,
        "github_issue_closure_recommendation": _text(closure_payload.get("issue_closure_recommendation")),
        "closure_recommended": bool(closure_payload.get("closure_recommended")),
        "issue_closure_allowed": False,
        "issue_closed": False,
        "blocked_reasons": [] if recommend else ["Keep the item under operator review until validation, artifacts, gates, and commit evidence are confirmed."],
        "next_safe_action": "Record operator-reviewed validation evidence and use separate gated commands for any queue or GitHub closeout.",
    }


def _loop_warnings(item: dict[str, Any], closure_payload: dict[str, Any]) -> list[str]:
    warnings = ["Self-managed project loop output is a dry-run artifact bundle, not execution approval."]
    if item and _text(item.get("status")) != "done":
        warnings.append("Selected queue item is not done; closeout recommendation remains preliminary.")
    warnings.extend(_list(closure_payload.get("warnings")))
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


def _gate_summary(gate_payload: dict[str, Any]) -> dict[str, Any]:
    checks = _dicts(gate_payload.get("checks"))
    return {
        "gate_profile": _text(gate_payload.get("gate_profile")) or "read_only_agent",
        "passed": bool(gate_payload.get("passed")) and not bool(gate_payload.get("blocked")),
        "blocked": bool(gate_payload.get("blocked")),
        "blocked_reasons": _list(gate_payload.get("blocked_reasons")),
        "checks_failed": [
            _text(check.get("check_id"))
            for check in checks
            if not bool(check.get("passed")) and not bool(check.get("warning_only"))
        ],
        "required_for_self_managed_loop": True,
    }


def _gate_required(gate: dict[str, Any]) -> bool:
    if "required_for_self_managed_loop" in gate:
        return bool(gate.get("required_for_self_managed_loop"))
    return True


def _next_safe_action(*, blocked: bool) -> str:
    if blocked:
        return "Review blocked dry-run evidence locally; do not proceed to queue or GitHub mutation."
    return "Review the local dry-run bundle, then use separate explicit gated commands for any queue completion or GitHub action."


def _emit(*, config: AppConfig, payload: dict[str, Any], output_path: Path, ok: bool) -> dict[str, Any]:
    return {
        "command": COMMAND_NAME,
        "ok": bool(ok),
        "local_only": True,
        "format": "json",
        "output": str(output_path),
        "wrote_output_file": output_path.exists() and bool(ok),
        "stdout": json.dumps(payload, indent=2),
        "payload": payload,
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


def _list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [_text(entry) for entry in value if _text(entry)]
    if isinstance(value, tuple):
        return [_text(entry) for entry in value if _text(entry)]
    if value in (None, ""):
        return []
    return [_text(value)]


def _dicts(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [entry for entry in value if isinstance(entry, dict)]
    return []


def _dedupe(values: Any) -> list[str]:
    deduped: list[str] = []
    for value in values:
        text = _text(value)
        if text and text not in deduped:
            deduped.append(text)
    return deduped


def _safe_id(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in _text(value).lower())
    return cleaned.strip("-") or "self-managed-loop"


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
