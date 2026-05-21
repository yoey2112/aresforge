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

## Boundaries

- Commands remain human-triggered.
- Planning-state writes are explicit and local-only.
- No autonomous merge/closeout/setup/queue mutation.
- No autonomous GitHub issue create/close/comment/label/milestone/release/tag.
- Generated GitHub issue scripts remain human-executed.
- Issue #39 remains protected historical evidence only.
