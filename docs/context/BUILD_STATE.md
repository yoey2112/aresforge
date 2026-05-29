# AresForge Build State

## M68 Local AI Operations Closeout Reconciliation

Status: Completed locally on `main`.

Reconciled implemented local AI operations baseline:

- Project AI settings contract and UI
- Agent/engine registry
- Queue routing metadata
- Routing decision matrix v1
- Routed queue views as filtered views over the canonical local queue
- Routing-aware prompt packs
- Local LLM environment contract
- Local LLM health check
- Codex CLI model profile contract
- Local LLM prompt preview
- Operator-gated local LLM execution prototype
- Codex CLI high-value prompt lane
- Execution audit log
- AI action safety gate
- AI artifact registry
- Operator run history panel

Current hard boundaries:

- no GitHub API, `gh`, GitHub issues, GitHub PRs, GitHub workflows, or GitHub mutation from the app
- no automatic Codex execution and no Codex CLI execution
- no automatic agent execution
- Codex high-value lane is prompt generation and operator handoff only
- local LLM execution is prototype-only, local-only, advisory-only, and operator-gated
- local LLM output is not applied to repository files automatically
- one canonical local queue remains the source of truth
- routed views are filtered views, not separate queues

Recommended next milestone:

- M69 - Local AI Operations Hardening.

## M67 Operator Run History Panel

Status: Completed locally on `main`.

Delivered:

- added `read_operator_run_history(...)` to combine execution audit entries and AI artifact registry records
- added read-only Hub route `GET /api/operator-run-history`
- added a read-only Queue UI Operator Run History panel with simple filters
- timeline shows audit and artifact entries newest first with action type, artifact type, outcome, summary, artifact path, execution state, and permission state
- supports filters for project id, item id, action type, artifact type, and limit

Boundaries:

- run history is read-only
- no execution controls, apply controls, GitHub buttons, or Codex run buttons
- no Codex CLI execution
- no GitHub API, `gh`, issues, PRs, workflow activity, or GitHub mutation
- no local LLM execution expansion beyond M62

Recommended next milestone:

- M68 - Local AI Operations Closeout Reconciliation.

## M66 AI Artifact Registry

Status: Completed locally on `main`.

Delivered:

- added local file-backed AI artifact registry helpers: `register_ai_artifact(...)`, `read_ai_artifact_registry(...)`, `filter_ai_artifacts(...)`, and `verify_ai_artifact_exists(...)`
- stores artifact records at `.aresforge/ai_artifact_registry.json`
- added read-only Hub route `GET /api/ai-artifacts`
- added a small read-only Queue UI AI Artifact Registry panel with simple filters
- registers successful local artifact writes for prompt packs, local LLM prompt previews, local LLM advisory execution results, Codex high-value prompts, and local project handoffs
- tracks artifact type, source action, local path, project/item ids when available, engine/model/lane metadata, checksum, existence state, warnings, and summary

Boundaries:

- artifact registry does not execute anything
- registry entries do not overwrite artifact content
- no Codex CLI execution
- no GitHub API, `gh`, issues, PRs, workflow activity, or GitHub mutation
- no local LLM execution expansion beyond M62

Recommended next milestone:

- M67 - Operator Run History Panel.

## M65 AI Action Safety Gate

Status: Completed locally on `main`.

Delivered:

- added `evaluate_ai_action_safety_gate(...)` as local-only decision/reporting logic
- added Hub route `POST /api/ai-action-safety-gate` for previewing gate decisions
- integrated safety gate decisions into M62 local LLM execution and M63 Codex high-value prompt generation
- centralized decision values: `allowed`, `blocked`, `warning`, `requires_operator_gate`, `requires_operator_override`, and `preview_only`
- supports local LLM preview/execution, Codex high-value prompt generation, prompt-pack generation, routing recommendation, and routing metadata update actions
- reports required operator gate/override state, execution permission, blockers, warnings, and next safe action

Boundaries:

- safety gate is decision/reporting logic only
- no new execution behavior
- no Codex CLI execution
- no GitHub API, `gh`, issues, PRs, workflow activity, or GitHub mutation
- no local LLM execution expansion beyond M62

