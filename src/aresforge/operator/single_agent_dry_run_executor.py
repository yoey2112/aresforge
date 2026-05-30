from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.agent_orchestration_plan_builder import build_agent_orchestration_plan
from aresforge.operator.agent_registry import build_agent_registry
from aresforge.operator.local_project_queue import inspect_project_queue, resolve_project_queue_path

COMMAND_NAME = "run-agent-dry-run"
EXECUTION_RECORD_VERSION = "m129.1"

SUPPORTED_DRY_RUN_AGENTS: tuple[str, ...] = (
    "artifact-registry-agent",
    "evidence-parser-agent",
    "completion-recommendation-agent",
    "validation-agent",
    "sprint-summary-agent",
    "queue-planner-agent",
)

_FORBIDDEN_CAPABILITIES: tuple[str, ...] = (
    "execute_agent",
    "execute_codex",
    "execute_ollama_prompt",
    "execute_local_llm",
    "call_github_api",
    "call_gh",
    "call_external_network",
    "apply_patch",
    "run_validation_commands",
    "mutate_queue_without_operator",
    "automatic_next_item_execution",
    "create_pr_or_issue",
    "background_daemon",
)

_BOUNDARY_CONFIRMATIONS: tuple[str, ...] = (
    "M129 runs only deterministic single-agent dry-run logic.",
    "M129 does not execute Codex, Codex CLI, Ollama, local LLMs, remote LLMs, GitHub, gh, network services, validation commands, or patches.",
    "M129 does not mutate queue state or source files.",
    "M129 may write one explicit dry-run execution record when --output is supplied.",
)


def run_single_agent_dry_run(
    config: AppConfig,
    *,
    agent_id: str,
    item_id: str,
    plan_path: str | Path | None = None,
    queue_path: str | Path | None = None,
    output: str | Path | None = None,
    force: bool = False,
    output_format: str = "json",
) -> dict[str, Any]:
    fmt = str(output_format or "json").lower().strip()
    if fmt != "json":
        return _error("invalid_format", {"format": output_format, "supported_formats": ["json"]})

    started_at = _now_iso()
    normalized_agent_id = str(agent_id or "").strip()
    normalized_item_id = str(item_id or "").strip()
    registry = build_agent_registry(config)
    registry_agents = {
        str(agent.get("agent_id", "")).strip(): agent
        for agent in registry.get("agents", [])
        if isinstance(agent, dict) and str(agent.get("agent_id", "")).strip()
    }
    agent = registry_agents.get(normalized_agent_id, {})
    item = _load_queue_item(config, item_id=normalized_item_id, queue_path=queue_path)
    plan, plan_warnings = _load_or_build_plan(
        config,
        item_id=normalized_item_id,
        plan_path=plan_path,
        queue_path=queue_path,
    )
    warnings = list(plan_warnings)
    errors: list[str] = []
    if not item:
        errors.append(f"Queue item not found: {normalized_item_id}")
    if not agent:
        errors.append(f"Agent is not registered: {normalized_agent_id}")
    if normalized_agent_id and normalized_agent_id not in SUPPORTED_DRY_RUN_AGENTS:
        errors.append(f"Agent is not supported for M129 dry-run execution: {normalized_agent_id}")

    forbidden_blocked = _forbidden_capabilities_blocked(agent)
    outputs = _agent_outputs(
        config=config,
        agent_id=normalized_agent_id,
        item=item,
        plan=plan,
        queue_path=queue_path,
    )
    status = "blocked" if errors else "completed"
    completed_at = _now_iso()
    payload = {
        "execution_record_type": "single_agent_dry_run",
        "execution_record_version": EXECUTION_RECORD_VERSION,
        "generated": True,
        "agent_id": normalized_agent_id,
        "item_id": normalized_item_id,
        "project_id": str(item.get("project_id", "")).strip(),
        "dry_run": True,
        "real_execution": False,
        "started_at": started_at,
        "completed_at": completed_at,
        "status": status,
        "inputs": {
            "queue_path": str(resolve_project_queue_path(config.repo_root, queue_path)),
            "plan_path": str(_resolve_path(config.repo_root, plan_path)) if plan_path else "",
            "plan_loaded": bool(plan),
            "agent_registered": bool(agent),
            "supported_dry_run_agents": list(SUPPORTED_DRY_RUN_AGENTS),
        },
        "outputs": outputs,
        "artifacts_created": [],
        "warnings": sorted({warning for warning in warnings if warning}),
        "errors": sorted({error for error in errors if error}),
        "capabilities_used": _capabilities_used(agent),
        "forbidden_capabilities_blocked": forbidden_blocked,
        "mutation_performed": False,
        "external_execution_performed": False,
        "model_execution_performed": False,
        "github_execution_performed": False,
        "patch_application_performed": False,
        "local_only": True,
        "next_safe_action": _next_safe_action(status, normalized_agent_id),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }
    return _emit_or_write(config=config, payload=payload, output=output, force=force)


