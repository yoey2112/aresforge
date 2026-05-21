# Runnable Skeleton

## Purpose

Describe the human-triggered local operator surface with M9 local planning memory additions.

## Operator Shape

Command entrypoint:

- `python -m aresforge`

## Current Additions

- `plan-agent-queue`: read-only governance-aware intake and queue planning.
- `report-batch-readiness`: read-only multi-issue validation summary.
- `plan-batch-closeout`: read-only by default; optional explicit local snapshot write.
- `generate-sprint-issue-script`: output-only by default; optional explicit local planning write.
- `inspect-planning-state`: read-only local planning-state summary.
- `compare-planning-state`: read-only local planning-state drift comparison.
- `inspect-closeout-planning-drift`: read-only planning-state vs live closeout child discovery comparison.

## Automation Boundary

- Human-triggered only.
- Read-only/output-only defaults.
- Explicit local planning-state writes only when write flags are supplied.
- No autonomous setup/mutation, merge, closeout, labels, milestones, comments, releases, or tags.
- Issue #39 is excluded from active planning and mutation scope.
