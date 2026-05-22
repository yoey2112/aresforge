# AresForge Roadmap

## Current Milestones

### M0-M8

Status: Completed.

### M9 - Persist Local Planning State And Drift Inspection

Status: Completed.

### M10 - Closeout Child-Link Discovery And Evidence Resolution

Status: Completed.

### M11 - Planning-State Closeout Drift Inspection

Status: Completed.

Child issues:

- #211 define planning-state closeout comparison contract
- #212 load persisted planning state for closeout comparison
- #213 compare planned children against live discovered children
- #214 improve closeout readiness evidence summary
- #217 add regression fixtures for planning/discovery drift
- #215 add operator documentation for closeout planning drift inspection
- #216 reconcile source-of-truth documentation

Implementation status:

- #211, #212, #213, #214, #217 implemented by merged integration PR #218.
- #215 and #216 completed by merged follow-up PR #219.

Delivered outcomes:

- `inspect-closeout-planning-drift` provides deterministic planned/discovered/matching/missing/extra group output.
- `planning_state_missing` is an explicit non-mutating warning posture (`ok: true`, `readiness_ok: false`) when no local planning state exists.
- read-only planning behavior remains unchanged.
- source-of-truth docs remain aligned with runnable command surface.

### M12 - Human-Gated Sprint Issue Creation Planner And Reconciliation

Status: In progress (final source-of-truth reconciliation pass).

Parent issue:

- #222 M12: Add human-gated sprint issue creation planner

Child issues:

- #223 define human-gated sprint issue creation planning contract
- #224 add sprint issue creation plan model and renderer
- #225 generate copy-paste-safe PowerShell issue creation blocks
- #226 add read-only CLI command for sprint issue creation planning
- #229 add regression fixtures for generated sprint issue scripts
- #227 document operator workflow for human-gated sprint issue creation
- #228 reconcile source-of-truth documentation after implementation

Implementation status:

- #223, #224, #225, #226, #229 implemented by merged integration PR #230.
- #227 implemented by merged operator documentation PR #231.
- #228 is the remaining documentation reconciliation scope for this pass.

Delivered M12 outcomes:

- `plan-sprint-issues` command added: `python -m aresforge plan-sprint-issues --definition <path>`.
- architecture contract added: `docs/architecture/SPRINT_ISSUE_CREATION_PLANNING_CONTRACT.md`.
- planner module added: `src/aresforge/operator/sprint_issue_planner.py`.
- regression coverage and fixtures added: `tests/test_sprint_issue_planner.py`, `tests/fixtures/m12-sprint-definition.json`, `tests/fixtures/m12-verification-failure-observed.json`.
- planner output remains read-only by default and mutation output remains human-gated only.

Required validation baseline after M12 doc reconciliation:

- `python -m pytest` -> `255 passed`
- `python -m aresforge inspect-repo-governance` -> `ok true`
- `python -m aresforge plan-sprint-issues --definition tests/fixtures/m12-sprint-definition.json` -> `ok true`

Remaining closeout expectation:

- After #228 merges, run QA/closeout planning for M12 parent #222 and child issues #223, #224, #225, #226, #229, #227, #228.

## Standing Boundaries

- No autonomous setup/mutation behavior.
- No autonomous queue mutation.
- No autonomous issue creation.
- No autonomous merge/issue closure.
- No autonomous labels, milestones, comments, releases, or tags.
- No automatic PR merge.
- Issue #39 remains retired historical validation evidence only.
- Issue #179 remains complete and unchanged.
