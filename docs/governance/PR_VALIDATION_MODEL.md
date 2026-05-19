# AresForge PR Validation Model

## Purpose

The PR validation model defines how AresForge will decide whether a pull request is ready to merge.

## Future Validation Agents

A mature PR should pass through:

- QA Agent
- Test Agent
- Documentation Agent
- PR Scoring Agent

## Initial Scoring Categories

Proposed score categories:

- Requirement fit
- Code quality
- Test coverage
- Documentation completeness
- Architecture alignment
- Security and safety risk
- Operational risk
- Rollback clarity
- Evidence quality

## Autonomy Rule

If a PR score is 90 percent or higher and the project autonomy setting allows it, the system should eventually be able to auto-merge.

## M0 Constraint

During M0, this document is a planning model only. No auto-merge behavior is enabled.
