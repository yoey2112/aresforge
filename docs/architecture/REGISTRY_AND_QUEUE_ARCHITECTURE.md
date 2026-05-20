# AresForge Registry And Queue Architecture

## Purpose

This document defines the M2 documentation-only architecture for AresForge project, agent, model, and queue registries, plus the related capability and skill registry layers.

Registries are needed because the existing M2 lifecycle foundation now describes how work should move, but it does not yet define the canonical records that future planning, routing, local operator workflows, local-first LLM selection, queue visibility, and multi-project support should read from.

This document is the architecture bridge between the current issue lifecycle pipeline and future orchestration work. It explains how registry definitions should support the local operator workflow, future prompt package generation, future evidence package generation, future queue routing, future local LLM routing, and future management of projects beyond AresForge itself.

During M2, this architecture is documentation only. It does not implement scripts, commands, workflows, services, queue runners, model routers, dashboard code, registry storage, or autonomous behavior.

## Core Definitions

### Project

A project is a managed unit of work, context, rules, and source-of-truth documentation inside AresForge.

A project may be AresForge itself or a future external managed project.

### Agent

An agent is a bounded work role with defined responsibilities, allowed inputs, expected outputs, approval boundaries, and lifecycle handoff expectations.

An agent is a role definition, not a specific model process or runtime instance.

### Model

A model is a local or later-approved external inference engine that can provide one or more bounded capabilities to an agent.

A model is not automatically authorized for every task just because it exists in a registry.

### Queue

A queue is a design-defined work routing lane that groups work items by lifecycle stage, responsibility, or handoff state.

A queue is not the same thing as a GitHub issue, GitHub Project board, or runtime worker process.

### Capability

A capability is a bounded type of work an agent or model may support, such as issue planning, documentation freshness review, implementation assistance, evidence review, verification support, or local operator packaging.

Capabilities describe allowed function, not blanket authority.

### Skill

A skill is a repo-owned markdown instruction package that helps an agent perform a bounded repeatable task consistently.

During M2, skills remain advisory and human-reviewed.

### Work Item

A work item is the unit of work being routed through the lifecycle, such as an issue, a documentation update package, a validation pass, or a closeout package.

The registry architecture assumes issues will often be the primary work item, but it does not require every future work item to be a GitHub issue.

### Handoff

A handoff is the documented transfer of responsibility, context, evidence, and next-step expectations from one lifecycle role or queue state to another.

### Registry

A registry is the authoritative or future-authoritative record that defines a class of managed entities, their minimum fields, their boundaries, and their review lifecycle.

## Concept Boundaries

### Agent vs Skill

An agent is a role with responsibilities and approval boundaries.

A skill is reusable guidance that an agent may consult while performing part of that role.

Skills help agents work consistently, but skill presence alone does not create a new role or authorize behavior.

### Agent vs Model

An agent defines who should do the work in process terms.

A model defines which inference system may support that work in execution terms.

One agent role may use different models over time, and one model may support multiple agent roles if governance and capability checks allow it.

### Model vs Capability

A model is a provider of potential ability.

A capability is the named task category that must be requested, reviewed, and routed.

Capabilities should be narrower than model existence so that the system does not over-authorize a model just because it is available.

### Queue vs Issue

An issue is a planning and tracking artifact.

A queue is a lifecycle routing concept that describes where work currently belongs.

One issue may move across many queues during its lifecycle, and some future queue items may not map one-to-one with issues.

### Queue vs GitHub Project

A queue is an AresForge lifecycle and orchestration concept.

A GitHub Project is an optional GitHub planning surface.

Future queue views may be mirrored into GitHub Projects, files, a dashboard, or another interface, but queue meaning must not depend on GitHub Project state alone.

### Project Registry vs Repository Documentation

The future project registry defines managed project records and their minimum fields.

Repository documentation remains the current M2 source of truth for project memory, governance, roadmap state, and architecture decisions.

The project registry must not silently replace repository documentation during M2.

### Runtime State vs Source-Of-Truth Documentation

Runtime state is transient execution state such as which queue item is active, which model was selected, or which handoff is waiting.

Source-of-truth documentation is the human-reviewed project memory that defines what should exist, what is allowed, and what is authoritative.

During M2, source-of-truth documentation remains primary.

## Registry Overview

The registry architecture defines six related registry layers:

- Project registry
- Agent registry
- Model registry
- Queue registry
- Capability registry
- Skill registry

Together, these registries should answer:

- What projects AresForge manages
- Which agent roles exist
- Which models are available and approved
- Which queue lanes and handoffs exist
- Which capabilities each role may request
- Which advisory skills support repeatable work

