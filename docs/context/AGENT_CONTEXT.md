# AresForge Agent Context

## M92 Documentation Reconciliation Plan Generator Context

Status: Completed locally on `main`.

Current documentation reconciliation scope:

- `plan-doc-reconciliation` produces a deterministic local documentation reconciliation plan.
- The plan reads source-of-truth docs, local queue state, changed source docs, and recent local commits.
- The plan reports stale/missing sections and recommended documentation updates for manual review.
- The default path writes nothing; `--output` is the only local artifact write path.

Boundaries preserved:

- no documentation mutation or automatic rewrite
- no local LLM invocation, Codex invocation, prompt execution, or generated-doc apply mode
- no queue mutation, queue completion, or automatic next-item execution
- no GitHub API, `gh`, issues, PRs, workflows, daemon, watcher, scheduler, external workflow execution, or GitHub mutation

## M91 Documentation Agent v1 Contract Context

Status: Completed locally on `main`.

Current documentation agent scope:

- `inspect-documentation-agent-contract` reports the local Documentation Agent v1 contract.
- `docs/architecture/DOCUMENTATION_AGENT_CONTRACT.md` defines source-of-truth reconciliation boundaries.
- Plan mode is available as non-mutating documentation reconciliation metadata.
- Apply mode is future work and requires a separate explicit operator gate.

Boundaries preserved:

- no automatic documentation updates from model output
- no queue mutation, queue completion, or automatic next-item execution
- no GitHub API, `gh`, issues, PRs, workflows, daemon, watcher, scheduler, external workflow execution, or GitHub mutation

## M90 Hub Routing Dashboard Data Contract Context

Status: Completed locally on `main`.

Current routing dashboard contract scope:

- `GET /api/local-queue/routing-dashboard` returns read-only routing decision data for local queue items.
- Rows include item id, status, risk, task size, recommended engine, recommended lane, recommended model, confidence score, validation burden, warnings, and blockers.
- The endpoint may filter by `project_id`, `repo_id`, and `status`.
- The payload is intended for Hub/dashboard display and future operator review.

Boundaries preserved:

- no mutation endpoints added
- no prompt execution, local LLM invocation, Codex invocation, or automatic next-item execution
- no queue mutation or queue completion
- no GitHub API, `gh`, issues, PRs, workflows, daemon, watcher, scheduler, external workflow execution, or GitHub mutation

## M89 Model Usage and Token Accounting Report Context

Status: Completed locally on `main`.

Current model usage report scope:

- `inspect-model-usage-report` summarizes local Codex dispatch token usage and missing usage metadata.
- The report includes Codex model/provider/reasoning effort fields when run states contain them.
- The report scans local advisory and coding draft metadata artifacts for provider/model/run status.
- Report output is stdout by default; `--output` is the only write path and writes a local report artifact.

Boundaries preserved:

- no network calls or provider invocation
- no repo mutation unless an operator explicitly supplies `--output`
- no queue mutation, queue completion, or automatic next-item execution
- no GitHub API, `gh`, issues, PRs, workflows, daemon, watcher, scheduler, external workflow execution, or GitHub mutation

## M88 Human-Gated Patch Application Contract Context

Status: Completed locally on `main`.

Current patch application contract scope:

- `inspect-human-gated-patch-application-contract` reports the M88 patch application contract.
- The contract defines patch artifact fields, explicit operator approval requirements, pre-apply safety gates, and post-apply validation requirements.
- The command is read-only and does not apply patches.
- Patch application remains future work behind a separate explicit operator-approved command and validation gates.

Boundaries preserved:

- no automatic file mutation or patch application
- no queue mutation, queue completion, or automatic next-item execution
- no provider invocation from contract inspection
- no GitHub API, `gh`, issues, PRs, workflows, daemon, watcher, scheduler, external workflow execution, or GitHub mutation

## M87 Local Coding Draft Artifact Mode Context

Status: Completed locally on `main`.

Current coding draft artifact scope:

- `prepare-local-coding-draft` generates a local coding draft prompt artifact for one queue item.
- The default path is artifact-only and does not invoke Ollama.
- An explicit `--run` flag may call local Ollama for draft output and writes local draft/metadata artifacts.
- Draft artifacts are marked non-applied, non-authoritative, and manual-review-only.

Boundaries preserved:

- no automatic file mutation or patch application from draft output
- no queue mutation, queue completion, or automatic next-item execution from draft output
- no GitHub API, `gh`, issues, PRs, workflows, daemon, watcher, scheduler, external workflow execution, or GitHub mutation

## M86 Routing Confidence Scoring Context

Status: Completed locally on `main`.

Current confidence scoring scope:

- `inspect-llm-decision-matrix` now includes `routing_confidence`.
- Confidence scoring compares Codex, local LLM advisory, local coding draft, and manual-only lanes.
- Factors include risk, task size, work mode, item type, dependencies, validation burden, provider/model availability, and recovery history.
- The score is deterministic advisory metadata with rationale, warnings, confidence level, and recommended lane.

Boundaries preserved:

- no execution, prompt dispatch, provider invocation, Codex invocation, or agent invocation from scoring
- no queue mutation, queue completion, or automatic next-item execution
- no GitHub API, `gh`, issues, PRs, workflows, daemon, watcher, scheduler, external workflow execution, or GitHub mutation

## M85 Local LLM Advisory Run Artifact Context

Status: Completed locally on `main`.

Current advisory artifact scope:

- `prepare-local-llm-advisory-run` generates a local advisory prompt artifact for one queue item.
- The default path is artifact-only and does not invoke Ollama.
- An explicit `--run` flag may call local Ollama for advisory output and writes local response/metadata artifacts.
- Outputs report prompt path, response path when present, provider/model metadata, safety confirmations, and next safe action.

Boundaries preserved:

- no automatic repo file mutation from advisory output
- no queue mutation, queue completion, or automatic next-item execution from advisory output
- no GitHub API, `gh`, issues, PRs, workflows, daemon, watcher, scheduler, external workflow execution, or GitHub mutation
- local LLM unavailable states are reported safely for operator review

## M84 Ollama Health Check and Model Inspection Context

Status: Completed locally on `main`.

Current Ollama inspection scope:

- `test-ollama` now performs health/model inspection only and does not invoke generation.
- `inspect-ollama-health` exposes the same local-only inspection path for operator review.
- The payload reports `available`, `provider`, `endpoint`, visible `models`, `error_summary`, and `next_safe_action`.
- Ollama being offline is reported as `available: false` with warning metadata and does not block normal project readiness.

Boundaries preserved:

- only the local `/api/tags` endpoint may be checked
- no prompts are sent and no inference or generation endpoint is called
- no repo file mutation, queue mutation, queue completion, or automatic next-item execution
- no GitHub API, `gh`, issues, PRs, workflows, daemon, watcher, scheduler, external workflow execution, or GitHub mutation

## M83 Local LLM Provider Contract Context

Status: Completed locally on `main`.

Current provider contract scope:

- `inspect-local-llm-provider-contract` inspects provider metadata without invoking Ollama.
- Ollama is the initial provider target.
- The payload reports local provider URL source, timeout expectations, allowed health-check endpoint, forbidden inference endpoints, reasoning/coding/fallback model identifiers, model roles, capabilities, and safety boundaries.
- Reasoning and coding model selection remain metadata for future operator-gated lanes.

Boundaries preserved:

- no prompt execution from provider contract inspection
- no local LLM provider invocation from provider contract inspection
- no repo file mutation, queue mutation, queue completion, or automatic next-item execution
- no GitHub API, `gh`, issues, PRs, workflows, daemon, watcher, scheduler, external workflow execution, or GitHub mutation

## M82 Self-Managed AresForge Test Run Context

Status: Completed locally on `main`.

Current dogfood scope:

- `inspect-local-project-report` now includes `self_managed_readiness_summary` for AresForge as its own managed project.
- The summary reports managed project selection, local queue status, M81/M82 posture, recovered dispatch run evidence, and read-only readiness flows.
- Recovered failed dispatch runs remain non-blocking only when dependency completion evidence is present and audited.

Boundaries preserved:

- no automatic next-item execution or unattended multi-item execution
- no repo file mutation or queue mutation from report output
- no GitHub API, `gh`, issues, PRs, workflows, daemon, watcher, scheduler, external workflow execution, or GitHub mutation
- operator review remains required before evidence closeout

## M81 Local LLM Advisory/Coding Lane Prototype Context

Status: Completed locally on `main`.

Current advisory lane scope:

- `inspect-local-llm-advisory-lane-readiness` inspects one local queue item without invoking a provider.
- The payload composes queue readiness, M80 decision metadata, and local LLM environment/model profile metadata.
- The advisory plan is structured JSON and names allowed advisory outputs, forbidden outputs, required response fields, validation expectations, and safety confirmations.

Boundaries preserved:

- no prompt dispatch
- no local LLM provider invocation from the readiness command
- no repo file mutation, queue mutation, queue completion, or automatic next-item execution
- no GitHub API, `gh`, issues, PRs, workflows, external workflow execution, or GitHub mutation
- any future local LLM invocation remains separate, explicit, local-only, operator-gated, and non-mutating

Recommended next milestone:

- M82 Self-Managed AresForge Test Run after M81 validation and evidence review.

## M79.4 Codex Dispatch Recovery and Windows argv Hardening Context

Status: In progress locally on `main`.

Current hardening scope:

- `recover-codex-dispatch-run` marks one explicitly named local dispatch run as recovery-required without completing queue work.
- Active stale states such as `approved_pending_dispatch` and `running` are converted to `failed` so they no longer look like live dispatches.
- Recovered run state records `recovery_required`, previous dispatch state, recovery note, and review/validation requirements.
- Dispatch and validation command strings now use Windows-aware argv splitting, while `--command-arg` remains the preferred Windows-safe operator path.

Boundaries preserved:

- dispatch remains local-only and explicitly operator-gated
- recovery does not complete queue items
- no automatic next-item execution
- no GitHub API, `gh`, issues, PRs, workflows, external workflow execution, or GitHub mutation
- no local LLM execution expansion

Recommended next milestone:

- Review M79.4 validation and recovery evidence; do not mark the queue item complete or start the next item automatically.

## M80 LLM Decision Matrix v2 Context

Status: In progress locally on `main`.

Current decision matrix scope:

- `inspect-llm-decision-matrix` inspects one local queue item and returns advisory routing decisions.
- The payload covers work mode, local LLM vs Codex engine recommendation, agent lane, model/profile selection source, task size, risk classification, validation burden, safety gates, and blocked execution flags.
- Prompt Builder artifacts and `prepare-queue-item-dispatch` payloads include the decision matrix as review metadata.

Boundaries preserved:

- Prompt Builder output remains artifact-only and non-executing
- decision matrix inspection does not call Codex, invoke local LLMs, dispatch prompts, mutate source files, mutate queue state, complete queue items, or start next items
- Codex recommendations still require the separate M78 approval and runner path
- local LLM recommendations remain advisory-only and non-mutating
- no GitHub API, `gh`, issues, PRs, workflows, external workflow execution, or GitHub mutation

Recommended next milestone:

- M81 Local LLM Advisory/Coding Lane Prototype after M80 review, validation, and queue evidence.

## M79.3 Codex Run Token Usage Capture Context

Status: In progress locally on `main`.

Current token accounting scope:

- Codex dispatch runs parse the captured CLI transcript footer `tokens used` followed by a numeric line.
- Comma-separated totals such as `221,534` are normalized into `token_usage.total_tokens`.
- Run state now stores `token_usage` with source `codex_cli_transcript_footer` when available, or an unavailable object with a clear `extraction_error`.
- `inspect-codex-dispatch-run` exposes `token_usage` and remains backward-compatible with older `run_state.json` files that do not contain the field.

Boundaries preserved:

- dispatch remains local-only and explicitly operator-gated
- no automatic queue completion
- no automatic next-item execution
- no GitHub API, `gh`, issues, PRs, workflows, external workflow execution, or GitHub mutation
- no local LLM execution expansion

Recommended next milestone:

- Review and validate M79.3 evidence; do not mark the queue item complete or start M80 automatically.

## M79.2 Single-Item Ready-to-Codex Automation Context

Status: In progress locally on `main`.

Current automation scope:

- `run-single-ready-codex-queue-item` processes exactly one manually ready/startable queue item.
- If `--item-id` is omitted, zero ready items and multiple ready items both fail safely.
- If `--item-id` is supplied, only that item is considered and it must be ready/startable.
- The workflow composes existing prompt preparation, M78 approval, M79.1 hardened stdin dispatch, validation commands, implementation commit/push, queue evidence capture, queue closeout, and queue evidence commit/push.
- Codex failure, validation failure, or implementation commit/push failure does not complete the item and records recovery state where possible.
- No next queue item is started automatically.

Boundaries preserved:

- explicit local command only; no watcher, daemon, scheduler, polling, file-change trigger, or unattended worker
- Prompt Builder output remains artifact-only and non-executing
- Codex dispatch still requires the exact M78 approval phrase
- no automatic next-item execution
- no local LLM execution expansion
- no GitHub API, `gh`, GitHub issues, PRs, workflows, external workflow execution, or GitHub mutation

Recommended next milestone:

- Complete M79.2 validation and evidence capture; do not start M79.3 or later items automatically.

## M79.1 Codex CLI Windows Runner Hardening Context

Status: In progress locally on `main`.

Current hardening scope:

- M78 runner approval and execution gates remain unchanged.
- Dispatch run-state JSON is read with BOM-tolerant decoding for Windows-authored `run_state.json` files.
- Dispatch stdout/stderr capture uses bytes plus tolerant UTF-8-sig decoding, avoiding platform-default decoding failures.
- The reviewed prompt artifact is copied into the run directory and sent to the subprocess over UTF-8 stdin so full multi-line prompts are delivered.
- Run-state records expose prompt handoff and decoding metadata for review.
- Current Codex sandbox behavior may prevent commits/pushes because `.git` can be outside writable sandbox permissions; in that case, leave validated source changes unstaged/uncommitted for the operator to commit and push.

Boundaries preserved:

- no automatic prompt dispatch beyond the explicitly approved M78 runner command
- no automatic queue completion
- no automatic next-item execution
- no GitHub API, `gh`, GitHub issues, PRs, workflows, external workflow execution, or GitHub mutation from AresForge
- no local LLM execution expansion

Recommended next milestone:

- Finish M79.1 validation and evidence capture without marking the item complete automatically.

## M78.5 Operator Workflow Compression and Prompt Builder Agent Contract

Status: Completed locally on `main`.

Purpose:

- reduce repeated operator copy/paste between queue readiness, item start, prompt generation, dispatch contract inspection, and handoff review
- add a first-class Prompt Builder Agent / Prompt Architect Agent contract for high-quality prompt artifacts
- keep M79 focused on queue blocking and sequencing enforcement

Implemented in M78.5:

- `build_prompt_builder_agent_contract(...)`
- `prepare_queue_item_dispatch(...)`
- CLI command: `python -m aresforge prepare-queue-item-dispatch --item-id <item_id> --target codex --format json`
- optional start gate: `--start-if-ready`
- optional prompt artifact output override: `--output <path> --force`

Prompt Builder boundaries:

- artifact-only
- local-only
- does not execute prompts
- does not call Codex
- does not invoke local LLMs
- does not mutate source files
- does not advance queue items automatically
- does not complete queue items

Preparation boundaries:

- inspects readiness and dispatch contract state
- generates or updates a local prompt artifact for operator review
- may start a ready item only when `--start-if-ready` is explicitly supplied
- does not approve Codex dispatch
- does not dispatch automatically
- does not run Codex
- does not run the next item automatically
- does not complete the queue item

Recommended next milestone:

- M79 - Queue Blocking and Sequencing Enforcement.

## M78 Operator-Gated Codex CLI Dispatch Prototype Context

Status: Completed locally on `main`.

Purpose:

- add the first safe local Codex CLI dispatch prototype after the M77 contract
- require explicit operator approval before invocation
- allow exactly one active run at a time
- capture run state, prompt artifact, stdout, stderr, and artifact directory locally
- leave queue completion as a separate operator-reviewed and validation-evidenced action

Implemented in M78:

- `approve_codex_dispatch(...)`
- `run_operator_gated_codex_dispatch(...)`
- `inspect_codex_dispatch_run(...)`
- `list_codex_dispatch_runs(...)`
- `cancel_codex_dispatch_run(...)`
- `validate_codex_dispatch_run_state(...)`
- CLI commands: `approve-codex-dispatch`, `run-codex-dispatch`, `inspect-codex-dispatch-run`, `list-codex-dispatch-runs`, and `cancel-codex-dispatch-run`

Operator command shape:

- `python -m aresforge approve-codex-dispatch --item-id m78-operator-gated-codex-cli-dispatch-prototype --approved-by local_operator --approval-phrase "APPROVE CODEX DISPATCH" --format json`
- `python -m aresforge run-codex-dispatch --item-id m78-operator-gated-codex-cli-dispatch-prototype --run-id <run_id> --command "<operator-provided command>" --format json`
- Windows-friendly alternative: `python -m aresforge run-codex-dispatch --item-id m78-operator-gated-codex-cli-dispatch-prototype --run-id <run_id> --command-arg python --command-arg=-c --command-arg "print('codex dispatch smoke')" --format json`
- `python -m aresforge inspect-codex-dispatch-run --run-id <run_id> --format json`

Run-state storage:

- `.aresforge/codex_dispatch/runs/<run_id>/run_state.json`
- `.aresforge/codex_dispatch/runs/<run_id>/prompt.txt`
- `.aresforge/codex_dispatch/runs/<run_id>/stdout.txt`
- `.aresforge/codex_dispatch/runs/<run_id>/stderr.txt`
- `.aresforge/codex_dispatch/runs/<run_id>/artifacts/`

Boundaries:

- no automatic next-item execution
- no queue item status mutation from dispatch
- no automatic queue completion from Codex output
- review evidence and validation evidence are required before queue completion
- no GitHub API, `gh`, issues, PRs, workflows, external workflow execution, or GitHub mutation
- no local LLM execution expansion; local LLM remains local-only, advisory-only, operator-gated, prototype-scoped, and non-mutating

M78.5 follow-on note:

- M78.5 introduced the Prompt Builder Agent / Prompt Architect Agent artifact contract for reviewed prompt artifacts from queue context, docs, routing metadata, model profiles, and safety gates. It remains prompt-generation only and must not execute prompts, call Codex, invoke local LLMs, mutate files, or advance queue items.

Recommended next milestone:

- M79 - Queue Blocking and Sequencing Enforcement.

## M77 Codex CLI Dispatch Contract Context

Status: Completed locally on `main`.

Purpose:

- define the stable local contract required before any Codex CLI process invocation can exist
- inspect one local queue item at a time
- make future dispatch shape, run-state fields, artifact paths, and safety gates testable
- preserve dry-run/no-execute behavior through M77

Implemented in M77:

- `build_codex_dispatch_contract(...)`
- `inspect_codex_dispatch_contract(...)`
- `prepare_codex_dispatch_dry_run(...)`
- `validate_codex_dispatch_contract_payload(...)`
- CLI command: `python -m aresforge inspect-codex-dispatch-contract --item-id <item_id> --format json`
- CLI command: `python -m aresforge prepare-codex-dispatch-dry-run --item-id <item_id> --format json`
- local artifact path reservations under `.aresforge/codex_dispatch/contracts` and `.aresforge/codex_dispatch/runs`

M77 contract invariants:

- `dry_run_only: true`
- `dispatch_allowed: false`
- `codex_cli_invocation_allowed: false`
- `automatic_next_item_execution_allowed: false`
- `operator_approval_required: true`
- `operator_approval_status: not_requested`
- command previews are preview-only and not executable in M77

Not implemented in M77:

- Codex CLI process invocation
- operator-approved dispatch
- automatic Codex execution
- automatic agent execution
- automatic queue execution
- unattended multi-item execution
- automatic next-item execution
- local LLM execution expansion
- GitHub API, `gh`, issues, PRs, workflows, or GitHub mutation

Future M78 run-state fields:

- `run_id`, `item_id`, `project_id`, `repo_id`, `dispatch_state`, `started_at`, `completed_at`, `exit_code`, `stdout_path`, `stderr_path`, `artifact_dir`, `prompt_artifact_path`, `operator_approval`, `review_evidence`, `validation_evidence`, `error_summary`, and `next_safe_action`

Future M78 gate reminders:

- explicit operator approval must exist before dispatch
- one item at a time must be enforced
- no automatic next-item execution
- run state, stdout, stderr, and artifacts must be captured where applicable
- review evidence is required before completion
- validation evidence is required before commit/push
- dependency blocking must be respected
- GitHub/`gh`/API/workflow mutation remains blocked

Recommended next milestone:

- M78 - Operator-Gated Codex CLI Dispatch Prototype.

## M76 Self-Seed AresForge as the First Managed Project Context

Status: Completed locally on `main`.

Purpose:

- let AresForge recognize and inspect itself as the first managed local project
- seed the next planned milestones into the canonical local queue as reviewable work
- preserve local-only, file-backed, operator-gated behavior

Implemented in M76:

- `seed_aresforge_self_project(...)`
- CLI command: `python -m aresforge seed-aresforge-self-project --format json`
- managed project `aresforge` with primary repo `aresforge-main`
- proposed queue items for M77, M78, M79, M80, M81, and M82
- active-project update only when `--set-active` is supplied

Not implemented in M76:

- Codex CLI dispatch
- automatic Codex execution
- automatic agent execution
- automatic prompt dispatch
- external workflow execution
- GitHub API, `gh`, GitHub issues, GitHub PRs, GitHub workflows, or GitHub mutation from the app
- unattended multi-item queue execution
- local LLM execution expansion
- automatic repo mutation from local LLM or Codex output

Next-phase direction:

- M77 - Codex CLI Dispatch Contract
- M78 - Operator-Gated Codex CLI Dispatch Prototype
- M79 - Queue Blocking and Sequencing Enforcement
- M80 - LLM Decision Matrix v2
- M81 - Local LLM Advisory/Coding Lane Prototype
- M82 - Self-Managed AresForge Test Run

