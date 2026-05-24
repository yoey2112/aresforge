# Local Operator Usage

## M25 Automatic Canonical Marker Emission Workflow

When to run:

- Run M25 readiness-by-construction checks while executing each child in sequence for a parent milestone.
- Use it to confirm canonical marker emission coverage across child, PR, parent, and closeout-comment evidence domains.
- Keep parent closeout blocked until both milestone execution readiness and marker emission readiness are true.

M25 command set (read-only by default):

- `python -m aresforge inspect-automatic-canonical-evidence-emission-contract`
- `python -m aresforge generate-child-closeout-evidence-bundle --parent-issue <parent> --child-issue <child>`
- `python -m aresforge generate-pr-evidence-bundle --issue <child> --pr <pr>`
- `python -m aresforge generate-parent-closeout-evidence-bundle --parent-issue <parent>`
- `python -m aresforge generate-evidence-comment-template --issue <issue>`
- `python -m aresforge check-closeout-readiness-by-construction --parent-issue <parent>`

Automatic canonical marker emission domains checked by readiness-by-construction:

- child evidence bundle canonical marker completeness
- PR evidence bundle canonical marker completeness
- parent closeout evidence bundle canonical marker completeness
- closeout comment canonical marker completeness

Readiness-by-construction interpretation:

- `readiness_by_construction.ready=true` means marker emission readiness and milestone execution readiness are both satisfied.
- `readiness_by_construction.ready=false` with `blocked_reasons` means closeout remains blocked and remediation should be targeted.
- `post_hoc_marker_repair_required=true` means generated marker completeness is not sufficient and readiness fails by construction.

Operator approval boundary:

- Marker generation/checking, preflight generation, snapshot generation, and readiness-by-construction checks remain read-only by default.
- Posting issue comments, editing PR bodies, and closing issues remain separate operator-approved targeted actions.
- Never use bulk issue closure.
- Never close the parent before children are closed/accounted for and parent readiness gates pass.

PowerShell-safe guidance:

- Avoid nested markdown fences inside here-strings.
- Use plain text command examples in issue/comment bodies.
- Prefer `--body-file` and `--comment-file` for multiline mutation content.

## M24 Canonical Evidence Marker Workflow

When to run:

- Run canonical marker generation before posting child, PR, or parent evidence comments.
- Run preflight snapshot generation before and after reconciliation updates to audit drift.
- Keep parent closeout blocked until marker + readiness checks report ready.

Canonical marker command set (read-only by default):

- `python -m aresforge inspect-canonical-evidence-marker-contract`
- `python -m aresforge generate-child-evidence-marker-template --parent-issue <parent> --child-issue <child>`
- `python -m aresforge generate-pr-evidence-marker-template --issue <child> --pr <pr>`
- `python -m aresforge generate-parent-closeout-marker-template --parent-issue <parent>`
- `python -m aresforge generate-preflight-baseline-snapshot --parent-issue <parent>`
- `python -m aresforge diff-preflight-snapshots --before <before_snapshot.json> --after <after_snapshot.json>`

Marker types and required fields:

- `child_evidence`: parent issue, child issue, branch, commit, PR, validation summary, safety notes
- `pr_evidence`: issue, PR, branch, commit, changed files, validation summary, merge status, safety posture, evidence status
- `parent_closeout_evidence`: parent issue, child issue list, child-to-PR mapping, final main HEAD, final validation results, readiness gate summary, safety confirmations, closeout readiness state
- `reconciliation_audit`: baseline snapshot, post-reconciliation snapshot, snapshot diff, audit classification, warnings/deviations

Snapshot and diff interpretation:

- `no-change`: no readiness signal improvements/regressions detected
- `improved`: one or more readiness signals improved and none regressed
- `regressed`: one or more readiness signals regressed and none improved
- `mixed`: both improvements and regressions detected in the same diff

Marker-complete evidence block examples (plain text, copy/paste safe):