During M2, these remain design targets described in documentation.

## Project Registry

### Purpose

The project registry should define every managed project that AresForge knows about and the boundaries that make each project safe to route, review, and support.

### Responsibilities

- Identify each managed project uniquely.
- Define the project's source-of-truth locations.
- Define project-specific rules, context, and approval boundaries.
- Define how project-specific registries relate to shared AresForge-wide architecture.
- Preserve separation between AresForge's own repo state and future external managed project state.

### Authoritative Scope

The future project registry should be authoritative for managed project identity, project-scoped registry links, context entry points, and project-level execution boundaries.

It should not replace the detailed architecture, roadmap, governance, or issue history documents for the project itself.

### Minimum Future Fields

- Project ID
- Project name
- Project type
- Owning repository or workspace
- Source-of-truth document entry points
- Human owner or approval authority
- Allowed lifecycle mode
- Allowed autonomy level
- Linked registries
- Active status

### M2 Design-Only Fields

- Intended canonical context documents
- Intended registry ownership rules
- Intended lifecycle participation
- Intended local operator integration points
- Intended evidence package expectations

### Future Implementation-Only Fields

- Runtime project state identifiers
- Dashboard read-model identifiers
- Database keys or storage locations
- Queue subscription bindings
- External connector identifiers
- Project-specific automation toggles if ever approved later

### Relationship To AresForge As Its Own First Managed Project

AresForge is the first managed project and the design reference for this architecture.

That means the initial project registry design should treat the AresForge repository, roadmap, architecture docs, agent context, and build state as the first example of a managed project record.

### Relationship To Future External Managed Projects

Future external projects should be represented as separate managed project entries with their own context, rules, source-of-truth links, and approval boundaries.

AresForge should not flatten external project state into its own docs without clearly marking project ownership and authority.

## Agent Registry

### Purpose

The agent registry should define the recognized AresForge lifecycle and specialist agent roles, their responsibilities, their boundaries, and their allowed relationships to capabilities, skills, models, and queues.

### Responsibilities

- Name and describe each agent role.
- Define allowed lifecycle stages and handoffs.
- Define required inputs and expected outputs.
- Define approval boundaries and escalation rules.
- Link agent roles to capabilities, skills, model requirements, and queue participation.

### Authoritative Scope

The future agent registry should be authoritative for agent role identity, lifecycle role definitions, and approved responsibility boundaries.

It should not replace detailed operating rules that remain better described in architecture, governance, or prompt documents.

### Minimum Future Fields

- Agent ID
- Agent name
- Lifecycle status
- Role summary
- Required inputs
- Expected outputs
- Allowed capabilities
- Queue participation
- Human approval boundaries
- Required evidence outputs

### M2 Design-Only Fields

- Documentation-only role descriptions
- Planned lifecycle relationships
- Planned skill associations
- Planned model-capability expectations
- Planned escalation conditions

### Future Implementation-Only Fields

- Runtime agent instance identifiers
- Health or availability signals
- Queue consumer bindings
- Execution environment bindings
- Telemetry or audit links
- Scheduling or concurrency limits

### Relationship To Current Agent Roles In `AGENT_CONTEXT.md`

The current agent role list in `docs/context/AGENT_CONTEXT.md` is the present documentation source for initial role names such as Planning Agent, Documentation Agent, QA Agent, Test Agent, and Release Agent.

The future agent registry should formalize those roles rather than inventing a conflicting second taxonomy.

### Relationship To `.agent/AGENT_REGISTRY.md`

`.agent/AGENT_REGISTRY.md` is currently a skill registry, not a full agent registry.

It should be treated as the current advisory record of repo-owned skills that agents may consult, not as the authoritative definition of all agent roles.

### Relationship To Lifecycle Roles From `ISSUE_LIFECYCLE_AGENT_PIPELINE.md`

The lifecycle roles defined in `docs/architecture/ISSUE_LIFECYCLE_AGENT_PIPELINE.md` should remain the authoritative design for core issue-flow roles during M2.

The future agent registry should import and formalize those lifecycle roles, including:

- Planning / Next-Issue Agent
- Triage / Routing Agent
- Worker Agent
- Verification Agent
- Testing Agent
- Debug Routing Agent
- Documentation Agent
- Final Closeout / Lifecycle Controller Agent

## Model Registry

`docs/architecture/MODEL_REGISTRY_SCHEMA.md` is the canonical M2 source-of-truth document for model records and bounded local LLM routing rules.

### Purpose

The model registry should define which local and later-approved external models are available for which capabilities, under which privacy, cost, validation, and approval constraints.

### Responsibilities

