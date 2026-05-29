# AresForge Agent Context

## M50 Handoff Generator Context

Status: Completed locally on `main`.

Current handoff contract:

- operator function: `generate_local_project_handoff(...)` in `src/aresforge/operator/local_project_handoff.py`
- Hub route: `POST /api/local-project/handoff`
- Handoff UI includes a Local Project Handoff Generator form and copy/paste preview

Inputs:

- optional `project_id`
- `include_queue`, `include_reports`, and `include_evidence` booleans
- optional `next_milestone` and `next_instruction`
- optional local `output` path and `force`

Output:

- stable JSON with `ok`, `project_id`, `project_name`, `generated_at`, `handoff_markdown`, `summary`, optional `output_path`, `next_safe_action`, `warnings`, and `blockers`
- markdown includes operating rules, architecture boundaries, Hub capabilities, queue/report/progress state, open work, blockers/warnings, evidence/closeout state, next milestone/instruction, and startup validation commands

Boundary reminders:

- local-only, file-backed, and operator-gated
- read-only unless explicitly writing an optional local artifact
- no GitHub API/`gh`, issue/PR/workflow activity, GitHub mutation, agent execution, Codex execution, local LLM execution, model routing, or external execution
- handoff generation builds on Reports v1 and M48 progress rollup state

Recommended next milestone:

- M51 - Project AI Settings Contract.

## M49 Reports v1 Context

Status: Completed locally on `main`.

Current Reports v1 contract:

- operator function: `read_local_project_reports(...)` in `src/aresforge/operator/local_project_report.py`
- Hub route: `GET /api/reports/local-projects`
- Reports UI includes a read-only Reports v1 panel

Reports v1 sections:

- overall project count and project status counts
- active project summary
- queue totals and counts by status, type, and assigned lane/agent
- blocked, ready, in-progress, evidence captured, closeout eligible, and closed/completed work
- latest activity summary
- M48 active project progress rollup integration
- local-only operating boundary summary, limitations, blockers, warnings, and `next_safe_action`

Boundary reminders:

- Reports v1 is local-only, file-backed, and read-only
- it does not mutate queue/project state or implement PDF/CSV/export workflows
- no Codex, local LLM, real agent, GitHub, `gh`, workflow, push, external execution, prompt execution, or routing execution
- routing implementation remains future work after workflow/reporting milestones

Recommended next milestone:

- M50 - Handoff Generator.

## M48 Project Progress Rollup Context

Status: Completed locally on `main`.

Current progress rollup contract:

- operator function: `read_local_project_progress_rollup(...)` in `src/aresforge/operator/local_project_queue.py`
- Hub route: `GET /api/projects/{project_id}/progress-rollup`
- Projects UI includes a small read-only Project Progress Rollup panel

Rollup content:

- project id/name and active-project flag
- total queue items
- counts by status, type, and assigned lane/agent
- ready, blocked, and in-progress item counts/lists
- evidence captured count/list
- closeout-eligible count/list
- closed/completed count/list
- latest activity timestamp, blockers, warnings, and `next_safe_action`

Boundary reminders:

- rollup is read-only and local-only
- no queue mutation, report generation, prompt generation/execution, Codex/local LLM/agent execution, model routing, GitHub/`gh`, push, workflow, or external execution
- routing metadata remains future/not implemented placeholder information only
- Reports v1 is not implemented by M48

Recommended next milestone:

- M49 - Reports v1.

## M47 Queue Item Closeout Workflow Context

Status: Completed locally on `main`.

Current closeout contract:

- operator function: `close_local_queue_item(...)` in `src/aresforge/operator/local_project_queue.py`
- Hub route: `POST /api/local-queue/items/{item_id}/closeout`
- Queue UI includes a minimal Close Out Queue Item form in the local lifecycle area

Closeout requirements:

- queue item must exist
- queue item must be `in_progress`
- completion evidence must exist
- completion evidence must include `evidence_summary`, `validation_results`, and `diff_check_result`
- operator must provide a closeout summary
- closeout must be explicitly requested by the operator

Closeout result:

- status transitions to existing `done` convention
- records `closed_at`, `closed_by`, `closeout_summary`, and `closeout_history`
- preserves `completion_evidence`
- returns stable local JSON with `next_safe_action`

Boundary reminders:

- local-only, file-backed, operator-gated
- no prompt generation or execution
- no Codex, local LLM, real agent, GitHub, `gh`, workflow, push, or external execution
- Agent/LLM routing remains future work

Recommended next milestone:

- M48 - Project Progress Rollup.

## M46 Completion Evidence Capture Context

Status: Completed locally on `main`.

Current evidence capture contract:

- operator function: `capture_local_queue_completion_evidence(...)` in `src/aresforge/operator/local_project_queue.py`
- Hub route: `POST /api/local-queue/items/{item_id}/evidence`
- Queue UI includes a minimal Capture Completion Evidence form in the local lifecycle area
- captured evidence is stored on the queue item as `completion_evidence`

Evidence fields:

- `evidence_summary`
- `validation_commands`
- `validation_results`
- `smoke_checks`
- `diff_check_result`
- `files_changed`
- `commit_hash`
- `push_result`
- `operator_notes`
- `captured_at`

Boundary reminders:

