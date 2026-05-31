# AresForge Agent Context

## M152 End-to-End Codex Loop Real Run for Low-Risk Code Context

Status: Completed locally on `main` after validation.

Queue item: `m152-end-to-end-codex-loop-real-run-for-low-risk-code`.

M152 extends `run-end-to-end-codex-loop` from M151 dry-run evidence into a real, local-first Codex loop for low-risk code only.

Dry-run command:

- `python -m aresforge run-end-to-end-codex-loop --item-id m152-end-to-end-codex-loop-real-run-for-low-risk-code --dry-run --format json`

Real execution requirements:

- `--execution-enabled`
- `--allow-low-risk-code`
- one or more `--changed-path` values limited to low-risk source/test scope
- passing M135 `codex_dispatch` machine gate
- clean worktree enforcement from the dispatch executor for non-dry-run execution
- M136 ingestion and allowlisted local validation before any completion decision

Agent-facing guidance:

- Treat `end_to_end_codex_loop_real_low_risk_v1` output as local execution/validation evidence only.
- `status=dry_run_completed` means no real Codex process ran.
- `status=real_run_validated` means a real dispatch and local validation completed through explicit flags and machine gates; queue completion and GitHub sync remain separate gated actions.
- Do not run real Codex without the explicit M152 flags and low-risk changed-path declarations.
- Do not apply source patches through AresForge from Codex output, call GitHub, push, merge, mutate workflows, complete queue items, retry automatically, or start follow-on work from this record.

## M151 End-to-End Codex Loop Dry Run Context

Status: Completed locally on `main` after validation.

Queue item: `m151-end-to-end-codex-loop-dry-run`.

M151 adds `run-end-to-end-codex-loop`, a dry-run-only coordinator that exercises the Codex loop from a local queue item through dispatch gating, synthetic dry-run Codex result capture, M136 validation-profile selection, dispatch evidence parsing, and queue completion recommendation.

Command:

- `python -m aresforge run-end-to-end-codex-loop --item-id m151-end-to-end-codex-loop-dry-run --dry-run --format json`

Agent-facing guidance:

- Treat M151 output as end-to-end dry-run evidence, not permission to run Codex or complete the queue.
- `status=dry_run_completed` means the required Codex dispatch dry-run gate passed and a local completion recommendation was generated.
- `completion_queue_gate_result` is advisory handoff evidence for future queue completion; dirty worktree state may block that downstream gate while M151 itself remains successful.
- M151 writes local artifacts only and reports `mutation_performed=false`, `external_execution_performed=false`, `model_execution_performed=false`, `codex_execution_performed=false`, `github_execution_performed=false`, and `patch_application_performed=false`.
- Do not run real Codex, call models, call GitHub, apply patches, mutate queue state, retry automatically, merge PRs, force push, mutate workflows, create releases, or start follow-on work from this dry-run record.

## M150 Machine-Gated Source Patch Apply Dry Run Context

Status: Completed locally on `main` after validation.

Queue item: `m150-machine-gated-source-patch-apply-dry-run`.

M150 adds `dry-run-source-patch-apply`, a local-only checker that proves whether a source patch currently passes `git apply --check` without applying it.

Command:

- `python -m aresforge dry-run-source-patch-apply --item-id m150-machine-gated-source-patch-apply-dry-run --patch-path artifacts/manual/sample-source.patch --format json`

Agent-facing guidance:

- Treat M150 output as applicability evidence, not permission to apply the patch.
- `status=dry_run_passed` means M149 apply planning, the source patch dry-run machine gate, and `git apply --check` passed.
- `patch_application_dry_run_performed=true` means only the clean apply check ran; `patch_application_performed=false` must remain true for M150.
- Do not run agents, Codex, local LLMs, GitHub, validation commands, real patch apply, queue completion, retries, PR merges, force pushes, workflow mutation, or next-item work from this dry-run record.

## M149 Controlled Source Patch Apply Plan Context

Status: Completed locally on `main` after validation.

Queue item: `m149-controlled-source-patch-apply-plan`.

M149 adds `plan-source-patch-apply`, a local-only planner that converts M148 source patch risk classification into an ordered future apply plan without applying the patch.

Command:

- `python -m aresforge plan-source-patch-apply --item-id m149-controlled-source-patch-apply-plan --patch-path artifacts/manual/sample-source.patch --format json`

Agent-facing guidance:

- Treat M149 output as planning and safety evidence, not permission to apply a patch.
- `controlled_apply_plan_available=true` means the patch has no hard apply blockers in the generated plan; it still requires a separate explicit future apply command, machine gate, clean apply check, operator review, and validation evidence.
- Workflow, protected config, queue-state, binary, executable-mode, and outside-repo patch operations are hard blockers for future controlled apply planning.
- Do not run agents, Codex, local LLMs, GitHub, validation commands, apply patches, mutate queue state, retry automatically, merge PRs, force push, mutate workflows, or start follow-on work from this planner.

## M148 Safe Source Patch Detection Context

Status: Completed locally on `main` after validation.

Queue item: `m148-safe-source-patch-detection-and-risk-classifier`.

M148 adds `classify-source-patch-risk`, a local-only classifier for unified source patches. It reports touched files, path classes, mutation types, risk level, blocked operations, and validation requirements without applying the patch.

Command:

- `python -m aresforge classify-source-patch-risk --patch-path artifacts/manual/sample-source.patch --format json`

Agent-facing guidance:

- Treat M148 output as planning and safety evidence, not permission to apply a patch.
- Source/code patches remain blocked from automatic application; use only separate explicit apply boundaries if a future milestone defines them.
- Workflow, protected config, queue-state, binary, executable-mode, and outside-repo patch operations require operator review and expanded validation.
- Do not run agents, Codex, local LLMs, GitHub, validation commands, apply patches, mutate queue state, retry automatically, merge PRs, force push, mutate workflows, or start follow-on work from this classifier.

## M147 Orchestrator Resume-from-Failure Context

Status: Completed locally on `main` after validation.

Queue item: `m147-orchestrator-resume-from-failure`.

M147 adds `inspect-orchestration-resume-plan`, a local-only inspector that reads orchestration history and source run artifacts to build a deterministic resume-from-failure plan from the last valid checkpoint.

Command:

- `python -m aresforge inspect-orchestration-resume-plan --run-id sample-run --format json`

Agent-facing guidance:

- Treat M147 output as resume planning evidence, not permission to resume automatically.
- `resume_eligible=true` only means a future explicit machine-gated orchestration command may resume from the reported checkpoint.
- Failed, blocked, mutating, Codex, GitHub, patch, queue-mutating, external-execution, or failed-gate runs require validation, classification, or operator review before any future resume.
- Do not run agents, Codex, local LLMs, GitHub, validation commands, apply patches, mutate queue state, retry automatically, merge PRs, force push, mutate workflows, or start follow-on work from this resume plan.

## M146 Agent Step Result Normalization Context

Status: Completed locally on `main` after validation.

Queue item: `m146-agent-step-result-normalization`.

M146 adds `normalize-agent-step-result`, a local-only normalizer that reads one agent step result artifact and returns a deterministic `agent_step_result_normalization_v1` record for orchestrator evaluation and recovery.

Command:

- `python -m aresforge normalize-agent-step-result --result-path artifacts/manual/sample-agent-step-result.json --format json`

Agent-facing guidance:

- Treat M146 output as normalized evidence, not permission to continue execution automatically.
- Top-level execution flags describe what the source step reported; `normalizer_execution_flags` describes the normalizer command and remains false for mutation, Codex, model, GitHub, validation, and patch execution.
- Completed non-mutating steps can inform the next explicit gated orchestration step.
- Failed, blocked, invalid, interrupted, mutation, Codex, GitHub, patch, or failed-gate results require separate recovery, validation, or operator review before completion or continuation.
- Do not run agents, Codex, local LLMs, GitHub, validation commands, apply patches, mutate queue state, retry automatically, merge PRs, force push, mutate workflows, or start follow-on work from this normalizer.

## M145 Codex Failure Classification and Retry Policy Context

Status: Completed locally on `main` after validation.

Queue item: `m145-codex-failure-classification-and-retry-policy`.

M145 adds `classify-codex-failure`, a local-only inspector that reads one failure artifact and returns deterministic failure classification plus retry/stop policy metadata.

Command:

- `python -m aresforge classify-codex-failure --failure-artifact artifacts/manual/sample-codex-failure.json --format json`

Agent-facing guidance:

- Treat M145 output as recovery policy evidence, not permission to retry.
- Automatic retry loops are prohibited.
- `process_timeout` and `process_nonzero` may report `manual_retry_capable`, but still require explicit operator action and the appropriate future machine-gated Codex command.
- Machine-gate, execution-denied, dirty-worktree, validation, evidence, interruption, artifact, and unknown failures stop until the reported recovery action is completed.
- Do not run Codex, call models, call GitHub, apply patches, mutate queue state, run validation commands, merge PRs, force push, mutate workflows, or start follow-on work from this classifier.

