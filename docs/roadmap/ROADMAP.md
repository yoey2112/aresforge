# AresForge Roadmap

## Current Milestones

### M0-M20

Status: Completed.

### M21 - Self-Managed Milestone Execution Loop

Status: Completed.

Parent issue:

- `#345` M21 self-managed milestone execution loop (OPEN)

Child issues:

- `#346` CLOSED via PR `#354`
- `#347` CLOSED via PR `#355`
- `#348` CLOSED via PR `#356`
- `#349` CLOSED via PR `#357`
- `#350` CLOSED via PR `#358`
- `#351` CLOSED via PR `#359`
- `#352` CLOSED via PR `#360`
- `#353` OPEN (final source-of-truth reconciliation; must be processed last)

Delivered M21 outcomes:

- `inspect-self-managed-milestone-execution-contract`
- `run-sequential-child-closeout-flow`
- `generate-sequential-closeout-execution-package`
- `generate-self-managed-milestone-handoff`
- `simulate-self-managed-milestone-execution`
- M21 operator workflow and architecture documentation updates

M21 safety posture:

- no autonomous broad mutation
- no bulk closure
- no parent closeout before all children are closed/accounted for
- mutation execution defaults to dry-run/planning unless explicitly approved
- every child is executed with dedicated branch, PR, validation, evidence comment, and targeted closeout
- final reconciliation kept last and docs-focused
- prior milestones are not mutated

M21 standard validation bundle:

- `git diff --check`
- `python -m pytest`
- `python -m aresforge inspect-repo-governance`
- `python -m aresforge inspect-milestone-dashboard --parent-issue 345`
- `python -m aresforge inspect-milestone-state --parent-issue 345`
- `python -m aresforge inspect-self-managed-milestone-execution-contract`
- `python -m aresforge simulate-self-managed-milestone-execution --parent-issue 345`

### M22 - Evidence Bundle And Documentation Automation

Status: Completed.

Parent issue:

- `#362` CLOSED

Child issues:

- `#363` CLOSED via PR `#372`
- `#364` CLOSED via PR `#373`
- `#365` CLOSED via PR `#374`
- `#366` CLOSED via PR `#375`
- `#367` CLOSED via PR `#376`
- `#368` CLOSED via PR `#377`
- `#369` CLOSED via PR `#378`
- `#370` CLOSED via PR `#379`
- `#371` CLOSED via PR `#380`

Delivered M22 outcomes:

- `inspect-evidence-bundle-automation-contract`
- `generate-child-closeout-evidence-bundle`
- `generate-parent-closeout-evidence-bundle`
- `generate-pr-evidence-bundle`
- validation summary normalization (`pass`/`fail`/`warning`/`unknown`)
- `simulate-evidence-bundle-generation`
- operator and architecture documentation updates for evidence bundle workflows

M22 safety posture:

- no autonomous broad mutation
- no bulk closure
- no parent closeout before all children are closed/accounted for
- mutation execution defaults to dry-run/planning unless explicitly approved
- every child is executed with dedicated branch, PR, validation, evidence comment, and targeted closeout
- final reconciliation kept last and docs-focused
- prior milestones are not mutated

M22 standard validation bundle:

- `git diff --check`
- `python -m pytest`
- `python -m aresforge inspect-repo-governance`
- `python -m aresforge inspect-milestone-dashboard --parent-issue 362`
- `python -m aresforge inspect-milestone-state --parent-issue 362`
- `python -m aresforge check-milestone-evidence-readiness --parent-issue 362`
- `python -m aresforge inspect-parent-closeout-readiness --parent-issue 362`
- `python -m aresforge generate-parent-closeout-evidence-bundle --parent-issue 362`

### M23 - Milestone Lineage And Evidence Mapping Preflight

Status: Completed.

Parent issue:

- `#381` CLOSED

Child issues:

- `#382` CLOSED via PR `#391`
- `#383` CLOSED via PR `#392`
- `#384` CLOSED via PR `#393`
- `#385` CLOSED via PR `#394`
- `#386` CLOSED via PR `#395`
- `#387` CLOSED via PR `#396`
- `#388` CLOSED via PR `#397`
- `#389` CLOSED via PR `#398`
- `#390` CLOSED (final source-of-truth reconciliation child)

Delivered M23 outcomes:

- `inspect-milestone-closeout-preflight-contract`
- `inspect-parent-child-linkage-preflight`
- `inspect-child-evidence-marker-preflight`
- `inspect-pr-mapping-preflight`
- `generate-closeout-preflight-repair-guidance`
- `inspect-milestone-closeout-preflight`
- operator documentation updates for preflight sequencing and state interpretation

M23 safety posture:

- no autonomous broad mutation
- no bulk closure
- no parent closeout before all children are closed/accounted for
- mutation execution defaults to dry-run/planning unless explicitly approved
- repair guidance remains copy/paste text only and does not execute mutation
- final reconciliation kept last and docs-focused
- prior milestones are not mutated

M23 standard validation bundle:

- `git diff --check`
- `python -m pytest`
- `python -m aresforge inspect-repo-governance`
- `python -m aresforge inspect-milestone-dashboard --parent-issue 381`
- `python -m aresforge inspect-milestone-state --parent-issue 381`
- `python -m aresforge check-milestone-evidence-readiness --parent-issue 381`
- `python -m aresforge inspect-parent-closeout-readiness --parent-issue 381`
- `python -m aresforge inspect-milestone-closeout-preflight --parent-issue 381`

### M24 - Canonical Evidence Marker Workflow

Status: Completed.

Parent issue:

- `#400` M24 canonical evidence marker workflow (OPEN)

Child issues:

- `#401` CLOSED via PR `#411`
- `#402` CLOSED via PR `#412`
- `#403` CLOSED via PR `#413`
- `#404` CLOSED via PR `#414`
- `#405` CLOSED via PR `#415`
- `#406` CLOSED via PR `#416`
- `#407` CLOSED via PR `#417`
- `#408` CLOSED via PR `#418`
- `#409` CLOSED via PR `#419`
- `#410` CLOSED

Delivered M24 outcomes:

- `inspect-canonical-evidence-marker-contract`
- `generate-child-evidence-marker-template`
- `generate-pr-evidence-marker-template`
- `generate-parent-closeout-marker-template`
- `generate-preflight-baseline-snapshot`
- `diff-preflight-snapshots`
- canonical-marker integration in evidence bundles and preflight guidance
- canonical-first preflight parsing with backward-compatible fallback
- operator and architecture documentation updates for canonical marker workflow

M24 safety posture:

- no autonomous broad mutation
- no bulk closure
- no parent closeout before all children are closed/accounted for
- mutation execution defaults to dry-run/planning unless explicitly approved
- canonical marker and snapshot/diff commands are read-only by default
- final reconciliation kept last and docs-focused
- prior milestones are not mutated

M24 standard validation bundle:

- `git diff --check`
- `python -m pytest`
- `python -m aresforge inspect-repo-governance`
- `python -m aresforge inspect-milestone-dashboard --parent-issue 400`
- `python -m aresforge inspect-milestone-state --parent-issue 400`
- `python -m aresforge check-milestone-evidence-readiness --parent-issue 400`
- `python -m aresforge inspect-parent-closeout-readiness --parent-issue 400`
- `python -m aresforge inspect-milestone-closeout-preflight --parent-issue 400`
- `python -m aresforge inspect-canonical-evidence-marker-contract`

### M25 - Automatic Canonical Marker Emission Workflow

Status: Final reconciliation in progress (`#430` only).

Parent issue:

- `#421` M25 automatic canonical marker emission workflow (OPEN; pending final closeout)

Child issues:

- `#422` CLOSED via PR `#431`
- `#423` CLOSED via PR `#432`
- `#424` CLOSED via PR `#433`
- `#425` CLOSED via PR `#434`
- `#426` CLOSED via PR `#435`
- `#427` CLOSED via PR `#436`
- `#428` CLOSED via PR `#437`
- `#429` CLOSED via PR `#438`
- `#430` OPEN (final source-of-truth reconciliation; must be processed last)

Delivered M25 outcomes:

- `inspect-automatic-canonical-evidence-emission-contract`
- canonical marker completeness emitted by child closeout evidence bundles
- canonical marker completeness emitted by PR evidence bundles
- canonical marker completeness emitted by parent closeout evidence bundles
- canonical marker completeness emitted by generated closeout comment templates
- `check-closeout-readiness-by-construction` read-only readiness gate
- regression fixtures proving complete generated marker paths do not require post-hoc marker repair
- operator documentation updates for automatic marker workflow
- local/offline state-file parent closeout readiness workflow implemented and pushed through `40de9fe`
- local-only `--state-file` command path for rate-limit-window execution without `gh`/GitHub API calls
- sample offline-ready fixture at `tests/fixtures/offline_state/parent_closeout_ready.json`

