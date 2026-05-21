# AresForge Agent Context

## Purpose

Provide the minimum current operating context for safe M6 execution.

## M6 Operating Model

- Documentation remains source of truth.
- Queue planning and batch readiness are read-only operator helpers.
- Human authority remains final for merge/closeout and all GitHub mutation.

## Required Source-Of-Truth Behavior

- Review and reconcile `BUILD_STATE`, `AGENT_CONTEXT`, and `ROADMAP` for project-state-changing work.
- Update architecture/operator docs when command behavior changes.
- Keep Issue #39 excluded from active lifecycle mutation.

## Canonical M6 Documents

- `docs/architecture/AGENT_QUEUE_ORCHESTRATION_CONTRACT.md`
- `docs/architecture/CODEX_BATCH_EXECUTION_WORKFLOW.md`
- `docs/architecture/REGISTRY_AND_QUEUE_ARCHITECTURE.md`
- `docs/architecture/QUEUE_REGISTRY_SCHEMA.md`
- `docs/operator/LOCAL_OPERATOR_USAGE.md`

## M6 Commands

- `python -m aresforge plan-agent-queue`
- `python -m aresforge report-batch-readiness`

## Closeout Reliability Posture

- `qa-closeout-pr` remains dry-run default.
- Execute mode stays explicitly gated.
- Close issue failures now include clearer diagnostics and state re-check behavior.

## Prohibited Behaviors

- autonomous queue transitions
- autonomous setup/mutation behavior
- autonomous merge/closeout/labeling
- Issue #39 mutation
