# Agent LLM Routing Strategy

## Status

M44A documented the future Agent/LLM routing strategy. M51 through M57 now add non-executing contracts and local Hub surfaces for project AI settings, agent/engine registry, queue routing metadata, recommendation-only routing decisions, Project AI Settings UI, routed queue views, and routing-aware prompt packs.

Current prompt-pack behavior extends M43 local-only grouped prompt packs with advisory routing metadata. Runtime routing, model invocation, Codex execution, local LLM execution, real agent execution, and GitHub integration remain unimplemented.

## M51 Project AI Settings Contract

M51 stores project-level AI routing preferences locally at `.aresforge/projects/{project_id}/ai_settings.json`.

The contract is intentionally non-executing. It validates settings for future routing milestones but does not decide a route, generate routed prompt-pack entries, update queue routing metadata, invoke a local LLM, invoke Codex, run an agent, or call GitHub.

Current operator functions:

- `read_project_ai_settings(...)`
- `update_project_ai_settings(...)`
- `validate_project_ai_settings(...)`

Current Hub routes:

- `GET /api/projects/{project_id}/ai-settings`
- `POST /api/projects/{project_id}/ai-settings`

Settings fields:

- `project_ai_mode`
- `available_engines`
- `disabled_engines`
- `default_engine`
- `default_model`
- `operator_override_allowed`
- `notes`
- `updated_at`

Validation rules:

- `project_ai_mode` must be one of the supported project AI modes.
- `available_engines` and `disabled_engines` may only contain supported engine keys.
- `default_engine` must be in `available_engines` unless the mode is `manual_only`.
- `default_engine` must not be in `disabled_engines`.
- `local_only` must not default to `codex_cli`.
- `codex_only` must not default to `local_reasoning_llm` or `local_coding_llm`.
- `manual_only` may omit `default_engine`.
- `cost_saver` and `high_confidence` are preference contracts only until later routing milestones.

M52 should add the Agent and Engine Registry Contract so these project settings can be evaluated against known agent lanes and engine profiles without executing routing.

## M52 Agent And Engine Registry Contract

M52 adds a read-only Agent and Engine Registry Contract for future routing validation.

Current operator function:

- `read_agent_engine_registry(...)`

Current Hub route:

- `GET /api/agent-engine-registry`

Agent lane keys:

- `architect_planner`: architecture, sequencing, constraints, and implementation strategy
- `coding`: implementation-focused prompts and code-change plans
- `reviewer_validator`: review, validation evidence, readiness, and closeout risk
- `documentation`: docs updates, handoff notes, and source-of-truth summaries
- `test`: validation command planning, test scope, and evidence expectations
- `local_operator_assistant`: local operator workflow, queue triage, and safe next actions
- `high_value_codex`: future Codex-worthy escalation lane for high-risk or high-value work

Engine keys:

- `local_reasoning_llm`: future local reasoning, review, and operator-assistance engine
- `local_coding_llm`: future local coding-oriented engine
- `codex_cli`: future operator-gated Codex CLI engine

Every lane has:

- `execution_allowed: false`
- `routing_only: true`

Every engine has:

- `execution_allowed: false`
- `operator_gate_required: true`

Codex CLI remains engine `codex_cli`. Its model profiles are placeholder-only and describe future fields for default Codex model, high-value Codex model, fast Codex model, allowed Codex models per project, and allowed Codex models per agent.

M52 does not execute routing, update queue routing metadata, invoke Codex, invoke local LLMs, run agents, call GitHub, or run external workflows. M53 should add the Queue Routing Metadata Contract.

## M53 Queue Routing Metadata Contract

M53 adds a non-executing routing metadata contract to local queue item state while preserving one canonical local queue.

Current operator helpers:

- `default_queue_routing_metadata(...)`
- `validate_queue_routing_metadata(...)`
- `update_local_queue_item_routing_metadata(...)`

Current Hub route:

- `POST /api/local-queue/items/{item_id}/routing-metadata`

Metadata fields:

- `recommended_agent_lane`
- `recommended_engine`
- `recommended_model`
- `fallback_engine`
- `fallback_model`
- `routing_policy_source`
- `routing_reason`
- `risk_level`
- `complexity_level`
- `escalation_reason`
- `project_ai_mode`
- `operator_override`

Supported values:

- agent lanes: `architect_planner`, `coding`, `reviewer_validator`, `documentation`, `test`, `local_operator_assistant`, `high_value_codex`
- engines: `local_reasoning_llm`, `local_coding_llm`, `codex_cli`
- risk levels: `low`, `medium`, `high`, `critical`, `unknown`
- complexity levels: `low`, `medium`, `high`, `unknown`

Empty or unassigned routing metadata is allowed. Non-empty lane and engine values must align with M52. Invalid metadata is rejected by metadata update paths.

M53 does not compute routing decisions, split queue storage, execute prompts, invoke Codex, invoke local LLMs, run agents, call GitHub, or run external workflows. M54 should implement Routing Decision Matrix v1.

## M54 Routing Decision Matrix v1

M54 adds recommendation-only routing decisions for local queue items.

