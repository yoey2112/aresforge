# AresForge Agent Context

## Purpose

Provide the minimum current operating context for safe M9 execution.

## M9 Operating Model

- Documentation remains source of truth.
- Local planning memory is optional, explicit-write, and local-only.
- Default command behavior remains read-only/output-only.
- Human authority remains final for all GitHub mutation.

## Canonical M9 Documents

- `docs/architecture/PERSISTED_LOCAL_PLANNING_STATE.md`
- `docs/architecture/RUNNABLE_SKELETON.md`
- `docs/operator/LOCAL_OPERATOR_USAGE.md`
- `docs/architecture/STRUCTURED_SPRINT_ISSUE_DEFINITION_CONTRACT.md`

## M9 Commands

- `python -m aresforge generate-sprint-issue-script --definition <file> [--write-planning-state]`
- `python -m aresforge plan-batch-closeout --parent-issue <number> [--write-planning-snapshot]`
- `python -m aresforge inspect-planning-state`
- `python -m aresforge compare-planning-state`

## Prohibited Behaviors

- autonomous queue transitions
- autonomous setup/mutation behavior
- autonomous merge/closeout/labeling/milestone assignment
- autonomous comments/releases/tags
- Issue #39 mutation
