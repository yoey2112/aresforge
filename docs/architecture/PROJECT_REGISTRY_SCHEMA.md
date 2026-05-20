# AresForge Project Registry Schema

## Purpose

The project registry exists so AresForge can describe each managed project with a stable, reviewable record before future registry storage, queue routing, model selection, dashboard state, or local operator helpers are implemented.

The first use case is AresForge managing itself. Later, the same schema should support additional managed projects without collapsing their ownership, source-of-truth rules, approval boundaries, or documentation entry points into AresForge's own project memory.

During M2, this schema remains primarily documentation-driven architecture. The local runnable skeleton now exposes a narrow read-only `inspect-project` helper over the seeded `projects` table, but that helper is inspection-only and does not replace this document as the canonical source of meaning for project records.

## Relationship To Registry Architecture

`docs/architecture/REGISTRY_AND_QUEUE_ARCHITECTURE.md` is the parent registry architecture for AresForge.

This document specializes only the project registry portion of that architecture. It turns the project-registry concept into a clearer schema design that future issues can reuse when defining project records, project onboarding rules, local operator inputs, queue routing inputs, and multi-project support boundaries.

This document does not implement registry storage, registry loading, runtime queue behavior, dashboard synchronization, or any other executable capability.

The current local `inspect-project` helper should be understood as a conservative visibility surface only. It reads a stored project row, returns explicit JSON for human review, and expands selected metadata fields into top-level output without authorizing routing, automation, or GitHub-state-changing behavior.

## Core Project Definitions

### Project

A project is a managed unit of work, context, rules, and source-of-truth documentation inside AresForge.

### Managed Project

A managed project is a project that AresForge intentionally tracks with explicit ownership, source-of-truth links, approval boundaries, and lifecycle state.

### Self-Managed Project

A self-managed project is a managed project where AresForge is documenting and coordinating its own repository, issue flow, and project memory. AresForge itself is the first self-managed project.

### External Managed Project

An external managed project is a future managed project outside the AresForge repository that AresForge may support later through its own project record, context pack, and review boundaries.

### Project Record

A project record is the canonical schema-shaped description of one managed project. It identifies the project, points to its source-of-truth entry points, and records the boundaries that future agents, local operators, and reviewers must respect.

### Project Owner

A project owner is the human or explicitly delegated human authority responsible for final direction, review, and approval decisions for the project.

### Project Source Of Truth

A project source of truth is the ordered set of documents, repositories, and later-approved systems that define what is authoritative for the project's current state, rules, and decisions.

### Project Autonomy Level

A project autonomy level is the conservative statement of how much execution authority is currently allowed for project work. It defines what kind of assistance is permitted, not what future automation might eventually exist.

### Project Lifecycle State

A project lifecycle state is the current high-level operational state of the project, such as planning, active work, paused work, blocked work, maintenance, or archived status.

### Project Context Pack

A project context pack is the set of entry-point documents and references future agents or local operator flows should read to understand the project's current rules, roadmap, architecture, operating constraints, and required evidence.

## Project Record Minimum Useful Schema

