# AresForge Build State

## M44A Agent LLM Routing Strategy Documentation Update

Status: Completed locally on `main`.

Delivered:

- added future-state routing source of truth: `docs/architecture/AGENT_LLM_ROUTING_STRATEGY.md`
- documented project-specific AI routing modes, agent lanes, future engines, routing hierarchy, routing metadata, Codex CLI model strategy, and M43 prompt-pack relationship
- clarified that routing decisions should happen before prompt generation
- confirmed the queue should remain one canonical local queue with future routing metadata and filtered routed views/lanes

Boundaries:

- documentation-only milestone
- no backend routes, frontend settings UI, queue schema changes, runtime routing, Codex CLI execution, agent execution, local LLM execution, or model invocation
- no GitHub API, no `gh`, no GitHub issues/PRs/workflow activity, and no GitHub mutation from the app

Recommended next milestone:

- M45 - implement the next small local-first routing/prompt-pack preparation step only after preserving the M44A boundaries.

## M43 Agent Prompt Pack Generator

Status: Completed locally on `main`.

Delivered:

- added operator function `generate_local_queue_prompt_pack` in `src/aresforge/operator/local_project_queue.py`
- added Hub route `POST /api/local-queue/prompt-pack` for local-only prompt-pack generation
- added Queue UI panel controls/results for Agent Prompt Pack generation and copy/paste preview
- optional local artifact output is supported with safe non-overwrite behavior unless `force=true`

Boundaries:

- local-only, file-backed, operator-triggered prompt generation only
- generated packs are copy/paste-ready and manual-run only
- no queue auto-start or auto-complete behavior
- no Codex execution, no agent execution, no LLM/model routing
- no GitHub API, no `gh`, no GitHub mutation, no external service calls

## M42 Queue Item Detail Panel

Status: Completed locally on `main`.

Delivered:

- added a read-only Queue Item Detail Panel in Hub Queue section
- panel displays selected queue item details, source/context fields, and parsed M41 notes metadata
- panel attempts read-only readiness context load for selected item
- added explicit empty and error states for detail/readiness visibility

Boundaries:

- read-only/advisory detail panel
- no new lifecycle mutation behavior introduced by the panel
- no auto-start, no auto prompt generation
- no GitHub/`gh`/GitHub mutation behavior
- no agent/Codex/LLM execution behavior

## M41 Active Project Task Intake v2

Status: Completed locally on `main`.

Delivered:

- improved Active Project intake form with structured fields for local queue item quality
- intake now captures source, requested outcome, acceptance notes, and validation notes in addition to title/details/type/priority/tags
- retained `POST /api/local-queue/items` and extended optional payload handling without adding new routes
- persisted intake quality fields via existing local queue `source` and `notes` fields (file-backed, backward compatible)

Boundaries:

- local-only, operator-gated, file-backed queue creation only
- no auto-start and no auto prompt generation
- no GitHub/`gh`/GitHub mutation behavior
- no agent execution and no Codex/LLM execution behavior

## M40 Dashboard Milestone Closeout And Docs Reconciliation

Status: Completed locally on `main`.

Scope:

- documentation and validation baseline reconciliation only for dashboard milestones M35-M39
- no new dashboard runtime behavior, backend routes, or frontend interaction changes

Reconciled dashboard source-of-truth (M35-M39):

- M35: local operator summary contract in `src/aresforge/operator/local_dashboard_summary.py`
- M35: `GET /api/dashboard/summary` exposed through Hub API/server for read-only Home dashboard use
- M36: Home dashboard cards/status panels consume `GET /api/dashboard/summary`
- M37: manual refresh only plus loading/empty/error states and last-successful-load label
- M38: Home deep links into existing Workspace/Projects/Queue/Repos/Reports sections
- M39: queue status drilldowns and advisory agent lane drilldowns

Current frontend module structure (dashboard-related):

- entrypoint: `src/aresforge/hub/static/app.js`
- Home section: `src/aresforge/hub/static/js/sections/home.js`
- Queue section: `src/aresforge/hub/static/js/sections/queue.js`
- Projects section: `src/aresforge/hub/static/js/sections/projects.js`
- Repos section: `src/aresforge/hub/static/js/sections/repos.js`
- Reports section: `src/aresforge/hub/static/js/sections/reports.js`

Boundary posture (reconfirmed):

- local-only
- file-backed/local inspection
- operator-gated
- read-only/advisory dashboard posture
- no GitHub API calls
- no `gh` calls
- no GitHub issues/PRs/workflows mutation
- no real agent execution
- no Codex execution from the Hub app
- no LLM/model routing or invocation

Validation baseline for dashboard closeout:

- `python -m pytest tests/test_hub_ui_foundation.py tests/test_hub_dashboard_summary_api.py tests/test_local_dashboard_summary.py tests/test_hub_project_factory_api.py tests/test_hub_local_queue_lifecycle_api.py tests/test_hub_active_project_api.py tests/test_local_project_factory.py tests/test_local_active_project.py`
- smoke:
  - `python -m aresforge inspect-local-queue-agent-summary`
  - `python -m aresforge inspect-local-project-report`
- diff check:
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
## M36 Hub Dashboard UI Cards And Status Panels

Status: Completed locally on `main`.

Delivered:

- Home dashboard now consumes `GET /api/dashboard/summary`
- read-only cards/panels for project summary, queue summary, advisory agent lanes, repo summary, blockers/warnings, and next safe action
- manual operator refresh path retained; no polling/auto-refresh added

