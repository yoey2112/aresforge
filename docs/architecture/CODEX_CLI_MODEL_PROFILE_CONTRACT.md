# Codex CLI Model Profile Contract

## Status

M80 adds LLM Decision Matrix v2 as advisory routing logic. `inspect-llm-decision-matrix` classifies one local queue item for local LLM vs Codex, coding vs reasoning, model/profile selection, task size, risk, validation burden, and safety gating. Prompt Builder and workflow preparation payloads include this decision matrix for operator review. The matrix does not execute prompts, call Codex, invoke local LLMs, mutate queue or source files, complete work, or start the next item. Codex recommendations still require the separate M78 approval and runner gates.

M79.3 adds token usage capture for operator-gated Codex dispatch runs. The runner parses the captured CLI transcript footer `tokens used` followed by a numeric line, including comma-separated totals such as `221,534`, and stores the result in `run_state.json` as `token_usage`. `inspect-codex-dispatch-run` returns this metadata and remains compatible with older run states that predate the field by reporting unavailable token usage with a clear extraction error. This is accounting metadata only and does not complete queue items, dispatch the next item, call GitHub, call `gh`, or expand local LLM execution.

M79.1 hardens the M78 Codex dispatch runner for Windows operator workflows. Run-state JSON reads tolerate UTF-8 BOMs, subprocess stdout/stderr are captured as bytes and decoded with UTF-8-sig plus replacement handling, and the full reviewed prompt artifact is sent to the subprocess over UTF-8 stdin so multi-line prompt bodies are preserved. The run state records prompt handoff and output decoding metadata. Dispatch remains local-only, operator-gated, one item at a time, and unable to complete queue items or run the next item automatically. Windows Codex sandbox limitations may still require an operator to commit and push manually when `.git` writes are blocked.

M78.5 adds a local Prompt Builder Agent / Prompt Architect Agent contract and a workflow preparation command before Codex approval or dispatch. `prepare-queue-item-dispatch` can inspect readiness, optionally start a ready item only with `--start-if-ready`, generate a local prompt artifact, and inspect the Codex dispatch contract. It does not approve Codex dispatch, execute Codex, invoke local LLMs, dispatch prompts, complete queue items, or run the next item automatically.

M78 adds the first operator-gated local dispatch prototype on top of the M77 contract. It requires the exact approval phrase `APPROVE CODEX DISPATCH`, allows only one active run at a time, stores run state under `.aresforge/codex_dispatch/runs/<run_id>/`, captures `prompt.txt`, `stdout.txt`, `stderr.txt`, and `artifacts/`, and leaves successful runs in `review_required`. M78 does not infer a Codex command; the operator must provide `--command`, so tests and smoke checks can use harmless local commands without requiring Codex CLI installation. Dispatch output does not complete queue items, does not auto-run the next item, does not call GitHub or `gh`, and does not expand local LLM execution.

M77 adds the Codex CLI Dispatch Contract. It is local-only, contract-first, and dry-run/no-execute. It inspects one queue item at a time, validates the managed project/repo binding, reserves future `.aresforge/codex_dispatch` contract/run paths, and defines the expected M78 run-state shape. It does not invoke Codex CLI, dispatch Codex, start runs, mutate queue item status, call GitHub, call `gh`, or implement M78 execution.

M60 adds a local-only Codex CLI Model Profile Contract. M63 adds Codex CLI High-Value Lane prompt generation that may reference queue routing metadata and model profile intent, but still does not execute Codex.

M64 adds a local Execution Audit Log. Codex high-value prompt generation is summarized in `.aresforge/execution_audit_log.json`, but the audit log does not execute Codex, invoke Codex CLI, or store full generated prompt text.

M65 adds a centralized AI Action Safety Gate. Codex high-value prompt generation may consult the gate as preview-only decision/reporting logic, while Codex execution remains blocked and unimplemented.

