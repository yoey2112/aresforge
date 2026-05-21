# Runnable Skeleton

## Purpose

Describe the human-triggered local operator surface with M7 governance-aware intake and closeout planning additions.

## Operator Shape

Command entrypoint:

- `python -m aresforge`

## M7 Additions

- `plan-agent-queue`: read-only governance-aware intake and queue planning contract.
- `report-batch-readiness`: read-only multi-issue validation and closeout readiness summary.
- `plan-batch-closeout`: read-only parent/child closeout readiness planning.

## Existing Closeout Posture

- `qa-review-pr` remains read-only.
- `qa-closeout-pr` remains dry-run default and execute-gated.
- `plan-batch-closeout` does not close issues, comment, or mutate GitHub state.

## Automation Boundary

- Human-triggered only.
- Read-only-first defaults.
- No autonomous setup/mutation, merge, or closeout.
- Issue #39 is excluded from active planning and mutation scope.
- Issue #179 remains complete and unchanged.
