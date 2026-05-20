from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from aresforge.db.repository import (
    DEFAULT_AGENT_RECORDS,
    DEFAULT_QUEUES,
    MODEL_SCHEMA_SOURCE_DOCUMENT,
    QUEUE_SCHEMA_SOURCE_DOCUMENT,
)
from aresforge.validation import ValidationReport, validate_registry_seed_data


PROJECT_REGISTRY_SOURCE_DOCUMENT = "docs/architecture/PROJECT_REGISTRY_SCHEMA.md"
AGENT_REGISTRY_SOURCE_DOCUMENT = "docs/architecture/AGENT_REGISTRY_SCHEMA.md"
WORK_ITEM_LIFECYCLE_SOURCE_DOCUMENT = QUEUE_SCHEMA_SOURCE_DOCUMENT


@dataclass(frozen=True, slots=True)
class RegistryInspectionSpec:
    registry: str
    source_document: str
    required_markers: tuple[str, ...]
    seed_validation_prefix: str | None = None
    seed_record_count: int | None = None


DEFAULT_REGISTRY_INSPECTION_SPECS = (
    RegistryInspectionSpec(
        registry="project_registry",
        source_document=PROJECT_REGISTRY_SOURCE_DOCUMENT,
        required_markers=(
            "# AresForge Project Registry Schema",
            "## Project Record Minimum Useful Schema",
            "`project_id`",
            "`autonomy_level`",
        ),
    ),
    RegistryInspectionSpec(
        registry="agent_registry",
        source_document=AGENT_REGISTRY_SOURCE_DOCUMENT,
        required_markers=(
            "# AresForge Agent Registry Schema",
            "## Agent Record Minimum Useful Schema",
            "`agent_id`",
            "`queue_participation`",
        ),
        seed_validation_prefix="agent.",
        seed_record_count=len(DEFAULT_AGENT_RECORDS),
    ),
    RegistryInspectionSpec(
        registry="model_registry",
        source_document=MODEL_SCHEMA_SOURCE_DOCUMENT,
        required_markers=(
            "# AresForge Model Registry Schema",
            "`docs/architecture/PROJECT_REGISTRY_SCHEMA.md`",
            "`docs/architecture/AGENT_REGISTRY_SCHEMA.md`",
            "## Model Record Minimum Useful Schema",
            "## Routing Priority Conventions",
        ),
    ),
    RegistryInspectionSpec(
        registry="queue_registry",
        source_document=QUEUE_SCHEMA_SOURCE_DOCUMENT,
        required_markers=(
            "# AresForge Queue Registry Schema",
            "## Queue Record Schema",
            "## Canonical M2 Queue Set",
            "`queue_id`",
        ),
        seed_validation_prefix="queue.",
        seed_record_count=len(DEFAULT_QUEUES),
    ),
    RegistryInspectionSpec(
        registry="work_item_lifecycle",
        source_document=WORK_ITEM_LIFECYCLE_SOURCE_DOCUMENT,
        required_markers=(
            "# AresForge Queue Registry Schema",
            "## Work-Item State Schema",
            "`lifecycle_state`",
            "`route_status`",
            "`current_queue`",
        ),
    ),
)


def _build_seed_findings_map(report: ValidationReport) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for finding in sorted(report.findings, key=lambda item: (item.code, item.location, item.message)):
        prefix = finding.code.split(".", 1)[0]
        grouped.setdefault(prefix, []).append(asdict(finding))
    return grouped


def _read_registry_source(repo_root: Path, source_document: str) -> tuple[str, Path]:
    source_path = (repo_root / source_document).resolve()
    return source_path.read_text(encoding="utf-8"), source_path


def inspect_local_registries(
    repo_root: Path,
    *,
    registry_specs: tuple[RegistryInspectionSpec, ...] = DEFAULT_REGISTRY_INSPECTION_SPECS,
    seed_validation_report: ValidationReport | None = None,
) -> dict[str, Any]:
    report = seed_validation_report or validate_registry_seed_data()
    seed_findings = _build_seed_findings_map(report)
    registries: list[dict[str, Any]] = []

    for spec in registry_specs:
        problems: list[dict[str, str]] = []
        source_path = (repo_root / spec.source_document).resolve()
        exists = source_path.exists()
        line_count = 0
        status = "ok"
        missing_markers: list[str] = []

        if not exists:
            status = "missing"
            problems.append(
                {
                    "code": "source_document_missing",
                    "message": f"Source document was not found: {spec.source_document}",
                }
            )
        else:
            try:
                content, resolved_source_path = _read_registry_source(repo_root, spec.source_document)
                source_path = resolved_source_path
                line_count = len(content.splitlines())
                if not content.strip():
                    status = "empty"
                    problems.append(
                        {
                            "code": "source_document_empty",
                            "message": f"Source document is empty: {spec.source_document}",
                        }
                    )
                else:
                    missing_markers = [
                        marker for marker in spec.required_markers if marker not in content
                    ]
                    if missing_markers:
                        status = "malformed"
                        for marker in missing_markers:
                            problems.append(
                                {
                                    "code": "required_marker_missing",
                                    "message": f"Missing required marker: {marker}",
                                }
                            )
            except OSError as exc:
                status = "read_error"
                problems.append(
                    {
                        "code": "source_document_read_error",
                        "message": f"Could not read source document: {exc}",
                    }
                )

        validation_findings: list[dict[str, str]] = []
        if spec.seed_validation_prefix:
            validation_findings = seed_findings.get(spec.seed_validation_prefix.rstrip("."), [])
            if validation_findings and status == "ok":
                status = "validation_problem"

        registries.append(
            {
                "registry": spec.registry,
                "status": status,
                "source_document": spec.source_document,
                "source_path": str(source_path),
                "exists": exists,
                "line_count": line_count,
                "required_markers_checked": list(spec.required_markers),
                "missing_markers": missing_markers,
                "seed_record_count": spec.seed_record_count,
                "validation_findings": validation_findings,
                "problems": problems,
            }
        )

    status_counts = {
        status: sum(1 for item in registries if item["status"] == status)
        for status in (
            "ok",
            "missing",
            "empty",
            "malformed",
            "read_error",
            "validation_problem",
        )
    }
    problem_registry_count = sum(1 for item in registries if item["status"] != "ok")

    return {
        "ok": problem_registry_count == 0,
        "inspection_mode": "local_repo_only",
        "summary": {
            "registry_count": len(registries),
            **status_counts,
            "problem_registry_count": problem_registry_count,
        },
        "registries": registries,
    }
