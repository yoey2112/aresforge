# AresForge Local Operator Workflow

## Purpose

This document defines the first AresForge local operator workflow.

The local operator workflow is a design-only documentation model for preparing repeatable, human-reviewed implementation work on a local machine. It describes how AresForge should reduce manual copy/paste across Codex, Windows PowerShell, GitHub CLI, validation notes, and PR evidence while preserving explicit human control.

During Issue #47, this document does not implement scripts, commands, workflows, tools, automation, autonomous repository behavior, auto-merge, autonomous approval, or autonomous issue closure.

## Problem It Solves

Current AresForge implementation sessions require humans and agents to copy issue context, source-of-truth files, branch names, validation commands, PR evidence, and closeout notes between GitHub, Codex, PowerShell, and documentation.

That manual flow is reviewable, but it creates repeated risks:

- Missing required source-of-truth documents before editing.
- Losing issue constraints while moving between tools.
- Repeating fragile GitHub CLI or PowerShell patterns.
- Forgetting documentation freshness checks before documentation-sync work.
- Producing inconsistent PR evidence.
- Blurring the line between future automation ideas and current human-reviewed behavior.

The local operator workflow should package the same information more consistently without removing human approval gates.

## What The Local Operator Workflow Is

The local operator workflow is a future local assistance layer that prepares implementation context, validation checklists, and evidence packages for human-guided AresForge work.

It should act as an operator helper, not an autonomous agent.

The workflow may prepare:

- Issue implementation context.
- Codex prompt packages.
- Worktree validation checklists.
- Pull request evidence packages.
- Closeout evidence packages.
- Documentation-sync evidence packages.
- Documentation freshness findings.
- Documentation-sync inputs.
- Follow-up recommendations for human review.

The workflow must keep repository documentation, GitHub issue state, validation evidence, and human decisions visible to the human owner before any material repository action is taken.

## What The First Version Should Do

The first version should be designed to:

- Read an issue scope and identify required source-of-truth documents.
- Prepare a Codex-ready implementation prompt package using `docs/prompts/CODEX_PROMPT_STANDARD.md`.
- List the expected working branch, changed-file targets, constraints, validation commands, and PR evidence sections.
- Run or guide manual documentation freshness review before documentation-sync work.
- Produce evidence summaries that a human can paste into a PR body or review before PR creation.
- Remind the operator to inspect `docs/learning/ERROR_PATTERNS.md` before repeating known fragile command patterns.
- Keep build-state, roadmap, governance, agent, skill, and prompt documentation impacts visible.
- Preserve explicit human approval gates before branch creation, file edits, staging, commit, push, PR creation, merge, release, issue closure, or repository setting changes.

The first version should optimize for repeatability and evidence quality before autonomy.

## What The First Version Must Not Do

The first version must not:

- Implement scripts or runnable command wrappers.
- Create GitHub Actions workflows, watchers, bots, daemons, scheduled jobs, services, or background automation.
- Create autonomous repository behavior.
- Edit files without an explicit human-directed implementation session.
- Stage, commit, push, merge, approve, auto-merge, or close issues without human instruction.
- Change repository settings, permissions, secrets, branch protection, rulesets, releases, tags, or GitHub Projects.
- Treat generated prompt packages or evidence packages as approval.
- Treat future design-target commands as available commands.
- Replace source-of-truth documentation, issue acceptance criteria, PR review, or human decisions.

## Human Approval Gates

Human approval is required before:

- Starting implementation work for an issue.
- Creating or switching branches.
- Editing repository files.
- Running validation commands that can modify repository, GitHub, release, project, or local state.
- Staging files.
- Creating commits.
- Pushing branches.
- Creating pull requests.
- Marking evidence as ready for reviewer use.
- Merging pull requests.
- Closing issues outside normal reviewed PR merge behavior.
- Changing autonomy level, governance meaning, approval rules, repository settings, branch protection, rulesets, secrets, releases, tags, workflows, or GitHub Projects.