Recommended next milestone:

- M66 - AI Artifact Registry.

## M64 Execution Audit Log

Status: Completed locally on `main`.

Delivered:

- added local file-backed execution audit helpers: `append_execution_audit_entry(...)`, `read_execution_audit_log(...)`, and `filter_execution_audit_log(...)`
- stores audit entries at `.aresforge/execution_audit_log.json`
- added audit logging for local LLM health checks, local LLM prompt previews, local LLM execution/dry runs/blocked attempts, Codex high-value prompt generation, prompt-pack generation, and routing metadata updates
- added read-only Hub route `GET /api/execution-audit-log`
- added a small read-only Queue UI Execution Audit Log panel with simple filters
- audit entries record action metadata, outcomes, blockers/warnings, artifact path, summary, source function, and whether anything executed
- audit entries avoid full prompt/response text and redact secret-like strings

Boundaries:

- audit logging does not execute anything
- no Codex CLI execution
- no GitHub API, `gh`, issues, PRs, workflow activity, or GitHub mutation
- no local LLM execution expansion beyond M62
- audit write failures are best-effort warnings and do not widen execution behavior

Recommended next milestone:

- M65 - AI Action Safety Gate.

## M63 Codex CLI High-Value Lane

Status: Completed locally on `main`.

Delivered:

- added `generate_codex_high_value_lane_prompt(...)` for conservative Codex-ready prompt generation
- added Hub route `POST /api/local-queue/items/{item_id}/codex-high-value-prompt`
- added Queue UI controls for Generate Codex High-Value Prompt with copy/paste preview output
- supports optional local prompt artifact output with safe non-overwrite behavior unless `force=true`
- uses the canonical local queue and routing metadata as the source of truth
- marks items Codex-worthy for `codex_cli`, `high_value_codex`, high/critical risk, high complexity, high-value affected areas, high validation burden, `codex_only`/`high_confidence`, or operator override
- returns `execution_allowed: false` and advisory `prompt_preview` only

Boundaries:

- no automatic Codex execution
- no Codex CLI command execution from the app
- no GitHub API, `gh`, issues, PRs, workflow activity, or GitHub mutation
- no repository mutation from Codex output
- local LLM execution from M62 remains operator-gated and unchanged
- generated Codex prompts must be manually copied by the operator and validated locally before commit/push

Recommended next milestone:

- M64 - Execution Audit Log.

## M62 Operator-Gated Local LLM Execution Prototype

Status: Completed locally on `main`.

Delivered:

- added `execute_local_llm_for_queue_item(...)` as a conservative local LLM execution prototype
- added Hub route `POST /api/local-queue/items/{item_id}/local-llm-execute`
- added Queue UI controls for explicit prototype execution and dry run
- allows the local LLM environment contract to set `execution_enabled: true` for prototype mode while keeping `operator_gate_required: true`
- requires local-routed queue metadata, prompt preview, local `ollama` provider configuration, reachable health check for real execution, explicit operator confirmation, and local model availability
- blocks `codex_cli` routes, unrouted items, missing confirmation, non-local provider URLs, disabled execution, unavailable health checks, and high/critical risk without operator override
- captures advisory response text in the response payload and optional local result artifact

Boundaries:

- explicit operator action only
- local provider only
- no Codex CLI execution
- no GitHub API, `gh`, issues, PRs, workflow activity, or GitHub mutation
- no automatic agent execution
- no automatic queue start, completion, closeout, commit, push, or repo file mutation
- local LLM output is advisory only

Recommended next milestone:

- M63 - Codex CLI High-Value Lane.

## M61 Local LLM Prompt Preview

Status: Completed locally on `main`.

Delivered:

- added `generate_local_llm_prompt_preview(...)` for copy/paste local LLM prompt previews
- added Hub route `POST /api/local-queue/items/{item_id}/local-llm-prompt-preview`
- added Queue UI controls for generating and viewing a local LLM prompt preview
- supports optional safe artifact output with non-overwrite behavior unless `force=true`
- preview is allowed only for routed queue items recommending `local_reasoning_llm` or `local_coding_llm`
- blocks or warns for unrouted items, `codex_cli` routes, missing local LLM environment/model configuration, and `manual_only` policy without operator override
- preview output includes task details, project context, routing metadata, local-only rules, validation expectations, final response format, and `execution_allowed: false`

