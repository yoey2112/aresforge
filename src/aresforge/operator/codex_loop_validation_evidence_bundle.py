from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import subprocess
from typing import Any, Callable

from aresforge.config import AppConfig
from aresforge.operator.codex_failure_classification_retry_policy import classify_codex_failure
from aresforge.operator.end_to_end_codex_loop_dry_run import run_end_to_end_codex_loop_dry_run
from aresforge.operator.local_project_queue import resolve_project_queue_path
from aresforge.operator.machine_safety_gate_engine import evaluate_machine_safety_gates
from aresforge.operator.source_patch_risk_classifier import classify_source_patch_risk

COMMAND_NAME = "bundle-codex-loop-validation-evidence"
RECORD_TYPE = "codex_loop_validation_evidence_bundle_v1"
BUNDLE_VERSION = "m161.1"
DEFAULT_ITEM_ID = "m161-codex-loop-validation-evidence-bundle"
DEFAULT_PROJECT_ID = "aresforge"
DEFAULT_AUTONOMY_PROFILE = "codex_dry_run"
DEFAULT_VALIDATION_PROFILE = "queue_system"

CommandRunner = Callable[..., subprocess.CompletedProcess[Any]]

_PROHIBITED_OPERATIONS: tuple[str, ...] = (
    "merge_pull_request",
    "force_push",
    "update_protected_branch",
    "enable_auto_merge",
    "create_release",
    "modify_github_workflow",
    "run_real_codex_from_bundle",
    "run_model_from_bundle",
    "mutate_github_from_bundle",
    "apply_source_patch_from_bundle",
    "complete_queue_item_from_bundle",
    "automatic_retry_loop",
    "automatic_next_item_execution",
    "bypass_machine_safety_gate",
)

_BOUNDARY_CONFIRMATIONS: tuple[str, ...] = (
    "M161 bundles local Codex loop validation evidence and is dry-run by default.",
    "M161 may write a durable local evidence bundle but does not invoke real Codex in dry-run mode.",
    "Validation results are captured from the composed Codex loop; dry-run validation commands remain skipped evidence.",
    "Source patch classification and retry classification are evidence only and never apply patches or retry automatically.",
    "Queue completion and GitHub sync remain separate explicit gated actions after operator review.",
)


