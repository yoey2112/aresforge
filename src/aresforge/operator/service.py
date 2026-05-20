from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aresforge.artifacts.store import ArtifactBundle, write_markdown_json_bundle
from aresforge.config import AppConfig
from aresforge.routing.routes import RoutePlan


def _bullet_lines(items: list[str], empty_message: str) -> list[str]:
    return [f"- {item}" for item in items] or [f"- {empty_message}"]


def render_prompt_package(
    *,
    config: AppConfig,
    title: str,
    objective: str,
    work_item_id: str | None,
    route_plan: RoutePlan | None,
    notes: str,
) -> ArtifactBundle:
    payload: dict[str, Any] = {
        "title": title,
        "objective": objective,
        "work_item_id": work_item_id,
        "route_plan": route_plan.as_dict() if route_plan else None,
        "notes": notes,
        "repo_root": str(config.repo_root),
        "github_repo": f"{config.github_owner}/{config.github_repo}",
    }
    markdown = "\n".join(
        [
            f"# {title}",
            "",
            "## Objective",
            objective,
            "",
            "## Context",
            f"- Repository: `{config.repo_root}`",
            f"- GitHub repo: `{config.github_owner}/{config.github_repo}`",
            f"- Work item: `{work_item_id or 'not-linked'}`",
            "",
            "## Planned Route",
            "```json",
            json.dumps(payload["route_plan"], indent=2),
            "```",
            "",
            "## Operator Notes",
            notes or "No additional notes.",
            "",
            "## Automation Boundary",
            "This artifact is human-reviewable input only. It does not authorize autonomous GitHub or repository state changes.",
        ]
    )
    return write_markdown_json_bundle(config.prompts_dir, title=title, markdown=markdown, payload=payload)


def render_evidence_package(
    *,
    config: AppConfig,
    title: str,
    work_item_id: str | None,
    files_changed: list[str],
    validations_run: list[str],
    skipped_checks: list[str],
    protected_issue_checks: list[str],
    automation_boundary_confirmation: str,
) -> ArtifactBundle:
    payload = {
        "title": title,
        "work_item_id": work_item_id,
        "files_changed": files_changed,
        "validations_run": validations_run,
        "skipped_checks": skipped_checks,
        "protected_issue_checks": protected_issue_checks,
        "automation_boundary_confirmation": automation_boundary_confirmation,
    }
    markdown = "\n".join(
        [
            f"# {title}",
            "",
            "## Files Changed",
            *_bullet_lines(files_changed, "None recorded."),
            "",
            "## Validations Run",
            *_bullet_lines(validations_run, "None recorded."),
            "",
            "## Skipped Checks",
            *_bullet_lines(skipped_checks, "None recorded."),
            "",
            "## Protected Issue Checks",
            *_bullet_lines(protected_issue_checks, "None recorded."),
            "",
            "## Automation Boundary Confirmation",
            automation_boundary_confirmation,
        ]
    )
    return write_markdown_json_bundle(config.evidence_dir, title=title, markdown=markdown, payload=payload)


def render_codex_handoff(
    *,
    config: AppConfig,
    title: str,
    summary: str,
    work_item_id: str | None,
    route_plan: RoutePlan | None,
    requested_output: str,
) -> ArtifactBundle:
    payload = {
        "title": title,
        "summary": summary,
        "work_item_id": work_item_id,
        "route_plan": route_plan.as_dict() if route_plan else None,
        "requested_output": requested_output,
        "boundary": "Output-file generation only. No autonomous Codex invocation.",
    }
    markdown = "\n".join(
        [
            f"# {title}",
            "",
            "## Summary",
            summary,
            "",
            "## Requested Output",
            requested_output,
            "",
            "## Routing Context",
            "```json",
            json.dumps(payload["route_plan"], indent=2),
            "```",
            "",
            "## Safety Boundary",
            "This handoff file is for human review and manual execution only. It must not trigger autonomous Codex, GitHub, or repository actions.",
        ]
    )
    return write_markdown_json_bundle(
        config.codex_handoffs_dir, title=title, markdown=markdown, payload=payload
    )
