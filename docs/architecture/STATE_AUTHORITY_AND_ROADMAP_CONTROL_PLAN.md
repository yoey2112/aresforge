# State Authority And Roadmap Control Plan

## 1. Purpose of this document

This document controls the next leg of work after the audit and recovery baseline pass.

It exists to prevent drift before AresForge implements roadmap control, task tracking, state authority, or agent execution. It is the control document for this paused implementation leg and is intended to be safe for future chat handoff, Codex handoff, Copilot review, AresForge AI agent context, and human architectural decision review.

This document should be read together with the current audit and recovery baseline set:

- `docs/audit/ARESFORGE_RECOVERY_BASELINE.md`
- `docs/audit/CURRENT_STATE_REVIEW.md`
- `docs/audit/COMPLETION_PLAN_DRAFT.md`
- `docs/audit/PROJECT_STANDARDIZATION_PLAN.md`
- `docs/audit/GAP_REGISTER_DRAFT.md`
- `docs/audit/ARCHITECTURE_DOMAIN_MAP.md`
- `docs/audit/ASSESSMENT_SUMMARY.md`
- `docs/architecture/SYSTEM_OVERVIEW.md`
- `docs/context/BUILD_STATE.md`
- `docs/roadmap/ROADMAP.md`

Until the decisions in this document are approved and translated into schema, commands, and runtime controls, documentation and planning remain the only approved work in this area.

## 2. Current agreed baseline

AresForge is currently strong as a local-first planning, governance, audit, and evidence platform.

It is not yet a complete runtime software factory.

The audit baseline already establishes the following as true:

- local assessment, reporting, artifact generation, and governance surfaces are real and test-backed
- database connectivity, migrations, repository primitives, and hub foundations exist
- planning, queue, milestone, review, and handoff surfaces are broad and useful
- significant orchestration, execution, routing, and mutation surfaces remain plan-only, simulation-heavy, or aspirational

Plan-only modules, contract-heavy modules, simulation layers, and roadmap-only surfaces must not be treated as implemented runtime. This applies even when a module name, CLI surface, dashboard surface, or document suggests a more complete lifecycle than the repository has yet proven.

Any future implementation or review in this area must preserve the recovery-baseline rule that documented intent is not runtime proof.

## 3. Product direction

AresForge should become a local-first AI software factory and project operating system that can manage multiple projects end-to-end.

The intended control flow is:

Project registry -> active project -> roadmap areas -> milestones -> tasks -> queue -> agent runs -> validation -> documentation -> human approval -> completion

The product direction is portfolio-aware, not single-repository-only. AresForge should eventually manage AresForge itself and other managed projects through the same structured operating model, with local-first execution, auditable state transitions, and human gates for risk-bearing actions.

## 4. State authority decision

The proposed source-of-truth hierarchy for review is:

- Postgres = authoritative live structured state
- Markdown = generated and reviewed human-readable project knowledge
- JSON = portable snapshots, handoff packages, offline evidence, and recovery artifacts
- Git = version history for docs, schema migrations, generated baselines, and source changes

This is the proposed architectural decision for review. It is not yet fully implemented.

This means AresForge should move away from any long-term assumption that roadmap and control state can remain authoritative as Markdown-only files. Markdown remains important, but should not be the sole durable authority for reusable roadmap, milestone, task, dependency, queue, validation, or completion state once Postgres-backed control is available.

## 5. Why Postgres should own roadmap and control state

Roadmap, milestones, tasks, dependencies, project standards, decision logs, gap registers, validation runs, agent runs, and completion tracking are relational and reusable across many managed projects.

Those domains need more than file storage. They need stable identifiers, history, joins, cross-project inspection, and deterministic transition rules.

Postgres is the right proposed authority for this layer because it enables:

- portfolio queries across all managed projects
- cross-project reporting and hub dashboards
- dependency tracking across tasks and milestones
- progress calculation at task, milestone, roadmap-area, project, and portfolio levels
- blocked-work views and next-action recommendation logic
- event logging and replayable transition history
- reusable validation and approval gate modeling
- consistent lifecycle handling for both AresForge and managed projects

If AresForge is intended to become a real project operating system, roadmap and control state must be queryable, constrained, and reusable across a portfolio. Postgres is the proposed mechanism for that authoritative structured layer.

## 6. Why Markdown still matters

Markdown remains essential for humans and coding agents.

Markdown documents are not being discarded. They become generated, reviewed, and committed views from structured state where possible, plus curated explanatory documents where narrative context is required.

Markdown remains the best medium for:

- architecture explanation
- operator guidance
- human review
- coding-agent context
- change rationale
- governance and approval review
- repository-native documentation history

