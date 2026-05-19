# GitHub Capability Validation

## Purpose

This document validates the GitHub operations AresForge needs in order to become a self-managed software factory.

This validation belongs to:

- Milestone: M0 — Self-Bootstrap Foundation
- Issue: #1 Validate GitHub capability operations
- Phase: Self-bootstrap foundation

## Validation Goals

AresForge must be able to safely perform and document the following GitHub operations:

1. Read repository metadata.
2. Read and update issues.
3. Create and update labels.
4. Read, create, and update milestones.
5. Create branches.
6. Commit and push changes.
7. Open pull requests.
8. Read pull request metadata.
9. Read workflow runs.
10. Read workflow artifacts.
11. Add issue evidence comments.
12. Close issues after acceptance criteria are satisfied.
13. Identify permission gaps before automation depends on them.

## Required GitHub Operations

| Capability | Required For | Validation Method | Status |
|---|---|---|---|
| Repository metadata read | Project context and repo validation | GitHub CLI/API query | Pending |
| Issue read | Agent intake and planning | gh issue view | Confirmed |
| Issue update | Labels, milestone, closure, evidence | GitHub CLI/API patch or comment | Pending |
| Label read/create/update | Routing and governance | gh label list/create/edit or API | Pending |
| Milestone read/create/update | Roadmap tracking | GitHub API milestone calls | Confirmed |
| Branch create | Isolated implementation work | Local git branch creation | Confirmed |
| Commit and push | Deliver implementation changes | Git commit and push | Pending |
| Pull request create/read | Review and merge workflow | gh pr create/view | Pending |
| Workflow run read | Automation validation | gh run list/view | Pending |
| Artifact read/download | Evidence collection | gh run download | Pending |
| Project board/table access | Delivery board sync | GitHub Projects API/CLI check | Pending |
| Issue closure | Done-state automation | gh issue close or API patch | Pending |

## Current Confirmed Evidence

### Local Repository State

- Local path: C:\Projects\aresforge
- Active branch at validation start: main
- Remote: https://github.com/yoey2112/aresforge.git
- Local status before issue branch creation: clean
- Latest baseline commit: e9f78c0 Update build state after M0 GitHub setup

### Issue #1 State

Issue #1 was confirmed open with:

- Title: Validate GitHub capability operations
- Milestone: M0 — Self-Bootstrap Foundation
- Labels:
  - type: validation
  - phase: m0
  - agent: devops
  - risk: level-1
  - evidence: required

### Branch Validation

Created working branch: m0/issue-1-github-capability-validation

Result: confirmed.

## Permission and Limitation Tracking

| Area | Current Finding | Impact | Follow-up |
|---|---|---|---|
| GitHub CLI auth | Authenticated as yoey2112 | Allows repo operations from Ares | Confirm scopes |
| Milestone assignment | -F milestone=1 works through gh api | Safe method for issue milestone patching | Document as preferred method |
| Long dash milestone names | gh issue list --milestone may be unreliable in PowerShell | API confirmation should be preferred | Use milestone number/API for validation |
| Project board/table access | Not yet validated | May affect automated board sync | Test later in issue #1 |

## Validation Plan

The rest of this issue should validate the following in order:

1. Capture current GitHub CLI authentication scopes.
2. Confirm repository metadata access.
3. Confirm label inventory access.
4. Confirm milestone inventory access.
5. Push this validation branch.
6. Open a pull request linked to issue #1.
7. Confirm pull request metadata can be read.
8. Confirm workflow run visibility.
9. Add evidence back to issue #1.
10. Merge after review.
11. Close issue #1 only after acceptance criteria are met.

## Acceptance Criteria Mapping

| Acceptance Criteria | Evidence Location | Status |
|---|---|---|
| A validation plan is documented. | This document | Complete |
| Required GitHub operations are listed. | Required GitHub Operations section | Complete |
| Current GitHub CLI permissions are documented. | GitHub CLI Authentication Evidence section | Complete |
| Any missing permissions or limitations are captured. | Permission and Limitation Tracking section | In progress |
| Evidence is added to the issue before closure. | Issue #1 evidence comment | Pending |

## GitHub CLI Authentication Evidence

Captured during issue #1 validation.

Authentication summary:

- Host: github.com
- Account: yoey2112
- Credential storage: keyring
- Active account: true
- Git operations protocol: https
- Token scopes:
  - gist
  - read:org
  - repo
  - workflow

Result: GitHub CLI authentication status captured for permission baseline.

## GitHub Read Operation Evidence

Captured during issue #1 validation.

### Repository Metadata

Repository metadata read succeeded.

Summary:

{"default_branch":"main","full_name":"yoey2112/aresforge","name":"aresforge","private":false,"visibility":"public"}

### Label Inventory

Label inventory read succeeded.

Observed labels:

bug	Something isn't working	#d73a4a documentation	Improvements or additions to documentation	#0075ca duplicate	This issue or pull request already exists	#cfd3d7 enhancement	New feature or request	#a2eeef good first issue	Good for newcomers	#7057ff help wanted	Extra attention is needed	#008672 invalid	This doesn't seem right	#e4e669 question	Further information is requested	#d876e3 wontfix	This will not be worked on	#ffffff type: documentation	Documentation work	#0075CA type: validation	Validation or proof task	#5319E7 phase: m0	M0 Self-Bootstrap Foundation	#0E8A16 type: governance	Governance, standards, or controls	#D93F0B agent: devops	DevOps or GitHub automation agent	#1D76DB agent: local-ai	Local AI or Ollama validation agent	#5319E7 agent: architect	Architecture or governance agent	#B60205 agent: documentation	Documentation agent	#0052CC risk: level-1	Low risk, human-guided	#C2E0C6 evidence: required	Requires validation evidence	#FBCA04

### Milestone Inventory

Milestone inventory read succeeded.

Summary:

[{"closed_issues":0,"number":1,"open_issues":6,"state":"open","title":"M0 ΓÇö Self-Bootstrap Foundation"}]

### Issue Read

Issue #1 read succeeded.

Summary:

{"labels":["type: validation","phase: m0","agent: devops","risk: level-1","evidence: required"],"milestone":"M0 ΓÇö Self-Bootstrap Foundation","number":1,"state":"OPEN","title":"Validate GitHub capability operations"}

### Workflow Run Visibility

Workflow run list command completed.

Summary:



Result: GitHub read operations for repository metadata, labels, milestones, issues, and workflow runs were validated from Ares.

## Pull Request Metadata Evidence

Captured during issue #1 validation.

Pull request metadata read succeeded.

Summary:

{"baseRefName":"main","changedFiles":["docs/validation/GITHUB_CAPABILITY_VALIDATION.md"],"commitCount":1,"headRefName":"m0/issue-1-github-capability-validation","mergeable":"MERGEABLE","number":7,"reviewDecision":"","state":"OPEN","title":"Document GitHub capability validation for issue 1","url":"https://github.com/yoey2112/aresforge/pull/7"}

Result: Pull request creation and metadata read access were validated from Ares.

## M1 Repeatable GitHub Issue Lifecycle Validation

This section extends the original M0 GitHub capability validation for M1.

This validation belongs to:

- Milestone: M1 — GitHub Operations Validation
- Issue: #18 Validate repeatable GitHub issue lifecycle operations using GitHub operations skill
- Phase: GitHub operations validation

### Issue #18 Creation Evidence

Issue #18 was created manually during M1 to validate a repeatable GitHub issue lifecycle operation.

Confirmed issue state:

- Issue number: #18
- Title: Validate repeatable GitHub issue lifecycle operations using GitHub operations skill
- State: OPEN
- Milestone: M1 — GitHub Operations Validation
- Milestone number: 2
- Labels:
  - type: validation
  - phase: m1
  - agent: devops
  - risk: level-1
  - evidence: required
  - status: ready
- Issue URL: https://github.com/yoey2112/aresforge/issues/18

An evidence comment was added to issue #18 during issue creation. The comment records the discovered command limitations and the currently reliable issue creation pattern for future reuse.

Evidence comment:

- URL: https://github.com/yoey2112/aresforge/issues/18#issuecomment-4484073090
- Purpose: capture issue creation lessons before they are promoted into reusable project documentation.

### Successful Issue Creation Pattern

The reliable M1 issue creation pattern on Windows PowerShell is:

1. Resolve the target milestone through `gh api`.
2. Parse the milestone response with PowerShell JSON handling instead of relying on shell-quoted `--jq` expressions.
3. Create the issue with `gh issue create`.
4. Capture the returned issue URL.
5. Extract the issue number from the returned URL.
6. Patch the issue milestone by milestone number through `gh api`.
7. Verify the final issue state with `gh issue view --json`.
8. Add an evidence comment when the operation itself discovers reusable lessons or limitations.

This pattern is preferred because it separates issue creation from milestone assignment, uses GitHub's API for the milestone patch, and produces a verifiable final state.

### Preferred Milestone Assignment Pattern

Milestone assignment should prefer the GitHub milestone number or API-backed milestone identifier over title matching.

For issue #18, the target milestone was verified as:

- Milestone title: M1 — GitHub Operations Validation
- Milestone number: 2

The preferred assignment pattern is to create the issue first, then patch the milestone by number through `gh api`, and finally confirm the result through `gh issue view --json`.

This avoids fragile title matching, shell quoting issues, and display encoding differences for milestone names that include punctuation such as long dashes.

### Failed Or Fragile Approaches To Avoid

The issue #18 creation evidence identified these approaches as unsupported or fragile in the current environment:

| Approach | Finding | Preferred alternative |
|---|---|---|
| `gh issue create --json` | The installed GitHub CLI does not support this option. | Capture the issue URL returned by `gh issue create`, then extract the issue number from the URL. |
| `gh api --jq` with quoted expressions in Windows PowerShell | Quoted expressions can fail depending on shell parsing. | Use `gh api` output with PowerShell JSON parsing. |
| Direct JSON payload posting through temporary files | Payload posting can fail when file encoding is not handled carefully. | Use supported `gh issue create` flags for creation and `gh api` form fields or carefully verified API calls for updates. |
| Milestone title matching in shell commands | Title matching can be brittle when punctuation or encoding differs. | Resolve and patch by milestone number or API-backed milestone identifier. |

These limitations should be treated as validation findings, not as blockers. They define the safer manual pattern for future issue lifecycle operations and future automation design.

### Evidence Comment And Verification Expectations

For repeatable issue lifecycle validation during M1:

- Issue creation should leave enough evidence for a human reviewer to reconstruct the operation.
- Evidence comments should be added when the operation discovers reusable command patterns, limitations, or safety guidance.
- Final issue state should be verified with `gh issue view --json`.
- Verification should include issue number, title, state, labels, milestone title, milestone number when available, URL, and relevant evidence comment URL.
- Documentation should record both successful and failed approaches so future agents avoid repeating fragile command patterns.

### M1 Safety Confirmation

This validation introduced documentation and manual operating guidance only.

It did not introduce:

- Runnable automation.
- Auto-merge.
- Autonomous approval.
- Destructive automation.
- Autonomous issue closure.
- Autonomous issue creation.
- Repository permission, secret, branch protection, or release setting changes.

Issue #18 remains open until a human-reviewed PR is merged with valid issue-closing language.

## M1 Repeatable GitHub Label Lifecycle Validation

This section extends the original M0 GitHub capability validation for M1 label lifecycle operations.

This validation belongs to:

- Milestone: M1 - GitHub Operations Validation
- Issue: #22 Validate repeatable GitHub label lifecycle operations using GitHub operations skill
- Phase: GitHub operations validation

### Current M1 Safety Boundaries

During M1, label lifecycle work is manually guided, manually reviewed, and evidence-based.

Allowed label lifecycle operations for this validation are limited to:

- Reading repository labels.
- Creating one clearly named non-critical validation label when needed.
- Editing only that non-critical validation label.
- Applying only that validation label to issue #22.
- Removing only that validation label from issue #22.
- Verifying the final repository and issue state.

This validation must not:

- Delete existing production labels.
- Delete validation labels unless separately human-approved.
- Alter branch protection, repository settings, repository permissions, secrets, workflows, auto-merge, or release settings.
- Close issue #22 outside the normal human-reviewed PR merge process.
- Introduce runnable automation or autonomous label management.

### Label Read Pattern

The safe read pattern is to inspect labels before changing them and preserve the output as validation evidence.

Preferred commands:

```powershell
gh label list --limit 100 --json name,description,color
gh issue view 22 --json number,title,state,labels,milestone,url
```

Expected evidence:

- The command succeeds.
- The repository label inventory can be read.
- Issue #22 can be read with its current labels.
- The validation label name is checked before creation or update.

### Label Creation Pattern

For M1 validation, create only a clearly named non-critical validation label.

Validated label:

- Name: `validation: issue-22-label-lifecycle`
- Initial description: `Temporary validation label for Issue #22 label lifecycle evidence`
- Initial color: `5319E7`

Preferred command:

```powershell
gh label create "validation: issue-22-label-lifecycle" --description "Temporary validation label for Issue #22 label lifecycle evidence" --color 5319E7
```

Expected evidence:

- The command succeeds.
- The new label appears in a later label read.
- No existing production label is changed.

### Label Update Pattern

Update only the non-critical validation label created for the validation.

Validated update:

- Name: `validation: issue-22-label-lifecycle`
- Updated description: `Issue #22 validation label for manual lifecycle evidence`
- Updated color: `1D76DB`

Preferred command:

```powershell
gh label edit "validation: issue-22-label-lifecycle" --description "Issue #22 validation label for manual lifecycle evidence" --color 1D76DB
```

Verification command:

```powershell
gh label list --search "validation: issue-22-label-lifecycle" --json name,description,color
```

Expected evidence:

- The command succeeds.
- The exact validation label shows the updated description and color.
- If a search command returns fuzzy matches, the exact label name must be checked in the returned data.

### Label Application Pattern

Apply only the validation label to the validation issue.

Preferred command:

```powershell
gh issue edit 22 --add-label "validation: issue-22-label-lifecycle"
```

Verification command:

```powershell
gh issue view 22 --json number,title,state,labels,milestone,url
```

Expected evidence:

- The command succeeds and returns the issue URL.
- Issue #22 includes `validation: issue-22-label-lifecycle` after application.
- Existing labels on issue #22 remain intact.

### Label Removal Pattern

Remove only the validation label from the validation issue.

Preferred command:

```powershell
gh issue edit 22 --remove-label "validation: issue-22-label-lifecycle"
```

Final verification command:

```powershell
gh issue view 22 --json number,title,state,labels,milestone,url
```

Expected evidence:

- The command succeeds and returns the issue URL.
- Issue #22 no longer includes `validation: issue-22-label-lifecycle`.
- Issue #22 keeps its original project labels.
- The validation label may remain in the repository label inventory unless human approval separately authorizes deletion.

### Final Verification Expectations

Final verification for issue #22 should confirm:

- Issue number: #22
- Issue state: OPEN
- Milestone: M1 - GitHub Operations Validation
- Labels include the original project labels:
  - `type: validation`
  - `phase: m1`
  - `agent: devops`
  - `risk: level-1`
  - `evidence: required`
  - `status: ready`
- Labels do not include `validation: issue-22-label-lifecycle` after removal.

### Evidence Requirements

PR or issue evidence for repeatable label lifecycle validation should include:

- Branch name.
- Files changed.
- Commands used or summarized.
- Result of label read validation.
- Result of label create and update validation.
- Result of label application and removal validation.
- Final `gh issue view` verification for issue #22.
- `git status --short` before commit and after commit.
- `git diff --check` result.
- Safety confirmation that no destructive label deletion, repository setting change, workflow automation, auto-merge, autonomous issue closure, or PR merge was performed.

### Fragile Or Failed Approaches

No reusable failed label lifecycle approach was encountered during issue #22 validation.

One practical caution was observed: `gh label list --search "validation: issue-22-label-lifecycle"` can return fuzzy matches in addition to the exact validation label. Future validation should confirm the exact label name in the returned JSON instead of assuming every returned row is the target label.

### Label Deletion Boundary

No destructive label deletion is required for this validation.

Deleting labels, including temporary or validation labels, should be avoided during M1 unless a separate human-approved issue or explicit human approval authorizes that deletion. Future automation design must treat label deletion as a destructive operation requiring stricter approval and evidence than read, create, update, apply, or remove-from-issue operations.

## M1 Repeatable GitHub Pull Request Lifecycle Validation

This section extends the original M0 GitHub capability validation for M1 pull request lifecycle operations.

This validation belongs to:

- Milestone: M1 - GitHub Operations Validation
- Milestone number: 2
- Issue: #24 Validate repeatable GitHub pull request lifecycle operations using GitHub operations skill
- Phase: GitHub operations validation

