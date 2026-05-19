# AresForge Documentation-Sync Evidence Packages

## Purpose

This document defines the M2 documentation-sync evidence package model for AresForge.

An evidence package is a review artifact that records what was checked, what was changed, what evidence supports the change, what remains uncertain, and what a human reviewer or next agent should know before continuing.

Evidence packages support consistent documentation-sync review. They do not approve, merge, close, automate, bypass review, satisfy branch protection, or replace human decisions.

During M2, this model is documentation-only, advisory, manually prepared, and human-reviewed. It does not create scripts, runnable automation, workflows, bots, watchers, merge gates, autonomous approval, autonomous issue closure, or repository-setting changes.

## When Evidence Packages Are Required

Documentation-sync evidence packages are required when an issue, PR, closeout, or local operator handoff performs or depends on documentation-sync work.

They are required for:

- Pull requests that change source-of-truth docs.
- Closeout work that updates build state, roadmap state, issue status notes, or next-step handoff context.
- Documentation-sync work that follows the freshness check model.
- Local operator workflow packages that prepare PR evidence, closeout evidence, documentation-sync inputs, or freshness findings.
- Handoffs from implementation agents to documentation agents, documentation agents to validation agents, and validation agents to the human owner.

If a documentation-sync package cannot be completed because an input is unavailable, the package must record the limitation rather than assuming the missing input is current.

## Non-Authority Statement

Every evidence package must include this non-authority statement, or wording with the same meaning:

> This evidence package is a review artifact only. It does not approve, merge, close, automate, bypass human review, change repository settings, or authorize future automation. Human-reviewed controls remain mandatory.

The statement must be visible in PR evidence, closeout evidence, and documentation-sync handoffs.

## Required Evidence Sections

Each evidence package must include these sections unless the package type below narrows or expands the expectation:

- Issue and PR references: issue number, issue title, PR number or pending PR state, branch name, base branch, and relevant GitHub URLs when available.
- Purpose and package type: whether the package is for PR evidence, closeout evidence, or documentation-sync evidence.
- Freshness-check evidence: source documents reviewed, freshness findings, stale or missing documentation warnings, unavailable inputs, skipped checks, and escalation items.
- Required source document list: all source-of-truth docs, issue bodies, PR summaries, skill files, registry entries, validation docs, prompts, local operator packages, and human decisions reviewed.
- Touched-document list: docs changed by the current work, with a concise reason for each change.
- Diff and validation summary: changed-file summary, validation commands or manual checks performed, concise results, and any checks intentionally skipped.
- Human-review notes: review boundaries, approval requirements, human decisions already recorded, and decisions still required.
- Limitation and exception notes: unavailable inputs, out-of-scope findings, stale warnings not fixed in the current issue, known risks, and follow-up recommendations.
- Handoff notes: what the next agent, operator, validation reviewer, or human owner should inspect next.
- Non-authority statement: explicit confirmation that the package does not approve, merge, close, automate, or bypass review.

Evidence must distinguish confirmed facts, agent judgment, unavailable inputs, skipped checks, future recommendations, and human decisions.

## Required Freshness-Check Evidence

Documentation-sync evidence must show that `docs/agents/DOCUMENTATION_FRESHNESS_CHECKS.md` was used before documentation-sync work.

Required freshness evidence includes:

- The issue or PR scope reviewed.
- The source-of-truth documents reviewed before editing.
- Changed or planned files considered.
- Stale documentation findings, if any.
- Missing documentation findings, if any.
- Conflicting documentation findings, if any.
- Incomplete documentation findings, if any.
- Outdated build-state or roadmap findings, if any.
- Findings updated in the current change set.
- Findings deferred as warnings or follow-up recommendations.
- Human escalation items when uncertainty remains.
- Confirmation that the freshness check remained advisory, manual, and human-reviewed.

Freshness evidence is required before documentation-sync work. It is not an automated gate and does not authorize broad rewrites.

## PR Evidence Package

A PR evidence package supports human review of a pull request that includes documentation-sync work.

Required PR evidence:

- Summary of the documentation change and why it belongs to the issue.
- Files reviewed.
- Files changed.
- Documentation impact summary.
- Freshness-check summary.
- Evidence package model notes when the PR changes evidence package expectations.
- Validation performed, including command names and concise results.
- Skipped checks or unavailable inputs.
- Human-review boundary confirmation.
- Limitation, exception, or stale-warning notes.
- Issue references and PR references.
- Explicit confirmation that no automation, scripts, workflow changes, auto-merge, autonomous approval, autonomous issue closure, repository setting changes, branch protection changes, ruleset changes, secret changes, release changes, tag changes, or GitHub Project changes were performed.
- Explicit closeout language, including whether the PR closes no issue or intentionally uses normal GitHub close-on-merge wording.
- Non-authority statement.

PR evidence packages may support a merge recommendation by a reviewer, but they do not approve or merge the PR.

## Closeout Evidence Package

A closeout evidence package supports post-PR project-memory work after a human-reviewed PR has merged or when a human owner explicitly directs closeout preparation.

