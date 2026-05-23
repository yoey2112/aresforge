from aresforge.operator.canonical_evidence_markers import (
    MARKER_STATE_INCOMPLETE,
    MARKER_STATE_INVALID,
    MARKER_STATE_MISSING,
    MARKER_STATE_READY,
    MARKER_STATE_UNKNOWN,
    MARKER_TYPE_CHILD_EVIDENCE,
    create_canonical_evidence_marker,
    parse_canonical_evidence_marker,
)


def test_create_canonical_evidence_marker_ready_state() -> None:
    marker = create_canonical_evidence_marker(
        marker_type=MARKER_TYPE_CHILD_EVIDENCE,
        required_fields={
            "parent_issue": "#400",
            "child_issue": "#402",
            "branch": "m24-402-canonical-marker-schema",
            "commit": "abc1234",
            "pr": "#412",
            "validation_summary": "pytest pass",
            "safety_notes": "read-only by default",
        },
        optional_fields={"closeout_status": "in_progress"},
    )

    assert marker.marker_state == MARKER_STATE_READY
    assert marker.missing_required_fields == ()
    assert marker.invalid_reasons == ()
    assert marker.required_fields["parent_issue"] == "#400"
    assert marker.optional_fields["closeout_status"] == "in_progress"


def test_create_canonical_evidence_marker_missing_state() -> None:
    marker = create_canonical_evidence_marker(
        marker_type=MARKER_TYPE_CHILD_EVIDENCE,
        required_fields={},
    )

    assert marker.marker_state == MARKER_STATE_MISSING
    assert marker.missing_required_fields == (
        "parent_issue",
        "child_issue",
        "branch",
        "commit",
        "pr",
        "validation_summary",
        "safety_notes",
    )


def test_create_canonical_evidence_marker_incomplete_state() -> None:
    marker = create_canonical_evidence_marker(
        marker_type=MARKER_TYPE_CHILD_EVIDENCE,
        required_fields={
            "parent_issue": "#400",
            "child_issue": "#402",
            "branch": "m24-402-canonical-marker-schema",
        },
    )

    assert marker.marker_state == MARKER_STATE_INCOMPLETE
    assert marker.missing_required_fields == (
        "commit",
        "pr",
        "validation_summary",
        "safety_notes",
    )


def test_create_canonical_evidence_marker_invalid_state() -> None:
    marker = create_canonical_evidence_marker(
        marker_type=MARKER_TYPE_CHILD_EVIDENCE,
        marker_state="ready",
        required_fields={"parent_issue": "#400"},
    )

    assert marker.marker_state == MARKER_STATE_INVALID
    assert "state_ready_with_missing_required_fields" in marker.invalid_reasons


def test_create_canonical_evidence_marker_unknown_type() -> None:
    marker = create_canonical_evidence_marker(
        marker_type="custom",
        required_fields={"foo": "bar"},
    )

    assert marker.marker_state == MARKER_STATE_UNKNOWN
    assert marker.invalid_reasons == ("unknown_marker_type:custom",)


def test_rendered_marker_is_deterministic_parse_friendly_and_copy_paste_safe() -> None:
    marker = create_canonical_evidence_marker(
        marker_type=MARKER_TYPE_CHILD_EVIDENCE,
        required_fields={
            "parent_issue": "#400",
            "child_issue": "#402",
            "branch": "m24-402-canonical-marker-schema",
            "commit": "abc1234",
            "pr": "#412",
            "validation_summary": "pytest pass",
            "safety_notes": "read-only by default",
        },
        optional_fields={
            "zeta": "z",
            "alpha": "a",
        },
    )

    rendered = marker.render()

    assert rendered.startswith("[ARESFORGE_CANONICAL_EVIDENCE_MARKER]\n")
    assert "marker_type: child_evidence" in rendered
    assert "marker_state: ready" in rendered
    assert rendered.index("optional.alpha: a") < rendered.index("optional.zeta: z")
    assert rendered.endswith("[/ARESFORGE_CANONICAL_EVIDENCE_MARKER]\n")
    assert "```" not in rendered

    parsed = parse_canonical_evidence_marker(rendered)
    assert parsed.marker_type == marker.marker_type
    assert parsed.marker_state == MARKER_STATE_READY
    assert parsed.required_fields == marker.required_fields
    assert parsed.optional_fields == marker.optional_fields