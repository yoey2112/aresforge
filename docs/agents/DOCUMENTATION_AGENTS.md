# AresForge Documentation Agents

## Purpose

Documentation agents keep AresForge's repository documentation usable as durable project memory for humans and future agents.

During M2, documentation agents are an operating model, not autonomous automation. A human-guided implementation session may perform documentation-agent responsibilities, update source-of-truth docs, and report stale documentation warnings, but all documentation changes remain human-reviewed through normal pull requests.

This document is the canonical documentation agent architecture document. The canonical path is `docs/agents/DOCUMENTATION_AGENTS.md`.

## Current M2 Foundation Boundary

The M2 documentation agent foundation establishes rules and handoffs before autonomous documentation automation exists.

M2 documentation agent work must not:

- Create runnable documentation automation.
- Create or modify workflows.
- Enable auto-merge.
- Enable autonomous approval.
- Enable autonomous issue closure.
- Close issues manually unless a human explicitly instructs that action.
- Change repository settings, branch protection, rulesets, secrets, releases, tags, or GitHub Projects.
- Treat future-state documentation as active capability.

Documentation agents may:

- Review source-of-truth docs.
- Identify documentation impact.
- Propose or make issue-scoped documentation updates in a branch.
- Record stale documentation warnings.
- Summarize validation evidence for PR review.
- Recommend follow-up issues when gaps are real but out of scope.

## Relationship To Agent Skills

AresForge's reusable skill model is defined in `docs/agents/AGENT_SKILLS_MODEL.md`.

Documentation agents should use repo-owned markdown skills for repeatable documentation-sync and build-state-update work when relevant. During M2, those skills remain advisory, manually executed, and human-reviewed unless a later governance change explicitly approves automation.

Primary related skills:

- `.agent/skills/documentation-sync/SKILL.md`
- `.agent/skills/build-state-update/SKILL.md`
- `.agent/skills/pr-validation/SKILL.md`

Primary related models:

- `docs/agents/DOCUMENTATION_FRESHNESS_CHECKS.md`
- `docs/agents/DOCUMENTATION_SYNC_EVIDENCE_PACKAGES.md`
- `docs/architecture/LOCAL_OPERATOR_WORKFLOW.md`

## Documentation Agent Responsibilities

Documentation agents are responsible for keeping source-of-truth documentation aligned with issue scope, implementation changes, validation evidence, and human decisions.

Core responsibilities:

- Read required source-of-truth docs before editing.
- Detect documentation impact from issue requirements, changed files, PR summaries, validation evidence, and human decisions.
- Update only the documentation files affected by the current issue or PR.
- Preserve historical context unless the issue explicitly supersedes it.
- Keep active project state, agent rules, roadmap state, governance expectations, prompt standards, and validation expectations consistent.
- Flag stale documentation when a related doc appears outdated but cannot be safely updated in the current scope.
- Report validation evidence in the PR body or final handoff.
- Preserve human-review boundaries and avoid implying approval, merge, issue closure, release, or automation that has not occurred.
- Use local operator packages as review inputs when available, while treating them as evidence summaries rather than approval or automation.
- Prepare documentation-sync evidence packages when documentation-sync work is performed, using `docs/agents/DOCUMENTATION_SYNC_EVIDENCE_PACKAGES.md` as the required review artifact model.

## Documentation Agent Types

### Context Documentation Agent

Maintains shared project context used by human reviewers and AI agents.

Primary files:

- `docs/context/PROJECT_CONTEXT.md`
- `docs/context/AGENT_CONTEXT.md`
- `docs/context/BUILD_STATE.md`

Responsibilities:

- Update project context when project identity, source of truth, managed project scope, or bootstrap assumptions change.
- Update agent context when agent roles, responsibilities, handoff expectations, or operating rules change.
- Update build state when milestone status, active issue, completed work, blockers, validation status, or next steps change.
- Preserve prior decisions as completed or historical context when useful.
- Flag stale context when implementation or issue scope contradicts current context docs.

### Architecture Documentation Agent

Maintains documentation about system structure and technical boundaries.

Primary files:

- `docs/architecture/SYSTEM_OVERVIEW.md`
- Future architecture decision records or component docs

Responsibilities:

- Update architecture docs when system structure, component boundaries, data flow, runtime assumptions, integrations, or deployment shape change.
- Record architectural decisions with enough context for future agents to understand why the decision was made.
- Flag undocumented structural changes, especially new services, workflows, agents, storage, external dependencies, or execution environments.
- Avoid treating temporary scaffolding or future-state concepts as active architecture unless the decision is intentional and human-reviewed.

### Roadmap Documentation Agent

Maintains milestone, priority, and sequencing documentation.

Primary files:

- `docs/roadmap/ROADMAP.md`
- `docs/context/BUILD_STATE.md`
- GitHub milestone and issue summaries when available

Responsibilities:

- Update roadmap docs when milestones, priorities, sequencing, scope, dependencies, status, or completion criteria change.
- Keep `BUILD_STATE` aligned with the current phase and active implementation issue.
- Flag issue or PR changes that imply roadmap movement without a matching roadmap or build-state update.
- Preserve deferred ideas and future work without silently promoting them into active scope.

### Governance Documentation Agent

Maintains operating rules, review expectations, and autonomy constraints.

Primary files:

- `docs/governance/SELF_MANAGEMENT_MODEL.md`
- `docs/governance/PR_VALIDATION_MODEL.md`
- Future governance, escalation, risk, and approval docs

Responsibilities:

- Update governance docs when autonomy levels, review gates, escalation paths, approval rules, validation standards, or source-of-truth rules change.
- Preserve the current manual, human-reviewed operating model unless a future human-approved governance issue changes it.
- Flag changes that appear to enable automation, workflows, auto-merge, autonomous approval, autonomous issue closure, destructive operations, or repository-setting changes without explicit approval.
- Record risk exceptions and human decisions without overwriting the original rationale.

### Prompt Documentation Agent

Maintains handoff standards for Codex and future implementation agents.

Primary files:

- `docs/prompts/CODEX_PROMPT_STANDARD.md`
- Future prompt templates and agent handoff docs

Responsibilities:

- Update prompt standards when handoff format, evidence expectations, validation expectations, safety constraints, or documentation requirements change.
- Ensure implementation prompts continue to require source-of-truth review, issue scope, constraints, documentation updates, validation steps, and deliverable evidence.
- Flag prompts that omit required context or allow broad unrelated changes.
- Preserve prompt standards as reviewable guidance rather than hidden automation behavior.

### Validation Documentation Agent

Maintains documentation that supports repeatable validation evidence and PR review.

Primary files:

- `docs/governance/PR_VALIDATION_MODEL.md`
- `docs/validation/`
- `docs/learning/ERROR_PATTERNS.md`
- PR validation summaries and evidence comments when available

Responsibilities:

- Confirm documentation changes include enough validation evidence for human review.
- Update validation docs when evidence requirements, review categories, or reusable command lessons change.
- Check `docs/learning/ERROR_PATTERNS.md` before repeating GitHub CLI, Windows PowerShell, encoding-sensitive, or operational state update commands.
- Flag missing or weak validation evidence without converting the warning into an autonomous merge gate.

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

- Active issue body, including goals, constraints, required changes, acceptance criteria, and out-of-scope boundaries.
- Required source-of-truth docs named by the issue or prompt.
- Changed files from the working tree, branch diff, or PR diff.
- PR summary, implementation notes, and stated validation when available.
- Validation evidence, including command output summaries, test results, screenshots, local review output, or manual review notes.
- Existing context docs, especially project context, agent context, build state, roadmap, architecture, governance, prompt standards, validation docs, and learning docs.
- Changelog or release notes when available.
- Human decisions recorded in issues, PR comments, review comments, or documentation.

If an input is unavailable, the documentation impact summary or PR evidence must state that limitation.

## Required Outputs

Documentation agents must produce:

- Updated documentation files for every confirmed documentation impact in scope.
- A documentation impact summary for PR review.
- Documentation freshness checks and stale documentation warnings when related docs may be outdated.
- Documentation-sync evidence package content when documentation-sync work is performed.
- Validation evidence for PR review, including commands or manual checks run and concise results.
- Human-review boundary confirmation.
- Follow-up issue recommendations when documentation gaps are real but out of scope.

The output must distinguish confirmed updates, warnings, skipped checks, future work, and human decisions.

## Source-Of-Truth Update Flow

Use this flow for M2 documentation-agent work:

1. Read the issue body and required source-of-truth docs before editing.
2. Check `docs/learning/ERROR_PATTERNS.md` before GitHub CLI, Windows PowerShell, encoding-sensitive, or operational state update commands.
3. Inspect the working tree and planned changes.
4. Classify documentation impact by agent type.
5. Identify canonical docs for each confirmed impact.
6. Update only issue-scoped documentation.
7. Preserve completed history and prior human decisions.
8. Add stale documentation warnings when related docs may need later review but are out of scope.
9. Run requested validation checks.
10. Review the changed files for scope, freshness, and human-review boundaries.
11. Prepare the required evidence package content when documentation-sync work occurred.
12. Report files changed, documentation impact, freshness checks, validation evidence, warnings, limitations, and non-authority statements in the PR or final handoff.

During M2, this flow is manual and human-reviewed. It must not create scripts, watchers, workflows, auto-updaters, auto-merge behavior, autonomous approvals, or autonomous issue closure.

Local operator workflow packages may prepare issue context, freshness check evidence, documentation-sync inputs, validation checklists, and PR evidence outlines for this flow. They must not be treated as implemented automation or as permission to skip human review.

## Documentation Impact Detection Rules

Documentation impact exists when a change affects one or more of the following:

- Project state, active issue, current phase, blockers, completed work, next steps, or handoff context.
- Agent responsibilities, operating rules, handoff expectations, skills, source-of-truth review rules, or documentation-agent behavior.
- Architecture, system boundaries, integrations, runtime assumptions, data flow, storage, workflows, services, or execution environments.
- Roadmap scope, milestone status, priority, sequencing, dependencies, first-deliverable wording, or completion criteria.
- Governance, autonomy level, approval boundaries, escalation paths, safety constraints, source-of-truth priority, or human-review rules.
- Prompt format, implementation-agent expectations, validation evidence requirements, or PR evidence requirements.
- Validation standards, scoring rules, evidence expectations, command patterns, known error patterns, or freshness checks.
- Release-facing behavior, changelog content, user-visible state, or milestone closeout summaries.

No documentation impact exists only when the issue or PR changes no project memory, operating rule, validation rule, architecture, roadmap state, or release-facing claim. When claiming no documentation impact, the PR evidence should say why.

## Documentation Freshness Checks

Documentation agents must use the repeatable freshness check model in `docs/agents/DOCUMENTATION_FRESHNESS_CHECKS.md` before documentation-sync work.

The freshness check model defines required inputs, required outputs, stale documentation detection, missing documentation detection, conflicting documentation detection, incomplete documentation detection, outdated build-state and roadmap detection, evidence rules, and human escalation rules.

Documentation agents should also check freshness before final handoff by asking:

- Does `BUILD_STATE` name the correct phase, active issue, current goal, in-progress work, and next step?
- Does `AGENT_CONTEXT` reflect current agent behavior, source-of-truth rules, handoff expectations, and phase-specific boundaries?
- Does the roadmap accurately describe the current phase status and first active M2 deliverable?
- Does the documentation-agent architecture match the current canonical path and operating model?
- Do skill files and the registry still describe advisory, manually executed, human-reviewed behavior?
- Do governance docs preserve the current autonomy boundary and human-review requirements?
- Do validation docs require adequate evidence without implying approval, merge, or autonomous enforcement?
- Do prompt docs require source-of-truth review, issue scope, documentation impact reasoning, validation evidence, and safe PR handling?
- Are stale M0 or M1 references still historical context, or do they incorrectly describe the current operating phase?
- Are out-of-scope docs intentionally left unchanged and, if relevant, called out as warnings?

Freshness checks do not authorize broad rewrites. They identify whether the current issue requires a focused update or a follow-up recommendation.

## Documentation-Sync Evidence Packages

Documentation agents must use `docs/agents/DOCUMENTATION_SYNC_EVIDENCE_PACKAGES.md` when documentation-sync work requires PR evidence, closeout evidence, or a documentation-sync handoff.

Evidence packages must record purpose, issue and PR references, freshness-check evidence, required source documents reviewed, touched documents, diff and validation summaries, human-review notes, limitation and exception notes, handoff notes, and a non-authority statement.

Evidence packages are review artifacts only. They do not approve, merge, close, automate, bypass review, or replace required human controls.

