# AresForge Documentation Freshness Checks

## Purpose

This document defines the M2 documentation freshness check model for AresForge.

A documentation freshness check is a manual, evidence-based review that compares current project work, source-of-truth documentation, validation evidence, and human decisions before documentation-sync work is performed.

The goal is to detect stale, missing, conflicting, incomplete, or outdated documentation early enough that a human-reviewed PR can either update the correct docs or record a clear warning and follow-up recommendation.

During M2, freshness checks are documentation-only, advisory, manually executed, and human-reviewed. They do not create runnable automation, workflows, watchers, merge gates, autonomous approval, autonomous issue closure, or autonomous documentation updates.

## Relationship To Documentation Agents And Skills

The canonical documentation agent architecture is `docs/agents/DOCUMENTATION_AGENTS.md`.

Documentation agents use this freshness check model before performing documentation-sync work. The documentation-sync skill at `.agent/skills/documentation-sync/SKILL.md` must point agents to this model as the required pre-sync review layer.

This model supports, but does not replace:

- Documentation agent responsibilities.
- Documentation impact detection.
- Source-of-truth update flow.
- Documentation-sync evidence packages defined in `docs/agents/DOCUMENTATION_SYNC_EVIDENCE_PACKAGES.md`.
- Documentation-sync handoff packages defined in `docs/agents/DOCUMENTATION_SYNC_HANDOFF_TEMPLATE.md`.
- Human-reviewed documentation update expectations.
- PR validation and evidence review.
- Human escalation when source-of-truth status is uncertain.
- Local operator workflow packaging defined in `docs/architecture/LOCAL_OPERATOR_WORKFLOW.md`.

## When A Freshness Check Must Be Performed

A freshness check must be performed before documentation-sync work when a task or PR affects any of the following:

- Project phase, active issue, build state, blockers, completed work, or next steps.
- Roadmap status, milestone sequencing, M2 foundation scope, or future-phase claims.
- Documentation agent responsibilities, skill behavior, handoff expectations, or source-of-truth rules.
- Governance, autonomy boundaries, human approval rules, validation expectations, or PR evidence expectations.
- Architecture, runtime assumptions, integrations, workflows, repository settings, or future dashboard state.
- Prompt standards, implementation handoff requirements, or required validation evidence.
- Learning entries, repeated error patterns, command guidance, or encoding-sensitive documentation updates.
- Release-facing summaries, changelog material, or user-visible project memory.

A freshness check should also be performed when a human reviewer, issue body, PR comment, or agent detects likely documentation drift even if no file edit is planned yet.

## Required Inputs

Use all available inputs that apply to the current task:

- Active issue body, title, labels, milestone, constraints, and acceptance criteria.
- Human instructions from the current session.
- Current branch name and working tree status.
- Changed files, planned files, branch diff, or PR diff.
- Source-of-truth docs named by the issue or prompt.
- `docs/context/PROJECT_CONTEXT.md`
- `docs/context/AGENT_CONTEXT.md`
- `docs/context/BUILD_STATE.md`
- `docs/roadmap/ROADMAP.md`
- `docs/agents/DOCUMENTATION_AGENTS.md`
- `.agent/AGENT_REGISTRY.md`
- Relevant `.agent/skills/*/SKILL.md` files.
- `docs/governance/SELF_MANAGEMENT_MODEL.md`
- `docs/governance/PR_VALIDATION_MODEL.md`
- `docs/prompts/CODEX_PROMPT_STANDARD.md`
- `docs/learning/ERROR_PATTERNS.md`
- Validation evidence, test results, screenshots, command output summaries, local AI review, or manual review notes.
- Existing PR summary, review comments, issue comments, and recorded human decisions when available.
- Local operator prompt packages, validation checklists, PR evidence packages, or closeout evidence packages when available.

If an expected input is unavailable, the freshness check output must record the limitation instead of silently assuming the missing input is current.

## Required Outputs

A freshness check must produce reviewable evidence that includes:

- Freshness check scope: issue or PR reviewed, source docs reviewed, and changed files considered.
- Confirmed documentation updates needed for the current scope.
- Confirmed documentation updates completed in the current change set.
- Stale documentation findings, if any.
- Missing documentation findings, if any.
- Conflicting documentation findings, if any.
- Incomplete documentation findings, if any.
- Outdated build-state or roadmap findings, if any.
- Evidence for each finding.
- Explicit distinction between confirmed facts, agent judgment, unavailable inputs, and future recommendations.
- Human escalation items when uncertainty cannot be resolved safely.
- Confirmation that the check remains advisory, manually executed, and human-reviewed.

