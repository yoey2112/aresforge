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
| Milestone read/create/update | Roadmap tracking | GitHub API milestone calls | Partially confirmed |
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
