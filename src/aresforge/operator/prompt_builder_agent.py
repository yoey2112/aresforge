from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.codex_dispatch_contract import DISPATCH_ROOT_RELATIVE
from aresforge.operator.local_project_queue import (
    inspect_local_queue_item_readiness,
    resolve_project_queue_path,
)
from aresforge.operator.llm_decision_matrix import build_llm_decision_matrix

PROMPT_BUILDER_VERSION = "m80.1"
PROMPT_ARTIFACT_DIR_RELATIVE = DISPATCH_ROOT_RELATIVE / "prompts"

SOURCE_OF_TRUTH_READING = (
    "docs/context/AGENT_CONTEXT.md",
    "docs/context/BUILD_STATE.md",
    "docs/roadmap/ROADMAP.md",
    "docs/architecture/RUNNABLE_SKELETON.md",
    "docs/operator/LOCAL_OPERATOR_USAGE.md",
    "docs/architecture/CODEX_CLI_MODEL_PROFILE_CONTRACT.md",
    "src/aresforge/operator/llm_decision_matrix.py",
    "src/aresforge/operator/local_project_queue.py",
    "src/aresforge/operator/codex_dispatch_contract.py",
    "src/aresforge/operator/codex_dispatch_runner.py",
    "src/aresforge/cli.py",
    "tests/test_local_project_queue.py",
    "tests/test_codex_dispatch_contract.py",
    "tests/test_codex_dispatch_runner.py",
    "tests/test_cli.py",
)

VALIDATION_COMMANDS = (
    "python -m pytest tests/test_prompt_builder_agent.py tests/test_queue_dispatch_preparation.py tests/test_codex_dispatch_contract.py tests/test_codex_dispatch_runner.py tests/test_cli.py tests/test_local_project_queue.py tests/test_local_project_factory.py tests/test_hub_local_queue_lifecycle_api.py tests/test_hub_project_factory_api.py tests/test_hub_ui_foundation.py",
    "git diff --check",
)

SMOKE_CHECKS = (
    "python -m aresforge inspect-llm-decision-matrix --item-id m80-llm-decision-matrix-v2 --format json",
    "python -m aresforge prepare-queue-item-dispatch --item-id m79-queue-blocking-and-sequencing-enforcement --target codex --format json",
    "python -m aresforge inspect-project-queue --project-id aresforge --format json",
    "python -m aresforge inspect-local-queue-agent-summary",
    "python -m aresforge inspect-local-project-report",
)

SAFETY_BOUNDARIES = (
    "Prompt Builder output is artifact-only.",
    "Prompt Builder must not execute prompts.",
    "Prompt Builder must not call Codex.",
    "Prompt Builder must not invoke local LLMs.",
    "Prompt Builder must not mutate source files.",
    "Prompt Builder must not advance queue items automatically.",
    "No automatic prompt dispatch.",
    "No automatic queue completion.",
    "No automatic next-item execution.",
    "No GitHub API calls.",
    "No gh calls.",
    "No GitHub issues, PRs, workflows, or GitHub mutation.",
    "No external workflow execution.",
)

FINAL_RESPONSE_REQUIREMENTS = (
    "Files changed.",
    "What changed.",
    "Prompt Builder command(s) added.",
    "Workflow preparation command(s) added.",
    "Payload highlights.",
    "Validation commands and results.",
    "Smoke check results.",
    "Diff check result.",
    "Commit hash.",
    "Push result.",
    "Recommended next milestone.",
)


