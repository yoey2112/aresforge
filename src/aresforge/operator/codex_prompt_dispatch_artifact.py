from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.local_project_queue import resolve_project_queue_path
from aresforge.operator.queue_agent_dispatch_plan import build_queue_agent_dispatch_plan

ARTIFACT_GENERATOR_VERSION = "m98.1"
CODEX_PROMPT_LANE = "codex_prompt_artifact"

_BOUNDARY_CONFIRMATIONS = (
    "M98 Codex prompt dispatch artifact generation is local-only.",
    "Generated artifacts are manual/operator-gated copy/paste prompts only.",
    "execution_allowed=false is required and preserved.",
    "M98 does not execute Codex.",
    "M98 does not invoke Ollama or local LLMs.",
    "M98 does not call GitHub APIs or gh.",
    "M98 does not make network calls.",
    "M98 does not execute external agents.",
    "M98 does not apply patches.",
    "M98 does not create GitHub issues, PRs, workflows, or mutations.",
    "M98 does not auto-start, auto-complete, or auto-dispatch queue items.",
)

_SOURCE_DOCS = (
    "docs/context/BUILD_STATE.md",
    "docs/context/AGENT_CONTEXT.md",
    "docs/roadmap/ROADMAP.md",
    "docs/operator/LOCAL_OPERATOR_USAGE.md",
    "docs/architecture/RUNNABLE_SKELETON.md",
    "docs/architecture/AGENT_LLM_ROUTING_STRATEGY.md",
    "docs/architecture/LOCAL_LLM_ENVIRONMENT_CONTRACT.md",
    "docs/architecture/DOCUMENTATION_AGENT_CONTRACT.md",
)

_DEFAULT_FILES_TO_INSPECT = (
    "src/aresforge/operator/queue_agent_dispatch_plan.py",
    "src/aresforge/cli.py",
    "tests/test_queue_agent_dispatch_plan.py",
    "tests/test_cli.py",
    "Existing local queue operator modules",
    "Existing prompt-pack or Codex prompt generation helpers from prior milestones",
    "Existing handoff/package/report artifact writing patterns",
)

_VALIDATION_COMMANDS = (
    "python -m pytest tests/test_cli.py",
    "python -m pytest tests/test_queue_agent_dispatch_plan.py",
    "python -m pytest tests/test_codex_prompt_dispatch_artifact.py",
    "python -m pytest tests/test_local_project_queue.py tests/test_local_queue_agent_summary.py tests/test_local_project_report.py",
    "git diff --check",
    "python -m aresforge inspect-local-project-report",
    "python -m aresforge inspect-local-queue-agent-summary",
    "python -m aresforge inspect-project-queue --project-id aresforge",
    "python -m aresforge inspect-queue-dispatch-plan --item-id <item_id> --format json",
    "python -m aresforge generate-codex-dispatch-artifact --item-id <item_id>",
    "python -m aresforge generate-codex-dispatch-artifact --item-id <item_id> --format json",
)


