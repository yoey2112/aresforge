from __future__ import annotations

from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.repo_governance import inspect_repo_governance


CONTRACT_VERSION = "m3-managed-repository-bootstrap-v1"


def inspect_repo_bootstrap_contract(config: AppConfig) -> dict[str, Any]:
    governance = inspect_repo_governance(config)
    warnings = list(governance.get("warnings", []))

    required = [
        "default_branch_expectations",
        "required_labels",
        "automation_trigger_labels",
        "platform_milestone_naming",
        "validation_evidence_expectations",
        "closeout_expectations",
        "documentation_expectations",
        "generated_artifact_conventions",
        "automation_boundary_confirmations",
        "protected_historical_evidence_handling",
        "local_path_and_repo_slug_expectations",
        "governance_profile_expectations",
    ]
    recommended = [
        "optional_platform_known_labels",
        "project_specific_milestone_mapping",
        "issue_templates_or_issue_conventions",
        "pr_linking_conventions",
    ]
    optional = []
    deferred = [
        "future_multi_repo_governance_alignment",
    ]

    area_evaluation = [
        _evaluate_default_branch(governance),
        _evaluate_required_labels(governance),
        _evaluate_optional_labels(governance),
        _evaluate_automation_trigger_labels(governance),
        _evaluate_platform_milestones(governance),
        _evaluate_project_milestone_mapping(governance),
        _evaluate_issue_templates_or_conventions(config.repo_root),
        _evaluate_pr_linking_conventions(),
        _evaluate_validation_evidence_expectations(config.repo_root),
        _evaluate_closeout_expectations(config.repo_root),
        _evaluate_documentation_expectations(config.repo_root),
        _evaluate_generated_artifact_conventions(config.repo_root),
        _evaluate_automation_boundaries(governance),
        _evaluate_protected_historical_evidence(governance),
        _evaluate_local_path_and_slug(config, governance),
        _evaluate_governance_profile(config.repo_root),
        _evaluate_multi_repo_deferred(),
    ]

    summary = _summarize(area_evaluation)
    if summary["attention_needed"] > 0:
        next_action = (
            "Address attention-needed required bootstrap areas first, then rerun "
            "inspect-repo-bootstrap-contract before enabling broader managed-repository automation."
        )
    elif warnings:
        next_action = (
            "Resolve environment warnings (for example GitHub CLI/network availability) and rerun "
            "inspect-repo-bootstrap-contract for a complete managed repository snapshot."
        )
    else:
        next_action = (
            "Bootstrap contract posture is acceptable for read-only planning; keep setup human-triggered "
            "and preserve explicit mutation gates."
        )

    return {
        "command": "inspect-repo-bootstrap-contract",
        "ok": True,
        "inspection_mode": "read_only_contract_evaluation",
        "contract_version": CONTRACT_VERSION,
        "repository_slug": governance.get("repository_slug")
        or f"{config.github_owner}/{config.github_repo}",
        "local_path": str(config.repo_root),
        "default_branch": governance.get("default_branch"),
        "bootstrap_contract": {
            "required": required,
            "recommended": recommended,
            "optional": optional,
            "deferred": deferred,
        },
        "area_evaluation": area_evaluation,
        "summary": summary,
        "warnings": warnings,
        "recommended_next_action": next_action,
        "boundary_confirmations": [
            "Read-only bootstrap contract inspection only.",
            "No labels, milestones, issues, pull requests, branches, settings, workflows, or files were mutated.",
            "No background jobs, schedulers, or polling loops were used.",
            "Bootstrap setup remains human-triggered; this command does not perform setup mutation.",
        ],
    }


def _status_payload(
    *,
    area: str,
    requirement_level: str,
    status: str,
    summary: str,
    available: bool,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "area": area,
        "requirement_level": requirement_level,
        "status": status,
        "summary": summary,
        "available": available,
        "details": details or {},
    }


def _evaluate_default_branch(governance: dict[str, Any]) -> dict[str, Any]:
    branch = governance.get("default_branch")
    if not isinstance(branch, str) or not branch.strip():
        return _status_payload(
            area="default_branch_expectations",
            requirement_level="required",
            status="attention_needed",
            summary="Default branch could not be confirmed from read-only inspection.",
            available=False,
        )
    return _status_payload(
        area="default_branch_expectations",
        requirement_level="required",
        status="satisfied",
        summary=f"Default branch is visible as '{branch}'.",
        available=True,
        details={"default_branch": branch, "platform_expected_default": "main"},
    )


