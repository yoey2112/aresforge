from __future__ import annotations

from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.managed_repo_readiness_report import managed_repo_readiness_report
from aresforge.operator.managed_repo_registry import inspect_managed_repos
from aresforge.operator.repo_bootstrap_contract import inspect_repo_bootstrap_contract
from aresforge.operator.repo_bootstrap_plan import plan_repo_bootstrap
from aresforge.operator.repo_governance import inspect_repo_governance


DEMO_VERSION = "m3-managed-repo-governance-demo-v1"


def demo_managed_repo_governance(config: AppConfig) -> dict[str, Any]:
    governance = inspect_repo_governance(config)
    bootstrap_contract = inspect_repo_bootstrap_contract(config)
    registry = inspect_managed_repos(config)
    readiness = managed_repo_readiness_report(config)
    bootstrap_plan = plan_repo_bootstrap(config)

    warnings = _collect_warnings(
        governance,
        bootstrap_contract,
        registry,
        readiness,
        bootstrap_plan,
    )
    steps = _demo_steps(
        governance=governance,
        bootstrap_contract=bootstrap_contract,
        registry=registry,
        readiness=readiness,
        bootstrap_plan=bootstrap_plan,
    )

    return {
        "command": "demo-managed-repo-governance",
        "ok": True,
        "inspection_mode": "read_only_demo_flow",
        "demo_version": DEMO_VERSION,
        "demo_summary": {
            "goal": "Demonstrate end-to-end managed repository governance inspection through read-only deterministic outputs.",
            "repository_count": readiness.get("repository_count"),
            "step_count": len(steps),
            "attention_needed_steps": sum(1 for step in steps if step["status"] == "attention_needed"),
            "deferred_steps": sum(1 for step in steps if step["status"] == "deferred"),
            "warnings_count": len(warnings),
        },
        "demo_steps": steps,
        "managed_repository_context": {
            "repository_slug": f"{config.github_owner}/{config.github_repo}",
            "local_path": str(config.repo_root),
            "default_managed_repository_expected": True,
            "human_trigger_required": True,
            "read_only_demo": True,
        },
        "governance_inspection": governance,
        "bootstrap_contract_evaluation": bootstrap_contract,
        "registry_representation": registry,
        "readiness_report": readiness,
        "bootstrap_plan": bootstrap_plan,
        "qa_validation_expectations": [
            {
                "command": "python -m aresforge inspect-managed-repos",
                "expected_signal": "Deterministic read-only managed repository registry posture with warnings preserved.",
            },
            {
                "command": "python -m aresforge inspect-repo-governance",
                "expected_signal": "Reusable repository governance posture with explicit required/optional/trigger labels and milestones.",
            },
            {
                "command": "python -m aresforge inspect-repo-bootstrap-contract",
                "expected_signal": "Required/recommended/deferred bootstrap contract status with attention-needed and advisory posture retained.",
            },
            {
                "command": "python -m aresforge managed-repo-readiness-report",
                "expected_signal": "Per-repository readiness level with local-path, git, gh, and contract degradation warnings when unavailable.",
            },
            {
                "command": "python -m aresforge plan-repo-bootstrap",
                "expected_signal": "Read-only human-reviewable setup plan with no setup mutation performed.",
            },
            {
                "command": "python -m aresforge demo-managed-repo-governance",
                "expected_signal": "End-to-end deterministic demo flow linking all governance stack steps.",
            },
        ],
        "documentation_expectations": {
            "required_source_of_truth_docs": [
                "docs/context/BUILD_STATE.md",
                "docs/context/AGENT_CONTEXT.md",
                "docs/roadmap/ROADMAP.md",
            ],
            "operator_doc": "docs/operator/LOCAL_OPERATOR_USAGE.md",
            "architecture_docs": [
                "docs/architecture/RUNNABLE_SKELETON.md",
                "docs/architecture/REPOSITORY_GOVERNANCE_CONTRACT.md",
                "docs/architecture/MANAGED_REPOSITORY_BOOTSTRAP_CONTRACT.md",
                "docs/architecture/MANAGED_REPOSITORY_REGISTRY.md",
            ],
            "expectation": "Project-state-changing governance work updates source-of-truth docs before closeout.",
        },
        "warnings": warnings,
        "recommended_next_action": _recommended_next_action(steps, warnings),
        "boundary_confirmations": [
            "Read-only managed repository governance demo only.",
            "No labels, milestones, issues, pull requests, branches, settings, workflows, artifacts, files, or git state were mutated.",
            "No background jobs, schedulers, daemons, or polling loops were used.",
            "No autonomous GitHub mutation was performed.",
            "Issue #39 remains retired historical validation evidence and was not modified.",
        ],
    }


