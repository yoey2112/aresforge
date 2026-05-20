from __future__ import annotations

from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.managed_repo_registry import inspect_managed_repos
from aresforge.operator.repo_bootstrap_contract import inspect_repo_bootstrap_contract
from aresforge.operator.repo_governance import inspect_repo_governance


PLAN_VERSION = "m3-repository-bootstrap-plan-v1"


def plan_repo_bootstrap(config: AppConfig) -> dict[str, Any]:
    registry = inspect_managed_repos(config)
    registry_warnings = _normalize_list(registry.get("warnings"))

    plan_rows: list[dict[str, Any]] = []
    for repo in registry.get("managed_repositories", []) if isinstance(registry.get("managed_repositories"), list) else []:
        if not isinstance(repo, dict):
            continue
        plan_rows.append(_plan_for_repository(config, repo))

    return {
        "command": "plan-repo-bootstrap",
        "ok": True,
        "inspection_mode": "read_only_bootstrap_plan",
        "plan_version": PLAN_VERSION,
        "plan_only": True,
        "setup_performed": False,
        "repository_count": len(plan_rows),
        "repositories": plan_rows,
        "warnings": registry_warnings,
        "recommended_next_action": _global_next_action(plan_rows, registry_warnings),
        "boundary_confirmations": [
            "Read-only bootstrap planning only.",
            "No labels, milestones, issues, pull requests, branches, settings, workflows, artifacts, files, or git state were mutated.",
            "No setup was performed; this command produces human-reviewable plan output only.",
            "No background jobs, schedulers, daemons, or polling loops were used.",
        ],
    }


def _plan_for_repository(base_config: AppConfig, repo_entry: dict[str, Any]) -> dict[str, Any]:
    slug = _coerce(repo_entry.get("repository_slug")) or f"{base_config.github_owner}/{base_config.github_repo}"
    owner, name = _owner_repo(slug, base_config)

    local_path = _coerce(repo_entry.get("local_path"))
    local_exists = bool(local_path and Path(local_path).exists())
    effective_root = Path(local_path) if local_exists and local_path else base_config.repo_root

    config = AppConfig(
        repo_root=effective_root,
        db_host=base_config.db_host,
        db_port=base_config.db_port,
        db_name=base_config.db_name,
        db_user=base_config.db_user,
        db_password=base_config.db_password,
        ollama_base_url=base_config.ollama_base_url,
        ollama_model=base_config.ollama_model,
        artifact_root=base_config.artifact_root,
        prompts_dir=base_config.prompts_dir,
        evidence_dir=base_config.evidence_dir,
        codex_handoffs_dir=base_config.codex_handoffs_dir,
        github_owner=owner,
        github_repo=name,
    )

    governance = inspect_repo_governance(config)
    bootstrap = inspect_repo_bootstrap_contract(config)

    required_labels = _safe_dict(governance.get("required_platform_labels"))
    optional_labels = _safe_dict(governance.get("optional_platform_labels"))
    trigger_labels = _safe_dict(governance.get("automation_trigger_labels"))
    milestone_status = _safe_dict(governance.get("milestone_naming_status"))

    actions = []
    actions.extend(_required_label_actions(slug, required_labels))
    actions.extend(_trigger_label_actions(slug, trigger_labels))
    actions.extend(_optional_label_actions(slug, optional_labels))
    actions.extend(_milestone_actions(slug, milestone_status))
    actions.extend(_contract_area_actions(slug, bootstrap))
    actions.extend(_registry_alignment_actions(slug, repo_entry, local_exists))

    actions = sorted(actions, key=lambda row: (row["priority_order"], row["title"].lower()))

    warning_rows = _normalize_list(repo_entry.get("warnings"))
    warning_rows.extend(_normalize_list(governance.get("warnings")))
    if local_path is None:
        warning_rows.append("Local path is not registered for this managed repository.")
    elif not local_exists:
        warning_rows.append("Local path is registered but not available on disk.")
    warning_rows = sorted(set(warning_rows), key=str.lower)

    return {
        "repository_slug": slug,
        "is_default": bool(repo_entry.get("is_default")),
        "project_key": _coerce(repo_entry.get("project_key")),
        "repo_role": _coerce(repo_entry.get("repo_role")),
        "plan_only": True,
        "setup_performed": False,
        "default_branch": governance.get("default_branch") or repo_entry.get("default_branch"),
        "local_path": local_path,
        "local_path_exists": local_exists,
        "warnings": warning_rows,
        "actions": actions,
        "recommended_next_action": _repo_next_action(actions, warning_rows),
        "future_setup_command_placeholders": [
            {
                "name": "create-label-placeholder",
                "command": f"gh label create <label-name> --repo {slug} --color <hex> --description \"<description>\"",
                "execute_now": False,
            },
            {
                "name": "create-milestone-placeholder",
                "command": f"gh api repos/{slug}/milestones -f title='M3 - Registry And Routing Deepening'",
                "execute_now": False,
            },
            {
                "name": "document-mapping-placeholder",
                "command": "Update roadmap/governance docs with project-specific milestone mapping notes and rerun plan-repo-bootstrap.",
                "execute_now": False,
            },
        ],
        "boundary_confirmations": [
            "This plan does not create labels.",
            "This plan does not create milestones.",
            "This plan does not modify GitHub state.",
            "Any setup must be manually triggered and human-reviewed.",
        ],
    }


