from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


MARKER_TYPE_CHILD_EVIDENCE = "child_evidence"
MARKER_TYPE_PR_EVIDENCE = "pr_evidence"
MARKER_TYPE_PARENT_CLOSEOUT_EVIDENCE = "parent_closeout_evidence"
MARKER_TYPE_RECONCILIATION_AUDIT = "reconciliation_audit"

CANONICAL_MARKER_TYPES: tuple[str, ...] = (
    MARKER_TYPE_CHILD_EVIDENCE,
    MARKER_TYPE_PR_EVIDENCE,
    MARKER_TYPE_PARENT_CLOSEOUT_EVIDENCE,
    MARKER_TYPE_RECONCILIATION_AUDIT,
)

MARKER_STATE_READY = "ready"
MARKER_STATE_INCOMPLETE = "incomplete"
MARKER_STATE_MISSING = "missing"
MARKER_STATE_INVALID = "invalid"
MARKER_STATE_UNKNOWN = "unknown"

CANONICAL_MARKER_STATES: tuple[str, ...] = (
    MARKER_STATE_READY,
    MARKER_STATE_INCOMPLETE,
    MARKER_STATE_MISSING,
    MARKER_STATE_INVALID,
    MARKER_STATE_UNKNOWN,
)

REQUIRED_FIELDS_BY_TYPE: dict[str, tuple[str, ...]] = {
    MARKER_TYPE_CHILD_EVIDENCE: (
        "parent_issue",
        "child_issue",
        "branch",
        "commit",
        "pr",
        "validation_summary",
        "safety_notes",
    ),
    MARKER_TYPE_PR_EVIDENCE: (
        "issue",
        "pr",
        "branch",
        "commit",
        "changed_files",
        "validation_summary",
        "merge_status",
        "safety_posture",
        "evidence_status",
    ),
    MARKER_TYPE_PARENT_CLOSEOUT_EVIDENCE: (
        "parent_issue",
        "child_issue_list",
        "child_to_pr_mapping",
        "final_main_head",
        "final_validation_results",
        "readiness_gate_summary",
        "safety_confirmations",
        "closeout_readiness_state",
    ),
    MARKER_TYPE_RECONCILIATION_AUDIT: (
        "baseline_snapshot",
        "post_reconciliation_snapshot",
        "snapshot_diff",
        "audit_classification",
        "warnings_deviations",
    ),
}

_BEGIN_MARKER = "[ARESFORGE_CANONICAL_EVIDENCE_MARKER]"
_END_MARKER = "[/ARESFORGE_CANONICAL_EVIDENCE_MARKER]"


@dataclass(frozen=True)
class CanonicalEvidenceMarker:
    marker_type: str
    marker_state: str
    required_fields: dict[str, str]
    optional_fields: dict[str, str]
    missing_required_fields: tuple[str, ...]
    invalid_reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "marker_type": self.marker_type,
            "marker_state": self.marker_state,
            "required_fields": dict(self.required_fields),
            "optional_fields": dict(self.optional_fields),
            "missing_required_fields": list(self.missing_required_fields),
            "invalid_reasons": list(self.invalid_reasons),
        }

    def render(self) -> str:
        return render_canonical_evidence_marker(self)


def create_canonical_evidence_marker(
    *,
    marker_type: str,
    required_fields: Mapping[str, Any] | None = None,
    optional_fields: Mapping[str, Any] | None = None,
    marker_state: str | None = None,
) -> CanonicalEvidenceMarker:
    normalized_type = _normalize_token(marker_type)
    normalized_required = _normalize_fields(required_fields)
    normalized_optional = _normalize_fields(optional_fields)

    invalid_reasons: list[str] = []
    if normalized_type not in REQUIRED_FIELDS_BY_TYPE:
        invalid_reasons.append(f"unknown_marker_type:{normalized_type or '<empty>'}")
        expected_required_fields: tuple[str, ...] = ()
    else:
        expected_required_fields = REQUIRED_FIELDS_BY_TYPE[normalized_type]

    if marker_state is not None and marker_state not in CANONICAL_MARKER_STATES:
        invalid_reasons.append(f"invalid_marker_state:{marker_state}")

    missing_required_fields = tuple(
        field for field in expected_required_fields if not _is_non_empty(normalized_required.get(field))
    )
    derived_state = _derive_state(
        marker_type=normalized_type,
        expected_required_fields=expected_required_fields,
        missing_required_fields=missing_required_fields,
        invalid_reasons=tuple(invalid_reasons),
    )

    selected_state = marker_state if marker_state in CANONICAL_MARKER_STATES else derived_state

    if selected_state == MARKER_STATE_READY and missing_required_fields:
        invalid_reasons.append("state_ready_with_missing_required_fields")
    if selected_state in (MARKER_STATE_MISSING, MARKER_STATE_INCOMPLETE) and not missing_required_fields:
        invalid_reasons.append("state_not_ready_without_missing_required_fields")

    has_non_unknown_invalid_reasons = any(
        not reason.startswith("unknown_marker_type:") for reason in invalid_reasons
    )
    if has_non_unknown_invalid_reasons:
        final_state = MARKER_STATE_INVALID
    elif any(reason.startswith("unknown_marker_type:") for reason in invalid_reasons):
        final_state = MARKER_STATE_UNKNOWN
    else:
        final_state = selected_state

    required_field_payload = {
        field: normalized_required.get(field, "") for field in sorted(expected_required_fields)
    }

    return CanonicalEvidenceMarker(
        marker_type=normalized_type,
        marker_state=final_state,
        required_fields=required_field_payload,
        optional_fields={name: normalized_optional[name] for name in sorted(normalized_optional.keys())},
        missing_required_fields=missing_required_fields,
        invalid_reasons=tuple(sorted(set(invalid_reasons))),
    )


