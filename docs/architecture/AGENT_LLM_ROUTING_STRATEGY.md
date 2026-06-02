# Agent LLM Routing Strategy

## M174 GitHub Issue State Reconciliation Routing Boundary

M174 adds no live agent, local LLM, or Codex route. It adds a recommendation-only GitHub issue-state reconciliation route that remains dry-run by default and may read mocked GitHub issue state from a local file or live issue state only after explicit GitHub enablement, autonomy profile allowance, and machine gates pass.

Routing rules:

- dry-run routes to local queue, issue plan, registry, autonomy, and gate inspection, plus optional mocked state-file loading
- missing GitHub state routes linked issue items to `skip` recommendations unless local queue/registry state supports a safe `create` recommendation for unlinked items
- open issues for done queue items route to advisory `close`
- closed issues for active queue items route to advisory `reopen`
- title/label drift routes to advisory `update`
- validation/evidence comments route to advisory `comment`

M174 reports no agent execution, no model execution, no Codex execution, no source patch application, no validation command execution, and no queue status mutation. GitHub execution can be true only for an explicitly enabled read-only live issue-state lookup; mutation remains false.

## M173 GitHub Status Comment Durable Sync Routing Boundary

M173 adds no live agent, local LLM, or Codex route. It adds a durable GitHub status comment sync route that remains dry-run by default and becomes live only after explicit GitHub enablement, autonomy profile allowance, linked issue checks, safe queue status, and machine gates pass.

Routing rules:

- dry-run routes to local queue, issue plan, registry, run monitor, autonomy, and gate inspection only
- missing queue items, unsafe queue status, blocked dependencies, missing issue metadata in live mode, wrong autonomy profile, or failed gates route to `blocked`
- existing registry `comment_id` routes live execution to update that managed comment
- missing registry `comment_id` routes live execution to marker lookup, then update or create exactly one managed comment
- successful mocked/live sync routes to local GitHub link registry recording of `comment_id` only, not queue completion

M173 reports no agent execution, no model execution, no Codex execution, no source patch application, no validation command execution, and no queue status mutation. Live GitHub execution can be true only on the explicitly enabled single-comment create/update path.

## M172 Queue-to-GitHub Issue Backfill Routing Boundary

M172 adds no live agent, local LLM, or Codex route. It adds a queue-to-GitHub issue backfill route that remains dry-run by default and becomes live only after explicit GitHub enablement, autonomy profile allowance, local duplicate-link checks, candidate safety checks, and machine gates pass.

Routing rules:

- dry-run routes to local queue scanning, issue payload planning, registry lookup, and machine-gate inspection only
- linked queue metadata or existing registry issue links route to `already_linked`
- blocked queue items or non-create recommendations route to `blocked` or `skipped`
- wrong autonomy profile or failed `github_sync` gate routes live execution to `blocked`
- successful mocked/live issue creation routes to local GitHub link registry recording only, not queue completion

M172 reports no agent execution, no model execution, no Codex execution, no source patch application, no validation command execution, and no queue status mutation. Live GitHub execution can be true only on the explicitly enabled gated create path.

## M171 GitHub Issue Creation Real-Run Gate Routing Boundary

M171 adds no live agent, local LLM, or Codex route. It adds a narrow GitHub issue creation route that remains dry-run by default and becomes live only after explicit GitHub enablement, autonomy profile allowance, local duplicate-link checks, safe queue status, and machine gates pass.

Routing rules:

- dry-run routes to local queue, issue plan, registry, autonomy, and gate inspection only
- blocked queue status, linked queue metadata, or existing registry issue links route to `blocked`
- wrong autonomy profile or failed `github_sync` gate routes to `blocked`
- successful mocked/live issue creation routes to local GitHub link registry recording only, not queue completion

M171 reports no agent execution, no model execution, no Codex execution, no source patch application, no validation command execution, and no queue mutation. Live GitHub execution can be true only on the explicitly enabled single-issue create path.

## M170 GitHub Link Registry Routing Boundary

M170 adds no live agent, local LLM, Codex, or live GitHub route. It routes queue-item GitHub issue/PR linkage into a durable local registry for operator review and later gated sync coordination.

Routing rules:

- registry inspection routes to local read-only metadata lookup
- `record-github-link` routes to local file-backed registry add/update only
- queue item, issue number, PR number, and repository filters route to local lookup results
- repeated writes with the same material link data route to `idempotent_noop`
- registry records route to future review evidence only, not automatic GitHub mutation

M170 reports no agent execution, no model execution, no Codex execution, no GitHub execution, no source patch application, no validation command execution, and no queue mutation.

## M169 Production Autonomy Readiness Report Routing Boundary

M169 adds no live agent, local LLM, Codex, or GitHub route. It routes M155, M156, M157, M158, M159, M160, M161, M162, M163, M164, M165, M166, M167, M168, and M169 local evidence into a production autonomy readiness report for operator review.

Routing rules:

- report generation routes through read-only and autonomy-profile machine gates
- durable run-store, artifact retention, autonomy profile, GitHub issue sync plan, Hub control center, and self-managed dry-run evidence remain local inspection inputs
- readiness output routes to next-sprint planning only, not automatic execution

M169 reports no live agent execution, no model execution, no live Codex execution, no GitHub execution, no source patch application, no validation command execution, and no queue mutation.

## M168 Self-Managed AresForge Project Loop Dry Run Routing Boundary

M168 adds no live agent, local LLM, Codex, or GitHub route. It adds a local dry-run route that selects an AresForge queue item and composes route decision metadata, orchestration planning, deterministic dry-run agent output, Codex loop dry-run evidence, GitHub issue sync planning, PR draft summary generation, run-store evidence, and closeout recommendation.

Routing rules:

- `--dry-run` is required; non-dry-run input routes to `blocked`
- queue selection routes to the requested item, then the M168 item, then the first eligible local AresForge queue item
- route decisions remain advisory and set `recommended_execution_target=dry-run`
- GitHub issue sync, PR summary, and closeout outputs remain review evidence only

M168 reports no live agent execution, no model execution, no live Codex execution, no GitHub execution, no source patch application, no validation command execution, and no queue mutation.

## M167 Hub Autonomy Control Center Routing Boundary

M167 adds no new agent, local LLM, Codex, or live GitHub route. It adds a local Hub/CLI aggregation route that reads autonomy profile, durable run-store, orchestration monitor, local evidence, GitHub issue sync plan, issue closure recommendation, and PR draft summary artifact state.

The control center reports dry-run and future-gated next actions only. It does not dispatch agents, call local/cloud models, invoke Codex, call GitHub or `gh`, create/update/merge PRs, close issues, mutate queue state, apply patches, retry, resume, or start follow-on work.

## M166 Pull Request Draft Summary Generator Routing Boundary

M166 does not add a new agent, local LLM, Codex, or live GitHub route. It adds a local PR summary artifact route for one queue item based on queue context, Codex evidence bundle metadata when present, changed files, validation output, artifact paths, linked issue references, risks, rollback notes, and machine gates.

Routing rules:

- complete local evidence routes to `draft_summary_created`
- missing queue items, missing validation evidence, missing artifact references, blocked evidence bundles, or gate failures route to `blocked`
- generated Markdown and JSON artifacts route to operator review only
- PR creation remains unauthorized and must wait for a separate future machine-gated route

M166 reports no agent execution, no model execution, no Codex execution, no GitHub execution, no source patch application, and no queue mutation.

## M165 GitHub Issue Closure Recommendation Gate Routing Boundary

M165 does not add a new agent, local LLM, Codex, or live GitHub route. It adds a local recommendation route for one linked issue based on queue completion, validation evidence, artifact evidence, linked issue metadata/state, autonomy profile inspection, and machine gates.

Routing rules:

- done queue items with complete evidence and linked open/unknown issue metadata route to `close` recommendation
- missing evidence, incomplete queue status, unsatisfied dependencies, blockers, absent linked issue metadata, already closed issues, or gate failures route to `keep_open`
- `close` remains advisory only and never authorizes issue closure

M165 reports no agent execution, no model execution, no Codex execution, no GitHub execution, no source patch application, and no queue mutation.

## M164 GitHub Issue Status Comment Sync Routing Boundary

