# Runnable Skeleton

## Purpose

Describe the implemented human-triggered operator surface after M16 controlled autonomous execution loop delivery.

## Operator Shape

Command entrypoint:

- `python -m aresforge`

## Current Additions

- `run-autonomous-cycle`: explicit controlled execution loop with mode-gated mutation boundaries.
- `inspect-autonomous-run`: inspect DB-backed run lifecycle and step history.
- `inspect-milestone-state`: read-only milestone parent/child issue state inspection.
- `inspect-milestone-dashboard`: unified read-only milestone execution dashboard across inspection/planning/readiness signals.
- `plan-milestone-execution-queue`: read-only, planning-only milestone child execution queue planner.
- `check-issue-evidence-readiness`: read-only issue evidence completeness classification.
- `check-milestone-evidence-readiness`: read-only milestone-level evidence readiness summary.
- `plan-milestone-final-reconciliation`: planning-only milestone final reconciliation readiness planner.
- Existing planning/validation/reporting commands remain available and compatible.

## M16 Capability Contract Alignment

- Contract authority: `docs/architecture/CONTROLLED_AUTONOMOUS_GITHUB_EXECUTION_CONTRACT.md`.
- Implemented mode set:
  - `dry-run`
  - `local-write`
  - `branch-write`
  - `push-pr`
  - `closeout-eligible`
- Implemented execution boundaries:
  - branch creation/commit only in `branch-write` or higher
  - push/PR only in `push-pr` or higher
  - issue closeout only in `closeout-eligible`
- Implemented persistence:
  - `autonomous_runs` for run lifecycle state
  - `run_steps` for ordered mutation/evaluation evidence

## Automation Boundary

- Human-triggered only.
- Read-only-safe defaults.
- Fail-closed gates for higher-permission modes.
- No automatic PR merge.
- No background jobs, polling loops, or schedulers.
- Evidence package generation for all run outcomes.
- For M17 milestone planning surfaces: no issue closure, no PR creation, no issue comments, and no mutation of M16 issues.
- For M18 milestone dashboard surface: read-only aggregation only; no issue closure, PR creation, comments, or broad mutation.
- Parent issue remains open until child issues are closed/accounted and final reconciliation is merged/accounted.

## Validation Bundle

- `git diff --check`
- `python -m pytest`
- `python -m aresforge inspect-repo-governance`
- `python -m aresforge run-autonomous-cycle --mode dry-run --parent-issue <parent> --target-issue <target> --validation-command "python -m aresforge inspect-repo-governance"`
- `python -m aresforge run-autonomous-cycle --mode local-write --parent-issue <parent> --target-issue <target> --validation-command "python -m aresforge inspect-repo-governance"`
- `python -m aresforge run-autonomous-cycle --mode branch-write --parent-issue <parent> --target-issue <target> --validation-command "python -m aresforge inspect-repo-governance"` (fail-closed check without branch/commit inputs)
- `python -m aresforge run-autonomous-cycle --mode push-pr --parent-issue <parent> --target-issue <target> --validation-command "python -m aresforge inspect-repo-governance"` (fail-closed check without branch/commit/PR inputs)
- `python -m aresforge run-autonomous-cycle --mode closeout-eligible --parent-issue <parent> --target-issue <target> --validation-command "python -m aresforge inspect-repo-governance"` (fail-closed check without branch/commit/PR inputs)
- `python -m aresforge inspect-autonomous-run --run-id <id>`

## Follow-Up Candidates

1. Tighten closeout gates with stricter PR-to-issue linkage inspection using deterministic GitHub evidence checks.
2. Add richer run inspection summaries and filtered views.
3. Add explicit no-op local-write step typing when no file mutation occurs.
4. Add optional branch-write integration tests in a disposable local fixture repository.
5. Extend M17 milestone orchestration beyond inspection only after explicit contract-gated approval paths.
