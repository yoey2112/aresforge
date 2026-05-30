from __future__ import annotations

from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.local_active_project import inspect_active_project, set_active_project
from aresforge.operator.local_project_queue import (
    add_queue_item,
    init_project_queue,
    resolve_project_queue_path,
    update_local_queue_item_routing_metadata,
)
from aresforge.operator.managed_project_registry_local import (
    init_managed_project_registry,
    register_managed_project,
    register_managed_repo,
    resolve_managed_project_registry_path,
)

SELF_PROJECT_ID = "aresforge"
SELF_PROJECT_NAME = "AresForge"
SELF_PROJECT_DESCRIPTION = "Local-first, file-backed, operator-gated AI development operations workbench."
SELF_REPO_ID = "aresforge-main"
SELF_REPO_NAME = "AresForge Main Repository"

_BOUNDARY_CONFIRMATIONS: tuple[str, ...] = (
    "Local-only self-seed operation.",
    "Idempotent file-backed project, repo, and queue updates only.",
    "No GitHub API calls.",
    "No gh calls.",
    "No GitHub issues, PRs, workflows, or GitHub mutation.",
    "No external workflow execution.",
    "No automatic agent execution.",
    "No automatic Codex execution or Codex CLI invocation.",
    "No prompt dispatch.",
    "No local LLM execution.",
    "Local LLM remains local-only, advisory-only, operator-gated, prototype-scoped, and non-mutating.",
)


