# AresForge Agent Context

## Purpose

This file gives AI agents the minimum operating context needed to work safely inside the AresForge repository.

## Operating Model

Agents must treat documentation as the source of truth for project meaning, governance, roadmap state, and automation boundaries.

Every implementation should update relevant context, roadmap, architecture, governance, operator, or prompt documentation before the work is considered complete.

Documentation agents are responsible for detecting documentation impact from changed files, issue requirements, PR summaries, validation evidence, existing context docs, and changelog or release notes when available.

During M2 runnable local skeleton work, documentation and implementation remain human-reviewed. Agents may update docs, code, migrations, and local operator tooling, but they must not enable autonomous GitHub-state-changing behavior, auto-merge, autonomous approval, autonomous issue closure, or overwrite intentional human decisions.

Documentation updates must preserve historical context and include validation evidence for PR review.

Codex implementation agents must follow docs/prompts/CODEX_PROMPT_STANDARD.md as the required implementation-agent handoff format when performing repository implementation work.

Future QA, Test, Documentation, and PR Scoring agents must use docs/governance/PR_VALIDATION_MODEL.md when evaluating implementation pull requests, producing review evidence, or recommending merge-readiness states.

## M1 Baseline Context

M1 GitHub operations validation was reconciled through Issue #41.

Future agents should treat `docs/validation/GITHUB_CAPABILITY_VALIDATION.md`, `.agent/skills/github-operations/SKILL.md`, `.agent/skills/build-state-update/SKILL.md`, and `docs/learning/ERROR_PATTERNS.md` as the baseline for manual GitHub operations until a later human-approved governance change explicitly authorizes automation.

The M1 baseline confirms enough manual, human-reviewed GitHub operations to proceed to M2, while preserving known limitations around GitHub Projects v2 `read:project` access, absent workflow runs and artifacts, absent branch protection and rulesets, and production release governance.

M2 began with Issue #43, `Create documentation agent foundation`, focused on documentation agent rules, source-of-truth update flow, documentation freshness checks, and human-reviewed documentation updates before any autonomous automation. Issue #45, `Create documentation freshness check model`, defines the repeatable freshness check layer that must run before documentation-sync work. Issue #47, `Define local operator workflow`, completed the local operator workflow as a design-only documentation layer for reducing manual copy/paste while preserving human-reviewed controls. Issue #51, `Define documentation-sync evidence package model`, completed the required PR evidence, closeout evidence, and documentation-sync evidence package structure for review artifacts. Issue #55, `Define documentation-sync handoff package template`, completed the reusable documentation-sync handoff package template for carrying documentation-sync evidence between implementation agents, documentation agents, validation agents, local operators, and human owners. Issue #59, `Define Codex prompt package template`, defines the reusable Codex prompt package template as documentation-only review/input scaffolding for implementation-agent handoffs. Issue #63, `Define PR evidence package template`, completed the reusable PR evidence package template as documentation-only review scaffolding for implementation PRs after PR #64 merged successfully, closeout evidence was posted, and Issue #63 was manually closed. Issue #65, `Define closeout evidence package template`, completed the reusable closeout evidence package template as documentation-only review scaffolding after PR #66 merged successfully, closeout evidence was posted, and Issue #65 was manually closed. Issue #77, `Define project, agent, model, and queue registry architecture`, completed through merged PR #78 and now serves as the bridge from the lifecycle foundation to later registry schema, queue, local-first model routing, and multi-project support work. Issue #79, `Define project registry schema`, completed through PR #80. Issue #81, `Build runnable local skeleton and automation foundation`, completed through PR #82 and introduced the practical human-triggered local operator foundation. Issue #83, `Define agent registry schema and lifecycle states`, is completed and remains the canonical agent-role schema layer. Issue #85, `Define model registry and local LLM routing rules`, is completed through merged PR #86 and formalizes bounded local-first model records and routing rules on top of that skeleton. Issue #87, `Define queue registry and work-item state transitions`, is completed and formalizes the canonical queue-record, transition-rule, blocked-handling, corrective-loop, and work-item state schema layer on top of the existing lifecycle and runnable local skeleton.

