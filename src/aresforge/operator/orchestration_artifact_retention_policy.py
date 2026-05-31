from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.durable_orchestration_run_store import read_orchestration_run_store
from aresforge.operator.machine_safety_gate_engine import evaluate_machine_safety_gates

COMMAND_NAME = "inspect-orchestration-artifact-retention"
RECORD_TYPE = "orchestration_artifact_retention_policy_v1"
POLICY_VERSION = "m156.1"
DEFAULT_ITEM_ID = "m156-orchestration-artifact-retention-policy"
DEFAULT_PROJECT_ID = "aresforge"

_CATEGORY_POLICIES: tuple[dict[str, Any], ...] = (
    {
        "category_id": "durable_run_store",
        "artifact_type": "durable_orchestration_run_store",
        "description": "Durable orchestration run-history index and recovery source of truth.",
        "expected_folders": [".aresforge/orchestrator"],
        "patterns": ["run_history.json"],
        "retention_days": 3650,
        "stale_after_days": 365,
        "cleanup_eligible": False,
        "requires_durable_index_reference": False,
    },
    {
        "category_id": "orchestration_runs",
        "artifact_type": "multi_agent_orchestration_run",
        "description": "Legacy and current multi-agent orchestration run artifacts.",
        "expected_folders": ["artifacts/multi-agent-orchestration"],
        "patterns": ["**/*.json"],
        "retention_days": 180,
        "stale_after_days": 90,
        "cleanup_eligible": True,
        "requires_durable_index_reference": True,
    },
    {
        "category_id": "orchestration_run_monitor_reports",
        "artifact_type": "hub_orchestration_run_monitor_report",
        "description": "Optional operator-written Hub orchestration monitor reports.",
        "expected_folders": [".aresforge/orchestrator/run_monitor"],
        "patterns": ["**/*.json"],
        "retention_days": 90,
        "stale_after_days": 30,
        "cleanup_eligible": True,
        "requires_durable_index_reference": False,
    },
    {
        "category_id": "orchestration_resume_plans",
        "artifact_type": "orchestration_resume_plan",
        "description": "Optional resume-from-failure planning artifacts.",
        "expected_folders": [".aresforge/orchestrator/resume_plans"],
        "patterns": ["**/*.json"],
        "retention_days": 180,
        "stale_after_days": 60,
        "cleanup_eligible": True,
        "requires_durable_index_reference": False,
    },
    {
        "category_id": "normalized_step_results",
        "artifact_type": "normalized_agent_step_result",
        "description": "Optional normalized step-result evidence for orchestrator evaluation.",
        "expected_folders": [".aresforge/orchestrator/step_results"],
        "patterns": ["**/*.json"],
        "retention_days": 180,
        "stale_after_days": 60,
        "cleanup_eligible": True,
        "requires_durable_index_reference": True,
    },
    {
        "category_id": "codex_loop_evidence",
        "artifact_type": "codex_loop_evidence",
        "description": "Dry-run and low-risk real Codex loop orchestration evidence.",
        "expected_folders": [
            ".aresforge/codex_loop_dry_runs",
            ".aresforge/codex_loop_real_runs",
            ".aresforge/codex_dispatch",
            "artifacts/codex_dispatch",
        ],
        "patterns": ["**/*.json", "**/*.txt", "**/*.log"],
        "retention_days": 120,
        "stale_after_days": 45,
        "cleanup_eligible": True,
        "requires_durable_index_reference": False,
    },
    {
        "category_id": "validation_evidence",
        "artifact_type": "orchestration_validation_evidence",
        "description": "Codex result ingestion, validation, and completion recommendation evidence.",
        "expected_folders": ["artifacts/codex_result_ingestion"],
        "patterns": ["**/*.json", "**/*.txt", "**/*.log"],
        "retention_days": 120,
        "stale_after_days": 45,
        "cleanup_eligible": True,
        "requires_durable_index_reference": False,
    },
    {
        "category_id": "documentation_agent_evidence",
        "artifact_type": "documentation_agent_evidence",
        "description": "Documentation-agent dry-run/proposal evidence related to orchestration workflows.",
        "expected_folders": ["artifacts/documentation_agent"],
        "patterns": ["**/*.json", "**/*.md", "**/*.patch", "**/*.txt"],
        "retention_days": 180,
        "stale_after_days": 90,
        "cleanup_eligible": True,
        "requires_durable_index_reference": False,
    },
    {
        "category_id": "autonomy_reports",
        "artifact_type": "autonomy_or_orchestration_report",
        "description": "Sprint closeout, autonomy readiness, and orchestration report artifacts.",
        "expected_folders": [".aresforge/autonomy_readiness_reports"],
        "patterns": ["**/*.json", "**/*.md"],
        "retention_days": 365,
        "stale_after_days": 180,
        "cleanup_eligible": False,
        "requires_durable_index_reference": False,
    },
)

