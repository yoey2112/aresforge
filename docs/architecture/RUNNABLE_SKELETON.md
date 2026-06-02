# Runnable Skeleton

## M174 GitHub Issue State Reconciliation

- `python -m aresforge reconcile-github-issue-state --project-id aresforge --dry-run --format json`
- emits `github_issue_state_reconciliation_v1`
- reads local queue metadata, issue sync planning, the GitHub link registry, autonomy profile policy, and machine gates
- optionally reads a mocked GitHub issue-state JSON file with `--github-state-path`
- recommends `create`, `update`, `comment`, `close`, `reopen`, or `skip` actions per queue item
- defaults to dry-run unless `--github-enabled` is supplied

Runnable boundary:

- recommendation-only by default and by design
- live GitHub reads require explicit enablement, `github_issue_sync_enabled`, and passing gates
- no recommendation is executed by this command
- no queue status mutation, PR merge, auto-merge, force push, protected branch update, release creation, workflow mutation, issue mutation, Codex execution, local LLM/model execution, source patch application, validation command execution, retry, resume, or automatic next-item execution

## M173 GitHub Status Comment Durable Sync

- `python -m aresforge sync-github-status-comment-durable --item-id m173-github-status-comment-durable-sync --dry-run --format json`
- emits `github_status_comment_durable_sync_v1`
- reads local queue metadata, issue sync planning, orchestration run monitor evidence, autonomy profile policy, machine gates, and the GitHub link registry
- composes one managed status comment body with queue, run, validation, artifact, gate, and next-action sections
- defaults to dry-run unless `--github-enabled` is supplied
- live sync stores `comment_id` and `comment_url` in the local GitHub link registry after successful create/update
- future live syncs update by durable registry `comment_id` when available

Runnable boundary:

- dry-run or blocked by default
- one issue status comment maximum per invocation
- no queue status mutation, PR merge, auto-merge, force push, protected branch update, release creation, workflow mutation, issue closure, Codex execution, local LLM/model execution, source patch application, validation command execution, retry, resume, or automatic next-item execution

## M172 Queue-to-GitHub Issue Backfill

- `python -m aresforge backfill-queue-items-to-github-issues --project-id aresforge --dry-run --format json`
- emits `queue_to_github_issue_backfill_v1`
- scans queue items for the selected project
- skips local queue metadata links and local GitHub link registry issue links
- generates per-item issue payloads from the M162 issue sync plan
- defaults to dry-run unless `--github-enabled` is supplied
- live creation routes each candidate through the M171 real-run gate and records local registry links after successful issue creation

Runnable boundary:

- dry-run or blocked by default
- live backfill defaults to one issue create maximum per invocation unless `--max-creations` is supplied
- no queue status mutation, PR merge, auto-merge, force push, protected branch update, release creation, workflow mutation, issue closure, Codex execution, local LLM/model execution, source patch application, validation command execution, retry, resume, or automatic next-item execution

## M171 GitHub Issue Creation Real-Run Gate

- `python -m aresforge create-github-issue-real-run-gate --item-id m171-github-issue-creation-real-run-gate --dry-run --format json`
- emits `github_issue_creation_real_run_gate_v1`
- checks one local queue item, M162 issue draft planning, M170 link registry state, M158 autonomy profile policy, and M131 machine gates
- defaults to dry-run unless `--github-enabled` is supplied
- live creation additionally requires non-dry-run behavior, `github_issue_sync_enabled`, safe queue status, no queue/registry duplicate issue link, and passing `github_sync`
- successful real issue creation records a local registry link for idempotency and future duplicate prevention

Runnable boundary:

- dry-run or blocked by default
- one issue create maximum per invocation
- no queue status mutation, PR merge, auto-merge, force push, protected branch update, release creation, workflow mutation, issue closure, Codex execution, local LLM/model execution, source patch application, validation command execution, retry, resume, or automatic next-item execution

## M170 GitHub Link Registry for Queue Items

- `python -m aresforge inspect-github-link-registry --project-id aresforge --format json`
- `python -m aresforge record-github-link --queue-item-id <item_id> --repository <owner/repo> --issue-number <n> --issue-url <url> --pr-number <n> --pr-url <url> --format json`
- emits `github_link_registry_for_queue_items_v1`
- reads and writes durable local metadata at `.aresforge/github_link_registry/links.json`
- supports inspect, local add/update, queue-item lookup, issue lookup, PR lookup, and repository filtering
- stores queue item id, repository, issue/PR numbers and URLs, sync status, sync time/result, linked-by/source metadata, warnings, and idempotency key

Runnable boundary:

- inspection is local-only and read-only
- record add/update mutates only the local registry file
- idempotent repeated writes with the same material link data are no-ops
- no live GitHub mutation, `gh`, GitHub API call, PR creation/update/merge, issue closure, queue mutation, Codex execution, local LLM/model execution, source patch application, validation command execution, protected branch update, force push, auto-merge, release, workflow mutation, retry, resume, or automatic next-item execution

## M169 Production Autonomy Readiness Report

- `python -m aresforge generate-production-autonomy-readiness-report --project-id aresforge --sprint-start M155 --sprint-end M169 --format json`
- emits `production_autonomy_readiness_report_v1`
- reconciles M155, M156, M157, M158, M159, M160, M161, M162, M163, M164, M165, M166, M167, M168, and M169 queue/docs/run-store/artifact/autonomy/GitHub-loop evidence
- composes durable run-store status, artifact retention status, autonomy profile status, Codex pilot readiness, GitHub issue sync planning status, Hub control center readiness, self-managed dry-run evidence, machine-gate behavior, blockers, warnings, and next sprint recommendations
- optional `--output` writes one local JSON artifact

Runnable boundary:

- report-only by default
- no queue mutation, live Codex execution, local LLM/model execution, GitHub execution, source patch application, validation command execution, PR merge, protected branch update, force push, auto-merge, release, workflow mutation, retry, resume, or automatic next-item execution
- production autonomy remains dry-run/audit/review-ready until separate explicit live gates are implemented

## M168 Self-Managed AresForge Project Loop Dry Run

- `python -m aresforge run-self-managed-project-loop --project-id aresforge --dry-run --format json`
- emits `self_managed_aresforge_project_loop_dry_run_v1`
- writes local artifacts under `.aresforge/self_managed_project_loop/<run_id>/`
- composes queue item selection, route decision, orchestration plan, machine gate rollup, deterministic multi-agent dry-run output, Codex loop evidence bundle, GitHub issue sync plan, PR draft summary, durable run-store entry, and closeout recommendation
- requires `--dry-run`
- no live GitHub, `gh`, PR creation/update/merge, issue closure, queue mutation, Codex execution, local LLM/model execution, source patch application, validation command execution, protected branch update, force push, auto-merge, release, workflow mutation, retry, resume, or automatic next-item execution

## M167 Hub Autonomy Control Center v1

M167 adds a read-only Hub control-center command:

- `python -m aresforge inspect-hub-autonomy-control-center-data --project-id aresforge --format json`

The command returns `hub_autonomy_control_center_v1` JSON and composes local autonomy profile state, durable orchestration run-store state, orchestration run monitor summaries, discovered evidence bundles, GitHub issue sync dry-run plans/status, issue closure recommendation evidence, existing PR draft summary artifacts, machine gates, and next safe actions.

Hub integration:

- `GET /api/autonomy/control-center`
- Autonomy panel in the local Hub UI

Execution boundary:

- no GitHub mutation, PR creation/update/merge, issue closure, queue mutation, Codex execution, model execution, source patch application, validation command execution, retry, resume, release creation, workflow mutation, protected-branch update, force push, auto-merge, or automatic next-item execution
- future-action gates are displayed as status evidence; they do not authorize execution

## M166 Pull Request Draft Summary Generator

M166 adds a local draft PR summary command:

- `python -m aresforge generate-pr-draft-summary --item-id m166-pull-request-draft-summary-generator --format json`

The command returns `pull_request_draft_summary_generator_v1` JSON and writes JSON plus Markdown artifacts under `.aresforge/pr_draft_summaries/`. It reads one local queue item, optional Codex evidence bundle metadata, changed files, validation evidence, artifact paths, linked issue metadata, autonomy profile inspection, and machine gates before producing operator-review PR body content.

Runnable boundary:

- safe for local smoke checks and local artifact generation
- optional `--output` writes the JSON artifact at a chosen local path and a sibling Markdown artifact
- no pull request is created, updated, merged, pushed, or auto-merged
- future PR creation requires a separate explicitly enabled machine-gated command
- no queue mutation, Codex, local LLM/model, source patch application, validation command execution, release, workflow mutation, retry, resume, protected-branch update, force push, or next-item execution is performed

## M165 GitHub Issue Closure Recommendation Gate

M165 adds an advisory-only closure recommendation command:

- `python -m aresforge recommend-github-issue-closure --item-id m165-github-issue-closure-recommendation-gate --format json`

The command returns `github_issue_closure_recommendation_gate_v1` JSON. It reads one local queue item, reuses M162 linked-issue metadata, inspects validation and artifact evidence, checks linked issue state from local metadata or `--linked-issue-state`, inspects the selected autonomy profile, and evaluates the read-only machine gate before recommending `close` or `keep_open`.

Runnable boundary:

- recommendation-only and safe for local smoke checks
- optional `--output` writes one local JSON artifact
- no live GitHub lookup or issue closure is performed
- future closure requires a separate explicitly enabled machine-gated command
- no queue mutation, Codex, local LLM/model, source patch application, validation command execution, PR merge, protected branch update, force push, auto-merge, release, workflow mutation, retry, resume, or next-item execution is performed

## M164 GitHub Issue Status Comment Sync

M164 adds a dry-run-default status comment sync command:

- `python -m aresforge sync-github-issue-status-comment --item-id m164-github-issue-status-comment-sync --dry-run --format json`

The command returns `github_issue_status_comment_sync_v1` JSON. It reads one local queue item, reuses M162 linked-issue metadata, reads M153 orchestration monitor evidence, inspects the selected autonomy profile, builds a marked status comment body, and checks machine gates before any live comment create/update can occur.

Runnable boundary:

- dry-run by default and safe for local smoke checks
- live status comment sync requires `--github-enabled`, no `--dry-run`, `--autonomy-profile github_issue_sync_enabled`, linked issue metadata or `--issue-number`, safe queue item status, and a passing `github_sync` machine gate
- optional `--output` writes one local JSON artifact
- no queue mutation, Codex, local LLM/model, source patch application, validation command execution, PR merge, protected branch update, force push, auto-merge, release, workflow mutation, retry, resume, or next-item execution is performed

## M163 GitHub Issue Creation for Safe Queue Items

M163 adds a dry-run-default issue creation command:

- `python -m aresforge create-github-issue-for-safe-queue-item --item-id m163-github-issue-creation-for-safe-queue-items --dry-run --format json`

The command returns `github_issue_creation_for_safe_queue_items_v1` JSON. It reads one local queue item, reuses M162 issue draft mapping and linked-issue detection, inspects the selected autonomy profile, and checks machine gates before any live issue creation can occur.

Runnable boundary:

- dry-run by default and safe for local smoke checks
- live creation requires `--github-enabled`, no `--dry-run`, `--autonomy-profile github_issue_sync_enabled`, no linked issue metadata, safe queue item status, and a passing `github_sync` machine gate
- optional `--output` writes one local JSON artifact
- no queue mutation, issue-link backfill, Codex, local LLM/model, source patch application, validation command execution, PR merge, protected branch update, force push, auto-merge, release, workflow mutation, retry, resume, or next-item execution is performed

## M162 GitHub Issue Sync Plan from Queue Items

M162 adds a local GitHub issue sync planning command:

- `python -m aresforge plan-github-issue-sync --project-id aresforge --format json`

The command returns `github_issue_sync_plan_from_queue_items_v1` JSON. It reads local queue items, maps queue fields to future GitHub issue title/body/labels/milestone/comments, detects already-linked issues from local metadata, and recommends create/update/comment/skip operations.

Runnable boundary:

- local planning only
- optional `--output` writes one local JSON artifact
- linked issue detection is local metadata inspection only
- no `gh`, GitHub API call, issue/comment/label/milestone mutation, Codex, local LLM/model, source patch application, queue mutation, retry, resume, PR merge, force push, protected-branch update, workflow mutation, release, or next-item execution is performed

## M161 Codex Loop Validation Evidence Bundle

M161 adds a dry-run evidence bundle command:

- `python -m aresforge bundle-codex-loop-validation-evidence --item-id m161-codex-loop-validation-evidence-bundle --dry-run --format json`

The command returns `codex_loop_validation_evidence_bundle_v1` JSON and writes a durable local bundle under `.aresforge/codex_loop_validation_evidence/`. The bundle composes the existing Codex loop dry-run record, stdout/stderr artifact copies, changed-file evidence, validation command/result evidence, machine gates, source patch risk classification, retry classification, completion recommendation, and next safe action.

Runnable boundary:

- `--dry-run` is required
- optional `--output` writes the bundle record at a chosen local path
- optional `--patch-path` classifies a local source patch but does not apply it
- no agent, live Codex, local LLM/model, GitHub, source patch application, queue completion, retry, resume, PR merge, force push, protected-branch update, workflow mutation, release, or next-item execution is performed

## M160 Low-Risk Codex Execution Pilot Item

M160 adds a low-risk Codex pilot coordinator:

- `python -m aresforge prepare-low-risk-codex-pilot --item-id m160-low-risk-codex-execution-pilot-item --dry-run --format json`

The command returns `low_risk_codex_execution_pilot_item_v1` JSON. It verifies the pilot queue item is low risk, captures M159 preflight decisions, runs the existing loop in dry-run mode by default, and can optionally invoke the existing M152 low-risk real Codex path only with explicit flags and safe changed-path scope.

Runnable boundary:

- dry-run is default
- real execution requires `--execution-enabled`, `--allow-low-risk-code`, declared low-risk `--changed-path` values, passing M159 preflight, and machine gates
- optional `--output` writes one local pilot artifact
- no GitHub push, PR creation, PR merge, protected branch update, auto-merge, release creation, source patch application, queue completion, retry, resume, or next-item execution is performed

## M159 Real Codex Execution Preflight Hardening

M159 adds a dry-run real Codex preflight command:

- `python -m aresforge preflight-real-codex-execution --item-id m159-real-codex-execution-preflight-hardening --dry-run --format json`

The command returns `real_codex_execution_preflight_hardening_v1` JSON. It composes the selected autonomy profile, worktree guard, local machine gates, durable run-store readiness, artifact capture roots, validation profile, retry policy, source patch risk policy, and dirty-tree detection into one future-execution readiness record.

Runnable boundary:

- `--dry-run` is required
- command success means the preflight record was generated; `blocked` controls future real Codex readiness
- optional `--output` writes one local preflight artifact
- real Codex execution remains a separate explicit low-risk command with required flags and machine gates
- no agent, Codex, local LLM/model, GitHub, validation command, source patch, queue mutation, retry, resume, PR merge, force push, protected-branch update, workflow mutation, release, or next-item execution is performed

## M158 Operator Autonomy Configuration Profile

M158 adds a local autonomy profile inspection command:

- `python -m aresforge inspect-autonomy-profile --project-id aresforge --format json`

The command returns `operator_autonomy_configuration_profile_v1` JSON. It lists explicit operator profiles, selects `locked_down` by default, and reports every controlled capability as `enabled`, `dry_run_only`, or `blocked`. Profiles include `locked_down`, `advisory_only`, `low_risk_local`, `codex_dry_run`, `codex_low_risk_enabled`, `github_sync_dry_run`, `github_issue_sync_enabled`, and `experimental_full_local`.

Runnable boundary:

- local profile inspection only
- optional `--output` writes one local profile artifact
- profile metadata does not execute the capabilities it describes
- enabled capabilities still require separate explicit commands, operator intent, required flags, and passing machine gates
- no agent, Codex, local LLM/model, GitHub, validation command, source patch, queue mutation, retry, resume, PR merge, force push, protected-branch update, workflow mutation, release, or next-item execution is performed

## M157 Run Replay and Audit Trail

M157 adds a local replay/audit command:

- `python -m aresforge replay-orchestration-run --run-id sample-run --dry-run --format json`

The command returns `orchestration_run_replay_audit_trail_v1` JSON. It reconstructs a run from the durable run store, run history, monitor evidence, retention index metadata, source artifacts, step records, evidence bundles, and referenced artifacts. It reports source records, artifact hashes, reconstructed machine gates, a decision timeline, audit events, source execution flags, and the next safe action.

Runnable boundary:

- `--dry-run` is required
- metadata reconstruction only; source run work is never re-executed
- optional `--output` writes one local replay audit artifact
- no agent, Codex, local LLM/model, GitHub, validation command, source patch, queue mutation, artifact cleanup, retry, resume, PR merge, force push, protected-branch update, workflow mutation, release, or next-item execution is performed

## M156 Orchestration Artifact Retention Policy

M156 adds a local orchestration artifact retention command:

- `python -m aresforge inspect-orchestration-artifact-retention --project-id aresforge --format json`

The command returns `orchestration_artifact_retention_policy_v1` JSON. It indexes expected local artifact folders, summarizes artifact counts by category, detects durable-store orphan candidates for index-required artifact folders, reports stale artifact warnings, and emits retention recommendations plus a dry-run cleanup plan.

Runnable boundary:

- local artifact inspection only by default
- optional `--output` writes one local JSON report artifact
- cleanup planning is dry-run only and never deletes, moves, archives, truncates, or rewrites artifacts
- no agent, Codex, local LLM/model, GitHub, validation command, source patch, queue progression, retry, resume, PR merge, force push, protected-branch update, workflow mutation, release, or next-item execution is performed

## M155 Durable Orchestration Run Store

M155 adds a durable orchestration run store command:

- `python -m aresforge inspect-orchestration-run-store --project-id aresforge --format json`

The command returns `durable_orchestration_run_store_v1` JSON. It validates and inspects `.aresforge/orchestrator/run_history.json`, bootstraps that file when missing, reports store capabilities, and exposes corruption-safe blocked errors for invalid JSON or schema state. M141 history/recovery now writes and reads through the same durable store while continuing to discover legacy `artifacts/multi-agent-orchestration` records.

Runnable boundary:

- local store inspection/bootstrap only
- append/read/update-by-run-id are local file operations for orchestration run metadata
- no agent, Codex, local LLM/model, GitHub, validation command, source patch, queue progression, retry, resume, PR merge, force push, protected-branch update, workflow mutation, release, or next-item execution is performed
- recovery and resume remain advisory until separate explicit machine-gated commands exist

## M154 Sprint Closeout and Autonomy Readiness Report

M154 adds a local readiness report command:

- `python -m aresforge generate-autonomy-readiness-report --project-id aresforge --sprint-start M140 --sprint-end M154 --format json`

The command returns `autonomy_readiness_report_v1` JSON. It reads the local queue, source-of-truth docs, local artifact roots, agent registry, LLM decision-policy recommendation, read-only machine safety gate, and orchestration run monitor output to summarize the M140-M154 sprint and recommend the next hardening sprint.

Runnable boundary:

- report-only by default
- optional `--output` writes one local report artifact
- no agent, Codex, local LLM/model, GitHub, validation command, source patch, queue, retry, resume, PR merge, force push, protected-branch update, workflow mutation, release, or next-item execution is performed
- real Codex execution remains default-deny and source patch application remains classification/planning/dry-run only until a separate explicit gated command exists

## M153 Hub Orchestration Run Monitor

M153 adds a read-only orchestration run monitor command:

- `python -m aresforge inspect-orchestration-run-monitor --project-id aresforge --format json`

The command returns `hub_orchestration_run_monitor_v1` JSON. It reads local M141 orchestration history, loads the latest or selected source run artifact when available, composes M147 resume-plan evidence, and reports run status, gates, step results, recovery, artifact references, and next safe action. Hub exposes the same local view at `GET /api/orchestration/run-monitor`.

Runnable boundary:

- inspection-only by default
- optional `--output` writes a local monitor artifact under an operator-chosen path such as `.aresforge/orchestrator/run_monitor/`
- no agent, Codex, local LLM/model, GitHub, validation command, patch, queue, retry, resume, PR merge, force push, protected-branch update, workflow mutation, release, or next-item execution is performed
- resume availability is advisory evidence for a separate explicit future machine-gated command

## M152 End-to-End Codex Loop Real Run for Low-Risk Code

M152 extends the Codex loop command with a real low-risk profile:

- `python -m aresforge run-end-to-end-codex-loop --item-id m152-end-to-end-codex-loop-real-run-for-low-risk-code --dry-run --format json`

The command returns `end_to_end_codex_loop_real_low_risk_v1` JSON for the M152 item. Dry-run mode writes local evidence but performs no Codex invocation. Non-dry-run mode requires `--execution-enabled`, `--allow-low-risk-code`, declared `--changed-path` scope, M135 dispatch gates, and M136 validation.

Runnable boundary:

- real execution is default-deny
- low-risk code scope allows declared source/test paths and blocks workflows, protected config, queue state, orchestration/Codex runtime, Hub, scripts, migrations, and unscoped paths
- non-dry-run execution captures local Codex stdout/stderr and validation evidence before any completion recommendation
- no GitHub push, PR merge, protected-branch update, workflow mutation, release creation, source patch application by AresForge, queue completion, retry loop, or next-item execution is performed

## M151 End-to-End Codex Loop Dry Run

M151 adds a dry-run end-to-end Codex loop command:

- `python -m aresforge run-end-to-end-codex-loop --item-id m151-end-to-end-codex-loop-dry-run --dry-run --format json`

The command returns `end_to_end_codex_loop_dry_run_v1` JSON. It reads the local queue item, writes a bounded queue snapshot and dry-run Codex artifacts, runs M135 dispatch in dry-run mode, then runs M136 ingestion in dry-run mode to select validation commands, parse local evidence, and generate a completion recommendation.

Runnable boundary:

- M151 is dry-run only and blocks non-dry-run requests
- the required dry-run Codex dispatch gate must pass before ingestion proceeds
- validation commands are recorded but not executed
- queue completion remains a separate explicit gated path
- no real Codex execution, model execution, GitHub operation, patch application, queue mutation, retry, PR merge, force push, protected branch update, workflow mutation, release creation, or next-item execution is performed

## M150 Machine-Gated Source Patch Apply Dry Run

M150 adds a source patch apply dry-run command:

- `python -m aresforge dry-run-source-patch-apply --item-id m150-machine-gated-source-patch-apply-dry-run --patch-path artifacts/manual/sample-source.patch --format json`

The command returns `source_patch_apply_dry_run_v1` JSON. It reuses M149 planning and the M148 classifier, evaluates the `source_patch_apply_dry_run` machine gate, then runs `git apply --check` only when gates and hard-blocker checks pass.

Runnable boundary:

- M150 proves applicability only
- no source patch application, validation command execution, Codex, model, GitHub, agent, queue mutation, retry, or next-item execution is performed
- workflow, protected config, queue-state, binary, executable-mode, outside-repo, machine-gate, and failed apply-check blockers prevent dry-run success
- actual source patch application remains a separate future explicit command with machine gates and validation evidence

## M149 Controlled Source Patch Apply Plan

M149 adds a read-only source patch apply planner:

- `python -m aresforge plan-source-patch-apply --item-id m149-controlled-source-patch-apply-plan --patch-path artifacts/manual/sample-source.patch --format json`

The command returns `source_patch_apply_plan_v1` JSON. It reuses M148 classification, reports hard apply blockers, generates ordered future apply steps, and records validation and rollback requirements without mutating repository files.

Runnable boundary:

- M149 is planning and safety evidence only
- no source patch application, validation command execution, Codex, model, GitHub, agent, queue mutation, retry, or next-item execution is performed
- source patch application remains a separate future explicit command with machine gates and validation evidence
- workflow, protected config, queue-state, binary, executable-mode, and outside-repo patch operations block future controlled apply eligibility

## M148 Safe Source Patch Detection and Risk Classifier

M148 adds a read-only source patch classifier:

- `python -m aresforge classify-source-patch-risk --patch-path artifacts/manual/sample-source.patch --format json`

The command returns `source_patch_risk_classification_v1` JSON. It reads one local unified patch, parses touched files, classifies path classes and mutation types, assigns a risk level, lists blocked operations, chooses recommended validation requirements, and checks the read-only machine gate.

Runnable boundary:

- M148 is classification and safety planning only
- no patch application, validation command execution, Codex, model, GitHub, agent, queue mutation, retry, or next-item execution is performed
- source patch application remains default-blocked and requires a separate explicit future boundary
- workflow, protected config, queue-state, binary, executable-mode, and outside-repo patch operations are detected as automatic-apply blockers

## M147 Orchestrator Resume-from-Failure

M147 adds a read-only orchestration resume-plan command:

- `python -m aresforge inspect-orchestration-resume-plan --run-id sample-run --format json`

The command returns `orchestrator_resume_from_failure_plan_v1` JSON. It reads local orchestration history, discovers source run artifacts, validates checkpoint evidence, checks the read-only machine gate, and reports whether a future explicit gated resume can safely start from the last valid checkpoint.

Runnable boundary:

- M147 is inspection and recovery planning only
- no resume, retry, agent, Codex, model, GitHub, validation command, patch, queue mutation, or next-item execution is performed
- failed, blocked, mutating, Codex, GitHub, patch, queue-mutating, external-execution, or failed-gate runs require explicit recovery or validation before continuation
- downstream resume remains a future explicit machine-gated orchestration command

## M146 Agent Step Result Normalization

M146 adds a read-only agent step result normalization command:

- `python -m aresforge normalize-agent-step-result --result-path artifacts/manual/sample-agent-step-result.json --format json`

The command returns `agent_step_result_normalization_v1` JSON. It reads one local step result artifact, unwraps command payloads where present, normalizes status/blocker/warning/artifact/execution fields, checks the read-only machine gate, and reports orchestrator evaluation guidance.

Runnable boundary:

- M146 is normalization and recovery evidence only
- top-level execution flags describe the source step; `normalizer_execution_flags` remain false for this command
- no agent, Codex, model, GitHub, validation command, patch, queue mutation, retry, or next-item execution is performed
- downstream recovery remains explicit through existing machine-gated commands such as failure classification, run-history inspection, validation ingestion, or queue completion

## M145 Codex Failure Classification and Retry Policy

M145 adds a read-only failure classification command:

- `python -m aresforge classify-codex-failure --failure-artifact artifacts/manual/sample-codex-failure.json --format json`

The command returns `codex_failure_classification_retry_policy_v1` JSON. It reads one local failure artifact, detects failure classes, chooses a deterministic retry or stop policy, checks the read-only machine gate, and confirms all command execution/mutation flags remain false.

Runnable boundary:

- M145 is inspection and policy selection only
- automatic retry loops are prohibited
- retry-capable classes require separate explicit operator action and machine gates
- Codex, models, GitHub, validation commands, patch application, queue mutation, and next-item execution remain separate explicit gated paths

## M144 Codex Validation Profile Expansion

M144 adds a read-only validation profile inspection command:

- `python -m aresforge inspect-codex-validation-profiles --format json`

The command returns `codex_validation_profile_expansion_v1` JSON. It classifies changed paths, resolves task type and risk class, selects a recommended M136 validation profile, lists allowlisted local validation commands, checks the read-only machine gate, and confirms all execution/mutation flags remain false.

Runnable boundary:

- M144 is inspection and profile selection only
- validation commands are not run by the inspector
- Codex, models, GitHub, patch application, queue mutation, and next-item execution remain separate explicit gated paths
- downstream result validation still goes through `ingest-codex-result-and-validate --validation-profile <profile>`

## M143 Codex Execution Sandbox and Worktree Guard

M143 adds a read-only Codex sandbox/worktree guard inspection command:

- `python -m aresforge inspect-codex-worktree-guard --item-id m143-codex-execution-sandbox-and-worktree-guard --format json`
- optional `--project-id`, `--queue-path`, `--output`, and `--force`

Runnable behavior:

- emits `codex_execution_sandbox_worktree_guard_v1` JSON
- checks the read-only machine safety gate for the target queue item
- captures git branch, HEAD, dirty state, status-line counts, and bounded status-line samples
- reports preflight checks for queue existence, gate evidence, clean-tree expectations, repo-root cwd, shell-disabled execution, bounded output capture, patch disablement, GitHub disablement, and protected-branch update blocking
- documents sandbox policy, allowed local artifact roots, output capture boundaries, transaction-log summary, prohibited operations, and next safe action

Still absent by design:

- Codex invocation from this inspector
- local LLM/model execution
- GitHub API, `gh`, PR merge, force push, release creation, or workflow mutation
- patch application, validation command execution, queue mutation, automatic completion, next-item execution, daemon behavior, or background scheduling

## M142 Real Codex Execution Enablement Profile

M142 adds a read-only Codex execution enablement profile inspection command:

- `python -m aresforge inspect-codex-execution-enablements --format json`
- optional `--item-id`, `--project-id`, `--queue-path`, `--output`, and `--force`

Runnable behavior:

- emits `codex_execution_enablement_profile_v1` JSON
- reports default-deny real Codex execution posture
- lists explicit profiles for default-deny inspection, dry-run dispatch, gated single Codex dispatch, and gated orchestrated Codex steps
- checks the read-only machine safety gate for the target queue item
- references the Codex dispatch agent registry record and LLM decision policy summary
- documents required explicit flags, required artifacts, post-execution validation handoff, prohibited operations, and next safe action

Still absent by design:

- Codex invocation from this inspector
- local LLM/model execution
- GitHub API, `gh`, PR merge, force push, release creation, or workflow mutation
- patch application, validation command execution, queue mutation, automatic completion, next-item execution, daemon behavior, or background scheduling

## M141 Orchestration Run History and Recovery

M141 adds local orchestration run-history persistence and inspection:

- `python -m aresforge inspect-orchestration-run-history --project-id aresforge --format json`
- optional `--item-id`, `--run-id`, `--queue-path`, `--history-path`, `--artifacts-root`, `--output`, and `--force`

Runnable behavior:

- emits `orchestration_run_history_recovery_v1` JSON
- reads `.aresforge/orchestrator/run_history.json`
- discovers legacy `artifacts/multi-agent-orchestration/**.json` records
- records stable run fields, machine-gate summaries, execution flags, artifact paths, and next safe actions
- produces advisory recovery records for blocked, failed, interrupted, running, and max-step-limited orchestration runs

Still absent by design:

- no automatic retry, resume, rollback, queue mutation, patch application, GitHub operation, Codex execution, model execution, validation command execution, or next-item execution

## M140 Orchestrator Execution State Machine v1

M140 adds a read-only state-machine inspection command:

- `python -m aresforge inspect-orchestrator-state-machine --format json`
- optional `--item-id`, `--project-id`, `--queue-path`, `--output`, and `--force`

Runnable behavior:

- emits `orchestrator_execution_state_machine_v1` JSON
- defines durable run states: `created`, `queued`, `planning`, `gate_check`, `checkpoint`, `step_dispatch`, `step_running`, `validation`, `recovery`, `completed`, `blocked`, `failed`, and `cancelled`
- defines terminal statuses: `completed`, `blocked`, `failed`, and `cancelled`
- defines checkpoint records for queue snapshots, plan snapshots, pre-step gates, post-step validation, and terminal status
- defines validation boundaries for queue dependencies, plan integrity, machine gates, external execution, model execution, patch application, and terminal reporting
- checks the `read_only_agent` machine gate for the target queue item

Still absent by design:

- agent execution from the inspector
- Codex, local LLM, GitHub, validation command, or patch execution
- queue mutation, automatic retry, automatic rollback, automatic completion, next-item execution, daemon behavior, or background scheduling

## M139 Autonomous Sprint Closeout v1

M139 adds a local-only sprint closeout generator:

- `python -m aresforge generate-autonomous-sprint-closeout --project-id aresforge --format json`
- optional `--sprint-start`, `--sprint-end`, `--dry-run`, `--apply-docs-only`, `--output`, and `--force`

Runnable behavior:

- inspects `.aresforge/queue/work_items.json` for M125-M139 status
- inspects the M126 agent registry and M125 runtime boundary
- inspects M131 machine gate availability and the M139 read-only closeout gate
- inspects M138 orchestration availability
- inventories local sprint artifacts and the queue transaction log
- checks source-of-truth docs for M125, M126, M127, M128, M129, M130, M131, M132, M133, M134, M135, M136, M137, M138, and M139 mentions
- emits a stable `autonomous_sprint_closeout_v1` artifact

Still absent by design:

- Codex execution from closeout
- local LLM execution from closeout
- GitHub API/`gh` from closeout
- PR merge, force push, protected branch update, release creation, workflow mutation, or automatic issue closure
- source-code patch application
- automatic queue completion, automatic next-item execution, daemon behavior, or background scheduling

## M138 Multi-Agent Orchestrator v1

M138 adds a machine-gated multi-agent orchestration command:

- `python -m aresforge run-agent-orchestration --item-id <item_id> --format json`
- optional `--plan-path`, `--dry-run`, `--max-steps`, `--allow-low-risk-real`, `--allow-local-llm`, `--allow-codex`, `--allow-github-sync`, `--output`, and `--force`

Runnable behavior:

- loads an M128-style plan from `--plan-path` or builds one for the queue item
- dry-run is the default when no allow flags are supplied
- evaluates a machine safety gate before each attempted step
- records `multi_agent_orchestration_v1` timelines with total, attempted, completed, and blocked step counts
- stops on the first blocking gate or failed step
- writes a local orchestration result artifact
- supports max-step bounded runs for partial safe timelines

Supported initial patterns:

- read-only planning chain
- docs-only reconciliation chain
- Codex dispatch dry-run chain
- low-risk validation chain
- sprint summary dry-run chain

Still absent by design:

- high-risk real execution by default
- machine gate bypass
- continuation after a failed required gate
- PR merge, force push, automatic queue completion, automatic next-item execution, daemon behavior, or background scheduling

## M137 GitHub PR/Issue Sync Agent

M137 adds a dry-run-first GitHub sync command:

- `python -m aresforge run-github-sync-agent --item-id <item_id> --format json`
- optional `--dry-run`, `--sync-mode issue-comment|issue-update|pr-comment|pr-summary`, `--github-enabled`, `--repo`, `--issue-number`, `--pr-number`, `--artifact-path`, `--output`, and `--force`

Runnable behavior:

- emits stable `github_sync_agent_v1` JSON
- plans issue and PR comments without live GitHub calls in dry-run mode
- posts one issue comment or one PR comment only when `--github-enabled` is explicit and `github_sync` machine gates pass
- writes local issue metadata and PR metadata summary artifacts
- may fetch live issue/PR metadata for summary artifacts only when `--github-enabled` is explicit and gates pass
- uses a mockable GitHub client boundary so tests do not require live GitHub access

Still absent by design:

- PR merge
- auto-merge enablement
- branch deletion
- force push
- PR approval or request-changes review
- release creation
- protected branch update
- repository file write
- automatic issue closure
- queue completion or automatic next-item execution

## M136 Codex Result Ingestion and Validation Runner

M136 adds the local validation handoff after Codex execution:

- `python -m aresforge ingest-codex-result-and-validate --item-id <item_id> --execution-record <path> --format json`
- optional `--dry-run`, `--validation-profile`, `--output`, and `--force`

Runnable behavior:

- reads one local Codex execution record
- reads stdout, stderr, and result artifact paths from that record when present
- detects changed files from the execution record, captured output, and local git status
- writes a local normalized result source artifact
- writes a `dispatch_result_evidence` artifact
- writes a `queue_completion_recommendation` artifact
- writes a `machine_safety_gate_evaluation` artifact for queue completion handoff
- runs local validation commands only from `docs_only`, `code_unit_tests`, `hub_ui`, `queue_system`, or `full_local_safe` unless `--dry-run` is supplied

Still absent by design:

- Codex execution
- GitHub API, `gh`, remote service calls, or automatic push
- queue status mutation, automatic completion, or automatic M132 delegation
- patch application by the ingestion runner
- automatic next-item execution, daemon behavior, or background scheduling

## M135 Codex Dispatch Executor v1

M135 adds a machine-gated Codex dispatch execution command:

- `python -m aresforge run-codex-dispatch --item-id <item_id> --artifact-path <artifact_path> --format json`
- optional `--dry-run`, `--execution-enabled`, `--output`, `--force`, `--timeout-seconds`, and `--require-clean-worktree`

Runnable behavior:

- reads one local queue item and one prepared Codex dispatch artifact
- requires the queue item to be `ready`
- requires dependencies to be satisfied and `blocked_by` to be empty
- evaluates the M131 `codex_dispatch` machine gate
- validates required artifact safety flags before execution
- dry-run writes stdout/stderr/result artifacts without invoking Codex
- non-dry-run requires `--execution-enabled`
- captures command, timestamps, exit code, stdout artifact path, stderr artifact path, and result artifact path

Still absent by design:

- patch application by AresForge
- GitHub API, `gh`, issues, PRs, workflows, or GitHub mutation
- queue completion or automatic status transition
- automatic push
- automatic next-item execution, daemon behavior, or background scheduling
- validation of Codex-produced file changes before M136

## M133 Documentation Agent Autonomous Apply for Docs-Only Patches

M133 adds a local-only docs patch apply command:

- `python -m aresforge apply-docs-only-patch --item-id <item_id> --patch-path <patch_path> --format json`
- optional `--dry-run`, `--force`, `--queue-path`, and `--output`

Runnable behavior:

- reads one local queue item
- parses a UTF-8 unified patch and extracts target files
- evaluates the M131 `docs_only_patch_apply` machine gate
- blocks source, tests, package/config, script, workflow, `.aresforge`, binary, non-doc, and executable/file-mode changes
- runs a clean local `git apply --check`
- dry-run reports the planned outcome without applying the patch
- successful non-dry-run applies only docs Markdown targets, performs a post-apply docs-only diff check, and appends a transaction-log entry

Still absent by design:

- Codex execution or Codex CLI shell-out
- Ollama/local LLM or remote LLM prompt execution
- validation command execution
- source-code patch application
- test patch application
- GitHub API, `gh`, issues, PRs, workflows, network calls, or external services
- queue completion, external mutation, automatic next-item execution, or background automation

## M132 Auto-Completion for Safe Queue Items

M132 adds a local-only auto-completion command:

- `python -m aresforge auto-complete-safe-queue-item --item-id <item_id> --format json`
- optional `--evidence-path`, `--gate-profile queue_status_mutation`, `--dry-run`, `--force`, and `--output`

Runnable behavior:

- reads one local queue item
- loads parsed dispatch evidence from an explicit path or discovers the latest local evidence for the item
- generates a deterministic queue completion recommendation when needed
- evaluates the M131 `queue_status_mutation` machine gate
- blocks high-risk and manual-only tagged items
- dry-run reports the planned outcome without queue mutation
- successful non-dry-run changes only the queue item status to `done` and appends a queue transaction-log entry

Still absent by design:

- Codex execution or Codex CLI shell-out
- Ollama/local LLM or remote LLM prompt execution
- agent execution
- GitHub API, `gh`, issues, PRs, workflows, network calls, or external services
- validation command execution
- patch application
- external mutation, automatic next-item execution, or background automation

## M124 Sprint Summary and Documentation Sync Closeout

M124 adds no runnable product feature. It synchronizes the M110-M124 controlled automation sprint docs and queue evidence.

Runnable behavior after M110-M124:

- local advisory artifact generation for LLM review requests
- local patch proposal intake metadata, blocked from application
- local dispatch result evidence parsing
- local queue completion recommendations
- Hub read-only dispatch/review/routing workspace
- local Ollama environment/provider metadata probing without prompts
- local documentation patch proposals for human review
- local artifact registry, approval ledger, batch sequencing, and queue transaction log inspection

Still absent by design:

- unattended Codex dispatch or Codex CLI shell-out
- Ollama/local LLM prompt execution from this sprint's planning contracts
- remote LLM execution
- real agent execution from M110-M124 contracts
- GitHub API, `gh`, issues, PRs, workflows, network calls, or external services
- validation command execution
- patch application or documentation-agent apply mode
- queue mutation from recommendations
- automatic handoff, automatic completion, autonomous execution, or next-item execution

Closeout guidance:

- use artifacts and recommendations as review inputs only
- require explicit human approval before patch intake or manual handoff
- require parsed evidence and validation results before completion decisions
- keep future execution runners as separate explicit milestones with machine and human gates

## M131 Machine Safety Gate Engine

M131 adds a local-only machine safety gate evaluator:

- `python -m aresforge evaluate-machine-safety-gates --item-id <item_id> --format json`
- optional `--gate-profile`, `--artifact-path`, `--patch-path`, `--execution-record`, `--output`, and `--force`

Runnable behavior:

- reads one local queue item
- evaluates one of eight gate profiles
- checks queue existence, status, dependencies, artifacts, execution records, forbidden capabilities, working tree state, path allowlists, docs-only patch targets, tests/evidence, warning thresholds, transaction logs, and explicit external allowance
- emits stable `machine_safety_gate_evaluation` JSON
- refuses output overwrite unless `--force` is explicit
- always reports `execution_performed=false` and `mutation_performed=false`

Still absent by design:

- agent execution
- Codex execution or Codex CLI shell-out
- Ollama/local LLM or remote LLM prompt execution
- GitHub API, `gh`, issues, PRs, workflows, network calls, or external services
- validation command execution
- patch application
- queue mutation, external mutation, autonomous execution, or next-item execution

## M123 Hub Controlled Automation Workspace Polish

M123 adds no execution surface. It polishes the existing Hub Queue controlled automation workspace so operators can distinguish local advisory review from executable work.

Runnable behavior:

- existing Hub serving remains `python -m aresforge serve-hub`
- Queue panel displays a Controlled Automation Workspace summary
- visible labels state local-only, advisory, operator-gated, no automatic execution, no patch application, and no network/GitHub calls
- Dispatch Review, Artifact Registry, Approval Ledger/Dispatch Gates, and Agent Routing sections have clearer human-review empty states

Still absent by design:

- new execution endpoints
- Codex execution or Codex CLI shell-out
- Ollama/local LLM or remote LLM prompt execution
- agent execution
- GitHub API, `gh`, issues, PRs, workflows, network calls, or external services
- validation command execution
- patch application
- source mutation beyond this milestone's UI/docs update
- queue automation, automatic completion, autonomous execution, or next-item execution

## M122 Safe Queue Mutation Transaction Log

M122 adds a local-only transaction log for queue mutation traceability:

- `python -m aresforge inspect-queue-transaction-log --project-id aresforge --format json`
- optional `--item-id`, `--output`, and `--force`

Runnable behavior:

- stores transaction metadata under `.aresforge/queue/transaction_log.json`
- appends records after successful explicit local queue mutations where practical
- records timestamp, item id, project id, previous status, new status, mutation type, actor/source, evidence summary, and reason
- supports read-only inspection by project and item
- refuses to overwrite output files unless `--force` is explicit

Still absent by design:

- autonomous queue mutation
- Codex execution or Codex CLI shell-out
- Ollama/local LLM or remote LLM prompt execution
- agent execution
- GitHub API, `gh`, issues, PRs, workflows, network calls, or external services
- validation command execution
- patch application
- external mutation, automatic completion, autonomous execution, or next-item execution

## M130 Single-Agent Real Executor for Low-Risk Agents

M130 adds a local-only real single-agent executor command:

- `python -m aresforge run-agent --agent-id <agent_id> --item-id <item_id> --format json`
- optional `--queue-path`, `--output`, `--force`, and `--require-machine-gates`

Runnable behavior:

- validates the requested agent against the M126 registry
- permits only deterministic low-risk local agents
- reads one local queue item
- checks machine gates for local-only, no-network, no-model, no-GitHub, no-patch execution
- writes a stable `single_agent_real_execution` local execution record
- refuses to overwrite output files unless `--force` is explicit

