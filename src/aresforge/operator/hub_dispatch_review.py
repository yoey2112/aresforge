from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig

DISPATCH_REVIEW_VERSION = "m114.1"

_BOUNDARY_CONFIRMATIONS = (
    "M114 Hub Dispatch Review Panel is local-only and read-only.",
    "M114 reads local artifact records for review only.",
    "M114 does not execute Codex, Codex CLI, Ollama, local LLMs, documentation agents, or external agents.",
    "M114 does not call GitHub APIs, gh, network services, issues, PRs, or workflows.",
    "M114 does not apply patches, mutate approvals, or mutate queue status.",
)

_ARTIFACT_SOURCES = (
    {
        "review_category": "manual_dispatch_preparation",
        "artifact_type": "manual_codex_dispatch_preparation",
        "directory": Path("artifacts/manual_codex_dispatch/prepared"),
        "record_markers": ("manual_codex_dispatch_preparation", "manual_codex_dispatch_run"),
    },
    {
        "review_category": "local_llm_advisory_artifact",
        "artifact_type": "local_llm_advisory_request",
        "directory": Path("artifacts/local_llm_advisory/requests"),
        "record_markers": ("local_llm_advisory_request",),
    },
    {
        "review_category": "patch_intake_record",
        "artifact_type": "patch_proposal_intake",
        "directory": Path("artifacts/patch_intake"),
        "record_markers": ("patch_proposal_intake",),
    },
    {
        "review_category": "parsed_dispatch_evidence",
        "artifact_type": "dispatch_result_evidence",
        "directory": Path("artifacts/dispatch_result_evidence"),
        "record_markers": ("dispatch_result_evidence",),
    },
    {
        "review_category": "queue_completion_recommendation",
        "artifact_type": "queue_completion_recommendation",
        "directory": Path("artifacts/queue_completion_recommendations"),
        "record_markers": ("queue_completion_recommendation",),
    },
)