Boundary posture:

- local-only and read-only/advisory UI
- no GitHub API calls and no `gh` calls
- no agent/Codex/model execution
- no LLM/model routing

## M35 Hub Dashboard Data Contract And Read-Only Metrics

Status: Completed locally on `main`.

Delivered:

- local-only read-only Hub dashboard summary operator contract
- new Hub API route: `GET /api/dashboard/summary`
- stable JSON payload for Home dashboard data consumption in a future UI pass

Boundary posture:

- local-only and file-backed inspection
- read-only/advisory response
- no GitHub API calls
- no `gh` calls
- no network calls beyond existing local Hub API behavior
- no agent/Codex/model execution

Scope note:

- Home dashboard UI cards/panels are intentionally deferred to M36.

## Local LLM Planning Package (Documentation-Only)

Local LLM integration planning is now documented but not implemented.

Planning documents added:

- `docs/architecture/LOCAL_LLM_STRATEGY.md`
- `docs/operator/OLLAMA_LOCAL_SETUP.md`
- `docs/architecture/LLM_TASK_ROUTING_PLAN.md`
- `docs/context/LOCAL_LLM_DECISION_RECORD.md`

Current status:

- no live Ollama execution is wired into AresForge
- no agent workflow calls a local model
- no cloud LLM dependency has been introduced
- no network execution has been introduced
- no GitHub API usage has been introduced
- the documented baseline uses one local coding model and one local reasoning model, loaded separately
- future implementation must remain local-first and operator-gated

## M34 Frontend Modularization Closeout And Docs Reconciliation

Status: Completed locally on `main`.

Frontend module structure now finalized:

- entrypoint: `src/aresforge/hub/static/app.js` (ES module entrypoint loaded by `index.html`)
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

Validation status used for closeout:

- `python -m pytest tests/test_hub_ui_foundation.py tests/test_hub_project_factory_api.py tests/test_hub_local_queue_lifecycle_api.py tests/test_hub_active_project_api.py tests/test_local_project_factory.py tests/test_local_active_project.py`
- smoke:
  - `python -m aresforge inspect-local-queue-agent-summary`
  - `python -m aresforge inspect-local-project-report`

Boundary posture reconfirmed:

- local-first
- file-backed
- operator-gated
- no real agent execution
- no GitHub mutation
- no network execution beyond existing local Hub API behavior

Recommended next milestone after M34:

- M35 - Hub Dashboard Data Contract And Read-Only Metrics
- scope:
  - read-only Home dashboard metrics
  - total projects
  - active project summary
  - queue item counts by status
  - advisory agent lane counts from local summaries
  - repo status summary from existing local inspection outputs
  - no new GitHub calls
  - no real agent execution
  - no mutation

## M28 Hub Orchestration And Escalation Section Modules

Status: Completed locally on `main`.

Delivered M28 items:

- extracted Orchestration section logic into `src/aresforge/hub/static/js/sections/orchestration.js`
- extracted Escalation section logic into `src/aresforge/hub/static/js/sections/escalation.js`
- kept `src/aresforge/hub/static/app.js` as the frontend entrypoint and startup orchestrator
- moved Orchestration/Escalation rendering, plan loading, reset/submit bindings, and section-local helpers into the new modules
- preserved local-only/operator-gated messaging, DOM ids, and API endpoint paths
- updated static frontend tests to validate new section modules and import wiring

M28 boundary posture:

- local-only static/frontend refactor
- no GitHub API calls
- no `gh` calls
- no new network calls
- no agent execution
- no model routing/invocation
- no UI redesign, DOM id changes, or endpoint path changes

## M17 Local Queue Execution-Prep Lifecycle

Status: Completed locally on `main` (no push performed).

Delivered M17 local queue workflow:

- `python -m aresforge add-local-queue-item --title <title> ...`
- `python -m aresforge inspect-local-queue-item-readiness --item-id <item_id>`
- `python -m aresforge start-local-queue-item --item-id <item_id>`
- `python -m aresforge generate-local-queue-item-codex-prompt --item-id <item_id> [--output <path>]`
- human runs Codex manually using the generated prompt
- `python -m aresforge complete-local-queue-item --item-id <item_id> --commit-hash <hash> --validation-summary <text> ...`

M17 completion evidence recorded locally in `.aresforge/queue/work_items.json` includes:

- `completed_at`
- `completed_by`
- `completion_commit`
- `validation_summary`
- optional `evidence_note`, `tests_run`, `changed_files`, and `artifact_paths`

M17 boundary posture:

- local-first and file-backed
- no GitHub API calls
- no `gh` calls
- no GitHub mutation/sync execution
- no automatic Codex execution
- no agent execution
- no model routing/invocation
- no remote commit verification

## M27 Hub Reports Section Module

Status: Completed locally on `main`.

Delivered M27 items:

- extracted Reports section logic into `src/aresforge/hub/static/js/sections/reports.js`
- kept `src/aresforge/hub/static/app.js` as the browser entrypoint and startup orchestrator
- moved Reports dashboard rendering, local project report rendering, report slice loading, export helpers, and Reports-specific bindings into the new section module
- kept non-Reports orchestration and shared cross-section flows in `app.js` so this milestone stays limited to Reports UI ownership
- updated static frontend tests to validate the new Reports section module and single-path Reports bindings

M27 boundary posture:

- local-only static/frontend refactor
- no GitHub API calls
- no `gh` calls
- no new network calls
- no agent execution
- no model routing/invocation
- no UI redesign, DOM id changes, or endpoint path changes

## M26 Hub Projects And Repos Section Modules

Status: Completed locally on `main`.

Delivered M26 items:

- extracted Projects section logic into `src/aresforge/hub/static/js/sections/projects.js`
- extracted Repos section logic into `src/aresforge/hub/static/js/sections/repos.js`
- kept `src/aresforge/hub/static/app.js` as the browser entrypoint and startup orchestrator
- moved Projects list rendering, read-only rendering, selector refresh, and Projects-specific bindings into the Projects section module
- moved Repos list rendering, repo loading, repo inspection, and Repos-specific bindings into the Repos section module
- kept project-factory lifecycle orchestration in `app.js` so this milestone stays limited to Projects/Repos UI ownership
- updated static frontend tests to validate the new Projects/Repos section modules and single-path bindings

M26 boundary posture:

- local-only static/frontend refactor
- no GitHub API calls
- no `gh` calls
- no new network calls
- no agent execution
- no model routing/invocation
- no UI redesign, DOM id changes, or endpoint path changes

## M25 Hub Queue Section Module

Status: Completed locally on `main`.

Delivered M25 items:

- extracted Queue section logic into `src/aresforge/hub/static/js/sections/queue.js`
- kept `src/aresforge/hub/static/app.js` as the browser entrypoint and startup orchestrator
- moved queue read-only summary rendering/loading and queue item card rendering into the new section module
- moved queue-only actions into the new section module: apply active-project defaults, filter to active project, filter submit/reset, and queue form submit
- kept local queue lifecycle internals in `app.js` to avoid mixing higher-risk flow extraction into this milestone
- updated static frontend tests to validate the new queue section module and single-path queue bindings

M25 boundary posture:

- local-only static/frontend refactor
- no GitHub API calls
- no `gh` calls
- no new network calls
- no agent execution
- no model routing/invocation
- no UI redesign, DOM id changes, or endpoint path changes

## M24 Hub Home And Workspace Section Modules

Status: Completed locally on `main`.

Delivered M24 items:

- extracted Home section logic into `src/aresforge/hub/static/js/sections/home.js`
- extracted Workspace section logic into `src/aresforge/hub/static/js/sections/workspace.js`
- kept `src/aresforge/hub/static/app.js` as the browser entrypoint and startup orchestrator
- moved Home dashboard rendering/loading and Home-specific action binding behind module exports
- moved Workspace rendering/loading, empty-state rendering, and quick-action binding behind module exports
- updated static frontend tests to validate the new section modules, preserved entrypoint loading, and single-path workspace bindings

M24 boundary posture:

- local-only static/frontend refactor
- no GitHub API calls
- no `gh` calls
- no new network calls
- no agent execution
- no model routing/invocation
- no UI redesign, DOM id changes, or endpoint path changes

## M23 Hub Frontend Modularization Foundation

Status: Completed locally on `main`.

Delivered M23 items:

- switched Hub static loading from a plain script tag to browser-native ES module loading for `src/aresforge/hub/static/app.js`
- extracted shared frontend primitives into:
  - `src/aresforge/hub/static/js/core/dom.js`
  - `src/aresforge/hub/static/js/core/http.js`
  - `src/aresforge/hub/static/js/core/state.js`
- kept `app.js` as the main entrypoint/orchestrator for existing Hub domain logic
- removed the unused `renderRunningActionsAgentsPlaceholders` helper
- consolidated duplicated workspace quick-action binding so workspace buttons bind once
- updated static frontend tests to validate the module foundation without forcing all frontend strings to remain in `app.js`

M23 boundary posture:

- local-only static/frontend refactor
- no GitHub API calls
- no `gh` calls
- no new network calls
- no agent execution
- no model routing/invocation
- no UI redesign and no DOM id changes

## M16 Hub UI Foundations And Local Validation Closeout

Status: Completed locally on `main` (no push performed).

Delivered M16 items:

- Home dashboard API wiring (`/api/local-project-dashboard`, `/api/local-project-report`, `/api/local-projects`)
- Home dashboard read-only UI foundation
- Projects page read-only UI foundation
- Queue page read-only UI foundation (`/api/local-queue-agent-summary`)
- Reports page read-only UI foundation

Current boundary posture:

- local-first and local-only control-plane read/report surfaces
- no GitHub API calls
- no `gh` calls
- no GitHub mutation/sync execution
- no agent execution
- no model routing/invocation

Validation commands used for M16 closeout:

- `git diff --check`
- `python -m pytest tests/test_roadmap_db_control.py tests/test_config_and_migrations.py tests/test_cli.py`
- `python -m pytest tests/test_hub_project_factory_api.py tests/test_hub_active_project_api.py tests/test_hub_ui_foundation.py`
- `python -m pytest tests/test_local_project_dashboard.py tests/test_local_project_readiness.py tests/test_local_queue_agent_summary.py tests/test_local_project_report.py`
- `python -m pytest`
- smoke:
  - `python -m aresforge inspect-local-project-dashboard`
  - `python -m aresforge list-local-projects`
  - `python -m aresforge inspect-local-queue-agent-summary`
  - `python -m aresforge inspect-local-project-report`

## M14 Source-of-Truth Reconciliation Snapshot

