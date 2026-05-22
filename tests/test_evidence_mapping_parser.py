from aresforge.operator.evidence_mapping_parser import parse_issue_evidence_mapping


def _comment(body: str) -> dict:
    return {"body": body}


def test_valid_structured_block_parses() -> None:
    payload = parse_issue_evidence_mapping(
        issue_number=299,
        issue_body=(
            "ARESFORGE_EVIDENCE_MAP_START\n"
            "Issue: #299\n"
            "Evidence Type: child-closeout\n"
            "Implemented By: PR #306\n"
            "Merged Commit: abcdef1234567\n"
            "Closeout Ready: true\n"
            "ARESFORGE_EVIDENCE_MAP_END\n"
        ),
        comments=[],
    )
    assert payload["issue_specific_mapping_detected"] is True
    assert payload["safe_to_trust_structured_mapping"] is True
    assert payload["derived_pr_evidence"][0]["number"] == 306


def test_missing_structured_block() -> None:
    payload = parse_issue_evidence_mapping(issue_number=299, issue_body="No mapping", comments=[])
    assert payload["issue_specific_mapping_detected"] is False
    assert payload["derived_pr_evidence"] == []


def test_malformed_structured_block_is_not_trusted() -> None:
    payload = parse_issue_evidence_mapping(
        issue_number=299,
        issue_body=(
            "ARESFORGE_EVIDENCE_MAP_START\n"
            "Issue: #299\n"
            "Implemented By: PR #306\n"
            "ARESFORGE_EVIDENCE_MAP_END\n"
        ),
        comments=[],
    )
    assert payload["malformed_structured_blocks_detected"] == 1
    assert payload["safe_to_trust_structured_mapping"] is False


def test_duplicate_structured_blocks_detected() -> None:
    body = (
        "ARESFORGE_EVIDENCE_MAP_START\nIssue: #299\nImplemented By: PR #306\nMerged Commit: abcdef1\nARESFORGE_EVIDENCE_MAP_END\n"
        "ARESFORGE_EVIDENCE_MAP_START\nIssue: #299\nImplemented By: PR #306\nMerged Commit: abcdef1\nARESFORGE_EVIDENCE_MAP_END\n"
    )
    payload = parse_issue_evidence_mapping(issue_number=299, issue_body=body, comments=[])
    assert payload["duplicate_structured_blocks_detected"] is True
    assert payload["safe_to_trust_structured_mapping"] is False


def test_conflicting_structured_blocks_detected() -> None:
    payload = parse_issue_evidence_mapping(
        issue_number=299,
        issue_body="",
        comments=[
            _comment(
                "ARESFORGE_EVIDENCE_MAP_START\nIssue: #299\nImplemented By: PR #306\nMerged Commit: abcdef1\nARESFORGE_EVIDENCE_MAP_END\n"
            ),
            _comment(
                "ARESFORGE_EVIDENCE_MAP_START\nIssue: #299\nImplemented By: PR #307\nMerged Commit: abcdef2\nARESFORGE_EVIDENCE_MAP_END\n"
            ),
        ],
    )
    assert payload["conflicting_structured_blocks_detected"] is True
    assert payload["safe_to_trust_structured_mapping"] is False


def test_legacy_evidence_comment_compatibility() -> None:
    payload = parse_issue_evidence_mapping(
        issue_number=297,
        issue_body="",
        comments=[
            _comment(
                "Issue #297\nImplemented by PR #304\nMerged main commit after PR merge: 3b2d2ba89a52d733985d4dcb9eb48a520213d64f"
            )
        ],
    )
    assert payload["legacy_fallback"]["matched"] is True
    assert payload["derived_pr_evidence"][0]["number"] == 304