- Child evidence marker:
   [ARESFORGE_CANONICAL_EVIDENCE_MARKER]
   marker_type: child_evidence
   marker_state: ready
   required.parent_issue: #400
   required.child_issue: #409
   required.branch: m24-409-canonical-marker-workflow-docs
   required.commit: <commit_sha>
   required.pr: #<pr>
   required.validation_summary: git diff --check=pass; pytest=pass; inspect-repo-governance=pass
   required.safety_notes: read-only by default; targeted mutation only
   optional.closeout_status: closed
   optional.evidence_comment_status: posted
   optional.merge_status: merged
   missing_required_fields: <none>
   invalid_reasons: <none>
   [/ARESFORGE_CANONICAL_EVIDENCE_MARKER]

- Parent closeout evidence marker:
   [ARESFORGE_CANONICAL_EVIDENCE_MARKER]
   marker_type: parent_closeout_evidence
   marker_state: ready
   required.parent_issue: #400
   required.child_issue_list: #401, #402, #403, #404, #405, #406, #407, #408, #409, #410
   required.child_to_pr_mapping: #401->#411, #402->#412, #403->#413, #404->#414, #405->#415, #406->#416, #407->#417, #408->#418, #409->#<pr>, #410->#<pr>
   required.final_main_head: <main_head>
   required.final_validation_results: git diff --check=pass; pytest=pass; inspect-repo-governance=pass
   required.readiness_gate_summary: parent_closeout_ready=true; blocked_reasons=none
   required.safety_confirmations: read-only generation; explicit operator-approved targeted mutation only
   required.closeout_readiness_state: ready
   optional.warnings_deviations: milestone_naming_status.naming_ok=false; missing milestone assignment warnings
   missing_required_fields: <none>
   invalid_reasons: <none>
   [/ARESFORGE_CANONICAL_EVIDENCE_MARKER]

Explicit mutation boundary:

- Marker generation, preflight generation, snapshot generation, and evidence bundle generation are read-only by default.
- Repair/update guidance is copy/paste guidance only unless a separate targeted mutation command is explicitly approved.
- PR body update, issue comment, and issue closeout execution remain separate operator-approved targeted commands.
- Never bulk-close child issues; never close parent before child closeout/readiness gates pass.

## M23 Lineage And Evidence Preflight Workflow

When to run:

- Run M23 preflight before any parent closeout action.
- Run after each child merge/closeout to detect lineage/evidence/PR mapping drift early.
- Run before parent evidence bundle generation and before parent closeout readiness review.

Primary command set:

- `python -m aresforge inspect-milestone-closeout-preflight-contract`
- `python -m aresforge inspect-parent-child-linkage-preflight --parent-issue <parent>`
- `python -m aresforge inspect-child-evidence-marker-preflight --parent-issue <parent>`
- `python -m aresforge inspect-pr-mapping-preflight --parent-issue <parent>`
- `python -m aresforge generate-closeout-preflight-repair-guidance --parent-issue <parent>`
- `python -m aresforge inspect-milestone-closeout-preflight --parent-issue <parent>`

How M23 preflight relates to existing readiness commands:

- `inspect-milestone-dashboard` and `inspect-milestone-state` remain the source for parent/child state and ordering.
- `check-milestone-evidence-readiness` and `inspect-parent-closeout-readiness` remain parent closeout gates.
- `inspect-milestone-closeout-preflight` adds strict lineage + evidence marker + PR mapping detectability checks before parent closeout.
- `generate-parent-closeout-evidence-bundle` should be run after preflight reports ready (or after operator-reviewed warning remediation).

State interpretation:

- `ready`: no blocked/warning/unknown findings; closeout preflight gate is satisfied.
- `blocked`: hard gaps found (for example missing lineage, missing PR mapping, missing evidence marker block).
- `warning`: partial/ambiguous findings requiring operator remediation before closeout.
- `unknown`: preflight could not determine required signal state from current data.

Repair guidance usage:

- `generate-closeout-preflight-repair-guidance` output is copy/paste-safe guidance only.
- Repair guidance is not mutation execution.
- Mutation remains a separate operator-approved targeted action.

PowerShell-safe examples (plain text only):