- Operating mode for current local foundation work:
  - local-first
  - direct-on-`main`
  - read-only/report-planning emphasis for new dashboard/report surfaces
- Safety restrictions remain explicit:
  - no GitHub API calls
  - no `gh` calls
  - no GitHub issue/PR mutation from these local read-model/report commands
  - no agent execution
  - no LLM routing or invocation
  - no background scheduler/daemon behavior
- Historical milestone record:
  - M9 through M13 were completed, validated, committed, and pushed before this chat.
  - M14 local foundation additions are now present locally on `main` and validated in this chat.

M14 local read-model/report command additions now available:

- `python -m aresforge inspect-local-project-dashboard`
- `python -m aresforge list-local-projects`
- `python -m aresforge inspect-local-project-readiness --project-id <id>`
- `python -m aresforge inspect-local-queue-agent-summary`
- `python -m aresforge inspect-local-project-report`

Targeted validation bundle for this local foundation layer:

- `git diff --check`
- `python -m pytest tests/test_roadmap_db_control.py tests/test_config_and_migrations.py tests/test_cli.py`
- targeted local suites as needed:
  - `python -m pytest tests/test_local_project_dashboard.py`
  - `python -m pytest tests/test_local_project_readiness.py`
  - `python -m pytest tests/test_local_queue_agent_summary.py`
  - `python -m pytest tests/test_local_project_report.py`

## M7 Local Queue Transition Planning And Gated Queue Move

- Added local queue transition planning and gated queue move control:
  - `python -m aresforge plan-work-item-queue-transition --work-item-id <id> --target-queue-id <id> [--format json|markdown]`
  - `python -m aresforge move-work-item-queue --work-item-id <id> --target-queue-id <id> [--actor <actor>] [--details-file <path>] [--format json|markdown]`
- Planning remains read-only and deterministic.
- Queue move remains local-only, does not execute agents, and does not call GitHub.

## M8 Local Execution Dossier

- Added local read-only execution dossier packaging for one work item:
  - `python -m aresforge build-work-item-execution-dossier --work-item-id <id> [--format json|markdown]`
- The dossier packages readiness, lifecycle, queue context, roadmap links, dependencies, related events, and a suggested operator prompt.
- M8 remains local-only and read-only. It does not execute agents, mutate GitHub, or implement Hub UI.

## M9 Local Implementation Handoff Command

- Added a local implementation handoff command:
  - `python -m aresforge handoff-work-item-to-implementation --work-item-id <id> [--actor <actor>] [--details-file <path>] [--format json|markdown]`
- The command reuses queue transition gates and returns a post-move execution dossier for the updated state.
- M9 remains local-only and does not execute agents, call GitHub, or implement Hub UI.

## M10 Local Project/Queue Dashboard CLI

- Added a read-only local dashboard command:
  - `python -m aresforge inspect-project-queue-dashboard [--project-id <id>] [--format json|markdown]`
- The dashboard summarizes work item totals, queue state, readiness state, roadmap state, recent events, and next safe actions.
- M10 does not implement Hub UI, execute agents, or call GitHub.

## M11 Local Roadmap Dependency Management

- Added local roadmap dependency management commands:
  - `python -m aresforge add-roadmap-task-dependency --task-id <id> --depends-on-task-id <id> [--dependency-type blocks] [--actor <actor>] [--details-file <path>] [--format json|markdown]`
  - `python -m aresforge remove-roadmap-task-dependency --task-id <id> --depends-on-task-id <id> [--actor <actor>] [--details-file <path>] [--format json|markdown]`
  - `python -m aresforge inspect-roadmap-task-dependencies [--task-id <id>] [--project-id <id>] [--format json|markdown]`
- Dependencies can now be added, inspected, and removed locally.
- Readiness gates can use these dependencies to explain blockers.
- M11 includes no GitHub calls, no agent execution, and no Hub UI.

## M12 Local Operator Prompt Export

- Added local export of execution dossier suggested operator prompts:
  - `python -m aresforge export-work-item-operator-prompt --work-item-id <id> --output <path> [--force] [--format json|markdown]`
- Export writes a UTF-8 prompt file for human handoff.
- M12 does not execute agents, call GitHub, or implement Hub UI.

## M46 Project Factory Source-of-Truth Realignment

Current state on `main` includes M43-M45 and establishes a local-first Hub control plane plus a partial project-factory shell:

- managed project/repo registry
- active project selection and context
- active project dashboard/workbench
- active project intake into local queue
- local queue, agent profile, orchestration planning, escalation planning, handoff, and local closeout tooling
- explicit planning boundaries for later GitHub sync/mutation

Important: the full end-to-end project factory loop is not yet complete. Missing pieces still include new-project wizarding, repo create/link apply flow, scope+architecture contract flow, milestone/issue generation from scope, explicit GitHub issue/milestone apply, and agent run execution lifecycle.

Canonical workflow source-of-truth:

- `docs/architecture/PROJECT_FACTORY_WORKFLOW.md`

Next milestone after this M46 realignment:

- M47 New Project Wizard

## Current Phase

M42 first-run bootstrap and seed wizard for local AresForge Hub setup.

## Current Goal

Implement and document M42 so the Hub can inspect local setup readiness, generate a plan-only bootstrap preview, and apply local file-backed bootstrap seeding for first-run operator workflows.

## M42 First-Run Bootstrap And Seed Wizard (Local-Only)

- Added local bootstrap operator module:
  - `src/aresforge/operator/local_bootstrap_wizard.py`
