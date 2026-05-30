# Local Operator Usage

## M115 Local Ollama Provider Probe Integration

M115 probes local Ollama provider readiness for environment discovery only. It does not send prompts, ask a model to reason or code, generate advisory output, execute Codex, call GitHub, call `gh`, execute agents, apply patches, mutate files, mutate queue state, or start follow-on work.

Readable probe:

    python -m aresforge probe-local-ollama-provider

JSON probe:

    python -m aresforge probe-local-ollama-provider --format json

Configuration-only probe:

    python -m aresforge probe-local-ollama-provider --no-network --format json

Write a local probe record:

    python -m aresforge probe-local-ollama-provider --output artifacts/local_ollama_provider_probes/probe.json --format json

Overwrite only with explicit force:

    python -m aresforge probe-local-ollama-provider --output artifacts/local_ollama_provider_probes/probe.json --format json --force

The probe record includes:

- `probe_type=local_ollama_provider_probe`
- probed/blocked status and blocked reasons
- Ollama expected/detected status
- probe method
- configured model profiles
- available models when safely detectable through loopback `/api/tags`
- coding and reasoning model recommendation metadata
- `advisory_execution_allowed=false`
- `prompt_execution_performed=false`
- `coding_execution_performed=false`
- `reasoning_execution_performed=false`
- `local_only=true`
- `execution_allowed=false`

Safety behavior:

- `--no-network` performs config-only inspection
- network probing is limited to loopback `localhost`, `127.0.0.1`, or `::1`
- non-loopback provider URLs block network probing
- offline Ollama is warning metadata, not a queue readiness blocker
- no prompt-bearing Ollama endpoints are called

## M114 Hub Dispatch Review Panel

M114 adds a read-only Dispatch Review panel in the Hub Queue section. It displays local dispatch review artifacts and recommendations only. It does not execute Codex, Ollama, local LLMs, agents, GitHub, `gh`, network services, patch application, approval updates, queue completion, handoff automation, or follow-on work.

Hub API:

    GET /api/dispatch-review
    GET /api/dispatch-review?item_id=<item_id>&limit=25

The API returns:

- `panel_type=hub_dispatch_review_panel`
- `local_only=true`
- `read_only=true`
- `execution_allowed=false`
- `queue_mutation_performed=false`
- `patch_application_allowed=false`
- source directories
- category counts
- normalized review records
- operator checklist
- next safe action

Review record sources:

- manual dispatch preparation records
- local LLM advisory artifacts
- patch intake records
- parsed dispatch evidence
- queue completion recommendations

Operator workflow:

- open Hub Queue
- load Dispatch Review
- optionally filter by item id
- review artifact type, milestone, blocked status, next safe action, and checklist
- use explicit local-only operator commands for any later action

## M126 Agent Registry

M126 inspects the local declarative registry of known AresForge agents. It does not execute agents, invoke Codex, invoke Ollama or local LLMs, run documentation agents, call GitHub, call `gh`, call network services, apply patches, mutate queue state, create autonomous workflows, or start follow-on work.

JSON inspection:

    python -m aresforge inspect-agent-registry --format json

Filter to one agent:

    python -m aresforge inspect-agent-registry --agent-id documentation-agent --format json

Filter by safety class or autonomy level:

    python -m aresforge inspect-agent-registry --safety-class external_mutation_prohibited --format json
    python -m aresforge inspect-agent-registry --autonomy-level recommendation_only --format json

Write a local registry snapshot:

    python -m aresforge inspect-agent-registry --format json --output artifacts/agent-registry/registry.json

Overwrite only with explicit force:

    python -m aresforge inspect-agent-registry --format json --output artifacts/agent-registry/registry.json --force

The registry output includes `registry_type=agent_registry`, `agent_count`, filtered agent records, grouping by type/safety/autonomy, blocked agents, executable agents, dry-run-only agents, `local_only=true`, and `execution_performed=false`.

Registered agents are declarative metadata only. `can_run_real=false` for every M126 agent until a later explicit operator-approved runner exists.

## M113 Queue Item Auto-Completion Recommendation Engine

M113 recommends whether a human operator may safely complete a queue item from local dispatch evidence. It does not complete queue items, mutate queue state, execute Codex, invoke models, call GitHub, call `gh`, call network services, apply patches, mutate approvals, hand off work, or start follow-on work.

Readable recommendation:

    python -m aresforge recommend-queue-completion --item-id <item_id> --evidence-path <path>

JSON recommendation:

    python -m aresforge recommend-queue-completion --item-id <item_id> --evidence-path <path> --format json

Write a local recommendation record:

    python -m aresforge recommend-queue-completion --item-id <item_id> --evidence-path <path> --output artifacts/queue_completion_recommendations/<item_id>.json --format json

Overwrite only with explicit force:

    python -m aresforge recommend-queue-completion --item-id <item_id> --evidence-path <path> --output artifacts/queue_completion_recommendations/<item_id>.json --format json --force

The recommendation record includes:

- `recommendation_record_type=queue_completion_recommendation`
- recommended/blocked status and blocked reasons
- queue identity
- evidence path and validity
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

- reads the local queue item and local M112 evidence JSON
- validates evidence type, item id, parsed/blocked state, local-only flag, execution flag, and human review flag
- checks files changed, change summary, tests, smoke checks, warnings/blockers, and commit hash
- evaluates queue `completion_requires` and `evidence_required` fields when present
- blocks when evidence is missing, invalid, failed, incomplete, mismatched, or reports severe warnings/blockers

Operator workflow:

- save or generate an M112 dispatch evidence record
- run `recommend-queue-completion`
- review `missing_evidence`, `blocked_reasons`, and `confidence`
- if the recommendation is complete-worthy, make the final human decision
- complete the queue item only through `complete-local-queue-item` with explicit validation evidence

## M125 Agent Runtime Boundary Contract

M125 inspects the agent runtime boundary contract. It does not execute agents, Codex, Ollama, local LLMs, documentation agents, GitHub, `gh`, network services, patch application, workflows, queue completion, handoff automation, or next-item execution.

Readable inspection:

    python -m aresforge inspect-agent-runtime-boundary

JSON inspection:

    python -m aresforge inspect-agent-runtime-boundary --format json

The JSON output includes:

- `contract_type=agent_runtime_boundary`
- `generated=true`
- `agent_boundary_version`
- supported execution modes
- supported autonomy levels
- supported safety classes
- allowed and forbidden capability catalogs
- mutation, network, and model scope catalogs
- evidence requirements
- default runtime limits
- `local_only=true`
- `execution_performed=false`
- next safe action

Required agent declaration fields for future runtimes:

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

Use this contract as the preflight boundary for future agent profiles, planners, dry-runs, and operator-gated runners. Do not treat it as execution approval.

## M112 Dispatch Result Evidence Parser

M112 parses a local text or markdown file containing human-pasted Codex result output. It does not execute Codex, invoke models, call GitHub, call `gh`, call network services, apply patches, mutate repository files from the parsed result, complete queue items, or start follow-on work.

Readable evidence parsing:

    python -m aresforge parse-dispatch-result-evidence --item-id <item_id> --result-path <path>

JSON evidence parsing:

    python -m aresforge parse-dispatch-result-evidence --item-id <item_id> --result-path <path> --format json

Write a local evidence record:

    python -m aresforge parse-dispatch-result-evidence --item-id <item_id> --result-path <path> --output artifacts/dispatch_result_evidence/<item_id>.json --format json

Overwrite only with explicit force:

    python -m aresforge parse-dispatch-result-evidence --item-id <item_id> --result-path <path> --output artifacts/dispatch_result_evidence/<item_id>.json --format json --force

The evidence record includes:

- `evidence_record_type=dispatch_result_evidence`
- parsed/blocked status and blocked reasons
- queue identity
- result file path and existence
- files changed
- change summary
- tests reported
- smoke checks reported
- warnings or blockers
- commit hash
- validation confidence
- completion recommendation
- `human_review_required=true`
- `local_only=true`
- `execution_allowed=false`

Parser behavior:

- recognizes common Codex completion sections
- infers file paths, validation lines, smoke lines, and commit hashes when possible
- treats missing sections as warnings
- blocks missing queue item, missing result file, and output overwrite without `--force`

Operator workflow:

- save the manual Codex result transcript or final summary to a local `.md` or `.txt` file
- run `parse-dispatch-result-evidence`
- review missing-section warnings and validation confidence
- use the evidence record as input for human review or later recommendation tooling
- complete the queue item only through the explicit queue lifecycle command with validation evidence

## M111 Approval-Gated Patch Intake Contract

M111 records a proposed patch artifact for human review. It does not apply patches, mutate repository files, execute Codex, invoke local LLMs, execute documentation agents, call GitHub, call `gh`, call network services, mutate approval state, complete queue items, or start follow-on work.

Readable intake:

    python -m aresforge intake-patch-proposal --item-id <item_id> --patch-artifact <path>

JSON intake:

    python -m aresforge intake-patch-proposal --item-id <item_id> --patch-artifact <path> --format json

Use a specific approval gate:

    python -m aresforge intake-patch-proposal --item-id <item_id> --patch-artifact <path> --approval-id <approval_id> --format json

Write a local intake record:

    python -m aresforge intake-patch-proposal --item-id <item_id> --patch-artifact <path> --output artifacts/patch_intake/<item_id>.json --format json

Overwrite only with explicit force:

    python -m aresforge intake-patch-proposal --item-id <item_id> --patch-artifact <path> --output artifacts/patch_intake/<item_id>.json --format json --force

Required behavior:

- queue item must exist
- patch artifact must exist locally
- approval gate must exist
- approval status must be `approved_for_manual_handoff`
- accepted records still keep `patch_application_allowed=false`
- accepted records still keep `patch_application_performed=false`

The intake record includes:

- `intake_record_type=patch_proposal_intake`
- accepted/blocked status and blocked reasons
- queue identity
- patch artifact path and existence
- patch summary
- approval gate id and status
- operator review requirement
- local-only and execution-denial fields
- next safe action

M111 boundaries:

- no patch application
- no repository file mutation
- no Codex, local LLM, documentation-agent, or external-agent execution
- no GitHub API, `gh`, network, issue, PR, or workflow behavior
- no queue completion, approval mutation, handoff automation, or next-item execution

## M110 Local LLM Advisory Artifact Generator

M110 prepares a local LLM advisory request artifact. It does not run Ollama, invoke local models, execute Codex, call GitHub, call network services, execute agents, apply patches, mutate queue state, or complete work. The artifact is a review package an operator may inspect before any later separately approved local LLM invocation milestone.

Readable generation:

    python -m aresforge generate-local-llm-advisory-artifact --item-id <item_id>

JSON generation:

    python -m aresforge generate-local-llm-advisory-artifact --item-id <item_id> --format json

Write a specific local artifact:

    python -m aresforge generate-local-llm-advisory-artifact --item-id <item_id> --output artifacts/local_llm_advisory/requests/<item_id>.json --format json

Overwrite only with explicit force:

    python -m aresforge generate-local-llm-advisory-artifact --item-id <item_id> --output artifacts/local_llm_advisory/requests/<item_id>.json --format json --force

Optionally name the intended advisory profile and scope:

    python -m aresforge generate-local-llm-advisory-artifact --item-id <item_id> --model-profile reasoning-fast --reasoning-scope safety_review

If `--output` is omitted, the command writes a timestamped JSON artifact under:

- `artifacts/local_llm_advisory/requests`

The artifact includes:

- `artifact_type=local_llm_advisory_request`
- generated/blocked status and blocked reasons
- queue identity and lifecycle status
- requested model profile and reasoning scope
- source documents
- queue context
- advisory prompt
- expected response shape
- operator review checklist
- `local_only=true`
- `execution_allowed=false`
- `local_llm_execution_performed=false`
- `codex_execution_performed=false`
- `network_execution_performed=false`
- `patch_application_allowed=false`
- next safe action

Required behavior:

- selected lane must be `local_llm_advisory`
- dispatch plan must be unblocked
- dispatch plan must preserve `local_only=true`
- dispatch plan must preserve `execution_allowed=false`
- explicit output files are not overwritten unless `--force` is provided

M110 boundaries:

- no Ollama API calls or local model inference
- no Codex execution or Codex CLI shell-out
- no GitHub API, `gh`, network, documentation-agent, or external-agent invocation
- no patch application
- no queue completion, approval mutation, handoff automation, or next-item execution

## M109 Manual Codex Dispatch Runner Contract

M109 prepares a manual Codex dispatch run record. It does not run Codex. It is the operator checklist and evidence contract between a generated M98 Codex prompt artifact and a human manually pasting that artifact into Codex outside AresForge.

Readable preparation:

    python -m aresforge prepare-manual-codex-dispatch --item-id <item_id>

JSON preparation:

    python -m aresforge prepare-manual-codex-dispatch --item-id <item_id> --format json

Use explicit artifact and approval records when the artifact index has multiple candidates:

    python -m aresforge prepare-manual-codex-dispatch --item-id <item_id> --artifact-path <path> --approval-id <approval_id> --format json

Write a local preparation record:

    python -m aresforge prepare-manual-codex-dispatch --item-id <item_id> --output artifacts/manual_codex_dispatch/prepared/<item_id>.json --format json

Overwrite only with explicit force:

    python -m aresforge prepare-manual-codex-dispatch --item-id <item_id> --output artifacts/manual_codex_dispatch/prepared/<item_id>.json --format json --force

The preparation record includes:

- prepared/blocked status and blocked reasons
- queue identity and lifecycle status
- selected lane
- Codex prompt artifact path
- approval gate id and approval status when available
- manual dispatch steps
- operator checklist
- evidence expected after the manual Codex run
- `local_only=true`
- `execution_allowed=false`
- `codex_execution_performed=false`
- next safe action

Required approval behavior:

- approval gate status must be `approved_for_manual_handoff`
- missing approval blocks as needs approval
- `pending_review`, `needs_revision`, `rejected`, and unknown statuses block
- approval still does not authorize automated execution

Required artifact behavior:

- selected lane must be `codex_prompt_artifact`
- Codex prompt artifact must exist
- M97 plan and artifact metadata must preserve `local_only=true` and `execution_allowed=false`
- missing artifacts block the preparation record

After the operator manually runs Codex outside AresForge, expected evidence includes:

- manual run transcript or summary
- proposed file changes
- patch or diff artifact if one was produced
- validation commands and output
- operator accept/reject/defer notes
- later M111 patch-intake approval evidence before any patch application

M109 boundaries:

- no Codex execution
- no Codex CLI shell-out
- no GitHub API, `gh`, network, Ollama/local LLM, documentation-agent, or external-agent invocation
- no patch application
- no queue completion, approval mutation, handoff automation, or next-item execution

M110 now generates local LLM advisory request artifacts only. M111 is the future approval-gated patch intake contract for returned manual Codex results.

## M108 Sprint Closeout and Next-Stage Automation Plan

M108 is a completed docs/data-only sprint closeout workflow after M99-M107. It reconciled local report state, source-of-truth docs, queue evidence, and the next controlled automation sequence. It did not add runtime features or execute any agent/model/dispatch workflow.

Recommended inspection commands:

    python -m aresforge inspect-local-project-report
    python -m aresforge inspect-local-queue-agent-summary
    python -m aresforge inspect-project-queue --project-id aresforge
    python -m aresforge plan-operator-batch --project-id aresforge --limit 10 --format json
    python -m aresforge inspect-dispatch-artifacts --format json
    python -m aresforge generate-safe-dispatch-handoff --format json
    python -m aresforge generate-handoff-package

Current closeout findings:

- M99-M107 are complete in the local queue.
- M108 is complete.
- M96 remains proposed as older manual planning context.
- The artifact index currently reports zero artifacts and warning-only missing default artifact folders.
- Safe dispatch handoff remains local-only/read-only and preserves `execution_allowed=false`.
- Persistent local warning noise remains from untracked `.codex-pytest-cache/` and inaccessible old pytest temp directories.

Operator workflow:

- run the local reports above
- update source-of-truth docs only
- keep implemented capabilities distinct from future automation
- select the next milestone manually
- seed/start only one approved next-stage milestone at a time
- record queue completion evidence after validation

Next controlled automation batch:

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

- no Codex execution
- no Ollama or local model invocation
- no documentation-agent execution
- no artifact execution
- no GitHub API, `gh`, issues, PRs, workflows, or network calls
- no external agents
- no patch application
- no queue auto-start, auto-completion, automatic handoff, dispatch, approval mutation, or next-item execution

## M107 Safe Dispatch Handoff Package

M107 generates a local-only handoff report for dispatch review and new chat handoffs. It bundles queue state, dispatch plans, the M106 artifact index, M101 approval status, and explicit operator instructions. It does not execute anything.

Readable safe dispatch handoff:

    python -m aresforge generate-safe-dispatch-handoff

JSON safe dispatch handoff:

    python -m aresforge generate-safe-dispatch-handoff --format json

Write a local handoff file:

    python -m aresforge generate-safe-dispatch-handoff --output artifacts/safe-dispatch/handoff.md

Overwrite only with explicit force:

    python -m aresforge generate-safe-dispatch-handoff --output artifacts/safe-dispatch/handoff.md --force

The handoff includes:

- repo path, branch, and HEAD
- active project identity
- queue summary and next recommended items
- dispatch plan summaries
- artifact index summary
- approval gate summary
- warnings and blockers
- local-only boundaries
- manual approval requirements
- operator next actions

Manual approval is required before:

- using any dispatch artifact in another tool or chat
- preparing artifacts for a new chat handoff
- changing approval gate status
- starting, completing, or dispatching queue work

M107 boundaries:

- no Codex execution
- no Ollama or local model invocation
- no documentation-agent execution
- no artifact execution
- no GitHub API, `gh`, issues, PRs, workflows, or network calls
- no external agents
- no patch application
- no queue mutation, approval mutation, automatic handoff, dispatch, or next-item execution
- `execution_allowed` remains false

## M106 Dispatch Artifact Index/Report

M106 indexes local dispatch artifacts and dry-run outputs so an operator can see what exists before handoff packaging. It is read-only and does not execute artifacts, agents, models, patches, or handoff workflows.

Readable artifact index:

    python -m aresforge inspect-dispatch-artifacts

JSON artifact index:

    python -m aresforge inspect-dispatch-artifacts --format json

Project-specific view:

    python -m aresforge inspect-dispatch-artifacts --project-id aresforge

The report scans known local output folders:

- `artifacts/codex_prompt_dispatch/generated`
- `artifacts/local_llm_advisory/dry_runs`
- `artifacts/documentation_agent/dry_runs`

Each artifact entry includes:

- stable `artifact_id`
- `artifact_type`
- `item_id`
- `dispatch_lane`
- `file_path`
- created and modified timestamps when available
- `approval_gate_status` and `approval_id` when available
- `local_only: true`
- `execution_allowed: false`
- `next_safe_action`

Operator workflow:

- generate dispatch artifacts or dry-runs through the existing M98-M100 commands
- create or update M101 approval gates for artifacts that need manual handoff review
- run `inspect-dispatch-artifacts`
- resolve missing, rejected, or needs-revision approval states before M107 handoff packaging
- treat `approved_for_manual_handoff` as manual packaging permission only, not execution approval

M106 boundaries:

- no Codex execution
- no Ollama or local model invocation
- no documentation-agent execution
- no artifact execution or automatic validation
- no GitHub API, `gh`, issues, PRs, workflows, or network calls
- no external agents
- no patch application
- no queue mutation, approval mutation, automatic handoff, dispatch, or next-item execution

## M105 Post-Batch Documentation Reconciliation

M105 is a docs/data-only reconciliation pass after M99-M104. It updates source-of-truth documentation and local project state; it does not add new runtime features or execute any agent/model/dispatch workflow.

Recommended inspection commands:

    python -m aresforge inspect-local-project-report
    python -m aresforge inspect-local-queue-agent-summary
    python -m aresforge inspect-project-queue --project-id aresforge
    python -m aresforge plan-operator-batch --project-id aresforge --limit 10 --format json
    python -m aresforge generate-handoff-package

Current reconciliation findings:

- M99-M104 are complete in the local queue.
- M96 remains proposed as older planning context.
- The M104 batch planner currently proposes M96 as the only non-done plannable item.
- Handoff generation remains local-only/read-only by default.
- Local warning noise remains from untracked `.codex-pytest-cache/` and inaccessible old pytest temp directories.

Operator workflow:

- inspect the local reports above
- update source-of-truth docs only
- keep implemented commands distinct from future automation
- record queue completion evidence after validation
- select any next milestone manually

M105 boundaries:

- no Codex execution
- no Ollama or local model invocation
- no documentation-agent execution
- no automatic documentation mutation
- no GitHub API, `gh`, issues, PRs, workflows, or network calls
- no external agents
- no patch application
- no automatic queue start, completion, dispatch, handoff, or next-item execution

