from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import subprocess
from typing import Any, Callable

from aresforge.config import AppConfig
from aresforge.operator.agent_registry import build_agent_registry
from aresforge.operator.llm_decision_policy import recommend_llm_decision
from aresforge.operator.local_project_queue import resolve_project_queue_path
from aresforge.operator.machine_safety_gate_engine import evaluate_machine_safety_gates

COMMAND_NAME = "inspect-codex-validation-profiles"
PROFILE_RECORD_TYPE = "codex_validation_profile_expansion_v1"
PROFILE_VERSION = "m144.1"
DEFAULT_ITEM_ID = "m144-codex-validation-profile-expansion"
DEFAULT_PROJECT_ID = "aresforge"

CommandRunner = Callable[..., subprocess.CompletedProcess[Any]]

VALIDATION_PROFILE_COMMANDS: dict[str, tuple[str, ...]] = {
    "docs_only": ("git diff --check",),
    "tests_only": (
        "git diff --check",
        "python -m pytest tests",
    ),
    "code_unit_tests": (
        "python -m pytest tests/test_cli.py",
        "python -m pytest tests/test_dispatch_result_evidence_parser.py",
        "python -m pytest tests/test_queue_completion_recommendation.py",
        "python -m pytest tests/test_machine_safety_gate_engine.py",
    ),
    "hub_ui": (
        "git diff --check",
        "python -m pytest tests/test_hub_ui_foundation.py",
        "python -m pytest tests/test_hub_project_factory_api.py",
    ),
    "queue_system": (
        "python -m pytest tests/test_local_project_queue.py",
        "python -m pytest tests/test_queue_completion_recommendation.py",
        "python -m pytest tests/test_machine_safety_gate_engine.py",
    ),
    "codex_orchestration": (
        "git diff --check",
        "python -m pytest tests/test_cli.py",
        "python -m pytest tests/test_codex_result_ingestion_validation.py",
        "python -m pytest tests/test_multi_agent_orchestrator.py",
        "python -m pytest tests/test_machine_safety_gate_engine.py",
    ),
    "full_local_safe": (
        "git diff --check",
        "python -m pytest tests/test_cli.py",
        "python -m pytest tests/test_codex_result_ingestion_validation.py",
        "python -m pytest tests/test_dispatch_result_evidence_parser.py",
        "python -m pytest tests/test_queue_completion_recommendation.py",
        "python -m pytest tests/test_machine_safety_gate_engine.py",
    ),
}

_PROFILE_METADATA: dict[str, dict[str, Any]] = {
    "docs_only": {
        "description": "Documentation-only Codex output validation.",
        "task_types": ["documentation", "architecture"],
        "path_classes": ["documentation"],
        "risk_classes": ["low"],
    },
    "tests_only": {
        "description": "Test-file-only Codex output validation.",
        "task_types": ["validation"],
        "path_classes": ["tests"],
        "risk_classes": ["low", "medium"],
    },
    "code_unit_tests": {
        "description": "Source-level unit validation for low-to-medium code changes.",
        "task_types": ["feature", "architecture", "orchestration", "validation"],
        "path_classes": ["source", "tests", "codex_runtime"],
        "risk_classes": ["low", "medium"],
    },
    "hub_ui": {
        "description": "Hub API/static UI validation for frontend or local Hub changes.",
        "task_types": ["dashboard", "feature"],
        "path_classes": ["hub_ui", "source", "tests"],
        "risk_classes": ["low", "medium"],
    },
    "queue_system": {
        "description": "Queue, completion, and machine-gate validation for queue-control changes.",
        "task_types": ["queue", "orchestration", "validation"],
        "path_classes": ["queue", "source", "tests"],
        "risk_classes": ["medium", "high"],
    },
    "codex_orchestration": {
        "description": "Codex loop and orchestration validation for dispatch, ingestion, and recovery boundaries.",
        "task_types": ["orchestration", "validation"],
        "path_classes": ["codex_runtime", "orchestration", "source", "tests"],
        "risk_classes": ["medium", "high"],
    },
    "full_local_safe": {
        "description": "Broad local-safe validation for mixed, high-risk, or protected-path changes.",
        "task_types": ["feature", "architecture", "orchestration", "validation", "queue", "dashboard"],
        "path_classes": ["protected", "workflow", "mixed", "unknown"],
        "risk_classes": ["high", "critical", "unknown"],
    },
}

_PATH_CLASS_RISK: dict[str, str] = {
    "documentation": "low",
    "tests": "low",
    "hub_ui": "medium",
    "queue": "high",
    "codex_runtime": "high",
    "orchestration": "high",
    "source": "medium",
    "protected": "critical",
    "workflow": "critical",
    "artifact": "low",
    "unknown": "medium",
}

