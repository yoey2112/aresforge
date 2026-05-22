# Sequential Run-State Schema

## Purpose

Define the local-only schema and safety boundaries for persisted sequential milestone execution state introduced in M19.

## Local-Only Storage

- Default path: `.aresforge/sequential-run-state.json`
- Scope: local planning artifact only
- Source-of-truth priority:
  - GitHub issue/PR state remains primary truth
  - local sequential run-state is advisory/operator support

## Schema (v1.0)

Top-level:

- `schema_version`: currently `1.0`
- `records`: list of one record per parent issue

Per-record fields:

- `schema_version`
- `generated_at_utc`
- `parent_issue`
- `current_child_issue`
- `completed_children`
- `failed_step`
- `pr_references`
- `validation_status`
- `evidence_status`
- `next_recommended_action`
- `dashboard_context`

## Safety Boundaries

- No GitHub mutation.
- No issue closure.
- No PR creation.
- No comment creation.
- No bulk mutation.
- Local write only when explicitly requested.

## Recovery/Resume Value

The schema is intended to preserve enough execution context to:

- identify the current child in sequence
- retain completed child lineage
- surface failure category for recovery planning
- preserve evidence/readiness status context
- provide deterministic next-action guidance
