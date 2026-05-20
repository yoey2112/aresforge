# AresForge Agent Registry Schema

## Purpose

This document defines the first canonical AresForge agent registry schema and lifecycle-state model.

The agent registry exists so AresForge can describe bounded agent roles with stable, reviewable records before future queue orchestration, model routing, dashboard views, or richer local operator helpers are implemented.

During M2, this document defines source-of-truth meaning and conservative validation expectations. It does not authorize autonomous execution, autonomous routing, autonomous GitHub mutation, autonomous approval, autonomous merge, or autonomous issue closure.

## Relationship To Other Source-Of-Truth Documents

### Relationship To `docs/architecture/REGISTRY_AND_QUEUE_ARCHITECTURE.md`

`docs/architecture/REGISTRY_AND_QUEUE_ARCHITECTURE.md` is the parent architecture document for project, agent, model, queue, capability, and skill registries.

This document specializes only the agent-registry layer. It turns the higher-level agent-registry concept into a concrete schema, lifecycle-state model, validation model, and bounded example set for M2.

### Relationship To `docs/architecture/ISSUE_LIFECYCLE_AGENT_PIPELINE.md`

`docs/architecture/ISSUE_LIFECYCLE_AGENT_PIPELINE.md` remains the canonical lifecycle-flow design for issue movement and handoff order.

This document does not replace that lifecycle design. Instead, it formalizes the role records that map to the lifecycle stages and clarifies which roles are active, planned, or documentation-only during M2.

### Relationship To `docs/context/AGENT_CONTEXT.md`

`docs/context/AGENT_CONTEXT.md` remains the minimum operating-context document for agents working in this repository.

This schema gives that context a more formal registry model. `AGENT_CONTEXT.md` explains operating rules and current-state expectations; this document explains the intended record structure for the roles those rules govern.

### Relationship To `.agent/AGENT_REGISTRY.md`

`.agent/AGENT_REGISTRY.md` is the current repo-owned skill registry.

It is not the full AresForge agent registry. It lists advisory skills that agents may consult. The full agent registry defined here describes agent-role identity, lifecycle state, capabilities, queues, evidence expectations, approval boundaries, escalation rules, and operator integration points.

## Core Definitions

### Agent

An agent is a bounded work role with defined responsibilities, allowed inputs, expected outputs, approval boundaries, evidence expectations, and lifecycle relationships.

An agent is a role definition, not a background process, not an always-on service, and not proof of runtime automation.

### Agent Record

An agent record is the schema-shaped description of one recognized AresForge role.

### Lifecycle State

A lifecycle state describes whether an agent role definition is planned, in active use, paused, blocked, deprecated, or archived.

### Capability Relationship

A capability relationship describes which bounded capability types an agent may perform, support, request, review, or explicitly must not perform.

### Queue Participation

Queue participation describes which lifecycle queues or queue classes an agent may enter, read from, prepare handoffs for, or close out.

### Approval Boundary

An approval boundary defines which decisions the agent may inform versus which decisions must remain human-approved.

## Agent Record Minimum Useful Schema

| Field | Required now? | Future implementation? | Description | Example value |
|---|---|---|---|---|
| `agent_id` | Yes | Yes | Stable unique identifier for the role. | `agent-worker` |
| `agent_name` | Yes | Yes | Human-readable role name. | `Worker Agent` |
| `agent_slug` | Yes | Yes | Stable slug for references and future storage. | `worker-agent` |
| `lifecycle_state` | Yes | Yes | Conservative current role state. | `planned` |
| `role_kind` | Yes | Yes | Broad category such as lifecycle, support, or human. | `lifecycle` |
| `role_summary` | Yes | Yes | Short description of the role's purpose. | `Performs issue-scoped implementation work.` |
| `inputs` | Yes | Yes | Minimum required inputs for safe work. | `["scoped issue handoff", "source-of-truth docs"]` |
| `outputs` | Yes | Yes | Expected artifacts or decisions. | `["repo changes", "implementation summary"]` |
| `allowed_capabilities` | Yes | Yes | Capability categories the role may perform or support. | `["implementation_drafting", "local_validation_support"]` |
| `disallowed_capabilities` | Yes | Yes | Explicitly blocked capability categories. | `["autonomous_issue_closure", "autonomous_merge"]` |
| `queue_participation` | Yes | Yes | Queue lanes or lifecycle stages the role may participate in. | `["implementation"]` |
| `approval_boundary` | Yes | Yes | Explicit human-approval boundary for the role. | `human_review_required` |
| `evidence_expectations` | Yes | Yes | Required evidence outputs for the role. | `["validation summary", "scope notes"]` |
| `operator_integration_points` | Yes | Yes | How the local operator may reference the role. | `["prompt package role selection", "read-only listing"]` |
| `source_of_truth_links` | No | Yes | Related canonical docs for the role. | `["docs/architecture/ISSUE_LIFECYCLE_AGENT_PIPELINE.md"]` |
| `skill_relationships` | No | Yes | Related advisory skills, if any. | `[".agent/skills/pr-validation/SKILL.md"]` |
| `model_relationships` | No | Yes | Allowed model usage notes for the role. | `["local-first review support"]` |
| `notes` | No | Yes | Important role-specific caveats. | `Documentation gate is required before closeout.` |

