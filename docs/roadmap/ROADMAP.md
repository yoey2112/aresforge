# AresForge Roadmap

## Current Milestones

### M0-M14

Status: Completed.

### M15 - Self-Managed Milestone Planning Foundations

Status: Implementation complete; source-of-truth reconciliation in progress via `#253`.

Parent issue:

- #249 M15 self-managed milestone planning

Child issues:

- #250 define self-managed milestone planning contract
- #251 add DB-backed self-managed milestone planner and run queue initializer
- #252 add self-managed issue script generator
- #253 reconcile source-of-truth docs for self-managed milestone planning

Implementation status:

- #250, #251, #252 implemented.
- #253 is the active documentation reconciliation scope.

Delivered M15 outcomes:

- Contract authority at `docs/architecture/SELF_MANAGED_MILESTONE_PLANNING_CONTRACT.md`.
- `plan-self-managed-milestone` command with read-only default.
- `plan-self-managed-milestone --mode local-write` with DB persistence.
- DB-backed persistence tables: `autonomous_runs` and `run_steps`.
- Queue advancement/current-ready target derivation implemented.
- `generate-self-managed-issue-script` command implemented.
- Derived read-only script generation implemented.
- DB-backed `--run-id` script generation implemented.

M15 safety boundaries:

- No autonomous GitHub mutation.
- No automatic issue closure.
- No automatic PR merge.
- No automatic branch creation.
- No background jobs, polling loops, or schedulers.
- GitHub mutation remains human-gated via reviewed manual workflows.

M15 validation command bundle:

- `git diff --check`
- `python -m pytest`
- `python -m aresforge inspect-repo-governance`
- `python -m aresforge plan-self-managed-milestone`
- `python -m aresforge plan-self-managed-milestone --mode local-write`
- `python -m aresforge generate-self-managed-issue-script`

Known follow-up candidates:

1. Milestone naming/mapping cleanup remains non-blocking (`milestone_naming_status.naming_ok: false`).
2. Next autonomy milestone should move toward local autonomous execution modes (likely branch-write or run-cycle preparation).
3. Generalize sequencing beyond bounded M15 issue ordering.
4. Add source-of-truth reconciliation automation.
5. Add controlled PR-write mode in a future milestone (not M15).

Closeout readiness note:

- Parent #249 can be prepared for human-gated closeout after #253 merges.

## Standing Boundaries

- No autonomous setup/mutation behavior.
- No autonomous queue mutation workers.
- No autonomous issue creation.
- No autonomous merge/issue closure.
- No autonomous labels, milestones, comments, releases, or tags.
- No automatic PR merge.
