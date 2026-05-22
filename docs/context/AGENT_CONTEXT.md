# AresForge Agent Context

## Purpose

Provide minimum operating context for safe M16 controlled autonomous execution with explicit mode gates and audit evidence.

## Current Operating Model

- Documentation remains source of truth.
- `run-autonomous-cycle` is human-triggered and mode-gated.
- Defaults remain safe and read-only.
- Every run and step is persisted in `autonomous_runs`/`run_steps`.
- Every run emits evidence artifacts.
- No unattended/background execution.

## Canonical Documents

- `docs/architecture/CONTROLLED_AUTONOMOUS_GITHUB_EXECUTION_CONTRACT.md`
- `docs/architecture/RUNNABLE_SKELETON.md`
- `docs/architecture/REPOSITORY_GOVERNANCE_CONTRACT.md`
- `docs/operator/LOCAL_OPERATOR_USAGE.md`
- `docs/context/BUILD_STATE.md`
- `docs/roadmap/ROADMAP.md`

## Current Commands

- `python -m aresforge run-autonomous-cycle --mode dry-run --parent-issue <parent> --target-issue <child>`
- `python -m aresforge run-autonomous-cycle --mode local-write --parent-issue <parent> --target-issue <child>`
- `python -m aresforge run-autonomous-cycle --mode branch-write --parent-issue <parent> --target-issue <child> --branch-name <branch> --commit-message <message>`
- `python -m aresforge run-autonomous-cycle --mode push-pr --parent-issue <parent> --target-issue <child> --branch-name <branch> --commit-message <message> --pr-title <title>`
- `python -m aresforge run-autonomous-cycle --mode closeout-eligible --parent-issue <parent> --target-issue <child> --branch-name <branch> --commit-message <message> --pr-title <title>`
- `python -m aresforge inspect-autonomous-run --run-id <id>`
- `python -m aresforge inspect-repo-governance`

## M16 Capability Snapshot

- Controlled autonomous execution contract implemented.
- Explicit modes implemented: `dry-run`, `local-write`, `branch-write`, `push-pr`, `closeout-eligible`.
- Fail-closed safety gates implemented for higher-permission modes.
- Branch/commit steps implemented for `branch-write` and above.
- Push/PR steps implemented for `push-pr` and above.
- Closeout gating and issue-closure path implemented for `closeout-eligible` only.
- Run inspection/reporting implemented via `inspect-autonomous-run`.
- Evidence package generation implemented for all run outcomes.

## Prohibited Behaviors

- autonomous mutation without explicit command invocation
- mutation in `dry-run`
- GitHub mutation in `local-write` or `branch-write`
- push/PR outside explicit `push-pr` / `closeout-eligible`
- issue closure outside explicit `closeout-eligible`
- automatic PR merge
- background jobs, polling loops, schedulers, or hidden workers

## Validation Snapshot

- `git diff --check`
- `python -m pytest`
- `python -m aresforge inspect-repo-governance`
- `run-autonomous-cycle` dry-run/local-write success checks
- `run-autonomous-cycle` higher-mode fail-closed checks
- `inspect-autonomous-run` DB evidence inspection

## Governance Note

- Project-specific milestone naming/mapping warning remains non-blocking (`milestone_naming_status.naming_ok: false`).
