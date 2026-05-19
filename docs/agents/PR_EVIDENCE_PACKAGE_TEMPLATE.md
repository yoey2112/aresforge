# AresForge PR Evidence Package Template

## Purpose

This document defines the reusable M2 PR evidence package template for AresForge implementation work.

A PR evidence package is a copy/paste-friendly review artifact that helps implementation agents, documentation agents, validation agents, local operators, and the human owner evaluate pull requests consistently.

During M2, this template is documentation-only, advisory, manually prepared, and human-reviewed. It does not create scripts, runnable automation, workflows, commands, bots, watchers, merge gates, approval gates, autonomous issue closure, repository-setting changes, branch protection changes, ruleset changes, secret changes, release or tag changes, GitHub Project changes, or future command implementations.

## When To Use This Template

Use this template when preparing PR evidence for:

- A documentation-only implementation PR.
- A code, configuration, validation, prompt, governance, architecture, roadmap, or context PR that needs consistent review evidence.
- A pull request that includes documentation-sync work.
- A handoff from an implementation agent to a documentation agent, validation agent, local operator, or human owner.
- Local operator workflow preparation for PR evidence.

This template implements the PR evidence package expectations defined in `docs/agents/DOCUMENTATION_SYNC_EVIDENCE_PACKAGES.md`. When documentation-sync work is involved, use the freshness check model before completing the freshness-check section.

## Required Non-Authority Statement

Every completed PR evidence package must include this statement:

> This PR evidence package is a review artifact only. It does not approve, merge, close, automate, bypass human review, replace human controls, change source-of-truth priority, or authorize future automation. Human-reviewed controls remain mandatory.

## Copy/Paste Template

