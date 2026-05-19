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

## Reusable Skill Model

AresForge will use repo-owned markdown skill definitions as the canonical reusable agent skills model.

The skill model is defined in docs/agents/AGENT_SKILLS_MODEL.md. The initial draft skill registry is stored at .agent/AGENT_REGISTRY.md with draft skill files under .agent/skills/. During M1, skills are advisory, manually guided, human-reviewed project assets. External skill frameworks may inform future adapters, but they are not required to operate AresForge.

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