- Added local bootstrap CLI commands:
  - `python -m aresforge inspect-bootstrap-status [--repo-path <path>]`
  - `python -m aresforge plan-bootstrap [--repo-path <path>] [--format json|markdown] [--seed-sample-work]`
  - `python -m aresforge apply-bootstrap [--repo-path <path>] [--force] [--seed-sample-work] [--format json|markdown]`
- Added local Hub bootstrap API endpoints:
  - `GET /api/bootstrap/status`
  - `GET /api/bootstrap/plan`
  - `POST /api/bootstrap/apply`
- Added Hub Bootstrap setup section for status, plan preview, force/sample toggles, and apply actions.
- Bootstrap initializes missing local state files under `.aresforge/`:
  - `.aresforge/state/project_state.json`
  - `.aresforge/projects/projects.json`
  - `.aresforge/queue/work_items.json`
  - `.aresforge/agents/agents.json`
- Bootstrap registers AresForge as a managed project/repo with local GitHub metadata.
- Bootstrap seeds default agent profiles/handoff targets and optional sample next-phase queue milestones.

M42 safety posture:

- local-only and file-backed
- no GitHub API calls
- no `gh` calls
- no GraphQL/REST calls
- no network service calls
- no live GitHub validation/discovery
- no local/cloud/Codex/ChatGPT/Ollama model invocation

## M21 Active Project Workspace (Polish & Local-Only)

Status: Completed locally on `main` and reconciled with tests and UI foundations.

Delivered M21 items:

- Polished the Active Project Workspace UI in the Hub with clearer operator-first guidance and empty states.
- Added explicit local-only messaging on quick actions and workspace cards (labels now include "(local-only)").
- Wired workspace quick actions in `app.js` to navigate/focus operator flows (refresh, continue intake, open queue, select project).
- Hardened tests with `tests/test_active_project_workspace.py` to validate the `get_active_project_workspace` payload for empty and seeded states.

Validation and boundary posture:

- Local-first and operator-driven only: all UI and API surfaces are read/report and plan-only.
- No GitHub API calls, no `gh` calls, no agent/model/Codex execution, no network mutation.
- Tests added and validated locally; full test run reported passing (207 passed, 1 warning) during local validation.

## M41 GitHub-Linked Project/Repo Model (Local-Only)

- Extended local managed project/repo registry schema for GitHub identity fields.
- Projects now track local GitHub linkage metadata:
  - `primary_repo_id`
  - `github_owner`
  - `github_repo`
  - `github_url`
  - `github_default_branch`
  - `github_connection_status`
- Repos now track local GitHub and local git inspection metadata:
  - `github_owner`
  - `github_repo`
  - `github_url`
  - `github_default_branch`
  - `github_connection_status`
  - `local_git_branch`
  - `local_git_head`
  - `local_git_remote_url`
  - `local_git_status_summary`
- GitHub identity rules now support:
  - owner/repo/url local storage
  - URL parsing for GitHub HTTPS and SSH remote formats
  - URL generation from owner/repo when URL is omitted
  - project-level identity derivation from primary repo when needed
  - project primary repo linkage enforcement when repos exist
- Added local-only git inspection support (no network):
  - `git -C <path> remote get-url origin`
  - `git -C <path> branch --show-current`
  - `git -C <path> rev-parse HEAD`
  - `git -C <path> status --short`
- Added CLI command:
  - `python -m aresforge inspect-managed-repo-github-link --project-id <id> --repo-id <id> [--registry-path <path>] [--inspect-local-git] [--format json|markdown]`
- Extended Hub API and UI with M41 GitHub-linked surfaces:
  - project/repo forms include GitHub metadata
  - repo-local action for local git link inspection
  - report/home/settings include GitHub linkage readiness summaries and boundary notes

M41 safety posture:

- local-only metadata management and inspection
- no GitHub API calls
- no `gh` calls
- no GraphQL or REST calls
- no network service calls
- no live GitHub validation
- no local/cloud/Codex/ChatGPT/Ollama invocation

Future (not implemented in M41):

- explicitly gated GitHub sync/validation execution under additional safeguards and approvals

## M40 Reporting, Dashboard Polish, And Operator Workflows

- Extended local Hub API with local-only report endpoints:
  - `GET /api/reports/dashboard`
  - `GET /api/reports/action-center`
  - `GET /api/reports/readiness`
  - `GET /api/reports/operator-workflows`
  - `GET /api/reports/export`
- Expanded local dashboard helper (`src/aresforge/operator/local_project_dashboard.py`) to emit a stable report schema including:
  - project/repo/queue/agent/handoff/orchestration/escalation/docs summaries
  - readiness indicators
  - action center
  - risks, warnings, recommended next actions
  - operator workflow cards
  - explicit boundary confirmations
- Hub Home now acts as a polished operator dashboard:
  - top-level status cards
  - readiness indicators
  - action-center preview
  - recommended next actions
  - quick workflow cards
- Hub Reports now provides control-plane report sections and in-page export/copy actions.
- Hub Settings now shows default local paths, artifact folders, boundary confirmations, known limitations, and next milestone scope.
- M40 remains local-only and workflow/report oriented:
  - no agent execution
  - no local LLM invocation
  - no cloud LLM invocation
  - no Codex invocation
  - no ChatGPT invocation
  - no Ollama invocation
  - no GitHub calls
  - no `gh` calls
  - no network/external API calls
  - no live GitHub sync
  - no authentication or production deployment implementation
