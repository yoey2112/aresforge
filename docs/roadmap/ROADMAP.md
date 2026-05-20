# AresForge Roadmap

## Purpose

This roadmap is the compact source-of-truth sequencing document for AresForge. It explains what is complete, what is active, what is planned next, and what remains out of scope.

Detailed completed M0-M2 history now lives in `docs/history/M0_M2_COMPLETED_WORK_SUMMARY.md`.

## Roadmap Operating Rules

- Documentation-before-closeout applies to roadmap-changing and project-state-changing work
- Future project-state-changing issues must review and update `docs/context/BUILD_STATE.md`, `docs/context/AGENT_CONTEXT.md`, and `docs/roadmap/ROADMAP.md` before PR merge and issue closeout when needed
- If one of those source-of-truth docs does not change, PR evidence or closeout evidence must explain why
- Human-reviewed controls remain mandatory
- Issue #75 remains the last routine reconciliation issue
- Separate reconciliation or related source-of-truth update issues are exception paths only when stale wording is discovered after closeout
- `docs/architecture/ISSUE_LIFECYCLE_AGENT_PIPELINE.md` remains the canonical lifecycle correction for documentation-before-closeout
- `docs/planning/FUTURE_FEATURE_IDEAS.md` must be reviewed at the start of each milestone
- Issue #39, `validation: issue-38-state-lifecycle`, is retired and closed by explicit human direction and is now historical validation evidence only

## Current Milestone Summary

### M0 - Self-Bootstrap Foundation

Status: Completed.

M0 established the repository, baseline docs, self-project framing, the first issue and milestone structure, the prompt and PR-review standards, and the initial documentation-driven operating model.

### M1 - GitHub Operations Validation

Status: Completed enough to proceed to M2.

M1 validated manual, human-reviewed GitHub operations across issue, PR, label, milestone, release/tag, workflow/artifact, branch/ruleset, and issue-state areas. Known limitations remain documented for GitHub Projects v2 access, absent workflow data, absent branch protection or rulesets, and production release governance.

### M2 - Documentation And Runnable Local Foundation

Status: Completed.

M2 established the documentation agent model, freshness checks, evidence templates, lifecycle pipeline, documentation-before-closeout gate, registry architecture, registry schemas, runnable local skeleton, and the first bounded local operator foundation.

PR #94 completed Issue #92 and Issue #93 and made `validate-registries`, `inspect-queue --write-artifact`, and `inspect-work-item --write-artifact` merged `main` behavior through commit `1f7b5fd`. Commit `42b02dd` then corrected stale source-of-truth wording on `main` after PR #94 closeout without creating a new routine reconciliation issue.

PR #96 completed Issue #95 and extended the M2 operator foundation with a human-triggered, local-only, read-only `list-models` command that emits deterministic JSON from seeded local model records without calling Ollama or introducing routing behavior.

PR #102 completed Issue #101 and extended the merged `main` M2 operator foundation with a human-triggered, local-only, read-only `inspect-model` command that reads a single local model row plus existing seeded registry metadata and expands approval, task-class, fallback, and source-document posture into deterministic JSON without selecting a model, recommending a model, routing work, or calling Ollama.

PR #98 completed Issue #97 and extended the merged `main` M2 operator foundation with a human-triggered, local-only, read-only `inspect-project` command that reads only from the local `projects` table, expands stored project metadata into visible JSON fields, and returns explicit found or `project_not_found` results without introducing routing, automation, or GitHub-state-changing behavior.

PR #100 completed Issue #99 and extended the merged `main` M2 operator foundation with a human-triggered PowerShell PR lifecycle helper that keeps validation, staging, commit and push, PR creation, PR verification, merge execution, post-merge verification, and source-of-truth scanning explicit and phase-gated rather than autonomous or hidden.

PR #104 completed Issue #103 and extended the merged `main` M2 operator foundation with a human-triggered, local-only, read-only `inspect-registries` command that summarizes repo-owned project, agent, model, queue, and work-item lifecycle source documents plus existing seeded registry validation surfaces into deterministic JSON without calling the network, mutating files, or changing queue, routing, or GitHub state.

PR #106 completed Issue #105 and extended the merged `main` M2 operator foundation with a human-triggered, local-only, read-only `list-artifacts` command that summarizes generated artifacts under the configured artifact root into deterministic JSON without creating missing directories, connecting to PostgreSQL, calling Ollama, mutating files, or changing queue, routing, or GitHub state.

PR #108 completed Issue #107 and extended the merged `main` M2 operator foundation with a human-triggered, local-only, read-only `inspect-artifact` command that inspects exactly one generated artifact under the configured artifact root, rejects unsafe or out-of-root paths, and emits deterministic JSON with bounded preview metadata for safe text artifacts.

PR #111 completed Issue #109 and extended the merged `main` M2 operator foundation with human-triggered, local-only, read-only `list-evidence-packages` and `inspect-evidence-package` commands plus opt-in local artifact discovery capture during `record-evidence-package`. These additions remain deterministic, auditable, and non-authoritative.

