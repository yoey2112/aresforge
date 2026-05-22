# AresForge Agent Context

## Purpose

Provide minimum operating context for safe M18 milestone execution, including read-only inspection, planning-only queue guidance, evidence mapping checks, and operator-reviewed closeout flow.

## Current Operating Model

- Documentation remains source of truth.
- `run-autonomous-cycle` is human-triggered and mode-gated.
- `inspect-milestone-state` is human-triggered and strictly read-only.
- `plan-milestone-execution-queue` is human-triggered and strictly planning-only.
- `check-issue-evidence-readiness` and `check-milestone-evidence-readiness` are human-triggered and strictly read-only.
- `plan-milestone-final-reconciliation` is human-triggered and strictly planning-only.
- `inspect-milestone-dashboard` is human-triggered and strictly read-only.
- `generate-evidence-comment-template` and `generate-child-closeout-script` are read-only generators.
- `inspect-parent-closeout-readiness` is human-triggered and strictly read-only.
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
- `docs/architecture/MILESTONE_EXECUTION_PLAN_CONTRACT.md`

## Current Commands

- `python -m aresforge run-autonomous-cycle --mode dry-run --parent-issue <parent> --target-issue <child>`
- `python -m aresforge run-autonomous-cycle --mode local-write --parent-issue <parent> --target-issue <child>`
- `python -m aresforge run-autonomous-cycle --mode branch-write --parent-issue <parent> --target-issue <child> --branch-name <branch> --commit-message <message>`
- `python -m aresforge run-autonomous-cycle --mode push-pr --parent-issue <parent> --target-issue <child> --branch-name <branch> --commit-message <message> --pr-title <title>`
- `python -m aresforge run-autonomous-cycle --mode closeout-eligible --parent-issue <parent> --target-issue <child> --branch-name <branch> --commit-message <message> --pr-title <title>`
- `python -m aresforge inspect-autonomous-run --run-id <id>`
- `python -m aresforge inspect-milestone-state --parent-issue <parent>`
- `python -m aresforge plan-milestone-execution-queue --parent-issue <parent>`
- `python -m aresforge check-issue-evidence-readiness --issue <issue>`
- `python -m aresforge check-milestone-evidence-readiness --parent-issue <parent>`
- `python -m aresforge plan-milestone-final-reconciliation --parent-issue <parent>`
- `python -m aresforge inspect-milestone-dashboard --parent-issue <parent>`
- `python -m aresforge generate-evidence-comment-template --issue <issue>`
- `python -m aresforge generate-child-closeout-script --issue <issue>`
- `python -m aresforge inspect-parent-closeout-readiness --parent-issue <parent>`
- `python -m aresforge inspect-repo-governance`

## M18 Capability Snapshot

- Controlled autonomous execution contract implemented.
- Explicit modes implemented: `dry-run`, `local-write`, `branch-write`, `push-pr`, `closeout-eligible`.
- Fail-closed safety gates implemented for higher-permission modes.
- Branch/commit steps implemented for `branch-write` and above.
- Push/PR steps implemented for `push-pr` and above.
- Closeout gating and issue-closure path implemented for `closeout-eligible` only.
- Run inspection/reporting implemented via `inspect-autonomous-run`.
- Evidence package generation implemented for all run outcomes.
- Read-only milestone state inspection with parent/child summary, lineage hints, and evidence hints.
- Planning-only milestone execution queue guidance with explicit non-execution safety gates.
- Evidence completeness and duplicate/no-op reuse recommendation checks with mutation disabled.
- Planning-only milestone final reconciliation readiness planner with explicit non-mutation outputs (`close_issues: false`, `create_pr: false`, `comment_on_issue: false`, `mutation_allowed: false`).
- Unified read-only milestone dashboard implemented.
- Child closeout script generator implemented (operator-reviewed, not auto-executed).
- Evidence comment template generator implemented with optional structured evidence block markers.
- Schema-driven evidence mapping detection implemented with malformed/duplicate/conflict safeguards and legacy compatibility.
- Parent closeout readiness inspection implemented with explicit lineage/accounted checks and blocked reasons.
- Final reconciliation remains docs-focused and must be sequenced last.

## Prohibited Behaviors

- autonomous mutation without explicit command invocation
- mutation in `dry-run`
- GitHub mutation in `local-write` or `branch-write`
- push/PR outside explicit `push-pr` / `closeout-eligible`
- issue closure outside explicit `closeout-eligible`
- automatic PR merge
- background jobs, polling loops, schedulers, or hidden workers
- milestone inspection command that mutates GitHub state
- milestone queue planner that executes issue work or mutates GitHub state
- evidence readiness checker that closes issues, creates PRs, comments, or mutates GitHub state
- final reconciliation planner that closes issues, creates PRs, comments, or mutates GitHub state
- parent closeout readiness command that closes parent/children, comments, or mutates GitHub state
- mutation of M16 issues from M17 planning/reconciliation flows
- bulk issue closure during milestone child execution

## Validation Snapshot

- `git diff --check`
- `python -m pytest`
- `python -m aresforge inspect-repo-governance`
- `python -m aresforge inspect-milestone-state --parent-issue <parent>`
- `python -m aresforge plan-milestone-execution-queue --parent-issue <parent>`
- `python -m aresforge check-issue-evidence-readiness --issue <issue>`
- `python -m aresforge check-milestone-evidence-readiness --parent-issue <parent>`
- `python -m aresforge plan-milestone-final-reconciliation --parent-issue <parent>`
- `python -m aresforge inspect-parent-closeout-readiness --parent-issue <parent>`

## Governance Note

- Project-specific milestone naming/mapping warning remains non-blocking (`milestone_naming_status.naming_ok: false`).