Future-agent reminders:

- Codex remains manual prompt-pack handoff until a future approved milestone changes the contract
- M77 must be contract-first and dry-run/no-execute friendly
- M78 may dispatch only one explicitly operator-approved queue item and must not auto-run the next item
- M79 must block dependent queue movement until completion/review/evidence is recorded
- M80 must decide local LLM vs Codex, coding vs reasoning, model/profile selection, task size, risk, and safety gating without creating autonomous execution
- M81 must start local-only with advisory/reasoning before any coding-output path, and local LLM output remains non-mutating
- M82 must test self-management using AresForge itself while preserving operator gates

Next phase safety gates before any Codex dispatch implementation:

- explicit operator approval
- one queue item at a time
- no automatic next-item execution
- run state tracked
- stdout/stderr/artifacts captured where applicable
- error and completion states recorded
- review evidence required before marking complete
- queue/dependency blocking enforced
- local validation required before commit/push

Recommended next milestone after M76:

- M77 - Codex CLI Dispatch Contract.

## M75 Source-of-Truth Documentation and Roadmap Reconciliation Context

Status: Completed on `main` in commit `7088204`.

Purpose:

- reconciled the major source-of-truth docs after M74
- kept future agents anchored to the current local-first, file-backed, operator-gated, preview/review-only operating model
- prepared the next phase without implementing Codex dispatch, agent execution, GitHub behavior, or external workflow execution

## M74 Hub UX Stabilization Pass Context

Status: Completed locally on `main`.

Current Hub UX state:

- Queue copy more clearly marks local-only, operator-gated, preview-only, and review-only AI operations
- prompt-pack generation is labeled as preview output and has a copy-only prompt-pack preview control for manual operator handoff
- local LLM prototype wording makes provider/model status a prototype configuration signal, not production execution approval
- AI Action Review Panel wording groups safety status, gate status, no automatic execution, no repo mutation, and next safe action labels for operator scanning
- empty states better explain what blocked, audit, artifact, prompt-pack, and AI review panels will show once local data exists

Boundary reminders:

- Hub UX changes did not add backend capabilities or execution controls
- no Codex execution, Codex CLI invocation, local LLM repo mutation, agent execution, GitHub API, `gh`, issue/PR/workflow activity, external workflow execution, or automatic repository mutation was added
- prompt-pack previews and AI review surfaces remain manual/operator handoff only

Recommended next milestone:

- M75 - Source-of-Truth Documentation and Roadmap Reconciliation.

## M73 Prompt Pack Quality and Routing Improvements Context

Status: Completed locally on `main`.

Current prompt-pack contract:

- local queue prompt packs now include lane-specific guidance for high-value Codex, local LLM advisory, documentation/review, and operator-only/manual work
- generated prompt packs include advisory model/engine recommendation metadata, task sizing guidance, validation/smoke expectations, and final response requirements
- high-value Codex lane wording explicitly says prompt-generation/operator-handoff only
- local LLM advisory lane wording explicitly says local LLM output must not mutate repo files
- generated prompt bodies remain copy/paste-friendly and do not use nested markdown fences

Boundary reminders:

- prompt-pack generation is manual operator handoff only and does not dispatch prompts
- no Codex execution, Codex CLI invocation, local LLM execution, agent execution, GitHub API, `gh`, issue/PR/workflow activity, external workflow execution, or repository mutation was added
- model/engine recommendations are advisory metadata only

Recommended next milestone:

- M74 - Hub UX Stabilization Pass.

## M72 Local LLM Provider Configuration Hardening Context

Status: Completed locally on `main`.

Current hardened provider contract:

- local LLM environment reads and updates now expose `provider_availability_status`, `provider_configuration_status`, `provider_execution_mode`, `provider_state`, `local_model_profiles`, and `fallback_behavior`
- provider states are operator-readable: `configured`, `missing_configuration`, `unavailable`, `unsupported`, `disabled`, and `prototype_only`
- model profile metadata is advisory and includes provider, model name, intended lane, recommended use, hardware notes, status, advisory warning, and prototype warning
- local health-check output carries the same provider/model metadata and keeps `inference_tested: false` and `execution_allowed: false`

Boundary reminders:

- provider/model metadata is configuration and review evidence only
- health checks do not send prompts, run inference, generate text, execute routing, execute Codex, run agents, call GitHub, call `gh`, or mutate repo files
- local LLM execution remains limited to the M62 explicit operator-gated local prototype
- local LLM output remains advisory-only and never automatically mutates repo files
- Codex high-value lane remains prompt-generation/operator-handoff only

Recommended next milestone:

- M73 - Prompt Pack Quality and Routing Improvements.

## M71 Operator-Facing AI Action Review Panel Context

Status: Completed locally on `main`.

Current review surface:

- Hub panel: AI Action Review Panel in Queue
- Hub route: `GET /api/ai-action-review`
- data sources: AI action safety metadata already carried through audit entries, execution audit log, AI artifact registry, Operator Run History, and local queue routing metadata
- operator-facing fields include action name, safety status, gate status, blocked action, blocked reason category, blocked reason, no automatic execution flag, no repo mutation flag, artifact references, audit references, run-history timeline entries, queue AI-adjacent actions, and next safe operator action

Boundary reminders:

- the review panel is read-only local evidence and does not add execution controls
- no Codex execution, Codex CLI invocation, local LLM execution, agent execution, GitHub API, `gh`, issue/PR/workflow activity, external workflow execution, or repository mutation is performed from the panel
- local LLM output remains advisory-only and never automatically mutates repo files
- Codex high-value lane remains prompt-generation/operator-handoff only

Recommended next milestone:

- M72 - Local LLM Provider Configuration Hardening.

## M70 Local AI Operations Verification Sweep Context

Status: Completed locally on `main`.

Verification outcome:

- M70 reviewed the implemented M58-M69 local AI operations chain for stale documentation, payload consistency, safety wording, and regression-test coverage
- source-of-truth docs now identify M70 as the latest completed local AI milestone and recommend M71 - Operator-Facing AI Action Review Panel next
- architecture docs now describe M69 hardening as completed and M70 as the verification sweep, not as future execution work
- AI action safety gate policy classification now treats PR-shaped prohibited action names as GitHub mutation representations
- Operator Run History UI timeline rendering now exposes existing safety status, gate status, and non-mutation state

Boundary reminders:

- local LLM execution remains prototype-scoped, local-only, advisory-only, and operator-gated
- local LLM output is not applied to repository files, queue state, project state, GitHub, `gh`, Codex, agents, commits, pushes, or workflows
- Codex high-value lane remains prompt generation and manual operator handoff only
- no GitHub API, `gh`, issues, PRs, workflows, GitHub mutation, automatic Codex execution, automatic agent execution, external workflow execution, or automatic repo mutation was added
- M70 did not add a new feature or execution capability

Recommended next milestone:

- M71 - Operator-Facing AI Action Review Panel.

## M69 Local AI Operations Hardening Context

Status: Completed locally on `main`.

Current hardened local AI operations surface:

- safety gate decisions now expose explicit `safety_status`, `gate_status`, `blocked_action`, `blocked_reason_category`, and operator next-action metadata
- blocked categories distinguish policy-blocked, gate-blocked, missing-operator-approval, and invalid-state outcomes where applicable
- execution audit entries carry safety/gate status plus fixed `repo_mutation_allowed: false`, `external_mutation_allowed: false`, and `automatic_execution_allowed: false`
- AI artifact registry entries remain advisory local records and now carry explicit advisory/non-mutation metadata
- Operator Run History timeline entries reflect audit/artifact safety and non-mutation status consistently

Boundary reminders:

- local LLM execution remains prototype-scoped, local-only, advisory-only, and operator-gated
- local LLM output is not applied to repository files, queue state, project state, GitHub, `gh`, Codex, agents, commits, pushes, or workflows
- Codex high-value lane remains prompt generation and manual operator handoff only
- no GitHub API, `gh`, issues, PRs, workflows, GitHub mutation, automatic Codex execution, automatic agent execution, external workflow execution, or automatic repo mutation was added

Recommended next milestone:

- M70 completed Local AI Operations Verification Sweep.

## M68 Local AI Operations Closeout Context

Status: Completed locally on `main`.

Current implemented local AI operations surface:

- project AI settings, agent/engine registry, queue routing metadata, routing decision matrix v1, routed queue views, and routing-aware prompt packs
- local LLM environment contract, local health check, prompt preview, and M62 operator-gated local execution prototype
- Codex CLI model profile contract and Codex high-value prompt lane
- execution audit log, AI action safety gate, AI artifact registry, and Operator Run History panel

Source-of-truth boundary:

- one canonical local queue remains the source of truth
- routed views are filters over that queue, not separate queues
- local LLM execution remains prototype-only, local-only, advisory-only, and operator-gated
- Codex high-value lane remains prompt generation/operator handoff only
- no output from a local LLM or Codex prompt is applied to repo files automatically
- no GitHub API, `gh`, issues, PRs, workflows, GitHub mutation, automatic Codex execution, automatic agent execution, or external workflow execution

Recommended next milestone:

- M69 - Local AI Operations Hardening.

## M67 Operator Run History Panel Context

Status: Completed locally on `main`.

Current run history contract:

- operator helper: `read_operator_run_history(...)`
- Hub route: `GET /api/operator-run-history`
- Queue UI panel: Operator Run History

Timeline behavior:

- combines M64 execution audit entries and M66 AI artifact records
- returns `audit_entries`, `artifacts`, and a normalized `timeline`
- sorts timeline entries newest first
- supports project id, item id, action type, artifact type, and limit filters

Boundary reminders:

- run history is read-only local evidence
- no execution, apply, delete, GitHub, `gh`, Codex run, local LLM, agent, workflow, issue, or PR controls are exposed
- audit log records action outcomes; artifact registry records generated local artifact files; run history is an operator-facing combined view

Recommended next milestone:

- M68 - Local AI Operations Closeout Reconciliation.

## M66 AI Artifact Registry Context

Status: Completed locally on `main`.

Current artifact registry contract:

- operator helpers: `register_ai_artifact(...)`, `read_ai_artifact_registry(...)`, `filter_ai_artifacts(...)`, `verify_ai_artifact_exists(...)`
- storage path: `.aresforge/ai_artifact_registry.json`
- Hub route: `GET /api/ai-artifacts`
- Queue UI panel: AI Artifact Registry

Supported artifact types:

- `prompt_pack`
- `handoff`
- `local_llm_prompt_preview`
- `local_llm_execution_result`
- `codex_high_value_prompt`
- `report`
- `audit_export`
- `other`

Boundary reminders:

- registry reads and writes never execute Codex, local LLMs, agents, GitHub, `gh`, issues, PRs, workflows, or external services
- registering an artifact records metadata only and never overwrites artifact content
- missing artifact files are represented with `exists: false`
- checksum is local and deterministic when the artifact file exists
- audit log records actions; artifact registry records local generated artifact files

Recommended next milestone:

- M67 - Operator Run History Panel.

## M65 AI Action Safety Gate Context

Status: Completed locally on `main`.

Current safety gate contract:

- operator helper: `evaluate_ai_action_safety_gate(...)`
- Hub route: `POST /api/ai-action-safety-gate`
- behavior: local-only decision/reporting logic

Supported action types:

- `local_llm_prompt_preview`
- `local_llm_execute`
- `codex_high_value_prompt`
- `prompt_pack_generate`
- `routing_recommendation`
- `routing_metadata_update`

Decision values:

- `allowed`
- `blocked`
- `warning`
- `requires_operator_gate`
- `requires_operator_override`
- `preview_only`

Boundary reminders:

- Codex execution and GitHub/`gh` mutation are always blocked
- local LLM execution requires local engine routing and explicit operator gate confirmation for real execution
- high/critical risk local LLM execution requires operator override
- preview-only actions return `execution_allowed: false`
- routing metadata updates require explicit operator action confirmation
- M65 does not add execution behavior or expand M62

Recommended next milestone:

- M66 - AI Artifact Registry.

## M64 Execution Audit Log Context

Status: Completed locally on `main`.

Current audit contract:

- operator helpers: `append_execution_audit_entry(...)`, `read_execution_audit_log(...)`, `filter_execution_audit_log(...)`
- storage path: `.aresforge/execution_audit_log.json`
- Hub route: `GET /api/execution-audit-log`
- Queue UI panel: Execution Audit Log

Logged action types:

- `local_llm_health_check`
- `local_llm_prompt_preview`
- `local_llm_execute`
- `codex_high_value_prompt`
- `prompt_pack_generate`
- `routing_recommendation`
- `routing_metadata_update`
- `blocked_attempt`

Logged fields include `audit_id`, `timestamp`, optional `project_id`/`item_id`, `action_type`, `engine`, optional `model`/`agent_lane`, operator gate state, dry-run/executed/execution-allowed booleans, outcome, blockers, warnings, optional artifact path, summary, and source function.

Boundary reminders:

- audit logging is local-only, file-backed, and best-effort
- audit logging does not execute Codex, local LLMs, agents, GitHub, `gh`, issues, PRs, workflows, or external services
- audit entries should not store full prompt text or full LLM response text
- secret-like strings are redacted from audit fields
- M62 local LLM execution behavior is not expanded

Recommended next milestone:

- M65 - AI Action Safety Gate.

## M63 Codex CLI High-Value Lane Context

Status: Completed locally on `main`.

Current Codex lane contract:

- operator helper: `generate_codex_high_value_lane_prompt(...)`
- Hub route: `POST /api/local-queue/items/{item_id}/codex-high-value-prompt`
- Queue UI panel: Codex High-Value Lane
- source queue: one canonical local queue
- output: advisory `prompt_preview` and optional local artifact

Eligibility:

- `recommended_engine` is `codex_cli`
- `recommended_agent_lane` is `high_value_codex`
- `risk_level` is high or critical
- `complexity_level` is high
- affected area includes backend/operator lifecycle, data contracts, API routes, queue lifecycle, routing matrix, execution path, evidence/closeout, or docs source-of-truth reconciliation
- validation burden is high
- `project_ai_mode` is `codex_only` or `high_confidence`
- operator override requests Codex

Boundary reminders:

- `execution_allowed` is always false
- AresForge does not execute Codex, call Codex CLI, call GitHub API, call `gh`, create issues, create PRs, run workflows, or mutate repo files from Codex output
- Codex may perform coding only when a human operator manually copies the prompt into Codex
- Codex output must be validated locally before commit/push
- M62 local LLM execution remains explicitly operator-gated and unaffected

Recommended next milestone:

- M64 - Execution Audit Log.

## M62 Operator-Gated Local LLM Execution Prototype Context

Status: Completed locally on `main`.

Current execution prototype:

- operator helper: `execute_local_llm_for_queue_item(...)`
- Hub route: `POST /api/local-queue/items/{item_id}/local-llm-execute`
- Queue UI panel: Prototype: Run Local LLM
- supported provider: local `ollama`

Eligibility gates:

- queue item exists
- routing metadata recommends `local_reasoning_llm` or `local_coding_llm`
- local LLM environment has `execution_enabled: true`
- local LLM environment keeps `operator_gate_required: true`
- provider URL is local: `localhost`, `127.0.0.1`, or `::1`
- prompt preview is generated
- real execution has `confirm_operator_gate: true`
- real execution passes local health check and model availability
- high or critical risk requires `operator_override: true`

Boundary reminders:

- dry run does not call the provider
- real execution calls only configured local `ollama`
- output is advisory only
- do not apply output to repo files, queue status, project state, GitHub, `gh`, Codex, agents, commits, pushes, or workflows

Recommended next milestone:

- M63 - Codex CLI High-Value Lane.

## M61 Local LLM Prompt Preview Context

Status: Completed locally on `main`.

Current preview contract:

- operator helper: `generate_local_llm_prompt_preview(...)`
- Hub route: `POST /api/local-queue/items/{item_id}/local-llm-prompt-preview`
- Queue UI panel: Local LLM Prompt Preview
- source queue: one canonical local queue
- source environment: `.aresforge/local_llm_environment.json`

Preview eligibility:

- queue item exists
- routing metadata recommends `local_reasoning_llm` or `local_coding_llm`
- local LLM environment contract is readable
- recommended model is present in routing metadata or the local environment contract
- project policy does not require manual-only handling without operator override

Boundary reminders:

- preview output is copy/paste text only
- `execution_allowed` is always false
- do not call Ollama, local LLMs, Codex CLI, agents, GitHub, `gh`, or external workflows
- do not send prompts, run inference, or claim execution
- artifact output is optional and local only; existing files are not overwritten unless `force=true`

Follow-up:

- M62 added Operator-Gated Local LLM Execution Prototype.

## M60 Codex CLI Model Profile Contract Context

Status: Completed locally on `main`.

Current contract:

- operator helpers: `read_codex_cli_model_profile_contract(...)`, `update_codex_cli_model_profile_contract(...)`, and `validate_codex_cli_model_profile_contract(...)`
- Hub routes: `GET /api/codex-cli/model-profiles` and `POST /api/codex-cli/model-profiles`
- storage path: `.aresforge/codex_cli_model_profiles.json`
- source doc: `docs/architecture/CODEX_CLI_MODEL_PROFILE_CONTRACT.md`

Boundary reminders:

- Codex CLI is represented as engine `codex_cli`
- model profiles are configuration only
- `execution_enabled` remains false for Codex CLI model profiles
- `operator_gate_required` must remain true
- no Codex CLI execution, prompt execution, real agent execution, GitHub integration, `gh`, or external workflow is added
- Codex high-value prompt generation exists, but Codex execution remains unimplemented

Recommended next milestone:

- M63 - Codex CLI High-Value Lane.

## M59 Local LLM Health Check Context

Status: Completed locally on `main`.

Current health-check contract:

- operator helper: `check_local_llm_health(...)`
- Hub route: `POST /api/local-llm/health-check`
- reads `.aresforge/local_llm_environment.json`
- provider `none` or `unknown` returns an unavailable/blocked health result without provider calls
- provider `ollama` may call only the local `/api/tags` endpoint
- output includes provider reachability, available models, configured model availability, `inference_tested: false`, and `execution_allowed: false`

Boundary reminders:

- health check must be explicitly invoked by the operator
- provider URL must be local: `localhost`, `127.0.0.1`, or `::1`
- do not call `/api/generate`, `/api/chat`, completion endpoints, or prompt endpoints
- do not send prompts or task content
- no prompt execution, model inference, local LLM generation, Codex execution, real agent execution, GitHub integration, queue mutation, or external workflow is added

Follow-up:

- M61 added Local LLM Prompt Preview.
- M62 added Operator-Gated Local LLM Execution Prototype.

## M58 Local LLM Environment Contract Context

Status: Completed locally on `main`.

Current contract:

- operator helpers: `read_local_llm_environment_contract(...)`, `update_local_llm_environment_contract(...)`, and `validate_local_llm_environment_contract(...)`
- Hub routes: `GET /api/local-llm/environment` and `POST /api/local-llm/environment`
- storage path: `.aresforge/local_llm_environment.json`
- source doc: `docs/architecture/LOCAL_LLM_ENVIRONMENT_CONTRACT.md`

Supported providers:

- `ollama`
- `none`
- `unknown`

Boundary reminders:

- this is configuration only
- model names are placeholders/config fields and do not prove installation
- `execution_enabled` may be true only for the M62 operator-gated local prototype
- `operator_gate_required` must remain true
- `health_check_enabled` does not run a health check yet
- no Ollama call, model API call, prompt execution, routing execution, local LLM execution, Codex execution, real agent execution, GitHub integration, or external workflow is added

Recommended next milestone:

- M59 - Local LLM Health Check.

## M57 Prompt Pack Routing Integration Context

Status: Completed locally on `main`.

Current prompt-pack routing contract:

- `generate_local_queue_prompt_pack(...)` includes routing metadata in generated prompts by default
- Hub prompt-pack API accepts `include_routing`, `group_by_routing`, `routing_group_by`, `include_unrouted`, and `recommend_missing_routing`
- Queue UI exposes prompt-pack routing controls and preview output
- output item summaries include routing metadata, dependencies, routing guidance, and `execution_allowed: false`
- unrouted items say manual routing is required
- `codex_cli` recommendations say Codex CLI is recommended but not executed
- `local_reasoning_llm` and `local_coding_llm` recommendations say local LLMs are recommended but not executed

Supported routing prompt-pack groups:

- `by_agent_lane`
- `by_engine`
- `by_model`
- `by_risk_level`
- `by_complexity_level`
- `by_status`

Boundary reminders:

- prompt packs are artifacts/previews only
- generation does not start, complete, route, or execute queue items
- no queue split, local LLM execution, Codex execution, real agent execution, GitHub integration, prompt execution, or external workflow is added

Recommended next milestone:

- M58 - Local LLM Environment Contract.

## M56 Routed Queue Views Context

Status: Completed locally on `main`.

Current routed view contract:

- operator helper: `read_local_routed_queue_views(...)`
- Hub route: `GET /api/local-queue/routed-views`
- Queue UI includes a Routed Queue Views panel
- views read from the one canonical local queue and do not write queue state
- unrouted queue items are included by default and can be filtered out
- output includes `execution_allowed: false`

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

Supported groups:

- `by_agent_lane`
- `by_engine`
- `by_model`
- `by_project_policy`
- `by_risk_level`
- `by_complexity_level`
- `by_status`

Boundary reminders:

- routed views are read-only filtered/grouped views, not separate queues
- one canonical local queue remains the source of truth
- no queue storage split, prompt-pack routing integration, routing execution, local LLM execution, Codex execution, real agent execution, GitHub integration, prompt execution, or external workflow is added

Recommended next milestone:

- M57 - Prompt Pack Routing Integration.

## M55 Project AI Settings UI Context

Status: Completed locally on `main`.

Current UI contract:

- Projects section includes a Project AI Settings panel
- panel reads `GET /api/projects/{project_id}/ai-settings`
- panel saves through `POST /api/projects/{project_id}/ai-settings`
- supported modes and engines are exposed as form controls
- validation, warnings, blockers, and `next_safe_action` are shown in the panel

