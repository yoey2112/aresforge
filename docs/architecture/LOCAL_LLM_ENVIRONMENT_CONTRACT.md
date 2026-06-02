# Local LLM Environment Contract

## M176 PR Draft Branch Planning Contract Boundary

M176 does not change local LLM permissions. It may inspect queue metadata, issue sync plans, PR draft summary evidence, autonomy profile policy, machine gates, local GitHub link registry records, and changed-file evidence, but it does not call Ollama, send prompts, run inference, select fallback local models, mutate repository files from model output, mutate queue status, call Codex, apply patches, run validation commands, retry failures, resume orchestration, start follow-on work, create branches, push branches, or create/update/merge PRs.

Local LLM advisory execution remains limited to separate explicit local-provider commands and their machine gates. M176 records branch/PR planning evidence only.

## M175 GitHub Issue Closure Safe Execution Gate Boundary

M175 does not change local LLM permissions. It may inspect queue metadata, closure recommendation evidence, issue-state reconciliation evidence, autonomy profile policy, machine gates, local GitHub link registry records, and linked issue metadata/state, and it may close one GitHub issue only on the explicit gated live path, but it does not call Ollama, send prompts, run inference, select fallback local models, mutate repository files from model output, mutate queue status, call Codex, apply patches, run validation commands, retry failures, resume orchestration, or start follow-on work.

Local LLM advisory execution remains limited to separate explicit local-provider commands and their machine gates. M175 records issue-closure gate evidence and, on successful live closure, local registry sync metadata only.

## M174 GitHub Issue State Reconciliation Boundary

M174 does not change local LLM permissions. It may inspect queue metadata, issue sync plans, autonomy profile policy, machine gates, local GitHub link registry records, and mocked or explicitly enabled GitHub issue-state snapshots, but it does not call Ollama, send prompts, run inference, select fallback local models, mutate repository files from model output, mutate queue status, call Codex, apply patches, run validation commands, retry failures, resume orchestration, or start follow-on work.

Local LLM advisory execution remains limited to separate explicit local-provider commands and their machine gates. M174 records recommendation-only issue-state reconciliation evidence; close/reopen/update/comment/create actions are not executed by this command.

## M173 GitHub Status Comment Durable Sync Boundary

M173 does not change local LLM permissions. It may inspect queue metadata, issue sync plans, orchestration run evidence, autonomy profile policy, machine gates, and the local GitHub link registry, and it may create or update one GitHub issue status comment only on the explicit gated live path, but it does not call Ollama, send prompts, run inference, select fallback local models, mutate repository files from model output, mutate queue status, call Codex, apply patches, run validation commands, retry failures, resume orchestration, or start follow-on work.

Local LLM advisory execution remains limited to separate explicit local-provider commands and their machine gates. M173 records durable status-comment sync evidence and, on successful live sync, local registry comment metadata only.

## M172 Queue-to-GitHub Issue Backfill Boundary

M172 does not change local LLM permissions. It may inspect queue metadata, issue sync plans, autonomy profile policy, machine gates, and the local GitHub link registry, and it may create gated GitHub issues only on the explicit live path, but it does not call Ollama, send prompts, run inference, select fallback local models, mutate repository files from model output, mutate queue status, call Codex, apply patches, run validation commands, retry failures, resume orchestration, or start follow-on work.

Local LLM advisory execution remains limited to separate explicit local-provider commands and their machine gates. M172 records backfill planning evidence and, on successful live creation, local registry metadata only.

## M171 GitHub Issue Creation Real-Run Gate Boundary

M171 does not change local LLM permissions. It may inspect queue metadata, issue sync plans, autonomy profile policy, machine gates, and the local GitHub link registry, and it may create one GitHub issue only on the explicit gated live path, but it does not call Ollama, send prompts, run inference, select fallback local models, mutate repository files from model output, mutate queue status, call Codex, apply patches, run validation commands, retry failures, resume orchestration, or start follow-on work.

Local LLM advisory execution remains limited to separate explicit local-provider commands and their machine gates. M171 records GitHub issue creation gate evidence and, on successful live creation, local registry metadata only.

## M170 GitHub Link Registry Boundary

M170 does not change local LLM permissions. It may inspect and write local queue-item GitHub issue/PR link metadata, but it does not call Ollama, send prompts, run inference, select fallback local models, mutate repository files from model output, mutate queue state, call Codex, call GitHub/`gh`, create/update/merge PRs, close issues, apply patches, run validation commands, retry failures, resume orchestration, or start follow-on work.

Local LLM advisory execution remains limited to separate explicit local-provider commands and their machine gates. M170 records local coordination metadata only.

## M169 Production Autonomy Readiness Boundary

M169 closes the M155-M169 sprint without expanding local LLM execution. The production autonomy readiness report names M155, M156, M157, M158, M159, M160, M161, M162, M163, M164, M165, M166, M167, M168, and M169 as local evidence sources only.

The report may inspect autonomy profiles and existing local model policy metadata, but it performs no local LLM/model execution, no Codex execution, no GitHub execution, no source patch application, no queue mutation, and no automatic next-item execution. Local LLM output remains advisory/prototype-scoped unless a separate explicit command and machine gates allow it.

## M168 Self-Managed AresForge Project Loop Dry Run Boundary

M168 does not change local LLM permissions. It may record route decision metadata and inspect local model execution flags from composed evidence, but it does not call Ollama, send prompts, run inference, select fallback models, apply model output, mutate repository files, mutate queue state, call live Codex, call GitHub/`gh`, create/update/merge PRs, close issues, apply patches, run validation commands, retry failures, resume orchestration, or start follow-on work.

Local LLM advisory execution remains limited to separate explicit local-provider commands and their machine gates. M168 records self-managed loop dry-run evidence only.

## M167 Hub Autonomy Control Center Boundary

M167 does not change local LLM permissions. The Hub Autonomy Control Center may read local LLM/model execution flags already present in evidence and run records, but it does not call Ollama, send prompts, run inference, select models, apply model output, mutate queue state, call Codex, call GitHub/`gh`, create/update/merge PRs, close issues, apply patches, retry failures, resume orchestration, or start follow-on work.

