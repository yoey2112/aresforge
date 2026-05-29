from __future__ import annotations

import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.local_active_project import inspect_active_project
from aresforge.operator.local_ai_artifacts import artifact_warning, register_ai_artifact
from aresforge.operator.local_project_report import read_local_project_reports
from aresforge.operator.local_project_queue import read_local_project_progress_rollup

_HANDOFF_BOUNDARY_CONFIRMATIONS: tuple[str, ...] = (
    "Local-only project handoff generation.",
    "Read-only local project, queue, evidence, closeout, and report inspection.",
    "Optional artifact output is local file-backed only.",
    "No GitHub API calls.",
    "No gh calls.",
    "No GitHub issues, PRs, workflow activity, or mutation.",
    "No agent execution.",
    "No Codex execution.",
    "No local LLM execution.",
    "No LLM/model routing execution.",
)

_OPERATING_RULES: tuple[str, ...] = (
    "Local-first.",
    "File-backed.",
    "Operator-gated.",
    "No GitHub API.",
    "No gh.",
    "No GitHub issues, PRs, workflow activity, or mutation from the app.",
    "No real agent execution.",
    "No automatic Codex execution.",
    "No local LLM execution.",
    "No LLM/model routing execution.",
)

_STARTUP_VALIDATION_COMMANDS: tuple[str, ...] = (
    "git status --short",
    "git branch --show-current",
    "git log -1 --oneline",
    "python -m pytest tests/test_local_project_queue.py tests/test_local_project_factory.py tests/test_hub_dashboard_summary_api.py tests/test_hub_local_queue_lifecycle_api.py tests/test_hub_ui_foundation.py",
    "python -m aresforge inspect-local-queue-agent-summary",
    "python -m aresforge inspect-local-project-report",
)


