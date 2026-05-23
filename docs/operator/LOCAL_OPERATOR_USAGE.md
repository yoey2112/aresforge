# Local Operator Usage

## M18 Core Validation Bundle

- `git diff --check`
- `python -m pytest`
- `python -m aresforge inspect-repo-governance`
- `python -m aresforge inspect-milestone-state --parent-issue <parent>`
- `python -m aresforge inspect-milestone-dashboard --parent-issue <parent>`
- `python -m aresforge plan-milestone-execution-queue --parent-issue <parent>`
- `python -m aresforge check-issue-evidence-readiness --issue <issue>`
- `python -m aresforge check-milestone-evidence-readiness --parent-issue <parent>`
- `python -m aresforge plan-milestone-final-reconciliation --parent-issue <parent>`
- `python -m aresforge inspect-parent-closeout-readiness --parent-issue <parent>`
- `python -m aresforge inspect-sequential-run-state --parent-issue <parent>`

## End-to-End Child Execution Pattern (M18)

1. Sync clean `main`.
2. Implement one child issue only on one issue-specific branch.
3. Run the validation bundle.
4. Open one PR for that child issue.
5. Merge PR.
6. Sync clean `main` again.
7. Re-run validation bundle.
8. Generate and post issue-specific evidence mapping comment.
9. Close only the target child issue.
10. Re-run milestone dashboard and queue checks.
11. Move to next recommended child issue.

Rules:

- never bulk-close issues
- never close parent before child sequence is complete
- keep final reconciliation issue last
- mutation remains human-triggered and review-gated

## M20 Mutation Intent Planning (Child #328)

Command:

- `python -m aresforge plan-github-mutation --mutation-type <issue_comment|issue_close|pr_body_update|audit_log_write> --planned-action "<action>" [--target-issue <issue>] [--target-pr <pr>] [--approval-marker <marker>]`

Behavior:

- planning-only and dry-run by default
- validates one explicit mutation type and one explicit target shape
- blocks unsafe target/type combinations
- emits required approvals, safety checks, blocked reasons, dry-run summary, and audit metadata preview
- never closes issues
- never creates PRs
- never comments on issues
- never mutates GitHub state

## M20 Targeted Issue Comment Execution (Child #329)

Commands:

- `python -m aresforge execute-github-issue-comment --issue <issue> --comment-body "<body>"`
- `python -m aresforge execute-github-issue-comment --issue <issue> --comment-file <path>`
- `python -m aresforge execute-github-issue-comment --issue <issue> --comment-body "<body>" --execute --approval-marker <marker>`

Behavior:

- dry-run by default
- requires explicit issue target
- requires non-empty comment body
- execution requires explicit `--execute` plus `--approval-marker`
- blocks parent target when `--parent-issue` matches `--issue` unless `--allow-parent-target` is supplied
- emits audit-ready result payload
- does not close issues
- no bulk comment mutation path

## M20 Targeted Issue Close Execution (Child #330)

Commands:

- `python -m aresforge execute-github-issue-close --issue-target <issue> --parent-issue <parent>`
- `python -m aresforge execute-github-issue-close --issue-target <issue> --parent-issue <parent> --execute --approval-marker <marker>`

Behavior:

- dry-run by default
- accepts only one plain-digit issue target (`--issue-target 330`)
- rejects lists/ranges/composite targets (`330,331`, `330-334`)
- child close requires child issue evidence readiness
- parent close requires parent closeout readiness true
- execution requires explicit `--execute` and `--approval-marker`
- emits audit-ready result payload
- no bulk closure path

## M20 PR Body Update Helper (Child #331)

Commands:

- `python -m aresforge prepare-pr-body-update --pr-number <pr> --target-issue <issue> --scope-summary "<summary>"`
- `python -m aresforge prepare-pr-body-update --pr-number <pr> --target-issue <issue> --scope-summary "<summary>" --file-changed <path> --validation-result "<result>" --safety-note "<note>"`
- `python -m aresforge prepare-pr-body-update --pr-number <pr> --target-issue <issue> --scope-summary "<summary>" --execute --approval-marker <marker>`

Behavior:

- dry-run by default
- renders structured PR body text with scope, files changed, validation results, and safety notes
- supports optional targeted execution for one PR body update only
- execution requires explicit `--execute` and `--approval-marker`
- generated output avoids nested markdown fences for PowerShell examples
- no bulk PR update path

## M20 Mutation Audit Log And Recovery Guidance (Child #332)

Commands:

- `python -m aresforge inspect-github-mutation-audit-log`
- `python -m aresforge inspect-github-mutation-audit-log --limit 50`

Behavior:

- mutation planning/execution commands append local audit records
- records include mutation intent, dry-run output, approval marker, execution result, timestamp, target, command concept, and recovery notes
- audit artifacts are local-only by default
- inspection command is read-only and does not mutate GitHub
- generated local audit artifacts must not be committed

