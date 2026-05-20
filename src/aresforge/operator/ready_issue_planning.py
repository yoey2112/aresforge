from __future__ import annotations

from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.ready_issue_intake import (
    PROTECTED_ISSUE_NUMBER,
    READY_TRIGGER_LABEL,
    fetch_issue_details,
)


_DOC_SYNC_KEYWORDS = (
    "documentation sync",
    "doc sync",
    "source-of-truth sync",
    "documentation-sync",
)
_DOC_KEYWORDS = (
    "documentation",
    "docs",
    "source of truth",
    "source-of-truth",
    "freshness",
)
_QA_KEYWORDS = (
    "qa",
    "review",
    "verification",
    "validate",
    "validation",
    "test",
    "testing",
    "regression",
)
_MODEL_ROUTING_KEYWORDS = (
    "model routing",
    "routing strategy",
    "model strategy",
    "model tier",
    "llm",
    "codex",
    "copilot",
)
_RELEASE_KEYWORDS = (
    "release",
    "readiness",
    "package",
    "packaging",
    "version",
    "changelog",
)
_COMPLEXITY_KEYWORDS = (
    "architecture",
    "multi-step",
    "multi step",
    "multi-document",
    "multi document",
    "cross-document",
    "cross document",
    "complex",
    "multi-file",
    "multi file",
    "refactor",
)

_PAID_APPROVAL_LABELS = {
    "paid-api-approved",
    "paid-api-explicit",
    "paid-api-ok",
}
_CODEX_APPROVAL_LABELS = {
    "codex-approved",
}


def plan_ready_issue(config: AppConfig, issue_number: int) -> dict[str, Any]:
    if issue_number == PROTECTED_ISSUE_NUMBER:
        return _blocked_payload(
            issue_number=issue_number,
            issue_title=None,
            issue_url=None,
            labels=[],
            blocked_reason="protected_issue",
        )

    issue_payload = fetch_issue_details(config, issue_number)
    if not issue_payload.get("ok"):
        return _blocked_payload(
            issue_number=issue_number,
            issue_title=None,
            issue_url=None,
            labels=[],
            blocked_reason=issue_payload.get("error", "issue_lookup_failed"),
        )

    issue = issue_payload["issue"]
    title = issue.get("title")
    body = issue.get("body")
    labels = _normalize_labels(issue.get("labels"))
    state = issue.get("state")

    blocked_reason = None
    if not _label_present(labels, READY_TRIGGER_LABEL):
        blocked_reason = f"missing_ready_label:{READY_TRIGGER_LABEL}"
    elif isinstance(state, str) and state.upper() != "OPEN":
        blocked_reason = f"issue_not_open:{state}"

    routing = _route_issue(title, body, labels)
    model_routing = _select_model_tier(
        category=routing["category"],
        title=title,
        body=body,
        labels=labels,
        blocked=blocked_reason is not None,
    )

    return _build_payload(
        issue_number=issue.get("number", issue_number),
        issue_title=title,
        issue_url=issue.get("url"),
        labels=labels,
        blocked_reason=blocked_reason,
        selected_primary_agent=routing["primary_agent"],
        selected_qa_agent="qa-agent",
        selected_documentation_agent="documentation-agent",
        selected_model_tier=model_routing["selected_model_tier"],
        model_routing_reason=model_routing["model_routing_reason"],
        lower_tiers_sufficient=model_routing["lower_tiers_sufficient"],
        codex_justified=model_routing["codex_justified"],
        paid_use_blocked=model_routing["paid_use_blocked"],
        confidence=routing["confidence"],
        recommended_next_command=_recommended_next_command(
            issue_number=issue.get("number", issue_number),
            issue_title=title,
            blocked=blocked_reason is not None,
        ),
    )


def _build_payload(
    *,
    issue_number: int,
    issue_title: str | None,
    issue_url: str | None,
    labels: list[str],
    blocked_reason: str | None,
    selected_primary_agent: str,
    selected_qa_agent: str,
    selected_documentation_agent: str,
    selected_model_tier: str,
    model_routing_reason: str,
    lower_tiers_sufficient: bool,
    codex_justified: bool,
    paid_use_blocked: bool,
    confidence: str,
    recommended_next_command: str,
) -> dict[str, Any]:
    blocked = blocked_reason is not None
    return {
        "issue_number": issue_number,
        "issue_title": issue_title,
        "issue_url": issue_url,
        "labels": labels,
        "automation_eligible": not blocked,
        "selected_primary_agent": selected_primary_agent,
        "selected_qa_agent": selected_qa_agent,
        "selected_documentation_agent": selected_documentation_agent,
        "selected_model_tier": selected_model_tier,
        "model_routing_reason": model_routing_reason,
        "lower_tiers_sufficient": lower_tiers_sufficient,
        "codex_justified": codex_justified,
        "paid_use_blocked": paid_use_blocked,
        "confidence": confidence,
        "blocked": blocked,
        "blocked_reason": blocked_reason,
        "recommended_next_command": recommended_next_command,
    }


