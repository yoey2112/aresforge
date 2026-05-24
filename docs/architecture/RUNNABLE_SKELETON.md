# Runnable Skeleton

## Purpose

Describe the implemented human-triggered operator surface through M31 foundation reconciliation and next-phase planning.

## Operator Shape

Command entrypoint:

- `python -m aresforge`

## M31 Foundation Reconciliation

- AresForge now has a local-first foundation for self-managed operation.
- GitHub is optional/syncable and not mandatory for local planning.
- M26-M30 capabilities are established and reconciled as the baseline foundation:
  - M26 handoff package generation
  - M27 local project state ledger
  - M28 plan-only documentation reconciliation
  - M29 plan-only offline-to-GitHub sync planning
  - M30 local self-managed milestone lifecycle
- Foundation batch boundary confirmations:
  - no new GitHub API calls
  - no new LLM API calls
  - no mandatory network dependency for local planning

## M32 Managed Project Registry

- Added local managed-project registry under `.aresforge/projects/projects.json`.
- Supports multiple projects and repos with local metadata and deterministic inspect output.
- Local-only boundary:
  - no `gh`
  - no GitHub API calls
  - no network access

## Current Additions (M25 Included)

- `inspect-evidence-bundle-automation-contract`
- `generate-child-closeout-evidence-bundle`
- `generate-parent-closeout-evidence-bundle`
- `generate-pr-evidence-bundle`
- `simulate-evidence-bundle-generation`

- `inspect-self-managed-milestone-execution-contract`
- `simulate-self-managed-milestone-execution`
- `run-sequential-child-closeout-flow`
- `generate-sequential-closeout-execution-package`
- `generate-self-managed-milestone-handoff`
- `inspect-milestone-state`
- `inspect-milestone-dashboard`
- `plan-milestone-execution-queue`
- `check-issue-evidence-readiness`
- `check-milestone-evidence-readiness`
- `inspect-parent-closeout-readiness`

- `inspect-milestone-closeout-preflight-contract`
- `inspect-parent-child-linkage-preflight`
- `inspect-child-evidence-marker-preflight`
- `inspect-pr-mapping-preflight`
- `generate-closeout-preflight-repair-guidance`
- `inspect-milestone-closeout-preflight`

- `inspect-canonical-evidence-marker-contract`
- `generate-child-evidence-marker-template`
- `generate-pr-evidence-marker-template`
- `generate-parent-closeout-marker-template`
- `generate-preflight-baseline-snapshot`
- `diff-preflight-snapshots`

- `inspect-automatic-canonical-evidence-emission-contract`
- `check-closeout-readiness-by-construction`
- `generate-handoff-package`
- `init-project-state`
- `inspect-project-state`
- `update-project-state`
- `append-operation-log`
- `inspect-operation-log`
- `plan-doc-reconciliation`
- `plan-github-sync`
- `generate-local-milestone-template`
- `inspect-local-milestone`
- `check-local-milestone-readiness`
- `generate-local-milestone-closeout`
- `init-managed-project-registry`
- `register-managed-project`
- `register-managed-repo`
- `inspect-managed-project-registry`
- `inspect-managed-project`
- `inspect-managed-repo`
- offline/local state-file mode supported for milestone/parent readiness and parent evidence generation commands via `--state-file <path>`
- canonical marker completeness payloads in:
  - child closeout evidence bundle generation
  - PR evidence bundle generation
  - parent closeout evidence bundle generation
  - closeout comment template generation

Offline state-file command surface:

- `python -m aresforge inspect-milestone-state --parent-issue <n> --state-file <path>`
- `python -m aresforge check-milestone-evidence-readiness --parent-issue <n> --state-file <path>`
- `python -m aresforge inspect-parent-closeout-readiness --parent-issue <n> --state-file <path>`
- `python -m aresforge generate-parent-closeout-evidence-bundle --parent-issue <n> --state-file <path>`
- `python -m aresforge check-closeout-readiness-by-construction --parent-issue <n> --state-file <path>`
- This local/offline path avoids `gh` and GitHub API calls when `--state-file` is provided.
- Reference fixture: `tests/fixtures/offline_state/parent_closeout_ready.json`.
- Implemented/pushed through commit `40de9fe`; preferred during GitHub GraphQL/API rate-limit windows.

