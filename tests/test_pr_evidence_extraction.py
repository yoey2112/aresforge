from aresforge.operator.pr_evidence_extraction import extract_pr_evidence_mapping


def _canonical_pr_marker(*, issue: int, pr: int, merge_status: str, evidence_status: str) -> str:
    return "\n".join(
        [
            "[ARESFORGE_CANONICAL_EVIDENCE_MARKER]",
            "marker_type: pr_evidence",
            "marker_state: ready",
            "required.issue: #" + str(issue),
            "required.pr: #" + str(pr),
            "required.branch: m24-404-pr-marker-template",
            "required.commit: abc1234",
            "required.changed_files: src/aresforge/cli.py",
            "required.validation_summary: pytest pass",
            "required.merge_status: " + merge_status,
            "required.safety_posture: read-only",
            "required.evidence_status: " + evidence_status,
            "missing_required_fields: <none>",
            "invalid_reasons: <none>",
            "[/ARESFORGE_CANONICAL_EVIDENCE_MARKER]",
        ]
    )


def test_extract_pr_evidence_mapping_canonical_ready() -> None:
    payload = extract_pr_evidence_mapping(
        issue_number=404,
        issue_body=_canonical_pr_marker(issue=404, pr=414, merge_status="merged", evidence_status="ready"),
        comments=[],
        linked_pr_count=1,
        merged_pr_count=1,
    )

    assert payload["mapping_state"] == "ready"
    assert payload["source"] == "canonical_marker"
    assert payload["pr_number"] == 414
    assert payload["merge_status"] == "merged"


def test_extract_pr_evidence_mapping_canonical_unmerged() -> None:
    payload = extract_pr_evidence_mapping(
        issue_number=404,
        issue_body=_canonical_pr_marker(issue=404, pr=414, merge_status="open", evidence_status="incomplete"),
        comments=[],
        linked_pr_count=1,
        merged_pr_count=0,
    )

    assert payload["mapping_state"] == "unmerged"
    assert payload["merge_status"] == "unmerged"


def test_extract_pr_evidence_mapping_canonical_ambiguous() -> None:
    body = "\n\n".join(
        [
            _canonical_pr_marker(issue=404, pr=414, merge_status="merged", evidence_status="ready"),
            _canonical_pr_marker(issue=404, pr=415, merge_status="merged", evidence_status="ready"),
        ]
    )
    payload = extract_pr_evidence_mapping(
        issue_number=404,
        issue_body=body,
        comments=[],
        linked_pr_count=2,
        merged_pr_count=1,
    )

    assert payload["mapping_state"] == "ambiguous"
    assert payload["source"] == "canonical_marker"


def test_extract_pr_evidence_mapping_legacy_ready_fallback() -> None:
    payload = extract_pr_evidence_mapping(
        issue_number=404,
        issue_body="Issue #404 Implemented by PR #414\nMerged commit: abc1234",
        comments=[],
        linked_pr_count=1,
        merged_pr_count=1,
    )

    assert payload["mapping_state"] == "ready"
    assert payload["source"] == "legacy_mapping"
    assert payload["pr_number"] == 414


def test_extract_pr_evidence_mapping_missing_from_counts() -> None:
    payload = extract_pr_evidence_mapping(
        issue_number=404,
        issue_body="",
        comments=[],
        linked_pr_count=0,
        merged_pr_count=0,
    )

    assert payload["mapping_state"] == "missing"
    assert payload["source"] == "milestone_counts"


def test_extract_pr_evidence_mapping_unknown_state() -> None:
    payload = extract_pr_evidence_mapping(
        issue_number=404,
        issue_body="No clear mapping but linked count is inconsistent.",
        comments=[],
        linked_pr_count=0,
        merged_pr_count=2,
    )

    assert payload["mapping_state"] == "unknown"