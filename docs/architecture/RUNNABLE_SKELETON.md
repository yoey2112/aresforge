# Runnable Skeleton

## Purpose

Describe the human-triggered local operator surface and M6 queue-planning additions.

## Operator Shape

Command entrypoint:

- `python -m aresforge`

## M6 Additions

- `plan-agent-queue`: read-only issue intake mapping to queue/orchestration MVP state.
- `report-batch-readiness`: read-only multi-issue validation and closeout readiness summary.

## Sprint Issue Creation Operator Standard

- Parent/child sprint issue creation should use `docs/operator/HARDENED_SPRINT_ISSUE_CREATION_TEMPLATE.md`.
- The template is human-run and includes hard gates for body-file validation, issue URL/number parsing, parent update sequencing, and cleanup-after-verification only.
- The template does not introduce autonomous issue creation or other autonomous GitHub mutation.

## Existing Closeout Posture

- `qa-review-pr` remains read-only.
- `qa-closeout-pr` remains dry-run default and execute-gated.
- M6 adds clearer close-issue failure diagnostics and state re-check support.

## Automation Boundary

- Human-triggered only.
- Read-only-first defaults.
- No autonomous setup/mutation, merge, or closeout.
- Issue #39 is excluded from mutation scope.