| Field | Required now? | Future implementation? | Description | Example value |
|---|---|---|---|---|
| `project_id` | Yes | Yes | Stable unique identifier for the managed project. | `aresforge` |
| `project_name` | Yes | Yes | Human-readable project name. | `AresForge` |
| `project_slug` | Yes | Yes | Stable slug used in file naming, registry references, and future routing. | `aresforge` |
| `project_type` | Yes | Yes | Project classification that distinguishes self-managed, external, reference-only, or archived records. | `self_managed` |
| `lifecycle_state` | Yes | Yes | Current high-level project state. | `active` |
| `primary_owner` | Yes | Yes | Human owner responsible for final direction and review. | `human owner` |
| `approval_authority` | Yes | Yes | Explicit authority model for approvals and governance-sensitive decisions. | `human_owner` |
| `source_of_truth_priority` | Yes | Yes | Ordered rule for which project memory sources take precedence. | `repo_docs_first` |
| `repository_url` | Yes | Yes | Repository URL for the managed project when applicable. | `https://github.com/yoey2112/aresforge` |
| `local_path` | Yes | Yes | Expected local workspace path when the project is locally available. | `C:\Projects\aresforge` |
| `default_branch` | Yes | Yes | Default review and integration branch. | `main` |
| `documentation_roots` | Yes | Yes | Root documentation locations that should be reviewed before project-state-changing work. | `["docs/", ".agent/"]` |
| `context_documents` | Yes | Yes | Core project context documents that act as the first reading list. | `["docs/context/BUILD_STATE.md", "docs/context/AGENT_CONTEXT.md"]` |
| `roadmap_document` | Yes | Yes | Primary roadmap or sequencing document for the project. | `docs/roadmap/ROADMAP.md` |
| `active_issue_policy` | No | Yes | Rule for how active issues should be interpreted or limited for the project. | `single_active_substantive_issue_preferred` |
| `autonomy_level` | Yes | Yes | Conservative execution authority allowed for the project right now. | `manual_only` |
| `allowed_operations` | Yes | Yes | Explicit list of operation categories allowed for the project in the current phase. | `["human-reviewed documentation updates", "human-reviewed GitHub PR creation"]` |
| `blocked_operations` | Yes | Yes | Explicit list of operation categories that remain blocked or require future governance. | `["autonomous merge", "repo settings changes"]` |
| `validation_requirements` | Yes | Yes | Minimum checks required before project work is considered review-ready. | `["git diff --check", "git diff --cached --check", "source-of-truth review"]` |
| `closeout_requirements` | Yes | Yes | Requirements that must be satisfied before project-state-changing work closes out. | `["update BUILD_STATE", "update AGENT_CONTEXT", "update ROADMAP"]` |
| `registry_links` | No | Yes | Links to related agent, model, queue, capability, or skill registry records. | `{"parent_architecture":"docs/architecture/REGISTRY_AND_QUEUE_ARCHITECTURE.md"}` |
| `notes` | No | Yes | Freeform project-specific notes that do not fit another field. | `AresForge is the first self-managed reference project.` |

## Required M2 Documentation-Only Fields

The following fields are required now for M2 design and planning:

- `project_id`
- `project_name`
- `project_slug`
- `project_type`
- `lifecycle_state`
- `primary_owner`
- `approval_authority`
- `source_of_truth_priority`
- `repository_url`
- `local_path`
- `default_branch`
- `documentation_roots`
- `context_documents`
- `roadmap_document`
- `autonomy_level`
- `allowed_operations`
- `blocked_operations`
- `validation_requirements`
- `closeout_requirements`

These fields are the minimum useful documentation-only record because they let future agents and human reviewers identify the project, find its source documents, understand its authority boundaries, and confirm what remains blocked during M2.

## Optional M2 Documentation-Only Fields

These fields are useful during M2 but are not required for every project record:

| Field | Purpose | Example value |
|---|---|---|
| `project_description` | Short human-readable summary of the project. | `Local-first AI project orchestration system.` |
| `project_goals` | Current high-level goals for the project. | `["Self-manage AresForge safely before multi-project expansion"]` |
| `stakeholder_notes` | Important context about stakeholders or review expectations. | `Human owner remains final escalation authority.` |
| `milestone_strategy` | Notes about milestone structure or sequencing approach. | `Complete M2 documentation-only registry design before implementation work.` |
| `risk_notes` | Important project-specific risk reminders. | `Do not infer automation authority from registry presence.` |
| `integration_notes` | Notes about expected integrations or boundaries. | `GitHub is current external state surface; dashboard is future only.` |
| `model_preferences` | Non-authoritative model preferences for future planning. | `Prefer local-first models for draft and review support.` |
| `queue_preferences` | Planning notes about future queue participation. | `Use lifecycle queues defined in future queue registry work.` |
| `dashboard_preferences` | Planning notes for future dashboard visibility. | `Show project health, active issue, and source-of-truth entry points.` |

## Future Implementation-Only Fields

These fields are reserved for later implementation work and should not be treated as active M2 capability:

| Field | Intended future use |
|---|---|
| `registry_storage_path` | Canonical file or storage location for the record once registry storage exists. |
| `dashboard_project_id` | Dashboard-side identifier for mirroring the project record. |
| `queue_namespace` | Namespace or prefix used by future queue storage or routing systems. |
| `agent_assignment_policy` | Structured rule for assigning work to agent roles. |
| `model_routing_policy` | Structured rule for model selection and validation routing. |
| `automation_policy_id` | Reference to a future governance-approved automation policy. |
| `audit_log_path` | Path or store for future audit events related to the project. |
| `last_registry_validation_at` | Timestamp of the last structured registry validation run. |
| `last_documentation_freshness_check_at` | Timestamp of the last formal freshness check. |
| `project_health_state` | Computed health or readiness state for dashboards or operators. |
| `external_connector_ids` | Safe references to future approved external connectors or integrations. |

