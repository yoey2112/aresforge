# AresForge Issue Lifecycle Agent Pipeline

## Purpose

This document defines the AresForge issue lifecycle pipeline for M2 architecture and design work.

The pipeline exists to stop treating source-of-truth documentation reconciliation as a routine follow-up issue after implementation closeout. Instead, documentation updates must be completed as a required pre-closeout gate inside the normal issue lifecycle.

During M2, this document is architecture and design documentation only. It does not introduce scripts, commands, workflows, runnable automation, auto-merge, autonomous approval, autonomous issue closure, or repository-setting changes.

## Problem It Solves

Recent reconciliation-only issues showed an unhealthy loop:

- An implementation issue changed project state.
- The implementation closed or merged before all source-of-truth docs were updated.
- A separate reconciliation issue was then needed to repair stale `BUILD_STATE`, `AGENT_CONTEXT`, `ROADMAP`, or related documentation.

That pattern weakens project memory, increases stale-state risk, and makes closeout evidence harder to trust.

The corrective design is to require documentation review and updates before PR merge and issue closeout whenever an issue changes project state.

## Lifecycle Flow

The intended lifecycle is:

Planning / Next-Issue Agent
-> Triage / Routing Agent
-> Worker Agent
-> Verification Agent
-> Testing Agent
-> if failed: Debug Routing Agent -> correct Worker Agent -> Verification Agent -> Testing Agent
-> if passed: Documentation Agent
-> Final Closeout / Lifecycle Controller Agent
-> Planning / Next-Issue Agent

## Core Lifecycle Principles

1. The Documentation Agent runs after implementation, verification, and testing pass.
2. The Documentation Agent runs before PR merge and issue closeout.
3. The Documentation Agent updates all impacted source-of-truth docs.
4. At minimum, project-state-changing issues must review and update as needed:
   - `docs/context/BUILD_STATE.md`
   - `docs/context/AGENT_CONTEXT.md`
   - `docs/roadmap/ROADMAP.md`
5. An issue is not ready to close until required documentation updates are complete.
6. Separate reconciliation issues are not the default closeout pattern.
7. Separate reconciliation issues should only be created when stale, conflicting, or incomplete source-of-truth documentation is discovered after closeout.
8. The Final Closeout / Lifecycle Controller Agent is the only lifecycle role that should close the issue after all gates pass.
9. During M2, this is architecture and design documentation only. No runnable automation is introduced.

## Lifecycle Roles

### Planning / Next-Issue Agent

Purpose:

- Select the next approved issue to work.
- Package issue intent, scope, constraints, and required source-of-truth inputs.

Inputs:

- Roadmap priorities.
- Active milestone context.
- Human decisions.
- Open issue inventory.
- Source-of-truth docs.

Outputs:

- Recommended next issue.
- Initial issue context and reading list.
- Sequencing notes and dependency notes.

Required gate:

- The selected issue must align with source-of-truth roadmap and human direction before routing begins.

### Triage / Routing Agent

Purpose:

- Convert the approved issue into a focused execution plan and assign the right worker path.

Inputs:

- Issue body and constraints.
- Planning handoff.
- Required source-of-truth docs.
- Known risks or blocked operations.

Outputs:

- Scoped execution handoff.
- Routing decision for the correct worker role.
- Validation and documentation expectations.

Required gate:

- The issue scope must be clear enough to avoid unrelated changes and unsafe authority assumptions.

### Worker Agent

Purpose:

- Perform the issue-scoped implementation work.

Inputs:

- Scoped execution handoff.
- Relevant docs, code, prompts, evidence, and constraints.

Outputs:

- Issue-scoped repository changes.
- Implementation summary.
- Initial validation notes and known limitations.

Required gate:

- Work must remain within issue scope and preserve M2 human-reviewed boundaries.

### Verification Agent

Purpose:

- Confirm the implemented change matches the issue requirements and changed-file intent.

Inputs:

- Worker output.
- Issue requirements.
- Changed files.
- Documentation impact expectations.

Outputs:

- Requirement-fit assessment.
- Scope-control assessment.
- Verification findings and defects, if any.

Required gate:

- Implementation requirements must be satisfied before testing proceeds.

### Testing Agent

Purpose:

- Validate the change with the issue-appropriate tests, checks, or manual review evidence.

Inputs:

- Verified implementation.
- Required validation commands or manual checks.
- Relevant issue-specific evidence expectations.

Outputs:

- Test and validation results.
- Pass or fail decision for the current implementation revision.
- Skipped-check notes and limitations.

Required gate:

- Required tests and checks must pass, or an explicit human decision must preserve a documented limitation.

### Debug Routing Agent

Purpose:

- Route failed verification or testing results back to the correct corrective worker path.

Inputs:

- Verification failures.
- Test failures.
- Logs, diffs, and reviewer notes.

Outputs:

