# AresForge Roadmap

## Current Milestones

### M0-M19

Status: Completed.

### M20 - Operator-approved GitHub Mutation Orchestration

Status: Final reconciliation in progress (`#334` only).

Parent issue:

- #326 M20 operator-approved GitHub mutation orchestration (OPEN)

Child issues:

- #327 CLOSED via PR #335
- #328 CLOSED via PR #336
- #329 CLOSED via PR #337
- #330 CLOSED via PR #338
- #331 CLOSED via PR #339
- #332 CLOSED via PR #340
- #333 CLOSED via PR #341
- #334 OPEN (final source-of-truth reconciliation, must be processed last)

Delivered M20 outcomes:

- `plan-github-mutation`
- `execute-github-issue-comment`
- `execute-github-issue-close`
- `prepare-pr-body-update`
- `inspect-github-mutation-audit-log`
- operator-approved mutation orchestration contract and lifecycle boundaries
- local audit logging plus targeted recovery guidance
- end-to-end operator-approved mutation workflow documentation

M20 safety posture:

- no autonomous broad mutation
- no bulk closure
- no parent closure before all children are closed/accounted for
- mutation execution defaults to dry-run/planning unless explicitly approved
- every child is executed with dedicated branch, PR, validation, evidence comment, and targeted closeout
- final reconciliation kept last and docs-focused
- prior milestones are not mutated unless explicitly required for M20 documentation references

M20 validation bundle:

- `git diff --check`
- `python -m pytest`
- `python -m aresforge inspect-repo-governance`
- `python -m aresforge inspect-milestone-dashboard --parent-issue 326`
- `python -m aresforge inspect-milestone-state --parent-issue 326`
- `python -m aresforge check-milestone-evidence-readiness --parent-issue 326`
- `python -m aresforge inspect-parent-closeout-readiness --parent-issue 326`

Known non-blocking warning:

- M20 child discovery mismatch persists in read-only milestone inspectors for parent `#326` due to lineage parsing expectations.

## Standing Boundaries

- No autonomous mutation without explicit mode selection.
- No autonomous queue workers.
- No automatic PR merge.
- No unattended background execution.
