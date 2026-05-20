# Model Routing Strategy

## Purpose

This document defines AresForge's local-first model-routing and LLM escalation strategy.

It provides human operators and agents with clear guidance on which inference model tier to choose for a given task, when escalation is appropriate, and which guardrails prevent unnecessary cost, privacy exposure, or over-use of high-cost inference resources.

This document is an architecture reference only. It does not introduce runtime routing behavior, autonomous model selection, API calls, or external provider integrations. Future operator and agent documentation should reference this strategy wherever model selection matters.

Related documents:

- `docs/architecture/MODEL_REGISTRY_SCHEMA.md` — canonical model-record schema and bounded local routing rules
- `docs/architecture/REGISTRY_AND_QUEUE_ARCHITECTURE.md` — parent registry architecture
- `docs/architecture/AGENT_REGISTRY_SCHEMA.md` — agent-role definitions and capability boundaries
- `docs/operator/LOCAL_OPERATOR_USAGE.md` — human-triggered local operator surface
- `docs/architecture/RUNNABLE_SKELETON.md` — runnable skeleton structure and operator command list

## Local-First Principle

AresForge executes locally first.

Every task that can be done by a local model must be offered to the local model tier before any escalation is considered. Escalation is not a convenience shortcut; it is a deliberate decision made when a task genuinely exceeds local model capability or when documentation, policy, or human direction explicitly authorizes a higher tier.

Local execution preserves:

- **privacy** — repository content, issue text, evidence packages, and implementation context never leave the operator's machine unless explicitly sent elsewhere
- **cost control** — no external inference billing is incurred for routine work
- **auditability** — all local model interactions and results remain inspectable by the human operator
- **speed** — local Ollama-served models respond without network round-trips

This principle applies to the current M2 foundation and must carry forward through M3, M4, and all future milestones unless a specific future issue explicitly revises it under human review.

## Escalation Ladder

The AresForge model-routing escalation ladder has four tiers. Each tier must only be used when the tier below it cannot handle the task adequately.

| Tier | Model / Surface | When To Use |
|------|-----------------|-------------|
| 1 | Local Ollama / local model | Default for all tasks |
| 2 | Copilot GPT-4.1, GPT-4o, or equivalent included Copilot-hosted model | Higher reasoning, multi-step analysis, complex review |
| 3 | Codex (OpenAI Codex agentic surface) | Complex agentic repository implementation tasks |
| 4 | Paid / API key–based model calls | Only by explicit human decision, never by default |

Escalation must always be a deliberate, documented choice. Agents must not silently escalate because a task feels slightly complicated or because a higher-tier model is faster or more capable in general.

## Task Routing Guide

The table below provides concrete routing decisions for common AresForge task classes.

| Task | Recommended Tier | Notes |
|------|-----------------|-------|
| Routine documentation drafting | Tier 1 — local model | Summaries, freshness checks, doc-sync proposals |
| Registry validation output review | Tier 1 — local model | Read-only inspection artifacts are small and structured |
| Evidence package formatting | Tier 1 — local model | Template-filling, field formatting |
| Prompt package preparation | Tier 1 — local model | Template-filling, context assembly |
| Basic documentation quality check | Tier 1 — local model | Spelling, structure, completeness against a template |
| Routine source-of-truth reconciliation | Tier 1 — local model | Comparing doc fields against known state |
| Complex multi-document architecture analysis | Tier 2 — Copilot | When local model produces unreliable or incomplete reasoning |
| Multi-step implementation planning | Tier 2 — Copilot | Issue decomposition, dependency analysis |
| Governance-sensitive PR review drafting | Tier 2 — Copilot | When nuanced cross-document reasoning is required |
| Complex agentic repo implementation | Tier 3 — Codex | End-to-end feature implementation across multiple files |
| Multi-file refactoring with test generation | Tier 3 — Codex | Only when scope genuinely requires agentic iteration |
| New external provider integration | Tier 4 — explicit decision | Requires human authorization, documented rationale |
| Production inference pipeline work | Tier 4 — explicit decision | Not authorized during M2 or M3 without dedicated issue |