- Name available models and providers.
- Record capability fit and limitations.
- Record privacy and cost characteristics.
- Record whether use is local-only, approved-external, or blocked.
- Support routing requests from agent roles without granting unrestricted authority.

### Authoritative Scope

The future model registry should be authoritative for approved model options, capability fit metadata, routing constraints, and validation expectations tied to model choice.

It should not replace governance decisions about whether a class of work is allowed at all.
It also should not replace the dedicated model-registry schema document that defines required record fields, local endpoint conventions, task-class rules, routing-priority rules, fallback rules, and evidence expectations for M2.

### Minimum Future Fields

- Model ID
- Model name
- Provider
- Execution location
- Capability profile
- Privacy profile
- Cost profile
- Validation suitability
- Approval status
- Known limitations

### M2 Design-Only Fields

- Intended routing factors
- Intended validation categories
- Intended local-first priority rules
- Intended privacy and cost notes
- Intended capability comparison notes

### Future Implementation-Only Fields

- Runtime adapter identifiers
- API endpoints or local service addresses
- Version pinning data
- Benchmark or evaluation references
- Health-check status
- Observed latency or throughput data

### Local-First LLM Routing Expectations

Model routing should prefer local models first when capability, privacy, and validation quality are sufficient for the requested work.

The routing layer should treat local-first preference as a policy input, not as proof that every local model is acceptable for every task.
The dedicated routing conventions now live in `docs/architecture/MODEL_REGISTRY_SCHEMA.md`.

### Ollama / Local Model Use

Ollama and other local model runners are the expected early execution surface for model registry design because they align with AresForge's local-first direction and current evidence-review history.

The model registry should be able to describe locally hosted implementation-support models, validation-support models, documentation-support models, and evidence-review models separately.

### Optional External Model Adapters Only If Approved Later

External model adapters may exist later, but they must remain optional and separately approved.

Registry presence for a future external adapter does not authorize use until governance and project documentation explicitly allow it.

### Privacy, Cost, Capability, And Validation Considerations

Model routing should consider:

- Whether project data may leave the local machine
- Whether the model cost is justified for the task
- Whether the model has the right capability profile
- Whether the model is appropriate for validation rather than implementation drafting
- Whether a second model or human review is required for higher-risk conclusions

Validation-support models should generally be held to stricter evidence expectations than implementation-support models.

### Relationship To The Runnable Skeleton

Issue #81 introduced a minimal runnable local `models` table plus a human-triggered `test-ollama` connectivity check.

Issue #85 does not turn that surface into autonomous runtime routing. Instead, it defines the documentation-first schema and routing rules that later human-triggered operator helpers or read-only inspection commands may follow.

## Queue Registry

### Purpose

The queue registry should define the visible routing lanes that work items move through as they progress across planning, routing, implementation, verification, testing, documentation, closeout, and failure loops.

### Responsibilities

- Define queue identities and meanings.
- Define allowed inbound and outbound handoffs.
- Define queue entry and exit conditions.
- Define required evidence or approvals at each transition.
- Preserve visibility into blocked, failed, waiting, and approval-required work.

### Authoritative Scope

The future queue registry should be authoritative for queue names, queue meanings, transition intent, handoff requirements, and failure-loop routing definitions.

It should not replace the detailed issue requirements or human approval decisions for a specific work item.

### Minimum Future Fields

- Queue ID
- Queue name
- Queue purpose
- Accepted work-item types
- Entry criteria
- Exit criteria
- Allowed next queues
- Required handoff evidence
- Human approval requirement
- Failure routing rule

### M2 Design-Only Fields

- Planned lifecycle mapping
- Planned role ownership
- Planned local operator visibility needs
- Planned evidence package references
- Planned approval checkpoint notes

### Future Implementation-Only Fields

- Runtime queue storage identifiers
- Queue depth or metrics
- Consumer bindings
- Retry counters
- Dashboard aggregation fields
- Notification or alert integrations if ever approved later

### Relationship To Issue Lifecycle Stages

The queue registry should map directly to the lifecycle stages defined in `docs/architecture/ISSUE_LIFECYCLE_AGENT_PIPELINE.md`.

That means queues should preserve the order and gate logic between planning, triage, worker, verification, testing, documentation, and final closeout rather than bypassing them.

### Relationship To Handoffs

Queue transitions should require explicit handoff packages, evidence summaries, or review notes that explain why the work item is ready for the next stage.

The registry should make those expectations visible so that handoffs are structured rather than inferred.

### Relationship To Local Operator Workflow

The local operator workflow may later read queue definitions to prepare prompt packages, validation checklists, documentation-sync handoffs, and PR or closeout evidence packages.

