from __future__ import annotations

from pathlib import Path
import subprocess
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.managed_repo_registry import inspect_managed_repos
from aresforge.operator.repo_bootstrap_contract import inspect_repo_bootstrap_contract
from aresforge.operator.repo_governance import inspect_repo_governance


def managed_repo_readiness_report(config: AppConfig) -> dict[str, Any]:
    registry = inspect_managed_repos(config)
    repos = registry.get("managed_repositories", [])
    global_warnings = _normalize_list(registry.get("warnings"))

    readiness_rows: list[dict[str, Any]] = []
    for repo in repos if isinstance(repos, list) else []:
        if not isinstance(repo, dict):
            continue
        readiness_rows.append(_evaluate_repo(config, repo))

    return {
        "command": "managed-repo-readiness-report",
        "ok": True,
        "inspection_mode": "read_only_managed_repository_readiness",
        "repository_count": len(readiness_rows),
        "repositories": readiness_rows,
        "warnings": sorted(set(global_warnings), key=str.lower),
        "boundary_confirmations": [
            "Read-only readiness reporting only.",
            "No files, labels, milestones, issues, pull requests, branches, settings, workflows, or artifacts were mutated.",
            "No background jobs, schedulers, or polling loops were used.",
            "Retired historical validation evidence remained protected and was not modified.",
        ],
    }