- evidence capture is local-only, file-backed, and operator-gated
- evidence capture does not complete or close out a queue item
- `closeout_eligible` is advisory only
- Agent/LLM routing implementation remains future work
- no local LLM execution, Codex execution, real agent execution, automatic prompt execution, or GitHub mutation

Recommended next milestone:

- M47 - Queue Item Closeout Workflow.

## M45 Local Hub End-to-End Operator Workflow Context

Status: Completed locally on `main`.

Validated workflow:

1. Operator inspects dashboard/local project state.
2. Operator identifies active project context.
3. Operator creates a local queue item through Hub intake.
4. Operator views local queue item details.
5. Operator checks local readiness.
6. Operator generates a local-only prompt pack.
7. Operator inspects the local project report.
8. Operator inspects the local queue agent summary.

Validation guarantees:

- workflow remains local-only, file-backed, and operator-gated
- prompt-pack generation is advisory copy/paste output only
- prompt-pack generation does not automatically execute prompts
- prompt-pack generation does not auto-start or auto-complete queue items
- the canonical local queue remains the single queue storage model

Still not implemented:

- Agent/LLM routing implementation remains future work
- no local LLM execution, Codex execution, real agent execution, or automatic prompt execution
- no GitHub API, `gh`, GitHub issues/PRs/workflows, or GitHub mutation from the app

Recommended next milestone:

- M46 - completion evidence capture for local operator workflow closeout.

## M44A Agent LLM Routing Strategy Context

Status: Completed locally on `main`.

Canonical strategy document:

- `docs/architecture/AGENT_LLM_ROUTING_STRATEGY.md`

Future-state routing contract:

- AresForge must support project-specific AI routing settings.
- Future flow: Project -> Agent Lane -> Allowed Engines/Models -> Routing Decision Matrix -> Prompt Pack Output.
- Routing decisions should happen before prompt generation.
- The queue should remain one canonical local queue with future routing metadata and filtered routed views/lanes.
- M43 prompt packs currently generate local-only grouped prompts without LLM/model routing.

Future routing vocabulary:

- project AI modes: `balanced`, `local_only`, `codex_only`, `cost_saver`, `high_confidence`, `manual_only`
- engines: `local_reasoning_llm`, `local_coding_llm`, `codex_cli`
- agent lanes: Architect / Planner Agent, Coding Agent, Reviewer / Validator Agent, Documentation Agent, Test Agent, Local Operator Assistant, High-Value Codex Lane

Implementation boundaries:

- documentation-only milestone
- no runtime routing or route/UI/schema implementation yet
- no Codex execution, no agent execution, no local LLM execution, no model invocation
- no GitHub API, no `gh`, no GitHub issues/PRs/workflows, no GitHub mutation from the app

## M43 Agent Prompt Pack Generator

Status: Completed locally on `main`.

Current prompt-pack contract:

- operator function: `generate_local_queue_prompt_pack(...)` in `src/aresforge/operator/local_project_queue.py`
- Hub route: `POST /api/local-queue/prompt-pack`
- Queue UI provides operator-triggered generation, summary, and copy/paste preview/output path

Boundaries:

- local-only, file-backed, operator-gated
- prompt-pack generation is advisory-only; operator manually runs prompts
- no queue auto-start/auto-complete mutation from prompt-pack generation
- no Codex execution, no real agent execution, no LLM/model routing
- no GitHub API, no `gh`, no GitHub mutation, no external calls

## M42 Queue Item Detail Panel

Status: Completed locally on `main`.

Queue detail panel contract:

- queue detail uses existing read-only routes:
  - `GET /api/queue/{item_id}`
  - `GET /api/local-queue/items/{item_id}/readiness`
- no new mutation route introduced
- panel content is read-only/advisory and intended for inspection before lifecycle actions

Detail fields shown include:

- item id/title/status/type/priority
- project/repo association
- source/tags/created/updated
- description
- requested outcome, acceptance notes, and validation notes when present in notes metadata
- readiness summary/blockers/warnings when available

## M41 Active Project Task Intake v2

Status: Completed locally on `main`.

Current intake contract:

- local intake uses `POST /api/local-queue/items`
- required: `title`
- optional structured fields:
  - `description`
  - `item_type`
  - `priority`
  - `tags`
  - `source` (defaulted by UI to `active_project_workspace`)
  - `requested_outcome`
  - `acceptance_notes`
  - `validation_notes`

Persistence model:

- keeps queue schema backward compatible
- stores `source` directly on queue item
- stores requested outcome and notes as structured local text in queue item `notes`

Boundary reminders:

- local-only, file-backed, operator-gated
- queue item creation only
- no auto-start, no auto-prompt generation
- no GitHub/`gh`/GitHub mutation
- no agent/Codex/LLM execution

## M40 Dashboard Milestone Closeout And Docs Reconciliation

Status: Completed locally on `main`.

This closeout reconciles documentation for completed dashboard milestones M35-M39 without introducing runtime changes.

Dashboard contract and behavior baseline:

- backend/operator summary contract: `src/aresforge/operator/local_dashboard_summary.py`
- Hub route: `GET /api/dashboard/summary`
- Home cards/status panels: local read-only/advisory rendering from dashboard summary
- refresh model: manual refresh only
- UI states: explicit loading, empty, and error handling
- deep links: Home links into existing Workspace/Projects/Queue/Repos/Reports sections
- drilldowns: queue status drilldowns and advisory agent lane drilldowns

