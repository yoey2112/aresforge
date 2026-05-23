# AresForge Agent Context

## Purpose

Provide minimum operating context for safe M20 operator-approved GitHub mutation orchestration with dry-run defaults, explicit approval gates, audit logging, targeted closeout safety checks, and final reconciliation discipline.

## Current Operating Model

- Documentation remains source of truth.
- Active milestone context: M20 parent `#326` OPEN, children `#327-#333` CLOSED/accounted, final reconciliation `#334` OPEN and processed last.
- Mutation planning/execution commands are human-triggered and narrow-scope.
- Mutation execution defaults to dry-run/planning and requires explicit operator approval markers for execute mode.
- Every child issue is executed with dedicated branch, dedicated PR, dedicated validation, dedicated evidence comment, and targeted closeout.
- Parent closeout is blocked until all children are closed/accounted and readiness is proven.
- No unattended/background execution.

## Canonical Documents

- `docs/context/BUILD_STATE.md`
- `docs/context/AGENT_CONTEXT.md`
- `docs/roadmap/ROADMAP.md`
- `docs/operator/LOCAL_OPERATOR_USAGE.md`
- `docs/architecture/OPERATOR_APPROVED_GITHUB_MUTATION_ORCHESTRATION_CONTRACT.md`
- `docs/architecture/LOCAL_OPERATOR_WORKFLOW.md`

## Current Commands

Mutation planning/execution:

- `python -m aresforge plan-github-mutation`
- `python -m aresforge execute-github-issue-comment`
- `python -m aresforge execute-github-issue-close`
- `python -m aresforge prepare-pr-body-update`
- `python -m aresforge inspect-github-mutation-audit-log`

Readiness/governance:

- `python -m aresforge inspect-repo-governance`
- `python -m aresforge inspect-milestone-dashboard --parent-issue <parent>`
- `python -m aresforge inspect-milestone-state --parent-issue <parent>`
- `python -m aresforge check-milestone-evidence-readiness --parent-issue <parent>`
- `python -m aresforge inspect-parent-closeout-readiness --parent-issue <parent>`

## M20 Capability Snapshot

- M20 mutation orchestration contract implemented and documented.
- Structured mutation intent planning implemented (`plan-github-mutation`).
- Targeted issue comment execution path with safeguards implemented.
- Targeted issue close execution path with readiness gates implemented.
- PR body/update helper with structured validation summary support implemented.
- Local mutation audit log append/inspect support implemented.
- End-to-end operator-approved mutation workflow documentation implemented.
- M20 final reconciliation in progress via `#334` (docs-only scope).
- M20 PR sequence to date: `#335` through `#341`.

## Prohibited Behaviors

- autonomous broad mutation
- bulk issue closure
- parent closure before child sequence completion and final reconciliation
- mutation of prior milestones unless explicitly required for M20 documentation references
- background jobs, polling loops, schedulers, or hidden workers

## Validation Snapshot

- `git diff --check`
- `python -m pytest`
- `python -m aresforge inspect-repo-governance`
- `python -m aresforge inspect-milestone-dashboard --parent-issue 326`
- `python -m aresforge inspect-milestone-state --parent-issue 326`
- `python -m aresforge check-milestone-evidence-readiness --parent-issue 326`
- `python -m aresforge inspect-parent-closeout-readiness --parent-issue 326`

## Governance Notes

- Project-specific milestone naming/mapping warning remains non-blocking (`milestone_naming_status.naming_ok: false`).
- M20 child discovery mismatch remains present in read-only milestone inspectors for parent `#326` due to lineage parsing expectations; this is tracked as a non-blocking warning unless/until parent closeout readiness depends on that lineage signal.
