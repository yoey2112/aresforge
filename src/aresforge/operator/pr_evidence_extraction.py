from __future__ import annotations

import re
from typing import Any

from aresforge.operator.canonical_evidence_markers import parse_canonical_evidence_marker
from aresforge.operator.evidence_mapping_parser import parse_issue_evidence_mapping


MAPPING_STATE_MISSING = "missing"
MAPPING_STATE_AMBIGUOUS = "ambiguous"
MAPPING_STATE_UNMERGED = "unmerged"
MAPPING_STATE_READY = "ready"
MAPPING_STATE_UNKNOWN = "unknown"

_PR_NUMBER_PATTERN = re.compile(r"#?(?P<number>\d+)")
_COMMIT_PATTERN = re.compile(r"\b[0-9a-f]{7,40}\b", re.IGNORECASE)


def extract_pr_evidence_mapping(
    *,
    issue_number: int,
    issue_body: str,
    comments: list[dict[str, Any]],
    linked_pr_count: int,
    merged_pr_count: int,
) -> dict[str, Any]:
    canonical = _extract_canonical_candidates(issue_number=issue_number, issue_body=issue_body, comments=comments)
    legacy = parse_issue_evidence_mapping(
        issue_number=issue_number,
        issue_body=issue_body,
        comments=comments,
    )

    canonical_candidates = canonical["candidates"]
    canonical_unique_prs = sorted(
        set(candidate["pr_number"] for candidate in canonical_candidates if isinstance(candidate.get("pr_number"), int))
    )

    if len(canonical_unique_prs) > 1:
        return _result(
            issue_number=issue_number,
            mapping_state=MAPPING_STATE_AMBIGUOUS,
            source="canonical_marker",
            linked_pr_count=linked_pr_count,
            merged_pr_count=merged_pr_count,
            canonical=canonical,
            legacy=legacy,
        )

    if len(canonical_candidates) == 1:
        selected = canonical_candidates[0]
        pr_number = selected.get("pr_number")
        merge_status = selected.get("merge_status")
        normalized_merge_status = _normalize_merge_status(merge_status, merged_pr_count)
        if not isinstance(pr_number, int):
            mapping_state = MAPPING_STATE_MISSING
        elif normalized_merge_status == "merged":
            mapping_state = MAPPING_STATE_READY
        elif normalized_merge_status == "unmerged":
            mapping_state = MAPPING_STATE_UNMERGED
        else:
            mapping_state = MAPPING_STATE_UNKNOWN
        return _result(
            issue_number=issue_number,
            mapping_state=mapping_state,
            source="canonical_marker",
            linked_pr_count=linked_pr_count,
            merged_pr_count=merged_pr_count,
            canonical=canonical,
            legacy=legacy,
            selected=selected,
        )

    legacy_derived = legacy.get("derived_pr_evidence") if isinstance(legacy.get("derived_pr_evidence"), list) else []
    legacy_pr = legacy_derived[0] if legacy_derived else {}
    if isinstance(legacy_pr.get("number"), int):
        merged = merged_pr_count > 0 or isinstance(legacy_pr.get("merged_commit"), str)
        return _result(
            issue_number=issue_number,
            mapping_state=MAPPING_STATE_READY if merged else MAPPING_STATE_UNMERGED,
            source="legacy_mapping",
            linked_pr_count=linked_pr_count,
            merged_pr_count=merged_pr_count,
            canonical=canonical,
            legacy=legacy,
            selected={
                "pr_number": legacy_pr.get("number"),
                "branch": "",
                "commit": _normalize_commit(legacy_pr.get("merged_commit")),
                "merge_status": "merged" if merged else "unmerged",
                "evidence_status": "unknown",
            },
        )

    counts_state = _state_from_counts(linked_pr_count=linked_pr_count, merged_pr_count=merged_pr_count)
    return _result(
        issue_number=issue_number,
        mapping_state=counts_state,
        source="milestone_counts",
        linked_pr_count=linked_pr_count,
        merged_pr_count=merged_pr_count,
        canonical=canonical,
        legacy=legacy,
    )