Boundary reminders:

- UI edits project AI settings only
- validation failures are displayed and the backend rejects invalid settings
- no routing execution, local LLM execution, Codex execution, real agent execution, prompt generation/execution, GitHub integration, or external workflow is added
- this is not model management; it is only the M51 settings contract exposed to operators

Recommended next milestone:

- M56 - Routed Queue Views.

## M54 Routing Decision Matrix v1 Context

Status: Completed locally on `main`.

Current recommendation contract:

- operator helpers: `recommend_queue_item_routing(...)` and `apply_queue_item_routing_recommendation(...)`
- Hub routes: `POST /api/local-queue/items/{item_id}/routing-recommendation` and `POST /api/local-queue/items/{item_id}/apply-routing-recommendation`
- Queue UI includes separate Recommend Routing and Apply Routing Metadata actions

Decision inputs:

- queue item details
- optional risk and complexity overrides
- optional affected files and validation burden
- M51 project AI settings
- M52 agent and engine registry
- M53 queue routing metadata validation

Boundary reminders:

- recommendations do not write metadata unless `write_metadata` is requested or the explicit apply helper/route is used
- apply writes metadata only; it does not execute routing
- all outputs keep `execution_allowed: false`
- no local LLM execution, Codex execution, real agent execution, GitHub integration, prompt execution, queue split, or external workflow is added

Recommended next milestone:

- M55 - Project AI Settings UI.

## M53 Queue Routing Metadata Contract Context

Status: Completed locally on `main`.

Current metadata contract:

- operator helpers: `default_queue_routing_metadata(...)`, `validate_queue_routing_metadata(...)`, and `update_local_queue_item_routing_metadata(...)` in `src/aresforge/operator/local_project_queue.py`
- Hub route: `POST /api/local-queue/items/{item_id}/routing-metadata`
- Queue item detail displays routing metadata as read-only context
- existing queue items without metadata are safely viewed with default empty/unassigned metadata

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

Boundary reminders:

- one canonical local queue remains the source of truth
- metadata is stored context only and does not compute routing
- empty/unassigned metadata is allowed
- invalid non-empty lane, engine, risk, or complexity values are rejected by metadata update paths
- no queue storage split, local LLM execution, Codex execution, real agent execution, GitHub integration, prompt execution, or external workflow is added

Recommended next milestone:

- M54 - Routing Decision Matrix v1.

## M52 Agent and Engine Registry Contract Context

Status: Completed locally on `main`.

Current registry contract:

- operator function: `read_agent_engine_registry(...)` in `src/aresforge/operator/local_project_factory.py`
- Hub route: `GET /api/agent-engine-registry`
- registry is static/read-only for now and does not write queue metadata or execute routes

Agent lanes:

- `architect_planner`: architecture, sequencing, constraints, and implementation strategy
- `coding`: implementation-focused prompts and code-change plans
- `reviewer_validator`: change review, validation evidence, readiness, and closeout risk
- `documentation`: docs updates, handoff notes, and source-of-truth summaries
- `test`: validation command planning, test scope, and evidence expectations
- `local_operator_assistant`: local operator workflow, queue triage, and safe next actions
- `high_value_codex`: future Codex-worthy escalation lane for high-risk or high-value work

Engines:

- `local_reasoning_llm`: future local reasoning, review, and operator-assistance engine
- `local_coding_llm`: future local coding-oriented engine
- `codex_cli`: future operator-gated Codex CLI engine with placeholder-only model profiles

Boundary reminders:

- every lane has `routing_only: true` and `execution_allowed: false`
- every engine has `execution_allowed: false` and `operator_gate_required: true`
- M52 does not implement routing decisions, routed queue metadata, local LLM execution, Codex execution, real agent execution, GitHub integration, or external workflows

Recommended next milestone:

- M53 - Queue Routing Metadata Contract.

## M51 Project AI Settings Contract Context

Status: Completed locally on `main`.

Current settings contract:

- operator functions: `read_project_ai_settings(...)`, `update_project_ai_settings(...)`, and `validate_project_ai_settings(...)` in `src/aresforge/operator/local_project_factory.py`
- file-backed artifact: `.aresforge/projects/{project_id}/ai_settings.json`
- Hub routes: `GET /api/projects/{project_id}/ai-settings` and `POST /api/projects/{project_id}/ai-settings`

Supported fields:

- `project_ai_mode`
- `available_engines`
- `disabled_engines`
- `default_engine`
- `default_model`
- `operator_override_allowed`
- `notes`
- `updated_at`

Supported values:

- project modes: `balanced`, `local_only`, `codex_only`, `cost_saver`, `high_confidence`, `manual_only`
- engines: `local_reasoning_llm`, `local_coding_llm`, `codex_cli`

Boundary reminders:

- settings are a validation contract only
- M51 does not implement routing decisions, routed queue metadata, local LLM execution, Codex execution, real agent execution, GitHub integration, or external workflows
- `cost_saver` and `high_confidence` express future preferences only
- `manual_only` may omit `default_engine`

Recommended next milestone:

- M52 - Agent and Engine Registry Contract.

## M50 Handoff Generator Context

Status: Completed locally on `main`.

Current handoff contract:

- operator function: `generate_local_project_handoff(...)` in `src/aresforge/operator/local_project_handoff.py`
- Hub route: `POST /api/local-project/handoff`
- Handoff UI includes a Local Project Handoff Generator form and copy/paste preview

Inputs:

- optional `project_id`
- `include_queue`, `include_reports`, and `include_evidence` booleans
- optional `next_milestone` and `next_instruction`
- optional local `output` path and `force`

Output:

- stable JSON with `ok`, `project_id`, `project_name`, `generated_at`, `handoff_markdown`, `summary`, optional `output_path`, `next_safe_action`, `warnings`, and `blockers`
- markdown includes operating rules, architecture boundaries, Hub capabilities, queue/report/progress state, open work, blockers/warnings, evidence/closeout state, next milestone/instruction, and startup validation commands

Boundary reminders:

- local-only, file-backed, and operator-gated
- read-only unless explicitly writing an optional local artifact
- no GitHub API/`gh`, issue/PR/workflow activity, GitHub mutation, agent execution, Codex execution, local LLM execution, model routing, or external execution
- handoff generation builds on Reports v1 and M48 progress rollup state

Recommended next milestone:

- M51 - Project AI Settings Contract.

## M49 Reports v1 Context

Status: Completed locally on `main`.

Current Reports v1 contract:

- operator function: `read_local_project_reports(...)` in `src/aresforge/operator/local_project_report.py`
- Hub route: `GET /api/reports/local-projects`
- Reports UI includes a read-only Reports v1 panel

Reports v1 sections:

- overall project count and project status counts
- active project summary
- queue totals and counts by status, type, and assigned lane/agent
- blocked, ready, in-progress, evidence captured, closeout eligible, and closed/completed work
- latest activity summary
- M48 active project progress rollup integration
- local-only operating boundary summary, limitations, blockers, warnings, and `next_safe_action`

Boundary reminders:

- Reports v1 is local-only, file-backed, and read-only
- it does not mutate queue/project state or implement PDF/CSV/export workflows
- no Codex, local LLM, real agent, GitHub, `gh`, workflow, push, external execution, prompt execution, or routing execution
- routing implementation remains future work after workflow/reporting milestones

Recommended next milestone:

- M50 - Handoff Generator.

## M48 Project Progress Rollup Context

Status: Completed locally on `main`.

Current progress rollup contract:

- operator function: `read_local_project_progress_rollup(...)` in `src/aresforge/operator/local_project_queue.py`
- Hub route: `GET /api/projects/{project_id}/progress-rollup`
- Projects UI includes a small read-only Project Progress Rollup panel

Rollup content:

- project id/name and active-project flag
- total queue items
- counts by status, type, and assigned lane/agent
- ready, blocked, and in-progress item counts/lists
- evidence captured count/list
- closeout-eligible count/list
- closed/completed count/list
- latest activity timestamp, blockers, warnings, and `next_safe_action`

Boundary reminders:

- rollup is read-only and local-only
- no queue mutation, report generation, prompt generation/execution, Codex/local LLM/agent execution, model routing, GitHub/`gh`, push, workflow, or external execution
- routing metadata remains future/not implemented placeholder information only
- Reports v1 is not implemented by M48

Recommended next milestone:

- M49 - Reports v1.

## M47 Queue Item Closeout Workflow Context

Status: Completed locally on `main`.

Current closeout contract:

- operator function: `close_local_queue_item(...)` in `src/aresforge/operator/local_project_queue.py`
- Hub route: `POST /api/local-queue/items/{item_id}/closeout`
- Queue UI includes a minimal Close Out Queue Item form in the local lifecycle area

Closeout requirements:

- queue item must exist
- queue item must be `in_progress`
- completion evidence must exist
- completion evidence must include `evidence_summary`, `validation_results`, and `diff_check_result`
- operator must provide a closeout summary
- closeout must be explicitly requested by the operator

Closeout result:

- status transitions to existing `done` convention
- records `closed_at`, `closed_by`, `closeout_summary`, and `closeout_history`
- preserves `completion_evidence`
- returns stable local JSON with `next_safe_action`

Boundary reminders:

- local-only, file-backed, operator-gated
- no prompt generation or execution
- no Codex, local LLM, real agent, GitHub, `gh`, workflow, push, or external execution
- Agent/LLM routing remains future work

Recommended next milestone:

- M48 - Project Progress Rollup.

## M46 Completion Evidence Capture Context

Status: Completed locally on `main`.

Current evidence capture contract:

- operator function: `capture_local_queue_completion_evidence(...)` in `src/aresforge/operator/local_project_queue.py`
- Hub route: `POST /api/local-queue/items/{item_id}/evidence`
- Queue UI includes a minimal Capture Completion Evidence form in the local lifecycle area
- captured evidence is stored on the queue item as `completion_evidence`

Evidence fields:

- `evidence_summary`
- `validation_commands`
- `validation_results`
- `smoke_checks`
- `diff_check_result`
- `files_changed`
- `commit_hash`
- `push_result`
- `operator_notes`
- `captured_at`

Boundary reminders:

- evidence capture is local-only, file-backed, and operator-gated
- evidence capture does not complete or close out a queue item
- `closeout_eligible` is advisory only
- Agent/LLM routing implementation remains future work
- no local LLM execution, Codex execution, real agent execution, automatic prompt execution, or GitHub mutation

Recommended next milestone:

- M47 - Queue Item Closeout Workflow.

## M45 Local Hub End-to-End Operator Workflow Context

Status: Completed locally on `main`.

Validated workflow:

1. Operator inspects dashboard/local project state.
2. Operator identifies active project context.
3. Operator creates a local queue item through Hub intake.
4. Operator views local queue item details.
5. Operator checks local readiness.
6. Operator generates a local-only prompt pack.
7. Operator inspects the local project report.
8. Operator inspects the local queue agent summary.

Validation guarantees:

- workflow remains local-only, file-backed, and operator-gated
- prompt-pack generation is advisory copy/paste output only
- prompt-pack generation does not automatically execute prompts
- prompt-pack generation does not auto-start or auto-complete queue items
- the canonical local queue remains the single queue storage model

