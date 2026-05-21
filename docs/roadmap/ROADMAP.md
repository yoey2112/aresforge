# AresForge Roadmap

## Current Milestones

### M0-M8

Status: Completed.

### M9 - Persist Local Planning State And Drift Inspection

Status: Completed.

### M10 - Closeout Child-Link Discovery And Evidence Resolution

Status: In progress.

Child issues:

- #202 define closeout child-link discovery contract
- #203 parse parent issue body/comments for active child issue references
- #204 parse child issue bodies for parent references
- #205 harden active vs historical/safety/protected closeout link classification
- #206 improve closeout evidence report with discovered child links
- #208 add M9-style closeout planner regression tests
- #207 source-of-truth reconciliation

Planned outcomes:

- `plan-batch-closeout` discovers child issues from parent body/comments and child parent-link evidence.
- corrected/reposted child issue index comments are recognized.
- evidence reports include discovered child-link source and classification.
- historical/safety/protected references are excluded from active linkage.
- read-only planning behavior remains unchanged.

## Standing Boundaries

- No autonomous setup/mutation behavior.
- No autonomous queue mutation.
- No autonomous merge/issue closure.
- No autonomous labels, milestones, comments, releases, or tags.
- Issue #39 remains retired historical validation evidence only.
- Issue #179 remains complete and unchanged.
