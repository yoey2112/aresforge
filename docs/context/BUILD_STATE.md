# AresForge Build State

## Current Phase

M2 - Runnable Local Skeleton Pivot

## Current Goal

Define the first canonical model registry schema and bounded local LLM routing rules for Issue #85 on top of the runnable local skeleton completed by Issue #81 / PR #82 and the agent-registry layer completed by Issue #83, while keeping the implementation human-triggered, local-first, read-only where possible, and aligned with the existing registry and lifecycle architecture.

## Current Repository State

- Main branch baseline for the runnable pivot: `d04041c` (`Define project registry schema (#80)`).
- Issue #81, `Build runnable local skeleton and automation foundation`, is completed through PR #82.
- Issue #83, `Define agent registry schema and lifecycle states`, is completed and remains the canonical agent-registry schema layer.
- Issue #85, `Define model registry and local LLM routing rules`, is the active implementation issue.
- `docs/architecture/REGISTRY_AND_QUEUE_ARCHITECTURE.md` remains the canonical registry and queue architecture artifact.
- `docs/architecture/PROJECT_REGISTRY_SCHEMA.md` remains the canonical project registry schema artifact.
- `docs/architecture/AGENT_REGISTRY_SCHEMA.md` is the canonical agent registry schema artifact.
- `docs/architecture/MODEL_REGISTRY_SCHEMA.md` is the canonical model registry and local LLM routing artifact.
- Issue #75 remains the last routine reconciliation issue.
- Remaining open protected validation issue: #39, `validation: issue-38-state-lifecycle`, intentionally preserved as audit evidence and not touched by Issue #85.

## Current Source of Truth

GitHub, repository documentation, and the new local PostgreSQL/operator state together now form the practical operating picture for M2 implementation work.

Repository documentation remains the authoritative source for roadmap, governance, architecture meaning, and automation boundaries. The new local database is an operational store for local runtime state, not a replacement for source-of-truth docs.

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

- Issue #30 completed via PR #31:
  - Documented read-only GitHub Project/table access validation.
  - Confirmed repository project enablement is readable through repository metadata.
  - Confirmed issue-level `projectItems` summary can be requested but returned no project items for Issue #30.
  - Confirmed native `gh project` support is available.
  - Confirmed ProjectV2 project lists, fields, views, and items are blocked until the current token has `read:project`.
  - Updated GitHub operations skill with safe project/table read guidance.
  - Confirmed no GitHub Project settings, fields, views, or items were modified.
  - Confirmed no runnable automation, auto-merge, autonomous approval, destructive automation, repository setting change, branch protection change, workflow change, release/tag change, secret change, permission change, or autonomous issue closure was introduced.
- Issue #32 completed via PR #33:
  - Documented read-only GitHub workflow run and artifact read validation.
  - Confirmed `.github/workflows` does not currently exist.
  - Confirmed no workflow files currently exist.
  - Confirmed `gh run list --repo yoey2112/aresforge --limit 10` is available and returns no workflow runs.
  - Documented that run detail, artifact list, and artifact download behavior cannot yet be fully validated because no workflow runs or artifacts exist.
  - Updated GitHub operations skill with safe workflow run and artifact read guidance.
  - Confirmed no new reusable failure was discovered, so `docs/learning/ERROR_PATTERNS.md` was not updated.
  - Confirmed no workflow creation, workflow editing, workflow triggering, artifact commit, runnable automation, auto-merge, autonomous approval, destructive automation, repository setting change, branch protection change, secret change, permission change, release/tag change, project change, or autonomous issue closure was introduced.
- Issue #34 completed via PR #35:
  - Documented read-only repository branch protection and repository ruleset validation.
  - Confirmed `main` branch metadata is readable and currently reports `protected: false`.
  - Confirmed the branch protection endpoint returns `Branch not protected` for `main`, documented as current repository state rather than a reusable command failure.
  - Confirmed the repository rulesets endpoint is readable and currently returns an empty list.
  - Updated GitHub operations skill with safe branch protection and repository ruleset read guidance.
  - Confirmed no new reusable failure was discovered, so `docs/learning/ERROR_PATTERNS.md` was not updated.
  - Confirmed no branch protection, repository rulesets, settings, permissions, secrets, workflows, releases, tags, GitHub Projects, auto-merge, approvals, merges, manual issue closure, or runnable automation were changed.
