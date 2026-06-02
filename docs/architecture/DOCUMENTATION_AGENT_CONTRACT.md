# Documentation Agent Contract

## M161 Codex Loop Validation Evidence Bundle Boundary

M161 does not add documentation-agent or source-code patch mutation. It may write local evidence bundle artifacts and classify a supplied source patch as review metadata, but it does not edit documentation through a documentation agent, generate documentation patches, apply patches, call local LLMs, call live Codex, call GitHub/`gh`, push, merge, mutate queue state, retry failures, resume orchestration, or start follow-on work.

Documentation mutation remains limited to separate docs-only Markdown patch commands that pass `docs_only_patch_apply` gates. Source patch classification inside an M161 bundle is evidence only and cannot authorize patch application.

## M160 Low-Risk Codex Execution Pilot Item Boundary

M160 does not add documentation-agent or source-code patch mutation. It may create local pilot, preflight, dispatch, ingestion, and validation artifacts, but it does not edit documentation through a documentation agent, generate documentation patches, apply patches, call local LLMs, call GitHub/`gh`, push, merge, mutate queue state, retry failures, resume orchestration, or start follow-on work.

Documentation mutation remains limited to separate docs-only Markdown patch commands that pass `docs_only_patch_apply` gates. Source/code changes from any explicit low-risk Codex pilot remain local evidence and must not be applied through AresForge patch automation from M160 output.

## M159 Real Codex Execution Preflight Hardening Boundary

M159 preflight does not add documentation-agent or source-code mutation. It may report validation and source patch policy metadata for future Codex output, but it does not edit documentation, generate patches, apply patches, execute documentation agents, call models, call Codex, call GitHub/`gh`, mutate queue state, run validation commands, retry failures, resume orchestration, or start follow-on work.

Documentation mutation remains limited to separate docs-only Markdown patch commands that pass `docs_only_patch_apply` gates. Source patch application remains default-deny and outside M159.

## M158 Operator Autonomy Configuration Profile Boundary

M158 autonomy profile inspection does not add documentation-agent mutation. Profiles may mark docs-only patch application or documentation-adjacent local planning as enabled, dry-run-only, or blocked, but those labels are inspectable policy metadata only. Documentation mutation remains limited to separate docs-only Markdown patch commands that pass `docs_only_patch_apply` gates.

The `inspect-autonomy-profile` command does not edit documentation, generate patches, apply patches, execute documentation agents, call models, call Codex, call GitHub/`gh`, mutate queue state, run validation commands, retry failures, resume orchestration, or start follow-on work.

## M157 Run Replay and Audit Trail Boundary

M157 replay/audit inspection does not add documentation-agent mutation. It may read artifacts that mention documentation-agent steps or documentation evidence, but it does not edit documentation, generate patches, apply patches, execute documentation agents, call models, call Codex, call GitHub/`gh`, mutate queue state, run validation commands, delete artifacts, retry failures, resume orchestration, or start follow-on work.

Documentation mutation remains limited to separate docs-only Markdown patch commands that pass `docs_only_patch_apply` gates. M157 output is reconstructed audit evidence only.

## M156 Orchestration Artifact Retention Policy Boundary

M156 artifact retention inspection does not add documentation-agent mutation. It may index documentation-agent evidence folders and report stale or orphan-like local artifacts, but it does not edit documentation, generate patches, apply patches, execute documentation agents, call models, call Codex, call GitHub/`gh`, mutate queue state, run validation commands, delete artifacts, retry failures, resume orchestration, or start follow-on work.

Documentation mutation remains limited to separate docs-only Markdown patch commands that pass `docs_only_patch_apply` gates. M156 output is retention and cleanup-planning evidence only.

## M155 Durable Orchestration Run Store Boundary

M155 durable run-store work does not add documentation-agent mutation. It may persist and inspect orchestration run metadata, including runs that reference documentation-agent steps, but it does not edit documentation, generate patches, apply patches, execute documentation agents, call models, call Codex, call GitHub/`gh`, mutate queue state, run validation commands, retry failures, resume orchestration, or start follow-on work.

Documentation mutation remains limited to separate docs-only Markdown patch commands that pass `docs_only_patch_apply` gates. M155 output is durable local history evidence only.

