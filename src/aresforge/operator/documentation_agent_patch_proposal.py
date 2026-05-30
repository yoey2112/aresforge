from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.local_project_queue import resolve_project_queue_path

ARTIFACT_TYPE = "documentation_agent_patch_proposal"
PATCH_PROPOSAL_VERSION = "m116.1"

_CONTEXT_DOCS = (
    "docs/context/BUILD_STATE.md",
    "docs/context/AGENT_CONTEXT.md",
)
_ROADMAP_DOCS = ("docs/roadmap/ROADMAP.md",)
_OPERATOR_DOCS = ("docs/operator/LOCAL_OPERATOR_USAGE.md",)
_BASE_DOCS = (
    "docs/architecture/DOCUMENTATION_AGENT_CONTRACT.md",
    "docs/architecture/RUNNABLE_SKELETON.md",
)

_OPERATOR_REVIEW_CHECKLIST = (
    "Confirm the patch proposal targets source-of-truth documentation only.",
    "Confirm the proposal is advisory and has not been applied.",
    "Confirm approval_required=true and patch_application_allowed=false.",
    "Review detected gaps against current queue and validation evidence.",
    "Create an M101 approval gate before any M111 patch intake review.",
    "Use a separate explicit apply workflow for any future patch application.",
)

_BOUNDARY_CONFIRMATIONS = (
    "M116 documentation-agent patch proposal generation is local-only.",
    "M116 reads queue and documentation files to produce review metadata.",
    "M116 may write local proposal artifacts only.",
    "M116 does not apply generated patches.",
    "M116 does not execute a documentation agent runtime or model.",
    "M116 does not call Codex, Ollama, local LLMs, GitHub APIs, gh, or network services.",
    "M116 does not mutate queue status except when the operator separately completes the M116 item.",
)


def generate_documentation_agent_patch_proposal(
    config: AppConfig,
    *,
    item_id: str,
    output: str | Path | None = None,
    force: bool = False,
    include_roadmap: bool = False,
    include_context: bool = False,
    include_operator_docs: bool = False,
    output_format: str = "markdown",
    queue_path: str | Path | None = None,
) -> dict[str, Any]:
    normalized_item_id = str(item_id or "").strip()
    item = _load_queue_item(config, item_id=normalized_item_id, queue_path=queue_path)
    selected_docs = _selected_source_documents(
        include_roadmap=include_roadmap,
        include_context=include_context,
        include_operator_docs=include_operator_docs,
    )
    blocked_reasons = _blocked_reasons(item=item, selected_docs=selected_docs)
    generated = not blocked_reasons
    record_path = _default_record_path(config, normalized_item_id) if output is None else _resolve_path(config.repo_root, output)
    patch_path = record_path.with_suffix(".patch")

    doc_snapshots = _read_source_documents(config, selected_docs)
    gaps = _detect_doc_gaps(item=item, item_id=normalized_item_id, documents=doc_snapshots)
    changes = _proposed_doc_changes(item=item, item_id=normalized_item_id, gaps=gaps, documents=doc_snapshots)
    patch_text = _render_patch_proposal(
        item=item,
        item_id=normalized_item_id,
        gaps=gaps,
        changes=changes,
        documents=doc_snapshots,
    )
    payload = _build_payload(
        item=item,
        item_id=normalized_item_id,
        generated=generated,
        blocked_reasons=blocked_reasons,
        source_documents=[snapshot["path"] for snapshot in doc_snapshots],
        gaps=gaps,
        changes=changes,
        patch_path=patch_path,
    )

    if generated:
        write_result = _write_artifacts(record_path=record_path, patch_path=patch_path, payload=payload, patch_text=patch_text, force=force)
        if not write_result["ok"]:
            payload["ok"] = False
            payload["generated"] = False
            payload["blocked"] = True
            payload["blocked_reasons"] = sorted(
                {
                    *[str(reason) for reason in payload.get("blocked_reasons", []) if str(reason).strip()],
                    str(write_result["reason"]),
                }
            )
            payload["proposed_patch_path"] = str(patch_path)
            payload["next_safe_action"] = "Review blocked reasons before generating another documentation patch proposal."
        else:
            payload["output_path"] = str(record_path)
            payload["proposed_patch_path"] = str(patch_path)

    return _stdout_result(
        "generate-doc-agent-patch-proposal",
        payload,
        output_format,
        _render_markdown(payload),
    )


