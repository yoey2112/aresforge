# AresForge Roadmap

## Current Milestones

### M0-M8

Status: Completed.

### M9 - Persist Local Planning State And Drift Inspection

Status: In progress.

Child issues:

- #193 define persisted local planning state schema
- #194 define local-only planning state storage and safety contract
- #195 persist sprint planning state from structured sprint definitions
- #198 persist closeout planning snapshots
- #199 add read-only planning state inspection command
- #196 add read-only planning state comparison command
- #197 source-of-truth reconciliation

Planned outcomes:

- Local-only planning memory at `.aresforge/planning-state.json`.
- Explicit write-gated persistence from sprint generation and closeout planning commands.
- Read-only inspect/compare commands for local drift checks.
- No new GitHub mutation behavior.

## Standing Boundaries

- No autonomous setup/mutation behavior.
- No autonomous queue mutation.
- No autonomous merge/issue closure.
- No autonomous labels, milestones, comments, releases, or tags.
- Issue #39 remains retired historical validation evidence only.
- Issue #179 remains complete and unchanged.
