# AresForge Model Registry Schema

## Purpose

This document defines the first canonical AresForge model registry schema and local LLM routing rules for M2.

The model registry exists so AresForge can describe which local models are available, what they are allowed to support, how routing recommendations should be recorded, and which decisions must remain human-approved before any broader routing, queue, or automation work is attempted.

During M2, this document is the source of truth for model-record meaning, bounded local routing expectations, and reviewable model-selection evidence. It does not authorize autonomous execution, autonomous model selection for governance-sensitive work, external hosted model calls, credential storage, destructive behavior, or GitHub-state-changing behavior.

## Relationship To Registry And Queue Architecture

`docs/architecture/REGISTRY_AND_QUEUE_ARCHITECTURE.md` remains the parent architecture document for the project, agent, model, queue, capability, and skill registry layers.

This document specializes the model-registry layer. It turns the higher-level model-registry concept into a concrete M2 schema, routing-policy vocabulary, validation model, and bounded local-first routing rules.

This document does not replace queue, capability, or lifecycle architecture. It gives those layers a stable model-selection reference point they can consult later.

## Relationship To Project Registry

`docs/architecture/PROJECT_REGISTRY_SCHEMA.md` remains the canonical source for managed-project identity, source-of-truth priority, approval authority, and project-level allowed or blocked operations.

Model records must remain subordinate to project records. A model may be available in the registry without being approved for every project, every data class, or every task class.

Project records may later point to preferred or blocked model-routing policies, but project ownership and project approval boundaries still win if model or routing metadata conflicts with project rules.

## Relationship To Agent Registry

`docs/architecture/AGENT_REGISTRY_SCHEMA.md` remains the canonical source for agent-role identity, lifecycle state, capability boundaries, queue participation, evidence expectations, and approval boundaries.

Agent records answer who is allowed to support a class of work. Model records answer which local inference option may support that work under bounded conditions.

Model presence must not imply that an agent may autonomously execute, approve, merge, close, or mutate anything. Agent and human-governance boundaries remain primary.

## Relationship To Skills And Capabilities

Capabilities remain the bounded task categories that agents may request, models may support, skills may assist, and queues may require.

Skills remain advisory markdown guidance only during M2.

The model registry should therefore describe support for bounded capability or task classes rather than broad claims like "general coding" or "full automation." A skill may help a human or agent use a model well, but a skill reference must not silently widen model authority.

## Relationship To Local Operator Workflow

The local operator is the human-triggered CLI and review surface described by:

- `docs/operator/LOCAL_OPERATOR_USAGE.md`
- `docs/architecture/RUNNABLE_SKELETON.md`
- `docs/architecture/LOCAL_STATE_STORE.md`

During M2, the local operator may inspect or seed conservative model metadata, list seeded local model rows, generate prompt and evidence artifacts that mention chosen model IDs, and test a configured local Ollama endpoint.

The local operator does not yet implement a full model-routing command, background selector, or autonomous dispatch loop. Any later operator extension must remain human-triggered and reviewable unless a future issue explicitly changes that rule.

## Relationship To Ollama / Local Runtime

The current M2 execution surface for local model support is Ollama.

The existing runnable skeleton already includes:

- a configured Ollama base URL
- a configured default Ollama model name
- a conservative seeded `models` row in the local state store
- a human-triggered `test-ollama` connectivity check

This document treats Ollama as the first supported local runtime convention for model records and routing examples. That does not imply that every Ollama-served model is automatically approved for every task.

## Core Definitions

### Model

A model is a local or later-approved external inference option that may support one or more bounded task classes under explicit review, privacy, approval, and evidence rules.

### Model Record

A model record is the schema-shaped description of one approved or planned inference option.

### Runtime

A runtime is the serving surface that exposes a model, such as Ollama.

### Provider

A provider is the named source or serving family associated with the model record, such as `ollama`.

### Routing Record

A routing record is the policy-shaped statement that explains how a model should be considered for bounded task classes, priority ordering, fallback behavior, and approval requirements.

### Task Class

A task class is a bounded category of model-supported work such as documentation drafting support, implementation drafting support, validation evidence review, or prompt package preparation.

Task classes are narrower than broad capabilities and must not imply governance authority.

### Routing Priority

Routing priority is the conservative ordering signal that says which approved local model should be considered first for a bounded task class.

### Fallback

A fallback is the next approved local option to consider when the preferred model is unavailable, unsuitable, or blocked for the requested task class.

