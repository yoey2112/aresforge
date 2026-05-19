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

## Safe GitHub Project/table read guidance

Before relying on GitHub Projects v2 data, confirm that the current token has the required project read scope:

```powershell
gh auth status
```

For the current AresForge environment, native `gh project` support is available, but project table metadata requires `read:project`. If `read:project` is missing, `gh project list --owner <owner> --format json` and GraphQL ProjectV2 queries can fail before any project number, fields, views, or items are returned.

Preferred read-only discovery pattern after `read:project` is available:

```powershell
gh project list --owner <owner> --format json
```

Then parse the returned JSON with PowerShell instead of using fragile shell-quoted jq expressions:

```powershell
$projectJson = gh project list --owner <owner> --format json
$projects = $projectJson | ConvertFrom-Json
```

After a project number is known, use read-only commands for project metadata:

```powershell
gh project view <project-number> --owner <owner> --format json
gh project field-list <project-number> --owner <owner> --format json
gh project item-list <project-number> --owner <owner> --format json
```

For GraphQL reads, place the query in a PowerShell here-string, pass variables with `-F`, and parse successful raw JSON with `ConvertFrom-Json`. Avoid `gh api --jq` for complex ProjectV2 reads unless quoting has been separately verified.

`gh issue view <issue-number> --json projectItems` can provide an issue-level project item summary, but an empty result does not prove project table access. Treat full project list, field, view, and item reads as blocked until `read:project` exists.

Do not create, edit, archive, delete, link, or unlink projects, fields, views, or project items during M1 unless a later human-approved issue explicitly authorizes that write. Future dashboard sync should start as read-only and should include a preflight check for `read:project`.

## Safe workflow run and artifact read guidance

Before relying on GitHub Actions run or artifact data, confirm the active issue allows workflow read validation and that the operation is read-only.

Recommended local and authentication preflight:

```powershell
git branch --show-current
git status --short
git log -1 --oneline
gh auth status
```

Check whether workflow files exist without creating or editing them:

```powershell
if (Test-Path .github/workflows) {
  Get-ChildItem .github/workflows -File | Select-Object -ExpandProperty Name
} else {
  'NO_WORKFLOW_DIRECTORY'
}
```

Read workflow run lists with:

```powershell
gh run list --repo <owner>/<repo> --limit 10
```

If the run list returns no rows, document that the command is available but the repository currently has no workflow runs. Treat no-run output as repository state, not as a failure. Do not create, add, enable, or trigger a workflow to manufacture validation data.

Inspect a workflow run only when one exists in `gh run list` output. Use a returned run ID:

```powershell
gh run view <run-id> --repo <owner>/<repo>
```

Check artifacts only when a run exists. Prefer a read-only run detail command that exposes artifact metadata when supported by the installed GitHub CLI:

```powershell
gh run view <run-id> --repo <owner>/<repo> --json databaseId,artifacts,conclusion,createdAt,event,headBranch,status,url,workflowName
```

If the installed CLI does not support the desired JSON fields, read the command help and document the exact read-only command that succeeds. Do not switch to write operations to work around missing read data.

Download artifacts only when all of these are true:

- A workflow run exists.
- Artifacts exist for that run.
- The active issue explicitly allows artifact download.
- The destination is a clearly named local validation folder under the repository.

Preferred validation download pattern:

```powershell
New-Item -ItemType Directory -Force .validation/issue-32-artifact-download
gh run download <run-id> --repo <owner>/<repo> --dir .validation/issue-32-artifact-download
```

Do not commit downloaded artifacts unless they are intentionally small text evidence and clearly appropriate for review. Prefer documenting the observed artifact names, counts, and download result instead.

Workflow run and artifact read validation must not create, edit, enable, disable, rename, delete, or trigger workflows. It must not change repository settings, branch protection, secrets, permissions, releases, tags, GitHub Projects, auto-merge, approvals, merges, destructive automation, or issue closure state.

## Safe branch protection and repository ruleset read guidance

Before relying on repository policy data, confirm the active issue allows branch protection or repository ruleset read validation and that the operation is read-only.

Recommended local and authentication preflight:

```powershell
git branch --show-current
git status --short
git log -1 --oneline
gh auth status
```

Read branch metadata before reading protection details:

```powershell
gh api repos/<owner>/<repo>/branches/<branch> --jq '{name: .name, protected: .protected, protection_url: .protection_url, commit_sha: .commit.sha}'
```