## M154 Sprint Closeout and Autonomy Readiness Report Boundary

M154 readiness reporting does not add documentation-agent mutation. It synchronizes source-of-truth documentation context for the M140-M154 closeout and can report documentation consistency, but it does not execute documentation agents, generate documentation patches, apply patches, call models, call Codex, call GitHub/`gh`, mutate queue state, run validation commands, retry failures, resume orchestration, or start follow-on work.

Documentation mutation remains limited to separate docs-only Markdown patch commands that pass `docs_only_patch_apply` gates. M154 output is closeout and readiness evidence only.

## M153 Hub Orchestration Run Monitor Boundary

M153 orchestration run monitoring does not add documentation-agent mutation. It may read run history, step results, and artifacts involving documentation agents, but it does not edit documentation, generate patches, apply patches, execute documentation agents, call models, call Codex, call GitHub/`gh`, mutate queue state, run validation commands, retry failures, resume orchestration, or start follow-on work.

Documentation mutation remains limited to separate docs-only Markdown patch commands that pass `docs_only_patch_apply` gates. M153 output is local status and recovery evidence only.

## M152 End-to-End Codex Loop Real Run Boundary

M152 real low-risk Codex loop execution does not add documentation-agent mutation. It may create local Codex loop artifacts, dispatch records, ingestion evidence, validation output, and completion recommendations, but it does not edit documentation through a documentation agent, generate documentation patches, apply patches, call local LLMs, call GitHub/`gh`, push, merge, mutate queue state, retry failures, or start follow-on work.

Documentation mutation remains limited to separate docs-only Markdown patch commands that pass `docs_only_patch_apply` gates. Source/code changes from a Codex run remain bounded by M152 low-risk scope and must be validated before any separate completion action.

## M151 End-to-End Codex Loop Dry Run Boundary

M151 end-to-end Codex loop dry-run does not add documentation-agent or source-code mutation. It may create local dry-run loop artifacts and M136 evidence/recommendation records, but it does not edit documentation, generate patches, apply patches, execute documentation agents, call models, call real Codex, call GitHub/`gh`, mutate queue state, run validation commands, retry failures, or start follow-on work.

Documentation mutation remains limited to separate docs-only Markdown patch commands that pass `docs_only_patch_apply` gates. Source/code patch application remains blocked unless a later explicit milestone defines and validates a safe apply boundary.

## M150 Source Patch Apply Dry Run Boundary

M150 source patch apply dry-run does not add documentation-agent or source-code mutation. It may dry-run documentation, source, and test patch applicability with `git apply --check` after M149 planning and machine gates pass, but it does not edit documentation, mutate source, generate patches, apply patches, execute documentation agents, call models, call Codex, call GitHub/`gh`, mutate queue state, run validation commands, retry failures, or start follow-on work.

Documentation mutation remains limited to separate docs-only Markdown patch commands that pass `docs_only_patch_apply` gates. Source/code patch application remains blocked unless a later explicit milestone defines and validates a safe apply boundary.

## M149 Controlled Source Patch Apply Plan Boundary

M149 source patch apply planning does not add documentation-agent or source-code mutation. It may plan around documentation, source, test, workflow, protected config, queue-state, binary, executable-mode, and outside-repo patch targets, but it does not edit documentation, mutate source, generate patches, apply patches, execute documentation agents, call models, call Codex, call GitHub/`gh`, mutate queue state, run validation commands, retry failures, or start follow-on work.

Documentation mutation remains limited to separate docs-only Markdown patch commands that pass `docs_only_patch_apply` gates. Source/code patch application remains blocked unless a later explicit milestone defines and validates a safe apply boundary.

## M148 Source Patch Risk Classifier Boundary

M148 source patch classification does not add documentation-agent or source-code mutation. It may classify documentation, source, test, workflow, protected config, queue-state, binary, executable-mode, and outside-repo patch targets, but it does not edit documentation, mutate source, generate patches, apply patches, execute documentation agents, call models, call Codex, call GitHub/`gh`, mutate queue state, run validation commands, retry failures, or start follow-on work.

