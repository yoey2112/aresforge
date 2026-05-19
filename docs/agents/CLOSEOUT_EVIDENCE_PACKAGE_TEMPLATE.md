# AresForge Closeout Evidence Package Template

This document defines the reusable M2 closeout evidence package template for AresForge implementation work.

A closeout evidence package is a copy/paste-friendly review artifact that supports post-PR or human-directed closeout work. It records what was merged or otherwise completed, what project memory changed, what validation evidence exists, what remains unresolved, and what the next agent, operator, or human owner should know before continuing.

Use this template when preparing closeout evidence for:

- Post-merge documentation closeout.
- Human-directed issue closeout preparation.
- Source-of-truth reconciliation after a PR merge.
- Build state, roadmap, agent context, skill, or evidence-template updates after implementation work.
- Local operator workflow preparation for closeout evidence.

This template implements the closeout evidence package expectations defined in docs/agents/DOCUMENTATION_SYNC_EVIDENCE_PACKAGES.md. When documentation-sync work is involved, use the freshness check model before completing the freshness-check section.

## Required Non-Authority Statement

Every completed closeout evidence package must include this statement:

> This closeout evidence package is a review artifact only. It does not approve, merge, close, automate, bypass human review, replace human controls, change source-of-truth priority, or authorize future automation. Human-reviewed controls remain mandatory.

## Template

### 1. Package Purpose

- Closeout package type:
- Prepared for:
- Prepared by:
- Prepared date:
- Related milestone or phase:
- Closeout is:
  - [ ] Post-merge closeout.
  - [ ] Human-directed closeout preparation.
  - [ ] Source-of-truth reconciliation.
  - [ ] Documentation-sync closeout.
  - [ ] Other:

### 2. Issue Reference

- Issue number:
- Issue title:
- Issue URL:
- Issue state before closeout:
- Issue state after closeout:
- Issue closure method:
  - [ ] Closed automatically by merge.
  - [ ] Closed manually by human direction.
  - [ ] Left open intentionally.
  - [ ] Not applicable.
- Closeout evidence comment posted:
- Closeout evidence comment URL, if applicable:
- Issue labels before closeout:
- Issue labels after closeout:
- Issue milestone before closeout:
- Issue milestone after closeout:

### 3. PR Reference

- PR number:
- PR title:
- PR URL:
- PR state:
- PR branch:
- Base branch:
- Merge commit:
- PR merged:
- PR merge method:
- PR closeout wording:
- PR evidence package used:
- PR evidence package location or link:
- PR discussion, review, or comment items relevant to closeout:

### 4. Merge or Closeout Trigger

- Trigger type:
  - [ ] PR merged.
  - [ ] Issue manually closed.
  - [ ] Human owner requested closeout preparation.
  - [ ] Source-of-truth reconciliation required.
  - [ ] Other:
- Trigger evidence:
- Trigger timestamp:
- Human instruction or decision that authorized closeout preparation:
- Any closeout action intentionally not performed:

### 5. Branch and Commit Context

- Local branch:
- Base branch:
- Commit before closeout:
- Commit after closeout:
- Origin branch state:
- git status --short before closeout:
- git status --short after closeout:
- Commit or merge SHA being recorded:
- Branches created, pushed, or deleted:
- Any branch operation intentionally not performed:

### 6. Source-of-Truth Documents Reviewed

Record each reviewed source and why it mattered.

| Source | Reviewed | Reason | Relevant finding |
| --- | --- | --- | --- |
| docs/context/BUILD_STATE.md |  |  |  |
| docs/context/AGENT_CONTEXT.md |  |  |  |
| docs/roadmap/ROADMAP.md |  |  |  |
| docs/agents/DOCUMENTATION_AGENTS.md |  |  |  |
| docs/agents/DOCUMENTATION_FRESHNESS_CHECKS.md |  |  |  |
| docs/agents/DOCUMENTATION_SYNC_EVIDENCE_PACKAGES.md |  |  |  |
| docs/agents/DOCUMENTATION_SYNC_HANDOFF_TEMPLATE.md |  |  |  |
| docs/agents/PR_EVIDENCE_PACKAGE_TEMPLATE.md |  |  |  |
| docs/agents/CLOSEOUT_EVIDENCE_PACKAGE_TEMPLATE.md |  |  |  |
| .agent/AGENT_REGISTRY.md |  |  |  |
| .agent/skills/documentation-sync/SKILL.md |  |  |  |
| Issue comments or PR comments |  |  |  |
| GitHub issue or PR state |  |  |  |

Additional reviewed sources:

- TBD.
-
- TBD.

Unavailable or intentionally skipped sources:

- TBD.
-
- TBD.

### 7. Documentation Freshness Check Evidence

- Freshness check performed:
- Freshness model used:
- Freshness scope:
- Stale documentation found:
- Missing documentation found:
- Conflicting documentation found:
- Incomplete documentation found:
- Outdated documentation found:
- Human escalation required:
- Freshness limitations or skipped checks:
- Freshness summary:

### 8. Files Changed During Closeout

| File | Change type | Reason | Closeout relevance |
| --- | --- | --- | --- |
|  |  |  |  |

Files reviewed but not changed:

- TBD.
-
- TBD.

Files intentionally out of scope:

- TBD.
-
- TBD.

### 9. Project-Memory Updates

Record updates to persistent project memory.

