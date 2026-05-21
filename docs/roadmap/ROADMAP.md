# AresForge Roadmap

## Current Milestones

### M0-M5

Status: Completed.

### M6 - Agent Queue And Orchestration MVP

Status: In implementation closeout for consolidated branch/PR.

Child issues:

- #165 queue/orchestration contract
- #166 Codex batch workflow contract
- #169 queue-driven intake/planning command
- #170 batch readiness reporting command
- #167 closeout reliability hardening
- #168 source-of-truth reconciliation

Outcomes targeted:

- Read-only queue planning with readiness classification and batch grouping.
- Read-only batch readiness report for multi-issue PR closeout posture.
- Stronger closeout diagnostics for close issue edge cases.
- Updated architecture/operator/source-of-truth docs.

### M7 - Dashboard MVP

Next after M6 closeout.

### M8+

Remain as previously planned: multi-project support, routing deepening, controlled automation, and governance maturity.

## Standing Boundaries

- No autonomous setup/mutation behavior.
- No autonomous queue mutation.
- No autonomous merge/issue closure.
- Issue #39 remains retired historical validation evidence only.
