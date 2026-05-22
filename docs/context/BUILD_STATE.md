# AresForge Build State

## Current Phase

M13 - Closeout Evidence Recognition

## Current Goal

Improve batch closeout readiness classification by recognizing human-gated closeout evidence in issue comments while preserving read-only and human-gated safety boundaries.

## Current Repository State

- Current branch target: `m13/closeout-evidence-recognition`
- Parent issue: #233
- M13 child scope: #234, #235, #236, #241, #237, #238, #239, #240

## Current Source Of Truth

- `docs/context/BUILD_STATE.md`
- `docs/context/AGENT_CONTEXT.md`
- `docs/roadmap/ROADMAP.md`

## Current Implemented Operator Additions

- `python -m aresforge generate-sprint-issue-script --definition <file> [--write-planning-state]`
- `python -m aresforge plan-batch-closeout --parent-issue <number> [--write-planning-snapshot]`
- `python -m aresforge inspect-planning-state`
- `python -m aresforge compare-planning-state`
- `python -m aresforge inspect-closeout-planning-drift --parent-issue <number>`
- `python -m aresforge plan-sprint-issues --definition <path>`
- closeout child-link discovery from parent body/comments and child parent-reference evidence
- read-only planning-state vs live closeout child discovery drift grouping
- closeout evidence summary drift blocking signals including `planning_state_missing`
- deterministic sprint issue planning output with human-gated PowerShell issue creation and verification guidance

## M13 Canonical Additions

- Architecture contract: `docs/architecture/CLOSEOUT_EVIDENCE_RECOGNITION_CONTRACT.md`
- Planner updates: `src/aresforge/operator/batch_closeout_planner.py`
- Regression coverage: `tests/test_batch_closeout_planner.py`
- Deterministic fixture: `tests/fixtures/m12-manual-closeout-comments.json`

## Validation Baseline

- `python -m pytest`
- `python -m aresforge inspect-repo-governance`
- `python -m aresforge plan-batch-closeout --parent-issue 222`

## Boundaries

Allowed:

- human-triggered local commands
- explicit local-only planning-state writes
- read-only planning inspection/comparison
- output-only generated sprint issue scripts requiring human execution
- read-only sprint issue planning output with human-gated mutation script generation

Not authorized:

- autonomous GitHub mutation (create/close/comment/label/milestone/merge/release/tag)
- autonomous setup/mutation behavior
- autonomous issue creation from planner output
- automatic issue closeout
- automatic PR merge

## Remaining Closeout Expectation

- After M13 implementation merges, run closeout planning for parent #222 and verify manual closeout evidence remains recognized.
