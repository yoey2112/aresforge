# AresForge Roadmap

## Purpose

This roadmap is the source-of-truth sequencing document for AresForge.

It guides milestone planning, future issue creation, documentation updates, and the order in which AresForge should expand from a self-bootstrapping repository into a local-first, document-driven AI project orchestration system.

The roadmap records what is complete, what is active, what is planned, what remains design-only, and what is not yet authorized.

## Roadmap Operating Rules

- Documentation-first and documentation-before-closeout rules apply to roadmap-changing and project-state-changing work.
- Future project-state-changing issues must update source-of-truth docs before PR merge and issue closeout.
- At minimum, future project-state-changing issues must review and update when needed:
  - `docs/context/BUILD_STATE.md`
  - `docs/context/AGENT_CONTEXT.md`
  - `docs/roadmap/ROADMAP.md`
- If one of those three source-of-truth docs does not require changes for a future project-state-changing issue, the PR evidence or closeout evidence must explicitly explain why.
- Human-reviewed controls remain mandatory. No autonomous approval, merge, closure, or repo-changing automation is allowed unless a later human-approved issue explicitly authorizes it.
- Reconciliation-only issues are exception paths, not the normal lifecycle.
- Separate reconciliation issues should only be created when stale, conflicting, or incomplete source-of-truth documentation is discovered after closeout.
- `docs/planning/FUTURE_FEATURE_IDEAS.md` must be reviewed at the start of each milestone.
- `docs/architecture/ISSUE_LIFECYCLE_AGENT_PIPELINE.md` is the canonical lifecycle correction for documentation-before-closeout.
- `docs/architecture/LOCAL_OPERATOR_WORKFLOW.md` is a design-only workflow model during M2 unless a later issue explicitly implements part of it.
- Issue #39, `validation: issue-38-state-lifecycle`, must remain intentionally open protected M1 validation audit evidence unless a future human-directed issue explicitly changes its state.

## Current Milestone Summary

### M0 - Self-Bootstrap Foundation

Status: Completed.

M0 established the repository, baseline docs, self-project context, first milestone and issue structure, GitHub and Ollama validation planning, and the first implementation and PR review standards.

### M1 - GitHub Operations Validation

Status: Completed enough to proceed to M2.

M1 validated manual, human-reviewed GitHub operations across issue, PR, label, milestone, release/tag, workflow/artifact, branch/ruleset, and issue-state areas. Known limitations remain intentionally documented, especially for GitHub Projects v2 access, absent workflow/artifact data, absent branch protection/rulesets, and production release governance.

### M2 - Documentation Automation / Runnable Local Foundation

Status: Active.

M2 began as documentation-only and design-first, but Issue #81 pivoted it into a runnable local foundation. M2 now includes the documentation agent operating model, freshness checks, evidence packages, handoff templates, prompt package templates, PR and closeout evidence templates, the issue lifecycle pipeline, the documentation-before-closeout gate, the local operator workflow model, the first human-triggered runnable local operator skeleton, and the first canonical agent-registry schema.

Current corrective closeout outcome:

- Issue #75: Reconcile source-of-truth after issue 73 closeout, completed and closed through PR #76.

Current completed M2 design deliverable:

- Issue #77: Define project, agent, model, and queue registry architecture, completed and closed through PR #78.
- `docs/architecture/REGISTRY_AND_QUEUE_ARCHITECTURE.md` remains the completed canonical M2 registry and queue architecture deliverable.

Current completed M2 design deliverable:

- Issue #79: Define project registry schema, completed and closed through PR #80.
- `docs/architecture/PROJECT_REGISTRY_SCHEMA.md` is the canonical M2 project registry schema artifact.

Current completed M2 implementation pivot:

- Issue #81: Build runnable local skeleton and automation foundation, completed through PR #82.
- The Issue #81 runnable implementation is documented by:
  - `docs/architecture/LOCAL_STATE_STORE.md`
  - `docs/architecture/RUNNABLE_SKELETON.md`
  - `docs/operator/LOCAL_OPERATOR_USAGE.md`

Current completed M2 registry deliverable:

- Issue #83: Define agent registry schema and lifecycle states, completed.
- `docs/architecture/AGENT_REGISTRY_SCHEMA.md` is the canonical M2 agent registry schema artifact.