Current operator helpers:

- `recommend_queue_item_routing(...)`
- `apply_queue_item_routing_recommendation(...)`

Current Hub routes:

- `POST /api/local-queue/items/{item_id}/routing-recommendation`
- `POST /api/local-queue/items/{item_id}/apply-routing-recommendation`

Decision hierarchy:

1. Project policy
2. Agent policy
3. Task classification
4. Risk/complexity
5. Affected area/files
6. Validation burden
7. Engine/model availability
8. Cost/credit preference
9. Operator override

Mode outcomes:

- `balanced`: recommends local engines for simple work and may recommend `codex_cli` for high-value/high-risk work.
- `local_only`: recommends local engines only and blocks Codex-worthy work unless an operator override is provided.
- `codex_only`: recommends `codex_cli` only.
- `cost_saver`: prefers local engines for low/medium risk and warns on high-risk Codex-worthy work.
- `high_confidence`: prefers `codex_cli` for high-risk or high-complexity work when allowed.
- `manual_only`: requires explicit operator decision and does not auto-recommend an engine.

Recommendation preview does not write metadata. Explicit apply writes M53 queue routing metadata only. Every recommendation includes `execution_allowed: false`.

M54 does not execute local LLMs, Codex, agents, GitHub, prompts, workflows, or external services. M55 should add Project AI Settings UI.

## M55 Project AI Settings UI

M55 exposes the M51 Project AI Settings Contract in the local Hub Projects section.

Current UI path:

- Projects -> Project AI Settings

Current API routes used by the UI:

- `GET /api/projects/{project_id}/ai-settings`
- `POST /api/projects/{project_id}/ai-settings`

The UI allows operators to view and update:

- project AI mode
- available engines
- disabled engines
- default engine
- optional default model
- operator override allowed
- notes

The UI displays validation status, warnings, blockers, and next safe action. Invalid settings are rejected by the API and shown in the panel.

M55 does not execute routing, invoke local LLMs, invoke Codex, run agents, generate or execute prompts, call GitHub, or run external workflows.

## M56 Routed Queue Views

M56 adds read-only routed queue views over the one canonical local queue.

Current operator helper:

- `read_local_routed_queue_views(...)`

Current Hub route:

- `GET /api/local-queue/routed-views`

Current UI path:

- Queue -> Routed Queue Views

Supported filters:

- `project_id`
- `status`
- `recommended_agent_lane`
- `recommended_engine`
- `recommended_model`
- `fallback_engine`
- `risk_level`
- `complexity_level`
- `project_ai_mode`
- `routing_policy_source`
- `operator_override`

Supported grouped views:

- `by_agent_lane`
- `by_engine`
- `by_model`
- `by_project_policy`
- `by_risk_level`
- `by_complexity_level`
- `by_status`

Routed views are not separate queues. They read and group the canonical local queue, include unrouted items by default, handle empty queue state, and return `execution_allowed: false`.

M56 does not split queue storage, execute routing, invoke local LLMs, invoke Codex, run agents, generate or execute prompts, call GitHub, or run external workflows.

## M57 Prompt Pack Routing Integration

M57 integrates routing metadata into local-only prompt-pack generation.

Current operator helper:

- `generate_local_queue_prompt_pack(...)`

Current Hub route:

- `POST /api/local-queue/prompt-pack`

Current UI path:

- Queue -> Agent Prompt Pack Generator

Prompt-pack inputs now include:

- `include_routing`
- `group_by_routing`
- `routing_group_by`
- `include_unrouted`
- `recommend_missing_routing`

Each routed prompt can include:

- project and queue item context
- sequence and dependencies
- recommended agent lane
- recommended engine and model
- fallback engine and model
- routing policy source
- routing reason
- risk and complexity
- escalation reason
- project AI mode
- operator override state
- `execution_allowed: false`
- local-only operating rules
- validation/smoke expectations
- final response format template

Unrouted items are labeled as manual routing required. Items recommended for `codex_cli` state that Codex CLI is recommended but not executed by AresForge. Items recommended for `local_reasoning_llm` or `local_coding_llm` state that a local LLM is recommended but not executed by AresForge.

Routing-aware prompt packs can group by agent lane, engine, model, risk level, complexity level, or status. The existing M43 local grouping remains available when routing grouping is disabled.

M57 does not execute prompts, invoke local LLMs, invoke Codex, run agents, apply routing automatically, start or complete queue items, call GitHub, or run external workflows. M58 should add Local LLM Environment Contract.

## Operating Boundaries

Routing must remain:

- local-first
- file-backed
- operator-gated
- advisory until an explicit execution milestone is approved
- compatible with the existing single local queue

Routing strategy documentation does not authorize:

- real agent execution
- automatic Codex execution
- local LLM execution
- LLM/model routing execution
- GitHub API calls, `gh`, GitHub issues, PRs, workflows, or GitHub mutation from the app
- external/network execution beyond existing local Hub API behavior

## Routing Flow

Future routing should follow this flow:

Project -> Agent Lane -> Allowed Engines/Models -> Routing Decision Matrix -> Prompt Pack Output

