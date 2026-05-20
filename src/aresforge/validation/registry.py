from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from aresforge.db.repository import (
    CANONICAL_QUEUE_IDS,
    DEFAULT_AGENT_ID,
    DEFAULT_AGENT_RECORDS,
    DEFAULT_QUEUES,
    QUEUE_SCHEMA_SOURCE_DOCUMENT,
)


CANONICAL_ROUTE_STATUSES = (
    "queued",
    "ready",
    "in_progress",
    "waiting_for_human",
    "waiting_for_external_input",
    "blocked",
    "failed",
    "handed_off",
)

REQUIRED_QUEUE_METADATA_KEYS = (
    "accepted_work_item_types",
    "allowed_next_queues",
    "human_approval_requirement",
    "lifecycle_stage_mapping",
    "local_operator_visibility_expectations",
    "source_document",
)

ALLOWED_LOCAL_OPERATOR_CAPABILITIES = {
    "local_state_inspection",
    "migration_execution",
    "prompt_package_generation",
    "evidence_package_recording",
    "codex_handoff_preparation",
    "read_only_registry_listing",
}

FORBIDDEN_AGENT_METADATA_FRAGMENTS = (
    "autonomous_approval",
    "autonomous_merge",
    "autonomous_issue_closure",
    "queue_worker",
    "queue_workers",
    "hosted_model",
    "external_model",
    "github_mutation",
    "github_state_change",
    "merge_authority",
    "issue_close_authority",
)


@dataclass(frozen=True, slots=True)
class ValidationFinding:
    severity: str
    code: str
    message: str
    location: str


@dataclass(frozen=True, slots=True)
class ValidationReport:
    ok: bool
    findings: tuple[ValidationFinding, ...]


def _iter_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        strings: list[str] = []
        for nested in value.values():
            strings.extend(_iter_strings(nested))
        return strings
    if isinstance(value, (list, tuple, set)):
        strings: list[str] = []
        for nested in value:
            strings.extend(_iter_strings(nested))
        return strings
    return []


def _build_report(findings: list[ValidationFinding]) -> ValidationReport:
    return ValidationReport(ok=not findings, findings=tuple(findings))


def _implies_forbidden_behavior(value: str) -> bool:
    normalized = value.lower().replace("-", "_").replace(" ", "_")
    if any(
        marker in normalized
        for marker in (
            "no_autonomous",
            "not_autonomous",
            "must_not",
            "blocked",
            "disallowed",
            "without_authority",
        )
    ):
        return False
    return any(fragment in normalized for fragment in FORBIDDEN_AGENT_METADATA_FRAGMENTS)


