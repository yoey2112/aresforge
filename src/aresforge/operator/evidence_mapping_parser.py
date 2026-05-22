from __future__ import annotations

import re
from typing import Any

START_MARKER = "ARESFORGE_EVIDENCE_MAP_START"
END_MARKER = "ARESFORGE_EVIDENCE_MAP_END"

_ISSUE_PATTERN = re.compile(r"^Issue:\s*#(?P<number>\d+)\s*$", re.IGNORECASE)
_TYPE_PATTERN = re.compile(r"^Evidence Type:\s*(?P<value>.+?)\s*$", re.IGNORECASE)
_PR_PATTERN = re.compile(r"^Implemented By:\s*PR\s+#(?P<number>\d+)\s*$", re.IGNORECASE)
_COMMIT_PATTERN = re.compile(r"^Merged Commit:\s*(?P<sha>[0-9a-fA-F]{7,40})\s*$", re.IGNORECASE)
_READY_PATTERN = re.compile(r"^Closeout Ready:\s*(?P<value>true|false)\s*$", re.IGNORECASE)
_LEGACY_PR_PATTERN = re.compile(r"\bImplemented by PR\s+#(?P<number>\d+)\b", re.IGNORECASE)
_LEGACY_COMMIT_PATTERN = re.compile(r"\bMerged (?:main )?commit(?: after PR merge)?:\s*(?P<sha>[0-9a-fA-F]{7,40})\b")


def parse_issue_evidence_mapping(
    *,
    issue_number: int,
    issue_body: str,
    comments: list[dict[str, Any]],
) -> dict[str, Any]:
    blocks: list[dict[str, Any]] = []
    malformed_blocks: list[dict[str, Any]] = []
    for source, text in _iter_sources(issue_body=issue_body, comments=comments):
        source_blocks, source_malformed = _parse_structured_blocks(text=text, source=source)
        blocks.extend(source_blocks)
        malformed_blocks.extend(source_malformed)

    matching_blocks = [item for item in blocks if item.get("issue_number") == issue_number]
    conflicting = _conflicting_blocks(matching_blocks)
    duplicates = _duplicate_blocks(matching_blocks)
    selected = _select_block(matching_blocks)
    legacy = _parse_legacy_fallback(issue_number=issue_number, issue_body=issue_body, comments=comments)

    mapped_pr = selected.get("pr_number") if isinstance(selected, dict) else None
    mapped_commit = selected.get("merged_commit") if isinstance(selected, dict) else None
    if mapped_pr is None:
        mapped_pr = legacy.get("pr_number")
    if mapped_commit is None:
        mapped_commit = legacy.get("merged_commit")

    return {
        "structured_blocks_detected": len(blocks),
        "structured_blocks_matching_issue": len(matching_blocks),
        "malformed_structured_blocks_detected": len(malformed_blocks),
        "duplicate_structured_blocks_detected": bool(duplicates),
        "conflicting_structured_blocks_detected": bool(conflicting),
        "selected_structured_block": selected,
        "legacy_fallback": legacy,
        "issue_specific_mapping_detected": bool(selected or legacy.get("matched")),
        "safe_to_trust_structured_mapping": bool(selected and not conflicting and not duplicates),
        "derived_pr_evidence": [
            {
                "number": mapped_pr,
                "url": None,
                "title": None,
                "state": "MERGED",
                "merged_at": None,
                "source": "structured_evidence_map" if selected else "legacy_evidence_map",
                "merged_commit": mapped_commit,
            }
        ]
        if isinstance(mapped_pr, int)
        else [],
        "signals": {
            "structured_conflicts": conflicting,
            "structured_duplicates": duplicates,
            "malformed_blocks": malformed_blocks,
        },
    }


def _iter_sources(*, issue_body: str, comments: list[dict[str, Any]]) -> list[tuple[str, str]]:
    sources: list[tuple[str, str]] = [("issue_body", issue_body or "")]
    for idx, comment in enumerate(comments):
        body = comment.get("body")
        if isinstance(body, str):
            sources.append((f"comment:{idx}", body))
    return sources


