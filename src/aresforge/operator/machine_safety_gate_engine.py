from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
import re
import subprocess
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.local_project_queue import (
    QUEUE_STATUSES,
    resolve_project_queue_path,
)

COMMAND_NAME = "evaluate-machine-safety-gates"
MACHINE_GATE_VERSION = "m131.1"

GATE_PROFILES: tuple[str, ...] = (
    "read_only_agent",
    "local_artifact_write",
    "queue_status_mutation",
    "docs_only_patch_apply",
    "local_llm_execution",
    "codex_dispatch",
    "github_sync",
    "multi_agent_orchestration",
)

_FORBIDDEN_CAPABILITIES: tuple[str, ...] = (
    "apply_patch",
    "mutate_queue_without_operator",
    "call_github_api",
    "call_gh",
    "call_external_network",
    "create_pr_or_issue",
    "background_daemon",
    "automatic_next_item_execution",
    "execute_codex",
    "execute_ollama_prompt",
    "execute_local_llm",
    "run_validation_commands",
)

_DOCS_ONLY_PATHS: tuple[str, ...] = (
    "docs/",
    ".aresforge/queue/work_items.json",
)


@dataclass(frozen=True)
class GateProfile:
    profile: str
    allowed_paths: tuple[str, ...]
    required_paths: tuple[str, ...] = ()
    require_artifact: bool = False
    require_patch: bool = False
    require_execution_record: bool = False
    require_tests: bool = False
    require_transaction_log: bool = False
    require_external_allowance: bool = False
    warning_threshold: int = 5


_PROFILES: dict[str, GateProfile] = {
    "read_only_agent": GateProfile(
        profile="read_only_agent",
        allowed_paths=("docs/", "src/", "tests/", ".aresforge/", "artifacts/"),
    ),
    "local_artifact_write": GateProfile(
        profile="local_artifact_write",
        allowed_paths=("artifacts/", ".aresforge/"),
    ),
    "queue_status_mutation": GateProfile(
        profile="queue_status_mutation",
        allowed_paths=(".aresforge/queue/work_items.json", ".aresforge/queue/transaction_log.json"),
        required_paths=(".aresforge/queue/transaction_log.json",),
        require_transaction_log=True,
        require_tests=True,
    ),
    "docs_only_patch_apply": GateProfile(
        profile="docs_only_patch_apply",
        allowed_paths=(*_DOCS_ONLY_PATHS, "artifacts/"),
        require_patch=True,
        require_tests=True,
    ),
    "local_llm_execution": GateProfile(
        profile="local_llm_execution",
        allowed_paths=("artifacts/", ".aresforge/local_llm_environment.json"),
        require_artifact=True,
        require_execution_record=True,
        require_tests=True,
    ),
    "codex_dispatch": GateProfile(
        profile="codex_dispatch",
        allowed_paths=("artifacts/", ".aresforge/codex_dispatch/"),
        require_artifact=True,
        require_execution_record=True,
        require_external_allowance=True,
        require_tests=True,
    ),
    "github_sync": GateProfile(
        profile="github_sync",
        allowed_paths=("artifacts/", ".aresforge/github-sync/"),
        require_artifact=True,
        require_execution_record=True,
        require_external_allowance=True,
        require_tests=True,
    ),
    "multi_agent_orchestration": GateProfile(
        profile="multi_agent_orchestration",
        allowed_paths=("artifacts/", ".aresforge/agents/", ".aresforge/queue/"),
        require_artifact=True,
        require_execution_record=True,
        require_external_allowance=True,
        require_tests=True,
        require_transaction_log=True,
    ),
}