def _build_payload(
    *,
    item: dict[str, Any],
    item_id: str,
    generated: bool,
    blocked_reasons: list[str],
    source_documents: list[str],
    gaps: list[dict[str, Any]],
    changes: list[dict[str, Any]],
    patch_path: Path,
) -> dict[str, Any]:
    return {
        "ok": generated,
        "artifact_type": ARTIFACT_TYPE,
        "artifact_version": PATCH_PROPOSAL_VERSION,
        "generated": generated,
        "generated_at": _now_iso(),
        "blocked": not generated,
        "blocked_reasons": sorted({reason for reason in blocked_reasons if reason}),
        "item_id": item_id,
        "title": str(item.get("title", "")).strip(),
        "project_id": str(item.get("project_id", "")).strip(),
        "milestone": _milestone(item, item_id=item_id),
        "queue_status": str(item.get("status", "")).strip(),
        "source_documents_reviewed": source_documents,
        "detected_doc_gaps": gaps,
        "proposed_doc_changes": changes,
        "proposed_patch_path": str(patch_path),
        "operator_review_checklist": list(_OPERATOR_REVIEW_CHECKLIST),
        "approval_required": True,
        "patch_application_allowed": False,
        "patch_application_performed": False,
        "local_only": True,
        "execution_allowed": False,
        "output_path": "",
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
        "next_safe_action": _next_safe_action(generated=generated, blocked_reasons=blocked_reasons),
    }


def _load_queue_item(config: AppConfig, *, item_id: str, queue_path: str | Path | None) -> dict[str, Any]:
    path = resolve_project_queue_path(config.repo_root, queue_path)
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    items = raw.get("work_items", []) if isinstance(raw, dict) else []
    for item in items:
        if isinstance(item, dict) and str(item.get("item_id", "")).strip() == item_id:
            return item
    return {}


def _selected_source_documents(*, include_roadmap: bool, include_context: bool, include_operator_docs: bool) -> list[str]:
    include_all = not any((include_roadmap, include_context, include_operator_docs))
    docs: list[str] = list(_BASE_DOCS)
    if include_all or include_context:
        docs.extend(_CONTEXT_DOCS)
    if include_all or include_roadmap:
        docs.extend(_ROADMAP_DOCS)
    if include_all or include_operator_docs:
        docs.extend(_OPERATOR_DOCS)
    return list(dict.fromkeys(docs))


def _blocked_reasons(*, item: dict[str, Any], selected_docs: list[str]) -> list[str]:
    reasons: list[str] = []
    if not item:
        reasons.append("Queue item was not found.")
    if not selected_docs:
        reasons.append("At least one source document group must be selected.")
    return sorted(set(reasons))


def _read_source_documents(config: AppConfig, selected_docs: list[str]) -> list[dict[str, Any]]:
    snapshots: list[dict[str, Any]] = []
    for doc in selected_docs:
        path = (config.repo_root / doc).resolve()
        exists = path.exists()
        text = ""
        if exists:
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                text = path.read_text(encoding="utf-8", errors="replace")
        snapshots.append(
            {
                "path": doc,
                "absolute_path": str(path),
                "exists": exists,
                "text": text,
            }
        )
    return snapshots