def bundle_codex_loop_validation_evidence(
    config: AppConfig,
    *,
    item_id: str = DEFAULT_ITEM_ID,
    project_id: str = DEFAULT_PROJECT_ID,
    dry_run: bool = False,
    autonomy_profile: str | None = None,
    validation_profile: str = DEFAULT_VALIDATION_PROFILE,
    changed_paths: list[str] | tuple[str, ...] | None = None,
    patch_path: str | Path | None = None,
    queue_path: str | Path | None = None,
    output: str | Path | None = None,
    force: bool = False,
    output_format: str = "json",
    codex_command_runner: CommandRunner | None = None,
    validation_command_runner: Any | None = None,
) -> dict[str, Any]:
    fmt = _text(output_format).lower() or "json"
    if fmt != "json":
        return _error("invalid_format", {"format": output_format, "supported_formats": ["json"]})

    normalized_item_id = _text(item_id) or DEFAULT_ITEM_ID
    normalized_project_id = _text(project_id) or DEFAULT_PROJECT_ID
    selected_autonomy_profile = _text(autonomy_profile) or DEFAULT_AUTONOMY_PROFILE
    selected_validation_profile = _text(validation_profile) or DEFAULT_VALIDATION_PROFILE
    normalized_changed_paths = _normalize_paths(changed_paths or [])
    run_id = f"{_safe_id(normalized_item_id)}-bundle-{datetime.now(UTC).strftime('%Y%m%dT%H%M%S%fZ')}"
    bundle_root = _bundle_root(config, normalized_item_id, run_id)
    output_path = _resolve(config.repo_root, output) if output else bundle_root / "codex-loop-validation-evidence-bundle.json"

    if output_path.exists() and not force:
        payload = _base_payload(
            config,
            item_id=normalized_item_id,
            project_id=normalized_project_id,
            run_id=run_id,
            bundle_root=bundle_root,
            autonomy_profile=selected_autonomy_profile,
            dry_run=bool(dry_run),
        )
        payload["status"] = "blocked"
        payload["blocked"] = True
        payload["blocked_reasons"] = ["Output file already exists. Re-run with --force to overwrite."]
        payload["next_safe_action"] = "Re-run with --force or choose a different output path."
        return _emit(config=config, payload=payload, output_path=output_path, force=force, ok=False)

    if not dry_run:
        payload = _base_payload(
            config,
            item_id=normalized_item_id,
            project_id=normalized_project_id,
            run_id=run_id,
            bundle_root=bundle_root,
            autonomy_profile=selected_autonomy_profile,
            dry_run=False,
        )
        payload["status"] = "blocked"
        payload["blocked"] = True
        payload["blocked_reasons"] = ["M161 evidence bundling requires --dry-run; it does not run live Codex."]
        payload["next_safe_action"] = "Re-run with --dry-run to generate local evidence bundle artifacts."
        return _emit(config=config, payload=payload, output_path=output_path, force=force, ok=False)

    queue = _load_queue(config, queue_path=queue_path)
    item = _find_item(queue, normalized_item_id)
    bundle_root.mkdir(parents=True, exist_ok=True)

    loop_result = run_end_to_end_codex_loop_dry_run(
        config,
        item_id=normalized_item_id,
        project_id=normalized_project_id,
        dry_run=True,
        validation_profile=selected_validation_profile,
        changed_paths=normalized_changed_paths,
        queue_path=queue_path,
        output=bundle_root / "codex-loop-execution-record.json",
        force=True,
        output_format="json",
        codex_command_runner=codex_command_runner,
        validation_command_runner=validation_command_runner,
    )
    loop_payload = _payload(loop_result)
    ingestion_payload = _load_json(_text(loop_payload.get("ingestion_record_path")))
    ingestion_execution_record = _load_json(_text(loop_payload.get("ingestion_execution_record_path")))

    stdout_artifact = _copy_text_artifact(
        source_path=_text(ingestion_execution_record.get("stdout_artifact_path")),
        destination=bundle_root / "stdout-artifact.md",
        fallback="",
    )
    stderr_artifact = _copy_text_artifact(
        source_path=_text(ingestion_execution_record.get("stderr_artifact_path")),
        destination=bundle_root / "stderr-artifact.txt",
        fallback="",
    )

    read_only_gate = _gate_summary(
        _gate_payload(config, item_id=normalized_item_id, gate_profile="read_only_agent", queue_path=queue_path)
    )
    local_artifact_gate = _gate_summary(
        _gate_payload(config, item_id=normalized_item_id, gate_profile="local_artifact_write", queue_path=queue_path)
    )
    source_patch_result = _source_patch_classification(
        config,
        item_id=normalized_item_id,
        project_id=normalized_project_id,
        patch_path=patch_path,
        queue_path=queue_path,
        bundle_root=bundle_root,
    )
    retry_result = _retry_classification(
        config,
        item_id=normalized_item_id,
        project_id=normalized_project_id,
        loop_payload=loop_payload,
        queue_path=queue_path,
        bundle_root=bundle_root,
    )

    changed_file_summary = _changed_file_summary(
        config,
        loop_payload=loop_payload,
        ingestion_payload=ingestion_payload,
        declared_changed_paths=normalized_changed_paths,
    )
    validation_summary = _validation_summary(loop_payload=loop_payload, ingestion_payload=ingestion_payload)
    completion_recommendation = _completion_recommendation(loop_payload=loop_payload, ingestion_payload=ingestion_payload)

    machine_gates = [
        read_only_gate,
        local_artifact_gate,
        *_dicts(loop_payload.get("machine_gates_checked")),
        *_dicts(source_patch_result.get("machine_gates_checked")),
        *_dicts(retry_result.get("machine_gates_checked")),
    ]
    blocked_reasons = _blocked_reasons(
        item=item,
        loop_result=loop_result,
        loop_payload=loop_payload,
        read_only_gate=read_only_gate,
        local_artifact_gate=local_artifact_gate,
        source_patch_result=source_patch_result,
        retry_result=retry_result,
    )
    blocked = bool(blocked_reasons)
    artifacts_created = _dedupe(
        [
            str(bundle_root),
            str(output_path),
            str(bundle_root / "codex-loop-execution-record.json"),
            stdout_artifact,
            stderr_artifact,
            *_list(loop_payload.get("artifacts_created")),
            *_list(source_patch_result.get("artifacts_created")),
            *_list(retry_result.get("artifacts_created")),
        ]
    )

    payload = _base_payload(
        config,
        item_id=normalized_item_id,
        project_id=normalized_project_id,
        run_id=run_id,
        bundle_root=bundle_root,
        autonomy_profile=selected_autonomy_profile,
        dry_run=True,
    )
    payload.update(
        {
            "status": "blocked" if blocked else "evidence_bundle_created",
            "blocked": blocked,
            "blocked_reasons": blocked_reasons,
            "warnings": _warnings(
                item=item,
                loop_payload=loop_payload,
                source_patch_result=source_patch_result,
                retry_result=retry_result,
            ),
            "machine_gates_checked": machine_gates,
            "machine_gates_passed": bool(machine_gates) and all(bool(gate.get("passed")) for gate in machine_gates),
            "artifacts_created": artifacts_created,
            "mutation_performed": False,
            "queue_mutation_performed": False,
            "codex_execution_performed": bool(loop_payload.get("codex_execution_performed")),
            "model_execution_performed": False,
            "github_execution_performed": False,
            "patch_application_performed": False,
            "validation_command_execution_performed": bool(loop_payload.get("validation_command_execution_performed")),
            "external_execution_performed": bool(loop_payload.get("external_execution_performed")),
            "next_safe_action": _next_safe_action(blocked=blocked, completion_recommendation=completion_recommendation),
            "queue_item_found": bool(item),
            "queue_item_status": _text(item.get("status")),
            "queue_path": str(resolve_project_queue_path(config.repo_root, queue_path)),
            "codex_loop_execution_record": _loop_execution_record(loop_result, loop_payload),
            "stdout_stderr_artifacts": {
                "stdout_artifact_path": stdout_artifact,
                "stderr_artifact_path": stderr_artifact,
                "source_stdout_artifact_path": _text(ingestion_execution_record.get("stdout_artifact_path")),
                "source_stderr_artifact_path": _text(ingestion_execution_record.get("stderr_artifact_path")),
            },
            "changed_files": changed_file_summary,
            "validation_evidence": validation_summary,
            "machine_gate_results": machine_gates,
            "source_patch_risk_classification": source_patch_result,
            "retry_classification": retry_result,
            "completion_recommendation": completion_recommendation,
            "completion_recommended": bool(completion_recommendation.get("recommended_complete")),
            "safe_completion_recommendation": _safe_completion_recommendation(completion_recommendation),
            "prohibited_operations": list(_PROHIBITED_OPERATIONS),
            "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
        }
    )
    return _emit(config=config, payload=payload, output_path=output_path, force=force, ok=True)