M164 does not add a new agent, local LLM, or Codex route. It adds a narrow GitHub issue status comment sync route for one queue item, using local queue status, run monitor evidence, validation evidence, artifact references, and machine gates.

Routing rules:

- default routing is dry-run status comment evidence only
- real GitHub routing requires `--github-enabled`, `github_issue_sync_enabled` autonomy profile, linked issue metadata or `--issue-number`, safe queue item status, and a passing `github_sync` machine gate
- missing, blocked, cancelled, unsafe-status, or gate-blocked queue items route to blocked output before any GitHub client call
- synced comment metadata routes to operator review only; queue completion or issue-link mutation remains a separate explicit future action

M164 reports no agent execution, no model execution, no Codex execution, no source patch application, and no queue mutation. `github_execution_performed=true` can appear only on the explicit live status comment sync path after gates pass.

## M163 GitHub Issue Creation Routing Boundary

M163 does not add a new agent, local LLM, or Codex route. It adds a narrow GitHub issue creation route for one safe queue item, using local M162 issue draft metadata and machine gates.

Routing rules:

- default routing is dry-run issue creation evidence only
- real GitHub routing requires `--github-enabled`, `github_issue_sync_enabled` autonomy profile, no linked issue metadata, safe queue item status, and a passing `github_sync` machine gate
- linked, blocked, cancelled, missing, or gate-blocked queue items route to blocked output before any GitHub client call
- created issue metadata routes to operator review only; queue issue-link mutation remains a separate explicit future action

M163 reports no agent execution, no model execution, no Codex execution, no source patch application, and no queue mutation. `github_execution_performed=true` can appear only on the explicit live issue creation path after gates pass.

## M162 GitHub Issue Sync Plan Routing Boundary

M162 does not add a new agent, local LLM, Codex, or live GitHub route. It routes local queue metadata into a deterministic issue sync plan for operator review.

Routing rules:

- queue items route to local issue drafts with title, body, labels, milestone, and candidate comments
- local linked-issue metadata routes items toward update/comment recommendations
- unlinked queue items route toward create recommendations
- blocked or cancelled queue items route toward skip recommendations
- all recommendations remain local evidence and do not authorize live GitHub mutation

M162 reports no agent execution, no model execution, no Codex execution, no GitHub execution, no source patch application, and no queue mutation.

## M161 Codex Loop Validation Evidence Bundle

M161 does not add a new agent, local LLM, GitHub, or live Codex execution route. It routes existing local Codex loop dry-run evidence into a durable validation evidence bundle for operator review.

Routing rules:

- bundle generation requires `--dry-run`
- Codex loop evidence routes through the existing dry-run dispatch, ingestion, validation selection, and completion recommendation path
- stdout/stderr, changed files, validation commands/results, machine gates, source patch classification, retry classification, and completion recommendation are bundled as local evidence
- source patch and retry outputs are advisory classifications only; no patch apply or retry route is authorized by the bundle
- queue completion and GitHub sync remain separate explicit gated routes

## M160 Low-Risk Codex Execution Pilot Item

M160 adds a pilot coordination route for exactly one low-risk Codex item. It does not add a local LLM route and does not route through GitHub automation. Dry-run preparation routes through M159 preflight evidence and M152/M151 loop artifacts without invoking Codex.

Routing implications:

- default route is dry-run pilot evidence only
- real Codex routing requires explicit operator flags, low-risk changed paths, passing M159 preflight, and the existing M152 machine-gated loop
- dirty worktree, non-low-risk tags, unsatisfied dependencies, high-risk changed paths, or failed preflight route to blocked output
- M160 reports Codex execution only when the explicit real path actually invokes the configured Codex command; model, GitHub, patch, queue, retry, resume, and next-item execution remain false

## M159 Real Codex Execution Preflight Hardening

M159 does not add a new agent, Codex, local LLM, or GitHub execution route. It adds a dry-run preflight route that composes local policy and readiness evidence before any separate real Codex command can be considered.

Routing implications:

- future real Codex remains routed only through explicit low-risk Codex commands with required operator flags
- dirty worktree, missing artifact readiness, invalid run-store state, unsuitable autonomy profile, or failed local gates route to blocked preflight output
- validation profile selection routes to planning evidence only; M159 does not run validation commands
- retry policy routes to stop/manual-review guidance only; no automatic retry route is introduced
- source patch output routes to default-deny policy and separate future dry-run/apply boundaries, not automatic application
- M159 reports no agent execution, no model execution, no Codex execution, no GitHub execution, no patch application, and no queue mutation by the preflight command itself

## M158 Operator Autonomy Configuration Profile

M158 does not add a new agent, Codex, local LLM, or GitHub execution route. It adds an explicit profile layer that lets operators and future orchestration code inspect whether a capability is currently `enabled`, `dry_run_only`, or `blocked`.

Routing implications:

- the default route is `locked_down`, which permits local inspection only
- `codex_dry_run` and `codex_low_risk_enabled` describe Codex routing boundaries but do not invoke Codex from the inspector
- `github_sync_dry_run` and `github_issue_sync_enabled` describe GitHub sync boundaries but do not call GitHub or `gh` from the inspector
- `experimental_full_local` remains explicit-selection metadata and does not bypass per-command machine gates
- M158 reports no agent execution, no model execution, no Codex execution, no GitHub execution, no patch application, and no queue mutation by the profile inspector itself

## M157 Run Replay and Audit Trail

M157 does not add a new agent, Codex, local LLM, or GitHub execution route. It routes prior orchestration evidence into a dry-run replay/audit record so operators can reconstruct what happened before considering any separate recovery, cleanup, or completion command.

Routing implications:

- replay input routes through local durable history, monitor, retention, and artifact evidence
- missing run evidence routes to local history/store inspection, not execution
- reconstructed source gates and execution flags route to operator audit review only
- M157 reports no agent execution, no model execution, no Codex execution, no GitHub execution, no patch application, no artifact cleanup, and no queue mutation by the replay command itself

## M156 Orchestration Artifact Retention Policy

M156 does not add a new agent, Codex, local LLM, or GitHub execution route. It indexes local orchestration artifacts so routing, recovery, and audit work can distinguish retained evidence, stale artifacts, and orphan candidates before any future cleanup or recovery action is considered.

Routing implications:

- artifact evidence routes through a local retention index before cleanup planning
- orphan artifacts route to operator review against durable run history, not automatic deletion
- stale artifacts route to advisory cleanup planning, not execution
- M156 reports no agent execution, no model execution, no Codex execution, no GitHub execution, no patch application, and no queue progression by the retention inspector itself

## M155 Durable Orchestration Run Store

M155 does not add a new agent, Codex, local LLM, or GitHub execution route. It adds durable local persistence for orchestration run records so routing and recovery decisions can reference stable run evidence instead of ephemeral artifacts or missing-history warnings.

Routing implications:

- orchestration run evidence routes through `.aresforge/orchestrator/run_history.json`
- failed, blocked, interrupted, running, or max-step-limited runs can be inspected reliably before any future recovery command is considered
- corrupt or invalid store state routes to local repair/restoration, not execution
- M155 reports no agent execution, no model execution, no Codex execution, no GitHub execution, no patch application, and no queue progression by the store inspector itself

## M154 Sprint Closeout and Autonomy Readiness Report

M154 does not add a new execution route. It routes local sprint evidence into a readiness report by reading queue records, machine gate output, the agent registry, the LLM decision policy, and the orchestration monitor.

Routing implications:

- completed M140-M154 evidence routes to next-sprint planning, not automatic execution
- missing queue/doc/gate evidence routes to local remediation and rerun of the report
- real Codex remains routed only through explicit low-risk execution commands with machine gates and validation
- local LLM output remains advisory and never routes to automatic patch application
- M154 reports no agent execution, no model execution, no Codex execution, no GitHub execution, no patch application, and no queue mutation by the report itself

## M153 Hub Orchestration Run Monitor

M153 does not add any new agent, Codex, local LLM, or GitHub execution route. It routes existing local orchestration run evidence into a Hub-readable status record by composing M141 run history and M147 resume-plan output.

Routing implications:

- completed runs route to artifact review and separate gated follow-on commands
- blocked, failed, interrupted, running, and max-step-limited runs route to operator recovery review
- resume-eligible runs remain advisory and route only to a future explicit machine-gated resume command
- M153 reports no agent execution, no model execution, no Codex execution, no GitHub execution, no patch application, and no queue mutation by the monitor itself

## M152 End-to-End Codex Loop Real Run for Low-Risk Code

M152 routes one queue item through a real Codex dispatch path only when the operator supplies explicit real-execution and low-risk-code flags. It still does not route through local LLM providers or GitHub automation. The Codex process is captured through M135, then evidence is routed through M136 validation and completion recommendation.

Routing implications:

- Codex-routed low-risk code can move from M151 dry-run evidence to a real local dispatch only through `--execution-enabled`, `--allow-low-risk-code`, and declared low-risk changed paths
- workflow, protected config, queue-state, Hub, orchestration, Codex runtime, script, migration, and undeclared path scopes route to blocked/operator review
- successful real dispatch routes to M136 allowlisted validation before any queue completion consideration
- M152 reports Codex execution separately from GitHub, patch application, queue mutation, and next-item execution, all of which remain false

## M151 End-to-End Codex Loop Dry Run

M151 adds `run-end-to-end-codex-loop` as the first dry-run coordinator across the Codex dispatch, ingestion, validation-selection, and completion-recommendation path. It does not execute agents or models. It routes one local queue item through M135 dry-run dispatch evidence and M136 dry-run ingestion evidence while preserving default-deny real Codex behavior.

Routing implications:

- Codex-routed queue work can now be tested through a full local dry-run loop before any real execution is enabled
- passing M151 evidence still routes to separate explicit commands for real Codex execution, validation, source patch handling, and queue completion
- dirty worktree or downstream completion-gate blockers remain visible as advisory handoff evidence
- M151 reports no agent execution, no model execution, no real Codex execution, no GitHub execution, no patch application, no validation command execution, and no queue mutation

## M150 Machine-Gated Source Patch Apply Dry Run

M150 adds `dry-run-source-patch-apply` as the first machine-gated source patch applicability proof. It does not execute agents or models. It maps an M149 apply plan to a dedicated dry-run machine gate and a `git apply --check` result without applying the patch.

Routing implications:

- source/code patch output can be routed from classification to planning to dry-run applicability evidence
- failed M149 planning, hard apply blockers, failed machine gates, or failed `git apply --check` route back to patch refresh or operator review
- passing dry-run evidence still routes to a future explicit apply command, machine gate, validation profile, and completion evidence path
- M150 reports no agent execution, no model execution, no Codex execution, no GitHub execution, no real patch application, no validation command execution, and no queue mutation

## M149 Controlled Source Patch Apply Planning

M149 adds `plan-source-patch-apply` as a non-executing planning layer after M148 source patch risk classification. It does not execute agents or models. It maps a local patch classification to hard apply blockers, future apply steps, validation requirements, rollback guidance, and explicit non-execution flags.

Routing implications:

- source/code patch output can be routed toward controlled apply planning without being applied
- hard blockers route workflow, protected config, queue-state, binary, executable-mode, and outside-repo patches back to operator review or redesign
- lower-risk source/test patches can produce a future controlled apply plan, but still require a separate explicit apply command, machine gate, clean apply check, operator review, and validation evidence
- M149 reports no agent execution, no model execution, no Codex execution, no GitHub execution, no patch application, no validation command execution, and no queue mutation

## M148 Source Patch Risk Classification

M148 adds `classify-source-patch-risk` as a non-executing safety layer between generated source patches and any future explicit apply path. It does not execute agents or models. It maps a local unified patch to touched files, path classes, mutation types, risk level, blocked operations, and recommended validation profile metadata.

Routing implications:

- source/code patch output can be routed toward review and validation planning without being applied
- workflow, protected config, queue-state, binary, executable-mode, and outside-repo patch operations route to operator review and expanded validation
- lower-risk source/test patches still require a separate explicit apply boundary and validation evidence before completion
- M148 reports no agent execution, no model execution, no Codex execution, no GitHub execution, no patch application, no validation command execution, and no queue mutation

## M147 Orchestrator Resume-from-Failure

M147 adds `inspect-orchestration-resume-plan` as the recovery bridge between orchestration run history and any future explicit resume command. It does not execute agents or models. It maps one local run id to checkpoint validity, resume eligibility, source execution flags, and pre-resume checks.

Routing implications:

- interrupted and max-step-limited orchestration runs can be routed toward future resume only when checkpoint evidence and read-only gates pass
- failed, blocked, mutating, Codex, GitHub, patch, external-execution, queue-mutating, or failed-gate runs route first to validation, classification, or operator review
- M147 reports no agent execution, no model execution, no Codex execution, no GitHub execution, no patch application, no validation command execution, and no queue mutation

## M146 Agent Step Result Normalization

M146 adds `normalize-agent-step-result` as the schema bridge between heterogeneous agent step outputs and orchestrator recovery logic. It does not execute agents or models. It maps one local result artifact to stable status, blocker, gate, artifact, and execution-flag fields.

Routing implications:

- routing and orchestration can evaluate one canonical step result schema instead of agent-specific output shapes
- source execution flags are preserved for recovery and validation decisions, while normalizer execution flags remain false
- mutating, Codex, GitHub, model, patch, failed, blocked, invalid, interrupted, or failed-gate results require separate explicit recovery or validation commands
- M146 itself reports no agent execution, no model execution, no Codex execution, no GitHub execution, no patch application, no validation command execution, and no queue mutation

## M145 Codex Failure Classification and Retry Policy

M145 adds `classify-codex-failure` as the recovery policy bridge after a Codex dispatch, orchestration step, or ingestion handoff reports failure. It does not execute Codex or models. It maps a local failure artifact to a primary failure class and deterministic retry/stop policy.

Routing implications:

- failure classification is advisory evidence for recovery planning, not permission to retry
- automatic retry loops are prohibited
- timeout and nonzero-process failures may be manual-retry-capable, but only through a separate explicit operator command with machine gates
- gate, execution-denied, dirty-worktree, validation, evidence, interruption, artifact, and unknown failures stop until recovery evidence exists
- M145 reports `model_execution_performed=false`, `codex_execution_performed=false`, `github_execution_performed=false`, `patch_application_performed=false`, `validation_command_execution_performed=false`, and `mutation_performed=false`

## M144 Codex Validation Profile Expansion

M144 adds `inspect-codex-validation-profiles` as the validation planning bridge after Codex routing and execution capture. It does not execute Codex or models. It maps task type, changed path class, and risk class to an allowlisted M136 validation profile.

Routing implications:

- documentation-only and tests-only outputs can use narrow local profiles when risk is low
- Hub UI, queue-system, Codex runtime, and orchestration changes route to matching targeted profiles
- high, critical, unknown, protected, workflow, and mixed-risk outputs expand to broader local-safe validation
- M144 reports `model_execution_performed=false`, `codex_execution_performed=false`, `github_execution_performed=false`, `patch_application_performed=false`, `validation_command_execution_performed=false`, and `mutation_performed=false`

## M143 Codex Sandbox/Worktree Guard

M143 adds `inspect-codex-worktree-guard` as the local guard evidence layer between routing recommendations and real Codex execution. It does not execute Codex. It records whether the worktree is dirty, what sandbox rules future Codex execution must obey, and where stdout, stderr, and execution metadata must be captured.

Routing impact:

- Codex recommendations remain advisory when the worktree is dirty or guard evidence has not been reviewed.
- Real Codex dispatch still requires `run-codex-dispatch --execution-enabled` and the `codex_dispatch` gate.
- Orchestrated Codex steps still require `run-agent-orchestration --allow-codex` and per-step gates.
- M136 validation remains the required handoff before completion evidence can be trusted.
- M143 reports `model_execution_performed=false`, `codex_execution_performed=false`, `github_execution_performed=false`, `patch_application_performed=false`, and `mutation_performed=false`.

## M142 Real Codex Execution Enablement Profile

M142 adds `inspect-codex-execution-enablements` as the policy bridge between routing recommendations and real Codex execution. It does not execute Codex. It records that Codex lanes may become executable only through separate explicit commands with allow flags and passing machine gates.

