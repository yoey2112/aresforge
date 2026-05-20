# Runnable Skeleton

## Purpose

Issue #81 established the runnable local skeleton. Subsequent milestones expanded it with read-only governance and closeout tooling.

## Operator Shape

The local operator is exposed as `python -m aresforge`.

Supported command groups:

- local validation and inspection
- ready-issue intake planning
- PR QA review and gated closeout
- project-state and governance reporting
- managed-repo registry, readiness, and bootstrap planning
- local artifact/evidence/handoff generation

## Managed Repository Contract Integration

The runnable stack includes a read-only managed-repository governance suite:

- `inspect-repo-governance`
- `inspect-repo-bootstrap-contract`
- `inspect-managed-repos`
- `managed-repo-readiness-report`
- `plan-repo-bootstrap`
- `demo-managed-repo-governance`

These commands provide deterministic inspection and planning outputs and do not perform setup mutation.

## M5 Onboarding And Setup Design Posture

M5 adds explicit documentation contracts for:

- managed repository onboarding classification and metadata
- readiness checks prior to setup consideration
- trust and mutation boundaries
- future gated setup command behavior requirements

M5 does not implement a new setup/mutation command.

## Automation Boundary

The current runnable layer remains:

- human-triggered
- read-only-first
- explicit-gate for existing execute-mode closeout behavior
- non-autonomous for setup/mutation behavior

No autonomous setup/mutation path is introduced.