## M2 Runnable Skeleton Rules

Issue #49 completed the M2 source-of-truth context reconciliation after Issue #47 closeout. Issue #57 completed the M2 source-of-truth reconciliation after Issue #55 and PR #56 closeout. Issue #59 completed the reusable Codex prompt package template after PR #60 closeout. Issue #61 added the future feature ideas planning document after PR #62 closeout. Issue #63 completed the reusable PR evidence package template after PR #64 closeout. Issue #65 completed the reusable closeout evidence package template after PR #66 closeout and manual issue closure. Issue #67 completed the M2 source-of-truth reconciliation after PR #68 merged successfully and the issue was manually closed. Issue #69 completed the M2 source-of-truth reconciliation after PR #70 merged successfully, Issue #69 was manually closed, and `main` advanced to commit `38fa94e`. Issue #71 completed the M2 source-of-truth reconciliation after PR #72 merged successfully, closeout evidence was posted, Issue #71 was manually closed, and `main` advanced to commit `7d21189`. Issue #73 completed the issue lifecycle pipeline and documentation-before-closeout design correction through merged PR #74, and `main` advanced to commit `031c3c4`. Issue #75 completed the corrective reconciliation closeout through merged PR #76, and `main` advanced to commit `e7bb49a`.

Future agents must treat `docs/agents/DOCUMENTATION_AGENTS.md` as the canonical documentation agent architecture document. The prior observed missing path `docs/architecture/DOCUMENTATION_AGENTS.md` should not be treated as canonical unless a future source-of-truth change explicitly moves the document.

Future agents must treat `docs/architecture/ISSUE_LIFECYCLE_AGENT_PIPELINE.md` as the canonical design document for the future issue lifecycle pipeline. During M2, that pipeline remains documentation-only architecture and does not authorize runnable automation, autonomous approval, PR merge, or issue closure behavior.

Future agents must treat `docs/agents/DOCUMENTATION_FRESHNESS_CHECKS.md` as the canonical M2 documentation freshness check model. Documentation-sync work must perform the freshness check before updating docs, classify stale, missing, conflicting, incomplete, or outdated documentation, record evidence, and escalate unresolved uncertainty to the human owner.

Future agents must treat `docs/architecture/LOCAL_OPERATOR_WORKFLOW.md` as the pre-implementation design document and `docs/operator/LOCAL_OPERATOR_USAGE.md` plus `docs/architecture/RUNNABLE_SKELETON.md` as the runnable implementation guidance introduced by Issue #81. The local operator now has real human-triggered commands, but it still does not authorize autonomous repository behavior, auto-merge, autonomous approval, or autonomous issue closure.

Future agents must treat `docs/architecture/REGISTRY_AND_QUEUE_ARCHITECTURE.md` as the canonical registry and queue architecture document. It still defines the main architectural relationships. Issue #81 adds a minimal runnable local state layer that reflects those concepts in PostgreSQL tables and local CLI commands without claiming that the full architecture is complete.

Future agents must treat `docs/architecture/PROJECT_REGISTRY_SCHEMA.md` as the canonical project registry schema design document. Issue #81 uses that schema as input for the first local `projects` table and AresForge bootstrap record, but the document still remains the source for intended meaning and boundaries.

Future agents must treat `docs/architecture/AGENT_REGISTRY_SCHEMA.md` as the canonical agent registry schema design document. Issue #83 formalizes bounded agent-role records, lifecycle states, capability relationships, queue participation expectations, evidence outputs, escalation rules, and local operator integration points. The current local `agents` table remains a conservative seed/reference layer for those records and does not authorize autonomous execution.