- Issue #36 completed via PR #37:
  - Documented repeatable GitHub release and tag lifecycle validation.
  - Confirmed initial release inventory was empty.
  - Confirmed initial local and remote tag inventories were empty.
  - Created only temporary validation tag `validation-issue-36-release-tag-lifecycle`.
  - Created only temporary prerelease `Validation Issue 36 Release Lifecycle`.
  - Verified temporary release metadata and remote tag metadata.
  - Deleted only the temporary validation release and tag.
  - Final cleanup verification returned no releases, no local validation tag, and no remote validation tag.
  - Added `M1-ERROR-010` for unsupported `gh release view --json isLatest` in GitHub CLI 2.92.0.
  - Updated GitHub operations skill with safe release and tag lifecycle guidance.
  - Confirmed no production releases, production tags, version-like production tags, repository settings, branch protection, repository rulesets, permissions, secrets, workflows, GitHub Projects, auto-merge, approvals, manual issue closure, or runnable automation were changed.
- Issue #38 completed via PR #40:
  - Documented repeatable GitHub issue state lifecycle validation.
  - Created one isolated temporary validation issue, #39, titled `validation: issue-38-state-lifecycle`.
  - Confirmed temporary issue #39 could be read, closed, verified closed, reopened, and verified open.
  - Left temporary issue #39 open with no milestone and no labels for future auditability.
  - Added final evidence comment to Issue #38.
  - Updated GitHub operations skill with safe issue state lifecycle guidance.
  - Confirmed Issue #38 was not manually closed and closed only through the reviewed PR merge.
  - Confirmed no production, roadmap, milestone, or active implementation issue state was changed.
  - Confirmed no repository settings, branch protection, repository rulesets, workflows, releases, tags, GitHub Projects, automation, auto-merge, approvals, or autonomous closure behavior were modified or enabled.
- Issue #41 completed via PR #42:
  - Reconciled M1 GitHub operations validation status.
  - Summarized completed M1 validation work across issues #18, #20, #22, #24, #26, #28, #30, #32, #34, #36, and #38.
  - Documented remaining limitations for GitHub Projects v2, workflow/artifact validation, branch protection/ruleset validation, and production release governance.
  - Confirmed M1 is complete enough to proceed to M2.
  - Recommended `Create documentation agent foundation` as the first M2 implementation issue.
  - Updated validation, agent context, roadmap, and build-state documentation.
  - Confirmed no automation, workflows, auto-merge, autonomous approval, autonomous issue closure, repository settings, branch protection, rulesets, releases, tags, GitHub Projects, or unrelated issue state were modified.


- Issue #43 completed via PR #44:
  - Created the M2 documentation agent foundation.
  - Expanded the canonical documentation agent model at docs/agents/DOCUMENTATION_AGENTS.md.
  - Defined documentation agent responsibilities, source-of-truth update flow, documentation impact detection rules, documentation freshness checks, human-reviewed documentation update expectations, validation evidence requirements, and agent handoffs.
  - Updated AGENT_CONTEXT.md, ROADMAP.md, BUILD_STATE.md, AGENT_SKILLS_MODEL.md, AGENT_REGISTRY.md, documentation-sync skill guidance, PR validation guidance, self-management governance, and Codex prompt standards where directly required.
  - Confirmed no runnable automation, workflow, auto-merge, autonomous approval, autonomous issue closure, repository setting change, branch protection change, ruleset change, secret change, release change, tag change, or GitHub Project change was introduced.
  - PR #44 merged successfully.
  - Issue #43 required manual closeout after merge because PR #44 did not auto-close the issue.
- Issue #45 completed via PR #46:
  - Created the M2 documentation freshness check model at docs/agents/DOCUMENTATION_FRESHNESS_CHECKS.md.
  - Updated documentation-sync skill guidance so freshness checks run before documentation-sync work.
  - Updated documentation agent, agent skills, agent context, build state, roadmap, and agent registry references.
  - PR #46 merged successfully.
  - Issue #45 required manual closeout after merge because PR #46 did not auto-close the issue.
  - Confirmed no runnable automation, workflow, auto-merge, autonomous approval, autonomous issue closure, repository setting change, branch protection change, ruleset change, secret change, release change, tag change, or GitHub Project change was introduced.
