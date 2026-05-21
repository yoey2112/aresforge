from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.ready_issue_intake import (
    PROTECTED_ISSUE_NUMBER,
    fetch_issue_batch_for_planning,
    normalize_issue_for_planning,
)

BLOCKED_LABELS = {"aresforge-blocked"}
ATTENTION_LABELS = {"aresforge-needs-evidence", "aresforge-needs-docs"}
AUTOMERGE_LABEL = "aresforge-automerge"
READY_LABEL = "aresforge-ready"

PLANNING_STATES = [
    "queued",
    "planned",
    "ready",
    "blocked",
    "in_progress",
    "review_pending",
    "closeout_ready",
    "closed",
    "skipped",
]


@dataclass(frozen=True)
class QueueItem:
    queue_item_id: str
    issue_number: int
    issue_title: str
    issue_url: str | None
    labels: list[str]
    queue_state: str
    lifecycle_state: str
    readiness: str
    blocked_reasons: list[str]
    attention_reasons: list[str]
    recommended_next_step: str
    batch_group: str
    planning_state: str


def plan_agent_queue(
    config: AppConfig,
    *,
    issue_numbers: list[int] | None = None,
    issues_file: str | None = None,
) -> dict[str, Any]:
    issues, excluded_issues, intake_warnings = _load_issues(
        config,
        issue_numbers=issue_numbers,
        issues_file=issues_file,
    )
    queue_items: list[QueueItem] = []

    for issue in issues:
        number = issue.get("number")
        if not isinstance(number, int):
            continue
        if number == PROTECTED_ISSUE_NUMBER:
            excluded_issues.append({"number": number, "reason": "protected_issue"})
            continue
        queue_items.append(_build_queue_item(issue))

    queue_items.sort(key=lambda item: (item.readiness != "ready", item.issue_number))
    recommended_execution_order = [item.issue_number for item in queue_items]
    groups = _build_batch_groups(queue_items)

    planning_state_history = _derive_planning_state_history(queue_items)

    return {
        "command": "plan-agent-queue",
        "ok": True,
        "inspection_mode": "read_only",
        "input_mode": "issues_file" if issues_file else "github_read_only",
        "repo": f"{config.github_owner}/{config.github_repo}",
        "queue_contract_version": "m7-governance-aware-intake",
        "protected_issue": PROTECTED_ISSUE_NUMBER,
        "excluded_issues": sorted(
            excluded_issues,
            key=lambda item: (item.get("number", 0), str(item.get("reason", ""))),
        ),
        "intake_warnings": intake_warnings,
        "queue_items": [item.__dict__ for item in queue_items],
        "recommended_execution_order": recommended_execution_order,
        "batch_groups": groups,
        "governance_aware_intake_contract": {
            "issue_discovery": "Read-only GitHub issue list/view or deterministic local issues file.",
            "issue_classification": "Normalize metadata and classify implementation vs safety/historical references.",
            "queue_planning": "Map each issue to readiness, lifecycle, batch grouping, and recommended next action.",
            "persisted_planning_state": "Represent queue planning state and transition history as inspectable design data only.",
            "batch_closeout_planning": "Read-only readiness planning for parent/child issue groups; no closeout execution.",
            "closeout_execution": "Out of scope for this command and remains human-triggered with explicit gates.",
        },
        "persisted_planning_state_design": {
            "states": PLANNING_STATES,
            "current_state_by_work_item": [
                {
                    "work_item_identifier": item.queue_item_id,
                    "issue_number": item.issue_number,
                    "state": item.planning_state,
                    "read_only": True,
                }
                for item in queue_items
            ],
            "transition_history": planning_state_history,
            "transition_fields": [
                "work_item_identifier",
                "previous_state",
                "new_state",
                "timestamp",
                "reason",
                "actor_or_command_source",
                "read_only_evidence_references",
            ],
            "mutation_posture": "read_only_design_only",
        },
        "execution_planning_inputs": [
            "issue identity and title",
            "issue labels",
            "issue milestone and assignees",
            "issue body references with safety classification",
            "protected issue exclusion rule",
        ],
        "execution_planning_outputs": [
            "queue item state classification",
            "recommended execution order",
            "batch grouping suggestions",
            "human review and safe-stop prompts",
        ],
        "orchestration_boundaries": [
            "Read-only analysis only; no GitHub mutation.",
            "Queue transitions are recommendations, not autonomous execution.",
            "Final merge and issue closeout remain human-triggered.",
        ],
        "human_review_gates": [
            "Confirm issue scope before implementation.",
            "Confirm validation evidence before closeout readiness.",
            "Confirm documentation reconciliation before final closeout.",
        ],
    }


