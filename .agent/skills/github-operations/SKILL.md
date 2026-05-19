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

## Safe issue creation guidance for Windows PowerShell

Before repeating a GitHub CLI, API, or Windows PowerShell pattern that previously failed, consult `docs/learning/ERROR_PATTERNS.md` for durable lessons and safer manual workarounds.

When a human-approved task requires creating a GitHub issue during M1, use a conservative manual pattern that can be verified after each step:

1. Resolve the target milestone through `gh api`.
2. Parse the milestone response with PowerShell JSON handling.
3. Create the issue with `gh issue create`.
4. Capture the issue URL returned by the command.
5. Extract the issue number from the returned URL.
6. Patch the issue milestone by milestone number through `gh api`.
7. Verify the final issue state with `gh issue view --json`.
8. Add an evidence comment when the operation discovers reusable command lessons, limitations, or safety guidance.

Preferred milestone assignment uses the GitHub milestone number or API-backed milestone identifier rather than shell-level title matching. This is especially important for milestone titles that contain punctuation or characters that may display differently across shells.

Avoid relying on `gh issue create --json` in the current AresForge environment because the installed GitHub CLI does not support that option.

Avoid relying on fragile `gh api --jq` expressions for milestone discovery in Windows PowerShell when quoting or escaping makes the result unreliable. Prefer raw API output parsed with PowerShell JSON handling.

Avoid direct JSON payload posting through temporary files unless encoding is intentionally controlled and verified. For routine issue creation, use `gh issue create` for the initial issue and an API-backed patch for milestone assignment.

When a GitHub operation reveals a repeatable failure, shell limitation, encoding risk, or safer workaround, document the lesson in `docs/learning/ERROR_PATTERNS.md` or update an existing entry. During M1, these entries are advisory, manually reviewed, and do not authorize autonomous GitHub operations.

## Execution boundaries

This skill is advisory and manually executed. It may guide commands that are already allowed by the active issue, but it is not a script, workflow, package, or autonomous GitHub operator.

## Human approval boundaries

Explicit human approval is required before changing repository visibility, permissions, secrets, runner settings, release state, branch protection, auto-merge settings, or any autonomy boundary.

## Documentation impact

Review docs/context/BUILD_STATE.md when GitHub work changes active issue, branch, PR, milestone, blockers, validation status, or next steps. Review docs/context/AGENT_CONTEXT.md, docs/learning/ERROR_PATTERNS.md, and governance docs when GitHub operating rules or repeatable error guidance change.

## Validation expectations

For documentation-only GitHub operation changes, run the issue-requested checks such as `git status --short`, `git diff --check`, and any tree listing or GitHub evidence commands requested by the task.

## Evidence requirements

Report branch name, commit hash when created, PR URL when created, files changed, commands run, command results, skipped checks, and any remaining risks or human decisions needed.

## Related docs

- docs/context/PROJECT_CONTEXT.md
- docs/context/AGENT_CONTEXT.md
- docs/context/BUILD_STATE.md
- docs/learning/ERROR_PATTERNS.md
- docs/governance/SELF_MANAGEMENT_MODEL.md
- docs/governance/PR_VALIDATION_MODEL.md
- docs/prompts/CODEX_PROMPT_STANDARD.md

## Lifecycle status

Draft