- Corrective routing decision.
- Focused defect summary.
- Updated implementation handoff for the correct worker.

Required gate:

- Failure causes must be specific enough that the next worker pass can fix the right problem without widening scope unnecessarily.

### Documentation Agent

Purpose:

- Perform the required documentation-before-closeout review and update all impacted source-of-truth docs.

Inputs:

- Passed implementation.
- Verification and testing evidence.
- Required source-of-truth docs.
- Documentation freshness findings.
- Issue and PR context.

Outputs:

- Updated source-of-truth docs.
- Documentation impact summary.
- Freshness findings, warnings, and limitations.
- PR and closeout evidence inputs confirming documentation readiness.

Required gate:

- Documentation updates must be complete before PR merge and issue closeout.

Documentation-before-closeout rule:

- Documentation is not optional cleanup after closure.
- For project-state-changing issues, the Documentation Agent must review `BUILD_STATE`, `AGENT_CONTEXT`, and `ROADMAP` at minimum and update them whenever the issue changes active state, completed history, sequencing, rules, or next-step context.
- If no update is needed for one of those documents, the evidence must say why.

### Final Closeout / Lifecycle Controller Agent

Purpose:

- Confirm that every required lifecycle gate has passed and only then prepare final closeout.

Inputs:

- Passed verification results.
- Passed testing results.
- Documentation Agent outputs.
- PR evidence and closeout evidence inputs.
- Human review decisions.

Outputs:

- Final closeout readiness decision.
- Final handoff to human review.
- Issue-close recommendation only after all gates pass.

Required gate:

- This is the only lifecycle role that should close the issue, and it may do so only after implementation, verification, testing, and documentation gates have passed.

## Required Gates

The lifecycle requires these gates, in order:

1. Planning gate: the issue is approved and correctly sequenced.
2. Triage gate: scope, constraints, and ownership are clear.
3. Implementation gate: issue-scoped work exists.
4. Verification gate: requirements and scope fit are confirmed.
5. Testing gate: required validation passes.
6. Documentation gate: impacted source-of-truth docs are reviewed and updated before closeout.
7. Final closeout gate: closeout evidence and human-reviewed controls confirm readiness.

An issue is not ready for merge or closeout until all required gates pass.

## Failure Loop Behavior

If verification or testing fails:

- The issue does not proceed to documentation or closeout.
- The Debug Routing Agent classifies the failure and sends it back to the correct Worker Agent path.
- Verification and testing repeat after the corrective change.
- Only after verification and testing pass does the Documentation Agent run.

This preserves documentation accuracy by preventing premature project-memory updates for work that still failed its technical gates.

## Documentation-Before-Closeout Rule

The central correction in this design is:

- Documentation updates belong inside the issue lifecycle.
- Documentation updates are required before PR merge and issue closeout for project-state-changing work.
- Reconciliation-only issues are discouraged as the default closeout pattern.

Separate reconciliation issues remain allowed only when documentation problems are discovered after closeout, including:

- Stale source-of-truth docs.
- Conflicting source-of-truth docs.
- Incomplete source-of-truth docs.

That exception path is a recovery mechanism, not the standard lifecycle.

## Final Closeout Responsibilities

Before an issue is closed, the Final Closeout / Lifecycle Controller Agent should confirm:

- Implementation work is complete for the scoped issue.
- Verification passed.
- Testing passed.
- Documentation freshness review occurred.
- Impacted source-of-truth docs were updated.
- `BUILD_STATE`, `AGENT_CONTEXT`, and `ROADMAP` were reviewed for project-state-changing issues.
- The issue is not still documented as active or in progress in source-of-truth docs.
- Evidence packages and handoff artifacts reflect the final documented state.
- Human-reviewed controls remain preserved.

## Human-Reviewed Controls

This lifecycle preserves explicit human-reviewed controls:

- Human review remains required before approval or merge.
- Human decisions remain authoritative over inferred agent behavior.
- Evidence packages, handoff packages, prompt packages, PR evidence packages, and closeout evidence packages remain review or input artifacts only.
- Those artifacts do not approve, merge, close, automate, bypass review, or replace human controls.

## M2 Restriction

During M2, this lifecycle pipeline is architecture and design documentation only.

It must not be implemented in this issue as:

- A script.
- A runnable command.
- A workflow.
- A bot.
- A watcher.
- A service.
- Auto-merge behavior.
- Autonomous approval.
- Autonomous issue closure.
- Autonomous PR merge.
- Autonomous issue routing.

Any future implementation requires a separate human-directed issue, governance review, validation expectations, and source-of-truth updates.

## Protected Validation Evidence

Issue #39, `validation: issue-38-state-lifecycle`, remains protected M1 audit evidence.

This pipeline does not close, modify, comment on, or otherwise change Issue #39. Issue #39 must remain intentionally preserved unless a future human-directed issue explicitly changes its state.
