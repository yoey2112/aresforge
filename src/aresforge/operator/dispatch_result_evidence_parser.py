from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import re
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.local_project_queue import resolve_project_queue_path

DISPATCH_RESULT_EVIDENCE_VERSION = "m112.1"
COMMAND_NAME = "parse-dispatch-result-evidence"

_BOUNDARY_CONFIRMATIONS = (
    "M112 dispatch result evidence parsing is local-only.",
    "M112 reads a human-supplied result file and records structured evidence only.",
    "M112 does not execute Codex, Codex CLI, local LLMs, documentation agents, or external agents.",
    "M112 does not call GitHub APIs, gh, network services, issues, PRs, or workflows.",
    "M112 does not apply patches or mutate repository files from parsed result content.",
    "M112 does not mark queue items complete or start follow-on work.",
)

_SECTION_ALIASES = {
    "files_changed": {
        "files changed",
        "changed files",
        "files modified",
        "files",
    },
    "what_changed": {
        "what changed",
        "changes",
        "change summary",
        "summary",
        "implementation summary",
    },
    "tests_reported": {
        "tests run",
        "tests",
        "validation",
        "validation run",
        "validation results",
        "tests run and results",
    },
    "smoke_checks_reported": {
        "smoke checks",
        "smoke check",
        "smoke checks run",
        "smoke checks run and results",
        "smoke",
    },
    "warnings_or_blockers": {
        "warnings or blockers",
        "warnings",
        "blockers",
        "warnings and blockers",
        "known warnings",
        "warnings or residual risk",
    },
    "commit_hash": {
        "commit hash",
        "commit",
        "commits",
        "hash",
    },
}


def parse_dispatch_result_evidence(
    config: AppConfig,
    *,
    item_id: str,
    result_path: str | Path,
    queue_path: str | Path | None = None,
    output: str | Path | None = None,
    force: bool = False,
    output_format: str = "markdown",
) -> dict[str, Any]:
    fmt = str(output_format or "markdown").lower().strip()
    if fmt not in {"markdown", "json"}:
        return _error("invalid_format", {"format": output_format, "supported_formats": ["markdown", "json"]})

    normalized_item_id = str(item_id or "").strip()
    item = _load_queue_item(config, item_id=normalized_item_id, queue_path=queue_path)
    resolved_result_path = _resolve_path(config.repo_root, result_path)
    text = _read_text(resolved_result_path)
    parsed_sections = _parse_sections(text)
    parser_warnings = _parser_warnings(parsed_sections, text)
    blocked_reasons = _blocked_reasons(item=item, result_path=resolved_result_path)
    parsed = not blocked_reasons
    payload = _build_payload(
        config=config,
        item_id=normalized_item_id,
        item=item,
        result_path=resolved_result_path,
        text=text,
        sections=parsed_sections,
        parser_warnings=parser_warnings,
        parsed=parsed,
        blocked_reasons=blocked_reasons,
    )
    return _emit_or_write(config=config, payload=payload, output=output, force=force, output_format=fmt)