## M20 End-To-End Operator-Approved Mutation Workflow (Child #333)

Recommended child order for M20:

1. #327
2. #328
3. #329
4. #330
5. #331
6. #332
7. #333
8. #334 (final reconciliation only; keep last)

M20 workflow example:

1. Plan mutation intent:
   - `python -m aresforge plan-github-mutation --mutation-type issue_comment --planned-action "post child evidence" --target-issue <child>`

## M21 Self-Managed Milestone Execution Contract (Child #346)

Command:

- `python -m aresforge inspect-self-managed-milestone-execution-contract`

Behavior:

- read-only contract inspection
- defines required inputs/outputs for parent-driven sequential child execution
- documents dry-run default and explicit operator-approval mutation boundary
- documents targeted mutation boundary (single issue comment, single issue close, single PR body update)
- documents parent closeout readiness boundary
2. Review dry-run output, required approvals, and blocked reasons.
3. Execute targeted issue comment only when explicitly approved:
   - `python -m aresforge execute-github-issue-comment --issue <child> --comment-body "<evidence>" --execute --approval-marker <marker>`
4. Validate closeout readiness for a single issue target:
   - `python -m aresforge execute-github-issue-close --issue-target <child> --parent-issue <parent>`
5. Execute targeted issue close only when explicitly approved and ready:
   - `python -m aresforge execute-github-issue-close --issue-target <child> --parent-issue <parent> --execute --approval-marker <marker>`
6. Prepare PR body/update summary in dry-run mode:
   - `python -m aresforge prepare-pr-body-update --pr-number <pr> --target-issue <child> --scope-summary "<summary>" --validation-result "python -m pytest -> pass" --safety-note "dry-run by default"`
7. Inspect local audit records:
   - `python -m aresforge inspect-github-mutation-audit-log --limit 20`
8. If blocked/failure occurs, use targeted recovery only:
   - resolve blocked reasons on one issue/PR target
   - rerun one command in dry-run first
   - do not run bulk mutation commands

M20 safety boundaries:

- no autonomous broad mutation
- no bulk closure
- no parent closure before children are closed/accounted for
- dry-run/planning default for mutation features
- explicit approval required for execution paths
- local audit artifacts remain local-only unless explicitly exported by an operator

What not to do:

- do not run issue ranges or lists for closeout (`330-334`, `330,331`)
- do not close parent #326 while any M20 child remains open
- do not execute mutation commands without explicit approval marker
- do not use broad scripts that mutate multiple issues/PRs in one step
- do not commit local audit runtime artifacts

PowerShell plain text examples (no nested markdown fences):

- Set-Location C:\Projects\aresforge
- python -m aresforge plan-github-mutation --mutation-type issue_close --planned-action "close child after readiness" --target-issue 333
- python -m aresforge execute-github-issue-close --issue-target 333 --parent-issue 326

## Read-Only Milestone Inspection

Commands:

- `python -m aresforge inspect-milestone-state --parent-issue <parent>`

Behavior:

- read-only issue and milestone state inspection
- parent/child discovery from detectable references
- child state, lineage, and merged PR evidence hints summary
- no issue closure
- no PR creation
- no comments
- no GitHub edits

## Read-Only Milestone Queue Planning

Commands:

- `python -m aresforge plan-milestone-execution-queue --parent-issue <parent>`

Behavior:

- planning-only milestone child execution ordering
- deterministic child sequencing with final reconciliation issue last when detected
- blocker and missing lineage surfacing
- missing merged PR evidence signal surfacing
- explicit safety gates:
  - execution enabled false
  - close issues false
  - bulk closeout allowed false
  - operator review required true
- no issue closure
- no PR creation
- no comments
- no GitHub edits

## Per-Child Execution Gate Inspection (M19 #312)

Commands:

- `python -m aresforge inspect-child-execution-gates --issue <issue> --parent-issue <parent>`

Behavior:

- read-only gate inspection for one child issue
- evaluates start/PR/merge/close safety posture for the target child
- checks local cleanliness and branch naming posture
- checks open PR presence and merged PR evidence/readiness posture
- reports blockers and deterministic next recommended action
- never closes issues
- never creates PRs
- never comments on issues
- never mutates GitHub state

## Unified Milestone Dashboard (M18 #295)

Commands:

- `python -m aresforge inspect-milestone-dashboard --parent-issue <parent>`

Behavior:

- read-only consolidated dashboard built from milestone inspection, queue planning, evidence readiness, and final reconciliation planning outputs
- reports parent state, child issue state summary, accounted/unaccounted child signals, and deterministic queue recommendation
- surfaces evidence readiness status counts, final reconciliation readiness, and operator-required next actions
- preserves non-mutation safety gates and boundary confirmations
- never closes issues
- never creates PRs
- never comments on issues
- never mutates GitHub state