def evaluate_machine_safety_gates(
    config: AppConfig,
    *,
    item_id: str,
    gate_profile: str = "read_only_agent",
    artifact_path: str | Path | None = None,
    patch_path: str | Path | None = None,
    execution_record: str | Path | None = None,
    queue_path: str | Path | None = None,
    output: str | Path | None = None,
    force: bool = False,
    output_format: str = "json",
) -> dict[str, Any]:
    fmt = str(output_format or "json").strip().lower()
    if fmt != "json":
        return _error("invalid_format", {"format": output_format, "supported_formats": ["json"]})

    normalized_item_id = str(item_id or "").strip()
    normalized_profile = str(gate_profile or "read_only_agent").strip()
    profile = _PROFILES.get(normalized_profile)
    queue = _load_queue(config, queue_path=queue_path)
    item = _find_item(queue, normalized_item_id)
    artifact = _load_json_if_present(config.repo_root, artifact_path)
    record = _load_json_if_present(config.repo_root, execution_record)
    patch_text, patch_read_errors = _load_text_if_present(config.repo_root, patch_path)
    patch_targets = _patch_targets(patch_text)
    git_status = _git_status(config.repo_root)

    checks: list[dict[str, Any]] = []
    warnings: list[str] = []

    checks.append(_check("gate_profile_known", profile is not None, f"Gate profile must be one of: {', '.join(GATE_PROFILES)}."))
    active_profile = profile or _PROFILES["read_only_agent"]
    checks.extend(
        [
            _check("queue_item_exists", bool(item), "Queue item must exist in the local queue."),
            _check(
                "item_status_valid",
                _item_status_valid(item),
                f"Queue item status must be one of: {', '.join(QUEUE_STATUSES)}.",
            ),
            _check(
                "dependencies_satisfied",
                _dependencies_satisfied(queue, item),
                "Dependencies must exist and be done; blocked_by must be empty.",
            ),
            _check(
                "required_artifacts_exist",
                _required_artifacts_exist(active_profile, artifact_path, patch_path, execution_record, config),
                "Profile-required artifacts, patches, records, and logs must exist.",
            ),
            _check(
                "artifact_schema_valid",
                _artifact_schema_valid(artifact, required=active_profile.require_artifact),
                "Supplied artifact JSON must be an object and confirm local-only/non-execution when those fields are present.",
            ),
            _check(
                "execution_record_valid",
                _execution_record_valid(record, required=active_profile.require_execution_record),
                "Supplied execution record JSON must be an object with local_only=true and no blocked execution flags.",
            ),
            _check(
                "forbidden_capabilities_not_used",
                _forbidden_capabilities_not_used(artifact.get("data"), record.get("data")),
                "Artifacts and execution records must not report forbidden capabilities as used.",
            ),
            _check(
                "working_tree_acceptable",
                _working_tree_acceptable(active_profile, git_status),
                "Working tree must be acceptable for the requested profile.",
                warning_only=active_profile.profile in {"read_only_agent", "local_artifact_write"},
            ),
            _check(
                "file_path_allowlist_respected",
                _path_allowlist_respected(
                    config.repo_root,
                    active_profile,
                    artifact_path=artifact_path,
                    patch_path=patch_path,
                    execution_record=execution_record,
                    patch_targets=patch_targets,
                ),
                "Supplied artifact, patch, execution-record, and patch-target paths must stay inside the profile allowlist.",
            ),
            _check(
                "docs_only_patch_check",
                _docs_only_patch_check(active_profile, patch_path, patch_read_errors, patch_targets),
                "Docs-only patch profiles may target only docs/ and approved source-of-truth queue metadata.",
            ),
            _check(
                "tests_reported_or_runnable",
                _tests_reported_or_runnable(active_profile, item, artifact.get("data"), record.get("data")),
                "Profiles that can mutate or execute must include test evidence or runnable validation commands.",
            ),
            _check(
                "warnings_below_threshold",
                True,
                f"Warnings must stay at or below threshold {active_profile.warning_threshold}.",
            ),
            _check(
                "rollback_transaction_log_available",
                _rollback_log_available(config, active_profile),
                "Queue/status/orchestration mutation profiles require a local transaction or rollback log.",
            ),
            _check(
                "external_execution_explicitly_allowed",
                _external_execution_allowed(active_profile, force),
                "External execution profiles require explicit allowance; this evaluation still performs no external execution.",
            ),
        ]
    )

    warnings.extend(_collect_warnings(active_profile, git_status, artifact, record, patch_read_errors))
    warning_check = next(check for check in checks if check["check_id"] == "warnings_below_threshold")
    warning_check["passed"] = len(warnings) <= active_profile.warning_threshold
    warning_check["observed"] = len(warnings)

    blocking_checks = [check for check in checks if not check["passed"] and not check.get("warning_only")]
    blocked_reasons = [check["message"] for check in blocking_checks]
    passed = not blocking_checks
    blocked = not passed
    payload = {
        "gate_result_type": "machine_safety_gate_evaluation",
        "item_id": normalized_item_id,
        "gate_profile": normalized_profile,
        "passed": passed,
        "blocked": blocked,
        "blocked_reasons": blocked_reasons,
        "warnings": warnings,
        "checks": checks,
        "required_next_steps": _required_next_steps(blocked_reasons, warnings),
        "autonomy_allowed": passed,
        "human_review_required": blocked,
        "machine_gate_version": MACHINE_GATE_VERSION,
        "local_only": True,
        "execution_performed": False,
        "mutation_performed": False,
        "next_safe_action": _next_safe_action(passed, normalized_profile),
        "evaluated_at": _now_iso(),
        "queue_path": str(resolve_project_queue_path(config.repo_root, queue_path)),
        "artifact_path": str(_resolve(config.repo_root, artifact_path)) if artifact_path else "",
        "patch_path": str(_resolve(config.repo_root, patch_path)) if patch_path else "",
        "execution_record_path": str(_resolve(config.repo_root, execution_record)) if execution_record else "",
    }
    return _emit_or_write(config=config, payload=payload, output=output, force=force)