## Required M2 Fields

The following fields are required for useful M2 role records:

- `agent_id`
- `agent_name`
- `agent_slug`
- `lifecycle_state`
- `role_kind`
- `role_summary`
- `inputs`
- `outputs`
- `allowed_capabilities`
- `disallowed_capabilities`
- `queue_participation`
- `approval_boundary`
- `evidence_expectations`
- `operator_integration_points`

These are the minimum fields needed to identify the role, explain its boundary, tie it to the lifecycle pipeline, and keep the registry conservative enough for human-reviewed M2 work.

## Optional M2 Fields

These fields are useful during M2 but are not required for every role record:

- `handoff_requirements`
- `escalation_triggers`
- `source_of_truth_links`
- `skill_relationships`
- `model_relationships`
- `human_owner_notes`
- `risk_notes`
- `example_work_items`
- `validation_notes`

## Future Implementation-Only Fields

These fields are reserved for later implementation work and should not be treated as active M2 capability:

- `runtime_instance_id`
- `queue_consumer_binding`
- `execution_environment`
- `health_state`
- `availability_state`
- `concurrency_limit`
- `scheduler_policy`
- `last_run_at`
- `last_handoff_at`
- `audit_log_path`
- `dashboard_agent_id`
- `registry_storage_path`

## Lifecycle-State Values

The canonical conservative lifecycle-state values are:

| State | Meaning | M2 interpretation |
|---|---|---|
| `planned` | The role is defined or intended, but not yet active as runnable behavior. | Documentation-only or seed-reference role. |
| `active` | The role definition is in current approved use. | May be human-triggered or manually performed. Not proof of autonomy. |
| `paused` | The role remains recognized but temporarily not in use. | Resume only through later human-reviewed change. |
| `blocked` | The role is recognized but currently cannot operate due to missing prerequisites or explicit boundary restrictions. | May exist in docs or state store without being callable. |
| `deprecated` | The role should be replaced and should not be used for new work. | Preserve for history and migration planning only. |
| `archived` | The role is retained for history only. | Not part of active planning or routing. |

## Allowed Capability Relationships

Agent records must define capability relationships conservatively.

Allowed relationship types during M2:

- The agent may perform a bounded capability.
- The agent may review or validate a bounded capability.
- The agent may prepare handoff context for a bounded capability.
- The agent may request human review for a bounded capability.
- The agent may explicitly refuse or block a bounded capability.

Disallowed relationship patterns during M2:

- Broad capability labels that silently imply authority.
- Capability inheritance from model presence alone.
- Capability inheritance from skill presence alone.
- Capability inference from queue access alone.

## Queue Participation Expectations

Queue participation must align with `docs/architecture/ISSUE_LIFECYCLE_AGENT_PIPELINE.md`.

During M2:

- Planning / Next-Issue Agent participates in planning-oriented intake or planning lanes.
- Triage / Routing Agent participates in routing and queue-selection preparation.
- Worker Agent participates in implementation lanes only.
- Verification Agent participates in verification lanes only.
- Testing Agent participates in testing or validation lanes only.
- Debug Routing Agent participates in failure-loop routing only.
- Documentation Agent participates in documentation and source-of-truth update lanes.
- Final Closeout / Lifecycle Controller Agent participates in final readiness and closeout lanes.
- Local Operator participates as the human-triggered integration surface that prepares or displays work across lanes without owning autonomous transitions.

Queue participation does not authorize autonomous consumption, autonomous transition, or background processing.

## Human Approval Boundaries

Every agent record must make human approval boundaries explicit.

During M2, agents may support:

- analysis
- packaging
- drafting
- review preparation
- validation reporting
- documentation updates
- local state inspection

During M2, agents must not independently approve:

- merges
- issue closure
- governance changes
- repo-setting changes
- branch protection changes
- ruleset changes
- secret changes
- release or tag changes
- GitHub Project changes
- autonomous GitHub mutation

Registry presence does not grant authority.

## Escalation Rules

Agent records should escalate to the human owner when:

- source-of-truth documents conflict
- issue scope is ambiguous
- required validation fails
- the required capability appears blocked
- a requested action crosses governance-sensitive boundaries
- documentation freshness findings cannot be resolved safely in scope
- a queue transition would bypass a required lifecycle gate
- a role definition appears stale, conflicting, or incomplete

