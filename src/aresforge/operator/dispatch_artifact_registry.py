from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.local_project_queue import resolve_project_queue_path

REGISTRY_TYPE = "dispatch_artifact_registry_v2"
REGISTRY_VERSION = "m119.1"
COMMAND_NAME = "inspect-artifact-registry"

_ARTIFACT_SOURCES: tuple[dict[str, object], ...] = (
    {
        "artifact_type": "manual_codex_dispatch_preparation",
        "directory": Path("artifacts/manual_codex_dispatch/prepared"),
        "extensions": (".json",),
    },
    {
        "artifact_type": "codex_prompt_dispatch",
        "directory": Path("artifacts/codex_prompt_dispatch/generated"),
        "extensions": (".json", ".txt", ".md"),
    },
    {
        "artifact_type": "local_llm_advisory_request",
        "directory": Path("artifacts/local_llm_advisory/requests"),
        "extensions": (".json",),
    },
    {
        "artifact_type": "patch_proposal_intake",
        "directory": Path("artifacts/patch_intake"),
        "extensions": (".json",),
    },
    {
        "artifact_type": "dispatch_result_evidence",
        "directory": Path("artifacts/dispatch_result_evidence"),
        "extensions": (".json",),
    },
    {
        "artifact_type": "queue_completion_recommendation",
        "directory": Path("artifacts/queue_completion_recommendations"),
        "extensions": (".json",),
    },
    {
        "artifact_type": "documentation_agent_patch_proposal",
        "directory": Path("artifacts/documentation_agent/patch_proposals"),
        "extensions": (".json", ".patch"),
    },
    {
        "artifact_type": "agent_route_recommendation",
        "directory": Path("artifacts/agent_route_recommendations"),
        "extensions": (".json",),
    },
    {
        "artifact_type": "agent_route_recommendation",
        "directory": Path("artifacts/agent_routes"),
        "extensions": (".json",),
    },
)

_BOUNDARY_CONFIRMATIONS = (
    "M119 dispatch artifact registry is local-only.",
    "M119 reads local artifact files and queue metadata only.",
    "M119 does not execute Codex, Ollama, local LLMs, agents, GitHub, gh, network services, or patches.",
    "M119 does not mutate queue state or source files.",
    "execution_allowed=false is preserved for the registry payload.",
)