Documentation mutation remains limited to separate docs-only Markdown patch commands that pass `docs_only_patch_apply` gates. Source/code patch application remains blocked unless a later explicit milestone defines and validates a safe apply boundary.

## M147 Orchestrator Resume-from-Failure Boundary

M147 resume-plan inspection does not add documentation-agent mutation. It may inspect a source orchestration run involving documentation steps or docs-only patch boundaries, but it does not edit documentation, generate patches, apply patches, execute documentation agents, call models, call Codex, call GitHub/`gh`, mutate queue state, run validation commands, retry failures, resume orchestration, or start follow-on work.

Documentation mutation remains limited to separate docs-only Markdown patch commands that pass `docs_only_patch_apply` gates. M147 output is checkpoint and resume-planning evidence only.

## M146 Agent Step Result Normalization Boundary

M146 step result normalization does not add documentation-agent mutation. It may normalize a source step result from a documentation agent or docs-only patch boundary, but it does not edit documentation, generate patches, apply patches, execute documentation agents, call models, call Codex, call GitHub/`gh`, mutate queue state, run validation commands, retry failures, or start follow-on work.

Documentation mutation remains limited to separate docs-only Markdown patch commands that pass `docs_only_patch_apply` gates. M146 output is schema-normalized evidence only.

## M145 Codex Failure Classification Boundary

M145 failure classification does not add documentation-agent mutation. It may classify a failure involving documentation output or validation evidence, but it does not edit documentation, generate patches, apply patches, execute documentation agents, call models, call Codex, call GitHub/`gh`, mutate queue state, run validation commands, retry failures, or start follow-on work.

Documentation mutation remains limited to separate docs-only Markdown patch commands that pass `docs_only_patch_apply` gates. Codex failure policy output is recovery guidance only.

## M144 Codex Validation Profile Boundary

M144 validation profile inspection does not add documentation-agent mutation. It may classify documentation paths and recommend the `docs_only` validation profile for low-risk docs-only Codex output, but it does not edit documentation, generate patches, apply patches, execute documentation agents, call models, call Codex, call GitHub/`gh`, mutate queue state, run validation commands, or start follow-on work.

Documentation mutation remains limited to separate docs-only Markdown patch commands that pass `docs_only_patch_apply` gates. Codex-generated documentation changes still require downstream validation evidence before completion.

## M143 Codex Worktree Guard Boundary

M143 Codex sandbox/worktree guard inspection does not add documentation-agent mutation. The guard may report documentation or queue files in dirty-tree evidence, but it does not apply documentation changes, generate or apply patches, execute documentation agents, call models, call Codex, call GitHub/`gh`, mutate queue state, run validation commands, or start follow-on work.

Documentation mutation remains limited to separate docs-only Markdown patch commands that pass `docs_only_patch_apply` gates. Source-code patches or Codex-generated patch application remain outside the M143 boundary.

## M142 Codex Enablement Boundary

M142 real Codex execution enablement profiles do not add documentation-agent mutation. The profile inspector may document that Codex-generated work must be validated before completion, but it does not apply documentation changes, generate or apply patches, execute documentation agents, call models, call GitHub/`gh`, mutate queue state, or start follow-on work.

Documentation mutation remains limited to separate docs-only Markdown patch commands that pass `docs_only_patch_apply` gates. Source-code patches or Codex-generated patch application remain outside the M142 boundary.

## M141 Orchestration History Boundary

M141 can report documentation-agent orchestration runs and recovery records from local history. Those records are inspection evidence only. They do not apply documentation changes, retry documentation steps, resume runs, mutate queue state, call Codex, call GitHub/`gh`, invoke models, or start follow-on work.

Documentation mutation remains limited to separate docs-only Markdown patch commands that pass `docs_only_patch_apply` gates.

## M140 Orchestrator Execution State Machine

M140 records documentation-agent orchestration as a state-machine boundary. Documentation steps may be planned, checkpointed, and validated, but documentation mutation remains limited to separate docs-only patch commands that pass `docs_only_patch_apply` gates.

The M140 inspector does not execute a documentation agent, call models, apply generated documentation changes, call Codex, call GitHub/`gh`, mutate queue state, or start follow-on work. It reports `patch_application_performed=false` and treats docs-only patch application as an explicit validation boundary for later gated commands.