## Evidence Output Expectations

Agent records must define what evidence each role should produce.

Minimum expected evidence categories during M2:

- planning notes or issue-sequencing notes for planning roles
- routing notes and constraints for triage roles
- implementation summary and changed-file notes for worker roles
- requirement-fit findings for verification roles
- test and validation results for testing roles
- defect summaries for debug routing roles
- source-of-truth updates and freshness findings for documentation roles
- closeout readiness confirmation for final closeout roles
- command output and artifact references for the local operator

Where applicable, evidence should align with:

- `docs/agents/PR_EVIDENCE_PACKAGE_TEMPLATE.md`
- `docs/agents/CLOSEOUT_EVIDENCE_PACKAGE_TEMPLATE.md`

## Skill And Model Relationships

### Skill Relationships

Skills are advisory inputs only during M2.

An agent record may reference skills that help the role perform work consistently, but a skill reference must not be interpreted as:

- an executable worker
- a queue consumer
- a permission grant
- a lifecycle-state upgrade

### Model Relationships

Model relationships describe which models may support a role, not which roles are autonomous.

During M2:

- model use remains local-first where possible
- model support is optional and bounded
- the human owner remains the final authority over model-sensitive or governance-sensitive usage
- no role may claim authority just because a model is configured

## Validation Rules

Agent registry records should pass these checks before they are considered usable:

- required fields exist
- `agent_id` and `agent_slug` are stable and unique
- `lifecycle_state` uses an approved value
- `allowed_capabilities` and `disallowed_capabilities` do not conflict
- queue participation matches the intended lifecycle role
- approval boundaries are explicit
- evidence expectations are not empty
- operator integration points do not imply hidden execution
- source-of-truth links reference real or explicitly planned documents
- role definitions do not imply autonomous GitHub-state-changing behavior

During M2, these are review expectations and optional local validation targets, not autonomous enforcement.

## Source-Of-Truth And Closeout Expectations

Agent-registry changes are project-state-changing changes.

That means Issue #83 and future agent-registry changes must review and update when needed:

- `docs/context/BUILD_STATE.md`
- `docs/context/AGENT_CONTEXT.md`
- `docs/roadmap/ROADMAP.md`

They must also preserve the lifecycle correction from `docs/architecture/ISSUE_LIFECYCLE_AGENT_PIPELINE.md`:

- documentation updates belong inside the same issue lifecycle
- separate routine reconciliation issues should not be created by default
- Issue #39 remains intentionally open protected validation audit evidence unless a future human-directed issue explicitly changes it

## Explicit M2 Restrictions

This schema does not authorize:

- autonomous GitHub-state-changing behavior
- autonomous PR merge
- autonomous approval
- autonomous issue closure
- autonomous issue routing
- background workers
- watchers
- workflow files
- repo settings changes
- branch protection changes
- ruleset changes
- secrets changes
- release or tag changes
- GitHub Project changes
- autonomous Codex execution
- autonomous Ollama planning loops

## Initial AresForge Agent-Role Example Set

The following initial example set aligns with the lifecycle pipeline and current M2 boundaries.

