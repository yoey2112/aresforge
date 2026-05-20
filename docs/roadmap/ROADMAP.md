# AresForge Roadmap

## Purpose

This roadmap is the compact source-of-truth sequencing document for AresForge.

## Roadmap Operating Rules

- Documentation-before-closeout applies to roadmap-changing and project-state-changing work.
- Source-of-truth docs (`BUILD_STATE`, `AGENT_CONTEXT`, `ROADMAP`) must be reconciled before closeout.
- Human-reviewed controls remain mandatory.
- Issue #75 remains the last routine reconciliation issue.
- Issue #39 is retired historical validation evidence only.

## Current Milestone Summary

### M0 - Self-Bootstrap Foundation

Status: Completed.

### M1 - GitHub Operations Validation

Status: Completed.

### M2 - Documentation And Runnable Local Foundation

Status: Completed.

### M3 - Registry And Routing Deepening

Status: Completed.

### M4 - Local Operator Expansion

Status: Completed and closed out through parent Issue #145.

### M5 - Local Operator Quality And Safe Onboarding Contracts

Status: Completed by consolidated closeout PR.

M5 child workstreams:

- #158 / PR #161 completed.
- #156 / PR #162 completed.
- #157 completed in consolidated M5 closeout PR: managed repository onboarding contract.
- #159 completed in consolidated M5 closeout PR: gated setup command contract design-only.
- #160 completed in consolidated M5 closeout PR: source-of-truth reconciliation.
- #155 completed in consolidated M5 closeout PR: parent closeout.

M5 outcomes:

- Managed repository onboarding contract now clearly distinguishes platform self-managed, fixture/demo, and real managed repositories.
- Onboarding metadata, readiness checks, trust boundaries, and human-triggered setup expectations are explicit.
- Future gated setup command contract is defined as design-only with dry-run, confirmation, audit, scope, and recovery requirements.
- No autonomous setup/mutation command was introduced.
- GitHub mutation posture remains human-triggered and gated.

## Planned Milestone Sequence

### M6 - Agent Queue And Orchestration MVP

Design visible queue and handoff structures that remain human-supervised and reversible.

### M7 - Dashboard MVP

Add local visibility for project state, queue state, documentation freshness, and manual action prompts.

### M8 - Multi-Project Support

Extend AresForge beyond self-management with per-project context and bounded autonomy levels.

### M9 - Model Routing And Local LLM Integration

Deepen bounded local model routing and evaluation with governance controls.

### M10 - Controlled Automation Layer

Consider carefully bounded automation only after queue, evidence, and approval systems are mature.

### M11 - Release And Governance System

Define release planning, versioning, governance review, and production-readiness controls.

### M12 - Self-Managed Delivery Loop

Long-term target: configurable autonomy with preserved human authority and reversibility.

## Explicit Non-Goals For The Current Phase

The post-M5 posture does not authorize:

- autonomous setup/mutation behavior
- autonomous queue/routing mutation
- autonomous approval, merge, or issue closure
- hidden background mutation agents
- repository settings, ruleset, branch protection, release/tag, secret, workflow, or GitHub Project mutation without explicit human action

## Next Recommended Direction

- Start M6 with a design-first, human-supervised queue/orchestration contract.
- Preserve read-only-first defaults and explicit mutation gates.
- Keep onboarding and setup evidence outputs deterministic and reviewable.
