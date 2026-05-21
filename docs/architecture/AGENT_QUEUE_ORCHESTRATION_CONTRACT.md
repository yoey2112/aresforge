# Agent Queue And Orchestration Contract (M7)

## Purpose

Define a human-supervised governance-aware intake and queue planning contract without autonomous mutation.

## Queue Item Identity And Required Fields

Each queue item is derived from one issue and includes:

- `queue_item_id` (`issue-<number>`)
- `issue_number`
- `issue_title`
- `issue_url` (if available)
- `labels`
- `queue_state`
- `lifecycle_state`
- `readiness` (`ready`, `attention_needed`, `blocked`)
- `blocked_reasons`
- `attention_reasons`
- `recommended_next_step`
- `batch_group`
- `planning_state`

## Governance-Aware Intake Boundary

Planning intake is split into explicit stages:

- Issue discovery: read-only issue listing/view or deterministic local issue file.
- Issue classification: normalize metadata and classify implementation references vs safety/historical references.
- Queue planning: map each issue to readiness and execution guidance.
- Persisted planning state design: expose state + transition-history design fields for inspection/reporting only.
- Batch closeout planning: read-only parent/child readiness checks.
- Closeout execution: explicitly out of scope and human-gated.

## Persisted Planning State Design

State vocabulary:

- `queued`
- `planned`
- `ready`
- `blocked`
- `in_progress`
- `review_pending`
- `closeout_ready`
- `closed`
- `skipped`

Transition history fields:

- `work_item_identifier`
- `previous_state`
- `new_state`
- `timestamp`
- `reason`
- `actor_or_command_source`
- `read_only_evidence_references`

## Orchestration Boundaries

- Read-only planning only.
- No autonomous issue, PR, label, merge, or closeout mutation.
- No background scheduler/poller.
- Human review gates are mandatory before implementation/validation/closeout transitions.

## Protected Historical Issue

the protected historical reference is always excluded from active implementation linkage and mutation.