M25 safety posture:

- no autonomous broad mutation
- no bulk closure
- no parent closeout before all children are closed/accounted for
- mutation execution defaults to dry-run/planning unless explicitly approved
- marker generation/checking and readiness-by-construction remain read-only by default
- final reconciliation kept last and docs-focused
- prior milestones are not mutated

M25 standard validation bundle:

- `git diff --check`
- `python -m pytest`
- `python -m aresforge inspect-repo-governance`
- `python -m aresforge check-closeout-readiness-by-construction --parent-issue 421`
- `python -m aresforge inspect-milestone-state --parent-issue 421`
- `python -m aresforge check-milestone-evidence-readiness --parent-issue 421`
- `python -m aresforge inspect-parent-closeout-readiness --parent-issue 421`
- `python -m aresforge generate-parent-closeout-evidence-bundle --parent-issue 421`

M25 offline state-file readiness path:

- Preferred during GitHub GraphQL/API rate-limit windows.
- `python -m aresforge inspect-milestone-state --parent-issue <n> --state-file <path>`
- `python -m aresforge check-milestone-evidence-readiness --parent-issue <n> --state-file <path>`
- `python -m aresforge inspect-parent-closeout-readiness --parent-issue <n> --state-file <path>`
- `python -m aresforge generate-parent-closeout-evidence-bundle --parent-issue <n> --state-file <path>`
- `python -m aresforge check-closeout-readiness-by-construction --parent-issue <n> --state-file <path>`
- Docs/sample checkpoint validation: `python -m pytest` passed (`502` tests).

M25 head tracking:

- main before remaining sequence (#428/#429/#430): `dd856632e2f1831b20b73613f29e9e953771180f`
- main after #428 and #429 merges: `cafda2ceda0a329de7d06a42c0edc6725ece3b10`
- final main after #430 merge: pending

### M26 - Local Handoff Package Generator

Status: Implemented.

Delivered M26 outcomes:

- `generate-handoff-package` local-only command added.
- Markdown and JSON handoff rendering from local repo/doc state.
- Safe local git-state capture limited to approved command set.
- Output write safety with directory creation, overwrite refusal, and `--force`.
- Source-of-truth doc ingestion with graceful missing-doc warnings.
- Continuity sections for human, Codex, and local LLM session handoff.
- Unit and CLI coverage for markdown/json output, stdout behavior, and overwrite protection.

M26 milestone value:

- Reduces manual handoff authoring and improves continuity across sessions/chats.
- Provides a prerequisite local continuity baseline before multi-project queue/orchestration/dashboard/cloud escalation milestones.

## Standing Boundaries

- No autonomous mutation without explicit mode selection.
- No autonomous queue workers.
- No automatic PR merge.
- No unattended background execution.

### M27 - Local Project State Ledger

Status: Implemented.

Delivered M27 outcomes:

- Persistent local project-state ledger under `.aresforge/state/project_state.json`.
- Append-only local operation log under `.aresforge/state/operation_log.jsonl`.
- Local-only CLI commands for ledger init/inspect/update and operation log append/inspect.
- M26 handoff package integration now includes local project-state summary when present.
- Handoff generation warning behavior when ledger is missing (generation still succeeds).
- Unit and CLI test coverage for ledger lifecycle and operation log behavior.

M27 milestone value:

- Establishes a broader local project state foundation beyond closeout-specific offline files.
- Removes GitHub as the only practical source for local progress/state tracking.
- Prepares future multi-project queue/orchestration/documentation/sync workflows for local-first continuity.

### M28 - Documentation Agent Foundation

Status: Implemented.

Delivered M28 outcomes:

- `plan-doc-reconciliation` local-only planning command added.
- Deterministic reconciliation output in markdown or stable JSON.
- Source-of-truth documentation inspection plus local project-state alignment checks.
- Optional local git-state inspection via approved command subset only.
- Overwrite-safe output writing with directory creation and explicit `--force`.
- M26 handoff package now references latest local doc reconciliation plan when available.
- Test coverage for missing docs detection, recommendation generation, CLI output modes, and overwrite protection.

M28 safety posture:

- plan-only output; no automatic documentation edits
- local-only; no `gh` and no GitHub APIs
- no LLM calls
- no network dependency