Frontend module baseline used by dashboard flows:

- `src/aresforge/hub/static/app.js`
- `src/aresforge/hub/static/js/sections/home.js`
- `src/aresforge/hub/static/js/sections/queue.js`
- `src/aresforge/hub/static/js/sections/projects.js`
- `src/aresforge/hub/static/js/sections/repos.js`
- `src/aresforge/hub/static/js/sections/reports.js`

Mandatory operating boundaries (reconfirmed):

- local-only, file-backed, operator-gated
- read-only/advisory dashboard posture
- no GitHub API, no `gh`, no GitHub issues/PRs/workflows mutation
- no real agent execution
- no Codex execution from the Hub app
- no local/cloud model routing or invocation

Validation baseline for this closeout:

- `python -m pytest tests/test_hub_ui_foundation.py tests/test_hub_dashboard_summary_api.py tests/test_local_dashboard_summary.py tests/test_hub_project_factory_api.py tests/test_hub_local_queue_lifecycle_api.py tests/test_hub_active_project_api.py tests/test_local_project_factory.py tests/test_local_active_project.py`
- `python -m aresforge inspect-local-queue-agent-summary`
- `python -m aresforge inspect-local-project-report`
- `git diff --check`

## M37 Dashboard Refresh, Empty States, and Error States

Status: Completed locally on main.

Delivered:

- Home dashboard refresh remains manual and re-reads GET /api/dashboard/summary
- clarified loading state messaging for local-only read-only advisory dashboard reads
- refined empty/error state messaging for missing active project, zero work, and summary fetch failures
- added a last-successful-load label for operator clarity

Boundary posture:

- local-only/read-only/advisory dashboard visibility
- no polling or background refresh
- no mutation, no execution, no GitHub/gh calls, no agent/Codex/model execution, no LLM routing
## M39 Queue And Agent Dashboard Drilldowns

Status: Completed locally on main.

Delivered:

- Home Local Dashboard now includes richer read-only queue-by-status advisory drilldowns
- Home Local Dashboard now includes richer read-only advisory agent lane drilldowns
- drilldowns use existing local dashboard summary payload and keep next safe action visible

Boundary posture:

- local-only/read-only/advisory dashboard visibility
- no mutation, no execution, no GitHub/gh calls, no agent/Codex/model execution, no LLM routing
## M38 Active Project Dashboard Deep Links

Status: Completed locally on main.

Delivered:

- Home Local Dashboard now includes deep-link controls into existing sections
- project context deep link routes to Projects when no active project is selected, otherwise routes to Workspace
- queue, advisory lane, repo status, and reports deep links route to existing Queue, Repos, and Reports sections

Boundary posture:

- navigation-only UI enhancement
- local-only/read-only/advisory behavior unchanged
- no mutation, GitHub calls, agent/Codex/model execution, or LLM routing
## M36 Home Dashboard UI Context

Current Home dashboard now consumes:

- `GET /api/dashboard/summary`

Home panels now display read-only/advisory:

- project summary (total projects, active project, active status)
- queue summary (total items and status counts)
- agent lane summary (lane totals/details)
- repo summary (availability/status/warnings)
- blockers and warnings (with empty-state messaging)
- next safe action

Boundary reminders remain:

- local-only/read-only/advisory
- no GitHub or `gh` calls
- no agent/Codex/model execution
- no LLM/model routing

## M35 Hub Dashboard Contract Context

Current Hub dashboard contract now includes:

- `GET /api/dashboard/summary`
- local-only read-only dashboard summary payload (`dashboard_type=hub_home`)
- project summary, queue summary, agent lane summary, repo summary, blockers/warnings, next safe action, and source summary fields

Boundary reminders:

- no mutation
- no GitHub or `gh` calls
- no agent/Codex/model execution
- local/file-backed inspection only

UI note:

- Home dashboard cards/panels are deferred to M36.

## Local LLM Planning Context (Documentation-Only)

AresForge now has documented future local Ollama model planning.

Planned local aliases:

- `aresforge-coder-local`
- `aresforge-reasoner-local`

Planned coding-model purpose:

- code generation
- bug fixing
- tests
- code review
- patch planning

Planned reasoning-model purpose:

- architecture planning
- task decomposition
- documentation synthesis
- risk analysis
- validation planning
- prompt optimization

Safety boundary:

- model output must not be treated as trusted execution authority
- generated commands and file changes must remain operator-approved

## M34 Frontend Modularization Closeout Context

Use this as the current frontend contract baseline:

- `src/aresforge/hub/static/app.js` is the ES module entrypoint.
- `src/aresforge/hub/static/index.html` loads `app.js` with `type="module"`.
- core modules:
  - `src/aresforge/hub/static/js/core/dom.js`
  - `src/aresforge/hub/static/js/core/http.js`
  - `src/aresforge/hub/static/js/core/state.js`
- section modules:
  - `src/aresforge/hub/static/js/sections/home.js`
  - `src/aresforge/hub/static/js/sections/workspace.js`
  - `src/aresforge/hub/static/js/sections/queue.js`
  - `src/aresforge/hub/static/js/sections/projects.js`
  - `src/aresforge/hub/static/js/sections/repos.js`
  - `src/aresforge/hub/static/js/sections/reports.js`
  - `src/aresforge/hub/static/js/sections/orchestration.js`
  - `src/aresforge/hub/static/js/sections/escalation.js`
