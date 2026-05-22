# Controlled Autonomous GitHub Execution Contract

## Purpose
M16 defines a controlled, human-triggered autonomous execution loop that can progress from planning to bounded local and GitHub mutation through explicit command modes.

## Command Surfaces
- `python -m aresforge run-autonomous-cycle`
- `python -m aresforge inspect-autonomous-run`

## Mode Matrix
- `dry-run`: Read-only planning and validation only. No repository or GitHub mutation.
- `local-write`: Local run/evidence lifecycle progression only. No GitHub mutation.
- `branch-write`: Allows local branch and commit mutation only.
- `push-pr`: Allows branch-write capabilities plus push and PR creation.
- `closeout-eligible`: Allows push-pr capabilities plus issue closure after explicit closeout gates pass.

## Required Safety Guarantees
- Read-only-safe defaults.
- No mutation in `dry-run`.
- No GitHub mutation in `local-write` or `branch-write`.
- No push/PR creation unless mode is exactly `push-pr` (or `closeout-eligible`, which is a higher permission mode).
- No issue closure unless mode is exactly `closeout-eligible`.
- No automatic PR merge.
- No background scheduling, polling, or unattended execution.
- Higher-permission modes fail closed when required inputs are missing.

## Lifecycle Tracking
- Every autonomous run is tracked in `autonomous_runs`.
- Every lifecycle stage and mutation attempt is tracked in `run_steps`.
- Run state transitions are explicit and auditable (`running`, `completed`, `failed`).

## Gating Requirements
- Common gates: required source-of-truth docs present, validation commands defined.
- Branch-write gates: explicit `branch_name`, explicit `commit_message`.
- Push-pr gates: branch-write gates plus explicit PR metadata.
- Closeout-eligible gates: successful validation, mapped issue/PR linkage (`pr_number` + `pr_url`), merged PR evidence, explicit target issue.

## Evidence Requirements
- Every run generates an evidence package.
- Every mutation step records structured inputs/outputs and pass/fail status.
- Failure paths still generate evidence and persist run state.

## Non-Goals
- Automatic merge or release flows.
- Background or continuous autonomous operation.
- Mutation outside the explicit mode boundary contract.
