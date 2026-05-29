# Local LLM Environment Contract

## Status

M58 adds a local-only Local LLM Environment Contract.

This contract represents future local LLM provider and model configuration. It does not call Ollama, perform health checks, call model APIs, send prompts, execute routing, execute Codex, run agents, or call GitHub.

M59 adds an explicitly invoked Local LLM Health Check. The health check reads this contract and may check local provider availability only. It does not send prompts, run inference, generate text, execute routing, execute Codex, run agents, or call GitHub.

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

## Supported Providers

- `ollama`
- `none`
- `unknown`

Model fields are placeholders/configuration only. A non-empty model name does not mean the model is installed.

## Validation

- `local_llm_provider` must be `ollama`, `none`, or `unknown`.
- `provider_base_url` may be blank for `none` or `unknown`.
- `execution_enabled` must remain `false`.
- `operator_gate_required` must remain `true`.
- `health_check_enabled` may be true or false, but does not trigger a health check in M58.
- Model names may be blank; non-blank values are strings.
- `max_context_tokens` and `request_timeout_seconds` must be positive integers when supplied.

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
- warnings and blockers

For provider `ollama`, the health check may call only the local `/api/tags` endpoint. It must not call generate, chat, completion, or prompt endpoints.

Provider URLs must be local: `localhost`, `127.0.0.1`, or `::1`.

## Boundaries

- local-only
- file-backed
- operator-gated
- configuration and health metadata only
- no prompt execution
- no model inference
- no local LLM generation
- no routing execution
- no Codex execution
- no agent execution
- no GitHub API or `gh`
- no external/network execution beyond explicitly operator-invoked local provider health check behavior

## Next Milestones

M61 should add Local LLM Prompt Preview without execution.

M62 should be the future point for any operator-gated local execution prototype, after health checks and additional gates exist.