def build_prompt_builder_agent_contract(
    config: AppConfig,
    *,
    item_id: str,
    target: str = "codex",
    queue_path: str | Path | None = None,
    registry_path: str | Path | None = None,
    output: str | Path | None = None,
    force: bool = False,
) -> dict[str, Any]:
    normalized_item_id = str(item_id or "").strip()
    normalized_target = _normalize_target(target)
    resolved_queue_path = resolve_project_queue_path(config.repo_root, queue_path)
    loaded_item = _load_queue_item(resolved_queue_path, normalized_item_id)
    warnings: list[str] = list(loaded_item.get("warnings", []))
    blockers: list[str] = list(loaded_item.get("blockers", []))
    item = loaded_item.get("item", {}) if isinstance(loaded_item.get("item"), dict) else {}

    readiness = inspect_local_queue_item_readiness(
        config,
        item_id=normalized_item_id,
        queue_path=resolved_queue_path,
        registry_path=registry_path,
    )
    if not readiness.get("ok", False):
        blockers.extend(str(blocker) for blocker in readiness.get("blockers", []) if str(blocker).strip())
        warnings.extend(str(warning) for warning in readiness.get("warnings", []) if str(warning).strip())

    source_context = _source_context(config.repo_root, item=item, readiness=readiness)
    decision_matrix = build_llm_decision_matrix(
        config,
        item_id=normalized_item_id,
        queue_path=resolved_queue_path,
        registry_path=registry_path,
    )
    warnings.extend(str(warning) for warning in decision_matrix.get("warnings", []) if str(warning).strip())
    guidance = _target_guidance(normalized_target, item)
    prompt_text = _render_prompt_artifact(
        repo_root=config.repo_root,
        item=item,
        readiness=readiness,
        target=normalized_target,
        source_context=source_context,
        decision_matrix=decision_matrix,
        guidance=guidance,
    )

    prompt_path = _resolve_prompt_output_path(config.repo_root, normalized_item_id, output)
    write_result = _write_prompt_artifact(prompt_path, prompt_text, force=force or output is None)
    if not write_result.get("ok", False):
        blockers.append(str(write_result.get("message", "Failed to write prompt artifact.")))

    ok = bool(loaded_item.get("ok", False)) and not blockers and bool(write_result.get("ok", False))
    payload: dict[str, Any] = {
        "ok": ok,
        "local_only": True,
        "artifact_only": True,
        "item_id": normalized_item_id,
        "project_id": str(item.get("project_id", "")).strip(),
        "repo_id": str(item.get("repo_id", "")).strip(),
        "target": normalized_target,
        "target_engine": guidance["target_engine"],
        "target_lane": guidance["target_lane"],
        "prompt_builder_version": PROMPT_BUILDER_VERSION,
        "prompt_artifact_path": str(prompt_path),
        "prompt_preview": prompt_text[:2400],
        "source_context": source_context,
        "llm_decision_matrix": decision_matrix,
        "safety_boundaries": list(SAFETY_BOUNDARIES),
        "validation_plan": list(VALIDATION_COMMANDS),
        "smoke_checks": list(SMOKE_CHECKS),
        "final_response_requirements": list(FINAL_RESPONSE_REQUIREMENTS),
        "warnings": sorted({str(warning).strip() for warning in warnings if str(warning).strip()}),
        "blockers": sorted({str(blocker).strip() for blocker in blockers if str(blocker).strip()}),
        "next_safe_action": _next_safe_action(normalized_target, normalized_item_id, ok),
        "boundary_confirmations": [
            "Prompt Builder Agent is local-only.",
            "Prompt Builder Agent is artifact-only.",
            "No prompt execution was performed.",
            "No Codex, local LLM, GitHub, gh, issue, PR, workflow, or external service was invoked.",
            "M80 decision matrix output was embedded as advisory metadata only.",
            "No queue item was started, completed, or advanced by Prompt Builder.",
        ],
    }
    return payload


