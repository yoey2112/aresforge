# AresForge Build State

## Current Phase

M37 AresForge Hub UI foundation (local-only).

## Current Goal

Implement and document a local-first Hub foundation that serves as the main local entry point for AresForge with a local server, API shell, frontend shell, navigation, home summary, docs status, and placeholder sections.

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