Supported real agents:

- `artifact-registry-agent`
- `evidence-parser-agent`
- `completion-recommendation-agent`
- `validation-agent`
- `queue-planner-agent`
- `sprint-summary-agent`

Still absent by design:

- Codex execution or Codex CLI shell-out
- Ollama/local LLM prompt execution
- remote LLM execution
- GitHub API, `gh`, issues, PRs, workflows, network calls, or external services
- validation command execution
- patch application or documentation patch application
- source mutation, queue completion, automatic handoff, automatic completion, autonomous execution, or next-item execution

## M121 Human Approval Inventory and Review Ledger

M121 adds local approval ledger commands:

- `python -m aresforge inspect-approval-ledger --project-id aresforge --format json`
- `python -m aresforge record-artifact-review --item-id <item_id> --artifact-path <path> --decision approved|rejected|needs_changes --format json`
- optional `--item-id`, `--artifact-path`, `--output`, and `--force`

Runnable behavior:

- reads local dispatch artifact registry output
- reads existing local dispatch approval gates
- reads and writes a local `.aresforge/approval_review_ledger.json` review record file
- records human decisions only when the operator explicitly invokes `record-artifact-review`
- reports approval gaps without approving or executing anything

Still absent by design:

- automatic approval
- queue item start or completion
- agent execution
- Codex execution or Codex CLI shell-out
- Ollama/local LLM or remote LLM prompt execution
- GitHub API, `gh`, issues, PRs, workflows, network calls, or external services
- validation command execution
- patch application
- source mutation from review, queue mutation from ledger inspection, external mutation, automatic completion, autonomous execution, or next-item execution

## M120 Operator Batch Queue Sequencer v2

M120 adds a local-only operator batch sequencing command:

- `python -m aresforge plan-operator-batch-v2 --project-id aresforge --format json`
- optional `--limit`, `--include-blocked`, `--output`, and `--force`

Runnable behavior:

- reads local queue state
- reuses the existing M104 batch planner summary
- reads the local dispatch artifact registry for artifact readiness signals
- reads local dispatch approval gate metadata for approval warnings
- recommends a sequence by priority, dependencies, and local readiness metadata
- groups recommended items by advisory lane
- reports dependency, approval, and artifact warnings without starting work
- writes an optional local report only when the target does not exist or `--force` is explicit

Still absent by design:

- queue item start
- agent execution
- Codex execution or Codex CLI shell-out
- Ollama/local LLM or remote LLM prompt execution
- GitHub API, `gh`, issues, PRs, workflows, network calls, or external services
- validation command execution
- patch application
- queue mutation, external mutation, automatic completion, autonomous execution, or next-item execution

## M119 Dispatch Artifact Registry Index v2

M119 adds a local-only registry inspection command:

- `python -m aresforge inspect-artifact-registry --format json`
- optional `--project-id`, `--item-id`, `--artifact-type`, `--output`, and `--force`

Runnable behavior:

- scans known local artifact directories for M109-M117 planning outputs
- reads JSON artifact metadata where available
- classifies artifact type, item id, project id, milestone, status, blocked state, review requirement, stale queue reference, and duplicates
- emits stable JSON by default
- refuses to overwrite output files unless `--force` is explicit
- preserves `local_only=true` and `execution_allowed=false`

Still absent by design:

- Codex execution or Codex CLI shell-out
- Ollama/local LLM prompt execution
- agent runtime execution
- GitHub API, `gh`, issues, PRs, workflows, network calls, or external services
- patch application
- source mutation, queue mutation, automatic handoff, automatic completion, autonomous execution, or next-item execution

## M129 Single-Agent Dry-Run Executor

M129 adds a local-only single-agent dry-run executor command:

- `python -m aresforge run-agent-dry-run --agent-id <agent_id> --item-id <item_id> --format json`
- optional `--plan-path`, `--queue-path`, `--output`, and `--force`

Runnable behavior:

- validates the requested agent against the M126 registry
- permits only deterministic low-risk dry-run agents
- reads one local queue item
- reads or builds local orchestration-plan metadata
- emits a stable `single_agent_dry_run` execution record
- records blocked forbidden capabilities
- refuses to overwrite output files unless `--force` is explicit

Supported dry-run agents:

- `artifact-registry-agent`
- `evidence-parser-agent`
- `completion-recommendation-agent`
- `validation-agent`
- `sprint-summary-agent`
- `queue-planner-agent`

Still absent by design:

- real agent execution
- Codex execution or Codex CLI shell-out
- Ollama/local LLM prompt execution
- remote LLM execution
- GitHub API, `gh`, issues, PRs, workflows, network calls, or external services
- validation command execution
- patch application
- source mutation, queue mutation from the dry-run, automatic handoff, automatic completion, autonomous execution, or next-item execution

## M118 Post-Automation Planning Reconciliation

M118 adds no runnable product feature. It reconciles the current local-only planning skeleton after M110-M117 and confirms that every automation-facing surface remains advisory, file-backed, and operator-gated.

Current local-only planning skeleton:

- M110 prepares local LLM advisory request artifacts.
- M111 records approval-gated patch proposal intake metadata.
- M112 parses human-pasted dispatch result evidence.
- M113 recommends, but does not perform, queue completion.
- M114 displays dispatch review artifacts in the Hub.
- M115 probes Ollama configuration or loopback model metadata without prompts.
- M116 generates documentation patch proposal artifacts.
- M117 recommends an agent/advisor route lane.

Still absent by design:

- unattended Codex execution
- Ollama or local LLM prompt execution from these contracts
- real agent runtime execution
- GitHub API, `gh`, issues, PRs, workflows, network calls, or external services
- patch application
- source mutation from generated proposals
- queue mutation from recommendations
- automatic handoff, automatic completion, autonomous execution, or next-item execution

## M117 Agent Routing Decision Dashboard

M117 adds a local-only advisory route recommendation command and Hub panel:

- `python -m aresforge recommend-agent-route --item-id <item_id>`
- `python -m aresforge recommend-agent-route --item-id <item_id> --format json`
- optional `--output` and `--force`
- `GET /api/agent-route-recommendation?item_id=<item_id>`
- Queue panel Agent Routing Decision Dashboard

Runnable behavior:

- reads local queue metadata for one item
- classifies documentation, local LLM advisory, coding/dashboard, and validation signals
- emits stable readable or JSON CLI output
- returns a stable Hub JSON payload
- displays recommendation, reasons, blockers, required artifacts, and next safe action in the Hub
- refuses to overwrite output files unless `--force` is explicit
- preserves `human_operator_required=true`, `dispatch_performed=false`, `execution_allowed=false`, and `local_only=true`

Stable recommendation fields:

- `recommendation_type`
- `item_id`
- `title`
- `project_id`
- `milestone`
- `recommended_lane`
- `alternative_lanes`
- `routing_reasons`
- `required_artifacts_before_dispatch`
- `approval_requirements`
- `local_llm_suitable`
- `codex_suitable`
- `documentation_agent_suitable`
- `human_operator_required`
- `dispatch_performed`
- `execution_allowed`
- `local_only`
- `next_safe_action`

Still absent by design:

- dispatch execution
- Hub execute buttons
- Codex execution or Codex CLI shell-out
- Ollama/local LLM prompt execution
- documentation-agent, validation-agent, GitHub-sync-agent, or external-agent execution
- GitHub API, `gh`, issues, PRs, workflows, network calls, or external services
- patch application
- source mutation, queue mutation, automatic handoff, automatic completion, autonomous execution, or next-item execution

## M128 Agent Orchestration Plan Builder

M128 adds a local-only orchestration plan builder command:

- `python -m aresforge build-agent-orchestration-plan --item-id <item_id> --format json`
- optional `--agent-id`, `--execution-target dry-run|real`, `--queue-path`, `--output`, and `--force`

Runnable behavior:

- reads one local queue item
- reads the M126 declarative agent registry
- reads the M127 LLM decision policy recommendation for the item
- emits an ordered `agent_orchestration_plan`
- records required artifacts, dependency checks, machine gates, blocked reasons, and next safe action
- refuses to overwrite output files unless `--force` is explicit
- preserves `execution_performed=false`

Still absent by design:

- agent execution
- Codex execution or Codex CLI shell-out
- Ollama/local LLM prompt execution
- remote LLM execution
- GitHub API, `gh`, issues, PRs, workflows, network calls, or external services
- validation command execution
- patch application
- source mutation, queue mutation, automatic handoff, automatic completion, autonomous execution, or next-item execution

## M127 LLM Decision Policy v1

M127 adds a local-only recommendation command:

- `python -m aresforge recommend-llm-decision --item-id <item_id> --format json`
- optional `--agent-id`, `--task-type`, `--risk-level`, `--mutation-scope`, `--output`, and `--force`

Runnable behavior:

- reads local queue metadata for one item
- applies optional CLI overrides for agent, task type, risk, and mutation scope
- classifies code, docs, planning, validation, GitHub/network, no-LLM, context-size, local-only, repo-aware coding, deterministic validation, test-verifiability, and autonomous-execution signals
- emits stable JSON only
- refuses to overwrite output files unless `--force` is explicit
- preserves `execution_performed=false`

Stable recommendation fields:

- `recommendation_type`
- `item_id`
- `agent_id`
- `recommended_lane`
- `recommended_provider`
- `recommended_model_profile`
- `alternatives`
- `decision_reasons`
- `risk_assessment`
- `autonomy_allowed`
- `machine_gate_required`
- `human_review_required`
- `execution_performed`
- `local_only`
- `next_safe_action`

Still absent by design:

- Codex execution or Codex CLI shell-out
- Ollama/local LLM prompt execution
- remote LLM execution
- documentation-agent, validation-agent, GitHub-sync-agent, or external-agent execution
- GitHub API, `gh`, issues, PRs, workflows, network calls, or external services
- patch application
- source mutation, queue mutation, automatic handoff, automatic completion, autonomous execution, or next-item execution

## M116 Documentation Agent Patch Proposal Generator

M116 adds a local-only documentation patch proposal command:

- `python -m aresforge generate-doc-agent-patch-proposal --item-id <item_id>`
- `python -m aresforge generate-doc-agent-patch-proposal --item-id <item_id> --format json`
- optional `--output`, `--force`, `--include-roadmap`, `--include-context`, and `--include-operator-docs`

Runnable behavior:

- reads local queue state for one item
- reads selected source-of-truth documentation files
- detects missing item, milestone, title, and operator command coverage
- emits stable readable or JSON CLI output
- writes a local structured proposal artifact and proposed patch text file
- refuses to overwrite proposal artifacts unless `--force` is explicit
- preserves `approval_required=true`, `patch_application_allowed=false`, `patch_application_performed=false`, `local_only=true`, and `execution_allowed=false`

Stable proposal fields:

- `artifact_type`
- `generated`
- `blocked`
- `blocked_reasons`
- `item_id`
- `title`
- `project_id`
- `milestone`
- `source_documents_reviewed`
- `detected_doc_gaps`
- `proposed_doc_changes`
- `proposed_patch_path`
- `operator_review_checklist`
- `approval_required`
- `patch_application_allowed`
- `patch_application_performed`
- `local_only`
- `execution_allowed`
- `next_safe_action`

Still absent by design:

- documentation-agent runtime execution
- model execution
- generated patch application
- source documentation mutation from the proposal
- Codex execution, local LLM/Ollama invocation, GitHub API, `gh`, network calls, workflows, or external services
- queue mutation, approval mutation, automatic handoff, automatic completion, or next-item execution

## M114 Hub Dispatch Review Panel

M114 adds a local-only, read-only Hub review surface:

- Hub Queue panel Dispatch Review section
- `GET /api/dispatch-review`
- optional `item_id` and `limit` filters

Runnable behavior:

- scans known local artifact directories
- reads local JSON review artifacts
- normalizes manual dispatch preparation, local LLM advisory request, patch intake, dispatch evidence, and queue completion recommendation records
- emits stable Hub JSON
- displays records in the Queue panel
- preserves `local_only=true`, `read_only=true`, `execution_allowed=false`, `queue_mutation_performed=false`, and `patch_application_allowed=false`

Stable panel fields:

- `panel_type`
- `panel_version`
- `generated_at`
- `local_only`
- `read_only`
- `execution_allowed`
- `execution_performed`
- `queue_mutation_performed`
- `network_execution_performed`
- `patch_application_allowed`
- `patch_application_performed`
- `filters`
- `source_directories`
- `record_count`
- `categories`
- `records`
- `operator_checklist`
- `warnings`
- `next_safe_action`

Still absent by design:

- execution endpoints
- Codex execution or Codex CLI shell-out
- local LLM or Ollama invocation
- documentation-agent execution or apply mode
- GitHub API, `gh`, issues, PRs, workflows, network calls, or external services
- external agent execution
- patch application
- queue mutation, approval mutation, automatic handoff, automatic completion, or next-item execution

## M126 Agent Registry

M126 adds a local-only declarative registry inspection command:

- `python -m aresforge inspect-agent-registry --format json`
- `python -m aresforge inspect-agent-registry --agent-id <agent_id> --format json`
- optional `--safety-class`, `--autonomy-level`, `--output`, and `--force`

Runnable behavior:

- builds a deterministic in-memory registry of known AresForge agents
- filters by agent id, safety class, or autonomy level
- emits stable JSON CLI output or writes a local JSON snapshot
- refuses to overwrite output files unless `--force` is explicit
- preserves `local_only=true`, `read_only=true`, `execution_allowed=false`, and `execution_performed=false`

Stable registry fields:

- `registry_type`
- `generated`
- `agent_count`
- `agents`
- `agents_by_type`
- `agents_by_safety_class`
- `agents_by_autonomy_level`
- `blocked_agents`
- `executable_agents`
- `dry_run_only_agents`
- `local_only`
- `execution_performed`
- `next_safe_action`

Still absent by design:

- real agent execution
- autonomous workflows
- Codex execution or Codex CLI shell-out
- Ollama/local LLM prompt execution
- documentation-agent execution or apply mode
- GitHub API, `gh`, issues, PRs, workflows, network calls, or external services
- external agent execution
- patch application
- queue mutation, approval mutation, automatic handoff, automatic completion, or next-item execution

M126 declares known agents and their boundaries only. Future runners must be separate explicit milestones and must validate against this registry and the M125 runtime boundary before any execution path can start.

## M113 Queue Item Auto-Completion Recommendation Engine

M113 adds a local-only recommendation command:

- `python -m aresforge recommend-queue-completion --item-id <item_id> --evidence-path <path>`
- `python -m aresforge recommend-queue-completion --item-id <item_id> --evidence-path <path> --format json`
- optional `--output`, `--force`, and `--queue-path`

Runnable behavior:

- reads local queue state
- reads a local M112 `dispatch_result_evidence` JSON file
- validates evidence type, item id, parsed state, blocked state, local-only flag, execution flag, and human review requirement
- checks required evidence for changed files, change summary, tests, smoke checks, warnings/blockers, and commit hash
- evaluates queue `completion_requires` and `evidence_required` fields when present
- emits stable readable or JSON CLI output
- refuses to overwrite output files unless `--force` is explicit
- preserves `operator_decision_required=true`, `queue_mutation_performed=false`, `local_only=true`, and `execution_allowed=false`

Stable recommendation fields:

- `recommendation_record_type`
- `recommended_complete`
- `blocked`
- `blocked_reasons`
- `item_id`
- `title`
- `project_id`
- `milestone`
- `evidence_path`
- `evidence_valid`
- `required_evidence_present`
- `missing_evidence`
- `tests_passed_reported`
- `smoke_checks_passed_reported`
- `warnings_or_blockers`
- `commit_hash_present`
- `confidence`
- `operator_decision_required`
- `queue_mutation_performed`
- `local_only`
- `execution_allowed`
- `next_safe_action`

Still absent by design:

- automatic queue completion or any queue mutation
- Codex execution or Codex CLI shell-out
- local LLM or Ollama invocation
- documentation-agent execution or apply mode
- GitHub API, `gh`, issues, PRs, workflows, network calls, or external services
- external agent execution
- patch application
- approval mutation, automatic handoff, or next-item execution

M113 prepares a completion recommendation only. It does not replace human review or the explicit queue lifecycle completion command.

## M125 Agent Runtime Boundary Contract

M125 adds a local-only, read-only boundary inspection command:

- `python -m aresforge inspect-agent-runtime-boundary`
- `python -m aresforge inspect-agent-runtime-boundary --format json`
- `python -m aresforge inspect-agent-runtime-boundary --format markdown`

Runnable behavior:

- builds a deterministic runtime boundary contract in memory
- emits stable readable or JSON CLI output
- defines schema-like agent declaration fields
- defines capability, mutation, network, model, evidence, timeout, retry, safety, and autonomy catalogs
- preserves `local_only=true`, `read_only=true`, `execution_allowed=false`, and `execution_performed=false`

Stable output fields:

- `contract_type`
- `generated`
- `agent_boundary_version`
- `supported_execution_modes`
- `supported_autonomy_levels`
- `supported_safety_classes`
- `allowed_capability_catalog`
- `forbidden_capability_catalog`
- `mutation_scope_catalog`
- `network_scope_catalog`
- `model_scope_catalog`
- `evidence_requirements`
- `default_runtime_limits`
- `local_only`
- `execution_performed`
- `next_safe_action`

Still absent by design:

- real agent execution
- Codex execution or Codex CLI shell-out
- Ollama/local LLM prompt execution
- documentation-agent execution or apply mode
- GitHub API, `gh`, issues, PRs, workflows, network calls, or external services
- external agent execution
- patch application
- queue mutation, approval mutation, automatic handoff, automatic completion, or next-item execution

M125 is a boundary contract only. Future agent runners must be separate explicit milestones and must enforce this contract before any execution path can start.

## M112 Dispatch Result Evidence Parser

M112 adds a local-only evidence parsing command:

- `python -m aresforge parse-dispatch-result-evidence --item-id <item_id> --result-path <path>`
- `python -m aresforge parse-dispatch-result-evidence --item-id <item_id> --result-path <path> --format json`
- optional `--output`, `--force`, and `--queue-path`

Runnable behavior:

- reads local queue state
- reads a local result text or markdown file
- parses common Codex completion sections
- infers file paths, validation lines, smoke lines, and commit hashes when sections are absent
- treats missing sections as warnings
- emits stable readable or JSON CLI output
- refuses to overwrite output files unless `--force` is explicit
- preserves `human_review_required=true`, `local_only=true`, and `execution_allowed=false`

Stable evidence fields:

- `evidence_record_type`
- `parsed`
- `blocked`
- `blocked_reasons`
- `item_id`
- `title`
- `project_id`
- `milestone`
- `result_path`
- `result_exists`
- `files_changed`
- `what_changed`
- `tests_reported`
- `smoke_checks_reported`
- `warnings_or_blockers`
- `commit_hash`
- `validation_confidence`
- `completion_recommendation`
- `human_review_required`
- `local_only`
- `execution_allowed`
- `next_safe_action`

Still absent by design:

- Codex execution or Codex CLI shell-out
- local LLM or Ollama invocation
- documentation-agent execution or apply mode
- GitHub API, `gh`, issues, PRs, workflows, network calls, or external services
- external agent execution
- patch application
- repository mutation from parsed result content
- queue mutation, approval mutation, automatic handoff, automatic completion, or next-item execution

M112 prepares evidence for human review only. It does not complete queue work automatically.

## M111 Approval-Gated Patch Intake Contract

M111 adds a local-only patch proposal intake command:

- `python -m aresforge intake-patch-proposal --item-id <item_id> --patch-artifact <path>`
- `python -m aresforge intake-patch-proposal --item-id <item_id> --patch-artifact <path> --format json`
- optional `--approval-id`, `--output`, `--force`, `--queue-path`, and `--approval-path`

Runnable behavior:

- reads local queue state
- reads local M101 approval gate records
- validates the patch artifact path exists
- summarizes a unified diff locally
- accepts proposals for review only when approval status is `approved_for_manual_handoff`
- emits stable readable or JSON CLI output
- refuses to overwrite output files unless `--force` is explicit
- preserves `operator_review_required=true`, `patch_application_allowed=false`, `patch_application_performed=false`, `local_only=true`, and `execution_allowed=false`

Stable intake fields:

- `intake_record_type`
- `accepted_for_review`
- `blocked`
- `blocked_reasons`
- `item_id`
- `title`
- `project_id`
- `milestone`
- `patch_artifact_path`
- `patch_artifact_exists`
- `patch_summary`
- `approval_gate_id`
- `approval_status`
- `operator_review_required`
- `patch_application_allowed`
- `patch_application_performed`
- `local_only`
- `execution_allowed`
- `next_safe_action`

Still absent by design:

- patch application
- repository file mutation
- Codex execution or Codex CLI shell-out
- local LLM invocation
- documentation-agent execution or apply mode
- GitHub API, `gh`, issues, PRs, workflows, network calls, or external services
- external agent execution
- queue mutation, approval mutation, automatic handoff, automatic completion, or next-item execution

M111 records patch proposal review metadata only. It does not authorize applying a patch.

## M110 Local LLM Advisory Artifact Generator

M110 adds a local-only request artifact command:

- `python -m aresforge generate-local-llm-advisory-artifact --item-id <item_id>`
- `python -m aresforge generate-local-llm-advisory-artifact --item-id <item_id> --format json`
- optional `--output`, `--force`, `--model-profile`, `--reasoning-scope`, `--queue-path`, and `--registry-path`

Runnable behavior:

- reads local queue state
- derives or consumes the M97 dispatch plan
- requires `selected_lane=local_llm_advisory`
- requires an unblocked local-only plan
- requires `execution_allowed=false`
- emits stable readable or JSON CLI output
- writes a JSON artifact under `artifacts/local_llm_advisory/requests` when `--output` is omitted
- refuses to overwrite explicit output files unless `--force` is explicit
- preserves `local_only=true`, `execution_allowed=false`, `local_llm_execution_performed=false`, `codex_execution_performed=false`, `network_execution_performed=false`, and `patch_application_allowed=false`

