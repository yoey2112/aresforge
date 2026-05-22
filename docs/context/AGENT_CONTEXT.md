# AresForge Agent Context

## Purpose

Provide minimum operating context for safe M19 sequential milestone execution with read-only planning defaults, per-child validation/evidence/closeout discipline, and recovery planning support.

## Current Operating Model

- Documentation remains source of truth.
- Active milestone context: M19 parent `#309` OPEN, children `#310-#316` CLOSED/accounted, final reconciliation `#317` OPEN and processed last.
- `run-autonomous-cycle` remains human-triggered and mode-gated.
- M19 sequential commands are human-triggered and read-only/planning by default.
- Every child issue is executed with dedicated branch, dedicated PR, dedicated validation, dedicated evidence comment, and targeted closeout.
- Parent closeout is blocked until all children are closed/accounted and readiness is proven.
- No unattended/background execution.

## Canonical Documents

- `docs/context/BUILD_STATE.md`
- `docs/context/AGENT_CONTEXT.md`
- `docs/roadmap/ROADMAP.md`
- `docs/operator/LOCAL_OPERATOR_USAGE.md`
- `docs/architecture/LOCAL_OPERATOR_WORKFLOW.md`
- `docs/architecture/SEQUENTIAL_MILESTONE_EXECUTION_CONTRACT.md`

## Current Commands

- `python -m aresforge run-autonomous-cycle --mode dry-run --parent-issue <parent> --target-issue <child>`
- `python -m aresforge run-autonomous-cycle --mode local-write --parent-issue <parent> --target-issue <child>`
- `python -m aresforge run-autonomous-cycle --mode branch-write --parent-issue <parent> --target-issue <child> --branch-name <branch> --commit-message <message>`
- `python -m aresforge run-autonomous-cycle --mode push-pr --parent-issue <parent> --target-issue <child> --branch-name <branch> --commit-message <message> --pr-title <title>`
- `python -m aresforge run-autonomous-cycle --mode closeout-eligible --parent-issue <parent> --target-issue <child> --branch-name <branch> --commit-message <message> --pr-title <title>`
- `python -m aresforge inspect-autonomous-run --run-id <id>`
- `python -m aresforge inspect-milestone-state --parent-issue <parent>`
- `python -m aresforge inspect-milestone-dashboard --parent-issue <parent>`
- `python -m aresforge check-milestone-evidence-readiness --parent-issue <parent>`
- `python -m aresforge inspect-parent-closeout-readiness --parent-issue <parent>`
- `python -m aresforge inspect-sequential-run-state --parent-issue <parent>`
- `python -m aresforge inspect-child-execution-gates --issue <issue> --parent-issue <parent>`
- `python -m aresforge plan-sequential-run-recovery --parent-issue <parent>`
- `python -m aresforge generate-sequential-handoff-package --parent-issue <parent>`
- `python -m aresforge inspect-repo-governance`

## M19 Capability Snapshot

- Sequential milestone execution contract implemented.
- Local run-state persistence and inspection implemented.
- Per-child execution gate inspection implemented.
- Sequential failure/recovery planner implemented.
- Sequential evidence/handoff package generation implemented.
- Milestone dashboard/readiness integration with sequential state and mismatch flags implemented.
- End-to-end sequential operator workflow documentation implemented.
- M19 final reconciliation in progress via `#317` (docs-only scope).

## Prohibited Behaviors

- autonomous broad mutation
- bulk issue closure
- parent closure before child sequence completion and final reconciliation
- mutation of prior milestones unless explicitly required for M19 documentation references
- background jobs, polling loops, schedulers, or hidden workers

## Validation Snapshot

- `git diff --check`
- `python -m pytest`
- `python -m aresforge inspect-repo-governance`
- `python -m aresforge inspect-milestone-dashboard --parent-issue 309`
- `python -m aresforge inspect-milestone-state --parent-issue 309`
- `python -m aresforge check-milestone-evidence-readiness --parent-issue 309`
- `python -m aresforge inspect-parent-closeout-readiness --parent-issue 309`

## Governance Note

- Project-specific milestone naming/mapping warning remains non-blocking (`milestone_naming_status.naming_ok: false`).
