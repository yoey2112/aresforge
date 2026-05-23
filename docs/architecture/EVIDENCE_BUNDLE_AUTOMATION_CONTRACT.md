# Evidence Bundle Automation Contract

## Purpose

Define deterministic, reusable evidence bundle generation for child closeout, parent closeout, PR body updates, validation summaries, and handoff/source-of-truth documentation support.

## Bundle Types

- child_closeout_evidence_bundle
- parent_closeout_evidence_bundle
- pr_evidence_bundle
- validation_summary_bundle
- handoff_summary_bundle
- documentation_reconciliation_bundle

## Contract Requirements

- Evidence bundle generation is read-only by default.
- Generation logic and mutation execution are separated.
- Mutation paths require explicit operator approval and targeted issue or PR scope.
- Output must be deterministic and fixture-testable.
- Output must include explicit safety notes and warnings where applicable.

## Mutation Boundary

- Generation commands produce text packages and guidance only unless an explicit execution mode is provided and intentionally invoked.
- Issue comments, issue closeout, and PR body updates remain operator-approved targeted mutations.
- Bulk issue closure and broad autonomous mutation are out of scope.

## PowerShell Safety

- Keep issue/comment command examples plain text and copy/paste safe.
- Avoid nested markdown fences inside PowerShell here-strings.