def _blocked_payload(
    *,
    issue_number: int,
    issue_title: str | None,
    issue_url: str | None,
    labels: list[str],
    blocked_reason: str,
) -> dict[str, Any]:
    return _build_payload(
        issue_number=issue_number,
        issue_title=issue_title,
        issue_url=issue_url,
        labels=_normalize_labels(labels),
        blocked_reason=blocked_reason,
        selected_primary_agent="implementation-agent",
        selected_qa_agent="qa-agent",
        selected_documentation_agent="documentation-agent",
        selected_model_tier="local",
        model_routing_reason="Issue is blocked; defaulting to local tier per local-first policy.",
        lower_tiers_sufficient=True,
        codex_justified=False,
        paid_use_blocked=True,
        confidence="low",
        recommended_next_command=_recommended_next_command(
            issue_number=issue_number,
            issue_title=issue_title,
            blocked=True,
        ),
    )


def _route_issue(title: str | None, body: str | None, labels: list[str]) -> dict[str, str]:
    text = _combined_text(title, body, labels)
    label_text = " ".join(labels)

    if _text_contains_any(text, _MODEL_ROUTING_KEYWORDS) or "model-routing" in label_text:
        return {
            "primary_agent": "model-routing-agent",
            "category": "model_routing",
            "confidence": _confidence_from_labels(labels, "model"),
        }

    if _text_contains_any(text, _RELEASE_KEYWORDS) or "release" in label_text:
        return {
            "primary_agent": "release-readiness-agent",
            "category": "release",
            "confidence": _confidence_from_labels(labels, "release"),
        }

    if _text_contains_any(text, _DOC_SYNC_KEYWORDS) or "documentation-sync" in label_text:
        return {
            "primary_agent": "documentation-sync-agent",
            "category": "documentation_sync",
            "confidence": _confidence_from_labels(labels, "documentation"),
        }

    if _text_contains_any(text, _DOC_KEYWORDS) or "documentation" in label_text or "docs" in label_text:
        return {
            "primary_agent": "documentation-agent",
            "category": "documentation",
            "confidence": _confidence_from_labels(labels, "documentation"),
        }

    if _text_contains_any(text, _QA_KEYWORDS) or "qa" in label_text or "validation" in label_text:
        return {
            "primary_agent": "qa-agent",
            "category": "qa",
            "confidence": _confidence_from_labels(labels, "qa"),
        }

    return {
        "primary_agent": "implementation-agent",
        "category": "implementation",
        "confidence": "medium",
    }


def _select_model_tier(
    *,
    category: str,
    title: str | None,
    body: str | None,
    labels: list[str],
    blocked: bool,
) -> dict[str, Any]:
    if blocked:
        return {
            "selected_model_tier": "local",
            "model_routing_reason": "Issue is blocked; defaulting to local tier per local-first policy.",
            "lower_tiers_sufficient": True,
            "codex_justified": False,
            "paid_use_blocked": True,
        }

    label_set = {label.lower() for label in labels}
    if label_set.intersection(_PAID_APPROVAL_LABELS):
        return {
            "selected_model_tier": "paid-api-explicit-only",
            "model_routing_reason": "Paid API usage explicitly approved for this issue.",
            "lower_tiers_sufficient": False,
            "codex_justified": False,
            "paid_use_blocked": False,
        }

    if label_set.intersection(_CODEX_APPROVAL_LABELS):
        return {
            "selected_model_tier": "codex",
            "model_routing_reason": "Codex use explicitly approved for agentic implementation scope.",
            "lower_tiers_sufficient": False,
            "codex_justified": True,
            "paid_use_blocked": True,
        }

    if category in {"documentation", "documentation_sync"}:
        return {
            "selected_model_tier": "local",
            "model_routing_reason": "Local tier is sufficient for documentation-focused work.",
            "lower_tiers_sufficient": True,
            "codex_justified": False,
            "paid_use_blocked": True,
        }

    if category in {"model_routing", "release"} or _text_contains_any(
        _combined_text(title, body, labels), _COMPLEXITY_KEYWORDS
    ):
        return {
            "selected_model_tier": "copilot",
            "model_routing_reason": "Copilot tier selected for complex multi-document or planning scope.",
            "lower_tiers_sufficient": False,
            "codex_justified": False,
            "paid_use_blocked": True,
        }

    return {
        "selected_model_tier": "local",
        "model_routing_reason": "Local-first default for routine scope.",
        "lower_tiers_sufficient": True,
        "codex_justified": False,
        "paid_use_blocked": True,
    }


def _recommended_next_command(*, issue_number: int, issue_title: str | None, blocked: bool) -> str:
    if blocked:
        return "python -m aresforge list-ready-issues"
    safe_title = issue_title or f"Issue {issue_number}"
    return (
        "python -m aresforge prepare-codex-handoff "
        f"--title \"{safe_title} handoff\" "
        f"--summary \"{safe_title}\" "
        "--requested-output \"Prepare a human-reviewable execution handoff.\""
    )


def _combined_text(title: str | None, body: str | None, labels: list[str]) -> str:
    parts = [title or "", body or "", " ".join(labels)]
    return " ".join(parts).lower()


def _text_contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword in text for keyword in keywords)


def _normalize_labels(labels: list[str] | None) -> list[str]:
    if not labels:
        return []
    normalized = [label for label in labels if isinstance(label, str)]
    return sorted(set(normalized), key=lambda label: (label.lower(), label))


def _label_present(labels: list[str], target: str) -> bool:
    lowered = {label.lower() for label in labels}
    return target.lower() in lowered


def _confidence_from_labels(labels: list[str], hint: str) -> str:
    lowered = {label.lower() for label in labels}
    if any(hint in label for label in lowered):
        return "high"
    return "medium"
