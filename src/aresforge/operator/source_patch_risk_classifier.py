from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import re
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.agent_registry import build_agent_registry
from aresforge.operator.codex_validation_profiles import (
    VALIDATION_PROFILE_COMMANDS,
    select_codex_validation_profile,
)
from aresforge.operator.llm_decision_policy import recommend_llm_decision
from aresforge.operator.local_project_queue import resolve_project_queue_path
from aresforge.operator.machine_safety_gate_engine import evaluate_machine_safety_gates

COMMAND_NAME = "classify-source-patch-risk"
RECORD_TYPE = "source_patch_risk_classification_v1"
CLASSIFIER_VERSION = "m148.1"
DEFAULT_ITEM_ID = "m148-safe-source-patch-detection-and-risk-classifier"
DEFAULT_PROJECT_ID = "aresforge"

_RISK_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3, "unknown": 1}
_PATH_RISKS: dict[str, str] = {
    "documentation": "low",
    "artifact": "low",
    "tests": "medium",
    "source": "medium",
    "hub_ui": "medium",
    "orchestration": "high",
    "codex_runtime": "high",
    "queue_state": "high",
    "script": "high",
    "config": "high",
    "protected": "critical",
    "workflow": "critical",
    "outside_repo": "critical",
    "unknown": "medium",
}

_PROTECTED_EXACT = frozenset(
    {
        "pyproject.toml",
        "poetry.lock",
        "requirements.txt",
        "requirements-dev.txt",
        "setup.py",
        "setup.cfg",
        "package.json",
        "package-lock.json",
        "pnpm-lock.yaml",
        "yarn.lock",
        "tsconfig.json",
        "vite.config.js",
        "vite.config.ts",
    }
)

_PROHIBITED_OPERATIONS: tuple[str, ...] = (
    "merge_pull_request",
    "force_push",
    "update_protected_branch",
    "enable_auto_merge",
    "create_release",
    "modify_github_workflow",
    "bypass_machine_safety_gate",
    "apply_source_patch_from_generated_output",
    "run_validation_commands_from_classifier",
    "automatic_next_item_execution",
)

_BOUNDARY_CONFIRMATIONS: tuple[str, ...] = (
    "M148 classifies local source patch risk without applying the patch.",
    "M148 parses touched files, mutation types, blocked operations, and validation requirements.",
    "M148 performs no agent, Codex, model, GitHub, validation-command, patch, queue, or external execution.",
    "Source patch application remains blocked until a separate explicit human-gated or future machine-gated apply path exists.",
)