def seed_aresforge_self_project(
    config: AppConfig,
    *,
    project_id: str = SELF_PROJECT_ID,
    repo_id: str = SELF_REPO_ID,
    root_path: str | Path | None = None,
    queue_path: str | Path | None = None,
    registry_path: str | Path | None = None,
    set_active: bool = False,
    seed_next_milestones: bool = True,
    force_update: bool = False,
    inspect_local_git: bool = False,
) -> dict[str, Any]:
    normalized_project_id = str(project_id or "").strip() or SELF_PROJECT_ID
    normalized_repo_id = str(repo_id or "").strip() or SELF_REPO_ID
    resolved_root = Path(root_path).resolve() if root_path else config.repo_root.resolve()
    resolved_registry_path = resolve_managed_project_registry_path(config.repo_root, registry_path)
    resolved_queue_path = resolve_project_queue_path(config.repo_root, queue_path)
    warnings: list[str] = []
    created_or_updated: dict[str, Any] = {
        "registry_created": False,
        "queue_created": False,
        "project_created": False,
        "repo_created": False,
        "active_project_set": False,
        "queue_items_created": [],
        "queue_items_updated": [],
        "routing_metadata_updated": [],
    }

    if not resolved_registry_path.exists():
        initialized = init_managed_project_registry(config, path=resolved_registry_path)
        if not initialized.get("ok", False):
            return _failure(initialized, registry_path=resolved_registry_path, queue_path=resolved_queue_path)
        created_or_updated["registry_created"] = True

    project_result = register_managed_project(
        config,
        project_id=normalized_project_id,
        name=SELF_PROJECT_NAME,
        root_path=resolved_root,
        registry_path=resolved_registry_path,
        description=SELF_PROJECT_DESCRIPTION,
        status="active",
        default_branch="main",
        tags=["self-managed", "local-first", "operator-gated", "ai-operations"],
        primary_repo_id=normalized_repo_id,
        notes=(
            "Seeded by M76 self-seed workflow. Local metadata only; no GitHub API, gh, "
            "issue, PR, workflow, Codex, agent, or local LLM execution was invoked."
        ),
    )
    if not project_result.get("ok", False):
        return _failure(project_result, registry_path=resolved_registry_path, queue_path=resolved_queue_path)
    created_or_updated["project_created"] = bool(project_result.get("created", False))
    warnings.extend(project_result.get("warnings", []))

    repo_result = register_managed_repo(
        config,
        project_id=normalized_project_id,
        repo_id=normalized_repo_id,
        name=SELF_REPO_NAME,
        path=resolved_root,
        registry_path=resolved_registry_path,
        remote_url=_github_remote_url(config),
        default_branch="main",
        github_owner=config.github_owner,
        github_repo=config.github_repo,
        github_default_branch="main",
        role="primary",
        status="active",
        tags=["primary", "self-managed", "local"],
        inspect_local_git=inspect_local_git,
        notes=(
            "Primary local repo for the AresForge self-managed project. GitHub identity, "
            "when present, is local metadata discovered from local git only."
        ),
    )
    if not repo_result.get("ok", False):
        return _failure(repo_result, registry_path=resolved_registry_path, queue_path=resolved_queue_path)
    created_or_updated["repo_created"] = bool(repo_result.get("created", False))
    warnings.extend(repo_result.get("warnings", []))

    if not resolved_queue_path.exists():
        initialized_queue = init_project_queue(config, path=resolved_queue_path)
        if not initialized_queue.get("ok", False):
            return _failure(initialized_queue, registry_path=resolved_registry_path, queue_path=resolved_queue_path)
        created_or_updated["queue_created"] = True

    seeded_items: list[dict[str, Any]] = []
    if seed_next_milestones:
        for spec in _seeded_milestone_specs():
            item_result = add_queue_item(
                config,
                item_id=spec["item_id"],
                project_id=normalized_project_id,
                repo_id=normalized_repo_id,
                title=spec["title"],
                queue_path=resolved_queue_path,
                registry_path=resolved_registry_path,
                description=spec["description"],
                status="proposed",
                priority=spec["priority"],
                item_type=spec["item_type"],
                tags=spec["tags"],
                dependencies=spec["dependencies"],
                blocked_by=[],
                assigned_agent="",
                source="m76_self_seed",
                notes=_format_notes(spec["acceptance_criteria"]),
            )
            if not item_result.get("ok", False):
                return _failure(item_result, registry_path=resolved_registry_path, queue_path=resolved_queue_path)
            item = item_result.get("item", {}) if isinstance(item_result.get("item"), dict) else {}
            item_id = str(item.get("item_id", spec["item_id"])).strip()
            if bool(item_result.get("created", False)):
                created_or_updated["queue_items_created"].append(item_id)
            else:
                created_or_updated["queue_items_updated"].append(item_id)
            warnings.extend(item_result.get("warnings", []))

            routing_result = update_local_queue_item_routing_metadata(
                config,
                item_id=item_id,
                queue_path=resolved_queue_path,
                routing_metadata=spec["routing_metadata"],
            )
            if not routing_result.get("ok", False):
                return _failure(routing_result, registry_path=resolved_registry_path, queue_path=resolved_queue_path)
            created_or_updated["routing_metadata_updated"].append(item_id)
            warnings.extend(routing_result.get("warnings", []))
            routed_item = routing_result.get("item", {}) if isinstance(routing_result.get("item"), dict) else item
            seeded_items.append(_seeded_item_summary(routed_item, spec))

    active_payload = inspect_active_project(config)
    if set_active:
        active_payload = set_active_project(config, project_id=normalized_project_id)
        if not active_payload.get("ok", False):
            return _failure(active_payload, registry_path=resolved_registry_path, queue_path=resolved_queue_path)
        created_or_updated["active_project_set"] = True

    return {
        "ok": True,
        "local_only": True,
        "project_id": normalized_project_id,
        "project_name": SELF_PROJECT_NAME,
        "repo_id": normalized_repo_id,
        "repo_path": str(resolved_root),
        "registry_path": str(resolved_registry_path),
        "queue_path": str(resolved_queue_path),
        "active_project_status": {
            "set_active_requested": bool(set_active),
            "active_project_selected": bool(active_payload.get("active_project_selected", False)),
            "active_project_id": str(active_payload.get("active_project_id", "")).strip(),
            "active_repo_id": str(active_payload.get("active_repo_id", "")).strip(),
        },
        "seeded_queue_items": seeded_items,
        "created_or_updated": created_or_updated,
        "force_update": bool(force_update),
        "warnings": sorted({str(warning).strip() for warning in warnings if str(warning).strip()}),
        "next_safe_action": "Review the seeded local queue items, then continue with M77 Codex CLI Dispatch Contract.",
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }


def _seeded_milestone_specs() -> list[dict[str, Any]]:
    return [
        {
            "item_id": "m77-codex-cli-dispatch-contract",
            "title": "M77 Codex CLI Dispatch Contract",
            "item_type": "architecture",
            "priority": "high",
            "tags": ["milestone:m77", "codex-dispatch", "contract-first", "dry-run", "local-only"],
            "dependencies": [],
            "description": "Define the operator-gated Codex CLI dispatch contract, run-state model, evidence fields, dry-run/no-execute behavior, and safety boundaries before any process invocation exists.",
            "acceptance_criteria": [
                "Contract is documented and testable.",
                "Dry-run/no-execute behavior is explicit.",
                "No Codex process invocation is added.",
                "No automatic queue execution is added.",
                "No GitHub API, gh, issue, PR, workflow, or external mutation behavior is added.",
            ],
            "routing_metadata": _routing("architect_planner", "local_reasoning_llm", "high", "medium", "M76 seed: contract-first planning only; no dispatch."),
        },
        {
            "item_id": "m78-operator-gated-codex-cli-dispatch-prototype",
            "title": "M78 Operator-Gated Codex CLI Dispatch Prototype",
            "item_type": "feature",
            "priority": "high",
            "tags": ["milestone:m78", "codex-dispatch", "operator-gated", "one-item-at-a-time"],
            "dependencies": ["m77-codex-cli-dispatch-contract"],
            "description": "Prototype one explicitly operator-approved Codex CLI dispatch for one local queue item after M77 contract is complete.",
            "acceptance_criteria": [
                "Requires explicit operator approval.",
                "Allows only one queue item at a time.",
                "Does not auto-run the next item.",
                "Captures run state and available stdout/stderr/artifacts.",
                "Records error and completion states.",
                "Requires review evidence before completion.",
            ],
            "routing_metadata": _routing("high_value_codex", "codex_cli", "critical", "high", "Future operator-gated prototype after M77; no execution from M76."),
        },
        {
            "item_id": "m79-queue-blocking-and-sequencing-enforcement",
            "title": "M79 Queue Blocking and Sequencing Enforcement",
            "item_type": "feature",
            "priority": "high",
            "tags": ["milestone:m79", "queue-blocking", "sequencing", "dependencies"],
            "dependencies": ["m78-operator-gated-codex-cli-dispatch-prototype"],
            "description": "Enforce queue/dependency blocking so downstream items cannot move forward until upstream LLM/Codex work is completed, reviewed, validated, and evidenced.",
            "acceptance_criteria": [
                "Dependent items remain blocked while upstream run state is active or incomplete.",
                "Completion requires review evidence.",
                "No unattended multi-item execution is introduced.",
                "No automatic next-item execution is introduced.",
            ],
            "routing_metadata": _routing("coding", "local_coding_llm", "high", "high", "Queue lifecycle enforcement must stay operator-gated."),
        },
        {
            "item_id": "m80-llm-decision-matrix-v2",
            "title": "M80 LLM Decision Matrix v2",
            "item_type": "architecture",
            "priority": "normal",
            "tags": ["milestone:m80", "llm-routing", "decision-matrix", "model-selection"],
            "dependencies": ["m79-queue-blocking-and-sequencing-enforcement"],
            "description": "Define routing logic for Local LLM vs Codex, coding vs reasoning, model/profile selection, task sizing, risk classification, validation burden, and safety gating.",
            "acceptance_criteria": [
                "Routing remains advisory unless an approved execution gate applies.",
                "Local LLM recommendations remain local-only and non-mutating.",
                "Codex recommendations remain prompt-generation/operator-handoff unless approved dispatch exists.",
                "Task risk and validation burden are included.",
            ],
            "routing_metadata": _routing("architect_planner", "local_reasoning_llm", "high", "medium", "Decision matrix remains advisory unless future approved gates apply."),
        },
        {
            "item_id": "m81-local-llm-advisory-coding-lane-prototype",
            "title": "M81 Local LLM Advisory/Coding Lane Prototype",
            "item_type": "feature",
            "priority": "normal",
            "tags": ["milestone:m81", "local-llm", "advisory", "coding-lane", "prototype"],
            "dependencies": ["m80-llm-decision-matrix-v2"],
            "description": "Expand local LLM usage carefully, starting with local-only advisory/reasoning before any coding-output path is allowed.",
            "acceptance_criteria": [
                "Local-only provider use.",
                "Advisory/reasoning comes before coding-output behavior.",
                "No automatic repo mutation from local LLM output.",
                "Coding-output paths remain gated and prototype-scoped.",
            ],
            "routing_metadata": _routing("local_operator_assistant", "local_reasoning_llm", "medium", "medium", "Local LLM remains advisory, gated, prototype-scoped, and non-mutating."),
        },
        {
            "item_id": "m82-self-managed-aresforge-test-run",
            "title": "M82 Self-Managed AresForge Test Run",
            "item_type": "validation",
            "priority": "normal",
            "tags": ["milestone:m82", "self-managed", "validation", "dogfood"],
            "dependencies": ["m81-local-llm-advisory-coding-lane-prototype"],
            "description": "Use AresForge's own local queue and managed project metadata to test routing, handoff, dispatch readiness, local LLM decisioning, blocking, audit, artifacts, and operator review.",
            "acceptance_criteria": [
                "AresForge is inspected as its own managed project.",
                "Self-management flow remains operator-gated.",
                "Review evidence is required before marking work complete.",
                "Local validation is required before commit/push.",
                "No GitHub API, gh, issue, PR, workflow, or unattended execution is introduced.",
            ],
            "routing_metadata": _routing("reviewer_validator", "local_reasoning_llm", "high", "medium", "Dogfood validation must preserve operator gates and evidence requirements."),
        },
    ]


