# AresForge Roadmap

## M121 Human Approval Inventory and Review Ledger

Status: Implemented locally on `main` pending completion evidence commit.

Queue item: `m121-human-approval-inventory-and-review-ledger`.

Purpose:

- inventory human review status for generated artifacts, patch proposals, dispatch records, and completion recommendations
- reuse existing dispatch approval gates as review evidence
- let operators record explicit artifact decisions as `approved`, `rejected`, or `needs_changes`
- surface approval gaps before manual handoff, patch intake, or completion

Runnable operator surface:

- `python -m aresforge inspect-approval-ledger --project-id aresforge --format json`
- `python -m aresforge record-artifact-review --item-id <item_id> --artifact-path <path> --decision approved --format json`
- optional `--item-id`, `--artifact-path`, `--output`, and `--force`

Constraints preserved:

- review ledger only
- no automatic approval
- `local_only=true` and `execution_allowed=false`
- no queue item start, queue completion, agent execution, Codex execution, Ollama/local LLM prompting, remote LLM call, GitHub API, `gh`, network service, validation command execution, patch application, external mutation, autonomous execution, or next-item execution

## M120 Operator Batch Queue Sequencer v2

Status: Completed locally on `main` after validation.

Queue item: `m120-operator-batch-queue-sequencer-v2`.

Implementation commit: `b4f6a39`.

Purpose:

- recommend an ordered local operator batch from proposed and ready queue items
- account for dependencies, priority, artifact readiness, approval gates, and lane grouping
- surface dependency warnings, approval warnings, artifact warnings, blocked items, operator checklist, and next safe action
- keep sequencing advisory and non-executing

Runnable operator surface:

- `python -m aresforge plan-operator-batch-v2 --project-id aresforge --format json`
- optional `--limit`, `--include-blocked`, `--output`, and `--force`

Constraints preserved:

- sequencing only
- `execution_performed=false`
- `queue_mutation_performed=false`
- `local_only=true` and `execution_allowed=false`
- no queue item start, agent execution, Codex execution, Ollama/local LLM prompting, remote LLM call, GitHub API, `gh`, network service, validation command execution, patch application, external mutation, automatic completion, autonomous execution, or next-item execution

## M119 Dispatch Artifact Registry Index v2

Status: Completed locally on `main` after validation.

Queue item: `m119-dispatch-artifact-registry-index-v2`.

Implementation commit: `6c31268`.

Purpose:

- provide a versioned local registry for dispatch and review artifacts created by M109-M117 planning workflows
- make manual dispatch records, Codex prompt dispatch artifacts, local LLM advisory requests, patch intake records, dispatch evidence, completion recommendations, documentation proposals, and route recommendations discoverable through one operator command
- surface missing expected folders, stale artifacts, duplicates, blocked artifacts, review-required artifacts, and next safe action
- keep artifact discovery advisory and non-executing

Runnable operator surface:

- `python -m aresforge inspect-artifact-registry --format json`
- `python -m aresforge inspect-artifact-registry --project-id aresforge --item-id <item_id> --artifact-type <type> --format json`
- optional `--output <path>` and `--force`

Constraints preserved:

- registry inspection only
- `local_only=true` and `execution_allowed=false`
- no Codex, Ollama/local LLM, remote LLM, agent, GitHub API, `gh`, network service, patch application, source mutation, queue mutation, automatic completion, autonomous execution, or next-item execution

## M128 Agent Orchestration Plan Builder

Status: Completed locally on `main` after validation.

Queue item: `m128-agent-orchestration-plan-builder`.

Purpose:

- convert one local queue item into an ordered machine-readable agent orchestration plan
- combine queue metadata, the M126 agent registry, and the M127 LLM decision policy
- surface required artifacts, dependency checks, machine gates, blocked reasons, autonomy level, and next safe action
- keep orchestration plan generation separate from runtime execution

Runnable operator surface:

- `python -m aresforge build-agent-orchestration-plan --item-id <item_id> --format json`
- optional `--agent-id`, `--execution-target dry-run|real`, `--output`, and `--force`

Constraints preserved:

- plan-only
- `execution_performed=false`
- real execution target requests block and recommend dry-run
- no agent execution, Codex, local LLM, Ollama, remote LLM, GitHub API, `gh`, network service, validation command execution, patch application, source mutation, queue mutation from the plan, autonomous execution, or next-item execution

## M129 Single-Agent Dry-Run Executor

Status: Completed locally on `main` after validation.

Queue item: `m129-single-agent-dry-run-executor`.

Purpose:

- introduce the first single-agent dry-run execution record path
- allow only deterministic low-risk local agents to inspect, summarize, validate plans, or generate explicit dry-run records
- preserve all external execution and mutation boundaries before any real runner exists

Runnable operator surface:

- `python -m aresforge run-agent-dry-run --agent-id <agent_id> --item-id <item_id> --format json`
- optional `--plan-path`, `--output`, and `--force`

Supported dry-run agents:

- `artifact-registry-agent`
- `evidence-parser-agent`
- `completion-recommendation-agent`
- `validation-agent`
- `sprint-summary-agent`
- `queue-planner-agent`

Constraints preserved:

- dry-run only
- unsupported agents block
- no Codex, local LLM, Ollama, remote LLM, GitHub API, `gh`, network service, validation command execution, patch application, source mutation, queue mutation from the dry-run, autonomous execution, or next-item execution
- explicit `--output` may write only the dry-run execution record artifact
## M118 Post-Automation Planning Reconciliation

Status: Completed locally on `main` after validation.

Queue item: `m118-post-automation-planning-reconciliation`.

Implementation commit: `46c007c`.

Purpose:

- reconcile source-of-truth documentation after M110-M117
- align queue state, roadmap, architecture notes, operator usage, and current safety boundaries
- document the current operator workflow and remaining automation gaps
- define the next safe milestone direction without adding runtime features

Reconciliation scope:

- M110 Local LLM Advisory Artifact Generator
- M111 Approval-Gated Patch Intake Contract
- M112 Dispatch Result Evidence Parser
- M113 Queue Item Auto-Completion Recommendation Engine
- M114 Hub Dispatch Review Panel
- M115 Local Ollama Provider Probe Integration
- M116 Documentation Agent Patch Proposal Generator
- M117 Agent Routing Decision Dashboard

Constraints preserved:

- docs/data-only milestone
- no new CLI, API, Hub runtime, or background automation behavior
- no Codex, Ollama, local LLM, agent runtime, GitHub API, `gh`, network service, workflow, patch application, automatic queue completion, or next-item execution
- all dispatch, advisory, patch, evidence, completion, and routing surfaces remain local-only and operator-gated

Next recommended milestones:

- define the next operator evidence or documentation ledger checkpoint
- keep any future execution runner as a separate explicitly approved milestone
- preserve artifact-first, approval-gated, validation-evidence-driven sequencing
## M117 Agent Routing Decision Dashboard

Status: Completed locally on `main` after validation.

Queue item: `m117-agent-routing-decision-dashboard`.

Implementation commit: `585c99a`.

Purpose:

- explain which executor or advisor lane is recommended for one queue item
- expose the recommendation through CLI, local Hub API, and Hub UI
- keep routing advisory-only and operator-gated
- preserve the no-dispatch, no-execution boundary

Runnable operator surface:

- `python -m aresforge recommend-agent-route --item-id <item_id>`
- `python -m aresforge recommend-agent-route --item-id <item_id> --format json`
- optional `--output <path>` and `--force`

Recommendation contract:

- `recommendation_type=agent_route_recommendation`
- queue identity and milestone
- recommended lane and alternative lanes
- routing reasons, required artifacts before dispatch, and approval requirements
- local LLM, Codex, and documentation-agent suitability flags
- `human_operator_required=true`
- `dispatch_performed=false`
- `execution_allowed=false`
- `local_only=true`
- next safe action

Hub surface:

- Queue page Agent Routing Decision Dashboard
- read-only local API wrapper
- no execute buttons or dispatch controls
- labels actions as local-only and advisory

Constraints preserved:

- no Codex, Codex CLI, Ollama, local LLM, agent runtime, GitHub API, `gh`, network service, workflow, patch application, source mutation, queue mutation, automatic completion, or next-item execution
## M127 LLM Decision Policy v1

Status: Completed locally on `main` after validation.

Queue item: `m127-llm-decision-policy-v1`.

Implementation commit: pending final commit.

Purpose:

- create the first formal LLM-level decision policy above queue and agent metadata
- recommend the appropriate lane, provider, and model profile for a queue item or agent task
- separate recommendation from execution with explicit human/machine gates
- keep all output machine-readable and local-only unless the recommended future lane itself requires network/GitHub review

Runnable operator surface:

- `python -m aresforge recommend-llm-decision --item-id <item_id> --format json`
- optional `--agent-id`, `--task-type`, `--risk-level`, `--mutation-scope`, `--output`, and `--force`

Supported lanes:

- `no_llm_required`
- `local_llm_reasoning`
- `local_llm_coding_review`
- `codex_coding`
- `codex_reasoning`
- `remote_high_value_reasoning`
- `remote_low_cost_reasoning`
- `documentation_agent`
- `validation_agent`
- `github_sync_agent`

Constraints preserved:

- recommendation-only
- `execution_performed=false`
- no Codex, local LLM, remote LLM, Ollama, GitHub API, `gh`, agent runtime, validation command, network service, patch application, queue mutation, source mutation, autonomous execution, or next-item execution

## M116 Documentation Agent Patch Proposal Generator

Status: Completed locally on `main` after validation.

Queue item: `m116-documentation-agent-patch-proposal-generator`.

Implementation commit: `0d8bbdf`.

Purpose:

- compare local queue/build state against selected source-of-truth docs
- detect documentation gaps for one queue item
- generate a structured documentation patch proposal artifact
- generate a proposed patch text file for operator review
- preserve the approval and patch-application boundary

Runnable operator surface:

- `python -m aresforge generate-doc-agent-patch-proposal --item-id <item_id>`
- `python -m aresforge generate-doc-agent-patch-proposal --item-id <item_id> --format json`
- optional `--output <path>` and `--force`
- optional `--include-roadmap`, `--include-context`, and `--include-operator-docs`

Proposal contract:

- `artifact_type=documentation_agent_patch_proposal`
- generated/blocked status and blocked reasons
- queue identity and milestone
- reviewed source documents
- detected documentation gaps
- proposed documentation changes
- proposed patch path
- operator checklist
- `approval_required=true`
- `patch_application_allowed=false`
- `patch_application_performed=false`
- `local_only=true`
- `execution_allowed=false`

Constraints preserved:

- no generated patch application
- no documentation-agent runtime execution
- no Codex, Ollama, local LLM, GitHub API, `gh`, network, workflow, source mutation, queue mutation, approval mutation, automatic handoff, or next-item execution

## M115 Local Ollama Provider Probe Integration

Status: Completed locally on `main` after validation.

Queue item: `m115-local-ollama-provider-probe-integration`.

Implementation commit: `9913605`.

Purpose:

- report whether local Ollama appears configured and detectable
- surface configured reasoning, coding, and fallback model profiles
- optionally inspect visible local models through loopback `/api/tags`
- preserve a strict no-prompt, no-inference, no-generation boundary

Runnable operator surface:

- `python -m aresforge probe-local-ollama-provider`
- `python -m aresforge probe-local-ollama-provider --format json`
- `python -m aresforge probe-local-ollama-provider --no-network --format json`
- optional `--config <path>`, `--output <path>`, and `--force`

Probe contract:

- `probe_type=local_ollama_provider_probe`
- records probed/blocked status and blocked reasons
- records `ollama_expected`, `ollama_detected`, `probe_method`, configured model profiles, visible models when safely detectable, and model recommendation metadata
- records `advisory_execution_allowed=false`
- records `prompt_execution_performed=false`, `coding_execution_performed=false`, and `reasoning_execution_performed=false`
- records `local_only=true` and `execution_allowed=false`

Constraints preserved:

- `--no-network` performs configuration-only inspection
- network probing is limited to local loopback `/api/tags`
- non-loopback provider URLs block network probing
- no prompts, generation, chat, completion, coding, reasoning, advisory execution, Codex execution, GitHub API, `gh`, agent execution, workflow behavior, patch application, queue mutation, repository mutation, or next-item execution

## M114 Hub Dispatch Review Panel

Status: Completed locally on `main` after validation.

Queue item: `m114-hub-dispatch-review-panel`.

Implementation commit: `d5ffb6b`.

Purpose:

- add a read-only Hub surface for dispatch review artifacts
- let operators inspect manual dispatch preparation, local LLM advisory, patch intake, parsed evidence, and completion recommendation records
- keep all review actions local-only and advisory
- preserve execution denial from the Hub

Runnable operator surface:

- Hub Queue panel Dispatch Review section
- `GET /api/dispatch-review`
- optional `item_id` and `limit` filters

API behavior:

- scans known local artifact folders
- normalizes record type, item id, milestone, blocked status, next safe action, and operator checklist
- returns stable JSON with `local_only=true`, `read_only=true`, and `execution_allowed=false`

UI behavior:

- shows dispatch review summary counts
- lists review records with artifact type, item id, milestone, blocked status, status, next safe action, and local path
- shows an operator checklist for human review
- labels the panel local-only and operator-gated

Constraints preserved:

- no execution endpoints
- no Codex, local LLM, Ollama, documentation-agent runtime, external-agent, GitHub API, `gh`, network, workflow, issue, PR, patch application, automatic queue mutation, automatic handoff, or next-item execution

## M126 Agent Registry

Status: Completed locally on `main` after validation.

Queue item: `m126-agent-registry`.

Implementation commit: pending final commit.

Purpose:

- create a local-only registry of supported AresForge agents
- declare what each agent may read, produce, and request
- declare allowed and forbidden capabilities, mutation/network/model scopes, safety classes, and autonomy levels
- keep the registry inspectable without executing agents or creating workflows