def generate_codex_prompt_dispatch_artifact(
    config: AppConfig,
    *,
    item_id: str,
    queue_path: str | Path | None = None,
    registry_path: str | Path | None = None,
    output: str | Path | None = None,
    force: bool = False,
    output_format: str = "markdown",
    dispatch_plan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_item_id = str(item_id or "").strip()
    plan = (
        dispatch_plan
        if dispatch_plan is not None
        else build_queue_agent_dispatch_plan(
            config,
            item_id=normalized_item_id,
            queue_path=queue_path,
            registry_path=registry_path,
        )
    )
    item = _load_queue_item(config, item_id=normalized_item_id, queue_path=queue_path)
    prompt_text = ""
    blocked_reasons = _generation_blockers(plan)
    generated = not blocked_reasons

    if generated:
        prompt_text = _render_prompt(
            config=config,
            item=item,
            plan=plan,
        )

    output_path = ""
    if generated and output is not None:
        write_result = _write_prompt(config=config, output=output, item_id=normalized_item_id, prompt_text=prompt_text, force=force)
        if not write_result["ok"]:
            generated = False
            blocked_reasons.append(str(write_result["reason"]))
        output_path = str(write_result.get("output_path", ""))

    selected_lane = str(plan.get("selected_lane", "")).strip()
    payload: dict[str, Any] = {
        "ok": generated,
        "generated": generated,
        "blocked": not generated,
        "blocked_reasons": sorted({reason for reason in blocked_reasons if reason}),
        "item_id": normalized_item_id,
        "selected_lane": selected_lane,
        "output_path": output_path,
        "prompt_text": prompt_text if generated and output is None else "",
        "prompt_preview": _preview(prompt_text) if generated and output is not None else "",
        "local_only": True,
        "execution_allowed": False,
        "codex_executed": False,
        "github_api_called": False,
        "gh_called": False,
        "network_called": False,
        "external_agent_executed": False,
        "patches_applied": False,
        "queue_mutated": False,
        "artifact_generator_version": ARTIFACT_GENERATOR_VERSION,
        "dispatch_plan_version": str(plan.get("dispatch_plan_version", "")).strip(),
        "next_safe_action": _next_safe_action(generated=generated, output_path=output_path, item_id=normalized_item_id),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }
    return _stdout_result("generate-codex-dispatch-artifact", payload, output_format, _render_markdown(payload))


def _generation_blockers(plan: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    selected_lane = str(plan.get("selected_lane", "")).strip()
    if selected_lane != CODEX_PROMPT_LANE:
        blockers.append(f"Selected lane is {selected_lane or '<missing>'}; M98 only generates artifacts for codex_prompt_artifact.")
    plan_blockers = plan.get("blocked_reasons", [])
    if isinstance(plan_blockers, list):
        blockers.extend(str(reason).strip() for reason in plan_blockers if str(reason).strip())
    if plan.get("local_only") is not True:
        blockers.append("Dispatch plan local_only must be true.")
    if plan.get("execution_allowed") is not False:
        blockers.append("Dispatch plan execution_allowed must be false.")
    if bool(plan.get("blocked", False)):
        blockers.append("Dispatch plan is blocked.")
    return sorted({blocker for blocker in blockers if blocker})


def _load_queue_item(config: AppConfig, *, item_id: str, queue_path: str | Path | None) -> dict[str, Any]:
    resolved_queue_path = resolve_project_queue_path(config.repo_root, queue_path)
    if not resolved_queue_path.exists():
        return {}
    try:
        raw = json.loads(resolved_queue_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    items = raw.get("work_items", []) if isinstance(raw, dict) else []
    item = next(
        (
            candidate
            for candidate in items
            if isinstance(candidate, dict) and str(candidate.get("item_id", "")).strip() == item_id
        ),
        {},
    )
    return item if isinstance(item, dict) else {}


def _render_prompt(*, config: AppConfig, item: dict[str, Any], plan: dict[str, Any]) -> str:
    confidence = plan.get("routing_confidence", {}) if isinstance(plan.get("routing_confidence"), dict) else {}
    artifact_intent = plan.get("planned_artifact_intent", {}) if isinstance(plan.get("planned_artifact_intent"), dict) else {}
    item_id = str(plan.get("item_id", "")).strip()
    title = str(plan.get("title", "")).strip()
    milestone = str(plan.get("milestone", "")).strip()
    requirements = _requirements_from_item(item)
    lines = [
        "AresForge Codex Prompt Dispatch Artifact",
        "",
        "Manual/operator-gated copy/paste prompt only.",
        "execution_allowed=false",
        "Do not execute this artifact from AresForge.",
        "",
        "Task context:",
        f"- task title: {title}",
        f"- item_id: {item_id}",
        f"- project_id: {plan.get('project_id') or '-'}",
        f"- milestone: {milestone or '-'}",
        f"- queue status: {plan.get('status') or '-'}",
        f"- dispatch lane: {plan.get('selected_lane')}",
        f"- dispatch confidence: {confidence.get('score', 0)} ({confidence.get('level', '')})",
        f"- selection reason: {plan.get('lane_selection_reason', '')}",
        f"- planned artifact intent: {artifact_intent.get('intent', '')}",
        f"- repository path: {config.repo_root}",
        "",
        "Safety boundaries:",
        "- Manual operator approval is required before pasting this prompt into Codex.",
        "- AresForge must not execute Codex.",
        "- Do not call GitHub APIs, gh, issues, PRs, workflows, or network services.",
        "- Do not invoke Ollama, local LLMs, documentation agents, or external agents.",
        "- Do not apply patches automatically.",
        "- Preserve local-only queue and artifact behavior.",
        "- Do not auto-start, auto-complete, or auto-dispatch queue items.",
        "- Keep execution_allowed=false in generated artifacts and final reporting.",
        "",
        "Docs to inspect:",
    ]
    lines.extend(f"- {doc}" for doc in _SOURCE_DOCS)
    lines.extend(["", "Files and modules to inspect:"])
    lines.extend(f"- {path}" for path in _DEFAULT_FILES_TO_INSPECT)
    lines.extend(["", "Implementation requirements derived from the queue item:"])
    if requirements:
        lines.extend(f"- {requirement}" for requirement in requirements)
    else:
        lines.append("- Implement the queue item conservatively with focused local changes and tests.")
    lines.extend(
        [
            "",
            "Validation commands:",
        ]
    )
    lines.extend(f"- {command.replace('<item_id>', item_id)}" for command in _VALIDATION_COMMANDS)
    lines.extend(
        [
            "",
            "Completion criteria:",
            "- Codex dispatch prompt artifact generator exists.",
            "- It consumes or derives the M97 dispatch plan.",
            "- It generates prompt artifacts only for codex_prompt_artifact lane.",
            "- It safely blocks all other lanes.",
            "- It never executes Codex.",
            "- It preserves local-only/manual-gated boundaries.",
            "- CLI command works in readable and JSON modes.",
            "- Tests pass and smoke checks pass.",
            "- Source-of-truth docs are updated.",
            "- Queue evidence is recorded only through existing local lifecycle commands.",
            "",
            "Final response format:",
            "- Files changed",
            "- What changed",
            "- Codex dispatch artifact summary",
            "- Blocked lane behavior",
            "- Operator workflow",
            "- M96/M97/M98 queue status",
            "- Tests run and results",
            "- Smoke checks run and results",
            "- Warnings or blockers",
            "- Commit hash",
        ]
    )
    return "\n".join(lines).rstrip()


def _requirements_from_item(item: dict[str, Any]) -> list[str]:
    values: list[str] = []
    description = str(item.get("description", "")).strip()
    if description:
        values.append(description)
    notes = str(item.get("notes", "")).strip()
    if notes:
        for line in notes.splitlines():
            cleaned = line.strip(" -\t")
            if cleaned:
                values.append(cleaned)
    return values


def _write_prompt(*, config: AppConfig, output: str | Path, item_id: str, prompt_text: str, force: bool) -> dict[str, Any]:
    output_path = Path(output)
    if not output_path.is_absolute():
        output_path = (config.repo_root / output_path).resolve()
    if output_path.exists() and not force:
        return {
            "ok": False,
            "output_path": str(output_path),
            "reason": "Output file already exists. Re-run with --force to overwrite.",
        }
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(prompt_text + "\n", encoding="utf-8")
    except OSError as exc:
        return {
            "ok": False,
            "output_path": str(output_path),
            "reason": f"Failed to write output file: {exc}",
        }
    return {"ok": True, "output_path": str(output_path)}


def default_codex_prompt_artifact_path(config: AppConfig, item_id: str) -> Path:
    return config.artifact_root / "codex_prompt_dispatch" / "generated" / f"{_slug(item_id)}.txt"


def _slug(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", str(value or "").lower()).strip("-")
    return normalized or "codex-dispatch-prompt"


def _preview(prompt_text: str) -> str:
    lines = prompt_text.splitlines()
    return "\n".join(lines[:20]).rstrip()


def _next_safe_action(*, generated: bool, output_path: str, item_id: str) -> str:
    if not generated:
        return "Review blocked reasons and inspect the M97 dispatch plan before generating any Codex prompt artifact."
    if output_path:
        return f"Review {output_path}, then manually copy/paste into Codex only after operator approval."
    return f"Review the generated prompt for {item_id}, then manually copy/paste into Codex only after operator approval."


def _stdout_result(command: str, payload: dict[str, Any], output_format: str, markdown: str) -> dict[str, Any]:
    fmt = str(output_format or "markdown").lower().strip()
    if fmt not in {"json", "markdown"}:
        return {
            "command": command,
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
        "wrote_output_file": bool(payload.get("output_path")),
        "stdout": json.dumps(payload, indent=2) if fmt == "json" else markdown,
        "payload": payload,
    }


def _render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Codex Dispatch Artifact Generator",
        "",
        f"- generated: {payload.get('generated')}",
        f"- blocked: {payload.get('blocked')}",
        f"- item_id: {payload.get('item_id', '')}",
        f"- selected_lane: {payload.get('selected_lane', '')}",
        f"- output_path: {payload.get('output_path', '') or '-'}",
        f"- local_only: {payload.get('local_only')}",
        f"- execution_allowed: {payload.get('execution_allowed')}",
        f"- next_safe_action: {payload.get('next_safe_action', '')}",
    ]
    blocked_reasons = payload.get("blocked_reasons", []) if isinstance(payload.get("blocked_reasons"), list) else []
    if blocked_reasons:
        lines.extend(["", "## Blocked Reasons"])
        lines.extend(f"- {reason}" for reason in blocked_reasons)
    prompt_text = str(payload.get("prompt_text", "")).strip()
    if prompt_text:
        lines.extend(["", "## Prompt Text", prompt_text])
    return "\n".join(lines).rstrip()