### Governance-Sensitive Action

A governance-sensitive action is any action involving merge authority, issue-close authority, repo mutation, approval authority, release or tag mutation, ruleset or settings mutation, secret handling, or other actions that must remain explicitly human-controlled during M2.

## Model Record Minimum Useful Schema

| Field | Required now? | Future implementation? | Description | Example value |
|---|---|---|---|---|
| `model_id` | Yes | Yes | Stable unique identifier for the model record. | `model-ollama-qwen25-32b` |
| `model_key` | Yes | Yes | Stable routing key used in references, policy records, and future storage. | `ollama/qwen2.5:32b` |
| `display_name` | Yes | Yes | Human-readable model name. | `qwen2.5:32b` |
| `provider` | Yes | Yes | Serving provider or family identifier. | `ollama` |
| `runtime` | Yes | Yes | Runtime exposing the model. | `ollama_local` |
| `execution_location` | Yes | Yes | Conservative statement of where inference happens. | `local_machine` |
| `local_endpoint` | Yes | Yes | Local runtime endpoint or endpoint template. | `http://127.0.0.1:11434` |
| `purpose` | Yes | Yes | Short description of intended use. | `Local validation and drafting support.` |
| `allowed_task_classes` | Yes | Yes | Bounded task classes the model may support. | `["documentation_support", "validation_evidence_review"]` |
| `default_routing_priority` | Yes | Yes | Relative priority for allowed task classes. | `primary` |
| `fallback_rules` | Yes | Yes | Conservative fallback policy or approved fallback targets. | `["fallback to smaller local Ollama model", "otherwise escalate to human"]` |
| `approval_requirements` | Yes | Yes | Human approval rules for model use. | `["human approval required for governance-sensitive tasks"]` |
| `approval_posture` | Yes | Yes | Conservative approval state for current use. | `local_human_review_required` |
| `validation_suitability` | Yes | Yes | Whether the model is suitable for validation-style review and how strongly. | `bounded_validation_support` |
| `evidence_expectations` | Yes | Yes | Required evidence when the model is selected or recommended. | `["record selected model key", "record routing reason"]` |
| `known_limitations` | Yes | Yes | Important limitations that affect routing or review trust. | `["may require human review for nuanced governance interpretation"]` |
| `status` | Yes | Yes | Conservative lifecycle status for the model record. | `active` |
| `notes` | No | Yes | Important model-specific caveats. | `Configured through local .env values.` |

## Required M2 Fields

The following fields are required for a useful M2 model record:

- `model_id`
- `model_key`
- `display_name`
- `provider`
- `runtime`
- `execution_location`
- `local_endpoint`
- `purpose`
- `allowed_task_classes`
- `default_routing_priority`
- `fallback_rules`
- `approval_requirements`
- `approval_posture`
- `validation_suitability`
- `evidence_expectations`
- `known_limitations`
- `status`

These fields are the minimum needed to identify the model, keep routing bounded, make approval posture explicit, and preserve reviewable evidence when a model is selected or recommended.

## Optional M2 Fields

These fields are useful during M2 but are not required for every record:

- `model_family`
- `parameter_scale`
- `context_window_notes`
- `performance_notes`
- `privacy_notes`
- `cost_notes`
- `supported_agent_roles`
- `supported_capabilities`
- `blocked_task_classes`
- `example_use_cases`
- `operator_notes`
- `comparison_notes`
- `source_of_truth_links`

## Future Implementation-Only Fields

These fields are reserved for later implementation work and must not be treated as current M2 capability:

- `runtime_adapter_id`
- `runtime_health_state`
- `observed_latency_ms`
- `observed_throughput_tokens_per_sec`
- `benchmark_refs`
- `evaluation_scorecard`
- `structured_routing_policy_id`
- `last_health_check_at`
- `last_selection_at`
- `selection_count`
- `prompt_template_bindings`
- `credential_reference`
- `external_connector_id`
- `dashboard_model_id`
- `registry_storage_path`

## Provider / Runtime Conventions

During current M2 work, the recommended conservative provider and runtime values are:

| Field | Recommended values | Notes |
|---|---|---|
| `provider` | `ollama`, `future_external_approved` | `future_external_approved` is planning-only until a later human-approved issue explicitly allows it. |
| `runtime` | `ollama_local`, `future_external_runtime` | `future_external_runtime` is planning-only. |
| `execution_location` | `local_machine`, `future_remote_approved` | Remote execution remains blocked for now. |
| `status` | `planned`, `active`, `paused`, `blocked`, `deprecated`, `archived` | `active` still means human-reviewed, not autonomous. |
| `approval_posture` | `local_human_review_required`, `blocked_pending_governance`, `future_external_review_required` | Use conservative values when uncertain. |