Runnable operator surface:

- `python -m aresforge inspect-agent-registry --format json`
- `python -m aresforge inspect-agent-registry --agent-id <agent_id> --format json`
- `python -m aresforge inspect-agent-registry --safety-class <safety_class> --format json`
- `python -m aresforge inspect-agent-registry --autonomy-level <level> --format json`
- optional `--output <path>` and `--force`

Registered agents:

- `queue-planner-agent`
- `codex-dispatch-agent`
- `local-llm-advisory-agent`
- `documentation-agent`
- `evidence-parser-agent`
- `completion-recommendation-agent`
- `validation-agent`
- `github-sync-agent`
- `sprint-summary-agent`
- `artifact-registry-agent`
- `approval-ledger-agent`
- `transaction-log-agent`

Constraints preserved:

- no agent execution
- no Codex, local LLM, Ollama, documentation-agent runtime, external-agent, GitHub API, `gh`, network, workflow, issue, PR, patch application, automatic queue mutation, automatic handoff, or next-item execution
- all registered agents are dry-run/inspection metadata only and have `can_run_real=false`

Relationship:

- M126 consumes the M125 boundary terms and applies them to named initial agents.
- Future runners must validate agent records against this registry before any separate operator-approved execution milestone can run.

## M113 Queue Item Auto-Completion Recommendation Engine

Status: Completed locally on `main` after validation.

Queue item: `m113-queue-item-auto-completion-recommendation-engine`.

Implementation commit: `a988af7`.

Purpose:

- evaluate local dispatch result evidence against known queue completion requirements
- recommend whether an operator may safely complete a queue item
- preserve explicit human completion by keeping queue mutation disabled
- surface missing evidence, failed validation, warnings/blockers, commit hash absence, and confidence

Runnable operator surface:

- `python -m aresforge recommend-queue-completion --item-id <item_id> --evidence-path <path>`
- `python -m aresforge recommend-queue-completion --item-id <item_id> --evidence-path <path> --format json`
- optional `--output`, `--force`, and `--queue-path`

Ready behavior:

- queue item must exist
- evidence file must be local JSON
- evidence must be M112 `dispatch_result_evidence`
- evidence must match the requested item and be parsed/unblocked
- tests and smoke checks must be reported as passed
- commit hash, files changed, and change summary evidence must be present
- queue `completion_requires` and `evidence_required` are evaluated when present

Blocked behavior:

- missing queue item blocks
- missing or invalid evidence file blocks
- mismatched, blocked, or unsafe evidence blocks
- missing required evidence blocks
- failed tests, failed smoke checks, missing commit hash, or severe warnings/blockers block completion recommendation
- output overwrite blocks unless `--force` is provided

Constraints preserved:

- no queue mutation or automatic completion
- no Codex execution or Codex CLI shell-out
- no local LLM, Ollama, documentation-agent, external-agent, GitHub API, `gh`, network, issue, PR, workflow, or patch application behavior
- no approval mutation, handoff automation, or next-item execution

Relationship:

- M113 consumes M112 dispatch evidence.
- M113 recommends only; human operators still complete queue items explicitly with validation evidence.

## M125 Agent Runtime Boundary Contract

Status: Completed locally on `main` after validation.

Queue item: `m125-agent-runtime-boundary-contract`.

Implementation commit: pending final commit.

Purpose:

- define what an AresForge agent is before runtime execution exists
- define allowed and forbidden capabilities, inputs, outputs, scopes, runtime limits, evidence requirements, safety classes, and autonomy levels
- expose a deterministic operator inspection command for future agent/runtime milestones
- keep execution denied by default

Runnable operator surface:

- `python -m aresforge inspect-agent-runtime-boundary`
- `python -m aresforge inspect-agent-runtime-boundary --format json`
- `python -m aresforge inspect-agent-runtime-boundary --format markdown`

Stable output fields:

- `contract_type`
- `generated`
- `agent_boundary_version`
- `supported_execution_modes`
- `supported_autonomy_levels`
- `supported_safety_classes`
- `allowed_capability_catalog`
- `forbidden_capability_catalog`
- `mutation_scope_catalog`
- `network_scope_catalog`
- `model_scope_catalog`
- `evidence_requirements`
- `default_runtime_limits`
- `local_only`
- `execution_performed`
- `next_safe_action`

Constraints preserved:

- no agent execution
- no Codex, local LLM, Ollama, documentation-agent, external-agent, GitHub API, `gh`, network, workflow, issue, PR, patch application, automatic queue mutation, automatic handoff, or next-item execution

Relationship:

- M125 is the foundation contract future agents and runners must satisfy.
- It does not replace M97-M111 dispatch, dry-run, approval, handoff, or patch-intake contracts.
- Any future runtime runner must separately enforce this boundary and require explicit operator approval.

## M112 Dispatch Result Evidence Parser

Status: Completed locally on `main` after validation.

Queue item: `m112-dispatch-result-evidence-parser`.

Implementation commit: `5088c95`.

Purpose:

- parse a local human-pasted Codex result text or markdown file
- extract structured evidence for files changed, change summary, tests, smoke checks, warnings/blockers, and commit hash
- warn on missing evidence sections without crashing
- preserve human review before queue completion

Runnable operator surface:

- `python -m aresforge parse-dispatch-result-evidence --item-id <item_id> --result-path <path>`
- `python -m aresforge parse-dispatch-result-evidence --item-id <item_id> --result-path <path> --format json`
- `python -m aresforge parse-dispatch-result-evidence --item-id <item_id> --result-path <path> --output <path> --force`

Ready behavior:

- queue item must exist
- result file must exist locally
- parser emits stable `dispatch_result_evidence`
- missing sections become warnings
- completion recommendation remains advisory

Blocked behavior:

- missing queue item blocks
- missing result file blocks
- explicit output path overwrite blocks unless `--force` is provided

Constraints preserved:

- no Codex execution or Codex CLI shell-out
- no local LLM, Ollama, documentation-agent, external-agent, GitHub API, `gh`, network, issue, PR, workflow, or patch application behavior
- no repository mutation from parsed output
- no automatic queue completion, approval mutation, handoff, or next-item execution

Relationship:

- M112 consumes manual dispatch result evidence after an operator-run Codex session.
- M112 does not complete the queue item; it prepares structured evidence for human review and later completion recommendation workflows.

## M111 Approval-Gated Patch Intake Contract

Status: Completed locally on `main` after validation.

Queue item: `m111-approval-gated-patch-intake-contract`.

Implementation commit: `98ec90c`.

Purpose:

- record a proposed patch artifact for human review
- validate queue item, patch artifact existence, and approval status
- accept patch proposals for review only after explicit human approval exists
- keep patch application blocked in every intake state

Runnable operator surface:

- `python -m aresforge intake-patch-proposal --item-id <item_id> --patch-artifact <path>`
- `python -m aresforge intake-patch-proposal --item-id <item_id> --patch-artifact <path> --format json`
- `python -m aresforge intake-patch-proposal --item-id <item_id> --patch-artifact <path> --approval-id <approval_id>`
- optional `--output <path>` and `--force`

Ready behavior:

- queue item must exist
- local patch artifact must exist
- approval gate must exist and be `approved_for_manual_handoff`
- record always reports `operator_review_required=true`
- record always reports `patch_application_allowed=false`
- record always reports `patch_application_performed=false`

Blocked behavior:

- missing queue item blocks
- missing patch artifact blocks
- missing approval gate blocks
- `pending_review`, `rejected`, `needs_revision`, missing, or unknown approval status blocks
- explicit output path overwrite blocks unless `--force` is provided

Constraints preserved:

- no patch application
- no repository mutation
- no Codex, local LLM, documentation-agent, external-agent, GitHub API, `gh`, network, issue, PR, or workflow behavior
- no automatic queue mutation, approval mutation, handoff, completion, or next-item execution

Relationship:

- M111 is the intake boundary for patch proposals returned by manual Codex, local LLM advisory/draft, or documentation-agent proposal workflows.
- M111 does not implement an apply command.
- Any future patch application remains a separate explicit operator-approved workflow with validation gates.

## M110 Local LLM Advisory Artifact Generator

Status: Completed locally on `main` after validation.

Queue item: `m110-local-llm-advisory-artifact-generator`.

Implementation commit: `f4e81ff`.

Purpose:

- generate a local-only advisory request artifact for queue items routed to `local_llm_advisory`
- describe what a future local reasoning model would review without invoking it
- capture queue context, source documents, advisory prompt, expected response shape, and operator checklist
- preserve local-only/manual-gated dispatch boundaries before any future provider run

Runnable operator surface:

- `python -m aresforge generate-local-llm-advisory-artifact --item-id <item_id>`
- `python -m aresforge generate-local-llm-advisory-artifact --item-id <item_id> --format json`
- `python -m aresforge generate-local-llm-advisory-artifact --item-id <item_id> --output <path> --force`
- optional `--model-profile <profile>` and `--reasoning-scope <scope>`

Ready behavior:

- selected lane must be `local_llm_advisory`
- M97 plan must be unblocked
- plan must preserve `local_only=true` and `execution_allowed=false`
- default artifacts are written under `artifacts/local_llm_advisory/requests`
- explicit output paths are overwrite-safe unless `--force` is present

Blocked behavior:

- non-advisory lanes block
- blocked M97 plans block
- unsafe local/execution flags block
- existing explicit output files block without `--force`

Constraints preserved:

- no Ollama/local LLM calls
- no Codex execution or Codex CLI shell-out
- no GitHub API, `gh`, network, external-agent, or documentation-agent behavior
- no patch application
- no automatic queue mutation, completion, approval mutation, handoff, or next-item execution

Relationship:

- M110 follows M99 advisory readiness validation and prepares the advisory request package only.
- M110 is separate from M85's optional provider execution prototype.
- Future local LLM execution still requires a separate explicit operator gate and milestone.

## M109 Manual Codex Dispatch Runner Contract

Status: Completed locally on `main` after validation.

Queue item: `m109-manual-codex-dispatch-runner-contract`.

Implementation commit: `bfa4139`.

Purpose:

- prepare a local manual Codex dispatch run record from a reviewed M98 prompt artifact
- bridge "prompt artifact generated" to "operator manually dispatched it" without automating Codex
- validate M97 lane/safety flags, M98 artifact presence, M101 approval status, M106 artifact index data when available, and queue lifecycle safety
- emit operator steps, checklist, expected post-run evidence, and next safe action

Runnable operator surface:

- `python -m aresforge prepare-manual-codex-dispatch --item-id <item_id>`
- `python -m aresforge prepare-manual-codex-dispatch --item-id <item_id> --format json`
- `python -m aresforge prepare-manual-codex-dispatch --item-id <item_id> --artifact-path <path> --approval-id <approval_id>`

Ready behavior:

- selected lane must be `codex_prompt_artifact`
- queue item must not be done, blocked, cancelled, or lifecycle-unsafe
- plan/artifact must be `local_only=true` and `execution_allowed=false`
- Codex prompt artifact must exist
- approval gate must be `approved_for_manual_handoff`
- result always reports `execution_allowed=false` and `codex_execution_performed=false`

Blocked behavior:

- missing artifact blocks
- missing approval gate blocks as `needs_approval`
- pending, rejected, needs-revision, or unknown approval status blocks
- non-Codex lane blocks
- unsafe queue status blocks
- any source plan/artifact that allows execution blocks

Constraints preserved:

- no Codex execution or Codex CLI shell-out
- no patch application
- no GitHub API, `gh`, network, Ollama/local LLM, documentation-agent, external-agent, workflow, issue, or PR behavior
- no automatic queue mutation, completion, approval mutation, handoff, or next-item execution

Relationship:

- M109 consumes M97/M98/M101/M106 context and prepares manual dispatch only.
- M110 should generate local LLM advisory artifacts without inheriting Codex runner behavior.
- M111 should define approval-gated patch intake for evidence returned after a manual Codex run.

## M108 Sprint Closeout and Next-Stage Automation Plan

Status: Completed locally on `main` after validation.

Queue item: `m105-post-batch-documentation-reconciliation-m108-sprint-closeout-and-next-stage-automation-plan`.

Implementation commit: `549c5fc`.

Purpose:

- close the M99-M107 sprint with local report evidence
- reconcile roadmap, build state, agent context, operator usage, and architecture docs
- summarize completed dispatch-preparation capabilities
- identify gaps and risks before automation work
- define the next controlled automation batch without implementing it

Current sprint achievements:

- M99 validates local LLM advisory dry-run readiness without invoking models.
- M100 validates documentation-agent dry-run review readiness without mutating docs.
- M101 records local human approval gate status while keeping execution blocked.
- M102 enforces dependency and completion evidence locks.
- M103 confirms AresForge as its self-managed project.
- M104 proposes read-only operator batches.
- M105 reconciles docs/data after M99-M104.
- M106 indexes dispatch artifacts and approval status.
- M107 generates safe dispatch handoff packages.

Current report posture:

- M99-M107 are complete.
- M108 is complete.
- M96 remains proposed as older manual planning context.
- No queue blockers are reported.
- The artifact index currently has zero entries and warns that known artifact folders are missing.
- Safe dispatch handoff and standard handoff outputs remain local-only/read-only.

Next recommended milestone batch:

- M109 Manual Codex Dispatch Runner Contract
- M110 Local LLM Advisory Artifact Generator
- M111 Approval-Gated Patch Intake Contract
- M112 Dispatch Result Evidence Parser
- M113 Queue Item Auto-Completion Recommendation Engine
- M114 Hub Dispatch Review Panel
- M115 Local Ollama Provider Probe Integration
- M116 Documentation Agent Patch Proposal Generator
- M117 Agent Routing Decision Dashboard
- M118 Post-Automation-Planning Reconciliation