def classify_source_patch_risk(
    config: AppConfig,
    *,
    patch_path: str | Path,
    item_id: str = DEFAULT_ITEM_ID,
    project_id: str = DEFAULT_PROJECT_ID,
    queue_path: str | Path | None = None,
    output: str | Path | None = None,
    force: bool = False,
    output_format: str = "json",
) -> dict[str, Any]:
    fmt = str(output_format or "json").strip().lower()
    if fmt != "json":
        return _error("invalid_format", {"format": output_format, "supported_formats": ["json"]})

    normalized_item_id = str(item_id or DEFAULT_ITEM_ID).strip() or DEFAULT_ITEM_ID
    normalized_project_id = str(project_id or DEFAULT_PROJECT_ID).strip() or DEFAULT_PROJECT_ID
    resolved_patch_path = _resolve(config.repo_root, patch_path)
    patch_text, patch_errors = _read_patch(resolved_patch_path)
    analysis = analyze_source_patch(patch_text)
    gate_payload = _gate_payload(config, item_id=normalized_item_id, queue_path=queue_path)
    gate_summary = _gate_summary(gate_payload)

    blocked_reasons = _blocked_reasons(patch_errors=patch_errors, analysis=analysis, gate_payload=gate_payload)
    blocked = bool(blocked_reasons)
    selected_profile = select_codex_validation_profile(
        task_type="orchestration" if analysis["codex_or_orchestration_touched"] else "feature",
        changed_paths=analysis["touched_files"],
        risk_class=analysis["risk_level"],
    )

    payload: dict[str, Any] = {
        "record_type": RECORD_TYPE,
        "artifact_type": RECORD_TYPE,
        "classifier_version": CLASSIFIER_VERSION,
        "generated": True,
        "generated_at": _now_iso(),
        "item_id": normalized_item_id,
        "project_id": normalized_project_id,
        "run_id": f"{normalized_item_id}:source-patch-risk-v1",
        "status": "blocked" if blocked else "classified",
        "blocked": blocked,
        "blocked_reasons": blocked_reasons,
        "warnings": _warnings(patch_errors=patch_errors, analysis=analysis, gate_payload=gate_payload),
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
        "next_safe_action": _next_safe_action(blocked=blocked, risk_level=analysis["risk_level"]),
        "patch_path": str(resolved_patch_path),
        "patch_file_found": resolved_patch_path.exists(),
        "patch_parse_status": "parsed" if not patch_errors and analysis["touched_files"] else "invalid",
        "touched_files": analysis["touched_files"],
        "touched_file_count": len(analysis["touched_files"]),
        "touched_file_details": analysis["file_details"],
        "path_classes": analysis["path_classes"],
        "risk_level": analysis["risk_level"],
        "risk_reasons": analysis["risk_reasons"],
        "mutation_type": analysis["mutation_type"],
        "mutation_types": analysis["mutation_types"],
        "blocked_operations": analysis["blocked_operations"],
        "blocked_operation_detected": any(bool(entry.get("detected")) for entry in analysis["blocked_operations"]),
        "source_code_touched": "source" in analysis["path_classes"],
        "tests_touched": "tests" in analysis["path_classes"],
        "documentation_touched": "documentation" in analysis["path_classes"],
        "workflow_touched": "workflow" in analysis["path_classes"],
        "protected_paths_touched": any(
            path_class in analysis["path_classes"]
            for path_class in ("protected", "config", "script", "queue_state", "outside_repo")
        ),
        "binary_patch_detected": analysis["binary_patch_detected"],
        "executable_or_mode_change_detected": analysis["executable_or_mode_change_detected"],
        "patch_application_allowed_by_classifier": False,
        "source_patch_application_requires_separate_gate": True,
        "test_requirements": _test_requirements(selected_profile, analysis),
        "recommended_validation_profile": selected_profile,
        "queue_path": str(resolve_project_queue_path(config.repo_root, queue_path)),
        "machine_gate_profile_for_inspection": "read_only_agent",
        "agent_registry_summary": _agent_summary(config),
        "llm_decision_policy_summary": _llm_decision_summary(
            config,
            item_id=normalized_item_id,
            queue_path=queue_path,
        ),
        "prohibited_operations": list(_PROHIBITED_OPERATIONS),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
        "recommended_classification_artifact_path": str(
            (config.repo_root / ".aresforge" / "source_patch_risk" / "m148-classification.json").resolve()
        ),
    }
    return _emit_or_write(config=config, payload=payload, output=output, force=force)


def analyze_source_patch(patch_text: str) -> dict[str, Any]:
    chunks = _patch_chunks(patch_text)
    file_details = [_file_detail(chunk) for chunk in chunks]
    if not file_details and patch_text.strip():
        file_details = [_fallback_detail(path) for path in _fallback_targets(patch_text)]
    touched_files = _dedupe([detail["path"] for detail in file_details])
    path_classes = _dedupe([detail["path_class"] for detail in file_details])
    mutation_types = _dedupe(
        mutation for detail in file_details for mutation in _list(detail.get("mutation_types"))
    )
    binary_patch_detected = "binary" in mutation_types or "GIT binary patch" in patch_text or "Binary files " in patch_text
    executable_or_mode_change_detected = any(
        mutation in mutation_types for mutation in ("mode_change", "executable_mode_change")
    )
    risk_reasons = _risk_reasons(
        file_details=file_details,
        path_classes=path_classes,
        mutation_types=mutation_types,
        binary_patch_detected=binary_patch_detected,
        executable_or_mode_change_detected=executable_or_mode_change_detected,
    )
    risk_level = _highest_risk([detail["risk_level"] for detail in file_details] + [reason["risk_level"] for reason in risk_reasons])
    return {
        "touched_files": touched_files,
        "file_details": file_details,
        "path_classes": path_classes,
        "risk_level": risk_level,
        "risk_reasons": risk_reasons,
        "mutation_type": _primary_mutation_type(path_classes=path_classes, mutation_types=mutation_types),
        "mutation_types": mutation_types,
        "blocked_operations": _blocked_operations(
            path_classes=path_classes,
            mutation_types=mutation_types,
            binary_patch_detected=binary_patch_detected,
            executable_or_mode_change_detected=executable_or_mode_change_detected,
        ),
        "binary_patch_detected": binary_patch_detected,
        "executable_or_mode_change_detected": executable_or_mode_change_detected,
        "codex_or_orchestration_touched": any(path_class in {"codex_runtime", "orchestration"} for path_class in path_classes),
    }