```markdown
# PR Evidence Package

## Issue Reference

- Issue number:
- Issue title:
- Issue URL:
- Issue state at package preparation:
- Issue closure expectation:
- Protected or unrelated issues that must remain unchanged:
  - Issue #39 was not modified or closed:

## PR Reference

- Pull request number:
- Pull request title:
- Pull request URL:
- Pull request state:
- Draft status:
- Base branch:
- Reviewer or human-owner notes already recorded:

## Branch And Commit Context

- Repository:
- Local repository path:
- Working branch:
- Base branch:
- Current branch commit:
- Main or base commit reviewed before branching:
- Commit range reviewed:
- Commit message:
- Package prepared by:
- Package prepared on:

## Source-Of-Truth Documents Reviewed

- Active issue body or human task prompt:
- PR summary, comments, or review threads:
- docs/context/AGENT_CONTEXT.md:
- docs/context/BUILD_STATE.md:
- docs/roadmap/ROADMAP.md:
- docs/agents/DOCUMENTATION_AGENTS.md:
- docs/agents/DOCUMENTATION_FRESHNESS_CHECKS.md:
- docs/agents/DOCUMENTATION_SYNC_EVIDENCE_PACKAGES.md:
- docs/agents/DOCUMENTATION_SYNC_HANDOFF_TEMPLATE.md:
- docs/agents/PR_EVIDENCE_PACKAGE_TEMPLATE.md:
- docs/architecture/LOCAL_OPERATOR_WORKFLOW.md:
- docs/prompts/CODEX_PROMPT_STANDARD.md:
- docs/prompts/CODEX_PROMPT_PACKAGE_TEMPLATE.md:
- docs/learning/ERROR_PATTERNS.md:
- .agent/AGENT_REGISTRY.md:
- .agent/skills/documentation-sync/SKILL.md:
- Other source-of-truth docs, issue comments, PR comments, validation notes, or human decisions reviewed:
- Unavailable source inputs:

## Files Changed

| File | Change type | Reason | Review focus |
|---|---|---|---|
|  | Added / Modified / Removed / Renamed |  |  |

## Scope Summary

- Implementation goal:
- Work completed:
- Work intentionally not completed:
- Out-of-scope findings:
- Historical context preserved:
- Local operator command names treated as future design targets only, if applicable:

## Documentation Impact Summary

- Documentation impact classification:
- Source-of-truth documents updated:
- Source-of-truth documents reviewed but not changed:
- Documentation-before-closeout readiness:
- Agent, skill, registry, prompt, governance, validation, roadmap, or build-state impact:
- Documentation updates deferred:
- Reasoning:

## Freshness-Check Evidence

- Documentation-sync work involved:
- Freshness check model used:
- Scope reviewed:
- Changed files considered:
- Stale documentation findings:
- Missing documentation findings:
- Conflicting documentation findings:
- Incomplete documentation findings:
- Outdated build-state or roadmap findings:
- Findings updated in this PR:
- Findings deferred as warnings or follow-up recommendations:
- Human escalation items:
- Freshness boundary confirmation:
  - The freshness check was advisory, manual, and human-reviewed. It did not authorize broad rewrites, automation, approval, merge, bypass, source-of-truth priority changes, or issue closure.

## Validation Commands And Results

| Command or check | Result | Notes |
|---|---|---|
| `git diff --check` |  |  |
| `git diff --cached --check` |  |  |
| `git status --short` |  |  |
| Changed-file review for issue scope |  |  |
| Boundary review for scripts, runnable automation, workflows, commands, auto-merge, autonomous approval, autonomous issue closure, repository settings, branch protection, rulesets, secrets, releases, tags, GitHub Projects, and Issue #39 |  |  |

## Diff Review Summary

- Diff reviewed:
- Intended files only:
- Unrelated changes found:
- Formatting or whitespace issues:
- Source-of-truth consistency notes:
- Validation evidence preserved in PR body:

## Human-Review Notes

- Human review remains required before approval or merge:
- Human decisions already recorded:
- Decisions still required:
- Reviewer focus areas:
- Escalation items for the human owner:
- This package does not approve the PR:
- This package does not merge the PR:
- This package does not close issues:
- This package does not bypass required review:

## Known Limitations, Exceptions, Skipped Checks, And Unavailable Inputs

- Known limitations:
- Exceptions:
- Skipped checks and reason:
- Unavailable inputs:
- Assumptions:
- Remaining risks:
- Follow-up recommendations:

## Protected Issue And Repository Boundary Confirmations

- Issue #39 was not modified:
- Issue #39 was not closed:
- No automation, workflows, auto-merge, autonomous approval, autonomous issue closure, repository settings, branch protection, rulesets, secrets, releases, tags, or GitHub Projects were changed unless explicitly in scope:
- No scripts, runnable automation, commands, bots, watchers, services, merge gates, approval gates, or issue closers were introduced unless explicitly in scope:
- Source-of-truth priority was not changed:
- Human-reviewed M2 controls were preserved:
- Evidence packages, handoff packages, and prompt packages were not treated as authority:

## Required Non-Authority Statement

This PR evidence package is a review artifact only. It does not approve, merge, close, automate, bypass human review, replace human controls, change source-of-truth priority, or authorize future automation. Human-reviewed controls remain mandatory.
```

## Completion Guidance

When completing the template:

- Keep issue, PR, branch, and commit references factual, including pending or unavailable states.
- List source-of-truth documents actually reviewed instead of assuming they were current.
- Include freshness-check evidence whenever documentation-sync work is involved.
- Separate documentation impact, validation results, diff review, human-review notes, and limitations.
- Record skipped checks and unavailable inputs explicitly.
- Confirm whether Issue #39 was modified or left unchanged.
- Confirm whether any automation, workflows, commands, auto-merge, autonomous approval, autonomous issue closure, repository settings, branch protection, rulesets, secrets, releases, tags, or GitHub Projects changed.
- Preserve explicit human-review boundaries and the required non-authority statement.
- Avoid issue-closing language unless the human owner explicitly requests normal close-on-merge behavior.

## M2 Boundary

This template is a review artifact scaffold only.

It must not be implemented as:

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
- Autonomous implementation, documentation-sync, validation, approval, merge, bypass, or issue-closure behavior.

Evidence packages may support human review, but they do not grant approval, merge, close, automation, bypass, source-of-truth priority, or future automation authority.

Any future automation or command that prepares this template, including future local operator design targets such as `New-PrEvidencePackage`, requires a separate issue, explicit human approval, governance review, validation expectations, and source-of-truth documentation updates.