Boundaries:

- preview only
- no Ollama call
- no local LLM inference or generation
- no prompt execution
- no Codex CLI execution
- no agent execution
- no GitHub API, `gh`, issues, PRs, workflow activity, or GitHub mutation
- no queue mutation unless the operator explicitly writes a local preview artifact

Follow-up:

- M62 added Operator-Gated Local LLM Execution Prototype.

## M60 Codex CLI Model Profile Contract

Status: Completed locally on `main`.

Delivered:

- added local-only Codex CLI Model Profile Contract at `.aresforge/codex_cli_model_profiles.json`
- added read/update/validation helpers for Codex CLI model profile configuration
- added Hub routes `GET /api/codex-cli/model-profiles` and `POST /api/codex-cli/model-profiles`
- represented `codex_cli` as the fixed Codex engine key
- represented default, high-value, and fast Codex model preferences
- added allowed model lists plus optional per-project and per-agent model restrictions
- enforces `execution_enabled: false` for Codex CLI model profiles while `operator_gate_required` stays true
- added detailed source doc `docs/architecture/CODEX_CLI_MODEL_PROFILE_CONTRACT.md`

Boundaries:

- configuration only
- no Codex CLI execution
- no prompt execution
- no agent execution
- no GitHub API, `gh`, issues, PRs, workflow activity, or GitHub mutation
- no external workflow execution
- no High-Value Codex Lane execution yet

Recommended next milestone:

- M63 - Codex CLI High-Value Lane.

## M59 Local LLM Health Check

Status: Completed locally on `main`.

Delivered:

- added explicitly invoked `check_local_llm_health(...)`
- added Hub route `POST /api/local-llm/health-check`
- reads the M58 Local LLM Environment Contract
- for provider `ollama`, checks only the local `/api/tags` model-list endpoint when explicitly invoked
- reports provider reachability, available model names, configured reasoning/coding model availability, `inference_tested: false`, and `execution_allowed: false`
- rejects non-local provider URLs and prompt/execution payload fields

Boundaries:

- local-only and operator-invoked
- no prompt execution
- no model inference
- no local LLM generation
- no Codex execution
- no agent execution
- no GitHub/`gh`
- no generate/chat/completion endpoint calls
- no queue/project mutation

Follow-up:

- M61 added Local LLM Prompt Preview.
- M62 added Operator-Gated Local LLM Execution Prototype.

## M58 Local LLM Environment Contract

Status: Completed locally on `main`.

Delivered:

- added local-only Local LLM Environment Contract at `.aresforge/local_llm_environment.json`
- added read/update/validation helpers for local LLM environment configuration
- added Hub routes `GET /api/local-llm/environment` and `POST /api/local-llm/environment`
- supported providers: `ollama`, `none`, and `unknown`
- represented provider URL, reasoning/coding/fallback model placeholders, optional context/timeout settings, health-check preference, notes, and timestamps
- originally enforced `execution_enabled: false`; M62 allows `execution_enabled: true` only for the operator-gated local prototype while `operator_gate_required` stays true
- added detailed source doc `docs/architecture/LOCAL_LLM_ENVIRONMENT_CONTRACT.md`

Boundaries:

- configuration only
- no Ollama call
- no health check yet
- no model API call
- no prompt execution, routing execution, local LLM execution, Codex execution, agent execution, GitHub/`gh`, workflow activity, network call, or external execution

Recommended next milestone:

- M59 - Local LLM Health Check.

## M57 Prompt Pack Routing Integration

Status: Completed locally on `main`.

Delivered:

- extended `generate_local_queue_prompt_pack(...)` so prompt packs include per-item routing metadata by default
- included routing fields for agent lane, engine, model, fallback, policy source, routing reason, risk, complexity, escalation, project AI mode, operator override, and `execution_allowed: false`
- represented unrouted items with manual routing guidance
- represented `codex_cli` and local LLM engines as recommendations only, never execution
- added optional routing grouping for prompt packs by agent lane, engine, model, risk level, complexity level, and status
- exposed routing prompt-pack options through the local Hub API and Queue UI

