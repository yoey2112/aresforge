# AresForge Queue Registry Schema

## Purpose

This document defines the canonical M2 queue registry and work-item state transition schema for AresForge.

It formalizes queue identities, queue meaning, accepted work-item types, handoff expectations, lifecycle-state mapping, failure routing, blocked or waiting handling, evidence requirements, and local operator visibility expectations for the current M2 lifecycle model.

During M2, this document is the source of truth for queue-record meaning and work-item state meaning. It does not implement queue workers, autonomous routing, autonomous issue dispatch, autonomous approval, autonomous merge, autonomous issue closure, GitHub Project changes, repository setting changes, branch protection or ruleset changes, secret or release or tag changes, or hosted external model use.

## Relationship To Other Source-Of-Truth Documents

### Relationship To `docs/architecture/REGISTRY_AND_QUEUE_ARCHITECTURE.md`

`docs/architecture/REGISTRY_AND_QUEUE_ARCHITECTURE.md` is the parent architecture document for the project, agent, model, queue, capability, and skill registry layers.

This document specializes the queue-registry layer and the work-item state-transition layer. It turns the higher-level queue concept into a concrete M2 schema, transition model, validation vocabulary, and bounded example set.

### Relationship To `docs/architecture/ISSUE_LIFECYCLE_AGENT_PIPELINE.md`

`docs/architecture/ISSUE_LIFECYCLE_AGENT_PIPELINE.md` remains the canonical lifecycle-flow design for issue movement and gate order.

This schema does not replace that lifecycle design. It formalizes queue records and work-item state records so the lifecycle path can be represented consistently in local state, operator views, prompt packages, evidence packages, and later read-only queue inspection.

### Relationship To `docs/architecture/RUNNABLE_SKELETON.md`

`docs/architecture/RUNNABLE_SKELETON.md` describes the current implemented local vertical slice.

This queue schema aligns with that runnable skeleton, but it is broader than the initial seeded runtime subset. The current runtime may expose only a conservative subset of canonical queues until a later human-directed issue expands the seeded local queue records and operator commands.

### Relationship To `docs/architecture/LOCAL_STATE_STORE.md`

`docs/architecture/LOCAL_STATE_STORE.md` describes the currently implemented PostgreSQL-backed local runtime tables.

This document clarifies the intended meaning of the existing `queues`, `work_items`, `prompts`, `evidence_packages`, `approvals`, and `audit_events` tables without claiming that the current migration already stores every canonical queue field as first-class columns.

### Relationship To Agent And Model Registry Schemas

`docs/architecture/AGENT_REGISTRY_SCHEMA.md` remains the canonical source for agent-role identity, queue participation expectations, evidence outputs, and approval boundaries.

`docs/architecture/MODEL_REGISTRY_SCHEMA.md` remains the canonical source for model-record meaning, local-first routing rules, approval posture, and model-selection evidence expectations.

Queue records may reference agent roles, capabilities, and model-selection touchpoints, but queue presence must not imply agent authority, model authority, or autonomous execution.

## Core Definitions

### Queue

A queue is a canonical lifecycle lane that groups work items by stage, responsibility, or handoff status.

### Queue Record

A queue record is the schema-shaped description of one recognized queue.

### Work Item

A work item is the routed unit of work, such as a GitHub issue implementation pass, a documentation update package, a validation pass, a closeout package, or another bounded lifecycle artifact.

### Work-Item State Record

A work-item state record is the structured description of the work item's current lifecycle state, queue location, route status, related evidence, approval posture, and retry or failure context.

### Route Status

Route status is the conservative statement of where a work item stands within queue movement, such as ready, in progress, waiting, blocked, failed, or handed off.

### Corrective Loop

A corrective loop is the bounded route used when verification, testing, documentation review, or another gate fails and the work must re-enter an earlier corrective path without bypassing required lifecycle gates.

## Queue Record Schema

The canonical queue record fields for M2 are:

| Field | Required now? | Future implementation? | Description | Example value |
|---|---|---|---|---|
| `queue_id` | Yes | Yes | Stable unique identifier for the queue. | `queue-verification` |
| `queue_name` | Yes | Yes | Human-readable queue name. | `verification` |
| `queue_purpose` | Yes | Yes | Short description of the queue's lifecycle meaning. | `Requirement-fit review after implementation.` |
| `accepted_work_item_types` | Yes | Yes | Allowed work-item types for this lane. | `["github_issue", "verification_pass"]` |
| `entry_criteria` | Yes | Yes | Conditions that must be true before entering the queue. | `["implementation changes exist", "triage handoff recorded"]` |
| `exit_criteria` | Yes | Yes | Conditions that must be true before leaving the queue. | `["verification findings recorded", "next queue chosen"]` |
| `allowed_next_queues` | Yes | Yes | Canonical next queues allowed from this queue. | `["queue-testing", "queue-corrective", "queue-blocked"]` |
| `required_handoff_evidence` | Yes | Yes | Evidence categories required before transition. | `["verification summary", "scope findings"]` |
| `human_approval_requirement` | Yes | Yes | Explicit human-review or approval posture for entering or leaving the queue. | `human_review_required` |
| `failure_routing_rule` | Yes | Yes | Required route when this queue fails. | `route_to_queue-corrective_with_failure_evidence` |
| `blocked_or_waiting_state_handling` | Yes | Yes | How blocked or waiting work should be represented without losing queue meaning. | `retain queue and set route_status to waiting_for_human` |
| `lifecycle_stage_mapping` | Yes | Yes | Mapping to the lifecycle stage in the canonical pipeline. | `verification` |
| `owning_or_participating_agent_roles` | Yes | Yes | Agent roles that own or participate in this queue. | `["agent-verification", "agent-local-operator"]` |
| `related_capabilities` | Yes | Yes | Capability categories expected in this queue. | `["requirement_fit_review", "scope_control_review"]` |
| `local_operator_visibility_expectations` | Yes | Yes | What the operator should be able to inspect or confirm for work in this queue. | `["current queue", "required evidence", "blocked reason if any"]` |

## Work-Item State Schema

The canonical work-item state fields for M2 are:

| Field | Required now? | Future implementation? | Description | Example value |
|---|---|---|---|---|
| `work_item_type` | Yes | Yes | Conservative classification of the work item. | `github_issue` |
| `lifecycle_state` | Yes | Yes | High-level lifecycle stage state. | `verification_ready` |
| `route_status` | Yes | Yes | Current routing posture. | `in_progress` |
| `current_queue` | Yes | Yes | Canonical queue identifier currently holding the work. | `queue-verification` |
| `assigned_agent_role` | Yes | Yes | Current owning or active agent role, if assigned. | `agent-verification` |
| `selected_model_reference` | No | Yes | Selected model record reference when model support is relevant. | `ollama/qwen2.5:32b` |
| `prompt_package_reference` | No | Yes | Prompt package record or artifact reference when applicable. | `artifacts/prompts/generated/prompt-issue-87.md` |
| `evidence_package_references` | Yes | Yes | Evidence package references accumulated so far. | `["artifacts/evidence/generated/pr-evidence-issue-87.md"]` |
| `approval_state` | Yes | Yes | Current approval posture or pending state. | `not_requested` |
| `blocked_reason` | No | Yes | Explicit reason the work is blocked or waiting. | `awaiting human scope decision` |
| `failure_reason` | No | Yes | Explicit reason the last gate failed. | `verification found missing transition rule coverage` |
| `retry_or_correction_context` | No | Yes | Notes used to re-enter corrective flow safely. | `return to implementation with missing testing handoff notes` |
| `audit/history expectations` | Yes | Yes | Required audit trail expectations for transitions and state changes. | `record queue transitions, approvals, evidence references, and failures` |

## Canonical Work-Item Field Conventions

### `work_item_type`

Recommended conservative M2 values:

- `github_issue`
- `documentation_update`
- `verification_pass`
- `testing_pass`
- `closeout_package`
- `prompt_package`
- `evidence_package`
- `correction_pass`

### `lifecycle_state`

Recommended conservative M2 values:

- `intake_ready`
- `planning_ready`
- `triage_ready`
- `implementation_ready`
- `implementation_in_progress`
- `verification_ready`
- `testing_ready`
- `documentation_ready`
- `closeout_ready`
- `blocked`
- `waiting`
- `corrective_in_progress`
- `completed`
- `cancelled`

### `route_status`

Recommended conservative M2 values:

