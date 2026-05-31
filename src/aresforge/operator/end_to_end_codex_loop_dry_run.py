from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.codex_dispatch_executor import run_codex_dispatch_executor
from aresforge.operator.codex_result_ingestion_validation import ingest_codex_result_and_validate
from aresforge.operator.local_project_queue import resolve_project_queue_path

COMMAND_NAME = "run-end-to-end-codex-loop"
RECORD_TYPE = "end_to_end_codex_loop_dry_run_v1"
DRY_RUN_VERSION = "m151.1"
DEFAULT_ITEM_ID = "m151-end-to-end-codex-loop-dry-run"
DEFAULT_PROJECT_ID = "aresforge"
DEFAULT_VALIDATION_PROFILE = "queue_system"

_PROHIBITED_OPERATIONS: tuple[str, ...] = (
    "merge_pull_request",
    "force_push",
    "update_protected_branch",
    "enable_auto_merge",
    "create_release",
    "modify_github_workflow",
    "bypass_machine_safety_gate",
    "apply_source_patch",
    "run_real_codex_without_explicit_flags",
    "automatic_queue_completion",
    "automatic_next_item_execution",
)

_BOUNDARY_CONFIRMATIONS: tuple[str, ...] = (
    "M151 runs the Codex orchestration loop in dry-run mode only.",
    "M151 reuses M135 dispatch gates and M136 ingestion/validation/completion recommendation boundaries.",
    "M151 writes local artifacts under .aresforge/codex_loop_dry_runs.",
    "M151 never invokes real Codex, local models, GitHub, source patch application, queue mutation, PR merge, force push, releases, or next-item execution.",
)