def _parse_structured_blocks(*, text: str, source: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    lines = text.splitlines()
    i = 0
    parsed: list[dict[str, Any]] = []
    malformed: list[dict[str, Any]] = []
    while i < len(lines):
        if lines[i].strip() != START_MARKER:
            i += 1
            continue
        j = i + 1
        payload_lines: list[str] = []
        while j < len(lines) and lines[j].strip() != END_MARKER:
            payload_lines.append(lines[j])
            j += 1
        if j >= len(lines):
            malformed.append({"source": source, "error": "missing_end_marker"})
            break
        parsed_block = _parse_block_lines(payload_lines)
        if parsed_block.get("ok"):
            parsed.append({"source": source, **parsed_block})
        else:
            malformed.append({"source": source, "error": parsed_block.get("error", "malformed_block")})
        i = j + 1
    return parsed, malformed


def _parse_block_lines(lines: list[str]) -> dict[str, Any]:
    issue_number: int | None = None
    evidence_type: str | None = None
    pr_number: int | None = None
    merged_commit: str | None = None
    closeout_ready: bool | None = None
    for line in lines:
        text = line.strip()
        if not text or text.lower().startswith("validation:") or text.startswith("- "):
            continue
        if match := _ISSUE_PATTERN.match(text):
            issue_number = int(match.group("number"))
            continue
        if match := _TYPE_PATTERN.match(text):
            evidence_type = match.group("value").strip()
            continue
        if match := _PR_PATTERN.match(text):
            pr_number = int(match.group("number"))
            continue
        if match := _COMMIT_PATTERN.match(text):
            merged_commit = match.group("sha").lower()
            continue
        if match := _READY_PATTERN.match(text):
            closeout_ready = match.group("value").lower() == "true"
            continue
    if not isinstance(issue_number, int):
        return {"ok": False, "error": "missing_issue_number"}
    if not isinstance(pr_number, int):
        return {"ok": False, "error": "missing_pr_number"}
    if not isinstance(merged_commit, str):
        return {"ok": False, "error": "missing_merged_commit"}
    if evidence_type is None:
        evidence_type = "child-closeout"
    return {
        "ok": True,
        "issue_number": issue_number,
        "evidence_type": evidence_type,
        "pr_number": pr_number,
        "merged_commit": merged_commit,
        "closeout_ready": closeout_ready,
    }


def _duplicate_blocks(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if len(blocks) <= 1:
        return []
    first = blocks[0]
    duplicates: list[dict[str, Any]] = []
    for item in blocks[1:]:
        if (
            item.get("pr_number") == first.get("pr_number")
            and item.get("merged_commit") == first.get("merged_commit")
            and item.get("evidence_type") == first.get("evidence_type")
        ):
            duplicates.append(item)
    return duplicates


def _conflicting_blocks(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if len(blocks) <= 1:
        return []
    baseline = blocks[0]
    conflicts: list[dict[str, Any]] = []
    for item in blocks[1:]:
        if item.get("pr_number") != baseline.get("pr_number") or item.get("merged_commit") != baseline.get(
            "merged_commit"
        ):
            conflicts.append(item)
    return conflicts


def _select_block(blocks: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not blocks:
        return None
    if _conflicting_blocks(blocks) or _duplicate_blocks(blocks):
        return None
    return blocks[0]


def _parse_legacy_fallback(*, issue_number: int, issue_body: str, comments: list[dict[str, Any]]) -> dict[str, Any]:
    texts = [issue_body or ""] + [comment.get("body") or "" for comment in comments if isinstance(comment, dict)]
    for text in texts:
        issue_match = re.search(rf"\bIssue\s+#?{issue_number}\b", text, re.IGNORECASE)
        pr_match = _LEGACY_PR_PATTERN.search(text)
        commit_match = _LEGACY_COMMIT_PATTERN.search(text)
        if issue_match and pr_match:
            return {
                "matched": True,
                "pr_number": int(pr_match.group("number")),
                "merged_commit": commit_match.group("sha").lower() if commit_match else None,
            }
    return {"matched": False, "pr_number": None, "merged_commit": None}
