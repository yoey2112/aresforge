# AresForge Roadmap

## Current Milestones

### M0-M6

Status: Completed.

### M7 - Governance-Aware Intake And Closeout Planning

Status: Completed.

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

### M8 - Hardened Sprint Planning And Closeout Evidence Workflows

Status: Implementation complete (#183-#188 via merged PR #190); source-of-truth reconciliation in progress (#189).

Child issues:

- #183 improve closeout planner merged PR evidence handling
- #184 harden readiness classification
- #185 structured `evidence_report` output for `plan-batch-closeout`
- #186 structured sprint issue definition contract documentation
- #187 read-only/output-only sprint issue generation command
- #188 generated issue body safety validation
- #189 source-of-truth reconciliation

Outcomes delivered:

- Improved closeout planner merged PR evidence handling.
- Hardened readiness classification.
- Structured `evidence_report` output for `plan-batch-closeout`.
- Structured sprint issue definition contract documentation.
- New read-only/output-only command: `python -m aresforge generate-sprint-issue-script --definition <file>`.
- Generated issue body safety validation for safety posture, linkage clarity, and mutation-boundary language.

### M9+

Remain as previously planned: dashboard maturity, multi-project support, routing deepening, and controlled governance evolution.

## Standing Boundaries

- No autonomous setup/mutation behavior.
- No autonomous queue mutation.
- No autonomous merge/issue closure.
- No autonomous labels, milestones, comments, releases, or tags.
- Issue #39 remains retired historical validation evidence only.
- Issue #179 remains complete and unchanged.
