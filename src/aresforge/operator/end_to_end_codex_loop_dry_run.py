from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import subprocess
from typing import Any, Callable

from aresforge.config import AppConfig
from aresforge.operator.codex_dispatch_executor import run_codex_dispatch_executor
from aresforge.operator.codex_result_ingestion_validation import ingest_codex_result_and_validate
from aresforge.operator.local_project_queue import resolve_project_queue_path

COMMAND_NAME = "run-end-to-end-codex-loop"
RECORD_TYPE = "end_to_end_codex_loop_dry_run_v1"
REAL_RECORD_TYPE = "end_to_end_codex_loop_real_low_risk_v1"
DRY_RUN_VERSION = "m151.1"
REAL_RUN_VERSION = "m152.1"
DEFAULT_ITEM_ID = "m151-end-to-end-codex-loop-dry-run"
DEFAULT_REAL_ITEM_ID = "m152-end-to-end-codex-loop-real-run-for-low-risk-code"
DEFAULT_PROJECT_ID = "aresforge"
DEFAULT_VALIDATION_PROFILE = "queue_system"
DEFAULT_CODEX_COMMAND = ("codex", "exec")

CommandRunner = Callable[..., subprocess.CompletedProcess[Any]]

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

_REAL_RUN_PROHIBITED_OPERATIONS: tuple[str, ...] = (
    "merge_pull_request",
    "force_push",
    "update_protected_branch",
    "enable_auto_merge",
    "create_release",
    "modify_github_workflow",
    "bypass_machine_safety_gate",
    "apply_source_patch_by_aresforge",
    "run_real_codex_without_execution_enabled",
    "run_real_codex_without_allow_low_risk_code",
    "run_real_codex_for_unscoped_or_high_risk_paths",
    "automatic_queue_completion",
    "github_push_or_merge_automation",
    "automatic_next_item_execution",
)

_BOUNDARY_CONFIRMATIONS: tuple[str, ...] = (
    "M151 runs the Codex orchestration loop in dry-run mode only.",
    "M151 reuses M135 dispatch gates and M136 ingestion/validation/completion recommendation boundaries.",
    "M151 writes local artifacts under .aresforge/codex_loop_dry_runs.",
    "M151 never invokes real Codex, local models, GitHub, source patch application, queue mutation, PR merge, force push, releases, or next-item execution.",
)

_REAL_RUN_BOUNDARY_CONFIRMATIONS: tuple[str, ...] = (
    "M152 enables one explicit real Codex loop only for low-risk code scope.",
    "Real execution is default-deny and requires --execution-enabled plus --allow-low-risk-code.",
    "M152 reuses M135 Codex dispatch gates and M136 ingestion/validation/completion recommendation boundaries.",
    "M152 captures all dispatch, ingestion, validation, and completion recommendation evidence as local artifacts.",
    "M152 does not apply patches through AresForge, push to GitHub, merge pull requests, mutate protected branches, enable auto-merge, create releases, complete queue items, or start another item.",
)

_LOW_RISK_CODE_PREFIXES: tuple[str, ...] = (
    "src/",
    "tests/",
)

_LOW_RISK_SUPPORT_PREFIXES: tuple[str, ...] = (
    "docs/",
    "artifacts/",
)

_LOW_RISK_BLOCKED_PREFIXES: tuple[str, ...] = (
    ".github/",
    ".aresforge/queue/",
    "migrations/",
    "scripts/",
    "src/aresforge/operator/codex",
    "src/aresforge/operator/orchestr",
    "src/aresforge/operator/agent",
    "src/aresforge/hub/",
)

_LOW_RISK_BLOCKED_EXACT: tuple[str, ...] = (
    "pyproject.toml",
    "docker-compose.yml",
    "requirements.txt",
    "requirements-dev.txt",
    "setup.py",
    "setup.cfg",
)