## M104 Operator Batch Planner

M104 proposes a safe local sprint batch from queue state. It is read-only and does not seed, start, complete, execute, dispatch, or hand off work.

Readable batch plan:

    python -m aresforge plan-operator-batch --project-id aresforge

Limit the batch size:

    python -m aresforge plan-operator-batch --project-id aresforge --limit 10

JSON batch plan:

    python -m aresforge plan-operator-batch --project-id aresforge --limit 10 --format json

The plan includes:

- `batch_id` and `generated_at`
- ordered `proposed_items`
- `excluded_items` such as done work or items past the requested limit
- `blocked_items` with JSON-serializable reasons
- `warnings`
- `recommended_next_action`
- `local_only: true`
- `read_only: true`
- `execution_allowed: false`

Safety classifications:

- `manual_only`
- `codex_artifact_possible`
- `local_llm_dry_run_possible`
- `documentation_dry_run_possible`
- `blocked`

Operator workflow before an overnight sprint:

- run the M103 self-managed project review
- run the M104 batch planner with the intended limit
- inspect blocked and excluded items before choosing work
- start only one approved queue item at a time through normal lifecycle commands
- generate dispatch artifacts or dry-runs only through the existing local-only M97-M101 workflows
- reconcile post-batch evidence and documentation drift through M105 or later workflow support

M104 boundaries:

- no queue mutation or default seeding
- no Codex execution
- no Ollama or local model invocation
- no documentation-agent execution
- no GitHub API, `gh`, issues, PRs, workflows, or network calls
- no external agents
- no patch application
- no automatic queue start, completion, dispatch, handoff, or next-item execution

## M103 Self-Managed Project Review

M103 reviews whether AresForge is ready to act as its own first managed project. The report is local-only and read-only.

Readable review:

    python -m aresforge inspect-self-managed-project --project-id aresforge

JSON review:

    python -m aresforge inspect-self-managed-project --project-id aresforge --format json

The report includes:

- project id, name, and active-project match
- primary repo id, repo path, registered default branch, and current local branch
- active milestone marker from the roadmap
- queue counts and next recommended queue item
- required source-of-truth doc presence
- readiness gaps, warnings, and blockers
- explicit false values for unsafe execution assumptions

Common gaps:

- missing active milestone marker in the roadmap
- missing required source-of-truth docs
- missing queue items for the project
- project registry or primary repo metadata mismatch
- local branch differing from the registered default branch

Operator workflow:

- run the readable report first
- inspect JSON when wiring future automation or tests
- make only safe local docs/data corrections
- use the review as input to M104 batch planning

## M102 Queue Dependency and Completion Locking

M102 hardens local queue sequencing and evidence checks. It does not execute Codex, local LLMs, Ollama, documentation agents, GitHub, `gh`, external agents, patches, workflows, or automatic dispatch.

Inspect queue locks:

    python -m aresforge inspect-queue-consistency --project-id aresforge

Inspect as JSON:

    python -m aresforge inspect-queue-consistency --project-id aresforge --format json

Dependency fields:

- `dependencies`
- `depends_on`
- `blocked_by`

Completion evidence fields:

- `completion_requires`
- `evidence_required`

Blocked behavior:

- start is blocked when dependency or blocked-by items are missing, not done, or missing required completion review/evidence
- completion is blocked when dependencies are unresolved
- completion is blocked when explicit evidence requirements such as `tests_run`, `changed_files`, `commit_hash`, `validation_summary`, or `evidence_note` are missing
- consistency inspection reports dependency locks, completion locks, missing evidence, and next safe action without mutating the queue

Operator workflow:

- inspect consistency before starting or completing sensitive queue items
- resolve upstream items and capture review/validation evidence first
- start only when readiness is `ready`
- complete only with commit, validation summary, review evidence, and any explicit evidence requirements
- treat M101 approval records as manual review state only; approval does not override M102 locks

Historical completed queue items remain valid unless explicit future requirements are added to those items.

## M101 Human Approval Gate UI/Data Contract

M101 records local operator approval state for dispatch artifacts and dry-run outputs. It is a data contract only: approval never executes Codex, local LLMs, Ollama, documentation agents, GitHub, `gh`, external agents, patches, workflows, or queue advancement.

Create a pending review gate:

    python -m aresforge create-dispatch-approval-gate --item-id <item_id> --artifact-type <type>

Create with artifact metadata and JSON output:

    python -m aresforge create-dispatch-approval-gate --item-id <item_id> --artifact-type <type> --artifact-path <path> --dispatch-lane <lane> --reviewer <name> --format json

Inspect one gate:

    python -m aresforge inspect-dispatch-approval-gate --approval-id <approval_id>

List gates for an item:

    python -m aresforge inspect-dispatch-approval-gate --item-id <item_id> --format json

Update approval status:

    python -m aresforge update-dispatch-approval-gate --approval-id <approval_id> --status approved_for_manual_handoff --review-notes "Reviewed for manual handoff only."

Supported statuses:

- `pending_review`
- `approved_for_manual_handoff`
- `rejected`
- `needs_revision`

Required checklist defaults:

- operator reviewed dispatch or dry-run output
- artifact matches the selected dispatch lane
- local-only boundary confirmed
- `execution_allowed=false` confirmed
- no automatic handoff or execution confirmed
- review notes recorded before status change

Operator workflow:

- inspect or generate the M97-M100 dispatch artifact or dry-run output
- create a local approval gate
- review the checklist and artifact path
- update status and notes
- use `approved_for_manual_handoff` only for manual operator handoff review
- wait for future milestones before any execution or apply path

M102 will add dependency/completion locking hardening around future workflows. M101 only records human approval state.

## M100 Documentation Agent Dry-Run Review Workflow

M100 validates documentation-agent dry-run readiness from M97 plans. It is dry-run only and never executes a documentation agent or mutates documentation.

Inspect the dispatch plan first:

    python -m aresforge inspect-queue-dispatch-plan --item-id <item_id>
    python -m aresforge inspect-queue-dispatch-plan --item-id <item_id> --format json

Validate a readable documentation dry-run to console:

    python -m aresforge validate-documentation-agent-dry-run --item-id <item_id>

Generate JSON:

    python -m aresforge validate-documentation-agent-dry-run --item-id <item_id> --format json

Write a local dry-run artifact file:

    python -m aresforge validate-documentation-agent-dry-run --item-id <item_id> --output artifacts/documentation_agent/dry_runs/<item_id>.md

Overwrite only with explicit force:

    python -m aresforge validate-documentation-agent-dry-run --item-id <item_id> --output artifacts/documentation_agent/dry_runs/<item_id>.md --force

M100 only reports ready when the M97 plan has:

- `selected_lane: documentation_agent_dry_run`
- `local_only: true`
- `execution_allowed: false`
- no blocked reasons

M100 blocks for:

- `codex_prompt_artifact`
- `local_llm_advisory`
- `local_llm_coding_draft`
- `human_only_manual`
- any plan with blocked reasons
- any plan where `local_only` is not true
- any plan where `execution_allowed` is not false

Operator workflow:

- inspect dispatch plan
- validate documentation-agent dry-run
- review source docs, expected updates, stale-doc checks, reconciliation scope, and validation expectations
- approve any future documentation apply path only in a later milestone
- keep later documentation changes in the existing queue completion evidence process

M100 boundaries:

- no documentation-agent execution
- no documentation mutation
- no local LLM or Ollama invocation
- no Codex execution
- no GitHub API, `gh`, issues, PRs, workflows, or network calls
- no external agents
- no patch application
- no automatic queue start, completion, dispatch, or next-item execution
- dry-run output must preserve `execution_allowed=false`

## M99 Local LLM Advisory Execution Dry-Run Validator

M99 validates local LLM advisory dry-run readiness from M97 plans. It is dry-run only and never calls Ollama or executes a local model.

Inspect the dispatch plan first:

    python -m aresforge inspect-queue-dispatch-plan --item-id <item_id>
    python -m aresforge inspect-queue-dispatch-plan --item-id <item_id> --format json

Validate a readable dry-run to console:

    python -m aresforge validate-local-llm-advisory-dry-run --item-id <item_id>

Generate JSON:

    python -m aresforge validate-local-llm-advisory-dry-run --item-id <item_id> --format json

Write a local dry-run artifact file:

    python -m aresforge validate-local-llm-advisory-dry-run --item-id <item_id> --output artifacts/local_llm_advisory/dry_runs/<item_id>.md

Overwrite only with explicit force:

    python -m aresforge validate-local-llm-advisory-dry-run --item-id <item_id> --output artifacts/local_llm_advisory/dry_runs/<item_id>.md --force

M99 only reports ready when the M97 plan has:

- `selected_lane: local_llm_advisory`
- `local_only: true`
- `execution_allowed: false`
- no blocked reasons

M99 blocks for:

- `codex_prompt_artifact`
- `local_llm_coding_draft`
- `documentation_agent_dry_run`
- `human_only_manual`
- any plan with blocked reasons
- any plan where `local_only` is not true
- any plan where `execution_allowed` is not false

Operator workflow:

- inspect dispatch plan
- validate local LLM advisory dry-run
- review dry-run output
- approve future advisory artifact/run only in a later milestone
- keep later advisory output in the existing queue completion evidence process

M99 boundaries:

- no Ollama API calls
- no local model execution
- no Codex execution
- no documentation-agent execution
- no GitHub API, `gh`, issues, PRs, workflows, or network calls
- no external agents
- no patch application
- no automatic queue start, completion, dispatch, or next-item execution
- dry-run output must preserve `execution_allowed=false`

## M98 Codex Prompt Dispatch Artifact Generator v1

M98 generates local Codex prompt dispatch artifacts from M97 plans. It is manual/operator-gated and never executes Codex.

Inspect the dispatch plan first:

    python -m aresforge inspect-queue-dispatch-plan --item-id <item_id>
    python -m aresforge inspect-queue-dispatch-plan --item-id <item_id> --format json

Generate a readable prompt artifact to console:

    python -m aresforge generate-codex-dispatch-artifact --item-id <item_id>

Generate JSON:

    python -m aresforge generate-codex-dispatch-artifact --item-id <item_id> --format json

Write a local artifact file:

    python -m aresforge generate-codex-dispatch-artifact --item-id <item_id> --output artifacts/codex_prompt_dispatch/generated/<item_id>.txt

Overwrite only with explicit force:

    python -m aresforge generate-codex-dispatch-artifact --item-id <item_id> --output artifacts/codex_prompt_dispatch/generated/<item_id>.txt --force

M98 only generates when the M97 plan has:

- `selected_lane: codex_prompt_artifact`
- `local_only: true`
- `execution_allowed: false`
- no blocked reasons

M98 blocks without prompt text for:

- `local_llm_advisory`
- `local_llm_coding_draft`
- `documentation_agent_dry_run`
- `human_only_manual`
- any plan with blocked reasons
- any plan where `local_only` is not true
- any plan where `execution_allowed` is not false

Operator workflow:

- inspect dispatch plan
- generate Codex prompt artifact
- review artifact locally
- manually copy/paste into Codex only after approval
- paste final Codex results back into the existing queue completion evidence process

M98 boundaries:

- no Codex execution
- no Ollama or local LLM invocation
- no documentation-agent execution
- no GitHub API, `gh`, issues, PRs, workflows, or network calls
- no external agents
- no patch application
- no automatic queue start, completion, dispatch, or next-item execution
- generated artifacts must clearly preserve `execution_allowed=false`

## M97 Queue-to-Agent Dispatch Plan Contract

M97 is completed locally and recorded in the queue as `done`.

Inspect one local queue item and build an advisory dispatch plan:

    python -m aresforge inspect-queue-dispatch-plan --item-id m97-queue-to-agent-dispatch-plan-contract

Inspect the same plan as JSON:

    python -m aresforge inspect-queue-dispatch-plan --item-id m97-queue-to-agent-dispatch-plan-contract --format json

The M97 plan payload includes:

- `item_id`, `title`, `status`, `project_id`, `repo_id`, and `milestone`
- `selected_lane`, `routing_confidence`, and `lane_selection_reason`
- `planned_artifact_intent`
- `approval_gates`
- `blocked_reasons`
- `next_safe_action`
- `local_only: true`
- `execution_allowed: false`

Supported lanes:

- `codex_prompt_artifact`
- `local_llm_advisory`
- `local_llm_coding_draft`
- `documentation_agent_dry_run`
- `human_only_manual`

Operator gates before any future dispatch:

- select and review the queue item explicitly
- review the dispatch plan and confirm the lane
- review the planned artifact intent
- confirm local-only boundaries
- run required local validation when implementation occurs
- record review evidence before queue completion
- use a later explicit approval gate before Codex, local LLM, documentation-agent apply mode, or any other execution path

M97 warnings:

- M97 does not generate the full Codex prompt; M98 owns that future artifact.
- M97 does not execute Codex, Ollama, local LLMs, documentation agents, external agents, GitHub API, `gh`, network calls, workflows, patches, queue completion, or next-item execution.
- If confidence is low, the item is missing, or requirements are unclear, the safe lane is `human_only_manual`.

## M96 Post-Sprint Planning and Prioritization

M96 is local planning and reconciliation only. It remains `proposed` in the local queue after M97 seeding.

Required review commands for this milestone:

    python -m aresforge inspect-local-project-report
    python -m aresforge inspect-local-queue-agent-summary
    python -m aresforge inspect-project-queue --project-id aresforge
    python -m aresforge inspect-sprint-batch-report --format json
    python -m aresforge generate-handoff-package

M96 queue status:

- M96 was not present before the post-sprint review.
- M96 is now represented locally as `m96-post-sprint-planning-and-prioritization`.
- Do not create GitHub issues for this local-only planning item unless a future explicit project contract changes that boundary.

Operator rules:

- use M96 to review reports, reconcile docs, and choose the next local milestone batch
- do not execute Codex, Ollama, local LLMs, GitHub CLI, GitHub API, external agents, issues, PRs, workflows, daemons, watchers, or schedulers
- do not apply generated patches or model output automatically
- do not start M97 or any later item automatically

Recommended next batch after M96:

- M97 Queue-to-Agent Dispatch Plan Contract
- M98 Codex Prompt Dispatch Artifact Generator v1
- M99 Local LLM Advisory Execution Dry-Run Validator
- M100 Documentation Agent Dry-Run Review Workflow
- M101 Human Approval Gate UI/Data Contract
- M102 Queue Dependency and Completion Locking Hardening
- M103 AresForge Self-Managed Project Seed Review
- M104 Operator Batch Planner v1
- M105 Post-M96 Documentation Reconciliation

## M95 Final Overnight Sprint Reconciliation

M95 is documentation reconciliation only. It does not add a runtime command.

Recommended final review commands:

    python -m aresforge inspect-local-project-report
    python -m aresforge inspect-local-queue-agent-summary
    python -m aresforge inspect-project-queue --project-id aresforge
    python -m aresforge generate-handoff-package
    python -m aresforge inspect-sprint-batch-report --format json

Operator rules:

- use the reports to review the completed M81-M95 sprint posture
- seed any follow-up milestone manually after reviewing the final handoff and sprint batch report
- do not treat documentation reconciliation as approval to run Codex, invoke local LLMs, apply patches, complete unrelated queue items, or start the next item automatically
- do not use GitHub API, `gh`, issues, PRs, workflows, daemon, watcher, scheduler, or external workflow behavior

## M94 Overnight Sprint Batch Report

Inspect the current local sprint batch using the default recent commit window:

    python -m aresforge inspect-sprint-batch-report --format json

Inspect a batch since a known baseline commit:

    python -m aresforge inspect-sprint-batch-report --since-commit <commit> --format json

Optionally write a local report artifact:

    python -m aresforge inspect-sprint-batch-report --commit-count 20 --output artifacts/reports/m94-sprint-batch.json

Payload highlights:

- `commit_window`
- `items_completed`
- `validation_evidence`
- `dispatch_runs`
- `queue_posture`
- `unresolved_warnings`
- `next_recommended_milestone`
- `safe_next_actions`
- `safety_boundary`

Operator rules:

- use the report for local review and handoff only
- inspect readiness manually before starting any next queue item
- do not execute Codex or local LLMs from report output
- do not use GitHub API, `gh`, issues, PRs, workflows, daemon, watcher, scheduler, or external workflow behavior

## M93 Operator Handoff Package v2

Generate a read-only operator handoff package:

    python -m aresforge generate-handoff-package

Optionally write a local handoff artifact:

    python -m aresforge generate-handoff-package --output artifacts/handoff/m93-handoff.md --force

Payload highlights:

- `handoff_package_version`
- `current_head`
- `recent_commits`
- `queue_v2_summary`
- `active_or_ready_items`
- `recovered_dispatch_summary`
- `model_routing_summary`
- `safe_command_suggestions`
- `next_safe_actions`
- `safety_boundary`

Operator rules:

- use the handoff package as continuation context only
- choose and start any next queue item manually after readiness inspection
- do not execute Codex or local LLMs from handoff output
- do not treat model routing summary as execution approval
- do not use GitHub API, `gh`, issues, PRs, workflows, daemon, watcher, scheduler, or external workflow behavior

## M92 Documentation Reconciliation Plan Generator

Generate a read-only documentation reconciliation plan:

    python -m aresforge plan-doc-reconciliation --format json

Optionally write the plan to a local artifact path:

    python -m aresforge plan-doc-reconciliation --format json --output artifacts/doc-reconciliation/m92-plan.json --force

Payload highlights:

- `source_docs`
- `changed_source_docs`
- `queue_items`
- `recent_commits`
- `stale_or_missing_sections`
- `recommended_doc_updates`
- `safety_boundary`
- `next_safe_action`

Operator rules:

- use the generated plan as manual documentation guidance only
- do not treat the plan as permission to rewrite documentation automatically
- do not invoke local LLMs or Codex from this command
- do not complete queue items or start another item from plan output
- do not use GitHub API, `gh`, issues, PRs, workflows, daemon, watcher, scheduler, or external workflow behavior

## M91 Documentation Agent v1 Contract

Inspect the documentation agent contract:

    python -m aresforge inspect-documentation-agent-contract --format json

Contract reference:

    docs/architecture/DOCUMENTATION_AGENT_CONTRACT.md

Payload highlights:

- `agent_scope`
- `source_docs_to_update`
- `evidence_required_before_docs_are_updated`
- `plan_mode`
- `future_gated_apply_mode`
- `safety_boundary`

Operator rules:

- use plan mode for documentation reconciliation guidance only
- update source-of-truth docs manually unless a future explicit apply gate exists
- require validation evidence before documentation is updated
- do not apply model output to docs automatically
- do not complete queue items or start another item from documentation agent output
- do not use GitHub API, `gh`, issues, PRs, workflows, daemon, watcher, scheduler, or external workflow behavior

## M90 Hub Routing Dashboard Data Contract

Inspect routing dashboard data through the local Hub API:

    GET /api/local-queue/routing-dashboard
    GET /api/local-queue/routing-dashboard?project_id=aresforge&status=proposed

Payload highlights:

- `items[].item_id`
- `items[].status`
- `items[].risk`
- `items[].task_size`
- `items[].recommended_engine`
- `items[].recommended_lane`
- `items[].confidence_score`
- `items[].validation_burden`
- `items[].warnings`
- `items[].blockers`

Operator rules:

- use this endpoint for dashboard display and routing review only
- do not treat routing dashboard data as approval to execute prompts or invoke models
- do not mutate queue state, complete items, or start another item from this endpoint
- do not use GitHub API, `gh`, issues, PRs, workflows, daemon, watcher, scheduler, or external workflow behavior

## M89 Model Usage and Token Accounting Report

Inspect local model usage and token accounting:

    python -m aresforge inspect-model-usage-report --format json

Optionally write the report to a local artifact path:

    python -m aresforge inspect-model-usage-report --format json --output artifacts/model_usage/m89-report.json

Payload highlights:

- `codex_dispatch.token_usage`
- `codex_dispatch.model_provider_reasoning_effort_counts`
- `missing_usage_metadata`
- `local_llm_advisory`
- `local_coding_drafts`
- `safety_boundary`

Operator rules:

- use the report for local routing and cost review only
- treat unavailable token usage and extraction errors as accounting metadata to improve later runs
- do not invoke providers or models from this report
- do not mutate queue state, complete items, or start another item from report output
- do not use GitHub API, `gh`, issues, PRs, workflows, daemon, watcher, scheduler, or external workflow behavior

## M88 Human-Gated Patch Application Contract

Inspect the patch application contract:

    python -m aresforge inspect-human-gated-patch-application-contract --format json

Payload highlights:

- `patch_artifact_structure`
- `operator_approval_requirements`
- `pre_apply_safety_gates`
- `post_apply_validation_requirements`
- `safety_boundary`
- `next_safe_action`