def inspect_artifact_registry(
    config: AppConfig,
    *,
    project_id: str | None = None,
    item_id: str | None = None,
    artifact_type: str | None = None,
    output: str | Path | None = None,
    force: bool = False,
    output_format: str = "json",
    queue_path: str | Path | None = None,
) -> dict[str, Any]:
    fmt = str(output_format or "json").strip().lower()
    if fmt not in {"json", "markdown"}:
        return _error("invalid_format", {"format": output_format, "supported_formats": ["json", "markdown"]})

    normalized_project_id = str(project_id or "aresforge").strip() or "aresforge"
    item_filter = str(item_id or "").strip()
    type_filter = str(artifact_type or "").strip()
    queue_items = _load_queue_items(config, queue_path=queue_path)
    queue_index = {str(item.get("item_id", "")).strip(): item for item in queue_items}

    source_directories: list[dict[str, Any]] = []
    missing_expected_artifacts: list[dict[str, Any]] = []
    artifacts: list[dict[str, Any]] = []
    warnings: list[str] = []

    for source in _ARTIFACT_SOURCES:
        source_type = str(source["artifact_type"])
        if type_filter and source_type != type_filter:
            continue
        directory = (config.repo_root / Path(str(source["directory"]))).resolve()
        exists = directory.exists() and directory.is_dir()
        source_directories.append(
            {
                "artifact_type": source_type,
                "path": str(directory),
                "exists": exists,
            }
        )
        if not exists:
            missing_expected_artifacts.append(
                {"artifact_type": source_type, "path": str(directory), "reason": "source_directory_missing"}
            )
            continue
        extensions = tuple(str(ext) for ext in source.get("extensions", (".json",)))
        for path in sorted(candidate for candidate in directory.rglob("*") if candidate.is_file()):
            if path.suffix.lower() not in extensions:
                continue
            record = _read_json(path, warnings) if path.suffix.lower() == ".json" else {}
            entry = _artifact_entry(
                config=config,
                source_type=source_type,
                path=path,
                record=record,
                queue_index=queue_index,
            )
            if item_filter and entry["item_id"] != item_filter:
                continue
            artifacts.append(entry)

    if item_filter and not artifacts:
        missing_expected_artifacts.append(
            {
                "artifact_type": type_filter or "any_supported_artifact",
                "item_id": item_filter,
                "reason": "no_matching_artifacts",
            }
        )

    duplicate_artifacts = _duplicate_artifacts(artifacts)
    stale_artifacts = [artifact for artifact in artifacts if artifact.get("stale")]
    blocked_artifacts = [artifact for artifact in artifacts if artifact.get("blocked")]
    review_required_artifacts = [artifact for artifact in artifacts if artifact.get("review_required")]
    artifacts_by_type = dict(sorted(Counter(str(artifact["artifact_type"]) for artifact in artifacts).items()))

    payload: dict[str, Any] = {
        "ok": True,
        "registry_type": REGISTRY_TYPE,
        "registry_version": REGISTRY_VERSION,
        "generated": True,
        "generated_at": _now_iso(),
        "project_id": normalized_project_id,
        "item_id": item_filter,
        "artifact_type_filter": type_filter,
        "artifact_count": len(artifacts),
        "artifacts_by_type": artifacts_by_type,
        "artifacts": artifacts,
        "source_directories": source_directories,
        "missing_expected_artifacts": missing_expected_artifacts,
        "stale_artifacts": stale_artifacts,
        "duplicate_artifacts": duplicate_artifacts,
        "blocked_artifacts": blocked_artifacts,
        "review_required_artifacts": review_required_artifacts,
        "warnings": warnings,
        "local_only": True,
        "execution_allowed": False,
        "next_safe_action": _next_safe_action(
            artifacts=artifacts,
            missing=missing_expected_artifacts,
            blocked=blocked_artifacts,
            review_required=review_required_artifacts,
        ),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }
    return _emit_or_write(config=config, payload=payload, output=output, force=force, output_format=fmt)