## M144 Codex Validation Profile Expansion Context

Status: Completed locally on `main` after validation.

Queue item: `m144-codex-validation-profile-expansion`.

M144 adds `inspect-codex-validation-profiles`, a local-only inspector for choosing Codex result validation profiles by task type, changed path class, and risk class.

Command:

- `python -m aresforge inspect-codex-validation-profiles --format json`

Agent-facing guidance:

- Treat M144 output as validation planning evidence, not permission to run validation commands.
- Use the selected profile only with a separate explicit M136 command after Codex output has been captured locally.
- High/critical/unknown risk, protected paths, workflow paths, mixed source/control-plane changes, Codex runtime changes, and orchestration changes require expanded validation.
- Do not run Codex, call models, call GitHub, apply generated patches, mutate queue state, merge PRs, force push, mutate workflows, or start follow-on work from this inspector.

## M143 Codex Execution Sandbox and Worktree Guard Context

Status: Completed locally on `main` after validation.

Queue item: `m143-codex-execution-sandbox-and-worktree-guard`.

M143 adds `inspect-codex-worktree-guard`, a local-only inspector for Codex execution sandbox policy, dirty-worktree state, preflight checks, and bounded output capture requirements.

Command:

- `python -m aresforge inspect-codex-worktree-guard --item-id m143-codex-execution-sandbox-and-worktree-guard --format json`

Agent-facing guidance:

- Treat M143 output as guard evidence, not execution permission.
- Real Codex execution remains disabled unless a separate explicit runner receives an allow flag and its machine gate passes.
- Dirty worktree state should block real Codex execution from being considered safe until reviewed or clean.
- Codex stdout, stderr, and result metadata must be captured to local artifacts before any M136 validation.
- Do not apply Codex-generated patches, call GitHub, merge PRs, force push, mutate workflows, complete queue items, or start follow-on work from this inspector.

## M142 Real Codex Execution Enablement Profile Context

Status: Completed locally on `main` after validation.

Queue item: `m142-real-codex-execution-enablement-profile`.

M142 adds `inspect-codex-execution-enablements`, a local-only profile inspector for real Codex execution readiness and default-deny behavior.

Command:

- `python -m aresforge inspect-codex-execution-enablements --format json`

Agent-facing guidance:

- Treat the M142 output as capability policy evidence, not execution permission.
- Real Codex execution remains disabled unless a separate existing runner receives an explicit allow flag and its machine gate passes.
- The default profile is `real_codex_default_deny`; it may inspect gates and policy but never invokes Codex.
- The only real Codex paths described are single prepared dispatch through `run-codex-dispatch --execution-enabled` and orchestrated Codex steps through `run-agent-orchestration --allow-codex`.
- Do not apply Codex-generated patches through M142, call GitHub, merge PRs, force push, mutate workflows, complete queue items, or start follow-on work.

## M141 Orchestration Run History and Recovery Context

Status: Completed locally on `main` after validation.

Queue item: `m141-orchestration-run-history-and-recovery`.

M141 adds `inspect-orchestration-run-history`, a local-only inspector for persisted orchestration run history and recovery records.

Command:

- `python -m aresforge inspect-orchestration-run-history --project-id aresforge --format json`

Agent-facing guidance:

- Treat `.aresforge/orchestrator/run_history.json` as the durable index for new explicit M138 orchestration runs.
- Treat legacy `artifacts/multi-agent-orchestration/**.json` files as read-only fallback history.
- Recovery records identify blocked, failed, interrupted, running, and max-step-limited runs; they do not authorize automatic retry, rollback, resume, queue mutation, or next-item execution.
- Real Codex, local LLM, GitHub, patch application, and queue mutation paths remain separate explicit gated commands.

## M140 Orchestrator Execution State Machine Context

Status: Completed locally on `main` after validation.

Queue item: `m140-orchestrator-execution-state-machine-v1`.

M140 adds `inspect-orchestrator-state-machine`, a read-only local inspector for the durable orchestration run state machine.

Command:

- `python -m aresforge inspect-orchestrator-state-machine --format json`

The command returns `orchestrator_execution_state_machine_v1` JSON with explicit states from `created` through `completed`, `blocked`, `failed`, and `cancelled`; allowed transitions; required checkpoints; validation boundaries; read-only machine-gate status; all execution/mutation flags set to false; and a next safe action.

Agent-facing guidance:

- Treat the M140 state machine as the contract for future resume, recovery, validation, and reporting.
- Do not treat M140 as permission to execute agents, Codex, local LLMs, GitHub, validation commands, patches, queue mutation, or automatic next-item work.
- Future executable transitions must pass their declared M131 machine gate before entering any execution state.
- Real Codex execution remains default-deny unless a separate explicit command supplies allow flags and passes gates.

## M139 Autonomous Sprint Closeout Context

Status: Completed locally on `main` after validation.

Queue item: `m139-autonomous-sprint-closeout-v1`.

M139 adds `generate-autonomous-sprint-closeout`, a local closeout generator for the M125-M139 agent foundation sprint.

Command:

- `python -m aresforge generate-autonomous-sprint-closeout --project-id aresforge --format json`

The command inspects queue state, agent registry metadata, machine gate status, orchestration availability, artifacts, transaction log entries, and source-of-truth doc consistency. It emits `autonomous_sprint_closeout_v1` JSON with completed/incomplete/blocked items, implemented capabilities, autonomy capabilities, remaining human gates, next sprint recommendations, warnings, blockers, and next safe action.

M125-M139 sprint summary:

- M125 defined the runtime boundary contract.
- M126 registered local agents.
- M127 added LLM decision policy records.
- M128 built non-executing orchestration plans.
- M129 added single-agent dry-run records.
- M130 allowed deterministic low-risk real local-agent records.
- M131 added machine safety gates.
- M132 allowed safe queue auto-completion from evidence and gates.
- M133 allowed docs-only Markdown patch apply behind machine gates.
- M134 allowed local Ollama advisory execution as non-applied evidence.
- M135 allowed explicit machine-gated Codex dispatch.
- M136 ingests Codex results and runs validation profiles.
- M137 performs dry-run-first narrow GitHub issue/PR sync.
- M138 runs gated multi-agent orchestration timelines.
- M139 reconciles the sprint and records the autonomy transition.

Agent-facing guidance:

- Treat machine gates as the replacement for human review only when every deterministic check passes.
- Low-risk local agents may run real local artifact/record execution through M130/M138 boundaries.
- Codex, local LLM, GitHub, docs patch apply, queue mutation, and orchestration remain explicit command paths with profile-specific gates.
- Do not infer permission to merge PRs, force push, mutate source from generated output, close issues automatically, run background workers, or start the next queue item.
- The recommended next sprint is hardening: orchestrator recovery, Codex loop reliability, model-quality comparison, GitHub automation expansion, Hub control center, rollback/recovery, telemetry, and self-managed issue automation.

## M138 Multi-Agent Orchestrator Context

Status: Completed locally on `main` after validation.

Queue item: `m138-multi-agent-orchestrator-v1`.

M138 introduces `run-agent-orchestration`, the first multi-agent runner. It consumes an explicit M128-style plan or builds one for a queue item, evaluates machine gates one step at a time, executes dry-run steps by default, records a timeline, stops on the first blocking failure, and writes a local orchestration result artifact.

Command:

- `python -m aresforge run-agent-orchestration --item-id <item_id> --format json`

M138 boundaries:

- default execution is dry-run
- real low-risk local-agent execution requires `--allow-low-risk-real`
- local LLM, Codex, and GitHub execution require `--allow-local-llm`, `--allow-codex`, or `--allow-github-sync`
- every attempted step must pass its machine safety gate before any step executor is called
- high-risk real steps remain blocked unless their explicit allow flag and gate evidence are present
- the orchestrator does not merge PRs, force push, bypass gates, complete queue items, start the next item, or continue after a failed required gate

## M137 GitHub Sync Agent Context

Status: Completed locally on `main` after validation.

Queue item: `m137-github-pr-issue-sync-agent`.

M137 introduces `run-github-sync-agent` for dry-run-first GitHub issue/PR metadata sync.

Command:

- `python -m aresforge run-github-sync-agent --item-id <item_id> --format json`

M137 boundaries:

- dry-run plans perform no GitHub operation
- live issue comments and PR comments require explicit `--github-enabled`
- live metadata fetch for issue/PR summary artifacts also requires `--github-enabled`
- every live GitHub path checks the `github_sync` machine gate before calling the mockable GitHub client
- local issue/PR metadata summary artifacts are allowed without live GitHub access
- PR merge, auto-merge, branch deletion, force push, PR approval, request-changes reviews, releases, protected branch updates, repository file writes, and automatic issue closure are blocked

## M136 Codex Result Ingestion Context

Status: Completed locally on `main` after validation.

