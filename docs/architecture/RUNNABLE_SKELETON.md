# Runnable Skeleton

## Purpose

Describe the human-triggered local operator surface with M12 human-gated sprint issue creation planning integrated.

## Operator Shape

Command entrypoint:

- `python -m aresforge`

## Current Additions

- `plan-agent-queue`: read-only governance-aware intake and queue planning.
- `report-batch-readiness`: read-only multi-issue validation summary.
- `plan-batch-closeout`: read-only by default; optional explicit local snapshot write.
- `generate-sprint-issue-script`: output-only by default; optional explicit local planning write.
- `plan-sprint-issues`: read-only deterministic sprint issue creation planning output with human-gated mutation script generation.
- `inspect-planning-state`: read-only local planning-state summary.
- `compare-planning-state`: read-only local planning-state drift comparison.
- `inspect-closeout-planning-drift`: read-only planning-state vs live closeout child discovery comparison with explicit drift groups and readiness blocking signals.

## M12 Documentation Reconciliation State

- M12 planner contract, model/rendering, copy/paste-safe PowerShell output, CLI wiring, and regression coverage were delivered in merged integration work.
- Current pass documents the operator workflow for human-gated issue creation planning (`plan-sprint-issues`).
- Final source-of-truth reconciliation remains deferred to dedicated follow-up scope.

## Automation Boundary

- Human-triggered only.
- Read-only/output-only defaults.
- Explicit local planning-state writes only when write flags are supplied.
- No autonomous setup/mutation, merge, closeout, labels, milestones, comments, releases, or tags.
- Generated mutation scripts are copy/paste output only and require human review/execution.
- Verification/repair guidance is text-only and human-gated.

## Recommended Post-M12 Follow-Up

- Complete source-of-truth reconciliation for M12 documentation alignment in the dedicated follow-up scope.
