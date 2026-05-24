# Automatic Canonical Evidence Emission Contract

## Purpose

Define the M25 contract for automatic canonical marker emission so milestone closeout readiness is achieved by construction across generated evidence artifacts.

## Required Artifact Types

Generated outputs that must emit canonical markers by default:

- child closeout evidence bundles
- pr evidence bundles
- parent closeout evidence bundles
- generated closeout comments

## Marker Completeness Rules

- Every required marker completeness field must be present for the artifact type.
- Completeness checks must remain machine-checkable and deterministic.
- Marker rendering must be stable and parse-friendly for repeat generation.
- Post-hoc marker repair comments should not be required for compliant generated artifacts.

## Read-Only and Mutation Safety Posture

- Marker generation and marker verification are read-only by default.
- Preflight, snapshot, and evidence bundle workflows remain dry-run/planning by default.
- Any GitHub mutation path (PR body, comment posting, issue closeout) remains operator-approved and targeted.
- No autonomous broad mutation and no bulk issue closure.

## Readiness Consumer Expectations

- Child-level checks consume emitted markers through child evidence marker preflight paths.
- PR linkage checks consume emitted markers through pr mapping preflight paths.
- Parent closure gates consume emitted markers through parent closeout readiness checks.
- Milestone-level closeout checks consume emitted markers through readiness-by-construction validation.

## Backward Compatibility

- Canonical marker parsing is preferred when emitted marker blocks are present.
- Backward-compatible fallback parsing remains supported for older marker-aware artifacts.
- Automatic emission extends existing M24 contract behavior without breaking prior read paths.

## Command Surfaces

- python -m aresforge inspect-automatic-canonical-evidence-emission-contract
- python -m aresforge inspect-canonical-evidence-marker-contract
- python -m aresforge generate-child-closeout-evidence-bundle --parent-issue <parent> --child-issue <child>
- python -m aresforge generate-pr-evidence-bundle --issue <child> --pr <pr>
- python -m aresforge generate-parent-closeout-evidence-bundle --parent-issue <parent>

## Operator Boundary

- This contract and its inspection command are documentation and planning aids.
- Parent closeout remains blocked until children are closed/accounted for and readiness checks pass.
- Mutation execution remains separately approved and narrowly scoped.