Stable artifact fields:

- `artifact_type`
- `generated`
- `generated_at`
- `blocked`
- `blocked_reasons`
- `item_id`
- `title`
- `project_id`
- `milestone`
- `queue_status`
- `requested_model_profile`
- `reasoning_scope`
- `source_documents`
- `queue_context`
- `advisory_prompt`
- `expected_response_shape`
- `operator_review_checklist`
- `local_only`
- `execution_allowed`
- `local_llm_execution_performed`
- `codex_execution_performed`
- `network_execution_performed`
- `patch_application_allowed`
- `next_safe_action`

Still absent by design:

- Ollama API calls or local LLM inference
- Codex execution or Codex CLI shell-out
- documentation-agent execution or apply mode
- GitHub API, `gh`, issues, PRs, workflows, network calls, or external services
- external agent execution
- patch application
- queue mutation, approval mutation, automatic handoff, automatic completion, or next-item execution

M110 is a request artifact generator only. It does not authorize local LLM execution.

## M109 Manual Codex Dispatch Runner Contract

M109 adds a local-only preparation command:

- `python -m aresforge prepare-manual-codex-dispatch --item-id <item_id>`
- `python -m aresforge prepare-manual-codex-dispatch --item-id <item_id> --format json`
- optional `--artifact-path`, `--approval-id`, `--queue-path`, `--registry-path`, `--artifact-root`, `--approval-path`, `--output`, and `--force`

Runnable behavior:

- reads local queue state
- derives or consumes the M97 dispatch plan
- requires `selected_lane=codex_prompt_artifact`
- inspects the M106 artifact index when available
- verifies the M98 Codex prompt artifact exists
- reads M101 approval gate records
- requires `approved_for_manual_handoff`
- emits stable readable or JSON preparation records
- refuses to overwrite output files unless `--force` is explicit
- preserves `local_only=true`, `execution_allowed=false`, and `codex_execution_performed=false`

Stable record fields:

- `prepared`
- `blocked`
- `blocked_reasons`
- `item_id`
- `title`
- `project_id`
- `milestone`
- `queue_status`
- `selected_lane`
- `codex_artifact_path`
- `approval_gate_id`
- `approval_status`
- `manual_dispatch_steps`
- `operator_checklist`
- `evidence_expected_after_manual_run`
- `local_only`
- `execution_allowed`
- `codex_execution_performed`
- `next_safe_action`

Still absent by design:

- Codex execution
- Codex CLI shell-out
- local LLM/Ollama invocation
- documentation-agent execution or apply mode
- GitHub API, `gh`, issues, PRs, workflows, network calls, or external services
- external agent execution
- patch application
- queue mutation, approval mutation, automatic handoff, automatic completion, or next-item execution

M109 is a manual-dispatch preparation contract only. It prepares evidence expectations for a later manual run and for M111 approval-gated patch intake.

## M108 Sprint Closeout and Next-Stage Automation Plan

M108 does not add a new runtime command. It is a docs/data closeout workflow that uses existing local inspection commands:

- `python -m aresforge inspect-local-project-report`
- `python -m aresforge inspect-local-queue-agent-summary`
- `python -m aresforge inspect-project-queue --project-id aresforge`
- `python -m aresforge plan-operator-batch --project-id aresforge --limit 10 --format json`
- `python -m aresforge inspect-dispatch-artifacts --format json`
- `python -m aresforge generate-safe-dispatch-handoff --format json`
- `python -m aresforge generate-handoff-package`

Runnable behavior:

- reads current local project, queue, batch plan, artifact index, approval summary, and handoff state through existing commands
- records M99-M107 as the completed dispatch-preparation sprint
- records M96 as older proposed manual planning context
- records empty artifact-index posture until M98-M100 artifacts exist under the default artifact folders
- records persistent local warning noise from `.codex-pytest-cache/` and old pytest temp permission errors
- defines the next controlled automation batch without seeding or implementing it

Still absent by design:

- new runtime feature implementation
- automatic queue seeding
- Codex execution
- Ollama or local LLM invocation
- documentation-agent execution or apply mode
- GitHub API, `gh`, issues, PRs, workflows, network calls, or external services
- external agent execution
- patch application
- automatic artifact execution, handoff, dispatch, queue completion, or next-item execution

M108 prepares the repo for M109+ controlled automation planning. It is not an execution milestone.

## M107 Safe Dispatch Handoff Package

M107 adds a local-only handoff command:

- `python -m aresforge generate-safe-dispatch-handoff`
- `python -m aresforge generate-safe-dispatch-handoff --format json`
- `python -m aresforge generate-safe-dispatch-handoff --output <path> [--force]`
- optional `--project-id`, `--queue-path`, `--registry-path`, `--artifact-root`, and `--approval-path`

Runnable behavior:

- reads branch and HEAD from local git
- reads local project report and queue state
- identifies active/proposed/ready/blocked queue items as next recommended items
- derives M97 dispatch plan summaries for those items
- consumes the M106 dispatch artifact index summary
- reads M101 approval gate status
- emits readable markdown or stable JSON
- refuses to overwrite output files unless `--force` is explicit
- preserves `local_only: true`, `read_only_by_default: true`, and `execution_allowed: false`

Still absent by design:

- artifact execution
- automatic Codex dispatch
- Ollama or local LLM invocation
- documentation-agent execution or apply mode
- automatic approval gate mutation
- queue mutation
- GitHub API, `gh`, issues, PRs, workflows, network calls, or external services
- external agent execution
- patch application
- automatic handoff, sprint execution, or next-item execution

M107 supports new chat handoffs and operator reviews. It does not authorize execution; M108 should use it as closeout and planning context.

## M106 Dispatch Artifact Index/Report

M106 adds a local-only read-only reporting command:

- `python -m aresforge inspect-dispatch-artifacts`
- `python -m aresforge inspect-dispatch-artifacts --format json`
- optional `--project-id`, `--artifact-root`, and `--approval-path`

Runnable behavior:

- scans known artifact directories under the configured artifact root
- recognizes Codex prompt dispatch artifacts, local LLM advisory dry-run outputs, and documentation-agent dry-run outputs
- derives a stable artifact id from artifact type and local path
- derives `item_id` from safe filename conventions
- reports file path, created timestamp, modified timestamp, artifact type, dispatch lane, and next safe action
- reads `.aresforge/dispatch_approval_gates.json` to join approval gate status when available
- handles missing artifact directories as warnings instead of failures
- returns readable markdown or stable JSON
- preserves `local_only: true`, `read_only: true`, and `execution_allowed: false`

Still absent by design:

- artifact execution
- deep content validation or semantic approval
- automatic approval gate creation or mutation
- queue mutation
- Codex execution
- Ollama or local LLM invocation
- documentation-agent execution or apply mode
- GitHub API, `gh`, issues, PRs, workflows, network calls, or external services
- external agent execution
- patch application
- automatic handoff package generation or next-item execution

M106 prepares artifact visibility for M107 safe dispatch handoff packaging. It does not authorize handoff or execution.

## M105 Post-Batch Documentation Reconciliation

M105 does not add a new runtime command. It is a docs/data reconciliation workflow that uses existing local inspection commands:

- `python -m aresforge inspect-local-project-report`
- `python -m aresforge inspect-local-queue-agent-summary`
- `python -m aresforge inspect-project-queue --project-id aresforge`
- `python -m aresforge plan-operator-batch --project-id aresforge --limit 10 --format json`
- `python -m aresforge generate-handoff-package`

Runnable behavior:

- reads current project, queue, batch-planner, and handoff state through existing commands
- updates source-of-truth docs and local project state only
- records that M99-M104 are implemented and completed
- records that M96 remains proposed planning context
- records local warnings from untracked pytest cache and old temp permission errors
- prepares the next recommended manual milestone sequence

Still absent by design:

- new runtime feature implementation
- automatic queue seeding
- Codex execution
- Ollama or local LLM invocation
- documentation-agent execution or apply mode
- GitHub API, `gh`, issues, PRs, workflows, network calls, or external services
- external agent execution
- patch application
- automatic batch execution or next-item execution

M105 prepares docs and queue evidence for M106+ planning. It does not itself create a dispatch artifact index, safe dispatch handoff package, runner contract, advisory artifact generator, or patch intake workflow.

## M104 Operator Batch Planner v1

M104 adds a local-only read-only planning command:

- `python -m aresforge plan-operator-batch --project-id aresforge`
- `python -m aresforge plan-operator-batch --project-id aresforge --limit 10`
- `python -m aresforge plan-operator-batch --project-id aresforge --limit 10 --format json`

Runnable behavior:

- reads the canonical local queue
- filters to the requested project
- excludes completed queue items
- treats `ready` and `proposed` items as plannable
- reports blocked and non-plannable items separately
- respects `dependencies`, `depends_on`, and `blocked_by`
- allows a dependency to be satisfied by an item planned earlier in the same proposed batch
- derives the M97 dispatch plan for safety classification only
- emits `manual_only`, `codex_artifact_possible`, `local_llm_dry_run_possible`, `documentation_dry_run_possible`, or `blocked`
- returns `batch_id`, `generated_at`, `proposed_items`, `excluded_items`, `blocked_items`, `warnings`, and `recommended_next_action`

Still absent by design:

- automatic queue seeding
- queue mutation
- Codex execution
- Ollama or local LLM invocation
- documentation-agent execution or apply mode
- GitHub API, `gh`, issues, PRs, workflows, network calls, or external services
- external agent execution
- patch application
- automatic batch execution or next-item execution

M105 reconciles planned batches against completed queue evidence and documentation/project drift after an operator-run sprint.

## M103 AresForge Self-Managed Project Seed Review

M103 adds a read-only local review command:

- `python -m aresforge inspect-self-managed-project --project-id aresforge`
- `python -m aresforge inspect-self-managed-project --project-id aresforge --format json`

Runnable behavior:

- reads active-project state
- reads managed project registry state
- reads local queue state
- reads existing local project report state
- reads source-of-truth doc presence
- reads current local branch from `.git/HEAD`
- reports project id, repo path, branch, active milestone, queue counts, next recommended item, warnings, blockers, and gaps

Still absent by design:

- registry mutation
- queue mutation
- automatic metadata repair
- GitHub API, `gh`, issues, PRs, workflows, network calls, or external services
- Codex execution
- Ollama or local LLM invocation
- documentation-agent execution or apply mode
- patch application
- automatic batch planning or next-item execution

M104 consumes the M103 review posture before proposing self-managed batches.

## M102 Queue Dependency and Completion Locking Hardening

M102 adds a local-only queue consistency command:

- `python -m aresforge inspect-queue-consistency --project-id <project_id>`
- `python -m aresforge inspect-queue-consistency --project-id <project_id> --format json`
- optional `--queue-path` and `--repo-id` filters

Runnable behavior:

- reads the canonical local queue
- reports dependency locks from `dependencies`, `depends_on`, and `blocked_by`
- reports completion locks from `completion_requires` and `evidence_required`
- blocks start readiness when dependencies or blockers are unresolved
- blocks completion when dependencies are unresolved
- blocks completion when explicit required evidence is missing
- returns JSON-serializable lock reasons and next safe action
- preserves historical completed items without explicit M102 evidence requirements

Still absent by design:

- automated dispatch after lock inspection
- lock bypass from approval status
- Codex execution
- Ollama or local LLM invocation
- documentation-agent execution or apply mode
- GitHub API, `gh`, issues, PRs, workflows, network calls, or external services
- patch application
- automatic next-item execution

M102 gives future dispatch milestones a shared local lock contract to inspect before any separate execution or handoff path can be introduced.

## M101 Human Approval Gate UI/Data Contract

M101 adds local-only approval gate commands:

- `python -m aresforge create-dispatch-approval-gate --item-id <item_id> --artifact-type <type>`
- `python -m aresforge inspect-dispatch-approval-gate --approval-id <approval_id>`
- `python -m aresforge update-dispatch-approval-gate --approval-id <approval_id> --status <status> --review-notes <text>`
- each command supports `--format json|markdown`

Runnable behavior:

- stores records in `.aresforge/dispatch_approval_gates.json`
- creates records with `pending_review` status
- updates records only to `pending_review`, `approved_for_manual_handoff`, `rejected`, or `needs_revision`
- preserves `local_only: true`
- preserves `execution_allowed: false`
- includes approval id, item id, artifact type/path, dispatch lane, reviewer, review notes, checklist, timestamps, status, and next safe action
- exposes a read-only Hub panel at `/api/dispatch-approval-gates` in the Queue review area

Still absent by design:

- automated execution after approval
- Codex dispatch
- Ollama or local LLM invocation
- documentation-agent execution or apply mode
- GitHub API, `gh`, issues, PRs, workflows, network calls, or external services
- patch application
- queue completion, dependency bypass, or automatic next-item execution from approval status

M102 should harden dependency and completion locking around future workflows that consume M101 approval records.

## M100 Documentation Agent Dry-Run Review Workflow

M100 adds a local-only dry-run validation command:

- `python -m aresforge validate-documentation-agent-dry-run --item-id <item_id>`
- `python -m aresforge validate-documentation-agent-dry-run --item-id <item_id> --format json`
- `python -m aresforge validate-documentation-agent-dry-run --item-id <item_id> --output artifacts/documentation_agent/dry_runs/<item_id>.md`

Runnable behavior:

- derives the M97 queue-to-agent dispatch plan for the selected item
- validates `selected_lane == documentation_agent_dry_run`
- validates no dispatch-plan blocked reasons
- validates `local_only is true`
- validates `execution_allowed is false`
- reports dry-run status, readiness, blocked reasons, item identity, queue status, selected lane, confidence, documentation review intent, source docs to review, expected doc updates, stale-doc checks, reconciliation scope, validation expectations, operator gates, and next safe action
- writes a local dry-run artifact only when `--output` is provided
- refuses to overwrite an existing output file unless `--force` is explicit

Still absent by design:

- documentation-agent execution or apply mode
- automatic documentation mutation
- local LLM or Ollama invocation
- Codex execution or automatic prompt dispatch
- external agent execution
- GitHub API, `gh`, issues, PRs, workflows, network calls, or external services
- patch application
- queue mutation, queue completion, or automatic next-item execution from dry-run validation

## M99 Local LLM Advisory Execution Dry-Run Validator

M99 adds a local-only dry-run validation command:

- `python -m aresforge validate-local-llm-advisory-dry-run --item-id <item_id>`
- `python -m aresforge validate-local-llm-advisory-dry-run --item-id <item_id> --format json`
- `python -m aresforge validate-local-llm-advisory-dry-run --item-id <item_id> --output artifacts/local_llm_advisory/dry_runs/<item_id>.md`

Runnable behavior:

- derives the M97 queue-to-agent dispatch plan for the selected item
- validates `selected_lane == local_llm_advisory`
- validates no dispatch-plan blocked reasons
- validates `local_only is true`
- validates `execution_allowed is false`
- reports dry-run status, readiness, blocked reasons, item identity, queue status, selected lane, confidence, advisory intent, recommended model role, context sources, prompt sections, validation expectations, operator gates, and next safe action
- writes a local dry-run artifact only when `--output` is provided
- refuses to overwrite an existing output file unless `--force` is explicit

Still absent by design:

- Ollama API calls or local model execution
- Codex execution or automatic prompt dispatch
- documentation-agent execution or apply mode
- external agent execution
- GitHub API, `gh`, issues, PRs, workflows, network calls, or external services
- patch application
- queue mutation, queue completion, or automatic next-item execution from dry-run validation

## M98 Codex Prompt Dispatch Artifact Generator v1

M98 adds a local-only artifact generation command:

- `python -m aresforge generate-codex-dispatch-artifact --item-id <item_id>`
- `python -m aresforge generate-codex-dispatch-artifact --item-id <item_id> --format json`
- `python -m aresforge generate-codex-dispatch-artifact --item-id <item_id> --output artifacts/codex_prompt_dispatch/generated/<item_id>.txt`

Runnable behavior:

- derives the M97 queue-to-agent dispatch plan for the selected item
- validates `selected_lane == codex_prompt_artifact`
- validates no dispatch-plan blocked reasons
- validates `local_only is true`
- validates `execution_allowed is false`
- renders a copy/paste-ready prompt with safety boundaries, docs/files to inspect, implementation requirements, validation commands, completion criteria, and final response format
- writes a local artifact only when `--output` is provided
- refuses to overwrite an existing output file unless `--force` is explicit

Still absent by design:

- Codex execution or automatic prompt dispatch
- Ollama or local LLM invocation
- documentation-agent execution or apply mode
- external agent execution
- GitHub API, `gh`, issues, PRs, workflows, network calls, or external services
- patch application
- queue mutation, queue completion, or automatic next-item execution from artifact generation

## M97 Queue-to-Agent Dispatch Plan Contract

M97 adds a local-only inspection command and is completed locally:

- `python -m aresforge inspect-queue-dispatch-plan --item-id <item_id>`
- `python -m aresforge inspect-queue-dispatch-plan --item-id <item_id> --format json`

Runnable behavior:

- reads the local queue item
- composes readiness and M80/M86 routing confidence metadata
- selects one advisory dispatch lane
- reports planned artifact intent, approval gates, blocked reasons, safety flags, and next safe action
- keeps output JSON-serializable

Supported lanes:

- `codex_prompt_artifact`
- `local_llm_advisory`
- `local_llm_coding_draft`
- `documentation_agent_dry_run`
- `human_only_manual`

Still absent by design:

- full Codex prompt generation; M98 owns that next artifact step
- Codex execution or prompt dispatch
- Ollama or local LLM invocation
- documentation-agent execution or apply mode
- GitHub API, `gh`, issues, PRs, workflows, network calls, or external agents
- repo mutation, queue mutation, queue completion, or automatic next-item execution from dispatch-plan inspection

## M96 Post-Sprint Planning and Prioritization

M96 adds no runtime command. It uses existing local inspection/report commands to reconcile the completed M81-M95 sprint and plan the next operator-gated batch.

Runnable review surface:

- `python -m aresforge inspect-local-project-report`
- `python -m aresforge inspect-local-queue-agent-summary`
- `python -m aresforge inspect-project-queue --project-id aresforge`
- `python -m aresforge inspect-sprint-batch-report --format json`
- `python -m aresforge generate-handoff-package`

Local data updates allowed:

- seed the M96 queue item if absent
- update source-of-truth documentation
- update local project-state planning fields

Still absent by design:

- new implementation features
- Codex CLI dispatch
- Ollama generation or local LLM inference
- documentation-agent apply mode
- patch application
- GitHub API, `gh`, issues, PRs, workflows, daemon, watcher, scheduler, or external workflow execution
- automatic queue completion or next-item execution

## M95 Final Overnight Sprint Reconciliation

M95 is documentation reconciliation and queue evidence only. It adds no runtime command.

Runnable review surface:

- `python -m aresforge inspect-local-project-report`
- `python -m aresforge inspect-local-queue-agent-summary`
- `python -m aresforge inspect-project-queue --project-id aresforge`
- `python -m aresforge generate-handoff-package`
- `python -m aresforge inspect-sprint-batch-report --format json`

Still absent by design:

- new runtime feature behavior
- automatic documentation rewrites
- local LLM or Codex invocation
- automatic generated-output application
- queue mutation except explicit local queue evidence commands
- automatic next-item execution
- GitHub API, `gh`, issues, PRs, workflows, daemon, watcher, scheduler, or external workflow execution

## M94 Overnight Sprint Batch Report

M94 adds a local sprint batch report:

- `python -m aresforge inspect-sprint-batch-report --format json`
- `python -m aresforge inspect-sprint-batch-report --since-commit <commit> --format json`
- `python -m aresforge inspect-sprint-batch-report --commit-count 20 --output artifacts/reports/m94-sprint-batch.json`

Runnable behavior:

- reads recent local git commits
- reads local queue completion evidence
- reads local dispatch run states and recovered run metadata
- summarizes validation evidence, unresolved warnings, queue posture, and next recommended milestone
- writes a local report artifact only when `--output` is explicitly supplied

Still absent by design:

- GitHub API or `gh`
- external workflows
- Codex execution
- local LLM invocation
- queue mutation or automatic next-item execution

## M93 Operator Handoff Package v2

M93 improves local operator handoff generation:

- `python -m aresforge generate-handoff-package`
- `python -m aresforge generate-handoff-package --output artifacts/handoff/m93-handoff.md --force`

Runnable behavior:

- reports current HEAD and recent local commits
- summarizes queue state, active/ready/proposed items, recovered dispatch history, model routing posture, warnings, and safe command suggestions
- writes a local handoff artifact only when `--output` is explicitly supplied

Still absent by design:

- Codex execution
- local LLM invocation
- prompt or routing execution
- GitHub API or `gh`
- automatic queue completion or next-item execution

## M92 Documentation Reconciliation Plan Generator

M92 expands the existing plan-only documentation reconciliation command:

- `python -m aresforge plan-doc-reconciliation --format json`
- `python -m aresforge plan-doc-reconciliation --format json --output artifacts/doc-reconciliation/m92-plan.json --force`

Runnable behavior:

- reads local source-of-truth docs
- reads local queue state
- reads changed source-doc status and recent local commits through local `git`
- reports stale or missing sections when detectable
- recommends manual documentation updates
- writes a local plan artifact only when `--output` is explicitly supplied

Still absent by design:

- automatic documentation rewrites
- local LLM invocation
- Codex invocation
- prompt execution
- queue mutation, queue completion, or automatic next-item execution
- GitHub API, `gh`, issues, PRs, workflows, daemon, watcher, scheduler, or external workflow execution

## M91 Documentation Agent v1 Contract

M91 adds a read-only documentation agent contract:

- `python -m aresforge inspect-documentation-agent-contract --format json`
- `docs/architecture/DOCUMENTATION_AGENT_CONTRACT.md`

Runnable behavior:

- reports Documentation Agent v1 scope
- lists source-of-truth docs
- lists evidence required before documentation updates
- defines non-mutating plan mode
- reserves future gated apply mode behind explicit operator approval

Still absent by design:

- automatic documentation updates from model output
- documentation apply mode
- queue mutation or queue completion from documentation agent output
- automatic next-item execution
- GitHub API, `gh`, issues, PRs, workflows, daemon, watcher, scheduler, or external workflow execution

## M90 Hub Routing Dashboard Data Contract

M90 adds a read-only Hub routing dashboard data endpoint:

- `GET /api/local-queue/routing-dashboard`
- `GET /api/local-queue/routing-dashboard?project_id=<project_id>&status=<status>`

Runnable behavior:

- reads local queue items and M80/M86 decision metadata
- returns item id, status, risk, task size, recommended engine, recommended lane, recommended model, confidence score, validation burden, warnings, and blockers
- returns summary counts by status, risk, task size, recommended engine, and recommended lane
- includes explicit safety flags for no execution or mutation

Still absent by design:

- mutation endpoints for this contract
- prompt execution
- local LLM or Codex invocation
- automatic queue completion or next-item execution
- GitHub API, `gh`, issues, PRs, workflows, daemon, watcher, scheduler, or external workflow execution

## M88 Human-Gated Patch Application Contract

M88 adds a read-only patch application contract inspector:

- `python -m aresforge inspect-human-gated-patch-application-contract --format json`

Runnable behavior:

- reports the expected patch artifact structure for generated local coding draft patches or instructions
- reports explicit operator approval requirements
- reports pre-apply safety gates and post-apply validation requirements
- confirms patch application is not implemented by this command

Still absent by design:

- automatic file mutation
- automatic patch application
- queue mutation or queue completion from patch artifacts
- automatic next-item execution
- GitHub API, `gh`, issues, PRs, workflows, daemon, watcher, scheduler, or external workflow execution

## M87 Local Coding Draft Artifact Mode

M87 adds local coding draft artifacts:

- `python -m aresforge prepare-local-coding-draft --item-id <item_id> --format json`
- `python -m aresforge prepare-local-coding-draft --item-id <item_id> --run --format json`

Runnable behavior:

- creates a coding draft prompt artifact under `artifacts/local_coding_drafts/generated/`
- default mode does not invoke a provider
- explicit `--run` mode may call local Ollama for draft output and stores draft/metadata artifacts
- marks drafts as non-applied, non-authoritative, and manual-review-only

Still absent by design:

- automatic file mutation
- automatic patch application
- queue mutation or queue completion from draft output
- automatic next-item execution
- GitHub API, `gh`, issues, PRs, workflows, daemon, watcher, scheduler, or external workflow execution

## M85 Local LLM Advisory Run Artifact

M85 adds local advisory prompt and response artifacts:

- `python -m aresforge prepare-local-llm-advisory-run --item-id <item_id> --format json`
- `python -m aresforge prepare-local-llm-advisory-run --item-id <item_id> --run --format json`

Runnable behavior:

- creates a prompt artifact under `artifacts/local_llm_advisory/generated/`
- default mode does not invoke a provider
- explicit `--run` mode may call local Ollama for advisory output and stores response/metadata artifacts
- reports prompt path, response path, provider/model metadata, safety confirmations, and next safe action
- handles unavailable local LLM state safely

Still absent by design:

- automatic application of model output to repo files
- queue mutation or queue completion from advisory output
- automatic next-item execution
- GitHub API, `gh`, issues, PRs, workflows, daemon, watcher, scheduler, or external workflow execution

## M84 Ollama Health Check and Model Inspection

M84 adds explicit local-only Ollama health/model inspection commands:

- `python -m aresforge test-ollama`
- `python -m aresforge inspect-ollama-health --format json`

Runnable behavior:

- checks only the configured local Ollama `/api/tags` endpoint
- reports `available`, `provider`, `endpoint`, `models`, `error_summary`, and `next_safe_action`
- treats Ollama offline state as non-blocking inspection metadata for normal project readiness
- returns visible model metadata without sending prompts or invoking generation

Still absent by design:

- model generation, chat, completion, or prompt execution
- repo or queue mutation from provider output
- automatic queue completion
- automatic next-item execution
- GitHub API, `gh`, issues, PRs, workflows, daemon, watcher, scheduler, or external workflow execution

## M83 Local LLM Provider Contract

M83 adds a local-only provider contract inspection path:

- `python -m aresforge inspect-local-llm-provider-contract --format json`

Runnable behavior:

- reads local LLM environment metadata
- identifies Ollama as the initial local provider target
- reports provider URL, timeout expectations, health-check endpoint boundaries, reasoning/coding/fallback model identifiers, role/capability metadata, and safety confirmations
- confirms contract inspection does not invoke Ollama or any model endpoint

Still absent by design:

- automatic provider invocation
- automatic prompt execution
- repo or queue mutation from provider output
- automatic queue completion
- automatic next-item execution
- GitHub API, `gh`, issues, PRs, workflows, daemon, watcher, scheduler, or external workflow execution

## M82 Self-Managed AresForge Test Run

M82 adds a self-managed, read-only dogfood summary to the local project report:

- `python -m aresforge inspect-local-project-report --format json`

Runnable behavior:

- reports AresForge as its own managed project when local registry and active-project state are present
- summarizes local queue counts, M81/M82 status, and the smoke/readiness flows used for operator review
- lists recovered dispatch runs and confirms audited recovered runs do not block project readiness when dependency completion evidence is present
- returns explicit safety boundary confirmations for no mutation, no automatic next-item execution, no unattended multi-item execution, no GitHub API, no `gh`, and no external workflow behavior

Still absent by design:

- automatic next-item execution
- unattended multi-item execution
- repo or queue mutation from report output
- GitHub API, `gh`, issues, PRs, workflows, daemon, watcher, scheduler, or external workflow execution

## M81 Local LLM Advisory/Coding Lane Prototype

M81 adds a local-only advisory lane readiness inspection path:

- `python -m aresforge inspect-local-llm-advisory-lane-readiness --item-id <item_id> --format json`

Runnable behavior:

- inspects one local queue item
- reuses M80 decision matrix metadata
- reads local LLM provider/model metadata from the local environment contract
- returns a structured advisory plan for reasoning/coding assistance
- confirms provider invocation, prompt dispatch, repo mutation, queue mutation, queue completion, GitHub/`gh`, workflows, and automatic next-item execution are disabled

Still absent by design:

- automatic local LLM invocation
- automatic file edits from local LLM output
- automatic queue completion
- automatic next-item execution
- GitHub API, `gh`, issues, PRs, workflows, or external workflow execution

## M79.4 Codex Dispatch Recovery and Windows argv Hardening

M79.4 adds an explicit recovery command for partial Codex dispatch failures:

- `python -m aresforge recover-codex-dispatch-run --run-id <run_id> --recovery-note "<operator note>" --format json`

Runnable behavior:

- reads one local dispatch `run_state.json`
- marks the run `recovery_required`
- converts stale active states such as `approved_pending_dispatch` and `running` to `failed`
- preserves queue completion as a separate review/validation-gated action
- keeps `automatic_next_item_execution_allowed` false
- parses operator command strings with Windows-aware argv handling; `--command-arg` remains preferred for Windows command construction

Still absent by design:

- automatic queue completion
- automatic next-item execution
- GitHub API, `gh`, issues, PRs, workflows, or external workflow execution
- local LLM execution expansion

## M80 LLM Decision Matrix v2

M80 adds an advisory decision matrix inspection path:

- `python -m aresforge inspect-llm-decision-matrix --item-id <item_id> --format json`
- `python -m aresforge prepare-queue-item-dispatch --item-id <item_id> --target codex --format json`

Runnable behavior:

- inspects one local queue item
- classifies work mode, task size, risk, validation burden, engine/lane recommendation, and model/profile source
- returns safety gating fields that keep prompt dispatch, Codex dispatch, local LLM invocation, queue mutation, and next-item execution disabled
- Prompt Builder artifacts include an M80 advisory decision section
- workflow preparation payloads include `llm_decision_matrix`

Still absent by design:

- automatic prompt dispatch
- Codex execution from the decision matrix
- local LLM invocation from the decision matrix
- automatic queue completion
- automatic next-item execution
- GitHub API, `gh`, issues, PRs, workflows, or external workflow execution

## M79.3 Codex Run Token Usage Capture

M79.3 adds token usage accounting to local Codex dispatch run state:

- `python -m aresforge run-codex-dispatch --item-id <item_id> --run-id <run_id> --command-arg codex --format json`
- `python -m aresforge inspect-codex-dispatch-run --run-id <run_id> --format json`

Runnable behavior:

- captured stdout/stderr transcript text is inspected for a `tokens used` footer
- comma-separated totals such as `221,534` are stored as integer `total_tokens`
- missing or malformed footers produce `token_usage.available: false` with `extraction_error`
- inspect output includes `token_usage`
- old `run_state.json` files without `token_usage` remain inspectable

Still absent by design:

- automatic queue completion
- automatic next-item execution
- unattended multi-item queue execution
- GitHub API, `gh`, issues, PRs, workflows, or external workflow execution
- local LLM execution expansion

## M79.2 Single-Item Ready-to-Codex Automation

M79.2 adds an explicit one-item local automation command:

- `python -m aresforge run-single-ready-codex-queue-item --item-id <item_id> --approved-by local_operator --approval-phrase "APPROVE CODEX DISPATCH" --command-arg codex --validation-command "git diff --check" --format json`

Runnable behavior:

- selects exactly one ready/startable queue item, or fails safely
- prepares the prompt artifact without letting Prompt Builder execute anything
- captures the M78 approval gate using the exact approval phrase
- dispatches the operator-provided command through the hardened stdin prompt workflow
- runs explicit validation commands
- attempts implementation commit/push only after validation passes
- captures queue evidence and closes only the selected item after required gates pass
- attempts queue evidence commit/push separately
- reports recovery-required state if Codex, validation, or commit/push fails
- never starts a next queue item

Still absent by design:

- watcher, daemon, scheduler, or file-change trigger
- unattended multi-item queue execution
- automatic next-item execution
- GitHub API, `gh`, issues, PRs, workflows, or external workflow execution
- local LLM execution expansion

## M79.1 Codex CLI Windows Runner Hardening

M79.1 hardens the M78 runner without changing dispatch gates:

- run-state JSON reads use BOM-tolerant decoding for Windows-created files
- subprocess output is captured as bytes and decoded safely before `stdout.txt` and `stderr.txt` are written
- the approved prompt artifact is passed over UTF-8 stdin to preserve full multi-line prompt bodies
- run-state metadata records prompt stdin handoff and output decoding behavior

Runnable path remains:

- `python -m aresforge prepare-queue-item-dispatch --item-id <item_id> --target codex --format json`
- `python -m aresforge approve-codex-dispatch --item-id <item_id> --approved-by local_operator --approval-phrase "APPROVE CODEX DISPATCH" --format json`
- `python -m aresforge run-codex-dispatch --item-id <item_id> --run-id <run_id> --command-arg codex --format json`
- `python -m aresforge inspect-codex-dispatch-run --run-id <run_id> --format json`

Behavior contract:

- explicit approval is still required before invocation
- one active run at a time remains enforced
- no queue item is completed from dispatch output
- no next queue item is run automatically
- no GitHub API, `gh`, issue, PR, workflow, or external workflow behavior is added
- Codex sandbox limitations may require the operator to commit and push manually when `.git` writes are unavailable

## M78.5 Operator Workflow Compression and Prompt Builder Agent Contract

M78.5 adds a local workflow preparation layer before any operator-approved dispatch:

- `python -m aresforge prepare-queue-item-dispatch --item-id <item_id> --target codex --format json`
- `python -m aresforge prepare-queue-item-dispatch --item-id <item_id> --target codex --start-if-ready --format json`

The command inspects local queue readiness, optionally starts a ready item only when `--start-if-ready` is present, generates a Prompt Builder Agent artifact under `.aresforge/codex_dispatch/prompts/`, inspects the Codex dispatch contract for Codex targets, and returns the next safe operator action.

Behavior contract:

- Prompt Builder output is artifact-only
- no prompt is dispatched automatically
- no Codex approval is created
- no Codex command is executed
- no queue completion is performed
- no next queue item is run automatically
- queue completion still requires review and validation evidence

Next skeleton focus:

- M79 should enforce queue blocking and sequencing.

## M78 Operator-Gated Codex CLI Dispatch Prototype

M78 adds the first local operator-gated dispatch prototype:

- `python -m aresforge approve-codex-dispatch --item-id <item_id> --approved-by local_operator --approval-phrase "APPROVE CODEX DISPATCH" --format json`
- `python -m aresforge run-codex-dispatch --item-id <item_id> --run-id <run_id> --command "<operator-provided command>" --format json`
- `python -m aresforge run-codex-dispatch --item-id <item_id> --run-id <run_id> --command-arg python --command-arg=-c --command-arg "print('codex dispatch smoke')" --format json`
- `python -m aresforge inspect-codex-dispatch-run --run-id <run_id> --format json`
- `python -m aresforge list-codex-dispatch-runs --format json`
- `python -m aresforge cancel-codex-dispatch-run --run-id <run_id> --format json`

Run state is written under `.aresforge/codex_dispatch/runs/<run_id>/` with `run_state.json`, `prompt.txt`, `stdout.txt`, `stderr.txt`, and `artifacts/`.

M78 keeps these runnable-skeleton boundaries:

- one active run at a time
- explicit operator approval before invocation
- operator-provided command only
- no automatic next-item execution
- no automatic queue completion
- review and validation evidence required before queue closeout
- no GitHub API, `gh`, issues, PRs, workflows, external workflow execution, or GitHub mutation
- no local LLM execution expansion

Next recommended milestone: M79 Queue Blocking and Sequencing Enforcement.

## M77 Codex CLI Dispatch Contract

Status: Completed locally on `main`.

Current runnable local skeleton additions:

- `python -m aresforge inspect-codex-dispatch-contract --item-id m77-codex-cli-dispatch-contract --format json` inspects the M77 contract for one queue item
- `python -m aresforge prepare-codex-dispatch-dry-run --item-id m77-codex-cli-dispatch-contract --format json` prepares a dry-run/no-execute contract payload
- optional dry-run contract output may be written only under `.aresforge/codex_dispatch`
- expected future run-state paths are reserved under `.aresforge/codex_dispatch/runs`

Behavior contract:

- the command inspects the canonical local queue and managed project/repo binding
- the contract describes exactly one queue item at a time
- `dry_run_only` is true
- `dispatch_allowed` is false
- `codex_cli_invocation_allowed` is false
- `automatic_next_item_execution_allowed` is false
- `operator_approval_required` is true
- command previews are labeled preview-only and not executable in M77

Still absent by design:

- Codex CLI dispatch
- Codex CLI process invocation
- operator-approved Codex run execution
- automatic Codex execution
- automatic agent execution
- automatic queue execution
- unattended multi-item execution
- automatic next-item execution
- GitHub API, `gh`, issues, PRs, workflows, or GitHub mutation
- local LLM execution expansion

Future M78 gates before any invocation:

- explicit operator approval
- one item at a time
- active run-state check
- stdout/stderr/artifact capture
- review evidence before completion
- validation evidence before commit/push
- dependency blocking respected
- no automatic next-item execution
- GitHub/`gh`/API/workflow mutation remains blocked

Recommended next milestone:

- M78 Operator-Gated Codex CLI Dispatch Prototype.

## M76 Self-Seed AresForge as the First Managed Project

Status: Completed locally on `main`.

Current runnable local skeleton:

- `python -m aresforge serve-hub` serves the local Hub
- `python -m aresforge seed-aresforge-self-project --format json` idempotently registers AresForge as managed project `aresforge`, primary repo `aresforge-main`, and seeds proposed M77-M82 queue items
- `python -m aresforge inspect-managed-project --project-id aresforge --format json` inspects the self-managed project
- `python -m aresforge inspect-managed-repo --project-id aresforge --repo-id aresforge-main --format json` inspects the primary self-managed repo
- `python -m aresforge inspect-project-queue --project-id aresforge --format json` inspects the canonical queue entries
- project/repo surfaces use the local managed-project registry and project factory storage
- queue lifecycle uses the canonical local queue
- prompt-pack generation creates preview text and optional local artifacts for manual handoff
- Local LLM Health Check inspects only configured local provider availability/model listing when explicitly invoked
- Local LLM Prompt Preview is preview-only and does not call a provider
- M62 local LLM execution prototype can call only a configured local provider after explicit operator gates and remains advisory-only/non-mutating
- Codex high-value lane generates prompts for manual handoff and does not invoke Codex CLI
- AI Action Review, execution audit log, AI artifact registry, and Operator Run History are review-only local evidence surfaces

Still absent by design:

- Codex CLI dispatch
- automatic Codex execution
- automatic agent execution
- external workflow execution
- GitHub API, `gh`, issues, PRs, workflows, or GitHub mutation from the app
- unattended multi-item queue execution
- local LLM or Codex output applying changes to repo files automatically

M76 self-seed boundary:

- no Hub/API/UI surface was required; the existing local CLI/registry/queue inspection surfaces cover this milestone
- self-seed does not dispatch Codex, run Codex CLI, execute agents, execute prompts, call local LLMs, call GitHub APIs, call `gh`, create issues, open PRs, run workflows, commit, or push

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

Recommended next milestone after M76:

- M77 Codex CLI Dispatch Contract.

## M75 Source-of-Truth Documentation and Roadmap Reconciliation

Status: Completed on `main` in commit `7088204`.

## M74 Hub UX Stabilization Pass

Status: Completed locally on `main`.

Implemented runnable path:

- Queue UI copy and labels in `src/aresforge/hub/static/index.html`
- Queue UI render/bind helpers in `src/aresforge/hub/static/js/sections/queue.js`
- existing local-only Hub routes for queue lifecycle, prompt packs, local LLM preview/prototype, audit log, artifact registry, run history, and AI Action Review Panel

Behavior contract:

- Hub labels now more clearly distinguish inspect/review/preview/copy/gated status actions from execution
- prompt-pack preview includes a copy-only manual handoff control
- local LLM provider/config wording remains prototype-scoped and does not imply production execution
- AI review wording emphasizes safety status, gate status, no automatic execution, no repo mutation, and next safe action metadata

Still absent by design:

- new backend capabilities
- automatic execution or prompt dispatch
- Codex execution or Codex CLI invocation
- local LLM repo mutation
- automatic agent execution
- GitHub API, `gh`, issues, PRs, workflows, or external workflow behavior

Next skeleton focus:

- M75 should reconcile source-of-truth documentation and the roadmap.

## M73 Prompt Pack Quality and Routing Improvements

Status: Completed locally on `main`.

Implemented runnable path:

- operator helper: `generate_local_queue_prompt_pack(...)`
- Hub route: `POST /api/local-queue/prompt-pack`
- Queue UI panel: Agent Prompt Pack Generator

Behavior contract:

- generated prompt packs expose routing-aware lane guidance, advisory model/engine recommendation text, task sizing guidance, validation expectations, smoke checks, and final response requirements
- high-value Codex prompts are labeled prompt-generation/operator-handoff only
- local LLM advisory prompts explicitly prohibit repo mutation from local LLM output
- prompt-pack text remains manual copy/paste output and avoids nested markdown fences

Still absent by design:

- automatic prompt dispatch or execution
- Codex execution or Codex CLI invocation
- local LLM execution from prompt packs
- automatic agent execution
- GitHub API, `gh`, issues, PRs, workflows, or GitHub mutation
- repository mutation from local LLM output

Next skeleton focus:

- M74 should perform a Hub UX stabilization pass.

## M72 Local LLM Provider Configuration Hardening

Status: Completed locally on `main`.

Implemented runnable path:

- operator helpers: `read_local_llm_environment_contract(...)`, `update_local_llm_environment_contract(...)`, and `check_local_llm_health(...)`
- Hub routes: `GET /api/local-llm/environment`, `POST /api/local-llm/environment`, and `POST /api/local-llm/health-check`

Behavior contract:

- local LLM environment payloads now expose provider availability status, provider configuration status, provider execution mode, provider state, advisory model profiles, and fallback behavior
- provider states distinguish configured, missing configuration, unavailable, unsupported, disabled, and prototype-only execution mode
- local model profiles describe provider, model name, intended lane, recommended use, hardware notes, status, advisory warnings, and prototype warnings
- health-check output keeps provider reachability/model listing separate from execution authorization

Still absent by design:

- automatic local LLM execution
- local LLM execution outside the M62 explicit operator-gated prototype
- prompt sending or inference during health checks
- Codex execution or Codex CLI invocation
- automatic agent execution
- GitHub API, `gh`, issues, PRs, workflows, or GitHub mutation
- repository mutation from local LLM output

Next skeleton focus:

- M73 should improve prompt-pack quality and routing guidance.

## M71 Operator-Facing AI Action Review Panel

Status: Completed locally on `main`.

Implemented runnable path:

- Hub route: `GET /api/ai-action-review`
- Queue UI panel: AI Action Review Panel
- operator helper: `read_ai_action_review_panel(...)`

Behavior contract:

- composes local AI action safety metadata, execution audit entries, AI artifact records, Operator Run History timeline entries, and local queue AI routing metadata
- displays action name, safety status, gate status, blocked action, blocked reason category, blocked reason, non-automatic execution flag, non-repo-mutation flag, artifact references, audit references, run-history timeline entries, and next safe operator action
- uses useful read-only empty states when no recent AI actions, artifacts, blocked actions, or audit entries are found

Still absent by design:

- execution controls
- Codex execution or Codex CLI invocation
- local LLM execution from the panel
- automatic agent execution
- GitHub API, `gh`, issues, PRs, workflows, or GitHub mutation
- repository mutation from AI output

Next skeleton focus:

- M72 should harden local LLM provider configuration.

## M70 Local AI Operations Verification Sweep

Status: Completed locally on `main`.

Verified runnable surface:

- local LLM environment contract, health check, prompt preview, and M62 explicit operator-gated local execution prototype
- Codex CLI model profile contract and Codex high-value prompt-generation/operator-handoff lane
- execution audit log, AI action safety gate, AI artifact registry, and Operator Run History
- queue lifecycle, Hub API, and Hub UI surfaces that render local AI safety and non-mutation metadata

