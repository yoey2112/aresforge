# AresForge Agent Context

## Purpose

This file gives agents the minimum current operating context needed to work safely in AresForge.

## Operating Model

Agents must treat repository documentation as the source of truth for project meaning, governance, milestone state, lifecycle rules, and autonomy boundaries.

During M5 closeout, implementation remains human-triggered and human-reviewed. Agents may help with documentation, code, migrations, local operator tooling, and evidence preparation, but they must not imply autonomous control.

## Required Source-Of-Truth Behavior

- Review `docs/context/BUILD_STATE.md`, `docs/context/AGENT_CONTEXT.md`, and `docs/roadmap/ROADMAP.md` for project-state-changing work.
- Update those docs before PR merge and issue closeout when project state changes.
- If one source-of-truth doc is unchanged, explain why in PR evidence.
- Treat Issue #75 as the last routine reconciliation issue.
- Do not create routine reconciliation issues for normal sprint closeout.

## Current M5 Rules

- Documentation-before-closeout is mandatory.
- Human-reviewed controls remain mandatory.
- Evidence artifacts remain review aids, not authority sources.
- GitHub mutation remains human-triggered and gated.
- No autonomous setup/mutation command is implemented.
- Issue #39 remains retired historical validation evidence only.

## M5 Workstream Status

- Issue #158 / PR #161: complete.
- Issue #156 / PR #162: complete.
- Issue #157: complete in this consolidated branch (managed onboarding contract).
- Issue #159: complete in this consolidated branch (gated setup contract design-only).
- Issue #160: complete in this consolidated branch (source-of-truth reconciliation).
- Issue #155: parent closeout completed by this consolidated branch.

## Managed Repository Onboarding Contract Summary

Managed repository classes:

- Platform self-managed repo: AresForge itself, always first/default.
- Fixture/demo repo: inspection-only validation record; non-production mutation scope.
- Real managed repo: explicitly onboarded target with full metadata, readiness evidence, and human-triggered setup intent.

Required real-managed onboarding metadata:

- repository slug, project key, repo role, governance profile
- default branch and local-path posture
- documentation and artifact roots
- allowed automation capabilities

Required readiness checks are read-only:

- inspect governance
- inspect bootstrap contract
- inspect managed repo registry
- run managed repo readiness report
- generate bootstrap plan

## Setup Contract Posture Summary

The setup command contract in M5 is design-only and not implemented as a new mutation command.

Required future command properties:

- dry-run behavior
- explicit confirmation gates
- audit evidence outputs
- strict mutation scope boundaries
- rollback/recovery notes
- human-triggered execution model
- no autonomous mutation
- validation that detects unsafe behavior

## Canonical Documents Agents Must Consult

- `docs/architecture/RUNNABLE_SKELETON.md`
- `docs/architecture/REPOSITORY_GOVERNANCE_CONTRACT.md`
- `docs/architecture/MANAGED_REPOSITORY_BOOTSTRAP_CONTRACT.md`
- `docs/architecture/MANAGED_REPOSITORY_REGISTRY.md`
- `docs/operator/LOCAL_OPERATOR_USAGE.md`
- `docs/context/BUILD_STATE.md`
- `docs/context/AGENT_CONTEXT.md`
- `docs/roadmap/ROADMAP.md`

## Current Allowed Local-Operator Behaviors

- read-only inspection and validation commands
- human-triggered dry-run or execute use of existing `qa-closeout-pr`
- read-only managed-repo governance stack commands
- read-only bootstrap planning output, including human-reviewable command recommendations

## Current Prohibited And Autonomy Boundaries

- autonomous queue transitions or routing mutation
- autonomous setup/mutation command execution
- autonomous merge, closeout, or approval
- hidden background mutation workflows
- mutation of Issue #39 context

## Human Owner Role

The human owner remains the final authority for governance-sensitive decisions, mutation approval, merge/closeout approval, and autonomy-boundary expansion.
