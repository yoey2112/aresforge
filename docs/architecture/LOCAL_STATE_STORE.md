# Local State Store

## Purpose

This document defines the first runnable local state-store layer introduced for Issue #81.

Unlike the earlier M2 design documents, this file describes implemented local behavior rather than documentation-only intent. The goal is practical: give AresForge a local operator, a local PostgreSQL-backed state store, repo-stored migrations, and reviewable artifact outputs without introducing autonomous GitHub control.

## Scope

The Issue #81 local state store covers:

- PostgreSQL as the operational system of record for local runtime state
- Repo-stored SQL migrations under `migrations/`
- A migration runner inside the local CLI
- Minimal queue, work-item, prompt, evidence, approval, documentation-state, and audit tables
- Local artifact files under `artifacts/`

The local state store does not cover:

- GitHub issue mutation
- pull request mutation
- approvals, merges, or issue closure
- dashboard storage
- autonomous routing or queue consumers
- background daemons or watchers

## Storage Layers

### PostgreSQL

PostgreSQL is the operational store for structured local state.

The initial runnable schema includes:

- `projects`
- `agents`
- `models`
- `queues`
- `work_items`
- `prompts`
- `prompt_runs`
- `evidence_packages`
- `documentation_state`
- `approvals`
- `audit_events`
- `schema_migrations`

`schema_migrations` is maintained by the local migration runner so applied migrations are tracked in the database.

### Local Artifact Files

Human-reviewable prompt, evidence, and Codex handoff artifacts are written to:

- `artifacts/prompts/generated/`
- `artifacts/evidence/generated/`
- `artifacts/codex_handoffs/generated/`

Each generated artifact writes:

- one Markdown file for review
- one JSON sidecar file for structured reuse

### Environment Configuration

Operator configuration is environment-driven through `.env.example` values and the `AppConfig` loader in `src/aresforge/config.py`.

No secrets are committed. The default sample values are local-only development defaults.

## Initial Schema Overview

### Projects

Stores managed-project records for local runtime use. Issue #81 bootstraps AresForge itself as the first local project row.

### Agents

Stores bounded agent-role rows. The initial bootstrap inserts a conservative M2 reference set that includes:

- Planning / Next-Issue Agent
- Triage / Routing Agent
- Worker Agent
- Verification Agent
- Testing Agent
- Debug Routing Agent
- Documentation Agent
- Final Closeout / Lifecycle Controller Agent
- Local Operator

These rows are seed/reference data only during M2. They support inspection and future schema alignment. They do not create queue consumers, background workers, autonomous routing, or autonomous execution.

### Models

Stores local model configuration metadata. The initial bootstrap inserts one default Ollama-backed model row using the configured base URL and model name.

### Queues

Stores visible routing lanes. The initial bootstrap seeds a small set of practical lanes:

- intake
- planning
- implementation
- verification
- documentation

### Work Items

Stores local units of work with queue, optional agent, optional model, optional prompt package, route status, and JSON metadata.

### Prompts And Prompt Runs

`prompts` stores prompt package metadata and artifact locations.

`prompt_runs` is reserved for future recorded executions. Issue #81 creates the table now so later work can attach local run history without another disruptive first migration.

### Evidence Packages

Stores local evidence metadata and points back to the generated local artifact files.

### Documentation State

Stores coarse freshness/review state for documentation paths when later issues start recording documentation review state in a structured way.

### Approvals

Stores approval requests and statuses as local records only. This does not grant approval authority and does not connect to GitHub approval actions.

### Audit Events

Stores append-only local audit rows for local CLI actions like bootstrap and work-item creation.

## Migration Process

Migrations are plain SQL files stored in `migrations/`.

Current commands:

- `python -m aresforge migrate --plan`
- `python -m aresforge migrate`

`migrate`:

- creates `schema_migrations` if missing
- applies pending SQL files in order
- records applied versions
- bootstraps the local reference project, default queues, local operator agent, and configured default Ollama model

## Design Boundaries

The local state store is intentionally conservative.

It does not:

- infer approval authority from database rows
- push to GitHub
- merge PRs
- close issues
- alter repository settings
- alter branch protection or rulesets
- trigger autonomous Codex runs
- trigger autonomous Ollama planning loops

Human-triggered local commands are allowed. Autonomous state-changing behavior remains blocked.
