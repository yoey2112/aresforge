from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.local_project_queue import resolve_project_queue_path
from aresforge.operator.managed_project_registry_local import resolve_managed_project_registry_path

DISPATCH_CONTRACT_VERSION = "m77.1"
DISPATCH_ROOT_RELATIVE = Path(".aresforge") / "codex_dispatch"
CONTRACTS_DIR_RELATIVE = DISPATCH_ROOT_RELATIVE / "contracts"
RUNS_DIR_RELATIVE = DISPATCH_ROOT_RELATIVE / "runs"

CONTRACT_REQUIRED_FIELDS: tuple[str, ...] = (
    "ok",
    "local_only",
    "dry_run_only",
    "dispatch_contract_version",
    "project_id",
    "repo_id",
    "item_id",
    "queue_item_status",
    "item_ready_for_dispatch_contract",
    "dispatch_allowed",
    "dispatch_blocked_reason",
    "dispatch_mode",
    "execution_mode",
    "operator_approval_required",
    "operator_approval_status",
    "one_item_at_a_time_required",
    "automatic_next_item_execution_allowed",
    "codex_cli_invocation_allowed",
    "codex_cli_command_preview",
    "working_directory",
    "prompt_source",
    "prompt_artifact_path",
    "expected_run_state_path",
    "expected_stdout_path",
    "expected_stderr_path",
    "expected_artifact_dir",
    "expected_audit_fields",
    "expected_completion_evidence_fields",
    "expected_run_state_shape",
    "allowed_dispatch_states",
    "safety_gates",
    "blockers",
    "warnings",
    "next_safe_action",
    "boundary_confirmations",
)

_NON_DISPATCHABLE_STATUSES = frozenset({"done", "cancelled"})
_ACTIVE_DISPATCH_STATES = frozenset(
    {
        "awaiting_operator_approval",
        "approved_pending_dispatch",
        "running",
        "review_required",
    }
)
_ALLOWED_DISPATCH_STATES = (
    "not_requested",
    "dry_run_prepared",
    "awaiting_operator_approval",
    "approved_pending_dispatch",
    "running",
    "completed",
    "failed",
    "cancelled",
    "review_required",
)
_BOUNDARY_CONFIRMATIONS = (
    "M77 is local-only, contract-only, and dry-run/no-execute.",
    "No Codex CLI process is invoked.",
    "No automatic Codex execution is implemented.",
    "No automatic agent execution is implemented.",
    "No automatic next-item execution is allowed.",
    "No queue item status is mutated.",
    "No local LLM execution expansion is added.",
    "No GitHub API calls.",
    "No gh calls.",
    "No GitHub issues, PRs, workflows, or GitHub mutation.",
    "No external workflow execution.",
)


def inspect_codex_dispatch_contract(
    config: AppConfig,
    *,
    item_id: str,
    queue_path: str | Path | None = None,
    registry_path: str | Path | None = None,
    output_format: str = "json",
) -> dict[str, Any]:
    payload = build_codex_dispatch_contract(
        config,
        item_id=item_id,
        queue_path=queue_path,
        registry_path=registry_path,
        dispatch_mode="inspect_contract",
        dry_run_prepared=False,
    )
    return _stdout_result(
        command="inspect-codex-dispatch-contract",
        payload=payload,
        output_format=output_format,
        markdown=_render_contract_markdown(payload),
    )


def prepare_codex_dispatch_dry_run(
    config: AppConfig,
    *,
    item_id: str,
    queue_path: str | Path | None = None,
    registry_path: str | Path | None = None,
    output: str | Path | None = None,
    force: bool = False,
    output_format: str = "json",
) -> dict[str, Any]:
    payload = build_codex_dispatch_contract(
        config,
        item_id=item_id,
        queue_path=queue_path,
        registry_path=registry_path,
        dispatch_mode="prepare_dry_run",
        dry_run_prepared=True,
    )

    if output is not None:
        output_result = _write_contract_output(config.repo_root, payload, output=output, force=force)
        payload["wrote_output_file"] = bool(output_result.get("ok"))
        payload["output_path"] = str(output_result.get("output_path", ""))
        if not output_result.get("ok", False):
            payload["ok"] = False
            payload["blockers"] = sorted(
                {
                    *[str(blocker) for blocker in payload.get("blockers", [])],
                    str(output_result.get("message", "Failed to write dry-run output.")),
                }
            )

    return _stdout_result(
        command="prepare-codex-dispatch-dry-run",
        payload=payload,
        output_format=output_format,
        markdown=_render_contract_markdown(payload),
    )


