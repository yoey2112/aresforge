# AresForge Agent Context

## Purpose

Provide minimum operating context for safe M15 self-managed milestone planning and documentation reconciliation.

## Current Operating Model

- Documentation remains source of truth.
- `plan-self-managed-milestone` defaults to read-only planning output.
- `plan-self-managed-milestone --mode local-write` is local DB write only.
- `generate-self-managed-issue-script` is text/script output only.
- Human authority remains final for all GitHub mutation.
- No autonomous queue workers or background execution.

## Canonical Documents

- `docs/architecture/SELF_MANAGED_MILESTONE_PLANNING_CONTRACT.md`
- `docs/architecture/RUNNABLE_SKELETON.md`
- `docs/architecture/REPOSITORY_GOVERNANCE_CONTRACT.md`
- `docs/architecture/CLOSEOUT_EVIDENCE_RECOGNITION_CONTRACT.md`
- `docs/operator/LOCAL_OPERATOR_USAGE.md`
- `docs/context/BUILD_STATE.md`
- `docs/roadmap/ROADMAP.md`

## Current Commands

- `python -m aresforge plan-self-managed-milestone`
- `python -m aresforge plan-self-managed-milestone --mode local-write`
- `python -m aresforge generate-self-managed-issue-script`
- `python -m aresforge generate-self-managed-issue-script --run-id <id>`
- `python -m aresforge generate-self-managed-issue-script --target-issue <number>`
- `python -m aresforge inspect-repo-governance`

## M15 Capability Snapshot

- Self-managed milestone planning contract implemented and active.
- Read-only planning mode implemented.
- Local-write planning mode implemented.
- DB-backed `autonomous_runs`/`run_steps` persistence implemented.
- Queue advancement/current-ready target selection implemented.
- Self-managed issue script generation command implemented.
- Derived read-only script generation implemented.
- DB-backed script generation by `--run-id` implemented.

## Prohibited Behaviors

- autonomous GitHub mutation
- automatic issue closure
- automatic PR merge
- automatic branch creation
- autonomous comments/labels/milestones/releases/tags
- background jobs, polling loops, schedulers, or hidden workers

## Validation Snapshot For Final M15 State

- `git diff --check`
- `python -m pytest`
- `python -m aresforge inspect-repo-governance`
- `python -m aresforge plan-self-managed-milestone`
- `python -m aresforge plan-self-managed-milestone --mode local-write`
- `python -m aresforge generate-self-managed-issue-script`

## Known Follow-Up Candidates

1. Milestone naming/mapping cleanup remains non-blocking.
2. Next autonomy milestone should target local autonomous execution path preparation.
3. Future generalized sequencing beyond M15's bounded sequence.
4. Future source-of-truth reconciliation automation.
5. Future controlled PR-write mode, out of M15 scope.

## Parent Closeout Readiness

- Parent `#249` can be prepared for human-gated closeout after issue `#253` merges.