_TASK_TYPE_DEFAULTS: dict[str, str] = {
    "documentation": "docs_only",
    "architecture": "docs_only",
    "validation": "code_unit_tests",
    "dashboard": "hub_ui",
    "queue": "queue_system",
    "orchestration": "codex_orchestration",
    "feature": "code_unit_tests",
}

_RISK_CLASS_DEFAULTS: dict[str, str] = {
    "low": "docs_only",
    "medium": "code_unit_tests",
    "high": "full_local_safe",
    "critical": "full_local_safe",
    "unknown": "full_local_safe",
}

_BOUNDARY_CONFIRMATIONS: tuple[str, ...] = (
    "M144 inspects Codex validation profile selection locally.",
    "This command performs no Codex execution, model execution, GitHub execution, validation command execution, patch application, or queue mutation.",
    "Validation profiles are allowlisted command plans for a separate explicit M136 ingestion path.",
    "Profile selection considers task type, changed path class, and risk class before any completion evidence can be trusted.",
)

_PROHIBITED_OPERATIONS: tuple[str, ...] = (
    "merge_pull_request",
    "force_push",
    "update_protected_branch",
    "enable_auto_merge",
    "create_release",
    "modify_github_workflow",
    "apply_source_patch_from_generated_output",
    "automatic_next_item_execution",
    "bypass_machine_safety_gate",
    "run_validation_commands_from_inspector",
)


def inspect_codex_validation_profiles(
    config: AppConfig,
    *,
    item_id: str = DEFAULT_ITEM_ID,
    project_id: str = DEFAULT_PROJECT_ID,
    queue_path: str | Path | None = None,
    task_type: str | None = None,
    risk_class: str | None = None,
    changed_paths: list[str] | tuple[str, ...] | None = None,
    output: str | Path | None = None,
    force: bool = False,
    output_format: str = "json",
    command_runner: CommandRunner | None = None,
) -> dict[str, Any]:
    fmt = str(output_format or "json").strip().lower()
    if fmt != "json":
        return _error("invalid_format", {"format": output_format, "supported_formats": ["json"]})

    normalized_item_id = str(item_id or DEFAULT_ITEM_ID).strip() or DEFAULT_ITEM_ID
    normalized_project_id = str(project_id or DEFAULT_PROJECT_ID).strip() or DEFAULT_PROJECT_ID
    queue = _load_queue(config, queue_path=queue_path)
    item = _find_item(queue, normalized_item_id)
    git_paths = _git_changed_paths(config.repo_root, command_runner=command_runner)
    supplied_paths = _dedupe(_list(changed_paths))
    effective_paths = supplied_paths or git_paths
    resolved_task_type = _normalize_task_type(task_type or item.get("item_type") or item.get("type"))
    resolved_risk_class = _normalize_risk_class(risk_class or _item_risk_class(item))
    path_summary = _path_summary(effective_paths)
    selected_profile = select_codex_validation_profile(
        task_type=resolved_task_type,
        changed_paths=effective_paths,
        risk_class=resolved_risk_class,
    )

    gate_payload = _gate_payload(config, item_id=normalized_item_id, queue_path=queue_path)
    gate_summary = _gate_summary(gate_payload)
    warnings = _warnings(
        item=item,
        gate_payload=gate_payload,
        project_id=normalized_project_id,
        effective_paths=effective_paths,
    )
    blocked_reasons = _blocked_reasons(item=item, gate_payload=gate_payload)
    blocked = bool(blocked_reasons)

    payload: dict[str, Any] = {
        "record_type": PROFILE_RECORD_TYPE,
        "artifact_type": PROFILE_RECORD_TYPE,
        "profile_version": PROFILE_VERSION,
        "generated": True,
        "generated_at": _now_iso(),
        "item_id": normalized_item_id,
        "project_id": normalized_project_id,
        "run_id": f"{normalized_item_id}:codex-validation-profiles-v1",
        "status": "blocked" if blocked else "ready",
        "blocked": blocked,
        "blocked_reasons": blocked_reasons,
        "warnings": warnings,
        "machine_gates_checked": [gate_summary],
        "machine_gates_passed": bool(gate_summary.get("passed")),
        "artifacts_created": [],
        "mutation_performed": False,
        "external_execution_performed": False,
        "model_execution_performed": False,
        "codex_execution_performed": False,
        "github_execution_performed": False,
        "patch_application_performed": False,
        "validation_command_execution_performed": False,
        "local_only": True,
        "next_safe_action": _next_safe_action(blocked=blocked, selected_profile=selected_profile),
        "queue_item_found": bool(item),
        "queue_item_status": str(item.get("status", "")).strip(),
        "queue_path": str(resolve_project_queue_path(config.repo_root, queue_path)),
        "task_type": resolved_task_type,
        "risk_class": resolved_risk_class,
        "changed_paths": effective_paths,
        "changed_path_summary": path_summary,
        "selected_profile": selected_profile,
        "recommended_validation_profiles": _recommended_profiles(
            selected_profile=selected_profile,
            path_summary=path_summary,
            risk_class=resolved_risk_class,
            task_type=resolved_task_type,
        ),
        "validation_profiles": _validation_profiles(),
        "validation_profile_selection": _selection_explanation(
            selected_profile=selected_profile,
            task_type=resolved_task_type,
            risk_class=resolved_risk_class,
            path_summary=path_summary,
        ),
        "machine_gate_profile_for_inspection": "read_only_agent",
        "m136_integration": {
            "command": "ingest-codex-result-and-validate",
            "validation_profile_argument": "--validation-profile",
            "supported_profiles": sorted(VALIDATION_PROFILE_COMMANDS),
            "inspector_runs_validation": False,
        },
        "validation_agent_summary": _validation_agent_summary(config),
        "llm_decision_policy_summary": _llm_decision_summary(
            config,
            item_id=normalized_item_id,
            queue_path=queue_path,
        ),
        "prohibited_operations": list(_PROHIBITED_OPERATIONS),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
        "recommended_profile_artifact_path": str(
            (config.repo_root / ".aresforge" / "codex_execution" / "validation_profiles" / "m144-profiles.json").resolve()
        ),
    }
    return _emit_or_write(config=config, payload=payload, output=output, force=force)


