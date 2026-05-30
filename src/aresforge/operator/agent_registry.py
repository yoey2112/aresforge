from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.agent_runtime_boundary import (
    SUPPORTED_AUTONOMY_LEVELS,
    SUPPORTED_SAFETY_CLASSES,
)

COMMAND_NAME = "inspect-agent-registry"
AGENT_REGISTRY_VERSION = "m126.1"

_COMMON_FORBIDDEN: tuple[str, ...] = (
    "apply_patch",
    "mutate_queue_without_operator",
    "call_github_api",
    "call_gh",
    "call_external_network",
    "create_pr_or_issue",
    "background_daemon",
    "automatic_next_item_execution",
)

_MODEL_FORBIDDEN: tuple[str, ...] = (
    "execute_ollama_prompt",
    "execute_local_llm",
)

_CODEX_FORBIDDEN: tuple[str, ...] = ("execute_codex",)


@dataclass(frozen=True)
class AgentRecord:
    agent_id: str
    display_name: str
    description: str
    agent_type: str
    supported_item_types: tuple[str, ...]
    required_inputs: tuple[str, ...]
    optional_inputs: tuple[str, ...]
    produced_artifacts: tuple[str, ...]
    allowed_capabilities: tuple[str, ...]
    forbidden_capabilities: tuple[str, ...]
    mutation_scope: str
    network_scope: str
    model_scope: str
    safety_class: str
    autonomy_level: str
    default_execution_mode: str
    can_run_dry_run: bool
    can_run_real: bool
    machine_gate_required: bool
    evidence_required: tuple[str, ...]
    docs: tuple[str, ...]


def inspect_agent_registry(
    config: AppConfig,
    *,
    agent_id: str | None = None,
    safety_class: str | None = None,
    autonomy_level: str | None = None,
    output: str | Path | None = None,
    force: bool = False,
    output_format: str = "json",
) -> dict[str, Any]:
    fmt = str(output_format or "json").lower().strip()
    if fmt != "json":
        return _error("invalid_format", {"format": output_format, "supported_formats": ["json"]})

    payload = build_agent_registry(
        config,
        agent_id=agent_id,
        safety_class=safety_class,
        autonomy_level=autonomy_level,
    )
    return _emit_or_write(payload, output=output, force=force)


def build_agent_registry(
    config: AppConfig,
    *,
    agent_id: str | None = None,
    safety_class: str | None = None,
    autonomy_level: str | None = None,
) -> dict[str, Any]:
    normalized_agent_id = _normalize_filter(agent_id)
    normalized_safety_class = _normalize_filter(safety_class)
    normalized_autonomy_level = _normalize_filter(autonomy_level)

    all_agents = [_agent_to_dict(agent) for agent in _agent_records()]
    agents = [
        agent
        for agent in all_agents
        if (not normalized_agent_id or agent["agent_id"] == normalized_agent_id)
        and (not normalized_safety_class or agent["safety_class"] == normalized_safety_class)
        and (not normalized_autonomy_level or agent["autonomy_level"] == normalized_autonomy_level)
    ]
    warnings: list[str] = []
    if normalized_safety_class and normalized_safety_class not in SUPPORTED_SAFETY_CLASSES:
        warnings.append(f"Unknown safety_class filter: {normalized_safety_class}")
    if normalized_autonomy_level and normalized_autonomy_level not in SUPPORTED_AUTONOMY_LEVELS:
        warnings.append(f"Unknown autonomy_level filter: {normalized_autonomy_level}")
    if normalized_agent_id and not any(agent["agent_id"] == normalized_agent_id for agent in all_agents):
        warnings.append(f"Unknown agent_id filter: {normalized_agent_id}")

    return {
        "registry_type": "agent_registry",
        "generated": True,
        "generated_at": _now_iso(),
        "agent_registry_version": AGENT_REGISTRY_VERSION,
        "repo_root": str(config.repo_root),
        "agent_count": len(agents),
        "agents": agents,
        "agents_by_type": _group_agents(agents, "agent_type"),
        "agents_by_safety_class": _group_agents(agents, "safety_class"),
        "agents_by_autonomy_level": _group_agents(agents, "autonomy_level"),
        "blocked_agents": [
            agent["agent_id"]
            for agent in agents
            if agent["machine_gate_required"] or not agent["can_run_real"]
        ],
        "executable_agents": [agent["agent_id"] for agent in agents if agent["can_run_real"]],
        "dry_run_only_agents": [
            agent["agent_id"]
            for agent in agents
            if agent["can_run_dry_run"] and not agent["can_run_real"]
        ],
        "local_only": True,
        "read_only": True,
        "execution_allowed": False,
        "execution_performed": False,
        "filters": {
            "agent_id": normalized_agent_id,
            "safety_class": normalized_safety_class,
            "autonomy_level": normalized_autonomy_level,
        },
        "warnings": warnings,
        "next_safe_action": "Review this declarative registry as policy metadata only; do not execute agents until a later explicit operator-approved runner exists.",
    }