Local LLM advisory execution remains limited to separate explicit local-provider commands and their machine gates.

## M166 Pull Request Draft Summary Generator Boundary

M166 does not change local LLM permissions. It may generate local JSON and Markdown draft PR summary artifacts from queue evidence, Codex evidence bundle metadata, changed files, validation output, linked issue references, risks, rollback notes, and artifact paths, but it does not call Ollama, send prompts, run inference, select fallback local models, mutate repository files from model output, mutate queue state, call Codex, call GitHub/`gh`, create PRs, update PRs, merge PRs, apply patches, retry failures, resume orchestration, or start follow-on work.

Local LLM advisory execution remains limited to separate explicit local-provider commands and their machine gates. M166 records PR summary review evidence only.

## M165 GitHub Issue Closure Recommendation Gate Boundary

M165 does not change local LLM permissions. It may recommend close or keep-open for one locally linked GitHub issue from queue completion, validation evidence, artifact evidence, local linked issue metadata/state, autonomy profile inspection, and machine gates, but it does not call Ollama, send prompts, run inference, select fallback local models, mutate repository files, mutate queue state, call Codex, call GitHub/`gh`, apply patches, retry failures, resume orchestration, close issues, or start follow-on work.

Local LLM advisory execution remains limited to separate explicit local-provider commands and their machine gates. M165 records issue closure recommendation evidence only.

## M164 GitHub Issue Status Comment Sync Boundary

M164 does not change local LLM permissions. It may prepare or perform one explicitly enabled GitHub issue status comment create/update after local queue checks, run evidence inspection, autonomy profile allowance, linked issue checks, and machine gates pass, but it does not call Ollama, send prompts, run inference, select fallback local models, mutate repository files, mutate queue state, call Codex, apply patches, retry failures, resume orchestration, or start follow-on work.

Local LLM advisory execution remains limited to separate explicit local-provider commands and their machine gates. M164 records GitHub issue status comment evidence only.

## M163 GitHub Issue Creation Boundary

M163 does not change local LLM permissions. It may prepare or perform one explicitly enabled GitHub issue creation after local queue checks, autonomy profile allowance, duplicate-linked-issue checks, and machine gates pass, but it does not call Ollama, send prompts, run inference, select fallback local models, mutate repository files, mutate queue state, call Codex, apply patches, retry failures, resume orchestration, or start follow-on work.

Local LLM advisory execution remains limited to separate explicit local-provider commands and their machine gates. M163 records GitHub issue creation evidence only.

## M162 GitHub Issue Sync Plan Boundary

M162 does not change local LLM permissions. It may map local queue metadata into future GitHub issue drafts and sync recommendations, but it does not call Ollama, send prompts, run inference, select fallback local models, mutate repository files, mutate queue state, call Codex, call GitHub/`gh`, create or update issues, post comments, apply labels or milestones, apply patches, retry failures, resume orchestration, or start follow-on work.

Local LLM advisory execution remains limited to separate explicit local-provider commands and their machine gates. M162 records GitHub issue sync planning evidence only.

## M161 Codex Loop Validation Evidence Bundle Boundary

M161 does not change local LLM permissions. It may bundle Codex loop dry-run evidence, validation metadata, source patch classification, retry classification, and completion recommendation into local artifacts, but it does not call Ollama, send prompts, run inference, select fallback local models, mutate repository files from model output, mutate queue state, call live Codex, call GitHub/`gh`, apply patches, retry failures, resume orchestration, or start follow-on work.

Local LLM advisory execution remains limited to separate explicit local-provider commands and their machine gates. M161 records validation evidence for operator review, not local model execution evidence.

## M160 Low-Risk Codex Execution Pilot Item Boundary

M160 does not change local LLM permissions. It may invoke the existing low-risk Codex path only when explicit Codex execution flags, low-risk changed paths, M159 preflight, and machine gates pass, but it does not call Ollama, send prompts to local LLM providers, run local inference, select fallback local models, mutate queue state, call GitHub/`gh`, apply patches, push, merge, retry failures, resume orchestration, or start follow-on work.

Local LLM advisory execution remains limited to separate explicit local-provider commands and their machine gates. M160 records Codex pilot evidence, not local LLM provider execution evidence.

## M159 Real Codex Execution Preflight Hardening Boundary

M159 preflight does not change local LLM permissions. It may report an autonomy profile that describes local model advisory capability, but the preflight command itself does not call Ollama, send prompts, run inference, select fallback models, mutate repository files, mutate queue state, call Codex, call GitHub/`gh`, apply patches, run validation commands, retry failures, resume orchestration, or start follow-on work.

Local LLM advisory execution remains limited to separate explicit local-provider commands and their machine gates. M159 records readiness and blockers for future Codex consideration only.

## M158 Operator Autonomy Configuration Profile Boundary

M158 autonomy profile inspection does not change local LLM permissions. Profiles may mark `local_model_advisory_execution` as `enabled`, `dry_run_only`, or `blocked`, but those labels are policy metadata only. Any real local model execution still requires the separate local LLM advisory/coding command path, explicit operator intent, local provider constraints, and a passing `local_llm_execution` machine gate.

The `inspect-autonomy-profile` command does not call Ollama, send prompts, run inference, select fallback models, mutate repository files, mutate queue state, call Codex, call GitHub/`gh`, apply patches, run validation commands, retry failures, resume orchestration, or start follow-on work.

## M157 Run Replay and Audit Trail Boundary

M157 replay/audit inspection does not change local LLM permissions. Replay may report that a source orchestration run performed or avoided model execution, but the replay command itself does not call Ollama, send prompts, run inference, select fallback models, mutate repository files, mutate queue state, call Codex, call GitHub/`gh`, apply patches, run validation commands, delete artifacts, retry failures, resume orchestration, or start follow-on work.