```yaml
agents:
  - agent_id: agent-planning-next-issue
    agent_name: Planning / Next-Issue Agent
    agent_slug: planning-next-issue-agent
    lifecycle_state: planned
    role_kind: lifecycle
    role_summary: Selects the next approved issue and packages initial scope and reading inputs.
    queue_participation: [intake, planning]
    allowed_capabilities:
      - issue_selection_support
      - sequencing_analysis
      - source_of_truth_reading_list_preparation
    disallowed_capabilities:
      - autonomous_issue_creation
      - autonomous_issue_closure
      - autonomous_merge
    approval_boundary: human_review_required
    evidence_expectations:
      - issue recommendation notes
      - dependency notes
      - required source-of-truth list

  - agent_id: agent-triage-routing
    agent_name: Triage / Routing Agent
    agent_slug: triage-routing-agent
    lifecycle_state: planned
    role_kind: lifecycle
    role_summary: Converts an approved issue into a scoped execution handoff and queue path.
    queue_participation: [planning, routing]
    allowed_capabilities:
      - scope_refinement
      - queue_path_recommendation
      - validation_requirement_packaging
    disallowed_capabilities:
      - autonomous_issue_routing
      - autonomous_governance_change
    approval_boundary: human_review_required
    evidence_expectations:
      - routing notes
      - scoped handoff summary
      - boundary notes

  - agent_id: agent-worker
    agent_name: Worker Agent
    agent_slug: worker-agent
    lifecycle_state: planned
    role_kind: lifecycle
    role_summary: Performs issue-scoped implementation work.
    queue_participation: [implementation]
    allowed_capabilities:
      - implementation_drafting
      - local_file_changes
      - local_validation_support
    disallowed_capabilities:
      - autonomous_merge
      - autonomous_issue_closure
      - repository_governance_change
    approval_boundary: human_review_required
    evidence_expectations:
      - changed-file summary
      - implementation notes
      - initial validation notes

  - agent_id: agent-verification
    agent_name: Verification Agent
    agent_slug: verification-agent
    lifecycle_state: planned
    role_kind: lifecycle
    role_summary: Confirms that implemented changes satisfy issue scope and requirements.
    queue_participation: [verification]
    allowed_capabilities:
      - requirement_fit_review
      - scope_control_review
      - defect_identification
    disallowed_capabilities:
      - issue_close_authority
      - merge_authority
    approval_boundary: human_review_required
    evidence_expectations:
      - findings summary
      - requirement coverage notes
      - scope warnings

  - agent_id: agent-testing
    agent_name: Testing Agent
    agent_slug: testing-agent
    lifecycle_state: planned
    role_kind: lifecycle
    role_summary: Runs or reports issue-appropriate validation commands and manual checks.
    queue_participation: [verification, testing]
    allowed_capabilities:
      - test_execution_support
      - validation_reporting
      - skipped_check_reporting
    disallowed_capabilities:
      - approval_authority
      - closeout_authority
    approval_boundary: human_review_required
    evidence_expectations:
      - validation results
      - skipped-check notes
      - remaining-risk notes

  - agent_id: agent-debug-routing
    agent_name: Debug Routing Agent
    agent_slug: debug-routing-agent
    lifecycle_state: planned
    role_kind: lifecycle
    role_summary: Routes failed verification or testing work back to the right corrective path.
    queue_participation: [verification, testing, routing]
    allowed_capabilities:
      - defect_classification
      - corrective_handoff_preparation
      - failure_loop_support
    disallowed_capabilities:
      - bypass_documentation_gate
      - autonomous_issue_routing
    approval_boundary: human_review_required
    evidence_expectations:
      - defect summary
      - corrective route notes
      - retry expectations

  - agent_id: agent-documentation
    agent_name: Documentation Agent
    agent_slug: documentation-agent
    lifecycle_state: active
    role_kind: lifecycle
    role_summary: Performs documentation-before-closeout review and updates impacted source-of-truth docs.
    queue_participation: [documentation]
    allowed_capabilities:
      - documentation_impact_review
      - documentation_updates
      - freshness_check_reporting
      - evidence_package_support
    disallowed_capabilities:
      - merge_authority
      - issue_close_authority
      - source_of_truth_bypass
    approval_boundary: human_review_required
    evidence_expectations:
      - source-of-truth update summary
      - freshness findings
      - PR and closeout evidence inputs

  - agent_id: agent-final-closeout
    agent_name: Final Closeout / Lifecycle Controller Agent
    agent_slug: final-closeout-lifecycle-controller-agent
    lifecycle_state: planned
    role_kind: lifecycle
    role_summary: Confirms that lifecycle gates passed and prepares final closeout readiness.
    queue_participation: [documentation, closeout]
    allowed_capabilities:
      - closeout_readiness_review
      - final_gate_confirmation
      - human_handoff_preparation
    disallowed_capabilities:
      - autonomous_issue_closure
      - autonomous_merge
      - autonomous_approval
    approval_boundary: human_review_required
    evidence_expectations:
      - closeout readiness summary
      - unresolved limitation notes
      - final handoff notes

  - agent_id: agent-local-operator
    agent_name: Local Operator
    agent_slug: local-operator
    lifecycle_state: active
    role_kind: human
    role_summary: Human-triggered local CLI surface for read-only inspection, local artifact preparation, and approved local state actions.
    queue_participation: [intake, planning, implementation, verification, documentation, closeout]
    allowed_capabilities:
      - local_state_inspection
      - migration_execution
      - prompt_package_generation
      - evidence_package_recording
      - codex_handoff_preparation
      - read_only_registry_listing
    disallowed_capabilities:
      - autonomous_codex_execution
      - autonomous_ollama_planning
      - autonomous_github_mutation
      - merge_authority
      - issue_close_authority
    approval_boundary: human_owner
    evidence_expectations:
      - command output
      - artifact paths
      - boundary confirmations
```

## Open Design Questions

The following questions remain intentionally open after this schema definition:

- Should future structured agent records live in markdown, YAML, JSON, database tables, or a hybrid model?
- How should capability names be normalized once the capability registry exists?
- Should queue participation be stored as lane names, queue IDs, or lifecycle-stage references?
- How should role-level lifecycle state differ from runtime-instance state?
- Which future agent roles should remain project-specific versus globally reusable?
- How should model suitability and validation strength be expressed without over-encoding implementation details too early?
- How should deprecated and archived roles be surfaced in local operator views?
- How should agent-registry validation eventually be implemented without creating hidden automation?