- BUILD_STATE updated:
- AGENT_CONTEXT updated:
- ROADMAP updated:
- Agent docs updated:
- Skill docs updated:
- Prompt or evidence templates updated:
- Learning or error pattern docs updated:
- Future feature ideas updated:
- Other memory updated:
- Project-memory summary:

### 10. Roadmap and State Updates

- Current phase before closeout:
- Current phase after closeout:
- Active issue before closeout:
- Active issue after closeout:
- Completed deliverable recorded:
- Next focus recorded:
- Roadmap status changed:
- Future milestone or phase affected:
- Any status intentionally left unchanged:
- Roadmap/state summary:

### 11. Validation Results

Record exact validation commands and results.

| Validation | Command | Result | Notes |
| --- | --- | --- | --- |
| Working tree before closeout | git status --short |  |  |
| Diff whitespace check | git diff --check |  |  |
| Cached diff whitespace check | git diff --cached --check |  |  |
| Cached diff review | git diff --cached or scoped equivalent |  |  |
| Final working tree | git status --short |  |  |
| Open PR check | gh pr list --repo yoey2112/aresforge --state open |  |  |
| Open issue check | gh issue list --repo yoey2112/aresforge --state open --limit 50 |  |  |

Additional validation:

- TBD.
-
- TBD.

Validation limitations:

- TBD.
-
- TBD.

### 12. Diff Review Summary

- Diff reviewed:
- Scope matched issue:
- Only intended files changed:
- Documentation-only boundary preserved:
- No unrelated formatting churn:
- No source-of-truth conflict introduced:
- No stale state introduced:
- No hidden automation introduced:
- Diff summary:

### 13. Human-Review Notes

- Human decisions applied:
- Human decisions still required:
- Manual review performed:
- Manual review still required:
- Owner-facing notes:
- Reviewer-facing notes:
- Any assumption that requires owner confirmation:
- Human-review summary:

### 14. Limitations and Unresolved Warnings

- Unavailable inputs:
- Unverified GitHub metadata:
- Known limitations:
- Unresolved stale documentation:
- Deferred documentation updates:
- Follow-up issues recommended:
- Items intentionally not changed:
- Limitation summary:

### 15. Protected Issue #39 Confirmation

- Issue #39 was reviewed:
- Issue #39 was not modified:
- Issue #39 was not closed:
- Issue #39 labels were not changed:
- Issue #39 milestone was not changed:
- Issue #39 remains intentionally preserved as M1 validation audit evidence:
- Any exception:
- Evidence:

### 16. Repository-Boundary Confirmation

Confirm whether any of the following were changed.

| Boundary | Changed? | Notes |
| --- | --- | --- |
| Scripts |  |  |
| Runnable automation |  |  |
| GitHub Actions workflows |  |  |
| Local operator commands |  |  |
| Auto-merge behavior |  |  |
| Autonomous approval behavior |  |  |
| Autonomous issue closure behavior |  |  |
| Repository settings |  |  |
| Branch protection |  |  |
| Rulesets |  |  |
| Secrets |  |  |
| Releases |  |  |
| Tags |  |  |
| GitHub Projects |  |  |
| PR creation, merge, or closure outside explicit scope |  |  |
| Issue closure outside explicit scope |  |  |

- Repository-boundary summary:

### 17. Next-Step Handoff Notes

- Next recommended action:
- Next issue or PR:
- Next source-of-truth docs to read:
- Known risks for the next session:
- Required validation for the next session:
- Human decision needed before continuing:
- Suggested next-chat handoff text:

### 18. Required Non-Authority Statement

This closeout evidence package is a review artifact only. It does not approve, merge, close, automate, bypass human review, replace human controls, change source-of-truth priority, or authorize future automation. Human-reviewed controls remain mandatory.

## Completion Checklist

Before using a completed closeout evidence package, confirm:

- [ ] Issue reference is present.
- [ ] PR reference is present or explicitly marked not applicable.
- [ ] Merge or closeout trigger is documented.
- [ ] Branch and commit context is documented.
- [ ] Source-of-truth documents reviewed are listed.
- [ ] Documentation freshness check evidence is included when documentation-sync work occurred.
- [ ] Source-of-truth docs were reviewed and updated before closeout when project state changed.
- [ ] The issue is not still documented as active or in progress in source-of-truth docs.
- [ ] Files changed during closeout are listed.
- [ ] Project-memory updates are summarized.
- [ ] Roadmap and state updates are summarized.
- [ ] Validation results are recorded.
- [ ] Diff review summary is included.
- [ ] Human-review notes are included.
- [ ] Limitations and unresolved warnings are included.
- [ ] Protected Issue #39 confirmation is included.
- [ ] Repository-boundary confirmation is included.
- [ ] Next-step handoff notes are included.
- [ ] Required non-authority statement is included.

## Usage Rules

The closeout evidence package template is a review artifact scaffold only. It does not run documentation-sync work, validate the repository, stage files, commit files, push branches, create PRs, approve PRs, merge PRs, close issues, bypass human review, change repository settings, replace human controls, change source-of-truth priority, implement New-CloseoutEvidencePackage, or authorize future automation.

A completed closeout evidence package may support human review and next-agent handoff, but it must not be treated as proof that closeout is approved or complete unless the human-reviewed repository state and GitHub state also support that conclusion.

During M2, all closeout evidence package preparation remains manual, advisory, and human-reviewed.