Constraints preserved:

- no new runtime feature implementation in M108
- no artifact execution, dispatch execution, Codex, Ollama, local LLM, documentation-agent, external-agent, GitHub API, `gh`, network, workflow, issue creation, PR creation, queue auto-mutation, approval auto-mutation, or patch application
- next-stage items must remain one-at-a-time and operator approved

## M107 Safe Dispatch Handoff Package

Status: Completed locally on `main` after validation.

Queue item: `m105-post-batch-documentation-reconciliation-m107-safe-dispatch-handoff-package`.

Implementation commit: `99c79b7`.

Purpose:

- bundle local queue state, dispatch plans, artifact index data, approval gate status, and operator instructions into one safe handoff report
- support readable and JSON handoff output
- support optional local file output without overwriting by default
- clearly identify which actions require manual approval
- preserve `execution_allowed=false` and avoid any implication of automated execution

Runnable operator surface:

- `python -m aresforge generate-safe-dispatch-handoff`
- `python -m aresforge generate-safe-dispatch-handoff --format json`
- `python -m aresforge generate-safe-dispatch-handoff --output artifacts/safe-dispatch/handoff.md`

Constraints preserved:

- read-only by default
- optional output writes one local file only
- no artifact execution, dispatch execution, Codex, Ollama, local LLM, documentation-agent, external-agent, GitHub API, `gh`, network, workflow, issue creation, PR creation, queue mutation, approval mutation, or patch application occurs

M108 relationship:

- M107 is the dispatch/new-chat handoff package.
- M108 should reconcile sprint closeout and the next-stage automation plan after M107 evidence is available.

## M106 Dispatch Artifact Index/Report

Status: Completed locally on `main` after validation.

Queue item: `m105-post-batch-documentation-reconciliation-m106-dispatch-artifact-index-report`.

Implementation commit: `fc77cd2`.

Purpose:

- provide a single local index of dispatch artifacts and dry-run outputs
- identify artifact type, queue item id, selected dispatch lane, file path, timestamps, and approval gate status
- handle missing artifact folders safely
- support readable and JSON output for operator review and future handoff packaging
- preserve local-only, read-only behavior before M107

Runnable operator surface:

- `python -m aresforge inspect-dispatch-artifacts`
- `python -m aresforge inspect-dispatch-artifacts --format json`
- `python -m aresforge inspect-dispatch-artifacts --project-id aresforge`

Constraints preserved:

- report output is advisory only
- `execution_allowed` remains false
- no artifact execution or validation beyond safe local reads
- no queue mutation, approval mutation, automatic handoff, Codex, Ollama, local LLM, documentation-agent, external-agent, GitHub API, `gh`, network, workflow, issue creation, PR creation, or patch application occurs

M107 relationship:

- M106 is the pre-handoff artifact visibility report.
- M107 is expected to create safe handoff packages from operator-reviewed artifacts while preserving approval gates and execution blocks.

## M105 Post-Batch Documentation Reconciliation

Status: Completed locally on `main` after validation.

Queue item: `m96-post-sprint-planning-and-prioritization-m105-post-batch-documentation-reconciliation`.

Implementation commit: `962ac8c`.

Purpose:

- reconcile source-of-truth docs after the completed M99-M104 local-only operator workflow batch
- distinguish implemented local-only commands/contracts from future automation
- update roadmap, build state, agent context, operator usage, and architecture docs
- document current queue/report/handoff warnings
- keep the next sequence manual/operator-selected

Constraints preserved:

- documentation/data reconciliation only
- no new runtime features
- no Codex, Ollama, local LLM, documentation-agent, external-agent, GitHub API, `gh`, network, workflow, issue creation, PR creation, patch application, or automatic next-item execution occurs
- documentation changes are operator-authored source-of-truth edits, not model-generated apply-mode output

Current report posture:

- M99-M104 are completed in the local queue.
- M96 remains `proposed` as older planning context.
- `plan-operator-batch --project-id aresforge --limit 10 --format json` proposes M96 as the only current plannable item.
- `generate-handoff-package` reports untracked `.codex-pytest-cache/` and older local pytest temp permission warnings.

Next recommended sequence:

- M106 Dispatch Artifact Index/Report
- M107 Safe Dispatch Handoff Package
- M108 Sprint Closeout and Next-Stage Automation Plan
- M109 Manual Codex Dispatch Runner Contract
- M110 Local LLM Advisory Artifact Generator
- M111 Approval-Gated Patch Intake Contract

## M104 Operator Batch Planner v1

Status: Completed locally on `main` after validation.

Queue item: `m104-operator-batch-planner-v1`.

Implementation commit: `864af13`.

Purpose:

- propose a safe ordered sprint batch from local queue state
- exclude completed queue items
- respect dependency and blocked status constraints
- prefer ready/proposed work in roadmap milestone order
- classify each planned item by safe local dispatch posture
- preserve local-only, read-only planning before M105 reconciliation

Runnable operator surface:

- `python -m aresforge plan-operator-batch --project-id aresforge`
- `python -m aresforge plan-operator-batch --project-id aresforge --limit 10`
- `python -m aresforge plan-operator-batch --project-id aresforge --limit 10 --format json`

Constraints preserved:

- planner output is advisory only
- `execution_allowed` remains false
- no queue mutation or default queue seeding occurs
- no Codex, Ollama, local LLM, documentation-agent, external-agent, GitHub API, `gh`, network, workflow, issue creation, PR creation, patch application, or automatic next-item execution occurs

M105 relationship:

- M104 is the pre-sprint batch planning view.
- M105 reconciles batch results, evidence, queue state, and documentation drift after operator-run work.

## M103 AresForge Self-Managed Project Seed Review

Status: Completed locally on `main` after validation.

Queue item: `m103-aresforge-self-managed-project-seed-review`.

Implementation commit: `f1b32ca`.

Purpose:

- review the AresForge self-managed project seed
- confirm `aresforge` is selected as active project and registered as a managed project
- report repo path, branch, active milestone, queue counts, next recommended item, docs, warnings, and gaps
- keep the report local-only and read-only
- prepare coherent self-management input for M104 batch planning

Runnable operator surface:

- `python -m aresforge inspect-self-managed-project --project-id aresforge`
- `python -m aresforge inspect-self-managed-project --project-id aresforge --format json`

Constraints preserved:

- no GitHub API, `gh`, network, external-agent, Codex, Ollama, local LLM, documentation-agent, patch application, queue mutation, registry mutation, or automatic next-item execution
- docs/data corrections may be made only when clearly local and safe
- warnings and gaps are reported rather than auto-fixed

M104 relationship:

- M103 is the seed review and readiness lens.
- M104 is expected to use this review before planning a self-managed batch.

## M102 Queue Dependency and Completion Locking Hardening

Status: Completed locally on `main` after validation.

Queue item: `m102-queue-dependency-and-completion-locking-hardening`.

Implementation commit: `ea1d719`.

Purpose:

- harden local queue dependency sequencing for starts and completions
- add explicit completion evidence requirements with `completion_requires` and `evidence_required`
- preserve existing completed historical queue items
- expose queue consistency and lock status through a read-only local inspection command
- ensure M101 approval gates cannot bypass queue locks

Runnable operator surface:

- `python -m aresforge inspect-queue-consistency --project-id aresforge`
- `python -m aresforge inspect-queue-consistency --project-id aresforge --format json`

Constraints preserved:

- start is blocked by unresolved dependencies or blockers
- completion is blocked by unresolved dependencies
- completion is blocked by missing explicit evidence requirements
- blocking reasons are JSON-serializable and visible in readiness/completion/consistency outputs
- historical completed items remain valid unless future work explicitly adds new requirements to them
- no Codex, Ollama, local LLM, documentation-agent, external-agent, GitHub API, `gh`, network, workflow, issue creation, patch application, queue bypass, or automatic next-item execution occurs

Future relationship:

- future dispatch workflows must satisfy M102 dependency and evidence locks before they can request or consume any separate execution approval
- M103+ work can build on the consistency view rather than re-deriving lock state ad hoc

## M101 Human Approval Gate UI/Data Contract

Status: Completed locally on `main` after validation.

Queue item: `m101-human-approval-gate-ui-data-contract`.

Implementation commit: `da90ed3`.

Purpose:

- define local approval records for Codex dispatch artifacts, local LLM advisory/draft artifacts, documentation dry-runs, and future patch gates
- record operator review notes, checklist, reviewer, artifact metadata, dispatch lane, and approval status
- expose CLI create/read/update commands plus a read-only Hub review panel
- preserve `execution_allowed=false` for every approval status
- ensure approval is a prerequisite data record for future workflows, not an execution trigger

Supported statuses:

- `pending_review`
- `approved_for_manual_handoff`
- `rejected`
- `needs_revision`

Constraints preserved:

- approval records are local-only file-backed data under `.aresforge/dispatch_approval_gates.json`
- invalid statuses are blocked
- `approved_for_manual_handoff` permits manual operator handoff review only
- no Codex, Ollama, local LLM, documentation-agent, external-agent, GitHub API, `gh`, network, workflow, issue creation, patch application, queue completion, or next-item execution occurs

Operator workflow:

- generate or inspect a dispatch artifact or dry-run output
- create a dispatch approval gate for the item and artifact type
- review checklist and notes locally
- update status to `approved_for_manual_handoff`, `rejected`, or `needs_revision`
- keep future execution blocked until later milestones add separate locking and execution checks

M102 relationship:

- M101 records human approval state.
- M102 hardens queue dependency and completion locks so approval state cannot bypass readiness, active-item, evidence, or completion constraints.

## M100 Documentation Agent Dry-Run Review Workflow

Status: Completed locally on `main` after validation.

Queue item: `m100-documentation-agent-dry-run-review-workflow`.

Implementation commit: `bc05476`.

Purpose:

- consume or derive the M97 queue-to-agent dispatch plan
- validate future documentation-agent dry-run readiness only for `documentation_agent_dry_run`
- produce structured dry-run output for source-doc review, expected updates, stale-doc checks, reconciliation scope, operator gates, and validation expectations
- support readable console output, JSON output, and optional local file output
- preserve manual/operator-gated approval before any future documentation-agent apply or documentation mutation path

Constraints preserved:

- `local_only` remains true and `execution_allowed` remains false
- non-documentation-agent lanes are blocked with clear reasons
- blocked M97 plans, non-local plans, or execution-allowed plans cannot be marked ready
- no documentation-agent execution, documentation mutation, local LLM, Codex, external-agent, GitHub API, `gh`, network, workflow, issue creation, patch application, queue completion, or next-item execution occurs

Operator workflow:

- inspect M97 dispatch plan
- validate documentation-agent dry-run
- review source docs, stale-doc checks, expected updates, and reconciliation scope locally
- approve future documentation apply only through a later human approval gate milestone
- return any later documentation changes to the existing queue evidence process

## M99 Local LLM Advisory Execution Dry-Run Validator

Status: Completed locally on `main` after validation.

Queue item: `m99-local-llm-advisory-dry-run-validator`.

Implementation commit: `b04e868`.

Purpose:

- consume or derive the M97 queue-to-agent dispatch plan
- validate future local LLM advisory readiness only for `local_llm_advisory`
- produce structured dry-run output for M100+ style future artifact/run preparation
- support readable console output, JSON output, and optional local file output
- preserve manual/operator-gated approval before any future local LLM advisory artifact or run

Constraints preserved:

- `local_only` remains true and `execution_allowed` remains false
- non-advisory lanes are blocked with clear reasons
- blocked M97 plans, non-local plans, or execution-allowed plans cannot be marked ready
- no Ollama API call, local model execution, Codex execution, documentation-agent execution, external-agent execution, GitHub API, `gh`, network, workflow, issue creation, patch application, queue completion, or next-item execution occurs

Operator workflow:

- inspect M97 dispatch plan
- validate local LLM advisory dry-run
- review the dry-run output locally
- approve future advisory artifact/run only in a later milestone
- return any later advisory results to the existing queue evidence process

## M98 Codex Prompt Dispatch Artifact Generator v1

Status: Completed locally on `main`.

Queue item: `m98-codex-prompt-dispatch-artifact-generator`.

Implementation commit: `80f64dd`.

Purpose:

- consume or derive the M97 queue-to-agent dispatch plan
- generate a copy/paste-ready Codex prompt artifact only for `codex_prompt_artifact`
- support readable console output, JSON output, and optional local file output
- preserve manual/operator-gated review before any Codex session

Constraints preserved:

- `local_only` remains true and `execution_allowed` remains false
- non-Codex lanes are blocked with clear reasons and no prompt text
- blocked M97 plans, non-local plans, or execution-allowed plans cannot generate artifacts
- no Codex, Ollama, local LLM, documentation-agent, external-agent, GitHub API, `gh`, network, workflow, issue creation, patch application, queue completion, or next-item execution occurs

Operator workflow:

- inspect M97 dispatch plan
- generate M98 Codex prompt artifact
- review the prompt artifact locally
- manually copy/paste into Codex only after approval
- return final Codex results to the existing queue completion evidence process

## M97 Queue-to-Agent Dispatch Plan Contract

Status: Completed locally on `main`.

Queue item: `m97-queue-to-agent-dispatch-plan-contract`.

Implementation commit: `4ec0500`.

Purpose:

- inspect one local queue item and produce a safe advisory dispatch plan
- select a future handling lane with routing confidence and a short reason
- describe planned artifact intent without generating the full Codex prompt
- list approval gates and blocked reasons before any future dispatch can occur

Supported lanes:

- `codex_prompt_artifact`
- `local_llm_advisory`
- `local_llm_coding_draft`
- `documentation_agent_dry_run`
- `human_only_manual`

Constraints preserved:

- M97 is plan/contract/inspection only
- `local_only` is true and `execution_allowed` is false
- no Codex, Ollama, local LLM, documentation-agent, external-agent, GitHub API, `gh`, network, workflow, patch-apply, queue-completion, or next-item execution occurs
- M98 is the next artifact milestone for generating local Codex prompt dispatch artifacts from reviewed M97 plans

## M96 Post-Sprint Planning and Prioritization

Status: Proposed in the local queue; retained as planning context.

Queue item: `m96-post-sprint-planning-and-prioritization`.

Purpose:

- review final M81-M95 reports, queue state, source-of-truth docs, and generated handoff output
- identify mismatches, stale claims, undocumented warnings, and next-step gaps
- seed a clean next milestone batch plan without starting implementation work

Findings:

- M81-M95 are complete in local queue evidence.
- M96 did not exist in the queue before this pass and was seeded as a local-only planning item.
- The sprint batch report had no next proposed/ready milestone, so roadmap planning needed a new explicit batch.
- Recovered M80 dispatch runs remain audited as non-blocking warnings and should stay visible in handoff/report review.
- The generated handoff package remains read-only and useful for continuity, but its prose summary can lag when current phase/goal headings are stale.

Constraints preserved:

- no new implementation features
- no GitHub API, `gh`, GitHub mutation, issues, PRs, workflows, or external workflow execution
- no Codex CLI dispatch, Ollama generation, local LLM inference, or unsupervised agent execution
- no automatic generated-output application, queue completion, or next-item execution

## Planned Milestone Sequence

### M96 Post-Sprint Planning and Prioritization

Status: Proposed.

Current local planning and reconciliation milestone. M96 should close only after the source-of-truth docs, queue state, smoke checks, and next planned batch are reviewed.

### M97 Queue-to-Agent Dispatch Plan Contract

Status: Completed locally.

Define a queue-to-agent dispatch plan payload that maps a selected queue item to advisory lane, required operator gates, artifact expectations, validation burden, and blocked execution states. This should be a contract and inspection surface only.

### M98 Codex Prompt Dispatch Artifact Generator v1

Status: Completed locally.

Generate local Codex prompt dispatch artifacts from queue items and M97 plans without invoking Codex. Artifacts are reviewable, manual/operator-gated, clearly marked non-executing, and blocked for non-Codex lanes.

### M99 Local LLM Advisory Execution Dry-Run Validator

Status: Completed locally.

Validate local LLM advisory run readiness without invoking a provider by consuming the M97 dispatch plan, requiring `local_llm_advisory`, preserving `execution_allowed=false`, blocking every other lane, and reporting operator gates for a future milestone.

### M100 Documentation Agent Dry-Run Review Workflow

Status: Completed locally.

Add a dry-run review workflow for documentation reconciliation plans that verifies selected docs, expected updates, stale sections, scope, and operator review requirements without rewriting documentation automatically.

### M101 Human Approval Gate UI/Data Contract

Status: Completed locally.

Define the data contract and Hub read surface for human approvals across Codex dispatch artifacts, local LLM advisory/draft artifacts, documentation plans, and future patch gates. This remains a UI/data contract, not an apply path.

### M102 Queue Dependency and Completion Locking Hardening

Status: Planned.

Harden dependency, active-item, completion, and evidence-lock behavior so operator batch workflows cannot accidentally advance dependent or incomplete work.

### M103 AresForge Self-Managed Project Seed Review

Status: Planned.

Review the self-managed AresForge seed, local project state, stale handoff summary inputs, queue conventions, and registry metadata before wider self-management workflows.

### M104 Operator Batch Planner v1

Status: Planned.

Plan a small operator-selected batch from local queue state, dependencies, and validation burden while preserving one-item-at-a-time execution and explicit approval gates.

### M105 Post-M96 Documentation Reconciliation

Status: Planned.

Reconcile source-of-truth docs after M97-M104 so contracts, local-only boundaries, queue state, and operator instructions remain aligned.

## M95 Final Overnight Sprint Reconciliation

Status: Completed locally on `main`.

Implementation commit: `21008e644bc433e820bd30346da23b422db43e8c`.

Purpose:

- reconcile source-of-truth docs and local queue state after the overnight sprint
- make the completed M81-M95 posture clear for a future operator or chat handoff
- identify the next recommended milestone without seeding or starting it automatically

Delivered scope:

- source-of-truth documentation alignment for M81-M95
- roadmap/current-state alignment with completed local LLM, routing, documentation agent, handoff, and sprint report work
- confirmation that no runtime features are introduced by this cleanup milestone

Completed overnight sprint themes:

- M81-M88: local LLM advisory/coding safety model, local Ollama provider/health inspection, advisory artifacts, routing confidence, coding draft artifacts, and human-gated patch application contract
- M89-M90: local model usage reporting and read-only Hub routing dashboard data
- M91-M92: Documentation Agent v1 and deterministic documentation reconciliation planning
- M93-M94: operator handoff package v2 and overnight sprint batch reporting

Next recommended milestone:

- M96 post-sprint planning and prioritization, to be seeded manually after operator review of M95 evidence, the handoff package, and the sprint batch report

Constraints preserved:

- no GitHub API, `gh`, GitHub mutation, or external workflow execution
- no Codex execution, local LLM invocation, or automatic generated-output application
- no automatic queue completion or next-item execution

## M94 Overnight Sprint Batch Report

Status: Completed locally on `main`.

Implementation commit: `ed8cc6df00fa7ffc5199b95aa9a72fd468a070b0`.

Purpose:

- summarize an overnight sprint batch from local commits, queue evidence, validation records, and dispatch run history
- give the next operator a compact read-only view of what completed and what remains

Delivered scope:

- `inspect-sprint-batch-report`
- commit window selection by `--since-commit` or `--commit-count`
- queue completion/evidence summary, test summary, dispatch/recovered run summary, queue posture, unresolved warnings, and next recommended milestone

Constraints preserved:

- no GitHub API, `gh`, GitHub mutation, or external workflow execution
- no Codex execution or local LLM invocation
- no automatic queue completion or next-item execution

## M93 Operator Handoff Package v2

Status: Completed locally on `main`.

Purpose:

- improve local operator/chat continuation from the current repo and queue state
- make safe next actions and continuation commands explicit without executing anything

Delivered scope:

- `generate-handoff-package` v2 payload fields
- current HEAD, recent commits, queue summary, active/ready items, recovered dispatch summary, model routing summary, known warnings, safe command suggestions, and next safe actions
- read-only default with explicit local artifact writing only through `--output`

Constraints preserved:

- no Codex execution, local LLM invocation, or model routing execution
- no GitHub API, `gh`, GitHub mutation, issues, PRs, workflows, daemon, watcher, scheduler, or external workflow execution
- no automatic queue completion or next-item execution

## M92 Documentation Reconciliation Plan Generator

Status: Completed locally on `main`.

Purpose:

- generate a local-only documentation reconciliation plan from source-of-truth docs and queue state
- make stale documentation sections and recommended updates visible without rewriting docs automatically

Delivered scope:

- expanded `plan-doc-reconciliation`
- deterministic plan payload with source docs, changed source docs, queue items, recent local commits, stale section signals, recommended updates, and safety boundaries
- explicit local artifact write only through `--output`

Constraints preserved:

- no local LLM or Codex invocation
- no automatic documentation mutation
- no automatic queue completion or next-item execution
- no GitHub API, `gh`, issues, PRs, workflows, daemon, watcher, scheduler, external workflow execution, or GitHub mutation

## M91 Documentation Agent v1 Contract

Status: Completed locally on `main`.

Purpose:

- define Documentation Agent v1 as a local-only source-of-truth documentation reconciliation contract
- prepare future gated automation for documentation updates after validated changes

Delivered scope:

- `inspect-documentation-agent-contract`
- `docs/architecture/DOCUMENTATION_AGENT_CONTRACT.md`
- source docs, evidence requirements, non-mutating plan mode, and future gated apply mode

Constraints preserved:

- no automatic documentation updates from model output
- no apply mode until a future explicit operator gate exists
- no automatic queue completion or next-item execution
- no GitHub API, `gh`, issues, PRs, workflows, daemon, watcher, scheduler, external workflow execution, or GitHub mutation

## M90 Hub Routing Dashboard Data Contract

Status: Completed locally on `main`.

Purpose:

- expose routing and model decision information through a read-only Hub/API contract
- provide stable dashboard data before full UI polish

Delivered scope:

- `GET /api/local-queue/routing-dashboard`
- queue item routing decision rows with risk, task size, recommended engine/lane/model, confidence score, validation burden, warnings, and blockers
- summary counts by status, risk, task size, engine, and lane
- safety metadata confirming read-only/no-execution behavior

Constraints preserved:

- no mutation endpoints
- no prompt execution, local LLM invocation, Codex invocation, automatic queue completion, or next-item execution
- no GitHub API, `gh`, issues, PRs, workflows, daemon, watcher, scheduler, external workflow execution, or GitHub mutation

## M89 Model Usage and Token Accounting Report

Status: Completed locally on `main`.

Purpose:

- summarize local model usage and token accounting for future routing and cost decisions
- make missing usage metadata and extraction errors visible for operator review

Delivered scope:

- `inspect-model-usage-report`
- Codex dispatch run state usage summary
- available and unavailable token usage accounting
- model/provider/reasoning effort metadata when present
- local LLM advisory and coding draft metadata summaries

Constraints preserved:

- read-only by default with optional explicit local report artifact output
- no network calls or provider invocation
- no automatic queue completion or next-item execution
- no GitHub API, `gh`, issues, PRs, workflows, daemon, watcher, scheduler, external workflow execution, or GitHub mutation

## M88 Human-Gated Patch Application Contract

Status: Completed locally on `main`.

Purpose:

- define how generated local coding draft patch artifacts may be reviewed for future manual application
- require explicit operator approval and validation gates before any patch application path can exist

Delivered scope:

- `inspect-human-gated-patch-application-contract`
- patch artifact structure for local draft patches or operator instructions
- operator approval record requirements
- pre-apply safety gates and post-apply validation requirements

Constraints preserved:

- contract-first and dry-run only
- no automatic file mutation or patch application
- no automatic queue completion or next-item execution
- no GitHub API, `gh`, issues, PRs, workflows, daemon, watcher, scheduler, external workflow execution, or GitHub mutation

## M87 Local Coding Draft Artifact Mode

Status: Completed locally on `main`.

Purpose:

- add local coding draft artifacts for local LLM-generated patch or implementation guidance
- keep draft output non-applied, non-authoritative, and manual-review-only

Delivered scope:

- `prepare-local-coding-draft`
- local coding draft prompt artifacts
- optional explicit local Ollama draft output artifacts
- safety metadata proving no automatic file mutation or patch application

Constraints preserved:

- no automatic file mutation
- no automatic patch application
- no automatic queue completion or next-item execution
- no GitHub API, `gh`, issues, PRs, workflows, daemon, watcher, scheduler, external workflow execution, or GitHub mutation

## M86 Routing Confidence Scoring

Status: Completed locally on `main`.

Purpose:

- add deterministic confidence scoring to the M80 advisory decision matrix
- make Codex, local LLM advisory, local coding draft, and manual-only routing confidence visible for operator review

Delivered scope:

- `routing_confidence` in `inspect-llm-decision-matrix`
- lane scores, selected score, confidence level, rationale, warnings, and factors
- scoring factors for risk, task size, work mode, item type, dependencies, validation burden, provider/model availability, and recovery history

Constraints preserved:

- advisory scoring only
- no prompt execution or model invocation
- no automatic queue mutation or next-item execution
- no GitHub API, `gh`, issues, PRs, workflows, daemon, watcher, scheduler, external workflow execution, or GitHub mutation

## M85 Local LLM Advisory Run Artifact

Status: Completed locally on `main`.

Purpose:

- add local advisory prompt and run artifact flow for local LLM guidance
- allow optional explicit local advisory output while preventing automatic repo or queue mutation

Delivered scope:

- `prepare-local-llm-advisory-run`
- local advisory prompt artifacts
- optional explicit local Ollama advisory response and metadata artifacts
- safe unavailable status when the local provider cannot produce advisory output

Constraints preserved:

- no auto-apply of code or model output
- no automatic queue completion
- no automatic next-item execution
- no GitHub API, `gh`, issues, PRs, workflows, daemon, watcher, scheduler, external workflow execution, or GitHub mutation

## M84 Ollama Health Check and Model Inspection

Status: Completed locally on `main`.

Purpose:

- add a local-only Ollama health/model inspection path
- report provider reachability and visible models without requiring Ollama availability for normal test or project readiness success

Delivered scope:

- `test-ollama` health/model inspection without generation
- `inspect-ollama-health`
- stable status fields for availability, provider, endpoint, visible models, error summary, and next safe action
- graceful offline handling for local operator review

Constraints preserved:

- no model generation, chat, completion, or prompt execution
- no repo/source mutation or queue mutation from provider output
- no automatic next-item execution
- no GitHub API, `gh`, issues, PRs, workflows, daemon, watcher, scheduler, external workflow execution, or GitHub mutation

## M83 Local LLM Provider Contract

Status: Completed locally on `main`.

Purpose:

- define the local-only provider contract used by advisory and future coding lanes
- make Ollama the initial provider target without adding implicit provider calls or prompt execution

Delivered scope:

- `inspect-local-llm-provider-contract`
- structured provider URL, timeout, health-check, model identifier, role/capability, and safety-boundary metadata
- separate contract entries for local reasoning, local coding, and fallback model fields

Constraints preserved:

- no provider invocation from contract inspection
- no real Ollama dependency in tests
- no repo/source mutation or queue mutation from provider output
- no automatic prompt execution or automatic next-item execution
- no GitHub API, `gh`, issues, PRs, workflows, daemon, watcher, scheduler, external workflow execution, or GitHub mutation

## M82 Self-Managed AresForge Test Run

