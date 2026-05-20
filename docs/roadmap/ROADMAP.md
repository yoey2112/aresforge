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
- Issue #39, `validation: issue-38-state-lifecycle`, remains intentionally open protected audit evidence unless a future human-directed issue explicitly changes it

## Current Milestone Summary

### M0 - Self-Bootstrap Foundation

Status: Completed.

M0 established the repository, baseline docs, self-project framing, the first issue and milestone structure, the prompt and PR-review standards, and the initial documentation-driven operating model.

### M1 - GitHub Operations Validation

Status: Completed enough to proceed to M2.

M1 validated manual, human-reviewed GitHub operations across issue, PR, label, milestone, release/tag, workflow/artifact, branch/ruleset, and issue-state areas. Known limitations remain documented for GitHub Projects v2 access, absent workflow data, absent branch protection or rulesets, and production release governance.

### M2 - Documentation And Runnable Local Foundation

Status: Active.

M2 established the documentation agent model, freshness checks, evidence templates, lifecycle pipeline, documentation-before-closeout gate, registry architecture, registry schemas, runnable local skeleton, and the first bounded local operator foundation.

PR #94 completed Issue #92 and Issue #93 and made `validate-registries`, `inspect-queue --write-artifact`, and `inspect-work-item --write-artifact` merged `main` behavior through commit `1f7b5fd`. Commit `42b02dd` then corrected stale source-of-truth wording on `main` after PR #94 closeout without creating a new routine reconciliation issue.

Issue #95 extends that M2 operator foundation with a human-triggered, local-only, read-only `list-models` command that emits deterministic JSON from seeded local model records without calling Ollama or introducing routing behavior.

## Planned Milestone Sequence

### M3 - Registry And Routing Deepening

Deepen the registry model and routing vocabulary on top of the current project, agent, model, and queue schema foundation without authorizing autonomous dispatch.

### M4 - Local Operator Expansion

Expand the human-triggered local operator with richer read-only inspection, safer helper commands, and better review artifact support.

### M5 - Documentation Sync MVP

Create a more repeatable, human-triggered documentation-sync flow with freshness checks, source-of-truth suggestions, and evidence capture while keeping closeout human-reviewed.

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

The current M2 phase does not authorize:

- autonomous queue transitions
- autonomous routing
- autonomous approval, merge, or issue closure
- autonomous GitHub-state-changing behavior
- repo setting, branch protection, ruleset, secret, workflow, release, tag, or GitHub Project changes
- hidden background workers that change project state
- hosted external model use as default runtime behavior

## Next Recommended Direction

- Continue the M2 runtime foundation with richer read-only model, project, or registry inspection views
- Extend local operator visibility while keeping queue transitions and GitHub-state-changing behavior out of scope
- Keep broader registry-aware operator inspection human-triggered and non-authoritative
- Optionally perform local historical branch cleanup as separate human-directed hygiene work

## Maintenance Rules

- Review this roadmap at milestone start
- Keep milestone wording concise and current rather than issue-by-issue
- Preserve the distinction between completed capability, current capability, planned capability, and out-of-scope capability
- Preserve current governance boundaries and the documentation-before-closeout rule
- Preserve the rule that active source-of-truth docs stay compact while durable historical context lives in `docs/history/M0_M2_COMPLETED_WORK_SUMMARY.md`
