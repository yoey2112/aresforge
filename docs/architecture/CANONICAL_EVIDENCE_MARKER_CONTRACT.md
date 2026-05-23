# Canonical Evidence Marker Contract

## Purpose

Define canonical marker blocks used across child issue evidence, PR evidence, parent closeout evidence, and reconciliation/audit evidence so extraction and preflight checks remain deterministic and auditable.

## Canonical Marker Types

- child evidence marker
- pr evidence marker
- parent closeout evidence marker
- reconciliation/audit marker

## Child Evidence Marker Required Fields

- parent issue
- child issue
- branch
- commit
- pr
- validation summary
- safety notes
- closeout status
- evidence comment status

## PR Evidence Marker Required Fields

- issue
- pr
- branch
- commit
- changed files
- validation summary
- merge status
- safety posture
- evidence status
- notes/warnings

## Parent Closeout Evidence Marker Required Fields

- parent issue
- child issue list
- child-to-pr mapping
- final main head
- final validation results
- readiness gate summary
- safety confirmations
- warnings/deviations
- closeout readiness state

## Reconciliation/Audit Marker Required Fields

- baseline snapshot
- post-reconciliation snapshot
- snapshot diff
- audit classification
- warnings/deviations

## Marker Safety and Formatting Requirements

- Marker generation and inspection are read-only by default.
- Marker generation must not execute issue/PR/comment/closeout mutation.
- Marker blocks must stay parse-friendly with stable section labels.
- Marker output must be copy/paste-safe.
- Avoid nested markdown fences inside PowerShell here-strings.
- Keep issue/comment command examples plain text and copy/paste-safe.

## Relationship to M22 Evidence Bundles

- Canonical markers align with the Evidence Bundle Automation Contract and M22 bundle workflows.
- Marker blocks are designed to be consumed by child/PR/parent evidence bundle generation paths.
- Marker adoption must not remove prior evidence bundle compatibility.

## Relationship to M23 Preflight Checks

- Canonical markers align with the Milestone Closeout Preflight Contract and M23 preflight inspectors.
- Parent-child linkage, child evidence marker checks, and child-to-pr mapping remain read-only checks.
- Canonical marker parsing is preferred when available while preserving backward-compatible fallback parsing.

## Snapshot and Diff Audit Expectations

- Reconciliation audits capture a baseline snapshot and a post-reconciliation snapshot.
- Snapshot diff results classify outcomes as no-change, improved, regressed, or mixed.
- Snapshot/diff output must be deterministic and fixture-testable.

## Operator Boundary

- Marker generation and inspection commands are documentation and planning aids only.
- Any mutation action requires explicit operator approval and targeted scope.
- Broad autonomous mutation and bulk closeout remain out of scope.