The local operator workflow may prepare a recommended next action, but the human owner or human-directed implementation prompt must approve execution.

## Allowed Operations

The local operator workflow may be designed to support these non-autonomous operations:

- Read issue metadata and issue body.
- Read repository documentation and source-of-truth files.
- Read local Git status and branch state.
- Prepare prompt text for Codex or another implementation agent.
- Prepare validation checklists.
- Prepare PR evidence outlines.
- Prepare closeout evidence outlines.
- Summarize documentation freshness findings.
- Summarize documentation-sync impact.
- Identify likely changed-file targets from issue scope.
- Identify blocked, risky, or approval-required operations.
- Recommend follow-up issues when gaps are real but out of scope.

During Issue #47, even these operations are documented as design targets only.

## Blocked Operations

The local operator workflow must block or escalate any operation that would:

- Enable runnable automation without a future human-approved issue.
- Execute hidden commands outside a visible human-directed session.
- Modify workflows or create CI/CD behavior.
- Modify repository settings, permissions, branch protection, rulesets, secrets, releases, tags, or GitHub Projects.
- Approve, merge, auto-merge, or close issues autonomously.
- Treat an AI-generated recommendation as a human decision.
- Skip required documentation freshness checks for documentation-sync work.
- Stage unrelated files or overwrite intentional human changes.
- Promote future-state design targets into active capability.
- Use fragile command patterns documented in `docs/learning/ERROR_PATTERNS.md` without mitigation and verification.

Blocked operations should produce evidence and escalation notes rather than continuing silently.

## Evidence Outputs

Future local operator work should produce reviewable evidence packages.

Expected evidence outputs include:

- Issue number, title, milestone, labels, and source URL.
- Branch name and base branch.
- Source-of-truth files reviewed.
- Documentation freshness check summary.
- Documentation-sync impact summary.
- Planned changed files.
- Human approval gates encountered.
- Allowed operations performed or recommended.
- Blocked operations and escalation notes.
- Validation commands or manual checks to run.
- Validation results when available.
- PR evidence outline.
- Closeout evidence outline.
- Documentation-sync evidence outline.
- Documentation-sync handoff package template content.
- Confirmation that future-state commands or workflow concepts were not treated as implemented capability.

Evidence must distinguish confirmed facts, agent judgment, unavailable inputs, skipped checks, future recommendations, and human decisions.

Evidence packages should follow `docs/agents/DOCUMENTATION_SYNC_EVIDENCE_PACKAGES.md` when they involve documentation-sync work. Documentation-sync handoffs should use `docs/agents/DOCUMENTATION_SYNC_HANDOFF_TEMPLATE.md` for copy/paste-friendly package structure. Each package must include a non-authority statement confirming that it is a review artifact only and does not approve, merge, close, automate, bypass human review, or authorize future automation.

## Validation Expectations

For documentation-only local operator model changes, validation should include:

- `git status --short`
- `git diff --check`
- `git diff --cached --check` before commit when staging
- Changed-file review for issue scope.
- Confirmation that no scripts, runnable automation, workflows, auto-merge, autonomous approval, autonomous issue closure, repository setting changes, branch protection changes, ruleset changes, secret changes, release changes, tag changes, or GitHub Project changes were introduced.

For future operator-assisted implementation work, validation expectations should be copied from the active issue and prompt standard, then reported in PR evidence. Operator-prepared validation checklists are not validation results until the checks are actually run and reviewed.

## Relationship To Documentation Freshness Checks

The local operator workflow should use `docs/agents/DOCUMENTATION_FRESHNESS_CHECKS.md` before documentation-sync work.

The operator should prepare freshness evidence by:

- Listing the issue or PR scope.
- Listing source-of-truth docs reviewed.
- Classifying stale, missing, conflicting, incomplete, or outdated build-state and roadmap findings.
- Identifying which documentation updates are in scope.
- Identifying which findings require human escalation or follow-up issues.
- Preserving the advisory, manual, human-reviewed M2 boundary.