Recommended interpretation:

- `ollama` plus `ollama_local` means the model is served locally through the current Ollama-based runtime surface.
- Any external-provider wording must be treated as blocked planning context only unless a later issue explicitly permits it.

## Local Endpoint Conventions

M2 model records may describe local endpoints only in conservative local-runtime form.

Recommended conventions:

- Use loopback or explicitly local hostnames when possible.
- Prefer endpoint templates or configured values rather than embedding secrets.
- Do not store tokens, credentials, or secret headers.
- Do not imply that endpoint reachability means task approval.

Recommended example values:

- `http://127.0.0.1:11434`
- `http://localhost:11434`

If a model record references a local endpoint, the record should still rely on human-triggered config validation and `test-ollama` style checks rather than hidden background health workers.

## Allowed Task Class Conventions

Task classes must remain bounded, reviewable, and non-authorizing.

Recommended M2 task-class values:

- `documentation_support`
- `implementation_support`
- `prompt_package_support`
- `codex_handoff_support`
- `validation_evidence_review`
- `diff_review_support`
- `routing_recommendation_support`
- `project_state_summary_support`

Recommended blocked or restricted task-class values during M2:

- `governance_decision`
- `merge_authority`
- `issue_close_authority`
- `repo_mutation`
- `release_mutation`
- `secret_handling`
- `ruleset_mutation`
- `settings_mutation`

Task classes should not be used as a workaround for blocked governance-sensitive actions. If a requested task approaches governance authority, the model should be treated as advisory only and the human owner must decide.

## Routing Priority Conventions

Routing priority should stay simple and reviewable during M2.

Recommended values:

- `primary`
- `secondary`
- `fallback_only`
- `blocked`

Interpretation rules:

- `primary` means this is the preferred approved local option for the bounded task class.
- `secondary` means it may be used when the primary local option is unavailable or less suitable.
- `fallback_only` means it should not be first choice.
- `blocked` means the model record may exist for planning or audit reasons but must not be selected.

Routing priority is a recommendation layer only. It must not bypass project-specific rules, agent approval boundaries, or explicit human direction.

## Fallback Rules

Fallback rules must remain explicit and conservative.

Minimum fallback expectations for M2:

- Try another approved local model only if it supports the same bounded task class.
- Preserve the same or stricter approval posture when falling back.
- Record why the preferred model was not used.
- Escalate to the human owner when no approved local model is suitable.
- Do not fall through to hosted external APIs by default.

Blocked fallback behaviors during M2:

- silent external escalation
- hidden provider switching
- credential-based fallback
- governance-sensitive task auto-selection
- destructive-action fallback

## Human Approval Requirements

The human owner remains the final authority for:

- approving model records
- approving routing-policy meaning
- approving use for governance-sensitive work
- approving any later external hosted provider support
- approving any later higher-autonomy routing behavior

During M2, routing recommendations may assist with:

- local drafting support
- local validation support
- local documentation support
- local prompt and evidence packaging support

During M2, routing recommendations must not independently decide:

- merge readiness
- issue closure
- repo mutation
- governance exceptions
- release or tag mutation
- settings, ruleset, or secret changes

## Evidence Expectations For Model Selection Decisions

Model-selection or routing recommendations must remain reviewable by the human owner.

Minimum evidence expectations:

- record the selected or recommended `model_key`
- record the requested task class
- record the routing reason in plain language
- record whether the choice was primary or fallback
- record any known limitations relevant to the task
- record whether human approval was required
- record whether the recommendation was advisory only

If a model participates in validation-style review, evidence should also note:

- why this model was considered suitable for validation support
- whether a second human review was still required
- whether the model surfaced uncertainty, limitations, or conflicting evidence

## Validation Rules

Model-registry records should pass these checks before they are considered usable:

- required fields exist
- `model_id` and `model_key` are stable and unique
- `provider`, `runtime`, and `execution_location` use approved conservative values
- `allowed_task_classes` does not include blocked governance-sensitive actions
- `default_routing_priority` uses an approved value
- `fallback_rules` do not imply hidden external escalation
- `approval_requirements` are explicit
- `approval_posture` is conservative and unambiguous
- `local_endpoint` is local-only or explicitly marked future/planned
- `evidence_expectations` are not empty
- `known_limitations` are not empty when routing risk exists
- model-record wording does not imply autonomous GitHub-state-changing behavior

