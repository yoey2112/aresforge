# Codex CLI Model Profile Contract

## Status

M60 adds a local-only Codex CLI Model Profile Contract.

This contract represents future Codex CLI model preferences for routing and high-value lane planning. It does not execute Codex CLI, send prompts, run agents, call GitHub, call `gh`, or run external workflows.

## Storage

The contract is stored locally at:

- `.aresforge/codex_cli_model_profiles.json`

Reading defaults does not write this file. Updating the contract writes the file only after validation passes.

## Operator Helpers

- `read_codex_cli_model_profile_contract(...)`
- `update_codex_cli_model_profile_contract(...)`
- `validate_codex_cli_model_profile_contract(...)`

## Hub Routes

- `GET /api/codex-cli/model-profiles`
- `POST /api/codex-cli/model-profiles`

## Fields

- `codex_engine_key`
- `default_codex_model`
- `high_value_codex_model`
- `fast_codex_model`
- `allowed_codex_models`
- `per_project_allowed_models`
- `per_agent_allowed_models`
- `execution_enabled`
- `operator_gate_required`
- `notes`
- `updated_at`

## Validation

- `codex_engine_key` must be `codex_cli`.
- `allowed_codex_models` must be a list of strings.
- `default_codex_model` must be in `allowed_codex_models` when provided.
- `high_value_codex_model` must be in `allowed_codex_models` when provided.
- `fast_codex_model` must be in `allowed_codex_models` when provided.
- `per_project_allowed_models` values must only include allowed models.
- `per_agent_allowed_models` values must only include allowed models.
- `execution_enabled` must remain `false`.
- `operator_gate_required` must remain `true`.

## Boundaries

- local-only
- file-backed
- operator-gated
- configuration only
- no Codex CLI execution
- no prompt execution
- no agent execution
- no GitHub API or `gh`
- no GitHub issues, PRs, workflow activity, or GitHub mutation
- no external workflow execution

## Next Milestone Relationship

M63 should use this contract for Codex CLI High-Value Lane planning. M60 does not implement the lane or execute Codex.