Operator rules:

- treat generated local coding draft patches as non-applied and non-authoritative
- require explicit approval before any future manual patch application path
- require safety gates before any manual application and validation after any manual application
- do not apply patches automatically
- do not mutate repository files automatically
- do not complete queue items or start another item from patch artifacts
- do not use GitHub API, `gh`, issues, PRs, workflows, daemon, watcher, scheduler, or external workflow behavior

## M87 Local Coding Draft Artifact Mode

Generate a local coding draft prompt artifact without invoking a model:

    python -m aresforge prepare-local-coding-draft --item-id <item_id> --format json

Explicitly request local draft output only when the operator wants a local Ollama run:

    python -m aresforge prepare-local-coding-draft --item-id <item_id> --run --format json

Payload highlights:

- `prompt_path`
- `draft_path`
- `metadata_path`
- `draft_contract`
- `safety_boundary`
- `boundary_confirmations`
- `next_safe_action`

Operator rules:

- treat generated draft output as non-applied and non-authoritative
- use artifact-only mode by default
- use `--run` only for explicit local operator-gated draft output
- do not apply generated patches automatically
- do not mutate repository files automatically
- do not complete queue items or start another item from draft output
- do not use GitHub API, `gh`, issues, PRs, workflows, daemon, watcher, scheduler, or external workflow behavior

## M86 Routing Confidence Scoring

Inspect routing confidence for one queue item:

    python -m aresforge inspect-llm-decision-matrix --item-id <item_id> --format json

Payload highlights:

- `routing_confidence.score`
- `routing_confidence.confidence_level`
- `routing_confidence.recommended_lane`
- `routing_confidence.rationale`
- `routing_confidence.warnings`
- `routing_confidence.scores`
- `routing_confidence.factors`

Operator rules:

- treat confidence scores as advisory routing metadata only
- compare Codex, local LLM advisory, local coding draft, and manual-only lane scores before choosing a handoff
- do not treat a high score as approval to execute prompts or mutate files
- do not complete queue items or start another item from scoring output
- do not use GitHub API, `gh`, issues, PRs, workflows, daemon, watcher, scheduler, or external workflow behavior

## M85 Local LLM Advisory Run Artifact

Generate a local advisory prompt artifact without invoking a model:

    python -m aresforge prepare-local-llm-advisory-run --item-id <item_id> --format json

Explicitly request local advisory output only when the operator wants a local Ollama run:

    python -m aresforge prepare-local-llm-advisory-run --item-id <item_id> --run --format json

Payload highlights:

- `prompt_path`
- `response_path`
- `metadata_path`
- `provider_model_metadata`
- `safety_boundary`
- `boundary_confirmations`
- `next_safe_action`

Operator rules:

- treat generated prompts and responses as advisory artifacts only
- use artifact-only mode by default
- use `--run` only for explicit local operator-gated advisory output
- do not apply model output to repository files automatically
- do not complete queue items or start another item from model output
- treat unavailable local LLM states as safe, non-blocking operator metadata
- do not use GitHub API, `gh`, issues, PRs, workflows, daemon, watcher, scheduler, or external workflow behavior

## M84 Ollama Health Check and Model Inspection

Inspect the local Ollama provider without generation:

    python -m aresforge test-ollama
    python -m aresforge inspect-ollama-health --format json

Payload highlights:

- `available`
- `provider`
- `endpoint`
- `models`
- `error_summary`
- `next_safe_action`
- `model_inspection_contract`
- `safety_boundary`

Operator rules:

- treat the output as local provider availability/model metadata only
- expect Ollama offline states to return `available: false` without blocking normal project readiness
- call only the local `/api/tags` endpoint for model listing
- do not send prompts, invoke generation, or call chat/completion endpoints in this milestone
- do not apply provider output to repo files or queue state
- do not start another queue item automatically
- do not use GitHub API, `gh`, issues, PRs, workflows, daemon, watcher, scheduler, or external workflow behavior

## M83 Local LLM Provider Contract

Inspect the local LLM provider contract:

    python -m aresforge inspect-local-llm-provider-contract --format json

Payload highlights:

- `initial_provider_target`
- `provider_base_url`
- `request_timeout_seconds`
- `health_check_contract`
- `model_selection_contract`
- `safety_boundary`

Operator rules:

- treat the provider contract as read-only metadata
- use Ollama as the initial local provider target
- use only the explicit health check path for local provider availability checks
- do not call generation/chat/completion endpoints from contract inspection
- do not apply provider output to repo files automatically
- do not execute prompts automatically unless a separate explicit operator-gated command allows it
- do not use GitHub API, `gh`, issues, PRs, workflows, daemon, watcher, scheduler, or external workflow behavior

## M82 Self-Managed AresForge Test Run

Inspect AresForge as its own local managed project:

    python -m aresforge inspect-managed-project --project-id aresforge --format json
    python -m aresforge inspect-local-project-readiness --project-id aresforge --format json
    python -m aresforge inspect-local-project-report --format json
    python -m aresforge inspect-local-queue-agent-summary --format json
    python -m aresforge inspect-project-queue --project-id aresforge --format json

Report highlights:

- `self_managed_readiness_summary`
- `m81_status`
- `m82_status`
- `recovered_dispatch_run_summary`
- `readiness_flows_checked`
- `safety_boundary_confirmations`

Operator rules:

- treat the self-managed report as read-only validation evidence
- do not start another queue item automatically
- do not run unattended multi-item execution
- do not use GitHub API, `gh`, issues, PRs, workflows, daemon, watcher, scheduler, or external workflow behavior
- capture queue completion evidence only after explicit operator review

## M81 Local LLM Advisory/Coding Lane Prototype

Inspect the local LLM advisory/coding lane readiness for one queue item:

    python -m aresforge inspect-local-llm-advisory-lane-readiness --item-id m81-local-llm-advisory-coding-lane-prototype --format json

Payload highlights:

- `recommended_engine`
- `recommended_lane`
- `selected_model`
- `provider_metadata`
- `decision_matrix_summary`
- `advisory_plan`
- `safety_boundary`

Operator rules:

- treat the output as advisory planning metadata only
- do not treat readiness inspection as provider invocation or prompt dispatch
- keep local LLM output manually reviewed and non-mutating
- do not complete a queue item until review and validation evidence are captured
- do not start the next queue item automatically

## M79.4 Codex Dispatch Recovery and Windows argv Hardening

Recover a partially failed or stale local Codex dispatch run:

    python -m aresforge recover-codex-dispatch-run --run-id <run_id> --recovery-note "operator reviewed partial run state" --format json

Payload highlights:

- `dispatch_state`
- `recovery_required`
- `recovery.previous_dispatch_state`
- `recovery.recovery_note`
- `queue_completion_allowed: false`
- `automatic_next_item_execution_allowed: false`

Windows command guidance:

- Prefer repeated `--command-arg` values for Codex dispatch commands on Windows.
- If `--command` is used, quoted Windows paths and quoted arguments are parsed with Windows-aware argv handling.
- Recovery does not approve dispatch, run Codex, complete queue items, or start another item.

## M80 LLM Decision Matrix v2

Inspect the advisory routing decision for one queue item:

    python -m aresforge inspect-llm-decision-matrix --item-id m80-llm-decision-matrix-v2 --format json

Use workflow preparation to generate a Prompt Builder artifact that includes the M80 decision payload:

    python -m aresforge prepare-queue-item-dispatch --item-id m80-llm-decision-matrix-v2 --target codex --format json

Payload highlights:

- `work_mode`
- `task_sizing`
- `risk_classification`
- `engine_recommendation`
- `lane_recommendation`
- `model_profile_selection`
- `validation_burden`
- `safety_gating`
- `routing_decision`

Operator rules:

- treat the decision matrix as advisory metadata only
- do not treat a Codex recommendation as dispatch approval
- use the M78 `approve-codex-dispatch` and `run-codex-dispatch` commands separately when Codex dispatch is intentionally approved
- do not invoke a local LLM from decision matrix inspection
- do not complete a queue item until review and validation evidence are captured

## M79.3 Codex Run Token Usage Capture

After a Codex dispatch run, inspect token usage metadata:

    python -m aresforge inspect-codex-dispatch-run --run-id <run_id> --format json

Token usage behavior:

- the runner parses a Codex CLI transcript footer formatted as `tokens used` followed by a numeric total
- comma-separated totals such as `221,534` are normalized to an integer
- successful extraction stores `token_usage.available: true`, `source: codex_cli_transcript_footer`, `total_tokens`, `raw`, and optional model/provider/reasoning-effort metadata
- missing or malformed footers store `token_usage.available: false` with a clear `extraction_error`
- older run states without `token_usage` still inspect successfully and report unavailable token usage

Operator rules:

- token usage capture is accounting metadata only
- dispatch remains explicitly operator-gated
- inspect output does not complete queue items
- do not mark a queue item complete until review and validation evidence are captured
- do not start a next queue item automatically

## M79.2 Single-Item Ready-to-Codex Automation

Run exactly one manually ready queue item through the local Codex workflow:

    python -m aresforge run-single-ready-codex-queue-item --item-id <item_id> --approved-by local_operator --approval-phrase "APPROVE CODEX DISPATCH" --command-arg codex --validation-command "python -m pytest tests/test_codex_dispatch_runner.py tests/test_local_project_queue.py tests/test_cli.py" --validation-command "git diff --check" --format json

When `--item-id` is omitted, the command selects only if exactly one queue item is `ready` and startable. If zero or multiple ready/startable items exist, it fails safely. If `--item-id` is supplied, only that item is considered, and it must be ready/startable.

Workflow behavior:

- prepares or reuses the prompt artifact through `prepare-queue-item-dispatch`
- requires the M78 approval phrase before Codex dispatch
- runs the operator-provided Codex command with the hardened stdin prompt handoff
- runs explicit validation commands
- attempts an implementation `git add`, `git commit`, and `git push`
- records queue completion evidence and closes only the selected item after validation and implementation commit/push pass
- attempts a second git commit/push for queue evidence
- never starts a next queue item

Failure behavior:

- Codex failure leaves the item in progress and records recovery evidence.
- Validation failure leaves the item in progress and records recovery evidence.
- Implementation commit/push failure leaves the item in progress and records recovery-required evidence.
- Queue evidence commit/push failure reports recovery required; inspect local git status and push/commit manually if needed.
- The command does not use GitHub API, `gh`, issues, PRs, workflows, or external workflow execution.

## M79.1 Codex CLI Windows Runner Hardening

For Windows Codex dispatch runs, prefer the reviewed prompt artifact workflow:

    python -m aresforge prepare-queue-item-dispatch --item-id <item_id> --target codex --format json
    python -m aresforge approve-codex-dispatch --item-id <item_id> --approved-by local_operator --approval-phrase "APPROVE CODEX DISPATCH" --format json
    python -m aresforge run-codex-dispatch --item-id <item_id> --run-id <run_id> --command-arg codex --format json

Runner behavior:

- `run_state.json` reads tolerate UTF-8 BOMs.
- subprocess stdout and stderr are captured as bytes and decoded with UTF-8-sig plus replacement handling before local files are written.
- the full reviewed prompt artifact is sent to the subprocess over UTF-8 stdin, preserving multi-line prompt bodies.
- run-state metadata reports `stdin_prompt_handoff` and `output_decoding` for operator review.

Windows sandbox note:

- Codex may be able to edit repository files while `.git` writes are blocked by sandbox permissions.
- If commit or push fails because `.git` is inaccessible, keep the validated changes in the worktree and have the operator run `git status`, `git diff --check`, `git add`, `git commit`, and `git push` manually from an approved shell.
- Do not mark the queue item complete until review and validation evidence are captured.

## M78.5 Operator Workflow Compression and Prompt Builder Agent Contract

Prepare a queue item for operator-reviewed Codex dispatch without dispatching:

    python -m aresforge prepare-queue-item-dispatch --item-id m79-queue-blocking-and-sequencing-enforcement --target codex --format json

Start the item only when readiness passes and the operator explicitly chooses that step:

    python -m aresforge prepare-queue-item-dispatch --item-id m78-5-operator-workflow-compression-prompt-builder-contract --target codex --start-if-ready --format json

Payload highlights:

- `prompt_artifact_path` points to the generated local prompt artifact
- `dispatch_contract_summary` reports the Codex dispatch contract without approving or running it
- `operator_approval_required` remains true for Codex
- `dispatch_allowed` remains false in the preparation command
- `automatic_next_item_execution_allowed` remains false
- `queue_completion_allowed` remains false

Operator rules:

- review the generated prompt artifact before handoff
- use `approve-codex-dispatch` and `run-codex-dispatch` separately if Codex dispatch is desired
- do not treat preparation as approval, dispatch, validation, or completion
- queue completion still requires review and validation evidence
- no GitHub API, `gh`, issues, PRs, workflows, external workflow execution, or GitHub mutation occurs

Next recommended milestone:

- M79 - Queue Blocking and Sequencing Enforcement.

## M78 Operator-Gated Codex CLI Dispatch Prototype

Approve exactly one local dispatch run:

    python -m aresforge approve-codex-dispatch --item-id m78-operator-gated-codex-cli-dispatch-prototype --approved-by local_operator --approval-phrase "APPROVE CODEX DISPATCH" --format json

Run the approved dispatch with an explicit operator-provided command:

    python -m aresforge run-codex-dispatch --item-id m78-operator-gated-codex-cli-dispatch-prototype --run-id <run_id> --command "python -c \"print('codex dispatch smoke')\"" --format json

On Windows, the safer smoke form is repeated command arguments:

    python -m aresforge run-codex-dispatch --item-id m78-operator-gated-codex-cli-dispatch-prototype --run-id <run_id> --command-arg python --command-arg=-c --command-arg "print('codex dispatch smoke')" --format json

Inspect or list local run records:

    python -m aresforge inspect-codex-dispatch-run --run-id <run_id> --format json
    python -m aresforge list-codex-dispatch-runs --format json

Run-state files are local:

- `.aresforge/codex_dispatch/runs/<run_id>/run_state.json`
- `.aresforge/codex_dispatch/runs/<run_id>/prompt.txt`
- `.aresforge/codex_dispatch/runs/<run_id>/stdout.txt`
- `.aresforge/codex_dispatch/runs/<run_id>/stderr.txt`
- `.aresforge/codex_dispatch/runs/<run_id>/artifacts/`

Operator rules:

- approval phrase must exactly match `APPROVE CODEX DISPATCH`
- only one active run is allowed at a time
- commands are never inferred automatically; the operator supplies `--command`
- successful command completion leaves the run in `review_required`
- dispatch output does not complete the queue item
- review evidence and validation evidence are required before queue completion
- no automatic next-item execution is allowed
- no GitHub API, `gh`, issues, PRs, workflows, external workflow execution, or GitHub mutation capability is added
- no local LLM execution expansion is performed

M78.5 follow-on note:

- The Prompt Builder Agent / Prompt Architect Agent now prepares prompt artifacts for operator review. It must not execute prompts, call Codex, invoke local LLMs, mutate files, or advance queue items automatically.

Next recommended milestone:

- M79 - Queue Blocking and Sequencing Enforcement.

## M77 Codex CLI Dispatch Contract

Status: Completed locally on `main`.

Operator workflow:

1. Confirm the target local queue item exists.
2. Inspect the contract with `python -m aresforge inspect-codex-dispatch-contract --item-id m77-codex-cli-dispatch-contract --format json`.
3. Optionally prepare a dry-run/no-execute contract payload with `python -m aresforge prepare-codex-dispatch-dry-run --item-id m77-codex-cli-dispatch-contract --format json`.
4. If writing an artifact, keep `--output` under `.aresforge/codex_dispatch/contracts` and use `--force` only when intentionally overwriting.
5. Review `safety_gates`, `blockers`, `expected_run_state_shape`, and `boundary_confirmations`.

Contract interpretation:

- `dry_run_only: true` means M77 cannot dispatch Codex.
- `dispatch_allowed: false` means no run may start from this milestone.
- `codex_cli_invocation_allowed: false` means AresForge must not invoke Codex CLI.
- `automatic_next_item_execution_allowed: false` means no follow-on queue item can run automatically.
- `operator_approval_required: true` records the future M78 gate; approval is not requested or consumed in M77.
- command previews are review-only strings and are not executable by this milestone.

Operator safety notes:

- M77 does not invoke Codex CLI.
- M77 does not implement M78 dispatch.
- M77 does not start a run.
- M77 does not mutate queue item status.
- M77 does not call local LLMs, Codex, agents, GitHub, `gh`, issues, PRs, workflows, external services, or external workflow execution.
- local LLM remains local-only, advisory-only, operator-gated, prototype-scoped, and non-mutating.

Future M78 gates:

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

Current operator workflow:

1. Run `python -m aresforge seed-aresforge-self-project --format json` to idempotently seed or refresh the self-managed project.
2. Add `--set-active` only when you explicitly want AresForge selected as the active local project.
3. Inspect the self-managed project with `python -m aresforge inspect-managed-project --project-id aresforge --format json`.
4. Inspect the self-managed repo with `python -m aresforge inspect-managed-repo --project-id aresforge --repo-id aresforge-main --format json`.
5. Inspect seeded work with `python -m aresforge inspect-project-queue --project-id aresforge --format json`.
6. Review the proposed M77-M82 queue items before starting anything.

Operator safety notes:

- no GitHub API, `gh`, GitHub issues, GitHub PRs, GitHub workflows, or GitHub mutation from the app
- no automatic Codex execution, Codex CLI dispatch, prompt dispatch, agent execution, external workflow execution, or unattended multi-item execution
- self-seed does not start queue items
- Codex high-value lane remains prompt-generation/operator-handoff only
- M76 does not add Codex dispatch
- M76 does not add local LLM execution expansion
- local LLM execution remains local-only, advisory-only, operator-gated, prototype-scoped, and non-mutating
- local LLM output must never automatically mutate repository files, queue state, project state, GitHub, `gh`, Codex, agents, commits, pushes, or workflows
- normal `git commit` and `git push origin main` are allowed only after local validation, smoke checks, clean diff check, and explicit prompt instruction

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

- M77 - Codex CLI Dispatch Contract.

## M75 Source-of-Truth Documentation and Roadmap Reconciliation

Status: Completed on `main` in commit `7088204`.

## M74 Hub UX Stabilization Pass

Status: Completed locally on `main`.

Operator workflow:

1. Use Queue as the local operations review surface for queue lifecycle, prompt previews, audit log, artifact registry, Operator Run History, and AI Action Review Panel.
2. Treat controls labeled inspect, review, preview, copy, or generate prompt as local operator handoff/review actions only.
3. Use Copy Prompt Pack Preview to copy generated prompt-pack text manually after review.
4. Review AI Action Review Panel safety status, gate status, no automatic execution, no repo mutation, and next safe action labels before acting outside the Hub.
5. Treat local LLM provider/model status as prototype configuration evidence only, not production execution approval.

Operator safety notes:

- Hub UX stabilization did not add backend execution behavior
- prompt-pack previews and AI review surfaces remain manual/operator handoff only
- no automatic execution, Codex execution, Codex CLI invocation, local LLM repo mutation, GitHub behavior, `gh`, workflow behavior, or external service behavior was introduced
- local LLM output remains advisory-only and cannot mutate repo files automatically

Recommended next milestone:

- M75 - Source-of-Truth Documentation and Roadmap Reconciliation.

## M73 Prompt Pack Quality and Routing Improvements

Status: Completed locally on `main`.

Operator workflow:

1. Open Queue in the Hub.
2. Use Agent Prompt Pack Generator for selected queue items or status filters.
3. Leave routing metadata enabled when routing-aware handoff context is useful.
4. Review lane guidance, advisory model/engine recommendation, task sizing, validation expectations, and final response requirements.
5. Copy/paste prompt text manually into the operator-approved tool only after review.

Operator safety notes:

- generated prompt packs are manual handoff artifacts only
- prompt-pack generation does not execute Codex, Codex CLI, local LLMs, agents, prompts, GitHub, `gh`, workflows, or external services
- Codex high-value lane remains prompt-generation/operator-handoff only
- local LLM advisory lane remains advisory-only and local LLM output cannot mutate repo files automatically
- model/engine recommendations are advisory metadata only and do not select or invoke a provider

Recommended next milestone:

- M74 - Hub UX Stabilization Pass.

## M72 Local LLM Provider Configuration Hardening

Status: Completed locally on `main`.

Operator workflow:

1. Read local LLM configuration through `GET /api/local-llm/environment`.
2. Review `provider_availability_status`, `provider_configuration_status`, `provider_execution_mode`, `local_model_profiles`, and `fallback_behavior`.
3. Update provider/model settings only through the existing local environment contract.
4. Run `POST /api/local-llm/health-check` only as an explicit operator action.
5. Treat health results as provider/model availability evidence only, not execution approval.

