# PR Validation Skill

## Name

PR validation

## Purpose

Guide advisory pull request validation for requirement fit, scope control, documentation completeness, validation evidence, safety boundaries, and merge-readiness recommendation.

## When to use

Use this skill when reviewing an AresForge pull request, preparing PR evidence, checking documentation-only work, or producing a human-review recommendation.

## When not to use

Do not use this skill to approve, merge, auto-merge, close issues, bypass required review, or replace the PR validation model.

## Inputs

- Pull request diff, summary, linked issue, and validation evidence.
- Source-of-truth docs governing the changed area.
- Commands run and results.
- Known skipped checks, assumptions, or limitations.
- Human decisions and review comments when available.

## Outputs

- Advisory validation summary.
- Documentation impact assessment.
- Risk notes and missing evidence.
- Merge-readiness recommendation for human review.
- Clear statement that human review remains required.

## Scope boundaries

This skill covers review and evidence synthesis. It does not authorize approval, merge, auto-merge, autonomous issue closure, or repository setting changes.

## Execution boundaries

This skill is advisory and manually executed. It does not create PR scoring services, branch-protection integrations, GitHub Actions workflows, scripts, packages, or adapters.

## Human approval boundaries

Human approval is required for merge decisions, approval decisions, issue closure through merge, risk exceptions, failed validation overrides, and any change to autonomy or repository protections.

## Documentation impact

Review docs/governance/PR_VALIDATION_MODEL.md for validation categories, safeguards, evidence requirements, and decision states. Review related docs when PR content changes project memory or operating rules.

## Validation expectations

Use the validation expectations from the issue, prompt, and PR validation model. For documentation-only PRs, `git diff --check`, `git status --short`, and requested file-tree checks are usually sufficient when no runnable behavior changed.

## Evidence requirements

Report branch, commit, PR URL when available, files changed, commands run, concise results, skipped checks, documentation impact, risk level, and advisory merge-readiness state.

## Related docs

- docs/governance/PR_VALIDATION_MODEL.md
- docs/context/AGENT_CONTEXT.md
- docs/context/BUILD_STATE.md
- docs/prompts/CODEX_PROMPT_STANDARD.md
- docs/agents/AGENT_SKILLS_MODEL.md

## Lifecycle status

Draft