def _load_queue_item(queue_path: Path, item_id: str) -> dict[str, Any]:
    if not queue_path.exists():
        return {
            "ok": False,
            "item": {},
            "warnings": [f"Local queue file not found: {queue_path}"],
            "blockers": [f"Queue item not found: {item_id}"],
        }
    try:
        raw = json.loads(queue_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "ok": False,
            "item": {},
            "warnings": [],
            "blockers": [f"Local queue file could not be read: {exc}"],
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
    if item is None:
        return {"ok": False, "item": {}, "warnings": [], "blockers": [f"Queue item not found: {item_id}"]}
    return {"ok": True, "item": item, "warnings": [], "blockers": []}


def _normalize_target(target: str) -> str:
    normalized = str(target or "codex").strip().lower()
    return normalized if normalized in {"codex", "local-llm", "manual"} else "manual"


def _target_guidance(target: str, item: dict[str, Any]) -> dict[str, str]:
    routing = item.get("routing_metadata", {}) if isinstance(item.get("routing_metadata"), dict) else {}
    if target == "codex":
        return {
            "target_engine": str(routing.get("recommended_engine") or "codex_cli"),
            "target_lane": str(routing.get("recommended_agent_lane") or "high_value_codex"),
            "safety_note": "Codex dispatch still requires separate explicit operator approval through the M78 runner.",
        }
    if target == "local-llm":
        return {
            "target_engine": str(routing.get("recommended_engine") or "local_reasoning_llm"),
            "target_lane": str(routing.get("recommended_agent_lane") or "local_operator_assistant"),
            "safety_note": "Local LLM output remains advisory-only, prototype-scoped, operator-gated, and non-mutating.",
        }
    return {
        "target_engine": "manual",
        "target_lane": "local_operator_assistant",
        "safety_note": "Manual target produces an operator review artifact only.",
    }


def _source_context(repo_root: Path, *, item: dict[str, Any], readiness: dict[str, Any]) -> dict[str, Any]:
    routing = item.get("routing_metadata", {}) if isinstance(item.get("routing_metadata"), dict) else {}
    return {
        "required_reading": list(SOURCE_OF_TRUTH_READING),
        "queue_item": {
            "title": str(item.get("title", "")).strip(),
            "description": str(item.get("description", "")).strip(),
            "status": str(item.get("status", "")).strip(),
            "priority": str(item.get("priority", "")).strip(),
            "item_type": str(item.get("item_type", "")).strip(),
            "tags": item.get("tags", []) if isinstance(item.get("tags"), list) else [],
            "dependencies": item.get("dependencies", []) if isinstance(item.get("dependencies"), list) else [],
            "blocked_by": item.get("blocked_by", []) if isinstance(item.get("blocked_by"), list) else [],
            "notes": str(item.get("notes", "")).strip(),
        },
        "routing_metadata": {
            "recommended_engine": str(routing.get("recommended_engine", "")).strip(),
            "recommended_model": str(routing.get("recommended_model", "")).strip(),
            "recommended_agent_lane": str(routing.get("recommended_agent_lane", "")).strip(),
            "risk_level": str(routing.get("risk_level", "unknown")).strip(),
            "complexity_level": str(routing.get("complexity_level", "unknown")).strip(),
            "routing_reason": str(routing.get("routing_reason", "")).strip(),
        },
        "readiness_status": str(readiness.get("readiness_status", "unknown")).strip(),
        "can_start": bool(readiness.get("can_start", False)),
        "previous_milestone_evidence": {
            "latest_completed_milestones": ["M77 - Codex CLI Dispatch Contract", "M78 - Operator-Gated Codex CLI Dispatch Prototype"],
            "latest_completed_commits": _latest_local_commits(repo_root),
        },
    }


def _latest_local_commits(repo_root: Path) -> list[str]:
    try:
        completed = subprocess.run(
            ["git", "log", "-n", "4", "--oneline"],
            cwd=str(repo_root),
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    if completed.returncode != 0:
        return []
    return [line.strip() for line in completed.stdout.splitlines() if line.strip()]


def _render_prompt_artifact(
    *,
    repo_root: Path,
    item: dict[str, Any],
    readiness: dict[str, Any],
    target: str,
    source_context: dict[str, Any],
    decision_matrix: dict[str, Any],
    guidance: dict[str, str],
) -> str:
    queue_item = source_context["queue_item"]
    routing = source_context["routing_metadata"]
    decision = decision_matrix.get("routing_decision", {}) if isinstance(decision_matrix.get("routing_decision"), dict) else {}
    sizing = decision_matrix.get("task_sizing", {}) if isinstance(decision_matrix.get("task_sizing"), dict) else {}
    risk = decision_matrix.get("risk_classification", {}) if isinstance(decision_matrix.get("risk_classification"), dict) else {}
    validation = decision_matrix.get("validation_burden", {}) if isinstance(decision_matrix.get("validation_burden"), dict) else {}
    safety_gating = decision_matrix.get("safety_gating", {}) if isinstance(decision_matrix.get("safety_gating"), dict) else {}
    lines = [
        "AresForge Prompt Builder Agent Artifact",
        "",
        "Task",
        f"- Implement queue item: {queue_item['title'] or item.get('item_id', '')}",
        f"- Repository: {repo_root}",
        f"- Target: {target}",
        f"- Target engine: {guidance['target_engine']}",
        f"- Target lane: {guidance['target_lane']}",
        "",
        "Queue item",
        f"- item_id: {item.get('item_id', '')}",
        f"- project_id: {item.get('project_id', '')}",
        f"- repo_id: {item.get('repo_id', '')}",
        f"- status: {queue_item['status'] or '-'}",
        f"- priority: {queue_item['priority'] or '-'}",
        f"- type: {queue_item['item_type'] or '-'}",
        f"- tags: {', '.join(queue_item['tags']) if queue_item['tags'] else '-'}",
        f"- dependencies: {', '.join(queue_item['dependencies']) if queue_item['dependencies'] else '-'}",
        f"- blocked_by: {', '.join(queue_item['blocked_by']) if queue_item['blocked_by'] else '-'}",
        "",
        "Current status",
        f"- readiness_status: {source_context['readiness_status']}",
        f"- can_start: {str(source_context['can_start']).lower()}",
        f"- recommended_next_action: {readiness.get('recommended_next_action', '')}",
        "",
        "Latest completed milestones/commits",
    ]
    lines.extend(f"- {entry}" for entry in source_context["previous_milestone_evidence"]["latest_completed_milestones"])
    commits = source_context["previous_milestone_evidence"]["latest_completed_commits"]
    lines.extend(f"- {entry}" for entry in commits) if commits else lines.append("- Local git commit evidence was not available.")
    lines.extend(
        [
            "",
            "Project/repo binding",
            f"- project_id: {item.get('project_id', '')}",
            f"- repo_id: {item.get('repo_id', '')}",
            "",
            "Goal",
            f"- {queue_item['description'] or 'Implement the queue item with focused local changes.'}",
            "",
            "Hard boundaries",
        ]
    )
    lines.extend(f"- {entry}" for entry in SAFETY_BOUNDARIES)
    lines.extend(["", "Required source-of-truth reading"])
    lines.extend(f"- {entry}" for entry in SOURCE_OF_TRUTH_READING)
    lines.extend(
        [
            "",
            "Primary objectives",
            "- Add or update only the files needed for this queue item.",
            "- Preserve M77/M78 dispatch gates and M62 local LLM safety posture.",
            "- Keep generated prompt bodies copy/paste-safe and avoid nested markdown fences.",
            "",
            "M80 advisory decision matrix",
            f"- recommended_engine: {decision.get('recommended_engine') or guidance['target_engine']}",
            f"- recommended_lane: {decision.get('recommended_lane') or guidance['target_lane']}",
            f"- recommended_model: {decision.get('recommended_model') or '-'}",
            f"- fallback_engine: {decision.get('fallback_engine') or '-'}",
            f"- task_size: {sizing.get('task_size') or 'unknown'}",
            f"- risk_level: {risk.get('risk_level') or routing['risk_level'] or 'unknown'}",
            f"- validation_burden: {validation.get('validation_burden') or 'unknown'}",
            f"- codex_operator_approval_required: {str(bool(safety_gating.get('codex_operator_approval_required'))).lower()}",
            f"- local_llm_repo_mutation_allowed: {str(bool(safety_gating.get('local_llm_repo_mutation_allowed'))).lower()}",
            "- decision_matrix_execution_allowed: false",
            "- decision_matrix_note: Advisory only; no model or dispatch invocation is authorized by this section.",
            "",
            "Implementation guidance",
            f"- risk_level: {routing['risk_level'] or 'unknown'}",
            f"- complexity_level: {routing['complexity_level'] or 'unknown'}",
            f"- routing_reason: {routing['routing_reason'] or '-'}",
            f"- safety_note: {guidance['safety_note']}",
            "- Reuse existing local queue and dispatch helpers.",
            "- Do not create another queue or execution engine.",
            "",
            "Testing requirements",
        ]
    )
    lines.extend(f"- {command}" for command in VALIDATION_COMMANDS)
    lines.extend(["", "Smoke checks"])
    lines.extend(f"- {command}" for command in SMOKE_CHECKS)
    lines.extend(
        [
            "",
            "Diff check",
            "- git diff --check",
            "",
            "Commit/push expectations",
            "- Commit and push only after validation and diff check pass.",
            "- Queue completion still requires review and validation evidence.",
            "",
            "Final response requirements",
        ]
    )
    lines.extend(f"- {entry}" for entry in FINAL_RESPONSE_REQUIREMENTS)
    lines.extend(
        [
            "",
            "Completion evidence template",
            "- evidence_summary: <what was implemented and reviewed>",
            "- validation_results: <commands and pass/fail result>",
            "- smoke_checks: <commands and pass/fail result>",
            "- diff_check_result: <git diff --check result>",
            "- files_changed: <reviewed file list>",
            "- commit_hash: <final commit hash>",
            "- push_result: <push result>",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def _resolve_prompt_output_path(repo_root: Path, item_id: str, output: str | Path | None) -> Path:
    if output is not None:
        output_path = Path(output)
        if not output_path.is_absolute():
            output_path = repo_root / output_path
        return output_path.resolve()
    safe_item_id = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in item_id) or "unknown-item"
    return (repo_root / PROMPT_ARTIFACT_DIR_RELATIVE / f"{safe_item_id}.prompt.txt").resolve()


def _write_prompt_artifact(path: Path, content: str, *, force: bool) -> dict[str, Any]:
    if path.exists() and not force:
        return {"ok": False, "message": "Prompt artifact already exists. Re-run with --force to overwrite."}
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    except OSError as exc:
        return {"ok": False, "message": f"Failed to write prompt artifact: {exc}"}
    return {"ok": True}


def _next_safe_action(target: str, item_id: str, ok: bool) -> str:
    if not ok:
        return "Resolve blockers, then rerun prompt builder locally."
    if target == "codex":
        return (
            "Review the prompt artifact, then approve and run Codex separately with "
            f"python -m aresforge approve-codex-dispatch --item-id {item_id} --approved-by local_operator --approval-phrase \"APPROVE CODEX DISPATCH\" --format json"
        )
    return "Review the generated prompt artifact manually; do not execute or apply output automatically."


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()