_BOUNDARY_CONFIRMATIONS: tuple[str, ...] = (
    "M156 indexes local orchestration artifacts and reports retention metadata only.",
    "M156 may generate a dry-run cleanup plan, but it never deletes, moves, truncates, or rewrites artifacts automatically.",
    "Orphan detection compares durable run-store references with expected orchestration artifact folders.",
    "Retention recommendations are advisory and require a separate explicit operator action before any cleanup.",
)


def inspect_orchestration_artifact_retention(
    config: AppConfig,
    *,
    project_id: str = DEFAULT_PROJECT_ID,
    item_id: str | None = None,
    history_path: str | Path | None = None,
    queue_path: str | Path | None = None,
    output: str | Path | None = None,
    force: bool = False,
    output_format: str = "json",
) -> dict[str, Any]:
    fmt = _text(output_format).lower() or "json"
    if fmt != "json":
        return _error("invalid_format", {"format": output_format, "supported_formats": ["json"]})

    normalized_project_id = _text(project_id) or DEFAULT_PROJECT_ID
    normalized_item_id = _text(item_id) or DEFAULT_ITEM_ID
    gate_payload = _gate_payload(config, item_id=normalized_item_id, queue_path=queue_path)
    gate_summary = _gate_summary(gate_payload)
    store = read_orchestration_run_store(
        config,
        store_path=history_path,
        bootstrap_missing=False,
        project_id=normalized_project_id,
    )
    store_records = [
        record for record in _dicts(store.get("records")) if _text(record.get("project_id")) == normalized_project_id
    ]
    referenced_paths = _referenced_artifact_paths(config.repo_root, store_records)
    category_summaries = [
        _category_summary(config, policy=policy, referenced_paths=referenced_paths) for policy in _CATEGORY_POLICIES
    ]
    artifact_count_summary = _artifact_count_summary(category_summaries)
    orphan_artifacts = [
        artifact
        for category in category_summaries
        for artifact in _dicts(category.get("orphan_artifacts"))
    ]
    stale_artifacts = [
        artifact
        for category in category_summaries
        for artifact in _dicts(category.get("stale_artifacts"))
    ]
    blocked_reasons = _dedupe([*_list(gate_payload.get("blocked_reasons")), *_store_blockers(store)])
    warnings = _dedupe(
        [
            *_store_warnings(store),
            *_retention_warnings(category_summaries=category_summaries),
        ]
    )
    blocked = bool(blocked_reasons)
    recommendations = _retention_recommendations(category_summaries)
    dry_run_cleanup_plan = _dry_run_cleanup_plan(category_summaries)

    payload: dict[str, Any] = {
        "record_type": RECORD_TYPE,
        "artifact_type": RECORD_TYPE,
        "policy_version": POLICY_VERSION,
        "generated": True,
        "generated_at": _now_iso(),
        "project_id": normalized_project_id,
        "item_id": normalized_item_id,
        "run_id": "",
        "status": _status(blocked=blocked, warnings=warnings, dry_run_cleanup_plan=dry_run_cleanup_plan),
        "blocked": blocked,
        "blocked_reasons": blocked_reasons,
        "warnings": warnings,
        "machine_gates_checked": [gate_summary],
        "machine_gates_passed": bool(gate_summary.get("passed")) and not blocked,
        "autonomy_profile": "local_orchestration_artifact_retention_inspection",
        "artifacts_created": [],
        "mutation_performed": False,
        "queue_mutation_performed": False,
        "external_execution_performed": False,
        "codex_execution_performed": False,
        "model_execution_performed": False,
        "github_execution_performed": False,
        "patch_application_performed": False,
        "local_only": True,
        "next_safe_action": _next_safe_action(blocked=blocked, cleanup_plan=dry_run_cleanup_plan, warnings=warnings),
        "retention_policy": {
            "cleanup_mode": "dry_run_plan_only",
            "automatic_deletion_allowed": False,
            "policy_categories": [
                {
                    "category_id": _text(policy.get("category_id")),
                    "artifact_type": _text(policy.get("artifact_type")),
                    "expected_folders": _list(policy.get("expected_folders")),
                    "retention_days": _int(policy.get("retention_days")),
                    "stale_after_days": _int(policy.get("stale_after_days")),
                    "cleanup_eligible": bool(policy.get("cleanup_eligible")),
                    "requires_durable_index_reference": bool(policy.get("requires_durable_index_reference")),
                }
                for policy in _CATEGORY_POLICIES
            ],
        },
        "expected_folders": _expected_folder_status(config, _CATEGORY_POLICIES),
        "category_summaries": category_summaries,
        "artifact_count_summary": artifact_count_summary,
        "orphan_detection": {
            "enabled": True,
            "durable_store_path": _text(store.get("store_path")),
            "durable_store_record_count": len(store_records),
            "referenced_artifact_path_count": len(referenced_paths),
            "orphan_count": len(orphan_artifacts),
            "orphan_artifacts": orphan_artifacts,
        },
        "stale_artifact_warnings": stale_artifacts,
        "retention_recommendations": recommendations,
        "dry_run_cleanup_plan": dry_run_cleanup_plan,
        "cleanup_plan_generated": bool(dry_run_cleanup_plan),
        "cleanup_performed": False,
        "artifact_deletion_performed": False,
        "queue_mutation_performed": False,
        "retention_index": _retention_index(category_summaries),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }
    return _emit_or_write(config=config, payload=payload, output=output, force=force)


