# AresForge Build State

## M164 GitHub Issue Status Comment Sync

Status: Completed locally on `main` after validation.

Queue item: `m164-github-issue-status-comment-sync`.

M164 adds a dry-run-default GitHub issue status comment sync command:

- `python -m aresforge sync-github-issue-status-comment --item-id m164-github-issue-status-comment-sync --dry-run --format json`
- stable `github_issue_status_comment_sync_v1` JSON
- composes local queue status, M153 orchestration run monitor evidence, validation evidence, artifact links/paths, M162 linked-issue planning, M158 autonomy profile policy, and M131 machine gates
- generates a marked status comment body for create/update synchronization
- supports mocked live create/update only when explicit GitHub enablement, `github_issue_sync_enabled` autonomy profile, linked issue metadata or `--issue-number`, safe queue status, and machine gates pass

Safety posture:

- dry-run remains the default and performs no GitHub mutation
- live status comment sync is one-item/one-comment scoped and requires `--github-enabled`, non-dry-run invocation, `autonomy_profile=github_issue_sync_enabled`, a linked issue number or `--issue-number`, safe queue status, and a passing `github_sync` machine gate
- the command performs no queue mutation, Codex execution, local LLM/model execution, source patch application, validation command execution, PR merge, protected branch update, force push, auto-merge, release creation, workflow mutation, retry, resume, or automatic next-item execution

## M163 GitHub Issue Creation for Safe Queue Items

Status: Completed locally on `main` after validation.

Queue item: `m163-github-issue-creation-for-safe-queue-items`.

M163 adds a dry-run-default GitHub issue creation command for one safe local queue item:

- `python -m aresforge create-github-issue-for-safe-queue-item --item-id m163-github-issue-creation-for-safe-queue-items --dry-run --format json`
- stable `github_issue_creation_for_safe_queue_items_v1` JSON
- composes the M162 local issue draft, linked-issue detection, M158 autonomy profile policy, and M131 `github_sync` machine gate
- blocks duplicate creation when local queue metadata already links a GitHub issue
- supports mocked real issue creation only when explicit GitHub enablement, `github_issue_sync_enabled` autonomy profile, safe queue status, and machine gates pass

Safety posture:

- dry-run remains the default and performs no GitHub mutation
- real issue creation is one-item-only and requires `--github-enabled`, non-dry-run invocation, `autonomy_profile=github_issue_sync_enabled`, a passing `github_sync` machine gate, no linked issue metadata, and safe queue status
- the command performs no queue mutation, Codex execution, local LLM/model execution, source patch application, validation command execution, PR merge, protected branch update, force push, auto-merge, release creation, workflow mutation, retry, resume, or automatic next-item execution

## M162 GitHub Issue Sync Plan from Queue Items

Status: Completed locally on `main` after validation.

Queue item: `m162-github-issue-sync-plan-from-queue-items`.

M162 adds a local-only GitHub issue sync planner:

- `python -m aresforge plan-github-issue-sync --project-id aresforge --format json`
- stable `github_issue_sync_plan_from_queue_items_v1` JSON
- maps local queue fields into future GitHub issue title, body, labels, milestone, and comments
- detects already-linked issues from local metadata fields such as `github_issue`, `github_issue_number`, `issue_url`, and `external_links`
- emits create, update, comment, and skip recommendations without calling GitHub

Safety posture:

- the planner reads the local queue and source-of-truth docs only
- it checks the read-only machine gate for planner evidence
- it performs no `gh`, GitHub API, issue mutation, label/milestone/comment mutation, Codex, model, queue mutation, source patch application, retry, resume, protected-branch update, workflow mutation, PR merge, force push, release creation, or automatic next-item execution
- recommendations are review evidence only; any future live issue sync remains a separate explicit machine-gated milestone

## M161 Codex Loop Validation Evidence Bundle

Status: Completed locally on `main` after validation.

Queue item: `m161-codex-loop-validation-evidence-bundle`.

M161 adds a durable local evidence bundle command for Codex loop validation:

- `python -m aresforge bundle-codex-loop-validation-evidence --item-id m161-codex-loop-validation-evidence-bundle --dry-run --format json`
- stable `codex_loop_validation_evidence_bundle_v1` JSON with execution record summary, stdout/stderr artifact copies, changed files, validation commands/results, machine gate results, source patch risk classification, retry classification, completion recommendation, and next safe action
- local bundle artifacts under `.aresforge/codex_loop_validation_evidence/`
- dry-run composition through the existing Codex loop evidence path; no live Codex is invoked by the bundle command

Safety posture:

- M161 requires `--dry-run` for evidence generation and writes only local evidence artifacts
- dry-run evidence bundling performs no real Codex, local LLM/model, GitHub, source patch application, queue completion, retry, resume, protected-branch update, workflow mutation, PR merge, force push, release creation, or automatic next-item execution
- source patch and retry classifications are advisory evidence only; any future patch apply, retry, queue completion, or GitHub sync remains a separate explicit gated action

## M160 Low-Risk Codex Execution Pilot Item

Status: Completed locally on `main` after validation.

Queue item: `m160-low-risk-codex-execution-pilot-item`.

M160 adds a machine-gated low-risk Codex pilot coordinator:

- `python -m aresforge prepare-low-risk-codex-pilot --item-id m160-low-risk-codex-execution-pilot-item --dry-run --format json`
- stable `low_risk_codex_execution_pilot_item_v1` JSON with pilot preparation, low-risk verification, M159 preflight decisions, M152/M151 loop summary, local artifacts, execution flags, and GitHub stop boundary
- dry-run is the default behavior and does not invoke real Codex
- optional real execution requires explicit `--execution-enabled`, `--allow-low-risk-code`, declared low-risk `--changed-path` scope, passing M159 preflight, passing pilot low-risk checks, and machine-gated M152 loop execution

Safety posture:

- dry-run preparation may create local loop artifacts only and performs no Codex, model, GitHub, patch, queue mutation, retry, resume, or next-item execution
- real pilot execution, when explicitly requested and safe, may invoke only the configured Codex command through the existing low-risk local loop and validation path
- M160 never pushes to GitHub, creates or merges PRs, updates protected branches, enables auto-merge, creates releases, applies source patches through AresForge, completes the queue item, retries automatically, or starts later milestones

## M159 Real Codex Execution Preflight Hardening

Status: Completed locally on `main` after validation.

Queue item: `m159-real-codex-execution-preflight-hardening`.

M159 adds a dry-run-only preflight hardening command for future real Codex execution:

- `python -m aresforge preflight-real-codex-execution --item-id m159-real-codex-execution-preflight-hardening --dry-run --format json`
- stable `real_codex_execution_preflight_hardening_v1` JSON with autonomy profile, worktree guard, read-only/operator-autonomy machine gates, durable run-store readiness, artifact readiness, validation profile, retry policy, source patch risk policy, dirty-tree detection, and future required gate metadata
- default candidate autonomy profile is `codex_low_risk_enabled`, but the command itself remains non-executing
- command success means the preflight record was generated; the record's `blocked` and `blocked_reasons` fields decide whether future real Codex should remain blocked
- dirty worktree state, missing required artifact roots, invalid run store, unsuitable autonomy profile, missing queue item, or failed local gates block future real Codex readiness

Safety posture:

- preflight requires `--dry-run` and never invokes Codex, local models, GitHub, validation commands, source patch apply, queue mutation, retry, resume, or next-item execution
- source patch application remains default-deny; M159 reports policy only and performs no patch classification or apply check unless a future separate command is invoked
- real Codex remains limited to a separate explicit low-risk command with operator flags, clean worktree, captured artifacts, machine gates, and validation evidence

## M158 Operator Autonomy Configuration Profile

Status: Completed locally on `main` after validation.

Queue item: `m158-operator-autonomy-configuration-profile`.

M158 adds explicit operator autonomy configuration profile inspection:

- `python -m aresforge inspect-autonomy-profile --project-id aresforge --format json`
- stable `operator_autonomy_configuration_profile_v1` JSON with `locked_down`, `advisory_only`, `low_risk_local`, `codex_dry_run`, `codex_low_risk_enabled`, `github_sync_dry_run`, `github_issue_sync_enabled`, and `experimental_full_local`
- default profile is `locked_down` with safe-deny behavior for every non-read capability
- each profile exposes capability controls as `enabled`, `dry_run_only`, or `blocked`, required machine-gate profiles, required explicit flags, status counts, blocked operations, and next safe action
- adds the read-only `operator_autonomy_profile` machine safety gate for profile inspection

Safety posture:

- profile inspection is local-only and does not execute the capabilities it describes
- "enabled" profile entries still require separate explicit commands, operator intent, and passing machine gates before any future action
- the inspector performs no agent, Codex, local LLM/model, GitHub, validation command, source patch, queue mutation, retry, resume, PR merge, force push, protected-branch update, workflow mutation, release, or automatic next-item execution

## M157 Run Replay and Audit Trail

Status: Completed locally on `main` after validation.

Queue item: `m157-run-replay-and-audit-trail`.

M157 adds a local orchestration replay/audit inspector:

- `python -m aresforge replay-orchestration-run --run-id sample-run --dry-run --format json`
- stable `orchestration_run_replay_audit_trail_v1` JSON with dry-run metadata reconstruction, source record summaries, source artifact hashes, reconstructed step records, reconstructed machine gates, decision timeline, audit events, and safety flags
- reads durable run-store records, M141 history/recovery evidence, M153 monitor evidence, M156 retention index metadata, source run artifacts, step results, evidence bundles, and referenced artifacts when present
- missing run evidence reports `status=no_replay_record` with warnings rather than executing anything

Safety posture:

- replay requires `--dry-run` and performs metadata reconstruction only
- replay performs no agent, Codex, local LLM/model, GitHub, validation command, source patch, queue mutation, artifact cleanup, retry, resume, protected-branch update, workflow mutation, PR merge, force push, release creation, or automatic next-item execution
- source execution flags and reconstructed source gates are reported as audit evidence; the replay command's own execution flags remain false

## M156 Orchestration Artifact Retention Policy

Status: Completed locally on `main` after validation.

Queue item: `m156-orchestration-artifact-retention-policy`.

M156 adds a local orchestration artifact retention/indexing inspector:

- `python -m aresforge inspect-orchestration-artifact-retention --project-id aresforge --format json`
- stable `orchestration_artifact_retention_policy_v1` JSON with artifact categories, expected folders, retention status, artifact count summaries, orphan detection, stale artifact warnings, retention recommendations, and dry-run cleanup planning
- coverage for durable run store metadata, orchestration run artifacts, run monitor reports, resume plans, normalized step results, Codex loop evidence, validation evidence, documentation-agent evidence, and autonomy reports
- orphan detection compares durable run-store artifact references against index-required artifact categories
- stale warnings are advisory and based on category-specific policy thresholds

Safety posture:

- retention inspection is local-only and read-only unless an explicit output path is supplied
- cleanup output is a dry-run plan only; M156 never deletes, moves, truncates, archives, or rewrites artifacts automatically
- it performs no agent, Codex, local LLM/model, GitHub, validation command, source patch, queue progression, retry, resume, protected-branch update, workflow mutation, PR merge, force push, release creation, or automatic next-item execution

## M155 Durable Orchestration Run Store

Status: Completed locally on `main` after validation.

Queue item: `m155-durable-orchestration-run-store`.

M155 adds a durable local orchestration run store:

- `python -m aresforge inspect-orchestration-run-store --project-id aresforge --format json`
- durable store path `.aresforge/orchestrator/run_history.json`
- stable `durable_orchestration_run_store_v1` JSON with append/read/update-by-run-id support, schema validation, deterministic ordering, missing-file bootstrap, corruption-safe structured errors, and store capability metadata
- M141 history/recovery append and read paths now use the durable store schema while preserving legacy artifact discovery
- the tracked empty store removes the prior missing durable `run_history.json` warning on fresh checkout

Safety posture:

- store inspection is local-only and never executes agents, Codex, local LLM/model calls, GitHub operations, validation commands, source patches, queue progression, retry, resume, or next-item work
- missing-file bootstrap is bounded local persistence only and is reported with `mutation_performed=true`; the tracked repository store means normal inspection reports no mutation
- corrupt store files fail closed with blocked structured output instead of falling back to execution or unsafe recovery assumptions

## M154 Sprint Closeout and Autonomy Readiness Report

Status: Completed locally on `main` after validation.

Queue item: `m154-sprint-closeout-and-autonomy-readiness-report`.

M154 closes the M140-M154 orchestrator hardening sprint with a local readiness report:

- `python -m aresforge generate-autonomy-readiness-report --project-id aresforge --sprint-start M140 --sprint-end M154 --format json`
- optional `--item-id`, `--queue-path`, `--output`, and `--force`
- stable `autonomy_readiness_report_v1` JSON with sprint closeout summary, capability summary, queue/doc/artifact evidence, machine gate status, LLM decision-policy summary, orchestration monitor summary, remaining blockers, next sprint recommendations, and next safe action
- optional local artifact output under `.aresforge/autonomy_readiness_reports/`

Safety posture:

- the report is local-first and read-only unless an explicit `--output` artifact path is supplied
- it reuses queue, agent registry, LLM decision policy, machine safety gate, and orchestration monitor evidence
- it performs no agent, Codex, local LLM/model, GitHub, validation command, source patch, queue mutation, retry, resume, protected-branch update, workflow mutation, PR merge, force push, release creation, or automatic next-item execution
- real Codex execution, source patch application, GitHub mutation, local LLM output application, and automatic next-item execution remain separate default-deny machine-gated paths

## M153 Hub Orchestration Run Monitor

Status: Completed locally on `main` after validation.

Queue item: `m153-hub-orchestration-run-monitor`.

M153 adds a read-only Hub orchestration run monitor:

- `python -m aresforge inspect-orchestration-run-monitor --project-id aresforge --format json`
- optional `--item-id`, `--run-id`, `--queue-path`, `--history-path`, `--artifacts-root`, `--output`, and `--force`
- stable `hub_orchestration_run_monitor_v1` JSON with run state, history summary, latest run details, step results, recovery status, resume-plan summary, machine-gate rollup, artifact references, and next safe action
- Hub API visibility through `GET /api/orchestration/run-monitor`
- optional local artifact output under `.aresforge/orchestrator/run_monitor/`

Safety posture:

- the monitor reads local history and artifacts only unless an explicit output path is supplied
- it performs no agent, Codex, local LLM/model, GitHub, validation command, patch, queue, retry, resume, or next-item execution
- recovery and resume signals are advisory; any future resume remains a separate explicit machine-gated command
- mutation, external execution, model execution, Codex execution, GitHub execution, and patch application flags remain false for the monitor itself

## M152 End-to-End Codex Loop Real Run for Low-Risk Code

Status: Completed locally on `main` after validation.

Queue item: `m152-end-to-end-codex-loop-real-run-for-low-risk-code`.

M152 extends `run-end-to-end-codex-loop` with a default-deny real execution profile for low-risk code:

- dry-run smoke: `python -m aresforge run-end-to-end-codex-loop --item-id m152-end-to-end-codex-loop-real-run-for-low-risk-code --dry-run --format json`
- real path requires `--execution-enabled`, `--allow-low-risk-code`, and one or more `--changed-path` values inside the low-risk source/test scope
- optional `--codex-command-arg` supplies the command array used by the existing M135 dispatch executor
- output is stable `end_to_end_codex_loop_real_low_risk_v1` JSON with local artifacts under `.aresforge/codex_loop_real_runs/` and dispatch artifacts under `.aresforge/codex_dispatch/loop_real_runs/`
- the loop reuses M135 Codex dispatch gates, M136 ingestion/validation/completion recommendation, queue snapshots, and the M152 `low_risk_code_scope` gate

Safety posture:

- dry-run remains non-executing and reports real execution as not allowed
- real Codex execution is blocked unless explicit real-execution and low-risk-code flags are present and the declared changed paths avoid workflows, protected config, queue state, orchestration/Codex runtime, Hub, scripts, migrations, and outside-scope paths
- non-dry-run dispatch requires the existing `codex_dispatch` machine gate and clean-worktree guard from M135
- M152 may run allowlisted M136 validation commands after real Codex dispatch, but it does not apply source patches through AresForge, push to GitHub, merge PRs, mutate protected branches, enable auto-merge, create releases, complete queue items, or start another item

## M151 End-to-End Codex Loop Dry Run

Status: Completed locally on `main` after validation.

Queue item: `m151-end-to-end-codex-loop-dry-run`.

M151 adds a local, machine-gated end-to-end Codex loop dry-run coordinator:

- `python -m aresforge run-end-to-end-codex-loop --item-id m151-end-to-end-codex-loop-dry-run --dry-run --format json`
- optional `--project-id`, `--validation-profile`, `--queue-path`, `--output`, and `--force`

The command emits stable `end_to_end_codex_loop_dry_run_v1` JSON and writes bounded local artifacts under `.aresforge/codex_loop_dry_runs/`, with a dispatch artifact under `.aresforge/codex_dispatch/loop_dry_runs/` and M136 ingestion evidence under `artifacts/codex_result_ingestion/`.

Safety posture:

- the loop is dry-run only; non-dry-run requests block
- it reuses M135 Codex dispatch machine gates and M136 result ingestion, validation-profile selection, dispatch-evidence parsing, and completion recommendation boundaries
- validation commands are selected and recorded but not executed in M151 dry-run mode
- completion recommendation is local evidence only and does not complete the queue item
- real Codex execution, local LLM/model execution, GitHub execution, patch application, queue mutation, retry, protected-branch updates, workflow mutation, PR merge, force push, release creation, and automatic next-item execution remain blocked
- dirty canonical worktree state may appear as advisory completion-gate evidence while the dry-run itself remains non-mutating

## M150 Machine-Gated Source Patch Apply Dry Run

Status: Completed locally on `main` after validation.

Queue item: `m150-machine-gated-source-patch-apply-dry-run`.

M150 adds a local, machine-gated source patch apply dry-run checker:

- `python -m aresforge dry-run-source-patch-apply --item-id m150-machine-gated-source-patch-apply-dry-run --patch-path artifacts/manual/sample-source.patch --format json`
- optional `--project-id`, `--queue-path`, `--output`, and `--force`

The dry-run emits stable `source_patch_apply_dry_run_v1` JSON with M149 apply-plan evidence, M148 classification summary, source-patch dry-run machine-gate evidence, `git apply --check` applicability proof, explicit non-mutation flags, and the next safe action.

Safety posture:

- this command may run `git apply --check` only after M149 apply-plan eligibility and the `source_patch_apply_dry_run` machine gate pass
- it never applies a patch, stages files, commits files, runs validation commands, mutates queue status, calls Codex, calls models, calls GitHub, retries, or starts follow-on work
- workflow, protected config, queue-state, binary, executable-mode, outside-repo, failed gate, and failed clean-apply checks block the dry run or future apply eligibility
- a passing dry run is applicability evidence only; actual source patch application remains a separate future explicit gated command with validation evidence

## M149 Controlled Source Patch Apply Plan

Status: Completed locally on `main` after validation.

Queue item: `m149-controlled-source-patch-apply-plan`.

M149 adds a local, machine-gated source patch apply planner:

- `python -m aresforge plan-source-patch-apply --item-id m149-controlled-source-patch-apply-plan --patch-path artifacts/manual/sample-source.patch --format json`
- optional `--project-id`, `--queue-path`, `--output`, and `--force`

The planner emits stable `source_patch_apply_plan_v1` JSON with the M148 risk classification summary, touched files, hard apply blockers, pre-apply checks, ordered future apply steps, validation plan, rollback plan, read-only machine-gate evidence, explicit execution flags, and next safe action.

Safety posture:

- this command reads and plans around a local patch but never applies it
- source patch application remains unavailable from M149 and requires a separate future explicit apply command, machine gate, clean apply check, operator review, and validation evidence
- workflow, protected config, queue-state, binary, executable-mode, and outside-repo patch operations are hard blockers for future controlled apply planning
- this command performs no agent, Codex, local LLM/model, GitHub, validation command, patch, queue, retry, or next-item execution

## M148 Safe Source Patch Detection and Risk Classifier

Status: Completed locally on `main` after validation.

Queue item: `m148-safe-source-patch-detection-and-risk-classifier`.

M148 adds a local, machine-gated source patch risk classifier:

- `python -m aresforge classify-source-patch-risk --patch-path artifacts/manual/sample-source.patch --format json`
- optional `--item-id`, `--project-id`, `--queue-path`, `--output`, and `--force`

The classifier emits stable `source_patch_risk_classification_v1` JSON with touched files, per-file path classes, mutation types, overall risk level, blocked operations, recommended validation profile/test requirements, read-only machine-gate evidence, validation-agent and LLM decision-policy summaries, and explicit execution flags.

Safety posture:

- this command reads and classifies a local patch but never applies it
- source patch application remains blocked until a separate explicit human-gated or future machine-gated apply path exists
- workflow, protected config, queue-state, binary, executable-mode, and outside-repo patch operations are detected as blocked automatic-apply operations
- this command performs no agent, Codex, local LLM/model, GitHub, validation command, patch, queue, retry, or next-item execution

## M147 Orchestrator Resume-from-Failure

Status: Completed locally on `main` after validation.

Queue item: `m147-orchestrator-resume-from-failure`.

M147 adds a local, machine-gated orchestration resume-plan inspector:

- `python -m aresforge inspect-orchestration-resume-plan --run-id sample-run --format json`
- optional `--item-id`, `--project-id`, `--queue-path`, `--history-path`, `--artifacts-root`, `--output`, and `--force`

The inspector emits stable `orchestrator_resume_from_failure_plan_v1` JSON with run/checkpoint status, resume eligibility, last valid checkpoint metadata, source run execution flags, read-only machine-gate evidence, pre-resume checks, agent registry and LLM decision-policy summaries, and a recommended next safe action.

Safety posture:

- this command performs no resume, retry, agent, Codex, local LLM/model, GitHub, validation command, patch, queue, or next-item execution
- missing run records are advisory and do not trigger execution
- interrupted and max-step-limited runs may report `resume_available` only when checkpoint evidence and read-only gates pass and no validation-required effects are present
- failed, blocked, mutating, Codex, GitHub, patch, queue-mutating, or failed-gate runs require explicit validation, classification, or operator review before any future resume
- PR merge, force push, protected branch updates, releases, workflow mutation, gate bypass, source patch application from generated output, automatic retry loops, and automatic next-item execution remain blocked

## M146 Agent Step Result Normalization

Status: Completed locally on `main` after validation.

Queue item: `m146-agent-step-result-normalization`.

M146 adds a local, machine-gated agent step result normalizer:

- `python -m aresforge normalize-agent-step-result --result-path artifacts/manual/sample-agent-step-result.json --format json`
- optional `--item-id`, `--project-id`, `--queue-path`, `--output`, and `--force`

The normalizer emits stable `agent_step_result_normalization_v1` JSON with canonical item/run/status fields, blocked state, warnings, machine-gate summaries, artifact references, source execution flags, normalizer execution flags, agent registry and LLM decision-policy summaries, and orchestrator evaluation/recovery guidance.

Safety posture:

- this command performs no agent, Codex, local LLM/model, GitHub, validation command, patch, queue, retry, or next-item execution
- top-level execution flags describe the source step result; `normalizer_execution_flags` confirms the normalizer itself performed no mutation or external execution
- failed, blocked, invalid, interrupted, machine-gate-failed, mutation, Codex, GitHub, and patch results require explicit downstream recovery, validation, or review commands before completion or continuation
- PR merge, force push, protected branch updates, releases, workflow mutation, gate bypass, source patch application from generated output, automatic retry loops, and automatic next-item execution remain blocked

## M145 Codex Failure Classification and Retry Policy

Status: Completed locally on `main` after validation.

Queue item: `m145-codex-failure-classification-and-retry-policy`.

M145 adds a local, machine-gated Codex failure classifier:

- `python -m aresforge classify-codex-failure --failure-artifact artifacts/manual/sample-codex-failure.json --format json`
- optional `--item-id`, `--project-id`, `--queue-path`, `--output`, and `--force`

The classifier emits stable `codex_failure_classification_retry_policy_v1` JSON with a primary failure class, detected classes, deterministic retry policy, policy matrix, read-only machine-gate evidence, Codex agent summary, LLM decision-policy summary, observed failure-artifact execution flags, prohibited operations, and next safe action.

Safety posture:

- automatic retry loops are disabled
- retry-capable classes allow at most one future explicit operator-triggered retry after triage and machine gates
- missing or invalid failure artifacts stop classification and report blockers
- machine-gate, execution-denied, dirty-worktree, validation, evidence, interruption, and unknown failures stop until the reported recovery action is completed
- this command performs no Codex execution, local LLM/model execution, GitHub execution, validation command execution, patch application, queue mutation, or next-item execution

## M144 Codex Validation Profile Expansion

Status: Completed locally on `main` after validation.

Queue item: `m144-codex-validation-profile-expansion`.

M144 adds a local, machine-gated Codex validation profile inspector:

- `python -m aresforge inspect-codex-validation-profiles --format json`
- optional `--item-id`, `--project-id`, `--queue-path`, `--task-type`, `--risk-class`, repeated `--changed-path`, `--output`, and `--force`

The inspector emits stable `codex_validation_profile_expansion_v1` JSON with validation profile metadata, task-type resolution, changed-path classification, risk-class resolution, recommended M136 validation profile selection, read-only machine-gate evidence, validation-agent summary, LLM decision policy summary, prohibited operations, execution flags, and the next safe action.

Safety posture:

- this command performs no Codex execution, local LLM/model execution, GitHub execution, validation command execution, patch application, queue mutation, or next-item execution
- validation profiles remain allowlisted command plans for separate explicit M136 ingestion through `ingest-codex-result-and-validate --validation-profile <profile>`
- high, critical, unknown, protected, workflow, and mixed-risk changes expand toward broader local-safe validation
- real Codex execution remains default-deny and completion still requires downstream evidence plus machine-gated queue mutation or human review

## M143 Codex Execution Sandbox and Worktree Guard

Status: Completed locally on `main` after validation.

Queue item: `m143-codex-execution-sandbox-and-worktree-guard`.

M143 adds a local, machine-gated Codex sandbox/worktree guard inspector:

- `python -m aresforge inspect-codex-worktree-guard --item-id m143-codex-execution-sandbox-and-worktree-guard --format json`
- optional `--project-id`, `--queue-path`, `--output`, and `--force`

The inspector emits stable `codex_execution_sandbox_worktree_guard_v1` JSON with read-only machine-gate evidence, queue status, dirty-worktree detection, sandbox policy, output capture boundaries, transaction-log summary, prohibited operations, execution flags, and the next safe action.

Safety posture:

- real Codex execution remains denied by default
- dirty worktree state is captured as guard evidence and prevents future real Codex execution from being treated as safe until reviewed or clean
- Codex stdout, stderr, and result metadata must stay in bounded local artifacts
- this command performs no Codex, local LLM, GitHub, patch, validation-command, queue, or external execution
- PR merge, force push, protected branch updates, releases, workflow mutation, source patch application from generated output, gate bypass, and automatic next-item execution remain blocked

## M142 Real Codex Execution Enablement Profile

Status: Completed locally on `main` after validation.

Queue item: `m142-real-codex-execution-enablement-profile`.

M142 adds a local, machine-gated real Codex execution enablement profile inspector:

- `python -m aresforge inspect-codex-execution-enablements --format json`
- optional `--item-id`, `--project-id`, `--queue-path`, `--output`, and `--force`

The inspector emits stable `codex_execution_enablement_profile_v1` JSON with default-deny status, explicit enablement profiles, read-only machine-gate evidence, Codex dispatch gate requirements, LLM decision policy summary, Codex agent registry summary, prohibited operations, execution flags, artifact references, and the next safe action.

Safety posture:

- real Codex execution is denied by default
- this command performs no Codex, local LLM, GitHub, patch, validation-command, queue, or external execution
- real Codex execution remains available only through separate explicit gated commands such as `run-codex-dispatch --execution-enabled` or `run-agent-orchestration --allow-codex`
- every real Codex path requires a prepared local artifact, explicit allow flag, machine gate, captured local artifacts, and M136 validation before any completion decision
- PR merge, force push, protected branch updates, releases, workflow mutation, source patch application from generated output, gate bypass, and automatic next-item execution remain blocked

## M141 Orchestration Run History and Recovery

Status: Completed locally on `main` after validation.

Queue item: `m141-orchestration-run-history-and-recovery`.

M141 adds a durable local orchestration run history and recovery inspector:

- `python -m aresforge inspect-orchestration-run-history --project-id aresforge --format json`
- optional `--item-id`, `--run-id`, `--queue-path`, `--history-path`, `--artifacts-root`, `--output`, and `--force`

The inspector emits stable `orchestration_run_history_recovery_v1` JSON with run records, recovery records for blocked, failed, interrupted, running, and max-step-limited runs, machine-gate summaries, local artifact references, execution flags, and the next safe action. New `run-agent-orchestration` executions append local metadata to `.aresforge/orchestrator/run_history.json`; the inspector also discovers older `artifacts/multi-agent-orchestration/**.json` records so existing M138 artifacts remain inspectable.

Safety posture:

- the history inspector is read-only
- run-history persistence is local metadata only after an explicit gated orchestration command
- recovery records are advisory inspection records, not retries or resumes
- no Codex, local LLM, GitHub, validation command, patch application, queue completion, or next-item execution is performed by M141

## M140 Orchestrator Execution State Machine v1

Status: Completed locally on `main` after validation.

Queue item: `m140-orchestrator-execution-state-machine-v1`.

M140 adds the durable orchestrator execution state machine inspector:

- `python -m aresforge inspect-orchestrator-state-machine --format json`
- optional `--item-id`, `--project-id`, `--queue-path`, `--output`, and `--force`

The inspector emits stable `orchestrator_execution_state_machine_v1` JSON with explicit run states, allowed transitions, terminal statuses, checkpoints, validation boundaries, machine-gate summaries, execution flags, and the next safe action. It reuses the M126 agent registry and M131 read-only machine safety gate. It does not execute agents, Codex, local LLMs, GitHub, validation commands, patches, queue mutation, or follow-on work.

Safety posture:

- future executable transitions must pass their declared machine gate before an execution state is entered
- checkpoint-first resume/recovery is defined, but no automatic retry/rollback worker is added
- real Codex, local LLM, GitHub, patch application, and queue mutation paths remain separate explicit gated commands
- PR merge, force push, protected branch updates, releases, workflow mutation, source-code patch application from generated output, and automatic next-item execution remain blocked

## M139 Autonomous Sprint Closeout v1

Status: Completed locally on `main` after validation.

Queue item: `m139-autonomous-sprint-closeout-v1`.

M139 closes the M125-M139 agent foundation sprint and adds the sprint closeout generator:

- `python -m aresforge generate-autonomous-sprint-closeout --project-id aresforge --format json`
- optional `--sprint-start`, `--sprint-end`, `--dry-run`, `--apply-docs-only`, `--output`, and `--force`

The closeout inspects local queue state, the M126 agent registry, M131 machine gate availability, M138 orchestration capability, local artifacts, the queue transaction log, and source-of-truth documentation consistency. It writes a local `autonomous_sprint_closeout_v1` artifact and never runs Codex, local LLMs, GitHub, PR merges, code patch application, or automatic next-item execution.

Milestone status for this sprint:

- M125 Agent Runtime Boundary Contract: done.
- M126 Agent Registry: done.
- M127 LLM Decision Policy v1: done.
- M128 Agent Orchestration Plan Builder: done.
- M129 Single-Agent Dry-Run Executor: done.
- M130 Single-Agent Real Executor for Low-Risk Agents: done.
- M131 Machine Safety Gate Engine: done.
- M132 Auto-Completion for Safe Queue Items: done.
- M133 Documentation Agent Autonomous Apply for Docs-Only Patches: done.
- M134 Local LLM Advisory Execution: done.
- M135 Codex Dispatch Executor v1: done.
- M136 Codex Result Ingestion and Validation Runner: done.
- M137 GitHub PR/Issue Sync Agent: done.
- M138 Multi-Agent Orchestrator v1: done.
- M139 Autonomous Sprint Closeout v1: done.

Current autonomy posture:

- human review can now be replaced by machine gates for deterministic read-only inspection, local artifact writes, low-risk queue completion, docs-only Markdown patch apply, local LLM advisory execution, Codex dispatch, GitHub sync, and multi-agent orchestration when every required gate passes
- low-risk local agents can run real local execution records; high-risk agents remain explicit and gated
- Codex, local LLM, GitHub, and orchestration real paths require dedicated enablement flags and passing machine gates
- PR merge, force push, protected branch updates, releases, source-code patch application from generated output, background daemons, and automatic next-item execution remain blocked

Recommended next sprint:

- production hardening for orchestrator resume/retry/rollback
- real Codex loop reliability across dispatch, ingestion, validation, and clean-tree handling
- local LLM model quality comparison under advisory-only boundaries
- GitHub PR automation expansion behind new gates
- Hub agent control center for gates, timelines, artifacts, and next safe actions
- rollback/recovery model, agent metrics/telemetry, and self-managed project issue automation

## M138 Multi-Agent Orchestrator v1

Status: Completed locally on `main` after validation.

Queue item: `m138-multi-agent-orchestrator-v1`.

M138 adds the first step-by-step multi-agent orchestration runner:

- `python -m aresforge run-agent-orchestration --item-id <item_id> --format json`
- optional `--plan-path`, `--dry-run`, `--max-steps`, `--allow-low-risk-real`, `--allow-local-llm`, `--allow-codex`, `--allow-github-sync`, `--output`, and `--force`

Default behavior:

- dry-run by default
- loads an explicit orchestration plan or builds an M128 plan for the queue item
- evaluates a machine safety gate for every attempted step
- records a timeline with attempted, completed, and blocked steps
- stops on the first blocking gate or execution failure
- writes a local `multi_agent_orchestration_v1` result artifact

Supported initial patterns:

- read-only planning chain
- docs-only reconciliation chain
- Codex dispatch dry-run chain
- low-risk validation chain
- sprint summary dry-run chain

Safety boundaries:

- low-risk real execution requires `--allow-low-risk-real`
- local LLM, Codex, and GitHub real paths require their dedicated allow flags and their dedicated machine gates
- high-risk real steps are blocked by default
- no PR merge, force push, gate bypass, automatic queue completion, automatic next-item execution, or continuation after a failed required gate

## M137 GitHub PR/Issue Sync Agent

Status: Completed locally on `main` after validation.

Queue item: `m137-github-pr-issue-sync-agent`.

M137 adds a dry-run-first GitHub issue/PR sync agent:

- `python -m aresforge run-github-sync-agent --item-id <item_id> --format json`
- optional `--dry-run`, `--sync-mode issue-comment|issue-update|pr-comment|pr-summary`, `--github-enabled`, `--repo`, `--issue-number`, `--pr-number`, `--artifact-path`, `--output`, and `--force`

Allowed scope:

- dry-run planning without GitHub calls
- issue comments only when `--github-enabled` is explicit and `github_sync` machine gates pass
- PR comments only when `--github-enabled` is explicit and `github_sync` machine gates pass
- local issue metadata summary artifacts
- local PR metadata summary artifacts
- optional live issue/PR metadata fetch for summary artifacts when `--github-enabled` and gates pass

Blocked in M137:

- PR merge, auto-merge enablement, branch deletion, force push, PR approval, request changes, release creation, protected branch update, repository file writes, and automatic issue closure

The agent uses a mockable GitHub client boundary. Tests do not require live GitHub access.

## M136 Codex Result Ingestion and Validation Runner

Status: Completed locally on `main` after validation.

Queue item: `m136-codex-result-ingestion-and-validation-runner`.

M136 adds a local-only ingestion and validation runner for Codex execution records:

- `python -m aresforge ingest-codex-result-and-validate --item-id <item_id> --execution-record <path> --format json`
- optional `--dry-run`, `--validation-profile`, `--output`, and `--force`

Validation profiles:

- `docs_only`
- `tests_only`
- `code_unit_tests`
- `hub_ui`
- `queue_system`
- `codex_orchestration`
- `full_local_safe`

The runner reads one local Codex execution record, extracts stdout/stderr/result artifact text, detects changed files, selects allowlisted local validation commands, writes dispatch evidence, writes a completion recommendation, evaluates queue completion machine gates, and emits a stable `codex_result_ingestion_validation` record.

Safety boundaries:

- dry-run selects validation commands but does not run them
- validation execution is limited to local allowlisted commands for the selected profile
- generated evidence is local-only and advisory until a separate M132 auto-completion or human queue lifecycle action is invoked
- no Codex execution, GitHub API, `gh`, network service call, push, queue status mutation, automatic completion, or next-item execution

## M135 Codex Dispatch Executor v1

Status: Completed locally on `main` after validation.

Queue item: `m135-codex-dispatch-executor-v1`.

M135 adds a machine-gated Codex dispatch executor for prepared local dispatch artifacts:

- `python -m aresforge run-codex-dispatch --item-id <item_id> --artifact-path <artifact_path> --format json`
- optional `--dry-run`, `--execution-enabled`, `--output`, `--force`, `--timeout-seconds`, and `--require-clean-worktree`

Safety boundaries:

- dry-run records the intended command and artifacts but never invokes Codex
- non-dry-run execution is blocked unless `--execution-enabled` is supplied
- the `codex_dispatch` machine gate must pass
- the dispatch artifact must be existing JSON with required local-only/non-mutation safety flags
- the queue item must be `ready` with satisfied dependencies
- stdout, stderr, and result metadata are captured as local artifacts
- AresForge does not apply patches, call GitHub/`gh`, mutate queue status, mark completion, push automatically, or start follow-on work
- M136 is responsible for validating any Codex-produced file changes before completion decisions

## M134 Local LLM Advisory Execution

Status: Completed locally on `main` after validation.

Queue item: `m134-local-llm-advisory-execution`.

M134 adds a machine-gated local LLM advisory execution path:

- `python -m aresforge run-local-llm-advisory --item-id <item_id> --artifact-path <artifact_path> --format json`
- optional `--provider`, `--model`, `--dry-run`, `--output`, `--force`, and `--timeout-seconds`

Safety boundaries:

- reads one local advisory artifact and checks `local_llm_execution` machine gates before provider execution
- supports only local Ollama provider execution through a mockable provider boundary
- dry-run performs no provider call
- response output is captured only as a local advisory artifact
- no patch application, source mutation, queue mutation, GitHub/`gh`, Codex execution, remote provider calls, automatic completion, or next-item execution

## M133 Documentation Agent Autonomous Apply for Docs-Only Patches

Status: Completed locally on `main` after validation.

Queue item: `m133-documentation-agent-autonomous-apply-for-docs-only-patches`.

M133 adds the first documentation-agent autonomous patch application path, limited to machine-gated docs-only Markdown patches:

- `python -m aresforge apply-docs-only-patch --item-id <item_id> --patch-path <patch_path> --format json`
- optional `--dry-run`, `--force`, `--queue-path`, and `--output`

Required gates:

- `docs_only_patch_apply` machine safety gate
- docs Markdown path allowlist
- clean `git apply --check`
- no `src/` paths
- no `tests/` paths
- no package/config/script/workflow paths
- no binary patch content
- no hidden executable or file-mode changes
- no dirty pre-existing patch targets
- post-apply diff check
- transaction-log entry after successful non-dry-run apply

Safety boundaries:

- allowed patch targets are Markdown docs under `docs/`, including source-of-truth docs and `docs/architecture/*.md`
- blocked patch targets include source, tests, pyproject/package/config files, scripts, workflows, `.aresforge` queue files, binary files, and non-doc files
- the command does not execute Codex, Codex CLI, Ollama/local LLMs, remote LLMs, agents, GitHub, `gh`, network services, validation commands, or follow-on work
- dry-run performs no patch application and no transaction-log mutation
- successful apply mutates only docs Markdown files plus the local transaction log

## M132 Auto-Completion for Safe Queue Items

Status: Completed locally on `main` after validation.

Queue item: `m132-auto-completion-for-safe-queue-items`.

M132 adds a machine-gated queue auto-completion path for low-risk items only:

- `python -m aresforge auto-complete-safe-queue-item --item-id <item_id> --format json`
- optional `--evidence-path`, `--gate-profile queue_status_mutation`, `--dry-run`, `--force`, and `--output`

Auto-completion requires an existing in-progress queue item, satisfied dependencies, parsed dispatch result evidence, a deterministic completion recommendation, passing reported tests, passing reported smoke checks, no blockers, no high-risk/manual-only tags, a passing `queue_status_mutation` machine gate, and a transaction-log entry for the mutation.

Safety boundaries:

- queue status is the only mutation
- dry-run performs no queue mutation
- no Codex, Codex CLI, Ollama/local LLM, remote LLM, GitHub API, `gh`, network service, validation command execution, patch application, external mutation, autonomous execution, or next-item execution
- high-risk, manual-only, missing-evidence, failed-test, failed-gate, and transaction-log-blocked items remain human-reviewed

## M124 Sprint Summary and Documentation Sync Closeout

Status: Completed locally on `main` after validation.

Queue item: `m124-sprint-summary-and-documentation-sync-closeout`.

M124 closes the M110-M124 controlled automation sprint as a docs/data-only reconciliation. The sprint now has a local-only, operator-gated planning layer for advisory packages, patch intake metadata, dispatch evidence, completion recommendations, Hub review, provider probing, documentation proposals, route recommendations, artifact discovery, batch sequencing, approval review, queue mutation traceability, and Hub clarity.

Implemented in this sprint:

- M110 local LLM advisory request artifacts, without invoking local models.
- M111 approval-gated patch proposal intake records, without applying patches.
- M112 dispatch result evidence parsing from human-pasted output, without executing Codex.
- M113 queue completion recommendations, without queue mutation.
- M114 Hub Dispatch Review Panel, read-only and local-only.
- M115 local Ollama provider probe, config-only or loopback `/api/tags` only, with no prompts.
- M116 documentation-agent patch proposal artifacts, never applied automatically.
- M117 agent route recommendations in CLI/API/Hub, without dispatch.
- M118 planning reconciliation for M110-M117.
- M119 dispatch artifact registry v2.
- M120 operator batch queue sequencer v2.
- M121 human approval inventory and review ledger.
- M122 safe queue mutation transaction log.
- M123 Hub controlled automation workspace polish.
- M124 sprint closeout and documentation sync.

Current blocked/not allowed behaviors:

- no unattended Codex dispatch, Codex CLI shell-out, or automatic prompt execution
- no Ollama/local LLM prompt execution from M110-M124 planning contracts
- no remote LLM execution
- no GitHub API, `gh`, issues, PRs, workflows, or network service behavior
- no patch application or documentation-agent apply mode
- no automatic queue completion, automatic next-item execution, daemon, scheduler, or background worker

Current operator workflow:

1. Inspect project and queue state.
2. Choose one queue item and generate/inspect local planning artifacts.
3. Review route recommendation, artifact registry, dispatch review, approval ledger, evidence parser output, and completion recommendation.
4. Record human approval/rejection/needs-changes decisions when required.
5. Perform any external Codex/model/manual work outside AresForge only after operator review.
6. Parse pasted results and decide completion manually.
7. Use explicit local queue lifecycle commands only after evidence is reviewed.

Recommended next sprint:

- Keep agent boundary, registry, policy, orchestration, dry-run, and low-risk local executor work machine-gated and separate from M110-M124 planning contracts.
- Add stronger cleanup for stale local artifacts and ignored runtime outputs.
- Improve consistency of completion commit metadata for older queue records.
- Keep any future model, GitHub, or patch apply behavior behind a separate explicit approval milestone.

## M131 Machine Safety Gate Engine

Status: Completed locally on `main` after validation.

Queue item: `m131-machine-safety-gate-engine`.

M131 adds a deterministic machine gate evaluator for future autonomous workflows:

- `python -m aresforge evaluate-machine-safety-gates --item-id <item_id> --format json`
- optional `--gate-profile`, `--artifact-path`, `--patch-path`, `--execution-record`, `--output`, and `--force`

Initial gate profiles:

- `read_only_agent`
- `local_artifact_write`
- `queue_status_mutation`
- `docs_only_patch_apply`
- `local_llm_execution`
- `codex_dispatch`
- `github_sync`
- `multi_agent_orchestration`

Gate checks cover queue item existence, queue status validity, dependency satisfaction, required artifact presence, artifact schema validity, execution-record validity, forbidden capability usage, working-tree acceptability, profile file-path allowlists, docs-only patch targets, test evidence, warning thresholds, rollback/transaction-log availability, and explicit external-execution allowance where applicable.

Safety boundaries:

- evaluation only
- `execution_performed=false`
- `mutation_performed=false`
- no agent execution, Codex dispatch, local LLM/Ollama prompting, remote LLM call, GitHub API, `gh`, network service, validation command execution, patch application, queue mutation, external mutation, autonomous execution, or next-item execution
- machine gates are the replacement path for human review only when every deterministic check passes

## M123 Hub Controlled Automation Workspace Polish

Status: Completed locally on `main` after validation.

Queue item: `m123-hub-controlled-automation-workspace-polish`.

M123 polishes the Hub Queue workspace for controlled automation review without adding any execution behavior. The Hub now surfaces a clearer Controlled Automation Workspace summary, explicit boundary chips, improved advisory/review headings, and stronger empty states for:

- local queue state
- manual Codex dispatch preparation
- local LLM advisory artifacts
- approval-gated patch intake and approval ledger review
- dispatch evidence parsing
- completion recommendations
- artifact registry discovery
- route recommendation review

Safety boundaries:

- UI/readability polish only
- no new API execution endpoint
- no Codex, Ollama/local LLM prompting, remote LLM call, GitHub API, `gh`, network service, agent execution, validation command execution, patch application, source mutation beyond this milestone's UI/docs update, automatic completion, autonomous execution, or next-item execution

## M122 Safe Queue Mutation Transaction Log

Status: Completed locally on `main` after validation.

Queue item: `m122-safe-queue-mutation-transaction-log`.

M122 adds a local-only transaction log for file-backed queue mutations:

- `python -m aresforge inspect-queue-transaction-log --project-id aresforge --format json`
- optional `--item-id`, `--output`, and `--force`
- transaction log storage under `.aresforge/queue/transaction_log.json`

Transaction entries are appended after successful local queue item creation/update, routing metadata update, start, completion evidence capture, explicit completion, and closeout where practical. Each entry records timestamp, item id, project id, previous status, new status, actor/source, evidence summary, reason, queue path, and local-only execution flags.

Safety boundaries:

- inspection is read-only and advisory
- append failures are warning-only so existing queue mutations remain compatible
- no Codex, Ollama/local LLM prompting, remote LLM call, GitHub API, `gh`, network service, validation command execution, patch application, external mutation, autonomous execution, or next-item execution

## M130 Single-Agent Real Executor for Low-Risk Agents

Status: Completed locally on `main` after validation.

Queue item: `m130-single-agent-real-executor-for-low-risk-agents`.

M130 introduces the first real single-agent execution path, restricted to deterministic low-risk local agents:

- `python -m aresforge run-agent --agent-id <agent_id> --item-id <item_id> --format json`
- optional `--output`, `--force`, and `--require-machine-gates`
- stable `single_agent_real_execution` records

Allowed real-execution agents:

- `artifact-registry-agent`
- `evidence-parser-agent`
- `completion-recommendation-agent`
- `validation-agent`
- `queue-planner-agent`
- `sprint-summary-agent`

Safety boundaries:

- machine gates must pass before a record is written
- real execution writes only local execution records and local artifact files
- no Codex, Codex CLI, Ollama/local LLM, remote LLM, GitHub API, `gh`, network service, validation command execution, patch application, source mutation, documentation patch application, queue completion, autonomous execution, or next-item execution
- blocked agents include `codex-dispatch-agent`, `local-llm-advisory-agent`, `documentation-agent` when patch application is requested, `github-sync-agent`, and any agent requiring network, model execution, or code patch application

## M121 Human Approval Inventory and Review Ledger

Status: In progress locally on `main`.

Queue item: `m121-human-approval-inventory-and-review-ledger`.

M121 adds a local-only approval inventory and review ledger:

- `python -m aresforge inspect-approval-ledger --project-id aresforge --format json`
- `python -m aresforge record-artifact-review --item-id <item_id> --artifact-path <path> --decision approved|rejected|needs_changes`
- optional ledger inspection filters `--item-id`, `--artifact-path`, `--output`, and `--force`

Ledger behavior:

- inventories generated artifacts from the dispatch artifact registry
- reuses existing dispatch approval gate records as review evidence
- records explicit human artifact review decisions in a local ledger file
- reports reviewed, unreviewed, approved, rejected, needs-changes artifacts, review records, approval gaps, and next safe action
- preserves `local_only=true` and `execution_allowed=false`

Safety boundaries:

- review metadata only
- no automatic approval, queue item start, queue completion, Codex execution, agent execution, Ollama/local LLM prompting, remote LLM call, GitHub API, `gh`, network service, validation command execution, patch application, source mutation from review, external mutation, autonomous execution, or next-item execution

## M120 Operator Batch Queue Sequencer v2

Status: In progress locally on `main`.

Queue item: `m120-operator-batch-queue-sequencer-v2`.

M120 adds a local-only batch sequencing recommendation:

- `python -m aresforge plan-operator-batch-v2 --project-id aresforge --format json`
- optional `--limit`, `--include-blocked`, `--output`, and `--force`
- stable `operator_batch_sequence_v2` records

Sequencer behavior:

- recommends an ordered batch from proposed and ready queue items
- respects dependencies, priority, artifact readiness, approval gates, and lane grouping
- reports dependency warnings, approval warnings, artifact warnings, blocked items, operator checklist, and next safe action
- preserves `execution_performed=false`, `queue_mutation_performed=false`, `local_only=true`, and `execution_allowed=false`

Safety boundaries:

- advisory sequencing only
- no queue item start, Codex execution, agent execution, Ollama/local LLM prompting, remote LLM call, GitHub API, `gh`, network service, validation command execution, patch application, queue mutation, external mutation, automatic completion, or next-item execution

## M129 Single-Agent Dry-Run Executor

Status: Completed locally on `main` after validation.

Queue item: `m129-single-agent-dry-run-executor`.

M129 adds the first single-agent dry-run execution record path:

- `python -m aresforge run-agent-dry-run --agent-id <agent_id> --item-id <item_id> --format json`
- optional `--plan-path`, `--output`, and `--force`
- stable `single_agent_dry_run` execution records

Supported deterministic dry-run agents:

- `artifact-registry-agent`
- `evidence-parser-agent`
- `completion-recommendation-agent`
- `validation-agent`
- `sprint-summary-agent`
- `queue-planner-agent`

Safety boundaries:

- dry-run only
- local deterministic inspection, validation planning, summarization, and artifact-record generation only
- no Codex, Codex CLI, Ollama, local LLM, remote LLM, GitHub API, `gh`, network service, validation command execution, patch application, source mutation, queue mutation from the dry-run, autonomous execution, or next-item execution
- unsupported agents are blocked
- forbidden capabilities are reported as blocked in every execution record
- `mutation_performed=true` only when the operator explicitly writes the dry-run record with `--output`

