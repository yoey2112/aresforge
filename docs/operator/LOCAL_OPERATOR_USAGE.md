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