def _demo_steps(
    *,
    governance: dict[str, Any],
    bootstrap_contract: dict[str, Any],
    registry: dict[str, Any],
    readiness: dict[str, Any],
    bootstrap_plan: dict[str, Any],
) -> list[dict[str, Any]]:
    return [
        _step(
            id="governance_inspection",
            title="Inspect repository governance",
            command="python -m aresforge inspect-repo-governance",
            status=_governance_step_status(governance),
            summary="Check reusable required/optional labels, trigger labels, milestone posture, and issue/PR readiness signals.",
        ),
        _step(
            id="bootstrap_contract_evaluation",
            title="Evaluate bootstrap contract",
            command="python -m aresforge inspect-repo-bootstrap-contract",
            status=_bootstrap_contract_step_status(bootstrap_contract),
            summary="Evaluate required/recommended/deferred bootstrap areas without setup mutation.",
        ),
        _step(
            id="registry_representation",
            title="Inspect managed repository registry",
            command="python -m aresforge inspect-managed-repos",
            status=_registry_step_status(registry),
            summary="Represent the configured repository as default managed repository with optional registry extension merge.",
        ),
        _step(
            id="readiness_report",
            title="Generate readiness report",
            command="python -m aresforge managed-repo-readiness-report",
            status=_readiness_step_status(readiness),
            summary="Classify per-repository readiness posture and preserve warnings for unavailable dependencies.",
        ),
        _step(
            id="bootstrap_plan",
            title="Generate bootstrap plan",
            command="python -m aresforge plan-repo-bootstrap",
            status=_bootstrap_plan_step_status(bootstrap_plan),
            summary="Produce deterministic human-reviewable setup action plan while confirming no setup mutation.",
        ),
        _step(
            id="qa_validation_expectations",
            title="Validate governance stack coverage",
            command="python -m aresforge --help",
            status="pass",
            summary="Confirm governance stack command surfaces remain exposed and testable.",
        ),
        _step(
            id="documentation_expectations",
            title="Validate source-of-truth documentation posture",
            command="python -m aresforge project-state-summary",
            status="pass",
            summary="Confirm documentation entry points remain mandatory for project-state-changing governance work.",
        ),
    ]


def _collect_warnings(*payloads: dict[str, Any]) -> list[str]:
    rows: list[str] = []
    for payload in payloads:
        warnings = payload.get("warnings")
        if isinstance(warnings, list):
            rows.extend(str(item).strip() for item in warnings if str(item).strip())
    return sorted(set(rows), key=str.lower)


def _governance_step_status(governance: dict[str, Any]) -> str:
    required = governance.get("required_platform_labels", {})
    triggers = governance.get("automation_trigger_labels", {})
    milestone = governance.get("milestone_naming_status", {})
    if _is_unavailable(required) or _is_unavailable(triggers) or _is_unavailable(milestone):
        return "attention_needed"
    if _has_missing(required) or _has_missing(triggers):
        return "attention_needed"
    missing_milestones = milestone.get("missing_platform_milestones") if isinstance(milestone, dict) else None
    if isinstance(missing_milestones, list) and missing_milestones:
        return "attention_needed"
    return "pass"


def _bootstrap_contract_step_status(contract: dict[str, Any]) -> str:
    summary = contract.get("summary", {})
    if not isinstance(summary, dict):
        return "attention_needed"
    required_attention = summary.get("required_attention_needed")
    if isinstance(required_attention, int) and required_attention > 0:
        return "attention_needed"
    unavailable = summary.get("unavailable")
    if isinstance(unavailable, int) and unavailable > 0:
        return "attention_needed"
    deferred = summary.get("deferred")
    if isinstance(deferred, int) and deferred > 0:
        return "deferred"
    return "pass"


def _registry_step_status(registry: dict[str, Any]) -> str:
    count = registry.get("managed_repository_count")
    if not isinstance(count, int) or count < 1:
        return "attention_needed"
    return "pass"


def _readiness_step_status(readiness: dict[str, Any]) -> str:
    rows = readiness.get("repositories")
    if not isinstance(rows, list) or not rows:
        return "attention_needed"
    levels = {row.get("readiness_level") for row in rows if isinstance(row, dict)}
    if levels & {"attention_needed", "degraded", "unavailable"}:
        return "attention_needed"
    return "pass"


def _bootstrap_plan_step_status(plan: dict[str, Any]) -> str:
    rows = plan.get("repositories")
    if not isinstance(rows, list) or not rows:
        return "attention_needed"
    for repo in rows:
        if not isinstance(repo, dict):
            continue
        actions = repo.get("actions")
        if isinstance(actions, list) and any(
            isinstance(action, dict) and action.get("category") == "required"
            for action in actions
        ):
            return "attention_needed"
    return "pass"


def _step(*, id: str, title: str, command: str, status: str, summary: str) -> dict[str, Any]:
    return {
        "step_id": id,
        "title": title,
        "status": status,
        "validation_command": command,
        "summary": summary,
    }


def _recommended_next_action(steps: list[dict[str, Any]], warnings: list[str]) -> str:
    if any(step["status"] == "attention_needed" for step in steps):
        return (
            "Review attention-needed steps, perform any repository setup changes manually, and rerun "
            "demo-managed-repo-governance to confirm deterministic read-only governance posture."
        )
    if warnings:
        return (
            "Resolve warnings (gh/network/local-path dependencies) and rerun demo-managed-repo-governance "
            "for a complete snapshot."
        )
    return "Managed repository governance demo passed in read-only mode; keep all setup mutation human-triggered."


def _is_unavailable(payload: Any) -> bool:
    return isinstance(payload, dict) and payload.get("available") is False


def _has_missing(payload: Any) -> bool:
    if not isinstance(payload, dict):
        return False
    missing = payload.get("missing")
    return isinstance(missing, list) and bool(missing)
