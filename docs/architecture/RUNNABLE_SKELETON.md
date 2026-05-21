# Runnable Skeleton

## Purpose

Describe the human-triggered local operator surface with M11 closeout planning drift inspection integrated.

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
- `inspect-closeout-planning-drift`: read-only planning-state vs live closeout child discovery comparison with explicit drift groups and readiness blocking signals.

## M11 Reconciliation State

- comparison contract, planning-state load path, child-group drift comparison, evidence summary improvements, and regression fixtures were delivered in merged integration work
- current pass reconciles operator/source-of-truth documentation for final M11 closeout

## Automation Boundary

- Human-triggered only.
- Read-only/output-only defaults.
- Explicit local planning-state writes only when write flags are supplied.
- No autonomous setup/mutation, merge, closeout, labels, milestones, comments, releases, or tags.
- Issue #39 is excluded from active planning and mutation scope.

## Recommended Post-M11 Follow-Up

- reduce recurring protected historical issue references in active governance/operator paths while retaining historical validation evidence requirements.