Routing impact:

- Codex recommendations from M127 or routed queue metadata remain advisory until a prepared dispatch artifact and explicit runner command are selected.
- The default enablement profile is `real_codex_default_deny`.
- Single Codex dispatch requires `run-codex-dispatch --execution-enabled` and the `codex_dispatch` gate.
- Orchestrated Codex steps require `run-agent-orchestration --allow-codex` and per-step machine gates.
- M136 validation remains the required handoff before completion evidence can be trusted.
- M142 reports `model_execution_performed=false`, `codex_execution_performed=false`, `github_execution_performed=false`, `patch_application_performed=false`, and `mutation_performed=false`.

## M141 Orchestration Run History and Recovery

M141 adds `inspect-orchestration-run-history` as the local recovery evidence view for orchestrated agent runs. Routing decisions may reference run history and recovery records, but those records remain advisory: they do not authorize retry, resume, patch application, queue mutation, Codex execution, local LLM execution, GitHub sync, or automatic next-item work.

New explicit `run-agent-orchestration` runs append local metadata to `.aresforge/orchestrator/run_history.json`; older `artifacts/multi-agent-orchestration/**.json` records remain discoverable for continuity.

## M140 Orchestrator Execution State Machine

M140 adds `inspect-orchestrator-state-machine` as a read-only contract for future orchestration hardening. The state machine makes queue inspection, plan loading, gate checks, checkpoints, step dispatch, validation, recovery, and terminal states explicit before the real Codex loop is expanded.

Routing impact:

- LLM and Codex lanes remain recommendations or separately gated execution paths.
- Any future executable transition must declare and pass the relevant machine gate, such as `local_llm_execution`, `codex_dispatch`, `github_sync`, `docs_only_patch_apply`, or `local_artifact_write`.
- The inspector itself reports `model_execution_performed=false`, `codex_execution_performed=false`, `github_execution_performed=false`, `patch_application_performed=false`, and `mutation_performed=false`.
- Real Codex execution remains default-deny unless a dedicated command and explicit flags allow it.

## M139 Autonomous Sprint Closeout

M139 closes the M125-M139 agent foundation sprint and records the routing/autonomy transition. The sprint now has a declared runtime boundary, agent registry, LLM decision policy, orchestration plan builder, dry-run executor, low-risk real local-agent executor, machine gate engine, safe queue auto-completion, docs-only autonomous apply, local LLM advisory execution, Codex dispatch, Codex result ingestion/validation, GitHub sync, and multi-agent orchestration.

Full sprint span: M125, M126, M127, M128, M129, M130, M131, M132, M133, M134, M135, M136, M137, M138, and M139.

Routing posture after closeout:

- LLM decisions remain recommendation records unless an explicit downstream runner is selected.
- Local LLM execution exists only as advisory local Ollama execution behind `local_llm_execution` gates; model output is never applied automatically.
- Codex execution exists only through prepared dispatch artifacts, explicit `--execution-enabled`, and `codex_dispatch` gates; M136 validation must follow before completion.
- GitHub sync exists only for narrow issue/PR comments or metadata summaries with `--github-enabled` and `github_sync` gates.
- Multi-agent orchestration may run dry-run steps by default and low-risk local real steps with `--allow-low-risk-real`; high-risk real steps require dedicated allow flags and gates.
- PR merge, force push, automatic issue closure, source-code patch application from generated output, background workers, and automatic next-item execution remain blocked.

## M134 Local LLM Advisory Execution

M134 introduces the first current-batch local LLM advisory execution surface: `run-local-llm-advisory`. It consumes a local advisory request artifact and requires the `local_llm_execution` machine gate profile before provider invocation. This narrows routing execution to a single explicit operator command and does not turn route recommendations, orchestration plans, approval records, or queue metadata into automatic dispatch.

Provider routing remains local-only. Ollama is the only supported provider, remote providers are blocked, and output is stored as advisory evidence rather than applied code. The command preserves `advisory_only=true`, `patch_application_performed=false`, `queue_mutation_performed=false`, `github_execution_performed=false`, and `codex_execution_performed=false`.

## M124 Sprint Closeout Note

M124 closes the M110-M124 controlled automation sprint and confirms that routing remains advisory. M117 route recommendations, M119 artifact registry results, M120 batch sequences, M121 approval ledger records, and M122 transaction log entries may guide operator decisions, but they do not dispatch agents, execute Codex, invoke local or remote LLMs, call GitHub/`gh`, apply patches, mutate queue state from recommendations, or start follow-on work.

The next sprint may add stronger machine gates and low-risk local executor records, but any model, Codex, GitHub, or patch execution must remain a separate explicit milestone with operator approval and evidence requirements.

## Status

M44A documented the future Agent/LLM routing strategy. M51 through M73 now add non-executing contracts and local Hub surfaces for project AI settings, agent/engine registry, queue routing metadata, recommendation-only routing decisions, Project AI Settings UI, routed queue views, routing-aware prompt packs, local LLM environment/health checks, Codex CLI model profile configuration, local LLM prompt preview/execution gates, Codex high-value prompt generation, a local execution audit log, centralized AI action safety gate decisions, a local AI artifact registry, an Operator Run History panel, an AI Action Review Panel, closeout reconciliation documentation, local AI operations hardening, verification, local LLM provider configuration hardening, and prompt-pack quality/routing guidance.

M74 stabilized the Hub wording around those surfaces. M75 reconciles the source-of-truth documentation and roadmap without adding execution behavior.

M81 adds a read-only local LLM advisory/coding lane readiness inspection path. It reuses M80 decision matrix output and local LLM environment/model metadata to produce structured advisory planning output without invoking a provider.

M83 adds a read-only local LLM provider contract. It makes Ollama the initial local provider target and exposes provider URL, health-check endpoint limits, timeout expectations, model identifiers, roles/capabilities, and safety boundaries without invoking the provider.

M86 adds deterministic confidence scoring to the M80 decision matrix. `inspect-llm-decision-matrix` now reports `routing_confidence` for Codex, local LLM advisory, local coding draft, and manual-only lanes. Scoring considers risk, task size, work mode, item type, dependencies, validation burden, provider availability, model profile availability, and recovery history. Scores are advisory metadata only and do not authorize execution or mutation.

M87 adds a local coding draft artifact mode. `prepare-local-coding-draft` can generate draft prompt artifacts and, only with an explicit operator `--run`, capture local draft patch/instruction output. Draft output is non-applied, non-authoritative, and cannot mutate files, apply patches, complete queue items, or start next items automatically.

M88 adds a human-gated patch application contract. `inspect-human-gated-patch-application-contract` defines patch artifact structure, explicit operator approval requirements, pre-apply safety gates, and post-apply validation requirements for any future manual patch application path. It is read-only and dry-run only.

M95 reconciles the completed overnight sprint documentation through M94. No routing runtime is added. Routing confidence, provider/model metadata, local advisory artifacts, local coding draft artifacts, and patch application contracts remain advisory/manual-review inputs only.

M96 is post-sprint planning and prioritization. It does not add routing runtime, dispatch execution, model invocation, or patch application.

M97 adds the first queue-to-agent dispatch plan contract. It wraps queue readiness and M80/M86 routing confidence into a local-only advisory payload with one selected lane, planned artifact intent, approval gates, blocked reasons, and `execution_allowed: false`. Its lanes are `codex_prompt_artifact`, `local_llm_advisory`, `local_llm_coding_draft`, `documentation_agent_dry_run`, and `human_only_manual`. Low-confidence, blocked, missing, or unclear items fall back to `human_only_manual`. M97 does not dispatch prompts, call Codex, invoke local LLMs, execute agents, or mutate queue/source state.

M98 adds the Codex prompt dispatch artifact generator for the `codex_prompt_artifact` lane only. It consumes or derives the M97 plan, blocks all non-Codex lanes, blocks unsafe plan flags, and emits manual/operator-gated prompt text or a local file. It does not execute Codex, invoke local LLMs, execute documentation agents, apply patches, call GitHub/`gh`, make network calls, or mutate queue state.

