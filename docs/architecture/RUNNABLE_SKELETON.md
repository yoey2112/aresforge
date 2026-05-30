# Runnable Skeleton

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
