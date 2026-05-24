from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig

COMMAND_NAME = "plan-github-sync"
DEFAULT_PROJECT_STATE_PATH = Path(".aresforge") / "state" / "project_state.json"
SOURCE_DOCS: tuple[str, ...] = (
    "docs/context/BUILD_STATE.md",
    "docs/context/AGENT_CONTEXT.md",
    "docs/roadmap/ROADMAP.md",
    "docs/architecture/RUNNABLE_SKELETON.md",
    "docs/operator/LOCAL_OPERATOR_USAGE.md",
)


def generate_github_sync_plan(
    config: AppConfig,
    *,
    state_file: str | Path | None = None,
    project_state: str | Path | None = None,
    output: str | Path | None = None,
    output_format: str = "markdown",
    force: bool = False,
) -> dict[str, Any]:
    format_name = output_format.lower().strip()
    if format_name not in {"markdown", "json"}:
        return _error("invalid_format", {"format": output_format})

    state_path = _resolve_path(config.repo_root, state_file) if state_file else None
    project_state_path = _resolve_path(config.repo_root, project_state) if project_state else (config.repo_root / DEFAULT_PROJECT_STATE_PATH)

    warnings: list[str] = []
    input_files_used: list[str] = []

    offline_state_data = _load_json_object(state_path)
    if isinstance(offline_state_data, dict) and "error" in offline_state_data:
        warnings.append(f"Offline state file warning: {offline_state_data['error']} ({offline_state_data.get('path')})")
    elif isinstance(offline_state_data, dict):
        input_files_used.append(str(state_path))

    project_state_data = _load_json_object(project_state_path)
    if isinstance(project_state_data, dict) and "error" in project_state_data:
        warnings.append(f"Project state warning: {project_state_data['error']} ({project_state_data.get('path')})")
    elif isinstance(project_state_data, dict):
        input_files_used.append(str(project_state_path))

    if not input_files_used:
        warnings.append("No readable offline state file or project state file detected; generating minimal advisory sync plan.")

    payload = _build_payload(
        repo_root=config.repo_root,
        offline_state_data=offline_state_data if isinstance(offline_state_data, dict) and "error" not in offline_state_data else None,
        project_state_data=project_state_data if isinstance(project_state_data, dict) and "error" not in project_state_data else None,
        offline_state_path=str(state_path) if state_path else None,
        project_state_path=str(project_state_path),
        warnings=warnings,
        input_files_used=input_files_used,
    )

    rendered_markdown = _render_markdown(payload)
    rendered_json = json.dumps(payload, indent=2)

    if output is None:
        return {
            "command": COMMAND_NAME,
            "ok": True,
            "local_only": True,
            "plan_only": True,
            "format": format_name,
            "wrote_output_file": False,
            "stdout": rendered_json if format_name == "json" else rendered_markdown,
            "payload": payload,
        }

    output_path = Path(output)
    if output_path.exists() and not force:
        return _error(
            "output_exists",
            {"path": str(output_path), "hint": "Re-run with --force to overwrite."},
            payload=payload,
        )

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return _error("output_directory_create_failed", {"path": str(output_path.parent), "message": str(exc)})

    content = rendered_json if format_name == "json" else rendered_markdown
    try:
        output_path.write_text(content + "\n", encoding="utf-8")
    except OSError as exc:
        return _error("output_write_failed", {"path": str(output_path), "message": str(exc)}, payload=payload)

    return {
        "command": COMMAND_NAME,
        "ok": True,
        "local_only": True,
        "plan_only": True,
        "format": format_name,
        "output": str(output_path),
        "force": force,
        "wrote_output_file": True,
        "warnings": payload["warnings"],
        "boundary_confirmations": payload["boundary_confirmations"],
    }


def _resolve_path(repo_root: Path, path: str | Path | None) -> Path:
    if path is None:
        return repo_root
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = (repo_root / candidate).resolve()
    return candidate


def _load_json_object(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    if not path.exists():
        return {"error": "file_not_found", "path": str(path)}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"error": "invalid_json", "path": str(path)}
    if not isinstance(raw, dict):
        return {"error": "not_json_object", "path": str(path)}
    return raw


