# AresForge Roadmap

## Current Milestones

### M0-M6

Status: Completed.

### M7 - Governance-Aware Intake And Closeout Planning

Status: Implemented in branch sequence, pending human merge/closeout.

Child issues:

- #173 governance-aware intake and queue planning contract
- #174 read-only GitHub issue intake adapter
- #175 hardened reference classification
- #178 persisted planning state design extension
- #176 read-only batch closeout planner
- #177 source-of-truth reconciliation

Outcomes delivered:

- Read-only issue intake normalization for planning fields and references.
- Protected historical issue handling that prevents Issue #39 implementation-link false positives.
- Queue planning outputs with persisted planning state and transition-history design metadata.
- Read-only parent/child closeout planning via `plan-batch-closeout`.
- Reconciled architecture/operator/context documentation for M7.

### M8+

Remain as previously planned: dashboard maturity, multi-project support, routing deepening, and controlled governance evolution.

## Standing Boundaries

- No autonomous setup/mutation behavior.
- No autonomous queue mutation.
- No autonomous merge/issue closure.
- Issue #39 remains retired historical validation evidence only.
- Issue #179 remains complete and unchanged.
