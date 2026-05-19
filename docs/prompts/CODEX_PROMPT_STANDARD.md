# AresForge Codex Prompt Standard

## Purpose

This standard defines how implementation work should be handed to Codex or another coding agent inside AresForge.

It exists so future implementation sessions are structured, safe, document-driven, reviewable, and able to produce usable validation evidence for the human owner and pull request reviewers.

During M0, this standard supports manually guided, manually reviewed work. It does not authorize destructive automation, auto-merge, autonomous issue closure, or autonomous project management.

## When To Use This Standard

Use this standard for every AresForge implementation prompt that asks an agent to change repository files, run validation, create a commit, or open a pull request.

This standard should be used for:

- GitHub issue implementation prompts.
- Documentation implementation prompts.
- Code, configuration, test, workflow, or prompt-standard changes.
- Follow-up prompts that continue work on an existing implementation branch.
- Handoff prompts for the next implementation session.

This standard is not required for simple read-only questions, brainstorming, or human-authored notes that do not ask an agent to modify the repository.

## Source-Of-Truth Reading Rules

Implementation agents must read the relevant source-of-truth documentation before coding or editing docs.

Every implementation prompt should list exact files under a `Read first` section. At minimum, prompts should include the files that define the current project state, agent operating rules, affected domain, and issue-specific requirements.

For M0 implementation work, agents should usually read:

- docs/context/AGENT_CONTEXT.md
- docs/context/BUILD_STATE.md
- Relevant roadmap, architecture, governance, prompt, validation, or agent documentation.
- The issue body or task prompt supplied by the human owner.

Agents must treat GitHub and repository documentation as the temporary source of truth until the AresForge dashboard exists. During M0, explicit human decisions and repository documentation take priority over AI-generated summaries or inferred automation behavior.

## Required Prompt Sections

Each implementation prompt should include:

1. `Task`: The issue number, title, and short implementation request.
2. `Repository`: The repository name and, when useful, local path.
3. `Branch`: The required working branch or branch naming expectation.
4. `Context`: The relevant project phase, source-of-truth assumptions, and why the work matters.
5. `Read first`: Exact source-of-truth files and issue inputs to inspect before editing.
6. `Goal`: The successful end state.
7. `Required changes`: The specific files, behaviors, or docs expected to change.
8. `Constraints`: Safety, scope, governance, and autonomy limits.
9. `Documentation expectations`: Required documentation updates or explicit notes when no docs should change.
10. `Validation`: Exact commands, checks, or manual review steps to run.
11. `Commit expectations`: Commit message and staging expectations.
12. `PR expectations`: Target branch, PR title, PR body sections, and issue-closing language.
13. `Evidence to report back`: The final evidence the agent must provide to the human owner.

## Required Safety Constraints

Every prompt should tell the agent to:

- Read source-of-truth documentation before coding or editing docs.
- Avoid unrelated changes.
- Keep changes small, focused, and reviewable.
- Preserve historical context unless the issue explicitly replaces it.
- Respect the M0 constraint that all work is manually guided and manually reviewed.
- Avoid destructive local commands unless explicitly approved by the human owner.
- Avoid auto-merge, autonomous issue closure, or autonomous write operations outside the requested implementation work.
- Avoid changing repository visibility, permissions, secrets, runner security settings, or release state unless the issue explicitly requires it and the human owner approves it.
- Do not stage unrelated files.
- Do not overwrite intentional human decisions.
- Escalate to the human owner when safety, scope, source-of-truth, or approval boundaries are unclear.

## Rules For Avoiding Unrelated Changes

Agents must inspect the working tree before editing and before staging.

If unrelated local changes are present, the agent must leave them untouched and stage only files required for the current issue. If unrelated changes are mixed into the same file and cannot be safely separated, the agent must explain the conflict and ask the human owner how to proceed.

Agents should not reformat unrelated files, rename unrelated sections, update generated artifacts, or make opportunistic cleanup changes unless the issue explicitly asks for that work.

## Required Documentation Requirements

Implementation prompts must describe the expected documentation impact.

Every implementation must either:

- Update the relevant documentation as part of the change, or
- State why no documentation update is required.

Documentation updates are required when the work changes:

- Project state, current phase, active issue status, blockers, or next steps.
- Agent responsibilities, handoff expectations, prompt format, or operating rules.
- Architecture, system boundaries, runtime assumptions, integrations, or data flow.
- Roadmap scope, sequencing, completion criteria, or milestone status.
- Governance, autonomy boundaries, approval gates, escalation paths, or source-of-truth rules.
- Validation standards, evidence requirements, PR review expectations, or release-facing behavior.

During M0, documentation changes must remain manually reviewed and must not imply that automation, auto-merge, or autonomous closure is enabled.