Important examples of Markdown views or managed knowledge artifacts include:

- `docs/roadmap/ARESFORGE_MASTER_ROADMAP.md`
- `docs/CURRENT_STATE.md`
- `docs/GAP_REGISTER.md`
- `docs/DECISION_LOG.md`
- `.agent/AGENT_CONTEXT.md`
- `.agent/QUALITY_GATES.md`
- `.agent/APPROVAL_GATES.md`

Some of these documents may be generated from structured state and then reviewed before commit. Others may remain hybrid, where structured fields are generated but explanatory context is maintained by humans. The key control rule is that Markdown should remain important, but should no longer be assumed to be the long-term sole authority for roadmap or control state.

## 7. Why JSON artifacts still matter

JSON remains useful for:

- offline audit snapshots
- handoff packages
- debugging
- recovery
- Codex prompt context
- portable state exchange
- local dry runs

JSON is an excellent transport and evidence format. It is compact, machine-readable, portable, and useful for reproducing a planning or validation snapshot outside the live control plane.

However, JSON should not become the long-term primary state authority for roadmap, task, and project control if Postgres is available. JSON snapshots should usually be emitted from authoritative structured state or from controlled exports of that state, not used as the primary live control ledger.

## 8. Proposed domain model

The following first-pass logical entities define the intended structured control model. This section is descriptive only. It does not authorize migrations or implementation yet.

| Entity | Purpose | Likely owner / source of truth | Relationship to other entities | Preferred storage / view model |
| --- | --- | --- | --- | --- |
| `projects` | Canonical managed-project identity and lifecycle container | Postgres authoritative row per managed project | Parent for repositories, roadmap areas, standards, decisions, gaps, validations, agents, and docs | Postgres authority, Markdown summaries, JSON snapshots |
| `project_repositories` | Repositories attached to a managed project, including local and optional external metadata | Postgres authoritative, with local inspection-derived fields | Belongs to `projects`; feeds documentation artifacts and later sync planning | Postgres authority, Markdown views, JSON exports |
| `roadmap_areas` | High-level product or delivery tracks within a project | Postgres authoritative | Belongs to `projects`; parents milestones; drives progress rollups | Postgres authority, generated roadmap Markdown, JSON snapshots |
| `roadmap_milestones` | Time- or outcome-bounded delivery checkpoints inside roadmap areas | Postgres authoritative | Belongs to `roadmap_areas`; parents tasks; aggregates status and progress | Postgres authority, generated roadmap Markdown, JSON snapshots |
| `roadmap_tasks` | Actionable scoped units of work with status, ownership, and acceptance criteria | Postgres authoritative | Belongs to milestones; links to dependencies, queue items, validations, docs, approvals, and agent assignments | Postgres authority, generated task views, JSON handoff/export |
| `roadmap_task_dependencies` | Explicit dependency edges between tasks | Postgres authoritative | Connects `roadmap_tasks` to other `roadmap_tasks`; supports blocked-work views | Postgres authority, generated reports, JSON export |
| `roadmap_events` | Append-only state transition and activity history for roadmap entities | Postgres authoritative event log | References areas, milestones, tasks, queue items, approvals, validations, and generated docs | Postgres authority, JSON audit export, Markdown summaries |
| `project_standards` | Required operating standards for a managed project | Postgres authoritative, seeded from approved standardization rules | Belongs to `projects`; evaluated by standard checks; referenced by docs and approvals | Postgres authority, generated Markdown operating package, JSON snapshots |
| `project_standard_checks` | Verification records showing whether project standards are satisfied | Postgres authoritative run/check results | References `project_standards`, projects, validation commands, and documentation artifacts | Postgres authority, Markdown status views, JSON evidence |
| `decision_log_entries` | Structured architectural, process, or product decisions | Postgres authoritative structured record with Markdown rendering | Belongs to `projects`; may reference milestones, tasks, standards, and gaps | Postgres authority, generated/reviewed `docs/DECISION_LOG.md`, JSON export |
| `gap_register_entries` | Structured tracking of known gaps, risks, or deficiencies | Postgres authoritative structured record with Markdown rendering | Belongs to `projects`; references tasks, milestones, validations, and decisions | Postgres authority, generated/reviewed `docs/GAP_REGISTER.md`, JSON export |
| `validation_commands` | Declared commands and policies used to verify work | Postgres authoritative registry, likely seeded from project package definitions | Belongs to `projects`; referenced by tasks, validations, standards, and approvals | Postgres authority, Markdown ops docs, JSON export |
| `validation_runs` | Execution records for validation commands and outcomes | Postgres authoritative run history | References `validation_commands`, tasks, milestones, agent runs, and docs | Postgres authority, JSON evidence bundles, Markdown summaries |
| `agent_profiles` | Structured definitions of allowed agent roles, boundaries, and expected outputs | Postgres authoritative planned registry once execution is resumed | Belongs to `projects`; referenced by assignments and operating package docs | Postgres authority, generated `.agent/` Markdown, JSON snapshot |
| `agent_assignments` | Mapping of work to agent profiles under approval and scheduling rules | Postgres authoritative planned scheduling data | References tasks, queue items, and `agent_profiles`; produces run candidates | Postgres authority, dashboard views, JSON planning export |
| `agent_run_records` | Durable records of actual or simulated agent runs and outcomes | Postgres authoritative when execution is approved | References assignments, tasks, validations, docs, evidence, and approvals | Postgres authority, JSON evidence, Markdown summaries |
| `documentation_artifacts` | Structured registry of generated or maintained docs tied to work and state | Postgres authoritative metadata with Markdown files as reviewed views | References projects, roadmap entities, validations, decisions, and gaps | Postgres metadata authority, Markdown files, JSON export |

