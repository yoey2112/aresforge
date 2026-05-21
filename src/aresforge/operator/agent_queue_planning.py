from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.ready_issue_intake import (
    PROTECTED_ISSUE_NUMBER,
    fetch_issue_details,
    list_ready_issues,
)

BLOCKED_LABELS = {"aresforge-blocked"}
ATTENTION_LABELS = {"aresforge-needs-evidence", "aresforge-needs-docs"}
AUTOMERGE_LABEL = "aresforge-automerge"
READY_LABEL = "aresforge-ready"


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


def plan_agent_queue(
    config: AppConfig,
    *,
    issue_numbers: list[int] | None = None,
    issues_file: str | None = None,
) -> dict[str, Any]:
    issues = _load_issues(config, issue_numbers=issue_numbers, issues_file=issues_file)
    queue_items: list[QueueItem] = []
    excluded_issues: list[dict[str, Any]] = []

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

    return {
        "command": "plan-agent-queue",
        "ok": True,
        "inspection_mode": "read_only",
        "input_mode": "issues_file" if issues_file else "github_read_only",
        "repo": f"{config.github_owner}/{config.github_repo}",
        "queue_contract_version": "m6-mvp",
        "protected_issue": PROTECTED_ISSUE_NUMBER,
        "excluded_issues": excluded_issues,
        "queue_items": [item.__dict__ for item in queue_items],
        "recommended_execution_order": recommended_execution_order,
        "batch_groups": groups,
        "execution_planning_inputs": [
            "issue identity and title",
            "issue labels",
            "ready/blocking/attention indicators",
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
) -> list[dict[str, Any]]:
    if issues_file:
        payload = json.loads(Path(issues_file).read_text(encoding="utf-8"))
        issues = payload.get("issues") if isinstance(payload, dict) else None
        if isinstance(issues, list):
            return [item for item in issues if isinstance(item, dict)]
        return []

    if issue_numbers:
        loaded: list[dict[str, Any]] = []
        for number in issue_numbers:
            details = fetch_issue_details(config, number)
            issue = details.get("issue")
            if isinstance(issue, dict):
                loaded.append(issue)
        return loaded

    listing = list_ready_issues(config)
    listed = listing.get("issues")
    if not isinstance(listed, list):
        return []
    return [item for item in listed if isinstance(item, dict)]


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
    elif attention_reasons:
        readiness = "attention_needed"
        queue_state = "queue-planning"
        lifecycle_state = "planning_ready"
        next_step = f"Resolve attention items: {', '.join(attention_reasons)}."
        batch_group = "follow_up"
    else:
        readiness = "ready"
        queue_state = "queue-implementation"
        lifecycle_state = "implementation_ready"
        next_step = (
            f"Run issue workflow for #{number} on the active batch branch with validation gates."
        )
        batch_group = "ready_batch"

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
    )


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
