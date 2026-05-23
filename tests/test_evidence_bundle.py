from aresforge.operator.evidence_bundle import EvidenceBundleInput, render_evidence_bundle_text


def test_render_evidence_bundle_text_is_deterministic_and_complete() -> None:
    payload = EvidenceBundleInput(
        summary_lines=("- Added reusable evidence template model.",),
        issue_ref="Issue: #364",
        pr_ref="PR: #373",
        branch_name="codex/m22-364-evidence-template-model",
        commit_sha="abc123",
        files_changed=("src/aresforge/operator/evidence_bundle.py", "tests/test_evidence_bundle.py"),
        validation_lines=("- git diff --check: pass", "- python -m pytest: pass"),
        safety_notes=(
            "- Read-only by default.",
            "- Targeted mutation requires explicit operator approval.",
        ),
        warnings=("- No deviations observed.",),
    )

    rendered = render_evidence_bundle_text(payload)

    assert "### Summary" in rendered
    assert "### Issue" in rendered
    assert "### PR" in rendered
    assert "### Branch/Commit" in rendered
    assert "### Files changed" in rendered
    assert "### Validation" in rendered
    assert "### Safety posture" in rendered
    assert "### Notes/warnings" in rendered
    assert rendered.index("### Summary") < rendered.index("### Validation")
    assert "Issue: #364" in rendered
    assert "PR: #373" in rendered
    assert "```" not in rendered


def test_render_evidence_bundle_text_handles_missing_optional_fields() -> None:
    payload = EvidenceBundleInput(
        summary_lines=("- Placeholder",),
        issue_ref="Issue: #364",
        pr_ref=None,
        branch_name=None,
        commit_sha=None,
        files_changed=(),
        validation_lines=(),
        safety_notes=(),
        warnings=(),
    )

    rendered = render_evidence_bundle_text(payload)

    assert "- <none>" in rendered
    assert "- Branch: <none>" in rendered
    assert "- Commit: <none>" in rendered