## Current Phase

M119 implements the Dispatch Artifact Registry Index v2 as a local-only artifact discovery layer across M109-M117 planning outputs. It inventories records and flags missing folders, stale item references, duplicates, blocked artifacts, and review-required artifacts without executing anything.

## Current Goal

M119 adds `inspect-artifact-registry --format json`. The command emits `dispatch_artifact_registry_v2` records with artifact counts by type, source directories, missing expected artifacts, stale artifacts, duplicate artifacts, blocked artifacts, review-required artifacts, `local_only=true`, `execution_allowed=false`, and next safe action.

## M119 Dispatch Artifact Registry Index v2

Status: In progress locally on `main`.

Queue item: `m119-dispatch-artifact-registry-index-v2`.

M119 adds:

- `inspect-artifact-registry --format json`
- optional `--project-id`, `--item-id`, `--artifact-type`, `--output`, and `--force`
- stable `dispatch_artifact_registry_v2` records

Supported artifact sources:

- manual Codex dispatch preparation records
- Codex prompt dispatch artifacts
- local LLM advisory request artifacts
- approval-gated patch intake records
- parsed dispatch result evidence
- queue completion recommendations
- documentation-agent patch proposals and patch sidecars
- agent route recommendations

Safety boundaries:

- local filesystem and queue metadata inspection only
- no Codex, Codex CLI, Ollama, local LLM, agent runtime, GitHub API, `gh`, network service, workflow, patch application, source mutation, queue mutation, automatic completion, or next-item execution
- registry records are advisory inventory metadata only

## M118 Post-Automation Planning Reconciliation

Status: In progress locally on `main`.

Queue item: `m118-post-automation-planning-reconciliation`.

Reconciled milestones:

- M110 Local LLM Advisory Artifact Generator prepares advisory request packages only; it does not invoke Ollama or local models.
- M111 Approval-Gated Patch Intake Contract records proposed patch review metadata only; it does not apply patches.
- M112 Dispatch Result Evidence Parser parses human-pasted Codex completion text into local evidence records only.
- M113 Queue Item Auto-Completion Recommendation Engine recommends whether an operator may complete work; it does not mutate queue status.
- M114 Hub Dispatch Review Panel displays local dispatch/advisory/evidence/recommendation artifacts read-only.
- M115 Local Ollama Provider Probe Integration performs config-only or loopback `/api/tags` discovery; it sends no prompts and requests no model output.
- M116 Documentation Agent Patch Proposal Generator creates documentation patch proposals for review; generated proposals are not applied.
- M117 Agent Routing Decision Dashboard recommends an advisory lane and required artifacts; it does not dispatch or execute.

Current boundary:

- AresForge may prepare local artifacts, dry-run validators, advisory recommendations, handoff packages, approval records, and evidence records.
- AresForge must not perform unattended Codex execution, Ollama/local LLM prompting, agent execution, GitHub/`gh` calls, network workflow behavior, patch application, automatic queue completion, or automatic next-item execution.
- All current automation-facing surfaces remain local-only and operator-gated.

Current operator workflow:

- inspect queue/project state
- generate or inspect advisory artifacts for one item
- review approval, dispatch, evidence, and completion recommendations in the Hub or CLI
- manually decide whether to hand work to an external tool or approve a patch proposal
- parse external result evidence after a human-pasted completion report
- use a separate explicit queue completion command only after validation evidence is reviewed

Remaining gaps:

- no real agent runtime
- no automated Codex or local LLM execution path
- no patch apply workflow
- no GitHub issue, PR, workflow, or `gh` integration
- no automatic queue completion, follow-on dispatch, or autonomous multi-item execution

Next recommended milestones:

- M119 should define the next docs/data checkpoint or operator evidence ledger hardening pass.
- A future runner milestone must remain separate from M118 and require explicit operator approval before any execution behavior exists.

## M117 Agent Routing Decision Dashboard

Status: In progress locally on `main`.

Queue item: `m117-agent-routing-decision-dashboard`.

M117 adds:

- `recommend-agent-route --item-id <item_id>`
- optional `--format json`, `--output`, and `--force`
- `GET /api/agent-route-recommendation?item_id=<item_id>`
- Hub Queue panel Agent Routing Decision Dashboard
- stable `agent_route_recommendation` records

Recommendation behavior:

- reads local queue metadata for one item
- classifies documentation, local LLM advisory, coding/dashboard, and validation signals
- recommends an advisory lane such as `codex_prompt_artifact`, `local_llm_advisory_artifact`, `documentation_agent_patch_proposal`, `validation_agent_dry_run`, or `human_operator_manual_review`
- records alternatives, routing reasons, required artifacts before dispatch, approval requirements, suitability flags, and next safe action

Safety boundaries:

- no execute buttons in the Hub panel
- no Codex, Codex CLI, Ollama, local LLM, agent runtime, GitHub API, `gh`, network service, workflow, patch application, source mutation, queue mutation, automatic completion, or next-item execution
- recommendations are advisory only and keep `human_operator_required=true`, `dispatch_performed=false`, and `execution_allowed=false`

## M128 Agent Orchestration Plan Builder

Status: Completed locally on `main` after validation.

Queue item: `m128-agent-orchestration-plan-builder`.

M128 adds:

- `build-agent-orchestration-plan --item-id <item_id> --format json`
- optional `--agent-id`, `--execution-target dry-run|real`, `--queue-path`, `--output`, and `--force`
- machine-readable `agent_orchestration_plan` records

Plan behavior:

- reads one local queue item
- reads the M126 declarative agent registry
- reads the M127 LLM decision policy recommendation
- chooses an ordered set of agent steps
- records required artifacts, dependency checks, machine gates, blocked state, blocked reasons, autonomy level, and next safe action
- refuses output overwrite unless `--force` is explicit
- blocks `--execution-target real` because no M128 runner exists

Validation:

- `python -m pytest tests/test_cli.py` passed (`198 passed`)
- `python -m pytest tests/test_agent_orchestration_plan_builder.py` passed (`6 passed`)
- `python -m pytest tests/test_llm_decision_policy.py` passed (`7 passed`)
- `python -m pytest tests/test_agent_registry.py` passed (`9 passed`)
- `git diff --check` passed with CRLF warnings only
- smoke checks passed for `build-agent-orchestration-plan`, `inspect-local-project-report`, and `inspect-local-queue-agent-summary`

Safety boundaries:

- no agent execution
- no Codex, Codex CLI, Ollama, local LLM, remote LLM, documentation-agent runtime, GitHub API, `gh`, network service, workflow, patch application, source mutation, queue mutation from the plan, validation command execution, autonomous execution, or next-item execution
- future runners must be separate explicit operator-approved milestones

## M127 LLM Decision Policy v1

Status: Completed locally on `main` after validation.

Queue item: `m127-llm-decision-policy-v1`.

Implementation commit: pending final commit.

M127 adds:

- `recommend-llm-decision --item-id <item_id> --format json`
- optional `--agent-id`, `--task-type`, `--risk-level`, `--mutation-scope`, `--output`, and `--force`
- machine-readable `llm_decision_policy_v1` records

Supported lanes:

- `no_llm_required`
- `local_llm_reasoning`
- `local_llm_coding_review`
- `codex_coding`
- `codex_reasoning`
- `remote_high_value_reasoning`
- `remote_low_cost_reasoning`
- `documentation_agent`
- `validation_agent`
- `github_sync_agent`

Policy behavior:

- reads local queue metadata and optional CLI overrides
- considers task type, risk, mutation scope, code/docs/planning shape, context size, repo-aware coding need, deterministic validation need, local-only requirement, GitHub/network requirement, test verifiability, and autonomous execution hints
- recommends a future lane/provider/model profile only
- records `execution_performed=false` for every recommendation

Safety boundaries:

- no Codex, Codex CLI, Ollama, local LLM, remote LLM, documentation-agent, validation-agent, GitHub API, `gh`, network service, workflow, patch application, source mutation, queue mutation, autonomous execution, or next-item execution
- `autonomy_allowed` is a future-policy hint only and is not execution authorization
- machine and human gates remain advisory metadata until a later explicit runner consumes them

## M116 Documentation Agent Patch Proposal Generator

Status: Completed locally on `main` after validation.

Queue item: `m116-documentation-agent-patch-proposal-generator`.

Implementation commit: `0d8bbdf`.

M116 adds:

- `generate-doc-agent-patch-proposal --item-id <item_id>`
- optional `--format json`
- optional `--output`, `--force`, `--include-roadmap`, `--include-context`, and `--include-operator-docs`
- stable `documentation_agent_patch_proposal` records
- local proposed patch files under `artifacts/documentation_agent/patch_proposals`

Proposal behavior:

- reads local queue state for the requested item
- reviews selected source-of-truth documentation groups
- detects missing item, milestone, title, or operator command coverage
- writes a structured proposal artifact and a patch proposal text file
- requires human review and later approval before any M111 patch intake

Safety boundaries:

- generated proposals are not applied
- no documentation-agent runtime execution
- no model, Codex, Ollama, local LLM, GitHub API, `gh`, network service, workflow, source mutation, queue mutation, automatic completion, or next-item execution
- patch application remains unavailable until a separate explicit operator-approved apply workflow exists

## M115 Local Ollama Provider Probe Integration

Status: Completed locally on `main` after validation.

Queue item: `m115-local-ollama-provider-probe-integration`.

Implementation commit: `9913605`.

M115 adds:

- `probe-local-ollama-provider`
- optional `--format json`
- optional `--output`, `--force`, `--no-network`, and `--config`
- stable `local_ollama_provider_probe` records

Probe behavior:

- reads the local LLM environment contract or an explicit local config file
- reports expected Ollama configuration and configured reasoning/coding/fallback profiles
- in `--no-network` mode, performs configuration-only inspection
- otherwise calls only loopback `http://localhost`, `http://127.0.0.1`, or `http://[::1]` `/api/tags`
- treats offline Ollama as warning metadata, not normal project readiness failure

Safety boundaries:

- no prompts are sent
- no generation, chat, completion, coding, reasoning, or advisory endpoint is called
- no model output is requested or used
- no Codex, GitHub API, `gh`, agent execution, documentation-agent execution, workflow, patch application, queue mutation, or repository mutation
- non-loopback provider URLs are blocked for network probing unless the operator reruns in config-only `--no-network` mode

## M114 Hub Dispatch Review Panel

Status: Completed locally on `main` after validation.

Queue item: `m114-hub-dispatch-review-panel`.

Implementation commit: `d5ffb6b`.

M114 adds:

- `GET /api/dispatch-review`
- optional `item_id` and `limit` query filters
- Queue panel Dispatch Review section

The panel shows:

- item id
- milestone
- artifact type
- artifact path and existence
- blocked status and blocked reasons
- next safe action
- operator checklist
- local-only, read-only, execution, queue mutation, and patch application flags

Review sources:

- manual dispatch preparation records
- local LLM advisory request artifacts
- patch proposal intake records
- dispatch result evidence records
- queue completion recommendation records

Safety boundaries:

- read-only Hub display and artifact scan only
- no execution endpoints
- no Codex, Codex CLI, Ollama, local LLM, documentation-agent, GitHub API, `gh`, network service, external-agent, workflow, issue, PR, or patch application behavior
- no queue completion automation, approval mutation, handoff automation, or next-item execution

## M126 Agent Registry

Status: Completed locally on `main` after validation.

Queue item: `m126-agent-registry`.

Implementation commit: pending final commit.

M126 adds:

- `inspect-agent-registry --format json`
- `inspect-agent-registry --agent-id <agent_id> --format json`
- `inspect-agent-registry --safety-class <safety_class> --format json`
- `inspect-agent-registry --autonomy-level <level> --format json`
- optional `--output` and `--force`

Initial registered agents:

- `queue-planner-agent`
- `codex-dispatch-agent`
- `local-llm-advisory-agent`
- `documentation-agent`
- `evidence-parser-agent`
- `completion-recommendation-agent`
- `validation-agent`
- `github-sync-agent`
- `sprint-summary-agent`
- `artifact-registry-agent`
- `approval-ledger-agent`
- `transaction-log-agent`

Each registry record includes:

- `agent_id`, `display_name`, `description`, `agent_type`
- supported item types, required inputs, optional inputs, and produced artifacts
- allowed and forbidden capabilities
- mutation, network, and model scopes
- safety class and autonomy level
- default execution mode and dry-run/real-run flags
- machine gate and evidence requirements
- source documentation references

Registry output includes:

- `registry_type=agent_registry`
- `generated=true`
- `agent_count`
- filtered `agents`
- `agents_by_type`, `agents_by_safety_class`, and `agents_by_autonomy_level`
- `blocked_agents`, `executable_agents`, and `dry_run_only_agents`
- `local_only=true`
- `execution_performed=false`
- next safe action

Safety boundaries:

- declarative registry only
- no agent execution
- no Codex, Ollama, local LLM, documentation-agent, GitHub API, `gh`, network service, patch application, workflow, daemon, watcher, scheduler, or external-agent execution
- no autonomous workflow creation
- all registered agents have `can_run_real=false` until a later explicit operator-approved runner exists

## M113 Queue Item Auto-Completion Recommendation Engine

M113 implements the Queue Item Auto-Completion Recommendation Engine. It evaluates local dispatch evidence and known completion requirements, then recommends whether an operator may safely complete a queue item without mutating queue state.

## M113 Goal

M113 adds `recommend-queue-completion` for local-only recommendation records. The command consumes an M112 dispatch evidence JSON file, verifies required evidence, tests, smoke checks, warnings/blockers, and commit hash presence, and preserves `queue_mutation_performed=false`.

## M113 Status

Status: Completed locally on `main` after validation.

Queue item: `m113-queue-item-auto-completion-recommendation-engine`.

Implementation commit: `a988af7`.

M113 adds:

- `recommend-queue-completion --item-id <item_id> --evidence-path <path>`
- `recommend-queue-completion --item-id <item_id> --evidence-path <path> --format json`
- optional `--output`, `--force`, and `--queue-path`

The recommendation record includes:

- `recommendation_record_type=queue_completion_recommendation`
- recommended/blocked status and blocked reasons
- queue identity fields: `item_id`, `title`, `project_id`, and `milestone`
- local evidence path
- evidence validity
- required evidence presence and missing evidence
- tests and smoke checks passed indicators
- warnings or blockers
- commit hash presence
- confidence
- `operator_decision_required=true`
- `queue_mutation_performed=false`
- `local_only=true`
- `execution_allowed=false`
- next safe action

Recommendation behavior:

- reads local queue state and a local M112 `dispatch_result_evidence` JSON file
- requires valid evidence for the requested item
- requires passed tests, passed smoke checks, changed files, change summary, and commit hash evidence
- treats queue `completion_requires` and `evidence_required` as additional local evidence requirements
- blocks recommendations when evidence is missing, invalid, failed, mismatched, or reports severe warnings/blockers

Safety boundaries:

- no queue mutation or automatic completion
- no Codex execution or Codex CLI shell-out
- no local LLM, Ollama, documentation-agent, GitHub API, `gh`, network service, external-agent, workflow, issue, PR, or patch application behavior
- no automatic handoff, approval mutation, or next-item execution

## M125 Agent Runtime Boundary Contract

Status: Completed locally on `main` after validation.

Queue item: `m125-agent-runtime-boundary-contract`.

Implementation commit: pending final commit.

M125 adds:

- `inspect-agent-runtime-boundary`
- `inspect-agent-runtime-boundary --format json`
- `inspect-agent-runtime-boundary --format markdown`

The contract output includes:

- `contract_type=agent_runtime_boundary`
- `generated=true`
- `agent_boundary_version`
- supported execution modes, autonomy levels, and safety classes
- allowed and forbidden capability catalogs
- mutation, network, and model scope catalogs
- evidence requirements
- default runtime limits, timeout policy, and retry policy
- `local_only=true`
- `execution_performed=false`
- next safe action

Boundary model:

- an AresForge agent must declare `agent_id`, `agent_type`, `execution_mode`, `input_contract`, `output_contract`, `allowed_capabilities`, `forbidden_capabilities`, `mutation_scope`, `network_scope`, `model_scope`, `timeout_policy`, `retry_policy`, `evidence_requirements`, `safety_class`, and `autonomy_level`
- requested capabilities must be intersected with the allowed catalog and blocked by the forbidden catalog
- mutation, network, and model access must be scoped before any future runner can start
- timeout, retry, and evidence policies are required before runtime handoff or completion recommendation

Safety boundaries:

- no real agent execution
- no Codex, Ollama, local LLM, documentation-agent, GitHub API, `gh`, network service, patch application, workflow, daemon, watcher, scheduler, or external-agent execution
- no queue auto-completion, automatic handoff, or next-item execution
- future runners must be separate explicit operator-approved milestones

## M112 Dispatch Result Evidence Parser

Status: Completed locally on `main` after validation.

Queue item: `m112-dispatch-result-evidence-parser`.

Implementation commit: `5088c95`.

M112 adds:

- `parse-dispatch-result-evidence --item-id <item_id> --result-path <path>`
- `parse-dispatch-result-evidence --item-id <item_id> --result-path <path> --format json`
- optional `--output`, `--force`, and `--queue-path`

The evidence record includes:

- `evidence_record_type=dispatch_result_evidence`
- parsed/blocked status and blocked reasons
- queue identity fields: `item_id`, `title`, `project_id`, and `milestone`
- local result path and existence
- parsed `files_changed`, `what_changed`, `tests_reported`, `smoke_checks_reported`, `warnings_or_blockers`, and `commit_hash`
- `validation_confidence`
- `completion_recommendation`
- `human_review_required=true`
- `local_only=true`
- `execution_allowed=false`
- next safe action

Parser behavior:

- recognizes common markdown sections such as Files Changed, What Changed, Tests Run, Smoke Checks, Warnings Or Blockers, and Commit Hash
- infers file paths, validation lines, smoke lines, and commit hashes when sections are absent
- treats missing sections as warnings instead of crashes
- refuses to overwrite output files unless `--force` is provided

Safety boundaries:

- no Codex execution or Codex CLI shell-out
- no local LLM, Ollama, documentation-agent, external-agent, GitHub API, `gh`, network, issue, PR, or workflow behavior
- no patch application or repository mutation from parsed output
- no automatic queue completion, approval mutation, handoff, or next-item execution

## M111 Approval-Gated Patch Intake Contract

Status: Completed locally on `main` after validation.

Queue item: `m111-approval-gated-patch-intake-contract`.

Implementation commit: `98ec90c`.

M111 adds:

- `intake-patch-proposal --item-id <item_id> --patch-artifact <path>`
- `intake-patch-proposal --item-id <item_id> --patch-artifact <path> --format json`
- optional `--approval-id`, `--output`, `--force`, `--queue-path`, and `--approval-path`

The intake record includes:

- `intake_record_type=patch_proposal_intake`
- `accepted_for_review`, `blocked`, and `blocked_reasons`
- queue identity fields: `item_id`, `title`, `project_id`, and `milestone`
- patch artifact path/existence and patch summary
- approval gate id/status
- `operator_review_required=true`
- `patch_application_allowed=false`
- `patch_application_performed=false`
- `local_only=true`
- `execution_allowed=false`
- next safe action

Ready behavior:

- requires a known queue item
- requires an existing local patch artifact
- requires an approval gate for the item/patch artifact or the provided `--approval-id`
- requires approval status `approved_for_manual_handoff`
- records review metadata only

Blocked behavior:

- missing queue item blocks
- missing patch artifact blocks
- missing approval gate blocks
- rejected, pending, needs-revision, missing, or unknown approval status blocks
- output overwrite blocks unless `--force` is provided

Safety boundaries:

- no patch application
- no repository file mutation
- no Codex, local LLM, documentation-agent, or external-agent execution
- no GitHub API, `gh`, network service, issue, PR, or workflow behavior
- no automatic queue completion, approval mutation, handoff, or next-item execution

## M110 Local LLM Advisory Artifact Generator

Status: Completed locally on `main` after validation.

Queue item: `m110-local-llm-advisory-artifact-generator`.

Implementation commit: `f4e81ff`.

M110 adds:

- `generate-local-llm-advisory-artifact`
- `generate-local-llm-advisory-artifact --format json`
- optional `--output`, `--force`, `--model-profile`, `--reasoning-scope`, `--queue-path`, and `--registry-path`

The generated artifact contract includes:

- `artifact_type=local_llm_advisory_request`
- generated/blocked status and blocked reasons
- queue identity fields: `item_id`, `title`, `project_id`, `milestone`, and `queue_status`
- requested model profile and reasoning scope
- source documents, queue context, advisory prompt, expected response shape, and operator review checklist
- `local_only=true`
- `execution_allowed=false`
- `local_llm_execution_performed=false`
- `codex_execution_performed=false`
- `network_execution_performed=false`
- `patch_application_allowed=false`
- next safe action

Ready behavior:

- requires the M97 selected lane to be `local_llm_advisory`
- requires the M97 plan to be local-only and unblocked
- requires `execution_allowed=false`
- writes a stable local JSON artifact to `artifacts/local_llm_advisory/requests` if `--output` is omitted
- refuses to overwrite explicit output files unless `--force` is provided

Blocked behavior:

- blocks Codex prompt, local coding draft, documentation-agent, manual-only, missing, or unsafe lanes
- blocks M97 plan blockers
- blocks source plans with `local_only` other than true
- blocks source plans with `execution_allowed` other than false
- blocks output overwrite attempts without `--force`

Safety boundaries:

- local-only request artifact generation
- no Ollama API calls or local model inference
- no Codex execution or Codex CLI shell-out
- no GitHub API, `gh`, network service, documentation-agent, or external-agent invocation
- no patch application or source mutation from advisory output
- no automatic queue start, completion, approval mutation, handoff, or next-item execution

M110 relationship:

- M110 builds on M97/M99 by turning the advisory lane into a structured request artifact only.
- M110 does not inherit M85 optional provider run behavior.
- Any future local LLM invocation remains a separate operator-approved milestone.

## M109 Manual Codex Dispatch Runner Contract

Status: Completed locally on `main` after validation.

Queue item: `m109-manual-codex-dispatch-runner-contract`.

Implementation commit: `bfa4139`.

M109 adds:

- `prepare-manual-codex-dispatch`
- `prepare-manual-codex-dispatch --format json`
- optional `--artifact-path`, `--approval-id`, `--queue-path`, `--registry-path`, `--artifact-root`, `--approval-path`, `--output`, and `--force`

The preparation record includes:

- `prepared`, `blocked`, and `blocked_reasons`
- queue identity fields: `item_id`, `title`, `project_id`, `milestone`, and `queue_status`
- `selected_lane`, `codex_artifact_path`, approval id/status, manual dispatch steps, operator checklist, expected evidence after manual run, `local_only`, `execution_allowed=false`, `codex_execution_performed=false`, and `next_safe_action`

Ready behavior:

- requires `selected_lane=codex_prompt_artifact`
- requires `local_only=true`
- requires `execution_allowed=false` on the M97 plan and discovered artifact metadata
- requires an existing Codex prompt artifact
- requires an M101 approval gate with `approved_for_manual_handoff`
- requires the queue item to be lifecycle-safe and not done/blocked

Blocked behavior:

- blocks non-Codex lanes
- blocks missing Codex prompt artifacts
- blocks missing approval gates as `needs_approval`
- blocks approval statuses other than `approved_for_manual_handoff`
- blocks done, blocked, cancelled, closed, or otherwise unsafe queue states
- blocks source plans/artifacts that are not local-only or allow execution

Safety boundaries:

- local-only preparation record
- no Codex execution or Codex CLI shell-out
- no patch application or source mutation from generated output
- no GitHub API, `gh`, network service, Ollama/local LLM, documentation-agent, or external-agent invocation
- no automatic queue start, completion, handoff, approval mutation, or next-item execution

M109 to M110/M111 relationship:

- M109 prepares manual Codex handoff only after a reviewed M98 prompt artifact exists.
- M110 generates local LLM advisory request artifacts without inheriting Codex execution behavior.
- M111 remains the future approval-gated patch intake contract for any returned Codex patch/proposal evidence.

## M108 Sprint Closeout and Next-Stage Automation Plan

Status: Completed locally on `main` after validation.

Queue item: `m105-post-batch-documentation-reconciliation-m108-sprint-closeout-and-next-stage-automation-plan`.

Implementation commit: `549c5fc`.

M108 inspection inputs:

- `inspect-local-project-report`
- `inspect-local-queue-agent-summary`
- `inspect-project-queue --project-id aresforge`
- `plan-operator-batch --project-id aresforge --limit 10 --format json`
- `inspect-dispatch-artifacts --format json`
- `generate-safe-dispatch-handoff --format json`
- `generate-handoff-package`

Sprint closeout summary:

- M99-M100 provide lane-specific dry-run validators for local LLM advisory and documentation-agent review.
- M101 provides local human approval gate records and a read-only Hub approval surface.
- M102 enforces dependency and evidence locking for queue start/completion.
- M103 confirms AresForge as its own first managed project.
- M104 proposes local-only operator batches without execution.
- M105 reconciled source docs after M99-M104.
- M106 indexes local dispatch artifacts and approval status.
- M107 packages queue state, dispatch plans, artifact index data, approval status, and operator instructions for safe handoff.

Current report posture:

- The queue has no blocked items.
- M108 is complete.
- M96 remains proposed as older manual planning context and should not be treated as a blocker for M97-M108 evidence.
- `plan-operator-batch --project-id aresforge --limit 10 --format json` proposes only M96 when M108 is not considered, because M99-M107 are done.
- `inspect-dispatch-artifacts --format json` currently reports zero artifacts and warning-only missing known artifact folders under `artifacts/`.
- `generate-safe-dispatch-handoff --format json` remains local-only/read-only and reports `execution_allowed=false`.
- `generate-handoff-package` remains local-only/read-only but still reports untracked `.codex-pytest-cache/` and old pytest temp permission warnings.

Remaining gaps:

- No dispatch artifact index entries exist yet because no M98-M100 artifacts are present under the default artifact folders.
- Approval gate data exists, but it is not yet a complete per-artifact review inventory.
- Safe dispatch handoff is a context package, not a runner or execution approval.
- Automated Codex dispatch, local LLM advisory artifact generation, approval-gated patch intake, documentation-agent patch proposal generation, dashboard execution controls, and auto-completion recommendations remain future work.

Next recommended controlled automation batch:

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

Batch guardrails:

- Keep M109-M114 contract/report/review-first before any widened execution.
- Treat M115 as provider probing only unless an explicit later milestone authorizes inference.
- Keep M116 proposal-only and require M111/M112 evidence before any patch intake.
- Use M118 to reconcile docs after the automation-planning batch.
- Do not seed the entire batch automatically; choose and start one approved milestone at a time.

Safety boundaries:

- docs/data reconciliation only
- no new runtime feature implementation
- no Codex execution
- no Ollama or local model invocation
- no documentation-agent execution or automatic documentation mutation
- no GitHub API, `gh`, network service, workflow, issue, PR, external-agent, or patch application
- no automatic queue start, completion, dispatch, handoff, or next-item execution

## M107 Safe Dispatch Handoff Package

Status: Completed locally on `main` after validation.

Queue item: `m105-post-batch-documentation-reconciliation-m107-safe-dispatch-handoff-package`.

Implementation commit: `99c79b7`.

M107 adds:

- `generate-safe-dispatch-handoff`
- `generate-safe-dispatch-handoff --format json`
- optional `--project-id`, `--queue-path`, `--registry-path`, `--artifact-root`, `--approval-path`, `--output`, and `--force`
- a local-only handoff package that bundles:
  - repo path, branch, and HEAD
  - active project summary
  - queue summary and next recommended items
  - M97 dispatch plan summaries for active/proposed/ready/blocked items
  - M106 artifact index summary
  - M101 approval gate summary
  - warnings, blockers, local-only boundaries, and operator next actions

Safety boundaries:

- read-only by default
- optional output writes one local file only
- no artifact execution
- no Codex execution
- no Ollama or local model invocation
- no documentation-agent execution or documentation mutation
- no GitHub API, `gh`, network service, workflow, issue, PR, external-agent, or patch application
- no queue mutation, approval mutation, automatic dispatch, automatic handoff, or automatic next-item execution
- `execution_allowed: false` remains explicit

M107 to M108 relationship:

- M107 packages the current dispatch posture for operator review and new chat handoffs.
- M108 is expected to reconcile sprint closeout and next-stage automation planning after this safe handoff layer exists.

## M106 Dispatch Artifact Index/Report

Status: Completed locally on `main` after validation.

Queue item: `m105-post-batch-documentation-reconciliation-m106-dispatch-artifact-index-report`.

Implementation commit: `fc77cd2`.

M106 adds:

- `inspect-dispatch-artifacts`
- `inspect-dispatch-artifacts --format json`
- optional `--project-id`, `--artifact-root`, and `--approval-path`
- local scanning of known artifact output folders:
  - `artifacts/codex_prompt_dispatch/generated`
  - `artifacts/local_llm_advisory/dry_runs`
  - `artifacts/documentation_agent/dry_runs`
- approval gate status joining from `.aresforge/dispatch_approval_gates.json`

Report output includes:

- stable `artifact_id`
- `artifact_type`
- `item_id`
- `dispatch_lane`
- `file_path`
- `created_at` and `modified_at`
- `approval_gate_status` and `approval_id` when available
- `local_only: true`
- `read_only: true`
- `execution_allowed: false`
- `next_safe_action`

Safety boundaries:

- local filesystem and approval gate inspection only
- no artifact execution
- no Codex execution
- no Ollama or local model invocation
- no documentation-agent execution or documentation mutation
- no GitHub API, `gh`, network service, workflow, issue, PR, external-agent, or patch application
- no queue mutation, approval mutation, or automatic handoff

M106 to M107 relationship:

- M106 indexes the artifacts and approval states an operator should review before handoff.
- M107 is expected to package safe handoff materials, still with `execution_allowed=false`.

## M105 Post-Batch Documentation Reconciliation

Status: Completed locally on `main` after validation.

Queue item: `m96-post-sprint-planning-and-prioritization-m105-post-batch-documentation-reconciliation`.

Implementation commit: `962ac8c`.

M105 reconciliation scope:

- reviewed completed M99-M104 work and queue evidence
- reconciled source-of-truth docs with implemented local-only commands and data contracts
- corrected stale future-tense claims for M100-M104 where implementation is now complete
- updated roadmap guidance for the next recommended sequence
- updated local project state to reflect M105 documentation reconciliation
- documented persistent local warning noise from `.codex-pytest-cache/` and inaccessible old pytest temp directories

Current implemented M99-M104 surface:

- M99: `validate-local-llm-advisory-dry-run`
- M100: `validate-documentation-agent-dry-run`
- M101: dispatch approval gate records and read-only Hub panel
- M102: queue dependency/completion locking plus `inspect-queue-consistency`
- M103: `inspect-self-managed-project`
- M104: `plan-operator-batch`

M105 safety boundaries:

- documentation and local data reconciliation only
- no new runtime feature implementation
- no Codex execution
- no Ollama or local model invocation
- no documentation-agent execution or automatic documentation mutation
- no GitHub API, `gh`, network service, workflow, issue, PR, external-agent, or patch application
- no automatic next-item execution

Recommended next sequence after M105:

- M106 Dispatch Artifact Index/Report
- M107 Safe Dispatch Handoff Package
- M108 Sprint Closeout and Next-Stage Automation Plan
- M109 Manual Codex Dispatch Runner Contract
- M110 Local LLM Advisory Artifact Generator
- M111 Approval-Gated Patch Intake Contract

## M104 Operator Batch Planner v1

Status: Completed locally on `main` after validation.

Queue item: `m104-operator-batch-planner-v1`.

Implementation commit: `864af13`.

M104 adds:

- `plan-operator-batch --project-id aresforge`
- `plan-operator-batch --project-id aresforge --limit 10`
- `plan-operator-batch --project-id aresforge --limit 10 --format json`
- ordered local sprint batch planning from `.aresforge/queue/work_items.json`
- exclusion of `done` items
- blocking of unresolved dependency and blocked status items
- intra-batch ordering support when a dependency is planned earlier in the same proposed batch
- safety classification per planned item:
  - `manual_only`
  - `codex_artifact_possible`
  - `local_llm_dry_run_possible`
  - `documentation_dry_run_possible`
  - `blocked`

Planner output includes:

- `batch_id`, `generated_at`, `project_id`
- `proposed_items`, `excluded_items`, `blocked_items`
- `warnings`
- `recommended_next_action`
- `local_only: true`
- `read_only: true`
- `execution_allowed: false`

Safety boundaries:

- local queue inspection only
- no queue seeding by default
- no queue mutation
- no Codex execution
- no Ollama or local model invocation
- no documentation-agent execution
- no GitHub API, `gh`, network service, workflow, issue, PR, external-agent, or patch application
- no automatic next-item execution

M104 to M105 relationship:

- M104 proposes the safe ordered batch before an operator sprint.
- M105 reconciles planned work, completed M99-M104 work, evidence, queue state, and source-of-truth docs after the batch.

## M103 AresForge Self-Managed Project Seed Review

Status: Completed locally on `main` after validation.

Queue item: `m103-aresforge-self-managed-project-seed-review`.

Implementation commit: `f1b32ca`.

M103 adds:

- `inspect-self-managed-project --project-id aresforge`
- `inspect-self-managed-project --project-id aresforge --format json`
- local-only/read-only self-managed identity reporting
- gap detection for missing metadata, missing docs, missing queue items, stale active milestone markers, repo path mismatch, branch mismatch, and unsafe execution assumptions

AresForge remains the first managed project:

- `project_id: aresforge`
- primary repo path: `C:\Projects\aresforge`
- active project: `aresforge`
- queue source of truth: `.aresforge/queue/work_items.json`
- managed project registry: `.aresforge/projects/projects.json`

M103 to M104 relationship:

- M103 does not plan or seed a batch.
- M103 tells the operator whether the self-managed seed is coherent enough for M104 batch planning.
- M104 can consume the M103 report rather than re-deriving project identity and queue/doc gaps.

## M102 Queue Dependency and Completion Locking Hardening

Status: Completed locally on `main` after validation.

Queue item: `m102-queue-dependency-and-completion-locking-hardening`.

Implementation commit: `ea1d719`.

M102 adds or hardens:

- queue dependency aliases through `dependencies` and `depends_on`
- explicit completion lock fields through `completion_requires` and `evidence_required`
- start blocking when dependencies or blocked-by items are unresolved
- completion blocking when dependencies are unresolved
- completion blocking when explicit evidence requirements are missing
- read-only consistency inspection with `inspect-queue-consistency --project-id <project_id> [--format json|markdown]`

Safety boundaries:

- local queue file-backed inspection and lifecycle mutation only
- no Codex, Ollama, local model, documentation-agent, GitHub API, `gh`, network, external agent, patch application, or automatic dispatch execution
- historical completed queue items without explicit M102 evidence requirements remain valid and are not retroactively broken

M102 relationship to future dispatch:

- M101 approval records do not bypass queue locks.
- Future dispatch or apply workflows must satisfy dependency, evidence, and approval gates before any separate execution milestone can be introduced.
- M102 prepares the lock model that M103+ workflows can consume without weakening local operator control.

## M101 Human Approval Gate UI/Data Contract

Status: Completed locally on `main` after validation.

Queue item: `m101-human-approval-gate-ui-data-contract`.

Implementation commit: `da90ed3`.

M101 adds a file-backed dispatch approval gate registry and commands:

- `create-dispatch-approval-gate --item-id <item_id> --artifact-type <type>`
- `inspect-dispatch-approval-gate --approval-id <approval_id>`
- `update-dispatch-approval-gate --approval-id <approval_id> --status <status> --review-notes <text>`
- `--format json` support for machine-readable output
- a read-only Hub approval gate panel under the Queue AI/action review area

Stable approval gate fields:

- `approval_id`, `item_id`, `artifact_type`, `artifact_path`, `dispatch_lane`
- `reviewer`, `review_notes`, `checklist`
- `created_at`, `updated_at`, `status`
- `local_only: true`
- `execution_allowed: false`
- `next_safe_action`

Supported statuses:

- `pending_review`
- `approved_for_manual_handoff`
- `rejected`
- `needs_revision`

M101 approval behavior:

- records approval state for dispatch artifacts and dry-run outputs only
- keeps `execution_allowed=false` even when status is `approved_for_manual_handoff`
- treats approval as permission for manual operator handoff review, not automatic execution
- blocks invalid statuses
- requires future dispatch or apply workflows to check approval records before execution can be introduced

M101 to M102 relationship:

- M101 defines the human approval data record that future dispatch workflows must satisfy.
- M102 remains planned to harden dependency, active-item, completion, and evidence locks so approved artifacts cannot bypass queue locking or completion rules.

## M100 Documentation Agent Dry-Run Review Workflow

Status: Completed locally on `main` after validation.

Queue item: `m100-documentation-agent-dry-run-review-workflow`.

Implementation commit: `bc05476`.

M100 consumes or derives the M97 dispatch plan and adds:

- `validate-documentation-agent-dry-run --item-id <item_id>`
- `validate-documentation-agent-dry-run --item-id <item_id> --format json`
- optional `--output <path>` with overwrite refusal unless `--force` is explicit
- a structured dry-run payload with item identity, queue status, selected lane, confidence, selection reason, documentation review intent, source docs to review, expected doc updates, stale doc checks, reconciliation scope, validation expectations, operator gates, and next safe action

M100 ready behavior:

- succeeds only when the M97 selected lane is exactly `documentation_agent_dry_run`
- requires no M97 blocked reasons
- requires `local_only: true`
- requires `execution_allowed: false`
- reports `dry_run: true`, `ready_for_future_documentation_review: true`, and `execution_allowed: false`

M100 blocked behavior:

- blocks `codex_prompt_artifact`, `local_llm_advisory`, `local_llm_coding_draft`, and `human_only_manual`
- blocks when the M97 plan has blocked reasons
- blocks when `local_only` is not true
- blocks when `execution_allowed` is not false
- emits clear blocked reasons and does not execute agents or mutate documentation

Operator workflow:

- inspect dispatch plan
- validate documentation-agent dry-run
- review source docs, stale-doc checks, expected updates, and reconciliation scope
- approve any future documentation apply path only in a later milestone

M100 to M101 relationship:

- M100 only covers dry-run review readiness for `documentation_agent_dry_run`.
- M101 remains the planned Human Approval Gate UI/Data Contract for approval records across Codex, local LLM, documentation, and patch gates.
- M100 does not authorize documentation-agent execution, documentation mutation, local LLM execution, Codex execution, or patch application.

## M99 Local LLM Advisory Execution Dry-Run Validator

Status: Completed locally on `main` after validation.

Queue item: `m99-local-llm-advisory-dry-run-validator`.

Implementation commit: `b04e868`.

M99 consumes or derives the M97 dispatch plan and adds:

- `validate-local-llm-advisory-dry-run --item-id <item_id>`
- `validate-local-llm-advisory-dry-run --item-id <item_id> --format json`
- optional `--output <path>` with overwrite refusal unless `--force` is explicit
- a structured dry-run payload with item identity, queue status, selected lane, confidence, selection reason, advisory intent, recommended model role, source context to review, dry-run prompt sections, validation expectations, operator gates, and next safe action

M99 ready behavior:

- succeeds only when the M97 selected lane is exactly `local_llm_advisory`
- requires no M97 blocked reasons
- requires `local_only: true`
- requires `execution_allowed: false`
- reports `dry_run: true`, `ready_for_future_advisory_run: true`, and `execution_allowed: false`

M99 blocked behavior:

- blocks `codex_prompt_artifact`, `local_llm_coding_draft`, `documentation_agent_dry_run`, and `human_only_manual`
- blocks when the M97 plan has blocked reasons
- blocks when `local_only` is not true
- blocks when `execution_allowed` is not false
- emits clear blocked reasons and does not generate or execute a model prompt

Operator workflow:

- inspect dispatch plan
- validate local LLM advisory dry-run
- review dry-run output
- approve any future advisory artifact or actual advisory run only in a later milestone

M99 to M100 relationship:

- M99 only covers local LLM advisory dry-run readiness for `local_llm_advisory`.
- M100 remains the planned Documentation Agent dry-run review workflow for `documentation_agent_dry_run`.
- M99 does not authorize local LLM execution, documentation-agent execution, or patch application.

## M98 Codex Prompt Dispatch Artifact Generator v1

Status: Completed locally on `main`.

Queue item: `m98-codex-prompt-dispatch-artifact-generator`.

Implementation commit: `80f64dd`.

Queue status: `done`; M96 remains `proposed` for planning context and M97 remains `done`.

M98 consumes or derives the M97 dispatch plan and adds:

- `generate-codex-dispatch-artifact --item-id <item_id>`
- `generate-codex-dispatch-artifact --item-id <item_id> --format json`
- optional `--output <path>` with overwrite refusal unless `--force` is explicit
- prompt text that includes item identity, queue status, selected lane, routing confidence, selection reason, planned artifact intent, safety boundaries, docs/files to inspect, implementation requirements, validation commands, completion criteria, and final response format

M98 blocked behavior:

- blocks every lane except `codex_prompt_artifact`
- blocks when the M97 plan has blocked reasons
- blocks when `local_only` is not true
- blocks when `execution_allowed` is not false
- emits only local console output or local files

Operator workflow:

- inspect dispatch plan
- generate Codex prompt artifact
- review the artifact
- manually copy/paste into Codex only after approval
- paste final Codex results back into the existing queue completion evidence process

M98 to M99 relationship:

- M98 only covers Codex prompt artifacts.
- M99 remains the planned local LLM advisory/coding dry-run validator and must not inherit Codex prompt generation as local LLM execution approval.

## M97 Queue-to-Agent Dispatch Plan Contract

Status: Completed locally on `main`.

Implementation commit: `4ec0500`.

Queue status: `m97-queue-to-agent-dispatch-plan-contract` is `done`; M96 remains `proposed` because no existing completion evidence was recorded for it in this pass.

Delivered in this pass:

- adds `inspect-queue-dispatch-plan` for local-only dispatch plan inspection
- adds a JSON-serializable M97 dispatch plan contract for one queue item
- supports `codex_prompt_artifact`, `local_llm_advisory`, `local_llm_coding_draft`, `documentation_agent_dry_run`, and `human_only_manual`
- maps implementation/coding items toward a future M98 Codex prompt artifact intent without generating the full prompt
- maps documentation/reconciliation items toward a documentation-agent dry-run plan
- falls back to `human_only_manual` when the item is missing, blocked, unclear, or below the confidence threshold
- reports `local_only: true` and `execution_allowed: false` on every plan

M97 safety posture:

- advisory plan/data/inspection only
- no Codex execution or Codex prompt dispatch
- no Ollama or local LLM invocation
- no documentation-agent execution or apply mode
- no GitHub API, `gh`, issues, PRs, workflows, daemon, watcher, scheduler, network call, or external agent execution
- no queue mutation from the inspection command
- any future execution remains outside M97 and requires explicit operator approval

M97 to M98 relationship:

- M97 identifies the intended artifact and gates.
- M98 may generate a local Codex prompt dispatch artifact from a reviewed M97 plan.
- M98 still must remain non-executing unless a later explicit dispatch gate applies.

## M96 Post-Sprint Planning and Prioritization

Status: Proposed in the local queue; planning docs from the prior pass remain authoritative context.

Queue status: seeded locally as `m96-post-sprint-planning-and-prioritization`.

M96 findings from initial review:

- M96 was not present in the queue before this planning pass; the queue had 29 items, all `done`, through M95.
- `inspect-sprint-batch-report --format json` reported no proposed or ready next milestone and recommended roadmap review before seeding more work.
- `generate-handoff-package` correctly reported current HEAD, queue totals, recovered dispatch summary, and local-only boundaries, but its high-level project summary still depended on older source-doc headings and was stale until this M96 reconciliation updated the current phase/goal.
- Four recovered M80 dispatch attempts remain audited as non-blocking historical context; they do not block current project readiness.
- No GitHub issue creation is required for this local-only planning item.

M96 scope boundaries:

- planning, reconciliation, and queue/documentation data only
- no new runtime feature behavior
- no Codex CLI dispatch
- no Ollama or local LLM inference
- no generated patch application
- no GitHub API, `gh`, issue, PR, workflow, daemon, watcher, scheduler, or external workflow execution
- no automatic next-item execution

Next recommended milestone batch after M96:

- M97 Queue-to-Agent Dispatch Plan Contract
- M98 Codex Prompt Dispatch Artifact Generator v1
- M99 Local LLM Advisory Execution Dry-Run Validator
- M100 Documentation Agent Dry-Run Review Workflow
- M101 Human Approval Gate UI/Data Contract
- M102 Queue Dependency and Completion Locking Hardening
- M103 AresForge Self-Managed Project Seed Review
- M104 Operator Batch Planner v1
- M105 Post-M96 Documentation Reconciliation

Batch rationale:

- M97-M98 should convert queue and Codex handoff contracts into non-executing dispatch artifacts before any process execution expansion.
- M99-M101 should validate advisory/dry-run flows and approval gates before any apply path exists.
- M102 should harden queue locking before larger operator batches.
- M103-M105 should review the self-managed seed, add batch planning support, and reconcile docs after the batch.

## M95 Final Overnight Sprint Reconciliation

Status: Completed locally on `main`.

Implementation commit: `21008e644bc433e820bd30346da23b422db43e8c`.

Final reconciliation scope:

- reconciles source-of-truth docs after the completed M81-M94 overnight sprint
- confirms the local queue is complete through M94 and M95 is the final documentation cleanup item
- records the completed local LLM advisory/coding safety model, documentation agent plan flow, handoff package, and sprint batch report posture
- keeps this milestone documentation-only unless queue evidence completion is explicitly recorded

M81-M94 completed scope:

- M81-M88 established local LLM advisory readiness, provider/health contracts, advisory artifacts, routing confidence, coding draft artifacts, and human-gated patch application boundaries
- M89-M90 added local usage accounting and read-only Hub routing dashboard data
- M91-M92 defined Documentation Agent v1 and the non-mutating documentation reconciliation plan generator
- M93-M94 added operator handoff v2 and the overnight sprint batch report

Recommended next milestone after this reconciliation:

- seed a new M96 planning/priority milestone only after operator review of the final handoff and sprint batch report; no next queue item is started automatically

M95 safety posture:

- documentation reconciliation only
- no GitHub API or `gh`
- no external workflows
- no Codex execution or local LLM invocation
- no automatic queue completion or next-item execution

## M94 Overnight Sprint Batch Report

Status: Completed locally on `main`.

Implementation commit: `ed8cc6df00fa7ffc5199b95aa9a72fd468a070b0`.

Delivered in this pass:

- adds `inspect-sprint-batch-report` for local overnight sprint batch summaries
- summarizes recent local commits by `--since-commit` or `--commit-count`
- summarizes completed queue items, completion evidence, tests recorded in queue evidence, dispatch runs, recovered runs, queue posture, unresolved warnings, and next recommended milestone
- keeps the report read-only by default; `--output` is the only local artifact write path

M94 safety posture:

- no GitHub API or `gh`
- no external workflows
- no Codex execution or local LLM invocation
- no queue mutation or automatic next-item execution

## M93 Operator Handoff Package v2

Status: Completed locally on `main`.

Delivered in this pass:

- expands `generate-handoff-package` to emit `handoff_package_version: m93.v2`
- adds current HEAD/recent commits, queue v2 active/ready item details, recovered dispatch summary, model routing summary, safe command suggestions, and next safe actions
- preserves stdout/read-only default behavior; `--output` remains the only local artifact write path

M93 safety posture:

- no Codex execution
- no local LLM invocation
- no model routing execution
- no GitHub mutation, GitHub API, or `gh`
- no automatic queue completion or next-item execution

## M92 Documentation Reconciliation Plan Generator

Status: Completed locally on `main`.

Delivered in this pass:

- expands `plan-doc-reconciliation` into the M92 local-only documentation reconciliation plan generator
- includes source docs, changed source-of-truth docs, queue items, recent local commits, stale/missing sections, recommended doc updates, and safety boundaries in the plan payload
- keeps the default behavior read-only and non-mutating; only an explicit `--output` path writes a local plan artifact
- omits runtime timestamps from the payload so the same local inputs produce stable plan output

M92 safety posture:

- no local LLM invocation
- no Codex invocation
- no automatic documentation rewrite
- no queue mutation, queue completion, or automatic next-item execution
- no GitHub API, `gh`, issues, PRs, workflows, daemon, watcher, scheduler, or external workflow behavior

## M91 Documentation Agent v1 Contract

Status: Completed locally on `main`.

Delivered in this pass:

- adds `inspect-documentation-agent-contract` for read-only Documentation Agent v1 contract inspection
- adds `docs/architecture/DOCUMENTATION_AGENT_CONTRACT.md`
- defines documentation agent scope, source-of-truth docs, required evidence, plan mode, and future gated apply mode
- confirms model output cannot automatically update documentation

M91 safety posture:

- contract-first and local-only
- plan mode is non-mutating
- future apply mode is unavailable until a separate explicit gate exists
- no automatic documentation updates, queue completion, next-item execution, GitHub API, `gh`, issues, PRs, workflows, daemon, watcher, scheduler, or external workflow behavior

## M90 Hub Routing Dashboard Data Contract

Status: Completed locally on `main`.

Delivered in this pass:

- adds `GET /api/local-queue/routing-dashboard` as a read-only Hub data contract
- summarizes queue routing decision data for dashboard use
- includes item id, status, risk, task size, recommended engine, recommended lane, recommended model, confidence score, validation burden, warnings, and blockers
- exposes safety flags showing no prompt execution, local LLM invocation, Codex invocation, queue mutation, or automatic next-item execution

M90 safety posture:

- API route is read-only
- no mutation endpoints are added
- no prompt execution, local LLM invocation, Codex invocation, GitHub API, `gh`, issues, PRs, workflows, daemon, watcher, scheduler, or external workflow behavior

## M89 Model Usage and Token Accounting Report

Status: Completed locally on `main`.

Delivered in this pass:

- adds `inspect-model-usage-report` for local model usage and token accounting
- reads local Codex dispatch run states and summarizes `token_usage` when present
- reports unavailable token usage and extraction errors for older or incomplete run states
- includes model, provider, and reasoning effort metadata when available
- scans local LLM advisory and coding draft metadata artifacts for run/model/provider posture

M89 safety posture:

- read-only by default and local-only
- optional report artifact writing requires an explicit `--output`
- no network calls, provider invocation, queue mutation, queue completion, automatic next-item execution, GitHub API, `gh`, issues, PRs, workflows, daemon, watcher, scheduler, or external workflow behavior

## M88 Human-Gated Patch Application Contract

Status: Completed locally on `main`.

Delivered in this pass:

- adds `inspect-human-gated-patch-application-contract` for read-only contract inspection
- defines the local patch artifact structure expected from generated local coding drafts
- defines explicit operator approval requirements, including an approval phrase and approval record fields
- defines pre-apply safety gates and post-apply validation requirements

M88 safety posture:

- contract-first and dry-run only
- patch application is not implemented by the contract inspector
- no automatic file mutation or patch application
- no queue mutation, queue completion, or automatic next-item execution
- no GitHub API, `gh`, issues, PRs, workflows, daemon, watcher, scheduler, or external workflow behavior

## M87 Local Coding Draft Artifact Mode

Status: Completed locally on `main`.

Delivered in this pass:

- adds `prepare-local-coding-draft` for local coding draft prompt artifact generation
- stores draft prompt/output metadata under `artifacts/local_coding_drafts/generated/`
- supports an explicit `--run` path that can capture local coding draft output as an artifact
- marks drafts as non-applied, non-authoritative, and manually reviewed only

M87 safety posture:

- draft artifacts never mutate repository files
- generated draft patch text is never applied automatically
- draft output never completes queue items or starts another item
- no GitHub API, `gh`, issues, PRs, workflows, daemon, watcher, scheduler, or external workflow behavior

## M86 Routing Confidence Scoring

Status: Completed locally on `main`.

Delivered in this pass:

- adds deterministic routing confidence scoring to the M80 decision matrix
- scores Codex, local LLM advisory, local coding draft, and manual-only lanes
- includes risk, task size, work mode, item type, dependencies, validation burden, provider/model availability, and recovery history factors
- reports selected score, confidence level, rationale, warnings, and recommended lane

M86 safety posture:

- scoring is advisory only and does not execute prompts
- no provider, Codex, or agent invocation is performed by scoring
- no queue mutation, queue completion, automatic next-item execution, GitHub API, `gh`, issues, PRs, workflows, daemon, watcher, scheduler, or external workflow behavior

## M85 Local LLM Advisory Run Artifact

Status: Completed locally on `main`.

Delivered in this pass:

- adds `prepare-local-llm-advisory-run` for local advisory prompt artifact generation
- stores prompt artifacts under `artifacts/local_llm_advisory/generated/`
- supports an explicit `--run` path that can write advisory response and metadata artifacts locally
- returns prompt path, response path, provider/model metadata, safety confirmations, and next safe action
- reports safe unavailable state when local Ollama advisory output is not available

M85 safety posture:

- prompt artifact generation is local-only and non-mutating
- provider invocation is opt-in only through the explicit operator `--run` flag
- advisory output is never applied to repository files
- advisory output never completes queue items or starts another item
- no GitHub API, `gh`, issues, PRs, workflows, daemon, watcher, scheduler, or external workflow behavior

## M84 Ollama Health Check and Model Inspection

Status: Completed locally on `main`.

Delivered in this pass:

- repurposes `test-ollama` as a local-only Ollama health/model inspection command that does not generate text
- adds `inspect-ollama-health` for explicit read-only inspection of Ollama reachability and visible models
- reports stable fields for `available`, `provider`, `endpoint`, `models`, `error_summary`, and `next_safe_action`
- handles Ollama being offline as non-blocking inspection metadata so normal project readiness is unaffected

M84 safety posture:

- local-only and operator-invoked
- calls only the local Ollama `/api/tags` model listing endpoint
- no `/api/generate`, `/api/chat`, completion, or prompt endpoint is invoked
- no provider output can mutate repo files, mutate queue state, execute prompts, start the next item, or use GitHub/`gh`/workflows/external automation

## M83 Local LLM Provider Contract

Status: Completed locally on `main`.

Delivered in this pass:

- added `inspect-local-llm-provider-contract` for read-only provider contract inspection
- defines Ollama as the initial local provider target
- reports provider URL, timeout expectations, health-check endpoint boundaries, model identifiers, model roles/capabilities, and safety confirmations
- supports separate future local reasoning and local coding model selection through contract metadata

M83 safety posture:

- local-only and non-executing
- provider contract inspection does not call Ollama or any model endpoint
- health checks remain explicit and limited to the local Ollama `/api/tags` endpoint
- no provider output can mutate repo files, mutate queue state, execute prompts automatically, start the next item, or use GitHub/`gh`/workflows/external automation

## M82 Self-Managed AresForge Test Run

Status: Completed locally on `main`.

Delivered in this pass:

- added a read-only `self_managed_readiness_summary` to `inspect-local-project-report`
- summarizes AresForge-as-managed-project status, local queue posture, M81/M82 status, and dogfood readiness flows
- surfaces recovered dispatch runs as audited non-blocking evidence when dependency completion evidence is present
- confirms no repo mutation, queue mutation, automatic next-item execution, unattended multi-item execution, GitHub API, `gh`, workflows, or external workflow behavior is allowed

M82 safety posture:

- validation-focused and local-only
- operator review remains required before queue completion evidence is recorded
- recovered dispatch run state is reported for review but does not start or complete work

## M81 Local LLM Advisory/Coding Lane Prototype

Status: Completed locally on `main`.

Delivered in this pass:

- added `inspect-local-llm-advisory-lane-readiness` for read-only inspection of one local queue item
- composes local queue readiness, M80 decision matrix output, and local LLM provider/model metadata
- returns a structured advisory plan for reasoning/coding advisory output, including required JSON fields and safety boundary confirmations
- keeps provider invocation, prompt dispatch, repo mutation, queue mutation, queue completion, and automatic next-item execution disabled

M81 safety posture:

- local-only and advisory-first
- no local LLM provider invocation from the readiness command
- no automatic repo file mutation from local LLM output
- no automatic queue completion or next-item execution
- no GitHub API, `gh`, issues, PRs, workflows, or external workflow execution

Recommended next milestone:

- M82 Self-Managed AresForge Test Run only after M81 review, validation, and queue evidence.

## M79.4 Codex Dispatch Recovery and Windows argv Hardening

Status: In progress locally on `main`.

Delivered in this pass:

- added `recover-codex-dispatch-run` for explicit local recovery of one Codex dispatch run state
- records recovery metadata without completing queue work or starting another item
- converts stale active dispatch states to `failed` so a partial run can be reviewed and recovered safely
- hardened operator command string parsing with Windows-aware argv handling
- reused the argv hardening in single-item validation command execution

M79.4 safety posture:

- local-only and operator-gated
- recovery does not dispatch Codex, invoke local LLMs, complete queue items, or run the next item
- no GitHub API, `gh`, issues, PRs, workflows, or external workflow execution

Recommended next milestone:

- After M79.4 review/evidence capture, continue only by explicit operator action.

## M80 LLM Decision Matrix v2

Status: In progress locally on `main`.

Delivered in this pass:

- added advisory LLM decision matrix v2 inspection for one local queue item
- classifies local LLM vs Codex, coding vs reasoning, task size, risk, validation burden, model/profile source, and safety gates
- exposes `inspect-llm-decision-matrix` as a local-only, non-executing command
- embeds the M80 decision payload into Prompt Builder and `prepare-queue-item-dispatch` outputs for operator review

M80 safety posture:

- decision matrix output is advisory only
- no prompt execution, Codex call, local LLM invocation, source mutation, queue mutation, GitHub API, `gh`, workflow execution, queue completion, or next-item execution is performed
- Codex recommendations still require separate M78 approval and runner dispatch
- local LLM recommendations remain advisory, prototype-scoped, operator-gated, and non-mutating

Recommended next milestone:

- M81 Local LLM Advisory/Coding Lane Prototype, only after M80 review and validation evidence.

## M79.3 Codex Run Token Usage Capture

Status: In progress locally on `main`.

Delivered in this pass:

- added Codex CLI transcript footer parsing for `tokens used` followed by a numeric line
- supports comma-separated totals such as `221,534`
- stores `token_usage` in Codex dispatch run state after each completed run attempt
- exposes `token_usage` through `inspect-codex-dispatch-run`
- preserves old run-state inspection when `token_usage` is absent by returning an unavailable token usage object

M79.3 token usage shape:

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

M79.3 safety posture:

- local-only and operator-gated
- no automatic queue completion
- no automatic next-item execution
- no GitHub API, `gh`, issues, PRs, workflows, or external workflow execution
- no local LLM execution expansion

Recommended next milestone:

- After M79.3 review/evidence capture, continue only by explicit operator action.

## M79.2 Single-Item Ready-to-Codex Automation

Status: In progress locally on `main`.

Delivered in this pass:

- added `run-single-ready-codex-queue-item` for one explicit local operator-controlled ready queue item
- selection fails safely when no ready/startable item exists or when multiple ready/startable items exist without `--item-id`
- explicit item selection processes only that item and requires it to be ready/startable
- workflow composes prompt preparation, M78 approval, hardened Codex dispatch, validation commands, implementation commit/push, queue evidence capture, queue closeout, and queue evidence commit/push
- failed Codex dispatch, failed validation, and failed implementation commit/push leave the queue item in progress and record recovery evidence where possible
- no next queue item is started automatically

M79.2 safety posture:

- local-only and explicit-command only
- no watcher, daemon, scheduler, polling loop, file-change trigger, or unattended queue worker
- Codex dispatch still requires the exact M78 approval phrase
- Prompt Builder remains artifact-only and does not execute prompts, call Codex, invoke local LLMs, mutate files, or advance queue items
- no GitHub API, `gh`, issues, PRs, workflows, or external workflow execution
- git commit/push attempts are local git CLI operations after validation gates pass

Recommended next milestone:

- After M79.2 review/evidence capture, continue to M79.3 only by explicit operator action.

## M79.1 Codex CLI Windows Runner Hardening

Status: In progress locally on `main`.

Delivered in this hardening pass:

- Codex dispatch run-state JSON reads tolerate a UTF-8 BOM for Windows-created `run_state.json` files.
- Codex dispatch subprocess output is captured as bytes and decoded with UTF-8-sig plus replacement handling before writing `stdout.txt` and `stderr.txt`.
- The approved prompt artifact is copied from the reviewed prompt source when available and passed to the dispatch subprocess over UTF-8 stdin so multi-line prompt bodies are preserved.
- Run-state payloads record `stdin_prompt_path`, `stdin_prompt_bytes`, `stdin_prompt_handoff`, and `output_decoding` for operator review.
- Windows Codex sandbox guidance is documented: Codex can author validated implementation changes, but the operator may need to perform `git commit` and `git push` outside the sandbox when `.git` write access is unavailable.

M79.1 safety posture:

- dispatch remains local-only and operator-gated
- no automatic queue completion
- no automatic next-item execution
- no GitHub API, `gh`, issues, PRs, workflows, external workflow execution, or GitHub mutation from AresForge
- local LLM safety posture is unchanged

Recommended next milestone:

- Complete M79.1 review/evidence capture, then continue to the next approved queue item only after explicit operator action.

## M78.5 Operator Workflow Compression and Prompt Builder Agent Contract

Status: Completed locally on `main`.

Delivered:

- added the local-only Prompt Builder Agent / Prompt Architect Agent contract
- exposed `python -m aresforge prepare-queue-item-dispatch --item-id <item_id> --target codex --format json`
- added workflow preparation that inspects readiness, optionally starts only with `--start-if-ready`, generates a stronger prompt artifact, and inspects the Codex dispatch contract
- writes prompt artifacts under `.aresforge/codex_dispatch/prompts/`
- returns stable JSON fields for prompt artifact path, readiness, dispatch contract summary, approval requirement, next safe action, blockers, warnings, and boundary confirmations

M78.5 safety posture:

- Prompt Builder is artifact-only and local-only
- preparation does not dispatch, approve, complete, or auto-run any item
- Codex approval and execution remain separate M78 operator-gated commands
- queue completion still requires review and validation evidence
- no GitHub API, `gh`, issues, PRs, workflows, external workflow execution, or GitHub mutation behavior
- no local LLM execution expansion; local LLM remains local-only, advisory-only, operator-gated, prototype-scoped, and non-mutating

Recommended next milestone:

- M79 - Queue Blocking and Sequencing Enforcement.

## M78 Operator-Gated Codex CLI Dispatch Prototype

Status: Completed locally on `main`.

Delivered:

- added `src/aresforge/operator/codex_dispatch_runner.py`
- exposed `python -m aresforge approve-codex-dispatch --item-id <item_id> --approved-by <operator> --approval-phrase "APPROVE CODEX DISPATCH" --format json`
- exposed `python -m aresforge run-codex-dispatch --item-id <item_id> --run-id <run_id> --command "<operator-provided command>" --format json`
- exposed `python -m aresforge inspect-codex-dispatch-run --run-id <run_id> --format json`
- exposed `python -m aresforge list-codex-dispatch-runs --format json`
- exposed `python -m aresforge cancel-codex-dispatch-run --run-id <run_id> --format json`
- implemented local run-state storage under `.aresforge/codex_dispatch/runs/<run_id>/`
- captured `run_state.json`, `prompt.txt`, `stdout.txt`, `stderr.txt`, and `artifacts/`
- kept the real command operator-provided so tests and smoke checks do not require Codex CLI installation

M78 run-state highlights:

- explicit operator approval is required before invocation
- one active dispatch run is allowed at a time
- `approved_pending_dispatch` and `running` are active run states
- successful command completion moves the run to `review_required`
- failed commands move the run to `failed` with `exit_code` and `error_summary`
- dispatch output does not mark queue items complete
- no automatic next-item execution is allowed
- review evidence and validation evidence remain required before queue completion

M78 safety posture:

- local-only and file-backed
- operator-gated command invocation only
- no autonomous multi-item execution
- no GitHub API, `gh`, GitHub issue, GitHub PR, GitHub workflow, external workflow, or GitHub mutation behavior
- no local LLM execution expansion
- local LLM remains local-only, advisory-only, operator-gated, prototype-scoped, and non-mutating

M78.5 follow-on note:

- M78.5 now creates high-quality Prompt Builder Agent / Prompt Architect Agent artifacts from queue items, docs, routing metadata, model profiles, and safety gates for operator review before dispatch. It must not execute prompts, call Codex, invoke local LLMs, mutate files, or advance queue items automatically.

Recommended next milestone:

- M79 - Queue Blocking and Sequencing Enforcement.

## M77 Codex CLI Dispatch Contract

Status: Completed locally on `main`.

Delivered:

- added the local-only Codex CLI Dispatch Contract helper module
- exposed `python -m aresforge inspect-codex-dispatch-contract --item-id <item_id> --format json`
- exposed `python -m aresforge prepare-codex-dispatch-dry-run --item-id <item_id> --format json`
- defined a stable one-queue-item-at-a-time dispatch contract payload for future Codex CLI work
- defined expected future run-state fields without implementing execution
- reserved local artifact path conventions under `.aresforge/codex_dispatch/contracts` and `.aresforge/codex_dispatch/runs`
- added targeted contract and CLI tests for M77 safety boundaries

M77 contract payload highlights:

- `dry_run_only` is always `true`
- `dispatch_allowed` is always `false`
- `codex_cli_invocation_allowed` is always `false`
- `automatic_next_item_execution_allowed` is always `false`
- `operator_approval_required` is `true`
- `operator_approval_status` defaults to `not_requested`
- `execution_mode` is `contract_only` or `dry_run_no_execute`
- command previews are labeled preview-only and not executable in M77

Expected future run-state shape for M78:

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
- `next_safe_action`

Allowed future dispatch states:

- `not_requested`
- `dry_run_prepared`
- `awaiting_operator_approval`
- `approved_pending_dispatch`
- `running`
- `completed`
- `failed`
- `cancelled`
- `review_required`

M77 safety posture:

- contract-only and dry-run/no-execute
- no Codex CLI process invocation
- no automatic Codex execution
- no automatic agent execution
- no automatic queue execution
- no unattended multi-item execution
- no automatic next-item execution
- no local LLM execution expansion
- local LLM remains local-only, advisory-only, operator-gated, prototype-scoped, and non-mutating
- no GitHub API, `gh`, GitHub issue, GitHub PR, GitHub workflow, external workflow, or GitHub mutation behavior was added

Future M78 gates before dispatch may invoke Codex:

- queue item exists
- queue item belongs to a registered managed project/repo
- queue item is not done or cancelled
- queue item is not already in an active dispatch state
- explicit operator approval is present
- one item at a time lock/check exists
- no automatic next-item execution
- run state path is reserved
- stdout/stderr/artifact capture paths are reserved
- review evidence is required before completion
- validation evidence is required before commit/push
- dependency blocking is respected
- GitHub/`gh`/API/workflow mutation remains blocked

Recommended next milestone:

- M78 - Operator-Gated Codex CLI Dispatch Prototype.

## M76 Self-Seed AresForge as the First Managed Project

Status: Completed locally on `main`.

Delivered:

- added `seed_aresforge_self_project(...)` as an idempotent local-only operator workflow
- exposed `python -m aresforge seed-aresforge-self-project --format json`
- registers or updates AresForge as managed project `aresforge`
- registers or updates primary repo `aresforge-main`
- ensures the canonical local project queue exists
- seeds reviewable proposed queue items for M77 through M82 without starting any item
- can set AresForge as the active project only when `--set-active` is supplied

Seeded self-project identity:

- project_id: `aresforge`
- project_name: `AresForge`
- repo_id: `aresforge-main`
- repo_name: `AresForge Main Repository`
- project status: `active`
- repo role/status: `primary` / `active`

Seeded queue item purpose:

- M77 Codex CLI Dispatch Contract
- M78 Operator-Gated Codex CLI Dispatch Prototype
- M79 Queue Blocking and Sequencing Enforcement
- M80 LLM Decision Matrix v2
- M81 Local LLM Advisory/Coding Lane Prototype
- M82 Self-Managed AresForge Test Run

M76 safety posture:

- self-seed is local-only, file-backed, and idempotent
- seeded items are proposed/reviewable only and are not started
- no Codex dispatch, automatic Codex execution, Codex CLI invocation, agent execution, prompt dispatch, or unattended multi-item execution was added
- no local LLM execution expansion was added
- local LLM remains local-only, advisory-only, operator-gated, prototype-scoped, and non-mutating
- no GitHub API, `gh`, GitHub issue, GitHub PR, GitHub workflow, external workflow, or GitHub mutation behavior was added

Recommended next milestone after M76:

- M77 - Codex CLI Dispatch Contract.

## M75 Source-of-Truth Documentation and Roadmap Reconciliation

Status: Completed on `main` in commit `7088204`.

Scope:

- documentation-only reconciliation after M74
- aligned source-of-truth docs around the current local-first, file-backed, operator-gated state
- prepared the roadmap for self-managing AresForge as the first managed project and for future approved Codex/local LLM milestones

Current implemented surfaces:

- local managed-project registry and project factory surfaces are file-backed and local-only
- local queue is the canonical work-tracking source for project/repo items, statuses, dependencies, routing metadata, and prompt-pack inputs
- Hub UI exposes local queue lifecycle controls, project/repo management, prompt-pack generation, routed queue views, local LLM environment/health/preview/prototype controls, Codex high-value prompt preview, AI Action Review visibility, execution audit log, AI artifact registry, and Operator Run History
- prompt-pack generation and Codex high-value lane output remain preview-only/manual handoff surfaces
- Copy Prompt Pack Preview is copy-only and does not dispatch prompts
- AI Action Review, execution audit log, artifact registry, and run history are review-only evidence surfaces
- local LLM provider/model status remains prototype-scoped configuration and health evidence, not production-ready dispatch
- M62 local LLM execution remains the only provider-calling local LLM path, and it is local-only, advisory-only, operator-gated, prototype-scoped, and non-mutating

Hard boundaries:

- no GitHub API, `gh`, GitHub issues, GitHub PRs, GitHub workflow activity, or GitHub mutation from the app
- no automatic agent execution, automatic Codex execution, automatic Codex CLI invocation, external workflow execution, or unattended multi-item execution
- Codex high-value lane currently remains prompt-generation/operator-handoff only
- local LLM output must never automatically mutate repository files, queue state, project state, GitHub, `gh`, Codex, agents, commits, pushes, or workflows
- normal `git commit` and `git push origin main` are operator/developer actions only after local validation, smoke checks, clean diff check, and explicit prompt instruction

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

Recommended next milestone:

- M76 - Self-Seed AresForge as the First Managed Project.

## M74 Hub UX Stabilization Pass

Status: Completed locally on `main`.

Delivered:

- clarified Hub Queue copy around local-only status, operator-gated lifecycle actions, prompt previews, local LLM prototype/config status, and review-only AI metadata
- improved empty states for blocked items, ready items, prompt-pack previews, audit entries, artifacts, and AI Action Review Panel blocked/safety metadata
- added a copy-only prompt-pack preview affordance for manual operator handoff
- strengthened AI Action Review Panel wording around safety status, gate status, no automatic execution, no repo mutation, and next safe action labels

Safety posture:

- Hub UX changes are wording and copy/paste affordance only
- prompt-pack previews and AI review surfaces remain manual/operator handoff only
- no automatic execution, Codex execution, Codex CLI invocation, local LLM repo mutation, GitHub behavior, external workflow behavior, or new backend capability was introduced

Recommended next milestone:

- M75 - Source-of-Truth Documentation and Roadmap Reconciliation.

## M73 Prompt Pack Quality and Routing Improvements

Status: Completed locally on `main`.

Delivered:

- improved local queue prompt packs with routing-aware lane guidance for high-value Codex, local LLM advisory, documentation/review, and operator-only/manual paths
- added advisory model/engine recommendation text, task sizing guidance, validation expectations, and final response requirements to generated prompt packs
- made prompt-pack safety boundaries explicit: no automatic execution, no GitHub API, no `gh`, no GitHub mutation, no Codex CLI execution unless a future approved milestone explicitly permits it, and no repo mutation from local LLM output
- kept prompt packs copy/paste-friendly and avoided nested markdown fences in generated prompt bodies

Safety posture:

- prompt packs remain manual operator handoff artifacts only
- Codex high-value lane remains prompt-generation/operator-handoff only
- local LLM advisory lane remains advisory-only and cannot mutate repo files automatically
- no automatic execution, provider invocation, GitHub behavior, workflow behavior, or external mutation was introduced

Recommended next milestone:

- M74 - Hub UX Stabilization Pass.

## M72 Local LLM Provider Configuration Hardening

Status: Completed locally on `main`.

Delivered:

- hardened the local LLM environment contract with explicit provider availability and configuration status fields
- added operator-readable provider states for configured, missing configuration, unavailable, unsupported, disabled, and prototype-only execution mode
- added advisory local model profile metadata for reasoning, coding, and fallback model fields, including provider, model name, intended lane, recommended use, hardware notes, status, and prototype warnings
- clarified fallback behavior so fallback model names are advisory only and never selected automatically
- improved local LLM health output with provider state, model profile status, fallback behavior, and explicit non-execution wording

Safety posture:

- local LLM usage remains local-only, advisory-only, operator-gated, and prototype-scoped
- provider/model metadata does not prove model availability or authorize execution
- health checks remain explicitly invoked and only inspect local provider availability/model listing
- no automatic local LLM execution, Codex execution, agent execution, GitHub behavior, workflow behavior, external workflow execution, or repository mutation was introduced

Recommended next milestone:

- M73 - Prompt Pack Quality and Routing Improvements.

## M71 Operator-Facing AI Action Review Panel

Status: Completed locally on `main`.

Delivered:

- added a read-only Hub AI Action Review Panel for operator review of AI-adjacent local actions
- added local-only review API `GET /api/ai-action-review`
- composed existing AI action safety, execution audit log, AI artifact registry, Operator Run History, and local queue routing metadata into one review payload
- surfaced operator-friendly labels for action name, safety status, gate status, blocked action, blocked reason category, blocked reason, no automatic execution, no repo mutation, artifact references, audit references, run-history timeline entries, and next safe operator action
- added useful empty states for no recent AI actions, no artifacts found, no blocked actions found, and no audit entries found

Safety posture:

- the panel is read-only and review-focused
- no execution controls were added
- no agents, Codex, Codex CLI, local LLMs, GitHub actions, `gh`, issues, PRs, workflows, external services, or repository mutations are executed from the panel
- local LLM output remains local-only, advisory-only, operator-gated, and never automatically mutates repo files
- Codex high-value lane remains prompt-generation/operator-handoff only

Recommended next milestone:

- M72 - Local LLM Provider Configuration Hardening.

## M70 Local AI Operations Verification Sweep

Status: Completed locally on `main`.

Verification outcome:

- swept the M58-M69 local AI operations chain for stale milestone references, implemented/future-state drift, and operator-facing boundary wording
- confirmed local LLM environment, health check, prompt preview, operator-gated local execution prototype, Codex model profile contract, Codex high-value prompt lane, execution audit log, AI action safety gate, AI artifact registry, Operator Run History, and M69 hardening remain aligned
- tightened PR-shaped prohibited action classification in the AI action safety gate so GitHub pull request mutation representations are reported as policy-blocked
- clarified Operator Run History UI rendering so existing safety/gate/non-mutation metadata is visible in the timeline
- added targeted regression coverage for local AI docs wording, static Hub source boundaries, safety metadata rendering, PR-shaped safety-gate blocking, and local LLM advisory non-mutation behavior

Safety posture:

- local AI operations remain local-first, file-backed, operator-gated, and advisory-only where local LLM output is involved
- local LLM execution remains limited to the M62 explicit local provider prototype and does not apply output to repository files, queue state, project state, GitHub, `gh`, Codex, agents, commits, pushes, or workflows
- Codex high-value lane remains prompt-generation/operator-handoff only
- no GitHub API, `gh`, GitHub mutation, issue, PR, workflow, automatic Codex execution, automatic agent execution, external workflow execution, or automatic repo mutation was introduced
- M70 was a verification and stabilization milestone, not a feature expansion