- Issue #47 completed via PR #48:
  - Created the local operator workflow model at docs/architecture/LOCAL_OPERATOR_WORKFLOW.md.
  - Defined the local operator workflow as a design-only documentation layer for reducing manual copy/paste while preserving human-reviewed controls.
  - Documented allowed operations, blocked operations, human approval gates, evidence outputs, validation expectations, and future command design targets.
  - Updated agent registry, documentation-sync skill, agent skills model, documentation agent model, documentation freshness model, agent context, build state, PR validation model, self-management model, Codex prompt standard, and roadmap references.
  - PR #48 merged successfully.
  - Issue #47 required manual closeout after merge because PR #48 did not auto-close the issue.
  - Confirmed no scripts, runnable automation, workflow, auto-merge, autonomous approval, autonomous issue closure, repository setting change, branch protection change, GitHub Project change, release change, or tag change was introduced.
- Issue #49 completed:
  - Reconciled M2 source-of-truth context after Issue #47 closeout.
  - Updated build-state, roadmap, and agent context to remove stale next-issue wording.
  - Confirmed no automation, workflows, auto-merge, autonomous approval, autonomous issue closure, repository setting change, or repo automation change was introduced.
- Issue #51 completed and closed via PR #52:
  - Defined the documentation-sync evidence package model at docs/agents/DOCUMENTATION_SYNC_EVIDENCE_PACKAGES.md.
  - Documented PR evidence packages, closeout evidence packages, documentation-sync evidence packages, freshness-check evidence, required source document lists, touched-document lists, diff and validation summaries, human-review notes, limitation and exception notes, handoff notes, issue and PR references, and non-authority statements.
  - Updated documentation-sync guidance and M2 source-of-truth context to preserve evidence packages as review artifacts only.
  - PR #52 merged successfully.
  - Issue #51 was manually closed after closeout evidence was posted.
  - Confirmed no scripts, runnable automation, workflows, commands, auto-merge, autonomous approval, autonomous issue closure, repository setting change, branch protection change, ruleset change, secret change, release change, tag change, or GitHub Project change was introduced.
- Issue #55 completed and closed via PR #56:
  - Defined the reusable documentation-sync handoff package template at docs/agents/DOCUMENTATION_SYNC_HANDOFF_TEMPLATE.md.
  - Documented copy/paste-friendly handoff package sections for issue and PR references, source-of-truth documents reviewed, freshness-check evidence, documentation impact, changed or expected documents, validation evidence, human-review boundaries, limitations, escalation items, handoff notes, and the required non-authority statement.
  - Updated documentation-sync guidance and M2 source-of-truth context so future documentation-sync handoffs can use the template after freshness checks and evidence package review.
  - PR #56 merged successfully.
  - Issue #55 closed through the PR merge.
  - Confirmed no scripts, runnable automation, workflows, commands, auto-merge, autonomous approval, autonomous issue closure, repository setting change, branch protection change, ruleset change, secret change, release change, tag change, or GitHub Project change was introduced.
- Issue #59 completed and closed after PR #60:
  - Defined the reusable Codex prompt package template at docs/prompts/CODEX_PROMPT_PACKAGE_TEMPLATE.md.
  - Aligned the prompt standard, local operator workflow, documentation-sync skill, agent registry, agent context, build state, and roadmap with the new template.
  - PR #60 merged successfully.
  - Issue #59 was manually closed after closeout evidence was posted.
  - Confirmed Issue #39 was not modified or closed.
  - Confirmed no scripts, runnable automation, workflows, commands, auto-merge, autonomous approval, autonomous issue closure, repository setting change, branch protection change, ruleset change, secret change, release change, tag change, or GitHub Project change was introduced.
- Issue #61 completed and closed after PR #62:
  - Added docs/planning/FUTURE_FEATURE_IDEAS.md as a future feature ideas parking lot.
  - Documented milestone-start review expectations, idea status values, an idea entry template, and MCP as a candidate future milestone review idea.
  - PR #62 merged successfully.
  - Issue #61 was manually closed after closeout evidence was posted.
  - Confirmed Issue #39 was not modified or closed.
  - Confirmed no scripts, runnable automation, workflows, commands, auto-merge, autonomous approval, autonomous issue closure, repository setting change, branch protection change, ruleset change, secret change, release change, tag change, or GitHub Project change was introduced.
- Issue #63 completed and closed after PR #64:
  - Created docs/agents/PR_EVIDENCE_PACKAGE_TEMPLATE.md as reusable M2 PR evidence package scaffolding.
  - Documented issue references, PR references, branch and commit context, source-of-truth documents reviewed, files changed, scope summary, documentation impact, freshness-check evidence, validation results, diff review, human-review notes, limitations, protected Issue #39 confirmations, repository-boundary confirmations, and the required non-authority statement.
  - PR #64 merged successfully.
  - Issue #63 was manually closed after closeout evidence was posted.
  - Confirmed Issue #39 was not modified or closed.
  - Confirmed no scripts, runnable automation, workflows, commands, auto-merge, autonomous approval, autonomous issue closure, repository setting change, branch protection change, ruleset change, secret change, release change, tag change, or GitHub Project change was introduced.