Local LLM advisory execution remains limited to separate explicit local-provider commands and their machine gates. M157 records reconstructed run evidence only.

## M156 Orchestration Artifact Retention Policy Boundary

M156 artifact retention inspection does not change local LLM permissions. The retention index may include local artifacts that mention model execution, advisory output, or validation evidence, but the command itself does not call Ollama, send prompts, run inference, select fallback models, mutate repository files, mutate queue state, call Codex, call GitHub/`gh`, apply patches, run validation commands, delete artifacts, retry failures, resume orchestration, or start follow-on work.

Local LLM advisory execution remains limited to separate explicit local-provider commands and their machine gates. M156 records local artifact retention and cleanup-planning metadata only.

## M155 Durable Orchestration Run Store Boundary

M155 durable run-store inspection does not change local LLM permissions. The store may persist records that report whether a source orchestration run performed model execution, but the store command itself does not call Ollama, send prompts, run inference, select fallback models, mutate repository files from model output, mutate queue state, call Codex, call GitHub/`gh`, apply patches, run validation commands, retry failures, resume orchestration, or start follow-on work.

Local LLM advisory execution remains limited to separate explicit local-provider commands and their machine gates. M155 records local orchestration history durability only.

## M154 Sprint Closeout and Autonomy Readiness Report Boundary

M154 readiness reporting does not change local LLM permissions. The report may call the deterministic LLM decision policy to summarize the recommended lane for the M154 closeout item, but it does not call Ollama, send prompts, run inference, select fallback models, mutate repository files, mutate queue state, call Codex, call GitHub/`gh`, apply patches, run validation commands, retry failures, resume orchestration, or start follow-on work.

Local LLM advisory execution remains limited to separate explicit local-provider commands and their machine gates. M154 records readiness and blocker guidance only.

## M153 Hub Orchestration Run Monitor Boundary

M153 orchestration run monitoring does not change local LLM permissions. The monitor may read run history and source artifacts that report model execution, but it does not call Ollama, send prompts, run inference, select fallback models, mutate repository files, mutate queue state, call Codex, call GitHub/`gh`, apply patches, run validation commands, retry failures, resume orchestration, or start follow-on work.

Local LLM advisory execution remains limited to separate explicit local-provider commands and their machine gates. M153 only records local run-state and recovery guidance in a stable Hub-readable schema.

## M152 End-to-End Codex Loop Real Run Boundary

M152 real low-risk Codex loop execution does not change local LLM permissions. The command may invoke the configured Codex CLI command only after explicit `--execution-enabled`, `--allow-low-risk-code`, declared low-risk changed paths, and machine gates pass, but it does not call Ollama, select fallback local models, send prompts to local LLM providers, call GitHub/`gh`, apply patches through AresForge, mutate queue state, push, merge, retry failures, or start follow-on work.

Any local LLM advisory or coding output remains governed by separate local-provider contracts and gates. M152 records Codex loop evidence, not local LLM provider execution evidence.

## M151 End-to-End Codex Loop Dry Run Boundary

M151 end-to-end Codex loop dry-run does not change local LLM permissions. The command may route a local queue item through Codex dry-run dispatch metadata, validation-profile selection, and completion recommendation, but it does not call Ollama, send prompts, run inference, select fallback models, mutate repository files, mutate queue state, call real Codex, call GitHub/`gh`, apply patches, run validation commands, retry failures, or start follow-on work.

Local LLM advisory and coding outputs remain non-applied review artifacts unless a separate explicit local-provider path and machine gate allow them. M151 only records local dry-run loop evidence in a stable schema.

## M150 Source Patch Apply Dry Run Boundary

M150 source patch apply dry-run does not change local LLM permissions. The command may inspect a patch that was produced by a model or intended for source code, but it does not call Ollama, send prompts, run inference, select fallback models, mutate repository files, mutate queue state, call Codex, call GitHub/`gh`, apply patches, run validation commands, retry failures, or start follow-on work.

Local LLM advisory and coding outputs remain non-applied review artifacts unless a separate explicit apply boundary exists. M150 only records M149 plan evidence, machine-gate evidence, and `git apply --check` applicability proof in a stable local schema.

## M149 Controlled Source Patch Apply Plan Boundary

M149 source patch apply planning does not change local LLM permissions. The command may plan around a patch that was produced by a model or intended for source code, but it does not call Ollama, send prompts, run inference, select fallback models, mutate repository files, mutate queue state, call Codex, call GitHub/`gh`, apply patches, run validation commands, retry failures, or start follow-on work.

Local LLM advisory and coding outputs remain non-applied review artifacts unless a separate explicit apply boundary exists. M149 only records a future apply plan, hard blockers, validation requirements, and rollback guidance in a stable local schema.

## M148 Source Patch Risk Classifier Boundary

M148 source patch classification does not change local LLM permissions. The command may classify a patch that was produced by a model or intended for source code, but it does not call Ollama, send prompts, run inference, select fallback models, mutate repository files, mutate queue state, call Codex, call GitHub/`gh`, apply patches, run validation commands, retry failures, or start follow-on work.

Local LLM advisory and coding outputs remain non-applied review artifacts unless a separate explicit apply boundary exists. M148 only records patch risk, blocked operations, and validation requirements in a stable local schema.

## M147 Orchestrator Resume-from-Failure Boundary

M147 resume-plan inspection does not change local LLM permissions. The command may inspect a source orchestration run that reports model execution, but it does not call Ollama, send prompts, run inference, select fallback models, mutate repository files, mutate queue state, call Codex, call GitHub/`gh`, apply patches, run validation commands, retry failures, resume orchestration, or start follow-on work.

Local LLM advisory execution remains limited to separate explicit local-provider commands and their machine gates. M147 only records source execution flags, checkpoint validity, and recovery guidance in a stable local schema.

## M146 Agent Step Result Normalization Boundary

M146 step result normalization does not change local LLM permissions. The command may normalize a source step result that reports model execution, but it does not call Ollama, send prompts, run inference, select fallback models, mutate repository files, mutate queue state, call Codex, call GitHub/`gh`, apply patches, run validation commands, retry failures, or start follow-on work.

