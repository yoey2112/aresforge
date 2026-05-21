# Batch Ready Issue Operations

## Purpose

This guide documents the M2 batch-ready issue planning and automation readiness reporting surfaces.

These commands are local, human-triggered, deterministic helpers. They are not autonomous runners and do not replace existing QA or closeout gates.

## Commands

Run read-only batch planning for all currently ready issues:

```powershell
python -m aresforge run-ready-issue-batch --plan-only
```

Optionally generate local-only implementation handoff artifacts for Copilot or Codex selected issues:

```powershell
python -m aresforge run-ready-issue-batch --plan-only --write-selected-handoffs
```

Run read-only automation readiness dashboard summary:

```powershell
python -m aresforge automation-readiness-report
```

## Batch Artifact Output

`run-ready-issue-batch --plan-only` writes deterministic local artifacts under:

- `artifacts/ready_issue_batches/generated/<timestamp>-ready-issue-batch.json`
- `artifacts/ready_issue_batches/generated/<timestamp>-ready-issue-batch.md`

When needed for deterministic testing, timestamp may be overridden with:

```powershell
python -m aresforge run-ready-issue-batch --plan-only --timestamp-override 20260520T200000Z
```

## Batch Summary Fields

Per ready issue, batch planning records:

- issue number
- issue title
- ready status
- blocked status
- blocked reasons
- selected primary agent
- selected QA agent
- selected documentation agent
- model tier
- routing reason
- confidence
- required labels
- closeout automation eligibility
- recommended next command

## Safety And Governance

Batch planning and readiness reporting must:

- always exclude protected the protected historical reference
- never mutate GitHub issue or PR state
- never run background jobs, polling loops, or schedulers
- never call paid/API remote LLM providers as default behavior
- keep closeout mutation gated through existing `qa-closeout-pr --execute` behavior only

## Recommended Human Workflow

1. Run `list-ready-issues` and inspect individual candidates.
2. Run `run-ready-issue-batch --plan-only` for deterministic multi-issue planning.
3. For selected issues, run per-issue `run-ready-issue-pipeline --plan-only` and then `--review-pr`.
4. Use `qa-closeout-pr --dry-run` first for closeout candidates.
5. Use `qa-closeout-pr --execute` only after all QA and required-label gates pass.