Queue item: `m136-codex-result-ingestion-and-validation-runner`.

M136 introduces `ingest-codex-result-and-validate` as the local handoff after M135 Codex dispatch. It consumes one local Codex execution record, parses captured stdout/stderr/result artifacts into dispatch evidence, runs a selected local validation profile unless `--dry-run` is supplied, generates a queue completion recommendation, and evaluates the queue status mutation machine gate.

Command:

- `python -m aresforge ingest-codex-result-and-validate --item-id <item_id> --execution-record <path> --format json`

Profiles are `docs_only`, `code_unit_tests`, `hub_ui`, `queue_system`, and `full_local_safe`.

M136 boundaries:

- local validation commands are allowlisted by profile
- dry-run never runs validation commands
- generated evidence and recommendation do not complete queue items
- the runner does not push, call GitHub/`gh`, call remote services, execute Codex, auto-complete, or start follow-on work
- delegation to M132 remains a separate explicit operator decision

## M135 Codex Dispatch Executor v1 Context

Status: Completed locally on `main` after validation.

Queue item: `m135-codex-dispatch-executor-v1`.

M135 introduces `run-codex-dispatch` as an artifact-driven Codex dispatch executor. It consumes one prepared Codex dispatch artifact, evaluates the `codex_dispatch` machine gate profile, checks that the queue item is `ready`, verifies dependencies and required safety flags, then records stdout, stderr, and result metadata as local artifacts.

Command:

- `python -m aresforge run-codex-dispatch --item-id <item_id> --artifact-path <artifact_path> --format json`

M135 boundaries:

- default non-dry-run execution is blocked
- `--dry-run` performs no Codex invocation
- real execution requires `--execution-enabled` plus passing machine gates
- `--require-clean-worktree` adds an explicit clean-tree preflight
- the command may capture Codex output, but AresForge itself performs no patch application, GitHub execution, queue completion, push, or next-item execution
- any files Codex changes must be validated by M136 before completion evidence is accepted

## M134 Local LLM Advisory Execution Context

Status: Completed locally on `main` after validation.

Queue item: `m134-local-llm-advisory-execution`.

M134 introduces `run-local-llm-advisory` as an advisory-only local provider execution path. It consumes an existing local LLM advisory request artifact, evaluates the `local_llm_execution` machine gate profile, and may submit the prompt only to a configured local Ollama provider when gates and provider boundaries pass.

Command:

- `python -m aresforge run-local-llm-advisory --item-id <item_id> --artifact-path <artifact_path> --format json`

M134 boundaries:

- dry-run checks gates but does not call Ollama
- real execution writes a local response artifact and execution metadata only
- model output is advisory/manual-review-only and is never applied
- no source mutation, patch application, queue mutation, automatic completion, Codex execution, GitHub/`gh`, remote provider call, or next-item execution

## M133 Documentation Agent Autonomous Apply Context

Status: Completed locally on `main` after validation.

Queue item: `m133-documentation-agent-autonomous-apply-for-docs-only-patches`.

M133 introduces `apply-docs-only-patch` as the first documentation-agent autonomous apply surface. It may apply only UTF-8 unified patches whose targets are Markdown documentation files under `docs/` and whose `docs_only_patch_apply` machine gates pass.

Command:

- `python -m aresforge apply-docs-only-patch --item-id <item_id> --patch-path <patch_path> --format json`

Required safety checks:

- queue item exists and dependencies are satisfied
- patch path exists and parses to target files
- every target is an allowed docs Markdown path
- source, test, package/config, script, workflow, `.aresforge`, binary, and executable-mode changes are blocked
- `git apply --check` passes
- patch targets are not already dirty
- post-apply diff check remains docs-only
- non-dry-run success records a transaction-log entry

M133 boundaries:

- docs Markdown patch application only
- dry-run applies nothing
- no Codex, Codex CLI, Ollama/local LLM, remote LLM, GitHub, `gh`, network service, validation command execution, source-code mutation, test mutation, queue completion, automatic next-item execution, or external workflow behavior

## M132 Auto-Completion for Safe Queue Items Context

Status: Completed locally on `main` after validation.

Queue item: `m132-auto-completion-for-safe-queue-items`.

M132 introduces `auto-complete-safe-queue-item` as the first machine-gated path that may complete a local queue item without human review, but only for low-risk status mutation when deterministic evidence and the M131 `queue_status_mutation` gate pass.

Command:

- `python -m aresforge auto-complete-safe-queue-item --item-id <item_id> --format json`

Required conditions:

- item exists and is in an allowable completion status
- dependencies are satisfied and no blockers are present
- parsed dispatch evidence exists or can be found locally
- deterministic queue completion recommendation recommends completion
- tests and required smoke checks are reported as passed
- item is not high-risk or manual-only tagged
- `queue_status_mutation` machine gates pass
- transaction logging can record the mutation

M132 boundaries:

- local queue status mutation only
- no Codex, local LLM/Ollama, remote LLM, GitHub, `gh`, network service, validation command execution, patch application, external mutation, autonomous execution, or next-item execution
- blocked or risky items remain human-reviewed

## M124 Sprint Summary and Documentation Sync Closeout Context

Status: Completed locally on `main` after validation.

Queue item: `m124-sprint-summary-and-documentation-sync-closeout`.

M124 is the final M110-M124 sprint reconciliation. It adds no runtime feature and records that the sprint delivered local-only advisory/review contracts for local LLM request artifacts, patch proposal intake, dispatch evidence parsing, queue completion recommendations, Hub dispatch review, Ollama provider probing, documentation patch proposals, route recommendations, artifact registry indexing, batch sequencing, approval ledger review, queue transaction logging, and Hub controlled automation polish.

Agent-facing guidance:

- Treat M110-M124 outputs as planning, evidence, approval, or review artifacts only.
- Do not infer permission to execute Codex, Ollama/local LLMs, remote LLMs, agents, GitHub, network workflows, validation commands, or patch application.
- Queue completion remains a separate human decision with explicit evidence.
- Approval records unlock review/intake decisions only; they do not execute or apply anything.
- Artifact registry and transaction log outputs improve traceability but do not mutate external systems.

Recommended next-sprint direction:

- Continue with explicit machine gates, declarative agent capability checks, and local-only dry-run/low-risk executor records.
- Keep Codex dispatch, local LLM inference, GitHub sync, and patch application as separate future milestones with explicit operator approval.

## M131 Machine Safety Gate Engine Context

Status: Completed locally on `main` after validation.

Queue item: `m131-machine-safety-gate-engine`.

M131 introduces `evaluate-machine-safety-gates` as the deterministic replacement path for human review before future queue mutation, docs patch application, Codex dispatch, GitHub sync, local LLM execution, or multi-agent orchestration.

Command:

- `python -m aresforge evaluate-machine-safety-gates --item-id <item_id> --gate-profile <profile> --format json`

Profiles are `read_only_agent`, `local_artifact_write`, `queue_status_mutation`, `docs_only_patch_apply`, `local_llm_execution`, `codex_dispatch`, `github_sync`, and `multi_agent_orchestration`.

Every gate record reports `gate_result_type=machine_safety_gate_evaluation`, blocked reasons, warnings, per-check results, required next steps, autonomy allowance, human-review requirement, `machine_gate_version`, `local_only=true`, `execution_performed=false`, and `mutation_performed=false`.

M131 boundaries:

- evaluates gates only
- no agents, Codex, local LLM/Ollama, remote LLM, GitHub, `gh`, network service, validation command execution, patch application, queue mutation, external mutation, autonomous execution, or next-item execution
- future workflows may remove human review only when the profile passes and the next action is still separately explicit

## M123 Hub Controlled Automation Workspace Polish Context

Status: Completed locally on `main` after validation.

Queue item: `m123-hub-controlled-automation-workspace-polish`.

M123 improves Hub clarity for the controlled automation workspace. It adds a visible Queue-panel summary that labels the workspace `local-only`, `advisory`, `operator-gated`, `no automatic execution`, `no patch application`, and `no network or GitHub calls`.

The polish improves wording and empty states for queue review, dispatch artifacts, approval/ledger review, parsed evidence, completion recommendations, artifact registry discovery, and route recommendations.

M123 boundaries:

- Hub UI polish and static test coverage only
- no new execution capability
- no Codex, Codex CLI, Ollama/local LLMs, remote LLMs, agents, GitHub API, `gh`, network services, validation command execution, patch application, queue automation, autonomous execution, or next-item execution

## M122 Safe Queue Mutation Transaction Log Context

Status: Completed locally on `main` after validation.

Queue item: `m122-safe-queue-mutation-transaction-log`.

M122 adds `.aresforge/queue/transaction_log.json` as a local audit trail for file-backed queue mutations and `inspect-queue-transaction-log` for read-only inspection.