def generate_local_project_handoff(
    config: AppConfig,
    *,
    project_id: str | None = None,
    include_queue: bool = True,
    include_reports: bool = True,
    include_evidence: bool = True,
    next_milestone: str | None = None,
    next_instruction: str | None = None,
    output: str | Path | None = None,
    force: bool = False,
    latest_commit: str | None = None,
) -> dict[str, Any]:
    generated_at = datetime.now(UTC).isoformat()
    reports = read_local_project_reports(config)
    active_payload = inspect_active_project(config)
    active_project = active_payload.get("active_project") if isinstance(active_payload.get("active_project"), dict) else {}
    active_repo = active_payload.get("active_repo") if isinstance(active_payload.get("active_repo"), dict) else {}
    requested_project_id = str(project_id or "").strip()
    resolved_project_id = requested_project_id or str(active_payload.get("active_project_id", "")).strip()
    progress_rollup: dict[str, Any] = {}
    warnings: list[str] = []
    blockers: list[str] = []

    if resolved_project_id:
        progress = read_local_project_progress_rollup(config, project_id=resolved_project_id)
        if progress.get("ok", False):
            progress_rollup = progress
        else:
            blockers.append(
                str((progress.get("details") or {}).get("message", progress.get("error", "project_progress_unavailable")))
            )
    else:
        warnings.append("No project_id supplied and no active project is selected.")

    if requested_project_id and requested_project_id != str(active_payload.get("active_project_id", "")).strip():
        warnings.append("Requested project is not the active project; repo path may be unavailable.")

    git_state = _collect_local_git_state(config.repo_root)
    latest_known_commit = str(latest_commit or "").strip() or str(git_state.get("current_head", "")).strip()
    project_name = (
        str(progress_rollup.get("project_name", "")).strip()
        or str(active_project.get("name", "")).strip()
        or resolved_project_id
        or "Unknown project"
    )
    repo_path = str(active_repo.get("path", "")).strip() or str(config.repo_root)
    branch_expectation = str(git_state.get("current_branch", "")).strip() or "main"
    detected_milestone = _latest_milestone_from_docs(config.repo_root)
    recommended_next_milestone = str(next_milestone or "").strip() or _recommended_next_milestone(config.repo_root)
    recommended_next_instruction = str(next_instruction or "").strip() or "Continue with the next local-only, operator-gated milestone."
    summary = _build_summary(
        reports=reports,
        progress_rollup=progress_rollup,
        include_queue=include_queue,
        include_reports=include_reports,
        include_evidence=include_evidence,
    )
    blockers = _unique_list(blockers + list(reports.get("blockers", [])))
    warnings = _unique_list(warnings + list(reports.get("warnings", [])) + list(git_state.get("warnings", [])))

    handoff_markdown = _render_handoff_markdown(
        project_name=project_name,
        project_id=resolved_project_id,
        repo_path=repo_path,
        branch_expectation=branch_expectation,
        current_milestone=detected_milestone,
        latest_known_commit=latest_known_commit,
        generated_at=generated_at,
        summary=summary,
        progress_rollup=progress_rollup,
        reports=reports,
        include_queue=include_queue,
        include_reports=include_reports,
        include_evidence=include_evidence,
        next_milestone=recommended_next_milestone,
        next_instruction=recommended_next_instruction,
        blockers=blockers,
        warnings=warnings,
    )

    payload: dict[str, Any] = {
        "command": "generate-local-project-handoff",
        "ok": True,
        "local_only": True,
        "read_only": output is None,
        "project_id": resolved_project_id,
        "project_name": project_name,
        "generated_at": generated_at,
        "handoff_markdown": handoff_markdown,
        "summary": summary,
        "next_safe_action": "Copy the handoff into the next operator chat or write the optional local artifact if requested.",
        "warnings": warnings,
        "blockers": blockers,
        "boundary_confirmations": list(_HANDOFF_BOUNDARY_CONFIRMATIONS),
    }

    if output is None:
        return payload

    output_path = _resolve_output_path(config.repo_root, output)
    if output_path.exists() and not force:
        payload.update(
            {
                "ok": False,
                "read_only": True,
                "output_path": str(output_path),
                "next_safe_action": "Choose a different local output path or re-run with force=true.",
                "warnings": _unique_list([*warnings, "Output file already exists. Re-run with force=true to overwrite."]),
            }
        )
        return payload

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(handoff_markdown + "\n", encoding="utf-8")
    except OSError as exc:
        payload.update(
            {
                "ok": False,
                "read_only": True,
                "output_path": str(output_path),
                "next_safe_action": "Inspect the local output path and retry handoff generation.",
                "warnings": _unique_list([*warnings, f"Failed to write local handoff artifact: {exc}"]),
            }
        )
        return payload

    payload.update(
        {
            "read_only": False,
            "output_path": str(output_path),
            "wrote_output_file": True,
            "next_safe_action": "Review the local handoff artifact before copying it into the next operator chat.",
        }
    )
    artifact_result = register_ai_artifact(
        config,
        artifact_type="handoff",
        artifact_path=output_path,
        source_action="generate_local_project_handoff",
        project_id=resolved_project_id,
        summary="Local project handoff artifact generated for manual operator continuity.",
        warnings=warnings,
    )
    payload["artifact_registry"] = artifact_result.get("artifact", {})
    payload["warnings"] = _unique_list([*payload["warnings"], *artifact_warning(artifact_result)])
    return payload


