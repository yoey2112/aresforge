# Repository Governance Contract

## Purpose

This document defines the reusable label and milestone governance contract for AresForge-managed repositories.

The contract is platform-level and is not specific to one repository. The current default managed repository is `yoey2112/aresforge`, but future managed repositories must be able to adopt this contract without changing command semantics.

This document introduces read-only governance inspection behavior only. It does not authorize label creation, milestone creation, or any autonomous repository mutation.

The broader managed repository setup contract now lives in `docs/architecture/MANAGED_REPOSITORY_BOOTSTRAP_CONTRACT.md`.

## Command Surface

The contract is inspected through:

- `python -m aresforge inspect-repo-governance`
- `python -m aresforge inspect-repo-bootstrap-contract`

This command is human-triggered, read-only, and local-first. It uses GitHub CLI read calls where available and degrades gracefully with explicit warnings when GitHub CLI or network access is unavailable.

`inspect-repo-governance` is focused on reusable labels and milestones.

`inspect-repo-bootstrap-contract` is focused on broader repository bootstrap setup readiness across required, recommended, optional, and deferred setup areas.

## Reusable Label Contract

### Platform-Required Labels

Required minimum labels:

- `aresforge-ready`

`aresforge-ready` is the manual trigger label for ready issue intake.

### Platform-Optional Labels

Known optional platform labels:

- `aresforge-automerge`
- `aresforge-blocked`
- `aresforge-needs-evidence`
- `aresforge-needs-docs`
- `aresforge-closeout-ready`
- `aresforge-managed`
- `aresforge-generated`

Optional labels may be absent in newly managed repositories, but governance inspection should report visibility so operators can standardize posture over time.

### Automation Trigger Labels

Automation-trigger labels are:

- `aresforge-ready`
- `aresforge-automerge`

Interpretation rules:

- `aresforge-ready` is a manual intake trigger only.
- `aresforge-automerge` is a gated intent marker only.
- `aresforge-automerge` does not grant autonomous merge permission.
- Merge and issue closeout remain gated by existing QA checks and explicit human-triggered execute modes.

### Project-Specific Label Extensions

Managed repositories may add project-specific labels for local workflows.

Extension rule:

- Never remove or rename platform-required labels without updating platform governance.
- Keep automation-trigger labels intact so reusable automation contracts remain stable.
- Treat project-specific labels as additive metadata, not replacement governance.

## Milestone Governance Contract

### Canonical Platform Milestones

Platform milestone naming convention:

- `M0 - Foundation`
- `M1 - Validation`
- `M2 - Local Automation Foundation`
- `M3 - Registry And Routing Deepening`
- `M4 - Local Operator Expansion`

### Naming And Lifecycle Expectations

- Platform milestones should use exact canonical naming for deterministic inspection.
- Project-specific milestones are allowed and should map to one platform milestone phase for traceability.
- Milestone state (open or closed) is informational for inspection and does not authorize mutation.

## Managed Repository Bootstrap Expectations

Canonical bootstrap contract details are defined in `docs/architecture/MANAGED_REPOSITORY_BOOTSTRAP_CONTRACT.md`.

Before automation is considered safe, a newly managed repository should satisfy:

- Required labels are present.
- Optional labels are reviewed and adopted where useful.
- Platform milestone naming is present or intentionally mapped.
- A visible default branch exists.
- PRs and issues use explicit linking for QA and closeout checks.
- Source-of-truth documentation expectations are documented.
- Automation boundaries are explicit and human-gated.
- Evidence package expectations are documented and repeatable.
- Closeout expectations remain QA-gated and human-approved.

## Safety Boundaries

This governance layer is intentionally conservative:

- Local-first and human-triggered.
- Read-only inspection first.
- No autonomous mutation.
- No scheduler, daemon, or polling loop.
- No paid/API model usage by default behavior.
- Issue #39 remains retired historical validation evidence only.

## Extension Point For Multi-Repository Management

The current runtime inspects the repository configured by `ARESFORGE_GITHUB_OWNER` and `ARESFORGE_GITHUB_REPO`.

Future multi-repository expansion should keep the same contract shape and add project-scoped selection through registry-backed project identity (for example project ID to repository slug mapping) without changing safety boundaries or governance semantics.
