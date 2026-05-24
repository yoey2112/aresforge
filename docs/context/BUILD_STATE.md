# AresForge Build State

## Current Phase

M30 self-managed local milestone lifecycle implementation and documentation.

## Current Goal

Connect local milestone definition, readiness checks, and closeout generation into a local-first lifecycle that links project state, documentation reconciliation planning, handoff generation, and optional future GitHub sync planning.

## M30 Self-Managed Milestone Lifecycle

- New local-only command surface:
  - `python -m aresforge generate-local-milestone-template --milestone-id <id> --output <path> [--title <title>] [--force]`
  - `python -m aresforge inspect-local-milestone --definition <path> [--format json|markdown]`
  - `python -m aresforge check-local-milestone-readiness --definition <path> [--project-state <path>] [--format json|markdown]`
  - `python -m aresforge generate-local-milestone-closeout --definition <path> --output <path> [--format json|markdown] [--force]`
- Definition files are local and operator-managed (suggested location: `.aresforge/milestones/`).
- Lifecycle is local-first and plan/check/generate only:
  - no `gh`
  - no GitHub API calls
  - no network access
  - no LLM calls
- Readiness checks validate required fields/docs/artifacts/commands/closeout requirements and optionally reconcile with local project state.
- Closeout generation includes milestone summary, readiness result, validation checklist, documentation reconciliation reminder (M28), handoff reminder (M26), and optional GitHub sync planning reminder (M29).
- M26 handoff package now surfaces `active_local_milestone` when inferable from M27 project state (`current_milestone`).

## M29 Offline-to-GitHub Sync Planner

- New local-only plan command:
  - `python -m aresforge plan-github-sync [--state-file <path>] [--project-state <path>] [--output <path>] [--format json|markdown] [--force]`
- Planner inspects only local sources:
  - optional offline closeout state file
  - optional/default project state ledger at `.aresforge/state/project_state.json`
  - optional source-of-truth docs context paths for plan traceability
- Planner output includes:
  - generated timestamp and input files used
  - parent/child sync candidates
  - evidence comment, closeout, label, milestone, PR evidence mapping, and validation candidates
  - rate-limit warnings, manual review checklist, and explicit no-GitHub-operations confirmation
- Strict M29 boundary:
  - plan-only
  - local-only
  - no `gh`
  - no GitHub API calls
  - no network access
  - no mutation
- M26 handoff package generation now includes latest local GitHub sync plan reference when detected under `artifacts/github-sync/`.
- M28 documentation reconciliation planning now recommends source-of-truth doc review when a local GitHub sync plan is present.

## M28 Documentation Agent Foundation

- New local-only plan command:
  - `python -m aresforge plan-doc-reconciliation [--output <path>] [--format json|markdown] [--include-git-state] [--force]`
- Planner inspects only local sources:
  - source-of-truth docs under `docs/context`, `docs/roadmap`, `docs/architecture`, `docs/operator`
  - local project state at `.aresforge/state/project_state.json` when present
  - local git state only when `--include-git-state` is supplied, using approved command subset
- Planner output fields include:
  - generated timestamp, docs inspected, missing docs, milestone and command references
  - stale/missing sections, recommended updates, alignment notes, risks, and next actions
- Strict M28 boundary:
  - plan-only (no doc edits)
  - local-only
  - no `gh`
  - no GitHub API calls
  - no LLM calls
  - no network dependency
- M26 handoff package generation now includes latest local doc reconciliation plan reference when detected under `artifacts/doc-reconciliation/`.
- M27 project-state documentation status can be used to track documentation reconciliation progress.

## M27 Local Project State Ledger

- New local-only ledger defaults:
  - `.aresforge/state/`
  - `.aresforge/state/project_state.json`
  - `.aresforge/state/operation_log.jsonl`
- New local-only command surface:
  - `python -m aresforge init-project-state [--path <path>] [--force]`
  - `python -m aresforge inspect-project-state [--path <path>]`
  - `python -m aresforge update-project-state [--path <path>] [--current-milestone <value>] [--current-phase <value>] [--current-mode <value>] [--validation-status <value>] [--documentation-status <value>] [--warning <text>]...`
  - `python -m aresforge append-operation-log [--state-path <path>] --event-type <type> --summary <summary> [--details <json>]`
  - `python -m aresforge inspect-operation-log [--state-path <path>] [--limit <n>]`
- M26 handoff package generation now includes local project-state summary when present.
- If project state is missing, handoff generation adds a warning and still succeeds.

## M26 Local Handoff Package Generator

- New local-only command: `python -m aresforge generate-handoff-package --output <path> [--format markdown|json] [--include-doc-excerpts] [--force]`.
- Reads only local repo + source-of-truth docs and does not call GitHub APIs or `gh`.
- Uses only safe local git commands for state capture:
  - `git branch --show-current`
  - `git rev-parse HEAD`
  - `git status --short`
  - `git log -n 10 --oneline`