Provider state guidance:

- `configured`: provider settings are syntactically usable; run the explicit health check before any prototype use
- `missing_configuration`: provider or local URL/model configuration is incomplete
- `unavailable`: configured local provider could not be reached by the explicit health check
- `unsupported`: provider or URL is not allowed for local LLM workflows
- `disabled`: provider is intentionally set to `none`
- `prototype_only`: execution is enabled only for the M62 explicit operator-gated prototype

Operator safety notes:

- local LLM usage remains local-only, advisory-only, operator-gated, and prototype-scoped
- model profile metadata is advisory and does not prove installation
- fallback model names are review metadata only and are never selected automatically
- health checks do not send prompts, run inference, execute agents, execute Codex, call GitHub, call `gh`, run workflows, or mutate repo files

Recommended next milestone:

- M73 - Prompt Pack Quality and Routing Improvements.

## M71 Operator-Facing AI Action Review Panel

Status: Completed locally on `main`.

Operator workflow:

1. Open Queue in the Hub.
2. Use the AI Action Review Panel.
3. Optionally filter by project id, item id, action type, artifact type, or limit.
4. Review safety status, gate status, blocked action details, artifact references, audit references, run-history timeline entries, queue AI-adjacent metadata, and next safe operator action.
5. Treat the panel as local review evidence only.

Operator safety notes:

- the panel is read-only and review-focused
- it does not execute agents, Codex, Codex CLI, local LLMs, GitHub actions, `gh`, issues, PRs, workflows, external services, or repo mutations
- it does not apply local LLM or Codex output to repo files
- local LLM output remains local-only, advisory-only, operator-gated, and prototype-scoped
- Codex high-value lane remains prompt-generation/operator-handoff only

Recommended next milestone:

- M72 - Local LLM Provider Configuration Hardening.

## M70 Local AI Operations Verification Sweep

Status: Completed locally on `main`.

Operator workflow notes:

1. Continue using the existing explicit local operator actions for local LLM preview/execution, Codex high-value prompt generation, prompt packs, routing, audit log, artifact registry, and Operator Run History.
2. Treat the M70 updates as verification/stabilization only: no new execution lane, external integration, or automatic mutation path was added.
3. When reviewing Operator Run History, use the visible safety status, gate status, execution state, and non-mutation flags to confirm that entries are local evidence only.
4. Treat GitHub/`gh`/issue/PR/workflow/Codex execution/agent execution/repo mutation representations as policy-blocked unless a future approved milestone explicitly changes the contract.

Operator safety notes:

- local LLM execution remains local-only, advisory-only, operator-gated, and prototype-scoped
- local LLM output is never applied to repo files, queue state, project state, GitHub, `gh`, Codex, agents, commits, pushes, or workflows automatically
- Codex high-value lane remains prompt-generation/operator-handoff only and never runs Codex
- no GitHub API, `gh`, GitHub mutation, issues, PRs, workflows, automatic Codex execution, automatic agent execution, external workflow execution, or automatic repo mutation was introduced

Recommended next milestone:

- M71 - Operator-Facing AI Action Review Panel.

## M69 Local AI Operations Hardening

Status: Completed locally on `main`.

Operator workflow notes:

1. Continue using local LLM preview/execution, Codex high-value prompt generation, prompt packs, routing, audit log, artifact registry, and Operator Run History through the existing explicit operator actions.
2. When an AI-adjacent action is blocked, inspect `blocked_action`, `blocked_reason_category`, `gate_status`, blockers, and `next_safe_action`.
3. Treat `policy_blocked` as non-overridable for GitHub/`gh`, issue/PR/workflow, Codex execution, automatic agent execution, and automatic repo-mutation paths.
4. Treat `missing_operator_approval` and `gate_blocked` as instructions to use only the existing explicit local operator-gated workflows.
5. Treat artifact registry and run-history records as local evidence only; they do not approve, execute, apply, delete, post, commit, push, or mutate anything.

Operator safety notes:

- local LLM execution remains local-only, advisory-only, operator-gated, and prototype-scoped
- local LLM output is never applied to repo files automatically
- Codex high-value lane remains prompt-generation/operator-handoff only and never runs Codex
- no GitHub API, `gh`, GitHub mutation, issues, PRs, workflows, automatic Codex execution, automatic agent execution, external workflow execution, or automatic repo mutation was introduced

Recommended next milestone:

- M70 completed Local AI Operations Verification Sweep.

## M68 Local AI Operations Closeout Reconciliation

Status: Completed locally on `main`.

Current supported local AI workflows:

1. Configure project AI settings and inspect the agent/engine registry.
2. Add or inspect queue routing metadata from the one canonical local queue.
3. Review routing decision matrix output and routed queue views as advisory filtered views.
4. Generate routing-aware prompt packs.
5. Configure local LLM environment and run the explicit local health check.
6. Generate local LLM prompt previews for locally routed items.
7. Use the M62 local LLM execution prototype only with explicit operator gate confirmation and local provider checks.
8. Generate Codex high-value prompts as copy/paste operator handoffs only.
9. Review execution audit log, AI artifact registry, and Operator Run History for local evidence.

Operator safety notes:

- these local AI workflows perform no GitHub API calls, `gh` calls, issue/PR/workflow activity, or GitHub mutation
- no automatic Codex execution, no Codex CLI invocation, and no automatic agent execution are implemented
- local LLM execution is prototype-only, local-only, advisory-only, and operator-gated
- local LLM and Codex outputs are never applied to repo files automatically
- routed queue views are filtered views, not separate queues

Recommended next milestone:

- M69 - Local AI Operations Hardening.

## M67 Operator Run History Panel

Status: Completed locally on `main`.

Operator workflow:

1. Open the Operator Run History panel in Queue.
2. Optionally filter by project id, item id, action type, artifact type, or limit.
3. Review recent timeline entries across audit events and generated artifact records.
4. Use the timeline for local evidence and operator orientation only.

Timeline fields:

- timestamp
- kind: `audit` or `artifact`
- project id and item id when available
- action type and artifact type when available
- outcome, summary, artifact path, executed state, and execution-allowed state

Operator safety notes:

- the panel is read-only
- no execution, apply, delete, GitHub, `gh`, Codex run, local LLM, agent, workflow, issue, or PR controls are available
- audit log records action outcomes
- artifact registry records generated local artifact files
- run history combines both into a single operator-facing timeline

Recommended next milestone:

- M68 - Local AI Operations Closeout Reconciliation.

## M66 AI Artifact Registry

Status: Completed locally on `main`.

Operator workflow:

1. Generate local artifacts through existing prompt pack, local LLM preview/result, Codex high-value prompt, or handoff workflows.
2. Open the AI Artifact Registry panel in Queue.
3. Optionally filter by item id, artifact type, source action, engine, exists state, or limit.
4. Review artifact type, item id, local path, exists state, and timestamp.
5. Treat the registry as local discovery/evidence only; it does not approve, execute, delete, or apply artifacts.

Artifact types:

- `prompt_pack`
- `handoff`
- `local_llm_prompt_preview`
- `local_llm_execution_result`
- `codex_high_value_prompt`
- `report`
- `audit_export`
- `other`

Operator safety notes:

- registering artifacts records metadata only and does not overwrite artifact content
- missing files are shown as `exists: false`
- checksum is local-only when the file exists
- the execution audit log records action outcomes; the artifact registry records generated local artifact files
- no Codex, local LLM, agent, GitHub, `gh`, workflow, or external execution is performed by the registry

Recommended next milestone:

- M67 - Operator Run History Panel.

## M65 AI Action Safety Gate

Status: Completed locally on `main`.

Operator workflow:

1. Use existing local LLM, Codex prompt, prompt-pack, and routing tools as before.
2. For a direct gate preview, POST an action request to `/api/ai-action-safety-gate`.
3. Review `decision`, `allowed`, `execution_allowed`, blockers, warnings, and `next_safe_action`.
4. Treat the gate as decision/reporting evidence only; it does not approve work by itself or execute anything.

Supported action types:

- `local_llm_prompt_preview`
- `local_llm_execute`
- `codex_high_value_prompt`
- `prompt_pack_generate`
- `routing_recommendation`
- `routing_metadata_update`

Operator safety notes:

- Codex execution and GitHub/`gh` mutation are always blocked.
- local LLM execution still requires local engine routing and explicit operator gate confirmation.
- high/critical risk local LLM execution requires operator override.
- prompt previews and Codex prompt generation are preview-only with `execution_allowed: false`.
- routing metadata updates require explicit operator action confirmation.
- M65 adds no new execution behavior and does not expand M62.

Recommended next milestone:

- M66 - AI Artifact Registry.

## M64 Execution Audit Log

Status: Completed locally on `main`.

Operator workflow:

1. Use the existing local LLM health check, prompt preview, local LLM prototype, Codex high-value prompt, prompt pack, and routing tools as before.
2. Open the Execution Audit Log panel in Queue.
3. Optionally filter by item id, action type, engine, or limit.
4. Review action type, item id, engine, outcome, executed state, and timestamp.
5. Treat the audit log as local evidence only; it does not approve or execute work.

What is logged:

- local LLM health checks
- local LLM prompt previews
- local LLM dry runs, blocked attempts, and advisory execution outputs
- Codex high-value prompt generation
- prompt-pack generation
- routing metadata updates

What is not logged:

- full prompt text
- full LLM response text
- secrets or secret-like strings
- GitHub/`gh` activity, because none is performed by these local workflows

Operator safety notes:

- audit logging does not run Codex, local LLMs, agents, GitHub, `gh`, issues, PRs, workflows, or external services
- audit logging does not apply AI output or mutate repo files
- M62 local LLM execution remains explicitly operator-gated

Recommended next milestone:

- M65 - AI Action Safety Gate.

## M63 Codex CLI High-Value Lane

Status: Completed locally on `main`.

Operator workflow:

1. Select a queue item in Queue lifecycle controls.
2. Confirm routing metadata or task context makes the item Codex-worthy.
3. Use Generate Codex High-Value Prompt.
4. Review eligibility, blockers, warnings, and `execution_allowed: false`.
5. Copy the prompt manually into Codex only if the operator chooses to run Codex outside AresForge.
6. Validate Codex output locally before applying commit/push instructions.
7. Optionally provide a local artifact path; existing files are not overwritten unless Force overwrite is enabled.

Eligibility:

- `codex_cli` engine, `high_value_codex` lane, high/critical risk, high complexity, high validation burden, high-value affected area, `codex_only`/`high_confidence`, or operator override

Operator safety notes:

- prompt generation does not run Codex
- no Codex CLI process is invoked
- no GitHub API, `gh`, issues, PRs, workflows, or GitHub mutation is used
- no repository file is changed from Codex output by AresForge
- Codex lane output is advisory copy/paste text only
- M62 local LLM execution stays behind its explicit operator gate

Recommended next milestone:

- M64 - Execution Audit Log.

## M62 Operator-Gated Local LLM Execution Prototype

Status: Completed locally on `main`.

Operator workflow:

1. Configure `.aresforge/local_llm_environment.json` for local `ollama`, local provider URL, model names, `execution_enabled: true`, and `operator_gate_required: true`.
2. Run Local LLM Health Check and confirm provider/model availability.
3. Confirm the queue item is routed to `local_reasoning_llm` or `local_coding_llm`.
4. Generate Local LLM Prompt Preview.
5. In Queue, use Prototype: Run Local LLM.
6. Leave Dry run enabled to validate gates without calling the provider.
7. For real execution, explicitly check Confirm explicit operator gate.
8. Use Operator override only for high/critical risk or manual policy cases the operator accepts.
9. Optionally provide a local result artifact path; existing files are not overwritten unless Force overwrite is enabled.

Operator safety notes:

- dry run does not call Ollama
- real execution calls only the configured local `ollama` provider
- response text is advisory only
- AresForge does not apply changes, edit files, complete queue items, commit, push, run Codex, call GitHub, call `gh`, run agents, or run workflows
- non-local provider URLs are blocked
- `codex_cli` and unrouted items are blocked

Recommended next milestone:

- M63 - Codex CLI High-Value Lane.

## M61 Local LLM Prompt Preview

Status: Completed locally on `main`.

Operator workflow:

1. Confirm the queue item has routing metadata recommending `local_reasoning_llm` or `local_coding_llm`.
2. Confirm `.aresforge/local_llm_environment.json` has provider/model configuration.
3. Open Queue and select the item in lifecycle controls.
4. Use Local LLM Prompt Preview to generate copy/paste preview text.
5. Optionally provide an output path for a local artifact; existing files are not overwritten unless Force overwrite is enabled.
6. Review blockers, warnings, routing metadata, local-only rules, validation expectations, and the final response format before doing anything manually outside AresForge.

Operator safety notes:

- preview generation does not call Ollama
- preview generation does not run inference or send prompts
- preview generation does not execute local LLMs, Codex CLI, agents, GitHub, `gh`, workflows, pushes, or external services
- `codex_cli` routes and unrouted items are blocked for local LLM preview
- `manual_only` project policy requires operator override before preview
- generated text tells the downstream local LLM not to claim execution when only reviewing or planning

Follow-up:

- M62 added Operator-Gated Local LLM Execution Prototype.

## M60 Codex CLI Model Profile Contract

Status: Completed locally on `main`.

Operator workflow:

1. Read Codex CLI model profiles with `GET /api/codex-cli/model-profiles`.
2. Optionally update allowed model names and role preferences with `POST /api/codex-cli/model-profiles`.
3. Keep `execution_enabled` false and `operator_gate_required` true.
4. Treat profiles as routing and prompt-lane configuration only.

Operator safety notes:

- Codex CLI model profiles are configuration only
- model names do not execute or verify Codex availability
- no Codex CLI command is run
- no prompt is executed
- no agent, GitHub, `gh`, workflow, push, or external service is used
- High-Value Codex Lane prompt generation exists, but Codex execution remains unimplemented

Recommended next milestone:

- M63 - Codex CLI High-Value Lane.

## M59 Local LLM Health Check

Status: Completed locally on `main`.

Operator workflow:

1. Configure local LLM environment with `GET /api/local-llm/environment` and `POST /api/local-llm/environment`.
2. Explicitly run `POST /api/local-llm/health-check`.
3. Review provider reachability and available model names.
4. Confirm whether configured reasoning and coding models appear in the local model list.

Operator safety notes:

- health check is explicitly invoked only
- provider URL must be local
- provider `ollama` checks only `/api/tags`
- no prompt is sent
- no inference is run
- no local LLM generation occurs
- no Codex, agent, GitHub, `gh`, workflow, queue mutation, prompt execution, or external service is used

Follow-up:

- M61 added Local LLM Prompt Preview.
- M62 added Operator-Gated Local LLM Execution Prototype.

## M58 Local LLM Environment Contract

Status: Completed locally on `main`.

Operator workflow:

1. Read local LLM configuration with `GET /api/local-llm/environment`.
2. Optionally update provider/model placeholders with `POST /api/local-llm/environment`.
3. Keep `execution_enabled` false and `operator_gate_required` true.
4. Treat `health_check_enabled` as future configuration only until M59.

Operator safety notes:

- local LLM settings are configuration only
- model names do not prove installation
- no Ollama call is made
- no health check is performed yet
- no prompt is executed
- no routing, local LLM, Codex, agent, GitHub, `gh`, workflow, push, or external service is used

Recommended next milestone:

- M59 - Local LLM Health Check.

## M57 Prompt Pack Routing Integration

Status: Completed locally on `main`.

Operator workflow:

1. Open Queue.
2. Use Agent Prompt Pack Generator.
3. Leave Include routing metadata enabled for routed prompt-pack output.
4. Optionally enable Group by routing metadata and choose agent lane, engine, model, risk, complexity, or status grouping.
5. Generate the prompt pack and copy/paste the preview manually.
6. Optionally write a local artifact path; existing files are not overwritten unless Force overwrite is enabled.

Operator safety notes:

- prompt packs are local artifacts/previews only
- routing metadata is advisory and non-executing
- unrouted items are labeled as manual routing required
- Codex CLI recommendations do not execute Codex
- local LLM recommendations do not execute local LLMs
- prompt-pack generation does not start, complete, route, or execute queue items
- prompt-pack generation does not call GitHub, `gh`, workflows, push, or external services

Recommended next milestone:

- M58 - Local LLM Environment Contract.

## M56 Routed Queue Views

Status: Completed locally on `main`.

Operator workflow:

1. Open Queue.
2. Use the Routed Queue Views panel.
3. Choose optional status, agent lane, engine, risk, complexity, and grouping filters.
4. Use Load Routed Queue Views.
5. Review grouped counts and item summaries as read-only context.

Operator safety notes:

- routed views read the one canonical local queue
- routed views do not create separate queue storage
- routed views do not mutate queue items
- unrouted items are included by default
- loading routed views does not generate prompt packs or execute prompts
- loading routed views does not call Codex, local LLMs, agents, GitHub, `gh`, workflows, push, or external services
- prompt-pack routing integration remains future work

Recommended next milestone:

- M57 - Prompt Pack Routing Integration.

## M55 Project AI Settings UI

Status: Completed locally on `main`.

Operator workflow:

1. Open Projects.
2. Select or confirm the active project.
3. Use Load Project AI Settings to view the current local settings contract.
4. Choose project AI mode, available engines, disabled engines, default engine, optional default model, operator override setting, and notes.
5. Use Save Project AI Settings to update the local file-backed contract.
6. Review validation, warnings, blockers, and `next_safe_action`.

Operator safety notes:

- settings are routing preferences only
- invalid settings are rejected and displayed in the validation panel
- saving settings does not execute routing
- saving settings does not call Codex, local LLMs, agents, GitHub, `gh`, workflows, push, prompt generation, or external services
- model management and executable engine configuration remain future work

Recommended next milestone:

- M56 - Routed Queue Views.

## M54 Routing Decision Matrix v1

Status: Completed locally on `main`.

Operator workflow:

1. Select or enter a queue item in Queue lifecycle controls.
2. Optionally enter risk level, complexity level, affected files, and validation burden.
3. Use Recommend Routing to preview routing metadata.
4. Review blockers, warnings, recommendation reason, and `execution_allowed: false`.
5. Use Apply Routing Metadata only when the operator explicitly wants to write metadata to the queue item.

Operator safety notes:

- recommendation preview is read-only
- applying a recommendation writes M53 metadata only
- no prompt is generated or executed by routing recommendation
- no Codex, agents, local LLMs, GitHub, `gh`, workflows, push, queue split, or external service is used
- `manual_only` project mode requires operator decision instead of automatic engine recommendation

Recommended next milestone:

- M55 - Project AI Settings UI.

## M53 Queue Routing Metadata Contract

Status: Completed locally on `main`.

Operator workflow:

1. Inspect a queue item from Queue detail.
2. Review routing metadata fields as advisory context only.
3. Optionally update metadata through `POST /api/local-queue/items/{item_id}/routing-metadata`.
4. Treat metadata as future routing input; do not execute it.

Supported metadata values:

- agent lanes: `architect_planner`, `coding`, `reviewer_validator`, `documentation`, `test`, `local_operator_assistant`, `high_value_codex`
- engines: `local_reasoning_llm`, `local_coding_llm`, `codex_cli`
- risk levels: `low`, `medium`, `high`, `critical`, `unknown`
- complexity levels: `low`, `medium`, `high`, `unknown`

Operator safety notes:

- one canonical local queue remains the source of truth
- routing metadata is local-only, file-backed, and non-executing
- metadata does not compute routing decisions
- metadata does not generate or execute prompts
- metadata does not call Codex, agents, local LLMs, GitHub, `gh`, workflows, push, or external services
- routed queue views and decision matrix behavior remain future work

Recommended next milestone:

- M54 - Routing Decision Matrix v1.

## M52 Agent and Engine Registry Contract

Status: Completed locally on `main`.

Operator workflow:

1. Inspect the registry with `GET /api/agent-engine-registry` or the operator helper.
2. Review the available future agent lanes and engines.
3. Use the registry only as future routing reference data.
4. Do not treat registry entries as permission to execute agents or models.

Agent lane keys:

- `architect_planner`
- `coding`
- `reviewer_validator`
- `documentation`
- `test`
- `local_operator_assistant`
- `high_value_codex`

Engine keys:

- `local_reasoning_llm`
- `local_coding_llm`
- `codex_cli`

Operator safety notes:

- registry inspection is local-only and read-only
- all lanes are routing-only and non-executing
- all engines are non-executing and require future operator gates
- Codex CLI is represented as a future engine placeholder only
- the registry does not call Codex, agents, local LLMs, routing, GitHub, `gh`, workflows, push, or external services
- the registry does not update queue routing metadata