def _extract_canonical_candidates(
    *,
    issue_number: int,
    issue_body: str,
    comments: list[dict[str, Any]],
) -> dict[str, Any]:
    sources = [issue_body or ""]
    sources.extend(
        comment.get("body", "")
        for comment in comments
        if isinstance(comment, dict) and isinstance(comment.get("body"), str)
    )
    candidates: list[dict[str, Any]] = []
    invalid_blocks = 0

    for source in sources:
        blocks = _extract_marker_blocks(source)
        for block in blocks:
            parsed = parse_canonical_evidence_marker(block)
            if parsed.marker_type != "pr_evidence":
                continue
            if parsed.invalid_reasons:
                invalid_blocks += 1
            parsed_issue = _parse_issue_number(parsed.required_fields.get("issue"))
            if parsed_issue != issue_number:
                continue
            candidates.append(
                {
                    "pr_number": _parse_pr_number(parsed.required_fields.get("pr")),
                    "branch": _clean(parsed.required_fields.get("branch")),
                    "commit": _normalize_commit(parsed.required_fields.get("commit")),
                    "merge_status": _clean(parsed.required_fields.get("merge_status")),
                    "evidence_status": _clean(parsed.required_fields.get("evidence_status")) or parsed.marker_state,
                    "marker_state": parsed.marker_state,
                }
            )

    return {
        "candidate_count": len(candidates),
        "invalid_block_count": invalid_blocks,
        "candidates": candidates,
    }


def _extract_marker_blocks(text: str) -> list[str]:
    begin = "[ARESFORGE_CANONICAL_EVIDENCE_MARKER]"
    end = "[/ARESFORGE_CANONICAL_EVIDENCE_MARKER]"
    lines = text.splitlines()
    blocks: list[str] = []
    i = 0
    while i < len(lines):
        if lines[i].strip() != begin:
            i += 1
            continue
        j = i + 1
        while j < len(lines) and lines[j].strip() != end:
            j += 1
        if j < len(lines):
            block_lines = lines[i : j + 1]
            blocks.append("\n".join(block_lines) + "\n")
            i = j + 1
            continue
        i += 1
    return blocks


def _state_from_counts(*, linked_pr_count: int, merged_pr_count: int) -> str:
    if linked_pr_count == 0 and merged_pr_count == 0:
        return MAPPING_STATE_MISSING
    if linked_pr_count > 1:
        return MAPPING_STATE_AMBIGUOUS
    if linked_pr_count >= 1 and merged_pr_count == 0:
        return MAPPING_STATE_UNMERGED
    if linked_pr_count >= 1 and merged_pr_count >= 1:
        return MAPPING_STATE_READY
    return MAPPING_STATE_UNKNOWN


def _result(
    *,
    issue_number: int,
    mapping_state: str,
    source: str,
    linked_pr_count: int,
    merged_pr_count: int,
    canonical: dict[str, Any],
    legacy: dict[str, Any],
    selected: dict[str, Any] | None = None,
) -> dict[str, Any]:
    selected_item = selected or {}
    return {
        "issue_number": issue_number,
        "mapping_state": mapping_state,
        "source": source,
        "pr_number": selected_item.get("pr_number"),
        "branch": _clean(selected_item.get("branch")),
        "commit": _normalize_commit(selected_item.get("commit")),
        "merge_status": _normalize_merge_status(selected_item.get("merge_status"), merged_pr_count),
        "evidence_status": _normalize_evidence_status(selected_item.get("evidence_status")),
        "linked_pr_count": linked_pr_count,
        "merged_pr_count": merged_pr_count,
        "canonical": canonical,
        "legacy": {
            "structured_blocks_detected": legacy.get("structured_blocks_detected"),
            "structured_blocks_matching_issue": legacy.get("structured_blocks_matching_issue"),
            "issue_specific_mapping_detected": legacy.get("issue_specific_mapping_detected"),
        },
    }


def _parse_pr_number(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    text = _clean(value)
    if not text:
        return None
    match = _PR_NUMBER_PATTERN.search(text)
    return int(match.group("number")) if match else None


def _parse_issue_number(value: Any) -> int | None:
    return _parse_pr_number(value)


def _normalize_merge_status(value: Any, merged_pr_count: int) -> str:
    text = _clean(value).lower()
    if text in {"merged", "ready", "closed"}:
        return "merged"
    if text in {"open", "unmerged", "pending"}:
        return "unmerged"
    if merged_pr_count > 0:
        return "merged"
    if merged_pr_count == 0 and text:
        return "unmerged"
    return "unknown"


def _normalize_evidence_status(value: Any) -> str:
    text = _clean(value).lower()
    if text in {"ready", "incomplete", "missing", "invalid", "unknown"}:
        return text
    return "unknown"


def _normalize_commit(value: Any) -> str:
    text = _clean(value).lower()
    match = _COMMIT_PATTERN.search(text)
    return match.group(0) if match else ""


def _clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()