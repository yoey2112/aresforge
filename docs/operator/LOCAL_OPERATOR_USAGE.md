# Local Operator Usage

## Core Validation Bundle

- `python -m pytest`
- `python -m aresforge inspect-repo-governance`
- `python -m aresforge plan-agent-queue --help`
- `python -m aresforge report-batch-readiness --help`
- `python -m aresforge plan-batch-closeout --help`
- `git diff --check`

## M7 Governance-Aware Queue Planning

Read-only intake/planning:

- `python -m aresforge plan-agent-queue`
- `python -m aresforge plan-agent-queue --issue-number 173 --issue-number 174`
- `python -m aresforge plan-agent-queue --issues-file <path-to-json>`

Outputs include normalized issue metadata, safe reference classification, readiness grouping, and persisted planning-state design metadata.

## M7 Batch Closeout Planning

Read-only parent/child closeout planning:

- `python -m aresforge plan-batch-closeout --parent-issue 172`

Outputs include completed child issues, open/blocked children, protected exclusions, merge-evidence signals, and human-gated closeout guidance.

## M8 Structured Sprint Issue Script Generation

Read-only script generation from structured local definition:

- `python -m aresforge generate-sprint-issue-script --definition <definition.json>`
- `python -m aresforge generate-sprint-issue-script --definition <definition.json> --output <script.ps1>`

Outputs include validation diagnostics and a local PowerShell script artifact.
The command does not call `gh issue create` and does not mutate GitHub.

## M7 Batch Readiness Reporting

Read-only multi-issue readiness summary:

- `python -m aresforge report-batch-readiness --issue-number 173 --issue-number 174`
- `python -m aresforge report-batch-readiness --pr-number 200 --validation "python -m pytest"`

## Boundaries

- Commands remain human-triggered.
- Intake, queue planning, and closeout planning remain read-only.
- No autonomous merge/closeout/setup/queue mutation.
- Issue #39 remains protected historical evidence only.
- Issue #179 remains complete and unchanged.