M99 adds the Local LLM Advisory Execution Dry-Run Validator for the `local_llm_advisory` lane only. It consumes or derives the M97 plan, blocks Codex, local coding draft, documentation-agent, and manual-only lanes, blocks unsafe plan flags, and emits structured dry-run readiness data with operator gates. It does not call Ollama APIs, execute local models, execute Codex, execute documentation agents, apply patches, call GitHub/`gh`, make network calls, or mutate queue state.

M100 adds the Documentation Agent Dry-Run Review Workflow for the `documentation_agent_dry_run` lane only. It consumes or derives the M97 plan, blocks Codex, local LLM advisory, local coding draft, and manual-only lanes, blocks unsafe plan flags, and emits structured dry-run review data with source docs, expected updates, stale-doc checks, reconciliation scope, validation expectations, and operator gates. It does not execute documentation agents, mutate documentation, call local LLMs, execute Codex, apply patches, call GitHub/`gh`, make network calls, or mutate queue state.

M101 adds the Human Approval Gate UI/Data Contract. It records local approval status for M98 Codex prompt artifacts, M99 local LLM advisory dry-runs, M100 documentation dry-runs, local coding draft artifacts, and future patch gates. Supported statuses are `pending_review`, `approved_for_manual_handoff`, `rejected`, and `needs_revision`. Approval records preserve `local_only: true` and `execution_allowed: false`; approval does not invoke Codex, Ollama/local models, documentation agents, GitHub/`gh`, external services, patch application, queue completion, or automatic next-item execution.

M102 hardens local queue dependency and completion locking. It does not add routing execution, but it gives future dispatch workflows a required local dependency/evidence gate before start, completion, or handoff state can be trusted.

M103 adds a read-only self-managed project review for `aresforge`. It confirms project identity, repo path, branch, queue counts, docs, warnings, and gaps before batch planning; it does not route or execute work.

M104 adds the Operator Batch Planner v1. It reads local queue state, excludes done items, respects dependency and blocked status constraints, and classifies proposed items as `manual_only`, `codex_artifact_possible`, `local_llm_dry_run_possible`, `documentation_dry_run_possible`, or `blocked`. Classification is advisory only and keeps `execution_allowed: false`.

M105 reconciles source-of-truth documentation and local project state after M99-M104. It does not add routing runtime, dispatch execution, model invocation, documentation-agent apply mode, or patch application.

M106 adds a read-only dispatch artifact index/report for local Codex prompt artifacts, local LLM advisory dry-run outputs, documentation-agent dry-run outputs, and approval gate status. It does not execute or validate artifacts beyond safe local reads.

M107 adds a safe dispatch handoff package that bundles queue state, dispatch plan summaries, artifact index summaries, approval gate summaries, warnings, blockers, and operator next actions. It keeps `execution_allowed=false` and does not authorize dispatch.

M108 closes the M99-M107 sprint and defines the next controlled automation batch. It is docs/data-only and does not add routing runtime, runner behavior, provider invocation, documentation-agent apply mode, patch intake, or automated queue completion.

M109 adds the Manual Codex Dispatch Runner Contract. It prepares a local record and operator checklist for manually running a previously generated M98 Codex prompt artifact outside AresForge. It requires `selected_lane=codex_prompt_artifact`, `local_only=true`, `execution_allowed=false`, an existing Codex prompt artifact, an approved M101 gate, and lifecycle-safe queue state. It always reports `codex_execution_performed=false` and does not execute Codex, shell out to Codex CLI, invoke providers, call GitHub/`gh`, apply patches, mutate queue state, or complete work automatically.

M110 adds the Local LLM Advisory Artifact Generator for the `local_llm_advisory` lane only. It consumes or derives the M97 dispatch plan, blocks non-advisory lanes and unsafe plan flags, writes a structured local request artifact with source documents, queue context, advisory prompt, expected response shape, and operator checklist, and preserves `execution_allowed=false`. It does not invoke Ollama/local models, execute Codex, call GitHub/`gh`, make network calls, execute agents, apply patches, mutate queue state, or complete work automatically.

M111 adds the Approval-Gated Patch Intake Contract. It records a proposed patch artifact for review only after a local M101 approval gate is `approved_for_manual_handoff`, summarizes the patch, and keeps `patch_application_allowed=false`, `patch_application_performed=false`, and `execution_allowed=false`. It does not apply patches, mutate repository files, execute Codex/local LLMs/documentation agents, call GitHub/`gh`, make network calls, mutate queue state, or complete work automatically.

M115 adds the Local Ollama Provider Probe Integration. It is environment discovery only: configuration-only when `--no-network` is supplied, or loopback `/api/tags` inspection when explicitly allowed by command invocation and provider URL safety. It reports model-profile metadata and visible model names when safely detectable, but it never sends prompts, never invokes generation/chat/completion/coding/reasoning endpoints, never routes work to a model, and never mutates repository, queue, approval, GitHub, or patch state.

M125 adds the Agent Runtime Boundary Contract. `inspect-agent-runtime-boundary` defines the future agent runtime schema and enforcement catalog before execution exists. It declares required fields for `agent_id`, `agent_type`, `execution_mode`, `input_contract`, `output_contract`, `allowed_capabilities`, `forbidden_capabilities`, `mutation_scope`, `network_scope`, `model_scope`, `timeout_policy`, `retry_policy`, `evidence_requirements`, `safety_class`, and `autonomy_level`. It also exposes supported execution modes, autonomy levels, safety classes, capability catalogs, mutation/network/model scope catalogs, evidence requirements, default runtime limits, and `execution_performed=false`. M125 does not execute agents, invoke models, call Codex, call GitHub/`gh`, apply patches, or mutate queue/source state.

M126 adds the Agent Registry. `inspect-agent-registry` declares the initial known AresForge agents and their inputs, outputs, supported item types, capabilities, scopes, safety classes, autonomy levels, default execution modes, evidence requirements, and source docs. Registered agents include the queue planner, Codex dispatch, local LLM advisory, documentation, evidence parser, completion recommendation, validation, GitHub sync, sprint summary, artifact registry, approval ledger, and transaction log agents. The registry is metadata only: every M126 agent has `can_run_real=false`, and registry inspection does not execute agents, invoke models, dispatch Codex, call GitHub/`gh`, call network services, apply patches, create workflows, mutate queue/source state, or start follow-on work.

M127 adds LLM Decision Policy v1. `recommend-llm-decision` emits machine-readable recommendations for one queue item or agent task. It supports `no_llm_required`, `local_llm_reasoning`, `local_llm_coding_review`, `codex_coding`, `codex_reasoning`, `remote_high_value_reasoning`, `remote_low_cost_reasoning`, `documentation_agent`, `validation_agent`, and `github_sync_agent`. The policy considers queue item type, risk level, mutation scope, code/docs/planning shape, context size, repo-aware coding need, deterministic validation need, local-only requirement, GitHub/network requirement, test verifiability, agent id, and autonomous execution hints. M127 is recommendation-only and always reports `execution_performed=false`; it does not invoke providers, run agents, dispatch Codex, call GitHub/`gh`, run validation commands, apply patches, mutate queue/source state, or start follow-on work.

M117 adds the Agent Routing Decision Dashboard and `recommend-agent-route`. It translates local queue metadata into a simpler operator-facing lane recommendation for `codex_prompt_artifact`, `local_llm_advisory_artifact`, `documentation_agent_patch_proposal`, `validation_agent_dry_run`, or `human_operator_manual_review`. The Hub panel displays recommended lane, alternatives, routing reasons, blockers, required artifacts, approval requirements, suitability flags, and next safe action. M117 is advisory-only and does not expose execute buttons, dispatch Codex, invoke Ollama/local LLMs, execute agents, call GitHub/`gh`, make network calls, apply patches, mutate source/queue state, or start follow-on work.

M118 reconciles the M110-M117 planning layer in source-of-truth docs. It confirms that route, LLM, patch, evidence, completion, Hub review, provider probe, and documentation proposal outputs are planning metadata only. It does not add routing runtime, dispatch execution, model invocation, agent execution, GitHub/`gh`, patch application, automatic queue completion, or next-item execution.