## M139 Autonomous Sprint Closeout

M139 reconciles documentation-agent behavior after the completed M125-M139 agent foundation sprint. The sprint span is M125, M126, M127, M128, M129, M130, M131, M132, M133, M134, M135, M136, M137, M138, and M139.

Current documentation-agent posture:

- M125 defines the runtime boundary that documentation agents must obey.
- M126 registers `documentation-agent` as a declarative source-doc planning/review agent.
- M128 can place documentation steps in a plan without executing them.
- M129 can dry-run deterministic documentation-related planning.
- M131 provides the `docs_only_patch_apply` machine gate.
- M133 permits autonomous application only for docs-only Markdown patches that pass gates, clean apply checks, path allowlists, dirty-target protection, and transaction logging.
- M139 records this as the first documentation-agent path where machine gates can replace human review for a narrow docs-only patch.

Still blocked: model-generated documentation mutation without a docs-only patch boundary, source-code patch application, test/config/workflow changes, Codex execution from documentation-agent flows, local or remote LLM execution from documentation-agent flows, GitHub/`gh`, queue completion, PR merge, and automatic next-item execution.

## M133 Docs-Only Autonomous Apply

M133 creates the first documentation-agent apply path, but only for docs-only Markdown patches that pass deterministic machine gates. The supported command is:

    python -m aresforge apply-docs-only-patch --item-id <item_id> --patch-path <patch_path> --format json

Allowed targets are Markdown documentation files under `docs/`, including the source-of-truth context, roadmap, operator, and architecture documents. Blocked targets include `src/`, `tests/`, package/config files, scripts, `.github` workflows, `.aresforge` queue files, binary files, non-doc files, and executable or file-mode changes.

The apply path requires `docs_only_patch_apply` machine gates, path allowlist checks, clean apply checks, dirty-target protection, post-apply diff checks, Markdown consistency checks, and transaction logging. It does not execute a model-backed documentation agent, Codex, local LLMs, remote LLMs, GitHub, `gh`, network workflows, validation commands, queue completion, or next-item execution.

## M124 Sprint Closeout Note

M124 closes the M110-M124 controlled automation sprint without adding documentation-agent execution. M116 can generate documentation patch proposal artifacts and M111 can record approved patch proposal intake metadata, but generated documentation proposals remain human-review-only and are not applied automatically.

Documentation-agent apply mode, model-generated documentation mutation, patch application, queue completion, GitHub/`gh`, network workflows, and automatic next-item execution remain blocked until a later explicit operator-approved milestone defines and validates that boundary.

## M118 Post-Automation Planning Reconciliation

M118 reconciles documentation-agent-related source-of-truth after M110-M117. It records that M116 can generate documentation patch proposal artifacts for review and that M111 can intake approved patch proposals as metadata, but no generated documentation patch is applied automatically.

M118 does not execute a documentation-agent runtime, does not call models, does not mutate documentation from generated output, does not call GitHub/`gh`, does not make network calls, does not apply patches, does not complete queue items, and does not start follow-on work. Any future documentation-agent apply path must remain a separate explicit milestone with operator approval, validation evidence, and a patch application boundary.

## M116 Patch Proposal Generator

M116 adds a local-only documentation-agent patch proposal generator. It reads the local queue item and selected source-of-truth documentation, detects missing milestone/item/command coverage, and writes a structured `documentation_agent_patch_proposal` artifact plus a local proposed patch text file for operator review.

M116 proposal generation does not execute a documentation-agent runtime, does not call models, does not apply generated patches, does not mutate source docs from the proposal, does not call GitHub/`gh`, does not make network calls, does not mutate queue status, and does not complete work automatically. Generated proposals require human review and a later approval gate before any M111 patch intake.

## M111 Patch Intake Boundary

M111 defines the local-only approval-gated intake boundary for patch proposals that may come from Codex, local LLM, or documentation-agent proposal workflows. Documentation-agent output may be recorded as a patch proposal only after a local approval gate exists and is `approved_for_manual_handoff`. The intake command records review metadata and patch summary data only; it does not apply documentation changes, mutate repository files, execute a documentation agent, call local LLMs, execute Codex, call GitHub/`gh`, make network calls, mutate queue state, or complete work automatically.

