# AresForge Roadmap

## Current Milestones

### M0-M15

Status: Completed.

### M16 - Controlled Autonomous GitHub Execution Loop

Status: Completed.

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

Final closeout record:

- Parent issue #258 is closed.
- Child issues #259 through #265 are closed.
- PR #266 is merged implementation evidence.
- PR #267 was duplicate/no-op and is closed.
- Child issue closure was executed per issue with explicit evidence mapping comments.

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

### M17 - Self-managed milestone orchestration after controlled autonomous execution

Status: In progress.

Parent issue:

- #269 M17 self-managed milestone orchestration after controlled autonomous execution

Current implementation scope:

- #270 define milestone execution plan contract
- #271 add read-only milestone state inspector
- #272 add guarded per-issue execution queue planner
- #273 add evidence completeness checker for issue closeout readiness
- #274 add duplicate/no-op PR prevention and reuse planner hardening

Current M17 outcomes:

- Contract authority at `docs/architecture/MILESTONE_EXECUTION_PLAN_CONTRACT.md`.
- `inspect-milestone-state` command:
  - `python -m aresforge inspect-milestone-state --parent-issue <parent>`
- `plan-milestone-execution-queue` command:
  - `python -m aresforge plan-milestone-execution-queue --parent-issue <parent>`
- `check-issue-evidence-readiness` command:
  - `python -m aresforge check-issue-evidence-readiness --issue <issue>`
- `check-milestone-evidence-readiness` command:
  - `python -m aresforge check-milestone-evidence-readiness --parent-issue <parent>`
- Read-only milestone parent/child inspection with:
  - parent summary
  - child discovery from detectable references
  - child state summaries
  - merged PR evidence hints
  - missing lineage hints
  - milestone naming/assignment warnings
  - explicit read-only boundary confirmations
- Planning-only milestone execution queue guidance with:
  - deterministic per-issue order
  - final reconciliation issue last when detected
  - blockers and missing lineage/evidence signals
  - explicit non-execution safety gates (`execution_enabled: false`)
- Read-only evidence readiness and duplicate/no-op reuse planning with:
  - issue-level readiness classification (`ready`, `not_ready`, `ambiguous`, `blocked`, `already_closed`)
  - `new_pr_needed` reuse/prevention guidance
  - explicit mutation disabled safety fields
  - no issue closure, PR creation, or issue comments

M17 #270/#271/#272/#273/#274 validation bundle:

- `git diff --check`
- `python -m pytest`
- `python -m aresforge inspect-repo-governance`
- `python -m aresforge inspect-milestone-state --parent-issue 269`
- `python -m aresforge plan-milestone-execution-queue --parent-issue 269`
- `python -m aresforge check-issue-evidence-readiness --issue 270`
- `python -m aresforge check-milestone-evidence-readiness --parent-issue 269`
- Governance and closeout remain explicitly human-triggered and auditable.
