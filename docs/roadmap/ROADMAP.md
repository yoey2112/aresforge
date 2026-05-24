# AresForge Roadmap

## Current Milestones

### M0-M20

Status: Completed.

### M21 - Self-Managed Milestone Execution Loop

Status: Completed.

Parent issue:

- `#345` M21 self-managed milestone execution loop (OPEN)

Child issues:

- `#346` CLOSED via PR `#354`
- `#347` CLOSED via PR `#355`
- `#348` CLOSED via PR `#356`
- `#349` CLOSED via PR `#357`
- `#350` CLOSED via PR `#358`
- `#351` CLOSED via PR `#359`
- `#352` CLOSED via PR `#360`
- `#353` OPEN (final source-of-truth reconciliation; must be processed last)

Delivered M21 outcomes:

- `inspect-self-managed-milestone-execution-contract`
- `run-sequential-child-closeout-flow`
- `generate-sequential-closeout-execution-package`
- `generate-self-managed-milestone-handoff`
- `simulate-self-managed-milestone-execution`
- M21 operator workflow and architecture documentation updates

M21 safety posture:

- no autonomous broad mutation
- no bulk closure
- no parent closeout before all children are closed/accounted for
- mutation execution defaults to dry-run/planning unless explicitly approved
- every child is executed with dedicated branch, PR, validation, evidence comment, and targeted closeout
- final reconciliation kept last and docs-focused
- prior milestones are not mutated

M21 standard validation bundle:

- `git diff --check`
- `python -m pytest`
- `python -m aresforge inspect-repo-governance`
- `python -m aresforge inspect-milestone-dashboard --parent-issue 345`
- `python -m aresforge inspect-milestone-state --parent-issue 345`
- `python -m aresforge inspect-self-managed-milestone-execution-contract`
- `python -m aresforge simulate-self-managed-milestone-execution --parent-issue 345`

### M22 - Evidence Bundle And Documentation Automation

Status: Completed.

Parent issue:

- `#362` CLOSED

Child issues:

- `#363` CLOSED via PR `#372`
- `#364` CLOSED via PR `#373`
- `#365` CLOSED via PR `#374`
- `#366` CLOSED via PR `#375`
- `#367` CLOSED via PR `#376`
- `#368` CLOSED via PR `#377`
- `#369` CLOSED via PR `#378`
- `#370` CLOSED via PR `#379`
- `#371` CLOSED via PR `#380`

Delivered M22 outcomes:

- `inspect-evidence-bundle-automation-contract`
- `generate-child-closeout-evidence-bundle`
- `generate-parent-closeout-evidence-bundle`
- `generate-pr-evidence-bundle`
- validation summary normalization (`pass`/`fail`/`warning`/`unknown`)
- `simulate-evidence-bundle-generation`
- operator and architecture documentation updates for evidence bundle workflows

M22 safety posture:

- no autonomous broad mutation
- no bulk closure
- no parent closeout before all children are closed/accounted for
- mutation execution defaults to dry-run/planning unless explicitly approved
- every child is executed with dedicated branch, PR, validation, evidence comment, and targeted closeout
- final reconciliation kept last and docs-focused
- prior milestones are not mutated

M22 standard validation bundle:

- `git diff --check`
- `python -m pytest`
- `python -m aresforge inspect-repo-governance`
- `python -m aresforge inspect-milestone-dashboard --parent-issue 362`
- `python -m aresforge inspect-milestone-state --parent-issue 362`
- `python -m aresforge check-milestone-evidence-readiness --parent-issue 362`
- `python -m aresforge inspect-parent-closeout-readiness --parent-issue 362`
- `python -m aresforge generate-parent-closeout-evidence-bundle --parent-issue 362`

### M23 - Milestone Lineage And Evidence Mapping Preflight

Status: Completed.

Parent issue:

- `#381` CLOSED

Child issues:

- `#382` CLOSED via PR `#391`
- `#383` CLOSED via PR `#392`
- `#384` CLOSED via PR `#393`
- `#385` CLOSED via PR `#394`
- `#386` CLOSED via PR `#395`
- `#387` CLOSED via PR `#396`
- `#388` CLOSED via PR `#397`
- `#389` CLOSED via PR `#398`
- `#390` CLOSED (final source-of-truth reconciliation child)

Delivered M23 outcomes:

- `inspect-milestone-closeout-preflight-contract`
- `inspect-parent-child-linkage-preflight`
- `inspect-child-evidence-marker-preflight`
- `inspect-pr-mapping-preflight`
- `generate-closeout-preflight-repair-guidance`
- `inspect-milestone-closeout-preflight`
- operator documentation updates for preflight sequencing and state interpretation

M23 safety posture:

- no autonomous broad mutation
- no bulk closure
- no parent closeout before all children are closed/accounted for
- mutation execution defaults to dry-run/planning unless explicitly approved
- repair guidance remains copy/paste text only and does not execute mutation
- final reconciliation kept last and docs-focused
- prior milestones are not mutated

M23 standard validation bundle:

- `git diff --check`
- `python -m pytest`
- `python -m aresforge inspect-repo-governance`
- `python -m aresforge inspect-milestone-dashboard --parent-issue 381`
- `python -m aresforge inspect-milestone-state --parent-issue 381`
- `python -m aresforge check-milestone-evidence-readiness --parent-issue 381`
- `python -m aresforge inspect-parent-closeout-readiness --parent-issue 381`
- `python -m aresforge inspect-milestone-closeout-preflight --parent-issue 381`

### M24 - Canonical Evidence Marker Workflow

Status: Final reconciliation in progress (`#410` only).

Parent issue:

- `#400` M24 canonical evidence marker workflow (OPEN)

Child issues:

- `#401` CLOSED via PR `#411`
- `#402` CLOSED via PR `#412`
- `#403` CLOSED via PR `#413`
- `#404` CLOSED via PR `#414`
- `#405` CLOSED via PR `#415`
- `#406` CLOSED via PR `#416`
- `#407` CLOSED via PR `#417`
- `#408` CLOSED via PR `#418`
- `#409` CLOSED via PR `#419`
- `#410` OPEN (final source-of-truth reconciliation; must be processed last)

Delivered M24 outcomes:

- `inspect-canonical-evidence-marker-contract`
- `generate-child-evidence-marker-template`
- `generate-pr-evidence-marker-template`
- `generate-parent-closeout-marker-template`
- `generate-preflight-baseline-snapshot`
- `diff-preflight-snapshots`
- canonical-marker integration in evidence bundles and preflight guidance
- canonical-first preflight parsing with backward-compatible fallback
- operator and architecture documentation updates for canonical marker workflow

M24 safety posture:

- no autonomous broad mutation
- no bulk closure
- no parent closeout before all children are closed/accounted for
- mutation execution defaults to dry-run/planning unless explicitly approved
- canonical marker and snapshot/diff commands are read-only by default
- final reconciliation kept last and docs-focused
- prior milestones are not mutated

M24 standard validation bundle:

- `git diff --check`
- `python -m pytest`
- `python -m aresforge inspect-repo-governance`
- `python -m aresforge inspect-milestone-dashboard --parent-issue 400`
- `python -m aresforge inspect-milestone-state --parent-issue 400`
- `python -m aresforge check-milestone-evidence-readiness --parent-issue 400`
- `python -m aresforge inspect-parent-closeout-readiness --parent-issue 400`
- `python -m aresforge inspect-milestone-closeout-preflight --parent-issue 400`
- `python -m aresforge inspect-canonical-evidence-marker-contract`

### M25 Candidate Themes

1. Close out parent #400 with final reconciliation evidence package automation checks.
2. Tighten milestone assignment governance warnings with explicit remediation playbooks.
3. Expand deterministic evidence extraction for historical closeout comments.

## Standing Boundaries

- No autonomous mutation without explicit mode selection.
- No autonomous queue workers.
- No automatic PR merge.
- No unattended background execution.