Routing decisions should happen before prompt generation when metadata is available. M57 prompt packs include existing routing metadata and mark missing metadata as manual routing required.

## Canonical Queue Model

AresForge should keep one canonical local queue. Future routing should add routing metadata and derive filtered routed views or lanes from that canonical queue.

Do not physically split queue storage too early. Separate queue files by agent, engine, model, or policy would make dependency ordering, lifecycle evidence, and project-wide status harder to reason about.

M56 implements routed queue views as filters over the canonical queue:

- by agent
- by engine
- by model
- by project policy
- by risk/complexity
- by status

## Project AI Routing Modes

Each project must be able to define AI routing settings. Future supported project-specific modes:

- `balanced`: use local engines for eligible work and reserve Codex for higher-value or higher-risk work
- `local_only`: use local LLM engines only when eligible; Codex is not recommended
- `codex_only`: recommend Codex CLI for every agent lane and never route to local LLM engines
- `cost_saver`: prefer local LLM engines and mark high-risk/Codex-worthy work as blocked or requiring operator override
- `high_confidence`: prefer the most reliable engine/model allowed by the project and agent policy
- `manual_only`: generate routing context for operator review without recommending an executable engine

## Future Engines

Future engine identifiers:

- `local_reasoning_llm`
- `local_coding_llm`
- `codex_cli`

Codex CLI is treated as engine `codex_cli`. Its model is the configured Codex model. Codex execution is not implemented yet.

Future Codex model profiles should include:

- default Codex model
- high-value Codex model
- fast Codex model
- allowed Codex models per project
- allowed Codex models per agent

## Per-Project And Per-Agent Settings

Future settings should support:

- per-agent engine/model toggles
- default engine per agent
- escalation engine per agent
- fallback engine per agent
- disabled engines per agent
- project-level override such as Codex only for all agents or Local only for all agents

Project-level policy must be able to constrain agent settings. For example, a `local_only` project must not recommend `codex_cli`, and a `codex_only` project must not recommend local LLM engines.

## Agent Lanes

Future routing should classify work into these lanes:

- Architect / Planner Agent
- Coding Agent
- Reviewer / Validator Agent
- Documentation Agent
- Test Agent
- Local Operator Assistant
- High-Value Codex Lane

The High-Value Codex Lane is reserved for work where cost, risk, lifecycle importance, or operator confidence justifies recommending `codex_cli`.

## Routing Decision Hierarchy

Routing decisions should be resolved in this order:

1. Project policy
2. Agent policy
3. Task classification
4. Risk/complexity
5. Affected area/files
6. Validation burden
7. Engine/model availability
8. Cost/credit preference
9. Operator override

Operator override is last because it should be explicit and auditable. It may approve a fallback, block routing, or select a different allowed engine/model, but it must not silently bypass project policy.

## Future Routing Metadata

Future queue items or generated prompt-pack entries should carry routing metadata such as:

- `recommended_agent_lane`
- `recommended_engine`
- `recommended_model`
- `fallback_engine`
- `fallback_model`
- `routing_policy_source`
- `routing_reason`
- `risk_level`
- `complexity_level`
- `escalation_reason`
- `project_ai_mode`
- `operator_override`

These fields are future-state metadata. M44A does not add them to the queue schema.

## Prompt Pack Relationship

M43 prompt packs currently generate local-only grouped prompts without LLM/model routing.

Future routing milestones should extend prompt packs so each generated prompt is assigned to:

- project
- agent lane
- engine
- model
- risk/complexity
- routing reason
- sequence/dependencies
- project policy source

The prompt pack output should remain copy/paste-ready and operator-controlled unless a later milestone explicitly adds a gated execution path.

## Routing Examples

Simple UI wording task:

- Task classification: small coding/UI copy change
- Agent lane: Coding Agent
- Likely route: `local_coding_llm` if project and agent policy allow local coding work
- Prompt pack result: local coding prompt with low risk/complexity and manual operator handoff

High-value backend/operator lifecycle change:

- Task classification: backend/operator lifecycle behavior
- Agent lane: High-Value Codex Lane or Coding Agent with escalation
- Likely route: `codex_cli`
- Prompt pack result: Codex-oriented prompt with high validation burden, routing reason, and explicit operator gate

Project set to `codex_only`:

- All agent lanes recommend `codex_cli`
- Local LLM engines are never recommended
- Prompt pack entries should cite the project policy as the routing source

Project set to `local_only` or `cost_saver`:

- Eligible low-risk work routes to `local_reasoning_llm` or `local_coding_llm`
- High-risk or Codex-worthy work is marked blocked or requiring operator override
- Prompt pack entries should explain why Codex was not selected automatically

## Implementation Boundaries For Future Milestones

Future implementation should be incremental:

- add routing policy data carefully and file-backed
- keep queue storage canonical
- derive routed views from metadata
- keep routing advisory until explicit operator approval exists
- validate routing output without invoking models
- avoid backend route or frontend settings expansion unless that milestone explicitly scopes it

M44A is complete when the strategy is documented and cross-linked. It intentionally leaves all execution and schema work for later milestones.