def build_codex_dispatch_contract(
    config: AppConfig,
    *,
    item_id: str,
    queue_path: str | Path | None = None,
    registry_path: str | Path | None = None,
    dispatch_mode: str = "inspect_contract",
    dry_run_prepared: bool = False,
) -> dict[str, Any]:
    normalized_item_id = str(item_id or "").strip()
    resolved_queue_path = resolve_project_queue_path(config.repo_root, queue_path)
    resolved_registry_path = resolve_managed_project_registry_path(config.repo_root, registry_path)
    item = _find_queue_item(resolved_queue_path, normalized_item_id)
    warnings: list[str] = []
    blockers: list[str] = []

    project_id = ""
    repo_id = ""
    status = ""
    item_found = bool(item.get("found"))
    if item_found:
        project_id = str(item["item"].get("project_id", "")).strip()
        repo_id = str(item["item"].get("repo_id", "")).strip()
        status = str(item["item"].get("status", "")).strip()
    else:
        blockers.append(f"Queue item not found: {normalized_item_id}")
        warnings.extend(item.get("warnings", []))

    binding = _inspect_registry_binding(
        registry_path=resolved_registry_path,
        project_id=project_id,
        repo_id=repo_id,
    )
    warnings.extend(binding.get("warnings", []))
    blockers.extend(binding.get("blockers", []))

    paths = _expected_paths(config.repo_root, normalized_item_id)
    active_dispatch = _inspect_existing_run_state(paths["expected_run_state_path"])
    warnings.extend(active_dispatch.get("warnings", []))
    blockers.extend(active_dispatch.get("blockers", []))

    if status in _NON_DISPATCHABLE_STATUSES:
        blockers.append(f"Queue item status is {status}; done/cancelled items are not dispatchable.")

    ready_for_contract = item_found and bool(binding.get("ok", False)) and status not in _NON_DISPATCHABLE_STATUSES
    working_directory = str(binding.get("repo_path") or config.repo_root)
    dispatch_state = "dry_run_prepared" if dry_run_prepared else "not_requested"
    dispatch_blocked_reason = (
        "M77 defines the local dispatch contract only; Codex CLI invocation is reserved for a later approved milestone."
    )
    if blockers:
        dispatch_blocked_reason = "; ".join(sorted({str(blocker).strip() for blocker in blockers if str(blocker).strip()}))

    payload: dict[str, Any] = {
        "ok": item_found and bool(binding.get("ok", False)) and not bool(active_dispatch.get("active", False)),
        "local_only": True,
        "dry_run_only": True,
        "dispatch_contract_version": DISPATCH_CONTRACT_VERSION,
        "generated_at": _now_iso(),
        "queue_path": str(resolved_queue_path),
        "registry_path": str(resolved_registry_path),
        "project_id": project_id,
        "repo_id": repo_id,
        "item_id": normalized_item_id,
        "queue_item_status": status,
        "item_ready_for_dispatch_contract": ready_for_contract,
        "dispatch_allowed": False,
        "dispatch_blocked_reason": dispatch_blocked_reason,
        "dispatch_mode": dispatch_mode,
        "execution_mode": "dry_run_no_execute" if dry_run_prepared else "contract_only",
        "operator_approval_required": True,
        "operator_approval_status": "not_requested",
        "one_item_at_a_time_required": True,
        "automatic_next_item_execution_allowed": False,
        "codex_cli_invocation_allowed": False,
        "codex_cli_command_preview": _command_preview(working_directory, paths["prompt_artifact_path"]),
        "codex_cli_command_preview_label": "preview_only_not_executable_in_m77",
        "working_directory": working_directory,
        "prompt_source": "future_prompt_artifact_reserved_no_prompt_generated",
        "prompt_artifact_path": str(paths["prompt_artifact_path"]),
        "expected_contract_path": str(paths["expected_contract_path"]),
        "expected_run_state_path": str(paths["expected_run_state_path"]),
        "expected_stdout_path": str(paths["expected_stdout_path"]),
        "expected_stderr_path": str(paths["expected_stderr_path"]),
        "expected_artifact_dir": str(paths["expected_artifact_dir"]),
        "expected_audit_fields": [
            "run_id",
            "item_id",
            "project_id",
            "repo_id",
            "dispatch_state",
            "operator_approval",
            "prompt_artifact_path",
            "stdout_path",
            "stderr_path",
            "artifact_dir",
            "review_evidence",
            "validation_evidence",
            "next_safe_action",
        ],
        "expected_completion_evidence_fields": [
            "review_evidence",
            "validation_evidence",
            "diff_check_result",
            "tests_run",
            "changed_files",
            "operator_closeout_note",
        ],
        "expected_run_state_shape": _expected_run_state_shape(
            item_id=normalized_item_id,
            project_id=project_id,
            repo_id=repo_id,
            dispatch_state=dispatch_state,
            paths=paths,
        ),
        "allowed_dispatch_states": list(_ALLOWED_DISPATCH_STATES),
        "safety_gates": _safety_gates(
            item_found=item_found,
            binding_ok=bool(binding.get("ok", False)),
            status=status,
            active_dispatch=bool(active_dispatch.get("active", False)),
        ),
        "blockers": sorted({str(blocker).strip() for blocker in blockers if str(blocker).strip()}),
        "warnings": sorted({str(warning).strip() for warning in warnings if str(warning).strip()}),
        "next_safe_action": (
            "Review this JSON contract locally. M78 may add explicit operator-approved dispatch, "
            "but M77 must not invoke Codex CLI."
        ),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }
    validation = validate_codex_dispatch_contract_payload(payload)
    payload["contract_payload_valid"] = bool(validation.get("valid", False))
    payload["contract_payload_validation"] = validation
    return payload


