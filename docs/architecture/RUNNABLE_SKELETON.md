# Runnable Skeleton

## Purpose

Describe the implemented human-triggered operator surface through M25 automatic canonical marker emission workflow orchestration.

## Operator Shape

Command entrypoint:

- `python -m aresforge`

## Current Additions (M25 Included)

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

- `inspect-canonical-evidence-marker-contract`
- `generate-child-evidence-marker-template`
- `generate-pr-evidence-marker-template`
- `generate-parent-closeout-marker-template`
- `generate-preflight-baseline-snapshot`
- `diff-preflight-snapshots`

- `inspect-automatic-canonical-evidence-emission-contract`
- `check-closeout-readiness-by-construction`
- canonical marker completeness payloads in:
  - child closeout evidence bundle generation
  - PR evidence bundle generation
  - parent closeout evidence bundle generation
  - closeout comment template generation

## M25 Capability Contract Alignment

- Contract authority: `docs/architecture/AUTOMATIC_CANONICAL_EVIDENCE_EMISSION_CONTRACT.md`.
- Canonical marker emission now occurs by default across child, PR, parent, and closeout-comment evidence domains.
- Readiness-by-construction inspects emitted marker completeness plus milestone execution readiness in a read-only command path.
- Missing marker completeness or post-hoc-repair-required signals block readiness-by-construction deterministically.
- Parent closeout remains human-gated and separate from marker/readiness command execution.

## M24 Capability Contract Alignment

- Contract authority: `docs/architecture/CANONICAL_EVIDENCE_MARKER_CONTRACT.md`.
- Canonical marker templates are deterministic and read-only by default.
- Snapshot generation and diff classification are read-only and audit-focused.
- Canonical markers are integrated into child/PR/parent evidence bundle outputs.
- Preflight parsing prefers canonical markers and preserves backward-compatible fallback parsing.
- Parent closeout remains readiness-gated and separate from marker/snapshot command execution.

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

## Current Validation Bundle (M25)

- `git diff --check`
- `python -m pytest`
- `python -m aresforge inspect-repo-governance`
- `python -m aresforge inspect-milestone-state --parent-issue 421`
- `python -m aresforge check-milestone-evidence-readiness --parent-issue 421`
- `python -m aresforge inspect-parent-closeout-readiness --parent-issue 421`
- `python -m aresforge inspect-milestone-closeout-preflight --parent-issue 421`
- `python -m aresforge inspect-automatic-canonical-evidence-emission-contract`
- `python -m aresforge check-closeout-readiness-by-construction --parent-issue 421`
- `python -m aresforge generate-parent-closeout-evidence-bundle --parent-issue 421`

## Known Limitations

- Parent closeout execution remains manually triggered and intentionally conservative.
- Governance milestone naming warning remains non-blocking and unresolved.
- Issue milestone assignment gaps are surfaced as warnings but do not block M25 child execution.

## Follow-Up Candidates (Post-M25)

1. Improve parent/child milestone assignment governance diagnostics and remediation playbooks.
2. Add higher-fidelity closeout lineage discoverability reporting to reduce `no_child_issue_targets_detected` ambiguity.
3. Expand deterministic historical evidence extraction for previously closed milestones.
