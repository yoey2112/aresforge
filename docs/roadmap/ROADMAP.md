# AresForge Roadmap

## M17 Local Queue Execution-Prep Lifecycle

Status: Completed locally on `main` (no push performed).

Delivered M17 scope:

- local queue item creation with active-project/default repo binding
- local readiness inspection before mutation
- gated local queue item start
- local-only Codex prompt generation for copy/paste manual implementation sessions
- local queue completion with validation evidence and commit metadata

Implemented local workflow:

- `add-local-queue-item`
- `inspect-local-queue-item-readiness`
- `start-local-queue-item`
- `generate-local-queue-item-codex-prompt`
- manual human-run Codex session
- `complete-local-queue-item`

M17 safety posture:

- local-only and file-backed
- no GitHub mutation/sync execution
- no GitHub API calls
- no `gh` calls
- no automatic Codex execution
- no agent execution
- no model routing/invocation

### M21 - Active Project Workspace (Polish & Tests)

Status: Completed locally on `main`.

Highlights:

- UI polish for the Active Project Workspace with operator-first guidance and clear empty states.
- Quick-action labels explicitly marked "(local-only)" and workspace actions wired in the frontend (`app.js`).
- Regression tests added (`tests/test_active_project_workspace.py`) covering empty and seeded active-workspace payloads.

Safety posture:

- local-only report and planning surfaces
- no GitHub API calls, no `gh` calls
- no agent or model execution

### M23 - Hub Frontend Modularization Foundation

Status: Completed locally on `main`.

Highlights:

- converted Hub static loading to use browser-native ES modules
- extracted shared frontend primitives into `js/core/dom.js`, `js/core/http.js`, and `js/core/state.js`
- kept `app.js` as the frontend entrypoint/orchestrator
- removed the unused placeholder helper and consolidated duplicated workspace button binding
- updated frontend foundation tests to validate the modularized static surface safely

Safety posture:

- local-only refactor
- no GitHub API calls, no `gh` calls
- no new network behavior
- no agent or model execution
- no DOM id or endpoint path contract changes


M17 completion evidence is stored locally with status transition metadata plus commit hash, validation summary, and optional evidence fields.

## M16 Hub Read-Only Foundations

Status: Completed locally on `main` (no push performed).

Delivered M16 scope:

- Home dashboard API wiring for local report/readiness data
- Home dashboard read-only UI foundation
- Projects page read-only UI foundation
- Queue page read-only UI foundation
- Reports page read-only UI foundation

M16 safety posture:

- local-only/report-oriented surfaces
- no GitHub mutation/sync execution
- no agent execution
- no model routing/invocation

## M14 Local Foundation Reconciliation

Status: Completed locally on `main` in this chat (read-only/report-summary scope).

Recorded completion context:

- M9-M13 were already completed, validated, committed, and pushed before this chat.
- M14 added local-only read model/report foundation surfaces without introducing execution/mutation behavior.

Delivered M14 local command additions:

- `inspect-local-project-dashboard`
- `list-local-projects`
- `inspect-local-project-readiness`
- `inspect-local-queue-agent-summary`
- `inspect-local-project-report`

M14 boundaries:

- local-first and local-only for new inspection/report commands
- no GitHub API calls
- no `gh` calls
- no GitHub issue/PR mutation
- no agent execution
- no LLM routing/invocation

## Project Factory Realignment Track

The primary near-term roadmap priority is completing the end-to-end project-factory loop. UI polish is secondary to finishing the workflow contract from intake through validated closeout.

### M46 - Project Factory Source-of-Truth Realignment

Status: Completed in documentation/contracts.

- aligns build state, agent context, roadmap, runnable skeleton, and operator usage with current `main` through M45
- introduces canonical workflow contract: `docs/architecture/PROJECT_FACTORY_WORKFLOW.md`

### M47 - New Project Wizard

Status: Planned.

### M48 - Repo Create/Link Planner And Approval Gate

Status: Planned.

### M49 - Project Scope And Architecture Contract

Status: Planned.

### M50 - Milestone And Issue Plan Generator

Status: Planned.

### M51 - Explicit GitHub Milestone/Issue Apply Boundary

Status: Planned.

### M52 - Agent Queue Dispatcher

Status: Planned.

### M53 - Agent Run Lifecycle, Evidence, And Validation Gates