Local LLM advisory execution remains limited to separate explicit local-provider commands and their machine gates. M146 only records source execution flags and recovery guidance in a stable local schema.

## M145 Codex Failure Classification Boundary

M145 failure classification does not change local LLM permissions. The command may report LLM decision-policy metadata as context for Codex recovery planning, but it does not call Ollama, send prompts, run inference, choose fallback models, mutate repository files, mutate queue state, call Codex, call GitHub/`gh`, apply patches, run validation commands, retry failures, or start follow-on work.

Local LLM advisory execution remains limited to separate explicit local-provider commands and their machine gates. M145 only classifies local failure artifacts and reports retry/stop policy metadata.

## M144 Codex Validation Profile Boundary

M144 validation profile inspection does not change local LLM permissions. The command may report LLM decision-policy metadata as context for Codex validation planning, but it does not call Ollama, send prompts, run inference, choose fallback models, mutate repository files, mutate queue state, call Codex, call GitHub/`gh`, apply patches, run validation commands, or start follow-on work.

Local LLM advisory execution remains limited to separate explicit local-provider commands and their machine gates. M144 only selects local validation profile metadata for downstream M136 ingestion.

## M143 Codex Worktree Guard Boundary

M143 Codex sandbox/worktree guard inspection does not change local LLM permissions. The command may report routing and execution guard boundaries, but it does not call Ollama, send prompts, run inference, select fallback models, mutate repository files, mutate queue state, call Codex, call GitHub/`gh`, apply patches, run validation commands, or start follow-on work.

Local LLM execution still requires the dedicated explicit advisory path and a passing `local_llm_execution` machine gate. Dirty-worktree guard evidence for Codex must not be used as a shortcut around local LLM provider gates.

## M142 Codex Enablement Boundary

M142 real Codex execution enablement profiles do not change local LLM permissions. The command may reference the LLM decision policy summary as routing evidence, but it does not call Ollama, send prompts, run inference, select fallback models, mutate repository files, mutate queue state, call Codex, call GitHub/`gh`, apply patches, or start follow-on work.

Local LLM execution still requires the dedicated explicit advisory path and a passing `local_llm_execution` machine gate. Codex execution profiles must not be used as a shortcut around local LLM provider gates.

## M141 Orchestration History Boundary

M141 run-history and recovery records may show that an orchestration plan included or blocked local LLM advisory steps. These records are inspection evidence only. They do not authorize local model invocation, remote model calls, prompt execution, retry, resume, patch application, queue mutation, or next-item execution.

Local LLM execution still requires the dedicated explicit local advisory path and a passing `local_llm_execution` machine gate.

## M140 Orchestrator Execution State Machine

M140 defines the orchestration state boundary that future local LLM steps must obey. A local LLM step may appear in a plan, but transition into model execution remains blocked unless a separate explicit command supplies the local LLM allow path and the `local_llm_execution` machine gate passes.

The M140 inspector does not call Ollama, send prompts, run inference, inspect live models, mutate repository files, mutate queue state, call Codex, call GitHub/`gh`, apply patches, or start follow-on work. It reports `model_execution_performed=false` and records model execution as a validation boundary, not as an enabled action.

## M139 Autonomous Sprint Closeout

M139 reconciles local LLM behavior within the completed M125-M139 agent foundation sprint. The relevant sprint milestones are M125, M126, M127, M128, M129, M130, M131, M132, M133, M134, M135, M136, M137, M138, and M139.

Current local LLM posture:

- M125 defines model scope in the runtime boundary.
- M126 registers `local-llm-advisory-agent` with local provider health/advisory boundaries.
- M127 may recommend local LLM reasoning or coding-review lanes without invoking a model.
- M128/M138 may include local LLM advisory steps, but real execution requires explicit allow flags and gates.
- M131 provides the `local_llm_execution` gate.
- M134 adds `run-local-llm-advisory` for local Ollama advisory output only.
- M139 confirms that local LLM output remains advisory evidence and is never applied automatically.

The closeout command itself does not call Ollama, inspect live models, send prompts, run inference, mutate repository files, mutate queue state, call Codex, call GitHub/`gh`, apply patches, or start follow-on work.

## M134 Local LLM Advisory Execution

M134 adds `run-local-llm-advisory` as the controlled successor to advisory request artifact generation. The command may read one local advisory artifact, evaluate the `local_llm_execution` machine gate profile, and submit the artifact prompt only to a local Ollama provider when all gates pass. Dry-run mode performs the same artifact and gate checks without invoking a provider.

The provider boundary is intentionally narrow: `ollama` is the only supported provider, provider URLs must resolve to `localhost`, `127.0.0.1`, or `::1`, and tests use a mock provider rather than requiring Ollama to be installed. Remote providers, non-local Ollama URLs, missing prompts, failed gates, and missing model configuration block execution.

M134 output is advisory-only. The response is captured as a local artifact and execution metadata reports `patch_application_performed=false`, `queue_mutation_performed=false`, `github_execution_performed=false`, `codex_execution_performed=false`, and `local_only=true`. The command must not apply patches, mutate repository files, complete queue items, execute Codex, call GitHub/`gh`, call remote network services, or start follow-on work.

## M124 Sprint Closeout Note

M124 closes the M110-M124 controlled automation sprint without changing local LLM execution permissions. M110 may generate local LLM advisory request artifacts and M115 may probe only configuration or loopback `/api/tags` metadata, but the sprint does not authorize Ollama prompt execution, local inference, model-generated code, model-generated patch application, queue mutation, or automatic completion.

For current operator workflows, local LLM-related outputs remain advisory artifacts, provider metadata, or routing recommendations only. Any future local LLM execution path must be a separate explicit milestone with operator approval, machine gates, evidence capture, and non-application of generated output unless a later human-approved patch boundary exists.

## Status

M58 adds a local-only Local LLM Environment Contract.