Boundaries:

- prompt packs remain local artifacts/previews only
- one canonical local queue remains the source of truth
- prompt-pack generation does not start, complete, or mutate queue items
- no routing execution, local LLM execution, Codex execution, agent execution, GitHub/`gh`, prompt execution, workflow activity, network call, or external execution

Recommended next milestone:

- M58 - Local LLM Environment Contract.

## M56 Routed Queue Views

Status: Completed locally on `main`.

Delivered:

- added read-only routed queue view helper `read_local_routed_queue_views(...)`
- added Hub route `GET /api/local-queue/routed-views`
- added Queue UI panel for routed view filters and grouped counts
- supported filters for project, status, agent lane, engine, model, fallback engine, risk, complexity, project AI mode, routing policy source, and operator override state
- supported grouped views by agent lane, engine, model, project policy, risk level, complexity level, and status
- handled mixed routed/unrouted items, empty queues, and legacy items without routing metadata

Boundaries:

- one canonical local queue remains the source of truth
- routed queue views are read-only filters over the canonical queue
- no queue storage split
- no prompt-pack routing integration yet
- no routing execution, local LLM execution, Codex execution, agent execution, GitHub/`gh`, prompt execution, workflow activity, network call, or external execution

Recommended next milestone:

- M57 - Prompt Pack Routing Integration.

## M55 Project AI Settings UI

Status: Completed locally on `main`.

Delivered:

- added a Project AI Settings panel to the Projects Hub section
- wired the panel to existing M51 routes `GET /api/projects/{project_id}/ai-settings` and `POST /api/projects/{project_id}/ai-settings`
- operators can view and update `project_ai_mode`, `available_engines`, `disabled_engines`, `default_engine`, optional `default_model`, `operator_override_allowed`, and notes
- UI displays validation status, warnings, blockers, and `next_safe_action`
- invalid settings are surfaced through validation output and are not saved by the API

Boundaries:

- local-only, file-backed, and operator-gated
- settings are routing preferences and future execution configuration only
- no routing execution, local LLM execution, Codex execution, agent execution, GitHub/`gh`, prompt execution, workflow activity, network call, or external execution
- no complex model management UI was added

Recommended next milestone:

- M56 - Routed Queue Views.

## M54 Routing Decision Matrix v1

Status: Completed locally on `main`.

Delivered:

- added recommendation-only routing helpers `recommend_queue_item_routing(...)` and `apply_queue_item_routing_recommendation(...)`
- recommendations use M51 Project AI Settings, M52 Agent and Engine Registry, and M53 Queue Routing Metadata
- added Hub routes `POST /api/local-queue/items/{item_id}/routing-recommendation` and `POST /api/local-queue/items/{item_id}/apply-routing-recommendation`
- added minimal Queue UI controls for Recommend Routing and explicit Apply Routing Metadata
- recommendations include project policy, agent lane, engine, fallback, risk/complexity, routing reason, escalation reason, operator override, and `execution_allowed: false`
- apply writes queue routing metadata only through explicit operator action

Boundaries:

- recommendation-only and local-only
- no local LLM, Codex, real agent, GitHub, `gh`, workflow, prompt, network, or external execution
- no queue storage split
- no metadata write unless the operator explicitly applies a recommendation

Recommended next milestone:

- M55 - Project AI Settings UI.

## M53 Queue Routing Metadata Contract

Status: Completed locally on `main`.

Delivered:

- added default queue routing metadata to queue item views and new queue item creation
- added `default_queue_routing_metadata(...)`, `validate_queue_routing_metadata(...)`, and `update_local_queue_item_routing_metadata(...)`
- added Hub route `POST /api/local-queue/items/{item_id}/routing-metadata`
- Queue item detail now displays routing metadata as read-only context
- supported agent lanes align with M52: `architect_planner`, `coding`, `reviewer_validator`, `documentation`, `test`, `local_operator_assistant`, and `high_value_codex`
- supported engines align with M52: `local_reasoning_llm`, `local_coding_llm`, and `codex_cli`
- supported risk levels are `low`, `medium`, `high`, `critical`, and `unknown`
- supported complexity levels are `low`, `medium`, `high`, and `unknown`