Status: Planned.

### M54 - Documentation And Closeout Automation

Status: Planned.

### M55 - Active-Project Feature Loop

Status: Planned.

## Current Milestones

### M42 - First-Run Bootstrap And Seed Wizard For Hub

Status: Completed (local-only first-run setup experience and bootstrap API/CLI/operator support).

Delivered M42 outcomes:

- new local bootstrap operator module:
  - `src/aresforge/operator/local_bootstrap_wizard.py`
- new local bootstrap CLI commands:
  - `inspect-bootstrap-status`
  - `plan-bootstrap`
  - `apply-bootstrap`
- new local Hub bootstrap endpoints:
  - `GET /api/bootstrap/status`
  - `GET /api/bootstrap/plan`
  - `POST /api/bootstrap/apply`
- new Hub Bootstrap setup section with:
  - first-run setup status signals
  - plan preview before apply
  - force and sample-work toggles
  - apply action and changed/already-existing feedback
- bootstrap initialization/seed coverage:
  - initializes local state files under `.aresforge/`
  - registers `aresforge` managed project/repo with local GitHub metadata
  - seeds default M34 agent profiles and handoff targets idempotently
  - optionally seeds sample next-phase queue milestones (`m43`-`m46`)

M42 safety posture:

- local-only and file-backed
- no GitHub API calls
- no `gh` calls
- no GraphQL or REST calls
- no network service calls
- no live GitHub validation/discovery
- no local/cloud/Codex/ChatGPT/Ollama model invocation

### M41 - GitHub-Linked Project/Repo Model In Hub

Status: Completed (local-only GitHub identity model and local git-link inspection support).

Delivered M41 outcomes:

- extended managed project/repo registry schema with local GitHub identity fields and local git inspection fields
- project-level primary repo linkage (`primary_repo_id`) and identity derivation from primary repo when project link fields are omitted
- GitHub URL parsing/generation rules for:
  - `https://github.com/owner/repo`
  - `https://github.com/owner/repo.git`
  - `git@github.com:owner/repo.git`
- local-only git inspection support using safe local commands:
  - `git -C <path> remote get-url origin`
  - `git -C <path> branch --show-current`
  - `git -C <path> rev-parse HEAD`
  - `git -C <path> status --short`
- CLI updates:
  - new GitHub-link flags on `register-managed-project`
  - new GitHub-link flags and `--inspect-local-git` on `register-managed-repo`
  - new `inspect-managed-repo-github-link` command
- Hub API updates:
  - project/repo create endpoints accept GitHub-link fields
  - new endpoint: `GET /api/projects/{project_id}/repos/{repo_id}/github-link`
- Hub UI updates:
  - Projects and Repos forms include GitHub-link fields
  - Repos supports local git-link inspection action
  - Home/Reports/Settings include GitHub linkage readiness/reporting and boundary notes
- dashboard reporting updates include `github_summary`, `github_links_ready`, and GitHub-link action-center items

M41 safety posture:

- local-only and file-backed
- no GitHub API calls
- no `gh` calls
- no GraphQL or REST calls
- no network service calls
- no live GitHub validation
- no local/cloud/Codex/ChatGPT/Ollama model invocation

Future after M41 (not implemented in M41):

- explicitly gated GitHub sync/validation execution with operator approvals and additional safeguards

### M40 - Reporting, Dashboard Polish, And Operator Workflows

Status: Completed (local-only control-plane reporting and workflow guidance).

Delivered M40 outcomes:

- local Hub API report endpoints:
  - `GET /api/reports/dashboard`
  - `GET /api/reports/action-center`
  - `GET /api/reports/readiness`
  - `GET /api/reports/operator-workflows`
  - `GET /api/reports/export`
- Home now acts as a polished local operator dashboard with status cards, readiness indicators, action-center preview, and workflow cards.
- Reports now includes project/repo/queue/agent/orchestration/escalation/docs/readiness/action-center/workflow sections plus local export/copy report actions.
- Settings now includes default local paths, artifact folders, boundary confirmations, known limitations, and next milestone scope.

M40 safety posture:

- local-only and file-backed
- report-only and plan-only workflow guidance
- no agent execution
- no local/cloud/Codex/ChatGPT/Ollama model execution
- no GitHub calls
- no `gh` calls
- no network service calls
- no external API calls
- no live GitHub sync execution
- no authentication implementation yet
- no production deployment implementation yet

