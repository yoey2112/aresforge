# Closeout Child-Link Discovery Contract

## Purpose

Define the M10 contract for discovering child issues during `plan-batch-closeout` without introducing GitHub mutation.

## Discovery Sources

- parent issue body (`parent_body`)
- parent issue comments (`parent_comments`)
- corrected/reposted child issue index comments (`corrected_child_index`)
- child issue body parent-link lines (`child_body`)

Supported child-parent body patterns:

- `Parent issue: #<number>`
- `Parent: #<number>`
- `Part of #<number>`
- `Child of #<number>`

## Classification Contract

Every discovered reference must be classified as one of:

- `active` (usable for child closeout linkage)
- `historical`
- `safety`
- `protected`
- `incidental`

the protected historical reference must remain protected historical/safety-only evidence and never become an active implementation child link.

## Corrected Index Behavior

When multiple parent comments look like child indexes:

- comments with correction hints (`corrected`, `updated`, `reposted`, `supersedes`, `latest`) are preferred
- otherwise the latest index-style comment is treated as corrected
- earlier index comments remain evidence but are not the preferred source

## Evidence Reporting Contract

`plan-batch-closeout` must expose:

- discovered child issue numbers
- per-link discovery source
- per-link classification
- ignored non-active references when useful for traceability
- conservative ambiguous readiness when no active child links are available

## Safety Contract

- read-only inspection posture remains default
- no autonomous GitHub mutation
- no automatic closeout behavior
- no autonomous comments/labels/milestones/PR merge/release/tag behavior