- project-factory modules:
  - `src/aresforge/hub/static/js/sections/projectFactory/index.js`
  - `src/aresforge/hub/static/js/sections/projectFactory/scope.js`
  - `src/aresforge/hub/static/js/sections/projectFactory/architecture.js`
  - `src/aresforge/hub/static/js/sections/projectFactory/milestonePlan.js`
  - `src/aresforge/hub/static/js/sections/projectFactory/validation.js`
  - `src/aresforge/hub/static/js/sections/projectFactory/agentDispatch.js`
  - `src/aresforge/hub/static/js/sections/projectFactory/executionApproval.js`
  - `src/aresforge/hub/static/js/sections/projectFactory/closeout.js`

Validation baseline for this contract:

- `tests/test_hub_ui_foundation.py`
- `tests/test_hub_project_factory_api.py`
- `tests/test_hub_local_queue_lifecycle_api.py`
- `tests/test_hub_active_project_api.py`
- `tests/test_local_project_factory.py`
- `tests/test_local_active_project.py`
- smoke:
  - `python -m aresforge inspect-local-queue-agent-summary`
  - `python -m aresforge inspect-local-project-report`

Boundary context remains mandatory:

- local-first
- file-backed
- operator-gated
- no real agent execution
- no GitHub mutation
- no network execution beyond existing local Hub API behavior

Next recommended milestone:

- M35 - Hub Dashboard Data Contract And Read-Only Metrics

## M28 Hub Orchestration And Escalation Section Modules

Latest Hub frontend context now includes dedicated section modules for Orchestration and Escalation:

- `src/aresforge/hub/static/app.js` remains the only frontend entrypoint
- Orchestration render/load/binding logic now lives in `src/aresforge/hub/static/js/sections/orchestration.js`
- Escalation render/load/binding logic now lives in `src/aresforge/hub/static/js/sections/escalation.js`
- project-factory lifecycle, queue lifecycle, and execution-approval orchestration remain in `src/aresforge/hub/static/app.js`

Guidance for follow-on frontend work:

- keep `app.js` focused on cross-section orchestration and higher-coupling flows
- continue extracting only clearly section-owned behavior
- preserve DOM ids and API endpoint paths
- keep validating the combined frontend script surface, not only `app.js`

## M17 Local Queue Execution-Prep Lifecycle

Latest local queue progression now supports a full operator-driven execution-prep loop:

- add a local queue item
- inspect readiness
- start the item locally
- generate a local Codex prompt artifact or stdout prompt
- have a human run Codex manually
- complete the item with local validation evidence and commit metadata

New local queue command surface to know:

- `python -m aresforge add-local-queue-item --title <title> ...`
- `python -m aresforge inspect-local-queue-item-readiness --item-id <item_id>`
- `python -m aresforge start-local-queue-item --item-id <item_id>`
- `python -m aresforge generate-local-queue-item-codex-prompt --item-id <item_id> [--output <path>]`
- `python -m aresforge complete-local-queue-item --item-id <item_id> --commit-hash <hash> --validation-summary <text> ...`

Required operating boundaries remain unchanged:

- local-first and local-only
- no GitHub API calls or `gh` calls
- no GitHub sync/mutation execution
- no automatic Codex execution
- no agent execution
- no local/cloud/Codex/ChatGPT/Ollama model routing or invocation
- completion records evidence locally only and does not verify commits remotely

## M27 Hub Reports Section Module

Latest Hub frontend context now includes a Reports section module for the Reports UI slice:

- `src/aresforge/hub/static/app.js` remains the only frontend entrypoint
- Reports dashboard rendering, local project report rendering, report slice loading, export helpers, and Reports-specific bindings now live in `src/aresforge/hub/static/js/sections/reports.js`
- non-Reports orchestration and other higher-coupling flows still remain in `src/aresforge/hub/static/app.js`

Guidance for follow-on frontend work:

- keep `app.js` focused on orchestration and higher-coupling flows
- continue extracting only clearly section-owned behavior when cross-section dependencies stay manageable
- preserve DOM ids and API endpoint paths
- keep validating the combined frontend script surface, not only `app.js`

## M26 Hub Projects And Repos Section Modules

Latest Hub frontend context now includes Projects and Repos section modules for the next UI slices:

- `src/aresforge/hub/static/app.js` remains the only frontend entrypoint
- Projects list rendering, read-only rendering, selector refresh, and Projects-specific bindings now live in `src/aresforge/hub/static/js/sections/projects.js`
- Repos list rendering, repo loading/inspection, and Repos-specific bindings now live in `src/aresforge/hub/static/js/sections/repos.js`
- project-factory and other higher-coupling orchestration still remains in `src/aresforge/hub/static/app.js`

Guidance for follow-on frontend work:

- keep `app.js` focused on orchestration and higher-coupling flows
- continue extracting only clearly section-owned behavior when cross-section dependencies stay manageable
- preserve DOM ids and API endpoint paths
- keep validating the combined frontend script surface, not only `app.js`

## M25 Hub Queue Section Module

Latest Hub frontend context now includes a Queue section module for the queue UI slice:

- `src/aresforge/hub/static/app.js` remains the only frontend entrypoint
- queue read-only summary rendering/loading and queue item card rendering now live in `src/aresforge/hub/static/js/sections/queue.js`
- queue-only bindings now live in `src/aresforge/hub/static/js/sections/queue.js`
- local queue lifecycle internals remain in `src/aresforge/hub/static/app.js` for now because they are more tightly coupled to intake/start/readiness/prompt/complete flows

Guidance for follow-on frontend work:

- keep `app.js` focused on orchestration and higher-coupling flows
- continue extracting only clearly section-owned queue behavior until lifecycle internals are safer to split
- preserve DOM ids and API endpoint paths
- keep validating the combined frontend script surface, not only `app.js`

## M24 Hub Home And Workspace Section Modules

Latest Hub frontend context now includes section-level modules for the lowest-risk UI slices:

- `src/aresforge/hub/static/app.js` remains the only frontend entrypoint
- Home dashboard rendering/loading and Home-specific button wiring now live in `src/aresforge/hub/static/js/sections/home.js`
- Active Project Workspace rendering/loading, empty-state handling, and quick-action wiring now live in `src/aresforge/hub/static/js/sections/workspace.js`
- workspace quick-action binding still follows a single binding path

Guidance for follow-on frontend work:

- keep `app.js` focused on orchestration and shared cross-section flows
- keep Home/Workspace helpers in their section modules unless they become clearly shared
- preserve DOM ids and API endpoint paths
- continue validating the combined frontend script surface, not only `app.js`

## M23 Hub Frontend Modularization Foundation

Latest Hub frontend context now includes a browser-native ES module foundation:

- `src/aresforge/hub/static/app.js` remains the main entrypoint
- shared DOM helpers live in `src/aresforge/hub/static/js/core/dom.js`
- shared HTTP/payload helpers live in `src/aresforge/hub/static/js/core/http.js`
- the shared frontend state container lives in `src/aresforge/hub/static/js/core/state.js`
- duplicate workspace button binding was consolidated into one binding path

Guidance for follow-on frontend work:

- preserve `app.js` as the entrypoint unless a later milestone explicitly changes that contract
- keep DOM ids and API endpoint paths stable
- prefer moving only generic helpers into `js/core/*` until section/domain modules are ready
- update static tests to validate the combined frontend script surface, not a single monolith file

## M21 Active Project Workspace (UI & Operator Flow)

Added and validated locally:

- Active Project Workspace UI polish with clearer operator guidance and empty-state messaging.
- Workspace quick-actions annotated with "(local-only)" and explicit operator next-steps.
- Frontend action wiring to support refreshing the workspace, continuing task intake, opening the queue, and selecting projects.
- New focused regression tests (`tests/test_active_project_workspace.py`) that assert the active-workspace API payload shape for empty and seeded states.

Operating constraints (unchanged):

- local-first and file-backed control-plane only
- no GitHub API calls, no `gh` calls
- no agent execution, no Codex or LLM invocation
- no network or remote mutation


## M16 Hub Local-Only Read/Report Foundations

Latest local milestone progression adds read-only Hub foundations for:

- Home dashboard API wiring and UI
- Projects page UI
- Queue page UI
- Reports page UI

Required operating boundaries remain unchanged:

- local-first and local-only
- no GitHub API calls or `gh` calls
- no GitHub sync/mutation execution
- no agent execution
- no local/cloud/Codex/ChatGPT/Ollama model routing or invocation

Validation closeout for this layer includes targeted suites, full `pytest`, and local smoke commands. Push has not been performed.

## M14 Local Foundation Context

- Current source-of-truth stance:
  - local-first operation
  - direct-on-`main` workflow
  - read-only local reporting/inspection expansion
- Explicit restrictions for this layer:
  - no GitHub API calls
  - no `gh` calls
  - no GitHub issue/PR mutation for local read-model/report commands
  - no real agent execution
  - no LLM routing/invocation
- Historical status:
  - M9-M13 were completed, validated, committed, and pushed before this chat.
  - M14 local read-model/report commands were added in this chat and validated on local `main`.

New local read-only command surface to know:

- `python -m aresforge inspect-local-project-dashboard`
- `python -m aresforge list-local-projects`
- `python -m aresforge inspect-local-project-readiness --project-id <id>`
- `python -m aresforge inspect-local-queue-agent-summary`
- `python -m aresforge inspect-local-project-report`

## M46 Project Factory Alignment Context

Project-factory vision:

- AresForge is a local-first AI project factory and orchestration hub.
- Future implementation must converge on the canonical end-to-end pipeline defined in `docs/architecture/PROJECT_FACTORY_WORKFLOW.md`.

Implementation guardrails for future agents:

- no GitHub mutations without an explicit approved GitHub apply boundary
- no model/agent execution without explicit approval boundary
- local planning and local artifact generation first

Current foundation status:

- M43 active project support is the active context layer.
- M44 active project intake is the first user-to-queue bridge.
- M45 active project workbench is the mission-control foundation.
- This foundation is not yet the complete project-factory loop.

## Purpose

Provide minimum operating context for M42 first-run bootstrap/setup with a local-first, self-managed operator model.

## Current Operating Model