def _load_issues(
    config: AppConfig,
    *,
    issue_numbers: list[int] | None,
    issues_file: str | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    excluded_issues: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    if issues_file:
        payload = json.loads(Path(issues_file).read_text(encoding="utf-8"))
        issues = payload.get("issues") if isinstance(payload, dict) else None
        if isinstance(issues, list):
            normalized: list[dict[str, Any]] = []
            for item in issues:
                if isinstance(item, dict):
                    normalized.append(normalize_issue_for_planning(item))
            return normalized, excluded_issues, warnings
        return [], excluded_issues, warnings

    if issue_numbers:
        intake_payload = fetch_issue_batch_for_planning(config, issue_numbers)
        issues = intake_payload.get("issues") if isinstance(intake_payload.get("issues"), list) else []
        excluded = intake_payload.get("excluded_issues")
        if isinstance(excluded, list):
            excluded_issues.extend(item for item in excluded if isinstance(item, dict))
        intake_warnings = intake_payload.get("warnings")
        if isinstance(intake_warnings, list):
            warnings.extend(item for item in intake_warnings if isinstance(item, dict))
        return [item for item in issues if isinstance(item, dict)], excluded_issues, warnings

    return [], excluded_issues, warnings


def _build_queue_item(issue: dict[str, Any]) -> QueueItem:
    number = int(issue["number"])
    title = issue.get("title") if isinstance(issue.get("title"), str) else f"Issue {number}"
    url = issue.get("url") if isinstance(issue.get("url"), str) else None
    labels = _normalize_labels(issue.get("labels"))

    blocked_reasons: list[str] = []
    attention_reasons: list[str] = []
    if not _has_label(labels, READY_LABEL):
        blocked_reasons.append("missing_ready_label")
    if _has_any_label(labels, BLOCKED_LABELS):
        blocked_reasons.append("blocked_label_present")
    if not _has_label(labels, AUTOMERGE_LABEL):
        attention_reasons.append("missing_automerge_label")
    for marker in sorted(ATTENTION_LABELS):
        if _has_label(labels, marker):
            attention_reasons.append(marker.replace("aresforge-", ""))

    if blocked_reasons:
        readiness = "blocked"
        queue_state = "queue-blocked"
        lifecycle_state = "blocked"
        next_step = f"Resolve blocked reasons: {', '.join(blocked_reasons)}."
        batch_group = "blocked"
        planning_state = "blocked"
    elif attention_reasons:
        readiness = "attention_needed"
        queue_state = "queue-planning"
        lifecycle_state = "planning_ready"
        next_step = f"Resolve attention items: {', '.join(attention_reasons)}."
        batch_group = "follow_up"
        planning_state = "planned"
    else:
        readiness = "ready"
        queue_state = "queue-implementation"
        lifecycle_state = "implementation_ready"
        next_step = (
            f"Run issue workflow for #{number} on the active batch branch with validation gates."
        )
        batch_group = "ready_batch"
        planning_state = "ready"

    return QueueItem(
        queue_item_id=f"issue-{number}",
        issue_number=number,
        issue_title=title,
        issue_url=url,
        labels=labels,
        queue_state=queue_state,
        lifecycle_state=lifecycle_state,
        readiness=readiness,
        blocked_reasons=blocked_reasons,
        attention_reasons=attention_reasons,
        recommended_next_step=next_step,
        batch_group=batch_group,
        planning_state=planning_state,
    )


def _derive_planning_state_history(queue_items: list[QueueItem]) -> list[dict[str, Any]]:
    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    history: list[dict[str, Any]] = []
    for item in queue_items:
        history.append(
            {
                "work_item_identifier": item.queue_item_id,
                "previous_state": "queued",
                "new_state": item.planning_state,
                "timestamp": timestamp,
                "reason": f"Derived from read-only planning classification ({item.readiness}).",
                "actor_or_command_source": "plan-agent-queue",
                "read_only_evidence_references": [
                    f"issue:{item.issue_number}",
                    f"queue_state:{item.queue_state}",
                ],
            }
        )
    return history


def _build_batch_groups(items: list[QueueItem]) -> list[dict[str, Any]]:
    grouped: dict[str, list[int]] = {}
    for item in items:
        grouped.setdefault(item.batch_group, []).append(item.issue_number)
    return [
        {"group": key, "issue_numbers": sorted(values)}
        for key, values in sorted(grouped.items(), key=lambda pair: pair[0])
    ]


def _normalize_labels(raw_labels: Any) -> list[str]:
    labels: list[str] = []
    if isinstance(raw_labels, list):
        for item in raw_labels:
            if isinstance(item, str):
                labels.append(item)
            elif isinstance(item, dict) and isinstance(item.get("name"), str):
                labels.append(item["name"])
    return sorted(set(labels), key=lambda label: (label.lower(), label))


def _has_label(labels: list[str], target: str) -> bool:
    lowered = {item.lower() for item in labels}
    return target.lower() in lowered


def _has_any_label(labels: list[str], targets: set[str]) -> bool:
    lowered = {item.lower() for item in labels}
    return any(target.lower() in lowered for target in targets)
