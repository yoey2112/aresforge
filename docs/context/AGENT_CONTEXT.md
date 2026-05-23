# AresForge Agent Context

## Purpose

Provide minimum operating context for safe M22 evidence bundle automation execution with read-only-first generation, deterministic child sequencing, targeted mutation boundaries, and parent closeout readiness gating.

## Current Operating Model

- Active milestone context: parent `#362` OPEN; children `#363-#370` CLOSED/accounted; final reconciliation child `#371` OPEN and processed last.
- M22 simulation command provides end-to-end dry-run evidence bundle generation rehearsal without mutation.
- Child execution remains one-branch, one-PR, one-evidence-comment, one-targeted-closeout.
- Parent closeout remains blocked until all children are closed/accounted and readiness checks explicitly pass.
- GitHub issue truth remains authoritative; local run/handoff artifacts are advisory support only.

## Canonical Documents

- `docs/context/BUILD_STATE.md`
- `docs/context/AGENT_CONTEXT.md`
- `docs/roadmap/ROADMAP.md`
- `docs/operator/LOCAL_OPERATOR_USAGE.md`
- `docs/architecture/EVIDENCE_BUNDLE_AUTOMATION_CONTRACT.md`
- `docs/architecture/RUNNABLE_SKELETON.md`

## Current M22 Commands

- `python -m aresforge inspect-evidence-bundle-automation-contract`
- `python -m aresforge generate-child-closeout-evidence-bundle --parent-issue <parent> --child-issue <child>`
- `python -m aresforge generate-parent-closeout-evidence-bundle --parent-issue <parent>`
- `python -m aresforge generate-pr-evidence-bundle --issue <issue> --pr <pr>`
- `python -m aresforge simulate-evidence-bundle-generation --parent-issue <parent>`

## M22 PR Mapping

- `#372` -> child `#363`
- `#373` -> child `#364`
- `#374` -> child `#365`
- `#375` -> child `#366`
- `#376` -> child `#367`
- `#377` -> child `#368`
- `#378` -> child `#369`
- `#379` -> child `#370`

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
- `python -m aresforge inspect-milestone-dashboard --parent-issue 362`
- `python -m aresforge inspect-milestone-state --parent-issue 362`
- `python -m aresforge check-milestone-evidence-readiness --parent-issue 362`
- `python -m aresforge inspect-parent-closeout-readiness --parent-issue 362`
- `python -m aresforge generate-parent-closeout-evidence-bundle --parent-issue 362`

## Known Limitations

- Parent closeout remains intentionally manual and readiness-gated.
- Non-blocking governance milestone naming warning remains present.
- Milestone assignment warnings remain present for parent/child issues in current repo state.