- Active milestone context: M42 first-run bootstrap and seed wizard in local registry and Hub.
- AresForge now has a local-first foundation for self-managed operation.
- GitHub is optional/syncable and not mandatory for local planning.
- M26 added local handoff package generation.
- M27 added the local project state ledger.
- M28 added plan-only documentation reconciliation.
- M29 added plan-only offline-to-GitHub sync planning.
- M30 added local self-managed milestone lifecycle support.
- M32 added local managed-project/multi-repo registry support.
- M33 added local project queue/work tracking support.
- M34 added local agent profiles and handoff target descriptors.
- M35 added local multi-agent orchestration planning (assignment + sequencing + handoff prompts).
- M36 added local escalation planning that classifies queue/orchestration work for local LLM, Codex, cloud advisory, human-required, and blocked/clarification paths.
- M37 added a local Hub server/API/frontend foundation intended to become the primary local entry point for AresForge.
- M38 added interactive local Hub screens and API workflows for M32 managed-project registry and M33 local queue management.
- M39 adds interactive local Hub screens and API workflows for M34 local agent profiles/handoff targets, M26 handoff preview, M35 orchestration planning, and M36 escalation planning.
- M40 adds unified local control-plane reporting, readiness indicators, action-center guidance, and operator workflow cards in Hub Home/Reports/Settings.
- M41 adds explicit local GitHub identity for managed projects/repos, primary repo linkage, local git-link inspection, and Hub GitHub linkage readiness/reporting surfaces.
- M42 adds first-run bootstrap status/plan/apply support for local file initialization and default seed data.
- Foundation-batch boundaries (M26-M30):
  - no `gh`
  - no GitHub API calls
  - no LLM API calls
  - no network-required execution path
- Current local-first command surface:
  - `python -m aresforge generate-handoff-package --output <path> [--format markdown|json] [--include-doc-excerpts] [--force]`
  - `python -m aresforge init-project-state [--path <path>] [--force]`
  - `python -m aresforge inspect-project-state [--path <path>]`
  - `python -m aresforge update-project-state [--path <path>] [--current-milestone <value>] [--current-phase <value>] [--current-mode <value>] [--validation-status <value>] [--documentation-status <value>] [--warning <text>]...`
  - `python -m aresforge append-operation-log [--state-path <path>] --event-type <type> --summary <summary> [--details <json>]`
  - `python -m aresforge inspect-operation-log [--state-path <path>] [--limit <n>]`
  - `python -m aresforge plan-doc-reconciliation [--output <path>] [--format json|markdown] [--include-git-state] [--force]`
  - `python -m aresforge plan-github-sync [--state-file <path>] [--project-state <path>] [--output <path>] [--format json|markdown] [--force]`
  - `python -m aresforge generate-local-milestone-template --milestone-id <id> --output <path> [--title <title>] [--force]`
  - `python -m aresforge inspect-local-milestone --definition <path> [--format json|markdown]`
  - `python -m aresforge check-local-milestone-readiness --definition <path> [--project-state <path>] [--format json|markdown]`
  - `python -m aresforge generate-local-milestone-closeout --definition <path> --output <path> [--format json|markdown] [--force]`
  - `python -m aresforge init-managed-project-registry [--path <path>] [--force]`
  - `python -m aresforge register-managed-project --project-id <id> --name <name> --root-path <path> [--registry-path <path>] [--description <text>] [--status <status>] [--default-branch <branch>] [--tag <tag>]... [--notes <text>]`
  - `python -m aresforge register-managed-project --project-id <id> --name <name> --root-path <path> [--registry-path <path>] [--description <text>] [--status <status>] [--default-branch <branch>] [--github-url <url>] [--github-owner <owner>] [--github-repo <repo>] [--github-default-branch <branch>] [--primary-repo-id <repo_id>] [--tag <tag>]... [--notes <text>]`
  - `python -m aresforge register-managed-repo --project-id <id> --repo-id <id> --name <name> --path <path> [--registry-path <path>] [--remote-url <url>] [--default-branch <branch>] [--github-url <url>] [--github-owner <owner>] [--github-repo <repo>] [--github-default-branch <branch>] [--inspect-local-git] [--role <role>] [--status <status>] [--tag <tag>]... [--notes <text>]`
  - `python -m aresforge inspect-managed-project-registry [--registry-path <path>] [--format json|markdown]`
  - `python -m aresforge inspect-managed-project --project-id <id> [--registry-path <path>] [--format json|markdown]`
  - `python -m aresforge inspect-managed-repo --project-id <id> --repo-id <id> [--registry-path <path>] [--format json|markdown]`
  - `python -m aresforge inspect-managed-repo-github-link --project-id <id> --repo-id <id> [--registry-path <path>] [--inspect-local-git] [--format json|markdown]`
  - `python -m aresforge inspect-bootstrap-status [--repo-path <path>]`
  - `python -m aresforge plan-bootstrap [--repo-path <path>] [--format json|markdown] [--seed-sample-work]`
  - `python -m aresforge apply-bootstrap [--repo-path <path>] [--force] [--seed-sample-work] [--format json|markdown]`
  - `python -m aresforge init-project-queue [--path <path>] [--force]`
  - `python -m aresforge add-queue-item --item-id <id> --project-id <id> --repo-id <id> --title <title> [--queue-path <path>] [--registry-path <path>] [--description <text>] [--status <status>] [--priority <priority>] [--type <type>] [--tag <tag>]... [--depends-on <item_id>]... [--blocked-by <item_id>]... [--assigned-agent <agent_id>] [--source <source>] [--notes <text>]`
  - `python -m aresforge update-queue-item --item-id <id> [--queue-path <path>] [--project-id <id>] [--repo-id <id>] [--status <status>] [--priority <priority>] [--type <type>] [--title <title>] [--description <text>] [--tag <tag>]... [--depends-on <item_id>]... [--blocked-by <item_id>]... [--assigned-agent <agent_id>] [--source <source>] [--notes <text>]`
  - `python -m aresforge inspect-project-queue [--queue-path <path>] [--project-id <id>] [--repo-id <id>] [--status <status>] [--type <type>] [--assigned-agent <agent_id>] [--format json|markdown]`
  - `python -m aresforge inspect-queue-item --item-id <id> [--queue-path <path>] [--format json|markdown]`
  - `python -m aresforge init-agent-profiles [--path <path>] [--force] [--with-defaults]`
  - `python -m aresforge register-agent-profile --agent-id <id> --name <name> --role <role> [--profiles-path <path>] [--description <text>] [--execution-mode <mode>] [--model-preference <value>] [--strength <text>]... [--constraint <text>]... [--allowed-type <type>]... [--escalation-allowed true|false] [--handoff-target-id <id>] [--status <status>] [--tag <tag>]... [--notes <text>]`
  - `python -m aresforge register-handoff-target --target-id <id> --name <name> --target-type <type> [--profiles-path <path>] [--description <text>] [--local-command <command>] [--input-format <format>] [--output-format <format>] [--safety-note <text>]... [--status <status>] [--tag <tag>]... [--notes <text>]`
  - `python -m aresforge inspect-agent-profiles [--profiles-path <path>] [--role <role>] [--execution-mode <mode>] [--status <status>] [--format json|markdown]`
  - `python -m aresforge inspect-agent-profile --agent-id <id> [--profiles-path <path>] [--format json|markdown]`
  - `python -m aresforge inspect-handoff-target --target-id <id> [--profiles-path <path>] [--format json|markdown]`
  - `python -m aresforge plan-agent-orchestration [--project-id <id>] [--repo-id <id>] [--status <status>] [--queue-path <path>] [--profiles-path <path>] [--registry-path <path>] [--output <path>] [--format json|markdown] [--force]`
  - `python -m aresforge plan-llm-escalation [--item-id <id>] [--project-id <id>] [--repo-id <id>] [--status <status>] [--queue-path <path>] [--profiles-path <path>] [--orchestration-plan <path>] [--output <path>] [--format json|markdown] [--force]`
  - `python -m aresforge serve-hub [--host <host>] [--port <port>] [--open-browser]`
