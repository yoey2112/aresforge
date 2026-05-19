# Issue Planning Skill

## Name

Issue planning

## Purpose

Guide conversion of approved AresForge goals into scoped GitHub issues, implementation prompts, documentation expectations, and validation evidence requirements.

## When to use

Use this skill when planning future work from roadmap items, human-approved goals, governance gaps, validation findings, or follow-up recommendations.

## When not to use

Do not use this skill to create issues autonomously, change project priorities without human approval, expand scope beyond the approved milestone, or treat draft plans as committed roadmap decisions.

## Inputs

- Human-approved goal, roadmap item, or follow-up need.
- Current roadmap, build state, project context, and governance docs.
- Relevant validation evidence, limitations, or stale documentation warnings.
- Existing issue and milestone state when available.

## Outputs

- Draft issue scope and acceptance criteria.
- Suggested labels, milestone, risk level, and evidence expectations.
- Implementation prompt outline that follows the Codex prompt standard.
- Issue creation documentation expectations when a planned issue will exercise or refine GitHub operations.
- Human decisions or clarifications needed before issue creation.

## Scope boundaries

This skill covers planning and drafting. It does not authorize autonomous issue creation, priority changes, milestone changes, or external project-management integration.

## Execution boundaries

This skill is advisory and manually executed. It does not create issue bots, planning workflows, packages, scripts, or runnable automation.

## Human approval boundaries

Human approval is required before creating issues, changing milestones, changing roadmap priority, assigning ownership, or promoting a plan into active work.

## Documentation impact

Review docs/roadmap/ROADMAP.md and docs/context/BUILD_STATE.md when issue planning affects milestone sequencing or active work. Review docs/prompts/CODEX_PROMPT_STANDARD.md for implementation prompt structure.

When issue creation itself discovers reusable GitHub CLI, API, milestone, label, shell, or evidence-comment patterns, record those lessons in the relevant validation, learning, or skill documentation. Issue creation patterns should be captured for future automation reuse, but during M1 they remain advisory, manually executed, and human-reviewed.

Recurring planning or issue-creation failures should become entries in `docs/learning/ERROR_PATTERNS.md` when they could affect future prompts, issue evidence, GitHub operations, or validation expectations.

## Validation expectations

Check planned issue scope against source-of-truth docs and confirm it preserves current governance and autonomy boundaries.

## Evidence requirements

Report source docs reviewed, planning assumptions, proposed scope, non-scope, acceptance criteria, validation expectations, documentation impact, issue creation lessons when relevant, and human decisions needed.

## Related docs

- docs/roadmap/ROADMAP.md
- docs/context/PROJECT_CONTEXT.md
- docs/context/BUILD_STATE.md
- docs/governance/SELF_MANAGEMENT_MODEL.md
- docs/prompts/CODEX_PROMPT_STANDARD.md
- docs/agents/AGENT_SKILLS_MODEL.md
- docs/learning/ERROR_PATTERNS.md

## Lifecycle status

Draft
