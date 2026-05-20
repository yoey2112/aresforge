# Agent Queue And Orchestration MVP Contract (M6)

## Purpose

Define a human-supervised queue contract for issue intake and execution planning without autonomous mutation.

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

## Issue-To-Queue Mapping

- Missing `aresforge-ready` or explicit blocked markers route to `queue-blocked`.
- Ready but attention-needed items route to planning-level follow-up.
- Fully ready items route to implementation planning.

## Lifecycle And Readiness

- Ready: safe to include in the active branch sequence with human review.
- Attention-needed: requires explicit pre-work clarification/evidence/docs before implementation.
- Blocked: must not advance until blockers are resolved.

## Planning Inputs And Outputs

Inputs:

- issue identity/title/labels
- protected issue exclusion policy
- queue/readiness classification rules

Outputs:

- queue item list
- readiness classification
- recommended execution order
- suggested batch groups

## Orchestration Boundaries

- Read-only planning only.
- No autonomous issue, PR, label, merge, or closeout mutation.
- No background scheduler/poller.
- Human review gates are mandatory before implementation/validation/closeout transitions.

## Human Review Gates

- Scope confirmation before work starts.
- Validation evidence confirmation before closeout readiness.
- Documentation reconciliation before final closeout.

## Protected Historical Issue

Issue #39 is always excluded from queue execution and mutation.