M128 adds the Agent Orchestration Plan Builder. `build-agent-orchestration-plan` consumes one queue item, the M126 registry, and the M127 decision policy to emit an ordered `agent_orchestration_plan` with per-step capabilities, forbidden capabilities, required artifacts, dependency checks, machine gates, blocked reasons, and `execution_performed=false`. It is a plan builder only. It does not execute agents, invoke providers, dispatch Codex, call GitHub/`gh`, call network services, run validation commands, apply patches, mutate queue/source state, or start follow-on work. `--execution-target real` is accepted as an input signal but blocks and recommends `dry-run` until a later explicit runner exists.

M129 adds the Single-Agent Dry-Run Executor. `run-agent-dry-run` may produce `single_agent_dry_run` records for deterministic local agents only: `artifact-registry-agent`, `evidence-parser-agent`, `completion-recommendation-agent`, `validation-agent`, `sprint-summary-agent`, and `queue-planner-agent`. It blocks unsupported agents and records forbidden capabilities as blocked. It does not execute Codex, invoke Ollama/local LLMs, call GitHub/`gh`, call network services, run validation commands, apply patches, mutate source/queue state from the dry-run, or start follow-on work. Optional `--output` writes only the dry-run execution record artifact.

M130 adds the Single-Agent Real Executor for Low-Risk Agents. `run-agent` may produce `single_agent_real_execution` records for deterministic local agents only: `artifact-registry-agent`, `evidence-parser-agent`, `completion-recommendation-agent`, `validation-agent`, `queue-planner-agent`, and `sprint-summary-agent`. Machine gates require a local queue item, registry real-execution eligibility, `network_scope=none`, `model_scope=none`, artifact-only mutation scope, and blocked forbidden capabilities. M130 writes only local execution records and local artifact files. It blocks Codex dispatch, local LLM advisory, documentation patch application, GitHub sync, network, model, and code-patch agents. It does not execute Codex, invoke Ollama/local LLMs, call GitHub/`gh`, call network services, run validation commands, apply patches, mutate source/queue state, or start follow-on work.

M131 adds the Machine Safety Gate Engine. `evaluate-machine-safety-gates` turns the scattered machine-gate concepts into one deterministic evaluator for `read_only_agent`, `local_artifact_write`, `queue_status_mutation`, `docs_only_patch_apply`, `local_llm_execution`, `codex_dispatch`, `github_sync`, and `multi_agent_orchestration`. It checks queue existence/status/dependencies, required artifacts, artifact and execution-record schema, forbidden capability usage, working-tree acceptability, file-path allowlists, docs-only patch targets, test evidence, warning thresholds, rollback/transaction-log availability, and explicit external allowance. M131 is the replacement path for human review only when a profile fully passes. It evaluates only and always reports `execution_performed=false` and `mutation_performed=false`; it does not execute agents, providers, Codex, GitHub, validation commands, patches, queue mutation, or follow-on work.

After M139, routing is no longer purely human-gated, but it is still machine-gated and explicit. The system can run deterministic low-risk local agents, apply docs-only patches, complete safe queue items, run local advisory LLM responses, dispatch Codex, perform narrow GitHub sync, and orchestrate multiple agents only through their dedicated commands and gates. High-risk source mutation, PR merge, force push, automatic issue closure, background automation, and automatic next-item execution remain unimplemented.

## M75 Source-of-Truth and Next Decision Matrix Direction

M75 is documentation-only. It prepares the next phase without implementing Codex CLI dispatch, agent execution, GitHub behavior, external workflow execution, unattended multi-item queue execution, or repository mutation from local LLM output.

The next decision-matrix direction is:

- M76 seeds AresForge as its first managed local project
- M77 defines the Codex CLI dispatch contract before execution exists
- M78 prototypes only one explicitly operator-approved Codex queue-item dispatch
- M79 enforces queue/dependency blocking before dependent movement
- M80 defines LLM decision matrix v2 for local LLM vs Codex, coding vs reasoning, model/profile selection, task size, risk, validation burden, and safety gating
- M81 extends local LLM lanes locally and advisory-first before any coding-output path
- M82 tests self-management using AresForge itself
- M83 formalizes the local LLM provider contract for advisory and future coding lanes
- M86 adds advisory-only routing confidence scoring for Codex, local LLM advisory, local coding draft, and manual-only lanes
- M87 adds local coding draft artifacts while preserving no automatic patch application or file mutation
- M88 defines the human-gated patch application contract while preserving dry-run-only behavior
- M95 reconciles the overnight sprint documentation and keeps the next phase manual/operator-selected
- M99-M104 add dispatch-plan dry-runs, approval gates, queue locks, self-managed review, and batch planning without widening execution
- M105 reconciles docs/data before the next manual sequence
- M106 indexes dispatch artifacts without execution
- M107 packages safe dispatch handoff context without execution authorization
- M108 closes the sprint and defines the next controlled automation batch

Next phase safety gates before any Codex dispatch implementation:

- explicit operator approval
- one item at a time
- no automatic next-item execution
- run state tracked
- stdout/stderr/artifacts captured where applicable
- error and completion states recorded
- review evidence required before marking complete
- queue/dependency blocking enforced
- local validation required before commit/push

Next recommended milestones remain manual/operator-selected:

- M109 Manual Codex Dispatch Runner Contract
- M110 Local LLM Advisory Artifact Generator
- M111 Approval-Gated Patch Intake Contract
- M112 Dispatch Result Evidence Parser
- M113 Queue Item Auto-Completion Recommendation Engine
- M114 Hub Dispatch Review Panel
- M115 Local Ollama Provider Probe Integration
- M116 Documentation Agent Patch Proposal Generator
- M117 Agent Routing Decision Dashboard
- M118 Post-Automation-Planning Reconciliation

## M73 Prompt Pack Quality and Routing Improvements

M73 improves generated prompt packs without adding execution behavior.

Prompt packs now include lane-specific guidance for high-value Codex, local LLM advisory, documentation/review, and operator-only/manual work. They also include advisory model/engine recommendation text, task sizing guidance, validation/smoke expectations, and final response requirements.

Codex high-value lane prompt-pack text remains prompt-generation/operator-handoff only. Local LLM advisory lane text explicitly states that local LLM output must not mutate repo files. Model/engine recommendations remain advisory metadata only and do not invoke a provider, select a fallback automatically, dispatch prompts, or authorize execution.

M73 does not add routing execution, Codex execution, Codex CLI invocation, local LLM execution, agent execution, GitHub API calls, `gh` calls, issues, PRs, workflow activity, external workflow execution, or automatic repository mutation from local LLM output.

## M72 Local LLM Provider Configuration Hardening

M72 clarifies local provider and model state without adding execution behavior.

The local LLM environment contract now exposes provider availability status, provider configuration status, provider execution mode, provider state, local model profiles, fallback behavior, and next safe operator action. Provider states distinguish configured, missing configuration, unavailable, unsupported, disabled, and prototype-only mode.

Local model profiles describe provider, model name, intended lane, recommended use, hardware notes, status, advisory warning, and prototype warning. These profiles are routing/review metadata only. They do not prove installation, select a fallback automatically, invoke a provider, execute prompts, or authorize local LLM execution.

Health-check output remains explicitly invoked and local-only. It may inspect local provider availability/model listing through the existing safe health path, but it keeps `inference_tested: false` and `execution_allowed: false`.

M72 does not add routing execution, Codex execution, agent execution, GitHub API calls, `gh` calls, issues, PRs, workflow activity, external workflow execution, automatic local LLM execution, or automatic repository mutation from local LLM output.

## M83 Local LLM Provider Contract

M83 adds `inspect-local-llm-provider-contract`.

The provider contract is a read-only routing input for advisory and future coding lanes. It reports:

- Ollama as the initial provider target
- local provider URL metadata
- request and health-check timeout expectations
- `/api/tags` as the only allowed health-check endpoint
- generation/chat/completion endpoints as forbidden from contract inspection and health checks
- reasoning, coding, and fallback model identifiers
- role/capability metadata for `local_reasoning_llm` and `local_coding_llm`
- explicit safety boundaries for no provider invocation, no repo mutation, no queue mutation, no automatic prompt execution, and no automatic next-item execution

M83 does not add routing execution, Codex execution, local LLM execution, agent execution, GitHub API calls, `gh` calls, issues, PRs, workflow activity, daemon/watch/scheduler behavior, external workflow execution, automatic local LLM execution, or automatic repository mutation from local LLM output.