Status: Completed locally on `main`.

Purpose:

- dogfood AresForge against its own managed project registry, local queue, readiness checks, advisory routing, dispatch readiness, recovery semantics, and operator review evidence
- keep the milestone validation-focused, local-only, read-only except for explicit queue evidence closeout

Delivered scope:

- `inspect-local-project-report` includes a deterministic `self_managed_readiness_summary`
- the summary exposes AresForge project registration, active-project state, local queue counts, M81/M82 statuses, recovered dispatch run accounting, and required smoke commands
- tests cover recovered failed dispatch runs as non-blocking for self-managed readiness when upstream completion evidence is present

Constraints preserved:

- no automatic next-item execution
- no unattended multi-item execution
- no repo/source mutation or queue mutation from report output
- no GitHub API, `gh`, issues, PRs, workflows, daemon, watcher, scheduler, external workflow execution, or GitHub mutation

## M81 Local LLM Advisory/Coding Lane Prototype

Status: Completed locally on `main`.

Purpose:

- prototype a local LLM advisory/coding lane as read-only readiness and structured advisory planning
- keep local LLM usage advisory-first before any coding-output application path exists
- reuse M80 decision matrix concepts and local provider/model registry metadata

Delivered scope:

- `inspect-local-llm-advisory-lane-readiness`
- structured advisory plan output for local reasoning/coding advisory work
- explicit safety boundary fields blocking provider invocation, prompt dispatch, repo mutation, queue mutation, queue completion, GitHub/`gh`, workflows, and automatic next-item execution

Constraints preserved:

- no automatic local LLM invocation
- no automatic repo mutation from local LLM output
- no automatic queue completion or next-item execution
- no GitHub API, `gh`, issues, PRs, workflows, external workflow execution, or GitHub mutation

Next recommended milestone:

- M82 Self-Managed AresForge Test Run after M81 evidence review.

## M79.4 Codex Dispatch Recovery and Windows argv Hardening

Status: In progress locally on `main`.

Purpose:

- harden operator recovery after partial Codex dispatch failures
- provide an explicit local command to mark a named run recovery-required without queue completion
- improve Windows command string argv parsing while preserving `--command-arg` as the safest operator path

Delivered scope:

- `recover-codex-dispatch-run`
- recovery metadata in dispatch run state
- Windows-aware command string normalization for dispatch and validation command execution

Constraints preserved:

- no automatic prompt dispatch
- no automatic queue completion
- no automatic next-item execution
- no local LLM execution expansion
- no GitHub API, `gh`, issues, PRs, workflows, external workflow execution, or GitHub mutation

Next recommended milestone:

- M79.4 evidence review and queue closeout only by explicit operator action.

## M80 LLM Decision Matrix v2

Status: In progress locally on `main`.

Purpose:

- define advisory routing logic for Local LLM vs Codex, coding vs reasoning, model/profile selection, task size, risk, validation burden, and safety gating
- make the routing decision visible in Prompt Builder and workflow preparation payloads without adding execution behavior

Delivered scope:

- `inspect-llm-decision-matrix`
- decision payload fields for work mode, task sizing, risk classification, engine/lane recommendation, model/profile selection, validation burden, and safety gates
- Prompt Builder and `prepare-queue-item-dispatch` decision matrix embedding

Constraints preserved:

- no automatic prompt dispatch
- no Codex call or local LLM invocation
- no queue/source mutation from the decision matrix
- no automatic queue completion or next-item execution
- no GitHub API, `gh`, issues, PRs, workflows, external workflow execution, or GitHub mutation

Next recommended milestone:

- M81 Local LLM Advisory/Coding Lane Prototype after M80 validation and evidence review.

## M79.3 Codex Run Token Usage Capture

Status: In progress locally on `main`.

Purpose:

- capture comparable Codex CLI token usage metadata for future routing, cost analysis, and LLM decision matrix work
- keep accounting local to the operator-gated dispatch run state

Delivered scope:

- parser support for the Codex CLI transcript footer:
  - `tokens used`
  - numeric total on the following line, including comma-separated values
- `token_usage` stored in Codex dispatch `run_state.json`
- `inspect-codex-dispatch-run` returns `token_usage`
- old run states without `token_usage` still inspect successfully

Constraints preserved:

- no automatic queue completion
- no automatic next-item execution
- no Prompt Builder execution
- no local LLM execution expansion
- no GitHub API, `gh`, issues, PRs, workflows, external workflow execution, or GitHub mutation

Next recommended milestone:

- M79.3 review and evidence capture only; do not start M80 automatically.

## M79.2 Single-Item Ready-to-Codex Automation

Status: In progress locally on `main`.

Purpose:

- add one explicit local operator command that can process exactly one manually ready queue item through prompt preparation, approved Codex dispatch, validation, commit/push, queue evidence capture, and queue evidence commit/push
- preserve the one-item boundary and avoid any automatic next-item execution

Delivered scope:

- `run-single-ready-codex-queue-item`
- fail-safe ready-item selection for zero, multiple, explicit not-ready, Codex failure, validation failure, and commit/push failure states
- local recovery evidence capture when the workflow starts but cannot complete
- targeted tests for selection, dispatch, validation, git failure, CLI wiring, and next-item non-execution

Constraints preserved:

- explicit command only; no background watcher or daemon
- no prompt dispatch from Prompt Builder itself
- Codex dispatch requires the M78 approval phrase
- no local LLM execution expansion
- no GitHub API, `gh`, issues, PRs, workflows, external workflow execution, or GitHub mutation
- no automatic queue completion outside this explicit workflow
- no automatic next-item execution

Next recommended milestone:

- M79.3 only after explicit operator review and queue action.

## M79.1 Codex CLI Windows Runner Hardening

Status: In progress locally on `main`.

Purpose:

- harden the post-M79 Codex CLI runner path for Windows operator workflows
- make dispatch run-state reads tolerant of UTF-8 BOMs
- make subprocess output capture resilient to Unicode decoding edge cases
- pass the full reviewed prompt artifact to the dispatch subprocess over stdin
- document current Codex sandbox Git limitations where operator commit/push may be required

Constraints preserved:

- explicit operator approval remains required before Codex dispatch
- one active dispatch run at a time
- no automatic queue completion
- no automatic next-item execution
- no GitHub API, `gh`, issues, PRs, workflows, external workflow execution, or GitHub mutation from AresForge
- no local LLM execution expansion

Next recommended milestone:

- complete M79.1 validation/evidence capture, then proceed only by explicit operator queue action.

## M78.5 Operator Workflow Compression and Prompt Builder Agent Contract

Status: Completed locally on `main`.

Purpose:

- insert a workflow-compression milestone between M78 and M79
- turn queue item context, routing metadata, source-of-truth reading, safety gates, validation commands, smoke checks, and final-response requirements into a reviewed prompt artifact
- reduce manual prompt rewriting after M77/M78 without adding autonomous execution

Delivered scope:

- Prompt Builder Agent / Prompt Architect Agent contract
- `prepare-queue-item-dispatch` workflow preparation command
- explicit `--start-if-ready` gate for queue item start
- stable preparation payload fields for readiness, prompt artifact path, dispatch contract summary, approval requirement, blocked automatic execution, blocked queue completion, warnings, blockers, and next safe action

Constraints preserved:

- no automatic prompt dispatch
- no automatic Codex execution
- no automatic queue completion
- no automatic next-item execution
- no local LLM execution expansion
- no GitHub API, `gh`, issues, PRs, workflows, external workflow execution, or GitHub mutation

Next recommended milestone:

- M79 Queue Blocking and Sequencing Enforcement.

## M78 Operator-Gated Codex CLI Dispatch Prototype

Status: Completed locally on `main`.

Purpose:

- prototype one explicitly operator-approved Codex CLI dispatch for one local queue item
- build on the M77 dispatch contract
- track local run state and capture stdout/stderr without adding autonomous execution

Delivered scope:

- approval command with required phrase: `APPROVE CODEX DISPATCH`
- explicit dispatch command requiring an operator-provided command string
- inspect/list/cancel run commands
- local run-state records under `.aresforge/codex_dispatch/runs/<run_id>/`
- stdout, stderr, prompt artifact, and artifact directory capture
- targeted tests that use harmless Python commands or injected runners, not a real Codex install

Constraints preserved:

- one queue item at a time
- explicit operator approval required
- no automatic next-item execution
- no automatic queue item completion
- review evidence and validation evidence required before queue completion
- no GitHub API, `gh`, issues, PRs, workflows, external workflow execution, or GitHub mutation
- no local LLM execution expansion; local LLM remains local-only, advisory-only, operator-gated, prototype-scoped, and non-mutating

M78.5 follow-on note:

- The Prompt Builder Agent / Prompt Architect Agent now generates high-quality prompt artifacts for operator review from queue items, docs, routing metadata, model profiles, and safety gates. It must not execute prompts, call Codex, invoke local LLMs, mutate files, or advance queue items automatically.

Next recommended milestone:

- M79 Queue Blocking and Sequencing Enforcement.

## M77 Codex CLI Dispatch Contract

Status: Completed locally on `main`.

Purpose:

- define a local-only Codex CLI Dispatch Contract before any Codex CLI process invocation exists
- describe future single-item dispatch payloads, path reservations, run-state fields, audit fields, completion evidence fields, and safety gates
- keep M77 contract-first, dry-run/no-execute friendly, and operator-reviewable

Delivered scope:

- new local operator module for M77 dispatch contracts
- `inspect-codex-dispatch-contract`
- `prepare-codex-dispatch-dry-run`
- stable JSON contract payload with no-execute invariants
- future M78 run-state shape and allowed dispatch states
- targeted regression coverage for contract payload shape, safe missing/done/cancelled item behavior, managed project/repo binding inspection, path boundaries, command preview labels, and CLI output

Constraints preserved:

- no Codex CLI invocation
- no operator-approved Codex dispatch yet
- no automatic Codex execution
- no automatic agent execution
- no automatic queue execution
- no unattended multi-item execution
- no automatic next-item execution
- no local LLM execution expansion
- no GitHub API, `gh`, issues, PRs, workflows, or GitHub mutation
- local LLM remains local-only, advisory-only, operator-gated, prototype-scoped, and non-mutating

Next recommended milestone:

- M78 Operator-Gated Codex CLI Dispatch Prototype.

## M76 Self-Seed AresForge as the First Managed Project

Status: Completed locally on `main`.

Purpose:

- seed AresForge into its own local project registry and queue as the first managed self-project
- make the self-project inspectable as managed project `aresforge`
- register the primary local repo as `aresforge-main`
- create reviewable local queue items for M77 through M82

Scope boundary:

- local-only and file-backed
- idempotent on rerun
- proposed/reviewable queue items only
- no Codex CLI dispatch
- no agent execution
- no GitHub API, `gh`, GitHub issues, GitHub PRs, GitHub workflows, or GitHub mutation from the app
- no external workflow execution
- no unattended multi-item autonomous execution
- no local LLM execution expansion or local LLM repo mutation

Next recommended milestone after M76:

- M77 Codex CLI Dispatch Contract.

## M75 Source-of-Truth Documentation and Roadmap Reconciliation

Status: Completed on `main` in commit `7088204`.

Purpose:

- reconciled the major source-of-truth docs after M74
- documented the current local-first, file-backed, operator-gated, preview-only, review-only state
- prepared the next phase for self-management, future Codex CLI dispatch contracts, and future local LLM routing without adding execution behavior in M75

Scope boundary:

- documentation-only
- no Codex CLI dispatch
- no agent execution
- no GitHub API, `gh`, GitHub issues, GitHub PRs, GitHub workflows, or GitHub mutation from the app
- no external workflow execution
- no unattended multi-item autonomous execution
- no local LLM repo mutation

## M77 Codex CLI Dispatch Contract

Completed boundaries:

- contract-first and dry-run/no-execute friendly
- no Codex CLI process invocation
- no automatic queue execution
- no GitHub API, `gh`, issues, PRs, workflows, or GitHub mutation

Contract invariants:

- `dry_run_only: true`
- `dispatch_allowed: false`
- `codex_cli_invocation_allowed: false`
- `automatic_next_item_execution_allowed: false`
- `operator_approval_required: true`
- command preview is review-only and not executable in M77

## M78 Operator-Gated Codex CLI Dispatch Prototype

Purpose: prototype one explicitly operator-approved Codex CLI dispatch for one queue item.

Boundaries:

- one queue item at a time
- explicit operator approval required
- no automatic next-item execution
- run state, stdout/stderr/artifacts, errors, and completion states must be captured where applicable
- review evidence required before marking work complete
- no GitHub API, `gh`, issues, PRs, workflows, or GitHub mutation from the app

## M79 Queue Blocking and Sequencing Enforcement

Purpose: enforce queue/dependency blocking so dependent items cannot move forward until upstream LLM/Codex completion, review, validation, and evidence are recorded.

Boundaries:

- blocking/sequencing enforcement only
- no unattended multi-item execution
- no automatic next-item execution
- no GitHub or external workflow behavior

## M80 LLM Decision Matrix v2

Purpose: define routing/decision logic for local LLM vs Codex, coding vs reasoning, model/profile selection, task size, risk, validation burden, and safety gating.

Boundaries:

- decision/recommendation logic only unless a later milestone explicitly approves execution expansion
- operator-gated and auditable
- local LLM recommendations remain advisory and non-mutating
- Codex recommendations remain prompt-generation/operator-handoff unless an approved dispatch gate applies

## M81 Local LLM Advisory/Coding Lane Prototype

Purpose: extend local LLM lanes carefully, starting with local-only advisory/reasoning before any coding-output path.

Boundaries:

- local-only provider use
- advisory-only and prototype-scoped
- no automatic repo mutation from local LLM output
- no unattended execution
- coding-output paths require explicit future gates before any application to files