PR #113 completed Issue #110 and extended the merged `main` M2 operator foundation with human-triggered `run-local-review` orchestration plus opt-in local review package generation. These additions remain local-only, deterministic, auditable, and non-authoritative.

PR #115 completed Issue #112 and extended the merged `main` M2 operator foundation with read-only `list-review-packages` and `inspect-review-package` visibility plus opt-in latest local review package capture during evidence and Codex handoff preparation. These additions remain local-only, deterministic, auditable, and non-authoritative.

Issue #114 added the canonical model-routing and LLM escalation strategy documentation as a docs-only architecture artifact in `docs/architecture/MODEL_ROUTING_STRATEGY.md`. This document defines the local-first principle, the four-tier escalation ladder, task routing guidance, cost and privacy guardrails, and Codex usage warnings without introducing runtime behavior or autonomous model selection.

Issue #117 adds decision-only ready-issue routing via `plan-ready-issue`, providing deterministic agent and model tier recommendations without mutating GitHub state.

Issue #118 adds validation-only QA PR inspection via `qa-review-pr`, providing deterministic pass/fail/blocked output without mutating GitHub state.

Issue #119 was completed through PR #125 and adds QA-gated PR closeout via `qa-closeout-pr`, with default dry-run/no-mutation behavior and execute-mode mutation limited to the target PR and linked non-protected issue only after all QA and required-label gates pass.

Issue #120 adds reusable ready issue orchestration via `run-ready-issue-pipeline`, with explicit plan-only, review-pr, and closeout-when-eligible modes that compose existing intake, planning, QA review, and QA-gated closeout behaviors while preserving non-mutating defaults.

Issue #127 adds reusable read-only batch ready issue planning via `run-ready-issue-batch --plan-only` plus read-only `automation-readiness-report`, including deterministic local JSON and Markdown batch artifacts and optional local-only selected issue handoff package generation for Copilot or Codex selected issues.

### M3 - Registry And Routing Deepening

Status: Completed.

M3 starts with local-first, read-only project-state visibility and milestone-aware operator guidance while preserving non-mutating defaults and explicit human review gates.

Issue #129 adds `project-state-summary`, a local-first read-only command that summarizes branch status, local-versus-origin commit posture where available, open GitHub issues and PRs where available, source-of-truth docs, latest generated artifacts, current milestone direction, and recommended next action with graceful degradation when `git`, `gh`, `origin/main`, or network access is unavailable.

Issue #131 adds `inspect-repo-governance`, a reusable read-only command that inspects configured repository slug and default branch posture where available, evaluates platform-required and platform-optional labels, evaluates automation-trigger labels, checks canonical platform milestone naming, and summarizes issue and PR readiness signals with explicit warnings and recommended next action when `gh` or network access is unavailable.

Issue #132 adds `inspect-repo-bootstrap-contract` and `docs/architecture/MANAGED_REPOSITORY_BOOTSTRAP_CONTRACT.md`, defining reusable required, recommended, optional, and deferred setup areas for managed repositories and providing deterministic read-only bootstrap readiness evaluation before any setup mutation.

Issue #133 adds `inspect-managed-repos` and `docs/architecture/MANAGED_REPOSITORY_REGISTRY.md`, extending M3 with a minimal read-only managed repository registry model that always includes AresForge as the first/default managed repository while supporting additional registered repositories.

Issue #134 adds `managed-repo-readiness-report`, extending M3 with read-only per-repository readiness classification (`ready`, `attention_needed`, `degraded`, `unavailable`, `disabled`, `archived`) for registered managed repositories while preserving deterministic output and graceful degradation.

Issue #135 adds `plan-repo-bootstrap`, extending M3 with deterministic read-only bootstrap planning for managed repositories that identifies required, recommended, optional, and deferred setup actions without performing setup mutation.

Issue #136 adds `demo-managed-repo-governance`, extending M3 with a deterministic read-only end-to-end managed repository governance demo that composes governance inspection, bootstrap contract evaluation, managed repository registry representation, readiness reporting, and bootstrap planning in one safe proof flow without setup mutation.

Issue #138 reconciles source-of-truth documentation after completion of Issues #131 through #136 so roadmap, context, operator usage, and architecture documents remain mutually consistent without introducing new mutation behavior.

### M4 - Local Operator Expansion

Status: Implementation complete; parent closeout in progress.

Issue #145 is the parent sprint issue for M4.

Issue #146 was completed through PR #150 and reconciles source-of-truth and operator/governance documentation after human-triggered bootstrap setup confirmed required and optional platform labels plus canonical platform milestones.

Issue #146 records explicit legacy/project-specific milestone mapping guidance:

- `M0 - Self-Bootstrap Foundation` maps to `M0 - Foundation`
- `M1 - GitHub Operations Validation` maps to `M1 - Validation`
- `M2 - Documentation Automation` maps to `M2 - Local Automation Foundation`
- `validation: issue-26-milestone-lifecycle` maps to `M1 - Validation`

Issue #146 is docs-only posture reconciliation and does not implement setup mutation commands.

Issue #147 was completed through PR #153 and expands managed repository governance fixture coverage to a second fixture/demo managed repository while preserving read-only and human-gated mutation boundaries.

Issue #148 was completed through PR #151 and hardens `qa-review-pr` validation evidence detection so explicit PR-body validation sections are recognized with strict heading plus command/check plus pass/result requirements and deterministic failure diagnostics.

Issue #149 was completed through PR #152 and adds `validate-pr-end-to-end`, a deterministic read-only end-to-end PR validation orchestration command that composes `qa-review-pr` output plus operator validation-command guidance without GitHub mutation.

All M4 implementation workstreams are complete:

- #146 / PR #150 completed
- #147 / PR #153 completed
- #148 / PR #151 completed
- #149 / PR #152 completed

Remaining open M4 issue:

- Issue #145 (parent sprint closeout)

## Planned Milestone Sequence

### M5 - Local Operator Quality And Safe Onboarding Contracts

Focus on local operator execution quality, managed-repository onboarding design, and preparation of safe human-triggered setup and mutation contracts without enabling autonomous GitHub mutation.

### M6 - Agent Queue And Orchestration MVP

Introduce visible queue and handoff structures that let AresForge represent lifecycle movement without hiding approvals or enabling autonomous execution.

### M7 - Dashboard MVP

Add local visibility for project state, queue state, documentation freshness, evidence, and manual action prompts without replacing source-of-truth docs.

### M8 - Multi-Project Support

Extend AresForge beyond self-management with per-project context, rules, and bounded autonomy levels.

### M9 - Model Routing And Local LLM Integration

Deepen bounded local model routing, evaluation, and possible later approved provider adapters while preserving governance and review controls.

### M10 - Controlled Automation Layer

Consider carefully bounded, human-approved automation only after registry, queue, evidence, and approval systems are mature enough to support safe supervision.

### M11 - Release And Governance System

Define release planning, versioning, governance review, and production-readiness controls after the orchestration foundation is mature enough.

### M12 - Self-Managed Delivery Loop

Long-term target: allow AresForge to plan, route, validate, document, and prepare work with configurable autonomy while preserving human authority and reversible controls.

## Cross-Cutting Capabilities

- Documentation source-of-truth and freshness discipline
- Evidence packages and handoff packages
- Bounded lifecycle roles and queue participation
- Repo-owned skills and prompt standards
- Local-first execution
- GitHub integration as a key but not exclusive state surface
- Registry-driven project, agent, model, and queue understanding
- Human approvals, auditability, and protected validation evidence
- Multi-project expansion without weakening per-project control

## Explicit Non-Goals For The Current Phase

The current M4 phase does not authorize:

- autonomous queue transitions
- autonomous routing
- autonomous approval, merge, or issue closure
- autonomous GitHub-state-changing behavior
- repo setting, branch protection, ruleset, secret, workflow, release, tag, or GitHub Project changes
- hidden background workers that change project state
- hosted external model use as default runtime behavior

## Next Recommended Direction

- Merge parent closeout reconciliation for Issue #145 and treat M4 implementation sprint workstreams as complete
- Keep M4 boundary posture explicit: setup and mutation remain human-triggered and gated, with no setup/mutation command surface implemented
- Use M5 to improve local operator execution quality, managed-repo onboarding design, and safe human-triggered setup/mutation contracts without autonomous GitHub mutation
- Extend local operator visibility with safer human-triggered helper commands while keeping queue transitions out of scope and GitHub-state-changing behavior tightly phase-gated
- Continue improving local review-aid visibility, including deterministic summaries of generated artifacts that remain non-authoritative
- Continue improving local review-aid visibility, including deterministic single-artifact inspection that remains non-authoritative
- Continue improving local review-aid visibility, including deterministic evidence package discovery and inspection that remain non-authoritative
- Continue improving local review-aid visibility, including deterministic local review orchestration and optional review package generation that remain human-triggered and non-authoritative
- Continue improving local review-aid visibility, including deterministic review package discovery, single-package inspection, and opt-in handoff or evidence capture that remain human-triggered and non-authoritative
- Keep broader registry-aware operator inspection human-triggered and non-authoritative
- Optionally perform local historical branch cleanup as separate human-directed hygiene work

## Maintenance Rules

- Review this roadmap at milestone start
- Keep milestone wording concise and current rather than issue-by-issue
- Preserve the distinction between completed capability, current capability, planned capability, and out-of-scope capability
- Preserve current governance boundaries and the documentation-before-closeout rule
- Preserve the rule that active source-of-truth docs stay compact while durable historical context lives in `docs/history/M0_M2_COMPLETED_WORK_SUMMARY.md`