- Issue #65 completed and closed after PR #66:
  - Created docs/agents/CLOSEOUT_EVIDENCE_PACKAGE_TEMPLATE.md as reusable M2 closeout evidence package scaffolding.
  - Documented issue references, PR references when applicable, merge or closeout trigger, branch and commit context, source-of-truth documents reviewed, documentation freshness-check evidence, closeout file changes, project-memory updates, roadmap and state updates, validation results, diff review, human-review notes, limitations, protected Issue #39 confirmations, repository-boundary confirmations, next-step handoff notes, and the required non-authority statement.
  - Updated documentation-sync evidence guidance, documentation agent guidance, documentation freshness guidance, documentation-sync skill guidance, agent context, build state, and roadmap.
  - PR #66 merged successfully.
  - Issue #65 was manually closed after closeout evidence was posted.
  - Confirmed Issue #39 was not modified or closed.
  - Confirmed no scripts, runnable automation, workflows, commands, auto-merge, autonomous approval, autonomous issue closure, repository setting change, branch protection change, ruleset change, secret change, release change, tag change, or GitHub Project change was introduced.
- Issue #67 completed and closed after PR #68:
  - Reconciled stale M2 source-of-truth wording after Issue #65 closeout.
  - Updated build state, agent context, and roadmap wording so Issue #65 remained recorded as completed and closed after PR #66 closeout rather than active.
  - PR #68 merged successfully.
  - Issue #67 was manually closed after PR #68 closeout.
  - Confirmed Issue #39 was not modified or closed.
  - Confirmed no scripts, runnable automation, workflows, commands, auto-merge, autonomous approval, autonomous issue closure, repository setting change, branch protection change, ruleset change, secret change, release change, tag change, or GitHub Project change was introduced.
- Issue #69 completed and closed after PR #70:
  - Reconciled stale M2 source-of-truth wording after Issue #67 closeout.
  - Updated build state, agent context, and roadmap wording so Issue #67 remained recorded as completed and closed after PR #68 closeout rather than active.
  - PR #70 merged successfully.
  - Latest `main` commit advanced to `38fa94e`, `Reconcile source-of-truth after issue 67 closeout`.
  - Issue #69 was manually closed after PR #70 closeout.
  - Confirmed Issue #39 was not modified or closed.
  - Confirmed no scripts, runnable automation, workflows, commands, auto-merge, autonomous approval, autonomous issue closure, repository setting change, branch protection change, ruleset change, secret change, release change, tag change, or GitHub Project change was introduced.
- Issue #71 completed and closed after PR #72:
  - Reconciled source-of-truth documentation after Issue #69 closeout.
  - Updated build state, agent context, and roadmap wording so Issue #69 remained recorded as completed and closed rather than active.
  - PR #72 merged successfully.
  - Latest `main` commit advanced to `7d21189`, `Reconcile source-of-truth after issue 69 closeout (#72)`.
  - Issue #71 was manually closed after closeout evidence was posted.
  - Confirmed Issue #39 was not modified or closed.
  - Confirmed no scripts, runnable automation, workflows, commands, auto-merge, autonomous approval, autonomous issue closure, repository setting change, branch protection change, ruleset change, secret change, release change, tag change, or GitHub Project change was introduced.
- Issue #73 completed and closed via PR #74:
  - Defined the canonical lifecycle design artifact at `docs/architecture/ISSUE_LIFECYCLE_AGENT_PIPELINE.md`.
  - Documented the Documentation Agent as a required pre-closeout gate for project-state-changing issues.
  - Documented that `docs/context/BUILD_STATE.md`, `docs/context/AGENT_CONTEXT.md`, and `docs/roadmap/ROADMAP.md` must be reviewed and updated as needed before PR merge and issue closeout.
  - Updated PR and closeout evidence templates so source-of-truth review is required before closeout.
  - PR #74 merged successfully.
  - Latest `main` commit advanced to `031c3c4`, `Define issue lifecycle pipeline and closeout gate (#74)`.
  - Confirmed Issue #39 was not modified or closed.
  - Confirmed no scripts, runnable automation, workflows, commands, auto-merge, autonomous approval, autonomous issue closure, repository setting change, branch protection change, ruleset change, secret change, release change, tag change, or GitHub Project change was introduced.