def select_codex_validation_profile(
    *,
    task_type: str | None,
    changed_paths: list[str] | tuple[str, ...] | None,
    risk_class: str | None,
) -> str:
    normalized_task = _normalize_task_type(task_type)
    normalized_risk = _normalize_risk_class(risk_class)
    path_summary = _path_summary(_list(changed_paths))
    classes = set(path_summary["path_classes"])
    if normalized_risk in {"high", "critical", "unknown"}:
        return "full_local_safe"
    if classes.intersection({"protected", "workflow"}):
        return "full_local_safe"
    if len(classes) > 1 and not classes.issubset({"documentation", "artifact"}):
        if "codex_runtime" in classes or "orchestration" in classes:
            return "codex_orchestration"
        if "queue" in classes:
            return "queue_system"
        return "full_local_safe"
    if "codex_runtime" in classes or "orchestration" in classes:
        return "codex_orchestration"
    if "queue" in classes:
        return "queue_system"
    if "hub_ui" in classes:
        return "hub_ui"
    if classes == {"tests"}:
        return "tests_only"
    if classes and classes.issubset({"documentation", "artifact"}):
        return "docs_only"
    if normalized_task in _TASK_TYPE_DEFAULTS:
        return _TASK_TYPE_DEFAULTS[normalized_task]
    return _RISK_CLASS_DEFAULTS.get(normalized_risk, "full_local_safe")


def _validation_profiles() -> list[dict[str, Any]]:
    profiles: list[dict[str, Any]] = []
    for profile_id in sorted(VALIDATION_PROFILE_COMMANDS):
        metadata = _PROFILE_METADATA.get(profile_id, {})
        profiles.append(
            {
                "profile_id": profile_id,
                "description": str(metadata.get("description", "")).strip(),
                "validation_commands": list(VALIDATION_PROFILE_COMMANDS[profile_id]),
                "task_types": _list(metadata.get("task_types")),
                "path_classes": _list(metadata.get("path_classes")),
                "risk_classes": _list(metadata.get("risk_classes")),
                "local_only": True,
                "allowlisted": True,
                "executes_from_inspector": False,
                "machine_gate_required_before_completion": "queue_status_mutation",
            }
        )
    return profiles


def _path_summary(paths: list[str]) -> dict[str, Any]:
    classes: list[str] = []
    entries: list[dict[str, str]] = []
    for path in paths:
        path_class = _path_class(path)
        classes.append(path_class)
        entries.append(
            {
                "path": path,
                "path_class": path_class,
                "risk_class": _PATH_CLASS_RISK.get(path_class, "medium"),
                "recommended_profile": _profile_for_path_class(path_class),
            }
        )
    unique_classes = _dedupe(classes)
    highest = _highest_risk([_PATH_CLASS_RISK.get(path_class, "medium") for path_class in unique_classes])
    return {
        "path_count": len(paths),
        "path_classes": unique_classes,
        "highest_path_risk_class": highest,
        "entries": entries,
        "mixed_path_classes": len(unique_classes) > 1,
    }