def _detect_doc_gaps(*, item: dict[str, Any], item_id: str, documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    title = str(item.get("title", "")).strip()
    milestone = _milestone(item, item_id=item_id)
    command = "generate-doc-agent-patch-proposal"
    gaps: list[dict[str, Any]] = []
    for document in documents:
        text = str(document.get("text", ""))
        path = str(document.get("path", ""))
        if not document.get("exists"):
            gaps.append({"document": path, "gap_type": "missing_source_document", "detail": "Source document does not exist."})
            continue
        if item_id and item_id not in text and milestone and milestone.upper() not in text.upper():
            gaps.append(
                {
                    "document": path,
                    "gap_type": "missing_item_or_milestone_reference",
                    "detail": f"Document does not mention {item_id} or {milestone}.",
                }
            )
        if path.endswith("LOCAL_OPERATOR_USAGE.md") and command not in text:
            gaps.append(
                {
                    "document": path,
                    "gap_type": "missing_operator_command_usage",
                    "detail": f"Operator usage does not mention {command}.",
                }
            )
        if title and title not in text and path.endswith(("BUILD_STATE.md", "ROADMAP.md", "AGENT_CONTEXT.md")):
            gaps.append(
                {
                    "document": path,
                    "gap_type": "missing_title_reference",
                    "detail": f"Document does not mention title '{title}'.",
                }
            )
    return gaps


def _proposed_doc_changes(
    *,
    item: dict[str, Any],
    item_id: str,
    gaps: list[dict[str, Any]],
    documents: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    milestone = _milestone(item, item_id=item_id)
    title = str(item.get("title", "")).strip()
    docs_with_gaps = {str(gap.get("document", "")) for gap in gaps}
    changes: list[dict[str, Any]] = []
    for document in documents:
        path = str(document.get("path", ""))
        if path in docs_with_gaps:
            changes.append(
                {
                    "document": path,
                    "change_type": "add_or_update_milestone_section",
                    "summary": f"Add operator-reviewed {milestone or item_id} coverage for {title or item_id}.",
                    "application_status": "proposal_only",
                }
            )
    if not changes:
        changes.append(
            {
                "document": "selected_source_documents",
                "change_type": "review_confirmation",
                "summary": f"No high-confidence missing references found for {item_id}; operator may still review generated proposal notes.",
                "application_status": "proposal_only",
            }
        )
    return changes


def _render_patch_proposal(
    *,
    item: dict[str, Any],
    item_id: str,
    gaps: list[dict[str, Any]],
    changes: list[dict[str, Any]],
    documents: list[dict[str, Any]],
) -> str:
    title = str(item.get("title", "")).strip()
    milestone = _milestone(item, item_id=item_id)
    lines = [
        "# Documentation Agent Patch Proposal",
        "",
        "This is a proposal artifact only. Do not apply automatically.",
        "",
        f"Item: {item_id}",
        f"Title: {title}",
        f"Milestone: {milestone}",
        "",
        "## Source Documents Reviewed",
    ]
    lines.extend(f"- {document.get('path')} (exists={document.get('exists')})" for document in documents)
    lines.extend(["", "## Detected Documentation Gaps"])
    if gaps:
        lines.extend(f"- {gap.get('document')}: {gap.get('gap_type')} - {gap.get('detail')}" for gap in gaps)
    else:
        lines.append("- No high-confidence missing documentation references detected.")
    lines.extend(["", "## Proposed Documentation Changes"])
    lines.extend(f"- {change.get('document')}: {change.get('summary')}" for change in changes)
    lines.extend(
        [
            "",
            "## Proposed Patch Sketch",
            "",
            "```diff",
            f"diff --git a/docs/operator/LOCAL_OPERATOR_USAGE.md b/docs/operator/LOCAL_OPERATOR_USAGE.md",
            "--- a/docs/operator/LOCAL_OPERATOR_USAGE.md",
            "+++ b/docs/operator/LOCAL_OPERATOR_USAGE.md",
            "@@ proposal only @@",
            f"+## {milestone or item_id} {title}",
            f"+Record {item_id} documentation-agent patch proposal behavior.",
            "+Confirm approval_required=true and patch_application_allowed=false.",
            "+Confirm generated proposals require operator review before any patch intake or apply path.",
            "```",
            "",
            "Patch application allowed: false",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def _write_artifacts(*, record_path: Path, patch_path: Path, payload: dict[str, Any], patch_text: str, force: bool) -> dict[str, Any]:
    existing = [path for path in (record_path, patch_path) if path.exists()]
    if existing and not force:
        return {"ok": False, "reason": f"Output artifact already exists: {existing[0]}", "output_path": str(existing[0])}
    try:
        record_path.parent.mkdir(parents=True, exist_ok=True)
        patch_path.parent.mkdir(parents=True, exist_ok=True)
        patch_path.write_text(patch_text, encoding="utf-8")
        payload = dict(payload)
        payload["proposed_patch_path"] = str(patch_path)
        payload["output_path"] = str(record_path)
        record_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    except OSError as exc:
        return {"ok": False, "reason": f"Failed to write documentation patch proposal artifacts: {exc}"}
    return {"ok": True, "output_path": str(record_path), "patch_path": str(patch_path)}


def _default_record_path(config: AppConfig, item_id: str) -> Path:
    safe_item = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in (item_id or "unknown"))
    return (config.artifact_root / "documentation_agent" / "patch_proposals" / f"{safe_item}.json").resolve()


def _resolve_path(repo_root: Path, value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


def _milestone(item: dict[str, Any], *, item_id: str) -> str:
    tags = item.get("tags", []) if isinstance(item.get("tags"), list) else []
    for tag in tags:
        text = str(tag).strip()
        if text.startswith("milestone:"):
            return text.split(":", 1)[1].split(",", 1)[0].strip()
    if item_id.lower().startswith("m") and "-" in item_id:
        return item_id.split("-", 1)[0]
    return ""


def _next_safe_action(*, generated: bool, blocked_reasons: list[str]) -> str:
    if generated:
        return "Review the proposed documentation patch artifact, then create an approval gate before M111 patch intake."
    if any("Queue item" in reason for reason in blocked_reasons):
        return "Inspect the local queue and choose a valid documentation patch proposal item."
    return "Resolve blocked reasons before generating a documentation patch proposal."


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
        "wrote_output_file": bool(payload.get("output_path")),
        "stdout": json.dumps(payload, indent=2) if fmt == "json" else markdown,
        "payload": payload,
    }


def _render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Documentation Agent Patch Proposal",
        "",
        f"- artifact_type: {payload.get('artifact_type')}",
        f"- generated: {payload.get('generated')}",
        f"- blocked: {payload.get('blocked')}",
        f"- item_id: {payload.get('item_id', '')}",
        f"- title: {payload.get('title', '')}",
        f"- proposed_patch_path: {payload.get('proposed_patch_path', '')}",
        f"- approval_required: {payload.get('approval_required')}",
        f"- patch_application_allowed: {payload.get('patch_application_allowed')}",
        f"- execution_allowed: {payload.get('execution_allowed')}",
        f"- next_safe_action: {payload.get('next_safe_action', '')}",
    ]
    blockers = payload.get("blocked_reasons", []) if isinstance(payload.get("blocked_reasons"), list) else []
    if blockers:
        lines.extend(["", "## Blocked Reasons"])
        lines.extend(f"- {reason}" for reason in blockers)
    lines.extend(["", "## Source Documents Reviewed"])
    lines.extend(f"- {doc}" for doc in payload.get("source_documents_reviewed", []) if str(doc).strip())
    lines.extend(["", "## Proposed Changes"])
    changes = payload.get("proposed_doc_changes", []) if isinstance(payload.get("proposed_doc_changes"), list) else []
    lines.extend(f"- {change.get('document')}: {change.get('summary')}" for change in changes if isinstance(change, dict))
    return "\n".join(lines).rstrip()


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()
