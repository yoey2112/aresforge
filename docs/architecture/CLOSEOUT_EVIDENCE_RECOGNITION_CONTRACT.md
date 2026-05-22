# Closeout Evidence Recognition Contract

## Purpose

Define deterministic, read-only recognition rules for human-gated closeout evidence used by `plan-batch-closeout`.

## Scope

This contract applies to parent/child closeout planning evidence classification only. It does not authorize GitHub mutation.

## Evidence Categories

Recognized merged PR evidence:

- issue-native merged PR references from read-only GitHub issue metadata
- closeout comment lines containing `PR #<number>` or `Pull Request #<number>`

Recognized validation evidence:

- issue body `## Validation` bullet lines
- closeout comment lines that include both a Python command and a pass signal, such as:
  - `python -m ... -> ok true`
  - `python -m ... -> ... passed`
  - `python -m ... -> success`

Recognized documentation reconciliation evidence:

- issue body `## Documentation` bullet lines
- closeout comment lines referencing documentation or source-of-truth reconciliation
- closeout comment lines referencing updated source-of-truth files, including:
  - `BUILD_STATE.md`
  - `AGENT_CONTEXT.md`
  - `ROADMAP.md`

Recognized safety posture evidence:

- closeout comment lines describing human-gated/read-only/no-autonomous-mutation posture

## Readiness Interpretation

- Closed child issues with recognized merged PR, validation, and documentation reconciliation evidence are eligible for `ready` classification when other gates pass.
- Missing evidence remains explicit when required evidence cannot be recognized.
- Parent readiness remains conservative and human-gated.

## Determinism And Boundaries

- Parsing is deterministic and local to fetched read-only issue payloads.
- No autonomous issue/PR/comment/label/milestone/merge/release/tag mutation is performed.
- Closeout execution authority remains human-gated and outside this planner command.