Current completed M2 registry deliverable:

- Issue #85: Define model registry and local LLM routing rules, completed through PR #86.
- `docs/architecture/MODEL_REGISTRY_SCHEMA.md` is the canonical M2 model registry and bounded local routing artifact.

Current completed M2 registry deliverable:

- Issue #87: Define queue registry and work-item state transitions, completed.
- `docs/architecture/QUEUE_REGISTRY_SCHEMA.md` is the canonical M2 queue registry and work-item state-transition artifact.

Current M2 corrective rule:

- Issue #75 exists only because stale source-of-truth documentation was discovered after Issue #73 / PR #74 closeout.
- Issue #75 should be the last routine reconciliation issue.
- Separate related source-of-truth documentation update issues should not be created by default because that recreates the reconciliation loop.

Next substantive M2 direction:

- Align later local queue seed data and work-item runtime fields with the canonical queue registry without expanding into hosted model use or autonomous GitHub control.
- Extend the local operator with richer registry-aware inspection now that queue and work-item state meaning is formalized.

## Full Milestone Roadmap

### M0 - Self-Bootstrap Foundation

Status: Completed.

Goal:

Create the AresForge repository and immediately define AresForge as its own first managed project.

Completed scope:

- Repository creation under `yoey2112/aresforge`
- Local clone under `C:\Projects\aresforge`
- Baseline document-driven structure
- Initial self-project context docs
- Initial milestone and issue structure
- GitHub capability validation plan
- Ollama review validation plan
- Documentation agent model
- Self-management context
- Future dashboard state framing
- Codex prompt standard
- PR validation and scoring standard

### M1 - GitHub Operations Validation

Status: Completed enough to proceed to M2.

Goal:

Prove AresForge can safely perform manual, human-reviewed GitHub operations and record durable validation evidence.

Completed scope:

- Manual GitHub operation validation
- Issue lifecycle validation
- Pull request lifecycle validation
- Label lifecycle validation
- Milestone lifecycle validation
- Release and tag lifecycle validation
- Workflow and artifact read validation
- Branch protection and ruleset read validation
- Issue evidence and issue-state validation
- Durable error-pattern capture for fragile command paths

Known limitations retained:

- GitHub Projects v2 remains limited by current token access
- Workflow and artifact validation remains limited by absent workflow data
- Branch protection and ruleset validation remains read-only and reflects current repo state
- Production release governance is not yet authorized

### M2 - Documentation Automation / Runnable Local Foundation

Status: Active.

Goal:

Establish the documentation-first operating model and the first practical local runtime foundation that must exist before any broader AresForge automation is considered.

Completed and active scope:

- Documentation agent model
- Documentation freshness checks
- Documentation-sync evidence packages
- Documentation-sync handoff templates
- Codex prompt package template
- PR evidence package template
- Closeout evidence package template
- Issue lifecycle pipeline
- Documentation-before-closeout gate
- Local operator workflow design
- Project registry schema design completed via Issue #79 and merged PR #80
- Registry and queue architecture design completed via Issue #77 and merged PR #78
- Runnable local operator skeleton completed via Issue #81 and merged PR #82
- Agent registry schema completed via Issue #83
- Canonical agent registry schema artifact at `docs/architecture/AGENT_REGISTRY_SCHEMA.md`
- Model registry and bounded local routing completed via Issue #85 and merged PR #86
- Canonical model registry artifact at `docs/architecture/MODEL_REGISTRY_SCHEMA.md`
- Queue registry and work-item state-transition schema completed via Issue #87
- Canonical queue registry artifact at `docs/architecture/QUEUE_REGISTRY_SCHEMA.md`
- PostgreSQL local state-store foundation
- Repo-stored SQL migrations
- Human-reviewable prompt/evidence/Codex handoff artifact generation
- Minimal Ollama adapter and dry-run check
- M2 reconciliation history through Issues #49, #57, #67, #69, #71, and closed Issue #75 via PR #76

Current M2 boundary:

- Human-triggered local runtime implementation is now allowed where Issue #81 explicitly implements it
- Human-triggered read-only agent-registry seed/listing support is allowed where Issue #83 explicitly implements it
- Human-triggered local model inspection, local Ollama checks, and advisory routing guidance are allowed where Issues #81 and #85 describe them
- Human-reviewed controls remain mandatory
- No autonomous GitHub-state-changing behavior or hosted external model traffic is authorized during current M2 work