Next-phase focus after M40:

- richer guided workflows and optional execution gates
- authentication hardening if exposed beyond localhost
- controlled GitHub sync execution behind explicit safeguards
- optional LLM execution behind explicit user-approved gates

### M39 - Hub Agent, Handoff, Orchestration, And Escalation Screens

Status: Completed (local-only, file-backed interactive planning workflows).

Delivered M39 outcomes:

- local Hub API endpoints for agent profiles, handoff targets, handoff preview, orchestration plan, and escalation plan:
  - `GET/POST /api/agents`
  - `GET /api/agents/{agent_id}`
  - `GET/POST /api/handoff-targets`
  - `GET /api/handoff-targets/{target_id}`
  - `GET /api/handoff/preview`
  - `GET/POST /api/orchestration/plan`
  - `GET/POST /api/escalation/plan`
- local Hub static UI now includes interactive:
  - Agents profile list and add/update form
  - Handoff targets list and add/update form
  - Handoff preview refresh panel
  - Orchestration planning controls and plan detail rendering
  - Escalation planning controls and classification/detail rendering
- M39 uses existing local operators instead of duplicating business logic:
  - M34 local agent profiles and handoff targets
  - M35 local orchestration planner
  - M36 local escalation planner
  - M26 local handoff package generation for preview content

M39 safety posture:

- local-only, local-first, file-backed management and planning surface
- orchestration and escalation remain plan-only
- no agent execution
- no local/cloud/Codex/ChatGPT/Ollama model execution
- no GitHub calls
- no `gh` calls
- no network service calls
- no external API calls
- no authentication implementation yet
- no production deployment implementation yet
- no live GitHub sync yet

Upcoming milestone split:

- M40 completed locally; follow-on work shifts to guided workflows, execution gates, and controlled sync/auth hardening.

### M38 - Hub Project, Repo, And Queue Management

Status: Completed (local-only interactive management screens and API).

Delivered M38 outcomes:

- local Hub API endpoints for managed projects, managed repos, and queue items:
  - `GET/POST /api/projects`
  - `GET /api/projects/{project_id}`
  - `GET/POST /api/projects/{project_id}/repos`
  - `GET/POST /api/queue`
  - `GET/PATCH /api/queue/{item_id}`
- local Hub static UI now includes interactive:
  - Projects list and create/update form
  - Repos selector, list, and create/update form
  - Queue filter surface, item display, create/update form, and quick status updates
  - Home readiness hints and Settings local storage-path display
- M38 uses M32 managed-project registry and M33 local queue operators/storage rather than duplicating business logic.

M38 safety posture:

- local-only, local-first, file-backed management surface
- no GitHub calls
- no `gh` calls
- no network service calls
- no local/cloud LLM calls
- no Codex/ChatGPT/Ollama calls
- no external API calls
- no authentication implementation yet
- no production deployment implementation yet
- no live GitHub sync yet
- no agent/LLM execution yet

Upcoming milestone split:

- M40 completed locally; follow-on work shifts to guided workflows, execution gates, and controlled sync/auth hardening.

### M37 - AresForge Hub UI Foundation

Status: Completed (local-first Hub foundation only).

Delivered M37 outcomes:

- local Hub package and static frontend shell under `src/aresforge/hub/`
- local Hub server command: `python -m aresforge serve-hub [--host <host>] [--port <port>] [--open-browser]`
- local API shell endpoints: `GET /api/health`, `GET /api/summary`, `GET /api/docs/status`
- persistent Hub navigation and Home summary view with local empty-state handling
- Settings boundary confirmations and placeholder sections for future milestones
- lightweight local dashboard helper for summary/docs/warnings/next-actions aggregation

M37 safety posture:

- local-only serving and API surface
- binds to `127.0.0.1` by default
- no GitHub calls
- no `gh` calls
- no network service calls
- no local/cloud LLM calls
- no Codex/ChatGPT/Ollama calls
- no external API calls
- no authentication implementation yet
- no production deployment implementation yet
- no agent execution yet
- no live GitHub sync yet

Upcoming milestone split:

- M38: project/repo/queue management screens
- M39: agent/orchestration/escalation/handoff screens
- M40: completed locally; next scope is guided workflows, optional execution gates, and controlled sync/auth hardening