def build_hub_dispatch_review_panel(
    config: AppConfig,
    *,
    item_id: str | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    normalized_item_id = str(item_id or "").strip()
    normalized_limit = limit if isinstance(limit, int) and limit > 0 else 50
    warnings: list[str] = []
    records: list[dict[str, Any]] = []

    for source in _ARTIFACT_SOURCES:
        records.extend(_records_from_source(config.repo_root, source, normalized_item_id, warnings))

    records.sort(key=lambda record: record.get("updated_at") or record.get("artifact_path") or "", reverse=True)
    limited_records = records[:normalized_limit]
    categories = _category_summary(limited_records)
    return {
        "ok": True,
        "panel_type": "hub_dispatch_review_panel",
        "panel_version": DISPATCH_REVIEW_VERSION,
        "generated_at": _now_iso(),
        "local_only": True,
        "read_only": True,
        "execution_allowed": False,
        "execution_performed": False,
        "queue_mutation_performed": False,
        "network_execution_performed": False,
        "patch_application_allowed": False,
        "patch_application_performed": False,
        "filters": {
            "item_id": normalized_item_id,
            "limit": normalized_limit,
        },
        "source_directories": [
            {
                "review_category": str(source["review_category"]),
                "artifact_type": str(source["artifact_type"]),
                "path": str((config.repo_root / source["directory"]).resolve()),
                "exists": (config.repo_root / source["directory"]).exists(),
            }
            for source in _ARTIFACT_SOURCES
        ],
        "record_count": len(limited_records),
        "categories": categories,
        "records": limited_records,
        "operator_checklist": _operator_checklist(),
        "warnings": warnings,
        "next_safe_action": _next_safe_action(limited_records),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }


def _records_from_source(
    repo_root: Path,
    source: dict[str, object],
    item_id: str,
    warnings: list[str],
) -> list[dict[str, Any]]:
    directory = (repo_root / Path(str(source["directory"]))).resolve()
    if not directory.exists():
        return []
    records: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.json")):
        record = _read_json(path, warnings)
        if not record:
            continue
        if item_id and str(record.get("item_id", "")).strip() != item_id:
            continue
        normalized = _normalize_record(path, record, source)
        if normalized:
            records.append(normalized)
    return records


def _normalize_record(path: Path, record: dict[str, Any], source: dict[str, object]) -> dict[str, Any]:
    artifact_type = _artifact_type(record) or str(source["artifact_type"])
    milestone = str(record.get("milestone", "")).strip() or _milestone_from_item_id(str(record.get("item_id", "")))
    blocked = bool(record.get("blocked", False))
    checklist = _record_checklist(record, artifact_type)
    return {
        "review_category": str(source["review_category"]),
        "artifact_type": artifact_type,
        "artifact_path": str(path),
        "artifact_exists": path.exists(),
        "item_id": str(record.get("item_id", "")).strip(),
        "title": str(record.get("title", "")).strip(),
        "project_id": str(record.get("project_id", "")).strip(),
        "milestone": milestone,
        "blocked": blocked,
        "blocked_reasons": _list(record.get("blocked_reasons")),
        "status": _status(record),
        "next_safe_action": str(record.get("next_safe_action", "")).strip(),
        "operator_checklist": checklist,
        "local_only": bool(record.get("local_only", True)),
        "execution_allowed": bool(record.get("execution_allowed", False)),
        "execution_performed": bool(record.get("execution_performed", False)),
        "patch_application_allowed": bool(record.get("patch_application_allowed", False)),
        "patch_application_performed": bool(record.get("patch_application_performed", False)),
        "operator_review_required": _operator_review_required(record),
        "updated_at": _updated_at(record),
    }


def _artifact_type(record: dict[str, Any]) -> str:
    for field in (
        "artifact_type",
        "preparation_record_type",
        "intake_record_type",
        "evidence_record_type",
        "recommendation_record_type",
        "record_type",
    ):
        value = str(record.get(field, "")).strip()
        if value:
            return value
    return ""


def _status(record: dict[str, Any]) -> str:
    if record.get("recommended_complete") is True:
        return "recommended_complete"
    if record.get("accepted_for_review") is True:
        return "accepted_for_review"
    if record.get("parsed") is True:
        return "parsed"
    if record.get("generated") is True:
        return "generated"
    if record.get("prepared") is True:
        return "prepared"
    if record.get("blocked") is True:
        return "blocked"
    return "available"


def _operator_review_required(record: dict[str, Any]) -> bool:
    for field in ("operator_review_required", "human_review_required", "operator_decision_required"):
        if field in record:
            return bool(record.get(field))
    return True


def _record_checklist(record: dict[str, Any], artifact_type: str) -> list[str]:
    checklist = _list(record.get("operator_review_checklist"))
    if checklist:
        return checklist
    if artifact_type == "queue_completion_recommendation":
        return [
            "Review recommended_complete, blocked_reasons, missing_evidence, and confidence.",
            "Complete the queue item only through explicit local queue lifecycle controls.",
        ]
    if artifact_type == "dispatch_result_evidence":
        return [
            "Review files changed, tests, smoke checks, warnings/blockers, and commit hash.",
            "Use evidence only as input for human review or recommendation tooling.",
        ]
    if artifact_type == "patch_proposal_intake":
        return [
            "Review approval status and patch summary.",
            "Do not apply patches from this panel.",
        ]
    if artifact_type == "local_llm_advisory_request":
        return [
            "Review advisory prompt, source documents, and expected response shape.",
            "Run local LLMs only through a separately approved operator gate.",
        ]
    return [
        "Review local artifact metadata before any manual operator action.",
        "Confirm no execution or mutation is implied by this review record.",
    ]


def _category_summary(records: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    summary: dict[str, dict[str, int]] = {}
    for record in records:
        category = str(record.get("review_category", "unknown"))
        bucket = summary.setdefault(category, {"count": 0, "blocked": 0})
        bucket["count"] += 1
        if record.get("blocked"):
            bucket["blocked"] += 1
    return dict(sorted(summary.items()))


def _operator_checklist() -> list[str]:
    return [
        "Confirm artifact type, item id, milestone, blocked status, and next safe action.",
        "Use this panel for local review only; it does not execute Codex, LLMs, agents, GitHub, or patches.",
        "Use explicit operator CLI or Hub lifecycle controls for any later local-only mutation.",
    ]


def _next_safe_action(records: list[dict[str, Any]]) -> str:
    if not records:
        return "Generate or parse local dispatch review artifacts, then refresh this read-only panel."
    return "Review local dispatch artifacts and recommendations before any explicit operator-gated action."


def _read_json(path: Path, warnings: list[str]) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        warnings.append(f"Could not read dispatch review artifact {path}: {exc}")
        return {}
    return raw if isinstance(raw, dict) else {}


def _list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if value in (None, ""):
        return []
    return [str(value).strip()]


def _updated_at(record: dict[str, Any]) -> str:
    for field in ("updated_at", "recorded_at", "generated_at", "created_at", "captured_at"):
        value = str(record.get(field, "")).strip()
        if value:
            return value
    return ""


def _milestone_from_item_id(item_id: str) -> str:
    text = item_id.strip()
    return text.split("-", 1)[0].lower() if text.lower().startswith("m") and "-" in text else ""


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
