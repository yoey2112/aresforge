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

Status: Active. Issue #43 completed the first M2 documentation agent foundation deliverable. Issue #45 completed the repeatable documentation freshness check model before documentation-sync work. Issue #47 completed the local operator workflow as a design-only documentation layer. Issue #49 completed corrective freshness reconciliation for M2 source-of-truth context.

Completed M2 foundation deliverables:

- Issue #43: Create documentation agent foundation.
- Issue #45: Create documentation freshness check model.
- Issue #47: Define local operator workflow.
- Issue #49: Reconcile M2 source-of-truth context after Issue #47 closeout.

Next M2 focus:

- Decide the next documentation automation foundation issue now that documentation agents, documentation freshness checks, local operator workflow, and source-of-truth context reconciliation are established.
- Keep local operator commands such as `Start-IssueImplementation`, `New-CodexPromptPackage`, `Test-AresForgeWorktree`, `New-PrEvidencePackage`, and `New-CloseoutEvidencePackage` as future design targets only until a later issue explicitly implements them.
## M3 — Agent Workflow Orchestration

Goal: Define and automate the handoffs between specialized agents.

## M4 — Dashboard MVP

Goal: Build the first AresForge dashboard that mirrors GitHub and documentation state.

## M5 — Self-Managed Delivery Loop

Goal: Enable AresForge to plan, execute, validate, score, document, and prepare releases with configurable autonomy.