def _build_summary(
    *,
    reports: dict[str, Any],
    progress_rollup: dict[str, Any],
    include_queue: bool,
    include_reports: bool,
    include_evidence: bool,
) -> dict[str, Any]:
    queue_totals = reports.get("queue_item_totals", {}) if include_queue else {}
    evidence = reports.get("evidence_summary", {}) if include_evidence else {}
    closeout = reports.get("closeout_summary", {}) if include_evidence else {}
    return {
        "include_queue": include_queue,
        "include_reports": include_reports,
        "include_evidence": include_evidence,
        "project_count": int(reports.get("overall_project_count", 0)) if include_reports else 0,
        "queue_total": int(queue_totals.get("total", 0)) if isinstance(queue_totals, dict) else 0,
        "ready_count": int(queue_totals.get("ready", 0)) if isinstance(queue_totals, dict) else 0,
        "blocked_count": int(queue_totals.get("blocked", 0)) if isinstance(queue_totals, dict) else 0,
        "in_progress_count": int(queue_totals.get("in_progress", 0)) if isinstance(queue_totals, dict) else 0,
        "closed_completed_count": int(queue_totals.get("closed_completed", 0)) if isinstance(queue_totals, dict) else 0,
        "evidence_captured_count": int(evidence.get("items_with_evidence_captured", 0)) if isinstance(evidence, dict) else 0,
        "closeout_eligible_count": int(closeout.get("items_eligible_for_closeout", 0)) if isinstance(closeout, dict) else 0,
        "latest_activity_timestamp": str((reports.get("latest_activity_summary") or {}).get("latest_activity_timestamp", "")).strip(),
        "progress_next_safe_action": str(progress_rollup.get("next_safe_action", "")).strip(),
    }


def _render_handoff_markdown(
    *,
    project_name: str,
    project_id: str,
    repo_path: str,
    branch_expectation: str,
    current_milestone: str,
    latest_known_commit: str,
    generated_at: str,
    summary: dict[str, Any],
    progress_rollup: dict[str, Any],
    reports: dict[str, Any],
    include_queue: bool,
    include_reports: bool,
    include_evidence: bool,
    next_milestone: str,
    next_instruction: str,
    blockers: list[str],
    warnings: list[str],
) -> str:
    lines: list[str] = [
        "# Local Project Handoff",
        "",
        f"- generated_at: {generated_at}",
        f"- project_name: {project_name}",
        f"- project_id: {project_id or '-'}",
        f"- repo_path: {repo_path}",
        f"- branch_expectation: {branch_expectation}",
        f"- latest_known_milestone: {current_milestone or '-'}",
        f"- latest_known_commit: {latest_known_commit or '-'}",
        "",
        "## Operating Rules",
        *[f"- {item}" for item in _OPERATING_RULES],
        "- Clear prohibition: no GitHub API, gh, agent execution, Codex execution, or local LLM execution is currently allowed.",
        "",
        "## Architecture Boundaries",
        "- AresForge remains local-first, file-backed, and operator-gated.",
        "- Hub API behavior stays local-only.",
        "- Queue storage remains one canonical local queue.",
        "- Reports and handoffs are read-only unless the operator explicitly writes a local artifact.",
        "- Agent/LLM routing remains future work and is not executed.",
        "",
        "## Current Hub Capabilities",
        "- Project selection and local project registry inspection.",
        "- Local queue intake, detail review, readiness checks, prompt-pack generation, evidence capture, and closeout.",
        "- Project progress rollup and Reports v1.",
        "- Local handoff generation for copy/paste continuity.",
    ]
    if include_queue:
        lines.extend(
            [
                "",
                "## Queue And Progress Summary",
                f"- queue_total: {summary['queue_total']}",
                f"- ready_count: {summary['ready_count']}",
                f"- blocked_count: {summary['blocked_count']}",
                f"- in_progress_count: {summary['in_progress_count']}",
                f"- closed_completed_count: {summary['closed_completed_count']}",
                f"- progress_next_safe_action: {summary['progress_next_safe_action'] or '-'}",
            ]
        )
        open_items = _open_item_lines(progress_rollup)
        lines.extend(["", "## Open Queue Items", *(open_items or ["- none"])])
    if include_reports:
        lines.extend(
            [
                "",
                "## Reports v1 Summary",
                f"- project_count: {summary['project_count']}",
                f"- latest_activity_timestamp: {summary['latest_activity_timestamp'] or '-'}",
                f"- reports_next_safe_action: {reports.get('next_safe_action', '-')}",
            ]
        )
    if include_evidence:
        closeout = reports.get("closeout_summary", {}) if isinstance(reports.get("closeout_summary"), dict) else {}
        evidence = reports.get("evidence_summary", {}) if isinstance(reports.get("evidence_summary"), dict) else {}
        lines.extend(
            [
                "",
                "## Evidence And Closeout Summary",
                f"- evidence_captured_count: {summary['evidence_captured_count']}",
                f"- evidence_item_ids: {', '.join(evidence.get('item_ids', [])) or 'none'}",
                f"- closeout_eligible_count: {summary['closeout_eligible_count']}",
                f"- closeout_eligible_item_ids: {', '.join(closeout.get('eligible_item_ids', [])) or 'none'}",
                f"- closed_completed_item_ids: {', '.join(closeout.get('closed_completed_item_ids', [])) or 'none'}",
            ]
        )
    lines.extend(
        [
            "",
            "## Blockers And Warnings",
            *(["- blockers: none"] if not blockers else [f"- blocker: {item}" for item in blockers]),
            *(["- warnings: none"] if not warnings else [f"- warning: {item}" for item in warnings]),
            "",
            "## Recommended Next Milestone",
            f"- {next_milestone}",
            "",
            "## Recommended Next Operator Instruction",
            f"- {next_instruction}",
            "",
            "## Start-Of-Next-Chat Validation",
            *[f"- {item}" for item in _STARTUP_VALIDATION_COMMANDS],
        ]
    )
    return "\n".join(lines).rstrip()


