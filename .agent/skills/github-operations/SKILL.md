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

## Safe milestone lifecycle guidance

Before changing milestones, read the existing repository milestone inventory and preserve enough evidence for review.

Recommended read commands:

```powershell
gh api repos/yoey2112/aresforge/milestones
gh api repos/yoey2112/aresforge/milestones?state=all
```

Use milestone numbers or API URLs returned by GitHub for all write operations. Avoid title matching for milestone writes because shell quoting, punctuation, and display encoding can make title-based matching fragile.

For M1 validation, create or update only clearly named non-production milestones such as `validation: issue-26-milestone-lifecycle`. Avoid changing production milestones unless the active issue explicitly requires it and the human owner has approved the scope.

Recommended create pattern:

```powershell
gh api repos/<owner>/<repo>/milestones -X POST -f title='<validation-milestone-name>' -f description='<clear validation description>' -f state='open'
```

After creation, record the returned milestone number and API URL. Verify the created milestone with an explicit read:

```powershell
gh api repos/<owner>/<repo>/milestones/<milestone-number>
```

Recommended metadata update pattern:

```powershell
gh api repos/<owner>/<repo>/milestones/<milestone-number> -X PATCH -f description='<updated validation description>'
```

After update, verify that the exact milestone number has the intended metadata and that production milestones were not changed.

Close and reopen a validation milestone only when an API read confirms the milestone is clearly non-production and has no assigned open or closed issues:

```powershell
gh api repos/<owner>/<repo>/milestones/<milestone-number> -X PATCH -f state='closed'
gh api repos/<owner>/<repo>/milestones/<milestone-number>
gh api repos/<owner>/<repo>/milestones/<milestone-number> -X PATCH -f state='open'
gh api repos/<owner>/<repo>/milestones/<milestone-number>
```

The final verification should confirm:

- The validation milestone title, number, API URL, description, and state.
- `state` is `open` after reopen.
- `closed_at` is `null` after reopen.
- `open_issues` and `closed_issues` remain unchanged from the expected validation state.
- Production milestones were not renamed, closed, deleted, or otherwise altered.

Avoid deleting milestones during M1 unless a separate human-approved issue or explicit human approval authorizes deletion. Milestone deletion is destructive because it can affect historical planning evidence, issue organization, roadmap reconstruction, and future project-state synchronization.

Update `docs/learning/ERROR_PATTERNS.md` only when milestone lifecycle work discovers a real repeatable failure pattern, such as a GitHub API limitation, PowerShell quoting issue, encoding problem, unsafe title-matching behavior, or a safer workaround future agents should reuse. Do not invent an error pattern for a clean validation run.

## Safe label lifecycle guidance

Before changing labels, read the current repository label inventory and the target issue label state.

Recommended read commands:

```powershell
gh label list --limit 100 --json name,description,color
gh issue view <issue-number> --json number,title,state,labels,milestone,url
```

For M1 validation, create or update only clearly named non-critical labels such as `validation: issue-22-label-lifecycle`. Avoid changing production labels unless the active issue explicitly requires it and the human owner has approved the scope.

Recommended create pattern:

```powershell
gh label create "<validation-label-name>" --description "<clear validation description>" --color <RRGGBB>
```

Recommended update pattern:

```powershell
gh label edit "<validation-label-name>" --description "<updated validation description>" --color <RRGGBB>
```

Verify label creation or update after the command. If `gh label list --search` returns fuzzy matches, confirm the exact label name, description, and color in the returned JSON before treating the validation as successful.

Apply labels to issues only when the issue scope allows it:

```powershell
gh issue edit <issue-number> --add-label "<validation-label-name>"
```

Remove labels from issues when cleanup is part of the validation:

```powershell
gh issue edit <issue-number> --remove-label "<validation-label-name>"
```

After applying or removing a label, verify the issue state:

```powershell
gh issue view <issue-number> --json number,title,state,labels,milestone,url
```

The verification should confirm the target label is present after application, absent after removal, and that unrelated labels remain intact.

Avoid deleting labels during M1 unless a separate human-approved issue or explicit human approval authorizes deletion. Label deletion is destructive because it can affect historical issues, pull requests, filtering, and future project-state evidence.

