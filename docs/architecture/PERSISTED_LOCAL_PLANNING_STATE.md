# Persisted Local Planning State

## Purpose

Define the M9 local planning memory contract. This state is local-only operator memory and is not GitHub source of truth.

## State File

- Default path: `.aresforge/planning-state.json`
- The directory/file are created only by explicit write flags.
- Read-only commands must not create `.aresforge`.

## Schema

Top-level fields:

- `schema_version` (current: `1.0`)
- `sprint_plans` (planned sprint records)
- `closeout_snapshots` (observed closeout planning records)
- `planned_state` (derived planned view)
- `observed_state` (derived observed view)
- `historical_snapshots` (closeout snapshot history)
- `command_runs` (command + local write metadata)

### Sprint Plan Record

- `sprint_id`
- `source.definition_path`
- `source.repo`
- `command`
- `parent_issue.number`
- `parent_issue.title`
- `children[].number`
- `children[].title`
- `relationships[]` parent/child linkage metadata

### Closeout Snapshot Record

- `snapshot_id`
- `parent_issue`
- `command`
- `closeout_plan`
- `evidence_report`
- `observed_children[]`

## Deterministic Serialization

- UTF-8 JSON
- `indent=2`
- `sort_keys=true`
- trailing newline
- deterministic list ordering where implemented (sprint ids, snapshot ids, relationship keys)

## Safety Contract

- Local file only; no GitHub mutation.
- Writes are explicit and human-triggered only:
  - `generate-sprint-issue-script --write-planning-state`
  - `plan-batch-closeout --write-planning-snapshot`
- Read-only inspection commands never write:
  - `inspect-planning-state`
  - `compare-planning-state`

## Lifecycle

1. Missing file is allowed and treated as no local memory yet.
2. Explicit write commands may create/update state.
3. Invalid/unsupported files are reported safely; no auto-repair.
