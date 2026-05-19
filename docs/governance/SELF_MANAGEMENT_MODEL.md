# AresForge Self-Management Model

## Principle

AresForge must become its own first customer.

## Temporary Source of Truth

Until the dashboard exists, GitHub and documentation are the source of truth.

## Managed Project State

The AresForge project state should include:

- Project name
- GitHub repo
- Project stage
- Completion percentage
- Current milestone
- Current task
- Assigned agent
- Task status
- Blockers
- AI summary
- Feature list
- Cost and usage tracking
- Next step

## Autonomy Levels

Future autonomy should be configurable per project.

Initial proposed levels:

- Level 0: Human executes everything manually
- Level 1: Agents draft plans and prompts only
- Level 2: Agents create issues and PRs, human merges
- Level 3: Agents validate and recommend merge
- Level 4: Agents auto-merge low-risk PRs above a configured score
- Level 5: Agents manage full release loops with human escalation only

## M0 Constraint

During M0, all changes are manually reviewed and committed by the human-guided implementation process.
