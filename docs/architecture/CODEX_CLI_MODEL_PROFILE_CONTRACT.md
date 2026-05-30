# Codex CLI Model Profile Contract

## Status

M60 adds a local-only Codex CLI Model Profile Contract. M63 adds Codex CLI High-Value Lane prompt generation that may reference queue routing metadata and model profile intent, but still does not execute Codex.

M64 adds a local Execution Audit Log. Codex high-value prompt generation is summarized in `.aresforge/execution_audit_log.json`, but the audit log does not execute Codex, invoke Codex CLI, or store full generated prompt text.

M65 adds a centralized AI Action Safety Gate. Codex high-value prompt generation may consult the gate as preview-only decision/reporting logic, while Codex execution remains blocked and unimplemented.

M66 adds a local AI Artifact Registry. Codex high-value prompt artifacts are registered when explicitly written, but the registry does not execute Codex or invoke Codex CLI.

M67 adds an Operator Run History panel that can display Codex high-value prompt audit and artifact records in a read-only timeline. It does not execute Codex or invoke Codex CLI.

M68 reconciles local AI operations documentation and confirms that Codex high-value lane behavior remains prompt generation/operator handoff only.

M69 hardens the Codex-adjacent safety posture. Codex high-value lane payloads, audit entries, artifacts, and run-history records now make prompt-only, advisory-only, non-mutation, safety-status, and gate-status state explicit. Codex execution, Codex CLI invocation, GitHub API calls, `gh`, issues, PRs, workflows, and automatic repository mutation remain blocked and unimplemented.

M70 verifies the full M58-M69 local AI operations chain. It reconciles documentation and payload wording, confirms the Codex high-value lane remains prompt-generation/operator-handoff only, and does not add Codex CLI invocation or automatic execution behavior.

M73 improves routing-aware prompt-pack guidance. Prompt packs that reference the Codex high-value lane now explicitly state prompt-generation/operator-handoff only, include advisory model/engine recommendation metadata, and continue to prohibit Codex CLI invocation unless a future approved milestone explicitly permits it.

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
- `GET /api/execution-audit-log`
- `POST /api/ai-action-safety-gate`
- `GET /api/ai-artifacts`
- `GET /api/operator-run-history`

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
- audit logging is local-only and non-executing
- safety gate decisions are local-only and non-executing
- artifact registry tracking is local-only and non-executing
- operator run history is local-only, read-only, and non-executing

## Next Milestone Relationship

M63 uses the `codex_cli` engine key and high-value lane concept for prompt generation only. It keeps output advisory and copy/paste/operator-controlled, returns `execution_allowed: false`, and preserves the no GitHub/`gh` boundary.

M64 adds an Execution Audit Log for operator-gated local execution and advisory outputs without adding automatic Codex or GitHub execution.

M65 adds an AI Action Safety Gate before any future expansion of AI execution behavior. Codex prompt generation remains advisory and preview-only, while Codex execution remains blocked.

M66 adds an AI Artifact Registry for generated advisory artifacts without adding automatic Codex or GitHub execution.

M67 adds an Operator Run History Panel for read-only audit/artifact timeline review.

M68 reconciles local AI operations documentation without adding automatic Codex or GitHub execution.

M69 hardened local AI operations around edge cases, blocked/error metadata, and non-mutation state.

M70 completed a verification sweep of the M58-M69 local AI operations chain without adding Codex execution or GitHub behavior.
