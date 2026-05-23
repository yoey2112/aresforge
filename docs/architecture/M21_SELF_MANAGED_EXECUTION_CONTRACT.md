# M21 Self-Managed Milestone Execution Contract

This document defines the M21 execution contract for running one milestone parent issue through ordered child issues with explicit human-gated mutation boundaries.

## Required Inputs

- `parent_issue_number`
- `ordered_child_issue_sequence`
- `repo_root_path`
- `synced_main_head_sha`

Optional inputs:

- `sequential_run_state_path`
- `operator_approval_token_or_explicit_execute_flag`
- `validation_command_overrides`

## Required Outputs

- `sequential_execution_plan`
- `per_child_execution_envelope`
- `validation_plan`
- `mutation_plan_dry_run_default`
- `audit_package`
- `handoff_recovery_package`

Closeout-gated outputs:

- `targeted_child_evidence_comment_payload`
- `targeted_child_closeout_payload`
- `targeted_parent_closeout_payload_after_readiness`

## State Transitions

1. `planned`
2. `child_selected`
3. `validation_passed`
4. `mutation_planned_dry_run`
5. `mutation_approved`
6. `mutation_executed_targeted`
7. `child_closed`
8. `handoff_written`
9. `parent_readiness_verified`
10. `parent_closed_targeted`

## Safety Boundaries

- Dry-run is the default posture for any mutation-capable flow.
- Mutation execution requires explicit operator approval.
- Bulk closeout is forbidden.
- Parent closeout before all children are closed or accounted for is forbidden.
- Final reconciliation must remain the last child in sequence.
- Prior milestone mutation is forbidden by default.
- Mutation scope must remain targeted to one issue or one PR body update per action.

## Approval Boundary

Required controls before execution:

- Explicit `--execute` (or equivalent) gate.
- Explicit target identifier (`--issue` or `--pr-number`).
- Dry-run plan preview available for operator review.
- Local audit intent and execution result captured.

## Parent Closeout Readiness Boundary

Parent closeout can only proceed when:

- All children are closed or accounted for.
- Milestone evidence readiness passes.
- Parent closeout readiness reports `parent_closeout_ready: true`.
- Parent closeout readiness reports no `blocked_reasons`.

If any condition fails, parent closeout mutation is blocked.

## CLI Inspection Surface

Read-only contract inspection command:

- `python -m aresforge inspect-self-managed-milestone-execution-contract`

Boundary confirmation:

- This command does not mutate GitHub state.
