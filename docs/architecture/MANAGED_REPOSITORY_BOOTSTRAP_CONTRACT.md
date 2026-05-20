# Managed Repository Bootstrap Contract

## Purpose

This document defines the reusable managed repository bootstrap contract for AresForge.

The contract answers one question before any broader automation is considered: what must be confirmed for a repository to be safely managed under the existing local-first, human-triggered, read-only-first governance posture.

This contract supports:

- repositories created by AresForge in the future
- existing repositories newly registered into AresForge
- the AresForge repository itself as the first managed repository
- read-only evaluation before any mutation decision
- explicit human-triggered setup and setup changes only
- future multi-repository governance extension without changing core safety boundaries

## Contract Surface

The bootstrap contract can be inspected through:

- `python -m aresforge inspect-repo-bootstrap-contract`
- `python -m aresforge inspect-managed-repos`

This command is read-only and deterministic JSON output by design. It reuses existing repository governance inspection where practical and degrades gracefully when GitHub CLI or network access is unavailable.

`inspect-managed-repos` reuses this bootstrap contract evaluation per managed repository entry and surfaces summarized per-repository bootstrap status while keeping read-only boundaries intact.

The command does not mutate files, labels, milestones, issues, pull requests, branches, workflows, settings, artifacts, or git state.

## Contract Buckets

### Required

A repository must satisfy or explicitly acknowledge these areas before broader automation use:

- default branch expectations
- required labels
- automation trigger labels
- platform milestone naming
- validation evidence expectations
- closeout expectations
- documentation expectations
- generated artifact conventions
- automation boundary confirmations
- protected historical evidence handling
- local path and repository slug expectations
- governance profile expectations

### Recommended

Recommended areas improve consistency and reduce operator ambiguity:

- optional platform-known labels
- project-specific milestone mapping
- issue templates or issue conventions
- pull request linking conventions

### Optional

No optional bootstrap-only areas are currently defined for M3.

Future optional areas may be added if they are truly non-gating and do not weaken required governance controls.

### Deferred

Deferred areas are intentionally postponed and should be handled by dedicated future issues:

- future multi-repository governance alignment and per-project bootstrap profile selection

## Contract Areas

### Default Branch Expectations

A visible repository default branch must exist for read-only inspection. Current platform expectation is `main` unless a managed-project policy explicitly defines a different default branch and documents why.

### Required Labels

Platform-required labels must be present:

- `aresforge-ready`

### Optional Platform-Known Labels

Known optional labels should be reviewed and adopted where useful:

- `aresforge-automerge`
- `aresforge-blocked`
- `aresforge-needs-evidence`
- `aresforge-needs-docs`
- `aresforge-closeout-ready`
- `aresforge-managed`
- `aresforge-generated`

### Automation Trigger Labels

Automation-trigger labels are required for stable reusable routing semantics:

- `aresforge-ready`
- `aresforge-automerge`

`aresforge-automerge` remains an intent marker only. It does not authorize autonomous merge.

### Platform Milestone Naming

Canonical platform milestone naming should be present and unambiguous:

- `M0 - Foundation`
- `M1 - Validation`
- `M2 - Local Automation Foundation`
- `M3 - Registry And Routing Deepening`
- `M4 - Local Operator Expansion`

### Project-Specific Milestone Mapping

Project-specific milestones are allowed, but they should map to one canonical platform milestone phase for traceability.

### Issue Templates Or Issue Conventions

Managed repositories should provide either issue templates or explicit issue conventions that preserve clear problem framing, trigger labeling posture, and evidence expectations.

### Pull Request Linking Conventions

Pull requests should explicitly link target issues for QA and closeout checks (for example `Closes #<issue-number>` for normal closeout cases).

### Validation Evidence Expectations

Validation evidence remains required for project-state-changing work and should follow the documented evidence package templates.

### Closeout Expectations

Closeout remains QA-gated and human-approved. Passing QA posture is required before merge and linked issue closeout actions.

### Documentation Expectations

Source-of-truth entry points must remain present and current:

- `docs/context/BUILD_STATE.md`
- `docs/context/AGENT_CONTEXT.md`
- `docs/roadmap/ROADMAP.md`

### Generated Artifact Conventions

Managed repositories should preserve deterministic generated artifact roots used by local review and evidence workflows:

- `artifacts/prompts/generated/`
- `artifacts/evidence/generated/`
- `artifacts/codex_handoffs/generated/`

### Automation Boundary Confirmations

Managed repositories must preserve these boundaries:

- human-triggered behavior only
- read-only inspection defaults
- explicit mutation gates for any state-changing behavior
- no hidden scheduler, daemon, polling, or background mutation behavior

### Protected Historical Evidence Handling

Historical protected evidence handling must remain explicit. Issue 39 is retired historical validation evidence only and must not be treated as routine automation scope.

### Local Path And Repository Slug Expectations

A managed project should have a clear repository slug and expected local path posture for deterministic local operator behavior.

### Governance Profile Expectations

Managed repositories should include and follow the repository governance profile contract in:

- `docs/architecture/REPOSITORY_GOVERNANCE_CONTRACT.md`

## Read-Only Evaluation Model

Bootstrap evaluation is read-only and deterministic. The evaluation should classify areas into consistent statuses such as:

- satisfied
- attention_needed
- advisory
- unavailable
- deferred

Unavailable status should not trigger mutation. It should produce warnings and a manual next-step recommendation.

## Setup Trigger Policy

Bootstrap setup or setup correction is human-triggered only.

This contract does not authorize autonomous setup mutation (for example creating labels, milestones, templates, branch rules, workflows, or documentation updates without explicit human invocation).

## Multi-Repository Extension Point

Future multi-repository support should reuse this contract shape and add project-scoped profile selection through registry-backed project identity.

The extension must preserve current boundaries:

- read-only inspection defaults
- explicit human-triggered mutation only
- deterministic output for review and evidence
- no autonomous GitHub-state-changing behavior
