# Evidence Bundle Automation Contract

## Purpose

Define deterministic, reusable evidence bundle generation for child closeout, parent closeout, PR body updates, validation summaries, and handoff/source-of-truth documentation support.

## Bundle Types

- child_closeout_evidence_bundle
- parent_closeout_evidence_bundle
- pr_evidence_bundle
- validation_summary_bundle
- handoff_summary_bundle
- documentation_reconciliation_bundle

## Contract Requirements

- Evidence bundle generation is read-only by default.
- Generation logic and mutation execution are separated.
- Mutation paths require explicit operator approval and targeted issue or PR scope.
- Output must be deterministic and fixture-testable.
- Output must include explicit safety notes and warnings where applicable.

## Command Surfaces

- `python -m aresforge inspect-evidence-bundle-automation-contract`
- `python -m aresforge generate-child-closeout-evidence-bundle --parent-issue <parent> --child-issue <child>`
- `python -m aresforge generate-parent-closeout-evidence-bundle --parent-issue <parent>`
- `python -m aresforge generate-pr-evidence-bundle --issue <issue> --pr <pr>`
- `python -m aresforge simulate-evidence-bundle-generation --parent-issue <parent>`

## Validation Summary Normalization

- Validation states are normalized to one of: `pass`, `fail`, `warning`, `unknown`.
- Normalized labels currently include:
	- `git diff --check`
	- `python -m pytest`
	- `python -m aresforge inspect-repo-governance`
	- `python -m aresforge inspect-milestone-dashboard`
	- `python -m aresforge inspect-milestone-state`
	- `python -m aresforge check-milestone-evidence-readiness`
	- `python -m aresforge inspect-parent-closeout-readiness`
- Bundle generators must consume normalized summary lines rather than command-specific freeform output.

## Simulation Coverage

- Dry-run simulation must cover multi-child sequencing and keep final reconciliation last.
- Simulation must include child evidence bundle generation coverage.
- Simulation must include parent blocked-state and ready-state fixture coverage.
- Simulation must include PR evidence body generation guidance coverage.
- Simulation must preserve no-mutation defaults.

## Mutation Boundary

- Generation commands produce text packages and guidance only unless an explicit execution mode is provided and intentionally invoked.
- Issue comments, issue closeout, and PR body updates remain operator-approved targeted mutations.
- Bulk issue closure and broad autonomous mutation are out of scope.

## PowerShell Safety

- Keep issue/comment command examples plain text and copy/paste safe.
- Avoid nested markdown fences inside PowerShell here-strings.

