# AresForge Build State

## Current Phase

M1 - GitHub Operations Validation

## Current Goal

Continue M1 by validating safe GitHub-managed workflows using repo-owned documentation, issues, milestones, labels, branches, pull requests, and human-reviewed evidence.

## Current Active Issue

- Issue #30 - Validate GitHub project table access
  - Branch: m1/issue-30-project-table-access-validation
  - Draft PR: #31
  - Status: In progress; read-only GitHub Project/table access validation documented and draft PR opened for human review.
  - Current finding: repository project enablement and issue-level project item summaries are readable, but ProjectV2 lists, fields, views, and items are blocked until the token has `read:project`.

## Current Source of Truth

GitHub and repository documentation are the temporary source of truth until the AresForge dashboard exists.

During M1, explicit human decisions and repository documentation take priority over AI-generated summaries or inferred automation behavior.

## Completed

- GitHub repository created: yoey2112/aresforge
- Repository cloned locally to: C:\Projects\aresforge
- Baseline document-driven structure created
- Initial self-project context docs created
- M0 milestone created: M0 - Self-Bootstrap Foundation
- Baseline GitHub labels created
- First six M0 issues created and assigned to the M0 milestone:
  - #1 Validate GitHub capability operations
  - #2 Validate Ollama GitHub operation review
  - #3 Define documentation agent model
  - #4 Create AresForge self-project context
  - #5 Create Codex prompt standard
  - #6 Define PR validation and scoring model
- Issue #1 completed:
  - PR #7 created, merged, and auto-closed issue #1
  - GitHub capability validation documented at docs/validation/GITHUB_CAPABILITY_VALIDATION.md
  - Confirmed GitHub CLI authentication scopes: gist, read:org, repo, workflow
  - Confirmed repository metadata read access
  - Confirmed label inventory read access
  - Confirmed milestone inventory read access
  - Confirmed issue read access
  - Confirmed workflow run visibility command execution
  - Confirmed branch creation, commit, push, pull request creation, pull request metadata read, PR merge, branch deletion, and issue auto-closure
- Issue #2 completed:
  - PR #9 created, merged, and auto-closed issue #2
  - Ollama GitHub operation review validation documented at docs/validation/OLLAMA_GITHUB_OPERATION_REVIEW.md
  - Confirmed local Ollama model qwen2.5:32b can review captured GitHub operation outputs
  - Confirmed Ollama can produce structured Markdown validation evidence
  - Confirmed conservative validation decisions such as NEEDS_HUMAN_REVIEW are useful as evidence when documented with human assessment
  - Documented limitations around empty workflow run output, milestone title encoding/mojibake, and future need for workflow-triggered local Ollama validation
- Issue #3 completed:
  - PR #10 created, merged, and auto-closed issue #3
  - Documentation agent model expanded at docs/agents/DOCUMENTATION_AGENTS.md
  - Defined documentation agent responsibilities, required inputs, required outputs, update rules, stale documentation warnings, validation evidence expectations, M0 manual flow, risks, and anti-patterns
  - Updated AGENT_CONTEXT.md with the M0 documentation agent operating model
  - Preserved the M0 constraint that documentation agent work is manual and human-reviewed
- Issue #4 completed:
  - PR #11 created, merged, and auto-closed issue #4
  - AresForge self-project context expanded across project context, self-management, architecture, roadmap, and build-state documentation
  - Documented AresForge as its own first managed project
  - Documented GitHub plus repository documentation as the temporary source of truth
  - Documented future dashboard state fields
  - Documented next-chat handoff expectations
- Issue #5 completed:
  - Codex prompt standard expanded at docs/prompts/CODEX_PROMPT_STANDARD.md
  - Required implementation prompt sections, safety constraints, documentation requirements, validation evidence, PR evidence, naming expectations, source-of-truth reading rules, unrelated-change rules, human escalation rules, and owner evidence reporting rules documented
  - AGENT_CONTEXT.md updated to require Codex implementation agents to follow the prompt standard
  - Preserved the M0 constraint that implementation work remains manually guided and manually reviewed
- Issue #6 completed:
  - PR validation and scoring model expanded at docs/governance/PR_VALIDATION_MODEL.md
  - Required validation agents, agent responsibilities, scoring categories, suggested scoring scale, evidence requirements, risk handling, safeguards, escalation rules, and merge-readiness decision states documented
  - AGENT_CONTEXT.md updated to require future QA, Test, Documentation, and PR Scoring agents to use the PR validation model when evaluating implementation work
  - Future 90 percent auto-merge concept documented as future behavior only
  - Preserved the M0 constraint that no auto-merge, autonomous issue closure, or autonomous approval is enabled
- Issue #8 completed via PR #14:
  - Defined the AresForge-native repo-owned markdown skills model
  - Evaluated external skill frameworks as optional inspiration or future adapters only
  - Linked the skill model to agent context, documentation agents, self-management governance, and PR validation expectations
  - Confirmed no external framework dependency, runnable skill automation, auto-merge, autonomous approval, or autonomous issue closure was introduced
- Issue #15 completed via PR #16:
  - Created `.agent/AGENT_REGISTRY.md`
  - Created the first six draft skill files under `.agent/skills/`
  - Updated BUILD_STATE.md, AGENT_CONTEXT.md, and AGENT_SKILLS_MODEL.md
  - Kept all skills advisory, manually executed, and human-reviewed until future governance approves automation

