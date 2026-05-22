# Runnable Skeleton

## Purpose

Describe the human-triggered local operator surface with completed M13/M14 closeout evidence classification behavior integrated.

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

## M13 Closeout Evidence Recognition State

- `plan-batch-closeout` now recognizes deterministic human-gated closeout evidence from issue comments in addition to issue bodies.
- Recognized categories include merged PR references, validation command pass signals, and documentation reconciliation evidence.
- Contract: `docs/architecture/CLOSEOUT_EVIDENCE_RECOGNITION_CONTRACT.md`.

## M14 Classification Cleanup State

- Historical parent-body issue references used as prior-milestone context are classified as historical/non-active.
- Qualifying merged PR references are classified as closeout evidence, not active children.
- Active child discovery remains constrained to real child issue references tied to the current parent scope.

## Automation Boundary

- Human-triggered only.
- Read-only/output-only defaults.
- Explicit local planning-state writes only when write flags are supplied.
- No autonomous setup/mutation, merge, closeout, labels, milestones, comments, releases, or tags.
- Generated mutation scripts are copy/paste output only and require human review/execution.
- Verification/repair guidance is text-only and human-gated.
- AresForge remains local-first and read-only by default.