## M26 Local Handoff Package Surface

- Command: `python -m aresforge generate-handoff-package --output <path> [--format markdown|json] [--include-doc-excerpts] [--force]`
- Local-only continuity artifact for:
  - human session handoff
  - Codex session continuation
  - local LLM agent continuation
  - future project agent continuation
- Reads local source-of-truth docs and local git state only.
- Approved local git command set:
  - `git branch --show-current`
  - `git rev-parse HEAD`
  - `git status --short`
  - `git log -n 10 --oneline`
- No `gh`, no GitHub API calls, no network dependency.
- Includes local project-state summary from `.aresforge/state/project_state.json` when available.
- Emits a warning and still succeeds when local project-state file is missing.
- Includes managed-project registry summary from `.aresforge/projects/projects.json` when available.

## M27 Local Project State Ledger Surface

- Ledger defaults:
  - `.aresforge/state/project_state.json`
  - `.aresforge/state/operation_log.jsonl`
- Commands:
  - `python -m aresforge init-project-state [--path <path>] [--force]`
  - `python -m aresforge inspect-project-state [--path <path>]`
  - `python -m aresforge update-project-state [--path <path>] [--current-milestone <value>] [--current-phase <value>] [--current-mode <value>] [--validation-status <value>] [--documentation-status <value>] [--warning <text>]...`
  - `python -m aresforge append-operation-log [--state-path <path>] --event-type <type> --summary <summary> [--details <json>]`
  - `python -m aresforge inspect-operation-log [--state-path <path>] [--limit <n>]`
- Local-only boundary: no `gh`, no GitHub API calls, no network dependency.
- Scope boundary: M27 project state is per current repo/session context; M32 registry tracks many projects/repos.

## M28 Documentation Reconciliation Surface

- Command: `python -m aresforge plan-doc-reconciliation [--output <path>] [--format json|markdown] [--include-git-state] [--force]`
- Planner scope:
  - source-of-truth docs in `docs/context`, `docs/roadmap`, `docs/architecture`, and `docs/operator`
  - local project state at `.aresforge/state/project_state.json` when present
  - optional local git state via approved command set only
- Output:
  - stable JSON for tests/automation
  - human-readable markdown for operator review
- Boundary:
  - plan-only (no automatic doc editing)
  - local-only
  - no `gh`, no GitHub APIs, no LLM calls, no external network use

## M29 Offline-to-GitHub Sync Planning Surface

- Command: `python -m aresforge plan-github-sync [--state-file <path>] [--project-state <path>] [--output <path>] [--format json|markdown] [--force]`
- Planner scope:
  - optional offline closeout state file
  - optional/default local project state file at `.aresforge/state/project_state.json`
  - local source-of-truth docs for context traceability
- Output:
  - stable JSON for automation/tests
  - human-readable markdown for operator review
- Boundary:
  - plan-only (no posting comments, no closing issues, no PR creation)
  - local-only
  - no `gh`, no GitHub APIs, no network access
- no mutation

## M30 Local Milestone Lifecycle Surface

- Commands:
  - `python -m aresforge generate-local-milestone-template --milestone-id <id> --output <path> [--title <title>] [--force]`
  - `python -m aresforge inspect-local-milestone --definition <path> [--format json|markdown]`
  - `python -m aresforge check-local-milestone-readiness --definition <path> [--project-state <path>] [--format json|markdown]`
  - `python -m aresforge generate-local-milestone-closeout --definition <path> --output <path> [--format json|markdown] [--force]`
- Suggested local definition path: `.aresforge/milestones/`.
- Lifecycle links:
  - M27 project-state ledger for active milestone/phase and documentation status checks.
  - M28 `plan-doc-reconciliation` as a required lifecycle closeout follow-up.
  - M26 `generate-handoff-package` reminder as a closeout continuity step.
  - M29 `plan-github-sync` as an optional future sync planning step.
  - Later milestones can be associated with M32 managed `project_id` / `repo_id`.
- Boundary:
  - local-only
  - plan/check/generate only
  - no `gh`, no GitHub APIs, no network, no LLM calls

## M25 Capability Contract Alignment