## M86 Routing Confidence Scoring

M86 extends the M80 decision matrix with `routing_confidence`.

The confidence payload includes:

- selected `score`
- `confidence_level`
- `recommended_lane`
- rationale for the selected lane
- warnings for low confidence or blocking factors
- per-lane `scores` for Codex, local LLM advisory, local coding draft, and manual-only
- deterministic `factors` used by scoring

Scoring factors include risk, task size, work mode, item type, dependency count, unresolved dependencies, validation burden, local provider availability/configuration, local model profile availability, Codex model profile availability, recovered dispatch runs, and dispatch run blockers.

M86 confidence scoring is advisory-only. It does not execute prompts, call providers, call Codex, run agents, mutate queue state, complete queue items, start next items, call GitHub APIs, call `gh`, or interact with issues, PRs, workflows, daemons, watchers, schedulers, or external workflow systems.

## M87 Local Coding Draft Artifact Mode

M87 adds `prepare-local-coding-draft`.

The command can generate local coding draft prompt artifacts and, with explicit `--run`, capture draft output artifacts. Draft artifacts may contain patch-like text or implementation instructions, but the draft contract states:

- draft is non-authoritative
- draft has not been applied
- automatic patch application is not allowed
- automatic file mutation is not allowed
- manual review is required

M87 does not add routing execution, automatic local LLM execution, patch application, repository mutation, queue mutation, queue completion, automatic next-item execution, GitHub API calls, `gh` calls, issues, PRs, workflows, daemons, watchers, schedulers, or external workflow behavior.

## M88 Human-Gated Patch Application Contract

M88 adds `inspect-human-gated-patch-application-contract`.

The command reports:

- required patch artifact fields for generated local coding draft patches or operator instructions
- explicit operator approval requirements, including `APPROVE LOCAL PATCH APPLICATION`
- pre-apply safety gates for local-only operation, approval record presence, schema validation, target file scoping, path traversal prevention, manual diff review, validation plan presence, and no external workflow behavior
- post-apply validation requirements such as final diff review, `git diff --check`, targeted tests, relevant smoke checks, and separate queue evidence completion
- safety boundaries confirming patch application is not implemented and is not allowed automatically

M88 does not add routing execution, automatic local LLM execution, patch application, repository mutation, queue mutation, queue completion, automatic next-item execution, GitHub API calls, `gh` calls, issues, PRs, workflows, daemons, watchers, schedulers, or external workflow behavior.

## M95 Overnight Sprint Reconciliation

M95 is documentation reconciliation for the completed M81-M94 sprint. It confirms:

- local LLM advisory outputs are advisory artifacts only
- local coding draft outputs are non-applied and non-authoritative
- patch application remains future work behind explicit human approval and validation gates
- documentation reconciliation can plan but cannot automatically rewrite docs
- routing dashboard and confidence scoring are read-only/advisory data

M95 does not add routing execution, automatic local LLM execution, Codex invocation, patch application, repository mutation from generated output, queue mutation beyond explicit queue evidence commands, automatic queue completion, automatic next-item execution, GitHub API calls, `gh` calls, issues, PRs, workflows, daemons, watchers, schedulers, or external workflow behavior.

## M69 Local AI Operations Hardening

M69 tightens the AI-adjacent safety posture without adding execution behavior.

The safety gate now reports explicit safety status, gate status, blocked action, blocked reason category, and next safe operator action fields. Blocked categories distinguish policy-blocked external/automatic paths, gate-blocked local paths, missing operator approval, and invalid local state where applicable.

Execution audit entries, AI artifact registry records, and Operator Run History timeline entries now carry consistent non-mutation flags for repository mutation, external mutation, and automatic execution. Advisory local LLM and Codex prompt artifacts remain evidence/handoff records only.

M69 does not add routing execution, Codex execution, agent execution, GitHub API calls, `gh` calls, issues, PRs, workflow activity, external workflow execution, or automatic repository mutation from local LLM/Codex output.

## M68 Local AI Operations Closeout Reconciliation

M68 reconciles the local AI operations documentation sequence through M67.

Implemented local AI operations now include project AI settings, the agent/engine registry, queue routing metadata, routing decision matrix v1, routed queue views, routing-aware prompt packs, local LLM environment and health contracts, Codex CLI model profile configuration, local LLM prompt preview, the M62 operator-gated local LLM execution prototype, Codex high-value prompt generation, execution audit logging, the AI action safety gate, the AI artifact registry, and the Operator Run History panel.

The canonical queue boundary remains unchanged: there is one local queue, and routed queue views are filters over that queue rather than separate queue stores. Routing recommendations and metadata are advisory context unless the operator explicitly applies metadata through local queue controls.

The execution boundary remains unchanged: Codex high-value lane output is prompt generation/operator handoff only, Codex CLI execution is not implemented, local LLM execution is prototype-only/local-only/advisory-only/operator-gated, and generated model output is never applied to repository files automatically.

M68 does not add routing execution, Codex execution, agent execution, GitHub API calls, `gh` calls, issues, PRs, workflow activity, external workflow execution, or local LLM behavior beyond M62.

## M67 Operator Run History Panel

M67 adds a read-only operator-facing timeline over M64 audit entries and M66 artifact records.

Current operator helper:

- `read_operator_run_history(...)`

Current Hub route:

- `GET /api/operator-run-history`

The timeline includes audit and artifact entries sorted newest first, with project/item identifiers when available, action type, artifact type, outcome, summary, artifact path, executed state, and execution-allowed state.

M67 does not expose execution, apply, delete, GitHub, `gh`, Codex run, local LLM, agent, workflow, issue, or PR controls.

## M66 AI Artifact Registry

M66 adds local-only artifact discovery for generated AI-adjacent artifacts.

Current operator helpers:

- `register_ai_artifact(...)`
- `read_ai_artifact_registry(...)`
- `filter_ai_artifacts(...)`
- `verify_ai_artifact_exists(...)`

Current Hub route:

- `GET /api/ai-artifacts`

Storage:

- `.aresforge/ai_artifact_registry.json`

Supported artifact types are `prompt_pack`, `handoff`, `local_llm_prompt_preview`, `local_llm_execution_result`, `codex_high_value_prompt`, `report`, `audit_export`, and `other`.

The registry records successful local artifact writes for prompt packs, handoffs, local LLM prompt previews, local LLM advisory output artifacts, and Codex high-value prompts. It stores local artifact paths, source actions, optional queue/project/routing metadata, summary, checksum, existence state, and warnings.

M66 complements M64: the audit log records what action happened, while the artifact registry records where generated local artifacts live. M66 does not execute Codex, expand local LLM execution beyond M62, call GitHub API, call `gh`, create issues, create PRs, run workflows, overwrite artifact content, or mutate repository files from AI output.

## M65 AI Action Safety Gate

M65 adds centralized local-only decision/reporting logic for AI-adjacent actions.

Current operator helper:

- `evaluate_ai_action_safety_gate(...)`

Current Hub route:

- `POST /api/ai-action-safety-gate`

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

The gate evaluates action type, queue/routing context, engine/model/lane, risk, complexity, project AI mode, dry-run state, operator gate confirmation, and operator override. It reports blockers, warnings, `execution_allowed`, and next safe action.

M65 blocks Codex execution and GitHub/`gh` mutation representations, keeps preview-only actions non-executing, requires local engine routing for local LLM execution, requires explicit operator gate confirmation for real local LLM execution, and requires override for high/critical risk local execution.

M65 does not add new execution behavior, execute Codex, call GitHub API, call `gh`, create issues, create PRs, run workflows, mutate repository files from AI output, or expand M62 local LLM execution.

## M64 Execution Audit Log

M64 adds a local-only audit trail for operator-gated AI/lane-adjacent actions.

Current operator helpers:

- `append_execution_audit_entry(...)`
- `read_execution_audit_log(...)`
- `filter_execution_audit_log(...)`

Current Hub route:

- `GET /api/execution-audit-log`

Storage:

- `.aresforge/execution_audit_log.json`

Audit entries record action type, item/project identifiers when available, engine/model/lane metadata, operator gate state, dry-run/executed/execution-allowed booleans, outcome, blockers, warnings, artifact path, summary, and source function.