Recommended next milestone:

- M71 - Operator-Facing AI Action Review Panel.

## M69 Local AI Operations Hardening

Status: Completed locally on `main`.

Delivered:

- validated AI action safety gate behavior across local LLM preview/execution, Codex high-value prompt generation, routing, prompt-pack, automatic-agent, repo-mutation, Codex-execution, and GitHub/`gh`-style action representations
- hardened blocked/error payloads with consistent safety status, gate status, blocked action, blocked reason category, and next safe operator action fields
- carried additive safety metadata through execution audit log entries, AI artifact registry records, and Operator Run History timeline entries
- added regression coverage confirming blocked local LLM execution does not call a provider or mutate the queue from local LLM output
- added regression coverage confirming Codex high-value lane remains prompt-generation/operator-handoff only and does not execute Codex or mutate repo state

Safety posture:

- local LLM execution remains local-only, advisory-only, operator-gated, and prototype-scoped
- Codex high-value lane remains prompt-generation/operator-handoff only
- no GitHub API, `gh`, GitHub mutation, issue, PR, workflow, automatic Codex execution, automatic agent execution, external workflow execution, or automatic repo mutation was introduced

Recommended next milestone:

- M70 completed Local AI Operations Verification Sweep.

## M68 Local AI Operations Closeout Reconciliation

Status: Completed locally on `main`.

Reconciled implemented local AI operations baseline:

- Project AI settings contract and UI
- Agent/engine registry
- Queue routing metadata
- Routing decision matrix v1
- Routed queue views as filtered views over the canonical local queue
- Routing-aware prompt packs
- Local LLM environment contract
- Local LLM health check
- Codex CLI model profile contract
- Local LLM prompt preview
- Operator-gated local LLM execution prototype
- Codex CLI high-value prompt lane
- Execution audit log
- AI action safety gate
- AI artifact registry
- Operator run history panel

Current hard boundaries:

- no GitHub API, `gh`, GitHub issues, GitHub PRs, GitHub workflows, or GitHub mutation from the app
- no automatic Codex execution and no Codex CLI execution
- no automatic agent execution
- Codex high-value lane is prompt generation and operator handoff only
- local LLM execution is prototype-only, local-only, advisory-only, and operator-gated
- local LLM output is not applied to repository files automatically
- one canonical local queue remains the source of truth
- routed views are filtered views, not separate queues

Recommended next milestone:

- M69 - Local AI Operations Hardening.

## M67 Operator Run History Panel

Status: Completed locally on `main`.

Delivered:

- added `read_operator_run_history(...)` to combine execution audit entries and AI artifact registry records
- added read-only Hub route `GET /api/operator-run-history`
- added a read-only Queue UI Operator Run History panel with simple filters
- timeline shows audit and artifact entries newest first with action type, artifact type, outcome, summary, artifact path, execution state, and permission state
- supports filters for project id, item id, action type, artifact type, and limit

Boundaries:

- run history is read-only
- no execution controls, apply controls, GitHub buttons, or Codex run buttons
- no Codex CLI execution
- no GitHub API, `gh`, issues, PRs, workflow activity, or GitHub mutation
- no local LLM execution expansion beyond M62

Recommended next milestone:

- M68 - Local AI Operations Closeout Reconciliation.

## M66 AI Artifact Registry

Status: Completed locally on `main`.

Delivered:

- added local file-backed AI artifact registry helpers: `register_ai_artifact(...)`, `read_ai_artifact_registry(...)`, `filter_ai_artifacts(...)`, and `verify_ai_artifact_exists(...)`
- stores artifact records at `.aresforge/ai_artifact_registry.json`
- added read-only Hub route `GET /api/ai-artifacts`
- added a small read-only Queue UI AI Artifact Registry panel with simple filters
- registers successful local artifact writes for prompt packs, local LLM prompt previews, local LLM advisory execution results, Codex high-value prompts, and local project handoffs
- tracks artifact type, source action, local path, project/item ids when available, engine/model/lane metadata, checksum, existence state, warnings, and summary

Boundaries:

- artifact registry does not execute anything
- registry entries do not overwrite artifact content
- no Codex CLI execution
- no GitHub API, `gh`, issues, PRs, workflow activity, or GitHub mutation
- no local LLM execution expansion beyond M62

Recommended next milestone:

- M67 - Operator Run History Panel.

## M65 AI Action Safety Gate

Status: Completed locally on `main`.

Delivered:

- added `evaluate_ai_action_safety_gate(...)` as local-only decision/reporting logic
- added Hub route `POST /api/ai-action-safety-gate` for previewing gate decisions
- integrated safety gate decisions into M62 local LLM execution and M63 Codex high-value prompt generation
- centralized decision values: `allowed`, `blocked`, `warning`, `requires_operator_gate`, `requires_operator_override`, and `preview_only`
- supports local LLM preview/execution, Codex high-value prompt generation, prompt-pack generation, routing recommendation, and routing metadata update actions
- reports required operator gate/override state, execution permission, blockers, warnings, and next safe action

Boundaries:

- safety gate is decision/reporting logic only
- no new execution behavior
- no Codex CLI execution
- no GitHub API, `gh`, issues, PRs, workflow activity, or GitHub mutation
- no local LLM execution expansion beyond M62

Recommended next milestone:

- M66 - AI Artifact Registry.

## M64 Execution Audit Log

Status: Completed locally on `main`.

Delivered:

- added local file-backed execution audit helpers: `append_execution_audit_entry(...)`, `read_execution_audit_log(...)`, and `filter_execution_audit_log(...)`
- stores audit entries at `.aresforge/execution_audit_log.json`
- added audit logging for local LLM health checks, local LLM prompt previews, local LLM execution/dry runs/blocked attempts, Codex high-value prompt generation, prompt-pack generation, and routing metadata updates
- added read-only Hub route `GET /api/execution-audit-log`
- added a small read-only Queue UI Execution Audit Log panel with simple filters
- audit entries record action metadata, outcomes, blockers/warnings, artifact path, summary, source function, and whether anything executed
- audit entries avoid full prompt/response text and redact secret-like strings

Boundaries:

- audit logging does not execute anything
- no Codex CLI execution
- no GitHub API, `gh`, issues, PRs, workflow activity, or GitHub mutation
- no local LLM execution expansion beyond M62
- audit write failures are best-effort warnings and do not widen execution behavior

Recommended next milestone:

- M65 - AI Action Safety Gate.

## M63 Codex CLI High-Value Lane

Status: Completed locally on `main`.

Delivered:

- added `generate_codex_high_value_lane_prompt(...)` for conservative Codex-ready prompt generation
- added Hub route `POST /api/local-queue/items/{item_id}/codex-high-value-prompt`
- added Queue UI controls for Generate Codex High-Value Prompt with copy/paste preview output
- supports optional local prompt artifact output with safe non-overwrite behavior unless `force=true`
- uses the canonical local queue and routing metadata as the source of truth
- marks items Codex-worthy for `codex_cli`, `high_value_codex`, high/critical risk, high complexity, high-value affected areas, high validation burden, `codex_only`/`high_confidence`, or operator override
- returns `execution_allowed: false` and advisory `prompt_preview` only

Boundaries:

- no automatic Codex execution
- no Codex CLI command execution from the app
- no GitHub API, `gh`, issues, PRs, workflow activity, or GitHub mutation
- no repository mutation from Codex output
- local LLM execution from M62 remains operator-gated and unchanged
- generated Codex prompts must be manually copied by the operator and validated locally before commit/push

Recommended next milestone:

- M64 - Execution Audit Log.

## M62 Operator-Gated Local LLM Execution Prototype

Status: Completed locally on `main`.

Delivered:

- added `execute_local_llm_for_queue_item(...)` as a conservative local LLM execution prototype
- added Hub route `POST /api/local-queue/items/{item_id}/local-llm-execute`
- added Queue UI controls for explicit prototype execution and dry run
- allows the local LLM environment contract to set `execution_enabled: true` for prototype mode while keeping `operator_gate_required: true`
- requires local-routed queue metadata, prompt preview, local `ollama` provider configuration, reachable health check for real execution, explicit operator confirmation, and local model availability
- blocks `codex_cli` routes, unrouted items, missing confirmation, non-local provider URLs, disabled execution, unavailable health checks, and high/critical risk without operator override
- captures advisory response text in the response payload and optional local result artifact

Boundaries:

- explicit operator action only
- local provider only
- no Codex CLI execution
- no GitHub API, `gh`, issues, PRs, workflow activity, or GitHub mutation
- no automatic agent execution
- no automatic queue start, completion, closeout, commit, push, or repo file mutation
- local LLM output is advisory only

Recommended next milestone:

- M63 - Codex CLI High-Value Lane.

## M61 Local LLM Prompt Preview

Status: Completed locally on `main`.

Delivered:

- added `generate_local_llm_prompt_preview(...)` for copy/paste local LLM prompt previews
- added Hub route `POST /api/local-queue/items/{item_id}/local-llm-prompt-preview`
- added Queue UI controls for generating and viewing a local LLM prompt preview
- supports optional safe artifact output with non-overwrite behavior unless `force=true`
- preview is allowed only for routed queue items recommending `local_reasoning_llm` or `local_coding_llm`
- blocks or warns for unrouted items, `codex_cli` routes, missing local LLM environment/model configuration, and `manual_only` policy without operator override
- preview output includes task details, project context, routing metadata, local-only rules, validation expectations, final response format, and `execution_allowed: false`

Boundaries:

- preview only
- no Ollama call
- no local LLM inference or generation
- no prompt execution
- no Codex CLI execution
- no agent execution
- no GitHub API, `gh`, issues, PRs, workflow activity, or GitHub mutation
- no queue mutation unless the operator explicitly writes a local preview artifact

Follow-up:

- M62 added Operator-Gated Local LLM Execution Prototype.

## M60 Codex CLI Model Profile Contract

Status: Completed locally on `main`.

Delivered:

- added local-only Codex CLI Model Profile Contract at `.aresforge/codex_cli_model_profiles.json`
- added read/update/validation helpers for Codex CLI model profile configuration
- added Hub routes `GET /api/codex-cli/model-profiles` and `POST /api/codex-cli/model-profiles`
- represented `codex_cli` as the fixed Codex engine key
- represented default, high-value, and fast Codex model preferences
- added allowed model lists plus optional per-project and per-agent model restrictions
- enforces `execution_enabled: false` for Codex CLI model profiles while `operator_gate_required` stays true
- added detailed source doc `docs/architecture/CODEX_CLI_MODEL_PROFILE_CONTRACT.md`

Boundaries:

- configuration only
- no Codex CLI execution
- no prompt execution
- no agent execution
- no GitHub API, `gh`, issues, PRs, workflow activity, or GitHub mutation
- no external workflow execution
- no High-Value Codex Lane execution yet

Recommended next milestone:

- M63 - Codex CLI High-Value Lane.

## M59 Local LLM Health Check

Status: Completed locally on `main`.

Delivered:

- added explicitly invoked `check_local_llm_health(...)`
- added Hub route `POST /api/local-llm/health-check`
- reads the M58 Local LLM Environment Contract
- for provider `ollama`, checks only the local `/api/tags` model-list endpoint when explicitly invoked
- reports provider reachability, available model names, configured reasoning/coding model availability, `inference_tested: false`, and `execution_allowed: false`
- rejects non-local provider URLs and prompt/execution payload fields

Boundaries:

- local-only and operator-invoked
- no prompt execution
- no model inference
- no local LLM generation
- no Codex execution
- no agent execution
- no GitHub/`gh`
- no generate/chat/completion endpoint calls
- no queue/project mutation

Follow-up:

- M61 added Local LLM Prompt Preview.
- M62 added Operator-Gated Local LLM Execution Prototype.

## M58 Local LLM Environment Contract

Status: Completed locally on `main`.

Delivered:

- added local-only Local LLM Environment Contract at `.aresforge/local_llm_environment.json`
- added read/update/validation helpers for local LLM environment configuration
- added Hub routes `GET /api/local-llm/environment` and `POST /api/local-llm/environment`
- supported providers: `ollama`, `none`, and `unknown`
- represented provider URL, reasoning/coding/fallback model placeholders, optional context/timeout settings, health-check preference, notes, and timestamps
- originally enforced `execution_enabled: false`; M62 allows `execution_enabled: true` only for the operator-gated local prototype while `operator_gate_required` stays true
- added detailed source doc `docs/architecture/LOCAL_LLM_ENVIRONMENT_CONTRACT.md`

Boundaries:

- configuration only
- no Ollama call
- no health check yet
- no model API call
- no prompt execution, routing execution, local LLM execution, Codex execution, agent execution, GitHub/`gh`, workflow activity, network call, or external execution

Recommended next milestone:

- M59 - Local LLM Health Check.

## M57 Prompt Pack Routing Integration

Status: Completed locally on `main`.

Delivered:

- extended `generate_local_queue_prompt_pack(...)` so prompt packs include per-item routing metadata by default
- included routing fields for agent lane, engine, model, fallback, policy source, routing reason, risk, complexity, escalation, project AI mode, operator override, and `execution_allowed: false`
- represented unrouted items with manual routing guidance
- represented `codex_cli` and local LLM engines as recommendations only, never execution
- added optional routing grouping for prompt packs by agent lane, engine, model, risk level, complexity level, and status
- exposed routing prompt-pack options through the local Hub API and Queue UI

Boundaries:

- prompt packs remain local artifacts/previews only
- one canonical local queue remains the source of truth
- prompt-pack generation does not start, complete, or mutate queue items
- no routing execution, local LLM execution, Codex execution, agent execution, GitHub/`gh`, prompt execution, workflow activity, network call, or external execution

Recommended next milestone:

- M58 - Local LLM Environment Contract.

## M56 Routed Queue Views

Status: Completed locally on `main`.

Delivered:

- added read-only routed queue view helper `read_local_routed_queue_views(...)`
- added Hub route `GET /api/local-queue/routed-views`
- added Queue UI panel for routed view filters and grouped counts
- supported filters for project, status, agent lane, engine, model, fallback engine, risk, complexity, project AI mode, routing policy source, and operator override state
- supported grouped views by agent lane, engine, model, project policy, risk level, complexity level, and status
- handled mixed routed/unrouted items, empty queues, and legacy items without routing metadata

Boundaries:

- one canonical local queue remains the source of truth
- routed queue views are read-only filters over the canonical queue
- no queue storage split
- no prompt-pack routing integration yet
- no routing execution, local LLM execution, Codex execution, agent execution, GitHub/`gh`, prompt execution, workflow activity, network call, or external execution

Recommended next milestone:

- M57 - Prompt Pack Routing Integration.

## M55 Project AI Settings UI

Status: Completed locally on `main`.

Delivered:

- added a Project AI Settings panel to the Projects Hub section
- wired the panel to existing M51 routes `GET /api/projects/{project_id}/ai-settings` and `POST /api/projects/{project_id}/ai-settings`
- operators can view and update `project_ai_mode`, `available_engines`, `disabled_engines`, `default_engine`, optional `default_model`, `operator_override_allowed`, and notes
- UI displays validation status, warnings, blockers, and `next_safe_action`
- invalid settings are surfaced through validation output and are not saved by the API

Boundaries:

- local-only, file-backed, and operator-gated
- settings are routing preferences and future execution configuration only
- no routing execution, local LLM execution, Codex execution, agent execution, GitHub/`gh`, prompt execution, workflow activity, network call, or external execution
- no complex model management UI was added

Recommended next milestone:

- M56 - Routed Queue Views.

## M54 Routing Decision Matrix v1

Status: Completed locally on `main`.

Delivered:

- added recommendation-only routing helpers `recommend_queue_item_routing(...)` and `apply_queue_item_routing_recommendation(...)`
- recommendations use M51 Project AI Settings, M52 Agent and Engine Registry, and M53 Queue Routing Metadata
- added Hub routes `POST /api/local-queue/items/{item_id}/routing-recommendation` and `POST /api/local-queue/items/{item_id}/apply-routing-recommendation`
- added minimal Queue UI controls for Recommend Routing and explicit Apply Routing Metadata
- recommendations include project policy, agent lane, engine, fallback, risk/complexity, routing reason, escalation reason, operator override, and `execution_allowed: false`
- apply writes queue routing metadata only through explicit operator action

Boundaries:

- recommendation-only and local-only
- no local LLM, Codex, real agent, GitHub, `gh`, workflow, prompt, network, or external execution
- no queue storage split
- no metadata write unless the operator explicitly applies a recommendation

Recommended next milestone:

- M55 - Project AI Settings UI.

## M53 Queue Routing Metadata Contract

Status: Completed locally on `main`.

Delivered:

- added default queue routing metadata to queue item views and new queue item creation
- added `default_queue_routing_metadata(...)`, `validate_queue_routing_metadata(...)`, and `update_local_queue_item_routing_metadata(...)`
- added Hub route `POST /api/local-queue/items/{item_id}/routing-metadata`
- Queue item detail now displays routing metadata as read-only context
- supported agent lanes align with M52: `architect_planner`, `coding`, `reviewer_validator`, `documentation`, `test`, `local_operator_assistant`, and `high_value_codex`
- supported engines align with M52: `local_reasoning_llm`, `local_coding_llm`, and `codex_cli`
- supported risk levels are `low`, `medium`, `high`, `critical`, and `unknown`
- supported complexity levels are `low`, `medium`, `high`, and `unknown`

Boundaries:

- one canonical local queue remains the source of truth
- routing metadata is local-only, file-backed, operator-gated, and non-executing
- no routing decisions are computed
- no queue storage split
- no local LLM, Codex, agent, GitHub, `gh`, workflow, network, prompt, or external execution is performed

Recommended next milestone:

- M54 - Routing Decision Matrix v1.

## M52 Agent and Engine Registry Contract

Status: Completed locally on `main`.

Delivered:

- added a read-only Agent and Engine Registry Contract through `read_agent_engine_registry(...)`
- added Hub route `GET /api/agent-engine-registry`
- documented required agent lanes: `architect_planner`, `coding`, `reviewer_validator`, `documentation`, `test`, `local_operator_assistant`, and `high_value_codex`
- documented required engines: `local_reasoning_llm`, `local_coding_llm`, and `codex_cli`
- each lane includes key, display name, purpose, default allowed engines, recommended default engine, risk notes, `execution_allowed: false`, and `routing_only: true`
- each engine includes key, display name, purpose, `execution_allowed: false`, local-only boundary notes, model profile placeholders, availability status, and `operator_gate_required: true`
- Codex CLI is represented as engine `codex_cli` with placeholder-only future model profile fields

Boundaries:

- local-only, read-only, non-executing, and operator-gated
- no routing decisions are executed
- no queue routing metadata is written
- no local LLM, Codex, agent, GitHub, `gh`, workflow, network, or external execution is performed
- no complex UI was added in M52

Recommended next milestone:

- M53 - Queue Routing Metadata Contract.

## M51 Project AI Settings Contract

Status: Completed locally on `main`.

Delivered:

- added a file-backed Project AI Settings Contract at `.aresforge/projects/{project_id}/ai_settings.json`
- added operator functions `read_project_ai_settings(...)`, `update_project_ai_settings(...)`, and `validate_project_ai_settings(...)`
- added Hub API wrappers for `GET /api/projects/{project_id}/ai-settings` and `POST /api/projects/{project_id}/ai-settings`
- settings support `project_ai_mode`, `available_engines`, `disabled_engines`, `default_engine`, optional `default_model`, `operator_override_allowed`, `notes`, and `updated_at`
- supported modes are `balanced`, `local_only`, `codex_only`, `cost_saver`, `high_confidence`, and `manual_only`
- supported engine keys are `local_reasoning_llm`, `local_coding_llm`, and `codex_cli`
- validation rejects unsupported modes/engines, disabled defaults, local-only Codex defaults, Codex-only local defaults, and missing defaults except for `manual_only`

Boundaries:

- local-only, file-backed, non-executing, and operator-gated
- no routing decisions are executed
- no queue routing metadata is written
- no local LLM, Codex, agent, GitHub, `gh`, workflow, network, or external execution is performed
- no Hub UI settings surface was added in M51

Recommended next milestone:

- M52 - Agent and Engine Registry Contract.

## M50 Handoff Generator

Status: Completed locally on `main`.

Delivered:

- added `generate_local_project_handoff(...)` for copy/paste-ready local project handoff generation
- added Hub route `POST /api/local-project/handoff`
- added a Local Project Handoff Generator panel to the Handoff section
- handoff output includes project/repo/branch context, operating rules, latest milestone/commit, architecture boundaries, Hub capabilities, queue/report/progress summary, open queue items, blockers/warnings, evidence/closeout summary, recommended next milestone/instruction, and start-of-next-chat validation commands
- optional local artifact output is supported with safe non-overwrite behavior unless `force=true`

Boundaries:

- local-only, file-backed, read-only unless optional local artifact output is explicitly requested, and operator-gated
- no GitHub API, `gh`, issues, PRs, workflow activity, GitHub mutation, agent execution, Codex execution, local LLM execution, model routing, or external execution
- handoff generation reuses Reports v1 and M48 progress rollup state

Recommended next milestone:

- M51 - Project AI Settings Contract.

## M49 Reports v1

Status: Completed locally on `main`.

Delivered:

- added `read_local_project_reports(...)` for local Reports v1
- added Hub route `GET /api/reports/local-projects`
- added a read-only Reports v1 panel to the existing Reports section
- Reports v1 summarizes project count/statuses, active project, queue totals, counts by status/type/lane, blocked/ready/in-progress work, evidence capture, closeout eligibility, closed/completed work, latest activity, M48 progress rollup, blockers, warnings, limitations, and `next_safe_action`

Boundaries:

- local-only, file-backed, read-only, and operator-gated
- no export/PDF/CSV expansion beyond existing in-page JSON text behavior
- no queue/project mutation, prompt execution, Codex execution, local LLM execution, agent execution, GitHub/`gh`, workflow activity, push, external service call, or routing execution
- routing implementation remains future work after the workflow/reporting sequence

Recommended next milestone:

- M50 - Handoff Generator.

## M48 Project Progress Rollup

Status: Completed locally on `main`.

Delivered:

- added `read_local_project_progress_rollup(...)` for read-only project queue progress inspection
- added Hub route `GET /api/projects/{project_id}/progress-rollup`
- added a minimal Projects UI Project Progress Rollup panel
- rollup summarizes total queue items, status/type/lane counts, ready/blocked/in-progress items, evidence capture count, closeout eligibility, closed/completed count, latest activity, blockers, warnings, and `next_safe_action`

Boundaries:

- local-only, file-backed, read-only, and operator-gated
- rollup does not mutate queue/project state, generate reports, execute prompts, call Codex/local LLMs/agents, route models, call GitHub/`gh`, push code, or run external workflows
- future routing metadata is only reported as future/not implemented
- full Reports v1 remains future work

Recommended next milestone:

- M49 - Reports v1.

## M47 Queue Item Closeout Workflow

Status: Completed locally on `main`.

Delivered:

- added `close_local_queue_item(...)` for explicit local queue item closeout
- added Hub route `POST /api/local-queue/items/{item_id}/closeout`
- added minimal Queue UI controls for operator-gated closeout
- closeout requires eligible `in_progress` status, captured completion evidence, required evidence fields, and a closeout summary
- closeout transitions the queue item to existing `done` status and records `closed_at`, `closed_by`, `closeout_summary`, and `closeout_history`

Boundaries:

- local-only, file-backed, operator-gated closeout
- closeout does not generate prompts, execute prompts, call Codex, call local LLMs, call GitHub, push code, or run external workflows
- Agent/LLM routing remains future work

Recommended next milestone:

- M48 - Project Progress Rollup.

## M46 Completion Evidence Capture

Status: Completed locally on `main`.

Delivered:

- added `capture_local_queue_completion_evidence(...)` for local queue item completion evidence capture
- added Hub route `POST /api/local-queue/items/{item_id}/evidence`
- added minimal Queue UI controls for capturing evidence without completing the item
- evidence capture records `completion_evidence` on the existing queue item while preserving existing queue item data and status
- response includes `next_safe_action` and advisory `closeout_eligible`

Boundaries:

- local-only, file-backed, operator-gated evidence capture
- evidence capture is separate from closeout and does not automatically complete queue items
- no routing implementation, local LLM execution, Codex execution, real agent execution, GitHub integration, or external workflow execution

Recommended next milestone:

- M47 - Queue Item Closeout Workflow.

## M45 Local Hub End-to-End Operator Workflow Validation

Status: Completed locally on `main`.

Delivered:

- added focused Hub end-to-end operator workflow validation in `tests/test_hub_end_to_end_operator_workflow.py`
- validated the existing local Hub path from dashboard inspection through active project context, queue intake, queue detail, readiness, prompt-pack generation, local project report, and queue agent summary
- confirmed prompt-pack generation remains advisory and does not start, complete, or otherwise mutate queue item lifecycle state
- documented the current validated operator workflow across source-of-truth docs

Boundaries:

- validation and documentation only
- no routing implementation, local LLM execution, Codex execution, real agent execution, GitHub integration, or queue storage split
- no backend route additions, no frontend settings UI, no queue schema changes

Recommended next milestone:

- M46 - completion evidence capture for local operator workflow closeout.

## M44A Agent LLM Routing Strategy Documentation Update

Status: Completed locally on `main`.

Delivered:

- added future-state routing source of truth: `docs/architecture/AGENT_LLM_ROUTING_STRATEGY.md`
- documented project-specific AI routing modes, agent lanes, future engines, routing hierarchy, routing metadata, Codex CLI model strategy, and M43 prompt-pack relationship
- clarified that routing decisions should happen before prompt generation
- confirmed the queue should remain one canonical local queue with future routing metadata and filtered routed views/lanes

Boundaries:

- documentation-only milestone
- no backend routes, frontend settings UI, queue schema changes, runtime routing, Codex CLI execution, agent execution, local LLM execution, or model invocation
- no GitHub API, no `gh`, no GitHub issues/PRs/workflow activity, and no GitHub mutation from the app

Recommended next milestone:

- M45 - implement the next small local-first routing/prompt-pack preparation step only after preserving the M44A boundaries.

## M43 Agent Prompt Pack Generator

Status: Completed locally on `main`.

Delivered:

- added operator function `generate_local_queue_prompt_pack` in `src/aresforge/operator/local_project_queue.py`
- added Hub route `POST /api/local-queue/prompt-pack` for local-only prompt-pack generation
- added Queue UI panel controls/results for Agent Prompt Pack generation and copy/paste preview
- optional local artifact output is supported with safe non-overwrite behavior unless `force=true`

Boundaries:

- local-only, file-backed, operator-triggered prompt generation only
- generated packs are copy/paste-ready and manual-run only
- no queue auto-start or auto-complete behavior
- no Codex execution, no agent execution, no LLM/model routing
- no GitHub API, no `gh`, no GitHub mutation, no external service calls

## M42 Queue Item Detail Panel

Status: Completed locally on `main`.

Delivered:

- added a read-only Queue Item Detail Panel in Hub Queue section
- panel displays selected queue item details, source/context fields, and parsed M41 notes metadata
- panel attempts read-only readiness context load for selected item
- added explicit empty and error states for detail/readiness visibility

Boundaries:

- read-only/advisory detail panel
- no new lifecycle mutation behavior introduced by the panel
- no auto-start, no auto prompt generation
- no GitHub/`gh`/GitHub mutation behavior
- no agent/Codex/LLM execution behavior

## M41 Active Project Task Intake v2

Status: Completed locally on `main`.

Delivered:

- improved Active Project intake form with structured fields for local queue item quality
- intake now captures source, requested outcome, acceptance notes, and validation notes in addition to title/details/type/priority/tags
- retained `POST /api/local-queue/items` and extended optional payload handling without adding new routes
- persisted intake quality fields via existing local queue `source` and `notes` fields (file-backed, backward compatible)

Boundaries:

- local-only, operator-gated, file-backed queue creation only
- no auto-start and no auto prompt generation
- no GitHub/`gh`/GitHub mutation behavior
- no agent execution and no Codex/LLM execution behavior

## M40 Dashboard Milestone Closeout And Docs Reconciliation

Status: Completed locally on `main`.

Scope:

- documentation and validation baseline reconciliation only for dashboard milestones M35-M39
- no new dashboard runtime behavior, backend routes, or frontend interaction changes

Reconciled dashboard source-of-truth (M35-M39):

- M35: local operator summary contract in `src/aresforge/operator/local_dashboard_summary.py`
- M35: `GET /api/dashboard/summary` exposed through Hub API/server for read-only Home dashboard use
- M36: Home dashboard cards/status panels consume `GET /api/dashboard/summary`
- M37: manual refresh only plus loading/empty/error states and last-successful-load label
- M38: Home deep links into existing Workspace/Projects/Queue/Repos/Reports sections
- M39: queue status drilldowns and advisory agent lane drilldowns

Current frontend module structure (dashboard-related):

- entrypoint: `src/aresforge/hub/static/app.js`
- Home section: `src/aresforge/hub/static/js/sections/home.js`
- Queue section: `src/aresforge/hub/static/js/sections/queue.js`
- Projects section: `src/aresforge/hub/static/js/sections/projects.js`
- Repos section: `src/aresforge/hub/static/js/sections/repos.js`
- Reports section: `src/aresforge/hub/static/js/sections/reports.js`

Boundary posture (reconfirmed):

- local-only
- file-backed/local inspection
- operator-gated
- read-only/advisory dashboard posture
- no GitHub API calls
- no `gh` calls
- no GitHub issues/PRs/workflows mutation
- no real agent execution
- no Codex execution from the Hub app
- no LLM/model routing or invocation

Validation baseline for dashboard closeout:

- `python -m pytest tests/test_hub_ui_foundation.py tests/test_hub_dashboard_summary_api.py tests/test_local_dashboard_summary.py tests/test_hub_project_factory_api.py tests/test_hub_local_queue_lifecycle_api.py tests/test_hub_active_project_api.py tests/test_local_project_factory.py tests/test_local_active_project.py`
- smoke:
  - `python -m aresforge inspect-local-queue-agent-summary`
  - `python -m aresforge inspect-local-project-report`
- diff check:
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
## M36 Hub Dashboard UI Cards And Status Panels

Status: Completed locally on `main`.

Delivered:

- Home dashboard now consumes `GET /api/dashboard/summary`
- read-only cards/panels for project summary, queue summary, advisory agent lanes, repo summary, blockers/warnings, and next safe action
- manual operator refresh path retained; no polling/auto-refresh added

Boundary posture:

- local-only and read-only/advisory UI
- no GitHub API calls and no `gh` calls
- no agent/Codex/model execution
- no LLM/model routing

## M35 Hub Dashboard Data Contract And Read-Only Metrics

Status: Completed locally on `main`.

Delivered:

- local-only read-only Hub dashboard summary operator contract
- new Hub API route: `GET /api/dashboard/summary`
- stable JSON payload for Home dashboard data consumption in a future UI pass

Boundary posture:

- local-only and file-backed inspection
- read-only/advisory response
- no GitHub API calls
- no `gh` calls
- no network calls beyond existing local Hub API behavior
- no agent/Codex/model execution

Scope note:

- Home dashboard UI cards/panels are intentionally deferred to M36.

## Local LLM Planning Package (Documentation-Only)

Local LLM integration planning is now documented but not implemented.

Planning documents added:

- `docs/architecture/LOCAL_LLM_STRATEGY.md`
- `docs/operator/OLLAMA_LOCAL_SETUP.md`
- `docs/architecture/LLM_TASK_ROUTING_PLAN.md`
- `docs/context/LOCAL_LLM_DECISION_RECORD.md`

Current status:

- no live Ollama execution is wired into AresForge
- no agent workflow calls a local model
- no cloud LLM dependency has been introduced
- no network execution has been introduced
- no GitHub API usage has been introduced
- the documented baseline uses one local coding model and one local reasoning model, loaded separately
- future implementation must remain local-first and operator-gated

## M34 Frontend Modularization Closeout And Docs Reconciliation

Status: Completed locally on `main`.

Frontend module structure now finalized:

- entrypoint: `src/aresforge/hub/static/app.js` (ES module entrypoint loaded by `index.html`)
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

Validation status used for closeout:

- `python -m pytest tests/test_hub_ui_foundation.py tests/test_hub_project_factory_api.py tests/test_hub_local_queue_lifecycle_api.py tests/test_hub_active_project_api.py tests/test_local_project_factory.py tests/test_local_active_project.py`
- smoke:
  - `python -m aresforge inspect-local-queue-agent-summary`
  - `python -m aresforge inspect-local-project-report`

Boundary posture reconfirmed:

- local-first
- file-backed
- operator-gated
- no real agent execution
- no GitHub mutation
- no network execution beyond existing local Hub API behavior

Recommended next milestone after M34:

- M35 - Hub Dashboard Data Contract And Read-Only Metrics
- scope:
  - read-only Home dashboard metrics
  - total projects
  - active project summary
  - queue item counts by status
  - advisory agent lane counts from local summaries
  - repo status summary from existing local inspection outputs
  - no new GitHub calls
  - no real agent execution
  - no mutation

## M28 Hub Orchestration And Escalation Section Modules

Status: Completed locally on `main`.

Delivered M28 items:

- extracted Orchestration section logic into `src/aresforge/hub/static/js/sections/orchestration.js`
- extracted Escalation section logic into `src/aresforge/hub/static/js/sections/escalation.js`
- kept `src/aresforge/hub/static/app.js` as the frontend entrypoint and startup orchestrator
- moved Orchestration/Escalation rendering, plan loading, reset/submit bindings, and section-local helpers into the new modules
- preserved local-only/operator-gated messaging, DOM ids, and API endpoint paths
- updated static frontend tests to validate new section modules and import wiring

M28 boundary posture:

- local-only static/frontend refactor
- no GitHub API calls
- no `gh` calls
- no new network calls
- no agent execution
- no model routing/invocation
- no UI redesign, DOM id changes, or endpoint path changes

## M17 Local Queue Execution-Prep Lifecycle

Status: Completed locally on `main` (no push performed).

Delivered M17 local queue workflow:

- `python -m aresforge add-local-queue-item --title <title> ...`
- `python -m aresforge inspect-local-queue-item-readiness --item-id <item_id>`
- `python -m aresforge start-local-queue-item --item-id <item_id>`
- `python -m aresforge generate-local-queue-item-codex-prompt --item-id <item_id> [--output <path>]`
- human runs Codex manually using the generated prompt
- `python -m aresforge complete-local-queue-item --item-id <item_id> --commit-hash <hash> --validation-summary <text> ...`

M17 completion evidence recorded locally in `.aresforge/queue/work_items.json` includes:

- `completed_at`
- `completed_by`
- `completion_commit`
- `validation_summary`
- optional `evidence_note`, `tests_run`, `changed_files`, and `artifact_paths`

M17 boundary posture:

- local-first and file-backed
- no GitHub API calls
- no `gh` calls
- no GitHub mutation/sync execution
- no automatic Codex execution
- no agent execution
- no model routing/invocation
- no remote commit verification

## M27 Hub Reports Section Module

Status: Completed locally on `main`.

Delivered M27 items:

- extracted Reports section logic into `src/aresforge/hub/static/js/sections/reports.js`
- kept `src/aresforge/hub/static/app.js` as the browser entrypoint and startup orchestrator
- moved Reports dashboard rendering, local project report rendering, report slice loading, export helpers, and Reports-specific bindings into the new section module
- kept non-Reports orchestration and shared cross-section flows in `app.js` so this milestone stays limited to Reports UI ownership
- updated static frontend tests to validate the new Reports section module and single-path Reports bindings

M27 boundary posture:

- local-only static/frontend refactor
- no GitHub API calls
- no `gh` calls
- no new network calls
- no agent execution
- no model routing/invocation
- no UI redesign, DOM id changes, or endpoint path changes

## M26 Hub Projects And Repos Section Modules

Status: Completed locally on `main`.

Delivered M26 items:

- extracted Projects section logic into `src/aresforge/hub/static/js/sections/projects.js`
- extracted Repos section logic into `src/aresforge/hub/static/js/sections/repos.js`
- kept `src/aresforge/hub/static/app.js` as the browser entrypoint and startup orchestrator
- moved Projects list rendering, read-only rendering, selector refresh, and Projects-specific bindings into the Projects section module
- moved Repos list rendering, repo loading, repo inspection, and Repos-specific bindings into the Repos section module
- kept project-factory lifecycle orchestration in `app.js` so this milestone stays limited to Projects/Repos UI ownership
- updated static frontend tests to validate the new Projects/Repos section modules and single-path bindings

M26 boundary posture:

- local-only static/frontend refactor
- no GitHub API calls
- no `gh` calls
- no new network calls
- no agent execution
- no model routing/invocation
- no UI redesign, DOM id changes, or endpoint path changes

## M25 Hub Queue Section Module

Status: Completed locally on `main`.

Delivered M25 items:

- extracted Queue section logic into `src/aresforge/hub/static/js/sections/queue.js`
- kept `src/aresforge/hub/static/app.js` as the browser entrypoint and startup orchestrator
- moved queue read-only summary rendering/loading and queue item card rendering into the new section module
- moved queue-only actions into the new section module: apply active-project defaults, filter to active project, filter submit/reset, and queue form submit
- kept local queue lifecycle internals in `app.js` to avoid mixing higher-risk flow extraction into this milestone
- updated static frontend tests to validate the new queue section module and single-path queue bindings

M25 boundary posture:

- local-only static/frontend refactor
- no GitHub API calls
- no `gh` calls
- no new network calls
- no agent execution
- no model routing/invocation
- no UI redesign, DOM id changes, or endpoint path changes

## M24 Hub Home And Workspace Section Modules

Status: Completed locally on `main`.

Delivered M24 items:

- extracted Home section logic into `src/aresforge/hub/static/js/sections/home.js`
- extracted Workspace section logic into `src/aresforge/hub/static/js/sections/workspace.js`
- kept `src/aresforge/hub/static/app.js` as the browser entrypoint and startup orchestrator
- moved Home dashboard rendering/loading and Home-specific action binding behind module exports
- moved Workspace rendering/loading, empty-state rendering, and quick-action binding behind module exports
- updated static frontend tests to validate the new section modules, preserved entrypoint loading, and single-path workspace bindings

M24 boundary posture:

- local-only static/frontend refactor
- no GitHub API calls
- no `gh` calls
- no new network calls
- no agent execution
- no model routing/invocation
- no UI redesign, DOM id changes, or endpoint path changes

## M23 Hub Frontend Modularization Foundation

Status: Completed locally on `main`.

Delivered M23 items:

- switched Hub static loading from a plain script tag to browser-native ES module loading for `src/aresforge/hub/static/app.js`
- extracted shared frontend primitives into:
  - `src/aresforge/hub/static/js/core/dom.js`
  - `src/aresforge/hub/static/js/core/http.js`
  - `src/aresforge/hub/static/js/core/state.js`
- kept `app.js` as the main entrypoint/orchestrator for existing Hub domain logic
- removed the unused `renderRunningActionsAgentsPlaceholders` helper
- consolidated duplicated workspace quick-action binding so workspace buttons bind once
- updated static frontend tests to validate the module foundation without forcing all frontend strings to remain in `app.js`

M23 boundary posture:

- local-only static/frontend refactor
- no GitHub API calls
- no `gh` calls
- no new network calls
- no agent execution
- no model routing/invocation
- no UI redesign and no DOM id changes

## M16 Hub UI Foundations And Local Validation Closeout

Status: Completed locally on `main` (no push performed).

Delivered M16 items:

- Home dashboard API wiring (`/api/local-project-dashboard`, `/api/local-project-report`, `/api/local-projects`)
- Home dashboard read-only UI foundation
- Projects page read-only UI foundation
- Queue page read-only UI foundation (`/api/local-queue-agent-summary`)
- Reports page read-only UI foundation

Current boundary posture:

- local-first and local-only control-plane read/report surfaces
- no GitHub API calls
- no `gh` calls
- no GitHub mutation/sync execution
- no agent execution
- no model routing/invocation

Validation commands used for M16 closeout:

- `git diff --check`
- `python -m pytest tests/test_roadmap_db_control.py tests/test_config_and_migrations.py tests/test_cli.py`
- `python -m pytest tests/test_hub_project_factory_api.py tests/test_hub_active_project_api.py tests/test_hub_ui_foundation.py`
- `python -m pytest tests/test_local_project_dashboard.py tests/test_local_project_readiness.py tests/test_local_queue_agent_summary.py tests/test_local_project_report.py`
- `python -m pytest`
- smoke:
  - `python -m aresforge inspect-local-project-dashboard`
  - `python -m aresforge list-local-projects`
  - `python -m aresforge inspect-local-queue-agent-summary`
  - `python -m aresforge inspect-local-project-report`

## M14 Source-of-Truth Reconciliation Snapshot

- Operating mode for current local foundation work:
  - local-first
  - direct-on-`main`
  - read-only/report-planning emphasis for new dashboard/report surfaces
- Safety restrictions remain explicit:
  - no GitHub API calls
  - no `gh` calls
  - no GitHub issue/PR mutation from these local read-model/report commands
  - no agent execution
  - no LLM routing or invocation
  - no background scheduler/daemon behavior
- Historical milestone record:
  - M9 through M13 were completed, validated, committed, and pushed before this chat.
  - M14 local foundation additions are now present locally on `main` and validated in this chat.

M14 local read-model/report command additions now available:

- `python -m aresforge inspect-local-project-dashboard`
- `python -m aresforge list-local-projects`
- `python -m aresforge inspect-local-project-readiness --project-id <id>`
- `python -m aresforge inspect-local-queue-agent-summary`
- `python -m aresforge inspect-local-project-report`

Targeted validation bundle for this local foundation layer:

- `git diff --check`
- `python -m pytest tests/test_roadmap_db_control.py tests/test_config_and_migrations.py tests/test_cli.py`
- targeted local suites as needed:
  - `python -m pytest tests/test_local_project_dashboard.py`
  - `python -m pytest tests/test_local_project_readiness.py`
  - `python -m pytest tests/test_local_queue_agent_summary.py`
  - `python -m pytest tests/test_local_project_report.py`

## M7 Local Queue Transition Planning And Gated Queue Move

- Added local queue transition planning and gated queue move control:
  - `python -m aresforge plan-work-item-queue-transition --work-item-id <id> --target-queue-id <id> [--format json|markdown]`
  - `python -m aresforge move-work-item-queue --work-item-id <id> --target-queue-id <id> [--actor <actor>] [--details-file <path>] [--format json|markdown]`
- Planning remains read-only and deterministic.
- Queue move remains local-only, does not execute agents, and does not call GitHub.

## M8 Local Execution Dossier

- Added local read-only execution dossier packaging for one work item:
  - `python -m aresforge build-work-item-execution-dossier --work-item-id <id> [--format json|markdown]`
- The dossier packages readiness, lifecycle, queue context, roadmap links, dependencies, related events, and a suggested operator prompt.
- M8 remains local-only and read-only. It does not execute agents, mutate GitHub, or implement Hub UI.

## M9 Local Implementation Handoff Command

- Added a local implementation handoff command:
  - `python -m aresforge handoff-work-item-to-implementation --work-item-id <id> [--actor <actor>] [--details-file <path>] [--format json|markdown]`
- The command reuses queue transition gates and returns a post-move execution dossier for the updated state.
- M9 remains local-only and does not execute agents, call GitHub, or implement Hub UI.

## M10 Local Project/Queue Dashboard CLI

- Added a read-only local dashboard command:
  - `python -m aresforge inspect-project-queue-dashboard [--project-id <id>] [--format json|markdown]`
- The dashboard summarizes work item totals, queue state, readiness state, roadmap state, recent events, and next safe actions.
- M10 does not implement Hub UI, execute agents, or call GitHub.

## M11 Local Roadmap Dependency Management

- Added local roadmap dependency management commands:
  - `python -m aresforge add-roadmap-task-dependency --task-id <id> --depends-on-task-id <id> [--dependency-type blocks] [--actor <actor>] [--details-file <path>] [--format json|markdown]`
  - `python -m aresforge remove-roadmap-task-dependency --task-id <id> --depends-on-task-id <id> [--actor <actor>] [--details-file <path>] [--format json|markdown]`
  - `python -m aresforge inspect-roadmap-task-dependencies [--task-id <id>] [--project-id <id>] [--format json|markdown]`
- Dependencies can now be added, inspected, and removed locally.
- Readiness gates can use these dependencies to explain blockers.
- M11 includes no GitHub calls, no agent execution, and no Hub UI.

## M12 Local Operator Prompt Export

- Added local export of execution dossier suggested operator prompts:
  - `python -m aresforge export-work-item-operator-prompt --work-item-id <id> --output <path> [--force] [--format json|markdown]`
- Export writes a UTF-8 prompt file for human handoff.
- M12 does not execute agents, call GitHub, or implement Hub UI.

## M46 Project Factory Source-of-Truth Realignment

Current state on `main` includes M43-M45 and establishes a local-first Hub control plane plus a partial project-factory shell:

- managed project/repo registry
- active project selection and context
- active project dashboard/workbench
- active project intake into local queue
- local queue, agent profile, orchestration planning, escalation planning, handoff, and local closeout tooling
- explicit planning boundaries for later GitHub sync/mutation

Important: the full end-to-end project factory loop is not yet complete. Missing pieces still include new-project wizarding, repo create/link apply flow, scope+architecture contract flow, milestone/issue generation from scope, explicit GitHub issue/milestone apply, and agent run execution lifecycle.

Canonical workflow source-of-truth:

- `docs/architecture/PROJECT_FACTORY_WORKFLOW.md`

Next milestone after this M46 realignment:

- M47 New Project Wizard

## Current Phase

M42 first-run bootstrap and seed wizard for local AresForge Hub setup.

## Current Goal

Implement and document M42 so the Hub can inspect local setup readiness, generate a plan-only bootstrap preview, and apply local file-backed bootstrap seeding for first-run operator workflows.

## M42 First-Run Bootstrap And Seed Wizard (Local-Only)

- Added local bootstrap operator module:
  - `src/aresforge/operator/local_bootstrap_wizard.py`
- Added local bootstrap CLI commands:
  - `python -m aresforge inspect-bootstrap-status [--repo-path <path>]`
  - `python -m aresforge plan-bootstrap [--repo-path <path>] [--format json|markdown] [--seed-sample-work]`
  - `python -m aresforge apply-bootstrap [--repo-path <path>] [--force] [--seed-sample-work] [--format json|markdown]`
- Added local Hub bootstrap API endpoints:
  - `GET /api/bootstrap/status`
  - `GET /api/bootstrap/plan`
  - `POST /api/bootstrap/apply`
- Added Hub Bootstrap setup section for status, plan preview, force/sample toggles, and apply actions.
- Bootstrap initializes missing local state files under `.aresforge/`:
  - `.aresforge/state/project_state.json`
  - `.aresforge/projects/projects.json`
  - `.aresforge/queue/work_items.json`
  - `.aresforge/agents/agents.json`
- Bootstrap registers AresForge as a managed project/repo with local GitHub metadata.
- Bootstrap seeds default agent profiles/handoff targets and optional sample next-phase queue milestones.

M42 safety posture:

- local-only and file-backed
- no GitHub API calls
- no `gh` calls
- no GraphQL/REST calls
- no network service calls
- no live GitHub validation/discovery
- no local/cloud/Codex/ChatGPT/Ollama model invocation

## M21 Active Project Workspace (Polish & Local-Only)

Status: Completed locally on `main` and reconciled with tests and UI foundations.

Delivered M21 items:

- Polished the Active Project Workspace UI in the Hub with clearer operator-first guidance and empty states.
- Added explicit local-only messaging on quick actions and workspace cards (labels now include "(local-only)").
- Wired workspace quick actions in `app.js` to navigate/focus operator flows (refresh, continue intake, open queue, select project).
- Hardened tests with `tests/test_active_project_workspace.py` to validate the `get_active_project_workspace` payload for empty and seeded states.

Validation and boundary posture:

- Local-first and operator-driven only: all UI and API surfaces are read/report and plan-only.
- No GitHub API calls, no `gh` calls, no agent/model/Codex execution, no network mutation.
- Tests added and validated locally; full test run reported passing (207 passed, 1 warning) during local validation.

## M41 GitHub-Linked Project/Repo Model (Local-Only)

- Extended local managed project/repo registry schema for GitHub identity fields.
- Projects now track local GitHub linkage metadata:
  - `primary_repo_id`
  - `github_owner`
  - `github_repo`
  - `github_url`
  - `github_default_branch`
  - `github_connection_status`
- Repos now track local GitHub and local git inspection metadata:
  - `github_owner`
  - `github_repo`
  - `github_url`
  - `github_default_branch`
  - `github_connection_status`
  - `local_git_branch`
  - `local_git_head`
  - `local_git_remote_url`
  - `local_git_status_summary`
- GitHub identity rules now support:
  - owner/repo/url local storage
  - URL parsing for GitHub HTTPS and SSH remote formats
  - URL generation from owner/repo when URL is omitted
  - project-level identity derivation from primary repo when needed
  - project primary repo linkage enforcement when repos exist
- Added local-only git inspection support (no network):
  - `git -C <path> remote get-url origin`
  - `git -C <path> branch --show-current`
  - `git -C <path> rev-parse HEAD`
  - `git -C <path> status --short`
- Added CLI command:
  - `python -m aresforge inspect-managed-repo-github-link --project-id <id> --repo-id <id> [--registry-path <path>] [--inspect-local-git] [--format json|markdown]`
- Extended Hub API and UI with M41 GitHub-linked surfaces:
  - project/repo forms include GitHub metadata
  - repo-local action for local git link inspection
  - report/home/settings include GitHub linkage readiness summaries and boundary notes

M41 safety posture:

- local-only metadata management and inspection
- no GitHub API calls
- no `gh` calls
- no GraphQL or REST calls
- no network service calls
- no live GitHub validation
- no local/cloud/Codex/ChatGPT/Ollama invocation

Future (not implemented in M41):

- explicitly gated GitHub sync/validation execution under additional safeguards and approvals

## M40 Reporting, Dashboard Polish, And Operator Workflows

- Extended local Hub API with local-only report endpoints:
  - `GET /api/reports/dashboard`
  - `GET /api/reports/action-center`
  - `GET /api/reports/readiness`
  - `GET /api/reports/operator-workflows`
  - `GET /api/reports/export`
- Expanded local dashboard helper (`src/aresforge/operator/local_project_dashboard.py`) to emit a stable report schema including:
  - project/repo/queue/agent/handoff/orchestration/escalation/docs summaries
  - readiness indicators
  - action center
  - risks, warnings, recommended next actions
  - operator workflow cards
  - explicit boundary confirmations
- Hub Home now acts as a polished operator dashboard:
  - top-level status cards
  - readiness indicators
  - action-center preview
  - recommended next actions
  - quick workflow cards
