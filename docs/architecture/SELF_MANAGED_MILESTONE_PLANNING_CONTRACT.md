# Self-Managed Milestone Planning Contract

## Purpose

Define the deterministic, read-only, human-gated planning contract for self-managed milestone planning in AresForge.

## Scope

This contract applies to milestone planning output only.

- It defines planning inputs, classification rules, sequencing rules, and output requirements.
- It does not authorize autonomous issue creation, issue mutation, PR mutation, or closeout mutation.
- It separates planning from execution. Planned output is advisory until human-approved.

## Command Surface Boundary

This contract is authoritative for future milestone planning surfaces, including:

- planned M15 issue planning command scope (#251)
- planned M15 issue script generation scope (#252)

Implementation of those commands is out of scope for this contract document.

## Read-Only Inspection Inputs

AresForge planning MAY inspect the following inputs in read-only mode:

- local repository documentation and architecture contracts
- local milestone planning definitions and optional local planning-state files
- read-only GitHub issue, milestone, and repository governance metadata fetched through human-triggered commands
- read-only governance inspection outputs (including project-specific milestone naming/mapping warnings)

AresForge planning MUST NOT mutate any inspected source during planning.

## Candidate Work Classification Expectations

Planned candidate work items MUST be classified deterministically into explicit categories:

- parent milestone coordination item
- implementation child item
- documentation/reconciliation child item
- validation/regression child item
- blocked/dependent item (not ready)
- historical or non-active reference context

Classification MUST be reproducible from the same inputs.

## Parent/Child Sequencing Expectations

Milestone plans MUST enforce deterministic sequencing:

- parent milestone issue planning precedes child planning output
- child items MUST include explicit parent linkage expectations
- child ordering MUST be stable and reproducible
- not-ready or blocked children MUST be emitted as blocked rather than silently omitted

## Dependency Handling Expectations

When dependencies exist between planned children:

- dependencies MUST be represented explicitly in planning output
- ordering recommendations MUST reflect dependency direction
- blocked status MUST identify the blocking dependency
- dependency handling remains advisory and human-gated; AresForge MUST NOT auto-resolve or auto-reorder live GitHub state

## Deterministic Planning Outputs

Milestone planning output MUST be deterministic and machine-checkable.

Minimum output expectations:

- command identity and `ok` status
- `inspection_mode` indicating read-only planning
- `mutation_posture` indicating human-gated mutation only
- normalized parent milestone summary
- normalized child work summary with classification and dependency state
- advisory sequencing recommendations
- explicit safety warnings and blocked-item rationale where applicable

## Documentation Reconciliation Expectations

Milestone planning output MUST include documentation reconciliation guidance:

- identify affected source-of-truth documents
- identify whether updates are required, reviewed-current, or not-applicable
- keep reconciliation planning separate from closeout execution

For M15 scope, this contract is the source of truth for future reconciliation work (#253), but does not itself complete that reconciliation.

## Validation Evidence Expectations

Milestone planning output MUST define required validation evidence expectations for downstream implementation items:

- required local validation command set
- expected pass signal format
- explicit failure gating guidance

Validation evidence remains human-produced and human-reviewed.

## Explicit Mutation Boundaries

By default, future milestone planning commands governed by this contract MUST remain read-only.

Not authorized:

- autonomous GitHub issue create/edit/close
- autonomous PR create/update/merge
- autonomous comment/label/milestone/assignee/project/release/tag mutation
- autonomous queue transitions, schedulers, polling loops, or background mutation workers

Authorized mutation posture:

- human-reviewed, human-triggered branch and PR workflows
- copy/paste or otherwise explicit human-triggered issue script execution

## Human-Gated GitHub Operation Requirements

Any generated GitHub operation content MUST be explicitly human-gated:

- generated plans are advisory until approved by a human operator
- generated issue creation/update scripts remain manual execution artifacts
- no planner output may claim autonomous execution authority

## Generated PowerShell And Future Issue Script Safety Boundaries

When future planning surfaces emit PowerShell or similar issue scripts:

- script output MUST be deterministic from plan inputs
- script output MUST include explicit human-review and manual-execution posture
- script output MUST avoid hidden execution paths or background execution behavior
- script output MUST preserve read-only default command posture until a human explicitly executes generated mutation commands
- script generation MUST NOT introduce autonomous GitHub mutation behavior

## Safety Posture

- Local-first planning posture remains in effect.
- Human authority remains final for all mutation.
- This contract is planning-only and does not change execution boundaries.
