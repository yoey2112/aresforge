from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

STATE_PASS = "pass"
STATE_FAIL = "fail"
STATE_WARNING = "warning"
STATE_UNKNOWN = "unknown"

_VALID_STATES = {STATE_PASS, STATE_FAIL, STATE_WARNING, STATE_UNKNOWN}

_KNOWN_COMMANDS: tuple[str, ...] = (
    "git diff --check",
    "python -m pytest",
    "python -m aresforge inspect-repo-governance",
    "python -m aresforge inspect-milestone-dashboard",
    "python -m aresforge inspect-milestone-state",
    "python -m aresforge check-milestone-evidence-readiness",
    "python -m aresforge inspect-parent-closeout-readiness",
)

_PASS_PATTERN = re.compile(r"\b(pass(?:ed)?|ok\s*[:=]?\s*true|success(?:ful|fully)?|clean)\b", re.IGNORECASE)
_FAIL_PATTERN = re.compile(r"\b(fail(?:ed|ure)?|error|traceback|exception|blocked)\b", re.IGNORECASE)
_WARNING_PATTERN = re.compile(r"\b(warn(?:ing)?|degraded|partial|ambiguous)\b", re.IGNORECASE)


@dataclass(frozen=True)
class ValidationEntryInput:
    command: str
    output: str | None = None
    state: str | None = None


def normalize_validation_entry(entry: ValidationEntryInput) -> dict[str, str]:
    command = _normalize_command(entry.command)
    source_output = (entry.output or "").strip()

    if entry.state is not None:
        normalized_state = _coerce_state(entry.state)
    else:
        normalized_state = _infer_state_from_output(source_output)

    return {
        "command": command,
        "state": normalized_state,
        "summary_line": f"- {command}: {normalized_state}",
    }


def build_validation_summary(entries: list[ValidationEntryInput]) -> dict[str, Any]:
    normalized = [normalize_validation_entry(item) for item in entries]
    state_counts = {
        STATE_PASS: 0,
        STATE_FAIL: 0,
        STATE_WARNING: 0,
        STATE_UNKNOWN: 0,
    }
    for item in normalized:
        state_counts[item["state"]] += 1

    overall_state = _overall_state(state_counts)
    return {
        "overall_state": overall_state,
        "state_counts": state_counts,
        "commands": [item["command"] for item in normalized],
        "entries": normalized,
        "summary_lines": [item["summary_line"] for item in normalized],
    }


def _normalize_command(command: str) -> str:
    normalized = " ".join((command or "").strip().split())
    if not normalized:
        return "<unknown-command>"
    lower = normalized.lower()
    for known in _KNOWN_COMMANDS:
        if lower == known.lower():
            return known
    return normalized


def _infer_state_from_output(output: str) -> str:
    if not output:
        return STATE_UNKNOWN
    if _FAIL_PATTERN.search(output):
        return STATE_FAIL
    if _WARNING_PATTERN.search(output):
        return STATE_WARNING
    if _PASS_PATTERN.search(output):
        return STATE_PASS
    return STATE_UNKNOWN


def _coerce_state(state: str) -> str:
    normalized = state.strip().lower()
    return normalized if normalized in _VALID_STATES else STATE_UNKNOWN


def _overall_state(counts: dict[str, int]) -> str:
    if counts[STATE_FAIL] > 0:
        return STATE_FAIL
    if counts[STATE_WARNING] > 0:
        return STATE_WARNING
    if counts[STATE_UNKNOWN] > 0:
        return STATE_UNKNOWN
    return STATE_PASS