Future agents must treat `docs/architecture/MODEL_REGISTRY_SCHEMA.md` as the canonical model registry and local LLM routing document. Issue #85 formalizes model-record meaning, local endpoint conventions, allowed task classes, routing priority, fallback rules, approval posture, and evidence expectations for bounded local-first model selection. The current local `models` table remains a conservative seed/reference layer and does not authorize autonomous routing, hosted model use, or governance-sensitive model selection.

Future agents must treat `docs/architecture/QUEUE_REGISTRY_SCHEMA.md` as the canonical queue registry and work-item state-transition document. Issue #87 formalizes queue identities, queue meaning, queue transitions, blocked and waiting handling, corrective-loop routing, lifecycle-state mapping, evidence requirements, and local operator visibility expectations. The current local `queues` and `work_items` tables remain conservative runtime reference layers even though the seeded local queue set now covers the canonical initial M2 queue IDs.

Future agents must treat `docs/architecture/LOCAL_STATE_STORE.md` as the canonical explanation of the new PostgreSQL-backed local state layer and repo-stored migration process.

Future agents must treat `docs/architecture/RUNNABLE_SKELETON.md` as the canonical explanation of the first runnable vertical slice and its explicit boundaries.

Future agents must treat `docs/agents/DOCUMENTATION_SYNC_EVIDENCE_PACKAGES.md` as the canonical M2 documentation-sync evidence package model. Evidence packages must include source documents reviewed, touched documents, freshness-check evidence, diff and validation summaries, human-review notes, limitation and exception notes, handoff notes, issue and PR references, and an explicit non-authority statement. Evidence packages are review artifacts only and do not approve, merge, close, automate, bypass review, or replace human controls.

Future agents must treat `docs/agents/DOCUMENTATION_SYNC_HANDOFF_TEMPLATE.md` as the reusable M2 documentation-sync handoff package template. The template is the copy/paste-friendly structure for transferring documentation-sync evidence between implementation agents, documentation agents, validation agents, local operators, and human owners. It remains documentation-only, advisory, manually prepared, and human-reviewed.

Future agents must treat `docs/prompts/CODEX_PROMPT_PACKAGE_TEMPLATE.md` as the reusable M2 Codex prompt package template. Issue #81 also introduces a runnable local prompt-package and Codex-handoff generator that writes human-reviewable files under `artifacts/`, but those files remain review/input artifacts only; they do not approve, merge, close, automate, bypass human review, change repository settings, or authorize future automation.

Future agents must treat `docs/agents/PR_EVIDENCE_PACKAGE_TEMPLATE.md` as the reusable M2 PR evidence package template. PR evidence packages organize issue reference, PR reference, branch and commit context, source-of-truth documents reviewed, files changed, scope summary, documentation impact, freshness-check evidence when documentation-sync work is involved, validation results, diff review summary, human-review notes, limitations, protected Issue #39 confirmations, repository-boundary confirmations, and a non-authority statement. During M2, PR evidence packages are review artifacts only; they do not approve, merge, close, automate, bypass human review, replace human controls, change source-of-truth priority, implement `New-PrEvidencePackage`, or authorize future automation.

Future agents must treat docs/agents/CLOSEOUT_EVIDENCE_PACKAGE_TEMPLATE.md as the reusable M2 closeout evidence package template. Closeout evidence packages organize issue references, PR references when applicable, merge or closeout trigger, branch and commit context, source-of-truth documents reviewed, documentation freshness-check evidence, closeout file changes, project-memory updates, roadmap and state updates, validation results, diff review summary, human-review notes, limitations, protected Issue #39 confirmations, repository-boundary confirmations, next-step handoff notes, and a non-authority statement. During M2, closeout evidence packages are review artifacts only; they do not approve, merge, close, automate, bypass human review, replace human controls, change source-of-truth priority, implement New-CloseoutEvidencePackage, or authorize future automation.

