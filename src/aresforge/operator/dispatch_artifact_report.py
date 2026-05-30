from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.dispatch_approval_gate import resolve_dispatch_approval_gate_path

DISPATCH_ARTIFACT_REPORT_VERSION = "m106.1"

_KNOWN_ARTIFACT_LOCATIONS: tuple[dict[str, str], ...] = (
    {
        "artifact_type": "codex_prompt_dispatch",
        "dispatch_lane": "codex_prompt_artifact",
        "relative_path": "codex_prompt_dispatch/generated",
    },
    {
        "artifact_type": "local_llm_advisory_dry_run",
        "dispatch_lane": "local_llm_advisory",
        "relative_path": "local_llm_advisory/dry_runs",
    },
    {
        "artifact_type": "documentation_agent_dry_run",
        "dispatch_lane": "documentation_agent_dry_run",
        "relative_path": "documentation_agent/dry_runs",
    },
)

_BOUNDARY_CONFIRMATIONS = (
    "M106 dispatch artifact index/report is local-only.",
    "The report performs read-only filesystem inspection of known artifact locations.",
    "The report may read local approval gate metadata for status joining.",
    "The report does not execute Codex.",
    "The report does not invoke Ollama, local LLMs, documentation agents, or external agents.",
    "The report does not call GitHub APIs, gh, or network services.",
    "The report does not apply patches or mutate queue state.",
    "execution_allowed=false is preserved for every artifact entry and report payload.",
)


def inspect_dispatch_artifacts(
    config: AppConfig,
    *,
    project_id: str | None = None,
    artifact_root: str | Path | None = None,
    approval_path: str | Path | None = None,
    output_format: str = "markdown",
) -> dict[str, Any]:
    normalized_project_id = str(project_id or "aresforge").strip() or "aresforge"
    root = _resolve_artifact_root(config, artifact_root)
    approval_file = resolve_dispatch_approval_gate_path(config.repo_root, approval_path)
    approval_index = _load_approval_index(approval_file)
    artifacts: list[dict[str, Any]] = []
    scanned_locations: list[dict[str, Any]] = []
    missing_locations: list[str] = []

    for location in _KNOWN_ARTIFACT_LOCATIONS:
        directory = (root / location["relative_path"]).resolve()
        exists = directory.exists()
        scanned_locations.append(
            {
                "artifact_type": location["artifact_type"],
                "dispatch_lane": location["dispatch_lane"],
                "path": str(directory),
                "exists": exists,
            }
        )
        if not exists:
            missing_locations.append(str(directory))
            continue
        if not directory.is_dir():
            missing_locations.append(str(directory))
            continue
        for path in sorted(candidate for candidate in directory.rglob("*") if candidate.is_file()):
            artifacts.append(_artifact_entry(root, path, location, approval_index))

    warnings = list(approval_index["warnings"])
    if missing_locations:
        warnings.append("One or more known dispatch artifact locations are missing; report continued with available folders.")

    payload: dict[str, Any] = {
        "ok": True,
        "report_type": "dispatch_artifact_index",
        "dispatch_artifact_report_version": DISPATCH_ARTIFACT_REPORT_VERSION,
        "generated_at": datetime.now(UTC).isoformat(),
        "project_id": normalized_project_id,
        "artifact_root": str(root),
        "approval_path": str(approval_file),
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
        "scanned_locations": scanned_locations,
        "missing_locations": sorted(missing_locations),
        "warnings": sorted({warning for warning in warnings if warning}),
        "local_only": True,
        "read_only": True,
        "execution_allowed": False,
        "next_safe_action": _report_next_safe_action(artifacts),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }
    return _stdout_result("inspect-dispatch-artifacts", payload, output_format, _render_markdown(payload))


def _artifact_entry(
    artifact_root: Path,
    path: Path,
    location: dict[str, str],
    approval_index: dict[str, Any],
) -> dict[str, Any]:
    relative_key = _relative_key(artifact_root, path)
    item_id = _derive_item_id(path)
    stat = path.stat()
    gate = _matching_gate(
        approval_index["approval_gates"],
        item_id=item_id,
        artifact_type=location["artifact_type"],
        artifact_path=path,
    )
    gate_status = str(gate.get("status", "")).strip() if gate else "missing"
    return {
        "artifact_id": _artifact_id(location["artifact_type"], relative_key),
        "artifact_type": location["artifact_type"],
        "item_id": item_id,
        "dispatch_lane": location["dispatch_lane"],
        "file_path": str(path.resolve()),
        "created_at": datetime.fromtimestamp(stat.st_ctime, UTC).isoformat(),
        "modified_at": datetime.fromtimestamp(stat.st_mtime, UTC).isoformat(),
        "approval_gate_status": gate_status,
        "approval_id": str(gate.get("approval_id", "")).strip() if gate else "",
        "local_only": True,
        "execution_allowed": False,
        "next_safe_action": _artifact_next_safe_action(gate_status),
    }


def _resolve_artifact_root(config: AppConfig, artifact_root: str | Path | None) -> Path:
    if artifact_root is None:
        return config.artifact_root.resolve()
    candidate = Path(artifact_root)
    if candidate.is_absolute():
        return candidate.resolve()
    return (config.repo_root / candidate).resolve()