## Field Value Conventions

### `project_type`

Recommended values:

- `self_managed`
- `managed_external`
- `reference_only`
- `archived`

### `lifecycle_state`

Recommended values:

- `planning`
- `active`
- `paused`
- `blocked`
- `maintenance`
- `archived`

### `source_of_truth_priority`

Recommended values:

- `repo_docs_first`
- `github_first`
- `dashboard_first_future`
- `mixed_human_review_required`

### `autonomy_level`

Recommended values:

- `manual_only`
- `advisory_only`
- `assisted_execution`
- `human_approved_automation`
- `governed_autonomy_future`

### `approval_authority`

Recommended values:

- `human_owner`
- `delegated_human`
- `governance_board_future`

### `allowed_operations` And `blocked_operations`

These fields should always be explicit lists of operation categories. They should not be inferred from project type, issue type, or registry presence alone.

Recommended list-item style:

- Use short operation phrases.
- Prefer reviewable categories over vague statements.
- Record blocked governance-sensitive operations explicitly even when they seem obvious.
- Treat anything not clearly allowed as conservatively blocked until human review says otherwise.

## AresForge Self-Project Record Example

The following example shows how AresForge should represent itself as the first self-managed project during M2:

```yaml
project_id: aresforge
project_name: AresForge
project_slug: aresforge
project_type: self_managed
lifecycle_state: active
primary_owner: human owner
approval_authority: human_owner
source_of_truth_priority: repo_docs_first
repository_url: https://github.com/yoey2112/aresforge
local_path: C:\Projects\aresforge
default_branch: main
documentation_roots:
  - docs/
  - .agent/
context_documents:
  - docs/context/BUILD_STATE.md
  - docs/context/AGENT_CONTEXT.md
  - docs/roadmap/ROADMAP.md
  - docs/architecture/ISSUE_LIFECYCLE_AGENT_PIPELINE.md
  - docs/architecture/REGISTRY_AND_QUEUE_ARCHITECTURE.md
roadmap_document: docs/roadmap/ROADMAP.md
active_issue_policy: single_active_substantive_issue_preferred
project_context_pack:
  roadmap_document: docs/roadmap/ROADMAP.md
  parent_registry_architecture: docs/architecture/REGISTRY_AND_QUEUE_ARCHITECTURE.md
  project_registry_schema: docs/architecture/PROJECT_REGISTRY_SCHEMA.md
autonomy_level: manual_only
allowed_operations:
  - human-reviewed documentation updates
  - human-reviewed local branch work
  - human-reviewed validation commands
  - human-reviewed GitHub issue and pull request inspection
  - human-reviewed GitHub branch push and draft PR creation
blocked_operations:
  - autonomous merge
  - autonomous issue closure
  - repo settings changes
  - branch protection changes
  - ruleset changes
  - secrets changes
  - workflow changes
  - releases or tags
  - GitHub Projects changes
validation_requirements:
  - review required source-of-truth docs before editing
  - run git diff --check
  - run git diff --cached --check before commit
  - confirm Issue #39 remains unchanged
  - confirm no automation or governance boundary changes were introduced
closeout_requirements:
  - update docs/context/BUILD_STATE.md as needed
  - update docs/context/AGENT_CONTEXT.md as needed
  - update docs/roadmap/ROADMAP.md as needed
  - report documentation impact in PR evidence
  - preserve non-authority and human-review boundaries
registry_links:
  parent_architecture: docs/architecture/REGISTRY_AND_QUEUE_ARCHITECTURE.md
  skill_registry: .agent/AGENT_REGISTRY.md
notes:
  - AresForge is the first self-managed project and reference record for future managed projects.
  - M2 remains documentation-only architecture.
```

`manual_only` is the safest current example value because M2 has not authorized runtime automation. A future issue could raise the record to `advisory_only` or another higher value only through explicit human-reviewed governance changes.

## External Managed Project Example

The following example is illustrative only. It uses placeholder-safe values and does not represent any real client or private project:

```yaml
project_id: sample-client-portal
project_name: Sample Client Portal
project_slug: sample-client-portal
project_type: managed_external
lifecycle_state: planning
primary_owner: delegated project sponsor
approval_authority: delegated_human
source_of_truth_priority: mixed_human_review_required
repository_url: https://github.com/example-org/sample-client-portal
local_path: D:\ManagedProjects\sample-client-portal
default_branch: main
documentation_roots:
  - docs/
  - operations/
context_documents:
  - docs/context/PROJECT_CONTEXT.md
  - docs/context/BUILD_STATE.md
  - docs/roadmap/ROADMAP.md
roadmap_document: docs/roadmap/ROADMAP.md
active_issue_policy: human_reviewed_multi_issue_allowed
autonomy_level: advisory_only
allowed_operations:
  - human-reviewed documentation analysis
  - human-reviewed issue triage recommendations
blocked_operations:
  - autonomous merge
  - secrets access
  - production deployment changes
validation_requirements:
  - verify source-of-truth docs exist or are marked planned
  - verify approval authority before use
closeout_requirements:
  - update project source-of-truth docs before closeout
  - preserve human-review boundaries
notes:
  - Illustrative example only. Not real project data.
```

## Validation Rules

Project registry records should pass the following validation checks before they are considered usable:

- Required fields must exist.
- `project_slug` must be stable and unique.
- Source-of-truth documents must exist or be explicitly marked planned.
- Approval authority must be explicit.
- Autonomy level must not imply automation unless governance allows it.
- `allowed_operations` and `blocked_operations` must not conflict.
- `repository_url` and `local_path` must be reviewed before use.
- `documentation_roots` must be reviewed before documentation-sync work.
- Issue #39 protection remains project-specific validation evidence for AresForge only.

For M2, these validation rules remain documentation-only review expectations. They do not create scripts, commands, or automated validation services.

## Relationship To Other Registries

Project records should link outward to other registries without replacing them:

- Agent registry: identifies which agent roles may operate within the project's lifecycle and approval boundaries.
- Model registry: identifies which local or later-approved external models are suitable for the project's allowed work.
- Queue registry: identifies which queue lanes, transitions, and handoffs are relevant for the project.
- Capability registry: identifies which bounded work categories the project uses or requires.
- Skill registry: identifies which advisory repo-owned skills help agents operate consistently within the project.

The project registry is the anchor that tells future routing and review systems which project a work item belongs to before they consult those other registries.

## Relationship To Issue Lifecycle

The project registry should support the lifecycle roles defined in `docs/architecture/ISSUE_LIFECYCLE_AGENT_PIPELINE.md`:

- Planning / Next-Issue Agent: identify which project is active, what its context pack is, and what authority boundaries apply.
- Triage / Routing Agent: route work using project-specific ownership, lifecycle state, and blocked-operation rules.
- Worker Agent: confirm which repositories, docs, and operation categories are in scope.
- Verification Agent: confirm the work matched the project record and did not violate project boundaries.
- Testing Agent: confirm project-specific validation requirements were met.
- Documentation Agent: use project-specific documentation roots and context documents to complete documentation-before-closeout work.
- Final Closeout / Lifecycle Controller Agent: confirm project-specific closeout requirements before issue closure recommendations.

## Relationship To Documentation-Sync And Closeout

Project records should make documentation-before-closeout easier to apply consistently:

- Project records identify required source-of-truth docs.
- Project-state-changing issues must update source-of-truth docs before closeout.
- No related documentation-update issue should be created by default.
- Separate reconciliation or documentation-update issues are exception paths only.

This means the project registry should strengthen the current lifecycle correction, not recreate the stale-documentation loop that Issue #75 was meant to end.

## Human Approval Boundaries

Registry presence does not authorize action.

The human owner remains the final authority for project meaning, approval boundaries, issue direction, PR review, merge decisions, closeout decisions, and any governance-sensitive change.

Any future automation requires later explicit governance, validation expectations, and human-approved implementation work.

Autonomy levels must be interpreted conservatively. If a record is ambiguous, human review takes precedence over inferred authority.

## M2 Restrictions

This issue does not implement:

- Scripts
- Runnable automation
- Workflows
- Commands
- Registry storage
- Dashboard code
- Queue execution
- Model routing
- GitHub Project changes
- Repo settings changes
- Branch protection or ruleset changes
- Secrets
- Releases or tags
- Auto-merge
- Autonomous approval
- Autonomous issue closure
- Autonomous PR merge
- Autonomous issue routing

## Open Design Questions

The following questions remain intentionally open after this schema design:

- Markdown vs YAML/JSON registry storage
- Whether project records live under `docs/architecture`, `docs/registry`, `.agent`, or another future path
- How project records are loaded by future local operator tools
- How dashboard state will mirror project registry data
- How project health is computed
- How external project credentials and connectors will be represented safely