Expected evidence includes branch name, protected flag, protection URL, and commit SHA. If the branch metadata reports `protected: false`, the branch protection endpoint may return `Branch not protected` with HTTP 404. When confirmed by GitHub branch metadata, treat that response as a valid read result and observed repository state, not as a reusable command failure.

Read branch protection only for inspection:

```powershell
gh api repos/<owner>/<repo>/branches/<branch>/protection
```

If protection exists, summarize the returned read-only metadata. If protection does not exist, document the exact GitHub response. Do not create, edit, enable, disable, or delete branch protection to produce validation data.

Read repository rulesets only for inspection:

```powershell
gh api repos/<owner>/<repo>/rulesets
```

If the endpoint succeeds with an empty list, document that the repository currently returns no rulesets. Empty rulesets output is repository state, not a failure. If rulesets are returned, summarize their read-only metadata without changing enforcement, conditions, bypass actors, or targets.

Reading branch protection or repository rulesets does not authorize changing them. Repository policy writes require explicit human approval, a separate approved issue, and updated governance documentation when applicable.

Prefer raw JSON parsed with PowerShell `ConvertFrom-Json` for complex verification. Avoid fragile `gh api --jq` quoting patterns when verifying markers, body text, or nested state in Windows PowerShell.

Branch protection and repository ruleset read validation must not change repository settings, permissions, secrets, workflows, releases, tags, GitHub Projects, auto-merge, approvals, merges, destructive automation, or issue closure state.

## Safe release and tag lifecycle guidance

Before creating, reading, or deleting releases or tags, confirm the active issue explicitly authorizes release and tag lifecycle validation. Release and tag operations are normally outside routine M1 collaboration because they can affect release history, package consumers, and future automation triggers.

Recommended preflight:

```powershell
git branch --show-current
git status --short
git log -1 --oneline
gh release list --repo <owner>/<repo> --limit 20
git fetch --tags origin
git tag --list
git ls-remote --tags origin
```

For validation work, first confirm whether production releases or tags exist. If production releases or tags are present, do not modify them. Use a clearly issue-owned temporary validation tag and release name, and document the inventory before any write.

Safe temporary tag creation pattern:

```powershell
git tag <validation-tag-name>
git push origin <validation-tag-name>
```

Create the tag only after the issue branch documentation changes have been committed, and push only that exact validation tag. Do not create version-like production tags such as `v1.0.0` for validation.

Safe temporary release creation pattern:

```powershell
$notes = @'
Temporary M1 validation evidence for Issue #<issue-number>.

This release validates release and tag lifecycle operations and must be deleted before validation completes.
'@
$notes | gh release create <validation-tag-name> --repo <owner>/<repo> --title "<validation-release-title>" --notes-file - --prerelease --latest=false
```

Use `--prerelease` when appropriate so the temporary release does not look production-ready. Use `--latest=false` when the installed GitHub CLI supports it. If `--latest=false` is unsupported, stop and document the limitation before deciding whether the validation can continue safely.

Verify release and tag metadata before cleanup:

```powershell
gh release view <validation-tag-name> --repo <owner>/<repo> --json tagName,name,isDraft,isPrerelease,url,createdAt,publishedAt,targetCommitish
git ls-remote --tags origin <validation-tag-name>
gh release list --repo <owner>/<repo> --limit 20
```

Do not assume every release JSON field is available in every installed GitHub CLI version. In GitHub CLI 2.92.0, `gh release view --json isLatest` is not supported even though `gh release create --latest=false` is accepted. Keep `--latest=false` in the create command when supported, then verify the release with available fields and document the limitation when direct latest-state verification is unavailable.

Cleanup must target only the issue-owned temporary release and tag:

```powershell
gh release delete <validation-tag-name> --repo <owner>/<repo> --yes
git tag -d <validation-tag-name>
git push origin ":refs/tags/<validation-tag-name>"
```

After cleanup, verify final state:

```powershell
gh release list --repo <owner>/<repo> --limit 20
git tag --list <validation-tag-name>
git ls-remote --tags origin <validation-tag-name>
```

Final evidence should confirm whether any release remains, whether the validation tag exists locally or remotely, which commit the temporary tag targeted, and whether cleanup completed. Do not leave temporary validation releases or tags behind unless cleanup fails; if cleanup fails, document the exact failure and do not attempt broad deletion commands.

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