def _patch_chunks(patch_text: str) -> list[str]:
    chunks: list[str] = []
    current: list[str] = []
    for line in patch_text.splitlines():
        if line.startswith("diff --git "):
            if current:
                chunks.append("\n".join(current))
            current = [line]
        elif current:
            current.append(line)
    if current:
        chunks.append("\n".join(current))
    return chunks


def _file_detail(chunk: str) -> dict[str, Any]:
    lines = chunk.splitlines()
    old_path = ""
    new_path = ""
    diff_line = lines[0] if lines else ""
    if diff_line.startswith("diff --git "):
        parts = diff_line.split()
        if len(parts) >= 4:
            old_path = _normalize_patch_target(parts[2])
            new_path = _normalize_patch_target(parts[3])
    for line in lines:
        if line.startswith("--- "):
            value = line[4:].strip()
            if value != "/dev/null":
                old_path = _normalize_patch_target(value)
        elif line.startswith("+++ "):
            value = line[4:].strip()
            if value != "/dev/null":
                new_path = _normalize_patch_target(value)
        elif line.startswith("rename from "):
            old_path = _normalize_patch_target(line.removeprefix("rename from ").strip())
        elif line.startswith("rename to "):
            new_path = _normalize_patch_target(line.removeprefix("rename to ").strip())

    target = new_path or old_path
    mutation_types = _mutation_types(lines, old_path=old_path, new_path=new_path)
    added_lines = sum(1 for line in lines if line.startswith("+") and not line.startswith("+++"))
    removed_lines = sum(1 for line in lines if line.startswith("-") and not line.startswith("---"))
    path_class = _path_class(target)
    risk_level = _file_risk(path_class=path_class, mutation_types=mutation_types)
    return {
        "path": target,
        "old_path": old_path,
        "new_path": new_path,
        "path_class": path_class,
        "risk_level": risk_level,
        "mutation_types": mutation_types,
        "added_lines": added_lines,
        "removed_lines": removed_lines,
        "binary": "binary" in mutation_types,
        "mode_change": any(mutation in mutation_types for mutation in ("mode_change", "executable_mode_change")),
    }


def _fallback_targets(patch_text: str) -> list[str]:
    targets: list[str] = []
    for line in patch_text.splitlines():
        if line.startswith(("+++ ", "--- ")):
            value = line[4:].strip()
            if value != "/dev/null":
                targets.append(_normalize_patch_target(value))
    return _dedupe(targets)


def _fallback_detail(path: str) -> dict[str, Any]:
    path_class = _path_class(path)
    return {
        "path": path,
        "old_path": path,
        "new_path": path,
        "path_class": path_class,
        "risk_level": _PATH_RISKS.get(path_class, "medium"),
        "mutation_types": ["modified"],
        "added_lines": 0,
        "removed_lines": 0,
        "binary": False,
        "mode_change": False,
    }


def _mutation_types(lines: list[str], *, old_path: str, new_path: str) -> list[str]:
    mutations: list[str] = []
    if any(line.startswith("new file mode ") for line in lines):
        mutations.append("added")
    if any(line.startswith("deleted file mode ") for line in lines):
        mutations.append("deleted")
    if any(line.startswith("rename ") or line.startswith("rename from ") or line.startswith("rename to ") for line in lines):
        mutations.append("renamed")
    if any(line.startswith(("old mode ", "new mode ")) for line in lines):
        mutations.append("mode_change")
    if any(line.startswith("new mode ") and line.rstrip().endswith("755") for line in lines):
        mutations.append("executable_mode_change")
    if "GIT binary patch" in "\n".join(lines) or any(line.startswith("Binary files ") for line in lines):
        mutations.append("binary")
    if not mutations:
        if old_path and not new_path:
            mutations.append("deleted")
        elif new_path and not old_path:
            mutations.append("added")
        else:
            mutations.append("modified")
    return _dedupe(mutations)


def _path_class(path: str) -> str:
    normalized = str(path or "").strip().replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    if not normalized:
        return "unknown"
    if normalized == "__outside_repo__" or normalized.startswith("../"):
        return "outside_repo"
    if normalized.startswith(".github/workflows/"):
        return "workflow"
    if normalized in _PROTECTED_EXACT or normalized.startswith(".github/"):
        return "protected"
    if normalized.startswith(".aresforge/queue/"):
        return "queue_state"
    if normalized.startswith("scripts/"):
        return "script"
    if normalized.startswith("docs/"):
        return "documentation"
    if normalized.startswith("tests/"):
        return "tests"
    if normalized.startswith("artifacts/") or normalized.startswith(".aresforge/"):
        return "artifact"
    if normalized.startswith("src/aresforge/hub/") or normalized.startswith("src/aresforge/hub/static/"):
        return "hub_ui"
    if normalized.startswith("src/aresforge/operator/") and "codex" in normalized:
        return "codex_runtime"
    if normalized.startswith("src/aresforge/operator/") and ("orchestr" in normalized or "agent" in normalized):
        return "orchestration"
    if normalized.startswith("src/"):
        return "source"
    if normalized.endswith((".toml", ".lock", ".json", ".yaml", ".yml", ".ini", ".cfg")):
        return "config"
    return "unknown"