def _build_payload(
    *,
    repo_root: Path,
    offline_state_data: dict[str, Any] | None,
    project_state_data: dict[str, Any] | None,
    offline_state_path: str | None,
    project_state_path: str,
    warnings: list[str],
    input_files_used: list[str],
) -> dict[str, Any]:
    parent_candidates: list[dict[str, Any]] = []
    child_candidates: list[dict[str, Any]] = []
    comment_candidates: list[dict[str, Any]] = []
    close_candidates: list[dict[str, Any]] = []
    pr_evidence_mappings: list[dict[str, Any]] = []
    label_candidates: list[dict[str, Any]] = []
    milestone_candidates: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []

    parent_issue = offline_state_data.get("parent_issue") if isinstance(offline_state_data, dict) else None
    if isinstance(parent_issue, dict):
        parent_number = parent_issue.get("number")
        parent_candidates.append(
            {
                "operation_type": "no_op",
                "target_type": "parent_issue",
                "issue_number": parent_number,
                "reason": "Parent issue captured for manual sync review.",
            }
        )
        if parent_issue.get("state", "").upper() == "OPEN":
            close_candidates.append(
                {
                    "operation_type": "close_candidate",
                    "target_type": "parent_issue",
                    "issue_number": parent_number,
                    "reason": "Parent closeout may be considered only after confirming child/accounting readiness.",
                }
            )

    child_issues = offline_state_data.get("child_issues") if isinstance(offline_state_data, dict) else None
    if isinstance(child_issues, list):
        for child in child_issues:
            if not isinstance(child, dict):
                continue
            child_number = child.get("number")
            child_candidates.append(
                {
                    "operation_type": "no_op",
                    "target_type": "child_issue",
                    "issue_number": child_number,
                    "state": child.get("state"),
                    "reason": "Child issue captured for manual sync review.",
                }
            )
            comment_candidates.append(
                {
                    "operation_type": "comment_candidate",
                    "target_type": "issue",
                    "issue_number": child_number,
                    "reason": "Post offline evidence summary comment if not already posted on GitHub.",
                }
            )
            if str(child.get("state", "")).upper() != "CLOSED":
                close_candidates.append(
                    {
                        "operation_type": "close_candidate",
                        "target_type": "child_issue",
                        "issue_number": child_number,
                        "reason": "Child appears open in offline state and may require closeout after validation.",
                    }
                )

            merged_pr_evidence = child.get("merged_pr_evidence")
            if isinstance(merged_pr_evidence, list):
                for pr in merged_pr_evidence:
                    if not isinstance(pr, dict):
                        continue
                    pr_evidence_mappings.append(
                        {
                            "operation_type": "comment_candidate",
                            "child_issue": child_number,
                            "pr_number": pr.get("number"),
                            "pr_url": pr.get("url"),
                            "reason": "Link offline evidence to merged PR context.",
                        }
                    )

            milestone_title = ""
            milestone = child.get("milestone")
            if isinstance(milestone, dict):
                title = milestone.get("title")
                if isinstance(title, str):
                    milestone_title = title.strip()
            if milestone_title:
                milestone_candidates.append(
                    {
                        "operation_type": "milestone_candidate",
                        "target_type": "issue",
                        "issue_number": child_number,
                        "milestone": milestone_title,
                        "reason": "Confirm GitHub milestone assignment matches offline state.",
                    }
                )

    if isinstance(project_state_data, dict):
        if project_state_data.get("pending_sync") is True:
            label_candidates.append(
                {
                    "operation_type": "label_candidate",
                    "target_type": "project_state",
                    "label": "pending-sync",
                    "reason": "Project state indicates pending sync work that may need tracking labels on GitHub.",
                }
            )

        documentation_status = project_state_data.get("documentation_status")
        if isinstance(documentation_status, str) and documentation_status.strip():
            label_candidates.append(
                {
                    "operation_type": "label_candidate",
                    "target_type": "project_state",
                    "label": f"documentation-status:{documentation_status.strip().lower()}",
                    "reason": "Documentation status may require matching tracking labels after sync.",
                }
            )

    validation_candidates = [
        {
            "operation_type": "validation_candidate",
            "command": "python -m pytest tests/test_local_github_sync_planner.py tests/test_cli_github_sync_planner.py",
            "reason": "Validate M29 planner behavior locally before any live GitHub sync actions.",
        },
        {
            "operation_type": "validation_candidate",
            "command": "python -m aresforge plan-github-sync --format json",
            "reason": "Rebuild and review stable JSON sync plan output.",
        },
    ]

    if not comment_candidates and not close_candidates and not pr_evidence_mappings:
        blocked.append(
            {
                "operation_type": "blocked",
                "reason": "Insufficient offline candidate data found for comments/closures/PR evidence mapping.",
            }
        )

    manual_review_checklist = [
        "Confirm local plan inputs are current and correspond to intended milestone/issue scope.",
        "Review each comment_candidate and close_candidate for correctness before any live mutation.",
        "Confirm PR evidence mappings still match merged PRs and intended linked issues.",
        "Confirm label/milestone candidates align with current project governance.",
        "Run validation_candidate commands locally before any live sync attempt.",
    ]

    operations: list[dict[str, Any]] = []
    operations.extend(comment_candidates)
    operations.extend(close_candidates)
    operations.extend(label_candidates)
    operations.extend(milestone_candidates)
    operations.extend(validation_candidates)
    operations.extend(parent_candidates)
    operations.extend(child_candidates)
    operations.extend(blocked)

    docs_context_paths = [
        str((repo_root / relative).resolve())
        for relative in SOURCE_DOCS
        if (repo_root / relative).exists()
    ]

    return {
        "title": "AresForge Offline-to-GitHub Sync Plan",
        "generated_at": datetime.now(UTC).isoformat(),
        "plan_only": True,
        "local_only": True,
        "github_operations_performed": False,
        "explicit_no_github_operations_statement": (
            "No GitHub operations were performed. This artifact is plan-only and local-only."
        ),
        "input_files_used": sorted(input_files_used),
        "offline_state_file": offline_state_path,
        "project_state_file": project_state_path,
        "source_of_truth_docs_used": docs_context_paths,
        "parent_issue_sync_candidates": parent_candidates,
        "child_issue_sync_candidates": child_candidates,
        "evidence_comments_to_post_later": comment_candidates,
        "issue_closures_to_consider_later": close_candidates,
        "pr_evidence_mappings": pr_evidence_mappings,
        "labels_to_consider_later": label_candidates,
        "milestones_to_consider_later": milestone_candidates,
        "validation_commands_to_run_before_live_sync": validation_candidates,
        "github_rate_limit_risk_warnings": [
            "Live comment/close/label/milestone sync may hit GitHub API/GraphQL rate limits; sequence operations and monitor limits.",
            "Prefer batched operator review and scoped sync windows to reduce rate-limit risk.",
        ],
        "manual_review_checklist": manual_review_checklist,
        "warnings": sorted(set(warnings)),
        "operations": operations,
        "classification_types": [
            "comment_candidate",
            "close_candidate",
            "label_candidate",
            "milestone_candidate",
            "validation_candidate",
            "no_op",
            "blocked",
        ],
        "boundary_confirmations": [
            "Plan-only offline-to-GitHub sync planning.",
            "Local-only inspection.",
            "No gh commands executed.",
            "No GitHub API calls executed.",
            "No network access used.",
            "No repository or GitHub mutation executed.",
        ],
    }


