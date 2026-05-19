# AresForge Roadmap

## M0 — Self-Bootstrap Foundation

Goal: Create the new AresForge repo and immediately define AresForge as its own first managed project.

Deliverables:

- New GitHub repo: yoey2112/aresforge
- Local clone under C:\Projects\aresforge
- Baseline document-driven structure
- Initial self-project context docs
- First milestone
- First GitHub issues
- GitHub capability validation plan
- Ollama validation plan
- Documentation agent model
- Self-management model
- Future dashboard state field definition
- Codex prompt standard
- PR validation/scoring model

Completion criteria:

- GitHub operations are validated.
- Local Ollama review is validated with documented limitations.
- Documentation agent responsibilities are defined.
- AresForge is documented as its own first managed project.
- Temporary source-of-truth rules are documented.
- Next-chat handoff expectations are documented.
- Prompt and PR validation standards are documented.

## M1 — GitHub Operations Validation

Goal: Prove AresForge can safely create, update, validate, and close work through GitHub-managed workflows.

Status: Complete enough to proceed to M2. M1 limitations remain documented and unresolved unless a later issue explicitly addresses them.

Closeout result:

- Reconcile M1 GitHub operations validation evidence.
- Summarize completed validation work from issues #18, #20, #22, #24, #26, #28, #30, #32, #34, #36, and #38.
- Document remaining limitations for GitHub Projects v2, workflows and artifacts, branch protection and rulesets, and production release governance.
- Confirm M1 is complete enough to proceed to M2 while preserving manual, human-reviewed, documentation-driven operations.

## M2 — Documentation Automation

Goal: Establish documentation agent rules, source-of-truth update flow, documentation freshness checks, and human-reviewed documentation update behavior before any autonomous automation.

Status: Active. Issue #43 completed the first M2 documentation agent foundation deliverable. Issue #45 completed the repeatable documentation freshness check model before documentation-sync work. Issue #47 completed the local operator workflow as a design-only documentation layer. Issue #49 completed corrective freshness reconciliation for M2 source-of-truth context. Issue #51 completed the documentation-sync evidence package model as a review artifact standard. Issue #55 completed the reusable documentation-sync handoff package template. No active M2 implementation issue is currently assigned; the next M2 deliverable must be chosen.

Completed M2 foundation deliverables:

- Issue #43: Create documentation agent foundation.
- Issue #45: Create documentation freshness check model.
- Issue #47: Define local operator workflow.
- Issue #49: Reconcile M2 source-of-truth context after Issue #47 closeout.
- Issue #51: Define documentation-sync evidence package model.
- Issue #55: Define documentation-sync handoff package template.

Next M2 focus:

- Choose the next M2 deliverable before assigning new implementation work.
- Use docs/agents/DOCUMENTATION_SYNC_HANDOFF_TEMPLATE.md for future documentation-sync handoffs.
- Keep documentation-sync evidence packages as review artifacts only.
- Keep documentation-sync handoff packages as review artifacts only.
- Keep documentation freshness checks required before future documentation-sync work.
- Keep local operator commands such as `Start-IssueImplementation`, `New-CodexPromptPackage`, `Test-AresForgeWorktree`, `New-PrEvidencePackage`, and `New-CloseoutEvidencePackage` as future design targets only until a later issue explicitly implements them.
## M3 — Agent Workflow Orchestration

Goal: Define and automate the handoffs between specialized agents.

## M4 — Dashboard MVP

Goal: Build the first AresForge dashboard that mirrors GitHub and documentation state.

## M5 — Self-Managed Delivery Loop

Goal: Enable AresForge to plan, execute, validate, score, document, and prepare releases with configurable autonomy.