- `python -m aresforge inspect-milestone-closeout-preflight --parent-issue <parent>`
- `python -m aresforge generate-closeout-preflight-repair-guidance --parent-issue <parent>`
- `gh issue edit <parent> --body-file artifacts/issue-<parent>-body.md`
- `gh issue comment <child> --body-file artifacts/issue-<child>-evidence.txt`
- `gh pr view <pr_number> --json state,mergeCommit,url`

Operator approval boundary:

- Preflight commands are read-only by default.
- PR/issue/body/comment mutation commands require explicit operator approval and targeted scope.
- Bulk closure is forbidden.
- Parent closeout is forbidden until children are closed/accounted for and parent readiness/preflight gates pass.

## M22 Evidence Bundle Workflow

M22 issue/PR mapping status:

- parent `#362` OPEN
- child `#363` CLOSED via PR `#372`
- child `#364` CLOSED via PR `#373`
- child `#365` CLOSED via PR `#374`
- child `#366` CLOSED via PR `#375`
- child `#367` CLOSED via PR `#376`
- child `#368` CLOSED via PR `#377`
- child `#369` CLOSED via PR `#378`
- child `#370` CLOSED via PR `#379`
- child `#371` OPEN via PR `#380` (final reconciliation, processed last)

Command inventory:

- `python -m aresforge inspect-evidence-bundle-automation-contract`
- `python -m aresforge generate-child-closeout-evidence-bundle --parent-issue <parent> --child-issue <child>`
- `python -m aresforge generate-parent-closeout-evidence-bundle --parent-issue <parent>`
- `python -m aresforge generate-pr-evidence-bundle --issue <issue> --pr <pr>`
- `python -m aresforge simulate-evidence-bundle-generation --parent-issue <parent>`

Read-only defaults and approval boundary:

- all evidence bundle generation commands are read-only by default
- generation commands must not close issues, edit PRs, or post comments automatically
- targeted mutation remains operator-approved and narrow (`gh issue close <issue>`, `gh issue comment <issue>`, `gh pr edit <pr> --body-file <file>`)
- never bulk-close child issues
- never close parent before child closeout/accounting and readiness checks pass

Child closeout bundle flow:

1. Generate child evidence body text.
2. Replace placeholders with concrete branch/commit/files/validation evidence.
3. Post one targeted issue comment for one child issue.
4. Close only that child issue.

Commands:

- `python -m aresforge generate-child-closeout-evidence-bundle --parent-issue <parent> --child-issue <child>`
- `gh issue comment <child> --body-file <comment_file>`
- `gh issue close <child> --comment "Closing after merged PR and posted evidence."`

Parent closeout bundle flow:

1. Run parent readiness checks and generate parent evidence bundle.
2. Confirm `parent_closeout_ready` is `true` and blocked reasons are empty.
3. Post one targeted parent evidence comment.
4. Close only the parent issue.

Commands:

- `python -m aresforge inspect-parent-closeout-readiness --parent-issue <parent>`
- `python -m aresforge generate-parent-closeout-evidence-bundle --parent-issue <parent>`
- `gh issue comment <parent> --body-file <comment_file>`
- `gh issue close <parent> --comment "Parent closeout after readiness confirmation."`

PR evidence body flow:

1. Generate deterministic PR evidence body text.
2. Review and save the text.
3. Apply one targeted PR body update only when explicitly approved.

Commands:

- `python -m aresforge generate-pr-evidence-bundle --issue <issue> --pr <pr>`
- `gh pr edit <pr> --body-file artifacts/pr-<pr>-body.md`
- `python -m aresforge prepare-pr-body-update --pr-number <pr> --target-issue <issue> --scope-summary "<summary>"`

Validation summary normalization:

- Validation summaries are normalized to: `pass`, `fail`, `warning`, `unknown`.
- Common labels are normalized for deterministic evidence output:
   - `git diff --check`
   - `python -m pytest`
   - `python -m aresforge inspect-repo-governance`
   - `python -m aresforge inspect-milestone-dashboard`
   - `python -m aresforge inspect-milestone-state`
   - `python -m aresforge check-milestone-evidence-readiness`
   - `python -m aresforge inspect-parent-closeout-readiness`

Dry-run simulation flow:

- `python -m aresforge simulate-evidence-bundle-generation --parent-issue <parent>`

Simulation guarantees:

- no mutation by default
- final reconciliation must remain last
- blocked and ready parent bundle states are represented for fixture coverage
- child and PR evidence generation paths are covered in dry-run planning form

Known warnings/deviations carried forward:

- `milestone_naming_status.naming_ok` remains `false` (non-blocking warning).
- parent/child GitHub milestone assignment gaps may still appear as warnings.
- `run-sequential-child-closeout-flow` requires explicit `--comment-body` in dry-run and execute modes.

PowerShell safety for issue/comment bodies:

- avoid nested markdown fences inside here-strings
- use plain text command examples inside issue/comment bodies
- prefer `--body-file` and `--comment-file` for multiline content

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

## M21 End-to-End Dry-Run Simulation (Child #351)

Command:

- `python -m aresforge simulate-self-managed-milestone-execution --parent-issue <parent>`

Behavior:

- read-only simulation only
- validates parent input, child discovery, sequential ordering, validation envelope, dry-run mutation planning, handoff planning, and parent closeout readiness blocking
- confirms no GitHub mutation, no issue closure, and no bulk closeout path
- preserves final reconciliation as the last child in sequence
- reports the recommended next open child issue based on current milestone dashboard state

## M21 Self-Managed Child Workflow (Child #352)

Use this workflow for M21 parent execution where each child has exactly one branch, one PR, one evidence comment, and one targeted closeout.

Start from parent issue:

1. Sync clean main:
   - `git checkout main`
   - `git fetch origin`
   - `git pull --ff-only origin main`
   - `git status --short` (must be empty)
2. Inspect parent state and child ordering:
   - `python -m aresforge inspect-milestone-dashboard --parent-issue <parent>`
   - `python -m aresforge inspect-milestone-state --parent-issue <parent>`
   - `python -m aresforge inspect-self-managed-milestone-execution-contract`
3. Run read-only simulation before implementation:
   - `python -m aresforge simulate-self-managed-milestone-execution --parent-issue <parent>`
4. Select only the recommended next open child issue (do not skip ahead; keep final reconciliation last).
5. Create one branch for that child issue and implement only that issue scope.
6. Run required validation for that child:
   - `git diff --check`
   - `python -m pytest`
   - `python -m aresforge inspect-repo-governance`
   - `python -m aresforge inspect-milestone-dashboard --parent-issue <parent>`
   - `python -m aresforge inspect-milestone-state --parent-issue <parent>`
   - `python -m aresforge inspect-self-managed-milestone-execution-contract`
   - `python -m aresforge run-sequential-child-closeout-flow --parent-issue <parent> --child-issue <child> --comment-body "M21 child evidence draft"`
   - `python -m aresforge generate-sequential-closeout-execution-package --parent-issue <parent> --child-issue <child>`
7. Open and merge one PR for one child issue only.
8. Sync clean main again and re-run validation commands.
9. Generate handoff/recovery output:
   - `python -m aresforge generate-self-managed-milestone-handoff --parent-issue <parent> --completed-child <child> --next-child <next-child>`
10. Post targeted evidence comment and close only the target child issue with explicit execution approval.
11. Re-check child and parent state:
   - `gh issue view <child> --json number,state,closedAt,url`
   - `gh issue view <parent> --json number,state,title,url`
12. Repeat from step 1 for the next open child.

M21 parent closeout guardrails:

- never close the parent while any child remains open or unaccounted for
- run readiness checks before parent closeout:
  - `python -m aresforge check-milestone-evidence-readiness --parent-issue <parent>`
  - `python -m aresforge inspect-parent-closeout-readiness --parent-issue <parent>`
- close parent only when `parent_closeout_ready` is true and blocked reasons are empty
- parent closeout must remain parent-targeted only and must not change child issue states

PowerShell issue/comment body guidance:

- avoid nested markdown fences inside here-strings
- prefer plain text command examples inside issue/comment bodies
- for multiline PR body/comment content, use `--body-file` or `--comment-file` rather than inline shell-escaped markdown
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
