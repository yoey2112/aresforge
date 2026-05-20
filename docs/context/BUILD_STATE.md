# AresForge Build State

## Current Phase

M5 - Local Operator Quality And Safe Onboarding Contracts

## Current Goal

Complete consolidated M5 closeout in one PR by finishing managed repository onboarding contract definition, gated setup command contract design, and source-of-truth reconciliation.

## Current Repository State

- Current branch: `m5/remaining-managed-onboarding-and-closeout`
- Baseline `main` / `origin/main` commit before this branch: `b5a0196` (`Issue #156: improve PR closeout label-target guidance (#162)`)
- M5 completed child workstreams before this branch:
  - Issue #158 / PR #161
  - Issue #156 / PR #162
- Remaining M5 issues targeted by this branch:
  - Issue #157: managed repository onboarding contract
  - Issue #159: gated repository setup command contract (design-only)
  - Issue #160: source-of-truth reconciliation
  - Issue #155: M5 parent closeout
- GitHub mutation remains human-triggered and gated.
- No autonomous setup or mutation command surface is implemented.
- Issue #39 remains retired historical validation evidence and is out of routine automation scope.

## Current Source Of Truth

Repository documentation remains the source of truth for roadmap state, governance meaning, architecture meaning, lifecycle gates, and autonomy boundaries.

Primary source-of-truth entry points:

- `docs/context/BUILD_STATE.md`
- `docs/context/AGENT_CONTEXT.md`
- `docs/roadmap/ROADMAP.md`

For project-state-changing work, these documents must be reviewed and updated before PR merge and issue closeout, or explicitly justified when unchanged.

## Current Implemented Local Operator Capabilities

The current human-triggered local operator foundation includes:

- local config and registry validation
- local migration planning and execution
- read-only registry and lifecycle inspection
- read-only artifact, review package, and evidence package inspection
- deterministic human-triggered review orchestration
- deterministic QA PR review and closeout gating with dry-run default
- deterministic read-only project-state, governance, bootstrap contract, managed-repo registry, readiness, bootstrap-plan, and governance-demo reporting
- deterministic read-only end-to-end PR validation orchestration

These capabilities are local-first helper surfaces and do not replace human governance decisions.

## Managed Repository Onboarding Posture (M5)

A managed repository is a repository explicitly registered for AresForge governance inspection and readiness planning under documented boundaries.

Repository classes:

- Platform self-managed repository: the AresForge repository itself (`yoey2112/aresforge`), always first/default in managed registry views.
- Fixture/demo repository: an inspection-only demo record used to validate multi-repository contract behavior safely; never treated as production mutation scope.
- Real managed repository: an intentionally onboarded repository with documented ownership, governance profile, local-path posture, readiness evidence, and explicit human setup expectations.

Required onboarding metadata for real managed repositories:

- `repository_slug`
- `project_key`
- `repo_role`
- `governance_profile`
- `default_branch`
- `local_path` posture
- `documentation_roots`
- `artifact_roots`
- `allowed_automation_capabilities`

Required readiness checks before setup mutation is considered:

- `python -m aresforge inspect-repo-governance`
- `python -m aresforge inspect-repo-bootstrap-contract`
- `python -m aresforge inspect-managed-repos`
- `python -m aresforge managed-repo-readiness-report`
- `python -m aresforge plan-repo-bootstrap`

Trust and mutation boundaries:

- onboarding is documentation-first and read-only-first
- setup/mutation remains human-triggered and explicit
- no autonomous label/milestone/template/settings mutation
- fixture/demo repositories are never used to justify production mutation

## Setup Command Contract Posture (M5 Design-Only)

M5 defines a future gated setup command contract and intentionally does not implement a new mutation command.

Contract expectations:

- dry-run-first behavior with explicit mutation intent previews
- explicit operator confirmation for each target repository
- audit evidence output that proves command path, target, and gates
- strict mutation scope boundaries (only declared setup surfaces)
- rollback and recovery notes for partial failures
- no autonomous execution, polling, or background mutation
- validation checks that fail when unsafe behavior or undeclared mutation appears

Current implementation status remains design-only; setup/mutation execution stays manual via human-reviewed commands.

## Current Boundaries

Allowed:

- human-triggered local commands
- read-only governance and bootstrap planning surfaces
- deterministic planning output and operator guidance

Not authorized:

- autonomous queue or routing mutation
- autonomous approval, merge, or issue closure
- autonomous GitHub setup/mutation behavior
- hidden background lifecycle or setup mutation behavior

## Next Recommended Direction

- Merge this consolidated M5 closeout PR to close Issues #157, #159, #160, and #155.
- Keep setup and mutation human-triggered and gated while maturing evidence-rich operator workflows.
- Use M6 to design visible queue-orchestration primitives that remain human-supervised and reversible.