def _file_risk(*, path_class: str, mutation_types: list[str]) -> str:
    if "binary" in mutation_types or "executable_mode_change" in mutation_types:
        return "critical"
    if "deleted" in mutation_types and path_class in {"source", "orchestration", "codex_runtime", "queue_state"}:
        return "high"
    return _PATH_RISKS.get(path_class, "medium")


def _risk_reasons(
    *,
    file_details: list[dict[str, Any]],
    path_classes: list[str],
    mutation_types: list[str],
    binary_patch_detected: bool,
    executable_or_mode_change_detected: bool,
) -> list[dict[str, str]]:
    reasons: list[dict[str, str]] = []
    for path_class in path_classes:
        reasons.append(
            {
                "reason": f"path_class:{path_class}",
                "risk_level": _PATH_RISKS.get(path_class, "medium"),
            }
        )
    if len(path_classes) > 1 and not set(path_classes).issubset({"documentation", "artifact"}):
        reasons.append({"reason": "mixed_non_documentation_paths", "risk_level": "high"})
    if binary_patch_detected:
        reasons.append({"reason": "binary_patch_detected", "risk_level": "critical"})
    if executable_or_mode_change_detected:
        reasons.append({"reason": "executable_or_mode_change_detected", "risk_level": "critical"})
    if any("deleted" in _list(detail.get("mutation_types")) for detail in file_details):
        reasons.append({"reason": "file_deletion_detected", "risk_level": "high"})
    return reasons or [{"reason": "no_patch_targets_detected", "risk_level": "unknown"}]


def _primary_mutation_type(*, path_classes: list[str], mutation_types: list[str]) -> str:
    if "binary" in mutation_types:
        return "binary_change"
    if any(mutation in mutation_types for mutation in ("mode_change", "executable_mode_change")):
        return "permission_change"
    if len(path_classes) > 1:
        return "mixed_change"
    only = path_classes[0] if path_classes else "unknown"
    if only == "source":
        return "source_code_change"
    if only == "tests":
        return "test_change"
    if only == "documentation":
        return "documentation_change"
    if only == "workflow":
        return "workflow_change"
    if only in {"protected", "config"}:
        return "config_change"
    if only in {"orchestration", "codex_runtime"}:
        return "orchestration_code_change"
    return "unknown_change"


def _blocked_operations(
    *,
    path_classes: list[str],
    mutation_types: list[str],
    binary_patch_detected: bool,
    executable_or_mode_change_detected: bool,
) -> list[dict[str, Any]]:
    entries = [
        _blocked_operation(
            "source_patch_application",
            detected=any(path_class in path_classes for path_class in ("source", "hub_ui", "orchestration", "codex_runtime")),
            severity="high",
            message="Source/code patches are classification-only in M148 and cannot be applied by this command.",
        ),
        _blocked_operation(
            "workflow_mutation",
            detected="workflow" in path_classes,
            severity="critical",
            message="GitHub workflow changes are blocked by orchestrator safety policy.",
        ),
        _blocked_operation(
            "protected_config_mutation",
            detected=any(path_class in path_classes for path_class in ("protected", "config", "script")),
            severity="high",
            message="Protected config or script changes require explicit operator review and expanded validation.",
        ),
        _blocked_operation(
            "queue_state_mutation",
            detected="queue_state" in path_classes,
            severity="high",
            message="Queue state patch mutation is blocked outside dedicated queue commands.",
        ),
        _blocked_operation(
            "binary_patch_application",
            detected=binary_patch_detected,
            severity="critical",
            message="Binary patches are blocked for autonomous patch handling.",
        ),
        _blocked_operation(
            "executable_or_mode_change",
            detected=executable_or_mode_change_detected or "mode_change" in mutation_types,
            severity="critical",
            message="Executable or file-mode changes are blocked for autonomous patch handling.",
        ),
        _blocked_operation(
            "outside_repo_path",
            detected="outside_repo" in path_classes,
            severity="critical",
            message="Patch paths must not traverse outside the repository.",
        ),
    ]
    return entries