## Human-Reviewed Documentation Update Expectations

All M2 documentation-agent updates must be human-reviewed.

Documentation PRs should:

- Use a dedicated branch.
- Keep changes issue-scoped.
- Stage only intended files.
- Preserve historical context.
- Avoid unrelated cleanup.
- Include documentation impact reasoning.
- Include freshness checks added or clarified.
- Include validation evidence.
- Confirm human-review boundaries.
- Avoid issue-closing language unless the human owner wants the issue to close after merge.

Documentation agents must not mark work complete in source-of-truth docs before enough evidence exists. They may mark an issue as active while implementation is in progress and may record completed work only after the relevant PR has merged or the source document explicitly describes in-progress state.

## Required Validation Evidence For Documentation Changes

For documentation-only M2 changes, required validation evidence normally includes:

- `git status --short`
- `git diff --check`
- Review of changed files for issue scope.
- Confirmation that no automation, workflow, auto-merge, autonomous approval, autonomous issue closure, repository setting, branch protection, ruleset, secret, release, tag, or GitHub Project change was introduced.

Issue-specific prompts may require additional checks.

Validation evidence should report:

- Documentation files reviewed.
- Documentation files changed.
- Commands or manual checks run.
- Concise result of each check.
- Known skipped checks or unavailable inputs.
- Stale documentation warnings.
- Follow-up recommendations, if any.

## Handoff Expectations

### Implementation Agent To Documentation Agent

Implementation agents should provide:

- Issue number and title.
- Branch name.
- Changed files or planned files.
- Summary of behavior or documentation changes.
- Source-of-truth docs reviewed.
- Validation already run.
- Known skipped checks, risks, or limitations.
- Human decisions that affect documentation.

### Documentation Agent To Validation Agent

Documentation agents should provide:

- Files changed.
- Documentation impact reasoning.
- Freshness checks performed or clarified.
- Stale documentation warnings.
- Human-review boundary confirmation.
- Validation commands and results.
- Known limitations and follow-up recommendations.

### Validation Agent To Human Owner

Validation agents should provide:

- Requirement fit assessment.
- Scope control assessment.
- Documentation completeness assessment.
- Evidence quality assessment.
- Risk notes.
- Advisory merge-readiness state.
- Explicit statement that human review remains required.

### Human Owner To Agents

The human owner remains the final escalation authority for:

- Approval decisions.
- Merge decisions.
- Issue closure decisions outside normal GitHub close-on-merge behavior.
- Governance changes.
- Autonomy changes.
- Risk exceptions.
- Repository settings, branch protection, rulesets, secrets, releases, tags, or GitHub Project changes.

## Stale Documentation Warnings

A stale documentation warning should be produced when:

- Code, docs, or issue scope imply changed behavior but the authoritative doc is not updated.
- A roadmap or build-state change is suggested but not confirmed by the issue.
- Architecture appears to change, but the current task does not include enough evidence to document the new structure safely.
- Governance or autonomy behavior appears to change without explicit approval.
- Validation expectations change but validation docs are out of scope.
- A skill or registry entry may be stale but ownership or lifecycle status is not part of the current issue.
- Release notes should exist, but no release notes file has been created yet.

Warnings should be specific, scoped, and actionable. During M2 foundation work, they are review evidence, not autonomous blockers.

## Risks And Anti-Patterns

Risks:

- Documentation drift if implementation changes merge without updating context, architecture, roadmap, governance, prompt, validation, or release-facing docs.
- Loss of project memory if agents replace historical context instead of preserving completed decisions.
- False authority if generated docs imply human approval before review occurs.
- Scope creep if documentation agents rewrite unrelated docs during a narrow issue.
- Automation risk if future agents update, merge, approve, or close work without respecting governance controls.

Anti-patterns:

- Treating documentation as cleanup after implementation rather than part of the work.
- Rewriting human decisions because they look outdated without confirming the new decision.
- Updating `BUILD_STATE` to completed before the work has enough review evidence.
- Changing roadmap sequencing based only on implementation convenience.
- Adding broad future architecture claims from temporary scaffolding.
- Omitting validation evidence from the PR handoff.
- Creating scripts, workflows, auto-updaters, or other automation during M2 documentation-agent foundation work.
- Using stale M0 or M1 phase wording as current-state wording.