No queue-reading command is implemented by this issue.

### Human Approval Checkpoints

The queue registry should make human approval requirements explicit for transitions such as:

- Starting implementation work
- Staging and committing
- Pushing branches
- Creating pull requests
- Merging pull requests
- Closing issues outside normal reviewed merge behavior
- Approving governance-sensitive queue or routing changes

### Failure Loop Routing

The queue registry should define how failed verification or testing returns a work item to the correct corrective path without collapsing documentation and closeout gates.

Failure routing should preserve evidence and explain why the work item moved backward.

## Capability Registry

### Purpose

The capability registry should define the named task categories that agents may request, models may support, skills may assist, and queues may require.

### Responsibilities

- Provide stable names for bounded work types.
- Allow agent roles to request work by capability rather than by vague model preference.
- Allow models to advertise bounded support without overclaiming.
- Allow queues and handoffs to express required capability expectations.
- Support safer routing, evaluation, and future auditing.

### Authoritative Scope

The future capability registry should be authoritative for capability names, intent, and bounded relationships to agent roles, models, queues, and skills.

It should not authorize work outside governance or issue scope.

### Minimum Future Fields

- Capability ID
- Capability name
- Capability description
- Allowed agent roles
- Candidate supporting models
- Related skills
- Related queues
- Risk level
- Human approval notes

### Relationship To Agents, Skills, Models, And Queues

Agents should request capabilities.

Models should be matched against capability needs.

Skills should describe how to perform capability work consistently.

Queues should define which capabilities are expected for work items in that lane.

### How Capabilities Should Avoid Over-Authorizing Agents

Capabilities should stay narrow enough that an agent does not gain blanket authority from one broad label like "development" or "automation."

For example, documentation freshness review, PR evidence preparation, implementation drafting, and merge approval should remain distinct capability concepts with different approval rules.

## Skill Registry Relationship

`.agent/AGENT_REGISTRY.md` and `.agent/skills/` are the current repo-owned skill inventory and skill file locations.

Within the broader registry architecture:

- `.agent/AGENT_REGISTRY.md` is the current advisory skill registry
- `.agent/skills/` stores the current markdown skill definitions
- `docs/agents/AGENT_SKILLS_MODEL.md` defines the canonical repo-owned markdown skill model

During M2, repo-owned markdown skills remain advisory and human-reviewed.

This architecture does not convert skills into runnable automation, hidden prompts, services, bots, workflows, or queue consumers.

## Registry Ownership And Source-Of-Truth

### Which Documentation Is Authoritative Now

During M2, the authoritative project-memory layer remains repository documentation plus explicit human decisions.

Key authoritative documents currently include:

- `docs/context/BUILD_STATE.md`
- `docs/context/AGENT_CONTEXT.md`
- `docs/roadmap/ROADMAP.md`
- `docs/architecture/ISSUE_LIFECYCLE_AGENT_PIPELINE.md`
- `docs/architecture/LOCAL_OPERATOR_WORKFLOW.md`
- `docs/agents/DOCUMENTATION_AGENTS.md`
- `docs/agents/AGENT_SKILLS_MODEL.md`
- `.agent/AGENT_REGISTRY.md`

### Which Future Registry Documents Or Files May Become Authoritative Later

Later phases may introduce dedicated registry documents or structured files for:

- Project records
- Agent records
- Model records
- Queue definitions
- Capability definitions
- Skill metadata views

Those future files may become authoritative only after explicit human-approved design and implementation work says so.

### Human Owner Authority

The human owner remains the final authority for:

- Registry meaning
- Approval boundaries
- Governance changes
- Autonomy changes
- Model approvals
- Queue transitions that require human judgment
- Project onboarding and offboarding

### How Registry Updates Should Be Reviewed

Registry changes should be reviewed through normal branch and PR review with explicit documentation impact reasoning, validation evidence, and boundary confirmation.

Project-state-changing registry work must review `BUILD_STATE`, `AGENT_CONTEXT`, and `ROADMAP` at minimum and update them when needed before closeout.

### How Registry Updates Should Avoid Documentation-Update Issue Loops

Registry updates should occur inside the same lifecycle as the project-state-changing issue that caused the update.

Separate source-of-truth documentation-update issues should not be created by default because they recreate the reconciliation loop that M2 is explicitly correcting.

## Registry Update Lifecycle

The design-only registry update lifecycle is:

1. Identify whether the issue changes registry meaning, scope, authority, or relationships.
2. Review the relevant source-of-truth docs before editing.
3. Update architecture and registry documents for the in-scope change.
4. Update `docs/context/BUILD_STATE.md`, `docs/context/AGENT_CONTEXT.md`, and `docs/roadmap/ROADMAP.md` when needed.
5. Validate diffs and confirm the changes remain documentation-only and issue-scoped.
6. Include registry impact, validation results, and source-of-truth review in PR and closeout evidence.
7. Do not create related source-of-truth update issues by default.

During M2, this lifecycle is documentation only and does not implement commands or automation.

## Relationship To Issue Lifecycle Pipeline

### Planning / Next-Issue Agent

The Planning / Next-Issue Agent should use registry definitions to understand which project is active, which lifecycle roles exist, which queues are available, and which capability gaps still need design or implementation work.

### Triage / Routing Agent

The Triage / Routing Agent should use registry definitions to map work items to the right lifecycle role, capability expectations, and queue path without inferring authority from model or skill presence alone.

### Worker, Verification, Testing, Documentation, And Closeout Roles

These roles should use registries to understand:

- Which capabilities they are expected to perform
- Which skills may support them
- Which models are suitable
- Which queue transitions are allowed
- Which evidence is required at handoff

### Documentation-Before-Closeout Gate Preservation

The registry architecture must preserve the documentation-before-closeout gate by ensuring that queue routing, model selection, and agent-role definitions still require documentation review and source-of-truth updates before final closeout.

Registry presence must never be used to bypass the Documentation Agent or Final Closeout / Lifecycle Controller role.

## Relationship To Local Operator Workflow

Future local commands may read registry definitions to:

- Prepare issue context
- Suggest queue-aware handoff packages
- Generate prompt package content
- Generate PR evidence package content
- Generate closeout evidence package content
- Highlight approval checkpoints

Prompt package generation may use project, agent, capability, queue, and skill registry data to assemble more consistent inputs.

Evidence package generation may use queue and capability definitions to explain why a work item is ready for a given transition.

No commands are implemented by this issue.

## Relationship To Multi-Project Support

Multiple projects may later be represented as separate managed project records linked to shared or project-specific registries.

Each project may define:

- Its own context entry points
- Its own rules and constraints
- Its own autonomy level
- Its own linked registries
- Its own human approval owner

Project-specific source-of-truth must remain separate and clear so that AresForge does not confuse self-management state with external managed project state.

## Relationship To Model Routing

Agents should request capabilities, not hard-code model choice as the first decision.

Model routing should then select the best local or later-approved model that satisfies:

- Capability needs
- Privacy needs
- Cost tolerance
- Performance expectations
- Validation quality requirements

Validation-support models differ from implementation-support models because they are expected to produce review-quality evidence, skepticism, and risk detection rather than only draft generation.

Privacy, cost, and performance should influence routing explicitly rather than being left to hidden preference.
During M2, routing recommendations remain advisory or human-triggered only, with governance-sensitive actions explicitly blocked from autonomous selection.

## Human Approval Boundaries

The following must remain human-approved:

- Governance changes
- Registry meaning changes that alter authority
- Model approval for sensitive or external use
- Queue changes that alter lifecycle gates
- Approval, merge, and closeout decisions
- Project onboarding that expands managed scope

The following may be advisory during M2:

- Registry design proposals
- Skill guidance
- Queue design suggestions
- Model capability comparisons
- Prompt and evidence package preparation

The following may become automatable later only after explicit governance:

- Registry-aware prompt package generation
- Registry-aware evidence package generation
- Read-only queue views
- Read-only model routing recommendations

The following must never be inferred from registry presence alone:

- Approval authority
- Merge authority
- Issue-closing authority
- Queue execution authority
- Runtime automation approval
- External data-sharing approval

## M2 Restrictions

This issue does not implement:

- Scripts
- Runnable automation
- Workflows
- Commands
- Services
- Watchers
- Bots
- Dashboard code
- Registry storage implementation
- Queue execution implementation
- Model routing implementation
- GitHub Project changes
- Repository setting changes
- Branch protection or ruleset changes
- Secrets
- Releases or tags
- Auto-merge
- Autonomous approval
- Autonomous issue closure
- Autonomous PR merge
- Autonomous issue routing

## Open Design Questions

The following decisions remain intentionally unresolved after this issue:

- Which registry storage format should eventually be used
- Whether registries should remain markdown or move to structured YAML or JSON
- What local dashboard read model should exist
- Whether queues should be represented in files, database tables, GitHub labels, GitHub Project state, or dashboard state
- How autonomy levels should be represented per project and per queue
- How model evaluation and routing-quality data should be captured
- How queue history and handoff audit data should be stored
- How registry versioning and migration should work if structured storage is later introduced
- How local-only and external-approved model adapters should share capability metadata
