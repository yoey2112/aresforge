# Repository Governance Contract

## Purpose

This document defines reusable label and milestone governance expectations for AresForge-managed repositories.

The contract is inspection-first and does not itself authorize setup mutation.

## Command Surface

- `python -m aresforge inspect-repo-governance`
- `python -m aresforge inspect-repo-bootstrap-contract`
- `python -m aresforge inspect-managed-repos`
- `python -m aresforge managed-repo-readiness-report`
- `python -m aresforge plan-repo-bootstrap`
- `python -m aresforge demo-managed-repo-governance`

All are human-triggered and read-only with graceful degradation.

## Reusable Label Contract

### Platform-Required Labels

- `aresforge-ready`

### Platform-Optional Labels

- `aresforge-automerge`
- `aresforge-blocked`
- `aresforge-needs-evidence`
- `aresforge-needs-docs`
- `aresforge-closeout-ready`
- `aresforge-managed`
- `aresforge-generated`

### Automation Trigger Labels

- `aresforge-ready`
- `aresforge-automerge`

`aresforge-automerge` is an intent marker only and does not grant autonomous merge permission.

## Milestone Governance Contract

Canonical milestone names:

- `M0 - Foundation`
- `M1 - Validation`
- `M2 - Local Automation Foundation`
- `M3 - Registry And Routing Deepening`
- `M4 - Local Operator Expansion`
- `M5 - Local Operator Quality And Safe Onboarding Contracts`

Project-specific milestones are allowed but should map to canonical phases for traceability.

## Setup And Mutation Boundary Posture

- Governance inspection is read-only.
- Managed-repository setup/mutation commands are not implemented here.
- Any setup mutation remains human-triggered and explicitly gated.
- No autonomous setup/mutation behavior is introduced by this contract.

## Safety Boundaries

This governance layer does not authorize:

- autonomous label or milestone mutation
- autonomous merge/closeout
- hidden background mutation workers
- Issue #39 mutation

Human-triggered command recommendations emitted by planning surfaces are guidance only and are never auto-executed by AresForge.
