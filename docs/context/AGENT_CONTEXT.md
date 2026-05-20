# AresForge Agent Context

## Purpose

This file gives agents the minimum current operating context needed to work safely in AresForge without re-reading long closeout history.

Detailed historical background for completed M0-M2 work lives in `docs/history/M0_M2_COMPLETED_WORK_SUMMARY.md`.

## Operating Model

Agents must treat repository documentation as the source of truth for project meaning, governance, milestone state, lifecycle rules, and autonomy boundaries.

During M2, implementation remains human-triggered and human-reviewed. Agents may help with documentation, code, migrations, local operator tooling, and evidence preparation, but they must not imply that current M2 foundations authorize autonomous control.

## Required Source-Of-Truth Behavior

- Review `docs/context/BUILD_STATE.md`, `docs/context/AGENT_CONTEXT.md`, and `docs/roadmap/ROADMAP.md` for project-state-changing work
- Update those source-of-truth docs before PR merge and issue closeout when the project state changes
- If one of those docs does not need an update, explain why in PR evidence or closeout evidence
- Preserve historical accuracy without leaving active docs cluttered with stale issue-by-issue detail
- Treat Issue #75 as the last routine reconciliation issue
- Do not create separate documentation-update or reconciliation issues by default; use that path only if stale source-of-truth wording is discovered after closeout

## Current M2 Rules

- Documentation-before-closeout is mandatory for project-state-changing work
- The Documentation Agent remains a required pre-closeout gate
- Human-reviewed controls remain mandatory
- Evidence packages, prompt packages, handoff packages, PR evidence, and closeout evidence remain review artifacts only
- Current local runtime foundations are local-first, human-triggered, read-only where possible, and non-authoritative
- Issue #92 and Issue #93 are completed through PR #94 and are merged `main` behavior
- The docs-only correction at commit `42b02dd` fixed stale post-closeout wording on `main` without creating a new routine reconciliation issue
- Issue #97 was completed through PR #98 and added merged `main` support for read-only local project inspection without changing routing, queue state, or GitHub state
- Issue #99 is the active working-branch implementation for a human-triggered PR lifecycle helper that keeps validation, staging, PR creation, PR verification, merge execution, post-merge verification, and source-of-truth scanning phase-gated and visible

## Canonical Documents Agents Must Consult

Agents should use these documents as the current M2 canon:

- `docs/agents/DOCUMENTATION_AGENTS.md`
- `docs/agents/DOCUMENTATION_FRESHNESS_CHECKS.md`
- `docs/architecture/ISSUE_LIFECYCLE_AGENT_PIPELINE.md`
- `docs/architecture/REGISTRY_AND_QUEUE_ARCHITECTURE.md`
- `docs/architecture/PROJECT_REGISTRY_SCHEMA.md`
- `docs/architecture/AGENT_REGISTRY_SCHEMA.md`
- `docs/architecture/MODEL_REGISTRY_SCHEMA.md`
- `docs/architecture/QUEUE_REGISTRY_SCHEMA.md`
- `docs/architecture/LOCAL_STATE_STORE.md`
- `docs/architecture/RUNNABLE_SKELETON.md`
- `docs/operator/LOCAL_OPERATOR_USAGE.md`
- `docs/agents/DOCUMENTATION_SYNC_EVIDENCE_PACKAGES.md`
- `docs/agents/DOCUMENTATION_SYNC_HANDOFF_TEMPLATE.md`
- `docs/prompts/CODEX_PROMPT_PACKAGE_TEMPLATE.md`
- `docs/agents/PR_EVIDENCE_PACKAGE_TEMPLATE.md`
- `docs/agents/CLOSEOUT_EVIDENCE_PACKAGE_TEMPLATE.md`
- `docs/governance/PR_VALIDATION_MODEL.md`
- `docs/learning/ERROR_PATTERNS.md`
- `docs/planning/FUTURE_FEATURE_IDEAS.md`

## Current Agent Roles

The current lifecycle and operator roles are:

- Planning / Next-Issue Agent
- Triage / Routing Agent
- Worker Agent
- Verification Agent
- Testing Agent
- Debug Routing Agent
- Documentation Agent
- Final Closeout / Lifecycle Controller Agent
- Local Operator

## Human Owner Role

The human owner remains CEO, final escalation authority, and the final approver for governance-sensitive decisions, closeout posture, and any future autonomy expansion.

## Current Allowed Local-Operator Behaviors

The local operator may currently support:

- config and registry validation
- local database migrations
- local state inspection
- read-only local project inspection from the `projects` table
- deterministic read-only local model listing
- read-only queue and work-item inspection
- read-only inspection report artifact generation
- a human-triggered PR lifecycle helper that requires an explicit phase selection before validation, staging, PR creation, PR verification, merge execution, post-merge verification, or source-of-truth scanning
- prompt, evidence, and Codex handoff artifact preparation
- bounded local Ollama connectivity or dry-run checks
- advisory, reviewable local model-selection support where the canonical model registry allows it

PR #94 makes `validate-registries`, `inspect-queue --write-artifact`, and `inspect-work-item --write-artifact` merged `main` behavior. These remain local-only, human-triggered, read-only, and non-authoritative.

## Current Prohibited And Autonomy Boundaries

The current M2 foundation does not authorize:

- autonomous queue transitions
- autonomous routing or routing mutation
- autonomous model selection for governance-sensitive actions
- autonomous approval, merge, or issue closure
- autonomous GitHub-state-changing behavior
- repo setting, branch protection, ruleset, workflow, secret, release, tag, or GitHub Project changes
- hidden background workers, bots, daemons, or services that change project state
- hidden background PR lifecycle execution
- hosted external model use as default project behavior

## Protected Issue #39 Rule

Issue #39, `validation: issue-38-state-lifecycle`, remains protected audit evidence. Agents must not modify, close, or otherwise change it unless a future human-directed issue explicitly authorizes that work.