def _artifact_entry(
    *,
    config: AppConfig,
    source_type: str,
    path: Path,
    record: dict[str, Any],
    queue_index: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    stat = path.stat()
    artifact_type = _artifact_type(record) or source_type
    item_id = _item_id(record, path)
    queue_item = queue_index.get(item_id, {})
    blocked = bool(record.get("blocked", False))
    review_required = _review_required(record, artifact_type, blocked)
    stale = bool(item_id and item_id not in queue_index)
    if not item_id:
        stale = True
    return {
        "artifact_id": _artifact_id(artifact_type, path),
        "artifact_type": artifact_type,
        "source_artifact_type": source_type,
        "item_id": item_id,
        "project_id": str(record.get("project_id", "") or queue_item.get("project_id", "") or "").strip(),
        "milestone": str(record.get("milestone", "") or _milestone_from_item_id(item_id)).strip(),
        "artifact_path": str(path.resolve()),
        "relative_path": _relative_path(config.repo_root, path),
        "exists": path.exists(),
        "size_bytes": stat.st_size,
        "modified_at": datetime.fromtimestamp(stat.st_mtime, UTC).isoformat(),
        "status": _status(record),
        "blocked": blocked,
        "blocked_reasons": _list(record.get("blocked_reasons")),
        "review_required": review_required,
        "stale": stale,
        "stale_reason": "" if not stale else _stale_reason(item_id, queue_index),
        "local_only": bool(record.get("local_only", True)),
        "execution_allowed": bool(record.get("execution_allowed", False)),
        "next_safe_action": str(record.get("next_safe_action", "") or _artifact_next_safe_action(review_required, blocked)),
    }


def _load_queue_items(config: AppConfig, *, queue_path: str | Path | None) -> list[dict[str, Any]]:
    path = resolve_project_queue_path(config.repo_root, queue_path)
    if not path.exists():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(raw, dict) or not isinstance(raw.get("work_items"), list):
        return []
    return [item for item in raw["work_items"] if isinstance(item, dict)]


def _read_json(path: Path, warnings: list[str]) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        warnings.append(f"Could not parse artifact JSON {path}: {exc}")
        return {}
    return raw if isinstance(raw, dict) else {}


def _artifact_type(record: dict[str, Any]) -> str:
    for field in (
        "artifact_type",
        "preparation_record_type",
        "intake_record_type",
        "evidence_record_type",
        "recommendation_record_type",
        "recommendation_type",
        "probe_type",
        "record_type",
    ):
        value = str(record.get(field, "")).strip()
        if value:
            return value
    return ""


def _item_id(record: dict[str, Any], path: Path) -> str:
    value = str(record.get("item_id", "")).strip()
    if value:
        return value
    name = path.name
    for suffix in (".prompt.txt", ".final.txt", ".json", ".patch", ".md", ".txt"):
        if name.endswith(suffix):
            name = name[: -len(suffix)]
            break
    if "-" in name and name[:15].isdigit():
        name = name.split("-", 1)[1]
    return name


def _status(record: dict[str, Any]) -> str:
    if record.get("accepted_for_review") is True:
        return "accepted_for_review"
    if record.get("recommended_complete") is True:
        return "recommended_complete"
    if record.get("parsed") is True:
        return "parsed"
    if record.get("generated") is True:
        return "generated"
    if record.get("prepared") is True:
        return "prepared"
    if record.get("blocked") is True:
        return "blocked"
    return "available"


def _review_required(record: dict[str, Any], artifact_type: str, blocked: bool) -> bool:
    if blocked:
        return True
    for field in ("operator_review_required", "human_review_required", "operator_decision_required"):
        if field in record:
            return bool(record.get(field))
    if artifact_type in {
        "patch_proposal_intake",
        "queue_completion_recommendation",
        "dispatch_result_evidence",
        "documentation_agent_patch_proposal",
        "local_llm_advisory_request",
        "agent_route_recommendation",
        "manual_codex_dispatch_preparation",
    }:
        return True
    return False


def _duplicate_artifacts(artifacts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for artifact in artifacts:
        key = (str(artifact.get("artifact_type", "")), str(artifact.get("item_id", "")))
        groups.setdefault(key, []).append(artifact)
    duplicates: list[dict[str, Any]] = []
    for (artifact_type, item_id), group in sorted(groups.items()):
        if item_id and len(group) > 1:
            duplicates.append(
                {
                    "artifact_type": artifact_type,
                    "item_id": item_id,
                    "count": len(group),
                    "artifact_ids": [str(artifact.get("artifact_id", "")) for artifact in group],
                    "paths": [str(artifact.get("artifact_path", "")) for artifact in group],
                }
            )
    return duplicates


def _list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if value in (None, ""):
        return []
    return [str(value).strip()]


def _artifact_id(artifact_type: str, path: Path) -> str:
    digest = hashlib.sha256(f"{artifact_type}:{path.resolve()}".encode("utf-8")).hexdigest()[:16]
    return f"artifact-registry-v2-{digest}"


def _relative_path(repo_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _milestone_from_item_id(item_id: str) -> str:
    text = item_id.strip()
    return text.split("-", 1)[0].lower() if text.lower().startswith("m") and "-" in text else ""


def _stale_reason(item_id: str, queue_index: dict[str, dict[str, Any]]) -> str:
    if not item_id:
        return "artifact_item_id_missing"
    if item_id not in queue_index:
        return "artifact_item_id_not_found_in_queue"
    return ""


def _artifact_next_safe_action(review_required: bool, blocked: bool) -> str:
    if blocked:
        return "Resolve artifact blocked reasons before using this record for any operator decision."
    if review_required:
        return "Review this local artifact before any explicit operator-gated follow-on action."
    return "Keep this artifact as local registry metadata; execution remains blocked."


def _next_safe_action(
    *,
    artifacts: list[dict[str, Any]],
    missing: list[dict[str, Any]],
    blocked: list[dict[str, Any]],
    review_required: list[dict[str, Any]],
) -> str:
    if blocked:
        return "Review blocked artifacts and resolve their blocked reasons before any handoff or completion decision."
    if review_required:
        return "Review registry artifacts that require operator attention before any explicit local follow-on command."
    if missing and not artifacts:
        return "Generate local artifacts with existing planning commands, then refresh the registry."
    return "Use this registry for local review only; execution and patch application remain blocked."


def _emit_or_write(
    *,
    config: AppConfig,
    payload: dict[str, Any],
    output: str | Path | None,
    force: bool,
    output_format: str,
) -> dict[str, Any]:
    rendered = json.dumps(payload, indent=2, sort_keys=True) if output_format == "json" else _render_markdown(payload)
    if output is None:
        return {
            "command": COMMAND_NAME,
            "ok": True,
            "local_only": True,
            "format": output_format,
            "wrote_output_file": False,
            "stdout": rendered,
            "payload": payload,
        }
    output_path = _resolve_path(config.repo_root, output)
    if output_path.exists() and not force:
        blocked_payload = dict(payload)
        blocked_payload["ok"] = False
        blocked_payload["generated"] = False
        blocked_payload["warnings"] = sorted(
            [*blocked_payload.get("warnings", []), "Output file already exists. Re-run with --force to overwrite."]
        )
        blocked_rendered = (
            json.dumps(blocked_payload, indent=2, sort_keys=True)
            if output_format == "json"
            else _render_markdown(blocked_payload)
        )
        return {
            "command": COMMAND_NAME,
            "ok": False,
            "local_only": True,
            "format": output_format,
            "output": str(output_path),
            "force": force,
            "wrote_output_file": False,
            "stdout": blocked_rendered,
            "payload": blocked_payload,
        }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered.rstrip() + "\n", encoding="utf-8")
    return {
        "command": COMMAND_NAME,
        "ok": True,
        "local_only": True,
        "format": output_format,
        "output": str(output_path),
        "force": force,
        "wrote_output_file": True,
        "stdout": rendered,
        "payload": payload,
    }


def _resolve_path(repo_root: Path, value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


def _render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Dispatch Artifact Registry v2",
        "",
        f"- registry_type: {payload.get('registry_type', '')}",
        f"- project_id: {payload.get('project_id', '')}",
        f"- item_id: {payload.get('item_id', '') or '-'}",
        f"- artifact_count: {payload.get('artifact_count', 0)}",
        f"- local_only: {payload.get('local_only')}",
        f"- execution_allowed: {payload.get('execution_allowed')}",
        f"- next_safe_action: {payload.get('next_safe_action', '')}",
        "",
        "## Artifacts By Type",
    ]
    by_type = payload.get("artifacts_by_type", {})
    if isinstance(by_type, dict) and by_type:
        lines.extend(f"- {key}: {value}" for key, value in sorted(by_type.items()))
    else:
        lines.append("- none")
    artifacts = payload.get("artifacts", [])
    if isinstance(artifacts, list) and artifacts:
        lines.extend(["", "## Artifacts"])
        lines.extend(
            f"- {artifact.get('artifact_type', '')} | {artifact.get('item_id', '')} | "
            f"blocked={artifact.get('blocked')} | review_required={artifact.get('review_required')} | "
            f"{artifact.get('relative_path', '')}"
            for artifact in artifacts
            if isinstance(artifact, dict)
        )
    return "\n".join(lines).rstrip()


def _error(code: str, details: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "ok": False,
        "registry_type": REGISTRY_TYPE,
        "generated": False,
        "blocked": True,
        "error": code,
        "details": details,
        "local_only": True,
        "execution_allowed": False,
        "next_safe_action": "Fix the registry inspection request and rerun locally.",
    }
    return {
        "command": COMMAND_NAME,
        "ok": False,
        "local_only": True,
        "format": "json",
        "wrote_output_file": False,
        "stdout": json.dumps(payload, indent=2, sort_keys=True),
        "payload": payload,
    }


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