- M33 boundary confirmations:
  - queue is local-only and can track work without GitHub issues
  - no `gh`
  - no GitHub API calls
  - no network access
  - no LLM calls
  - `assigned_agent` is data-only for future orchestration and does not execute agents
  - M32 registry validation is local-only when registry exists or `--registry-path` is supplied
- M34 boundary confirmations:
  - local-only configuration for agent and handoff metadata
  - handoff targets are descriptive/advisory only
  - no agent execution path is introduced yet
  - no local LLM invocation is introduced yet
  - no cloud LLM invocation is introduced yet
  - no `gh`, no GitHub API calls, no network access
  - M33 `assigned_agent` can reference M34 `agent_id`
- M35 boundary confirmations:
  - local-only orchestration planning
  - plan-only output (assignment and sequencing guidance only)
  - no agent execution
  - no local LLM invocation
  - no cloud LLM invocation
  - no `gh`, no GitHub API calls, no network access
  - reads M32 registry, M33 queue, and M34 profiles where available
- M36 boundary confirmations:
  - local-only escalation planning
  - plan-only classification output only (no execution)
  - cloud escalation is advisory only
  - no LLM invocation
  - no local LLM calls
  - no cloud LLM calls
  - no Codex execution
  - no ChatGPT calls
  - no `gh`, no GitHub API calls, no network access
  - reads M33 queue and M34 profiles where available and optional M35 orchestration artifact input when supplied
- M37 boundary confirmations:
  - local-first local UI serving path
  - binds to `127.0.0.1` by default
  - no `gh`, no GitHub API calls, no network service calls
  - no local LLM calls, no cloud LLM calls
  - no Codex calls, no ChatGPT calls, no Ollama calls
  - no external API calls
  - no agent execution
  - no live GitHub sync
  - no authentication implementation yet
  - no production deployment implementation yet
- M38 boundary confirmations:
  - local-first, file-backed project/repo/queue management via Hub API and static UI
  - no `gh`, no GitHub API calls, no network services
  - no local LLM calls, no cloud LLM calls, no Codex/ChatGPT/Ollama calls
  - no external API calls
  - no agent execution, no live GitHub sync
  - M40 reporting/dashboard/operator workflow surfaces are implemented as local-only report/plan-only flows
  - authentication and production deployment remain unimplemented