M64 logs local LLM health checks, local LLM prompt previews, local LLM dry runs/execution/blocked attempts, Codex high-value prompt generation, prompt-pack generation, and routing metadata updates. It does not store full prompt text or full LLM response text, and it redacts secret-like strings.

M64 does not execute Codex, expand local LLM execution beyond M62, call GitHub API, call `gh`, create issues, create PRs, run workflows, or mutate repository files from AI output.

## M63 Codex CLI High-Value Lane

M63 adds a local-only high-value Codex prompt lane over the canonical local queue.

Current operator helper:

- `generate_codex_high_value_lane_prompt(...)`

Current Hub route:

- `POST /api/local-queue/items/{item_id}/codex-high-value-prompt`

Eligibility inputs:

- queue routing metadata (`recommended_engine`, `recommended_agent_lane`, `recommended_model`, `risk_level`, `complexity_level`, `project_ai_mode`, and reasons)
- queue item title, description, notes, and tags for affected-area and validation-burden signals
- optional operator override

Codex-worthy criteria:

- `recommended_engine` is `codex_cli`
- `recommended_agent_lane` is `high_value_codex`
- `risk_level` is high or critical
- `complexity_level` is high
- affected area includes backend/operator lifecycle, data contracts, API routes, queue lifecycle, routing matrix, execution path, evidence/closeout, or docs source-of-truth reconciliation
- validation burden is high
- `project_ai_mode` is `codex_only` or `high_confidence`
- operator override requests Codex

The generated prompt includes operating rules, files to inspect, pre-checks, implementation goal, constraints, validation commands, smoke checks, `git diff --check`, commit/push-after-validation guidance, and required final response format.

M63 does not execute Codex, call Codex CLI, call GitHub API, call `gh`, create issues, create PRs, run workflows, or mutate repository files from Codex output. `execution_allowed` is always false.

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

## M58 Local LLM Environment Contract

M58 adds a local-only Local LLM Environment Contract for future health checks and operator-gated local execution work.

Current operator helpers:

- `read_local_llm_environment_contract(...)`
- `update_local_llm_environment_contract(...)`
- `validate_local_llm_environment_contract(...)`

Current Hub routes:

- `GET /api/local-llm/environment`
- `POST /api/local-llm/environment`

Storage path:

- `.aresforge/local_llm_environment.json`

Supported providers:

- `ollama`
- `none`
- `unknown`

Fields:

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

The contract is configuration only in M58. Model names are placeholders/config values and do not claim that a model is installed. `health_check_enabled` may be stored, but no health check runs in M58. M62 allows `execution_enabled: true` only for the operator-gated local prototype, and `operator_gate_required` must remain true.

M58 does not call Ollama, call model APIs, perform health checks, send prompts, execute routing, invoke local LLMs, invoke Codex, run agents, call GitHub, or run external workflows.

## M59 Local LLM Health Check

M59 adds an explicitly invoked Local LLM Health Check.

Current operator helper:

- `check_local_llm_health(...)`

Current Hub route:

- `POST /api/local-llm/health-check`

The health check reads the M58 contract. Provider `none` or `unknown` returns an unavailable/blocked result without provider calls. Provider `ollama` may call only a local `/api/tags` endpoint to check provider reachability and list local model names.

The health check returns:

- provider
- provider base URL
- configured reasoning model
- configured coding model
- provider reachability
- available models
- configured model availability
- `inference_tested: false`
- `execution_allowed: false`
- checked timestamp
- warnings and blockers

M59 does not send prompts, call generate/chat/completion endpoints, run model inference, generate text, execute routing, invoke Codex, run agents, mutate queue/project state, call GitHub, or run external workflows. M61 adds Local LLM Prompt Preview. M62 adds an operator-gated local execution prototype.

## M60 Codex CLI Model Profile Contract

M60 adds a local-only Codex CLI Model Profile Contract.

Current operator helpers:

- `read_codex_cli_model_profile_contract(...)`
- `update_codex_cli_model_profile_contract(...)`
- `validate_codex_cli_model_profile_contract(...)`

Current Hub routes:

- `GET /api/codex-cli/model-profiles`
- `POST /api/codex-cli/model-profiles`

Storage path:

- `.aresforge/codex_cli_model_profiles.json`

Codex CLI remains engine `codex_cli`. The contract stores default, high-value, and fast Codex model preferences, an allowed model list, and optional per-project/per-agent allowed model mappings.

The contract is configuration only. `execution_enabled` must remain false and `operator_gate_required` must remain true for Codex CLI model profiles.

M60 does not execute Codex CLI, execute prompts, run agents, call GitHub, call `gh`, or run external workflows. M63 should add Codex CLI High-Value Lane planning and still must remain operator-gated unless a later execution milestone explicitly changes that boundary.

## M61 Local LLM Prompt Preview

M61 adds preview-only local LLM prompt generation for routed queue items.

Current operator helper:

- `generate_local_llm_prompt_preview(...)`

Current Hub route:

- `POST /api/local-queue/items/{item_id}/local-llm-prompt-preview`

Current UI path:

- Queue -> Local LLM Prompt Preview

The preview reads canonical queue routing metadata and the M58 local LLM environment contract. It produces copy/paste prompt text only and returns `execution_allowed: false`.

Preview output includes:

- task title and details
- project context when available
- routing metadata
- local-only operating rules
- no GitHub API/`gh`/GitHub mutation reminder
- validation expectations
- final response format
- instruction that a local LLM must not claim execution when only reviewing or planning

Preview is allowed for queue items routed to `local_reasoning_llm` or `local_coding_llm` when the local environment/model configuration is present. It blocks or warns for `codex_cli` routes, unrouted items, missing local model configuration, malformed environment contract, high-risk policy concerns, and `manual_only` mode without operator override.

M61 does not call Ollama, send prompts, run model inference, generate text, execute routing, invoke Codex, run agents, mutate GitHub, call `gh`, or run external workflows. M62 adds the first operator-gated local LLM execution prototype.

## M62 Operator-Gated Local LLM Execution Prototype

M62 adds the first conservative local LLM execution prototype.

Current operator helper:

- `execute_local_llm_for_queue_item(...)`

Current Hub route:

- `POST /api/local-queue/items/{item_id}/local-llm-execute`

Current UI path:

- Queue -> Prototype: Run Local LLM

Execution gates:

- explicit operator request
- queue item exists
- routing metadata recommends `local_reasoning_llm` or `local_coding_llm`
- local LLM environment has `execution_enabled: true`
- local LLM environment keeps `operator_gate_required: true`
- provider is local `ollama`
- provider URL is local-only
- prompt preview is generated
- health check confirms provider reachability and model availability for real execution
- high or critical risk requires operator override

Dry run validates gates and returns the prompt preview without calling the provider. Real execution calls only the configured local provider and captures advisory response text. Optional result artifacts are local-only and refuse overwrite unless `force=true`.

M62 does not execute Codex CLI, call GitHub, call `gh`, mutate GitHub, execute external/non-local LLM providers, auto-run agents, apply response text to files, start/complete/close queue items, create commits, push code, or run workflows. M63 added Codex CLI High-Value Lane as a non-automatic prompt-generation/operator-handoff lane.

## M70 Local AI Operations Verification Sweep

M70 verifies the M58-M69 local AI operations chain without expanding execution.

Verification scope:

- local LLM environment contract, health check, prompt preview, and M62 operator-gated local execution prototype
- Codex CLI model profile contract and Codex high-value prompt lane
- execution audit log, AI action safety gate, AI artifact registry, and Operator Run History
- queue lifecycle, Hub API, and Hub UI rendering expectations for safety/gate/non-mutation metadata

The verified boundary remains: local-first, file-backed, operator-gated, advisory-only for local LLM output, and prompt-generation/operator-handoff only for Codex high-value work.

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
- local LLM execution outside the M62 explicit operator-gated local prototype
- LLM/model routing execution
- GitHub API calls, `gh`, GitHub issues, PRs, workflows, or GitHub mutation from the app
- external/network execution beyond existing local Hub API behavior
- unattended multi-item execution
- repository mutation from local LLM or Codex output

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
