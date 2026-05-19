# AresForge Agent Context

## Purpose

This file gives AI agents the minimum operating context needed to work safely inside the AresForge repository.

## Operating Model

Agents must treat documentation as the source of truth.

Every implementation should update relevant context, roadmap, architecture, governance, or prompt documentation before the work is considered complete.

Documentation agents are responsible for detecting documentation impact from changed files, issue requirements, PR summaries, validation evidence, existing context docs, and changelog or release notes when available.

During M2 documentation-agent foundation work, documentation agent work remains manual and human-reviewed. Agents may update docs and report stale documentation warnings, but they must not enable automation, workflows, auto-merge, autonomous approval, autonomous issue closure, or overwrite intentional human decisions.

Documentation updates must preserve historical context and include validation evidence for PR review.

Codex implementation agents must follow docs/prompts/CODEX_PROMPT_STANDARD.md as the required implementation-agent handoff format when performing repository implementation work.

Future QA, Test, Documentation, and PR Scoring agents must use docs/governance/PR_VALIDATION_MODEL.md when evaluating implementation pull requests, producing review evidence, or recommending merge-readiness states.

## M1 Baseline Context

M1 GitHub operations validation was reconciled through Issue #41.

Future agents should treat `docs/validation/GITHUB_CAPABILITY_VALIDATION.md`, `.agent/skills/github-operations/SKILL.md`, `.agent/skills/build-state-update/SKILL.md`, and `docs/learning/ERROR_PATTERNS.md` as the baseline for manual GitHub operations until a later human-approved governance change explicitly authorizes automation.

The M1 baseline confirms enough manual, human-reviewed GitHub operations to proceed to M2, while preserving known limitations around GitHub Projects v2 `read:project` access, absent workflow runs and artifacts, absent branch protection and rulesets, and production release governance.

M2 began with Issue #43, `Create documentation agent foundation`, focused on documentation agent rules, source-of-truth update flow, documentation freshness checks, and human-reviewed documentation updates before any autonomous automation. Issue #45, `Create documentation freshness check model`, defines the repeatable freshness check layer that must run before documentation-sync work. Issue #47, `Define local operator workflow`, completed the local operator workflow as a design-only documentation layer for reducing manual copy/paste while preserving human-reviewed controls. Issue #51, `Define documentation-sync evidence package model`, completed the required PR evidence, closeout evidence, and documentation-sync evidence package structure for review artifacts. Issue #55, `Define documentation-sync handoff package template`, completed the reusable documentation-sync handoff package template for carrying documentation-sync evidence between implementation agents, documentation agents, validation agents, local operators, and human owners. Issue #59, `Define Codex prompt package template`, defines the reusable Codex prompt package template as documentation-only review/input scaffolding for implementation-agent handoffs.

## M2 Documentation Agent Foundation Rules

Issue #49 completed the M2 source-of-truth context reconciliation after Issue #47 closeout. Issue #57 completed the M2 source-of-truth reconciliation after Issue #55 and PR #56 closeout. After Issue #57 and PR #58 closeout, no active M2 implementation issue is currently assigned until the next deliverable is chosen.

Future agents must treat `docs/agents/DOCUMENTATION_AGENTS.md` as the canonical documentation agent architecture document. The prior observed missing path `docs/architecture/DOCUMENTATION_AGENTS.md` should not be treated as canonical unless a future source-of-truth change explicitly moves the document.

Future agents must treat `docs/agents/DOCUMENTATION_FRESHNESS_CHECKS.md` as the canonical M2 documentation freshness check model. Documentation-sync work must perform the freshness check before updating docs, classify stale, missing, conflicting, incomplete, or outdated documentation, record evidence, and escalate unresolved uncertainty to the human owner.

Future agents must treat `docs/architecture/LOCAL_OPERATOR_WORKFLOW.md` as the canonical local operator workflow model. During M2, the local operator workflow is a design target only. It may describe future prompt packages, evidence packages, approval gates, and command names, but it does not implement scripts, runnable automation, workflows, autonomous repository behavior, auto-merge, autonomous approval, or autonomous issue closure.

Future agents must treat `docs/agents/DOCUMENTATION_SYNC_EVIDENCE_PACKAGES.md` as the canonical M2 documentation-sync evidence package model. Evidence packages must include source documents reviewed, touched documents, freshness-check evidence, diff and validation summaries, human-review notes, limitation and exception notes, handoff notes, issue and PR references, and an explicit non-authority statement. Evidence packages are review artifacts only and do not approve, merge, close, automate, bypass review, or replace human controls.

Future agents must treat `docs/agents/DOCUMENTATION_SYNC_HANDOFF_TEMPLATE.md` as the reusable M2 documentation-sync handoff package template. The template is the copy/paste-friendly structure for transferring documentation-sync evidence between implementation agents, documentation agents, validation agents, local operators, and human owners. It remains documentation-only, advisory, manually prepared, and human-reviewed.

Future agents must treat `docs/prompts/CODEX_PROMPT_PACKAGE_TEMPLATE.md` as the reusable M2 Codex prompt package template. Prompt packages organize task context, repository and branch context, source-of-truth reading lists, issue and PR context, scope, implementation requirements, freshness checks, documentation impact, validation commands, PR evidence expectations, human-review boundaries, completion guidance, and a non-authority statement. During M2, prompt packages are review/input artifacts only; they do not approve, merge, close, automate, bypass human review, change repository settings, implement `New-CodexPromptPackage`, or authorize future automation.

M2 documentation-agent work must define and preserve:

- Documentation agent responsibilities.
- Source-of-truth update flow.
- Documentation impact detection rules.
- Documentation freshness checks.
- Documentation-sync evidence packages.
- Documentation-sync handoff package templates.
- Codex prompt package templates.
- Human-reviewed documentation update expectations.
- Required validation evidence for documentation changes.
- Handoffs between implementation agents, documentation agents, validation agents, and the human owner.
- Local operator workflow expectations that package issue context, freshness check inputs, documentation-sync inputs, validation checklists, and PR evidence for human review.

The M2 foundation does not introduce autonomous documentation automation. Documentation agents, repo-owned skills, and validation agents remain advisory, manually executed, and human-reviewed until a future human-approved governance change explicitly authorizes a different execution model.

## Reusable Skill Model

AresForge will use repo-owned markdown skill definitions as the canonical reusable agent skills model.

The skill model is defined in docs/agents/AGENT_SKILLS_MODEL.md. The initial draft skill registry is stored at .agent/AGENT_REGISTRY.md with draft skill files under .agent/skills/. During M2 foundation work, skills remain advisory, manually guided, human-reviewed project assets. External skill frameworks may inform future adapters, but they are not required to operate AresForge.

Agents should consult docs/learning/ERROR_PATTERNS.md before generating or repeating GitHub CLI, Windows PowerShell, encoding-sensitive, or operational state update commands that match known failure patterns. During M2 foundation work, the learning document remains advisory project memory only and does not enable automation.

## Current Agent Roles

Initial planned agent roles include:

- Intake Agent
- Product Analyst Agent
- Architecture Agent
- Planning Agent
- Frontend Agent
- Backend Agent
- DevOps Agent
- Automation Agent
- QA Agent
- Test Agent
- Documentation Agent
- Monitoring Agent
- PR Scoring Agent
- Release Agent
- Escalation Agent

## Current Human Role

The human owner acts as CEO and final escalation authority.

The system should reduce human involvement to key decisions, approvals, risk exceptions, and product direction.
