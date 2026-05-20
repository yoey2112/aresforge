from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aresforge.artifacts.store import ArtifactBundle, write_markdown_json_bundle
from aresforge.config import AppConfig


def _inspection_reports_dir(config: AppConfig) -> Path:
    return config.artifact_root / "inspection_reports" / "generated"


def _generated_at() -> str:
    return datetime.now(UTC).isoformat()


def _stringify(value: Any, empty_message: str = "Not recorded.") -> str:
    if value is None or value == "":
        return empty_message
    if isinstance(value, (dict, list)):
        return json.dumps(value, indent=2, sort_keys=True)
    return str(value)


def _bullet_lines(items: list[Any] | None, empty_message: str) -> list[str]:
    if not items:
        return [f"- {empty_message}"]
    return [f"- {item}" for item in items]


def _code_block(value: Any) -> list[str]:
    return ["```json", json.dumps(value, indent=2, sort_keys=True), "```"]


def render_queue_inspection_report(
    *,
    config: AppConfig,
    inspection_payload: dict[str, Any],
) -> ArtifactBundle:
    queue_id = inspection_payload.get("id", "unknown-queue")
    queue_name = inspection_payload.get("name", "unknown")
    report_metadata = {
        "report_type": "queue_inspection",
        "generated_at": _generated_at(),
        "artifact_kind": "local_operator_inspection_report",
        "source_document": inspection_payload.get("source_document"),
        "queue_id": queue_id,
    }
    payload = {
        "report_metadata": report_metadata,
        "inspection_payload": inspection_payload,
    }
    markdown = "\n".join(
        [
            "# Queue Inspection Report",
            "",
            "## Queue Summary",
            f"- Queue ID: `{queue_id}`",
            f"- Queue Name: `{queue_name}`",
            f"- Status: `{_stringify(inspection_payload.get('status'))}`",
            f"- Purpose: {_stringify(inspection_payload.get('purpose'))}",
            "",
            "## Registry Mapping",
            f"- Lifecycle Stage Mapping: `{_stringify(inspection_payload.get('lifecycle_stage_mapping'))}`",
            *(
                ["- Accepted Work Item Types:"]
                + _bullet_lines(
                    inspection_payload.get("accepted_work_item_types"),
                    "No accepted work item types recorded.",
                )
            ),
            *(
                ["- Allowed Next Queues:"]
                + _bullet_lines(
                    inspection_payload.get("allowed_next_queues"),
                    "No allowed next queues recorded.",
                )
            ),
            f"- Human Approval Requirement: `{_stringify(inspection_payload.get('human_approval_requirement'))}`",
            "",
            "## Local Operator Visibility",
            *(
                _bullet_lines(
                    inspection_payload.get("local_operator_visibility_expectations"),
                    "No local operator visibility expectations recorded.",
                )
            ),
            "",
            "## Source Document",
            _stringify(inspection_payload.get("source_document")),
            "",
            "## Metadata",
            *_code_block(inspection_payload.get("metadata") or {}),
            "",
            "## Report Metadata",
            *_code_block(report_metadata),
        ]
    )
    return write_markdown_json_bundle(
        _inspection_reports_dir(config),
        title=f"queue-inspection-report-{queue_id}-{queue_name}",
        markdown=markdown,
        payload=payload,
    )


def render_work_item_inspection_report(
    *,
    config: AppConfig,
    inspection_payload: dict[str, Any],
) -> ArtifactBundle:
    work_item_id = inspection_payload.get("id", "unknown-work-item")
    title = inspection_payload.get("title", "untitled")
    report_metadata = {
        "report_type": "work_item_inspection",
        "generated_at": _generated_at(),
        "artifact_kind": "local_operator_inspection_report",
        "queue_id": inspection_payload.get("queue_id"),
        "work_item_id": work_item_id,
    }
    payload = {
        "report_metadata": report_metadata,
        "inspection_payload": inspection_payload,
    }
    markdown = "\n".join(
        [
            "# Work Item Inspection Report",
            "",
            "## Work Item Summary",
            f"- Work Item ID: `{work_item_id}`",
            f"- Title: {title}",
            f"- Description: {_stringify(inspection_payload.get('description'))}",
            f"- Status: `{_stringify(inspection_payload.get('status'))}`",
            f"- Priority: `{_stringify(inspection_payload.get('priority'))}`",
            f"- Route Status: `{_stringify(inspection_payload.get('route_status'))}`",
            "",
            "## Queue Context",
            f"- Queue ID: `{_stringify(inspection_payload.get('queue_id'))}`",
            f"- Queue Name: `{_stringify(inspection_payload.get('queue_name'))}`",
            f"- Queue Purpose: {_stringify(inspection_payload.get('queue_purpose'))}",
            f"- Lifecycle Mapping: `{_stringify(inspection_payload.get('queue_lifecycle_stage_mapping'))}`",
            *(
                ["- Allowed Next Queues:"]
                + _bullet_lines(
                    inspection_payload.get("queue_allowed_next_queues"),
                    "No allowed next queues recorded.",
                )
            ),
            f"- Human Approval Requirement: `{_stringify(inspection_payload.get('queue_human_approval_requirement'))}`",
            "",
            "## Agent And Model Context",
            f"- Agent ID: `{_stringify(inspection_payload.get('agent_id'))}`",
            f"- Agent Name: `{_stringify(inspection_payload.get('agent_name'))}`",
            f"- Model ID: `{_stringify(inspection_payload.get('model_id'))}`",
            f"- Model Name: `{_stringify(inspection_payload.get('model_name'))}`",
            f"- Model Provider: `{_stringify(inspection_payload.get('model_provider'))}`",
            f"- Prompt ID: `{_stringify(inspection_payload.get('prompt_id'))}`",
            "",
            "## Work Item State",
            f"- Lifecycle State: `{_stringify(inspection_payload.get('lifecycle_state'))}`",
            f"- Approval State: `{_stringify(inspection_payload.get('approval_state'))}`",
            f"- Blocked Reason: {_stringify(inspection_payload.get('blocked_reason'))}",
            f"- Failure Reason: {_stringify(inspection_payload.get('failure_reason'))}",
            f"- Retry Or Correction Context: {_stringify(inspection_payload.get('retry_or_correction_context'))}",
            "",
            "## Metadata",
            *_code_block(inspection_payload.get("metadata") or {}),
            "",
            "## Report Metadata",
            *_code_block(report_metadata),
        ]
    )
    return write_markdown_json_bundle(
        _inspection_reports_dir(config),
        title=f"work-item-inspection-report-{work_item_id}-{title}",
        markdown=markdown,
        payload=payload,
    )
