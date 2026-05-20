# Local Operator Usage

## Purpose

This guide explains how to use current local AresForge operator surfaces, including M5 managed-repository onboarding and gated setup-contract planning posture.

## Core Validation Bundle

Run this bundle for branch validation and PR evidence:

- `python -m pytest`
- `python -m aresforge project-state-summary`
- `python -m aresforge inspect-repo-governance`
- `python -m aresforge inspect-repo-bootstrap-contract`
- `python -m aresforge inspect-managed-repos`
- `python -m aresforge managed-repo-readiness-report`
- `python -m aresforge plan-repo-bootstrap`
- `python -m aresforge validate-pr-end-to-end --help`
- `python -m aresforge qa-review-pr --help`
- `python -m aresforge qa-closeout-pr --help`
- `git diff --check`

## Managed Repository Onboarding Workflow (M5)

1. Confirm repository class: platform self-managed, fixture/demo, or real managed.
2. Confirm required metadata in managed repo registry posture.
3. Run read-only readiness checks:
   - `python -m aresforge inspect-repo-governance`
   - `python -m aresforge inspect-repo-bootstrap-contract`
   - `python -m aresforge inspect-managed-repos`
   - `python -m aresforge managed-repo-readiness-report`
   - `python -m aresforge plan-repo-bootstrap`
4. Review planning output and warnings.
5. If mutation is needed, run human-reviewed manual commands outside autonomous automation.

## Gated Setup Command Contract Posture (M5 Design-Only)

AresForge currently does not implement a setup/mutation command.

The future command contract is documented only and must support:

- dry-run-first previews
- explicit operator confirmations
- deterministic audit evidence
- strict mutation scope boundaries
- rollback/recovery guidance
- human-triggered execution only
- no autonomous mutation behavior

## PR QA And Closeout Guidance

`qa-review-pr` is read-only QA validation.

`validate-pr-end-to-end` is read-only orchestration that includes `qa-closeout-pr --dry-run` posture guidance.

`qa-closeout-pr` defaults to `--dry-run` and only mutates in explicit `--execute` mode after all gates pass.

## Boundaries

Allowed:

- human-triggered local command execution
- read-only inspection and planning
- explicit dry-run and gated execute for existing closeout workflow

Not allowed:

- autonomous setup/mutation command execution
- hidden background mutation behavior
- autonomous merge/closeout
- mutation of Issue #39
