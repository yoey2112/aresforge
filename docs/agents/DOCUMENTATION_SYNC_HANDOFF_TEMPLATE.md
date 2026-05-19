# AresForge Documentation-Sync Handoff Package Template

## Purpose

This document defines the reusable M2 documentation-sync handoff package template.

The template is copy/paste-friendly evidence scaffolding for an implementation agent, documentation agent, validation agent, local operator, or human owner when documentation-sync work is required.

During M2, this template is documentation-only, advisory, manually prepared, and human-reviewed. It does not create scripts, runnable automation, workflows, bots, watchers, merge gates, approval gates, autonomous issue closure, repository-setting changes, or future command implementations.

## When To Use This Template

Use this template when work requires documentation-sync evidence for:

- A pull request that changes source-of-truth docs.
- A handoff from an implementation agent to a documentation agent.
- A handoff from a documentation agent to a validation agent.
- A validation handoff to the human owner.
- A local operator package that prepares documentation-sync inputs.
- Closeout preparation that depends on documentation freshness or source-of-truth updates.

This template implements the evidence shape defined in `docs/agents/DOCUMENTATION_SYNC_EVIDENCE_PACKAGES.md` and must be used after the freshness check model in `docs/agents/DOCUMENTATION_FRESHNESS_CHECKS.md`.

## Required Non-Authority Statement

Every completed handoff package must include this statement:

> This evidence package is a review artifact only. It does not approve, merge, close, automate, bypass human review, change repository settings, or authorize future automation. Human-reviewed controls remain mandatory.

## Copy/Paste Template

```markdown
# Documentation-Sync Handoff Package

## Issue And PR References

- Issue:
  - Number:
  - Title:
  - URL:
  - State at handoff:
- Pull request:
  - Number:
  - Title:
  - URL:
  - State at handoff:
- Branch:
- Base branch:
- Relevant commit or range:
- Package prepared by:
- Package prepared on:

## Source-Of-Truth Documents Reviewed

- Active issue or task prompt:
- PR summary, comments, or review threads:
- docs/agents/DOCUMENTATION_AGENTS.md:
- docs/agents/DOCUMENTATION_FRESHNESS_CHECKS.md:
- docs/agents/DOCUMENTATION_SYNC_EVIDENCE_PACKAGES.md:
- docs/agents/DOCUMENTATION_SYNC_HANDOFF_TEMPLATE.md:
- docs/architecture/LOCAL_OPERATOR_WORKFLOW.md:
- docs/context/AGENT_CONTEXT.md:
- docs/context/BUILD_STATE.md:
- docs/roadmap/ROADMAP.md:
- .agent/AGENT_REGISTRY.md:
- .agent/skills/documentation-sync/SKILL.md:
- docs/prompts/CODEX_PROMPT_STANDARD.md:
- docs/learning/ERROR_PATTERNS.md:
- Other docs, issue comments, PR comments, validation notes, or human decisions reviewed:
- Unavailable source inputs:

## Documentation Freshness Check Summary

- Freshness check model used:
- Scope reviewed:
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
  - This freshness check was advisory, manual, and human-reviewed. It did not authorize broad rewrites, automation, approval, merge, or issue closure.

## Documentation Impact Summary

- Documentation impact classification:
- Confirmed source-of-truth updates required:
- Confirmed source-of-truth updates not required:
- Agent, skill, registry, prompt, governance, validation, roadmap, or build-state impact:
- Out-of-scope documentation impact:
- Reasoning:

## Changed Or Expected-To-Change Documents

| Document | Status | Reason | Owner or next reviewer |
|---|---|---|---|
|  | Changed / Expected / Not changed / Deferred |  |  |

## Documentation-Sync Evidence

- Documentation-sync package type:
- Source-of-truth updates made:
- Evidence supporting each update:
- Findings fixed:
- Findings deferred:
- Findings escalated:
- Findings marked out of scope:
- Diff summary:
- Review notes for documentation changes:

## Validation Commands And Results

| Command or check | Result | Notes |
|---|---|---|
| `git diff --check` |  |  |
| `git diff --cached --check` |  |  |
| `git status --short` |  |  |
| Changed-file review for issue scope |  |  |
| Boundary review for scripts, workflows, automation, repo settings, releases, tags, GitHub Projects, and issue-state changes |  |  |

## Human-Review Boundary Confirmation

- Human review remains required before approval or merge:
- This package does not approve the PR:
- This package does not merge the PR:
- This package does not close issues:
- This package does not bypass required review:
- This package does not change repository settings, branch protection, rulesets, secrets, releases, tags, workflows, or GitHub Projects:
- This package does not authorize future automation:
- Issue #39 state was preserved, if applicable:
- Local operator command names were treated as future design targets only, if applicable:

## Known Limitations, Skipped Checks, Unavailable Inputs, And Escalation Items

- Known limitations:
- Skipped checks and reason:
- Unavailable inputs:
- Stale warnings not fixed in this scope:
- Risks or assumptions:
- Escalation items for the human owner:
- Recommended follow-up issues or documentation tasks:

## Handoff Notes For Next Agent Or Human Owner

- Suggested next reviewer:
- What to inspect first:
- Decisions still needed:
- Validation or documentation evidence to preserve:
- Closeout notes:
- Next issue or next branch context:

## Required Non-Authority Statement

This evidence package is a review artifact only. It does not approve, merge, close, automate, bypass human review, change repository settings, or authorize future automation. Human-reviewed controls remain mandatory.
```

## Completion Guidance

When completing the template:

- Keep issue and PR references factual, including pending or unavailable states.
- List source-of-truth documents actually reviewed instead of assuming they were current.
- Preserve freshness findings even when they are warnings or deferred follow-ups.
- Separate documentation impact reasoning from validation results.
- Mark documents as changed, expected, deferred, or not changed so the next owner can see what remains.
- Record unavailable inputs, skipped checks, and human escalation items explicitly.
- Use the required non-authority statement verbatim.
- Avoid issue-closing language unless the human owner explicitly requests normal close-on-merge behavior.

## M2 Boundary

This template is a review artifact scaffold only.

It must not be implemented as:

- A script.
- A runnable command.
- A workflow.
- A watcher.
- A bot.
- A merge gate.
- An approval gate.
- An issue closer.
- A repository setting.
- A branch protection rule.
- A ruleset.
- A secret.
- A release or tag operation.
- A GitHub Project change.
- Autonomous documentation-sync automation.

Any future automation or command that prepares this template requires a separate issue, explicit human approval, governance review, validation expectations, and source-of-truth documentation updates.