- Future work after M40:
  - richer guided UI workflows
  - optional execution gates with explicit operator approval
  - authentication if exposed beyond localhost
  - controlled GitHub sync execution behind safeguards
  - optional LLM execution behind explicit user-approved gates

## M39 Agent, Handoff, Orchestration, And Escalation Hub Screens

- Extended local Hub API with local-only M39 endpoints:
  - `GET /api/agents`
  - `POST /api/agents`
  - `GET /api/agents/{agent_id}`
  - `GET /api/handoff-targets`
  - `POST /api/handoff-targets`
  - `GET /api/handoff-targets/{target_id}`
  - `GET /api/handoff/preview`
  - `POST /api/orchestration/plan`
  - `GET /api/orchestration/plan`
  - `POST /api/escalation/plan`
  - `GET /api/escalation/plan`
- Extended Hub frontend with interactive sections:
  - Agents list and add/update form
  - Handoff targets list and add/update form
  - Handoff preview refresh and local-only preview panel
  - Orchestration filter controls and plan visualization
  - Escalation filter controls and classification visualization
- M39 data model linkage:
  - agent and handoff target operations reuse M34 local profiles storage
  - orchestration plan responses reuse M35 plan-only orchestration logic
  - escalation plan responses reuse M36 plan-only escalation logic
  - handoff preview reuses M26 local handoff package logic without posting anywhere
- M39 boundary confirmations:
  - local-only
  - file-backed
  - plan-only for orchestration and escalation
  - no agent execution
  - no local LLM calls
  - no cloud LLM calls
  - no Codex execution
  - no ChatGPT calls
  - no Ollama calls
  - no `gh`
  - no GitHub API calls
  - no network service calls
  - no external API calls
- M39 scope boundary:
  - reporting/dashboard polish and expanded operator workflows remain planned for M40
  - authentication and production deployment remain unimplemented
  - live GitHub sync remains unimplemented

## M38 Hub Project, Repo, And Queue Management

- Extended local Hub API with local-only management endpoints:
  - `GET /api/projects`
  - `POST /api/projects`
  - `GET /api/projects/{project_id}`
  - `GET /api/projects/{project_id}/repos`
  - `POST /api/projects/{project_id}/repos`
  - `GET /api/queue`
  - `POST /api/queue`
  - `GET /api/queue/{item_id}`
  - `PATCH /api/queue/{item_id}`
  - `GET /api/settings`
- Extended Hub frontend with interactive sections:
  - Projects list and add/update project form
  - Repos project selector, repo list, and add/update repo form
  - Queue filters, item list/cards, add/update item form, and quick status update controls
  - Home readiness hints for project/repo/queue management
  - Settings storage-path display for local registry and queue files
- M38 data model linkage:
  - project/repo operations reuse M32 managed-project registry storage
  - queue operations reuse M33 local project queue storage
  - create/update behavior is idempotent where operator contracts already support idempotent registration/update
- M38 local-first/file-backed boundary:
  - no `gh`
  - no GitHub API calls
  - no network service calls
  - no local LLM calls
  - no cloud LLM calls
  - no Codex calls
  - no ChatGPT calls
  - no Ollama calls
  - no external API calls
- M38 scope boundary:
  - agent, handoff, orchestration, and escalation screens remain planned for M39
  - reporting/dashboard polish and operator workflow expansion remain planned for M40
  - authentication and production deployment remain unimplemented
  - live GitHub sync and agent/LLM execution remain unimplemented

## M37 AresForge Hub UI Foundation

- Added local Hub package:
  - `src/aresforge/hub/`
  - `src/aresforge/hub/api.py`
  - `src/aresforge/hub/server.py`
  - `src/aresforge/hub/static/index.html`
  - `src/aresforge/hub/static/app.js`
  - `src/aresforge/hub/static/styles.css`
- Added local Hub command:
  - `python -m aresforge serve-hub [--host <host>] [--port <port>] [--open-browser]`
- Default Hub host/port behavior:
  - host defaults to `127.0.0.1`
  - port defaults to `8765`
  - browser auto-open is off by default and only opens localhost when `--open-browser` is supplied
- Added local API shell endpoints:
  - `GET /api/health`
  - `GET /api/summary`
  - `GET /api/docs/status`
- Added local dashboard helper:
  - `src/aresforge/operator/local_project_dashboard.py`
- M37 Hub scope:
  - server + API shell + static frontend shell
  - persistent navigation (Home/Projects/Repos/Queue/Agents/Handoff/Orchestration/Escalation/Reports/Settings)
  - Home summary cards and warnings/actions using local files where available
  - docs status endpoint and Settings boundary confirmations
  - placeholder sections for M38-M40 surfaces
- M37 safety posture:
  - local-first and local-only serving path
  - binds to `127.0.0.1` by default
  - no `gh`
  - no GitHub API calls
  - no network service calls
  - no local LLM calls
  - no cloud LLM calls
  - no Codex calls
  - no ChatGPT calls
  - no Ollama calls
  - no external API calls
  - no agent execution
  - no live GitHub sync
  - no authentication implementation yet
  - no production deployment implementation yet

## M36 Cloud LLM Escalation Planner

- Added local escalation planner command:
  - `python -m aresforge plan-llm-escalation [--item-id <id>] [--project-id <id>] [--repo-id <id>] [--status <status>] [--queue-path <path>] [--profiles-path <path>] [--orchestration-plan <path>] [--output <path>] [--format json|markdown] [--force]`
