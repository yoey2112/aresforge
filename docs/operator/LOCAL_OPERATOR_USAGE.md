# Local Operator Usage

## Core Validation Bundle

- `python -m pytest`
- `python -m aresforge inspect-repo-governance`
- `python -m aresforge plan-sprint-issues --definition tests/fixtures/m12-sprint-definition.json`
- `python -m aresforge plan-self-managed-milestone`
- `python -m aresforge plan-self-managed-milestone --mode local-write`
- `python -m aresforge generate-sprint-issue-script --definition tests/fixtures/m8-sprint-definition.json`
- `python -m aresforge inspect-planning-state`
- `python -m aresforge compare-planning-state`
- `python -m aresforge inspect-closeout-planning-drift --parent-issue <number>`
- `git diff --check`

## Human-Gated Sprint Issue Creation Planning (M12)

Purpose:

- Generate a deterministic, read-only sprint issue creation plan from a local definition file.
- Produce human-reviewable parent/child issue bodies and a copy/paste PowerShell mutation script.
- Gate implementation progress on post-creation verification pass/fail output.

Command:

- `python -m aresforge plan-sprint-issues --definition <path>`

Required local input:

- A local JSON definition file passed to `--definition`.
- Required root fields: `sprint_id`, `repo`, `parent`, `children`.
- Parent and child bodies must include `## Safety Posture`, `## Acceptance Criteria`, and `## Validation`.
- Child bodies must include `Part of #{{PARENT_ISSUE_NUMBER}}`.
- Nested markdown fences (``` ) are rejected to keep generated PowerShell here-strings copy/paste-safe.

Read-only default behavior:

- `plan-sprint-issues` is inspection/output-only and does not execute `gh`.
- AresForge does not create issues by default.
- AresForge does not close issues, merge PRs, or perform automatic closeout.

Generated output posture:

- `inspection_mode` is `read_only_generated_plan`.
- `mutation_posture` is `human_gated_output_only`.
- Generated mutation commands are copy/paste output for human review and execution only.
- Repair guidance is text-only and human-gated.

Operator workflow:

1. Run `python -m aresforge plan-sprint-issues --definition <path>`.
2. Review `rendered.parent_issue_body` for scope and safety-boundary text.
3. Review each entry in `rendered.child_issue_bodies` for parent linkage (`Part of #{{PARENT_ISSUE_NUMBER}}`), required sections, and safety-boundary text.
4. Review `rendered.powershell_issue_creation_block` line-by-line before any execution.
5. Copy/paste and run the generated PowerShell block manually if the plan is approved.
6. Run the generated post-creation verification section from the output (`rendered.final_post_creation_verification_block`) to compare expected plan versus live issue state.
7. Continue implementation only if verification reports pass.

Manual execution of generated issue creation:

- Use the generated `powershell_issue_creation_block` as-is after review.
- Run it manually in a PowerShell session with `gh` authenticated for the target repo.
- Live GitHub inspection occurs only when the human operator runs generated commands.

Post-creation verification usage:

- Verify expected parent title vs actual parent title.
- Verify expected child count vs actual child count.
- Verify missing expected child titles and unexpected child titles.
- Verify parent child-index completeness.
- Verify required body sections and safety-boundary text presence.
- Treat pass/fail as a gate for implementation start.

If verification fails:

- Do not continue implementation.
- Review the mismatch report and reconcile parent/child state.
- Use generated repair guidance as human-gated text instructions.
- Re-run verification manually until it passes.

Why verification is required:

- Observed M12 failure coverage (see `tests/fixtures/m12-verification-failure-observed.json`) showed realistic mismatch modes:
  - missing expected child issues,
  - incomplete parent child index,
  - and child safety/body-section drift.
- Because those failure modes can silently break implementation tracking, implementation should not proceed until verification passes.

Relationship to AresForge safety boundaries:

- Planner output can include mutation commands, but command generation itself remains read-only.
- Mutation authority remains with the human operator, not AresForge.
- No autonomous GitHub mutation is performed (create/close/comment/label/milestone/merge/release/tag).

## Structured Sprint Issue Script Generation

- `python -m aresforge generate-sprint-issue-script --definition <definition.json>`
- `python -m aresforge generate-sprint-issue-script --definition <definition.json> --write-planning-state`

Default behavior is output-only. Planning-state writes are explicit and local-only.

## Batch Closeout Planning

- `python -m aresforge plan-batch-closeout --parent-issue <number>`
- `python -m aresforge plan-batch-closeout --parent-issue <number> --write-planning-snapshot`

Default behavior remains read-only. Snapshot writes are explicit and local-only.

M13 closeout evidence recognition:

- `plan-batch-closeout` recognizes human-gated closeout evidence from issue bodies and issue comments.
- Recognized comment evidence includes:
  - merged PR references such as `PR #<number>`
  - validation pass lines such as `python -m ... -> ok true` or `... passed`
  - documentation reconciliation lines, including source-of-truth reconciliation and updated source-of-truth document references
- Evidence recognition remains deterministic and read-only.
- Closeout mutation remains human-gated and is not performed by this command.
- Qualifying merged PR references are classification evidence, not active children.
- Historical parent-body issue references used for historical context are non-active and excluded from active child discovery.

Closeout comment template guidance:

- Closeout comments should include a `Documentation reconciliation evidence` section.
- Required documentation status line (choose one):
  - `updated` with specific files (for example source-of-truth docs when changed),
  - `reviewed_current` when docs were reviewed and already current,
  - `not_applicable` with rationale.
- Missing documentation reconciliation evidence can keep parent closeout planning incomplete even if implementation PRs are merged.
- Keep closeout execution human-gated; do not introduce autonomous GitHub mutation.
M14 closeout classification cleanup baseline:

- issue #243 resolved by merged PR #244: historical parent-body issue references are not treated as active children.
- issue #245 resolved by merged PR #246: merged PR references are treated as evidence, not active children.
- parent #233 historical references #223 through #229 remain historical/non-active.
- PR references #230, #231, #232, and #242 are recognized as evidence.
- active requested/discovered child range for parent #233 remains #234 through #241.

## Planning State Inspection

- `python -m aresforge inspect-planning-state`
- `python -m aresforge compare-planning-state`

Both commands are read-only and never create local planning-state files.

## Closeout Planning Drift Inspection

Run:

- `python -m aresforge inspect-closeout-planning-drift --parent-issue <number>`

When to run:

- after generating and/or persisting sprint planning state for a parent issue
- before closeout decisions when you need planned-vs-discovered child alignment evidence
- during documentation/validation passes to confirm read-only closeout readiness posture

Expected input:

- `--parent-issue <number>` (required)
- optional planning-state path via shared CLI planning-state option defaults (local-only)

Expected output groups:

- planned/discovered overlap: `planned_child_issues`, `discovered_child_issues`, `matching_child_issues`
- drift: `planned_missing_from_discovery`, `discovered_extra_not_planned`
- child state: `closed_child_issues`, `open_child_issues`, `unresolved_child_issues`
- filtered references: `protected_or_historical_references_excluded`
- readiness summary: `readiness_ok`, `evidence_summary`

`planning_state_missing` behavior:

- if local planning state does not exist, command remains successful and read-only (`ok: true`, `state_exists: false`)
- readiness is blocked (`readiness_ok: false`) and `evidence_summary.status` is `planning_state_missing`
- output includes warning text and empty comparison groups instead of mutating or synthesizing state

Read-only safety posture:

- command is inspection-only and does not write planning state
- command does not create/close/comment/label/milestone/merge/release/tag any GitHub issue/PR state

What this command does not do:

- does not resolve drift automatically
- does not override human closeout decisions
- does not replace full closeout evidence review
- does not perform autonomous setup/mutation actions

## Boundaries

- Commands remain human-triggered.
- Planning-state writes are explicit and local-only.
- No autonomous merge/closeout/setup/queue mutation.
- No autonomous GitHub issue create/close/comment/label/milestone/release/tag.
- Generated GitHub issue scripts remain human-executed.
- The protected historical reference remains protected historical evidence only.
- GitHub mutation remains human-gated and copy/paste-driven.

## M15 Contract Reference

- Self-managed milestone planning contract authority: `docs/architecture/SELF_MANAGED_MILESTONE_PLANNING_CONTRACT.md`.
- Any future milestone planning or issue script generation additions must default to read-only planning output and remain human-gated for GitHub mutation.

## Self-Managed Milestone Planner (M15)

- `python -m aresforge plan-self-managed-milestone`
- `python -m aresforge plan-self-managed-milestone --mode local-write`

Default mode is read-only.

Mode behavior:

- `read-only`: reads local source-of-truth docs, performs read-only GitHub inspection where available, emits deterministic plan JSON, and writes a local evidence artifact package.
- `local-write`: includes all read-only behavior plus local DB persistence for `autonomous_runs` and ordered `run_steps`.
- `branch-write`, `pr-write`, `closeout-write`, `full-auto`: intentionally not implemented in M15 and fail safely without mutation.

Safety boundaries:

- No GitHub mutation is performed in any mode.
- No labels, milestones, issues, PRs, branches, workflows, or settings are created or modified.
- Local DB state mutation is allowed only in `local-write`.