- `queued`
- `ready`
- `in_progress`
- `handoff_prepared`
- `waiting_for_human`
- `waiting_for_external_input`
- `blocked`
- `failed`
- `returned_for_correction`
- `complete`

### `approval_state`

Recommended conservative M2 values:

- `not_requested`
- `pending_human_review`
- `human_review_complete`
- `human_approval_required`
- `approved_for_next_step`
- `denied`

## Canonical M2 Queue Set

The canonical initial M2 queues are:

- `queue-intake`
- `queue-planning`
- `queue-triage`
- `queue-implementation`
- `queue-verification`
- `queue-testing`
- `queue-documentation`
- `queue-closeout`
- `queue-blocked`
- `queue-corrective`

The current runnable local skeleton may seed only a subset of these queues in the local database. During M2, that seeded subset should be treated as an implementation slice of this broader canonical queue schema, not as a conflicting authority source.

## Queue Records

### `queue-intake`

- `queue_id`: `queue-intake`
- `queue_name`: `intake`
- `queue_purpose`: Capture new approved work before detailed planning or triage.
- `accepted_work_item_types`: `github_issue`, `documentation_update`, `closeout_package`
- `entry_criteria`: work is approved for consideration; project context exists; source-of-truth reading list can be identified
- `exit_criteria`: intake summary exists; required docs are identified; next queue selected
- `allowed_next_queues`: `queue-planning`, `queue-blocked`
- `required_handoff_evidence`: issue reference, reading list, scope notes
- `human_approval_requirement`: human review required
- `failure_routing_rule`: move to `queue-blocked` when issue approval or prerequisite context is missing
- `blocked_or_waiting_state_handling`: retain work item with `route_status` of `waiting_for_human` or move to `queue-blocked` if no safe next step exists
- `lifecycle_stage_mapping`: planning
- `owning_or_participating_agent_roles`: `agent-planning-next-issue`, `agent-local-operator`
- `related_capabilities`: issue selection support, sequencing analysis, source-of-truth reading-list preparation
- `local_operator_visibility_expectations`: visible issue reference, required docs, project, and approval posture

### `queue-planning`

- `queue_id`: `queue-planning`
- `queue_name`: `planning`
- `queue_purpose`: Shape approved work into a bounded issue-scoped execution target.
- `accepted_work_item_types`: `github_issue`, `documentation_update`
- `entry_criteria`: intake handoff exists; project context is readable; issue direction is known
- `exit_criteria`: scope summary, constraints, and documentation expectations are recorded
- `allowed_next_queues`: `queue-triage`, `queue-blocked`
- `required_handoff_evidence`: planning notes, dependency notes, documentation expectations
- `human_approval_requirement`: human review required
- `failure_routing_rule`: move to `queue-blocked` if scope or authority remains ambiguous
- `blocked_or_waiting_state_handling`: keep current queue with `waiting_for_human` when clarification is pending
- `lifecycle_stage_mapping`: planning
- `owning_or_participating_agent_roles`: `agent-planning-next-issue`, `agent-local-operator`
- `related_capabilities`: sequencing analysis, scope preparation, source-of-truth context packaging
- `local_operator_visibility_expectations`: visible scope summary, dependency notes, and required next queue

### `queue-triage`

- `queue_id`: `queue-triage`
- `queue_name`: `triage`
- `queue_purpose`: Convert the planning package into a bounded route, queue path, and execution handoff.
- `accepted_work_item_types`: `github_issue`, `correction_pass`
- `entry_criteria`: planning package exists; issue scope is sufficiently bounded for routing
- `exit_criteria`: route path exists; active queue owner is known; validation and documentation expectations are recorded
- `allowed_next_queues`: `queue-implementation`, `queue-blocked`
- `required_handoff_evidence`: routing notes, queue recommendation, validation expectations, boundary notes
- `human_approval_requirement`: human review required
- `failure_routing_rule`: move to `queue-blocked` if the route would widen scope or cross governance boundaries
- `blocked_or_waiting_state_handling`: retain current queue with `waiting_for_human` when route selection needs human direction
- `lifecycle_stage_mapping`: triage
- `owning_or_participating_agent_roles`: `agent-triage-routing`, `agent-local-operator`
- `related_capabilities`: scope refinement, queue path recommendation, validation requirement packaging
- `local_operator_visibility_expectations`: visible planned route, next queue, blocked reason, and approval posture

