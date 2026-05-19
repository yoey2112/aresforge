# Documentation Sync Skill

## Name

Documentation sync

## Purpose

Guide agents in detecting documentation impact and updating the correct AresForge docs as part of scoped implementation work.

Documentation sync must begin with the freshness check model in `docs/agents/DOCUMENTATION_FRESHNESS_CHECKS.md` so agents classify stale, missing, conflicting, incomplete, or outdated project documentation before updating source-of-truth docs.

## When to use

Use this skill when a change affects project context, build state, roadmap sequencing, agent behavior, governance, architecture, prompt standards, validation expectations, or release-facing project memory.

During M2 documentation-agent foundation work, also use this skill to verify documentation impact detection, freshness checks, source-of-truth update flow, validation evidence, and handoff expectations.

## When not to use

Do not use this skill to rewrite unrelated documentation, replace source-of-truth governance docs, overwrite intentional human decisions, or promote future-state ideas into completed functionality.

## Inputs

- Active issue or task requirements.
- Changed files or planned file changes.
- Existing context, agent, governance, roadmap, prompt, architecture, and validation docs.
- Documentation freshness check model from docs/agents/DOCUMENTATION_FRESHNESS_CHECKS.md.
- Documentation-sync evidence package model from docs/agents/DOCUMENTATION_SYNC_EVIDENCE_PACKAGES.md.
- Documentation-sync handoff template from docs/agents/DOCUMENTATION_SYNC_HANDOFF_TEMPLATE.md when a reusable package or next-agent handoff is needed.
- Documentation freshness checks from docs/agents/DOCUMENTATION_AGENTS.md when relevant.
- Local operator workflow package or evidence outline from docs/architecture/LOCAL_OPERATOR_WORKFLOW.md when available.
- Codex prompt package template from docs/prompts/CODEX_PROMPT_PACKAGE_TEMPLATE.md when prompt-package documentation or implementation handoff packaging is in scope.
- Validation evidence and PR summary when available.
- Explicit human decisions relevant to the work.

## Outputs

- Focused documentation edits.
- Documentation impact summary.
- Freshness check findings classified as stale, missing, conflicting, incomplete, outdated build-state or roadmap references, unavailable inputs, or out of scope.
- Stale documentation warnings when a related update is real but out of scope.
- Freshness check summary for source-of-truth docs affected by the issue.
- Documentation-sync evidence package content, including source documents reviewed, touched documents, freshness evidence, diff and validation summary, human-review notes, limitations, handoff notes, issue and PR references, and a non-authority statement.
- Completed handoff template content when the work must be transferred to an implementation agent, documentation agent, validation agent, local operator, or human owner.
- Human-review boundary confirmation.
- Validation evidence for documentation review.

## Scope boundaries

This skill covers documentation impact analysis and scoped documentation updates. It does not authorize unrelated rewrites, broad reorganization, new automation, or changes to project authority boundaries.

## Execution boundaries

This skill is advisory and manually executed. It does not create documentation agents as services, watchers, workflows, scripts, or runnable sync automation.

Local operator workflow support is also design-only during M2. Operator packages may organize documentation-sync inputs, but they do not execute this skill.

Evidence packages prepared through this skill are review artifacts only. They do not approve, merge, close, automate, bypass human review, or authorize future automation.

The documentation-sync handoff template is also a review artifact scaffold only. It does not run this skill, implement local operator commands, or replace human-reviewed PR evidence.

## Human approval boundaries

Human approval is required before changing governance meaning, autonomy levels, approval requirements, source-of-truth priority, roadmap commitments, or historical project decisions.

## Documentation impact

Review docs/agents/DOCUMENTATION_FRESHNESS_CHECKS.md before updating docs, docs/agents/DOCUMENTATION_AGENTS.md for documentation-agent behavior, and docs/context/BUILD_STATE.md for active project state. Update only the docs affected by the current task.

For M2 documentation-agent foundation work, confirm whether the change affects:

- Documentation agent responsibilities.
- Source-of-truth update flow.
- Documentation impact detection rules.
- Documentation freshness checks.
- Human-reviewed documentation update expectations.
- Required validation evidence.
- Handoffs between implementation agents, documentation agents, validation agents, and the human owner.

## Validation expectations

Validate documentation-only changes with the issue-requested commands, normally including `git diff --check` and `git status --short`. Confirm changed docs preserve manual-review and advisory boundaries during M2 foundation work unless governance changes them.

Confirm no automation, workflow, auto-merge, autonomous approval, autonomous issue closure, repository setting, branch protection, ruleset, secret, release, tag, or GitHub Project change was introduced.

## Evidence requirements

Report files reviewed, files changed, documentation impact, freshness checks, stale documentation warnings, validation commands and results, skipped checks, human-review boundary confirmation, known limitations, issue and PR references, handoff notes, and the required non-authority statement from `docs/agents/DOCUMENTATION_SYNC_EVIDENCE_PACKAGES.md`.

When a handoff package is required, use `docs/agents/DOCUMENTATION_SYNC_HANDOFF_TEMPLATE.md` to keep issue and PR references, source documents reviewed, freshness-check evidence, documentation-sync evidence, validation evidence, human-review notes, limitations, escalation items, and next-owner notes clearly separated.

## Related docs

- docs/agents/DOCUMENTATION_FRESHNESS_CHECKS.md
- docs/agents/DOCUMENTATION_SYNC_EVIDENCE_PACKAGES.md
- docs/agents/DOCUMENTATION_SYNC_HANDOFF_TEMPLATE.md
- docs/agents/DOCUMENTATION_AGENTS.md
- docs/agents/AGENT_SKILLS_MODEL.md
- docs/architecture/LOCAL_OPERATOR_WORKFLOW.md
- docs/context/AGENT_CONTEXT.md
- docs/context/BUILD_STATE.md
- docs/governance/SELF_MANAGEMENT_MODEL.md
- docs/prompts/CODEX_PROMPT_STANDARD.md
- docs/prompts/CODEX_PROMPT_PACKAGE_TEMPLATE.md

## Lifecycle status

Draft
