# Sequential Milestone Execution Contract

## Purpose

Define the M19 contract for safe sequential execution of milestone child issues, one child at a time, with explicit operator approval and read-only-first planning surfaces.

## Scope

- In scope:
  - one-child-at-a-time milestone execution lifecycle
  - run-state terminology and transition boundaries
  - per-child validation and evidence expectations
  - recovery checkpoints and handoff expectations
- Out of scope:
  - autonomous broad mutation
  - bulk issue closure
  - automatic parent closure

## Core Sequential Loop

For each child issue, execute this loop in order:

1. Start from clean synced `main`.
2. Create a dedicated child branch.
3. Implement only that child scope.
4. Validate on branch.
5. Create and merge a dedicated PR.
6. Sync and validate `main`.
7. Post issue-specific evidence comment.
8. Close only the target child issue.
9. Inspect milestone dashboard/readiness before next child.

Final reconciliation must run last and parent closure must remain gated.

## Child Lifecycle States

Each child issue execution should map to explicit lifecycle states:

- `queued`: child is identified and not started.
- `in_progress`: implementation branch work has started.
- `branch_validated`: branch-level validation passed.
- `pr_open`: PR exists and is under review.
- `merged`: PR merged to `main`.
- `main_validated`: post-merge `main` validation passed.
- `evidence_posted`: issue-specific evidence comment posted.
- `closed`: targeted child closeout complete.
- `blocked`: execution paused due to failed gate.

Transitions must be forward-only unless a recovery plan explicitly reclassifies state after interruption.

## Required Per-Child Gates

Before advancing a child to `closed`, all gates must be satisfied:

- Clean synced `main` confirmed before start.
- Dedicated child branch and dedicated PR confirmed.
- Required validation commands pass.
- Issue-specific evidence comment is posted.
- Targeted closeout is performed only for the child issue.
- Milestone dashboard/readiness inspection is run after merge and closeout.

## Safety Boundaries

- No autonomous broad mutation.
- No bulk issue close commands.
- No parent closeout before children are closed/accounted for and final reconciliation is complete.
- Each child must have its own PR, validation, evidence, and targeted closeout.
- Planning and inspection surfaces remain read-only by default.
- Recovery planning may recommend actions but must not force mutation.
- Prior milestone mutation is out of scope unless explicitly required for M19 documentation references.

## Recovery Boundaries

When any gate fails:

- Stop advancing to the next child.
- Keep target child open until gates are satisfied.
- Preserve branch/PR/evidence context for operator review.
- Produce a recovery report with failed step, current state, last passing validation, and recommended next action.

## Parent Closure Gate

Parent closure is forbidden until all conditions are true:

- All M19 child issues are closed or explicitly accounted for.
- Final reconciliation child is closed.
- Milestone dashboard/readiness reports parent readiness.
- Evidence readiness confirms closeout posture.
- Final `main` validation has passed.

## Validation Expectations

For M19 sequential execution work, run:

- `git diff --check`
- `python -m pytest`
- `python -m aresforge inspect-repo-governance`
- `python -m aresforge inspect-milestone-dashboard --parent-issue <parent>`
- `python -m aresforge inspect-milestone-state --parent-issue <parent>`
- `python -m aresforge check-milestone-evidence-readiness --parent-issue <parent>`
