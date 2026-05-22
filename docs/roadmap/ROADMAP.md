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

### M18 - Milestone execution automation ergonomics and operator-driven closeout workflows

Status: Final reconciliation in progress (`#301` only).

Parent issue:

- #294 M18 milestone execution automation ergonomics and operator-driven closeout workflows (open)

Implementation children:

- #295 CLOSED via PR #302
- #296 CLOSED via PR #303
- #297 CLOSED via PR #304
- #298 CLOSED via PR #305
- #299 CLOSED via PR #306
- #300 CLOSED via PR #307
- #301 OPEN (final source-of-truth reconciliation, must be processed last)

Delivered M18 command outcomes:

- `inspect-milestone-dashboard`
- `generate-child-closeout-script`
- `generate-evidence-comment-template`
- `inspect-parent-closeout-readiness`
- schema-driven evidence mapping support with structured marker parsing and legacy compatibility

M18 safety posture:

- read-only inspection/planning commands do not mutate GitHub state
- template/script generators are output-only and require explicit human execution for mutation
- child issues are executed one-by-one with issue-specific evidence mapping
- no bulk issue closure
- parent remains open until final reconciliation is merged/accounted and reviewed

M18 validation bundle:

- `git diff --check`
- `python -m pytest`
- `python -m aresforge inspect-repo-governance`
- `python -m aresforge inspect-milestone-state --parent-issue 294`
- `python -m aresforge inspect-milestone-dashboard --parent-issue 294`
- `python -m aresforge plan-milestone-execution-queue --parent-issue 294`
- `python -m aresforge check-issue-evidence-readiness --issue <issue>`
- `python -m aresforge check-milestone-evidence-readiness --parent-issue 294`
- `python -m aresforge plan-milestone-final-reconciliation --parent-issue 294`
- `python -m aresforge inspect-parent-closeout-readiness --parent-issue 294`