When in doubt, default to Tier 1. If Tier 1 output is genuinely insufficient after a reasonable attempt, escalate to Tier 2 with a note in the evidence package. Never escalate directly to Tier 3 or Tier 4 without explicit human direction.

## Local Model Usage

### When To Use Local Models

Use local Ollama-served models (Tier 1) for:

- documentation drafting and summarization
- registry and queue inspection report formatting
- evidence package and prompt package text generation
- source-of-truth freshness comparison against documented state
- basic validation output review
- routine Codex handoff preparation where the context is already structured
- any task that can be expressed as structured text generation from well-defined inputs

### Capabilities And Limits

Local models are fast, private, and cost-free. Their reasoning depth and cross-document coherence is bounded by model size and available context.

Local models should not be asked to:

- make governance decisions (approvals, merge decisions, issue closure)
- perform complex multi-document reasoning across large corpora without summarization assistance
- generate final authoritative architecture decisions without human review

### Configuration

Local model configuration follows `docs/architecture/MODEL_REGISTRY_SCHEMA.md`. The current M2 default local model ID is `model-ollama-default`. The configured Ollama base URL and default model name are set in the local `.env` file and validated by `validate-config`.

## Copilot Model Usage

### When To Use Copilot Models

Use Copilot-hosted models (Tier 2) — currently GPT-4.1, GPT-4o, or equivalent included Copilot models — when:

- the task requires multi-step reasoning that local models handle unreliably
- the task involves complex cross-document analysis that exceeds local model context or coherence
- the local model has produced multiple inadequate outputs and escalation is the documented next step
- an operator or agent needs implementation guidance for a novel or architecturally complex issue
- the task involves writing new governance documentation that must reason about the entire existing canon

### Guardrails

Copilot models are included in existing GitHub Copilot subscriptions and therefore do not incur direct per-token billing when used within normal subscription limits. However:

- Copilot model access should not be treated as unlimited capacity for trivial tasks
- Repository content sent to Copilot models leaves the local machine and is processed by GitHub/Microsoft infrastructure
- Privacy-sensitive content (credentials, unreleased business logic, PII) must not be included in Copilot model prompts

Copilot model use must not be chosen simply because it is faster or more capable than the local model for a task that the local model can handle adequately.

## Codex Usage

### When To Use Codex

Use Codex (Tier 3) only for complex agentic repository implementation tasks where:

- the task requires autonomous multi-file editing across the repository
- the task involves generating or modifying code, tests, and documentation together as part of a single issue
- the task has been explicitly scoped in a Codex handoff artifact prepared by the local operator
- a human operator has reviewed the prompt package and explicitly authorized the Codex invocation

### Warning: Do Not Use Codex For Routine Work

**Codex must not be used for:**

- routine documentation summaries
- routine validation output review
- basic documentation freshness checks
- formatting evidence packages or prompt packages
- tasks that a local model or Copilot model can handle adequately

Codex is an agentic surface. Agentic invocations have broader repo-mutation potential, higher cost, and less predictable scope than non-agentic model use. Overusing Codex for routine tasks wastes resources, increases review burden, and risks unintended mutations.

Every Codex invocation must be traceable to an explicit issue, a prepared Codex handoff artifact, and a human authorization decision.

### Codex Invocation Flow

1. Human operator prepares a Codex handoff artifact using `prepare-codex-handoff`
2. Human operator reviews the artifact and confirms scope
3. Human operator explicitly invokes Codex with the prepared prompt
4. Codex output is reviewed by a human before any merge or closeout

Codex output is never authoritative without human review. Codex-generated PRs must pass the same validation, documentation, and evidence gates as any other implementation PR.

## Paid / API Model Usage