The log records successful local queue item proposal/update, routing metadata update, start, validation evidence capture, explicit completion, and closeout mutations where practical. Records include timestamp, item id, project id, previous status, new status, mutation type, actor/source, evidence summary, reason, queue path, `local_only=true`, and `execution_allowed=false`.

M122 boundaries:

- append-only local metadata for explicit queue mutations
- inspection does not mutate queue state
- append failures are surfaced as warnings and do not break existing queue behavior
- no Codex, Codex CLI, Ollama/local LLMs, remote LLMs, agents, GitHub API, `gh`, network services, validation command execution, patch application, source mutation beyond the requested queue write, external mutation, autonomous execution, or next-item execution

## M130 Single-Agent Real Executor Context

Status: Completed locally on `main` after validation.

Queue item: `m130-single-agent-real-executor-for-low-risk-agents`.

M130 introduces `run-agent` as the first real execution path for machine-restricted local agents only.

Command:

- `python -m aresforge run-agent --agent-id <agent_id> --item-id <item_id> --format json`

Allowed real agents are `artifact-registry-agent`, `evidence-parser-agent`, `completion-recommendation-agent`, `validation-agent`, `queue-planner-agent`, and `sprint-summary-agent`.

Every record reports `execution_record_type=single_agent_real_execution`, `dry_run=false`, `real_execution=true`, checked machine gates, local execution artifacts, blocked forbidden capabilities, no external/model/GitHub/patch execution, and `local_only=true`.

M130 boundaries:

- local deterministic single-agent execution only
- writes only local execution records and local artifact files
- no Codex, Codex CLI, Ollama/local LLMs, remote LLMs, GitHub API, `gh`, network services, validation command execution, source-code mutation, documentation patch application, patch application, queue completion, autonomous execution, or next-item execution
- high-risk agents and any agent requiring network, model execution, GitHub execution, or patch application remain blocked

## M121 Human Approval Inventory and Review Ledger Context

Status: In progress locally on `main`.

Queue item: `m121-human-approval-inventory-and-review-ledger`.

M121 adds `inspect-approval-ledger` and `record-artifact-review` for local artifact review inventory. The ledger combines dispatch artifact registry entries, existing dispatch approval gate decisions, and explicit operator-recorded review decisions.

Ledger output includes `human_approval_review_ledger`, reviewed/unreviewed artifacts, approved/rejected/needs-changes artifacts, review records, approval gaps, `local_only=true`, `execution_allowed=false`, and next safe action.

M121 boundaries:

- local review metadata only
- no automatic approval
- no queue item start or completion
- no Codex, agents, Ollama/local LLMs, remote LLMs, GitHub, `gh`, network services, validation command execution, patch application, source mutation from review, external mutation, autonomous execution, or next-item execution

## M120 Operator Batch Queue Sequencer v2 Context

Status: In progress locally on `main`.

Queue item: `m120-operator-batch-queue-sequencer-v2`.

M120 adds `python -m aresforge plan-operator-batch-v2 --project-id aresforge --format json` for advisory batch sequencing. The command reads local queue state, the local dispatch artifact registry, and local approval gate metadata to recommend an ordered sequence with prerequisites.

The sequencer reports `operator_batch_sequence_v2`, proposed and blocked counts, recommended sequence, dependency warnings, approval warnings, artifact warnings, lane grouping, operator checklist, `execution_performed=false`, `queue_mutation_performed=false`, `local_only=true`, `execution_allowed=false`, and next safe action.

M120 boundaries:

- local planning only
- optional local output write only with no-overwrite safeguards
- no queue item start, agents, Codex, Ollama/local LLMs, remote LLMs, GitHub, `gh`, network services, validation command execution, patch application, queue mutation, external mutation, automatic completion, autonomous execution, or next-item execution

## M119 Dispatch Artifact Registry Index v2 Context

Status: In progress locally on `main`.

Queue item: `m119-dispatch-artifact-registry-index-v2`.

M119 adds a local-only artifact registry index:

- `python -m aresforge inspect-artifact-registry --format json`
- optional `--project-id`, `--item-id`, `--artifact-type`, `--output`, and `--force`

The registry inventories local artifacts from manual Codex dispatch preparation, Codex prompt artifacts, local LLM advisory requests, patch intake, dispatch result evidence, completion recommendations, documentation patch proposals, and agent route recommendations.

M119 boundaries:

- registry/index only
- `local_only=true`
- `execution_allowed=false`
- no Codex, Ollama, local LLM, agent runtime, GitHub API, `gh`, network service, patch application, source mutation, queue mutation, automatic completion, or next-item execution

## M129 Single-Agent Dry-Run Executor Context

Status: Completed locally on `main` after validation.

Queue item: `m129-single-agent-dry-run-executor`.

M129 introduces `run-agent-dry-run` as the first actual agent-shaped execution path, but only for deterministic local dry-run records.

Command:

- `python -m aresforge run-agent-dry-run --agent-id <agent_id> --item-id <item_id> --format json`

Supported dry-run agents are `artifact-registry-agent`, `evidence-parser-agent`, `completion-recommendation-agent`, `validation-agent`, `sprint-summary-agent`, and `queue-planner-agent`.

Every record reports `execution_record_type=single_agent_dry_run`, `dry_run=true`, `real_execution=false`, blocked forbidden capabilities, no external/model/GitHub/patch execution, and `local_only=true`.

M129 boundaries:

- deterministic local dry-run inspection, validation planning, summarization, and optional execution-record artifact writing only
- no Codex, Codex CLI, Ollama, local LLM, remote LLM, GitHub API, `gh`, network services, validation command execution, patch application, source mutation, queue mutation from the dry-run, autonomous execution, or next-item execution
- unsupported agents block before any agent-specific output is considered

## M118 Post-Automation Planning Reconciliation Context

Status: In progress locally on `main`.

Queue item: `m118-post-automation-planning-reconciliation`.

M118 is a docs/data reconciliation milestone after M110-M117. It aligns source-of-truth docs, roadmap notes, operator instructions, architecture boundaries, and queue state for the controlled automation planning layer.

M110-M117 current capabilities:

- M110 generates local LLM advisory request artifacts without invoking local models.
- M111 records approval-gated patch proposal intake metadata without applying patches.
- M112 parses human-pasted Codex result text into local evidence records without executing Codex.
- M113 recommends queue completion decisions without mutating queue state.
- M114 displays dispatch review artifacts in the Hub without execution endpoints.
- M115 probes only local Ollama configuration or loopback `/api/tags` metadata without prompts or inference.
- M116 generates documentation patch proposals for review without applying them.
- M117 recommends an advisory route lane in CLI/API/Hub without dispatch.

M118 boundaries:

- docs/data only
- no new runtime features
- no Codex, Ollama, local LLM, agent, GitHub API, `gh`, network service, patch application, source mutation beyond this operator-authored docs reconciliation, automatic completion, or next-item execution
- any future execution runner must be a separate explicit milestone with human approval requirements

## M117 Agent Routing Decision Dashboard Context

Status: In progress locally on `main`.

Queue item: `m117-agent-routing-decision-dashboard`.

M117 adds a local-only agent route recommendation command and Hub panel:

- `python -m aresforge recommend-agent-route --item-id <item_id>`
- `python -m aresforge recommend-agent-route --item-id <item_id> --format json`
- optional `--output` and `--force`
- `GET /api/agent-route-recommendation?item_id=<item_id>`
- Queue panel Agent Routing Decision Dashboard

The recommendation reads local queue metadata only and reports `recommendation_type=agent_route_recommendation`, recommended lane, alternatives, routing reasons, required artifacts before dispatch, approval requirements, suitability flags, `human_operator_required=true`, `dispatch_performed=false`, `execution_allowed=false`, and `local_only=true`.

M117 boundaries:

- recommendation and dashboard display only
- no execute buttons
- no Codex, local LLM, Ollama, agent runtime, GitHub API, `gh`, network service, patch application, source mutation, queue mutation, approval mutation, automatic handoff, or next-item execution

## M128 Agent Orchestration Plan Builder Context

Status: Completed locally on `main` after validation.

Queue item: `m128-agent-orchestration-plan-builder`.

M128 adds a local-only orchestration plan builder:

- `python -m aresforge build-agent-orchestration-plan --item-id <item_id> --format json`
- optional `--agent-id`, `--execution-target dry-run|real`, `--output`, and `--force`

The builder converts a queue item into ordered agent steps. It combines queue metadata, the M126 agent registry, and the M127 LLM decision policy into an `agent_orchestration_plan` with required artifacts, dependency checks, machine gates, blocked reasons, and next safe action.

M128 boundaries:

- plan builder only
- `execution_performed=false`
- real execution target requests are blocked and recommend `dry-run`
- no agents, Codex, Ollama/local LLMs, remote LLMs, GitHub, `gh`, network services, validation commands, patch application, source mutation, queue mutation from the plan, autonomous execution, or next-item execution

## M127 LLM Decision Policy v1 Context

Status: Completed locally on `main` after validation.

