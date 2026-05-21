# AresForge Agent Context

## Purpose

Provide the minimum current operating context for safe M8 execution.

## M8 Operating Model

- Documentation remains source of truth.
- Governance-aware intake, queue planning, readiness reporting, and batch closeout planning remain read-only operator helpers.
- Structured sprint issue creation support is output-only through generated local scripts.
- Human authority remains final for all GitHub mutation, including issue creation, merge, and closeout.

## Required Source-Of-Truth Behavior

- Review and reconcile `BUILD_STATE`, `AGENT_CONTEXT`, and `ROADMAP` for project-state-changing work.
- Update architecture/operator docs when command behavior changes.
- Keep Issue #39 excluded from active lifecycle mutation and active implementation linkage.
- Keep Issue #179 recorded as already complete.

## Canonical M8 Documents

- `docs/architecture/AGENT_QUEUE_ORCHESTRATION_CONTRACT.md`
- `docs/architecture/RUNNABLE_SKELETON.md`
- `docs/architecture/REPOSITORY_GOVERNANCE_CONTRACT.md`
- `docs/architecture/STRUCTURED_SPRINT_ISSUE_DEFINITION_CONTRACT.md`
- `docs/operator/LOCAL_OPERATOR_USAGE.md`

## M8 Commands

- `python -m aresforge plan-agent-queue`
- `python -m aresforge report-batch-readiness`
- `python -m aresforge plan-batch-closeout --parent-issue <number>`
- `python -m aresforge generate-sprint-issue-script --definition <file>`

## Closeout Posture

- Batch closeout planning remains read-only and advisory.
- `plan-batch-closeout` now reports structured evidence details for merged PR linkage and closeout rationale.
- `qa-closeout-pr` remains dry-run default and execute-gated.
- Final issue closeout remains human-gated after PR merge and validation.

## Prohibited Behaviors

- autonomous queue transitions
- autonomous setup/mutation behavior
- autonomous merge/closeout/labeling/milestone assignment
- autonomous comments/releases/tags
- Issue #39 mutation