Boundaries:

- one canonical local queue remains the source of truth
- routing metadata is local-only, file-backed, operator-gated, and non-executing
- no routing decisions are computed
- no queue storage split
- no local LLM, Codex, agent, GitHub, `gh`, workflow, network, prompt, or external execution is performed

Recommended next milestone:

- M54 - Routing Decision Matrix v1.

## M52 Agent and Engine Registry Contract

Status: Completed locally on `main`.

Delivered:

- added a read-only Agent and Engine Registry Contract through `read_agent_engine_registry(...)`
- added Hub route `GET /api/agent-engine-registry`
- documented required agent lanes: `architect_planner`, `coding`, `reviewer_validator`, `documentation`, `test`, `local_operator_assistant`, and `high_value_codex`
- documented required engines: `local_reasoning_llm`, `local_coding_llm`, and `codex_cli`
- each lane includes key, display name, purpose, default allowed engines, recommended default engine, risk notes, `execution_allowed: false`, and `routing_only: true`
- each engine includes key, display name, purpose, `execution_allowed: false`, local-only boundary notes, model profile placeholders, availability status, and `operator_gate_required: true`
- Codex CLI is represented as engine `codex_cli` with placeholder-only future model profile fields

Boundaries:

- local-only, read-only, non-executing, and operator-gated
- no routing decisions are executed
- no queue routing metadata is written
- no local LLM, Codex, agent, GitHub, `gh`, workflow, network, or external execution is performed
- no complex UI was added in M52

Recommended next milestone:

- M53 - Queue Routing Metadata Contract.

## M51 Project AI Settings Contract

Status: Completed locally on `main`.

Delivered:

- added a file-backed Project AI Settings Contract at `.aresforge/projects/{project_id}/ai_settings.json`
- added operator functions `read_project_ai_settings(...)`, `update_project_ai_settings(...)`, and `validate_project_ai_settings(...)`
- added Hub API wrappers for `GET /api/projects/{project_id}/ai-settings` and `POST /api/projects/{project_id}/ai-settings`
- settings support `project_ai_mode`, `available_engines`, `disabled_engines`, `default_engine`, optional `default_model`, `operator_override_allowed`, `notes`, and `updated_at`
- supported modes are `balanced`, `local_only`, `codex_only`, `cost_saver`, `high_confidence`, and `manual_only`
- supported engine keys are `local_reasoning_llm`, `local_coding_llm`, and `codex_cli`
- validation rejects unsupported modes/engines, disabled defaults, local-only Codex defaults, Codex-only local defaults, and missing defaults except for `manual_only`

Boundaries:

- local-only, file-backed, non-executing, and operator-gated
- no routing decisions are executed
- no queue routing metadata is written
- no local LLM, Codex, agent, GitHub, `gh`, workflow, network, or external execution is performed
- no Hub UI settings surface was added in M51

Recommended next milestone:

- M52 - Agent and Engine Registry Contract.

## M50 Handoff Generator

Status: Completed locally on `main`.

Delivered:

- added `generate_local_project_handoff(...)` for copy/paste-ready local project handoff generation
- added Hub route `POST /api/local-project/handoff`
- added a Local Project Handoff Generator panel to the Handoff section
- handoff output includes project/repo/branch context, operating rules, latest milestone/commit, architecture boundaries, Hub capabilities, queue/report/progress summary, open queue items, blockers/warnings, evidence/closeout summary, recommended next milestone/instruction, and start-of-next-chat validation commands
- optional local artifact output is supported with safe non-overwrite behavior unless `force=true`

Boundaries:

- local-only, file-backed, read-only unless optional local artifact output is explicitly requested, and operator-gated
- no GitHub API, `gh`, issues, PRs, workflow activity, GitHub mutation, agent execution, Codex execution, local LLM execution, model routing, or external execution
- handoff generation reuses Reports v1 and M48 progress rollup state

Recommended next milestone:

- M51 - Project AI Settings Contract.

## M49 Reports v1

Status: Completed locally on `main`.

Delivered:

- added `read_local_project_reports(...)` for local Reports v1
- added Hub route `GET /api/reports/local-projects`
- added a read-only Reports v1 panel to the existing Reports section
- Reports v1 summarizes project count/statuses, active project, queue totals, counts by status/type/lane, blocked/ready/in-progress work, evidence capture, closeout eligibility, closed/completed work, latest activity, M48 progress rollup, blockers, warnings, limitations, and `next_safe_action`

Boundaries:

- local-only, file-backed, read-only, and operator-gated
- no export/PDF/CSV expansion beyond existing in-page JSON text behavior
- no queue/project mutation, prompt execution, Codex execution, local LLM execution, agent execution, GitHub/`gh`, workflow activity, push, external service call, or routing execution
- routing implementation remains future work after the workflow/reporting sequence

Recommended next milestone:

- M50 - Handoff Generator.

## M48 Project Progress Rollup

Status: Completed locally on `main`.

Delivered:

- added `read_local_project_progress_rollup(...)` for read-only project queue progress inspection
- added Hub route `GET /api/projects/{project_id}/progress-rollup`
- added a minimal Projects UI Project Progress Rollup panel
- rollup summarizes total queue items, status/type/lane counts, ready/blocked/in-progress items, evidence capture count, closeout eligibility, closed/completed count, latest activity, blockers, warnings, and `next_safe_action`

Boundaries:

- local-only, file-backed, read-only, and operator-gated
- rollup does not mutate queue/project state, generate reports, execute prompts, call Codex/local LLMs/agents, route models, call GitHub/`gh`, push code, or run external workflows
- future routing metadata is only reported as future/not implemented
- full Reports v1 remains future work

Recommended next milestone:

- M49 - Reports v1.

## M47 Queue Item Closeout Workflow

Status: Completed locally on `main`.

Delivered:

- added `close_local_queue_item(...)` for explicit local queue item closeout
- added Hub route `POST /api/local-queue/items/{item_id}/closeout`
- added minimal Queue UI controls for operator-gated closeout
- closeout requires eligible `in_progress` status, captured completion evidence, required evidence fields, and a closeout summary
- closeout transitions the queue item to existing `done` status and records `closed_at`, `closed_by`, `closeout_summary`, and `closeout_history`

Boundaries:

- local-only, file-backed, operator-gated closeout
- closeout does not generate prompts, execute prompts, call Codex, call local LLMs, call GitHub, push code, or run external workflows
- Agent/LLM routing remains future work

Recommended next milestone:

- M48 - Project Progress Rollup.

## M46 Completion Evidence Capture

Status: Completed locally on `main`.

Delivered:

- added `capture_local_queue_completion_evidence(...)` for local queue item completion evidence capture
- added Hub route `POST /api/local-queue/items/{item_id}/evidence`
- added minimal Queue UI controls for capturing evidence without completing the item
- evidence capture records `completion_evidence` on the existing queue item while preserving existing queue item data and status
- response includes `next_safe_action` and advisory `closeout_eligible`

Boundaries:

- local-only, file-backed, operator-gated evidence capture
- evidence capture is separate from closeout and does not automatically complete queue items
- no routing implementation, local LLM execution, Codex execution, real agent execution, GitHub integration, or external workflow execution

Recommended next milestone:

- M47 - Queue Item Closeout Workflow.

## M45 Local Hub End-to-End Operator Workflow Validation

Status: Completed locally on `main`.

Delivered:

- added focused Hub end-to-end operator workflow validation in `tests/test_hub_end_to_end_operator_workflow.py`
- validated the existing local Hub path from dashboard inspection through active project context, queue intake, queue detail, readiness, prompt-pack generation, local project report, and queue agent summary
- confirmed prompt-pack generation remains advisory and does not start, complete, or otherwise mutate queue item lifecycle state
- documented the current validated operator workflow across source-of-truth docs

Boundaries:

- validation and documentation only
- no routing implementation, local LLM execution, Codex execution, real agent execution, GitHub integration, or queue storage split
- no backend route additions, no frontend settings UI, no queue schema changes

Recommended next milestone:

- M46 - completion evidence capture for local operator workflow closeout.

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