### Current M1 Safety Boundaries

During M1, pull request lifecycle work is manually guided, manually reviewed, and evidence-based.

Allowed pull request lifecycle operations for this validation are limited to:

- Creating a scoped implementation branch.
- Creating a draft pull request linked to the validation issue.
- Handling multiline pull request bodies safely in Windows PowerShell.
- Reading pull request metadata after creation.
- Updating pull request metadata only when needed to correct title, body, base branch, draft state, or review evidence.
- Verifying changed files, commit count, base branch, head branch, state, draft status, and URL.
- Reading mergeability as advisory metadata with known limitations.
- Adding issue evidence comments.

This validation must not:

- Merge the pull request.
- Approve the pull request.
- Enable auto-merge.
- Close issue #24 manually.
- Change branch protection, repository settings, secrets, permissions, workflows, or release settings.
- Introduce runnable automation, autonomous approval, destructive automation, or autonomous issue closure.

### Safe Pull Request Lifecycle Pattern

The preferred M1 pull request lifecycle pattern is:

1. Confirm the working tree is clean or contains only intentional issue-scoped changes.
2. Create a dedicated branch for the issue.
3. Make focused documentation or implementation changes.
4. Run local validation before commit.
5. Commit only issue-scoped files.
6. Push the issue branch.
7. Create a draft pull request linked to the issue.
8. Verify pull request metadata after creation.
9. Add an issue evidence comment summarizing branch, files changed, validation, PR pattern, reusable failures, and safety status.
10. Leave merge, approval, auto-merge, and issue closure to the human-reviewed process.

### Preferred Windows PowerShell Multiline Body Pattern

When creating a pull request with multiline Markdown evidence, command examples, quotes, or backticks in Windows PowerShell, use a here-string and pipe it to `gh pr create --body-file -`.

Preferred pattern:

```powershell
$body = @'
Closes #24

## Summary

- Documented repeatable PR lifecycle validation.
- Preserved M1 manual review boundaries.

## Validation performed

- git status --short
- git diff --check
'@

$body | gh pr create --draft --title "Validate PR lifecycle operations" --body-file - --base main --head m1/issue-24-pr-lifecycle-validation
```

Avoid this pattern for multiline evidence:

```powershell
gh pr create --draft --title "Validate PR lifecycle operations" --body $body --base main --head m1/issue-24-pr-lifecycle-validation
```

Passing complex multiline content directly through `--body $body` can be fragile in Windows PowerShell when the body includes quoted command examples, Markdown backticks, or other shell-sensitive content. Use `--body-file -` so GitHub CLI receives the intended body through standard input.

### Required Pull Request Verification Commands

After creating or materially updating a pull request, run:

```powershell
gh pr view <number> --json number,title,state,isDraft,baseRefName,headRefName,changedFiles,commits,mergeable,url
```

Before committing documentation-only pull request lifecycle changes, run:

```powershell
git status --short
git diff --check
```

Expected pull request metadata evidence:

- `number` matches the created or updated pull request.
- `title` matches the intended validation scope.
- `state` is `OPEN` for draft PRs awaiting human review, or `CLOSED` only when reading historical state.
- `isDraft` is `true` for M1 validation PRs unless a human explicitly requests otherwise.
- `baseRefName` is `main` unless the issue explicitly specifies another base.
- `headRefName` is the issue branch.
- `changedFiles` includes only issue-scoped files.
- `commits` supports commit count verification.
- `mergeable` is treated as advisory because GitHub can report delayed, unknown, or stale mergeability while background checks update.
- `url` is recorded for evidence.

### PR Metadata Update Guidance

Metadata updates are allowed only when they correct or complete review evidence within the active issue scope, such as:

- Fixing a title typo.
- Replacing or extending a body section.
- Correcting issue linkage.
- Keeping the PR as draft when human review is still pending.

After any metadata update, repeat the `gh pr view` verification command and record the relevant result in PR or issue evidence.

### Evidence Comment Expectations

Future PR lifecycle validations should add an issue evidence comment that includes:

- Branch name.
- Draft PR number and URL when available.
- Files changed.
- Validation commands run and concise results.
- Pull request lifecycle pattern documented or exercised.
- Confirmation that multiline PR body handling used `gh pr create --body-file -` when applicable.
- Any new reusable failure found, or an explicit statement that no new reusable failure was found.
- Safety confirmation that no merge, approval, auto-merge, autonomous issue closure, destructive repository setting change, branch protection change, secret change, permission change, workflow change, or release setting change was performed.

### M1 Safety Confirmation

This validation introduces documentation and manual operating guidance only.

It does not introduce:

- Runnable automation.
- Auto-merge.
- Autonomous approval.
- Destructive automation.
- Autonomous issue closure.
- Repository permission, secret, branch protection, workflow, or release setting changes.

## M1 Repeatable GitHub Milestone Lifecycle Validation

This section extends the original M0 GitHub capability validation for M1 milestone lifecycle operations.

This validation belongs to:

- Milestone: M1 - GitHub Operations Validation
- Milestone number: 2
- Issue: #26 Validate repeatable GitHub milestone lifecycle operations using GitHub operations skill
- Phase: GitHub operations validation

### Current M1 Safety Boundaries

During M1, milestone lifecycle work is manually guided, manually reviewed, and evidence-based.

Allowed milestone lifecycle operations for this validation are limited to:

- Reading existing repository milestone metadata.
- Creating one clearly named non-production validation milestone.
- Updating only that temporary validation milestone metadata.
- Closing and reopening only that temporary validation milestone when it has no assigned issues.
- Verifying every write with an explicit API read.
- Leaving the temporary validation milestone undeleted unless the human owner separately approves deletion.

This validation must not:

- Rename, close, delete, or otherwise alter production milestones.
- Assign production issues to the validation milestone.
- Delete the validation milestone without explicit human approval.
- Change repository settings, branch protection, secrets, permissions, workflows, releases, or project settings.
- Introduce runnable automation, auto-merge, autonomous approval, destructive automation, or autonomous issue closure.
- Close issue #26 manually.

### Milestone Read Pattern

Read existing milestone metadata before any milestone write and preserve the output as validation evidence.

Preferred commands:

```powershell
gh api repos/yoey2112/aresforge/milestones
gh api repos/yoey2112/aresforge/milestones?state=all
```

Expected evidence:

- The command succeeds.
- Production milestone numbers, titles, states, descriptions, and issue counts are visible.
- Future writes use the target milestone number or API URL returned by GitHub, not title matching.

### Milestone Creation Pattern

For M1 validation, create only a clearly named non-production milestone.

Validated milestone:

- Title: `validation: issue-26-milestone-lifecycle`
- Number: `3`
- API URL: `https://api.github.com/repos/yoey2112/aresforge/milestones/3`
- Initial description: `Temporary validation milestone for Issue #26 milestone lifecycle evidence`
- Initial state: `open`

Preferred command:

```powershell
gh api repos/yoey2112/aresforge/milestones -X POST -f title='validation: issue-26-milestone-lifecycle' -f description='Temporary validation milestone for Issue #26 milestone lifecycle evidence' -f state='open'
```

Verification command:

```powershell
gh api repos/yoey2112/aresforge/milestones/3
```

Expected evidence:

- The command succeeds.
- The created milestone has the intended non-production title.
- The created milestone returns a stable milestone number and API URL.
- `open_issues` and `closed_issues` are both `0` at creation.

### Milestone Metadata Update Pattern

Update only the validation milestone by milestone number or API URL.

Validated update:

- Number: `3`
- Updated description: `Updated temporary validation milestone for Issue #26 lifecycle evidence; safe to leave open after validation`

Preferred command:

```powershell
gh api repos/yoey2112/aresforge/milestones/3 -X PATCH -f description='Updated temporary validation milestone for Issue #26 lifecycle evidence; safe to leave open after validation'
```

Verification command:

```powershell
gh api repos/yoey2112/aresforge/milestones/3
```

Expected evidence:

- The command succeeds.
- The milestone title remains `validation: issue-26-milestone-lifecycle`.
- The description matches the intended updated description.
- The milestone state remains `open`.
- Production milestones are not changed.

### Milestone Close And Reopen Pattern

Close and reopen only the temporary validation milestone when the API read confirms it is safe to do so.

Precondition:

- The target milestone title is `validation: issue-26-milestone-lifecycle`.
- The target milestone number is `3`.
- `open_issues` is `0`.
- `closed_issues` is `0`.