def _evaluate_repo(base_config: AppConfig, repo: dict[str, Any]) -> dict[str, Any]:
    slug = str(repo.get("repository_slug") or f"{base_config.github_owner}/{base_config.github_repo}")
    owner, name = _owner_repo(slug, base_config)
    local_path = _coerce(repo.get("local_path"))
    local_exists = bool(local_path and Path(local_path).exists())
    effective_root = Path(local_path) if local_exists and local_path else base_config.repo_root

    per_repo_config = AppConfig(
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

    governance = inspect_repo_governance(per_repo_config)
    bootstrap = inspect_repo_bootstrap_contract(per_repo_config)
    current_branch, working_tree_clean, git_warning = _local_git_state(local_path, local_exists)

    required_labels = governance.get("required_platform_labels", {})
    optional_labels = governance.get("optional_platform_labels", {})
    trigger_labels = governance.get("automation_trigger_labels", {})
    milestone_status = governance.get("milestone_naming_status", {})
    issue_signal = governance.get("open_issue_readiness_signal", {})
    pr_signal = governance.get("open_pr_readiness_signal", {})

    bootstrap_summary = bootstrap.get("summary", {})
    bootstrap_status = _bootstrap_status(bootstrap_summary)
    governance_status = _governance_status(required_labels, trigger_labels, governance.get("warnings"))
    docs_status = _docs_status(bootstrap)
    disabled = bool(repo.get("disabled"))
    archived = bool(repo.get("archived"))

    warnings = _normalize_list(repo.get("warnings"))
    warnings.extend(_normalize_list(governance.get("warnings")))
    if git_warning:
        warnings.append(git_warning)
    if local_path is None:
        warnings.append("Local path not registered.")
    elif not local_exists:
        warnings.append("Local path is registered but not available on disk.")
    warnings = sorted(set(warnings), key=str.lower)

    readiness_level = _readiness_level(
        disabled=disabled,
        archived=archived,
        governance_status=governance_status,
        bootstrap_status=bootstrap_status,
        warnings=warnings,
    )

    return {
        "repository_slug": slug,
        "is_default": bool(repo.get("is_default")),
        "project_key": _coerce(repo.get("project_key")),
        "repo_role": _coerce(repo.get("repo_role")),
        "readiness_level": readiness_level,
        "local_path": local_path,
        "local_path_exists": local_exists,
        "current_branch": current_branch,
        "default_branch": governance.get("default_branch") or repo.get("default_branch"),
        "working_tree_clean": working_tree_clean,
        "governance_profile": _coerce(repo.get("governance_profile")) or "aresforge-default",
        "governance_profile_status": governance_status,
        "bootstrap_contract_status": bootstrap_status,
        "required_labels": required_labels,
        "optional_labels": optional_labels,
        "automation_trigger_labels": trigger_labels,
        "milestone_status": milestone_status,
        "documentation_baseline_status": docs_status,
        "open_issue_readiness_signal": issue_signal,
        "open_pr_readiness_signal": pr_signal,
        "evidence_artifact_expectations": {
            "validation_evidence_area": _area_status(bootstrap, "validation_evidence_expectations"),
            "generated_artifact_area": _area_status(bootstrap, "generated_artifact_conventions"),
        },
        "allowed_automation_capabilities": _normalize_list(repo.get("allowed_automation_capabilities")),
        "warnings": warnings,
        "recommended_next_action": _next_action(
            readiness_level=readiness_level,
            trigger_labels=trigger_labels,
            milestone_status=milestone_status,
            warnings=warnings,
        ),
        "boundary_confirmations": [
            "Read-only managed repository readiness inspection only.",
            "No GitHub, git, or file mutation was performed.",
            "Any setup or correction remains human-triggered.",
        ],
    }


def _owner_repo(slug: str, config: AppConfig) -> tuple[str, str]:
    if "/" not in slug:
        return config.github_owner, config.github_repo
    owner, repo = slug.split("/", 1)
    owner = owner.strip() or config.github_owner
    repo = repo.strip() or config.github_repo
    return owner, repo


def _run(args: list[str], cwd: Path) -> tuple[bool, int | None, str, str]:
    try:
        result = subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        return False, None, "", "command_not_found"
    except OSError as exc:
        return False, None, "", str(exc)
    return True, result.returncode, result.stdout, result.stderr


def _local_git_state(local_path: str | None, local_exists: bool) -> tuple[str | None, bool | None, str | None]:
    if not local_path or not local_exists:
        return None, None, None
    root = Path(local_path)
    available, code, out, err = _run(["git", "branch", "--show-current"], root)
    if not available:
        return None, None, "git command unavailable for local branch inspection."
    branch = out.strip() if code == 0 and out.strip() else None
    if code != 0:
        return None, None, f"local git branch inspection failed: {(err or 'unknown_error').strip()}"
    s_ok, s_code, s_out, s_err = _run(["git", "status", "--porcelain"], root)
    if not s_ok:
        return branch, None, "git command unavailable for working tree inspection."
    if s_code != 0:
        return branch, None, f"local git status inspection failed: {(s_err or 'unknown_error').strip()}"
    return branch, s_out.strip() == "", None


def _governance_status(
    required: Any,
    triggers: Any,
    warnings: Any,
) -> str:
    req_missing = required.get("missing") if isinstance(required, dict) else None
    trig_missing = triggers.get("missing") if isinstance(triggers, dict) else None
    req_avail = required.get("available") if isinstance(required, dict) else None
    trig_avail = triggers.get("available") if isinstance(triggers, dict) else None
    if req_avail is False or trig_avail is False:
        return "unavailable"
    if isinstance(req_missing, list) and req_missing:
        return "attention_needed"
    if isinstance(trig_missing, list) and trig_missing:
        return "attention_needed"
    if isinstance(warnings, list) and warnings:
        return "degraded"
    return "ready"


def _bootstrap_status(summary: Any) -> str:
    if not isinstance(summary, dict):
        return "unavailable"
    required_attention = summary.get("required_attention_needed")
    unavailable = summary.get("unavailable")
    if isinstance(required_attention, int) and required_attention > 0:
        return "attention_needed"
    if isinstance(unavailable, int) and unavailable > 0:
        return "degraded"
    return "ready"


def _docs_status(bootstrap: dict[str, Any]) -> dict[str, Any]:
    return {
        "documentation_expectations": _area_status(bootstrap, "documentation_expectations"),
        "generated_artifact_conventions": _area_status(bootstrap, "generated_artifact_conventions"),
        "governance_profile_expectations": _area_status(bootstrap, "governance_profile_expectations"),
    }


def _area_status(bootstrap: dict[str, Any], area: str) -> dict[str, Any]:
    rows = bootstrap.get("area_evaluation", [])
    if not isinstance(rows, list):
        return {"status": "unavailable", "available": False}
    for row in rows:
        if isinstance(row, dict) and row.get("area") == area:
            return {
                "status": row.get("status"),
                "available": bool(row.get("available")),
                "summary": row.get("summary"),
                "details": row.get("details", {}),
            }
    return {"status": "unavailable", "available": False}


def _readiness_level(
    *,
    disabled: bool,
    archived: bool,
    governance_status: str,
    bootstrap_status: str,
    warnings: list[str],
) -> str:
    if archived:
        return "archived"
    if disabled:
        return "disabled"
    if governance_status == "unavailable":
        return "unavailable"
    if governance_status == "attention_needed" or bootstrap_status == "attention_needed":
        return "attention_needed"
    if governance_status == "degraded" or bootstrap_status == "degraded" or warnings:
        return "degraded"
    return "ready"


def _next_action(
    *,
    readiness_level: str,
    trigger_labels: Any,
    milestone_status: Any,
    warnings: list[str],
) -> str:
    if readiness_level == "archived":
        return "Repository is archived; keep excluded from active automation planning."
    if readiness_level == "disabled":
        return "Repository is disabled; keep excluded until manually re-enabled."
    missing_triggers = trigger_labels.get("missing") if isinstance(trigger_labels, dict) else None
    if isinstance(missing_triggers, list) and missing_triggers:
        return "Add missing automation-trigger labels and rerun managed-repo-readiness-report."
    missing_milestones = (
        milestone_status.get("missing_platform_milestones")
        if isinstance(milestone_status, dict)
        else None
    )
    if isinstance(missing_milestones, list) and missing_milestones:
        return "Align platform milestone naming and rerun managed-repo-readiness-report."
    if warnings:
        return "Resolve warnings (local path, gh/network, or git availability) and rerun managed-repo-readiness-report."
    if readiness_level == "ready":
        return "Repository is ready for safe read-only automation inspection flows."
    return "Review readiness output and resolve attention-needed governance/bootstrap gaps."


def _normalize_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return sorted({str(item).strip() for item in value if str(item).strip()}, key=str.lower)


def _coerce(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None
