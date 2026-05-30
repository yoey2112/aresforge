from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.codex_dispatch_contract import build_codex_dispatch_contract
from aresforge.operator.local_project_queue import (
    inspect_local_queue_item_readiness,
    start_local_queue_item,
)
from aresforge.operator.llm_decision_matrix import build_llm_decision_matrix
from aresforge.operator.prompt_builder_agent import build_prompt_builder_agent_contract

PREPARATION_VERSION = "m80.1"

_BOUNDARY_CONFIRMATIONS = (
    "Workflow preparation is local-only.",
    "Workflow preparation does not dispatch prompts.",
    "Workflow preparation does not approve Codex dispatch.",
    "Workflow preparation does not complete queue items.",
    "Workflow preparation does not run the next queue item automatically.",
    "Workflow preparation does not call Codex.",
    "Workflow preparation does not invoke local LLMs.",
    "No GitHub API calls.",
    "No gh calls.",
    "No GitHub issues, PRs, workflows, or GitHub mutation.",
    "No external workflow execution.",
)


def prepare_queue_item_dispatch(
    config: AppConfig,
    *,
    item_id: str,
    target: str = "codex",
    queue_path: str | Path | None = None,
    registry_path: str | Path | None = None,
    output: str | Path | None = None,
    start_if_ready: bool = False,
    force: bool = False,
    output_format: str = "json",
) -> dict[str, Any]:
    normalized_item_id = str(item_id or "").strip()
    normalized_target = _normalize_target(target)
    warnings: list[str] = []
    blockers: list[str] = []

    readiness = inspect_local_queue_item_readiness(
        config,
        item_id=normalized_item_id,
        queue_path=queue_path,
        registry_path=registry_path,
    )
    readiness_status = str(readiness.get("readiness_status", "unknown")).strip()
    can_start = bool(readiness.get("can_start", False))
    post_start_readiness_status = ""
    if not readiness.get("ok", False):
        blockers.extend(str(blocker) for blocker in readiness.get("blockers", []) if str(blocker).strip())
    warnings.extend(str(warning) for warning in readiness.get("warnings", []) if str(warning).strip())

    started = False
    start_result: dict[str, Any] | None = None
    if start_if_ready:
        start_result = start_local_queue_item(
            config,
            item_id=normalized_item_id,
            queue_path=queue_path,
            registry_path=registry_path,
            started_via="prepare-queue-item-dispatch",
        )
        started = bool(start_result.get("ok", False))
        if not started:
            blockers.extend(str(warning) for warning in start_result.get("warnings", []) if str(warning).strip())
        else:
            post_start_readiness = inspect_local_queue_item_readiness(
                config,
                item_id=normalized_item_id,
                queue_path=queue_path,
                registry_path=registry_path,
            )
            post_start_readiness_status = str(post_start_readiness.get("readiness_status", "unknown")).strip()

    prompt_contract = build_prompt_builder_agent_contract(
        config,
        item_id=normalized_item_id,
        target=normalized_target,
        queue_path=queue_path,
        registry_path=registry_path,
        output=output,
        force=force or output is None,
    )
    warnings.extend(str(warning) for warning in prompt_contract.get("warnings", []) if str(warning).strip())
    blockers.extend(str(blocker) for blocker in prompt_contract.get("blockers", []) if str(blocker).strip())
    decision_matrix = build_llm_decision_matrix(
        config,
        item_id=normalized_item_id,
        queue_path=queue_path,
        registry_path=registry_path,
    )
    warnings.extend(str(warning) for warning in decision_matrix.get("warnings", []) if str(warning).strip())
    blockers.extend(str(blocker) for blocker in decision_matrix.get("blockers", []) if str(blocker).strip())

    dispatch_contract_summary: dict[str, Any] = {}
    operator_approval_required = normalized_target == "codex"
    if normalized_target == "codex":
        dispatch_contract = build_codex_dispatch_contract(
            config,
            item_id=normalized_item_id,
            queue_path=queue_path,
            registry_path=registry_path,
            dry_run_prepared=True,
        )
        dispatch_contract_summary = {
            "ok": bool(dispatch_contract.get("ok", False)),
            "dry_run_only": bool(dispatch_contract.get("dry_run_only", False)),
            "dispatch_allowed": bool(dispatch_contract.get("dispatch_allowed", False)),
            "codex_cli_invocation_allowed": bool(dispatch_contract.get("codex_cli_invocation_allowed", False)),
            "operator_approval_required": bool(dispatch_contract.get("operator_approval_required", False)),
            "operator_approval_status": str(dispatch_contract.get("operator_approval_status", "")).strip(),
            "prompt_artifact_path": str(dispatch_contract.get("prompt_artifact_path", "")).strip(),
            "blockers": dispatch_contract.get("blockers", []) if isinstance(dispatch_contract.get("blockers"), list) else [],
            "warnings": dispatch_contract.get("warnings", []) if isinstance(dispatch_contract.get("warnings"), list) else [],
            "next_safe_action": str(dispatch_contract.get("next_safe_action", "")).strip(),
        }
        warnings.extend(str(warning) for warning in dispatch_contract_summary["warnings"] if str(warning).strip())
    else:
        dispatch_contract_summary = {
            "ok": True,
            "dry_run_only": True,
            "dispatch_allowed": False,
            "codex_cli_invocation_allowed": False,
            "operator_approval_required": False,
            "operator_approval_status": "not_applicable",
            "blockers": [],
            "warnings": [],
            "next_safe_action": "Review the generated prompt artifact manually; no dispatch contract is required for this target.",
        }

    dispatch_ready = bool(prompt_contract.get("ok", False)) and (
        normalized_target != "codex" or bool(dispatch_contract_summary.get("ok", False))
    )
    payload = {
        "ok": bool(prompt_contract.get("ok", False)) and not blockers,
        "local_only": True,
        "preparation_version": PREPARATION_VERSION,
        "item_id": normalized_item_id,
        "project_id": str(prompt_contract.get("project_id", "")).strip(),
        "repo_id": str(prompt_contract.get("repo_id", "")).strip(),
        "target": normalized_target,
        "readiness_status": readiness_status,
        "can_start": can_start,
        "started": started,
        "post_start_readiness_status": post_start_readiness_status,
        "start_result": start_result or {},
        "prompt_artifact_path": str(prompt_contract.get("prompt_artifact_path", "")).strip(),
        "llm_decision_matrix": decision_matrix,
        "dispatch_contract_summary": dispatch_contract_summary,
        "operator_approval_required": operator_approval_required,
        "dispatch_ready": dispatch_ready,
        "dispatch_allowed": False,
        "automatic_next_item_execution_allowed": False,
        "queue_completion_allowed": False,
        "warnings": sorted({str(warning).strip() for warning in warnings if str(warning).strip()}),
        "blockers": sorted({str(blocker).strip() for blocker in blockers if str(blocker).strip()}),
        "next_safe_action": _next_safe_action(
            item_id=normalized_item_id,
            target=normalized_target,
            dispatch_ready=dispatch_ready,
            prompt_path=str(prompt_contract.get("prompt_artifact_path", "")).strip(),
        ),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }
    return _stdout_result("prepare-queue-item-dispatch", payload, output_format)


