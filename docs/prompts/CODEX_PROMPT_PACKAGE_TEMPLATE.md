# AresForge Codex Prompt Package Template

## Purpose

This document defines the first reusable Codex prompt package template for AresForge M2 implementation work.

A Codex prompt package is a copy/paste-ready review input artifact that gathers issue scope, source-of-truth reading requirements, repository and branch context, validation expectations, documentation impact, evidence expectations, and human-review boundaries before an implementation agent begins work.

During M2, this template supports manually guided, manually reviewed work only. It does not implement `New-CodexPromptPackage`, create runnable automation, approve work, merge pull requests, close issues, bypass review, change repository settings, or authorize future automation.

## M2 Boundary

The prompt package template is documentation-only.

It may be manually copied, filled in, reviewed, and used as implementation-session input by a human owner or human-directed agent.

It must not be treated as:

- A script.
- A runnable command.
- A workflow.
- A watcher.
- A bot.
- A service.
- A merge gate.
- An approval gate.
- An issue closer.
- A repository setting.
- A branch protection rule.
- A ruleset.
- A secret.
- A release or tag operation.
- A GitHub Project change.
- Autonomous implementation, documentation-sync, validation, approval, merge, or issue-closure behavior.

Local operator command names, including `New-CodexPromptPackage`, remain future design targets only during M2 unless a later human-approved issue explicitly implements them.

## When To Use This Template

Use this template when preparing a reusable Codex implementation prompt package for:

- A GitHub issue implementation session.
- Documentation-only implementation work.
- Local operator workflow preparation.
- A follow-up session on an existing implementation branch.
- A handoff from a human owner, local operator, documentation agent, or validation agent to an implementation agent.
- Work that requires explicit source-of-truth reading, validation evidence, documentation impact reasoning, and PR evidence expectations.

This template is not required for simple read-only questions, brainstorming, or informal notes that do not ask an agent to change repository files, run validation, commit, push, or open a pull request.

## Required Non-Authority Statement

Every completed prompt package must include this statement:

> This prompt package is a review/input artifact only. It does not approve, merge, close, automate, bypass human review, change repository settings, or authorize future automation. Human-reviewed controls remain mandatory.

The statement must remain visible in implementation prompts and PR evidence when a prompt package shaped the work.

## Copy/Paste Template