The output may appear in a PR body, final implementation handoff, review comment, or documentation-change evidence summary.

When documentation-sync work is performed, the freshness check output must be carried into the appropriate evidence package: PR evidence, closeout evidence, or documentation-sync evidence. The evidence package must preserve stale warnings, skipped checks, unavailable inputs, human escalation items, and the advisory/manual M2 boundary.

## Freshness Check Flow

Use this manual flow before documentation-sync work:

1. Read the issue or task and identify its documentation impact.
2. Read required source-of-truth docs before editing.
3. Inspect the working tree and changed or planned files.
4. Compare current issue scope against project context, agent context, build state, roadmap, agent docs, skills, governance, prompts, validation docs, and learning docs.
5. Classify any documentation gap as stale, missing, conflicting, incomplete, outdated build-state or roadmap reference, or out of scope.
6. Record evidence for each finding using exact file paths, section names, issue or PR references, and validation facts when available.
7. Update only issue-scoped documentation that can be safely corrected.
8. Escalate uncertainty to the human owner when source-of-truth status, intent, approval, or scope cannot be determined.
9. Report the check results in the PR body or final handoff.

Freshness checks identify what should be updated. They do not authorize broad rewrites or unapproved changes outside the issue scope.

## Detecting Stale Documentation

Documentation is stale when it was once correct but no longer reflects the current source-of-truth state.

Signals include:

- `BUILD_STATE` names an old active issue, phase, goal, blocker, next step, or in-progress item.
- `AGENT_CONTEXT` describes prior phase behavior as current behavior.
- A skill summary omits a newly required pre-check, boundary, input, output, or evidence rule.
- Governance docs describe an autonomy level, review expectation, or approval boundary that no longer matches the current milestone rules.
- Validation docs or prompt standards omit evidence that the current issue now requires.
- A prior limitation is described as unresolved after a later reviewed change resolved it.
- A completed issue is still described as active, or an active issue is described as future work.

Evidence should cite the stale statement and the newer source that supersedes it, such as an issue body, merged PR summary, updated source-of-truth doc, or explicit human decision.

## Detecting Missing Documentation

Documentation is missing when a required project-memory record does not exist in the expected source-of-truth location.

Signals include:

- A new agent responsibility exists in an issue or PR but no agent doc, skill, or context doc describes it.
- A new governance boundary is required but no governance doc records it.
- A project-state change exists but `BUILD_STATE` has no corresponding current, in-progress, completed, or next-step entry.
- A roadmap milestone begins, changes status, or gains a foundation deliverable without a roadmap note.
- A reusable error pattern is discovered but `docs/learning/ERROR_PATTERNS.md` has no durable entry.
- A validation expectation is required by a prompt or issue but no validation or prompt doc captures it for future work.

Evidence should name the expected document, the reason it should contain the information, and the source that introduced the missing requirement.

## Detecting Conflicting Documentation

Documentation conflicts when two or more source-of-truth records make incompatible claims about current state, authority, scope, or behavior.

Signals include:

- One doc says an issue is active while another says no issue is active.
- One doc says a capability is advisory while another implies runnable automation exists.
- Roadmap status and build state disagree about the current phase or milestone progress.
- A skill grants authority that governance docs reserve for the human owner.
- A prompt standard requires one validation behavior while PR validation docs require an incompatible behavior.
- A file path is described differently across docs, especially for canonical agent, skill, or governance documents.

Evidence should include both sides of the conflict and the source-of-truth priority used to decide whether to update, warn, or escalate.

## Detecting Incomplete Documentation

Documentation is incomplete when it points in the right direction but lacks the details needed for a future human or agent to act safely.

Signals include:

- A model exists but lacks required inputs, outputs, evidence expectations, or escalation rules.
- A skill says to perform a check but does not identify the governing model or related docs.
- A build-state entry records an issue number but omits status, validation, or next step.
- A roadmap entry names a deliverable but omits status or sequencing context.
- A governance or prompt update describes a rule but omits approval boundaries.
- A validation summary says a check was run but does not include the command or concise result.

Evidence should identify the missing detail and explain why it is required for safe future use.