Working interpretation:

- Postgres should own the structured lifecycle state for these entities.
- Markdown should present reviewed human-readable projections and context.
- JSON should capture portable snapshots and evidence exports.
- Git should preserve change history across schema, docs, and source.

## 9. Roadmap hierarchy

The planned hierarchy is:

Portfolio
  -> Project
    -> Roadmap area
      -> Milestone
        -> Task
          -> Work item / agent run / validation evidence / documentation update

High-level roadmap sections should break down into roadmap areas. Each roadmap area should contain milestones that describe meaningful delivery stages. Each milestone should decompose into tasks with explicit acceptance criteria, dependencies, status, and implementation-state labels. Each task may then produce one or more concrete work items, agent runs, validation records, and documentation updates.

This hierarchy is intended to support both planning and execution, while keeping audit evidence and human approval attached to the same structured lineage.

## 10. Status model

Initial lifecycle statuses for roadmap areas, milestones, and tasks:

- `not_started`
- `planned`
- `ready`
- `in_progress`
- `blocked`
- `needs_review`
- `completed`
- `deferred`
- `cancelled`

Additional implementation-state labels required to avoid future drift:

- `implemented`
- `plan_only`
- `aspirational`
- `stale`
- `verified`

These labels serve different purposes:

- lifecycle status describes where a roadmap entity is in its active flow
- implementation-state labels describe how trustworthy the implementation claim is

Both are required. Without implementation-state labels, AresForge risks repeating the current documentation/runtime drift problem where planned capability is read as delivered capability.

## 11. Automatic update model

Desired future behavior after a task is completed:

- validation evidence is recorded
- task status changes
- roadmap progress recalculates
- milestone progress recalculates
- generated docs update or are flagged stale
- follow-up tasks may be added
- next recommended work is recalculated
- human approval is required where gates apply

This should be implemented in phases.

It must not begin as uncontrolled autonomous behavior. Status recalculation, document generation, follow-up creation, validation recording, and recommendation logic must be introduced behind deterministic rules, explicit approvals, and auditable event logging. No autonomous execution or mutation should be assumed from this planning document alone.

## 12. Managed-project standardization connection

This roadmap and state model applies not only to AresForge itself, but to every AresForge-managed project.

Each managed project should receive a generated and verified operating package based on `docs/audit/PROJECT_STANDARDIZATION_PLAN.md`, including:

- required docs
- agent context files
- AI-agent rules
- architecture docs
- task and queue structure
- validation commands
- decision log
- gap register
- project-specific agent profiles
- LLM routing notes
- source-of-truth rules

The structured state model should supply the data needed to generate, validate, and keep that package current. Standardization is therefore not a documentation side concern. It is part of the operating model for every managed project in the portfolio.

## 13. State authority matrix draft