Still not implemented:

- Agent/LLM routing implementation remains future work
- no local LLM execution, Codex execution, real agent execution, or automatic prompt execution
- no GitHub API, `gh`, GitHub issues/PRs/workflows, or GitHub mutation from the app

Recommended next milestone:

- M46 - completion evidence capture for local operator workflow closeout.

## M44A Agent LLM Routing Strategy Context

Status: Completed locally on `main`.

Canonical strategy document:

- `docs/architecture/AGENT_LLM_ROUTING_STRATEGY.md`

Future-state routing contract:

- AresForge must support project-specific AI routing settings.
- Future flow: Project -> Agent Lane -> Allowed Engines/Models -> Routing Decision Matrix -> Prompt Pack Output.
- Routing decisions should happen before prompt generation.
- The queue should remain one canonical local queue with future routing metadata and filtered routed views/lanes.
- M43 prompt packs currently generate local-only grouped prompts without LLM/model routing.

Future routing vocabulary:

- project AI modes: `balanced`, `local_only`, `codex_only`, `cost_saver`, `high_confidence`, `manual_only`
- engines: `local_reasoning_llm`, `local_coding_llm`, `codex_cli`
- agent lanes: Architect / Planner Agent, Coding Agent, Reviewer / Validator Agent, Documentation Agent, Test Agent, Local Operator Assistant, High-Value Codex Lane

Implementation boundaries:

- documentation-only milestone
- no runtime routing or route/UI/schema implementation yet
- no Codex execution, no agent execution, no local LLM execution, no model invocation
- no GitHub API, no `gh`, no GitHub issues/PRs/workflows, no GitHub mutation from the app

## M43 Agent Prompt Pack Generator

Status: Completed locally on `main`.

Current prompt-pack contract:

- operator function: `generate_local_queue_prompt_pack(...)` in `src/aresforge/operator/local_project_queue.py`
- Hub route: `POST /api/local-queue/prompt-pack`
- Queue UI provides operator-triggered generation, summary, and copy/paste preview/output path

Boundaries:

- local-only, file-backed, operator-gated
- prompt-pack generation is advisory-only; operator manually runs prompts
- no queue auto-start/auto-complete mutation from prompt-pack generation
- no Codex execution, no real agent execution, no LLM/model routing
- no GitHub API, no `gh`, no GitHub mutation, no external calls

## M42 Queue Item Detail Panel

Status: Completed locally on `main`.

Queue detail panel contract:

- queue detail uses existing read-only routes:
  - `GET /api/queue/{item_id}`
  - `GET /api/local-queue/items/{item_id}/readiness`
- no new mutation route introduced
- panel content is read-only/advisory and intended for inspection before lifecycle actions

Detail fields shown include:

- item id/title/status/type/priority
- project/repo association
- source/tags/created/updated
- description
- requested outcome, acceptance notes, and validation notes when present in notes metadata
- readiness summary/blockers/warnings when available

## M41 Active Project Task Intake v2

Status: Completed locally on `main`.

Current intake contract:

- local intake uses `POST /api/local-queue/items`
- required: `title`
- optional structured fields:
  - `description`
  - `item_type`
  - `priority`
  - `tags`
  - `source` (defaulted by UI to `active_project_workspace`)
  - `requested_outcome`
  - `acceptance_notes`
  - `validation_notes`

Persistence model:

- keeps queue schema backward compatible
- stores `source` directly on queue item
- stores requested outcome and notes as structured local text in queue item `notes`

Boundary reminders:

- local-only, file-backed, operator-gated
- queue item creation only
- no auto-start, no auto-prompt generation
- no GitHub/`gh`/GitHub mutation
- no agent/Codex/LLM execution

## M40 Dashboard Milestone Closeout And Docs Reconciliation

Status: Completed locally on `main`.

This closeout reconciles documentation for completed dashboard milestones M35-M39 without introducing runtime changes.

Dashboard contract and behavior baseline:

- backend/operator summary contract: `src/aresforge/operator/local_dashboard_summary.py`
- Hub route: `GET /api/dashboard/summary`
- Home cards/status panels: local read-only/advisory rendering from dashboard summary
- refresh model: manual refresh only
- UI states: explicit loading, empty, and error handling
- deep links: Home links into existing Workspace/Projects/Queue/Repos/Reports sections
- drilldowns: queue status drilldowns and advisory agent lane drilldowns

Frontend module baseline used by dashboard flows:

- `src/aresforge/hub/static/app.js`
- `src/aresforge/hub/static/js/sections/home.js`
- `src/aresforge/hub/static/js/sections/queue.js`
- `src/aresforge/hub/static/js/sections/projects.js`
- `src/aresforge/hub/static/js/sections/repos.js`
- `src/aresforge/hub/static/js/sections/reports.js`

Mandatory operating boundaries (reconfirmed):

- local-only, file-backed, operator-gated
- read-only/advisory dashboard posture
- no GitHub API, no `gh`, no GitHub issues/PRs/workflows mutation
- no real agent execution
- no Codex execution from the Hub app
- no local/cloud model routing or invocation

Validation baseline for this closeout:

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
## M36 Home Dashboard UI Context

Current Home dashboard now consumes:

- `GET /api/dashboard/summary`

Home panels now display read-only/advisory:

- project summary (total projects, active project, active status)
- queue summary (total items and status counts)
- agent lane summary (lane totals/details)
- repo summary (availability/status/warnings)
- blockers and warnings (with empty-state messaging)
- next safe action

Boundary reminders remain:

- local-only/read-only/advisory
- no GitHub or `gh` calls
- no agent/Codex/model execution
- no LLM/model routing

## M35 Hub Dashboard Contract Context

Current Hub dashboard contract now includes:

- `GET /api/dashboard/summary`
- local-only read-only dashboard summary payload (`dashboard_type=hub_home`)
- project summary, queue summary, agent lane summary, repo summary, blockers/warnings, next safe action, and source summary fields

Boundary reminders:

- no mutation
- no GitHub or `gh` calls
- no agent/Codex/model execution
- local/file-backed inspection only

UI note:

- Home dashboard cards/panels are deferred to M36.

## Local LLM Planning Context (Documentation-Only)

AresForge now has documented future local Ollama model planning.

Planned local aliases:

- `aresforge-coder-local`
- `aresforge-reasoner-local`

Planned coding-model purpose:

- code generation
- bug fixing
- tests
- code review
- patch planning

Planned reasoning-model purpose:

- architecture planning
- task decomposition
- documentation synthesis
- risk analysis
- validation planning
- prompt optimization

Safety boundary:

- model output must not be treated as trusted execution authority
- generated commands and file changes must remain operator-approved

## M34 Frontend Modularization Closeout Context

Use this as the current frontend contract baseline:

- `src/aresforge/hub/static/app.js` is the ES module entrypoint.
- `src/aresforge/hub/static/index.html` loads `app.js` with `type="module"`.
- core modules:
  - `src/aresforge/hub/static/js/core/dom.js`
  - `src/aresforge/hub/static/js/core/http.js`
  - `src/aresforge/hub/static/js/core/state.js`
- section modules:
  - `src/aresforge/hub/static/js/sections/home.js`
  - `src/aresforge/hub/static/js/sections/workspace.js`
  - `src/aresforge/hub/static/js/sections/queue.js`
  - `src/aresforge/hub/static/js/sections/projects.js`
  - `src/aresforge/hub/static/js/sections/repos.js`
  - `src/aresforge/hub/static/js/sections/reports.js`
  - `src/aresforge/hub/static/js/sections/orchestration.js`
  - `src/aresforge/hub/static/js/sections/escalation.js`
- project-factory modules:
  - `src/aresforge/hub/static/js/sections/projectFactory/index.js`
  - `src/aresforge/hub/static/js/sections/projectFactory/scope.js`
  - `src/aresforge/hub/static/js/sections/projectFactory/architecture.js`
  - `src/aresforge/hub/static/js/sections/projectFactory/milestonePlan.js`
  - `src/aresforge/hub/static/js/sections/projectFactory/validation.js`
  - `src/aresforge/hub/static/js/sections/projectFactory/agentDispatch.js`
  - `src/aresforge/hub/static/js/sections/projectFactory/executionApproval.js`
  - `src/aresforge/hub/static/js/sections/projectFactory/closeout.js`

Validation baseline for this contract:

- `tests/test_hub_ui_foundation.py`
- `tests/test_hub_project_factory_api.py`
- `tests/test_hub_local_queue_lifecycle_api.py`
- `tests/test_hub_active_project_api.py`
- `tests/test_local_project_factory.py`
- `tests/test_local_active_project.py`
- smoke:
  - `python -m aresforge inspect-local-queue-agent-summary`
  - `python -m aresforge inspect-local-project-report`

Boundary context remains mandatory:

- local-first
- file-backed
- operator-gated
- no real agent execution
- no GitHub mutation
- no network execution beyond existing local Hub API behavior

Next recommended milestone:

- M35 - Hub Dashboard Data Contract And Read-Only Metrics

## M28 Hub Orchestration And Escalation Section Modules

Latest Hub frontend context now includes dedicated section modules for Orchestration and Escalation:

- `src/aresforge/hub/static/app.js` remains the only frontend entrypoint
- Orchestration render/load/binding logic now lives in `src/aresforge/hub/static/js/sections/orchestration.js`
- Escalation render/load/binding logic now lives in `src/aresforge/hub/static/js/sections/escalation.js`
- project-factory lifecycle, queue lifecycle, and execution-approval orchestration remain in `src/aresforge/hub/static/app.js`

Guidance for follow-on frontend work:

- keep `app.js` focused on cross-section orchestration and higher-coupling flows
- continue extracting only clearly section-owned behavior
- preserve DOM ids and API endpoint paths
- keep validating the combined frontend script surface, not only `app.js`

## M17 Local Queue Execution-Prep Lifecycle

Latest local queue progression now supports a full operator-driven execution-prep loop:

- add a local queue item
- inspect readiness
- start the item locally
- generate a local Codex prompt artifact or stdout prompt
- have a human run Codex manually
- complete the item with local validation evidence and commit metadata

New local queue command surface to know:

- `python -m aresforge add-local-queue-item --title <title> ...`
- `python -m aresforge inspect-local-queue-item-readiness --item-id <item_id>`
- `python -m aresforge start-local-queue-item --item-id <item_id>`
- `python -m aresforge generate-local-queue-item-codex-prompt --item-id <item_id> [--output <path>]`
- `python -m aresforge complete-local-queue-item --item-id <item_id> --commit-hash <hash> --validation-summary <text> ...`

Required operating boundaries remain unchanged:

- local-first and local-only
- no GitHub API calls or `gh` calls
- no GitHub sync/mutation execution
- no automatic Codex execution
- no agent execution
- no local/cloud/Codex/ChatGPT/Ollama model routing or invocation
- completion records evidence locally only and does not verify commits remotely

## M27 Hub Reports Section Module

Latest Hub frontend context now includes a Reports section module for the Reports UI slice:

- `src/aresforge/hub/static/app.js` remains the only frontend entrypoint
- Reports dashboard rendering, local project report rendering, report slice loading, export helpers, and Reports-specific bindings now live in `src/aresforge/hub/static/js/sections/reports.js`
- non-Reports orchestration and other higher-coupling flows still remain in `src/aresforge/hub/static/app.js`