Future agents must not treat reconciliation-only issues as the default closeout pattern. Issue #75 should be the last routine reconciliation issue. When an issue changes project state, documentation updates must occur before PR merge and issue closeout. The Documentation Agent is a required pre-closeout gate, and the Final Closeout / Lifecycle Controller Agent closes the issue only after implementation, verification, testing, and documentation gates pass. Separate related source-of-truth documentation update issues should not be created by default because they recreate the reconciliation loop. Separate reconciliation or documentation-update issues should be reserved only for stale, conflicting, or incomplete source-of-truth documentation discovered after closeout.

Issue #81 specifically allows human-triggered local automation such as config validation, database migrations, local state inspection, local artifact generation, and local Ollama dry-run checks. Issue #81 does not authorize autonomous PR merge, autonomous issue closure, autonomous approval, repo-setting changes, branch-protection changes, ruleset changes, secret changes, release or tag changes, or GitHub Project changes.

At minimum, future project-state-changing issues must review and update when needed:

- `docs/context/BUILD_STATE.md`
- `docs/context/AGENT_CONTEXT.md`
- `docs/roadmap/ROADMAP.md`

If one of those three documents does not need an update for a future project-state-changing issue, the PR evidence or closeout evidence must explicitly explain why.

Issue #75 existed only because stale source-of-truth documentation was discovered after Issue #73 / PR #74 closeout. That exception path is preserved for after-closeout stale, conflicting, or incomplete source-of-truth documentation, but it is not the standard future closeout pattern.

M2 documentation-agent work must define and preserve:

- Documentation agent responsibilities.
- Source-of-truth update flow.
- Documentation impact detection rules.
- Documentation freshness checks.
- Documentation-sync evidence packages.
- Documentation-sync handoff package templates.
- Codex prompt package templates.
- PR evidence package templates.
- Closeout evidence package templates.
- Human-reviewed documentation update expectations.
- Required validation evidence for documentation changes.
- Handoffs between implementation agents, documentation agents, validation agents, and the human owner.
- Local operator workflow expectations that package issue context, freshness check inputs, documentation-sync inputs, validation checklists, and PR evidence for human review.

The M2 runnable skeleton still does not introduce autonomous documentation automation or autonomous GitHub control. Documentation agents, repo-owned skills, validation agents, and the new local operator remain bounded, human-triggered, and human-reviewed until a future human-approved governance change explicitly authorizes a different execution model.

Issue #77 is completed and closed through PR #78. Issue #79 is completed through PR #80. Issue #81 is completed through PR #82. Issue #83 is completed and provides the canonical agent-registry schema layer. Issue #85 is completed through PR #86 and advances `main` to `e2bbe85`. Issue #87 is completed and adds the canonical queue-registry and work-item state-transition schema layer. Future agents should use the resulting registry architecture, project-registry schema, runnable local skeleton, agent-registry schema, model-registry schema, and queue-registry schema to shape later queue evolution, model routing, and multi-project work. No related source-of-truth documentation-update issue should be created by default for this kind of project-state-changing work.

## Reusable Skill Model

AresForge will use repo-owned markdown skill definitions as the canonical reusable agent skills model.

The skill model is defined in docs/agents/AGENT_SKILLS_MODEL.md. The initial draft skill registry is stored at .agent/AGENT_REGISTRY.md with draft skill files under .agent/skills/. During M2 foundation work, skills remain advisory, manually guided, human-reviewed project assets. External skill frameworks may inform future adapters, but they are not required to operate AresForge.

Agents should consult docs/learning/ERROR_PATTERNS.md before generating or repeating GitHub CLI, Windows PowerShell, encoding-sensitive, or operational state update commands that match known failure patterns. During M2 foundation work, the learning document remains advisory project memory only and does not enable automation.

## Current Agent Roles

Current canonical lifecycle and operator roles are:

- Planning / Next-Issue Agent
- Triage / Routing Agent
- Worker Agent
- Verification Agent
- Testing Agent
- Debug Routing Agent
- Documentation Agent
- Final Closeout / Lifecycle Controller Agent
- Local Operator

## Current Human Role

The human owner acts as CEO and final escalation authority.

The system should reduce human involvement to key decisions, approvals, risk exceptions, and product direction.
