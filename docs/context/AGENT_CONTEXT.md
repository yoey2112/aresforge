# AresForge Agent Context

## Purpose

Provide minimum operating context for safe M21 self-managed milestone execution with read-only-first planning, deterministic child sequencing, targeted mutation boundaries, and parent closeout readiness gating.

## Current Operating Model

- Active milestone context: parent `#345` OPEN; children `#346-#352` CLOSED/accounted; final reconciliation child `#353` OPEN and processed last.
- New M21 simulation command provides end-to-end dry-run execution rehearsal without mutation.
- Child execution remains one-branch, one-PR, one-evidence-comment, one-targeted-closeout.
- Parent closeout remains blocked until all children are closed/accounted and readiness checks explicitly pass.
- GitHub issue truth remains authoritative; local run/handoff artifacts are advisory support only.

## Canonical Documents

- `docs/context/BUILD_STATE.md`
- `docs/context/AGENT_CONTEXT.md`
- `docs/roadmap/ROADMAP.md`
- `docs/operator/LOCAL_OPERATOR_USAGE.md`
- `docs/architecture/M21_SELF_MANAGED_EXECUTION_CONTRACT.md`
- `docs/architecture/RUNNABLE_SKELETON.md`

## Current M21 Commands

- `python -m aresforge inspect-self-managed-milestone-execution-contract`
- `python -m aresforge simulate-self-managed-milestone-execution --parent-issue <parent>`
- `python -m aresforge run-sequential-child-closeout-flow --parent-issue <parent> --child-issue <child> --comment-body "<body>"`
- `python -m aresforge generate-sequential-closeout-execution-package --parent-issue <parent> --child-issue <child>`
- `python -m aresforge generate-self-managed-milestone-handoff --parent-issue <parent> --completed-child <child> --next-child <next-child>`

## M21 PR Mapping

- `#354` -> child `#346`
- `#355` -> child `#347`
- `#356` -> child `#348`
- `#357` -> child `#349`
- `#358` -> child `#350`
- `#359` -> child `#351`
- `#360` -> child `#352`
- next PR reserved for child `#353` reconciliation

## Prohibited Behaviors

- autonomous broad mutation
- bulk issue closure
- parent closeout before all children are closed/accounted for
- prior milestone mutation unless explicitly required
- nested markdown fences inside PowerShell here-string issue/comment bodies

## Validation Snapshot

- `git diff --check`
- `python -m pytest`
- `python -m aresforge inspect-repo-governance`
- `python -m aresforge inspect-milestone-dashboard --parent-issue 345`
- `python -m aresforge inspect-milestone-state --parent-issue 345`
- `python -m aresforge inspect-self-managed-milestone-execution-contract`
- `python -m aresforge simulate-self-managed-milestone-execution --parent-issue 345`

## Known Limitations

- Parent closeout remains intentionally manual and readiness-gated.
- Non-blocking governance milestone naming warning remains present.
- Milestone assignment warnings remain present for parent/child issues in current repo state.