def _check(check_id: str, passed: bool, message: str, *, warning_only: bool = False) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "passed": bool(passed),
        "message": message,
        "warning_only": bool(warning_only),
    }


def _load_queue(config: AppConfig, *, queue_path: str | Path | None) -> dict[str, Any]:
    path = resolve_project_queue_path(config.repo_root, queue_path)
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
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


def _item_status_valid(item: dict[str, Any]) -> bool:
    if not item:
        return False
    return str(item.get("status", "")).strip() in QUEUE_STATUSES


def _dependencies_satisfied(queue: dict[str, Any], item: dict[str, Any]) -> bool:
    if not item:
        return False
    if _list(item.get("blocked_by")):
        return False
    by_id = {
        str(candidate.get("item_id", "")).strip(): candidate
        for candidate in queue.get("work_items", [])
        if isinstance(candidate, dict)
    }
    for dep in [*_list(item.get("dependencies")), *_list(item.get("depends_on"))]:
        if str(by_id.get(dep, {}).get("status", "")).strip() != "done":
            return False
    return True


def _required_artifacts_exist(
    profile: GateProfile,
    artifact_path: str | Path | None,
    patch_path: str | Path | None,
    execution_record: str | Path | None,
    config: AppConfig,
) -> bool:
    if profile.require_artifact and not _path_exists(config.repo_root, artifact_path):
        return False
    if profile.require_patch and not _path_exists(config.repo_root, patch_path):
        return False
    if profile.require_execution_record and not _path_exists(config.repo_root, execution_record):
        return False
    for required in profile.required_paths:
        if not (config.repo_root / required).exists():
            return False
    return True


def _artifact_schema_valid(artifact: dict[str, Any], *, required: bool) -> bool:
    if required and not artifact.get("exists"):
        return False
    if not artifact.get("exists"):
        return True
    data = artifact.get("data")
    if not isinstance(data, dict):
        return False
    if data.get("local_only") is False:
        return False
    if data.get("execution_allowed") is True:
        return False
    if data.get("execution_performed") is True:
        return False
    return True


def _execution_record_valid(record: dict[str, Any], *, required: bool) -> bool:
    if required and not record.get("exists"):
        return False
    if not record.get("exists"):
        return True
    data = record.get("data")
    if not isinstance(data, dict):
        return False
    if data.get("local_only") is not True:
        return False
    for key in (
        "external_execution_performed",
        "model_execution_performed",
        "github_execution_performed",
        "patch_application_performed",
        "queue_mutation_performed",
    ):
        if data.get(key) is True:
            return False
    if data.get("blocked") is True or str(data.get("status", "")).strip() == "blocked":
        return False
    return True