This contract represents future local LLM provider and model configuration. It does not call Ollama, perform health checks, call model APIs, send prompts, execute routing, execute Codex, run agents, or call GitHub.

M59 adds an explicitly invoked Local LLM Health Check. The health check reads this contract and may check local provider availability only. It does not send prompts, run inference, generate text, execute routing, execute Codex, run agents, or call GitHub.

M61 adds Local LLM Prompt Preview. The preview reads this contract to resolve configured local provider/model fields for routed queue items, but it does not call Ollama, send prompts, run inference, generate text, execute routing, execute Codex, run agents, or call GitHub.

M62 adds an operator-gated local LLM execution prototype. Execution is allowed only when this contract explicitly has `execution_enabled: true`, `operator_gate_required: true`, a supported local provider, and the request passes prompt preview, health check, routing, risk, and operator confirmation gates.

M64 adds a local Execution Audit Log. Health checks, prompt previews, dry runs, blocked attempts, and advisory local LLM execution outputs are summarized in `.aresforge/execution_audit_log.json`. The audit log does not add execution behavior, does not store full prompt/response text, and does not execute anything.

M65 adds a centralized AI Action Safety Gate. Local LLM prompt preview and execution paths may consult the gate for consistent decision reporting, but the gate does not execute anything and does not expand M62 local LLM behavior.

M66 adds a local AI Artifact Registry. Local LLM prompt preview artifacts and advisory local LLM result artifacts are registered when explicitly written, but registry writes do not execute providers or expand M62 behavior.

M67 adds an Operator Run History panel that can display local LLM audit and artifact records in a read-only timeline. It does not execute providers or expand M62 behavior.

M68 reconciles local AI operations documentation and confirms that local LLM execution remains prototype-only, local-only, advisory-only, and operator-gated.

M69 hardens local AI operations around this contract. Local LLM execution payloads, audit entries, artifacts, and run-history records now make advisory-only, non-mutation, safety-status, gate-status, and blocked-reason state explicit. Local LLM output still never mutates repository files, queue state, project state, GitHub, `gh`, Codex, agents, commits, pushes, or workflows automatically.

M70 verifies the full M58-M69 local AI operations chain. It reconciles documentation and payload wording, confirms the local-first/file-backed/operator-gated/advisory-only boundaries, and does not add local LLM execution behavior beyond the M62 prototype.

M72 hardens provider and model configuration metadata. Environment reads, updates, and health-check responses now expose explicit provider availability status, provider configuration status, provider execution mode, advisory model profile metadata, fallback behavior, and next safe operator action. M72 does not add provider execution, automatic local LLM execution, or repository mutation behavior.

M75 reconciles source-of-truth documentation after M74. It does not add local LLM execution behavior. The local LLM contract remains local-only, advisory-only, operator-gated, prototype-scoped, and non-mutating. Local LLM output must never automatically mutate repository files, queue state, project state, GitHub, `gh`, Codex, agents, commits, pushes, or workflows.

M81 adds a read-only local LLM advisory/coding lane readiness inspection path. It reads this environment contract and M80 decision metadata to produce structured advisory planning output, but it does not invoke a provider, send prompts, run inference, mutate repository files, mutate queue state, complete queue items, or start another queue item.

M83 adds a read-only local LLM provider contract inspection path. It formalizes Ollama as the initial provider target and reports provider URL, health-check endpoint limits, timeout expectations, model identifiers, role/capability metadata, and safety boundaries. It does not call Ollama, send prompts, run inference, execute routing, mutate repository files, mutate queue state, complete queue items, or start another queue item.

M84 adds an explicitly invoked Ollama health/model inspection path. It may call only the local `/api/tags` endpoint to report provider reachability and visible models. Ollama offline states are warning metadata and must not block normal project readiness. M84 does not call generation, chat, completion, or prompt endpoints, and it does not mutate repository files, mutate queue state, complete queue items, or start another queue item.

M85 adds a local LLM advisory run artifact flow. It generates advisory prompt artifacts by default without invoking a provider. If the operator supplies an explicit run flag, it may call local Ollama for advisory output and store response/metadata artifacts locally. Advisory output is never applied to repository files, never mutates queue state, never completes queue items, and never starts another item.

M87 adds local coding draft artifact mode. It generates coding draft prompt artifacts by default without invoking a provider. If the operator supplies an explicit run flag, it may call local Ollama for draft patch/instruction output and store draft/metadata artifacts locally. Draft output is non-applied, non-authoritative, manual-review-only, and never mutates repository files, applies patches, mutates queue state, completes queue items, or starts another item automatically.

M88 adds a human-gated patch application contract. It defines the patch artifact structure, explicit operator approval record requirements, pre-apply safety gates, and post-apply validation requirements for any future patch application path. The contract inspector is read-only, contract-first, and dry-run only; it does not apply patches, mutate files, mutate queue state, complete queue items, or start another item.

M95 reconciles the overnight sprint documentation after M81-M94. It does not add local LLM provider behavior. The local LLM model remains local-only, explicit-operator-gated for any advisory/draft run, advisory/manual-review-only, and non-mutating. Provider output still never automatically mutates repository files, applies patches, mutates queue state, completes queue items, starts another item, calls GitHub, calls `gh`, or triggers workflows, daemons, watchers, schedulers, or external workflow systems.

M96 is post-sprint planning and prioritization. It does not add local LLM provider behavior, does not call Ollama, does not invoke advisory or coding draft runs, and does not validate provider inference.

M97 adds a queue-to-agent dispatch plan contract that may select `local_llm_advisory` or `local_llm_coding_draft` as advisory future lanes. That selection is metadata only. M97 does not call Ollama, check model inference, send prompts, invoke local advisory or coding draft runs, apply patches, mutate queue state, or complete work. Any future local LLM dry-run validation remains M99 or later and requires explicit operator approval.

M98 adds Codex prompt artifact generation only for the M97 `codex_prompt_artifact` lane. It explicitly blocks `local_llm_advisory` and `local_llm_coding_draft`, does not call Ollama, does not invoke provider health or inference endpoints, and does not authorize local LLM advisory or coding draft execution. M99 remains the planned local LLM dry-run validation milestone.