def _category_summary(config: AppConfig, *, policy: dict[str, Any], referenced_paths: set[str]) -> dict[str, Any]:
    files = _discover_files(config.repo_root, policy)
    stale_after_days = _int(policy.get("stale_after_days"))
    cleanup_eligible = bool(policy.get("cleanup_eligible"))
    requires_reference = bool(policy.get("requires_durable_index_reference"))
    artifacts = [_artifact_summary(config.repo_root, path, category_id=_text(policy.get("category_id"))) for path in files]
    stale_artifacts = [artifact for artifact in artifacts if _int(artifact.get("age_days")) > stale_after_days]
    orphan_artifacts = [
        artifact
        for artifact in artifacts
        if requires_reference and _canonical_path(config.repo_root, artifact.get("artifact_path")) not in referenced_paths
    ]
    missing_folders = [
        folder for folder in _list(policy.get("expected_folders")) if not _resolve(config.repo_root, folder).exists()
    ]
    retention_status = _category_status(
        missing_folders=missing_folders,
        file_count=len(artifacts),
        stale_count=len(stale_artifacts),
        orphan_count=len(orphan_artifacts),
    )
    return {
        "category_id": _text(policy.get("category_id")),
        "artifact_type": _text(policy.get("artifact_type")),
        "description": _text(policy.get("description")),
        "retention_status": retention_status,
        "expected_folders": _list(policy.get("expected_folders")),
        "expected_file_patterns": _list(policy.get("patterns")),
        "retention_days": _int(policy.get("retention_days")),
        "stale_after_days": stale_after_days,
        "cleanup_eligible": cleanup_eligible,
        "requires_durable_index_reference": requires_reference,
        "file_count": len(artifacts),
        "total_bytes": sum(_int(artifact.get("size_bytes")) for artifact in artifacts),
        "referenced_count": len(artifacts) - len(orphan_artifacts) if requires_reference else 0,
        "orphan_count": len(orphan_artifacts),
        "stale_count": len(stale_artifacts),
        "missing_folders": missing_folders,
        "latest_artifact_at": _latest_artifact_at(artifacts),
        "artifacts": artifacts,
        "orphan_artifacts": orphan_artifacts,
        "stale_artifacts": stale_artifacts,
        "recommendation": _category_recommendation(
            status=retention_status,
            cleanup_eligible=cleanup_eligible,
            orphan_count=len(orphan_artifacts),
            stale_count=len(stale_artifacts),
        ),
    }