Stabilization applied:

- prohibited PR-shaped action names are classified as policy-blocked by the safety gate
- Operator Run History timeline rendering now shows existing safety status, gate status, and non-mutation state
- docs now identify M70 as completed verification and recommend M71 as the next operator-facing review-panel milestone

Still absent by design:

- automatic Codex execution or Codex CLI invocation
- automatic agent execution
- GitHub API, `gh`, issues, PRs, workflows, or GitHub mutation
- automatic repository mutation from generated local LLM or Codex output
- local LLM execution beyond the M62 explicit operator-gated local prototype

Next skeleton focus:

- M71 may add an Operator-Facing AI Action Review Panel if approved.

## M69 Local AI Operations Hardening

Status: Completed locally on `main`.

Hardened runnable path:

- AI action safety gate remains local-only decision/reporting logic and now reports explicit safety status, gate status, blocked action, blocked reason category, and operator next safe action
- execution audit log records blocked/allowed/dry-run outcomes with consistent non-mutation flags
- AI artifact registry records generated advisory artifacts with explicit advisory-only and non-mutation metadata
- Operator Run History combines audit and artifact entries while preserving safety/gate status and non-execution flags

Still absent by design:

- automatic Codex execution or Codex CLI invocation
- automatic agent execution
- GitHub API, `gh`, issues, PRs, workflows, or GitHub mutation
- automatic repository mutation from generated local LLM or Codex output
- local LLM execution beyond the M62 explicit operator-gated local prototype

Next skeleton focus:

- M70 completed Local AI Operations Verification Sweep.

## M68 Local AI Operations Closeout Reconciliation

Status: Completed locally on `main`.

Reconciled runnable surface:

- project AI settings and UI
- agent/engine registry
- queue routing metadata and routing decision matrix v1
- routed queue views as filtered views over the canonical local queue
- routing-aware prompt packs
- local LLM environment contract, health check, prompt preview, and operator-gated execution prototype
- Codex CLI model profile contract and high-value prompt lane
- execution audit log, AI action safety gate, AI artifact registry, and Operator Run History panel

Still absent by design:

- automatic Codex execution or Codex CLI invocation
- automatic agent execution
- GitHub API, `gh`, issues, PRs, workflows, or GitHub mutation
- repository file mutation from generated local LLM or Codex output
- split queues or routed queue storage separate from the canonical local queue
- local LLM execution beyond the M62 explicit operator-gated prototype

Next skeleton focus:

- M69 completed Local AI Operations Hardening.

## M67 Operator Run History Panel

Status: Completed locally on `main`.

Implemented runnable path:

- operator helper: `read_operator_run_history(...)`
- Hub route: `GET /api/operator-run-history`
- Queue UI panel: Operator Run History

Behavior contract:

- read execution audit log and AI artifact registry as local data sources
- combine audit and artifact records into a normalized timeline
- sort timeline entries newest first
- filter by project id, item id, action type, artifact type, and limit
- report totals, warnings, blockers, and next safe action

Still absent by design:

- execution controls
- apply/delete controls
- Codex CLI execution
- GitHub API, `gh`, issues, PRs, or workflow activity
- local LLM execution beyond M62
- automatic agent execution

Follow-up:

- M68 added Local AI Operations Closeout Reconciliation.

## M66 AI Artifact Registry

Status: Completed locally on `main`.

Implemented runnable path:

- operator helpers: `register_ai_artifact(...)`, `read_ai_artifact_registry(...)`, `filter_ai_artifacts(...)`, `verify_ai_artifact_exists(...)`
- local storage: `.aresforge/ai_artifact_registry.json`
- Hub route: `GET /api/ai-artifacts`
- Queue UI panel: AI Artifact Registry

Behavior contract:

- register metadata for successful local artifact writes
- read missing/empty registry files safely
- filter by project, item, artifact type, source action, engine, exists state, and limit
- recompute local file existence/checksum on read
- avoid storing secret-like strings
- never overwrite artifact content

Still absent by design:

- artifact execution or application
- Codex CLI execution
- GitHub API, `gh`, issues, PRs, or workflow activity
- local LLM execution beyond M62
- automatic agent execution
- automatic file edits, queue completion, commits, pushes, or external workflow execution

Follow-up:

- M67 added an Operator Run History Panel over local action history.

## M65 AI Action Safety Gate

Status: Completed locally on `main`.

Implemented runnable path:

- operator helper: `evaluate_ai_action_safety_gate(...)`
- Hub route: `POST /api/ai-action-safety-gate`
- integrated decision payloads into local LLM execution and Codex high-value prompt generation

Behavior contract:

- evaluate action type, item/routing context, engine/model/lane, risk, complexity, operator override, operator gate confirmation, and dry-run state
- return allowed/blocked/warning/operator-gate/operator-override/preview-only decisions
- keep `execution_allowed: false` for preview-only actions
- block Codex execution and GitHub/`gh` mutation representations
- report blockers and next safe action without executing anything

Still absent by design:

- new execution behavior
- Codex CLI execution
- GitHub API, `gh`, issues, PRs, or workflow activity
- local LLM execution beyond M62
- automatic agent execution
- automatic file edits, queue completion, commits, pushes, or external workflow execution

Next skeleton focus:

- M66 should add an AI Artifact Registry for advisory outputs and generated artifacts.

## M64 Execution Audit Log

Status: Completed locally on `main`.

Implemented runnable path:

- operator helpers: `append_execution_audit_entry(...)`, `read_execution_audit_log(...)`, `filter_execution_audit_log(...)`
- local storage: `.aresforge/execution_audit_log.json`
- Hub route: `GET /api/execution-audit-log`
- Queue UI panel: Execution Audit Log

Behavior contract:

- append audit entries for operator-gated AI/lane-adjacent actions
- read missing/empty audit logs safely
- filter by project, item, action type, engine, executed state, outcome, and limit
- record summaries and artifact paths instead of full prompt or response bodies
- redact secret-like strings
- keep audit write failures best-effort and non-executing

Still absent by design:

- automatic Codex execution
- new local LLM execution paths beyond M62
- GitHub API, `gh`, issues, PRs, or workflow activity
- repo mutation from AI output
- automatic agent execution
- automatic file edits, queue completion, commits, pushes, or external workflow execution

Next skeleton focus:

- M65 should add an AI Action Safety Gate before any future execution expansion.

## M63 Codex CLI High-Value Lane

Status: Completed locally on `main`.

Implemented runnable path:

- operator helper: `generate_codex_high_value_lane_prompt(...)`
- Hub route: `POST /api/local-queue/items/{item_id}/codex-high-value-prompt`
- Queue UI panel: Codex High-Value Lane
- optional local prompt artifact output with `force` overwrite gate

Behavior contract:

- reads queue item routing metadata from the canonical local queue
- evaluates Codex-worthiness using engine, lane, risk, complexity, affected area, validation burden, project AI mode, and operator override
- produces a copy/paste prompt preview only
- includes local-first operating rules, files to inspect, pre-checks, validation commands, smoke checks, `git diff --check`, and final response expectations
- returns `execution_allowed: false`

Still absent by design:

- automatic Codex execution
- Codex CLI process invocation
- GitHub API, `gh`, issues, PRs, or workflow activity
- repo mutation from Codex output
- automatic agent execution
- automatic file edits, queue completion, commits, pushes, or external workflow execution

Next skeleton focus:

- M64 should add an Execution Audit Log for operator-gated runs and advisory outputs.

## M62 Operator-Gated Local LLM Execution Prototype

Status: Completed locally on `main`.

Implemented runnable path:

- operator helper: `execute_local_llm_for_queue_item(...)`
- Hub route: `POST /api/local-queue/items/{item_id}/local-llm-execute`
- Queue UI panel: Prototype: Run Local LLM
- optional local result artifact output with `force` overwrite gate

Behavior contract:

- dry run validates preview and local gates without calling the provider
- real execution requires `confirm_operator_gate: true`
- reads routing metadata from the canonical local queue
- generates prompt preview before execution
- requires local LLM environment `execution_enabled: true` and `operator_gate_required: true`
- requires local `ollama` provider URL and reachable health check
- requires model availability from the local health check
- returns advisory response text and `executed` state

Still absent by design:

- Codex CLI execution
- GitHub integration or mutation
- non-local provider execution
- automatic agent execution
- automatic file edits, queue completion, commits, pushes, or workflow execution

Next skeleton focus:

- M63 should add Codex CLI High-Value Lane as non-automatic and operator-gated.

## M61 Local LLM Prompt Preview

Status: Completed locally on `main`.

Implemented runnable path:

- operator helper: `generate_local_llm_prompt_preview(...)`
- Hub route: `POST /api/local-queue/items/{item_id}/local-llm-prompt-preview`
- Queue UI panel: Local LLM Prompt Preview
- optional local artifact output path with `force` overwrite gate

Behavior contract:

- reads queue item routing metadata from the canonical local queue
- reads the local LLM environment contract without calling the provider
- produces copy/paste prompt preview text only
- includes task details, project context, routing metadata, local-only rules, validation expectations, and final response format
- blocks unrouted items, `codex_cli` routes, missing environment/model configuration, and manual-only policy without override
- returns `execution_allowed: false`

Still absent by design:

- Ollama calls
- local LLM inference or generation
- prompt execution
- Codex CLI execution
- real agent execution
- GitHub integration or mutation
- external workflow execution

Follow-up skeleton focus:

- M62 added the first operator-gated local LLM execution prototype.

## M60 Codex CLI Model Profile Contract

Status: Completed locally on `main`.

Implemented runnable path:

- operator helpers: `read_codex_cli_model_profile_contract(...)`, `update_codex_cli_model_profile_contract(...)`, `validate_codex_cli_model_profile_contract(...)`
- Hub routes: `GET /api/codex-cli/model-profiles`, `POST /api/codex-cli/model-profiles`
- storage path: `.aresforge/codex_cli_model_profiles.json`

Behavior contract:

- reads default profile contract without writing a file
- writes settings only after validation passes
- fixes `codex_engine_key` to `codex_cli`
- validates default, high-value, and fast models against `allowed_codex_models`
- validates per-project and per-agent allowed model mappings
- forces `execution_enabled` to remain false and `operator_gate_required` to remain true
- returns `execution_allowed: false`

Still absent by design:

- Codex CLI execution
- prompt execution
- High-Value Codex Lane execution
- real agent execution
- GitHub integration or mutation
- external workflow execution

Next skeleton focus:

- M63 should add Codex CLI High-Value Lane.

## M59 Local LLM Health Check

Status: Completed locally on `main`.

Implemented runnable path:

- operator helper: `check_local_llm_health(...)`
- Hub route: `POST /api/local-llm/health-check`
- source contract: `.aresforge/local_llm_environment.json`

Behavior contract:

- health check runs only when explicitly invoked
- provider `none` and `unknown` return unavailable/blocked status without HTTP calls
- provider `ollama` may call only local `/api/tags`
- non-local provider URLs are blocked
- returns provider reachability, available models, configured model availability, `inference_tested: false`, and `execution_allowed: false`
- rejects prompt/execution/routing payload fields on the API

Still absent by design:

- prompt execution
- model inference
- local LLM generation
- generate/chat/completion endpoint calls
- Codex execution
- real agent execution
- GitHub integration or mutation
- queue/project mutation

Follow-up skeleton focus:

- M61 added Local LLM Prompt Preview.
- M62 added an Operator-Gated Local LLM Execution Prototype after additional gates were added.

## M58 Local LLM Environment Contract

Status: Completed locally on `main`.

Implemented runnable path:

- operator helpers: `read_local_llm_environment_contract(...)`, `update_local_llm_environment_contract(...)`, `validate_local_llm_environment_contract(...)`
- Hub routes: `GET /api/local-llm/environment`, `POST /api/local-llm/environment`
- storage path: `.aresforge/local_llm_environment.json`

Behavior contract:

- reads default contract without writing a file
- writes settings only after validation passes
- supports providers `ollama`, `none`, and `unknown`
- stores provider URL and model placeholder/config names
- stores optional positive integer context and timeout values
- allows `health_check_enabled` as configuration only
- forces `execution_enabled` to remain false and `operator_gate_required` to remain true
- returns `execution_allowed: false`

Still absent by design:

- Ollama calls
- health checks
- model API calls
- prompt execution
- routing execution
- local LLM execution
- Codex execution
- real agent execution
- GitHub integration or mutation

Next skeleton focus:

- M59 should add Local LLM Health Check.

## M57 Prompt Pack Routing Integration

Status: Completed locally on `main`.

Implemented runnable path:

- operator helper: `generate_local_queue_prompt_pack(...)`
- Hub route: `POST /api/local-queue/prompt-pack`
- Queue UI panel: Agent Prompt Pack Generator

Behavior contract:

- prompt packs include routing metadata by default
- unrouted items are marked as manual routing required
- Codex and local LLM recommendations are advisory only
- prompt items include dependencies when available
- routing grouping can be enabled for agent lane, engine, model, risk, complexity, or status
- `execution_allowed` is always false
- safe artifact output behavior still refuses overwrite unless `force=true`

Still absent by design:

- prompt execution
- automatic routing apply
- queue item start or completion
- local LLM execution
- Codex execution
- real agent execution
- GitHub integration or mutation
- queue storage split

Next skeleton focus:

- M58 should add Local LLM Environment Contract.

## M56 Routed Queue Views

Status: Completed locally on `main`.

Implemented runnable path:

- operator helper: `read_local_routed_queue_views(...)`
- Hub route: `GET /api/local-queue/routed-views`
- Queue UI panel: Routed Queue Views

Behavior contract:

- reads from the canonical local queue only
- filters queue items by project, status, agent lane, engine, model, fallback engine, risk, complexity, project AI mode, routing policy source, and operator override state
- groups queue items by agent lane, engine, model, project policy, risk level, complexity level, or status
- includes unrouted items by default
- safely handles queue items without routing metadata and empty queue state
- returns stable JSON with `execution_allowed: false`

Still absent by design:

- separate routed queues or split queue storage
- prompt-pack routing integration
- local LLM execution
- Codex execution
- real agent execution
- GitHub integration or mutation
- prompt execution

Next skeleton focus:

- M57 should add Prompt Pack Routing Integration.

## M55 Project AI Settings UI

Status: Completed locally on `main`.

Implemented runnable path:

- Projects UI panel: Project AI Settings
- API reads: `GET /api/projects/{project_id}/ai-settings`
- API writes: `POST /api/projects/{project_id}/ai-settings`

Behavior contract:

- loads settings for the active project
- updates settings only through explicit operator save
- exposes all supported modes: `balanced`, `local_only`, `codex_only`, `cost_saver`, `high_confidence`, `manual_only`
- exposes supported engines: `local_reasoning_llm`, `local_coding_llm`, `codex_cli`
- displays validation status, warnings, blockers, and next safe action
- invalid settings are rejected by the backend and shown in the UI

Still absent by design:

- routing execution
- local LLM execution
- Codex execution
- real agent execution
- GitHub integration or mutation
- prompt execution
- complex model management

Next skeleton focus:

- M56 should add Routed Queue Views.

## M54 Routing Decision Matrix v1

Status: Completed locally on `main`.

Implemented runnable path:

- operator helpers: `recommend_queue_item_routing(...)`, `apply_queue_item_routing_recommendation(...)`
- Hub routes: `POST /api/local-queue/items/{item_id}/routing-recommendation`, `POST /api/local-queue/items/{item_id}/apply-routing-recommendation`
- Queue UI actions: Recommend Routing and Apply Routing Metadata

Behavior contract:

- reads queue item context, M51 settings, M52 registry, and M53 metadata validation
- recommends agent lane, engine, fallback engine, risk/complexity, routing reason, escalation reason, policy source, and operator override context
- `balanced` recommends local engines for simple work and can recommend Codex for high-value work
- `codex_only` recommends `codex_cli`
- `local_only` avoids `codex_cli` and blocks Codex-worthy work without override
- `cost_saver` prefers local engines and warns on high-risk Codex-worthy work
- `high_confidence` prefers `codex_cli` for high-risk or high-complexity work
- `manual_only` requires an explicit operator decision
- explicit apply writes M53 queue routing metadata only

Still absent by design:

- local LLM execution
- Codex execution
- real agent execution
- GitHub integration or mutation
- prompt execution
- queue storage split

Next skeleton focus:

- M55 should add Project AI Settings UI.

## M53 Queue Routing Metadata Contract

Status: Completed locally on `main`.

Implemented runnable path:

- operator helpers: `default_queue_routing_metadata(...)`, `validate_queue_routing_metadata(...)`, `update_local_queue_item_routing_metadata(...)`
- Hub route: `POST /api/local-queue/items/{item_id}/routing-metadata`
- Queue detail read-only display for routing metadata

Behavior contract:

- new queue items include default empty/unassigned routing metadata
- legacy queue items without metadata are safely normalized in item views
- metadata updates validate M52 agent lane keys and engine keys
- `risk_level` must be `low`, `medium`, `high`, `critical`, or `unknown`
- `complexity_level` must be `low`, `medium`, `high`, or `unknown`
- invalid metadata is rejected before writing
- prompt-pack generation, evidence capture, and closeout continue to operate without executing routing

Still absent by design:

- Routing Decision Matrix v1
- runtime Agent/LLM routing
- prompt-pack routing assignment
- Codex CLI execution
- local LLM execution
- real agent execution
- GitHub integration or mutation
- queue storage split

Next skeleton focus:

- M54 should implement Routing Decision Matrix v1.

## M52 Agent and Engine Registry Contract

Status: Completed locally on `main`.

Implemented runnable path:

- operator function: `read_agent_engine_registry(...)`
- Hub route: `GET /api/agent-engine-registry`

Behavior contract:

- returns a stable read-only registry of future agent lanes and engines
- includes required lane keys, display names, purposes, default allowed engines, recommended default engines, and risk notes
- includes required engine keys, display names, purposes, local-only boundary notes, model profile placeholders, availability status, and operator gate requirements
- marks all lanes `routing_only: true` and `execution_allowed: false`
- marks all engines `execution_allowed: false`
- reports `next_safe_action` for future routing contract validation only

Still absent by design:

- runtime Agent/LLM routing
- routed queue metadata
- prompt-pack routing assignment
- Codex CLI execution
- local LLM execution
- real agent execution
- GitHub integration or mutation
- complex registry UI

Next skeleton focus:

- M53 should add the Queue Routing Metadata Contract.

## M51 Project AI Settings Contract

Status: Completed locally on `main`.

Implemented runnable path:

- operator functions: `read_project_ai_settings(...)`, `update_project_ai_settings(...)`, `validate_project_ai_settings(...)`
- file-backed artifact: `.aresforge/projects/{project_id}/ai_settings.json`
- Hub routes: `GET /api/projects/{project_id}/ai-settings` and `POST /api/projects/{project_id}/ai-settings`

Behavior contract:

- returns default valid settings for a project with no explicit AI settings file
- writes validated project settings only when the operator/API submits a valid contract
- validates supported project modes, supported engine keys, default engine availability, disabled engine conflicts, local-only/Codex-only restrictions, and `manual_only` default omission
- reports `next_safe_action`, warnings, blockers, and `routing_execution_status: not_implemented`

Still absent by design:

- runtime Agent/LLM routing
- routed queue metadata
- prompt-pack routing assignment
- Codex CLI execution
- local LLM execution
- real agent execution
- GitHub integration or mutation
- Hub settings UI

Next skeleton focus:

- M52 should add the Agent and Engine Registry Contract.

## M50 Handoff Generator

Status: Completed locally on `main`.

Implemented runnable path:

- operator function: `generate_local_project_handoff(...)`
- Hub route: `POST /api/local-project/handoff`
- Handoff UI panel: Local Project Handoff Generator

Behavior contract:

- reads existing local active project, queue, Reports v1, evidence, closeout, and M48 progress rollup state
- generates copy/paste-ready markdown for next-chat/project handoff
- includes project name, repo path, branch expectation, current operating rules, latest known milestone/commit, architecture boundaries, Hub capabilities, queue/report/progress state, open queue work, blockers/warnings, evidence/closeout state, recommended next milestone/instruction, and startup validation commands
- optional local artifact output uses safe non-overwrite behavior unless `force=true`

Still absent by design:

- runtime Agent/LLM routing
- Codex CLI execution
- local LLM execution
- real agent execution
- GitHub integration or mutation
- automatic posting or external workflow execution

Next skeleton focus:

- M51 should begin Project AI Settings Contract.

## M49 Reports v1

Status: Completed locally on `main`.

Implemented runnable path:

- operator function: `read_local_project_reports(...)`
- Hub route: `GET /api/reports/local-projects`
- Reports UI panel: Reports v1

Behavior contract:

- reads existing local project, active project, queue, evidence, closeout, and M48 progress rollup state
- summarizes project counts, active project, queue totals, status/type/lane counts, blocked/ready/in-progress items, evidence capture, closeout eligibility, closed/completed items, latest activity, blockers, warnings, limitations, and `next_safe_action`
- reports local-only operating boundaries in the payload

Still absent by design:

- PDF/CSV/export workflow expansion
- runtime Agent/LLM routing
- Codex CLI execution
- local LLM execution
- real agent execution
- GitHub integration or mutation

Next skeleton focus:

- M50 should implement Handoff Generator.

## M48 Project Progress Rollup

Status: Completed locally on `main`.

Implemented runnable path:

- operator function: `read_local_project_progress_rollup(...)`
- Hub route: `GET /api/projects/{project_id}/progress-rollup`
- Projects UI panel: Project Progress Rollup

Behavior contract:

- reads existing managed project, active project, and local queue files
- summarizes project queue progress without mutating state
- reports total items, counts by status/type/lane, ready items, blocked items, in-progress items, evidence captured, closeout eligibility, closed/completed items, latest activity, blockers, warnings, and `next_safe_action`
- includes future routing metadata only as explicitly not implemented

Still absent by design:

- Reports v1
- runtime Agent/LLM routing
- Codex CLI execution
- local LLM execution
- real agent execution
- GitHub integration or mutation

Next skeleton focus:

- M49 should implement Reports v1.

## M47 Queue Item Closeout Workflow

Status: Completed locally on `main`.

Implemented runnable path:

- operator function: `close_local_queue_item(...)`
- Hub route: `POST /api/local-queue/items/{item_id}/closeout`
- Queue UI lifecycle form: `queue-lifecycle-closeout-form`

Behavior contract:

- validates that the queue item exists
- validates eligible status (`in_progress`)
- validates completion evidence exists
- validates required evidence fields: `evidence_summary`, `validation_results`, and `diff_check_result`
- requires explicit operator closeout summary
- transitions the item to existing `done` status
- records `closed_at`, `closed_by`, `closeout_summary`, and `closeout_history`
- preserves captured completion evidence
- returns stable JSON with `next_safe_action`

Non-execution contract:

- no prompt generation
- no prompt execution
- no Codex, local LLM, real agent, GitHub, push, workflow, or external action
- no Agent/LLM routing implementation

Next skeleton focus:

- M48 should implement Project Progress Rollup.

## M46 Completion Evidence Capture

Status: Completed locally on `main`.

Implemented runnable path:

- operator function: `capture_local_queue_completion_evidence(...)`
- Hub route: `POST /api/local-queue/items/{item_id}/evidence`
- Queue UI lifecycle form: `queue-lifecycle-evidence-form`

Behavior contract:

- validates that the queue item exists
- validates at least one meaningful evidence field
- writes a `completion_evidence` object to the existing file-backed queue item
- records `captured_at`
- preserves existing queue item fields and lifecycle status
- returns stable JSON with `next_safe_action` and advisory `closeout_eligible`

Evidence capture versus closeout:

- evidence capture prepares local evidence before closeout
- evidence capture does not complete, close out, execute, push, route, or invoke models
- final Queue Item Closeout Workflow remains future work

Still absent by design:

- runtime Agent/LLM routing
- Codex CLI execution
- local LLM execution
- real agent execution
- GitHub integration or mutation

Next skeleton focus:

- M47 should implement Queue Item Closeout Workflow.

## M45 Local Hub End-to-End Operator Workflow Validation

Status: Completed locally on `main`.

Validated runnable path:

- `GET /api/dashboard/summary`
- `GET /api/projects/active`
- `POST /api/local-queue/items`
- `GET /api/queue/{item_id}`
- `GET /api/local-queue/items/{item_id}/readiness`
- `POST /api/local-queue/prompt-pack`
- `GET /api/local-project-report`
- `GET /api/local-queue-agent-summary`

Behavior confirmed:

- operators can move from project/dashboard context to queue intake, detail review, readiness, prompt-pack generation, and local reports using existing Hub surfaces
- readiness inspection is advisory/read-only
- prompt-pack generation produces local copy/paste output and optional local artifact output
- prompt-pack generation does not auto-start, auto-complete, execute Codex, execute agents, execute local LLMs, or route models

Still absent by design:

- runtime Agent/LLM routing
- Codex CLI execution
- local LLM execution
- GitHub integration or mutation
- split queue storage

Next skeleton focus:

- M46 should focus on completion evidence capture for the local operator workflow.

## M44A Agent LLM Routing Strategy Documentation Update

Status: Completed locally on `main`.

Source of truth:

- `docs/architecture/AGENT_LLM_ROUTING_STRATEGY.md`

Current runnable behavior:

- M43 prompt packs generate local-only grouped prompt text/artifacts for manual operator use.
- The Hub does not execute Codex, agents, local LLMs, or routing decisions.
- No runtime routing metadata is added to the queue schema in M44A.

Future routing behavior:

- project-specific AI routing settings should select an agent lane, allowed engines/models, routing decision, and prompt-pack output before prompt generation
- future engines are `local_reasoning_llm`, `local_coding_llm`, and `codex_cli`
- future routed views should filter one canonical local queue by agent, engine, model, project policy, risk/complexity, and status

Skeleton boundary:

- this milestone adds documentation only
- no backend routes, frontend settings UI, queue schema changes, runtime routing, agent execution, Codex execution, or LLM/model invocation

## M43 Agent Prompt Pack Generator

Status: Completed locally on `main`.

Implementation mapping:

- operator generation logic:
  - `src/aresforge/operator/local_project_queue.py` (`generate_local_queue_prompt_pack`)
- Hub API/route wiring:
  - `src/aresforge/hub/api.py` (`post_local_queue_prompt_pack`)
  - `src/aresforge/hub/server.py` (`POST /api/local-queue/prompt-pack`)
- Queue UI contract:
  - `src/aresforge/hub/static/index.html`
  - `src/aresforge/hub/static/js/sections/queue.js`

Behavior contract:

- local-only prompt-pack text/artifact generation for queue items
- grouped copy/paste-ready prompts with sequence and explicit operating boundaries
- read-only/advisory result surface in Hub UI (no execution side effects)
- optional output artifact path with non-overwrite default unless `force` is provided

Safety contract:

- operator-gated, local-first, file-backed only
- no automatic Codex/agent/model execution
- no auto-start/auto-complete queue mutations
- no GitHub API, no `gh`, no GitHub mutation, no external service calls

## M42 Queue Item Detail Panel

Status: Completed locally on `main`.

Implementation mapping:

- Queue panel UI updates:
  - `src/aresforge/hub/static/index.html`
  - `src/aresforge/hub/static/js/sections/queue.js`
- API reuse (no new route):
  - `GET /api/queue/{item_id}`
  - `GET /api/local-queue/items/{item_id}/readiness`

Behavior contract:

- read-only/advisory queue item inspection
- detail panel renders core item fields plus M41 notes-derived metadata when present
- readiness context is displayed when available
- empty/error/readiness-unavailable states are explicit
- panel does not trigger lifecycle mutations automatically

## M41 Active Project Task Intake v2

Status: Completed locally on `main`.

Implementation mapping:

- intake API path unchanged:
  - `POST /api/local-queue/items` in `src/aresforge/hub/api.py` and `src/aresforge/hub/server.py`
- queue intake operator logic:
  - `src/aresforge/operator/local_project_queue.py`
- intake UI contract:
  - `src/aresforge/hub/static/index.html`
  - `src/aresforge/hub/static/js/sections/home.js`
  - `src/aresforge/hub/static/app.js`

Data contract notes:

- intake now supports optional `source`, `requested_outcome`, `acceptance_notes`, and `validation_notes`
- queue schema remains backward compatible
- additional structured intake details are persisted using existing queue item `source` and `notes`

Safety/behavior contract:

- creation-only intake flow
- no automatic status transitions
- no automatic prompt generation
- local-only and operator-gated
- no GitHub/agent/Codex/LLM execution behavior

## M40 Dashboard Milestone Closeout And Docs Reconciliation

Status: Completed locally on `main`.

Closeout intent:

- lock documentation to implemented dashboard behavior from M35-M39
- lock validation baseline for dashboard/operator contract checks
- avoid runtime changes

Implemented dashboard skeleton (M35-M39):

- operator summary contract: `src/aresforge/operator/local_dashboard_summary.py`
- Hub route wiring: `src/aresforge/hub/api.py` + `src/aresforge/hub/server.py` expose `GET /api/dashboard/summary`
- Home UI consumption and states:
  - `src/aresforge/hub/static/index.html`
  - `src/aresforge/hub/static/app.js`
  - `src/aresforge/hub/static/js/sections/home.js`
- related section modules used by deep links/drilldowns:
  - `src/aresforge/hub/static/js/sections/queue.js`
  - `src/aresforge/hub/static/js/sections/projects.js`
  - `src/aresforge/hub/static/js/sections/repos.js`
  - `src/aresforge/hub/static/js/sections/reports.js`

Behavior contract:

- manual refresh only
- explicit loading, empty, and error states
- deep links route only to existing local sections
- queue and advisory lane drilldowns are read-only/advisory

Operating boundaries:

- local-only, file-backed, operator-gated
- read-only/advisory dashboard posture
- no GitHub API, no `gh`, no GitHub mutations
- no real agent execution
- no Codex execution from Hub app
- no local/cloud model routing or invocation

Validation baseline:

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
## M36 Home Dashboard UI Consumption

Implemented:

- Home UI consumes `GET /api/dashboard/summary`
- renders read-only/advisory cards and status panels for project, queue, advisory agent lanes, repo status, blockers/warnings, and next safe action
- uses explicit manual refresh only (no polling/auto-refresh)

Boundaries preserved:

- local-only/read-only/advisory
- no GitHub/`gh` execution
- no agent/Codex/model execution
- no LLM/model routing

## M35 Hub Dashboard Summary Contract

Implemented contract:

- operator summary function: `src/aresforge/operator/local_dashboard_summary.py`
- Hub API route: `GET /api/dashboard/summary`
- payload: read-only local advisory metrics for Home dashboard consumption

Contract intent:

- provide backend/API data only
- avoid Home UI card/panel implementation in this milestone
- keep M35 local-only, file-backed, and non-mutating

Deferred scope:

- M36 consumes this contract for dashboard UI cards and status panels.

## M34 Frontend Modularization Closeout Skeleton

Frontend entrypoint contract:

- `src/aresforge/hub/static/index.html` loads `src/aresforge/hub/static/app.js` as `type="module"`.
- `src/aresforge/hub/static/app.js` remains the only browser entrypoint.

Frontend module topology:

- core:
  - `src/aresforge/hub/static/js/core/dom.js`
  - `src/aresforge/hub/static/js/core/http.js`
  - `src/aresforge/hub/static/js/core/state.js`
- sections:
  - `src/aresforge/hub/static/js/sections/home.js`
  - `src/aresforge/hub/static/js/sections/workspace.js`
  - `src/aresforge/hub/static/js/sections/queue.js`
  - `src/aresforge/hub/static/js/sections/projects.js`
  - `src/aresforge/hub/static/js/sections/repos.js`
  - `src/aresforge/hub/static/js/sections/reports.js`
  - `src/aresforge/hub/static/js/sections/orchestration.js`
  - `src/aresforge/hub/static/js/sections/escalation.js`
- project factory:
  - `src/aresforge/hub/static/js/sections/projectFactory/index.js`
  - `src/aresforge/hub/static/js/sections/projectFactory/scope.js`
  - `src/aresforge/hub/static/js/sections/projectFactory/architecture.js`
  - `src/aresforge/hub/static/js/sections/projectFactory/milestonePlan.js`
  - `src/aresforge/hub/static/js/sections/projectFactory/validation.js`
  - `src/aresforge/hub/static/js/sections/projectFactory/agentDispatch.js`
  - `src/aresforge/hub/static/js/sections/projectFactory/executionApproval.js`
  - `src/aresforge/hub/static/js/sections/projectFactory/closeout.js`

Validation/smoke baseline:

- `python -m pytest tests/test_hub_ui_foundation.py tests/test_hub_project_factory_api.py tests/test_hub_local_queue_lifecycle_api.py tests/test_hub_active_project_api.py tests/test_local_project_factory.py tests/test_local_active_project.py`
- `python -m aresforge inspect-local-queue-agent-summary`
- `python -m aresforge inspect-local-project-report`

Runtime boundaries:

- local-first and file-backed
- operator-gated flows
- no real agent execution
- no GitHub mutation
- no network execution beyond existing local Hub API behavior

## M17 Local Queue Execution-Prep Layer

Implemented local-only queue execution-prep additions now include:

- local queue item creation using active-project/default repo context
- local readiness inspection for one queue item
- gated local start for one queue item
- copy/paste-ready local Codex prompt generation
- local queue completion with validation evidence and commit metadata

CLI entry points:

- `python -m aresforge add-local-queue-item --title <title> ...`
- `python -m aresforge inspect-local-queue-item-readiness --item-id <item_id>`
- `python -m aresforge start-local-queue-item --item-id <item_id>`
- `python -m aresforge generate-local-queue-item-codex-prompt --item-id <item_id> [--output <path>]`
- `python -m aresforge complete-local-queue-item --item-id <item_id> --commit-hash <hash> --validation-summary <text> ...`

Execution boundaries remain unchanged:

- local-only and file-backed for this M17 layer
- no GitHub API calls
- no `gh` calls
- no GitHub mutation/sync execution
- no automatic Codex execution
- no agent execution
- no model routing/invocation
- human review stays responsible for running Codex and deciding when completion evidence is sufficient

## M23 Hub Frontend Modularization Foundation

Implemented frontend foundation changes now include:

- browser-native ES module loading for Hub static frontend entrypoint `src/aresforge/hub/static/app.js`
- extracted shared DOM primitives in `src/aresforge/hub/static/js/core/dom.js`
- extracted shared HTTP/payload primitives in `src/aresforge/hub/static/js/core/http.js`
- extracted the shared frontend state container in `src/aresforge/hub/static/js/core/state.js`
- consolidated workspace quick-action binding to a single binding path

Execution boundaries remain unchanged:

- local-only frontend/static refactor
- no GitHub API calls
- no `gh` calls
- no network-required execution path
- no automatic agent or model execution

## M24 Home And Workspace Section Modules

Implemented frontend modularization now also includes:

- `src/aresforge/hub/static/js/sections/home.js` for Home dashboard rendering/loading and Home-specific actions
- `src/aresforge/hub/static/js/sections/workspace.js` for Active Project Workspace rendering/loading and quick actions
- `src/aresforge/hub/static/app.js` retained as the browser entrypoint and cross-section orchestrator

Execution boundaries remain unchanged:

- local-only frontend/static refactor
- no GitHub API calls
- no `gh` calls
- no new network execution path
- no automatic agent or model execution

## M25 Queue Section Module

Implemented frontend modularization now also includes:

- `src/aresforge/hub/static/js/sections/queue.js` for Queue read-only summary rendering/loading, queue item card rendering, and queue-only actions
- `src/aresforge/hub/static/app.js` retained as the browser entrypoint and cross-section orchestrator
- local queue lifecycle forms and lifecycle-specific handlers remain in `app.js` for now

Execution boundaries remain unchanged:

- local-only frontend/static refactor
- no GitHub API calls
- no `gh` calls
- no new network execution path
- no automatic agent or model execution

## M26 Projects And Repos Section Modules

Implemented frontend modularization now also includes:

- `src/aresforge/hub/static/js/sections/projects.js` for Projects rendering, selector refresh, and Projects-specific actions
- `src/aresforge/hub/static/js/sections/repos.js` for Repos rendering, repo loading/inspection, and Repos-specific actions
- `src/aresforge/hub/static/app.js` retained as the browser entrypoint and cross-section orchestrator
- project-factory lifecycle orchestration remains in `app.js` for now

Execution boundaries remain unchanged:

- local-only frontend/static refactor
- no GitHub API calls
- no `gh` calls
- no new network execution path
- no automatic agent or model execution

## M27 Reports Section Module

Implemented frontend modularization now also includes:

- `src/aresforge/hub/static/js/sections/reports.js` for Reports rendering, report slice loading, export helpers, and Reports-specific actions
- `src/aresforge/hub/static/app.js` retained as the browser entrypoint and cross-section orchestrator
- non-Reports orchestration remains in `app.js` for now

Execution boundaries remain unchanged:

- local-only frontend/static refactor
- no GitHub API calls
- no `gh` calls
- no new network execution path
- no automatic agent or model execution

## M21 Active Project Workspace

Implemented polish and operator wiring:

- Hub Active Project Workspace UI updated for scanability, empty states, and operator-first actions.
- Quick actions annotated with "(local-only)" and bound in `src/aresforge/hub/static/app.js` to support refresh, continue-intake, open-queue, and select-project flows.
- New tests (`tests/test_active_project_workspace.py`) validate the `get_active_project_workspace` API behavior for empty and seeded scenarios.

Execution/operational guarantees:

- local-only, file-backed operator flows
- no automatic Codex/agent execution, no GitHub mutation or network calls


## M16 Hub Read-Only UI And API Wiring Layer

Implemented local-only Hub read/report additions include:

- local Home API wiring for dashboard/report/project readiness
- Home read-only dashboard section
- Projects read-only managed-projects section
- Queue read-only summary section
- Reports read-only local project report section

Key local endpoints now used by UI foundations:

- `GET /api/local-project-dashboard`
- `GET /api/local-project-report`
- `GET /api/local-projects`
- `GET /api/local-queue-agent-summary`

Execution boundaries remain:

- read-only/report-only surface for these M16 foundations
- no GitHub mutation/sync execution
- no agent execution
- no model routing/invocation

## M14 Local Read-Model/Report Layer

Implemented local-only inspection surfaces now include:

- project dashboard summary
- local project list and per-project readiness inspection
- queue and agent workload summary
- consolidated local project report summary

CLI entry points:

- `python -m aresforge inspect-local-project-dashboard`
- `python -m aresforge list-local-projects`
- `python -m aresforge inspect-local-project-readiness --project-id <id>`
- `python -m aresforge inspect-local-queue-agent-summary`
- `python -m aresforge inspect-local-project-report`

Execution boundaries remain unchanged:

- read-only/report-only for this M14 layer
- no GitHub API calls
- no `gh` calls
- no GitHub mutation
- no real agent execution
- no LLM routing/invocation

## M46 Project Factory Mapping

This runnable skeleton currently maps to a partial project-factory shell, not the full pipeline.

Built now (through M45):

- local-first Hub mission-control foundation
- managed project/repo registry
- active project selection/context
- active project intake into local queue
- project workbench and local control-plane views
- local planning artifacts for orchestration/escalation/handoff/closeout

Partial now:

- GitHub identity and sync planning boundaries exist, but explicit milestone/issue apply flow is not yet integrated into the Hub factory loop
- queue and agent metadata exist, but dispatch and run lifecycle are not yet executable

Missing for canonical pipeline completion:

- new project wizard
- repo create/link apply flow
- scope and architecture artifact contracts
- milestone/issue generation from accepted scope
- explicit GitHub milestone/issue apply boundary and execution path
- agent dispatcher and approved agent/model run lifecycle
- integrated validation, documentation update, and closeout automation loop

Canonical source-of-truth target state:

- `docs/architecture/PROJECT_FACTORY_WORKFLOW.md`

## Purpose

Describe the implemented human-triggered operator surface through M41 GitHub-linked project/repo identity management and local Hub workflows.

## Operator Shape

Command entrypoint:

- `python -m aresforge`

## M42 First-Run Bootstrap And Seed Wizard

- Added local bootstrap operator:
  - `src/aresforge/operator/local_bootstrap_wizard.py`
- Added local bootstrap CLI commands:
  - `python -m aresforge inspect-bootstrap-status [--repo-path <path>]`
  - `python -m aresforge plan-bootstrap [--repo-path <path>] [--format json|markdown] [--seed-sample-work]`
  - `python -m aresforge apply-bootstrap [--repo-path <path>] [--force] [--seed-sample-work] [--format json|markdown]`
- Added local Hub bootstrap endpoints:
  - `GET /api/bootstrap/status`
  - `GET /api/bootstrap/plan`
  - `POST /api/bootstrap/apply`
- Added Hub Bootstrap setup section for first-run initialization and seed workflows.

Bootstrap seeds:

- local state files under `.aresforge/` (state/projects/queue/agents)
- managed `aresforge` project and primary repo linkage
- local GitHub metadata fields for AresForge project/repo
- default agent profiles and handoff targets (M34 defaults)
- optional sample queue milestones for next work phase (`m43`-`m46`)

M42 local boundary:

- local-only, file-backed setup flow
- no GitHub API calls
- no `gh` calls
- no GraphQL/REST calls
- no network service calls
- no live GitHub discovery or validation
- no local/cloud/Codex/ChatGPT/Ollama model invocation

## M41 GitHub-Linked Project/Repo Model

- Managed project/repo registry now supports local GitHub identity metadata at both project and repo levels.
- Projects now carry `primary_repo_id` and local GitHub identity fields.
- Repos now carry local GitHub identity fields plus local git inspection fields.
- New local inspection command:
  - `python -m aresforge inspect-managed-repo-github-link --project-id <id> --repo-id <id> [--registry-path <path>] [--inspect-local-git] [--format json|markdown]`
- Updated local registration commands:
  - `python -m aresforge register-managed-project --project-id <id> --name <name> --root-path <path> [--github-url <url>] [--github-owner <owner>] [--github-repo <repo>] [--github-default-branch <branch>] [--primary-repo-id <repo_id>] ...`
  - `python -m aresforge register-managed-repo --project-id <id> --repo-id <id> --name <name> --path <path> [--github-url <url>] [--github-owner <owner>] [--github-repo <repo>] [--github-default-branch <branch>] [--inspect-local-git] ...`
- Hub API adds:
  - GitHub-link fields accepted by project/repo create endpoints
  - `GET /api/projects/{project_id}/repos/{repo_id}/github-link`
- Hub UI adds:
  - project/repo GitHub-link form fields
  - local git-link inspection action in Repos
  - GitHub linkage signals in Home/Reports/Settings

M41 local boundary:

- GitHub link metadata is local-only and file-backed
- local git inspection uses only local `git -C` commands
- no GitHub API calls
- no `gh` calls
- no GraphQL/REST calls
- no network service calls
- no live GitHub validation

## M31 Foundation Reconciliation

- AresForge now has a local-first foundation for self-managed operation.
- GitHub is optional/syncable and not mandatory for local planning.
- M26-M30 capabilities are established and reconciled as the baseline foundation:
  - M26 handoff package generation
  - M27 local project state ledger
  - M28 plan-only documentation reconciliation
  - M29 plan-only offline-to-GitHub sync planning
  - M30 local self-managed milestone lifecycle
- Foundation batch boundary confirmations:
  - no new GitHub API calls
  - no new LLM API calls
  - no mandatory network dependency for local planning

## M32 Managed Project Registry

- Added local managed-project registry under `.aresforge/projects/projects.json`.
- Supports multiple projects and repos with local metadata and deterministic inspect output.
- M33 queue registration reuses this registry for local `project_id`/`repo_id` validation when available.
- Local-only boundary:
  - no `gh`
  - no GitHub API calls
  - no network access