### M36 - Cloud LLM Escalation Planner

Status: Completed (local-only, plan-only advisory classification).

Delivered M36 outcomes:

- `plan-llm-escalation` local command for queue/profile/orchestration-based escalation planning
- classification buckets for local LLM, Codex, cloud advisory, human-required, and blocked/clarification
- recommended handoff target generation from local agent profiles and handoff target metadata
- copy/paste prompt guidance with explicit local-only and external-call boundaries
- escalation artifact linkage in M26 handoff package generation (`artifacts/escalation/`)
- operator/context/architecture documentation updates for advisory-only escalation posture

M36 safety posture:

- local-only planning surface
- plan-only classification output
- cloud escalation is advisory only
- no LLM invocation
- no local LLM calls
- no cloud LLM calls
- no Codex execution
- no ChatGPT calls
- no `gh` calls
- no GitHub API calls
- no network access

### M0-M20

Status: Completed.

### M21 - Self-Managed Milestone Execution Loop

Status: Completed.

Parent issue:

- `#345` M21 self-managed milestone execution loop (OPEN)

Child issues:

- `#346` CLOSED via PR `#354`
- `#347` CLOSED via PR `#355`
- `#348` CLOSED via PR `#356`
- `#349` CLOSED via PR `#357`
- `#350` CLOSED via PR `#358`
- `#351` CLOSED via PR `#359`
- `#352` CLOSED via PR `#360`
- `#353` OPEN (final source-of-truth reconciliation; must be processed last)

Delivered M21 outcomes:

- `inspect-self-managed-milestone-execution-contract`
- `run-sequential-child-closeout-flow`
- `generate-sequential-closeout-execution-package`
- `generate-self-managed-milestone-handoff`
- `simulate-self-managed-milestone-execution`
- M21 operator workflow and architecture documentation updates

M21 safety posture:

- no autonomous broad mutation
- no bulk closure
- no parent closeout before all children are closed/accounted for
- mutation execution defaults to dry-run/planning unless explicitly approved
- every child is executed with dedicated branch, PR, validation, evidence comment, and targeted closeout
- final reconciliation kept last and docs-focused
- prior milestones are not mutated

M21 standard validation bundle:

- `git diff --check`
- `python -m pytest`
- `python -m aresforge inspect-repo-governance`
- `python -m aresforge inspect-milestone-dashboard --parent-issue 345`
- `python -m aresforge inspect-milestone-state --parent-issue 345`
- `python -m aresforge inspect-self-managed-milestone-execution-contract`
- `python -m aresforge simulate-self-managed-milestone-execution --parent-issue 345`

### M22 - Evidence Bundle And Documentation Automation

Status: Completed.

Parent issue:

- `#362` CLOSED

Child issues:

- `#363` CLOSED via PR `#372`
- `#364` CLOSED via PR `#373`
- `#365` CLOSED via PR `#374`
- `#366` CLOSED via PR `#375`
- `#367` CLOSED via PR `#376`
- `#368` CLOSED via PR `#377`
- `#369` CLOSED via PR `#378`
- `#370` CLOSED via PR `#379`
- `#371` CLOSED via PR `#380`

Delivered M22 outcomes:

- `inspect-evidence-bundle-automation-contract`
- `generate-child-closeout-evidence-bundle`
- `generate-parent-closeout-evidence-bundle`
- `generate-pr-evidence-bundle`
- validation summary normalization (`pass`/`fail`/`warning`/`unknown`)
- `simulate-evidence-bundle-generation`
- operator and architecture documentation updates for evidence bundle workflows

M22 safety posture:

- no autonomous broad mutation
- no bulk closure
- no parent closeout before all children are closed/accounted for
- mutation execution defaults to dry-run/planning unless explicitly approved
- every child is executed with dedicated branch, PR, validation, evidence comment, and targeted closeout
- final reconciliation kept last and docs-focused
- prior milestones are not mutated

M22 standard validation bundle:

- `git diff --check`
- `python -m pytest`
- `python -m aresforge inspect-repo-governance`
- `python -m aresforge inspect-milestone-dashboard --parent-issue 362`
- `python -m aresforge inspect-milestone-state --parent-issue 362`
- `python -m aresforge check-milestone-evidence-readiness --parent-issue 362`
- `python -m aresforge inspect-parent-closeout-readiness --parent-issue 362`
- `python -m aresforge generate-parent-closeout-evidence-bundle --parent-issue 362`