## M125 Agent Runtime Boundary

M125 defines the general Agent Runtime Boundary Contract that future documentation-agent runtimes must satisfy before any execution or apply path can exist. The boundary requires declared `agent_id`, `agent_type`, `execution_mode`, `input_contract`, `output_contract`, `allowed_capabilities`, `forbidden_capabilities`, `mutation_scope`, `network_scope`, `model_scope`, `timeout_policy`, `retry_policy`, `evidence_requirements`, `safety_class`, and `autonomy_level`.

For documentation-agent work, M125 preserves the existing documentation contract boundaries: no documentation-agent execution, no automatic documentation mutation, no model-generated apply mode, no GitHub API/`gh`, no network services, no patch application, no queue completion, and no automatic next-item execution. Future documentation-agent patch proposal or apply milestones must enforce both this M125 runtime boundary and the documentation-agent-specific contract.

## M126 Agent Registry

M126 registers `documentation-agent` as a declarative local agent record. The record allows source-doc reads and documentation reconciliation/review artifact generation, but forbids documentation-agent execution, model execution, Codex execution, GitHub API/`gh`, external network calls, patch application, automatic queue mutation, and automatic next-item execution.

The M126 documentation-agent registry record uses `mutation_scope=source_patch_prohibited`, `network_scope=none`, `model_scope=none`, `safety_class=external_mutation_prohibited`, `autonomy_level=recommendation_only`, and `can_run_real=false`. It is a registry declaration only and does not add apply mode or documentation mutation behavior.

## M91 Documentation Agent v1

Documentation Agent v1 is a local-only, source-of-truth documentation reconciliation contract.

The agent exists to prepare future automation that can update documentation after validated local changes. M91 is contract-first: the implemented surface is read-only contract inspection, not documentation mutation.

## Scope

Allowed work:

- inspect changed files, queue evidence, validation results, and smoke checks
- prepare a documentation reconciliation plan
- identify source-of-truth docs that need updates
- list evidence gaps before documentation is updated
- prepare future operator-reviewed documentation patch proposals

Forbidden work:

- automatic documentation updates from model output
- automatic queue completion
- automatic next-item execution
- GitHub API calls
- `gh` calls
- issues, PRs, workflows, daemon, watcher, scheduler, or external workflow behavior

## Source Docs

Documentation Agent v1 treats these as source-of-truth docs:

- `docs/context/BUILD_STATE.md`
- `docs/context/AGENT_CONTEXT.md`
- `docs/roadmap/ROADMAP.md`
- `docs/architecture/RUNNABLE_SKELETON.md`
- `docs/operator/LOCAL_OPERATOR_USAGE.md`

Future milestones may expand this list only through an explicit contract update.

M95 confirms the documentation agent contract also treats these architecture docs as required review inputs when local LLM, routing, and documentation-agent behavior changes:

- `docs/architecture/LOCAL_LLM_ENVIRONMENT_CONTRACT.md`
- `docs/architecture/AGENT_LLM_ROUTING_STRATEGY.md`
- `docs/architecture/DOCUMENTATION_AGENT_CONTRACT.md`

## Evidence Required

Before documentation is updated, the operator must have:

- implementation commit hash or local diff summary
- queue item id and milestone identifier
- validation commands and results
- smoke checks and results
- `git diff --check` result
- files changed summary
- operator statement that documentation reconciliation is required
- explicit source docs selected for update

## Modes

Plan mode is available now and is non-mutating. It may produce:

- docs to review
- evidence gaps
- recommended documentation updates
- blocked reasons
- next safe action

Future gated apply mode is not available in M91. It requires a later milestone and explicit operator approval phrase:

    APPROVE DOCUMENTATION AGENT APPLY

Apply mode must also require validation evidence, selected source docs, worktree review, and post-apply validation. Queue completion remains a separate explicit evidence command.

M92 plan generation and M95 reconciliation are manual documentation workflows. They may identify stale sections and recommended updates, but they do not authorize automatic documentation rewrites or model-generated apply behavior.