M19 #315 extension:

- dashboard now surfaces local sequential run-state when available
- output explicitly separates GitHub issue truth from local sequential run-state
- mismatch flags are raised when local sequential run-state and GitHub child discovery diverge

## Sequential Run-State Inspection (M19 #311)

Commands:

- `python -m aresforge inspect-sequential-run-state --parent-issue <parent>`
- `python -m aresforge inspect-sequential-run-state --parent-issue <parent> --write-local-state`

Behavior:

- builds a local sequential run-state snapshot from read-only milestone inspection, queue planning, and evidence readiness commands
- captures parent issue, current child recommendation, completed children, failed-step signal, PR/evidence summary, and next recommended action
- defaults to read-only mode without writing local files
- optional local persistence writes only to `.aresforge/sequential-run-state.json`
- never closes issues
- never creates PRs
- never comments on issues
- never mutates GitHub state

## Sequential Recovery Planning (M19 #313)

Commands:

- `python -m aresforge plan-sequential-run-recovery --parent-issue <parent>`

Behavior:

- reads persisted sequential run-state and compares against current dashboard and child gate inspection signals
- reports recovery states for failed validation, failed PR creation, unmerged PR, merged PR with missing evidence, closed child, stale branch, dirty tree, and dashboard mismatch
- returns deterministic next recommended action
- read-only/planning only by default
- never closes issues
- never creates PRs
- never comments on issues
- never mutates GitHub state

## Sequential Evidence/Handoff Package (M19 #314)

Commands:

- `python -m aresforge generate-sequential-handoff-package --parent-issue <parent>`
- `python -m aresforge generate-sequential-handoff-package --parent-issue <parent> --issue <child>`
- `python -m aresforge generate-sequential-handoff-package --parent-issue <parent> --write-package`

Behavior:

- generates structured per-child and per-milestone handoff/evidence package output
- includes child issue, branch, commit, PR, merge/main hash, validations, evidence URL if known, final child state, dashboard status, and next child recommendation
- read-only by default
- local artifact writing is opt-in using `--write-package`
- never closes issues
- never creates PRs
- never comments on issues
- never mutates GitHub state

## End-to-End Sequential Operator Workflow (M19 #316)

Recommended child order for M19:

1. #310
2. #311
3. #312
4. #313
5. #314
6. #315
7. #316
8. #317 (final reconciliation only; keep last)

Per-child one-at-a-time loop:

1. Sync clean main:
   - `git checkout main`
   - `git fetch origin`
   - `git pull --ff-only origin main`
   - `git status --short` (must be empty)
2. Create one dedicated child branch (example: `m19/<issue>-short-slug`).
3. Implement only the target child scope.
4. Run validation bundle:
   - `git diff --check`
   - `python -m pytest`
   - `python -m aresforge inspect-repo-governance`
   - `python -m aresforge inspect-milestone-dashboard --parent-issue <parent>`
   - `python -m aresforge inspect-milestone-state --parent-issue <parent>`
   - `python -m aresforge check-milestone-evidence-readiness --parent-issue <parent>`
5. Commit with issue reference and push branch.
6. Open one PR for one child issue.
7. Merge the PR only after readiness checks pass.
8. Sync clean main and rerun validation bundle.
9. Generate child evidence package:
   - `python -m aresforge generate-sequential-handoff-package --parent-issue <parent> --issue <child>`
10. Post issue-specific evidence comment scoped only to that child issue.
11. Close only the target child issue.
12. Re-run dashboard/readiness commands before starting next child.

Recovery and resume examples:

- Resume local status snapshot:
  - `python -m aresforge inspect-sequential-run-state --parent-issue <parent>`
- Persist local snapshot for handoff:
  - `python -m aresforge inspect-sequential-run-state --parent-issue <parent> --write-local-state`
- Generate recovery plan after interruption/failure:
  - `python -m aresforge plan-sequential-run-recovery --parent-issue <parent>`
- If blocked, stop progression, do not close current issue, and do not advance to next child until recovery action is resolved.

Evidence and closeout guidance:

- Every child must have:
  - one branch
  - one PR
  - one validation cycle on branch and on main after merge
  - one issue-specific evidence comment
  - one targeted closeout
- Evidence comments should include child issue number, branch, commit, PR URL, merge/main hash, files changed, validation results, safety notes, dashboard/readiness summary, and a statement that evidence applies only to that child.
- Never use bulk closeout commands.
- Never close parent until all children are closed/accounted for and final reconciliation is complete.

Safety boundaries:

- No autonomous broad mutation.
- No bulk issue closure.
- No parent closure before child sequence completion and explicit readiness proof.
- Prior milestone mutation is out of scope unless explicitly required for M19 documentation references.
- Local sequential run-state remains advisory and must not override GitHub issue truth.

