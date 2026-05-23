from __future__ import annotations

from dataclasses import dataclass

from aresforge.operator.evidence_templates import EvidenceTemplateSection, render_markdown_sections


@dataclass(frozen=True)
class EvidenceBundleInput:
    summary_lines: tuple[str, ...]
    issue_ref: str
    pr_ref: str | None
    branch_name: str | None
    commit_sha: str | None
    files_changed: tuple[str, ...]
    validation_lines: tuple[str, ...]
    safety_notes: tuple[str, ...]
    warnings: tuple[str, ...]


def render_evidence_bundle_text(bundle: EvidenceBundleInput) -> str:
    branch_commit_lines = _branch_commit_lines(bundle.branch_name, bundle.commit_sha)
    notes_warnings = bundle.warnings or ("- <none>",)
    sections = (
        EvidenceTemplateSection("### Summary", bundle.summary_lines),
        EvidenceTemplateSection("### Issue", (f"- {bundle.issue_ref}",)),
        EvidenceTemplateSection("### PR", (f"- {bundle.pr_ref}" if bundle.pr_ref else "- <none>",)),
        EvidenceTemplateSection("### Branch/Commit", branch_commit_lines),
        EvidenceTemplateSection("### Files changed", tuple(f"- {path}" for path in bundle.files_changed)),
        EvidenceTemplateSection("### Validation", bundle.validation_lines),
        EvidenceTemplateSection("### Safety posture", bundle.safety_notes),
        EvidenceTemplateSection("### Notes/warnings", notes_warnings),
    )
    return render_markdown_sections(sections)


def _branch_commit_lines(branch_name: str | None, commit_sha: str | None) -> tuple[str, ...]:
    lines: list[str] = []
    lines.append(f"- Branch: {branch_name}" if branch_name else "- Branch: <none>")
    lines.append(f"- Commit: {commit_sha}" if commit_sha else "- Commit: <none>")
    return tuple(lines)