def validate_codex_dispatch_contract_payload(payload: dict[str, Any]) -> dict[str, Any]:
    missing = [field for field in CONTRACT_REQUIRED_FIELDS if field not in payload]
    blockers: list[str] = []
    if payload.get("dry_run_only") is not True:
        blockers.append("dry_run_only must be true.")
    if payload.get("dispatch_allowed") is not False:
        blockers.append("dispatch_allowed must be false for M77.")
    if payload.get("codex_cli_invocation_allowed") is not False:
        blockers.append("codex_cli_invocation_allowed must be false for M77.")
    if payload.get("automatic_next_item_execution_allowed") is not False:
        blockers.append("automatic_next_item_execution_allowed must be false.")
    if payload.get("operator_approval_required") is not True:
        blockers.append("operator_approval_required must be true.")
    preview = str(payload.get("codex_cli_command_preview", "")).lower()
    if preview and ("preview only" not in preview or "not executable" not in preview):
        blockers.append("codex_cli_command_preview must be marked preview only and not executable.")
    for path_field in (
        "expected_contract_path",
        "expected_run_state_path",
        "expected_stdout_path",
        "expected_stderr_path",
        "expected_artifact_dir",
        "prompt_artifact_path",
    ):
        value = str(payload.get(path_field, ""))
        if value and f"{Path('.aresforge') / 'codex_dispatch'}" not in value:
            blockers.append(f"{path_field} must stay under .aresforge/codex_dispatch.")

    return {
        "valid": not missing and not blockers,
        "missing_fields": missing,
        "blockers": blockers,
    }


def _find_queue_item(queue_path: Path, item_id: str) -> dict[str, Any]:
    if not queue_path.exists():
        return {
            "found": False,
            "item": {},
            "warnings": [f"Local queue file not found: {queue_path}"],
        }
    try:
        raw = json.loads(queue_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "found": False,
            "item": {},
            "warnings": [f"Local queue file could not be read: {exc}"],
        }
    items = raw.get("work_items", []) if isinstance(raw, dict) else []
    item = next(
        (
            candidate
            for candidate in items
            if isinstance(candidate, dict) and str(candidate.get("item_id", "")).strip() == item_id
        ),
        None,
    )
    return {"found": item is not None, "item": item or {}, "warnings": []}