def _open_item_lines(progress_rollup: dict[str, Any]) -> list[str]:
    items: list[dict[str, Any]] = []
    for field in ("ready_items", "blocked_items", "in_progress_items", "items_eligible_for_closeout"):
        values = progress_rollup.get(field, [])
        if isinstance(values, list):
            items.extend([item for item in values if isinstance(item, dict)])
    seen: set[str] = set()
    lines: list[str] = []
    for item in items:
        item_id = str(item.get("item_id", "")).strip()
        if not item_id or item_id in seen:
            continue
        seen.add(item_id)
        lines.append(
            f"- {item_id} | status={item.get('status', '-') or '-'} | type={item.get('item_type', '-') or '-'} | title={item.get('title', '-') or '-'}"
        )
    return lines


def _collect_local_git_state(repo_root: Path) -> dict[str, Any]:
    commands = {
        "current_branch": ["git", "branch", "--show-current"],
        "current_head": ["git", "rev-parse", "HEAD"],
    }
    result: dict[str, Any] = {"warnings": []}
    for key, command in commands.items():
        try:
            completed = subprocess.run(command, cwd=repo_root, check=False, capture_output=True, text=True)
        except OSError as exc:
            result[key] = ""
            result["warnings"].append(f"{' '.join(command)} failed: {exc}")
            continue
        if completed.returncode != 0:
            result[key] = ""
            result["warnings"].append(f"{' '.join(command)} failed: {(completed.stderr or '').strip() or completed.returncode}")
            continue
        result[key] = (completed.stdout or "").strip()
    return result


def _latest_milestone_from_docs(repo_root: Path) -> str:
    for relative in ("docs/context/BUILD_STATE.md", "docs/roadmap/ROADMAP.md"):
        text = _read_text(repo_root / relative)
        match = re.search(r"^##\s+(M\d+[A-Z]?\s+.+?)\s*$", text, flags=re.MULTILINE)
        if match:
            return match.group(1).strip()
    return ""


def _recommended_next_milestone(repo_root: Path) -> str:
    text = _read_text(repo_root / "docs/context/BUILD_STATE.md")
    match = re.search(r"Recommended next milestone:\s*\n\s*-\s*(M\d+[A-Z]?\s+-\s+.+?)\s*$", text, flags=re.MULTILINE)
    if match:
        return match.group(1).strip()
    return "M51 - Project AI Settings Contract"


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _resolve_output_path(repo_root: Path, output: str | Path) -> Path:
    candidate = Path(output)
    if candidate.is_absolute():
        return candidate
    return (repo_root / candidate).resolve()


def _unique_list(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        normalized = str(value).strip()
        if normalized and normalized not in result:
            result.append(normalized)
    return result