| Entity | Authoritative source | Generated views | Portable artifacts | Notes |
| --- | --- | --- | --- | --- |
| project registry | Postgres | Hub dashboards, project summary docs | JSON registry exports | Replaces long-term file-only registry authority |
| repositories | Postgres | project repo inventory docs, hub views | JSON exports | Local inspection can enrich records but should not outrank DB authority |
| active project | Postgres | hub active-project views, operator summaries | JSON session/export snapshots | Selection state may have transient local cache, but canonical active-project record should live in DB |
| roadmap areas | Postgres | roadmap docs, hub portfolio views | JSON roadmap exports | Rolls up milestone and task state |
| milestones | Postgres | roadmap docs, progress dashboards | JSON roadmap exports | Structured parent under roadmap area |
| tasks | Postgres | task lists, roadmap docs, queue views | JSON handoff and export packages | Primary unit of scoped delivery control |
| task dependencies | Postgres | blocked-work reports, dependency graphs | JSON export | Needed for reliable blocked and ready calculations |
| task events | Postgres | activity logs, milestone summaries | JSON audit bundles | Append-only event history preferred |
| queue items | Postgres | queue dashboard, work-ready reports | JSON run-planning exports | May be derived from tasks plus assignment and readiness rules |
| agent profiles | Postgres | `.agent/` docs, hub agent views | JSON profile snapshots | Planned authority once agent execution work resumes |
| agent runs | Postgres | run summaries, closeout docs | JSON evidence bundles | Not authorized for implementation in this phase |
| validation commands | Postgres | `docs/OPERATIONS.md`, quality gate docs | JSON config export | Managed-project standard package input |
| validation runs | Postgres | validation summaries, dashboard views | JSON evidence bundles | Supports completion and approval gates |
| decision log | Postgres | reviewed `docs/DECISION_LOG.md` | JSON audit export | Structured entries can render to Markdown |
| gap register | Postgres | reviewed `docs/GAP_REGISTER.md` | JSON audit export | Structured gaps should support severity and owner queries |
| project standards | Postgres | operating package docs, compliance dashboards | JSON package export | Derived from approved standardization rules |
| documentation artifacts | Postgres metadata plus Markdown files | Markdown docs, hub doc-status views | JSON artifact indexes | Markdown content remains important; DB tracks structured metadata |
| audit snapshots | Generated from Postgres plus repo inspection | audit Markdown reports | JSON snapshots | Snapshots are evidence, not live authority |
| handoff packages | Generated from Postgres plus selected docs and evidence | handoff Markdown summaries | JSON handoff packages | Portable artifact, not primary control ledger |
| GitHub sync plans | Postgres once reintroduced, for planning only | operator review docs | JSON mutation-plan bundles | Remains deferred and non-executing in this phase |
| external mutation records | Postgres when and if mutation is approved | audit and approval docs | JSON mutation logs | Deferred until later mutation gate approval |

This matrix is a draft pending approval. It is sufficient for planning and schema design, but not yet a license to implement behavior.

## 14. Immediate freeze rules

Until this state authority model is approved:

- do not implement roadmap control as file-only long-term state
- do not implement agent execution
- do not implement multi-LLM routing
- do not reintroduce GitHub mutation or sync execution
- do not treat docs as proof of runtime capability
- allow documentation, schema design, and planning only

These freeze rules are direct continuations of the recovery baseline and remain binding for this leg of work.

## 15. Recommended next milestones

The next milestones after this document are:

1. M1. Approve state authority and roadmap control model
2. M2. Design Postgres schema and migrations for project, roadmap, and task control
3. M3. Implement read-only DB-backed roadmap inspection
4. M4. Implement roadmap mutation commands with event logging
5. M5. Generate Markdown and JSON roadmap views from Postgres
6. M6. Connect Hub dashboard to DB-backed roadmap state
7. M7. Add managed-project standardization verifier
8. M8. Only then resume local agent execution MVP planning

This sequence is intentionally conservative. Schema and read-only inspection should land before mutation commands, generated views, dashboard coupling, or any discussion of resumed execution implementation.

## 16. Acceptance criteria for this leg

This leg is complete when:

- this document exists
- it references the recovery and audit baseline
- it clearly chooses Postgres as the proposed structured authority
- it preserves Markdown and JSON roles
- it defines the draft domain model
- it defines freeze rules
- it defines next milestones
- validation passes

No broader implementation is required for this leg.

## 17. Handoff summary

## 18. M1 schema foundation status note

M1 now includes the first Postgres-backed roadmap control schema foundation via migration `migrations/0004_roadmap_control_schema.sql`, introducing:

- `roadmap_areas`
- `roadmap_milestones`
- `roadmap_tasks`
- `roadmap_task_dependencies`
- `roadmap_events`

Local CLI support was also added for this phase:

- `init-roadmap-schema`
- `seed-aresforge-roadmap`
- `inspect-roadmap-db --format json|markdown`

## 19. M2 roadmap mutation and event logging status note

M2 now adds DB-backed roadmap mutation and event-inspection CLI support while preserving freeze boundaries (no Hub UI mutation work, no agent execution, no LLM routing, no GitHub sync/mutation execution):