M96 is post-sprint planning and prioritization. It may update source-of-truth docs directly as an operator-authored reconciliation step, but it does not add Documentation Agent apply mode and does not permit model-generated documentation rewrites.

M97 may select `documentation_agent_dry_run` for documentation or reconciliation queue items. This is only a dispatch plan lane and planned artifact intent. It does not execute a documentation agent, generate documentation patches, apply documentation changes, complete queue items, or create an apply mode. M100 remains the planned milestone for a documentation-agent dry-run review workflow.

M98 generates Codex prompt dispatch artifacts only for `codex_prompt_artifact`. If M97 selects `documentation_agent_dry_run`, M98 blocks generation and emits no Codex prompt text. This preserves M100 as the future documentation-agent dry-run review workflow and does not add documentation-agent execution, patch generation, apply mode, or automatic documentation mutation.

M99 validates Local LLM advisory dry-run readiness only for `local_llm_advisory`. If M97 selects `documentation_agent_dry_run`, M99 blocks readiness and emits no local LLM advisory approval. This preserves M100 as the future documentation-agent dry-run review workflow and does not add documentation-agent execution, patch generation, apply mode, or automatic documentation mutation.

M100 adds `validate-documentation-agent-dry-run` for `documentation_agent_dry_run`. The workflow consumes or derives the M97 dispatch plan, validates source docs to review, expected doc updates, stale-doc checks, reconciliation scope, validation expectations, and operator gates. It is dry-run only: it does not execute a documentation agent, does not mutate documentation, does not generate documentation patches, does not add apply mode, and does not complete queue items automatically.

M101 adds local human approval gate records for documentation-agent dry-run outputs and other dispatch artifacts. A documentation gate may move through `pending_review`, `approved_for_manual_handoff`, `rejected`, or `needs_revision`, but every status preserves `execution_allowed=false`. `approved_for_manual_handoff` means the operator may manually review or hand off the artifact; it does not authorize documentation-agent execution, documentation mutation, or apply mode. M102 remains the planned dependency/completion locking hardening milestone for future workflows that consume approval records.

M102 hardens dependency and completion locking for the local queue. Documentation-agent dry-run approval cannot bypass dependency, evidence, start, or completion locks.

M103 adds read-only self-managed project review. It may report stale documentation or source-of-truth gaps, but it does not execute a documentation agent or mutate docs automatically.

M104 adds read-only operator batch planning. It may classify documentation items as `documentation_dry_run_possible`, but that classification is advisory only and preserves `execution_allowed=false`.

M105 is an operator-authored docs/data reconciliation pass after M99-M104. It updates source-of-truth docs directly under operator control, records queue/report/handoff warnings, and does not add documentation-agent apply mode, model-generated documentation rewrites, patch generation, or automatic queue completion.

M106 may index documentation-agent dry-run artifacts if they exist under the configured local artifact folders, but it does not execute documentation agents, validate document semantics, generate patches, or apply documentation changes.

M107 may include documentation-agent dry-run artifact summaries and approval status in a safe handoff package, but the package is context only and does not authorize documentation-agent execution or apply mode.

M108 is an operator-authored sprint closeout and next-stage automation plan after M99-M107. It reconciles docs/data and recommends M116 as a future documentation-agent patch proposal milestone. M108 does not execute a documentation agent, does not generate documentation patches, does not apply documentation changes from model output, and does not complete queue items automatically.

M109 prepares manual Codex dispatch records only for `codex_prompt_artifact` items. It does not route documentation-agent dry-runs into Codex, execute a documentation agent, generate documentation patches, apply documentation changes, or approve documentation-agent apply mode. Documentation-agent patch proposal generation remains future M116 work and any patch application remains behind a later approval-gated intake path.

## Safety Boundaries

- local-only
- read-only from contract inspection
- no automatic documentation updates
- no documentation mutation from model output
- no queue mutation or queue completion
- no automatic next-item execution
- no GitHub API or `gh`
- no issues, PRs, workflows, daemons, watchers, schedulers, or external workflow behavior
- documentation-agent dry-run and approval records remain advisory until a later explicit apply milestone exists
