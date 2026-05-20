# Managed Repository Bootstrap Contract

## Purpose

This document defines bootstrap and onboarding readiness expectations for managed repositories.

It provides a reusable, read-only contract so operators can decide whether setup work is safe before any mutation is attempted.

## Contract Surface

- `python -m aresforge inspect-repo-bootstrap-contract`
- `python -m aresforge inspect-managed-repos`
- `python -m aresforge managed-repo-readiness-report`
- `python -m aresforge plan-repo-bootstrap`
- `python -m aresforge demo-managed-repo-governance`

All current surfaces are read-only.

## Contract Buckets

### Required

- default branch posture
- required and trigger labels
- canonical milestone posture
- validation evidence expectations
- closeout expectations
- source-of-truth documentation expectations
- artifact convention expectations
- automation boundary confirmations
- protected historical evidence handling
- local path and repository slug posture
- governance profile posture

### Recommended

- optional platform labels
- project-specific milestone mapping notes
- issue and PR convention clarity
- registry metadata completeness

### Optional

No standalone optional setup bucket is currently defined.

### Deferred

- future multi-repository setup profile automation

## Setup Trigger Policy

Setup or setup correction is human-triggered only.

This contract does not implement setup mutation behavior.

## Gated Setup Command Contract (Design-Only, M5)

M5 defines the future setup-command contract requirements without implementing a new mutation command.

Required future behavior:

- dry-run-first execution path
- explicit confirmation requirement before mutation
- audit evidence showing target, scope, and gate outcomes
- strict mutation scope boundaries
- explicit rollback or recovery notes
- human-triggered execution model only
- no autonomous mutation execution
- output proving exactly what was inspected, planned, and changed
- validation gates that detect unsafe or undeclared mutation behavior

Current state: design-only. Setup mutation continues to require manual human-reviewed commands.

## Automation Boundary Confirmations

Managed repositories must preserve:

- read-only-first inspection defaults
- explicit, visible, human-triggered mutation steps
- no hidden schedulers/daemons/polling loops for mutation
- no autonomous closeout, merge, or setup execution