M99 adds a Local LLM Advisory Execution Dry-Run Validator for the M97 `local_llm_advisory` lane only. It validates readiness metadata and operator gates while preserving `execution_allowed=false`. It does not call Ollama, does not invoke provider health or inference endpoints, does not send prompts, does not generate model responses, does not authorize advisory execution, and blocks non-advisory lanes safely. Any actual advisory artifact or provider run remains a later explicit operator-approved milestone.

M100 adds a Documentation Agent dry-run review for `documentation_agent_dry_run`; it does not call local LLMs or affect provider behavior.

M101 adds local human approval gate records for dispatch artifacts and dry-runs. Approval status does not authorize local LLM execution and keeps `execution_allowed=false`.

M102 hardens queue dependency and completion locks. These locks do not invoke providers and must remain separate from any future local LLM artifact or execution approval.

M103 adds read-only self-managed project review, and M104 adds read-only operator batch planning. Both may report local LLM-related safety classifications or warnings, but neither calls Ollama, sends prompts, runs inference, or authorizes local LLM execution.

M105 reconciles source-of-truth docs after M99-M104. It does not add local LLM provider behavior. Any future local LLM advisory artifact generator remains a later explicit milestone such as M110.

M106 indexes local dispatch artifacts and dry-run outputs, including local LLM advisory dry-run files if they exist, but it does not call Ollama, inspect models, send prompts, or run inference.

M107 includes local LLM-related dispatch summaries and artifact index summaries in a safe handoff package, but it remains read-only context and does not authorize provider execution.

M108 closes the M99-M107 sprint and recommends M110 and M115 as future controlled local LLM milestones. M110 should generate advisory artifacts without broadening execution by default. M115 should be provider probing only unless a later explicit milestone authorizes inference. M108 itself does not call Ollama, list models, send prompts, run inference, or mutate repository/queue state.

M109 adds manual Codex dispatch preparation only. It may read local dispatch and approval records that sit beside local LLM dry-run artifacts, but it does not invoke Ollama, list models, send prompts to a local provider, run inference, produce local LLM advice, or authorize local LLM execution.

M110 adds local LLM advisory request artifact generation for the M97 `local_llm_advisory` lane. It prepares a structured local JSON package with queue context, source documents, advisory prompt, expected response shape, and operator checklist. It does not call Ollama, list models, send prompts, run inference, execute Codex, call GitHub/`gh`, make network calls, apply patches, mutate queue state, or authorize provider execution. Generated artifacts preserve `local_only=true`, `execution_allowed=false`, `local_llm_execution_performed=false`, and `patch_application_allowed=false`.

M115 adds a local Ollama provider probe for environment discovery only. The probe reads the local LLM environment contract or an explicit local config file, supports `--no-network` configuration-only inspection, and otherwise may call only a loopback `/api/tags` endpoint to list visible local model metadata. It never sends prompts, never calls generation/chat/completion endpoints, never asks a model to reason or code, and never authorizes advisory execution, coding execution, repository mutation, queue mutation, Codex execution, GitHub/`gh`, agents, workflows, or patch application.

M125 adds an Agent Runtime Boundary Contract. The boundary contract may describe model scope values such as `none`, `metadata_only`, `local_health_probe_only`, `operator_gated_local_advisory`, and `codex_handoff_only`, but inspection is metadata-only and does not call Ollama, list models, send prompts, run inference, execute agents, execute Codex, call GitHub/`gh`, make network calls, apply patches, mutate queue state, or authorize provider execution. Any future agent runtime that uses local models must satisfy the M125 boundary and the local LLM environment/provider contracts before a separate explicit operator-approved execution milestone may run.

M126 adds the local Agent Registry. The `local-llm-advisory-agent` record declares local provider health probing and advisory request artifact generation as allowed metadata capabilities, while explicitly forbidding Ollama prompt execution and local LLM inference. Its `network_scope` is `localhost_health_only`, `model_scope` is `local_health_probe_only`, `safety_class` is `local_provider_probe`, and `can_run_real=false`. Registry inspection does not call Ollama, list models, send prompts, run inference, execute agents, execute Codex, call GitHub/`gh`, make network calls beyond no-op metadata inspection, apply patches, mutate queue state, or authorize provider execution.

M127 adds LLM Decision Policy v1. The policy may recommend local reasoning or local coding review lanes from queue and agent metadata, but it does not read visible model lists, call Ollama, list models, send prompts, run inference, execute routing, execute agents, execute Codex, call GitHub/`gh`, make network calls, apply patches, mutate queue state, or authorize provider execution. Local LLM-related recommendations remain advisory inputs for later explicit artifacts or operator-approved runners only.

M117 adds an Agent Routing Decision Dashboard that may mark local LLM advisory artifacts as suitable for a queue item. That suitability flag is routing metadata only. The dashboard and `recommend-agent-route` do not call Ollama, inspect visible models, send prompts, run inference, execute routing, execute agents, execute Codex, call GitHub/`gh`, make network calls, apply patches, mutate queue state, or authorize provider execution.

M118 reconciles the post-automation planning documentation after M110-M117. It does not change the local LLM environment contract, does not call Ollama, does not inspect models, does not send prompts, does not run inference, and does not authorize local provider execution. The local LLM posture remains artifact-first, advisory-only, local-only, and operator-gated.

