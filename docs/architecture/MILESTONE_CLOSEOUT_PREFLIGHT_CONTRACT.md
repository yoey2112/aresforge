# Milestone Closeout Preflight Contract

This contract defines strict, deterministic, read-only milestone lineage and evidence mapping preflight requirements before parent closeout.

## Purpose

- Detect parent-child lineage, evidence mapping, and PR mapping problems before closeout.
- Remove manual detective work from closeout readiness checks.
- Keep mutation execution outside this preflight surface.

## Read-Only Boundary

- Read-only by default.
- Preflight commands do not close issues, merge PRs, update issue bodies, or post comments.
- Repair output is copy/paste-safe operator guidance only.

## Required Parent-Child Lineage Signals

- parent references all intended children
- child references parent
- missing lineage
- ambiguous lineage
- conflicting lineage

## Required Child Evidence Mapping Signals

- evidence comment marker
- branch
- commit
- pr
- validation
- safety notes

## Required PR Mapping Signals

- child to pr mapping
- pr merge status
- missing pr mapping
- ambiguous pr mapping
- unmerged pr

## Required Preflight States

- ready
- blocked
- warning
- unknown

## Actionable Repair Guidance Requirements

- Actionable repair guidance must be explicit and issue-specific.
- Guidance must include copy/paste-safe repair guidance with plain text command examples.
- Guidance must separate parent repair, child evidence marker repair, and PR mapping repair.
- Guidance does not execute mutation.

## Relationship to Existing Commands

- inspect-milestone-dashboard
- inspect-milestone-state
- check-milestone-evidence-readiness
- inspect-parent-closeout-readiness
- generate-parent-closeout-evidence-bundle

Preflight augments the commands above by validating lineage and mapping detectability before parent closeout.

## Contract Inspection Surface

Use this read-only inspection command:

python -m aresforge inspect-milestone-closeout-preflight-contract

Expected command guarantees:

- Confirms contract document presence.
- Confirms required lineage, evidence mapping, PR mapping, and state definitions are present.
- Confirms actionable repair guidance requirements are present.
- Confirms read-only boundary is preserved.