def _base_payload(
    config: AppConfig,
    *,
    item_id: str,
    project_id: str,
    run_id: str,
    bundle_root: Path,
    autonomy_profile: str,
    dry_run: bool,
) -> dict[str, Any]:
    return {
        "record_type": RECORD_TYPE,
        "artifact_type": RECORD_TYPE,
        "bundle_version": BUNDLE_VERSION,
        "generated": True,
        "generated_at": _now_iso(),
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
        "validation_command_execution_performed": False,
        "external_execution_performed": False,
        "local_only": True,
        "dry_run": bool(dry_run),
        "bundle_root": str(bundle_root),
        "recommended_bundle_artifact_path": str(
            (config.repo_root / ".aresforge" / "codex_loop_validation_evidence" / _path_id(item_id)).resolve()
        ),
        "next_safe_action": "",
    }


def _source_patch_classification(
    config: AppConfig,
    *,
    item_id: str,
    project_id: str,
    patch_path: str | Path | None,
    queue_path: str | Path | None,
    bundle_root: Path,
) -> dict[str, Any]:
    if patch_path:
        result = classify_source_patch_risk(
            config,
            patch_path=patch_path,
            item_id=item_id,
            project_id=project_id,
            queue_path=queue_path,
            output=bundle_root / "source-patch-risk-classification.json",
            force=True,
            output_format="json",
        )
        return _payload(result)
    artifact_path = bundle_root / "source-patch-risk-classification.json"
    payload = {
        "record_type": "source_patch_risk_classification_v1",
        "artifact_type": "source_patch_risk_classification_v1",
        "generated": True,
        "generated_at": _now_iso(),
        "project_id": project_id,
        "item_id": item_id,
        "run_id": f"{item_id}:m161-no-source-patch",
        "status": "not_applicable_no_source_patch",
        "blocked": False,
        "blocked_reasons": [],
        "warnings": ["No source patch artifact was supplied; source patch risk is recorded as not applicable."],
        "machine_gates_checked": [],
        "machine_gates_passed": True,
        "artifacts_created": [str(artifact_path)],
        "mutation_performed": False,
        "queue_mutation_performed": False,
        "codex_execution_performed": False,
        "model_execution_performed": False,
        "github_execution_performed": False,
        "patch_application_performed": False,
        "validation_command_execution_performed": False,
        "local_only": True,
        "next_safe_action": "If a generated source patch appears later, classify it with classify-source-patch-risk before any apply plan.",
        "patch_path": "",
        "patch_file_found": False,
        "source_patch_detected": False,
        "risk_level": "none",
        "touched_files": [],
        "blocked_operations": [],
        "patch_application_allowed_by_classifier": False,
        "source_patch_application_requires_separate_gate": True,
    }
    artifact_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def _retry_classification(
    config: AppConfig,
    *,
    item_id: str,
    project_id: str,
    loop_payload: dict[str, Any],
    queue_path: str | Path | None,
    bundle_root: Path,
) -> dict[str, Any]:
    if loop_payload.get("blocked") is True:
        failure_artifact = bundle_root / "codex-loop-failure-artifact.json"
        failure_artifact.write_text(
            json.dumps(
                {
                    "item_id": item_id,
                    "project_id": project_id,
                    "run_id": _text(loop_payload.get("run_id")),
                    "status": _text(loop_payload.get("status")) or "blocked",
                    "blocked": True,
                    "blocked_reasons": _list(loop_payload.get("blocked_reasons")),
                    "warnings": _list(loop_payload.get("warnings")),
                    "validation_passed": bool(loop_payload.get("validation_passed")),
                    "machine_gates_checked": loop_payload.get("machine_gates_checked", []),
                    "external_execution_performed": bool(loop_payload.get("external_execution_performed")),
                    "codex_execution_performed": bool(loop_payload.get("codex_execution_performed")),
                    "model_execution_performed": bool(loop_payload.get("model_execution_performed")),
                    "github_execution_performed": bool(loop_payload.get("github_execution_performed")),
                    "patch_application_performed": bool(loop_payload.get("patch_application_performed")),
                    "mutation_performed": bool(loop_payload.get("mutation_performed")),
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        result = classify_codex_failure(
            config,
            failure_artifact=failure_artifact,
            item_id=item_id,
            project_id=project_id,
            queue_path=queue_path,
            output=bundle_root / "retry-classification.json",
            force=True,
            output_format="json",
        )
        return _payload(result)
    artifact_path = bundle_root / "retry-classification.json"
    payload = {
        "record_type": "codex_failure_classification_retry_policy_v1",
        "artifact_type": "codex_failure_classification_retry_policy_v1",
        "generated": True,
        "generated_at": _now_iso(),
        "project_id": project_id,
        "item_id": item_id,
        "run_id": _text(loop_payload.get("run_id")) or f"{item_id}:m161-retry-not-required",
        "status": "not_applicable_no_failure",
        "blocked": False,
        "blocked_reasons": [],
        "warnings": ["Codex loop evidence was not blocked; retry classification records no retry required."],
        "machine_gates_checked": [],
        "machine_gates_passed": True,
        "artifacts_created": [str(artifact_path)],
        "mutation_performed": False,
        "queue_mutation_performed": False,
        "codex_execution_performed": False,
        "model_execution_performed": False,
        "github_execution_performed": False,
        "patch_application_performed": False,
        "validation_command_execution_performed": False,
        "local_only": True,
        "next_safe_action": "Do not retry automatically; review evidence and use a separate explicit command if future retry evidence is needed.",
        "primary_failure_class": "none",
        "detected_failure_classes": [],
        "retry_policy": {
            "policy_id": "no_retry_required",
            "decision": "stop",
            "automatic_retry_allowed": False,
            "max_retry_attempts": 0,
            "requires_operator_approval": True,
            "requires_machine_gate": "codex_dispatch for any future retry",
            "safe_recovery_command": "",
            "stop_reason": "No failed Codex loop was present in this bundle.",
        },
    }
    artifact_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def _loop_execution_record(result: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "command": result.get("command", "run-end-to-end-codex-loop"),
        "ok": bool(result.get("ok")),
        "record_type": _text(payload.get("record_type")),
        "status": _text(payload.get("status")),
        "blocked": bool(payload.get("blocked")),
        "blocked_reasons": _list(payload.get("blocked_reasons")),
        "run_id": _text(payload.get("run_id")),
        "execution_record_path": _text(result.get("output")),
        "dispatch_execution_record_path": _text(payload.get("dispatch_execution_record_path")),
        "ingestion_execution_record_path": _text(payload.get("ingestion_execution_record_path")),
        "ingestion_record_path": _text(payload.get("ingestion_record_path")),
        "artifacts_created": _list(payload.get("artifacts_created")),
        "codex_execution_performed": bool(payload.get("codex_execution_performed")),
        "validation_command_execution_performed": bool(payload.get("validation_command_execution_performed")),
        "github_execution_performed": bool(payload.get("github_execution_performed")),
        "patch_application_performed": bool(payload.get("patch_application_performed")),
        "queue_mutation_performed": bool(payload.get("queue_mutation_performed")),
        "next_safe_action": _text(payload.get("next_safe_action")),
    }


def _changed_file_summary(
    config: AppConfig,
    *,
    loop_payload: dict[str, Any],
    ingestion_payload: dict[str, Any],
    declared_changed_paths: list[str],
) -> dict[str, Any]:
    detected = _dedupe(
        [
            *declared_changed_paths,
            *_list(loop_payload.get("changed_paths_declared")),
            *_list(ingestion_payload.get("changed_files")),
        ]
    )
    workspace = _git_changed_files(config.repo_root)
    return {
        "declared_changed_paths": declared_changed_paths,
        "loop_reported_changed_files": _list(loop_payload.get("changed_paths_declared")),
        "ingestion_reported_changed_files": _list(ingestion_payload.get("changed_files")),
        "workspace_changed_files": workspace,
        "bundled_changed_files": _dedupe([*detected, *workspace]),
        "changed_file_count": len(_dedupe([*detected, *workspace])),
    }


def _validation_summary(*, loop_payload: dict[str, Any], ingestion_payload: dict[str, Any]) -> dict[str, Any]:
    validation_run = ingestion_payload.get("validation_run", loop_payload.get("validation_run", []))
    validation_entries = _dicts(validation_run)
    return {
        "validation_profile": _text(loop_payload.get("validation_profile") or ingestion_payload.get("validation_profile")),
        "validation_commands": _list(loop_payload.get("validation_commands") or ingestion_payload.get("validation_commands")),
        "validation_run": validation_entries,
        "validation_passed": bool(loop_payload.get("validation_passed") or ingestion_payload.get("validation_passed")),
        "validation_command_execution_performed": bool(loop_payload.get("validation_command_execution_performed")),
        "dry_run_validation_skipped": any(bool(entry.get("skipped")) for entry in validation_entries),
        "ingestion_record_path": _text(loop_payload.get("ingestion_record_path")),
        "machine_gate_result_path": _text(ingestion_payload.get("machine_gate_result_path")),
    }


def _completion_recommendation(*, loop_payload: dict[str, Any], ingestion_payload: dict[str, Any]) -> dict[str, Any]:
    recommendation = loop_payload.get("completion_recommendation")
    if not isinstance(recommendation, dict):
        recommendation = ingestion_payload.get("completion_recommendation", {})
    return recommendation if isinstance(recommendation, dict) else {}


def _safe_completion_recommendation(recommendation: dict[str, Any]) -> dict[str, Any]:
    return {
        "recommended_complete": bool(recommendation.get("recommended_complete")),
        "operator_decision_required": True,
        "queue_completion_performed": False,
        "github_sync_performed": False,
        "next_safe_action": _text(recommendation.get("next_safe_action"))
        or "Review evidence before any separate explicit queue completion action.",
    }


def _blocked_reasons(
    *,
    item: dict[str, Any],
    loop_result: dict[str, Any],
    loop_payload: dict[str, Any],
    read_only_gate: dict[str, Any],
    local_artifact_gate: dict[str, Any],
    source_patch_result: dict[str, Any],
    retry_result: dict[str, Any],
) -> list[str]:
    reasons: list[str] = []
    if not item:
        reasons.append("Queue item was not found.")
    if loop_result.get("ok") is not True or loop_payload.get("blocked") is True:
        reasons.append("Codex loop evidence generation did not pass.")
        reasons.extend(_list(loop_payload.get("blocked_reasons")))
    for gate in (read_only_gate, local_artifact_gate):
        if gate.get("passed") is not True:
            reasons.extend(_list(gate.get("blocked_reasons")) or [f"Machine gate did not pass: {gate.get('gate_profile')}"])
    if source_patch_result.get("blocked") is True:
        reasons.append("Source patch risk classification is blocked.")
        reasons.extend(_list(source_patch_result.get("blocked_reasons")))
    if retry_result.get("blocked") is True:
        reasons.append("Retry classification is blocked.")
        reasons.extend(_list(retry_result.get("blocked_reasons")))
    return _dedupe(reasons)


def _warnings(
    *,
    item: dict[str, Any],
    loop_payload: dict[str, Any],
    source_patch_result: dict[str, Any],
    retry_result: dict[str, Any],
) -> list[str]:
    warnings = [
        *_list(loop_payload.get("warnings")),
        *_list(source_patch_result.get("warnings")),
        *_list(retry_result.get("warnings")),
        "M161 dry-run evidence bundling did not invoke real Codex, models, GitHub, source patch apply, queue completion, retry, or next-item execution.",
    ]
    if item and _text(item.get("status")) == "done":
        warnings.append("Queue item is already done; bundle remains reproducible validation evidence.")
    return _dedupe(warnings)


def _next_safe_action(*, blocked: bool, completion_recommendation: dict[str, Any]) -> str:
    if blocked:
        return "Resolve bundle blockers and regenerate local evidence before any completion or GitHub action."
    if completion_recommendation.get("recommended_complete") is True:
        return "Review the durable evidence bundle; any queue completion remains a separate explicit operator action."
    return "Review missing completion evidence and keep queue/GitHub mutation blocked until separate validation evidence is accepted."


def _gate_payload(
    config: AppConfig,
    *,
    item_id: str,
    gate_profile: str,
    queue_path: str | Path | None,
) -> dict[str, Any]:
    result = evaluate_machine_safety_gates(
        config,
        item_id=item_id,
        gate_profile=gate_profile,
        queue_path=queue_path,
        output_format="json",
    )
    return _payload(result)


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


def _copy_text_artifact(*, source_path: str, destination: Path, fallback: str) -> str:
    text = fallback
    if source_path:
        source = Path(source_path)
        if source.exists():
            try:
                text = source.read_text(encoding="utf-8-sig")
            except UnicodeDecodeError:
                text = source.read_text(encoding="utf-8", errors="replace")
            except OSError:
                text = fallback
    destination.write_text(text, encoding="utf-8")
    return str(destination)


def _load_queue(config: AppConfig, *, queue_path: str | Path | None) -> dict[str, Any]:
    path = resolve_project_queue_path(config.repo_root, queue_path)
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    return raw if isinstance(raw, dict) else {}


def _find_item(queue: dict[str, Any], item_id: str) -> dict[str, Any]:
    items = queue.get("work_items", []) if isinstance(queue, dict) else []
    if not isinstance(items, list):
        return {}
    for item in items:
        if isinstance(item, dict) and _text(item.get("item_id")) == item_id:
            return item
    return {}


def _load_json(path_value: str) -> dict[str, Any]:
    if not path_value:
        return {}
    path = Path(path_value)
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    return raw if isinstance(raw, dict) else {}


def _git_changed_files(repo_root: Path) -> list[str]:
    try:
        completed = subprocess.run(
            ["git", "status", "--short"],
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    files: list[str] = []
    for line in completed.stdout.splitlines():
        if not line.strip():
            continue
        candidate = line[3:].strip()
        if " -> " in candidate:
            candidate = candidate.split(" -> ", 1)[1].strip()
        if candidate:
            files.append(candidate.replace("\\", "/"))
    return _dedupe(files)


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


def _bundle_root(config: AppConfig, item_id: str, run_id: str) -> Path:
    return (
        config.repo_root
        / ".aresforge"
        / "codex_loop_validation_evidence"
        / _path_id(item_id)
        / _run_dir_id(run_id)
    ).resolve()


def _run_dir_id(run_id: str) -> str:
    safe = _safe_id(run_id)
    if len(safe) <= 36:
        return safe
    return f"run-{safe[-24:]}"


def _path_id(value: str) -> str:
    safe = _safe_id(value)
    if len(safe) <= 24:
        return safe
    return f"{safe[:10]}-{safe[-10:]}"


def _resolve(repo_root: Path, value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


def _normalize_paths(values: list[str] | tuple[str, ...]) -> list[str]:
    return _dedupe([_text(value).replace("\\", "/").lstrip("/") for value in values if _text(value)])


def _payload(result: dict[str, Any]) -> dict[str, Any]:
    payload = result.get("payload", {}) if isinstance(result, dict) else {}
    return payload if isinstance(payload, dict) else {}


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


def _safe_id(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in _text(value).lower())
    return cleaned.strip("-") or "codex-loop-validation-evidence"


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