### When Paid API Calls Are Allowed

Paid / API key–based model calls (Tier 4) are only allowed when:

- a human operator has explicitly decided to use a paid API-key model for a specific task
- the decision is documented in issue, PR, or evidence context
- the task cannot be accomplished adequately by Tier 1, Tier 2, or Tier 3 resources
- the API key is managed securely and is not stored in repository files or committed to version control

### Warning: No Unapproved API Billing

**Under no circumstances may an agent or automated flow initiate API-key–based model calls without explicit prior human authorization.**

This prohibition covers:

- OpenAI API direct calls
- Anthropic API direct calls
- Azure OpenAI API direct calls
- Any other provider API that incurs per-token or per-request billing

Agents must never store, read, or use API keys from environment variables or config files for inference purposes unless a dedicated issue explicitly authorizes the integration and the human operator has confirmed the key management approach.

Unapproved API billing is a governance violation and a security concern. Any code or automation that initiates such calls without explicit human authorization must be removed immediately.

## Cost And Privacy Guardrails

### Cost Summary

| Tier | Cost | Notes |
|------|------|-------|
| Tier 1 — local model | Free (local compute only) | Default; preferred for all routine work |
| Tier 2 — Copilot | Included in subscription | Do not use for tasks local models handle |
| Tier 3 — Codex | Included in Copilot/subscription tier | Only for authorized agentic implementation |
| Tier 4 — Paid API | Per-token billing | Explicit human decision required; never default |

### Privacy Summary

| Tier | Data Leaves Machine? | Notes |
|------|---------------------|-------|
| Tier 1 — local model | No | All data stays local |
| Tier 2 — Copilot | Yes (GitHub/Microsoft infra) | Do not include PII or credentials |
| Tier 3 — Codex | Yes (GitHub/Microsoft infra) | Do not include PII or credentials |
| Tier 4 — Paid API | Yes (third-party provider infra) | Explicit authorization required; no PII |

Operators must apply the minimum-disclosure principle: only include in model prompts the context genuinely needed for the task. Do not include credentials, PII, unreleased business logic, or content that should not leave the local environment in Tier 2, Tier 3, or Tier 4 prompts.

## Future Documentation References

Future operator and agent documentation that involves model selection must reference this strategy document.

The following documents are expected to grow their model-selection guidance as AresForge advances:

- `docs/operator/LOCAL_OPERATOR_USAGE.md` — should note which commands use local model context and when Tier 2+ escalation may be appropriate for reviewing command output
- `docs/architecture/MODEL_REGISTRY_SCHEMA.md` — already the canonical schema; should cross-reference this strategy for routing decisions
- `docs/agents/DOCUMENTATION_AGENTS.md` — should reference this strategy when describing which model tier documentation agents should use for freshness checks and drafting
- `docs/architecture/ISSUE_LIFECYCLE_AGENT_PIPELINE.md` — should reference this strategy at lifecycle stages where model selection is relevant
- `docs/prompts/CODEX_PROMPT_PACKAGE_TEMPLATE.md` — should note that Codex invocations follow the Tier 3 rules defined here
- Future M9 model routing implementation documents — must treat this strategy as the parent policy document

When writing new operator or agent documentation, authors must not assign a model tier without consulting this strategy. If a new task class does not fit an existing tier, the operator or agent must escalate to human review before assigning a tier.

## Non-Goals

This document does not:

- implement model routing logic, background selectors, or autonomous dispatch
- authorize any tier of model call autonomously
- replace `docs/architecture/MODEL_REGISTRY_SCHEMA.md` as the canonical model-record and routing-rule schema
- authorize Tier 4 paid API calls for any specific task (each Tier 4 use requires its own explicit human decision)
- define the full M9 model routing architecture (that belongs to a dedicated future milestone)
- apply retroactively to work already completed before Issue #114
- supersede human judgment in any governance-sensitive decision
