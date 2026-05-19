# Build State Update Skill

## Name

Build-state update

## Purpose

Guide focused updates to AresForge build state so current phase, active work, completed work, blockers, validation status, and next steps remain useful for future sessions.

## When to use

Use this skill when work starts, completes, changes milestone state, changes active issue or branch context, adds validation evidence, identifies blockers, or changes the recommended next step.

## When not to use

Do not use this skill to mark work complete before evidence exists, rewrite project history, change roadmap commitments without approval, or imply a PR has merged before human review.

## Inputs

- Current issue, branch, PR, milestone, and validation state.
- docs/context/BUILD_STATE.md.
- Relevant roadmap, project context, and governance docs.
- Human decisions and PR evidence when available.

## Outputs

- Focused BUILD_STATE update.
- Clear active work and next-step summary.
- Completed work entry only when supported by evidence.
- Blocker or limitation notes when work cannot safely proceed.

## Scope boundaries

This skill covers project-state documentation. It does not authorize roadmap reprioritization, issue closure, merge decisions, release decisions, or autonomous state synchronization.

## Execution boundaries

This skill is advisory and manually executed. It does not create state-sync scripts, dashboard adapters, workflows, packages, or runnable automation.

## Human approval boundaries

Human approval is required before changing milestone commitments, marking governance-relevant decisions as approved, marking unmerged PR work as completed, or changing autonomy boundaries.

## Documentation impact

Update docs/context/BUILD_STATE.md when active work changes. Review docs/roadmap/ROADMAP.md if milestone sequencing changes and docs/context/AGENT_CONTEXT.md if agent operating context changes.

## Validation expectations

Confirm the build-state update matches issue scope, current branch or PR facts, and source-of-truth docs. For documentation-only updates, run the requested diff and status checks.

## Evidence requirements

Report build-state fields changed, source evidence used, validation commands and results, unresolved blockers, and whether any related docs were reviewed but left unchanged.

## Related docs

- docs/context/BUILD_STATE.md
- docs/context/PROJECT_CONTEXT.md
- docs/context/AGENT_CONTEXT.md
- docs/roadmap/ROADMAP.md
- docs/governance/SELF_MANAGEMENT_MODEL.md
- docs/agents/AGENT_SKILLS_MODEL.md

## Lifecycle status

Draft
