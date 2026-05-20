# AresForge Build State

## Current Phase

M2 - Runnable Local Foundation

## Current Goal

Continue the M2 runtime foundation by extending human-triggered local operator support, read-only registry inspection, and safer helper flows without introducing autonomous repository or queue control.

## Current Repository State

- Current branch: `m2/sprint-120-ready-issue-pipeline`
- Latest `main` commit: `874b500` (`M2 sprint: QA-gated automatic PR merge and issue closeout (#125)`)
- Latest runtime-affecting merged foundation commit: `874b500` (`M2 sprint: QA-gated automatic PR merge and issue closeout (#125)`)
- Issue #105 was completed through PR #106 and is merged `main` behavior
- Issue #107 was completed through PR #108 and is merged `main` behavior
- Issue #109 was completed through PR #111 and is merged `main` behavior
- Issue #103 was completed through PR #104 and is merged `main` behavior
- Issue #101 was completed through PR #102 and is merged `main` behavior
- Issue #99 was completed through PR #100 and is merged `main` behavior
- Issue #92 and Issue #93 were completed through PR #94 and are merged `main` behavior
- `validate-registries`, `inspect-queue --write-artifact`, `inspect-work-item --write-artifact`, and `list-models` are available on `main`
- `inspect-model` is available on `main`
- `inspect-registries` is available on `main`
- `list-artifacts` is available on `main`
- `inspect-artifact` is available on `main`
- `run-local-review` with opt-in local review package generation is available on `main`
- `list-evidence-packages` and `inspect-evidence-package` are available on `main`
- opt-in artifact discovery capture for `record-evidence-package` is available on `main`
- `list-review-packages` and `inspect-review-package` are available on `main`
- opt-in latest local review package capture for `record-evidence-package` and `prepare-codex-handoff` is available on `main`
- Issue #112 was completed through PR #115 and is merged `main` behavior
- Issue #114 was completed through PR pending merge and added the canonical model-routing and LLM escalation strategy documentation
- Issue #118 was completed through PR #124 and is merged `main` behavior
- Issue #119 was completed through PR #125 and is merged `main` behavior
- Issue #120 is in progress on the current branch and adds `run-ready-issue-pipeline` orchestration with explicit mode gating
- Issue #127 is in progress on the current branch and adds read-only `run-ready-issue-batch --plan-only` plus `automation-readiness-report`, deterministic batch artifact generation, and optional local-only selected issue handoff package generation
- Issue #95 was completed through PR #96 and is merged `main` behavior
- Issue #97 was completed through PR #98 and is merged `main` behavior
- Issue #75 remains the last routine reconciliation issue
- Issue #39, `validation: issue-38-state-lifecycle`, remains intentionally open protected audit evidence and must not be modified or closed except through a future human-directed issue

## Current Source Of Truth

Repository documentation remains the authoritative source for roadmap state, governance meaning, architecture meaning, lifecycle gates, and autonomy boundaries.

GitHub issue and PR state plus the local PostgreSQL-backed runtime provide operational context, but they do not replace the source-of-truth role of the docs.

The active source-of-truth entry points are:

- `docs/context/BUILD_STATE.md`
- `docs/context/AGENT_CONTEXT.md`
- `docs/roadmap/ROADMAP.md`

Future project-state-changing work must review and update those documents when needed before PR merge and issue closeout. If one does not require changes, PR evidence or closeout evidence must explain why.

## Latest Completed Work

- PR #94 completed Issue #92 and Issue #93 and added merged `main` support for read-only registry validation plus inspection report artifact generation
- Commit `42b02dd` corrected stale source-of-truth wording after PR #94 closeout directly on `main` without creating a new routine reconciliation issue
- The canonical runnable M2 implementation foundation now consists of:
  - `docs/architecture/LOCAL_STATE_STORE.md`
  - `docs/architecture/RUNNABLE_SKELETON.md`
  - `docs/operator/LOCAL_OPERATOR_USAGE.md`
  - `docs/architecture/AGENT_REGISTRY_SCHEMA.md`
  - `docs/architecture/MODEL_REGISTRY_SCHEMA.md`
  - `docs/architecture/QUEUE_REGISTRY_SCHEMA.md`
  - `docs/architecture/MODEL_ROUTING_STRATEGY.md`

Older completed M0-M2 issue history now lives in `docs/history/M0_M2_COMPLETED_WORK_SUMMARY.md`.

## Current Implemented Local Operator Capabilities

The current human-triggered local operator foundation supports:

- local config and registry validation
- database migration execution for the repo-stored local state layer
- deterministic read-only local model listing through `list-models`
- deterministic read-only local model inspection through `inspect-model`
- deterministic read-only local project inspection through `inspect-project`
- deterministic read-only local registry and lifecycle source inspection through `inspect-registries`
- read-only queue and work-item inspection
- read-only inspection report artifact generation through `inspect-queue --write-artifact` and `inspect-work-item --write-artifact`
- deterministic read-only generated artifact discovery through `list-artifacts`
- deterministic read-only single-artifact inspection through `inspect-artifact`
- deterministic read-only local review package discovery through `list-review-packages`
- deterministic read-only single local review package inspection through `inspect-review-package`
- deterministic read-only evidence package discovery through `list-evidence-packages`
- deterministic read-only single evidence package inspection through `inspect-evidence-package`
- deterministic human-triggered local review orchestration through `run-local-review`
- deterministic decision-only ready issue routing through `plan-ready-issue`
- deterministic QA PR validation-only inspection through `qa-review-pr`
- deterministic QA-gated PR closeout through `qa-closeout-pr` with default dry-run/no-mutation and explicit execute mode
- deterministic reusable ready issue orchestration through `run-ready-issue-pipeline` with explicit plan-only, review-pr, and closeout-when-eligible modes
- deterministic reusable read-only ready issue batch planning through `run-ready-issue-batch --plan-only` with deterministic JSON and Markdown artifact generation
- deterministic read-only automation readiness dashboard reporting through `automation-readiness-report`
- a human-triggered phase-based PR lifecycle helper for explicit validation, staging, commit and push, PR creation, PR verification, merge verification, post-merge verification, and source-of-truth scanning
- prompt package, evidence package, and Codex handoff artifact preparation, including opt-in local artifact discovery capture in evidence packages plus opt-in latest local review package capture in evidence and handoff outputs
- opt-in local review package generation under `artifacts/local_reviews/generated/`
- bounded local Ollama connectivity and dry-run support

These capabilities are local-only helper surfaces. They are reviewable, non-authoritative, and intended to support implementation and closeout work rather than replace human decision-making.

## Current Boundaries

The current M2 implementation does allow:

- human-triggered local commands
- read-only registry-aware validation and inspection
- read-only inspection of repo-owned registry and lifecycle source documents
- read-only project inspection from local seeded project rows
- visible human-triggered PR lifecycle helper phases selected one at a time
- local artifact generation for review
- local artifact discovery for review
- local single-artifact inspection for review
- local review package discovery for review
- local single review package inspection for review
- local evidence package discovery for review
- local single evidence package inspection for review
- deterministic local review orchestration across existing local operator checks
- local review package generation only when explicitly requested
- opt-in latest local review package capture in handoff and evidence outputs
- bounded local model inspection, listing, and Ollama dry-run checks
- bounded local model inspection, listing, and Ollama dry-run checks without autonomous selection or routing

The current M2 implementation does not authorize:

- queue transitions performed autonomously
- routing mutation or autonomous routing
- autonomous approval, merge, or issue closure
- GitHub-state-changing behavior except when a human explicitly runs a matching visible PR lifecycle helper phase such as `CreatePr` or `MergePr`
- repo setting, branch protection, ruleset, secret, release, tag, workflow, or GitHub Project changes
- hosted external model use as part of the default runtime foundation
- any modification to protected Issue #39
- any hidden background PR lifecycle behavior

## Next Recommended Direction

- Use the merged human-triggered PR lifecycle helper to reduce repetitive PR validation, merge verification, and source-of-truth scanning work
- Continue the M2 runtime foundation with richer read-only registry inspection views and safer human-triggered helper flows where useful
- Continue the M2 runtime foundation with deterministic local review orchestration, review package inspection, and auditable handoff or evidence capture that remain human-triggered and local-only
- Prioritize broader read-only registry inspection summaries and safer helper flows while keeping them local-only and non-authoritative
- Extend local operator visibility while keeping queue transitions and GitHub-state-changing behavior tightly human-triggered and reviewable
- Optionally perform local historical branch cleanup as separate human-directed repository hygiene work
- Keep documentation freshness, documentation-before-closeout, and source-of-truth updates mandatory for future project-state-changing work

## History Reference

For compact historical context about completed M0, M1, and M2 work, use `docs/history/M0_M2_COMPLETED_WORK_SUMMARY.md`. That history file preserves why major patterns, documents, and constraints exist, but it does not replace the active source-of-truth documents above.