The operator does not replace the freshness check model. It packages the inputs and evidence so the freshness check is easier to perform consistently.

Freshness evidence prepared by the operator should be carried into the appropriate PR evidence package, closeout evidence package, or documentation-sync evidence package.

## Relationship To Documentation Sync

The local operator workflow should prepare inputs for `.agent/skills/documentation-sync/SKILL.md`.

Before documentation-sync work, the operator should identify:

- Documentation impact from the issue and planned changes.
- The freshness check findings that justify each documentation update.
- The exact docs that should be updated.
- Out-of-scope docs that should be reported as warnings instead of edited.
- Human-review boundary confirmations required in the PR body.

Documentation-sync remains a repo-owned markdown skill and a manual, human-reviewed behavior during M2. The local operator workflow does not turn documentation-sync into runnable automation.

Documentation-sync evidence packages provide the review structure for operator-prepared documentation-sync handoffs. They do not execute the documentation-sync skill and do not replace human-reviewed PR evidence.

The reusable handoff template at `docs/agents/DOCUMENTATION_SYNC_HANDOFF_TEMPLATE.md` may be used to format operator-prepared documentation-sync handoff content, but it remains a manual review artifact scaffold and not an implemented local operator command.

## Relationship To M3 Agent Workflow Orchestration

The local operator workflow prepares for M3 by defining the evidence packages and approval gates that future agent workflow orchestration must preserve.

M3 orchestration should be able to consume operator-style packages for:

- Issue intake.
- Agent handoff context.
- Documentation freshness findings.
- Validation evidence.
- PR readiness evidence.
- Human escalation items.

This Issue #47 model does not implement M3 orchestration. It only defines the local workflow shape that future orchestration can build on after a separate human-approved issue and governance review.

## Future Command Design Targets

The following names are future design targets only. They are not implemented by Issue #47 and must not be invoked as existing commands.

| Design target | Intended future purpose | Current Issue #47 status |
|---|---|---|
| `Start-IssueImplementation` | Prepare issue context, branch recommendation, source-of-truth reading list, constraints, and approval gates before implementation begins. | Design target only; not implemented. |
| `New-CodexPromptPackage` | Generate a Codex prompt package aligned with `docs/prompts/CODEX_PROMPT_STANDARD.md`. | Design target only; not implemented. |
| `Test-AresForgeWorktree` | Prepare or run approved local validation checks and summarize worktree state. | Design target only; not implemented. |
| `New-PrEvidencePackage` | Prepare PR body evidence including summary, changed files, freshness findings, validation, approval gates, non-authority statements, and issue linkage. | Design target only; not implemented. |
| `New-CloseoutEvidencePackage` | Prepare post-PR closeout evidence for build state, roadmap, issue status, documentation freshness, limitations, and next handoff. | Design target only; not implemented. |

Any future implementation of these design targets requires a separate issue, explicit human approval, governance review, validation expectations, and documentation updates.

## Risks And Anti-Patterns

Risks:

- Operators may be mistaken for automation if future command names are written without clear design-only labels.
- Evidence packages may be treated as approval instead of review input.
- Prompt packages may drift from the Codex prompt standard.
- Documentation freshness checks may be skipped if the operator focuses only on PR evidence.
- Future orchestration may accidentally broaden authority beyond the human-reviewed M2 boundary.

Anti-patterns:

- Creating scripts while claiming the issue is documentation-only.
- Treating a generated prompt as permission to edit, stage, commit, push, merge, or close.
- Hiding command execution behind an operator helper.
- Collapsing freshness checks, documentation-sync, validation, and approval into one unreviewed step.
- Recording future commands in docs without saying they are design targets only.

## Issue #47 Boundary

Issue #47 defines the local operator workflow as a design-only documentation layer.

It introduces no scripts, runnable automation, workflows, autonomous approval, auto-merge, autonomous issue closure, repository setting changes, branch protection changes, GitHub Project changes, release or tag changes, or autonomous repository behavior.