def _agent_outputs(
    *,
    config: AppConfig,
    agent_id: str,
    item: dict[str, Any],
    plan: dict[str, Any],
    queue_path: str | Path | None,
) -> dict[str, Any]:
    if not item:
        return {"summary": "No deterministic dry-run output was generated because the queue item was not found."}
    if agent_id == "artifact-registry-agent":
        return _artifact_registry_outputs(config)
    if agent_id == "evidence-parser-agent":
        return _evidence_parser_outputs(config, item)
    if agent_id == "completion-recommendation-agent":
        return _completion_recommendation_outputs(item)
    if agent_id == "validation-agent":
        return _validation_outputs(item)
    if agent_id == "sprint-summary-agent":
        return _sprint_summary_outputs(config, queue_path)
    if agent_id == "queue-planner-agent":
        return _queue_planner_outputs(item, plan)
    return {"summary": "Agent is not supported for M129 dry-run output generation."}


def _artifact_registry_outputs(config: AppConfig) -> dict[str, Any]:
    root = config.artifact_root
    files = sorted(path for path in root.rglob("*") if path.is_file()) if root.exists() else []
    by_suffix: dict[str, int] = {}
    for path in files:
        suffix = path.suffix.lower() or "(none)"
        by_suffix[suffix] = by_suffix.get(suffix, 0) + 1
    return {
        "summary": "Inspected local artifact root metadata only.",
        "artifact_root": str(root),
        "artifact_root_exists": root.exists(),
        "file_count": len(files),
        "file_counts_by_suffix": dict(sorted(by_suffix.items())),
        "sample_artifacts": [_relative(config.repo_root, path) for path in files[:10]],
    }


def _evidence_parser_outputs(config: AppConfig, item: dict[str, Any]) -> dict[str, Any]:
    item_id = str(item.get("item_id", "")).strip()
    candidates = []
    for directory in (
        config.artifact_root / "dispatch_result_evidence",
        config.artifact_root / "evidence" / "generated",
    ):
        if not directory.exists():
            continue
        for path in sorted(directory.rglob("*")):
            if path.is_file() and item_id in path.name:
                candidates.append(_relative(config.repo_root, path))
    return {
        "summary": "Inspected candidate local evidence files and parser expectations without parsing external output.",
        "candidate_evidence_records": candidates[:20],
        "candidate_count": len(candidates),
        "expected_fields": [
            "files_changed",
            "what_changed",
            "tests_reported",
            "smoke_checks_reported",
            "warnings_or_blockers",
            "commit_hash",
        ],
    }


def _completion_recommendation_outputs(item: dict[str, Any]) -> dict[str, Any]:
    evidence = item.get("completion_evidence", {}) if isinstance(item.get("completion_evidence"), dict) else {}
    return {
        "summary": "Inspected queue completion metadata without recommending automatic completion.",
        "queue_status": str(item.get("status", "")).strip(),
        "completion_requires": _list(item.get("completion_requires")),
        "evidence_required": _list(item.get("evidence_required")),
        "completion_evidence_present": bool(evidence),
        "completion_commit_present": bool(str(item.get("completion_commit", "")).strip()),
        "operator_decision_required": True,
        "queue_mutation_performed": False,
    }


def _validation_outputs(item: dict[str, Any]) -> dict[str, Any]:
    item_id = str(item.get("item_id", "")).strip()
    return {
        "summary": "Generated deterministic validation plan metadata without running commands.",
        "validation_commands_planned_not_run": [
            "python -m pytest tests/test_cli.py",
            "git diff --check",
            f"python -m aresforge inspect-queue-item --item-id {item_id} --format json",
        ],
        "validation_execution_performed": False,
        "smoke_checks_planned_not_run": [
            "python -m aresforge inspect-local-project-report",
            "python -m aresforge inspect-local-queue-agent-summary",
        ],
    }


def _sprint_summary_outputs(config: AppConfig, queue_path: str | Path | None) -> dict[str, Any]:
    queue = inspect_project_queue(config, queue_path=queue_path, output_format="json")
    payload = queue.get("payload", {}) if isinstance(queue.get("payload"), dict) else {}
    items = payload.get("work_items", []) if isinstance(payload.get("work_items"), list) else []
    status_counts: dict[str, int] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        status = str(item.get("status", "")).strip() or "unknown"
        status_counts[status] = status_counts.get(status, 0) + 1
    return {
        "summary": "Summarized local queue posture without inspecting git or running validation.",
        "queue_item_count": len(items),
        "queue_counts_by_status": dict(sorted(status_counts.items())),
        "in_progress_items": [
            str(item.get("item_id", "")).strip()
            for item in items
            if isinstance(item, dict) and str(item.get("status", "")).strip() == "in_progress"
        ][:20],
    }