## M82 Self-Managed AresForge Test Run

Purpose: test the self-management loop using AresForge itself as the managed project.

Boundaries:

- operator-gated self-management only
- local validation required before commit/push
- review evidence required before marking queue items complete
- no GitHub API, `gh`, GitHub issues, GitHub PRs, GitHub workflows, or GitHub mutation from the app
- no unattended multi-item autonomous execution

## Next Phase Safety Gates

Before Codex dispatch can be implemented:

- explicit operator approval
- one item at a time
- no automatic next-item execution
- run state tracked
- stdout/stderr/artifacts captured where applicable
- error and completion states recorded
- review evidence required before marking complete
- queue/dependency blocking enforced
- local validation required before commit/push

## M74 Hub UX Stabilization Pass

Status: Completed locally on `main`.

Delivered scope:

- stabilized Hub Queue wording after the local AI operations sequence
- clarified local-only/operator-gated behavior for queue lifecycle controls, prompt previews, local LLM prototype/config status, AI Action Review Panel, audit log, artifact registry, and run-history surfaces
- improved prompt-pack preview/copy wording so copy/paste handoff cannot be mistaken for execution
- improved empty states for safety, blocked, artifact, audit, and review surfaces
- kept safety/gate/no-mutation metadata labels visible and scan-friendly

Constraints preserved:

- no new backend capability or execution control
- prompt-pack previews and AI review surfaces remain manual/operator handoff only
- no automatic execution, Codex execution, Codex CLI invocation, local LLM repo mutation, GitHub behavior, external workflow behavior, or repository mutation was introduced

Recommended next milestone:

- M75 - Source-of-Truth Documentation and Roadmap Reconciliation.

## M73 Prompt Pack Quality and Routing Improvements

Status: Completed locally on `main`.

Delivered scope:

- improved prompt-pack quality for queue items without adding execution behavior
- added routing-aware handoff guidance for high-value Codex, local LLM advisory, documentation/review, and operator-only/manual lanes
- added advisory model/engine recommendation metadata, task sizing language, validation expectations, smoke checks, and final response requirements to generated prompt packs
- made safety boundaries explicit in generated prompts, including no automatic execution, no GitHub API, no `gh`, no GitHub mutation, no Codex CLI execution unless a future approved milestone permits it, and no repo mutation from local LLM output
- kept generated prompt bodies copy/paste-friendly and free of nested markdown fences

Constraints preserved:

- generated prompt packs remain manual operator handoff artifacts only
- Codex high-value lane remains prompt-generation/operator-handoff only
- local LLM advisory lane remains advisory-only and cannot mutate repo files automatically
- no Codex/local LLM/agent execution, GitHub behavior, workflow behavior, external mutation, or repository mutation was introduced

Recommended next milestone:

- M74 - Hub UX Stabilization Pass.

## M72 Local LLM Provider Configuration Hardening

Status: Completed locally on `main`.

Delivered scope:

- hardened local LLM provider/model configuration without expanding execution behavior
- added clearer provider availability and configuration states for configured, missing configuration, unavailable, unsupported, disabled, and prototype-only mode
- added advisory provider/model profile metadata for local reasoning, local coding, and fallback model fields
- made fallback behavior explicit and non-automatic
- improved health-check payload wording so provider availability and model listing cannot be mistaken for execution approval

Constraints preserved:

- local LLM execution remains local-only, advisory-only, operator-gated, and prototype-scoped
- health checks remain explicit and do not send prompts or run inference
- no automatic local LLM execution, Codex execution, Codex CLI invocation, agent execution, GitHub API, `gh`, issue/PR/workflow behavior, external workflow execution, or repository mutation was introduced
- Codex high-value lane remains prompt-generation/operator-handoff only

Recommended next milestone:

- M73 - Prompt Pack Quality and Routing Improvements.

## M71 Operator-Facing AI Action Review Panel

Status: Completed locally on `main`.

Delivered scope:

- added an operator-facing Hub AI Action Review Panel for local AI-adjacent action review
- added read-only local API support via `GET /api/ai-action-review`
- exposed existing local AI safety, audit, artifact, run-history, and queue routing metadata in one place
- rendered safety status, gate status, blocked action, blocked reason category, blocked reason, no automatic execution, no repo mutation, artifact references, audit references, timeline entries, and next safe action labels
- added empty-state coverage for no recent AI actions, no artifacts found, no blocked actions found, and no audit entries found

Constraints preserved:

- review-only/read-only panel
- no execution controls
- no automatic agent execution, automatic Codex execution, Codex CLI execution, local LLM execution, GitHub API, `gh`, issue/PR/workflow behavior, external workflow execution, or repository mutation from the panel
- local LLM output remains local-only, advisory-only, operator-gated, and non-mutating
- Codex high-value lane remains prompt-generation/operator-handoff only

Recommended next milestone:

- M72 - Local LLM Provider Configuration Hardening.

## M70 Local AI Operations Verification Sweep

Status: Completed locally on `main`.

Delivered scope:

- verified the M58-M69 local AI operations chain across docs, safety gate payloads, execution audit entries, artifact registry records, Operator Run History, queue lifecycle responses, Hub API responses, and Hub UI rendering expectations
- reconciled stale latest-milestone and future-state wording now that M69 hardening is complete and M70 is the current verification milestone
- tightened blocked/policy wording for PR-shaped prohibited action names in the AI action safety gate
- surfaced existing safety/gate/non-mutation metadata in Operator Run History timeline rendering
- added targeted contract regressions for local AI docs, static Hub source boundaries, safety gate policy classification, advisory local LLM non-mutation, and run-history safety rendering

Constraints preserved:

- local LLM execution remains local-only, advisory-only, operator-gated, and prototype-scoped
- Codex high-value lane remains prompt-generation/operator-handoff only
- no GitHub API, no `gh`, no GitHub issues/PRs/workflow activity, no GitHub mutation from the app
- no automatic Codex execution, automatic agent execution, external workflow execution, or automatic repo mutation from local LLM/Codex output
- M70 was a verification and stabilization milestone, not a feature expansion

Recommended next milestone:

- M71 - Operator-Facing AI Action Review Panel.

## M69 Local AI Operations Hardening

Status: Completed locally on `main`.

Delivered scope:

- tightened AI-adjacent safety-gate reporting for blocked, preview-only, allowed, operator-gated, and override-required outcomes
- made blocked states more explicit with blocked action, blocked reason category, gate status, safety status, and next safe operator action
- aligned execution audit log, AI artifact registry, and Operator Run History payloads around consistent project/item/action/lane metadata and non-mutation flags
- added targeted regressions for prohibited automatic execution paths, blocked local LLM provider calls, non-mutating local LLM output, Codex prompt-only handoff behavior, and read-only history/artifact consistency

Constraints preserved:

- local LLM execution remains local-only, advisory-only, operator-gated, and prototype-scoped
- Codex high-value lane remains prompt-generation/operator-handoff only
- no GitHub API, no `gh`, no GitHub issues/PRs/workflow activity, no GitHub mutation from the app
- no automatic Codex execution, automatic agent execution, external workflow execution, or automatic repo mutation from local LLM/Codex output

Recommended next milestone:

- M70 completed Local AI Operations Verification Sweep.

## M68 Local AI Operations Closeout Reconciliation

Status: Completed locally on `main`.

Delivered scope:

- reconciled source-of-truth docs for the local AI operations sequence through M67
- clarified implemented workflows from project AI settings through Operator Run History
- clarified that routed queue views are filtered views over the one canonical local queue
- clarified that Codex high-value lane is prompt generation/operator handoff only
- clarified that local LLM execution remains prototype-only, local-only, advisory-only, and operator-gated
- confirmed validation coverage for queue, project factory, Hub API, and Hub UI contracts

Constraints preserved:

- no new execution behavior
- no Codex CLI execution
- no GitHub API, no `gh`, no GitHub issues/PRs/workflow activity, no GitHub mutation from the app
- no external workflow execution
- no expansion of M62 local LLM execution
- no automatic application of local LLM or Codex output to repo files

Recommended next milestone:

- M69 - Local AI Operations Hardening.

## M67 Operator Run History Panel

Status: Completed locally on `main`.

Delivered scope:

- added a local-only operator run history helper that combines audit entries and artifact records
- added read-only Hub API support for `GET /api/operator-run-history`
- added a minimal read-only Queue UI Operator Run History panel
- added newest-first timeline entries for audit and artifact events
- added targeted tests for empty state, combined timeline, sorting, project/item filters, API behavior, and UI contract references

Constraints preserved:

- no new execution capability
- no Codex CLI execution
- no GitHub API, no `gh`, no GitHub issues/PRs/workflow activity, no GitHub mutation from the app
- no external workflow execution
- no expansion of M62 local LLM execution
- run history panel is read-only and exposes no execution/apply/delete controls

Recommended next milestone:

- M68 - Local AI Operations Closeout Reconciliation.

## M66 AI Artifact Registry

Status: Completed locally on `main`.

Delivered scope:

- added local-only file-backed AI artifact registry at `.aresforge/ai_artifact_registry.json`
- added append/read/filter/verify operator helpers for artifact records
- added read-only Hub API support for `GET /api/ai-artifacts`
- added a minimal read-only Queue UI artifact registry panel
- registered artifact writes from prompt-pack generation, local LLM prompt previews, local LLM advisory result output, Codex high-value prompt generation, and local project handoff generation
- added targeted tests for registering, empty reads, filtering, missing artifacts, artifact-producing workflows, API route behavior, and UI contract references

Constraints preserved:

- no new execution capability
- no Codex CLI execution
- no GitHub API, no `gh`, no GitHub issues/PRs/workflow activity, no GitHub mutation from the app
- no external workflow execution
- no expansion of M62 local LLM execution
- artifact registry records metadata only and does not overwrite artifact files

Recommended next milestone:

- M67 - Operator Run History Panel.

## M65 AI Action Safety Gate

Status: Completed locally on `main`.

Delivered scope:

- added centralized local-only AI action safety gate decision helper
- added API support for `POST /api/ai-action-safety-gate`
- integrated gate output into M62 local LLM execution and M63 Codex high-value prompt generation
- added tests for preview-only decisions, missing operator gate, low-risk local execution allowance, high-risk override requirement, `codex_cli` local execution blocking, Codex/GitHub action blocking, routing metadata explicit action requirement, and API behavior

Constraints preserved:

- no new execution capability
- no Codex CLI execution
- no GitHub API, no `gh`, no GitHub issues/PRs/workflow activity, no GitHub mutation from the app
- no external workflow execution
- no expansion of M62 local LLM execution
- one canonical local queue remains the source of truth for item routing context

Recommended next milestone:

- M66 - AI Artifact Registry.

## M64 Execution Audit Log

Status: Completed locally on `main`.

Delivered scope:

- added a local-only execution audit log at `.aresforge/execution_audit_log.json`
- added append/read/filter operator helpers for audit entries
- added audit entries for health checks, prompt previews, local LLM dry runs/execution/blocked attempts, Codex high-value prompt generation, prompt-pack generation, and routing metadata updates
- added read-only Hub API support for `GET /api/execution-audit-log`
- added a minimal read-only Queue UI audit panel with simple filters
- added targeted tests for append/read/filter, redaction, dry-run and blocked local LLM attempts, Codex high-value prompt audit entries, API route behavior, and UI contract references

Constraints preserved:

- no new execution behavior
- no Codex CLI execution
- no GitHub API, no `gh`, no GitHub issues/PRs/workflow activity, no GitHub mutation from the app
- no external workflow execution
- no expansion of M62 local LLM execution
- audit entries avoid full prompt/response text and redact secret-like values

Recommended next milestone:

- M65 - AI Action Safety Gate.

## M63 Codex CLI High-Value Lane

Status: Completed locally on `main`.

Delivered scope:

- added a local-only Codex CLI high-value lane prompt generator
- added operator/API/UI support for `POST /api/local-queue/items/{item_id}/codex-high-value-prompt`
- generated Codex-ready prompts for eligible queue items without running Codex
- included operating rules, files to inspect, pre-checks, implementation goal, constraints, validation commands, smoke checks, `git diff --check`, commit/push-after-validation guidance, and required final response format
- supported optional local artifact output with safe non-overwrite behavior
- preserved one canonical local queue as the source of truth
- added targeted operator, API, and UI foundation tests

Eligibility:

- `recommended_engine=codex_cli`, `recommended_agent_lane=high_value_codex`, high/critical risk, high complexity, high validation burden, high-value affected areas, `codex_only`/`high_confidence`, or operator override

Constraints preserved:

- no automatic Codex execution
- no Codex CLI command execution from AresForge
- no GitHub API, no `gh`, no GitHub issues/PRs/workflow activity, no GitHub mutation from the app
- no repo mutation from Codex output
- local LLM execution remains operator-gated and unaffected
- Codex lane output is advisory/copy-paste/operator-controlled

Recommended next milestone:

- M64 - Execution Audit Log.

## M62 Operator-Gated Local LLM Execution Prototype

Status: Completed locally on `main`.

Delivered scope:

- added a conservative operator-gated local LLM execution prototype
- added operator/API/UI support for `POST /api/local-queue/items/{item_id}/local-llm-execute`
- enabled prototype execution configuration through `execution_enabled: true` while requiring `operator_gate_required: true`
- supports dry run without provider calls
- supports real execution only after prompt preview, explicit confirmation, local health/model availability, local-routed metadata, and local provider validation
- saves advisory local result artifacts only when explicitly requested
- added mocked tests so Ollama is not required

Constraints preserved:

- no Codex CLI execution
- no GitHub API, no `gh`, no GitHub issues/PRs/workflow activity, no GitHub mutation from the app
- no external/non-local LLM execution
- no automatic agent execution
- no automatic queue start, completion, closeout, commit, push, repo mutation, or workflow execution
- one canonical local queue remains the source of truth