- M39 boundary confirmations:
- M40 boundary confirmations:
  - local-first, file-backed reporting and workflow guidance
  - report-only and plan-only control-plane surfaces
  - no agent execution
  - no local/cloud/Codex/ChatGPT/Ollama model invocation
  - no GitHub calls, no `gh` calls, no network/external API calls
  - no live GitHub sync execution
  - authentication and production deployment remain unimplemented
  - future work includes guided workflow depth, optional execution gates, auth hardening when exposed beyond localhost, controlled sync execution, and optional LLM execution behind explicit user approval gates
- M41 boundary confirmations:
  - GitHub links are local metadata only
  - local git inspection is local-only and non-networked
  - no GitHub API calls
  - no `gh` calls
  - no GraphQL/REST calls
  - no network service calls
  - no live GitHub validation
- M42 boundary confirmations:
  - bootstrap is local-only and file-backed
  - no GitHub API calls
  - no `gh` calls
  - no GraphQL/REST calls
  - no network service calls
  - no local/cloud/Codex/ChatGPT/Ollama calls
  - no live GitHub discovery/validation
- M39 boundary confirmations:
  - local-first, file-backed agent/handoff/orchestration/escalation management via Hub API and static UI
  - no `gh`, no GitHub API calls, no network services
  - no local LLM calls, no cloud LLM calls, no Codex/ChatGPT/Ollama calls
  - no external API calls
  - orchestration and escalation remain plan-only
  - no agent execution and no model invocation
  - handoff preview is local-only and does not post anywhere
  - M40 reporting/dashboard/operator workflow surfaces are implemented as local-only report/plan-only flows
  - authentication and production deployment remain unimplemented
- Next-phase planning focus:
  - richer guided Hub workflows and cross-section automation
  - optional execution gates with explicit user approval
  - authentication hardening if exposed beyond localhost
  - controlled GitHub sync execution behind explicit safety gates
  - optional LLM execution behind explicit user-approved gates

## Canonical Documents

- `docs/context/BUILD_STATE.md`
- `docs/context/AGENT_CONTEXT.md`
- `docs/roadmap/ROADMAP.md`
- `docs/operator/LOCAL_OPERATOR_USAGE.md`
- `docs/architecture/AUTOMATIC_CANONICAL_EVIDENCE_EMISSION_CONTRACT.md`
- `docs/architecture/MILESTONE_CLOSEOUT_PREFLIGHT_CONTRACT.md`
- `docs/architecture/RUNNABLE_SKELETON.md`

## Current M25 Commands

- `python -m aresforge inspect-automatic-canonical-evidence-emission-contract`
- `python -m aresforge generate-child-closeout-evidence-bundle --parent-issue <parent> --child-issue <child>`
- `python -m aresforge generate-pr-evidence-bundle --issue <child> --pr <pr>`
- `python -m aresforge generate-parent-closeout-evidence-bundle --parent-issue <parent>`
- `python -m aresforge generate-evidence-comment-template --issue <issue>`
- `python -m aresforge check-closeout-readiness-by-construction --parent-issue <parent>`

## M26 Continuity Command

- `python -m aresforge generate-handoff-package --output <path> [--format markdown|json] [--include-doc-excerpts] [--force]`
- If `--output` is omitted:
  - markdown is printed to stdout by default
  - JSON is printed to stdout when `--format json`

## Offline State-File Commands

- `python -m aresforge inspect-milestone-state --parent-issue <n> --state-file <path>`
- `python -m aresforge check-milestone-evidence-readiness --parent-issue <n> --state-file <path>`
- `python -m aresforge inspect-parent-closeout-readiness --parent-issue <n> --state-file <path>`
- `python -m aresforge generate-parent-closeout-evidence-bundle --parent-issue <n> --state-file <path>`
- `python -m aresforge check-closeout-readiness-by-construction --parent-issue <n> --state-file <path>`
- Example fixture: `tests/fixtures/offline_state/parent_closeout_ready.json`.
- Validation checkpoint: `python -m pytest` passed with `502` tests.

## M25 Child/PR Mapping

- `#431` -> child `#422`
- `#432` -> child `#423`
- `#433` -> child `#424`
- `#434` -> child `#425`
- `#435` -> child `#426`
- `#436` -> child `#427`
- `#437` -> child `#428`
- `#438` -> child `#429`
- `pending` -> child `#430` (this reconciliation PR)

## Prohibited Behaviors

- autonomous broad mutation
- bulk issue closure
- parent closeout before all children are closed/accounted for
- prior milestone mutation unless explicitly required
- nested markdown fences inside PowerShell here-string issue/comment bodies

## Validation Snapshot

- `git diff --check`
- `python -m pytest`
- `python -m aresforge inspect-repo-governance`
- `python -m aresforge inspect-milestone-state --parent-issue 421`
- `python -m aresforge check-milestone-evidence-readiness --parent-issue 421`
- `python -m aresforge inspect-parent-closeout-readiness --parent-issue 421`
- `python -m aresforge inspect-milestone-closeout-preflight --parent-issue 421`
- `python -m aresforge inspect-automatic-canonical-evidence-emission-contract`
- `python -m aresforge check-closeout-readiness-by-construction --parent-issue 421`

## Known Limitations

- No actual LLM invocation yet.
- No cloud LLM API integration yet.
- No GitHub sync execution yet.
- Hub now provides M40 local management/planning/reporting workflows; execution gates/auth/deployment hardening remain future work.
- No cross-machine coordination yet.
- No background daemon/scheduler yet.
