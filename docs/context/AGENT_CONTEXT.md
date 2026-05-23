# AresForge Agent Context

## Purpose

Provide minimum operating context for safe M23 milestone lineage/evidence/PR mapping preflight execution with read-only-first behavior, deterministic child sequencing, targeted mutation boundaries, and parent closeout readiness gating.

## Current Operating Model

- Active milestone context: parent `#381` OPEN; children `#382-#389` CLOSED/accounted; final reconciliation child `#390` OPEN and processed last.
- M23 preflight commands provide read-only lineage/evidence/PR mapping detectability checks before parent closeout.
- Child execution remains one-branch, one-PR, one-evidence-comment, one-targeted-closeout.
- Parent closeout remains blocked until all children are closed/accounted and readiness checks explicitly pass.
- GitHub issue truth remains authoritative; local run/handoff artifacts are advisory support only.

## Canonical Documents

- `docs/context/BUILD_STATE.md`
- `docs/context/AGENT_CONTEXT.md`
- `docs/roadmap/ROADMAP.md`
- `docs/operator/LOCAL_OPERATOR_USAGE.md`
- `docs/architecture/MILESTONE_CLOSEOUT_PREFLIGHT_CONTRACT.md`
- `docs/architecture/RUNNABLE_SKELETON.md`

## Current M23 Commands

- `python -m aresforge inspect-milestone-closeout-preflight-contract`
- `python -m aresforge inspect-parent-child-linkage-preflight --parent-issue <parent>`
- `python -m aresforge inspect-child-evidence-marker-preflight --parent-issue <parent>`
- `python -m aresforge inspect-pr-mapping-preflight --parent-issue <parent>`
- `python -m aresforge generate-closeout-preflight-repair-guidance --parent-issue <parent>`
- `python -m aresforge inspect-milestone-closeout-preflight --parent-issue <parent>`

## M23 PR Mapping

- `#391` -> child `#382`
- `#392` -> child `#383`
- `#393` -> child `#384`
- `#394` -> child `#385`
- `#395` -> child `#386`
- `#396` -> child `#387`
- `#397` -> child `#388`
- `#398` -> child `#389`

## Prohibited Behaviors

- autonomous broad mutation
- bulk issue closure
- parent closeout before all children are closed/accounted for
- prior milestone mutation unless explicitly required
- nested markdown fences inside PowerShell here-string issue/comment bodies

## Validation Snapshot

- `git diff --check`
- `python -m pytest`
- `python -m aresforge inspect-repo-governance`
- `python -m aresforge inspect-milestone-dashboard --parent-issue 381`
- `python -m aresforge inspect-milestone-state --parent-issue 381`
- `python -m aresforge check-milestone-evidence-readiness --parent-issue 381`
- `python -m aresforge inspect-parent-closeout-readiness --parent-issue 381`
- `python -m aresforge inspect-milestone-closeout-preflight --parent-issue 381`
- `python -m aresforge generate-parent-closeout-evidence-bundle --parent-issue 381`

## Known Limitations

- Parent closeout remains intentionally manual and readiness-gated.
- Non-blocking governance milestone naming warning remains present.
- Milestone assignment warnings remain present for parent/child issues in current repo state.
