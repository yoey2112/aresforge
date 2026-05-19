# AresForge Documentation Agents

## Purpose

Documentation agents ensure that every pushed change updates the documentation needed by humans and AI agents.

They keep AresForge usable while GitHub and repository documentation are the temporary source of truth. During M0, documentation agents are an operating model, not autonomous automation: a human-guided agent proposes and edits documentation, validation evidence is captured for PR review, and all changes remain manually reviewed.

## M0 Documentation Agent Model

AresForge uses specialized documentation agents to decide which docs must change when project behavior, architecture, governance, roadmap, prompts, validation evidence, or release state changes.

In M0, these agents may be represented by one implementation session. The session must still reason through the specialist responsibilities below and report the documentation impact in the PR evidence.

Future versions may split these responsibilities into separate automated agents after the dashboard, validation workflows, and autonomy controls exist.

## Relationship To Agent Skills

AresForge's reusable skill model is defined in docs/agents/AGENT_SKILLS_MODEL.md.

Future documentation agents should use repo-owned markdown skills for repeatable documentation-sync and build-state-update work. During M0, those skills are guidance only: a human-guided agent may follow them, but documentation changes remain manually reviewed and must include validation evidence.

## Documentation Agent Types

### Context Documentation Agent

Maintains the shared project context used by human reviewers and AI agents.

Primary files:

- docs/context/PROJECT_CONTEXT.md
- docs/context/AGENT_CONTEXT.md
- docs/context/BUILD_STATE.md

Responsibilities:

- Update project context when the project identity, source of truth, managed project scope, or bootstrap assumptions change.
- Update agent context when agent roles, responsibilities, handoff expectations, or behavior rules change.
- Update build state when milestone status, completed work, active work, blockers, or next steps change.
- Preserve earlier decisions as historical context unless a human-approved change explicitly supersedes them.
- Flag stale context when implementation changes contradict current context docs.

### Architecture Documentation Agent

Maintains documentation about system structure and technical boundaries.

Primary files:

- docs/architecture/SYSTEM_OVERVIEW.md
- Future architecture decision records or component docs

Responsibilities:

- Update architecture docs when system structure, component boundaries, data flow, runtime assumptions, integrations, or deployment shape changes.
- Record architectural decisions with enough context for future agents to understand why the decision was made.
- Flag undocumented structural changes, especially new services, workflows, agents, storage, external dependencies, or execution environments.
- Avoid treating temporary M0 scaffolding as permanent architecture unless the decision is intentional.

### Roadmap Documentation Agent

Maintains milestone, priority, and sequencing documentation.

Primary files:

- docs/roadmap/ROADMAP.md
- docs/context/BUILD_STATE.md
- GitHub milestone and issue summaries when available

Responsibilities:

- Update roadmap docs when milestones, priorities, sequencing, scope, dependencies, or completion criteria change.
- Keep BUILD_STATE aligned with the current milestone and active work.
- Flag issue or PR changes that imply roadmap movement but do not update roadmap docs.
- Preserve deferred ideas and future work without silently promoting them into active scope.

### Governance Documentation Agent

Maintains operating rules, review expectations, and autonomy constraints.

Primary files:

- docs/governance/SELF_MANAGEMENT_MODEL.md
- Future governance, escalation, risk, and approval docs

Responsibilities:

- Update governance docs when autonomy levels, review gates, escalation paths, approval rules, or source-of-truth rules change.
- Preserve the M0 constraint that all changes are manually reviewed.
- Flag changes that appear to enable automation, auto-merge, destructive operations, or autonomous issue closure without explicit governance approval.
- Record risk exceptions and human decisions without overwriting the original rationale.

### Prompt Documentation Agent

Maintains handoff standards for Codex and future implementation agents.

Primary files:

- docs/prompts/CODEX_PROMPT_STANDARD.md
- Future prompt templates and agent handoff docs

Responsibilities:

- Update prompt standards when the required handoff format, evidence expectations, validation expectations, or documentation update requirements change.
- Ensure prompts continue to require relevant context docs, constraints, validation steps, documentation updates, and deliverable evidence.
- Flag prompts that omit required context or allow broad unrelated changes.
- Preserve prompt standards as reviewable guidance rather than hidden automation behavior.

### Release Notes Documentation Agent

Maintains release-facing summaries and changelog evidence.

Primary files:

- Future changelog or release notes files
- PR summaries and validation evidence while formal release notes do not exist

Responsibilities:

- Update changelog or release notes when user-visible behavior, project state, shipped capability, validation result, or milestone completion changes.
- Summarize documentation impact for PR reviewers.
- Link or reference validation evidence that supports release claims.
- Flag missing release notes when a change should be visible to future users or operators.

## Required Inputs

Documentation agents must review the following inputs when available:

- Changed files from the working tree, branch diff, or PR diff.
- Issue body, including goals, constraints, required changes, and acceptance criteria.
- PR summary, including implementation notes and stated validation.
- Validation evidence, including command output summaries, test results, screenshots, local review output, or manual review notes.
- Existing context docs, especially PROJECT_CONTEXT, AGENT_CONTEXT, BUILD_STATE, roadmap, architecture, governance, and prompt standards.
- Changelog or release notes when available.
- Human decisions recorded in issues, PR comments, review comments, or documentation.

If an input is unavailable, the agent must state that limitation in the documentation impact summary or PR evidence.

## Required Outputs

Documentation agents must produce:

- Updated documentation files for every confirmed documentation impact.
- A documentation impact summary for PR review.
- Stale documentation warnings when related docs may be outdated but cannot be safely changed in the current task.
- Validation evidence for PR review, including commands run and relevant results.
- Follow-up issue recommendations when documentation gaps are real but out of scope.

The output must distinguish between confirmed updates, warnings, and future work.

## Documentation Update Rules

Documentation agents must follow these rules:

- Docs must not overwrite intentional human decisions unless the issue or PR explicitly changes that decision.
- Docs must preserve historical context by recording superseded decisions as prior context or completed state when useful.
- BUILD_STATE must be updated when project phase, current goal, source of truth, completed work, active work, blockers, or next steps change.
- AGENT_CONTEXT must be updated when agent behavior, responsibilities, roles, handoff expectations, or operating rules change.
- Architecture docs must be updated when system structure, boundaries, runtime assumptions, integrations, or data flow change.
- Roadmap docs must be updated when milestones, priorities, sequencing, dependencies, or completion criteria change.
- Prompt standards must be updated when agent handoff format, required prompt sections, validation expectations, documentation expectations, or evidence requirements change.
- Governance docs must be updated when autonomy, review, approval, escalation, or source-of-truth rules change.
- Release notes or changelog docs must be updated when a change should be visible to future users, operators, or release reviewers.
- Documentation changes must stay scoped to the issue or PR.
- M0 documentation changes must remain manually reviewed.

## Initial M0 Documentation Update Flow

1. Read the issue body and required context docs before editing.
2. Inspect changed files or planned changes.
3. Classify the documentation impact by agent type:
   - Context
   - Architecture
   - Roadmap
   - Governance
   - Prompt
   - Release notes
4. Update only the affected documentation files.
5. Preserve prior decisions and completed history.
6. Add stale documentation warnings when a related doc may need later review but is out of scope.
7. Run the validation commands requested by the issue or PR prompt.
8. Report files changed, documentation impact, validation evidence, and follow-up risks in the PR or final handoff.

During M0, this flow is manual and human-reviewed. Documentation agents may recommend updates, but they must not create scripts, enable automation, auto-close issues, auto-merge PRs, or treat a PR as accepted without human review.

## Stale Documentation Warnings

A stale documentation warning should be produced when:

- Code or docs imply a changed behavior but the authoritative doc is not updated.
- A roadmap or build-state change is suggested but not confirmed by the issue.
- Architecture appears to change, but the current task does not include enough evidence to document the new structure safely.
- Governance or autonomy behavior appears to change without explicit approval.
- Release notes should exist, but no release notes file has been created yet.

Warnings should be specific, scoped, and actionable. They should not block a PR automatically during M0, but they should give reviewers enough context to decide whether follow-up work is required.

## Validation Evidence

Documentation agent validation evidence should include:

- Documentation files changed.
- Documentation files reviewed but left unchanged when relevant.
- Commands run and concise results.
- Known limitations, skipped checks, or unavailable inputs.
- Stale documentation warnings.
- Follow-up issue recommendations, if any.

For M0 documentation-only work, a diff review and working-tree status may be sufficient when the issue explicitly requests those checks.

## Risks And Anti-Patterns

Risks:

- Documentation drift if implementation changes are merged without updating context, architecture, roadmap, governance, prompt, or release notes docs.
- Loss of project memory if agents replace historical context instead of preserving completed decisions.
- False authority if generated docs imply human approval before review occurs.
- Scope creep if documentation agents rewrite unrelated docs during a narrow issue.
- Automation risk if future agents update, merge, or close work without respecting governance controls.

Anti-patterns:

- Treating documentation as cleanup after implementation rather than part of the work.
- Rewriting human decisions because they look outdated without confirming the new decision.
- Updating BUILD_STATE to completed before the work has enough review evidence.
- Changing roadmap sequencing based only on an implementation convenience.
- Adding broad future architecture claims from temporary M0 scaffolding.
- Omitting validation evidence from the PR handoff.
- Creating scripts or automation during M0 documentation-model work.

## M0 Decision

The first M0 documentation workflow should focus on keeping these files current:

- docs/context/PROJECT_CONTEXT.md
- docs/context/AGENT_CONTEXT.md
- docs/context/BUILD_STATE.md
- docs/roadmap/ROADMAP.md
- docs/architecture/SYSTEM_OVERVIEW.md

Additional governance, prompt, validation, changelog, and release notes docs should be updated when the issue or PR changes their scope.