- `update-roadmap-task-status --task-id <id> --status <status> [--summary <text>] [--details-json <json>]`
- `update-roadmap-milestone-status --milestone-id <id> --status <status> [--summary <text>] [--details-json <json>]`
- `update-roadmap-area-status --area-id <id> --status <status> [--summary <text>] [--details-json <json>]`
- `add-roadmap-event --event-type <type> --summary <text> [--project-id <id>] [--area-id <id>] [--milestone-id <id>] [--task-id <id>] [--details-json <json>]`
- `inspect-roadmap-events [--project-id <id>] [--limit <n>] [--format json|markdown]`

M2 details metadata input supports either `--details-json` (strict JSON object) or Windows-safe `--details-file` (UTF-8 JSON object file path).

## 20. M3 roadmap-to-work-item bridge status note

M3 adds a local Postgres-backed bridge from roadmap tasks to local work items:

- migration `migrations/0005_roadmap_work_item_bridge.sql` introducing `roadmap_work_item_links`
- `create-work-item-from-roadmap-task` to create/link local work from roadmap tasks with idempotent active-link behavior
- `inspect-roadmap-work-item-links --format json|markdown` for read-only bridge inspection

This milestone remains within current freeze boundaries: no Hub UI mutation implementation, no agent execution, no LLM routing, and no GitHub sync/mutation execution.

## 21. M4 local work item lifecycle status note

M4 adds local CLI lifecycle and inspection surfaces for roadmap-linked work items without introducing execution behavior:

- `update-work-item-status --work-item-id <id> --status <status> [--summary <text>] [--details-json <json>] [--details-file <path>]`
- `inspect-work-item-lifecycle --work-item-id <id> [--format json|markdown]`
- `inspect-queue-work-state [--project-id <id>] [--queue-id <id>] [--format json|markdown]`

M4 updates local `work_items` lifecycle state with strict status validation, logs audit events, and logs related roadmap events when a roadmap task link exists. It does not automatically mutate roadmap task status, does not implement agent execution, and does not add Hub UI mutation flows.

## 22. M5 local readiness gates status note

M5 adds deterministic local readiness gate inspection for local work items and queues without mutating state:

- `inspect-work-item-readiness --work-item-id <id> [--format json|markdown]`
- `inspect-queue-readiness [--project-id <id>] [--queue-id <id>] [--format json|markdown]`

Readiness inspection introduces explicit local readiness statuses (`ready`, `not_ready`, `blocked`, `already_active`, `already_complete`, `cancelled`, `missing`), validates roadmap-link presence for queued work, checks linked roadmap-task cancellation, and checks roadmap dependency completion before start.

## 23. M6 work item start gate status note

M6 adds a local mutation gate for starting queued work items only when M5 readiness allows it:

- `start-work-item --work-item-id <id> [--actor <actor>] [--details-file <path>] [--format json|markdown]`

The command evaluates M5 `inspect_work_item_readiness` first, only transitions `queued -> active` when readiness is `ready`, and remains local-only. It does not execute agents, route LLMs, or call GitHub APIs.

### What was decided

- AresForge should move toward Postgres as the authoritative live structured state layer for roadmap, control, validation, and completion tracking
- Markdown remains required as generated and reviewed human-readable knowledge
- JSON remains required as portable snapshot, handoff, evidence, and recovery format
- Git remains the version history layer for docs, schema, baselines, and source changes
- roadmap control must stop assuming Markdown-only authority

### What is still unresolved

- exact schema design and normalization boundaries
- event model details and conflict-resolution rules
- final queue-item derivation model versus first-class storage shape
- approval policy details for specific mutation classes and human gate roles
- exact generated-view ownership rules for hybrid documents

### What must not be done next

- do not implement roadmap control as file-only long-term state
- do not implement agent execution
- do not implement multi-LLM routing
- do not reintroduce GitHub mutation or sync execution
- do not treat planning docs as implementation proof
- do not start uncontrolled automation from this document alone

### What the next agent should read

- `docs/audit/ARESFORGE_RECOVERY_BASELINE.md`
- `docs/audit/CURRENT_STATE_REVIEW.md`
- `docs/audit/COMPLETION_PLAN_DRAFT.md`
- `docs/audit/PROJECT_STANDARDIZATION_PLAN.md`
- `docs/audit/GAP_REGISTER_DRAFT.md`
- `docs/architecture/SYSTEM_OVERVIEW.md`
- this document

### What the next agent should produce

- a schema-design document for the approved domain model and authority matrix
- a proposed migration plan for moving roadmap and control state into Postgres without losing auditability
- a read-only roadmap inspection design that does not introduce mutation behavior