## Required Validation Evidence Requirements

Every implementation prompt must require validation evidence that is appropriate to the change.

For documentation-only changes, validation evidence may be limited to:

- `git diff --check`
- `git status --short`
- Any issue-specific documentation review checks requested by the human owner.

For code, workflow, or behavior changes, validation should include the most relevant tests, build checks, lint checks, local manual checks, screenshots, logs, or local AI review output available for the change.

Validation evidence must include:

- The commands or checks run.
- The concise result of each command or check.
- Any skipped checks and why they were skipped.
- Known limitations or risks that remain after validation.

## Required PR Evidence Expectations

Pull request bodies must include enough evidence for manual review.

Every implementation PR should include:

- `Summary`: What changed and why.
- `Files changed`: The intended files or areas touched.
- `Validation performed`: Commands or checks run and their results.
- `Evidence`: Branch, commit, validation output, screenshots, logs, or other review evidence relevant to the change.
- `Risk notes`: Known risks, assumptions, skipped checks, or follow-up recommendations.
- Issue linkage such as `Closes #N` when the PR should close the issue after merge.

During M0, PR evidence must not imply that a PR is accepted, merged, or issue-closing until the human owner reviews and merges it.

## Branch, Commit, And PR Naming Expectations

Implementation prompts should specify naming expectations.

Default branch naming:

- Use `codex/issue-N-short-description` for issue implementation branches.
- Use a focused descriptive branch name when no issue number exists.

Default commit expectations:

- Use one focused commit for narrow implementation issues when practical.
- Use a concise imperative message, such as `Expand Codex prompt standard`.
- Stage only files that belong to the issue.

Default PR expectations:

- Target `main` unless the human owner specifies another base branch.
- Use a concise PR title that matches the implemented scope.
- Include the required PR evidence sections.
- Include `Closes #N` only when the PR should close the linked issue after merge.
- Do not enable auto-merge or merge the PR during M0 unless the human owner explicitly instructs it.

## Rules For Human Escalation

Agents must escalate to the human owner before proceeding when:

- The requested work conflicts with source-of-truth documentation.
- The issue scope is ambiguous enough that a reasonable implementation could cause unrelated changes.
- Validation fails and the fix is outside the issue scope.
- Required credentials, secrets, permissions, or external approvals are missing.
- The work appears to require destructive commands, auto-merge, autonomous issue closure, or repository security changes.
- The agent discovers unrelated local changes that block safe staging or editing.
- The agent cannot produce required validation evidence.

Escalation should be specific. The agent should name the blocker, the affected files or commands, and the decision needed from the human owner.

## Rules For Evidence Reporting Back To The Human Owner

At the end of implementation work, the agent must report:

- Branch name.
- Commit hash.
- PR URL, if a PR was created.
- Files changed.
- Validation command output or concise command results.
- Documentation impact.
- Risks, assumptions, skipped checks, and follow-up recommendations.

If any requested deliverable was not completed, the agent must state that clearly and explain the blocker.

## Baseline Prompt Template

Task:
[Issue #N: issue title]

Implement [short description of the requested change].

Repository:
[owner/repository]

Branch:
[codex/issue-N-short-description]

Context:
[Summarize the project phase, temporary source of truth, relevant completed work, and why this issue matters.]

Read first:
- [Exact source-of-truth file]
- [Exact source-of-truth file]
- [Issue body or other required input]

Goal:
[Define the successful end state in concrete terms.]

Required changes:
1. [File or area]: [specific expected change]
2. [File or area]: [specific expected change]
3. [File or area]: [specific expected change]

Constraints:
- Do not make unrelated changes.
- Do not enable destructive automation.
- Do not introduce auto-merge, autonomous issue closure, or autonomous write operations beyond the requested implementation work.
- Preserve the M0 constraint that all work is manually guided and manually reviewed.
- Preserve historical context unless the issue explicitly replaces it.
- Stage only files that belong to this issue.
- Escalate to the human owner if source-of-truth documentation conflicts with the issue or if safe implementation is unclear.

Validation:
- [Exact command or check]
- [Exact command or check]

Documentation expectations:
- [Documentation file]: [required update]
- [Documentation file]: [required update]
- If no other docs are required, state why.

Commit expectations:
- Commit message: [Focused imperative commit message]

PR expectations:
- Target branch: main
- PR title: [Focused PR title]
- PR body must include:
  - Summary
  - Files changed
  - Validation performed
  - Evidence
  - Risk notes
  - Closes #N

Evidence to report back:
- Branch name
- Commit hash
- PR URL
- Files changed
- Validation command output
- Documentation impact
- Risks, assumptions, skipped checks, or follow-up recommendations