- Added local escalation planner module:
  - `src/aresforge/operator/local_llm_escalation.py`
- Default escalation artifact folder:
  - `artifacts/escalation/`
- Planner reads local inputs where available:
  - M33 queue file (`.aresforge/queue/work_items.json` by default)
  - M34 profiles file (`.aresforge/agents/agents.json` by default)
  - optional M35 orchestration plan file when supplied via `--orchestration-plan`
- Missing files are warning-only and produce reduced output rather than hard failure.
- Plan output includes:
  - selected work items and available agents
  - per-item classification and reasons
  - category buckets: `local_llm_suitable`, `codex_suitable`, `cloud_llm_recommended`, `human_required`, `blocked_or_needs_clarification`
  - recommended handoff targets and copy/paste prompt guidance
  - risk warnings, next actions, and explicit boundary confirmations
- M26 handoff linkage:
  - handoff package includes latest escalation artifact when found under `artifacts/escalation/`
  - otherwise includes an escalation capability note
- M36 safety posture:
  - local-only escalation planning
  - plan-only
  - cloud escalation is advisory only
  - no LLM invocation
  - no local LLM calls
  - no cloud LLM calls
  - no Codex execution
  - no ChatGPT calls
  - no GitHub calls
  - no `gh` calls
  - no network calls

## M35 Multi-Agent Orchestration Planner

- Added local orchestration planner command:
  - `python -m aresforge plan-agent-orchestration [--project-id <id>] [--repo-id <id>] [--status <status>] [--queue-path <path>] [--profiles-path <path>] [--registry-path <path>] [--output <path>] [--format json|markdown] [--force]`
- Added local orchestration planner module:
  - `src/aresforge/operator/local_agent_orchestration.py`
- Default orchestration artifact folder:
  - `artifacts/orchestration/`
- Planner reads local inputs where available:
  - M33 queue file (`.aresforge/queue/work_items.json` by default)
  - M34 profiles file (`.aresforge/agents/agents.json` by default)
  - M32 registry file (`.aresforge/projects/projects.json` by default)
- Missing files are warning-only and produce reduced plans rather than hard failures.
- Plan includes:
  - selected work items
  - available agents
  - recommended assignments
  - dependency ordering
  - blocked/unassigned items
  - handoff prompts
  - risk warnings
  - next actions
  - explicit boundary confirmations
- Assignment behavior:
  - preserves queue `assigned_agent` when present in profiles
  - warns and leaves unassigned when `assigned_agent` is missing from profiles
  - recommends by `item_type`, role preference, and `allowed_item_types`
- Dependency behavior:
  - respects `dependencies` order
  - detects unresolved `blocked_by` blockers
  - reports circular dependency risks without crashing
- M26 handoff linkage:
  - handoff package includes latest orchestration artifact when found under `artifacts/orchestration/`
  - otherwise includes an orchestration capability note
- M35 safety posture:
  - local-only orchestration planning
  - plan-only
  - no agent execution
  - no local LLM invocation
  - no cloud LLM invocation
  - no `gh`
  - no GitHub API calls
  - no network access

## M34 Local LLM Agent Profiles And Handoff Targets

- Added local agent profile defaults under `.aresforge/agents/agents.json`.
- Agent profiles schema stores `schema_version`, `updated_at`, `agents`, and `handoff_targets`.
- Agent profile records support role, execution mode, strengths/constraints, allowed item types, escalation metadata, status, tags, notes, and timestamps.
- Handoff target records support descriptive target type metadata, local command placeholder fields, input/output formats, safety notes, status, tags, notes, and timestamps.
- New local-only command surface:
  - `python -m aresforge init-agent-profiles [--path <path>] [--force] [--with-defaults]`
  - `python -m aresforge register-agent-profile --agent-id <id> --name <name> --role <role> [--profiles-path <path>] [--description <text>] [--execution-mode <mode>] [--model-preference <value>] [--strength <text>]... [--constraint <text>]... [--allowed-type <type>]... [--escalation-allowed true|false] [--handoff-target-id <id>] [--status <status>] [--tag <tag>]... [--notes <text>]`
  - `python -m aresforge register-handoff-target --target-id <id> --name <name> --target-type <type> [--profiles-path <path>] [--description <text>] [--local-command <command>] [--input-format <format>] [--output-format <format>] [--safety-note <text>]... [--status <status>] [--tag <tag>]... [--notes <text>]`
  - `python -m aresforge inspect-agent-profiles [--profiles-path <path>] [--role <role>] [--execution-mode <mode>] [--status <status>] [--format json|markdown]`
  - `python -m aresforge inspect-agent-profile --agent-id <id> [--profiles-path <path>] [--format json|markdown]`
  - `python -m aresforge inspect-handoff-target --target-id <id> [--profiles-path <path>] [--format json|markdown]`
- `init-agent-profiles --with-defaults` seeds generic local-first defaults for architect, implementer, tester, documentation, reviewer, operator, local-llm-general, and cloud-escalation profiles.
- Agent profile registration is idempotent by `agent_id`; handoff target registration is idempotent by `target_id`.
- Agent registration allows unresolved `handoff_target_id` values and returns warning-only guidance for future linkage.
- M26 handoff generation now includes local agent profile summary when profiles exist.
- M35 orchestration planning consumes M34 agent profiles and handoff-target metadata for assignment and handoff prompt generation.
- M34 safety posture:
  - local-only configuration and planning surface
  - no `gh`
  - no GitHub API calls
  - no network access
  - no local LLM invocation
  - no cloud LLM invocation
  - no agent execution/orchestration in this milestone

