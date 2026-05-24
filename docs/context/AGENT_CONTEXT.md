# AresForge Agent Context

## Purpose

Provide minimum operating context for safe M24 canonical evidence marker workflow execution with read-only-first behavior, deterministic child sequencing, targeted mutation boundaries, and parent closeout readiness gating.

## Current Operating Model

- Active milestone context: parent `#400` OPEN; children `#401-#409` CLOSED/accounted; final reconciliation child `#410` OPEN and processed last.
- M24 canonical marker commands provide deterministic marker templates and snapshot/diff audit outputs.
- M24 integration keeps preflight and evidence bundle commands canonical-first while preserving backward-compatible fallback parsing.
- Child execution remains one-branch, one-PR, one-evidence-comment, one-targeted-closeout.
- Parent closeout remains blocked until all children are closed/accounted and readiness checks explicitly pass.
- GitHub issue truth remains authoritative; local run/handoff artifacts are advisory support only.

## Canonical Documents

- `docs/context/BUILD_STATE.md`
- `docs/context/AGENT_CONTEXT.md`
- `docs/roadmap/ROADMAP.md`
- `docs/operator/LOCAL_OPERATOR_USAGE.md`
- `docs/architecture/CANONICAL_EVIDENCE_MARKER_CONTRACT.md`
- `docs/architecture/MILESTONE_CLOSEOUT_PREFLIGHT_CONTRACT.md`
- `docs/architecture/RUNNABLE_SKELETON.md`

## Current M24 Commands

- `python -m aresforge inspect-canonical-evidence-marker-contract`
- `python -m aresforge generate-child-evidence-marker-template --parent-issue <parent> --child-issue <child>`
- `python -m aresforge generate-pr-evidence-marker-template --issue <child> --pr <pr>`
- `python -m aresforge generate-parent-closeout-marker-template --parent-issue <parent>`
- `python -m aresforge generate-preflight-baseline-snapshot --parent-issue <parent> --output <path>`
- `python -m aresforge diff-preflight-snapshots --before <before_snapshot.json> --after <after_snapshot.json>`
- `python -m aresforge inspect-child-evidence-marker-preflight --parent-issue <parent>`
- `python -m aresforge inspect-pr-mapping-preflight --parent-issue <parent>`
- `python -m aresforge generate-closeout-preflight-repair-guidance --parent-issue <parent>`
- `python -m aresforge inspect-milestone-closeout-preflight --parent-issue <parent>`

## M24 Child/PR Mapping

- `#411` -> child `#401`
- `#412` -> child `#402`
- `#413` -> child `#403`
- `#414` -> child `#404`
- `#415` -> child `#405`
- `#416` -> child `#406`
- `#417` -> child `#407`
- `#418` -> child `#408`
- `#419` -> child `#409`

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
- `python -m aresforge inspect-milestone-dashboard --parent-issue 400`
- `python -m aresforge inspect-milestone-state --parent-issue 400`
- `python -m aresforge check-milestone-evidence-readiness --parent-issue 400`
- `python -m aresforge inspect-parent-closeout-readiness --parent-issue 400`
- `python -m aresforge inspect-milestone-closeout-preflight --parent-issue 400`
- `python -m aresforge inspect-canonical-evidence-marker-contract`
- `python -m aresforge generate-parent-closeout-marker-template --parent-issue 400`
- `python -m aresforge generate-preflight-baseline-snapshot --parent-issue 400 --output artifacts/evidence/generated/m24-400-baseline.json`

## Known Limitations

- Parent closeout remains intentionally manual and readiness-gated.
- Non-blocking governance milestone naming warning remains present.
- Milestone assignment warnings remain present for parent/child issues in current repo state.