- Hub Reports now provides control-plane report sections and in-page export/copy actions.
- Hub Settings now shows default local paths, artifact folders, boundary confirmations, known limitations, and next milestone scope.
- M40 remains local-only and workflow/report oriented:
  - no agent execution
  - no local LLM invocation
  - no cloud LLM invocation
  - no Codex invocation
  - no ChatGPT invocation
  - no Ollama invocation
  - no GitHub calls
  - no `gh` calls
  - no network/external API calls
  - no live GitHub sync
  - no authentication or production deployment implementation
- Future work after M40:
  - richer guided UI workflows
  - optional execution gates with explicit operator approval
  - authentication if exposed beyond localhost
  - controlled GitHub sync execution behind safeguards
  - optional LLM execution behind explicit user-approved gates

## M39 Agent, Handoff, Orchestration, And Escalation Hub Screens

- Extended local Hub API with local-only M39 endpoints:
  - `GET /api/agents`
  - `POST /api/agents`
  - `GET /api/agents/{agent_id}`
  - `GET /api/handoff-targets`
  - `POST /api/handoff-targets`
  - `GET /api/handoff-targets/{target_id}`
  - `GET /api/handoff/preview`
  - `POST /api/orchestration/plan`
  - `GET /api/orchestration/plan`
  - `POST /api/escalation/plan`
  - `GET /api/escalation/plan`
- Extended Hub frontend with interactive sections:
  - Agents list and add/update form
  - Handoff targets list and add/update form
  - Handoff preview refresh and local-only preview panel
  - Orchestration filter controls and plan visualization
  - Escalation filter controls and classification visualization
- M39 data model linkage:
  - agent and handoff target operations reuse M34 local profiles storage
  - orchestration plan responses reuse M35 plan-only orchestration logic
  - escalation plan responses reuse M36 plan-only escalation logic
  - handoff preview reuses M26 local handoff package logic without posting anywhere
- M39 boundary confirmations:
  - local-only
  - file-backed
  - plan-only for orchestration and escalation
  - no agent execution
  - no local LLM calls
  - no cloud LLM calls
  - no Codex execution
  - no ChatGPT calls
  - no Ollama calls
  - no `gh`
  - no GitHub API calls
  - no network service calls
  - no external API calls
- M39 scope boundary:
  - reporting/dashboard polish and expanded operator workflows remain planned for M40
  - authentication and production deployment remain unimplemented
  - live GitHub sync remains unimplemented

## M38 Hub Project, Repo, And Queue Management

- Extended local Hub API with local-only management endpoints:
  - `GET /api/projects`
  - `POST /api/projects`
  - `GET /api/projects/{project_id}`
  - `GET /api/projects/{project_id}/repos`
  - `POST /api/projects/{project_id}/repos`
  - `GET /api/queue`
  - `POST /api/queue`
  - `GET /api/queue/{item_id}`
  - `PATCH /api/queue/{item_id}`
  - `GET /api/settings`
- Extended Hub frontend with interactive sections:
  - Projects list and add/update project form
  - Repos project selector, repo list, and add/update repo form
  - Queue filters, item list/cards, add/update item form, and quick status update controls
  - Home readiness hints for project/repo/queue management
  - Settings storage-path display for local registry and queue files
- M38 data model linkage:
  - project/repo operations reuse M32 managed-project registry storage
  - queue operations reuse M33 local project queue storage
  - create/update behavior is idempotent where operator contracts already support idempotent registration/update
- M38 local-first/file-backed boundary:
  - no `gh`
  - no GitHub API calls
  - no network service calls
  - no local LLM calls
  - no cloud LLM calls
  - no Codex calls
  - no ChatGPT calls
  - no Ollama calls
  - no external API calls
- M38 scope boundary:
  - agent, handoff, orchestration, and escalation screens remain planned for M39
  - reporting/dashboard polish and operator workflow expansion remain planned for M40
  - authentication and production deployment remain unimplemented
  - live GitHub sync and agent/LLM execution remain unimplemented

## M37 AresForge Hub UI Foundation

- Added local Hub package:
  - `src/aresforge/hub/`
  - `src/aresforge/hub/api.py`
  - `src/aresforge/hub/server.py`
  - `src/aresforge/hub/static/index.html`
  - `src/aresforge/hub/static/app.js`
  - `src/aresforge/hub/static/styles.css`
- Added local Hub command:
  - `python -m aresforge serve-hub [--host <host>] [--port <port>] [--open-browser]`
- Default Hub host/port behavior:
  - host defaults to `127.0.0.1`
  - port defaults to `8765`
  - browser auto-open is off by default and only opens localhost when `--open-browser` is supplied
- Added local API shell endpoints:
  - `GET /api/health`
  - `GET /api/summary`
  - `GET /api/docs/status`
- Added local dashboard helper:
  - `src/aresforge/operator/local_project_dashboard.py`
- M37 Hub scope:
  - server + API shell + static frontend shell
  - persistent navigation (Home/Projects/Repos/Queue/Agents/Handoff/Orchestration/Escalation/Reports/Settings)
  - Home summary cards and warnings/actions using local files where available
  - docs status endpoint and Settings boundary confirmations
  - placeholder sections for M38-M40 surfaces
- M37 safety posture:
  - local-first and local-only serving path
  - binds to `127.0.0.1` by default
  - no `gh`
  - no GitHub API calls
  - no network service calls
  - no local LLM calls
  - no cloud LLM calls
  - no Codex calls
  - no ChatGPT calls
  - no Ollama calls
  - no external API calls
  - no agent execution
  - no live GitHub sync
  - no authentication implementation yet
  - no production deployment implementation yet

## M36 Cloud LLM Escalation Planner

- Added local escalation planner command:
  - `python -m aresforge plan-llm-escalation [--item-id <id>] [--project-id <id>] [--repo-id <id>] [--status <status>] [--queue-path <path>] [--profiles-path <path>] [--orchestration-plan <path>] [--output <path>] [--format json|markdown] [--force]`
- Added local escalation planner module:
  - `src/aresforge/operator/local_llm_escalation.py`
- Default escalation artifact folder:
  - `artifacts/escalation/`
- Planner reads local inputs where available:
  - M33 queue file (`.aresforge/queue/work_items.json` by default)
  - M34 profiles file (`.aresforge/agents/agents.json` by default)
  - optional M35 orchestration plan file when supplied via `--orchestration-plan`
- Missing files are warning-only and produce reduced output rather than hard failure.
- Plan output includes:
  - selected work items and available agents
  - per-item classification and reasons
  - category buckets: `local_llm_suitable`, `codex_suitable`, `cloud_llm_recommended`, `human_required`, `blocked_or_needs_clarification`
  - recommended handoff targets and copy/paste prompt guidance
  - risk warnings, next actions, and explicit boundary confirmations
- M26 handoff linkage:
  - handoff package includes latest escalation artifact when found under `artifacts/escalation/`
  - otherwise includes an escalation capability note
- M36 safety posture:
  - local-only escalation planning
  - plan-only
  - cloud escalation is advisory only
  - no LLM invocation
  - no local LLM calls
  - no cloud LLM calls
  - no Codex execution
  - no ChatGPT calls
  - no GitHub calls
  - no `gh` calls
  - no network calls

## M35 Multi-Agent Orchestration Planner

- Added local orchestration planner command:
  - `python -m aresforge plan-agent-orchestration [--project-id <id>] [--repo-id <id>] [--status <status>] [--queue-path <path>] [--profiles-path <path>] [--registry-path <path>] [--output <path>] [--format json|markdown] [--force]`
- Added local orchestration planner module:
  - `src/aresforge/operator/local_agent_orchestration.py`
- Default orchestration artifact folder:
  - `artifacts/orchestration/`
- Planner reads local inputs where available:
  - M33 queue file (`.aresforge/queue/work_items.json` by default)
  - M34 profiles file (`.aresforge/agents/agents.json` by default)
  - M32 registry file (`.aresforge/projects/projects.json` by default)
- Missing files are warning-only and produce reduced plans rather than hard failures.
- Plan includes:
  - selected work items
  - available agents
  - recommended assignments
  - dependency ordering
  - blocked/unassigned items
  - handoff prompts
  - risk warnings
  - next actions
  - explicit boundary confirmations
- Assignment behavior:
  - preserves queue `assigned_agent` when present in profiles
  - warns and leaves unassigned when `assigned_agent` is missing from profiles
  - recommends by `item_type`, role preference, and `allowed_item_types`
- Dependency behavior:
  - respects `dependencies` order
  - detects unresolved `blocked_by` blockers
  - reports circular dependency risks without crashing
- M26 handoff linkage:
  - handoff package includes latest orchestration artifact when found under `artifacts/orchestration/`
  - otherwise includes an orchestration capability note
- M35 safety posture:
  - local-only orchestration planning
  - plan-only
  - no agent execution
  - no local LLM invocation
  - no cloud LLM invocation
  - no `gh`
  - no GitHub API calls
  - no network access

## M34 Local LLM Agent Profiles And Handoff Targets

- Added local agent profile defaults under `.aresforge/agents/agents.json`.
- Agent profiles schema stores `schema_version`, `updated_at`, `agents`, and `handoff_targets`.
- Agent profile records support role, execution mode, strengths/constraints, allowed item types, escalation metadata, status, tags, notes, and timestamps.
- Handoff target records support descriptive target type metadata, local command placeholder fields, input/output formats, safety notes, status, tags, notes, and timestamps.
- New local-only command surface:
  - `python -m aresforge init-agent-profiles [--path <path>] [--force] [--with-defaults]`
  - `python -m aresforge register-agent-profile --agent-id <id> --name <name> --role <role> [--profiles-path <path>] [--description <text>] [--execution-mode <mode>] [--model-preference <value>] [--strength <text>]... [--constraint <text>]... [--allowed-type <type>]... [--escalation-allowed true|false] [--handoff-target-id <id>] [--status <status>] [--tag <tag>]... [--notes <text>]`
  - `python -m aresforge register-handoff-target --target-id <id> --name <name> --target-type <type> [--profiles-path <path>] [--description <text>] [--local-command <command>] [--input-format <format>] [--output-format <format>] [--safety-note <text>]... [--status <status>] [--tag <tag>]... [--notes <text>]`
  - `python -m aresforge inspect-agent-profiles [--profiles-path <path>] [--role <role>] [--execution-mode <mode>] [--status <status>] [--format json|markdown]`
  - `python -m aresforge inspect-agent-profile --agent-id <id> [--profiles-path <path>] [--format json|markdown]`
  - `python -m aresforge inspect-handoff-target --target-id <id> [--profiles-path <path>] [--format json|markdown]`
- `init-agent-profiles --with-defaults` seeds generic local-first defaults for architect, implementer, tester, documentation, reviewer, operator, local-llm-general, and cloud-escalation profiles.
- Agent profile registration is idempotent by `agent_id`; handoff target registration is idempotent by `target_id`.
- Agent registration allows unresolved `handoff_target_id` values and returns warning-only guidance for future linkage.
- M26 handoff generation now includes local agent profile summary when profiles exist.
- M35 orchestration planning consumes M34 agent profiles and handoff-target metadata for assignment and handoff prompt generation.
- M34 safety posture:
  - local-only configuration and planning surface
  - no `gh`
  - no GitHub API calls
  - no network access
  - no local LLM invocation
  - no cloud LLM invocation
  - no agent execution/orchestration in this milestone

## M33 Local Project Queue And Work Tracking

- Added a local project queue under `.aresforge/queue/work_items.json`.
- Queue schema stores `schema_version`, `updated_at`, and `work_items`.
- Work items support local planning fields for cross-project tracking, including `project_id`, `repo_id`, dependency links, and `assigned_agent`.
- New local-only command surface:
  - `python -m aresforge init-project-queue [--path <path>] [--force]`
  - `python -m aresforge add-queue-item --item-id <id> --project-id <id> --repo-id <id> --title <title> [--queue-path <path>] [--registry-path <path>] [--description <text>] [--status <status>] [--priority <priority>] [--type <type>] [--tag <tag>]... [--depends-on <item_id>]... [--blocked-by <item_id>]... [--assigned-agent <agent_id>] [--source <source>] [--notes <text>]`
  - `python -m aresforge update-queue-item --item-id <id> [--queue-path <path>] [--project-id <id>] [--repo-id <id>] [--status <status>] [--priority <priority>] [--type <type>] [--title <title>] [--description <text>] [--tag <tag>]... [--depends-on <item_id>]... [--blocked-by <item_id>]... [--assigned-agent <agent_id>] [--source <source>] [--notes <text>]`
  - `python -m aresforge inspect-project-queue [--queue-path <path>] [--project-id <id>] [--repo-id <id>] [--status <status>] [--type <type>] [--assigned-agent <agent_id>] [--format json|markdown]`
  - `python -m aresforge inspect-queue-item --item-id <id> [--queue-path <path>] [--format json|markdown]`
- M33 local validation behavior:
  - optional M32 registry validation for `project_id` + `repo_id` bindings
  - missing dependency references are saved with warnings for future linkage
  - queue remains local-only and does not call GitHub APIs, `gh`, network services, or LLM services
- M26 handoff generation now includes local project queue summary when queue exists.
- `assigned_agent` is stored for future orchestration and does not execute agents in M33.
- `assigned_agent` can now reference an M34 `agent_id` from local agent profiles.
- M35 orchestration planning consumes queue `assigned_agent`, `dependencies`, and `blocked_by` fields for plan-only assignment and sequencing.

## M32 Multi-Project / Multi-Repo Local Registry

- Added a local managed-project registry under `.aresforge/projects/projects.json`.
- Registry tracks multiple projects and multiple repos with explicit status, role, metadata, and timestamps.
- New local-only command surface:
  - `python -m aresforge init-managed-project-registry [--path <path>] [--force]`
  - `python -m aresforge register-managed-project --project-id <id> --name <name> --root-path <path> [--registry-path <path>] [--description <text>] [--status <status>] [--default-branch <branch>] [--tag <tag>]... [--notes <text>]`
  - `python -m aresforge register-managed-repo --project-id <id> --repo-id <id> --name <name> --path <path> [--registry-path <path>] [--remote-url <url>] [--default-branch <branch>] [--role <role>] [--status <status>] [--tag <tag>]... [--notes <text>]`
  - `python -m aresforge inspect-managed-project-registry [--registry-path <path>] [--format json|markdown]`
  - `python -m aresforge inspect-managed-project --project-id <id> [--registry-path <path>] [--format json|markdown]`
  - `python -m aresforge inspect-managed-repo --project-id <id> --repo-id <id> [--registry-path <path>] [--format json|markdown]`
- M26 handoff generation now includes managed-project registry summary when the registry exists.
- M33 queue item registration now uses this registry for local `project_id` / `repo_id` validation when available.
- M32 boundary confirmation:
  - local-only
  - no `gh`
  - no GitHub API calls
  - no network access
## M31 Foundation Reconciliation and Next-Phase Planning

- AresForge now has a local-first foundation for self-managed operation.
- GitHub is optional/syncable and not mandatory for local planning.
- M26 added local handoff package generation.
- M27 added the local project state ledger.
- M28 added plan-only documentation reconciliation.
- M29 added plan-only offline-to-GitHub sync planning.
- M30 added local self-managed milestone lifecycle support.
- No new functionality in this foundation batch calls GitHub APIs.
- No new functionality in this foundation batch calls LLM APIs.
- The system is ready to move into multi-project and multi-agent project-management capabilities.

## Next-Phase Roadmap (Planned)

- M38: project/repo/queue management screens and workflows.
- M39: agent/orchestration/escalation/handoff screens.
- M40: reporting/dashboard polish and operator workflows.

## Known Limitations (Current Foundation Batch)

- No production-ready LLM dispatch exists; only the M62 explicit local LLM prototype may call a local provider under operator gates.
- No cloud LLM API integration yet.
- No GitHub sync execution yet.
- Hub now includes local project/repo/queue, agent/handoff/orchestration/escalation, reporting, dashboard, prompt-pack, AI review, audit, artifact, and run-history surfaces; execution gates/auth/deployment hardening remain future work.
- No cross-machine coordination yet.
- No background daemon/scheduler yet.

## M30 Self-Managed Milestone Lifecycle

- New local-only command surface:
  - `python -m aresforge generate-local-milestone-template --milestone-id <id> --output <path> [--title <title>] [--force]`
  - `python -m aresforge inspect-local-milestone --definition <path> [--format json|markdown]`
  - `python -m aresforge check-local-milestone-readiness --definition <path> [--project-state <path>] [--format json|markdown]`
  - `python -m aresforge generate-local-milestone-closeout --definition <path> --output <path> [--format json|markdown] [--force]`
- Definition files are local and operator-managed (suggested location: `.aresforge/milestones/`).
- Lifecycle is local-first and plan/check/generate only:
  - no `gh`
  - no GitHub API calls
  - no network access
  - no LLM calls
- Readiness checks validate required fields/docs/artifacts/commands/closeout requirements and optionally reconcile with local project state.
- Closeout generation includes milestone summary, readiness result, validation checklist, documentation reconciliation reminder (M28), handoff reminder (M26), and optional GitHub sync planning reminder (M29).
- M26 handoff package now surfaces `active_local_milestone` when inferable from M27 project state (`current_milestone`).
- Later milestones can be associated with managed `project_id` and `repo_id` from the M32 registry.

## M29 Offline-to-GitHub Sync Planner

- New local-only plan command:
  - `python -m aresforge plan-github-sync [--state-file <path>] [--project-state <path>] [--output <path>] [--format json|markdown] [--force]`
- Planner inspects only local sources:
  - optional offline closeout state file
  - optional/default project state ledger at `.aresforge/state/project_state.json`
  - optional source-of-truth docs context paths for plan traceability
- Planner output includes:
  - generated timestamp and input files used
  - parent/child sync candidates
  - evidence comment, closeout, label, milestone, PR evidence mapping, and validation candidates
  - rate-limit warnings, manual review checklist, and explicit no-GitHub-operations confirmation
- Strict M29 boundary:
  - plan-only
  - local-only
  - no `gh`
  - no GitHub API calls
  - no network access
  - no mutation
- M26 handoff package generation now includes latest local GitHub sync plan reference when detected under `artifacts/github-sync/`.
- M28 documentation reconciliation planning now recommends source-of-truth doc review when a local GitHub sync plan is present.

## M28 Documentation Agent Foundation

- New local-only plan command:
  - `python -m aresforge plan-doc-reconciliation [--output <path>] [--format json|markdown] [--include-git-state] [--force]`
- Planner inspects only local sources:
  - source-of-truth docs under `docs/context`, `docs/roadmap`, `docs/architecture`, `docs/operator`
  - local project state at `.aresforge/state/project_state.json` when present
  - local git state only when `--include-git-state` is supplied, using approved command subset
- Planner output fields include:
  - generated timestamp, docs inspected, missing docs, milestone and command references
  - stale/missing sections, recommended updates, alignment notes, risks, and next actions
- Strict M28 boundary:
  - plan-only (no doc edits)
  - local-only
  - no `gh`
  - no GitHub API calls
  - no LLM calls
  - no network dependency
- M26 handoff package generation now includes latest local doc reconciliation plan reference when detected under `artifacts/doc-reconciliation/`.
- M27 project-state documentation status can be used to track documentation reconciliation progress.

## M27 Local Project State Ledger

- New local-only ledger defaults:
  - `.aresforge/state/`
  - `.aresforge/state/project_state.json`
  - `.aresforge/state/operation_log.jsonl`
- New local-only command surface:
  - `python -m aresforge init-project-state [--path <path>] [--force]`
  - `python -m aresforge inspect-project-state [--path <path>]`
  - `python -m aresforge update-project-state [--path <path>] [--current-milestone <value>] [--current-phase <value>] [--current-mode <value>] [--validation-status <value>] [--documentation-status <value>] [--warning <text>]...`
  - `python -m aresforge append-operation-log [--state-path <path>] --event-type <type> --summary <summary> [--details <json>]`
  - `python -m aresforge inspect-operation-log [--state-path <path>] [--limit <n>]`
- M26 handoff package generation now includes local project-state summary when present.
- If project state is missing, handoff generation adds a warning and still succeeds.
- Scope clarification:
  - M27 local project state tracks the current repo/session context.
  - M32 managed-project registry tracks many projects and repos in local-first control-plane context.
  - M33 local project queue tracks local work progression across project/repo inventory.

## M26 Local Handoff Package Generator

- New local-only command: `python -m aresforge generate-handoff-package --output <path> [--format markdown|json] [--include-doc-excerpts] [--force]`.
- Reads only local repo + source-of-truth docs and does not call GitHub APIs or `gh`.
- Uses only safe local git commands for state capture:
  - `git branch --show-current`
  - `git rev-parse HEAD`
  - `git status --short`
  - `git log -n 10 --oneline`
- Supports stdout rendering when `--output` is omitted:
  - Markdown by default.
  - Stable JSON when `--format json`.
- Supports continuity sections for future sessions:
  - project status summary
  - completed recent capabilities
  - known blockers/warnings
  - working preferences
  - recommended next options
  - Codex continuation prompt

## Continuity Value

- Reduces manual handoff writing for human and agent transitions.
- Establishes a local-first continuity baseline required before future multi-project queue/orchestration/dashboard/cloud escalation milestones.

## Current Repository State

- M25 parent issue: `#421` (OPEN; pending final closeout).
- M25 child issue status:
  - `#422` CLOSED via PR `#431`
  - `#423` CLOSED via PR `#432`
  - `#424` CLOSED via PR `#433`
  - `#425` CLOSED via PR `#434`
  - `#426` CLOSED via PR `#435`
  - `#427` CLOSED via PR `#436`
  - `#428` CLOSED via PR `#437`
  - `#429` CLOSED via PR `#438`
  - `#430` OPEN (final source-of-truth reconciliation; sequenced last)
- Offline state-file parent closeout readiness workflow is implemented and pushed on `main` through commit `40de9fe`.

## Offline State-File Closeout Readiness (Local-Only)

- Preferred path during GitHub GraphQL/API rate-limit windows.
- When `--state-file <path>` is provided, these commands run local/offline and avoid `gh` and GitHub API calls.
- Supported commands:
  - `python -m aresforge inspect-milestone-state --parent-issue <n> --state-file <path>`
  - `python -m aresforge check-milestone-evidence-readiness --parent-issue <n> --state-file <path>`
  - `python -m aresforge inspect-parent-closeout-readiness --parent-issue <n> --state-file <path>`
  - `python -m aresforge generate-parent-closeout-evidence-bundle --parent-issue <n> --state-file <path>`
  - `python -m aresforge check-closeout-readiness-by-construction --parent-issue <n> --state-file <path>`
- Example fixture: `tests/fixtures/offline_state/parent_closeout_ready.json`.
- Validation checkpoint for docs/sample addition passed: `python -m pytest` (`502` tests).

## M25 Command Surface

- `python -m aresforge inspect-automatic-canonical-evidence-emission-contract`
- `python -m aresforge inspect-child-evidence-marker-preflight --parent-issue <parent>`
- `python -m aresforge inspect-pr-mapping-preflight --parent-issue <parent>`
- `python -m aresforge generate-closeout-preflight-repair-guidance --parent-issue <parent>`
- `python -m aresforge generate-child-closeout-evidence-bundle --parent-issue <parent> --child-issue <child>`
- `python -m aresforge generate-pr-evidence-bundle --issue <child> --pr <pr>`
- `python -m aresforge generate-parent-closeout-evidence-bundle --parent-issue <parent>`
- `python -m aresforge generate-evidence-comment-template --issue <issue>`
- `python -m aresforge check-closeout-readiness-by-construction --parent-issue <parent>`

## M25 Safety Posture

- no autonomous broad mutation
- no bulk closeout
- no parent closeout before children are closed/accounted for and readiness passes
- dry-run/read-only defaults preserved
- execute-mode mutation requires explicit operator approval markers
- mutation scope remains single-target and auditable
- canonical marker generation and snapshot/diff inspection remain read-only by default
- final reconciliation issue remains sequenced last (`#430`)
- no post-hoc marker repair should be needed when generated evidence artifacts are complete

## Known Limitations

- Project-specific milestone naming mapping warning remains non-blocking (`milestone_naming_status.naming_ok: false`).
- Parent and some child issues currently have no GitHub milestone assignment (warning only, non-blocking for M25 closeout).

## Validation Baseline For M25

- `git diff --check`
- `python -m pytest`
- `python -m aresforge inspect-repo-governance`
- `python -m aresforge inspect-milestone-state --parent-issue 421`
- `python -m aresforge check-milestone-evidence-readiness --parent-issue 421`
- `python -m aresforge inspect-parent-closeout-readiness --parent-issue 421`
- `python -m aresforge inspect-milestone-closeout-preflight --parent-issue 421`
- `python -m aresforge inspect-automatic-canonical-evidence-emission-contract`
- `python -m aresforge check-closeout-readiness-by-construction --parent-issue 421`
- `python -m aresforge generate-parent-closeout-evidence-bundle --parent-issue 421`

## M25 Child/PR Mapping

- `#422` -> `#431`
- `#423` -> `#432`
- `#424` -> `#433`
- `#425` -> `#434`
- `#426` -> `#435`
- `#427` -> `#436`
- `#428` -> `#437`
- `#429` -> `#438`
- `#430` -> pending (this reconciliation PR)

## Main HEAD Tracking (M25 Remaining Sequence)

- Before #428/#429/#430 sequence: `dd856632e2f1831b20b73613f29e9e953771180f`
- After #428 and #429 merges: `cafda2ceda0a329de7d06a42c0edc6725ece3b10`
- Final main HEAD after #430 merge: pending (set after merge)