Recommended next milestone:

- M53 - Queue Routing Metadata Contract.

## M51 Project AI Settings Contract

Status: Completed locally on `main`.

Operator workflow:

1. Confirm or create a local project through the existing Project Factory flow.
2. Read project AI settings through the Hub API or operator helper.
3. Update settings only when choosing a project-level routing preference contract.
4. Review validation output, blockers, warnings, and `next_safe_action`.
5. Treat the settings as future routing input only.

Supported modes:

- `balanced`
- `local_only`
- `codex_only`
- `cost_saver`
- `high_confidence`
- `manual_only`

Supported engines:

- `local_reasoning_llm`
- `local_coding_llm`
- `codex_cli`

Operator safety notes:

- settings are local-only and file-backed
- settings do not execute routing
- settings do not invoke Codex, agents, local LLMs, GitHub, `gh`, workflows, push, or external services
- settings do not change queue routing metadata
- no Hub settings UI was added in M51

Recommended next milestone:

- M52 - Agent and Engine Registry Contract.

## M50 Handoff Generator

Status: Completed locally on `main`.

Operator workflow:

1. Open Handoff.
2. Enter an optional project id, next milestone, next instruction, and optional local output path.
3. Choose whether to include queue, reports, and evidence summaries.
4. Generate the local project handoff.
5. Copy the generated markdown into the next operator chat, or review the optional local artifact if one was explicitly requested.

Operator safety notes:

- handoff generation is local-only and operator-gated
- default behavior is read-only
- optional artifact output writes only to a local file and refuses to overwrite unless `force=true`
- it does not call GitHub, `gh`, agents, Codex, local LLMs, routing, workflows, push, or external services
- it builds on Reports v1 and M48 progress rollup state

Recommended next milestone:

- M51 - Project AI Settings Contract.

## M49 Reports v1

Status: Completed locally on `main`.

Operator workflow:

1. Open Reports.
2. Review Reports v1 summary cards for projects, queue, evidence, closeout eligibility, and closed/completed work.
3. Review queue counts, active project progress rollup, local-only boundaries, limitations, blockers, warnings, and `next_safe_action`.
4. Continue to Queue, Projects, or the next local handoff workflow only after choosing an explicit operator action.

Operator safety notes:

- Reports v1 is read-only and local-only
- it does not mutate queue/project state
- it does not execute prompts, Codex, agents, local LLMs, routing, GitHub, `gh`, workflows, push, or external services
- it does not add PDF/CSV/export workflow complexity beyond existing in-page JSON text behavior
- routing implementation remains future work after the workflow/reporting sequence

Recommended next milestone:

- M50 - Handoff Generator.

## M48 Project Progress Rollup

Status: Completed locally on `main`.

Operator workflow:

1. Select or confirm the active project in Projects.
2. Review Project Progress Rollup counts for queue status, type/lane, evidence capture, closeout eligibility, and closed/completed work.
3. Use the returned `next_safe_action`, blockers, and warnings to choose the next operator-gated action.
4. Continue to Queue for evidence capture, closeout, or intake as needed.

Operator safety notes:

- the rollup is read-only and local-only
- it does not generate Reports v1 output
- it does not mutate queue/project state
- it does not generate or execute prompts
- it does not call Codex, agents, local LLMs, routing, GitHub, `gh`, workflows, push, or external services
- future routing metadata is a not-implemented placeholder only

Recommended next milestone:

- M49 - Reports v1.

## M47 Queue Item Closeout Workflow

Status: Completed locally on `main`.

Operator workflow:

1. Start or keep a queue item in `in_progress`.
2. Capture completion evidence with evidence summary, validation results, and diff check result.
3. Review evidence and provide a closeout summary.
4. Use Close Out Queue Item to explicitly close the item locally.
5. Inspect queue summary and local project report for updated progress.

Operator safety notes:

- closeout uses existing `done` status
- closeout preserves captured evidence and records local closeout metadata
- closeout does not generate or execute prompts
- closeout does not call Codex, agents, local LLMs, routing, GitHub, `gh`, workflows, push, or external services
- routing implementation remains future work

Recommended next milestone:

- M48 - Project Progress Rollup.

## M46 Completion Evidence Capture

Status: Completed locally on `main`.

Operator workflow:

1. Select or enter a queue item id in the Queue lifecycle area.
2. Use Capture Completion Evidence to paste local validation evidence.
3. Record validation commands, validation results, smoke checks, diff check result, changed files, known commit/push state, and operator notes.
4. Review the returned `closeout_eligible` and `next_safe_action`.

Operator safety notes:

- evidence capture records local queue metadata only
- evidence capture does not complete the queue item
- evidence capture does not run validation commands
- evidence capture does not run Codex, agents, local LLMs, routing, GitHub actions, or external workflows
- closeout remains a separate future workflow

Recommended next milestone:

- M47 - Queue Item Closeout Workflow.

## M45 Local Hub End-to-End Operator Workflow

Status: Completed locally on `main`.

Validated operator workflow:

1. Inspect the Hub dashboard summary.
2. Confirm active project context.
3. Create or inspect a local queue item.
4. Open local queue item details.
5. Check local readiness.
6. Generate a local-only prompt pack.
7. Inspect the local project report.
8. Inspect the local queue agent summary.

Operator safety notes:

- prompt packs are copy/paste-ready advisory output only
- no prompt is automatically executed
- prompt-pack generation does not start queue items
- prompt-pack generation does not complete queue items
- routing implementation remains future work
- local LLM execution, Codex execution, and real agent execution remain unimplemented
- the queue remains one canonical local queue

Recommended next milestone:

- M46 - completion evidence capture for local operator workflow closeout.

## M44A Agent LLM Routing Strategy Operator Note

Status: Completed locally on `main`.

Reference:

- `docs/architecture/AGENT_LLM_ROUTING_STRATEGY.md`

Operator meaning:

- operators can generate M43 prompt packs today
- those prompt packs are local-only grouped prompts for manual copy/paste use
- routed prompt packs are future work
- AresForge does not yet assign generated prompts to an engine/model or execute Codex/local LLMs

Future routing intent:

- future flow: Project -> Agent Lane -> Allowed Engines/Models -> Routing Decision Matrix -> Prompt Pack Output
- future project AI modes include `balanced`, `local_only`, `codex_only`, `cost_saver`, `high_confidence`, and `manual_only`
- future engines include `local_reasoning_llm`, `local_coding_llm`, and `codex_cli`
- the local queue should remain one canonical queue with routed views derived from metadata

Current boundaries:

- no real agent execution
- no automatic Codex execution
- no local LLM execution
- no LLM/model routing execution
- no GitHub API, no `gh`, no GitHub mutation from the app

## M43 Agent Prompt Pack Generator

Status: Completed locally on `main`.

Operator workflow:

- In Queue -> Local Queue Lifecycle, use `Generate Agent Prompt Pack`.
- Optional inputs:
  - specific queue item ids (comma-separated)
  - status filter list (comma-separated)
  - optional output path and overwrite force toggle
- Output:
  - prompt-pack summary (count, groups, path)
  - copy/paste-ready prompt-pack preview text

Route and behavior:

- `POST /api/local-queue/prompt-pack`
- local-only prompt generation artifact/preview
- no queue lifecycle execution is started automatically
- operator must manually copy prompts into external AI tools if desired

Boundaries:

- no Codex execution from Hub
- no real agent execution
- no LLM/model routing
- no GitHub API, no `gh`, no GitHub mutation
- no external service calls

## M42 Queue Item Detail Panel

Status: Completed locally on `main`.

Operator visibility updates:

- Queue section now includes a read-only Queue Item Detail Panel
- use `View Details` on a queue card to load item detail and readiness context
- panel shows:
  - item basics (id/title/status/type/priority)
  - project/repo/source/tags/timestamps
  - description
  - requested outcome, acceptance notes, validation notes (when captured)
  - readiness summary/blockers/warnings (when available)

Operational boundaries remain unchanged:

- detail panel is advisory/read-only
- no automatic lifecycle mutations
- no auto-start and no auto prompt generation
- no GitHub/`gh`/GitHub mutation
- no agent/model execution behavior

## M41 Active Project Task Intake v2

Status: Completed locally on `main`.

Operator intake flow updates:

- Active Project Task Intake now captures:
  - title
  - summary/details
  - type
  - priority
  - tags
  - source (defaults to `active_project_workspace`)
  - requested outcome
  - acceptance notes
  - validation notes
- successful intake result now shows:
  - queue item id
  - status
  - active project association
  - source
  - next safe action

Behavior remains local-only and gated:

- no auto-start of queue items
- no auto-generated Codex prompt
- no GitHub/`gh`/GitHub mutation actions
- no agent/model execution behavior

## M40 Dashboard Milestone Closeout And Docs Reconciliation

Status: Completed locally on `main`.

Operator-facing reconciliation outcome:

- dashboard docs now match completed M35-M39 behavior
- validation/smoke baseline for dashboard closeout is explicitly recorded
- no runtime behavior was changed during this milestone

What operators should treat as current dashboard contract:

- summary endpoint: `GET /api/dashboard/summary`
- Home dashboard cards/panels are read-only/advisory
- refresh is manual only (no auto-refresh/background polling)
- loading, empty, and error states are explicit and expected
- deep links route to existing sections only (Workspace/Projects/Queue/Repos/Reports)
- queue/agent lane drilldowns are advisory and non-executing

Current module ownership relevant to dashboard behavior:

- `src/aresforge/hub/static/app.js`
- `src/aresforge/hub/static/js/sections/home.js`
- `src/aresforge/hub/static/js/sections/queue.js`
- `src/aresforge/hub/static/js/sections/projects.js`
- `src/aresforge/hub/static/js/sections/repos.js`
- `src/aresforge/hub/static/js/sections/reports.js`

Boundary guarantees (unchanged):

- local-only, file-backed, operator-gated
- read-only/advisory dashboard posture
- no GitHub API, no `gh`, no GitHub issues/PRs/workflows mutation
- no real agent execution
- no Codex execution from Hub app
- no LLM/model routing or invocation

Dashboard closeout validation baseline:

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
## M36 Home Dashboard Operator Note

Home dashboard now uses:

- `GET /api/dashboard/summary`

Operator-visible read-only panels now include:

- total/active project summary
- queue totals and status counts
- advisory agent lanes
- repo availability/status/warnings
- blockers and warnings
- next safe action

Boundary posture is unchanged:

- local-only/read-only/advisory
- no GitHub API calls and no `gh`
- no agent/Codex/model execution
- no LLM/model routing
- no background polling; refresh is manual

## M35 Hub Dashboard Data Contract Operator Note

New local-only read-only Hub endpoint:

- `GET /api/dashboard/summary`

Purpose:

- provide a stable dashboard summary payload for Hub Home data consumption
- surface advisory local project/queue/agent-lane/repo state without mutation

Boundaries:

- no GitHub API calls
- no `gh`
- no local/cloud/Codex model execution
- no mutation side effects

Scope guard:

- dashboard UI cards/panels are deferred to M36.

## Local Ollama Planning References (Documentation-Only)

AresForge has local Ollama planning documentation for future LLM integration.

Reference documents:

- `docs/operator/OLLAMA_LOCAL_SETUP.md`
- `docs/architecture/LOCAL_LLM_STRATEGY.md`
- `docs/architecture/LLM_TASK_ROUTING_PLAN.md`
- `docs/context/LOCAL_LLM_DECISION_RECORD.md`

Operator reminders:

- do not run both large local models at the same time on the baseline machine
- use `ollama ps` to check loaded models
- use `ollama list` to check installed models and aliases
- use `nvidia-smi` to inspect GPU visibility
- treat local model output as advisory until an explicit operator-approved application workflow exists

## M34 Frontend Modularization Closeout Operator Notes

Status: frontend modularization sequence is closed out and reconciled in docs.

Current frontend contract:

- `src/aresforge/hub/static/index.html` loads `src/aresforge/hub/static/app.js` as `type="module"`.
- `src/aresforge/hub/static/app.js` remains the Hub frontend entrypoint.
- module structure:
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

Validation commands for this contract:

- `python -m pytest tests/test_hub_ui_foundation.py tests/test_hub_project_factory_api.py tests/test_hub_local_queue_lifecycle_api.py tests/test_hub_active_project_api.py tests/test_local_project_factory.py tests/test_local_active_project.py`
- `python -m aresforge inspect-local-queue-agent-summary`
- `python -m aresforge inspect-local-project-report`

Operational boundaries:

- local-first
- file-backed
- operator-gated
- no real agent execution
- no GitHub mutation
- no network execution beyond existing local Hub API behavior

Next recommended milestone:

- M35 - Hub Dashboard Data Contract And Read-Only Metrics
- read-only metrics only: total projects, active project summary, queue counts by status, advisory agent lane counts, and repo status summary from existing local inspection outputs

## M17 Local Queue Execution-Prep Lifecycle

Purpose:

- prepare, start, hand off, and close out local queue work without GitHub mutation or automatic agent/model execution

Command set:

- `python -m aresforge add-local-queue-item --title <title> [--description <text>] [--type <type>] [--priority <priority>] [--target-area <area>] [--acceptance-criteria <text>]...`
- `python -m aresforge inspect-local-queue-item-readiness --item-id <item_id>`
- `python -m aresforge start-local-queue-item --item-id <item_id>`
- `python -m aresforge generate-local-queue-item-codex-prompt --item-id <item_id> [--output <path>] [--commit-message <text>] [--force]`
- human runs Codex manually using the generated prompt
- `python -m aresforge complete-local-queue-item --item-id <item_id> --commit-hash <hash> --validation-summary <text> [--evidence-note <text>] [--tests-run <text>]... [--changed-files <path>]... [--artifact-path <path>]... [--completed-by <actor>]`

Lifecycle notes:

- readiness is read-only and explains blockers before start
- start mutates only the local queue item state to `in_progress`
- prompt generation is local-only and does not execute Codex
- completion requires validation evidence and records it locally in the queue item
- completion does not run tests automatically and does not verify the commit remotely

Boundary guarantees:

- local-first and file-backed
- no GitHub API calls
- no `gh` calls
- no GitHub issues, PRs, workflow activity, or GitHub mutation
- no automatic Codex execution
- no agent execution
- no model routing/invocation
- no push

## M23 Hub Frontend Modularization Foundation

Operator impact:

- no new commands were added
- Hub page behavior remains the same, but the frontend now loads `app.js` as a browser-native module
- shared frontend helpers now live under `src/aresforge/hub/static/js/core/`
- workspace quick actions no longer risk duplicate binding

Boundary guarantees remain unchanged:

- local-only frontend refactor
- no GitHub API calls
- no `gh` calls
- no network calls or external dependencies added
- no automatic Codex, agent, or model execution

## M24 Hub Home And Workspace Section Modules

Operator impact:

- no new commands were added
- Home dashboard and Workspace behavior remain the same, but their frontend logic now lives in dedicated section modules
- `src/aresforge/hub/static/app.js` remains the module entrypoint loaded by the Hub page
- workspace quick actions still bind once and remain local-only

Boundary guarantees remain unchanged:

- local-only frontend refactor
- no GitHub API calls
- no `gh` calls
- no new network calls or external dependencies
- no automatic Codex, agent, or model execution

## M25 Hub Queue Section Module

Operator impact:

- no new commands were added
- Queue behavior remains the same, but queue summary/list rendering and queue-only actions now live in a dedicated section module
- `src/aresforge/hub/static/app.js` remains the module entrypoint loaded by the Hub page
- local queue lifecycle flows still behave the same and remain local-only

Boundary guarantees remain unchanged:

- local-only frontend refactor
- no GitHub API calls
- no `gh` calls
- no new network calls or external dependencies
- no automatic Codex, agent, or model execution

## M26 Hub Projects And Repos Section Modules

Operator impact:

- no new commands were added
- Projects and Repos behavior remain the same, but their rendering/loading and section-owned actions now live in dedicated section modules
- `src/aresforge/hub/static/app.js` remains the module entrypoint loaded by the Hub page
- project-factory and other higher-coupling flows remain local-only and continue to behave the same

Boundary guarantees remain unchanged:

- local-only frontend refactor
- no GitHub API calls
- no `gh` calls
- no new network calls or external dependencies
- no automatic Codex, agent, or model execution

## M27 Hub Reports Section Module

Operator impact:

- no new commands were added
- Reports behavior remains the same, but report rendering/loading/export helpers and Reports-owned actions now live in a dedicated section module
- `src/aresforge/hub/static/app.js` remains the module entrypoint loaded by the Hub page
- other local-only control-plane flows continue to behave the same

Boundary guarantees remain unchanged:

- local-only frontend refactor
- no GitHub API calls
- no `gh` calls
- no new network calls or external dependencies
- no automatic Codex, agent, or model execution

## M21 Active Project Workspace: Operator Flow & Safety

Summary:

- The Hub includes a polished Active Project Workspace that surfaces the current active project, workspace actions, and empty states for operators.
- Workspace quick-actions are labeled "(local-only)" and are operator-driven: refresh workspace/report, continue task intake (focus intake UI), open queue, and select project.

Operator guidance and constraints:

- Workspace actions are local-only and do not trigger agent/model execution or GitHub mutation.
- Use the workspace to prepare and plan work; generate local Codex prompts for manual human-run sessions as needed.
- Focused regression tests (`tests/test_active_project_workspace.py`) validate workspace API payloads for empty and active states.


## M16 Local Validation Closeout

Completed locally on `main` with no push performed.

M16 additions:

- Home dashboard API wiring and read-only UI foundation
- Projects read-only UI foundation
- Queue read-only UI foundation
- Reports read-only UI foundation

Boundary reaffirmation:

- local-first/local-only
- no GitHub API calls
- no `gh` calls
- no GitHub mutation/sync execution
- no agent execution
- no model routing/invocation

Validation commands used:

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

## M14 Source-of-Truth Reconciliation Note

This section captures the current local foundation status after M14 reconciliation work.

State summary:

- M9-M13 were completed, validated, committed, and pushed before this chat.
- M14 local read-model/report additions are now present on local `main` and validated.
- Operating posture remains local-first and direct-on-`main`.

Hard restrictions (unchanged):

- no GitHub API calls
- no `gh` calls
- no GitHub issue/PR mutation for these local summary commands
- no agent execution
- no LLM routing/invocation

M14 read-only command additions:

- `python -m aresforge inspect-local-project-dashboard`
- `python -m aresforge list-local-projects`
- `python -m aresforge inspect-local-project-readiness --project-id <id>`
- `python -m aresforge inspect-local-queue-agent-summary`
- `python -m aresforge inspect-local-project-report`

Targeted validation for this layer:

- `git diff --check`
- `python -m pytest tests/test_roadmap_db_control.py tests/test_config_and_migrations.py tests/test_cli.py`
- `python -m pytest tests/test_local_project_dashboard.py`
- `python -m pytest tests/test_local_project_readiness.py`
- `python -m pytest tests/test_local_queue_agent_summary.py`
- `python -m pytest tests/test_local_project_report.py`

## M46 Operator Note: Project Factory Pipeline And Approval Boundaries

AresForge should now be operated as a local-first project-factory control plane with explicit approval boundaries. The canonical workflow is defined in:

- `docs/architecture/PROJECT_FACTORY_WORKFLOW.md`

Current mission-control foundation on `main`:

- M43 active project support
- M44 active project intake
- M45 active project workbench

Important scope note:

- M43-M45 provide foundational Hub control-plane capability.
- M43-M45 do not yet implement the full end-to-end project-factory loop.

Operator approval boundaries:

- local read-only and planning operations are allowed by default
- local write operations are allowed for local state/artifact/doc updates
- GitHub mutation operations require explicit approved apply boundary
- model/agent execution requires explicit approved execution boundary

## M31 Foundation Reconciliation And Next-Phase Planning

Foundation status:

- AresForge now has a local-first foundation for self-managed operation.
- GitHub is optional/syncable and not mandatory for local planning.
- M26 added handoff package generation.
- M27 added the local project state ledger.
- M28 added plan-only documentation reconciliation.
- M29 added plan-only offline-to-GitHub sync planning.
- M30 added local self-managed milestone lifecycle support.
- M32 added local managed-project registry support for multi-project/multi-repo tracking.
- M33 added local project queue/work tracking for local issue-free planning across projects/repos.
- M35 added local multi-agent orchestration planning.
- M36 added local escalation planning for local LLM/Codex/cloud-advisory/human/blocked paths.
- No new functionality in this foundation batch calls GitHub APIs.
- No new functionality in this foundation batch calls LLM APIs.
- The system is ready to move into multi-project and multi-agent project-management capabilities.

## Next-Phase Roadmap (Planned)

