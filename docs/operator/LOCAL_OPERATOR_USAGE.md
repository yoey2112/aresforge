# Local Operator Usage

## Core Validation Bundle

- `python -m pytest`
- `python -m aresforge inspect-repo-governance`
- `python -m aresforge generate-sprint-issue-script --definition tests/fixtures/m8-sprint-definition.json`
- `python -m aresforge inspect-planning-state`
- `python -m aresforge compare-planning-state`
- `python -m aresforge inspect-closeout-planning-drift --parent-issue <number>`
- `git diff --check`

## Structured Sprint Issue Script Generation

- `python -m aresforge generate-sprint-issue-script --definition <definition.json>`
- `python -m aresforge generate-sprint-issue-script --definition <definition.json> --write-planning-state`

Default behavior is output-only. Planning-state writes are explicit and local-only.

## Batch Closeout Planning

- `python -m aresforge plan-batch-closeout --parent-issue <number>`
- `python -m aresforge plan-batch-closeout --parent-issue <number> --write-planning-snapshot`

Default behavior remains read-only. Snapshot writes are explicit and local-only.

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
- the protected historical reference remains protected historical evidence only.