Recommended next milestone:

- M63 - Codex CLI High-Value Lane.

## M61 Local LLM Prompt Preview

Status: Completed locally on `main`.

Delivered scope:

- added preview-only local LLM prompt generation for routed queue items
- added local operator/API/UI support for `POST /api/local-queue/items/{item_id}/local-llm-prompt-preview`
- included routing metadata, task details, local-only boundaries, validation expectations, and final response format in generated previews
- allowed optional local artifact output with safe non-overwrite behavior
- blocked local preview for `codex_cli` routes, unrouted items, missing local environment/model configuration, and `manual_only` policy without operator override
- added targeted operator, API, and UI foundation tests

Constraints preserved:

- no Ollama call
- no local LLM execution
- no model inference
- no Codex CLI execution
- no prompt execution
- no real agent execution
- no GitHub API, no `gh`, no GitHub issues/PRs/workflow activity, no GitHub mutation from the app
- no external workflow execution
- no queue storage split

Follow-up:

- M62 added Operator-Gated Local LLM Execution Prototype.

## M60 Codex CLI Model Profile Contract

Status: Completed locally on `main`.

Delivered scope:

- added local-only Codex CLI Model Profile Contract
- added file-backed read/update/validation helpers
- added Hub API support for `GET /api/codex-cli/model-profiles` and `POST /api/codex-cli/model-profiles`
- represented Codex CLI as engine `codex_cli`
- represented default, high-value, and fast model preferences
- represented allowed models plus optional per-project and per-agent allowed model mappings
- enforces `execution_enabled: false` for Codex CLI model profiles while `operator_gate_required` stays true
- added `docs/architecture/CODEX_CLI_MODEL_PROFILE_CONTRACT.md`
- added targeted tests for default state, valid updates, invalid engine key, invalid role models, execution rejection, model mapping validation, and API behavior

Constraints preserved:

- no Codex CLI execution
- no prompt execution
- no local LLM execution
- no real agent execution
- no GitHub API, no `gh`, no GitHub issues/PRs/workflow activity, no GitHub mutation from the app
- no external workflow execution
- no High-Value Codex Lane execution

Recommended next milestone:

- M63 - Codex CLI High-Value Lane.

## M59 Local LLM Health Check

Status: Completed locally on `main`.

Delivered scope:

- added explicitly invoked local LLM health-check helper
- added Hub route `POST /api/local-llm/health-check`
- health check reads the M58 local LLM environment contract
- provider `none` and `unknown` return unavailable/blocked status without provider calls
- provider `ollama` checks only local `/api/tags` model listing when configured with a local provider URL
- reports provider reachability, available models, configured model availability, `inference_tested: false`, and `execution_allowed: false`
- added mocked tests so Ollama is not required

Constraints preserved:

- no prompt execution
- no model inference
- no local LLM generation
- no Codex execution
- no real agent execution
- no GitHub API, no `gh`, no GitHub issues/PRs/workflow activity, no GitHub mutation from the app
- no generate/chat/completion endpoint calls
- no queue storage split or queue/project mutation

Follow-up:

- M61 added Local LLM Prompt Preview.
- M62 added Operator-Gated Local LLM Execution Prototype.

## M58 Local LLM Environment Contract

Status: Completed locally on `main`.

Delivered scope:

- added a local-only Local LLM Environment Contract
- added file-backed read/update/validation helpers
- added Hub API support for `GET /api/local-llm/environment` and `POST /api/local-llm/environment`
- documented supported providers: `ollama`, `none`, and `unknown`
- documented placeholder model configuration for future reasoning, coding, and fallback models
- originally enforced `execution_enabled: false`; M62 allows `execution_enabled: true` only for the operator-gated local prototype while `operator_gate_required` stays true
- added `docs/architecture/LOCAL_LLM_ENVIRONMENT_CONTRACT.md`
- added targeted tests for default state, valid Ollama configuration, provider none, invalid provider, execution rejection, invalid timeout/context, and API behavior

Constraints preserved:

- no Ollama call
- no health check yet
- no model API call
- no local LLM execution
- no prompt execution
- no routing execution
- no Codex execution
- no real agent execution
- no GitHub API, no `gh`, no GitHub issues/PRs/workflow activity, no GitHub mutation from the app
- no external workflow execution

Recommended next milestone:

- M59 - Local LLM Health Check.

## M57 Prompt Pack Routing Integration

Status: Completed locally on `main`.

Delivered scope:

- integrated M53 routing metadata into M43 local prompt-pack generation
- preserved existing prompt-pack generation and artifact output behavior
- added per-prompt routing metadata, routing guidance, dependencies, validation expectations, operating rules, final response template, and `execution_allowed: false`
- added optional prompt-pack grouping by routing metadata
- added local Hub API and Queue UI inputs for routing-aware prompt packs
- added tests for routed, unrouted, Codex-recommended, local-LLM-recommended, grouped, artifact non-overwrite, API, and UI behavior

Constraints preserved:

- prompt packs are local copy/paste artifacts/previews only
- no automatic routing apply
- no queue item start or completion
- no local LLM execution
- no Codex execution
- no real agent execution
- no GitHub API, no `gh`, no GitHub issues/PRs/workflow activity, no GitHub mutation from the app
- no external workflow execution
- no queue storage split

Recommended next milestone:

- M58 - Local LLM Environment Contract.

## M56 Routed Queue Views

Status: Completed locally on `main`.

Delivered scope:

- added local-only routed queue views over the canonical local queue
- added operator/API support for `GET /api/local-queue/routed-views`
- added a small read-only Queue UI panel for routed filters, grouped counts, and item summaries
- supported filters for project, status, agent lane, engine, model, fallback engine, risk, complexity, project policy, routing policy source, and operator override
- supported grouped views by agent lane, engine, model, project policy, risk level, complexity level, and status
- added targeted tests for mixed routed/unrouted items, filters, groups, empty queue behavior, canonical queue non-mutation, API behavior, and UI contract references

Constraints preserved:

- one canonical local queue remains the source of truth
- routed views are read-only and do not split queue storage
- no prompt-pack routing integration yet
- no local LLM execution
- no Codex execution
- no real agent execution
- no GitHub API, no `gh`, no GitHub issues/PRs/workflow activity, no GitHub mutation from the app
- no external workflow execution

Recommended next milestone:

- M57 - Prompt Pack Routing Integration.

## M55 Project AI Settings UI

Status: Completed locally on `main`.

Delivered scope:

- added Hub Projects UI for M51 Project AI Settings
- included controls for all supported project AI modes and engines
- included controls for default engine, optional default model, operator override, and notes
- wired load/save behavior to existing local-only M51 API routes
- displayed validation, warnings, blockers, and next safe action
- added targeted UI tests while preserving existing API/factory coverage

Constraints preserved:

- local-only, file-backed, operator-gated settings updates
- no routing execution
- no local LLM execution
- no Codex execution
- no real agent execution
- no GitHub API, no `gh`, no GitHub issues/PRs/workflow activity, no GitHub mutation from the app
- no complex model management UI

Recommended next milestone:

- M56 - Routed Queue Views.

## M54 Routing Decision Matrix v1

Status: Completed locally on `main`.

Delivered scope:

- added local-only Routing Decision Matrix v1 recommendation support
- used project AI settings, agent/engine registry, queue item classification, risk/complexity inputs, affected files, validation burden, and operator override context
- added explicit apply support that writes M53 routing metadata only when requested
- added Hub API support for recommendation preview and explicit apply
- added minimal Queue UI controls for recommendation preview and metadata apply
- added targeted tests for balanced, `codex_only`, `local_only`, `cost_saver`, `high_confidence`, and `manual_only` outcomes; non-writing previews; explicit apply; invalid item failure; API behavior; and UI references

Constraints preserved:

- recommendation-only behavior
- no local LLM execution
- no Codex execution
- no real agent execution
- no GitHub API, no `gh`, no GitHub issues/PRs/workflow activity, no GitHub mutation from the app
- no external workflow execution
- no queue storage split

Recommended next milestone:

- M55 - Project AI Settings UI.

## M53 Queue Routing Metadata Contract

Status: Completed locally on `main`.

Delivered scope:

- added local queue routing metadata contract support
- added default empty/unassigned routing metadata for new and legacy queue item views
- added a validation helper for supported lanes, engines, risk levels, complexity levels, and operator override shape
- added local metadata update helper and Hub API support for `POST /api/local-queue/items/{item_id}/routing-metadata`
- added minimal Queue detail display for routing metadata
- added targeted tests for defaults, legacy item handling, valid updates, invalid lanes/engines/risk/complexity, API success/failure, prompt-pack compatibility, evidence/closeout compatibility, and UI contract references

Constraints preserved:

- one canonical local queue remains the source of truth
- routing metadata is local-only, file-backed, and non-executing
- no routing decision matrix implementation yet
- no queue storage split
- no local LLM execution
- no Codex execution
- no real agent execution
- no GitHub API, no `gh`, no GitHub issues/PRs/workflow activity, no GitHub mutation from the app

Recommended next milestone:

- M54 - Routing Decision Matrix v1.

## M52 Agent and Engine Registry Contract

Status: Completed locally on `main`.

Delivered scope:

- added local-only read-only Agent and Engine Registry Contract support
- added Hub API support for `GET /api/agent-engine-registry`
- represented required future agent lanes and engines with stable keys
- represented Codex CLI as engine `codex_cli` with placeholder-only model profile strategy
- added targeted tests for registry loading, required lanes, required engines, non-execution flags, Codex CLI representation, and API success

Constraints preserved:

- registry is local-only, read-only, and non-executing
- no routing implementation or execution
- no queue routing metadata changes
- no local LLM execution
- no Codex execution
- no real agent execution
- no GitHub API, no `gh`, no GitHub issues/PRs/workflow activity, no GitHub mutation from the app

Recommended next milestone:

- M53 - Queue Routing Metadata Contract.

## M51 Project AI Settings Contract

Status: Completed locally on `main`.

Delivered scope:

- added local-only project AI settings contract support
- added file-backed settings storage under each project directory
- added validation for supported project modes and engine keys
- added Hub API support for `GET /api/projects/{project_id}/ai-settings` and `POST /api/projects/{project_id}/ai-settings`
- added targeted tests for defaults, successful update, invalid modes/engines, disabled defaults, mode-specific default restrictions, `manual_only`, and API failures

Constraints preserved:

- settings are local-only, file-backed, and non-executing
- no routing implementation or execution
- no queue routing metadata changes
- no local LLM execution
- no Codex execution
- no real agent execution
- no GitHub API, no `gh`, no GitHub issues/PRs/workflow activity, no GitHub mutation from the app

Recommended next milestone:

- M52 - Agent and Engine Registry Contract.

## M50 Handoff Generator

Status: Completed locally on `main`.

Delivered scope:

- added local-only handoff generator operator support
- added Hub API support for `POST /api/local-project/handoff`
- added a small Handoff UI panel for next milestone/instruction, include toggles, optional artifact output, force overwrite, summary, and copy/paste preview
- added targeted tests for handoff generation, operating rules content, queue/report/progress content, recommended next milestone/instruction, optional artifact writes, non-overwrite behavior, API route behavior, and UI contract references

Constraints preserved:

- local-only, file-backed, read-only unless optional local artifact output is requested
- no routing implementation or execution
- no local LLM execution
- no Codex execution
- no real agent execution
- no GitHub API, no `gh`, no GitHub issues/PRs/workflow activity, no GitHub mutation from the app

Recommended next milestone:

- M51 - Project AI Settings Contract.

## M49 Reports v1

Status: Completed locally on `main`.

Delivered scope:

- added local-only Reports v1 operator support
- added Hub API support for `GET /api/reports/local-projects`
- added a read-only Reports v1 panel to the existing Reports UI
- added targeted tests for operator success, empty state, status/type/lane count accuracy, active project summary, evidence/closeout counts, API route behavior, and UI contract references

Constraints preserved:

- Reports v1 is local-only, file-backed, and read-only
- no export/PDF/CSV expansion beyond existing in-page JSON text behavior
- no routing implementation or execution
- no local LLM execution
- no Codex execution
- no real agent execution
- no GitHub API, no `gh`, no GitHub issues/PRs/workflow activity, no GitHub mutation from the app

Recommended next milestone:

- M50 - Handoff Generator.

## M48 Project Progress Rollup

Status: Completed locally on `main`.

Delivered scope:

- added read-only local Project Progress Rollup support
- added Hub API support for `GET /api/projects/{project_id}/progress-rollup`
- added minimal Projects UI display for active project progress counts and next safe action
- added targeted tests for rollup success, empty queue/project state, status/type/lane counts, evidence and closeout counts, API success/failure, and UI contract references

Constraints preserved:

- rollup is local-only, file-backed, and read-only
- no Reports v1 implementation
- no routing implementation
- no local LLM execution
- no Codex execution
- no real agent execution
- no GitHub API, no `gh`, no GitHub issues/PRs/workflow activity, no GitHub mutation from the app

Recommended next milestone:

- M49 - Reports v1.

## M47 Queue Item Closeout Workflow

Status: Completed locally on `main`.

Delivered scope:

- added explicit local queue item closeout workflow
- added Hub API support for `POST /api/local-queue/items/{item_id}/closeout`
- added minimal Queue UI support for operator-gated closeout
- added targeted tests for successful closeout, missing item, missing evidence, ineligible status, required evidence fields, evidence preservation, API route behavior, and UI contract references

Constraints preserved:

- closeout is local-only and file-backed
- no routing implementation
- no local LLM execution
- no Codex execution
- no real agent execution
- no GitHub API, no `gh`, no GitHub issues/PRs/workflow activity, no GitHub mutation from the app

Recommended next milestone:

- M48 - Project Progress Rollup.

## M46 Completion Evidence Capture