def _routing(lane: str, engine: str, risk: str, complexity: str, reason: str) -> dict[str, Any]:
    return {
        "recommended_agent_lane": lane,
        "recommended_engine": engine,
        "recommended_model": "",
        "fallback_engine": "",
        "fallback_model": "",
        "routing_policy_source": "m76_self_seed",
        "routing_reason": reason,
        "risk_level": risk,
        "complexity_level": complexity,
        "escalation_reason": reason if engine == "codex_cli" else "",
        "project_ai_mode": "manual_only",
        "operator_override": False,
    }


def _github_remote_url(config: AppConfig) -> str:
    owner = str(config.github_owner or "").strip()
    repo = str(config.github_repo or "").strip()
    if owner and repo:
        return f"https://github.com/{owner}/{repo}.git"
    return ""


def _format_notes(acceptance_criteria: list[str]) -> str:
    lines = [
        "Acceptance criteria:",
        *[f"- {criterion}" for criterion in acceptance_criteria],
        "",
        "M76 safety notes:",
        "- Seeded for review only.",
        "- Not started automatically.",
        "- No prompt, agent, Codex, local LLM, GitHub, gh, issue, PR, workflow, commit, or push action was invoked.",
    ]
    return "\n".join(lines).strip()


def _seeded_item_summary(item: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    return {
        "item_id": str(item.get("item_id", spec["item_id"])).strip(),
        "title": str(item.get("title", spec["title"])).strip(),
        "status": str(item.get("status", "")).strip(),
        "priority": str(item.get("priority", "")).strip(),
        "item_type": str(item.get("item_type", "")).strip(),
        "dependencies": list(item.get("dependencies", [])) if isinstance(item.get("dependencies"), list) else [],
        "tags": list(item.get("tags", [])) if isinstance(item.get("tags"), list) else [],
        "routing_metadata": item.get("routing_metadata", {}),
        "reviewable_only": str(item.get("status", "")).strip() in {"proposed", "ready"},
        "started": bool(str(item.get("started_at", "")).strip() or str(item.get("started_via", "")).strip()),
    }


def _failure(error_payload: dict[str, Any], *, registry_path: Path, queue_path: Path) -> dict[str, Any]:
    return {
        "ok": False,
        "local_only": True,
        "registry_path": str(registry_path),
        "queue_path": str(queue_path),
        "error": error_payload.get("error", "self_seed_failed"),
        "details": error_payload.get("details", error_payload),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }
