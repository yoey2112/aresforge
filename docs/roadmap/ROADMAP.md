# AresForge Roadmap

## Current Milestones

### M0-M15

Status: Completed.

### M16 - Controlled Autonomous GitHub Execution Loop

Status: In progress (aggressive implementation path).

Parent issue:

- #258 M16 controlled autonomous GitHub execution loop

Child issues:

- #259 define controlled autonomous GitHub execution contract
- #260 add autonomous run lifecycle and safety gates
- #261 add branch-write execution mode
- #262 add push and PR creation mode
- #263 add issue closeout eligibility and controlled closure mode
- #264 add autonomous run inspection and evidence reporting
- #265 reconcile source-of-truth docs for controlled autonomous GitHub execution

Delivered M16 outcomes (current branch):

- Contract authority at `docs/architecture/CONTROLLED_AUTONOMOUS_GITHUB_EXECUTION_CONTRACT.md`.
- `run-autonomous-cycle` command with explicit modes:
  - `dry-run`
  - `local-write`
  - `branch-write`
  - `push-pr`
  - `closeout-eligible`
- `inspect-autonomous-run` command for run/step inspection.
- DB-backed run lifecycle and step tracking using `autonomous_runs` and `run_steps`.
- Fail-closed safety gates for higher-permission mode prerequisites.
- Evidence artifact generation for successful and failed runs.

M16 safety boundaries:

- No mutation in `dry-run`.
- No GitHub mutation in `local-write` or `branch-write`.
- No push/PR creation unless mode is explicitly `push-pr` or `closeout-eligible`.
- No issue closure unless mode is explicitly `closeout-eligible`.
- No automatic PR merge.
- No background jobs, polling loops, schedulers, or unattended execution.

M16 validation command bundle:

- `git diff --check`
- `python -m pytest`
- `python -m aresforge inspect-repo-governance`
- `python -m aresforge run-autonomous-cycle --mode dry-run --parent-issue 258 --target-issue 259 --validation-command "python -m aresforge inspect-repo-governance"`
- `python -m aresforge run-autonomous-cycle --mode local-write --parent-issue 258 --target-issue 260 --validation-command "python -m aresforge inspect-repo-governance"`
- `python -m aresforge run-autonomous-cycle --mode branch-write --parent-issue 258 --target-issue 261 --validation-command "python -m aresforge inspect-repo-governance"` (fail-closed validation)
- `python -m aresforge run-autonomous-cycle --mode push-pr --parent-issue 258 --target-issue 262 --validation-command "python -m aresforge inspect-repo-governance"` (fail-closed validation)
- `python -m aresforge run-autonomous-cycle --mode closeout-eligible --parent-issue 258 --target-issue 263 --validation-command "python -m aresforge inspect-repo-governance"` (fail-closed validation)
- `python -m aresforge inspect-autonomous-run --run-id <id>`

## Standing Boundaries

- No autonomous mutation without explicit mode selection.
- No autonomous queue workers.
- No automatic PR merge.
- No unattended background execution.
- Governance and closeout remain explicitly human-triggered and auditable.