def _inspect_registry_binding(*, registry_path: Path, project_id: str, repo_id: str) -> dict[str, Any]:
    if not project_id or not repo_id:
        return {
            "ok": False,
            "repo_path": "",
            "warnings": [],
            "blockers": ["Queue item must include project_id and repo_id before dispatch contract inspection."],
        }
    if not registry_path.exists():
        return {
            "ok": False,
            "repo_path": "",
            "warnings": [],
            "blockers": [f"Managed project registry not found: {registry_path}"],
        }
    try:
        raw = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "ok": False,
            "repo_path": "",
            "warnings": [],
            "blockers": [f"Managed project registry could not be read: {exc}"],
        }
    projects = raw.get("projects", []) if isinstance(raw, dict) else []
    project = next(
        (
            candidate
            for candidate in projects
            if isinstance(candidate, dict) and str(candidate.get("project_id", "")).strip() == project_id
        ),
        None,
    )
    if project is None:
        return {"ok": False, "repo_path": "", "warnings": [], "blockers": [f"Managed project not found: {project_id}"]}
    repos = project.get("repos", []) if isinstance(project.get("repos"), list) else []
    repo = next(
        (
            candidate
            for candidate in repos
            if isinstance(candidate, dict) and str(candidate.get("repo_id", "")).strip() == repo_id
        ),
        None,
    )
    if repo is None:
        return {"ok": False, "repo_path": "", "warnings": [], "blockers": [f"Managed repo not found: {project_id}/{repo_id}"]}
    repo_path = str(repo.get("path", "")).strip()
    warnings = []
    if not repo_path:
        warnings.append("Managed repo binding has no local path; using repo root as fallback.")
    return {"ok": True, "repo_path": repo_path, "warnings": warnings, "blockers": []}


def _inspect_existing_run_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"active": False, "warnings": [], "blockers": []}
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"active": False, "warnings": [f"Existing run-state file could not be inspected: {exc}"], "blockers": []}
    state = str(raw.get("dispatch_state", "") if isinstance(raw, dict) else "").strip()
    if state in _ACTIVE_DISPATCH_STATES:
        return {
            "active": True,
            "warnings": [],
            "blockers": [f"Existing run state is active: {state}"],
        }
    return {"active": False, "warnings": [], "blockers": []}


def _expected_paths(repo_root: Path, item_id: str) -> dict[str, Path]:
    safe_item_id = _safe_path_token(item_id)
    run_dir = (repo_root / RUNS_DIR_RELATIVE / safe_item_id).resolve()
    return {
        "prompt_artifact_path": (repo_root / DISPATCH_ROOT_RELATIVE / "prompts" / f"{safe_item_id}.prompt.txt").resolve(),
        "expected_contract_path": (repo_root / CONTRACTS_DIR_RELATIVE / f"{safe_item_id}.dispatch-contract.json").resolve(),
        "expected_run_state_path": (run_dir / "run-state.json").resolve(),
        "expected_stdout_path": (run_dir / "stdout.txt").resolve(),
        "expected_stderr_path": (run_dir / "stderr.txt").resolve(),
        "expected_artifact_dir": (run_dir / "artifacts").resolve(),
    }


def _expected_run_state_shape(
    *,
    item_id: str,
    project_id: str,
    repo_id: str,
    dispatch_state: str,
    paths: dict[str, Path],
) -> dict[str, Any]:
    return {
        "run_id": "",
        "item_id": item_id,
        "project_id": project_id,
        "repo_id": repo_id,
        "dispatch_state": dispatch_state,
        "started_at": "",
        "completed_at": "",
        "exit_code": None,
        "stdout_path": str(paths["expected_stdout_path"]),
        "stderr_path": str(paths["expected_stderr_path"]),
        "artifact_dir": str(paths["expected_artifact_dir"]),
        "prompt_artifact_path": str(paths["prompt_artifact_path"]),
        "operator_approval": {"required": True, "status": "not_requested", "approved_by": "", "approved_at": ""},
        "review_evidence": [],
        "validation_evidence": [],
        "error_summary": "",
        "next_safe_action": "Await explicit operator approval in a future milestone; do not dispatch in M77.",
    }


