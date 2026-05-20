# AresForge Agent Context

## Purpose

This file gives agents the minimum current operating context needed to work safely in AresForge without re-reading long closeout history.

Detailed historical background for completed M0-M2 work lives in `docs/history/M0_M2_COMPLETED_WORK_SUMMARY.md`.

## Operating Model

Agents must treat repository documentation as the source of truth for project meaning, governance, milestone state, lifecycle rules, and autonomy boundaries.

During M3, implementation remains human-triggered and human-reviewed. Agents may help with documentation, code, migrations, local operator tooling, and evidence preparation, but they must not imply that current M3 foundations authorize autonomous control.

## Required Source-Of-Truth Behavior

- Review `docs/context/BUILD_STATE.md`, `docs/context/AGENT_CONTEXT.md`, and `docs/roadmap/ROADMAP.md` for project-state-changing work
- Update those source-of-truth docs before PR merge and issue closeout when the project state changes
- If one of those docs does not need an update, explain why in PR evidence or closeout evidence
- Preserve historical accuracy without leaving active docs cluttered with stale issue-by-issue detail
- Treat Issue #75 as the last routine reconciliation issue
- Do not create separate documentation-update or reconciliation issues by default; use that path only if stale source-of-truth wording is discovered after closeout

## Current M3 Rules

- Documentation-before-closeout is mandatory for project-state-changing work
- The Documentation Agent remains a required pre-closeout gate
- Human-reviewed controls remain mandatory
- Evidence packages, prompt packages, handoff packages, PR evidence, and closeout evidence remain review artifacts only
- Current local runtime foundations are local-first, human-triggered, read-only where possible, and non-authoritative
- Issue #92 and Issue #93 are completed through PR #94 and are merged `main` behavior
- The docs-only correction at commit `42b02dd` fixed stale post-closeout wording on `main` without creating a new routine reconciliation issue
- Issue #103 was completed through PR #104 and added merged `main` support for read-only local registry inspection across project, agent, model, queue, and work-item lifecycle surfaces without introducing routing, queue mutation, file mutation, network calls, or GitHub-state-changing behavior
- Issue #107 was completed through PR #108 and added merged `main` support for read-only single-artifact inspection without introducing file mutation, routing, queue mutation, network calls, or GitHub-state-changing behavior
- Issue #109 was completed through PR #111 and added merged `main` support for read-only evidence package discovery, read-only single evidence-package inspection, and opt-in artifact discovery capture during evidence package recording without introducing routing, queue mutation, network calls, or GitHub-state-changing behavior
- Issue #110 was completed through PR #113 and added merged `main` support for human-triggered `run-local-review` orchestration plus opt-in local review package generation without introducing routing, queue mutation, network calls, or GitHub-state-changing behavior
- Issue #112 was completed through PR #115 and added merged `main` support for read-only `list-review-packages` and `inspect-review-package` visibility plus opt-in latest local review package capture during evidence and Codex handoff preparation without introducing routing, queue mutation, network calls, or GitHub-state-changing behavior
- Issue #114 added the canonical model-routing and LLM escalation strategy documentation as a docs-only architecture artifact in `docs/architecture/MODEL_ROUTING_STRATEGY.md`
- Issue #118 was completed through PR #124 and added merged `main` support for deterministic QA PR validation-only inspection via `qa-review-pr`
- Issue #119 was completed through PR #125 and added merged `main` support for `qa-closeout-pr` with default dry-run/no-mutation behavior plus explicit execute gating
- Issue #120 is merged `main` behavior and provides `run-ready-issue-pipeline` orchestration with explicit mode boundaries
- Issue #127 is merged `main` behavior and provides read-only `run-ready-issue-batch --plan-only` plus `automation-readiness-report` command surfaces
- Issue #129 starts M3 and adds a local-first read-only `project-state-summary` command surface with graceful degradation when local tools or network access are unavailable
- Issue #101 was completed through PR #102 and added merged `main` support for read-only local model inspection without introducing model selection, routing, or GitHub-state-changing behavior
- Issue #97 was completed through PR #98 and added merged `main` support for read-only local project inspection without changing routing, queue state, or GitHub state
- Issue #99 was completed through PR #100 and added merged `main` support for a human-triggered PR lifecycle helper that keeps validation, staging, PR creation, PR verification, merge execution, post-merge verification, and source-of-truth scanning phase-gated and visible

## Canonical Documents Agents Must Consult

Agents should use these documents as the current M3 canon:

- `docs/agents/DOCUMENTATION_AGENTS.md`
- `docs/agents/DOCUMENTATION_FRESHNESS_CHECKS.md`
- `docs/architecture/ISSUE_LIFECYCLE_AGENT_PIPELINE.md`
- `docs/architecture/REGISTRY_AND_QUEUE_ARCHITECTURE.md`
- `docs/architecture/PROJECT_REGISTRY_SCHEMA.md`
- `docs/architecture/AGENT_REGISTRY_SCHEMA.md`
- `docs/architecture/MODEL_REGISTRY_SCHEMA.md`
- `docs/architecture/MODEL_ROUTING_STRATEGY.md`
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
- deterministic read-only local model inspection
- deterministic read-only local registry and lifecycle source inspection from repo-owned schema documents
- read-only queue and work-item inspection
- read-only inspection report artifact generation
- deterministic read-only generated artifact discovery
- deterministic read-only single-artifact inspection
- deterministic read-only local review package discovery
- deterministic read-only single local review package inspection
- deterministic read-only evidence package discovery
- deterministic read-only single evidence package inspection
- deterministic human-triggered local review orchestration across existing local operator checks
- deterministic decision-only ready issue routing for automation intake
- deterministic QA PR validation-only inspection via `qa-review-pr`
- deterministic QA-gated PR closeout via `qa-closeout-pr` with default dry-run/no-mutation and explicit execute mode
- deterministic reusable ready issue orchestration via `run-ready-issue-pipeline` with explicit plan-only, review-pr, and closeout-when-eligible modes
- deterministic reusable read-only ready issue batch planning via `run-ready-issue-batch --plan-only`, including deterministic JSON and Markdown batch artifacts under `artifacts/ready_issue_batches/generated/`
- deterministic read-only automation readiness dashboard reporting via `automation-readiness-report`
- deterministic local-first read-only project state reporting via `project-state-summary`
- a human-triggered PR lifecycle helper that requires an explicit phase selection before validation, staging, PR creation, PR verification, merge execution, post-merge verification, or source-of-truth scanning
- prompt, evidence, and Codex handoff artifact preparation, including opt-in local artifact discovery capture in evidence packages plus opt-in latest local review package capture in evidence and handoff outputs
- opt-in local review package generation under `artifacts/local_reviews/generated/`
- bounded local Ollama connectivity or dry-run checks
- bounded local model inspection visibility from seeded local model records
- advisory, reviewable local model-selection support where the canonical model registry allows it

PR #94 makes `validate-registries`, `inspect-queue --write-artifact`, and `inspect-work-item --write-artifact` merged `main` behavior. These remain local-only, human-triggered, read-only, and non-authoritative.

## Current Prohibited And Autonomy Boundaries

The current M3 foundation does not authorize:

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

Issue #39, `validation: issue-38-state-lifecycle`, is retired and closed by explicit human direction. It should be treated as historical validation evidence only, not as an active protected open issue.