Status: Completed locally on `main`.

Delivered scope:

- added local-only queue completion evidence capture
- added Hub API support for `POST /api/local-queue/items/{item_id}/evidence`
- added minimal Queue UI support for pasteable validation and evidence details
- added targeted tests for successful capture, safe failures, non-completion behavior, field preservation, API route behavior, and UI contract references

Constraints preserved:

- evidence capture is not closeout
- no automatic queue completion
- no routing implementation
- no local LLM execution
- no Codex execution
- no real agent execution
- no GitHub API, no `gh`, no GitHub issues/PRs/workflow activity, no GitHub mutation from the app

Recommended next milestone:

- M47 - Queue Item Closeout Workflow.

## M45 Local Hub End-to-End Operator Workflow Validation

Status: Completed locally on `main`.

Delivered scope:

- added focused end-to-end Hub operator workflow coverage
- validated dashboard summary, active project context, local queue intake, queue item detail, readiness inspection, prompt-pack generation, local project report, and local queue agent summary together
- confirmed M43 prompt-pack generation remains local-only and advisory
- confirmed prompt-pack generation does not automatically start or complete queue items

Constraints preserved:

- no routing implementation
- no local LLM execution
- no Codex execution
- no real agent execution
- no GitHub API, no `gh`, no GitHub issues/PRs/workflow activity, no GitHub mutation from the app
- no queue storage split

Recommended next milestone:

- M46 - completion evidence capture for local operator workflow closeout.

## M44A Agent LLM Routing Strategy Documentation Update

Status: Completed locally on `main`.

Delivered scope:

- added `docs/architecture/AGENT_LLM_ROUTING_STRATEGY.md` as the detailed source of truth for future Agent/LLM routing
- documented project-specific AI routing modes, agent lanes, future engines/models, routing decision hierarchy, routing metadata, routed queue views, and Codex CLI model strategy
- documented that future routing decisions should happen before prompt generation
- documented that M43 prompt packs remain local-only grouped prompts without LLM/model routing

Constraints preserved:

- documentation-only
- no backend routes
- no frontend settings UI
- no queue schema changes
- no runtime routing
- no Codex CLI execution
- no real agent execution
- no local LLM execution
- no model invocation
- no GitHub API, no `gh`, no GitHub issues/PRs/workflow activity, no GitHub mutation from the app

Recommended next milestone:

- M45 - next local-first routing/prompt-pack preparation milestone, scoped to advisory metadata/design validation before any execution path.

## M43 Agent Prompt Pack Generator

Status: Completed locally on `main`.

Delivered scope:

- added local operator prompt-pack generator for selected/eligible queue items
- added `POST /api/local-queue/prompt-pack` for operator-triggered local generation
- added Queue UI prompt-pack controls with summary and copy/paste preview/output path
- added operator/API/UI tests for stable prompt-pack shape and route behavior

Constraints preserved:

- prompt-pack generation only; no automatic execution behavior
- no queue auto-start or auto-complete
- no Codex execution, no agent execution, no LLM/model routing
- no GitHub API, no `gh`, no GitHub mutation, no external calls

## M42 Queue Item Detail Panel

Status: Completed locally on `main`.

Delivered scope:

- added Queue Item Detail Panel for read-only queue item inspection
- reused existing queue detail/readiness APIs
- surfaced M41 metadata context (requested outcome/acceptance/validation notes) in panel
- added empty/error/readiness-unavailable states

Constraints preserved:

- no new mutation actions introduced in detail panel
- no auto-start
- no auto prompt generation
- no GitHub/`gh` behavior
- no agent/Codex/LLM execution

## M41 Active Project Task Intake v2

Status: Completed locally on `main`.

Delivered scope:

- improved local Active Project intake UX for better queue item quality
- added structured intake fields (source, requested outcome, acceptance notes, validation notes)
- reused existing local intake endpoint (`POST /api/local-queue/items`) and queue model
- maintained backward compatibility and local-only behavior

Constraints preserved:

- no execution side effects
- no auto-start
- no auto prompt generation
- no GitHub/`gh` behavior
- no agent/Codex/LLM execution

## M40 Dashboard Milestone Closeout And Docs Reconciliation

Status: Completed locally on `main`.

Scope:

- source-of-truth documentation reconciliation after M35-M39 dashboard delivery
- validation baseline reconciliation for dashboard coverage
- no feature additions and no backend behavior changes

Closed-out dashboard capabilities:

- M35 dashboard summary data contract and `GET /api/dashboard/summary`
- M36 Home dashboard cards/status panels
- M37 manual refresh plus loading/empty/error states
- M38 Home dashboard deep links to existing sections
- M39 queue/advisory-lane drilldowns

Reconfirmed boundaries:

- local-only and file-backed
- operator-gated
- read-only/advisory dashboard experience
- no GitHub API/`gh`/GitHub mutation
- no real agent execution
- no Codex execution from Hub app
- no LLM/model routing or invocation

Dashboard closeout validation baseline:

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
## M36 Hub Dashboard UI Cards And Status Panels

Status: Completed locally on `main`.

Delivered M36 scope:

- Home now consumes `GET /api/dashboard/summary`
- read-only/advisory Home cards and status panels for project/queue/agent-lane/repo summaries
- blockers/warnings and next safe action surfaced in Home
- manual refresh retained without background polling

Constraints preserved:

- no GitHub calls
- no `gh`
- no mutation
- no agent/Codex/model execution
- no LLM/model routing

## M35 Hub Dashboard Data Contract And Read-Only Metrics

Status: Completed locally on `main`.

Delivered M35 scope:

- local-only read-only Home dashboard data contract
- operator-level summary aggregation for existing local project/queue/active-project state
- Hub route `GET /api/dashboard/summary` for stable JSON contract delivery

Constraints preserved:

- no GitHub calls
- no `gh`
- no mutation
- no agent/Codex/model execution

Deferred:

- dashboard UI cards and status panels move to M36.

## Future Milestone: Local LLM Readiness

Status: Planned.

Goal:

- document and validate local Ollama model readiness before wiring any model into AresForge workflows

Scope:

- confirm Ollama installation
- confirm selected model availability
- confirm `aresforge-coder-local` alias
- confirm `aresforge-reasoner-local` alias
- add read-only local model readiness inspection
- add local configuration records for model aliases and intended task routing
- add tests proving readiness inspection does not execute model prompts
- preserve operator-gated behavior

Non-goals:

- no live agent execution
- no autonomous command execution
- no GitHub API usage
- no cloud LLM fallback

## Future Milestone: Advisory LLM Task Routing

Status: Planned.

Goal:

- introduce advisory task routing that recommends either the coding model or reasoning model without automatically executing model calls

Scope:

- add routing metadata
- add model recommendation output
- add routing rationale
- add prompt artifact generation
- add operator approval gate before inference
- add tests proving routing is advisory only

Non-goals:

- no automated model execution
- no automated code application
- no autonomous commits or pushes

## M34 Frontend Modularization Closeout And Docs Reconciliation

Status: Completed locally on `main`.

Delivered M34 scope:

- reconciled source-of-truth docs with final Hub frontend module structure
- confirmed `src/aresforge/hub/static/app.js` remains the ES module entrypoint
- confirmed module split across core, section, and project-factory section modules
- reconfirmed validation/smoke baseline for the modularized frontend contract

Final frontend module structure:

- core:
  - `src/aresforge/hub/static/js/core/dom.js`
  - `src/aresforge/hub/static/js/core/http.js`
  - `src/aresforge/hub/static/js/core/state.js`
- sections:
  - `src/aresforge/hub/static/js/sections/home.js`
  - `src/aresforge/hub/static/js/sections/workspace.js`
  - `src/aresforge/hub/static/js/sections/queue.js`
  - `src/aresforge/hub/static/js/sections/projects.js`
  - `src/aresforge/hub/static/js/sections/repos.js`
  - `src/aresforge/hub/static/js/sections/reports.js`
  - `src/aresforge/hub/static/js/sections/orchestration.js`
  - `src/aresforge/hub/static/js/sections/escalation.js`
- project factory:
  - `src/aresforge/hub/static/js/sections/projectFactory/index.js`
  - `src/aresforge/hub/static/js/sections/projectFactory/scope.js`
  - `src/aresforge/hub/static/js/sections/projectFactory/architecture.js`
  - `src/aresforge/hub/static/js/sections/projectFactory/milestonePlan.js`
  - `src/aresforge/hub/static/js/sections/projectFactory/validation.js`
  - `src/aresforge/hub/static/js/sections/projectFactory/agentDispatch.js`
  - `src/aresforge/hub/static/js/sections/projectFactory/executionApproval.js`
  - `src/aresforge/hub/static/js/sections/projectFactory/closeout.js`

Validation baseline:

- `python -m pytest tests/test_hub_ui_foundation.py tests/test_hub_project_factory_api.py tests/test_hub_local_queue_lifecycle_api.py tests/test_hub_active_project_api.py tests/test_local_project_factory.py tests/test_local_active_project.py`
- smoke:
  - `python -m aresforge inspect-local-queue-agent-summary`
  - `python -m aresforge inspect-local-project-report`

Boundaries:

- local-first, file-backed, operator-gated
- no real agent execution
- no GitHub mutation
- no network execution beyond existing local Hub API behavior

## Next Recommended Milestone

### M35 - Hub Dashboard Data Contract And Read-Only Metrics

Planned scope:

- read-only Home dashboard metrics
- total projects
- active project summary
- queue item counts by status
- advisory agent lane counts from local summaries
- repo status summary from existing local inspection outputs

Constraints:

- no new GitHub calls
- no real agent execution
- no mutation

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

### M24 - Extract Home + Workspace Section Modules

Status: Completed locally on `main`.

Highlights:

- extracted Home dashboard rendering/loading plus Home-specific action binding into `src/aresforge/hub/static/js/sections/home.js`
- extracted Active Project Workspace rendering/loading, empty-state wiring, and quick actions into `src/aresforge/hub/static/js/sections/workspace.js`
- kept `src/aresforge/hub/static/app.js` as the frontend entrypoint and init/orchestration surface
- updated static tests to assert the new section modules exist, are imported by `app.js`, and do not duplicate workspace bindings

Safety posture:

- local-only refactor
- no GitHub API calls, no `gh` calls
- no new network behavior
- no agent or model execution
- no UI redesign and no DOM id or endpoint path changes

### M25 - Extract Hub Queue Section Module

Status: Completed locally on `main`.

Highlights:

- extracted Queue read-only summary rendering/loading and queue item card rendering into `src/aresforge/hub/static/js/sections/queue.js`
- extracted queue-only actions into `src/aresforge/hub/static/js/sections/queue.js`
- kept `src/aresforge/hub/static/app.js` as the frontend entrypoint and init/orchestration surface
- intentionally left local queue lifecycle internals in `app.js` to keep this refactor conservative and behavior-preserving
- updated static tests to assert the new queue section module exists, is imported by `app.js`, and owns queue-only bindings

Safety posture:

- local-only refactor
- no GitHub API calls, no `gh` calls
- no new network behavior
- no agent or model execution
- no UI redesign and no DOM id or endpoint path changes

### M26 - Extract Hub Projects And Repos Section Modules

Status: Completed locally on `main`.

Highlights:

- extracted Projects rendering/selectors/bindings into `src/aresforge/hub/static/js/sections/projects.js`
- extracted Repos rendering/loading/inspection/bindings into `src/aresforge/hub/static/js/sections/repos.js`
- kept `src/aresforge/hub/static/app.js` as the frontend entrypoint and init/orchestration surface
- intentionally kept project-factory lifecycle orchestration in `app.js` to keep this refactor conservative and behavior-preserving
- updated static tests to assert the new Projects/Repos section modules exist, are imported by `app.js`, and own their section bindings

Safety posture:

- local-only refactor
- no GitHub API calls, no `gh` calls
- no new network behavior
- no agent or model execution
- no UI redesign and no DOM id or endpoint path changes

### M27 - Extract Hub Reports Section Module

Status: Completed locally on `main`.

Highlights:

- extracted Reports rendering/loading/export helpers and Reports-specific bindings into `src/aresforge/hub/static/js/sections/reports.js`
- kept `src/aresforge/hub/static/app.js` as the frontend entrypoint and init/orchestration surface
- intentionally kept non-Reports orchestration in `app.js` to keep this refactor conservative and behavior-preserving
- updated static tests to assert the new Reports section module exists, is imported by `app.js`, and owns Reports bindings

Safety posture:

- local-only refactor
- no GitHub API calls, no `gh` calls
- no new network behavior
- no agent or model execution
- no UI redesign and no DOM id or endpoint path changes

### M28 - Extract Hub Orchestration And Escalation Section Modules

Status: Completed locally on `main`.

Highlights:

- extracted Orchestration rendering/loading/bindings into `src/aresforge/hub/static/js/sections/orchestration.js`
- extracted Escalation rendering/loading/bindings into `src/aresforge/hub/static/js/sections/escalation.js`
- kept `src/aresforge/hub/static/app.js` as the frontend entrypoint and init/orchestration surface
- intentionally kept project-factory lifecycle, queue lifecycle internals, and execution approval orchestration in `app.js` to keep this refactor conservative and behavior-preserving
- updated static tests to assert the new section modules exist, are imported by `app.js`, and preserve Orchestration/Escalation static contracts

Safety posture:

- local-only refactor
- no GitHub API calls, no `gh` calls
- no new network behavior
- no agent or model execution
- no UI redesign and no DOM id or endpoint path changes


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

- No production-ready LLM dispatch exists; only the M62 explicit local LLM prototype may call a local provider under operator gates.
- No cloud LLM API integration yet.
- No GitHub sync execution yet.
- Hub provides the local web UI; auth/deployment hardening and execution gates remain future work.
- No cross-machine coordination yet.
- No background daemon/scheduler yet.
