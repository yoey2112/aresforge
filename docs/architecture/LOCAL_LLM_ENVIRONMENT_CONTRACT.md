# Local LLM Environment Contract

## Status

M58 adds a local-only Local LLM Environment Contract.

This contract represents future local LLM provider and model configuration. It does not call Ollama, perform health checks, call model APIs, send prompts, execute routing, execute Codex, run agents, or call GitHub.

M59 adds an explicitly invoked Local LLM Health Check. The health check reads this contract and may check local provider availability only. It does not send prompts, run inference, generate text, execute routing, execute Codex, run agents, or call GitHub.

M61 adds Local LLM Prompt Preview. The preview reads this contract to resolve configured local provider/model fields for routed queue items, but it does not call Ollama, send prompts, run inference, generate text, execute routing, execute Codex, run agents, or call GitHub.

M62 adds an operator-gated local LLM execution prototype. Execution is allowed only when this contract explicitly has `execution_enabled: true`, `operator_gate_required: true`, a supported local provider, and the request passes prompt preview, health check, routing, risk, and operator confirmation gates.

M64 adds a local Execution Audit Log. Health checks, prompt previews, dry runs, blocked attempts, and advisory local LLM execution outputs are summarized in `.aresforge/execution_audit_log.json`. The audit log does not add execution behavior, does not store full prompt/response text, and does not execute anything.

M65 adds a centralized AI Action Safety Gate. Local LLM prompt preview and execution paths may consult the gate for consistent decision reporting, but the gate does not execute anything and does not expand M62 local LLM behavior.

M66 adds a local AI Artifact Registry. Local LLM prompt preview artifacts and advisory local LLM result artifacts are registered when explicitly written, but registry writes do not execute providers or expand M62 behavior.

M67 adds an Operator Run History panel that can display local LLM audit and artifact records in a read-only timeline. It does not execute providers or expand M62 behavior.

M68 reconciles local AI operations documentation and confirms that local LLM execution remains prototype-only, local-only, advisory-only, and operator-gated.

M69 hardens local AI operations around this contract. Local LLM execution payloads, audit entries, artifacts, and run-history records now make advisory-only, non-mutation, safety-status, gate-status, and blocked-reason state explicit. Local LLM output still never mutates repository files, queue state, project state, GitHub, `gh`, Codex, agents, commits, pushes, or workflows automatically.

M70 verifies the full M58-M69 local AI operations chain. It reconciles documentation and payload wording, confirms the local-first/file-backed/operator-gated/advisory-only boundaries, and does not add local LLM execution behavior beyond the M62 prototype.

M72 hardens provider and model configuration metadata. Environment reads, updates, and health-check responses now expose explicit provider availability status, provider configuration status, provider execution mode, advisory model profile metadata, fallback behavior, and next safe operator action. M72 does not add provider execution, automatic local LLM execution, or repository mutation behavior.

M75 reconciles source-of-truth documentation after M74. It does not add local LLM execution behavior. The local LLM contract remains local-only, advisory-only, operator-gated, prototype-scoped, and non-mutating. Local LLM output must never automatically mutate repository files, queue state, project state, GitHub, `gh`, Codex, agents, commits, pushes, or workflows.

M81 adds a read-only local LLM advisory/coding lane readiness inspection path. It reads this environment contract and M80 decision metadata to produce structured advisory planning output, but it does not invoke a provider, send prompts, run inference, mutate repository files, mutate queue state, complete queue items, or start another queue item.

M83 adds a read-only local LLM provider contract inspection path. It formalizes Ollama as the initial provider target and reports provider URL, health-check endpoint limits, timeout expectations, model identifiers, role/capability metadata, and safety boundaries. It does not call Ollama, send prompts, run inference, execute routing, mutate repository files, mutate queue state, complete queue items, or start another queue item.

M84 adds an explicitly invoked Ollama health/model inspection path. It may call only the local `/api/tags` endpoint to report provider reachability and visible models. Ollama offline states are warning metadata and must not block normal project readiness. M84 does not call generation, chat, completion, or prompt endpoints, and it does not mutate repository files, mutate queue state, complete queue items, or start another queue item.

M85 adds a local LLM advisory run artifact flow. It generates advisory prompt artifacts by default without invoking a provider. If the operator supplies an explicit run flag, it may call local Ollama for advisory output and store response/metadata artifacts locally. Advisory output is never applied to repository files, never mutates queue state, never completes queue items, and never starts another item.

M87 adds local coding draft artifact mode. It generates coding draft prompt artifacts by default without invoking a provider. If the operator supplies an explicit run flag, it may call local Ollama for draft patch/instruction output and store draft/metadata artifacts locally. Draft output is non-applied, non-authoritative, manual-review-only, and never mutates repository files, applies patches, mutates queue state, completes queue items, or starts another item automatically.

