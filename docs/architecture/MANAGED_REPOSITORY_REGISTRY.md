# Managed Repository Registry

## Purpose

This document defines the managed repository onboarding contract baseline used by AresForge.

The contract supports safe, read-only-first expansion from the default AresForge repository to additional managed repositories without introducing autonomous setup or mutation.

## Managed Repository Classes

- Platform self-managed repository: `yoey2112/aresforge`, always included first/default.
- Fixture/demo repository: a non-production inspection fixture used to validate contract behavior safely.
- Real managed repository: an intentionally onboarded repository with explicit ownership, metadata, readiness evidence, and human-triggered setup expectations.

Fixture/demo posture is explicitly not equivalent to real managed onboarding readiness.

## Command Surface

- `python -m aresforge inspect-managed-repos`
- `python -m aresforge managed-repo-readiness-report`
- `python -m aresforge plan-repo-bootstrap`
- `python -m aresforge demo-managed-repo-governance`

All are human-triggered and read-only.

## Required Onboarding Metadata (Real Managed Repos)

- `repository_slug`
- `project_key`
- `repo_role`
- `governance_profile`
- `default_branch`
- `local_path` posture
- `documentation_roots`
- `artifact_roots`
- `allowed_automation_capabilities`
- `disabled` and `archived` flags

## Required Readiness Checks Before Setup Is Considered

- `inspect-repo-governance`
- `inspect-repo-bootstrap-contract`
- `inspect-managed-repos`
- `managed-repo-readiness-report`
- `plan-repo-bootstrap`

Expected operator validation bundle also includes `python -m pytest` and `git diff --check` in change-bearing work.

## Managed State Documentation Expectations

Managed repository state must be represented consistently across:

- registry output (`inspect-managed-repos`)
- readiness output (`managed-repo-readiness-report`)
- bootstrap planning output (`plan-repo-bootstrap`)
- source-of-truth docs (`BUILD_STATE`, `AGENT_CONTEXT`, `ROADMAP`)

## Safety Boundaries

This contract does not authorize:

- autonomous mutation
- setup command execution by AresForge
- hidden background setup actions
- fixture/demo repositories being treated as production mutation targets

## Extension Direction

Future multi-project expansion can add richer per-repository policy overlays, but must preserve read-only-first defaults and explicit human-triggered mutation gates.
