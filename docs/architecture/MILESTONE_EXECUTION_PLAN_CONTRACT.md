# Milestone Execution Plan Contract

## Purpose

Define the M17 contract for milestone-level orchestration planning and read-only milestone inspection.

## Scope

- In scope for this contract:
  - milestone execution boundaries
  - read-only milestone inspection
  - planning and guarded execution recommendation boundaries
  - evidence and closeout expectations
- Out of scope in this phase:
  - autonomous closeout mutation workflows
  - bulk closeout automation
  - implicit GitHub mutation paths

## Milestone Planning Boundaries

- Milestone planning is milestone-level and parent-led.
- Parent issues define the intended child issue set and sequence.
- Child issues remain the unit of implementation and closeout evidence.
- Planning outputs can recommend next commands but must not perform mutation by default.

## Inspection vs Planning vs Execution

- `inspect-milestone-state`:
  - read-only only
  - no issue closure
  - no PR creation
  - no comments
  - no GitHub edits
- Planning commands:
  - may compute deterministic plans and safety warnings
  - may emit local-only artifacts where already established by existing command contracts
  - must declare non-execution posture (`execution_enabled: false`) for queue planning outputs
  - evidence readiness checkers must declare mutation disabled and operator review required
  - final reconciliation planner must declare planning-only posture and explicit non-mutation fields:
    - `close_issues: false`
    - `create_pr: false`
    - `comment_on_issue: false`
    - `mutation_allowed: false`
    - `operator_review_required: true`
- Guarded execution recommendations:
  - must be explicit and human-triggered
  - must preserve fail-closed behavior for missing gates

## Approval Gates

- Execution recommendations must include explicit operator approval gates.
- No transition from inspection to mutation may occur implicitly.
- Required gates must be surfaced before higher-permission actions.

## Parent/Child Relationship Expectations

- Parent issue should reference child issues clearly.
- Child issues should include explicit parent lineage when possible.
- Missing lineage must be surfaced as a warning/hint, not auto-corrected.

## Required Evidence Fields

- Parent issue summary: issue number, state, title, URL, milestone title.
- Child issue summary: issue number, state, title, URL, milestone title.
- Lineage status: detected/missing and source hints.
- PR/evidence hints: detectable merged PR linkage summary per child issue.
- Read-only boundary confirmations.

## Closeout Expectations

- Closeout remains issue-specific.
- Closeout evidence must be mapped per child issue.
- No bulk closeout action is authorized.
- Parent-level closeout sequencing must follow child evidence reconciliation.

## Mutation Rules

- No implicit GitHub mutation.
- No closeout mutation from inspection commands.
- No issue closure, PR creation, comment creation, or edit operations from milestone inspection.
- No issue execution, closure, PR creation, or comments from milestone queue planning commands.
- Bulk closeout recommendations are not authorized.

## Duplicate/No-Op PR Handling

- Duplicate/no-op PR outcomes must be explicitly recorded when they occur in future execution phases.
- Duplicate/no-op handling never authorizes skipping evidence mapping or issue-specific closeout checks.
- Duplicate/no-op prevention in planning/checking commands must recommend evidence reuse and avoid proposing duplicate implementation PRs when valid merged evidence exists.

## Final Reconciliation Sequencing

- Reconcile child-level evidence first.
- Reconcile parent milestone state second.
- Reconcile source-of-truth docs last.
- When a final reconciliation issue is detectable in child set (for M17 this is `#276`), it must be placed last in recommended execution order.
- Final reconciliation planning MUST verify implementation children are closed or evidence-accounted before emitting `ready_for_final_reconciliation: true`.
- Parent issue MUST remain open while final reconciliation is still open or unaccounted.

## Final Reconciliation Planner Output Contract

The `plan-milestone-final-reconciliation` command MUST emit a planning-only payload with at least:

- `ok`
- `read_only`
- `parent_issue`
- `final_reconciliation_issue`
- `implementation_children`
- `unaccounted_children`
- `docs_likely_required`
- `docs_only_expected`
- `ready_for_final_reconciliation`
- `parent_should_remain_open`
- `close_issues` set to `false`
- `create_pr` set to `false`
- `comment_on_issue` set to `false`
- `mutation_allowed` set to `false`
- `operator_review_required` set to `true`

Evidence mapping expectations in this output SHOULD be schema-oriented rather than heuristic-only, favoring deterministic fields such as:

- `reference_classification.implementation_issue_numbers`
- `reference_classification.explicit_implementation_issue_numbers`
- `merged_pr_evidence`

Duplicate/no-op prevention in this phase MUST reduce false positives by prioritizing issue evidence checker outputs over title-only keyword matching.

## Validation Expectations

- Validation must run in Codex before reporting completion.
- Required validation bundle for this phase:
  - `git diff --check`
  - `python -m pytest`
  - `python -m aresforge inspect-repo-governance`
  - `python -m aresforge inspect-milestone-state --parent-issue <parent>`
  - `python -m aresforge plan-milestone-execution-queue --parent-issue <parent>`
  - `python -m aresforge check-issue-evidence-readiness --issue <issue>`
  - `python -m aresforge check-milestone-evidence-readiness --parent-issue <parent>`
  - `python -m aresforge plan-milestone-final-reconciliation --parent-issue <parent>`