- Issue #18 completed via PR #19:
  - Documented repeatable GitHub issue lifecycle validation
  - Captured the reliable Windows PowerShell issue creation pattern using `gh issue create`, returned URL parsing, milestone-number patching, and final `gh issue view --json` verification
  - Documented failed or fragile approaches including unsupported `gh issue create --json`, fragile quoted `gh api --jq` milestone discovery, and temp-file JSON encoding issues
  - Updated GitHub operations and issue-planning skills with advisory/manual issue creation guidance
  - Corrected current-phase references in the self-management model for M1
  - Confirmed no runnable automation, auto-merge, autonomous approval, destructive automation, or autonomous issue closure was introduced

- Issue #20 completed via PR #21:
  - Created canonical learning document at docs/learning/ERROR_PATTERNS.md
  - Defined when repeatable errors must be promoted from chat/output into durable documentation
  - Captured required learning-entry fields including observed facts, suspected causes, confirmed causes, workarounds, fixes, validation expectations, and update targets
  - Seeded M1 learning entries for GitHub CLI, PowerShell, temp JSON payload, markdown encoding, special-character repair, verification mismatch, and ASCII-safe operational state patterns
  - Updated relevant skills, AGENT_CONTEXT.md, SELF_MANAGEMENT_MODEL.md, CODEX_PROMPT_STANDARD.md, and BUILD_STATE.md
  - Confirmed learning capture remains advisory/manual during M1 and does not enable runnable automation, auto-merge, autonomous approval, destructive automation, or autonomous issue closure

- Issue #22 completed via PR #23:
  - Documented repeatable GitHub label lifecycle validation
  - Validated safe label read, create, update, apply-to-issue, remove-from-issue, and verification operations
  - Updated GitHub operations skill with label lifecycle guidance
  - Added M1-ERROR-008 for multiline gh pr create --body argument splitting in Windows PowerShell
  - Confirmed no destructive label deletion, production label edits, runnable automation, auto-merge, autonomous approval, destructive automation, or autonomous issue closure was introduced

- Issue #24 completed via PR #25:
  - Documented repeatable GitHub pull request lifecycle validation
  - Validated safe branch creation, draft PR creation, multiline PR body handling, PR metadata read expectations, changed files verification, commit count verification, base/head branch verification, draft/open/closed state verification, mergeability read limitations, and evidence comment expectations
  - Updated GitHub operations skill with PR lifecycle guidance
  - Confirmed the safe Windows PowerShell pattern for multiline PR bodies: here-string body piped to gh pr create --body-file -
  - Confirmed no runnable automation, auto-merge, autonomous approval, destructive automation, repository setting change, branch protection change, workflow change, or autonomous issue closure was introduced
- Issue #26 completed via PR #27:
  - Documented repeatable GitHub milestone lifecycle validation.
  - Validated safe milestone metadata reads, creation of a non-production validation milestone, metadata update, close/reopen verification, and final reopened state verification.
  - Created temporary validation milestone `validation: issue-26-milestone-lifecycle` as milestone number 3 and left it open with no assigned issues.
  - Updated GitHub operations skill with milestone lifecycle guidance.
  - Confirmed production milestones were not renamed, closed, deleted, or otherwise altered.
  - Confirmed no runnable automation, auto-merge, autonomous approval, destructive automation, repository setting change, branch protection change, workflow change, milestone deletion, or autonomous issue closure was introduced.
- Issue #28 completed via PR #29:
  - Documented repeatable GitHub issue evidence/comment lifecycle validation.
  - Validated adding one clearly owned validation comment, reading comments through GitHub API output, identifying the validation comment by returned comment ID, URL, author, and unique marker, updating only that owned comment, and verifying body, author, URL, created_at, and updated_at metadata.
  - Added M1-ERROR-009 for `gh api --jq` marker checks failing with hyphenated issue-comment markers when quoting is not safely preserved for jq parsing.
  - Documented the safer PowerShell pattern: read raw `gh api` JSON, parse with `ConvertFrom-Json`, then verify marker presence with PowerShell string methods.
  - Updated GitHub operations skill with issue comment lifecycle guidance.
  - Confirmed no comment deletion, production comment edit, runnable automation, auto-merge, autonomous approval, destructive automation, repository setting change, branch protection change, workflow change, or autonomous issue closure was introduced.
## In Progress

- Issue #30:
  - Validated current GitHub CLI version, auth scopes, native `gh project` command availability, repository `has_projects` metadata, Issue #30 project item summary, and read-only REST/GraphQL limitations.
  - Confirmed current token scopes are `gist`, `read:org`, `repo`, and `workflow`; `read:project` is not present.
  - Confirmed `gh project list --owner yoey2112 --format json` and GraphQL ProjectV2 metadata reads are blocked by missing `read:project`.
  - Confirmed no GitHub Project settings, fields, views, or items were modified.

## Next

- Leave Issue #30 draft PR review, merge, approval, and issue closure to the human-reviewed process.
- After Issue #30 is human-reviewed and merged, select the next M1 GitHub operations validation issue.

## Current Operating Constraint

All M1 changes are manually guided and manually reviewed.

No runnable automation, auto-merge, autonomous approval, destructive automation, or autonomous issue closure is enabled during M1.
