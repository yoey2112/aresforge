# AresForge Agent Context

## Purpose

Provide the minimum current operating context for safe M7 execution.

## M7 Operating Model

- Documentation remains source of truth.
- Governance-aware intake, queue planning, and batch closeout planning are read-only operator helpers.
- Human authority remains final for merge/closeout and all GitHub mutation.

## Required Source-Of-Truth Behavior

- Review and reconcile `BUILD_STATE`, `AGENT_CONTEXT`, and `ROADMAP` for project-state-changing work.
- Update architecture/operator docs when command behavior changes.
- Keep Issue #39 excluded from active lifecycle mutation.
- Keep Issue #179 recorded as already complete.

## Canonical M7 Documents

- `docs/architecture/AGENT_QUEUE_ORCHESTRATION_CONTRACT.md`
- `docs/architecture/RUNNABLE_SKELETON.md`
- `docs/architecture/REPOSITORY_GOVERNANCE_CONTRACT.md`
- `docs/operator/LOCAL_OPERATOR_USAGE.md`

## M7 Commands

- `python -m aresforge plan-agent-queue`
- `python -m aresforge report-batch-readiness`
- `python -m aresforge plan-batch-closeout --parent-issue <number>`

## Closeout Posture

- Batch closeout planning remains read-only and advisory.
- `qa-closeout-pr` remains dry-run default and execute-gated.
- Final issue closeout remains human-gated after PR merge and validation.

## Prohibited Behaviors

- autonomous queue transitions
- autonomous setup/mutation behavior
- autonomous merge/closeout/labeling
- Issue #39 mutation
