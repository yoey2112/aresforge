# AresForge Roadmap

## Current Milestones

### M0-M8

Status: Completed.

### M9 - Persist Local Planning State And Drift Inspection

Status: Completed.

### M10 - Closeout Child-Link Discovery And Evidence Resolution

Status: Completed.

### M11 - Planning-State Closeout Drift Inspection

Status: In progress (documentation/reconciliation closeout pass).

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
- #215 and #216 are the remaining documentation/reconciliation scope for this pass.

Planned outcomes:

- `inspect-closeout-planning-drift` provides deterministic planned/discovered/matching/missing/extra group output.
- `planning_state_missing` is an explicit non-mutating warning posture (`ok: true`, `readiness_ok: false`) when no local planning state exists.
- read-only planning behavior remains unchanged.
- source-of-truth docs remain aligned with runnable command surface.

### M12 - Governance Reference Hygiene (Proposed)

Status: Proposed follow-up.

Proposed outcome:

- reduce recurring protected historical issue references from active governance/operator paths while preserving required historical validation evidence.

## Standing Boundaries

- No autonomous setup/mutation behavior.
- No autonomous queue mutation.
- No autonomous merge/issue closure.
- No autonomous labels, milestones, comments, releases, or tags.
- Issue #39 remains retired historical validation evidence only.
- Issue #179 remains complete and unchanged.
