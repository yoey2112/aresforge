# AresForge Build State

## Current Phase

M17 Self-managed milestone orchestration after controlled autonomous execution

## Current Goal

Deliver M17 issue #270 contract authority, #271 read-only milestone inspection, #272 planning-only milestone execution queue guidance, #273/#274 evidence completeness plus duplicate/no-op reuse planning, #275 final reconciliation planning, and #276 source-of-truth reconciliation on active PR #277 without introducing new mutation surfaces.

## Current Repository State

- M16 baseline commit: `1c5cacd` (`M16 final source-of-truth reconciliation (#268)`)
- M17 parent issue: `#269`
- Active M17 implementation PR: `#277` (`m17/270-271-contract-and-inspector` -> `main`)
- Current M17 implementation scope on branch/PR: `#270`, `#271`, `#272`, `#273`, `#274`, `#275`, and `#276`
- Issue closure status for M17 scope: all child issues currently open pending merge/evidence mapping
- Parent #269 status expectation: remains open until all children are closed/accounted for
- Governance inspection: `ok: true`
- Known non-blocking warning: `milestone_naming_status.naming_ok: false`

## Current Source Of Truth

- `docs/context/BUILD_STATE.md`
- `docs/context/AGENT_CONTEXT.md`
- `docs/roadmap/ROADMAP.md`
- `docs/operator/LOCAL_OPERATOR_USAGE.md`
- `docs/architecture/RUNNABLE_SKELETON.md`
- `docs/architecture/CONTROLLED_AUTONOMOUS_GITHUB_EXECUTION_CONTRACT.md`
- `docs/architecture/MILESTONE_EXECUTION_PLAN_CONTRACT.md`

## M16/M17 Capability Snapshot

- Contract authority: `docs/architecture/CONTROLLED_AUTONOMOUS_GITHUB_EXECUTION_CONTRACT.md`
- `python -m aresforge run-autonomous-cycle`
- `python -m aresforge inspect-autonomous-run`
- Supported autonomous execution modes:
  - `dry-run`
  - `local-write`
  - `branch-write`
  - `push-pr`
  - `closeout-eligible`
- DB-backed lifecycle persistence in `autonomous_runs` and `run_steps`
- Explicit fail-closed gate evaluation before higher-permission mutation
- Step-level mutation/evaluation evidence with run-level evidence artifact generation
- `python -m aresforge inspect-milestone-state --parent-issue <parent>` read-only milestone state inspector
- `python -m aresforge plan-milestone-execution-queue --parent-issue <parent>` read-only milestone execution queue planner
- `python -m aresforge check-issue-evidence-readiness --issue <issue>` read-only issue evidence completeness checker
- `python -m aresforge check-milestone-evidence-readiness --parent-issue <parent>` read-only milestone evidence readiness checker
- `python -m aresforge plan-milestone-final-reconciliation --parent-issue <parent>` planning-only milestone final reconciliation planner
- Explicit safety posture preserved:
  - no bulk closeout
  - no implicit mutation
  - no closeout without explicit evidence mapping
  - no parent closeout before children are closed/accounted for
  - no mutation of M16 issues

## Validation Baseline For Current M17 Scope (#270/#271/#272/#273/#274/#275/#276)

- `git diff --check`
- `python -m pytest`
- `python -m aresforge inspect-repo-governance`
- `python -m aresforge inspect-milestone-state --parent-issue 269`
- `python -m aresforge plan-milestone-execution-queue --parent-issue 269`
- `python -m aresforge check-issue-evidence-readiness --issue 270`
- `python -m aresforge check-milestone-evidence-readiness --parent-issue 269`
- `python -m aresforge plan-milestone-final-reconciliation --parent-issue 269`

## Boundaries

Allowed:

- human-triggered command execution
- read-only defaults
- explicit mode-gated local and GitHub mutation
- DB run/step tracking for every autonomous run
- evidence artifact generation for every run

Not authorized:

- mutation in `dry-run`
- GitHub mutation in `local-write` or `branch-write`
- push/PR creation outside explicit `push-pr`/`closeout-eligible`
- issue closure outside explicit `closeout-eligible`
- automatic PR merge
- background jobs, polling loops, schedulers, or unattended execution
