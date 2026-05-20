from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path, PurePosixPath, PureWindowsPath

from aresforge.config import AppConfig


_CATEGORY_BY_PREFIX: tuple[tuple[Path, str], ...] = (
    (Path("prompts/generated"), "prompt_package"),
    (Path("evidence/generated"), "evidence_package"),
    (Path("codex_handoffs/generated"), "codex_handoff"),
    (Path("inspection_reports/generated"), "inspection_report"),
)
_TEXT_PREVIEW_BYTE_LIMIT = 4096
_TEXT_PREVIEW_CHAR_LIMIT = 400
_TEXT_EXTENSIONS = frozenset(
    {
        ".json",
        ".log",
        ".md",
        ".ps1",
        ".py",
        ".txt",
        ".yaml",
        ".yml",
    }
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


def _normalize_relative_artifact_path(raw_path: str) -> Path:
    trimmed = raw_path.strip()
    if not trimmed:
        raise ValueError("artifact_path_empty")
    if PurePosixPath(trimmed).is_absolute() or PureWindowsPath(trimmed).is_absolute():
        raise ValueError("artifact_path_outside_root")

    normalized = trimmed.replace("\\", "/")
    pure_path = PurePosixPath(normalized)
    if pure_path in (PurePosixPath(""), PurePosixPath(".")):
        raise ValueError("artifact_path_empty")
    if any(part in ("", ".", "..") for part in pure_path.parts):
        raise ValueError("artifact_path_unsafe")

    return Path(*pure_path.parts)


def _is_safe_text_extension(path: Path) -> bool:
    return path.suffix.lower() in _TEXT_EXTENSIONS


def _read_text_preview(path: Path) -> tuple[bool, str | None]:
    if not _is_safe_text_extension(path):
        return False, None

    try:
        preview_bytes = path.read_bytes()[:_TEXT_PREVIEW_BYTE_LIMIT]
    except OSError:
        return False, None

    if b"\x00" in preview_bytes:
        return False, None

    try:
        preview_text = preview_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return False, None

    preview_text = preview_text.replace("\r\r\n", "\n").replace("\r\n", "\n").replace("\r", "\n")
    return True, preview_text[:_TEXT_PREVIEW_CHAR_LIMIT]


def _artifact_payload(artifact_root: Path, path: Path) -> dict[str, object]:
    relative_path = path.relative_to(artifact_root)
    category = _category_for(relative_path)
    text_readable, text_preview = _read_text_preview(path)
    return {
        "artifact_path": relative_path.as_posix(),
        "filename": path.name,
        "size_bytes": path.stat().st_size,
        "modified_at": _modified_at(path),
        "artifact_type": category,
        "command_source_hint": _command_source_hint(relative_path, category),
        "extension": path.suffix.lower(),
        "text_readable": text_readable,
        "text_preview": text_preview,
    }


def discover_local_artifacts(config: AppConfig) -> dict[str, object]:
    artifact_root = config.artifact_root
    artifact_root_exists = artifact_root.exists()

    artifacts: list[dict[str, object]] = []
    if artifact_root_exists and artifact_root.is_dir():
        for path in sorted(
            (candidate for candidate in artifact_root.rglob("*") if candidate.is_file()),
            key=lambda candidate: candidate.relative_to(artifact_root).as_posix(),
        ):
            artifacts.append(_artifact_payload(artifact_root, path))

    return {
        "ok": True,
        "inspection_mode": "local_artifact_root_only",
        "artifact_root": str(artifact_root),
        "artifact_root_exists": artifact_root_exists and artifact_root.is_dir(),
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
    }


def inspect_local_artifact(config: AppConfig, artifact_path: str) -> dict[str, object]:
    artifact_root = config.artifact_root.resolve()
    artifact_root_exists = artifact_root.exists() and artifact_root.is_dir()

    try:
        normalized_relative_path = _normalize_relative_artifact_path(artifact_path)
    except ValueError as exc:
        return {
            "ok": False,
            "inspection_mode": "local_artifact_root_only",
            "artifact_root": str(artifact_root),
            "artifact_root_exists": artifact_root_exists,
            "error": str(exc),
            "artifact_path": artifact_path,
        }

    candidate = (artifact_root / normalized_relative_path).resolve()
    try:
        candidate.relative_to(artifact_root)
    except ValueError:
        return {
            "ok": False,
            "inspection_mode": "local_artifact_root_only",
            "artifact_root": str(artifact_root),
            "artifact_root_exists": artifact_root_exists,
            "error": "artifact_path_outside_root",
            "artifact_path": normalized_relative_path.as_posix(),
        }

    if not candidate.exists() or not candidate.is_file():
        return {
            "ok": False,
            "inspection_mode": "local_artifact_root_only",
            "artifact_root": str(artifact_root),
            "artifact_root_exists": artifact_root_exists,
            "error": "artifact_not_found",
            "artifact_path": normalized_relative_path.as_posix(),
        }

    return {
        "ok": True,
        "inspection_mode": "local_artifact_root_only",
        "artifact_root": str(artifact_root),
        "artifact_root_exists": artifact_root_exists,
        "artifact": _artifact_payload(artifact_root, candidate),
    }