M66 adds a local AI Artifact Registry. Codex high-value prompt artifacts are registered when explicitly written, but the registry does not execute Codex or invoke Codex CLI.

M67 adds an Operator Run History panel that can display Codex high-value prompt audit and artifact records in a read-only timeline. It does not execute Codex or invoke Codex CLI.

M68 reconciles local AI operations documentation and confirms that Codex high-value lane behavior remains prompt generation/operator handoff only.

M69 hardens the Codex-adjacent safety posture. Codex high-value lane payloads, audit entries, artifacts, and run-history records now make prompt-only, advisory-only, non-mutation, safety-status, and gate-status state explicit. Codex execution, Codex CLI invocation, GitHub API calls, `gh`, issues, PRs, workflows, and automatic repository mutation remain blocked and unimplemented.

M70 verifies the full M58-M69 local AI operations chain. It reconciles documentation and payload wording, confirms the Codex high-value lane remains prompt-generation/operator-handoff only, and does not add Codex CLI invocation or automatic execution behavior.

M73 improves routing-aware prompt-pack guidance. Prompt packs that reference the Codex high-value lane now explicitly state prompt-generation/operator-handoff only, include advisory model/engine recommendation metadata, and continue to prohibit Codex CLI invocation unless a future approved milestone explicitly permits it.

M74 stabilized Hub UX wording around Codex high-value prompt preview/copy behavior. M75 reconciles source-of-truth documentation and roadmap sequencing. Neither milestone implements Codex CLI dispatch.

This contract represents future Codex CLI model preferences for routing, high-value lane planning, and future contract-first dispatch design. It does not execute Codex CLI, send prompts, run agents, call GitHub, call `gh`, or run external workflows.

M78.5 follow-on note: the Prompt Builder Agent / Prompt Architect Agent now creates high-quality prompt artifacts from queue items, docs, routing metadata, model profiles, and safety gates for operator review before dispatch. It must not execute prompts, call Codex, invoke local LLMs, mutate files, or advance queue items automatically.

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

## M78.5 Prompt Builder Workflow

Command:

- `python -m aresforge prepare-queue-item-dispatch --item-id <item_id> --target codex --format json`
- `python -m aresforge inspect-llm-decision-matrix --item-id <item_id> --format json`

Stable preparation fields include:

- `ok`
- `local_only`
- `item_id`
- `project_id`
- `repo_id`
- `target`
- `readiness_status`
- `can_start`
- `started`
- `prompt_artifact_path`
- `dispatch_contract_summary`
- `operator_approval_required`
- `dispatch_ready`
- `dispatch_allowed`
- `automatic_next_item_execution_allowed`
- `queue_completion_allowed`
- `warnings`
- `blockers`
- `next_safe_action`
- `boundary_confirmations`

Prompt Builder fields include:

- `artifact_only: true`
- `prompt_builder_version`
- `prompt_preview`
- `source_context`
- `safety_boundaries`
- `validation_plan`
- `smoke_checks`
- `final_response_requirements`
- `llm_decision_matrix`

M78.5 invariants:

- `dispatch_allowed` remains false in preparation.
- `automatic_next_item_execution_allowed` remains false.
- `queue_completion_allowed` remains false.
- Codex targets still require explicit M78 operator approval.
- Prompt Builder does not execute prompts, call Codex, invoke local LLMs, mutate source files, or advance queue items automatically.

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
- no Codex CLI dispatch implemented today
- no prompt execution
- no agent execution
- no GitHub API or `gh`
- no GitHub issues, PRs, workflow activity, or GitHub mutation
- no external workflow execution
- no unattended multi-item execution
- no automatic repository mutation from Codex output
- audit logging is local-only and non-executing
- safety gate decisions are local-only and non-executing
- artifact registry tracking is local-only and non-executing
- operator run history is local-only, read-only, and non-executing

## Future Dispatch Safety Gates

Before Codex CLI dispatch can be implemented:

- explicit operator approval
- one queue item at a time
- no automatic next-item execution
- run state tracked
- stdout/stderr/artifacts captured where applicable
- error and completion states recorded
- review evidence required before marking complete
- queue/dependency blocking enforced
- local validation required before commit/push

## Next Milestone Relationship

M63 uses the `codex_cli` engine key and high-value lane concept for prompt generation only. It keeps output advisory and copy/paste/operator-controlled, returns `execution_allowed: false`, and preserves the no GitHub/`gh` boundary.

M64 adds an Execution Audit Log for operator-gated local execution and advisory outputs without adding automatic Codex or GitHub execution.

M65 adds an AI Action Safety Gate before any future expansion of AI execution behavior. Codex prompt generation remains advisory and preview-only, while Codex execution remains blocked.

M66 adds an AI Artifact Registry for generated advisory artifacts without adding automatic Codex or GitHub execution.

M67 adds an Operator Run History Panel for read-only audit/artifact timeline review.

M68 reconciles local AI operations documentation without adding automatic Codex or GitHub execution.

M69 hardened local AI operations around edge cases, blocked/error metadata, and non-mutation state.

M70 completed a verification sweep of the M58-M69 local AI operations chain without adding Codex execution or GitHub behavior.

M75 keeps this contract as future planning only. M77 should define a dry-run/no-execute Codex dispatch contract, and M78 may only prototype one explicitly operator-approved item dispatch if that later milestone is approved.

M77 is now complete as a no-execute dispatch contract. M78 remains the first possible milestone for an operator-gated dispatch prototype.

## M77 Dispatch Contract

Commands:

- `python -m aresforge inspect-codex-dispatch-contract --item-id <item_id> --format json`
- `python -m aresforge prepare-codex-dispatch-dry-run --item-id <item_id> --format json`

Stable contract fields include:

- `ok`
- `local_only`
- `dry_run_only`
- `dispatch_contract_version`
- `project_id`
- `repo_id`
- `item_id`
- `queue_item_status`
- `item_ready_for_dispatch_contract`
- `dispatch_allowed`
- `dispatch_blocked_reason`
- `dispatch_mode`
- `execution_mode`
- `operator_approval_required`
- `operator_approval_status`
- `one_item_at_a_time_required`
- `automatic_next_item_execution_allowed`
- `codex_cli_invocation_allowed`
- `codex_cli_command_preview`
- `working_directory`
- `prompt_source`
- `prompt_artifact_path`
- `expected_run_state_path`
- `expected_stdout_path`
- `expected_stderr_path`
- `expected_artifact_dir`
- `expected_audit_fields`
- `expected_completion_evidence_fields`
- `expected_run_state_shape`
- `allowed_dispatch_states`
- `safety_gates`
- `blockers`
- `warnings`
- `next_safe_action`
- `boundary_confirmations`

M77 invariants:

- `dry_run_only` is true.
- `dispatch_allowed` is false.
- `codex_cli_invocation_allowed` is false.
- `automatic_next_item_execution_allowed` is false.
- `operator_approval_required` is true.
- `operator_approval_status` is `not_requested`.
- `execution_mode` is `contract_only` or `dry_run_no_execute`.
- `codex_cli_command_preview` is preview-only and not executable in M77.

Future run-state fields:

- `run_id`
- `item_id`
- `project_id`
- `repo_id`
- `dispatch_state`
- `started_at`
- `completed_at`
- `exit_code`
- `stdout_path`
- `stderr_path`
- `artifact_dir`
- `prompt_artifact_path`
- `operator_approval`
- `review_evidence`
- `validation_evidence`
- `error_summary`
- `token_usage`
- `next_safe_action`

M79.3 token usage fields:

- `available`
- `source`
- `total_tokens`
- `raw`
- `prompt_tokens`
- `completion_tokens`
- `reasoning_tokens`
- `model`
- `provider`
- `reasoning_effort`
- `extraction_error` when unavailable