def _queue_planner_outputs(item: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "summary": "Inspected queue ordering metadata and available orchestration plan without executing steps.",
        "queue_status": str(item.get("status", "")).strip(),
        "dependencies": _list(item.get("dependencies")),
        "depends_on": _list(item.get("depends_on")),
        "blocked_by": _list(item.get("blocked_by")),
        "plan_available": bool(plan),
        "planned_steps": [
            str(step.get("agent_id", "")).strip()
            for step in plan.get("steps", [])
            if isinstance(step, dict)
        ],
        "plan_blocked": bool(plan.get("blocked")) if plan else False,
    }


def _load_or_build_plan(
    config: AppConfig,
    *,
    item_id: str,
    plan_path: str | Path | None,
    queue_path: str | Path | None,
) -> tuple[dict[str, Any], list[str]]:
    if plan_path:
        path = _resolve_path(config.repo_root, plan_path)
        if not path.exists():
            return {}, [f"Plan path was supplied but does not exist: {path}"]
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            return {}, [f"Plan path could not be parsed as JSON: {exc}"]
        if not isinstance(raw, dict):
            return {}, ["Plan path JSON root is not an object."]
        return raw, []
    result = build_agent_orchestration_plan(
        config,
        item_id=item_id,
        queue_path=queue_path,
        output_format="json",
    )
    payload = result.get("payload", {}) if isinstance(result.get("payload"), dict) else {}
    return payload, [] if payload else ["No orchestration plan metadata could be built."]


def _load_queue_item(config: AppConfig, *, item_id: str, queue_path: str | Path | None) -> dict[str, Any]:
    path = resolve_project_queue_path(config.repo_root, queue_path)
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    items = raw.get("work_items", []) if isinstance(raw, dict) else []
    for item in items:
        if isinstance(item, dict) and str(item.get("item_id", "")).strip() == item_id:
            return item
    return {}


def _emit_or_write(
    *,
    config: AppConfig,
    payload: dict[str, Any],
    output: str | Path | None,
    force: bool,
) -> dict[str, Any]:
    rendered = json.dumps(payload, indent=2)
    ok = payload.get("status") == "completed"
    if output is None:
        return {
            "command": COMMAND_NAME,
            "ok": ok,
            "local_only": True,
            "format": "json",
            "wrote_output_file": False,
            "stdout": rendered,
            "payload": payload,
        }
    output_path = _resolve_path(config.repo_root, output)
    if output_path.exists() and not force:
        blocked = dict(payload)
        blocked["status"] = "blocked"
        blocked["errors"] = sorted(
            {*_list(payload.get("errors")), "Output file already exists. Re-run with --force to overwrite."}
        )
        blocked["next_safe_action"] = "Choose a new output path or rerun with --force; no agent execution was performed."
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
    artifact_payload = dict(payload)
    artifact_payload["mutation_performed"] = True
    artifact_payload["artifacts_created"] = [str(output_path)]
    rendered = json.dumps(artifact_payload, indent=2)
    output_path.write_text(rendered + "\n", encoding="utf-8")
    return {
        "command": COMMAND_NAME,
        "ok": ok,
        "local_only": True,
        "format": "json",
        "output": str(output_path),
        "force": force,
        "wrote_output_file": True,
        "stdout": rendered,
        "payload": artifact_payload,
    }


def _forbidden_capabilities_blocked(agent: dict[str, Any]) -> list[str]:
    declared = _list(agent.get("forbidden_capabilities")) if agent else []
    return sorted(set([*declared, *_FORBIDDEN_CAPABILITIES]))


def _capabilities_used(agent: dict[str, Any]) -> list[str]:
    allowed = set(_list(agent.get("allowed_capabilities")) if agent else [])
    safe_used = {"read_local_queue", "read_local_artifacts", "generate_plan_artifact", "generate_review_artifact"}
    return sorted(allowed.intersection(safe_used))


def _next_safe_action(status: str, agent_id: str) -> str:
    if status != "completed":
        return "Review errors and select one of the supported deterministic M129 dry-run agents before retrying."
    if agent_id == "validation-agent":
        return "Review the planned validation commands and run them manually outside this dry-run record when appropriate."
    return "Review the dry-run record; use explicit local-only follow-on commands for any artifact or evidence workflow."


def _resolve_path(repo_root: Path, value: str | Path | None) -> Path:
    path = Path(str(value or ""))
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


def _relative(repo_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(entry).strip() for entry in value if str(entry).strip()]
    if isinstance(value, tuple):
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
