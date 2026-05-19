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

### M2 - Documentation Automation / Documentation Agent Foundation

Status: Active.

M2 is still documentation-only and design-first. It defines the documentation agent operating model, freshness checks, evidence packages, handoff templates, prompt package templates, PR and closeout evidence templates, the issue lifecycle pipeline, the documentation-before-closeout gate, and the local operator workflow model.

Current active corrective item:

- Issue #75: Reconcile source-of-truth after issue 73 closeout.

Current M2 corrective rule:

- Issue #75 exists only because stale source-of-truth documentation was discovered after Issue #73 / PR #74 closeout.
- Issue #75 should be the last routine reconciliation issue.

Next substantive M2 design direction:

- Define AresForge project, agent, model, and queue registry architecture.

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

### M2 - Documentation Automation / Documentation Agent Foundation

Status: Active.

Goal:

Establish the documentation-first operating model that must exist before any broader AresForge automation is considered.

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
- M2 reconciliation history through Issues #49, #57, #67, #69, #71, and active Issue #75

Current M2 boundary:

- Documentation-only and design-only where implementation has not happened
- Human-reviewed controls remain mandatory
- No runnable automation is authorized during current M2 work

Next substantive M2 design direction:

- Future project, agent, model, and queue registry architecture

### M3 - Registry and Routing Architecture

Status: Planned. Design target only.

Goal:

Define the canonical registries and routing rules that let AresForge understand what work exists, who can do it, and how execution should be sequenced under human control.

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

Not yet implemented:

- Runnable routing automation
- Autonomous registry mutation
- Autonomous issue dispatch

### M4 - Local Operator MVP

Status: Planned. Implementation target after design work.

Goal:

Create a human-triggered local operator layer that prepares implementation context, evidence, and safe helper flows without enabling autonomous repository-changing behavior.

Planned scope:

- Human-triggered local commands
- Safe command wrappers
- Prompt package generation
- Evidence package generation
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

Formalize how AresForge chooses among local and approved external models for planning, implementation support, validation, and evidence review.

Planned scope:

- Ollama and local model registry
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

- No runnable automation in M2 unless a later issue explicitly authorizes it.
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

- Define AresForge project, agent, model, and queue registry architecture.
- Define project registry schema.
- Define agent registry schema and lifecycle states.
- Define model registry and local LLM routing rules.
- Define queue registry and work item state transitions.
- Define local operator command design for registry inspection.

## Maintenance Rules

- `docs/roadmap/ROADMAP.md` must be reviewed at milestone start.
- `docs/roadmap/ROADMAP.md` must be updated before closeout for roadmap-changing issues.
- `docs/planning/FUTURE_FEATURE_IDEAS.md` must be reviewed at milestone start.
- Completed issue references should be preserved but not rewritten unnecessarily.
- Active and next wording must not be left stale after closeout.
- Roadmap wording must clearly distinguish current capability, planned capability, design-only targets, and not-yet-authorized behavior.
- Future milestones should stay specific enough to guide issue creation without implying that implementation already exists.