def _evaluate_required_labels(governance: dict[str, Any]) -> dict[str, Any]:
    payload = governance.get("required_platform_labels")
    if not isinstance(payload, dict) or payload.get("available") is not True:
        return _status_payload(
            area="required_labels",
            requirement_level="required",
            status="unavailable",
            summary="Required label posture is unavailable because label inspection data is not available.",
            available=False,
        )
    missing = payload.get("missing", [])
    if isinstance(missing, list) and missing:
        return _status_payload(
            area="required_labels",
            requirement_level="required",
            status="attention_needed",
            summary="One or more required platform labels are missing.",
            available=True,
            details={"missing": missing},
        )
    return _status_payload(
        area="required_labels",
        requirement_level="required",
        status="satisfied",
        summary="Required platform labels are present.",
        available=True,
    )


def _evaluate_optional_labels(governance: dict[str, Any]) -> dict[str, Any]:
    payload = governance.get("optional_platform_labels")
    if not isinstance(payload, dict) or payload.get("available") is not True:
        return _status_payload(
            area="optional_platform_known_labels",
            requirement_level="recommended",
            status="unavailable",
            summary="Optional platform label visibility is unavailable.",
            available=False,
        )
    missing = payload.get("missing", [])
    if isinstance(missing, list) and missing:
        return _status_payload(
            area="optional_platform_known_labels",
            requirement_level="recommended",
            status="advisory",
            summary="Some optional platform-known labels are not present yet.",
            available=True,
            details={"missing": missing},
        )
    return _status_payload(
        area="optional_platform_known_labels",
        requirement_level="recommended",
        status="satisfied",
        summary="All known optional platform labels are present.",
        available=True,
    )


def _evaluate_automation_trigger_labels(governance: dict[str, Any]) -> dict[str, Any]:
    payload = governance.get("automation_trigger_labels")
    if not isinstance(payload, dict) or payload.get("available") is not True:
        return _status_payload(
            area="automation_trigger_labels",
            requirement_level="required",
            status="unavailable",
            summary="Automation-trigger label posture is unavailable.",
            available=False,
        )
    missing = payload.get("missing", [])
    if isinstance(missing, list) and missing:
        return _status_payload(
            area="automation_trigger_labels",
            requirement_level="required",
            status="attention_needed",
            summary="One or more automation-trigger labels are missing.",
            available=True,
            details={"missing": missing},
        )
    return _status_payload(
        area="automation_trigger_labels",
        requirement_level="required",
        status="satisfied",
        summary="Automation-trigger labels are present.",
        available=True,
    )


def _evaluate_platform_milestones(governance: dict[str, Any]) -> dict[str, Any]:
    payload = governance.get("milestone_naming_status")
    if not isinstance(payload, dict) or payload.get("available") is not True:
        return _status_payload(
            area="platform_milestone_naming",
            requirement_level="required",
            status="unavailable",
            summary="Platform milestone naming posture is unavailable.",
            available=False,
        )
    missing = payload.get("missing_platform_milestones", [])
    unknown = payload.get("unknown_platform_like_milestones", [])
    if (isinstance(missing, list) and missing) or (isinstance(unknown, list) and unknown):
        return _status_payload(
            area="platform_milestone_naming",
            requirement_level="required",
            status="attention_needed",
            summary="Platform milestone naming needs alignment.",
            available=True,
            details={
                "missing_platform_milestones": missing,
                "unknown_platform_like_milestones": unknown,
            },
        )
    return _status_payload(
        area="platform_milestone_naming",
        requirement_level="required",
        status="satisfied",
        summary="Platform milestone naming is aligned with the canonical contract.",
        available=True,
    )


def _evaluate_project_milestone_mapping(governance: dict[str, Any]) -> dict[str, Any]:
    payload = governance.get("milestone_naming_status")
    if not isinstance(payload, dict) or payload.get("available") is not True:
        return _status_payload(
            area="project_specific_milestone_mapping",
            requirement_level="recommended",
            status="unavailable",
            summary="Project-specific milestone mapping could not be evaluated.",
            available=False,
        )
    project_specific = payload.get("project_specific_milestones", [])
    if isinstance(project_specific, list) and project_specific:
        return _status_payload(
            area="project_specific_milestone_mapping",
            requirement_level="recommended",
            status="advisory",
            summary="Project-specific milestones exist and should map to platform phases.",
            available=True,
            details={"project_specific_milestones": project_specific},
        )
    return _status_payload(
        area="project_specific_milestone_mapping",
        requirement_level="recommended",
        status="satisfied",
        summary="No project-specific milestones were detected; platform naming remains clean.",
        available=True,
    )