Queue item: `m127-llm-decision-policy-v1`.

M127 adds a local-only LLM decision policy:

- `python -m aresforge recommend-llm-decision --item-id <item_id> --format json`
- optional `--agent-id`, `--task-type`, `--risk-level`, `--mutation-scope`, `--output`, and `--force`

The policy recommends one of: `no_llm_required`, `local_llm_reasoning`, `local_llm_coding_review`, `codex_coding`, `codex_reasoning`, `remote_high_value_reasoning`, `remote_low_cost_reasoning`, `documentation_agent`, `validation_agent`, or `github_sync_agent`.

Recommendation inputs include queue item type, risk level, mutation requirement, code/docs/planning shape, context size, repo-aware coding need, deterministic validation need, local-only requirement, GitHub/network requirement, test verifiability, agent id, and autonomous execution hints.

M127 boundaries:

- recommendation only
- `execution_performed=false`
- no Codex, local LLM, remote LLM, Ollama, agent runtime, GitHub API, `gh`, network service, patch application, validation execution, source mutation, queue mutation, autonomous execution, or next-item execution
- future autonomous execution hints do not authorize execution

## M116 Documentation Agent Patch Proposal Generator Context

Status: Completed locally on `main` after validation.

Queue item: `m116-documentation-agent-patch-proposal-generator`.

Implementation commit: `0d8bbdf`.

M116 adds a local-only documentation patch proposal command:

- `python -m aresforge generate-doc-agent-patch-proposal --item-id <item_id>`
- `python -m aresforge generate-doc-agent-patch-proposal --item-id <item_id> --format json`
- optional `--output`, `--force`, `--include-roadmap`, `--include-context`, and `--include-operator-docs`

The command reads local queue state and selected source-of-truth docs, detects documentation gaps, writes a structured `documentation_agent_patch_proposal` artifact, and writes a proposed patch text artifact for operator review.

M116 boundaries:

- generated patch proposals are not applied
- `approval_required=true`
- `patch_application_allowed=false`
- `patch_application_performed=false`
- no documentation-agent runtime, Codex, local LLM, Ollama, GitHub API, `gh`, network service, source mutation, queue mutation, approval mutation, patch application, or next-item execution

## M115 Local Ollama Provider Probe Integration Context

Status: Completed locally on `main` after validation.

Queue item: `m115-local-ollama-provider-probe-integration`.

Implementation commit: `9913605`.

M115 adds a local-only Ollama provider probe:

- `python -m aresforge probe-local-ollama-provider`
- `python -m aresforge probe-local-ollama-provider --format json`
- optional `--output`, `--force`, `--no-network`, and `--config`

The probe reports `probe_type=local_ollama_provider_probe`, configured local model profiles, optional visible model metadata from the loopback `/api/tags` endpoint, coding/reasoning profile recommendation metadata, and explicit non-execution flags.

M115 boundaries:

- configuration-only when `--no-network` is supplied
- loopback `/api/tags` only when network probing is allowed
- non-loopback provider URLs block network probing
- no prompts, generation, chat, completion, coding, reasoning, advisory execution, Codex execution, GitHub API, `gh`, agent execution, patch application, repository mutation, queue mutation, workflow behavior, or next-item execution

## M114 Hub Dispatch Review Panel Context

Status: Completed locally on `main` after validation.

Queue item: `m114-hub-dispatch-review-panel`.

Implementation commit: `d5ffb6b`.

M114 adds a read-only Hub dispatch review surface:

- `GET /api/dispatch-review`
- Queue panel Dispatch Review section

The panel normalizes local review records for:

- manual dispatch preparation
- local LLM advisory request artifacts
- patch proposal intake records
- dispatch result evidence
- queue completion recommendations

Each normalized record exposes item id, title, project id, milestone, artifact type, artifact path, blocked status, blocked reasons, status, next safe action, and operator checklist entries. The API and UI preserve `local_only=true`, `read_only=true`, `execution_allowed=false`, `queue_mutation_performed=false`, and `patch_application_allowed=false`.

M114 boundaries:

- no execution endpoints
- no Codex execution
- no Codex CLI shell-out
- no local LLM or Ollama invocation
- no documentation-agent runtime, GitHub API, `gh`, network service, external-agent, workflow, issue, PR, or patch application behavior
- no queue completion, approval mutation, automatic handoff, or next-item execution

## M126 Agent Registry Context

Status: Completed locally on `main` after validation.

Queue item: `m126-agent-registry`.

Implementation commit: pending final commit.

M126 adds a local-only declarative registry inspector:

- `python -m aresforge inspect-agent-registry --format json`
- `python -m aresforge inspect-agent-registry --agent-id documentation-agent --format json`
- optional `--safety-class`, `--autonomy-level`, `--output`, and `--force`

The registry defines the initial known AresForge agents: queue planner, Codex dispatch, local LLM advisory, documentation, evidence parser, completion recommendation, validation, GitHub sync, sprint summary, artifact registry, approval ledger, and transaction log.

Each agent record declares identity, type, supported item types, inputs, outputs, allowed and forbidden capabilities, mutation/network/model scopes, safety class, autonomy level, default execution mode, dry-run/real-run eligibility, machine gate requirement, evidence requirements, and source docs.

M126 boundaries:

- local-only registry inspection
- `execution_performed=false`
- no agents are executed
- `can_run_real=false` for every registered agent until a future explicit operator-approved runner exists
- no Codex, Ollama, local LLM, documentation-agent apply mode, GitHub API, `gh`, network service, patch application, autonomous workflow, or next-item execution is introduced

## M113 Queue Item Auto-Completion Recommendation Context

Status: Completed locally on `main` after validation.

Queue item: `m113-queue-item-auto-completion-recommendation-engine`.

Implementation commit: `a988af7`.

M113 adds a local-only queue completion recommendation command:

- `python -m aresforge recommend-queue-completion --item-id <item_id> --evidence-path <path>`
- `python -m aresforge recommend-queue-completion --item-id <item_id> --evidence-path <path> --format json`
- optional `--output`, `--force`, and `--queue-path`

The command reads a local M112 `dispatch_result_evidence` JSON record and local queue metadata. It recommends whether a human operator may safely complete the item, but it never completes the queue item itself.

The recommendation checks:

- evidence record type and item id match
- evidence parsed successfully and is not blocked
- evidence confirms `local_only=true`, `execution_allowed=false`, and `human_review_required=true`
- files changed and change summary are present
- tests and smoke checks are reported as passed
- warnings or blockers do not indicate severe failure
- commit hash evidence is present
- queue `completion_requires` and `evidence_required` entries are satisfied when present

M113 boundaries:

- no queue mutation or automatic completion
- no Codex execution
- no Codex CLI shell-out
- no local LLM, Ollama, documentation-agent, GitHub API, `gh`, network service, external-agent, workflow, issue, PR, or patch application behavior
- no approval mutation, handoff automation, or next-item execution

M113 output is advisory only. A human operator must still run the explicit queue completion command with validation evidence.

## M125 Agent Runtime Boundary Contract Context

Status: Completed locally on `main` after validation.

Queue item: `m125-agent-runtime-boundary-contract`.

Implementation commit: pending final commit.

M125 adds a local-only runtime boundary inspector:

- `python -m aresforge inspect-agent-runtime-boundary`
- `python -m aresforge inspect-agent-runtime-boundary --format json`

The contract defines what an AresForge agent is before real execution exists. An agent is a declared local control-plane actor with a stable `agent_id`, `agent_type`, `execution_mode`, bounded inputs, declared outputs, explicit capability catalogs, scoped side effects, evidence requirements, runtime limits, safety class, and autonomy level.

M125 schema terms:

- `agent_id`
- `agent_type`
- `execution_mode`
- `input_contract`
- `output_contract`
- `allowed_capabilities`
- `forbidden_capabilities`
- `mutation_scope`
- `network_scope`
- `model_scope`
- `timeout_policy`
- `retry_policy`
- `evidence_requirements`
- `safety_class`
- `autonomy_level`

Supported autonomy levels:

- `manual_only`
- `recommendation_only`
- `operator_approved_single_step`
- `operator_approved_bounded_run`

Supported safety classes:

- `read_only`
- `local_file_write`
- `local_provider_probe`
- `operator_gated_local_provider_execution`
- `external_mutation_prohibited`

M125 boundaries:

- boundary inspection is local-only and read-only
- `execution_performed=false`
- no real agent execution is introduced
- no Codex, Ollama, local LLM, documentation-agent, GitHub API, `gh`, network service, patch application, workflow, daemon, watcher, scheduler, or external-agent execution
- future runtime execution requires a separate explicit operator-approved milestone

## M112 Dispatch Result Evidence Parser Context

Status: Completed locally on `main` after validation.

Queue item: `m112-dispatch-result-evidence-parser`.

Implementation commit: `5088c95`.

M112 adds a local-only evidence parser:

- `python -m aresforge parse-dispatch-result-evidence --item-id <item_id> --result-path <path>`
- `python -m aresforge parse-dispatch-result-evidence --item-id <item_id> --result-path <path> --format json`
- optional `--output`, `--force`, and `--queue-path`

The command reads a human-pasted Codex result text or markdown file and emits structured `dispatch_result_evidence`. It extracts common completion sections for files changed, change summary, tests, smoke checks, warnings/blockers, and commit hash. Missing sections become warning entries rather than crashes.

M112 boundaries:

- no Codex execution
- no Codex CLI shell-out
- no local LLM, Ollama, documentation-agent, GitHub API, `gh`, network service, external-agent, workflow, issue, PR, or patch application behavior
- no repository mutation from parsed result content
- no queue completion, approval mutation, automatic handoff, or next-item execution

M112 evidence is advisory and always requires human review before any queue completion decision.

## M111 Approval-Gated Patch Intake Contract Context

Status: Completed locally on `main` after validation.

Queue item: `m111-approval-gated-patch-intake-contract`.

Implementation commit: `98ec90c`.

M111 adds a local-only patch proposal intake command:

- `python -m aresforge intake-patch-proposal --item-id <item_id> --patch-artifact <path>`
- `python -m aresforge intake-patch-proposal --item-id <item_id> --patch-artifact <path> --format json`
- optional `--approval-id`, `--output`, and `--force`

The command validates a queue item, a local patch artifact path, and an M101 approval gate. A patch proposal is accepted for review only when the approval gate is `approved_for_manual_handoff`. The intake record includes patch summary metadata and always reports `operator_review_required=true`, `patch_application_allowed=false`, `patch_application_performed=false`, `local_only=true`, and `execution_allowed=false`.

M111 blocked behavior:

- missing item, missing patch artifact, missing approval, rejected approval, pending approval, and needs-revision approval block intake
- existing output files block unless `--force` is explicit

M111 boundaries:

- no patch application
- no repository file mutation
- no Codex, Codex CLI, local LLM, documentation-agent, or external-agent execution
- no GitHub API, `gh`, network, issue, PR, or workflow behavior
- no queue mutation, approval mutation, automatic handoff, completion, or next-item execution

M111 does not authorize applying a patch. It records patch proposal review metadata only.

## M110 Local LLM Advisory Artifact Generator Context

Status: Completed locally on `main` after validation.

Queue item: `m110-local-llm-advisory-artifact-generator`.

Implementation commit: `f4e81ff`.

M110 adds a local-only advisory request artifact command:

- `python -m aresforge generate-local-llm-advisory-artifact --item-id <item_id>`
- `python -m aresforge generate-local-llm-advisory-artifact --item-id <item_id> --format json`
- optional `--output`, `--force`, `--model-profile`, and `--reasoning-scope`

The command consumes current queue state and the M97 dispatch plan. It generates a JSON request artifact under `artifacts/local_llm_advisory/requests` by default, or at the operator-provided output path. The artifact describes what a future local reasoning model would be asked to review, including source documents, queue context, advisory prompt, expected response shape, and operator checklist.

M110 ready behavior:

- requires `selected_lane=local_llm_advisory`
- requires `local_only=true`
- requires `execution_allowed=false`
- requires no M97 plan blockers
- refuses to overwrite explicit output files unless `--force` is provided

M110 blocked behavior:

- blocks non-advisory lanes, blocked dispatch plans, unsafe plan flags, and no-overwrite conflicts
- still emits blocked reasons, next safe action, and execution-denial flags

M110 boundaries:

- no Ollama or local model execution
- no Codex execution or Codex CLI shell-out
- no GitHub API, `gh`, network, documentation-agent, or external-agent calls
- no patch application
- no queue mutation, approval mutation, automatic handoff, completion, or next-item execution

M110 does not authorize advisory execution. Any later local LLM invocation requires a separate operator-approved milestone and evidence gate.

## M109 Manual Codex Dispatch Runner Contract Context

Status: Completed locally on `main` after validation.

Queue item: `m109-manual-codex-dispatch-runner-contract`.

Implementation commit: `bfa4139`.

M109 adds a local-only manual dispatch preparation command:

- `python -m aresforge prepare-manual-codex-dispatch --item-id <item_id>`
- `python -m aresforge prepare-manual-codex-dispatch --item-id <item_id> --format json`
- optional `--artifact-path`, `--approval-id`, `--output`, and `--force`

The command consumes current queue state, the M97 dispatch plan, the M98 Codex prompt artifact, M101 approval gate status, and M106 artifact index data when available. It produces a dispatch run preparation record only.

M109 ready behavior:

- requires `selected_lane=codex_prompt_artifact`
- requires `local_only=true`
- requires `execution_allowed=false`
- requires a present Codex prompt artifact
- requires approval status `approved_for_manual_handoff`
- requires the queue item to be lifecycle-safe and not done or blocked

M109 blocked behavior:

- blocks non-Codex lanes, missing artifacts, missing approval gates, non-approved gates, done/blocked queue items, non-local plans/artifacts, and any source plan/artifact that allows execution
- represents missing approval as a blocked `needs_approval` state

M109 boundaries:

- no Codex execution
- no Codex CLI shell-out
- no GitHub API, `gh`, network, Ollama/local LLM, documentation-agent, or external-agent calls
- no patch application
- no queue mutation, approval mutation, automatic handoff, or next-item execution

After the operator manually runs Codex outside AresForge, expected evidence includes the transcript or summary, proposed file changes, any patch/diff artifact, validation output, operator notes, and future M111 patch-intake approval evidence.

M110 is now the completed local LLM advisory artifact generator milestone. M111 remains the approval-gated patch intake contract for returned manual Codex results.

## M108 Sprint Closeout and Next-Stage Automation Plan Context

Status: Completed locally on `main` after validation.

Queue item: `m105-post-batch-documentation-reconciliation-m108-sprint-closeout-and-next-stage-automation-plan`.

Implementation commit: `549c5fc`.

M108 is a docs/data closeout pass for the completed M99-M107 dispatch-preparation sprint. It used the local project report, queue summary, project queue report, operator batch plan, dispatch artifact index, safe dispatch handoff, and standard handoff package as evidence. It did not add runtime features.

Current closeout findings:

- M99-M107 are complete in the local queue.
- M108 is complete.
- M96 remains proposed as older planning context.
- The local queue has no blocked items.
- The operator batch planner proposes M96 as the only remaining non-done plannable item when M108 is not active.
- The dispatch artifact index is empty because default dispatch artifact folders are not present yet.
- The safe dispatch handoff reports queue, dispatch plan, artifact index, approval status, warnings, and operator next actions with `execution_allowed=false`.
- Persistent local warning noise remains from untracked `.codex-pytest-cache/` and inaccessible old pytest temp directories.

Next-stage automation should stay controlled and manual-gated:

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

M108 boundaries:

- docs/data-only reconciliation
- no Codex, local LLM, Ollama, documentation-agent, GitHub API, `gh`, network service, external-agent, patch, or automated dispatch execution
- no automatic queue start, completion, next-item execution, artifact execution, or approval mutation
- no seeding of the entire next-stage batch

## M107 Safe Dispatch Handoff Package Context

Status: Completed locally on `main` after validation.

Queue item: `m105-post-batch-documentation-reconciliation-m107-safe-dispatch-handoff-package`.

Implementation commit: `99c79b7`.

M107 adds a local-only safe dispatch handoff command:

- `python -m aresforge generate-safe-dispatch-handoff`
- `python -m aresforge generate-safe-dispatch-handoff --format json`
- optional `--output <path>` and `--force`

The package bundles queue state, active project identity, branch/HEAD, next recommended queue items, dispatch plan summaries, M106 artifact index summary, M101 approval gate summary, warnings/blockers, manual approval requirements, and operator next actions.

M107 boundaries:

- local-only/read-only by default
- optional output writes one local file only and refuses overwrite unless `--force`
- no artifact execution, Codex execution, local LLM/Ollama invocation, documentation-agent execution, GitHub API, `gh`, network service, external-agent, patch, automatic handoff, or queue/approval mutation
- `execution_allowed` remains false

M108 should use the M107 package as sprint closeout context, not as execution authorization.

## M106 Dispatch Artifact Index/Report Context

Status: Completed locally on `main` after validation.

Queue item: `m105-post-batch-documentation-reconciliation-m106-dispatch-artifact-index-report`.

Implementation commit: `fc77cd2`.

M106 adds a read-only local report for dispatch artifacts and dry-run outputs:

- `python -m aresforge inspect-dispatch-artifacts`
- `python -m aresforge inspect-dispatch-artifacts --format json`
- optional `--project-id`, `--artifact-root`, and `--approval-path`

The report scans known local artifact locations created by M98-M100 workflows:

- Codex prompt dispatch artifacts
- Local LLM advisory dry-run outputs
- Documentation-agent dry-run outputs