## M33 Local Project Queue

- Added local queue storage under `.aresforge/queue/work_items.json`.
- Queue tracks local work items without GitHub issues and supports cross-project/repo linking through `project_id` and `repo_id`.
- Commands:
  - `python -m aresforge init-project-queue [--path <path>] [--force]`
  - `python -m aresforge add-queue-item --item-id <id> --project-id <id> --repo-id <id> --title <title> [--queue-path <path>] [--registry-path <path>] [--description <text>] [--status <status>] [--priority <priority>] [--type <type>] [--tag <tag>]... [--depends-on <item_id>]... [--blocked-by <item_id>]... [--assigned-agent <agent_id>] [--source <source>] [--notes <text>]`
  - `python -m aresforge update-queue-item --item-id <id> [--queue-path <path>] [--project-id <id>] [--repo-id <id>] [--status <status>] [--priority <priority>] [--type <type>] [--title <title>] [--description <text>] [--tag <tag>]... [--depends-on <item_id>]... [--blocked-by <item_id>]... [--assigned-agent <agent_id>] [--source <source>] [--notes <text>]`
  - `python -m aresforge inspect-project-queue [--queue-path <path>] [--project-id <id>] [--repo-id <id>] [--status <status>] [--type <type>] [--assigned-agent <agent_id>] [--format json|markdown]`
  - `python -m aresforge inspect-queue-item --item-id <id> [--queue-path <path>] [--format json|markdown]`
- Queue supports dependency references with warning-only handling for future IDs.
- `assigned_agent` is stored for future orchestration and does not execute agents in M33.
- `assigned_agent` can reference an M34 local agent profile `agent_id`.
- Local-only boundary:
  - no `gh`
  - no GitHub API calls
  - no network access
  - no LLM calls

## M34 Local Agent Profiles And Handoff Targets

- Added local agent profile storage under `.aresforge/agents/agents.json`.
- Agent profile schema now stores `schema_version`, `updated_at`, `agents`, and `handoff_targets`.
- Commands:
  - `python -m aresforge init-agent-profiles [--path <path>] [--force] [--with-defaults]`
  - `python -m aresforge register-agent-profile --agent-id <id> --name <name> --role <role> [--profiles-path <path>] [--description <text>] [--execution-mode <mode>] [--model-preference <value>] [--strength <text>]... [--constraint <text>]... [--allowed-type <type>]... [--escalation-allowed true|false] [--handoff-target-id <id>] [--status <status>] [--tag <tag>]... [--notes <text>]`
  - `python -m aresforge register-handoff-target --target-id <id> --name <name> --target-type <type> [--profiles-path <path>] [--description <text>] [--local-command <command>] [--input-format <format>] [--output-format <format>] [--safety-note <text>]... [--status <status>] [--tag <tag>]... [--notes <text>]`
  - `python -m aresforge inspect-agent-profiles [--profiles-path <path>] [--role <role>] [--execution-mode <mode>] [--status <status>] [--format json|markdown]`
  - `python -m aresforge inspect-agent-profile --agent-id <id> [--profiles-path <path>] [--format json|markdown]`
  - `python -m aresforge inspect-handoff-target --target-id <id> [--profiles-path <path>] [--format json|markdown]`
- M26 handoff package includes local agent profile summary when profiles exist.
- Local-only boundary:
  - no `gh`
  - no GitHub API calls
  - no network access
  - no local LLM invocation
  - no cloud LLM invocation
  - handoff targets are descriptive/advisory only
  - no agent execution/orchestration is introduced yet

## M35 Local Multi-Agent Orchestration Planner

- Added local orchestration planner module under `src/aresforge/operator/local_agent_orchestration.py`.
- Added command:
  - `python -m aresforge plan-agent-orchestration [--project-id <id>] [--repo-id <id>] [--status <status>] [--queue-path <path>] [--profiles-path <path>] [--registry-path <path>] [--output <path>] [--format json|markdown] [--force]`
- Planner links:
  - M32 managed-project registry for project/repo context where available
  - M33 queue work items including `assigned_agent`, `dependencies`, and `blocked_by`
  - M34 agent profiles and handoff target references for assignment planning
- Planner output includes:
  - selected work items
  - available agents
  - recommended assignments
  - dependency order
  - blocked and unassigned item lists
  - handoff prompts
  - risk warnings and next actions
- Output behavior:
  - default stdout format: JSON
  - optional markdown format
  - optional file output with directory creation and overwrite protection (`--force`)
- Local-only boundary:
  - plan-only
  - no agent execution
  - no local LLM calls
  - no cloud LLM calls
  - no `gh`
  - no GitHub API calls
  - no network access

## M36 Local Escalation Planner

- Added local escalation planner module under `src/aresforge/operator/local_llm_escalation.py`.
- Added command:
  - `python -m aresforge plan-llm-escalation [--item-id <id>] [--project-id <id>] [--repo-id <id>] [--status <status>] [--queue-path <path>] [--profiles-path <path>] [--orchestration-plan <path>] [--output <path>] [--format json|markdown] [--force]`
- Planner links:
  - M33 queue work items
  - M34 agent profiles and handoff targets
  - optional M35 orchestration plan artifact when supplied
- Planner output includes:
  - per-item escalation classifications and reasons
  - classification buckets for local LLM, Codex, cloud advisory, human-required, and blocked/clarification
  - recommended handoff targets
  - copy/paste prompt guidance
  - risk warnings and next actions
- Output behavior:
  - default stdout format: JSON (stable/testable)
  - optional markdown format
  - optional file output with directory creation and overwrite protection (`--force`)
- Local-only boundary:
  - plan-only classification
  - no LLM invocation
  - no local LLM calls
  - no cloud LLM calls
  - no Codex execution
  - no ChatGPT calls
  - no `gh`
  - no GitHub API calls
  - no network access
  - cloud escalation guidance is advisory only

## M37 Hub UI Foundation

- Added local Hub package under `src/aresforge/hub/`.
- Added local command:
  - `python -m aresforge serve-hub [--host <host>] [--port <port>] [--open-browser]`
- Defaults:
  - `--host` defaults to `127.0.0.1`
  - `--port` defaults to `8765`
  - `--open-browser` defaults to disabled
- Hub serves:
  - local static frontend shell with persistent navigation
  - local API shell endpoints under `/api/`
  - `GET /api/health`
  - `GET /api/summary`
  - `GET /api/docs/status`
- M37 intentionally provides foundation scope only:
  - Home summary and Settings boundary confirmations
  - placeholder sections for Projects/Repos/Queue/Agents/Handoff/Orchestration/Escalation/Reports
  - full project/repo/queue management deferred to M38
  - full agent/orchestration/escalation/handoff screens deferred to M39
  - M40 reporting/dashboard/operator workflows are now implemented
- Local-only boundary:
  - local-first serving path
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
  - no authentication implementation yet
  - no production deployment implementation yet
  - no agent execution yet
  - no live GitHub sync yet

## M38 Hub Project, Repo, And Queue Management

- Extended Hub API endpoints:
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
- Hub UI now supports local interactive management for:
  - Projects (list + add/update)
  - Repos (project-scoped list + add/update)
  - Queue (filter + add/update + quick status transitions)
- M38 data path:
  - project/repo operations use M32 managed-project registry file-backed storage
  - queue operations use M33 local queue file-backed storage
- Home/Settings updates:
  - Home includes management readiness hints
  - Settings shows local registry/queue file paths and local-only boundaries
- Local-only boundary:
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
- Deferred scope remains:
  - follow-on scope: richer guided workflows, optional execution gates, authentication hardening, and controlled sync execution

## M39 Hub Agent, Handoff, Orchestration, And Escalation Screens

- Extended Hub API endpoints:
  - `GET /api/agents`
  - `POST /api/agents`
  - `GET /api/agents/{agent_id}`
  - `GET /api/handoff-targets`
  - `POST /api/handoff-targets`
  - `GET /api/handoff-targets/{target_id}`
  - `GET /api/handoff/preview`
  - `GET /api/orchestration/plan`
  - `POST /api/orchestration/plan`
  - `GET /api/escalation/plan`
  - `POST /api/escalation/plan`
- Hub UI now supports local interactive workflows for:
  - Agent profile list and add/update management
  - Handoff target list and add/update management
  - Handoff preview generation and refresh
  - Orchestration plan generation/viewing with filters
  - Escalation plan generation/viewing with filters
- M39 data path:
  - agent/handoff operations use M34 local profile storage
  - orchestration operations use M35 local plan-only logic
  - escalation operations use M36 local plan-only logic
  - handoff preview uses M26 local handoff logic without posting externally
- Local-only boundary:
  - file-backed local-first workflows
  - orchestration and escalation are plan-only
  - no agent execution
  - no local LLM invocation
  - no cloud LLM invocation
  - no Codex execution
  - no ChatGPT calls
  - no Ollama calls
  - no `gh`
  - no GitHub API calls
  - no network service calls
  - no external API calls
  - no authentication implementation yet
  - no production deployment implementation yet
  - no live GitHub sync yet
- Deferred scope remains:
  - follow-on scope: richer guided workflows, optional execution gates, authentication hardening, and controlled sync execution

## M40 Hub Reporting, Dashboard, And Operator Workflows

- Extended Hub API report endpoints:
  - `GET /api/reports/dashboard`
  - `GET /api/reports/action-center`
  - `GET /api/reports/readiness`
  - `GET /api/reports/operator-workflows`
  - `GET /api/reports/export`
- Hub Home now provides:
  - top-level status cards for projects/repos/queue/agents/orchestration/escalation/docs/overall readiness
  - readiness indicators and action-center preview
  - recommended next actions and quick workflow cards
- Hub Reports now provides:
  - local control-plane summaries for projects/repos/queue/agents/orchestration/escalation/docs/readiness
  - action-center and operator-workflow sections
  - local in-page report export/copy actions
- Hub Settings now provides:
  - default local state file paths
  - default artifact folders for handoff/orchestration/escalation/dashboard
  - boundary confirmations, known limitations, and next milestone scope
- Local-only boundary:
  - report-only and plan-only guidance surfaces
  - no agent execution
  - no local/cloud/Codex/ChatGPT/Ollama invocation
  - no GitHub/gh/network/external API calls
  - no live GitHub sync execution
  - authentication and production deployment remain unimplemented

## Current Additions (M25 Included)

- `inspect-evidence-bundle-automation-contract`
- `generate-child-closeout-evidence-bundle`
- `generate-parent-closeout-evidence-bundle`
- `generate-pr-evidence-bundle`
- `simulate-evidence-bundle-generation`

- `inspect-self-managed-milestone-execution-contract`
- `simulate-self-managed-milestone-execution`
- `run-sequential-child-closeout-flow`
- `generate-sequential-closeout-execution-package`
- `generate-self-managed-milestone-handoff`
- `inspect-milestone-state`
- `inspect-milestone-dashboard`
- `plan-milestone-execution-queue`
- `check-issue-evidence-readiness`
- `check-milestone-evidence-readiness`
- `inspect-parent-closeout-readiness`

- `inspect-milestone-closeout-preflight-contract`
- `inspect-parent-child-linkage-preflight`
- `inspect-child-evidence-marker-preflight`
- `inspect-pr-mapping-preflight`
- `generate-closeout-preflight-repair-guidance`
- `inspect-milestone-closeout-preflight`

- `inspect-canonical-evidence-marker-contract`
- `generate-child-evidence-marker-template`
- `generate-pr-evidence-marker-template`
- `generate-parent-closeout-marker-template`
- `generate-preflight-baseline-snapshot`
- `diff-preflight-snapshots`

- `inspect-automatic-canonical-evidence-emission-contract`
- `check-closeout-readiness-by-construction`
- `generate-handoff-package`
- `init-project-state`
- `inspect-project-state`
- `update-project-state`
- `append-operation-log`
- `inspect-operation-log`
- `plan-doc-reconciliation`
- `plan-github-sync`
- `generate-local-milestone-template`
- `inspect-local-milestone`
- `check-local-milestone-readiness`
- `generate-local-milestone-closeout`
- `init-managed-project-registry`
- `register-managed-project`
- `register-managed-repo`
- `inspect-managed-project-registry`
- `inspect-managed-project`
- `inspect-managed-repo`
- `init-agent-profiles`
- `register-agent-profile`
- `register-handoff-target`
- `inspect-agent-profiles`
- `inspect-agent-profile`
- `inspect-handoff-target`
- offline/local state-file mode supported for milestone/parent readiness and parent evidence generation commands via `--state-file <path>`
- canonical marker completeness payloads in:
  - child closeout evidence bundle generation
  - PR evidence bundle generation
  - parent closeout evidence bundle generation
  - closeout comment template generation

Offline state-file command surface:

- `python -m aresforge inspect-milestone-state --parent-issue <n> --state-file <path>`
- `python -m aresforge check-milestone-evidence-readiness --parent-issue <n> --state-file <path>`
- `python -m aresforge inspect-parent-closeout-readiness --parent-issue <n> --state-file <path>`
- `python -m aresforge generate-parent-closeout-evidence-bundle --parent-issue <n> --state-file <path>`
- `python -m aresforge check-closeout-readiness-by-construction --parent-issue <n> --state-file <path>`
- This local/offline path avoids `gh` and GitHub API calls when `--state-file` is provided.
- Reference fixture: `tests/fixtures/offline_state/parent_closeout_ready.json`.
- Implemented/pushed through commit `40de9fe`; preferred during GitHub GraphQL/API rate-limit windows.

## M26 Local Handoff Package Surface

- Command: `python -m aresforge generate-handoff-package --output <path> [--format markdown|json] [--include-doc-excerpts] [--force]`
- Local-only continuity artifact for:
  - human session handoff
  - Codex session continuation
  - local LLM agent continuation
  - future project agent continuation
- Reads local source-of-truth docs and local git state only.
- Approved local git command set:
  - `git branch --show-current`
  - `git rev-parse HEAD`
  - `git status --short`
  - `git log -n 10 --oneline`
- No `gh`, no GitHub API calls, no network dependency.
- Includes local project-state summary from `.aresforge/state/project_state.json` when available.
- Emits a warning and still succeeds when local project-state file is missing.
- Includes managed-project registry summary from `.aresforge/projects/projects.json` when available.
- Includes local project queue summary from `.aresforge/queue/work_items.json` when available.
- Includes local agent profiles summary from `.aresforge/agents/agents.json` when available.
- Includes latest orchestration artifact summary from `artifacts/orchestration/` when available, or an orchestration capability note when none exists.

## M27 Local Project State Ledger Surface

- Ledger defaults:
  - `.aresforge/state/project_state.json`
  - `.aresforge/state/operation_log.jsonl`
- Commands:
  - `python -m aresforge init-project-state [--path <path>] [--force]`
  - `python -m aresforge inspect-project-state [--path <path>]`
  - `python -m aresforge update-project-state [--path <path>] [--current-milestone <value>] [--current-phase <value>] [--current-mode <value>] [--validation-status <value>] [--documentation-status <value>] [--warning <text>]...`
  - `python -m aresforge append-operation-log [--state-path <path>] --event-type <type> --summary <summary> [--details <json>]`
  - `python -m aresforge inspect-operation-log [--state-path <path>] [--limit <n>]`
- Local-only boundary: no `gh`, no GitHub API calls, no network dependency.
- Scope boundary: M27 project state is per current repo/session context; M32 registry tracks many projects/repos; M33 queue tracks local work progression.

## M28 Documentation Reconciliation Surface

- Command: `python -m aresforge plan-doc-reconciliation [--output <path>] [--format json|markdown] [--include-git-state] [--force]`
- Planner scope:
  - source-of-truth docs in `docs/context`, `docs/roadmap`, `docs/architecture`, and `docs/operator`
  - local project state at `.aresforge/state/project_state.json` when present
  - optional local git state via approved command set only
- Output:
  - stable JSON for tests/automation
  - human-readable markdown for operator review
- Boundary:
  - plan-only (no automatic doc editing)
  - local-only
  - no `gh`, no GitHub APIs, no LLM calls, no external network use

## M29 Offline-to-GitHub Sync Planning Surface

- Command: `python -m aresforge plan-github-sync [--state-file <path>] [--project-state <path>] [--output <path>] [--format json|markdown] [--force]`
- Planner scope:
  - optional offline closeout state file
  - optional/default local project state file at `.aresforge/state/project_state.json`
  - local source-of-truth docs for context traceability
- Output:
  - stable JSON for automation/tests
  - human-readable markdown for operator review
- Boundary:
  - plan-only (no posting comments, no closing issues, no PR creation)
  - local-only
  - no `gh`, no GitHub APIs, no network access
- no mutation

## M30 Local Milestone Lifecycle Surface

- Commands:
  - `python -m aresforge generate-local-milestone-template --milestone-id <id> --output <path> [--title <title>] [--force]`
  - `python -m aresforge inspect-local-milestone --definition <path> [--format json|markdown]`
  - `python -m aresforge check-local-milestone-readiness --definition <path> [--project-state <path>] [--format json|markdown]`
  - `python -m aresforge generate-local-milestone-closeout --definition <path> --output <path> [--format json|markdown] [--force]`
- Suggested local definition path: `.aresforge/milestones/`.
- Lifecycle links:
  - M27 project-state ledger for active milestone/phase and documentation status checks.
  - M28 `plan-doc-reconciliation` as a required lifecycle closeout follow-up.
  - M26 `generate-handoff-package` reminder as a closeout continuity step.
  - M29 `plan-github-sync` as an optional future sync planning step.
  - Later milestones can be associated with M32 managed `project_id` / `repo_id`.
- Boundary:
  - local-only
  - plan/check/generate only
  - no `gh`, no GitHub APIs, no network, no LLM calls

## M25 Capability Contract Alignment

- Contract authority: `docs/architecture/AUTOMATIC_CANONICAL_EVIDENCE_EMISSION_CONTRACT.md`.
- Canonical marker emission now occurs by default across child, PR, parent, and closeout-comment evidence domains.
- Readiness-by-construction inspects emitted marker completeness plus milestone execution readiness in a read-only command path.
- Missing marker completeness or post-hoc-repair-required signals block readiness-by-construction deterministically.
- Parent closeout remains human-gated and separate from marker/readiness command execution.

## M24 Capability Contract Alignment

- Contract authority: `docs/architecture/CANONICAL_EVIDENCE_MARKER_CONTRACT.md`.
- Canonical marker templates are deterministic and read-only by default.
- Snapshot generation and diff classification are read-only and audit-focused.
- Canonical markers are integrated into child/PR/parent evidence bundle outputs.
- Preflight parsing prefers canonical markers and preserves backward-compatible fallback parsing.
- Parent closeout remains readiness-gated and separate from marker/snapshot command execution.

## M23 Capability Contract Alignment

- Contract authority: `docs/architecture/MILESTONE_CLOSEOUT_PREFLIGHT_CONTRACT.md`.
- Parent-child lineage detection, child evidence markers, and PR mapping checks are read-only by default.
- Repair guidance output is copy/paste-safe text only and does not execute mutation.
- Orchestration command (`inspect-milestone-closeout-preflight`) provides one deterministic readiness report.
- Parent closeout remains readiness-gated and separate from preflight command execution.

## M22 Capability Contract Alignment

- Contract authority: `docs/architecture/EVIDENCE_BUNDLE_AUTOMATION_CONTRACT.md`.
- Evidence bundle generation paths are read-only by default.
- Validation summaries are normalized for deterministic evidence rendering.
- Simulation path provides fixture-friendly blocked/ready planning outputs with no mutation.
- Parent closeout remains readiness-gated and separate from generation commands.

## M21 Capability Contract Alignment

- Contract authority: `docs/architecture/M21_SELF_MANAGED_EXECUTION_CONTRACT.md`.
- Parent-driven sequential child execution with final reconciliation last.
- Read-only simulation available before mutation execution.
- Targeted closeout flow accepts a single child issue only.
- Parent closeout remains readiness-gated and separate from child closeout flow.

## Automation Boundary

- human-triggered only
- read-only-safe defaults
- explicit operator approval required for execute-mode mutation
- no bulk mutation path
- no automatic PR merge
- no background jobs, polling loops, or schedulers
- parent issue remains open until children are closed/accounted and parent readiness checks pass

## Current Foundation Validation Bundle (Local-Only)

- `git diff --check`
- `python -m pytest`
- `python -m aresforge init-project-state --force`
- `python -m aresforge inspect-project-state`
- `python -m aresforge generate-handoff-package --output artifacts/handoff/final-handoff.md --force`
- `python -m aresforge plan-doc-reconciliation --output artifacts/doc-reconciliation/final-plan.json --force`
- `python -m aresforge plan-github-sync --output artifacts/github-sync/final-sync-plan.json --force`
- `python -m aresforge generate-local-milestone-template --milestone-id m31-final-validation --title "M31 Final Validation" --output artifacts/milestones/m31-final-validation.json --force`
- `python -m aresforge inspect-local-milestone --definition artifacts/milestones/m31-final-validation.json --format markdown`
- `python -m aresforge check-local-milestone-readiness --definition artifacts/milestones/m31-final-validation.json --format markdown`
- `python -m aresforge generate-local-milestone-closeout --definition artifacts/milestones/m31-final-validation.json --output artifacts/milestones/m31-closeout.md --format markdown --force`

## Known Limitations

- No production-ready LLM dispatch exists; only the M62 explicit local LLM prototype may call a local provider under operator gates.
- No cloud LLM API integration yet.
- No GitHub sync execution yet.
- Hub provides the local web UI; auth/deployment hardening and execution gates remain future work.
- No cross-machine coordination yet.
- No background daemon/scheduler yet.

## Next-Phase Roadmap (Planned)

1. Local LLM agent handoff profiles.
2. Multi-agent orchestration planning.
3. Escalation to cloud LLMs.
4. Project dashboard and local project management reporting.
5. Optional later GitHub sync execution.
6. Optional later web dashboard UI.
7. Optional later background daemon or scheduler.