Preferred close command:

```powershell
gh api repos/yoey2112/aresforge/milestones/3 -X PATCH -f state='closed'
```

Close verification command:

```powershell
gh api repos/yoey2112/aresforge/milestones/3
```

Preferred reopen command:

```powershell
gh api repos/yoey2112/aresforge/milestones/3 -X PATCH -f state='open'
```

Final verification command:

```powershell
gh api repos/yoey2112/aresforge/milestones/3
```

Expected evidence:

- The close command changes only milestone `3` to `closed`.
- The close verification shows `state` as `closed` and a populated `closed_at`.
- The reopen command changes only milestone `3` back to `open`.
- The final verification shows `state` as `open` and `closed_at` as `null`.
- `open_issues` and `closed_issues` remain `0`.
- A final all-state milestone read confirms production milestones remain open and the validation milestone is open.

### Final Verified State

Final milestone API verification for issue #26 confirmed:

- Temporary validation milestone title: `validation: issue-26-milestone-lifecycle`
- Temporary validation milestone number: `3`
- Temporary validation milestone API URL: `https://api.github.com/repos/yoey2112/aresforge/milestones/3`
- State: `open`
- Description: `Updated temporary validation milestone for Issue #26 lifecycle evidence; safe to leave open after validation`
- Open issues: `0`
- Closed issues: `0`
- Closed at: `null`

The temporary milestone was not deleted.

### Evidence Comment Expectations

Future milestone lifecycle validations should add an issue evidence comment that includes:

- Branch name.
- Temporary milestone title, number, API URL, and final state.
- Existing milestone read result summary.
- Create, update, close, reopen, and final read verification summaries.
- Confirmation that production milestones were not renamed, closed, deleted, or otherwise altered.
- Confirmation that milestone deletion was not performed.
- Any new reusable failure found, or an explicit statement that no new reusable failure was found.
- Safety confirmation that no repository setting, branch protection, secret, permission, workflow, release setting, project setting, auto-merge, autonomous approval, destructive automation, or autonomous issue closure change was performed.

### Milestone Deletion Boundary

No destructive milestone deletion is required for this validation.

Deleting milestones, including temporary validation milestones, should be avoided during M1 unless a separate human-approved issue or explicit human approval authorizes deletion. Future automation design must treat milestone deletion as a destructive operation requiring stricter approval and evidence than read, create, update, close, or reopen operations.

### M1 Safety Confirmation

This validation introduces documentation and manual operating guidance only.

It does not introduce:

- Runnable automation.
- Auto-merge.
- Autonomous approval.
- Destructive automation.
- Autonomous issue closure.
- Repository permission, secret, branch protection, workflow, project setting, or release setting changes.

## M1 Repeatable GitHub Issue Evidence Comment Lifecycle Validation

This section extends the M1 GitHub operations validation for issue evidence comment lifecycle operations.

This validation belongs to:

- Milestone: M1 - GitHub Operations Validation
- Milestone number: 2
- Issue: #28 Validate repeatable GitHub issue evidence comment lifecycle operations using GitHub operations skill
- Phase: GitHub operations validation

### Current M1 Safety Boundaries

During M1, issue evidence comment lifecycle work is manually guided, manually reviewed, and evidence-based.

Allowed issue evidence comment lifecycle operations for this validation are limited to:

- Reading the target issue state.
- Creating one clearly owned validation evidence comment on Issue #28.
- Reading issue comments through the GitHub API.
- Identifying the validation comment by returned comment ID, API URL, HTML URL, author, and unique marker.
- Updating only that clearly owned validation comment by returned comment ID or API URL.
- Verifying the updated body and metadata with an explicit read after write.
- Adding a final evidence comment to Issue #28.

This validation must not:

- Delete any issue comments.
- Edit or delete production or historical evidence comments.
- Modify unrelated issues, labels, milestones, pull requests, branches, repository settings, branch protection, secrets, workflows, permissions, project settings, or release settings.
- Introduce runnable automation, auto-merge, autonomous approval, destructive automation, or autonomous issue closure.
- Close Issue #28 manually.

### Comment Creation Pattern

For M1 validation, create only a clearly owned issue evidence comment with a unique marker.

Validated marker:

