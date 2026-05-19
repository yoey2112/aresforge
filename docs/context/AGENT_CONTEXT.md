# AresForge Agent Context

## Purpose

This file gives AI agents the minimum operating context needed to work safely inside the AresForge repository.

## Operating Model

Agents must treat documentation as the source of truth.

Every implementation should update relevant context, roadmap, architecture, governance, or prompt documentation before the work is considered complete.

Documentation agents are responsible for detecting documentation impact from changed files, issue requirements, PR summaries, validation evidence, existing context docs, and changelog or release notes when available.

During M0 and M1, documentation agent work is manual and human-reviewed. Agents may update docs and report stale documentation warnings, but they must not enable automation, auto-merge, autonomous issue closure, or overwrite intentional human decisions.

Documentation updates must preserve historical context and include validation evidence for PR review.

Codex implementation agents must follow docs/prompts/CODEX_PROMPT_STANDARD.md as the required implementation-agent handoff format when performing repository implementation work.

Future QA, Test, Documentation, and PR Scoring agents must use docs/governance/PR_VALIDATION_MODEL.md when evaluating implementation pull requests, producing review evidence, or recommending merge-readiness states.

## M1 Closeout Context

M1 GitHub operations validation is being closed out through Issue #41.

Future agents should treat `docs/validation/GITHUB_CAPABILITY_VALIDATION.md`, `.agent/skills/github-operations/SKILL.md`, `.agent/skills/build-state-update/SKILL.md`, and `docs/learning/ERROR_PATTERNS.md` as the baseline for manual GitHub operations until a later human-approved governance change explicitly authorizes automation.

The M1 baseline confirms enough manual, human-reviewed GitHub operations to proceed to M2, while preserving known limitations around GitHub Projects v2 `read:project` access, absent workflow runs and artifacts, absent branch protection and rulesets, and production release governance.

M2 should begin with documentation agent foundation work. The first recommended M2 issue is `Create documentation agent foundation`, focused on documentation agent rules, source-of-truth update flow, documentation freshness checks, and human-reviewed documentation updates before any autonomous automation.

## Reusable Skill Model

AresForge will use repo-owned markdown skill definitions as the canonical reusable agent skills model.

The skill model is defined in docs/agents/AGENT_SKILLS_MODEL.md. The initial draft skill registry is stored at .agent/AGENT_REGISTRY.md with draft skill files under .agent/skills/. During M1, skills are advisory, manually guided, human-reviewed project assets. External skill frameworks may inform future adapters, but they are not required to operate AresForge.

Agents should consult docs/learning/ERROR_PATTERNS.md before generating or repeating GitHub CLI, Windows PowerShell, encoding-sensitive, or operational state update commands that match known failure patterns. During M1, the learning document is advisory project memory only and does not enable automation.

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
