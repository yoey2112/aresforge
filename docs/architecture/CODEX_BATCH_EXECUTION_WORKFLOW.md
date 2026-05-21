# Codex CLI Sequential Batch Runner Workflow (M6)

## Purpose

Define a safe, human-supervised method for processing multiple child issues on one branch and one PR where practical.

## Workflow

1. Preparation
- Confirm clean baseline expectations.
- Update local `main`, create one implementation branch.
- Read source-of-truth and architecture contracts first.

2. Selection
- Use read-only intake/planning to select eligible child issues.
- Exclude protected historical issue #39.

3. Sequencing
- Execute ready items in deterministic order.
- Keep blocked/attention-needed items visible with explicit reasons.
- Stage documentation updates before final closeout readiness checks.

4. Validation Cadence
- Run tests and governance checks throughout the sequence.
- Re-run full validation before PR publication.

5. Readiness Reporting
- Use batch readiness reporting to summarize:
  - issue coverage
  - changed files
  - validation evidence
  - unresolved gates
  - closeout posture

6. Safe Stop Conditions
- Missing required validation evidence.
- Protected issue involvement.
- Missing source-of-truth reconciliation.
- Any boundary conflict requiring human escalation.

## Boundaries

- Read-only planning and reporting defaults.
- Human-triggered mutation only.
- No autonomous merge/closeout.