Required closeout evidence:

- Issue and PR references, including merge state when available.
- Source documents reviewed for closeout, especially `BUILD_STATE`, `AGENT_CONTEXT`, `ROADMAP`, relevant agent docs, relevant skills, validation docs, and issue or PR comments.
- Documentation freshness check summary for closeout-sensitive docs.
- Build-state and roadmap impact summary.
- Touched-document list for any closeout doc updates.
- Validation or manual checks performed after the closeout updates.
- Issue state evidence, including whether the issue remains open, closed by merge, or requires human-directed closure.
- Human-review notes and remaining owner decisions.
- Limitation or exception notes, including unavailable GitHub metadata or intentionally deferred docs.
- Handoff notes for the next active issue or next operator session.
- Non-authority statement.

Closeout evidence packages do not close issues by themselves. Any issue closure must happen through normal reviewed GitHub behavior or explicit human instruction.

## Documentation-Sync Evidence Package

A documentation-sync evidence package records the focused documentation update work performed by a documentation agent or human-directed implementation session.

Required documentation-sync evidence:

- Issue or task scope.
- Documentation impact classification.
- Freshness-check evidence used before editing.
- Required source document list.
- Touched-document list.
- Source-of-truth updates made.
- Stale, missing, conflicting, incomplete, or outdated documentation findings.
- Findings fixed, deferred, escalated, or marked out of scope.
- Diff and validation summary.
- Human-review notes.
- Limitation and exception notes.
- Handoff notes for validation, PR evidence, closeout, or the next agent.
- Non-authority statement.

Documentation-sync evidence packages are the bridge between the freshness check and the PR or closeout evidence. They explain why specific docs changed and which warnings remain.

## Reusable Handoff Template

The canonical reusable documentation-sync handoff package template is `docs/agents/DOCUMENTATION_SYNC_HANDOFF_TEMPLATE.md`.

Use the template when documentation-sync work needs a copy/paste-friendly handoff for an implementation agent, documentation agent, validation agent, local operator, or human owner. The template preserves the required separation between issue and PR references, source documents reviewed, freshness-check evidence, documentation impact, touched or expected documents, documentation-sync evidence, validation results, human-review boundaries, limitations, escalation items, handoff notes, and the required non-authority statement.

The template is a review artifact scaffold only. It does not execute this model, approve work, merge PRs, close issues, bypass human review, change repository settings, or authorize future automation.

## Relationship To Documentation Freshness Checks

Freshness checks are the diagnostic layer. Evidence packages record the diagnostic findings, the updates made from those findings, and the unresolved warnings or limitations.

The evidence package must cite the freshness check scope and results. It must not treat a freshness check as an automated gate or approval.

## Relationship To Documentation-Sync Skill

The documentation-sync skill at `.agent/skills/documentation-sync/SKILL.md` is the advisory skill that guides focused documentation updates.

The skill should require agents to prepare documentation-sync evidence after using the freshness check model and before handing work to PR evidence, closeout evidence, validation review, or the human owner.

During M2, the skill remains a repo-owned markdown guide. It does not execute this model.

## Relationship To Local Operator Workflow

The local operator workflow at `docs/architecture/LOCAL_OPERATOR_WORKFLOW.md` may prepare evidence package outlines for future human-reviewed work.

The future design targets `New-PrEvidencePackage` and `New-CloseoutEvidencePackage` describe intended package preparation roles only. They are not implemented commands during M2 and must not be invoked as existing tooling.

Operator-prepared evidence packages are review inputs. They do not stage, commit, push, create PRs, approve, merge, close, or automate work.

## Relationship To AGENT_CONTEXT

`docs/context/AGENT_CONTEXT.md` should identify this evidence package model as part of the M2 documentation-agent foundation. Future agents should treat it as a required review structure when documentation-sync work occurs.

The agent context must continue to preserve the M2 boundary: advisory, manual, human-reviewed documentation work only.

## Relationship To BUILD_STATE

`docs/context/BUILD_STATE.md` should record the current active documentation-sync foundation issue while evidence models or handoff templates are being defined and later record completion only after reviewed PR merge or explicit closeout evidence supports the update.

Build-state updates are high-churn project memory and must include evidence of source documents reviewed, validation performed, and any stale warnings or next-step handoff notes.

## Relationship To ROADMAP

`docs/roadmap/ROADMAP.md` should treat this evidence package model as an M2 foundation deliverable while it is in progress or completed.

The roadmap must not imply that evidence package generation is automated, that local operator commands exist, or that evidence packages replace human review.

## M2 Boundary

This model is documentation-agent foundation work only.

It must not be implemented as:

- A script.
- A command.
- A workflow.
- A watcher.
- A bot.
- A service.
- A merge gate.
- An approval gate.
- An issue closer.
- A repository setting.
- A branch protection rule.
- Autonomous documentation-sync automation.

Any future implementation of evidence package tooling requires a separate issue, explicit human approval, governance review, validation expectations, and source-of-truth documentation updates.