def _normalize_target(target: str) -> str:
    normalized = str(target or "codex").strip().lower()
    return normalized if normalized in {"codex", "local-llm", "manual"} else "manual"


def _next_safe_action(*, item_id: str, target: str, dispatch_ready: bool, prompt_path: str) -> str:
    if not dispatch_ready:
        return "Resolve preparation blockers, then rerun prepare-queue-item-dispatch."
    if target == "codex":
        return (
            f"Review prompt artifact {prompt_path}, then explicitly approve dispatch with "
            f"python -m aresforge approve-codex-dispatch --item-id {item_id} --approved-by local_operator --approval-phrase \"APPROVE CODEX DISPATCH\" --format json"
        )
    return f"Review prompt artifact {prompt_path}; execute any follow-up manually outside this preparation command."


def _stdout_result(command: str, payload: dict[str, Any], output_format: str) -> dict[str, Any]:
    fmt = str(output_format or "json").lower().strip()
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
        "wrote_output_file": False,
        "stdout": json.dumps(payload, indent=2) if fmt == "json" else _render_markdown(payload),
        "payload": payload,
    }


def _render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Queue Dispatch Preparation",
        "",
        f"- ok: {payload.get('ok')}",
        f"- item_id: {payload.get('item_id', '')}",
        f"- target: {payload.get('target', '')}",
        f"- readiness_status: {payload.get('readiness_status', '')}",
        f"- started: {payload.get('started')}",
        f"- dispatch_allowed: {payload.get('dispatch_allowed')}",
        f"- prompt_artifact_path: {payload.get('prompt_artifact_path', '')}",
        f"- next_safe_action: {payload.get('next_safe_action', '')}",
        "",
        "## Boundaries",
    ]
    lines.extend(f"- {entry}" for entry in payload.get("boundary_confirmations", []))
    blockers = payload.get("blockers", []) if isinstance(payload.get("blockers"), list) else []
    if blockers:
        lines.extend(["", "## Blockers"])
        lines.extend(f"- {entry}" for entry in blockers)
    return "\n".join(lines)