- Local LLM agent handoff profiles.
- Multi-agent orchestration planning.
- Escalation to cloud LLMs.
- Project dashboard and local project management reporting.
- Optional later GitHub sync execution.
- Optional later web dashboard UI.
- Optional later background daemon or scheduler.

## Known Limitations (Current Foundation Batch)

- No production-ready LLM dispatch exists; only the M62 explicit local LLM prototype may call a local provider under operator gates.
- No cloud LLM API integration yet.
- No GitHub sync execution yet.
- Hub now supports M40 local reporting/dashboard/operator workflows, but execution gates/auth/deployment hardening remain future work.
- No cross-machine coordination yet.
- No background daemon/scheduler yet.

## M42 First-Run Bootstrap And Seed Wizard

Purpose:

- Provide a first-run local setup flow for Hub and CLI.
- Initialize missing local state files and seed useful defaults.
- Keep setup local-only and file-backed.

Commands:

- `python -m aresforge inspect-bootstrap-status`
- `python -m aresforge plan-bootstrap`
- `python -m aresforge apply-bootstrap`
- `python -m aresforge apply-bootstrap --seed-sample-work`
- `python -m aresforge serve-hub`

Hub usage:

- Open `http://127.0.0.1:8765`
- Use Bootstrap/Setup to initialize local state.
- Review Projects, Queue, Agents, and Reports after setup.

M42 boundary guarantees:

- local-only and file-backed
- no GitHub API calls
- no `gh` calls
- no GraphQL/REST calls
- no network service calls
- no local/cloud/Codex/ChatGPT/Ollama calls
- no external API calls
- no live GitHub discovery/validation
- future work may add additional repo import/connect flows, but M42 does not perform live GitHub discovery

## M37 AresForge Hub UI Foundation

Purpose:

- Establish the local AresForge Hub foundation as the main local entry point for AresForge.
- Provide a lightweight local server, API shell, and static frontend shell without external dependencies.

Command:

- `python -m aresforge serve-hub [--host <host>] [--port <port>] [--open-browser]`

Command examples:

- `python -m aresforge serve-hub`
- `python -m aresforge serve-hub --port 8765`
- `python -m aresforge serve-hub --open-browser`

Defaults:

- host: `127.0.0.1`
- port: `8765`
- browser auto-open: disabled unless `--open-browser` is supplied

M37 Hub surface:

- local API shell endpoints:
   - `GET /api/health`
   - `GET /api/summary`
   - `GET /api/docs/status`
- local static frontend shell with navigation:
   - Home, Projects, Repos, Queue, Agents, Handoff, Orchestration, Escalation, Reports, Settings
- Home renders local summary data and empty states when optional files are missing.
- Settings shows local-only boundary confirmations.
- non-Home sections are now implemented through M40 for local management/planning/reporting.

Boundary guarantees:

- local-first, local-only command surface
- binds to `127.0.0.1` by default
- no `gh` calls
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

Milestone split after M37:

- M38: full project/repo/queue management screens
- M39: full agent/orchestration/escalation/handoff screens
- M40: completed locally (reporting/dashboard/operator workflow expansion)

## M38 Hub Project, Repo, And Queue Management

M38 adds interactive local Hub project-management screens using file-backed M32/M33 storage.

Quick operator note:

- Start the Hub:
   - `python -m aresforge serve-hub`
- Open:
   - `http://127.0.0.1:8765`
- Use Projects, Repos, and Queue sections for local management.
- Data remains local file-backed.

M38 Hub API endpoints:

- `GET /api/projects`
- `POST /api/projects`
- `GET /api/projects/{project_id}`
- `GET /api/projects/{project_id}/repos`
- `POST /api/projects/{project_id}/repos`
- `GET /api/queue`
- `POST /api/queue`
- `GET /api/queue/{item_id}`
- `PATCH /api/queue/{item_id}`

M38 boundary guarantees:

- local-only command/API/UI surface
- no `gh` calls
- no GitHub API calls
- no network service calls
- no local LLM calls
- no cloud LLM calls
- no Codex/ChatGPT/Ollama calls
- no external API calls
- no agent execution and no live GitHub sync

Remaining scope split:

- M40: completed locally; next work includes guided workflows, optional execution gates, authentication hardening, and controlled sync execution
- authentication and production deployment are not implemented yet

## M39 Hub Agent, Handoff, Orchestration, And Escalation Screens

M39 extends the local Hub with interactive planning-focused workflows on top of M34, M35, and M36.

Quick M39 operator note:

- Start the Hub:
   - `python -m aresforge serve-hub`
- Open:
   - `http://127.0.0.1:8765`
- Use Agents to manage local profiles and handoff targets.
- Use Handoff to preview local handoff content.
- Use Orchestration to generate plan-only agent assignments.
- Use Escalation to generate plan-only local/Codex/cloud/human classification.
- Data remains local file-backed.
- No agents or models are executed.

M39 Hub API endpoints:

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

M39 boundary guarantees:

- local-only command/API/UI surface
- file-backed storage and planning
- orchestration and escalation are plan-only
- no agent execution
- no local/cloud/Codex/ChatGPT/Ollama model execution
- no `gh` calls
- no GitHub API calls
- no network service calls
- no external API calls

Remaining scope split:

- M40: completed locally; next work includes guided workflows, optional execution gates, authentication hardening, and controlled sync execution

## M40 Operator Note

- Start the Hub:
   - `python -m aresforge serve-hub`
- Open:
   - `http://127.0.0.1:8765`
- Use Home for readiness and action center.
- Use Reports for local control-plane reporting.
- Use Settings to review local paths and boundary confirmations.
- Use workflow cards to guide local operations.
- Data remains local file-backed.
- Reports/workflows do not execute agents, models, GitHub sync, or external calls.
- Optional CLI `inspect-project-dashboard` command is deferred as future work; M40 focuses on Hub/API reporting surfaces.
- authentication and production deployment are not implemented yet

## M41 GitHub-Linked Project/Repo Operations (Local-Only)

M41 introduces local GitHub-link identity metadata for managed projects and repos.

Boundary note:

- GitHub links are stored locally.
- M41 does not validate against live GitHub.
- M41 does not call GitHub APIs, `gh`, GraphQL, REST, or any network services.

Register a project with a GitHub URL:

- `python -m aresforge register-managed-project --project-id aresforge-main --name "AresForge" --root-path "C:\Projects\aresforge" --status active --default-branch main --github-url "https://github.com/yoey2112/aresforge" --github-default-branch main --primary-repo-id repo-main`

Register a repo with a GitHub URL and local git inspection:

- `python -m aresforge register-managed-repo --project-id aresforge-main --repo-id repo-main --name "AresForge Main Repo" --path "C:\Projects\aresforge" --role primary --status active --github-url "https://github.com/yoey2112/aresforge.git" --github-default-branch main --inspect-local-git`

Inspect repo GitHub link posture:

- `python -m aresforge inspect-managed-repo-github-link --project-id aresforge-main --repo-id repo-main --inspect-local-git --format json`
- `python -m aresforge inspect-managed-repo-github-link --project-id aresforge-main --repo-id repo-main --format markdown`

Hub usage for GitHub-link metadata:

- Start Hub: `python -m aresforge serve-hub`
- Open `http://127.0.0.1:8765`
- Use Projects screen to set project GitHub URL/owner/repo/default branch and primary repo ID.
- Use Repos screen to set repo GitHub URL/owner/repo/default branch and optionally inspect local git during save.
- Use Repos action `Inspect Local Git Link For Repo ID` for local-only git-link checks.
- Use Home/Reports to review linked/unlinked counts and missing primary repo warnings.

## Final Validation Checklist (Local-Only)

```powershell
$ErrorActionPreference = "Stop"

Set-Location "C:\Projects\aresforge"

Write-Host "== Confirm branch and recent commits ==" -ForegroundColor Cyan
git branch --show-current
git log -n 10 --oneline

Write-Host ""
Write-Host "== Confirm working tree ==" -ForegroundColor Cyan
git status --short

Write-Host ""
Write-Host "== Whitespace validation ==" -ForegroundColor Cyan
git diff --check

Write-Host ""
Write-Host "== Full test suite ==" -ForegroundColor Cyan
python -m pytest

Write-Host ""
Write-Host "== Generate local project state if needed ==" -ForegroundColor Cyan
python -m aresforge init-project-state --force

Write-Host ""
Write-Host "== Inspect project state ==" -ForegroundColor Cyan
python -m aresforge inspect-project-state

Write-Host ""
Write-Host "== Generate handoff package ==" -ForegroundColor Cyan
python -m aresforge generate-handoff-package --output "artifacts\handoff\final-handoff.md" --force

Write-Host ""
Write-Host "== Plan doc reconciliation ==" -ForegroundColor Cyan
python -m aresforge plan-doc-reconciliation --output "artifacts\doc-reconciliation\final-plan.json" --force

Write-Host ""
Write-Host "== Plan GitHub sync locally ==" -ForegroundColor Cyan
python -m aresforge plan-github-sync --output "artifacts\github-sync\final-sync-plan.json" --force

Write-Host ""
Write-Host "== Generate local milestone template ==" -ForegroundColor Cyan
python -m aresforge generate-local-milestone-template --milestone-id "m31-final-validation" --title "M31 Final Validation" --output "artifacts\milestones\m31-final-validation.json" --force

Write-Host ""
Write-Host "== Inspect local milestone ==" -ForegroundColor Cyan
python -m aresforge inspect-local-milestone --definition "artifacts\milestones\m31-final-validation.json" --format markdown

Write-Host ""
Write-Host "== Check local milestone readiness ==" -ForegroundColor Cyan
python -m aresforge check-local-milestone-readiness --definition "artifacts\milestones\m31-final-validation.json" --format markdown

Write-Host ""
Write-Host "== Generate local milestone closeout ==" -ForegroundColor Cyan
python -m aresforge generate-local-milestone-closeout --definition "artifacts\milestones\m31-final-validation.json" --output "artifacts\milestones\m31-closeout.md" --format markdown --force

Write-Host ""
Write-Host "== Final status ==" -ForegroundColor Cyan
git status --short
```

## M32 Managed Project Registry

Purpose:

- Track multiple local projects and multiple repos in a local-first control-plane registry.
- Keep registry management local-only with no GitHub or network dependency.

Defaults:

- registry directory: `.aresforge/projects/`
- registry file: `.aresforge/projects/projects.json`

Commands:

- `python -m aresforge init-managed-project-registry [--path <path>] [--force]`
- `python -m aresforge register-managed-project --project-id <id> --name <name> --root-path <path> [--registry-path <path>] [--description <text>] [--status <status>] [--default-branch <branch>] [--tag <tag>]... [--notes <text>]`
- `python -m aresforge register-managed-repo --project-id <id> --repo-id <id> --name <name> --path <path> [--registry-path <path>] [--remote-url <url>] [--default-branch <branch>] [--role <role>] [--status <status>] [--tag <tag>]... [--notes <text>]`
- `python -m aresforge inspect-managed-project-registry [--registry-path <path>] [--format json|markdown]`
- `python -m aresforge inspect-managed-project --project-id <id> [--registry-path <path>] [--format json|markdown]`
- `python -m aresforge inspect-managed-repo --project-id <id> --repo-id <id> [--registry-path <path>] [--format json|markdown]`

Behavior guarantees:

- local-only command surface
- no `gh` calls
- no GitHub API calls
- no network access
- `init-managed-project-registry` creates missing directories and refuses overwrite unless `--force`
- `register-managed-project` is idempotent by `project_id`
- `register-managed-repo` is idempotent by `project_id + repo_id`
- repo registration fails clearly when `project_id` does not exist

M26/M27/M30 linkage:

- M26 `generate-handoff-package` includes managed-project registry summary when registry exists.
- M27 local project state remains per current repo/session context, while M32 registry tracks many projects/repos.
- M30 milestones can later be associated with managed `project_id` / `repo_id`.
- M33 queue add-item validates `project_id` and `repo_id` locally against M32 registry when registry exists or `--registry-path` is supplied.

## M33 Local Project Queue And Work Tracking

Purpose:

- Track local work items across managed projects/repos without GitHub issues.
- Provide a local foundation for future handoff profiles, multi-agent orchestration planning, escalation planning, and dashboards.

Defaults:

- queue directory: `.aresforge/queue/`
- queue file: `.aresforge/queue/work_items.json`

Commands:

- `python -m aresforge init-project-queue [--path <path>] [--force]`
- `python -m aresforge add-queue-item --item-id <id> --project-id <id> --repo-id <id> --title <title> [--queue-path <path>] [--registry-path <path>] [--description <text>] [--status <status>] [--priority <priority>] [--type <type>] [--tag <tag>]... [--depends-on <item_id>]... [--blocked-by <item_id>]... [--assigned-agent <agent_id>] [--source <source>] [--notes <text>]`
- `python -m aresforge update-queue-item --item-id <id> [--queue-path <path>] [--project-id <id>] [--repo-id <id>] [--status <status>] [--priority <priority>] [--type <type>] [--title <title>] [--description <text>] [--tag <tag>]... [--depends-on <item_id>]... [--blocked-by <item_id>]... [--assigned-agent <agent_id>] [--source <source>] [--notes <text>]`
- `python -m aresforge inspect-project-queue [--queue-path <path>] [--project-id <id>] [--repo-id <id>] [--status <status>] [--type <type>] [--assigned-agent <agent_id>] [--format json|markdown]`
- `python -m aresforge inspect-queue-item --item-id <id> [--queue-path <path>] [--format json|markdown]`

Behavior guarantees:

- local-only command surface
- no `gh` calls
- no GitHub API calls
- no network access
- no LLM calls
- `init-project-queue` creates missing directories and refuses overwrite unless `--force`
- `add-queue-item` is idempotent by `item_id`
- `update-queue-item` updates only supplied fields
- inspect commands default to stable JSON and can render readable markdown
- dependency references can target future items and produce warning-only guidance
- `assigned_agent` is stored for future orchestration and does not execute agents in M33
- `assigned_agent` can reference an M34 local agent profile `agent_id`

M26/M27/M32 linkage:

- M26 `generate-handoff-package` includes local project queue summary when queue exists.
- M27 local project state captures current repo/session state, while M33 queue tracks local work progression.
- M32 managed-project registry provides local project/repo validation for queue item registration.

## M34 Local Agent Profiles And Handoff Targets

Purpose:

- Define local-only agent profiles describing roles, execution mode preferences, and handoff metadata.
- Define local-only handoff target descriptors for operator workflows.
- Keep M34 configuration/planning oriented with no agent execution.

Defaults:

- profiles directory: `.aresforge/agents/`
- profiles file: `.aresforge/agents/agents.json`

Commands:

- `python -m aresforge init-agent-profiles [--path <path>] [--force] [--with-defaults]`
- `python -m aresforge register-agent-profile --agent-id <id> --name <name> --role <role> [--profiles-path <path>] [--description <text>] [--execution-mode <mode>] [--model-preference <value>] [--strength <text>]... [--constraint <text>]... [--allowed-type <type>]... [--escalation-allowed true|false] [--handoff-target-id <id>] [--status <status>] [--tag <tag>]... [--notes <text>]`
- `python -m aresforge register-handoff-target --target-id <id> --name <name> --target-type <type> [--profiles-path <path>] [--description <text>] [--local-command <command>] [--input-format <format>] [--output-format <format>] [--safety-note <text>]... [--status <status>] [--tag <tag>]... [--notes <text>]`
- `python -m aresforge inspect-agent-profiles [--profiles-path <path>] [--role <role>] [--execution-mode <mode>] [--status <status>] [--format json|markdown]`
- `python -m aresforge inspect-agent-profile --agent-id <id> [--profiles-path <path>] [--format json|markdown]`
- `python -m aresforge inspect-handoff-target --target-id <id> [--profiles-path <path>] [--format json|markdown]`

Behavior guarantees:

- local-only command surface
- no `gh` calls
- no GitHub API calls
- no network access
- no local LLM calls
- no cloud LLM calls
- handoff targets are descriptive/advisory only
- no orchestration execution is introduced in M34
- `init-agent-profiles` creates missing directories and refuses overwrite unless `--force`
- `init-agent-profiles --with-defaults` seeds safe, generic local-first defaults
- `register-agent-profile` is idempotent by `agent_id`
- `register-handoff-target` is idempotent by `target_id`
- missing `handoff_target_id` references are saved with warning-only guidance

M26/M33 linkage:

- M26 `generate-handoff-package` includes local agent profile summary when profiles exist.
- M33 `assigned_agent` can point to an M34 `agent_id`.

## M35 Local Multi-Agent Orchestration Planner

Purpose:

- Produce local-only, plan-only multi-agent orchestration recommendations.
- Connect M32 managed registry context, M33 queue work items, and M34 agent profiles.
- Generate handoff-ready prompts without executing agents.

Defaults:

- orchestration artifact folder: `artifacts/orchestration/`

Command:

- `python -m aresforge plan-agent-orchestration [--project-id <id>] [--repo-id <id>] [--status <status>] [--queue-path <path>] [--profiles-path <path>] [--registry-path <path>] [--output <path>] [--format json|markdown] [--force]`

Behavior guarantees:

- local-only command surface
- plan-only output
- no agent execution
- no local LLM calls
- no cloud LLM calls
- no `gh` calls
- no GitHub API calls
- no network access
- default output format is stable JSON
- markdown output is available for operator readability
- if `--output` is omitted, plan renders to stdout
- if `--output` is supplied, missing directories are created and overwrite is refused unless `--force`
- missing queue/profiles/registry inputs produce warnings and reduced output instead of hard failure
- assignment logic preserves valid existing `assigned_agent`, warns on missing assigned agents, otherwise recommends by `item_type`, role preference, and allowed item types
- dependency ordering respects `dependencies`, flags unresolved `blocked_by`, and reports circular dependency risks

M26/M32/M33/M34 linkage:

- M26 `generate-handoff-package` includes latest orchestration artifact note when found under `artifacts/orchestration/`, or an orchestration capability note if none exist.
- M32 registry can be used for project/repo linkage checks during orchestration planning.
- M33 queue `assigned_agent`, `dependencies`, and `blocked_by` fields are used directly by M35 planning logic.
- M34 profiles and handoff target references are used for assignment recommendations and handoff prompt generation.

## M36 Local Escalation Planner

Purpose:

- Produce local-only, plan-only escalation guidance for queue work.
- Classify items into `local_llm_suitable`, `codex_suitable`, `cloud_llm_recommended`, `human_required`, or `blocked_or_needs_clarification`.
- Recommend handoff targets and copy/paste prompt guidance without executing any model or service.

Defaults:

- escalation artifact folder: `artifacts/escalation/`

Command:

- `python -m aresforge plan-llm-escalation [--item-id <id>] [--project-id <id>] [--repo-id <id>] [--status <status>] [--queue-path <path>] [--profiles-path <path>] [--orchestration-plan <path>] [--output <path>] [--format json|markdown] [--force]`

Behavior guarantees:

- local-only command surface
- plan-only classification output
- cloud escalation guidance is advisory only
- no LLM invocation
- no local LLM calls
- no cloud LLM calls
- no Codex execution
- no ChatGPT calls
- no `gh` calls
- no GitHub API calls
- no network access
- default stdout format is stable JSON
- markdown output is available for readability
- if `--output` is omitted, plan renders to stdout
- if `--output` is supplied, missing directories are created and overwrite is refused unless `--force`
- missing queue/profiles/orchestration inputs produce warnings and reduced output instead of hard failure

M26/M33/M34/M35 linkage:

- M26 `generate-handoff-package` includes latest escalation artifact note when found under `artifacts/escalation/`, or an escalation capability note if none exist.
- M33 queue fields (`item_id`, `project_id`, `repo_id`, `status`, `item_type`, dependencies/blockers) are classification inputs.
- M34 profiles and handoff targets are used for recommended escalation routing.
- M35 orchestration output can be provided to classify orchestration outcomes and queue work for local/Codex/cloud/human paths.

## M30 Self-Managed Local Milestone Lifecycle

When to run:

- Run at milestone start to create a local milestone definition template.
- Run during implementation to inspect/update scope and check readiness.
- Run before handoff/closeout to generate a deterministic local closeout package.

Commands:

- `python -m aresforge generate-local-milestone-template --milestone-id <id> --output <path> [--title <title>] [--force]`
- `python -m aresforge inspect-local-milestone --definition <path> [--format json|markdown]`
- `python -m aresforge check-local-milestone-readiness --definition <path> [--project-state <path>] [--format json|markdown]`
- `python -m aresforge generate-local-milestone-closeout --definition <path> --output <path> [--format json|markdown] [--force]`

Suggested local structure:

- `.aresforge/milestones/<milestone-id>.json`

Lifecycle expectations:

- Local-only, plan/check/generate only.
- No `gh`, no GitHub API calls, no network access, no LLM calls.
- Treat M28 documentation reconciliation as a required closeout lifecycle step:
  - `python -m aresforge plan-doc-reconciliation ...`
