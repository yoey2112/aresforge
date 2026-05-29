# Agent LLM Routing Strategy

## Status

M44A documents the future Agent/LLM routing strategy only. It does not implement runtime routing, model invocation, Codex execution, new Hub routes, frontend settings UI, or queue schema changes.

Current implemented behavior remains M43 prompt-pack generation: local-only grouped prompt packs for manual operator use, without LLM/model routing.

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

Routing decisions should happen before prompt generation. A prompt pack should be generated only after the project policy, agent lane, engine/model recommendation, fallback, risk/complexity, routing reason, and sequencing context are known.

## Canonical Queue Model

AresForge should keep one canonical local queue. Future routing should add routing metadata and derive filtered routed views or lanes from that canonical queue.

Do not physically split queue storage too early. Separate queue files by agent, engine, model, or policy would make dependency ordering, lifecycle evidence, and project-wide status harder to reason about.

Future routed queue views should be filters over the canonical queue:

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