It joins local approval gate status from `.aresforge/dispatch_approval_gates.json` when a matching item/artifact record exists.

M106 boundaries:

- local-only/read-only inspection
- no artifact execution or dispatch
- no Codex, local LLM, Ollama, documentation-agent, GitHub API, `gh`, network service, external-agent, patch, or automatic handoff
- `execution_allowed` remains false for the report and every artifact entry

M107 should consume this index as a pre-handoff visibility report, not as execution authorization.

## M105 Post-Batch Documentation Reconciliation Context

Status: Completed locally on `main` after validation.

Queue item: `m96-post-sprint-planning-and-prioritization-m105-post-batch-documentation-reconciliation`.

Implementation commit: `962ac8c`.

M105 is a docs/data reconciliation pass for the completed M99-M104 operator workflow batch. It does not add runtime features.

Current post-batch state:

- M99 through M104 are completed in the local queue.
- M96 remains `proposed` as older planning context.
- The operator batch planner currently proposes M96 as the only non-done plannable item.
- Local project report and queue summary are ready with no queue blockers.
- `generate-handoff-package` is safe/read-only and shows the latest M104 commits plus persistent local warning noise.

M105 reconciliation targets:

- `docs/context/BUILD_STATE.md`
- `docs/context/AGENT_CONTEXT.md`
- `docs/roadmap/ROADMAP.md`
- `docs/operator/LOCAL_OPERATOR_USAGE.md`
- `docs/architecture/RUNNABLE_SKELETON.md`
- `docs/architecture/AGENT_LLM_ROUTING_STRATEGY.md`
- `docs/architecture/LOCAL_LLM_ENVIRONMENT_CONTRACT.md`
- `docs/architecture/DOCUMENTATION_AGENT_CONTRACT.md`

M105 boundaries:

- docs/data-only reconciliation
- no new operator runtime feature implementation
- no Codex, local LLM, Ollama, documentation-agent, GitHub API, `gh`, network service, external-agent, patch, or automatic dispatch execution
- no automatic documentation mutation from model output
- no automatic queue start, completion, or next-item execution

Warnings to keep visible:

- `.codex-pytest-cache/` remains untracked after local pytest runs.
- `git status` still reports permission warnings for old local pytest temp directories under `.codex-tmp` and `.tmp*`.
- Recovered M80 dispatch runs remain audited as non-blocking warnings.

Next recommended sequence after M105:

- M106 Dispatch Artifact Index/Report
- M107 Safe Dispatch Handoff Package
- M108 Sprint Closeout and Next-Stage Automation Plan
- M109 Manual Codex Dispatch Runner Contract
- M110 Local LLM Advisory Artifact Generator
- M111 Approval-Gated Patch Intake Contract

## M104 Operator Batch Planner v1 Context

Status: Completed locally on `main` after validation.

Queue item: `m104-operator-batch-planner-v1`.

Implementation commit: `864af13`.

M104 adds a read-only local batch planner:

- `python -m aresforge plan-operator-batch --project-id aresforge`
- `python -m aresforge plan-operator-batch --project-id aresforge --limit 10`
- `python -m aresforge plan-operator-batch --project-id aresforge --limit 10 --format json`

The planner reads the local queue and proposes an ordered sprint batch. It excludes `done` items, respects blocked statuses, blocks unresolved dependencies, and allows a dependency to be satisfied by an earlier item in the same proposed batch.

Per-item safety classifications:

- `manual_only`
- `codex_artifact_possible`
- `local_llm_dry_run_possible`
- `documentation_dry_run_possible`
- `blocked`

M104 boundaries:

- local-only/read-only inspection
- no queue mutation or automatic seeding
- no Codex, local LLM, Ollama, documentation-agent, GitHub API, `gh`, network service, external-agent, patch, or automatic dispatch execution
- `execution_allowed` remains false at the batch and item level

M105 consumes planned batch output, completed queue evidence, and report warnings as a documentation/data reconciliation workflow rather than treating M104 as an execution workflow.

## M103 AresForge Self-Managed Project Seed Review Context

Status: Completed locally on `main` after validation.

Queue item: `m103-aresforge-self-managed-project-seed-review`.

Implementation commit: `f1b32ca`.

M103 adds a read-only self-managed project review command:

- `python -m aresforge inspect-self-managed-project --project-id aresforge`
- `python -m aresforge inspect-self-managed-project --project-id aresforge --format json`

The report confirms AresForge as its own first managed project:

- active project identity
- managed registry project and primary repo metadata
- repo path and current local branch
- roadmap active milestone marker
- queue counts and next recommended item
- source-of-truth doc presence
- warnings, blockers, and gaps
- explicit unsafe execution assumptions set to false

M103 boundaries:

- local-only/read-only inspection
- no queue mutation
- no registry mutation
- no Codex, local LLM, Ollama, documentation-agent, GitHub API, `gh`, network service, external-agent, patch, or automatic dispatch execution

M104 is now complete and uses the M103 self-managed review posture before proposing batches.

## M102 Queue Dependency and Completion Locking Context

Status: Completed locally on `main` after validation.

Queue item: `m102-queue-dependency-and-completion-locking-hardening`.

Implementation commit: `ea1d719`.

M102 hardens local queue sequencing and evidence locks:

- queue items may use `dependencies` or `depends_on` for prerequisite items
- queue items may use `blocked_by` for explicit local blockers
- queue items may use `completion_requires` and `evidence_required` for extra completion evidence requirements
- starts are blocked when dependencies or blockers are unresolved
- completions are blocked when dependencies are unresolved or explicit evidence is missing
- `inspect-queue-consistency` exposes dependency and completion lock status without mutating the queue

Primary command:

- `python -m aresforge inspect-queue-consistency --project-id aresforge [--format json|markdown]`

M102 boundaries:

- local-only queue inspection and lifecycle mutation
- no Codex execution
- no Ollama or local model invocation
- no documentation-agent execution or documentation mutation
- no GitHub API, `gh`, issues, PRs, workflows, or network calls
- no external agents
- no patch application
- no automatic dispatch, completion bypass, or next-item execution

M102 preserves historical completed queue items that predate explicit evidence requirements. M101 approval state remains advisory/manual handoff state only and cannot bypass dependency or completion locks.

## M101 Human Approval Gate UI/Data Contract Context

Status: Completed locally on `main` after validation.

Queue item: `m101-human-approval-gate-ui-data-contract`.

Implementation commit: `da90ed3`.

M101 creates local-only approval gate records for dispatch artifacts and dry-run outputs. It is a data/UI contract only:

- `local_only: true`
- `execution_allowed: false`
- file-backed records under `.aresforge/dispatch_approval_gates.json`
- read-only Hub surface for reviewing gate records
- no automated execution or external handoff after approval

Primary commands:

- `python -m aresforge create-dispatch-approval-gate --item-id <item_id> --artifact-type <type> [--format json]`
- `python -m aresforge inspect-dispatch-approval-gate --approval-id <approval_id> [--format json]`
- `python -m aresforge update-dispatch-approval-gate --approval-id <approval_id> --status <status> --review-notes <text> [--format json]`

Supported statuses:

- `pending_review`
- `approved_for_manual_handoff`
- `rejected`
- `needs_revision`

Required checklist defaults:

- operator reviewed the dispatch or dry-run output
- operator confirmed the artifact matches the selected lane
- operator confirmed the local-only boundary
- operator confirmed `execution_allowed=false`
- operator confirmed no automatic handoff or execution
- operator recorded review notes before status change

M101 boundaries:

- no Codex execution
- no Ollama or local model invocation
- no documentation-agent execution or documentation mutation
- no GitHub API, `gh`, issues, PRs, workflows, or network calls
- no external agents
- no patch application
- no automatic queue start, completion, dispatch, or next-item execution

M102 remains the dependency/completion locking hardening milestone; M101 supplies approval state, not lock bypass.

## M100 Documentation Agent Dry-Run Review Workflow Context

Status: Completed locally on `main` after validation.

Queue item: `m100-documentation-agent-dry-run-review-workflow`.

Implementation commit: `bc05476`.

M100 builds on M97 by validating documentation-agent dry-run readiness only when the M97 selected lane is `documentation_agent_dry_run` and the plan remains safe:

- `local_only: true`
- `execution_allowed: false`
- no dispatch-plan blocked reasons
- selected lane exactly `documentation_agent_dry_run`

Primary command:

- `python -m aresforge validate-documentation-agent-dry-run --item-id <item_id> [--format json|markdown] [--output <path>] [--force]`

M100 dry-run boundaries:

- dry-run output only
- no documentation-agent execution
- no documentation mutation
- no local LLM or Ollama invocation
- no Codex execution
- no GitHub API, `gh`, issues, PRs, workflows, or network calls
- no external agents
- no patch application
- no automatic queue start, completion, dispatch, or next-item execution

Blocked lanes:

- `codex_prompt_artifact`
- `local_llm_advisory`
- `local_llm_coding_draft`
- `human_only_manual`