def _forbidden_capabilities_not_used(*records: dict[str, Any] | None) -> bool:
    for record in records:
        if not isinstance(record, dict):
            continue
        used = set(_list(record.get("capabilities_used")))
        used.update(_list(record.get("forbidden_capabilities_used")))
        if used.intersection(_FORBIDDEN_CAPABILITIES):
            return False
    return True


def _working_tree_acceptable(profile: GateProfile, git_status: dict[str, Any]) -> bool:
    if not git_status.get("available", False):
        return True
    dirty = bool(git_status.get("dirty"))
    if not dirty:
        return True
    return profile.profile in {"read_only_agent", "local_artifact_write", "docs_only_patch_apply", "local_llm_execution"}


def _path_allowlist_respected(
    repo_root: Path,
    profile: GateProfile,
    *,
    artifact_path: str | Path | None,
    patch_path: str | Path | None,
    execution_record: str | Path | None,
    patch_targets: list[str],
) -> bool:
    paths = [artifact_path, patch_path, execution_record]
    normalized = [_normalize_repo_path(repo_root, path) for path in paths if path]
    normalized.extend(target.replace("\\", "/").lstrip("/") for target in patch_targets)
    return all(_is_allowed_path(path, profile.allowed_paths) for path in normalized if path)


def _docs_only_patch_check(
    profile: GateProfile,
    patch_path: str | Path | None,
    patch_read_errors: list[str],
    patch_targets: list[str],
) -> bool:
    if profile.profile != "docs_only_patch_apply":
        return True
    if not patch_path or patch_read_errors:
        return False
    if not patch_targets:
        return False
    return all(_is_allowed_path(target, _DOCS_ONLY_PATHS) for target in patch_targets)


def _tests_reported_or_runnable(
    profile: GateProfile,
    item: dict[str, Any],
    artifact: dict[str, Any] | None,
    record: dict[str, Any] | None,
) -> bool:
    if not profile.require_tests:
        return True
    sources = [item, artifact or {}, record or {}]
    for source in sources:
        if _list(source.get("tests_run")) or _list(source.get("tests_reported")):
            return True
        if _list(source.get("validation_commands")) or _list(source.get("smoke_checks")):
            return True
        if str(source.get("validation_summary", "")).strip():
            return True
    return False


def _rollback_log_available(config: AppConfig, profile: GateProfile) -> bool:
    if not profile.require_transaction_log:
        return True
    return (config.repo_root / ".aresforge" / "queue" / "transaction_log.json").exists()


def _external_execution_allowed(profile: GateProfile, force: bool) -> bool:
    if not profile.require_external_allowance:
        return True
    return bool(force)


def _collect_warnings(
    profile: GateProfile,
    git_status: dict[str, Any],
    artifact: dict[str, Any],
    record: dict[str, Any],
    patch_read_errors: list[str],
) -> list[str]:
    warnings: list[str] = []
    if git_status.get("dirty") and profile.profile in {"read_only_agent", "local_artifact_write", "local_llm_execution"}:
        warnings.append(
            "Working tree has local changes; read-only, artifact-write, and advisory local LLM gates treat this as warning-only."
        )
    warnings.extend(_list(artifact.get("warnings")))
    warnings.extend(_list(record.get("warnings")))
    warnings.extend(patch_read_errors)
    return sorted(set(warnings))


def _load_json_if_present(repo_root: Path, value: str | Path | None) -> dict[str, Any]:
    if value is None:
        return {"exists": False, "data": {}, "warnings": []}
    path = _resolve(repo_root, value)
    if not path.exists():
        return {"exists": False, "data": {}, "warnings": [f"JSON artifact is missing: {path}"]}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"exists": True, "data": None, "warnings": [f"JSON artifact is invalid: {exc.msg}."]}
    except OSError as exc:
        return {"exists": True, "data": None, "warnings": [f"JSON artifact could not be read: {exc}."]}
    return {"exists": True, "data": raw, "warnings": []}