### M23 - Milestone Lineage And Evidence Mapping Preflight

Status: Completed.

Parent issue:

- `#381` CLOSED

Child issues:

- `#382` CLOSED via PR `#391`
- `#383` CLOSED via PR `#392`
- `#384` CLOSED via PR `#393`
- `#385` CLOSED via PR `#394`
- `#386` CLOSED via PR `#395`
- `#387` CLOSED via PR `#396`
- `#388` CLOSED via PR `#397`
- `#389` CLOSED via PR `#398`
- `#390` CLOSED (final source-of-truth reconciliation child)

Delivered M23 outcomes:

- `inspect-milestone-closeout-preflight-contract`
- `inspect-parent-child-linkage-preflight`
- `inspect-child-evidence-marker-preflight`
- `inspect-pr-mapping-preflight`
- `generate-closeout-preflight-repair-guidance`
- `inspect-milestone-closeout-preflight`
- operator documentation updates for preflight sequencing and state interpretation

M23 safety posture:

- no autonomous broad mutation
- no bulk closure
- no parent closeout before all children are closed/accounted for
- mutation execution defaults to dry-run/planning unless explicitly approved
- repair guidance remains copy/paste text only and does not execute mutation
- final reconciliation kept last and docs-focused
- prior milestones are not mutated

M23 standard validation bundle:

- `git diff --check`
- `python -m pytest`
- `python -m aresforge inspect-repo-governance`
- `python -m aresforge inspect-milestone-dashboard --parent-issue 381`
- `python -m aresforge inspect-milestone-state --parent-issue 381`
- `python -m aresforge check-milestone-evidence-readiness --parent-issue 381`
- `python -m aresforge inspect-parent-closeout-readiness --parent-issue 381`
- `python -m aresforge inspect-milestone-closeout-preflight --parent-issue 381`

### M24 - Canonical Evidence Marker Workflow

Status: Completed.

Parent issue:

- `#400` M24 canonical evidence marker workflow (OPEN)

Child issues:

- `#401` CLOSED via PR `#411`
- `#402` CLOSED via PR `#412`
- `#403` CLOSED via PR `#413`
- `#404` CLOSED via PR `#414`
- `#405` CLOSED via PR `#415`
- `#406` CLOSED via PR `#416`
- `#407` CLOSED via PR `#417`
- `#408` CLOSED via PR `#418`
- `#409` CLOSED via PR `#419`
- `#410` CLOSED

Delivered M24 outcomes:

- `inspect-canonical-evidence-marker-contract`
- `generate-child-evidence-marker-template`
- `generate-pr-evidence-marker-template`
- `generate-parent-closeout-marker-template`
- `generate-preflight-baseline-snapshot`
- `diff-preflight-snapshots`
- canonical-marker integration in evidence bundles and preflight guidance
- canonical-first preflight parsing with backward-compatible fallback
- operator and architecture documentation updates for canonical marker workflow

M24 safety posture:

- no autonomous broad mutation
- no bulk closure
- no parent closeout before all children are closed/accounted for
- mutation execution defaults to dry-run/planning unless explicitly approved
- canonical marker and snapshot/diff commands are read-only by default
- final reconciliation kept last and docs-focused
- prior milestones are not mutated

M24 standard validation bundle:

- `git diff --check`
- `python -m pytest`
- `python -m aresforge inspect-repo-governance`
- `python -m aresforge inspect-milestone-dashboard --parent-issue 400`
- `python -m aresforge inspect-milestone-state --parent-issue 400`
- `python -m aresforge check-milestone-evidence-readiness --parent-issue 400`
- `python -m aresforge inspect-parent-closeout-readiness --parent-issue 400`
- `python -m aresforge inspect-milestone-closeout-preflight --parent-issue 400`
- `python -m aresforge inspect-canonical-evidence-marker-contract`

### M25 - Automatic Canonical Marker Emission Workflow

Status: Final reconciliation in progress (`#430` only).

Parent issue:

- `#421` M25 automatic canonical marker emission workflow (OPEN; pending final closeout)

Child issues:

- `#422` CLOSED via PR `#431`
- `#423` CLOSED via PR `#432`
- `#424` CLOSED via PR `#433`
- `#425` CLOSED via PR `#434`
- `#426` CLOSED via PR `#435`
- `#427` CLOSED via PR `#436`
- `#428` CLOSED via PR `#437`
- `#429` CLOSED via PR `#438`
- `#430` OPEN (final source-of-truth reconciliation; must be processed last)

Delivered M25 outcomes:

- `inspect-automatic-canonical-evidence-emission-contract`
- canonical marker completeness emitted by child closeout evidence bundles
- canonical marker completeness emitted by PR evidence bundles
- canonical marker completeness emitted by parent closeout evidence bundles
- canonical marker completeness emitted by generated closeout comment templates
- `check-closeout-readiness-by-construction` read-only readiness gate
- regression fixtures proving complete generated marker paths do not require post-hoc marker repair
- operator documentation updates for automatic marker workflow
- local/offline state-file parent closeout readiness workflow implemented and pushed through `40de9fe`
- local-only `--state-file` command path for rate-limit-window execution without `gh`/GitHub API calls
- sample offline-ready fixture at `tests/fixtures/offline_state/parent_closeout_ready.json`

M25 safety posture:

- no autonomous broad mutation
- no bulk closure
- no parent closeout before all children are closed/accounted for
- mutation execution defaults to dry-run/planning unless explicitly approved
- marker generation/checking and readiness-by-construction remain read-only by default
- final reconciliation kept last and docs-focused
- prior milestones are not mutated

M25 standard validation bundle:

- `git diff --check`
- `python -m pytest`
- `python -m aresforge inspect-repo-governance`
- `python -m aresforge check-closeout-readiness-by-construction --parent-issue 421`
- `python -m aresforge inspect-milestone-state --parent-issue 421`
- `python -m aresforge check-milestone-evidence-readiness --parent-issue 421`
- `python -m aresforge inspect-parent-closeout-readiness --parent-issue 421`
- `python -m aresforge generate-parent-closeout-evidence-bundle --parent-issue 421`

M25 offline state-file readiness path:

- Preferred during GitHub GraphQL/API rate-limit windows.
- `python -m aresforge inspect-milestone-state --parent-issue <n> --state-file <path>`
- `python -m aresforge check-milestone-evidence-readiness --parent-issue <n> --state-file <path>`
- `python -m aresforge inspect-parent-closeout-readiness --parent-issue <n> --state-file <path>`
- `python -m aresforge generate-parent-closeout-evidence-bundle --parent-issue <n> --state-file <path>`
- `python -m aresforge check-closeout-readiness-by-construction --parent-issue <n> --state-file <path>`
- Docs/sample checkpoint validation: `python -m pytest` passed (`502` tests).

M25 head tracking:

- main before remaining sequence (#428/#429/#430): `dd856632e2f1831b20b73613f29e9e953771180f`
- main after #428 and #429 merges: `cafda2ceda0a329de7d06a42c0edc6725ece3b10`
- final main after #430 merge: pending

### M26 - Local Handoff Package Generator

Status: Implemented.

Delivered M26 outcomes:

- `generate-handoff-package` local-only command added.
- Markdown and JSON handoff rendering from local repo/doc state.
- Safe local git-state capture limited to approved command set.
- Output write safety with directory creation, overwrite refusal, and `--force`.
- Source-of-truth doc ingestion with graceful missing-doc warnings.
- Continuity sections for human, Codex, and local LLM session handoff.
- Unit and CLI coverage for markdown/json output, stdout behavior, and overwrite protection.

M26 milestone value:

- Reduces manual handoff authoring and improves continuity across sessions/chats.
- Provides a prerequisite local continuity baseline before multi-project queue/orchestration/dashboard/cloud escalation milestones.

### M35 - Local Multi-Agent Orchestration Planner

Status: Implemented.

Delivered M35 outcomes:

- Added `plan-agent-orchestration` local command for plan-only multi-agent orchestration recommendations.
- Reads local inputs from M32 managed-project registry, M33 project queue, and M34 agent profiles when available.
- Handles missing queue/profiles/registry inputs with warning-only degraded planning output.
- Produces stable JSON and readable markdown with:
  - recommended assignments
  - dependency ordering
  - blocked items
  - unassigned items
  - handoff prompts
  - risk warnings
  - next actions
  - explicit boundary confirmations
- M26 handoff package now references latest orchestration artifact under `artifacts/orchestration/` when available, or emits orchestration capability guidance.

M35 safety posture:

- local-only
- plan-only
- no agent execution
- no local LLM invocation
- no cloud LLM invocation
- no `gh`
- no GitHub API calls
- no network access

## Standing Boundaries

- No autonomous mutation without explicit mode selection.
- No autonomous queue workers.
- No automatic PR merge.
- No unattended background execution.

### M27 - Local Project State Ledger

Status: Implemented.

Delivered M27 outcomes:

- Persistent local project-state ledger under `.aresforge/state/project_state.json`.
- Append-only local operation log under `.aresforge/state/operation_log.jsonl`.
- Local-only CLI commands for ledger init/inspect/update and operation log append/inspect.
- M26 handoff package integration now includes local project-state summary when present.
- Handoff generation warning behavior when ledger is missing (generation still succeeds).
- Unit and CLI test coverage for ledger lifecycle and operation log behavior.

M27 milestone value:

- Establishes a broader local project state foundation beyond closeout-specific offline files.
- Removes GitHub as the only practical source for local progress/state tracking.
- Prepares future multi-project queue/orchestration/documentation/sync workflows for local-first continuity.

### M28 - Documentation Agent Foundation

Status: Implemented.

Delivered M28 outcomes:

- `plan-doc-reconciliation` local-only planning command added.
- Deterministic reconciliation output in markdown or stable JSON.
- Source-of-truth documentation inspection plus local project-state alignment checks.
- Optional local git-state inspection via approved command subset only.
- Overwrite-safe output writing with directory creation and explicit `--force`.
- M26 handoff package now references latest local doc reconciliation plan when available.
- Test coverage for missing docs detection, recommendation generation, CLI output modes, and overwrite protection.

M28 safety posture:

- plan-only output; no automatic documentation edits
- local-only; no `gh` and no GitHub APIs
- no LLM calls
- no network dependency

### M29 - Offline-to-GitHub Sync Planner

Status: Implemented.

Delivered M29 outcomes:

- `plan-github-sync` local-only planning command added.
- Deterministic markdown/json sync-plan output with operation classification.
- Input support for offline closeout state file and local project state ledger.
- Candidate sections for comments, issue closures, PR evidence linkage, labels/milestones, and validation commands.
- Explicit boundary confirmations and no-GitHub-operations statement in generated plans.
- Overwrite-safe output behavior with directory creation and `--force` gating.
- M26 handoff package integration now references latest local sync plan in `artifacts/github-sync/`.
- M28 docs reconciliation planner now flags follow-up docs review after sync planning when applicable.

M29 safety posture:

- plan-only output; no GitHub mutation execution
- local-only; no `gh`, no GitHub APIs
- no network dependency
- no automatic issue comment posting, issue closure, PR creation, or live sync validation

### M30 - Self-Managed Local Milestone Lifecycle

Status: Implemented.

Delivered M30 outcomes:

- Local milestone definition template generation under operator-defined local paths (suggested `.aresforge/milestones/`).
- Local milestone inspection command with deterministic markdown/json rendering.
- Local milestone readiness checks for required fields, required docs/artifacts, validation command coverage, closeout requirement coverage, and optional project-state documentation status alignment.
- Local milestone closeout generation with readiness summary, checklist output, and lifecycle reminders.
- Lifecycle integration across prior milestones:
  - M27 local project state (`current_milestone`/`current_phase`) as readiness context.
  - M28 documentation reconciliation planning as required lifecycle follow-up.
  - M26 handoff package continuity includes active local milestone when inferable.
  - M29 offline-to-GitHub sync planning referenced as optional future sync step.

M30 safety posture:

- local-only plan/check/generate commands
- no `gh`, no GitHub API calls, no network usage
- no LLM calls
- no live mutation execution

### M31 - Foundation Reconciliation and Next-Phase Planning

Status: Implemented.

Delivered M31 outcomes:

- Reconciled source-of-truth docs across build state, agent context, roadmap, runnable skeleton, and operator usage.
- Confirmed M26-M30 foundation status and boundaries in one aligned narrative.
- Documented that AresForge now has a local-first foundation for self-managed operation.
- Documented that GitHub is optional/syncable and not mandatory for local planning.
- Preserved and clarified M26-M30 command surfaces:
  - M26 handoff package generation
  - M27 local project state ledger
  - M28 plan-only documentation reconciliation
  - M29 plan-only offline-to-GitHub sync planning
  - M30 local self-managed milestone lifecycle

M31 safety posture:

- no new GitHub API calls in this foundation batch
- no new LLM API calls in this foundation batch
- local-first planning remains available without GitHub access
- no automatic sync execution, no background automation, no unattended mutation

### M32 - Multi-Project / Multi-Repo Local Registry

Status: Implemented.

Delivered M32 outcomes:

- Added local managed-project registry defaults under `.aresforge/projects/projects.json`.
- Implemented local-only project and repo registration with idempotent update behavior.
- Added local inspection commands with stable JSON default and readable markdown option.
- Added validation gates for project/repo statuses and repo roles.
- Added clear missing-registry and missing-project error paths for register/inspect workflows.
- Integrated managed-project registry summary into M26 local handoff package when registry exists.
- Added unit and CLI coverage for registry initialization, registration/update idempotency, validation, and inspection paths.

M32 safety posture:

- local-only command surface
- no `gh`
- no GitHub API calls
- no network access
- no queue/orchestration execution introduced in this milestone

### M33 - Local Project Queue And Work Tracking

Status: Implemented.

Delivered M33 outcomes:

- Added local queue defaults under `.aresforge/queue/work_items.json`.
- Implemented local-only queue lifecycle commands for initialization, add/update item mutation, and queue/item inspection.
- Added queue schema with deterministic work item fields for status, priority, type, dependencies, blocking relationships, and future agent assignment metadata.
- Added queue validation gates for status, priority, and item type values.
- Added clear error paths for missing queue file and missing queue item updates.
- Added warning-only dependency-link checks for future item references.
- Added local registry validation reuse: queue item add validates `project_id` and `repo_id` against M32 registry when available or explicitly supplied.
- Integrated queue summary into M26 local handoff package when queue exists.
- Added unit and CLI coverage for queue lifecycle, filtering, markdown/json inspection output, validation behavior, and handoff integration.

M33 safety posture:

- local-only command surface
- no `gh`
- no GitHub API calls
- no network access
- no LLM calls
- `assigned_agent` persisted as metadata only; no agent orchestration execution introduced in this milestone

### M34 - Local LLM Agent Profiles And Handoff Targets

Status: Implemented.

Delivered M34 outcomes:

- Added local agent profile defaults under `.aresforge/agents/agents.json` with schema fields `schema_version`, `updated_at`, `agents`, and `handoff_targets`.
- Implemented local-only profile and target lifecycle commands for initialization, idempotent registration/update, and profile/target inspection.
- Added validation gates for supported agent roles, execution modes, handoff target types, and statuses.
- Added safe boolean parsing for `--escalation-allowed true|false`.
- Added warning-only behavior when agent `handoff_target_id` references a target not yet registered.
- Added optional default profile seeding for architect, implementer, tester, documentation, reviewer, operator, local-llm-general, and cloud-escalation.
- Integrated agent profile summary into M26 local handoff package when profiles exist.
- Clarified M33 linkage so `assigned_agent` can reference M34 `agent_id` without introducing orchestration execution.
- Added unit and CLI coverage for initialization, overwrite protection, idempotency, validation failures, filtering, markdown/json output, and handoff summary integration.

M34 safety posture:

- local-only command surface
- no `gh`
- no GitHub API calls
- no network access
- no local LLM invocation
- no cloud LLM invocation
- handoff targets are descriptive/advisory only
- no agent execution/orchestration introduced in this milestone

## Next Phase Roadmap (Planned)

The next phase shifts from single-repo local foundation hardening to multi-project and multi-agent project-management capabilities.

- Multi-agent orchestration planning.
- Escalation to cloud LLMs.
- Project dashboard and local project management reporting.
- Optional later GitHub sync execution.
- Optional later web dashboard UI.
- Optional later background daemon or scheduler.

## Known Limitations (Current Foundation Batch)

- No actual LLM invocation yet.
- No cloud LLM API integration yet.
- No GitHub sync execution yet.
- No web dashboard UI yet.
- No cross-machine coordination yet.
- No background daemon/scheduler yet.