Next substantive M2 direction:

- Next likely issue: align the seeded local queue set and work-item runtime interpretation with the canonical queue schema where human-directed implementation scope allows it
- Follow with richer registry-aware local operator inspection now that queue and work-item state meaning is in place

### M3 - Registry and Routing Deepening

Status: Planned. Design target only.

Goal:

Expand the documentation-defined registry architecture and the new runnable skeleton into more specific schemas, routing rules, and deeper implementation planning that let AresForge understand what work exists, who can do it, and how execution should be sequenced under human control.

Planned scope:

- Project registry
- Agent registry expansion
- Model registry
- Queue registry
- Capability registry
- Skill registry alignment
- Routing rules
- Work item state model
- Human approval boundary model

Completed foundation now available to this milestone:

- Project registry canonical schema
- Agent registry canonical schema
- Model registry canonical schema
- Queue registry and work-item state-transition canonical schema

Not yet implemented:

- Intelligent routing automation
- Autonomous registry mutation
- Autonomous issue dispatch
- Rich registry storage beyond the initial local skeleton
- Queue execution workers
- Full model routing runtime

### M4 - Local Operator Expansion

Status: Planned. Implementation target after design work.

Goal:

Expand the human-triggered local operator layer from the Issue #81 runnable skeleton into a broader helper surface for implementation context, evidence, and safe workflows without enabling autonomous repository-changing behavior.

Planned scope:

- More complete local commands
- Safer command wrappers
- Richer prompt package generation
- Richer evidence package generation
- Worktree validation helpers
- Read-only GitHub inspection helpers

Boundary:

- No autonomous repo-changing behavior unless separately approved later

### M5 - Documentation Sync MVP

Status: Planned. Implementation target after M2 models and M4 helpers are mature enough.

Goal:

Create a human-triggered documentation-sync flow that makes source-of-truth upkeep more repeatable without turning it into autonomous closeout behavior.

Planned scope:

- Human-triggered documentation sync flow
- Freshness-check execution
- Source-of-truth update suggestions
- Evidence capture
- Closeout package preparation
- Documentation drift warnings

Boundary:

- Still human-reviewed
- Not autonomous documentation closure

### M6 - Agent Queue and Orchestration MVP

Status: Planned. Design and implementation target after registry definitions exist.

Goal:

Introduce visible queue and handoff structures that let AresForge route work between lifecycle roles without hiding human approvals.

Planned scope:

- Queue definitions
- Agent handoff states
- Routing between planning, worker, verification, testing, documentation, and closeout roles
- Failure loop routing
- Queue visibility
- Human intervention checkpoints

Boundary:

- Queue orchestration must preserve the lifecycle gates in `docs/architecture/ISSUE_LIFECYCLE_AGENT_PIPELINE.md`

### M7 - Dashboard MVP

Status: Planned. Future implementation target.

Goal:

Build a local dashboard or web UI that makes AresForge project memory and work state visible without replacing source-of-truth documentation prematurely.

Planned scope:

- Local dashboard or web UI
- GitHub issue and PR visibility
- Project state view
- Documentation freshness state
- Queue state
- Agent state
- Evidence package visibility
- Manual action prompts

Boundary:

- Dashboard visibility does not authorize autonomous control by itself

### M8 - Multi-Project Support

Status: Planned. Future expansion target.

Goal:

Expand AresForge beyond self-management so it can manage additional projects with per-project context, rules, and review boundaries.

Planned scope:

- Manage projects beyond AresForge itself
- Per-project context packs
- Per-project registries
- Per-project rules and autonomy levels
- Project onboarding workflow
- Cross-project visibility

Boundary:

- Multi-project support must preserve per-project human authority and source-of-truth clarity

### M9 - Model Routing and Local LLM Integration

Status: Planned. Future design and implementation target.

Goal:

Extend the M2 model-registry schema into richer local routing, evaluation, and possibly later approved external-provider support for planning, implementation support, validation, and evidence review.

Planned scope:

- Ollama and local model registry deepening beyond the Issue #81 adapter and Issue #85 schema
- Model capability profiles
- Task-to-model routing rules
- Cost, privacy, and performance routing
- Validation model selection
- Optional external model adapters if explicitly approved

Boundary:

- Model routing remains subject to governance, evidence quality, and human approval rules

### M10 - Controlled Automation Layer

Status: Planned. Future governance-sensitive target.

Goal:

Introduce carefully bounded automation only after the necessary registries, evidence, queue, and approval systems are mature enough to support safe human-supervised operation.

Planned scope:

- Human-approved automation only
- Safe automation boundaries
- Dry-run-first operations
- Approval gates
- Audit logs
- Rollback and recovery expectations

Boundary:

- No destructive automation without explicit governance and validation

### M11 - Release and Governance System

Status: Planned. Future governance and release target.

Goal:

Define how AresForge should plan releases, track versioned readiness, and evolve governance after the core orchestration model is stable enough to support it.

Planned scope:

- Release planning
- Versioning
- Governance reviews
- Production-readiness gates
- Branch protection and ruleset strategy if approved
- Release evidence packages

Boundary:

- Release governance must not be implied before explicit human approval

### M12 - Self-Managed Delivery Loop

Status: Planned. Long-term target.

Goal:

Allow AresForge to plan, route, validate, document, and prepare work with configurable autonomy while preserving human authority and durable auditability.

Planned scope:

- AresForge manages its own backlog and documentation lifecycle under approved controls
- Agent recommendations become increasingly packaged and repeatable
- Planning, routing, validation, documentation, and closeout become more structured and less copy/paste-driven
- Human remains final authority

Boundary:

- Self-management does not remove human authority
- Any autonomy increase must remain explicitly governed and reversible

## Cross-Cutting Project Capabilities

These capabilities span multiple milestones and should be treated as long-term program threads rather than single-issue deliverables.

- Documentation source-of-truth: repository docs remain the authoritative project memory until a later dashboard state is explicitly promoted.
- Evidence packages: PR, closeout, and documentation-sync evidence remain required review artifacts.
- Agent roles: planning, worker, verification, testing, documentation, closeout, and future specialist roles must remain explicitly bounded.
- Repo-owned skills: markdown skills remain the reusable guidance layer until future governance approves a different execution model.
- Local-first execution: AresForge is designed to run primarily from local tools, local docs, local branches, and local validation.
- GitHub integration: GitHub remains a key state and workflow surface, but not the only future control surface.
- Model routing: future model selection must account for capability, privacy, cost, and validation needs.
- Queue orchestration: queue and routing concepts must preserve lifecycle gates and human approvals.
- Dashboard visibility: future dashboards should expose project state, queue state, agent state, and evidence state without weakening source-of-truth rigor.
- Human approvals: human review remains mandatory for approval, merge, closeout, and governance-sensitive actions unless later explicitly changed.
- Auditability: validation evidence, freshness findings, issue history, and closeout reasoning must remain reviewable.
- Multi-project support: future expansion beyond AresForge itself must preserve per-project context, rules, and visibility.

## Explicit Non-Goals For Current Phase

The current M2 phase does not authorize the following:

- No autonomous GitHub-state-changing automation in M2 unless a later issue explicitly authorizes it.
- No autonomous merge.
- No autonomous issue closure.
- No autonomous approval.
- No repo settings changes.
- No branch protection or ruleset changes.
- No secrets changes.
- No workflow implementation.
- No release or tag changes.
- No GitHub Project changes.

## Next Recommended Issues

These are roadmap-driven recommendations only. They are not created issues.

- Define queue registry and work item state transitions.
- Extend the local operator with richer registry-aware inspection after queue and work-item state meaning is formalized.

## Maintenance Rules

- `docs/roadmap/ROADMAP.md` must be reviewed at milestone start.
- `docs/roadmap/ROADMAP.md` must be updated before closeout for roadmap-changing issues.
- `docs/planning/FUTURE_FEATURE_IDEAS.md` must be reviewed at milestone start.
- Completed issue references should be preserved but not rewritten unnecessarily.
- Active and next wording must not be left stale after closeout.
- Roadmap wording must clearly distinguish current capability, planned capability, design-only targets, and not-yet-authorized behavior.
- Future milestones should stay specific enough to guide issue creation without implying that implementation already exists.
