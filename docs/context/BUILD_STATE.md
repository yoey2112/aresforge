# AresForge Build State

## Current Phase

M25 automatic canonical marker emission workflow final reconciliation.

## Current Goal

Complete M25 source-of-truth reconciliation child issue `#430` (last child), then run parent closeout readiness checks for parent `#421`.

## Current Repository State

- M25 parent issue: `#421` (OPEN; pending final closeout).
- M25 child issue status:
  - `#422` CLOSED via PR `#431`
  - `#423` CLOSED via PR `#432`
  - `#424` CLOSED via PR `#433`
  - `#425` CLOSED via PR `#434`
  - `#426` CLOSED via PR `#435`
  - `#427` CLOSED via PR `#436`
  - `#428` CLOSED via PR `#437`
  - `#429` CLOSED via PR `#438`
  - `#430` OPEN (final source-of-truth reconciliation; sequenced last)
- Offline state-file parent closeout readiness workflow is implemented and pushed on `main` through commit `40de9fe`.

## Offline State-File Closeout Readiness (Local-Only)

- Preferred path during GitHub GraphQL/API rate-limit windows.
- When `--state-file <path>` is provided, these commands run local/offline and avoid `gh` and GitHub API calls.
- Supported commands:
  - `python -m aresforge inspect-milestone-state --parent-issue <n> --state-file <path>`
  - `python -m aresforge check-milestone-evidence-readiness --parent-issue <n> --state-file <path>`
  - `python -m aresforge inspect-parent-closeout-readiness --parent-issue <n> --state-file <path>`
  - `python -m aresforge generate-parent-closeout-evidence-bundle --parent-issue <n> --state-file <path>`
  - `python -m aresforge check-closeout-readiness-by-construction --parent-issue <n> --state-file <path>`
- Example fixture: `tests/fixtures/offline_state/parent_closeout_ready.json`.
- Validation checkpoint for docs/sample addition passed: `python -m pytest` (`502` tests).

## M25 Command Surface

- `python -m aresforge inspect-automatic-canonical-evidence-emission-contract`
- `python -m aresforge inspect-child-evidence-marker-preflight --parent-issue <parent>`
- `python -m aresforge inspect-pr-mapping-preflight --parent-issue <parent>`
- `python -m aresforge generate-closeout-preflight-repair-guidance --parent-issue <parent>`
- `python -m aresforge generate-child-closeout-evidence-bundle --parent-issue <parent> --child-issue <child>`
- `python -m aresforge generate-pr-evidence-bundle --issue <child> --pr <pr>`
- `python -m aresforge generate-parent-closeout-evidence-bundle --parent-issue <parent>`
- `python -m aresforge generate-evidence-comment-template --issue <issue>`
- `python -m aresforge check-closeout-readiness-by-construction --parent-issue <parent>`

## M25 Safety Posture

- no autonomous broad mutation
- no bulk closeout
- no parent closeout before children are closed/accounted for and readiness passes
- dry-run/read-only defaults preserved
- execute-mode mutation requires explicit operator approval markers
- mutation scope remains single-target and auditable
- canonical marker generation and snapshot/diff inspection remain read-only by default
- final reconciliation issue remains sequenced last (`#430`)
- no post-hoc marker repair should be needed when generated evidence artifacts are complete

## Known Limitations

- Project-specific milestone naming mapping warning remains non-blocking (`milestone_naming_status.naming_ok: false`).
- Parent and some child issues currently have no GitHub milestone assignment (warning only, non-blocking for M25 closeout).

## Validation Baseline For M25

- `git diff --check`
- `python -m pytest`
- `python -m aresforge inspect-repo-governance`
- `python -m aresforge inspect-milestone-state --parent-issue 421`
- `python -m aresforge check-milestone-evidence-readiness --parent-issue 421`
- `python -m aresforge inspect-parent-closeout-readiness --parent-issue 421`
- `python -m aresforge inspect-milestone-closeout-preflight --parent-issue 421`
- `python -m aresforge inspect-automatic-canonical-evidence-emission-contract`
- `python -m aresforge check-closeout-readiness-by-construction --parent-issue 421`
- `python -m aresforge generate-parent-closeout-evidence-bundle --parent-issue 421`

## M25 Child/PR Mapping

- `#422` -> `#431`
- `#423` -> `#432`
- `#424` -> `#433`
- `#425` -> `#434`
- `#426` -> `#435`
- `#427` -> `#436`
- `#428` -> `#437`
- `#429` -> `#438`
- `#430` -> pending (this reconciliation PR)

## Main HEAD Tracking (M25 Remaining Sequence)

- Before #428/#429/#430 sequence: `dd856632e2f1831b20b73613f29e9e953771180f`
- After #428 and #429 merges: `cafda2ceda0a329de7d06a42c0edc6725ece3b10`
- Final main HEAD after #430 merge: pending (set after merge)
