# Runnable Skeleton

## Purpose

Describe the implemented human-triggered operator surface through M21 self-managed milestone execution.

## Operator Shape

Command entrypoint:

- `python -m aresforge`

## Current Additions (M21 Included)

- `inspect-self-managed-milestone-execution-contract`
- `simulate-self-managed-milestone-execution`
- `run-sequential-child-closeout-flow`
- `generate-sequential-closeout-execution-package`
- `generate-self-managed-milestone-handoff`
- `inspect-milestone-state`
- `inspect-milestone-dashboard`
- `plan-milestone-execution-queue`
- `check-issue-evidence-readiness`
- `check-milestone-evidence-readiness`
- `inspect-parent-closeout-readiness`

## M21 Capability Contract Alignment

- Contract authority: `docs/architecture/M21_SELF_MANAGED_EXECUTION_CONTRACT.md`.
- Parent-driven sequential child execution with final reconciliation last.
- Read-only simulation available before mutation execution.
- Targeted closeout flow accepts a single child issue only.
- Parent closeout remains readiness-gated and separate from child closeout flow.

## Automation Boundary

- human-triggered only
- read-only-safe defaults
- explicit operator approval required for execute-mode mutation
- no bulk mutation path
- no automatic PR merge
- no background jobs, polling loops, or schedulers
- parent issue remains open until children are closed/accounted and parent readiness checks pass

## Current Validation Bundle (M21)

- `git diff --check`
- `python -m pytest`
- `python -m aresforge inspect-repo-governance`
- `python -m aresforge inspect-milestone-dashboard --parent-issue 345`
- `python -m aresforge inspect-milestone-state --parent-issue 345`
- `python -m aresforge inspect-self-managed-milestone-execution-contract`
- `python -m aresforge simulate-self-managed-milestone-execution --parent-issue 345`
- `python -m aresforge run-sequential-child-closeout-flow --parent-issue 345 --child-issue <child> --comment-body "M21 child evidence draft"`
- `python -m aresforge generate-sequential-closeout-execution-package --parent-issue 345 --child-issue <child>`

## Known Limitations

- Parent closeout execution remains manually triggered and intentionally conservative.
- Governance milestone naming warning remains non-blocking and unresolved.
- Issue milestone assignment gaps are surfaced as warnings but do not block M21 child execution.

## Follow-Up Candidates (M22)

1. Add read-only parent closeout evidence package generator.
2. Add stricter issue lineage diagnostics and remediation hints.
3. Add optional command scaffolds for evidence comments and parent closeout narratives.