- Treat M26 handoff generation as a required continuity step:
  - `python -m aresforge generate-handoff-package ...`
- Treat M29 GitHub sync planning as optional for future sync windows:
  - `python -m aresforge plan-github-sync ...`

## M29 Offline-to-GitHub Sync Planner

When to run:

- Run after offline closeout/state updates to prepare a reviewed GitHub sync plan.
- Run before any live GitHub mutation window to classify potential comment/close/label/milestone actions.
- Run during rate-limit-sensitive periods to keep planning local and deterministic.

Command:

- `python -m aresforge plan-github-sync [--state-file <path>] [--project-state <path>] [--output <path>] [--format json|markdown] [--force]`

Stdout behavior when `--output` is omitted:

- default: markdown to stdout
- `--format json`: stable JSON to stdout

Safety and boundary:

- plan-only (does not post comments, close issues, or create PRs)
- local-only command surface
- does not call `gh`
- does not call GitHub APIs
- does not validate against live GitHub state
- does not require network access
- does not mutate local state files

Output highlights:

- generated timestamp and input files used
- parent/child sync candidates
- evidence comments and issue closures to consider later
- PR evidence mappings, label/milestone candidates, and validation command candidates
- rate-limit risk warnings and manual review checklist
- explicit statement that no GitHub operations were performed

## M28 Documentation Reconciliation Planner

When to run:

- Run after milestone implementation or doc-heavy changes to detect stale source-of-truth sections.
- Run before session handoff to produce a local documentation update plan for the next operator.
- Run after updating `.aresforge/state/project_state.json` documentation fields to verify source-of-truth alignment.

Command:

- `python -m aresforge plan-doc-reconciliation [--output <path>] [--format json|markdown] [--include-git-state] [--force]`

Stdout behavior when `--output` is omitted:

- default: markdown to stdout
- `--format json`: stable JSON to stdout

Safety and boundary:

- plan-only (no automatic doc edits)
- local-only command surface
- does not call `gh`
- does not call GitHub APIs
- does not call LLMs
- does not require network access
- local git state collection only when `--include-git-state` is set, and limited to:
  - `git branch --show-current`
  - `git rev-parse HEAD`
  - `git status --short`
  - `git log -n 10 --oneline`

M26/M27 continuity integration:

- M26 `generate-handoff-package` now includes latest local documentation reconciliation plan reference when present in `artifacts/doc-reconciliation/`.
- M27 local project state ledger `documentation_status` should be used to track documentation progress between planning runs.

## M26 Local Handoff Package Generator

When to run:

- Run before ending a session to reduce manual handoff writing.
- Run when transferring work between human sessions, Codex sessions, or local LLM agents.
- Run after meaningful changes so the next session has current branch/head/status context and next-step options.

Command:

- `python -m aresforge generate-handoff-package --output <path> [--format markdown|json] [--include-doc-excerpts] [--force]`

Stdout behavior when `--output` is omitted:

- default: markdown to stdout
- `--format json`: stable JSON to stdout

Safety and boundary:

- local-only command surface
- does not call `gh`
- does not call GitHub APIs
- does not require network access
- local git state collection is limited to:
  - `git branch --show-current`
  - `git rev-parse HEAD`
  - `git status --short`
  - `git log -n 10 --oneline`

M27 integration:

- When `.aresforge/state/project_state.json` exists, handoff payloads include a local project-state summary.
- If the local project-state file is missing, handoff generation warns and still succeeds.

## M27 Local Project State Ledger

Purpose:

- Persist local project status without requiring GitHub as the only source of project state.

Defaults:

- state directory: `.aresforge/state/`
- state file: `.aresforge/state/project_state.json`
- operation log: `.aresforge/state/operation_log.jsonl`

Commands:

- `python -m aresforge init-project-state [--path <path>] [--force]`
- `python -m aresforge inspect-project-state [--path <path>]`
- `python -m aresforge update-project-state [--path <path>] [--current-milestone <value>] [--current-phase <value>] [--current-mode <value>] [--validation-status <value>] [--documentation-status <value>] [--warning <text>]...`
- `python -m aresforge append-operation-log [--state-path <path>] --event-type <type> --summary <summary> [--details <json>]`
- `python -m aresforge inspect-operation-log [--state-path <path>] [--limit <n>]`

Behavior guarantees:

- Local-only command surface.
- No `gh` calls.
- No GitHub API calls.
- No network dependency.
- `init-project-state` creates missing folders and refuses overwrite unless `--force`.
- `update-project-state` updates only supplied fields (plus `updated_at`).
- `append-operation-log` creates log file if missing and appends JSONL entries.
- `inspect-operation-log --limit <n>` returns newest entries when limit is provided.

## M25 Automatic Canonical Marker Emission Workflow

When to run:

- Run M25 readiness-by-construction checks while executing each child in sequence for a parent milestone.
- Use it to confirm canonical marker emission coverage across child, PR, parent, and closeout-comment evidence domains.
- Keep parent closeout blocked until both milestone execution readiness and marker emission readiness are true.

M25 command set (read-only by default):

- `python -m aresforge inspect-automatic-canonical-evidence-emission-contract`
- `python -m aresforge generate-child-closeout-evidence-bundle --parent-issue <parent> --child-issue <child>`
- `python -m aresforge generate-pr-evidence-bundle --issue <child> --pr <pr>`
- `python -m aresforge generate-parent-closeout-evidence-bundle --parent-issue <parent>`
- `python -m aresforge generate-evidence-comment-template --issue <issue>`
- `python -m aresforge check-closeout-readiness-by-construction --parent-issue <parent>`

Automatic canonical marker emission domains checked by readiness-by-construction:

- child evidence bundle canonical marker completeness
- PR evidence bundle canonical marker completeness
- parent closeout evidence bundle canonical marker completeness
- closeout comment canonical marker completeness

Readiness-by-construction interpretation:

- `readiness_by_construction.ready=true` means marker emission readiness and milestone execution readiness are both satisfied.
- `readiness_by_construction.ready=false` with `blocked_reasons` means closeout remains blocked and remediation should be targeted.
- `post_hoc_marker_repair_required=true` means generated marker completeness is not sufficient and readiness fails by construction.

Operator approval boundary:

- Marker generation/checking, preflight generation, snapshot generation, and readiness-by-construction checks remain read-only by default.
- Posting issue comments, editing PR bodies, and closing issues remain separate operator-approved targeted actions.
- Never use bulk issue closure.
- Never close the parent before children are closed/accounted for and parent readiness gates pass.

PowerShell-safe guidance:

- Avoid nested markdown fences inside here-strings.
- Use plain text command examples in issue/comment bodies.
- Prefer `--body-file` and `--comment-file` for multiline mutation content.

## Offline State-File Mode (Local-Only Parent Closeout Readiness)

Use `--state-file` when you need local, deterministic closeout readiness checks with no live GitHub calls.

Local-only command set:

- `python -m aresforge generate-offline-closeout-state-template --parent-issue <parent> --children <child1,child2,...> --output <path>`
- `python -m aresforge inspect-milestone-state --parent-issue <parent> --state-file <path>`
- `python -m aresforge check-milestone-evidence-readiness --parent-issue <parent> --state-file <path>`
- `python -m aresforge inspect-parent-closeout-readiness --parent-issue <parent> --state-file <path>`
- `python -m aresforge generate-parent-closeout-evidence-bundle --parent-issue <parent> --state-file <path>`
- `python -m aresforge check-closeout-readiness-by-construction --parent-issue <parent> --state-file <path>`

Template generation notes:

- The generator is local-only and does not call `gh` or live GitHub APIs.
- Output is an editable JSON template artifact that includes parent/child placeholders, marker placeholders, and a `final_reconciliation` section.
- Use `--force` to overwrite an existing template file; otherwise the command fails safely when output already exists.

Offline boundary:

- `--state-file` mode is local-only.
- Do not run `gh` commands as part of this flow.
- Do not create or close issues, do not comment on issues, and do not create PRs from these commands.

Expected local state schema (minimum + readiness markers):

- `parent_issue`: object with `number` (must match `--parent-issue`), plus normal issue fields (`state`, `title`, `url`, optional lineage references).
- `child_issues`: list of child issue objects with:
- `number`, `state`, `title`, `url`
- child lineage hints (`body` containing `Parent issue: #<parent>` and/or `reference_classification.implementation_issue_numbers`)
- `merged_pr_evidence` (each PR supports `number` and/or `url`)
- `closeout_marker` marker completeness object
- `closeout_comment_marker` marker completeness object
- PR marker data per `merged_pr_evidence` item via `marker` when validating readiness-by-construction
- `final_reconciliation`: object with `ready_for_final_reconciliation`, `parent_should_remain_open`, optional `final_reconciliation_issue`, and `unaccounted_children`
- `final_main_head`: string for parent closeout marker completeness
- `final_validation_results`: string for parent closeout marker completeness

Marker completeness object shape:

- `state` (`ready` or `incomplete`)
- `marker_complete` (`true`/`false`)
- `missing_required_fields` (list)
- `invalid_reasons` (list)
- `post_hoc_marker_repair_required` (`true`/`false`)

Example synthetic fixture:

- `tests/fixtures/offline_state/parent_closeout_ready.json`
- Example-only test data; not production GitHub state.

## M24 Canonical Evidence Marker Workflow

When to run:

- Run canonical marker generation before posting child, PR, or parent evidence comments.
- Run preflight snapshot generation before and after reconciliation updates to audit drift.
- Keep parent closeout blocked until marker + readiness checks report ready.

Canonical marker command set (read-only by default):

- `python -m aresforge inspect-canonical-evidence-marker-contract`
- `python -m aresforge generate-child-evidence-marker-template --parent-issue <parent> --child-issue <child>`
- `python -m aresforge generate-pr-evidence-marker-template --issue <child> --pr <pr>`
- `python -m aresforge generate-parent-closeout-marker-template --parent-issue <parent>`
- `python -m aresforge generate-preflight-baseline-snapshot --parent-issue <parent>`
- `python -m aresforge diff-preflight-snapshots --before <before_snapshot.json> --after <after_snapshot.json>`

Marker types and required fields:

- `child_evidence`: parent issue, child issue, branch, commit, PR, validation summary, safety notes
- `pr_evidence`: issue, PR, branch, commit, changed files, validation summary, merge status, safety posture, evidence status
- `parent_closeout_evidence`: parent issue, child issue list, child-to-PR mapping, final main HEAD, final validation results, readiness gate summary, safety confirmations, closeout readiness state
- `reconciliation_audit`: baseline snapshot, post-reconciliation snapshot, snapshot diff, audit classification, warnings/deviations

Snapshot and diff interpretation:

- `no-change`: no readiness signal improvements/regressions detected
- `improved`: one or more readiness signals improved and none regressed
- `regressed`: one or more readiness signals regressed and none improved
- `mixed`: both improvements and regressions detected in the same diff

Marker-complete evidence block examples (plain text, copy/paste safe):

- Child evidence marker:
   [ARESFORGE_CANONICAL_EVIDENCE_MARKER]
   marker_type: child_evidence
   marker_state: ready
   required.parent_issue: #400
   required.child_issue: #409
   required.branch: m24-409-canonical-marker-workflow-docs
   required.commit: <commit_sha>
   required.pr: #<pr>
   required.validation_summary: git diff --check=pass; pytest=pass; inspect-repo-governance=pass
   required.safety_notes: read-only by default; targeted mutation only
   optional.closeout_status: closed
   optional.evidence_comment_status: posted
   optional.merge_status: merged
   missing_required_fields: <none>
   invalid_reasons: <none>
   [/ARESFORGE_CANONICAL_EVIDENCE_MARKER]

- Parent closeout evidence marker:
   [ARESFORGE_CANONICAL_EVIDENCE_MARKER]
   marker_type: parent_closeout_evidence
   marker_state: ready
   required.parent_issue: #400
   required.child_issue_list: #401, #402, #403, #404, #405, #406, #407, #408, #409, #410
   required.child_to_pr_mapping: #401->#411, #402->#412, #403->#413, #404->#414, #405->#415, #406->#416, #407->#417, #408->#418, #409->#<pr>, #410->#<pr>
   required.final_main_head: <main_head>
   required.final_validation_results: git diff --check=pass; pytest=pass; inspect-repo-governance=pass
   required.readiness_gate_summary: parent_closeout_ready=true; blocked_reasons=none
   required.safety_confirmations: read-only generation; explicit operator-approved targeted mutation only
   required.closeout_readiness_state: ready
   optional.warnings_deviations: milestone_naming_status.naming_ok=false; missing milestone assignment warnings
   missing_required_fields: <none>
   invalid_reasons: <none>
   [/ARESFORGE_CANONICAL_EVIDENCE_MARKER]

Explicit mutation boundary:

- Marker generation, preflight generation, snapshot generation, and evidence bundle generation are read-only by default.
- Repair/update guidance is copy/paste guidance only unless a separate targeted mutation command is explicitly approved.
- PR body update, issue comment, and issue closeout execution remain separate operator-approved targeted commands.
- Never bulk-close child issues; never close parent before child closeout/readiness gates pass.

## M23 Lineage And Evidence Preflight Workflow

When to run:

- Run M23 preflight before any parent closeout action.
- Run after each child merge/closeout to detect lineage/evidence/PR mapping drift early.
- Run before parent evidence bundle generation and before parent closeout readiness review.

Primary command set:

- `python -m aresforge inspect-milestone-closeout-preflight-contract`
- `python -m aresforge inspect-parent-child-linkage-preflight --parent-issue <parent>`
- `python -m aresforge inspect-child-evidence-marker-preflight --parent-issue <parent>`
- `python -m aresforge inspect-pr-mapping-preflight --parent-issue <parent>`
- `python -m aresforge generate-closeout-preflight-repair-guidance --parent-issue <parent>`
- `python -m aresforge inspect-milestone-closeout-preflight --parent-issue <parent>`

How M23 preflight relates to existing readiness commands:

- `inspect-milestone-dashboard` and `inspect-milestone-state` remain the source for parent/child state and ordering.
- `check-milestone-evidence-readiness` and `inspect-parent-closeout-readiness` remain parent closeout gates.
- `inspect-milestone-closeout-preflight` adds strict lineage + evidence marker + PR mapping detectability checks before parent closeout.
- `generate-parent-closeout-evidence-bundle` should be run after preflight reports ready (or after operator-reviewed warning remediation).

State interpretation:

- `ready`: no blocked/warning/unknown findings; closeout preflight gate is satisfied.
- `blocked`: hard gaps found (for example missing lineage, missing PR mapping, missing evidence marker block).
- `warning`: partial/ambiguous findings requiring operator remediation before closeout.
- `unknown`: preflight could not determine required signal state from current data.

Repair guidance usage:

- `generate-closeout-preflight-repair-guidance` output is copy/paste-safe guidance only.
- Repair guidance is not mutation execution.
- Mutation remains a separate operator-approved targeted action.

PowerShell-safe examples (plain text only):

- `python -m aresforge inspect-milestone-closeout-preflight --parent-issue <parent>`
- `python -m aresforge generate-closeout-preflight-repair-guidance --parent-issue <parent>`
- `gh issue edit <parent> --body-file artifacts/issue-<parent>-body.md`
- `gh issue comment <child> --body-file artifacts/issue-<child>-evidence.txt`
- `gh pr view <pr_number> --json state,mergeCommit,url`

Operator approval boundary:

- Preflight commands are read-only by default.
- PR/issue/body/comment mutation commands require explicit operator approval and targeted scope.
- Bulk closure is forbidden.
- Parent closeout is forbidden until children are closed/accounted for and parent readiness/preflight gates pass.

## M22 Evidence Bundle Workflow

M22 issue/PR mapping status:

- parent `#362` OPEN
- child `#363` CLOSED via PR `#372`
- child `#364` CLOSED via PR `#373`
- child `#365` CLOSED via PR `#374`
- child `#366` CLOSED via PR `#375`
- child `#367` CLOSED via PR `#376`
- child `#368` CLOSED via PR `#377`
- child `#369` CLOSED via PR `#378`
- child `#370` CLOSED via PR `#379`
- child `#371` OPEN via PR `#380` (final reconciliation, processed last)

Command inventory:

- `python -m aresforge inspect-evidence-bundle-automation-contract`
- `python -m aresforge generate-child-closeout-evidence-bundle --parent-issue <parent> --child-issue <child>`
- `python -m aresforge generate-parent-closeout-evidence-bundle --parent-issue <parent>`
- `python -m aresforge generate-pr-evidence-bundle --issue <issue> --pr <pr>`
- `python -m aresforge simulate-evidence-bundle-generation --parent-issue <parent>`

Read-only defaults and approval boundary:

- all evidence bundle generation commands are read-only by default
- generation commands must not close issues, edit PRs, or post comments automatically
- targeted mutation remains operator-approved and narrow (`gh issue close <issue>`, `gh issue comment <issue>`, `gh pr edit <pr> --body-file <file>`)
- never bulk-close child issues
- never close parent before child closeout/accounting and readiness checks pass

Child closeout bundle flow:

1. Generate child evidence body text.
2. Replace placeholders with concrete branch/commit/files/validation evidence.
3. Post one targeted issue comment for one child issue.
4. Close only that child issue.

Commands:

- `python -m aresforge generate-child-closeout-evidence-bundle --parent-issue <parent> --child-issue <child>`
- `gh issue comment <child> --body-file <comment_file>`
- `gh issue close <child> --comment "Closing after merged PR and posted evidence."`

Parent closeout bundle flow:

1. Run parent readiness checks and generate parent evidence bundle.
2. Confirm `parent_closeout_ready` is `true` and blocked reasons are empty.
3. Post one targeted parent evidence comment.
4. Close only the parent issue.

Commands:

- `python -m aresforge inspect-parent-closeout-readiness --parent-issue <parent>`
- `python -m aresforge generate-parent-closeout-evidence-bundle --parent-issue <parent>`
- `gh issue comment <parent> --body-file <comment_file>`
- `gh issue close <parent> --comment "Parent closeout after readiness confirmation."`

PR evidence body flow:

1. Generate deterministic PR evidence body text.
2. Review and save the text.
3. Apply one targeted PR body update only when explicitly approved.

Commands:

- `python -m aresforge generate-pr-evidence-bundle --issue <issue> --pr <pr>`
- `gh pr edit <pr> --body-file artifacts/pr-<pr>-body.md`
- `python -m aresforge prepare-pr-body-update --pr-number <pr> --target-issue <issue> --scope-summary "<summary>"`

Validation summary normalization:

- Validation summaries are normalized to: `pass`, `fail`, `warning`, `unknown`.
- Common labels are normalized for deterministic evidence output:
   - `git diff --check`
   - `python -m pytest`
   - `python -m aresforge inspect-repo-governance`
   - `python -m aresforge inspect-milestone-dashboard`
   - `python -m aresforge inspect-milestone-state`
   - `python -m aresforge check-milestone-evidence-readiness`
   - `python -m aresforge inspect-parent-closeout-readiness`

Dry-run simulation flow:

- `python -m aresforge simulate-evidence-bundle-generation --parent-issue <parent>`

Simulation guarantees:

- no mutation by default
- final reconciliation must remain last
- blocked and ready parent bundle states are represented for fixture coverage
- child and PR evidence generation paths are covered in dry-run planning form

Known warnings/deviations carried forward:

- `milestone_naming_status.naming_ok` remains `false` (non-blocking warning).
- parent/child GitHub milestone assignment gaps may still appear as warnings.
- `run-sequential-child-closeout-flow` requires explicit `--comment-body` in dry-run and execute modes.

PowerShell safety for issue/comment bodies:

- avoid nested markdown fences inside here-strings
- use plain text command examples inside issue/comment bodies
- prefer `--body-file` and `--comment-file` for multiline content

## M18 Core Validation Bundle

- `git diff --check`
- `python -m pytest`
- `python -m aresforge inspect-repo-governance`
- `python -m aresforge inspect-milestone-state --parent-issue <parent>`
- `python -m aresforge inspect-milestone-dashboard --parent-issue <parent>`
- `python -m aresforge plan-milestone-execution-queue --parent-issue <parent>`
- `python -m aresforge check-issue-evidence-readiness --issue <issue>`
- `python -m aresforge check-milestone-evidence-readiness --parent-issue <parent>`
- `python -m aresforge plan-milestone-final-reconciliation --parent-issue <parent>`
- `python -m aresforge inspect-parent-closeout-readiness --parent-issue <parent>`
- `python -m aresforge inspect-sequential-run-state --parent-issue <parent>`

## End-to-End Child Execution Pattern (M18)