def _evaluate_issue_templates_or_conventions(repo_root: Path) -> dict[str, Any]:
    template_dir = repo_root / ".github" / "ISSUE_TEMPLATE"
    has_issue_template_dir = template_dir.exists() and template_dir.is_dir()
    has_issue_template_file = (repo_root / ".github" / "ISSUE_TEMPLATE.md").exists()
    conventions_doc = (repo_root / "docs" / "operator" / "LOCAL_OPERATOR_USAGE.md").exists()
    if has_issue_template_dir or has_issue_template_file:
        return _status_payload(
            area="issue_templates_or_issue_conventions",
            requirement_level="recommended",
            status="satisfied",
            summary="Issue template coverage exists in repository metadata.",
            available=True,
        )
    if conventions_doc:
        return _status_payload(
            area="issue_templates_or_issue_conventions",
            requirement_level="recommended",
            status="advisory",
            summary="No issue templates detected; issue conventions are expected to be documented and manually applied.",
            available=True,
        )
    return _status_payload(
        area="issue_templates_or_issue_conventions",
        requirement_level="recommended",
        status="attention_needed",
        summary="No issue templates or issue conventions document was detected.",
        available=True,
    )


def _evaluate_pr_linking_conventions() -> dict[str, Any]:
    return _status_payload(
        area="pr_linking_conventions",
        requirement_level="recommended",
        status="advisory",
        summary="PR-to-issue linking remains a human review convention and should be validated per PR.",
        available=True,
        details={
            "expected_pattern": "Use explicit issue linking in PR body, for example 'Closes #<issue-number>'."
        },
    )


def _evaluate_validation_evidence_expectations(repo_root: Path) -> dict[str, Any]:
    pr_template_exists = (repo_root / "docs" / "agents" / "PR_EVIDENCE_PACKAGE_TEMPLATE.md").exists()
    return _status_payload(
        area="validation_evidence_expectations",
        requirement_level="required",
        status="satisfied" if pr_template_exists else "attention_needed",
        summary=(
            "Validation evidence template is present."
            if pr_template_exists
            else "Validation evidence template is missing."
        ),
        available=True,
    )


def _evaluate_closeout_expectations(repo_root: Path) -> dict[str, Any]:
    closeout_template_exists = (
        repo_root / "docs" / "agents" / "CLOSEOUT_EVIDENCE_PACKAGE_TEMPLATE.md"
    ).exists()
    return _status_payload(
        area="closeout_expectations",
        requirement_level="required",
        status="satisfied" if closeout_template_exists else "attention_needed",
        summary=(
            "Closeout evidence template is present."
            if closeout_template_exists
            else "Closeout evidence template is missing."
        ),
        available=True,
    )


def _evaluate_documentation_expectations(repo_root: Path) -> dict[str, Any]:
    required_docs = [
        repo_root / "docs" / "context" / "BUILD_STATE.md",
        repo_root / "docs" / "context" / "AGENT_CONTEXT.md",
        repo_root / "docs" / "roadmap" / "ROADMAP.md",
    ]
    missing = [str(path.relative_to(repo_root)).replace("\\", "/") for path in required_docs if not path.exists()]
    if missing:
        return _status_payload(
            area="documentation_expectations",
            requirement_level="required",
            status="attention_needed",
            summary="One or more source-of-truth documents are missing.",
            available=True,
            details={"missing_documents": missing},
        )
    return _status_payload(
        area="documentation_expectations",
        requirement_level="required",
        status="satisfied",
        summary="Source-of-truth documentation entry points are present.",
        available=True,
    )