## Detecting Outdated Build-State Or Roadmap References

`docs/context/BUILD_STATE.md` and `docs/roadmap/ROADMAP.md` are high-churn project-memory files and require explicit review during freshness checks when project status changes.

Check `BUILD_STATE` for:

- Current phase.
- Current goal.
- Current active issue.
- In-progress work.
- Completed issue and PR history.
- Next step.
- Current operating constraints.
- ASCII-safe operational wording where practical.

Check `ROADMAP` for:

- Current milestone status.
- Completed foundation deliverables.
- Active or next M2 focus.
- Future-phase language that might be mistaken for current capability.
- Any milestone movement implied by the issue or PR.

If build-state or roadmap references cannot be safely updated during the current issue, record a warning and recommend follow-up rather than broadening the PR.

## Evidence Rules

Freshness evidence must be specific enough for human review.

Record:

- File paths and section names reviewed.
- Issue, PR, branch, or commit references when available.
- The observed statement or absence being evaluated.
- The source that supports the finding.
- The classification: stale, missing, conflicting, incomplete, outdated build-state or roadmap reference, no issue found, unavailable input, or out of scope.
- The action taken: updated, warned, escalated, or deferred.
- Validation commands or manual checks used to support the conclusion.

Do not rely on agent memory alone. If a claim matters to the check, ground it in repository docs, GitHub state, validation evidence, or an explicit human instruction.

## Human Escalation Rules

Escalate uncertainty to the human owner before updating documentation when:

- Source-of-truth docs and human instructions conflict.
- A doc appears intentionally historical but could be mistaken for current state.
- A change would alter governance meaning, autonomy level, approval rules, roadmap commitment, or human authority.
- A stale statement may reflect an unresolved human decision rather than drift.
- Required inputs are unavailable and a reasonable assumption could produce incorrect project memory.
- The current issue does not authorize a needed update.
- The update would imply automation, auto-merge, autonomous approval, autonomous issue closure, workflow changes, repository setting changes, branch protection changes, release changes, tag changes, or GitHub Project changes.

Escalation output should name the uncertainty, affected files, known evidence, and the decision needed.

## Connection To Documentation Sync

Documentation-sync work must begin with this freshness check model.

The documentation-sync skill should:

- Read this model before updating docs.
- Use the required inputs to inspect source-of-truth state.
- Classify documentation issues using the detection rules above.
- Update only issue-scoped docs that can be corrected safely.
- Report warnings and escalation items for anything uncertain or out of scope.
- Preserve the advisory, manual, human-reviewed M2 boundary.

The freshness check is the diagnostic layer. Documentation sync is the focused update layer that follows after the diagnostic findings are understood.

The documentation-sync evidence package model is the review artifact layer. It records the freshness findings, source documents reviewed, touched documents, validation summary, limitations, human-review notes, and handoff notes for PR review or closeout.

The documentation-sync handoff template is the copy/paste-friendly structure for carrying those findings to another agent, validation reviewer, local operator, or human owner. It remains a manual review artifact scaffold and does not approve, merge, close, automate, bypass review, or authorize future automation.

## Connection To Local Operator Workflow

The local operator workflow in `docs/architecture/LOCAL_OPERATOR_WORKFLOW.md` may prepare freshness check inputs and evidence summaries before documentation-sync work.

Operator-prepared packages should help identify source-of-truth docs, issue scope, likely documentation impact, stale or missing documentation findings, validation expectations, and human escalation items. They do not replace this freshness check model and do not authorize runnable automation, autonomous documentation updates, merge gates, approval gates, or issue closure.

Operator-prepared PR and closeout evidence packages should follow `docs/agents/DOCUMENTATION_SYNC_EVIDENCE_PACKAGES.md`, `docs/agents/PR_EVIDENCE_PACKAGE_TEMPLATE.md`, and `docs/agents/CLOSEOUT_EVIDENCE_PACKAGE_TEMPLATE.md` as applicable while remaining design-only review inputs during M2.

## M2 Boundary

During M2, this model remains a reviewable documentation standard only.

It must not be implemented as:

- A script.
- A workflow.
- A watcher.
- A bot.
- A merge gate.
- An approval gate.
- An autonomous documentation updater.
- An issue closer.
- A repository setting or branch protection rule.

Any future move from manual freshness checks to automated checks requires a separate human-approved governance change and implementation issue.