```markdown
# Codex Prompt Package

## Task

- Task:
- Issue number:
- Issue title:
- Issue URL:

## Repository Context

- Repository:
- Repository path:
- Base branch:
- Current main commit:
- Open PR state:
- Open issue state:
- Branch name:

## Purpose And M2 Boundary

- Purpose of this package:
- M2 boundary:
  - This package is documentation/input only.
  - This package does not approve implementation.
  - This package does not merge a PR.
  - This package does not close an issue.
  - This package does not authorize automation.
  - This package does not bypass human review.
  - Local operator command names remain future design targets only during M2.

## When To Use This Package

- Intended implementation session:
- Intended agent or reviewer:
- Inputs this package organizes:
- Conditions that make this package applicable:
- Conditions where this package should not be used:

## Required Source-Of-Truth Reading List

- Active issue body or human task prompt:
- docs/context/AGENT_CONTEXT.md:
- docs/context/BUILD_STATE.md:
- docs/roadmap/ROADMAP.md:
- docs/prompts/CODEX_PROMPT_STANDARD.md:
- docs/prompts/CODEX_PROMPT_PACKAGE_TEMPLATE.md:
- docs/architecture/LOCAL_OPERATOR_WORKFLOW.md:
- docs/agents/DOCUMENTATION_AGENTS.md:
- docs/agents/DOCUMENTATION_FRESHNESS_CHECKS.md:
- docs/agents/DOCUMENTATION_SYNC_EVIDENCE_PACKAGES.md:
- docs/agents/DOCUMENTATION_SYNC_HANDOFF_TEMPLATE.md:
- .agent/AGENT_REGISTRY.md:
- .agent/skills/documentation-sync/SKILL.md:
- docs/learning/ERROR_PATTERNS.md:
- Other issue-specific source-of-truth docs:
- Unavailable source inputs:

## Issue And PR Context

- Issue number:
- Issue title:
- Issue URL:
- Issue state at package preparation:
- Issue labels:
- Issue milestone:
- Related issues:
- Pull request number:
- Pull request title:
- Pull request URL:
- Pull request state:
- Open PR state:
- Issue closure expectation:
- Issues that must remain unchanged:

## Branch And Repository Context

- Repository owner/name:
- Repository path:
- Current branch before implementation:
- Required branch name:
- Base branch:
- Current main commit:
- Expected commit message:
- Expected PR base branch:
- Expected PR draft state:
- Required staging boundary:

## Scope And Non-Scope

- Implementation goal:
- Required changes:
- Out-of-scope changes:
- Files likely to change:
- Files that must not change:
- Historical records to preserve:
- Related open issues that must remain open or unchanged:

## Required Implementation Task

- Required implementation task:
- Required documentation-only, code, configuration, or validation classification:
- Required new files:
- Required modified files:
- Required behavior or documentation outcome:
- Completion criteria:

## Documentation Freshness Check

- Freshness check scope:
- Source docs reviewed before editing:
- Changed or planned files considered:
- Stale documentation findings:
- Missing documentation findings:
- Conflicting documentation findings:
- Incomplete documentation findings:
- Outdated build-state or roadmap findings:
- Findings updated in this change set:
- Findings deferred as warnings or follow-up recommendations:
- Human escalation items:
- Freshness boundary confirmation:
  - The freshness check remains advisory, manual, and human-reviewed.

## Documentation Impact

- Documentation impact classification:
- Required documentation updates:
- Documentation updates not required and why:
- Prompt standard impact:
- Local operator workflow impact:
- Agent context impact:
- Build-state impact:
- Roadmap impact:
- Agent registry or skill impact:
- Governance or validation impact:
- Out-of-scope documentation warnings:

## Validation Commands

- Required validation commands:
  - `git status --short`
  - `git diff --check`
  - `git diff --cached --check` before commit
- Issue-specific validation commands:
- Manual review checks:
  - Changed-file review for issue scope.
  - Boundary review confirming no scripts, workflows, automation, repository settings, releases, tags, GitHub Projects, or protected issue-state changes were performed.
- Commands that must not be run:
- Skipped checks and reason:

## PR Evidence Requirements

The PR body must include:

- Summary.
- Source-of-truth documents reviewed.
- Documentation freshness check evidence.
- Files changed and why.
- Validation results.
- Human-review boundary confirmation.
- Explicit issue-state confirmations, including protected open issues that were not modified or closed.
- Explicit confirmation that future local operator command names were not implemented.
- Explicit confirmation that no scripts, workflows, automation, commands, repository settings, releases, tags, GitHub Projects, or autonomous behavior were introduced.
- Non-authority statement.

## Human-Review Boundary Confirmation

- Human review remains required before approval or merge:
- This package does not approve implementation:
- This package does not approve the PR:
- This package does not merge the PR:
- This package does not close issues:
- This package does not bypass required review:
- This package does not change repository settings, branch protection, rulesets, secrets, releases, tags, workflows, or GitHub Projects:
- This package does not authorize future automation:
- This package does not implement local operator commands:
- Protected issue state to preserve:

## Required Non-Authority Statement

This prompt package is a review/input artifact only. It does not approve, merge, close, automate, bypass human review, change repository settings, or authorize future automation. Human-reviewed controls remain mandatory.

## Completion Guidance For Implementation Agents

- Read all required source-of-truth documents before editing.
- Inspect the working tree before editing and before staging.
- Make only issue-scoped changes.
- Preserve historical completed issue records.
- Preserve protected open issues unless the human owner explicitly directs otherwise.
- Keep local operator command names as future design targets only during M2.
- Do not create scripts, workflows, automation, commands, bots, watchers, services, auto-merge, autonomous approval, autonomous issue closure, repository setting changes, releases, tags, or GitHub Project changes unless a later human-approved issue explicitly requires them.
- Run and report the required validation commands and manual reviews.
- Stop immediately if `git diff --check` or `git diff --cached --check` fails.
- Stage only intended files.
- Commit only after validation succeeds.
- Open a draft PR when requested, but do not merge it.
- Do not manually close issues unless the human owner explicitly directs that action.
- Include the required non-authority statement in the final evidence.
```

## Completion Guidance

When preparing a prompt package:

- Keep issue, PR, branch, and commit references factual.
- List exact source-of-truth files instead of broad document categories.
- Record unavailable inputs rather than assuming they are current.
- Separate required changes from out-of-scope changes.
- Include validation commands as commands to run, not as proof that validation has already passed.
- Include documentation freshness and documentation impact sections even when the expected result is no update.
- Preserve explicit human-review and non-authority statements.
- Confirm protected issues that must remain open or unchanged.
- Avoid issue-closing language unless the human owner explicitly requests normal close-on-merge behavior.

## Prohibited Interpretations

A prompt package must never be treated as:

- Approval to implement.
- Approval to stage or commit.
- Approval to push a branch.
- Approval to open a pull request unless the human-directed task explicitly requests it.
- Approval to merge a pull request.
- Permission to close an issue.
- Permission to modify unrelated issue state.
- Permission to enable automation.
- Permission to bypass human review.
- Permission to change repository settings, branch protection, rulesets, secrets, workflows, releases, tags, or GitHub Projects.
- Evidence that local operator command names are implemented.

Any future implementation that generates prompt packages with a command such as `New-CodexPromptPackage` requires a separate issue, explicit human approval, governance review, validation expectations, and source-of-truth documentation updates.
