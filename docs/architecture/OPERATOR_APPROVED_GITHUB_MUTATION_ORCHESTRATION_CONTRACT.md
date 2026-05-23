# Operator-approved GitHub Mutation Orchestration Contract

## Objective
M20 defines a narrow, explicit, operator-approved GitHub mutation orchestration model for targeted issue comments, targeted issue closeout, PR body preparation or update support, and local mutation audit logging.

This contract does not authorize broad or autonomous mutation.

## Lifecycle States
- `planned`: Mutation intent exists and is normalized, but no execution approval exists.
- `approval_required`: Intent passed planning checks and still requires explicit operator execution approval.
- `approved`: Explicit operator approval marker is present for one targeted mutation.
- `executing`: A single approved targeted mutation is in progress.
- `executed`: The targeted mutation completed and captured an execution result.
- `blocked`: The targeted mutation failed safety gates and cannot execute.
- `recovery_required`: The targeted mutation failed during execution and requires targeted recovery steps.
- `recovered`: Recovery steps were applied and the mutation attempt is accounted for.

## Boundary Contract
### Planning boundary
- Builds mutation intent, required approvals, safety checks, and dry-run outputs.
- Must not mutate GitHub.

### Approval boundary
- Requires explicit operator intent to execute one targeted mutation.
- Approval must be attached to the specific mutation type and target.

### Execution boundary
- Permitted only for one explicit target and one explicit mutation category.
- Must fail closed when target, payload, or approval is missing.

### Audit boundary
- Every attempt records intent, dry-run output, approval marker, execution result, timestamp, target, command concept, and recovery notes.
- Audit artifacts are local-only unless explicitly documented otherwise.

### Recovery boundary
- Recovery guidance must recommend targeted corrective actions only.
- No bulk or broad compensating mutations are allowed.

## Allowed Mutation Categories For M20
- Targeted issue comment for one explicit issue target.
- Targeted issue closeout for one explicit issue target with readiness checks.
- Targeted PR body preparation/update support for one explicit PR target.
- Local audit log writing for mutation planning and execution evidence.

## Excluded Mutation Categories For M20
- Bulk issue closure.
- Broad issue edits across sibling/parent sets.
- Milestone-wide mutation without explicit single-issue or single-PR targets.
- Autonomous parent closeout.
- Prior milestone mutation unless explicitly requested.
- Autonomous continuous loops or background mutation workers.

## Safety Guarantees
- Default behavior is dry-run or planning.
- Mutation execution always requires explicit operator approval.
- Parent closeout remains blocked until child readiness/accounting is confirmed.
- No sibling issue mutation from a targeted child operation.
- Every mutation path must emit audit-ready output.

## M20 Command Concepts
- `plan-github-mutation`
- `execute-github-issue-comment`
- `execute-github-issue-close`
- `prepare-pr-body-update`
- `inspect-github-mutation-audit-log`

## Required Evidence For Child Completion
- Child-specific branch, PR, validation results, and merge evidence.
- Child-specific issue evidence comment.
- Targeted issue closeout only for that child.
- Dashboard and readiness inspection after closeout.

## Non-Goals
- Autonomous broad mutation.
- Bulk issue or PR mutation.
- Parent closure before final reconciliation and child accounting.