Update `docs/learning/ERROR_PATTERNS.md` only when label lifecycle work discovers a real repeatable failure pattern, such as a GitHub CLI limitation, PowerShell quoting issue, encoding problem, fuzzy-match verification risk that caused incorrect evidence, or a safer workaround future agents should reuse. Do not invent an error pattern for a clean validation run.

## Safe pull request body guidance for PowerShell

When creating pull requests with multiline evidence, command examples, quotes, or Markdown backticks in Windows PowerShell, avoid passing a complex body variable directly to `gh pr create --body` if the shell may split or reinterpret the content.

Prefer piping the body to standard input and using `--body-file -`:

```powershell
$body = @'
Closes #<issue-number>

## Summary

...
'@
$body | gh pr create --draft --title "<title>" --body-file - --base main --head <branch-name>
```

Avoid this pattern when the body is multiline or contains quotes, backticks, command examples, issue evidence, or other shell-sensitive content:

```powershell
gh pr create --draft --title "<title>" --body $body --base main --head <branch-name>
```

Create draft pull requests by default during M1 unless the active issue or human owner explicitly requests a ready-for-review PR:

```powershell
$body | gh pr create --draft --title "<title>" --body-file - --base main --head <branch-name>
```

After creating the PR, verify that the PR body rendered with the intended evidence sections before treating PR creation evidence as complete.

Always verify pull request metadata after creation or after any metadata update:

```powershell
gh pr view <number> --json number,title,state,isDraft,baseRefName,headRefName,changedFiles,commits,mergeable,url
```

The verification should confirm the PR number, title, state, draft status, base branch, head branch, changed files, commit count, mergeability read result, and URL. Treat `mergeable` as advisory metadata because GitHub can report delayed, unknown, or stale mergeability while background checks update.

Do not merge, approve, enable auto-merge, mark ready for review, or close linked issues unless explicitly human-approved and allowed by the current phase rules. During M1, pull request lifecycle validation remains manually guided and manually reviewed.

## Safe issue evidence comment lifecycle guidance

Before creating or updating issue evidence comments, read the target issue state and confirm the active issue scope allows comment operations.

For M1 validation, create only clearly owned evidence comments with a unique marker that identifies the active issue and validation purpose. Prefer `gh issue comment` for initial creation when it returns a usable HTML URL:

```powershell
$body = @'
ARESFORGE-ISSUE-28-COMMENT-LIFECYCLE-VALIDATION

Initial validation comment for Issue #28 comment lifecycle evidence.
'@
$body | gh issue comment 28 --body-file -
```

After creation, read comments through the GitHub API and identify the owned validation comment by returned metadata:

```powershell
gh api repos/yoey2112/aresforge/issues/28/comments
```

For single-comment verification after a comment ID is known, prefer an explicit comment ID or API URL read:

```powershell
$commentJson = gh api "repos/yoey2112/aresforge/issues/comments/<comment-id>"
$comment = $commentJson | ConvertFrom-Json
$marker = "ARESFORGE-ISSUE-28-COMMENT-LIFECYCLE-VALIDATION"
$comment.body.Contains($marker)
```

Use raw JSON parsed with PowerShell for marker checks in Windows PowerShell. Avoid complex `gh api --jq` string `contains(...)` expressions for hyphenated markers unless the jq expression and shell quoting have been separately verified, because unsafe quoting can cause jq parser failures.

Required identification evidence includes:

- Comment `id`.
- Comment API `url`.
- Comment `html_url`.
- Author `user.login`.
- Unique marker in `body`.
- `created_at` and `updated_at`.

Update comments only when the returned metadata proves the comment is clearly owned by the active validation task. Prefer the returned comment ID or API URL over body-text guessing:

```powershell
$updatedBody = @'
ARESFORGE-ISSUE-28-COMMENT-LIFECYCLE-VALIDATION

Updated validation comment for Issue #28 comment lifecycle evidence.
'@
gh api repos/yoey2112/aresforge/issues/comments/<comment-id> -X PATCH -f body="$updatedBody"
```

After any update, run another explicit API read and verify:

- The same comment ID was updated.
- The author and URLs still match the intended comment.
- The updated body contains the expected marker and content.
- `created_at` remains unchanged.
- `updated_at` is later than `created_at`.
- No delete endpoint was used.
- No production or historical evidence comments were edited.

Do not delete issue comments during M1 unless a separate human-approved issue or explicit human approval authorizes deletion. Treat comment deletion as destructive because it can remove review evidence, historical decisions, and audit context.

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