def _load_text_if_present(repo_root: Path, value: str | Path | None) -> tuple[str, list[str]]:
    if value is None:
        return "", []
    path = _resolve(repo_root, value)
    if not path.exists():
        return "", [f"Patch file is missing: {path}"]
    try:
        return path.read_text(encoding="utf-8"), []
    except OSError as exc:
        return "", [f"Patch file could not be read: {exc}"]


def _patch_targets(patch_text: str) -> list[str]:
    targets: list[str] = []
    for line in patch_text.splitlines():
        if line.startswith("diff --git "):
            parts = line.split()
            if len(parts) >= 4:
                targets.append(_strip_patch_prefix(parts[3]))
        elif line.startswith("+++ "):
            target = line[4:].strip()
            if target != "/dev/null":
                targets.append(_strip_patch_prefix(target))
    return sorted(set(target for target in targets if target))


def _strip_patch_prefix(value: str) -> str:
    text = value.strip().replace("\\", "/")
    if text.startswith('"') and text.endswith('"'):
        text = text[1:-1]
    return re.sub(r"^[ab]/", "", text)


def _git_status(repo_root: Path) -> dict[str, Any]:
    try:
        result = subprocess.run(
            ["git", "status", "--short"],
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"available": False, "dirty": False, "warnings": [str(exc)]}
    return {
        "available": result.returncode == 0,
        "dirty": bool(result.stdout.strip()),
        "status_lines": [line for line in result.stdout.splitlines() if line.strip()],
        "warnings": [result.stderr.strip()] if result.stderr.strip() else [],
    }


def _path_exists(repo_root: Path, value: str | Path | None) -> bool:
    return value is not None and _resolve(repo_root, value).exists()


def _resolve(repo_root: Path, value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


def _normalize_repo_path(repo_root: Path, value: str | Path) -> str:
    resolved = _resolve(repo_root, value)
    try:
        return resolved.relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return "__outside_repo__"


def _is_allowed_path(path: str, allowed_paths: tuple[str, ...]) -> bool:
    normalized = path.replace("\\", "/").lstrip("/")
    return any(
        normalized == allowed.rstrip("/") or normalized.startswith(allowed.rstrip("/") + "/")
        for allowed in allowed_paths
    )


def _required_next_steps(blocked_reasons: list[str], warnings: list[str]) -> list[str]:
    if not blocked_reasons and not warnings:
        return ["Proceed only with the next explicit local operator command allowed by this gate profile."]
    steps = []
    steps.extend(f"Resolve blocker: {reason}" for reason in blocked_reasons)
    steps.extend(f"Review warning: {warning}" for warning in warnings)
    return steps


def _next_safe_action(passed: bool, profile: str) -> str:
    if passed:
        return f"Machine safety gate passed for {profile}; future workflows may continue to the next explicit gated step."
    return "Machine safety gate blocked; resolve required next steps before any queue mutation, patch application, dispatch, sync, or orchestration."


def _emit_or_write(
    *,
    config: AppConfig,
    payload: dict[str, Any],
    output: str | Path | None,
    force: bool,
) -> dict[str, Any]:
    rendered = json.dumps(payload, indent=2)
    if output is None:
        return {
            "command": COMMAND_NAME,
            "ok": bool(payload.get("passed")) and not bool(payload.get("blocked")),
            "local_only": True,
            "format": "json",
            "wrote_output_file": False,
            "stdout": rendered,
            "payload": payload,
        }
    output_path = _resolve(config.repo_root, output)
    if output_path.exists() and not force:
        blocked = dict(payload)
        blocked["passed"] = False
        blocked["blocked"] = True
        blocked["blocked_reasons"] = [
            *list(blocked.get("blocked_reasons", [])),
            "Output file already exists. Re-run with --force to overwrite.",
        ]
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
        "ok": bool(payload.get("passed")) and not bool(payload.get("blocked")),
        "local_only": True,
        "format": "json",
        "output": str(output_path),
        "force": force,
        "wrote_output_file": True,
        "payload": payload,
    }


def _list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(entry).strip() for entry in value if str(entry).strip()]
    if value in (None, ""):
        return []
    return [str(value).strip()]


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
