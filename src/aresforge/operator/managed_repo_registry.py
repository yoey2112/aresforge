from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.repo_bootstrap_contract import inspect_repo_bootstrap_contract
from aresforge.operator.repo_governance import inspect_repo_governance


REGISTRY_VERSION = "m3-managed-repository-registry-v1"
REGISTRY_PATH = Path("config/managed_repositories.json")


def inspect_managed_repos(config: AppConfig) -> dict[str, Any]:
    warnings: list[str] = []
    registry_entries = _load_registry_entries(config.repo_root, warnings)

    default_entry = _default_managed_repository_entry(config)
    merged_entries = _merge_registry_entries(default_entry, registry_entries)

    repositories: list[dict[str, Any]] = []
    for entry in merged_entries:
        repositories.append(_evaluate_managed_repository(config, entry))

    return {
        "command": "inspect-managed-repos",
        "ok": True,
        "inspection_mode": "read_only_registry_evaluation",
        "registry_version": REGISTRY_VERSION,
        "registry_path": str((config.repo_root / REGISTRY_PATH).resolve()),
        "managed_repository_count": len(repositories),
        "managed_repositories": repositories,
        "warnings": warnings,
        "boundary_confirmations": [
            "Read-only managed repository registry inspection only.",
            "No files, labels, milestones, issues, pull requests, branches, settings, or workflows were mutated.",
            "No background jobs, schedulers, or polling loops were used.",
        ],
    }


def _load_registry_entries(repo_root: Path, warnings: list[str]) -> list[dict[str, Any]]:
    path = repo_root / REGISTRY_PATH
    if not path.exists():
        return []

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        warnings.append(f"Managed repository registry file could not be read: {exc}")
        return []
    except json.JSONDecodeError as exc:
        warnings.append(f"Managed repository registry file is not valid JSON: {exc}")
        return []

    if not isinstance(raw, dict):
        warnings.append("Managed repository registry file must be a JSON object.")
        return []

    entries = raw.get("managed_repositories")
    if not isinstance(entries, list):
        warnings.append("Managed repository registry file is missing 'managed_repositories' list.")
        return []

    normalized: list[dict[str, Any]] = []
    for item in entries:
        if isinstance(item, dict):
            normalized.append(item)
    return normalized


def _default_managed_repository_entry(config: AppConfig) -> dict[str, Any]:
    return {
        "repository_slug": f"{config.github_owner}/{config.github_repo}",
        "local_path": str(config.repo_root),
        "default_branch": "main",
        "project_key": "project-aresforge",
        "repo_role": "platform_self_managed",
        "governance_profile": "aresforge-default",
        "documentation_roots": ["docs/"],
        "artifact_roots": [
            "artifacts/prompts/generated/",
            "artifacts/evidence/generated/",
            "artifacts/codex_handoffs/generated/",
        ],
        "allowed_automation_capabilities": [
            "read_only_inspection",
            "human_triggered_validation",
            "qa_gated_closeout",
        ],
        "disabled": False,
        "archived": False,
        "is_default": True,
    }


def _merge_registry_entries(
    default_entry: dict[str, Any],
    registry_entries: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    slug_to_entry: dict[str, dict[str, Any]] = {}

    default_slug = _normalize_slug(default_entry.get("repository_slug"))
    if default_slug is not None:
        slug_to_entry[default_slug] = dict(default_entry)

    for entry in registry_entries:
        slug = _normalize_slug(entry.get("repository_slug"))
        if slug is None:
            continue

        base = dict(slug_to_entry.get(slug, {}))
        base.update(entry)
        base["repository_slug"] = slug
        base["is_default"] = slug == default_slug
        slug_to_entry[slug] = base

    default = slug_to_entry.pop(default_slug, default_entry) if default_slug else default_entry
    others = [slug_to_entry[key] for key in sorted(slug_to_entry.keys())]
    return [default, *others]


def _normalize_slug(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    slug = value.strip().strip("/")
    if not slug or "/" not in slug:
        return None
    owner, repo = slug.split("/", 1)
    owner = owner.strip()
    repo = repo.strip()
    if not owner or not repo:
        return None
    return f"{owner}/{repo}"


def _evaluate_managed_repository(
    base_config: AppConfig,
    entry: dict[str, Any],
) -> dict[str, Any]:
    slug = _normalize_slug(entry.get("repository_slug")) or f"{base_config.github_owner}/{base_config.github_repo}"
    owner, repo = slug.split("/", 1)

    local_path = _normalize_local_path(entry.get("local_path"))
    effective_repo_root = _resolve_repo_root_for_inspection(base_config.repo_root, local_path)

    repo_config = AppConfig(
        repo_root=effective_repo_root,
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
        github_repo=repo,
    )

    governance = inspect_repo_governance(repo_config)
    bootstrap = inspect_repo_bootstrap_contract(repo_config)

    default_branch = _coerce_string(entry.get("default_branch")) or governance.get("default_branch")
    repo_warnings = _normalize_string_list(governance.get("warnings", []))
    if local_path is None:
        repo_warnings.append("Local path is not registered for this managed repository.")

    return {
        "repository_slug": slug,
        "is_default": bool(entry.get("is_default")),
        "project_key": _coerce_string(entry.get("project_key")),
        "repo_role": _coerce_string(entry.get("repo_role")),
        "local_path": local_path,
        "local_path_exists": bool(local_path and Path(local_path).exists()),
        "default_branch": default_branch,
        "governance_profile": _coerce_string(entry.get("governance_profile")) or "aresforge-default",
        "automation_status": _automation_status_from_governance(governance),
        "bootstrap_status": _bootstrap_status_from_contract(bootstrap),
        "documentation_roots": _normalize_string_list(entry.get("documentation_roots", [])),
        "artifact_roots": _normalize_string_list(entry.get("artifact_roots", [])),
        "allowed_automation_capabilities": _normalize_string_list(
            entry.get("allowed_automation_capabilities", [])
        ),
        "disabled": bool(entry.get("disabled")),
        "archived": bool(entry.get("archived")),
        "warnings": sorted(set(repo_warnings), key=str.lower),
    }


def _normalize_local_path(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    return str(Path(text).resolve())


def _resolve_repo_root_for_inspection(default_repo_root: Path, local_path: str | None) -> Path:
    if local_path is None:
        return default_repo_root
    candidate = Path(local_path)
    if candidate.exists():
        return candidate
    return default_repo_root


def _coerce_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def _normalize_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    rows = [item.strip() for item in value if isinstance(item, str) and item.strip()]
    return sorted(set(rows), key=lambda item: item.lower())


def _automation_status_from_governance(governance: dict[str, Any]) -> str:
    required = governance.get("required_platform_labels", {})
    triggers = governance.get("automation_trigger_labels", {})
    warnings = governance.get("warnings", [])
    missing_required = required.get("missing") if isinstance(required, dict) else None
    missing_trigger = triggers.get("missing") if isinstance(triggers, dict) else None
    if isinstance(missing_required, list) and missing_required:
        return "attention_needed"
    if isinstance(missing_trigger, list) and missing_trigger:
        return "attention_needed"
    if isinstance(warnings, list) and warnings:
        return "degraded"
    return "ready_read_only"


def _bootstrap_status_from_contract(contract: dict[str, Any]) -> str:
    summary = contract.get("summary", {})
    if not isinstance(summary, dict):
        return "unknown"
    required_attention = summary.get("required_attention_needed")
    unavailable = summary.get("unavailable")
    if isinstance(required_attention, int) and required_attention > 0:
        return "attention_needed"
    if isinstance(unavailable, int) and unavailable > 0:
        return "degraded"
    return "ready_read_only"