def _path_class(path: str) -> str:
    normalized = str(path or "").strip().replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    if not normalized:
        return "unknown"
    if normalized.startswith(".github/workflows/"):
        return "workflow"
    if normalized in {"pyproject.toml", "setup.py", "setup.cfg"} or normalized.startswith(".github/"):
        return "protected"
    if normalized.startswith("docs/"):
        return "documentation"
    if normalized.startswith("tests/"):
        return "tests"
    if normalized.startswith(".aresforge/queue/"):
        return "queue"
    if normalized.startswith("src/aresforge/hub/") or normalized.startswith("src/aresforge/hub/static/"):
        return "hub_ui"
    if "codex" in normalized and normalized.startswith("src/aresforge/operator/"):
        return "codex_runtime"
    if "orchestr" in normalized and normalized.startswith("src/aresforge/operator/"):
        return "orchestration"
    if normalized.startswith("src/"):
        return "source"
    if normalized.startswith("artifacts/") or normalized.startswith(".aresforge/codex_execution/"):
        return "artifact"
    return "unknown"


def _profile_for_path_class(path_class: str) -> str:
    if path_class == "documentation":
        return "docs_only"
    if path_class == "tests":
        return "tests_only"
    if path_class == "hub_ui":
        return "hub_ui"
    if path_class == "queue":
        return "queue_system"
    if path_class in {"codex_runtime", "orchestration"}:
        return "codex_orchestration"
    if path_class in {"protected", "workflow"}:
        return "full_local_safe"
    return "code_unit_tests"


def _recommended_profiles(
    *,
    selected_profile: str,
    path_summary: dict[str, Any],
    risk_class: str,
    task_type: str,
) -> list[dict[str, Any]]:
    candidates = [selected_profile]
    for entry in path_summary.get("entries", []):
        if isinstance(entry, dict):
            candidates.append(str(entry.get("recommended_profile", "")).strip())
    candidates.append(_TASK_TYPE_DEFAULTS.get(task_type, ""))
    candidates.append(_RISK_CLASS_DEFAULTS.get(risk_class, ""))
    deduped = [candidate for candidate in _dedupe(candidates) if candidate in VALIDATION_PROFILE_COMMANDS]
    return [
        {
            "profile_id": profile_id,
            "selected": profile_id == selected_profile,
            "validation_commands": list(VALIDATION_PROFILE_COMMANDS[profile_id]),
        }
        for profile_id in deduped
    ]


def _selection_explanation(
    *,
    selected_profile: str,
    task_type: str,
    risk_class: str,
    path_summary: dict[str, Any],
) -> dict[str, Any]:
    reasons = [
        f"task_type={task_type}",
        f"risk_class={risk_class}",
        "path_classes=" + ",".join(path_summary.get("path_classes", []) or ["none"]),
    ]
    if risk_class in {"high", "critical", "unknown"}:
        reasons.append("high_or_unknown_risk_requires_broad_local_safe_profile")
    if path_summary.get("mixed_path_classes"):
        reasons.append("mixed_path_classes_require_profile_expansion")
    return {
        "selected_profile": selected_profile,
        "selection_reasons": reasons,
        "fallback_profile": "full_local_safe",
        "selector_inputs": {
            "task_type": task_type,
            "risk_class": risk_class,
            "path_classes": path_summary.get("path_classes", []),
        },
    }


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
        str(check.get("check_id", "")).strip()
        for check in checks
        if isinstance(check, dict) and not bool(check.get("passed")) and not bool(check.get("warning_only"))
    ]
    return {
        "gate_profile": str(gate_payload.get("gate_profile", "read_only_agent")).strip() or "read_only_agent",
        "passed": bool(gate_payload.get("passed")) and not bool(gate_payload.get("blocked")),
        "blocked": bool(gate_payload.get("blocked")),
        "blocked_reasons": _list(gate_payload.get("blocked_reasons")),
        "checks_failed": failed,
    }


def _validation_agent_summary(config: AppConfig) -> dict[str, Any]:
    registry = build_agent_registry(config, agent_id="validation-agent")
    agents = registry.get("agents", []) if isinstance(registry, dict) else []
    agent = agents[0] if agents and isinstance(agents[0], dict) else {}
    return {
        "agent_id": str(agent.get("agent_id", "validation-agent")).strip() or "validation-agent",
        "can_run_real": bool(agent.get("can_run_real")),
        "can_run_dry_run": bool(agent.get("can_run_dry_run")),
        "machine_gate_required": bool(agent.get("machine_gate_required", True)),
        "default_execution_mode": str(agent.get("default_execution_mode", "")).strip(),
        "forbidden_capabilities": _list(agent.get("forbidden_capabilities")),
    }


def _llm_decision_summary(
    config: AppConfig,
    *,
    item_id: str,
    queue_path: str | Path | None,
) -> dict[str, Any]:
    result = recommend_llm_decision(
        config,
        item_id=item_id,
        queue_path=queue_path,
        output_format="json",
    )
    payload = result.get("payload", {}) if isinstance(result, dict) else {}
    return {
        "recommendation_type": str(payload.get("recommendation_type", "")).strip(),
        "item_found": bool(payload.get("item_found")),
        "recommended_lane": str(payload.get("recommended_lane", "")).strip(),
        "recommended_provider": str(payload.get("recommended_provider", "")).strip(),
        "machine_gate_required": bool(payload.get("machine_gate_required")),
        "execution_performed": bool(payload.get("execution_performed")),
        "next_safe_action": str(payload.get("next_safe_action", "")).strip(),
    }


def _git_changed_paths(repo_root: Path, *, command_runner: CommandRunner | None) -> list[str]:
    runner = command_runner or subprocess.run
    try:
        completed = runner(
            ["git", "status", "--short"],
            cwd=str(repo_root.resolve()),
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    files: list[str] = []
    stdout = _decode_output(getattr(completed, "stdout", ""))
    for line in stdout.splitlines():
        if not line.strip() or len(line) < 4:
            continue
        candidate = line[3:].strip()
        if " -> " in candidate:
            candidate = candidate.split(" -> ", 1)[1].strip()
        if candidate:
            files.append(candidate.replace("\\", "/"))
    return _dedupe(files)


def _warnings(
    *,
    item: dict[str, Any],
    gate_payload: dict[str, Any],
    project_id: str,
    effective_paths: list[str],
) -> list[str]:
    warnings = _list(gate_payload.get("warnings"))
    if item and str(item.get("project_id", "")).strip() != project_id:
        warnings.append("Queue item project_id does not match the requested project_id.")
    if item and str(item.get("status", "")).strip() == "done":
        warnings.append("Queue item is already done; this profile remains useful as a stable validation contract.")
    if not effective_paths:
        warnings.append("No changed paths were supplied or detected; selection falls back to task and risk metadata.")
    return _dedupe(warnings)


def _blocked_reasons(*, item: dict[str, Any], gate_payload: dict[str, Any]) -> list[str]:
    reasons = _list(gate_payload.get("blocked_reasons"))
    if not item:
        reasons.append("Queue item must exist before this validation profile contract can be used as local capability evidence.")
    return _dedupe(reasons)


def _next_safe_action(*, blocked: bool, selected_profile: str) -> str:
    if blocked:
        return "Resolve read-only machine gate blockers before relying on Codex validation profile metadata."
    return (
        "Use the selected profile with a separate explicit M136 ingestion command after Codex output is captured; "
        f"recommended profile: {selected_profile}."
    )


def _item_risk_class(item: dict[str, Any]) -> str:
    routing = item.get("routing_metadata", {}) if isinstance(item, dict) else {}
    if isinstance(routing, dict):
        risk = str(routing.get("risk_level", "")).strip()
        if risk:
            return risk
    tags = set(_list(item.get("tags"))) if isinstance(item, dict) else set()
    if any("critical" in tag or "high-risk" in tag for tag in tags):
        return "critical"
    if any("machine-gated" in tag or "codex" in tag or "orchestration" in tag for tag in tags):
        return "high"
    return "unknown"


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
        if isinstance(item, dict) and str(item.get("item_id", "")).strip() == item_id:
            return item
    return {}


def _normalize_task_type(value: Any) -> str:
    text = str(value or "").strip().lower().replace("-", "_")
    return text if text else "unknown"


def _normalize_risk_class(value: Any) -> str:
    text = str(value or "").strip().lower().replace("-", "_")
    if text in {"low", "medium", "high", "critical"}:
        return text
    return "unknown"


def _highest_risk(values: list[str]) -> str:
    order = {"low": 0, "medium": 1, "high": 2, "critical": 3, "unknown": 1}
    if not values:
        return "unknown"
    return max(values, key=lambda value: order.get(value, 1))


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
    artifact_payload["artifacts_created"] = [str(output_path)]
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


def _decode_output(value: bytes | str | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8-sig", errors="replace")
    return str(value)


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