1. Sync clean `main`.
2. Implement one child issue only on one issue-specific branch.
3. Run the validation bundle.
4. Open one PR for that child issue.
5. Merge PR.
6. Sync clean `main` again.
7. Re-run validation bundle.
8. Generate and post issue-specific evidence mapping comment.
9. Close only the target child issue.
10. Re-run milestone dashboard and queue checks.
11. Move to next recommended child issue.

Rules:

- never bulk-close issues
- never close parent before child sequence is complete
- keep final reconciliation issue last
- mutation remains human-triggered and review-gated

## M20 Mutation Intent Planning (Child #328)

Command:

- `python -m aresforge plan-github-mutation --mutation-type <issue_comment|issue_close|pr_body_update|audit_log_write> --planned-action "<action>" [--target-issue <issue>] [--target-pr <pr>] [--approval-marker <marker>]`

Behavior:

- planning-only and dry-run by default
- validates one explicit mutation type and one explicit target shape
- blocks unsafe target/type combinations
- emits required approvals, safety checks, blocked reasons, dry-run summary, and audit metadata preview
- never closes issues
- never creates PRs
- never comments on issues
- never mutates GitHub state

## M20 Targeted Issue Comment Execution (Child #329)

Commands:

- `python -m aresforge execute-github-issue-comment --issue <issue> --comment-body "<body>"`
- `python -m aresforge execute-github-issue-comment --issue <issue> --comment-file <path>`
- `python -m aresforge execute-github-issue-comment --issue <issue> --comment-body "<body>" --execute --approval-marker <marker>`

Behavior:

- dry-run by default
- requires explicit issue target
- requires non-empty comment body
- execution requires explicit `--execute` plus `--approval-marker`
- blocks parent target when `--parent-issue` matches `--issue` unless `--allow-parent-target` is supplied
- emits audit-ready result payload
- does not close issues
- no bulk comment mutation path

## M20 Targeted Issue Close Execution (Child #330)

Commands:

- `python -m aresforge execute-github-issue-close --issue-target <issue> --parent-issue <parent>`
- `python -m aresforge execute-github-issue-close --issue-target <issue> --parent-issue <parent> --execute --approval-marker <marker>`

Behavior:

- dry-run by default
- accepts only one plain-digit issue target (`--issue-target 330`)
- rejects lists/ranges/composite targets (`330,331`, `330-334`)
- child close requires child issue evidence readiness
- parent close requires parent closeout readiness true
- execution requires explicit `--execute` and `--approval-marker`
- emits audit-ready result payload
- no bulk closure path

## M20 PR Body Update Helper (Child #331)

Commands:

- `python -m aresforge prepare-pr-body-update --pr-number <pr> --target-issue <issue> --scope-summary "<summary>"`
- `python -m aresforge prepare-pr-body-update --pr-number <pr> --target-issue <issue> --scope-summary "<summary>" --file-changed <path> --validation-result "<result>" --safety-note "<note>"`
- `python -m aresforge prepare-pr-body-update --pr-number <pr> --target-issue <issue> --scope-summary "<summary>" --execute --approval-marker <marker>`

Behavior:

- dry-run by default
- renders structured PR body text with scope, files changed, validation results, and safety notes
- supports optional targeted execution for one PR body update only
- execution requires explicit `--execute` and `--approval-marker`
- generated output avoids nested markdown fences for PowerShell examples
- no bulk PR update path

## M20 Mutation Audit Log And Recovery Guidance (Child #332)

Commands:

- `python -m aresforge inspect-github-mutation-audit-log`
- `python -m aresforge inspect-github-mutation-audit-log --limit 50`

Behavior:

- mutation planning/execution commands append local audit records
- records include mutation intent, dry-run output, approval marker, execution result, timestamp, target, command concept, and recovery notes
- audit artifacts are local-only by default
- inspection command is read-only and does not mutate GitHub
- generated local audit artifacts must not be committed

## M20 End-To-End Operator-Approved Mutation Workflow (Child #333)

Recommended child order for M20:

1. #327
2. #328
3. #329
4. #330
5. #331
6. #332
7. #333
8. #334 (final reconciliation only; keep last)

M20 workflow example:

1. Plan mutation intent:
   - `python -m aresforge plan-github-mutation --mutation-type issue_comment --planned-action "post child evidence" --target-issue <child>`

## M21 Self-Managed Milestone Execution Contract (Child #346)

Command:

- `python -m aresforge inspect-self-managed-milestone-execution-contract`

Behavior:

- read-only contract inspection
- defines required inputs/outputs for parent-driven sequential child execution
- documents dry-run default and explicit operator-approval mutation boundary
- documents targeted mutation boundary (single issue comment, single issue close, single PR body update)
- documents parent closeout readiness boundary

## M21 End-to-End Dry-Run Simulation (Child #351)

Command:

- `python -m aresforge simulate-self-managed-milestone-execution --parent-issue <parent>`

Behavior:

- read-only simulation only
- validates parent input, child discovery, sequential ordering, validation envelope, dry-run mutation planning, handoff planning, and parent closeout readiness blocking
- confirms no GitHub mutation, no issue closure, and no bulk closeout path
- preserves final reconciliation as the last child in sequence
- reports the recommended next open child issue based on current milestone dashboard state

## M21 Self-Managed Child Workflow (Child #352)

Use this workflow for M21 parent execution where each child has exactly one branch, one PR, one evidence comment, and one targeted closeout.

Start from parent issue:

1. Sync clean main:
   - `git checkout main`
   - `git fetch origin`
   - `git pull --ff-only origin main`
   - `git status --short` (must be empty)
2. Inspect parent state and child ordering:
   - `python -m aresforge inspect-milestone-dashboard --parent-issue <parent>`
   - `python -m aresforge inspect-milestone-state --parent-issue <parent>`
   - `python -m aresforge inspect-self-managed-milestone-execution-contract`
3. Run read-only simulation before implementation:
   - `python -m aresforge simulate-self-managed-milestone-execution --parent-issue <parent>`
4. Select only the recommended next open child issue (do not skip ahead; keep final reconciliation last).
5. Create one branch for that child issue and implement only that issue scope.
6. Run required validation for that child:
   - `git diff --check`
   - `python -m pytest`
   - `python -m aresforge inspect-repo-governance`
   - `python -m aresforge inspect-milestone-dashboard --parent-issue <parent>`
   - `python -m aresforge inspect-milestone-state --parent-issue <parent>`
   - `python -m aresforge inspect-self-managed-milestone-execution-contract`
   - `python -m aresforge run-sequential-child-closeout-flow --parent-issue <parent> --child-issue <child> --comment-body "M21 child evidence draft"`
   - `python -m aresforge generate-sequential-closeout-execution-package --parent-issue <parent> --child-issue <child>`
7. Open and merge one PR for one child issue only.
8. Sync clean main again and re-run validation commands.
9. Generate handoff/recovery output:
   - `python -m aresforge generate-self-managed-milestone-handoff --parent-issue <parent> --completed-child <child> --next-child <next-child>`
10. Post targeted evidence comment and close only the target child issue with explicit execution approval.
11. Re-check child and parent state:
   - `gh issue view <child> --json number,state,closedAt,url`
   - `gh issue view <parent> --json number,state,title,url`
12. Repeat from step 1 for the next open child.

M21 parent closeout guardrails:

- never close the parent while any child remains open or unaccounted for
- run readiness checks before parent closeout:
  - `python -m aresforge check-milestone-evidence-readiness --parent-issue <parent>`
  - `python -m aresforge inspect-parent-closeout-readiness --parent-issue <parent>`
- close parent only when `parent_closeout_ready` is true and blocked reasons are empty
- parent closeout must remain parent-targeted only and must not change child issue states

PowerShell issue/comment body guidance:

- avoid nested markdown fences inside here-strings
- prefer plain text command examples inside issue/comment bodies
- for multiline PR body/comment content, use `--body-file` or `--comment-file` rather than inline shell-escaped markdown
2. Review dry-run output, required approvals, and blocked reasons.
3. Execute targeted issue comment only when explicitly approved:
   - `python -m aresforge execute-github-issue-comment --issue <child> --comment-body "<evidence>" --execute --approval-marker <marker>`
4. Validate closeout readiness for a single issue target:
   - `python -m aresforge execute-github-issue-close --issue-target <child> --parent-issue <parent>`
5. Execute targeted issue close only when explicitly approved and ready:
   - `python -m aresforge execute-github-issue-close --issue-target <child> --parent-issue <parent> --execute --approval-marker <marker>`
6. Prepare PR body/update summary in dry-run mode:
   - `python -m aresforge prepare-pr-body-update --pr-number <pr> --target-issue <child> --scope-summary "<summary>" --validation-result "python -m pytest -> pass" --safety-note "dry-run by default"`
7. Inspect local audit records:
   - `python -m aresforge inspect-github-mutation-audit-log --limit 20`
8. If blocked/failure occurs, use targeted recovery only:
   - resolve blocked reasons on one issue/PR target
   - rerun one command in dry-run first
   - do not run bulk mutation commands

M20 safety boundaries:

- no autonomous broad mutation
- no bulk closure
- no parent closure before children are closed/accounted for
- dry-run/planning default for mutation features
- explicit approval required for execution paths
- local audit artifacts remain local-only unless explicitly exported by an operator

What not to do:

- do not run issue ranges or lists for closeout (`330-334`, `330,331`)
- do not close parent #326 while any M20 child remains open
- do not execute mutation commands without explicit approval marker
- do not use broad scripts that mutate multiple issues/PRs in one step
- do not commit local audit runtime artifacts

PowerShell plain text examples (no nested markdown fences):

- Set-Location C:\Projects\aresforge
- python -m aresforge plan-github-mutation --mutation-type issue_close --planned-action "close child after readiness" --target-issue 333
- python -m aresforge execute-github-issue-close --issue-target 333 --parent-issue 326

## Read-Only Milestone Inspection

Commands:

- `python -m aresforge inspect-milestone-state --parent-issue <parent>`

Behavior:

- read-only issue and milestone state inspection
- parent/child discovery from detectable references
- child state, lineage, and merged PR evidence hints summary
- no issue closure
- no PR creation
- no comments
- no GitHub edits

## Read-Only Milestone Queue Planning

Commands:

- `python -m aresforge plan-milestone-execution-queue --parent-issue <parent>`

Behavior:

- planning-only milestone child execution ordering
- deterministic child sequencing with final reconciliation issue last when detected
- blocker and missing lineage surfacing
- missing merged PR evidence signal surfacing
- explicit safety gates:
  - execution enabled false
  - close issues false
  - bulk closeout allowed false
  - operator review required true
- no issue closure
- no PR creation
- no comments
- no GitHub edits

## Per-Child Execution Gate Inspection (M19 #312)

Commands:

- `python -m aresforge inspect-child-execution-gates --issue <issue> --parent-issue <parent>`

Behavior:

- read-only gate inspection for one child issue
- evaluates start/PR/merge/close safety posture for the target child
- checks local cleanliness and branch naming posture
- checks open PR presence and merged PR evidence/readiness posture
- reports blockers and deterministic next recommended action
- never closes issues
- never creates PRs
- never comments on issues
- never mutates GitHub state

## Unified Milestone Dashboard (M18 #295)

Commands:

- `python -m aresforge inspect-milestone-dashboard --parent-issue <parent>`

Behavior:

- read-only consolidated dashboard built from milestone inspection, queue planning, evidence readiness, and final reconciliation planning outputs
- reports parent state, child issue state summary, accounted/unaccounted child signals, and deterministic queue recommendation
- surfaces evidence readiness status counts, final reconciliation readiness, and operator-required next actions
- preserves non-mutation safety gates and boundary confirmations
- never closes issues
- never creates PRs
- never comments on issues
- never mutates GitHub state

M19 #315 extension:

- dashboard now surfaces local sequential run-state when available
- output explicitly separates GitHub issue truth from local sequential run-state
- mismatch flags are raised when local sequential run-state and GitHub child discovery diverge

## Sequential Run-State Inspection (M19 #311)

Commands:

- `python -m aresforge inspect-sequential-run-state --parent-issue <parent>`
- `python -m aresforge inspect-sequential-run-state --parent-issue <parent> --write-local-state`

Behavior:

- builds a local sequential run-state snapshot from read-only milestone inspection, queue planning, and evidence readiness commands
- captures parent issue, current child recommendation, completed children, failed-step signal, PR/evidence summary, and next recommended action
- defaults to read-only mode without writing local files
- optional local persistence writes only to `.aresforge/sequential-run-state.json`
- never closes issues
- never creates PRs
- never comments on issues
- never mutates GitHub state

## Sequential Recovery Planning (M19 #313)

Commands:

- `python -m aresforge plan-sequential-run-recovery --parent-issue <parent>`

Behavior:

- reads persisted sequential run-state and compares against current dashboard and child gate inspection signals
- reports recovery states for failed validation, failed PR creation, unmerged PR, merged PR with missing evidence, closed child, stale branch, dirty tree, and dashboard mismatch
- returns deterministic next recommended action
- read-only/planning only by default
- never closes issues
- never creates PRs
- never comments on issues
- never mutates GitHub state

## Sequential Evidence/Handoff Package (M19 #314)

Commands:

- `python -m aresforge generate-sequential-handoff-package --parent-issue <parent>`
- `python -m aresforge generate-sequential-handoff-package --parent-issue <parent> --issue <child>`
- `python -m aresforge generate-sequential-handoff-package --parent-issue <parent> --write-package`

Behavior:

- generates structured per-child and per-milestone handoff/evidence package output
- includes child issue, branch, commit, PR, merge/main hash, validations, evidence URL if known, final child state, dashboard status, and next child recommendation
- read-only by default
- local artifact writing is opt-in using `--write-package`
- never closes issues
- never creates PRs
- never comments on issues
- never mutates GitHub state

## End-to-End Sequential Operator Workflow (M19 #316)

Recommended child order for M19:

1. #310
2. #311
3. #312
4. #313
5. #314
6. #315
7. #316
8. #317 (final reconciliation only; keep last)

Per-child one-at-a-time loop:

1. Sync clean main:
   - `git checkout main`
   - `git fetch origin`
   - `git pull --ff-only origin main`
   - `git status --short` (must be empty)
2. Create one dedicated child branch (example: `m19/<issue>-short-slug`).
3. Implement only the target child scope.
4. Run validation bundle:
   - `git diff --check`
   - `python -m pytest`
   - `python -m aresforge inspect-repo-governance`
   - `python -m aresforge inspect-milestone-dashboard --parent-issue <parent>`
   - `python -m aresforge inspect-milestone-state --parent-issue <parent>`
   - `python -m aresforge check-milestone-evidence-readiness --parent-issue <parent>`
5. Commit with issue reference and push branch.
6. Open one PR for one child issue.
7. Merge the PR only after readiness checks pass.
8. Sync clean main and rerun validation bundle.
9. Generate child evidence package:
   - `python -m aresforge generate-sequential-handoff-package --parent-issue <parent> --issue <child>`
10. Post issue-specific evidence comment scoped only to that child issue.
11. Close only the target child issue.
12. Re-run dashboard/readiness commands before starting next child.

Recovery and resume examples:

- Resume local status snapshot:
  - `python -m aresforge inspect-sequential-run-state --parent-issue <parent>`
- Persist local snapshot for handoff:
  - `python -m aresforge inspect-sequential-run-state --parent-issue <parent> --write-local-state`
- Generate recovery plan after interruption/failure:
  - `python -m aresforge plan-sequential-run-recovery --parent-issue <parent>`
- If blocked, stop progression, do not close current issue, and do not advance to next child until recovery action is resolved.

Evidence and closeout guidance:

- Every child must have:
  - one branch
  - one PR
  - one validation cycle on branch and on main after merge
  - one issue-specific evidence comment
  - one targeted closeout
- Evidence comments should include child issue number, branch, commit, PR URL, merge/main hash, files changed, validation results, safety notes, dashboard/readiness summary, and a statement that evidence applies only to that child.
- Never use bulk closeout commands.
- Never close parent until all children are closed/accounted for and final reconciliation is complete.

Safety boundaries:

- No autonomous broad mutation.
- No bulk issue closure.
- No parent closure before child sequence completion and explicit readiness proof.
- Prior milestone mutation is out of scope unless explicitly required for M19 documentation references.
- Local sequential run-state remains advisory and must not override GitHub issue truth.

## Evidence Readiness Checking (M17/#274 and M18/#299 enhancements)

Commands:

- `python -m aresforge check-issue-evidence-readiness --issue <issue>`
- `python -m aresforge check-milestone-evidence-readiness --parent-issue <parent>`

Behavior:

- read-only/planning-only evidence completeness classification
- duplicate/no-op PR prevention via evidence reuse recommendation
- schema-driven structured evidence block support with safe malformed/duplicate/conflict handling
- never closes issues
- never creates PRs
- never comments on issues
- never mutates GitHub state

## Parent Closeout Readiness (M18 #298)

Commands:

- `python -m aresforge inspect-parent-closeout-readiness --parent-issue <parent>`

Behavior:

- read-only parent closeout readiness report with explicit child lineage
- reports child state, evidence mapping status, individual closure/accounted signals
- reports blocked reasons, required operator actions, and safety gates
- never closes parent or children
- never creates PRs
- never comments on issues
- never mutates GitHub state

## Milestone Final Reconciliation Planning

Commands:

- `python -m aresforge plan-milestone-final-reconciliation --parent-issue <parent>`

Behavior:

- planning-only milestone final reconciliation readiness check
- inspects parent/child milestone state via read-only command surfaces
- verifies implementation children are closed or evidence-accounted before reconciliation
- confirms final reconciliation issue should be last
- surfaces likely source-of-truth docs requiring updates
- confirms docs-only expectation for final reconciliation
- confirms no generated evidence artifact changes are expected
- emits explicit non-mutation gates:
  - close issues false
  - create PR false
  - comment on issue false
  - mutation allowed false
  - operator review required true
- never closes issues
- never creates PRs
- never comments on issues
- never mutates GitHub state

## Script/Template Generation Commands (Read-Only Generators)

Commands:

- `python -m aresforge generate-evidence-comment-template --issue <issue>`
- `python -m aresforge generate-child-closeout-script --issue <issue>`

Behavior:

- generate operator-reviewed text/script artifacts only
- do not post comments automatically
- do not close issues automatically
- do not create PRs/branches automatically
- keep PowerShell output fence-safe for operator copy/review

## Controlled Autonomous Execution (M16)

Commands:

- `python -m aresforge run-autonomous-cycle --mode dry-run --parent-issue <parent> --target-issue <target>`
- `python -m aresforge run-autonomous-cycle --mode local-write --parent-issue <parent> --target-issue <target>`
- `python -m aresforge run-autonomous-cycle --mode branch-write --parent-issue <parent> --target-issue <target> --branch-name <branch> --commit-message <message>`
- `python -m aresforge run-autonomous-cycle --mode push-pr --parent-issue <parent> --target-issue <target> --branch-name <branch> --commit-message <message> --pr-title <title>`
- `python -m aresforge run-autonomous-cycle --mode closeout-eligible --parent-issue <parent> --target-issue <target> --branch-name <branch> --commit-message <message> --pr-title <title>`
- `python -m aresforge inspect-autonomous-run --run-id <id>`

Mode behavior:

- `dry-run`: read-only plan and validation path; no repository or GitHub mutation.
- `local-write`: local lifecycle progression with evidence generation; no GitHub mutation.
- `branch-write`: enables branch and commit mutation only after gate pass.
- `push-pr`: enables branch/commit plus push and PR creation after gate pass.
- `closeout-eligible`: enables push-pr path plus controlled issue closure after closeout gates pass.

## Fail-Closed Gate Design

Higher-permission modes require explicit inputs and fail closed when missing:

- `branch-write`: requires `--branch-name` and `--commit-message`
- `push-pr`: requires branch-write inputs plus `--pr-title`
- `closeout-eligible`: requires push-pr inputs plus validation pass, issue-PR linkage (`pr_number` + `pr_url`), and merged-PR evidence pass

## Evidence And Audit

- Every run writes evidence artifacts under `artifacts/evidence/generated`.
- Every mutation/evaluation step is recorded in DB-backed `run_steps`.
- Run lifecycle state is recorded in `autonomous_runs`.
- Failed runs still produce evidence and persisted step history.

## Human-Gated Mutation Boundaries

Allowed:

- human-triggered command execution
- explicit mode-scoped mutation
- evidence-backed run inspection

Not authorized:

- mutation in `dry-run`
- GitHub mutation in `local-write` or `branch-write`
- push/PR outside explicit higher-permission modes
- issue closure outside explicit `closeout-eligible`
- automatic PR merge
- background jobs, polling loops, or schedulers

## Governance Note

- `inspect-repo-governance` milestone naming warning may remain non-blocking (`milestone_naming_status.naming_ok: false`).
