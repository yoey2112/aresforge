# AresForge Agent Context

## Purpose

Provide the minimum current operating context for safe M11 documentation reconciliation and closeout drift operation.

## M11 Operating Model

- Documentation remains source of truth.
- Local planning memory is optional, explicit-write, and local-only.
- Default command behavior remains read-only/output-only.
- Human authority remains final for all GitHub mutation.
- Closeout planning drift inspection compares planned children vs live discovery and blocks readiness when drift/unresolved state exists.

## Canonical M11 Documents

- `docs/architecture/PERSISTED_LOCAL_PLANNING_STATE.md`
- `docs/architecture/CLOSEOUT_CHILD_LINK_DISCOVERY_CONTRACT.md`
- `docs/architecture/PLANNING_STATE_CLOSEOUT_COMPARISON_CONTRACT.md`
- `docs/architecture/RUNNABLE_SKELETON.md`
- `docs/operator/LOCAL_OPERATOR_USAGE.md`

## M11 Commands

- `python -m aresforge generate-sprint-issue-script --definition <file> [--write-planning-state]`
- `python -m aresforge plan-batch-closeout --parent-issue <number> [--write-planning-snapshot]`
- `python -m aresforge inspect-planning-state`
- `python -m aresforge compare-planning-state`
- `python -m aresforge inspect-closeout-planning-drift --parent-issue <number>`

## M11 Delivery Status

- Implemented in merged integration PR: #211, #212, #213, #214, #217
- Documentation/reconciliation scope now active: #215, #216

## Prohibited Behaviors

- autonomous queue transitions
- autonomous setup/mutation behavior
- autonomous merge/closeout/labeling/milestone assignment
- autonomous comments/releases/tags
- the protected historical reference mutation

## Recommended Follow-Up After M11 Closeout

- Remove recurring protected historical issue references from active governance/operator paths while keeping required historical evidence behavior.