- Issue #75 completed and closed via PR #76:
  - Reconciled stale source-of-truth wording left behind after Issue #73 / PR #74 closeout.
  - Updated build state, agent context, and roadmap wording so Issue #75 remains recorded as completed and closed rather than active.
  - Reinforced that Issue #75 should be the last routine reconciliation issue.
  - Reinforced that future project-state-changing issues must update source-of-truth docs before PR merge and issue closeout.
  - Reinforced that separate related source-of-truth documentation update issues should not be created by default because they recreate the reconciliation loop.
  - Reinforced that separate reconciliation or documentation-update issues are appropriate only when stale, conflicting, or incomplete source-of-truth documentation is discovered after closeout.
  - PR #76 merged successfully.
  - Latest `main` commit advanced to `e7bb49a`, `Reconcile source-of-truth after issue 73 closeout (#76)`.
  - Confirmed Issue #39 was not modified or closed.
  - Confirmed no scripts, runnable automation, workflows, commands, auto-merge, autonomous approval, autonomous issue closure, repository setting change, branch protection change, ruleset change, secret change, release change, tag change, or GitHub Project change was introduced.
- Issue #77 completed and closed via PR #78:
  - Defined the canonical registry and queue architecture artifact at `docs/architecture/REGISTRY_AND_QUEUE_ARCHITECTURE.md`.
  - Documented the project, agent, model, queue, capability, and skill registry layers as documentation-only M2 architecture.
  - Preserved the rule that source-of-truth documentation updates belong inside the same project-state-changing issue lifecycle before PR merge and issue closeout.
  - Preserved the rule that Issue #75 should remain the last routine reconciliation issue.
  - Preserved the rule that separate related source-of-truth documentation-update issues should not be created by default because they recreate the reconciliation loop.
  - PR #78 merged successfully.
  - Latest `main` commit advanced to `1eb7efb`, `Define registry and queue architecture (#78)`.
  - Confirmed Issue #39 was not modified or closed.
  - Confirmed no scripts, runnable automation, workflows, commands, auto-merge, autonomous approval, autonomous issue closure, repository setting change, branch protection change, ruleset change, secret change, release change, tag change, or GitHub Project change was introduced.
- Issue #79 completed and closed via PR #80:
  - Defined the canonical project registry schema artifact at `docs/architecture/PROJECT_REGISTRY_SCHEMA.md`.
  - Completed the documentation-only project-record schema that specialized the registry architecture.
  - Latest `main` commit advanced to `d04041c`, `Define project registry schema (#80)`.
  - Confirmed Issue #39 was not modified or closed.
  - Confirmed no runnable automation, auto-merge, autonomous approval, autonomous issue closure, repository setting change, branch protection change, ruleset change, secret change, release change, tag change, or GitHub Project change was introduced.
- Issue #81 completed via PR #82:
  - Built the first runnable local skeleton and automation foundation.
  - Added the PostgreSQL-backed local state store, repo-stored migrations, human-triggered CLI commands, reviewable prompt/evidence/Codex handoff artifacts, and the bounded Ollama dry-run integration layer.
  - Added the first local `projects`, `agents`, `models`, `queues`, `work_items`, `prompts`, `evidence_packages`, `documentation_state`, `approvals`, and `audit_events` runtime tables.
  - Added `docs/architecture/LOCAL_STATE_STORE.md`, `docs/architecture/RUNNABLE_SKELETON.md`, and `docs/operator/LOCAL_OPERATOR_USAGE.md` as the canonical runnable-skeleton implementation artifacts.
  - PR #82 merged successfully.
  - Confirmed Issue #39 was not modified or closed.
  - Confirmed no autonomous PR merge, autonomous approval, autonomous issue closure, autonomous GitHub-state-changing behavior, repository setting change, branch protection change, ruleset change, secret change, release change, tag change, or GitHub Project change was introduced.
- Issue #83 completed:
   - Defined the canonical agent registry schema artifact at `docs/architecture/AGENT_REGISTRY_SCHEMA.md`.
   - Formalized bounded agent-role records, lifecycle states, capability relationships, queue participation expectations, evidence outputs, escalation rules, and local operator integration points.
   - Preserved the local `agents` table as conservative seed/reference data rather than autonomous execution authority.
   - Confirmed Issue #39 was not modified or closed.
   - Confirmed no autonomous execution, autonomous routing, autonomous approval, autonomous merge, autonomous issue closure, hosted model enablement, or GitHub-state-changing behavior was introduced.