- Supports stdout rendering when `--output` is omitted:
  - Markdown by default.
  - Stable JSON when `--format json`.
- Supports continuity sections for future sessions:
  - project status summary
  - completed recent capabilities
  - known blockers/warnings
  - working preferences
  - recommended next options
  - Codex continuation prompt

## Continuity Value

- Reduces manual handoff writing for human and agent transitions.
- Establishes a local-first continuity baseline required before future multi-project queue/orchestration/dashboard/cloud escalation milestones.

## Current Repository State

- M25 parent issue: `#421` (OPEN; pending final closeout).
- M25 child issue status:
  - `#422` CLOSED via PR `#431`
  - `#423` CLOSED via PR `#432`
  - `#424` CLOSED via PR `#433`
  - `#425` CLOSED via PR `#434`
  - `#426` CLOSED via PR `#435`
  - `#427` CLOSED via PR `#436`
  - `#428` CLOSED via PR `#437`
  - `#429` CLOSED via PR `#438`
  - `#430` OPEN (final source-of-truth reconciliation; sequenced last)
- Offline state-file parent closeout readiness workflow is implemented and pushed on `main` through commit `40de9fe`.

## Offline State-File Closeout Readiness (Local-Only)

- Preferred path during GitHub GraphQL/API rate-limit windows.
- When `--state-file <path>` is provided, these commands run local/offline and avoid `gh` and GitHub API calls.
- Supported commands:
  - `python -m aresforge inspect-milestone-state --parent-issue <n> --state-file <path>`
  - `python -m aresforge check-milestone-evidence-readiness --parent-issue <n> --state-file <path>`
  - `python -m aresforge inspect-parent-closeout-readiness --parent-issue <n> --state-file <path>`
  - `python -m aresforge generate-parent-closeout-evidence-bundle --parent-issue <n> --state-file <path>`
  - `python -m aresforge check-closeout-readiness-by-construction --parent-issue <n> --state-file <path>`
- Example fixture: `tests/fixtures/offline_state/parent_closeout_ready.json`.
- Validation checkpoint for docs/sample addition passed: `python -m pytest` (`502` tests).

## M25 Command Surface

- `python -m aresforge inspect-automatic-canonical-evidence-emission-contract`
- `python -m aresforge inspect-child-evidence-marker-preflight --parent-issue <parent>`
- `python -m aresforge inspect-pr-mapping-preflight --parent-issue <parent>`
- `python -m aresforge generate-closeout-preflight-repair-guidance --parent-issue <parent>`
- `python -m aresforge generate-child-closeout-evidence-bundle --parent-issue <parent> --child-issue <child>`
- `python -m aresforge generate-pr-evidence-bundle --issue <child> --pr <pr>`
- `python -m aresforge generate-parent-closeout-evidence-bundle --parent-issue <parent>`
- `python -m aresforge generate-evidence-comment-template --issue <issue>`
- `python -m aresforge check-closeout-readiness-by-construction --parent-issue <parent>`

## M25 Safety Posture

- no autonomous broad mutation
- no bulk closeout
- no parent closeout before children are closed/accounted for and readiness passes
- dry-run/read-only defaults preserved
- execute-mode mutation requires explicit operator approval markers
- mutation scope remains single-target and auditable
- canonical marker generation and snapshot/diff inspection remain read-only by default
- final reconciliation issue remains sequenced last (`#430`)
- no post-hoc marker repair should be needed when generated evidence artifacts are complete

## Known Limitations

- Project-specific milestone naming mapping warning remains non-blocking (`milestone_naming_status.naming_ok: false`).
- Parent and some child issues currently have no GitHub milestone assignment (warning only, non-blocking for M25 closeout).

## Validation Baseline For M25

- `git diff --check`
- `python -m pytest`
- `python -m aresforge inspect-repo-governance`
- `python -m aresforge inspect-milestone-state --parent-issue 421`
- `python -m aresforge check-milestone-evidence-readiness --parent-issue 421`
- `python -m aresforge inspect-parent-closeout-readiness --parent-issue 421`
- `python -m aresforge inspect-milestone-closeout-preflight --parent-issue 421`
- `python -m aresforge inspect-automatic-canonical-evidence-emission-contract`
- `python -m aresforge check-closeout-readiness-by-construction --parent-issue 421`
- `python -m aresforge generate-parent-closeout-evidence-bundle --parent-issue 421`

## M25 Child/PR Mapping

- `#422` -> `#431`
- `#423` -> `#432`
- `#424` -> `#433`
- `#425` -> `#434`
- `#426` -> `#435`
- `#427` -> `#436`
- `#428` -> `#437`
- `#429` -> `#438`
- `#430` -> pending (this reconciliation PR)

## Main HEAD Tracking (M25 Remaining Sequence)

- Before #428/#429/#430 sequence: `dd856632e2f1831b20b73613f29e9e953771180f`
- After #428 and #429 merges: `cafda2ceda0a329de7d06a42c0edc6725ece3b10`
- Final main HEAD after #430 merge: pending (set after merge)
