# GitHub Operations Skill

## Name

GitHub operations

## Purpose

Guide safe, evidence-based GitHub work for AresForge issues, branches, commits, pull requests, labels, milestones, and repository-state checks.

## When to use

Use this skill when an approved task asks an agent to inspect or update GitHub-managed project state, create an implementation branch, open a pull request, collect GitHub evidence, or summarize issue and PR state for review.

## When not to use

Do not use this skill to bypass human review, change repository permissions, configure secrets, publish releases, enable auto-merge, approve pull requests, or close issues outside normal human-reviewed merge behavior.

## Inputs

- Human-approved issue or task scope.
- Current branch and working-tree status.
- Relevant GitHub issue, PR, label, milestone, and repository metadata.
- Source-of-truth documentation listed in the agent registry.
- Validation evidence requested by the issue or prompt.

## Outputs

- Scoped branch, commit, push, or draft PR actions when requested.
- Concise GitHub state summaries.
- Evidence of commands or GitHub operations performed.
- Warnings when credentials, permissions, branch state, or scope boundaries are unclear.

## Scope boundaries

This skill covers routine repository collaboration tasks for AresForge. It does not authorize repository administration, release publishing, branch deletion outside approved cleanup scope, security setting changes, or workflow changes.

## Execution boundaries

This skill is advisory and manually executed. It may guide commands that are already allowed by the active issue, but it is not a script, workflow, package, or autonomous GitHub operator.

## Human approval boundaries

Explicit human approval is required before changing repository visibility, permissions, secrets, runner settings, release state, branch protection, auto-merge settings, or any autonomy boundary.

## Documentation impact

Review docs/context/BUILD_STATE.md when GitHub work changes active issue, branch, PR, milestone, blockers, validation status, or next steps. Review docs/context/AGENT_CONTEXT.md and governance docs when GitHub operating rules change.

## Validation expectations

For documentation-only GitHub operation changes, run the issue-requested checks such as `git status --short`, `git diff --check`, and any tree listing or GitHub evidence commands requested by the task.

## Evidence requirements

Report branch name, commit hash when created, PR URL when created, files changed, commands run, command results, skipped checks, and any remaining risks or human decisions needed.

## Related docs

- docs/context/PROJECT_CONTEXT.md
- docs/context/AGENT_CONTEXT.md
- docs/context/BUILD_STATE.md
- docs/governance/SELF_MANAGEMENT_MODEL.md
- docs/governance/PR_VALIDATION_MODEL.md
- docs/prompts/CODEX_PROMPT_STANDARD.md

## Lifecycle status

Draft