Operator workflow:

- inspect the M97 dispatch plan
- validate the M100 documentation-agent dry-run
- review source docs, stale-doc checks, expected updates, and reconciliation scope locally
- approve any future documentation apply path only in a later milestone

M101 remains the human approval gate contract milestone and is not authorized by M100.

## M99 Local LLM Advisory Execution Dry-Run Validator Context

Status: Completed locally on `main` after validation.

Queue item: `m99-local-llm-advisory-dry-run-validator`.

Implementation commit: `b04e868`.

M99 builds on M97 by validating local LLM advisory dry-run readiness only when the M97 selected lane is `local_llm_advisory` and the plan remains safe:

- `local_only: true`
- `execution_allowed: false`
- no dispatch-plan blocked reasons
- selected lane exactly `local_llm_advisory`

Primary command:

- `python -m aresforge validate-local-llm-advisory-dry-run --item-id <item_id> [--format json|markdown] [--output <path>] [--force]`

M99 dry-run boundaries:

- dry-run output only
- no Ollama API calls
- no local model execution
- no Codex execution
- no documentation-agent execution
- no GitHub API, `gh`, issues, PRs, workflows, or network calls
- no external agents
- no patch application
- no automatic queue start, completion, dispatch, or next-item execution

Blocked lanes:

- `codex_prompt_artifact`
- `local_llm_coding_draft`
- `documentation_agent_dry_run`
- `human_only_manual`

Operator workflow:

- inspect the M97 dispatch plan
- validate the M99 local LLM advisory dry-run
- review the dry-run output locally
- approve any future advisory artifact or local LLM advisory run only in a later milestone

M100 remains the documentation-agent dry-run milestone and is not authorized by M99.

## M98 Codex Prompt Dispatch Artifact Generator Context

Status: Completed locally on `main`.

Queue item: `m98-codex-prompt-dispatch-artifact-generator`.

Implementation commit: `80f64dd`.

M98 builds on M97 by generating a local Codex prompt artifact only when the M97 selected lane is `codex_prompt_artifact` and the plan remains safe:

- `local_only: true`
- `execution_allowed: false`
- no dispatch-plan blocked reasons
- selected lane exactly `codex_prompt_artifact`

Primary command:

- `python -m aresforge generate-codex-dispatch-artifact --item-id <item_id> [--format json|markdown] [--output <path>] [--force]`

M98 artifact boundaries:

- prompt artifacts are manual/operator-gated and copy/paste-only
- no Codex execution
- no Ollama or local LLM invocation
- no documentation-agent execution
- no GitHub API, `gh`, issues, PRs, workflows, or network calls
- no external agents
- no patch application
- no automatic queue start, completion, dispatch, or next-item execution

Blocked lanes:

- `local_llm_advisory`
- `local_llm_coding_draft`
- `documentation_agent_dry_run`
- `human_only_manual`

Operator workflow:

- inspect the M97 dispatch plan
- generate the M98 Codex prompt artifact
- review the artifact locally
- manually copy/paste into Codex only after approval
- paste final Codex results back into the queue completion evidence flow

M99 remains the local LLM dry-run validation milestone and is not authorized by M98.

## M97 Queue-to-Agent Dispatch Plan Contract Context

Status: Completed locally on `main`.

Queue item: `m97-queue-to-agent-dispatch-plan-contract`.

Implementation commit: `4ec0500`.

M96 queue status: `m96-post-sprint-planning-and-prioritization` remains `proposed`; M97 was seeded separately for this implementation pass and is now `done`.

Current M97 scope:

- inspect exactly one local queue item
- produce a structured advisory dispatch plan
- select one dispatch lane with confidence and reason
- include item identity, planned artifact intent, approval gates, blocked reasons, and next safe action
- keep `local_only: true` and `execution_allowed: false`

Supported M97 lanes:

- `codex_prompt_artifact`
- `local_llm_advisory`
- `local_llm_coding_draft`
- `documentation_agent_dry_run`
- `human_only_manual`

M97 operator boundaries:

- do not execute Codex, Ollama, local LLMs, documentation agents, external agents, GitHub CLI, GitHub API, issues, PRs, workflows, daemons, watchers, schedulers, or network calls
- do not generate the full Codex prompt in M97; M98 owns that artifact generation
- do not apply generated patches or documentation output
- do not mutate queue state from dispatch-plan inspection
- require operator review and approval before any future dispatch or model/provider run

Primary command:

- `python -m aresforge inspect-queue-dispatch-plan --item-id <item_id> [--format json|markdown]`

## M96 Post-Sprint Planning and Prioritization Context

Status: Proposed in the local queue; retained as planning context.

Queue item: `m96-post-sprint-planning-and-prioritization`.

Current review posture:

- M81-M95 are complete in the local queue.
- M96 was absent before this pass and has been seeded locally for planning/reconciliation.
- The local project report is ready, local-only, and shows no blockers.
- The queue summary shows no blocked, ready, or in-progress items before M96 seeding.
- The sprint batch report shows no next proposed milestone, so the roadmap now carries the next planned batch.
- The handoff package is safe/read-only but depended on older current-phase headings for its prose summary; use the M96 source docs as the fresher authority.

M96 operator boundaries:

- do not execute Codex, Ollama, local LLMs, external agents, GitHub CLI, GitHub API, issues, PRs, workflows, daemons, watchers, or schedulers
- do not apply generated patches or rewrite docs from model output automatically
- do not auto-start or auto-complete any next queue item
- treat local LLM, Codex, documentation-agent, and patch application flows as advisory/contract-level unless an existing command explicitly writes a local artifact under operator control

Next recommended batch:

- M97 Queue-to-Agent Dispatch Plan Contract
- M98 Codex Prompt Dispatch Artifact Generator v1
- M99 Local LLM Advisory Execution Dry-Run Validator
- M100 Documentation Agent Dry-Run Review Workflow
- M101 Human Approval Gate UI/Data Contract
- M102 Queue Dependency and Completion Locking Hardening
- M103 AresForge Self-Managed Project Seed Review
- M104 Operator Batch Planner v1
- M105 Post-M96 Documentation Reconciliation

Do not start M97 automatically. Seed or start it only after M96 closeout review and explicit operator selection.

## M95 Final Overnight Sprint Reconciliation Context

Status: Completed locally on `main`.

Implementation commit: `21008e644bc433e820bd30346da23b422db43e8c`.

Final reconciliation focus:

- align `BUILD_STATE`, `AGENT_CONTEXT`, roadmap, local operator usage, and architecture docs with the completed M81-M94 sprint
- keep M95 contract-first and documentation-only, with no new runtime feature work
- preserve local-only/manual gates for queue completion evidence

Current implementation posture:

- local LLM advisory and coding lanes can produce artifacts only through explicit local operator commands
- local coding draft output remains non-applied and non-authoritative
- human-gated patch application remains a dry-run contract only
- documentation reconciliation can plan but cannot rewrite docs automatically
- handoff and sprint batch reports are read-only by default and write local artifacts only through explicit `--output`

Recommended next milestone:

- after M95 evidence is recorded, review `generate-handoff-package` and `inspect-sprint-batch-report`; seed a new M96 planning or priority item manually if more work is desired

Boundaries preserved:

- no GitHub API or `gh`
- no external workflow execution
- no Codex execution, local LLM invocation, prompt/model execution, or generated-output apply path
- no automatic queue completion or next-item execution

## M94 Overnight Sprint Batch Report Context

Status: Completed locally on `main`.

Implementation commit: `ed8cc6df00fa7ffc5199b95aa9a72fd468a070b0`.

Current batch report scope:

- `inspect-sprint-batch-report` summarizes an overnight sprint batch from local git history, queue evidence, and dispatch run states.
- Operators can choose `--since-commit <hash>` or `--commit-count <n>`.
- The report includes completed items, commits, validation evidence from queue completion, dispatch/recovered run summary, queue posture, unresolved warnings, and next recommended milestone.
- The default path writes nothing; `--output` is the only local artifact write path.

Boundaries preserved:

- no GitHub API or `gh`
- no external workflow execution
- no Codex execution, local LLM invocation, or prompt/model execution
- no queue mutation, queue completion, or automatic next-item execution

## M93 Operator Handoff Package v2 Context

Status: Completed locally on `main`.

Current handoff scope:

- `generate-handoff-package` now reports the M93 v2 handoff contract.
- Handoff output includes current HEAD, recent commits, queue summary, active/ready queue items, recovered dispatch summary, model routing summary, known warnings, safe command suggestions, and next safe actions.
- The default path writes nothing; `--output` is the only local artifact write path.

Boundaries preserved:

- no Codex execution, local LLM invocation, or model routing execution
- no queue mutation, queue completion, or automatic next-item execution
- no GitHub API, `gh`, GitHub mutation, issues, PRs, workflows, daemon, watcher, scheduler, or external workflow execution

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
