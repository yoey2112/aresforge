# Local Operator Usage

## Core Validation Bundle

- `python -m pytest`
- `python -m aresforge inspect-repo-governance`
- `python -m aresforge plan-agent-queue --help`
- `python -m aresforge report-batch-readiness --help`
- `git diff --check`

## M6 Queue Planning

Read-only queue intake/planning:

- `python -m aresforge plan-agent-queue`
- `python -m aresforge plan-agent-queue --issue-number 165 --issue-number 166`
- `python -m aresforge plan-agent-queue --issues-file <path-to-json>`

Outputs include queue state classification, blocked/attention reasons, recommended order, and batch groups.

## M6 Batch Readiness Reporting

Read-only multi-issue readiness summary:

- `python -m aresforge report-batch-readiness --issue-number 165 --issue-number 166`
- `python -m aresforge report-batch-readiness --issues-file <path-to-json>`
- `python -m aresforge report-batch-readiness --pr-number 200 --validation "python -m pytest"`

Outputs include issue coverage, changed-file awareness, validation evidence summary, unresolved gates, and explicit human closeout requirements.

## Hardened Sprint Issue Creation Standard

For parent/child sprint issue creation, operators must use:

- `docs/operator/HARDENED_SPRINT_ISSUE_CREATION_TEMPLATE.md`

Required gates:

- Every declared child `BodyPath` must be written.
- All declared body files must exist and be non-empty before GitHub mutation.
- Created issue URLs must be non-blank and parse to issue numbers.
- Parent issue updates are blocked until every expected child issue number is known.
- Temporary local artifacts are retained until final verification passes.

## Closeout Reliability

- `qa-closeout-pr` remains dry-run by default.
- Execute mode remains explicit and gated.
- Close issue failures now emit improved diagnostics including post-failure issue-state recheck.

## Boundaries

- Commands remain human-triggered.
- Queue planning and readiness reporting remain read-only.
- No autonomous merge/closeout/setup/queue mutation.
- Issue #39 must remain untouched.