- `ARESFORGE-ISSUE-28-COMMENT-LIFECYCLE-VALIDATION`

Preferred creation pattern:

```powershell
$body = @'
ARESFORGE-ISSUE-28-COMMENT-LIFECYCLE-VALIDATION

Initial validation comment for Issue #28 comment lifecycle evidence.
'@
$body | gh issue comment 28 --body-file -
```

Expected evidence:

- The command succeeds.
- `gh issue comment` returns a usable HTML URL.
- The body includes a unique marker that distinguishes the validation comment from production or historical evidence comments.
- The comment is clearly owned by the active validation task.

### Comment Read And Identification Pattern

Read issue comments through the GitHub API after creation and before any update.

Preferred read command:

```powershell
gh api repos/yoey2112/aresforge/issues/28/comments
```

Expected evidence:

- The command succeeds.
- The target comment can be identified by returned `id`, `url`, `html_url`, `user.login`, and marker in `body`.
- The validation process records enough metadata for a human reviewer to reconstruct the operation.
- Future updates use the returned comment ID or API URL, not body-text guessing alone.

Validated comment metadata:

- Comment ID: `4484336358`
- API URL: `https://api.github.com/repos/yoey2112/aresforge/issues/comments/4484336358`
- HTML URL: `https://github.com/yoey2112/aresforge/issues/28#issuecomment-4484336358`
- Author: `yoey2112`
- Marker: `ARESFORGE-ISSUE-28-COMMENT-LIFECYCLE-VALIDATION`
- Created at: `2026-05-19T04:18:25Z`

### Comment Update Pattern

Update only the clearly owned validation comment by returned comment ID or API URL.

Preferred update pattern:

```powershell
$updatedBody = @'
ARESFORGE-ISSUE-28-COMMENT-LIFECYCLE-VALIDATION

Updated validation comment for Issue #28 comment lifecycle evidence.
'@
gh api repos/yoey2112/aresforge/issues/comments/4484336358 -X PATCH -f body="$updatedBody"
```

Expected evidence:

- The command succeeds.
- The returned `id`, `url`, `html_url`, and `user.login` still match the intended validation comment.
- The returned `body` contains the updated content and the unique marker.
- `created_at` remains unchanged.
- `updated_at` is later than `created_at`.
- No delete endpoint is used.
- No other comments are edited.

Validated update metadata:

- Comment ID: `4484336358`
- Author: `yoey2112`
- HTML URL: `https://github.com/yoey2112/aresforge/issues/28#issuecomment-4484336358`
- Created at: `2026-05-19T04:18:25Z`
- Updated at: `2026-05-19T04:18:42Z`

### Final Verification Expectations

Final verification for issue evidence comment lifecycle work should include:

- The target issue number and state.
- The validation comment marker.
- The validation comment ID, API URL, HTML URL, author, `created_at`, and `updated_at`.
- Confirmation that the updated comment body matches the intended validation content.
- Confirmation that no comments were deleted.
- Confirmation that production or historical evidence comments were not edited.
- Confirmation that unrelated GitHub resources were not modified.

### Evidence Comment Expectations

Future issue evidence comment lifecycle validations should add a final issue evidence comment that includes:

- Branch name.
- Draft PR number and URL when available.
- Validation comment marker.
- Validation comment ID and URL.
- Read, create, update, and final verification summary.
- Files changed.
- Local validation commands and concise results.
- Any new reusable failure found, or an explicit statement that no new reusable failure was found.
- Safety confirmation that no comment deletion, production comment edit, repository setting change, branch protection change, secret change, permission change, workflow change, project setting change, release setting change, auto-merge, autonomous approval, destructive automation, or autonomous issue closure was performed.

### Comment Deletion Boundary

No comment deletion is required for this validation.

Deleting issue comments, including temporary validation comments, should be avoided during M1 unless a separate human-approved issue or explicit human approval authorizes deletion. Future automation design must treat comment deletion as a destructive operation requiring stricter approval and evidence than read, create, or update operations.

### M1 Safety Confirmation

This validation introduces documentation and manual operating guidance only.

It does not introduce:

- Runnable automation.
- Auto-merge.
- Autonomous approval.
- Destructive automation.
- Autonomous issue closure.
- Repository permission, secret, branch protection, workflow, project setting, or release setting changes.