def _discover_files(repo_root: Path, policy: dict[str, Any]) -> list[Path]:
    files: dict[str, Path] = {}
    for folder in _list(policy.get("expected_folders")):
        root = _resolve(repo_root, folder)
        if not root.exists():
            continue
        if root.is_file():
            files[str(root)] = root
            continue
        for pattern in _list(policy.get("patterns")):
            try:
                matches = root.glob(pattern)
                for match in matches:
                    if match.is_file():
                        files[str(match.resolve())] = match.resolve()
            except OSError:
                continue
    return [files[key] for key in sorted(files)]


def _artifact_summary(repo_root: Path, path: Path, *, category_id: str) -> dict[str, Any]:
    stat = path.stat()
    modified_at = datetime.fromtimestamp(stat.st_mtime, UTC).replace(microsecond=0)
    age_days = max(0, int((_now() - modified_at).total_seconds() // 86400))
    return {
        "artifact_type": category_id,
        "artifact_path": _relative_path(repo_root, path),
        "absolute_path": str(path.resolve()),
        "size_bytes": stat.st_size,
        "modified_at": modified_at.isoformat().replace("+00:00", "Z"),
        "age_days": age_days,
        "retention_status": "indexed",
    }


def _referenced_artifact_paths(repo_root: Path, records: list[dict[str, Any]]) -> set[str]:
    referenced: set[str] = set()
    for record in records:
        for value in [_text(record.get("artifact_path")), *_list(record.get("artifacts_created"))]:
            canonical = _canonical_path(repo_root, value)
            if canonical:
                referenced.add(canonical)
    return referenced


def _canonical_path(repo_root: Path, value: Any) -> str:
    text = _text(value)
    if not text:
        return ""
    path = Path(text)
    if not path.is_absolute():
        path = repo_root / path
    try:
        return str(path.resolve())
    except OSError:
        return str(path)


def _artifact_count_summary(category_summaries: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "category_count": len(category_summaries),
        "total_artifact_count": sum(_int(category.get("file_count")) for category in category_summaries),
        "total_bytes": sum(_int(category.get("total_bytes")) for category in category_summaries),
        "orphan_count": sum(_int(category.get("orphan_count")) for category in category_summaries),
        "stale_count": sum(_int(category.get("stale_count")) for category in category_summaries),
        "missing_folder_count": sum(len(_list(category.get("missing_folders"))) for category in category_summaries),
        "empty_category_count": sum(1 for category in category_summaries if _int(category.get("file_count")) == 0),
        "by_category": [
            {
                "category_id": _text(category.get("category_id")),
                "artifact_type": _text(category.get("artifact_type")),
                "retention_status": _text(category.get("retention_status")),
                "file_count": _int(category.get("file_count")),
                "orphan_count": _int(category.get("orphan_count")),
                "stale_count": _int(category.get("stale_count")),
            }
            for category in category_summaries
        ],
    }


def _retention_recommendations(category_summaries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    recommendations: list[dict[str, Any]] = []
    for category in category_summaries:
        category_id = _text(category.get("category_id"))
        if _list(category.get("missing_folders")):
            recommendations.append(
                {
                    "category_id": category_id,
                    "status": "missing_expected_folder",
                    "recommendation": "Create the expected folder only when a future command needs to write this artifact category.",
                    "mutation_performed": False,
                }
            )
        if _int(category.get("orphan_count")):
            recommendations.append(
                {
                    "category_id": category_id,
                    "status": "orphan_review_required",
                    "recommendation": "Review orphan artifacts against durable run history before any manual cleanup.",
                    "mutation_performed": False,
                }
            )
        if _int(category.get("stale_count")):
            recommendations.append(
                {
                    "category_id": category_id,
                    "status": "stale_review_required",
                    "recommendation": "Review stale artifacts and archive or delete only through an explicit operator-approved cleanup flow.",
                    "mutation_performed": False,
                }
            )
    return recommendations


def _dry_run_cleanup_plan(category_summaries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    plan: list[dict[str, Any]] = []
    for category in category_summaries:
        if not bool(category.get("cleanup_eligible")):
            continue
        seen: set[str] = set()
        for reason, artifacts in (
            ("orphan_artifact", _dicts(category.get("orphan_artifacts"))),
            ("stale_artifact", _dicts(category.get("stale_artifacts"))),
        ):
            for artifact in artifacts:
                path = _text(artifact.get("artifact_path"))
                if not path or path in seen:
                    continue
                seen.add(path)
                plan.append(
                    {
                        "category_id": _text(category.get("category_id")),
                        "artifact_type": _text(category.get("artifact_type")),
                        "artifact_path": path,
                        "reason": reason,
                        "recommended_action": "operator_review_then_manual_cleanup",
                        "mutation_performed": False,
                        "destructive_action_performed": False,
                    }
                )
    return plan


def _retention_index(category_summaries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "category_id": _text(category.get("category_id")),
            "artifact_paths": [_text(artifact.get("artifact_path")) for artifact in _dicts(category.get("artifacts"))],
        }
        for category in category_summaries
    ]


def _expected_folder_status(config: AppConfig, policies: tuple[dict[str, Any], ...]) -> list[dict[str, Any]]:
    statuses: list[dict[str, Any]] = []
    for policy in policies:
        for folder in _list(policy.get("expected_folders")):
            path = _resolve(config.repo_root, folder)
            statuses.append(
                {
                    "category_id": _text(policy.get("category_id")),
                    "expected_folder": folder,
                    "absolute_path": str(path),
                    "exists": path.exists(),
                    "status": "present" if path.exists() else "missing",
                }
            )
    return statuses


def _gate_payload(config: AppConfig, *, item_id: str, queue_path: str | Path | None) -> dict[str, Any]:
    result = evaluate_machine_safety_gates(
        config,
        item_id=item_id,
        gate_profile="read_only_agent",
        queue_path=queue_path,
        output_format="json",
    )
    return result.get("payload", {}) if isinstance(result, dict) else {}


def _gate_summary(gate_payload: dict[str, Any]) -> dict[str, Any]:
    checks = gate_payload.get("checks", [])
    failed = [
        _text(check.get("check_id"))
        for check in checks
        if isinstance(check, dict) and not bool(check.get("passed")) and not bool(check.get("warning_only"))
    ]
    return {
        "gate_profile": _text(gate_payload.get("gate_profile") or gate_payload.get("profile")) or "read_only_agent",
        "passed": bool(gate_payload.get("passed")) and not bool(gate_payload.get("blocked")),
        "blocked": bool(gate_payload.get("blocked")),
        "blocked_reasons": _list(gate_payload.get("blocked_reasons")),
        "checks_failed": failed,
    }


def _store_blockers(store: dict[str, Any]) -> list[str]:
    if store.get("ok") is False and store.get("schema_valid") is False:
        return _list(store.get("errors"))
    return []


def _store_warnings(store: dict[str, Any]) -> list[str]:
    warnings = _list(store.get("warnings"))
    if not _text(store.get("store_path")):
        warnings.append("Durable orchestration run store path could not be resolved.")
    if store.get("ok") is True and not _dicts(store.get("records")):
        warnings.append("Durable orchestration run store has no records; orphan detection may be conservative.")
    return warnings


def _retention_warnings(*, category_summaries: list[dict[str, Any]]) -> list[str]:
    warnings: list[str] = []
    for category in category_summaries:
        category_id = _text(category.get("category_id"))
        if _int(category.get("orphan_count")):
            warnings.append(f"{category_id} has {_int(category.get('orphan_count'))} orphan artifact(s) not referenced by the durable store.")
        if _int(category.get("stale_count")):
            warnings.append(f"{category_id} has {_int(category.get('stale_count'))} stale artifact(s) past the warning threshold.")
    return warnings


def _category_status(*, missing_folders: list[str], file_count: int, stale_count: int, orphan_count: int) -> str:
    if orphan_count:
        return "orphan_review_required"
    if stale_count:
        return "stale_review_required"
    if missing_folders and file_count == 0:
        return "missing_expected_folder"
    if file_count == 0:
        return "empty"
    return "retained"


def _category_recommendation(*, status: str, cleanup_eligible: bool, orphan_count: int, stale_count: int) -> str:
    if status == "missing_expected_folder":
        return "No cleanup needed; create this folder only when future local artifact writes require it."
    if orphan_count:
        return "Review durable run-store references before manual cleanup; no deletion was performed."
    if stale_count and cleanup_eligible:
        return "Consider an operator-reviewed cleanup or archival pass; this command generated a dry-run plan only."
    if stale_count:
        return "Retain for audit unless an explicit archival policy supersedes this recommendation."
    return "Retain artifacts under the current local policy."


def _status(*, blocked: bool, warnings: list[str], dry_run_cleanup_plan: list[dict[str, Any]]) -> str:
    if blocked:
        return "blocked"
    if dry_run_cleanup_plan:
        return "review_required"
    if warnings:
        return "ready_with_warnings"
    return "ready"


def _next_safe_action(*, blocked: bool, cleanup_plan: list[dict[str, Any]], warnings: list[str]) -> str:
    if blocked:
        return "Resolve retention inspection blockers before trusting artifact index recommendations."
    if cleanup_plan:
        return "Review the dry-run cleanup plan manually; do not delete artifacts without a separate explicit operator-approved cleanup action."
    if warnings:
        return "Review retention warnings, then rerun this inspection after any manual artifact organization."
    return "Use this retention index as local audit evidence; keep cleanup as a separate explicit operator action."


def _emit_or_write(
    *,
    config: AppConfig,
    payload: dict[str, Any],
    output: str | Path | None,
    force: bool,
) -> dict[str, Any]:
    if output is None:
        return {
            "command": COMMAND_NAME,
            "ok": not bool(payload.get("blocked")),
            "local_only": True,
            "format": "json",
            "wrote_output_file": False,
            "stdout": json.dumps(payload, indent=2),
            "payload": payload,
        }
    output_path = _resolve(config.repo_root, output)
    if output_path.exists() and not force:
        blocked = dict(payload)
        blocked["status"] = "blocked"
        blocked["blocked"] = True
        blocked["blocked_reasons"] = _dedupe(
            [*_list(blocked.get("blocked_reasons")), "Output file already exists. Re-run with --force to overwrite."]
        )
        return {
            "command": COMMAND_NAME,
            "ok": False,
            "local_only": True,
            "format": "json",
            "output": str(output_path),
            "force": force,
            "wrote_output_file": False,
            "stdout": json.dumps(blocked, indent=2),
            "payload": blocked,
        }
    artifact_payload = dict(payload)
    artifact_payload["artifacts_created"] = _dedupe([*_list(payload.get("artifacts_created")), str(output_path)])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact_payload, indent=2) + "\n", encoding="utf-8")
    return {
        "command": COMMAND_NAME,
        "ok": not bool(artifact_payload.get("blocked")),
        "local_only": True,
        "format": "json",
        "output": str(output_path),
        "force": force,
        "wrote_output_file": True,
        "payload": artifact_payload,
    }


def _latest_artifact_at(artifacts: list[dict[str, Any]]) -> str:
    values = sorted(_text(artifact.get("modified_at")) for artifact in artifacts if _text(artifact.get("modified_at")))
    return values[-1] if values else ""


def _resolve(repo_root: Path, value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


def _relative_path(repo_root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo_root.resolve())).replace("\\", "/")
    except ValueError:
        return str(path.resolve())


def _text(value: Any) -> str:
    return str(value or "").strip()


def _dicts(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [entry for entry in value if isinstance(entry, dict)]
    return []


def _list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [_text(entry) for entry in value if _text(entry)]
    if isinstance(value, tuple):
        return [_text(entry) for entry in value if _text(entry)]
    if value in (None, ""):
        return []
    return [_text(value)]


def _dedupe(values: Any) -> list[str]:
    deduped: list[str] = []
    for value in values:
        text = _text(value)
        if text and text not in deduped:
            deduped.append(text)
    return deduped


def _int(value: Any) -> int:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    text = _text(value)
    return int(text) if text.isdigit() else 0


def _now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def _now_iso() -> str:
    return _now().isoformat().replace("+00:00", "Z")


def _error(error: str, details: dict[str, Any]) -> dict[str, Any]:
    return {
        "command": COMMAND_NAME,
        "ok": False,
        "local_only": True,
        "error": error,
        "details": details,
    }