def _required_label_actions(slug: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
    if payload.get("available") is not True:
        return [
            _action(
                category="required",
                title="Confirm required labels",
                summary="Required label posture is unavailable; confirm manually before setup.",
                detail=f"Run inspect-repo-governance for {slug} after restoring gh/network access.",
                priority_order=0,
            )
        ]
    missing = _normalize_list(payload.get("missing"))
    return [
        _action(
            category="required",
            title=f"Create required label {label}",
            summary="Required governance label is missing.",
            detail=f"Add '{label}' in {slug} via human-triggered setup, then rerun plan.",
            priority_order=0,
        )
        for label in missing
    ]


def _trigger_label_actions(slug: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
    if payload.get("available") is not True:
        return [
            _action(
                category="required",
                title="Confirm automation trigger labels",
                summary="Automation-trigger label posture is unavailable.",
                detail=f"Inspect trigger labels for {slug} when GitHub read access is available.",
                priority_order=0,
            )
        ]
    missing = _normalize_list(payload.get("missing"))
    return [
        _action(
            category="required",
            title=f"Create automation trigger label {label}",
            summary="Automation-trigger label is missing.",
            detail=f"Add '{label}' in {slug}; this remains an intent marker and not autonomous permission.",
            priority_order=0,
        )
        for label in missing
    ]


def _optional_label_actions(slug: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
    if payload.get("available") is not True:
        return [
            _action(
                category="optional",
                title="Review optional labels",
                summary="Optional platform-known label posture is unavailable.",
                detail=f"Inspect optional labels for {slug} after restoring read access.",
                priority_order=2,
            )
        ]
    missing = _normalize_list(payload.get("missing"))
    return [
        _action(
            category="optional",
            title=f"Consider optional label {label}",
            summary="Optional platform-known label is missing.",
            detail=f"Optionally add '{label}' to improve cross-repository consistency.",
            priority_order=2,
        )
        for label in missing
    ]


def _milestone_actions(slug: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    if payload.get("available") is not True:
        actions.append(
            _action(
                category="required",
                title="Confirm canonical platform milestones",
                summary="Milestone naming posture is unavailable.",
                detail=f"Inspect milestone naming for {slug} after restoring gh/network access.",
                priority_order=0,
            )
        )
        return actions

    for milestone in _normalize_list(payload.get("missing_platform_milestones")):
        actions.append(
            _action(
                category="required",
                title=f"Create canonical milestone {milestone}",
                summary="Canonical platform milestone is missing.",
                detail="Create the missing milestone name exactly and rerun the bootstrap plan.",
                priority_order=0,
            )
        )

    for milestone in _normalize_list(payload.get("unknown_platform_like_milestones")):
        actions.append(
            _action(
                category="recommended",
                title=f"Align platform-like milestone {milestone}",
                summary="Platform-like milestone name does not match canonical naming.",
                detail="Align naming to canonical platform milestone contract for deterministic inspection.",
                priority_order=1,
            )
        )

    project_specific = _normalize_list(payload.get("project_specific_milestones"))
    if project_specific:
        actions.append(
            _action(
                category="recommended",
                title="Document project-specific milestone mapping",
                summary="Project-specific milestones should map to canonical platform phases.",
                detail=f"Map milestones to platform phases: {', '.join(project_specific)}.",
                priority_order=1,
            )
        )

    return actions


def _contract_area_actions(slug: str, contract: dict[str, Any]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for area in contract.get("area_evaluation", []) if isinstance(contract.get("area_evaluation"), list) else []:
        if not isinstance(area, dict):
            continue
        area_name = _coerce(area.get("area"))
        status = _coerce(area.get("status"))
        level = _coerce(area.get("requirement_level"))
        summary = _coerce(area.get("summary")) or "Contract area requires review."
        if area_name is None or status is None or level is None:
            continue

        category = level if level in {"required", "recommended", "optional", "deferred"} else "recommended"
        priority = 0 if category == "required" else 1 if category == "recommended" else 2 if category == "optional" else 3

        if status == "attention_needed":
            actions.append(
                _action(
                    category=category,
                    title=f"Address {area_name.replace('_', ' ')}",
                    summary=summary,
                    detail=f"Review {area_name} for {slug} and prepare human-triggered setup steps.",
                    priority_order=priority,
                )
            )
        elif status == "advisory":
            actions.append(
                _action(
                    category="recommended" if category == "required" else category,
                    title=f"Review {area_name.replace('_', ' ')}",
                    summary=summary,
                    detail=f"Capture explicit decision for {area_name} during bootstrap review.",
                    priority_order=max(priority, 1),
                )
            )
        elif status == "unavailable":
            actions.append(
                _action(
                    category=category,
                    title=f"Collect missing data for {area_name.replace('_', ' ')}",
                    summary="Required inspection data is unavailable.",
                    detail="Restore dependencies (gh/network/local paths) and rerun plan before setup.",
                    priority_order=priority,
                )
            )
        elif status == "deferred":
            actions.append(
                _action(
                    category="deferred",
                    title=f"Track deferred area {area_name.replace('_', ' ')}",
                    summary=summary,
                    detail="Leave deferred until dedicated follow-up issue is selected.",
                    priority_order=3,
                )
            )
    return actions


def _registry_alignment_actions(slug: str, repo_entry: dict[str, Any], local_exists: bool) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    if _coerce(repo_entry.get("project_key")) is None:
        actions.append(
            _action(
                category="recommended",
                title="Set project key in managed repository registry",
                summary="Managed repository record is missing project_key.",
                detail=f"Add project_key for {slug} in managed registry for clearer ownership mapping.",
                priority_order=1,
            )
        )
    if _coerce(repo_entry.get("governance_profile")) is None:
        actions.append(
            _action(
                category="recommended",
                title="Set governance profile in managed repository registry",
                summary="Managed repository record is missing governance_profile.",
                detail="Add explicit governance profile to avoid ambiguous contract selection.",
                priority_order=1,
            )
        )
    if not local_exists:
        actions.append(
            _action(
                category="recommended",
                title="Confirm local path alignment",
                summary="Managed repository local path is missing or unavailable.",
                detail="Register a valid local path before relying on local git posture in readiness planning.",
                priority_order=1,
            )
        )
    if bool(repo_entry.get("disabled")):
        actions.append(
            _action(
                category="deferred",
                title="Repository is disabled",
                summary="Repository is disabled in registry and excluded from active setup.",
                detail="Re-enable intentionally when governance setup is ready for manual execution.",
                priority_order=3,
            )
        )
    if bool(repo_entry.get("archived")):
        actions.append(
            _action(
                category="deferred",
                title="Repository is archived",
                summary="Repository is archived in registry and excluded from active setup.",
                detail="Keep archived unless explicit human decision reactivates repository management.",
                priority_order=3,
            )
        )
    return actions


def _repo_next_action(actions: list[dict[str, Any]], warnings: list[str]) -> str:
    required_attention = [a for a in actions if a.get("category") == "required"]
    if required_attention:
        return "Review required actions first, then run human-triggered setup commands manually and rerun plan-repo-bootstrap."
    recommended = [a for a in actions if a.get("category") == "recommended"]
    if recommended:
        return "Review recommended actions, confirm project-specific mappings, then rerun plan-repo-bootstrap."
    if warnings:
        return "Resolve warnings and rerun plan-repo-bootstrap for a complete planning snapshot."
    return "Bootstrap posture appears aligned for read-only governance; keep setup human-triggered when needed."


def _global_next_action(plan_rows: list[dict[str, Any]], warnings: list[str]) -> str:
    has_required = any(
        isinstance(repo.get("actions"), list)
        and any(isinstance(action, dict) and action.get("category") == "required" for action in repo["actions"])
        for repo in plan_rows
        if isinstance(repo, dict)
    )
    if has_required:
        return "Prioritize required bootstrap actions, perform setup manually, and rerun plan-repo-bootstrap for verification."
    if warnings:
        return "Resolve registry/environment warnings and rerun plan-repo-bootstrap for complete coverage."
    return "Plan shows no required bootstrap gaps; review recommended and optional actions before future setup commands."


def _action(*, category: str, title: str, summary: str, detail: str, priority_order: int) -> dict[str, Any]:
    return {
        "category": category,
        "title": title,
        "summary": summary,
        "detail": detail,
        "priority_order": priority_order,
    }


def _owner_repo(slug: str, config: AppConfig) -> tuple[str, str]:
    if "/" not in slug:
        return config.github_owner, config.github_repo
    owner, repo = slug.split("/", 1)
    owner = owner.strip() or config.github_owner
    repo = repo.strip() or config.github_repo
    return owner, repo


def _normalize_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    rows = [str(item).strip() for item in value if str(item).strip()]
    return sorted(set(rows), key=str.lower)


def _coerce(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}
