from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig

DEFAULT_DEFINITION_ROOT = Path(".aresforge") / "milestones"


def generate_local_milestone_template(
    config: AppConfig,
    *,
    milestone_id: str,
    output: str | Path,
    title: str | None = None,
    force: bool = False,
) -> dict[str, Any]:
    output_path = _resolve_path(config.repo_root, output)
    if output_path.exists() and not force:
        return _error("output_exists", {"path": str(output_path), "hint": "Re-run with --force to overwrite."})
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return _error("output_directory_create_failed", {"path": str(output_path.parent), "message": str(exc)})

    normalized_id = milestone_id.strip()
    template = {
        "milestone_id": normalized_id,
        "title": (title or f"{normalized_id} local milestone").strip(),
        "goal": "",
        "status": "draft",
        "parent_reference": "",
        "work_items": [],
        "required_docs": [],
        "required_artifacts": [],
        "validation_commands": [],
        "closeout_requirements": [],
        "risks": [],
        "notes": [],
    }
    try:
        output_path.write_text(json.dumps(template, indent=2) + "\n", encoding="utf-8")
    except OSError as exc:
        return _error("output_write_failed", {"path": str(output_path), "message": str(exc)})
    return {
        "command": "generate-local-milestone-template",
        "ok": True,
        "local_only": True,
        "plan_only": True,
        "output": str(output_path),
        "force": force,
        "definition": template,
    }


def inspect_local_milestone(
    config: AppConfig,
    *,
    definition: str | Path,
    output_format: str = "markdown",
) -> dict[str, Any]:
    definition_path = _resolve_path(config.repo_root, definition)
    parsed = _load_definition(definition_path)
    if not parsed["ok"]:
        return {
            "command": "inspect-local-milestone",
            "ok": False,
            "local_only": True,
            **parsed,
        }
    payload = _build_inspection_payload(definition_path, parsed["definition"])
    return _stdout_result("inspect-local-milestone", payload, output_format, _render_inspection_markdown(payload))


def check_local_milestone_readiness(
    config: AppConfig,
    *,
    definition: str | Path,
    project_state: str | Path | None = None,
    output_format: str = "markdown",
) -> dict[str, Any]:
    definition_path = _resolve_path(config.repo_root, definition)
    parsed = _load_definition(definition_path)
    if not parsed["ok"]:
        return {
            "command": "check-local-milestone-readiness",
            "ok": False,
            "local_only": True,
            "plan_only": True,
            **parsed,
        }
    state_path = _resolve_path(config.repo_root, project_state) if project_state is not None else (
        config.repo_root / ".aresforge" / "state" / "project_state.json"
    )
    payload = _build_readiness_payload(
        config.repo_root,
        definition_path,
        parsed["definition"],
        state_path,
        project_state is not None,
    )
    return _stdout_result(
        "check-local-milestone-readiness",
        payload,
        output_format,
        _render_readiness_markdown(payload),
    )


def generate_local_milestone_closeout(
    config: AppConfig,
    *,
    definition: str | Path,
    output: str | Path,
    output_format: str = "markdown",
    force: bool = False,
) -> dict[str, Any]:
    definition_path = _resolve_path(config.repo_root, definition)
    parsed = _load_definition(definition_path)
    if not parsed["ok"]:
        return {
            "command": "generate-local-milestone-closeout",
            "ok": False,
            "local_only": True,
            "plan_only": True,
            **parsed,
        }
    readiness = _build_readiness_payload(
        config.repo_root,
        definition_path,
        parsed["definition"],
        config.repo_root / ".aresforge" / "state" / "project_state.json",
        False,
    )
    closeout = _build_closeout_payload(parsed["definition"], readiness)
    output_path = _resolve_path(config.repo_root, output)
    if output_path.exists() and not force:
        return _error("output_exists", {"path": str(output_path), "hint": "Re-run with --force to overwrite."})
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return _error("output_directory_create_failed", {"path": str(output_path.parent), "message": str(exc)})
    fmt = output_format.lower().strip()
    if fmt not in {"markdown", "json"}:
        return _error("invalid_format", {"format": output_format})
    content = json.dumps(closeout, indent=2) if fmt == "json" else _render_closeout_markdown(closeout)
    try:
        output_path.write_text(content + "\n", encoding="utf-8")
    except OSError as exc:
        return _error("output_write_failed", {"path": str(output_path), "message": str(exc)})
    return {
        "command": "generate-local-milestone-closeout",
        "ok": True,
        "local_only": True,
        "plan_only": True,
        "output": str(output_path),
        "format": fmt,
        "force": force,
        "readiness_ready": closeout["readiness_result"]["ready"],
    }


def _build_inspection_payload(definition_path: Path, definition: dict[str, Any]) -> dict[str, Any]:
    return {
        "definition_path": str(definition_path),
        "milestone_id": str(definition.get("milestone_id", "")).strip(),
        "title": str(definition.get("title", "")).strip(),
        "goal": str(definition.get("goal", "")).strip(),
        "status": str(definition.get("status", "")).strip(),
        "parent_reference": str(definition.get("parent_reference", "")).strip(),
        "work_items": _as_string_list(definition.get("work_items")),
        "required_docs": _as_string_list(definition.get("required_docs")),
        "required_artifacts": _as_string_list(definition.get("required_artifacts")),
        "validation_commands": _as_string_list(definition.get("validation_commands")),
        "closeout_requirements": _as_string_list(definition.get("closeout_requirements")),
        "risks": _as_string_list(definition.get("risks")),
        "notes": _as_string_list(definition.get("notes")),
        "inspected_at": datetime.now(UTC).isoformat(),
    }


def _build_readiness_payload(
    repo_root: Path,
    definition_path: Path,
    definition: dict[str, Any],
    project_state_path: Path,
    explicit_project_state: bool,
) -> dict[str, Any]:
    required_docs = _as_string_list(definition.get("required_docs"))
    required_artifacts = _as_string_list(definition.get("required_artifacts"))
    validation_commands = _as_string_list(definition.get("validation_commands"))
    closeout_requirements = _as_string_list(definition.get("closeout_requirements"))
    work_items = _as_string_list(definition.get("work_items"))
    risks = _as_string_list(definition.get("risks"))
    notes = _as_string_list(definition.get("notes"))

    errors: list[str] = []
    warnings: list[str] = []
    checks: list[dict[str, Any]] = []

    milestone_id = str(definition.get("milestone_id", "")).strip()
    title = str(definition.get("title", "")).strip()
    goal = str(definition.get("goal", "")).strip()
    status = str(definition.get("status", "")).strip()

    checks.append(_check("definition_parsed", True, "Milestone definition parsed."))
    if milestone_id:
        checks.append(_check("milestone_id_exists", True, "milestone_id is present."))
    else:
        checks.append(_check("milestone_id_exists", False, "milestone_id is missing."))
        errors.append("milestone_id is required.")
    if title:
        checks.append(_check("title_exists", True, "title is present."))
    else:
        checks.append(_check("title_exists", False, "title is missing."))
        errors.append("title is required.")
    if goal:
        checks.append(_check("goal_exists", True, "goal is present."))
    else:
        checks.append(_check("goal_exists", False, "goal is missing."))
        errors.append("goal is required.")

    missing_docs: list[str] = []
    for rel in required_docs:
        candidate = Path(rel)
        exists = candidate.exists() if candidate.is_absolute() else (
            (definition_path.parent / candidate).exists() or (repo_root / candidate).exists()
        )
        if not exists:
            missing_docs.append(rel)
    checks.append(_check("required_docs_exist", len(missing_docs) == 0, "Required docs checked.", {"missing": missing_docs}))
    if missing_docs:
        errors.append("One or more required_docs entries are missing.")

    missing_artifacts: list[str] = []
    for rel in required_artifacts:
        candidate = Path(rel)
        exists = candidate.exists() if candidate.is_absolute() else (
            (definition_path.parent / candidate).exists() or (repo_root / candidate).exists()
        )
        if not exists:
            missing_artifacts.append(rel)
    checks.append(
        _check(
            "required_artifacts_exist",
            len(missing_artifacts) == 0,
            "Required artifacts checked.",
            {"missing": missing_artifacts},
        )
    )
    if missing_artifacts:
        errors.append("One or more required_artifacts entries are missing.")

    checks.append(
        _check(
            "validation_commands_listed",
            len(validation_commands) > 0,
            "validation_commands list checked.",
            {"count": len(validation_commands)},
        )
    )
    if not validation_commands:
        errors.append("validation_commands must contain at least one command.")

    checks.append(
        _check(
            "closeout_requirements_listed",
            len(closeout_requirements) > 0,
            "closeout_requirements list checked.",
            {"count": len(closeout_requirements)},
        )
    )
    if not closeout_requirements:
        errors.append("closeout_requirements must contain at least one item.")

    project_state_loaded = False
    project_state_summary: dict[str, Any] | None = None
    if explicit_project_state or project_state_path.exists():
        loaded = _load_json_object(project_state_path)
        project_state_loaded = loaded.get("ok", False)
        if project_state_loaded:
            state = loaded["value"]
            doc_status = state.get("documentation_status")
            has_doc_status = isinstance(doc_status, str) and bool(doc_status.strip())
            checks.append(
                _check(
                    "documentation_status_represented",
                    has_doc_status,
                    "Project-state documentation_status check.",
                    {"documentation_status": doc_status},
                )
            )
            if not has_doc_status:
                errors.append("documentation_status is missing in supplied project state.")
            project_state_summary = {
                "path": str(project_state_path),
                "current_milestone": state.get("current_milestone"),
                "current_phase": state.get("current_phase"),
                "documentation_status": state.get("documentation_status"),
                "validation_status": state.get("validation_status"),
            }
        else:
            checks.append(
                _check(
                    "project_state_loaded",
                    False,
                    "Project-state file could not be loaded.",
                    {"path": str(project_state_path), "error": loaded.get("error")},
                )
            )
            errors.append("project_state could not be loaded.")
    else:
        checks.append(_check("project_state_loaded", True, "No project state supplied; check skipped."))

    if not work_items:
        warnings.append("work_items is empty.")
    if not status:
        warnings.append("status is empty.")
    if not risks:
        warnings.append("risks is empty.")
    if not notes:
        warnings.append("notes is empty.")

    return {
        "definition_path": str(definition_path),
        "milestone_id": milestone_id,
        "title": title,
        "goal": goal,
        "status": status,
        "checks": checks,
        "errors": errors,
        "warnings": warnings,
        "required_docs_status": {"required": required_docs, "missing": missing_docs},
        "required_artifacts_status": {"required": required_artifacts, "missing": missing_artifacts},
        "validation_commands": validation_commands,
        "closeout_requirements": closeout_requirements,
        "project_state_path": str(project_state_path),
        "project_state_loaded": project_state_loaded,
        "project_state_summary": project_state_summary,
        "ready": len(errors) == 0,
        "checked_at": datetime.now(UTC).isoformat(),
    }


def _build_closeout_payload(definition: dict[str, Any], readiness: dict[str, Any]) -> dict[str, Any]:
    work_items = _as_string_list(definition.get("work_items"))
    completed_items = [item for item in work_items if item.lower().startswith("done:") or item.lower().startswith("[x]")]
    return {
        "title": "AresForge Local Milestone Closeout",
        "generated_at": datetime.now(UTC).isoformat(),
        "milestone_summary": {
            "milestone_id": str(definition.get("milestone_id", "")).strip(),
            "title": str(definition.get("title", "")).strip(),
            "goal": str(definition.get("goal", "")).strip(),
            "status": str(definition.get("status", "")).strip(),
            "parent_reference": str(definition.get("parent_reference", "")).strip(),
        },
        "completed_work_items": completed_items,
        "required_docs_status": readiness["required_docs_status"],
        "artifact_status": readiness["required_artifacts_status"],
        "validation_command_checklist": readiness["validation_commands"],
        "readiness_result": {
            "ready": readiness["ready"],
            "errors": readiness["errors"],
            "warnings": readiness["warnings"],
        },
        "documentation_reconciliation_reminder": "Run plan-doc-reconciliation and update source-of-truth docs as needed.",
        "github_sync_planning_reminder": "Optional: run plan-github-sync for future GitHub mutation windows.",
        "handoff_package_reminder": "Run generate-handoff-package after closeout updates.",
        "known_risks": _as_string_list(definition.get("risks")),
        "final_operator_checklist": [
            "Confirm readiness_result.ready is true.",
            "Confirm required docs and artifacts are present.",
            "Confirm validation commands were executed and reviewed.",
            "Confirm documentation reconciliation plan has been reviewed.",
            "Optional: confirm offline-to-GitHub sync plan is prepared for future sync.",
            "Generate and archive a final local handoff package.",
        ],
    }


def _render_inspection_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Local Milestone Inspection",
        "",
        f"- milestone_id: {payload['milestone_id']}",
        f"- title: {payload['title']}",
        f"- goal: {payload['goal']}",
        f"- status: {payload['status']}",
        f"- parent_reference: {payload['parent_reference']}",
        "",
        "## Work Items",
    ]
    lines.extend(f"- {item}" for item in payload["work_items"])
    if not payload["work_items"]:
        lines.append("- None")
    lines.extend(["", "## Required Docs"])
    lines.extend(f"- {item}" for item in payload["required_docs"])
    if not payload["required_docs"]:
        lines.append("- None")
    lines.extend(["", "## Required Artifacts"])
    lines.extend(f"- {item}" for item in payload["required_artifacts"])
    if not payload["required_artifacts"]:
        lines.append("- None")
    return "\n".join(lines)


def _render_readiness_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Local Milestone Readiness",
        "",
        f"- milestone_id: {payload['milestone_id']}",
        f"- ready: {payload['ready']}",
        "",
        "## Errors",
    ]
    lines.extend(f"- {item}" for item in payload["errors"])
    if not payload["errors"]:
        lines.append("- None")
    lines.extend(["", "## Warnings"])
    lines.extend(f"- {item}" for item in payload["warnings"])
    if not payload["warnings"]:
        lines.append("- None")
    return "\n".join(lines)


def _render_closeout_markdown(payload: dict[str, Any]) -> str:
    summary = payload["milestone_summary"]
    lines = [
        f"# {payload['title']}",
        "",
        f"- milestone_id: {summary.get('milestone_id')}",
        f"- title: {summary.get('title')}",
        f"- goal: {summary.get('goal')}",
        f"- readiness_ready: {payload['readiness_result']['ready']}",
        "",
        "## Final Operator Checklist",
    ]
    lines.extend(f"- {item}" for item in payload["final_operator_checklist"])
    return "\n".join(lines)


def _stdout_result(command: str, payload: dict[str, Any], output_format: str, markdown: str) -> dict[str, Any]:
    fmt = output_format.lower().strip()
    if fmt not in {"markdown", "json"}:
        return _error("invalid_format", {"format": output_format})
    return {
        "command": command,
        "ok": True,
        "local_only": True,
        "plan_only": True,
        "format": fmt,
        "wrote_output_file": False,
        "stdout": json.dumps(payload, indent=2) if fmt == "json" else markdown,
        "payload": payload,
    }


def _load_definition(path: Path) -> dict[str, Any]:
    loaded = _load_json_object(path)
    if not loaded.get("ok", False):
        return {"ok": False, "error": loaded.get("error"), "details": loaded.get("details", {})}
    data = loaded["value"]
    if not isinstance(data, dict):
        return {"ok": False, "error": "definition_not_object", "details": {"path": str(path)}}
    return {"ok": True, "definition": data}


def _load_json_object(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"ok": False, "error": "file_not_found", "details": {"path": str(path)}}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"ok": False, "error": "invalid_json", "details": {"path": str(path), "message": str(exc)}}
    if not isinstance(raw, dict):
        return {"ok": False, "error": "not_json_object", "details": {"path": str(path)}}
    return {"ok": True, "value": raw}


def _resolve_path(repo_root: Path, path: str | Path) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = (repo_root / candidate).resolve()
    return candidate


def _as_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        if isinstance(item, str):
            stripped = item.strip()
            if stripped:
                result.append(stripped)
    return result


def _check(name: str, passed: bool, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    entry: dict[str, Any] = {"name": name, "passed": passed, "message": message}
    if details is not None:
        entry["details"] = details
    return entry


def _error(error: str, details: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": False,
        "local_only": True,
        "plan_only": True,
        "error": error,
        "details": details,
    }