M128 adds the Agent Orchestration Plan Builder. It may place `local-llm-advisory-agent` in an ordered plan when M127 recommends local reasoning or coding review, but the step is metadata only. M128 does not call Ollama, list models, send prompts, run inference, execute agents, execute Codex, call GitHub/`gh`, make network calls, apply patches, mutate queue state, or authorize provider execution. Real execution target requests are blocked and reduced to a dry-run recommendation until a later explicit runner exists.

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
- `POST /api/local-queue/items/{item_id}/local-llm-prompt-preview`
- `POST /api/local-queue/items/{item_id}/local-llm-execute`
- `GET /api/execution-audit-log`
- `POST /api/ai-action-safety-gate`
- `GET /api/ai-artifacts`
- `GET /api/operator-run-history`
- `GET /api/ai-action-review`
- CLI: `python -m aresforge inspect-local-llm-advisory-lane-readiness --item-id <item_id> --format json`
- CLI: `python -m aresforge inspect-local-llm-provider-contract --format json`
- CLI: `python -m aresforge inspect-ollama-health --format json`
- CLI: `python -m aresforge probe-local-ollama-provider --format json`
- CLI: `python -m aresforge test-ollama`
- CLI: `python -m aresforge prepare-local-llm-advisory-run --item-id <item_id> --format json`
- CLI: `python -m aresforge prepare-local-coding-draft --item-id <item_id> --format json`
- CLI: `python -m aresforge inspect-human-gated-patch-application-contract --format json`
- CLI: `python -m aresforge validate-local-llm-advisory-dry-run --item-id <item_id> --format json`
- CLI: `python -m aresforge plan-operator-batch --project-id aresforge --limit 10 --format json`

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

Derived read-only metadata:

- `provider_availability_status`
- `provider_configuration_status`
- `provider_execution_mode`
- `provider_state`
- `local_model_profiles`
- `fallback_behavior`

## Supported Providers

- `ollama`
- `none`
- `unknown`

Model fields are placeholders/configuration only. A non-empty model name does not mean the model is installed.

## M83 Provider Contract

`inspect-local-llm-provider-contract` is a read-only provider contract inspector. It uses the local environment contract as input and returns:

- initial provider target: `ollama`
- supported provider targets
- provider base URL and source
- request timeout and health-check timeout expectations
- allowed health endpoint: `/api/tags`
- forbidden inference endpoints such as `/api/generate`, `/api/chat`, `/api/completions`, and `/v1/chat/completions`
- separate reasoning, coding, and fallback model identifiers
- role/capability metadata for local reasoning and local coding lanes
- safety boundary confirmations

The provider contract supports future local reasoning and local coding model selection, but selection remains operator-reviewed metadata. Fallback model configuration is never selected or executed automatically.

Provider contract inspection does not require Ollama to be running. Tests must mock or inspect local files only and must not require a real Ollama service.

## M84 Ollama Health and Model Inspection

`test-ollama` and `inspect-ollama-health` are explicit local-only inspection commands. They return a stable payload with:

- `available`
- `provider`
- `endpoint`
- `models`
- `error_summary`
- `next_safe_action`
- `model_inspection_contract`
- `safety_boundary`

The inspection path may call only the configured local Ollama `/api/tags` endpoint. It must not call `/api/generate`, `/api/chat`, `/api/completions`, `/v1/chat/completions`, or any prompt-bearing endpoint.

When Ollama is not running, the command should still succeed as an inspection operation and return `available: false`, an `error_summary`, an empty model list, and a next safe operator action. This offline state is not a normal project readiness blocker.

Visible model names are metadata only. Model presence does not authorize prompt execution, local LLM advisory execution, repo mutation, queue mutation, queue completion, automatic fallback selection, or automatic next-item execution.

## M85 Advisory Run Artifacts

`prepare-local-llm-advisory-run` creates a local prompt artifact for one queue item. The default behavior is artifact-only and does not call Ollama.

The optional `--run` flag is an explicit operator gate for advisory output. When used, the command first inspects local Ollama model availability and then may call the local `/api/generate` endpoint for advisory text. The response and run metadata are stored under `artifacts/local_llm_advisory/generated/`.

Required output includes:

- `prompt_path`
- `response_path`
- `metadata_path`
- `provider_model_metadata`
- `safety_boundary`
- `boundary_confirmations`
- `next_safe_action`

Unavailable provider or model states return safe unavailable metadata. They do not fail normal project readiness and do not authorize fallback execution.

Advisory artifacts and responses are never applied automatically to repository files, queue state, project state, GitHub, `gh`, Codex, agents, commits, pushes, workflows, daemons, watchers, or schedulers.

## M87 Local Coding Draft Artifacts

`prepare-local-coding-draft` creates a local coding draft prompt artifact for one queue item. The default behavior is artifact-only and does not call Ollama.

The optional `--run` flag is an explicit operator gate for draft output. When used, the command first inspects local Ollama model availability and then may call the local `/api/generate` endpoint for draft patch or instruction text. The draft and run metadata are stored under `artifacts/local_coding_drafts/generated/`.

Required output includes:

- `prompt_path`
- `draft_path`
- `metadata_path`
- `provider_model_metadata`
- `draft_contract`
- `safety_boundary`
- `boundary_confirmations`
- `next_safe_action`

Draft output may include patch-like text, but it is not an applied patch. It is non-authoritative manual guidance only. A draft artifact must not mutate repository files, apply patches, mutate queue state, complete queue items, start next items, call GitHub, call `gh`, or trigger workflows, daemons, watchers, schedulers, or external workflow systems.

## M88 Human-Gated Patch Application Contract

`inspect-human-gated-patch-application-contract` reports the contract for any future manual patch application path.

The contract defines:

- required patch artifact fields, including source draft artifact path, target item id, patch format, target files, patch text, rationale, risks, expected validation, provider/model metadata, and applied/manual review booleans
- explicit operator approval requirements, including the approval phrase `APPROVE LOCAL PATCH APPLICATION`
- pre-apply safety gates for local-only operation, approval record presence, patch schema validation, target file scoping, path traversal prevention, manual diff review, validation plan presence, and no external workflow behavior
- post-apply validation requirements, including operator final diff review, `git diff --check`, targeted tests, relevant smoke checks, and separate queue evidence completion

M88 remains dry-run only. The contract inspector does not apply patches, mutate repository files, mutate queue state, complete queue items, start another item, invoke a provider, call GitHub APIs, call `gh`, create issues or PRs, touch workflows, or run daemon, watcher, scheduler, or external workflow behavior.