M88 adds a human-gated patch application contract. It defines the patch artifact structure, explicit operator approval record requirements, pre-apply safety gates, and post-apply validation requirements for any future patch application path. The contract inspector is read-only, contract-first, and dry-run only; it does not apply patches, mutate files, mutate queue state, complete queue items, or start another item.

M95 reconciles the overnight sprint documentation after M81-M94. It does not add local LLM provider behavior. The local LLM model remains local-only, explicit-operator-gated for any advisory/draft run, advisory/manual-review-only, and non-mutating. Provider output still never automatically mutates repository files, applies patches, mutates queue state, completes queue items, starts another item, calls GitHub, calls `gh`, or triggers workflows, daemons, watchers, schedulers, or external workflow systems.

M96 is post-sprint planning and prioritization. It does not add local LLM provider behavior, does not call Ollama, does not invoke advisory or coding draft runs, and does not validate provider inference.

M97 adds a queue-to-agent dispatch plan contract that may select `local_llm_advisory` or `local_llm_coding_draft` as advisory future lanes. That selection is metadata only. M97 does not call Ollama, check model inference, send prompts, invoke local advisory or coding draft runs, apply patches, mutate queue state, or complete work. Any future local LLM dry-run validation remains M99 or later and requires explicit operator approval.

M98 adds Codex prompt artifact generation only for the M97 `codex_prompt_artifact` lane. It explicitly blocks `local_llm_advisory` and `local_llm_coding_draft`, does not call Ollama, does not invoke provider health or inference endpoints, and does not authorize local LLM advisory or coding draft execution. M99 remains the planned local LLM dry-run validation milestone.

## Storage

The contract is stored locally at:

- `.aresforge/local_llm_environment.json`

Reading defaults does not write this file. Updating the contract writes the file only after validation passes.

## Operator Helpers

- `read_local_llm_environment_contract(...)`
- `update_local_llm_environment_contract(...)`
- `validate_local_llm_environment_contract(...)`

## Hub Routes

- `GET /api/local-llm/environment`
- `POST /api/local-llm/environment`
- `POST /api/local-llm/health-check`
- `POST /api/local-queue/items/{item_id}/local-llm-prompt-preview`
- `POST /api/local-queue/items/{item_id}/local-llm-execute`
- `GET /api/execution-audit-log`
- `POST /api/ai-action-safety-gate`
- `GET /api/ai-artifacts`
- `GET /api/operator-run-history`
- `GET /api/ai-action-review`
- CLI: `python -m aresforge inspect-local-llm-advisory-lane-readiness --item-id <item_id> --format json`
- CLI: `python -m aresforge inspect-local-llm-provider-contract --format json`
- CLI: `python -m aresforge inspect-ollama-health --format json`
- CLI: `python -m aresforge test-ollama`
- CLI: `python -m aresforge prepare-local-llm-advisory-run --item-id <item_id> --format json`
- CLI: `python -m aresforge prepare-local-coding-draft --item-id <item_id> --format json`
- CLI: `python -m aresforge inspect-human-gated-patch-application-contract --format json`

## Fields

- `local_llm_provider`
- `provider_base_url`
- `reasoning_model`
- `coding_model`
- `fallback_model`
- `max_context_tokens`
- `request_timeout_seconds`
- `health_check_enabled`
- `execution_enabled`
- `operator_gate_required`
- `notes`
- `updated_at`

Derived read-only metadata:

- `provider_availability_status`
- `provider_configuration_status`
- `provider_execution_mode`
- `provider_state`
- `local_model_profiles`
- `fallback_behavior`

## Supported Providers

- `ollama`
- `none`
- `unknown`

Model fields are placeholders/configuration only. A non-empty model name does not mean the model is installed.

## M83 Provider Contract

`inspect-local-llm-provider-contract` is a read-only provider contract inspector. It uses the local environment contract as input and returns:

- initial provider target: `ollama`
- supported provider targets
- provider base URL and source
- request timeout and health-check timeout expectations
- allowed health endpoint: `/api/tags`
- forbidden inference endpoints such as `/api/generate`, `/api/chat`, `/api/completions`, and `/v1/chat/completions`
- separate reasoning, coding, and fallback model identifiers
- role/capability metadata for local reasoning and local coding lanes
- safety boundary confirmations

The provider contract supports future local reasoning and local coding model selection, but selection remains operator-reviewed metadata. Fallback model configuration is never selected or executed automatically.

Provider contract inspection does not require Ollama to be running. Tests must mock or inspect local files only and must not require a real Ollama service.

## M84 Ollama Health and Model Inspection

`test-ollama` and `inspect-ollama-health` are explicit local-only inspection commands. They return a stable payload with:

- `available`
- `provider`
- `endpoint`
- `models`
- `error_summary`
- `next_safe_action`
- `model_inspection_contract`
- `safety_boundary`

