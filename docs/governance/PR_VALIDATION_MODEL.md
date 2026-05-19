# AresForge PR Validation Model

## Purpose

The PR validation model defines how AresForge evaluates whether a pull request is ready for merge.

It gives future QA, Test, Documentation, and PR Scoring agents a shared review foundation while preserving the current M0 rule that all implementation work remains manually guided and manually reviewed.

During M0, this model is guidance for human-reviewed pull requests. It does not enable auto-merge, autonomous issue closure, autonomous approval, destructive automation, or any workflow that can merge or approve work without a human decision.

## Scope

This model applies to implementation pull requests for AresForge, including changes to code, tests, documentation, prompts, governance, validation evidence, workflows, and project state.

The model should be used to:

- Identify the validation agents or review perspectives required for a PR.
- Define the evidence reviewers need before deciding whether work is merge-ready.
- Score the implementation against practical categories.
- Identify risks, missing validation, and required human escalation.
- Produce a merge-readiness recommendation for human review.

This model does not replace issue acceptance criteria, source-of-truth documentation, human review, GitHub branch protections, or future release approval rules.

## M0 Manual-Review Constraint

During M0:

- All implementation work is manually guided.
- All pull requests require human review before merge.
- Validation agents may be represented by one human-guided implementation or review session.
- Agent scoring is advisory evidence only.
- No auto-merge is enabled.
- No autonomous issue closure is enabled.
- No autonomous approval is enabled.
- No destructive automation is enabled.
- GitHub may close linked issues after a human merges a PR that contains valid closing language.

If any issue, PR, prompt, script, workflow, or agent output appears to enable auto-merge, autonomous issue closure, autonomous approval, or destructive automation during M0, reviewers must treat it as a blocker and escalate to the human owner.

## Required Validation Agents

A mature AresForge PR validation flow should include these review perspectives:

- QA Agent
- Test Agent
- Documentation Agent
- PR Scoring Agent

During M0, these are required perspectives rather than autonomous services. A single Codex session or human reviewer may perform multiple perspectives, but the PR evidence should still make the relevant checks visible.

Future phases may split these perspectives into separate agents after the dashboard, validation workflows, and autonomy controls exist.

## Agent Responsibilities

### QA Agent

The QA Agent reviews whether the PR satisfies the issue and is safe to review.

Responsibilities:

- Compare the PR against the issue goal, required changes, constraints, and acceptance criteria.
- Confirm the implementation is scoped and does not include unrelated changes.
- Identify behavior, usability, regression, safety, security, and operational risks.
- Check that skipped validation is explained.
- Recommend human escalation when requirements, safety boundaries, or source-of-truth documents conflict.

### Test Agent

The Test Agent reviews whether the implementation has enough validation evidence for the change type.

Responsibilities:

- Identify the tests, checks, builds, linters, manual checks, screenshots, logs, or local AI review evidence relevant to the PR.
- Confirm requested validation commands were run and reported.
- Evaluate whether the evidence supports the stated behavior.
- Identify missing tests or checks that should block or limit merge readiness.
- Distinguish test failures caused by the PR from pre-existing or out-of-scope failures when evidence allows.

### Documentation Agent

The Documentation Agent reviews whether the PR keeps AresForge documentation current.

Responsibilities:

- Detect documentation impact from changed files, issue requirements, PR summaries, validation evidence, context docs, roadmap docs, governance docs, prompt docs, architecture docs, and release notes when available.
- Confirm required documentation updates are included.
- Confirm documentation preserves M0 manual-review and autonomy constraints.
- Flag stale documentation warnings when related docs may need follow-up but cannot be safely changed in the PR scope.
- Ensure documentation claims do not imply completed functionality, approval, merge, release, or autonomy that has not happened.

### PR Scoring Agent

The PR Scoring Agent turns validation evidence into a practical score and merge-readiness recommendation.

Responsibilities:

- Review QA, Test, and Documentation Agent findings.
- Score each required category using the scoring scale in this document.
- Identify blockers, risks, and missing evidence.
- Produce an overall advisory score.
- Assign one merge-readiness decision state.
- Explain the decision in terms that a human reviewer can verify.

During M0, the PR Scoring Agent must not approve, merge, close, or request auto-merge. Its output is evidence for manual review only.

## Scoring Categories

Each implementation PR should be scored against the categories below when applicable.

| Category | What To Evaluate |
|---|---|
| Requirement fit | The PR satisfies the issue goal, required changes, constraints, and acceptance criteria. |
| Scope control | The PR avoids unrelated changes and preserves intentional human decisions. |
| Code or content quality | The implementation is clear, maintainable, consistent with existing patterns, and practical for future work. |
| Test and validation coverage | Relevant commands, tests, builds, lint checks, manual checks, screenshots, logs, or local review evidence were performed and reported. |
| Documentation completeness | Required docs are updated, stale docs are flagged, and documentation impact is explained. |
| Architecture alignment | The PR fits current architecture, governance, roadmap, prompt standards, and source-of-truth rules. |
| Security and safety risk | The PR avoids unsafe permissions, secrets exposure, destructive actions, uncontrolled automation, and unapproved autonomy. |
| Operational risk | The PR has acceptable runtime, deployment, workflow, repository, and rollback implications. |
| Evidence quality | The PR body and final handoff provide enough evidence for a human reviewer to understand what changed and how it was validated. |

Documentation-only PRs may mark code-specific checks as not applicable, but they still need evidence quality, documentation completeness, scope control, and M0 safety review.

## Suggested Scoring Scale

Use a 0 to 5 score for each applicable category.

| Score | Meaning |
|---:|---|
| 0 | Missing, contradicted, or unsafe. |
| 1 | Major gaps; cannot support merge readiness. |
| 2 | Partial coverage with material unresolved concerns. |
| 3 | Adequate for limited review, with known limitations. |
| 4 | Strong evidence with minor non-blocking issues. |
| 5 | Complete, clear, and low-risk for the PR scope. |

Suggested overall score:

1. Score each applicable category from 0 to 5.
2. Exclude categories that are genuinely not applicable and explain why.
3. Divide the earned points by the maximum applicable points.
4. Convert the result to a percentage.

Example:

- 38 earned points across 45 applicable points = 84 percent.

The percentage is an advisory review signal. During M0, it must not cause automatic approval, merge, or issue closure.

## Evidence Requirements

Every PR validation should include enough evidence for a human reviewer to reproduce or understand the result.

Required evidence:

- Branch name.
- Commit hash.
- Files changed.
- Issue or requirement summary.
- Validation commands or checks run.
- Concise result of each command or check.
- Documentation impact summary.
- Known risks, assumptions, skipped checks, and limitations.
- Merge-readiness decision state.

Additional evidence when relevant:

- Test output.
- Build or lint output.
- Screenshots or rendered artifacts.
- Logs or workflow artifacts.
- Local AI review output.
- Manual QA notes.
- Rollback notes.
- Stale documentation warnings.

Evidence must distinguish between verified facts, reviewer judgment, and future recommendations.

## Risk Handling

Reviewers and validation agents should classify risk before recommending merge readiness.

Suggested risk levels:

| Level | Meaning | Expected Handling |
|---|---|---|
| Low | Narrow change with clear evidence and limited blast radius. | Normal human review. |
| Medium | Some uncertainty, broader docs or code impact, skipped checks, or moderate operational effect. | Human review with explicit risk notes. |
| High | Security, data, workflow, automation, release, permission, architecture, or major behavior impact. | Human escalation required before merge. |
| Blocked | Missing evidence, failed required validation, source-of-truth conflict, unsafe autonomy, or destructive behavior. | Do not recommend merge until resolved. |

Risk notes should describe:

- What could go wrong.
- Whether the risk is introduced by the PR or pre-existing.
- What evidence reduces the risk.
- What follow-up or human decision is needed.

## Required Safeguards

Validation agents and reviewers must preserve these safeguards:

- Treat repository documentation and explicit human decisions as source of truth during M0.
- Keep validation advisory unless and until a later governance document explicitly changes autonomy level.
- Do not enable auto-merge during M0.
- Do not enable autonomous issue closure during M0.
- Do not enable autonomous approval during M0.
- Do not create or modify destructive automation unless a human-approved issue explicitly requires it.
- Do not approve changes that add secrets, change repository permissions, alter runner security settings, publish releases, or promote autonomy without explicit human approval.
- Do not treat future-state documentation as current functionality.
- Do not score around failed required validation without documenting the failure and escalation path.
- Do not stage or recommend merging unrelated changes.

## Human Escalation Rules

Validation agents must escalate to the human owner before recommending merge readiness when:

- Source-of-truth documentation conflicts with the issue or PR.
- Required validation fails and the fix is outside the PR scope.
- Required evidence is missing or cannot be produced.
- The PR changes security, secrets, permissions, repository visibility, runner settings, release behavior, or destructive operations.
- The PR appears to enable auto-merge, autonomous issue closure, autonomous approval, or destructive automation during M0.
- The PR introduces high-risk architecture or operational changes.
- The work depends on unavailable credentials, external approvals, or unclear ownership.
- Unrelated local changes prevent safe staging or review.
- The reviewer cannot distinguish implemented behavior from future-state documentation.

Escalation should name the blocker, affected files or commands, known evidence, and the decision needed from the human owner.

## Merge-Readiness Decision States

The PR Scoring Agent should assign exactly one advisory decision state.

| State | Meaning |
|---|---|
| READY_FOR_HUMAN_REVIEW | Evidence is adequate and no known blockers remain. Human review and merge decision still required. |
| READY_WITH_LIMITATIONS | Evidence is mostly adequate, but there are non-blocking limitations, skipped checks, or follow-up recommendations. Human review must decide whether the risk is acceptable. |
| NEEDS_CHANGES | The PR has fixable gaps, failed checks, missing docs, unclear evidence, or scope issues that should be addressed before merge. |
| NEEDS_HUMAN_ESCALATION | A human decision is required because of risk, conflict, missing authority, or unclear source-of-truth boundaries. |
| BLOCKED | The PR should not proceed until a required input, validation result, conflict, or safety issue is resolved. |

No decision state is an approval during M0. A human reviewer remains the final authority.

## Future 90 Percent Auto-Merge Concept

In a later phase, AresForge may support controlled auto-merge for low-risk PRs that score at or above 90 percent.

That future behavior would require all of the following before it could be enabled:

- A governance update that raises the project autonomy level.
- Explicit human approval for controlled auto-merge.
- Branch protection and repository permission review.
- Reliable validation workflows and auditable evidence.
- Clear risk thresholds and exclusion categories.
- Escalation behavior for failed checks, high-risk changes, missing evidence, and source-of-truth conflicts.
- A way to disable or pause auto-merge quickly.

The 90 percent concept is future behavior only. It is not active during M0, does not authorize any current workflow change, and must not be interpreted as approval for autonomous merge, autonomous issue closure, autonomous approval, or destructive automation.

## Initial M0 Validation Flow

For M0 implementation PRs, use this manual flow:

1. Read the issue, PR summary, changed files, and relevant source-of-truth documentation.
2. Confirm the PR scope matches the issue.
3. Review validation evidence and identify skipped checks.
4. Review documentation impact.
5. Score applicable categories.
6. Classify risk.
7. Assign one merge-readiness decision state.
8. Report evidence, limitations, and escalation needs in the PR or final handoff.
9. Leave the merge decision to the human reviewer.

This flow is intentionally practical and lightweight so it can support M0 documentation-only PRs as well as future implementation PRs.