def _agent_records() -> tuple[AgentRecord, ...]:
    docs_common = (
        "docs/context/AGENT_CONTEXT.md",
        "docs/architecture/RUNNABLE_SKELETON.md",
        "docs/architecture/AGENT_LLM_ROUTING_STRATEGY.md",
    )
    queue_inputs = ("queue_item", "project_registry", "runtime_boundary_contract")
    evidence_inputs = ("queue_item", "validation_evidence", "runtime_boundary_contract")
    return (
        AgentRecord(
            agent_id="queue-planner-agent",
            display_name="Queue Planner Agent",
            description="Plans local queue ordering, dependencies, and operator next actions without mutating queue state.",
            agent_type="planner",
            supported_item_types=("architecture", "feature", "documentation", "dashboard", "validation"),
            required_inputs=queue_inputs,
            optional_inputs=("operator_batch_limit", "project_filter", "repo_filter"),
            produced_artifacts=("queue_plan_report", "blocked_item_summary"),
            allowed_capabilities=("read_local_queue", "read_local_artifacts", "generate_plan_artifact"),
            forbidden_capabilities=_COMMON_FORBIDDEN + _MODEL_FORBIDDEN + _CODEX_FORBIDDEN,
            mutation_scope="artifact_only",
            network_scope="none",
            model_scope="none",
            safety_class="read_only",
            autonomy_level="recommendation_only",
            default_execution_mode="plan_only",
            can_run_dry_run=True,
            can_run_real=False,
            machine_gate_required=False,
            evidence_required=("queue_snapshot", "dependency_summary", "blocked_reasons"),
            docs=docs_common + ("docs/operator/LOCAL_OPERATOR_USAGE.md",),
        ),
        AgentRecord(
            agent_id="codex-dispatch-agent",
            display_name="Codex Dispatch Agent",
            description="Prepares operator-reviewed Codex handoff records and evidence expectations without invoking Codex.",
            agent_type="codex_handoff",
            supported_item_types=("architecture", "feature", "validation", "dashboard"),
            required_inputs=("queue_item", "codex_prompt_artifact", "approval_gate", "runtime_boundary_contract"),
            optional_inputs=("dispatch_artifact_index", "operator_notes"),
            produced_artifacts=("manual_codex_dispatch_preparation", "codex_handoff_checklist"),
            allowed_capabilities=("read_local_queue", "read_local_artifacts", "generate_review_artifact"),
            forbidden_capabilities=_COMMON_FORBIDDEN + _MODEL_FORBIDDEN + _CODEX_FORBIDDEN,
            mutation_scope="artifact_only",
            network_scope="none",
            model_scope="codex_handoff_only",
            safety_class="external_mutation_prohibited",
            autonomy_level="manual_only",
            default_execution_mode="human_handoff",
            can_run_dry_run=True,
            can_run_real=False,
            machine_gate_required=True,
            evidence_required=("approval_gate_id", "prompt_artifact_path", "operator_checklist"),
            docs=docs_common + ("docs/operator/LOCAL_OPERATOR_USAGE.md",),
        ),
        AgentRecord(
            agent_id="local-llm-advisory-agent",
            display_name="Local LLM Advisory Agent",
            description="Builds local advisory request packages and provider metadata without calling prompt endpoints.",
            agent_type="local_llm_advisory",
            supported_item_types=("architecture", "documentation", "validation", "feature"),
            required_inputs=("queue_item", "dispatch_plan", "local_llm_environment_contract", "runtime_boundary_contract"),
            optional_inputs=("model_profile", "reasoning_scope", "source_documents"),
            produced_artifacts=("local_llm_advisory_request", "local_provider_readiness_summary"),
            allowed_capabilities=("read_local_queue", "read_source_docs", "read_local_artifacts", "generate_review_artifact", "local_provider_health_probe"),
            forbidden_capabilities=_COMMON_FORBIDDEN + _CODEX_FORBIDDEN + ("execute_ollama_prompt", "execute_local_llm"),
            mutation_scope="artifact_only",
            network_scope="localhost_health_only",
            model_scope="local_health_probe_only",
            safety_class="local_provider_probe",
            autonomy_level="operator_approved_single_step",
            default_execution_mode="artifact_generation",
            can_run_dry_run=True,
            can_run_real=False,
            machine_gate_required=True,
            evidence_required=("dispatch_plan", "provider_contract_summary", "execution_allowed_false"),
            docs=docs_common + ("docs/architecture/LOCAL_LLM_ENVIRONMENT_CONTRACT.md",),
        ),
        AgentRecord(
            agent_id="documentation-agent",
            display_name="Documentation Agent",
            description="Plans source-of-truth documentation reconciliation and future patch proposals without applying documentation changes.",
            agent_type="documentation",
            supported_item_types=("documentation", "architecture"),
            required_inputs=("source_documents", "change_summary", "validation_evidence", "runtime_boundary_contract"),
            optional_inputs=("dispatch_result_evidence", "operator_selected_docs"),
            produced_artifacts=("documentation_reconciliation_plan", "documentation_patch_proposal"),
            allowed_capabilities=("read_source_docs", "read_local_artifacts", "generate_plan_artifact", "generate_review_artifact"),
            forbidden_capabilities=_COMMON_FORBIDDEN + _MODEL_FORBIDDEN + _CODEX_FORBIDDEN + ("execute_documentation_agent",),
            mutation_scope="source_patch_prohibited",
            network_scope="none",
            model_scope="none",
            safety_class="external_mutation_prohibited",
            autonomy_level="recommendation_only",
            default_execution_mode="plan_only",
            can_run_dry_run=True,
            can_run_real=False,
            machine_gate_required=True,
            evidence_required=("source_docs_selected", "validation_summary", "operator_review_status"),
            docs=docs_common + ("docs/architecture/DOCUMENTATION_AGENT_CONTRACT.md",),
        ),
        AgentRecord(
            agent_id="evidence-parser-agent",
            display_name="Evidence Parser Agent",
            description="Parses local dispatch result evidence into structured metadata for human review.",
            agent_type="evidence",
            supported_item_types=("architecture", "feature", "validation", "documentation", "dashboard"),
            required_inputs=("queue_item", "local_result_file", "runtime_boundary_contract"),
            optional_inputs=("section_aliases", "operator_notes"),
            produced_artifacts=("dispatch_result_evidence", "missing_evidence_warnings"),
            allowed_capabilities=("read_local_queue", "read_local_artifacts", "generate_review_artifact"),
            forbidden_capabilities=_COMMON_FORBIDDEN + _MODEL_FORBIDDEN + _CODEX_FORBIDDEN,
            mutation_scope="artifact_only",
            network_scope="none",
            model_scope="none",
            safety_class="read_only",
            autonomy_level="recommendation_only",
            default_execution_mode="artifact_generation",
            can_run_dry_run=True,
            can_run_real=False,
            machine_gate_required=False,
            evidence_required=("result_path", "parsed_sections", "human_review_required"),
            docs=docs_common + ("docs/operator/LOCAL_OPERATOR_USAGE.md",),
        ),
        AgentRecord(
            agent_id="completion-recommendation-agent",
            display_name="Completion Recommendation Agent",
            description="Recommends whether a queue item appears complete from local evidence without changing queue status.",
            agent_type="recommendation",
            supported_item_types=("architecture", "feature", "validation", "documentation", "dashboard"),
            required_inputs=evidence_inputs,
            optional_inputs=("completion_requirements", "operator_notes"),
            produced_artifacts=("queue_completion_recommendation", "evidence_gap_report"),
            allowed_capabilities=("read_local_queue", "read_local_artifacts", "generate_review_artifact"),
            forbidden_capabilities=_COMMON_FORBIDDEN + _MODEL_FORBIDDEN + _CODEX_FORBIDDEN,
            mutation_scope="artifact_only",
            network_scope="none",
            model_scope="none",
            safety_class="read_only",
            autonomy_level="recommendation_only",
            default_execution_mode="plan_only",
            can_run_dry_run=True,
            can_run_real=False,
            machine_gate_required=False,
            evidence_required=("dispatch_evidence", "validation_summary", "operator_decision_required"),
            docs=docs_common + ("docs/operator/LOCAL_OPERATOR_USAGE.md",),
        ),
        AgentRecord(
            agent_id="validation-agent",
            display_name="Validation Agent",
            description="Describes local validation command plans and result evidence requirements without running commands.",
            agent_type="validation",
            supported_item_types=("validation", "feature", "architecture", "documentation"),
            required_inputs=("queue_item", "changed_files", "validation_contract", "runtime_boundary_contract"),
            optional_inputs=("smoke_check_targets", "test_selection_hints"),
            produced_artifacts=("validation_plan", "validation_evidence_summary"),
            allowed_capabilities=("read_local_queue", "read_local_artifacts", "generate_plan_artifact"),
            forbidden_capabilities=_COMMON_FORBIDDEN + _MODEL_FORBIDDEN + _CODEX_FORBIDDEN,
            mutation_scope="artifact_only",
            network_scope="none",
            model_scope="none",
            safety_class="external_mutation_prohibited",
            autonomy_level="operator_approved_single_step",
            default_execution_mode="plan_only",
            can_run_dry_run=True,
            can_run_real=False,
            machine_gate_required=True,
            evidence_required=("validation_commands", "smoke_checks", "git_diff_check_result"),
            docs=docs_common + ("docs/operator/LOCAL_OPERATOR_USAGE.md",),
        ),
        AgentRecord(
            agent_id="github-sync-agent",
            display_name="GitHub Sync Agent",
            description="Plans offline-to-GitHub sync candidates while forbidding live GitHub and gh execution.",
            agent_type="github_sync",
            supported_item_types=("architecture", "documentation", "validation"),
            required_inputs=("local_queue_state", "local_project_state", "sync_intent", "runtime_boundary_contract"),
            optional_inputs=("offline_state_file", "operator_selected_targets"),
            produced_artifacts=("github_sync_plan", "manual_sync_checklist"),
            allowed_capabilities=("read_local_queue", "read_local_artifacts", "generate_plan_artifact"),
            forbidden_capabilities=_COMMON_FORBIDDEN + _MODEL_FORBIDDEN + _CODEX_FORBIDDEN,
            mutation_scope="artifact_only",
            network_scope="external_network_forbidden",
            model_scope="none",
            safety_class="external_mutation_prohibited",
            autonomy_level="manual_only",
            default_execution_mode="plan_only",
            can_run_dry_run=True,
            can_run_real=False,
            machine_gate_required=True,
            evidence_required=("sync_plan", "operator_review_required", "execution_allowed_false"),
            docs=docs_common + ("docs/operator/LOCAL_OPERATOR_USAGE.md",),
        ),
        AgentRecord(
            agent_id="sprint-summary-agent",
            display_name="Sprint Summary Agent",
            description="Summarizes local queue, validation, and documentation posture for operator review.",
            agent_type="reporting",
            supported_item_types=("architecture", "documentation", "dashboard", "validation"),
            required_inputs=("queue_state", "project_report", "runtime_boundary_contract"),
            optional_inputs=("since_commit", "commit_count", "artifact_index"),
            produced_artifacts=("sprint_summary_report", "operator_handoff_summary"),
            allowed_capabilities=("read_local_queue", "read_source_docs", "read_local_artifacts", "inspect_local_git_state", "generate_plan_artifact"),
            forbidden_capabilities=_COMMON_FORBIDDEN + _MODEL_FORBIDDEN + _CODEX_FORBIDDEN,
            mutation_scope="artifact_only",
            network_scope="none",
            model_scope="none",
            safety_class="read_only",
            autonomy_level="recommendation_only",
            default_execution_mode="plan_only",
            can_run_dry_run=True,
            can_run_real=False,
            machine_gate_required=False,
            evidence_required=("queue_summary", "validation_summary", "warnings_or_blockers"),
            docs=docs_common + ("docs/context/BUILD_STATE.md",),
        ),
        AgentRecord(
            agent_id="artifact-registry-agent",
            display_name="Artifact Registry Agent",
            description="Indexes local artifacts and approval metadata for review without executing artifacts.",
            agent_type="artifact_registry",
            supported_item_types=("architecture", "feature", "documentation", "validation"),
            required_inputs=("artifact_root", "runtime_boundary_contract"),
            optional_inputs=("approval_gate_path", "project_filter"),
            produced_artifacts=("artifact_index_report", "approval_status_summary"),
            allowed_capabilities=("read_local_artifacts", "generate_review_artifact"),
            forbidden_capabilities=_COMMON_FORBIDDEN + _MODEL_FORBIDDEN + _CODEX_FORBIDDEN,
            mutation_scope="artifact_only",
            network_scope="none",
            model_scope="none",
            safety_class="read_only",
            autonomy_level="recommendation_only",
            default_execution_mode="inspect_only",
            can_run_dry_run=True,
            can_run_real=False,
            machine_gate_required=False,
            evidence_required=("artifact_paths", "approval_statuses", "execution_allowed_false"),
            docs=docs_common + ("docs/operator/LOCAL_OPERATOR_USAGE.md",),
        ),
        AgentRecord(
            agent_id="approval-ledger-agent",
            display_name="Approval Ledger Agent",
            description="Reads and records local approval gate metadata while preserving execution denial.",
            agent_type="approval",
            supported_item_types=("architecture", "feature", "documentation", "validation"),
            required_inputs=("approval_gate_record", "runtime_boundary_contract"),
            optional_inputs=("review_notes", "artifact_reference"),
            produced_artifacts=("approval_gate_summary", "approval_review_record"),
            allowed_capabilities=("read_local_artifacts", "generate_review_artifact"),
            forbidden_capabilities=_COMMON_FORBIDDEN + _MODEL_FORBIDDEN + _CODEX_FORBIDDEN,
            mutation_scope="artifact_only",
            network_scope="none",
            model_scope="none",
            safety_class="local_file_write",
            autonomy_level="manual_only",
            default_execution_mode="artifact_generation",
            can_run_dry_run=True,
            can_run_real=False,
            machine_gate_required=True,
            evidence_required=("approval_status", "review_notes", "operator_identity"),
            docs=docs_common + ("docs/operator/LOCAL_OPERATOR_USAGE.md",),
        ),
        AgentRecord(
            agent_id="transaction-log-agent",
            display_name="Transaction Log Agent",
            description="Records local operation summaries and audit metadata without executing external workflows.",
            agent_type="audit",
            supported_item_types=("architecture", "feature", "documentation", "validation", "dashboard"),
            required_inputs=("operation_summary", "runtime_boundary_contract"),
            optional_inputs=("artifact_refs", "validation_refs", "operator_notes"),
            produced_artifacts=("operation_log_entry", "audit_summary"),
            allowed_capabilities=("read_local_artifacts", "generate_review_artifact"),
            forbidden_capabilities=_COMMON_FORBIDDEN + _MODEL_FORBIDDEN + _CODEX_FORBIDDEN,
            mutation_scope="artifact_only",
            network_scope="none",
            model_scope="none",
            safety_class="local_file_write",
            autonomy_level="manual_only",
            default_execution_mode="artifact_generation",
            can_run_dry_run=True,
            can_run_real=False,
            machine_gate_required=True,
            evidence_required=("operation_summary", "timestamp", "operator_review_status"),
            docs=docs_common + ("docs/context/BUILD_STATE.md",),
        ),
    )