### `queue-implementation`

- `queue_id`: `queue-implementation`
- `queue_name`: `implementation`
- `queue_purpose`: Hold issue-scoped repository work while implementation changes are being prepared.
- `accepted_work_item_types`: `github_issue`, `correction_pass`
- `entry_criteria`: triage handoff exists; scope is bounded; implementation work is approved to begin
- `exit_criteria`: issue-scoped changes exist; implementation summary exists; initial validation notes exist
- `allowed_next_queues`: `queue-verification`, `queue-blocked`
- `required_handoff_evidence`: changed-file summary, implementation notes, known limitations
- `human_approval_requirement`: human review required
- `failure_routing_rule`: move to `queue-blocked` if implementation cannot proceed safely under current constraints
- `blocked_or_waiting_state_handling`: retain queue with `waiting_for_human` or `blocked` when implementation is paused pending decision
- `lifecycle_stage_mapping`: implementation
- `owning_or_participating_agent_roles`: `agent-worker`, `agent-local-operator`
- `related_capabilities`: implementation drafting, local file changes, local validation support
- `local_operator_visibility_expectations`: visible queue placement, assigned role, changed files, and current route status

### `queue-verification`

- `queue_id`: `queue-verification`
- `queue_name`: `verification`
- `queue_purpose`: Confirm that the implementation matches issue requirements and scope.
- `accepted_work_item_types`: `github_issue`, `verification_pass`, `correction_pass`
- `entry_criteria`: implementation changes and summary exist
- `exit_criteria`: verification findings recorded; either pass to testing or fail into corrective flow
- `allowed_next_queues`: `queue-testing`, `queue-corrective`, `queue-blocked`
- `required_handoff_evidence`: verification findings, requirement coverage notes, scope warnings if any
- `human_approval_requirement`: human review required
- `failure_routing_rule`: move to `queue-corrective` with specific defect evidence
- `blocked_or_waiting_state_handling`: retain queue when waiting on clarifying evidence or human interpretation
- `lifecycle_stage_mapping`: verification
- `owning_or_participating_agent_roles`: `agent-verification`, `agent-local-operator`
- `related_capabilities`: requirement-fit review, scope-control review, defect identification
- `local_operator_visibility_expectations`: visible findings, pass/fail posture, and correction target when failed

### `queue-testing`

- `queue_id`: `queue-testing`
- `queue_name`: `testing`
- `queue_purpose`: Record issue-appropriate tests, checks, skips, and residual-risk notes before documentation.
- `accepted_work_item_types`: `github_issue`, `testing_pass`, `correction_pass`
- `entry_criteria`: verification passed or human-documented exception allows testing path
- `exit_criteria`: testing results recorded; passed work is ready for documentation; failed work routes to corrective
- `allowed_next_queues`: `queue-documentation`, `queue-corrective`, `queue-blocked`
- `required_handoff_evidence`: validation results, skipped-check notes, remaining-risk notes
- `human_approval_requirement`: human review required
- `failure_routing_rule`: move to `queue-corrective` with failed test context and retry expectations
- `blocked_or_waiting_state_handling`: retain queue with waiting status when required environment or human decision is missing
- `lifecycle_stage_mapping`: testing
- `owning_or_participating_agent_roles`: `agent-testing`, `agent-local-operator`
- `related_capabilities`: test execution support, validation reporting, skipped-check reporting
- `local_operator_visibility_expectations`: visible commands or checks run, result posture, and skipped-check reasons

### `queue-documentation`

- `queue_id`: `queue-documentation`
- `queue_name`: `documentation`
- `queue_purpose`: Perform documentation-before-closeout review and update impacted source-of-truth documents.
- `accepted_work_item_types`: `github_issue`, `documentation_update`, `closeout_package`
- `entry_criteria`: verification and testing passed; required documentation inputs exist
- `exit_criteria`: documentation impact is resolved; source-of-truth docs updated or explicitly justified; evidence inputs prepared
- `allowed_next_queues`: `queue-closeout`, `queue-corrective`, `queue-blocked`
- `required_handoff_evidence`: documentation impact summary, freshness findings, PR or closeout evidence inputs
- `human_approval_requirement`: human review required
- `failure_routing_rule`: move to `queue-corrective` if source-of-truth conflicts or missing updates prevent closeout readiness
- `blocked_or_waiting_state_handling`: retain queue with `waiting_for_human` when documentation conflict needs escalation
- `lifecycle_stage_mapping`: documentation
- `owning_or_participating_agent_roles`: `agent-documentation`, `agent-local-operator`
- `related_capabilities`: documentation impact review, documentation updates, freshness-check reporting, evidence-package support
- `local_operator_visibility_expectations`: visible touched docs, unresolved freshness findings, and documentation gate posture