def render_canonical_evidence_marker(marker: CanonicalEvidenceMarker) -> str:
    lines: list[str] = [_BEGIN_MARKER]
    lines.append(f"marker_type: {marker.marker_type}")
    lines.append(f"marker_state: {marker.marker_state}")
    for field_name, value in marker.required_fields.items():
        lines.append(f"required.{field_name}: {value or '<missing>'}")
    for field_name, value in marker.optional_fields.items():
        lines.append(f"optional.{field_name}: {value}")
    lines.append(
        "missing_required_fields: "
        + (", ".join(marker.missing_required_fields) if marker.missing_required_fields else "<none>")
    )
    lines.append(
        "invalid_reasons: " + (", ".join(marker.invalid_reasons) if marker.invalid_reasons else "<none>")
    )
    lines.append(_END_MARKER)
    return "\n".join(lines) + "\n"


def parse_canonical_evidence_marker(text: str) -> CanonicalEvidenceMarker:
    parsed = _parse_marker_lines(text)
    marker_type = parsed.pop("marker_type", "")
    marker_state = parsed.pop("marker_state", None)
    required: dict[str, str] = {}
    optional: dict[str, str] = {}
    for key, value in parsed.items():
        if key.startswith("required."):
            required[key.removeprefix("required.")] = "" if value == "<missing>" else value
        elif key.startswith("optional."):
            optional[key.removeprefix("optional.")] = value
    return create_canonical_evidence_marker(
        marker_type=marker_type,
        marker_state=marker_state,
        required_fields=required,
        optional_fields=optional,
    )


def _parse_marker_lines(text: str) -> dict[str, str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if _BEGIN_MARKER not in lines or _END_MARKER not in lines:
        return {}
    start = lines.index(_BEGIN_MARKER) + 1
    end = lines.index(_END_MARKER)
    body = lines[start:end]
    parsed: dict[str, str] = {}
    for line in body:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        parsed[_normalize_token(key)] = value.strip()
    return parsed


def _derive_state(
    *,
    marker_type: str,
    expected_required_fields: tuple[str, ...],
    missing_required_fields: tuple[str, ...],
    invalid_reasons: tuple[str, ...],
) -> str:
    if marker_type not in REQUIRED_FIELDS_BY_TYPE:
        return MARKER_STATE_UNKNOWN
    if any(not reason.startswith("unknown_marker_type:") for reason in invalid_reasons):
        return MARKER_STATE_INVALID
    if not expected_required_fields:
        return MARKER_STATE_UNKNOWN
    if len(missing_required_fields) == len(expected_required_fields):
        return MARKER_STATE_MISSING
    if missing_required_fields:
        return MARKER_STATE_INCOMPLETE
    return MARKER_STATE_READY


def _normalize_fields(fields: Mapping[str, Any] | None) -> dict[str, str]:
    if fields is None:
        return {}
    normalized: dict[str, str] = {}
    for key, value in fields.items():
        normalized[_normalize_token(str(key))] = _stringify_value(value)
    return normalized


def _stringify_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple, set)):
        return ", ".join(_stringify_value(item) for item in value)
    return str(value).strip()


def _normalize_token(value: str) -> str:
    return value.strip().lower()


def _is_non_empty(value: str | None) -> bool:
    if value is None:
        return False
    return bool(value.strip())