The inspection path may call only the configured local Ollama `/api/tags` endpoint. It must not call `/api/generate`, `/api/chat`, `/api/completions`, `/v1/chat/completions`, or any prompt-bearing endpoint.

When Ollama is not running, the command should still succeed as an inspection operation and return `available: false`, an `error_summary`, an empty model list, and a next safe operator action. This offline state is not a normal project readiness blocker.

Visible model names are metadata only. Model presence does not authorize prompt execution, local LLM advisory execution, repo mutation, queue mutation, queue completion, automatic fallback selection, or automatic next-item execution.

## M85 Advisory Run Artifacts

`prepare-local-llm-advisory-run` creates a local prompt artifact for one queue item. The default behavior is artifact-only and does not call Ollama.

The optional `--run` flag is an explicit operator gate for advisory output. When used, the command first inspects local Ollama model availability and then may call the local `/api/generate` endpoint for advisory text. The response and run metadata are stored under `artifacts/local_llm_advisory/generated/`.

Required output includes:

- `prompt_path`
- `response_path`
- `metadata_path`
- `provider_model_metadata`
- `safety_boundary`
- `boundary_confirmations`
- `next_safe_action`

Unavailable provider or model states return safe unavailable metadata. They do not fail normal project readiness and do not authorize fallback execution.

Advisory artifacts and responses are never applied automatically to repository files, queue state, project state, GitHub, `gh`, Codex, agents, commits, pushes, workflows, daemons, watchers, or schedulers.

## M87 Local Coding Draft Artifacts

`prepare-local-coding-draft` creates a local coding draft prompt artifact for one queue item. The default behavior is artifact-only and does not call Ollama.

The optional `--run` flag is an explicit operator gate for draft output. When used, the command first inspects local Ollama model availability and then may call the local `/api/generate` endpoint for draft patch or instruction text. The draft and run metadata are stored under `artifacts/local_coding_drafts/generated/`.

Required output includes:

- `prompt_path`
- `draft_path`
- `metadata_path`
- `provider_model_metadata`
- `draft_contract`
- `safety_boundary`
- `boundary_confirmations`
- `next_safe_action`

Draft output may include patch-like text, but it is not an applied patch. It is non-authoritative manual guidance only. A draft artifact must not mutate repository files, apply patches, mutate queue state, complete queue items, start next items, call GitHub, call `gh`, or trigger workflows, daemons, watchers, schedulers, or external workflow systems.

## M88 Human-Gated Patch Application Contract

`inspect-human-gated-patch-application-contract` reports the contract for any future manual patch application path.

The contract defines:

- required patch artifact fields, including source draft artifact path, target item id, patch format, target files, patch text, rationale, risks, expected validation, provider/model metadata, and applied/manual review booleans
- explicit operator approval requirements, including the approval phrase `APPROVE LOCAL PATCH APPLICATION`
- pre-apply safety gates for local-only operation, approval record presence, patch schema validation, target file scoping, path traversal prevention, manual diff review, validation plan presence, and no external workflow behavior
- post-apply validation requirements, including operator final diff review, `git diff --check`, targeted tests, relevant smoke checks, and separate queue evidence completion

M88 remains dry-run only. The contract inspector does not apply patches, mutate repository files, mutate queue state, complete queue items, start another item, invoke a provider, call GitHub APIs, call `gh`, create issues or PRs, touch workflows, or run daemon, watcher, scheduler, or external workflow behavior.

## Provider Availability States

M72 exposes provider state in operator-readable form:

- `configured`: supported local provider configuration is syntactically complete
- `missing_configuration`: provider, local URL, or model configuration is incomplete
- `unavailable`: explicit health check could not reach the configured local provider
- `unsupported`: provider value or URL is not allowed for local LLM workflows
- `disabled`: provider is intentionally set to `none`
- `prototype_only`: execution mode is enabled only for the M62 explicit operator-gated prototype

These states are review metadata. They do not authorize automatic execution.

## Local Model Profiles

M72 derives advisory profile metadata for:

- reasoning model -> intended lane `local_reasoning_llm`
- coding model -> intended lane `local_coding_llm`
- fallback model -> intended lane `fallback`

Each profile includes provider, model name, intended lane, recommended use, hardware notes, status, advisory warning, and prototype warning. Profile status may be `configured`, `missing_configuration`, `unavailable`, `unsupported`, or `disabled` depending on provider configuration and explicit health-check results.

Fallback behavior is explicit: fallback model names are advisory operator review metadata only and are never selected or executed automatically.

## Validation

- `local_llm_provider` must be `ollama`, `none`, or `unknown`.
- `provider_base_url` may be blank for `none` or `unknown`.
- `execution_enabled` may be `false` or `true`; `true` enables only the M62 operator-gated local execution prototype.
- `operator_gate_required` must remain `true`.
- `health_check_enabled` may be true or false, but does not trigger a health check in M58.
- Model names may be blank; non-blank values are strings.
- `max_context_tokens` and `request_timeout_seconds` must be positive integers when supplied.
- provider/model metadata must remain advisory and non-executing.

