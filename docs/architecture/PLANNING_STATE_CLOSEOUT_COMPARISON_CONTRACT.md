# Planning State Closeout Comparison Contract

## Purpose

Define a read-only M11 comparison between persisted local planning state and live closeout child-link discovery for one parent issue.

## Inputs

- local planning state file (default: `.aresforge/planning-state.json`)
- parent issue number
- live GitHub issue data fetched through existing read-only closeout planning/discovery helpers

## Outputs

`inspect-closeout-planning-drift` emits deterministic JSON including:

- `command`
- `ok`
- `inspection_mode`
- `state_exists`
- `planning_state_path`
- `parent_issue`
- `planned_child_issues`
- `discovered_child_issues`
- `matching_child_issues`
- `planned_missing_from_discovery`
- `discovered_extra_not_planned`
- `closed_child_issues`
- `open_child_issues`
- `unresolved_child_issues`
- `protected_or_historical_references_excluded`
- `evidence_summary`
- `readiness_ok`

## Comparison Groups

- Planned children are sourced from persisted sprint plans for the target parent issue.
- Discovered children are sourced from live closeout child-link discovery.
- Matching children are intersection of planned/discovered.
- Planned-missing and discovered-extra groups are reported explicitly and never ignored.
- Closed/open/unresolved are based on currently fetched child issue state for the compared child set.

## Evidence Summary Behavior

- Preserves conservative closeout posture from existing closeout readiness.
- Adds drift-aware blocking signals when planning/discovery diverge or child states are unresolved.
- Distinguishes:
  - present evidence (for example merged PR evidence rows detected),
  - missing evidence (including drift-derived gaps),
  - not-applicable evidence (currently empty when no explicit N/A conditions are proven).
- Must not mark work ready when drift or unresolved child state prevents reliable closeout confidence.

## `planning_state_missing` Behavior

- Missing planning state is a non-mutating inspection result (`ok: true`, `state_exists: false`) rather than a write/recovery path.
- Comparison groups are empty and readiness is blocked (`readiness_ok: false`).
- `evidence_summary.status` is `planning_state_missing` and `missing_evidence` includes `planning_state_missing`.
- Warning text is returned for operator visibility.

## Protected/Historical Handling

- Protected historical/safety references are excluded from active planned/discovered child groups.
- Protected/historical exclusions are surfaced for traceability in `protected_or_historical_references_excluded`.
- Protected issue behavior remains historical/safety-only and out of active implementation linkage.

## Read-Only Safety Posture

- Command is read-only by default and by design.
- No planning-state writes.
- No GitHub mutation (no create/close/comment/label/milestone/merge/release/tag actions).

## What The Command Does Not Do

- Does not perform any automatic issue-state reconciliation.
- Does not mutate planning state to repair drift.
- Does not replace human-gated closeout decisions.

## Known Limitations

- Comparison quality depends on available planning-state coverage for the target parent.
- Unresolved child state may occur when issue lookup is unavailable/incomplete.
- Evidence summary enriches classification signals but does not replace human-gated closeout review.