def _agent_to_dict(agent: AgentRecord) -> dict[str, Any]:
    data = asdict(agent)
    for key, value in list(data.items()):
        if isinstance(value, tuple):
            data[key] = list(value)
    return data


def _group_agents(agents: list[dict[str, Any]], key: str) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for agent in agents:
        grouped.setdefault(str(agent[key]), []).append(str(agent["agent_id"]))
    return {group_key: sorted(ids) for group_key, ids in sorted(grouped.items())}


def _emit_or_write(payload: dict[str, Any], *, output: str | Path | None, force: bool) -> dict[str, Any]:
    rendered = json.dumps(payload, indent=2)
    if output:
        output_path = Path(output)
        if output_path.exists() and not force:
            return _error(
                "output_exists",
                {"output": str(output_path), "message": "Refusing to overwrite output without --force."},
            )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered + "\n", encoding="utf-8")
        return {
            "command": COMMAND_NAME,
            "ok": True,
            "local_only": True,
            "format": "json",
            "wrote_output_file": True,
            "output": str(output_path),
            "payload": payload,
        }
    return {
        "command": COMMAND_NAME,
        "ok": True,
        "local_only": True,
        "format": "json",
        "wrote_output_file": False,
        "stdout": rendered,
        "payload": payload,
    }


def _error(error: str, details: Any) -> dict[str, Any]:
    return {
        "command": COMMAND_NAME,
        "ok": False,
        "local_only": True,
        "error": error,
        "details": details,
    }


def _normalize_filter(value: str | None) -> str:
    return str(value or "").strip()


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