def _build_payload(
    *,
    config: AppConfig,
    item_id: str,
    item: dict[str, Any],
    result_path: Path,
    text: str,
    sections: dict[str, list[str]],
    parser_warnings: list[str],
    parsed: bool,
    blocked_reasons: list[str],
) -> dict[str, Any]:
    files_changed = _section_or_detected_list(sections, "files_changed", _detect_files(text))
    tests_reported = _section_or_detected_list(sections, "tests_reported", _detect_test_lines(text))
    smoke_checks_reported = _section_or_detected_list(sections, "smoke_checks_reported", _detect_smoke_lines(text))
    warnings_or_blockers = _section_or_detected_list(sections, "warnings_or_blockers", [])
    warnings_or_blockers = _dedupe([*warnings_or_blockers, *parser_warnings])
    commit_hash = _first_commit_hash(_section_text(sections, "commit_hash")) or _first_commit_hash(text)
    validation_confidence = _validation_confidence(
        parsed=parsed,
        files_changed=files_changed,
        tests_reported=tests_reported,
        smoke_checks_reported=smoke_checks_reported,
        commit_hash=commit_hash,
        warnings_or_blockers=warnings_or_blockers,
    )
    return {
        "dispatch_result_evidence_version": DISPATCH_RESULT_EVIDENCE_VERSION,
        "evidence_record_type": "dispatch_result_evidence",
        "parsed": parsed,
        "blocked": not parsed,
        "blocked_reasons": sorted({reason for reason in blocked_reasons if reason}),
        "item_id": item_id,
        "title": str(item.get("title", "")).strip(),
        "project_id": str(item.get("project_id", "")).strip(),
        "milestone": _milestone(item),
        "result_path": str(result_path),
        "result_exists": result_path.exists(),
        "files_changed": files_changed,
        "what_changed": _section_or_detected_list(sections, "what_changed", []),
        "tests_reported": tests_reported,
        "smoke_checks_reported": smoke_checks_reported,
        "warnings_or_blockers": warnings_or_blockers,
        "commit_hash": commit_hash,
        "validation_confidence": validation_confidence,
        "completion_recommendation": _completion_recommendation(
            parsed=parsed,
            validation_confidence=validation_confidence,
            warnings_or_blockers=warnings_or_blockers,
        ),
        "human_review_required": True,
        "local_only": True,
        "execution_allowed": False,
        "recorded_at": _now_iso(),
        "repo_root": str(config.repo_root),
        "next_safe_action": _next_safe_action(parsed=parsed, blocked_reasons=blocked_reasons),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }


def _parse_sections(text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for raw_line in text.splitlines():
        heading = _heading_key(raw_line)
        if heading:
            current = _canonical_section(heading)
            if current:
                sections.setdefault(current, [])
            continue
        if current:
            cleaned = _clean_entry(raw_line)
            if cleaned:
                sections.setdefault(current, []).append(cleaned)
    return {key: _dedupe(values) for key, values in sections.items()}


def _heading_key(line: str) -> str:
    stripped = line.strip()
    if not stripped:
        return ""
    markdown = re.match(r"^#{1,6}\s+(.+?)\s*$", stripped)
    if markdown:
        return _normalize_heading(markdown.group(1))
    bold = re.match(r"^\*\*(.+?)\*\*\s*:?\s*$", stripped)
    if bold:
        return _normalize_heading(bold.group(1))
    colon = re.match(r"^([A-Za-z][A-Za-z0-9 /&_-]{2,60}):\s*$", stripped)
    if colon:
        return _normalize_heading(colon.group(1))
    return ""


def _canonical_section(heading: str) -> str | None:
    for canonical, aliases in _SECTION_ALIASES.items():
        if heading in aliases:
            return canonical
    return None


def _normalize_heading(value: str) -> str:
    normalized = re.sub(r"[*`_]+", "", value).strip().lower()
    normalized = normalized.replace("&", "and")
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


def _clean_entry(line: str) -> str:
    stripped = line.strip()
    if not stripped:
        return ""
    stripped = re.sub(r"^[-*]\s+", "", stripped)
    stripped = re.sub(r"^\d+[.)]\s+", "", stripped)
    return stripped.strip("` ").strip()


def _section_or_detected_list(sections: dict[str, list[str]], key: str, fallback: list[str]) -> list[str]:
    values = sections.get(key, [])
    if values:
        return _dedupe(values)
    return _dedupe(fallback)


def _section_text(sections: dict[str, list[str]], key: str) -> str:
    return "\n".join(sections.get(key, []))


def _detect_files(text: str) -> list[str]:
    candidates: list[str] = []
    pattern = re.compile(r"(?<![\w./\\-])([A-Za-z0-9_.-]+(?:[/\\][A-Za-z0-9_.-]+)+)(?::\d+)?")
    for match in pattern.finditer(text):
        candidate = match.group(1).replace("\\", "/").strip("`.,;)")
        if "/" in candidate and not candidate.startswith(("http:/", "https:/")) and candidate not in candidates:
            candidates.append(candidate)
    return candidates


def _detect_test_lines(text: str) -> list[str]:
    lines = []
    for line in text.splitlines():
        lower = line.lower()
        if "pytest" in lower or re.search(r"\b\d+\s+passed\b", lower) or "git diff --check" in lower:
            lines.append(_clean_entry(line))
    return _dedupe(lines)


def _detect_smoke_lines(text: str) -> list[str]:
    return _dedupe(_clean_entry(line) for line in text.splitlines() if "smoke" in line.lower())


def _first_commit_hash(text: str) -> str:
    match = re.search(r"\b[0-9a-f]{7,40}\b", text, flags=re.IGNORECASE)
    return match.group(0) if match else ""


def _parser_warnings(sections: dict[str, list[str]], text: str) -> list[str]:
    warnings: list[str] = []
    for key, label in (
        ("files_changed", "Files changed section was not found; file paths were inferred when possible."),
        ("what_changed", "What changed section was not found."),
        ("tests_reported", "Tests reported section was not found; validation lines were inferred when possible."),
        ("smoke_checks_reported", "Smoke checks section was not found; smoke lines were inferred when possible."),
        ("commit_hash", "Commit hash section was not found; commit hash was inferred when possible."),
    ):
        if not sections.get(key):
            warnings.append(label)
    if not text.strip():
        warnings.append("Result file is empty.")
    return warnings


def _validation_confidence(
    *,
    parsed: bool,
    files_changed: list[str],
    tests_reported: list[str],
    smoke_checks_reported: list[str],
    commit_hash: str,
    warnings_or_blockers: list[str],
) -> str:
    if not parsed:
        return "blocked"
    severe = any(_looks_like_blocker(entry) for entry in warnings_or_blockers)
    if severe:
        return "low"
    if files_changed and tests_reported and smoke_checks_reported and commit_hash:
        return "high"
    if (tests_reported or smoke_checks_reported) and (files_changed or commit_hash):
        return "medium"
    return "low"


def _completion_recommendation(*, parsed: bool, validation_confidence: str, warnings_or_blockers: list[str]) -> str:
    if not parsed:
        return "do_not_complete"
    if validation_confidence == "high" and not any(_looks_like_blocker(entry) for entry in warnings_or_blockers):
        return "ready_for_human_completion_review"
    if validation_confidence == "medium":
        return "review_missing_evidence_before_completion"
    return "collect_additional_evidence_before_completion"


def _looks_like_blocker(entry: str) -> bool:
    lower = entry.lower()
    if "no blocker" in lower or "no blockers" in lower:
        return False
    return any(token in lower for token in ("blocker", "blocked", "failed", "failure", "error", "unable", "not run"))


def _blocked_reasons(*, item: dict[str, Any], result_path: Path) -> list[str]:
    reasons: list[str] = []
    if not item:
        reasons.append("Queue item was not found.")
    if not result_path.exists():
        reasons.append(f"Result file is missing: {result_path}")
    return sorted(reasons)


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


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _milestone(item: dict[str, Any]) -> str:
    tags = item.get("tags", []) if isinstance(item.get("tags"), list) else []
    for tag in tags:
        text = str(tag).strip()
        if text.startswith("milestone:"):
            return text.split(":", 1)[1].split(",", 1)[0].strip()
    item_id = str(item.get("item_id", "")).strip()
    return item_id.split("-", 1)[0].upper() if item_id.lower().startswith("m") and "-" in item_id else ""


def _resolve_path(repo_root: Path, value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


def _emit_or_write(
    *,
    config: AppConfig,
    payload: dict[str, Any],
    output: str | Path | None,
    force: bool,
    output_format: str,
) -> dict[str, Any]:
    rendered = json.dumps(payload, indent=2) if output_format == "json" else _render_markdown(payload)
    ok = bool(payload.get("parsed")) and not bool(payload.get("blocked"))
    if output is None:
        return {
            "command": COMMAND_NAME,
            "ok": ok,
            "local_only": True,
            "format": output_format,
            "wrote_output_file": False,
            "stdout": rendered,
            "payload": payload,
        }
    output_path = _resolve_path(config.repo_root, output)
    if output_path.exists() and not force:
        payload = dict(payload)
        payload["parsed"] = False
        payload["blocked"] = True
        payload["blocked_reasons"] = sorted(
            {*payload.get("blocked_reasons", []), "Output file already exists. Re-run with --force to overwrite."}
        )
        rendered = json.dumps(payload, indent=2) if output_format == "json" else _render_markdown(payload)
        ok = False
    else:
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(rendered.rstrip() + "\n", encoding="utf-8")
        except OSError as exc:
            return _error("output_write_failed", {"path": str(output_path), "message": str(exc)}, payload=payload)
    return {
        "command": COMMAND_NAME,
        "ok": ok,
        "local_only": True,
        "format": output_format,
        "output": str(output_path),
        "force": force,
        "wrote_output_file": ok,
        "stdout": rendered,
        "payload": payload,
    }


def _render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Dispatch Result Evidence",
        "",
        f"- evidence_record_type: {payload.get('evidence_record_type', '')}",
        f"- parsed: {payload.get('parsed')}",
        f"- blocked: {payload.get('blocked')}",
        f"- item_id: {payload.get('item_id', '')}",
        f"- title: {payload.get('title', '')}",
        f"- result_path: {payload.get('result_path', '')}",
        f"- result_exists: {payload.get('result_exists')}",
        f"- commit_hash: {payload.get('commit_hash', '') or '-'}",
        f"- validation_confidence: {payload.get('validation_confidence', '')}",
        f"- completion_recommendation: {payload.get('completion_recommendation', '')}",
        f"- human_review_required: {payload.get('human_review_required')}",
        f"- local_only: {payload.get('local_only')}",
        f"- execution_allowed: {payload.get('execution_allowed')}",
        f"- next_safe_action: {payload.get('next_safe_action', '')}",
    ]
    blockers = payload.get("blocked_reasons", []) if isinstance(payload.get("blocked_reasons"), list) else []
    if blockers:
        lines.extend(["", "## Blocked Reasons"])
        lines.extend(f"- {reason}" for reason in blockers)
    for key, title in (
        ("files_changed", "Files Changed"),
        ("what_changed", "What Changed"),
        ("tests_reported", "Tests Reported"),
        ("smoke_checks_reported", "Smoke Checks Reported"),
        ("warnings_or_blockers", "Warnings Or Blockers"),
    ):
        values = payload.get(key, []) if isinstance(payload.get(key), list) else []
        if values:
            lines.extend(["", f"## {title}"])
            lines.extend(f"- {value}" for value in values)
    return "\n".join(lines).rstrip()


def _next_safe_action(*, parsed: bool, blocked_reasons: list[str]) -> str:
    if parsed:
        return "Review the parsed evidence record manually before any queue completion decision."
    if any("Result file is missing" in reason for reason in blocked_reasons):
        return "Provide a local Codex result text or markdown file before parsing evidence."
    return "Resolve blocked reasons before parsing dispatch result evidence."


def _dedupe(values: list[str] | tuple[str, ...] | Any) -> list[str]:
    deduped: list[str] = []
    for value in values:
        text = str(value).strip()
        if text and text not in deduped:
            deduped.append(text)
    return deduped


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _error(error: str, details: dict[str, Any], payload: dict[str, Any] | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "command": COMMAND_NAME,
        "ok": False,
        "local_only": True,
        "error": error,
        "details": details,
    }
    if payload is not None:
        result["payload"] = payload
    return result