## M33 Local Project Queue And Work Tracking

- Added a local project queue under `.aresforge/queue/work_items.json`.
- Queue schema stores `schema_version`, `updated_at`, and `work_items`.
- Work items support local planning fields for cross-project tracking, including `project_id`, `repo_id`, dependency links, and `assigned_agent`.
- New local-only command surface:
  - `python -m aresforge init-project-queue [--path <path>] [--force]`
  - `python -m aresforge add-queue-item --item-id <id> --project-id <id> --repo-id <id> --title <title> [--queue-path <path>] [--registry-path <path>] [--description <text>] [--status <status>] [--priority <priority>] [--type <type>] [--tag <tag>]... [--depends-on <item_id>]... [--blocked-by <item_id>]... [--assigned-agent <agent_id>] [--source <source>] [--notes <text>]`
  - `python -m aresforge update-queue-item --item-id <id> [--queue-path <path>] [--project-id <id>] [--repo-id <id>] [--status <status>] [--priority <priority>] [--type <type>] [--title <title>] [--description <text>] [--tag <tag>]... [--depends-on <item_id>]... [--blocked-by <item_id>]... [--assigned-agent <agent_id>] [--source <source>] [--notes <text>]`
  - `python -m aresforge inspect-project-queue [--queue-path <path>] [--project-id <id>] [--repo-id <id>] [--status <status>] [--type <type>] [--assigned-agent <agent_id>] [--format json|markdown]`
  - `python -m aresforge inspect-queue-item --item-id <id> [--queue-path <path>] [--format json|markdown]`
- M33 local validation behavior:
  - optional M32 registry validation for `project_id` + `repo_id` bindings
  - missing dependency references are saved with warnings for future linkage
  - queue remains local-only and does not call GitHub APIs, `gh`, network services, or LLM services
- M26 handoff generation now includes local project queue summary when queue exists.
- `assigned_agent` is stored for future orchestration and does not execute agents in M33.
- `assigned_agent` can now reference an M34 `agent_id` from local agent profiles.
- M35 orchestration planning consumes queue `assigned_agent`, `dependencies`, and `blocked_by` fields for plan-only assignment and sequencing.

## M32 Multi-Project / Multi-Repo Local Registry

- Added a local managed-project registry under `.aresforge/projects/projects.json`.
- Registry tracks multiple projects and multiple repos with explicit status, role, metadata, and timestamps.
- New local-only command surface:
  - `python -m aresforge init-managed-project-registry [--path <path>] [--force]`
  - `python -m aresforge register-managed-project --project-id <id> --name <name> --root-path <path> [--registry-path <path>] [--description <text>] [--status <status>] [--default-branch <branch>] [--tag <tag>]... [--notes <text>]`
  - `python -m aresforge register-managed-repo --project-id <id> --repo-id <id> --name <name> --path <path> [--registry-path <path>] [--remote-url <url>] [--default-branch <branch>] [--role <role>] [--status <status>] [--tag <tag>]... [--notes <text>]`
  - `python -m aresforge inspect-managed-project-registry [--registry-path <path>] [--format json|markdown]`
  - `python -m aresforge inspect-managed-project --project-id <id> [--registry-path <path>] [--format json|markdown]`
  - `python -m aresforge inspect-managed-repo --project-id <id> --repo-id <id> [--registry-path <path>] [--format json|markdown]`
- M26 handoff generation now includes managed-project registry summary when the registry exists.
- M33 queue item registration now uses this registry for local `project_id` / `repo_id` validation when available.
- M32 boundary confirmation:
  - local-only
  - no `gh`
  - no GitHub API calls
  - no network access
## M31 Foundation Reconciliation and Next-Phase Planning

- AresForge now has a local-first foundation for self-managed operation.
- GitHub is optional/syncable and not mandatory for local planning.
- M26 added local handoff package generation.
- M27 added the local project state ledger.
- M28 added plan-only documentation reconciliation.
- M29 added plan-only offline-to-GitHub sync planning.
- M30 added local self-managed milestone lifecycle support.
- No new functionality in this foundation batch calls GitHub APIs.
- No new functionality in this foundation batch calls LLM APIs.
- The system is ready to move into multi-project and multi-agent project-management capabilities.

## Next-Phase Roadmap (Planned)

- M38: project/repo/queue management screens and workflows.
- M39: agent/orchestration/escalation/handoff screens.
- M40: reporting/dashboard polish and operator workflows.

## Known Limitations (Current Foundation Batch)

- No actual LLM invocation yet.
- No cloud LLM API integration yet.
- No GitHub sync execution yet.
- Hub UI is a foundation shell only; full CRUD management screens are deferred to M38.
- Full agent/orchestration/escalation/handoff screens are deferred to M39.
- Full reporting and dashboard polish are deferred to M40.
- No cross-machine coordination yet.
- No background daemon/scheduler yet.

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
- Later milestones can be associated with managed `project_id` and `repo_id` from the M32 registry.

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
- Scope clarification:
  - M27 local project state tracks the current repo/session context.
  - M32 managed-project registry tracks many projects and repos in local-first control-plane context.
  - M33 local project queue tracks local work progression across project/repo inventory.

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
