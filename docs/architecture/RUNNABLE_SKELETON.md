# Runnable Skeleton

## Purpose

Describe the implemented human-triggered local operator surface after M15 self-managed milestone planning and run queue/script generation delivery.

## Operator Shape

Command entrypoint:

- `python -m aresforge`

## Current Additions

- `plan-agent-queue`: read-only governance-aware intake and queue planning.
- `report-batch-readiness`: read-only multi-issue validation summary.
- `plan-batch-closeout`: read-only by default; optional explicit local snapshot write.
- `generate-sprint-issue-script`: output-only by default; optional explicit local planning write.
- `plan-sprint-issues`: read-only deterministic sprint issue planning with human-gated script output.
- `plan-self-managed-milestone`: read-only deterministic milestone planning by default; `local-write` persists local DB run queue state.
- `generate-self-managed-issue-script`: read-only deterministic script generation from derived planning or DB-backed run queue state.
- `inspect-planning-state`: read-only local planning-state summary.
- `compare-planning-state`: read-only local planning-state drift comparison.
- `inspect-closeout-planning-drift`: read-only planning-state versus live closeout child discovery comparison.

## M15 Capability Contract Alignment

- Contract authority: `docs/architecture/SELF_MANAGED_MILESTONE_PLANNING_CONTRACT.md`.
- Implemented M15 subset:
  - `plan-self-managed-milestone` (read-only)
  - `plan-self-managed-milestone --mode local-write` (local DB write)
  - DB-backed `autonomous_runs` and `run_steps`
  - queue advancement/current-ready target derivation
  - `generate-self-managed-issue-script`
  - derived read-only script generation
  - DB-backed script generation using `--run-id`
- Not implemented in M15:
  - autonomous/higher-permission execution modes (`branch-write`, `pr-write`, `closeout-write`, `full-auto`)
  - autonomous GitHub mutation paths

## Automation Boundary

- Human-triggered only.
- Read-only/output-only defaults.
- Explicit local DB writes only in `local-write` mode.
- No autonomous GitHub mutation.
- No automatic issue closure.
- No automatic PR merge.
- No automatic branch creation.
- No background jobs, polling loops, or schedulers.
- Generated mutation scripts are copy/paste output requiring human review and manual execution.

## Validation Bundle

- `git diff --check`
- `python -m pytest`
- `python -m aresforge inspect-repo-governance`
- `python -m aresforge plan-self-managed-milestone`
- `python -m aresforge plan-self-managed-milestone --mode local-write`
- `python -m aresforge generate-self-managed-issue-script`

## Follow-Up Candidates

1. Milestone naming/mapping cleanup (non-blocking warning).
2. Next autonomy milestone toward local autonomous execution preparations.
3. Generalized sequencing beyond M15 bounded sequence.
4. Source-of-truth reconciliation automation.
5. Controlled PR-write mode in a future milestone.
