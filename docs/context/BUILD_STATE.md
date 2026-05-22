# AresForge Build State

## Current Phase

M18 milestone execution automation ergonomics and operator-driven closeout workflows

## Current Goal

Complete M18 final source-of-truth reconciliation issue #301 after implementation children #295/#296/#297/#298/#299/#300 were merged and closed with issue-specific evidence mapping.

## Current Repository State

- M18 parent issue: `#294` (open, expected to remain open until #301 closeout is complete and reviewed)
- M18 child issue status:
  - `#295` CLOSED via PR `#302`
  - `#296` CLOSED via PR `#303`
  - `#297` CLOSED via PR `#304`
  - `#298` CLOSED via PR `#305`
  - `#299` CLOSED via PR `#306`
  - `#300` CLOSED via PR `#307`
  - `#301` OPEN (final reconciliation only, processed last)
- Current main HEAD before #301 implementation: `b3dfc65` (`Merge pull request #307`)
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

## M18 Capability Snapshot

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
- `python -m aresforge inspect-milestone-dashboard --parent-issue <parent>` unified read-only milestone dashboard
- `python -m aresforge generate-child-closeout-script --issue <issue>` read-only operator script generator
- `python -m aresforge generate-evidence-comment-template --issue <issue>` read-only issue-specific evidence template generator
- `python -m aresforge inspect-parent-closeout-readiness --parent-issue <parent>` read-only parent closeout readiness report
- schema-driven evidence mapping support with structured marker parsing and legacy compatibility fallback
- Explicit safety posture preserved:
  - no bulk closeout
  - no implicit mutation
  - no closeout without explicit evidence mapping
  - no parent closeout before children are closed/accounted for
  - no mutation of M16 issues

## Validation Baseline For Current M18 Scope (#295/#296/#297/#298/#299/#300/#301)

- `git diff --check`
- `python -m pytest`
- `python -m aresforge inspect-repo-governance`
- `python -m aresforge inspect-milestone-state --parent-issue 294`
- `python -m aresforge inspect-milestone-dashboard --parent-issue 294`
- `python -m aresforge plan-milestone-execution-queue --parent-issue 294`
- `python -m aresforge check-issue-evidence-readiness --issue 301`
- `python -m aresforge check-milestone-evidence-readiness --parent-issue 294`
- `python -m aresforge plan-milestone-final-reconciliation --parent-issue 294`
- `python -m aresforge inspect-parent-closeout-readiness --parent-issue 294`

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
- parent closeout before all child issues are closed/accounted and final reconciliation is complete