def _evaluate_generated_artifact_conventions(repo_root: Path) -> dict[str, Any]:
    artifact_roots = [
        repo_root / "artifacts" / "prompts" / "generated",
        repo_root / "artifacts" / "evidence" / "generated",
        repo_root / "artifacts" / "codex_handoffs" / "generated",
    ]
    missing = [str(path.relative_to(repo_root)).replace("\\", "/") for path in artifact_roots if not path.exists()]
    if missing:
        return _status_payload(
            area="generated_artifact_conventions",
            requirement_level="required",
            status="attention_needed",
            summary="One or more generated artifact convention paths are missing.",
            available=True,
            details={"missing_paths": missing},
        )
    return _status_payload(
        area="generated_artifact_conventions",
        requirement_level="required",
        status="satisfied",
        summary="Generated artifact convention paths are present.",
        available=True,
    )


def _evaluate_automation_boundaries(governance: dict[str, Any]) -> dict[str, Any]:
    boundary_confirmations = governance.get("boundary_confirmations")
    has_boundary_confirmation = isinstance(boundary_confirmations, list) and bool(boundary_confirmations)
    return _status_payload(
        area="automation_boundary_confirmations",
        requirement_level="required",
        status="satisfied" if has_boundary_confirmation else "attention_needed",
        summary=(
            "Automation boundaries are explicitly confirmed in governance inspection output."
            if has_boundary_confirmation
            else "Automation boundary confirmations were not available from governance inspection output."
        ),
        available=has_boundary_confirmation,
    )


def _evaluate_protected_historical_evidence(governance: dict[str, Any]) -> dict[str, Any]:
    boundary_confirmations = governance.get("boundary_confirmations")
    protected = False
    if isinstance(boundary_confirmations, list):
        protected = any(
            "protected historical" in str(item).lower()
            or "retired historical validation evidence" in str(item).lower()
            for item in boundary_confirmations
        )
    return _status_payload(
        area="protected_historical_evidence_handling",
        requirement_level="required",
        status="satisfied" if protected else "attention_needed",
        summary=(
            "Protected historical evidence handling is explicitly confirmed."
            if protected
            else "Protected historical evidence handling confirmation was not found in governance output."
        ),
        available=True,
    )


def _evaluate_local_path_and_slug(config: AppConfig, governance: dict[str, Any]) -> dict[str, Any]:
    repo_slug = governance.get("repository_slug")
    local_path_exists = config.repo_root.exists()
    slug_matches = isinstance(repo_slug, str) and repo_slug == f"{config.github_owner}/{config.github_repo}"
    status = "satisfied" if local_path_exists and slug_matches else "attention_needed"
    summary = (
        "Configured local path exists and repository slug matches configuration."
        if status == "satisfied"
        else "Local path or repository slug expectations need manual confirmation."
    )
    return _status_payload(
        area="local_path_and_repo_slug_expectations",
        requirement_level="required",
        status=status,
        summary=summary,
        available=True,
        details={
            "configured_repository_slug": f"{config.github_owner}/{config.github_repo}",
            "inspected_repository_slug": repo_slug,
            "local_path_exists": local_path_exists,
            "local_path": str(config.repo_root),
        },
    )


def _evaluate_governance_profile(repo_root: Path) -> dict[str, Any]:
    governance_doc = repo_root / "docs" / "architecture" / "REPOSITORY_GOVERNANCE_CONTRACT.md"
    exists = governance_doc.exists()
    return _status_payload(
        area="governance_profile_expectations",
        requirement_level="required",
        status="satisfied" if exists else "attention_needed",
        summary=(
            "Repository governance profile contract document is present."
            if exists
            else "Repository governance profile contract document is missing."
        ),
        available=True,
    )


def _evaluate_multi_repo_deferred() -> dict[str, Any]:
    return _status_payload(
        area="future_multi_repo_governance_alignment",
        requirement_level="deferred",
        status="deferred",
        summary="Multi-repository bootstrap expansion is intentionally deferred to later M3 issues.",
        available=True,
    )


def _summarize(area_evaluation: list[dict[str, Any]]) -> dict[str, Any]:
    by_status = {
        "satisfied": 0,
        "attention_needed": 0,
        "advisory": 0,
        "unavailable": 0,
        "deferred": 0,
    }
    for area in area_evaluation:
        status = area.get("status")
        if status in by_status:
            by_status[status] += 1

    return {
        "area_count": len(area_evaluation),
        **by_status,
        "required_attention_needed": sum(
            1
            for area in area_evaluation
            if area.get("requirement_level") == "required" and area.get("status") == "attention_needed"
        ),
    }