### `queue-closeout`

- `queue_id`: `queue-closeout`
- `queue_name`: `closeout`
- `queue_purpose`: Confirm that all lifecycle gates passed and prepare final human-reviewed closeout readiness.
- `accepted_work_item_types`: `github_issue`, `closeout_package`
- `entry_criteria`: documentation gate passed; evidence packages are prepared; source-of-truth state is consistent
- `exit_criteria`: closeout readiness recorded; work item marked complete or escalated
- `allowed_next_queues`: `queue-blocked`
- `required_handoff_evidence`: closeout readiness summary, unresolved limitation notes, final handoff notes
- `human_approval_requirement`: human review required and human authority remains final
- `failure_routing_rule`: move to `queue-blocked` if closeout cannot proceed because human review or protected constraints stop completion
- `blocked_or_waiting_state_handling`: retain queue with `waiting_for_human` when final review or explicit closeout action is pending
- `lifecycle_stage_mapping`: closeout
- `owning_or_participating_agent_roles`: `agent-final-closeout`, `agent-local-operator`
- `related_capabilities`: closeout readiness review, final gate confirmation, human handoff preparation
- `local_operator_visibility_expectations`: visible gate checklist, final evidence references, and final human action required

### `queue-blocked`

- `queue_id`: `queue-blocked`
- `queue_name`: `blocked`
- `queue_purpose`: Represent work that cannot advance safely because approvals, prerequisites, or missing inputs prevent progress.
- `accepted_work_item_types`: all canonical work-item types
- `entry_criteria`: another queue cannot proceed safely and records a specific blocked or waiting reason
- `exit_criteria`: blocked condition is resolved and a valid re-entry queue is selected
- `allowed_next_queues`: `queue-intake`, `queue-planning`, `queue-triage`, `queue-implementation`, `queue-verification`, `queue-testing`, `queue-documentation`, `queue-closeout`, `queue-corrective`
- `required_handoff_evidence`: blocked reason, waiting context, resumption condition, last completed queue
- `human_approval_requirement`: human review required
- `failure_routing_rule`: remain blocked until the blocking condition changes
- `blocked_or_waiting_state_handling`: this queue is the explicit blocked state queue; `route_status` should distinguish blocked vs waiting
- `lifecycle_stage_mapping`: blocked
- `owning_or_participating_agent_roles`: `agent-local-operator`, plus the last owning lifecycle role as context
- `related_capabilities`: blocked-state inspection, escalation packaging, resumption planning
- `local_operator_visibility_expectations`: visible blocked reason, resume condition, prior queue, and human decision needed

### `queue-corrective`

- `queue_id`: `queue-corrective`
- `queue_name`: `corrective`
- `queue_purpose`: Hold work that failed verification, testing, documentation, or another gate and needs a bounded corrective pass.
- `accepted_work_item_types`: `github_issue`, `correction_pass`, `verification_pass`, `testing_pass`, `documentation_update`
- `entry_criteria`: a failed gate recorded specific failure evidence and retry context
- `exit_criteria`: corrective route is clear and work is sent back to the proper active execution queue
- `allowed_next_queues`: `queue-implementation`, `queue-verification`, `queue-testing`, `queue-documentation`, `queue-blocked`
- `required_handoff_evidence`: failure summary, retry expectations, defect classification, targeted next queue
- `human_approval_requirement`: human review required
- `failure_routing_rule`: remain in corrective or move to blocked if no safe corrective path is available
- `blocked_or_waiting_state_handling`: retain queue with waiting state when correction depends on human decision or unavailable environment
- `lifecycle_stage_mapping`: corrective
- `owning_or_participating_agent_roles`: `agent-debug-routing`, `agent-local-operator`, and the next corrective role
- `related_capabilities`: defect classification, corrective handoff preparation, failure-loop support
- `local_operator_visibility_expectations`: visible failed gate, targeted corrective queue, retry notes, and unresolved blockers