Guidance for follow-on frontend work:

- keep `app.js` focused on orchestration and higher-coupling flows
- continue extracting only clearly section-owned behavior when cross-section dependencies stay manageable
- preserve DOM ids and API endpoint paths
- keep validating the combined frontend script surface, not only `app.js`

## M26 Hub Projects And Repos Section Modules

Latest Hub frontend context now includes Projects and Repos section modules for the next UI slices:

- `src/aresforge/hub/static/app.js` remains the only frontend entrypoint
- Projects list rendering, read-only rendering, selector refresh, and Projects-specific bindings now live in `src/aresforge/hub/static/js/sections/projects.js`
- Repos list rendering, repo loading/inspection, and Repos-specific bindings now live in `src/aresforge/hub/static/js/sections/repos.js`
- project-factory and other higher-coupling orchestration still remains in `src/aresforge/hub/static/app.js`

Guidance for follow-on frontend work:

- keep `app.js` focused on orchestration and higher-coupling flows
- continue extracting only clearly section-owned behavior when cross-section dependencies stay manageable
- preserve DOM ids and API endpoint paths
- keep validating the combined frontend script surface, not only `app.js`

## M25 Hub Queue Section Module

Latest Hub frontend context now includes a Queue section module for the queue UI slice:

- `src/aresforge/hub/static/app.js` remains the only frontend entrypoint
- queue read-only summary rendering/loading and queue item card rendering now live in `src/aresforge/hub/static/js/sections/queue.js`
- queue-only bindings now live in `src/aresforge/hub/static/js/sections/queue.js`
- local queue lifecycle internals remain in `src/aresforge/hub/static/app.js` for now because they are more tightly coupled to intake/start/readiness/prompt/complete flows

Guidance for follow-on frontend work:

- keep `app.js` focused on orchestration and higher-coupling flows
- continue extracting only clearly section-owned queue behavior until lifecycle internals are safer to split
- preserve DOM ids and API endpoint paths
- keep validating the combined frontend script surface, not only `app.js`

## M24 Hub Home And Workspace Section Modules

Latest Hub frontend context now includes section-level modules for the lowest-risk UI slices:

- `src/aresforge/hub/static/app.js` remains the only frontend entrypoint
- Home dashboard rendering/loading and Home-specific button wiring now live in `src/aresforge/hub/static/js/sections/home.js`
- Active Project Workspace rendering/loading, empty-state handling, and quick-action wiring now live in `src/aresforge/hub/static/js/sections/workspace.js`
- workspace quick-action binding still follows a single binding path

Guidance for follow-on frontend work:

- keep `app.js` focused on orchestration and shared cross-section flows
- keep Home/Workspace helpers in their section modules unless they become clearly shared
- preserve DOM ids and API endpoint paths
- continue validating the combined frontend script surface, not only `app.js`

## M23 Hub Frontend Modularization Foundation

Latest Hub frontend context now includes a browser-native ES module foundation:

- `src/aresforge/hub/static/app.js` remains the main entrypoint
- shared DOM helpers live in `src/aresforge/hub/static/js/core/dom.js`
- shared HTTP/payload helpers live in `src/aresforge/hub/static/js/core/http.js`
- the shared frontend state container lives in `src/aresforge/hub/static/js/core/state.js`
- duplicate workspace button binding was consolidated into one binding path

Guidance for follow-on frontend work:

- preserve `app.js` as the entrypoint unless a later milestone explicitly changes that contract
- keep DOM ids and API endpoint paths stable
- prefer moving only generic helpers into `js/core/*` until section/domain modules are ready
- update static tests to validate the combined frontend script surface, not a single monolith file

## M21 Active Project Workspace (UI & Operator Flow)

Added and validated locally:

- Active Project Workspace UI polish with clearer operator guidance and empty-state messaging.
- Workspace quick-actions annotated with "(local-only)" and explicit operator next-steps.
- Frontend action wiring to support refreshing the workspace, continuing task intake, opening the queue, and selecting projects.
- New focused regression tests (`tests/test_active_project_workspace.py`) that assert the active-workspace API payload shape for empty and seeded states.

Operating constraints (unchanged):

- local-first and file-backed control-plane only
- no GitHub API calls, no `gh` calls
- no agent execution, no Codex or LLM invocation
- no network or remote mutation


## M16 Hub Local-Only Read/Report Foundations

Latest local milestone progression adds read-only Hub foundations for:

- Home dashboard API wiring and UI
- Projects page UI
- Queue page UI
- Reports page UI

Required operating boundaries remain unchanged:

- local-first and local-only
- no GitHub API calls or `gh` calls
- no GitHub sync/mutation execution
- no agent execution
- no local/cloud/Codex/ChatGPT/Ollama model routing or invocation

Validation closeout for this layer includes targeted suites, full `pytest`, and local smoke commands. Push has not been performed.

## M14 Local Foundation Context

- Current source-of-truth stance:
  - local-first operation
  - direct-on-`main` workflow
  - read-only local reporting/inspection expansion
- Explicit restrictions for this layer:
  - no GitHub API calls
  - no `gh` calls
  - no GitHub issue/PR mutation for local read-model/report commands
  - no real agent execution
  - no LLM routing/invocation
- Historical status:
  - M9-M13 were completed, validated, committed, and pushed before this chat.
  - M14 local read-model/report commands were added in this chat and validated on local `main`.

New local read-only command surface to know:

- `python -m aresforge inspect-local-project-dashboard`
- `python -m aresforge list-local-projects`
- `python -m aresforge inspect-local-project-readiness --project-id <id>`
- `python -m aresforge inspect-local-queue-agent-summary`
- `python -m aresforge inspect-local-project-report`

## M46 Project Factory Alignment Context

Project-factory vision:

- AresForge is a local-first AI project factory and orchestration hub.
- Future implementation must converge on the canonical end-to-end pipeline defined in `docs/architecture/PROJECT_FACTORY_WORKFLOW.md`.

Implementation guardrails for future agents:

- no GitHub mutations without an explicit approved GitHub apply boundary
- no model/agent execution without explicit approval boundary
- local planning and local artifact generation first

Current foundation status:

- M43 active project support is the active context layer.
- M44 active project intake is the first user-to-queue bridge.
- M45 active project workbench is the mission-control foundation.
- This foundation is not yet the complete project-factory loop.

## Purpose

Provide minimum operating context for M42 first-run bootstrap/setup with a local-first, self-managed operator model.

## Current Operating Model

- Active milestone context: M42 first-run bootstrap and seed wizard in local registry and Hub.
- AresForge now has a local-first foundation for self-managed operation.
- GitHub is optional/syncable and not mandatory for local planning.
- M26 added local handoff package generation.
- M27 added the local project state ledger.
- M28 added plan-only documentation reconciliation.
- M29 added plan-only offline-to-GitHub sync planning.
- M30 added local self-managed milestone lifecycle support.
- M32 added local managed-project/multi-repo registry support.
- M33 added local project queue/work tracking support.
- M34 added local agent profiles and handoff target descriptors.
- M35 added local multi-agent orchestration planning (assignment + sequencing + handoff prompts).
- M36 added local escalation planning that classifies queue/orchestration work for local LLM, Codex, cloud advisory, human-required, and blocked/clarification paths.
- M37 added a local Hub server/API/frontend foundation intended to become the primary local entry point for AresForge.
- M38 added interactive local Hub screens and API workflows for M32 managed-project registry and M33 local queue management.
- M39 adds interactive local Hub screens and API workflows for M34 local agent profiles/handoff targets, M26 handoff preview, M35 orchestration planning, and M36 escalation planning.
- M40 adds unified local control-plane reporting, readiness indicators, action-center guidance, and operator workflow cards in Hub Home/Reports/Settings.
- M41 adds explicit local GitHub identity for managed projects/repos, primary repo linkage, local git-link inspection, and Hub GitHub linkage readiness/reporting surfaces.
- M42 adds first-run bootstrap status/plan/apply support for local file initialization and default seed data.
- Foundation-batch boundaries (M26-M30):
  - no `gh`
  - no GitHub API calls
  - no LLM API calls
  - no network-required execution path