## M59 Health Check

The health check is explicitly invoked only.

Required output includes:

- provider
- provider base URL
- configured reasoning model
- configured coding model
- provider reachability
- available models
- configured model availability
- `inference_tested: false`
- `execution_allowed: false`
- provider availability/configuration status
- local model profile status
- fallback behavior
- warnings and blockers

For provider `ollama`, the health check may call only the local `/api/tags` endpoint. It must not call generate, chat, completion, or prompt endpoints.

Provider URLs must be local: `localhost`, `127.0.0.1`, or `::1`.

M64 records a local audit summary for health check outcomes. The audit entry records provider/model metadata and outcome, not secrets or prompt content.

## M61 Prompt Preview

Local LLM Prompt Preview is copy/paste preview generation only.

Preview may proceed when:

- a queue item exists
- routing metadata recommends `local_reasoning_llm` or `local_coding_llm`
- this environment contract is readable
- the recommended model is available from routing metadata or this environment contract
- project policy does not require `manual_only` handling without operator override

Preview blocks or warns for:

- `codex_cli` routes
- unrouted queue items
- provider `none` or `unknown`
- missing local model configuration
- malformed local LLM environment contract
- high-risk local preview that may need Codex review

Preview output includes local-only operating rules, validation expectations, routing metadata, and `execution_allowed: false`. Optional artifact output is local-only and refuses to overwrite existing files unless `force=true`.

M64 records prompt preview audit entries for generated and blocked previews. Audit entries do not store the full generated prompt.

M65 classifies prompt preview as a preview-only action. Gate output keeps `execution_allowed: false` for preview and reports blockers/warnings without calling a provider.

## M62 Execution Prototype

Local LLM execution is conservative and operator-gated.

Execution may proceed only when:

- the queue item exists
- routing metadata recommends `local_reasoning_llm` or `local_coding_llm`
- provider is local `ollama`
- provider URL points to `localhost`, `127.0.0.1`, or `::1`
- `execution_enabled` is `true`
- `operator_gate_required` remains `true`
- prompt preview is generated
- local health check confirms provider reachability and model availability
- real execution request has `confirm_operator_gate: true`
- high or critical risk has `operator_override: true`

Execution output is advisory only. It may be written to a local result artifact if the operator provides an output path. It is never applied to repo files, queue status, project state, GitHub, `gh`, Codex, agents, commits, pushes, or workflows.

M64 records dry runs, blocked attempts, and advisory execution outcomes in the local audit log. Audit entries prefer summaries and artifact paths over full response text.

M65 centralizes execution gate reporting for this path. The local LLM execution helper consults the gate for operator confirmation, local routing, high/critical risk override, and manual policy decisions without adding any provider behavior.

## Boundaries

- local-only
- file-backed
- operator-gated
- advisory-only
- prototype-scoped
- non-mutating
- configuration and health metadata only
- prompt preview metadata only
- local LLM execution only through M62 explicit operator-gated prototype
- no routing execution
- no Codex execution
- no agent execution
- no GitHub API or `gh`
- no external/network execution beyond explicitly operator-invoked local provider health check and local provider execution behavior
- no automatic queue progression, commit, push, workflow, or repository file mutation from local LLM output

## Next Phase Safety Gates

Before any local LLM coding-output expansion can move beyond advisory prototype behavior:

- explicit operator approval
- one queue item at a time
- no automatic next-item execution
- run state tracked
- stdout/stderr/artifacts captured where applicable
- error and completion states recorded
- review evidence required before marking complete
- queue/dependency blocking enforced
- local validation required before commit/push

## Next Milestones

M61 added Local LLM Prompt Preview without execution.

M62 added the first operator-gated local execution prototype.

M64 added the local Execution Audit Log without expanding execution.

M65 added the AI Action Safety Gate for consistent decision reporting without expanding execution.

M66 added the AI Artifact Registry for generated advisory artifacts without expanding execution.

M67 added the Operator Run History Panel as a read-only timeline.

M68 reconciled local AI operations docs and validation without expanding execution.

M69 hardened local AI operations around edge cases, blocked/error metadata, and non-mutation state.

M70 completed a verification sweep of the M58-M69 local AI operations chain without expanding execution.

M71 added an operator-facing AI Action Review Panel without adding execution.

M72 hardened local LLM provider/model configuration.

M73 improved prompt-pack quality and routing guidance.

M74 stabilized Hub UX wording.

M75 reconciles source-of-truth docs and prepares M76-M82 without expanding local LLM execution.

M81 adds local LLM advisory lane readiness inspection without expanding local LLM execution.