## Allowed Canonical M2 Transitions

The canonical normal path is:

`queue-intake` -> `queue-planning` -> `queue-triage` -> `queue-implementation` -> `queue-verification` -> `queue-testing` -> `queue-documentation` -> `queue-closeout`

Allowed additional transitions are:

- `queue-intake` -> `queue-blocked`
- `queue-planning` -> `queue-blocked`
- `queue-triage` -> `queue-blocked`
- `queue-implementation` -> `queue-blocked`
- `queue-verification` -> `queue-corrective`
- `queue-verification` -> `queue-blocked`
- `queue-testing` -> `queue-corrective`
- `queue-testing` -> `queue-blocked`
- `queue-documentation` -> `queue-corrective`
- `queue-documentation` -> `queue-blocked`
- `queue-closeout` -> `queue-blocked`
- `queue-corrective` -> `queue-implementation`
- `queue-corrective` -> `queue-verification`
- `queue-corrective` -> `queue-testing`
- `queue-corrective` -> `queue-documentation`
- `queue-corrective` -> `queue-blocked`
- `queue-blocked` -> the last valid recovery queue once the blocking condition is resolved

Transitions that bypass the documentation gate are not allowed. Documentation-before-closeout remains a mandatory gate.

## Blocked And Waiting Handling

Blocked and waiting status must be visible without erasing lifecycle context.

Recommended M2 handling:

- Preserve the last meaningful queue whenever the work is only temporarily waiting for input, review, or environment readiness.
- Use `route_status` to distinguish `waiting_for_human`, `waiting_for_external_input`, and `blocked`.
- Move the work item to `queue-blocked` when the blocked condition is strong enough that the work should leave the active lane until a human or prerequisite resolves it.
- Always record `blocked_reason`, expected resumption condition, and last meaningful queue context.

## Failed And Corrective-Loop Handling

Failure routing must preserve specificity and auditability.

Minimum M2 rules:

- Verification failures route to `queue-corrective`.
- Testing failures route to `queue-corrective`.
- Documentation failures or source-of-truth conflicts route to `queue-corrective`.
- Corrective routing must record `failure_reason`, `retry_or_correction_context`, and targeted return queue.
- Corrective routing must not skip required re-verification, re-testing, or documentation review when those gates remain relevant.

## Relationship To GitHub Issues, Local State, And Review Artifacts

### GitHub Issues

GitHub issues remain the primary planning and tracking artifact for most M2 work.

A GitHub issue is not itself a queue. Instead:

- the issue is usually the main human-facing planning record
- the local work-item state record reflects where that issue currently sits in the AresForge lifecycle
- queue movement may happen many times without changing the GitHub issue state

This schema does not authorize autonomous issue creation, issue dispatch, issue closure, or GitHub issue mutation.

### Local `work_items` Rows

The current local `work_items` table is the runtime row shape that most directly reflects this schema.

At minimum, future work-item rows should be interpreted through this queue schema as:

- `status`: coarse runtime status, not the full canonical lifecycle meaning by itself
- `route_status`: current route posture using the canonical vocabulary defined here
- `queue_id`: the current queue reference, which should map to `current_queue`
- `agent_id`: optional assigned role reference for `assigned_agent_role`
- `model_id`: optional local model record reference for `selected_model_reference`
- `prompt_id`: optional prompt-package record reference for `prompt_package_reference`
- `metadata`: conservative extension area for additional queue-state meaning until later schema changes are approved

### Agent Registry Roles

Queue ownership and participation must align with `docs/architecture/AGENT_REGISTRY_SCHEMA.md`.

Queue records define which roles may participate in each queue, but queue presence does not grant those roles autonomous transition authority.

### Model Registry Selection

When a model is relevant, the work-item state may reference a selected local model record.

Model selection must remain subordinate to `docs/architecture/MODEL_REGISTRY_SCHEMA.md`, especially for governance-sensitive work where autonomous model selection remains blocked.

### Prompt Packages

Prompt packages may package queue context, assigned role, and route status for human-reviewed implementation or review handoff.

Prompt-package presence does not mean the queue transition is complete by itself.

### Evidence Packages

Evidence packages are required handoff support artifacts for queue movement, especially at verification, testing, documentation, and closeout gates.

Relevant templates remain:

- `docs/agents/PR_EVIDENCE_PACKAGE_TEMPLATE.md`
- `docs/agents/CLOSEOUT_EVIDENCE_PACKAGE_TEMPLATE.md`

### Approvals

Approval records and `approval_state` are local review-state artifacts only during M2.

They may capture that human review is required, pending, or completed for a queue transition, but they do not approve, merge, close, or mutate GitHub by themselves.

### Audit Events

Queue transitions, blocked transitions, corrective loops, approval-posture changes, and evidence links should be reviewable through local audit history.

At minimum, queue-related audit expectations should preserve:

- when the transition occurred
- which queue changed
- who initiated or recorded the transition
- which evidence references were attached
- why the transition was allowed or blocked

## Human-Readable Example Queue Record

This example is documentation only:

```yaml
queue_id: queue-testing
queue_name: testing
queue_purpose: Record issue-appropriate tests, checks, and residual risk after verification.
accepted_work_item_types:
  - github_issue
  - testing_pass
entry_criteria:
  - verification findings indicate pass
  - test scope is known
exit_criteria:
  - validation results are recorded
  - skipped checks are justified
  - next queue is selected
allowed_next_queues:
  - queue-documentation
  - queue-corrective
  - queue-blocked
required_handoff_evidence:
  - validation results
  - skipped-check notes
  - remaining-risk notes
human_approval_requirement: human_review_required
failure_routing_rule: route_to_queue-corrective_with_failed_test_context
blocked_or_waiting_state_handling: retain queue with waiting_for_external_input when env prerequisites are missing
lifecycle_stage_mapping: testing
owning_or_participating_agent_roles:
  - agent-testing
  - agent-local-operator
related_capabilities:
  - test_execution_support
  - validation_reporting
local_operator_visibility_expectations:
  - show commands or checks run
  - show result posture
  - show skipped checks and reasons
```

## Human-Readable Example Work-Item State Record

This example is documentation only:

```yaml
work_item_type: github_issue
lifecycle_state: documentation_ready
route_status: ready
current_queue: queue-documentation
assigned_agent_role: agent-documentation
selected_model_reference: ollama/qwen2.5:32b
prompt_package_reference: artifacts/prompts/generated/issue-87-prompt.md
evidence_package_references:
  - artifacts/evidence/generated/issue-87-pr-evidence.md
approval_state: pending_human_review
blocked_reason: null
failure_reason: null
retry_or_correction_context: null
audit/history expectations:
  - queue transition from queue-testing to queue-documentation recorded
  - validation evidence references preserved
  - human review requirement preserved before closeout
```

## Validation Rules

Queue and work-item state definitions should pass these checks before they are considered usable:

- required queue fields exist
- required work-item fields exist
- `queue_id` values are stable and unique
- `allowed_next_queues` references only valid canonical queues
- entry and exit criteria do not bypass lifecycle gates
- documentation-before-closeout remains mandatory
- blocked and corrective behavior is explicit
- required handoff evidence is not empty for gated queues
- human approval posture is explicit
- queue participation aligns with the agent registry
- model references do not imply autonomous model authority
- wording does not imply autonomous GitHub-state-changing behavior

During M2, these are documentation and review expectations only unless a later human-directed issue implements read-only validation helpers.

## Explicit M2 Boundaries

This schema does not authorize:

- queue workers
- autonomous routing
- autonomous issue dispatch
- autonomous model selection for governance-sensitive work
- autonomous approval
- autonomous merge
- autonomous issue closure
- GitHub Project changes
- repository setting changes
- branch protection or ruleset changes
- secret, release, or tag changes
- hosted external model use

It also does not authorize scripts, workflows, bots, services, background daemons, autonomous queue consumers, or hidden transition logic.

## Open Design Questions

The following questions remain intentionally open after this schema definition:

- When should the seeded local queue set expand from the current runnable subset to the full canonical M2 set?
- Which queue and work-item fields should remain in JSON metadata versus becoming first-class columns in a later migration?
- How should future read-only operator helpers display queue history, blocked reasons, and corrective-loop depth?
- Should route status and lifecycle state remain separate first-class concepts in future structured storage?
- How should queue-state reporting represent multiple simultaneous evidence packages without obscuring the main lifecycle path?
- How should queue visibility evolve when multi-project support is introduced?