def _blocked_operation(operation_id: str, *, detected: bool, severity: str, message: str) -> dict[str, Any]:
    return {
        "operation_id": operation_id,
        "detected": bool(detected),
        "severity": severity,
        "blocks_automatic_apply": True,
        "message": message,
    }


def _test_requirements(selected_profile: str, analysis: dict[str, Any]) -> dict[str, Any]:
    commands = list(VALIDATION_PROFILE_COMMANDS.get(selected_profile, ()))
    required_checks = ["git diff --check"]
    if analysis["risk_level"] in {"high", "critical"} and "python -m pytest tests/test_cli.py" not in commands:
        required_checks.append("python -m pytest tests/test_cli.py")
    return {
        "required_before_apply_or_completion": True,
        "recommended_validation_profile": selected_profile,
        "validation_commands": commands,
        "additional_required_checks": _dedupe(required_checks),
        "requires_operator_diff_review": True,
        "requires_machine_gate_before_apply": True,
        "requires_source_patch_apply_gate": True,
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


def _blocked_reasons(*, patch_errors: list[str], analysis: dict[str, Any], gate_payload: dict[str, Any]) -> list[str]:
    reasons = [*patch_errors, *_list(gate_payload.get("blocked_reasons"))]
    if not analysis["touched_files"]:
        reasons.append("Patch does not declare any target files.")
    if "outside_repo" in analysis["path_classes"]:
        reasons.append("Patch declares a path outside the repository.")
    return _dedupe(reasons)


def _warnings(*, patch_errors: list[str], analysis: dict[str, Any], gate_payload: dict[str, Any]) -> list[str]:
    warnings = [*_list(gate_payload.get("warnings")), *patch_errors]
    if any(bool(entry.get("detected")) for entry in analysis.get("blocked_operations", [])):
        warnings.append("Patch contains operations that block automatic apply.")
    if analysis["risk_level"] in {"high", "critical"}:
        warnings.append("Patch risk is high enough to require expanded validation and operator review.")
    return _dedupe(warnings)


def _agent_summary(config: AppConfig) -> dict[str, Any]:
    registry = build_agent_registry(config, agent_id="validation-agent")
    agents = registry.get("agents", []) if isinstance(registry, dict) else []
    agent = agents[0] if agents and isinstance(agents[0], dict) else {}
    return {
        "agent_id": str(agent.get("agent_id", "validation-agent")).strip() or "validation-agent",
        "agent_found": bool(agent),
        "can_run_real": bool(agent.get("can_run_real")),
        "can_run_dry_run": bool(agent.get("can_run_dry_run")),
        "machine_gate_required": bool(agent.get("machine_gate_required", True)),
        "forbidden_capabilities": _list(agent.get("forbidden_capabilities")),
    }


def _llm_decision_summary(config: AppConfig, *, item_id: str, queue_path: str | Path | None) -> dict[str, Any]:
    result = recommend_llm_decision(config, item_id=item_id, queue_path=queue_path, output_format="json")
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


def _next_safe_action(*, blocked: bool, risk_level: str) -> str:
    if blocked:
        return "Resolve classifier blockers before relying on this source patch risk record."
    if risk_level in {"high", "critical"}:
        return "Treat this as operator-review evidence only; do not apply the source patch without a separate explicit gate and expanded validation."
    return "Use this classification as planning evidence; any future patch apply must use a separate explicit gated command."


def _read_patch(path: Path) -> tuple[str, list[str]]:
    if not path.exists():
        return "", [f"Patch file is missing: {path}"]
    try:
        return path.read_text(encoding="utf-8-sig"), []
    except UnicodeDecodeError:
        return "", [f"Patch file is not UTF-8 text: {path}"]
    except OSError as exc:
        return "", [f"Patch file could not be read: {exc}"]


def _normalize_patch_target(value: str) -> str:
    text = value.strip().replace("\\", "/")
    if text.startswith('"') and text.endswith('"'):
        text = text[1:-1]
    text = re.sub(r"^[ab]/", "", text).lstrip("/")
    parts = [part for part in text.split("/") if part not in {"", "."}]
    if any(part == ".." for part in parts):
        return "__outside_repo__"
    return "/".join(parts)


def _highest_risk(values: list[str]) -> str:
    if not values:
        return "unknown"
    return max(values, key=lambda value: _RISK_ORDER.get(value, 1))


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


def _resolve(repo_root: Path, value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


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