def _safety_gates(*, item_found: bool, binding_ok: bool, status: str, active_dispatch: bool) -> list[dict[str, Any]]:
    return [
        {"gate": "queue_item_exists", "required": True, "passed": item_found},
        {"gate": "queue_item_belongs_to_registered_managed_project_repo", "required": True, "passed": binding_ok},
        {"gate": "queue_item_not_done_or_cancelled", "required": True, "passed": status not in _NON_DISPATCHABLE_STATUSES},
        {"gate": "queue_item_not_already_in_active_dispatch_state", "required": True, "passed": not active_dispatch},
        {"gate": "explicit_operator_approval_present", "required": True, "passed": False},
        {"gate": "one_item_at_a_time_lock_check_exists", "required": True, "passed": False},
        {"gate": "automatic_next_item_execution_disabled", "required": True, "passed": True},
        {"gate": "run_state_path_reserved", "required": True, "passed": True},
        {"gate": "stdout_stderr_artifact_capture_paths_reserved", "required": True, "passed": True},
        {"gate": "review_evidence_required_before_completion", "required": True, "passed": True},
        {"gate": "validation_evidence_required_before_commit_push", "required": True, "passed": True},
        {"gate": "dependency_blocking_respected", "required": True, "passed": False},
        {"gate": "github_gh_api_workflow_mutation_blocked", "required": True, "passed": True},
    ]


def _command_preview(working_directory: str, prompt_artifact_path: Path) -> str:
    return (
        "PREVIEW ONLY - NOT EXECUTABLE IN M77: "
        f"codex --cd {working_directory} --prompt-file {prompt_artifact_path}"
    )


def _write_contract_output(repo_root: Path, payload: dict[str, Any], *, output: str | Path, force: bool) -> dict[str, Any]:
    output_path = Path(output)
    if not output_path.is_absolute():
        output_path = repo_root / output_path
    output_path = output_path.resolve()
    root = repo_root.resolve()
    try:
        output_path.relative_to(root)
    except ValueError:
        return {
            "ok": False,
            "output_path": str(output_path),
            "message": "Dry-run contract output must stay inside the repository root.",
        }
    if DISPATCH_ROOT_RELATIVE.as_posix().replace("/", str(Path("/"))) not in str(output_path):
        try:
            output_path.relative_to((root / DISPATCH_ROOT_RELATIVE).resolve())
        except ValueError:
            return {
                "ok": False,
                "output_path": str(output_path),
                "message": "Dry-run contract output must stay under .aresforge/codex_dispatch.",
            }
    if output_path.exists() and not force:
        return {
            "ok": False,
            "output_path": str(output_path),
            "message": "Dry-run contract output already exists. Re-run with --force to overwrite.",
        }
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    except OSError as exc:
        return {"ok": False, "output_path": str(output_path), "message": f"Failed to write dry-run output: {exc}"}
    return {"ok": True, "output_path": str(output_path)}


def _stdout_result(command: str, payload: dict[str, Any], output_format: str, markdown: str) -> dict[str, Any]:
    fmt = output_format.lower().strip()
    if fmt not in {"json", "markdown"}:
        return {
            "ok": False,
            "local_only": True,
            "error": "invalid_format",
            "details": {"format": output_format, "supported_formats": ["json", "markdown"]},
        }
    return {
        "command": command,
        "ok": bool(payload.get("ok", False)),
        "local_only": True,
        "format": fmt,
        "wrote_output_file": bool(payload.get("wrote_output_file", False)),
        "stdout": json.dumps(payload, indent=2) if fmt == "json" else markdown,
        "payload": payload,
    }


def _render_contract_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Codex CLI Dispatch Contract",
        "",
        f"- item_id: {payload.get('item_id', '')}",
        f"- project_id: {payload.get('project_id', '')}",
        f"- repo_id: {payload.get('repo_id', '')}",
        f"- queue_item_status: {payload.get('queue_item_status', '')}",
        f"- dry_run_only: {payload.get('dry_run_only')}",
        f"- dispatch_allowed: {payload.get('dispatch_allowed')}",
        f"- codex_cli_invocation_allowed: {payload.get('codex_cli_invocation_allowed')}",
        f"- automatic_next_item_execution_allowed: {payload.get('automatic_next_item_execution_allowed')}",
        f"- operator_approval_required: {payload.get('operator_approval_required')}",
        f"- execution_mode: {payload.get('execution_mode')}",
        "",
        "## Blockers",
    ]
    blockers = payload.get("blockers", []) if isinstance(payload.get("blockers"), list) else []
    lines.extend([f"- {blocker}" for blocker in blockers] or ["- M77 blocks dispatch by design."])
    lines.extend(["", "## Boundary Confirmations"])
    lines.extend(f"- {entry}" for entry in payload.get("boundary_confirmations", []))
    return "\n".join(lines)


def _safe_path_token(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in str(value).strip()) or "unknown-item"


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()
