# Runnable Skeleton

## Purpose

Describe the implemented human-triggered operator surface through M23 milestone lineage/evidence mapping preflight orchestration.

## Operator Shape

Command entrypoint:

- `python -m aresforge`

## Current Additions (M23 Included)

- `inspect-evidence-bundle-automation-contract`
- `generate-child-closeout-evidence-bundle`
- `generate-parent-closeout-evidence-bundle`
- `generate-pr-evidence-bundle`
- `simulate-evidence-bundle-generation`

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

- `inspect-milestone-closeout-preflight-contract`
- `inspect-parent-child-linkage-preflight`
- `inspect-child-evidence-marker-preflight`
- `inspect-pr-mapping-preflight`
- `generate-closeout-preflight-repair-guidance`
- `inspect-milestone-closeout-preflight`

## M23 Capability Contract Alignment

- Contract authority: `docs/architecture/MILESTONE_CLOSEOUT_PREFLIGHT_CONTRACT.md`.
- Parent-child lineage detection, child evidence markers, and PR mapping checks are read-only by default.
- Repair guidance output is copy/paste-safe text only and does not execute mutation.
- Orchestration command (`inspect-milestone-closeout-preflight`) provides one deterministic readiness report.
- Parent closeout remains readiness-gated and separate from preflight command execution.

## M22 Capability Contract Alignment

- Contract authority: `docs/architecture/EVIDENCE_BUNDLE_AUTOMATION_CONTRACT.md`.
- Evidence bundle generation paths are read-only by default.
- Validation summaries are normalized for deterministic evidence rendering.
- Simulation path provides fixture-friendly blocked/ready planning outputs with no mutation.
- Parent closeout remains readiness-gated and separate from generation commands.

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

## Current Validation Bundle (M23)

- `git diff --check`
- `python -m pytest`
- `python -m aresforge inspect-repo-governance`
- `python -m aresforge inspect-milestone-dashboard --parent-issue 381`
- `python -m aresforge inspect-milestone-state --parent-issue 381`
- `python -m aresforge check-milestone-evidence-readiness --parent-issue 381`
- `python -m aresforge inspect-parent-closeout-readiness --parent-issue 381`
- `python -m aresforge inspect-milestone-closeout-preflight --parent-issue 381`
- `python -m aresforge generate-parent-closeout-evidence-bundle --parent-issue 381`

## Known Limitations

- Parent closeout execution remains manually triggered and intentionally conservative.
- Governance milestone naming warning remains non-blocking and unresolved.
- Issue milestone assignment gaps are surfaced as warnings but do not block M23 child execution.

## Follow-Up Candidates (M24)

1. Add canonical child evidence marker templates to reduce parsing ambiguity.
2. Add stronger linked/merged PR extraction to reduce mapping ambiguity warnings.
3. Add baseline snapshot comparison for closeout preflight drift.
