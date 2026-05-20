from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Callable

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


def _normalize_relative_path(
    raw_path: str,
    *,
    empty_error: str,
    outside_root_error: str,
    unsafe_error: str,
) -> Path:
    trimmed = raw_path.strip()
    if not trimmed:
        raise ValueError(empty_error)
    if PurePosixPath(trimmed).is_absolute() or PureWindowsPath(trimmed).is_absolute():
        raise ValueError(outside_root_error)

    normalized = trimmed.replace("\\", "/")
    pure_path = PurePosixPath(normalized)
    if pure_path in (PurePosixPath(""), PurePosixPath(".")):
        raise ValueError(empty_error)
    if any(part in ("", ".", "..") for part in pure_path.parts):
        raise ValueError(unsafe_error)

    return Path(*pure_path.parts)


def _normalize_relative_artifact_path(raw_path: str) -> Path:
    return _normalize_relative_path(
        raw_path,
        empty_error="artifact_path_empty",
        outside_root_error="artifact_path_outside_root",
        unsafe_error="artifact_path_unsafe",
    )


def _normalize_relative_evidence_path(raw_path: str) -> Path:
    return _normalize_relative_path(
        raw_path,
        empty_error="evidence_path_empty",
        outside_root_error="evidence_path_outside_root",
        unsafe_error="evidence_path_unsafe",
    )


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


def _evidence_package_payload(evidence_root: Path, path: Path) -> dict[str, object]:
    relative_path = path.relative_to(evidence_root)
    text_readable, text_preview = _read_text_preview(path)
    return {
        "evidence_path": relative_path.as_posix(),
        "filename": path.name,
        "size_bytes": path.stat().st_size,
        "modified_at": _modified_at(path),
        "artifact_type": "evidence_package",
        "command_source_hint": "record-evidence-package",
        "extension": path.suffix.lower(),
        "text_readable": text_readable,
        "text_preview": text_preview,
    }


def _discover_local_files(
    root: Path,
    *,
    inspection_mode: str,
    root_key: str,
    collection_key: str,
    payload_builder: Callable[[Path, Path], dict[str, object]],
) -> dict[str, object]:
    root_exists = root.exists() and root.is_dir()
    items: list[dict[str, object]] = []
    if root_exists:
        for path in sorted(
            (candidate for candidate in root.rglob("*") if candidate.is_file()),
            key=lambda candidate: candidate.relative_to(root).as_posix(),
        ):
            items.append(payload_builder(root, path))

    return {
        "ok": True,
        "inspection_mode": inspection_mode,
        root_key: str(root),
        f"{root_key}_exists": root_exists,
        collection_key[:-1] + "_count": len(items),
        collection_key: items,
    }


def _inspect_local_file(
    root: Path,
    *,
    inspection_mode: str,
    root_key: str,
    item_key: str,
    requested_path: str,
    normalize_path: Callable[[str], Path],
    not_found_error: str,
    payload_builder: Callable[[Path, Path], dict[str, object]],
) -> dict[str, object]:
    resolved_root = root.resolve()
    root_exists = resolved_root.exists() and resolved_root.is_dir()

    try:
        normalized_relative_path = normalize_path(requested_path)
    except ValueError as exc:
        return {
            "ok": False,
            "inspection_mode": inspection_mode,
            root_key: str(resolved_root),
            f"{root_key}_exists": root_exists,
            "error": str(exc),
            item_key: requested_path,
        }

    candidate = (resolved_root / normalized_relative_path).resolve()
    try:
        candidate.relative_to(resolved_root)
    except ValueError:
        return {
            "ok": False,
            "inspection_mode": inspection_mode,
            root_key: str(resolved_root),
            f"{root_key}_exists": root_exists,
            "error": item_key.replace("_path", "_path_outside_root"),
            item_key: normalized_relative_path.as_posix(),
        }

    if not candidate.exists() or not candidate.is_file():
        return {
            "ok": False,
            "inspection_mode": inspection_mode,
            root_key: str(resolved_root),
            f"{root_key}_exists": root_exists,
            "error": not_found_error,
            item_key: normalized_relative_path.as_posix(),
        }

    return {
        "ok": True,
        "inspection_mode": inspection_mode,
        root_key: str(resolved_root),
        f"{root_key}_exists": root_exists,
        item_key[:-5]: payload_builder(resolved_root, candidate),
    }


def discover_local_artifacts(config: AppConfig) -> dict[str, object]:
    return _discover_local_files(
        config.artifact_root,
        inspection_mode="local_artifact_root_only",
        root_key="artifact_root",
        collection_key="artifacts",
        payload_builder=_artifact_payload,
    )


def inspect_local_artifact(config: AppConfig, artifact_path: str) -> dict[str, object]:
    return _inspect_local_file(
        config.artifact_root,
        inspection_mode="local_artifact_root_only",
        root_key="artifact_root",
        item_key="artifact_path",
        requested_path=artifact_path,
        normalize_path=_normalize_relative_artifact_path,
        not_found_error="artifact_not_found",
        payload_builder=_artifact_payload,
    )


def discover_local_evidence_packages(config: AppConfig) -> dict[str, object]:
    return _discover_local_files(
        config.evidence_dir,
        inspection_mode="local_evidence_root_only",
        root_key="evidence_root",
        collection_key="evidence_packages",
        payload_builder=_evidence_package_payload,
    )


def inspect_local_evidence_package(config: AppConfig, evidence_path: str) -> dict[str, object]:
    payload = _inspect_local_file(
        config.evidence_dir,
        inspection_mode="local_evidence_root_only",
        root_key="evidence_root",
        item_key="evidence_path",
        requested_path=evidence_path,
        normalize_path=_normalize_relative_evidence_path,
        not_found_error="evidence_package_not_found",
        payload_builder=_evidence_package_payload,
    )
    if payload.get("ok") is True and "evidence" in payload:
        payload["evidence_package"] = payload.pop("evidence")
    return payload
