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

## Command Surfaces

- python -m aresforge inspect-canonical-evidence-marker-contract
- python -m aresforge generate-child-evidence-marker-template --parent-issue <parent> --child-issue <child>
- python -m aresforge generate-pr-evidence-marker-template --issue <child> --pr <pr>
- python -m aresforge generate-parent-closeout-marker-template --parent-issue <parent>
- python -m aresforge generate-preflight-baseline-snapshot --parent-issue <parent>
- python -m aresforge diff-preflight-snapshots --before <before_snapshot.json> --after <after_snapshot.json>

## Marker-Complete Examples

Child evidence marker (ready):

[ARESFORGE_CANONICAL_EVIDENCE_MARKER]
marker_type: child_evidence
marker_state: ready
required.parent_issue: #400
required.child_issue: #409
required.branch: m24-409-canonical-marker-workflow-docs
required.commit: <commit_sha>
required.pr: #<pr>
required.validation_summary: git diff --check=pass; pytest=pass; inspect-repo-governance=pass
required.safety_notes: read-only by default; targeted mutation only
optional.closeout_status: closed
optional.evidence_comment_status: posted
optional.merge_status: merged
missing_required_fields: <none>
invalid_reasons: <none>
[/ARESFORGE_CANONICAL_EVIDENCE_MARKER]

Reconciliation audit marker (ready):

[ARESFORGE_CANONICAL_EVIDENCE_MARKER]
marker_type: reconciliation_audit
marker_state: ready
required.baseline_snapshot: artifacts/evidence/generated/m24-400-baseline-before.json
required.post_reconciliation_snapshot: artifacts/evidence/generated/m24-400-baseline-after.json
required.snapshot_diff: artifacts/evidence/generated/m24-400-diff.json
required.audit_classification: improved
required.warnings_deviations: milestone_naming_status.naming_ok=false; missing milestone assignment warnings
missing_required_fields: <none>
invalid_reasons: <none>
[/ARESFORGE_CANONICAL_EVIDENCE_MARKER]

## Operator Boundary

- Marker generation and inspection commands are documentation and planning aids only.
- Any mutation action requires explicit operator approval and targeted scope.
- Broad autonomous mutation and bulk closeout remain out of scope.