## In Progress

- `docs/architecture/ISSUE_LIFECYCLE_AGENT_PIPELINE.md` remains the completed canonical lifecycle pipeline design artifact.
- `docs/architecture/REGISTRY_AND_QUEUE_ARCHITECTURE.md` remains the completed canonical registry and queue architecture artifact.
- `docs/architecture/PROJECT_REGISTRY_SCHEMA.md` remains the completed canonical project registry schema artifact.
- `docs/architecture/AGENT_REGISTRY_SCHEMA.md` remains the completed canonical agent registry schema artifact from Issue #83.
- `docs/architecture/MODEL_REGISTRY_SCHEMA.md` is the active canonical model registry and local LLM routing artifact for Issue #85.
- Issue #85 is the active model-registry and bounded local-routing implementation issue.
- The repository now has a completed runnable local operator foundation from Issue #81 and is formalizing bounded lifecycle-role and model-routing meaning on top of it.
- The new local state-store and operator usage docs are:
  - `docs/architecture/LOCAL_STATE_STORE.md`
  - `docs/architecture/RUNNABLE_SKELETON.md`
  - `docs/operator/LOCAL_OPERATOR_USAGE.md`
- The agent-registry schema and lifecycle-state work now adds:
  - `docs/architecture/AGENT_REGISTRY_SCHEMA.md`
- The model-registry schema and local-routing work now adds:
  - `docs/architecture/MODEL_REGISTRY_SCHEMA.md`
- Future project-state-changing issues must continue updating source-of-truth docs before PR merge and issue closeout.
- Issue #75 remains the last routine reconciliation issue.
- Separate reconciliation or documentation-update issues remain the exception path only.
- Preserve the explicit rule that Issue #39 remains intentionally open as protected validation audit evidence unless a future human-directed issue explicitly changes its state.
- Preserve the explicit rule that no related source-of-truth documentation-update issue should be created by default for future project-state-changing work.

## Next

- Preserve Issue #39 as the only remaining open protected validation issue unless a future human-directed issue explicitly changes its state.
- Validate and iterate on the local operator CLI, migration flow, local artifact outputs, and agent-registry seed/listing behavior created by Issues #81 and #83.
- Keep documentation freshness checks required before future documentation-sync work.
- Use the new runnable skeleton docs when extending the local operator:
  - `docs/architecture/LOCAL_STATE_STORE.md`
  - `docs/architecture/RUNNABLE_SKELETON.md`
  - `docs/operator/LOCAL_OPERATOR_USAGE.md`
- Use `docs/architecture/AGENT_REGISTRY_SCHEMA.md` as the canonical agent-role, lifecycle-state, capability-boundary, and queue-participation artifact.
- Use `docs/architecture/MODEL_REGISTRY_SCHEMA.md` as the canonical model-record, routing-priority, fallback, approval-posture, and local-endpoint artifact.
- Keep Codex handoff generation as output-file preparation only until a later human-approved issue expands it.
- Keep Ollama integration bounded to human-triggered local test, support, and advisory routing contexts until a later issue explicitly authorizes richer routing or execution.
- Do not create another routine reconciliation issue after Issue #75.
- Do not create related source-of-truth documentation update issues by default.
- Use `docs/architecture/ISSUE_LIFECYCLE_AGENT_PIPELINE.md` as the canonical lifecycle correction for documentation-before-closeout.
- Use `docs/architecture/REGISTRY_AND_QUEUE_ARCHITECTURE.md`, `docs/architecture/PROJECT_REGISTRY_SCHEMA.md`, `docs/architecture/AGENT_REGISTRY_SCHEMA.md`, and `docs/architecture/MODEL_REGISTRY_SCHEMA.md` as the architectural input for later queue evolution, capability alignment, and multi-project routing work.
- Review docs/planning/FUTURE_FEATURE_IDEAS.md at the beginning of each future milestone.

## Current Operating Constraint

All current M2 runnable-skeleton changes remain manually guided, human-triggered, and manually reviewed.

Human-triggered local automation is allowed for config validation, local migrations, local state inspection, read-only registry listing, local artifact generation, local Ollama checks, and advisory model-selection reasoning that remains reviewable and non-governance-authoritative.

No autonomous PR merge, autonomous approval, autonomous issue closure, autonomous GitHub-state-changing behavior, repository setting change, branch protection change, ruleset change, secret change, release change, tag change, hosted external model call, or GitHub Project change is enabled by Issues #81, #83, or #85.