def _render_markdown(payload: dict[str, Any]) -> str:
    lines: list[str] = [
        f"# {payload['title']}",
        "",
        f"- generated_at: {payload['generated_at']}",
        f"- plan_only: {payload['plan_only']}",
        f"- local_only: {payload['local_only']}",
        f"- github_operations_performed: {payload['github_operations_performed']}",
        f"- statement: {payload['explicit_no_github_operations_statement']}",
        "",
        "## Input Files Used",
    ]

    input_files_used = payload.get("input_files_used", [])
    if input_files_used:
        lines.extend(f"- {item}" for item in input_files_used)
    else:
        lines.append("- None")

    lines.extend(["", "## Parent Issue Sync Candidates"])
    lines.extend(_render_operation_list(payload.get("parent_issue_sync_candidates", [])))

    lines.extend(["", "## Child Issue Sync Candidates"])
    lines.extend(_render_operation_list(payload.get("child_issue_sync_candidates", [])))

    lines.extend(["", "## Evidence Comments To Post Later"])
    lines.extend(_render_operation_list(payload.get("evidence_comments_to_post_later", [])))

    lines.extend(["", "## Issue Closures To Consider Later"])
    lines.extend(_render_operation_list(payload.get("issue_closures_to_consider_later", [])))

    lines.extend(["", "## PR Evidence Mappings"])
    pr_mappings = payload.get("pr_evidence_mappings", [])
    if pr_mappings:
        for item in pr_mappings:
            lines.append(
                f"- child_issue={item.get('child_issue')} pr={item.get('pr_number')} type={item.get('operation_type')} reason={item.get('reason')}"
            )
    else:
        lines.append("- None")

    lines.extend(["", "## Labels/Milestones To Consider Later"])
    lines.extend(_render_operation_list(payload.get("labels_to_consider_later", [])))
    lines.extend(_render_operation_list(payload.get("milestones_to_consider_later", [])))

    lines.extend(["", "## Validation Commands Before Live Sync"])
    for item in payload.get("validation_commands_to_run_before_live_sync", []):
        lines.append(f"- {item.get('command')}")

    lines.extend(["", "## Rate Limit Risk Warnings"])
    lines.extend(f"- {item}" for item in payload.get("github_rate_limit_risk_warnings", []))

    lines.extend(["", "## Manual Review Checklist"])
    lines.extend(f"- {item}" for item in payload.get("manual_review_checklist", []))

    warnings = payload.get("warnings", [])
    lines.extend(["", "## Warnings"])
    if warnings:
        lines.extend(f"- {item}" for item in warnings)
    else:
        lines.append("- None")

    lines.extend(["", "## Boundary Confirmations"])
    lines.extend(f"- {item}" for item in payload.get("boundary_confirmations", []))

    return "\n".join(lines)


def _render_operation_list(items: list[dict[str, Any]]) -> list[str]:
    if not items:
        return ["- None"]
    rendered: list[str] = []
    for item in items:
        operation_type = item.get("operation_type", "no_op")
        reason = item.get("reason", "")
        issue_number = item.get("issue_number")
        target_type = item.get("target_type", "")
        core = f"type={operation_type}"
        if target_type:
            core += f" target={target_type}"
        if issue_number is not None:
            core += f" issue=#{issue_number}"
        if reason:
            core += f" reason={reason}"
        rendered.append(f"- {core}")
    return rendered


def _error(error: str, details: dict[str, Any], payload: dict[str, Any] | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "command": COMMAND_NAME,
        "ok": False,
        "local_only": True,
        "plan_only": True,
        "error": error,
        "details": details,
    }
    if payload is not None:
        result["payload"] = payload
    return result