During M2, these are review expectations and possible future local validation targets. They do not create autonomous routing or background enforcement.

## Source-Of-Truth And Closeout Expectations

Model-registry changes are project-state-changing changes.

That means Issue #85 and future model-registry changes must review and update when needed:

- `docs/context/BUILD_STATE.md`
- `docs/context/AGENT_CONTEXT.md`
- `docs/roadmap/ROADMAP.md`

They must also preserve the documentation-before-closeout rule:

- update source-of-truth docs inside the same issue lifecycle
- do not create a separate routine reconciliation issue by default
- preserve Issue #39 as intentionally open protected validation audit evidence unless a future human-directed issue explicitly changes it

## Explicit M2 Restrictions

This schema and routing model do not authorize:

- autonomous model selection for governance-sensitive actions
- autonomous GitHub-state-changing behavior
- hosted or external model API calls
- credential, token, or secret storage
- destructive actions
- model-triggered repo mutation
- model-triggered issue, PR, milestone, label, release, tag, ruleset, workflow, or settings mutation
- background routing workers
- queue consumers
- autonomous approval
- autonomous merge
- autonomous issue closure
- autonomous Codex execution
- autonomous Ollama planning loops

## Initial Local Model Examples

The following example set is intentionally conservative and local-first.

```yaml
models:
  - model_id: model-ollama-qwen25-32b
    model_key: ollama/qwen2.5:32b
    display_name: qwen2.5:32b
    provider: ollama
    runtime: ollama_local
    execution_location: local_machine
    local_endpoint: http://127.0.0.1:11434
    purpose: Local drafting, documentation support, and bounded validation evidence review.
    allowed_task_classes:
      - documentation_support
      - implementation_support
      - validation_evidence_review
      - diff_review_support
      - project_state_summary_support
    default_routing_priority: primary
    fallback_rules:
      - If unavailable, try an approved smaller local Ollama model for the same task class.
      - If no approved local model is suitable, escalate to the human owner.
    approval_requirements:
      - Human review remains required for all output.
      - Human approval is mandatory for any governance-sensitive interpretation or action.
    approval_posture: local_human_review_required
    validation_suitability: bounded_validation_support
    evidence_expectations:
      - record selected model key
      - record task class
      - record routing reason
      - record limitations relevant to the task
    known_limitations:
      - May produce useful review evidence without being authoritative.
      - Must not be treated as approval, merge, or closeout authority.
    status: active

  - model_id: model-ollama-llama31-8b
    model_key: ollama/llama3.1:8b
    display_name: llama3.1:8b
    provider: ollama
    runtime: ollama_local
    execution_location: local_machine
    local_endpoint: http://127.0.0.1:11434
    purpose: Smaller local fallback for light drafting or summary tasks when the primary local model is unavailable.
    allowed_task_classes:
      - documentation_support
      - prompt_package_support
      - project_state_summary_support
    default_routing_priority: fallback_only
    fallback_rules:
      - Use only when the preferred local model is unavailable or oversized for the task.
      - Escalate to the human owner instead of using for governance-sensitive review.
    approval_requirements:
      - Human review remains required for all output.
      - Not approved for governance-sensitive task classes.
    approval_posture: local_human_review_required
    validation_suitability: limited_validation_support
    evidence_expectations:
      - record that fallback was used
      - record the reason the primary model was skipped
    known_limitations:
      - Smaller context and reasoning depth may reduce review quality.
      - Not suitable as sole authority for risky validation decisions.
    status: planned
```

These examples are schema examples only. They do not require that both models already exist in the runnable state store or local machine configuration.

## Open Design Questions

The following questions remain intentionally open after Issue #85:

- Should future structured model records live in markdown, YAML, JSON, database tables, or a hybrid model?
- How should task classes align with a future capability registry without duplicating meaning?
- Should routing policies be project-specific, global, or layered?
- How should queue context influence model selection without creating autonomous dispatch?
- How should future evaluation data and benchmark evidence be stored?
- How should model suitability for validation be measured without overstating confidence?
- When, if ever, should external hosted providers be introduced, and under which credential and privacy controls?
- Should the local operator eventually expose a read-only `show-routing-policy` command?
- How should model deprecation or replacement be surfaced in future operator and dashboard views?
