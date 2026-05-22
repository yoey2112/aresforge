# AresForge Agent Context

## Purpose

Provide the minimum current operating context for safe post-M14 operator usage and source-of-truth reconciliation.

## Current Operating Model

- Documentation remains source of truth.
- Local planning memory is optional, explicit-write, and local-only.
- Default command behavior remains read-only/output-only.
- Human authority remains final for all GitHub mutation.
- Sprint issue creation planning is deterministic, read-only by default, and emits human-gated mutation output only.
- Implementation progress remains gated by human-run post-creation verification pass/fail output.
- Closeout planning recognizes deterministic human-gated closeout evidence in issue comments without mutation.
- Historical parent-body references are classified as historical/non-active evidence context, not active child work.
- Merged PR references used in closeout comments are classified as evidence, not active child work.

## Canonical Documents

- `docs/architecture/SPRINT_ISSUE_CREATION_PLANNING_CONTRACT.md`
- `docs/architecture/CLOSEOUT_EVIDENCE_RECOGNITION_CONTRACT.md`
- `docs/architecture/RUNNABLE_SKELETON.md`
- `docs/operator/LOCAL_OPERATOR_USAGE.md`
- `docs/context/BUILD_STATE.md`
- `docs/roadmap/ROADMAP.md`

## Current Commands

- `python -m aresforge generate-sprint-issue-script --definition <file> [--write-planning-state]`
- `python -m aresforge plan-batch-closeout --parent-issue <number> [--write-planning-snapshot]`
- `python -m aresforge inspect-planning-state`
- `python -m aresforge compare-planning-state`
- `python -m aresforge inspect-closeout-planning-drift --parent-issue <number>`
- `python -m aresforge plan-sprint-issues --definition <path>`

## Delivery Status

- M13 complete; closeout evidence recognition contract and parser coverage delivered via merged PR #242.
- M14 cleanup complete via merged PR #244 (issue #243) and PR #246 (issue #245).
- Baseline state: `main` at `dde2683`, no open issues, no open PRs, governance inspection `ok true`.

## Prohibited Behaviors

- autonomous queue transitions
- autonomous setup/mutation behavior
- autonomous issue creation from planner output
- autonomous merge/closeout/labeling/milestone assignment
- autonomous comments/releases/tags
- automatic issue closeout
- automatic PR merge

## Validation Snapshot

- `python -m pytest` -> `258 passed`
- `python -m aresforge inspect-repo-governance` -> `ok true`
- `python -m aresforge plan-batch-closeout --parent-issue 222` -> `ready`
- `python -m aresforge plan-batch-closeout --parent-issue 233` -> discovered/requested children `#234` through `#241` only; historical references remain historical; PR references are evidence

## Historical Closeout Note

- Parent #233 may remain incomplete for some older M13 closeout comments missing documentation reconciliation evidence.
- This reflects historical closeout-comment quality evidence, not a current child discovery blocker.