def run_end_to_end_codex_loop_dry_run(
    config: AppConfig,
    *,
    item_id: str = DEFAULT_ITEM_ID,
    project_id: str = DEFAULT_PROJECT_ID,
    dry_run: bool = False,
    execution_enabled: bool = False,
    allow_low_risk_code: bool = False,
    codex_command: list[str] | tuple[str, ...] | None = None,
    changed_paths: list[str] | tuple[str, ...] | None = None,
    timeout_seconds: int | None = None,
    validation_profile: str = DEFAULT_VALIDATION_PROFILE,
    queue_path: str | Path | None = None,
    output: str | Path | None = None,
    force: bool = False,
    output_format: str = "json",
    codex_command_runner: CommandRunner | None = None,
    validation_command_runner: Any | None = None,
) -> dict[str, Any]:
    fmt = str(output_format or "json").strip().lower()
    if fmt != "json":
        return _error("invalid_format", {"format": output_format, "supported_formats": ["json"]})

    normalized_item_id = str(item_id or DEFAULT_ITEM_ID).strip() or DEFAULT_ITEM_ID
    real_profile = _is_real_profile(
        item_id=normalized_item_id,
        execution_enabled=execution_enabled,
        allow_low_risk_code=allow_low_risk_code,
        changed_paths=changed_paths,
    )
    record_type = REAL_RECORD_TYPE if real_profile else RECORD_TYPE
    loop_version = REAL_RUN_VERSION if real_profile else DRY_RUN_VERSION
    queue, queue_errors, resolved_queue_path = _load_queue(config, queue_path=queue_path)
    item = _find_item(queue, normalized_item_id)
    normalized_project_id = (
        str(item.get("project_id", "") or project_id or DEFAULT_PROJECT_ID).strip() or DEFAULT_PROJECT_ID
    )
    started_at = _now_iso()
    run_id = f"{_safe_id(normalized_item_id)}-{datetime.now(UTC).strftime('%Y%m%dT%H%M%S%fZ')}"
    run_root = _run_root(config, normalized_item_id, run_id, real_profile=real_profile)
    output_path = _resolve(config.repo_root, output) if output else run_root / "loop-result.json"

    if output_path.exists() and not force:
        payload = _blocked_payload(
            record_type=record_type,
            loop_version=loop_version,
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
    normalized_changed_paths = _normalize_paths(changed_paths or [])
    low_risk_gate = _low_risk_code_gate(
        item=item,
        changed_paths=normalized_changed_paths,
        dry_run=bool(dry_run),
        execution_enabled=bool(execution_enabled),
        allow_low_risk_code=bool(allow_low_risk_code),
    )
    codex_command_parts = _normalize_command(codex_command)

    if real_profile:
        if not dry_run and not execution_enabled:
            blocked_reasons.append(
                "Real Codex loop execution is disabled by default; pass --execution-enabled for non-dry-run execution."
            )
        if not dry_run and not allow_low_risk_code:
            blocked_reasons.append(
                "Real Codex loop execution for code requires --allow-low-risk-code."
            )
        if not dry_run and low_risk_gate.get("passed") is not True:
            blocked_reasons.append("Low-risk code scope gate did not pass.")
            blocked_reasons.extend(_list(low_risk_gate.get("blocked_reasons")))
    elif not dry_run:
        blocked_reasons.append("M151 only supports --dry-run; real Codex loop execution remains default-deny.")
    if not item:
        blocked_reasons.append("Queue item was not found.")

    dispatch_artifact_path = (
        config.repo_root
        / ".aresforge"
        / "codex_dispatch"
        / ("loop_real_runs" if real_profile else "loop_dry_runs")
        / _safe_id(normalized_item_id)
        / _run_dir_id(run_id)
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
            json.dumps(_queue_snapshot(queue, normalized_item_id, validation_profile, real_profile=real_profile), indent=2) + "\n",
            encoding="utf-8",
        )
        dispatch_artifact_path.write_text(
            json.dumps(
                _dispatch_artifact(
                    normalized_item_id,
                    normalized_project_id,
                    item,
                    real_profile=real_profile,
                    dry_run=bool(dry_run),
                    codex_command=codex_command_parts,
                    validation_profile=validation_profile,
                    changed_paths=normalized_changed_paths,
                ),
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        synthetic_result_path.write_text(
            _synthetic_codex_result(normalized_item_id, item, validation_profile, real_profile=real_profile),
            encoding="utf-8",
        )
        ingestion_execution_record_path.write_text(
            json.dumps(
                _ingestion_execution_record(
                    item_id=normalized_item_id,
                    stdout_path=synthetic_result_path,
                    dispatch_record_path=dispatch_execution_record_path,
                    dry_run=True,
                    executed=False,
                    changed_files=normalized_changed_paths or [".aresforge/codex_loop_real_runs" if real_profile else ".aresforge/codex_loop_dry_runs"],
                    commit_hash="dead152" if real_profile else "dead151",
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
            dry_run=bool(dry_run),
            force=True,
            output=dispatch_execution_record_path,
            queue_path=queue_snapshot_path,
            execution_enabled=bool(real_profile and execution_enabled and not dry_run),
            require_clean_worktree=bool(real_profile and not dry_run),
            timeout_seconds=timeout_seconds,
            output_format="json",
            command_runner=codex_command_runner,
        )
        dispatch_payload = _payload(dispatch_result)
        steps.append(
            _step_summary(
                "codex_dispatch_real_low_risk" if real_profile and not dry_run else "codex_dispatch_dry_run",
                dispatch_result,
                dispatch_payload,
            )
        )
        artifacts_created.extend(_artifact_paths_from_payload(dispatch_payload))
        if dispatch_result.get("ok") is not True or dispatch_payload.get("blocked") is True:
            blocked_reasons.append("Codex dispatch did not pass.")
            blocked_reasons.extend(_list(dispatch_payload.get("blocked_reasons")))
        elif real_profile and not dry_run:
            ingestion_execution_record_path.write_text(
                json.dumps(
                    _ingestion_execution_record_from_dispatch(
                        item_id=normalized_item_id,
                        dispatch_payload=dispatch_payload,
                        dispatch_record_path=dispatch_execution_record_path,
                        changed_files=normalized_changed_paths,
                    ),
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

    else:
        dispatch_payload = {}

    if not blocked_reasons:
        ingestion_result = ingest_codex_result_and_validate(
            config,
            item_id=normalized_item_id,
            execution_record=ingestion_execution_record_path,
            validation_profile=validation_profile,
            dry_run=bool(dry_run),
            queue_path=queue_snapshot_path,
            output=ingestion_record_path,
            force=True,
            output_format="json",
            command_runner=validation_command_runner,
        )
        ingestion_payload = _payload(ingestion_result)
        steps.append(
            _step_summary(
                "codex_result_ingestion_validation_real" if real_profile and not dry_run else "codex_result_ingestion_validation_dry_run",
                ingestion_result,
                ingestion_payload,
            )
        )
        artifacts_created.extend(_artifact_paths_from_payload(ingestion_payload))
        if ingestion_result.get("ok") is not True or ingestion_payload.get("blocked") is True:
            blocked_reasons.append("Codex result ingestion and validation did not pass.")
            blocked_reasons.extend(_list(ingestion_payload.get("blocked_reasons")))
    else:
        ingestion_payload = {}

    warnings.extend(_collect_warnings(dispatch_payload, ingestion_payload, real_profile=real_profile, dry_run=bool(dry_run)))
    machine_gates = _machine_gates(dispatch_payload)
    if real_profile:
        machine_gates.append(low_risk_gate)
    completion_queue_gate_result = _gate_summary_from_payload(ingestion_payload)
    completion_recommendation = (
        ingestion_payload.get("completion_recommendation", {}) if isinstance(ingestion_payload, dict) else {}
    )
    blocked = bool(blocked_reasons)
    status = _status(
        blocked=blocked,
        completion_recommendation=completion_recommendation,
        real_profile=real_profile,
        dry_run=bool(dry_run),
        validation_passed=bool(ingestion_payload.get("validation_passed")) if ingestion_payload else False,
    )
    codex_execution_performed = bool(dispatch_payload.get("codex_execution_performed")) if dispatch_payload else False
    external_execution_performed = bool(dispatch_payload.get("external_execution_performed")) if dispatch_payload else False
    validation_command_execution_performed = any(
        isinstance(entry, dict) and not bool(entry.get("skipped"))
        for entry in (ingestion_payload.get("validation_run", []) if ingestion_payload else [])
    )
    payload: dict[str, Any] = {
        "record_type": record_type,
        "artifact_type": record_type,
        "dry_run_version": DRY_RUN_VERSION if not real_profile else "",
        "loop_version": loop_version,
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
        "external_execution_performed": external_execution_performed,
        "model_execution_performed": False,
        "codex_execution_performed": codex_execution_performed,
        "github_execution_performed": False,
        "patch_application_performed": False,
        "queue_mutation_performed": False,
        "validation_command_execution_performed": validation_command_execution_performed,
        "local_only": True,
        "next_safe_action": _next_safe_action(
            status=status,
            completion_recommendation=completion_recommendation,
            real_profile=real_profile,
            dry_run=bool(dry_run),
        ),
        "dry_run": bool(dry_run),
        "execution_enabled": bool(execution_enabled),
        "allow_low_risk_code": bool(allow_low_risk_code),
        "real_execution_allowed": bool(real_profile and not dry_run and execution_enabled and allow_low_risk_code and low_risk_gate.get("passed") is True),
        "low_risk_code_only": bool(real_profile),
        "low_risk_code_gate": low_risk_gate if real_profile else {},
        "changed_paths_declared": normalized_changed_paths,
        "codex_command": codex_command_parts,
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
        "prohibited_operations": list(_REAL_RUN_PROHIBITED_OPERATIONS if real_profile else _PROHIBITED_OPERATIONS),
        "boundary_confirmations": list(_REAL_RUN_BOUNDARY_CONFIRMATIONS if real_profile else _BOUNDARY_CONFIRMATIONS),
        "started_at": started_at,
        "completed_at": _now_iso(),
    }
    return _emit(config=config, payload=payload, output_path=output_path, force=force, ok=not blocked)


def _dispatch_artifact(
    item_id: str,
    project_id: str,
    item: dict[str, Any],
    *,
    real_profile: bool,
    dry_run: bool,
    codex_command: list[str],
    validation_profile: str,
    changed_paths: list[str],
) -> dict[str, Any]:
    return {
        "artifact_type": "codex_dispatch_artifact_v1",
        "item_id": item_id,
        "project_id": project_id,
        "title": str(item.get("title", "")).strip(),
        "codex_command": codex_command if real_profile and not dry_run else ["codex", "exec", "--dry-run"],
        "prompt_text": _dispatch_prompt(item_id, item, real_profile=real_profile, dry_run=dry_run, changed_paths=changed_paths),
        "tests_run": [
            (
                f"M152 selected validation profile {validation_profile}; validation commands run only after real Codex execution."
                if real_profile and not dry_run
                else f"Selected validation profile {validation_profile}; commands are not executed in dry-run mode."
            )
        ],
        "validation_commands": ["python -m aresforge ingest-codex-result-and-validate --validation-profile " + validation_profile],
        "local_only": True,
        "execution_allowed": False,
        "execution_performed": False,
        "codex_execution_performed": False,
        "patch_application_performed": False,
        "github_execution_performed": False,
        "queue_mutation_performed": False,
        "low_risk_code_only": bool(real_profile),
        "declared_changed_paths": changed_paths,
    }


def _dispatch_prompt(
    item_id: str,
    item: dict[str, Any],
    *,
    real_profile: bool,
    dry_run: bool,
    changed_paths: list[str],
) -> str:
    title = str(item.get("title", "")).strip() or item_id
    if real_profile and not dry_run:
        path_text = ", ".join(changed_paths) if changed_paths else "the declared low-risk code scope"
        return (
            f"Run the low-risk Codex loop for {title}. "
            f"Stay within {path_text}. Do not push, merge, edit workflows, apply external patches, "
            "or start another item. Return files changed, validation, warnings, and commit hash evidence."
        )
    if real_profile:
        return "M152 dry-run placeholder. Real Codex execution is intentionally not invoked."
    return "M151 dry-run placeholder. Real Codex execution is intentionally not invoked."


def _synthetic_codex_result(item_id: str, item: dict[str, Any], validation_profile: str, *, real_profile: bool) -> str:
    title = str(item.get("title", "")).strip() or item_id
    milestone = "M152" if real_profile else "M151"
    root = "codex_loop_real_runs" if real_profile else "codex_loop_dry_runs"
    commit_hash = "dead152" if real_profile else "dead151"
    return f"""# Codex Loop Dry Run Result

**Files Changed**
- .aresforge/{root}/{_safe_id(item_id)}/loop-result.json

**What Changed**
- Simulated the Codex-backed dispatch, ingestion, validation selection, and completion recommendation loop for {title}.

**Tests Run And Results**
- python -m aresforge ingest-codex-result-and-validate --validation-profile {validation_profile} --dry-run --format json -> passed

**Smoke Checks Run And Results**
- python -m aresforge run-end-to-end-codex-loop --item-id {item_id} --dry-run --format json -> passed

**Warnings Or Blockers**
- No blockers. {milestone} dry-run did not invoke real Codex.

**Commit Hash**
- {commit_hash}
"""


def _ingestion_execution_record(
    *,
    item_id: str,
    stdout_path: Path,
    dispatch_record_path: Path,
    dry_run: bool,
    executed: bool,
    changed_files: list[str],
    commit_hash: str,
) -> dict[str, Any]:
    return {
        "execution_record_type": "codex_dispatch_execution_v1",
        "item_id": item_id,
        "dry_run": bool(dry_run),
        "executed": bool(executed),
        "exit_code": 0,
        "stdout_artifact_path": str(stdout_path),
        "stderr_artifact_path": "",
        "result_artifact_path": "",
        "dispatch_execution_record_path": str(dispatch_record_path),
        "changed_files": changed_files,
        "commit_hash": commit_hash,
        "local_only": True,
        "external_execution_performed": bool(executed),
        "model_execution_performed": False,
        "codex_execution_performed": bool(executed),
        "github_execution_performed": False,
        "queue_mutation_performed": False,
        "patch_application_performed": False,
    }


def _ingestion_execution_record_from_dispatch(
    *,
    item_id: str,
    dispatch_payload: dict[str, Any],
    dispatch_record_path: Path,
    changed_files: list[str],
) -> dict[str, Any]:
    return {
        "execution_record_type": "codex_dispatch_execution_v1",
        "item_id": item_id,
        "dry_run": False,
        "executed": bool(dispatch_payload.get("executed")),
        "exit_code": dispatch_payload.get("exit_code"),
        "stdout_artifact_path": str(dispatch_payload.get("stdout_artifact_path", "") or ""),
        "stderr_artifact_path": str(dispatch_payload.get("stderr_artifact_path", "") or ""),
        "result_artifact_path": str(dispatch_payload.get("result_artifact_path", "") or ""),
        "dispatch_execution_record_path": str(dispatch_record_path),
        "changed_files": changed_files,
        "commit_hash": "uncommitted-local-real-run",
        "local_only": True,
        "external_execution_performed": bool(dispatch_payload.get("external_execution_performed")),
        "model_execution_performed": False,
        "codex_execution_performed": bool(dispatch_payload.get("codex_execution_performed")),
        "github_execution_performed": False,
        "queue_mutation_performed": False,
        "patch_application_performed": False,
        "warnings_or_blockers": _list(dispatch_payload.get("blocked_reasons")),
    }


def _queue_snapshot(queue: dict[str, Any], item_id: str, validation_profile: str, *, real_profile: bool) -> dict[str, Any]:
    snapshot = json.loads(json.dumps(queue))
    items = snapshot.get("work_items", []) if isinstance(snapshot, dict) else []
    if isinstance(items, list):
        for item in items:
            if isinstance(item, dict) and str(item.get("item_id", "")).strip() == item_id:
                item["source_status_before_codex_loop_snapshot"] = str(item.get("status", "")).strip()
                item["status"] = "ready"
                item["tests_run"] = _dedupe(
                    [
                        *_list(item.get("tests_run")),
                        (
                            f"M152 selected validation profile {validation_profile}; validation commands are executed only in real low-risk mode."
                            if real_profile
                            else f"M151 dry-run selected validation profile {validation_profile}; validation commands were not executed."
                        ),
                    ]
                )
                item["validation_summary"] = (
                    str(item.get("validation_summary", "")).strip()
                    or "Codex loop queue snapshot for machine-gated completion recommendation."
                )
                item["artifact_paths"] = _dedupe(
                    [
                        *_list(item.get("artifact_paths")),
                        ".aresforge/codex_loop_real_runs" if real_profile else ".aresforge/codex_loop_dry_runs",
                    ]
                )
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


def _collect_warnings(*payloads: dict[str, Any], real_profile: bool, dry_run: bool) -> list[str]:
    warnings: list[str] = []
    for payload in payloads:
        if not isinstance(payload, dict):
            continue
        warnings.extend(_list(payload.get("warnings")))
        gate = payload.get("machine_gate_result")
        if isinstance(gate, dict):
            warnings.extend(_list(gate.get("warnings")))
    if dry_run:
        warnings.append(
            "M152 used synthetic dry-run Codex output; no real Codex process was invoked."
            if real_profile
            else "M151 used synthetic dry-run Codex output; no real Codex process was invoked."
        )
    return _dedupe(warnings)


def _status(
    *,
    blocked: bool,
    completion_recommendation: dict[str, Any],
    real_profile: bool,
    dry_run: bool,
    validation_passed: bool,
) -> str:
    if blocked:
        return "blocked"
    if real_profile and dry_run:
        return "dry_run_completed"
    if real_profile and validation_passed:
        return "real_run_validated"
    if real_profile:
        return "real_run_completed_needs_review"
    if completion_recommendation.get("recommended_complete") is True:
        return "dry_run_completed"
    return "dry_run_completed_needs_review"


def _next_safe_action(
    *,
    status: str,
    completion_recommendation: dict[str, Any],
    real_profile: bool,
    dry_run: bool,
) -> str:
    if status == "blocked":
        return "Resolve blocked reasons before rerunning the Codex loop."
    if real_profile and dry_run:
        return "Review the M152 dry-run artifacts; real execution requires --execution-enabled, --allow-low-risk-code, declared low-risk changed paths, and passing machine gates."
    if real_profile:
        return "Review captured local Codex and validation artifacts; queue completion and GitHub sync remain separate explicit gated actions."
    if completion_recommendation.get("recommended_complete") is True:
        return "Review the local dry-run artifacts; real execution and queue completion still require separate explicit gated commands."
    return "Review missing evidence in the completion recommendation before any real execution or completion path."


def _blocked_payload(
    *,
    record_type: str,
    loop_version: str,
    item_id: str,
    project_id: str,
    run_id: str,
    started_at: str,
    queue_path: Path,
    reasons: list[str],
) -> dict[str, Any]:
    return {
        "record_type": record_type,
        "artifact_type": record_type,
        "loop_version": loop_version,
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
        "next_safe_action": "Resolve blocked reasons before rerunning the Codex loop.",
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


def _run_root(config: AppConfig, item_id: str, run_id: str, *, real_profile: bool) -> Path:
    root = "codex_loop_real_runs" if real_profile else "codex_loop_dry_runs"
    return (config.repo_root / ".aresforge" / root / _safe_id(item_id) / _run_dir_id(run_id)).resolve()


def _run_dir_id(run_id: str) -> str:
    safe = _safe_id(run_id)
    if len(safe) <= 72:
        return safe
    return f"run-{safe[-28:]}"


def _is_real_profile(
    *,
    item_id: str,
    execution_enabled: bool,
    allow_low_risk_code: bool,
    changed_paths: list[str] | tuple[str, ...] | None,
) -> bool:
    return (
        str(item_id or "").strip() == DEFAULT_REAL_ITEM_ID
        or bool(execution_enabled)
        or bool(allow_low_risk_code)
        or bool(changed_paths)
    )


def _low_risk_code_gate(
    *,
    item: dict[str, Any],
    changed_paths: list[str],
    dry_run: bool,
    execution_enabled: bool,
    allow_low_risk_code: bool,
) -> dict[str, Any]:
    blocked_reasons: list[str] = []
    warnings: list[str] = []
    if dry_run:
        warnings.append("Low-risk code scope was not enforced for mutation because this is a dry-run.")
    else:
        if not execution_enabled:
            blocked_reasons.append("Real execution flag is required before evaluating low-risk code scope.")
        if not allow_low_risk_code:
            blocked_reasons.append("Low-risk code allowance flag is required before real code execution.")
        if not changed_paths:
            blocked_reasons.append("At least one --changed-path must declare the expected low-risk code scope.")
        blocked_reasons.extend(_blocked_low_risk_paths(changed_paths))
    tags = set(_list(item.get("tags"))) if item else set()
    if not dry_run and item and "risk:low" not in tags and "low-risk-code" not in tags:
        warnings.append("Queue item does not declare risk:low or low-risk-code; explicit flags and path scope still gate execution.")
    blocked = bool(blocked_reasons)
    return {
        "gate_profile": "low_risk_code_scope",
        "passed": not blocked,
        "blocked": blocked,
        "blocked_reasons": _dedupe(blocked_reasons),
        "warnings": _dedupe(warnings),
        "checks_failed": ["changed_path_scope"] if blocked else [],
        "changed_paths": changed_paths,
    }


def _blocked_low_risk_paths(paths: list[str]) -> list[str]:
    reasons: list[str] = []
    for path in paths:
        normalized = path.replace("\\", "/").lstrip("/")
        if normalized in _LOW_RISK_BLOCKED_EXACT or any(normalized.startswith(prefix) for prefix in _LOW_RISK_BLOCKED_PREFIXES):
            reasons.append(f"Path is outside the M152 low-risk code scope: {normalized}")
            continue
        if normalized.startswith(_LOW_RISK_CODE_PREFIXES) or normalized.startswith(_LOW_RISK_SUPPORT_PREFIXES):
            continue
        reasons.append(f"Path is outside the M152 low-risk code scope: {normalized}")
    return _dedupe(reasons)


def _normalize_paths(values: list[str] | tuple[str, ...]) -> list[str]:
    return _dedupe([str(value).strip().replace("\\", "/").lstrip("/") for value in values if str(value).strip()])


def _normalize_command(value: list[str] | tuple[str, ...] | None) -> list[str]:
    parts = [str(part).strip() for part in (value or DEFAULT_CODEX_COMMAND) if str(part).strip()]
    return parts or list(DEFAULT_CODEX_COMMAND)


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