## Provider Availability States

M72 exposes provider state in operator-readable form:

- `configured`: supported local provider configuration is syntactically complete
- `missing_configuration`: provider, local URL, or model configuration is incomplete
- `unavailable`: explicit health check could not reach the configured local provider
- `unsupported`: provider value or URL is not allowed for local LLM workflows
- `disabled`: provider is intentionally set to `none`
- `prototype_only`: execution mode is enabled only for the M62 explicit operator-gated prototype

These states are review metadata. They do not authorize automatic execution.

## Local Model Profiles

M72 derives advisory profile metadata for:

- reasoning model -> intended lane `local_reasoning_llm`
- coding model -> intended lane `local_coding_llm`
- fallback model -> intended lane `fallback`

Each profile includes provider, model name, intended lane, recommended use, hardware notes, status, advisory warning, and prototype warning. Profile status may be `configured`, `missing_configuration`, `unavailable`, `unsupported`, or `disabled` depending on provider configuration and explicit health-check results.

Fallback behavior is explicit: fallback model names are advisory operator review metadata only and are never selected or executed automatically.

## Validation

- `local_llm_provider` must be `ollama`, `none`, or `unknown`.
- `provider_base_url` may be blank for `none` or `unknown`.
- `execution_enabled` may be `false` or `true`; `true` enables only the M62 operator-gated local execution prototype.
- `operator_gate_required` must remain `true`.
- `health_check_enabled` may be true or false, but does not trigger a health check in M58.
- Model names may be blank; non-blank values are strings.
- `max_context_tokens` and `request_timeout_seconds` must be positive integers when supplied.
- provider/model metadata must remain advisory and non-executing.

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
- provider availability/configuration status
- local model profile status
- fallback behavior
- warnings and blockers

For provider `ollama`, the health check may call only the local `/api/tags` endpoint. It must not call generate, chat, completion, or prompt endpoints.

Provider URLs must be local: `localhost`, `127.0.0.1`, or `::1`.

M64 records a local audit summary for health check outcomes. The audit entry records provider/model metadata and outcome, not secrets or prompt content.

## M61 Prompt Preview

Local LLM Prompt Preview is copy/paste preview generation only.

Preview may proceed when:

- a queue item exists
- routing metadata recommends `local_reasoning_llm` or `local_coding_llm`
- this environment contract is readable
- the recommended model is available from routing metadata or this environment contract
- project policy does not require `manual_only` handling without operator override

Preview blocks or warns for:

- `codex_cli` routes
- unrouted queue items
- provider `none` or `unknown`
- missing local model configuration
- malformed local LLM environment contract
- high-risk local preview that may need Codex review

Preview output includes local-only operating rules, validation expectations, routing metadata, and `execution_allowed: false`. Optional artifact output is local-only and refuses to overwrite existing files unless `force=true`.

M64 records prompt preview audit entries for generated and blocked previews. Audit entries do not store the full generated prompt.

M65 classifies prompt preview as a preview-only action. Gate output keeps `execution_allowed: false` for preview and reports blockers/warnings without calling a provider.

## M62 Execution Prototype

Local LLM execution is conservative and operator-gated.

Execution may proceed only when:

- the queue item exists
- routing metadata recommends `local_reasoning_llm` or `local_coding_llm`
- provider is local `ollama`
- provider URL points to `localhost`, `127.0.0.1`, or `::1`
- `execution_enabled` is `true`
- `operator_gate_required` remains `true`
- prompt preview is generated
- local health check confirms provider reachability and model availability
- real execution request has `confirm_operator_gate: true`
- high or critical risk has `operator_override: true`

Execution output is advisory only. It may be written to a local result artifact if the operator provides an output path. It is never applied to repo files, queue status, project state, GitHub, `gh`, Codex, agents, commits, pushes, or workflows.

M64 records dry runs, blocked attempts, and advisory execution outcomes in the local audit log. Audit entries prefer summaries and artifact paths over full response text.

M65 centralizes execution gate reporting for this path. The local LLM execution helper consults the gate for operator confirmation, local routing, high/critical risk override, and manual policy decisions without adding any provider behavior.

## Boundaries

- local-only
- file-backed
- operator-gated
- advisory-only
- prototype-scoped
- non-mutating
- configuration and health metadata only
- prompt preview metadata only
- local LLM execution only through M62 explicit operator-gated prototype
- no routing execution
- no Codex execution
- no agent execution
- no GitHub API or `gh`
- no external/network execution beyond explicitly operator-invoked local provider health check and local provider execution behavior
- no automatic queue progression, commit, push, workflow, or repository file mutation from local LLM output

## Next Phase Safety Gates

Before any local LLM coding-output expansion can move beyond advisory prototype behavior:

- explicit operator approval
- one queue item at a time
- no automatic next-item execution
- run state tracked
- stdout/stderr/artifacts captured where applicable
- error and completion states recorded
- review evidence required before marking complete
- queue/dependency blocking enforced
- local validation required before commit/push

## Next Milestones

M61 added Local LLM Prompt Preview without execution.

M62 added the first operator-gated local execution prototype.

M64 added the local Execution Audit Log without expanding execution.

M65 added the AI Action Safety Gate for consistent decision reporting without expanding execution.

M66 added the AI Artifact Registry for generated advisory artifacts without expanding execution.

M67 added the Operator Run History Panel as a read-only timeline.

M68 reconciled local AI operations docs and validation without expanding execution.

M69 hardened local AI operations around edge cases, blocked/error metadata, and non-mutation state.

M70 completed a verification sweep of the M58-M69 local AI operations chain without expanding execution.

M71 added an operator-facing AI Action Review Panel without adding execution.

M72 hardened local LLM provider/model configuration.

M73 improved prompt-pack quality and routing guidance.

M74 stabilized Hub UX wording.

M75 reconciles source-of-truth docs and prepares M76-M82 without expanding local LLM execution.

M81 adds local LLM advisory lane readiness inspection without expanding local LLM execution.