- Current local-first command surface:
  - `python -m aresforge generate-handoff-package --output <path> [--format markdown|json] [--include-doc-excerpts] [--force]`
  - `python -m aresforge init-project-state [--path <path>] [--force]`
  - `python -m aresforge inspect-project-state [--path <path>]`
  - `python -m aresforge update-project-state [--path <path>] [--current-milestone <value>] [--current-phase <value>] [--current-mode <value>] [--validation-status <value>] [--documentation-status <value>] [--warning <text>]...`
  - `python -m aresforge append-operation-log [--state-path <path>] --event-type <type> --summary <summary> [--details <json>]`
  - `python -m aresforge inspect-operation-log [--state-path <path>] [--limit <n>]`
  - `python -m aresforge plan-doc-reconciliation [--output <path>] [--format json|markdown] [--include-git-state] [--force]`
  - `python -m aresforge plan-github-sync [--state-file <path>] [--project-state <path>] [--output <path>] [--format json|markdown] [--force]`
  - `python -m aresforge generate-local-milestone-template --milestone-id <id> --output <path> [--title <title>] [--force]`
  - `python -m aresforge inspect-local-milestone --definition <path> [--format json|markdown]`
  - `python -m aresforge check-local-milestone-readiness --definition <path> [--project-state <path>] [--format json|markdown]`
  - `python -m aresforge generate-local-milestone-closeout --definition <path> --output <path> [--format json|markdown] [--force]`
  - `python -m aresforge init-managed-project-registry [--path <path>] [--force]`
  - `python -m aresforge register-managed-project --project-id <id> --name <name> --root-path <path> [--registry-path <path>] [--description <text>] [--status <status>] [--default-branch <branch>] [--tag <tag>]... [--notes <text>]`
  - `python -m aresforge register-managed-project --project-id <id> --name <name> --root-path <path> [--registry-path <path>] [--description <text>] [--status <status>] [--default-branch <branch>] [--github-url <url>] [--github-owner <owner>] [--github-repo <repo>] [--github-default-branch <branch>] [--primary-repo-id <repo_id>] [--tag <tag>]... [--notes <text>]`
  - `python -m aresforge register-managed-repo --project-id <id> --repo-id <id> --name <name> --path <path> [--registry-path <path>] [--remote-url <url>] [--default-branch <branch>] [--github-url <url>] [--github-owner <owner>] [--github-repo <repo>] [--github-default-branch <branch>] [--inspect-local-git] [--role <role>] [--status <status>] [--tag <tag>]... [--notes <text>]`
  - `python -m aresforge inspect-managed-project-registry [--registry-path <path>] [--format json|markdown]`
  - `python -m aresforge inspect-managed-project --project-id <id> [--registry-path <path>] [--format json|markdown]`
  - `python -m aresforge inspect-managed-repo --project-id <id> --repo-id <id> [--registry-path <path>] [--format json|markdown]`
  - `python -m aresforge inspect-managed-repo-github-link --project-id <id> --repo-id <id> [--registry-path <path>] [--inspect-local-git] [--format json|markdown]`
  - `python -m aresforge inspect-bootstrap-status [--repo-path <path>]`
  - `python -m aresforge plan-bootstrap [--repo-path <path>] [--format json|markdown] [--seed-sample-work]`
  - `python -m aresforge apply-bootstrap [--repo-path <path>] [--force] [--seed-sample-work] [--format json|markdown]`
  - `python -m aresforge init-project-queue [--path <path>] [--force]`
  - `python -m aresforge add-queue-item --item-id <id> --project-id <id> --repo-id <id> --title <title> [--queue-path <path>] [--registry-path <path>] [--description <text>] [--status <status>] [--priority <priority>] [--type <type>] [--tag <tag>]... [--depends-on <item_id>]... [--blocked-by <item_id>]... [--assigned-agent <agent_id>] [--source <source>] [--notes <text>]`
  - `python -m aresforge update-queue-item --item-id <id> [--queue-path <path>] [--project-id <id>] [--repo-id <id>] [--status <status>] [--priority <priority>] [--type <type>] [--title <title>] [--description <text>] [--tag <tag>]... [--depends-on <item_id>]... [--blocked-by <item_id>]... [--assigned-agent <agent_id>] [--source <source>] [--notes <text>]`
  - `python -m aresforge inspect-project-queue [--queue-path <path>] [--project-id <id>] [--repo-id <id>] [--status <status>] [--type <type>] [--assigned-agent <agent_id>] [--format json|markdown]`
  - `python -m aresforge inspect-queue-item --item-id <id> [--queue-path <path>] [--format json|markdown]`
  - `python -m aresforge init-agent-profiles [--path <path>] [--force] [--with-defaults]`
  - `python -m aresforge register-agent-profile --agent-id <id> --name <name> --role <role> [--profiles-path <path>] [--description <text>] [--execution-mode <mode>] [--model-preference <value>] [--strength <text>]... [--constraint <text>]... [--allowed-type <type>]... [--escalation-allowed true|false] [--handoff-target-id <id>] [--status <status>] [--tag <tag>]... [--notes <text>]`
  - `python -m aresforge register-handoff-target --target-id <id> --name <name> --target-type <type> [--profiles-path <path>] [--description <text>] [--local-command <command>] [--input-format <format>] [--output-format <format>] [--safety-note <text>]... [--status <status>] [--tag <tag>]... [--notes <text>]`
  - `python -m aresforge inspect-agent-profiles [--profiles-path <path>] [--role <role>] [--execution-mode <mode>] [--status <status>] [--format json|markdown]`
  - `python -m aresforge inspect-agent-profile --agent-id <id> [--profiles-path <path>] [--format json|markdown]`
  - `python -m aresforge inspect-handoff-target --target-id <id> [--profiles-path <path>] [--format json|markdown]`
  - `python -m aresforge plan-agent-orchestration [--project-id <id>] [--repo-id <id>] [--status <status>] [--queue-path <path>] [--profiles-path <path>] [--registry-path <path>] [--output <path>] [--format json|markdown] [--force]`
  - `python -m aresforge plan-llm-escalation [--item-id <id>] [--project-id <id>] [--repo-id <id>] [--status <status>] [--queue-path <path>] [--profiles-path <path>] [--orchestration-plan <path>] [--output <path>] [--format json|markdown] [--force]`
  - `python -m aresforge serve-hub [--host <host>] [--port <port>] [--open-browser]`
- M33 boundary confirmations:
  - queue is local-only and can track work without GitHub issues
  - no `gh`
  - no GitHub API calls
  - no network access
  - no LLM calls
  - `assigned_agent` is data-only for future orchestration and does not execute agents
  - M32 registry validation is local-only when registry exists or `--registry-path` is supplied
- M34 boundary confirmations:
  - local-only configuration for agent and handoff metadata
  - handoff targets are descriptive/advisory only
  - no agent execution path is introduced yet
  - no local LLM invocation is introduced yet
  - no cloud LLM invocation is introduced yet
  - no `gh`, no GitHub API calls, no network access
  - M33 `assigned_agent` can reference M34 `agent_id`
- M35 boundary confirmations:
  - local-only orchestration planning
  - plan-only output (assignment and sequencing guidance only)
  - no agent execution
  - no local LLM invocation
  - no cloud LLM invocation
  - no `gh`, no GitHub API calls, no network access
  - reads M32 registry, M33 queue, and M34 profiles where available
- M36 boundary confirmations:
  - local-only escalation planning
  - plan-only classification output only (no execution)
  - cloud escalation is advisory only
  - no LLM invocation
  - no local LLM calls
  - no cloud LLM calls
  - no Codex execution
  - no ChatGPT calls
  - no `gh`, no GitHub API calls, no network access
  - reads M33 queue and M34 profiles where available and optional M35 orchestration artifact input when supplied
- M37 boundary confirmations:
  - local-first local UI serving path
  - binds to `127.0.0.1` by default
  - no `gh`, no GitHub API calls, no network service calls
  - no local LLM calls, no cloud LLM calls
  - no Codex calls, no ChatGPT calls, no Ollama calls
  - no external API calls
  - no agent execution
  - no live GitHub sync
  - no authentication implementation yet
  - no production deployment implementation yet
- M38 boundary confirmations:
  - local-first, file-backed project/repo/queue management via Hub API and static UI
  - no `gh`, no GitHub API calls, no network services
  - no local LLM calls, no cloud LLM calls, no Codex/ChatGPT/Ollama calls
  - no external API calls
  - no agent execution, no live GitHub sync
  - M40 reporting/dashboard/operator workflow surfaces are implemented as local-only report/plan-only flows
  - authentication and production deployment remain unimplemented
- M39 boundary confirmations:
- M40 boundary confirmations:
  - local-first, file-backed reporting and workflow guidance
  - report-only and plan-only control-plane surfaces
  - no agent execution
  - no local/cloud/Codex/ChatGPT/Ollama model invocation
  - no GitHub calls, no `gh` calls, no network/external API calls
  - no live GitHub sync execution
  - authentication and production deployment remain unimplemented
  - future work includes guided workflow depth, optional execution gates, auth hardening when exposed beyond localhost, controlled sync execution, and optional LLM execution behind explicit user approval gates
- M41 boundary confirmations:
  - GitHub links are local metadata only
  - local git inspection is local-only and non-networked
  - no GitHub API calls
  - no `gh` calls
  - no GraphQL/REST calls
  - no network service calls
  - no live GitHub validation
- M42 boundary confirmations:
  - bootstrap is local-only and file-backed
  - no GitHub API calls
  - no `gh` calls
  - no GraphQL/REST calls
  - no network service calls
  - no local/cloud/Codex/ChatGPT/Ollama calls
  - no live GitHub discovery/validation
- M39 boundary confirmations:
  - local-first, file-backed agent/handoff/orchestration/escalation management via Hub API and static UI
  - no `gh`, no GitHub API calls, no network services
  - no local LLM calls, no cloud LLM calls, no Codex/ChatGPT/Ollama calls
  - no external API calls
  - orchestration and escalation remain plan-only
  - no agent execution and no model invocation
  - handoff preview is local-only and does not post anywhere
  - M40 reporting/dashboard/operator workflow surfaces are implemented as local-only report/plan-only flows
  - authentication and production deployment remain unimplemented
- Next-phase planning focus:
  - richer guided Hub workflows and cross-section automation
  - optional execution gates with explicit user approval
  - authentication hardening if exposed beyond localhost
  - controlled GitHub sync execution behind explicit safety gates
  - optional LLM execution behind explicit user-approved gates

## Canonical Documents

- `docs/context/BUILD_STATE.md`
- `docs/context/AGENT_CONTEXT.md`
- `docs/roadmap/ROADMAP.md`
- `docs/operator/LOCAL_OPERATOR_USAGE.md`
- `docs/architecture/AUTOMATIC_CANONICAL_EVIDENCE_EMISSION_CONTRACT.md`
- `docs/architecture/MILESTONE_CLOSEOUT_PREFLIGHT_CONTRACT.md`
- `docs/architecture/RUNNABLE_SKELETON.md`

## Current M25 Commands

- `python -m aresforge inspect-automatic-canonical-evidence-emission-contract`
- `python -m aresforge generate-child-closeout-evidence-bundle --parent-issue <parent> --child-issue <child>`
- `python -m aresforge generate-pr-evidence-bundle --issue <child> --pr <pr>`
- `python -m aresforge generate-parent-closeout-evidence-bundle --parent-issue <parent>`
- `python -m aresforge generate-evidence-comment-template --issue <issue>`
- `python -m aresforge check-closeout-readiness-by-construction --parent-issue <parent>`

## M26 Continuity Command

- `python -m aresforge generate-handoff-package --output <path> [--format markdown|json] [--include-doc-excerpts] [--force]`
- If `--output` is omitted:
  - markdown is printed to stdout by default
  - JSON is printed to stdout when `--format json`

## Offline State-File Commands

- `python -m aresforge inspect-milestone-state --parent-issue <n> --state-file <path>`
- `python -m aresforge check-milestone-evidence-readiness --parent-issue <n> --state-file <path>`
- `python -m aresforge inspect-parent-closeout-readiness --parent-issue <n> --state-file <path>`
- `python -m aresforge generate-parent-closeout-evidence-bundle --parent-issue <n> --state-file <path>`
- `python -m aresforge check-closeout-readiness-by-construction --parent-issue <n> --state-file <path>`
- Example fixture: `tests/fixtures/offline_state/parent_closeout_ready.json`.
- Validation checkpoint: `python -m pytest` passed with `502` tests.

## M25 Child/PR Mapping

- `#431` -> child `#422`
- `#432` -> child `#423`
- `#433` -> child `#424`
- `#434` -> child `#425`
- `#435` -> child `#426`
- `#436` -> child `#427`
- `#437` -> child `#428`
- `#438` -> child `#429`
- `pending` -> child `#430` (this reconciliation PR)

## Prohibited Behaviors

- autonomous broad mutation
- bulk issue closure
- parent closeout before all children are closed/accounted for
- prior milestone mutation unless explicitly required
- nested markdown fences inside PowerShell here-string issue/comment bodies

## Validation Snapshot

- `git diff --check`
- `python -m pytest`
- `python -m aresforge inspect-repo-governance`
- `python -m aresforge inspect-milestone-state --parent-issue 421`
- `python -m aresforge check-milestone-evidence-readiness --parent-issue 421`
- `python -m aresforge inspect-parent-closeout-readiness --parent-issue 421`
- `python -m aresforge inspect-milestone-closeout-preflight --parent-issue 421`
- `python -m aresforge inspect-automatic-canonical-evidence-emission-contract`
- `python -m aresforge check-closeout-readiness-by-construction --parent-issue 421`

## Known Limitations

- No production-ready LLM dispatch exists; only the M62 explicit local LLM prototype may call a local provider under operator gates.
- No cloud LLM API integration yet.
- No GitHub sync execution yet.
- Hub now provides M40 local management/planning/reporting workflows; execution gates/auth/deployment hardening remain future work.
- No cross-machine coordination yet.
- No background daemon/scheduler yet.
