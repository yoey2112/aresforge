# Documentation Sync Skill

## Name

Documentation sync

## Purpose

Guide agents in detecting documentation impact and updating the correct AresForge docs as part of scoped implementation work.

## When to use

Use this skill when a change affects project context, build state, roadmap sequencing, agent behavior, governance, architecture, prompt standards, validation expectations, or release-facing project memory.

## When not to use

Do not use this skill to rewrite unrelated documentation, replace source-of-truth governance docs, overwrite intentional human decisions, or promote future-state ideas into completed functionality.

## Inputs

- Active issue or task requirements.
- Changed files or planned file changes.
- Existing context, agent, governance, roadmap, prompt, architecture, and validation docs.
- Validation evidence and PR summary when available.
- Explicit human decisions relevant to the work.

## Outputs

- Focused documentation edits.
- Documentation impact summary.
- Stale documentation warnings when a related update is real but out of scope.
- Validation evidence for documentation review.

## Scope boundaries

This skill covers documentation impact analysis and scoped documentation updates. It does not authorize unrelated rewrites, broad reorganization, new automation, or changes to project authority boundaries.

## Execution boundaries

This skill is advisory and manually executed. It does not create documentation agents, watchers, workflows, scripts, or runnable sync automation.

## Human approval boundaries

Human approval is required before changing governance meaning, autonomy levels, approval requirements, source-of-truth priority, roadmap commitments, or historical project decisions.

## Documentation impact

Review docs/agents/DOCUMENTATION_AGENTS.md for documentation-agent behavior and docs/context/BUILD_STATE.md for active project state. Update only the docs affected by the current task.

## Validation expectations

Validate documentation-only changes with the issue-requested commands, normally including `git diff --check` and `git status --short`. Confirm changed docs preserve manual-review and advisory boundaries during M0 and M1 unless governance changes them.

## Evidence requirements

Report files reviewed, files changed, documentation impact, stale documentation warnings, validation commands and results, skipped checks, and known limitations.

## Related docs

- docs/agents/DOCUMENTATION_AGENTS.md
- docs/agents/AGENT_SKILLS_MODEL.md
- docs/context/AGENT_CONTEXT.md
- docs/context/BUILD_STATE.md
- docs/governance/SELF_MANAGEMENT_MODEL.md
- docs/prompts/CODEX_PROMPT_STANDARD.md

## Lifecycle status

Draft