def run_end_to_end_codex_loop_dry_run(
    config: AppConfig,
    *,
    item_id: str = DEFAULT_ITEM_ID,
    project_id: str = DEFAULT_PROJECT_ID,
    dry_run: bool = False,
    validation_profile: str = DEFAULT_VALIDATION_PROFILE,
    queue_path: str | Path | None = None,
    output: str | Path | None = None,
    force: bool = False,
    output_format: str = "json",
) -> dict[str, Any]:
    fmt = str(output_format or "json").strip().lower()
    if fmt != "json":
        return _error("invalid_format", {"format": output_format, "supported_formats": ["json"]})

    normalized_item_id = str(item_id or DEFAULT_ITEM_ID).strip() or DEFAULT_ITEM_ID
    queue, queue_errors, resolved_queue_path = _load_queue(config, queue_path=queue_path)
    item = _find_item(queue, normalized_item_id)
    normalized_project_id = (
        str(item.get("project_id", "") or project_id or DEFAULT_PROJECT_ID).strip() or DEFAULT_PROJECT_ID
    )
    started_at = _now_iso()
    run_id = f"{_safe_id(normalized_item_id)}-{datetime.now(UTC).strftime('%Y%m%dT%H%M%S%fZ')}"
    run_root = _run_root(config, normalized_item_id, run_id)
    output_path = _resolve(config.repo_root, output) if output else run_root / "loop-result.json"

    if output_path.exists() and not force:
        payload = _blocked_payload(
            item_id=normalized_item_id,
            project_id=normalized_project_id,
            run_id=run_id,
            started_at=started_at,
            queue_path=resolved_queue_path,
            reasons=["Output file already exists. Re-run with --force to overwrite."],
        )
        return _emit(config=config, payload=payload, output_path=output_path, force=force, ok=False)

    blocked_reasons: list[str] = list(queue_errors)
    warnings: list[str] = []
    artifacts_created: list[str] = []
    steps: list[dict[str, Any]] = []

    if not dry_run:
        blocked_reasons.append("M151 only supports --dry-run; real Codex loop execution remains default-deny.")
    if not item:
        blocked_reasons.append("Queue item was not found.")

    dispatch_artifact_path = (
        config.repo_root
        / ".aresforge"
        / "codex_dispatch"
        / "loop_dry_runs"
        / _safe_id(normalized_item_id)
        / _safe_id(run_id)
        / "codex-dispatch-artifact.json"
    ).resolve()
    synthetic_result_path = run_root / "synthetic-codex-result.md"
    ingestion_execution_record_path = run_root / "ingestion-execution-record.json"
    dispatch_execution_record_path = run_root / "dispatch-execution-record.json"
    ingestion_record_path = run_root / "ingestion-validation-record.json"
    queue_snapshot_path = run_root / "queue-snapshot.json"

    if not blocked_reasons:
        run_root.mkdir(parents=True, exist_ok=True)
        dispatch_artifact_path.parent.mkdir(parents=True, exist_ok=True)
        queue_snapshot_path.write_text(
            json.dumps(_queue_snapshot(queue, normalized_item_id, validation_profile), indent=2) + "\n",
            encoding="utf-8",
        )
        dispatch_artifact_path.write_text(
            json.dumps(_dispatch_artifact(normalized_item_id, normalized_project_id, item), indent=2) + "\n",
            encoding="utf-8",
        )
        synthetic_result_path.write_text(
            _synthetic_codex_result(normalized_item_id, item, validation_profile),
            encoding="utf-8",
        )
        ingestion_execution_record_path.write_text(
            json.dumps(
                _ingestion_execution_record(
                    item_id=normalized_item_id,
                    stdout_path=synthetic_result_path,
                    dispatch_record_path=dispatch_execution_record_path,
                ),
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        artifacts_created.extend(
            [
                str(dispatch_artifact_path),
                str(synthetic_result_path),
                str(ingestion_execution_record_path),
                str(queue_snapshot_path),
            ]
        )

        dispatch_result = run_codex_dispatch_executor(
            config,
            item_id=normalized_item_id,
            artifact_path=dispatch_artifact_path,
            dry_run=True,
            force=True,
            output=dispatch_execution_record_path,
            queue_path=queue_snapshot_path,
            output_format="json",
        )
        dispatch_payload = _payload(dispatch_result)
        steps.append(_step_summary("codex_dispatch_dry_run", dispatch_result, dispatch_payload))
        artifacts_created.extend(_artifact_paths_from_payload(dispatch_payload))
        if dispatch_result.get("ok") is not True or dispatch_payload.get("blocked") is True:
            blocked_reasons.append("Codex dispatch dry run did not pass.")
            blocked_reasons.extend(_list(dispatch_payload.get("blocked_reasons")))

    else:
        dispatch_payload = {}

    if not blocked_reasons:
        ingestion_result = ingest_codex_result_and_validate(
            config,
            item_id=normalized_item_id,
            execution_record=ingestion_execution_record_path,
            validation_profile=validation_profile,
            dry_run=True,
            queue_path=queue_snapshot_path,
            output=ingestion_record_path,
            force=True,
            output_format="json",
        )
        ingestion_payload = _payload(ingestion_result)
        steps.append(_step_summary("codex_result_ingestion_validation_dry_run", ingestion_result, ingestion_payload))
        artifacts_created.extend(_artifact_paths_from_payload(ingestion_payload))
        if ingestion_result.get("ok") is not True or ingestion_payload.get("blocked") is True:
            blocked_reasons.append("Codex result ingestion dry run did not pass.")
            blocked_reasons.extend(_list(ingestion_payload.get("blocked_reasons")))
    else:
        ingestion_payload = {}

    warnings.extend(_collect_warnings(dispatch_payload, ingestion_payload))
    machine_gates = _machine_gates(dispatch_payload)
    completion_queue_gate_result = _gate_summary_from_payload(ingestion_payload)
    completion_recommendation = (
        ingestion_payload.get("completion_recommendation", {}) if isinstance(ingestion_payload, dict) else {}
    )
    blocked = bool(blocked_reasons)
    status = _status(blocked=blocked, completion_recommendation=completion_recommendation)
    payload: dict[str, Any] = {
        "record_type": RECORD_TYPE,
        "artifact_type": RECORD_TYPE,
        "dry_run_version": DRY_RUN_VERSION,
        "generated": True,
        "generated_at": _now_iso(),
        "item_id": normalized_item_id,
        "project_id": normalized_project_id,
        "run_id": run_id,
        "status": status,
        "blocked": blocked,
        "blocked_reasons": _dedupe(blocked_reasons),
        "warnings": _dedupe(warnings),
        "machine_gates_checked": machine_gates,
        "machine_gates_passed": bool(machine_gates) and all(bool(gate.get("passed")) for gate in machine_gates),
        "artifacts_created": sorted(set([*artifacts_created, str(output_path)])),
        "mutation_performed": False,
        "external_execution_performed": False,
        "model_execution_performed": False,
        "codex_execution_performed": False,
        "github_execution_performed": False,
        "patch_application_performed": False,
        "queue_mutation_performed": False,
        "validation_command_execution_performed": False,
        "local_only": True,
        "next_safe_action": _next_safe_action(status=status, completion_recommendation=completion_recommendation),
        "dry_run": bool(dry_run),
        "queue_path": str(resolved_queue_path),
        "queue_snapshot_path": str(queue_snapshot_path) if queue_snapshot_path.exists() else "",
        "validation_profile": validation_profile,
        "validation_commands": _list(ingestion_payload.get("validation_commands")) if ingestion_payload else [],
        "validation_run": ingestion_payload.get("validation_run", []) if ingestion_payload else [],
        "validation_passed": bool(ingestion_payload.get("validation_passed")) if ingestion_payload else False,
        "completion_recommendation": completion_recommendation,
        "completion_queue_gate_result": completion_queue_gate_result,
        "completion_recommended": bool(completion_recommendation.get("recommended_complete")),
        "dispatch_artifact_path": str(dispatch_artifact_path),
        "dispatch_execution_record_path": str(dispatch_execution_record_path) if dispatch_payload else "",
        "ingestion_execution_record_path": str(ingestion_execution_record_path),
        "ingestion_record_path": str(ingestion_record_path) if ingestion_payload else "",
        "steps": steps,
        "prohibited_operations": list(_PROHIBITED_OPERATIONS),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
        "started_at": started_at,
        "completed_at": _now_iso(),
    }
    return _emit(config=config, payload=payload, output_path=output_path, force=force, ok=not blocked)


def _dispatch_artifact(item_id: str, project_id: str, item: dict[str, Any]) -> dict[str, Any]:
    return {
        "artifact_type": "codex_dispatch_artifact_v1",
        "item_id": item_id,
        "project_id": project_id,
        "title": str(item.get("title", "")).strip(),
        "codex_command": ["codex", "exec", "--dry-run"],
        "prompt_text": "M151 dry-run placeholder. Real Codex execution is intentionally not invoked.",
        "tests_run": ["M151 dry-run selected validation profile; commands are not executed in dry-run mode."],
        "validation_commands": ["python -m aresforge ingest-codex-result-and-validate --dry-run"],
        "local_only": True,
        "execution_allowed": False,
        "execution_performed": False,
        "codex_execution_performed": False,
        "patch_application_performed": False,
        "github_execution_performed": False,
        "queue_mutation_performed": False,
    }


def _synthetic_codex_result(item_id: str, item: dict[str, Any], validation_profile: str) -> str:
    title = str(item.get("title", "")).strip() or item_id
    return f"""# Codex Loop Dry Run Result

**Files Changed**
- .aresforge/codex_loop_dry_runs/{_safe_id(item_id)}/loop-result.json

**What Changed**
- Simulated the Codex-backed dispatch, ingestion, validation selection, and completion recommendation loop for {title}.

**Tests Run And Results**
- python -m aresforge ingest-codex-result-and-validate --validation-profile {validation_profile} --dry-run --format json -> passed

**Smoke Checks Run And Results**
- python -m aresforge run-end-to-end-codex-loop --item-id {item_id} --dry-run --format json -> passed

**Warnings Or Blockers**
- No blockers.

**Commit Hash**
- dead151
"""


def _ingestion_execution_record(*, item_id: str, stdout_path: Path, dispatch_record_path: Path) -> dict[str, Any]:
    return {
        "execution_record_type": "codex_dispatch_execution_v1",
        "item_id": item_id,
        "dry_run": True,
        "executed": False,
        "exit_code": 0,
        "stdout_artifact_path": str(stdout_path),
        "stderr_artifact_path": "",
        "result_artifact_path": "",
        "dispatch_execution_record_path": str(dispatch_record_path),
        "changed_files": [".aresforge/codex_loop_dry_runs"],
        "commit_hash": "dead151",
        "local_only": True,
        "external_execution_performed": False,
        "model_execution_performed": False,
        "codex_execution_performed": False,
        "github_execution_performed": False,
        "queue_mutation_performed": False,
        "patch_application_performed": False,
    }


def _queue_snapshot(queue: dict[str, Any], item_id: str, validation_profile: str) -> dict[str, Any]:
    snapshot = json.loads(json.dumps(queue))
    items = snapshot.get("work_items", []) if isinstance(snapshot, dict) else []
    if isinstance(items, list):
        for item in items:
            if isinstance(item, dict) and str(item.get("item_id", "")).strip() == item_id:
                item["source_status_before_m151_dry_run_snapshot"] = str(item.get("status", "")).strip()
                item["status"] = "ready"
                item["tests_run"] = _dedupe(
                    [
                        *_list(item.get("tests_run")),
                        f"M151 dry-run selected validation profile {validation_profile}; validation commands were not executed.",
                    ]
                )
                item["validation_summary"] = (
                    str(item.get("validation_summary", "")).strip()
                    or "M151 dry-run queue snapshot for machine-gated completion recommendation."
                )
                item["artifact_paths"] = _dedupe([*_list(item.get("artifact_paths")), ".aresforge/codex_loop_dry_runs"])
                break
    snapshot["updated_at"] = _now_iso()
    return snapshot


def _step_summary(name: str, result: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "step_name": name,
        "ok": bool(result.get("ok")),
        "blocked": bool(payload.get("blocked")),
        "blocked_reasons": _list(payload.get("blocked_reasons")),
        "artifacts_created": _artifact_paths_from_payload(payload),
        "mutation_performed": bool(payload.get("mutation_performed") or payload.get("queue_mutation_performed")),
        "external_execution_performed": bool(payload.get("external_execution_performed")),
        "model_execution_performed": bool(payload.get("model_execution_performed")),
        "codex_execution_performed": bool(payload.get("codex_execution_performed")),
        "github_execution_performed": bool(payload.get("github_execution_performed")),
        "patch_application_performed": bool(payload.get("patch_application_performed")),
    }


def _machine_gates(*payloads: dict[str, Any]) -> list[dict[str, Any]]:
    gates: list[dict[str, Any]] = []
    for payload in payloads:
        if not isinstance(payload, dict):
            continue
        gate = payload.get("machine_gate_result")
        if isinstance(gate, dict) and gate:
            gates.append(_gate_summary(gate))
    return gates


def _gate_summary_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    gate = payload.get("machine_gate_result") if isinstance(payload, dict) else {}
    return _gate_summary(gate) if isinstance(gate, dict) and gate else {}


def _gate_summary(gate: dict[str, Any]) -> dict[str, Any]:
    return {
        "gate_profile": str(gate.get("gate_profile", "")).strip(),
        "passed": bool(gate.get("passed")) and not bool(gate.get("blocked")),
        "blocked": bool(gate.get("blocked")),
        "blocked_reasons": _list(gate.get("blocked_reasons")),
        "checks_failed": [
            str(check.get("check_id", "")).strip()
            for check in gate.get("checks", [])
            if isinstance(check, dict)
            and not bool(check.get("passed"))
            and not bool(check.get("warning_only"))
        ],
    }


def _artifact_paths_from_payload(payload: dict[str, Any]) -> list[str]:
    paths: list[str] = []
    for key in (
        "artifact_path",
        "stdout_artifact_path",
        "stderr_artifact_path",
        "result_artifact_path",
        "evidence_artifact_path",
        "completion_recommendation_path",
        "machine_gate_result_path",
        "result_source_path",
        "output",
    ):
        value = str(payload.get(key, "") or "").strip()
        if value:
            paths.append(value)
    paths.extend(_list(payload.get("result_artifact_paths")))
    return _dedupe(paths)


def _collect_warnings(*payloads: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    for payload in payloads:
        if not isinstance(payload, dict):
            continue
        warnings.extend(_list(payload.get("warnings")))
        gate = payload.get("machine_gate_result")
        if isinstance(gate, dict):
            warnings.extend(_list(gate.get("warnings")))
    warnings.append("M151 used synthetic dry-run Codex output; no real Codex process was invoked.")
    return _dedupe(warnings)


def _status(*, blocked: bool, completion_recommendation: dict[str, Any]) -> str:
    if blocked:
        return "blocked"
    if completion_recommendation.get("recommended_complete") is True:
        return "dry_run_completed"
    return "dry_run_completed_needs_review"


def _next_safe_action(*, status: str, completion_recommendation: dict[str, Any]) -> str:
    if status == "blocked":
        return "Resolve blocked reasons before rerunning the M151 dry-run loop."
    if completion_recommendation.get("recommended_complete") is True:
        return "Review the local dry-run artifacts; real execution and queue completion still require separate explicit gated commands."
    return "Review missing evidence in the completion recommendation before any real execution or completion path."


def _blocked_payload(
    *,
    item_id: str,
    project_id: str,
    run_id: str,
    started_at: str,
    queue_path: Path,
    reasons: list[str],
) -> dict[str, Any]:
    return {
        "record_type": RECORD_TYPE,
        "artifact_type": RECORD_TYPE,
        "generated": True,
        "generated_at": _now_iso(),
        "item_id": item_id,
        "project_id": project_id,
        "run_id": run_id,
        "status": "blocked",
        "blocked": True,
        "blocked_reasons": _dedupe(reasons),
        "warnings": [],
        "machine_gates_checked": [],
        "machine_gates_passed": False,
        "artifacts_created": [],
        "mutation_performed": False,
        "external_execution_performed": False,
        "model_execution_performed": False,
        "codex_execution_performed": False,
        "github_execution_performed": False,
        "patch_application_performed": False,
        "queue_mutation_performed": False,
        "validation_command_execution_performed": False,
        "local_only": True,
        "next_safe_action": "Resolve blocked reasons before rerunning the M151 dry-run loop.",
        "queue_path": str(queue_path),
        "started_at": started_at,
        "completed_at": _now_iso(),
    }


def _emit(
    *,
    config: AppConfig,
    payload: dict[str, Any],
    output_path: Path,
    force: bool,
    ok: bool,
) -> dict[str, Any]:
    if output_path.exists() and not force:
        blocked = dict(payload)
        blocked["status"] = "blocked"
        blocked["blocked"] = True
        blocked["blocked_reasons"] = _dedupe(
            [*_list(blocked.get("blocked_reasons")), "Output file already exists. Re-run with --force to overwrite."]
        )
        rendered_blocked = json.dumps(blocked, indent=2)
        return {
            "command": COMMAND_NAME,
            "ok": False,
            "local_only": True,
            "format": "json",
            "output": str(output_path),
            "force": force,
            "wrote_output_file": False,
            "stdout": rendered_blocked,
            "payload": blocked,
        }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    rendered = json.dumps(payload, indent=2)
    return {
        "command": COMMAND_NAME,
        "ok": bool(ok),
        "local_only": True,
        "format": "json",
        "output": str(output_path),
        "force": force,
        "wrote_output_file": True,
        "stdout": rendered,
        "payload": payload,
    }


def _load_queue(config: AppConfig, *, queue_path: str | Path | None) -> tuple[dict[str, Any], list[str], Path]:
    path = resolve_project_queue_path(config.repo_root, queue_path)
    if not path.exists():
        return {}, [f"Queue file is missing: {path}"], path
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {}, [f"Queue file is not valid JSON: {exc.msg}."], path
    except OSError as exc:
        return {}, [f"Queue file could not be read: {exc}."], path
    if not isinstance(raw, dict):
        return {}, ["Queue file JSON root must be an object."], path
    return raw, [], path


def _find_item(queue: dict[str, Any], item_id: str) -> dict[str, Any]:
    items = queue.get("work_items", []) if isinstance(queue, dict) else []
    if not isinstance(items, list):
        return {}
    for item in items:
        if isinstance(item, dict) and str(item.get("item_id", "")).strip() == item_id:
            return item
    return {}


def _payload(result: dict[str, Any]) -> dict[str, Any]:
    payload = result.get("payload", {}) if isinstance(result, dict) else {}
    return payload if isinstance(payload, dict) else {}


def _run_root(config: AppConfig, item_id: str, run_id: str) -> Path:
    return (config.repo_root / ".aresforge" / "codex_loop_dry_runs" / _safe_id(item_id) / _safe_id(run_id)).resolve()


def _resolve(repo_root: Path, value: str | Path | None) -> Path:
    path = Path(value or "")
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


def _safe_id(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in str(value or "").strip().lower())
    return cleaned.strip("-") or "codex-loop-dry-run"


def _list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(entry).strip() for entry in value if str(entry).strip()]
    if isinstance(value, tuple):
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