def validate_registry_seed_data(
    *,
    queues: tuple[dict[str, Any], ...] = DEFAULT_QUEUES,
    agents: tuple[dict[str, Any], ...] = DEFAULT_AGENT_RECORDS,
) -> ValidationReport:
    findings: list[ValidationFinding] = []
    canonical_queue_ids = set(CANONICAL_QUEUE_IDS)
    queue_ids_in_seed = {record.get("id") for record in queues if record.get("id")}

    missing_queue_ids = canonical_queue_ids - queue_ids_in_seed
    for queue_id in sorted(missing_queue_ids):
        findings.append(
            ValidationFinding(
                severity="error",
                code="queue.missing_canonical_id",
                message=f"Canonical queue seed is missing required queue id '{queue_id}'.",
                location="queues",
            )
        )

    for record in queues:
        queue_id = record.get("id", "<missing-id>")
        metadata = record.get("metadata")
        location = f"queues[{queue_id}]"
        if not isinstance(metadata, dict):
            findings.append(
                ValidationFinding(
                    severity="error",
                    code="queue.missing_metadata",
                    message="Queue record is missing metadata.",
                    location=location,
                )
            )
            continue

        for key in REQUIRED_QUEUE_METADATA_KEYS:
            value = metadata.get(key)
            if value in (None, "", [], ()):
                findings.append(
                    ValidationFinding(
                        severity="error",
                        code="queue.missing_required_metadata",
                        message=f"Queue metadata is missing required key '{key}'.",
                        location=f"{location}.metadata.{key}",
                    )
                )

        accepted_types = metadata.get("accepted_work_item_types")
        if isinstance(accepted_types, list) and not accepted_types:
            findings.append(
                ValidationFinding(
                    severity="error",
                    code="queue.empty_accepted_work_item_types",
                    message="Queue must declare at least one accepted work item type.",
                    location=f"{location}.metadata.accepted_work_item_types",
                )
            )

        allowed_next_queues = metadata.get("allowed_next_queues")
        if isinstance(allowed_next_queues, list):
            if not allowed_next_queues:
                findings.append(
                    ValidationFinding(
                        severity="error",
                        code="queue.empty_allowed_next_queues",
                        message="Queue must declare at least one allowed next queue.",
                        location=f"{location}.metadata.allowed_next_queues",
                    )
                )
            for next_queue in allowed_next_queues:
                if next_queue not in canonical_queue_ids:
                    findings.append(
                        ValidationFinding(
                            severity="error",
                            code="queue.invalid_allowed_next_queue",
                            message=(
                                f"Queue references unknown next queue '{next_queue}'."
                            ),
                            location=f"{location}.metadata.allowed_next_queues",
                        )
                    )

        source_document = metadata.get("source_document")
        if source_document not in (None, QUEUE_SCHEMA_SOURCE_DOCUMENT):
            findings.append(
                ValidationFinding(
                    severity="error",
                    code="queue.invalid_source_document",
                    message=(
                        "Queue source document must point to the canonical queue schema."
                    ),
                    location=f"{location}.metadata.source_document",
                )
            )

        human_approval_requirement = metadata.get("human_approval_requirement")
        if human_approval_requirement not in (None, "human_review_required"):
            findings.append(
                ValidationFinding(
                    severity="error",
                    code="queue.invalid_human_approval_requirement",
                    message=(
                        "Queue human approval requirement must be explicit and equal "
                        "to 'human_review_required'."
                    ),
                    location=f"{location}.metadata.human_approval_requirement",
                )
            )

        visibility = metadata.get("local_operator_visibility_expectations")
        if isinstance(visibility, list) and not visibility:
            findings.append(
                ValidationFinding(
                    severity="error",
                    code="queue.empty_local_operator_visibility_expectations",
                    message="Queue must declare non-empty local operator visibility expectations.",
                    location=f"{location}.metadata.local_operator_visibility_expectations",
                )
            )

    for record in agents:
        agent_id = record.get("id", "<missing-id>")
        metadata = record.get("metadata")
        location = f"agents[{agent_id}]"
        if not isinstance(metadata, dict):
            findings.append(
                ValidationFinding(
                    severity="error",
                    code="agent.missing_metadata",
                    message="Agent record is missing metadata.",
                    location=location,
                )
            )
            continue

        queue_participation = metadata.get("queue_participation")
        if not isinstance(queue_participation, list) or not queue_participation:
            findings.append(
                ValidationFinding(
                    severity="error",
                    code="agent.missing_queue_participation",
                    message="Agent metadata must declare queue participation.",
                    location=f"{location}.metadata.queue_participation",
                )
            )
        else:
            for queue_id in queue_participation:
                if queue_id not in canonical_queue_ids:
                    findings.append(
                        ValidationFinding(
                            severity="error",
                            code="agent.invalid_queue_participation",
                            message=f"Agent references unknown queue '{queue_id}'.",
                            location=f"{location}.metadata.queue_participation",
                        )
                    )

        approval_boundary = metadata.get("approval_boundary")
        if not approval_boundary:
            findings.append(
                ValidationFinding(
                    severity="error",
                    code="agent.missing_approval_boundary",
                    message="Agent metadata must declare an approval boundary.",
                    location=f"{location}.metadata.approval_boundary",
                )
            )

        if agent_id == DEFAULT_AGENT_ID:
            capabilities = metadata.get("allowed_capabilities")
            if not isinstance(capabilities, list) or not capabilities:
                findings.append(
                    ValidationFinding(
                        severity="error",
                        code="agent.local_operator_missing_capabilities",
                        message="Local Operator must declare bounded allowed capabilities.",
                        location=f"{location}.metadata.allowed_capabilities",
                    )
                )
            else:
                unexpected_capabilities = sorted(
                    capability
                    for capability in capabilities
                    if capability not in ALLOWED_LOCAL_OPERATOR_CAPABILITIES
                )
                if unexpected_capabilities:
                    findings.append(
                        ValidationFinding(
                            severity="error",
                            code="agent.local_operator_unbounded_capability",
                            message=(
                                "Local Operator includes capabilities outside the allowed "
                                f"human-triggered local set: {unexpected_capabilities}."
                            ),
                            location=f"{location}.metadata.allowed_capabilities",
                        )
                    )

        for value in _iter_strings(metadata):
            if _implies_forbidden_behavior(value):
                findings.append(
                    ValidationFinding(
                        severity="error",
                        code="agent.forbidden_metadata_implication",
                        message=(
                            "Agent metadata implies blocked authority or execution mode "
                            f"through value '{value}'."
                        ),
                        location=location,
                    )
                )

    return _build_report(findings)
