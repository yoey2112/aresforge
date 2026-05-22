# AresForge Agent Context

## Purpose

Provide the minimum current operating context for safe M12 source-of-truth reconciliation and operator usage.

## M12 Operating Model

- Documentation remains source of truth.
- Local planning memory is optional, explicit-write, and local-only.
- Default command behavior remains read-only/output-only.
- Human authority remains final for all GitHub mutation.
- Sprint issue creation planning is deterministic, read-only by default, and emits human-gated mutation output only.
- Implementation progress remains gated by human-run post-creation verification pass/fail output.

## Canonical M12 Documents

- `docs/architecture/SPRINT_ISSUE_CREATION_PLANNING_CONTRACT.md`
- `docs/architecture/RUNNABLE_SKELETON.md`
- `docs/operator/LOCAL_OPERATOR_USAGE.md`
- `docs/context/BUILD_STATE.md`
- `docs/roadmap/ROADMAP.md`

## M12 Commands

- `python -m aresforge generate-sprint-issue-script --definition <file> [--write-planning-state]`
- `python -m aresforge plan-batch-closeout --parent-issue <number> [--write-planning-snapshot]`
- `python -m aresforge inspect-planning-state`
- `python -m aresforge compare-planning-state`
- `python -m aresforge inspect-closeout-planning-drift --parent-issue <number>`
- `python -m aresforge plan-sprint-issues --definition <path>`

## M12 Delivery Status

- M12 core planner implementation delivered in merged PR #230: #223, #224, #225, #226, #229.
- M12 operator workflow documentation delivered in merged PR #231: #227.
- Current scope is source-of-truth reconciliation: #228.

## Prohibited Behaviors

- autonomous queue transitions
- autonomous setup/mutation behavior
- autonomous issue creation from planner output
- autonomous merge/closeout/labeling/milestone assignment
- autonomous comments/releases/tags
- automatic issue closeout
- automatic PR merge

## Remaining Closeout Expectation

- After #228 merges, run QA/closeout planning for M12 parent #222 and child issues #223, #224, #225, #226, #229, #227, #228.