def _load_approval_index(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"approval_gates": [], "warnings": []}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"approval_gates": [], "warnings": [f"Dispatch approval gate file could not be parsed: {exc}"]}
    if not isinstance(raw, dict):
        return {"approval_gates": [], "warnings": ["Dispatch approval gate file has invalid schema; expected object."]}
    gates = raw.get("approval_gates", [])
    if not isinstance(gates, list):
        return {"approval_gates": [], "warnings": ["Dispatch approval gate file has invalid approval_gates field."]}
    return {"approval_gates": [gate for gate in gates if isinstance(gate, dict)], "warnings": []}


def _matching_gate(
    gates: list[dict[str, Any]],
    *,
    item_id: str,
    artifact_type: str,
    artifact_path: Path,
) -> dict[str, Any]:
    artifact_path_text = str(artifact_path.resolve())
    matches = [
        gate
        for gate in gates
        if str(gate.get("item_id", "")).strip() == item_id
        and (
            str(gate.get("artifact_type", "")).strip() == artifact_type
            or str(gate.get("artifact_type", "")).strip() == _legacy_artifact_type(artifact_type)
        )
    ]
    path_matches = [
        gate
        for gate in matches
        if str(gate.get("artifact_path", "")).strip() and str(Path(str(gate.get("artifact_path", ""))).resolve()) == artifact_path_text
    ]
    candidates = path_matches or matches
    if not candidates:
        return {}
    return sorted(candidates, key=lambda gate: str(gate.get("updated_at") or gate.get("created_at") or ""))[-1]


def _legacy_artifact_type(artifact_type: str) -> str:
    if artifact_type == "codex_prompt_dispatch":
        return "codex_prompt_artifact"
    return artifact_type


def _derive_item_id(path: Path) -> str:
    name = path.name
    for suffix in (".prompt.txt", ".final.txt", ".txt", ".json", ".md"):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return path.stem


def _artifact_id(artifact_type: str, relative_key: str) -> str:
    digest = hashlib.sha256(f"{artifact_type}:{relative_key}".encode("utf-8")).hexdigest()[:16]
    return f"dispatch-artifact-{digest}"


def _relative_key(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _artifact_next_safe_action(approval_gate_status: str) -> str:
    if approval_gate_status == "approved_for_manual_handoff":
        return "Prepare manual handoff packaging only; automated execution remains blocked."
    if approval_gate_status == "rejected":
        return "Do not use this artifact; revise or abandon the underlying dispatch output."
    if approval_gate_status == "needs_revision":
        return "Revise the artifact or dry-run output before any handoff packaging."
    if approval_gate_status == "pending_review":
        return "Complete operator review and update the approval gate before manual handoff."
    return "Create or inspect a dispatch approval gate before any manual handoff."


def _report_next_safe_action(artifacts: list[dict[str, Any]]) -> str:
    if not artifacts:
        return "No dispatch artifacts were found; generate or validate artifacts through local-only commands before M107 handoff packaging."
    if any(str(artifact.get("approval_gate_status", "")) == "missing" for artifact in artifacts):
        return "Create missing dispatch approval gates or review existing gates before M107 handoff packaging."
    return "Review approval gate statuses, then prepare any M107 handoff package manually with execution still blocked."


def _stdout_result(command: str, payload: dict[str, Any], output_format: str, markdown: str) -> dict[str, Any]:
    fmt = str(output_format or "markdown").lower().strip()
    if fmt not in {"json", "markdown"}:
        return {
            "command": command,
            "ok": False,
            "local_only": True,
            "error": "invalid_format",
            "details": {"format": output_format, "supported_formats": ["json", "markdown"]},
        }
    return {
        "command": command,
        "ok": bool(payload.get("ok", False)),
        "local_only": True,
        "format": fmt,
        "wrote_output_file": False,
        "stdout": json.dumps(payload, indent=2) if fmt == "json" else markdown,
        "payload": payload,
    }


def _render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Dispatch Artifact Index",
        "",
        f"- project_id: {payload.get('project_id', '')}",
        f"- artifact_count: {payload.get('artifact_count', 0)}",
        f"- artifact_root: {payload.get('artifact_root', '')}",
        f"- approval_path: {payload.get('approval_path', '')}",
        f"- local_only: {payload.get('local_only')}",
        f"- read_only: {payload.get('read_only')}",
        f"- execution_allowed: {payload.get('execution_allowed')}",
        f"- next_safe_action: {payload.get('next_safe_action', '')}",
    ]
    artifacts = payload.get("artifacts", []) if isinstance(payload.get("artifacts"), list) else []
    if artifacts:
        lines.extend(["", "## Artifacts"])
        lines.extend(
            (
                f"- {artifact.get('artifact_id', '')} | {artifact.get('artifact_type', '')} | "
                f"{artifact.get('item_id', '')} | {artifact.get('dispatch_lane', '')} | "
                f"approval={artifact.get('approval_gate_status', '')} | {artifact.get('file_path', '')}"
            )
            for artifact in artifacts
            if isinstance(artifact, dict)
        )
    else:
        lines.extend(["", "## Artifacts", "- none found"])
    warnings = payload.get("warnings", []) if isinstance(payload.get("warnings"), list) else []
    if warnings:
        lines.extend(["", "## Warnings"])
        lines.extend(f"- {warning}" for warning in warnings)
    return "\n".join(lines).rstrip()
