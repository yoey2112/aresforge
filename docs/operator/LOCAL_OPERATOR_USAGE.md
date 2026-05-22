# Local Operator Usage

## Core Validation Bundle (Final M15 State)

- `git diff --check`
- `python -m pytest`
- `python -m aresforge inspect-repo-governance`
- `python -m aresforge plan-self-managed-milestone`
- `python -m aresforge plan-self-managed-milestone --mode local-write`
- `python -m aresforge generate-self-managed-issue-script`
- `git status --short`
- `git diff --name-only`

## Self-Managed Milestone Planner (M15)

Commands:

- `python -m aresforge plan-self-managed-milestone`
- `python -m aresforge plan-self-managed-milestone --mode local-write`

Mode behavior:

- `read-only`: inspects source-of-truth docs plus read-only governance/readiness signals and emits deterministic planning output and evidence artifacts.
- `local-write`: includes all read-only behavior plus local DB writes to `autonomous_runs` and `run_steps`.
- `branch-write`, `pr-write`, `closeout-write`, `full-auto`: intentionally unimplemented and fail safe.

Queue advancement/current-ready targeting:

- Active target issue is derived from current ready-issue state.
- Previously targeted closed issues are not retained when a newer ready issue exists.
- If no ready issue exists, output reports no active target and recommends human-gated readiness advancement.

## Self-Managed Issue Script Generation (M15)

Commands:

- `python -m aresforge generate-self-managed-issue-script`
- `python -m aresforge generate-self-managed-issue-script --run-id <id>`
- `python -m aresforge generate-self-managed-issue-script --target-issue <number>`

Behavior:

- Generates deterministic text-only copy/paste PowerShell guidance.
- Uses DB-backed run queue state when run records are available (including `--run-id`).
- Falls back to derived read-only planning state when no run record is available.
- Keeps mutation human-gated; Python command does not execute GitHub mutation.

## Human-Gated Mutation Boundaries

Allowed:

- human-triggered local command execution
- explicit local DB writes in `local-write` mode
- manual, reviewed execution of generated scripts
- human-reviewed branch and PR workflows

Not authorized:

- autonomous GitHub mutation
- automatic issue closure
- automatic PR merge
- automatic branch creation
- background jobs, polling loops, or schedulers

## Governance Note

- `inspect-repo-governance` may continue to report project-specific milestone naming/mapping warnings (`milestone_naming_status.naming_ok: false`); this remains non-blocking for current M15 workflow.

## M15 Closeout Readiness Note

- Parent issue `#249` can be prepared for human-gated closeout after issue `#253` merges.