- Contract authority: `docs/architecture/AUTOMATIC_CANONICAL_EVIDENCE_EMISSION_CONTRACT.md`.
- Canonical marker emission now occurs by default across child, PR, parent, and closeout-comment evidence domains.
- Readiness-by-construction inspects emitted marker completeness plus milestone execution readiness in a read-only command path.
- Missing marker completeness or post-hoc-repair-required signals block readiness-by-construction deterministically.
- Parent closeout remains human-gated and separate from marker/readiness command execution.

## M24 Capability Contract Alignment

- Contract authority: `docs/architecture/CANONICAL_EVIDENCE_MARKER_CONTRACT.md`.
- Canonical marker templates are deterministic and read-only by default.
- Snapshot generation and diff classification are read-only and audit-focused.
- Canonical markers are integrated into child/PR/parent evidence bundle outputs.
- Preflight parsing prefers canonical markers and preserves backward-compatible fallback parsing.
- Parent closeout remains readiness-gated and separate from marker/snapshot command execution.

## M23 Capability Contract Alignment

- Contract authority: `docs/architecture/MILESTONE_CLOSEOUT_PREFLIGHT_CONTRACT.md`.
- Parent-child lineage detection, child evidence markers, and PR mapping checks are read-only by default.
- Repair guidance output is copy/paste-safe text only and does not execute mutation.
- Orchestration command (`inspect-milestone-closeout-preflight`) provides one deterministic readiness report.
- Parent closeout remains readiness-gated and separate from preflight command execution.

## M22 Capability Contract Alignment

- Contract authority: `docs/architecture/EVIDENCE_BUNDLE_AUTOMATION_CONTRACT.md`.
- Evidence bundle generation paths are read-only by default.
- Validation summaries are normalized for deterministic evidence rendering.
- Simulation path provides fixture-friendly blocked/ready planning outputs with no mutation.
- Parent closeout remains readiness-gated and separate from generation commands.

## M21 Capability Contract Alignment

- Contract authority: `docs/architecture/M21_SELF_MANAGED_EXECUTION_CONTRACT.md`.
- Parent-driven sequential child execution with final reconciliation last.
- Read-only simulation available before mutation execution.
- Targeted closeout flow accepts a single child issue only.
- Parent closeout remains readiness-gated and separate from child closeout flow.

## Automation Boundary

- human-triggered only
- read-only-safe defaults
- explicit operator approval required for execute-mode mutation
- no bulk mutation path
- no automatic PR merge
- no background jobs, polling loops, or schedulers
- parent issue remains open until children are closed/accounted and parent readiness checks pass

## Current Foundation Validation Bundle (Local-Only)

- `git diff --check`
- `python -m pytest`
- `python -m aresforge init-project-state --force`
- `python -m aresforge inspect-project-state`
- `python -m aresforge generate-handoff-package --output artifacts/handoff/final-handoff.md --force`
- `python -m aresforge plan-doc-reconciliation --output artifacts/doc-reconciliation/final-plan.json --force`
- `python -m aresforge plan-github-sync --output artifacts/github-sync/final-sync-plan.json --force`
- `python -m aresforge generate-local-milestone-template --milestone-id m31-final-validation --title "M31 Final Validation" --output artifacts/milestones/m31-final-validation.json --force`
- `python -m aresforge inspect-local-milestone --definition artifacts/milestones/m31-final-validation.json --format markdown`
- `python -m aresforge check-local-milestone-readiness --definition artifacts/milestones/m31-final-validation.json --format markdown`
- `python -m aresforge generate-local-milestone-closeout --definition artifacts/milestones/m31-final-validation.json --output artifacts/milestones/m31-closeout.md --format markdown --force`

## Known Limitations

- No local queue/tracking yet unless implemented later.
- No actual LLM invocation yet.
- No cloud LLM API integration yet.
- No GitHub sync execution yet.
- No web dashboard UI yet.
- No cross-machine coordination yet.
- No background daemon/scheduler yet.

## Next-Phase Roadmap (Planned)

1. Local project queue and tracking.
2. Local LLM agent handoff profiles.
3. Multi-agent orchestration planning.
4. Escalation to cloud LLMs.
5. Project dashboard and local project management reporting.
6. Optional later GitHub sync execution.
7. Optional later web dashboard UI.
8. Optional later background daemon or scheduler.