## Evidence Readiness Checking (M17/#274 and M18/#299 enhancements)

Commands:

- `python -m aresforge check-issue-evidence-readiness --issue <issue>`
- `python -m aresforge check-milestone-evidence-readiness --parent-issue <parent>`

Behavior:

- read-only/planning-only evidence completeness classification
- duplicate/no-op PR prevention via evidence reuse recommendation
- schema-driven structured evidence block support with safe malformed/duplicate/conflict handling
- never closes issues
- never creates PRs
- never comments on issues
- never mutates GitHub state

## Parent Closeout Readiness (M18 #298)

Commands:

- `python -m aresforge inspect-parent-closeout-readiness --parent-issue <parent>`

Behavior:

- read-only parent closeout readiness report with explicit child lineage
- reports child state, evidence mapping status, individual closure/accounted signals
- reports blocked reasons, required operator actions, and safety gates
- never closes parent or children
- never creates PRs
- never comments on issues
- never mutates GitHub state

## Milestone Final Reconciliation Planning

Commands:

- `python -m aresforge plan-milestone-final-reconciliation --parent-issue <parent>`

Behavior:

- planning-only milestone final reconciliation readiness check
- inspects parent/child milestone state via read-only command surfaces
- verifies implementation children are closed or evidence-accounted before reconciliation
- confirms final reconciliation issue should be last
- surfaces likely source-of-truth docs requiring updates
- confirms docs-only expectation for final reconciliation
- confirms no generated evidence artifact changes are expected
- emits explicit non-mutation gates:
  - close issues false
  - create PR false
  - comment on issue false
  - mutation allowed false
  - operator review required true
- never closes issues
- never creates PRs
- never comments on issues
- never mutates GitHub state

## Script/Template Generation Commands (Read-Only Generators)

Commands:

- `python -m aresforge generate-evidence-comment-template --issue <issue>`
- `python -m aresforge generate-child-closeout-script --issue <issue>`

Behavior:

- generate operator-reviewed text/script artifacts only
- do not post comments automatically
- do not close issues automatically
- do not create PRs/branches automatically
- keep PowerShell output fence-safe for operator copy/review

## Controlled Autonomous Execution (M16)

Commands:

- `python -m aresforge run-autonomous-cycle --mode dry-run --parent-issue <parent> --target-issue <target>`
- `python -m aresforge run-autonomous-cycle --mode local-write --parent-issue <parent> --target-issue <target>`
- `python -m aresforge run-autonomous-cycle --mode branch-write --parent-issue <parent> --target-issue <target> --branch-name <branch> --commit-message <message>`
- `python -m aresforge run-autonomous-cycle --mode push-pr --parent-issue <parent> --target-issue <target> --branch-name <branch> --commit-message <message> --pr-title <title>`
- `python -m aresforge run-autonomous-cycle --mode closeout-eligible --parent-issue <parent> --target-issue <target> --branch-name <branch> --commit-message <message> --pr-title <title>`
- `python -m aresforge inspect-autonomous-run --run-id <id>`

Mode behavior:

- `dry-run`: read-only plan and validation path; no repository or GitHub mutation.
- `local-write`: local lifecycle progression with evidence generation; no GitHub mutation.
- `branch-write`: enables branch and commit mutation only after gate pass.
- `push-pr`: enables branch/commit plus push and PR creation after gate pass.
- `closeout-eligible`: enables push-pr path plus controlled issue closure after closeout gates pass.

## Fail-Closed Gate Design

Higher-permission modes require explicit inputs and fail closed when missing:

- `branch-write`: requires `--branch-name` and `--commit-message`
- `push-pr`: requires branch-write inputs plus `--pr-title`
- `closeout-eligible`: requires push-pr inputs plus validation pass, issue-PR linkage (`pr_number` + `pr_url`), and merged-PR evidence pass

## Evidence And Audit

- Every run writes evidence artifacts under `artifacts/evidence/generated`.
- Every mutation/evaluation step is recorded in DB-backed `run_steps`.
- Run lifecycle state is recorded in `autonomous_runs`.
- Failed runs still produce evidence and persisted step history.

## Human-Gated Mutation Boundaries

Allowed:

- human-triggered command execution
- explicit mode-scoped mutation
- evidence-backed run inspection

Not authorized:

- mutation in `dry-run`
- GitHub mutation in `local-write` or `branch-write`
- push/PR outside explicit higher-permission modes
- issue closure outside explicit `closeout-eligible`
- automatic PR merge
- background jobs, polling loops, or schedulers

## Governance Note

- `inspect-repo-governance` milestone naming warning may remain non-blocking (`milestone_naming_status.naming_ok: false`).
