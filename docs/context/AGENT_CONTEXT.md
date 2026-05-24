# AresForge Agent Context

## Purpose

Provide minimum operating context for safe M25 automatic canonical marker emission workflow execution with read-only-first behavior, deterministic child sequencing, targeted mutation boundaries, and parent closeout readiness gating.

## Current Operating Model

- Active milestone context: parent `#421` OPEN; children `#422-#429` CLOSED/accounted; final reconciliation child `#430` OPEN and processed last.
- M25 automatic canonical marker emission now spans child/PR/parent/closeout-comment evidence domains.
- M25 readiness-by-construction validation remains read-only and surfaces actionable blockers.
- Child execution remains one-branch, one-PR, one-evidence-comment, one-targeted-closeout.
- Parent closeout remains blocked until all children are closed/accounted and readiness checks explicitly pass.
- GitHub issue truth remains authoritative; local run/handoff artifacts are advisory support only.
- Offline state-file parent closeout readiness workflow is implemented and pushed through `40de9fe`; use it as the preferred path during GitHub GraphQL/API rate-limit windows.
- With `--state-file <path>`, supported readiness/evidence commands execute local-only without `gh` or GitHub API calls.

## Canonical Documents

- `docs/context/BUILD_STATE.md`
- `docs/context/AGENT_CONTEXT.md`
- `docs/roadmap/ROADMAP.md`
- `docs/operator/LOCAL_OPERATOR_USAGE.md`
- `docs/architecture/AUTOMATIC_CANONICAL_EVIDENCE_EMISSION_CONTRACT.md`
- `docs/architecture/MILESTONE_CLOSEOUT_PREFLIGHT_CONTRACT.md`
- `docs/architecture/RUNNABLE_SKELETON.md`

## Current M25 Commands

- `python -m aresforge inspect-automatic-canonical-evidence-emission-contract`
- `python -m aresforge generate-child-closeout-evidence-bundle --parent-issue <parent> --child-issue <child>`
- `python -m aresforge generate-pr-evidence-bundle --issue <child> --pr <pr>`
- `python -m aresforge generate-parent-closeout-evidence-bundle --parent-issue <parent>`
- `python -m aresforge generate-evidence-comment-template --issue <issue>`
- `python -m aresforge check-closeout-readiness-by-construction --parent-issue <parent>`

## Offline State-File Commands

- `python -m aresforge inspect-milestone-state --parent-issue <n> --state-file <path>`
- `python -m aresforge check-milestone-evidence-readiness --parent-issue <n> --state-file <path>`
- `python -m aresforge inspect-parent-closeout-readiness --parent-issue <n> --state-file <path>`
- `python -m aresforge generate-parent-closeout-evidence-bundle --parent-issue <n> --state-file <path>`
- `python -m aresforge check-closeout-readiness-by-construction --parent-issue <n> --state-file <path>`
- Example fixture: `tests/fixtures/offline_state/parent_closeout_ready.json`.
- Validation checkpoint: `python -m pytest` passed with `502` tests.

## M25 Child/PR Mapping

- `#431` -> child `#422`
- `#432` -> child `#423`
- `#433` -> child `#424`
- `#434` -> child `#425`
- `#435` -> child `#426`
- `#436` -> child `#427`
- `#437` -> child `#428`
- `#438` -> child `#429`
- `pending` -> child `#430` (this reconciliation PR)

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
- `python -m aresforge inspect-milestone-state --parent-issue 421`
- `python -m aresforge check-milestone-evidence-readiness --parent-issue 421`
- `python -m aresforge inspect-parent-closeout-readiness --parent-issue 421`
- `python -m aresforge inspect-milestone-closeout-preflight --parent-issue 421`
- `python -m aresforge inspect-automatic-canonical-evidence-emission-contract`
- `python -m aresforge check-closeout-readiness-by-construction --parent-issue 421`

## Known Limitations

- Parent closeout remains intentionally manual and readiness-gated.
- Non-blocking governance milestone naming warning remains present.
- Milestone assignment warnings remain present for parent/child issues in current repo state.
- Final parent closeout for `#421` remains pending until child `#430` is closed and readiness passes.
