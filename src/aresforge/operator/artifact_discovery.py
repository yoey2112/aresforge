from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from aresforge.config import AppConfig


_CATEGORY_BY_PREFIX: tuple[tuple[Path, str], ...] = (
    (Path("prompts/generated"), "prompt_package"),
    (Path("evidence/generated"), "evidence_package"),
    (Path("codex_handoffs/generated"), "codex_handoff"),
    (Path("inspection_reports/generated"), "inspection_report"),
)


def _modified_at(path: Path) -> str | None:
    try:
        stat_result = path.stat()
    except OSError:
        return None
    return datetime.fromtimestamp(stat_result.st_mtime, UTC).isoformat()


def _category_for(relative_path: Path) -> str | None:
    for prefix, category in _CATEGORY_BY_PREFIX:
        if relative_path.parts[: len(prefix.parts)] == prefix.parts:
            return category
    return None


def _command_source_hint(relative_path: Path, category: str | None) -> str | None:
    normalized_parts = relative_path.parts
    filename = relative_path.name

    if filename.startswith("queue-inspection-report-"):
        return "inspect-queue --write-artifact"
    if filename.startswith("work-item-inspection-report-"):
        return "inspect-work-item --write-artifact"
    if category == "prompt_package" and "generated" in normalized_parts:
        return "generate-prompt-package"
    if category == "evidence_package" and "generated" in normalized_parts:
        return "record-evidence-package"
    if category == "codex_handoff" and "generated" in normalized_parts:
        return "prepare-codex-handoff"
    return None


def discover_local_artifacts(config: AppConfig) -> dict[str, object]:
    artifact_root = config.artifact_root
    artifact_root_exists = artifact_root.exists()

    artifacts: list[dict[str, object]] = []
    if artifact_root_exists and artifact_root.is_dir():
        for path in sorted(
            (candidate for candidate in artifact_root.rglob("*") if candidate.is_file()),
            key=lambda candidate: candidate.relative_to(artifact_root).as_posix(),
        ):
            relative_path = path.relative_to(artifact_root)
            category = _category_for(relative_path)
            artifacts.append(
                {
                    "artifact_path": relative_path.as_posix(),
                    "filename": path.name,
                    "size_bytes": path.stat().st_size,
                    "modified_at": _modified_at(path),
                    "artifact_type": category,
                    "command_source_hint": _command_source_hint(relative_path, category),
                }
            )

    return {
        "ok": True,
        "inspection_mode": "local_artifact_root_only",
        "artifact_root": str(artifact_root),
        "artifact_root_exists": artifact_root_exists and artifact_root.is_dir(),
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
    }
