# Runnable Skeleton

## Purpose

Describe the human-triggered local operator surface and M6 queue-planning additions.

## Operator Shape

Command entrypoint:

- `python -m aresforge`

## M6 Additions

- `plan-agent-queue`: read-only issue intake mapping to queue/orchestration MVP state.
- `report-batch-readiness`: read-only multi-issue validation and closeout readiness summary.

## Existing Closeout Posture

- `qa-review-pr` remains read-only.
- `qa-closeout-pr` remains dry-run default and execute-gated.
- M6 adds clearer close-issue failure diagnostics and state re-check support.

## Automation Boundary

- Human-triggered only.
- Read-only-first defaults.
- No autonomous setup/mutation, merge, or closeout.
- Issue #39 is excluded from mutation scope.
