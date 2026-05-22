# AresForge Agent Context

## Purpose

Provide the minimum current operating context for safe M13 closeout evidence recognition and operator usage.

## M13 Operating Model

- Documentation remains source of truth.
- Local planning memory is optional, explicit-write, and local-only.
- Default command behavior remains read-only/output-only.
- Human authority remains final for all GitHub mutation.
- Sprint issue creation planning is deterministic, read-only by default, and emits human-gated mutation output only.
- Implementation progress remains gated by human-run post-creation verification pass/fail output.
- Closeout planning recognizes deterministic human-gated closeout evidence in issue comments without mutation.

## Canonical M13 Documents

- `docs/architecture/SPRINT_ISSUE_CREATION_PLANNING_CONTRACT.md`
- `docs/architecture/CLOSEOUT_EVIDENCE_RECOGNITION_CONTRACT.md`
- `docs/architecture/RUNNABLE_SKELETON.md`
- `docs/operator/LOCAL_OPERATOR_USAGE.md`
- `docs/context/BUILD_STATE.md`
- `docs/roadmap/ROADMAP.md`

## M13 Commands

- `python -m aresforge generate-sprint-issue-script --definition <file> [--write-planning-state]`
- `python -m aresforge plan-batch-closeout --parent-issue <number> [--write-planning-snapshot]`
- `python -m aresforge inspect-planning-state`
- `python -m aresforge compare-planning-state`
- `python -m aresforge inspect-closeout-planning-drift --parent-issue <number>`
- `python -m aresforge plan-sprint-issues --definition <path>`

## M13 Delivery Status

- Current scope: closeout evidence recognition contract, parser updates, regression fixtures, and source-of-truth reconciliation.

## Prohibited Behaviors

- autonomous queue transitions
- autonomous setup/mutation behavior
- autonomous issue creation from planner output
- autonomous merge/closeout/labeling/milestone assignment
- autonomous comments/releases/tags
- automatic issue closeout
- automatic PR merge

## Remaining Closeout Expectation

- Verify parent #222 closeout planning reports recognized manual evidence for merged PR, validation, and documentation reconciliation categories.
